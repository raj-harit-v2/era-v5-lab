# Wide benchmark pass: results (G12, week 4)

**sarvam-1: Q8_0 loses nothing measurable; Q4_K_M loses 2.9 points on MMLU and 4.0 to 7.6 points on every Indic
reading task, Kannada worst.** The 200-item stand-in set showed no loss for either format (#643). For an Indic model
the evidence supports serving **Q8_0, not Q4_K_M**.

**Granite 3.0 3B-A800M (MoE) shows the same pattern in English:** Q8_0 −0.04 on MMLU (no loss), Q4_K_M −2.31
(p < 0.001), section 6. On both models Q4_K_M fails the proposal's MMLU test and Q8_0 passes everything.

Scope and sample sizes: [`../../docs/wide_benchmark_scope.md`](../../docs/wide_benchmark_scope.md). Approved job
requests: [`../../jobs/2026-11-22-wide-bench-sarvam1.md`](../../jobs/2026-11-22-wide-bench-sarvam1.md),
[`../../jobs/2026-11-22-wide-bench-granite30-3b.md`](../../jobs/2026-11-22-wide-bench-granite30-3b.md). The runs were
made on a member's own Kaggle quota, as the lab said on #714; section 5 lists where they differ from the requests.

## 1. sarvam-1: scores

`sarvamai/sarvam-1` @ `e9607337286d`, llama.cpp b11669 GGUF files (output layer Q8_0 in every quantized file),
llama-cpp-python 0.3.36 in-process on Kaggle 2 × Tesla T4, `n_ctx` 4,096 (no request truncated in any run), seed 42.
Accuracy in %; ARC-C is `acc_norm`, every other task `acc`. Chance is 25% on every task.

| Task | Items | Shots | bf16 | Q8_0 | Q4_K_M |
|---|---:|---:|---:|---:|---:|
| MMLU | 14,042 | 0 | 48.89 | 48.65 | 45.95 |
| ARC-C | 1,172 | 0 | 51.11 | 50.26 | 49.74 |
| Belebele Kannada | 900 | 5 | 57.67 | 57.11 | 50.11 |
| Belebele Hindi | 900 | 5 | 59.22 | 58.89 | 54.56 |
| Belebele Telugu | 900 | 5 | 52.22 | 52.22 | 47.22 |
| Belebele Tamil | 900 | 5 | 56.11 | 56.11 | 51.89 |
| Belebele Bengali | 900 | 5 | 51.22 | 50.00 | 47.22 |
| MILU Kannada (control) | 2,500 | 5 | 27.96 | 28.00 | 27.44 |
| MILU Hindi (control) | 2,500 | 5 | 29.96 | 29.68 | 28.96 |
| MILU Telugu (control) | 2,500 | 5 | 28.92 | 28.44 | 26.88 |
| MILU Tamil (control) | 2,500 | 5 | 29.24 | 29.44 | 27.08 |
| MILU Bengali (control) | 2,500 | 5 | 28.52 | 28.32 | 27.44 |

| | bf16 | Q8_0 | Q4_K_M | Q3_K_M |
|---|---:|---:|---:|---:|
| GGUF size | 5.05 GB | 2.69 GB | 1.58 GB | not scored (section 4) |
| Guard test (`test_llamacpp_lm.py`), prefix-cache diff | PASS, 0.0001 | PASS, 0.0093 | PASS, 0.0074 | **FAIL, 0.0862** |
| Scoring time, all 12 tasks | 3.6 h | 1.4 h | 1.3 h (over three runs, each task counted once) | |

## 2. sarvam-1: each format against bf16 on the same items

Difference in points (format minus bf16), 95% CI from the paired variance, b = right in bf16 and wrong in the format,
c = the reverse, McNemar's exact test. Same statistics as `../eval_mini/paired.py`. Full table:
[`paired_sarvam-1.md`](paired_sarvam-1.md). **Bold**: p < 0.01.

| Task | Q8_0 | p | Q4_K_M | p |
|---|---|---:|---|---:|
| MMLU | −0.24 (−0.59 to +0.11) | 0.188 | **−2.94** (−3.58 to −2.30) | < 0.001 |
| ARC-C | −0.85 (−1.80 to +0.09) | 0.110 | −1.37 (−3.05 to +0.32) | 0.137 |
| Belebele Kannada | −0.56 (−1.55 to +0.44) | 0.383 | **−7.56** (−10.05 to −5.06) | < 0.001 |
| Belebele Hindi | −0.33 (−1.42 to +0.76) | 0.690 | **−4.67** (−7.13 to −2.20) | < 0.001 |
| Belebele Telugu | +0.00 (−1.31 to +1.31) | 1.000 | **−5.00** (−7.60 to −2.40) | < 0.001 |
| Belebele Tamil | +0.00 (−0.97 to +0.97) | 1.000 | **−4.22** (−6.59 to −1.85) | 0.001 |
| Belebele Bengali | −1.22 (−2.43 to −0.01) | 0.071 | **−4.00** (−6.45 to −1.55) | 0.002 |
| MILU Kannada (control) | +0.04 (−0.47 to +0.55) | 1.000 | −0.52 (−1.79 to +0.75) | 0.459 |
| MILU Hindi (control) | −0.28 (−0.86 to +0.30) | 0.419 | −1.00 (−2.35 to +0.35) | 0.162 |
| MILU Telugu (control) | −0.48 (−1.11 to +0.15) | 0.169 | **−2.04** (−3.40 to −0.68) | 0.004 |
| MILU Tamil (control) | +0.20 (−0.43 to +0.83) | 0.620 | **−2.16** (−3.54 to −0.78) | 0.003 |
| MILU Bengali (control) | −0.20 (−0.86 to +0.46) | 0.635 | −1.08 (−2.41 to +0.25) | 0.126 |

## 3. What it shows

- **Q8_0 is indistinguishable from bf16 on every task.** No p is under 0.07. On MMLU the interval is ±0.35 points, so
  a 1-point loss is ruled out, which the 200 to 570 item tasks of eval-mini could not do. Between 1.7% and 4.5% of
  items change answer, in both directions about equally.
- **Q4_K_M fails sarvam-1 under `docs/bitwidth_proposal.md`.** MMLU −2.94 sits just inside the −3 point limit, but the
  proposal also fails a task at McNemar p < 0.01, and MMLU's p is below 0.001 (2,117 of 14,042 items flip, 15%; OLMoE's
  Q4_K_M flipped 7.5%). ARC-C (−1.37, p 0.137) is inside its −2 limit.
