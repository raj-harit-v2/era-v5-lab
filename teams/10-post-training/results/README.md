# results: committed run reports

Index of the files in this folder. Each entry says what produced it and what it does not show. Numbers live in the linked file, not here.

## Week 3 / Gate 3 summary & core reports

| File | What it is | Limits |
|---|---|---|
| `gate3_summary.md` | Gate 3 evidence checklist, Week 3 Tasks 1–11 status, cross-team handoffs, and open TSAI decisions (20 Nov). | Index only; numbers live in the linked reports. |
| `rl_data_v1_close.md`, `rl_data_v1_closure.md` | RL data v1 rebuild kit, pool flags (`3,577` code close pool, `7,209` reserved MATH), verifier two-test evidence, and Team 9 handoff. | Pool bytes stay outside Git (rebuilt by TSAI in #564; checked 6/6 by Team 9 in #661). |
| `objective_v1_trainer.md` | Session 18 objective (`rl/objective_v1.py`) integration in `rl-loop/train.py`. | Mechanics verification; not a capstone quality claim. |
| `small_sft.md`, `small_sft_evidence/` | Small SFT run (`SmolLM2-135M`, OCR-2 slice) with `forgetting.py` verdicts (`0.05` bpb limit, `0.01` at-limit mark). | Surrogate model on C3 slice; not re-run on p1536. |
| `small_rl.md`, `code_rl_e1_20261115.md` | Small RL run on code verifiers (`Qwen2.5-Coder-7B-Instruct`, held-out pass@1 `0.151 -> 0.251`, 60 steps). | Surrogate model, one seed; dry-run-1 RL job queued in `jobs/2026-11-19-g10-rl-dryrun1.md`. |
| `dt_vs_fft.md`, `dt_sft_surrogate.md`, `dt_toy_sharpness_check_20261117.md`, `dt_lr_check_20261118.md` | Deletion Tuning (candidate, not decided) vs LoRA vs full FT comparison (`SmolLM2-135M`/`1.7B`) + deletion-fraction & target-layer sweeps + sharpness `100 -> 1000` & lr port checks. | Surrogate models; TSAI decides at Gate 3. |
| `dt_then_rl.md`, `dt_then_rl_evidence/` | Deletion Tuning SFT followed by small RL (3-seed CPU rehearsal on stand-in Team 5 MoE; 348,469 deleted weights stayed 0). | Toy reward on CPU; code-verifier GPU canary staged in `jobs/2026-11-17-dt-then-rl-code.md` and `jobs/2026-11-20-g10-dt-sft-dryrun1.md`. |

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
