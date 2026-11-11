# Harness agreement with published scores (v0, code + Indic)

Generated 2026-11-10. Rule, fixed before any run: **PASS if |ours − published| ≤ 2.0 points** on the full test set, same protocol.
Companion report for the general tasks: `compare_v0.md` (PR #21).

**Status: 21 PASS, 2 FAIL, 3 NOT RUN.**

- MMLU-Pro agrees with the Open LLM Leaderboard's own lm-eval runs for all three models (within 0.31).
- Code scoring agrees with the EvalPlus leaderboard for DeepSeek-Coder-1.3B-base (within 1.2) and phi-2 on 3 of 4.
- The two FAILs are on the stricter `+` tests, just past the line (−2.41, −2.88). evalplus recorded 0 timeouts across all executed code, so a slow executor does not explain them. They stand under the pre-registered rule and are tracked as known failures: qwen2.5-1.5b HumanEval+ ([#334](https://github.com/theschoolofai/era-v5-lab/issues/334)), phi-2 MBPP+ ([#335](https://github.com/theschoolofai/era-v5-lab/issues/335)).
- MILU-avg (both rows) is the simple mean of the 11 per-language `gate_milu_<Language>` full runs (79,608 items per model), computed only when all 11 exist; until then the row is DEFERRED. The rule was fixed before the remaining runs (see the README).
- MILU-avg gemma-2-2b, the 11 scores: Bengali 29.53, English 51.05, Gujarati 30.00, Hindi 32.72, Kannada 29.37, Malayalam 28.67, Marathi 30.99, Odia 24.46, Punjabi 30.67, Tamil 29.76, Telugu 29.34
- MILU-avg llama-3.2-3b, the 11 scores: Bengali 32.41, English 50.76, Gujarati 31.33, Hindi 35.10, Kannada 31.17, Malayalam 29.18, Marathi 33.46, Odia 28.35, Punjabi 31.74, Tamil 31.59, Telugu 29.45
- MILU-avg llama-3.2-3b: Bengali, Kannada, Malayalam, Odia, Punjabi, Tamil ran with `--full-logits`. Each has answer options longer than the 512 positions the default path keeps (up to 1,112 tokens), so the guard stops the default run. Same log-likelihoods either way: on milu_Marathi (200 items, both paths) all 800 option log-likelihoods were identical.
- MILU per-language rows: the five deferred on 25 Oct were run on 29-30 Oct on a second machine (RTX 4060 Ti 16 GB, Windows) with this harness at the pinned revisions; all PASS (largest |Δ| 0.88). As a cross-machine check, gemma-2-2b MILU-en scored 51.16 there against 51.05 in the gate row.
- NOT RUN: BBH (optional; MMLU-Pro already covers general ability against the same leaderboard).

| Model | Benchmark | Published | Ours | Δ | Verdict | Source |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b | MMLU-Pro | 28.55 | 28.49 | -0.06 | **PASS** | [Open LLM Leaderboard v2, per-run results file](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/Qwen/Qwen2.5-1.5B/results_2024-10-24T00-00-00.000000.json) |
| qwen2.5-1.5b | BBH | 40.46 |  |  | **NOT RUN** | [Open LLM Leaderboard v2, per-run results file](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/Qwen/Qwen2.5-1.5B/results_2024-10-24T00-00-00.000000.json) |
| gemma-2-2b | MMLU-Pro | 21.80 | 21.56 | -0.24 | **PASS** | [Open LLM Leaderboard v2, per-run results file](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/google/gemma-2-2b/results_2024-07-29T16-38-17.664954.json) |
| gemma-2-2b | BBH | 36.21 |  |  | **NOT RUN** | [Open LLM Leaderboard v2, per-run results file](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/google/gemma-2-2b/results_2024-07-29T16-38-17.664954.json) |
| llama-3.2-3b | MMLU-Pro | 24.92 | 24.61 | -0.31 | **PASS** | [Open LLM Leaderboard v2, per-run results file](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/meta-llama/Llama-3.2-3B/results_2024-09-23T09-55-05.332092.json) |
| llama-3.2-3b | BBH | 39.25 |  |  | **NOT RUN** | [Open LLM Leaderboard v2, per-run results file](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/meta-llama/Llama-3.2-3B/results_2024-09-23T09-55-05.332092.json) |
| gemma-2-2b | MILU-en | 50.86 | 51.05 | +0.19 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| gemma-2-2b | MILU-hi | 32.32 | 32.72 | +0.40 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| gemma-2-2b | MILU-te | 28.46 | 29.34 | +0.88 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| gemma-2-2b | MILU-avg | 31.43 | 31.51 | +0.08 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| llama-3.2-3b | MILU-en | 50.25 | 50.76 | +0.51 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| llama-3.2-3b | MILU-hi | 34.63 | 35.10 | +0.47 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| llama-3.2-3b | MILU-te | 29.75 | 29.45 | -0.30 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| llama-3.2-3b | MILU-avg | 32.85 | 33.14 | +0.29 | **PASS** | [MILU paper, Table 3](https://arxiv.org/abs/2411.02538) |
| qwen2.5-1.5b | HumanEval | 37.20 | 35.37 | -1.83 | **PASS** | [Qwen2.5 blog, base-model table](https://qwenlm.github.io/blog/qwen2.5-llm/) |
| qwen2.5-1.5b | HumanEval+ | 32.90 | 30.49 | -2.41 | **FAIL** (known failure, [#334](https://github.com/theschoolofai/era-v5-lab/issues/334)) | [Qwen2.5 blog, base-model table](https://qwenlm.github.io/blog/qwen2.5-llm/) |
| qwen2.5-1.5b | MBPP | 60.20 | 59.52 | -0.68 | **PASS** | [Qwen2.5 blog, base-model table](https://qwenlm.github.io/blog/qwen2.5-llm/) |
| qwen2.5-1.5b | MBPP+ | 49.60 | 48.15 | -1.45 | **PASS** | [Qwen2.5 blog, base-model table](https://qwenlm.github.io/blog/qwen2.5-llm/) |
| deepseek-coder-1.3b | HumanEval | 28.70 | 29.88 | +1.18 | **PASS** | [EvalPlus leaderboard (DeepSeek-Coder-1.3B-base)](https://evalplus.github.io/leaderboard.html) |
| deepseek-coder-1.3b | HumanEval+ | 25.60 | 25.61 | +0.01 | **PASS** | [EvalPlus leaderboard (DeepSeek-Coder-1.3B-base)](https://evalplus.github.io/leaderboard.html) |
| deepseek-coder-1.3b | MBPP | 56.90 | 57.41 | +0.51 | **PASS** | [EvalPlus leaderboard (DeepSeek-Coder-1.3B-base)](https://evalplus.github.io/leaderboard.html) |
| deepseek-coder-1.3b | MBPP+ | 47.90 | 47.88 | -0.02 | **PASS** | [EvalPlus leaderboard (DeepSeek-Coder-1.3B-base)](https://evalplus.github.io/leaderboard.html) |
| phi-2 | HumanEval | 49.40 | 48.17 | -1.23 | **PASS** | [EvalPlus leaderboard (phi-2-2.7B)](https://evalplus.github.io/leaderboard.html) |
| phi-2 | HumanEval+ | 45.10 | 43.90 | -1.20 | **PASS** | [EvalPlus leaderboard (phi-2-2.7B)](https://evalplus.github.io/leaderboard.html) |
| phi-2 | MBPP | 64.00 | 62.43 | -1.57 | **PASS** | [EvalPlus leaderboard (phi-2-2.7B)](https://evalplus.github.io/leaderboard.html) |
| phi-2 | MBPP+ | 54.20 | 51.32 | -2.88 | **FAIL** (known failure, [#335](https://github.com/theschoolofai/era-v5-lab/issues/335)) | [EvalPlus leaderboard (phi-2-2.7B)](https://evalplus.github.io/leaderboard.html) |

The `deepseek-coder-1.3b` and `phi-2` rows were registered on 25 Oct, after the first code FAILs and before either model was run, to check code scoring against a reference with a documented protocol (EvalPlus leaderboard: HumanEval+ v0.1.10, MBPP+ v0.2.0, greedy, direct completion). Selection criteria: base model, ungated, fits 8 GB in bf16, all four scores published.

## Protocol

- lm-evaluation-harness 0.4.13, HF backend, bf16, greedy, batch size 1, `max_length` as in each anchor run, no chat template.
- gemma-2-2b uses eager attention (logit soft-capping), as in its anchor run.
- Code: evalplus 0.3.1, greedy, base completion prompt; generated locally, executed on Linux (Colab).

## Cross-check: gemma-2-2b scored by the Qwen report's setup (post hoc, not part of the gate)

The Qwen2.5 report ([arXiv 2412.15115](https://arxiv.org/abs/2412.15115), Table 5) states 0-shot for HumanEval(+) and MBPP(+), as we do, but names no harness, prompt format or MBPP version. The same table scores gemma-2-2b; our numbers for it agree within 1.2 points:

| Model | Benchmark | Qwen report | Ours | Δ |
|---|---|---|---|---|
| gemma-2-2b | HumanEval | 19.5 | 20.12 | +0.62 |
| gemma-2-2b | HumanEval+ | 15.9 | 17.07 | +1.17 |
| gemma-2-2b | MBPP | 42.1 | 41.80 | -0.30 |
| gemma-2-2b | MBPP+ | 33.6 | 33.33 | -0.27 |

## Consistency with PR #21 (general tasks)

- **Same weights.** Both reports run Qwen/Qwen2.5-1.5B. We pin `e5dfabbc`, the commit the Open LLM Leaderboard evaluated (our MMLU-Pro anchor); PR #21 pins `8faed761` (main). `model.safetensors`, the tokenizer and `generation_config.json` are identical. Only `config.json` (`max_position_embeddings` and `sliding_window`, 32768 → 131072, not reached at these prompt lengths) and `tokenizer_config.json` (`eos_token`) differ.
- **Same scores.** On PR #21's eval-mini GSM8K items (the first 200, 5-shot), our harness scores 61.0 on an RTX 3070 Laptop (Windows) against PR #21's 61.5 on an M2 Pro (MPS).
- So our eval-mini GSM8K for Qwen (100 seeded random items) differs from PR #21's because of which items were drawn, not the harness: one standard error is about 5 points at 100 items.
- **Units differ.** Our `eval_mini_v0_code_indic.json` is in points (0–100); PR #21's `eval_mini_v0.json` stores fractions (0–1).

## Harness fixes

- evalplus 0.3.1 HF decoder stacks one extra stop criterion per problem (each wrap captures the previous one). Stale criteria use earlier prompt lengths and can stop generation after 1 token: HumanEval/32 and /38 kept 1 token in a long run, but 768 and 101 tokens when generated fresh. `run_codegen.py` removes the leftover patch before each problem, so one criterion is active, as evalplus intends. Verified: per-problem time flat (447 s → 60 s for 16 problems) and outputs identical to fresh runs. All code samples were generated after the fix.
- lm-eval 0.4.13 computes logits for every position, which OOMs gemma-2-2b (256k vocab) and Llama-3.2-3B on 8 GB. `run_lm_eval.py` asks the model for only the last 512 positions (`logits_to_keep`) at batch size 1, which lm-eval's own slicing already supports, and fails loudly if a continuation is longer. Verified on Qwen2.5-1.5B: 269 log-likelihoods over 45 MMLU-Pro / MILU-Hindi / Belebele-Hindi items are bit-identical with and without it (max |diff| = 0).
- This PyTorch build (Windows) has no flash SDPA kernel, and its memory-efficient kernel rejects `enable_gqa`, so grouped-query models fell back to the math kernel, which builds the full attention matrix (Llama-3.2-3B OOM). `run_lm_eval.py` repeats the KV heads first (transformers' own path when a mask is present), so the memory-efficient kernel runs. Not bit-identical: on the same 45 Qwen items, mean |Δ log-likelihood| = 0.053 nats (max 0.23), 44/45 identical choices (the flip was an exact tie in the reference), identical task accuracies. Qwen's MMLU-Pro gate run predates this change (math kernel); all three eval-mini runs use the current code (Qwen's was rerun on 26 Oct). gemma-2 uses eager attention and is unaffected. The leaderboard used yet another kernel (flash, Linux).
- evalplus 0.3.1 sets `self.eos = EOS` (the module-level list) and then extends it in place, so in one process MBPP inherited HumanEval's stop strings (`\ndef `, `\nclass `, `\nimport `, `\nfrom `), confirmed in every MBPP run log. MBPP answers were cut at their first or second function (phi-2: 346/378 empty). `run_codegen.py` gives each decoder its own copy. **All MBPP/MBPP+ results before 26 Oct were invalid and were regenerated** (the invalid files are kept locally, not committed). HumanEval ran first in each process and was unaffected.
- transformers 5 rebuilt deepseek-coder-1.3b-base's tokenizer from its config class (LlamaTokenizerFast) instead of its byte-level `tokenizer.json`, dropping every space and newline (`def f(x):\n    return x + 1` → `deff(x):returnx+1`). `run_codegen.py` checks a round trip and falls back to the repo's own `tokenizer.json`, or stops. The other four tokenizers round-trip correctly (code, Devanagari, Telugu), so no other result was affected.
- Qwen2.5 ships `max_new_tokens: 2048` in `generation_config.json`, which transformers lets override lm-eval's own generation cap (`max_gen_toks`, 256 for GSM8K). `run_lm_eval.py` now clears it, as standard lm-eval behaviour intends (found by `maheshsv`, PR #21). Only Qwen's eval-mini GSM8K was affected (51 → 52 after a fresh rerun; the earlier run is kept locally). gemma-2-2b and Llama-3.2-3B have no such override, and gate tasks (log-likelihood) and code generation (explicit `max_new_tokens=768`) never used it.

## Protocol changes after seeing results

- none

## Limitations

- Qwen's code anchors come from a table that names no harness; its one code FAIL (HumanEval+ −2.41) may be protocol, not a bug.
- The leaderboard used a pinned lm-eval fork (commits `d4631ea6` / `121ee91`) on Linux GPUs; we use release 0.4.13 on Windows (RTX 3070 Laptop; MILU per-language rows on an RTX 4060 Ti 16 GB).
- Small models score close to chance (25%) on MILU's Indic languages, so MILU agreement is a weaker check than MMLU-Pro.
- The MILU paper's `avg` column does not state its aggregation. We use the simple mean of the 11 languages, which reproduces the paper's 31.43 / 32.85; lm-eval's size-weighted mean would give 33.51 / 34.87. Per-language rows are still the primary check.
