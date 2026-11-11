# OLMoE-1B-7B: bf16 and six llama.cpp formats on G9's eval_mini

**What was run.** G9's **mini** profile, imported unchanged from `teams/09-evaluation/harness/run_eval_mini.py`:
ARC-Challenge 500, HellaSwag 400, MMLU 570 (10 per subject), GSM8K 5-shot 200, TruthfulQA-mc2 200; seed 42; 1,870
questions per format. Model `allenai/OLMoE-1B-7B-0924` @ `6d84c48581ec`. The GGUFs were converted and quantized with
llama.cpp b11669 (output tensor Q8_0 for every quantized format, as in `scripts/quantize_eval.py`) and scored
in-process with llama-cpp-python 0.3.36 under lm_eval 0.4.13. All runs were on Kaggle 2×T4, with every layer on the GPU.
Every format passed `test_llamacpp_lm.py` (the " Paris" log-probability check) before it was scored.

## Scores (% correct ± standard error)

| Format | ARC-C | HellaSwag | MMLU | GSM8K | TruthfulQA-mc2 |
|---|---|---|---|---|---|
| bf16 | 46.8 ± 2.2 | 66.0 ± 2.4 | 53.7 ± 2.0 | 10.5 ± 2.2 | 37.3 ± 2.8 |
| Q8_0 | 46.4 ± 2.2 | 65.8 ± 2.4 | 53.3 ± 2.0 | 12.5 ± 2.3 | 37.0 ± 2.8 |
| Q6_K | 47.6 ± 2.2 | 66.8 ± 2.4 | 53.7 ± 2.0 | 10.5 ± 2.2 | 37.4 ± 2.8 |
| Q5_K_M | 46.4 ± 2.2 | 66.2 ± 2.4 | 54.6 ± 2.0 | 13.0 ± 2.4 | 37.7 ± 2.8 |
| Q4_K_M | 47.0 ± 2.2 | 65.8 ± 2.4 | 51.8 ± 2.0 | 11.5 ± 2.3 | 36.9 ± 2.8 |
| Q3_K_M | 46.6 ± 2.2 | 64.8 ± 2.4 | 49.5 ± 2.0 | 9.0 ± 2.0 | 36.7 ± 2.7 |
| Q2_K | 39.2 ± 2.2 | 61.5 ± 2.4 | 43.3 ± 2.0 | 5.0 ± 1.5 | 38.9 ± 2.8 |

Primary metrics are G9's: acc_norm for ARC-C and HellaSwag, acc for MMLU and TruthfulQA-mc2 (the mc2 probability
share), and exact match (flexible extract) for GSM8K.

## Each format against bf16, on the same questions

A difference in points (format minus bf16) with its paired 95% CI and McNemar's exact p. **Bold** marks a difference
whose CI excludes zero. TruthfulQA-mc2 is a per-question probability, so it gets a mean paired difference with no
McNemar test. Full table (b / c counts): [`combined/paired.md`](combined/paired.md).

| Format | ARC-C | HellaSwag | MMLU | GSM8K | TruthfulQA-mc2 |
|---|---|---|---|---|---|
| Q8_0 | −0.4 (−1.0, +0.2) p 0.50 | −0.2 (−0.7, +0.2) p 1.00 | −0.4 (−1.3, +0.6) p 0.73 | +2.0 (−1.4, +5.4) p 0.39 | **−0.3 (−0.6, −0.1)** |
| Q6_K | +0.8 (−0.2, +1.8) p 0.22 | +0.8 (−0.7, +2.2) p 0.51 | +0.0 (−1.4, +1.4) p 1.00 | +0.0 (−2.8, +2.8) p 1.00 | +0.1 (−0.3, +0.5) |
| Q5_K_M | −0.4 (−1.9, +1.1) p 0.79 | +0.2 (−1.2, +1.7) p 1.00 | +0.9 (−1.0, +2.8) p 0.47 | +2.5 (−1.3, +6.3) p 0.30 | +0.4 (−0.2, +1.0) |
| Q4_K_M | +0.2 (−1.5, +1.9) p 1.00 | −0.2 (−2.1, +1.6) p 1.00 | −1.9 (−4.2, +0.3) p 0.13 | +1.0 (−3.4, +5.4) p 0.82 | −0.5 (−1.4, +0.5) |
| Q3_K_M | −0.2 (−2.2, +1.8) p 1.00 | −1.2 (−3.6, +1.1) p 0.41 | **−4.2 (−7.0, −1.4) p 0.004** | −1.5 (−6.0, +3.0) p 0.66 | −0.6 (−2.0, +0.8) |
| Q2_K | **−7.6 (−10.9, −4.3) p <0.001** | **−4.5 (−7.7, −1.3) p 0.010** | **−10.4 (−14.4, −6.3) p <0.001** | **−5.5 (−10.5, −0.5)** p 0.052 | +1.5 (−0.9, +4.0) |

