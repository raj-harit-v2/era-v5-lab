# Spec v1: English family

> **Status:** DRAFT, not frozen. All 20 rules are `CANDIDATE`; 11 more are `BLOCKED`.
> **Tested on:** `g1-harm-test` at `bae5163`, gold sets at that commit. `harm_test.py` there is the same file as PR 140's head.
> **Sections follow `spec_v1_TEMPLATE.md`**, as [spec_v1_code.md](spec_v1_code.md). §3 and §4 are in [medicine_english.md](medicine_english.md); reasons are in [decisions_english.md](decisions_english.md); harm results in [harm_tests_english.md](../results/cleaner/harm_tests_english.md).

## 1. Scope and inputs

| pack | language tags | gold docs | limit | gold sha256 | pack sha256 |
|---|---|---:|---:|---|---|
| `en-dclm` | en | 62 | 1 | `8165439648189b96` | `d5ae1e7e991de478` |
| `en-fineweb-edu` | en | 158 | 1 | `a06212a5f4952b9b` | `3a0ad16983c03e9d` |
| `en-nemotroncc` | eng | 34 | 1 | `0175e5d0afa8d661` | `6eae1507bc689c79` |
| `en-nemotroncc-synth` | eng | 96 | 1 | `72216094cbebbf7b` | `0f1c3a9866ada7fb` |

**Inputs:** the latest `medicine.md` of the 8 English sheets (`fetch_medicines.py --include-open-prs`), the latest labels of the 10 English label sheets in the open diagnosis PRs, and the 11 rules of the 29 Oct sheet. No English pack reaches the gold target of about 200 documents. Digests of every input: [results/sheets/inputs_manifest_english.json](../results/sheets/inputs_manifest_english.json).

**Assumption:** the language tag on a row is correct. No detector runs.

## 3 and 4. Registry and rule cards

The table at the top of [medicine_english.md](medicine_english.md) is the registry. Each section below it is the rule card: disease, medicine in words and code, action, harm test per pack, side effects, source.

Fields of the template's rule card that are still open for every rule: independent reviewer, and rule commit (set when the sheet is merged).

## 5. Execution plan and conflicts

| stage | rules, in order | status |
|---|---|---|
| 00 guard | `LANGS = {"en", "eng"}` in each rule | tested: a row outside `LANGS` passes unchanged, and the code family's rules keep every English row |
| 10 characters | `DA-A1-004`, `DA-A2-008`, `DA-A5-001`, `DA-A3-002` | in the combined test |
| 20 markup | `DA-B1-002`, `DA-B2-002` | in the combined test |
| 30 drops | `DA-C3-001`, `DA-C3-002`, `DA-C5-002`, `DA-D4-001` | in the combined test |
| 35 strips | `DA-C1-006`, `DA-C2-003`, `DA-C5-005`, `DA-D3-003` | in the combined test |
| 40 data safety | `DA-B4-007`, `DA-B4-008`, `DA-B4-009`, `DA-B4-010`, `DA-B4-011`, `DA-F1-005` | in the combined test. In `clean.py`, `DA-F1-005` is the last English rule `clean()` runs |
| 90 post-clean | a test, not a rule | dclm 0, fineweb-edu 0, nemotroncc 0, synth 0 documents left empty |

**Conflict ledger** (each check on every document of the four packs: `results/cleaner/order_checks_english.json`, made by `scripts/order_checks_english.py`)

