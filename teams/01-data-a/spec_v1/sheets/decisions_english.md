# English medicines: final decision

## Verdict

**Ready for team review. Not approved or frozen.** 20 rules are `CANDIDATE` and in [medicine_english.md](medicine_english.md); 11 are `BLOCKED`. Every annotator rule that could not run now runs: the authors' code is unchanged, and what was missing is added from their own sheets (below). The whole sheet touches no official gold document on any English pack. `clean.py`, built by `spec_v1/tools/build_clean.py` from `specv1.md`, runs these rules and gives the same result as the sheet on all 2,000 English documents. It needs an independent reviewer, and the questions below need an answer.

### Result per pack

Each pack is tested with the team's `harm_test.py --rule all` on its own gold set. Limit: changed + dropped at most `max(1, floor(1% of gold))`, that is `max(1 document, 1%)` (TSAI decision); an empty gold set is NOT TESTABLE. "Stress" leaves in the docs that the gold builder excludes as disputed (`build_gold.py --allow-disputed`); it is not the official test.

| pack | gold harm | limit | result | stress | fixed / dropped / untouched | labelled rows treated |
|---|---|---|---|---|---|---|
| dclm | 0 / 62 | 1 | PASS | 1 / 170 PASS | 54 / 9 / 437 | 63 / 438 |
| fineweb-edu | 0 / 158 | 1 | PASS | 1 / 295 PASS | 12 / 1 / 487 | 13 / 342 |
| nemotroncc | 0 / 34 | 1 | PASS | 0 / 34 PASS | 62 / 17 / 421 | 75 / 296 |
| synth | 0 / 96 | 1 | PASS | 0 / 96 PASS | 32 / 1 / 467 | 33 / 165 |

- **Stress hits:** 2 docs, `0b6d3f138a3faac0` (dclm), `ab731016903cbb4f` (fineweb-edu), both changed by `DA-C2-003`. Two readers said clean and a third did not, so the gold builder left them out (table below).
- **0 hits is not 0 harm.** A gold set of n docs with 0 hits only bounds the harm rate below about 3/n: dclm 4.8%, fineweb-edu 1.9%, nemotroncc 8.8%, synth 3.1%. About 300 docs are needed to show 1%.
- **A second clean changes nothing** on any English doc. `DA-A5-001` (NFC) now runs before `DA-A3-002`: NFC composes the characters A3's signature looks for, so with A3 first its repair of `68575a61a90990d5` (dclm, a page of mojibake) only came on a second run.

### Against the criteria

| criterion | source | result |
|---|---|---|
| Disease, medicine in words and code, action, harm test, side effects | `DISEASES.md` §4 | **Met.** Every section of the sheet has all 5. Examples give `doc_id` only. |
| Within the limit, alone and combined, per pack | `README.md` criterion 1; TSAI decision `max(1 document, 1%)` | **Met.** Every rule alone and the whole sheet: 0 official gold docs on every pack. |
| Treats real rows | criterion 2 | **Met.** Every kept rule treats labelled rows that no rule kept before it treats. |
| Does not damage what it keeps | criterion 3 | **Partly.** Stage 90: 0 docs left empty. ZWJ and ZWNJ are never deleted on their own (unit tests). `DA-D3-003` deletes a whole line whose letters are mostly not Latin, so a Hindi line in an English doc goes, joiners with it. |
| Idempotent | criterion 4 | **Met.** Every rule alone, and the whole of `clean()`: a second run changes nothing on any English doc. 3 C3 rules are `BLOCKED` because a second run cuts again; `DA-A5-001` runs before `DA-A3-002` for it (item 6 below). |
| Not resting on a dispute | criterion 5 | **Met.** Within the limit with disputed docs left in on every pack, with 3 rules held for it. |
| Reviewed by someone other than its author | criterion 6 | **Pending** for every rule. |
| The instructor's F1 ruling, 31 Oct | ruling | **Met.** `DA-F1-005` is in the sheet and runs on the English packs in `clean.py`; the F1 rules that do not follow the ruling are out. |
| Keep ZWJ and ZWNJ in all text | `DISEASES.md` A1 | **Met** for the characters (`tests/test_clean.py`); a joiner goes only with a whole line D3 removes. |
| No secrets or personal data | `DISEASES.md` §2a, pr-guard | **Met.** IDs, offsets and made-up values only; the files are scanned with pr-guard's own patterns. |
| Digests, owner, reviewer, commit | Spec v1 §1 and §2.9 | **Partly.** Gold and pack digests are in the sheet and in `results/sheets/inputs_manifest_english.json`. Reviewer and the sheet's commit come at review. |

### What changed in this round

