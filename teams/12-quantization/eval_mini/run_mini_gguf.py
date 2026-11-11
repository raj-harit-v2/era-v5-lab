#!/usr/bin/env python3
"""Run G9's eval_mini profile on one GGUF file, with per-item logs, in G9's eval_mini_v0 record format.

    python run_mini_gguf.py --gguf OLMoE-1B-7B-0924-Q8_0.gguf --format Q8_0 --out runs/ \
        --g9-harness <era-v5-lab main>/teams/09-evaluation/harness/run_eval_mini.py

The task set, shot counts, limits, seed and record format are imported from G9's run_eval_mini.py, not copied,
so a run here is like for like with G9's baseline. Per task it writes:
  <out>/<format>/<task>_<k>shot.samples.jsonl   one line per item: task, doc_id, filter, metric values (no item text)
  <out>/<format>/summary.json                   run metadata + one record per (task, metric, filter)
A task whose records are already in summary.json is skipped, so an interrupted run resumes where it stopped.
"""
from __future__ import annotations

import argparse, datetime, hashlib, importlib.util, json, platform, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load_g9(path: Path):
    spec = importlib.util.spec_from_file_location("run_eval_mini", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_eval_mini"] = mod   # its dataclasses look themselves up in sys.modules while being defined
    spec.loader.exec_module(mod)
    return mod


def gpu_name() -> str:
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                              capture_output=True, text=True, check=True).stdout.strip().replace("\n", " + ")
    except (OSError, subprocess.CalledProcessError):
        if platform.system() == "Darwin":
            sc = lambda k: subprocess.run(["sysctl", "-n", k], capture_output=True, text=True).stdout.strip()
            return f"{sc('machdep.cpu.brand_string')} {int(sc('hw.memsize')) // 2**30}GB (Metal)"
        return platform.processor() or platform.machine()


def sample_rows(results: dict, metric_names: set[str]) -> list[dict]:
    """Flatten lm_eval's per-sample logs (one list per leaf task) into slim rows keyed by (task, filter, doc_id);
    GSM8K logs each item once per answer filter (strict-match, flexible-extract).

    Eval firewall (Team 9): only task, doc_id, filter and metric values are kept. Never write an item's target or
    response text; combine.py refuses any row that has them."""
    rows = []
    for task, samples in (results.get("samples") or {}).items():
        for s in samples:
            rows.append({"task": task, "doc_id": s["doc_id"], "filter": s.get("filter", "none"),
                         **{m: s[m] for m in metric_names if m in s}})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf", required=True, type=Path)
    ap.add_argument("--format", required=True, help="label for this file, e.g. bf16, Q8_0")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--g9-harness", required=True, type=Path, help="path to G9's run_eval_mini.py")
    ap.add_argument("--profile", default="mini")
    ap.add_argument("--tasks", nargs="+", help="subset of the profile's tasks")
    ap.add_argument("--limit", type=int, help="override every task's limit (smoke tests only)")
    ap.add_argument("--n-ctx", type=int, default=2048)
    ap.add_argument("--n-gpu-layers", type=int, default=-1, help="-1 = all layers on the GPU")
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

    import llama_cpp, lm_eval
    from llamacpp_lm import LlamaCppLM
    t0 = time.perf_counter()
    lm = LlamaCppLM(str(args.gguf), n_ctx=args.n_ctx, n_gpu_layers=args.n_gpu_layers, seed=g9.DEFAULT_SEED)
    load_s = time.perf_counter() - t0
    summary["run_meta"] = {
        "model": args.model, "model_revision": args.revision, "format": args.format,
        "gguf": args.gguf.name, "gguf_bytes": args.gguf.stat().st_size, "profile": args.profile,
        "backend": f"llama-cpp-python {llama_cpp.__version__} (in-process, logits_all)",
        "lm_eval": lm_eval.__version__, "hardware": gpu_name(), "n_ctx": args.n_ctx,
        "n_gpu_layers": args.n_gpu_layers, "seed": g9.DEFAULT_SEED, "load_s": round(load_s, 1),
        "g9_harness_sha256": hashlib.sha256(args.g9_harness.read_bytes()).hexdigest()[:16],
    }
    for name in tasks:
        if name in done:
            print(f"{args.format}/{name}: already done, skipped", flush=True); continue
        spec, run = g9.TASKS[name], profile[name]
        limit = args.limit if args.limit is not None else run.limit
        t = time.perf_counter()
        results = lm_eval.simple_evaluate(
            model=lm, tasks=[name], num_fewshot=run.num_fewshot or None, limit=limit, log_samples=True,
            random_seed=g9.DEFAULT_SEED, numpy_random_seed=g9.DEFAULT_SEED, fewshot_random_seed=g9.DEFAULT_SEED,
            # no torch seed: this backend does not use torch, and setting it imports torch, which is broken on
            # Kaggle (libtorch_cuda: undefined symbol ncclCommShrink). G9's other three seeds are unchanged.
            torch_random_seed=None)
        secs = time.perf_counter() - t
        context = {"model": args.model, "model_revision": args.revision, "dtype": args.format,
                   "profile": args.profile, "limit": limit, "seed": g9.DEFAULT_SEED,
                   "harness_version": lm_eval.__version__, "run_date": datetime.date.today().isoformat(),
                   "device": "llama-cpp-python", "hardware": summary["run_meta"]["hardware"], "batch_size": 1,
                   "wall_clock_s": round(secs, 1)}
        records = g9.extract_records(results, spec, run.num_fewshot, context)
        metric_names = {r["metric"] for r in records}
        rows = sample_rows(results, metric_names)
        with open(out / f"{name}_{run.num_fewshot}shot.samples.jsonl", "w") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary["records"] = [r for r in summary["records"] if r["task"] != name] + records
        summary_path.write_text(json.dumps(summary, indent=1))   # after every task: a crash loses one task at most
        prim = next((r for r in records if r["primary"]), records[0])
        print(f"{args.format}/{name}: {prim['metric']}={prim['value']:.4f} +/- {prim['stderr'] or 0:.4f} "
              f"n={prim['n_items']} in {secs:.0f}s ({secs / max(prim['n_items'], 1):.2f}s/item), "
              f"{len(rows)} per-item rows", flush=True)


if __name__ == "__main__":
    main()
