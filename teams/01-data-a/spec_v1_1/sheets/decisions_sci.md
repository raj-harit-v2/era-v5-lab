# decisions_sci: Spec v1.1 science candidates and what to do with each

**Draft, 12 Nov; updated 13 Nov with Utkarsh's reading.** A first pass from the readers' notes and the cleaned text at their offsets. Nothing here is decided until the hand check of the examples is done.

- **Task.** Write a medicine and a harm test for each **new** disease above 1%. New means not in `diagnosis/DISEASES.md`, the spec v1 list. Codes and IDs are in `NEW_DISEASES.md`.
- **Inputs.**
  - Aditeya's sci-finepdfs audit: 100 docs (rows 101–200 of the shuffle), mittalutkarsh/era-v5-lab#3. Every row is `source = ai`.
  - Utkarsh's sci-finepdfs audit: 100 docs (rows 1–100), mittalutkarsh/era-v5-lab#5. Every row is `source = manual`. It was added on 13 Nov, at the user's request.
- **Bar.** 200 docs read, so a disease needs **2 docs**.
- **Pack and limit.** sci-finepdfs has 202 gold docs, so the limit is `max(1, floor(1% of 202))` = 2 docs.

## New diseases with 2 or more docs

| reading code | docs | code (rule ID) | action | medicine idea | why / risk |
|---|---|---|---|---|---|
| NEW-page-artifact | 9 (Utkarsh) | C8 (`DA-C8-005`) | fix | Delete `Page N` / `Page N of M` lines, an unfilled `Page No. – Page No.`, a date-only line that repeats, and a lone page number as the first line, the last line after a finished sentence, or between two lines of running text. | It treats 8 of 9. Contents-page numbers next to headings are left. The first version removed signature dates in gold doc `8a2493cdf33f9a38`. A date footer must now stand alone between blank lines, and it touches 0/202. |
| NEW-underscore-blanks + NEW-form-blanks | 7 (Aditeya 2, Utkarsh 5) | B6 (`DA-B6-001`) | drop | Drop a doc whose underscore runs make up 30% or more of its text (a blank form). | B4 covers template placeholders, not form lines, so this is new. It catches Aditeya's 2 but none of Utkarsh's 5, whose blanks are a small part of the form. The rule isn't changed. |
| NEW-hyphen-split-words | 3 | A7 (`DA-A7-001`) | fix | Join a word broken at a line end: `stereo- scopic` becomes `stereo-scopic`. The hyphen is kept and the space goes. Suspended hyphens (`pre- and post-test`) are left alone. | Written and tested: 1/202 on gold, and it catches 3 of 3 reading docs. Its one gold hit has the disease. |
| NEW-merged-table-cells | 3 | C8 (`DA-C8-003`); math has its own rule | fix | Split a table cell that holds two numbers into the empty cell next to it (`\| 332 50.4 \|  \|` → `\| 332 \| 50.4 \|`). | Shifted rows and tables flattened into lines can't be put back. It treats 1 of 3. |
| NEW-missing-table-data | 3 | C7 (`DA-C7-003`) | fix | Cut a dangling "… with the following members." when no list follows. | The content is gone; cutting the empty frame is the most that can be done. Headings with no data are left. It treats 1 of 3. |
| NEW-missing-spaces | 3 (Aditeya 1, Utkarsh 2) | A8 (`DA-A8-002`); math has its own rule | fix | Put a space back in front of a listed field label glued to the word before it (`MACEDuration:`). | Capitals run together (`NEILABERCROMBIEGOVERNOR`) and joined URLs need a word list, so they are left. It treats 1 of 3. 0/202 on gold. |
| NEW-reading-order | 2 | C8 (`DA-C8-004`) | fix | Put numbered steps that are out of order (3, 5, 4) back in order. | Scrambled sentences can't be put back. It treats 1 of 2. |
| NEW-seo-filler | 2 | C9 (`DA-C9-002`); math has its own rule | drop | Start from the math rule, plus the "download / access free ebook" pages with `Page n/N` markers. | Folding NEW-spun-text in would make it 3. |
| NEW-drop-cap-split | 2 (Utkarsh) | A7 (`DA-A7-002`) | fix | Join a lone capital letter to the lowercase line after it (`D` / `eveloping` → `Developing`). `A` and `I` are left. | A lost drop cap (`t. Thomas`) can't be put back. It treats 1 of 2. 0/202 on gold. |
| NEW-small-caps-split | 2 (Utkarsh) | A7 (`DA-A7-003`) | fix | Join the split first letter back (`F OODS` → `FOODS`) on lines set in small caps: no lowercase letter, more split pairs than whole capital words, and no letter right after an apostrophe. | The first version harmed 3 gold docs (`G HIST` → `GHIST`, `A COMPREHENSIVE` → `ACOMPREHENSIVE`, `CECILY’S ENGLISH` → `CECILY’SENGLISH`). After narrowing: 0/202, and it treats 2 of 2. |
| NEW-missing-figures | 2 (Utkarsh) | C7 (`DA-C7-004`); megamath has its own rule (drop) | fix | Replace each Markdown image link to a bare `image` / `image1.png` with its caption as text, and delete links with no caption. | **FAIL: 3/202**, all 3 gold contradictions: each has empty image links. The first version deleted their captions too, so it now keeps them. It treats 2 of 2. It passes if the gold contradictions are left out. |
| NEW-near-empty | 2 (Utkarsh) | C7 (`DA-C7-005`) | drop | Drop a doc under 250 characters. | 1/202 PASS, but the gold doc dropped (`b6fd81dbf90b0d17`, a complete 220-character certificate) is a real false positive. Length alone can't tell it from the reading docs (96 and 233 characters). It treats 2 of 2. |

