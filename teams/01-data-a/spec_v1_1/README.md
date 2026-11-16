# Spec v1.1 (Data A)

## The final spec v1.1

**[`teams/01-data-a/spec_v1_1/sheets/specv1_1.md`](sheets/specv1_1.md)**

At Gate 2 (14 Nov 2026), TSAI made spec v1 and spec v1.1 one spec v1.1, and theschoolofai/era-v5-lab#435 is that spec. This one file holds it:
- **364 medicines**, each a card with its disease, examples, python code, action, harm result and side effects: spec v1's 340, then the 24 new ones, in the order `clean.py` runs them.
- **Run order:** each family's spec v1 rules first, then its spec v1.1 rules. In English, the v1.1 rules come before the instructor's F1 rule `DA-F1-005`, so F1 stays last.
- **Its harm check** on every pack with a gold set is copied in at the end, from [`results/combined/validation.md`](results/combined/validation.md).
- It is written by [`scripts/combine_spec.py`](scripts/combine_spec.py) from spec v1 and the 24 new cards. Don't edit it by hand.

The new medicines treat the **new** diseases that the Week 2 reading audits found in **1% or more of the docs read in a domain** (English, code, math, science), plus Data B's one Indic rule. Each has unit tests and a harm test on the gold docs. The `clean.py` rebuild from this spec is the next PR (task 2).

Paths are from the repository root.

## What is in this PR (30 files), in the order to read them

**1. The combined spec v1.1**

| file | what it is |
|---|---|
| [`teams/01-data-a/spec_v1_1/sheets/specv1_1.md`](sheets/specv1_1.md) | **The final spec v1.1**: all 364 medicines in run order (see above) |
| [`teams/01-data-a/spec_v1_1/scripts/combine_spec.py`](scripts/combine_spec.py) | Writes `specv1_1.md` from `spec_v1/sheets/specv1.md` and `specv1_1_additions.md` |

**2. The medicine sheets of the 24 new medicines**

