# Week 2 Rotation Checks: Open Model Agreement with Published Scores

Each Week 2 rotation member in Team 09 (`09-evaluation`) runs one benchmark on one open model and compares our harness score against its published reference score.

## 1. Agreement Rule (Fixed Before Any Run)

- **Gate rule:** `PASS` if `|ours - published| <= 2.0` percentage points on the **full test set**, using the publisher's protocol (task definition, number of shots, metric, and aggregation).
- **No cherry-picking:** The rule and protocol are fixed before any run starts. A `FAIL` stands and is recorded with its observed difference and investigation notes.
- **Full test set:** Run the complete benchmark (`no --limit`, `no --log-samples`). Do not commit raw run outputs or per-item benchmark logs to git; post `results.json` and its `sha256` in `G9` chat.

## 2. How to Claim a Pair

1. Check the table below and `G9` chat first so no two rotation members run the same `(model, benchmark)` pair.
2. Post your claim in `G9` chat naming the model, pinned Hugging Face revision, benchmark task, shot count, metric, and published score with its source link.
3. Run via `teams/09-evaluation/harness_code_indic/run_lm_eval.py` (or the matching Team 09 harness) with weights fetched via `fetch_weights.py`.
4. Open a pull request adding your row to the results table below.

## 3. Results

| rotator | model @ revision | benchmark (task, shots, metric) | published (source link) | ours ± s.e. | Δ | verdict | harness commit | results.json sha256 | date |
|---|---|---|---|---|---|---|---|---|---|
| `@sureshmantha` | `Qwen/Qwen2.5-0.5B` @ `2630d3d2` | MuSR (`leaderboard_musr`, 0-shot, `acc_norm`, $n=756$) | `34.26 ± 1.68` ([Open LLM Leaderboard v2, `results_2024-10-24`](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/Qwen/Qwen2.5-0.5B/results_2024-10-24T00-00-00.000000.json)) | `33.86 ± 1.68` | `-0.40` | `PASS` | `1fc0130` (lm-eval 0.4.13, bf16, MPS) | `9e910fb2a52291120d6cf70deb83fc9a133ac79956a8a74690a080c1cbeb59d2` | `2026-11-03` |
| `@shank343` | `meta-llama/Llama-3.2-3B` @ `95c10230` | BBH (`leaderboard_bbh`, 3-shot, `acc_norm`, $n=5761$) | `39.25 ± 0.61` ([Open LLM Leaderboard v2, `results_2024-09-23`](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/meta-llama/Llama-3.2-3B/results_2024-09-23T09-55-05.332092.json)) | `39.30 ± 0.61` | `+0.05` | `PASS` | `4169aae` (lm-eval 0.4.13, bf16, NVIDIA L4) | `a97204a1770cf611ee7fd838ba3733a431b638ae9c442859fe383f2835fd7d2f` | `2026-11-04` |
| `@saitej123` | `Qwen/Qwen2.5-1.5B` @ `e5dfabbc` | MMLU-Pro (`leaderboard_mmlu_pro`, 5-shot, `acc`, $n=12032$) | `28.55 ± 0.41` ([Open LLM v2, `results_2024-10-24`](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/Qwen/Qwen2.5-1.5B/results_2024-10-24T00-00-00.000000.json)) | `28.51 ± 0.41` | `-0.04` | `PASS` | `e206f35` (lm-eval 0.4.13, bf16, RTX 5070 Ti, torch 2.13.0+cu129) | `1f7450a42f8a64e1c54d48926aa6e596514bf57c43443f220d2c2ce2e737d000` | `2026-11-03` |
| `@udisinghania` | `Qwen/Qwen2.5-1.5B` @ `e5dfabbc` | ARC-Challenge (`arc_challenge`, 25-shot, `acc_norm`, $n=1172$) | `54.7` ([Qwen blog](https://qwenlm.github.io/blog/qwen2.5-llm/), [report §5.1](https://arxiv.org/abs/2412.15115); publisher metric and s.e. unspecified; ours uses `acc_norm`; anchor corrected after run from 54.01 to 54.7 by G9 lead, verdict unchanged) | `54.78 ± 1.45` | `+0.08` | `PASS` | `837769fc6642643c2085d89b7a8984d36cc3f285` (lm-eval 0.4.13, bf16, Tesla T4) | `4b8020fabae8f7207ff05136d8efd884ab9c360fd5095936d2a5b33a7389c759` | `2026-11-03` |
| `@millermuttu` | `google/gemma-2-2b` @ `4d05c88d` | BBH (`leaderboard_bbh`, 3-shot, `acc_norm`, $n=5761$) | `36.21 ± 0.59` ([Open LLM Leaderboard v2, `results_2024-07-29`](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/main/google/gemma-2-2b/results_2024-07-29T16-38-17.664954.json)) | `36.21 ± 0.59` | `0.00` | `PASS` | `ba572c2` (lm-eval 0.4.13, bf16, eager attention, CUDA) | `55203cd604cec613aab8ebbef9d6372370593d867d09ba67b7fb4c10588508da` | `2026-11-04` |
| `@sandeepkunkunuru` | `Qwen/Qwen2.5-1.5B` @ `e5dfabbc` | BBH (`leaderboard_bbh`, 3-shot, `acc_norm`, $n=5761$) | `40.46 ± 0.60` ([Open LLM Leaderboard v2](https://huggingface.co/datasets/open-llm-leaderboard/results) / [`published_scores.json`](../harness_code_indic/published_scores.json)) | `40.50 ± 0.60` | `+0.04` | `PASS` | `5a1c5f3` (lm-eval 0.4.13, bf16, RTX 4050) | `1efac93132366cbb3004b31742728669dcc99a127891dba43fafcf0b957a67b5` | `2026-11-02` |
