"""Measure run-level MFU across real processes and GPUs. A check of metrics.mfu_run, not a throughput result.

    python -m perfkit.mfu_fixture --config configs/tiny_cpu.yaml --out out.json             # one process
    torchrun --standalone --nproc_per_node 2 -m perfkit.mfu_fixture --out out.json          # one rank per GPU
    torchrun --standalone --nproc_per_node 2 -m perfkit.mfu_fixture --sync-grads --out out.json

Each rank trains the config on random tokens with SGD between two barriers; global tokens/s is all tokens over
the slowest rank's time. --sync-grads adds a gradient all-reduce; without it per-rank and run-level MFU agree.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import time
from contextlib import nullcontext
from pathlib import Path

import torch
import torch.distributed as dist

from models.config import load_config, model_config
from models.gpt import GPT
from perfkit.metrics import flops_per_token, mfu, mfu_run, peak_tflops
from perfkit.schema import MFU_SCOPES

ROOT = Path(__file__).resolve().parents[1]
AMP = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": None}


def _gather(value, device, dtype=torch.float64) -> list:
    """Every rank's value, in rank order. One process: just this value."""
    if not dist.is_initialized():
        return [value]
    x = torch.tensor([value], dtype=dtype, device=device)
    out = [torch.zeros_like(x) for _ in range(dist.get_world_size())]
    dist.all_gather(out, x)
    return [t.item() for t in out]


def _barrier():
    """dist.barrier() when distributed, else nothing."""
    if dist.is_initialized():
        dist.barrier()


def _sync_grads(params, world: int):
    """Average the gradients over the ranks as one flat all_reduce, the way a data-parallel trainer would."""
    grads = [p.grad for p in params if p.grad is not None]
    flat = torch.cat([g.reshape(-1) for g in grads])
    dist.all_reduce(flat)
    flat /= world
    i = 0
    for g in grads:
        g.copy_(flat[i:i + g.numel()].view_as(g))
        i += g.numel()


def _name(device) -> str:
    return torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu"


def measure(a) -> dict | None:
    """Run the steps on every rank; rank 0 returns the run-level MFU JSON, the others None."""
    world = int(os.environ.get("WORLD_SIZE", "1"))
    cuda = torch.cuda.is_available()
    if world > 1:
        dist.init_process_group("nccl" if cuda else "gloo")
    rank = dist.get_rank() if world > 1 else 0
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    device = torch.device("cuda", local_rank) if cuda else torch.device("cpu")
    if cuda:
        torch.cuda.set_device(device)
    cfg = load_config(a.config, a.overrides)
    mcfg = model_config(cfg)
    B, T = a.batch_size or cfg["run"]["batch_size"], mcfg.block_size
    dtype = a.dtype or cfg["run"]["dtype"]
    if not cuda and dtype == "fp16":
        dtype = "bf16"
    torch.manual_seed(cfg["run"]["seed"])                      # same weights on every rank
    model = GPT(mcfg).to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.SGD(params, lr=1e-4)
    gen = torch.Generator(device=device).manual_seed(cfg["run"]["seed"] + 1000 + rank)   # different tokens per rank
    amp = torch.autocast(device.type, dtype=AMP[dtype]) if AMP[dtype] is not None else nullcontext()
    lens = getattr(model.tok, "lens", None)
    support = []

    def step(record=False):
        x = torch.randint(0, mcfg.vocab_size, (B, T), device=device, generator=gen)
        y = torch.randint(0, mcfg.vocab_size, (B, T), device=device, generator=gen)
        with amp:
            _, loss = model(x, y)
        loss.backward()
        if a.sync_grads and world > 1:
            _sync_grads(params, world)
        opt.step()
        opt.zero_grad(set_to_none=True)
        if record and lens is not None:
            support.append(lens.index_select(0, x.reshape(-1)).float().mean())

    for _ in range(a.warmup):
        step()
    if cuda:
        torch.cuda.synchronize(device)
    _barrier()
    start = time.perf_counter()
    for _ in range(a.steps):
        step(record=True)
    if cuda:
        torch.cuda.synchronize(device)
    local_seconds = time.perf_counter() - start               # this rank's own time, before it waits for the others
    _barrier()

    seconds = _gather(local_seconds, device)
    ranks = [int(r) for r in _gather(rank, device)]
    tokens = B * T * a.steps
    if world > 1:
        all_names = [None] * world
        dist.all_gather_object(all_names, (_name(device), socket.gethostname()))
    else:
        all_names = [(_name(device), socket.gethostname())]
    mean_support = float(torch.stack(support).mean()) if support else None
    if world > 1:
        dist.destroy_process_group()
    if rank != 0:
        return None

    peaks = [a.peak_tflops if a.peak_tflops else peak_tflops(n, dtype)[0] for n, _ in all_names]
    f1 = flops_per_token(model, T)
    f2 = flops_per_token(model, T, method="g6-v2", ke2_mean_support_len=mean_support)
    global_tps = tokens * world / max(seconds)                # all tokens over the slowest rank's time
    run = mfu_run(f1, global_tps, peaks, ranks=ranks)
    per_rank = [mfu(f1, tokens / s, p) for s, p in zip(seconds, peaks)]
    known = [r["mfu"] for r in per_rank if r["mfu"] is not None]
    return {
        "world_size": world, "participants": [{"rank": r, "name": n, "host": h, "peak_tflops": p}
                                              for r, (n, h), p in zip(ranks, all_names, peaks)],
        "visible_gpus": torch.cuda.device_count() if cuda else 0,
        "peak_source": "override" if a.peak_tflops else "table",
        "config": str(a.config), "overrides": a.overrides, "dtype": dtype, "batch_size": B, "seq_len": T,
        "steps": a.steps, "warmup": a.warmup, "sync_grads": bool(a.sync_grads and world > 1),
        "data": "synthetic uniform random tokens", "optimizer": "SGD (fixture only)",
        "seconds_per_rank": seconds, "global_tokens_per_s": global_tps,
        "per_rank_tokens_per_s": [tokens / s for s in seconds],
        "flops_g6_v1": f1, "flops_g6_v2": f2, "mean_support_len": mean_support,
        "mfu_scope": MFU_SCOPES[1], "run": run, "run_g6_v2": mfu_run(f2, global_tps, peaks, ranks=ranks),
        "per_rank_mfu": [r["mfu"] for r in per_rank],
        "mean_per_rank_mfu": sum(known) / len(known) if known else None,
        # The two mistakes this contract exists to prevent, computed so the JSON shows how wrong they would be:
        "if_local_tps_over_world_peak": (mfu(f1, tokens / seconds[0], sum(peaks))["mfu"]
                                         if all(p for p in peaks) else None),
        "if_peak_used_device_count": (mfu(f1, global_tps, (peaks[0] or 0) * torch.cuda.device_count())["mfu"]
                                      if cuda and peaks[0] else None),
        "duplicate_rank_result": mfu_run(f1, global_tps + tokens / seconds[0], peaks + peaks[:1],
                                         ranks=ranks + ranks[:1])["mfu_unavailable_reason"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "base.yaml")
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--dtype", choices=sorted(AMP), default=None)
    ap.add_argument("--peak-tflops", type=float, default=None, help="for a GPU not in the table; recorded as an override")
    ap.add_argument("--sync-grads", action="store_true", help="average gradients across ranks after each backward")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("overrides", nargs="*", help="config overrides, key=value, as in perfkit.bench")
    a = ap.parse_args(argv)
    res = measure(a)
    if res is None:
        return 0
    text = json.dumps(res, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