1. **Packaged as Spec v1.** The sheet is `medicine_english.md`, in the form of `medicine_code.md`: the gold and pack digests and the harm test of the whole sheet are added. Each code block is that of the earlier English sheet, unchanged; only the order in stage 10 changed (item 6).
2. **`clean.py` is the one cleaner.** `spec_v1/tools/build_clean.py` builds it from `specv1.md`, which collates the four family sheets, with a `SCOPE` table of the packs each rule applies to; `run_clean.py` runs it on a pack. `clean_english.py`, the English cleaner made before `specv1.md`, has been removed; `scripts/clean_english.py` is kept but not used: no script or test loads it.
3. **F1 on English is `DA-F1-005`.** `spec_v1/tools/build_clean.py` used to leave every sheet's F1 out for the shared `spec_v1/tools/f1_rule.py`, which does not run on `en` or `eng`. In `clean.py` each family runs its own sheet's F1 on its own packs: `DA-F1-005` on the English packs, and the shared rule on the code, math and science packs (`SCOPE`; TSAI, 1 Nov).
4. **Personal names are out of the text.** `AUTHOR` stays as a code field because the team's `medicine_conflicts.py` reads it.
5. **F1 checked as `spec_v1/tools/f1_eval.py` checks it**, by `scripts/f1_eval_english.py`: see F1 below.
6. **`DA-A5-001` runs before `DA-A3-002`** (decided 31 Oct). NFC composes the characters A3's signature looks for, so with A3 first, A3 repaired `68575a61a90990d5` (dclm) only on a second run. With A5 first it repairs it in one pass. No other English doc changes, and no harm number moves: that doc is in neither gold set. `spec_v1/tools/build_clean.py` lists the English codes in its `CODE_ORDER` in the sheet's order, so `harm_test.py`'s `ALL IN ORDER` on `clean.py` runs A5 before A3, as `clean()` does.

### What was fixed

Each block gives the same result as the author's own function, run from their full rules file, on all 2,000 English documents: 37 of 37 blocks differ on 0 documents (`results/sheets/equivalence_english.json`).

| sheet | its rules | what was wrong | what the sheet adds |
|---|---|---|---|
| en-dclm | `DA-A1-003`, `DA-A3-002`, `DA-B4-006`, `DA-C1-002`, `DA-C2-002`, `DA-C3-001`, `DA-C5-001`, `DA-F1-002` | 8 rules return `(text, flag)`, a form `harm_test.py` rejects (TypeError on every document). A3 uses `ftfy`, C2 and C5 use `Counter`, and the rules file imports neither. | `_std` reads `(text, flag)`: a flag is a drop, as the sheet says. `import ftfy` and `from collections import Counter`. |
| en-fineweb-edu | `DA-B4-010`, `DA-C1-005`, `DA-C2-003`, `DA-C3-003`, `DA-C5-003`, `DA-D3-002`, `DA-F1-003` | 7 rules return the character spans to remove, not the text (TypeError on every document). | `_std` removes the spans as the sheet's own `clean()` does: `(spans, True)` from `c1_spans`, a `B4-mostly-code` or `C5-list-page` span is a drop. `d3_flags` only points at passages, so its D3 rule keeps the text. |
| en-nemotroncc-synth | `DA-B4-007`, `DA-B4-008`, `DA-B5-001`, `DA-C1-003`, `DA-C3-006`, `DA-C4-001` | 5 rules use constants their rules file never defines (NameError on every document). C3 has three public functions in its section, so the extractor took none. | The constants from the sheet's own `medicine.md`: `META`, `DETOK` and `BOILERPLATE_LINE` from the plain fences after their names, the C3 ones from its words (as the 29 Oct sheet had them). Its C3 by hand (`trim_truncation_both_ends`, new ID) with the guard of the 29 Oct sheet: only texts with a `Question:` line. `_std` reads `(text or None, changed)`. C4 and B5 are not rebuilt (below). |
| en-nemotroncc | `DA-A1-005`, `DA-C1-006`, `DA-C3-004`, `DA-C4-003`, `DA-C5-004`, `DA-D3-003` | C3, C4 and C5 return `None` to drop, which `harm_test.py` rejects (TypeError on 24, 25 and 16 documents of the pack). | `_std` reads `None` as a drop. |
| en-fineweb-edu | `DA-C1-008`, `DA-C3-007`, `DA-C5-006`, `DA-F1-004` | All four functions sit in one block of the F1 section, so the extractor took none. | Mapped by hand: `c1_line` C1, `c3_trim` C3, `c5_line` C5, `f1_spans` F1, with new IDs. An empty result is a drop. |
| en-nemotroncc-synth | `DA-B4-011` | Five python blocks of the sheet are example edits that do not run on their own, so `harm_test.py --rules medicine.md` stops on the sheet. | Only the rule (`medicine_b4`) is copied; the examples are not. |
| en-dclm | `DA-A1-004`, `DA-B4-009`, `DA-C1-004`, `DA-C3-002`, `DA-C4-002`, `DA-C5-002`, `DA-D4-001` | Nothing: all seven rules run as written. | Nothing. |
| the 29 Oct sheet, all four packs | `DA-A2-008`, `DA-A4-004`, `DA-A5-001`, `DA-B1-002`, `DA-B2-002`, `DA-B3-008`, `DA-C1-007`, `DA-C2-004`, `DA-C2-005`, `DA-C3-005`, `DA-C5-005` | Its 11 rules carried IDs that now belong to other rules in the registry. | The same code under the next free IDs. |