- **Indic reading drops 1.4 to 2.6 times as many points as English.** The proposal sets no limit for Indic tasks; by
  the same p < 0.01 rule all five Belebele languages fail at Q4_K_M. Measured as the share of each task's margin
  above chance that Q4_K_M loses:

  | Task | bf16 above chance | Lost at Q4_K_M | Share lost |
  |---|---:|---:|---:|
  | ARC-C | 26.1 | 1.37 | 5% |
  | MMLU | 23.9 | 2.94 | 12% |
  | Belebele Hindi | 34.2 | 4.67 | 14% |
  | Belebele Tamil | 31.1 | 4.22 | 14% |
  | Belebele Bengali | 26.2 | 4.00 | 15% |
  | Belebele Telugu | 27.2 | 5.00 | 18% |
  | **Belebele Kannada** | 32.7 | **7.56** | **23%** |

- **Kannada drops most**, as week 3's KL and same-top-1 measures on Kannada text predicted (#643), now on a benchmark
  at p < 0.001. One model, one seed: read it as a measurement on sarvam-1, not a rule for every Indic model.
- **The 200-item stand-in set missed all of this.** On it, sarvam-1's Q4_K_M scored MMLU +2 against bf16 (#643).
- **MILU is a control, not evidence.** sarvam-1 scores 28 to 30% on it at bf16, 3 to 5 points above chance, so most of
  its flips are noise. Even so, Q4_K_M's Telugu and Tamil drops are significant and bring both close to chance.

## 4. Q3_K_M: not scored (guard test)

sarvam-1 Q3_K_M failed check 3 of `../eval_mini/test_llamacpp_lm.py` in two separate runs, with the same value both
times: scoring with the prefix cache moved a score by **0.0862 nats** against scoring from scratch (limit 0.05).
Checks 1 and 2 passed (log p(' Paris') −0.537 in scoring and in generation; off-by-one value −6.067), so the
shifted-logprob bug is not back. At 3 bits the cached and uncached computations differ more (bf16 0.0001, Q8_0
0.0093, Q4_K_M 0.0074). The guard was not loosened to get a number; Q3_K_M is reported as not scored. A rerun with
check 3 at 0.10 for Q3_K_M only is possible if the lab wants it on the ladder. It would not change the ship decision:
the proposal already drops Q3_K_M, and Q4_K_M already fails.

## 5. Provenance and differences from the job requests

- **Compute:** the member's Kaggle quota (2 × Tesla T4 throughout), not a TSAI job, as the lab said on #714.
- **MILU capped at the first 2,500 items per language** (`--cap 2500`) to fit one member's 30 GPU-hour quota. MMLU
  (no subject has 2,500 items) and ARC-C run in full. lm_eval takes the first N items, so every format scored the
  same items.
- **Belebele added** (22 Nov), after bf16 scored MILU at 28 to 30%. Five 5-shot tasks of 900 items, as in G9's
  eval-mini v0. This changed `run_wide_gguf.py` from runner sha256 `46190a8ab3e9ba2f` to `66f9de0b6b168f49`; the
  change only adds the Belebele entries, so MMLU, ARC-C and MILU are scored the same way by both.
