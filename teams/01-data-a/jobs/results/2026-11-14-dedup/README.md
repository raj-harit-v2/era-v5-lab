# Results: G1 dedup job (PR #255), 17 Nov 2026

Job request: `teams/01-data-a/jobs/2026-11-14-dedup.md`. Approved by the Data A lead. TSAI ran it on a CPU host.
Code: `teams/01-data-a/dedup/dedup.py` at `6cfc24ada545c7b64c33f0afb9661c3979ae3c18`, config `dedup.json`.
Inputs: the returned outputs of the overlap rerun (#469) and the cleaned sample v0 parts (cleaner sha256 `22d818c7...`).

| Item | Value |
|---|---|
| Status | complete, 4.2 s |
| Documents | 1,414,996 (7 empty, listed, not removed) |
| Matches used | 2,729 in 1,084 clusters |
| Removed | 1,345 (0.0951%): H2 1,289, H1 56 |
| By stage | within pack 1,309, cross pack 36 |
| By priority rule | rule 0: 64, rule 2: 21, rule 3: 920, rule 4: 340 |
| Held-out removed | 0 |

These match the totals the Data A request expected: 1,345 removed, 64 by rule 0, 0 held-out removed.

Files: `remove_list.csv`, `dedup_log.jsonl`, `heldout_duplicates.csv`, `empty_documents.csv`, `dedup_groups.csv`, `dedup_summary.json`.
The harm check is `not_testable` and the licence map is not filled for the 38 packs (the default was used), as the job request notes.
