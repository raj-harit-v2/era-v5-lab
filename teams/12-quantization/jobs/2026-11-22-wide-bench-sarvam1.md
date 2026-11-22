# Wide benchmark pass on sarvam-1: bf16 against Q8_0, Q4_K_M and Q3_K_M (Gate 4 evidence)

REQUEST FOR TSAI REVIEW. No approval and no run result is claimed. The author is the G12 owner below. SreekanthZipsy, the lead, approves; TSAI runs it. I need the result for Gate 4 evidence, due Fri 27 Nov, 11:59 PM IST.

```text
Team:            12-quantization
Owner:           Soma Korada (SomaKorada07)
Lead approval:   SreekanthZipsy
Question:        On full MMLU, ARC-Challenge and MILU (Kannada, Hindi, Telugu, Tamil, Bengali), how many points do sarvam-1's Q8_0, Q4_K_M and Q3_K_M GGUF files lose against its bf16 file on the same items, and do the Indic tasks lose more than the English ones?
Script:          teams/12-quantization/eval_wide/run_job.py (runs llama.cpp's converter, llama-quantize, eval_mini/test_llamacpp_lm.py, eval_wide/run_wide_gguf.py and eval_wide/paired.py)
Command:         python teams/12-quantization/eval_wide/run_job.py --model-dir ./inputs/sarvam-1 --hf-home ./inputs/hf_home --llama-dir ./work/llama.cpp-b11669 --convert-python ./work/.venv-convert/bin/python --formats bf16 Q8_0 Q4_K_M Q3_K_M --work ./work --out ./out/wide-sarvam1 --model sarvamai/sarvam-1 --revision e9607337286ddf496d4a2562b194e489dcf3feea
Config:          none. Every setting is on the command line or is a default of the scripts.
Inputs:          sarvamai/sarvam-1 at e9607337286d (public, licence click-through); lm_eval's MMLU and ai2_arc datasets; ai4bharat/MILU (CC-BY-4.0, gated). All staged once with network by eval_wide/prepare_inputs.py. See "Source and staging".
Hardware:        1 GPU (16 GB or more; the bf16 file is 5.05 GB)
Max time:        1,440 minutes (ESTIMATE from a T4, see "What I ran before filing"; shorter on a faster GPU)
Precision:       bf16 baseline; Q8_0, Q4_K_M and Q3_K_M weights, output layer Q8_0
Measures:        Per format and task: accuracy (acc; ARC-C acc_norm), item count, seconds per item, requests truncated at 4,096 tokens. Per quantized format and task, against bf16 on the same items: difference in points, 95% CI, McNemar exact p. Per format: GGUF size and sha256, guard test PASS/FAIL.
Expected result: Guard test PASS on all four files. Q8_0 within ±1 point of bf16 on every task. Q4_K_M 0 to 3 points down, more on MILU Kannada than on MMLU. Q3_K_M 2 to 6 points down. bf16 near 49% on MMLU (timing run: 48.9% on 1,140 items).
Outputs:         ./out/wide-sarvam1/{job.json, paired.md, runs/<format>/summary.json, runs/<format>/<task>.samples.jsonl, logs/*.log}, about 25 MB in total. No item text: per-item rows hold task, doc_id, filter and the metric only (Team 9's firewall). GGUF files are written to ./work/ and the quantized ones are deleted after each format.
Test log:        teams/12-quantization/jobs/evidence/2026-11-22-wide-bench-sarvam1/ (Kaggle T4 x2, run_wide_gguf.py on bf16, 20 items per task)
```

## Why a job and not Kaggle

The full pass is 56,592 items per format. On a Kaggle T4 that is about 8 GPU-hours for bf16 and 4 to 5.5 for each quantized file, about 22 hours for this one model. That is most of three members' weekly Kaggle quota, before Granite 3.0 MoE. Running all four formats on one machine also keeps the hardware the same for the paired comparison.

## One run

| Model | Formats | Tasks (items) | Output directory |
|---|---|---|---|
| sarvamai/sarvam-1 @ e9607337286d | bf16, Q8_0, Q4_K_M, Q3_K_M | MMLU (14,042), ARC-C (1,172), MILU Kannada (6,234), Hindi (14,831), Telugu (7,304), Tamil (6,372), Bengali (6,637) | ./out/wide-sarvam1/ |

