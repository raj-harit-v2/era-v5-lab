# Spec v1.1 harm tests: summary (Data A)

**Committed:** `14d45499a5213b7a981debe1c41abdd7ff825774`, 13 Nov 2026, 00:36:54 IST (+0530), by Aneesha Das. The harm reports and the results in this file belong to that commit. This line was filled in by a follow-up commit.
**Update, 13 Nov 2026:** these came after #365 was merged. **Not committed yet.** The commit line goes here once it is made.
- science sections 7–12 of `medicine_sci.md` and a new `sci-finepdfs_harm.json`, after Utkarsh's reading (mittalutkarsh/era-v5-lab#5) was added;
- the new `medicine_english.md`, with 4 English harm reports, after the English readings (mittalutkarsh/era-v5-lab#7, #8 and #9, and patilvijay23/era-v5-lab#36).

**Written:** 13 Nov 2026.
**Branch:** `g1-spec-v1-1` on patilvijay23/era-v5-lab, for theschoolofai/era-v5-lab#365; the new work goes to a new PR that follows #365.

The rules are the Spec v1.1 medicines for the new diseases in `../../sheets/NEW_DISEASES.md`. These are diseases not in `diagnosis/DISEASES.md` that appear in 1% or more of the docs read in a domain: 8 math, 12 science and 2 English. A third English rule, `DA-D6-002`, was withdrawn. The Indic family's C6 (`DB-C6-001`) is Data B's, and is not tested here.

## How they were tested

- **Tool:** `teams/01-data-a/harmtest/harm_test.py --rule all`, unchanged. It was `tools/harm_test.py` until theschoolofai/era-v5-lab#244 moved it on 13 Nov; the code is byte-identical. It runs each rule alone, then all of a sheet's rules in sheet order (ALL IN ORDER), with a drop ending the doc and a fix passing its text on.
- **Sheets:** `sheets/medicine_english.md`, `sheets/medicine_math.md` and `sheets/medicine_sci.md`. Only the v1.1 rules were run, not v1 + v1.1.
- **Data:** the Week 1 pack files, with `teams/01-data-a/gold/<pack>_gold.csv` (docs that two readers agreed are clean).
- **Limit:** gold docs changed plus dropped must be at most `max(1, floor(1% of gold))`, per pack, never pooled. A gold doc counts as touched when any character changes or it is dropped. The limit is:
  - 1 doc on finemath (86), megamath (26), en-dclm (62), en-fineweb-edu (158) and en-nemotroncc (129);
  - 2 on sci-finepdfs (202);
  - 3 on en-nemotroncc-synth (326).
- **Reading docs treated:** the readers' docs with the rule's code that it changes or drops, on the cleaned sample (`scripts/reading_recall.py`).

## Results

### math-finemath: 86 gold docs, limit 1

| rule | disease | changed | dropped | result | gold docs touched | reading docs treated |
|---|---|---|---|---|---|---|
| `DA-A8-001` | words run together | 1 | 0 | PASS | `2d328b828fa97706` | 5 / 13 |
| `DA-C9-003` | template pages | 0 | 1 | PASS | `0f119a596e8b7f63` | 8 / 9 |
| `DA-C9-001` | SEO filler | 0 | 0 | PASS | none | 8 / 15 |
| `DA-D6-001` | machine-written text | 0 | 0 | PASS | none | 3 / 8 |
| `DA-C7-001` | lost formulas | 0 | 0 | PASS | none | 4 / 29 |
| `DA-C7-002` | lost figures | - | - | off (megamath only) | - | 4 / 5 |
| `DA-C8-001` | flattened formulas | 0 | 0 | PASS | none | 3 / 22 |
| `DA-C8-002` | merged table cells | 0 | 0 | PASS | none | 3 / 11 |
| **ALL IN ORDER** | | 1 | 1 | **FAIL (2/86)** | both above | |

The reading counts are for math as a whole, across both packs.

### math-megamath: 26 gold docs, limit 1

All 8 rules touch 0 gold docs, alone and in order: **PASS**. `DA-D6-001` is off on this pack.

### sci-finepdfs: 202 gold docs, limit 2

Run of 13 Nov, with 12 rules: the 6 from 12 Nov, and 6 from Utkarsh's reading. The reading counts are out of 200 science docs read.

| rule | disease | changed | dropped | result | gold docs touched | reading docs treated |
|---|---|---|---|---|---|---|
| `DA-A7-001` | hyphen-split words | 1 | 0 | PASS | `920855df51f37db8` | 3 / 3 |
| `DA-C9-002` | SEO filler (ebook spinner) | 0 | 0 | PASS | none | 2 / 2 |
| `DA-B6-001` | blank forms | 0 | 0 | PASS | none | 2 / 7 |
| `DA-C7-003` | lost list | 0 | 0 | PASS | none | 1 / 3 |
| `DA-C8-004` | steps out of order | 0 | 0 | PASS | none | 1 / 2 |
| `DA-C8-003` | two numbers in one table cell | 0 | 0 | PASS | none | 1 / 3 |
| `DA-A7-002` | drop cap split off | 0 | 0 | PASS | none | 1 / 2 |
| `DA-A7-003` | small caps split | 0 | 0 | PASS | none | 2 / 2 |
| `DA-A8-002` | field labels run together | 0 | 0 | PASS | none | 1 / 3 |
| `DA-C7-005` | near-empty doc | 0 | 1 | PASS | `b6fd81dbf90b0d17` (a false positive) | 2 / 2 |
| `DA-C7-004` | empty image links | 3 | 0 | **FAIL** | `4b958ac1f45443b5`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd` (gold contradictions) | 2 / 2 |
| `DA-C8-005` | page numbers and footers | 0 | 0 | PASS | none | 8 / 9 |
| **ALL IN ORDER** | | 4 | 1 | **FAIL (5/202)** | `920855df51f37db8` and the 4 above | |

With the first 6 rules only (12 Nov), the run in order was 1/202 PASS.
- **First run with all 12 rules:** 9/202. `DA-A7-003` and `DA-C7-004` failed alone.
- **The 8 gold docs** were then read the same day:
  - `DA-A7-003` and `DA-C8-005` caused real harm, so both were narrowed, and now touch 0.
  - `DA-C7-004`'s 3 docs are gold contradictions: each has empty image links. It now keeps captions as text.
  - `DA-C7-005`'s doc is a complete short certificate: a false positive, within the limit.
- **Leaving out the gold contradictions:** the run in order passes at 1/198.

### English: 4 packs

Run of 13 Nov. The reading counts are out of 200 English docs read.

| rule | disease | pack | changed | dropped | result | gold docs touched | reading docs treated |
|---|---|---|---|---|---|---|---|
| `DA-A8-003` | no space after a full stop | en-nemotroncc (129, limit 1) | 1 | 0 | PASS | `056cc9bc44c927e2` (a gold contradiction) | 1 / 2 |
| `DA-D7-001` | facts the rewrite got wrong (6 IDs quarantined) | en-nemotroncc-synth (326, limit 3) | 0 | 0 | PASS (trivial) | none | 4 / 4, and the 2 wrong answers |
| `DA-D6-002` | appended Q&A, **withdrawn** | en-nemotroncc-synth | 32 | 0 | **FAIL** | 32 docs with ordinary, correct Q&A | 3 / 3 |
| **ALL IN ORDER** | | en-nemotroncc | 1 | 0 | **PASS (1/129)** | `056cc9bc44c927e2` | |
| **ALL IN ORDER** | | en-nemotroncc-synth | 0 | 0 | **PASS (0/326)** | none | |

en-dclm (62) and en-fineweb-edu (158): both rules are off there, 0 touched, PASS.

## Gold contradictions

Every gold doc touched has the very disease that the rule targets. The gold set was built in Week 1, before these diseases were named.

| gold doc | pack | rule | what's in it |
|---|---|---|---|
| `2d328b828fa97706` | finemath | `DA-A8-001`, words run together (fix) | `fieldtrip.Write an equation`: a missing space after a full stop. The rule makes it `fieldtrip. Write`. |
| `0f119a596e8b7f63` | finemath | `DA-C9-003`, template pages (drop) | A grams-to-kilograms converter page, with the same template headings as reading doc `d0693c18056bae02` ("Alternative conversion", "Approximate result", "Conversion table", "… chart"). |
| `920855df51f37db8` | sci-finepdfs | `DA-A7-001`, hyphen-split words (fix) | A word split at a line-end hyphen in a Finnish abstract. This is within the limit. |
| `056cc9bc44c927e2` | en-nemotroncc | `DA-A8-003`, words run together (fix) | `tantrum.To the sociopath`: a missing space after a full stop. Within the limit. Read 13 Nov. |
| `4b958ac1f45443b5`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd` | sci-finepdfs | `DA-C7-004`, empty image links (fix) | Markdown image links to an image that isn't there (`![Biotin](image)`, `![Diagram](image)`, a figure legend). Read 13 Nov. |
| `85644a4840025b6f`, `01418489e7410bdf` | ind-te-sangraha-v | `DB-C6-001`, runs of dots (fix) | A bare `..` in mid-sentence, which the rule turns into `...`. oddjoker91, one of the two gold readers, labelled a bare `..` as C6 in other docs of the pack. Read 13 Nov. |

**Handling** (proposed by aneeshads on 13 Nov; **Vijay agreed**): they are marked as gold contradictions, as spec v1 did for `eee25e81417bc1b7` in sci.
- They stay out of the count for these rules only.
- They are flagged for a reader to check again at the next gold refresh.
- The gold CSVs, `harm_test.py` and `harm_test_indic.py` are not changed.

With the two finemath docs left out, finemath in order touches 0 of the other 84 gold docs and passes. With the two Indic docs left out, `DB-C6-001` passes at 0/78 on ind-te-sangraha-v.

If they count instead, spec v1's hold rule holds `DA-A8-001`, which treats fewer reading docs. That leaves "words run together" without a working medicine.

## Rules narrowed after a false positive

Each fix is recorded in that rule's side effects in the sheet.

- **`DA-C7-001`:** it counted option labels and `=` with the answer on the next line as gaps. It also counted line-ending words before options, bullets, equations and wrapped lines. These no longer count, and the cut is now 4 gaps.
- **`DA-C8-001`:** answer-option labels such as `(a)` now break a run.
- **`DA-C8-002`:** it needed 2 long numeric rows and so caught none of the 11 reading docs. One row now suffices; no gold doc has such a row.
- **`DA-B6-001`:** at 10% it dropped 4 gold docs. The threshold is now 30%. The reading docs are at 31% and 63%; the highest gold doc is at 26%.
- **Taken out as not new:** `DA-B1-101`, `DA-A5-101` and `DA-C1-101`. B1, A5 and C1 are in `DISEASES.md`.

## Reports

One `<pack>_harm.json` per pack is in this folder: the 2 math packs, sci-finepdfs and the 4 English packs. They hold doc_ids and counts only. The en-dclm, en-fineweb-edu and en-nemotroncc reports are from the run that still had `DA-D6-002` in the sheet. It was off on those packs, so their results are the same.

## Open

1. **Gold contradictions:** Vijay agreed to marking them. They still need a reader's check at the next gold refresh.
2. **Team agreement on the new codes** (A7–A9, B6, C7–C9, D6, D7), and their entries in `DISEASES.md` and `CODE_ORDER`.
3. **`DA-C7-005`'s false positive** (`b6fd81dbf90b0d17`, within the limit): keep the rule, or find a sign other than length.
4. **Collector run of 13 Nov, 13:13 UTC:**
   - **Science:** complete, 200 docs (Utkarsh in).
   - **Code:** complete, 200 docs, with no new disease.
   - **English:** 200 docs, 50 each from mittalutkarsh/era-v5-lab#7, #8 and #9 and patilvijay23/era-v5-lab#36.
   - **Math:** 299 docs, with Satyanarayana's reading now read from theschoolofai `main`.
5. **Appended Q&A in en-nemotroncc-synth:** is it a disease, or the pack's own format? `DA-D6-002` was withdrawn after it changed 32 of 326 gold docs.
6. **The human check** of the reading examples.
7. **Collation:** done on 14 Nov (Gate 2). `specv1_1.md` is now the combined spec, from `specv1.md` as on TSAI main (with Smita's pack check, on main since #244) and `specv1_1_additions.md`. Her spec v1 math speed fixes (patilvijay23/era-v5-lab#43) were taken back out of this PR on Vijay's ruling (14 Nov), and go into the `clean.py` PR. `medicine_conflicts.py` has not been run on it.
8. **The counting run:** settled by Gate 2. It is v1 + v1.1 together; see `../combined/validation.md`.
