"""Numerics-only trust-region firing and expert-set flips on Team 5's LanguageModel (rl-loop/mismatch_probe.py logic).

    python capstone/mismatch_g5.py --adapter-config A.yaml --prompts rows.jsonl --k 8 --max-new 64 --n 16 \
        --device cpu --out probe.json

No reward, no update. k completions per prompt are drawn once (fp32, temperature 1, the adapter's native sampler).
The same tokens are then re-scored under four settings of the training forward:

    fp32_row     fp32, one row per forward                      (reference)
    fp32_batch   fp32, all k rows in one forward
    bf16_row     bf16 autocast, one row per forward
    bf16_batch   bf16 autocast, all k rows in one forward       (the trainer under train.autocast bf16)

and pairs of them are compared the way objective_v1 would: share of real tokens whose ratio exp(lp_a - lp_b) lies
outside [1 - eps, 1 + eps], quantiles of |log ratio|, and the share of (token, layer) pairs whose top-k expert set
differs. Expert sets are read from G5's own routing rule, recomputed in a pre-hook on each `MoE` from the exact input
it receives (`F.linear(x.float(), router.weight.float()).softmax(-1).topk(k)`, model.py), because G5 calls the router
weight functionally and a module hook on `router` never fires.

With the native sampler the trainer's ratio at epoch 1 is exactly 1 (it recomputes the sampler log-probabilities
itself); these pairs measure what a different engine (vLLM in bf16, other batch shapes) would add. Writes aggregates
only: no prompt or completion text.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rl-loop"))

PAIRS = (("fp32_batch", "fp32_row"), ("bf16_row", "fp32_row"), ("bf16_batch", "bf16_row"),
         ("bf16_batch", "fp32_row"), ("fp32_row_repeat", "fp32_row"))


def ratio_stats(lr: torch.Tensor, eps: float) -> dict:
    n = lr.numel()
    if n == 0:
        return {"tokens": 0}
    r = torch.exp(lr)
    a = lr.abs()
    q = torch.quantile(a, torch.tensor([0.5, 0.9, 0.99, 0.999], dtype=a.dtype)).tolist()
    return {"tokens": n, "outside": float(((r < 1 - eps) | (r > 1 + eps)).double().mean()),
            "abs_logratio_p50_p90_p99_p999": [float(f"{x:.4g}") for x in q], "max_abs_logratio": float(a.max())}


class RouteRecorder:
    """Pre-hooks on every G5 MoE: record the top-k expert set of each valid flattened row, per layer."""

    def __init__(self, model, moe_cls):
        self.layers = [m for m in model.modules() if isinstance(m, moe_cls)]
        self.calls: list[list[torch.Tensor]] = []
        self.handles = [m.register_forward_pre_hook(self._hook(i)) for i, m in enumerate(self.layers)]
        self.current: list | None = None

    def _hook(self, i):
        def hook(mod, args):
            if self.current is None:  # not recording (e.g. while sampling)
                return
            x = args[0]
            flat = x.reshape(-1, x.shape[-1])
            with torch.autocast(device_type=x.device.type, enabled=False):
                scores = F.linear(flat.float(), mod.router.weight.float()).softmax(-1)
            choice = scores.topk(mod.topk, dim=-1).indices.sort(-1).values
            self.current[i] = choice.reshape(*x.shape[:-1], mod.topk).detach().cpu()
        return hook

    def start(self):
        self.current = [None] * len(self.layers)

    def stop(self):
        out, self.current = self.current, None
        return out

    def close(self):
        for h in self.handles:
            h.remove()


def score(policy, seqs: list[torch.Tensor], plen: int, batch: bool, bf16: bool, rec: RouteRecorder, device: str):
    """Per-token log-probs [k, T] of the completion and per-layer expert sets [k, P+T, topk] under one setting."""
    from policy import completion_logprobs  # noqa: PLC0415
    seq = torch.stack(seqs).to(device)
    ctx = torch.autocast(device_type=torch.device(device).type, dtype=torch.bfloat16) if bf16 else torch.autocast(
        device_type=torch.device(device).type, enabled=False)
    with torch.no_grad(), ctx:
        if batch:
            rec.start()
            lp = completion_logprobs(policy, seq, plen).float().cpu()
            routes = rec.stop()
        else:
            lps, per = [], []
            for i in range(seq.shape[0]):
                rec.start()
                lps.append(completion_logprobs(policy, seq[i:i + 1], plen).float().cpu())
                per.append(rec.stop())
            lp = torch.cat(lps, 0)
            routes = [torch.cat([p[layer] for p in per], 0) for layer in range(len(per[0]))]
    return lp, routes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter-config", type=Path, required=True)
    ap.add_argument("--prompts", type=Path, required=True, help="jsonl rows with input_ids and prompt_len")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--max-new", type=int, default=64)
    ap.add_argument("--eps", type=float, default=0.2)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    import team5_adapter as ta  # noqa: PLC0415
    res = ta.build(a.adapter_config, device=a.device)
    bundle = res.require_bundle()
    policy = bundle.policy()
    moe_cls = sys.modules["week2.model"].MoE
    rec = RouteRecorder(bundle.model, moe_cls)
    rows = [json.loads(x) for x in a.prompts.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if r["prompt_len"] + a.max_new <= bundle.spec["block_size"]][: a.n]
    gen = torch.Generator(device=a.device).manual_seed(a.seed)
    settings = {"fp32_row": (False, False), "fp32_batch": (True, False), "bf16_row": (False, True),
                "bf16_batch": (True, True), "fp32_row_repeat": (False, False)}
    lrs = {p: [] for p in PAIRS}
    flips = {p: [0, 0] for p in PAIRS}
    flips_by_layer = {p: None for p in PAIRS}
    t0 = time.perf_counter()
    for r in rows:
        prompt = r["input_ids"][: r["prompt_len"]]
        seq, cmask, _ = bundle.sample(prompt, a.k, a.max_new, 1.0, gen)
        seqs, plen = list(seq.cpu()), len(prompt)
        out = {name: score(policy, seqs, plen, b, h, rec, a.device) for name, (b, h) in settings.items()}
        real = cmask.cpu().bool()
        tok_valid = torch.cat([torch.ones(seq.shape[0], plen, dtype=torch.bool), real], 1)
        for pa, pb in PAIRS:
            (la, ra), (lb, rb) = out[pa], out[pb]
            lrs[(pa, pb)].append((la.double() - lb.double())[real])
            per_layer = []
            for layer in range(len(ra)):
                diff = (ra[layer] != rb[layer]).any(-1)[tok_valid]
                per_layer.append(int(diff.sum()))
                flips[(pa, pb)][0] += int(diff.sum())
                flips[(pa, pb)][1] += int(tok_valid.sum())
            fl = flips_by_layer[(pa, pb)]
            flips_by_layer[(pa, pb)] = per_layer if fl is None else [x + y for x, y in zip(fl, per_layer)]
    rec.close()
    report = {"schema": "g10-capstone-mismatch/1", "adapter_status": res.status, "model_spec": bundle.spec,
              "device": a.device, "prompts": len(rows), "k": a.k, "max_new": a.max_new, "eps": a.eps,
              "sampler": "adapter native (no KV cache), fp32, temperature 1", "seconds": round(time.perf_counter() - t0, 1),
              "pairs": {}}
    for p in PAIRS:
        lr = torch.cat(lrs[p]) if lrs[p] else torch.zeros(0, dtype=torch.float64)
        report["pairs"][f"{p[0]}_vs_{p[1]}"] = {**ratio_stats(lr, a.eps),
                                               "expert_set_flip_share": flips[p][0] / max(flips[p][1], 1),
                                               "expert_set_flips_by_layer": flips_by_layer[p]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1))
    print(json.dumps({k: (v["outside"], v["expert_set_flip_share"]) for k, v in report["pairs"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
