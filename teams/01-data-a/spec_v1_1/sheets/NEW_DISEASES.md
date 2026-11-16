# NEW_DISEASES: the new diseases found for Spec v1.1 (Data A reading audits and the Indic family)

**The task (pipeline owner, due Fri 13 Nov):** for each new disease above 1%, write a medicine and a harm test for Spec v1.1.

- **New** means a disease that is not in `diagnosis/DISEASES.md`, the list of diseases spec v1 made medicines for.
- **Above 1%** means it is in 1% or more of the docs read in its domain.

This file records each new disease: its name, a description, its code, its rule ID and the packs where it was found. Rows that readers marked `new` but that `DISEASES.md` already describes are listed under "Not new" at the end. Update this file after every collector run (`scripts/collect_reading_prs.py`, output in `results/reading/summary.md`).

**Two teams are in this file:**
- **Data A families** (english, code, math, sci): their rules are `DA-…`.
- **The Indic family** (Data B): its rules are `DB-<code>-<nnn>`, so they can't clash with the `DA-…` ones. Its new diseases come from theschoolofai/era-v5-lab#216 and are marked **Indic** in the family column.

**C6 is the Indic family's code.** The Indic family proposed C6 first (31 Oct), for inconsistent punctuation and formatting, and TSAI ruled on 5 Nov that C6 goes into the spec. Data A's template pages first had C6 too, so on 12 Nov they moved to C9 as `DA-C9-003`, beside SEO filler. Now every code means one disease for both teams.

