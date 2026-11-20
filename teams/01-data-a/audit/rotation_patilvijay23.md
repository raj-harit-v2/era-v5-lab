# Data A rotation audit — patilvijay23

Checked on **16 November 2026** against TSAI main `23d7902a39c7cc78e1e3c19f25aeaee7a5355697`. Owner: Vijay Patil (`patilvijay23`).

R1: verify the two assigned shards from TSAI’s **p1536 tokenizer sample-v0** bundle. R2: record and link each problem. Report structure follows [Shivanshu’s merged PR #502](https://github.com/theschoolofai/era-v5-lab/pull/502).

## Result

| Shard | Pack | Documents | Tokens, EOS included | Checks |
|---|---|---:|---:|---|
| `en-dclm-train-000000` | `en-dclm` | 45,032 | 53,960,422 | 53 PASS / 1 FAIL / 0 NOT CHECKED |
| `math-megamath-train-000000` | `math-megamath` | 17,232 | 33,979,879 | 53 PASS / 1 FAIL / 0 NOT CHECKED |

The sole failed check on each shard is the shared `cleaning_pipeline.json` recording `dedup: null`. This reproduces [issue #503](https://github.com/theschoolofai/era-v5-lab/issues/503). The issue remained open without a TSAI disposition when checked; the observation remains FAIL. No duplicate issue was opened. All checked artifact hashes, payload/index counts, EOS boundaries, source metadata and quality-report accounting agree.

## Method and reproducibility

Used Keshava’s existing `check_shard.py` from [PR #482](https://github.com/theschoolofai/era-v5-lab/pull/482), pinned to commit `f0716023f972fabdb55885c76399dd8d51747633`; checker SHA-256 `b3b47f445439755a9d39616301e1a74cb08de02582c9cf5f82e499873cc7eb40`. The generic checker is referenced rather than duplicated in this PR. The accompanying [reproducer](rotation_patilvijay23/reproduce.py) adds assigned-pack/sample scope, source-row/exclusion consistency and writer-history checks.

Frozen p1536 tokenizer bytes were independently hashed: `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`. Its 356 marked-special IDs were read directly from that file. The audit does not decode documents; the core decoding task has a separate branch and report.

Environment: Python 3.12.3, NumPy 2.5.4, PyArrow 26.0.1. Checks read local downloaded artifacts without modifying them. JSON evidence contains metadata, IDs, counts and hashes.

Obtain the checker at the pinned PR #482 commit above, then run from this repository root (paths below are placeholders for local authorized inputs):

```bash
python3 -I teams/01-data-a/audit/rotation_patilvijay23/reproduce.py \
  --input <downloaded-shard-folder> \
  --tokenizer <p1536-folder>/tokenizer.json \
  --checker <PR482-checkout>/teams/01-data-a/audit/check_shard.py \
  --repo . \
  --out teams/01-data-a/audit/rotation_patilvijay23
```

Exit code **1** is expected for this bundle because the dedup-version check fails; missing checks are never counted as PASS. Per-shard run times were 3.863 s, 2.082 s. The checkout’s cleaner hash matches the version recorded in the bundle.

## en-dclm-train-000000

Pack `en-dclm`; split `train`; schema `shard-v1`; lane `general_language`; language `en`; script `Latn`; domain `english`.

| Artifact | Recomputed SHA-256 | Comparison |
|---|---|---|
| `en-dclm-train-000000.json` | `aea60298ee0c7eed31b498c49f709d7f2fb96d01896388d8af2ec28a9240331a` | Recorded identity; no independent expected manifest hash supplied |
| `en-dclm-train-000000.bin` | `1fccdcc4c15bb22ea564c8d3f1850582abd8b60e6c504386ee84308f6ee074de` | Matches manifest |
| `en-dclm-train-000000.idx.npy` | `2cb4f8478781d20a73c43db1dbf5426ec85a7784f1fd3e4cbb60d443bfd6891d` | Matches manifest |
| `en-dclm-train-000000.docs.parquet` | `3193a184ca4f89a3ef8d13ababaaa576d034fe767fed85269bd0322f5bb15bf7` | Matches manifest |
| `en-dclm-train-000000.quality_report.json` | `ce3729e776105cd4ab4c82496d8913fa4aef794eb8e52342e5c6d3807faa9dea` | Matches manifest |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` | Matches manifest |

| Check | Observed | Result |
|---|---|---|
| Manifest | All 28 template fields present, no extras/placeholders; assigned sample/train scope | PASS |
| Payload layout | little-endian uint32; 215,842,712 bytes = 1,024 + 4 × 53,960,422 | PASS |
| Header | magic 20261025; version 2; 53,960,422 tokens; reserved header entries zero | PASS |
| Index | int64; 45,033 entries; starts at 0, ends at 53,960,422; positive lengths | PASS |
| Document metadata | 45,032 rows; unique IDs; token lengths match index; source rows ordered and unique | PASS |
| Source | `en-dclm_part-00000_clean.parquet`; source-row gaps equal excluded count | PASS |
| Quality accounting | 45,336 rows read = 45,032 kept + 304 excluded | PASS |
| Exclusions | {'secret': 304, 'empty': 0, 'special': 0, 'roundtrip': 0}; excluded IDs unique and absent from kept metadata | PASS |
| Document token lengths | 25–102,670, EOS included | PASS |
| Tokenizer/EOS | Frozen p1536; every document ends with 130822; no special ID inside documents; all IDs below 131072 | PASS |
| F2 provenance | Manifest fingerprint-set hash agrees with shared pipeline metadata and frozen v2 reference | PASS |
| Writer | `0064f81d57ef47e22d8fa5f42d96c99089a98ce4`; ancestor of audited TSAI main | PASS |
| Dedup provenance | Shared pipeline metadata contains `dedup: null` | FAIL; #503 |

Detailed expected/observed results: [en-dclm-train-000000.checks.json](rotation_patilvijay23/en-dclm-train-000000.checks.json).

## math-megamath-train-000000

Pack `math-megamath`; split `train`; schema `shard-v1`; lane `math`; language `en`; script `Latn`; domain `math`.

| Artifact | Recomputed SHA-256 | Comparison |
|---|---|---|
| `math-megamath-train-000000.json` | `ccdae49682b19c7f724620406911d02c157eb94b14463b9eb2463e27b0318214` | Recorded identity; no independent expected manifest hash supplied |
| `math-megamath-train-000000.bin` | `ff5a213f47981243e42a31e3ffe6733e276181ef0e8cfb7c581f77bea6e22e57` | Matches manifest |
| `math-megamath-train-000000.idx.npy` | `1fbbfcfc8a8e19f160f5bbfc8b4902a017455421572232b3b55c0e6ed98fca8f` | Matches manifest |
| `math-megamath-train-000000.docs.parquet` | `7f11583f97a20c2904cb583a24981d04c4d4b002b3809e79447bd09bbff8e770` | Matches manifest |
| `math-megamath-train-000000.quality_report.json` | `538f893f47a2eb805fb27e7b11ba8d5890acd16d3359a254d00ec57b1eb6b33c` | Matches manifest |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` | Matches manifest |

| Check | Observed | Result |
|---|---|---|
| Manifest | All 28 template fields present, no extras/placeholders; assigned sample/train scope | PASS |
| Payload layout | little-endian uint32; 135,920,540 bytes = 1,024 + 4 × 33,979,879 | PASS |
| Header | magic 20261025; version 2; 33,979,879 tokens; reserved header entries zero | PASS |
| Index | int64; 17,233 entries; starts at 0, ends at 33,979,879; positive lengths | PASS |
| Document metadata | 17,232 rows; unique IDs; token lengths match index; source rows ordered and unique | PASS |
| Source | `math-megamath_part-00000_clean.parquet`; source-row gaps equal excluded count | PASS |
| Quality accounting | 17,555 rows read = 17,232 kept + 323 excluded | PASS |
| Exclusions | {'secret': 323, 'empty': 0, 'special': 0, 'roundtrip': 0}; excluded IDs unique and absent from kept metadata | PASS |
| Document token lengths | 10–518,496, EOS included | PASS |
| Tokenizer/EOS | Frozen p1536; every document ends with 130822; no special ID inside documents; all IDs below 131072 | PASS |
| F2 provenance | Manifest fingerprint-set hash agrees with shared pipeline metadata and frozen v2 reference | PASS |
| Writer | `0064f81d57ef47e22d8fa5f42d96c99089a98ce4`; ancestor of audited TSAI main | PASS |
| Dedup provenance | Shared pipeline metadata contains `dedup: null` | FAIL; #503 |

Detailed expected/observed results: [math-megamath-train-000000.checks.json](rotation_patilvijay23/math-megamath-train-000000.checks.json).

## Coverage and findings

Each complete payload was checked for token range, special IDs and document-ending EOS; counts and hashes were recomputed from bytes. Manifest hashes identify the downloaded JSON but are not separately authenticated against an external manifest-hash list.

Original cleaned Parquet parts, raw source documents and the F2 fingerprint payload were not supplied for this audit. Their provenance references were checked for consistency, rather than recomputed or rescanned. This is sample-bundle integrity evidence; training admission, cleaning harm and G9 contamination clearance are separate checks.

Writer exclusions marked secret-like were 304 / 45,336 documents (0.67%) for en-dclm and 323 / 17,555 (1.84%) for math-megamath. Both are fully accounted for and do not indicate an unexplained manifest/count mismatch. The quality of the exclusion decisions was not assessed from the unavailable original texts.

R2: reproduced #503 on both assigned shards; linked the existing issue. No additional integrity defect was observed. No signed URLs, downloaded payloads, tokenizer bytes or document text are included.
