# Tokenizer CPU speed benchmark v1

Encode throughput for the frozen **C3 sample-v0** tokenizer vs the **p1536** candidate on English, Code and Indic text. Median of three measured runs per configuration. No IN22 / FLORES fertility numbers here — speed only.

## Upstream sync

| Item | Value |
|---|---|
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
