# Matrix confirmation: TSAI's 38-pack overlap rerun

**Date:** Sunday 15 November 2026. **By:** Aneesha Das (aneeshads).
**Run confirmed:** job `jobs/2026-11-12-overlap-rerun.md`, run by TSAI on 15 Nov 2026 at commit `7526194` on the
sample-v0 packs cleaned by the merged #244 cleaner (sha256 `22d818c7…bae99179`). Results in #469,
`teams/01-data-a/jobs/results/2026-11-12-overlap-rerun/`.
This replaces the confirmation of the 5 Nov run (`jobs/2026-11-04-overlap.md`), whose results the rerun supersedes.

## Result

- **Confirmed: 20 of 20 checks passed.** The source-by-source matrix rebuilt from TSAI's `overlap_matches.csv`, with
  the row → pack map rebuilt from the part order in the summary, is **byte-identical** to the returned
  `overlap_matrix.csv` and `overlap_matrix_counts.csv`.
- The five returned outputs equal the SHA-256 and size the run recorded in `overlap_summary.json`.
- The run: **1,414,996 documents** in 38 packs and 86 parts (48 train, 38 held-out); **2,750 qualifying pairs**
  (98 H1 in 71 exact groups of 150 documents, 2,652 H2; 2,700 within a pack, 50 across packs); 7 empty documents.
- **One caveat for the reviewed matrix:** 8 cells (code-cpp, code-java, code-js-ts) are inflated by the 7 documents
  that are empty after normalisation and therefore match each other. The cells are correct for what `overlap.py`
  measures, but these are not real duplicates (see "The empty-document group").
- **Checked on 16 Nov (Kunal Sinha), after TSAI sent the three large files by link:** with
  `--docs out/overlap_rerun/overlap_docs.parquet`, **23 of 23 checks passed** (the map read from the parquet: 1,414,996
  rows, 2,750 matches on 2,436 distinct rows, 0 pack mismatches; rebuilt matrices byte-identical); the job request's
  own command, `overlap_report.py --results out/overlap_rerun`, wrote both matrix files byte-identical to the returned
  ones; and all 9 outputs, including `overlap_docs.parquet`, `overlap_pairs.csv` and `overlap_matrix.npz`, equal the
  SHA-256 and size in the summary. Run with this commit's `confirm_matrix.py` and `overlap_report.py`.

## What the matrix is

`overlap_matrix.csv` is a 38 × 38 table. Row pack A, column pack B: the share of A's documents that have at least one
qualifying H1 or H2 match in B. A document counts once per column, however many copies it has. The diagonal is
within-pack and excludes a document matching itself. The matrix is directional: A→B and B→A have different
denominators. `overlap_matrix_counts.csv` holds each cell's numerator (`matched_documents`) and denominator
(`total_documents`).

## Inputs

The returned files of #469 (head commit `064e054b`), in `out/overlap_rerun/` (git-ignored):

