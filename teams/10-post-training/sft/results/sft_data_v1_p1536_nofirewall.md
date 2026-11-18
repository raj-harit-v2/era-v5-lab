> Availability: p1536 OCR-2 shards 4-69 were built and checked, then discarded in the requested no-keep-pack pass. They require rebuilding into TSAI storage before training. This remains a partial SFT mix.

# SFT data v1 with p1536 (work-order task 1), 16-17 Nov 2026

Machine-readable record: `sft_data_v1_p1536_manifest.json`, written by `../sft_v1_manifest.py --tokenizer p1536` from the
p1536 admission summaries (`sft_v1_admission_p1536/`), conversion records (`sft_v1_records_p1536/`), the OCR-2 pack
manifest (`ocr2_pack_v1_p1536_manifest.json`), the loss-mask reports (`sft_v1_mask_checks_p1536/`), the length tables
(`sft_v1_lengths_p1536/`) and the OCR-2 effort-tier report. No row text or id in any of them.

Why: the instructor told G10 on 16 Nov to rebuild SFT data v1 with p1536 (TSAI froze it on 15 Nov), rerun render and
pack, re-check the effort tiers and keep the C3 pack as a record. The C3 version stays unchanged:
`sft_data_v1_c3.md`, `sft_data_v1_c3_manifest.json`.

## Scope (unchanged from C3)

In the pack: OCR-2 (Code), Dolly (General), dolly-t (Indic). Not in the pack: Proofs (decontam covers 3 of 287 parts;
its C3 records are listed, the p1536 rebuild belongs to its job request) and math-v2 (not built). No TSAI-reserves set
is in scope until admitted (BLOCKED B1).

## Per set, C3 → p1536

| Set | Rows C3 | Rows p1536 | Tokens C3 | Tokens p1536 | Change | Longest (p1536) | Loss mask (p1536, real rows) |
|---|---:|---:|---:|---:|---:|---:|---|
| OCR-2 | 418,496 | 418,496 | 2,661,029,931 | 2,661,573,319 | +0.02% | 29,846 | 0 violations |
| Dolly | 15,007 | 15,007 | 2,921,023 | 2,922,204 | +0.04% | 5,664 | 0 violations |
| dolly-t | 10,541 | 10,541 | 1,951,624 | 1,795,934 | -7.98% | 6,899 | 0 violations |

Same rows: the kept-id lists of Dolly and dolly-t are sha256-identical to C3, and OCR-2's train and held-out ids are
identical shard by shard. Conversions compared row by row (Dolly, dolly-t; `sft_v1_p1536_conversion_compare.json`):

| Set | Rows | Same id, same order | Text identical | Spans identical | Tier identical | Tokens p1536 / C3 |
|---|---:|---:|---:|---:|---:|---:|
| Dolly | 15,011 | 15,011 | 15,011 | 15,011 | 15,011 | 1.0004 |
| dolly-t | 10,541 | 10,541 | 10,541 | 10,541 | 10,541 | 0.9202 |

Decontamination: re-run on the p1536 outputs because the admission step needs a record bound to the new file hash. The
scan reads text only; Dolly and dolly-t text is identical for every id, OCR-2 text differs only in the effort line of
flipped rows. Result: flagged ids identical to C3 in every set (Dolly 4, dolly-t 0, OCR-2 115,040), 0 canaries.

Effort tiers: Dolly and dolly-t are 1k in every row under both tokenizers (no trace). OCR-2:
35 of 542,043 rendered rows change tier (35 up, 0 down), 31 in the training pack
(`ocr2_pack_v1_p1536.md`).

## Context length under p1536

A row fits a context of L tokens when its whole length (system line, prompt, reasoning, answer and markers) is at most L.
A row that does not fit is counted as lost: cutting it removes the answer and the closing `<|im_end|>`, which is the
supervised end of the turn. (`tokens_if_truncated` in the tables gives the cut-at-L total for comparison.)

Per set (cells: rows that fit / tokens in rows that fit):

| Set | Area | Rows | Tokens | Length p50 / p90 / max | ≤ 2,048 | ≤ 4,096 | ≤ 8,192 | ≤ 32,768 |
|---|---|---:|---:|---|---|---|---|---|
| OCR-2 | Code | 418,496 | 2,661,573,319 | 5,004 / 13,638 / 29,846 | 18.6% / 4.0% | 42.1% / 15.1% | 69.9% / 40.9% | 100.0% / 100.0% |
| Dolly | General | 15,007 | 2,922,204 | 123 / 393 / 5,664 | 99.8% / 96.4% | 100.0% / 98.8% | 100.0% / 100.0% | 100.0% / 100.0% |
| dolly-t | Indic | 10,541 | 1,795,934 | 126 / 318 / 6,899 | 99.9% / 97.6% | 100.0% / 99.6% | 100.0% / 100.0% | 100.0% / 100.0% |

