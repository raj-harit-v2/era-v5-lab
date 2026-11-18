# Rotation R1: attn4_gate (Sigmoid gate on attention output) at seed 1239

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           thinktinkergreen (@thinktinkergreen)
Lead approval:   pending review by shivman (the arm and the seed were assigned in G5 on 14 Nov: Sigmoid gate, seed 1239)
Question:        Does attn4_gate give the same T2 held-out bits per byte at a new seed, 1239, as in the TSAI T2 table?
Script:          teams/05-architecture/harness/train_week2.py at lab commit 71bc0fb (the trainer commit of the TSAI T2 runs), with the TSAI T2 speed fixes (the diff in the TSAI comment on #441). Pinned as the Instructor asked in G5 on 14 Nov for seed repeats of Week 2 runs; not the #441 harness.
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn4_gate.yaml --runtime teams/05-architecture/configs/runtime_fast.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1239 --out ./out/attn4-gate-1239
Config:          teams/05-architecture/configs/arms/attn4_gate.yaml (inherits t2.yaml). model.attn_gate: true, model.attn_gate_input: normalized, model.attn_gate_bias: false, model.attn_gate_init: linear_default. AdamW with `--lr 0.001` passed explicitly, the same command form as the TSAI attention job (jobs/2026-11-10-attention-t2.md). Runtime: configs/runtime_fast.yaml, which the TSAI comment on #441 says the T2 runs used; it is not in the repo, so TSAI supplies it. config v1 is not touched.
Inputs:          the same TSAI-staged bundle as the TSAI T2 runs (the bundle of official job #310: tokenizer v0 and the matching P32 raw table, as jobs/2026-11-10-attention-t2.md names it). Held-out is heldout_v1. Identities from the TSAI attention records: tokenizer v0 sha256 2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5, raw table content sha256 47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f. TSAI to confirm the paths.
Hardware:        1 GPU, native bf16
Max time:        90 minutes (one T2 run; experiments/plan_v1.md gives attn-4 a 90 min cap)
Precision:       bf16
Measures:        val/bpb (aggregate), val/three_group_bpb, val/groups/english_bpb, val/groups/code_bpb, val/groups/indic_mean_bpb, per-slice val/slices/*/bpb, loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, completed steps, final_model_sha256
Expected result: no outcome is assumed. Compare with existing attn-4 seeds (1234, 1235, 1236) and the T2 reference (attn-0). A run that stops before 1,221 steps is INCOMPLETE_NOT_A_RESULT. Void if any NaN or inf.
Outputs:         metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt only; 50 MB or less. The trainer also writes a checkpoint, because a quality run (no `--smoke`) requires one; it is retained internally and not returned. final_model_sha256 in summary.json is the weights fingerprint.
Test log:        teams/05-architecture/jobs/evidence/2026-11-15-rotation-attn4-seed1239/smoke.log: train_week2.py at lab commit 71bc0fb on attn4_gate.yaml, CPU fp32, seed 1239, `--smoke`, 6 steps, context 160, batch 1, with configs/runtime.yaml and without the TSAI speed-fix diff. Exit 0, all 6 steps with finite losses (train CE 11.964 to 6.878), training wall time 24.8 s. Same tokenizer v0 and raw table content hashes as the TSAI screen. A smoke on synthetic text, not a quality result.
```

## One run

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| attn-4 (sigmoid gate) | attn4_gate.yaml | 1239 | ./out/attn4-gate-1239/ |

The T2 reference is not re-run. It stays the runs already done at seeds 1234, 1235 and 1236.

## How the result will be reported (R2)

The seed-1239 bits per byte (aggregate, three-group, English, code, Indic) go beside the existing attn-4
seeds and the T2 reference seeds, in `experiments/rotation_thinktinkergreen.md`. Lower is better. Two readings:

1. **Against the baseline (attn-0):** Does attn-4 at seed 1239 maintain the win observed in primary seeds under the winner rule without unexpected regression on code or Indic?
2. **Spread check:** Is the seed-1239 bits-per-byte within the spread established by the three prior seeds?
