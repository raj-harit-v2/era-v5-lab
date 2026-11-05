#!/usr/bin/env python3
"""Check a Hugging Face model folder (bf16 or llm-compressor output) and write its SHA-256 manifest.

    python model_check.py <model_dir> --label W4A16 --out manifest_W4A16.json [--base <bf16_dir>] [--expect-quantized]

Reads only the safetensors headers (stdlib, no torch), so it runs anywhere. It reports:
  router   dtypes of the 16 OLMoE router weights (`mlp.gate.weight`); must be BF16 or F32 (G12 rule)
  output   dtype of `lm_head.weight`; must be BF16 or F32
  packed   how many Linear weights are stored packed (`weight_packed`): experts and attention separately
  size     bytes of all weight files, and bits per weight against the bf16 parameter count (--base)
With --expect-quantized it fails unless every expert and attention projection is packed, so a run where
llm-compressor silently skipped the experts (for example a fused-experts module it cannot see) stops here.
The manifest lists every file of the folder with its size and SHA-256: commit the manifest, never the weights.
"""
from __future__ import annotations

import argparse, hashlib, json, re, struct, sys
from pathlib import Path

OK_HIGH = {"BF16", "F32"}
ROUTER = re.compile(r"(^|\.)mlp\.gate\.weight$")
EXPERT = re.compile(r"\.mlp\.experts\.\d+\.(gate_proj|up_proj|down_proj)\.")
ATTN = re.compile(r"\.self_attn\.(q_proj|k_proj|v_proj|o_proj)\.")


def read_header(path: Path) -> dict:
    """The JSON header of a .safetensors file: {tensor name: {dtype, shape, data_offsets}}."""
    with open(path, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        header = json.loads(fh.read(n))
    header.pop("__metadata__", None)
    return header


def tensors(model_dir: Path) -> dict:
    out = {}
    for f in sorted(model_dir.glob("*.safetensors")):
        out.update(read_header(f))
    if not out:
        raise SystemExit(f"{model_dir}: no .safetensors files")
    return out


def n_params(ts: dict) -> int:
    total = 0
    for t in ts.values():
        k = 1
        for d in t["shape"]:
            k *= d
        total += k
    return total


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def check(model_dir: Path, base_params: int | None = None) -> dict:
    ts = tensors(model_dir)
    router = {k: v["dtype"] for k, v in ts.items() if ROUTER.search(k)}
    output = ts.get("lm_head.weight", {}).get("dtype")
    packed = [k for k in ts if k.endswith(".weight_packed")]
    expert_lin = {k.rsplit(".", 1)[0] for k in ts if EXPERT.search(k)}
    attn_lin = {k.rsplit(".", 1)[0] for k in ts if ATTN.search(k)}
    weight_bytes = sum(f.stat().st_size for f in model_dir.glob("*.safetensors"))
    params = base_params or n_params(ts)
    return {
        "router_dtypes": sorted(set(router.values())), "router_tensors": len(router),
        "output_dtype": output,
        "experts_linear": len(expert_lin), "experts_packed": sum(bool(EXPERT.search(k)) for k in packed),
        "attn_linear": len(attn_lin), "attn_packed": sum(bool(ATTN.search(k)) for k in packed),
        "weight_bytes": weight_bytes, "size_gb": round(weight_bytes / 1e9, 2),
        "base_params": params, "bpw": round(8 * weight_bytes / params, 2),
    }


def problems(info: dict, expect_quantized: bool) -> list[str]:
    out = []
    if info["router_tensors"] == 0:
        out.append("no router tensor (mlp.gate.weight) found")
    elif not set(info["router_dtypes"]) <= OK_HIGH:
        out.append(f"router stored as {info['router_dtypes']}, must be BF16 or F32")
    if info["output_dtype"] not in OK_HIGH:
        out.append(f"lm_head stored as {info['output_dtype']}, must be BF16 or F32")
    if expect_quantized:
        if info["experts_linear"] == 0 or info["experts_packed"] != info["experts_linear"]:
            out.append(f"experts packed {info['experts_packed']} of {info['experts_linear']}: not all experts are quantized")
        if info["attn_packed"] != info["attn_linear"]:
            out.append(f"attention packed {info['attn_packed']} of {info['attn_linear']}")
    return out


def manifest(model_dir: Path, label: str, info: dict) -> dict:
    files = [{"file": f.name, "bytes": f.stat().st_size, "sha256": sha256(f)}
             for f in sorted(model_dir.iterdir()) if f.is_file()]
    return {"label": label, "dir": model_dir.name, "check": info, "files": files}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_dir", type=Path)
    ap.add_argument("--label", required=True, help="format label, e.g. bf16 or W4A16")
    ap.add_argument("--out", type=Path, help="manifest JSON to write")
    ap.add_argument("--base", type=Path, help="bf16 model folder: its parameter count is the bits-per-weight base")
    ap.add_argument("--expect-quantized", action="store_true", help="fail unless experts and attention are packed")
    args = ap.parse_args()

    base_params = n_params(tensors(args.base)) if args.base else None
    info = check(args.model_dir, base_params)
    print(json.dumps(info, indent=1))
    bad = problems(info, args.expect_quantized)
    if args.out:
        args.out.write_text(json.dumps(manifest(args.model_dir, args.label, info), indent=1) + "\n")
        print(f"wrote {args.out}")
    if bad:
        sys.exit(f"{args.label}: " + "; ".join(bad))
    print(f"{args.label}: router {info['router_dtypes']}, lm_head {info['output_dtype']}: OK")


if __name__ == "__main__":
    main()
