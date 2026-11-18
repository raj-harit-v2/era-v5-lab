"""Sampling throughput on Team 5's LanguageModel: before / after for the RL loop's native sampler.

    python capstone/bench_sampling_g5.py --adapter-config A.yaml --prompt-len 64 --k 8 --max-new 64 --device cpu

Three paths, same prompt, greedy (so outputs must be identical), each timed after one warm-up call:
    before   the adapter's sampler before 16 Nov: re-forward the whole sequence and project EVERY position through the
             131,072-row head at every step (reproduced here as it was)
    head     re-forward the whole sequence, project only the last position (team5_adapter.Bundle.sample default now)
    kv       rl-loop/g5_decode.py: prefill once, then one token per step against a key/value cache
Reports new tokens per second (k rows x max_new / seconds) and whether the three token sequences are identical.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from torch import no_grad  # undotted decorator: pr-guard reads '+@a.b' as an email

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rl-loop"))


@no_grad()
def sample_before(bundle, prompt, k, max_new):
    """The pre-16-Nov loop, greedy: full forward, [:, -1] of the full [k, L, V] logits."""
    seq = torch.tensor([prompt] * k, dtype=torch.long, device=bundle.device)
    for _ in range(max_new):
        logits = bundle.forward(seq, torch.ones_like(seq, dtype=torch.bool))[:, -1, :].float()
        seq = torch.cat([seq, logits.argmax(-1)[:, None]], 1)
    return seq


def sync(device):
    if device == "mps":
        torch.mps.synchronize()
    elif device.startswith("cuda"):
        torch.cuda.synchronize()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter-config", type=Path, required=True)
    ap.add_argument("--prompt-len", type=int, default=64)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--max-new", type=int, default=64)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--paths", default="before,head,kv")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    import team5_adapter as ta  # noqa: PLC0415
    bundle = ta.build(a.adapter_config, device=a.device).require_bundle()
    text = "def add(a, b):\n    return a + b\n\n" * 64
    prompt = bundle.artifacts.encode(text)[: a.prompt_len]
    stop = [-1]  # never stop: every path generates exactly max_new tokens

    def run(path):
        if path == "before":
            return sample_before(bundle, prompt, a.k, a.max_new)
        bundle.kv_cache = path == "kv"
        seq, _, _ = bundle.sample(prompt, a.k, a.max_new, 0.0, None, stop_ids=stop)
        return seq

    rec = {"device": a.device, "prompt_len": a.prompt_len, "k": a.k, "max_new": a.max_new,
           "model_spec": {x: bundle.spec[x] for x in ("n_layer", "n_embd", "n_head", "n_kv_head", "block_size")},
           "experts": bundle.spec["moe"], "torch": torch.__version__, "paths": {}}
    outs = {}
    for path in a.paths.split(","):
        run(path)  # warm-up
        sync(a.device)
        t0 = time.perf_counter()
        outs[path] = run(path).cpu()
        sync(a.device)
        dt = time.perf_counter() - t0
        rec["paths"][path] = {"seconds": round(dt, 3), "new_tokens_per_s": round(a.k * a.max_new / dt, 1)}
    names = list(outs)
    rec["identical_tokens"] = all(torch.equal(outs[names[0]], outs[n]) for n in names[1:])
    if "before" in rec["paths"]:
        for p in names:
            rec["paths"][p]["speedup_vs_before"] = round(rec["paths"]["before"]["seconds"] / rec["paths"][p]["seconds"], 2)
    print(json.dumps(rec))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
