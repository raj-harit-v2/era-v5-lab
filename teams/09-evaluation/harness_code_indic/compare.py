"""Assemble ../results/eval_mini_v0_code_indic.json and ../results/compare_v0_code_indic.md from the runs that exist.

Gate rule (pre-registered in published_scores.json): PASS if |ours - published| <= 2.0 points on the full test set with the
same protocol. A pair without a finished full run is PENDING (or DEFERRED / NOT RUN, by decision); nothing is estimated.

Inputs, all under runs/<model>/ (gitignored, kept locally):
    eval_mini_v0/results.json          lm-eval part of eval-mini        (run_lm_eval.py --samples-file eval_mini_v0_spec.json)
    gate_<task>/results.json           full-set gate runs               (run_lm_eval.py --tasks <task> --tag gate_<task>)
    evalplus/*_eval_results.json       executed code samples            (code_eval_colab.ipynb)

Usage (from this folder):  python compare.py
"""
import hashlib
import json
from datetime import date

from run_lm_eval import HERE, RUNS

RESULTS = HERE.parent / "results"
EVAL_MINI_OUT = "eval_mini_v0_code_indic.json"
COMPARE_OUT = "compare_v0_code_indic.md"
METRIC = {"leaderboard_mmlu_pro": "acc,none", "leaderboard_bbh": "acc_norm,none", "gsm8k": "exact_match,flexible-extract"}
PROTOCOL_CHANGES = [  # every change made after seeing a result goes here, with the reason (pre-registered rule)
]
HARNESS_FIXES = [  # bugs in the tools themselves; every affected result was regenerated after its fix
    "evalplus 0.3.1 HF decoder stacks one extra stop criterion per problem (each wrap captures the previous one). Stale criteria "
    "use earlier prompt lengths and can stop generation after 1 token: HumanEval/32 and /38 kept 1 token in a long run, but 768 "
    "and 101 tokens when generated fresh. `run_codegen.py` removes the leftover patch before each problem, so one criterion is "
    "active, as evalplus intends. Verified: per-problem time flat (447 s → 60 s for 16 problems) and outputs identical to fresh runs. "
    "All code samples were generated after the fix.",
    "lm-eval 0.4.13 computes logits for every position, which OOMs gemma-2-2b (256k vocab) and Llama-3.2-3B on 8 GB. "
    "`run_lm_eval.py` asks the model for only the last 512 positions (`logits_to_keep`) at batch size 1, which lm-eval's own "
    "slicing already supports, and fails loudly if a continuation is longer. Verified on Qwen2.5-1.5B: 269 log-likelihoods "
    "over 45 MMLU-Pro / MILU-Hindi / Belebele-Hindi items are bit-identical with and without it (max |diff| = 0).",
    "This PyTorch build (Windows) has no flash SDPA kernel, and its memory-efficient kernel rejects `enable_gqa`, so grouped-query "
    "models fell back to the math kernel, which builds the full attention matrix (Llama-3.2-3B OOM). `run_lm_eval.py` repeats the "
    "KV heads first (transformers' own path when a mask is present), so the memory-efficient kernel runs. Not bit-identical: on the "
    "same 45 Qwen items, mean |Δ log-likelihood| = 0.053 nats (max 0.23), 44/45 identical choices (the flip was an exact tie in the "
    "reference), identical task accuracies. Qwen's MMLU-Pro gate run predates this change (math kernel); all three eval-mini runs "
    "use the current code (Qwen's was rerun on 26 Oct). gemma-2 uses eager attention and is unaffected. The leaderboard used yet "
    "another kernel (flash, Linux).",
    "evalplus 0.3.1 sets `self.eos = EOS` (the module-level list) and then extends it in place, so in one process MBPP inherited "
    "HumanEval's stop strings (`\\ndef `, `\\nclass `, `\\nimport `, `\\nfrom `), confirmed in every MBPP run log. MBPP answers were cut at "
    "their first or second function (phi-2: 346/378 empty). `run_codegen.py` gives each decoder its own copy. **All MBPP/MBPP+ results "
    "before 26 Oct were invalid and were regenerated** (the invalid files are kept locally, not committed). HumanEval ran first in "
    "each process and was unaffected.",
    "transformers 5 rebuilt deepseek-coder-1.3b-base's tokenizer from its config class (LlamaTokenizerFast) instead of its byte-level "
    "`tokenizer.json`, dropping every space and newline (`def f(x):\\n    return x + 1` → `deff(x):returnx+1`). `run_codegen.py` checks a "
    "round trip and falls back to the repo's own `tokenizer.json`, or stops. The other four tokenizers round-trip correctly "
    "(code, Devanagari, Telugu), so no other result was affected.",
    "Qwen2.5 ships `max_new_tokens: 2048` in `generation_config.json`, which transformers lets override lm-eval's own "
    "generation cap (`max_gen_toks`, 256 for GSM8K). `run_lm_eval.py` now clears it, as standard lm-eval behaviour intends "
    "(found by Mahesh Sv, PR #21). Only Qwen's eval-mini GSM8K was affected (51 → 52 after a fresh rerun; the earlier run is kept "
    "locally). gemma-2-2b and Llama-3.2-3B have no such override, and gate tasks (log-likelihood) and code generation (explicit "
    "`max_new_tokens=768`) never used it.",
]