| rule A | rule B | case | decision | check |
|---|---|---|---|---|
| C3, C5, D4 drops (stage 30) | C1, C2, C5, D3 strips (stage 35) | A strip can remove the very end or the spam a drop rule reads | Drops first | Strips first changes the result on dclm 0, fineweb-edu 0, nemotroncc 0, synth 0 docs; drop decisions on dclm 0, fineweb-edu 0, nemotroncc 0, synth 0 |
| `DA-A5-001` | `DA-A3-002` | NFC composes the characters A3's signature looks for | A5 first (decided 31 Oct) | A3 first, the order before, changes dclm 1, fineweb-edu 0, nemotroncc 0, synth 0 docs, and a second `clean()` then changed that doc again |
| `DA-B1-002` | `DA-B2-002` | An entity can hide a tag (`&lt;p&gt;`) | B1 first | B2 first changes dclm 0, fineweb-edu 0, nemotroncc 0, synth 0 docs |
| `DA-C3-001` | `DA-C3-002` | Both drop truncated docs | 001 first; 002 adds the `[...]` marker and more dangling words | 002 acts on dclm 2, fineweb-edu 1, nemotroncc 12, synth 1 docs after 001 (dclm 1, fineweb-edu 0, nemotroncc 5, synth 0 for 001); swapping them changes dclm 0, fineweb-edu 0, nemotroncc 0, synth 0 |
| `DA-C5-002` | `DA-C5-005` | A spam drop and a tag-line strip | 002 in the drops, 005 in the strips | 005 acts on dclm 4, fineweb-edu 2, nemotroncc 4, synth 1 docs after 002; strip first changes dclm 0, fineweb-edu 0, nemotroncc 0, synth 0 |
| `DA-C1-006` | `DA-D3-003` | Both remove whole lines | C1 first | D3 first changes dclm 0, fineweb-edu 0, nemotroncc 1, synth 0 docs |
| `DA-B4-007` to `DA-B4-011` | each other | Five B4 rules on different junk | Sheet order | Each acts after the ones before it: `DA-B4-007` dclm 0, fineweb-edu 0, nemotroncc 0, synth 8; `DA-B4-008` dclm 2, fineweb-edu 0, nemotroncc 0, synth 18; `DA-B4-009` dclm 5, fineweb-edu 0, nemotroncc 0, synth 0; `DA-B4-010` dclm 0, fineweb-edu 1, nemotroncc 0, synth 0; `DA-B4-011` dclm 0, fineweb-edu 0, nemotroncc 0, synth 1 |
| B4 | `DA-F1-005` | B4 must not rewrite the F1 tags | F1 last | F1 before B4 changes dclm 0, fineweb-edu 0, nemotroncc 0, synth 0 docs; a second `clean()` leaves every F1 tag |
| `DA-F1-005` | shared `spec_v1/tools/f1_rule.py` | Two F1 rules | `DA-F1-005` on English; the shared rule does not run on `en`, `eng` | `clean.py` runs `DA-F1-005` on the English packs and the shared rule on the code, math and science packs (`SCOPE`, TSAI 1 Nov; `tests/test_clean.py`). **Open:** question 6 of the decisions |
| `DA-D3-003` | ZWJ, ZWNJ | A Hindi line in an English doc goes, with its joiners | Kept: D3 removes the line, never the joiner | Unit test; 0 English docs have a joiner |

**Combined harm test** (`harm_test.py --rule all`; files in [results/cleaner/](../results/cleaner/) and [results/sheets/](../results/sheets/), made by [scripts/make_harm_tests_english.py](../scripts/make_harm_tests_english.py)):

| pack | gold harm | limit | result | with disputed docs left in | fixed / dropped / untouched | labelled rows treated |
|---|---|---:|---|---|---|---|
| dclm | 0 / 62 | 1 | PASS | 1 / 170 PASS | 54 / 9 / 437 | 63 / 438 |
| fineweb-edu | 0 / 158 | 1 | PASS | 1 / 295 PASS | 12 / 1 / 487 | 13 / 342 |
| nemotroncc | 0 / 34 | 1 | PASS | 0 / 34 PASS | 62 / 17 / 421 | 75 / 296 |
| synth | 0 / 96 | 1 | PASS | 0 / 96 PASS | 32 / 1 / 467 | 33 / 165 |

`clean.py` gives the same action and text as the English rules of `specv1.md` run in order, on every English document (`results/cleaner/verify_clean_english.json`).

With 0 hits the harm rate is only shown to be below about 3/n: dclm 4.8%, fineweb-edu 1.9%, nemotroncc 8.8%, synth 3.1%.

## 6. Dependencies

- **Instructor ruling, F1, 31 Oct:** Replace each phone number, personal email address and street-level address of a private person with a typed placeholder: `<PHONE>`, `<EMAIL>`, `<ADDRESS>`. The rule written to it is `DA-F1-005`; it is never left out.
- **Shared F1:** `spec_v1/tools/f1_rule.py` runs on the code, math and science packs (`SCOPE` in `clean.py`; TSAI, 1 Nov). `clean.py` runs the English sheet's own F1, `DA-F1-005`, on the English packs.
- **TSAI decision, harm rule:** `max(1 document, 1%)` of each gold set; an empty gold set is NOT TESTABLE (exit code 2). In `harm_test.py` at `bae5163` with its tests.
- **G2 Indic:** not part of this family. ZWJ and ZWNJ are kept in all text (`DISEASES.md` A1); `tests/test_clean.py` checks it.
- **F2:** no English rule; waits on the G9 fingerprints.

## 7. Coverage and open items

**Rules:** 20 `CANDIDATE`, 0 `APPROVED`. Reasons for each rule not picked are in [decisions_english.md](decisions_english.md).

