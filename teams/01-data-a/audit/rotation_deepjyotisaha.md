# Rotation check, deepjyotisaha

Week 3 rotation in Team 01 Data A (R1 and R2). The task is to check 2 tokenized shards for manifest fields, hashes,
and token counts, and to file each problem as an issue.

**These are sample-v0 shards**: TSAI's p1536 bundle of 16 Nov (41 shards from the 48 tokenizer sample v0 train parts,
after `clean.py` and F2). The two shards were assigned in Vijay's table in the Data A group (17 Nov). The files were
downloaded from TSAI's link list; no download link is recorded here.

Checked on 17 Nov 2026 against main `23d7902a39c7cc78e1e3c19f25aeaee7a5355697`.

## Result

| | Shard | Documents | Tokens | Result |
|---|---|---:|---:|---|
| 1 | `code-python-train-000000` | 53,221 | 60,537,332 | 11 of 12 checks PASS; 1 FAIL (`dedup: null`, issue 503) |
| 2 | `en-fineweb-edu-train-000000` | 53,444 | 52,995,687 | 11 of 12 checks PASS; 1 FAIL (`dedup: null`, issue 503) |

Every recomputed file hash, size, header, index, token count and manifest field matches the manifest. Both shards use
the frozen p1536 tokenizer, and every document ends with EOS 130822. The one FAIL is the shared
`cleaning_pipeline.json`, whose `dedup` field is null; it is already issue 503, so no new issue is filed (R2).

## How the checks were run

Three tools, all reading only IDs, counts and hashes (no document text is in this file):

- Team 9's `teams/09-evaluation/decontam/decode_shard.py` (#458, #484) with the p1536 `tokenizer.json` (its sha256
  recomputed: `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`). It checks the header, size, index,
  docs.parquet, manifest hashes, counts, EOS, token ids and special ids, then decodes every document. Both shards passed
  and decoded fully (53,221 and 53,444 documents).
- `audit/check_shard.py` from Keshava's #482, with `--expect-tokenizer p1536`: 45 PASS, 1 FAIL, 0 NOT CHECKED on each
  shard. The one FAIL is `dedup: null`.
- A small extra check for the manifest fields and hashes `decode_shard.py` does not cover (every template field filled,
  quality report and cleaning pipeline sha256, decontamination set, writer commit): 5 of 5 PASS on each shard.

## The checks

The rules come from `teams/01-data-a/shards/shard_format_v1.md` and `shard_manifest_v1.template.json`.

