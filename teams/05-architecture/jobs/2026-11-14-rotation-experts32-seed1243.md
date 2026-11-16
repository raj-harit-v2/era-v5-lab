# Rotation R1: exp3_experts_32 (32 routed experts) at seed 1243

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Rahul Uniyal (rahulni)
Lead approval:   pending review by shivman (the arm and the seed were assigned in G5 on 14 Nov: 32 experts, seed 1243)
Question:        Does exp3_experts_32 give the same T2 held-out bits per byte at a new seed, 1243, as in the TSAI T2 table?
Script:          teams/05-architecture/harness/train_week2.py at lab commit 71bc0fb (the trainer commit of the TSAI T2 runs), with the TSAI T2 speed fixes (the diff in the TSAI comment on #441). Pinned as the Instructor asked in G5 on 14 Nov for seed repeats of Week 2 runs; not the #441 harness.
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp3_experts_32.yaml --runtime teams/05-architecture/configs/runtime_fast.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1243 --out ./out/exp3-experts32-1243
Config:          teams/05-architecture/configs/arms/exp3_experts_32.yaml (inherits t2.yaml). Only model.moe.num_experts changes, to 32. AdamW with `--lr 0.001` passed explicitly, the same command form as the TSAI attention job (jobs/2026-11-10-attention-t2.md). Runtime: configs/runtime_fast.yaml, which the TSAI comment on #441 says the T2 runs used; it is not in the repo (neither on main nor at 71bc0fb), so TSAI supplies it. config v1 is not touched.
Inputs:          the same TSAI-staged bundle as the TSAI T2 runs (the bundle of official job #310: tokenizer v0 and the matching P32 raw table, as jobs/2026-11-10-attention-t2.md names it). Held-out is heldout_v1. Identities from the TSAI attention records: tokenizer v0 sha256 2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5, raw table content sha256 47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f. I have not checked that the bundle is staged for a new job. TSAI to confirm the paths.
Hardware:        1 GPU, native bf16
Max time:        90 minutes (one T2 run; experiments/plan_v1.md gives exp3-experts-32 a 90 min cap)
Precision:       bf16
Measures:        val/bpb (aggregate), val/three_group_bpb, val/groups/english_bpb, val/groups/code_bpb, val/groups/indic_mean_bpb, per-slice val/slices/*/bpb, loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, completed steps, final_model_sha256
Expected result: no outcome is assumed. For comparison, the TSAI T2 table posted in G5 on 13 Nov (not yet in main): exp3_experts_32 mean 1.7716 over 2 seeds (-0.002 against the reference mean 1.7754, whose seed spread is about 0.007), with the TSAI reading "The expert count (8, 16 or 32) and the shared expert make no measurable difference at this size." A run that stops before 1,221 steps is INCOMPLETE_NOT_A_RESULT. Void if any NaN or inf.
Outputs:         metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt only; 50 MB or less. The trainer also writes a checkpoint, because a quality run (no `--smoke`) requires one; it is retained internally and not returned. final_model_sha256 in summary.json is the weights fingerprint.
Test log:        teams/05-architecture/jobs/evidence/2026-11-14-rotation-experts32-seed1243/smoke.log: train_week2.py at lab commit 71bc0fb on exp3_experts_32.yaml, CPU fp32, seed 1243, `--smoke`, 6 steps, context 160, batch 1, with configs/runtime.yaml (runtime_fast.yaml is not in the repo) and without the TSAI speed-fix diff. Exit 0, all 6 steps with finite losses (train CE 11.786 to 8.520), training wall time 36.5 s on Kaggle CPU. Same tokenizer v0 and raw table content hashes as the TSAI screen. A smoke on synthetic text, not a quality result.
```

## One run

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| exp3-experts-32 | exp3_experts_32.yaml | 1243 | ./out/exp3-experts32-1243/ |

The T2 reference is not re-run. It stays the runs already done at seeds 1234, 1235 and 1236.

## How the result will be reported (R2)

The seed-1243 bits per byte (aggregate, three-group, English, code, Indic) go beside the existing exp3_experts_32
seeds and the T2 reference seeds, in `experiments/rotation_rahulni.md`. Lower is better. Two readings:

1. **Beside the arm's own seeds.** Is the seed-1243 aggregate `val/bpb` inside the range of the two exp3_experts_32
   seeds in the TSAI T2 table? The G5 post gives only their mean (1.7716), so the per-seed values are asked for.
2. **Against the reference.** The gap between exp3_experts_32 at seed 1243 and the reference mean (1.7754), next to
   the reference seed spread (about 0.007, as posted).

One new seed does not name a winner and does not change config v1.

## Open items

1. **Inputs:** TSAI to confirm that the staged bundle and the heldout_v1 files are available for this job.
2. **Source:** pinned to trainer commit 71bc0fb with runtime_fast.yaml and the TSAI T2 speed fixes, as the Instructor asked in G5 on 14 Nov ("Use the updated harness only after TSAI merges #441"). Between 71bc0fb and main, the harness, this arm file, t2.yaml and runtime.yaml are unchanged, but teams/06-performance/configs/base.yaml (inherited by t2.yaml) changed in #406. Pinning keeps the run comparable with the T2 table.
3. **runtime_fast.yaml path:** the command uses `teams/05-architecture/configs/runtime_fast.yaml`, from "configs/runtime_fast.yaml" in the TSAI comment on #441 (not in the repo). TSAI to confirm the path; asked in G5 on 14 Nov.
4. **Per-seed values:** the per-seed val/bpb of exp3_experts_32 and of t2 at seeds 1234 to 1236, for the R2 comparison; asked TSAI in G5 on 14 Nov.
