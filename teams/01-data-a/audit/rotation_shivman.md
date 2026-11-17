# Rotation check, shivman

Week 3 rotation in Team 01 Data A. The task is to check 2 tokenized shards for manifest fields, hashes, and token counts, and to file each problem as an issue.

## Sample check (merged in #449)

Checked on 14 Nov 2026 against main `3af7741b48b0e171fc5199511ee3d193e5c1c74c`.

The repository then had one tokenized sample shard, `teams/01-data-a/shards/sample/code-go-train-000000` (frozen C3). That check is unchanged and stays as the sample record from pull request 449. Issue 448 recorded that a second shard was not on main at that time.

## Follow-up: two p1536 shards (this update)

Checked on 16 Nov 2026 against main `917fafb2e42f`.

TSAI published 41 tokenized shards from sample v0 with frozen tokenizer p1536 (`e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`). I picked two shard ids from that list and checked every published file for each shard (`.bin`, `.idx.npy`, `.docs.parquet`, `.json`, `.quality_report.json`, plus the shared `cleaning_pipeline.json`). Download URLs are not recorded in this file.

| | Shard id | Pack | Docs | Tokens |
|---|---|---|---:|---:|
| 1 | `ind-ta-sangraha-v-train-000000` | ind-ta-sangraha-v | 6795 | 4497005 |
| 2 | `ind-kn-fw2-train-000000` | ind-kn-fw2 | 7735 | 4737714 |

## ind-ta-sangraha-v-train-000000

Pack `ind-ta-sangraha-v`, split `train`, schema `shard-v1`. Read from the TSAI p1536 sample-v0 shard bundle (download links not recorded here).

| Check | Result |
|---|---|
| Manifest file sha256 | `102e55601de11d559b854ba6bb74e72d8827df285ac5a264f52ec4bc9a4a7a4e` |
| Payload sha256 | Recomputed `418b46986e796f806d520b883091af93be976a068554b81026f7096417b455d7`, matches `payload_sha256` |
| Payload size | `17989044` bytes = 1024 + 4 × `4497005` |
| Index sha256 | Recomputed `392a803c9e2854ac733ff28d89da66e6cfce8f081ffe1d252cba5bdb6421862d`, matches `index_sha256` |
| Index | int64, shape `(6796,)`, starts at 0, ends at `4497005`, strictly increasing |
| Documents | `6795`, equal to the index length minus 1, equal to `doc_count` |
| Tokens | `4497005`, equal to the last index entry and to the sum of the document lengths |
| Document metadata sha256 | Recomputed `97bccf7e5e31c9af5482ef9474cb352b3a37c60da902c1ef6a80ed96a9582645`, matches `sample_metadata_sha256` |
| Quality report sha256 | Recomputed `111af26f12f3a101c7f21b3c97107484d0ff06c15b603867bb59697ce66485b8`, matches `quality_report_sha256` |
| Cleaning pipeline sha256 | Recomputed `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589`, matches `cleaning_pipeline_sha256` |
| EOS | `130822`; every document ends with it; no other special id inside a document |
| Tokenizer | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, the Gate 3 frozen p1536 hash |
| Decontamination set | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, equal to `f2_set_sha256` in `cleaning_pipeline.json` |
| Header | magic `20261025`, version `2`, header token count equals `token_count` |
| Writer commit | `0064f81d57ef47e22d8fa5f42d96c99089a98ce4` |
| Automated checks | 44 PASS, 1 FAIL, 0 NOT CHECKED |

Failed check(s): cleaning_pipeline records a dedup version (observed None).
## ind-kn-fw2-train-000000

Pack `ind-kn-fw2`, split `train`, schema `shard-v1`. Read from the TSAI p1536 sample-v0 shard bundle (download links not recorded here).

| Check | Result |
|---|---|
| Manifest file sha256 | `c683d5be3aaf7223ca56ebdf609277abfe840ae81e064130af09588cac19a890` |
| Payload sha256 | Recomputed `7224b101435879f73f07b17e5156919aa225376d1636bb622cb4ec80540a8126`, matches `payload_sha256` |
| Payload size | `18951880` bytes = 1024 + 4 × `4737714` |
| Index sha256 | Recomputed `830c5bd4630098f51105d72c78fa4905064e0073d35f0f220b183b35d64a06c3`, matches `index_sha256` |
| Index | int64, shape `(7736,)`, starts at 0, ends at `4737714`, strictly increasing |
| Documents | `7735`, equal to the index length minus 1, equal to `doc_count` |
| Tokens | `4737714`, equal to the last index entry and to the sum of the document lengths |
| Document metadata sha256 | Recomputed `102a8f05625b9b5e050224f1cb3cb5c0ed165ce3ccb9fb0b9047c858772fb15f`, matches `sample_metadata_sha256` |
| Quality report sha256 | Recomputed `19b8327257d3e642c492b5eb0bd2a1b089e03f3d4a36bd10b5ca56cf880a5508`, matches `quality_report_sha256` |
| Cleaning pipeline sha256 | Recomputed `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589`, matches `cleaning_pipeline_sha256` |
| EOS | `130822`; every document ends with it; no other special id inside a document |
| Tokenizer | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, the Gate 3 frozen p1536 hash |
| Decontamination set | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, equal to `f2_set_sha256` in `cleaning_pipeline.json` |
| Header | magic `20261025`, version `2`, header token count equals `token_count` |
| Writer commit | `0064f81d57ef47e22d8fa5f42d96c99089a98ce4` |
| Automated checks | 44 PASS, 1 FAIL, 0 NOT CHECKED |

Failed check(s): cleaning_pipeline records a dedup version (observed None).

## Problems filed (R2)

1. `cleaning_pipeline.json` for this p1536 sample-v0 bundle records `dedup` as null on both shards (same observation as the earlier sample on main). Filed as issue #503.
