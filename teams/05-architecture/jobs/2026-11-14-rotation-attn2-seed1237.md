# Rotation R1: attn-2 (window 128 with a sink) and the T2 reference at seed 1237

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Ravi Naik (RaviNaik)
Lead approval:   shivman
Question:        Does attn-2 (sliding window 128 with a sink) still pass its not-worse rule against the T2 reference at a new seed, 1237?
Script:          teams/05-architecture/harness/train_week2.py (on main)
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn2_swa128_sink.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1237 --out ./out/attn-2-1237
Config:          teams/05-architecture/configs/arms/attn2_swa128_sink.yaml (inherits t2.yaml). Only the attention changes: layer pattern L L L G L L L G, window 128 on L layers, learned sink on L layers. t2.yaml is the reference, unchanged. Both use AdamW with `--lr 0.001` passed explicitly, the same command form and output names as the TSAI attention job (attn-0 and attn-2). config v1 is not touched.
Inputs:          the same TSAI-staged bundle as the TSAI T2 runs (train split of tokenizer sample v0-clean, tokenizer teams/03-tokenizer/v0, byte table raw_table_P32.npz). Held-out is heldout_v1 (all 15 slices). Identities from the TSAI attention records: tokenizer v0 sha256 2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5, raw table content sha256 47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f. I have not checked that the bundle is staged for a new job. TSAI to confirm the paths.
Hardware:        1 GPU, native bf16 (compute capability 8 or higher)
Max time:        180 minutes total: 2 runs, 90 minutes cap per run.
Precision:       bf16
Measures:        val/bpb (aggregate), val/three_group_bpb, val/groups/code_bpb, val/groups/english_bpb, val/groups/indic_mean_bpb, per-slice val/slices/*/bpb (15 slices), loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, final_model_sha256, per run
Expected result: no outcome is assumed. For comparison, the TSAI T2 table posted in G5 (seeds 1234, 1235, 1236; not yet in main): reference mean 1.7754 with seed spread about 0.007, attn2 mean 1.7627 (-0.013 against the reference). In the one-seed preliminary screen in this folder (jobs/evidence/2026-11-10-attention-screen, seed 1235, `--smoke`, reconstructed inputs, not a quality result), three-group bits per byte were 1.9379 for the reference and 1.9250 for attn-2 (-0.0129). A run that stops before 1,221 steps is INCOMPLETE_NOT_A_RESULT. Void if any NaN or inf.
Outputs:         each run's metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt only; 50 MB or less total. The trainer also writes a checkpoint, because a quality run (no `--smoke`) requires one; it is retained internally and not returned. final_model_sha256 in summary.json is the weights fingerprint.
Test log:        teams/05-architecture/jobs/evidence/2026-11-14-rotation-smoke/smoke.log: train_week2.py on attn2_swa128_sink.yaml and on t2.yaml, CPU fp32, seed 1237, `--smoke`, 6 steps, context 160, batch 1. Both exit 0 with finite losses (train CE 11.86 to 4.55 for attn-2, 11.87 to 4.73 for the reference). Same tokenizer v0 and raw table hashes as the TSAI screen. A smoke on synthetic text, not a quality result.
```

## Two runs

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| attn-2 | attn2_swa128_sink.yaml | 1237 | ./out/attn-2-1237/ |
| reference (attn-0) | t2.yaml | 1237 | ./out/attn-0-1237/ |

The Command field holds the attn-2 run. The reference run is the same command with `--config teams/05-architecture/configs/arms/t2.yaml` and `--out ./out/attn-0-1237`.

## How the result will be read (R2)

The rule is the not-worse rule that TSAI accepted for attn-1, attn-2 and attn-3 (`docs/attention_harness.md`, `docs/attention_candidates.md`). For each of three metrics M (three-group mean `val/three_group_bpb`, code mean `val/groups/code_bpb`, Indic mean `val/groups/indic_mean_bpb`; lower is better), attn-2 passes when

    mean_M(attn-2) - mean_M(attn-0) <= max(range_M(attn-2), range_M(attn-0))

and all three must pass. I will read it two ways and report both:

1. **Seed 1237 alone.** The difference between the two arms at seed 1237, against the larger seed range of the two arms from seeds 1234 to 1236 (from the TSAI T2 table).
2. **Four seeds.** Means and ranges over seeds 1234 to 1237 for both arms.

I will also give the aggregate val/bpb gap against the seed spread, so that a reader can see how close it is to the noise. If a metric is outside the allowance, the answer is "does not hold" for that metric and the numbers are reported as they are. No arm is named a winner, and config v1 is not changed.

`compare_arms` in `harness/week2/scoring.py` is winner-only and needs exactly seeds 1234 to 1236, so it is not used for this. The comparison is made by hand and written to `experiments/rotation_RaviNaik.md`.

## Why now

Rotation R1 is due Wed 18 Nov and R2 on Thu 19 Nov (Team 5 week-3 work order). Seed 1237 is the one the lead assigned to this arm; seeds 1234 to 1236 were used by EXP-1 and T2.

## Open items

1. **Inputs:** TSAI to confirm that the staged bundle and the heldout_v1 files are available for this job.
2. **Harness:** PR 441 changes the harness and is still open. If it lands before the run, TSAI to say which version to use.
3. **Seed:** the lead assigned 1237; if that changes, only `--seed` and the output names change.
