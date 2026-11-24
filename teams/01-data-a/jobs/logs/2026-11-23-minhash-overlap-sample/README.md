# MinHash + LSH overlap on the cleaned sample (23 Nov 2026)

Evidence for `dedup/minhash_overlap.py` (#744). Inputs: the 47 train parts of the 5 Nov cleaned sample (the local copy
has no `ind-ta-sangraha-v` train part), plus the 38 held-out parts for `heldout_check.json`. IDs and counts only.

- `minhash_overlap.log`: the first full run, from scratch (39.6 min on 2 cores).
- `overlap_summary.json`, `minhash_overlap_rerun.log`, `config.json`: the final code on the same parts, step 1 reused
  from `work/` (stage times and `peak_rss_mb_after_stage` for the later stages).
- `agreement.json`: `minhash_agreement.py` against TSAI's 5 Nov exact run: 2,550/2,550 H2 pairs, identical groups,
  `dedup.py` remove list byte-identical (1,317 rows).
- `heldout_check.json`, `heldout_reference.py`: exact held-out ↔ train reference without MinHash; 66/66 pairs at
  Jaccard >= 0.80 are MinHash candidates.
