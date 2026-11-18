# Dedup results v1

The measurements behind `dedup_design_v1.md`, for discussion. The design states the decisions; this file holds the numbers, and grows as new runs come in.

**How to read it**
- **Final** means measured by TSAI on the approved input with committed code. It changes only if the rules change.
- **Estimate** means computed by us from TSAI's files without `dedup.py` (used only for the superseded 5 Nov run). The removal counts in section 1 come from TSAI's run of `dedup.py` itself.
- **Local** means a test run on raw (not cleaned) sample v0 parts. It shows the code works and gives findings for the hand review; the TSAI run supersedes its counts.
- Every number is for the Week-2 tokenizer sample v0 (1.4 million documents). Applied to the full data, the counts will differ.

**17 Nov 2026: final numbers.** Section 1 now holds TSAI's runs on sample v0 cleaned by the merged #244 cleaner: the overlap rerun (15 Nov, results in #469) and the `dedup.py` job (17 Nov, results in #547). These replace the 5 Nov run, which TSAI set aside on 12 Nov because #244 changed the cleaner; it is kept briefly in section 1b as the record. Sections 2 and 3 (local runs, harm check) are unchanged; the E4 part of section 3 is redone on the rerun.

**Licence (TSAI, 12 Nov).** These runs treat all 38 packs as usable (`default_licence_usable: true` and an empty `licence_usable` in `dedup.json`). This holds for this experiment only. The licences of `code-js-ts` and `ind-hi-hplt` are **not verified**: G10's licence table leaves both open (`code-js-ts`: training-use rights need further verification; `ind-hi-hplt`: CC0 covers the packaging only, and the text keeps its web terms). G10 owns the final licence decision.

## 1. TSAI 38-pack runs on the #244 cleaning (final)

