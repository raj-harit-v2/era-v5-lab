# Week 3 frozen-tokenizer comparison

**Result:** TSAI's matched T2 Muon run at seed 1235 scored **1.5381 BPB** with p1536, down from **1.6601 BPB** with tokenizer v0. The matched delta is **−0.1220 BPB**. This comparison covers one seed. [TSAI result on PR #474](https://github.com/theschoolofai/era-v5-lab/pull/474#issuecomment-6908490508)

| Run | Seed | Completed steps | Held-out BPB |
| --- | ---: | ---: | ---: |
| Gate 2 tokenizer v0 | 1235 | 1,221 | 1.6601 |
| Gate 3 frozen p1536 | 1235 | 1,221 | 1.5381 |

The old-tokenizer results at seeds 1234 and 1236 were 1.6443 and 1.6777 BPB. The three-seed Gate 2 mean was 1.6607 BPB. The matched delta uses the seed-1235 baseline. [Gate 2 EXP-2 request](https://github.com/theschoolofai/era-v5-lab/pull/354)

## Frozen p1536 group metrics

| Metric | BPB |
| --- | ---: |
| English | 1.9849 |
| Code | 1.9034 |
| Indic mean | 1.3552 |
| Three-group mean | 1.7478 |

The three-group mean weights English, code, and the Indic mean equally. Whole-file BPB uses summed next-token loss divided by log(2) and by the total original UTF-8 bytes.

## Run and scoring provenance

- TSAI ran the T2 `exp2_muon` arm on trainer `71bc0fb` with its Gate 2 speed fixes and the #474 scoring patch, updating the patch's tokenizer pin from C3-s0 to p1536. [TSAI result](https://github.com/theschoolofai/era-v5-lab/pull/474#issuecomment-6908490508) · [Gate 2 trainer diff](https://github.com/theschoolofai/era-v5-lab/pull/441#issuecomment-6880790263)
- TSAI confirmed p1536 tokenizer hash `e6b93a93…a64b` and raw P32 table content hash prefix `21072027…`. The full tokenizer SHA-256 verified locally is `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`. The locally rebuilt table content SHA-256 is `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a`. G5 preflight verified all 131,072 raw table rows with zero truncations. [Team 3 p1536 candidate](https://github.com/theschoolofai/era-v5-lab/pull/414)
- TSAI scored all **1,059 documents** on the original `heldout_v1` text, totaling **3,775,551 UTF-8 bytes**. The local holdout SHA-256 is `21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb`. Validation uses original bytes both overall and per slice. In the normalization-aware scoring path, `train/utf8_bytes` counts encoded training bytes and `val/encoded_utf8_bytes` reports encoded holdout bytes.
- TSAI confirmed the run setup matched the Gate 2 EXP-2 Muon manifest at seed 1235, with two differences: the tokenizer and the scoring patch.

## C3-s0 preflight record

The original #474 request was prepared for C3-s0. Its local preflight found 74 of 1,059 documents changed under tokenizer normalization. The tokenizer's reconstructed bytes matched the normalized text for those documents, and the full holdout contained 3,762,753 bytes after normalization. The preflight and smoke checks established the original-byte scoring path before TSAI switched the job to p1536. [C3-s0 smoke evidence](../../jobs/evidence/2026-11-15-frozen-c3-muon/smoke.md)
