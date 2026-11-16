# Rotation R1: exp3-experts-8 (8 routed experts) at seed 1242

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Pradeep Kumar G S (pradeep-kumar-gs)
Lead approval:   pending review by shivman
Question:        Does exp3-experts-8 at a new seed, 1242, give bits per byte in line with its seeds in the TSAI T2 table?
Script:          teams/05-architecture/harness/train_week2.py at trainer commit 71bc0fb, with the TSAI execution-only speed fixes (comment on #441)
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp3_experts_8.yaml --runtime teams/05-architecture/configs/runtime_fast.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout_v1.jsonl --heldout-sources ./inputs/heldout_v1_sources.jsonl --heldout-sha256 ./inputs/heldout_v1.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1242 --out ./out/exp3-experts-8-1242
Config:          teams/05-architecture/configs/arms/exp3_experts_8.yaml (inherits t2.yaml; only num_experts changes, 16 -> 8 routed; 1 shared, top-2, expert FFN 768, block 2,048, batch 8, 1,221 steps). AdamW, --lr 0.001 passed explicitly, as in the EXP-3 job. config v1 is not touched.
Inputs:          the same TSAI-staged bundle as the EXP-3 T2 runs (training split, tokenizer v0, matching P32 byte table, resolution) and heldout_v1 (all 15 slices) with source map, checksum and G9 report. TSAI to confirm the paths.
Hardware:        1 GPU, native bf16
Max time:        90 minutes
Precision:       bf16
Measures:        val/bpb, val/three_group_bpb, val/groups/code_bpb, val/groups/english_bpb, val/groups/indic_mean_bpb, val/slices/*/bpb (15 slices), loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, completed steps, final_model_sha256
Expected result: no outcome is assumed; val/bpb close to the exp3-experts-8 seeds in the TSAI T2 table (T2 reference mean 1.7754, seed spread about 0.007, as posted in G5). Fewer than 1,221 steps is INCOMPLETE_NOT_A_RESULT. Void if any NaN or inf.
Outputs:         metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt; 50 MB or less. The checkpoint stays on the job machine.
Test log:        teams/05-architecture/jobs/evidence/2026-11-14-rotation-experts8-seed1242-smoke.txt (train_week2.py at 71bc0fb, CPU, 6 steps, seed 1242, exp3_experts_8 and t2, both exit 0, status SMOKE)
```

## Run

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| exp3-experts-8 | exp3_experts_8.yaml | 1242 | ./out/exp3-experts-8-1242/ |

The T2 reference is not re-run. It stays the runs already done at seeds 1234, 1235 and 1236.

## How the result will be reported (R2)

The seed-1242 bits per byte (aggregate, three-group, code, Indic) go beside the existing exp3-experts-8 seeds and the T2 reference seeds, in `experiments/rotation_pradeep-kumar-gs.md`. The file says whether seed 1242 falls within the existing seed spread. One new seed does not name a winner and does not change config v1.

## Open items for TSAI

1. Confirm the staged bundle and the heldout_v1 files for this job.
2. Confirm the runtime path `teams/05-architecture/configs/runtime_fast.yaml` (named `configs/runtime_fast.yaml` in the #441 comment; not in the repo).
3. The per-seed val/bpb of exp3-experts-8 and of t2 at seeds 1234 to 1236, for the R2 comparison.