The 11 rules of the 29 Oct sheet, under their new IDs: `DA-A2-007` → `DA-A2-008`, `DA-A4-002` → `DA-A4-004`, `DA-A5-001` → `DA-A5-001`, `DA-B1-002` → `DA-B1-002`, `DA-B2-002` → `DA-B2-002`, `DA-B3-009` → `DA-B3-008`, `DA-C1-006` → `DA-C1-007`, `DA-C2-003` → `DA-C2-004`, `DA-C2-004` → `DA-C2-005`, `DA-C3-005` → `DA-C3-005`, `DA-C5-002` → `DA-C5-005`. `DA-F1-005` is new.

### Disputed docs the whole sheet touches

Not in the official gold: two readers said clean and the third did not, so the gold builder left them out.

| pack | doc_id | rule | readers |
|---|---|---|---|
| dclm | `0b6d3f138a3faac0` | `DA-C2-003` | clean; clean; fix C1;C3 |
| fineweb-edu | `ab731016903cbb4f` | `DA-C2-003` | clean; fix C1; clean |

### Instructor rulings

**F1, 31 Oct:** Replace each phone number, personal email address and street-level address of a private person with a typed placeholder: `<PHONE>`, `<EMAIL>`, `<ADDRESS>`.

- In the sheet: `DA-F1-005`, a new rule written to it, and never left out: `spec_v1/tools/build_clean.py` stops if it is missing or not on every English pack. It treats dclm 2/13, fineweb-edu 0/12, nemotroncc 1/13, synth 1/2 labelled F1 rows: most labelled rows are organisations' contacts, which readers labelled before the ruling and the ruling leaves alone, or hold no phone, email or street address.
- Out because they do not follow it: `DA-F1-002`, `DA-F1-003`, `DA-F1-004`.
- Not in the ruling, so not treated: ID numbers (social security, card, Aadhaar, PAN) and names.

### Rules held for the whole sheet

All the kept rules together went over the limit with disputed docs left in, although each one alone was within it. Rules were held one at a time, the one that treats the fewest labelled rows no other kept rule of its disease treats first, until every pack fitted.

| rule | source | why it is held |
|---|---|---|
| `DA-B4-006` | en-dclm | held so that the whole sheet fits the limit with disputed docs left in on dclm (4/170 docs touched, limit 1): it touches 4bf0462bc9268575, and treats 2 labelled rows that no other kept B4 rule treats, the fewest of the rules that touch counted docs |
| `DA-C2-004` | 29 Oct sheet | held so that the whole sheet fits the limit with disputed docs left in on dclm (2/170 docs touched, limit 1): it touches ba717fd13068128a, and treats 14 labelled rows that no other kept C2 rule treats, the fewest of the rules that touch counted docs |
| `DA-C5-003` | en-fineweb-edu | held so that the whole sheet fits the limit with disputed docs left in on dclm (3/170 docs touched, limit 1): it touches b19371a31d9aed81, and treats 4 labelled rows that no other kept C5 rule treats, the fewest of the rules that touch counted docs |

### F1 on the English packs

`scripts/f1_eval_english.py`, the English counterpart of `spec_v1/tools/f1_eval.py`, with its made-up values (`results/cleaner/f1_eval_english.json`). The shared rule is switched on for `en` and `eng` in memory only, to show what switching it on would do; no file is changed.

| pack | `DA-F1-005`: docs fixed · gold touched · tags | shared F1 on English: docs fixed · gold touched · tags |
|---|---|---|
| dclm | 2 · 0/62 · `<EMAIL>` 4 | 14 · 1/62 (`09319f191c620efe`) · `<EMAIL>` 7, `<PHONE>` 8, `<ADDRESS>` 7 |
| fineweb-edu | 0 · 0/158 · none | 6 · 0/158 · `<PHONE>` 6, `<ADDRESS>` 4 |
| nemotroncc | 1 · 0/34 · `<EMAIL>` 1 | 14 · 0/34 · `<EMAIL>` 8, `<PHONE>` 7, `<ADDRESS>` 1 |
| synth | 2 · 0/96 · `<EMAIL>` 2, `<PHONE>` 1 | 8 · 0/96 · `<EMAIL>` 3, `<PHONE>` 4, `<ADDRESS>` 2 |

Made-up details on a line of their own at the end of up to 40 real gold docs per pack (154 docs): share that get the right tag and nothing else changed.

| made-up value | `DA-F1-005` | shared F1 |
|---|---:|---:|
| email plain | 44% | 100% |
| email country domain | 0% | 100% |
| phone with a word | 44% | 90% |
| phone +44 | 44% | 90% |
| phone (555) | 44% | 90% |
| phone US plain | 44% | 90% |
| phone +91 | 0% | 90% |
| phone India no code | 0% | 90% |
| phone digits only | 0% | 90% |
| address road | 44% | 90% |
| address 221B | 44% | 90% |
| address India | 0% | 90% |
| address lower case | 0% | 0% |

