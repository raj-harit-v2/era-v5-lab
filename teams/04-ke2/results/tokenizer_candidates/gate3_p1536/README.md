# Gate 3 tokenizer table and collision check

TSAI replaced the C3-s0 freeze with Team 3's p1536-s0 candidate on 16 Nov.
The local `tokenizer.json` was accepted only after its SHA-256 matched
`e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`.
The tokenizer file is not committed. C3-s0 is included here solely as the comparison baseline.

| Check | C3-s0 | p1536-s0 |
|---|---:|---:|
| Vocabulary | 131,072 | 131,072 |
| Special tokens | 356 | 356 |
| Longest raw token | 32 bytes | 32 bytes |
| Raw collisions at P=32 / P=64 | 0 / 0 | 0 / 0 |
| Truncated tokens at P=32 / P=64 | 0 / 0 | 0 / 0 |
| Decode-table excess collisions at P=32 / P=64 | 1,095 / 1,095 | 857 / 857 |
| Unexplained collision groups | 0 | 0 |

P1536-s0 has 10 known `decode_collapse` groups covering 867 token IDs at either P.
The exact group IDs and their script classes are in `collision_groups.csv` and
`collisions_by_script.csv`. The raw table is injective; its 32-byte bound is met.
Compared with C3-s0, 13,824 raw rows and 13,824 decode rows changed. The changed-ID
list has SHA-256 `2eca6069dfb319cf27c921e4cce35f8f7b59fe383d0fa37edf3ffcbeb7ee311b`.

Reproduce using the two exact local tokenizer files:

```bash
python teams/04-ke2/src/revalidate_tokenizer_candidates.py \
  --candidate C3-s0=/path/to/c3-sample-v0/tokenizer.json \
  --candidate p1536-s0=/path/to/p1536-sample-v0/tokenizer.json \
  --out teams/04-ke2/results/tokenizer_candidates/gate3_p1536

python teams/04-ke2/src/build_tables.py \
  --tokenizer /path/to/p1536-sample-v0/tokenizer.json \
  --out teams/04-ke2/results/tables/p1536-s0 --pos-dims 32 64
```

The second command writes the committed four NPZ tables and manifest. Its manifest
binds each table to the tokenizer SHA-256. C3-s0 results and historical baseline
codec experiments remain unchanged.