**What it says**

- **Q8_0 through Q4_K_M are indistinguishable from bf16** on ARC-C, HellaSwag, MMLU and GSM8K. No McNemar p is below 0.1.
  Q4_K_M's MMLU (−1.9, p 0.13) is the closest to a real drop.
- **Q3_K_M is the first format with a measured loss**: −4.2 points on MMLU (45 questions lost, 21 gained). The other tasks are within noise.
- **Q2_K degrades broadly**: −7.6 ARC-C, −4.5 HellaSwag, −10.4 MMLU, −5.5 GSM8K.
- **TruthfulQA-mc2 hardly moves at any format**: the largest change is +1.5 at Q2_K, which is not significant.

**Two borderline cells, reported as they are**

- **Q8_0 TruthfulQA-mc2:** −0.3 points with a CI that excludes zero. The effect is real but tiny: a consistent small
  shift in the probability share, about one tenth of the score's standard error.
- **Q2_K GSM8K:** the normal-approximation CI excludes zero but the exact McNemar test gives p 0.052 (19 lost vs 8
  gained). With only 27 questions changing, the exact test is the one to trust: a likely but unconfirmed drop.

**Why paired.** Between formats, the standard errors are about ±2 to ±3 points, so error bars alone could not separate any
format above Q2_K from bf16. The paired comparison removes the question-to-question variation that both runs share.
That is how it detects Q3_K_M's 4-point MMLU drop. It also rules out drops larger than about 2 points on ARC-C,
HellaSwag and MMLU for Q8_0 to Q5_K_M (about 3 points on GSM8K, which has only 200 questions).

**Checks behind these numbers**

- **Backend vs G9's harness:** Qwen2.5-0.5B bf16 matches G9's own harness on all five tasks; the largest gap is
  1.5 points (0.32 SE).
- **bf16 first:** the bf16 run was posted before any quantized format, as the instructor required.
- **Identical settings:** `combine.py` checked every run against the bf16 run (revision, profile, seed, n_ctx, lm_eval and
  llama-cpp-python versions, the hash of G9's runner, full question counts). It also checked that all quantized runs share
  one notebook version, `70829160c1bd`.
- **Independent recompute:** the PM agent recomputed every score from the per-question files with 0 mismatches.

## Where things are

| Path | What |
|---|---|
| `combined/scores.csv`, `combined/scores.md` | the scores table |
| `combined/paired.md` | the paired table with b / c counts |
| `combined/provenance.json` | who ran each format, hardware, scoring time |
| `raw/runs_<formats>/<format>/summary.json` | G9's record format, all metrics |
| `raw/runs_<formats>/<format>/*.samples.jsonl` | one row per question: task, doc_id, filter, metric values (what `paired.py` reads) |
| `raw/runs_<formats>/environment.json` | settings, versions, GPU, timings |
| `raw/runs_<formats>/logs/SUMMARY.md` | the run's logs cut to what matters: build, quantize sizes and times, per-task results, errors |
| `raw/runs_<formats>/logs/test_llamacpp_lm_<format>.log` | the logprob test output |

| Run | Formats | Run by | Date |
|---|---|---|---|
| `runs_bf16` | bf16 | s9k96 | 28 Oct |
| `runs_Q8_0-Q6_K` | Q8_0, Q6_K | SreekanthZipsy | 29 Oct |
| `runs_Q5_K_M-Q4_K_M` | Q5_K_M, Q4_K_M | therahulbhati | 29 Oct |
| `runs_Q3_K_M-Q2_K` | Q3_K_M, Q2_K | s9k96 | 29 Oct |

To keep the PR small, some things were cut:
- the full Kaggle logs (about 2 MB per run, mostly compiler output), replaced by `logs/SUMMARY.md`;

**Rebuild the tables:** `python combine.py results/raw/* --out <dir>` from `eval_mini/`. It writes the same
`scores.md` and `paired.md` as `combined/`, plus a copy of every format folder.