| must stay unchanged | `DA-F1-005` | shared F1 |
|---|---:|---:|
| org role email | 100% | 100% |
| office gov email | 100% | 100% |
| org phone | 100% | 100% |
| org address | 100% | 100% |
| example email | 100% | 100% |
| git address | 100% | 100% |
| date | 100% | 100% |
| version | 100% | 100% |
| ip | 56% | 100% |
| digit groups | 56% | 100% |
| retina file | 100% | 100% |
| npm scope | 100% | 100% |
| package version | 100% | 100% |
| uuid | 100% | 100% |
| byte size street | 56% | 10% |

- `DA-F1-005` leaves a phone or address alone when an organisation's cue words sit within 6 lines of it, or the page speaks for an organisation ("call us", "our office"), as the ruling's "private person" asks. The end of a real page is often its footer, so the planted value stays on 56% of these docs; put 7 neutral lines further down, the same phone gets `<PHONE>` on 97% of them, and in a neutral text on all.
- It **misses** Indian forms: `+91` and 10-digit numbers with no country code, `18 MG Road`, and an email at `post.co.in`. On a private page it **reads an IP address and a group of digits as a phone**, and `8 Bit Drive` as an address. Question 7.
- The shared rule finds far more, but on dclm it touches 1 official gold doc (at the limit) and with the disputed docs left in it takes the whole sheet over the limit: question 6.
- A second `clean()` leaves every F1 tag as it is on all four packs.

### Questions for the team

| # | question | changes |
|---|---|---|
| 1 | DA-B4-006, DA-C2-004, DA-C5-003 are held so that the whole sheet fits the limit with disputed docs left in. Each touches one disputed doc (table above). Accept the holds, or accept the overrun and keep them? | Labelled rows only these rules treat: 20 |
| 2 | Should a rule written for one pack run on every English pack? Here every rule does, so each is tested on all four gold sets. | Scope of every rule |
| 3 | Do label sheets from open PRs count? None of the English sheets is merged. | Every "labelled rows" number |
| 4 | C1: 3 C1 rules are BLOCKED (`DA-C1-003`, `DA-C1-004`, `DA-C1-007`), only by disputed docs; the sheet has `DA-C1-006`. | C1 coverage: 36 labelled rows treated by the sheet now |
| 5 | F1: are ID numbers (social security, card, Aadhaar, PAN) of private persons also to be replaced, and with which placeholder? The 31 Oct ruling names phone, email and street address only. | F1 scope |
| 6 | One F1 for every family: switch the shared `spec_v1/tools/f1_rule.py` on for English in place of `DA-F1-005`? | dclm: 1/62 gold (at the limit), and 2/170 with the disputed docs left in, over the limit |
| 7 | Widen `DA-F1-005` to Indian phone and address forms, and stop it reading IPs and digit groups as phones? It is the rule written to the instructor's ruling, so its behaviour changes only with the team's and the instructor's agreement. | F1 recall on English |

### Problems to report to the team

- **`spec_v1/tools/build_clean.py` was changed.** The tool's owner should review it. It now writes one `clean.py` from `specv1.md`, with the `SCOPE` table at the top.
- **`spec_v1/tools/make_harm_tests.py` rewrites `harm_tests.md` for every family at once**, and lists a family whose packs are not on the machine as NOT RUN. Run where the code packs are missing, it would drop the code results, so the English results are in `harm_tests_english.md`, made by `spec_v1/tools/make_harm_tests_english.py`.
- **`clean_english.py` has been removed, and `scripts/clean_english.py` is not used.** `scripts/clean_english.py` is kept for the record; `clean.py` is the one cleaner, and no script or test loads it.
- **`spec_v1/tools/f1_eval.py` covers the code packs only** (tree-sitter, `code-*`). English has `spec_v1/tools/f1_eval_english.py`.
- **`README.md` names the English sheet `medicine_en.md`.** It is `medicine_english.md` here, so the family in `clean.py` is `english` and its rules are `_english_*`.

### Limits

- A 0 is a bound, not proof: with n gold docs and 0 hits the harm rate is only shown to be below about 3/n: dclm 4.8%, fineweb-edu 1.9%, nemotroncc 8.8%, synth 3.1%. About 300 gold docs are needed to show 1%.
- A labelled row "treated" means the rule changes or drops it, not that the new text is right.
- The en-fineweb-edu C1 scorer gets no pack line counts here (`harm_test.py` passes one document), as in the 29 Oct sheet.
- "Labelled rows" counts the H3 and F2 rows too; no English rule treats them.

## How rules were picked

Every rule runs on every document of the four English packs (`results/sheets/evidence_english.json`). A rule is out (DROP) if it raises on any document, goes over the limit on any official gold set, or changes nothing. It is BLOCKED if it goes over the limit with disputed docs left in, or if a second run changes a document again. Of the rest, for each disease, the rule that treats the most labelled rows is kept, and another only if it treats labelled rows the kept ones do not (the advice of `rule_report.py`). Then the kept rules run together, in sheet order, on each pack's official gold and with disputed docs left in. While a pack is over the limit, one rule is held (BLOCKED): of the rules that alone touch a counted doc, the one that treats the fewest labelled rows no other kept rule of its disease treats. The pick is then made again without it. A rule written to an instructor's ruling (`DA-F1-005`) is never dropped, blocked or held.

