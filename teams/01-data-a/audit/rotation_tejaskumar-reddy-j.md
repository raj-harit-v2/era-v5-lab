# Data A rotation audit — tejaskumar-reddy-j

Checked on **17 November 2026** against TSAI main `6614178d2bf0d1ae526e8f0cf67498cc523f456c`. Owner: Tejaskumar Reddy J (`TEJASKUMAR-REDDY-J`).

R1: verify the two assigned shards from TSAI's **p1536 tokenizer sample-v0** bundle (downloaded from the 16 Nov download TSV), and decode 20 documents per assigned shard. R2: record and link each problem. Report structure follows [#540](https://github.com/theschoolofai/era-v5-lab/pull/540) and [#502](https://github.com/theschoolofai/era-v5-lab/pull/502).

**These are sample-v0 shards.** This is sample-bundle integrity evidence, not first-training-shard verification.

## Result

| Shard | Pack | Documents | Tokens, EOS included | Checks |
|---|---|---:|---:|---|
| `code-go-train-000001` | `code-go` | 20,213 | 20,255,694 | 57 PASS / 1 FAIL / 0 NOT CHECKED |
| `sci-finepdfs-train-000000` | `sci-finepdfs` | 5,993 | 39,470,275 | 57 PASS / 1 FAIL / 0 NOT CHECKED |

The only failed check on each shard is the shared `cleaning_pipeline.json` recording `dedup: null`. This reproduces [issue #503](https://github.com/theschoolofai/era-v5-lab/issues/503). The issue was still open without a TSAI disposition when checked, so the observation stays FAIL. No duplicate issue was opened. All checked artifact hashes, payload/index counts, EOS boundaries, source metadata, quality-report accounting and the 20-document decodes agree.

## Method and reproducibility

Used Keshava's `check_shard.py` from [#482](https://github.com/theschoolofai/era-v5-lab/pull/482), now on main at [`teams/01-data-a/audit/check_shard.py`](check_shard.py) (checker SHA-256 `196c20ff70f7bdd6551a4a54dd3df1d6c5647e4d510a32276cd64bae24f6f007`; byte-identical to #482's commit `f0716023f972fabdb55885c76399dd8d51747633`). The [reproducer](rotation_tejaskumar-reddy-j/reproduce.py) adds the assigned-pack/sample scope, source-row/exclusion consistency and writer-history checks of #540, and the decode.

Frozen p1536 tokenizer bytes were independently hashed: `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`. Its 356 marked-special IDs were read directly from that file.

**Decode (20 documents per shard).** 20 documents spread evenly over each shard, first and last included (positions 0, 1,064, 2,128, … 20,212 for code-go; 0, 315, 631, … 5,992 for sci-finepdfs). Each document's IDs are read from the `.bin` at its index offsets and decoded with the frozen p1536 tokenizer. Checked per document: it ends with EOS 130822; the decoded text has no U+FFFD replacement character; re-encoding the decoded text gives the same IDs; the decoded length equals the `n_chars` recorded in `.docs.parquet`. The JSON evidence keeps only positions, doc IDs, counts and a SHA-256 of each decoded text, never the text.

Environment: Python 3.12.7, NumPy 1.26.4, PyArrow 21.0.0, tokenizers 0.20.3. Checks read local downloaded artifacts without modifying them. JSON evidence contains metadata, IDs, counts and hashes.

Run from this repository root (paths in `<...>` are local authorized inputs):

```bash
python teams/01-data-a/audit/rotation_tejaskumar-reddy-j/reproduce.py \
  --input <downloaded-shard-folder> \
  --tokenizer <p1536-folder>/tokenizer.json \
  --repo . \
  --out teams/01-data-a/audit/rotation_tejaskumar-reddy-j
```

Exit code **1** is expected for this bundle because the dedup-version check fails; missing checks are never counted as PASS. Per-shard run times were 4.153 s and 4.011 s. The checkout's `clean.py` hash (`22d818c72c9f…`) matches the version recorded in the bundle.

## code-go-train-000001

Pack `code-go`; split `train`; schema `shard-v1`; lane `code`; language `go`; script `Latn`; domain `code`. This is the second `code-go` shard: it holds `code-go_part-00001_clean.parquet` (rows 0–20,224); `code-go-train-000000` holds part 00000.

