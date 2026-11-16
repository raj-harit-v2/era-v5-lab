# Rotation R1: exp2-muon at seed 1244

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Raj H (raj-harit-v2)
Lead approval:   pending review by shivman (arm and seed assigned in G5 on 13 Nov: Muon, seed 1244)
Question:        Does exp2-muon give held-out bits per byte at a new seed, 1244, in line with its seeds in the T2 Muon table?
Script:          teams/05-architecture/harness/train_week2.py at trainer commit 71bc0fb, with the TSAI execution-only speed fixes (comment on #441)
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime_fast.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1244 --out ./out/exp2_muon-1244
Config:          teams/05-architecture/configs/arms/exp2_muon.yaml (inherits t2.yaml; optim.name muon, optim.lr 0.001, optim.muon_lr 0.01 provisional). Same T2 setup as EXP-2 (#354 / jobs/2026-11-11-exp2-optimizer.md). Only the seed changes, to 1244. config v1 is not touched.
Inputs:          the same TSAI-staged bundle as the EXP-2 / T2 Muon runs (tokenizer v0, matching P32 raw table, train split, resolution). Held-out is heldout_v1 (all 15 slices) with source map, checksum and report, as in the EXP-2 job. TSAI to confirm the staged paths.
Hardware:        1 GPU, native bf16
Max time:        90 minutes (one T2 run; experiments/plan_v1.md gives exp2-muon a 90 min cap)
Precision:       bf16
Measures:        val/bpb (aggregate), val/three_group_bpb, val/groups/english_bpb, val/groups/code_bpb, val/groups/indic_mean_bpb, per-slice val/slices/*/bpb, loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, completed steps, final_model_sha256
Expected result: no outcome is assumed. Compare seed-1244 bits per byte to the T2 Muon seeds (1234/1235/1236) from the EXP-2 / TSAI T2 table. A run that stops before 1,221 steps is INCOMPLETE_NOT_A_RESULT. Void if any NaN or inf.
Outputs:         metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt only; 50 MB or less. The trainer also writes a checkpoint, because a quality run (no --smoke) requires one; it is retained internally and not returned. final_model_sha256 in summary.json is the weights fingerprint.
Test log:        teams/05-architecture/jobs/evidence/2026-11-15-rotation-muon-seed1244-smoke.txt (exp2_muon.yaml load+validate; week2 optim tests; no full CPU train smoke — BrahmicTokenizer not installed in this environment)
```

## Run

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| exp2-muon | exp2_muon.yaml | 1244 | ./out/exp2_muon-1244/ |

The T2 Muon reference is not re-run. It stays the runs already done at seeds 1234, 1235 and 1236 (EXP-2 job #354).

## How the result will be reported (R2)

The seed-1244 bits per byte (aggregate, three-group, code, Indic) go beside the existing exp2-muon seeds in `experiments/rotation_raj-harit-v2.md`. The file says whether seed 1244 falls within the existing seed spread / preserves the Gate-2 Muon direction. One new seed does not name a winner and does not change config v1.

## Open items for TSAI

1. Confirm the staged bundle and the heldout_v1 files for this job (paths as in EXP-2 #354).
2. Confirm the runtime path `teams/05-architecture/configs/runtime_fast.yaml` (named in the #441 comment; not in the repo).
3. Confirm the per-seed val/bpb of exp2-muon at T2 (seeds 1234/1235/1236) for the hold call, if not yet on main.