**Inputs:** the latest `medicine.md` of the 8 English sheets (`fetch_medicines.py --include-open-prs`), the latest labels of the 10 English label sheets in the open diagnosis PRs, the 11 rules of the 29 Oct sheet, and the official gold sets of `g1-harm-test` at `bae5163`.

## The decision for each disease

Each cell: gold docs touched · labelled rows treated / labelled rows · labelled-clean docs touched outside gold.

### A1 invisible junk characters

**Picked:** `DA-A1-004` (en-dclm) on all 4 packs.

**Why:** `DA-A1-004`: passes and treats the most labelled rows (25). Labelled rows: dclm 12, fineweb-edu 1, nemotroncc 14, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-A1-004` | en-dclm | **PICKED** | 0 · 11/12 · 1 | 0 · 0/1 · 0 | 0 · 14/14 · 0 | 0 · 0/0 · 0 |
| `DA-A1-003` | en-dclm | DROP: its 24 labelled rows are all treated by DA-A1-004 | 0 · 10/12 · 0 | 0 · 0/1 · 0 | 0 · 14/14 · 0 | 0 · 0/0 · 0 |
| `DA-A1-005` | en-nemotroncc | DROP: its 24 labelled rows are all treated by DA-A1-004 | 0 · 10/12 · 0 | 0 · 0/1 · 0 | 0 · 14/14 · 0 | 0 · 0/0 · 0 |

### A2 control characters

**Picked:** `DA-A2-008` (29 Oct sheet) on all 4 packs.

**Why:** `DA-A2-008`: passes and treats the most labelled rows (3). Labelled rows: dclm 3, fineweb-edu 0, nemotroncc 0, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-A2-008` | 29 Oct sheet | **PICKED** | 0 · 3/3 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

### A3 mojibake

**Picked:** `DA-A3-002` (en-dclm) on all 4 packs.

**Why:** `DA-A3-002`: passes and treats the most labelled rows (5). Labelled rows: dclm 7, fineweb-edu 4, nemotroncc 4, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-A3-002` | en-dclm | **PICKED** | 0 · 4/7 · 1 | 0 · 1/4 · 0 | 0 · 0/4 · 0 | 0 · 0/0 · 0 |

### A4 replacement characters

**Picked:** nothing.

**Why:** No rule passes every test: see the table. Labelled rows: dclm 1, fineweb-edu 1, nemotroncc 1, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-A4-004` | 29 Oct sheet | DROP: changes no document of any English pack | 0 · 0/1 · 0 | 0 · 0/1 · 0 | 0 · 0/1 · 0 | 0 · 0/0 · 0 |

### A5 wrong normal form

**Picked:** `DA-A5-001` (29 Oct sheet) on all 4 packs.

**Why:** `DA-A5-001`: passes and treats the most labelled rows (3). Labelled rows: dclm 3, fineweb-edu 0, nemotroncc 0, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-A5-001` | 29 Oct sheet | **PICKED** | 0 · 3/3 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

### A6 wrong or mixed script

**Picked:** nothing.

**Why:** No English medicine was submitted for it. Labelled rows: dclm 3, fineweb-edu 0, nemotroncc 0, synth 0.

### B1 HTML entities

**Picked:** `DA-B1-002` (29 Oct sheet) on all 4 packs.

**Why:** `DA-B1-002`: passes and treats the most labelled rows (1). Labelled rows: dclm 1, fineweb-edu 0, nemotroncc 3, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-B1-002` | 29 Oct sheet | **PICKED** | 0 · 1/1 · 0 | 0 · 0/0 · 0 | 0 · 0/3 · 0 | 0 · 0/0 · 0 |

### B2 HTML or XML tags

**Picked:** `DA-B2-002` (29 Oct sheet) on all 4 packs.

**Why:** `DA-B2-002`: passes and treats the most labelled rows (2). Labelled rows: dclm 3, fineweb-edu 1, nemotroncc 1, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-B2-002` | 29 Oct sheet | **PICKED** | 0 · 1/3 · 0 | 0 · 1/1 · 0 | 0 · 0/1 · 0 | 0 · 0/0 · 0 |

### B3 ghost chat markers

**Picked:** nothing.

**Why:** No rule passes every test: see the table. Labelled rows: dclm 0, fineweb-edu 0, nemotroncc 1, synth 0.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-B3-008` | 29 Oct sheet | DROP: changes no document of any English pack | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/1 · 0 | 0 · 0/0 · 0 |

### B4 template and code junk in prose

**Picked:** `DA-B4-007` (en-nemotroncc-synth) on all 4 packs; `DA-B4-008` (en-nemotroncc-synth) on all 4 packs; `DA-B4-009` (en-dclm) on all 4 packs; `DA-B4-010` (en-fineweb-edu) on all 4 packs; `DA-B4-011` (en-nemotroncc-synth) on all 4 packs.