One job, one command, no shell pipe. `run_job.py` stops at the first non-zero exit code and writes `job.json` after every step, so a stopped job shows where it stopped.

## Why these numbers of items

From OLMoE's paired bf16 against Q4_K_M data, a 2-point drop needs about 1,100 (ARC-C) to 2,900 (GSM8K) items per task to be seen at 80% power and p < 0.01. eval-mini has 200 to 570. Full splits clear the 2-point bar on every task here, and the 1-point bar on MMLU and MILU Hindi. Detail: `teams/12-quantization/docs/wide_benchmark_scope.md`.

## Where each setting comes from

| Setting | Value in this job | Source |
|---|---|---|
| Model | sarvamai/sarvam-1 @ `e9607337286ddf496d4a2562b194e489dcf3feea` | The week 3 Kannada drift run (#643, `runs/rotation_subramanyanaik.md`). |
| Formats | bf16, Q8_0, Q4_K_M, Q3_K_M | Q4_K_M is the format `docs/bitwidth_proposal.md` ships; Q8_0 is its fallback; Q3_K_M is where OLMoE first lost points. |
| Output layer | Q8_0 in every quantized file | Same rule as `scripts/quantize_eval.py` and every G12 result. |
| llama.cpp | b11669 converter and `llama-quantize` | The team's build since week 1. |
| Backend | llama-cpp-python 0.3.36 in-process, every position's logits | `eval_mini/llamacpp_lm.py`; the server routes give wrong prompt log-probabilities (`eval_mini/README.md`). |
| Guard test | `eval_mini/test_llamacpp_lm.py` on every file before it is scored | Instructor, 28 Oct: a file's scores must equal its own greedy generation's. |
| Tasks and shots | MMLU 0-shot, ARC-C 0-shot, MILU 5-shot | eval_mini profile (G9) for MMLU and ARC-C; G9's eval-mini v0 spec for MILU. |
| MILU task configs | `teams/09-evaluation/harness_code_indic/tasks/milu/` | G9, on main. |
| Context | 4,096 tokens | The timing run truncated no request at this length. |
| Seed | 42 | G9's default seed. |

## Source and staging

- Start from `theschoolofai/era-v5-lab` main with the PR that carries this file merged. `eval_wide/` and G9's `harness_code_indic/tasks/` are in it.
- Python 3.12 or later that runs `run_job.py`: `llama-cpp-python==0.3.36` (CUDA build), `lm_eval==0.4.13`, `datasets==5.1.0`. **No torch and no transformers in this environment**: lm_eval imports them when it finds them, and the eval_mini runs found broken ones on Kaggle.
- `llama-quantize` at b11669 on the PATH, or pass `--quantize <path>`.
- Work folder `./work/`, prepared once with network:
  - `llama.cpp-b11669/`, a checkout of tag b11669 (`git clone --depth 1 --branch b11669 https://github.com/ggml-org/llama.cpp`);
  - `.venv-convert/`, a Python venv with `llama.cpp-b11669/requirements/requirements-convert_hf_to_gguf.txt` and `llama.cpp-b11669/gguf-py` installed.
- Inputs, staged once with network by one command, with a read token of an account that accepted the terms of `ai4bharat/MILU` and `sarvamai/sarvam-1` in `HF_TOKEN`:
  `python teams/12-quantization/eval_wide/prepare_inputs.py --hf-home ./inputs/hf_home --model-dir ./inputs/sarvam-1 --model sarvamai/sarvam-1 --revision e9607337286ddf496d4a2562b194e489dcf3feea`
  It downloads the model snapshot (about 5 GB), loads every task through lm_eval's own loader into `./inputs/hf_home`, then loads them again with `HF_HUB_OFFLINE=1`, `HF_DATASETS_OFFLINE=1` and no token, to check the cache is complete. The token is not written anywhere.

With these in place the job makes no network call: `run_job.py` gives every step `HF_HUB_OFFLINE=1` and `HF_DATASETS_OFFLINE=1`, and needs no key.

## How the run is reported

- `paired.md`: one row per quantized format and task, with n, bf16 score, format score, difference (95% CI), b / c (items right in bf16 and wrong in the format, and the reverse) and McNemar p. The statistics are those of `eval_mini/paired.py`, used for every G12 bit-width result.
- English (MMLU, ARC-C) and Indic (MILU) rows are in one table. No pooled number across tasks.
- One model, one seed, greedy log-probability scoring. No bit width is chosen here; the result goes to Gate 4 next to `docs/bitwidth_proposal.md`'s drop limits.

## What I ran before filing

Kaggle, 2 × Tesla T4, 21 Nov, through `eval_wide/eval_wide.ipynb`. That notebook runs the same `run_wide_gguf.py` (runner sha256 `46190a8ab3e9ba2f`) with the same llama.cpp build, llama-cpp-python, lm_eval and G9 task configs, on sarvam-1 bf16 with 20 items per task (MMLU 20 per subject). Guard test PASS (log p(' Paris') −0.492 in both scoring and generation). All layers on the GPU, no request truncated, 549 s of scoring after about 32 minutes of setup.

| Task | Items | Score | Seconds per item |
|---|---:|---:|---:|
| MMLU | 1,140 | 48.9 | 0.40 |
| ARC-C | 20 | 45.0 | 0.52 |
| MILU Kannada | 20 | 10.0 | 0.68 |
| MILU Hindi | 20 | 35.0 | 0.46 |
| MILU Telugu | 20 | 50.0 | 0.60 |
| MILU Tamil | 20 | 30.0 | 0.58 |
| MILU Bengali | 20 | 30.0 | 0.51 |

From these times: bf16 about 8.0 h on a T4. The quantized files scored faster in the week 3 sarvam-1 run (#643: Q8_0 0.67×, Q4_K_M 0.53×, Q3_K_M 0.56× bf16's eval time), so about 22 h for the four formats, plus about 10 minutes to convert and quantize (Q4_K_M took 116 s in the smoke). A faster GPU should cut this, but llama-cpp-python scores one request at a time, so the speedup is less than the GPU's.

Files: [environment.json](evidence/2026-11-22-wide-bench-sarvam1/environment.json), [summary.json](evidence/2026-11-22-wide-bench-sarvam1/summary.json), [scores_long.csv](evidence/2026-11-22-wide-bench-sarvam1/scores_long.csv), [logs/](evidence/2026-11-22-wide-bench-sarvam1/logs/).

**The job command itself:** [smoke_run_job.md](evidence/2026-11-22-wide-bench-sarvam1/smoke_run_job.md), Kaggle, 21 Nov. `prepare_inputs.py` staged all 56,592 items and its offline check (no token, offline flags) PASSED. Then `run_job.py`, the command above with `--formats bf16 Q4_K_M --cap 2`: every step exit 0, Q4_K_M quantized in 116 s, and both GGUF files are byte-identical to the week 3 sarvam-1 files of #643 (bf16 `cfc747d2…`, Q4_K_M `21f41881…`). The smoke log says what that run did not cover.

The 20-item scores are not a result. Kannada's 2 of 20 is below the 25% chance line; at chance, 2 or fewer of 20 happens about 9% of the time, so the full split is needed to tell.

## Open items for TSAI

1. **Time.** 1,440 minutes is a T4 estimate. If that is too long, the same command with `--formats bf16 Q4_K_M` (about 13 h on a T4) answers the question for the format we ship. With `--cap 500`, each task is capped at 500 items (MMLU: 500 per subject, so most subjects run in full), which brings MILU Hindi and MMLU down while keeping every task over the 2-point bar.
2. **Gated inputs.** Can TSAI stage MILU and sarvam-1 with an account that accepted their terms? The job itself needs no token.
3. **Tools.** Are llama.cpp b11669 (`llama-quantize`) and a Python with llama-cpp-python 0.3.36 (CUDA), lm_eval 0.4.13 and datasets 5.1.0, without torch, available, and can `./work/` be prepared with network once?
4. **Work folder.** The rule is that a job writes only to `./out/`. The bf16 GGUF (5.05 GB) and one quantized file at a time go to `./work/`, outside `./out/`, as in our dry run 1 request (#508). If it must be under `./out/`, tell me which path is left out of the 50 MB count.
5. **Granite 3.0 MoE.** A second request follows: `ibm-granite/granite-3.0-3b-a800m-base` @ `142d2c8e3f7f`, MMLU and ARC-C only. Not the 1B-A400M of #643: it scored 27.1% on MMLU in our timing run, too close to chance to show drift. One job, one question.
