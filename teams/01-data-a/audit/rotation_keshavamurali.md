# Rotation check, keshavamurali

Week 3 rotation in Team 01 Data A, tasks R1 (check 2 tokenized shards: manifest fields, hashes and token counts) and R2 (file each problem as an issue).

**These are sample-v0 shards.** TSAI built them on 16 Nov from the tokenizer sample v0 train parts, after `clean.py` and F2, with the frozen p1536 tokenizer (one shard per input part; held-out parts are not sharded). They are not yet the first training data. Assignment: Vijay's G1 shard-check table of 16 Nov.

Checked on 16 Nov 2026 with main `85639f0` (#504, the p1536 release). Files from TSAI's p1536 sample-v0 download list (links not recorded here).

## Summary

| Shard | Docs | Tokens | Result |
|---|---:|---:|---|
| `code-rust-train-000000` | 43,116 | 59,530,999 | 45 PASS, 1 FAIL (`dedup: null`, #503) |
| `math-finemath-train-000000` | 28,088 | 38,582,010 | 45 PASS, 1 FAIL (`dedup: null`, #503) |

Every file hash, size, header, index, token count and manifest field matches. The only FAIL is the shared `cleaning_pipeline.json` recording `dedup: null`. That is issue #503 (filed by shivman for the same bundle), so no new issue. No other problem found; nothing new filed under R2.

## How it was checked

[`check_shard.py`](check_shard.py), in this folder, reads the manifest and every file it names, and reports each check as PASS, FAIL or NOT CHECKED. A missing file is NOT CHECKED, never PASS. It prints IDs, counts and hashes only, never document text.

- **Tokenizer:** `--expect-tokenizer p1536` requires `tokenizer_sha256` = `e6b93a93a60520d7…` (G3 #504).
- **Special ids:** `--specials-from` reads the special ids from a `tokenizer.json`. G3 states that p1536's special tokens are byte-for-byte C3's (#504), so the frozen C3 file (sha256 `15468e66…`) was used: 9 special ids below 130,725, plus 130,725 and above. The p1536 `tokenizer.json` itself (private Kaggle dataset) was not used, so no text was decoded here. Decoding 20 documents per shard is Vijay's and Tejaskumar's task.
- **Tests:** `tests/audit/test_check_shard.py`, 22 cases on a made-up shard, including one that the results do not depend on how the `.bin` is read in chunks.

Rerun, from the repository root (Python 3.12, numpy 2.5.4, pyarrow 26.0.1), with the shard files in `<dir>`:

```
python -I teams/01-data-a/audit/check_shard.py <dir> code-rust-train-000000 --expect-tokenizer p1536 --specials-from <c3 or p1536>/tokenizer.json
python -I teams/01-data-a/audit/check_shard.py <dir> math-finemath-train-000000 --expect-tokenizer p1536 --specials-from <c3 or p1536>/tokenizer.json
python -m pytest teams/01-data-a/tests/audit -q
```

Last lines: `{'PASS': 45, 'FAIL': 1, 'NOT CHECKED': 0}` for each shard (exit code 1, from the `dedup` FAIL), 2.6 s and 2.0 s, under 400 MiB of memory; `22 passed`.

## Shard 1: `code-rust-train-000000`

Manifest file sha256 `e8c9cbb7bf03a6d56ec82d721a44798acb8882b8d98aa42d14728be936aefc73`.

| # | Check | Manifest | Recomputed | Result |
|---|---|---|---|---|
| 1 | Manifest fields | 28 template fields | 28, none extra, no placeholders; `shard-v1`, `brahmic_u32_v2+doc_index`, `uint32`, split `train`, id `code-rust-train-000000` | PASS |
| 2 | Payload sha256 | `9468c56cccae9055…` | `9468c56cccae9055…` | PASS |
| 3 | Payload size | 238,125,020 = 1,024 + 4 × 59,530,999 | 238,125,020 | PASS |
| 4 | Header | magic 20261025, version 2, 59,530,999 tokens | same; rest zeros | PASS |
| 5 | Index sha256 | `978a875772b39a37…` | `978a875772b39a37…` | PASS |
| 6 | Index | 43,117 entries, 0 … 59,530,999 | int64, 43,117, 0 … 59,530,999, lengths sum to `token_count`, shortest doc 5 tokens | PASS |
| 7 | Document metadata | `b47840d725272e10…` | same; 43,116 rows, unique doc_ids, `n_tokens` = index lengths; one input part (`code-rust_part-00000_clean.parquet`), rows 0 … 43,131 in order | PASS |
| 8 | Quality report | `ea22d8909d72239b…` | same; 43,132 read = 43,116 in shard + 16 left out (secret-like) | PASS |
| 9 | Tokenizer | p1536 `e6b93a93a60520d7…` | same | PASS |
| 10 | EOS | 130822 | every one of 43,116 documents ends with it; no special id inside a document; max id 130,822 (< 131,072) | PASS |
| 11 | Decontamination set | `2826a3b883210c65…` (F2 v2) | = `f2_set_sha256` in `cleaning_pipeline.json` (sha256 `35611a83…`, matches) | PASS |
| 12 | Writer | `0064f81d57ef47e2…` | a full commit hash, on main | PASS |
| – | Dedup version | – | `cleaning_pipeline.json`: `dedup: null` | FAIL, #503 |

## Shard 2: `math-finemath-train-000000`

Manifest file sha256 `2e18384cbeb96254f99ac302f8f53c1a6dddd6bdd68d75fdd754808f7ac5e206`.

| # | Check | Manifest | Recomputed | Result |
|---|---|---|---|---|
| 1 | Manifest fields | 28 template fields | 28, none extra, no placeholders; `shard-v1`, `brahmic_u32_v2+doc_index`, `uint32`, split `train`, id `math-finemath-train-000000` | PASS |
| 2 | Payload sha256 | `6e84f270a53bcdd2…` | `6e84f270a53bcdd2…` | PASS |
| 3 | Payload size | 154,329,064 = 1,024 + 4 × 38,582,010 | 154,329,064 | PASS |
| 4 | Header | magic 20261025, version 2, 38,582,010 tokens | same; rest zeros | PASS |
| 5 | Index sha256 | `71e7583ba412e00d…` | `71e7583ba412e00d…` | PASS |
| 6 | Index | 28,089 entries, 0 … 38,582,010 | int64, 28,089, 0 … 38,582,010, lengths sum to `token_count`, shortest doc 42 tokens | PASS |
| 7 | Document metadata | `49bca3b3a8eb9955…` | same; 28,088 rows, unique doc_ids, `n_tokens` = index lengths; one input part (`math-finemath_part-00000_clean.parquet`), rows 0 … 28,261 in order | PASS |
| 8 | Quality report | `7608571c0930abc2…` | same; 28,262 read = 28,088 in shard + 174 left out (secret-like) | PASS |
| 9 | Tokenizer | p1536 `e6b93a93a60520d7…` | same | PASS |
| 10 | EOS | 130822 | every one of 28,088 documents ends with it; no special id inside a document; max id 130,822 (< 131,072) | PASS |
| 11 | Decontamination set | `2826a3b883210c65…` (F2 v2) | = `f2_set_sha256` in `cleaning_pipeline.json` | PASS |
| 12 | Writer | `0064f81d57ef47e2…` | a full commit hash, on main | PASS |
| – | Dedup version | – | `cleaning_pipeline.json`: `dedup: null` | FAIL, #503 |

## Notes

1. **`dedup: null`** in the shared `cleaning_pipeline.json` (sha256 `35611a83…`): these shards were cleaned before dedup (#255) runs. Covered by #503.
2. **Documents the writer left out as secret-like:** 174 of 28,262 on math-finemath (0.62%) and 16 of 43,132 on code-rust (0.04%). They are counted and listed by doc_id in each quality report, as the shard format says, so this is not a manifest problem. On math-finemath it is a visible loss. A likely cause, not checked here: the cleaner's F1 keeps organisation and role emails by design (`spec_v1/README.md`), and the writer then drops the whole document for any email-like string. For the lead to judge whether this is intended; not filed as an issue.
3. **`created_by` = `0064f81d57ef47e22d8fa5f42d96c99089a98ce4`** is on main's history, so the writer version can be found from a clone of main. (The earlier in-repo sample named a commit only on a fork, see below.)
4. **`clean.py`:** `cleaning_pipeline.json` names `clean.py` `22d818c7…`, the cleaner on main today (before the spec v1.1 rebuild, task 2).

## Earlier: the in-repo sample shard (15 Nov)

Before the sample-v0 shards existed, the lead asked for a check of the sample shard on main, `teams/01-data-a/shards/sample/code-go-train-000000` (C3 tokenizer, written to test the shard code, #358, #373). Its `.bin` and `.docs.parquet` are not in git, so only the manifest, index, quality report and `cleaning_pipeline.json` were checked: 30 PASS, 1 FAIL (`dedup: null`, now #503), 4 NOT CHECKED (the missing files). Its `created_by` (`5255556c7fc4…`) is not on main's history after the squash merge of #373, but GitHub serves it and its `shard_writer.py` is byte-identical to main's. Rerun: `python -I teams/01-data-a/audit/check_shard.py teams/01-data-a/shards/sample code-go-train-000000 --expect-tokenizer C3`.

## R2: issues

| Problem | Issue |
|---|---|
| `cleaning_pipeline.json` records `dedup: null` | #503 (existing; linked, not filed again) |
| A second shard missing on main (15 Nov) | #448 (existing; superseded by the sample-v0 bundle) |
