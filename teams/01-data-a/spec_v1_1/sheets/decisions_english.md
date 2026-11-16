# decisions_english: Spec v1.1 English candidates and what to do with each

**Draft, 13 Nov.** A first pass from the readers' notes and the cleaned text at their offsets. Nothing here is decided until the hand check of the examples is done.

- **Task.** Write a medicine and a harm test for each **new** disease above 1%. New means not in `diagnosis/DISEASES.md`. Codes and IDs are in `NEW_DISEASES.md`.
- **Inputs.** Four English audits, 50 docs each, so 200 docs read and a bar of **2 docs**:

  | reader | pack | PR | rows | source |
  |---|---|---|---|---|
  | narasimhatejav | en-fineweb-edu | mittalutkarsh/era-v5-lab#7 | 14 | manual |
  | kunal | en-nemotroncc-synth | mittalutkarsh/era-v5-lab#8 | 16 | ai, each checked by the reader |
  | aneesha | en-nemotroncc | mittalutkarsh/era-v5-lab#9 | 52 | manual |
  | Smita | en-dclm | patilvijay23/era-v5-lab#36 | 22 | see the PR |

  narasimhatejav's 50 docs aren't the `pick_docs.py` rows.
- **Limits.** en-nemotroncc-synth has 326 gold docs, a limit of 3. en-nemotroncc has 129, a limit of 1.

## New diseases with 2 or more docs

| reading code | docs | code (rule ID) | action | medicine idea | why / risk |
|---|---|---|---|---|---|
| NEW-factual-error | 4 (kunal), plus 2 wrong answers from NEW-appended-qa | D7, proposed (`DA-D7-001`) | drop | Quarantine the 6 confirmed doc IDs, as spec v1 does for confirmed records (`DA-D1-001`, `DA-F1-006`). | Nothing in the text marks a wrong fact; finding others needs a fact check or a model. Chosen by aneeshads, 13 Nov. Its harm test passes trivially. |
| NEW-appended-qa | 3 (kunal) | D6 (`DA-D6-002`, **withdrawn**) | none | A rule removing trailing `Question: … Answer: …` lines caught all 3 reading docs, but changed **32 of 326** gold docs, against a limit of 3. | The 32 gold docs end in ordinary, correct Q&A; it is part of this synthetic pack, and the gold readers marked it clean. No text signal separates kunal's docs: the answer-support score is 0.67, 1.00 and 1.00 for his, and 0.50 to 1.00 for gold. His 2 wrong answers went to `DA-D7-001`, and the third is correct. Withdrawn by aneeshads, 13 Nov. The team to rule whether appended Q&A is a disease. |
| NEW-missing-spaces | 2 (aneesha) | A8 (`DA-A8-003`); math and science have their own | fix | Put the space back after a full stop between a lowercase word and a capitalised one (`choose.Compose`). | URLs, abbreviations and code are left. `awhile`, the other reading doc, is an English word and stays. |

## Not new: already in DISEASES.md

| reading code | docs | DISEASES.md code | what happened |
|---|---|---|---|
| C4 | 4 (kunal) | C4 two documents joined | Outside v1.1. Spec v1 has no English C4 rule, so this is a gap in spec v1's scope. kunal notes it likely needs a model or classifier. |

## Below the bar: 1 doc of 200

There are 23 codes with one doc each, so no medicine:
- **kunal:** NEW-missing-code. It would have qualified with only PRs #7 and #8 (100 docs read).
- **Smita:** NEW-bibtex-record.
- **aneesha (21):**
  - NEW-abstract-with-no-paper-behind-it
  - NEW-ad-disguised-as-an-article
  - NEW-clickbait-and-promotional-tone
  - NEW-footnote-whose-main-content-is-missing
  - NEW-grammar-error
  - NEW-header-details-stripped
  - NEW-heading-stuck-to-the-paragraph
  - NEW-hyphen-split-words
  - NEW-leftover-hyphens-from-line-breaks
  - NEW-mismatched-quotation-marks
  - NEW-missing-space-after-a-full-stop
  - NEW-old-place-name-spelling
  - NEW-pronoun-slip
  - NEW-spliced-sentences
  - NEW-squashed-into-prose
  - NEW-text-describing-a-missing-video
  - NEW-text-with-the-link-gone
  - NEW-too-few-words
  - NEW-two-pieces-stuck-together-with-no-space
  - NEW-two-words-stuck-together
  - NEW-typos-and-grammar-errors

Some of aneesha's names may be the same disease as a code above, and could be counted together with `--alias` if the team agrees:
- NEW-missing-space-after-a-full-stop, NEW-two-words-stuck-together, NEW-two-pieces-stuck-together-with-no-space and NEW-heading-stuck-to-the-paragraph look like NEW-missing-spaces (A8).
- NEW-hyphen-split-words and NEW-leftover-hyphens-from-line-breaks look like each other: line-end hyphens, A7 in science. Together they would make 2 docs, which reaches the bar.

These merges aren't made yet; they need the team's agreement.

## Spec v1 misses

- **C1:** 38 docs.
- **C3:** 6.
- **B4:** 3. kunal: `DA-B4-007` doesn't match "The user / The speaker / The text discusses".
- **D3:** 3.
- **B1:** 1.
- **F1:** 1.
- **Harm row:** one, for `DA-C2-003` (Smita).

These are about spec v1 rules, not Spec v1.1.

## Open

- **New code D7** (facts the rewrite got wrong): team agreement.
- **Appended Q&A** in en-nemotroncc-synth: is it a disease, or the pack's own format? `DA-D6-002` was withdrawn.
- **The aliases above:** they decide whether line-end hyphens reach the English bar.
- **narasimhatejav's docs:** keep his 50 docs, which aren't the `pick_docs.py` rows, or redo the reading on the right rows.