## New diseases with 1 doc: below the bar

With 200 docs read, these need a second doc to qualify:
- **Aditeya:**
  - NEW-detached-diacritics (A9, `Mo´nica`)
  - NEW-figure-only-doc (C7)
  - NEW-orphan-figure-labels (C7)
  - NEW-split-superscripts (C8)
  - NEW-spun-text (C9)
  - NEW-generated-image-captions (D6)
- **Utkarsh:**
  - NEW-empty-table-rows
  - NEW-huge-tables
  - NEW-latex-residue
  - NEW-prose-in-code-fence
  - NEW-scrambled-vertical-text

  The nearest code for each is in `NEW_DISEASES.md`.

## Not new: already in DISEASES.md

| reading code | docs | DISEASES.md code | what happened |
|---|---|---|---|
| NEW-pdf-ligatures | 5 | A5 wrong normal form (ligatures, as in math's `DA-A5-001`) | Outside v1.1. A rule drafted as `DA-A5-101` was taken out of `medicine_sci.md` on 12 Nov. Utkarsh also marks 4 ligature docs as missed A5. |
| NEW-toc-dot-leaders | 2 | C1 boilerplate | Outside v1.1. A rule drafted as `DA-C1-101` was taken out of `medicine_sci.md` on 12 Nov. |
| NEW-pdf-quote-glyphs | 1 | A6 wrong glyphs (as in math's `DA-A6-001`) | Outside v1.1. |
| C5 | 1 | C5 lists of keywords or links | Outside v1.1. |
| NEW-personal-names-ages | 1 | F1 personal data | Outside v1.1. Type and position only. |

## Spec v1 misses in Utkarsh's reading

Utkarsh has 17 `missed` rows in 15 docs. They were checked on 13 Nov against the cleaning job's `specv1.md` (`g1-specv1`, theschoolofai/era-v5-lab#244). No sci rule changes any of the 15 docs. They are not Spec v1.1 work, but they explain the misses:
- **A1 (soft hyphen U+00AD):** `DA-A1-006` removes only U+FEFF and U+200B.
- **A5 (ligatures):** there's no sci A5 rule. Folding is math-only (`DA-A5-002`).
- **B4 (mail-merge field):** `DA-B4-013` converts only a few converter labels.
- **C1, C2, D1, F1:** `DA-C1-007` (the repeated-header part), `DA-C2-004`, `DA-D1-001` and `DA-F1-006` act only on doc IDs listed from the Week 1 pack, so they do nothing on the sample. That is Utkarsh's open question 1.

## Open

- **New codes.** See `NEW_DISEASES.md`.
- **Fold NEW-spun-text into NEW-seo-filler?** If so, run the collector with `--alias NEW-spun-text=NEW-seo-filler`.
- **Gold contradictions** (`DA-C7-004`'s 3 docs and `DA-A7-001`'s `920855df51f37db8`): Vijay agreed to marking them, so they are left out of the count, and the science run in order passes at 1/198. They are to be re-read at the next gold refresh.
- **`DA-C7-005`'s false positive:** keep the rule as it is, or find a sign other than length that separates a lost body from a short complete doc.
