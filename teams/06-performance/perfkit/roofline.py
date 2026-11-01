"""A deliberately approximate forward-pass roofline estimator.

It estimates work from ModelConfig shapes, then compares compute, memory-bandwidth, and
kernel-launch lower bounds. It is for forming profiling hypotheses, not replacing measured
regions. The byte and launch counts are analytical approximations; validate them on each GPU.

Example (from teams/06-performance):
    python -m perfkit.roofline --config configs/base.yaml --gpu "NVIDIA A100-SXM4-40GB" \
        --run results/runs/baseline_v0.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from models.config import load_config
from perfkit.metrics import peak_tflops


# Peak memory bandwidth in GB/s. Values are theoretical vendor specifications, not measured
# sustained bandwidth. More profiles can be added as matching run JSONs become available.
MEMORY_BW_GBS = [
    ("B200", 8000.0),
    ("H200 NVL", 4800.0),
    ("H200", 4800.0),
    ("H100 PCIe", 2000.0),
    ("H100 NVL", 3900.0),
    ("H100", 3350.0),
    ("A100", 1555.0),
    ("RTX 4090", 1008.0),
    ("RTX 3090", 936.0),
    ("RTX 3060", 360.0),
    ("L40S", 864.0),
    ("L40", 864.0),
    ("L4", 300.0),
    ("A10G", 600.0),
    ("A10", 600.0),
    ("V100", 900.0),
    ("T4", 320.0),
    ("P100", 732.0),
]

DTYPE_BYTES = {"fp32": 4.0, "bf16": 2.0, "fp16": 2.0, "fp8": 1.0, "fp4": 0.5}
TOP_LEVEL_REGIONS = ("fwd:embed", "fwd:stack", "fwd:head+loss")
DEFAULT_LAUNCH_US = 5.0  # heuristic; replace with an empirical per-GPU value when available


def _model_dict(mcfg) -> dict:
    if hasattr(mcfg, "to_dict"):
        return mcfg.to_dict()
    if not isinstance(mcfg, dict):
        raise TypeError("mcfg must be a ModelConfig or dict")
    return mcfg.get("model", mcfg)


def _positive_int(name: str, value) -> int:
    value = int(value)
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def _rollup(regions: dict, name: str, children: list[str], *, total: bool = False) -> None:
    rows = [regions[child] for child in children]
    regions[name] = {
        "flops": sum(row["flops"] for row in rows),
        "bytes": sum(row["bytes"] for row in rows),
        "kernels": sum(row["kernels"] for row in rows),
        "inclusive": True,
        "count_in_total": total,
        "assumption": "roll-up of child regions; do not add to the children",
    }


def forward_costs(mcfg: dict, B: int, T: int, dtype: str) -> dict:
    """Estimate forward FLOPs, bytes moved, and kernel count by timed region.

    ``mcfg`` may be a ModelConfig, the model section of a YAML config, or the complete
    loaded YAML config. The returned regions include inclusive roll-ups matching the
    region names in the model; only the top-level forward regions count in the total.
    FLOPs count a multiply-add as two operations. Byte counts use a simple one-pass
    activation/weight model and do not predict cache reuse or fused-kernel behavior.
    """
    cfg = _model_dict(mcfg)
    B, T = _positive_int("B", B), _positive_int("T", T)
    if dtype not in DTYPE_BYTES:
        raise ValueError(f"unsupported dtype {dtype!r}; choose from {tuple(DTYPE_BYTES)}")
    d = _positive_int("n_embd", cfg.get("n_embd", 256))
    L = _positive_int("n_layer", cfg.get("n_layer", 1))
    n_head = _positive_int("n_head", cfg.get("n_head", 1))
    if d % n_head:
        raise ValueError("n_embd must be divisible by n_head")
    n_kv_head = _positive_int("n_kv_head", cfg.get("n_kv_head") or n_head)
    if n_head % n_kv_head:
        raise ValueError("n_kv_head must divide n_head")
    V = _positive_int("vocab_size", cfg.get("vocab_size", 131072))
    h = _positive_int("mlp_ratio", cfg.get("mlp_ratio", 4)) * d
    activation = cfg.get("activation", "gelu")
    if activation not in ("gelu", "swiglu"):
        raise ValueError(f"unsupported activation {activation!r}; choose gelu or swiglu")
    # FFN shape per row: GELU = 2 matrices (d x h, h x d) with biases, GELU ~8 flops per hidden value;
    # SwiGLU = 3 matrices (gate, up, down), no biases, SiLU(gate) * up ~6 flops per hidden value.
    n_mat, act_flops, act_reads = (3, 6, 3) if activation == "swiglu" else (2, 8, 2)
    M, item = B * T, DTYPE_BYTES[dtype]
    hd, kv = d // n_head, n_kv_head
    moe_cfg = cfg.get("moe") or {}
    E = _positive_int("num_experts", moe_cfg.get("num_experts", 8))
    top_k = _positive_int("top_k", moe_cfg.get("top_k", 2))
    shared = max(0, int(moe_cfg.get("num_shared", 0)))
    if top_k > E:
        raise ValueError("top_k cannot exceed num_experts")

    regions: dict[str, dict] = {}

    def put(name, flops, byte_count, kernels, *, count_in_total=False, assumption="shape estimate"):
        regions[name] = {
            "flops": int(flops), "bytes": int(byte_count), "kernels": int(kernels),
            "inclusive": False, "count_in_total": count_in_total, "assumption": assumption,
        }

    def linear(name, rows, width_in, width_out, *, count_in_total=False, kernels=2, item_bytes=item):
        flops = 2 * rows * width_in * width_out + rows * width_out  # GEMM plus bias add
        byte_count = (width_in * width_out + rows * (width_in + width_out)) * item_bytes
        put(name, flops, byte_count, kernels, count_in_total=count_in_total)

    def norm(name):
        # Mean, variance, normalize, scale and shift; parameters are fp32 LayerNorm gains/biases.
        put(name, 8 * M * d, 2 * M * d * item + 2 * d * 4, 3)

    # Embedding (KE is also exposed as a nested region in the model's timing markers).
    if cfg.get("embedding", "table") == "ke1":
        P = _positive_int("ke_max_pos", cfg.get("ke_max_pos", 32))
        codec_dim = 256 * P
        proj_flops = 2 * M * codec_dim * d
        proj_bytes = (codec_dim * d + M * (codec_dim + d)) * item
        if cfg.get("ke_mode", "dynamic") == "cached":
            codec_flops, codec_bytes, codec_kernels = 0, M * codec_dim * 4, 1
            codec_assumption = "cached fp32 codec-table gather"
        else:
            # Scatter-add and per-token z-normalization over the 256*P codec vector.
            codec_flops = M * (6 * codec_dim + 4 * P)
            codec_bytes = M * (3 * codec_dim * 4 + P + 8)
            codec_kernels = 5
            codec_assumption = "dynamic fp32 codec, scatter and z-normalization approximation"
        ke_flops = proj_flops + codec_flops
        ke_bytes = proj_bytes + codec_bytes
        put("fwd:embed.ke", ke_flops, ke_bytes, codec_kernels + 2, assumption=codec_assumption)
        # Parent region also includes position lookup and the token+position addition.
        embed_flops = ke_flops
        embed_bytes = ke_bytes + 3 * M * d * item
        embed_kernels = codec_kernels + 5
        put("fwd:embed", embed_flops, embed_bytes, embed_kernels, count_in_total=True,
            assumption="inclusive KE projection/codec plus position lookup and add")
        regions["fwd:embed.ke"]["inclusive"] = False
    else:
        # Token/position gathers plus their sum; traffic approximates two reads and a write.
        put("fwd:embed", 0, 5 * M * d * item, 3, count_in_total=True,
            assumption="token/position table gathers and pointwise add")

    block_names = []
    for i in range(L):
        prefix = f"fwd:block{i}"
        children = []
        norm(f"{prefix}.ln1")
        children.append(f"{prefix}.ln1")
        qkv_out = d + 2 * kv * hd
        linear(f"{prefix}.attn.qkv", M, d, qkv_out)
        children.append(f"{prefix}.attn.qkv")
        # Causal QK and AV products; flash attention avoids materializing the full score matrix.
        sdpa_flops = 2 * B * n_head * T * T * hd
        sdpa_bytes = B * T * (2 * d + 2 * kv * hd) * item
        put(f"{prefix}.attn.sdpa", sdpa_flops, sdpa_bytes, 1,
            assumption="causal attention arithmetic; linear-size IO, flash-style scores")
        children.append(f"{prefix}.attn.sdpa")
        linear(f"{prefix}.attn.proj", M, d, d)
        children.append(f"{prefix}.attn.proj")
        norm(f"{prefix}.ln2")
        children.append(f"{prefix}.ln2")

        if cfg.get("ffn", "mlp") == "moe":
            # Router is fp32 in forward; include softmax/top-k and selected-gate arithmetic.
            router_flops = 2 * M * d * E + 8 * M * E + 5 * M * top_k
            router_bytes = (d * E + M * (d + 2 * E + top_k)) * 4
            put(f"{prefix}.moe.router", router_flops, router_bytes, 5,
                assumption="fp32 router plus softmax/top-k estimate")
            children.append(f"{prefix}.moe.router")

            routes = M * top_k
            expert_flops = 2 * n_mat * routes * d * h + act_flops * routes * h
            active_expert_weights = E * n_mat * d * h * item
            dispatch_bytes = active_expert_weights + routes * (2 * d + (n_mat - 1) * h) * item
            dispatch = moe_cfg.get("dispatch", "loop")
            dispatch_kernels = max(1, E * 4) if dispatch == "loop" else 8
            put(f"{prefix}.moe.dispatch", expert_flops + 5 * routes,
                dispatch_bytes + routes * d * item, dispatch_kernels,
                assumption=f"top-k expert MLPs and route movement; {dispatch} launch estimate")
            children.append(f"{prefix}.moe.dispatch")

            if shared:
                shared_flops = shared * (2 * n_mat * M * d * h + act_flops * M * h)
                shared_bytes = shared * (n_mat * d * h * item + M * (d + (n_mat - 1) * h) * item)
                put(f"{prefix}.moe.shared", shared_flops, shared_bytes, shared * 4)
                children.append(f"{prefix}.moe.shared")
        else:
            mlp_flops = 2 * n_mat * M * d * h + act_flops * M * h
            mlp_bytes = n_mat * d * h * item + M * (2 * d + act_reads * h) * item
            put(f"{prefix}.mlp", mlp_flops, mlp_bytes, 6 if activation == "gelu" else 5,
                assumption=("two linear layers, GELU and activation movement" if activation == "gelu" else
                            "three linear layers (gate, up, down), SiLU(gate) * up and activation movement"))
            children.append(f"{prefix}.mlp")

        # Midpoint/residual adds are inside the block region, not separate timing markers.
        put(f"{prefix}.residual", 4 * M * d, 4 * M * d * item, 2,
            assumption="unfused residual / midpoint pointwise operations")
        children.append(f"{prefix}.residual")
        _rollup(regions, prefix, children, total=False)
        block_names.append(prefix)

    _rollup(regions, "fwd:stack", block_names, total=True)

    # Final LayerNorm, vocabulary projection, cast/logits and cross-entropy.
    head_flops = 2 * M * d * V + 8 * M * V + 8 * M * d
    head_bytes = d * V * item + M * (d + V) * item + 4 * M * V + 2 * d * 4
    put("fwd:head+loss", head_flops, head_bytes, 5, count_in_total=True,
        assumption="final norm, vocabulary projection and full-logit cross entropy")
    _rollup(regions, "fwd", ["fwd:embed", "fwd:stack", "fwd:head+loss"])

    total_rows = [regions[name] for name in TOP_LEVEL_REGIONS]
    totals = {key: sum(row[key] for row in total_rows) for key in ("flops", "bytes", "kernels")}
    return {
        "B": B, "T": T, "dtype": dtype, "model": cfg,
        "regions": regions, "totals": totals,
        "notes": [
            "Forward only: backward, optimizer, data loading, and communication are excluded.",
            "Byte counts, kernel counts, fusion, cache reuse, and attention implementation are estimates.",
            "Use measured region timings for conclusions; the estimator only suggests likely bounds.",
        ],
    }


def memory_bandwidth_gbs(gpu_name: str) -> tuple[float | None, str | None]:
    """Return a theoretical memory-bandwidth profile for a known GPU name."""
    name = gpu_name.lower()
    for spec, bandwidth in MEMORY_BW_GBS:
        if spec.lower() in name:
            return bandwidth, spec
    return None, None


def estimate_costs(costs: dict, gpu_name: str, *, compute_tflops: float | None = None,
                   bandwidth_gbs: float | None = None, launch_us: float = DEFAULT_LAUNCH_US) -> dict:
    """Convert region FLOPs/bytes/kernels to roofline lower bounds in milliseconds."""
    if launch_us <= 0:
        raise ValueError("launch_us must be > 0")
    dtype = costs["dtype"]
    peak, spec = peak_tflops(gpu_name, dtype)
    compute_tflops = compute_tflops if compute_tflops is not None else peak
    known_bandwidth, _ = memory_bandwidth_gbs(gpu_name)
    bandwidth_gbs = bandwidth_gbs if bandwidth_gbs is not None else known_bandwidth
    if compute_tflops is None or compute_tflops <= 0:
        raise ValueError(f"no {dtype} compute peak for {gpu_name}; pass compute_tflops")
    if bandwidth_gbs is None or bandwidth_gbs <= 0:
        raise ValueError(f"no memory-bandwidth profile for {gpu_name}; pass bandwidth_gbs")

    by_region = {}
    total_flops = total_bytes = 0
    total_compute = total_memory = total_launch = total_nonlaunch = 0.0
    for name, row in costs["regions"].items():
        compute_ms = row["flops"] / (compute_tflops * 1e9)
        memory_ms = row["bytes"] / (bandwidth_gbs * 1e6)
        launch_ms = row["kernels"] * launch_us / 1000.0
        roofline_ms = max(compute_ms, memory_ms)
        bound = "compute" if compute_ms >= memory_ms else "bandwidth"
        predicted_ms = max(roofline_ms, launch_ms)
        if row.get("count_in_total"):
            total_flops += row["flops"]
            total_bytes += row["bytes"]
            total_compute += compute_ms
            total_memory += memory_ms
            total_launch += launch_ms
            total_nonlaunch += roofline_ms
        by_region[name] = {
            **row, "compute_ms": compute_ms, "bandwidth_ms": memory_ms,
            "launch_ms": launch_ms, "roofline_ms": roofline_ms,
            "predicted_ms": predicted_ms,
            "bound": "launch" if launch_ms > roofline_ms else bound,
        }
    return {
        "gpu": gpu_name, "gpu_spec": spec, "dtype": dtype,
        "B": costs.get("B"), "T": costs.get("T"),
        "compute_tflops": compute_tflops, "bandwidth_gbs": bandwidth_gbs,
        "launch_us": launch_us, "regions": by_region,
        "totals": {
            "flops": total_flops, "bytes": total_bytes,
            "compute_ms": total_compute, "bandwidth_ms": total_memory,
            "launch_ms": total_launch,
            "roofline_ms": total_nonlaunch,
            "predicted_ms": max(total_nonlaunch, total_launch),
            "bound": "launch" if total_launch > total_nonlaunch else
                     "compute" if total_compute >= total_memory else "bandwidth",
        },
        "notes": costs["notes"],
    }


def compare_measured(estimate: dict, run: dict) -> list[dict]:
    """Compare predicted and measured medians for matching forward regions in a perfkit run."""
    measured = (run.get("layer") or {}).get("regions") or {}
    rows = []
    for name, pred in estimate["regions"].items():
        if not name.startswith("fwd:") or name not in measured:
            continue
        actual = measured[name].get("median")
        if actual is None:
            continue
        predicted = pred["predicted_ms"]
        rows.append({
            "region": name, "predicted_ms": predicted, "measured_ms": actual,
            "measured_over_predicted": actual / predicted if predicted > 0 else None,
            "bound": pred["bound"], "level": measured[name].get("level"),
        })
    return rows


def render_table(estimate: dict) -> str:
    """Render an aligned, human-readable region table like the correctness summary."""
    measured = {row["region"]: row for row in estimate.get("measured_regions", [])}
    rows = []
    for name, cost in estimate["regions"].items():
        if not name.startswith("fwd:"):
            continue
        scope = "total" if cost.get("count_in_total") else "sum" if cost.get("inclusive") else "part"
        actual = measured.get(name, {})
        ratio = actual.get("measured_over_predicted")
        rows.append((
            name, scope, f"{cost['flops']:.3g}", f"{cost['bytes']:.3g}",
            f"{cost['compute_ms']:.3f}", f"{cost['bandwidth_ms']:.3f}",
            f"{cost['launch_ms']:.3f}", f"{cost['predicted_ms']:.3f}", cost["bound"],
            f"{actual['measured_ms']:.3f}" if actual.get("measured_ms") is not None else "-",
            f"{ratio:.2f}x" if ratio is not None else "-",
        ))

    columns = ("region", "scope", "FLOPs", "bytes", "compute ms", "memory ms",
               "launch ms", "estimate ms", "bound", "measured ms", "meas/est")
    widths = [max(len(column), *(len(row[i]) for row in rows)) for i, column in enumerate(columns)]
    fmt = "  ".join(f"{{:{width}}}" for width in widths)
    lines = [
        f"Roofline estimate: {estimate['gpu']} ({estimate.get('gpu_spec') or 'custom profile'})  "
        f"dtype={estimate['dtype']}  B={estimate.get('B', '?')}  T={estimate.get('T', '?')}",
        f"Compute peak: {estimate['compute_tflops']:g} TFLOP/s  "
        f"Memory bandwidth: {estimate['bandwidth_gbs']:g} GB/s  "
        f"Launch estimate: {estimate['launch_us']:g} us/kernel",
        "",
        fmt.format(*columns),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(fmt.format(*row).rstrip() for row in rows)
    total = estimate["totals"]
    lines.extend((
        "",
        f"Total (top-level regions): {total['flops']:.3g} FLOPs, {total['bytes']:.3g} bytes, "
        f"{total['predicted_ms']:.3f} ms estimated; {total['bound']} bound.",
    ))
    run_path = estimate.get("measured_run")
    if run_path:
        lines.append(f"Measured comparison: {run_path}  (meas/est is a comparison, not a pass/fail threshold)")
    lines.append("Scope: total rows are added once; sum rows include their child parts; part rows are individual estimates.")
    return "\n".join(lines)


def _default_batch(run_cfg: dict, gpu_name: str) -> int:
    configured = run_cfg.get("batch_size")
    if isinstance(configured, int):
        return configured
    return 32 if any(key in gpu_name.lower() for key in ("a100", "h100", "h200", "b200")) else 8


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Estimate forward-region compute, bandwidth and launch ceilings")
    parser.add_argument("--config", required=True, help="Model config YAML")
    parser.add_argument("--gpu", required=True, help="GPU name, e.g. NVIDIA A100-SXM4-40GB")
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--seq-len", type=int, default=None)
    parser.add_argument("--peak-tflops", type=float, default=None, help="override dense compute peak")
    parser.add_argument("--bandwidth-gbs", type=float, default=None, help="override memory bandwidth profile")
    parser.add_argument("--launch-us", type=float, default=DEFAULT_LAUNCH_US,
                        help="estimated launch latency per kernel (default: heuristic 5 us)")
    parser.add_argument("--run", help="optional measured perfkit run JSON to compare forward regions")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    model_cfg = cfg["model"]
    batch = (args.batch_size if args.batch_size is not None
             else _default_batch(cfg.get("run", {}), args.gpu))
    seq_len = args.seq_len if args.seq_len is not None else model_cfg["block_size"]
    dtype = cfg.get("run", {}).get("dtype", "bf16")
    costs = forward_costs(model_cfg, batch, seq_len, dtype)
    estimate = estimate_costs(costs, args.gpu, compute_tflops=args.peak_tflops,
                              bandwidth_gbs=args.bandwidth_gbs, launch_us=args.launch_us)
    if args.run:
        run = json.loads(Path(args.run).read_text(encoding="utf-8"))
        estimate["measured_regions"] = compare_measured(estimate, run)
        estimate["measured_run"] = str(args.run)
    print(render_table(estimate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
