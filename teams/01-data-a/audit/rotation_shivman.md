# Rotation check, shivman

Week 3 rotation in Team 01 Data A. The task is to check 2 tokenized shards for manifest fields, hashes, and token counts, and to file each problem as an issue.

Checked on 14 Nov 2026 against main `3af7741b48b0e171fc5199511ee3d193e5c1c74c`.

The repository has one tokenized shard, `teams/01-data-a/shards/sample/code-go-train-000000`. A second tokenized shard is not on main and not in an open pull request. This file checks the shard that is present. It does not claim that two shards were checked. The missing shard is issue 448.

## code-go-train-000000

The manifest uses schema `shard-v1`. Every field in `shard_manifest_v1.template.json` is present and filled.

| Check | Result |
|---|---|
| Manifest file sha256 | `0b062310577feec1d38ff7aa538f7b880bd85226d826040c4646811e62959f87`, the same value as `sample/README.md` |
| Index sha256 | Recomputed `d808fcda4116f03d8017c4c6ade92c8914a64a2df5c3a530d447b92f6ada8ce0`, matches `index_sha256` |
| Quality report sha256 | Recomputed `5ecae0dbc4f3c9c82f7c3277bde45212d12a903927d3babc7aa44103102d307e`, matches `quality_report_sha256` |
| Cleaning pipeline sha256 | Recomputed `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589`, matches `cleaning_pipeline_sha256` |
| Dump sha256 | Recomputed `bfd2e8bea7d866e221295699c625fd3591b1008a2a9ddc17250681f861175045`, matches `sample/README.md` |
| Index | int64, shape `(272,)`, starts at 0, ends at 262032, strictly increasing |
| Documents | 271, equal to the index length minus 1, equal to `doc_count` |
| Tokens | 262032, equal to the last index entry and to the sum of the document lengths. Shortest document 41 tokens, longest 12079 |
| EOS | 130822 |
| Tokenizer | `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3`, the frozen C3 hash named in `shard_format_v1.md` |
| Decontamination set | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, equal to `f2_set_sha256` in `cleaning_pipeline.json` |
| Payload size | 1049152, equal to 1024 + 4 × 262032 |
| Layout | `brahmic_u32_v2+doc_index`, `uint32`, split `train` |
| Writer commit | `5255556c7fc4e824efc0680c994da34c1c6f2125`, the `created_by` value, dated 12 Nov 2026 |

The `.bin` and the `.docs.parquet` are not in the repository. `payload_sha256` is `a9f5e861508679e774a38d3c3af16454bd3c956c96504c9b9ea2e533eda450ed` and `sample_metadata_sha256` is `215004216f384089c59baf2e666787df7288d12c6366c88863f5db82402e7e44`. Both are the values already written in the manifest and in `sample/README.md`. They were not recomputed from bytes.

`cleaning_pipeline.json` records `dedup` as null. This sample was written before a dedup version was set.

## Problem filed

No field in the published shard disagreed with the files in git. The two-shard task is unfinished because the second shard is not in the repository. That is issue 448.