- **Which runner scored what.** bf16: MMLU, ARC-C and MILU by `46190a8a…`, Belebele by `66f9de0b…` (its
  `summary.json` shows the last pass's hash). Q8_0: all 12 by `66f9de0b…`. Q4_K_M: three runs, because an interactive
  session was lost after it finished: MMLU and ARC-C (run 1, `66f9de0b…`; run 2, `46190a8a…`, **byte-identical
  per-item results**), MILU (run 2), Belebele (run 3, `66f9de0b…`). Every run quantized the same 1,581,512,288-byte
  Q4_K_M file; its sha256 `21f41881…` matches #643 (job smoke, `../../jobs/evidence/2026-11-22-wide-bench-sarvam1/`).
- **Eval firewall:** per-item rows hold only task, doc_id, filter and the metric. No item text, prompt or answer was
  written anywhere.

## 6. Granite 3.0 3B-A800M (MoE)

`ibm-granite/granite-3.0-3b-a800m-base` @ `142d2c8e3f7f` (32 layers, 40 experts with top-8, router F32 in every file),
one committed Kaggle run (2 × Tesla T4, 23 Nov, runner `66f9de0b6b168f49`), full MMLU and ARC-C, no cap, nothing
truncated. English tasks only: Granite 3.0 is not trained on Indic languages. Full paired table:
[`paired_granite-3.0-3b-a800m.md`](paired_granite-3.0-3b-a800m.md).

| | bf16 | Q8_0 | Q4_K_M |
|---|---:|---:|---:|
| GGUF size | 6.75 GB | 3.59 GB | 2.08 GB |
| Guard test, prefix-cache diff | PASS, 0.0434 | PASS, 0.0097 | PASS, 0.0424 |
| Scoring time (MMLU + ARC-C) | 1.6 h | 0.5 h | 0.4 h |
| MMLU (14,042) | 47.46 | 47.41 | 45.15 |
| ARC-C (1,172) | 46.50 | 46.16 | 46.25 |

| Task | Q8_0 against bf16 | p | Q4_K_M against bf16 | p |
|---|---|---:|---|---:|
| MMLU | −0.04 (−0.40 to +0.31) | 0.844 | **−2.31** (−3.01 to −1.60) | < 0.001 |
| ARC-C | −0.34 (−1.23 to +0.54) | 0.572 | −0.26 (−1.87 to +1.36) | 0.836 |

- **Q8_0 is indistinguishable from bf16** (4.6% of MMLU items change answer, evenly in both directions).
- **Q4_K_M fails on MMLU by the proposal's p < 0.01 rule** (point estimate −2.31, inside the −3 limit). 18% of MMLU
  items change answer (sarvam-1: 15%, OLMoE: 7.5%), which fits week 3's finding that the 1B Granite sibling drifts
  more than OLMoE at Q4_K_M (KL 0.065 against 0.023). It loses 10% of its MMLU margin above chance (sarvam-1: 12%).
- **ARC-C does not move** at either format. With 1,172 items it cannot rule out a drop of about 2 points.
- **The guard margin on this MoE held:** prefix-cache diff 0.0434 (bf16), 0.0097 (Q8_0), 0.0424 (Q4_K_M), all under
  0.05, as the lab asked us to watch. Q3_K_M was left out of this run (sarvam-1 Q3_K_M failed the same check, section 4).

## 7. Both models together

| Model | Format | MMLU against bf16 | Indic (Belebele, 5 languages) | Under the proposal |
|---|---|---|---|---|
| sarvam-1 (dense, Indic) | Q8_0 | −0.24, p 0.19 | −1.22 to +0.00, all p ≥ 0.07 | pass |
| sarvam-1 | Q4_K_M | −2.94, p < 0.001 | −4.00 to −7.56, all p ≤ 0.002 | fail |
| Granite 3.0 3B-A800M (MoE, English) | Q8_0 | −0.04, p 0.84 | not run | pass |
| Granite 3.0 3B-A800M | Q4_K_M | −2.31, p < 0.001 | not run | fail |

On both architectures Q4_K_M's loss is real and large enough to see once the benchmark has enough items, and Q8_0's
is not measurable. On the Indic model the Indic tasks lose the most.

## 8. Files and rerun

| Path | What |
|---|---|
| `raw/<model>/<format>/<task>.samples.jsonl` | per-item results (task, doc_id, filter, metric) |
| `raw/<model>/<format>/summary*.json` | run metadata and one record per task (sarvam-1 Q4_K_M: one file per run) |
| [`paired_sarvam-1.md`](paired_sarvam-1.md), [`paired_granite-3.0-3b-a800m.md`](paired_granite-3.0-3b-a800m.md) | the paired tables, written by `../paired.py` |

Rebuild a paired table, from this folder: `python ../paired.py raw/sarvam-1 --base bf16 --out paired_sarvam-1.md`
(Granite: `raw/granite-3.0-3b-a800m`). Rerun a format: `../eval_wide.ipynb` on Kaggle, `CAP = 2500`, the model and revision above, and `TASKS` for
a subset.
