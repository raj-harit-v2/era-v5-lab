# Week 3 job request: frozen C3 tokenizer, T2 Muon

**Historical request.** This file records the original C3-s0 request. TSAI completed the corresponding T2 Muon run at seed 1235 with p1536 and its matching raw P32 table. TSAI reported BPB for the comparison and retains the raw timing and manifest files. See the [final comparison](../experiments/results/frozen_tok.md) and the [official result on PR #474](https://github.com/theschoolofai/era-v5-lab/pull/474#issuecomment-6908490508). The command, inputs, and outputs below describe the original request.

```text
Team:            05-architecture
Owner:           Udit Singhania (udisinghania)
Lead approval:   shivman (lead review on #474)
Question:        How does frozen C3 change held-out bits per original UTF-8 byte versus tokenizer v0 for the same T2 Muon arm and seed?
Script:          teams/05-architecture/harness/train_week2.py at 71bc0fb, with the TSAI Gate 2 speed fixes and the C3 scoring patch linked below
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime_fast.yaml --resolution ./inputs/resolution.yaml --tokenizer-release frozen-c3 --tokenizer ./inputs/tokenizer_c3.json --byte-table ./inputs/raw_table_c3_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout_v1.jsonl --heldout-sources ./inputs/heldout_v1_sources.jsonl --heldout-sha256 ./inputs/heldout_v1.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1235 --out ./out/frozen-c3-muon-1235
Config:          teams/05-architecture/configs/arms/exp2_muon.yaml, runtime_fast.yaml and TSAI's t2m1 resolution (staged as ./inputs/resolution.yaml)
Inputs:          Same Gate 2 train.jsonl (TSAI-confirmed SHA-256 prefix 267c33bf), original heldout_v1 with its source map/checksum/report, frozen C3 tokenizer and matching raw P32 table
Hardware:        1 GPU with native BF16 support
Max time:        90 minutes requested, matching the EXP-2 job
Precision:       bf16
Measures:        Final val/bpb, val/nll_nats, val/utf8_bytes, val/encoded_utf8_bytes, scored tokens, per-slice and grouped BPB, completed steps, finite loss and gradient norm, step and wall time, data_load_seconds from manifest.json
Expected result: 1,221 completed steps and BPB on the original heldout_v1 bytes. Report frozen BPB minus 1.6601 at seed 1235. No direction assumed.
Outputs:         ./out/frozen-c3-muon-1235/{manifest.json,summary.json,metrics.jsonl,losses.txt,total_losses.txt}, 50 MB or less in total. Retain the checkpoint on the job machine.
Test log:        teams/05-architecture/jobs/evidence/2026-11-15-frozen-c3-muon/smoke.md
```

## Source and staging

- Start from [71bc0fb](https://github.com/theschoolofai/era-v5-lab/commit/71bc0fbb99fbe5e90d8a09055b7622010e8ab23f) and apply TSAI's Gate 2 implementation from [#441](https://github.com/theschoolofai/era-v5-lab/pull/441), followed by the [C3 scoring patch](evidence/2026-11-15-frozen-c3-muon/c3-original-byte-bpb.patch). Use the staged `runtime_fast.yaml`. Record the effective source and runtime hashes. Disable `G5_DOCUMENT_CACHE_DIR` for this comparison because the current cache assumes token bytes equal original bytes. Stage everything before running offline.
- TSAI confirmed seed `1235` and old-tokenizer `val/bpb: 1.6601`. Use the matching manifest from the Gate 2 evidence page to verify the resolved optimizer, attention, data, and batch settings. Use `t2m1` as supplied by TSAI and record the resolved microbatch from the manifest.
- TSAI will stage the same Gate 2 `train.jsonl` (SHA-256 starts `267c33bf`), `runtime_fast.yaml`, and the `t2m1` resolution, then apply the C3 scoring patch on top of the pinned speed fixes after reviewing #474. Verify the full staged training digest against the Gate 2 manifest. Preflight the staged inputs with the frozen tokenizer. Use the repository's original `heldout_v1` data, sources, checksum and report, and verify the old run used the same holdout hash.
- For the original C3 setup, use tokenizer SHA-256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3` and raw P32 table content SHA-256 `fc5e5f8ffacbe93ecdedc276661edfd43ed9a13621eb4a68166ef80e24e88f9b`. Build the table offline with `python teams/04-ke2/src/build_tables.py --tokenizer ./inputs/tokenizer_c3.json --pos-dims 32 --out ./out/c3-tables`. Verify the embedded tokenizer and raw table content hashes. Stage the resulting raw table for the run.

## Scoring and reporting

Use the unchanged `heldout_v1` text for both runs. C3 normalizes inside the tokenizer. The harness checks its token bytes against that normalized text, while total and per-slice BPB divide by the original source byte counts. The full holdout has 1,059 documents and 3,775,551 original UTF-8 bytes. The 74 changed documents remain in the score. Reuse the old seed's original score as directed by TSAI. Report the matched delta as frozen BPB minus 1.6601, with the three-seed mean 1.6607 as context. A timeout before step 1,221 is `INCOMPLETE_NOT_A_RESULT`.

After applying the C3 patch, run the targeted original-vs-encoded-byte BPB regression from the repository root:

```bash
python -m unittest discover -s teams/05-architecture/tests -p test_week2_scoring.py -k test_frozen_c3_bpb_uses_original_bytes -v
```

The original request included `data_load_seconds` for building the training and held-out windows after file hashing. The completed tokenizer comparison reports BPB.
