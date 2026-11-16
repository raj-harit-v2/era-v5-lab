# Spec v1.1 harm tests: the new diseases and their medicines

**The ask** (instructor, due Fri 13 Nov): "Pipeline owner: for each new disease above 1%, write a medicine and a harm test for spec v1.1."

This file records, for each new disease above 1%, its medicine and its harm test.
- **New** means not in `diagnosis/DISEASES.md`.
- **Above 1%** means 1% or more of the docs read in its domain, as counted in `teams/01-data-a/reading/reading_check_v1.md`.

The diseases, codes and rule IDs come from `../../sheets/NEW_DISEASES.md`. The rules themselves are in `../../sheets/medicine_english.md`, `../../sheets/medicine_math.md` and `../../sheets/medicine_sci.md`.

## How the harm tests were run

- **Tool:** the team's `teams/01-data-a/harmtest/harm_test.py`, run unchanged, with `--rule all`. It was `tools/harm_test.py` until theschoolofai/era-v5-lab#244 moved it on 13 Nov; the code is byte-identical, so every run here holds. That runs each rule alone, then all of a sheet's rules in order (ALL IN ORDER). A drop ends a doc, and a fix passes the new text on.
- **Command,** from the repo root, once per pack:

  ```
  python3 -I teams/01-data-a/harmtest/harm_test.py --pack <pack>.parquet --gold teams/01-data-a/gold/<pack>_gold.csv \
    --rules teams/01-data-a/spec_v1_1/sheets/medicine_<domain>.md --rule all --report teams/01-data-a/spec_v1_1/results/sheets/<pack>_harm.json
  ```
- **Data:** the Week 1 pack files, and the Data A gold set of each pack, which is the docs two readers agreed are clean.
- **Limit:** gold docs changed plus dropped must be at most `max(1, floor(1% of gold))`. Each pack is judged on its own, never pooled. A gold doc counts as touched if any character changes or the doc is dropped.

  | packs | gold docs | limit |
  |---|---|---|
  | math-finemath | 86 | 1 |
  | math-megamath | 26 | 1 |
  | sci-finepdfs | 202 | 2 |
  | en-dclm | 62 | 1 |
  | en-fineweb-edu | 158 | 1 |
  | en-nemotroncc | 129 | 1 |
  | en-nemotroncc-synth | 326 | 3 |
- **Reports** (IDs and counts only): one `<pack>_harm.json` per pack in this folder, for the 2 math packs, sci-finepdfs and the 4 English packs.
  - **Code sha256:** `538501e9…` for `medicine_math.md`; `82b62928…` for `medicine_sci.md` (13 Nov, sections 1–12 after the gold-doc fixes; it was `3efa627d…` with sections 1–6); `8fb54cd5…` for `medicine_english.md`.
  - **Older English reports:** `en-dclm`, `en-fineweb-edu` and `en-nemotroncc` are from the run with the withdrawn `DA-D6-002` still in the sheet (code `22853296…`). That rule was off on those three packs, so the results for the two remaining rules are the same.
  - **Commit:** the math rules and reports are from `14d4549` on `g1-spec-v1-1` (patilvijay23/era-v5-lab). The science update of 13 Nov (sections 7–12 and the new `sci-finepdfs_harm.json`) is not committed yet.
- **What else was checked:**
  - each rule's unit tests (`tests/test_medicine_english.py`, `tests/test_medicine_math.py`, `tests/test_medicine_sci.py`), listed per medicine under "Unit tests for each medicine" below;
  - how many of the readers' docs each rule catches on the cleaned sample (`scripts/reading_recall.py`).

## Each new disease: medicine and harm test

The harm column gives the gold docs changed plus dropped, over the gold docs, for each pack the rule was tested on.
- A rule is tested on every gold set of its family. On a pack outside its `ORIGIN`, it keeps every doc by design; this is marked "not in ORIGIN".
- "Reading docs treated" counts the readers' docs with the disease that the rule changes or drops.

### Math: 299 docs read, so a disease needs 3

| # | new disease (reading code) | docs, rate | rule | action | medicine | harm test (alone) | reading docs treated |
|---|---|---|---|---|---|---|---|
| 1 | Content lost in extraction: formulas (NEW-missing-formulas) | 29, 9.7% | `DA-C7-001` | drop | Drops a doc with 4 or more gaps that lost formulas leave: a line ending in `=` or a word like "is" before a new sentence, `show that .`, empty answer options, a `?` where a value should be. | finemath 0/86 PASS · megamath 0/26 PASS | 4 / 29 |
| 2 | Layout lost in extraction: flattened formulas (NEW-flattened-formulas) | 22, 7.4% | `DA-C8-001` | drop | Drops a doc where a formula is split one token per line: 8 or more short lines in a row, 2 or more of them with an operator. Option labels such as `(a)` break the run. | finemath 0/86 PASS · megamath 0/26 PASS | 3 / 22 |
| 3 | SEO filler (NEW-seo-filler) | 15, 5.0% | `DA-C9-001` | fix + drop | Drops SEO landing pages by the sentences only they write: tutoring and homework-app sales lines, the 6ya line, exam-tips filler, a "Road distance" page, the ebook spinner. Removes the "You are watching: …" line that copying sites add. | finemath 0/86 PASS · megamath 0/26 PASS | 8 / 15 |
| 4 | Words run together (NEW-missing-spaces) | 13, 4.3% | `DA-A8-001` | fix | Puts the space back where a lowercase word runs into a capitalised word that starts a sentence or heading (`HydrogenWhen` → `Hydrogen When`, `here.The` → `here. The`). It leaves code lines, code fences and brand names alone. | finemath 1/86 PASS · megamath 0/26 PASS | 5 / 13 |
| 5 | Layout lost in extraction: merged table cells (NEW-merged-table-cells) | 11, 3.7% | `DA-C8-002` | drop | Drops a doc with a flattened table row: a line of 20 or more tokens, at least 80% of them numbers or operators. | finemath 0/86 PASS · megamath 0/26 PASS | 3 / 11 |
| 6 | Pages made for search: template pages (NEW-template-pages) | 9, 3.0% | `DA-C9-003` | drop | Drops calculator, unit-converter and number-fact pages made from a template, recognised by any of three signs: their fixed headings, a sentence only converter sites write, or one value repeated in the headings. | finemath 1/86 PASS · megamath 0/26 PASS | 8 / 9 |
| 7 | Machine-written text (NEW-ai-generated-text) | 8, 2.7% | `DA-D6-001` | fix + drop | On a forum page, it removes the "In summary, the conversation …" line and the numbered FAQ the forum adds. It drops a machine-written article that shows 2 of these signs: FAQ headings, a Conclusion heading, 3 or more intro-style headings, an "In summary/In conclusion," sentence. | finemath 0/86 PASS · megamath 0/26 (not in ORIGIN) | 3 / 8 |
| 8 | Content lost in extraction: figures (NEW-missing-figures) | 5, 1.7% | `DA-C7-002` | drop | Drops a problem that refers to a missing figure, plot or drawing: twice, or once in a doc under 2,000 characters. | megamath 0/26 PASS · finemath 0/86 (not in ORIGIN) | 4 / 5 |