**Why:** `DA-B4-007`: treats 8 labelled rows that DA-B4-008 does not. `DA-B4-008`: passes and treats the most labelled rows (17). `DA-B4-009`: treats 5 labelled rows that DA-B4-008, DA-B4-007 do not. `DA-B4-010`: treats 1 labelled row that DA-B4-008, DA-B4-007, DA-B4-009 do not. `DA-B4-011`: treats 1 labelled row that DA-B4-008, DA-B4-007, DA-B4-009, DA-B4-010 do not. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-B4-007` | en-nemotroncc-synth | **PICKED** | 0 · 0/25 · 0 | 0 · 0/8 · 0 | 0 · 0/15 · 0 | 0 · 8/36 · 2 |
| `DA-B4-008` | en-nemotroncc-synth | **PICKED** | 0 · 0/25 · 1 | 0 · 0/8 · 0 | 0 · 0/15 · 0 | 0 · 17/36 · 6 |
| `DA-B4-009` | en-dclm | **PICKED** | 0 · 5/25 · 4 | 0 · 0/8 · 0 | 0 · 0/15 · 0 | 0 · 0/36 · 0 |
| `DA-B4-010` | en-fineweb-edu | **PICKED** | 0 · 0/25 · 0 | 0 · 1/8 · 1 | 0 · 0/15 · 0 | 0 · 0/36 · 0 |
| `DA-B4-011` | en-nemotroncc-synth | **PICKED** | 0 · 0/25 · 0 | 0 · 0/8 · 0 | 0 · 0/15 · 0 | 0 · 1/36 · 0 |
| `DA-B4-006` | en-dclm | BLOCKED: held so that the whole sheet fits the limit with disputed docs left in on dclm (4/170 docs touched, limit 1): it touches 4bf0462bc9268575, and treats 2 labelled rows that no other kept B4 rule treats, the fewest of the rules that touch counted docs | 0 · 2/25 · 5 | 0 · 0/8 · 1 | 0 · 0/15 · 0 | 0 · 1/36 · 0 |

### B5 Markdown or LaTeX that is broken

**Picked:** nothing.

**Why:** No rule passes every test: see the table. Labelled rows: dclm 3, fineweb-edu 4, nemotroncc 3, synth 12.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-B5-001` | en-nemotroncc-synth | DROP: not rebuilt: a detector that routes documents to a manual fix; CODE_SPAN, LONG_LOWER and _dictionary are given nowhere | - | - | - | - |

### C1 boilerplate

**Picked:** `DA-C1-006` (en-nemotroncc) on all 4 packs.

**Why:** `DA-C1-006`: passes and treats the most labelled rows (36). Labelled rows: dclm 389, fineweb-edu 308, nemotroncc 161, synth 76.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-C1-006` | en-nemotroncc | **PICKED** | 0 · 6/389 · 6 | 0 · 2/308 · 2 | 0 · 27/161 · 1 | 0 · 1/76 · 0 |
| `DA-C1-002` | en-dclm | DROP: over the limit on dclm (16/62) | 16 · 290/389 · 281 | 0 · 18/308 · 11 | 0 · 27/161 · 1 | 0 · 4/76 · 0 |
| `DA-C1-003` | en-nemotroncc-synth | BLOCKED: over the limit with disputed docs left in: dclm 7 of 170, fineweb-edu 3 of 295 | 0 · 64/389 · 59 | 0 · 20/308 · 11 | 0 · 22/161 · 0 | 0 · 4/76 · 1 |
| `DA-C1-004` | en-dclm | BLOCKED: over the limit with disputed docs left in: dclm 8 of 170 | 0 · 108/389 · 96 | 0 · 0/308 · 0 | 0 · 1/161 · 0 | 0 · 2/76 · 0 |
| `DA-C1-005` | en-fineweb-edu | DROP: over the limit on dclm (11/62), nemotroncc (2/34) | 11 · 218/389 · 212 | 1 · 144/308 · 92 | 2 · 45/161 · 12 | 0 · 13/76 · 8 |
| `DA-C1-007` | 29 Oct sheet | BLOCKED: over the limit with disputed docs left in: dclm 8 of 170, fineweb-edu 4 of 295 | 0 · 147/389 · 133 | 0 · 32/308 · 18 | 0 · 32/161 · 1 | 0 · 6/76 · 0 |
| `DA-C1-008` | en-fineweb-edu | DROP: over the limit on dclm (3/62) | 3 · 49/389 · 50 | 0 · 36/308 · 7 | 0 · 4/161 · 0 | 0 · 1/76 · 0 |

### C2 repeated lines

**Picked:** `DA-C2-003` (en-fineweb-edu) on all 4 packs.

**Why:** `DA-C2-003`: passes and treats the most labelled rows (27). Labelled rows: dclm 38, fineweb-edu 6, nemotroncc 39, synth 1.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-C2-003` | en-fineweb-edu | **PICKED** | 0 · 18/38 · 8 | 0 · 1/6 · 4 | 0 · 7/39 · 3 | 0 · 1/1 · 0 |
| `DA-C2-002` | en-dclm | DROP: its 14 labelled rows are all treated by DA-C2-003 | 0 · 8/38 · 1 | 0 · 0/6 · 3 | 0 · 5/39 · 0 | 0 · 1/1 · 0 |
| `DA-C2-004` | 29 Oct sheet | BLOCKED: held so that the whole sheet fits the limit with disputed docs left in on dclm (2/170 docs touched, limit 1): it touches ba717fd13068128a, and treats 14 labelled rows that no other kept C2 rule treats, the fewest of the rules that touch counted docs | 0 · 7/38 · 9 | 0 · 0/6 · 0 | 0 · 12/39 · 4 | 0 · 0/1 · 0 |
| `DA-C2-005` | 29 Oct sheet | DROP: its 3 labelled rows are all treated by DA-C2-003 | 0 · 2/38 · 1 | 0 · 1/6 · 1 | 0 · 0/39 · 0 | 0 · 0/1 · 0 |

