# SFT data tools: conversion and decontamination

This README covers the tools that turn a candidate SFT set into chat-format v0 rows and check those rows against Team 9's benchmark fingerprints. The OCR-2 admission scripts, the mix inventory and the other records in this folder are listed in the second table below; the SFT probe (`train_probe.py`, `probe_note.md`) has its own note.

## What is here

| File | What it does |
|---|---|
| `convert.py` | Converts one candidate set to chat-format v0 JSONL with a loss mask and a manifest. Every row goes through `chat-format/render.py`. |
| `test_convert.py` | Tests for `convert.py`, on hand-written rows in each set's schema (no real data). |
| `decontam_run.py` | Runs Team 9's `decontam_check.py` and `canary_scan.py` on one set, writes the set without the flagged and canary rows, and writes a record of counts and ids. |
| `decontam_report.py` | Builds `decontam_report.md` from those records. |
| `decontam_pipeline.py` | Runs download, convert and decontam for several sets in parallel, then merges the part records. |
| `test_decontam_run.py` | Tests for `decontam_run.py` and `decontam_report.py`, on a toy fingerprint set built from made-up items. |
| `decontam_report.md` | The result per set: flagged, canary and kept rows, benchmarks hit, and the inputs to reproduce a run. |
| `decontam_kept_rows.md` | Rows in, removed and kept per set for the sets run on every converted row. |
| `sft_v1_worklist.py` | Builds the SFT v1 work list from `convert.py` ADAPTERS, the Stage 1 licence table and `sft_mix_proposal.md`, with the reason each set is in or out and the pinned Hub revisions (`fetch-hf` writes the pins; `results/sft_v1_hf_pins.json` is the committed copy). |
| `sft_v1_records.py` | One set at a time: `run` (first N rows), `full` (whole set, streamed, gzipped parts, disk budgets), `check` (row checks), `verify-local` (staged files against pinned sha256). Refuses any tokenizer but C3. |
| `sft_v1_report.py` | Builds `results/sft_v1_token_records.md` and the JSONL for `mix_inventory.py --c3-records` from the per-set records in `results/sft_v1_records/`. |
| `test_sft_v1_records.py` | Tests for the three scripts, the batched path of `convert.py` and the ledger input. Hand-written rows and a toy tokenizer only. |
| `deletion_tuning.py` | Deletion Tuning mask from arXiv 2611.10866: frozen weight, soft mask, hard mask, Wanda init. |
| `dt_vs_fft.py`, `test_deletion_tuning.py` | Equal-step comparison of Deletion Tuning, LoRA, and full fine-tuning on one synthetic slice. |

The RL sets use the same tools. Their report is `rl/decontam_report.md`.

## Other files in this folder

