# Overlap speed review evidence, 13 November 2026

The hashing dependencies are pinned: NumPy 2.2.6 and pandas 2.3.3. The tested environment also pins SciPy 1.15.3,
PyArrow 19.0.1 and Pygments 2.21.0, with Python 3.10+ required by NumPy. Validation used Python 3.12.12 on Linux/WSL2.
`overlap_summary.json` now records pandas as well as the other package versions. Missing pandas fails at startup with
the requirements-file installation command, before inputs are processed.

## Remaining token iteration

Word and token-window hashing uses `pandas.util.hash_array` plus NumPy arithmetic, with no Python loop over tokens
or 5-grams in that hashing step. `gram_set()` now decodes fixed-width digests in NumPy and builds the set without
our previous Python slicing comprehension. The void dtype preserves embedded and trailing zero bytes.

`code_shingles()` **still loops over the Pygments token iterator in Python** to apply v1 filtering: exclude comments
while preserving preprocessor directives, recognize a leading licence docstring only before the first retained token,
keep token values and case, and count nonblank lines after comment removal. Pygments lexers themselves use Python.
Moving the same generator into a comprehension or `fromiter` would retain per-token Python work. Replacing the lexer
or changing token boundaries would need separate rule-equivalence evidence. This remaining constraint is disclosed
for TSAI acceptance; this PR does not establish compliance with a strict ban on all Python token iteration.

## Reproduce inputs, configs, runs and comparisons

From the repository root, using an environment with Git and Python 3.10+:

```sh
python -m pip install -r teams/01-data-a/dedup/requirements_overlap.txt pytest==9.2.0
python -B -m pytest teams/01-data-a/dedup/tests -q -p no:cacheprovider
python -B teams/01-data-a/dedup/benchmark_overlap.py --out out/bench_speed_review --per-pack 4000 --runs 2
python -B teams/01-data-a/dedup/benchmark_overlap.py --out out/bench_speed_incremental --per-pack 4000 --runs 2 --baseline 1d934335175c631510cd7e88e4c98aaf88d0c4d9
```

Use new output directories on repeated invocations; the preparation refuses existing directories. The script:

1. Generates deterministic synthetic Parquet inputs: 4,000 documents each for code-rust, en-dclm and math-finemath,
   including edited copies, comment variants and exact copies. No downloads or credentials are used.
2. Snapshots the five scoring files and normalizer at baseline `43fa750` (or `--baseline`) and the current working
   files (or `--candidate-ref`). All snapshots, inputs, configs, logs and results go under the selected `out/` folder.
3. Writes identical configs: train only, those three expected packs, k=5, floor=0.5, block=256, default 50 MiB cap.
   Runs `python -I <snapshot>/teams/01-data-a/dedup/overlap.py --config <snapshot>/config.json`, alternating order.
4. Fails on any changed CSV/Parquet measurement, qualifying-pair row, sparse-matrix value, or summary count/rule.
   Summary timings, versions, output hashes and hashing description are expected to differ; NPZ ZIP bytes need not
   match when timestamps differ. The report records input hashes, scoring-file hashes, versions, timings and RSS.

For real cleaned inputs already staged locally, add `--inputs out/tokenizer_sample_v0_clean` with a new `--out`.
This selects the first 4,000 train rows per benchmark pack in sorted part/row order and records source and subset
hashes. It fails if a pack has fewer rows. The original PR's cleaned input subset and preparation artifacts are not
present in this checkout, so the measurements below use synthetic inputs. They do not reproduce or replace the
original reported 25% cleaned-sample speedup, and do not predict all-38-pack runtime.

## Results

| Comparison | Run | Baseline wall seconds | Updated wall seconds |
|---|---:|---:|---:|
| Before speed work (`43fa750`) | 1 | 15.375 | 13.936 |
| Before speed work (`43fa750`) | 2 | 15.961 | 14.461 |
| Original PR head (`1d93433`) | 1 | 13.732 | 13.667 |
| Original PR head (`1d93433`) | 2 | 13.675 | 13.718 |

The complete speed work is about 9.4% faster end to end on this synthetic workload. The follow-up changes produce
no material end-to-end speedup versus the original PR head (within timing variation). Peak RSS is 286–296 MiB.
A focused local decoder check (100,000 distinct eight-byte digests, 20 decodes, best of five) took 0.448 seconds
with the Python slicing comprehension and 0.340 seconds with NumPy decoding; whole-job gains depend on the workload.

Both comparisons passed: six CSV/Parquet files byte-identical, matches the same rows, sparse matrix the same values,
summary counts/config/rules unchanged. Full evidence is in `before-speed-report.json`, `incremental-report.json`,
and their corresponding `*-console.txt` files. Regression coverage includes binary digests containing zero bytes,
missing-pandas guidance, pinned hash values, brute-force pair scores, mixed domains, and code lexer rules.

Final pytest output is preserved in `pytest.txt`:

```text
115 passed
```
