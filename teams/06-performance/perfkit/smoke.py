"""Smoke test: does a config build, train and run at a sane speed on this machine?  [implemented]

    cd teams/06-performance
    python -m perfkit.smoke                                         # configs/base.yaml
    python -m perfkit.smoke --config configs/tiny_cpu.yaml        # laptop
    python -m perfkit.smoke run.batch_size=16 model.ce_impl=chunked  # key=value overrides as in bench

Prints: GPU, params, reversible reconstruction error, loss at the start and end, median step time
with p10 / p90, tokens/s, peak memory, whether every weight is finite. Everything comes from the config, as in
bench: run.device, run.dtype (bf16 on a GPU without native bf16 falls back to fp16 + GradScaler, bench's rule),
run.batch_size, smoke.warmup and smoke.steps (--batch, --warmup, --steps are shortcuts for those keys).
Every step, warmup included, is a real training step: optim.schedule / warmup_steps / min_lr_ratio are
applied over smoke.warmup + smoke.steps.

Not the baseline: plain wall-clock step times with one CUDA event pair, no per-part regions, no run JSON.
Gate 1 numbers come from perfkit.bench on committed code.
"""
from __future__ import annotations

import argparse
import sys
import time
from contextlib import nullcontext
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataio.loader import Loader  # noqa: E402
from models.config import load_config, model_config  # noqa: E402
from models.gpt import GPT  # noqa: E402
from models.optim import build_optimizer  # noqa: E402
from models.reversible import reconstruction_error  # noqa: E402
from perfkit.bench import AMP, choose_dtype, pick_device, resolve_batch  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "configs/base.yaml"))
    ap.add_argument("--batch", type=int, default=None, help="(= run.batch_size)")
    ap.add_argument("--steps", type=int, default=None, help="timed steps (= smoke.steps)")
    ap.add_argument("--warmup", type=int, default=None, help="(= smoke.warmup)")
    ap.add_argument("overrides", nargs="*", help="key=value, e.g. model.reversible=false")
    a = ap.parse_args(argv)
    ov = list(a.overrides)
    for key, val in (("run.batch_size", a.batch), ("smoke.steps", a.steps), ("smoke.warmup", a.warmup)):
        if val is not None:
            ov.append(f"{key}={val}")

    cfg = load_config(a.config, ov)
    m = model_config(cfg)
    run, sm = cfg["run"], cfg["smoke"]
    dev = pick_device(run["device"])
    notes = []
    amp = AMP[choose_dtype(run["dtype"], dev, notes)]
    B = resolve_batch(run["batch_size"])
    warmup, steps = sm["warmup"], sm["steps"]
    print("GPU:", torch.cuda.get_device_name() if dev.type == "cuda" else dev.type, "| torch", torch.__version__,
          "| dtype", amp or torch.float32, "| B", B, "| T", m.block_size, "| config", Path(a.config).name, *ov)
    for n in notes:
        print("note:", n)

    def autocast():
        return torch.autocast(dev.type, dtype=amp) if amp is not None else nullcontext()

    ld = Loader(cfg["data"]["source"], B, m.block_size, dev, data_dir=cfg["data"]["dir"], vocab_size=m.vocab_size,
                seed=run["seed"], tokenizer_path=cfg["data"]["tokenizer_path"], prefetch=cfg["data"]["prefetch"])
    print(f"tokenizer: BrahmicTokenizer-131K | vocab {ld.vocab_size} | artifact {ld.tokenizer.path}")
    torch.manual_seed(run["seed"])
    model = GPT(m, ld.token_bytes(m.ke_max_pos) if m.embedding == "ke1" else None).to(dev)
    opt = build_optimizer(model, cfg["optim"])
    scaler = torch.amp.GradScaler("cuda") if amp == torch.float16 else None
    total, active = model.param_counts()
    print(f"params total {total / 1e6:.1f}M, active {active / 1e6:.1f}M")

    if m.reversible:
        x, _ = ld.next_batch()
        with autocast():
            err = reconstruction_error(model.embed(x), model.blocks)
        print(f"reversible reconstruction error: {err:.1e}  ({'OK' if err < 1e-3 else 'TOO HIGH'})")

    def step(step_index):
        x, y = ld.next_batch()
        with autocast():
            loss = model(x, y)[1]
        if scaler:
            scaler.scale(loss).backward()
            opt.unscale(scaler)
        else:
            loss.backward()
        ld.prefetch()
        torch.nn.utils.clip_grad_norm_(model.parameters(), run["grad_clip"])
        opt.set_lr(step_index, warmup + steps,
                   schedule=cfg["optim"]["schedule"],
                   warmup_steps=cfg["optim"]["warmup_steps"],
                   min_lr_ratio=cfg["optim"]["min_lr_ratio"])
        opt.step(scaler)
        if scaler:
            scaler.update()
        for moe in model.moe_layers():
            moe.update_bias()
        opt.zero_grad()
        return loss

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    times, losses = [], []
    for i in range(warmup + steps):
        if dev.type == "cuda":
            start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
            start.record()
        t0 = time.perf_counter()
        loss = step(i)
        if dev.type == "cuda":
            end.record()
            end.synchronize()
            ms = start.elapsed_time(end)
        else:
            ms = (time.perf_counter() - t0) * 1e3
        losses.append(loss.item())
        if i >= warmup:
            times.append(ms)
        if i % 10 == 0:
            print(f"step {i:3d}  loss {losses[-1]:.3f}  {ms:.0f} ms")

    times.sort()
    med = times[len(times) // 2]
    print(f"\nloss {losses[0]:.3f} -> {losses[-1]:.3f}  (start should be ~ln({m.vocab_size}) = "
          f"{torch.log(torch.tensor(float(m.vocab_size))):.2f})")
    print(f"step median {med:.1f} ms  p10 {times[len(times) // 10]:.1f}  p90 {times[9 * len(times) // 10]:.1f}"
          f"  -> {B * m.block_size / med * 1e3:,.0f} tokens/s")
    if dev.type == "cuda":
        print(f"peak memory {torch.cuda.max_memory_allocated() / 2 ** 30:.1f} GB")
    print("all weights finite:", all(torch.isfinite(p).all().item() for p in model.parameters()))


if __name__ == "__main__":
    main()