| Group | Files |
|---|---|
| Proposals | `sft_mix_proposal.md` (area shares 35 / 25 / 15 / 15 / 7 / 3, effort distribution, revision notes to 9 Nov). `max_sequence_tokens_proposal.md` (proposes `max_sequence_tokens = 32768` for the OCR-2 pack, for TSAI's signature at Gate 2). |
| Conversion record | `convert_report.md`: a 1,000-row test on four sets. |
| OpenCodeReasoning-2 (OCR-2) | `source_index.py`, `prepare_ocr2.py`, `run_ocr2.py`, `pack_admission.py`, `ocr2_policy.json`, `ocr2_fixtures.py`. |
| Inventory | `mix_inventory.py` builds `results/eligibility_ledger.jsonl` and `../docs/eligibility_ledger.md`. |
| Tests | `test_*.py` for convert, decontam_run, mix_inventory, ocr2_resume, pack_admission and prepare_ocr2. `verify.sh` re-runs the OCR-2 tests and fails if any is skipped. |
| `results/` | `eligibility_ledger.jsonl`, `ocr2_coverage.md`, `ocr2_full_run.json`, `ocr2_full_run_inputs.tsv`. |

## Convert a set

```bash
python teams/10-post-training/sft/convert.py --set sft-code-codeforces-cots --hf-rows 1000 --out out/codeforces.jsonl
python teams/10-post-training/sft/convert.py --set sft-indic-aya-dataset --input aya_train.parquet --limit 1000 \
    --out out/aya.jsonl --tokenizer tokenizer.json
```

It writes `<out>` and `<out>.manifest.json`.

- The set must have a Stage 1 row in `licences/licence_table.md`. A set marked `excluded`, or missing from the table, is refused. The licence, source, generator model and decision in the manifest come from that row.
- A row that does not fit the chat format is skipped and counted by reason. It is never patched.
- The effort level is the smallest budget (1k, 4k, 16k, 64k) that holds the row's trace. Without `--tokenizer` the token count is an estimate (UTF-8 bytes / 4), and the manifest says so. With `--tokenizer`, each row also gets `input_ids` and a per-token `loss_mask`.
- Source options: `--input` (a local `.parquet` or `.jsonl`), `--hf-rows N` (from the Hugging Face datasets-server) or `--hf-file N` (N rows read from the set's own file in the Hub repo by ranged download; `--file-spec`, `--index-base` and `--roll-mb` are what `decontam_pipeline.py` uses for parallel runs).

### Token records for the SFT v1 mix (C3)

```bash
python teams/10-post-training/sft/sft_v1_worklist.py build --hf-pins teams/10-post-training/sft/results/sft_v1_hf_pins.json --out-json worklist.json --out-md worklist.md
python teams/10-post-training/sft/sft_v1_records.py run --set sft-dolly-15k --rows 1000 --tokenizer tokenizer.json --revisions-json teams/10-post-training/sft/results/sft_v1_hf_pins.json --out-dir out/p1 --record-dir out/records
python teams/10-post-training/sft/sft_v1_records.py full --set sft-dolly-15k --tokenizer tokenizer.json --revisions-json teams/10-post-training/sft/results/sft_v1_hf_pins.json --out-dir out/full --record-dir out/records
```

- `convert.py --revisions-json` reads the Hub files at the pinned commits instead of `main`; `G10_MAX_HUB_BYTES` stops a run that reads more than that many bytes. Rows are tokenised in chunks of 32 through `encode_batch` (the output is byte-identical to one call per row; see `results/sft_v1_token_records.md`). Set `RAYON_NUM_THREADS` to bound the tokenizer's threads.
- The checks in `sft_v1_records.py` accept a decode that differs from the text only by the C3 normaliser (NFC, Malayalam chillu rewrite) and count those rows. They do not claim raw-byte-exact decoding.
- A full output is **converted, not decontaminated, and not a pack**: it can hold rows over 32,768 tokens, it has not been through the decontamination run at the pinned revision, and a held-out id list, if one exists, has not been applied. `TSAI reserves` sets are measurements only.
- `full` keeps no source copy, gzips each finished part and checks that it decompresses to the same bytes, and stops if one set passes `--budget-gb` or everything under `--out-dir` passes `--global-budget-gb` (default 80). `--local-root` reads a staged copy of the Hub repo (`<root>/<dataset id>/<file>`; check it with `verify-local`) and uses no network.

## Recover a completed conversion

`sft_v1_records.py check-parts` checks completed gzip parts while conversion runs. `finalize` verifies the manifest,
all decompressed hashes/CRC, row counts and source-prefix determinism, then aggregates valid stored checks. See
each command's `--help` for required paths. Stored checks bind the gzip/tokenizer hashes, row-check source,
renderer source, effective marker assignments/surfaces, maximum length and NumPy/tokenizers/Python versions.
Keep the checked source and environment fixed during a run. Changed dependencies invalidate the stored checks.

The full Proofs execution used revision `8574a9b516562ca6d5086c36ef64b276ba21871e` and its historical checker key.
`results/sft_v1_proofs_execution_context.json` records the observed dependency context. The broader cache key was
added after that verified run; the completed record retains the key actually used. In a finalized record,
`checks_wall_s` covers cache validation/aggregation and any uncached checks, excluding earlier per-part work.
Conversion metrics unavailable from the original driver stay `null`, rather than being inferred from these times.

## Decontaminate a set

```bash
python teams/10-post-training/sft/decontam_run.py --set sft-code-codeforces-cots --input out/codeforces.jsonl --out-dir decontam_out
python teams/10-post-training/sft/decontam_report.py --records decontam_out --out decontam_out/decontam_report.md
```

Write a trial report to a scratch path as above. `sft/decontam_report.md` is built from the records of all sets with `--sets`, so do not point `--out` at it from a one-set run.

`decontam_run.py` does five things for one set:

1. Runs `decontam_check.py` on the full fingerprint set. It refuses any other scope, and any `set_sha256` other than the pinned one (fingerprints v2, lab PR #280).
2. Runs `canary_scan.py` on the same files. A canary is a leak, never a pass.
3. Writes the set without the flagged and canary documents (`<set>.clean.jsonl` or `.parquet`).
4. Reconciles the counts: rows in = rows kept + rows removed, ids are unique, every flagged id is an input id, and the checker run again on the clean file flags 0.
5. Writes `<set>.record.json` with counts, ids, benchmark item ids, offsets, sha256 values and the hashes of the tools.

Exit code 0 means every check passed (flagged documents may exist: they are removed and recorded). Exit code 1 means a canary was found or a reconciliation check failed: stop using the file and post in G9 with the item or canary id, document id and offset only. Exit code 2 means a tool could not run.

`decontam_report.py` refuses to write when a record failed, when a record has no second pass over its clean file, when the records carry different `set_sha256` values or different Team 9 tool files, or when the `set_sha256` is not the expected one. Use `--sets` to name the sets to include, and `--pending` for sets of the mix that were not run yet.

For several sets at once, `decontam_pipeline.py` converts and checks each downloaded part as it arrives. It writes `progress.log` and `status.txt` in its work folder so a person can watch the run.

## Rules

- **Team 9's tools.** They come from lab main, not from this folder. Point `G10_DECONTAM_TOOLS` at `teams/09-evaluation/decontam` of a lab main checkout that has fingerprints v2 (the report names the commit it used). The folder on an older branch does not have v2, and the tests that need it are skipped.
- **Plain `python`.** Run these scripts with plain `python`, not `python -I`: Team 9's scripts import their neighbours from their own folder.
- **No benchmark text, no document text.** Only counts, document ids, benchmark item ids, character offsets and sha256 values leave these scripts (eval firewall, section 4). Keep the `--out-dir` out of Git: the clean files and the records hold training rows and document ids.
- **A rerun is needed** when Team 9 publishes a new fingerprint set (a different `set_sha256`), and for any set whose rows change.

## Tests

```bash
G10_DECONTAM_TOOLS=<lab main>/teams/09-evaluation/decontam \
  python -m pytest teams/10-post-training/sft/test_convert.py teams/10-post-training/sft/test_decontam_run.py -q
```

The Hub calls in `test_convert.py` are mocked, and `test_decontam_run.py` states that it needs no network. Without `G10_DECONTAM_TOOLS` pointing at a v2 folder, the decontam tests that need Team 9's tools are skipped.

## OCR-2 pack v1 under C3 (14 Nov 2026)

TSAI decided the OCR-2 pack on 14 Nov (G10 group): C3 frozen (eos 130822), `max_sequence_tokens` 32768 provisional for SFT
data v1, the 69,690 Codeforces rows held out of v1, the source repo and revision recorded for TACO, APPS and code_contests,
and rows without a clear source left out. The pack v1 was built under that ruling with C3: `results/ocr2_pack_v1_c3.md` and
`results/ocr2_pack_v1_c3_manifest.json` (418,496 training rows, 8,507 held-out rows, 0 blockers in training mode). It is not
yet reviewed or stored by TSAI, and no model has been fine-tuned on it.

- **Context limit:** 32768 is set in `manifests/ocr2_source_manifest_v1_c3.json`. No row exceeds it (longest 29,829 C3 tokens).
- **Source identity:** taco/apps/code_contests train are `pinned_revision` (repo and revision recorded, every file sha256 equal
  to the Hub object). They are not relabelled `verified`; `diagnostic` still never admits a row.
- **Tokenizer:** the C3 sha256 is approved in `ocr2_policy.json`; the file itself is still not in the repo.
- **Codeforces:** the 69,690 rows stay held under the ruling. 0 are eligible in the pack.
- **Still open:** the quality threshold (the #391 rule, which the policy calls a proposal); the human spot check of the 14
  unclear-source TACO problems; and whether the 2% `heldout_eval_v1` split stays, which is a G10 proposal. Both of the last
  two change the pack hashes if changed. Bytes are stored by TSAI through `../jobs/2026-11-16-ocr2-pack-v1-c3.md`, which is not sent.

This C3 section is kept as a record (TSAI, 15 Nov: C3 work stays valid as a record). SFT data v1 is now built with p1536
(instructor, 16 Nov): `results/ocr2_pack_v1_p1536.md`, `results/sft_data_v1_p1536.md`, rebuild-and-store job
`../jobs/2026-11-17-ocr2-pack-v1-p1536.md`. The lead's evaluation firewall (16 Nov) is applied after the pack stage by
`eval_firewall.py` (record `results/ocr2_eval_firewall_v1.json`); the p1536 manifest before it is kept as
`results/sft_data_v1_p1536_nofirewall_manifest.json`.

> Status as of 12 Nov 2026 (kept from `main`). Where it differs from the 14 Nov section above, the 14 Nov section is current.

## Gate

Workstream "SFT data v1" (1 to 21 Nov, plan sheet). The SFT mix is one of the items TSAI decides at Gate 2 (14 Nov).

## What has been measured (from the committed reports)

- **Decontamination** against Team 9 fingerprints v2, full set (`set_sha256` 2826a3b8...): 34 sets, 18,376,709 rows in, 464,365 removed (2.53%), 17,912,344 kept, 0 canaries. See `decontam_report.md`.
- **OCR-2, all 70 Python shards** (`results/ocr2_coverage.md`, `../docs/eligibility_ledger.md`): raw 1,398,166 rows; 786,190 excluded by policy; 69,690 held; 542,286 joined; 67 rejected by the converter; 542,219 scanned; 115,067 removed; 427,152 kept; **admitted 0**.
- **Kept OCR-2 rows, token lengths** (ledger): p50 5,007, max 29,851; 2,714,970,210 sequence tokens in total.
- **Conversion test:** 1,000 rows each on four sets (`convert_report.md`). No data file is committed.

## What has not been done

- **No SFT run.** No model has been fine-tuned on these rows. No pack is admitted. The ledger counts 34 scanned entries and 0 approved complete training packs.
- **Token records exist for OCR-2 only.** 32 other scanned sets have row counts and no token record (ledger, section 6, item 4).
- **Overlap between OCR-2, OpenCodeReasoning and codeforces-cots** is not measured.
- **Safety share.** The table in the proposal says 3% Safety, but the revision notes say to use 0% Safety until TSAI names an allowed safety set with chat rows.
- **The tests in this folder were not run for this README.** The only run record is whatever the reports above quote.

## Blockers

- **max_sequence_tokens is not set.** The OCR-2 manifest has `max_sequence_tokens` null, so the admission check reports `context_limit_not_set` (Gate 2). `max_sequence_tokens_proposal.md` proposes 32768 and waits for TSAI's signature.
- **Source identity is not verified** for `apps/train`, `code_contests/train` and `taco/train` (`source_identity_not_verified:*`), and those sources are not approved for training. The pack report also lists `set_not_allowed_in_licence_table`, `set_not_allowed_in_policy`, `join_not_in_admission_mode` and `tokenizer_not_approved`.
- **The tokenizer is not in the repo as of 12 Nov.** Gate 2 references sha 15468e66...; `teams/03-tokenizer/` has build scripts and `SHA256SUMS` but no `tokenizer.json` for it. The OCR-2 pack check lists `tokenizer_not_approved`, and `../docs/eligibility_ledger.md` notes that token counts taken before the frozen tokenizer arrives would need a rerun.
- **Codeforces pool: 69,690 `open-r1/codeforces` train rows are held** until the producer revision is settled.

## Reports

- [sft_mix_proposal.md](sft_mix_proposal.md), [max_sequence_tokens_proposal.md](max_sequence_tokens_proposal.md)
- [decontam_report.md](decontam_report.md), [decontam_kept_rows.md](decontam_kept_rows.md)
- [convert_report.md](convert_report.md)
- [results/ocr2_coverage.md](results/ocr2_coverage.md)
- [../docs/eligibility_ledger.md](../docs/eligibility_ledger.md)
