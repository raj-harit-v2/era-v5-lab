#!/usr/bin/env python3
"""Run G9's eval-mini v0 code + Indic part on one GGUF file, with per-item logs.

    python run_code_indic_gguf.py --gguf OLMoE-1B-7B-0924-Q8_0.gguf --format Q8_0 --out runs/ \
        --g9-dir <era-v5-lab main>/teams/09-evaluation/harness_code_indic

G9's definition is read from --g9-dir, not copied: eval_mini_v0_spec.json (tasks, doc_ids, shots) and tasks/milu/
(the MILU task configs). Two parts, both through llama-cpp-python in-process (../eval_mini/llamacpp_lm.py):

  lm   MMLU-Pro 300, GSM8K 100, Belebele hin/tel/tam and MILU Hindi/Telugu/Tamil/Bengali 100 each, 5-shot,
       lm_eval 0.4.13 with the spec's doc_ids and lm_eval's default seeds, as G9's run_lm_eval.py does
  code HumanEval+ 164 and MBPP+ 378 with evalplus 0.3.1: greedy, base (completion) prompt, evalplus's stop strings
       and 768 new tokens, as G9's run_codegen.py; then evalplus executes every answer (Linux only)

Per format it writes:
  <out>/<format>/<task>.samples.jsonl   one line per item: task, doc_id, filter, metric values (no question text)
  <out>/<format>/summary.json           run metadata + one record per task: metric, value (0-1), stderr, n, time
  <out>/<format>/evalplus/              evalplus's raw and sanitized answers and its eval_results.json
A task already in summary.json is skipped, so an interrupted run resumes where it stopped.
"""
from __future__ import annotations

import argparse, datetime, hashlib, json, math, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "eval_mini"))   # llamacpp_lm.py and run_mini_gguf.gpu_name
CODE_TASKS = {"humaneval_plus": "humaneval", "mbpp_plus": "mbpp"}
GATED = {"ai4bharat/MILU"}
# G9's primary metric per task (results/eval_mini_v0_code_indic.json)
METRIC = {"gsm8k": ("exact_match", "flexible-extract")}


def lm_part(args, lm, spec, tasks, summary, save, out):
    import lm_eval
    from lm_eval.tasks import TaskManager
    tm = TaskManager(include_path=str(args.g9_dir / "tasks"))
    for name in tasks:
        t = spec["tasks"][name]
        doc_ids = t["doc_ids"][: args.limit] if args.limit else t["doc_ids"]
        lm.truncated = 0
        t0 = time.perf_counter()
        res = lm_eval.simple_evaluate(
            model=lm, tasks=[name], num_fewshot=t["num_fewshot"], samples={name: doc_ids}, log_samples=True,
            task_manager=tm, apply_chat_template=False, fewshot_as_multiturn=False,
            # lm_eval's default seeds, as G9's run_lm_eval.py; no torch seed: setting it imports torch, which this
            # venv does not have (and which is broken on Kaggle)
            torch_random_seed=None)
        secs = time.perf_counter() - t0
        metric, filt = METRIC.get(name, ("acc", "none"))
        r = res["results"][name]
        rows = [{"task": name, "doc_id": s["doc_id"], "filter": s.get("filter", "none"),
                 **{m: s[m] for m in ("acc", "acc_norm", "exact_match") if m in s}}
                for s in res["samples"][name]]
        write_rows(out / f"{name}.samples.jsonl", rows)
        record = {"task": name, "metric": metric, "filter": filt, "value": r[f"{metric},{filt}"],
                  "stderr": r.get(f"{metric}_stderr,{filt}"), "n_items": len(doc_ids), "num_fewshot": t["num_fewshot"],
                  "dataset_revision": t["dataset_revision"], "items_sha256": t["items_sha256"],
                  "truncated_requests": lm.truncated, "wall_clock_s": round(secs, 1)}
        save(record)
        print(f"{args.format}/{name}: {metric}={record['value']:.4f} n={len(doc_ids)} in {secs:.0f}s, "
              f"{lm.truncated} requests left-truncated to n_ctx={args.n_ctx}", flush=True)


