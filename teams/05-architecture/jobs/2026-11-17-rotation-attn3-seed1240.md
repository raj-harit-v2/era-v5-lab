# Rotation R1: attn-3 (Half RoPE) at seed 1240

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Dattatreya Manjunath (@dattatreyamanjunath)
Lead approval:   pending review by shivman (arm and seed assigned in G5: Half RoPE, seed 1240)
Question:        Does attn-3 (Half RoPE: RoPE on 32 of 64 head dims) give the same T2 held-out bits per byte at a new seed, 1240, as in the TSAI T2 table, and does it still pass its not-worse rule against the T2 reference?
Script:          teams/05-architecture/harness/train_week2.py at lab commit 71bc0fb (the trainer commit of the TSAI T2 runs), with the TSAI T2 speed fixes (the diff in the TSAI comment on #441). The same pin as the attn4, experts32 and muon rotation requests, so the run is comparable with the T2 table.
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn3_prope_half.yaml --runtime teams/05-architecture/configs/runtime_fast.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1240 --out ./out/attn-3-1240
Config:          teams/05-architecture/configs/arms/attn3_prope_half.yaml (inherits t2.yaml). Only the attention changes: model.rotary_fraction 0.5, so RoPE rotates the first 32 of the 64 head dimensions and passes the other 32 through. AdamW with `--lr 0.001` passed explicitly, the same command form as the TSAI attention job (jobs/2026-11-10-attention-t2.md). Runtime: configs/runtime_fast.yaml, which the TSAI comment on #441 says the T2 runs used; it is not in the repo, so TSAI supplies it. No file under configs/ changes; config v1 is not touched.
Inputs:          the same TSAI-staged bundle as the TSAI T2 runs (the bundle of official job #310: tokenizer v0 and the matching P32 raw table, as jobs/2026-11-10-attention-t2.md names it). Held-out is heldout_v1 (all 15 slices). Identities from the TSAI attention records: tokenizer v0 sha256 2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5, raw table content sha256 47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f. TSAI to confirm the paths.
Hardware:        1 GPU, native bf16
Max time:        90 minutes (one T2 run; 1,221 steps, batch 8, context 2,048)
Precision:       bf16
Measures:        val/bpb (aggregate), val/three_group_bpb, val/groups/english_bpb, val/groups/code_bpb, val/groups/indic_mean_bpb, per-slice val/slices/*/bpb, loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, completed steps, final_model_sha256
Expected result: no outcome is assumed. For comparison, the T2 reference (attn-0) val/bpb at four seeds from the TSAI result comment on PR 462: 1.7673 (1234), 1.7796 (1235), 1.7792 (1236), 1.7542 (1237); mean 1.7701, range 0.0254. In the one-seed preliminary screen in this folder (jobs/evidence/2026-11-10-attention-screen, seed 1235, smoke-marked, reconstructed inputs, not a quality result), three-group bits per byte were 1.9313 for attn-3 and 1.9379 for the reference (-0.0066). A run that stops before 1,221 steps is INCOMPLETE_NOT_A_RESULT. Void if any NaN or inf.
Outputs:         metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt only; 50 MB or less. The trainer also writes a checkpoint, because a quality run (no `--smoke`) requires one; it is retained internally and not returned. final_model_sha256 in summary.json is the weights fingerprint.
Test log:        teams/05-architecture/jobs/evidence/2026-11-17-rotation-attn3-seed1240/smoke.log: train_week2.py at lab commit 71bc0fb on attn3_prope_half.yaml, CPU fp32, seed 1240, `--smoke`, 6 steps, context 160, batch 1, with configs/runtime.yaml and without the TSAI speed-fix diff. Exit 0, all 6 steps with finite losses, synthetic held-out BPB 2.7719 to 2.0702, training wall time 173.6 s, peak memory 1,269 MiB. manifest.json records rotary_fraction 0.5. Same tokenizer v0 and raw table content hashes as the TSAI screen. check_week2.py: valid; tests/test_week2_attention.py: 17 passed. A smoke on synthetic text, not a quality result.
```

## One run

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| attn-3 (Half RoPE) | attn3_prope_half.yaml | 1240 | ./out/attn-3-1240/ |

The T2 reference is not re-run. It stays the runs already done.

## How the result will be read (R2)

The rule is the not-worse rule for alternatives 1 to 3 in `jobs/2026-11-10-attention-t2.md` (and `docs/attention_harness.md`). For each of three metrics M (three-group `val/three_group_bpb`, code `val/groups/code_bpb`, Indic mean `val/groups/indic_mean_bpb`; lower is better), attn-3 passes when

    mean_M(attn-3) - mean_M(attn-0) <= max(range_M(attn-3), range_M(attn-0))

and all three must pass. I will read it two ways and report both:

1. **Seed 1240 alone.** attn-3 at seed 1240 against the reference mean, with the reference seed range as the allowance.
2. **All seeds.** Means and ranges over every attn-3 and reference seed that TSAI has posted.

The rule is defined on three seeds per arm. If either arm has fewer, the reading is reported as "not a formal pass". The aggregate val/bpb gap is also given next to the reference seed spread. No arm is named a winner, `comparison_final` stays false, and config v1 is not changed. The result goes to `experiments/rotation_dattatreyamanjunath.md`.

## Why now

Rotation R1 is due Wed 18 Nov and R2 on Thu 19 Nov (Team 5 week-3 work order). Seed 1240 is the one assigned to this arm in G5; seeds 1234 to 1236 were used by EXP-1 and T2.

## Open items

1. **Inputs:** TSAI to confirm that the staged #310 bundle and the heldout_v1 files are available for this job.
2. **Runtime path:** the command uses `teams/05-architecture/configs/runtime_fast.yaml`, from "configs/runtime_fast.yaml" in the TSAI comment on #441 (not in the repo). TSAI to confirm the path.
3. **Source:** main now carries the ported Gate 2 harness speedups (#521), and since `71bc0fb` it has also changed `t2.yaml` (explicit `ffn_hidden: 768`), `week2/model.py`, `week2/optim.py`, `week2/config.py`, `train_week2.py` and `teams/06-performance/configs/base.yaml`. This request pins `71bc0fb` plus the #441 diff, like the other rotation requests. TSAI to say if main should be used instead.
4. **Per-seed values:** the per-seed three-group, code and Indic BPB of attn-3 and of the reference at seeds 1234 to 1236 (from the TSAI T2 table), for the R2 comparison. To be asked in G5.
