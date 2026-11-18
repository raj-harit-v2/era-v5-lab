# Tokenizer CPU speed benchmark v1 — p1536

Encode throughput for **p1536** on English, Code and Indic text. Median of three measured runs per domain.

## Tokenizer verification (p1536)

| Field | Value |
|---|---|
| Artifact | `$WEEK3DATA/archive/tokenizer.json` |
| Expected sha256 | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| Observed sha256 | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| Matches | `archive/SHA256SUMS`, `train/p1536_s0_manifest.json` |
| Checks | structure (BPE, vocab 131072, 130460 merges, 356 specials), roles, round trip, AutoTokenizer |
| EOS | `<\|endoftext\|>` **130822** |
| Result | **PASS** |
# Tokenizer CPU speed benchmark v1

Encode throughput for the frozen **C3 sample-v0** tokenizer vs the **p1536** candidate on English, Code and Indic text. Median of three measured runs per configuration. No IN22 / FLORES fertility numbers here — speed only.

## Upstream sync

| Item | Value |
|---|---|
| Upstream `main` SHA | `ae4c03dbe69b9a46bfdd8a0922cf5d48118ab51f` |
| Upstream remote | `https://github.com/theschoolofai/era-v5-lab.git` (`upstream`) |
| Upstream `main` SHA | `ae4c03dbe69b9a46bfdd8a0922cf5d48118ab51f` |
| Working branch base | same SHA (fork `main` fast-forwarded to upstream `main`) |
| Benchmark script commit (at run) | `ae4c03dbe69b9a46bfdd8a0922cf5d48118ab51f` |

## Tokenizer versions and verification

| Tokenizer | Path used | sha256 |
|---|---|---|
| C3 sample-v0 (frozen release) | `teams/03-tokenizer/release/tokenizer.json` | `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3` |
| p1536 | `week3data/archive/tokenizer.json` | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |

- **C3:** `python teams/03-tokenizer/release/verify_release.py …` → `RESULT: PASS` (structure, roles, round trip, `eos_token_id` **130822**). Log: `release_verification.log`.
- **p1536:** sha256 matches `week3data/archive/SHA256SUMS`. `verify_release.py` is pinned to frozen C3 and would FAIL on purpose for any other file; p1536 was checked separately for vocab 131072, 130460 merges, 356 specials, and EOS id **130822**. Special-token ids were not modified. Archives were not rewritten.

## Machine and configuration

| Field | Value |
|---|---|
| Machine | Apple MacBook Pro, **Apple M2**, 8 logical CPUs |
| OS | macOS 15.1.1 (Darwin 24.1.0, arm64) |
| Python | 3.11.8 |
| `tokenizers` | 0.21.1 |
| Runs / domain | 3 measured + 1 warm-up |
| Encode API | `Tokenizer.encode(text, add_special_tokens=False)` |
| Parallelism | `TOKENIZERS_PARALLELISM=false`; BLAS/OpenMP threads = 1 |

### One-core affinity

**Not verified** on Darwin (no `os.sched_setaffinity`). Thread pools limited to 1; hard CPU pin not claimed.

## Dataset sizes

| Domain | Selected records | Input UTF-8 bytes | vs 1 GB target |
|---|---:|---:|---|
| English | 354 320 | 1 000 002 183 | reached target |
| Code | 233 254 | 1 000 000 966 | reached target |
| Indic | 353 558 | 1 000 008 297 | reached target |

Selection: sorted parquet paths under `$WEEK3DATA/{english,code,indic}`, row order, stop at 1 000 000 000 UTF-8 bytes (or all available). Text column: `text`.

## Methodology

Load/decode Parquet before timing. Warm-up excluded. Timed window = encode loop only. Report **median** of three runs.  
`MB/s = (input_bytes / 1e6) / elapsed_s`, `tokens/s = total_tokens / elapsed_s`.

## p1536 results — three runs and medians

### English (~1.000 GB)

| Run | MB/s | tokens/s | elapsed_s | tokens |
|---:|---:|---:|---:|---:|
| 1 | 1.594 | 329 511 | 627.2 | 206 673 500 |
| 2 | 1.638 | 338 621 | 610.3 | 206 673 500 |
| 3 | 1.659 | 342 961 | 602.6 | 206 673 500 |
| **Median** | **1.638** | **338 621** | | tokens/byte **0.2067** |

### Code (~1.000 GB)

