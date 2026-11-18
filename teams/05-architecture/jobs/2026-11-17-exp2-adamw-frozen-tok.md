# Week 3 job request: frozen p1536 tokenizer, T2 AdamW (completes the EXP-2 comparison)

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or run completion is claimed.

```text
Team:            05-architecture
Owner:           Vardhan Walavalkar (vpw)
Lead approval:   pending review by shivman / udisinghania
Question:        Udit's matched T2 Muon rerun (#474) found p1536 at 1.5381 BPB vs tokenizer v0 at 1.6601 BPB (seed 1235, -0.1220 BPB). Does the T2 AdamW arm move the same way, and by how much, under the same frozen tokenizer? This is the AdamW half of the EXP-2 (AdamW vs Muon, PR #354) comparison that #474 left open.
Script:          teams/05-architecture/harness/train_week2.py at 71bc0fb, with TSAI's Gate 2 speed fixes (#441) and the C3/p1536 scoring patch from #474 (jobs/evidence/2026-11-15-frozen-c3-muon/c3-original-byte-bpb.patch). The patch is tokenizer-only -- it changes expected_tokenizer_sha and the byte-reconstruction check, nothing optimizer-specific -- so it applies unmodified to the AdamW arm.
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_adamw.yaml --runtime teams/05-architecture/configs/runtime_fast.yaml --resolution ./inputs/resolution.yaml --tokenizer-release frozen-c3 --tokenizer ./inputs/tokenizer_p1536.json --byte-table ./inputs/raw_table_p1536_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout_v1.jsonl --heldout-sources ./inputs/heldout_v1_sources.jsonl --heldout-sha256 ./inputs/heldout_v1.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1235 --out ./out/frozen-p1536-adamw-1235
Config:          teams/05-architecture/configs/arms/exp2_adamw.yaml, unchanged since #354 (optim.lr = 0.001, intended.comparison_final: false). Same runtime_fast.yaml and t2m1 resolution TSAI staged for #474.
Inputs:          Same Gate 2 train.jsonl (SHA-256 starts 267c33bf), original heldout_v1 (1,059 documents, 3,775,551 original UTF-8 bytes), the frozen p1536 tokenizer (SHA-256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b, released in #504, archiving C3) and its matching raw P32 byte table (content SHA-256 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a). Note the --tokenizer-release flag still reads "frozen-c3" -- the patch's flag name wasn't renamed in #474 -- but the expected hash pins to p1536, the same substitution TSAI made for the Muon run.
Hardware:        1 GPU with native BF16 support
Max time:        90 minutes, matching #474 and the original EXP-2 cap. A run stopping before step 1,221 is INCOMPLETE_NOT_A_RESULT.
Precision:       bf16
Measures:        Final val/bpb, val/nll_nats, val/utf8_bytes, val/encoded_utf8_bytes, scored tokens, per-slice and grouped BPB, completed steps, finite loss and gradient norm, step and wall time, data_load_seconds from manifest.json -- the same set #474 reported.
Expected result: 1,221 completed steps and BPB on the original heldout_v1 bytes. Report frozen AdamW BPB minus the matched v0-tokenizer AdamW result at seed 1235 (PR #354). No direction assumed -- AdamW's own tokenizer sensitivity hasn't been measured, only Muon's.
Outputs:         ./out/frozen-p1536-adamw-1235/{manifest.json,summary.json,metrics.jsonl,losses.txt,total_losses.txt}, 50 MB or less in total. Retain the checkpoint on the job machine.
Test log:        No fresh GPU/CPU training smoke -- no local GPU/torch in this environment. Re-checked today that exp2_adamw.yaml still loads and resolves cleanly through week2.config.load/validate (optim.lr 0.001, intended.arm exp2-adamw, intended.comparison_final false); unchanged since #354. The scoring patch is #474's own and already has its smoke evidence there.
```

## Why this, and why now

`experiments/results/frozen_tok.md` currently reports only the T2 Muon arm under the frozen tokenizer (#474). EXP-2 is an AdamW-vs-Muon comparison (#354); a Week 3 verdict on which optimizer the frozen tokenizer favors needs both arms at the matched seed. Nobody has filed the AdamW half yet. This mirrors #474's own request exactly -- same seed, same held-out file, same trainer pin and speed fixes, same scoring patch -- so the two results slot into one table.

## Pending

- [ ] TSAI review and preflight with the staged p1536 inputs and `runtime_fast.yaml`.
- [ ] Complete the frozen p1536 seed-1235 AdamW run.
- [ ] Record the frozen BPB, frozen BPB minus the matched v0 AdamW seed-1235 result, official data-load time, and run manifest in `frozen_tok.md`, adding an AdamW row alongside the existing Muon row.
