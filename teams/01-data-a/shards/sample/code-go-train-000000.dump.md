# Shard `code-go-train-000000`

Written by `shard_writer.py` from `part-00001.parquet` of `code-go`, after `clean.py` and F2 (fingerprints `2826a3b88321`): the first 271 docs that fit in 262,144 tokens, of 271 rows read.

Tokenizer `15468e66457b` (C3, frozen); EOS `<|endoftext|>` id 130822 after each doc; no BOS, no language tag.

Left out: 0 secret-like, 0 empty, 0 with a special id inside, 0 not round-tripping (doc_ids in `code-go-train-000000.quality_report.json`).

| file | bytes | sha256 |
|---|---:|---|
| `code-go-train-000000.bin` | 1,049,152 | `a9f5e861508679e7…` |
| `code-go-train-000000.idx.npy` | 2,304 | `d808fcda4116f03d…` |
| `code-go-train-000000.docs.parquet` | 11,204 | `215004216f384089…` |
| `cleaning_pipeline.json` | 196 | `35611a83cfa6d6b5…` |
| `code-go-train-000000.quality_report.json` | 880 | `5ecae0dbc4f3c9c8…` |

## `code-go-train-000000.bin`

- header, 1,024 bytes = 256 little-endian int32: `20261025` (magic), `2` (version), `262,032` (token count), then zeros
- then 262,032 little-endian uint32 token IDs; every doc ends with 130822, and no other special id occurs
- tokens per character: median 0.286, max 0.589

## `code-go-train-000000.idx.npy`

int64, 272 entries (start of each doc, then token_count): `[0, 323, 470, 820, 1203] … [261650, 262032]`

## `code-go-train-000000.docs.parquet`

One row per doc in shard order, IDs and counts only. First rows:

| doc_id | input_part | input_row | n_tokens | n_chars | lang_label |
|---|---|---:|---:|---:|---|
| `bca061a4cf90b329` | `code-go_part-00001_clean.parquet` | 0 | 323 | 1,203 | code |
| `009e279dfca8ad00` | `code-go_part-00001_clean.parquet` | 1 | 147 | 477 | code |
| `ded7462c63ff1929` | `code-go_part-00001_clean.parquet` | 2 | 350 | 1,012 | code |
| `1922dd43189cde78` | `code-go_part-00001_clean.parquet` | 3 | 383 | 1,276 | code |
| `edc27d46452dd366` | `code-go_part-00001_clean.parquet` | 4 | 431 | 1,565 | code |
