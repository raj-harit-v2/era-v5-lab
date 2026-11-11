#!/usr/bin/env python3
"""Run G9's eval_mini profile on one model folder served by vLLM, with per-item logs, in G9's record format.

    python run_mini_vllm.py --model-dir <dir> --format W4A16 --out runs_vllm/ \
        --g9-harness <era-v5-lab main>/teams/09-evaluation/harness/run_eval_mini.py [--tp 2] [--limit 5]

The same as ../eval_mini/run_mini_gguf.py, with lm_eval's own vLLM backend in place of llama-cpp-python: the task
set, shots, limits, seed and record format come from G9's run_eval_mini.py, and the output layout is the same
(<out>/<format>/summary.json and <task>_<k>shot.samples.jsonl), so ../eval_mini/paired.py compares formats item by
item. vLLM returns the log-probabilities of the prompt tokens (`prompt_logprobs`), which multiple choice needs.

Before scoring it checks the backend on one known case: log p(" Paris" | "The capital of France is") is about
-0.49 for OLMoE in bf16 and must be the greedy token. A broken load (flat or shifted log-probabilities) fails here.
It also times one greedy generation of 256 tokens (single stream) for gen_tok_s.

Compare a vLLM score only with the vLLM bf16 score from this same script and settings (G12 rule): the llama.cpp
rows in runs.csv use another runtime. On a GPU without bf16 (T4, P100) vLLM computes in fp16 for every format;
the dtype used is recorded.
"""
from __future__ import annotations

import argparse, datetime, hashlib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "eval_mini"))
from run_mini_gguf import gpu_name, load_g9, sample_rows  # noqa: E402

PROBE = ("The capital of France is", " Paris")


def pick_dtype(requested: str) -> str:
    if requested != "auto":
        return requested
    import torch
    return "bfloat16" if torch.cuda.is_available() and torch.cuda.get_device_capability(0) >= (8, 0) else "float16"


def probe(lm) -> tuple[float, bool]:
    from lm_eval.api.instance import Instance
    req = Instance(request_type="loglikelihood", doc={}, arguments=PROBE, idx=0)
    (logprob, greedy), = lm.loglikelihood([req])
    return logprob, greedy


