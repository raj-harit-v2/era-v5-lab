"""How often would objective_v1's trust-region mask fire from sampler/trainer mismatch alone?

    python mismatch_probe.py --model <local folder> --prompts <jsonl with "statement"> --out probe.json \
        [--n 48] [--k 8] [--max-new 512] [--trainable '\\.self_attn\\.'] [--dense]

No reward, no update. The sampler (colocated vLLM) draws k completions per prompt at temperature 1; the training
model (same weights, the trainer's fp32-master / bf16-autocast setup) recomputes each sampled token's log-probability.
objective_v1 keeps a token only when ratio = trainer / sampler lies in [1 - eps, 1 + eps]. With identical weights
every ratio should be 1, so anything outside the region is numerics: different kernels, different batch shapes and,
in an MoE, different routing. Three comparisons on the same tokens:

    engine   trainer (one row per forward) vs the sampler's reported log-probabilities   <- what the trainer masks on
    batch    trainer, all k rows in one forward vs one row per forward
    repeat   trainer, the same forward twice (determinism floor)

For MoE models it also reports how many tokens change their expert set between the one-row and k-row forwards.
Writes aggregate numbers only: no prompt or completion text.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grpo  # noqa: E402
import rollout  # noqa: E402
import routing  # noqa: E402
import train  # noqa: E402
from policy import completion_logprobs, use_fp32_master  # noqa: E402

P_BUCKETS = ((0.0, 0.1), (0.1, 0.5), (0.5, 0.9), (0.9, 1.0001))
POS_BUCKETS = ((0, 64), (64, 256), (256, 10**9))


def ratio_stats(log_ratio: torch.Tensor, eps: float) -> dict:
    """log_ratio: 1-D float64 over real tokens."""
    n = log_ratio.numel()
    if n == 0:
        return {"tokens": 0}
    r = torch.exp(log_ratio)
    below, above = r < 1 - eps, r > 1 + eps
    a = log_ratio.abs()
    q = torch.quantile(a, torch.tensor([0.5, 0.9, 0.99, 0.999], dtype=a.dtype)).tolist()
    return {"tokens": n, "outside": float((below | above).double().mean()), "below": float(below.double().mean()),
            "above": float(above.double().mean()), "mean_abs_logratio": float(a.mean()),
            "abs_logratio_p50_p90_p99_p999": [float(f"{x:.4g}") for x in q], "max_abs_logratio": float(a.max()),
            "k3": float((r - log_ratio - 1).mean())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--max-new", type=int, default=512)
    ap.add_argument("--eps", type=float, default=grpo.TR_EPSILON)
    ap.add_argument("--trainable", default=r"\.self_attn\.")
    ap.add_argument("--dense", action="store_true")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--vllm-util", type=float, default=0.35)
    ap.add_argument("--sampler", choices=("vllm", "hf"), default="vllm",
                    help="hf: sample with the training model itself (no engine comparison; batch and routing only)")
    ap.add_argument("--hf-dtype", choices=("bfloat16", "float32"), default="bfloat16",
                    help="float32 runs the whole training model in fp32 (is the batch-shape gap a bf16 effect?)")
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    t0 = time.time()
    vllm = (rollout.VLLMSampler(a.model, seed=a.seed, gpu_memory_utilization=a.vllm_util, max_model_len=2048)
            if a.sampler == "vllm" else None)
    policy, tok = train.build_model({"kind": "hf", "path": a.model, "dtype": a.hf_dtype, "stop_at_eos": True}, "cuda")
    train.set_trainable(policy.model, [a.trainable])
    n_fp32 = use_fp32_master(policy)
    policy.model.eval()
    sampler = rollout.make_sampler("vllm" if vllm is not None else "hf_batch", policy, vllm, tok.pad_token_id)
    prompts = []
    for line in Path(a.prompts).read_text(encoding="utf-8").splitlines():
        if line.strip() and len(prompts) < a.n:
            ids = tok.apply_chat_template([{"role": "user", "content": json.loads(line)["statement"]}],
                                          add_generation_prompt=True, tokenize=True)
            ids = [int(x) for x in (ids["input_ids"] if hasattr(ids, "keys") else ids)]
            if len(ids) + a.max_new <= 2048:
                prompts.append(ids)
    gen = torch.Generator().manual_seed(a.seed)
    c0 = time.time()
    if vllm is not None:
        rolls = sampler.sample(prompts, a.k, a.max_new, 1.0, gen)
    else:  # a few prompts per generate call: all rows of a call share one padded batch
        rolls = [r for i in range(0, len(prompts), 4) for r in sampler.sample(prompts[i:i + 4], a.k, a.max_new, 1.0, gen)]
    sample_s = time.time() - c0
    is_moe = bool(routing.router_modules(policy.model)) and not a.dense
    cols = {key: [] for key in ("engine", "batch", "repeat", "p", "pos", "seq_engine_sum", "seq_len")}
    flips = {"tokens": 0, "any_layer": 0.0, "top1": 0.0, "mass": 0.0, "groups": 0}
    c0 = time.time()
    with torch.no_grad():
        for p, r in zip(prompts, rolls):
            plen, m = len(p), r.cmask
            lp_k = completion_logprobs(policy, r.seq, plen).double()
            lp_k2 = completion_logprobs(policy, r.seq, plen).double()
            lp_1 = torch.cat([completion_logprobs(policy, r.seq[i:i + 1], plen) for i in range(r.seq.shape[0])], 0).double()
            samp = r.rollout_lp.double() if r.rollout_lp is not None else lp_1  # hf sampler: no engine comparison
            eng = lp_1 - samp
            cols["engine"].append(eng[m].cpu())
            cols["batch"].append((lp_k - lp_1)[m].cpu())
            cols["repeat"].append((lp_k2 - lp_k)[m].cpu())
            cols["p"].append(torch.exp(samp[m]).cpu())
            cols["pos"].append(torch.arange(m.shape[1], device=m.device).expand_as(m)[m].cpu())
            cols["seq_engine_sum"].append((eng * m).sum(1).cpu())
            cols["seq_len"].append(m.sum(1).cpu())
            if is_moe:
                full = routing.completion_positions(plen, m)
                w_k = routing.routing(policy, r.seq, full)
                w_1 = torch.cat([routing.routing(policy, r.seq[i:i + 1], full[i:i + 1]) for i in range(r.seq.shape[0])], 1)
                n_tok = int(m.sum())
                flips["tokens"] += n_tok
                flips["any_layer"] += routing.flip_rate(w_1, w_k)[0] * n_tok
                flips["top1"] += routing.top1_flip_rate(w_1, w_k) * n_tok
                flips["mass"] += routing.mass_shift(w_1, w_k) * n_tok
                flips["groups"] += 1
    forward_s = time.time() - c0
    eng, bat, rep = (torch.cat(cols[key]) for key in ("engine", "batch", "repeat"))
    p, pos = torch.cat(cols["p"]), torch.cat(cols["pos"])
    seq_sum, seq_len = torch.cat(cols["seq_engine_sum"]), torch.cat(cols["seq_len"])
    outside = (torch.exp(eng) < 1 - a.eps) | (torch.exp(eng) > 1 + a.eps)
    per_seq_any, i = [], 0
    for n_ in seq_len.tolist():
        per_seq_any.append(bool(outside[i:i + int(n_)].any()))
        i += int(n_)
    seq_ratio = torch.exp(seq_sum / seq_len.clamp_min(1))  # GSPO-style length-normalised sequence ratio
    out = {"model": a.model, "moe": is_moe, "eps": a.eps, "sampler": a.sampler, "hf_dtype": a.hf_dtype,
           "engine_comparison_valid": vllm is not None, "prompts": len(prompts), "k": a.k, "max_new": a.max_new,
           "trainable_pattern": a.trainable, "fp32_master_params": n_fp32, "real_tokens": int(eng.numel()),
           "engine": ratio_stats(eng, a.eps), "batch": ratio_stats(bat, a.eps), "repeat": ratio_stats(rep, a.eps),
           "engine_by_sampler_prob": {f"{lo}-{min(hi, 1.0)}": ratio_stats(eng[(p >= lo) & (p < hi)], a.eps)
                                      for lo, hi in P_BUCKETS},
           "engine_by_position": {f"{lo}-{hi if hi < 10**9 else 'end'}": ratio_stats(eng[(pos >= lo) & (pos < hi)], a.eps)
                                  for lo, hi in POS_BUCKETS},
           "sequences": len(per_seq_any), "sequences_with_a_masked_token": sum(per_seq_any) / max(len(per_seq_any), 1),
           "sequence_ratio_outside": float(((seq_ratio < 1 - a.eps) | (seq_ratio > 1 + a.eps)).double().mean()),
           "sequence_abs_log_ratio_mean_normalised": float((seq_sum / seq_len.clamp_min(1)).abs().mean()),
           "sequence_abs_log_ratio_sum_p50_p90_max": [float(f"{x:.4g}") for x in
                                                      (*torch.quantile(seq_sum.abs(), torch.tensor([0.5, 0.9],
                                                                       dtype=seq_sum.dtype)).tolist(),
                                                       float(seq_sum.abs().max()))],
           "share_of_sampler_prob_below_0.1": float((p < 0.1).double().mean()),
           "seconds": {"load": round(c0 - forward_s - sample_s - t0, 1) if False else None, "sample": round(sample_s, 1),
                       "forward": round(forward_s, 1), "total": round(time.time() - t0, 1)},
           "gpu": torch.cuda.get_device_name(0), "peak_torch_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
           "versions": train.versions()}
    if is_moe and flips["tokens"]:
        out["routing_one_row_vs_k_rows"] = {"tokens": flips["tokens"],
                                            "expert_set_differs_in_a_layer": flips["any_layer"] / flips["tokens"],
                                            "top1_differs": flips["top1"] / flips["tokens"],
                                            "mass_shift": flips["mass"] / flips["tokens"]}
    out["seconds"].pop("load")
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
