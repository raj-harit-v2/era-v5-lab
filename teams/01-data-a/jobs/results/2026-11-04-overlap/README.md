# Results: G1 overlap job (PR #255), 2026-11-05

Job request: `teams/01-data-a/jobs/2026-11-04-overlap.md`. Approved by the Data A lead.
TSAI ran it on a CPU host. Code: PR #255 head `86ecdd4460a4137baf78597e83eb0f872642dc55`.
Input: the 38 cleaned tokenizer sample v0 packs (`tokenizer_sample_v0_clean`), 86 parts, train + heldout.

| Item | Value |
|---|---|
| Status | complete, exit 0 |
| Wall time | 3,351 s (56 min) |
| Peak RSS | 9.8 GB |
| Documents | 1,416,236 (7 empty) |
| Pairs that share a shingle | 2,347,235,732 |
| Pairs stored (Jaccard >= 0.50) | 32,738 |
| Qualifying duplicates | H1: 98 pairs (71 exact groups, 150 docs). H2: 2,613 pairs |
| Within pack / cross pack | 2,661 / 50 |
| Train x heldout pairs among the matches | 63 |

Largest sources of near-duplicates (pairs at Jaccard >= 0.80): cadj-commits 1,094, ind-hi-sangraha-s 545,
cadj-stackexchange 208, ind-hi-sangraha-v 134, math-megamath 100. Cross-pack overlap is small: the largest
exact cross-pack group is code-java x code-js-ts (8 pairs).

Files here: `overlap_summary.json`, `overlap_matrix.csv`, `overlap_matrix_counts.csv`, `overlap_by_pack.csv`,
`overlap_histogram.csv`, `overlap_matches.csv`, `run.log`. Three large files are not in the repo:
`overlap_pairs.csv` (6.7 MB), `overlap_matrix.npz` (4.4 MB) and `overlap_docs.parquet` (34 MB). Ask TSAI in G1 if
you need them. SHA-256 of all outputs is in `overlap_summary.json` under `outputs`.

Note: a first start on 5 Nov stopped when the host restarted during loading. This is the second run, with no change in code or input.