| Run | MB/s | tokens/s | elapsed_s | tokens |
|---:|---:|---:|---:|---:|
| 1 | 2.580 | 667 893 | 387.7 | 258 914 207 |
| 2 | 2.575 | 666 634 | 388.4 | 258 914 207 |
| 3 | 2.507 | 649 055 | 398.9 | 258 914 207 |
| **Median** | **2.575** | **666 634** | | tokens/byte **0.2589** |

### Indic (~1.000 GB)

| Run | MB/s | tokens/s | elapsed_s | tokens |
|---:|---:|---:|---:|---:|
| 1 | 2.111 | 251 236 | 473.8 | 119 041 782 |
| 2 | 2.119 | 252 202 | 472.0 | 119 041 782 |
| 3 | 1.955 | 232 767 | 511.4 | 119 041 782 |
| **Median** | **2.111** | **251 236** | | tokens/byte **0.1190** |


## Median summary (p1536)

| Domain | Median MB/s | Median tokens/s | tokens/byte |
|---|---:|---:|---:|
| English | **1.638** | **338 621** | 0.2067 |
| Code | **2.575** | **666 634** | 0.2589 |
| Indic | **2.111** | **251 236** | 0.1190 |

## Cross-check

Cross-check: done on a second machine, see "Cross-check run" below.


## Cross-check run (second machine, pinned to one core)