Per #391 area (tokens in rows that fit, and the share of the area's admitted tokens):

| Area | ≤ 2,048 | ≤ 4,096 | ≤ 8,192 | ≤ 32,768 |
|---|---|---|---|---|
| Code | 107,704,700 (4.0%) | 402,061,048 (15.1%) | 1,089,358,137 (40.9%) | 2,661,573,319 (100.0%) |
| Agentic | empty | empty | empty | empty |
| Tool use | empty | empty | empty | empty |
| Indic | 1,753,374 (97.6%) | 1,789,035 (99.6%) | 1,795,934 (100.0%) | 1,795,934 (100.0%) |
| General | 2,817,925 (96.4%) | 2,887,014 (98.8%) | 2,922,204 (100.0%) | 2,922,204 (100.0%) |
| Safety | empty | empty | empty | empty |

Mix shares against #391 at each length (share of the fitting tokens, then fill against #391 with Code as the anchor):

| Area | #391 | Share ≤2k | ≤4k | ≤8k | ≤32k | Fill ≤2k | ≤4k | ≤8k | ≤32k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Code | 35% | 95.93% | 98.85% | 99.57% | 99.82% | 100.00% | 100.00% | 100.00% | 100.00% |
| Agentic | 25% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| Tool use | 15% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| Indic | 15% | 1.56% | 0.44% | 0.16% | 0.07% | 3.80% | 1.04% | 0.38% | 0.16% |
| General | 7% | 2.51% | 0.71% | 0.27% | 0.11% | 13.08% | 3.59% | 1.34% | 0.55% |
| Safety | 3% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

**At a 2,048-token context, 18.6% of the code rows and 4.0% of the code tokens survive**
(77,944 rows, 107,704,700 tokens). Dry run 1 of the capstone model uses a 2,048-token context
(`work/fable-research-2026-11-15/WORKING_PLAN.md` section 12, D7). Dolly and dolly-t barely move at 2,048, so a short
context also shifts the mix: Code's share of the fitting tokens falls while General and Indic rise. TSAI confirmed 32,768 as the provisional SFT admission limit on 16 Nov. The 2,048 column is diagnostic only; longer rows are not excluded from admission for failing that diagnostic.

## Area budget against #391 (32,768, all admitted rows)

| Area | Share | Admitted tokens (p1536) | Needed at the Code anchor | Fill |
|---|---:|---:|---:|---:|
| Agentic | 25% | 0 | 1,901,123,799 | 0.00% |
| Code | 35% | 2,661,573,319 | 2,661,573,319 | 100.00% |
| General | 7% | 2,922,204 | 532,314,664 | 0.55% |
| Indic | 15% | 1,795,934 | 1,140,674,280 | 0.16% |
| Safety | 3% | 0 | 228,134,856 | 0.00% |
| Tool use | 15% | 0 | 1,140,674,280 | 0.00% |

As in C3, the admitted sets cannot form the #391 mix: Agentic, Tool use and Safety are empty and Indic and General are
far below their share until B1 (reserves admission) and B6 (Proofs decontam) are ruled.

## Reproduce

```
python sft/sft_v1_records.py full --set <set> --tokenizer <p1536 tokenizer.json> --tokenizer-label p1536 --revisions-json <pins> \
    --out-dir <private>/full --record-dir sft/results/sft_v1_records_p1536 --threads 2
python sft/decontam_run.py --set <set> --input <concatenated plain parts> --out-dir <private>/decontam/<set> --drop-clean
python sft/sft_v1_admit.py --record sft/results/sft_v1_records_p1536/<set>.full.record.json --parts-dir <private>/full/<set> \
    --decontam-record <private>/decontam/<set>/<set>.record.json --out-dir <private>/admit --summary sft/results/sft_v1_admission_p1536/<set>.admission.json
python sft/check_pack_rows.py --pack <private>/full/<set>/<set>.part*.jsonl.gz --tokenizer <p1536> --report sft/results/sft_v1_mask_checks_p1536/<set>.mask_check.json
python sft/sft_v1_lengths.py --set <set> --area <area> --rows <parts or OCR-2 row stats> [--keep-ids <kept ids> | --status pack] \
    --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b --out sft/results/sft_v1_lengths_p1536/<set>.json
python sft/sft_v1_manifest.py --tokenizer p1536 --out sft/results/sft_data_v1_p1536_manifest.json
```
