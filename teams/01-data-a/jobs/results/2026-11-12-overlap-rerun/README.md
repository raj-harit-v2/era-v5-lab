# Results: G1 overlap rerun (PR #255), 15 Nov 2026

Job request: `teams/01-data-a/jobs/2026-11-12-overlap-rerun.md`. Approved by the Data A lead.
TSAI ran it on a CPU host. Code: PR #255 at `7526194f6a9cafd64416ff30fd149d19660d31f8`. v1 thresholds, unchanged.
Input: the 38 sample-v0 packs cleaned by the merged #244 cleaner (86 parts, 1,414,996 documents; cleaner sha256 `22d818c72c9f30bf338de344a0fcda230e2d1de30a1aaec5d92bc525bae99179`, rebuilt by TSAI on 15 Nov with the same hash).

| Item | Value |
|---|---|
| Status | complete |
| Documents | 1,414,996 (7 empty) |
| Run time | 4,591 s (77 min) |
| Pairs that share a shingle | 2,345,501,632 |
| Pairs stored (Jaccard >= 0.50) | 32,329 |
| Qualifying duplicates | H1: 98 pairs (71 exact groups, 150 documents). H2: 2,652 pairs |
| Pairs at Jaccard >= 0.80 / 0.90 / 0.95 | 2,446 / 1,122 / 333 |

The 5 Nov run on the old cleaning gave 2,711 qualifying pairs (98 H1, 2,613 H2). This run gives 2,750 (98 H1, 2,652 H2).

Files here: `overlap_summary.json`, `overlap_matrix.csv`, `overlap_matrix_counts.csv`, `overlap_by_pack.csv`, `overlap_histogram.csv`, `overlap_matches.csv`. Three large files are not in the repo: `overlap_pairs.csv` (6.6 MB), `overlap_matrix.npz` (4.4 MB), `overlap_docs.parquet` (34 MB). Their sha256 values are in `overlap_summary.json`. Ask TSAI for a download link.

Next for Data A: confirm the matrix, run dedup locally, record expected totals, then ask for the dedup job (see the comment on #255).
