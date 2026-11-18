# SFT data v1 (task 1): what is admissible today, what was applied, what still needs a ruling

Week-3 work order, task 1 (Member B, due Tue 17 Nov): finish SFT data v1 with loss masks from the #391 mix. This note records the steps that needed no new ruling, run on 15 Nov 2026 on a laptop CPU (Apple M1 Pro, 8 cores, 16 GB, shared with other jobs). No dataset text, row id or held-out id is in this file; private outputs stay outside Git.

## 1. Rulings applied (G10 group, checked in the 15 Nov export)

- Tokenizer frozen (C3, eos 130822); `max_sequence_tokens` 32,768 accepted as provisional for SFT data v1 (TSAI).
- OCR-2 pack: hold the 69,690 Codeforces rows; rows without a clear TACO/APPS/code_contests source stay out; keep the 2% held-out split, record the split seed and row ids, finish the 14 source spot checks before the pack is final (TSAI).
- Large files are not committed: script, manifest (sha256, row count) and rebuild recipe go to Git; TSAI stores built files through a job request (TSAI).
- `aya_collection`: 10 subsets usable (TSAI reserves), `templated_hindi_headline` excluded, `templated_hindi_news` pending TSAI (school repo PR #399, mix proposal Area 4 and section 9.3 on `g10-week1-post-training`).

No licence decision of a #391 set differs between this branch, `g10-week3-post-training` (7a3f122) and `g10-week1-post-training` (72d65ef).

## 2. Admission index per set (`sft/sft_v1_admit.py`)

The index drops, from a full C3 conversion: rows flagged by Team 9's full fingerprint set v2 (set_sha256 `2826a3b8…`) or holding a canary, rows in a held-out id list, and rows over 32,768 tokens. It writes the kept-id list privately and a public summary (`sft/results/sft_v1_admission/`).

| Set | Licence | Rows in | Decontam flagged (benchmarks) | Canary | Held-out | Over 32,768 | Rows kept | Tokens kept | Status |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| `sft-dolly-15k` | allowed | 15,011 | 4 (mmlu 2, milu 2) | 0 | 0 (no list) | 0 | 15,007 | 2,921,023 | admissible |
| `sft-indic-indic-align-dolly-t` | allowed | 10,541 | 0 | 0 | 0 (no list) | 0 | 10,541 | 1,951,624 | admissible |
| `sft-math-nemotron-proofs` | allowed | 920,881 | 27 in the 3 parts checked (hle 22, heldout_g5_v1 3, gpqa_diamond 1, livecodebench 1) | 0 | 0 (no list) | 18,661 | 902,194 (provisional) | 9,695,160,211 | decontam pending (3 of 287 parts checked) |
| `sft-code-opencodereasoning-2` | allowed (TSAI admitted) | WP1 pack | in the pack build | 0 | 8,507 rows / 317 families held out | 0 (max 29,829) | 418,496 | see `ocr2_pack_v1.md` | final after the 14 spot checks |

Decontamination of Dolly and dolly-t ran on the whole set: the concatenated parts hash to each record's `content_sha256`, and the clean copy rechecks to 0 flagged. Proofs is 287 parts (106.8 GiB decompressed); one part takes about 6 CPU-minutes on this machine, about 29 CPU-hours for the set, so the full run is the job request `jobs/2026-11-16-sft-v1-proofs-decontam.md` with the local test log next to it. Its over-length count (18,661) is computed from the stored per-part checks bound to each part's gz sha256 and equals the full record.

`sft-math-nemotron-math-v2` (allowed) has no full conversion yet: 50.3 GB of source and about 269 GB of gzip (estimate) do not fit this machine; the tested job request is `jobs/2026-11-14-sft-v1-math-v2-full.md`. Its decontamination and admission index follow the same three commands as the Proofs request.

## 3. Aya policy in the converter

`convert.py` now reads only the 10 usable `aya_collection` subsets, keeps rows whose `language` is one of the ten proposal languages (this drops the 1,156 Urdu rows of `templated_indic_sentiment`) and keeps `source_id` = `<subset>/<source id>`. The prefix record was re-measured on the 10 subsets (`sft_v1_records/sft-indic-aya-collection.record.json`: 1,000 rows, 100 per subset, all checks pass, rerun hash equal). For every usable subset, its first 83 rows convert to the same text, token ids, mask, spans and effort as in the old 12-subset record, so only the subset list, the language filter and the added `source_id` changed. Source counts (datasets-server statistics, current parquet conversion, not the pinned revision): 517,789 rows in the 10 subsets, 516,633 in the proposal languages, of which `templated_telugu_news` is 467,090 (90.4%). The set stays TSAI reserves.

Speed and identity: old (`6fb275e`) and new `convert.py` on the same saved raw inputs (math-v2 300 rows, Proofs 400, agentic-v1 600, commitpackft 1,500), `RAYON_NUM_THREADS=4`, two alternating repetitions: output sha256 identical in all 8 pairs (`6eefdc07…`, `9424620e…`, `4ac0c68d…`, `038744ca…`); wall 18.45/16.93 vs 19.53/16.54 s, 6.87/6.59 vs 6.54/6.62 s, 6.04/6.08 vs 6.65/6.04 s, 1.94/1.72 vs 1.71/1.77 s (before vs after, host shared, so equal within noise). The change adds no per-token work.

## 4. OCR-2 held-out split: seed and row ids (`sft/ocr2_heldout_handoff.py`)

The split has no random seed. `pack_admission.heldout_selector` holds out a problem family when the first 8 bytes of sha256(salt + newline + family key) fall under 0.02 x 2^64, with salt `g10-ocr2-heldout-eval-v1`. The checker recomputes that rule for every listed row and reconciles the private id list with the public manifest: 8,507 rows, 317 families, apps 2,550 / code_contests 1,225 / taco 4,732, per-shard counts equal to the 70 shard entries, id list sha256 `193d589d…d7f1` equal to the manifest. The public summary is `sft/results/ocr2_heldout_v1_handoff.json`; the id list, family list (sha256 `4aee753a…`) and split rule go to TSAI as a private bundle, not to Git.

## 5. Still open (needs a ruling or a TSAI job)

1. Admission of the 19 TSAI-reserves sets of the mix and the 4 held sets (data-rule flags: unknown-generator split, Modified MIT generator, DeepSeek licence rows). Until then their records are measurements.
2. `templated_hindi_news` (CC BY-SA 4.0): TSAI decision.
3. The 14 TACO source spot checks for OCR-2 (176 rows excluded meanwhile).
4. Where the OCR-2 held-out row ids go: the public manifest, or TSAI storage with the hash in Git.
5. Proofs decontamination (job request) and the math-v2 full build (job request).
6. Mix shares and the safety fallback (0% safety / 10% general) in proposal section 9.

## 6. Commands (run from `teams/10-post-training`)

```
python sft/sft_v1_admit.py --record sft/results/sft_v1_records/<set>.full.record.json --parts-dir <private>/full/<set> [--partials <private>/partials/<set>] --decontam-record <private>/decontam/<set>/<set>.record.json --out-dir <private>/admit --summary sft/results/sft_v1_admission/<set>.admission.json
python sft/ocr2_heldout_handoff.py --ids <private>/heldout_eval_v1_ids.PRIVATE.jsonl --bundle-dir <private>/ocr2_heldout_handoff --summary sft/results/ocr2_heldout_v1_handoff.json
python sft/sft_v1_records.py run --set sft-indic-aya-collection --rows 1000 --source-rows 1000 --tokenizer tokenizer.json --revisions-json <pins> --out-dir <private>/p1 --record-dir <records>
```
