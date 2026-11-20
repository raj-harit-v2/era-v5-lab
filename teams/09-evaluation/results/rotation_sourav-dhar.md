# G9 week 3 rotation: decontamination and canary check of two shards (sourav-dhar)

Checked on **17 November 2026** at TSAI main `8de78eced899111ddea295d6822d024e3c6faecc`. Shards assigned in the G9 shard post (17 Nov), from TSAI's p1536 shard list (sample-v0, `dataset_version: sample`). `results/decontam_shards.md` remains the main report for all 41 shards.

## R1: result per shard

| shard_id | payload_sha256 | docs scanned | docs flagged | set_sha256 (fingerprints v2, full set) | canary hits |
|---|---|---:|---:|---|---:|
| `code-js-ts-train-000000` | `61d72a9aa9c8078e9e5a621fe497244fb7699dbe855bf8793a2b0631a23e605a` | 85,508 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | 0 |
| `ind-ta-sangraha-v-train-000000` | `418b46986e796f806d520b883091af93be976a068554b81026f7096417b455d7` | 6,795 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | 0 |

- **Download:** the `.bin`, `.idx.npy` and `.docs.parquet` of both shards have the sha256 their manifests give (`payload_sha256`, `index_sha256`, `sample_metadata_sha256`).
- **Decode:** `decode_shard.py` accepted both shards: manifest, header, index, metadata and tokenizer checks passed. Tokenizer p1536 (sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`). code-js-ts: 85,508 documents, 58,203,242 tokens; ind-ta-sangraha-v: 6,795 documents, 4,497,005 tokens.
- **Decontamination:** `decontam_check.py` with the full set (no `--benchmarks`, `--tags` or `--exclude`): 0 of 85,508 and 0 of 6,795 documents flagged.
- **Canary scan:** `canary_scan.py`, 4 canaries (era-v5-lab, gpqa_diamond, hle, terminal_bench_2): 0 documents with a canary in either shard.

## R2: hits

None. No document in either shard was flagged, so there is no benchmark item ID, doc_id or offset to report.

## Commands

```bash
D=teams/09-evaluation/decontam
python -m pytest $D/tests -q    # 145 passed, 2 skipped
for s in code-js-ts-train-000000 ind-ta-sangraha-v-train-000000; do
  python $D/decode_shard.py <shards>/$s.bin --tokenizer <p1536>/tokenizer.json --out <local-dir>
  python $D/decontam_check.py <local-dir>/$s.text.parquet
  python $D/canary_scan.py <local-dir>/$s.text.parquet
done
```

All exit codes were 0. Environment: Windows, Python 3.13.12, tokenizers 0.23.3, pyarrow 26.0.1, numpy 2.5.4. The decoded `.text.parquet` files hold document text and stay local; nothing here contains item text, document text or download links.

## Task 2 shards (19 Nov)

Four shards from the task 2 split (Team 9 lead post, 18 Nov 2026), as a second check of `results/decontam_shards.md`. Same chain and table as R1: `decode_shard.py` (p1536) → `decontam_check.py` (fingerprints v2, full set) → `canary_scan.py`.
Repo commit `ecb9a27` (TSAI main). Tokenizer: frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`.
Fingerprint set: v2, `set_sha256 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, scope `full set`.

| shard_id | payload_sha256 | docs scanned | flagged | canary hits | set_sha256 |
|---|---|---:|---:|---:|---|
| `code-java-train-000000` | `d885478b8a77ebfec35d9525d35a2f479e38f2b475f1167215c64b2ec5bec2dd` | 62,421 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `en-fineweb-edu-train-000000` | `6625fc47c89e34bf2242a2c747c7e1f9b3583234e45e13e3a653b265007aca07` | 53,444 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-hi-hplt-train-000000` | `e7e357d21beceacab190959591e68e9b00e24729fd098b87be0a28c4cdf95d46` | 8,386 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-te-sangraha-s-train-000000` | `fbc93236d63888dd04421090847c98831ae033234908474e97713b87bb33bea9` | 4,419 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |

Decode details:

| shard_id | tokens | tokenizer (decoder label) | split | dataset_version |
|---|---:|---|---|---|
| `code-java-train-000000` | 56,003,499 | `p1536 e6b93a93a605` | train | sample |
| `en-fineweb-edu-train-000000` | 52,995,687 | `p1536 e6b93a93a605` | train | sample |
| `ind-hi-hplt-train-000000` | 8,090,716 | `p1536 e6b93a93a605` | train | sample |
| `ind-te-sangraha-s-train-000000` | 4,781,160 | `p1536 e6b93a93a605` | train | sample |

- **Download:** the `.bin`, `.idx.npy`, `.docs.parquet` and quality report of each shard have the sha256 their manifests give; docs and tokens are the manifests' `doc_count` and `token_count`.
- **Agrees with `results/decontam_shards.md`** (#641): the same payload_sha256, docs and tokens for all four, and 0 flagged, 0 canary hits there too.
- **Hits for R2:** none. All four shards returned `flagged 0 (0.00%) by benchmark {}` on the full v2 set, so there is no benchmark item ID, doc_id or offset to report. Canary scan: 4 canaries (`era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2`), 0 hits on all four.
- `python -m pytest teams/09-evaluation/decontam/tests -q` at `ecb9a27`: 145 passed, 2 skipped. All exit codes were 0. Environment: Windows, Python 3.13.12, tokenizers 0.23.3, pyarrow 26.0.1, numpy 2.5.4.

Decoded `.text.parquet` files hold document text and stay local; nothing here contains item text, document text or download links.
