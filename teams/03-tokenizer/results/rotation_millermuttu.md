# G3 rotation R1 + R2: p1536 vs BrahmicTokenizer-131K on the speed_v1 text (Linux, one pinned core)

- **R1:** encode speed of the frozen p1536 on 1 GB of text per domain.
- **R2:** the same run for BrahmicTokenizer-131K.

Both use the exact text of `speed_v1.md` (#488): the same files, the same selection and the same `benchmark_input_sha256` per domain. The numbers compare directly with #488 and #505. This run also gives a second machine with a hard one-core pin, which `speed_v1.md` lists as pending. No corpus text is in this file.

## 1. Result (median of 3 timed passes, 1 warm-up)

| Domain | Input | p1536 MB/s | Brahmic MB/s | p1536 vs Brahmic (MB/s) | p1536 tokens | Brahmic tokens | p1536 vs Brahmic (tokens) |
|---|---:|---:|---:|---:|---:|---:|---:|
| English | 1.000 GB | **2.205** | 2.327 | −5.2% | 206,673,500 | 206,900,539 | −0.1% |
| Code | 1.000 GB | **1.894** | 2.079 | −8.9% | 258,914,207 | 257,268,472 | +0.6% |
| Indic | 0.309 GB (all available) | **2.983** | 3.153 | −5.4% | 36,646,601 | 39,533,199 | −7.3% |

| Domain | p1536 tokens/s | Brahmic tokens/s | p1536 tokens/byte | Brahmic tokens/byte | p1536 seconds per 1 GB |
|---|---:|---:|---:|---:|---:|
| English | 455,785 | 481,379 | 0.2067 | 0.2069 | 453 |
| Code | 490,470 | 534,815 | 0.2589 | 0.2573 | 528 |
| Indic | 353,696 | 403,342 | 0.1186 | 0.1279 | 335 |

**Speed:** p1536 reads text 5 to 9% slower than BrahmicTokenizer-131K on one core in every domain. Compare MB/s, not tokens/s: on Indic, p1536 makes 7.3% fewer tokens for the same bytes, so its tokens/s drops more than its actual work rate.

**Tokens:** on English and code the two tokenizers produce almost the same number of tokens (within 0.6%).

**Why p1536 is slower:** this matches Nisarg's finding in `rotation_Nisarg189.md` §3. p1536 runs a normalizer (NFC plus 15 `Replace` steps) and BrahmicTokenizer-131K has none.

### All runs (MB/s)

| Domain | Tokenizer | Run 1 | Run 2 | Run 3 | Median |
|---|---|---:|---:|---:|---:|
| English | p1536 | 2.199 | 2.205 | 2.212 | 2.205 |
| English | Brahmic | 2.327 | 2.311 | 2.328 | 2.327 |
| Code | p1536 | 1.893 | 1.910 | 1.894 | 1.894 |
| Code | Brahmic | 2.079 | 2.064 | 2.089 | 2.079 |
| Indic | p1536 | 2.983 | 2.965 | 2.984 | 2.983 |
| Indic | Brahmic | 3.131 | 3.153 | 3.180 | 3.153 |

Within each configuration, the runs are within 1.6% of each other. The token counts were identical in all three runs.

## 2. Cross-check with speed_v1.md (#488)

p1536 gives the same tokens/byte as #488 on all three domains (0.2067 / 0.2589 / 0.1186). Same text and same tokenizer give the same ids, so the inputs match.

| Domain | p1536 MB/s, #488 (Apple M2, macOS, tokenizers 0.21.1, no hard pin) | p1536 MB/s, this run (i5-10300H, Linux, tokenizers 0.23.3, core 0 pinned) |
|---|---:|---:|
| English | 1.638 | 2.205 |
| Code | 2.575 | 1.894 |
| Indic | 3.213 | 2.983 |

Machine and `tokenizers` version both differ, so this table does not separate the two effects. English is faster here and code is slower, so neither the CPU nor the 0.23.3 speed-up (#516) explains the whole difference on its own.

## 3. Data

The text is tokenizer sample v0-clean: sample v0 after the Data A cleaner (`clean.py`, spec v1, #244), from the Capstone Lab 1 page. Each file sha256 was matched against `cleaned_manifest.json` and against `dataset_manifest.json` of #488. All 18 match. Files are named as in `dataset_manifest.json`, so the sorted read order is the same.

| Domain | Packs (train parts) | Selected records | Input UTF-8 bytes | `benchmark_input_sha256` |
|---|---|---:|---:|---|
| English | en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth (part-00000, part-00001) | 354,320 | 1,000,002,183 | `c4b96c7a05961246…` (same as #488) |
| Code | code-cpp, code-go, code-java, code-python (part-00000, part-00001) | 233,254 | 1,000,000,966 | `d534c7485e69546f…` (same as #488) |
| Indic | ind-hi-sangraha-v, ind-bn-fw2, ind-hi-sangraha-s, ind-hi-hplt (part-00000) | 42,260 | 309,018,421 (all available) | `57109b404789c22f…` (same as #488) |

## 4. Tokenizers

| Tokenizer | Source | sha256 |
|---|---|---|
| p1536 (frozen, #504) | TSAI release link; `release/verify_release.py` PASS, `SHA256SUMS` OK | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| BrahmicTokenizer-131K | github.com/theschoolofai/BrahmicTokenizer-131K `tokenizer.json` | `01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff` |

## 5. Machine and method

| Field | Value |
|---|---|
| CPU | Intel Core i5-10300H (4 cores / 8 threads), laptop on mains power |
| OS | Linux 7.0.0-43-generic x86_64, glibc 2.39 |
| Python / tokenizers / pyarrow | 3.13.9 / **0.23.3** (release pin) / 21.0.0 |
| One-core pin | **enforced**: `os.sched_setaffinity(0, {0})` by the script, CPU 0 |
| Threads | `TOKENIZERS_PARALLELISM=false`, OMP/MKL/OPENBLAS/NUMEXPR threads = 1 |
| Encode call | `Tokenizer.encode(text, add_special_tokens=False)`, one document per call |
| Timing | encode loop only; load and warm-up excluded; median of 3 |
| Script | `harness/bench_cpu_speed.py`, sha256 `e6798946fdb561d0…`, repo commit `85639f0` |
| Run | 17 Nov 2026, 11:47 to 14:07 IST |

The script takes the two files as `--c3` and `--p1536`. BrahmicTokenizer-131K was passed as `--c3`, so the raw JSON calls it `c3_sample_v0`. C3 itself was not run.

```bash
GIT_COMMIT=$(git rev-parse HEAD) python teams/03-tokenizer/harness/bench_cpu_speed.py \
  --data-root /path/to/week3data \
  --c3 /path/to/BrahmicTokenizer-131K/tokenizer.json \
  --p1536 teams/03-tokenizer/release/tokenizer.json \
  --results-dir /path/to/out --target-bytes 1000000000 --runs 3 --warmup 1
```

## 6. Limits

- Laptop CPU with frequency scaling. Turbo was not disabled, so absolute MB/s can move with temperature. The runs agreed within 1.6%.
- Indic is 0.309 GB (all available in these packs), as in #488.
- One document per encode call, as in #488. Batch and multi-process modes are in `rotation_Nisarg189.md` §4.

## Contributors

- [@millermuttu](https://github.com/millermuttu): data match, runs, report
