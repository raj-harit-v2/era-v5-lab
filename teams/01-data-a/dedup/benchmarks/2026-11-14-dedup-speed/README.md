# dedup.py speed evidence, 14 November 2026

The change ([kunal2016/era-v5-lab#2](https://github.com/kunal2016/era-v5-lab/pull/2), Aneesha Das's review of the
speed work): the work over every document in `dedup.py` moves from Python loops to PyArrow and SciPy.

- `read_docs`: matched and empty rows picked with `pc.is_in`, documents per pack with `pc.value_counts`, gold IDs found
  in one `pc.is_in` pass (a gold ID still counts once per pack). Only those rows become Python objects, not all 1.4M.
- `read_gold`: gold sets read once; `harm_check` gets the sets and the counts.
- `read_urls`: only the needed rows of each part (`take`), each still checked against its `doc_id`.
- `clusters`: SciPy `connected_components` in place of the Python union-find.

`dedup.py` now needs `numpy` and `scipy` besides `pyarrow`; all three are pinned in `requirements_overlap.txt`.

## Results are unchanged

Against `0011cc4` (the `g1-dedup-design` head before this change), on three overlap runs that cover every path:

| Input | Documents | What it exercises | Outputs |
|---|---:|---|---|
| TSAI's 38-pack overlap run of 5 Nov (`dedup_gold_main`) | 1,416,236 | Size; no cleaned parts, so rule 2 is skipped | **SAME** |
| The 4 week-1 diagnosis packs (`dedup_diag2`) | 1,964 | Cleaned parts, so rule 2 reads urls; 727 gold IDs present | **SAME** |
| The math E1 run (`dedup_math`) | 47,250 | Raw parts with urls | **SAME** |

SAME means `remove_list.csv`, `dedup_log.jsonl`, `heldout_duplicates.csv`, `empty_documents.csv` and
`dedup_groups.csv` are byte-identical, and every count in `dedup_summary.json` is equal (only `config`, `outputs` and
`seconds` may differ). New test: a gold ID held by several rows of one pack counts once. **116 tests pass**
(`pytest.txt`).

## Time and memory

Linux, 2 CPU, no GPU (a CPU job: the rule's GPU checks don't apply). 4 runs per version, alternating order; median
(min–max). Full numbers in `report.json`.

| Input | 0011cc4 (before) | After |
|---|---|---|
| TSAI's 5 Nov files | 2.60 s (2.34–5.28), **1,044 MB** | 2.24 s (1.63–5.37), **400 MB** |
| Diagnosis packs | 0.93 s (0.85–0.97), 125 MB | 1.08 s (1.02–1.13), 147 MB |
| Math E1 | 1.13 s (0.96–1.29), 218 MB | 1.20 s (1.06–1.55), 222 MB |

On the large run: about 14% faster and **62% less memory**. The memory is the main gain: the old code held every
document as Python objects, so its memory grew with the corpus. On small inputs the new code is about 0.1–0.15 s slower,
the cost of loading SciPy. Timings on this machine vary between runs (the first run of each is often slow), hence the
medians.

No Python loop runs over every document any more. The loops left run over matches (2,690 on the TSAI files), groups or
gold files, which are small.

## Exact command and output

```sh
python3 -B teams/01-data-a/dedup/benchmark_dedup.py \
    --configs out/dedup_gold_main.json out/dedup_diag2.json out/dedup_math.json \
    --baseline 0011cc4 --runs 4 --out out/bench_dedup_20261114_r4
```

```
dedup_gold_main: baseline 5.28 s / 1050 MB, 2.62 s / 1044 MB, 2.58 s / 1042 MB, 2.34 s / 1043 MB | candidate 5.37 s / 398 MB, 2.64 s / 401 MB, 1.83 s / 411 MB, 1.63 s / 388 MB | SAME
dedup_diag2: baseline 0.95 s / 125 MB, 0.85 s / 125 MB, 0.91 s / 125 MB, 0.97 s / 125 MB | candidate 1.13 s / 147 MB, 1.11 s / 147 MB, 1.04 s / 147 MB, 1.02 s / 147 MB | SAME
dedup_math: baseline 0.97 s / 212 MB, 0.96 s / 217 MB, 1.29 s / 218 MB, 1.29 s / 221 MB | candidate 1.06 s / 218 MB, 1.08 s / 233 MB, 1.55 s / 221 MB, 1.31 s / 222 MB | SAME
ALL SAME - report: out/bench_dedup_20261114_r4/report.json
```

The console output of one run per version and input is in `*-console.txt` (counts only, no document text).

## Reproducing it

`benchmark_dedup.py` takes the baseline `dedup.py` from git, runs both versions on each config, and fails if anything
differs. Each config is a copy of `dedup.json` pointing at a local overlap run:

| Config | `results` | `inputs` | `gold_dirs` |
|---|---|---|---|
| `dedup_gold_main` | TSAI's 5 Nov overlap outputs | none | Data A and Data B gold, plus `cadj-commits_gold.csv` from `main` (6b09da4) |
| `dedup_diag2` | the diagnosis-pack overlap run (`jobs/logs/2026-11-11-dedup-harm-diag-local.txt`) | the 4 cleaned diagnosis packs | as above |
| `dedup_math` | the math E1 overlap run | raw sample-v0 math parts | Data A gold |

TSAI's overlap files are for Data A only and are not in the repo, so the first row can only be rerun by someone who has
them. The diagnosis-pack run (steps in the harm-check log) is small and easier to repeat.
