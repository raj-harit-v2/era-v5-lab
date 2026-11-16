# Native Indic share: Data B's proposal for Gate 2 (v1.1, draft of 12 Nov 2026, numbers updated 14 Nov)

Deliverable of #217 ("Our proposal for the native Indic share, by Thu 12 Nov") and the first item of #216. TSAI decides
the share at Gate 2 (14 Nov) and said that a pack with few clean documents is important evidence for it (G2, 31 Oct).
This file brings that evidence and a proposal. **What is measured and what is a proposed value is kept apart below.**
Only counts and pack IDs are used; no document text. The gold numbers are those of the gold sets rebuilt from the readers'
sheets of 11 Nov (#229, #362); they replace the 2 Nov gold (1,957 documents) that v1 used. The translation ratings are those of
`translation/quality_v1.md` and `agreement_v1.md` of 14 Nov (Tamil now has both sheets, #432 and #438; #440 updates the two files); they are not final.

## 1. What "native Indic share" means here

The Indic text in the mix is of three kinds, and Data B has measured each:

| Kind | Packs | How it is measured |
|---|---|---|
| **Native**: a document written in the language's own script by people | `fw2`, `hplt`, `indiccorp`, `sangraha-v` | gold sets: documents that two readers both called clean |
| **Translated**: machine-translated text | the four `sangraha-s` packs (#212) | translation rating, 1 to 5, by native readers (due Thu 12 and Fri 13 Nov, #216) |
| **Romanised**: an Indian language in Latin letters (D2) | any pack | the document rule and the cap of #213 |

**Native share of a language = tokens of native documents ÷ all Indic tokens of that language in the mix**, after
cleaning and after the romanised cap. Counted in tokens, as TSAI's rule for the romanised cap (5 Nov) counts them,
because the data mix is set in tokens. (`sangraha-v` and `sangraha-s` are Sangraha's verified and synthetic splits; only
`sangraha-s` = translated is stated in #212. The other packs are read as native.)

## 2. Evidence (all measured, 22 sample packs of 500 documents each)

### 2.1 Clean documents in each pack (gold sets, `gold/gold_coverage.csv`)

"Clean" = both readers marked the document clean, and nobody disputed it. This is a **lower bound** of the clean share:
disputed documents are left out (ind-hi-hplt 102, ind-mr-fw2 45, ind-te-sangraha-v 40), and a pack with one reader has no gold
set, so it cannot be measured.

| Pack | Readers | Labelled | Gold (clean) | Clean | Disputed |
|---|---:|---:|---:|---:|---:|
| ind-hi-indiccorp | 2 | 500 | 425 | 85.0% | 0 |
| ind-bn-fw2 | 3 | 500 | 227 | 45.4% | 17 |
| ind-hi-sangraha-v | 3 | 500 | 219 | 43.8% | 3 |
| ind-hi-fw2 | 3 | 500 | 218 | 43.6% | 16 |
| ind-mr-fw2 | 3 | 500 | 158 | 31.6% | 45 |
| ind-ta-sangraha-v | 2 | 500 | 141 | 28.2% | 0 |
| ind-bn-sangraha-v | 3 | 500 | 137 | 27.4% | 7 |
| ind-kn-fw2 | 2 | 500 | 115 | 23.0% | 0 |
| ind-kn-sangraha-v | 3 | 500 | 99 | 19.8% | 4 |
| ind-mr-sangraha-v | 2 | 500 | 99 | 19.8% | 0 |
| ind-gu-fw2 | 2 | 500 | 80 | 16.0% | 0 |
| ind-te-sangraha-v | 3 | 500 | 80 | 16.0% | 40 |
| ind-sa-fw2 | 2 | 500 | 71 | 14.2% | 0 |
| ind-hi-hplt | 4 | 500 | 37 | 7.4% | 102 |
| ind-hi-sangraha-s | 2 | 500 | 24 | 4.8% | 0 |
| ind-te-sangraha-s | 2 | 500 | 24 | 4.8% | 0 |
| ind-kn-sangraha-s | 3 | 500 | 22 | 4.4% | 5 |
| ind-te-fw2 | 4 | 500 | 17 | 3.4% | 1 |
| ind-ta-fw2, ind-ta-sangraha-s, ind-ml-fw2, ind-or-fw2 | 1 | 500 | 0 | not measurable | 0 |

### 2.2 By source and by language (the 18 packs with two or more readers: 9,000 documents, 2,193 clean, 24.4%)

| Source | Packs | Clean |
|---|---:|---:|
| indiccorp | 1 | 85.0% |
| sangraha-v | 6 | 25.8% |
| fw2 | 7 | 25.3% |
| hplt | 1 | 7.4% |
| **sangraha-s (translated)** | **3** | **4.7%** (70 of 1,500) |

| Language | Packs | Labelled | Clean | Note |
|---|---:|---:|---:|---|
| hi | 5 | 2,500 | 36.9% | one pack alone is 85%; without indiccorp 24.9% (498 of 2,000) |
| bn | 2 | 1,000 | 36.4% |  |
| ta | 1 | 500 | 28.2% | ta-fw2 and ta-sangraha-s not measurable |
| mr | 2 | 1,000 | 25.7% |  |
| gu | 1 | 500 | 16.0% |  |
| kn | 3 | 1,500 | 15.7% |  |
| sa | 1 | 500 | 14.2% |  |
| **te** | **3** | **1,500** | **8.1%** | **121 clean documents in three packs (17, 24, 80)** |
| ml, or | 0 | | not measurable | one reader each |

### 2.3 Romanised (`romanised/romanised_policy_v1.md`, #213)
The word-list detector finds 0 mostly-romanised documents in the 11,000 sample documents, so the cap share is 0% for
every language (12.1 million tokens). Romanised segments inside native documents are 0.025% of tokens. Proposed cap there:
1% per language (option B).

### 2.4 Translated
Ratings of 14 Nov (`translation/quality_v1.md`, `agreement_v1.md`, 1 to 5 on TSAI's rubric; from the #212 review pack; the Tamil row is from #432 and #438, as updated in #440):

| Language | Readers | Documents rated | Mean score | Agreement (within 1 point; at least 20 shared; 25 per language now) |
|---|---:|---:|---:|---|
| kn | 2 | 50 | 3.31 | 19 of 25 (76%): **fails** (the second reader scores lower on 21 of 25, never higher) |
| ta | 2 | 50 | 3.21 | 21 of 25 (84%): passes |
| te | 1 | 38 | 2.37 | not checkable: second sheet not in |
| hi | 0 | none | none | not checkable: no sheets |

Under the rating condition of Option B below (mean 3.5 or higher, and agreement of 80% or more), **no language qualifies
today** (Kannada is under 3.5 and fails agreement; Tamil agrees but its mean is under 3.5; Telugu has one reader; Hindi has no sheets), so translated text would be 0% in every language for now. The Tamil row comes from #440, which is not merged yet: once it is, check this table against the merged `quality_v1.md` and `agreement_v1.md` (dated 14 Nov, sheets of 14 Nov 09:50 IST). Both files are updated when more sheets come in.

### 2.5 What the cleaning code does to the clean documents
The filters of #214 (D1 script share, A1 invisible characters, G1 broken vowel signs) change or drop 0 of the gold
documents (the rebuilt gold) in each of the six packs tested so far (ind-bn-fw2, ind-bn-sangraha-v, ind-hi-sangraha-s, ind-kn-fw2,
ind-kn-sangraha-s, ind-te-sangraha-s). So the clean counts above are not reduced by these filters; the other 12 packs (all with gold) are not run yet, because their pack files are missing.

## 3. What the evidence says
1. **Translated text is the least clean source.** 4.7% clean in `sangraha-s`, against 25.3% in `fw2` and 25.8% in
   `sangraha-v`. The next lowest is `hplt` at 7.4%, but 102 of its documents are disputed and left out, so that is a
   lower bound. This is the "pack with few clean documents" evidence TSAI asked for. It is a quality signal for the
   readers' notion of clean, not yet the translation rating.
2. **Telugu is the language with the least clean text: 8.1% over three packs** (fw2 3.4%, sangraha-s 4.8%, sangraha-v 16.0%).
   It is below the source average in `fw2` (25.3%) and `sangraha-v` (25.8%); in `sangraha-s` it matches the other languages (4.4% to 4.8%
   in each of the three packs). No share fixes this, and filtering alone cannot: at the sample rate 500 documents leave about 40
   clean ones.
3. **The clean share depends on the source** (3.4% to 85.0%), so one global share would be wrong for some languages.
4. **Four packs cannot be judged (one reader): Malayalam, Odia, and two Tamil packs.**

## 4. Proposal

Data B's proposal as posted on #216 is Option B below, with Indic at least 12% of all pre-training tokens (the S05 Indic floor; V4 used 8%).

*Measured:* sections 2 and 3. *Proposed (my values, not derived from the data: the data gives the direction and the
per-language conditions, TSAI sets the numbers):*

| | Option A: native only | **Option B (proposed)** | Option C: permissive |
|---|---|---|---|
| Native share of each language's Indic tokens | 100% | **at least 90%** | at least 80% |
| Romanised (D2), within the above | 0% | **at most 1%** (#213 option B) | at most 2% (#213 option C) |
| Translated (`sangraha-s`) | 0% | **at most 9%, and only when the rating condition holds** | at most 18% |
| What it costs in the sample | drops the 3 measured `sangraha-s` packs: 70 of 2,193 clean documents (3.2%) | the same, but allows part of it back where rated well | keeps all of it |

Rating condition for translated text in Option B (scale 1 to 5, #212; both are proposed thresholds):
- a language's translated share may be used only if its mean rating is **3.5 or higher** and the two readers agree
  within 1 point on at least 80% of the shared documents, at least 20 (each language has 25 shared; the agreement rule of #216);
- a mean of **4.0 or higher** allows the full 9%; from 3.5 up to 4.0, **at most 4.5%** (half);
- a language with no rating, one reader, or a mean under 3.5 gets **0%** translated: nothing then shows it is safe.

Per-language rules:
- Languages short of clean text (Telugu now; ml, or and ta-fw2 once they have gold) are **not topped up with translated
  text**. Their clean supply is reported to #215 (new sources and licences) as the gap to fill.
- The share is checked per language on the training corpus, in tokens, with the project tokenizer (BrahmicTokenizer-131K
  is the stand-in, as in `token_share.py`).

**Why B and not A:** A throws away the one source that may be good (if the Hindi, Kannada, Tamil or Telugu ratings come
back high), at a cost of 3.2% of the clean gold documents. **Why not C:** at 4.7% clean, translated text is the weakest
evidence we have, and TSAI asked for a few-clean-documents pack to weigh most.

## 5. What is not known yet (so this draft will change)
- The rest of the translation ratings and the agreement checks: Telugu needs a second reader and Hindi has no
  sheets yet (2.4). Kannada's low agreement is a steady offset between its two readers, not random, so it may change once
  the readers align.
- Tokens per source for the full corpus. The sample has 500 documents per pack, so the share of translated text in the
  sample is an artefact of how it was drawn and is not used here.
- Gold for `ind-ta-fw2`, `ind-ta-sangraha-s`, `ind-ml-fw2`, `ind-or-fw2` (one reader each).
- The final tokenizer (the token share will be recomputed with it).

## 6. Where the numbers come from
`teams/02-data-b/gold/gold_coverage.csv` (sections 2.1 and 2.2); `romanised/romanised_policy_v1.md` and
`romanised/romanised_token_share_v1.csv` (2.3); #212 (2.4, the scale and the review pack); `filters/README.md` and
`filters/harm_<pack>.md` (2.5); #216 and #217 (what is asked, and when).
