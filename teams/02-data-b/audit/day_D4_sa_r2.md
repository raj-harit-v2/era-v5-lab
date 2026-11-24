# Sanskrit reader audit, second reader, D4 (day-4 seed)

Issue #711, second reader (@keshavamurali), read without seeing the first reader's verdicts. Documents drawn with `random.Random(4).sample(range(n), 25)` from `ind-sa-fw2-train-000000`, decoded with the frozen tokenizer p1536. Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `75423f9e4d47b94e` | `ind-sa-fw2-train-000000` | finding | C3 | 872 | text stops mid-sentence at end, source |
| `4a0d46c68a0ec578` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `bd181980f5d209a9` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `b7c7d966b6019d97` | `ind-sa-fw2-train-000000` | finding | C3 | 1136 | text cut mid-word at end, source |
| `738dca7eb9deb0bb` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `d6049ed74b2695f9` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `bd4759d1fb5e05ad` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `0fe8486c2bb9e0c4` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `68c788acd9ae8594` | `ind-sa-fw2-train-000000` | finding | D3 | 1444 | one Hindi sentence inside Sanskrit news, source; not D1 |
| `37d6294642ac041a` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `9f60e07096013f17` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `e4e5b4944e701553` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `1e92b88cfec3f31a` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `ec09cf84f27662b9` | `ind-sa-fw2-train-000000` | ok |  |  | cleaning removed English header line, correct; title repeated, source |
| `4d8f70ef5085c008` | `ind-sa-fw2-train-000000` | ok |  |  | OCR commentary page, noisy and split words, source |
| `cd67620279a32c81` | `ind-sa-fw2-train-000000` | finding | A6 | 62 | Latin capital I used as danda, 2 places, source |
| `185387955f0849d5` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `832cf7bbd1a72622` | `ind-sa-fw2-train-000000` | finding | G4 | 2401 | visarga typed as ASCII colon, 7 places, in raw too, source |
| `4f7a6a85a601d7bf` | `ind-sa-fw2-train-000000` | finding | G3 | 8753 | cleaning deleted verse numbers 100-120 (numbers only, verses kept) |
| `7bd8a8fa5e6288c7` | `ind-sa-fw2-train-000000` | finding | A1 | 104314 | 211 orphan U+FE0E at footnote ends, source; cleaning removed the arrows |
| `51e19714fc999a42` | `ind-sa-fw2-train-000000` | ok |  |  | cleaning removed Hindi site header line, correct |
| `c1a3da3a70d87d45` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `46f9b9113237390c` | `ind-sa-fw2-train-000000` | finding | C1 | 0 | wiki user page title with Latin username, source |
| `46f9b9113237390c` | `ind-sa-fw2-train-000000` | finding | B2 | 194 | leftover poem markup tag, unclosed, source |
| `07aafc1c903649cd` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `7d742912c34be333` | `ind-sa-fw2-train-000000` | ok |  |  | OCR page fragment, starts mid-word; G1 hits are avagraha |

## Summary

- Documents read: 25
- ok: 17
- With a finding: 8
- Codes found: A1 (1), A6 (1), B2 (1), C1 (1), C3 (2), D3 (1), G3 (1), G4 (1)