### C3 truncated document

**Picked:** `DA-C3-001` (en-dclm) on all 4 packs; `DA-C3-002` (en-dclm) on all 4 packs.

**Why:** `DA-C3-001`: treats 3 labelled rows that DA-C3-002 does not. `DA-C3-002`: passes and treats the most labelled rows (12). Labelled rows: dclm 103, fineweb-edu 35, nemotroncc 101, synth 50.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-C3-001` | en-dclm | **PICKED** | 0 · 1/103 · 1 | 0 · 0/35 · 0 | 0 · 5/101 · 0 | 0 · 0/50 · 0 |
| `DA-C3-002` | en-dclm | **PICKED** | 0 · 3/103 · 3 | 0 · 1/35 · 0 | 0 · 8/101 · 1 | 0 · 0/50 · 0 |
| `DA-C3-003` | en-fineweb-edu | BLOCKED: not idempotent: a second run changes 2 docs again | 0 · 3/103 · 2 | 0 · 4/35 · 0 | 0 · 14/101 · 2 | 0 · 0/50 · 2 |
| `DA-C3-004` | en-nemotroncc | DROP: over the limit on dclm (2/62) | 2 · 4/103 · 14 | 1 · 2/35 · 4 | 0 · 14/101 · 1 | 0 · 0/50 · 0 |
| `DA-C3-005` | 29 Oct sheet | BLOCKED: not idempotent: a second run changes 1 doc again | 0 · 2/103 · 2 | 0 · 1/35 · 0 | 0 · 2/101 · 0 | 0 · 0/50 · 0 |
| `DA-C3-006` | en-nemotroncc-synth | BLOCKED: not idempotent: a second run changes 2 docs again | 0 · 0/103 · 0 | 0 · 0/35 · 0 | 0 · 0/101 · 0 | 0 · 24/50 · 5 |
| `DA-C3-007` | en-fineweb-edu | DROP: over the limit on dclm (4/62) | 4 · 19/103 · 71 | 0 · 8/35 · 1 | 0 · 8/101 · 1 | 0 · 0/50 · 0 |

### C4 two documents joined

**Picked:** nothing.

**Why:** No rule passes every test: see the table. Labelled rows: dclm 28, fineweb-edu 18, nemotroncc 81, synth 10.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-C4-001` | en-nemotroncc-synth | DROP: not rebuilt: the author proposes no automatic rule, and WORD_RE and STOP are given nowhere | - | - | - | - |
| `DA-C4-002` | en-dclm | DROP: treats none of the labelled rows: a rule that does nothing also passes | 0 · 0/28 · 1 | 0 · 0/18 · 0 | 0 · 0/81 · 0 | 0 · 0/10 · 0 |
| `DA-C4-003` | en-nemotroncc | BLOCKED: over the limit with disputed docs left in: fineweb-edu 3 of 295 | 0 · 8/28 · 12 | 0 · 0/18 · 5 | 0 · 11/81 · 2 | 0 · 0/10 · 0 |

### C5 lists of keywords or links

**Picked:** `DA-C5-002` (en-dclm) on all 4 packs; `DA-C5-005` (29 Oct sheet) on all 4 packs.

