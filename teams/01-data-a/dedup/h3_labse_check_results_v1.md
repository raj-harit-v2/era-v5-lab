# H3 encoder check, v1: LaBSE on Sanskrit, Hindi and Odia (15 Nov 2026)

**What:** `labse_check.py` with `sentence-transformers/LaBSE`, H3's settings from `h3_design_v1.md` (sentences of at
least 20 characters, at most 16 per document, `max_seq_length` 128; two sentences align when each is the other's best
match and their cosine is at least the sentence threshold; a pair qualifies at coverage >= 0.6). Run by Kunal Sinha on
CPU, 863 s. Measurement only: nothing removed. Numbers from `out/labse/summary.json`; no text in this note.

**Data:**
- **True translations:** FLORES-200 devtest, 1,012 sentences in English, Hindi, Sanskrit and Odia (an evaluation set:
  read to test the encoder, never training data). Pseudo-documents: 126 blocks of 8 consecutive sentences; a block
  against its translation (true pair) and against another block (other pair).
- **Real same-page pairs:** 433 raw `ind-sa-fw2` documents split into Sanskrit lines and the lines `DB-H3-001` calls
  translations (`build_known_pairs.py`). Mostly the same topic in two languages, not translations.

## Results

### Sentences (FLORES)

| Pair | P@1 (→ / ←) | True-pair cosine, median (p05–p95) | Best wrong cosine, median (p95) | True pairs ≥ 0.7 |
|---|---|---|---|---|
| Hindi–English | 1.000 / 1.000 | 0.860 (0.771–0.923) | 0.490 (0.603) | 99.0% |
| Odia–English | 1.000 / 1.000 | 0.875 (0.784–0.930) | 0.479 (0.596) | 99.8% |
| Sanskrit–English | 0.980 / 0.952 | 0.687 (0.391–0.858) | 0.405 (0.547) | 45.9% |
| Sanskrit–Hindi | 0.970 / 0.835 | 0.637 (0.330–0.842) | 0.408 (0.576) | 33.8% |

LaBSE **finds** Sanskrit translations (P@1 0.95–0.98 against English), but its cosines for them are much lower than
for Hindi or Odia: the median true Sanskrit pair sits just under H3's 0.7.

### 8-sentence pseudo-documents (FLORES): share qualifying at coverage ≥ 0.6

| Sentence threshold | 0.5 | 0.6 | **0.7 (draft)** | 0.8 |
|---|---|---|---|---|
| Hindi–English, true | 100% | 100% | **100%** | 99.2% |
| Odia–English, true | 100% | 100% | **100%** | 100% |
| Sanskrit–English, true | 96.0% | 77.0% | **29.4%** | 4.8% |
| Sanskrit–Hindi, true | 88.9% | 55.6% | **19.0%** | 0% |
| Any pair, other block | 0% | 0% | 0% | 0% |

The mutual-best rule keeps different blocks apart at every threshold. With the draft's 0.7, H3 would find nearly all
Hindi and Odia translations but only 29% of Sanskrit–English and 19% of Sanskrit–Hindi ones.

### Real `ind-sa-fw2` same-page pairs: pairs qualifying, and what they are (read by hand)

| Sentence threshold | Qualifying | Real translations | Not translations |
|---|---|---|---|
| 0.5 | 7 of 433 | 4 (a sentence-translation exercise with Hindi, a forum post with English renderings, two essays with English translations) | 3 (a news story with the tweet it reports, a software blog with English product names, two essays on one topic) |
| 0.6 | 4 | 2 | 2 |
| 0.7 | 1 | 1 | 0 |

Head cosine (first 4 sentences, the retrieval step) of these same-topic pages: median 0.31–0.44, p95 0.62–0.71 by
kind; a large share pass `doc_floor` 0.5 into verification, where the sentence rule rejects almost all of them.

## What this means for H3

1. **Odia and Hindi: LaBSE is fine** with the draft settings (H3-i answered for Odia: no weakness).
2. **Sanskrit needs its own sentence threshold** (H3-h). At 0.7 H3 misses about 70–80% of Sanskrit translations; at
   0.5 it finds 89–96%, but on real pages 3 of its 7 matches are not translations. No single threshold fits both
   languages.
3. Options to test next, in order of cost:
   - a threshold per language pair (for example 0.7 for Hindi and Odia, 0.55 for Sanskrit), checked on a larger
     hand-labelled sample of real pages;
   - a margin score instead of a plain cosine (a pair's cosine relative to each sentence's nearest neighbours, as in
     bitext mining), which adapts to languages whose cosines run low;
   - another encoder for Sanskrit, with the same script (`--model BAAI/bge-m3` or a multilingual-e5 model).
4. **Positives from real pages are rare:** 4 real translations in 433 same-page pairs of the week-1 pack. A Sanskrit
   reader's labels on the candidates are needed before any threshold is final (E5d).
5. **Speed:** about 23 sentences a second on a laptop CPU; consistent with TSAI's rule that the H3 job runs batched
   on a GPU.

Scripts and outputs: `Wk2/h3/` (`build_known_pairs.py`, `labse_check.py`, `README_h3_checks.md`, `out/` with text,
kept out of the repo).