### Science: 200 docs read, so a disease needs 2

Aditeya read 100 docs (mittalutkarsh/era-v5-lab#3) and Utkarsh read 100 (mittalutkarsh/era-v5-lab#5). Utkarsh's reading was added on 13 Nov, and rows 15–20 come from it.

| # | new disease (reading code) | docs, rate | rule | action | medicine | harm test (alone) | reading docs treated |
|---|---|---|---|---|---|---|---|
| 9 | Word split in extraction: line-end hyphen (NEW-hyphen-split-words) | 3, 1.5% | `DA-A7-001` | fix | Joins a word split at a line end (`stereo- scopic` → `stereo-scopic`) and keeps the hyphen. Suspended hyphens such as `pre- and post-` stay. | sci-finepdfs 1/202 PASS | 3 / 3 |
| 10 | Layout lost in extraction: merged table cells (NEW-merged-table-cells) | 3, 1.5% | `DA-C8-003` | fix | Splits a table cell that holds two numbers into the empty cell next to it (`\| 332 50.4 \|  \|` → `\| 332 \| 50.4 \|`). | sci-finepdfs 0/202 PASS | 1 / 3 |
| 11 | Content lost in extraction: table body or list (NEW-missing-table-data) | 3, 1.5% | `DA-C7-003` | fix | Cuts a dangling "… with the following members." when no list follows it. | sci-finepdfs 0/202 PASS | 1 / 3 |
| 12 | Layout lost in extraction: reading order (NEW-reading-order) | 2, 1.0% | `DA-C8-004` | fix | Puts numbered steps that are out of order back in order (3, 5, 4 → 3, 4, 5). | sci-finepdfs 0/202 PASS | 1 / 2 |
| 13 | SEO filler (NEW-seo-filler) | 2, 1.0% | `DA-C9-002` | drop | Drops "ebook" pages made by a text spinner, recognised by the sentences only the spinner writes. | sci-finepdfs 0/202 PASS | 2 / 2 |
| 14 | Blank form fields (NEW-underscore-blanks, NEW-form-blanks) | 7, 3.5% | `DA-B6-001` | drop | Drops a blank form: one where underscore runs make up 30% or more of the text. | sci-finepdfs 0/202 PASS | 2 / 7 |
| 15 | Layout lost in extraction: page numbers and footers (NEW-page-artifact) | 9, 4.5% | `DA-C8-005` | fix | Deletes `Page N` / `Page N of M` lines, an unfilled `Page No. – Page No.`, a date-only line that stands alone and repeats, and a lone page number as the first line, the last line after a finished sentence, or between two lines of running text. | sci-finepdfs 0/202 PASS | 8 / 9 |
| 16 | Words run together (NEW-missing-spaces) | 3, 1.5% | `DA-A8-002` | fix | Puts a space back in front of a listed field label glued to the word before it (`MACEDuration:` → `MACE Duration:`). | sci-finepdfs 0/202 PASS | 1 / 3 |
| 17 | Word split in extraction: drop cap (NEW-drop-cap-split) | 2, 1.0% | `DA-A7-002` | fix | Joins a lone capital letter to the lowercase line after it (`D` / `eveloping` → `Developing`). `A` and `I` are left. | sci-finepdfs 0/202 PASS | 1 / 2 |
| 18 | Word split in extraction: small caps (NEW-small-caps-split) | 2, 1.0% | `DA-A7-003` | fix | Joins a split first letter back (`F OODS` → `FOODS`) on lines set in small caps (no lowercase letter, more split pairs than whole capital words), in a doc with 3 or more splits. | sci-finepdfs 0/202 PASS | 2 / 2 |
| 19 | Content lost in extraction: figures (NEW-missing-figures) | 2, 1.0% | `DA-C7-004` | fix | Replaces each Markdown image link to a bare `image` / `image1.png` with its caption as text, and deletes links with no caption. | sci-finepdfs 3/202 **FAIL**, all 3 gold contradictions | 2 / 2 |
| 20 | Content lost in extraction: near-empty doc (NEW-near-empty) | 2, 1.0% | `DA-C7-005` | drop | Drops a doc under 250 characters. | sci-finepdfs 1/202 PASS | 2 / 2 |

### English: 200 docs read, so a disease needs 2

Four readers read 50 docs each:
- narasimhatejav, en-fineweb-edu (mittalutkarsh/era-v5-lab#7)
- kunal, en-nemotroncc-synth (mittalutkarsh/era-v5-lab#8)
- aneesha, en-nemotroncc (mittalutkarsh/era-v5-lab#9)
- Smita, en-dclm (patilvijay23/era-v5-lab#36)

Each English rule also keeps every doc of en-dclm and en-fineweb-edu, which aren't in its `ORIGIN` (both 0, PASS).

| # | new disease (reading code) | docs, rate | rule | action | medicine | harm test (alone) | reading docs treated |
|---|---|---|---|---|---|---|---|
| 21 | Words run together (NEW-missing-spaces) | 2, 1.0% | `DA-A8-003` | fix | Puts the space back after a full stop between a lowercase word and a capitalised one (`choose.Compose` → `choose. Compose`). It leaves URLs, abbreviations and code alone. | en-nemotroncc 1/129 PASS (a gold contradiction) · en-nemotroncc-synth 0/326 (not in ORIGIN) | 1 / 2 |
| 21b | Words run together with no full stop (NEW-missing-spaces; HariniJasti, patilvijay23/era-v5-lab#41) | 56 of 500 Week 1 diagnosis docs (HariniJasti's labels) | `DA-A8-004` | fix | Puts a space between a lowercase word of 3+ letters and a capitalised word glued to it (`fileEdit` → `file Edit`). It leaves code lines, multi-hump camelCase, 1–2 letter prefixes (`iPhone`) and a short list of names (`youTube`) alone. | en-nemotroncc 1/129 PASS (a gold contradiction, `fd16036899796ca4`) | not measured on the reading sample; 29 of the 500 diagnosis docs, 66 glued pairs (15 Nov) |
| 22 | Facts the rewrite got wrong (NEW-factual-error), new code D7 | 4, 2.0% | `DA-D7-001` | drop | Quarantines the 6 confirmed docs by doc_id: kunal's 4, and 2 wrong answers from appended Q&A. Nothing in the text marks a wrong fact, so it finds no other cases. | en-nemotroncc-synth 0/326 PASS (trivial: no listed doc is gold) · en-nemotroncc 0/129 (not in ORIGIN) | 4 / 4, and the 2 wrong answers |
| 23 | Machine-written text: an appended question and answer (NEW-appended-qa) | 3, 1.5% | `DA-D6-002`, **withdrawn** | — | It removed trailing `Question: … Answer: …` lines, and caught all 3 reading docs. | en-nemotroncc-synth **32/326 FAIL** in its first run | 3 / 3 |

**Why `DA-D6-002` was withdrawn** (aneeshads, 13 Nov):
- **The 32 gold docs:** each ends in ordinary, correct Q&A (1 to 4 pairs). Appended Q&A is part of this synthetic pack, and the gold readers marked it clean.
- **No narrower rule:** nothing in the text separates kunal's docs. A score for how much of the answer appears in the passage gives 0.67, 1.00 and 1.00 for his 3, and 0.50 to 1.00 for the gold docs.
- **kunal's 3 docs:** his 2 wrong answers are facts the rewrite got wrong, so they went to `DA-D7-001`; the third answer is correct.
- **Open:** whether appended Q&A is a disease is for the team to rule.

**Of the 23 Data A medicines in force, 22 pass their harm test on their own.** (The 23rd is `DA-A8-004`, added on 14 Nov from HariniJasti's #41: 1/129 PASS.) `DA-C7-004` fails: it changes 3 of 202 gold docs, against a limit of 2, and all 3 have the disease itself (gold contradictions, below). With them left out, it passes at 0/199. A 23rd, `DA-D6-002`, was withdrawn after failing at 32/326. Data B's `DB-C6-001`, the 23rd medicine in `specv1_1.md`, also fails alone: 2/80 on ind-te-sangraha-v, both gold contradictions, so 0/78 without them (see "Other families and diseases").

## All the rules of a sheet together (ALL IN ORDER)

| pack | gold docs (limit) | changed | dropped | result | gold docs touched |
|---|---|---|---|---|---|
| math-finemath | 86 (1) | 1 | 1 | **FAIL** (2/86) | `2d328b828fa97706` (`DA-A8-001`), `0f119a596e8b7f63` (`DA-C9-003`) |
| math-megamath | 26 (1) | 0 | 0 | **PASS** | none |
| sci-finepdfs | 202 (2) | 4 | 1 | **FAIL** (5/202) | `920855df51f37db8` (`DA-A7-001`); `4b958ac1f45443b5`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd` (`DA-C7-004`); `b6fd81dbf90b0d17` dropped (`DA-C7-005`) |
| en-dclm | 62 (1) | 0 | 0 | **PASS** | none |
| en-fineweb-edu | 158 (1) | 0 | 0 | **PASS** | none |
| en-nemotroncc | 129 (1) | 2 | 0 | **FAIL** (2/129); 0/127 PASS without the gold contradictions | `056cc9bc44c927e2` (`DA-A8-003`), `fd16036899796ca4` (`DA-A8-004`) |
| en-nemotroncc-synth | 326 (3) | 0 | 0 | **PASS** | none (32/326 FAIL before `DA-D6-002` was withdrawn) |

With sections 1–6 only (12 Nov), sci-finepdfs was 1/202 PASS in order. With all 12 rules, the first run of 13 Nov was 9/202. After the gold docs were read and two rules narrowed, it is 5/202. 4 of those 5 are gold contradictions. With them left out, it passes at 1/198.

### Science gold docs read on 13 Nov

The first run of the 12 rules touched 8 gold docs, and all 8 were read:
- **`DA-A7-003`, real harm in 3 docs:** `322dc47ddcb0a780` (course codes `G HIST` → `GHIST`), `b31b17ba09b9a8b8` (`A COMPREHENSIVE` → `ACOMPREHENSIVE`, `D AND E` → `DAND E`) and `d8df5df66bb7a574` (`CECILY’S ENGLISH` → `CECILY’SENGLISH`). The rule was narrowed to lines set in small caps, and now touches 0.
- **`DA-C8-005`, real harm in 1 doc:** `8a2493cdf33f9a38` lost the date under each signed comment. A date footer now has to stand alone between blank lines, and the rule touches 0.
- **`DA-C7-004`, gold contradictions in 3 docs:** `4b958ac1f45443b5`, `d0a0a41263e845f5` and `eb6ad9726f2d7ddd` each have empty image links. The first version also deleted their captions, so it now keeps them as text.
- **`DA-C7-005`, a false positive within the limit:** `b6fd81dbf90b0d17` is a complete 220-character certificate.

### Gold contradictions

Each gold doc touched has the very disease its rule targets. The gold set was built in Week 1, before these diseases were named.

| gold doc | rule | what is in it |
|---|---|---|
| `2d328b828fa97706` | `DA-A8-001`, words run together (fix) | `fieldtrip.Write an equation`: a missing space after a full stop. The rule makes it `fieldtrip. Write`. |
| `0f119a596e8b7f63` | `DA-C9-003`, template pages (drop) | A grams-to-kilograms converter page, with the same template headings as reading doc `d0693c18056bae02` ("Alternative conversion", "Approximate result", "Conversion table", "… chart"). |
| `920855df51f37db8` | `DA-A7-001`, hyphen-split words (fix) | A word split at a line-end hyphen in a Finnish abstract. This one is within the limit. |
| `4b958ac1f45443b5` | `DA-C7-004`, empty image links (fix) | `![Fig. 4. XPS of C dots …](image)` and `![Fig. 5. EDAX …](image)`: figure legends in links to an image that isn't there. |
| `d0a0a41263e845f5` | `DA-C7-004`, empty image links (fix) | `![Biotin](image)`, `![Folate](image)`, `![Ascorbic acid](image1.png)` and 4 more: structure drawings that aren't there. |
| `eb6ad9726f2d7ddd` | `DA-C7-004`, empty image links (fix) | `![Diagram](image)` after "according to the following diagram:". |
| `056cc9bc44c927e2` | `DA-A8-003`, words run together (fix) | `tantrum.To the sociopath`: a missing space after a full stop, in en-nemotroncc. This one is within the limit. |
| `fd16036899796ca4` | `DA-A8-004`, words run together with no full stop (fix) | `saidSanaz`: a quote glued to the speaker's name (withheld here), in en-nemotroncc. Alone it is within the limit; with `056cc9bc44c927e2` it takes en-nemotroncc in order to 2/129. |
| `85644a4840025b6f` | `DB-C6-001`, runs of dots (fix), ind-te-sangraha-v | A bare `..` after మాట్లాడుతూ ("speaking"), before a quote. oddjoker91 labelled a bare `..` as C6 in other docs of the pack. |
| `01418489e7410bdf` | `DB-C6-001`, runs of dots (fix), ind-te-sangraha-v | A bare `..` after మరణిస్తే ("if they die"), at the end of a clause. |

**Handling** (proposed by aneeshads on 13 Nov; **Vijay agreed**): they are marked as gold contradictions, as spec v1 did for `eee25e81417bc1b7` in sci.
- They are left out of the count for these rules only.
- They are flagged for a reader to check again at the next gold refresh.

With the two finemath docs left out, finemath in order touches 0 of the other 84 gold docs and passes. With the two Indic docs left out, `DB-C6-001` passes at 0/78. The gold CSVs, `harm_test.py` and `harm_test_indic.py` are not changed.

## The combined spec v1.1 (Gate 2, 14 Nov)

TSAI made spec v1 and spec v1.1 one spec. `sheets/specv1_1.md` holds both, in run order: 364 cards (with `DA-A8-004`), which build into a `clean.py` of 246 rules and the shared F1. `scripts/combine_spec.py` writes it from `specv1.md` and `specv1_1_additions.md`. Its `clean()` was harm-tested per pack, summarised in `../combined/validation.md`; the per-pack reports go into the `clean.py` PR, with the rebuilt `clean.py`. It was checked on 14 Nov:
- **Harm, all rules in order:** on every pack it changes exactly the gold docs the v1.1 rules change on their own. Spec v1 alone changes none.
  - **Pass:** the 6 code packs, en-dclm, en-fineweb-edu, en-nemotroncc-synth and math-megamath.
  - **Fail:** en-nemotroncc 2/129, math-finemath 2/86, sci-finepdfs 5/202 and ind-te-sangraha-v 2/80, each only on its gold contradictions (and `DA-C7-005`'s one false positive on sci-finepdfs).
  - **Without the gold contradictions:** every pack passes (en-nemotroncc 0/127, finemath 0/84, sci-finepdfs 1/198, ind-te-sangraha-v 0/78).
- **Speed, whole `clean()`** (Apple M4, one core, best of 3; spec v1 as on TSAI main): unchanged on code, English and Indic, except en-nemotroncc (714 → 556 docs/s). Math goes from 167 and 417 to 122 and 227 docs/s, and sci-finepdfs from 125 to 70 docs/s: the v1.1 rules' own time, after both speed passes below. 0 errors.

## Speed (TSAI rule of 14 Nov)

All 23 rules of the Spec v1.1 sheet (then `specv1_1.md`, now `specv1_1_additions.md`) were timed with `scripts/time_rules.py` (which comes with the `clean.py` PR) on every doc of 8 whole packs, not only the gold:
- **The packs:** the Week-1 packs used by the harm runs (sha256 checked against each `<pack>_harm.json`), and `ind-te-sangraha-v.parquet`. Each pack has 500 docs.
- **The method:** each rule alone, then the whole sheet in order, as `clean.py` runs it.
- **Result:** 0 errors, and 0 docs over the 5 s limit. On a pack a rule doesn't cover, its `pack_id` check costs under 1 µs per doc.

**Five science rules were made faster on 14 Nov.**
- **The fixes:** each now does a cheap check for text its regex needs, and returns at once without it. `DA-B6-001` no longer counts characters in a Python loop.
- **The output is identical:** old and new versions gave the same output on every doc of all 8 packs, rule by rule and in order.
- **Harm and tests:** the sci-finepdfs harm test is unchanged (5/202 in order; only the code fingerprint in `sci-finepdfs_harm.json` is new). The 177 unit tests of that day pass, 10 of them for `time_rules.py`.

| rule | sci-finepdfs, 500 docs: before → after | the change |
|---|---|---|
| `DA-C9-002` | 2.11 s → 0.44 s | skip unless the text holds a phrase every spinner sentence needs (`ebook`, `perplexed to enjoy` …) |
| `DA-C7-003` | 1.78 s → 0.48 s | skip unless the text holds "the following" and one of its nouns |
| `DA-B6-001` | 1.11 s → 0.33 s | skip unless the text holds `_____`; count non-space characters with one regex pass, not a Python loop |
| `DA-A8-002` | 1.15 s → 0.57 s | a fast search for any `Label:` before the slow insert pass |
| `DA-A7-001` | 0.59 s → 0.55 s | skip unless the text holds `- ` (most science docs do) |

| pack (500 docs) | whole sheet in order, before → after |
|---|---|
| sci-finepdfs | 7.86 s (64 docs/s) → **3.43 s (146 docs/s)** |
| math-finemath / math-megamath | 1.35 s / 1.57 s (370 / 319 docs/s), unchanged |
| en-nemotroncc | 0.16 s (3,087 docs/s) |
| en-dclm, en-fineweb-edu, en-nemotroncc-synth | 0.015 s each (about 34,000 docs/s) |
| ind-te-sangraha-v | 0.017 s (29,715 docs/s) |

The "after" column is the run of `scripts/time_rules.py` quoted in the PR (14 Nov): 14.0 s for all 8 packs, 0 errors or timeouts.

**A second speed pass (14 Nov), on the rules the skill's checklist flagged.** It took out the last Python loops over tokens and characters, and added cheap checks to three more rules. Old and new gave **identical output on every doc of the 8 packs**, for each of the three sheets, rule by rule and in order. The harm tests on the 7 packs of these sheets are unchanged (only the code fingerprints in `<pack>_harm.json` are new). 199 unit tests pass.

| rule | before → after, 500 docs | the change |
|---|---|---|
| `DA-C9-001` (math) | 0.36 / 0.44 s → **0.11 / 0.15 s** (finemath / megamath) | skip the 11-way case-insensitive search unless the text holds a phrase every alternative needs (`tutor`, `homework`, `6ya` …) |
| `DA-C7-001` (math) | 0.50 / 0.57 s → 0.43 / 0.47 s | count the cheap gaps first and stop at 4; skip the line loop when no line ends in `=` or a dangling word, or is an empty option |
| `DA-C8-002` (math) | 0.08 / 0.09 s → 0.07 / 0.09 s | **the Python loop over tokens is gone**: one anchored regex counts the tokens that `C8T_CELL` matches whole |
| `DA-A7-003` (sci) | 0.34 s → **0.21 s** | **the Python loop over characters is gone on ASCII lines**: one `[a-z]` search. A non-ASCII line keeps `str.islower` |
| `DA-A8-003` (English) | 0.15 s → **0.08 s** | skip the line loop when no glued `word.Word` is in the text |

Two other ideas were measured and dropped, because they were slower: a whole-text pre-check for `DA-A8-001` (0.21 → 0.27 s) and one for `DA-A7-003` (0.34 → 0.48 s).

**`DA-A8-004`, 15 Nov (HariniJasti's two suggestions on patilvijay23/era-v5-lab#41).** A quick check, `[a-z]{3}[A-Z][a-z]`, on the doc and then on each line, takes the rule from 0.123 s to **0.085 s** per 500 en-nemotroncc docs (4,079 → 5,908 docs/s; Apple M4, one core, best of 5), with identical output on all 500 docs. Her narrower code test, added with it, splits 66 glued pairs in 29 docs, not 55 in 28, and loses none. The harm tests of the 4 English packs are unchanged (only the code fingerprints in `<pack>_harm.json` are new), and so is the combined sheet's on en-nemotroncc (the same 2 gold contradictions).

| pack (500 docs) | v1.1 rules in order (`time_rules.py`): after pass 1 → after pass 2 |
|---|---|
| math-finemath / math-megamath | 1.35 / 1.57 s (370 / 319 docs/s) → **1.03 / 1.17 s (486 / 429 docs/s)** |
| sci-finepdfs | 3.43 s (146 docs/s) → 3.30 s (152 docs/s) |
| en-nemotroncc | 0.16 s (3,087 docs/s) → **0.09 s (5,369 docs/s)** |

**What is still slowest:**
- **Science:** `DA-A8-002` (0.58 s), `DA-A7-001` (0.56 s), `DA-C7-003` (0.49 s), `DA-C9-002` (0.44 s) and `DA-B6-001` (0.34 s). All are regex passes or cheap checks, with no Python loop over characters or tokens. Where in each the time goes was not profiled further.
- **Math:** `DA-C7-001` (0.44 to 0.47 s).
- **Loops left:** about 10 rules still loop over a doc's lines, because each line is compared with its neighbours (`DA-D6-001`, `DA-C8-004`, `DA-C8-005`, `DA-A7-002` …).

None is near the 5 s per-doc limit. The slowest single doc for any rule is 96 ms (`DA-B6-001` on `35eb8b91a98d3a41`). Before the first pass it was 255 ms (`DA-C9-002`, the same doc).

## Unit tests for each medicine

The harm test checks a rule against the gold set. The unit tests check that it does what its card says: what it must change or drop, what it must leave alone, and that running it twice gives the same text.
- **How they load the rules:** each test file loads its sheet the way `harmtest/harm_test.py` does (`harm_test.load_rules`), so the tests run the same code as the harm test.
- **Text:** all of it is made up. Where a test copies the shape of a gold doc a rule once harmed, it is a look-alike, not gold text.
- **Run:** from `teams/01-data-a`: `python3 -m unittest discover -s spec_v1_1/tests`.
- **Last run:** 15 Nov 2026, 184 tests, **OK**:
  - 17 for `scripts/combine_spec.py` (`test_combine_spec.py`): run order, wrapper, links and refusals on made-up sheets; that `build_clean.py` reads the real combined sheet; and that `sheets/specv1_1.md` is up to date;
  - 41 for the math medicines;
  - 44 for the science medicines;
  - 20 for the English medicines (10 of them for `DA-A8-004`);
  - 7 for the Indic medicine;
  - 5 for a spec v1 code rule on docs labelled `lang_label = "code"` (`test_code_lang_label.py`, Gate 2 request): `DA-A1-001` fires in all 6 code packs, because of its `pack_id` check;
  - 50 for the reading scripts, as on main (`test_collect_reading_prs.py` 24, `test_show_examples.py` 11, `test_reading_check.py` 10, `test_reading_recall.py` 5). The tests of `time_rules.py` go into the `clean.py` PR with it.

The numbers in the `#` column match the disease tables above. "Twice" means a test that runs the rule on its own output and expects no change.

### Math: `tests/test_medicine_math.py`, 41 tests

**For the whole sheet (3):**
- `test_one_rule_for_each_new_math_disease`: the sheet holds exactly the 8 math rules.
- `test_no_rule_uses_the_indic_code_c6`: no rule uses C6, the Indic family's code.
- `test_no_rule_touches_a_doc_with_no_pack`: every rule keeps a doc that has no `pack_id`.

| # | rule | test class (tests) | must change or drop | must stay | other checks |
|---|---|---|---|---|---|
| 1 | `DA-C7-001` lost formulas | `C7Formulas` (6) | 4 gaps (`… tank B =`, `show that .`, `Comparing ,`, a line ending in "is"); empty options `(A)`–`(D)`; sentences cut where the formula was | answer options and lines that carry on to the next line; complete working; only 2 gaps; `=` with the answer below; option labels set above their options. These are the cases behind the gold false positives fixed on 12 Nov. | |
| 2 | `DA-C8-001` flattened formulas | `C8Formulas` (4) | a formula split one token per line | a column of plain numbers (post counts); a short run (`x + 2 = 5` over 6 lines); options one per line, like gold `8828b7bee424578d` | |
| 3 | `DA-C9-001` SEO filler | `C9` (3) | tutor sales, "math teachers in …", homework-app, road-distance and ebook-spinner pages (dropped); a "You are watching: …" line (removed) | an ordinary lesson that mentions a tutor | |
| 4 | `DA-A8-001` words run together | `A8` (6) | `HydrogenWhen` → `Hydrogen When`, `ProblemsThe` → `Problems The`, `minQuestions` → `min Questions`, `here.The` → `here. The` | brand and code names (`JavaScript`, `WordPress`, `PowerPoint`, `LinkedIn`, `YouTube`, `maxValue`); code lines and code fences | twice; off on sci-finepdfs and on another language (`hi`) |
| 5 | `DA-C8-002` merged table cells | `C8Tables` (2) | a flattened table row of 20 or more numeric tokens | short numeric lines; prose with numbers | |
| 6 | `DA-C9-003` template pages | `C9Templates` (8) | a number-fact page; one dollar amount in three headings; a unit-converter sentence; converter and conversion-table headings | a lesson with weak headings only; years and short numbers in headings; text with no headings | off on sci-finepdfs |
| 7 | `DA-D6-001` machine-written text | `D6` (5) | a forum's "In summary, the conversation …" line with its numbered FAQ, and the summary line alone (removed); an article with 2 machine-written signs (dropped) | a doc with one sign only | off on megamath |
| 8 | `DA-C7-002` lost figures | `C7Figures` (4) | a short problem with a missing figure; a long doc with two figure references | a long doc with one reference | off on finemath |

### Science: `tests/test_medicine_sci.py`, 44 tests

**For the whole sheet (3):**
- `test_one_rule_for_each_new_science_disease`: the sheet holds exactly the 12 science rules.
- `test_every_rule_is_off_on_other_packs`: every rule keeps a doc from a math pack or with no `pack_id`.
- `test_the_13_nov_rules_are_off_on_other_packs`: the 6 rules added on 13 Nov keep their own trigger text on other packs.

| # | rule | test class (tests) | must change or drop | must stay | other checks |
|---|---|---|---|---|---|
| 9 | `DA-A7-001` line-end hyphen | `A7` (5) | `company- owned` → `company-owned`, `stereo- scopic` → `stereo-scopic`, `day- to-day` → `day-to-day` | suspended hyphens (`pre- and post-test`, `two- to three-fold`, `first- or second-order`, `low- versus high-dose`); other dashes (`x- axis`, a list dash, `a - b`, `Section A- Part`, `COVID- 19`, `pages 10- 12`) | twice |
| 10 | `DA-C8-003` two numbers in one cell | `C8Cells` (3) | `\| 332 50.4 \|  \|` → `\| 332 \| 50.4 \|` | full cells (`10 20` next to a filled cell); a row that doesn't start with `\|`; `1,323` with an empty cell | twice |
| 11 | `DA-C7-003` lost list | `C7Tables` (2) | "… is constituted with the following members." with no list after it | an intro followed by a numbered list or by a name; "Consider the following: …" in running text | |
| 12 | `DA-C8-004` steps out of order | `C8Order` (2) | steps 1, 2, 3, 5, 4 put back in order | steps in order; counting down; numbers with a gap (1, 3, 2, 7); a block of only 2 | |
| 13 | `DA-C9-002` ebook spinner | `C9` (2) | 4 spinner pages: "If you ally dependence …", "Right here, we have countless books …", "Access Free Ebook …", 5 `Page n/N` markers with "Ebook" | a report with 3 page markers | |
| 14 | `DA-B6-001` blank forms | `B6` (3) | a form that is mostly underscore blanks | a few blanks in a long text; a page just under the 30% bar | |
| 15 | `DA-C8-005` page numbers and footers | `C8Pages` (7) | `Page 10 of 11`, `Page 1`, `PAGE 3/12`, `Page No. – Page No.`; a page number as the first line, the last line, or between two paragraphs; a date footer that repeats; a date left alone once a `Page N` line above it goes | a date under each signature (look-alike of gold `8a2493cdf33f9a38`); a column of years; a single date; a section number between headings; a number at the end of an unfinished sentence; `14` above `15`; a number inside a sentence | twice |
| 16 | `DA-A8-002` field labels | `A8Labels` (3) | `MACEDuration:` → `MACE Duration:`, `On-goingCurrent Value:` → `On-going Current Value:` | `Telephone:`, `JavaScript:`, a label at the start, `the Value:`, a label with no colon, capitals run together | twice |
| 17 | `DA-A7-002` drop cap | `A7DropCap` (3) | `D` / `eveloping a Resort …` → `Developing a Resort …` | `A` and `I` (words); single letters in a form (`T`, `F`, `E`); a short next line (`B` / `ok`); a next line that starts with a capital | twice |
| 18 | `DA-A7-003` small caps | `A7SmallCaps` (4) | `L AKEVILLE S OUTH H IGH S CHOOL`, `S TUDENT A NNOUNCEMENTS`, `M AY 27, 2022`; `F OODS L IMITED … A PEX F ROZEN F OODS` | `A NEW STUDY OF T CELLS`; `VITAMIN D AND E LEVELS`; lines with lowercase; the gold look-alikes: course codes beside lowercase names (`G CHEM 10050`), all-capitals titles with `D AND E`, and a possessive (`MARY’S ENGLISH`) | twice |
| 19 | `DA-C7-004` empty image links | `C7Images` (5) | `![Particle size distribution](image1.png)` → its caption as text; an inline link → its caption; links with no caption (`![](image)`) deleted | real links (a URL, a folder path); a link with no `!`; the word "image" in a sentence | twice |
| 20 | `DA-C7-005` near-empty doc | `C7NearEmpty` (2) | a title and a date only (about 100 characters) | a doc of 254 characters | |

### English: `tests/test_medicine_english.py`, 17 tests

**For the whole sheet (4):**
- `test_one_rule_for_each_new_english_disease`: the sheet holds exactly the 2 English rules in force.
- `test_every_rule_is_off_on_other_packs`: each rule keeps a doc from en-dclm, en-fineweb-edu, a math pack, or with no `pack_id`.
- `test_each_rule_runs_only_on_its_pack`: `DA-D7-001` keeps a listed doc found on en-nemotroncc, and `DA-A8-003` keeps one on en-nemotroncc-synth.
- `test_appended_questions_and_answers_are_left_alone`: no rule removes a trailing Q&A, now that `DA-D6-002` is withdrawn.

| # | rule | test class (tests) | must change or drop | must stay | other checks |
|---|---|---|---|---|---|
| 21b | `DA-A8-004` no full stop (HariniJasti's 3, 4 for the review changes of 14 Nov, and 3 for those of 15 Nov) | `A8NoFullStop` (10) | `fileEdit` → `file Edit`; `saidSanaz` → `said Sanaz`; a prose line with `$`, `<` or a mid-line `;`; `thank youFor` → `thank you For`; a prose line with `return`, `function`, a bare `=` or a URL; a later line after a plain one | `iPhone`, `eBay`, `macOS`, `pdfFiller`, `youTube`, `getMockBuilder`, a code line (` = `, `==`, `=>`, `// `, `$this`, a tag, braces, `()`), a line ending in `;`, a fence, `creamthe` (lowercase glue, not caught) | twice |
| 21 | `DA-A8-003` no space after a full stop | `A8` (3) | `choose.Compose` → `choose. Compose`; `there.Then,` → `there. Then,` | `www.Google.com`, `e.g.The`, `Mr.Smith`, `Node.Js`, `awhile`, a code line, a code fence, an email address, a line with a URL | twice |
| 22 | `DA-D7-001` facts the rewrite got wrong | `D7` (3) | the 6 confirmed doc IDs (dropped) | `ffaad5c6d3dde332`, the appended-Q&A doc whose answer is correct; any other doc | |

**How the tests changed after the gold docs were read (13 Nov):**
- **English, `DA-D6-002` withdrawn:** its 5 tests were removed, and `test_appended_questions_and_answers_are_left_alone` was added. `DA-D7-001`'s tests now cover 6 IDs.
- **`DA-A7-003`:** `test_ordinary_capitals_in_the_gold_set_stay` was added, with look-alikes of the 3 gold docs the first version harmed.
- **`DA-C8-005`:** `test_dates_under_a_signature_stay` and `test_a_date_left_alone_after_a_page_line_goes_in_one_run` were added.
- **`DA-C7-004`:** `test_lines_of_empty_image_links_go` became `test_links_become_their_captions`. `test_links_with_no_caption_go` was added, and the twice test now expects the caption kept.

## Other families and diseases

- **C1 boilerplate in en-nemotroncc (spec v1's `DA-C1-006`, 14 Nov).** HariniJasti's Week 1 labels list C1 lines that `clean()` left in. Her doc_ids were run through `DA-C1-006` and spec v1's whole English `clean()`:

  | label | doc | today | change |
  |---|---|---|---|
  | `Menu` | `f27c315dee45a78b`, `f7b15b4a083e9b67` | removed | none needed |
  | `Advertisement` (a whole line) | `fe09c89adf442739` | removed | none needed |
  | `Share This Post, Choose Your Platform!` | `e19e0e25c760eef3` | kept | added |
  | `STORY CONTINUES BELOW THESE SALTWIRE VIDEOS` | `7533f8eb8ea4eb8d` | kept | added, as `story continues below` and up to 4 words |
  | `Featured athletes` | `739f7ece88e53e0d` | kept | added |
  | `Vote in our latest poll` | `dbd1dda436710dba` | kept | added |
  | `Story Headers` | `58e73b4d54222916` | kept | added |
  | `Hosted 6 events total` | `8eb16f1232108357` | kept | added, as `hosted N events total` |
  | `Link copied`, glued to the end of a headline | `21bd8896d208bfd6` | kept | out of reach: a whole-line rule can't cut it from a content line |
  | `Advertisement – Continue Reading Below …`, the start of a content line | `82b8dbe973dc9e52` | kept | out of reach, for the same reason |

  - **Not in this PR.** `DA-C1-006` is a spec v1 rule, and on Vijay's ruling of 14 Nov this PR holds only spec v1.1. The six labels go into the `clean.py` PR, with the spec v1 speed fixes. The patch is ready: it adds them to `DA-C1-006`'s `WIDGET` list in `spec_v1/sheets/medicine_english.md` and `specv1.md`, still as whole-line matches.
  - **Tested on 14 Nov:**
    - **Old vs new:** they differ on exactly the 6 docs above, and on no other doc of the 4 English packs (2,000 docs).
    - **Gold:** no gold doc changes (0 of 675).
    - **Spec v1's English `clean()`** on the gold stays at 0 changed on all 4 packs, as in #244.
    - **Spec v1's 2,300 pytest tests pass**, with a `clean.py` rebuilt from the edited sheet.

- **Indic family (Data B):** C6, inconsistent punctuation and formatting (`DB-C6-001`, ind-te-sangraha-v, 161 of 500 docs).
  - **Medicine:** Data B's, Medicine 1 in #177. It turns runs of dots into `...`.
  - **Harm test:** Data B's, with `teams/02-data-b/tools/harm_test_indic.py`. On the old 18-doc gold (9 Nov): 1/18 changed, PASS, and the joiner and normal-form audits passed. The 80-doc run below replaces it.
  - **Run on ind-te-sangraha-v's 80-doc gold (aneeshads, 13 Nov):** the same tool and `--rule all`, on oddjoker91's `medicine.md`. Report: `indic_sangraha-v_harm.md` in this folder.

    | rule | changed | dropped | limit | joiners, normal form | result |
    |---|---|---|---|---|---|
    | C6 (`DB-C6-001`) | 2/80 (`01418489e7410bdf`, `85644a4840025b6f`) | 0 | 1 | ok | **FAIL**; 0/78 PASS with the 2 gold contradictions left out |
    | C1 | 0/80 | 0 | 1 | ok | PASS |
    | C2 | 0/80 | 0 | 1 | ok | PASS |
    | all in order | 2/80 | 0 | 1 | ok | **FAIL**; 0/78 PASS with them left out |

    - **The 2 docs:** each has a bare `..`, which the rule turns into `...`. Both readers (oddjoker91 and sreekanthzipsy) marked the docs clean. But oddjoker91 labelled a bare `..` as C6 in other docs: 23 C6 labels point at a 2-character span. So the docs hold the disease as the pack's reader defined it. They are gold contradictions (see "Gold contradictions" above).
    - **The pack file:** `ind-te-sangraha-v.parquet`, 500 docs, the pack that was read and labelled. The Week-1 copy in `Cap1-packs` holds none of the 80 gold docs. Its sha256, `d3d928606d1fd0a7a81fcbce10db3e3d8f4b7df74486bc51c9a9d30299812817`, is the `pack_sha256` in `../../../results/spec_v1/cleaner/specv1_ind-te-sangraha-v_harm.json` (theschoolofai/era-v5-lab#244). So it is the same file as the spec v1 harm run on this pack.
    - **What the rule reaches there:** it changes 241 of the 500 docs, including 144 of the 161 C6-labelled ones.
    - **A narrower version was tried and not taken.** It left a bare `..` alone and passed on all five packs (0/80, 0/24, 0/22, 0/24). But it fixed only 102 of the 161 labelled docs, so Data B's function was kept unchanged.
  - **Run on the sangraha-s packs (aneeshads, 13 Nov):** `teams/02-data-b/tools/harm_test_indic.py --rule all` on oddjoker91's `medicine.md`. Report: `indic_sangraha-s_harm.md` in this folder.

    | pack | gold docs (limit) | C6 | C1 | C2 | all in order | joiners, normal form |
    |---|---|---|---|---|---|---|
    | ind-hi-sangraha-s | 24 (1) | 0/24 PASS | 0/24 PASS | 0/24 PASS | 0/24 PASS | ok |
    | ind-kn-sangraha-s | 22 (1) | 0/22 PASS | 0/22 PASS | 0/22 PASS | 0/22 PASS | ok |
    | ind-te-sangraha-s | 24 (1) | 0/24 PASS | 0/24 PASS | 0/24 PASS | 0/24 PASS | ok |
    | ind-ta-sangraha-s | none | not testable | | | | |

    The rules have no pack check, so they ran on every gold doc and changed none. That is no harm on these packs. The disease was found on ind-te-sangraha-v, which this run doesn't cover.

    **The pack files** are the 500-doc samples published on the `sangraha-s-packs` branch of shankarpandala/era-v5-lab (commit `a836972`, 13 Nov). The packs come from the week-1 packs, from Sangraha's synthetic (translated) split, by AI4Bharat ([ai4bharat/sangraha](https://huggingface.co/datasets/ai4bharat/sangraha), CC-BY-4.0). The copies used match the sha256 values in that branch's `NOTICE.txt` (`shasum -a 256 -c`, all OK):

    | pack file | sha256 |
    |---|---|
    | `ind-hi-sangraha-s.parquet` | `7fd34f97729659a7c0c7f6bed0190e7f4eda29ed8a0f9b9eacbfe4a607a3ff6d` |
    | `ind-kn-sangraha-s.parquet` | `a161966005c037a1bdb70245c2b6135520967c57c5fc618cba5f29d9e248f427` |
    | `ind-ta-sangraha-s.parquet` | `40509e609fb6020649a86baf1b8e849659442ef8e807b02a842ac8f9f757b74d` |
    | `ind-te-sangraha-s.parquet` | `feeb676e76dee102d132846c1af2a92c3ea4d1018e0fd5239f50fc0da0fb6069` |
  - **In `specv1_1_additions.md`:** Medicine 23 (Medicine 363 of the combined `specv1_1.md`), through `sheets/medicine_indic.md`. Data B's function is copied unchanged inside a `pack_id` check for ind-te-sangraha-v.
  - **Unit tests:** `tests/test_medicine_indic.py`, 7 tests:
    - runs of dots (`. .`, `..`, `. . .`, with spaces or tabs) become `...`, and `....` becomes `...`;
    - single dots, `…`, an existing `...`, dots across a line break and `3.67` stay;
    - joiners (ZWJ, ZWNJ) are untouched;
    - it is off on other packs, and a second run changes nothing.
- **Code:** no new disease above 1% was found, so no medicine or harm test is needed. 200 docs were read, by Revant and narasimhatejav (mittalutkarsh/era-v5-lab#6), and every code row is a spec v1 miss.
- **Not new** (already in `DISEASES.md`), so outside v1.1:
  - B1, C5, ligatures (A5), table of contents (C1), many questions on one page (C4), wrong PDF glyphs (A6), and personal names with ages (F1);
  - English two documents joined (C4, 4 docs). Spec v1 has no English C4 rule.
- **Below the bar in English:** 23 codes with 1 doc each; see `../../sheets/decisions_english.md`.
- **Below the bar:** 11 science diseases found in 1 of 200 docs each (0.5%), so they need no medicine. 6 are Aditeya's (A9 accent split, C7 all-figure doc, C7 figure labels, C8 split superscripts, C9 spun text, D6 picture captions) and 5 are Utkarsh's. See `NEW_DISEASES.md`.