| File | Bytes | SHA-256 | Equals the summary |
|---|---:|---|---|
| `overlap_matches.csv` | 209,637 | `ff8e4feec9f390cd78648ed0808095db1c8baf8484a5ed1a9c8a9016398d0433` | yes |
| `overlap_matrix.csv` | 19,866 | `b89c4909a2d77335674cedfd9f16d599a93b00b861e58e4a3d4eebc5da54bacb` | yes |
| `overlap_matrix_counts.csv` | 52,511 | `6e908ec7bf070110ede515f31403ac1529ac207b4dc9c21c244ec56417562468` | yes |
| `overlap_by_pack.csv` | 238,211 | `2deea68e96e505b6d260ac542720ba33dad5201bf6d8e1ed9692f442e6fb786b` | yes |
| `overlap_histogram.csv` | 1,692 | `5abf12186bcf9223ec5bf813c3e9d95011793fcdda0ca2b1ab0a648b8a9e05c4` | yes |
| `overlap_summary.json` | 272,952 | `37e7b26ef471f8400243b0f69b9b4eaab3515fd4b51a32f2cb156037a14c41d9` | not recorded by the run |
| `overlap_docs.parquet` | 34,015,494 | `4f61c80a23a9e49b4b12b2d6aaff639771d70fc2dd130f0a73d99a8449992e30` | yes (by TSAI's link, 16 Nov) |
| `overlap_pairs.csv` | 6,643,296 | `de7dd2d3c056909cc1bba12ef7353a22a783d921b9ee20cdc57bc56883f828e4` | yes (by TSAI's link, 16 Nov) |
| `overlap_matrix.npz` | 4,400,672 | `74f6cb30ae07eac5cb165bd9e80b2ff5175ad0954d86ae1be3a7af80e14930a5` | yes (by TSAI's link, 16 Nov) |

## Steps

**1. Stage the returned files** (from the repository root):

```sh
mkdir -p out/overlap_rerun && cd out/overlap_rerun
B=https://raw.githubusercontent.com/theschoolofai/era-v5-lab/064e054b5d8a2575c3b7c7399b4776623c0e5517/teams/01-data-a/jobs/results/2026-11-12-overlap-rerun
for f in overlap_summary.json overlap_matches.csv overlap_matrix.csv overlap_matrix_counts.csv overlap_by_pack.csv overlap_histogram.csv; do curl -sSfL -o "$f" "$B/$f"; done
cd ../..
```

**2. Run the confirmation with the map rebuilt from the part order:**

```sh
python3 teams/01-data-a/dedup/confirm_matrix.py --results out/overlap_rerun --out out/matrix_confirmation_rerun
```

Last lines of its output:

```
PASS  rebuilt overlap_matrix.csv is byte-identical to the returned file                  sha256 b89c4909a2d77335674cedfd9f16d599a93b00b861e58e4a3d4eebc5da54bacb
PASS  rebuilt overlap_matrix_counts.csv is byte-identical to the returned file           sha256 6e908ec7bf070110ede515f31403ac1529ac207b4dc9c21c244ec56417562468
PASS  overlap_matrix.csv is packs x packs, in sorted order                               38 rows x 38 columns
PASS  overlap_matrix_counts.csv has one cell per pair of packs                           1,444 cells (38 x 38)
PASS  every denominator equals its pack's document count                                 0 differ
PASS  every share equals matched / total (10 decimals)                                   0 differ
PASS  the empty documents form exactly one H1 group                                      7 empty documents; H1 groups of that size: 1

20 of 20 checks passed; wrote out/matrix_confirmation_rerun/confirmation.json and the rebuilt matrices
```

macOS (arm64), Python 3.12.10: 0.22 s wall time, peak memory 26 MiB (26,902,528 bytes). Exit 0.

`confirm_matrix.py` reads no document text and writes only beneath `out/`. It uses `overlap_report.write_matrix`, the
same function `overlap.py` used to write the returned matrix. It does this:

1. Checks the run: `status` is `complete`, and the 38 packs equal the config's `expected_packs`.
2. Hashes every returned output and compares its SHA-256 and size with `overlap_summary.json`.
3. Builds the row → pack map and checks it against the matches (see "Row → pack map" below).
4. Rebuilds `overlap_matrix.csv` and `overlap_matrix_counts.csv` from `overlap_matches.csv` and compares them with the
   returned files byte for byte.
5. Checks the content: 38 × 38 with packs in sorted order, every denominator equal to the pack's document count, every
   share equal to matched ÷ total to 10 decimals.
6. Finds the group of empty documents (the H1 group whose size equals `empty_documents`) and rebuilds the matrix
   without the pairs inside it, for review.

**Row → pack map.** `overlap.py` numbers documents 0 to N−1 in the order it reads the parts, and that order is the
part list in `overlap_summary.json` (`inputs.parts`), so step 2 rebuilds the map from that list, keeping one entry per
part (`overlap_report.RowRuns`; a row's pack is found by bisecting the part starts). With `--docs`, the map is read
with `overlap_report.read_docs`, which requires the rows to be 0..N−1 in order. It is accepted only because:
- the 86 parts add up to 1,414,996 documents, equal to `documents_all`;
- the per-pack train and held-out counts from the parts equal the summary's, which `overlap.py` counted from each row's
  `pack_id` (38 packs × 2 splits);
- all 2,436 distinct rows in the 2,750 matches fall in the pack `overlap_matches.csv` names for them (0 mismatches).

On the 5 Nov run, the map rebuilt this way equalled `overlap_docs.parquet` on every row.

## Checks: 20 of 20 passed

| # | Check | Result | Detail |
|---:|---|---|---|
| 1 | Overlap run status is `complete` | PASS | `complete` |
| 2 | The packs equal the config's `expected_packs` | PASS | 38 packs |
| 3 | `overlap_by_pack.csv` SHA-256 and size equal the summary | PASS | 238,211 bytes |
| 4 | `overlap_histogram.csv` SHA-256 and size equal the summary | PASS | 1,692 bytes |
| 5 | `overlap_matches.csv` SHA-256 and size equal the summary | PASS | 209,637 bytes |
| 6 | `overlap_matrix.csv` SHA-256 and size equal the summary | PASS | 19,866 bytes |
| 7 | `overlap_matrix_counts.csv` SHA-256 and size equal the summary | PASS | 52,511 bytes |
| 8 | The parts add up to `documents_all` | PASS | 86 parts, 1,414,996 documents |
| 9 | Per-pack train / held-out counts from the parts equal the summary | PASS | 38 packs × 2 splits agree |
| 10 | Every matched row is in the pack `overlap_matches.csv` names | PASS | 2,750 matches, 2,436 rows, 0 mismatches |
| 11 | Every `stage` label agrees with its packs | PASS | 0 disagree |
| 12 | No document is matched with itself | PASS | |
| 13 | Rule counts equal `qualifying_pairs_by_rule` | PASS | H1 98, H2 2,652 |
| 14 | Rebuilt `overlap_matrix.csv` is byte-identical to the returned file | PASS | SHA-256 `b89c4909…54bacb` |
| 15 | Rebuilt `overlap_matrix_counts.csv` is byte-identical to the returned file | PASS | SHA-256 `6e908ec7…562468` |
| 16 | `overlap_matrix.csv` is packs × packs, in sorted order | PASS | 38 rows × 38 columns |
| 17 | `overlap_matrix_counts.csv` has one cell per pair of packs | PASS | 1,444 cells (38 × 38) |
| 18 | Every denominator equals its pack's document count | PASS | 0 differ |
| 19 | Every share equals matched ÷ total (10 decimals) | PASS | 0 differ |
| 20 | The empty documents form exactly one H1 group | PASS | 7 empty documents, 1 group of 7 |

## What the matrix shows

- **1,444 cells, 58 non-zero:** 20 on the diagonal (within a pack) and 38 off it (across packs).
- **2,436 documents (0.172%)** have at least one qualifying match: 2,363 matched within their own pack (the diagonal
  numerators added up) and 79 (0.0056%) with a copy in another pack. A document can count in both.
- **9 packs have no match at all:** `ind-gu-fw2`, `ind-hi-hplt`, `ind-kn-sangraha-s`, `ind-ml-fw2`, `ind-or-fw2`,
  `ind-ta-fw2`, `ind-ta-sangraha-v`, `ind-te-sangraha-s`, `sci-finepdfs`.
- **The largest cross-pack share is 0.044%** (`ind-mr-fw2` → `ind-mr-sangraha-v`); every off-diagonal cell is below
  0.05%.
- **Directional counts:** every cross-pack pair of packs has the same number of matched documents in both directions,
  except three code pairs (code-cpp ↔ code-java, code-cpp ↔ code-js-ts, code-java ↔ code-js-ts). All three come from
  the empty-document group.
- **Train ↔ held-out pairs among the matches: 64.**

**Against the 5 Nov run** (1,416,236 documents, 2,711 pairs): 1,240 fewer documents, 39 more H2 pairs, the same 98 H1
pairs and 50 cross-pack pairs. The number of matched documents is unchanged (2,436; 2,363 own pack, 79 cross-pack).
`ind-ta-fw2` ↔ `ind-ta-sangraha-v` no longer match (1 document each way before), `ind-hi-indiccorp` ↔
`ind-hi-sangraha-v` went from 1 to 2 documents each way, and train ↔ held-out pairs went from 63 to 64.

### Per pack (diagonal and cross-pack documents)

"Own pack" is the diagonal cell; "other packs" is the number of distinct documents with a copy in any other pack.

| Pack | Documents | Matched, own pack | Share, own pack | Matched, other packs | Other packs reached |
|---|---:|---:|---:|---:|---:|
| `cadj-commits` | 75,579 | 1,664 | 2.2017% | 9 | 4 |
| `cadj-stackexchange` | 41,805 | 384 | 0.9186% | 0 | 0 |
| `ind-hi-sangraha-s` | 7,542 | 37 | 0.4906% | 0 | 0 |
| `ind-sa-fw2` | 5,721 | 23 | 0.4020% | 0 | 0 |
| `cadj-notebooks` | 15,732 | 27 | 0.1716% | 0 | 0 |
| `ind-hi-sangraha-v` | 14,614 | 18 | 0.1232% | 3 | 2 |
| `math-megamath` | 17,803 | 20 | 0.1123% | 1 | 1 |
| `code-rust` | 58,795 | 66 | 0.1123% | 3 | 1 |
| `ind-ta-sangraha-s` | 4,372 | 2 | 0.0457% | 0 | 0 |
| `en-dclm` | 60,802 | 19 | 0.0312% | 5 | 2 |
| `en-nemotroncc` | 89,183 | 27 | 0.0303% | 6 | 2 |
| `math-finemath` | 28,830 | 6 | 0.0208% | 2 | 2 |
| `en-fineweb-edu` | 72,100 | 14 | 0.0194% | 11 | 4 |
| `code-cpp` | 55,195 | 10 | 0.0181% | 2 | 3 |
| `code-python` | 73,305 | 13 | 0.0177% | 4 | 1 |
| `code-go` | 77,765 | 12 | 0.0154% | 0 | 0 |
| `code-java` | 85,518 | 10 | 0.0117% | 5 | 3 |
| `ind-hi-indiccorp` | 110,755 | 7 | 0.0063% | 2 | 1 |
| `code-js-ts` | 117,208 | 2 | 0.0017% | 2 | 2 |
| `en-nemotroncc-synth` | 198,877 | 2 | 0.0010% | 1 | 1 |
| `ind-bn-fw2` | 10,809 | 0 | 0 | 1 | 1 |
| `ind-bn-sangraha-v` | 10,217 | 0 | 0 | 1 | 1 |
| `ind-hi-fw2` | 13,932 | 0 | 0 | 1 | 1 |
| `ind-kn-fw2` | 7,841 | 0 | 0 | 3 | 1 |
| `ind-kn-sangraha-v` | 8,444 | 0 | 0 | 3 | 1 |
| `ind-mr-fw2` | 11,353 | 0 | 0 | 5 | 1 |
| `ind-mr-sangraha-v` | 12,299 | 0 | 0 | 5 | 1 |
| `ind-te-fw2` | 5,763 | 0 | 0 | 2 | 1 |
| `ind-te-sangraha-v` | 8,678 | 0 | 0 | 2 | 1 |
| `ind-gu-fw2` | 23,011 | 0 | 0 | 0 | 0 |
| `ind-hi-hplt` | 8,515 | 0 | 0 | 0 | 0 |
| `ind-kn-sangraha-s` | 5,238 | 0 | 0 | 0 | 0 |
| `ind-ml-fw2` | 19,161 | 0 | 0 | 0 | 0 |
| `ind-or-fw2` | 34,012 | 0 | 0 | 0 | 0 |
| `ind-ta-fw2` | 6,824 | 0 | 0 | 0 | 0 |
| `ind-ta-sangraha-v` | 6,861 | 0 | 0 | 0 | 0 |
| `ind-te-sangraha-s` | 4,463 | 0 | 0 | 0 | 0 |
| `sci-finepdfs` | 6,074 | 0 | 0 | 0 | 0 |
| **All 38** | **1,414,996** | **2,363** | | **79** | |

### Cross-pack cells (38 cells, 19 pairs of packs)

Matched documents of A with a copy in B, and the share of A; then the same for B → A.

| Pack A | Pack B | A → B | Share of A | B → A | Share of B |
|---|---|---:|---:|---:|---:|
| `en-fineweb-edu` | `en-nemotroncc` | 5 | 0.0069% | 5 | 0.0056% |
| `ind-mr-fw2` | `ind-mr-sangraha-v` | 5 | 0.0440% | 5 | 0.0407% |
| `cadj-commits` | `code-python` | 4 | 0.0053% | 4 | 0.0055% |
| `en-dclm` | `en-fineweb-edu` | 4 | 0.0066% | 4 | 0.0055% |
| `code-java` | `code-cpp` | 4 | 0.0047% | 1 | 0.0018% |
| `code-java` | `code-js-ts` | 4 | 0.0047% | 2 | 0.0017% |
| `cadj-commits` | `code-rust` | 3 | 0.0040% | 3 | 0.0051% |
| `ind-kn-fw2` | `ind-kn-sangraha-v` | 3 | 0.0383% | 3 | 0.0355% |
| `code-js-ts` | `code-cpp` | 2 | 0.0017% | 1 | 0.0018% |
| `ind-hi-indiccorp` | `ind-hi-sangraha-v` | 2 | 0.0018% | 2 | 0.0137% |
| `ind-te-fw2` | `ind-te-sangraha-v` | 2 | 0.0347% | 2 | 0.0230% |
| `cadj-commits` | `code-cpp` | 1 | 0.0013% | 1 | 0.0018% |
| `cadj-commits` | `code-java` | 1 | 0.0013% | 1 | 0.0012% |
| `en-dclm` | `en-nemotroncc` | 1 | 0.0016% | 1 | 0.0011% |
| `en-fineweb-edu` | `en-nemotroncc-synth` | 1 | 0.0014% | 1 | 0.0005% |
| `en-fineweb-edu` | `math-finemath` | 1 | 0.0014% | 1 | 0.0035% |
| `ind-bn-fw2` | `ind-bn-sangraha-v` | 1 | 0.0093% | 1 | 0.0098% |
| `ind-hi-fw2` | `ind-hi-sangraha-v` | 1 | 0.0072% | 1 | 0.0068% |
| `math-finemath` | `math-megamath` | 1 | 0.0035% | 1 | 0.0056% |

## The empty-document group

The summary reports 7 empty documents (no word left after normalisation). Empty documents all have the same H1 key, so
they always form one complete H1 group. Exactly one of the 71 H1 groups has 7 members (the others: 68 of 2, one of 3,
one of 4):

| Row | Pack | Split |
|---:|---|---|
| 173629 | `code-cpp` | train |
| 305920 | `code-java` | train |
| 309041 | `code-java` | train |
| 331691 | `code-java` | train |
| 347544 | `code-java` | train |
| 360063 | `code-js-ts` | train |
| 404794 | `code-js-ts` | train |

These are the same 7 rows as the empty documents of the 5 Nov run. Their `doc_id`, part and row in part come from
`overlap_docs.parquet` (see "Open").

They make **21 of the 98 H1 pairs** and **14 of the 50 cross-pack pairs**. These are files that cleaning emptied but did
not drop, not real duplicates. Without the pairs inside the group, 8 cells change:

| From | To | Matched now | Matched without the group | Documents of A |
|---|---|---:|---:|---:|
| `code-cpp` | `code-java` | 1 | 0 | 55,195 |
| `code-cpp` | `code-js-ts` | 1 | 0 | 55,195 |
| `code-java` | `code-cpp` | 4 | 0 | 85,518 |
| `code-java` | `code-java` | 10 | 6 | 85,518 |
| `code-java` | `code-js-ts` | 4 | 0 | 85,518 |
| `code-js-ts` | `code-cpp` | 2 | 0 | 117,208 |
| `code-js-ts` | `code-java` | 2 | 0 | 117,208 |
| `code-js-ts` | `code-js-ts` | 2 | 0 | 117,208 |

Without the group the matrix has 51 non-zero cells (19 diagonal, 32 cross-pack), 72 documents have a cross-pack copy
instead of 79, and every cross-pack pair of packs has equal counts in both directions. The rebuilt files without the
group are in `out/matrix_confirmation_rerun/without_empty_documents/`, for review only.

The reviewed matrix is TSAI's, unchanged, since it is exactly what the job measured. `dedup.py` sets aside the matches
between documents with no shingles and removes none of them (`README_dedup.md`, "Empty documents").

## Tests

`tests/test_confirm_matrix.py` runs `confirm_matrix.py` on small made-up overlap runs, with no real data:

```sh
python3 -B -m pytest teams/01-data-a/dedup/tests/test_confirm_matrix.py -q -p no:cacheprovider
```

Result on 15 Nov 2026 (macOS arm64, Python 3.12.10, pytest 9.1.1): **12 passed in 0.86 s.** The row maps themselves
(`RowRuns`, `read_docs`) are tested in `tests/test_overlap_report.py`: 9 passed in 0.54 s.

**The made-up run.** Every test builds it in a temporary folder, so nothing in the real repository is touched:
- **Documents:** 9 in 2 packs. `en-a` has train rows 0–3 and held-out row 7; `en-b` has train rows 4–6 and held-out
  row 8.
- **Matches:** 4 qualifying pairs: one within `en-a`, one exact pair across the two packs, and two train ↔ held-out
  pairs.
- **Matrix files:** written with `overlap_report.write_matrix`, the function `overlap.py` uses.
- **Summary:** records each file's SHA-256 and size, as TSAI's does.

Each test then changes one thing and checks that the script reacts correctly.

| # | Test | What it changes | What it proves |
|---:|---|---|---|
| 1 | `test_matching_run_is_confirmed` | Nothing; the run is consistent | All checks pass, exit 0, and the rebuilt files are identical. The counts come out right: 8 documents with a match, 2 with a cross-pack copy, 2 train ↔ held-out pairs, 2 non-zero cross-pack cells. |
| 2 | `test_changed_matrix_is_not_byte_identical` | One share in the matrix becomes 0.5000000001 instead of 0.5000000000, and the summary's hash is updated to hide it | Exactly two checks fail: "byte-identical" and "share = matched ÷ total". The rebuild catches an error that a hash check alone would miss. |
| 3 | `test_file_that_differs_from_the_summary_fails` | An extra row is added to the matches file | The SHA-256 check fails. A file that is not the run's own is refused. |
| 4 | `test_wrong_part_order_is_caught_by_the_matches` | The summary lists the parts in a different order | The per-pack counts still agree, but rows land in the wrong packs, and the matches check catches it. This is the key safeguard for building the map without `overlap_docs.parquet`. |
| 5 | `test_part_counts_that_disagree_with_the_summary_fail` | The part list says `en-a` has 5 train documents instead of 4 | The per-pack count check fails. |
| 6 | `test_empty_document_group_is_reported_and_removed_for_review` | 3 "empty" documents (rows 0 and 1 in `en-a`, row 4 in `en-b`) form one exact group, plus one real pair | The group is found, with 3 pairs inside it, 2 of them cross-pack. The changed cells are exact: `en-a→en-a` 4→2, `en-a→en-b` 2→0, `en-b→en-a` 1→0. The review copy is written, and the group is reported, not failed. |
| 7 | `test_empty_documents_without_one_group_fail` | The summary says 3 empty documents, but no exact group has 3 members | The check fails, so the script never guesses which documents are empty. |
| 8 | `test_docs_parquet_route` | `--docs` with an `overlap_docs.parquet` | The row → pack map is read from the parquet after its hash is checked, and everything passes. This is the route for when TSAI sends the file. |
| 9 | `test_docs_parquet_with_another_hash_fails` | The summary records a different hash for the parquet | The parquet is refused. |
| 10 | `test_docs_parquet_with_rows_out_of_order_returns_2` | `--docs` with a parquet whose first two rows are swapped (hash updated to match) | The run stops with exit code 2, since the map needs rows 0..N−1 in order. |
| 11 | `test_missing_input_returns_2` | The counts file is deleted | The run stops with exit code 2 before any check. |
| 12 | `test_out_must_be_inside_out` | `--out elsewhere` | Writing outside `out/` is refused, as `JOB_REQUEST.md` requires. |

## Limits

- This confirms that the matrix follows exactly from the qualifying matches. It does not check whether each match is a
  true duplicate; that is the hand review (prose, code, `cadj-commits`) and E4.
- `overlap.py` does not record the summary's own SHA-256.

## Open

1. **Done 16 Nov:** the `--docs` check and `overlap_report.py --results` (see "Result"). The 7 empty documents
   (from `empty_documents.csv` of the local dedup run, `jobs/logs/2026-11-16-dedup-local.txt`), all train:

   | Pack | Part | Row in part | `doc_id` |
   |---|---|---:|---|
   | `code-cpp` | `code-cpp/part-00001.parquet` | 1499 | `79fa36f8339f9ebd` |
   | `code-java` | `code-java/part-00000.parquet` | 42665 | `d5d0b4192775579c` |
   | `code-java` | `code-java/part-00000.parquet` | 45786 | `4a67489226159c57` |
   | `code-java` | `code-java/part-00001.parquet` | 5993 | `8a07c8e5f95eee27` |
   | `code-java` | `code-java/part-00001.parquet` | 21846 | `91f4b8de1c11bf4b` |
   | `code-js-ts` | `code-js-ts/part-00000.parquet` | 12129 | `a2ffa5d828d9e9ab` |
   | `code-js-ts` | `code-js-ts/part-00000.parquet` | 56860 | `fff1410ec5527f29` |

   The same 7 `doc_id`s as on 5 Nov.
2. **Which cleaning rule emptied the 7 documents** is not yet recorded. They pass `clean.py`'s empty-output check
   (`out.strip()`) but have no words after normalisation. Dropping them is a cleaning change for spec v1.1.

## Files

| File | What it is | In git |
|---|---|---|
| `teams/01-data-a/dedup/confirm_matrix.py` | The confirmation script | yes |
| `teams/01-data-a/dedup/tests/test_confirm_matrix.py` | Its tests: 12 cases on made-up runs (see "Tests") | yes |
| `teams/01-data-a/dedup/matrix_confirmation.md` | This report | yes |
| `teams/01-data-a/dedup/overlap_matrix.csv` | The reviewed matrix, byte-identical to TSAI's (SHA-256 `b89c4909…54bacb`) | yes |
| `out/overlap_rerun/` | TSAI's returned files from #469 | no (`out/` is ignored) |
| `out/matrix_confirmation_rerun/confirmation.json` | Every check and number above | no |
| `out/matrix_confirmation_rerun/rebuilt/` | The rebuilt matrix files | no |
| `out/matrix_confirmation_rerun/without_empty_documents/` | The matrix without the empty-document group | no |