| Artifact | Recomputed SHA-256 | Comparison |
|---|---|---|
| `code-go-train-000001.json` | `32905229e516b346b9ea84ebec696d6e8ce26085cc24f718c1b13949d19b0626` | Recorded identity; no independent expected manifest hash supplied |
| `code-go-train-000001.bin` | `36430989fd7f5caf0f4e22ab1a88b730ca3b901eec537a5ab286d4b3c766fadd` | Matches manifest |
| `code-go-train-000001.idx.npy` | `f0c1311278c2032422e6cc601c74d6b3f7f8ad729cc2ea15daa7e2ca3378503f` | Matches manifest |
| `code-go-train-000001.docs.parquet` | `c86f78f0ed6dfb253f3f8ebba16dd98768bf5efa0d37060d3ed7b58148be7078` | Matches manifest |
| `code-go-train-000001.quality_report.json` | `d370e1a29fa5710a7f2590c27c03f2d133e95a3ecd95fa5d552747878e48c2c9` | Matches manifest |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` | Matches manifest |

| Check | Observed | Result |
|---|---|---|
| Manifest | All template fields present, no extras/placeholders; assigned sample/train scope | PASS |
| Payload layout | little-endian uint32; 81,023,800 bytes = 1,024 + 4 × 20,255,694 | PASS |
| Header | magic 20261025; version 2; 20,255,694 tokens; reserved header entries zero | PASS |
| Index | int64; 20,214 entries; starts at 0, ends at 20,255,694; positive lengths | PASS |
| Document metadata | 20,213 rows; unique IDs; token lengths match index; source rows ordered and unique | PASS |
| Source | `code-go_part-00001_clean.parquet`; source-row gaps equal excluded count | PASS |
| Quality accounting | 20,225 rows read = 20,213 kept + 12 excluded | PASS |
| Exclusions | {'secret': 12, 'empty': 0, 'special': 0, 'roundtrip': 0}; excluded IDs unique and absent from kept metadata | PASS |
| Document token lengths | 5–34,758, EOS included | PASS |
| Tokenizer/EOS | Frozen p1536; every document ends with 130822; no special ID inside documents; all IDs below 131072 | PASS |
| F2 provenance | Manifest fingerprint-set hash agrees with shared pipeline metadata and frozen v2 reference | PASS |
| Writer | `0064f81d57ef47e22d8fa5f42d96c99089a98ce4`; ancestor of audited TSAI main | PASS |
| Decode, 20 documents (25,656 tokens) | 20/20 end with EOS; 0 U+FFFD; 20/20 re-encode to the same IDs; 20/20 decoded length = `n_chars` | PASS |
| Dedup provenance | Shared pipeline metadata contains `dedup: null` | FAIL; #503 |

Detailed expected/observed results: [code-go-train-000001.checks.json](rotation_tejaskumar-reddy-j/code-go-train-000001.checks.json).

## sci-finepdfs-train-000000

Pack `sci-finepdfs`; split `train`; schema `shard-v1`; lane `science`; language `en`; script `Latn`; domain `sci`.

| Artifact | Recomputed SHA-256 | Comparison |
|---|---|---|
| `sci-finepdfs-train-000000.json` | `659ff75ecb86c4625e445d3211c316a1322083336158deb0de4163b447dda21f` | Recorded identity; no independent expected manifest hash supplied |
| `sci-finepdfs-train-000000.bin` | `e95a44b141ec04314968a54bc44e48183861fd4591197c862553a9f6d2968585` | Matches manifest |
| `sci-finepdfs-train-000000.idx.npy` | `7a290cbf1835fda071697c040d341a7db4fe06ac7597970bc5b0a36c90c29e3d` | Matches manifest |
| `sci-finepdfs-train-000000.docs.parquet` | `5cab0da0405d6e903caabfaa0d9b04d6bc32cc7d79a8d363ec1c7cb1a2af891b` | Matches manifest |
| `sci-finepdfs-train-000000.quality_report.json` | `f655095bf5872eecf092595b8941df82b7ffb8b4a77c0696ce05c52d452df5cc` | Matches manifest |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` | Matches manifest |

| Check | Observed | Result |
|---|---|---|
| Manifest | All template fields present, no extras/placeholders; assigned sample/train scope | PASS |
| Payload layout | little-endian uint32; 157,882,124 bytes = 1,024 + 4 × 39,470,275 | PASS |
| Header | magic 20261025; version 2; 39,470,275 tokens; reserved header entries zero | PASS |
| Index | int64; 5,994 entries; starts at 0, ends at 39,470,275; positive lengths | PASS |
| Document metadata | 5,993 rows; unique IDs; token lengths match index; source rows ordered and unique | PASS |
| Source | `sci-finepdfs_part-00000_clean.parquet`; source-row gaps equal excluded count | PASS |
| Quality accounting | 5,997 rows read = 5,993 kept + 4 excluded | PASS |
| Exclusions | {'secret': 4, 'empty': 0, 'special': 0, 'roundtrip': 0}; excluded IDs unique and absent from kept metadata | PASS |
| Document token lengths | 15–1,122,846, EOS included | PASS |
| Tokenizer/EOS | Frozen p1536; every document ends with 130822; no special ID inside documents; all IDs below 131072 | PASS |
| F2 provenance | Manifest fingerprint-set hash agrees with shared pipeline metadata and frozen v2 reference | PASS |
| Writer | `0064f81d57ef47e22d8fa5f42d96c99089a98ce4`; ancestor of audited TSAI main | PASS |
| Decode, 20 documents (55,569 tokens) | 20/20 end with EOS; 0 U+FFFD; 20/20 re-encode to the same IDs; 20/20 decoded length = `n_chars` | PASS |
| Dedup provenance | Shared pipeline metadata contains `dedup: null` | FAIL; #503 |

Detailed expected/observed results: [sci-finepdfs-train-000000.checks.json](rotation_tejaskumar-reddy-j/sci-finepdfs-train-000000.checks.json).

## Coverage and findings

Each complete payload was checked for token range, special IDs and document-ending EOS; counts and hashes were recomputed from bytes. Manifest hashes identify the downloaded JSON but are not separately authenticated against an external manifest-hash list.

The decode covers 20 documents per shard, not every document; the byte-level checks above cover every document. Decoded text was checked for round-trip consistency, not read for cleaning quality: cleaning harm is the daily audit (task 5).

Original cleaned Parquet parts, raw source documents and the F2 fingerprint payload were not supplied for this audit. Their provenance references were checked for consistency, rather than recomputed or rescanned. Training admission, cleaning harm and G9 contamination clearance are separate checks.

The longest `sci-finepdfs` document is 1,122,846 tokens. The writer never splits a document and the shard stays within 2^26 tokens, so this is expected and not a defect. Writer exclusions marked secret-like were 12 / 20,225 documents (0.06%) for code-go and 4 / 5,997 (0.07%) for sci-finepdfs. Both are fully accounted for. The quality of the exclusion decisions was not assessed from the unavailable original texts.

R2: reproduced #503 on both assigned shards; linked the existing issue. No additional integrity defect was observed. No signed URLs, downloaded payloads, tokenizer bytes or document text are included.
