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
