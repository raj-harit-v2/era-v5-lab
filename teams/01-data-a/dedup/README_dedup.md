# dedup.py: from overlap matches to a remove list

`dedup.py` turns the qualifying duplicate pairs from `overlap.py` into the list of documents to remove, with the rules of `source_priority_v1.md`. It never reads or rewrites document text: it writes IDs, scores and counts only. TSAI filters the cleaned data with the remove list (`dedup_design_v1.md`, "Pipeline and hand-off to TSAI").

```
overlap.py  ──▶  overlap_summary.json, overlap_matches.csv, overlap_docs.parquet  ──▶  dedup.py  ──▶  remove_list.csv, dedup_log.jsonl
```

## Run it

Python 3.10 or later with `pyarrow`, `numpy` and `scipy` (pinned in `requirements_overlap.txt`). It runs on Windows, macOS and Linux
(no WSL needed).

```sh
python3 -m pip install -r teams/01-data-a/dedup/requirements_overlap.txt pytest
python3 -m pytest -q teams/01-data-a/dedup/tests/test_dedup.py
python3 teams/01-data-a/dedup/dedup.py --config teams/01-data-a/dedup/dedup.json
```

Speed and equivalence evidence (PyArrow/SciPy rewrite, timings, exact command and output, how to rerun it with
`benchmark_dedup.py`): [benchmarks/2026-11-14-dedup-speed/README.md](benchmarks/2026-11-14-dedup-speed/README.md).

On Windows, if PowerShell refuses to run the venv's `Activate.ps1`, call the venv's Python directly (`<venv>\Scripts\python.exe ...`) or use Git Bash (`source <venv>/Scripts/activate`). Paths in the config are relative to the repository root, so the script can be started from any folder.

## Inputs

| Input | Used for |
|---|---|
| `overlap_summary.json` | The run must have `status: complete`; its `outputs` SHA-256 values check the two files below |
| `overlap_matches.csv` | The qualifying H1/H2 pairs that are joined into clusters |
| `overlap_docs.parquet` | Matrix row → `pack`, `split`, `part`, `row_in_part`, `doc_id`, `words` (rules 0, 3 and 4, and the remove list) |
| Cleaned parts (`inputs`, optional) | Each matched copy's `url`, for rule 2 |

`overlap_pairs.csv` is not used; it is for the hand review.

`dedup.py` stops with an error, before writing anything, if the overlap run did not complete, if a file's SHA-256 does not match the summary, or if a cleaned part's row is not the `doc_id` the run recorded.

## Config (`dedup.json`)

| Key | Meaning |
|---|---|
| `results` | Folder with the three overlap files. On TSAI's host: `out/overlap` |
| `inputs` | The cleaned parts (`train/`, `heldout/`) given to `overlap.py`, for rule 2's url. `""` skips rule 2 |
| `out` | Output folder, inside `out/` (default `out/dedup`) |
| `cross_pack` | `true` applies the cross-pack pass (E2 answered: applied in v1). `false` drops cross-pack matches without rerunning `overlap.py` |
| `pack_order` | All 38 pack IDs in `source_priority_v1.md` rule 4 order |
| `licence_usable` | `{pack_id: true/false}` from G10's licence table; packs not listed use `default_licence_usable` |
| `gold_dirs` | Folders with `<pack_id>_gold.csv`, for the harm check |

## The rules

Applied to each cluster in order; each breaks the ties left by the one above (`source_priority_v1.md`):

| Rule | Survivor |
|---|---|
| 0 | Every held-out copy; every train copy in the cluster is removed. Held-out ↔ held-out matches are reported, never removed |
| 1 | A copy whose pack has a usable licence. With none, every train copy is removed |
| 2 | A copy with a url (only when `inputs` is given) |
| 3 | The longer copy (`words`) |
| 4 | The pack ranked first in `pack_order`, then the lowest `(split, part, doc_id)` |

## Outputs (in `out`)

| File | Contents |
|---|---|
| `remove_list.csv` | What TSAI filters out: `pack_id, split, part, row_in_part, doc_id` |
| `dedup_log.jsonl` | One row per removed document: the removed and kept copies, `rule` (H1/H2), `similarity`, `priority_rule` (0–4), `stage` (`within_pack`, `cross_pack`, or `none` when no copy could survive), and `direct` (`false` when the copy reached the survivor only through other copies) |
| `heldout_duplicates.csv` | Held-out ↔ held-out matches, for G3 |
| `empty_documents.csv` | Documents with no shingles, for the cleaning team: `pack_id, split, part, row_in_part, doc_id`. Nothing is removed for them |
| `dedup_groups.csv` | Every duplicate group, one row per member: `group_id, group_size, priority_rule, role` (`survivor` or `removed`), `pack_id, split, part, row_in_part, doc_id`. Group IDs follow the lowest overlap row, so they are the same on every run of the same inputs. A group can have several survivors (every held-out copy, rule 0) or none (no usable licence, rule 1). For the F2 step after dedup: the groups whose survivor F2 removes are counted and listed from it (TSAI, 12 Nov) |
| `dedup_summary.json` | Per pack: documents in, removed by H1 / H2 / cross-pack, documents out; totals; how often each rule decided; the number of empty documents and of matches set aside for them; the harm check; the config; each output's size and SHA-256 |

A document is always identified by `(pack_id, split, part, row_in_part)` and its `doc_id`, never by `doc_id` alone: exact copies in different packs share a `doc_id`.

## Empty documents

A document with no shingles (`overlap_docs.parquet` column `shingles` = 0) is empty after normalisation. All such documents share one H1 key, so `overlap.py` reports them as exact copies of each other. They are not duplicates: cleaning emptied them without dropping them. `dedup.py` therefore sets their matches aside before forming clusters, removes none of them, and lists them in `empty_documents.csv`.

TSAI's 38-pack run has 7 such documents in `code-cpp`, `code-java` and `code-js-ts` (21 of its 98 H1 pairs; see `matrix_confirmation.md`). They pass `clean.py`'s empty-output check (`out.strip()`) but have no words after normalisation, so they stay in the data. Dropping them is a cleaning rule change for spec v1.1, not a dedup one.

## Harm check

With `gold_dirs` set, `dedup.py` counts the gold IDs present in the input and the gold documents removed, matched on `(pack_id, doc_id)`. The result is `pass`, `fail`, or `not_testable` when no gold ID is in the input. Gold comes from the week-1 diagnosis packs, so on the tokenizer sample the check is `not_testable`; run it on the diagnosis packs.

## Reruns

The same inputs and config give byte-identical outputs on any system (checked on Windows and Linux). A rerun therefore changes the result only when an input or a setting changed, and `dedup_summary.json` records both.

| What changed | Rerun |
|---|---|
| Licence map, pack order, cross-pack switch, gold folders | `dedup.py` only (seconds) |
| A duplicate rule (thresholds, numbers rule, minimum length) | `overlap.py` (TSAI job), then `dedup.py` |
| The data | Both |

## Results so far

On TSAI's 38-pack run of 5 Nov 2026 (1,416,236 documents; superseded by the rerun on the #244 cleaning, TSAI 12 Nov), without urls: 1,345 documents removed (0.095%: 1,289 H2, 56 H1; 1,309 within a pack, 36 across packs), 0 held-out removed, 63 train copies removed by rule 0. The 7 empty documents are listed in `empty_documents.csv`, not removed; before they were set aside, 1,351 documents were removed, 6 of them empty. Details in `results_v1.md`.
