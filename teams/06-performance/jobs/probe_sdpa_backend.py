"""CUDA probe for attn_impl=sdpa: Flash eligibility, observed repeat-bits, and timing.

Standalone diagnostic (not CI). No edits to models/ or kernels/. Writes JSON for Gate-4 review.
Shapes match Nv_Kernel_Plan / Analysis1: B=4, H=8, KV=2, hd=64, bf16, T in {256,1024,2048}.

Usage (from teams/06-performance on a CUDA pod):
  python jobs/probe_sdpa_backend.py --device cuda --dtype bf16 --out results/sdpa_probe.json
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

PERF = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PERF))

B, H, KV, HD = 4, 8, 2, 64
TS = (256, 1024, 2048)


def _qkv(t: int, device: str, dtype: torch.dtype):
    g = torch.Generator(device=device).manual_seed(1234)
    q = torch.randn(B, H, t, HD, device=device, dtype=dtype, generator=g, requires_grad=True)
    k = torch.randn(B, KV, t, HD, device=device, dtype=dtype, generator=g, requires_grad=True)
    v = torch.randn(B, KV, t, HD, device=device, dtype=dtype, generator=g, requires_grad=True)
    return q, k, v


def _sdpa(q, k, v):
    kwargs = {"is_causal": True}
    if tuple(int(x) for x in torch.__version__.split(".")[:2]) >= (2, 5):
        kwargs["enable_gqa"] = True
    else:
        r = H // KV
        k = k.repeat_interleave(r, dim=1)
        v = v.repeat_interleave(r, dim=1)
    return F.scaled_dot_product_attention(q, k, v, **kwargs)


def _eager(q, k, v):
    r = H // KV
    k = k.repeat_interleave(r, dim=1)
    v = v.repeat_interleave(r, dim=1)
    scale = HD ** -0.5
    scores = (q.float() @ k.float().transpose(-2, -1)) * scale
    t = q.shape[-2]
    scores = scores.masked_fill(~torch.ones(t, t, dtype=torch.bool, device=q.device).tril(), float("-inf"))
    return (scores.softmax(-1).to(v.dtype) @ v)


def _backends():
    from torch.nn.attention import SDPBackend, sdpa_kernel

    out = {}
    q, k, v = _qkv(256, "cuda", torch.bfloat16)
    for name, backend in (
        ("FLASH_ATTENTION", SDPBackend.FLASH_ATTENTION),
        ("EFFICIENT_ATTENTION", SDPBackend.EFFICIENT_ATTENTION),
        ("CUDNN_ATTENTION", SDPBackend.CUDNN_ATTENTION),
    ):
        try:
            with sdpa_kernel(backend):
                y = _sdpa(q, k, v)
                y.sum().backward()
            out[name] = "eligible"
        except Exception as e:  # noqa: BLE001 — probe records ineligibility
            out[name] = f"not_eligible: {type(e).__name__}: {e}"
        q.grad = k.grad = v.grad = None
    return out


def _repeat_bits(t: int, dtype: torch.dtype) -> dict:
    from torch.nn.attention import SDPBackend, sdpa_kernel

    def one():
        q, k, v = _qkv(t, "cuda", dtype)
        with sdpa_kernel(SDPBackend.FLASH_ATTENTION):
            y = _sdpa(q, k, v)
            y.square().mean().backward()
        return y.detach(), q.grad.detach(), k.grad.detach(), v.grad.detach()

    a, b = one(), one()
    return {
        "T": t,
        "out_equal": bool(torch.equal(a[0], b[0])),
        "dq_equal": bool(torch.equal(a[1], b[1])),
        "dk_equal": bool(torch.equal(a[2], b[2])),
        "dv_equal": bool(torch.equal(a[3], b[3])),
        "note": "observed under Flash pin only; not a PyTorch guarantee",
    }


def _time_ms(fn, warmup: int, iters: int) -> tuple[float, float]:
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    start, end = torch.cuda.Event(True), torch.cuda.Event(True)
    start.record()
    for _ in range(iters):
        fn()
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / iters, torch.cuda.max_memory_allocated() / 2**30


def _timing(t: int, dtype: torch.dtype, warmup: int, iters: int) -> dict:
    from torch.nn.attention import SDPBackend, sdpa_kernel

    rows = {}

    def run(label, call):
        def body():
            q, k, v = _qkv(t, "cuda", dtype)
            y = call(q, k, v)
            y.square().mean().backward()

        ms, gib = _time_ms(body, warmup, iters)
        rows[label] = {"ms_fwd_bwd": round(ms, 3), "peak_GiB": round(gib, 3)}

    run("eager", _eager)

    def flash_call(q, k, v):
        with sdpa_kernel(SDPBackend.FLASH_ATTENTION):
            return _sdpa(q, k, v)

    run("sdpa_flash", flash_call)
    try:
        from kernels.attention import attention as triton_attn

        run("triton", triton_attn)  # same [B, H, T, hd] / [B, KV, T, hd] layout as SDPA
    except Exception as e:  # noqa: BLE001
        rows["triton"] = {"error": f"{type(e).__name__}: {e}"}
    return {"T": t, **rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="bf16", choices=("bf16", "fp16", "fp32"))
    ap.add_argument("--out", type=Path, default=Path("results/sdpa_probe.json"))
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--skip-timing", action="store_true")
    a = ap.parse_args()
    if a.device != "cuda" or not torch.cuda.is_available():
        print("CUDA required", file=sys.stderr)
        return 2
    dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[a.dtype]
    report = {
        "probe": "sdpa_backend",
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "python": platform.python_version(),
        "shape": {"B": B, "H": H, "KV": KV, "hd": HD, "dtype": a.dtype},
        "backends": _backends(),
        "repeat_bits_flash": [_repeat_bits(t, dtype) for t in TS],
        "timing": [] if a.skip_timing else [_timing(t, dtype, a.warmup, a.iters) for t in TS],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"[probe_sdpa_backend] wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
