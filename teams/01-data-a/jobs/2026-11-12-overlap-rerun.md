# Overlap rerun on the #244 cleaning of sample v0 — Thursday 12 November 2026

**Done, 15 Nov 2026.** TSAI ran this job (4,591 s, 77 min); results in PR #469
(`jobs/results/2026-11-12-overlap-rerun/`); the three large files came by TSAI's links on 16 Nov. After the results
returned: step 1 done (matrix confirmed, 20/20 and 23/23 checks; `dedup/overlap_matrix.csv` replaced; see
`dedup/matrix_confirmation.md`); step 2 done (`logs/2026-11-16-dedup-local.txt`, counts in `2026-11-14-dedup.md`);
step 3 done (E4 sheets rebuilt on the rerun, unchanged); step 4 done on 17 Nov (`results_v1.md`, `dedup_design_v1.md`; the dedup job's results are in #547).

**Updated 13 Nov 2026.** The code pin, scoring-file audit, input provenance and fresh local log are filled in.
Vijay Patil (`patilvijay23`) [approved the overlap rerun only](https://github.com/theschoolofai/era-v5-lab/pull/255#issuecomment-6871794399).
Dedup approval remains dependent on the returned overlap results and local validation. The speed work in
[kunal2016/era-v5-lab#1](https://github.com/kunal2016/era-v5-lab/pull/1) is merged. This request pins merged commit
`7526194f6a9cafd64416ff30fd149d19660d31f8`, validated with 115 tests and a fresh 38-pack synthetic smoke run.

**Updated 14 Nov 2026.** "Inputs and execution" names the folder TSAI's cleaning rerun wrote to and how to stage it.
The code pin, command and config are unchanged.

```text
Team:            01-data-a
Owner:           Aneesha Das (aneeshads)
Lead approval:   Vijay Patil (patilvijay23), overlap rerun only: https://github.com/theschoolofai/era-v5-lab/pull/255#issuecomment-6871794399
Question:        On the sample v0 cleaned with #244, what share of documents in each source has an H1 exact or eligible H2 near duplicate in each source, including its own?
Script:          teams/01-data-a/dedup/overlap.py (with h1_sha256.py, jaccard_matrix.py, overlap_rules.py, overlap_report.py and the frozen spec v1 normalize.py), PR #255 at commit 7526194f6a9cafd64416ff30fd149d19660d31f8
Command:         python -I teams/01-data-a/dedup/overlap.py --config teams/01-data-a/dedup/overlap.json
Config:          teams/01-data-a/dedup/overlap.json (unchanged from the 5 Nov run: the 38 sample-v0 packs)
Inputs:          All 38 sample-v0 packs from TSAI's completed #244 cleaning rerun (confirmed 13 Nov), staged under ./out/tokenizer_sample_v0_clean/{train,heldout}/ from TSAI's output folder ./out/tokenizer_sample_v0_clean_pr244_2026-11-12/ (see "Inputs and execution"); each Parquet row has pack_id, doc_id and text. Not the 3 Nov cleaned parts
Hardware:        CPU (single process; request 2 vCPU and 32 GiB RAM; no GPU)
Max time:        90 minutes
Precision:       not used
Measures:        Directional source-by-source document shares; matched-document numerators and source denominators; H1/H2 qualifying pairs; raw word-Jaccard threshold sweep and histogram; pack/part/split document counts; wall time, peak RSS, versions and output SHA-256
Expected result: 38 x 38 source matrix with values in [0,1], potentially asymmetric; counts to be measured. The 5 Nov run on the 3 Nov cleaning gives the scale, not expected values: 1,416,236 documents, 2,711 qualifying pairs (98 H1, 2,613 H2; 50 cross-pack), 7 empty documents, 56 minutes, 9.6 GiB peak
Outputs:         out/overlap/{overlap_matrix.csv,overlap_matrix_counts.csv,overlap_matches.csv,overlap_pairs.csv,overlap_by_pack.csv,overlap_histogram.csv,overlap_matrix.npz,overlap_docs.parquet,overlap_summary.json}; 50 MiB maximum including summary
Test log:        teams/01-data-a/jobs/logs/2026-11-13-overlap-rerun-merged.txt (merged scoring code; 115 tests; synthetic 38-pack overlap, matrix confirmation and dedup hand-off; not a measurement of TSAI data)
```

## Why a rerun

TSAI answered in G1 on 12 Nov: #244 changes the cleaner, so the cleaned sample of 3 Nov is out of date. TSAI runs the
#244 cleaning job on sample v0 after #244 is merged. The overlap measurement is then run again on the new cleaned output,
and the `dedup.py` job (`2026-11-14-dedup.md`) is approved and run on that output. The 5 Nov results
(`2026-11-04-overlap.md`) are not used.

This is the same measurement as `2026-11-04-overlap.md`, on new inputs. That request describes the method, the matrix
definition and the H1/H2 scope; they are unchanged and are not repeated here. The full method and reproduction commands
are in `dedup/README_overlap.md`.

## What changed since the 5 Nov run

| | 5 Nov run | This run |
|---|---|---|
| Cleaned input | #244's cleaner as of 3 Nov | #244's cleaner as merged (it changed on 10, 11 and 12 Nov) |
| Code | PR #255 at `86ecdd4` | PR #255 at the merged commit above: normalizer import fallback, bulk word/token hashing, NumPy digest decoding, deterministic code-pair order, dependency/version reporting; audit below |
| Rules | v1: prose 0.80 and 50 words, math 0.90 and the same numbers, code 0.85 tokens and 20 lines | Unchanged v1 rules for this request; math numbers, same-URL and Indic minimum changes remain separate proposals requiring evidence and approval |
| Max time | 60 minutes (it took 56) | 90 minutes, for headroom |

The normalizer contents are unchanged at this pin; the SHA-256 audit below confirms that H1 normalization is frozen.

## Scoring-file audit and completed cleaner provenance

At the pinned commit, `git diff 86ecdd4..7526194 --` on the five scoring files shows:

| File | Change |
|---|---|
| `h1_sha256.py` | Normalizer import path fallback from `5ac143a`; H1 key unchanged |
| `jaccard_matrix.py` | Bulk pandas/NumPy word and token-window hashing instead of BLAKE2b per gram; dependency guidance and hashing description |
| `overlap_rules.py` | Bulk token-window hashing and NumPy digest decoding; code pairs emitted in `(row_a, row_b)` order |
| `overlap.py` | pandas startup check and version reporting; Python 3.10+ guidance and hashing description |
| `overlap_report.py` | Unchanged |

Thresholds, length/number guards, lexer behavior and source-matrix semantics are unchanged. The merged speed PR's
reproducible 12,000-document synthetic comparison against `43fa750` confirms identical measurement CSV/Parquet
bytes, equivalent qualifying-pair rows and equal sparse scores; timing, versions, hashing descriptions and dependent
artifact hashes can differ. Evidence and full logs: `dedup/benchmarks/2026-11-13-speed/README.md`.

Pygments token filtering still iterates in Python to preserve v1 comment, licence-docstring and line-count rules.
This is disclosed for TSAI acceptance; merging the speed PR does not establish compliance with a strict ban on all
Python token iteration. The original reported cleaned-sample speedup is separate from the synthetic measurements.

The old `spec_v1/tools/normalize.py` and new `spec_v1/normalize.py` are byte-identical, SHA-256
`b96e39af6b048cf135e5915acb13c2d5630d1a238760df494776c6783a0a6669`.

[TSAI's confirmation](https://github.com/theschoolofai/era-v5-lab/pull/255#issuecomment-6870892120)
reports 86/86 parts, 0 errors and 1,414,996 cleaned rows from 1,444,766 input rows, using
`teams/01-data-a/jobs/2026-11-12-pr244-rerun/tokenizer_sample_v0_clean.json`:

| Cleaner provenance | SHA-256 |
|---|---|
| clean | `22d818c72c9f30bf338de344a0fcda230e2d1de30a1aaec5d92bc525bae99179` |
| config | `8c58030f51e3d9f338f59719daa91b6ab59614f3ffdb9c60bb35997b35ea63ec` |
| manifest | `7fd647c8d4662d17e2310efbcc20981d70656fdad2fabb7663c266a2153a1b7e` |

Stage those completed cleaner outputs at the configured input path. Check the returned overlap inventory against
86 parts and 1,414,996 rows before accepting results. These checks establish counts and provenance; cleaned-input
checksum verification inside `overlap.py` remains deferred.

## Reproduce the local test

From the repository root, with the overlap requirements and pytest installed:

```sh
python -I teams/01-data-a/jobs/2026-11-12-overlap-rerun/prepare_local.py
python -I teams/01-data-a/dedup/overlap.py --config out/overlap_rerun_local/overlap.json
python -I teams/01-data-a/dedup/confirm_matrix.py --results out/overlap_rerun_local/overlap --docs out/overlap_rerun_local/overlap/overlap_docs.parquet --out out/overlap_rerun_local/matrix_confirmation
python -I teams/01-data-a/dedup/dedup.py --config out/overlap_rerun_local/dedup.json
python -B -m pytest teams/01-data-a/dedup/tests -q -p no:cacheprovider
```

The preparation script refuses an existing `out/overlap_rerun_local/` directory. It creates 152 artificial documents
in 76 parts across all 38 configured packs, including train/heldout copies. Its configs write to a separate smoke
output directory. The attached log records the commands, versions, complete overlap/dedup console output and pytest
result. The merged run completes with 38 H1 and 72 H2 pairs; dedup removes 74 train documents in 38 groups and no
held-out document. Matrix confirmation passes and removed group members match the remove list. The synthetic harm
check is `not_testable` because these are artificial IDs. This checks execution and the hand-off; it cannot predict
counts or runtime on the actual cleaned sample or replace diagnosis-pack harm evidence.

## Inputs and execution

TSAI's #244 cleaning rerun wrote its parts to `out/tokenizer_sample_v0_clean_pr244_2026-11-12/{train,heldout}/`
(`output_root` in `teams/01-data-a/jobs/2026-11-12-pr244-rerun/tokenizer_sample_v0_clean.json`). `overlap.json` reads
`out/tokenizer_sample_v0_clean/`, so stage those parts there before the run, as on 5 Nov: first move any 3 Nov parts out
of `out/tokenizer_sample_v0_clean/`, so that it holds only the 12 Nov parts (48 train, 38 held-out). The command and the
config stay as approved. The inventory check above shows if the wrong parts were read: the 12 Nov parts have 1,414,996
rows, the 3 Nov parts had 1,416,236. The dedup job (`2026-11-10-dedup.md`) reads the same staged folder.

`overlap.json` asserts the exact 38-pack inventory before scoring; a missing or unexpected pack fails. Packs that #244's
cleaner does not support pass through it unchanged and are still in the inventory.

Before the offline run, install `teams/01-data-a/dedup/requirements_overlap.txt`: `numpy==2.2.6`, `pandas==2.3.3`,
`scipy==1.15.3`, `pyarrow==19.0.1`, `pygments==2.21.0`. Use Python 3.10+ on Linux or macOS (validated with 3.12.12).
No network access or keys during the job; all output stays under `out/`. Stop at 90 minutes and return
the partial console log if the limit is reached; incomplete output must not be used.

## Returned artifacts

Return the nine output files and the console log to `teams/01-data-a/jobs/results/2026-11-12-overlap-rerun/`, as
described in `JOB_REQUEST.md`. On 5 Nov, `overlap_docs.parquet` (34 MB) and `overlap_pairs.csv` (6.7 MB) stayed out of
the repository and were sent separately. Please send them again the same way: `dedup.py` needs `overlap_docs.parquet`,
and the matrix confirmation, E4 and the hand review need both.

## After the results return

1. Rebuild and confirm the matrix: `python teams/01-data-a/dedup/confirm_matrix.py --results <returned folder>`, and
   with `--docs` once `overlap_docs.parquet` is here. Replace `teams/01-data-a/dedup/overlap_matrix.csv` with the
   confirmed matrix and update `matrix_confirmation.md`.
2. Run `dedup.py` locally on the returned files without urls and add its counts to `2026-11-14-dedup.md`; then the lead
   approves that job.
3. Run `e4_review.py` again on the new outputs before an Indic reader labels the pairs.
4. Replace the 5 Nov numbers in `results_v1.md`, `dedup_design_v1.md` and `source_priority_v1.md`.
