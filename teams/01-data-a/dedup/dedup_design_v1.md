# Dedup design v1: How duplicates are found

**Status:** v1. [decision log](#decision-log) at the end; open items are listed before it.
**Scope:** the duplicate diseases H1–H3 of `diagnosis/DISEASES.md`, section H. Which copy survives a duplicate group is defined in `source_priority_v1.md`.

## Summary of decisions

| Topic | Decision | Status |
|---|---|---|
| H1, exact duplicates | SHA-256 of the H1 key: spec v1 `normalize.match_key`, then NFKC, casefold, whitespace collapse | Decided |
| H2, near duplicates | Exact Jaccard of every pair. Prose: word 5-grams ≥ 0.80, both ≥ 50 words. Math: ≥ 0.90 and the same numbers. Code: token 5-grams ≥ 0.85, both ≥ 20 non-blank lines. A pair from two families must pass both families' rules | Decided; code threshold under review |
| H3, another source or language | Same-language copies from another source: covered by H1/H2 within and across packs. Translations: out of scope for v1 | Agreed |
| Where dedup runs | After `clean.py` and before F2 (Clean → Dedup → F2); within each pack, across packs and across both teams (Data A and Data B) | Agreed; order with F2 set by TSAI, 12 Nov |
| Which copy survives | `source_priority_v1.md`: held-out first, licence, provenance, completeness, pack order. A survivor that F2 later removes is not replaced | Agreed |
| Hand-off to TSAI | A remove list `(pack_id, split, part, doc_id)` and `dedup_log.jsonl`; TSAI filters the cleaned data, our code never rewrites it | Agreed |
| Validation | Known pairs, threshold sweep and hand review per family, gold harm check on the diagnosis packs | Partly done |
| Result on sample v0 | 1,345 of 1,414,996 documents removed (0.095%), 0 held-out; TSAI's runs on the #244 cleaning (overlap #469, dedup #547) | Final, 17 Nov |

## H1: exact duplicates

**The H1 key** (used only for matching; the stored text is never changed), `h1_key()` in `h1_sha256.py`:
1. Spec v1 `normalize.match_key(text)` from `spec_v1/tools/normalize.py`, unchanged (spec v1 is frozen): HTML entities decoded, control and invisible characters removed, NFC with its listed folds, casefold, spaces collapsed.
2. Then Unicode NFKC, casefold, and every run of whitespace to one space. NFKC is applied here, never inside `normalize.py`, so spec v1 and G9's fingerprints are unaffected.

Two documents are H1 duplicates when the SHA-256 of their keys is equal. H1 bypasses the H2 length guards.

- **Punctuation and digits are kept** in the key on purpose: stripping them would merge math problems that differ only in a number.
- **The H1 hash never replaces `doc_id`.** `doc_id` is `sha256(utf-8 original text)[:16]`, set before cleaning and carried through unchanged; dedup never re-hashes the cleaned text.

## H2: near duplicates

**Terms.** A document's *shingles* are the set of its word 5-grams (overlapping 5-word windows of the H1 key; repeats count once). The *Jaccard similarity* of two documents is shingles in both ÷ shingles in either. Example with 3-word shingles: "the cat sat on the mat" and "the cat sat on a mat" share 2 of 6 distinct shingles, J = 0.33; compared word by word they would score 5/6 = 0.83, which is why single words are not used.

**Method: exact Jaccard of every pair** (`overlap.py`, `jaccard_matrix.py`). Each shingle is stored as a 64-bit hash (`gram_hashes` in `jaccard_matrix.py`: each word hashed once, combined per 5-word window with NumPy). The documents × shingles matrix times its transpose gives the shared count of every pair that shares a shingle, block by block. There is no sampling and no MinHash estimate, so every score is exact and is the value logged. On the 38-pack sample (1.4 million documents) this ran in 56 minutes. MinHash + LSH remains the fallback for a run that does not fit.

`overlap.py` keeps every pair at word Jaccard ≥ 0.5 (at most 0.80, so no prose candidate is lost). `overlap_rules.py` decides which pairs qualify (`overlap_matches.csv`):

| Setting | Prose (English, science, Indic, `cadj-*`) | Code (`code-*`) | Math (`math-*`) |
|---|---|---|---|
| Shingles | word 5-grams of the H1 key | token 5-grams from the language's Pygments lexer; comments and a leading licence docstring dropped; strings and preprocessor directives kept | word 5-grams of the H1 key; numbers and LaTeX kept |
| Threshold (Jaccard) | 0.80 | 0.85 | 0.90, and the multisets of signed numbers must match |
| Minimum length | 50 words; shorter documents get H1 only | 20 non-blank lines after comment removal | none |

**Why these settings**
- **0.80 for prose:** the common setting in public pre-training pipelines. It catches re-posted pages with changed boilerplate, dates or a few edited sentences; pages that only share a topic score far lower.
- **5-grams:** shorter shingles make unrelated texts look similar through common phrases; longer ones let one edited word break many shingles.
- **Minimum length:** in a 60-word document one changed word breaks 5 of about 56 shingles, so short template pages that differ only in a name or date score 0.82–0.85.
- **Code on tokens:** files copied between forks differ in licence headers, comments and formatting. Code pairs are scored in their own all-pairs pass, independent of the word floor, so a forked file is found even when comments lower its word score. 0.85 avoids merging different files that share boilerplate (imports, generated code).
- **Math numbers rule:** *"Solve 2x + 3 = 7"* and *"Solve 2x + 5 = 7"* are near-identical text but different problems.

**Families.** H1 compares every pack with every other. For H2, a pair inside one family uses that family's rules; a pair from two families must pass both families' rules on both documents. Notebooks and math pages can contain code, so mixed pairs are kept but judged strictly.

**Clusters.** Qualifying pairs are joined into clusters (union-find); `source_priority_v1.md` chooses the survivors of each cluster.

## H3: another source or language

| Half of H3 | v1 |
|---|---|
| Same text from another source, same language | Covered by H1 and H2, within and across packs |
| A translation into another language | Out of scope: not detected |

Detecting translations needs multilingual embeddings or translate-then-match, a different method and cost from hashing; it is the v2 candidate, starting with Sanskrit/Hindi/English, where the Sanskrit packs are known to carry translations. `clean.py`'s within-document rule `DB-H3-001` (translation lines in `ind-sa-fw2`) stays. `spec_v1/README.md` already lists H3 among the diseases that regex cannot handle.

## Where dedup runs

1. **After `clean.py`.** Cleaning can make two different pages identical, so deduplicating earlier would miss those copies.
2. **Within each pack**, the analogue of FineWeb's per-snapshot dedup (Session 3, §7).
3. **Across packs, and across both teams' packs.** Data B's Indic and `cadj-*` packs join the H1/H2 pass. Translations between the teams stay out of v1. The cross-pack pass was gated on experiment E2 because of Risk 1; on the 38-pack run it adds very few removals (see Evidence), so v1 applies it. Its removals carry `stage = cross_pack` in the log and can be reversed.
4. **Before F2.** The order is Clean, then Dedup, then F2 (TSAI, 12 Nov). F2 runs on the deduplicated data. If it removes the survivor of a duplicate group, the removal stands and no other copy is promoted; these groups are counted and listed in the report (`source_priority_v1.md`, "After dedup: F2").

## Pipeline and hand-off to TSAI

```
raw sample ─▶ clean.py (TSAI, spec v1) ─▶ cleaned parts (doc_id, text, url, lang_label, pack_id)
                                              │                                │
                                              ▼                                │ url (rule 2),
                  overlap.py   MEASURES + QUALIFIES: H1 key, exact Jaccard     │ doc_id check
                               of every pair, family rules                     │
                               → overlap_matches.csv, overlap_docs.parquet,    │
                                 overlap_summary.json (status, SHA-256),       │
                                 overlap_pairs.csv (≥ 0.50), histogram, matrix │
                                              │                                │
                                              ▼                                │
  dedup.json ─────────▶  dedup.py    DECIDES: clusters, which copy survives ◀──┘
  (pack order, licences,             (rules 0–4), and runs the harm check:
   cross-pack switch)    gold ─────▶ gold matched on (pack_id, doc_id)
                               → remove_list.csv, dedup_log.jsonl, dedup_summary.json,
                                 heldout_duplicates.csv (for G3), empty_documents.csv (for cleaning)
                                              │
                                              ▼
                  TSAI         filters the cleaned parts with remove_list.csv
                               → deduplicated sample (every removal reversible from the log)
                                              │
                                              ▼
                  F2           benchmark contamination (G9's fingerprints) on the
                               deduplicated sample. A survivor it removes is not replaced;
                               those groups are counted and listed in the report
```

| Step | Code | Status |
|---|---|---|
| Measure and qualify | `overlap.py`, `overlap_rules.py`, `h1_sha256.py`, `jaccard_matrix.py`, `overlap_report.py`, tests; config `overlap.json` (38 cleaned packs) | Done (Aneesha Das, Vijay Patil; speed work Kunal Sinha). Job `jobs/2026-11-04-overlap.md`, run by TSAI on 5 Nov; superseded. Rerun on the #244 cleaning, `jobs/2026-11-12-overlap-rerun.md`: run by TSAI on 15 Nov at `7526194`, results in #469 |
| Reviewed matrix | `overlap_report.py`, `confirm_matrix.py` → `dedup/overlap_matrix.csv` | Done on the rerun (Aneesha Das, 15 Nov; the `--docs` check added 16 Nov): byte-identical to TSAI's matrix, 20/20 and 23/23 checks; `matrix_confirmation.md` |
| Decide | `dedup.py` + `dedup.json`: read `overlap_matches.csv` and `overlap_docs.parquet`, set aside matches between empty documents, form clusters, apply `source_priority_v1.md`, write the remove list and log. A scope switch can turn the cross-pack pass off without rerunning the overlap job | Written (Kunal Sinha), with tests and `README_dedup.md`; PyArrow/SciPy rewrite byte-identical (`benchmarks/2026-11-14-dedup-speed/`). Job `jobs/2026-11-14-dedup.md`, approved by the Data A lead on 16 Nov, run by TSAI on 17 Nov at `6cfc24a`: 1,345 removed, results in #547, matching the local run (`jobs/logs/2026-11-17-dedup-tsai-check.txt`) |
| Check | Harm check of the remove list against gold | Built into `dedup.py`. `not_testable` on sample v0; **pass** on 4 diagnosis packs (727 gold, 0 removed), to be repeated with the #244 cleaner |
| Filter contamination | F2 with G9's fingerprints, after dedup (optional in `clean.py` from #244) | Order set by TSAI, 12 Nov. The groups whose survivor F2 removes are counted and listed; `dedup.py` writes each group's survivors and removed copies to `dedup_groups.csv` for that count. F2 runs in the pipeline job (F2 → tokenize and shard → verify), which adopts #547's outputs (TSAI, 16 Nov) |

**What TSAI receives:** this design and `source_priority_v1.md`; the code, configs, tests and test logs above; the reviewed overlap matrix (`dedup/overlap_matrix.csv`, rebuilt from the rerun); a job request for the overlap rerun on the #244 cleaning; and a job request for `dedup.py` on sample v0 ("which documents would v1 remove, per pack and stage, and does it remove any gold?"). After approval, TSAI filters the full cleaned data with the remove list, as it applies spec v1. Our code never rewrites the data, so every removal can be reversed from the log. This is not a cleaning job request.

## What is recorded

For every removed document, one row in `dedup_log.jsonl`:

| Field | Meaning |
|---|---|
| `removed_pack_id`, `removed_split`, `removed_part`, `removed_row_in_part`, `removed_id` | The removed document; `removed_id` is its `doc_id`, unchanged |
| `kept_pack_id`, `kept_split`, `kept_part`, `kept_row_in_part`, `kept_id` | The surviving copy it duplicated (empty when no copy could survive) |
| `rule` | `H1` or `H2` |
| `similarity` | 1.0 for H1; exact Jaccard for H2 (token Jaccard for code) |
| `priority_rule` | The `source_priority_v1.md` rule that chose the survivor (0–4) |
| `stage` | `within_pack`, `cross_pack`, or `none` when no copy could survive |
| `direct` | `false` when the removed copy reached the survivor only through other copies |

Plus `remove_list.csv` (`pack_id, split, part, row_in_part, doc_id`: what TSAI filters out), a list of held-out ↔ held-out duplicates for G3, a list of empty documents for the cleaning team (`empty_documents.csv`; nothing is removed for them), and a summary per pack: documents in, removed by H1, removed by H2, removed cross-pack, documents out.

**A document is identified by `(pack_id, split, part, doc_id)`, never by `doc_id` alone.** `doc_id` hashes the original text, so exact copies in different parts or packs share it, and `removed_id` can equal `kept_id`.

## Validation

| # | Check | What it shows | Status |
|---|---|---|---|
| E1 | **Threshold sweep and hand review per family:** pair counts at 0.70–0.95 (`overlap_histogram.csv`), ~20 pairs read on each side of the threshold | Whether each threshold sits in the gap between "same text" and "related text" | Math reviewed (findings below). Prose and code: counts in, hand review open |
| E2 | **Within-pack vs cross-pack** removal counts | Whether the cross-pack pass is worth applying (Risk 1) | Answered by the TSAI run: applied |
| E3 | **Known pairs:** an exact copy, a whitespace/case variant, an edited sentence, a forked code file, a truncated copy (must be caught); math problems differing in a number, same-topic pages, code sharing only imports (must be kept) | The rules behave as specified | Done. The earlier tests check an edited copy, exact scores against brute force, the math numbers rule, code comment removal and mixed families. `tests/test_known_pairs.py` adds the rest: a whitespace/case variant is caught as H1; a truncated copy is caught as H2; same-topic pages (same site header and vocabulary) and code sharing only its imports are kept, and a one-value fork of that code is caught. **Limit found:** a truncated copy is caught only while it keeps about 80% of the text (on a 100-word text, 85 words kept scores 0.84 and is caught, 80 words scores 0.79 and is missed), because Jaccard compares the two documents as a whole, not whether one is contained in the other |
| E4 | **Indic threshold check:** E1 on at least one Indic pack | Whether the prose rules suit Indic text (Risk 2) | Measured on the rerun (`results_v1.md`, section 3): the 50-word minimum causes every rejection of a near-identical pair in the three Indic `sangraha-s` packs (106 pairs, the same as on 5 Nov), and 20.0% of Indic documents are under 50 words. Rebuilt from the raw text (`e4_review.py`): all 106 give TSAI's score; they come from only 35 documents in 4 clusters, and each pair differs by 1–5 words per side. Across all `ind-*` packs the 50-word minimum rejects 135 near-identical pairs (69 documents). Open: a human reader's labels (sheets sent privately, #392) |
| Harm | **No gold document is removed.** Gold is `<pack>_gold.csv` from `build_gold.py` (`teams/01-data-a/gold/`, `teams/02-data-b/gold/`), matched on `(pack_id, doc_id)`. The number of gold IDs present in the input is reported first; if it is zero, the check fails, because it tested nothing | No harm to reviewed clean documents | Done on the 4 diagnosis packs on hand (`math-finemath`, `math-megamath`, `sci-finepdfs`, `cadj-commits`): 727 gold IDs present (314 from the gold in this branch, plus 413 for `cadj-commits` from `main`), 0 removed (`results_v1.md`, section 3). The only pair at word Jaccard ≥ 0.50 is two `cadj-commits` gold documents at 0.716, both kept; no math or science gold document is in any pair at ≥ 0.50. Limit: 4 of the 13 Data A packs have gold here |

## Evidence

The full numbers, per pack and per run, are in **`results_v1.md`**. This section lists only what the decisions rest on. The measurements come from TSAI's rerun of `overlap.py` (commit `7526194`) on the 38 sample v0 packs cleaned by the merged #244 cleaner, 15 Nov 2026 (`jobs/results/2026-11-12-overlap-rerun/`, #469), and the removal counts from TSAI's run of `dedup.py` (commit `6cfc24a`) on its output, 17 Nov (`jobs/results/2026-11-14-dedup/`, #547). They replace the 5 Nov run on the old cleaning (1,416,236 documents, 2,711 qualifying pairs), which gave the same removal total; each decision below was checked again on the rerun and still holds.

- **Scale:** 1,414,996 documents in 77 minutes with a 12.1 GiB peak, within the requested 90 minutes and 32 GiB, so exact all-pairs scoring fits the sample (Risk 4). It was slower than on 5 Nov (56 min) with the same work; local tests ruled out the code and library versions.
- **Duplicates are rare:** 98 H1 pairs and 2,652 H2 pairs. 21 of the H1 pairs are between 7 documents that cleaning emptied without dropping (1 `code-cpp`, 4 `code-java`, 2 `code-js-ts`); they share one H1 key but are not copies, so `dedup.py` sets them aside and lists them for the cleaning team. `dedup.py` removes **1,345 documents (0.095%)**, none held-out.
- **Cross-pack overlap is small:** 50 of the 2,750 qualifying pairs are cross-pack, 14 of them between the empty documents; 36 documents are removed across packs. This answers E2: the cross-pack pass cannot cause a measurable FineWeb effect, so v1 applies it and no training ablation is needed.
- **Held-out copies exist:** 64 qualifying pairs join a train and a held-out document, so rule 0 matters: it removes 64 train copies and no held-out document.
- **The survivor rules all act:** of 1,084 groups, rule 0 decides 28, rule 2 (url) 21, rule 3 (longer) 750 and rule 4 (pack order) 285.
- **Concentration:** most near duplicates are in `cadj-commits` (904 removed, 1.20%, the only pack above 1%), `cadj-stackexchange` and `ind-hi-sangraha-s`; English packs have very few.
- **Two signals for the hand review** (`results_v1.md`, section 1): the code token pass finds many pairs that word scores miss (`code-rust`: 3 pairs ≥ 0.80 by words, 530 qualifying), and the 50-word minimum removes almost every pair in three Indic `sangraha-s` packs, which is where E4 starts.

Findings from local test runs on raw sample v0 parts (details in `results_v1.md`, section 2):
- **Math numbers rule** (math E1, 47,250 documents): it keeps different worked examples apart as intended, but it also rejected two true copies of the same page whose only numeric difference was a date line or a number in the title. Both pairs share their URL.
- **Template pages pass the thresholds:** slideserve.com pages with different titles inside identical site boilerplate (math, ~117 words, above 0.90) and short template pages that differ only in a name or date (English, 0.82–0.85). They are not copies of one document; this is a quality-filter problem, not a dedup one.
- **A same-URL copy can fall just below the threshold:** one math page with an identical URL scored 0.894.

## Risks

1. **A wider scope can remove better text.** FineWeb found that global dedup trained worse models than per-snapshot dedup, because text repeated across crawls tends to be good text, and cutting it to one copy raised the share of unique low-quality text (Session 3, §7). Choosing a better survivor does not fix this. *Mitigation:* the cross-pack pass was gated on E2, and its effect is negligible on the sample; every removal records its `stage` and can be reversed.
2. **Thresholds may not suit Indic text.** Whitespace word 5-grams and a 50-word minimum were set on English. Indic scripts have longer, agglutinative words and code-mixing, and English-tuned methods are known to erase Indic content (Session 3, §8). *Mitigation:* E4 before H2 removals are applied to Indic packs, with Indic removal rates reported separately.
3. **Benchmark contamination is not covered.** Matching against benchmark sets is a separate evaluation step (Session 3, §12). Passing dedup does not mean the data is free of test leakage. Train/held-out copies inside the sample are handled by rule 0.

**Training ablation.** The definitive test of dedup scope is to train small proxy models on data with and without the cross-pack pass (Session 3, §7 and §11). It is only worth running where the cross-pack pass removes a measurable share (≥ 1% of a pack). No pack comes close on the sample, so v1 requests none.

## Open items

- **The rerun, in TSAI's order (12 Nov): done.** #244 cleaning of sample v0 (86/86 parts, 1,414,996 rows); overlap rerun at `7526194` (#469, 15 Nov); matrix confirmed (`matrix_confirmation.md`); `dedup.py` run locally on the returned files (`jobs/logs/2026-11-16-dedup-local.txt`); the approved dedup job run by TSAI with urls (#547, 17 Nov), matching the local run. E4's sheets were rebuilt on the rerun and are unchanged. #547's `remove_list.csv` and `dedup_groups.csv` go to the pipeline job.
- **Hand review:** prose (0.80) and code (0.85), as done for math; and a sample of `cadj-commits`, the pack with the most duplicates. On the rerun's pairs.
- **E4:** a human Kannada, Telugu and Tamil reader to label the rejected `sangraha-s` pairs (copy, template, different or unsure) on blind sheets. The measured part and the rebuild from the raw text are done on the rerun (`results_v1.md`, section 3: the same 106 pairs as on 5 Nov; whatever the labels, a lower minimum would affect at most 69 Indic documents). The sheets go to the readers privately (TSAI, 16 Nov), through #392.
- **Math numbers rule and same URL:** compare numbers in the body only (ignoring the title and first line), and count same-URL pairs as H2 duplicates at ≥ 0.80. Decided 13 Nov: the rerun keeps v1's rules frozen, so both changes, and a lower Indic word minimum from E4, are left for v1.1, each with its own evidence.
- **Speed follow-ups (TSAI's speed rule, 14 Nov):** from the review of kunal2016/era-v5-lab#1. Proposed by Kunal Sinha: run the rerun at `7526194` as approved and do these in the next overlap run; Vijay Patil to confirm, or hold the rerun and re-pin. Measured exceptions, disclosed in `benchmarks/2026-11-13-speed/README.md`: the Pygments lexer (about half the wall time on the 12,000-document sample) and `normalize.match_key` (about 8%), one call per document.
  - `overlap.py`: shingle the parts in parallel, keeping part order (about 1.8× on 2 vCPU; the only change to the wall time).
  - `overlap_rules.qualifying_pairs`: NumPy masks over the stored pairs, not a loop (32,329 pairs on the rerun, so milliseconds).
  - `overlap.py`: the `exact` flags with `pandas.factorize`, not a loop over the stored pairs (milliseconds).
  - `overlap_rules.gram_set`: decoded with NumPy in `1c89f9a`; `np.intersect1d` for the rest (mixed code/text pairs only).
  - `dedup.py`: done before the dedup job request (kunal2016/era-v5-lab#2): pyarrow reads (`pc.is_in`, `value_counts`, `take`), the gold check with `pc.is_in`, and `connected_components` for the clusters, byte-identical on three real inputs; peak memory 1,044 → 400 MB on TSAI's files (Kunal Sinha).
- **F2 groups:** done (12 Nov). `dedup.py` writes `dedup_groups.csv`: every duplicate group, one row per member (`group_id, group_size, priority_rule, role, pack_id, split, part, row_in_part, doc_id`; role is `survivor` or `removed`); the F2 step counts and lists the groups whose survivor it removes from it.
- **Licence:** G10 owns the final decision. `code-js-ts` and `ind-hi-hplt` are not verified; all 38 packs are treated as usable for this experiment only.

## Decision log

It covers this file and `source_priority_v1.md`. The body states the decisions; this log is the record of approval. Add a row whenever a decision is made or changed.

| Date | Decision | Agreed by | Where |
|---|---|---|---|
| 3 Nov 2026 | First drafts of both design files | Data A team | PR #255, commit `8a772b2` |
| 4 Nov 2026 | Method follows the implemented `overlap.py` / `overlap_rules.py`: exact Jaccard; family rules (prose 0.80 + 50 words, math 0.90 + numbers, code 0.85 tokens + 20 lines); a mixed pair must pass both families' rules | Data A team | PR #255, commits `1718918`, `16c479c` |
| 4 Nov 2026 | Design v1 agreed by the team | Data A team | PR #255, commit `16c479c` |
| 5 Nov 2026 | H3: translations out of scope for v1; H1/H2 cover same-language copies from another source; `DB-H3-001` stays | TSAI | PR #255, TSAI comment of 5 Nov, point 1 |
| 5 Nov 2026 | Data B packs join the cross-team H1/H2 pass; E4 required; translations between the teams stay out | TSAI | PR #255, point 2 |
| 5 Nov 2026 | Pack order (rule 4): the order in which `clean.py` lists the packs, written in `source_priority_v1.md` | TSAI | PR #255, point 3 |
| 5 Nov 2026 | Held-out first (rule 0): a train copy of a held-out document is removed; held-out ↔ held-out duplicates are reported, not removed; dedup never shrinks the held-out set | TSAI | PR #255, point 4 |
| 5 Nov 2026 | Hand-off: a remove list `(pack_id, split, part, doc_id)` and `dedup_log.jsonl`; TSAI filters the cleaned data, our code never rewrites it | TSAI | PR #255, point 5 |
| 5 Nov 2026 | Location: code and design in `teams/01-data-a/dedup/`, job requests in `teams/01-data-a/jobs/` | TSAI | PR #255, point 6 |
| 10 Nov 2026 | The 25 Data B packs, which `clean.py` does not list, follow the Data A packs in alphabetical order. It affects 23 of the 50 cross-pack pairs. The Data B lead may ask for a different order, with a reason, by Fri 13 Nov | Data A team; approved by TSAI | `source_priority_v1.md`, rule 4; TSAI in G1 |
| 10 Nov 2026 | Cross-pack pass applied in v1 (E2 answered: 50 of 2,711 qualifying pairs are cross-pack); no training ablation for v1 | Data A team | `results_v1.md`, section 1 |
| 10 Nov 2026 | Reviewed source matrix: `dedup/overlap_matrix.csv` is TSAI's returned matrix, unchanged; rebuilt byte-identically with and without `overlap_docs.parquet` and with `overlap_report.py --results` | Aneesha Das (Data A) | `matrix_confirmation.md`; PR #255 |
| 10 Nov 2026 | Empty documents (no shingles) are not duplicates: `dedup.py` sets aside their matches, removes none of them and lists them in `empty_documents.csv` for the cleaning team. On the sample: 7 documents, 21 matches; 1,345 removed instead of 1,351. The 7 documents stay in the data; dropping them is a cleaning change for spec v1.1 | Data A team (proposed by Aneesha Das, agreed by Kunal Sinha; Kunal's Windows rerun gave the same result, `remove_list.csv` `913e66a6…`) | PR #255, commit `497dbd3`; `dedup.py`, `README_dedup.md`, `jobs/2026-11-14-dedup.md` (filed on 10 Nov as `2026-11-10-dedup.md`) |
| 11 Nov 2026 | Licence (rule 1): all 38 sample-v0 packs usable; `dedup.json` unchanged (empty `licence_usable`, default true). G10's table on `main` lists 8 of the packs, none excluded; `code-js-ts` and `ind-hi-hplt` left open for TSAI, with no effect on the v1 remove list | Data A team (Vijay pointed to the table) | `source_priority_v1.md`, rule 1; G10 `licence_table.md` |
| 12 Nov 2026 | Cleaning rerun: #244 changes the cleaner, so the 3 Nov cleaned sample is out of date. TSAI reruns the cleaning on sample v0 after #244 merges; the overlap measurement is run again on the new output, then the `dedup.py` job on that output. The 5 Nov results are not used | TSAI | G1, TSAI's answers to Vijay, points 1–2 |
| 12 Nov 2026 | Licence: `default_licence_usable: true` for this experiment only; `code-js-ts` and `ind-hi-hplt` are not verified; G10 owns the final licence decision | TSAI | G1, point 3; `results_v1.md`; `source_priority_v1.md`, rule 1 |
| 12 Nov 2026 | Pipeline order: Clean, then Dedup, then F2. If F2 removes the survivor of a duplicate group, the removal stands and no other copy is promoted; these groups are counted and listed in the report | TSAI | G1, point 4; `source_priority_v1.md`, "After dedup: F2" |
| 12 Nov 2026 | `dedup.py` writes `dedup_groups.csv`: every duplicate group, one row per member (`group_id, group_size, priority_rule, role, pack_id, split, part, row_in_part, doc_id`; role is `survivor` or `removed`), so the F2 step can count and list the groups whose survivor it removes (TSAI's point 4). A group can have several survivors (held-out copies, rule 0) or none (rule 1). The four existing outputs are unchanged: on TSAI's 5 Nov files they are byte-identical to the earlier code (`remove_list.csv` `913e66a6…`); 1,084 groups, 0 without a survivor, 0 with several. 106 tests pass | Data A team (asked by Aneesha Das, written by Kunal Sinha) | PR #255; `dedup.py`, `tests/test_dedup.py`, `README_dedup.md` |
| 13 Nov 2026 | Overlap rerun approved at the merged speed commit `7526194`, with v1's rules frozen; the math numbers rule, same-URL pairs and a lower Indic minimum are left for v1.1 | Vijay Patil (Data A lead) | PR #255, lead approval comment; `jobs/2026-11-12-overlap-rerun.md` |
| 16 Nov 2026 | Dedup job (`jobs/2026-11-14-dedup.md`) approved at `6cfc24a`, with the expected values from the local run on the rerun's returned files (1,345 removed, 64 by rule 0, 0 held-out) | Vijay Patil (Data A lead) | PR #255; G1, 16 Nov |
| 16 Nov 2026 | One pipeline job runs F2, then tokenizes and shards, then verifies, adopting the verified #244 and #255 outputs; no separate F2 job. E4 review files go to the readers privately, not on GitHub | TSAI | G1, TSAI's answers to Vijay, points 2 and 6 |
| 17 Nov 2026 | Final remove list for sample v0: TSAI's dedup run with urls, 1,345 removed (0.095%), 0 held-out; matches the local run, with 13 different survivors in groups decided by rule 2 | TSAI run; checked by Kunal Sinha | #547; `jobs/logs/2026-11-17-dedup-tsai-check.txt`; `results_v1.md`, section 1 |
