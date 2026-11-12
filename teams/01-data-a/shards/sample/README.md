# Sample shard: code-go-train-000000 (C3)

One shard from code-go, written with the C3 tokenizer: 271 docs, 262,032 tokens, EOS `<|endoftext|>` 130822 after each doc.

**Inputs**
- Tokenizer: C3 `tokenizer.json`, sha256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3` (G3, #340). Not in the
  repo (8 MB).
- Tokenizer sample: CAP-1 packs, `code-go/Part_2/part-00001.parquet`, sha256
  `40aedd68c4ec949eb825edc68896ae4518cf6c3283027d9ba1430ee66ee247fc` (21,874 docs).
- Cleaned with `spec_v1/run_clean.py --f2` at `cc6f4c8` (`g1-specv1`): `clean.py` `22d818c7…`, F2 set v2 `2826a3b8…`. 20,225
  docs kept, 1,621 dropped by `clean.py`, 28 by F2. The shard takes the first 271 that fit in 262,144 tokens.

**Commands** (from the repo root)

```bash
python teams/01-data-a/spec_v1/run_clean.py --pack <cap1>/code-go/Part_2/part-00001.parquet --pack-id code-go --out <out> --f2
python teams/01-data-a/shards/shard_writer.py --clean <out>/code-go_part-00001_clean.parquet \
  --summary <out>/code-go_part-00001_summary.json --tokenizer <c3>/tokenizer.json \
  --language go --script Latn --lane code --tokens 262144 --out teams/01-data-a/shards/sample
```

**Files** (sha256)

| file | in the repo | sha256 |
|---|---|---|
| `code-go-train-000000.bin` | no: pr-guard refuses `.bin` | `a9f5e861508679e774a38d3c3af16454bd3c956c96504c9b9ea2e533eda450ed` |
| `code-go-train-000000.docs.parquet` | no: pr-guard refuses `.parquet` | `215004216f384089c59baf2e666787df7288d12c6366c88863f5db82402e7e44` |
| `code-go-train-000000.idx.npy` | yes | `d808fcda4116f03d8017c4c6ade92c8914a64a2df5c3a530d447b92f6ada8ce0` |
| `code-go-train-000000.json` | yes | `0b062310577feec1d38ff7aa538f7b880bd85226d826040c4646811e62959f87` |
| `code-go-train-000000.quality_report.json` | yes | `5ecae0dbc4f3c9c82f7c3277bde45212d12a903927d3babc7aa44103102d307e` |
| `code-go-train-000000.dump.md` | yes | `bfd2e8bea7d866e221295699c625fd3591b1008a2a9ddc17250681f861175045` |
| `cleaning_pipeline.json` | yes | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

The commands above make the `.bin` and `.docs.parquet` again; check them against these hashes (also in the manifest as
`payload_sha256` and `sample_metadata_sha256`). `.dump.md` shows what both hold.
