# G9 week 3 rotation: decontamination and canary check of two shards (tejaskumar-reddy-j)

Checked on **17 November 2026** at TSAI main `5aed520fd4a4707b64795ed2e722eba368477978`. Shards assigned in the G9 shard post, from TSAI's p1536 shard list (sample-v0, `dataset_version: sample`). `results/decontam_shards.md` remains the main report for all 41 shards.

## R1: result per shard

| shard_id | payload_sha256 | docs scanned | docs flagged | set_sha256 (fingerprints v2, full set) | canary hits |
|---|---|---:|---:|---|---:|
| `code-go-train-000001` | `36430989fd7f5caf0f4e22ab1a88b730ca3b901eec537a5ab286d4b3c766fadd` | 20,213 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | 0 |
| `sci-finepdfs-train-000000` | `e95a44b141ec04314968a54bc44e48183861fd4591197c862553a9f6d2968585` | 5,993 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | 0 |

- **Decode:** `decode_shard.py` accepted both shards: manifest, header, index, metadata and tokenizer checks passed. Tokenizer p1536 (sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`). code-go: 20,213 documents, 20,255,694 tokens; sci-finepdfs: 5,993 documents, 39,470,275 tokens.
- **Decontamination:** `decontam_check.py` with the full set (no `--benchmarks`, `--tags` or `--exclude`): 0 of 20,213 and 0 of 5,993 documents flagged.
- **Canary scan:** `canary_scan.py`, 4 canaries (era-v5-lab, gpqa_diamond, hle, terminal_bench_2): 0 documents with a canary in either shard.

## R2: hits

None. No document in either shard was flagged, so there is no benchmark item ID, doc_id or offset to report.

## Commands

```bash
D=teams/09-evaluation/decontam
python -m pytest $D/tests -q    # 145 passed, 2 skipped
for s in code-go-train-000001 sci-finepdfs-train-000000; do
  python $D/decode_shard.py <shards>/$s.bin --tokenizer <p1536>/tokenizer.json --out <local-dir>
  python $D/decontam_check.py <local-dir>/$s.text.parquet
  python $D/canary_scan.py <local-dir>/$s.text.parquet
done
```

All exit codes were 0. Environment: Python 3.12.7, tokenizers 0.20.3, pyarrow 21.0.0, numpy 1.26.4. The decoded `.text.parquet` files hold document text and stay local; nothing here contains item text, document text or download links.