**Overlap:** job `jobs/2026-11-12-overlap-rerun.md`, approved by the Data A lead; run by TSAI on a CPU host on 15 Nov 2026 at commit `7526194`. Results: `jobs/results/2026-11-12-overlap-rerun/` (#469); the three large files (`overlap_docs.parquet`, `overlap_pairs.csv`, `overlap_matrix.npz`) came by TSAI's links on 16 Nov and match the summary's SHA-256. Input: the 38 sample v0 packs cleaned by the merged #244 cleaner (cleaner sha256 `22d818c7…`), 86 parts, train + held-out.
**Dedup:** job `jobs/2026-11-14-dedup.md`, approved by the Data A lead; run by TSAI on 17 Nov at `6cfc24a` on those overlap outputs and the same cleaned parts, so rule 2 (url) applied. Results: `jobs/results/2026-11-14-dedup/` (#547).

| | |
|---|---|
| Documents | 1,414,996 (7 empty) |
| Overlap wall time, peak memory | 4,591 s (77 min), 12.1 GiB (12,356.5 MiB); requested 90 min, 32 GiB |
| Pairs that share a shingle | 2,345,501,632 |
| Pairs stored (word Jaccard ≥ 0.50) | 32,329 |
| Pairs by word Jaccard ≥ 0.70 / 0.75 / 0.80 / 0.85 / 0.90 / 0.95 | 4,622 / 3,410 / 2,446 / 1,683 / 1,122 / 333 |
| Qualifying pairs (after the family rules) | **2,750**: 98 H1 (71 exact groups, 150 documents) + 2,652 H2. One H1 group is the 7 empty documents (21 pairs; observation 6) |
| Within pack / cross pack | 2,700 / **50** |
| Train ↔ held-out pairs among the qualifying pairs | 64 |
| `doc_id`s used by two or more documents | 0 |
| **Removed by `dedup.py`** | **1,345 (0.095%)**: 1,289 H2, 56 H1; 1,309 within a pack, 36 across packs |
| Held-out removed | **0** (64 train copies of held-out documents removed by rule 0; 0 held-out ↔ held-out pairs) |
| Groups | 1,084, each with one survivor; decided by rule 0: 28, rule 2 (url): 21, rule 3 (longer): 750, rule 4 (pack order): 285 |
| Empty documents | 7, listed in `empty_documents.csv`, not removed; their 21 matches set aside |
| Dedup wall time | 4.2 s |

The word-Jaccard counts cover every pair, before the family rules; the qualifying pairs are what dedup acts on.

*Source:* overlap `overlap_summary.json` (documents, time, memory, pairs at each threshold, H1 groups, qualifying pairs by rule) and `overlap_matches.csv` (within / cross pack; train ↔ held-out from `overlap_docs.parquet`); dedup `dedup_summary.json` and `dedup_groups.csv`. The source matrix was confirmed from these files (`matrix_confirmation.md`: 20/20 checks, 23/23 with `overlap_docs.parquet`).

**Check against our local run** (`jobs/logs/2026-11-16-dedup-local.txt`, no urls; checked in `jobs/logs/2026-11-17-dedup-tsai-check.txt`): the total, the rule-0 removals, the held-out result, `heldout_duplicates.csv` and `empty_documents.csv` match, as the job request required, and so do the groups, the H1/H2 and the stage counts. With urls, rule 2 decided 21 two-document groups that the local run decided by rule 3 (19) or rule 4 (2); in 13 of them the other copy survives. So 1,332 of the 1,345 removed documents are the same in both runs, and per pack the removals move by at most 9.

**Against the 5 Nov run** (section 1b): the same total (1,345) and the same number of groups (1,084). The #244 cleaning moved 64 removed documents to a different row, so only this run's `remove_list.csv` fits the cleaned parts.

### Per pack

Where each column comes from (overlap files in `jobs/results/2026-11-12-overlap-rerun/`, dedup files in `jobs/results/2026-11-14-dedup/`):

| Column | Source |
|---|---|
| Documents | `overlap_summary.json`, `documents` |
| Pairs ≥ 0.80 | `overlap_by_pack.csv`, level `0.80`, same pack on both sides (raw word score, before the family rules) |
| Qualifying | `overlap_matches.csv`, `stage = within_pack` (pairs that pass the family rules) |
| Docs matched, own pack | `overlap_matrix_counts.csv`, the diagonal (`source_a = source_b`) |
| Docs matched, other packs | `overlap_matches.csv`, `stage = cross_pack`: distinct documents per pack |
| Removed, Removed % | `dedup_summary.json`, `by_pack.removed` (TSAI's `dedup.py` run, with urls; within and cross pack) |

| Pack | Documents (train + held-out) | Pairs ≥ 0.80 | Qualifying | Docs matched, own pack | Docs matched, other packs | Removed | Removed % |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cadj-commits` | 75,579 | 1,094 | 1,094 | 1,664 | 9 | 904 | 1.20% |
| `cadj-notebooks` | 15,732 | 15 | 15 | 27 | 0 | 14 | 0.09% |
| `cadj-stackexchange` | 41,805 | 208 | 208 | 384 | 0 | 199 | 0.48% |
| `code-cpp` | 55,195 | 6 | 5 | 10 | 2 | 5 | 0.01% |
| `code-go` | 77,765 | 8 | 6 | 12 | 0 | 6 | 0.01% |
| `code-java` | 85,518 | 8 | 9 | 10 | 5 | 3 | 0.00% |
| `code-js-ts` | 117,208 | 1 | 1 | 2 | 2 | 0 | 0 |
| `code-python` | 73,305 | 1 | 24 | 13 | 4 | 9 | 0.01% |
| `code-rust` | 58,795 | 3 | 530 | 66 | 3 | 58 | 0.10% |
| `en-dclm` | 60,802 | 14 | 14 | 19 | 5 | 11 | 0.02% |
| `en-fineweb-edu` | 72,100 | 7 | 7 | 14 | 11 | 15 | 0.02% |
| `en-nemotroncc` | 89,183 | 23 | 19 | 27 | 6 | 19 | 0.02% |
| `en-nemotroncc-synth` | 198,877 | 1 | 1 | 2 | 1 | 1 | 0.00% |
| `ind-bn-fw2` | 10,809 | 0 | 0 | 0 | 1 | 0 | 0 |
| `ind-bn-sangraha-v` | 10,217 | 0 | 0 | 0 | 1 | 1 | 0.01% |
| `ind-gu-fw2` | 23,011 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ind-hi-fw2` | 13,932 | 0 | 0 | 0 | 1 | 0 | 0 |
| `ind-hi-hplt` | 8,515 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ind-hi-indiccorp` | 110,755 | 29 | 5 | 7 | 2 | 4 | 0.00% |
| `ind-hi-sangraha-s` | 7,542 | 584 | 579 | 37 | 0 | 35 | 0.46% |
| `ind-hi-sangraha-v` | 14,614 | 134 | 134 | 18 | 3 | 20 | 0.14% |
| `ind-kn-fw2` | 7,841 | 0 | 0 | 0 | 3 | 0 | 0 |
| `ind-kn-sangraha-s` | 5,238 | 20 | 0 | 0 | 0 | 0 | 0 |
| `ind-kn-sangraha-v` | 8,444 | 0 | 0 | 0 | 3 | 3 | 0.04% |
| `ind-ml-fw2` | 19,161 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ind-mr-fw2` | 11,353 | 0 | 0 | 0 | 5 | 0 | 0 |
| `ind-mr-sangraha-v` | 12,299 | 0 | 0 | 0 | 5 | 5 | 0.04% |
| `ind-or-fw2` | 34,012 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ind-sa-fw2` | 5,721 | 13 | 13 | 23 | 0 | 12 | 0.21% |
| `ind-ta-fw2` | 6,824 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ind-ta-sangraha-s` | 4,372 | 55 | 1 | 2 | 0 | 1 | 0.02% |
| `ind-ta-sangraha-v` | 6,861 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ind-te-fw2` | 5,763 | 0 | 0 | 0 | 2 | 0 | 0 |
| `ind-te-sangraha-s` | 4,463 | 32 | 0 | 0 | 0 | 0 | 0 |
| `ind-te-sangraha-v` | 8,678 | 0 | 0 | 0 | 2 | 2 | 0.02% |
| `math-finemath` | 28,830 | 18 | 3 | 6 | 2 | 3 | 0.01% |
| `math-megamath` | 17,803 | 100 | 32 | 20 | 1 | 15 | 0.08% |
| `sci-finepdfs` | 6,074 | 0 | 0 | 0 | 0 | 0 | 0 |
| **All** | **1,414,996** | **2,374** | **2,700** | **2,363** | **79** | **1,345** | **0.095%** |

**By family (removed):** code-adjacent 1,117 of 133,116 (0.84%); Indic 83 of 340,425 (0.02%); code 81 of 467,786 (0.02%); English 46 of 420,962 (0.01%); math 18 of 46,633 (0.04%); science 0 of 6,074. *Source:* the per-pack table, summed by the pack name's prefix.

### Cross-pack pairs (50)

| Packs | Qualifying pairs |
|---|---:|
| `code-java` × `code-js-ts` | 8 |
| `en-fineweb-edu` × `en-nemotroncc` | 5 |
| `ind-mr-fw2` × `ind-mr-sangraha-v` | 5 |
| `code-cpp` × `code-java` | 4 |
| `en-dclm` × `en-fineweb-edu` | 4 |
| `cadj-commits` × `code-python` | 4 |
| `ind-kn-fw2` × `ind-kn-sangraha-v` | 3 |
| `cadj-commits` × `code-rust` | 3 |
| `code-cpp` × `code-js-ts` | 2 |
| `ind-hi-indiccorp` × `ind-hi-sangraha-v` | 2 |
| `ind-te-fw2` × `ind-te-sangraha-v` | 2 |
| Other pack pairs (1 each) | 8 |

*Source:* `overlap_matches.csv`, `stage = cross_pack`, counted by pack pair.

**14 of these 50 are between empty documents:** all 8 `code-java` × `code-js-ts`, all 4 `code-cpp` × `code-java` and both `code-cpp` × `code-js-ts` pairs (observation 6). The real cross-pack pairs number 36, and `dedup.py` removes 36 documents across packs.

**Pairs affected by the Data B pack order** (`source_priority_v1.md`, rule 4): **23 of the 50** have a Data B pack on at least one side. 14 are between two Data B packs, mostly the same Indic language in `fw2` and `sangraha-v` (`ind-mr` 5, `ind-kn` 3, `ind-te` 2, `ind-bn` 1; `ind-hi-indiccorp` × `ind-hi-sangraha-v` 2, `ind-hi-fw2` × `ind-hi-sangraha-v` 1). 9 are between `cadj-commits` and a code pack (`code-python` 4, `code-rust` 3, `code-cpp` 1, `code-java` 1). The other 27 are between two Data A packs (14 of them between empty documents). Rule 4 decides a pair only if the copies are still tied after rules 0–3. TSAI approved this order in G1 on 10 Nov 2026. *Source:* `overlap_matches.csv`, by each side's pack.

### Observations for discussion

1. **`cadj-commits` holds two-fifths of all qualifying pairs** (1,094 of 2,750) and 45 of the 98 exact pairs; it loses 904 documents (1.20%), the only pack above 1%. A sample should be read to confirm they are true copies (for example repeated commit messages).
2. **The code token pass finds what word scores miss.** `code-rust` has 3 pairs at word Jaccard ≥ 0.80 but 530 qualifying pairs; `code-python` has 1 and 24. These come from the token pass, which ignores comments and licence headers. The code hand review (0.85) should look at these.
3. **E4 signal: the Indic `sangraha-s` packs.** `ind-kn-sangraha-s` (20 pairs ≥ 0.80), `ind-te-sangraha-s` (32) and `ind-ta-sangraha-s` (55) end with 0, 0 and 1 qualifying pairs, all because of the 50-word minimum (section 3). In contrast, `ind-hi-sangraha-s` keeps 579 of 584, all among only 37 documents, so a few near-identical documents form large clusters.
4. **Cross-pack overlap is small and mostly expected:** English web crawls, the `fw2` and `sangraha-v` versions of the same Indic language, and `cadj-commits` with code packs. The pairs between code languages (Java, JS/TS, C++) are not shared files: all 14 are between empty documents (observation 6).
5. **The cleaning rerun changed little that dedup sees.** Against the 5 Nov cleaning: 1,240 fewer documents (1,416,236 → 1,414,996), 39 more qualifying pairs (2,711 → 2,750), the same 50 cross-pack pairs and the same 7 empty documents; the removal total is unchanged.
6. **7 documents are empty after cleaning:** 1 `code-cpp`, 4 `code-java`, 2 `code-js-ts`, all train, the same 7 as on 5 Nov (0 words and 0 shingles in `overlap_docs.parquet`; their `doc_id`s are in `matrix_confirmation.md`). They pass `clean.py`'s empty-output check (`out.strip()`) but have no words after normalisation, so cleaning kept them. They share one H1 key, so `overlap.py` counts them as one exact group: 21 of the 98 H1 pairs and 14 of the 50 cross-pack pairs, inflating 8 code cells of the source matrix. `dedup.py` sets their matches aside and lists them in `empty_documents.csv`; they stay in the data. Dropping them is a cleaning rule change for spec v1.1.

## 1b. TSAI 38-pack run of 5 Nov (superseded)

Job `jobs/2026-11-04-overlap.md`, run by TSAI on 5 Nov 2026 at commit `86ecdd4` on the 3 Nov cleaning; results in `jobs/results/2026-11-04-overlap/` (#307). Set aside by TSAI on 12 Nov because #244 changed the cleaner; not used for the remove list.

| | 5 Nov run | Final run (section 1) |
|---|---:|---:|
| Documents | 1,416,236 | 1,414,996 |
| Overlap wall time, peak memory | 56 min, 9.6 GiB | 77 min, 12.1 GiB |
| Qualifying pairs (H1 + H2) | 2,711 (98 + 2,613) | 2,750 (98 + 2,652) |
| Cross pack | 50 | 50 |
| Train ↔ held-out pairs | 63 | 64 |
| Removed by `dedup.py` | 1,345, local, no urls (`jobs/logs/2026-11-10-dedup-local.txt`) | 1,345, TSAI, with urls |

The per-pack tables and observations of the 5 Nov run are in this file's history (commit `1252c6f`). The rerun was slower with the same work (2.346 vs 2.347 billion pairs sharing a shingle). Local tests ruled out the code and the library versions, so the host is the likely cause; `run.log` and host details were asked of TSAI.

## 2. Local runs (raw sample v0 parts)

### English packs (Aneesha Das, 4 Nov)

`en-dclm`, `en-fineweb-edu`, `en-nemotroncc`, `en-nemotroncc-synth`; 426,508 documents; 845 s, 3.4 GB. Raw word scores, before the family rules. *Source:* the run log, `jobs/logs/2026-11-04-overlap-en-local.txt`.

| | Within pack | Cross pack | All |
|---|---:|---:|---:|
| Exact (H1) pairs | 16 | 0 | 16 |
| Pairs at word Jaccard ≥ 0.80 | 44 | 11 | 55 |

- H1: 9 groups, 21 documents, all in `en-nemotroncc`.
- Pairs at ≥ 0.70 / 0.75 / 0.80 / 0.85 / 0.90 / 0.95: 135 / 90 / 55 / 43 / 33 / 25.
- **Finding:** short template pages that differ only in a name or date score 0.82–0.85; this is why H2 has a minimum length.

### Five packs (Vijay Patil, 4 Nov)

`code-rust`, `en-fineweb-edu`, `ind-hi-hplt`, `ind-mr-sangraha-v`, `math-finemath`; 183,976 documents; 571 s, 2.76 GiB. With the family rules. *Source:* the run's transcript and result snapshots in `jobs/logs/2026-11-04-overlap-local/`.

- 0 H1 groups; 372 qualifying H2 pairs: 371 within packs, 1 cross-pack (`en-fineweb-edu` × `math-finemath`).
- Largest share: `code-rust`, 57 of 60,738 documents with a match in their own pack (0.09%).

### Math packs, E1 (Kunal Sinha, 4 Nov)

`math-finemath`, `math-megamath`; 47,250 documents; 97 s, 1.0 GB. Config `overlap_math.json`, log `jobs/logs/2026-11-04-overlap-math-local.txt`. *Source:* that run's `overlap_summary.json`, `overlap_pairs.csv`, `overlap_matches.csv` and `overlap_docs.parquet` (local, in `out/overlap_math/`, not in the repo); the hand review also read the document text from the input parts. Gold IDs were checked against `teams/01-data-a/gold/math-*_gold.csv`.

| | |
|---|---|
| H1 exact groups | 0 |
| Pairs by word Jaccard ≥ 0.70 / 0.75 / 0.80 / 0.85 / 0.90 / 0.95 | 369 / 243 / 131 / 68 / 46 / 18 |
| Of the 46 at ≥ 0.90: qualify / rejected by the numbers rule | 36 / 10 |
| Qualifying: within `megamath` / within `finemath` / cross-pack | 32 / 3 / 1 |
| Train ↔ held-out qualifying pairs | 1 |
| Gold IDs present in this input | 0 of 112 |

**Hand review** (all 10 rejected pairs and the lowest-scoring kept pairs):
1. **The numbers rule rejects true copies with a different header.** Two pairs are the same page saved twice (Jaccard 0.987 and 0.972), differing only in a date line ("Dec 10, 2015 · 15 minute read") or a number in the title ("UVa 11357"), plus Markdown formatting. Both pairs share their URL.
2. **Template pages pass 0.90.** The largest cluster (7 documents) is slideserve.com pages: different presentations ("projectile motion", "the preprocessor", …) inside about 117 words of identical site boilerplate. Only the title differs, so they are not copies of one document.
3. **The rule works where it should:** two chemistry textbook chapters with different worked values are kept apart.
4. **A same-URL copy is missed just below 0.90:** reference.com's "examples of quadrilaterals" is in `finemath` train and `megamath` held-out with the identical URL, at 0.894.
5. **The gold harm check cannot run on the sample:** none of the 112 math gold IDs are in it.

Per-pack `jaccard_matrix.py` outputs for the two math packs (histogram, matrix, pairs with shingle counts) are in `out/jaccard_math/` on the local machine; they match the within-pack counts above.

## 3. Checks on the week-1 diagnosis packs and E4 (11 Nov)

### Harm check (pass)

The gold sets come from the week-1 diagnosis packs, not from sample v0, so the harm check on the 38-pack run was `not_testable`. It was run on the 4 diagnosis packs on hand, through the production order: `clean.py` (main, SHA-256 `d3464bda…`), then `overlap.py`, then `dedup.py` with `gold_dirs` set. It was run twice on the same overlap output: run 1 with the gold files in this branch, run 2 adding the `cadj-commits` gold file from `main`. Log: `jobs/logs/2026-11-11-dedup-harm-diag-local.txt` (counts and hashes only).

| | |
|---|---|
| Packs | `math-finemath`, `math-megamath`, `sci-finepdfs` (cleaned), `cadj-commits` (raw: `clean.py` has no rules for it) |
| Documents after cleaning | 1,964 |
| Gold IDs present, run 1 | **314**: `math-finemath` 86, `math-megamath` 26, `sci-finepdfs` 202 (this branch has no `cadj-commits` gold file) |
| Gold IDs present, run 2 | **727**: the 314 above plus `cadj-commits` 413 (all 413 IDs in its gold file) |
| Qualifying duplicate pairs | 0 |
| Documents removed / gold removed | 0 / **0** in both runs |
| Gold dropped by `clean.py` | 0 |

The result is a pass, but a check where nothing is removed is weak on its own. The stronger evidence is the margin: **only one pair in the 1,964 documents reaches word Jaccard ≥ 0.50**: two `cadj-commits` documents at 0.716. Both are `cadj-commits` gold documents (run 2), and both are kept, because 0.716 is below the 0.80 prose threshold. No math or science gold document is in any pair at ≥ 0.50, so none came near the 0.80 or 0.90 thresholds. Limits: 4 of the 13 Data A packs have gold here, and each pack is checked on its own.

**The `cadj-commits` gold file (run 2)** is `teams/02-data-b/gold/cadj-commits_gold.csv` on `main` (added in commit `6b09da4`, 2 Nov; SHA-256 `ba4da5c2…`). It is not in this branch, which has not been synced with `main`, and it was not added here because it is a Data B file. When this PR merges, `main` already has it.

**To reproduce run 2** from the repo root, after the clean and overlap steps in the log:

```bash
git fetch upstream
mkdir -p out/gold_main
git show 6b09da4:teams/02-data-b/gold/cadj-commits_gold.csv > out/gold_main/cadj-commits_gold.csv
sha256sum out/gold_main/cadj-commits_gold.csv     # ba4da5c2…
# config: copy out/dedup_diag.json to out/dedup_diag2.json, set
#   "gold_dirs": ["teams/01-data-a/gold", "teams/02-data-b/gold", "out/gold_main"], "out": "out/dedup_diag2"
python teams/01-data-a/dedup/dedup.py --config out/dedup_diag2.json   # harm check: pass
```

### E4, measured part: the 50-word minimum and Indic text

**Source:** TSAI's 38-pack overlap rerun on the #244 cleaning (all 1,414,996 documents, Data B's Indic packs included; section 1), not the gold sets or the week-1 diagnosis packs. No document text was read. The 5 Nov run gave the same 106 rejected pairs.

**Method:**
1. From `overlap_pairs.csv` (every pair at word Jaccard ≥ 0.50), keep the pairs inside each `sangraha-s` pack with word Jaccard ≥ 0.80.
2. Check each pair against `overlap_matches.csv`: did it qualify under the family rules?
3. For each pair that did not qualify, look up both documents' `words` in `overlap_docs.parquet`, the same count `overlap_rules.py` uses for the 50-word minimum.

For prose (which includes Indic), a pair qualifies only if its word Jaccard is ≥ 0.80 and both documents have ≥ 50 words. Every pair kept in step 1 already passes the score, so the length rule is the only possible reason for a rejection; the "Rejected: other" column below is 0, which confirms it. The shares of documents under 50 words come from the same `words` column, over every document of each pack.

Every near-identical pair (word Jaccard ≥ 0.80) that was rejected in the three `sangraha-s` packs was rejected because a document has fewer than 50 words:

| Pack | Pairs ≥ 0.80 | Qualify | Rejected: a document < 50 words | Rejected: other |
|---|---:|---:|---:|---:|
| `ind-kn-sangraha-s` | 20 | 0 | 20 | 0 |
| `ind-te-sangraha-s` | 32 | 0 | 32 | 0 |
| `ind-ta-sangraha-s` | 55 | 1 | 54 | 0 |
| `ind-hi-sangraha-s` (for comparison) | 584 | 579 | 5 | 0 |

Share of documents under 50 words, by family: **Indic 20.0%**, code 14.1% (code uses a 20-line minimum, not words), science 2.8%, English 1.7%, math 1.4%, code-adjacent 1.2%. Among the Indic packs it is concentrated in `ind-hi-indiccorp` (56.9%, median 42 words) and the `sangraha-s` packs (14.5–18.4%); the `fw2` and `sangraha-v` packs are 0–3.1%.

So the 50-word minimum, set on English, leaves about a fifth of Indic documents to H1 only (Risk 2). Still open: a reader to judge whether the 106 rejected `sangraha-s` pairs are true copies. If they are, a lower word minimum for Indic is the fix (a minimum in characters would not separate these pairs; see the rebuild below); it changes `overlap_rules.py` and needs an overlap rerun.

### E4, rebuilt from the raw text (11 Nov; redone on the rerun, 16 Nov)

**Source:** the 106 pairs, from the rerun's `overlap_pairs.csv`, `overlap_matches.csv` and `overlap_docs.parquet`, with each document's text taken from the raw sample-v0 parts of the three packs (all 6 match `inputs/sample_v0/SHA256SUMS`). `e4_review.py` rebuilds each document's H1 key and 5-grams as `overlap.py` does. Document text stays in the git-ignored `out/e4_rerun/`; only counts are given here. **The rerun gives the same 106 pairs as the 5 Nov run**, with the same pair IDs and scores, and the blind review sheets are byte-identical.

**Raw text versus what TSAI scored.** TSAI scored the parts cleaned by #244, and cleaning changed two of the three packs:

| Pack | Documents, raw → cleaned | Cleaned documents whose raw text gives TSAI's word and 5-gram counts | Rejected pairs whose raw text gives TSAI's score |
|---|---:|---:|---:|
| `ind-kn-sangraha-s` | 5,244 → 5,238 | 3,824 (73.0%) | 20 of 20 |
| `ind-te-sangraha-s` | 4,829 → 4,463 | 4,338 (97.2%) | 32 of 32 |
| `ind-ta-sangraha-s` | 4,372 → 4,372 | 4,372 (100%) | 54 of 54 |

Every rejected pair gives TSAI's score from the raw text (to its 6 decimals), so all 106 were rebuilt from the text TSAI scored, even in the two packs that cleaning changed.

**What the pairs are, by the numbers** (no reading needed):

| Pack | Rejected pairs | Distinct documents | Clusters (sizes) | Shorter document of each pair | Words that differ, each side | Would qualify with a minimum of 40 / 30 / 20 / 10 words |
|---|---:|---:|---|---|---|---|
| `ind-kn-sangraha-s` | 20 | 10 | 2 (8, 2) | 17 words (1 pair), 30–39 (19) | 1–4 | 0 / 19 / 19 / 20 |
| `ind-te-sangraha-s` | 32 | 9 | 1 (9) | 30–39 (29), 40–49 (3) | 1–5 | 3 / 32 / 32 / 32 |
| `ind-ta-sangraha-s` | 54 | 16 | 1 (16) | 30–39 (54) | 1–4 | 0 / 54 / 54 / 54 |

- The 106 pairs come from only **35 documents in 4 clusters**. Every pair is within the train split, and the two documents differ by only 1–5 words per side. That fits either short copies or one fixed text with a word changed; only a reader can say which.
- A character minimum would not separate them either: their H1 keys have 148–366 characters.
- **What is at stake:** with one document kept per cluster, a 30-word minimum would remove 30 documents of the 14,062 in the three packs (31 with a 10-word minimum).

**Across all `ind-*` packs** (TSAI's outputs only): the 50-word minimum rejects 135 prose pairs ≥ 0.80 with an `ind-*` side, among 69 documents, and no other rule rejects any. A minimum of 40 / 30 / 20 / 10 words would admit 3 / 106 / 111 / 135 of them (3 / 35 / 42 / 69 documents). So although 20.0% of Indic documents are under 50 words, few of them are in near-identical pairs: lowering the minimum affects at most 69 documents across the 22 Indic packs.

**Still open: the reading.** The blind review sheets are ready in `out/e4_rerun/review/<pack>/` (zipped per language in `out/e4_rerun/`), on the local machine and not in the repo; TSAI asked on 16 Nov that they go to the readers privately, not on the GitHub issues (#392). Each sheet shows the two texts of every pair side by side, in random order, without scores, lengths or IDs, and comes with a `labels.csv` to fill in (copy, template, different or unsure). The labels must come from a human reader of the language, and theirs are the E4 result.

To repeat this, run `python3 -B teams/01-data-a/dedup/e4_review.py --tsai out/overlap_rerun --out out/e4_rerun` from the repo root. It needs the raw parts in `inputs/sample_v0/packs` (or `--raw`) and the rerun's outputs in `out/overlap_rerun`; its tests are in `tests/test_e4_review.py`.

## 4. Still to come

Updated 17 Nov. Done: the #244 cleaning, the overlap rerun (#469), the reviewed matrix (`dedup/overlap_matrix.csv`, `matrix_confirmation.md`) and the dedup job (#547), all in section 1.

| Result | From | Needs |
|---|---|---|
| Groups whose survivor F2 removes: count and list | The F2 step, after dedup (Clean → Dedup → F2), in the pipeline job | F2's removals and #547's `dedup_groups.csv` |
| Harm check with the #244 cleaner | Local, on the 4 diagnosis packs | Still needs to run with the merged cleaner; sample-v0 `not_testable` checks do not replace it |
| Hand review: prose 0.80, code 0.85, `cadj-commits` sample | Pairs from the rerun | `overlap_pairs.csv` and text |
| E4: are the rejected `sangraha-s` pairs true copies? | A human reader of Kannada, Telugu and Tamil (#392) | The readers' labels on the blind sheets (rebuilt on the rerun, unchanged) |
| Licence map in `dedup.json` | G10 | All 38 packs treated as usable for this experiment only (see the top) |
