# results: committed run reports

Index of the files in this folder. Each entry says what produced it and what it does not show. Numbers live in the linked file, not here.

## Effort suite (`eval/`)

| File | What it is | Limits |
|---|---|---|
| `effort_probe.md` | Suite design and CPU checks, 11 Nov. | Written before any generation run. It says no model had generated anything. |
| `effort_stageA_olmoe_2026-11-12/`, `effort_stageB_olmoe_2026-11-12/` | Per-cell records, per-sample summaries and pooled numbers for OLMoE-1B-7B-0924-Instruct; Stage B also has `report.md` (22 of 440 cells correct). | Not the capstone model. Cap 1024 for every label. Records carry `do_not_train: true`. |
| `attainability_survey_code2048.md` | Code arm re-run at a 2048-token cap on the Qwen stand-in. | Code arm only (32 prompts); math not re-run. A stand-in diagnostic, not a claim about the capstone model. |
| `effort_stageB_qwen_2026-11-12/` | `report.md`, `stageB_pooled.json`, and `sample0/`, `sample1/` (`summary.json`, `effort_stageB.jsonl`). Qwen3.6-35B-A3B-FP8, 55 prompts x 4 labels x 2 samples, cap 1024. | Not the capstone model. Cap 1024 for every label. Records carry `do_not_train: true`. |

## SWE environments (`../swe-envs/`)

| File | What it is | Limits |
|---|---|---|
| `swe_gold_check.md` | Gold check of the 21 environments, `linux/arm64`, 5 Nov. | Checks that tests fail before and pass after the upstream patch. No model attempt. |
| `swe_gold_check_amd64.md` | Same check on `linux/amd64`, 5 Nov. | Run under emulation on an Apple M1 Pro host, not native x86. |
| `swe_gold_reproduction.md` | Independent re-run of one environment (`python-validators__validators-191`), 5 Nov. | One environment. |
| `swe_env_review.md` | Quality review of the first environments against SWE-bench Verified criteria, 4 Nov. | Model-assisted (its header says Claude Sonnet) and "needs a human spot-check". Nothing was executed. Metadata for choosing environments, not training data. |
| `swe_rebench_pilot.md` | Admission results for five environments rebuilt from `nebius/SWE-rebench` PRs, on arm64 and amd64, with the rejected candidates listed. | A pilot of five. |

## RL reward (`../rl/`)

| File | What it is | Limits |
|---|---|---|
| `reward_pool_bench.md` | Rollouts per second with and without warm container pools, 5 Nov. | Throughput on known good and bad outputs on one Mac. It says nothing about model quality. |

## Small SWE tasks (`../swe-task/`, `../swe-task-go/`)

| File | What it is | Limits |
|---|---|---|
| `swe_e2e.md` | Calculator task, Docker. | No model. |
| `go_swe_e2e.md` | Go task, Docker. | No model. |
| `hindi_swe_e2e.md` | Hindi text-preparation task, 30 Oct. | Authored strings; no model, no score (its own statement). |
| `tamil_swe_e2e.md` | Tamil UTF-8 task, 28 Oct, local Python. | Authored strings; no model, no score (its own statement). |
| `kannada_swe_e2e.md` | Kannada serialization and SWE demonstration. | Browser appearance check is described in the report only. |

## Tokenizer and chat format (`../chat-format/`)

| File | What it is | Limits |
|---|---|---|
| `render_frozen_tokenizer.txt` | Output of a run on Team 3's tokenizer v0.1 (sha256 `a33c9907...`). | Not the Gate 2 tokenizer (sha 15468e66...), which is not in the repo as of 12 Nov. |

## Reports that live elsewhere

- SFT decontamination, conversion and OCR-2 records are under `../sft/` and `../docs/`, not here.
- RL data v1 records are in `../rl-data/` (see its README).
