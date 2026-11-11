# OpenCodeReasoning-2 question join: coverage so far (10 Nov)

Aggregates and replay commands only. Rows, statements, completions and document ids stay in the private
run folder. Every number is labelled **measured** (read from a run record of this work), **inferred**
(reasoned from something measured) or **not measured**.

## Full run: all 70 Python shards (measured, run of 10 Nov)

All 70 shards of the pinned Python split ran end to end in diagnostic mode, 67 of them on Modal CPU in
parallel containers and shards 0 to 2 locally. Every shard is a full 20,000-row file at revision
`eadf535931451525f3e5621d0f960c240bc62fd9`, each verified against its recorded size and sha256 before use.

| Stage | Rows |
|---|---:|
| Raw | 1,398,166 |
| Upstream test splits excluded | 268,752 |
| Protected family | 3,629 |
| Quality proposal, critique wrong | 310,019 |
| Quality proposal, pass_rate under 1 | 203,790 |
| Held, source revision unestablished | 69,690 |
| **Joined** | **542,286** |
| Converter rejected | 67 |
| Rendered | 542,219 |
| Flagged by fingerprint set v2 | 115,067 |
| Kept | 427,152 |
| **Admitted** | **0** |

Conservation holds exactly: 1,398,166 = 268,752 + 3,629 + 310,019 + 203,790 + 69,690 + 542,286, and
542,286 − 67 − 115,067 = 427,152. Every held row names `open-r1/codeforces`, the one source whose producer
revision is not established. Rendered and kept rows were counted in every shard; 0 canaries were found.

### How many distinct problems this actually is

| | Joined | Kept (after the scan) |
|---|---:|---:|
| Rows | 542,286 | 427,152 |
| Distinct problems by position | **19,825** | **15,670** |
| Distinct problems by content, Jaccard 0.8 | **19,340** | **15,402** |
| Trained tokens | **3,400,978,077** (over the 542,219 rendered rows; the 67 converter-rejected rows have none) | **2,539,177,884** |
| Rows per content cluster, mean / max | not recorded | 27.7 / 349 |
| Tokens per content cluster, mean (all rendered tokens, not trained-only) | not recorded | 176,274 |

The 1,398,166 figure is rows, not problems. The same problem recurs across shards within a source;
cross-source collapse is small (365 clusters at 0.8 over the joined rows, 169 over the kept rows). The supply
figure for the mix is the kept one: **2.54B trained tokens across roughly 15,400 distinct problems** (15,402 by
content at Jaccard 0.8), not a row count.

### What the full run does not settle

- **Gate D1 row-level reconciliation is impossible.** The historical run's `record.json` no longer exists,
  and its 4,200 removed was counted before the join on rows whose question was `-`, so it is not the same
  quantity as any count here. The difference can only be recorded by definition.
- **Admission is unchanged.** The set is `TSAI reserves`, no tokenizer is approved, and
  `--mode admission` exits 3 without creating a folder.
- The quality thresholds are a proposal in `ocr2_policy.json`, not a ruling. On the first three shards,
  pass_rate 0.9 recovers 2,421 rows and 445 problems; 0.5 recovers 6,694 and 1,259.

## Earlier runs kept as history

The two-shard run of shards 0 and 1, the single-shard run of shard 0, and the 1,000-row prefix run are
described below. Their numbers are subsets of the table above and are retained for provenance.


- It is a **diagnostic scan of shards 0 and 1, the full files**: all 20,000 rows of each of
  `train/python/train-00000-of-00070.parquet` (sha256 `18f09c9b93a4…`, 366,930,945 bytes) and
  `train/python/train-00001-of-00070.parquet` (sha256 `21f5d72fb28a…`, 366,805,860 bytes) at OCR-2 revision
  `eadf535931451525f3e5621d0f960c240bc62fd9`. Both files equal the Hub LFS hash and size (measured).
- It is **two of 70 Python shards**, not the dataset. It is **not** an eligible retained subset anyone
  approved and **not** a pack. The set is `TSAI reserves` in `licences/licence_table.md`, so
  `pack_admission.py --mode training` refuses it. **0 rows are admitted and no pack file exists.**