**Why:** `DA-C5-002`: passes and treats the most labelled rows (4). `DA-C5-005`: treats 3 labelled rows that DA-C5-002 does not. Labelled rows: dclm 61, fineweb-edu 30, nemotroncc 71, synth 7.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-C5-002` | en-dclm | **PICKED** | 0 · 4/61 · 4 | 0 · 0/30 · 0 | 0 · 0/71 · 0 | 0 · 0/7 · 0 |
| `DA-C5-005` | 29 Oct sheet | **PICKED** | 0 · 0/61 · 4 | 0 · 2/30 · 0 | 0 · 1/71 · 0 | 0 · 0/7 · 0 |
| `DA-C5-001` | en-dclm | DROP: over the limit on fineweb-edu (4/158) | 0 · 7/61 · 8 | 4 · 3/30 · 8 | 0 · 9/71 · 2 | 0 · 0/7 · 5 |
| `DA-C5-003` | en-fineweb-edu | BLOCKED: held so that the whole sheet fits the limit with disputed docs left in on dclm (3/170 docs touched, limit 1): it touches b19371a31d9aed81, and treats 4 labelled rows that no other kept C5 rule treats, the fewest of the rules that touch counted docs | 0 · 1/61 · 5 | 0 · 2/30 · 0 | 0 · 0/71 · 4 | 0 · 1/7 · 0 |
| `DA-C5-004` | en-nemotroncc | BLOCKED: over the limit with disputed docs left in: dclm 2 of 170, fineweb-edu 7 of 295 | 1 · 2/61 · 11 | 0 · 1/30 · 8 | 0 · 10/71 · 1 | 0 · 0/7 · 1 |
| `DA-C5-006` | en-fineweb-edu | DROP: over the limit on dclm (3/62) | 3 · 8/61 · 46 | 0 · 3/30 · 0 | 0 · 0/71 · 0 | 0 · 0/7 · 0 |

### D1 wrong language label

**Picked:** nothing.

**Why:** The language tag is taken as correct; no detector runs. Labelled rows: dclm 1, fineweb-edu 0, nemotroncc 1, synth 0.

### D3 mixed language

**Picked:** `DA-D3-003` (en-nemotroncc) on all 4 packs.

**Why:** `DA-D3-003`: passes and treats the most labelled rows (6). Labelled rows: dclm 24, fineweb-edu 5, nemotroncc 6, synth 1.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-D3-003` | en-nemotroncc | **PICKED** | 0 · 3/24 · 3 | 0 · 1/5 · 1 | 0 · 2/6 · 0 | 0 · 0/1 · 0 |
| `DA-D3-002` | en-fineweb-edu | DROP: changes no document of any English pack | 0 · 0/24 · 0 | 0 · 0/5 · 0 | 0 · 0/6 · 0 | 0 · 0/1 · 0 |

### D4 bad machine translation

**Picked:** `DA-D4-001` (en-dclm) on all 4 packs.

**Why:** `DA-D4-001`: passes and treats the most labelled rows (1). Labelled rows: dclm 21, fineweb-edu 3, nemotroncc 17, synth 2.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-D4-001` | en-dclm | **PICKED** | 0 · 1/21 · 1 | 0 · 0/3 · 0 | 0 · 0/17 · 0 | 0 · 0/2 · 0 |

### D5 translationese

**Picked:** nothing.

**Why:** No English medicine; translationese needs a model, not a pattern. Labelled rows: dclm 1, fineweb-edu 1, nemotroncc 0, synth 0.

### F1 personal data

**Picked:** `DA-F1-005` (new, to the F1 ruling) on all 4 packs.

**Why:** `DA-F1-005`: the rule written to the instructor's ruling of 31 Oct, so it is never left out; the other F1 rules treat more labelled rows but do not follow the ruling. It treats 4 labelled rows. Labelled rows: dclm 13, fineweb-edu 12, nemotroncc 13, synth 2.

| rule | source | decision | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|
| `DA-F1-005` | new, to the F1 ruling | **PICKED** | 0 · 2/13 · 0 | 0 · 0/12 · 0 | 0 · 1/13 · 0 | 0 · 1/2 · 1 |
| `DA-F1-002` | en-dclm | DROP: does not follow the instructor's ruling: it writes `[EMAIL]` and `[PHONE]`, not `<EMAIL>` and `<PHONE>`; it replaces every phone number, also an organisation's; it has no address part. Its email test is used in the new rule | 0 · 7/13 · 7 | 0 · 8/12 · 7 | 0 · 9/13 · 3 | 0 · 1/2 · 3 |
| `DA-F1-003` | en-fineweb-edu | DROP: does not follow the instructor's ruling: it deletes the value (and the line, when nothing else is left on it) instead of putting a typed placeholder; it also removes ID numbers, which the ruling does not name | 0 · 10/13 · 14 | 0 · 8/12 · 4 | 0 · 11/13 · 5 | 0 · 2/2 · 4 |
| `DA-F1-004` | en-fineweb-edu | DROP: does not follow the instructor's ruling: it deletes emails and phone numbers instead of putting a typed placeholder, and takes every email and number, also an organisation's | 0 · 9/13 · 9 | 0 · 8/12 · 7 | 0 · 10/13 · 5 | 0 · 2/2 · 3 |

### F2 benchmark leak

**Picked:** nothing.

**Why:** No English medicine; a real rule waits on the G9 benchmark fingerprints. Labelled rows: dclm 1, fineweb-edu 0, nemotroncc 0, synth 1.

### F3 harmful content

**Picked:** nothing.

**Why:** No English medicine; it needs a harm classifier. Labelled rows: dclm 4, fineweb-edu 0, nemotroncc 2, synth 2.

### H3 the same content in another source or language

**Picked:** nothing.

**Why:** No English medicine was submitted for it. Labelled rows: dclm 7, fineweb-edu 0, nemotroncc 0, synth 0.

## Medicines that could not run

| medicine | why |
|---|---|
| `DA-B5-001` (en-nemotroncc-synth) | not rebuilt: a detector that routes documents to a manual fix; CODE_SPAN, LONG_LOWER and _dictionary are given nowhere |
| `DA-C4-001` (en-nemotroncc-synth) | not rebuilt: the author proposes no automatic rule, and WORD_RE and STOP are given nowhere |
| the example edits of one en-nemotroncc-synth sheet | Five python blocks that change one example text each and do not run on their own: not rules. Its rule, `DA-B4-011`, is in the sheet. |