| file | what it is |
|---|---|
| [`teams/01-data-a/spec_v1_1/sheets/specv1_1_additions.md`](sheets/specv1_1_additions.md) | The 24 new medicines alone, as cards. They are copied unchanged from the four sheets below |
| [`teams/01-data-a/spec_v1_1/sheets/medicine_english.md`](sheets/medicine_english.md) | English: `DA-A8-003`, `DA-D7-001` and `DA-A8-004` (HariniJasti's) |
| [`teams/01-data-a/spec_v1_1/sheets/medicine_math.md`](sheets/medicine_math.md) | Math: 8 medicines |
| [`teams/01-data-a/spec_v1_1/sheets/medicine_sci.md`](sheets/medicine_sci.md) | Science: 12 medicines |
| [`teams/01-data-a/spec_v1_1/sheets/medicine_indic.md`](sheets/medicine_indic.md) | Indic: Data B's `DB-C6-001` |
| [`teams/01-data-a/spec_v1_1/sheets/decisions_english.md`](sheets/decisions_english.md), [`decisions_math.md`](sheets/decisions_math.md), [`decisions_sci.md`](sheets/decisions_sci.md) | The choices behind each family's medicines |
| [`teams/01-data-a/spec_v1_1/sheets/NEW_DISEASES.md`](sheets/NEW_DISEASES.md) | Why these medicines: each new disease, how many docs it is in, whether it reaches the 1% bar, and the medicine that treats it. It also lists the 10 gold contradictions |

**3. The harm checks of the new medicines**

| file | what it is |
|---|---|
| [`teams/01-data-a/spec_v1_1/results/combined/validation.md`](results/combined/validation.md) | **The combined spec's harm check:** `specv1_1.md` on all 32 packs with a gold set (15 Nov), and its speed |
| [`teams/01-data-a/spec_v1_1/results/sheets/harm_tests.md`](results/sheets/harm_tests.md) | **The record for each new disease:** its medicine, its harm test alone and in order, the gold docs read, the speed passes and the unit tests |
| [`teams/01-data-a/spec_v1_1/results/sheets/summary.md`](results/sheets/summary.md) | The harm results per pack, and what is still open |
| `teams/01-data-a/spec_v1_1/results/sheets/<pack>_harm.json` | One report per pack for its family's sheet, doc_ids and counts only: [en-dclm](results/sheets/en-dclm_harm.json), [en-fineweb-edu](results/sheets/en-fineweb-edu_harm.json), [en-nemotroncc](results/sheets/en-nemotroncc_harm.json), [en-nemotroncc-synth](results/sheets/en-nemotroncc-synth_harm.json), [math-finemath](results/sheets/math-finemath_harm.json), [math-megamath](results/sheets/math-megamath_harm.json), [sci-finepdfs](results/sheets/sci-finepdfs_harm.json) |
| [`teams/01-data-a/spec_v1_1/results/sheets/indic_sangraha-v_harm.md`](results/sheets/indic_sangraha-v_harm.md), [`indic_sangraha-s_harm.md`](results/sheets/indic_sangraha-s_harm.md) | `DB-C6-001`'s harm reports, with Data B's `harm_test_indic.py` |

**4. The tests**

| file | what it is |
|---|---|
| [`teams/01-data-a/spec_v1_1/tests/test_medicine_english.py`](tests/test_medicine_english.py), [`test_medicine_math.py`](tests/test_medicine_math.py), [`test_medicine_sci.py`](tests/test_medicine_sci.py), [`test_medicine_indic.py`](tests/test_medicine_indic.py) | Unit tests of the new medicines, one file per sheet. All text in them is made up |
| [`teams/01-data-a/spec_v1_1/tests/test_code_lang_label.py`](tests/test_code_lang_label.py) | TSAI's Gate 2 request: a code rule (`DA-A1-001`) fires on a doc labelled `lang_label = "code"` |
| [`teams/01-data-a/spec_v1_1/tests/test_combine_spec.py`](tests/test_combine_spec.py) | `combine_spec.py`'s tests, and that `specv1_1.md` is up to date |

**5. This guide:** [`teams/01-data-a/spec_v1_1/README.md`](README.md).

The other files in `teams/01-data-a/spec_v1_1/` are as merged in #365.

## Files outside this folder that spec v1.1 uses (not changed here)

| path | what it is |
|---|---|
| [`teams/01-data-a/harmtest/harm_test.py`](../harmtest/harm_test.py) | The team's harm test: it runs rules on a pack's gold docs and counts the docs they change or drop |
| [`teams/02-data-b/tools/harm_test_indic.py`](../../02-data-b/tools/harm_test_indic.py) | Data B's harm test for Indic, with the joiner (ZWJ/ZWNJ) and normal-form checks |
| [`teams/01-data-a/gold/`](../gold/), [`teams/02-data-b/gold/`](../../02-data-b/gold/) | The gold sets: Data A's for code, English, math and science; Data B's for Indic and cadj |
| [`teams/01-data-a/spec_v1/sheets/specv1.md`](../spec_v1/sheets/specv1.md) | Spec v1, the first part of `specv1_1.md` |
| [`teams/01-data-a/reading/`](../reading/) | The readers' audits and `reading_check_v1.md`, which the 1% counts come from |

## How to rerun

From `teams/01-data-a`, write the combined sheet:

```
python3 -I spec_v1_1/scripts/combine_spec.py \
  --v1 spec_v1/sheets/specv1.md \
  --additions spec_v1_1/sheets/specv1_1_additions.md \
  --validation spec_v1_1/results/combined/validation.md \
  --out spec_v1_1/sheets/specv1_1.md
```

From the repository root, the harm test of the combined sheet, one run per pack, never pooled. `--rule all` tests each rule alone, then all of them in sheet order:

```
python3 -I teams/01-data-a/harmtest/harm_test.py \
  --pack <packs folder>/<pack>.parquet \
  --gold teams/01-data-a/gold/<pack>_gold.csv \
  --rules teams/01-data-a/spec_v1_1/sheets/specv1_1.md \
  --rule all \
  --report <out>/<pack>_harm.json
```

For an Indic or cadj pack, use `teams/02-data-b/gold/<pack>_gold.csv`. For one family's sheet, use `--rules teams/01-data-a/spec_v1_1/sheets/medicine_<family>.md`.

- **Limit:** gold docs changed plus dropped must be at most `max(1, floor(1% of gold))`.
- **No gold set, so NOT TESTABLE:** cadj-notebooks, cadj-stackexchange, ind-ml-fw2, ind-or-fw2, ind-ta-fw2 and ind-ta-sangraha-s.
- **Gold contradictions:** gold docs that hold the very disease a rule targets. Vijay agreed that they are left out of the count for that rule, and re-read at the next gold refresh. The 10 are listed in `NEW_DISEASES.md`.
- **The packs** are TSAI's 500-doc sample packs. They stay outside the repo, and each report records the pack's sha256.

**Unit tests**, from `teams/01-data-a`: `python3 -m unittest discover -s spec_v1_1/tests`.

## Not in this PR

As TSAI asked (15 Nov), #435 holds only the combined spec v1.1, the medicine sheets, and the essential tests and harm checks for the new medicines.
- **In a separate PR:** the member reading CSVs and reports of Week 2, the collector changes since #365, and the other generated evidence (the per-pack harm reports of the combined sheet).
- **In the `clean.py` PR (task 2):**
  - the rebuilt `clean.py` and its timing tool;
  - Smita's spec v1 math speed fixes (patilvijay23/era-v5-lab#43);
  - six whole-line labels for spec v1's `DA-C1-006`, from HariniJasti's labels.

## Open decisions

- **The new codes** (A7, A8, B6, C6, C7, C8, C9, D6, D7) need the team's agreement, and entries in `diagnosis/DISEASES.md` and in `CODE_ORDER` in `teams/01-data-a/spec_v1/build/build_clean.py`.
- **The gold contradictions** are to be re-read at the next gold refresh.
