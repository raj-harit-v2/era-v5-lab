# Round trip on the p1536 token shards (week 3, Task 4)

**Result: PASS.** 1,000 documents drawn from 5 shards in 1 domains (up to 1,000 per domain, seed 4); 0 failures.

| Field | Value |
|---|---|
| Tokenizer | p1536 `tokenizer.json`, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| Shards | TSAI's p1536 sample-v0 bundle (16 Nov), `dataset_version: sample` |
| Script | `teams/03-tokenizer/harness/roundtrip_shards.py` at `1bba5698a147` |
| Environment | Python 3.9.6, tokenizers 0.22.2, macOS-27.2.1-arm64-arm-64bit |
| Wall time | 0.7 s, including sha256 of every shard |

## Checks per document

| Check | Rule |
|---|---|
| eos | ends with EOS `<\|endoftext\|>` 130822; no other special id inside |
| ids | `encode(decode(ids)) == ids` (ids without the final EOS, `add_special_tokens=False`) |
| normal | `normalizer(decode(ids)) == decode(ids)`: decoded text is already NFC + chillu + nukta form |
| source | `decode(ids) == normalizer(source text)`, source row from `docs.parquet` `input_part` / `input_row` |

Each shard was first checked against its manifest: tokenizer sha256, EOS id, `.bin` header and size, payload and index sha256, and the document index.

## By domain

| Domain | Shards | Docs in shards | Drawn | eos | ids | normal | source | Tokens drawn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| indic | 5 | 153,777 | 1,000 | 1,000 / 1,000 | 1,000 / 1,000 | 1,000 / 1,000 | not run | 256,921 |

## By shard

Writer drops: documents `shard_writer.py` already left out because `decode(encode(x)) != normalizer(x)` (from each shard's `quality_report.json`), of rows read.

| Shard | Domain | payload sha256 | Docs | Tokens | Drawn | Failures | Writer drops |
|---|---|---|---:|---:|---:|---:|---:|
| `ind-hi-fw2-train-000000` | indic | `e64b18601f2f…` | 13,773 | 8,988,818 | 93 | 0 | 0 / 13,773 |
| `ind-hi-hplt-train-000000` | indic | `e7e357d21bec…` | 8,386 | 8,090,716 | 59 | 0 | 0 / 8,418 |
| `ind-hi-indiccorp-train-000000` | indic | `6be0f58e567a…` | 109,668 | 9,343,359 | 709 | 0 | 0 / 109,674 |
| `ind-hi-sangraha-s-train-000000` | indic | `4b92b39b4275…` | 7,467 | 5,988,971 | 49 | 0 | 0 / 7,467 |
| `ind-hi-sangraha-v-train-000000` | indic | `78aca29173b7…` | 14,483 | 9,254,413 | 90 | 0 | 0 / 14,489 |

## Failures

None.

## Notes

- The round trip is against the normalized text, as the tokenizer card says (section 2): Bn/Pa nukta and Ml old chillu come back in normal form, so `decode(encode(x))` can differ from the raw `x`.
- The source check (`--clean`) did not run: the cleaned parts were not available. `ids` and `normal` together show the shard ids are p1536's own encoding of text already in normal form, and the writer had already checked decode against the normalized source for every kept document.
- No document text is in this file: only IDs, counts, hashes and token positions.

## Command

```
python teams/03-tokenizer/harness/roundtrip_shards.py <shards> --tokenizer <p1536>/tokenizer.json --per-domain 1000 --seed 4 --out teams/03-tokenizer/results/roundtrip_shards.md
```
