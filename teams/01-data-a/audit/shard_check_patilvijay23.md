> Historical two-shard check. The complete task report is [shard_check.md](shard_check.md).

# Core shard decode check — Vijay Patil

G1 core task 6, checked on **16 November 2026** by Vijay Patil (`patilvijay23`). Coverage: the two assigned **sample-v0** shards below, out of TSAI’s 41-shard bundle. Repository base `23d7902a39c7cc78e1e3c19f25aeaee7a5355697`.

## Result

| Shard | Source pack | Documents in shard | Tokens in shard | Decoded and exact token round-trip |
|---|---|---:|---:|---|
| `en-dclm-train-000000` | `en-dclm` | 45,032 | 53,960,422 | 20/20 PASS |
| `math-megamath-train-000000` | `math-megamath` | 17,232 | 33,979,879 | 20/20 PASS |

**40/40 selected documents decoded successfully**, were nonempty, already tokenizer-normalized, ended with EOS 130822 and re-encoded to exactly the original document token IDs (excluding the terminal EOS). Artifact hashes, payload headers, index boundaries and metadata token counts were verified before decoding.

## Method

Actual local tokenizer bytes match frozen p1536 SHA-256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`; vocabulary 131,072; EOS `<|endoftext|>` 130822. Uses the Rust-backed `tokenizers.Tokenizer` implementation, with no substitute/test tokenizer.

Deterministic selection: document index `i * (doc_count - 1) // 19` for `i = 0..19`, including the first and last documents and positions across the shard. Document boundaries come from the index; source part and row come from the corresponding `.docs.parquet` row. The final EOS is removed for decoding and re-encoding uses `add_special_tokens=False`.

Each JSON evidence row records the document ID, source part/row, token offsets, decoded character count, SHA-256 of decoded UTF-8 and the four verification outcomes. Decoded text stays in memory and is not written to disk or Git.

Environment: Python 3.12.3, NumPy 2.5.4, PyArrow 26.0.1, tokenizers 0.23.3.

## Reproduce

```bash
python3 -I teams/01-data-a/audit/shard_decode_patilvijay23/reproduce.py \
  --input <downloaded-shard-folder> \
  --tokenizer <p1536-folder>/tokenizer.json \
  --out teams/01-data-a/audit/shard_decode_patilvijay23
```

Exit code **0**. Both shards report `20/20 decoded, normalized and exact token round-trip`.

## en-dclm-train-000000

Evidence: [en-dclm-train-000000.decode.json](shard_decode_patilvijay23/en-dclm-train-000000.decode.json).

Selected zero-based document indices: `0, 2370, 4740, 7110, 9480, 11850, 14220, 16590, 18960, 21330, 23700, 26070, 28440, 30810, 33180, 35550, 37920, 40290, 42660, 45031`.

Source part: `en-dclm_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-dclm-train-000000.json` | `aea60298ee0c7eed31b498c49f709d7f2fb96d01896388d8af2ec28a9240331a` |
| `en-dclm-train-000000.bin` | `1fccdcc4c15bb22ea564c8d3f1850582abd8b60e6c504386ee84308f6ee074de` |
| `en-dclm-train-000000.idx.npy` | `2cb4f8478781d20a73c43db1dbf5426ec85a7784f1fd3e4cbb60d443bfd6891d` |
| `en-dclm-train-000000.docs.parquet` | `3193a184ca4f89a3ef8d13ababaaa576d034fe767fed85269bd0322f5bb15bf7` |
| `en-dclm-train-000000.quality_report.json` | `ce3729e776105cd4ab4c82496d8913fa4aef794eb8e52342e5c6d3807faa9dea` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## math-megamath-train-000000

Evidence: [math-megamath-train-000000.decode.json](shard_decode_patilvijay23/math-megamath-train-000000.decode.json).

Selected zero-based document indices: `0, 906, 1813, 2720, 3627, 4534, 5441, 6348, 7255, 8162, 9068, 9975, 10882, 11789, 12696, 13603, 14510, 15417, 16324, 17231`.

Source part: `math-megamath_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `math-megamath-train-000000.json` | `ccdae49682b19c7f724620406911d02c157eb94b14463b9eb2463e27b0318214` |
| `math-megamath-train-000000.bin` | `ff5a213f47981243e42a31e3ffe6733e276181ef0e8cfb7c581f77bea6e22e57` |
| `math-megamath-train-000000.idx.npy` | `1fbbfcfc8a8e19f160f5bbfc8b4902a017455421572232b3b55c0e6ed98fca8f` |
| `math-megamath-train-000000.docs.parquet` | `7f11583f97a20c2904cb583a24981d04c4d4b002b3809e79447bd09bbff8e770` |
| `math-megamath-train-000000.quality_report.json` | `538f893f47a2eb805fb27e7b11ba8d5890acd16d3359a254d00ec57b1eb6b33c` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## Limits and related evidence

Token round-trip establishes consistency of the decoded text with the selected token sequences. Comparing that text with the original cleaned documents requires upstream Parquet files. This report does not claim human semantic review, all-document decoding, a whole-bundle audit or benchmark decontamination.

The shared `cleaning_pipeline.json` has `dedup: null`, tracked by [#503](https://github.com/theschoolofai/era-v5-lab/issues/503). Successful decoding does not resolve that provenance finding or establish training admission. The separate Data A rotation report contains the full-shard integrity results.