- It does **not** reproduce the historical 20,000 / 4,200 / 15,800 of `sft/decontam_report.md`: that run's
  script and scan record are not in the repository (see the end).
- The two-shard run comes first below. The single-shard run of shard 0 and the 1,000-row prefix run are
  kept after it as history.

## How the question is rebuilt

The dataset card at the pinned revision ("How to use it") gives the rule: the question of a row is
`hf_datasets[dataset][split][int(index)]`, read as `question` for TACO and APPS, as `description` for
code_contests, and as description + input format + output format + examples + note for
open-r1/codeforces. `index` is therefore the row position in the **original source split**. The card names
the four repositories but no revision and no hash, so each source is pinned here to an exact Hub revision
and every file is hash-checked before it is indexed.

| Source split | Repository | Pinned revision | Files | Rows in split | Used as |
|---|---|---|---|---|---|
| taco/train | `BAAI/TACO` | `d593ed0a2bec…` | 9 Arrow streams | 25,443 | join |
| taco/test | `BAAI/TACO` | `d593ed0a2bec…` | 1 Arrow stream | 1,000 | protected: statement hashes only |
| apps/train | `codeparrot/apps` | `21e74ddf8de1…` | `train.jsonl` | 5,000 | join |
| apps/test | `codeparrot/apps` | `21e74ddf8de1…` | `test.jsonl` | 5,000 | protected: statement hashes only |
| code_contests/train | `deepmind/code_contests` | `802411c3010c…` | 39 parquet (statement extraction) | 13,328 | join |
| open-r1/codeforces/train | `open-r1/codeforces` | `fbe3f6e903ee…` (today's head, reference only) | 11 parquet | 9,556 | **not indexed: held** (see below; no row in shards 0 and 1) |
| open-r1/codeforces/test | `open-r1/codeforces` | `fbe3f6e903ee…` | 1 parquet | 468 | protected: statement hashes only |

All row counts are measured from the pinned files. Each revision was the head of its repository on
10 Nov 2026 (Hub API, measured). TACO and APPS ship a loader script; it was read as text to learn the row
order (files in the listed order, rows in file order, default config filters nothing) and never executed.

Evidence that the pinned snapshot is the one the producer indexed (measured unless marked). The per-row
check counts rows that agree on difficulty and platform with the original row at `index`; the control is
the same check at index+1.

| Source | Data files last changed | Shard 0: agree | Shard 0: control | Shard 1: agree | Shard 1: control |
|---|---|---|---|---|---|
| TACO train | 20 Dec 2023 | 11,678 / 11,678 | 666 | 11,734 / 11,734 | 686 |
| TACO test | 19 Jun 2024 | 401 / 401 | 30 | 387 / 387 | 24 |
| APPS train | 15 Jun 2022 | 495 / 495 | 482 | 481 / 481 | 471 |
| APPS test | 15 Jun 2022 | 2,175 / 2,175 | 2,100 | 2,211 / 2,211 | 2,133 |
| code_contests train | 19 Jul 2022 | 5,251 / 5,251 | 1,369 | 5,187 / 5,187 | 1,371 |
| open-r1/codeforces | 15 May 2025 | no row: not measured | not measured | no row: not measured | not measured |

- The OCR-2 data upload is dated 16 May 2025 and the card gives March to May 2025 as the creation window.
  For TACO, APPS and code_contests the data files did not change during or after that window, so a load of
  the default branch at that time read the pinned bytes (**inferred** from the commit history).
- The per-row check compares the `difficulty` and `source` that each OCR-2 row repeats with the original
  row at `index`. For TACO and code_contests the control shows the check would notice a shifted or
  reordered split. **For APPS the control is 97%**, because neighbouring APPS problems share difficulty and
  platform: there the check is weak, and the evidence is the unchanged files plus the fact that the row
  position equals the problem id in both APPS splits (measured).
- code_contests: the comparison used the platform names of the card's `Source` enum and accepted the OCR-2
  difficulty when it equals either the Codeforces rating or the difficulty class of the original row. That
  rule was fitted to shard 0, so read the 5,251 as support, not proof; the 5,187 of shard 1 use the same
  rule unchanged, on rows it was not fitted to. Separately, all 13,328 statements of
  the extraction equal the `description` column of the pinned revision row for row (read by range request;
  the 39 raw files were not downloaded and their hashes are listed, not verified).
- **open-r1/codeforces is not established.** Its default config went through 25 distinct states between Feb and
  15 May 2025, most of them inside the creation window, and nothing says which state the producer indexed. Its statement terms
  conflict (Hub tag `cc-by-4.0`, card text ODC-By 4.0) and Team 9's confirmation for the Codeforces pool is
  open. The whole pinned train split was checked against the card's recipe recomputed outside this code:
  9,556 / 9,556 agree, 43 of them have no description and give no question.
  **From the two-shard run on, its train split is therefore not a source at all**: the source manifest lists
  it under `unavailable_sources`, the index does not contain it, and a row that names it ends as
  `held_source_unavailable` instead of being joined against today's head. Its test split stays in the index
  as statement hashes only, which can hold a row out and can never join one. Shards 0 and 1 name no
  open-r1/codeforces row (measured), so the hold is shown on relabelled probe rows passed through the real
  index and the unchanged policy: of 2,000 probe train rows with judgement `right` and pass_rate 1.0, 2,000
  end as `held_source_unavailable`; of 2,000 probe test rows, 2,000 end as `policy_protected_split`; none
  is eligible. One thing to know: the quality proposal is applied before the source lookup, so a
  Codeforces train row with a `wrong` critique or a pass_rate under 1.0 is counted under its quality outcome,
  not as held (1,223 held, 777 on quality, 0 eligible in the as-is probe). Either way it is left out.
- Every source stays at identity level `diagnostic` in the source manifest. Promoting one to `verified` is
  a review decision, not something a helper script does.

## Counts per stage, shards 0 and 1 (all measured, run `diagnostic-0a023522c939`)

| Stage | Attempted | Left out | Passed on | Emitted to training |
|---|---|---|---|---|
| join (`prepare_ocr2.py`) | 40,000 raw rows | 18,982 policy excluded + 0 unresolved | 21,018 eligible joined | 0 |
| render (`convert.py`, Team 3 v0.1 tokenizer) | 21,018 | 0 converter rejected | 21,018 rendered | 0 |
| scan (`decontam_run.py`, full v2 set `2826a3b8…`) | 21,018 | 4,557 flagged, 0 canary | 16,461 kept | 0 |
| second pass over the kept files | 16,461 | 0 hits | 16,461 | 0 |
| pack admission (report mode) | 16,461 | 0 row-level rejects | 16,461 pass the row checks | **0 admitted** |

Conservation holds exactly, per shard and in total: 40,000 = 18,982 + 0 + 21,018; 21,018 = 0 + 21,018;
21,018 = 4,557 + 16,461; 16,461 = 0 + 16,461. The 40,000 OCR-2 row ids are distinct across the two shards
and so are the 21,018 rendered ids (shard 1 starts at id 20,000).

Per source and shard (measured). "Resolved" is counted for every row, whatever the policy says about it:
the index is canonical, inside the pinned split, and the original row has a statement (for a test split:
a statement hash).

| Shard | Source split | Rows in | Resolved | Protected | Left out on the quality proposal | Held | Failed | Eligible joined | Flagged | Kept after scan | Admitted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | taco/train | 11,678 | 11,678 | 0 | 5,194 | 0 | 0 | 6,484 | 806 | 5,678 | 0 |
| 0 | code_contests/train | 5,251 | 5,251 | 0 | 1,460 | 0 | 0 | 3,791 | 1,461 | 2,330 | 0 |
| 0 | apps/train | 495 | 495 | 23 | 175 | 0 | 0 | 297 | 49 | 248 | 0 |
| 0 | apps/test | 2,175 | 2,175 (hash only) | 2,175 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0 | taco/test | 401 | 401 (hash only) | 401 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0 | **all** | **20,000** | **20,000** | **2,599** | **6,829** | **0** | **0** | **10,572** | **2,316** | **8,256** | **0** |
| 1 | taco/train | 11,734 | 11,734 | 0 | 5,311 | 0 | 0 | 6,423 | 788 | 5,635 | 0 |
| 1 | code_contests/train | 5,187 | 5,187 | 0 | 1,460 | 0 | 0 | 3,727 | 1,415 | 2,312 | 0 |
| 1 | apps/train | 481 | 481 | 20 | 165 | 0 | 0 | 296 | 38 | 258 | 0 |
| 1 | apps/test | 2,211 | 2,211 (hash only) | 2,211 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | taco/test | 387 | 387 (hash only) | 387 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | **all** | **20,000** | **20,000** | **2,618** | **6,936** | **0** | **0** | **10,446** | **2,241** | **8,205** | **0** |
| 0+1 | taco/train | 23,412 | 23,412 | 0 | 10,505 | 0 | 0 | 12,907 | 1,594 | 11,313 | 0 |
| 0+1 | code_contests/train | 10,438 | 10,438 | 0 | 2,920 | 0 | 0 | 7,518 | 2,876 | 4,642 | 0 |
| 0+1 | apps/train | 976 | 976 | 43 | 340 | 0 | 0 | 593 | 87 | 506 | 0 |
| 0+1 | apps/test | 4,386 | 4,386 (hash only) | 4,386 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0+1 | taco/test | 788 | 788 (hash only) | 788 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0+1 | open-r1/codeforces | 0 | not measured (train split held, not indexed) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0+1 | **all** | **40,000** | **40,000** | **5,217** | **13,765** | **0** | **0** | **21,018** | **4,557** | **16,461** | **0** |

- Protected = 5,174 rows of an upstream test split (`policy_protected_split`: 2,576 + 2,598) + 43
  apps/train rows whose statement is also in an indexed test split (`policy_protected_family`: 23 + 20).
- Left out on the quality proposal = 4,532 with a critique of `wrong` (2,243 + 2,289) + 9,233 with a
  pass_rate under 1.0 (4,586 + 4,647). These thresholds are a proposal in `ocr2_policy.json`, not a ruling.
- Held is 0 because no row of these two shards names a source that is missing from the index. The only
  held source is open-r1/codeforces/train, and no row names it.
- Shard 1 on its own: of the 10,446 joined rows, 9,466 have an execution pass and 980 have no execution
  evidence; of the 8,205 kept rows, 7,332 and 873. Flag hits by benchmark: `livecodebench` 1,675,
  `codeforces` 942, `hle` 48 (one row can hit several). Rendered: 66,448,651 tokens, 61,770,871 trained.
  Kept: 53,244,815 tokens, 49,496,582 shifted assistant targets, length p50 5,515, p95 14,706, max 17,344
  (v0.1 tokenizer, so these are not final pack numbers). The same numbers for shard 0 are in the next section.

### Rows are not problems (measured)

OCR-2 holds several solutions per problem, and the two shards mostly hold the same problems. A problem
here is one original row (dataset, split, `index`). In these two shards that is the same count as distinct
statements (exact text after whitespace folding) and as distinct OCR-2 `question_id`: the three agree one
to one for all 6,144 joined problems.

| | Shard 0 | Shard 1 | Both shards | Problems present in both shards |
|---|---|---|---|---|
| Eligible joined rows | 10,572 | 10,446 | 21,018 | |
| Distinct problems among them | 5,547 | 5,574 | 6,144 | 4,977 |
| Kept rows after the scan | 8,256 | 8,205 | 16,461 | |
| Distinct problems among them | 4,343 | 4,384 | 4,839 | 3,888 |

- Distinct problems in both shards by source: joined taco 3,838, code_contests 2,156, apps 150; kept taco
  3,361, code_contests 1,351, apps 127.
- Adding shard 1 doubled the rows and added 597 joined problems (5,547 to 6,144) and 496 kept problems
  (4,343 to 4,839). A per-shard family count must not be summed across shards: 5,547 + 5,574 = 11,121 would
  overstate the 6,144 by 81%.
- The scan decides per row, not per problem. Of the 6,144 joined problems, 4,799 have no flagged row, 1,305
  have every row flagged and 40 have both: 102 kept rows belong to a problem that also has a flagged row.
  Whether such a problem should be removed as a whole is a decision for the lead and Team 9; nothing is
  changed here.
- Near-duplicate statements are not found by this identity (exact text only).

Checks on the real rows of both shards (measured):

- **Upstream test rows: 5,174 in the two shards (2,576 + 2,598), 5,174 in the `exclusions.jsonl` files, all
  with outcome `policy_protected_split`, and 0 in each joined file, joined sidecar, rendered file, kept file
  and kept sidecar.** No admitted pack file exists in either shard folder.
- All 21,018 joined questions equal the original row when recomputed outside this code (TACO 12,907 from
  the Arrow streams, code_contests 7,518, APPS 593); all 16,461 kept rows contain the statement of their
  own original row.
- A fresh second run in a new folder, with `--workers 2` instead of 1, gives the same run hash
  (`ea5f2575e977cca5…`), the same per-shard hashes and the same five stage hashes for each shard.
  `--resume` on the finished folder reruns nothing and leaves the hash unchanged. `--mode admission` exits
  3 and creates no folder.
- Shard 0 against the earlier single-shard run: the joined file, the exclusions, the rendered file and the
  kept file are byte-identical. Only the `family_sources` list of 939 sidecar rows differs, because
  open-r1/codeforces/train is no longer in the index, so the stage hashes of shard 0 differ from that run
  as they should (statements also present in another indexed source: 3,547 now, 3,597 then).
- Time and memory on a laptop CPU: 2,212 s wall with one worker, 1,142 s with two; peak 1.06 GB per
  process; 3.5 GB of private run files per run.

Against the historical shard-0 numbers (20,000 in, 4,200 removed, 15,800 kept): see the shard-0 section
below. Shard 1 behaves the same way: 2,241 of 10,446 scanned rows are flagged (21.5%).

## Earlier run: shard 0 alone (all measured, run `diagnostic-2badf43469a5`)

Kept as history. In this run open-r1/codeforces/train was still in the index (no row named it). Row files
of shard 0 are byte-identical to the two-shard run above.


| Stage | Attempted | Left out | Passed on | Emitted to training |
|---|---|---|---|---|
| join (`prepare_ocr2.py`) | 20,000 raw rows | 9,428 policy excluded + 0 unresolved | 10,572 eligible joined | 0 |
| render (`convert.py`, Team 3 v0.1 tokenizer) | 10,572 | 0 converter rejected | 10,572 rendered | 0 |
| scan (`decontam_run.py`, full v2 set `2826a3b8…`) | 10,572 | 2,316 flagged, 0 canary | 8,256 kept | 0 |
| second pass over the kept file | 8,256 | 0 hits | 8,256 | 0 |
| pack admission (report mode) | 8,256 | 0 row-level rejects | 8,256 pass the row checks | **0 admitted** |

Conservation holds exactly: 20,000 = 9,428 + 0 + 10,572; 10,572 = 0 + 10,572; 10,572 = 2,316 + 8,256;
8,256 = 0 + 8,256.

Per source (measured). "Resolved" is counted for every row, whatever the policy says about it: the index
is canonical, inside the split, and the original row has a statement.

| Source split | Rows in | Resolved | Protected | Left out on the quality proposal | Held | Failed | Eligible joined | Flagged | Kept after scan | Admitted |
|---|---|---|---|---|---|---|---|---|---|---|
| taco/train | 11,678 | 11,678 | 0 | 5,194 | 0 | 0 | 6,484 | 806 | 5,678 | 0 |
| code_contests/train | 5,251 | 5,251 | 0 | 1,460 | 0 | 0 | 3,791 | 1,461 | 2,330 | 0 |
| apps/train | 495 | 495 | 23 | 175 | 0 | 0 | 297 | 49 | 248 | 0 |
| apps/test | 2,175 | 2,175 (hash only) | 2,175 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| taco/test | 401 | 401 (hash only) | 401 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| open-r1/codeforces | 0 | not measured | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **20,000** | **20,000** | **2,599** | **6,829** | **0** | **0** | **10,572** | **2,316** | **8,256** | **0** |

- Protected = 2,576 rows of an upstream test split (`policy_protected_split`) + 23 apps/train rows whose
  statement is also in an indexed test split (`policy_protected_family`). In all, 38 apps/train rows have
  such a statement; the other 15 had already been left out on quality.
- Left out on the quality proposal = 2,243 with a critique of `wrong` + 4,586 with a pass_rate under 1.0.
  These thresholds are a proposal in `ocr2_policy.json`, not a ruling.
- Held = no pinned source, source not approved, identity not verified, split not allowed or row licence not
  allowed. In a diagnostic run the first is the only one that can occur for a train split, and it is 0 now.
- Of the 10,572 joined rows, 9,573 have an execution pass and 999 have no execution evidence (tagged
  `exec_missing`, never counted as a pass). Of the 8,256 kept rows: 7,369 and 887.
- Flag hits by benchmark: `livecodebench` 1,710, `codeforces` 993, `hle` 42 (one row can hit several).
- The 10,572 joined rows cover 5,547 distinct statements; 3,597 of those statements also sit in another
  indexed source (TACO train repeats APPS and code_contests problems). The 8,256 kept rows cover 4,343
  distinct statements, 2,777 of them with more than one solution. Identity here is exact text after
  whitespace folding: near-duplicates are not found.
- The 10,572 rendered rows hold 67,398,739 tokens, 62,673,394 of them trained; the 8,256 kept rows hold
  53,566,110 tokens and 49,801,925 shifted assistant targets, length p50 5,490, p95 14,701, max 17,967
  (v0.1 tokenizer, so these are not final pack numbers).

Checks on the real rows (measured):

- **Upstream test rows: 2,576 in the shard, 2,576 in `exclusions.jsonl` with outcome
  `policy_protected_split`, and 0 in each of the joined file, its sidecar, the rendered file, the kept file
  and the kept sidecar.** No admitted pack file exists. The index holds a hash for each test statement and
  no test text.
- All 10,572 joined questions equal the original row when recomputed outside this code (TACO 6,484 from
  the Arrow streams, code_contests 3,791, APPS 297); all 8,256 kept rows contain the statement of their own
  original row.
- A fresh second run of the same command in a new folder gives the same deterministic hash
  (`a28c1b02310fac11…`) and the same five stage hashes; `--resume` on the finished folder reruns nothing
  (3 s). `--workers 2` was not rerun on real data: with one shard it cannot change the order.
- Time and memory, one worker on a laptop CPU: 1,124 s wall (scan 775 s, render 224 s, pack report 93 s,
  second-pass bookkeeping 15 s, index build 11 s, join 3 s), peak 0.99 GB, 1.9 GB of private run files.

Against the historical shard-0 numbers (20,000 in, 4,200 removed, 15,800 kept): this run scans 10,572
rows, not 20,000, because 2,599 protected rows and 6,829 rows under the quality proposal never reach the
scan. Of the scanned rows 2,316 are flagged (21.9%); the historical 4,200 of 20,000 is 21.0%. That the two
rates are close is an observation, **not** a reconciliation: which rows the 4,200 were is not measured here.

## Earlier run: pinned 1,000-row prefix

Kept as history. At that time only code_contests/train was pinned, so TACO and APPS train rows were held.

### Counts per stage, pinned 1,000-row prefix (all measured, run `diagnostic-bbfec59d0f80`)

| Stage | Attempted | Left out | Passed on | Emitted to training |
|---|---|---|---|---|
| join (`prepare_ocr2.py`) | 1,000 raw rows | 473 policy excluded + 342 unresolved | 185 eligible joined | 0 |
| render (`convert.py`, Team 3 v0.1 tokenizer) | 185 | 0 converter rejected | 185 rendered | 0 |
| scan (`decontam_run.py`, full v2 set `2826a3b8…`) | 185 | 68 flagged, 0 canary | 117 kept | 0 |
| second pass over the kept file | 117 | 0 hits | 117 | 0 |
| pack admission (report mode) | 117 | 0 row-level rejects | 117 pass the row checks | **0 admitted** |

Conservation holds exactly: 1,000 = 473 + 342 + 185; 185 = 0 + 185; 185 = 68 + 117; 117 = 0 + 117.

Join outcomes (one primary outcome per row, measured):

| Outcome | Rows | By upstream source and split |
|---|---|---|
| `policy_protected_split` | 123 | apps/test 102, taco/test 21 |
| `quality_critique_wrong` | 109 | taco/train 90, code_contests/train 19 |
| `quality_execution_failed` (pass_rate under 1.0) | 241 | taco/train 173, code_contests/train 57, apps/train 11 |
| `held_source_unavailable` | 342 | taco/train 321, apps/train 21 |
| `eligible_joined` | 185 | code_contests/train 185 |

Of the 185 joined rows, 181 have an execution pass and 4 have no execution evidence (tagged `exec_missing`,
never counted as a pass). Flag hits by benchmark: `livecodebench` 59, `codeforces` 30 (one row can hit both).
The 185 rendered rows hold 1,149,288 tokens, 1,061,247 of them trained; the 117 kept rows hold 774,721
tokens and 716,963 shifted assistant targets (v0.1 tokenizer, so these are not final pack numbers).

Checks on the real rows (measured):

- None of the 123 upstream test rows is in the joined, rendered or kept file.
- All 185 joined questions equal the statement at `int(index)` of the pinned code_contests train extraction
  when recomputed outside this code; all 117 kept rows contain the statement of their own original row.
- One raw code_contests parquet (342 rows) matches the extraction segment at ordinal 684 row for row.
- A fresh second run with `--workers 2` gives the same deterministic hash
  (`df445e61390591b0…`); `--resume` on the finished folder reruns nothing.
- Against the 6 Nov sample check (242 rendered, 87 flagged, 155 kept): the 57 rows missing here are exactly
  the code_contests rows with a pass_rate under 1.0. On the 185 shared rows the flag decision is the same
  for every row. The rendered text differs only in whitespace (the branch adapter strips the think span).

## Why training admission is refused today (measured, from `pack_report.json` of both shards)

`set_not_allowed_in_policy`, `set_not_allowed_in_licence_table`, `join_not_in_admission_mode`,
`source_not_approved_for_training:{taco, apps, code_contests}`,
`source_identity_not_verified:{taco/train, apps/train, code_contests/train}`, `tokenizer_not_approved`,
`context_limit_not_set`. `run_ocr2.py --mode admission` exits 3 before creating its run folder.

## Not measured, or not built

- Shards 2 to 69: no local input. The manifest lists all 70 shard paths with the Hub's LFS sha256 and size
  (30,396,891,890 bytes in total, measured from the Hub listing at the pinned revision); **the row count is
  measured for shards 0 and 1 only** (20,000 each), so the id range of shard 2 starts at 40,000 and no
  later range exists yet.
- The join rate of open-r1/codeforces: shards 0 and 1 name no such row, and its train split is held.
- code_contests valid and test are not indexed, so a train row whose statement is also a code_contests
  valid or test problem is not held out yet. TACO, APPS and open-r1/codeforces test splits are indexed.
- Family de-duplication across shards and near-duplicate review: not built. The family key is in each
  sidecar, and the overlap between shards 0 and 1 is counted above.
- The quality thresholds (`judgement == right`, `pass_rate == 1.0`) and the row-licence list in
  `ocr2_policy.json` are a proposal. They are not a TSAI or lead ruling.
- The final frozen tokenizer: every token number here uses Team 3 v0.1.

## Tests

`bash teams/10-post-training/sft/verify.sh` runs the three new test files and the two existing ones of the
reused tools; a skipped test counts as a failure.

| Failure to catch | Test |
|---|---|
| Off-by-one, global against file-local ordinal | `test_first_last_ordinal_and_the_file_boundary` |
| Source cache keyed wrongly | `test_same_index_in_two_sources_and_two_splits` |
| Negative, fractional, boolean, padded, out-of-range index | `test_parse_ordinal_refuses_everything_else`, `test_bad_indexes_never_resolve_and_minus_one_is_not_the_last_row` |
| Valid index under a reordered or other revision | `test_a_reordered_or_other_revision_source_file_stops_the_build`, `test_an_index_built_from_another_manifest_is_not_reused`, `test_identity_cross_check_must_hold` |
| Upstream APPS or TACO test row under a train path | `test_upstream_test_rows_never_join_and_their_text_is_not_stored` |
| Existing question disagrees | `test_a_question_already_in_the_row_must_agree` |
| Unknown teacher or licence, reserve in training mode | `test_admission_mode_is_refused_under_a_reserve_ruling`, `test_admission_mode_needs_a_known_approved_teacher_and_licence`, `test_one_missing_approval_closes_the_gate` |
| Repeated problem, train and test copies of one problem | `test_families_are_tracked_and_a_test_problem_is_held_out_of_train` |
| Join exclusion, then converter skip, then scan removal | `test_exclusion_then_converter_skip_then_scan_removal_keeps_row_identity` |
| Shard with nothing eligible or renderable | `test_shards_with_nothing_to_join_or_render_get_no_scan_credit_and_are_not_retried` |
| Broken or oversized reasoning trace | `test_exclusion_then_converter_skip_then_scan_removal_keeps_row_identity` (both skip reasons are counted) |
| Empty shifted target, context overflow | `test_a_row_with_no_shifted_assistant_target_is_rejected`, `test_row_checks` |
| Kill after each stage, rerun twice | `test_killed_at_any_stage_then_rerun_twice_gives_the_same_result` (5 stages x 2 stop points) |
| Reordered workers | `test_worker_count_and_order_do_not_change_ids_or_hashes` |
| A source in its own file format read in another order (Arrow batches, several files) | `test_arrow_stream_files_resolve_in_stream_order_across_batches_and_files` |
| An Arrow file the TACO loader could not read, or a reordered one | `test_an_arrow_file_that_is_not_the_pinned_stream_stops_the_build` |
| One of the four card sources assembled differently from the card | `test_all_four_publisher_sources_resolve_at_the_card_recipe`, `test_codeforces_question_follows_the_publisher_recipe` |

Fixtures are synthetic placeholders built in a temporary folder. They carry `test_fixture: true` and
`pack_admission.py` refuses a pack from such a run (`test_a_fixture_run_is_never_a_training_pack`).

## Replay

```sh
G=teams/10-post-training
export G10_DECONTAM_TOOLS="$G9_MAIN/teams/09-evaluation/decontam"   # lab main at b470b4c or later, with fingerprints v2
bash "$G/sft/verify.sh"
python "$G/sft/run_ocr2.py" --manifest "$SOURCE_MANIFEST" --policy "$G/sft/ocr2_policy.json" \
  --shards 0:70 --workers 1 --out-dir "$RUN" --mode diagnostic
python "$G/sft/run_ocr2.py" --manifest "$SOURCE_MANIFEST" --policy "$G/sft/ocr2_policy.json" \
  --shards 0:70 --workers 1 --out-dir "$RUN" --resume
```

`$SOURCE_MANIFEST` is private (it holds local paths). It pins the OCR-2 revision and the 70 shard
identities, each local input, each original split (repository, revision, ordered files, row counts,
sha256), the tokenizer file and Team 9's tools and set hash. An unset one stops the run.

## Open: reconciling with the historical shard-0 numbers

`sft/decontam_report.md` section 7 and the mix proposal record shard 0 as 20,000 rows in, 4,200 removed,
15,800 kept, "after joining questions from TACO, APPS, and code_contests by `dataset` + `index`". Commit
`8cd0fb9` changed three report files only: the join script, its inputs and the scan record are not in the
repository. Those three numbers are kept as historical evidence. Nothing here reproduces or re-derives them.

The join itself no longer waits on that run: the dataset card publishes the rule, and the sources are
pinned above. What is still needed from the owner of that run (`saitej123`) to explain every difference
row by row:

1. the scan record `sft-code-opencodereasoning-2.record.json` (clean file `7a56ebc206c3…`), which lists
   the flagged ids;
2. whether the 2,576 upstream test rows were joined and scanned, and which revisions were loaded.
