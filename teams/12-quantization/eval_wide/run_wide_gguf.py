#!/usr/bin/env python3
"""Widened benchmark pass on one GGUF file: full splits (or a per-task cap) so quantization drift is visible.

    python run_wide_gguf.py --gguf sarvam-1-Q4_K_M.gguf --format Q4_K_M --out runs/ \
        --g9-dir <era-v5-lab main>/teams/09-evaluation/harness_code_indic \
        --model sarvamai/sarvam-1 --revision e9607337286ddf496d4a2562b194e489dcf3feea

Why: the 200 to 570 item tasks of eval_mini cannot see a 2-point drop (about 1,100 to 2,900 items needed at 80%
power, p < 0.01; see ../docs/wide_benchmark_scope.md). Same backend as ../eval_mini (llama-cpp-python in-process,
shifted-logprob safe) and the same per-item record style, so ../eval_mini/paired.py statistics apply unchanged.

Tasks and shots are WIDE below. `--cap N` limits every task to its first N items (MMLU: N per subject), for timing
runs and for fitting a compute budget; the cap is written to summary.json. Without it every task runs in full.
A task already in summary.json is skipped, so an interrupted run resumes.

Per task it writes <out>/<format>/<task>.samples.jsonl (one row per item: task, doc_id, filter, metric values; no
item text, Team 9's firewall) and updates <out>/<format>/summary.json after every task.
"""
from __future__ import annotations

import argparse, datetime, hashlib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "eval_mini"))   # llamacpp_lm.py, run_mini_gguf.gpu_name
sys.path.insert(0, str(HERE))                        # the notebook writes all files into one folder

# task -> (shots, primary metric, needs G9's task folder (MILU), gated)
WIDE = {
    "mmlu": (0, "acc", False, False),                  # 57 subjects, 14,042 items
    "arc_challenge": (0, "acc_norm", False, False),    # 1,172 items
    "milu_Kannada": (5, "acc", True, True),            # G9's shot count for MILU
    "milu_Hindi": (5, "acc", True, True),
    "milu_Telugu": (5, "acc", True, True),
    "milu_Tamil": (5, "acc", True, True),
    "milu_Bengali": (5, "acc", True, True),
    # Belebele (reading comprehension, 900 items per language, not gated; 5-shot as G9's eval-mini v0). Added 22 Nov:
    # sarvam-1 bf16 scored 28 to 30% on MILU kn/hi/te (2,500 items each), too close to the 25% chance line to show
    # drift; Belebele's answer is in the passage, so an Indic-trained model should sit well above chance.
    "belebele_kan_Knda": (5, "acc", False, False),
    "belebele_hin_Deva": (5, "acc", False, False),
    "belebele_tel_Telu": (5, "acc", False, False),
    "belebele_tam_Taml": (5, "acc", False, False),
    "belebele_ben_Beng": (5, "acc", False, False),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf", required=True, type=Path)
    ap.add_argument("--format", required=True, help="label for this file, e.g. bf16, Q4_K_M")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--g9-dir", required=True, type=Path, help="G9's harness_code_indic folder (MILU task configs)")
    ap.add_argument("--tasks", nargs="+", choices=sorted(WIDE), help="subset (default: all)")
    ap.add_argument("--skip-gated", action="store_true", help="leave out MILU (needs HF_TOKEN)")
    ap.add_argument("--cap", type=int, help="first N items per task (MMLU: per subject); default full split")
    ap.add_argument("--n-ctx", type=int, default=4096)
    ap.add_argument("--n-gpu-layers", type=int, default=-1, help="-1 = all layers on the GPU")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model", required=True)
    ap.add_argument("--revision", required=True)
    args = ap.parse_args()

    tasks = args.tasks or list(WIDE)
    if args.skip_gated:
        tasks = [t for t in tasks if not WIDE[t][3]]
    out = args.out / args.format
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {"run_meta": {}, "records": []}
    done = {r["task"] for r in summary["records"]}
    todo = [t for t in tasks if t not in done]
    for t in set(tasks) - set(todo):
        print(f"{args.format}/{t}: already done, skipped", flush=True)
    if not todo:
        return

    import llama_cpp, lm_eval
    from lm_eval.tasks import TaskManager
    from llamacpp_lm import LlamaCppLM
    from run_mini_gguf import gpu_name

    class CountingLM(LlamaCppLM):
        """Counts requests left-truncated to n_ctx (5-shot Indic prompts can be long)."""
        truncated = 0

        def _score(self, context_tokens, continuation_tokens):
            self.truncated += len(context_tokens) + len(continuation_tokens) > self.n_ctx
            return super()._score(context_tokens, continuation_tokens)

    tm = TaskManager(include_path=str(args.g9_dir / "tasks"))
    t0 = time.perf_counter()
    lm = CountingLM(str(args.gguf), n_ctx=args.n_ctx, n_gpu_layers=args.n_gpu_layers, seed=args.seed)
    summary["run_meta"] = {
        "model": args.model, "model_revision": args.revision, "format": args.format, "gguf": args.gguf.name,
        "gguf_bytes": args.gguf.stat().st_size, "eval_set": "G12 wide pass", "cap": args.cap,
        "backend": f"llama-cpp-python {llama_cpp.__version__} (in-process, logits_all)",
        "lm_eval": lm_eval.__version__, "hardware": gpu_name(), "n_ctx": args.n_ctx,
        "n_gpu_layers": args.n_gpu_layers, "seed": args.seed, "load_s": round(time.perf_counter() - t0, 1),
        "run_date": datetime.date.today().isoformat(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
    }

    for name in todo:
        shots, metric, _, _ = WIDE[name]
        lm.truncated = 0
        t = time.perf_counter()
        res = lm_eval.simple_evaluate(
            model=lm, tasks=[name], num_fewshot=shots or None, limit=args.cap, log_samples=True, task_manager=tm,
            apply_chat_template=False, fewshot_as_multiturn=False, random_seed=args.seed,
            numpy_random_seed=args.seed, fewshot_random_seed=args.seed,
            torch_random_seed=None)   # setting the torch seed imports torch, broken on Kaggle
        secs = time.perf_counter() - t
        # one file per task; doc_id is made unique across MMLU's 57 subjects as "<subject>/<doc_id>"
        rows = [{"task": name, "doc_id": f"{leaf}/{s['doc_id']}", "filter": s.get("filter", "none"),
                 metric: s[metric]}
                for leaf, samples in res["samples"].items() for s in samples if metric in s]
        with open(out / f"{name}.samples.jsonl", "w") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        n = len(rows)
        value = sum(r[metric] for r in rows) / n
        record = {"task": name, "metric": metric, "filter": "none", "value": value, "n_items": n,
                  "stderr": res["results"][name].get(f"{metric}_stderr,none"), "num_fewshot": shots,
                  "cap": args.cap, "truncated_requests": lm.truncated, "wall_clock_s": round(secs, 1)}
        summary["records"] = [r for r in summary["records"] if r["task"] != name] + [record]
        summary_path.write_text(json.dumps(summary, indent=1))   # after every task: a crash loses one task at most
        print(f"{args.format}/{name}: {metric}={value:.4f} n={n} in {secs:.0f}s ({secs / n:.2f}s/item), "
              f"{lm.truncated} requests left-truncated to n_ctx={args.n_ctx}", flush=True)


if __name__ == "__main__":
    main()
