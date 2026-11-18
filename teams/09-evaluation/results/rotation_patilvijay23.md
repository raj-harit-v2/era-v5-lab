# G9 Week 3 rotation — patilvijay23

- Inputs: TSAI p1536 sample-v0 shards released 16 November 2026 (`dataset_version: sample`).
- Source commit: `87323846b325997ea2c21737c7816f950b8f1a26`.
- Run date: 17 November 2026 (America/New_York / EST).
- Environment: Linux (Ubuntu on WSL), Python 3.12.12, tokenizers 0.23.3, pyarrow 25.0.0, numpy 2.5.0, pytest 9.2.0.
- Tests: 146 passed, 1 skipped (test_clean_docs skipped: `set ERA_CLEAN_DOCS to a Parquet pack`), 1 warning in 78.37s (anyio uses the deprecated pytest `CallSpec2` import).
- Tokenizer: frozen p1536.
- Tokenizer SHA256: `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`.
- Fingerprints: v2, full set, normalizer g9-v2.
- set_sha256: `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`.

## R1 — shard checks

| Shard ID | Payload SHA256 | Docs decoded | Docs scanned | Docs flagged | Canary hits |
|---|---|---:|---:|---:|---:|
| `en-dclm-train-000000` | `1fccdcc4c15bb22ea564c8d3f1850582abd8b60e6c504386ee84308f6ee074de` | 45,032 | 45,032 | 0 | 0 |
| `math-megamath-train-000000` | `ff5a213f47981243e42a31e3ffe6733e276181ef0e8cfb7c581f77bea6e22e57` | 17,232 | 17,232 | 0 | 0 |

- **Decode:** `decode_shard.py` accepted both shards with exit code 0: manifest, header, index, metadata, document boundaries, and tokenizer checks passed.
  - `en-dclm-train-000000`: `dataset_version: sample`, `split: train`, 45,032 documents, 53,960,422 tokens, tokenizer `p1536 e6b93a93a605`.
  - `math-megamath-train-000000`: `dataset_version: sample`, `split: train`, 17,232 documents, 33,979,879 tokens, tokenizer `p1536 e6b93a93a605`.
- **Decontamination:** `decontam_check.py` with full set (no `--benchmarks`, `--tags`, or `--exclude`; `--max-items 1000000`): 0 of 45,032 (0.00%) and 0 of 17,232 (0.00%) documents flagged.
- **Canary scan:** `canary_scan.py` scanned 4 canaries (`era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2`): 0 documents with canary hits across both shards.

## R2 — hits

Both shards had zero flagged documents and zero canary hits, so R2 has no hits to report.

| Shard ID | Benchmark item / canary ID | Document ID | Character offset |
|---|---|---|---:|
| *(no hits)* | — | — | — |

## Reproduction

```bash
# Replace these local path placeholders before running.
G9_SHARDS_DIR="/ABSOLUTE/PATH/TO/SHARDS"
G9_TOKENIZER="/ABSOLUTE/PATH/TO/p1536/tokenizer.json"
G9_OUT_DIR="/ABSOLUTE/PATH/TO/LOCAL/DECODED/OUTPUT"
D=teams/09-evaluation/decontam
mkdir -p "$G9_OUT_DIR"

# Test suite (enabling real-shard decoder test)
ERA_SHARD="$G9_SHARDS_DIR/en-dclm-train-000000.bin" \
ERA_TOKENIZER="$G9_TOKENIZER" \
python -m pytest "$D/tests" -q -rs

# Verification loop for assigned shards; stop on any command failure.
for s in en-dclm-train-000000 math-megamath-train-000000; do
  python "$D/decode_shard.py" "$G9_SHARDS_DIR/$s.bin" \
    --tokenizer "$G9_TOKENIZER" \
    --out "$G9_OUT_DIR" || break

  python "$D/decontam_check.py" "$G9_OUT_DIR/$s.text.parquet" \
    --fingerprints teams/09-evaluation/fingerprints/v2 \
    --max-items 1000000 || break

  python "$D/canary_scan.py" "$G9_OUT_DIR/$s.text.parquet" \
    --fingerprints teams/09-evaluation/fingerprints/v2 || break
done

```

All exit codes were 0. The decoded `.text.parquet` files hold document text and stay local; nothing here contains raw item text, document text, or download links.

## Findings and limitations

All decode, decontamination, and canary checks completed successfully with zero failures and zero flags. A zero-hit result means no matches were found by this fingerprint/canary set; it does not establish that the shards contain no paraphrased contamination or content outside the set's coverage.
