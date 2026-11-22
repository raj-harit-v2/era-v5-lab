# Rotation R1: exp3-shared-0 (no shared expert) at seed 1241

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Lokesh Arundathi (LokeshJatangi)
Lead approval:   pending review by shivman (arm and seed assigned in G5 on 14 Nov: no shared expert, seed 1241)
Question:        Does exp3-shared-0 (shared expert off) at a new seed, 1241, give T2 held-out bits per byte in line with its seeds in the TSAI T2 table?
Script:          teams/05-architecture/harness/train_week2.py on lab main (a2e7fc6), which carries the Gate 2 speed fixes merged in #521
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp3_shared_0.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout_v1.jsonl --heldout-sources ./inputs/heldout_v1_sources.jsonl --heldout-sha256 ./inputs/heldout_v1.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1241 --out ./out/exp3-shared-0-1241
Config:          teams/05-architecture/configs/arms/exp3_shared_0.yaml (inherits t2.yaml; only model.moe.num_shared changes, 1 -> 0; 16 routed, top-2, expert FFN 768, block 2,048, batch 8, 1,221 steps). AdamW, --lr 0.001 passed explicitly, as in the EXP-3 job. config v1 is not touched.
Inputs:          the same TSAI-staged bundle as the EXP-3 T2 runs (training split, tokenizer v0 sha256 2de039f2..., matching P32 byte table content sha256 47d411a9..., resolution) and heldout_v1 (all 15 slices) with source map, checksum and G9 report. TSAI to confirm the paths.
Hardware:        1 GPU, native bf16
Max time:        90 minutes
Precision:       bf16
Measures:        val/bpb, val/three_group_bpb, val/groups/code_bpb, val/groups/english_bpb, val/groups/indic_mean_bpb, val/slices/*/bpb (15 slices), loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, completed steps, final_model_sha256
Expected result: no outcome is assumed. For comparison: exp3-shared-0 mean 1.7659 over 2 seeds (TSAI T2 table, 13 Nov); T2 reference at seeds 1234/1235/1236/1237 = 1.7673/1.7796/1.7792/1.7542 (mean 1.7701, range 0.0254). Fewer than 1,221 steps is INCOMPLETE_NOT_A_RESULT. Void if any NaN or inf.
Outputs:         metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt; 50 MB or less. The checkpoint stays on the job machine.
Test log:        teams/05-architecture/jobs/evidence/2026-11-18-rotation-shared0-seed1241/smoke.log (train_week2.py on main a2e7fc6 with configs/runtime.yaml, CPU fp32, 6 steps, seed 1241, exp3_shared_0, run twice: both exit 0, status SMOKE, losses.txt byte-identical, same final_model_sha256, all losses finite)
```

## One run

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| exp3-shared-0 | exp3_shared_0.yaml | 1241 | ./out/exp3-shared-0-1241/ |

The T2 reference is not re-run. It stays the runs already done at seeds 1234 to 1237.

## How the result will be reported (R2)

The seed-1241 bits per byte (aggregate, three-group, English, code, Indic) go beside the existing exp3-shared-0 seeds and the T2 reference seeds, in `experiments/rotation_LokeshJatangi.md`. The file says whether seed 1241 falls within the existing seed spread. One new seed does not name a winner and does not change config v1.

## Open items for TSAI

1. Confirm the staged bundle and the heldout_v1 files for this job.
2. The command uses `configs/runtime.yaml` and the trainer on main (speed fixes from #521). If TSAI wants a different resolution file for T2 (e.g. the micro-batch used in the Gate 2 runs), it goes in `--resolution`.
3. The per-seed val/bpb of exp3-shared-0 at its two existing seeds, for the R2 comparison.
