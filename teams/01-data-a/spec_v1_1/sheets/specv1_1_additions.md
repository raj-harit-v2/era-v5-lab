# Medicine sheet: Data A — consolidated spec v1.1 (contributors retained per rule)

Status: **DRAFT / CANDIDATE**. Consolidates the Spec v1.1 medicine sheets: Data A's [medicine_english.md](medicine_english.md), [medicine_math.md](medicine_math.md) and [medicine_sci.md](medicine_sci.md), and [medicine_indic.md](medicine_indic.md), which carries the Indic family's rule (Data B's). No rule is approved by this document. It holds the 24 medicines for the new diseases: 3 English, 8 math, 12 science and 1 Indic: diseases not in `diagnosis/DISEASES.md` that appear in 1% or more of the docs read in a domain (`NEW_DISEASES.md`). It adds to spec v1 (`../../spec_v1/sheets/specv1.md`) and does not repeat its 70 medicines. Arranged like `specv1.md` and the template [medicine_TEMPLATE.md](../../../../diagnosis/templates/medicine_TEMPLATE.md): each medicine keeps its disease, count and examples, words and Python, action, harm evidence and side effects.

## Scope, dispatch and executable contract

- **Families.** The new diseases are in three families:
  - **English:** en-nemotroncc and en-nemotroncc-synth. 200 docs were read, 50 each in mittalutkarsh/era-v5-lab#7, #8 and #9 and patilvijay23/era-v5-lab#36.
  - **Math:** math-finemath and math-megamath.
  - **Science:** sci-finepdfs.
  - **Indic:** ind-te-sangraha-v, from Data B's diagnosis labels (161 of 500 docs), not the Week 2 reading.

  Code has none at 1% or more: 200 docs were read, and every code row is a spec v1 miss.
- **Withdrawn:** a third English rule, `DA-D6-002` (appended Q&A), changed 32 of 326 gold docs and was withdrawn. Its ID is not reused, and it has no card here.
- **The Indic family's C6.** `DB-C6-001` is Data B's rule (oddjoker91, theschoolofai/era-v5-lab#177, listed for v1.1 in #216).
  - **Its card:** the last card here comes from `medicine_indic.md`. That sheet copies Data B's function unchanged and adds only the block's header lines and a `pack_id` check for ind-te-sangraha-v, the pack where the disease was found.
  - **Its harm test:** Data B's `teams/02-data-b/tools/harm_test_indic.py`, which adds the joiner and normal-form audits Indic text needs. So its results are on its card, not in the validation table below.
- **`pack_id`.** It is required, from trusted pack provenance. Every rule checks it against its `ORIGIN`, so a rule runs only on the packs where its disease was found. Math rules also check `lang_label`; English and science rules don't, as each runs on named packs only and sci-finepdfs holds more than one language. Missing or unknown pack IDs pass unchanged and are not eligible for release.
- **Python blocks.** Each fence is one independent rule module. Load it with `teams/01-data-a/harmtest/harm_test.py`, which isolates sheet blocks. Shared names (`medicine`, `_std`, helpers) differ between blocks, so they must not be joined into one namespace. All IDs are unique, and every code is a **proposed** new code (A7, A8, B6, C7, C8, C9, D6, D7). A new code needs an entry in `DISEASES.md` and in `CODE_ORDER` in `build_clean.py`.
- **Order.** v1.1 rules run after their family's spec v1 rules, because the readers found these diseases in text that spec v1 had cleaned. Within a family they run in medicine-section order, carrying each fixed text into the next rule and stopping on the first drop. A drop excludes the whole record and keeps audit provenance. A rule exception or timeout is ERROR, never keep or PASS.
- **Collation into `clean.py`.** Use `g1-specv1`'s `specv1.md` (theschoolofai/era-v5-lab#244), which cleaned the Week 2 sample. Its 24 code rules also check `pack_id` (Smita, 2 Nov); `main`'s don't, and the sample labels every code doc `lang_label = "code"`.

## Binding clash resolutions

| Clash | Resolution in this spec |
|---|---|
| Gold-control limit | As spec v1: `changed + dropped <= max(1, floor(gold_count / 100))`, per rule and for all of a family's rules in order, **per pack**. |
| One disease code in two or more families (A8, C7, C8, C9) | One rule per family, each with its own ID and pack guard. A8: `DA-A8-001` math, `DA-A8-002` science, `DA-A8-003` English. C7: `DA-C7-001`, `DA-C7-002` math; `DA-C7-003`, `DA-C7-004`, `DA-C7-005` science. C8: `DA-C8-001`, `DA-C8-002` math; `DA-C8-003`, `DA-C8-004`, `DA-C8-005` science. C9: `DA-C9-001`, `DA-C9-003` math; `DA-C9-002` science. |
| C6 is the Indic family's code | Template pages moved from C6 to C9 on 12 Nov (`DA-C9-003`, drafted as `DA-C6-001`), so every code means one disease for both teams. |
| Missing figures: drop in math, fix in science | Math `DA-C7-002` drops a problem that can't be done without its figure. Science `DA-C7-004` keeps the text and turns each empty image link into its caption, because a science text can still be read. |
| Merged table cells: drop in math, fix in science | Math `DA-C8-002` drops a doc with a flattened numeric row. Science `DA-C8-003` splits two numbers in one cell, the one case it can repair. |
| Ebook pages with `Page n/N` markers (`DA-C9-002`) and page-line removal (`DA-C8-005`) | `DA-C9-002` runs first and drops the page while its markers are still there; `DA-C8-005` only sees what is left. |
| Near-empty drop (`DA-C7-005`) and fixes that shorten a doc | Source order is kept: it runs after science sections 1–9 and before `DA-C7-004` and `DA-C8-005`. A doc that those two later fixes shorten below 250 characters is not dropped. |
| Facts the rewrite got wrong (D7) | No text signal marks a wrong fact, so `DA-D7-001` quarantines the 6 confirmed doc IDs, as spec v1 quarantines confirmed records (`DA-D1-001`, `DA-F1-006`). It finds no other cases, and its 0 gold harm proves little. Chosen by aneeshads, 13 Nov. |
| Appended Q&A in en-nemotroncc-synth (`DA-D6-002`) | Withdrawn: 32 of 326 gold docs end in ordinary, correct Q&A, and no text signal separates the reading docs. The 2 reading docs with wrong answers are in `DA-D7-001`. Whether appended Q&A is a disease is for the team to rule. |
| Order within a family | Source order, as measured by the harm runs: English sections 1–2, math sections 1–8, science sections 1–12. Science sections 7–12 were added after 1–6 and keep that place, so stage 10 rules 7–9 run after stage 30 rules 2–6. Re-ordering needs a new harm run. |
| Diseases readers marked new that are in `DISEASES.md` | No v1.1 rule: ligatures (A5), wrong glyphs (A6), HTML entities (B1), contents-page dot leaders (C1), questions joined on one page and two English documents joined (C4), keyword lists (C5), names with ages (F1). Drafts `DA-A5-101`, `DA-B1-101` and `DA-C1-101` were taken out on 12 Nov. |
| Gold contradictions | Gold docs that hold the disease their rule targets are recorded, not edited: finemath `2d328b828fa97706` (`DA-A8-001`) and `0f119a596e8b7f63` (`DA-C9-003`); sci `920855df51f37db8` (`DA-A7-001`) and `4b958ac1f45443b5`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd` (`DA-C7-004`); en-nemotroncc `056cc9bc44c927e2` (`DA-A8-003`); ind-te-sangraha-v `85644a4840025b6f` and `01418489e7410bdf` (`DB-C6-001`, a bare `..`). Proposed by aneeshads on 13 Nov, and **Vijay agreed**: they are marked as gold contradictions, left out of the count for those rules only, and re-read at the next gold refresh. The results below are given as measured, FAIL included, and without them. |

## Harm acceptance and evidence gaps

Acceptance follows `harm_test.py`'s gold-control policy: no errors, and at most `max(1, floor(1% of n))` affected gold docs per rule and per family in order, for each pack. That is 1 doc on finemath (86), megamath (26), en-dclm (62), en-fineweb-edu (158) and en-nemotroncc (129); 2 on sci-finepdfs (202); and 3 on en-nemotroncc-synth (326). A gold doc counts if any character changes or it is dropped. A failed candidate is kept for review and blocks release; it is not silently disabled to improve the numbers.

- **Alone:** 22 of the 24 medicines pass. Two fail, and every gold doc they touch is a gold contradiction:
  - `DA-C7-004` fails on sci-finepdfs at 3/202.
  - `DB-C6-001` fails on ind-te-sangraha-v at 2/80.
- **Indic, on Data B's `harm_test_indic.py`:**
  - **ind-te-sangraha-v (13 Nov), the 80-doc gold:** `DB-C6-001` changed 2/80, FAIL. Both docs have a bare `..`, which the pack's reader labelled C6 in other docs, so they are gold contradictions. Without them it is 0/78, PASS.
  - **The sangraha-s packs (13 Nov):** Data B's function changed 0 gold docs on hi, kn and te, PASS.
- **In order:**
  - **Pass:** megamath, and all four English packs (en-nemotroncc 1/129, a gold contradiction).
  - **finemath:** fails at 2/86, both gold contradictions.
  - **sci-finepdfs:** fails at 5/202: 4 gold contradictions, and one false positive within the rule's own limit (`b6fd81dbf90b0d17`, `DA-C7-005`).
- **With the gold contradictions left out** (Vijay agreed): finemath passes at 0/84, sci-finepdfs at 1/198, and ind-te-sangraha-v at 0/78.
- **Gold docs read:** every gold doc a v1.1 rule touched has been read.
  - `DA-A7-003` and `DA-C8-005` harmed 4 docs in their first versions and were narrowed on 13 Nov (see their cards).
  - `DA-D6-002` was withdrawn (above).
- **Recall is separate from harm.** Each card counts the readers' docs it changes or drops, on the cleaned sample the readers read (`scripts/reading_recall.py`). A low harm count does not show recall or that a fix is right.
- **Examples.** Cards give examples by doc_id with short quotes. Exact source characters are withheld: pack text stays out of the public repo, and the cleaned text behind each example is kept outside it. Aditeya's, pyru's and Satyanarayana's reading rows are AI-suggested, and kunal's are AI-suggested with each checked by him. Utkarsh's and aneesha's are manual. A person's check of the examples is still a release gate.

Source code stays CANDIDATE after a measured pass. Semantic side effects, reviewer approval, the proposed codes and the re-read of the gold contradictions at the next gold refresh remain release gates.

## Source snapshots

| Source | Code sha256 (python blocks, as `harm_test.py` hashes them) | Harm reports |
|---|---|---|
| [medicine_english.md](medicine_english.md) | `882209876997f090dacc2ad2ee71f478be07641ae4b65a3ed227d0c8e716e2e6` | `en-dclm_harm.json`, `en-fineweb-edu_harm.json`, `en-nemotroncc_harm.json`, `en-nemotroncc-synth_harm.json` |
| [medicine_math.md](medicine_math.md) | `9bcc84b267a7ad53ba9da138823bb55ce48d35e975ddd2fdc9e4ca6ec4665ff6` | `math-finemath_harm.json`, `math-megamath_harm.json` |
| [medicine_sci.md](medicine_sci.md) | `ed7d1cc0a0b4e2620c7e206ab1fd40a172b71442209524461ead92754c00b0cd` | `sci-finepdfs_harm.json` |
| [medicine_indic.md](medicine_indic.md) | `4cbb55c02cde32dbff07ef2a4c797c7394548e0c9642bf7f0e9cbaf5bba5a09f` | `indic_sangraha-v_harm.md` and `indic_sangraha-s_harm.md` (Data B's `harm_test_indic.py`, run on Data B's function, which the sheet copies unchanged) |

## Identity mapping

| Medicine | Family | Disease | Source | Source identity | Consolidated identity |
|---|---|---|---|---|---|
| 1 | english | A8 | [medicine_english.md](medicine_english.md) section 1 | `DA-A8-003` | `DA-A8-003` |
| 2 | english | D7 | [medicine_english.md](medicine_english.md) section 2 | `DA-D7-001` | `DA-D7-001` |
| 3 | english | A8 | [medicine_english.md](medicine_english.md) section 3 | `DA-A8-004` | `DA-A8-004` |
| 4 | math | A8 | [medicine_math.md](medicine_math.md) section 1 | `DA-A8-001` | `DA-A8-001` |
| 5 | math | C9 | [medicine_math.md](medicine_math.md) section 2 | `DA-C9-003` (drafted as `DA-C6-001`) | `DA-C9-003` |
| 6 | math | C9 | [medicine_math.md](medicine_math.md) section 3 | `DA-C9-001` | `DA-C9-001` |
| 7 | math | D6 | [medicine_math.md](medicine_math.md) section 4 | `DA-D6-001` | `DA-D6-001` |
| 8 | math | C7 | [medicine_math.md](medicine_math.md) section 5 | `DA-C7-001` | `DA-C7-001` |
| 9 | math | C7 | [medicine_math.md](medicine_math.md) section 6 | `DA-C7-002` | `DA-C7-002` |
| 10 | math | C8 | [medicine_math.md](medicine_math.md) section 7 | `DA-C8-001` | `DA-C8-001` |
| 11 | math | C8 | [medicine_math.md](medicine_math.md) section 8 | `DA-C8-002` | `DA-C8-002` |
| 12 | sci | A7 | [medicine_sci.md](medicine_sci.md) section 1 | `DA-A7-001` (drafted as `DA-A7-101`) | `DA-A7-001` |
| 13 | sci | C9 | [medicine_sci.md](medicine_sci.md) section 2 | `DA-C9-002` | `DA-C9-002` |
| 14 | sci | B6 | [medicine_sci.md](medicine_sci.md) section 3 | `DA-B6-001` | `DA-B6-001` |
| 15 | sci | C7 | [medicine_sci.md](medicine_sci.md) section 4 | `DA-C7-003` | `DA-C7-003` |
| 16 | sci | C8 | [medicine_sci.md](medicine_sci.md) section 5 | `DA-C8-004` | `DA-C8-004` |
| 17 | sci | C8 | [medicine_sci.md](medicine_sci.md) section 6 | `DA-C8-003` | `DA-C8-003` |
| 18 | sci | A7 | [medicine_sci.md](medicine_sci.md) section 7 | `DA-A7-002` | `DA-A7-002` |
| 19 | sci | A7 | [medicine_sci.md](medicine_sci.md) section 8 | `DA-A7-003` | `DA-A7-003` |
| 20 | sci | A8 | [medicine_sci.md](medicine_sci.md) section 9 | `DA-A8-002` | `DA-A8-002` |
| 21 | sci | C7 | [medicine_sci.md](medicine_sci.md) section 10 | `DA-C7-005` | `DA-C7-005` |
| 22 | sci | C7 | [medicine_sci.md](medicine_sci.md) section 11 | `DA-C7-004` | `DA-C7-004` |
| 23 | sci | C8 | [medicine_sci.md](medicine_sci.md) section 12 | `DA-C8-005` | `DA-C8-005` |
| 24 | indic | C6 | [medicine_indic.md](medicine_indic.md) section 1 | `DB-C6-001` | `DB-C6-001` |

## Fresh validation

<!-- VALIDATION -->

Harm runs with the team's `teams/01-data-a/harmtest/harm_test.py --rule all` (it was `tools/harm_test.py` until theschoolofai/era-v5-lab#244 moved it; the code is byte-identical), run unchanged, on the Week 1 pack files and the Data A gold sets: each rule alone, then all of a sheet's rules in order. These are the runs of the two source sheets. The python blocks here are the same text, in the same order, so the results carry over; the build checks that. Reports contain IDs and digests only. Whole-pack counts (all docs, not only gold) were not run for v1.1.

| Pack | Gold n | Rules failing alone | All in order: changed / dropped | Result | Gold docs touched in order |
|---|---:|---|---:|---|---|
| en-dclm | 62 | none | 0 / 0 | **PASS** | none |
| en-fineweb-edu | 158 | none | 0 / 0 | **PASS** | none |
| en-nemotroncc | 129 | none | 2 / 0 | **FAIL** | `056cc9bc44c927e2`, `fd16036899796ca4` |
| en-nemotroncc-synth | 326 | none | 0 / 0 | **PASS** | none |
| math-finemath | 86 | none | 1 / 1 | **FAIL** | `2d328b828fa97706`, `0f119a596e8b7f63` (dropped) |
| math-megamath | 26 | none | 0 / 0 | **PASS** | none |
| sci-finepdfs | 202 | `DA-C7-004` (3/202) | 4 / 1 | **FAIL** | `4b958ac1f45443b5`, `920855df51f37db8`, `d0a0a41263e845f5`, `eb6ad9726f2d7ddd`, `b6fd81dbf90b0d17` (dropped) |

Reproduce from the repository root, once per pack (`W1` is the folder that holds the Week 1 packs):

```bash
python3 -I teams/01-data-a/harmtest/harm_test.py --pack <W1>/<pack>.parquet --gold teams/01-data-a/gold/<pack>_gold.csv \
  --rules teams/01-data-a/spec_v1_1/sheets/medicine_<domain>.md --rule all \
  --report teams/01-data-a/spec_v1_1/results/sheets/<pack>_harm.json
```

The same command with `--rules teams/01-data-a/spec_v1_1/sheets/specv1_1_additions.md` runs this sheet: the other families' rules keep every doc of the pack.

**Indic (`DB-C6-001`).** Its harm test is Data B's, run with `teams/02-data-b/tools/harm_test_indic.py --medicine <sheet> --pack <pack>.parquet --gold-dir teams/02-data-b/gold --rule all`.

| pack | gold docs (limit) | changed / dropped | result | run |
|---|---:|---:|---|---|
| ind-te-sangraha-v | 80 (1) | 2 / 0 | **FAIL**; 0/78 PASS without the 2 gold contradictions (`85644a4840025b6f`, `01418489e7410bdf`) | aneeshads, 13 Nov, on `ind-te-sangraha-v.parquet` (the 500 docs that were read); report `indic_sangraha-v_harm.md` |
| ind-te-sangraha-v | 18 (1), the old gold | 1 / 0 | **PASS** | Data B, 9 Nov; superseded by the 80-doc run |
| ind-hi-sangraha-s | 24 (1) | 0 / 0 | **PASS** | aneeshads, 13 Nov, on Data B's function, which has no pack check |
| ind-kn-sangraha-s | 22 (1) | 0 / 0 | **PASS** | the same run |
| ind-te-sangraha-s | 24 (1) | 0 / 0 | **PASS** | the same run |
| ind-ta-sangraha-s | none | - | not testable | the same run |

## Medicine 1 — english / A8 / `DA-A8-003`

**Consolidation:** Source [medicine_english.md](medicine_english.md), section 1 (A8 words run together: no space after a full stop; fix; stage 10); identity `DA-A8-003`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-spaces, 2 docs, aneesha (en-nemotroncc). Examples:
   - `2feb05980d7d894a`: `as you choose.Compose a 500-750-word paper`
   - `502ee3da08920d31`: `Every once in awhile`

   Math has 13 more and science 3, each with its own rule: `DA-A8-001` and `DA-A8-002`.

<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: off (not in `ORIGIN`); en-fineweb-edu: off (not in `ORIGIN`); en-nemotroncc: 1 changed / 0 dropped of 129 (PASS); en-nemotroncc-synth: off (not in `ORIGIN`).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** put the space back where a sentence ends with a lowercase word and the next one starts with a capital, with no space between them: `choose.Compose` becomes `choose. Compose`. It leaves these alone:
   - **URLs, file names and abbreviations:** the word after the dot must be followed by a space, punctuation or the end of the text (`www.Google.com` stays), and the word before it must start a token (`e.g.The`, `Mr.Smith` and `Node.Js` stay);
   - **code:** lines that look like code, and lines inside code fences.

   `awhile` is an English word, so it is left as it is.

```python
RULE_ID = "DA-A8-003"
CODE = "A8"  # proposed new code: words run together (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "en-nemotroncc"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "en-nemotroncc"  # pack whose reading found it (aneesha, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A8E_GLUED = re.compile(r"(?<![\w./@:\-])([a-z]{2,})\.([A-Z][a-z]+)(?=[\s,;:!?)\"']|$)")
A8E_CODE = re.compile(r"[{};]|==|=>|->|::|//|\bdef |\bfunction\b|\breturn\b")


def medicine_a8e(text):
    if not A8E_GLUED.search(text):  # speed (14 Nov): no glued pair anywhere, so the line loop would change nothing
        return text
    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if fence or A8E_CODE.search(line):
            out.append(line)
            continue
        out.append(A8E_GLUED.sub(lambda m: m.group(1) + ". " + m.group(2), line))
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a8e(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** en-nemotroncc. **Reading docs it treats:** 1 of 2 (`2feb05980d7d894a`). `awhile` is kept on purpose.
4. **Harm test:** en-nemotroncc 0.78% (1/129) PASS. The gold doc it changes, `056cc9bc44c927e2`, has the disease itself (`tantrum.To`).
5. **Side effects:**
   - A name written with a dot and a capital, followed by a space (`site.Com today`), gets a space.
   - Words run together with no dot (`twowords`) are missed, because they need a word list.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: aneesha's en-nemotroncc reading, mittalutkarsh/era-v5-lab#9.

---

## Medicine 2 — english / D7 / `DA-D7-001`

**Consolidation:** Source [medicine_english.md](medicine_english.md), section 2 (D7 facts the rewrite got wrong; drop; stage 30); identity `DA-D7-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-factual-error, 4 docs, kunal (en-nemotroncc-synth). The synthetic rewrite brought in an error that can be checked. Examples:
   - `0f7b90400c1362df`: Victoria called "the Virgin Queen" (that is Elizabeth I)
   - `0f7240ba1fdd3411`: "the battles of Artemisia and Salamis" (Artemisium)
   - `52bd1da881ee0592`: "In Exodus 9" (Joshua 9)
   - `f2a8b2cc25bb5c7a`: a camera comparison reversed

   2 more docs from kunal's NEW-appended-qa have a wrong answer in their appended Q&A:
   - `5aeafd200220c080`: the answer names the Duke of Lauderdale, whom the passage doesn't mention
   - `c3d88009d8a459e9`: "The Institute" for the Albert Shanker Institute

   **Proposed new code D7:** none of D1–D5 covers wrong facts; D4 is about translation.

<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: off (not in `ORIGIN`); en-fineweb-edu: off (not in `ORIGIN`); en-nemotroncc: off (not in `ORIGIN`); en-nemotroncc-synth: 0 changed / 0 dropped of 326 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** quarantine the 6 confirmed docs by doc_id, the way spec v1 quarantines confirmed records (`DA-D1-001`, `DA-F1-006`). Nothing in the text marks a wrong fact, so a rule can't find other cases. That needs a fact check or a model. **Chosen by aneeshads, 13 Nov.**

```python
RULE_ID = "DA-D7-001"
CODE = "D7"  # proposed new code: facts the rewrite got wrong (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "en-nemotroncc-synth"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "en-nemotroncc-synth"  # pack whose reading found it (kunal, Week 2 reading audit)
AUTHOR = "aneeshads"

D7_CONFIRMED = frozenset({
    "0f7b90400c1362df", "0f7240ba1fdd3411", "52bd1da881ee0592", "f2a8b2cc25bb5c7a",  # NEW-factual-error
    "5aeafd200220c080", "c3d88009d8a459e9",  # a wrong answer in an appended Q&A (NEW-appended-qa)
})


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return ("drop", doc["text"]) if doc.get("doc_id") in D7_CONFIRMED else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** en-nemotroncc-synth. **Reading docs it treats:** all 4 NEW-factual-error docs and the 2 wrong-answer docs, all dropped.
4. **Harm test:** en-nemotroncc-synth 0.00% (0/326) PASS. The pass proves little: the rule acts only on the 6 listed docs, and none is a gold doc.
5. **Side effects:**
   - Every other doc with a wrong fact is missed; the rule finds only what a reader confirmed.
   - The rest of each of the 6 docs, which may be fine, is dropped with them.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: kunal's en-nemotroncc-synth reading, mittalutkarsh/era-v5-lab#8.

---

## Medicine 3 — english / A8 / `DA-A8-004`

**Consolidation:** Source [medicine_english.md](medicine_english.md), section 3 (A8 words run together: no full stop; fix; stage 10); identity `DA-A8-004`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-spaces where there is no full stop between the two words, so `DA-A8-003` can't see it. Found by HariniJasti in the Week 1 en-nemotroncc diagnosis (500 docs, PR #79) and raised on #435. Examples:
   - `43c65ec608a359bf`: `import your fileEdit with ease`
   - `6555a5194920ffbb`: `your first adjustmentHere are`
   - `cecff9e9578553e4`: `relativelyThree teenage girls`
   - `3605b6a14d0ee8d8`: `the topographyZoom into`
   - `566402921614f959`: `Admission is freeJohn McCrae`
   - `fd16036899796ca4`: `saidSanaz` (a gold doc, see the harm test; the rest of the name is withheld)

<!-- CARD EVIDENCE -->
**Current gold harm:** en-dclm: off (not in `ORIGIN`); en-fineweb-edu: off (not in `ORIGIN`); en-nemotroncc: 1 changed / 0 dropped of 129 (PASS); en-nemotroncc-synth: off (not in `ORIGIN`).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** put a space between a lowercase word of 3 or more letters and a capitalised word glued to it, so `fileEdit` becomes `file Edit`. The glued token must stand alone: before it a space, the start of the line, or an opening quote or bracket; after it a space, punctuation or the end of the line. It leaves these alone:
   - **code and markup:** a line with `{` or `}`, a `;` at its end, `==`, `=>`, `->`, `::`, `()`, ` = `, `$this`, a tag (`<div>`) or a `// ` comment, and a line inside a code fence. So `validateString();` and `$this->assertTrue` stay;
   - **camelCase with more humps:** `getMockBuilder` stays, because the token must end after the second word;
   - **one- and two-letter prefixes:** `iPhone`, `eBay`, `macOS` and `jQuery` stay;
   - **product names on a short list** (`A8F_KEEP`, whole tokens): `pdfFiller`, `webAssembly`, `appStore`, `youTube`.

   Lowercase words glued to lowercase words (`creamthe`, `Whilewe`) are not caught: they need a word list (open for v1.2).

   **Changed in review (aneeshads, 14 Nov, from HariniJasti's patilvijay23/era-v5-lab#41):**
   - **The code test is narrower.** `<`, `>`, `$` and a `;` inside a line also occur in prose (prices, lists), so they no longer mark a line as code. On the 500 docs this wins back 8 glued pairs (`devicesTo`, `modelsWhat`, `potentialTourism` …), and it changes no other gold doc.
   - **`A8F_KEEP` is a list of whole tokens, not first words.** A first word such as `you` also kept real glues (`thank youFor`).
   - **A quick check first** (speed rule): a doc with no glued token at all is returned as it is. It takes the rule from 0.20 s to 0.12 s per 500 en-nemotroncc docs (`scripts/time_rules.py`, in the `clean.py` PR; best of 3), with the same output.

   **Changed on 15 Nov, from HariniJasti's two follow-up suggestions on patilvijay23/era-v5-lab#41:**
   - **The code test is narrower again.** `return`, `function`, `def`, a bare `=` and a `//` inside a URL no longer mark a line as code. A line now counts as code if it has braces, a `;` at its end, `==`, `=>`, `->`, `::`, `()`, ` = `, `$this`, a tag, or a `// ` comment. On the 500 docs this splits 66 glued pairs in 29 docs, not 55 in 28, and loses none. The 11 it adds are `civilizationThe` and `influencesEgyptian` (one doc), `newCage`, and `pdfFile` and `pdfDownload` 4 times each (one doc of download links). The gold doc changed is the same one.
   - **A cheaper quick check** (`A8F_QUICK`, `[a-z]{3}[A-Z][a-z]`) runs on the whole doc, then on each line before the code test. Output is identical on all 500 docs. The rule goes from 0.123 s to 0.085 s per 500 en-nemotroncc docs (4,079 to 5,911 docs/s; Apple M4, one core, best of 5).
   - The code test is written from HariniJasti's description of it; her own pattern wasn't posted.

```python
RULE_ID = "DA-A8-004"
CODE = "A8"  # proposed new code: words run together (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "en-nemotroncc"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "en-nemotroncc"  # pack whose reading found it (HariniJasti, Week 1 diagnosis, PR #79)
AUTHOR = "HariniJasti"
import re

A8F_GLUED = re.compile(r"(?:(?<=^)|(?<=[\s\"“(]))([a-z]{3,})([A-Z][a-z]{1,})(?=[\s,;:!?\"”]|\.(?:\s|$)|$)", re.M)
# speed: a doc, or a line, without this cannot hold a glued token, so it is skipped before the slower tests
A8F_QUICK = re.compile(r"[a-z]{3}[A-Z][a-z]")
# a code line: braces, a ";" at the end, ==, =>, ->, ::, (), " = ", $this, a tag or a "// " comment.
# "return", "function", a bare "=" and the "//" of a URL occur in prose, so they no longer count (15 Nov)
A8F_CODE = re.compile(r"[{}]|;[ \t]*$|==|=>|->|::|\(\)| = |\$this|</?[A-Za-z][^<>]*>|(?:^|\s)//\s")
# whole tokens, not first words: a first word such as "you" would also keep real glues ("thank youFor")
A8F_KEEP = frozenset({"youTube", "pdfFiller", "webAssembly", "appStore", "airPods", "airBnb", "dotNet", "macBook"})


def medicine_a8f(text):
    if not A8F_QUICK.search(text) or not A8F_GLUED.search(text):  # speed: no glued token anywhere, so no line changes
        return text
    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if fence or not A8F_QUICK.search(line) or A8F_CODE.search(line):
            out.append(line)
            continue
        out.append(A8F_GLUED.sub(
            lambda m: m.group(0) if m.group(0) in A8F_KEEP else m.group(1) + " " + m.group(2), line))
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a8f(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** en-nemotroncc.
   - **Diagnosis docs it treats:** 29 of the 500 Week 1 diagnosis docs, with 66 glued pairs. HariniJasti read the 47 pairs her first version split: all are words run together, and none is a name or code. The 8 pairs the first narrower code test added (14 Nov) and the 11 the second one adds (15 Nov) were read by aneeshads, as a first pass: all are glues too, though `pdfFile` and `pdfDownload` sit in one doc of download links.
   - **Reading docs it treats:** not measured, because the cleaned reading sample of en-nemotroncc was not rerun. That makes this column unlike the other rows', which count reading docs (`scripts/reading_recall.py`).
4. **Harm test:** en-nemotroncc 0.78% (1/129) PASS on its own. The gold doc it changes, `fd16036899796ca4`, has the disease itself (`saidSanaz`: a quote glued to the speaker's name, withheld here), so it is a gold contradiction, as `056cc9bc44c927e2` is for `DA-A8-003`.
   - **All in order:** 2/129 with `DA-A8-003`, FAIL against a limit of 1. Both changed gold docs hold the disease, and Vijay agreed to marking gold contradictions, so it is **0/127 PASS** without them. They are to be re-read at the next gold refresh.
5. **Side effects:**
   - A brand written with a lowercase prefix of 3+ letters and not on `A8F_KEEP` gets a space (`fooBar`-style names in prose).
   - **camelCase names in prose** are split when the line has no code sign (`setTimeout`, `forEach`, `useState`, `linkedIn`). None is in this pack.
   - A German or Dutch compound glued to a capitalised noun is split (`gesuchtJugendherbergen` on this pack, which is itself a glue).
   - **Lines with code signs:** a glue on such a line is still missed. The narrower test of 15 Nov leaves fewer of these: the 11 pairs missed on 14 Nov are now split.
   - **Prose that looks like code:** a prose line with ` = ` (a sum such as `x = 2`) or an empty `()` is still treated as code, and its glues are missed.
   - **Lowercase-to-lowercase glues** are missed (see above).
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Author: HariniJasti, from her en-nemotroncc diagnosis (theschoolofai/era-v5-lab#79), raised on #435 and proposed in patilvijay23/era-v5-lab#41. Review changes by aneeshads, 14 Nov.

---

## Medicine 4 — math / A8 / `DA-A8-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 1 (A8 words run together; fix; stage 10); identity `DA-A8-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-spaces, 13 docs: pyru 5 (finemath) and Satyanarayana 8 (megamath). Examples: `03aeffcf72c72418`, `167ef4a340862a0e`, `1ab888d9366a43fd`. A line break or space was lost, so two words run together, as in `HydrogenWhen`, `ProblemsThe`, `minQuestions`.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 1 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:**
   - **What it fixes.** It puts a space back where a lowercase word of 3+ letters runs into a capitalised word that starts a sentence or a heading (`The`, `When`, `Questions`, `Solution`, `Example`…), or into that word after a full stop (`word.The`).
   - **Why only those words.** A capitalised word that opens a sentence is never part of a brand or code name, so `JavaScript`, `WordPress`, `LinkedIn` and `maxValue` stay as they are.
   - **What it leaves alone.** Lines that look like code, lines inside code fences, and words with digits or underscores.
   - **What it can't fix.** Lowercase pairs such as `twoapproaches` need a dictionary, so they are left.

```python
RULE_ID = "DA-A8-001"
CODE = "A8"  # proposed new code: words run together (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

# capitalised words that open a sentence or a heading; a word glued to one of these lost its space
A8_STARTERS = frozenset((
    "The This That These Those There Then Thus Therefore Hence When Where What Which Why How Who It If We You Your Our "
    "For From Let Find Given Solve Show Prove Step Steps Note Example Examples Exercise Exercises Question Questions "
    "Problem Problems Solution Solutions Answer Answers Continue Click Each Every All Here Now First Next Finally "
    "Lesson Chapter Section Table Figure Write Calculate Determine Explain Consider Suppose Assume").split())
A8_GLUED = re.compile(r"(?<![A-Za-z0-9_.])([A-Z]?[a-z]{3,})(\.?)([A-Z][a-z]+)(?![A-Za-z0-9_])")
A8_CODE = re.compile(r"[{};]|==|=>|->|::|//|\bdef |\bfunction\b|\breturn\b")


def _a8_join(m):
    left, dot, right = m.groups()
    if right not in A8_STARTERS:
        return m.group()
    return left + dot + " " + right


def medicine_a8(text):
    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        if fence or A8_CODE.search(line) or line.lstrip().startswith("```"):
            out.append(line)
            continue
        out.append(A8_GLUED.sub(_a8_join, line))
    return "\n".join(out)


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a8(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath. **Reading docs it treats:** 5 of 13, all fixed.
4. **Harm test:** finemath 1.16% (1/86) PASS; megamath 0.00% (0/26) PASS. The finemath gold doc it changes, `2d328b828fa97706`, has a real missing space (`fieldtrip.Write`).
5. **Side effects:**
   - A name that really is glued to a sentence word, such as a product called `SmartThe`, would be split.
   - It misses joins into words not on the list (`ZakharovShabat`, `instead.Cf.`) and all lowercase joins.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

---

## Medicine 5 — math / C9 / `DA-C9-003`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 2 (C9 page made from a template for one value; drop; stage 30); identity `DA-C9-003`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-template-pages, 9 docs: pyru 8 and Satyanarayana 1. Examples:
   - `28f56e454b2ade39`: number facts for 36871
   - `32b1f031d8c464e4`: 15 percent off \$41
   - `647d9713533c5664`: the number 6186

   These are calculator, unit-converter and number-fact pages that a site makes for each value.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 1 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop the doc when any one of these holds.
   - **(a)** It has a sentence that only unit-converter sites write ("Feel free to use our online unit conversion calculator").
   - **(b)** Its Markdown headings hold at least 2 different template phrases, and at least one of them is used only by such sites ("as geometric shapes", "Cryptographic Hash Functions", "Latest conversions of", "converter", "How to write / spell"…). Weak phrases that a real lesson may use too, such as "Prime factorization of", "Divisors of" and "Conversion table", count only next to one of these.
   - **(c)** One value appears in at least 3 headings and in at least a quarter of all headings. A value is a number of 3 or more digits, a decimal, or a dollar amount; years 1900–2099 don't count.

```python
RULE_ID = "DA-C9-003"
CODE = "C9"  # proposed new code: pages made for search traffic; here, a page made from a template for one value (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose reading found it (pyru and Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re
from collections import Counter

C9T_SENTENCE = re.compile(r"feel free to use our online unit conversion calculator", re.I)
C9T_HEADING = re.compile(r"^#{1,6}[ \t]+(.+)$", re.M)
# headings that only calculator and number-fact sites use
C9T_STRONG = re.compile(r"as geometric shapes|cryptographic hash functions|other arithmetic functions|basic calculations \(n ="
                       r"|alternative conversion|\bconverter\b|how to write / spell|decomposition of the number"
                       r"|mathematical representations and links|latest conversions of|roman system of writing numerals", re.I)
# headings a real lesson may use too: they count only next to a strong one
C9T_WEAK = re.compile(r"prime factori[sz]ation of|divisors of|divisibility of|classification of|base conversion"
                     r"|conversion table|percent off|approximate result|mathematical properties of", re.I)
C9T_NUMBER = re.compile(r"(?<![\w.])(\d{3,}(?:\.\d+)?|\d+\.\d+)(?![\w.])")
C9T_DOLLARS = re.compile(r"\\?\$(\d+(?:\.\d+)?)")
C9T_YEAR = re.compile(r"(?:19|20)\d\d")


def medicine_c9t(text):
    if C9T_SENTENCE.search(text):
        return True
    headings = C9T_HEADING.findall(text)
    if not headings:
        return False
    strong = {m.group().lower() for h in headings for m in C9T_STRONG.finditer(h)}
    weak = {m.group().lower() for h in headings for m in C9T_WEAK.finditer(h)}
    if strong and len(strong) + len(weak) >= 2:
        return True
    values = Counter()
    for h in headings:
        found = set(C9T_NUMBER.findall(h)) | {"$" + v for v in C9T_DOLLARS.findall(h)}
        values.update(v for v in found if not C9T_YEAR.fullmatch(v))
    if values:
        _, n = values.most_common(1)[0]
        if n >= 3 and 4 * n >= len(headings):
            return True
    return False


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c9t(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 8 of 9, all dropped. It misses `ec4ea0009df33e1a`.
4. **Harm test:** finemath 1.16% (1/86) PASS, at the limit; megamath 0.00% (0/26) PASS. The finemath gold doc it drops, `0f119a596e8b7f63`, is itself a converter template page. That gold contradiction is noted under the table at the top of this sheet.
5. **Side effects:**
   - A real lesson whose headings name one 3-digit number three times would be dropped ("Is 1001 prime?", "Factors of 1001", "Multiples of 1001").
   - So would a lesson that pairs a strong phrase with a weak one, such as a "converter" heading next to "Conversion table".
   - It misses template pages that have none of the Markdown headings it knows. In the reading, that is `ec4ea0009df33e1a`, the Bohr-model page of one element.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350). It was drafted as `DA-C6-101`, then `DA-C6-001`. On 12 Nov it moved to C9, beside SEO filler, because C6 is the Indic family's code. Both are pages made for search traffic.

---

## Medicine 6 — math / C9 / `DA-C9-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 3 (C9 SEO filler; fix + drop; stage 30); identity `DA-C9-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-seo-filler, 15 docs: pyru 10 and Satyanarayana 5. Examples: `053c7e6dfbdb4e46`, `085f9f7987b7cf56`, `0e2b9cc0beb5fb11`. These are pages written to rank in search, not to teach: tutoring and homework-app sales pages, exam-tips filler, route-distance pages and spun "ebook" pages.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:**
   - **Drop** a doc that has a sentence only these pages write. The list covers the tutoring sales lines ("Find your perfect private math tutor", "is the world's leading network of private tutors", "Find an … Tutor" headings, "367 math teachers in …"), the homework-app lines ("App that will do your homework", "We solve all types of math problems"), the 6ya help line, the exam-shortcut filler, a "Road distance" heading, and the ebook spinner ("If you ally dependence such a referred …", "You may not be perplexed to enjoy …").
   - **Fix:** remove the "You are watching: …" line that copying sites add to an article. The rest of that article stays.

```python
RULE_ID = "DA-C9-001"
CODE = "C9"  # proposed new code: SEO filler (NEW_DISEASES.md)
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

# sentences that only SEO landing pages write: tutoring and homework-app sales, the 6ya help line, exam filler,
# route-distance pages and the "ebook" spinner
C9_DROP = re.compile("|".join((
    r"find your perfect (?:private )?(?:math |maths )?tutor",
    r"is the world'?s leading network of private tutors",
    r"^#*[ \t]*find an? [\w .'-]{2,40} tutor\b",
    r"\b\d+ (?:math|maths) (?:teachers|tutors) in\b",
    r"\bapp that will (?:do|solve) your (?:math |maths )?homework",
    r"we solve all types of math problems",
    r"\ba 6ya expert can help you",
    r"shortcut tricks are very important thing to know for your exams",
    r"^#*[ \t]*road distance\b",
    r"if you ally (?:dependence|need|obsession|craving|habit) such a referred",
    r"you may not be perplexed to enjoy",
)), re.I | re.M)
C9_INJECTED = re.compile(r"^[ \t]*you are watching:[^\n]*(?:\n|$)", re.I | re.M)
# Speed (14 Nov): every C9_DROP sentence holds one of these, and C9_INJECTED holds "you are watch". casefold() maps every
# character re.I matches to them (each is cut before any "i", which re.I also matches as a dotless "ı" that casefold()
# keeps), so a doc without them can't match, and the 11-way case-insensitive search is skipped.
C9_NEEDS = ("tutor", "teachers", "homework", "math problems", "6ya", "shortcut tr", "road d", "such a referred",
            "perplexed to enjoy")


def medicine_c9(text):
    low = text.casefold()
    if any(k in low for k in C9_NEEDS) and C9_DROP.search(text):
        return True
    if "you are watch" not in low:
        return text
    return C9_INJECTED.sub("", text)


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c9(doc["text"]), doc["text"])
```

3. **Action:** fix + drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 8 of 15 (7 dropped, 1 fixed).
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A real lesson that quotes one of these sales lines would be dropped.
   - SEO pages that don't use one of the listed sentences are missed, such as worksheet pages and question-heading pages.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

---

## Medicine 7 — math / D6 / `DA-D6-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 4 (D6 machine-written text; fix + drop; stage 30); identity `DA-D6-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-ai-generated-text, 8 docs, pyru (finemath), 3 of them marked "unsure". Examples: `10d547035dd610e2`, `36c3e8b4b4457083`, `8f1f8a9c194e88f2`. There are two kinds:
   - text a forum adds to a thread: an "In summary, the conversation discusses …" line, and a numbered FAQ at the end;
   - whole machine-written SEO articles.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: off (not in `ORIGIN`).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:**
   - **Fix (forum pages).** When a doc has the forum's "In summary, the conversation/discussion/thread …" line, remove that line. Also remove the numbered FAQ the forum adds: 4 or more questions numbered `1.`, `2.`, `3.`… in order, at most 8 lines apart, each ending in `?`. The block ends after the last question's answer, or at the next `•` navigation line or heading. The users' posts stay.
   - **Drop (machine-written articles).** Drop a doc that shows 2 or more of these signs:
     - FAQ headings (`FAQ 1:` or "Frequently Asked Questions")
     - a "Conclusion" heading
     - 3 or more headings that start "Introduction to", "Understanding" or "Benefits of"
     - a sentence starting "In summary," or "In conclusion,"

```python
RULE_ID = "DA-D6-001"
CODE = "D6"  # proposed new code: machine-written text (NEW_DISEASES.md)
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on: the disease was found in finemath only
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose reading found it (pyru, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

D6_FORUM_SUMMARY = re.compile(r"^[ \t]*In summary, the (?:conversation|discussion|thread)\b[^\n]*(?:\n|$)", re.M)
D6_QUESTION = re.compile(r"^[ \t]*(\d{1,2})\.[ \t]+[^\n]{5,200}\?[ \t]*$")
D6_NAV = ("\u2022", "#")  # a forum navigation bullet or a heading ends the FAQ
D6_GAP = 8  # questions of one FAQ are at most this many lines apart
D6_FAQ_HEAD = re.compile(r"^#{1,6}[ \t]*(?:FAQ[ \t]*\d+[ \t]*:|Frequently Asked Questions)", re.M | re.I)
D6_CONCLUSION = re.compile(r"^#{1,6}[ \t]*(?:In )?Conclusion[ \t]*:?[ \t]*$", re.M | re.I)
D6_ARTICLE_HEAD = re.compile(r"^#{1,6}[ \t]*(?:Introduction to|Understanding|Benefits of)\b", re.M)
D6_WRAP_UP = re.compile(r"(?:^|[.!?][ \t]+)In (?:summary|conclusion), [a-z]", re.M)


def _d6_faq(lines):
    """(start, end) of a numbered FAQ of 4+ questions in order, close together, each followed by its answer, or None."""
    for i, line in enumerate(lines):
        m = D6_QUESTION.match(line)
        if not m or m.group(1) != "1":
            continue
        want, last, j = 2, i, i + 1
        while j < len(lines) and j - last <= D6_GAP and not lines[j].strip().startswith(D6_NAV):
            m = D6_QUESTION.match(lines[j])
            if m and int(m.group(1)) == want:
                want, last = want + 1, j
            j += 1
        if want - 1 < 4:
            continue
        end = last + 1
        while end < len(lines) and not lines[end].strip():
            end += 1  # the blank lines after the last question
        while end < len(lines) and lines[end].strip() and not lines[end].strip().startswith(D6_NAV):
            end += 1  # its answer
        return i, end
    return None


def medicine_d6(text):
    if D6_FORUM_SUMMARY.search(text):
        text = D6_FORUM_SUMMARY.sub("", text)
        lines = text.split("\n")
        block = _d6_faq(lines)
        if block:
            lines = lines[:block[0]] + lines[block[1]:]
        return "\n".join(lines)
    signs = (len(D6_FAQ_HEAD.findall(text)) >= 1) + bool(D6_CONCLUSION.search(text)) \
        + (len(D6_ARTICLE_HEAD.findall(text)) >= 3) + bool(D6_WRAP_UP.search(text))
    return True if signs >= 2 else text


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_d6(doc["text"]), doc["text"])
```

3. **Action:** fix + drop. **Runs on:** finemath only, where the disease was found. **Reading docs it treats:** 3 of 8 (2 dropped, 1 fixed).
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath off.
5. **Side effects:**
   - A human-written lesson with a "Conclusion" heading and a closing "In conclusion, …" sentence would be dropped.
   - A machine-written article without these signs is missed, and so are the 3 "unsure" rows.
   - On a forum page, a real numbered list of 4 or more questions after the summary line would be removed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading, mittalutkarsh/era-v5-lab#2. If a machine summary comes from a closed model, the licence rule may exclude the whole doc. That is for the team to decide.

---

## Medicine 8 — math / C7 / `DA-C7-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 5 (C7 content lost in extraction: formulas; drop; stage 30); identity `DA-C7-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-formulas, 29 docs: pyru 26 and Satyanarayana 3. Examples: `0614bc6ecf034495`, `06f2d75b8c5610f1`, `0e89fda818263262`. Formula images and symbols were lost when the page was turned into text. What is left can't be followed, as in "the number of fish in tank B =", "Use Binet's formula to show that .", "Comparing , we can see".

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** count the gaps that a lost formula leaves, and drop the doc at 4 or more. The gaps it counts:
   - a line that ends in `=`, or in a word that needs what comes after it (`is`, `of`, `that`, `therefore`, `get`…), when the next line starts a new sentence instead of carrying on. A next line carries on when it starts with a value, a lowercase letter (a wrapped line, or `a^2 + a = 0`), an answer option or a bullet, or when it holds `=` or `^`.
   - a word that needs an object, followed straight by `.`, `,` or `;` (`show that .`, `write as .`, `Comparing , we`, `and .`)
   - an empty answer option: a line holding only `(A)`, `B.` and the like, followed by another such line or by nothing
   - a `?` where a value should be (`radius: ?`, `= ?`), or `???`

   Nothing can put the formula back, so the medicine is a drop.

```python
RULE_ID = "DA-C7-001"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7_EQ_END = re.compile(r"=[ \t]*$")
C7_DANGLING = re.compile(r"\b(?:is|are|was|of|that|by|be|as|equals|gives|get|obtain|therefore|becomes)[ \t]*$", re.I)
C7_VALUE = re.compile("^[ \t]*[-+\\d(−√$\\\\]")  # the next line starts with a value: the formula is there
# the next line carries on: lowercase (a wrapped line or "a^2 + a = 0"), an answer option, a bullet, or a formula
C7_CONTINUES = re.compile("^[ \t]*(?:[a-z]|\\(?[A-Da-d][).][ \t]|[-*•])|[=^]")
C7_NO_OBJECT = re.compile(r"\b(?:is|are|as|that|of|to|by|be|get|gives?|obtain|equals?|becomes?|write|find|show|compute"
                          r"|calculate|evaluate|simplify|solve|comparing|where|and|or|then|than|with|for)[ \t]+[.,;](?=[ \t]|$)",
                          re.M | re.I)
C7_OPTION = re.compile(r"^[ \t]*\(?[A-Da-d][).][ \t]*$")
C7_QUESTION_MARK = re.compile(r"[:=][ \t]*\?[ \t]*$|(?<!\?)\?{3,}", re.M)
C7_MIN_GAPS = 4  # the most gaps in a gold doc is 3; the reading docs it drops have 4 to over 100
# Speed (14 Nov). C7_NO_OBJECT needs a space or tab before . , or ;, and C7_QUESTION_MARK needs a "?": without them
# each counts 0. A line adds a gap only if it ends in "=" or a dangling word, or is an empty answer option:
# C7_CANDIDATE finds such a line anywhere in the text, so without one the line loop adds nothing. And the count
# only grows, so once it reaches C7_MIN_GAPS the answer is known.
C7_SPACE_PUNCT = re.compile(r"[ \t][.,;]")
C7_CANDIDATE = re.compile("|".join(p.pattern for p in (C7_EQ_END, C7_DANGLING, C7_OPTION)), re.I | re.M)


def medicine_c7(text):
    gaps = len(C7_NO_OBJECT.findall(text)) if C7_SPACE_PUNCT.search(text) else 0
    if "?" in text:
        gaps += len(C7_QUESTION_MARK.findall(text))
    if gaps >= C7_MIN_GAPS:
        return True
    if not C7_CANDIDATE.search(text):
        return False
    lines = [line for line in text.split("\n") if line.strip()]
    for k, line in enumerate(lines):
        nxt = lines[k + 1] if k + 1 < len(lines) else ""
        if (C7_EQ_END.search(line) or C7_DANGLING.search(line)) and not (C7_VALUE.match(nxt) or C7_CONTINUES.search(nxt)):
            gaps += 1  # "... tank B =" or "... the parallel line is", then a new sentence: the formula is gone
        if C7_OPTION.match(line) and (not nxt or C7_OPTION.match(nxt)):
            gaps += 1  # an answer option with nothing in it
    return gaps >= C7_MIN_GAPS


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c7(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 4 of 29, all dropped. Most of the other 25 show none of these signs: their formulas were dropped mid-sentence, leaving no gap a rule can see.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A doc with 1 to 3 gaps is kept, even though those formulas are lost too.
   - Earlier versions counted lines that don't end at a gap, and so dropped gold docs:
     - option labels above their options, and `=` with the answer on the next line (`8828b7bee424578d`, `e238227f95913a28`);
     - question stems before their options (`1d47bc0cfcb2c463`);
     - "gives" before an equation (`505b2d2be1ef9b8f`);
     - "These are" before a bullet list (`c483df6e3fd9f283`);
     - a hard-wrapped line (megamath `14f21801b0ecf71e`).

     None of these counts now. Gold `5323283b31159262` has 3 gaps (a sentence ending "in worst case is" before a new sentence), so it is kept, at a cut of 4.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

---

## Medicine 9 — math / C7 / `DA-C7-002`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 6 (C7 content lost in extraction: figures; drop; stage 30); identity `DA-C7-002`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-figures, 5 docs, Satyanarayana (megamath). Examples: `019fda08843696eb`, `03aeffcf72c72418`, `0ab64ed894610ef7`. The problem refers to a figure, plot or drawing that isn't in the text: "Figure P9.26 shows the thrust", "the truss shown below".

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: off (not in `ORIGIN`); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop the doc when it refers to a missing picture twice, or once in a short doc (under 2,000 characters), where the problem can't be done without it. A reference is one of these:
   - "figure", "diagram", "graph", "picture", "image", "plot", "truss", "circuit" or "drawing", followed within the sentence by "below", "above", "shown", "shows" or "given"
   - "shown below" / "shown above", or "shown in the figure"
   - a numbered figure such as `Figure 3.12`

```python
RULE_ID = "DA-C7-002"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-megamath"  # packs it runs on: the disease was found in megamath only
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-megamath"  # pack whose reading found it (Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7F_REF = re.compile(r"\b(?:figure|fig\.|diagram|graph|picture|image|plot|truss|circuit|drawing)s?\b[^.\n]{0,60}?"
                     r"\b(?:below|above|shown|shows|given)\b"
                     r"|\b(?:shown|given|pictured|illustrated) (?:below|above|in the (?:figure|diagram|graph|picture))\b"
                     r"|\bfig(?:ure|\.) ?[A-Z]?\d+(?:\.\d+)*\b", re.I)
C7F_SHORT = 2000


def medicine_c7f(text):
    refs = len(C7F_REF.findall(text))
    return refs >= 2 or (refs == 1 and len(text) < C7F_SHORT)


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c7f(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** megamath only, where the disease was found. **Reading docs it treats:** 4 of 5, all dropped. It misses `ea37d46cbd5f339c`, whose missing figure isn't named by any of these phrases.
4. **Harm test:** megamath 0.00% (0/26) PASS; finemath off.
5. **Side effects:**
   - A long lesson that mentions two figures would be dropped, even if the text can be followed without them.
   - A reference worded another way is missed, such as "the preview images".
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Satyanarayana's megamath reading, theschoolofai/era-v5-lab#350. It may be folded into `DA-C7-001` if the team agrees.

---

## Medicine 10 — math / C8 / `DA-C8-001`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 7 (C8 layout lost in extraction: flattened formulas; drop; stage 30); identity `DA-C8-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-flattened-formulas, 22 docs: pyru 20 and Satyanarayana 2. Examples: `033ab42a96110ff9`, `0f2f052fd95da6d4`, `1ab888d9366a43fd`. The formula's layout is gone. Either superscripts and subscripts sit on the base line (`x2` for `x²`), or every token of a formula is on its own line.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop the doc when a formula has been broken into 8 or more lines in a row (blank lines between them are skipped). Each such line holds 1–3 characters: digits, single letters or operators. At least 2 of the lines must hold an operator (`+ - = ( ) / × ÷ √ ≤ ≥`…), so a column of plain numbers, such as a forum's post counts, doesn't count. An answer-option label on its own line, such as `(a)`, breaks the run: the first version counted options set out one per line (gold `8828b7bee424578d`). `x2` for `x²` can't be told from real text, so those docs are left alone.

```python
RULE_ID = "DA-C8-001"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8_TOKEN = re.compile(r"[A-Za-z0-9+\-=()\[\]/*^.,<>|\u2212\u00d7\u00f7\u221a\u2264\u2265\u2260]{1,3}")
C8_OPERATOR = re.compile(r"[+\-=()\[\]/*^<>\u2212\u00d7\u00f7\u221a\u2264\u2265\u2260]")
C8_OPTION = re.compile(r"\(?[A-Ea-e][).]")  # an answer-option label on its own line is not a piece of a formula
C8_MIN_RUN = 8


def medicine_c8(text):
    run = ops = 0
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue  # blank lines between the pieces do not break a run
        if C8_TOKEN.fullmatch(s) and not C8_OPTION.fullmatch(s):
            run += 1
            ops += bool(C8_OPERATOR.search(s))
            if run >= C8_MIN_RUN and ops >= 2:
                return True
        else:
            run = ops = 0
    return False


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c8(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 3 of 22, all dropped. Most of the 22 have superscripts flattened onto one line, which can't be told from real text.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A real column of short items with operators, such as a list of signs, would be dropped.
   - Flattened superscripts on one line (`x2`, `104` for 10⁴) are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

---

## Medicine 11 — math / C8 / `DA-C8-002`

**Consolidation:** Source [medicine_math.md](medicine_math.md), section 8 (C8 layout lost in extraction: merged table cells; drop; stage 30); identity `DA-C8-002`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-merged-table-cells, 11 docs: pyru 10 and Satyanarayana 1. Examples: `06f2d75b8c5610f1`, `1b1c42eddd14c8e7`, `1e7fad525310d310`. A table has been flattened into running text, with its cell values run together on one line ("m n mod m 2 3 4 5 6 7 8 9 1 1 3 …", "3 + 4 = 7 7 − 3 = 4 4 + 3 = 7 …"). The columns are gone.

<!-- CARD EVIDENCE -->
**Current gold harm:** math-finemath: 0 changed / 0 dropped of 86 (PASS); math-megamath: 0 changed / 0 dropped of 26 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop the doc when it has a flattened table row: a line of 20 or more tokens, at least 80% of which are numbers (up to 4 digits, with an optional decimal part or `%`) or single operators. A table whose columns are lost can't be rebuilt, so the medicine is a drop. The first version needed 2 such rows and caught none of the 11 reading docs. Each of them has one such row, and no gold doc has a numeric line longer than 15 tokens.

```python
RULE_ID = "DA-C8-002"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8T_CELL = re.compile(r"[-+]?\d{1,4}(?:[.,]\d+)?%?|[+\-=\u2212\u00d7\u00f7x*/]")
C8T_MIN_TOKENS = 20
C8T_SHARE = 0.8
C8T_MIN_ROWS = 1  # each reading doc has one such row; no gold doc has a numeric line of 20+ tokens (the longest is 15)


# Speed (14 Nov): one regex pass counts the whitespace-separated tokens C8T_CELL matches whole, instead of a Python
# loop over the tokens. (?<!\S) and (?!\S) make a match start and end at a token's edges: \s and str.split() use the
# same whitespace.
C8T_TOKEN = re.compile(r"(?<!\S)(?:" + C8T_CELL.pattern + r")(?!\S)")


def _c8t_flat_row(line):
    tokens = line.split()
    if len(tokens) < C8T_MIN_TOKENS:
        return False
    return len(C8T_TOKEN.findall(line)) >= C8T_SHARE * len(tokens)


def medicine_c8t(text):
    return sum(1 for line in text.split("\n") if _c8t_flat_row(line)) >= C8T_MIN_ROWS


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c8t(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 3 of 11, all dropped.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A doc with one long line of numbers would be dropped, for example a data set of 20 values, or a sum written out as `1 + 2 + … + 10 = 55`.
   - Tables flattened one cell per line, or mixed with words, are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

---

## Medicine 12 — sci / A7 / `DA-A7-001`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 1 (A7 word split at a line-end hyphen; fix; stage 10); identity `DA-A7-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-hyphen-split-words, 3 docs, Aditeya. The line-end hyphen was kept and the line break became a space. Examples:
   - `5a201c19575522f9`: `company- owned`, `performance- based`
   - `75768b1b6b165557`: `stereo- scopic`
   - `93412124dc441459`: `day- to-day`

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 1 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:**
   - **What it joins:** a word of 2 or more letters, then `- `, then a lowercase word. The space goes and the hyphen stays: `stereo-scopic`. With no word list it can't tell `stereoscopic` from a real compound, so it never drops the hyphen.
   - **What it leaves alone:** suspended hyphens, where the next word is `and`, `or`, `nor`, `to`, `through`, `versus` or `vs` followed by a space (`pre- and post-test`, `two- to three-fold`).
   - **`day- to-day`** becomes `day-to-day`, because there `to` is followed by a hyphen.

```python
RULE_ID = "DA-A7-001"
CODE = "A7"  # proposed new code: a word split at a line-end hyphen (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A7_SPLIT = re.compile(r"\b([A-Za-z]{2,})- ([a-z]{2,})\b(-?)")
A7_SUSPENDED = {"and", "or", "nor", "to", "through", "versus", "vs"}  # "pre- and post-test", "two- to three-fold"


def _a7_join(m):
    left, right, hyphen = m.groups()
    if right in A7_SUSPENDED and not hyphen:
        return m.group()
    return left + "-" + right + hyphen


def medicine_a7(text):
    if "- " not in text:  # speed (14 Nov): A7_SPLIT needs a hyphen and a space
        return text
    return A7_SPLIT.sub(_a7_join, text)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a7(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 3 of 3, all fixed.
4. **Harm test:** sci-finepdfs 0.50% (1/202) PASS. The one gold doc it changes, `920855df51f37db8`, has the disease itself.
5. **Side effects:**
   - A hyphen used as a dash with no space before it is joined to the next word: `it was late- we left` becomes `late-we`.
   - A word that was really split, such as `stereo-scopic`, keeps a hyphen it shouldn't have.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3. Drafted as `DA-A7-101`.

---

## Medicine 13 — sci / C9 / `DA-C9-002`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 2 (C9 SEO filler; drop; stage 30); identity `DA-C9-002`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-seo-filler, 2 docs, Aditeya. These are "ebook" pages made by a text spinner: the keyword title is repeated, there's no real content, and some carry `Page n/N` markers. Examples:
   - `d8a1ed9b1607a1dd`: "If you ally dependence such a referred … book"
   - `365b8539483e5a3f`: "access free ebook", `Page n/33`

   Math has 15 more, with their own rule, `DA-C9-001`.

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop a doc that matches either of these:
   - it has a sentence that only the ebook spinner writes: "If you ally dependence such a referred …", "You may not be perplexed to enjoy …", "every ebook collections … that we will extremely offer", "access/download/read free ebook", "acquire the enormously best seller from us", "Right here, we have countless books …";
   - it has 5 or more `Page n/N` markers and mentions "ebook".

```python
RULE_ID = "DA-C9-002"
CODE = "C9"  # proposed new code: SEO filler (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

# sentences that only the "ebook" text spinner writes
C9S_SPINNER = re.compile("|".join((
    r"if you ally (?:dependence|need|obsession|craving|habit) such a referred",
    r"you may not be perplexed to enjoy",
    r"\bebook collections?\b[^\n]{0,120}\bthat we will (?:extremely|unconditionally|very|totally) offer",
    r"\b(?:access|download|read) (?:free|this) ebook\b",
    r"acquire the (?:enormously|extremely) best seller from us",
    r"right here, we have countless (?:books?|ebooks?)\b",
)), re.I)
C9S_PAGE = re.compile(r"\bPage \d+/\d+\b")
C9S_MIN_PAGES = 5
# Speed (14 Nov): every spinner sentence, and the page test, needs one of these. casefold() maps every character that
# re.I matches to these letters, so a doc without any of them can't match, and the slow search is skipped.
C9S_NEEDS = ("such a referred", "perplexed to enjoy", "ebook", "best seller from us", "we have countless")


def medicine_c9s(text):
    low = text.casefold()
    if not any(k in low for k in C9S_NEEDS):
        return False
    if C9S_SPINNER.search(text):
        return True
    return "ebook" in text.lower() and len(C9S_PAGE.findall(text)) >= C9S_MIN_PAGES


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return ("drop", doc["text"]) if medicine_c9s(doc["text"]) else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** sci-finepdfs. **Reading docs it treats:** 2 of 2, both dropped.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A real paper that quotes one of these sentences would be dropped.
   - SEO pages that don't use one of the listed sentences are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

---

## Medicine 14 — sci / B6 / `DA-B6-001`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 3 (B6 blank form fields; drop; stage 30); identity `DA-B6-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-underscore-blanks, 2 docs, Aditeya: `3b2c0420a33ccaab` (a blank questionnaire) and `d8e3f724095e4aaa` (a blank permit form). In both, long runs of underscores mark the blanks and make up much of the text.

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop the doc when underscore runs (5 or more `_` in a row) make up 30% or more of its non-space characters. A blank form has labels but no content. The two reading docs are at 31% and 63%. The highest gold doc is at 26%: the first version, at 10%, dropped 4 gold docs.

```python
RULE_ID = "DA-B6-001"
CODE = "B6"  # proposed new code: blank form fields (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

B6_RUN = re.compile(r"_{5,}")
B6_SHARE = 0.30  # the reading docs are at 0.31 and 0.63; the highest gold doc is at 0.26
B6_SPACE = re.compile(r"\s")  # \s is str.isspace(): both use the same Unicode whitespace test


def medicine_b6(text):
    if "_____" not in text:  # speed (14 Nov): no blank, so it can't reach the share
        return False
    chars = len(text) - len(B6_SPACE.findall(text))  # non-space characters, in one pass, not a Python loop
    blanks = sum(len(m.group()) for m in B6_RUN.finditer(text))
    return chars > 0 and blanks >= B6_SHARE * chars


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return ("drop", doc["text"]) if medicine_b6(doc["text"]) else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** sci-finepdfs. **Reading docs it treats:** 2 of 2, both dropped.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A worksheet with many fill-in lines would be dropped as well.
   - The margin is small: 31% for one reading doc against 26% for the highest gold doc.
   - A form whose blanks are boxes or dots, not underscores, is missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

---

## Medicine 15 — sci / C7 / `DA-C7-003`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 4 (C7 content lost in extraction: table body or list; fix; stage 30); identity `DA-C7-003`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-table-data, 3 docs, Aditeya. A table or list was an image or a PDF object and was dropped, while the line that introduces it remained. Examples:
   - `0863ac75c9ec153e`: a table heading with no numbers
   - `4a33733776358fac`: "… is constituted with the following members." with no members after it
   - `fac0d63aba9fab0c`: action-plan column headings with no rows

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** when a line ends by announcing a list of people ("the following members." / "the following persons:" and the like), and the next non-blank line is not a list, the dangling clause is cut and the sentence ends there: "… is constituted with the following members." becomes "… is constituted.". The next line counts as a list when it starts with a bullet, number, letter, `|`, or is shorter than 60 characters, as a name would be. Headings with no data can't be told from real headings, so they are left.

```python
RULE_ID = "DA-C7-003"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7T_NOUNS = r"(?:members|persons|names|people|officials|officers|staff|students|participants|candidates)"
C7T_INTRO = re.compile(r"[ \t]*\b(?:(?:with|of|are|is|as|by)[ \t]+)?the following " + C7T_NOUNS + r"[ \t]*[.:][ \t]*$", re.I)
C7T_LIST = re.compile(r"^[ \t]*(?:[-*|•●▪]|\(?\d{1,2}[.)]|\(?[A-Za-z][.)][ \t])")
C7T_SHORT = 60
# Speed (14 Nov): C7T_INTRO needs "the following " and a noun. These cut each noun before any "i", because re.I also
# matches a dotless "ı" that casefold() keeps, so a doc without any of them can't match.
C7T_NEEDS = tuple("the following " + n for n in ("member", "person", "name", "people", "off", "staff", "student",
                                                  "part", "cand"))


def _c7t_is_list(line):
    return bool(C7T_LIST.match(line)) or len(line.strip()) < C7T_SHORT


def medicine_c7t(text):
    low = text.casefold()
    if not any(k in low for k in C7T_NEEDS):  # skip the line loop
        return text
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not C7T_INTRO.search(line):
            continue
        nxt = next((l for l in lines[i + 1:] if l.strip()), None)
        if nxt is None or not _c7t_is_list(nxt):
            lines[i] = C7T_INTRO.sub(".", line)
    return "\n".join(lines)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c7t(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 of 3 (`4a33733776358fac`).
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A list that really does follow, written as running prose, loses its introducing clause.
   - Table headings with no data and other lost lists are left as they are.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

---

## Medicine 16 — sci / C8 / `DA-C8-004`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 5 (C8 layout lost in extraction: reading order; fix; stage 30); identity `DA-C8-004`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-reading-order, 2 docs, Aditeya:
   - `ef812364b6cca7a0`: numbered steps extracted as 3, 5, 4
   - `e4d1400f9236b8c9`: a sentence split into parts that are scrambled across lines

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** in a block of 3 or more lines in a row that each start with a step number (`3. …`), check the numbers. If they are a set of consecutive numbers, each used once, but are neither ascending nor descending, the lines are put back in number order. Scrambled sentences can't be put back, so they are left.

```python
RULE_ID = "DA-C8-004"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8O_STEP = re.compile(r"^[ \t]*(\d{1,2})\.[ \t]+\S")
C8O_MIN_BLOCK = 3


def _c8o_reorder(block):
    nums = [int(C8O_STEP.match(line).group(1)) for line in block]
    if sorted(nums) != list(range(min(nums), min(nums) + len(nums))):
        return block  # not one run of consecutive step numbers
    if nums == sorted(nums) or nums == sorted(nums, reverse=True):
        return block  # already in order, or counting down on purpose
    return [line for _, line in sorted(zip(nums, block))]


def medicine_c8o(text):
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        j = i
        while j < len(lines) and C8O_STEP.match(lines[j]):
            j += 1
        if j - i >= C8O_MIN_BLOCK:
            out += _c8o_reorder(lines[i:j])
        else:
            out += lines[i:max(j, i + 1)]
        i = max(j, i + 1)
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c8o(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 of 2 (`ef812364b6cca7a0`).
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A numbered list that is out of order on purpose (a list of rankings, say) is put back in number order.
   - Steps separated by blank lines or other text are not checked.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

---

## Medicine 17 — sci / C8 / `DA-C8-003`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 6 (C8 layout lost in extraction: merged table cells; fix; stage 30); identity `DA-C8-003`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-merged-table-cells, 3 docs, Aditeya. Examples:
   - `6cdcf2807cbf5156`: `| Female | 332 50.4 |  | 48.5 |`, where the count and the percent ended up in one cell and the next cell was left empty
   - `680400a6c14bde86`: a row with one cell too many
   - `6deaff0b02c57734`: a spec table flattened into separate lines

   Math has 11 more, with their own rule, `DA-C8-002`.

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** in a Markdown table row, a cell that holds exactly two numbers and is followed by an empty cell is split, with the second number moved into the empty cell: `| 332 50.4 |  |` becomes `| 332 | 50.4 |`. Shifted rows and tables flattened into lines can't be put back, so they are left.

```python
RULE_ID = "DA-C8-003"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8C_NUM = r"-?\d[\d,]*(?:\.\d+)?%?"
C8C_PAIR = re.compile(r"\|[ \t]*(" + C8C_NUM + r")[ \t]+(" + C8C_NUM + r")[ \t]*\|[ \t]*(?=\|)")


def medicine_c8c(text):
    out = []
    for line in text.split("\n"):
        if line.lstrip().startswith("|"):
            line = C8C_PAIR.sub(lambda m: "| " + m.group(1) + " | " + m.group(2) + " ", line)
        out.append(line)
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c8c(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 of 3 (`6cdcf2807cbf5156`).
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A cell that really holds two numbers, such as a range `10 20`, followed by an empty cell would be split.
   - Shifted rows (`680400a6c14bde86`) and flattened tables (`6deaff0b02c57734`) are not fixed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

---

## Medicine 18 — sci / A7 / `DA-A7-002`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 7 (A7 word split in extraction: drop cap; fix; stage 10); identity `DA-A7-002`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-drop-cap-split, 2 docs, Utkarsh. A large first letter (a drop cap) was extracted as a line of its own, or lost. Examples:
   - `94f54a2af0a8c897`: `D` on its own line, then `eveloping a Resort and Leisure Ministries Committee`
   - `768ce30e6fac2306`: the drop cap is gone, so `St. Thomas` reads `t. Thomas`

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** a line that holds one capital letter and nothing else is joined to the next non-blank line, when that line starts with 2 or more lowercase letters and is at least 20 characters long: `D` + `eveloping a Resort …` becomes `Developing a Resort …`. `A` and `I` are left alone, because they are words (`A` / `new approach …`). A lost drop cap can't be put back, so `t. Thomas` is left.

```python
RULE_ID = "DA-A7-002"
CODE = "A7"  # proposed new code: a word split in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A7D_CAP = re.compile(r"^[ \t]*([B-HJ-Z])[ \t]*$")  # one capital letter alone on a line; A and I are words
A7D_REST = re.compile(r"^[ \t]*[a-z]{2,}")
A7D_MIN = 20  # the line it joins must be running text, not a table cell


def medicine_a7d(text):
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        m = A7D_CAP.match(lines[i])
        if m:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and A7D_REST.match(lines[j]) and len(lines[j].strip()) >= A7D_MIN:
                out.append(m.group(1) + lines[j].lstrip())
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a7d(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 / 2.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A single capital letter in a list or a form, followed by a long lowercase line, is joined to it.
   - Drop caps `A` and `I` are missed, and so are lost drop caps.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

---

## Medicine 19 — sci / A7 / `DA-A7-003`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 8 (A7 word split in extraction: small caps; fix; stage 10); identity `DA-A7-003`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-small-caps-split, 2 docs, Utkarsh. Text set in small caps was extracted with the first letter of each word split off. Examples:
   - `feaaf0b7ad58777d`: `F OODS L IMITED`, `V IJAYA K UMAR`
   - `5b348d724c744d07`: `L AKEVILLE S OUTH H IGH S CHOOL`, `S TUDENT A NNOUNCEMENTS`, `M AY 27, 2022`

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** a capital letter, a space, then 2 or more capitals (`F OODS`) is one split word, and the space goes: `FOODS`. It only works on a line set in small caps, which means all three of these:
   - the line has no lowercase letter (a course list such as `G CHEM 10050 | General Chemistry` has some);
   - it has more split pairs than whole capital words of 3 or more letters (`… ENACTING A REVISED CODE … D AND E` has many whole words);
   - the letter doesn't follow an apostrophe (`MARY’S ENGLISH` is a possessive).

   It only runs on a doc with 3 or more such splits, not counting `A` and `I`. On a small-caps line it joins every split, `A NNOUNCEMENTS` included. **Narrowed on 13 Nov:** the first version changed 3 gold docs (`G HIST` → `GHIST`, `A COMPREHENSIVE` → `ACOMPREHENSIVE`, `CECILY’S ENGLISH` → `CECILY’SENGLISH`).

```python
RULE_ID = "DA-A7-003"
CODE = "A7"  # proposed new code: a word split in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A7S_PAIR = re.compile(r"(?<![\w’'])([A-Z]) ([A-Z]{2,})\b")  # not after an apostrophe: MARY’S ENGLISH
A7S_WORDS = {"A", "I"}  # one-letter words: joined only on a small-caps line
A7S_MIN_DOC = 3  # splits on small-caps lines in the doc, not counting A and I
A7S_WHOLE = re.compile(r"\b[A-Z]{3,}\b")
A7S_LOWER = re.compile(r"[a-z]")  # speed (14 Nov): on an ASCII line, a lowercase letter is one of a-z


def _a7s_pairs(line):
    return sum(1 for m in A7S_PAIR.finditer(line) if m.group(1) not in A7S_WORDS)


def _a7s_small_caps(line):
    """No lowercase letter, and more split pairs than whole capital words."""
    # speed (14 Nov): one regex search on an ASCII line instead of a Python loop over its characters
    if A7S_LOWER.search(line) if line.isascii() else any(ch.islower() for ch in line):
        return False
    pairs = _a7s_pairs(line)
    return pairs > 0 and pairs > len(A7S_WHOLE.findall(A7S_PAIR.sub(" ", line)))


def _a7s_join(line):
    while True:
        new = A7S_PAIR.sub(lambda m: m.group(1) + m.group(2), line)
        if new == line:
            return line
        line = new


def medicine_a7s(text):
    lines = text.split("\n")
    small = [_a7s_small_caps(line) for line in lines]
    if sum(_a7s_pairs(line) for line, s in zip(lines, small) if s) < A7S_MIN_DOC:
        return text
    return "\n".join(_a7s_join(line) if s else line for line, s in zip(lines, small))


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a7s(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 2 / 2.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A short all-capitals line made mostly of letter-and-word pairs, such as `ZONES D AND E`, is joined when the doc has 3 or more such splits.
   - Small caps mixed with lowercase on one line are missed.
   - `M R .` (`MR.`) stays split, because only one letter follows the `M`.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

---

## Medicine 20 — sci / A8 / `DA-A8-002`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 9 (A8 words run together: field labels; fix; stage 10); identity `DA-A8-002`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-spaces, 3 docs: Aditeya 1, Utkarsh 2. Words or fields were run together with no space. Examples:
   - `4a6a549c3ead2ceb`: `MACEDuration:  On-goingCurrent Value:`
   - `48ffcdfea0bdbaf7`: `NEILABERCROMBIEGOVERNOR`
   - `f163172e98bdaa35`: `www.ct.gov/dcpDivision`

   Math has 13 more, with their own rule, `DA-A8-001`.

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** a space goes back in front of a known field label that is glued to the word before it and followed by a colon: `MACEDuration:` becomes `MACE Duration:`, and `On-goingCurrent Value:` becomes `On-going Current Value:`. The labels are listed (`Duration`, `Current Value`, `Client`, `Date`, `Phone`, `Email` and the like), so camel-case words such as `JavaScript:` stay. Capitals run together (`NEILABERCROMBIEGOVERNOR`) and URLs can't be split without a word list, so they are left.

```python
RULE_ID = "DA-A8-002"
CODE = "A8"  # proposed new code: words run together (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya and Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A8L_LABELS = ("Current Value", "Contract Value", "Duration", "Value", "Client", "Location", "Date", "Status",
              "Contact", "Telephone", "Tel", "Phone", "Fax", "E-Mail", "Email", "Address", "Website", "Web site",
              "Project", "Sector", "Programme", "Cost")
A8L_GLUED = re.compile(r"(?<=[A-Za-z0-9])(?=(?:" + "|".join(re.escape(l) for l in A8L_LABELS) + r")[ \t]*:)")
# Speed (14 Nov): a fast search for any "Label:" first. It starts with the labels, so the regex engine can skip to
# their first letters; A8L_GLUED, which starts with a lookbehind, is tried at every character.
A8L_ANY = re.compile(r"(?:" + "|".join(re.escape(l) for l in A8L_LABELS) + r")[ \t]*:")


def medicine_a8l(text):
    if not A8L_ANY.search(text):
        return text
    return A8L_GLUED.sub(" ", text)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a8l(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 / 3.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A camel-case name that ends in a listed label and is followed by a colon is split: `startDate:` becomes `start Date:`.
   - Labels that aren't listed, capitals run together and joined URLs are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's (mittalutkarsh/era-v5-lab#3) and Utkarsh's (mittalutkarsh/era-v5-lab#5) sci-finepdfs readings.

---

## Medicine 21 — sci / C7 / `DA-C7-005`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 10 (C7 content lost in extraction: near-empty doc; drop; stage 30); identity `DA-C7-005`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-near-empty, 2 docs, Utkarsh. Only a title or a header is left, and the body is gone. Examples:
   - `e5c998e626aeaef9`: 233 characters, a tennis order-of-play header with no matches
   - `766c83b5e63a0192`: 96 characters, a title and a date

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 1 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** drop the doc when it has fewer than 250 characters, not counting space at the start and end.

```python
RULE_ID = "DA-C7-005"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"

C7E_MIN = 250  # characters; the two reading docs have 233 and 96


def medicine_c7e(text):
    return len(text.strip()) < C7E_MIN


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return ("drop", doc["text"]) if medicine_c7e(doc["text"]) else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** sci-finepdfs. **Reading docs it treats:** 2 / 2.
4. **Harm test:** sci-finepdfs 0.50% (1/202) PASS.
5. **Side effects:**
   - A short doc that is complete, such as a one-paragraph notice, is dropped. Gold doc `b6fd81dbf90b0d17`, a 220-character certificate, is one (within the limit).
   - A doc with a long header and no body is missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

---

## Medicine 22 — sci / C7 / `DA-C7-004`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 11 (C7 content lost in extraction: figures; fix; stage 30); identity `DA-C7-004`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-missing-figures, 2 docs, Utkarsh. Where a figure was, there is a Markdown image link to a file that isn't there. Examples:
   - `ceea9671dd61d0b1`: `![Particle size distribution of CSP by LD](image1.png)`, 4 times
   - `469a6695b57d9130`: `![Figure 1-1: Power path of the LTC4061 charger](image)`, 15 times

   Megamath has 5 more, with their own rule, `DA-C7-002`. That one drops the doc, because a maths problem can't be done without its figure. A science text can still be read without its figures, so here only the empty link goes.

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 3 changed / 0 dropped of 202 (FAIL).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:**
   - **Every such link** is replaced with its caption as plain text: `![Figure 1-1: Power path](image)` becomes `Figure 1-1: Power path`. The caption is real text, often the figure's legend, so it stays.
   - **A line of links with no caption** (`![](image)`) is deleted.
   - **What counts:** a link counts only when its target is a bare `image`, `image1.png` or the like, with no folder or URL, so real image links stay.
   - **Changed on 13 Nov:** the first version deleted a line of links together with its captions, which lost figure legends and compound names in 3 gold docs.

```python
RULE_ID = "DA-C7-004"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7I_TARGET = r"\((?:image\d*(?:\.(?:png|jpe?g|gif|bmp|tiff?|svg|emf|wmf))?)\)"  # a bare file name, no folder or URL
C7I_LINK = re.compile(r"!\[([^\]\n]*)\]" + C7I_TARGET, re.I)
C7I_EMPTY_LINE = re.compile(r"^[ \t]*(?:!\[[ \t]*\]" + C7I_TARGET + r"[ \t]*)+$", re.I)  # links with no caption


def _c7i_drop_lines(lines, drop):
    """Delete these lines without leaving two blank lines in a row, or blank lines at the end."""
    out, skip_blank = [], False
    for i, line in enumerate(lines):
        if i in drop:
            skip_blank = not out or not out[-1].strip()
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    if len(lines) - 1 in drop:
        while out and not out[-1].strip():
            out.pop()
    return out


def medicine_c7i(text):
    lines = text.split("\n")
    drop = {i for i, line in enumerate(lines) if C7I_EMPTY_LINE.match(line)}
    out = "\n".join(_c7i_drop_lines(lines, drop)) if drop else text
    return C7I_LINK.sub(lambda m: m.group(1).strip(), out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c7i(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 2 / 2.
4. **Harm test:** sci-finepdfs 1.49% (3/202) FAIL.
5. **Side effects:**
   - The figure itself is still lost; only the link markup goes.
   - A caption kept as text may repeat the `Fig. 1.` caption that follows.
   - **Gold contradictions:** gold docs `4b958ac1f45443b5`, `d0a0a41263e845f5` and `eb6ad9726f2d7ddd` each have empty image links (`![Fig. 4. XPS of C dots …](image)`, `![Biotin](image)`, `![Diagram](image)`), so they hold the disease itself. Every version of this rule changes them.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

---

## Medicine 23 — sci / C8 / `DA-C8-005`

**Consolidation:** Source [medicine_sci.md](medicine_sci.md), section 12 (C8 layout lost in extraction: page numbers and footers; fix; stage 30); identity `DA-C8-005`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** NEW-page-artifact, 9 docs, Utkarsh. Page furniture from the PDF is left in the text. Examples:
   - `3f77b536af11bdbd`: `Page 1`
   - `28b7763d4a13a37e`: `Page 10 of 11`
   - `69bec7d4c7c5b24a`, `6431e058711852b7`: a page number as the last line
   - `c700ec66afb3d047`: a page number as the first line
   - `e54d3904f1e15ffb`: a page number between two paragraphs
   - `d20e4affc1d318fe`: a slide date footer (`10/21/2011`), twice
   - `77f152ce4336c6d9`: an unfilled `Page No. – Page No.` footer
   - `e58d6a06c9323550`: page numbers in a table of contents

<!-- CARD EVIDENCE -->
**Current gold harm:** sci-finepdfs: 0 changed / 0 dropped of 202 (PASS).

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** these lines are deleted:
   - a line that is only `Page N`, `Page N of M`, `Page N/M` or `Pg N`, or the unfilled `Page No. – Page No.`;
   - a date-only line (`10/21/2011`) that stands alone between blank lines and occurs 2 or more times that way in the doc. A date right under a name is the date of a letter, not a footer, and stays. This was narrowed on 13 Nov, after gold doc `8a2493cdf33f9a38` lost the dates under its signed comments;
   - a line that is only a number of 1–4 digits, in one of three places:
     - **the first line,** when the next line is not a number too;
     - **the last line,** when the line before it is a finished sentence of running text;
     - **between two lines of running text.**

     Running text means 60 or more characters with 6 or more words. A number next to other numbers or short lines (a table, a list, a contents page) stays. That is why the contents-page numbers in `e58d6a06c9323550` are left.

```python
RULE_ID = "DA-C8-005"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8P_PAGE = re.compile(r"^[ \t]*(?:page|pg\.?)[ \t]+\d{1,4}(?:[ \t]*(?:of|/)[ \t]*\d{1,4})?[ \t]*$", re.I)
C8P_UNFILLED = re.compile(r"^[ \t]*page no\.[ \t]*[-–][ \t]*page no\.[ \t]*$", re.I)
C8P_DATE = re.compile(r"^[ \t]*\d{1,2}/\d{1,2}/\d{2,4}[ \t]*$")
C8P_NUMBER = re.compile(r"^[ \t]*\d{1,4}[ \t]*$")
C8P_WORD = re.compile(r"[A-Za-z]{2,}")
C8P_END = re.compile(r"[.!?)\"”’]$")
C8P_PROSE_CHARS, C8P_PROSE_WORDS = 60, 6  # running text, not a heading or a table cell


def _c8p_prose(line, finished=False):
    s = line.strip()
    if len(s) < C8P_PROSE_CHARS or len(C8P_WORD.findall(s)) < C8P_PROSE_WORDS:
        return False
    return not finished or bool(C8P_END.search(s))


def _c8p_drop_lines(lines, drop):
    """Delete these lines without leaving two blank lines in a row, or blank lines at the end."""
    out, skip_blank = [], False
    for i, line in enumerate(lines):
        if i in drop:
            skip_blank = not out or not out[-1].strip()
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    if len(lines) - 1 in drop:
        while out and not out[-1].strip():
            out.pop()
    return out


def _c8p_alone(lines, i):
    """Blank (or the doc's edge) on both sides: a footer, not the date line of a letter."""
    return (i == 0 or not lines[i - 1].strip()) and (i == len(lines) - 1 or not lines[i + 1].strip())


def medicine_c8p(text):
    """Repeat until nothing changes: deleting one line can leave a date or number alone that wasn't before."""
    while True:
        new = _c8p_once(text)
        if new == text:
            return text
        text = new


def _c8p_once(text):
    lines = text.split("\n")
    full = [i for i, line in enumerate(lines) if line.strip()]
    dates = {}
    for i in full:
        if C8P_DATE.match(lines[i]) and _c8p_alone(lines, i):
            dates.setdefault(lines[i].strip(), []).append(i)
    drop = {i for found in dates.values() if len(found) >= 2 for i in found}
    drop |= {i for i in full if C8P_PAGE.match(lines[i]) or C8P_UNFILLED.match(lines[i])}
    rest = [i for i in full if i not in drop]  # page numbers are judged by the lines that stay
    for k, i in enumerate(rest):
        if not C8P_NUMBER.match(lines[i]):
            continue
        prev = lines[rest[k - 1]] if k > 0 else None
        nxt = lines[rest[k + 1]] if k + 1 < len(rest) else None
        if prev is None and nxt is not None and not C8P_NUMBER.match(nxt):
            drop.add(i)  # the first line
        elif nxt is None and prev is not None and _c8p_prose(prev, finished=True):
            drop.add(i)  # the last line, after a finished sentence
        elif prev is not None and nxt is not None and _c8p_prose(prev) and _c8p_prose(nxt):
            drop.add(i)  # between two lines of running text
    return "\n".join(_c8p_drop_lines(lines, drop)) if drop else text


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c8p(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 8 / 9.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A doc that really starts with a number on its own line, such as a section number, loses it.
   - A date footer written right under other text, with no blank line, is missed.
   - Page numbers next to tables, lists or headings, and a repeated title at the end (`77f152ce4336c6d9`), are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

---

## Medicine 24 — indic / C6 / `DB-C6-001`

**Consolidation:** Source [medicine_indic.md](medicine_indic.md), section 1 (C6 inconsistent punctuation: runs of dots; fix; stage 10); identity `DB-C6-001`, unchanged. The card and its python block are copied from the source sheet unchanged, so the source sheet's harm runs apply. Reading counts are per domain and are not additive across rules.


1. **Disease:** C6, the Indic family's code. TSAI ruled on 5 Nov that C6 goes into the spec. Punctuation is broken up or repeated: runs of two or more dots, with or without spaces between them, where one full stop or a standard `...` was meant. Found in ind-te-sangraha-v by one reader (oddjoker91, #177): 161 of 500 docs (32%). Examples:
   - `2a0cfe90fd36e4ed`: `. .`
   - `11960d16258cd4b5`: `..`
   - `05fa567dfc849e6b`: `. . .`

<!-- CARD EVIDENCE -->
**Current gold harm:** measured with Data B's `teams/02-data-b/tools/harm_test_indic.py`, not `harm_test.py`; see item 4 and `results/sheets/indic_sangraha-v_harm.md` and `indic_sangraha-s_harm.md`.

**Examples:** the doc_ids and short quotes in item 1. Exact source characters are not published here, because pack text stays out of the public repo; the cleaned text behind each example is kept outside the repo (`scripts/show_examples.py`).
<!-- END CARD EVIDENCE -->

2. **Medicine:** turn a run of two or more ASCII dots, including spaces or tabs between them, into exactly `...`. It never joins dots across a line break. A single dot and Unicode `…` stay. An existing `...` is matched but stays the same. Data B's separate decimal repair (`3. 67` → `3.67`) is deferred and isn't here: together with this rule it changed 2 of 18 gold docs and failed.

```python
RULE_ID = "DB-C6-001"
CODE = "C6"  # the Indic family's code (TSAI ruling, 5 Nov)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "ind-te-sangraha-v"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "ind-te-sangraha-v"  # oddjoker91's sheet, theschoolofai/era-v5-lab#177, Medicine 1
AUTHOR = "oddjoker91"
# ---- Data B's medicine, copied unchanged from diagnosis/submissions/ind-te-sangraha-v/oddjoker91/medicine.md ----
import re
_DOT_RUN = re.compile(r'\.(?:[^\S\r\n]*\.)+')
def medicine_c6(text):
    return _DOT_RUN.sub('...', text)
# ---- end of Data B's medicine ----


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c6(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix; it never drops a doc. **Runs on:** ind-te-sangraha-v. **Docs it treats:** 144 of the 161 C6-labelled docs in Data B's diagnosis. On the 500-doc diagnosis pack, 241 docs change.
4. **Harm test** (Data B's `harm_test_indic.py`):
   - **ind-te-sangraha-v, 13 Nov (aneeshads), on the 80-doc gold:** 2/80 changed, 0 dropped: **FAIL**, over the limit of 1. The joiner and normal-form audits pass. C6 → C1 → C2 in order is also 2/80; C1 and C2 change none. Report: `results/sheets/indic_sangraha-v_harm.md`. The pack file is `ind-te-sangraha-v.parquet`, the 500 docs that were read; the Week-1 copy in `Cap1-packs` holds none of the 80 gold docs.
   - **The 2 docs are gold contradictions:** `85644a4840025b6f` has `..` after మాట్లాడుతూ ("speaking"), before a quote, and `01418489e7410bdf` has `..` after మరణిస్తే ("if they die"). Both readers (oddjoker91 and sreekanthzipsy) marked the docs clean. But oddjoker91 labelled a bare `..` as C6 in other docs of the pack: 23 C6 labels point at a 2-character span. Vijay agreed to marking gold contradictions, so they are left out of the count: **0/78, PASS**. They are to be re-read at the next gold refresh.
   - **A narrower version was tried and not taken (13 Nov):** leaving a bare `..` alone, it passed at 0/80, and changed none of the sangraha-s gold docs. But it treated only 102 of the 161 labelled docs, so Data B's function stays unchanged.
   - **ind-te-sangraha-v, 9 Nov (Data B), on the old 18-doc gold:** 1/18 changed (`85644a4840025b6f`), 0 dropped. That is PASS under the 1-doc allowance, and the joiner and normal-form audits pass. C6 → C1 → C2 in order also passes at 1/18.
   - **The sangraha-s packs, 13 Nov (aneeshads):** Data B's function, which has no pack check, ran on every gold doc and changed none. That is 0/24 on ind-hi-sangraha-s, 0/22 on ind-kn-sangraha-s and 0/24 on ind-te-sangraha-s, all PASS with the audits passing. ind-ta-sangraha-s has no gold set. Report: `results/sheets/indic_sangraha-s_harm.md`. With this sheet's pack check, the rule is off on those packs.
5. **Side effects:**
   - Dots used on purpose are changed, such as four dots for a full stop plus an ellipsis (`....` becomes `...`).
   - A bare `..` used as a pause in Telugu news writing becomes `...`, as in the 2 gold contradictions. Whether that `..` is a disease is open for Data B.
   - Code, paths and other structured text may use dots meaningfully.
   - It doesn't fix every C6 case, or make an affected doc clean.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Author: oddjoker91 (Data B). Source: theschoolofai/era-v5-lab#177, listed for v1.1 in theschoolofai/era-v5-lab#216. Carried into this sheet by aneeshads, 13 Nov.

---