| rule | status | why |
|---|---|---|
| `DA-B4-006` (B4, en-dclm) | BLOCKED | held so that the whole sheet fits the limit with disputed docs left in on dclm (4/170 docs touched, limit 1): it touches 4bf0462bc9268575, and treats 2 labelled rows that no other kept B4 rule treats, the fewest of the rules that touch counted docs |
| `DA-C1-003` (C1, en-nemotroncc-synth) | BLOCKED | over the limit with disputed docs left in: dclm 7 of 170, fineweb-edu 3 of 295 |
| `DA-C1-004` (C1, en-dclm) | BLOCKED | over the limit with disputed docs left in: dclm 8 of 170 |
| `DA-C1-007` (C1, 29 Oct sheet) | BLOCKED | over the limit with disputed docs left in: dclm 8 of 170, fineweb-edu 4 of 295 |
| `DA-C2-004` (C2, 29 Oct sheet) | BLOCKED | held so that the whole sheet fits the limit with disputed docs left in on dclm (2/170 docs touched, limit 1): it touches ba717fd13068128a, and treats 14 labelled rows that no other kept C2 rule treats, the fewest of the rules that touch counted docs |
| `DA-C3-003` (C3, en-fineweb-edu) | BLOCKED | not idempotent: a second run changes 2 docs again |
| `DA-C3-005` (C3, 29 Oct sheet) | BLOCKED | not idempotent: a second run changes 1 doc again |
| `DA-C3-006` (C3, en-nemotroncc-synth) | BLOCKED | not idempotent: a second run changes 2 docs again |
| `DA-C4-003` (C4, en-nemotroncc) | BLOCKED | over the limit with disputed docs left in: fineweb-edu 3 of 295 |
| `DA-C5-003` (C5, en-fineweb-edu) | BLOCKED | held so that the whole sheet fits the limit with disputed docs left in on dclm (3/170 docs touched, limit 1): it touches b19371a31d9aed81, and treats 4 labelled rows that no other kept C5 rule treats, the fewest of the rules that touch counted docs |
| `DA-C5-004` (C5, en-nemotroncc) | BLOCKED | over the limit with disputed docs left in: dclm 2 of 170, fineweb-edu 7 of 295 |

Diseases labelled in the packs with no rule in the sheet:

| pack | disease (labelled rows not treated by the sheet) |
|---|---|
| dclm | C4 (28), H3 (7) |
| fineweb-edu | C4 (18) |
| nemotroncc | C4 (81) |
| synth | B5 (12), C4 (10) |

Codes with fewer than 5 labelled rows on a pack are left out of this table.

**Questions for the instructor**

| # | question | changes |
|---|---|---|
| 1 | F1: are ID numbers (social security, card, Aadhaar, PAN) of private persons also to be replaced, and with which placeholder? The 31 Oct ruling names phone, email and street address only. | F1 scope |
| 2 | F1: may the rule written to the ruling be widened to Indian phone and address forms, which it misses now? | F1 recall on English |

**For review**

- `DA-D3-003` deletes whole lines that are mostly not Latin, so an Indic line in an English doc goes, with its joiners.
- `DA-F1-005` reads an IP address and a group of digits as a phone on a private page, and leaves an organisation's page alone (`decisions_english.md`, F1).
- `spec_v1/tools/build_clean.py` now keeps a family's own F1 where the shared rule does not run: the tool's owner should review it.
- 3 rules are held only so that the whole sheet fits with the disputed docs left in: question 1 of the decisions.

## 8. Freeze checklist

- [x] Gold CSVs: IDs only, coverage shortfalls disclosed above.
- [x] Medicines inventoried; every annotator rule that could not run is fixed or its reason written down.
- [x] Each rule has runnable code and labelled rows it treats.
- [x] Per-pack harm results within the limit, alone and combined.
- [x] Changed and dropped gold IDs can be audited: `results/`.
- [x] Combined order tested; `clean.py` equals the English rules of `specv1.md` on every English doc.
- [x] Within the limit with disputed docs left in, on every pack (DA-B4-006, DA-C2-004, DA-C5-003 held for it).
- [x] The instructor's F1 ruling is in the sheet and in `clean.py` (`DA-F1-005`).
- [x] ZWJ and ZWNJ kept: unit tests.
- [x] F2 status disclosed.
- [x] `clean()` idempotent: a second run changes nothing on any English doc (`DA-A5-001` runs before `DA-A3-002`).
- [ ] Rule IDs committed to the registry: the IDs of the four fineweb-edu rules mapped by hand, the hand-built synth C3, the 11 rules of the 29 Oct sheet and `DA-F1-005` are provisional.
- [ ] Independent reviewer for every rule.
- [ ] Questions in [decisions_english.md](decisions_english.md) answered.

## 9. Handoff

Week 2 and later need the frozen sheet, its digests and `results/`. Cleaning at scale (15 Nov) runs `clean.py`, the one cleaner of every family, on the English packs (`run_clean.py --pack <pack>.parquet --out <dir>`; see `README_clean.md`). `clean_english.py` has been removed; `scripts/clean_english.py` is kept but not used: nothing loads it. The sheet itself was compiled from the annotators' sheets by scripts outside this repo (not committed yet); `results/sheets/evidence_english.json` and `results/sheets/equivalence_english.json` are what they found. `run_harm_suite.py` cannot test the sheet yet: it tests registry rules one at a time, never a combined sheet. Spec v1 has not been applied to the tokenizer sample yet.
