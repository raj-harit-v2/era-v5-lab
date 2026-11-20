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

## Task 2 shards

Additional four-shard assignment from G9 on 18 November 2026. The original R1/R2 results above are unchanged.

- Run date: 18 November 2026 (America/New_York / EST).
- Source commit: `17fd544c57e207aebe6ee692444338c9e18753ea`.
- Environment: Linux (Ubuntu on WSL), Python 3.12.12.
- Tests: **146 passed, 1 skipped, 1 warning in 28.72s**. The real-shard decoder test used `code-rust-train-000000`; `test_clean_docs` skipped because `ERA_CLEAN_DOCS` was not set. The warning is anyio's deprecated pytest `CallSpec2` import.
- Inputs: TSAI p1536 sample-v0 shards (`dataset_version: sample`, `split: train`).
- Frozen p1536 tokenizer SHA256: `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`.
- Fingerprints: v2, full set, normalizer `g9-v2`; `set_sha256`: `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`.

### Results

| Shard ID | payload_sha256 | Docs scanned | Flagged | Canary hits | set_sha256 |
|---|---|---:|---:|---:|---|
| `code-rust-train-000000` | `9468c56cccae9055e00dc2a530be2e1732b4798d1025611bc1ec438c1727278b` | 43,116 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `en-nemotroncc-train-000001` | `a7b14cbbbfc45f81aa1f881c1da97d97d3ce656018073c869435423b61095a42` | 21,912 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-bn-sangraha-v-train-000000` | `dec1b695aca02613d958a232c760f09e77127ba4d680920c1284d8feba8f834d` | 10,112 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-kn-sangraha-s-train-000000` | `41fe68ef433fe8612de02c9b30d846b58597f4e46ee456b806a03355421dce7e` | 5,185 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |

**Total: 80,325 documents, 89,541,757 tokens; 0 flagged documents and 0 canary hits.**

All four decodes completed successfully (exit code 0, `decoded 1 of 1 shard(s)` per invocation), validating manifest hashes, header, index, document metadata, document boundaries and tokenizer compatibility. Decoded document counts matched both scan counts for every shard. Token counts from the decoder:

- `code-rust-train-000000`: 59,530,999 tokens.
- `en-nemotroncc-train-000001`: 16,778,602 tokens.
- `ind-bn-sangraha-v-train-000000`: 8,014,810 tokens.
- `ind-kn-sangraha-s-train-000000`: 5,217,346 tokens.

Each full-set decontamination check and canary scan exited 0. Canary scans checked four canaries (`era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2`). All four flagged-document outputs and all four canary-hit outputs were empty.

### Hits

No hits were found in any of the four Task 2 shards, so there are no benchmark item IDs, document IDs or offsets to report.

### Reproduction

Run from the repository root, replacing the local path placeholders. These checks use the same shared scripts as the original rotation run.

```bash
G9_SHARDS_DIR="/ABSOLUTE/PATH/TO/SHARDS"
G9_TOKENIZER="/ABSOLUTE/PATH/TO/p1536/tokenizer.json"
G9_OUT_DIR="/ABSOLUTE/PATH/TO/LOCAL/TASK2/DECODED/OUTPUT"
D=teams/09-evaluation/decontam
mkdir -p "$G9_OUT_DIR"

ERA_SHARD="$G9_SHARDS_DIR/code-rust-train-000000.bin" \
ERA_TOKENIZER="$G9_TOKENIZER" \
python -m pytest "$D/tests" -q -rs

for s in code-rust-train-000000 en-nemotroncc-train-000001 \
         ind-bn-sangraha-v-train-000000 ind-kn-sangraha-s-train-000000; do
  python "$D/decode_shard.py" "$G9_SHARDS_DIR/$s.bin" \
    --tokenizer "$G9_TOKENIZER" --out "$G9_OUT_DIR" || break
  python "$D/decontam_check.py" "$G9_OUT_DIR/$s.text.parquet" \
    --fingerprints teams/09-evaluation/fingerprints/v2 \
    --max-items 1000000 || break
  python "$D/canary_scan.py" "$G9_OUT_DIR/$s.text.parquet" \
    --fingerprints teams/09-evaluation/fingerprints/v2 || break
done
```

No `--tags`, `--benchmarks` or `--exclude` filters were used; the minimum-hit threshold stayed at its default. Decoded text and raw run artifacts remain local. Zero hits means no matches found by this fingerprint/canary set, subject to the matching limits stated above.
