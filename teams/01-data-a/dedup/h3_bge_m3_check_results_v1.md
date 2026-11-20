# H3 encoder check, v1b: BGE-M3 against LaBSE on Sanskrit, Hindi and Odia (16 Nov 2026)

**What:** the same script and settings as the LaBSE check of 15 Nov (`h3_labse_check_results_v1.md`), with
`--model BAAI/bge-m3`: sentences of at least 20 characters, at most 16 per document, `max_seq_length` 128, mutual best
match, coverage rule 0.6. Same data: FLORES-200 devtest (1,012 sentences; 126 blocks of 8) and the 433 `ind-sa-fw2`
same-page pairs. Run by Kunal Sinha on a laptop CPU, 7,255 s (LaBSE: 863 s). Measurement only: nothing removed.
Numbers from `out/bge_m3/summary.json` and `pair_scores.csv`; no text in this note.

## FLORES: sentences

| Pair | P@1 (→ / ←), LaBSE | P@1, BGE-M3 | True-pair cosine, median: LaBSE / BGE-M3 | Best wrong, median: LaBSE / BGE-M3 | True pairs ≥ 0.7: LaBSE / BGE-M3 |
|---|---|---|---|---|---|
| Sanskrit–English | 0.980 / 0.952 | 0.993 / 0.987 | 0.687 / 0.742 | 0.405 / 0.566 | 45.9% / 71.4% |
| Sanskrit–Hindi | 0.970 / 0.835 | 0.992 / 0.988 | 0.637 / 0.784 | 0.408 / 0.575 | 33.8% / 83.9% |
| Hindi–English | 1.000 / 1.000 | 1.000 / 1.000 | 0.860 / 0.841 | 0.490 / 0.584 | 99.0% / 98.2% |
| Odia–English | 1.000 / 1.000 | 0.999 / 0.999 | 0.875 / 0.801 | 0.479 / 0.572 | 99.8% / 93.1% |

BGE-M3 finds Sanskrit translations more often and scores them higher. Its cosines are higher for everything, though:
the median wrong match rises from about 0.41 to 0.57, so the gap between a translation and the best wrong sentence
narrows (Sanskrit–English: 0.28 with LaBSE, 0.18 with BGE-M3).

## FLORES: 8-sentence pseudo-documents qualifying at coverage ≥ 0.6

| Sentence threshold | 0.5 | 0.6 | **0.7 (draft)** | 0.8 |
|---|---|---|---|---|
| Sanskrit–English, LaBSE / BGE-M3 | 96.0% / 100% | 77.0% / 100% | **29.4% / 81.7%** | 4.8% / 4.8% |
| Sanskrit–Hindi, LaBSE / BGE-M3 | 88.9% / 100% | 55.6% / 100% | **19.0% / 95.2%** | 0% / 22.2% |
| Hindi–English, LaBSE / BGE-M3 | 100% / 100% | 100% / 100% | **100% / 100%** | 99.2% / 83.3% |
| Odia–English, LaBSE / BGE-M3 | 100% / 100% | 100% / 100% | **100% / 100%** | 100% / 40.5% |
| Any pair, other block (both) | 0% | 0% | 0% | 0% |

With BGE-M3, one threshold (0.7) finds 82–100% of translated blocks in every language pair; with LaBSE, Sanskrit
needs about 0.5. The mutual-best rule still keeps different blocks apart at every threshold.

## Real `ind-sa-fw2` same-page pairs qualifying (read by hand)

| Sentence threshold | LaBSE | BGE-M3 |
|---|---|---|
| 0.5 | 7 (4 translations, 3 not) | 27 (not read) |
| 0.6 | 4 (2, 2) | 16 (not read) |
| **0.7** | **1 (1, 0)** | **8 (6 translations, 2 not)** |
| 0.8 | 0 | 2 (2, 0) |

BGE-M3 at 0.7, by doc_id:
- **Translations (6):** `602d649b7ca0cc34`, `a4c2e787200c9aaa`, `ad0757f87d86972c`, `6155338a1dab37ff` (sentence
  exercises or essays with line-by-line English or Hindi), `708c90d81397fc22` (a verse with an English explanation),
  `3fc54f50af2fe5ec` (an essay with a loose English rendering).
- **Not translations (2):** `d0479a80829a2dc1` (a news story with the tweet it reports; LaBSE also passes it at 0.5),
  `c0a1c98ea5fa9e8e` (an essay whose "Translation in English" lines are about something else).

Head cosine (first 4 sentences, the retrieval step) of these same-topic pages rises from a median of 0.31–0.44
(LaBSE) to 0.47–0.59 (BGE-M3), so with `doc_floor` 0.5 far more pairs would go on to verification.

## What this means for H3 (H3-h, H3-i)

1. **BGE-M3 removes the need for a separate Sanskrit threshold.** At the draft's 0.7 it finds 82% (Sanskrit–English)
   and 95% (Sanskrit–Hindi) of translated blocks, against LaBSE's 29% and 19%, and Hindi and Odia stay at 100%.
2. **Precision on real pages is similar to LaBSE at a lower threshold.** At 0.7, 6 of BGE-M3's 8 matches are
   translations; LaBSE at 0.5 gives 4 of 7. Both pass the news-plus-tweet page.
3. **Its retrieval floor would need retuning.** Its cosines run about 0.15 higher for unrelated text, so
   `doc_floor` 0.5 lets through most same-topic pages; something near 0.6 should be measured.
4. **It is about 8 times slower on CPU** (7,255 s against 863 s; 24 layers against 12). On TSAI's GPU this matters
   for the full data, not for a sample.
5. **Still open:** a margin score with LaBSE (it may close the Sanskrit gap without the cost), and a Sanskrit reader's
   labels on the 16–27 BGE-M3 candidates at 0.5–0.6 before any threshold is final (E5d).

Command (from `Wk2/h3`): `python labse_check.py --pairs out/known_pairs.parquet --model BAAI/bge-m3 --out out/bge_m3`
(`--progress` prints stage times; `--max-pairs 100` shortens the page-pair part). The model is about 2.3 GB.