def gen_speed(lm, n_tokens: int = 256) -> float:
    from vllm import SamplingParams
    params = SamplingParams(max_tokens=n_tokens, temperature=0.0, ignore_eos=True)
    lm.model.generate([PROBE[0]], params, use_tqdm=False)          # warm-up
    t = time.perf_counter()
    out = lm.model.generate([PROBE[0]], params, use_tqdm=False)
    return len(out[0].outputs[0].token_ids) / (time.perf_counter() - t)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", required=True, type=Path)
    ap.add_argument("--format", required=True, help="label, e.g. bf16 or W4A16")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--g9-harness", required=True, type=Path, help="path to G9's run_eval_mini.py")
    ap.add_argument("--profile", default="mini")
    ap.add_argument("--tasks", nargs="+", help="subset of the profile's tasks")
    ap.add_argument("--limit", type=int, help="override every task's limit (smoke tests only)")
    ap.add_argument("--dtype", default="auto", help="auto = bfloat16 on compute capability 8.0+, else float16")
    ap.add_argument("--tp", type=int, default=1, help="tensor parallel size (2 on Kaggle T4 x2)")
    ap.add_argument("--max-model-len", type=int, default=2048, help="same context as the GGUF runs (n_ctx 2048)")
    ap.add_argument("--gpu-mem", type=float, default=0.85)
    ap.add_argument("--model", default="allenai/OLMoE-1B-7B-0924")
    ap.add_argument("--revision", default="6d84c48581ece794365f2b8e9cfb043c68ade9c5")
    args = ap.parse_args()

    g9 = load_g9(args.g9_harness)
    profile = g9.PROFILES[args.profile]
    tasks = args.tasks or list(profile)
    out = args.out / args.format; out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {
        "schema_version": g9.SCHEMA_VERSION, "run_meta": {}, "records": []}
    done = {r["task"] for r in summary["records"]}

    import lm_eval, vllm
    from lm_eval.models.vllm_causallms import VLLM
    dtype = pick_dtype(args.dtype)
    t0 = time.perf_counter()
    lm = VLLM(pretrained=str(args.model_dir), dtype=dtype, tensor_parallel_size=args.tp, batch_size="auto",
              max_model_len=args.max_model_len, gpu_memory_utilization=args.gpu_mem, seed=g9.DEFAULT_SEED)
    load_s = time.perf_counter() - t0

    logprob, greedy = probe(lm)
    print(f"{args.format}: log p{PROBE} = {logprob:.3f}, greedy={greedy}", flush=True)
    if not greedy or logprob < -2.0:
        sys.exit(f"{args.format}: backend check failed (expected about -0.49 and greedy); not scoring")
    tok_s = gen_speed(lm)
    print(f"{args.format}: {tok_s:.1f} tok/s (one stream, 256 tokens)", flush=True)

    meta_file = args.model_dir / "quantize_meta.json"
    summary["run_meta"] = {
        "model": args.model, "model_revision": args.revision, "format": args.format,
        "model_dir": args.model_dir.name, "profile": args.profile,
        "backend": f"vLLM {vllm.__version__} via lm_eval VLLM (prompt_logprobs)", "dtype": dtype,
        "tensor_parallel": args.tp, "max_model_len": args.max_model_len, "lm_eval": lm_eval.__version__,
        "hardware": gpu_name(), "seed": g9.DEFAULT_SEED, "load_s": round(load_s, 1),
        "probe_logprob": round(logprob, 4), "gen_tok_s": round(tok_s, 1),
        "quantize_meta": json.loads(meta_file.read_text()) if meta_file.exists() else None,
        "g9_harness_sha256": hashlib.sha256(args.g9_harness.read_bytes()).hexdigest()[:16],
    }
    summary_path.write_text(json.dumps(summary, indent=1))
    for name in tasks:
        if name in done:
            print(f"{args.format}/{name}: already done, skipped", flush=True); continue
        spec, run = g9.TASKS[name], profile[name]
        limit = args.limit if args.limit is not None else run.limit
        t = time.perf_counter()
        results = lm_eval.simple_evaluate(
            model=lm, tasks=[name], num_fewshot=run.num_fewshot or None, limit=limit, log_samples=True,
            random_seed=g9.DEFAULT_SEED, numpy_random_seed=g9.DEFAULT_SEED, torch_random_seed=g9.DEFAULT_SEED,
            fewshot_random_seed=g9.DEFAULT_SEED)
        secs = time.perf_counter() - t
        context = {"model": args.model, "model_revision": args.revision, "dtype": f"{args.format} ({dtype})",
                   "profile": args.profile, "limit": limit, "seed": g9.DEFAULT_SEED,
                   "harness_version": lm_eval.__version__, "run_date": datetime.date.today().isoformat(),
                   "device": "vllm", "hardware": summary["run_meta"]["hardware"], "batch_size": "auto",
                   "wall_clock_s": round(secs, 1)}
        records = g9.extract_records(results, spec, run.num_fewshot, context)
        # Eval firewall: keep only task, doc_id, filter and metric values; never write target or response text.
        rows = [{k: v for k, v in r.items() if k not in ("target", "response")}
                for r in sample_rows(results, {r["metric"] for r in records})]
        with open(out / f"{name}_{run.num_fewshot}shot.samples.jsonl", "w") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary["records"] = [r for r in summary["records"] if r["task"] != name] + records
        summary_path.write_text(json.dumps(summary, indent=1))   # after every task: a crash loses one task at most
        prim = next((r for r in records if r["primary"]), records[0])
        print(f"{args.format}/{name}: {prim['metric']}={prim['value']:.4f} +/- {prim['stderr'] or 0:.4f} "
              f"n={prim['n_items']} in {secs:.0f}s, {len(rows)} per-item rows", flush=True)


if __name__ == "__main__":
    main()