DEFERRED = {  # (model, task) gate pairs shown as DEFERRED, never FAIL, until their runs exist: MILU-avg needs all 11 languages.
    ("gemma-2-2b", "milu"), ("llama-3.2-3b", "milu"),
}
MILU_LANGS = ["Bengali", "English", "Gujarati", "Hindi", "Kannada", "Malayalam", "Marathi", "Odia", "Punjabi", "Tamil", "Telugu"]
NOT_RUN = {  # optional gate pairs never queued (BBH: MMLU-Pro already covers general ability against the same leaderboard)
    ("qwen2.5-1.5b", "leaderboard_bbh"), ("gemma-2-2b", "leaderboard_bbh"), ("llama-3.2-3b", "leaderboard_bbh"),
}
QWEN_REPORT = "https://arxiv.org/abs/2412.15115"
PR21_GSM8K_FIRST200 = 61.5  # PR #21 results/eval_mini_v0.json: Qwen/Qwen2.5-1.5B, profile mini, gsm8k 5-shot flexible-extract, n=200
POSTHOC = [  # a second model scored by the Qwen report's own setup. NOT part of the gate.
    {"model": "gemma-2-2b", "benchmark": "HumanEval", "dataset": "humaneval", "split": "base", "published": 19.5},
    {"model": "gemma-2-2b", "benchmark": "HumanEval+", "dataset": "humaneval", "split": "plus", "published": 15.9},
    {"model": "gemma-2-2b", "benchmark": "MBPP", "dataset": "mbpp", "split": "base", "published": 42.1},
    {"model": "gemma-2-2b", "benchmark": "MBPP+", "dataset": "mbpp", "split": "plus", "published": 33.6},
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def metric_of(task, row):
    key = METRIC.get(task, "acc,none")
    return row.get(key), row.get(key.replace(",", "_stderr,", 1))


def evalplus_results(model):
    for f in sorted((RUNS / model / "evalplus").glob("*_eval_results.json")):
        yield ("humaneval" if "__humaneval" in f.name else "mbpp"), json.loads(f.read_text(encoding="utf-8"))


def evalplus_scores(model):
    out = {}
    for name, res in evalplus_results(model):
        n = len(res["eval"])
        base = sum(all(r["base_status"] == "pass" for r in v) for v in res["eval"].values()) / n
        plus = sum(all(r["base_status"] == r["plus_status"] == "pass" for r in v) for v in res["eval"].values()) / n
        out[name] = {"n": n, "base": round(100 * base, 2), "plus": round(100 * plus, 2)}
    return out


def count_timeouts(models):
    """Timeouts recorded by evalplus across all executed code samples (a slow executor would show up here)."""
    n = 0
    for m in models:
        for _, res in evalplus_results(m):
            n += sum(r.get("base_status") == "timeout" or r.get("plus_status") == "timeout" for v in res["eval"].values() for r in v)
    return n


def milu_avg(model):
    """MILU-avg: simple mean of the 11 per-language full runs, as (avg, {language: score}); None until all 11 exist."""
    scores = {}
    for lang in MILU_LANGS:
        task = f"milu_{lang}"
        run = load(RUNS / model / f"gate_{task}" / "results.json")
        if not run or run.get("limit") or run.get("samples_file"):
            return None
        value, _ = metric_of(task, run["results"].get(task) or {})
        if value is None:
            return None
        scores[lang] = round(100 * value, 2)
    return round(sum(scores.values()) / len(scores), 2), scores


def ours_for(anchor):
    """Our full-set score for one anchor, or None while the run is missing."""
    model, task = anchor["model"], anchor["task"]
    if task.startswith("evalplus:"):
        ds = task.split(":")[1]
        sc = evalplus_scores(model).get(ds)
        if not sc:
            return None
        return sc["plus"] if anchor["benchmark"].endswith("+") else sc["base"]
    if task == "milu":  # the paper's avg column: simple mean of the 11 per-language runs, not lm-eval's size-weighted group score
        avg = milu_avg(model)
        return None if avg is None else avg[0]
    run = load(RUNS / model / f"gate_{task}" / "results.json")
    if not run or run.get("limit") or run.get("samples_file"):
        return None  # only unrestricted full-set runs count for the gate
    row = run["results"].get(task)
    value, _ = metric_of(task, row or {})
    return None if value is None else round(100 * value, 2)


def main():
    pub = load(HERE / "published_scores.json")
    spec_path = HERE / "eval_mini_v0_spec.json"
    spec = load(spec_path)
    RESULTS.mkdir(exist_ok=True)

    models = {}
    for key, m in pub["models"].items():
        if m.get("role") == "code_reference":  # used only to validate code scoring; not part of eval-mini
            continue
        run = load(RUNS / key / "eval_mini_v0" / "results.json")
        entry = {"hf_id": m["hf_id"], "revision": m["revision"], "status": "done" if run else "pending"}
        if run:
            entry["env"] = run["env"]
            entry["gpu"] = {"before": run["gpu_before"], "after": run["gpu_after"]}
            entry["wall_seconds"] = run["wall_seconds"]
            entry["scores"] = {}
            for task, row in run["results"].items():
                value, stderr = metric_of(task, row)
                if value is not None:
                    entry["scores"][task] = {"metric": METRIC.get(task, "acc,none"), "value": round(100 * value, 2),
                                             "stderr": None if stderr is None else round(100 * stderr, 2),
                                             "n": run["n-samples"].get(task, {}).get("effective")}
        code = evalplus_scores(key)
        if code:
            entry["code"] = code
        models[key] = entry

    eval_mini = {"name": "eval-mini", "version": "v0", "part": "code + Indic (+ MMLU-Pro, GSM8K)", "generated": str(date.today()),
                 "spec_file": "harness_code_indic/eval_mini_v0_spec.json",
                 "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                 "companion": "results/eval_mini_v0.json: general tasks (ARC, HellaSwag, MMLU, GSM8K, TruthfulQA), PR #21",
                 "units": "points (0-100)", "note": spec["scoring_note"], "noise_note": spec.get("noise_note"), "models": models}
    (RESULTS / EVAL_MINI_OUT).write_text(json.dumps(eval_mini, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    rows, counts = [], {"PASS": 0, "FAIL": 0, "PENDING": 0, "DEFERRED": 0, "NOT RUN": 0}
    milu_notes = []
    for a in [a for a in pub["anchors"] if a["use_for_gate"]]:
        ours = ours_for(a)
        diff = ""
        if ours is None:
            verdict = "DEFERRED" if (a["model"], a["task"]) in DEFERRED else "NOT RUN" if (a["model"], a["task"]) in NOT_RUN else "PENDING"
        else:
            d = ours - a["published"]
            verdict, diff = ("PASS" if abs(d) <= 2.0 else "FAIL"), f"{d:+.2f}"
        counts[verdict] += 1
        if a["task"] == "milu" and ours is not None:
            milu_notes.append(f"- MILU-avg {a['model']}, the 11 scores: " + ", ".join(f"{k} {v:.2f}" for k, v in milu_avg(a["model"])[1].items()))
        rows.append(f"| {a['model']} | {a['benchmark']} | {a['published']:.2f} | {'' if ours is None else f'{ours:.2f}'} | {diff} | "
                    f"**{verdict}** | [{a['source']['name']}]({a['source']['url']}) |")

    diag = []
    for p in POSTHOC:
        sc = evalplus_scores(p["model"]).get(p["dataset"])
        ours = None if not sc else sc[p["split"]]
        diag.append(f"| {p['model']} | {p['benchmark']} | {p['published']:.1f} | {'' if ours is None else f'{ours:.2f}'} | "
                    f"{'' if ours is None else f'{ours - p['published']:+.2f}'} |")

    compat = load(RUNS / "qwen2.5-1.5b" / "compat_pr21_gsm8k_first200" / "results.json")
    compat_gsm8k = None if not compat else round(100 * metric_of("gsm8k", compat["results"]["gsm8k"])[0], 1)

    code_models = [k for k in pub["models"]]
    timeouts = count_timeouts(code_models)
    status = ", ".join(f"{v} {k}" for k, v in counts.items() if v)
    md = [f"# Harness agreement with published scores (v0, code + Indic)", "",
          f"Generated {date.today()}. Rule, fixed before any run: **PASS if |ours − published| ≤ 2.0 points** on the full test set, same protocol.",
          f"Companion report for the general tasks: `compare_v0.md` (PR #21).", "",
          f"**Status: {status}.**", "",
          "- MMLU-Pro agrees with the Open LLM Leaderboard's own lm-eval runs for all three models (within 0.31).",
          "- Code scoring agrees with the EvalPlus leaderboard for DeepSeek-Coder-1.3B-base (within 1.2) and phi-2 on 3 of 4.",
          f"- The two FAILs are on the stricter `+` tests, just past the line (−2.41, −2.88). evalplus recorded {timeouts} timeouts "
          "across all executed code, so a slow executor does not explain them. They stand under the pre-registered rule.",
          "- MILU-avg (both rows) is the simple mean of the 11 per-language `gate_milu_<Language>` full runs (79,608 items per model), "
          "computed only when all 11 exist; until then the row is DEFERRED. The rule was fixed before the remaining runs (see the README).",
          *milu_notes,
          "- MILU per-language rows: the five deferred on 25 Oct were run on 29-30 Oct on a second machine (RTX 4060 Ti 16 GB, Windows) with this harness at the pinned revisions; all PASS (largest |Δ| 0.88). As a cross-machine check, gemma-2-2b MILU-en scored 51.16 there against 51.05 in the gate row.",
          "- NOT RUN: BBH (optional; MMLU-Pro already covers general ability against the same leaderboard).", "",
          "| Model | Benchmark | Published | Ours | Δ | Verdict | Source |", "|---|---|---|---|---|---|---|", *rows, "",
          "The `deepseek-coder-1.3b` and `phi-2` rows were registered on 25 Oct, after the first code FAILs and before either model was "
          "run, to check code scoring against a reference with a documented protocol (EvalPlus leaderboard: HumanEval+ v0.1.10, "
          "MBPP+ v0.2.0, greedy, direct completion). Selection criteria: base model, ungated, fits 8 GB in bf16, all four scores published.", "",
          "## Protocol", "",
          "- lm-evaluation-harness 0.4.13, HF backend, bf16, greedy, batch size 1, `max_length` as in each anchor run, no chat template.",
          "- gemma-2-2b uses eager attention (logit soft-capping), as in its anchor run.",
          "- Code: evalplus 0.3.1, greedy, base completion prompt; generated locally, executed on Linux (Colab).", "",
          "## Cross-check: gemma-2-2b scored by the Qwen report's setup (post hoc, not part of the gate)", "",
          "The Qwen2.5 report ([arXiv 2412.15115](" + QWEN_REPORT + "), Table 5) states 0-shot for HumanEval(+) and MBPP(+), as we do, but "
          "names no harness, prompt format or MBPP version. The same table scores gemma-2-2b; our numbers for it agree within 1.2 points:", "",
          "| Model | Benchmark | Qwen report | Ours | Δ |", "|---|---|---|---|---|", *diag, "",
          "## Consistency with PR #21 (general tasks)", "",
          "- **Same weights.** Both reports run Qwen/Qwen2.5-1.5B. We pin `e5dfabbc`, the commit the Open LLM Leaderboard evaluated "
          "(our MMLU-Pro anchor); PR #21 pins `8faed761` (main). `model.safetensors`, the tokenizer and `generation_config.json` are "
          "identical. Only `config.json` (`max_position_embeddings` and `sliding_window`, 32768 → 131072, not reached at these prompt "
          "lengths) and `tokenizer_config.json` (`eos_token`) differ.",
          f"- **Same scores.** On PR #21's eval-mini GSM8K items (the first 200, 5-shot), our harness scores "
          f"{'(not run)' if compat_gsm8k is None else compat_gsm8k} on an RTX 3070 Laptop (Windows) against PR #21's "
          f"{PR21_GSM8K_FIRST200} on an M2 Pro (MPS).",
          "- So our eval-mini GSM8K for Qwen (100 seeded random items) differs from PR #21's because of which items were drawn, not "
          "the harness: one standard error is about 5 points at 100 items.",
          "- **Units differ.** Our `eval_mini_v0_code_indic.json` is in points (0–100); PR #21's `eval_mini_v0.json` stores fractions (0–1).", "",
          "## Harness fixes", "",
          *[f"- {c}" for c in HARNESS_FIXES], "",
          "## Protocol changes after seeing results", "",
          *([f"- {c}" for c in PROTOCOL_CHANGES] or ["- none"]), "",
          "## Limitations", "",
          "- Qwen's code anchors come from a table that names no harness; its one code FAIL (HumanEval+ −2.41) may be protocol, not a bug.",
          "- The leaderboard used a pinned lm-eval fork (commits `d4631ea6` / `121ee91`) on Linux GPUs; we use release 0.4.13 on Windows (RTX 3070 Laptop; MILU per-language rows on an RTX 4060 Ti 16 GB).",
          "- Small models score close to chance (25%) on MILU's Indic languages, so MILU agreement is a weaker check than MMLU-Pro.",
          "- The MILU paper's `avg` column does not state its aggregation. We use the simple mean of the 11 languages, which reproduces "
          "the paper's 31.43 / 32.85; lm-eval's size-weighted mean would give 33.51 / 34.87. Per-language rows are still the primary check.", ""]
    (RESULTS / COMPARE_OUT).write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"{EVAL_MINI_OUT}: {sum(v['status'] == 'done' for v in models.values())}/{len(models)} models done | gate: {status} | timeouts {timeouts}")


if __name__ == "__main__":
    main()
