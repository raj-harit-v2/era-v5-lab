# Week 3 rotation check, R1/R2 (`truesrini`)

Team 9 (Evaluation) week-3 rotation. Decontamination check of 2 training shards with fingerprints v2.

- **Assigned by:** Team 9 lead, G9 shard post, 17 Nov 2026.
- **Shards:** `en-fineweb-edu-train-000001`, `ind-sa-fw2-train-000000` (TSAI's p1536 sample-v0 shard list, 16 Nov).
- **Chain:** `decode_shard.py` (p1536) → `decontam_check.py` (fingerprints v2, full set) → `canary_scan.py`.
- **Repo commit:** `ecb9a27d` (main, 18 Nov).
- **Tokenizer:** frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` (Gate 3 freeze, verified before use).
- **Fingerprint set:** v2, `set_sha256 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, scope `full set`.
- **Download check:** the `.bin`, `.idx.npy` and `.docs.parquet` of both shards match the `payload_sha256`, `index_sha256` and `sample_metadata_sha256` in their manifests.

## R1 — per shard

| shard_id | payload_sha256 | docs scanned | docs flagged | canary hits | set_sha256 |
|---|---|---:|---:|---:|---|
| `en-fineweb-edu-train-000001` | `f1b97344614f7f54b407e60602204fd8313b83565de817cdf75b2cd6990a55ef` | 17725 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-sa-fw2-train-000000` | `a6d8546c5f48e7e1388edc441b48b409e29be870b79fd61ee6624f930ba7dab5` | 5667 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |

Decode details:

| shard_id | tokens | tokenizer (decoder label) | split | dataset_version |
|---|---:|---|---|---|
| `en-fineweb-edu-train-000001` | 17662417 | `p1536 e6b93a93a605` | train | sample |
| `ind-sa-fw2-train-000000` | 13940676 | `p1536 e6b93a93a605` | train | sample |

## R2 — each hit

**No hits.** Both shards scanned with the full v2 set (no `--tags`, no `--benchmarks`, no `--exclude`) returned `flagged 0 (0.00%) by benchmark {}`. No benchmark item ID, document ID or offset to report.


Canary scan: 4 canaries checked (`era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2`), 0 hits on both shards.

## Notes

- Decoded `.text.parquet` files were kept local and are not committed (they hold document text; eval firewall section 4). They are deleted after the run.
- The `decontam_check.py` stderr line for every run named the full set and the same `set_sha256`, so the two results are comparable.
- Tests: `pytest teams/09-evaluation/decontam/tests -q` on the commit above: 145 passed, 2 skipped.
- Environment: Windows, Python 3.12.10, tokenizers 0.23.3, pyarrow 26.0.1, numpy 2.5.5.