**Last updated:** 13 Nov 2026, from the collector run of 13:13 UTC: 8 open reading PRs plus the merged copies, 20 files, 650 rows. It used `--docs-read pyru=199 --docs-read narasimhatejav@english=50 --docs-read kunal=50 --docs-read aneesha=50 --docs-read smita=50 --alias NEW-form-blanks=NEW-underscore-blanks`.
- **Math:** complete. pyru read 199 finemath docs and Satyanarayana 100 megamath docs. Satyanarayana's reading (theschoolofai/era-v5-lab#350) was merged into theschoolofai `main` on 13 Nov, and the collector now reads it from there.
- **Science:** complete. Aditeya read 100 docs (mittalutkarsh/era-v5-lab#3) and Utkarsh 100 (mittalutkarsh/era-v5-lab#5), so the bar is 2 of 200.
- **Code:** no new diseases. narasimhatejav (mittalutkarsh/era-v5-lab#6) and Revant read 100 docs each, and every code row is a spec v1 miss.
- **English:** 200 docs read, 50 by each of four readers, so the bar is 2:
  - narasimhatejav, en-fineweb-edu (mittalutkarsh/era-v5-lab#7). He chose the 50 docs; they aren't the `pick_docs.py` rows.
  - kunal, en-nemotroncc-synth (mittalutkarsh/era-v5-lab#8).
  - aneesha, en-nemotroncc (mittalutkarsh/era-v5-lab#9).
  - Smita, en-dclm (patilvijay23/era-v5-lab#36).

  Three new diseases reach the bar: facts the rewrite got wrong (D7), appended Q&A (D6, rule withdrawn) and words run together (A8). C4, two documents joined, reaches it too, but it isn't new.

**Status of the codes:** every new code and ID below is **proposed** and needs the team's agreement. A new code also needs an entry in `diagnosis/DISEASES.md` and in `CODE_ORDER` in `spec_v1/tools/build_clean.py`, or `clean.py` can't be built with it.

## Naming rules

1. **New or not.** A disease is new only if no disease in `diagnosis/DISEASES.md` describes it. If one does, the disease is not new, even in a family that has no spec v1 rule for it. It goes under "Not new", and Spec v1.1 doesn't cover it.
2. **New code.** A new disease gets the next free code in the nearest group of `DISEASES.md`:
   - A: Characters
   - B: Markup and ghost tokens
   - C: Document structure
   - D: Language
   - E: Code
   - F: Safety, privacy and contamination
   - G: Damage from earlier cleaning
   - H: Duplicates

   A code is one letter A–H plus one digit 1–9, the only form that `harm_test.py` and `build_clean.py` accept. Related diseases share a code when a group runs out of digits.
3. **Rule ID.** `DA-<code>-<nnn>` for the Data A families, and `DB-<code>-<nnn>` for the Indic family (Data B) ("Stable `DA-<code>-<nnn>`. Never reused", `spec_v1/README.md`). `nnn` is the next number that team has not used for that code on main, on `g1-specv1` or in the sheets. A new code starts at 001.
   - **One code, one meaning.** A disease code means the same disease for both teams. Only the prefix differs.
4. **One rule per family.** A disease found in two families gets one rule in each, with its own ID. `build_clean.py` puts each rule in one family and needs every ID in the collated sheet to be unique.
5. **When an ID is assigned.** Only when the disease qualifies. A disease below the bar has no ID yet, and its next free ID is shown in brackets.

## Summary: new diseases

| code | disease | reading code | family | packs (docs) | ≥1% of docs read | rule ID | medicine |
|---|---|---|---|---|---|---|---|
| **A7** | Word split in extraction: line-end hyphen | NEW-hyphen-split-words | sci | sci-finepdfs (3) | yes | `DA-A7-001` | written, tested |
| **A7** | Word split in extraction: drop cap | NEW-drop-cap-split | sci | sci-finepdfs (2) | yes | `DA-A7-002` | written, tested |
| **A7** | Word split in extraction: small caps | NEW-small-caps-split | sci | sci-finepdfs (2) | yes | `DA-A7-003` | written, tested; narrowed after it harmed 3 gold docs, now 0/202 |
| **A8** | Words run together | NEW-missing-spaces | math | math-finemath (5), math-megamath (8) | yes | `DA-A8-001` | written, tested |
| **A8** | Words run together | NEW-missing-spaces | sci | sci-finepdfs (3) | yes | `DA-A8-002` | written, tested |
| **A8** | Words run together | NEW-missing-spaces | english | en-nemotroncc (2; and 56 of 500 Week 1 diagnosis docs in HariniJasti's labels without a full stop) | yes | `DA-A8-003`, `DA-A8-004` | written, tested; `DA-A8-004` from HariniJasti (patilvijay23/era-v5-lab#41), carried in 14 Nov |
| **A9** | Accent split from its letter | NEW-detached-diacritics | sci | sci-finepdfs (1) | no (1 of 200) | (`DA-A9-001`) | - |
| **B6** | Blank form fields (Utkarsh's NEW-form-blanks counted with it) | NEW-underscore-blanks | sci | sci-finepdfs (7) | yes | `DA-B6-001` | written, tested; catches 2 of 7 |
| **C6** | Inconsistent punctuation and formatting (runs of dots) | C6 (diagnosis labels, #177) | **Indic** | ind-te-sangraha-v (161 of 500 labelled docs, one reader) | yes (32%) | `DB-C6-001` | written by Data B (#177, Medicine 1). Harm test on the 80-doc gold: 2/80 FAIL, both gold contradictions, so 0/78 PASS without them (13 Nov). Carried into `specv1_1.md` as Medicine 23 through `medicine_indic.md`, unchanged (13 Nov) |
| **C7** | Content lost in extraction: formulas | NEW-missing-formulas | math | math-finemath (26), math-megamath (3) | yes | `DA-C7-001` | written, tested |
| **C7** | Content lost in extraction: figures | NEW-missing-figures | math | math-megamath (5) | yes | `DA-C7-002` | written, tested |
| **C7** | Content lost in extraction: table body | NEW-missing-table-data | sci | sci-finepdfs (3) | yes | `DA-C7-003` | written, tested |
| **C7** | Content lost in extraction: figures | NEW-missing-figures | sci | sci-finepdfs (2) | yes | `DA-C7-004` | written, tested; harm **FAIL** (3/202), all 3 gold contradictions |
| **C7** | Content lost in extraction: near-empty doc | NEW-near-empty | sci | sci-finepdfs (2) | yes | `DA-C7-005` | written, tested |
| **C7** | Content lost in extraction: a doc that was all figures | NEW-figure-only-doc | sci | sci-finepdfs (1) | no (1 of 200) | (`DA-C7-006`) | - |
| **C7** | Content lost in extraction: figure labels left alone | NEW-orphan-figure-labels | sci | sci-finepdfs (1) | no (1 of 200) | (`DA-C7-006`) | - |
| **C8** | Layout lost in extraction: flattened formulas | NEW-flattened-formulas | math | math-finemath (20), math-megamath (2) | yes | `DA-C8-001` | written, tested |
| **C8** | Layout lost in extraction: merged table cells | NEW-merged-table-cells | math | math-finemath (10), math-megamath (1) | yes | `DA-C8-002` | written, tested |
| **C8** | Layout lost in extraction: merged table cells | NEW-merged-table-cells | sci | sci-finepdfs (3) | yes | `DA-C8-003` | written, tested |
| **C8** | Layout lost in extraction: reading order | NEW-reading-order | sci | sci-finepdfs (2) | yes | `DA-C8-004` | written, tested |
| **C8** | Layout lost in extraction: page numbers and footers | NEW-page-artifact | sci | sci-finepdfs (9) | yes | `DA-C8-005` | written, tested |
| **C8** | Layout lost in extraction: split superscripts | NEW-split-superscripts | sci | sci-finepdfs (1) | no (1 of 200) | (`DA-C8-006`) | - |
| **C9** | SEO filler | NEW-seo-filler | math | math-finemath (10), math-megamath (5) | yes | `DA-C9-001` | written, tested |
| **C9** | SEO filler | NEW-seo-filler | sci | sci-finepdfs (2) | yes | `DA-C9-002` | written, tested |
| **C9** | Pages made for search: a page made from a template for one value | NEW-template-pages | math | math-finemath (8), math-megamath (1) | yes | `DA-C9-003` | written, tested |
| **C9** | SEO filler: spun text | NEW-spun-text | sci | sci-finepdfs (1) | no (1 of 200) | (with `DA-C9-002`) | - |
| **D6** | Machine-written text | NEW-ai-generated-text | math | math-finemath (8) | yes | `DA-D6-001` | written, tested |
| **D6** | Machine-written text: an appended question and answer | NEW-appended-qa | english | en-nemotroncc-synth (3) | yes | `DA-D6-002`, **withdrawn** | written and tested, then withdrawn on 13 Nov: 32 of 326 gold docs have the same Q&A; its 2 wrong answers are in `DA-D7-001` |
| **D6** | Machine-written text: picture captions | NEW-generated-image-captions | sci | sci-finepdfs (1) | no (1 of 200) | (`DA-D6-003`) | - |
| **D7** | Facts the rewrite got wrong | NEW-factual-error | english | en-nemotroncc-synth (4) | yes | `DA-D7-001` | written, tested; quarantines 6 confirmed doc IDs |

**Totals:** 30 rows. 24 qualify (8 math, 12 science, 3 English, 1 Indic); the English appended-Q&A row's rule is withdrawn. 6 science rows are below the bar. When two rows below the bar share a next free ID, the first to qualify takes it, and the other moves to the next number.

**Below the bar, from Utkarsh's reading:** one doc each (0.5% of 200), so they need no medicine. They have no code yet; the nearest code is shown, to be agreed if one ever reaches the bar.

| reading code | doc | what it is | nearest code |
|---|---|---|---|
| NEW-empty-table-rows | 1 | Markdown table rows with every cell empty | C8 layout lost in extraction |
| NEW-huge-tables | 1 | thousands of table lines filling a doc | none agreed |
| NEW-latex-residue | 1 | well-formed LaTeX commands left in prose (`\textsuperscript`) | B5 broken Markdown or LaTeX, if the team counts it |
| NEW-prose-in-code-fence | 1 | prose wrapped in code fences | B5 broken Markdown or LaTeX, if the team counts it |
| NEW-scrambled-vertical-text | 1 | a vertical letterhead read one word or letter per line, out of order | C8 layout lost in extraction (reading order) |

**The "≥1% of docs read" column** shows whether a disease passes the Spec v1.1 bar: it is in 1% or more of the docs read in its domain. Only those diseases need a medicine and a harm test.
- **Math:** 299 docs read, so a disease needs 3. Every math row passes.
- **Science:** 200 docs read (Aditeya 100, Utkarsh 100), so a disease needs 2.
- **English:** 200 docs read (four readers, 50 each), so a disease needs 2. There are 23 more English codes with 1 doc each, below the bar; they are listed in `decisions_english.md`. Some of them may be the same disease as a code here.
- **Indic:** the count comes from Data B's diagnosis labels of the 500-doc pack, not from the Week 2 reading: 161 of 500 docs (32%).

## A. Characters

### A7 Word split in extraction

- **Disease:** extraction breaks a word into pieces. There are three kinds:
  - **Line-end hyphen:** a word broken across a PDF line keeps its hyphen, and the line break becomes a space: `stereo- scopic`, `company- owned`, `day- to-day`.
  - **Drop cap:** a large first letter ends up on a line of its own (`D` / `eveloping`), or is lost (`t. Thomas` for `St. Thomas`).
  - **Small caps:** the first letter of each word is split off: `F OODS L IMITED`, `L AKEVILLE S OUTH H IGH S CHOOL`.
- **Not in DISEASES.md:** G1 covers Indic words cut at a vowel sign only.
- **Found:**
  - **NEW-hyphen-split-words:** sci-finepdfs, 3 docs (Aditeya): `5a201c19575522f9`, `75768b1b6b165557`, `93412124dc441459`. Rule `DA-A7-001`, fix: the space goes and the hyphen stays.
  - **NEW-drop-cap-split:** sci-finepdfs, 2 docs (Utkarsh): `94f54a2af0a8c897`, `768ce30e6fac2306`. Rule `DA-A7-002`, fix: a lone capital is joined to the lowercase line after it.
  - **NEW-small-caps-split:** sci-finepdfs, 2 docs (Utkarsh): `feaaf0b7ad58777d`, `5b348d724c744d07`. Rule `DA-A7-003`, fix: the split letter is joined back on lines set in small caps, in a doc with 3 or more splits. The first version harmed 3 gold docs (course codes, all-capitals titles, a possessive `’S`). It was narrowed the same day, and now touches 0/202 gold docs and still catches 2 of 2.
- **Name:** this was "Word split at a line-end hyphen" until 13 Nov. It was widened when Utkarsh's reading found the other two kinds, because group A has no free digit left.

### A8 Words run together

- **Disease:** a space or line break between two pieces of text is lost, so they run together. Examples: a title glued to the sentence after it, a list of glossary entries on one line, a variable stuck to the next word, field labels glued to their values (`MACEDuration:`).
- **Found:**
  - math-finemath, 5 docs (pyru), and math-megamath, 8 docs (Satyanarayana): `03aeffcf72c72418`, `167ef4a340862a0e`, `1ab888d9366a43fd`.
  - sci-finepdfs, 3 docs: Aditeya `f163172e98bdaa35`; Utkarsh `4a6a549c3ead2ceb`, `48ffcdfea0bdbaf7`.
- **English:** en-nemotroncc, 2 docs (aneesha): `2feb05980d7d894a` (`choose.Compose`), `502ee3da08920d31` (`awhile`, an English word that no rule should split). Rule `DA-A8-003`, fix, in `medicine_english.md`: a space goes back after a full stop between a lowercase word and a capitalised one. 1 of 129 gold docs changed (PASS); that doc, `056cc9bc44c927e2`, has the disease itself.
- **Rules:** `DA-A8-001`, fix, math, in `medicine_math.md`. `DA-A8-002`, fix, science, in `medicine_sci.md`: a space goes back in front of a listed field label. It catches 1 of the 3 science docs.

### A9 Accent split from its letter

- **Disease:** an accent comes out as a separate spacing character next to its letter: `Mo´nica` for `Mónica`.
- **Found:** sci-finepdfs, 1 doc (Aditeya): `21f33206f24a2f0e`.
- **Rule:** none. It is below the bar (1 of 200 science docs). It would get `DA-A9-001`.

## B. Markup and ghost tokens

### B6 Blank form fields

- **Disease:** a blank fill-in form or questionnaire. Long runs of underscores mark the blanks and make up much of the text.
- **Not in DISEASES.md:** B4 covers template and code placeholders (`{{ variable }}`, `${...}`), not unfilled form lines.
- **Found:** sci-finepdfs, 7 docs.
  - Aditeya, as NEW-underscore-blanks: `3b2c0420a33ccaab`, `d8e3f724095e4aaa`.
  - Utkarsh, as NEW-form-blanks: `323d03a0c69a993a`, `5379152bb87b7ecf`, `6bd9cff2867dde6b`, `bf7287e7e6c32f33`, `fefc24dc3b193463`.

  The collector counts the two names as one (`--alias NEW-form-blanks=NEW-underscore-blanks`).
- **Rule:** `DA-B6-001`, drop, in `medicine_sci.md`. It drops a doc whose underscore runs make up 30% or more of its text. It catches Aditeya's 2 docs but none of Utkarsh's 5, whose blanks are a small part of a longer form. The rule is unchanged.

## C. Document structure

### C7 Content lost in extraction

- **Disease:** when the page was turned into text, formulas, pictures or table bodies that were images or PDF objects were dropped, and what is left can't be followed. Nothing can put the content back. Typical signs:
  - a sentence ending in `=` or `:` with nothing after it
  - empty answer options `(A)`–`(D)`
  - "the figure below" with no figure
  - table headings with no rows
  - diagram labels with no diagram
- **Found:**
  - **NEW-missing-formulas:** math-finemath, 26 docs (pyru), and math-megamath, 3 docs (Satyanarayana): `0614bc6ecf034495`, `06f2d75b8c5610f1`, `0e89fda818263262`. Rule `DA-C7-001`.
  - **NEW-missing-figures:** math-megamath, 5 docs (Satyanarayana): `019fda08843696eb`, `03aeffcf72c72418`, `0ab64ed894610ef7`. Rule `DA-C7-002`, or the same rule as `DA-C7-001` if the team folds the two together.
  - **NEW-missing-table-data:** sci-finepdfs, 3 docs (Aditeya): `0863ac75c9ec153e`, `4a33733776358fac`, `fac0d63aba9fab0c`. Rule `DA-C7-003`.
  - **NEW-missing-figures, science:** sci-finepdfs, 2 docs (Utkarsh): `ceea9671dd61d0b1`, `469a6695b57d9130`. Markdown image links point to files that aren't there. Rule `DA-C7-004`, fix: each link becomes its caption as plain text, and links with no caption go. **Harm: FAIL**, 3 of 202 gold docs changed. All 3 have empty image links themselves, so they are gold contradictions.
  - **NEW-near-empty:** sci-finepdfs, 2 docs (Utkarsh): `e5c998e626aeaef9`, `766c83b5e63a0192`. Only a title or header is left. Rule `DA-C7-005`, drop: under 250 characters.
  - **NEW-figure-only-doc:** sci-finepdfs, 1 doc (Aditeya): `35d51dcf919068f8`. Only the title, authors and licence are left. Below the bar (1 of 200).
  - **NEW-orphan-figure-labels:** sci-finepdfs, 1 doc (Aditeya): `75183caf56d8e54b`. Diagram callouts are left as lines of single letters and numbers. Below the bar (1 of 200).

### C8 Layout lost in extraction

- **Disease:** the text is all there, but its layout isn't. Typical signs:
  - superscripts and subscripts on the base line (`x2` for `x²`), or one token per line
  - table cells run together or shifted a column
  - steps or sentences out of order
  - an ordinal suffix moved onto its own line
- **Found:**
  - **NEW-flattened-formulas:** math-finemath, 20 docs (pyru), and math-megamath, 2 docs (Satyanarayana): `033ab42a96110ff9`, `0f2f052fd95da6d4`, `1ab888d9366a43fd`. Rule `DA-C8-001`.
  - **NEW-merged-table-cells, math:** math-finemath, 10 docs (pyru), and math-megamath, 1 doc (Satyanarayana): `06f2d75b8c5610f1`, `1b1c42eddd14c8e7`, `1e7fad525310d310`. Rule `DA-C8-002`.
  - **NEW-merged-table-cells, science:** sci-finepdfs, 3 docs (Aditeya): `680400a6c14bde86`, `6cdcf2807cbf5156`, `6deaff0b02c57734`. Rule `DA-C8-003`.
  - **NEW-reading-order:** sci-finepdfs, 2 docs (Aditeya): `e4d1400f9236b8c9`, `ef812364b6cca7a0`. Rule `DA-C8-004`.
  - **NEW-page-artifact:** sci-finepdfs, 9 docs (Utkarsh): `3f77b536af11bdbd`, `28b7763d4a13a37e`, `69bec7d4c7c5b24a`. These are page numbers, `Page N of M` footers and slide date footers. Rule `DA-C8-005`, fix: it deletes those lines, and catches 8 of the 9 docs.
  - **NEW-split-superscripts:** sci-finepdfs, 1 doc (Aditeya): `db955ac64864c36c`. Below the bar (1 of 200).
- **Note:** merged table cells and reading order may have no safe repair. If so, the medicine is a drop rule, and the harm test sets its status.

### C9 Pages made for search traffic: SEO filler and template pages

- **Disease:** a page written to rank in search, not to teach. There are two kinds.
  - **SEO filler**, with these typical signs:
    - generic filler paragraphs
    - tutoring or homework-app sales copy
    - "download this ebook" pages
    - the title repeated many times
    - text run through a synonym spinner
  - **Template pages:** a calculator, unit-converter or number-fact page that a site generates for every value, such as "Prime factorization of 36871", "68.71 kg in pounds" or "15 percent off $41". It is the same template with one number swapped in, and it often states wrong results.
- **Not in DISEASES.md:** C5 is lists of keywords or links. These pages are prose and generated pages.
- **Why template pages are here:** they were C6 at first. C6 is the Indic family's code (see "Indic family" below), so on 12 Nov they moved here, beside SEO filler.
- **Found:**
  - **NEW-template-pages:** math-finemath, 8 docs (pyru), and math-megamath, 1 doc (Satyanarayana): `28f56e454b2ade39`, `32b1f031d8c464e4`, `647d9713533c5664`. Rule `DA-C9-003` (was `DA-C6-001`), drop, both math packs, in `medicine_math.md`.
  - **NEW-seo-filler, math:** math-finemath, 10 docs (pyru), and math-megamath, 5 docs (Satyanarayana): `053c7e6dfbdb4e46`, `085f9f7987b7cf56`, `0e2b9cc0beb5fb11`. Rule `DA-C9-001`.
  - **NEW-seo-filler, science:** sci-finepdfs, 2 docs (Aditeya): `365b8539483e5a3f`, `d8a1ed9b1607a1dd`. Rule `DA-C9-002`.
  - **NEW-spun-text:** sci-finepdfs, 1 doc (Aditeya): `f82d23a50e08a31f`. Below the bar (1 of 200). If the team agrees, it can be counted with NEW-seo-filler (`--alias NEW-spun-text=NEW-seo-filler`).

## D. Language

### D6 Machine-written text

- **Disease:** text generated by a model and added to the page. Typical signs:
  - machine-written SEO articles, often with false statements
  - AI summaries and FAQ blocks that a site adds under a forum thread
  - machine-written picture descriptions inserted into the text
- **Not in DISEASES.md:** D4 and D5 are about translation.
- **Found:**
  - **NEW-ai-generated-text:** math-finemath, 8 docs (pyru), 3 of them marked "unsure": `10d547035dd610e2`, `36c3e8b4b4457083`, `8f1f8a9c194e88f2`. Rule `DA-D6-001`.
  - **NEW-generated-image-captions:** sci-finepdfs, 1 doc (Aditeya): `79596acc4ee8648a`. Below the bar (1 of 200). Its next free ID moved to `DA-D6-003`, because `DA-D6-002` was used (and withdrawn) for appended Q&A.
  - **NEW-appended-qa, English:** en-nemotroncc-synth, 3 docs (kunal): `5aeafd200220c080`, `ffaad5c6d3dde332`, `c3d88009d8a459e9`. A synthetic `Question: … Answer: …` pair is added after the passage.
    - **The rule:** `DA-D6-002` removed it and caught all 3, but changed 32 of 326 gold docs. Those end in ordinary, correct Q&A: it is part of this synthetic pack, and the gold readers marked it clean. No text signal separates the reading docs, so the rule was **withdrawn** (aneeshads, 13 Nov), and the ID is not reused.
    - **The 3 docs:** 2 have wrong answers, so they are in `DA-D7-001`; the third is correct.
    - **Open:** is appended Q&A a disease, or the pack's own format?

### D7 Facts the rewrite got wrong

- **Disease:** a synthetic rewrite brings in an error that can be checked. Victoria is called "the Virgin Queen" (Elizabeth I); "the battles of Artemisia" stands for Artemisium; "Exodus 9" for Joshua 9; a camera comparison is reversed.
- **Not in DISEASES.md:** D4 (bad machine translation) is about translation. This is the next free code in group D.
- **Found:** en-nemotroncc-synth, 4 docs (kunal): `0f7b90400c1362df`, `0f7240ba1fdd3411`, `52bd1da881ee0592`, `f2a8b2cc25bb5c7a`. 2 more are wrong answers in an appended Q&A: `5aeafd200220c080`, `c3d88009d8a459e9`.
- **Rule:** `DA-D7-001`, drop, in `medicine_english.md`. It quarantines the 6 confirmed doc IDs, as spec v1 does for confirmed records (`DA-D1-001`, `DA-F1-006`). Nothing in the text marks a wrong fact, so a rule can't find others; that needs a fact check or a model. Chosen by aneeshads, 13 Nov. Harm 0/326, which proves little.

## Indic family (Data B)

The Indic family's rules are `DB-<code>-<nnn>`.

- **Source:** Data B's list of proposed new codes for Spec v1.1 (shankarpandala, theschoolofai/era-v5-lab#216, 12 Nov). Data B checked every `ind-*` and `cadj-*` sheet on main. Only one code in use isn't in `DISEASES.md`, and the checking reads and rotation audits used existing codes only.

### C6 Inconsistent punctuation and formatting · Indic

- **Disease:** punctuation that has been broken up or repeated: runs of two or more dots, with or without spaces between them (`. .`, `..`, `. . .`), where one full stop or a standard `...` was meant. A separate C6 case is a decimal broken by a space (`3. 67` for `3.67`).
- **Not in DISEASES.md:** proposed as a new code by oddjoker91 on 31 Oct (G2). TSAI ruled on 5 Nov that C6 goes into spec v1 once #177 is approved. #177 is merged, but theschoolofai/era-v5-lab#244 doesn't turn C6 on, so Data B proposes it for v1.1.
- **Found:** ind-te-sangraha-v, one reader (oddjoker91, #177). 161 of 500 docs (32%): 138 fix and 23 drop, 108 of them with C6 alone. Examples: `2a0cfe90fd36e4ed` (`. .`), `11960d16258cd4b5` (`..`), `05fa567dfc849e6b` (`. . .`).
- **Rule:** `DB-C6-001`, fix, from Medicine 1 in `diagnosis/submissions/ind-te-sangraha-v/oddjoker91/medicine.md`. It turns a run of two or more ASCII dots, including spaces between them, into exactly `...`, never across a line break. A single dot, an existing `...` and `…` stay. It never drops a doc.
- **Harm test (Data B, 9 Nov):** PASS on the 18-doc gold: 1 of 18 changed (`85644a4840025b6f`), within the 1-doc allowance, and 0 dropped. The joiner (ZWJ/ZWNJ) and normal-form audits passed. Run in order C6 → C1 → C2, it also passed at 1 of 18.
- **Harm test on the sangraha-s packs (aneeshads, 13 Nov):** run with `teams/02-data-b/tools/harm_test_indic.py --rule all` on oddjoker91's `medicine.md` (sha256 `812cb37e435e…`), with the gold in `teams/02-data-b/gold/`. Report: `results/sheets/indic_sangraha-s_harm.md`.
  - **Results:** C6, C1, C2 and all three in order: **0 changed, 0 dropped, PASS** on ind-hi-sangraha-s (24 gold docs), ind-kn-sangraha-s (22) and ind-te-sangraha-s (24). The joiner and normal-form audits pass. ind-ta-sangraha-s has no gold set, so it is not testable.
  - **What it shows:** the rules have no pack check, so they ran on every gold doc and changed none. That is no harm on these packs, not proof that the rules treat anything there. These aren't the pack the disease was found on.
- **Harm test on ind-te-sangraha-v's 80-doc gold (aneeshads, 13 Nov):** the same tool, on oddjoker91's `medicine.md`, with the pack that was read (`ind-te-sangraha-v.parquet`, 500 docs). Report: `results/sheets/indic_sangraha-v_harm.md`.
  - **Results:** C6 changes **2 of 80, FAIL** (limit 1): `01418489e7410bdf` and `85644a4840025b6f`. C1 and C2 change 0, PASS. All three in order: 2 of 80, FAIL. The joiner and normal-form audits pass.
  - **The 2 docs are gold contradictions.** Each has a bare `..` in mid-sentence. Both readers marked them clean, but oddjoker91 labelled a bare `..` as C6 in other docs of the pack. Vijay agreed to marking gold contradictions, so they are left out of the count: **0 of 78, PASS**.
  - **Reach:** the rule changes 241 of the 500 docs, and 144 of the 161 C6-labelled ones.
  - **A narrower version was tried and not taken.** It left a bare `..` alone and passed (0 of 80), but fixed only 102 of the 161 labelled docs.
- **In the consolidated sheet (13 Nov):** `sheets/medicine_indic.md` carries `DB-C6-001` into `specv1_1_additions.md` as Medicine 23. From there it goes into the combined `specv1_1.md` (14 Nov) as Medicine 363, the last Indic rule.
  - **The code:** Data B's `medicine_c6` is copied unchanged. Only the block's header lines and a `pack_id` check for ind-te-sangraha-v are added, so it loads with `harm_test.py` and runs on that pack only.
  - **Tests:** `tests/test_medicine_indic.py`, 7 tests.
  - **Not carried:** C1 and C2 from the same sheet, which aren't new.
- **Deferred:** the decimal repair (`3. 67` → `3.67`). Together with the dot rule it changes 2 of 18 gold docs and FAILS, so it isn't active.
- **ID check:** no `DB-C6-…` ID is used on main or on `g1-specv1`, so `DB-C6-001` is free.

## Not new: the disease is already in DISEASES.md

Readers flagged these as new, either as `NEW-…` codes or as a known code with kind `new`. In each case a disease in `DISEASES.md` already describes them, so Spec v1.1 doesn't cover them and they get no v1.1 ID. Where the family has no spec v1 rule for the disease, that is a gap in spec v1's pack scope, not a new disease.

| reading code | family | packs (docs) | DISEASES.md code | spec v1 rule in this family | note |
|---|---|---|---|---|---|
| NEW-pdf-ligatures | sci | sci-finepdfs (5) | A5 wrong normal form (ligatures, as in math's `DA-A5-001`) | none | A rule drafted as `DA-A5-101` was taken out of `medicine_sci.md` on 12 Nov. |
| NEW-pdf-quote-glyphs | sci | sci-finepdfs (1) | A6 wrong or mixed script (wrong glyphs, as in math's `DA-A6-001`) | `DA-A6-002` | |
| B1 | math | math-finemath (3) | B1 HTML entities | none (`DA-B1-002` runs on English only) | A rule drafted as `DA-B1-101` was taken out of `medicine_math.md` on 12 Nov. |
| NEW-toc-dot-leaders | sci | sci-finepdfs (2): `59aef569bc52cdff`, `b1857f12c0d28f07` | C1 boilerplate | `DA-C1-007` | A rule drafted as `DA-C1-101` was taken out of `medicine_sci.md` on 12 Nov. |
| NEW-aggregated-questions | math | math-megamath (4) | C4 two documents joined | none | |
| C5 | sci | sci-finepdfs (1) | C5 lists of keywords or links | none | |
| NEW-personal-names-ages | sci | sci-finepdfs (1) | F1 personal data (names of private people with ages) | `DA-F1-006` | From Utkarsh's reading. Type and position only. |
| C4 | english | en-nemotroncc-synth (4) | C4 two documents joined | none | From kunal's reading, at the English bar (2.0%). It is a gap in spec v1's English scope. kunal notes it likely needs a model or classifier. |

## Open

- **The team's agreement** is still needed for every proposed code, both Data A's and Data B's.
- **Gold contradictions.** Ten gold docs have a new disease that a v1.1 rule targets:
  - finemath `2d328b828fa97706` (A8)
  - finemath `0f119a596e8b7f63` (C9 template pages)
  - sci `920855df51f37db8` (A7)
  - sci `4b958ac1f45443b5`, `d0a0a41263e845f5` and `eb6ad9726f2d7ddd` (C7 empty image links, `DA-C7-004`; read 13 Nov)
  - en-nemotroncc `056cc9bc44c927e2` (A8, `DA-A8-003`: `tantrum.To`; within the limit; read 13 Nov) and `fd16036899796ca4` (A8, `DA-A8-004`: `saidSanaz`; 14 Nov)
  - ind-te-sangraha-v `85644a4840025b6f` and `01418489e7410bdf` (C6, `DB-C6-001`: a bare `..`; read 13 Nov)

  The handling proposed by aneeshads on 13 Nov, which **Vijay agreed to**, is to mark them as gold contradictions: out of the count for those rules only, and re-read at the next gold refresh. So the finemath run in order passes (0/84), and so do `DA-C7-004` and the science run in order (1/198, `b6fd81dbf90b0d17`). `DB-C6-001` passes too (0/78). Still to do: the re-read at the next gold refresh.
- **The other science gold docs read on 13 Nov:**
  - `DA-A7-003` really harmed 3 docs, and `DA-C8-005` really harmed 1. Both rules were narrowed and now touch none.
  - `DA-C7-005` drops `b6fd81dbf90b0d17`, a complete short certificate. That is a real false positive, within the limit.
- **Appended Q&A in en-nemotroncc-synth:** is it a disease, or the pack's own format? `DA-D6-002` was withdrawn, because 32 of 326 gold docs have it.
- **New code D7** (facts the rewrite got wrong), and whether an ID quarantine is enough as its medicine.

## How to update this file

After each collector run:
1. Add a row for every new reading code of kind `new`. If a disease in `DISEASES.md` describes it, list it under "Not new". Otherwise give it the next free code in the nearest group.
2. Update the doc counts per pack and the bar per domain (1% of docs read).
3. When a row reaches the bar, give it the next free ID for its code. Never reuse an ID.
4. Note the date and the collector run under "Last updated".
5. For the Indic family, read Data B's latest list of proposed codes (theschoolofai/era-v5-lab#216) and add its diseases with `DB-` IDs. Check that no code means one thing for Data A and another for Data B.

## Changes

- **13 Nov 2026, 13:13 UTC:** English added. These are kunal's (mittalutkarsh/era-v5-lab#8), aneesha's (mittalutkarsh/era-v5-lab#9) and Smita's (patilvijay23/era-v5-lab#36) readings, 50 docs each, so English has 200 docs read and a bar of 2.
  - **New rules:** `DA-A8-003` (words run together) and `DA-D7-001` (facts the rewrite got wrong, new code D7, an ID quarantine).
  - **Withdrawn:** `DA-D6-002` (appended Q&A), after it changed 32 of 326 gold docs.
  - **Not new:** C4 (4 docs).
  - **Totals:** 30 rows, 24 qualifying.

- **13 Nov 2026, 11:12 UTC:** collector run with narasimhatejav's English reading (mittalutkarsh/era-v5-lab#7, en-fineweb-edu, 50 docs). Its 14 rows are all spec v1 misses (C1, D3), so the new-disease list is unchanged.
  - **Collector changes:** it now also reads files merged into theschoolofai `main`. A run at 10:55 UTC had lost Satyanarayana's megamath reading when its PR was merged there. `--docs-read` also takes `READER@DOMAIN=N`.

- **13 Nov 2026, later:** the 8 science gold docs touched by the new rules were read.
  - **Narrowed:** `DA-A7-003` (small-caps lines only) and `DA-C8-005` (a date footer must stand alone).
  - **Changed:** `DA-C7-004` now keeps captions as text.
  - **Second harm run:** only `DA-C7-004` fails alone, at 3/202, all gold contradictions. The run in order is 5/202 FAIL, and 4 of those are gold contradictions.

- **13 Nov 2026, 04:37 UTC:** collector run with Utkarsh's reading (mittalutkarsh/era-v5-lab#5) back in, at the user's request: 6 PRs, 12 files, 546 rows. Science has 200 docs read, so the bar is 2.
  - **New rules for six science diseases now at the bar:** drop cap `DA-A7-002`, small caps `DA-A7-003`, field labels `DA-A8-002`, figures `DA-C7-004`, near-empty doc `DA-C7-005`, and page numbers and footers `DA-C8-005`.
  - **A7 widened** to "Word split in extraction".
  - **Utkarsh's NEW-form-blanks** is counted as B6.
  - **Below the bar:** Aditeya's six one-doc diseases are now 1 of 200, so their next free IDs moved to `DA-C7-006` and `DA-C8-006`.
  - **Harm:** `DA-A7-003` and `DA-C7-004` fail alone (3 of 202 each), and the science run in order fails (9 of 202). Totals: 27 rows, 21 qualifying.
- **13 Nov 2026:** narasimhatejav's code reading (mittalutkarsh/era-v5-lab#6) added. Its 9 rows are all spec v1 misses (E1, E2, E3, E4, C1), so it brings no new disease.

- **12 Nov 2026:** template pages moved from C6 to C9 as `DA-C9-003` (was `DA-C6-001`), beside SEO filler, so that C6 means only the Indic family's punctuation disease.
- **12 Nov 2026:** the Indic family added, from theschoolofai/era-v5-lab#216: C6, inconsistent punctuation and formatting (ind-te-sangraha-v, 161 of 500 docs), rule `DB-C6-001`. Indic rules use the `DB-` prefix. C6 now clashes with Data A's template pages, which need a new code. 22 rows, 15 qualifying.
- **12 Nov 2026:** first version, from the collector run of 14:53 UTC. 27 rows, 18 qualifying. Codes A7, A8, A9, C6, C7, C8, C9 and D6 are proposed new codes.
- **12 Nov 2026:** NEW-toc-dot-leaders moved to "Not new". It is C1 boilerplate, and sci has a C1 rule (`DA-C1-007`), so it is a missed C1 case. 26 rows, 17 qualifying.
- **12 Nov 2026, 16:52 UTC:** collector run, no change: same 4 PRs, 490 rows and 27 candidates. Aswani, Harini, Mahesh and Utkarsh still have no reading files.
- **12 Nov 2026:** every one of the 14 qualifying new diseases has a written medicine, a unit test and a harm test.
  - **Harm, each rule alone:** every rule passes.
  - **Harm, in order:** megamath and science pass. Finemath is at 2/86, and both gold docs touched have the disease (gold contradictions).
  - **Reading docs treated:** see `medicine_math.md` and `medicine_sci.md`.
  - **IDs:** the two drafts now carry their IDs from this file (`DA-C6-001`, later `DA-C9-003`, and `DA-A7-001`).
- **12 Nov 2026:** the task restated: new means not in `DISEASES.md`. A5 ligatures, A6 quote glyphs, B1, C4 aggregated questions and C5 moved to "Not new". The blank-form disease, which was B4, is now new code B6, because B4 covers template placeholders. 21 rows, 14 qualifying.