def code_part(args, lm, tasks, save, out):
    from evalplus.codegen import codegen
    from evalplus.evaluate import evaluate
    from evalplus.provider.base import DecoderBase
    from evalplus.provider.utility import extra_eos_for_direct_completion

    class LlamaCppDecoder(DecoderBase):
        """evalplus's HF decoder with the base prompt, on llama-cpp-python: same prompt, stop strings, token limit
        (768), cut at the first stop string and tab replacement. Greedy only."""
        def __init__(self, dataset):
            super().__init__(name=f"{args.format}-gguf", batch_size=1, temperature=0.0)
            # a copy: evalplus 0.3.1's `self.eos += ...` grows its shared EOS list (G9's fix_shared_eos_list)
            self.eos = list(self.eos) + extra_eos_for_direct_completion(dataset)

        def is_direct_completion(self):
            return True

        def codegen(self, prompt, do_sample=True, num_samples=200):
            assert not do_sample and num_samples == 1, "greedy only"
            tokens = lm._tok(prompt, bos=lm.add_bos)
            lm.llm.reset()
            text = lm.llm.create_completion(prompt=tokens, max_tokens=self.max_new_tokens, temperature=0.0, top_k=1,
                                            stop=self.eos)["choices"][0]["text"]
            cut = min([text.index(e) for e in self.eos if e in text], default=len(text))
            return [text[:cut].replace("\t", "    ")]

    if args.limit:
        limit_problems(args.limit)
    for name in tasks:
        dataset = CODE_TASKS[name]
        root = out / "evalplus"; root.mkdir(exist_ok=True)
        path = root / f"{dataset}.jsonl"
        t0 = time.perf_counter()
        codegen(str(path), LlamaCppDecoder(dataset), dataset, greedy=True)   # resumes from the answers in the file
        gen_s = time.perf_counter() - t0
        lm.llm.reset()
        t1 = time.perf_counter()
        results_path = root / f"{dataset}_eval_results.json"
        results_path.unlink(missing_ok=True)   # evalplus would reuse an old result
        evaluate(dataset, samples=str(path), parallel=args.parallel)
        results = json.loads(results_path.read_text())["eval"]
        rows = [{"task": name, "doc_id": task_id, "filter": "none",
                 "base": int(r[0]["base_status"] == "pass"),
                 "plus": int(r[0]["base_status"] == r[0]["plus_status"] == "pass")}
                for task_id, r in sorted(results.items())]
        write_rows(out / f"{name}.samples.jsonl", rows)
        n = len(rows)
        for metric in ("plus", "base"):
            p = sum(r[metric] for r in rows) / n
            save({"task": name if metric == "plus" else name.removesuffix("_plus"), "metric": "pass@1",
                  "filter": metric, "value": p, "stderr": math.sqrt(p * (1 - p) / (n - 1)) if n > 1 else None,
                  "n_items": n, "num_fewshot": 0, "generate_s": round(gen_s, 1),
                  "execute_s": round(time.perf_counter() - t1, 1), "wall_clock_s": round(time.perf_counter() - t0, 1)})
        print(f"{args.format}/{name}: plus pass@1={sum(r['plus'] for r in rows) / n:.4f} "
              f"base pass@1={sum(r['base'] for r in rows) / n:.4f} n={n}, generated in {gen_s:.0f}s", flush=True)


def limit_problems(n):
    """Smoke tests: the first n problems of each dataset. evalplus caches its ground truth under the dataset hash,
    so the hash gets a suffix and the partial ground truth never lands under the full dataset's name."""
    import evalplus.codegen as cg, evalplus.evaluate as ev
    for mod in (cg, ev):
        for fn in ("get_human_eval_plus", "get_mbpp_plus"):
            full = getattr(mod, fn)
            setattr(mod, fn, lambda *a, _full=full, **k: dict(list(_full(*a, **k).items())[:n]))
    for fn in ("get_human_eval_plus_hash", "get_mbpp_plus_hash"):
        full = getattr(ev, fn)
        setattr(ev, fn, lambda *a, _full=full, **k: f"{_full(*a, **k)}-first{n}")


