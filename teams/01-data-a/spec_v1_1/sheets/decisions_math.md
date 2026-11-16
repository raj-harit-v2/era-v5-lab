# decisions_math: Spec v1.1 math candidates and what to do with each

**Draft, 12 Nov.** A first pass from the readers' notes and the cleaned text at their offsets. Nothing here is decided until the hand check of the examples is done.

- **Task.** A medicine and a harm test for each **new** disease above 1%. New means not in `diagnosis/DISEASES.md`, the spec v1 list. Codes and IDs are in `NEW_DISEASES.md`.
- **Inputs.** The math reading audits: pyru (Ramesh), 199 finemath docs, mittalutkarsh/era-v5-lab#2. Satyanarayana, 100 megamath docs, theschoolofai/era-v5-lab#350.
- **Docs read.** 299, so a disease needs 3 docs (1%). Both math readers have submitted, so this list is final unless their PRs change before 12 Nov 23:59 IST.
- **Rows are AI-suggested.** Every row is `source = ai`.
- **Packs and limits.** finemath has 86 gold docs and megamath 26, so the limit is `max(1, floor(1% of gold))` = 1 doc on each. Each pack is tested on its own gold set.

## New diseases

| reading code | docs | code (rule ID) | action | medicine idea | why / risk |
|---|---|---|---|---|---|
| NEW-missing-formulas | 29 (pyru 26, Satyanarayana 3) | C7 (`DA-C7-001`) | drop | Drop when a doc shows several signs of removed formulas:<br>- a line ending in `=`, `:` or a connective with nothing after it<br>- empty answer options `(A)`–`(D)`<br>- runs of `?` where a formula was<br>The harm test sets the count. | Formula images and symbols were lost when the page was turned into text, so it can't be repaired. The risk is a drop that is too eager on short worked answers. |
| NEW-flattened-formulas | 22 (pyru 20, Satyanarayana 2) | C8 (`DA-C8-001`) | drop | Drop when a doc has many runs of one-token lines (subscripts and fraction parts split one per line). | The `x2`-for-`x²` form can't be told apart from real text, so it is left alone. Many rows overlap NEW-missing-formulas (same docs). |
| NEW-seo-filler | 15 (pyru 10, Satyanarayana 5) | C9 (`DA-C9-001`); science has its own rule | drop | Drop on landing-page and spun-SEO signs:<br>- tutoring and homework-app sales lines<br>- the title repeated many times<br>- "download this ebook"<br>- `Page n/N` markers | Prose filler, not a keyword list, so it isn't C5. |
| NEW-missing-spaces | 13 (pyru 5, Satyanarayana 8) | A8 (`DA-A8-001`) | fix | Put a space back where a lowercase word runs into a capitalised word (`[a-z]{3,}[A-Z][a-z]{2,}`), on prose lines only. | Could split camelCase in code and names such as `McDonald`. The harm test decides. |
| NEW-merged-table-cells | 11 (pyru 10, Satyanarayana 1) | C8 (`DA-C8-002`); science has its own rule | drop | No safe repair: the columns are gone. Drop a doc with a line of 20+ tokens that are 80% numbers or operators. | It treats 3 of 11; no gold doc has such a line. |
| NEW-template-pages | 9 (pyru 8, Satyanarayana 1) | C9 (`DA-C9-003`; it was C6, which is now the Indic family's code) | drop | Drop number, unit and percent calculator pages, matched by their fixed headings or one value repeated in the headings. | Written and tested: finemath 1/86, megamath 0/26, and it catches 8 of 9 reading docs. |
| NEW-ai-generated-text | 8 (pyru) | D6 (`DA-D6-001`) | fix + drop | Fix: remove the AI summary and numbered FAQ blocks that the site added under a forum thread. Drop: whole machine-written SEO articles. | 3 of the 8 rows say "unsure". The hand check decides which rows stay. |
| NEW-missing-figures | 5 (Satyanarayana) | C7 (`DA-C7-002`) | drop | Same signs as lost formulas, plus "the figure / graph / diagram below" with nothing after it. | Qualifies on its own (5 ≥ 3). One medicine for both is an option. |

## Not new: already in DISEASES.md

| reading code | docs | DISEASES.md code | what happened |
|---|---|---|---|
| B1 | 3 (pyru) | B1 HTML entities | It is in `DISEASES.md`, so it is outside v1.1. A rule drafted as `DA-B1-101` was taken out of `medicine_math.md` on 12 Nov. Spec v1's B1 rule, `DA-B1-002`, runs on English only. |
| NEW-aggregated-questions | 4 (Satyanarayana) | C4 two documents joined | It is in `DISEASES.md`, so it is outside v1.1. |

## Open

- **Gold contradictions in finemath.** Two gold docs have the new disease that the rule touching them targets:
  - `2d328b828fa97706` has `fieldtrip.Write` (`DA-A8-001`)
  - `0f119a596e8b7f63` is a converter template page (`DA-C9-003`)

  Counted, they take finemath in order to 2/86, over the limit of 1. The proposal (aneeshads, 13 Nov) was to record them as gold contradictions, as spec v1 did for `eee25e81417bc1b7`: out of the count for these two rules only, and re-read at the next gold refresh. **Vijay agreed**, so finemath in order passes at 0/84.
- **New codes.** A7–A9, B6, C7–C9 and D6 are proposed in `NEW_DISEASES.md`. C6 is the Indic family's code, for inconsistent punctuation and formatting. The new codes need the team's agreement, an entry in `DISEASES.md`, and `CODE_ORDER` in `spec_v1/tools/build_clean.py`.
- **Where v1.1 rules run.** Readers found these diseases in v1-cleaned text, so v1.1 rules should run after the family's v1 rules.
- **Which harm run counts.** Is it the v1.1 rules alone, or all v1 + v1.1 rules in order?
- **Aliases.** Should NEW-missing-figures be folded into NEW-missing-formulas? If so, run the collector with `--alias NEW-missing-figures=NEW-missing-formulas`.