| # | Check | How |
|---|---|---|
| 1 | Manifest fields | Every field of `shard_manifest_v1.template.json` is present and filled; `schema_version` is `shard-v1` |
| 2 | Payload sha256 | sha256 of the `.bin` bytes (header included) equals `payload_sha256` |
| 3 | Payload size | `.bin` size equals `payload_bytes` and 1,024 + 4 × `token_count` |
| 4 | Header | magic `20261025`, version `2`, header token count equals `token_count` |
| 5 | Index sha256 | sha256 of the `.idx.npy` equals `index_sha256` |
| 6 | Index | int64, starts at 0, strictly increasing, last entry equals `token_count`; length − 1 equals `doc_count` |
| 7 | Document metadata | sha256 of the `.docs.parquet` equals `sample_metadata_sha256`; one row per document; sum of `n_tokens` equals `token_count` |
| 8 | Quality report | sha256 equals `quality_report_sha256`; rows read = documents in the shard + documents left out |
| 9 | Tokenizer | `tokenizer_sha256` is the frozen p1536 hash `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` (TSAI's Gate 3 notice, 16 Nov, moved the frozen tokenizer from C3 to p1536, #414) |
| 10 | EOS | `eos_token_id` is `130822`; every document ends with it; no special id inside a document |
| 11 | Decontamination set | `decontam_set_sha256` equals `f2_set_sha256` in the shard's `cleaning_pipeline.json`, and its sha256 equals `cleaning_pipeline_sha256` |
| 12 | Cleaning pipeline | `cleaning_pipeline.json` records the cleaner (`clean_py_sha256`) and a dedup version; `created_by` names a commit |

## Shard 1: `code-python-train-000000`

Pack `code-python`, language `python`, domain `code`, lane `code`, split `train`, dataset version `sample`.

| # | Check | Manifest | Recomputed | Match |
|---|---|---|---|---|
| 1 | Manifest fields | 28 template fields | 28 present, none empty, none extra; `shard-v1` | PASS |
| 2 | Payload sha256 | `bf6c275f296566cb88eb5e732238c1744c3294cbc8a47502a1ebfb06685b7900` | same | PASS |
| 3 | Payload size | 242,150,352 | 242,150,352 = 1,024 + 4 × 60,537,332 | PASS |
| 4 | Header | token count 60,537,332 | magic 20261025, version 2, 60,537,332, rest zeros | PASS |
| 5 | Index sha256 | `55bbde3a87e44c50b4566933f12583633101c165cc91a082cc8c444802e5b27d` | same | PASS |
| 6 | Index | 53,221 documents | int64, 53,222 entries, starts at 0, ends at 60,537,332 | PASS |
| 7 | Document metadata | `18ea16dadefc38f0256179f029980c58d2f499c96962d3bc4d9e3096fb9293a3` | same; 53,221 rows, unique doc_ids, n_tokens = index lengths | PASS |
| 8 | Quality report | `410256c92da98eb3d204812dff5035c16c9115172e12113dc84e58e79846f9f4` | same; 53,259 rows read = 53,221 + 38 left out (31 secret-like, 7 special) | PASS |
| 9 | Tokenizer | `e6b93a93a60520d7…25a64b` | p1536 | PASS |
| 10 | EOS | 130822 | 53,221 of 53,221 documents end with EOS; no special id inside a document | PASS |
| 11 | Decontamination set | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | equals `f2_set_sha256`; pipeline file sha256 `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` matches | PASS |
| 12 | Cleaning pipeline | `created_by` `0064f81d57ef47e22d8fa5f42d96c99089a98ce4` | `clean_py_sha256` `22d818c7…99179` matches `clean.py` on main; **`dedup` is null** | **FAIL** (issue 503) |

## Shard 2: `en-fineweb-edu-train-000000`

Pack `en-fineweb-edu`, language `en`, domain `english`, lane `general_language`, split `train`, dataset version `sample`.

| # | Check | Manifest | Recomputed | Match |
|---|---|---|---|---|
| 1 | Manifest fields | 28 template fields | 28 present, none empty, none extra; `shard-v1` | PASS |
| 2 | Payload sha256 | `6625fc47c89e34bf2242a2c747c7e1f9b3583234e45e13e3a653b265007aca07` | same | PASS |
| 3 | Payload size | 211,983,772 | 211,983,772 = 1,024 + 4 × 52,995,687 | PASS |
| 4 | Header | token count 52,995,687 | magic 20261025, version 2, 52,995,687, rest zeros | PASS |
| 5 | Index sha256 | `8302b6298e67f07be6e1a0ea5218c33da2bcba7b510e9bdd7b2bbc41d0f72c18` | same | PASS |
| 6 | Index | 53,444 documents | int64, 53,445 entries, starts at 0, ends at 52,995,687 | PASS |
| 7 | Document metadata | `13845ffb8fa6e8bc0fe91d58dde62c4d812fba1ed63d6673a8bee351594cfefe` | same; 53,444 rows, unique doc_ids, n_tokens = index lengths | PASS |
| 8 | Quality report | `03775cec876ddec067b4e8921f77587fa3c49585e727c61c15cf14a686fd9bfd` | same; 53,538 rows read = 53,444 + 94 left out (94 secret-like) | PASS |
| 9 | Tokenizer | `e6b93a93a60520d7…25a64b` | p1536 | PASS |
| 10 | EOS | 130822 | 53,444 of 53,444 documents end with EOS; no special id inside a document | PASS |
| 11 | Decontamination set | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | equals `f2_set_sha256`; pipeline file sha256 `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` matches | PASS |
| 12 | Cleaning pipeline | `created_by` `0064f81d57ef47e22d8fa5f42d96c99089a98ce4` | `clean_py_sha256` `22d818c7…99179` matches `clean.py` on main; **`dedup` is null** | **FAIL** (issue 503) |

## Problems (R2)

| Problem | Shards | Issue |
|---|---|---|
| `cleaning_pipeline.json` records `dedup: null` for the sample-v0 bundle | both | Already **issue 503** (shared by every sample-v0 shard; also found in #482, #476, #502). Not filed again. |

**Note for the lead (not a manifest problem):** the shard writer left out documents it judged secret-like: 31 of 53,259
code-python documents (0.06%) and 94 of 53,538 en-fineweb-edu documents (0.18%), plus 7 code-python documents for a
special id. They are listed in each quality report and the counts reconcile, so the manifests are correct; whether these
removals are intended is for Data A to judge (Keshava noted the same on #482).