def write_rows(path, rows):
    with open(path, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf", required=True, type=Path)
    ap.add_argument("--format", required=True, help="label for this file, e.g. bf16, Q8_0")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--g9-dir", required=True, type=Path, help="G9's harness_code_indic folder")
    ap.add_argument("--tasks", nargs="+", help="subset of the tasks (default: all of the spec, then code)")
    ap.add_argument("--skip-gated", action="store_true", help="leave out MILU (gated on Hugging Face)")
    ap.add_argument("--limit", type=int, help="first N items per task (smoke tests only)")
    ap.add_argument("--n-ctx", type=int, default=4096, help="OLMoE's trained context; longer prompts are left-truncated")
    ap.add_argument("--n-gpu-layers", type=int, default=-1, help="-1 = all layers on the GPU")
    ap.add_argument("--parallel", type=int, help="evalplus execution workers (default: half the CPUs)")
    ap.add_argument("--model", default="allenai/OLMoE-1B-7B-0924")
    ap.add_argument("--revision", default="6d84c48581ece794365f2b8e9cfb043c68ade9c5")
    args = ap.parse_args()

    spec_path = args.g9_dir / "eval_mini_v0_spec.json"
    spec = json.loads(spec_path.read_text())
    tasks = args.tasks or [*spec["tasks"], *CODE_TASKS]
    if args.skip_gated:
        tasks = [t for t in tasks if spec["tasks"].get(t, {}).get("dataset") not in GATED]
    unknown = set(tasks) - set(spec["tasks"]) - set(CODE_TASKS)
    if unknown:
        sys.exit(f"unknown tasks: {sorted(unknown)}")

    out = args.out / args.format; out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {"run_meta": {}, "records": []}
    done = {r["task"] for r in summary["records"]}
    todo = [t for t in tasks if t not in done]
    for t in set(tasks) - set(todo):
        print(f"{args.format}/{t}: already done, skipped", flush=True)

    def save(record):
        summary["records"] = [r for r in summary["records"]
                              if (r["task"], r["filter"]) != (record["task"], record["filter"])] + [record]
        summary_path.write_text(json.dumps(summary, indent=1))   # after every task: a crash loses one task at most

    import llama_cpp, lm_eval
    from llamacpp_lm import LlamaCppLM
    from run_mini_gguf import gpu_name

    class CountingLM(LlamaCppLM):
        """LlamaCppLM that counts the requests it left-truncates to n_ctx (5-shot Indic prompts can be long)."""
        truncated = 0

        def _score(self, context_tokens, continuation_tokens):
            self.truncated += len(context_tokens) + len(continuation_tokens) > self.n_ctx
            return super()._score(context_tokens, continuation_tokens)

    t0 = time.perf_counter()
    lm = CountingLM(str(args.gguf), n_ctx=args.n_ctx, n_gpu_layers=args.n_gpu_layers)
    versions = {"llama_cpp_python": llama_cpp.__version__, "lm_eval": lm_eval.__version__}
    if any(t in CODE_TASKS for t in todo):
        from importlib.metadata import version
        versions["evalplus"] = version("evalplus")
    summary["run_meta"] = {
        "model": args.model, "model_revision": args.revision, "format": args.format, "gguf": args.gguf.name,
        "gguf_bytes": args.gguf.stat().st_size, "eval_set": f"{spec['name']} {spec['version']} code + Indic",
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(), "limit": args.limit,
        "backend": "llama-cpp-python in-process (logits_all)", **versions, "hardware": gpu_name(),
        "n_ctx": args.n_ctx, "n_gpu_layers": args.n_gpu_layers, "load_s": round(time.perf_counter() - t0, 1),
        "run_date": datetime.date.today().isoformat(),
    }
    lm_part(args, lm, spec, [t for t in todo if t in spec["tasks"]], summary, save, out)
    code_part(args, lm, [t for t in todo if t in CODE_TASKS], save, out)


if __name__ == "__main__":
    main()
