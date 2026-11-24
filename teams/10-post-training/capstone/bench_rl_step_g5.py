"""RL step throughput and memory on Team 5's LanguageModel: the sampler against rows in flight, a component split of one
decode step, and the trainer's own update, so the share of an RL step spent sampling can be read off.

    python capstone/bench_rl_step_g5.py --g5-root G --spec SPEC.json --byte-table T.npz --device cuda --dtype fp16 \\
        --rows 1,4,16,64,128,256 --k 8 --prompt-len 416 --max-new 512 --out OUT/

What runs (every timing synchronises the device before reading the clock; one warm-up call per arm first):
  decode     rl-loop/g5_decode.sample exactly as the RL job calls it (sampler `policy`, model.kv_cache true):
               per_prompt   R / k calls of k rows, one after another (rollout.PolicySampler: one call per prompt)
               one_call     one call of R rows (the same prompt R times: the upper bound of batching across prompts)
               batched      g5_decode.sample_many over R / k prompts of the --prompt-lens mix (present only if the module has it)
             stop is disabled, so every row runs to max_new (tokens/s = rows x max_new / seconds). Temperature 1, seeded
             generator on the device. An instrumented second call records the time of every decode step (raw file).
  parts      one decode step split into Team 5's modules at R rows and cache length L: embedding, attention (g5_decode._attend,
             including the cache torch.cat), the cat alone, MoE, the head, softmax + multinomial (median of 20 synced calls)
  update     rl-loop/train.py's chunked_logprobs (old log-probs, no grad) and backward_objective_v1 + clip + AdamW on one
             group of k rows of prompt + max_new tokens; the RL step does this once per prompt (P groups)
Weights are random (Team 5's own init, seeded): throughput and memory only, never a quality number. Dtype: fp32 weights
(a G5 checkpoint is fp32) under autocast fp16/bf16, as Team5Policy.sample runs under the trainer's autocast; fp32 = none.
Each record is one JSON line in OUT/raw.jsonl; OUT/env.json holds the device, torch version and model shape.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import no_grad  # undotted decorator: pr-guard reads '+@a.b' as an email

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rl-loop"))


def sync(device: str) -> None:
    if device.startswith("cuda"):
        torch.cuda.synchronize()
    elif device == "mps":
        torch.mps.synchronize()


def reset_peak(device: str) -> None:
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()


def peak_gb(device: str):
    return round(torch.cuda.max_memory_allocated() / 2**30, 3) if device.startswith("cuda") else None


def is_oom(e: BaseException) -> bool:
    return isinstance(e, torch.cuda.OutOfMemoryError) or "out of memory" in str(e).lower()


def load_spec(spec_path: Path, arm: Path | None) -> dict:
    """The resolved model dict (a run manifest's config.model, or a file holding it), then the `model:` keys of a Team 5
    arm file laid over it (e.g. configs/arms/t3.yaml for the T3 width, depth and expert size)."""
    raw = json.loads(spec_path.read_text())
    spec = raw.get("config", raw).get("model", raw.get("config", raw))
    if arm is not None:
        import yaml  # noqa: PLC0415
        over = (yaml.safe_load(arm.read_text()) or {}).get("model", {})
        moe = over.pop("moe", None)
        spec = {**spec, **over}
        if moe:
            spec["moe"] = {**spec["moe"], **moe}
    return spec


def build_lm(g5_root: Path, spec: dict, byte_table: Path, device: str, seed: int, checkpoint: Path | None):
    sys.path.insert(0, str(g5_root / "teams" / "05-architecture" / "harness"))
    from week2.model import LanguageModel  # noqa: PLC0415  Team 5's model, unchanged
    t = np.load(byte_table)
    torch.manual_seed(seed)
    lm = LanguageModel(spec, t["bytes"], t["lengths"])
    if checkpoint is not None:
        lm.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=False)["model"], strict=True)
    return lm.to(device).eval()


def amp(device: str, dtype: str):
    if dtype == "fp32":
        return contextlib.nullcontext()
    return torch.autocast(device_type=torch.device(device).type, dtype={"fp16": torch.float16, "bf16": torch.bfloat16}[dtype])


def prompts_for(n: int, lens: list[int], vocab: int, seed: int) -> list[list[int]]:
    g = np.random.default_rng(seed)
    return [g.integers(16, vocab, lens[i % len(lens)]).tolist() for i in range(n)]


# --- decode ------------------------------------------------------------------------------------------------------------

def decode_once(g5_decode, lm, mode, prompts, k, max_new, gen, device, pad_id):
    stop = [-1]  # never stop: every row runs to max_new
    if mode == "one_call":
        return [g5_decode.sample(lm, prompts[0], k, max_new, 1.0, gen, stop, pad_id, device)]
    if mode == "per_prompt":
        return [g5_decode.sample(lm, p, k, max_new, 1.0, gen, stop, pad_id, device) for p in prompts]
    if mode == "batched":
        return g5_decode.sample_many(lm, prompts, k, max_new, 1.0, gen, stop, pad_id, device)
    raise ValueError(mode)


def bench_decode(g5_decode, lm, a, mode, rows, prompts, out, one_prompt):
    if mode == "one_call":  # one call of `rows` rows of one prompt of --prompt-len tokens
        k, n_prompts, ps = rows, 1, [one_prompt]
    else:  # rows / k prompts (the --prompt-lens mix) of k rows each: per_prompt and batched see the same prompts
        k = min(a.k, rows)
        n_prompts = max(1, rows // k)
        ps = prompts[:n_prompts]
    gen = torch.Generator(device=a.device).manual_seed(a.seed)
    rec = {"kind": "decode", "mode": mode, "rows": rows, "k": k, "prompts": n_prompts, "max_new": a.max_new,
           "prompt_lens": sorted({len(p) for p in ps}), "dtype": a.dtype}
    try:
        with amp(a.device, a.dtype):
            decode_once(g5_decode, lm, mode, ps, k, min(a.max_new, 8), gen, a.device, a.pad_id)  # warm-up
            reset_peak(a.device)
            sync(a.device)
            t0 = time.perf_counter()
            decode_once(g5_decode, lm, mode, ps, k, a.max_new, gen, a.device, a.pad_id)
            sync(a.device)
            dt = time.perf_counter() - t0
        rec.update(seconds=round(dt, 4), tokens=rows * a.max_new, tok_per_s=round(rows * a.max_new / dt, 1),
                   ms_per_step=round(1000 * dt / a.max_new / (n_prompts if mode == "per_prompt" else 1), 3),
                   peak_gb=peak_gb(a.device))
    except RuntimeError as e:
        if not is_oom(e):
            raise
        rec.update(oom=True, error=str(e).splitlines()[0][:200])
    out(rec)
    return rec


def bench_positions(g5_decode, lm, a, rows, prompt, out):
    """One call of `rows` rows, the time of every decode step (forward_cached + head + sampling) and of forward_cached
    alone. forward_cached is wrapped with device syncs; the extra syncs cost little because sample() already syncs once
    per token (`alive.any()`)."""
    orig = g5_decode.forward_cached
    marks = []

    def timed(lm_, ids, caches, start):
        sync(a.device)
        t0 = time.perf_counter()
        h = orig(lm_, ids, caches, start)
        sync(a.device)
        marks.append((start, ids.shape[1], t0, time.perf_counter()))
        return h

    g5_decode.forward_cached = timed
    gen = torch.Generator(device=a.device).manual_seed(a.seed)
    try:
        with amp(a.device, a.dtype):
            g5_decode.sample(lm, prompt, rows, a.max_new, 1.0, gen, [-1], a.pad_id, a.device)
    except RuntimeError as e:
        if not is_oom(e):
            raise
        out({"kind": "positions", "rows": rows, "oom": True})
        return
    finally:
        g5_decode.forward_cached = orig
    pre = marks[0]
    steps = []  # step i: from the end of forward i to the end of forward i+1 = head + sampling + bookkeeping + forward
    for (s0, _, b0, e0), (s1, _, b1, e1) in zip(marks, marks[1:]):
        steps.append({"pos": s1, "step_ms": round(1000 * (e1 - e0), 3), "forward_ms": round(1000 * (e1 - b1), 3)})
    out({"kind": "positions", "rows": rows, "prompt_len": len(prompt), "dtype": a.dtype,
         "prefill_ms": round(1000 * (pre[3] - pre[2]), 3), "steps": steps})


# --- one decode step, split into modules -------------------------------------------------------------------------------

def timeit(fn, device, n=20, warm=3):
    for _ in range(warm):
        fn()
    ts = []
    for _ in range(n):
        sync(device)
        t0 = time.perf_counter()
        fn()
        sync(device)
        ts.append(1000 * (time.perf_counter() - t0))
    return round(statistics.median(ts), 4)


@no_grad()
def bench_parts(g5_decode, lm, a, rows, L, out):
    dev, w = a.device, lm.spec["n_embd"]
    b = lm.blocks[0]
    at = b.attn
    rec = {"kind": "parts", "rows": rows, "cache_len": L, "dtype": a.dtype, "n_layer": len(lm.blocks)}
    try:
        with amp(dev, a.dtype):
            cdt = torch.float16 if a.dtype == "fp16" else torch.bfloat16 if a.dtype == "bf16" else torch.float32
            ids = torch.randint(16, lm.spec["vocab_size"], (rows, 1), device=dev)
            x = torch.randn(rows, 1, w, device=dev)
            ck = torch.randn(rows, at.nkv, L, at.d, device=dev, dtype=cdt)
            cv = torch.randn_like(ck)
            knew = torch.randn(rows, at.nkv, 1, at.d, device=dev, dtype=cdt)
            valid = torch.ones(rows, 1, dtype=torch.bool, device=dev)
            h = torch.randn(rows, w, device=dev)
            logits = torch.randn(rows, lm.spec["vocab_size"], device=dev)
            gen = torch.Generator(device=dev).manual_seed(0)
            rec["embedding_ms"] = timeit(lambda: lm.embedding(ids), dev)
            rec["attention_ms"] = timeit(lambda: g5_decode._attend(at, b.n1(x), {"k": ck, "v": cv}, L), dev)
            rec["cache_cat_ms"] = timeit(lambda: (torch.cat((ck, knew), 2), torch.cat((cv, knew), 2)), dev)
            rec["moe_ms"] = timeit(lambda: b.moe(b.n2(x), valid), dev)
            rec["head_ms"] = timeit(lambda: lm.head(h), dev)
            rec["sample_ms"] = timeit(lambda: torch.multinomial(torch.softmax(logits, -1), 1, generator=gen), dev)
        n = len(lm.blocks)
        rec["step_estimate_ms"] = round(rec["embedding_ms"] + n * (rec["attention_ms"] + rec["moe_ms"]) + rec["head_ms"]
                                        + rec["sample_ms"], 3)
        rec["share"] = {key: round(v / rec["step_estimate_ms"], 3) for key, v in
                        (("attention", n * rec["attention_ms"]), ("cache_cat", n * rec["cache_cat_ms"]),
                         ("moe", n * rec["moe_ms"]), ("head", rec["head_ms"]), ("embedding", rec["embedding_ms"]),
                         ("sample", rec["sample_ms"]))}
    except RuntimeError as e:
        if not is_oom(e):
            raise
        rec.update(oom=True)
    out(rec)


# --- the trainer's update on one group ---------------------------------------------------------------------------------

def bench_update(lm, a, micro, out):
    import importlib.util as iu  # noqa: PLC0415  rl-loop/train.py by path: Team 5's harness also has a train.py
    spec_ = iu.spec_from_file_location("g10_rl_train", HERE.parent / "rl-loop" / "train.py")
    train = iu.module_from_spec(spec_)
    spec_.loader.exec_module(train)
    from policy import module_policy  # noqa: PLC0415
    dev = a.device
    pol = module_policy(lm, None, dev)
    pol.amp_dtype = {"fp16": torch.float16, "bf16": torch.bfloat16}.get(a.dtype)
    for n, p in lm.named_parameters():  # rl_job's adapter: everything trains except the routers
        p.requires_grad_(".moe.router." not in n)
    named = [(n, p) for n, p in lm.named_parameters() if p.requires_grad]
    opt = torch.optim.AdamW([p for _, p in named], lr=1e-5, weight_decay=0.0)
    k, plen = a.k, a.prompt_len
    g = torch.Generator().manual_seed(a.seed)
    seq = torch.randint(16, lm.spec["vocab_size"], (k, plen + a.max_new), generator=g).to(dev)
    cmask = torch.ones(k, a.max_new, dtype=torch.bool, device=dev)
    adv = torch.tensor([1.0, -1.0] * (k // 2) + [0.5] * (k % 2), device=dev)
    rec = {"kind": "update", "rows": k, "micro_rows": micro or k, "seq_len": plen + a.max_new, "dtype": a.dtype,
           "trainable": sum(p.numel() for _, p in named)}
    try:
        times = []
        for rep in range(2):  # the first repetition allocates AdamW state; the second is the one reported
            reset_peak(dev)
            sync(dev)
            t0 = time.perf_counter()
            lm.eval()
            with torch.no_grad():
                old = train.chunked_logprobs(pol, seq, plen, micro)
            sync(dev)
            t1 = time.perf_counter()
            lm.train()
            opt.zero_grad()
            train.backward_objective_v1(pol, (seq, cmask, adv, old, None, plen, None), 0.2, int(cmask.sum()), micro)
            sync(dev)
            t2 = time.perf_counter()
            torch.nn.utils.clip_grad_norm_([p for _, p in named], 1.0)
            opt.step()
            sync(dev)
            t3 = time.perf_counter()
            times.append((t1 - t0, t2 - t1, t3 - t2))
        # the RL step runs old log-probs and forward + backward once per prompt (group), and clip + AdamW once
        rec.update(old_logprobs_s=round(times[-1][0], 4), fwd_bwd_s=round(times[-1][1], 4), opt_step_s=round(times[-1][2], 4),
                   first_rep_s=round(sum(times[0]), 4), peak_gb=peak_gb(dev))
    except RuntimeError as e:
        if not is_oom(e):
            raise
        rec.update(oom=True, error=str(e).splitlines()[0][:200])
    finally:
        opt.zero_grad(set_to_none=True)
        del opt
        lm.eval()
        for p in lm.parameters():
            p.grad = None
        reset_peak(dev)
    out(rec)
    return rec


# --- main ----------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--g5-root", type=Path, required=True, help="checkout holding teams/05-architecture/harness")
    ap.add_argument("--spec", type=Path, required=True, help="resolved model spec (a run manifest.json or a {model: ...} file)")
    ap.add_argument("--arm", type=Path, help="Team 5 arm yaml whose model: keys override the spec (e.g. t3.yaml)")
    ap.add_argument("--tier", default="", help="label only (T2, T3)")
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, help="optional: load these weights (else Team 5's random init)")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--dtype", default="fp32", choices=("fp32", "fp16", "bf16"))
    ap.add_argument("--rows", default="1,4,16,64,128,256")
    ap.add_argument("--modes", default="per_prompt,one_call")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--prompt-len", type=int, default=416)
    ap.add_argument("--prompt-lens", default="", help="comma list cycled over prompts (default: --prompt-len for all)")
    ap.add_argument("--max-new", type=int, default=512)
    ap.add_argument("--positions-rows", default="", help="rows for the per-step instrumented call (default: none)")
    ap.add_argument("--parts-rows", default="", help="rows for the module split")
    ap.add_argument("--parts-cache", default="256,1024,1792")
    ap.add_argument("--update-micro", default="", help="micro rows for the update bench, e.g. 8,4,2,1 (empty: skip)")
    ap.add_argument("--max-call-seconds", type=float, default=300.0, help="skip larger rows of a mode after a call this long")
    ap.add_argument("--pad-id", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    import g5_decode  # noqa: PLC0415
    a.out.mkdir(parents=True, exist_ok=True)
    raw = (a.out / "raw.jsonl").open("a")

    def out(rec):
        rec = {"tier": a.tier, "device": a.device, **rec}
        line = json.dumps(rec)
        raw.write(line + "\n")
        raw.flush()
        short = {k: v for k, v in rec.items() if k != "steps"}
        print(json.dumps(short), flush=True)

    spec = load_spec(a.spec, a.arm)
    lm = build_lm(a.g5_root, spec, a.byte_table, a.device, a.seed, a.checkpoint)
    g5_decode.check_supported(lm)
    env = {"torch": torch.__version__, "device": a.device, "dtype": a.dtype, "tier": a.tier, "params": lm.parameter_count(),
           "spec": {x: spec[x] for x in ("n_layer", "n_embd", "n_head", "n_kv_head", "vocab_size", "block_size")},
           "moe": spec["moe"], "argv": sys.argv[1:], "unix": time.time(),
           "gpu": torch.cuda.get_device_name(0) if a.device.startswith("cuda") else None,
           "threads": torch.get_num_threads(), "has_sample_many": hasattr(g5_decode, "sample_many")}
    (a.out / "env.json").write_text(json.dumps(env, indent=1))
    print(json.dumps({"env": env}), flush=True)
    lens = [int(x) for x in a.prompt_lens.split(",") if x] or [a.prompt_len]
    rows_list = [int(x) for x in a.rows.split(",") if x]
    prompts = prompts_for(max(rows_list) // max(1, min(a.k, max(rows_list))) + 1, lens, spec["vocab_size"], a.seed)
    one_prompt = prompts_for(1, [a.prompt_len], spec["vocab_size"], a.seed + 1)[0]
    if max(lens + [a.prompt_len]) + a.max_new > spec["block_size"]:
        raise SystemExit(f"prompt {max(lens)} + max_new {a.max_new} exceeds block_size {spec['block_size']}")
    with torch.no_grad():
        ids = torch.tensor([one_prompt[:40]], device=a.device)
        with amp(a.device, a.dtype):
            out({"kind": "parity", "max_abs_dlogit": g5_decode.parity(lm, ids, 24), "tolerance": 1e-4})
    for mode in [m for m in a.modes.split(",") if m]:
        if mode == "batched" and not hasattr(g5_decode, "sample_many"):
            out({"kind": "decode", "mode": mode, "skipped": "g5_decode has no sample_many"})
            continue
        for rows in rows_list:
            if mode in ("per_prompt", "batched") and rows > a.k and rows % a.k:
                continue
            rec = bench_decode(g5_decode, lm, a, mode, rows, prompts, out, one_prompt)
            if rec.get("oom") or rec.get("seconds", 0) > a.max_call_seconds:
                out({"kind": "decode", "mode": mode, "stopped_after_rows": rows,
                     "reason": "oom" if rec.get("oom") else f"call over {a.max_call_seconds} s"})
                break
    for rows in [int(x) for x in a.positions_rows.split(",") if x]:
        bench_positions(g5_decode, lm, a, rows, one_prompt, out)
    for rows in [int(x) for x in a.parts_rows.split(",") if x]:
        for L in [int(x) for x in a.parts_cache.split(",") if x]:
            bench_parts(g5_decode, lm, a, rows, L, out)
    for micro in [int(x) for x in a.update_micro.split(",") if x]:
        bench_update(lm, a, None if micro >= a.k else micro, out)
    raw.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