Run by @HariniJasti on 17 Nov 2026 with the same script (`harness/bench_cpu_speed.py`), timing p1536 only (C3 is archived since #504).

- **Tokenizer:** p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` (checked)
- **Machine:** Intel laptop (Intel64 Family 6 Model 186), Windows 11, Python 3.12.7, **tokenizers 0.23.3** (the version pinned in `release/`)
- **One core:** pinned with Windows CPU affinity (`start /affinity 1`, CPU 0). The script cannot set affinity on Windows, so it reports `enforced: false`, but the process was pinned from outside (Task Manager showed one core in use).
- **Method:** same as above: 1 warm-up and 3 timed runs per domain, median reported, encode loop timed only.
- **Text:** CAP lab train packs, read in sorted file order until 1 GB:

| Domain | Packs | Records | UTF-8 bytes |
|---|---|---:|---:|
| English | en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth | 351,901 | 1,000,001,080 |
| Code | code-cpp, code-go, code-java, code-python | 234,567 | 1,000,056,968 |
| Indic | bn, gu, hi, kn, ml, mr, or, ta, te (fw2, sangraha, hplt) | 158,632 | 975,447,767 (all available) |

Indic is 975 MB because that is all the text in the 13 Indic packs downloaded; CAP has no Punjabi or Assamese pack.

**Per-run results (p1536):**

| Domain | Run | MB/s | tokens/s | elapsed_s | tokens |
|---|---:|---:|---:|---:|---:|
| English | 1 | 3.07 | 634,522 | 325.9 | 206,760,061 |
| English | 2 | 2.88 | 595,148 | 347.4 | 206,760,061 |
| English | 3 | 3.46 | 715,637 | 288.9 | 206,760,061 |
| Code | 1 | 2.97 | 785,370 | 337.1 | 264,753,125 |
| Code | 2 | 3.04 | 805,211 | 328.8 | 264,753,125 |
| Code | 3 | 3.07 | 813,310 | 325.5 | 264,753,125 |
| Indic | 1 | 4.20 | 468,851 | 232.4 | 108,954,478 |
| Indic | 2 | 4.20 | 468,873 | 232.4 | 108,954,478 |
| Indic | 3 | 4.21 | 469,932 | 231.9 | 108,954,478 |

**Medians:**

| Domain | MB/s | tokens/s | tokens/byte |
|---|---:|---:|---:|
| English | **3.07** | 634,522 | 0.2068 |
| Code | **3.04** | 805,211 | 0.2647 |
| Indic | **4.20** | 468,873 | 0.1117 |

## Reconciling the two runs

| p1536, one core | Run 1 (@nitinranjansharma) | Run 2 (@HariniJasti) | Run 2 / Run 1 |
|---|---:|---:|---:|
| English MB/s | 1.638 | 3.07 | 1.87× |
| Code MB/s | 2.575 | 3.04 | 1.18× |
| Indic MB/s | 2.111 | 4.20 | 1.99× |
| tokenizers | 0.21.1 | 0.23.3 (pinned) | |
| Machine | Apple M2, macOS | Intel, Windows 11 | |
| One-core pin | thread pools only | OS affinity, CPU 0 | |
| Text | week3data | CAP packs (above), different files | |

- **The tokens per byte agree** (English 0.2067 vs 0.2068), so both runs tokenize comparable text the same way; the difference is speed, not output.
- **Most of the gap is the setup, not the tokenizer.** Nisarg (#516) measured tokenizers 0.23.3 about 19% faster than 0.21.1 on the same machine and text; the rest comes from the CPU and from the pin.
- **Use Run 2 for the team numbers.** It matches the pinned setup in `release/` (tokenizers 0.23.3) and is pinned to one core at the OS level. Run 1 stays as the second machine.
- **Indic is the fastest domain in MB/s** on both machines: Indic text is several bytes per character, and p1536 makes about 0.11 tokens per byte on it, so it covers more bytes per token than English (0.21) or code (0.26).
- Run 2's English runs vary more (2.88–3.46 MB/s) than code and Indic (within 3%); laptop clock boost is the likely cause, so the median is used.
- For comparison, #516 measured p1536 Indic at 7.28 MB/s on one core of an M4 Pro (FineWeb-2, 11 languages), so faster CPUs give proportionally higher numbers.

## Faster tokenizing for the full job (from #516)

Nisarg found two changes that make the tokenizing job about **1.7× faster with identical ids**: `encode_batch_fast` instead of `encode_batch`, and one process per core instead of one process with many threads. This does not change the one-core numbers above, which measure the tokenizer itself.

Contributors: @nitinranjansharma, @HariniJasti
| `pyarrow` | (runtime import; used only for load) |
| Official runs | this machine only |
| Runs / config | 3 measured + 1 warm-up |
| Encode API | `Tokenizer.encode(text, add_special_tokens=False)` |
| Parallelism | `TOKENIZERS_PARALLELISM=false`; `OMP/MKL/OPENBLAS/VECLIB/NUMEXPR_NUM_THREADS=1` |

### One-core affinity

**Not verified.** Darwin has no `os.sched_setaffinity`. Thread pools were limited as above, but a hard one-core CPU pin could not be enforced or checked. Do not treat these numbers as Linux `taskset -c 0` results.

## Dataset provenance and input sizes

Data root: `/Users/nitinranjansharma/Documents/codes/ERA/CAP/week3data/{english,code,indic}`. Text column: `text`. Selection: sorted parquet paths, row order, stop at 1 000 000 000 UTF-8 bytes (or all available). No duplication, no rewrite of source packs.

| Domain | Selected records | Input UTF-8 bytes | vs 1 GB target | `benchmark_input_sha256` |
|---|---:|---:|---|---|
| English | 354 320 | 1 000 002 183 | reached target | `c4b96c7a05961246…` (full in manifest) |
| Code | 233 254 | 1 000 000 966 | reached target | `d534c7485e69546f…` |
| Indic | 42 260 | 309 018 421 | **all available** (0.309 GB) | `57109b404789c22f…` |

Details and per-file sha256: `dataset_manifest.json`. Both tokenizers saw the same strings in the same order (shared in-memory lists).

## Methodology / timing boundary

1. Load Parquet and materialise UTF-8 strings **before** timing.
2. Warm-up: one full encode pass (excluded from reported runs).
3. Measured window: only the encode loop.
4. Metrics per run: `MB/s = (input_bytes / 1e6) / elapsed_s`, `tokens/s = total_tokens / elapsed_s`.
5. Report **median** of the three measured runs (not mean, not best).
6. Secondary: `tokens_per_byte = total_tokens / input_bytes` (same across the three runs; encode is deterministic).

Script: `teams/03-tokenizer/harness/bench_cpu_speed.py`. Raw: `speed_v1.json`. Commands/log: `benchmark_execution.log`.

## Results — three runs and medians

### English (~1.000 GB)

| Tokenizer | Run 1 MB/s | Run 2 | Run 3 | **Median MB/s** | Run 1 tok/s | Run 2 | Run 3 | **Median tok/s** | tokens/byte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C3 sample-v0 | 1.796 | 1.661 | 1.636 | **1.661** | 371 039 | 343 170 | 337 991 | **343 170** | 0.2066 |
| p1536 | 1.594 | 1.638 | 1.659 | **1.638** | 329 511 | 338 621 | 342 961 | **338 621** | 0.2067 |

### Code (~1.000 GB)

| Tokenizer | Run 1 MB/s | Run 2 | Run 3 | **Median MB/s** | Run 1 tok/s | Run 2 | Run 3 | **Median tok/s** | tokens/byte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C3 sample-v0 | 1.539 | 2.543 | 2.610 | **2.543** | 395 225 | 653 180 | 670 295 | **653 180** | 0.2569 |
| p1536 | 2.580 | 2.575 | 2.507 | **2.575** | 667 893 | 666 634 | 649 055 | **666 634** | 0.2589 |

### Indic (0.309 GB, all available)

| Tokenizer | Run 1 MB/s | Run 2 | Run 3 | **Median MB/s** | Run 1 tok/s | Run 2 | Run 3 | **Median tok/s** | tokens/byte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C3 sample-v0 | 3.440 | 3.500 | 3.492 | **3.492** | 429 593 | 437 108 | 436 066 | **436 066** | 0.1249 |
| p1536 | 3.178 | 3.245 | 3.213 | **3.213** | 376 891 | 384 880 | 381 047 | **381 047** | 0.1186 |

## Comparison (medians)

| Domain | C3 MB/s | p1536 MB/s | Δ MB/s (p1536 vs C3) | C3 tok/s | p1536 tok/s | tokens/byte C3 | tokens/byte p1536 |
|---|---:|---:|---:|---:|---:|---:|---:|
| English | 1.661 | 1.638 | −1.4% | 343 170 | 338 621 | 0.2066 | 0.2067 |
| Code | 2.543 | 2.575 | +1.3% | 653 180 | 666 634 | 0.2569 | 0.2589 |
| Indic | 3.492 | 3.213 | −8.0% | 436 066 | 381 047 | 0.1249 | 0.1186 |

On this machine, encode **throughput** is similar for English and Code; Indic is faster for C3 in MB/s. **tokens/byte** is nearly identical on English, slightly higher for p1536 on Code, and lower for p1536 on Indic (fewer tokens for the same UTF-8 bytes).

Code / C3 run 1 was a cold outlier (1.54 MB/s vs ~2.5+); the median correctly ignores the outlier extremes.

## Cross-check

**Pending.** See `speed_crosscheck.json`. No second machine with the same artifacts was available. Official medians above are from this host only and were not averaged with any other environment.

## Limitations

- One-core affinity **not** verifiable on macOS.
- Indic corpus is 0.309 GB (all available), not 1 GB.
- Long wall-clock runs (~10 min per 1 GB encode); background load can move individual runs (hence median of three).
- Script lives in-repo because no prior tokenizer encode-speed harness existed under `teams/03-tokenizer/` (Data A `speed_check.py` times `clean.py`, not tokenizers).

## Reproduction

```bash
# sync
git fetch upstream main
git checkout -b G3/nrs/tokenizer-cpu-speed-v1 upstream/main

# C3 tokenizer (gitignored): place at teams/03-tokenizer/release/tokenizer.json
python teams/03-tokenizer/release/verify_release.py teams/03-tokenizer/release/tokenizer.json

# p1536: shasum -a 256 week3data/archive/tokenizer.json  # expect e6b93a93…

export GIT_COMMIT=$(git rev-parse HEAD)
python teams/03-tokenizer/harness/bench_cpu_speed.py \
  --data-root /path/to/week3data \
  --c3 teams/03-tokenizer/release/tokenizer.json \
  --p1536 /path/to/week3data/archive/tokenizer.json \
  --results-dir teams/03-tokenizer/results \
  --target-bytes 1000000000 --runs 3 --warmup 1
```

On Linux, pin with `taskset -c 0` (or rely on the script’s `sched_setaffinity`).

## Artifacts in this PR

| File | Role |
|---|---|
| `harness/bench_cpu_speed.py` | Benchmark script |
| `results/speed_v1.md` | This report |
| `results/speed_v1.json` | Raw runs + medians |
| `results/dataset_manifest.json` | Dataset provenance |
| `results/release_verification.log` | C3 + p1536 verification |
| `results/benchmark_execution.log` | Execution log |
| `results/speed_crosscheck.json` | Cross-check status (pending) |

## Contributors

- [@nitinranjansharma](https://github.com/nitinranjansharma) — verification, dataset prep, benchmark runs, report
