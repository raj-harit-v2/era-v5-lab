# OLMoE-1B-7B: bf16, Q8_0, Q4_K_M and Q3_K_M on G9's eval-mini v0 code + Indic

**What was run.** G9's code + Indic half of eval-mini v0 (`harness_code_indic/eval_mini_v0_spec.json` at G9 commit
`fa5d87e41ebe`, spec sha256 `94de47d2334e`): MMLU-Pro 300, GSM8K 100, Belebele Hindi/Telugu/Tamil 100 each, MILU
Hindi/Telugu/Tamil/Bengali 100 each (5-shot), HumanEval+ 164 and MBPP+ 378 (greedy, 768 new tokens). That is 1,642
items per format. Model `allenai/OLMoE-1B-7B-0924` @ `6d84c48581ec`. The GGUFs were converted and quantized with
llama.cpp b11669 (output tensor Q8_0 in every quantized format) and scored in-process with llama-cpp-python 0.3.36,
lm_eval 0.4.13 and evalplus 0.3.1, with `n_ctx` 4096. All four formats ran in one Kaggle 2×T4 session on 1 Nov 2026
(14:30 to 18:28 GMT), every layer on the GPU. Each file passed `test_llamacpp_lm.py` (the " Paris" log-probability
check) before it was scored.

**Router and output types**, from this run's own conversion and quantization logs (`raw/.../logs/`): all 16
`ffn_gate_inp` (router) tensors are F32 in every format. `output.weight` is BF16 in bf16 and Q8_0 in the quantized files.

## Scores (% correct)

Primary metrics as G9's results file: acc; GSM8K exact match (flexible extract); HumanEval+ and MBPP+ plus pass@1
(base pass@1 in brackets). Standard errors are about ±2 points for MMLU-Pro and the code tasks and about ±4.5 for the
100-item tasks.

| Format | GB | MMLU-Pro | GSM8K | Belebele hin / tel / tam | MILU hi / te / ta / bn | HumanEval+ | MBPP+ | Mean of 11 |
|---|---|---|---|---|---|---|---|---|
| bf16 | 13.84 | 14.0 | 10.0 | 27 / 26 / 28 | 22 / 22 / 35 / 25 | 13.4 (14.6) | 20.9 (28.0) | 22.1 |
| Q8_0 | 7.36 | 13.7 | 10.0 | 27 / 27 / 27 | 25 / 24 / 35 / 25 | 13.4 (15.2) | 21.2 (27.0) | 22.6 |
| Q4_K_M | 4.24 | 13.0 | 7.0 | 26 / 26 / 29 | 24 / 23 / 33 / 28 | 11.6 (13.4) | 20.4 (26.5) | 21.9 |
| Q3_K_M | 3.37 | 13.3 | 6.0 | 30 / 29 / 28 | 22 / 28 / 27 / 25 | 9.8 (11.0) | 19.3 (25.4) | 21.6 |

## Each format against bf16, on the same items

Full table with 95% CIs and b / c counts: [`raw/runs_bf16-Q8_0-Q4_K_M-Q3_K_M/paired.md`](raw/runs_bf16-Q8_0-Q4_K_M-Q3_K_M/paired.md).

- **One significant change:** Q3_K_M HumanEval+ is −3.7 points (CI −6.5 to −0.8, McNemar p 0.031). bf16 solved 6
  problems that Q3_K_M failed, and Q3_K_M solved none that bf16 failed.
- **Q8_0 matches bf16.** Every difference is within 3 points with p ≥ 0.375. HumanEval+ is identical item for item.
- **Q4_K_M** has no significant change. The largest differences are GSM8K −3.0 (p 0.58) and HumanEval+ −1.8 (p 0.38).
- **Q3_K_M** also loses 4 points on GSM8K (p 0.34) and 8 on MILU Tamil (p 0.19). Neither is significant at 100 items.

## What the Indic tasks can and cannot show

OLMoE is trained mostly on English. Belebele and MILU both have four options, so chance is 25%, and bf16 scores 22
to 35%. Belebele is also cut hard by the 4096-token context: 388 of 400 Hindi requests and all 400 Telugu and Tamil
requests were left-truncated (the oldest shots go first), the same in every format. With the model near chance, the
Indic differences between formats are noise in both directions (Q3_K_M is +6 on MILU Telugu and −8 on MILU Tamil).
They cannot detect quantization loss for this model. MMLU-Pro (also near its 10% chance), GSM8K and the code tasks carry
what signal there is, and code is where Q3_K_M shows its loss.

## Files

- `raw/runs_bf16-Q8_0-Q4_K_M-Q3_K_M/<format>/summary.json`: run metadata and per-task scores, with dataset revision,
  item hash, truncation count and wall time.
- `raw/.../<format>/<task>.samples.jsonl`: per-item correctness only (task, doc_id, filter, score), no question text.
- `raw/.../logs/`: conversion, quantization, logprob check and run logs. The `wrapt` and `not a git repository`
  lines are Kaggle start-up noise and do not affect the run.
- The GGUFs and evalplus generations are not in the repo.
- The notebook version used (`e8611441a4dc`) predates the notebook's own tensor-type check. Router and output types
  were therefore read from the logs above.
