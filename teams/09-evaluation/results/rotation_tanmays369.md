# Week 3 rotation check, R1/R2 (`tanmays369`)

Team 9 (Evaluation) week-3 rotation. Decontamination check of 2 training shards with fingerprints v2.

- **Assigned by:** Team 9 lead (`rahulni`), G9 shard post, 17 Nov 2026.
- **Shards:** `en-nemotroncc-train-000000`, `math-finemath-train-000000`.
- **Chain:** `decode_shard.py` (p1536) → `decontam_check.py` (fingerprints v2, full set) → `canary_scan.py`.
- **Repo commit:** `8de78ec` (main, 17 Nov).
- **Tokenizer:** frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` (Gate 3 freeze, verified before use).
- **Fingerprint set:** v2, `set_sha256 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, scope `full set`.

## R1 — per shard

| shard_id | payload_sha256 | docs scanned | docs flagged | canary hits | set_sha256 |
|---|---|---:|---:|---:|---|
| `en-nemotroncc-train-000000` | `3b64c48e320d38c58ae3e8114cdb26fabb71f387131ddebd5453184128ae2ce0` | 65,284 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `math-finemath-train-000000` | `6e84f270a53bcdd225bb2a6cd6cd053b5e8e74c3cdf93d3aa80a2606cc9597da` | 28,088 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |

Decode details:

| shard_id | tokens | tokenizer (decoder label) | split | dataset_version |
|---|---:|---|---|---|
| `en-nemotroncc-train-000000` | 50,343,044 | `p1536 e6b93a93a605` | train | sample |
| `math-finemath-train-000000` | 38,582,010 | `p1536 e6b93a93a605` | train | sample |

## R2 — each hit

**No hits.** Both shards scanned with the full v2 set (no `--tags`, no `--benchmarks`, no `--exclude`) returned `flagged 0 (0.00%) by benchmark {}`. No benchmark item ID, document ID or offset to report.

Canary scan: 4 canaries checked (`era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2`), 0 hits on both shards.

## Notes

- Decoded `.text.parquet` files were kept local and are not committed (they hold document text; eval firewall section 4). Deleted after the run.
- Wall time: the full-set check took about 450 s of user time on `en-nemotroncc` and 200 s on `math-finemath`. The canary scan took under 3 s per shard.
- The `decontam_check.py` stderr line for every run named the full set and the same `set_sha256`, so the two results are comparable.

## Task 2 shards — 18 Nov

Four shards from the task 2 split (Team 9 lead post, 18 Nov 2026). Same chain and table as R1:
`decode_shard.py` (p1536) → `decontam_check.py` (fingerprints v2, full set) → `canary_scan.py`.
Repo commit `8de78ec`. Tokenizer: frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`.
Fingerprint set: v2, `set_sha256 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, scope `full set`.

| shard_id | payload_sha256 | docs scanned | flagged | canary hits | set_sha256 |
|---|---|---:|---:|---:|---|
| `code-python-train-000000` | `bf6c275f296566cb88eb5e732238c1744c3294cbc8a47502a1ebfb06685b7900` | 53,221 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `en-nemotroncc-synth-train-000001` | `2d041dc03bfbaabb3b6be8c43abe8122d012a0006ef1325f6fea57513f3eda34` | 49,008 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-hi-sangraha-s-train-000000` | `4b92b39b427566809d1653f1b81b35b274c2a6c7de99c3b4f8a9d5b017bb5561` | 7,467 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-kn-fw2-train-000000` | `7224b101435879f73f07b17e5156919aa225376d1636bb622cb4ec80540a8126` | 7,735 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |

Decode details:

| shard_id | tokens | tokenizer (decoder label) | split | dataset_version |
|---|---:|---|---|---|
| `code-python-train-000000` | 60,537,332 | `p1536 e6b93a93a605` | train | sample |
| `en-nemotroncc-synth-train-000001` | 16,961,507 | `p1536 e6b93a93a605` | train | sample |
| `ind-hi-sangraha-s-train-000000` | 5,988,971 | `p1536 e6b93a93a605` | train | sample |
| `ind-kn-fw2-train-000000` | 4,737,714 | `p1536 e6b93a93a605` | train | sample |

**Hits for R2:** none. All four shards returned `flagged 0 (0.00%) by benchmark {}` on the full v2 set, so there is no benchmark item ID, document ID or offset to report. Canary scan: 4 canaries checked (`era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2`), 0 hits on all four.

Decoded `.text.parquet` files stayed local and were not committed (eval firewall section 4); they were deleted after the run.
