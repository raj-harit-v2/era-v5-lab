> Historical request, superseded by [the all-cleaned-pack overlap job](2026-11-04-overlap.md).
> The counts, checksums and raw-English benchmark below describe the earlier implementation.
> Current `overlap.py` uses cleaned inputs and the current JSON schema; use the all-pack request for TSAI submission.

# Cross-pack overlap of the four English packs (sample v0, all-to-all Jaccard)

```
Team:            01-data-a
Owner:           Aneesha Das (aneeshads)
Lead approval:   Pending team-lead review/approval on the job-request PR
Question:        How much do the four English packs of the Week-2 tokenizer sample v0 overlap, inside each pack and across packs, by exact word 5-gram Jaccard over every pair of documents?
Script:          teams/01-data-a/dedup/overlap.py   (this PR, with h1_sha256.py and jaccard_matrix.py; uses spec_v1/tools/normalize.py, frozen)
Command:         python teams/01-data-a/dedup/overlap.py --config teams/01-data-a/dedup/overlap_en.json
Config:          teams/01-data-a/dedup/overlap_en.json
Inputs:          Week-2 tokenizer sample v0 only: the 8 train and 4 heldout Parquet parts of en-dclm, en-fineweb-edu, en-nemotroncc and en-nemotroncc-synth (426,508 documents), under ./inputs/sample_v0/, checked against SHA256SUMS pinned by sha256 (table below)
Hardware:        CPU (single process; request 2 vCPU and 8 GiB RAM; no GPU)
Max time:        45 minutes
Precision:       not used
Measures:        documents per part, pack and split; pairs compared; pairs at Jaccard >= 0.50, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.0 and exact (same H1 key), per pack pair; H1 exact groups; Jaccard histogram of all pairs in 0.01 bins; wall time, peak RSS, input and output sha256
Expected result: as in the test log: 426,508 documents, 90,954,323,778 pairs; 9 H1 exact groups (21 documents, 16 exact pairs), all inside en-nemotroncc; 55 pairs at >= 0.80 and 135 at >= 0.70; 520 pairs stored at >= 0.50; the three CSV outputs byte-identical to the test log (sha256 below)
Outputs:         out/overlap_en/overlap_pairs.csv, overlap_by_pack.csv, overlap_histogram.csv, overlap_summary.json, overlap_matrix.npz, overlap_docs.parquet (7.7 MB in total)
Test log:        teams/01-data-a/jobs/logs/2026-11-04-overlap-en-local.txt (own machine, macOS arm64, Python 3.12.10; 845 s, peak RSS 3.4 GB)
```

## What the job does

`overlap.py` reads the 12 parts as one set and names each document `<pack_id>-<doc_id>`. It builds each document's H1
key (spec v1 `normalize.match_key`, then NFKC, casefold and whitespace collapsed to one space, as in
`dedup/dedup_design_v1.md`), splits the key into word 5-grams and computes the exact Jaccard similarity of every pair of
documents, with no sampling or MinHash estimate. Pairs at 1.0 are listed like any other pair, and `exact` marks pairs
whose keys are identical. It changes and removes nothing, and writes no document text: IDs, scores and counts only. It
needs no network and no keys, reads only `./inputs/sample_v0/` and writes only to `./out/overlap_en/`.

This is the cross-pack measurement of `dedup/dedup_design_v1.md` (experiment E2: measured, not applied). The full
description is in `teams/01-data-a/dedup/README_overlap.md`.

## Pinned inputs

The script hashes `inputs/sample_v0/SHA256SUMS` and stops unless it has sha256
`0b7da76396a7078b07a5e5f96a4ced88279e77205c164a35f284f387b0546faa` (the same pin as
`teams/03-tokenizer/train/rebuild_c3_s0.json`). It then checks each part against `SHA256SUMS` and stops on any missing
part or mismatch, before any work. A part not at `inputs/sample_v0/<split>/<pack>/<part>` is looked for by its sha256
anywhere under `inputs/sample_v0/`.

| Part under `./inputs/sample_v0/` | Documents | sha256 |
|---|---:|---|
| `train/en-dclm/part-00000.parquet` | 46,245 | `67b305d60aa0f4091612f6fefe0c7aee867872943017c5ebb598293c19dfeb88` |
| `train/en-dclm/part-00001.parquet` | 15,122 | `0dec2d4fc09db2950d6f619810b6d2abf6d854b5d44d402c646cce2b74bd96a6` |
| `heldout/en-dclm/part-00000.parquet` | 608 | `60d0741e754b70dffab4398ca617b37a408121b2f60fed95f8cf871996aacc36` |
| `train/en-fineweb-edu/part-00000.parquet` | 54,004 | `53cbbf7a77b84e46108836c889e6cb83e6fcdc048c316fbf699586a7fef1dbe2` |
| `train/en-fineweb-edu/part-00001.parquet` | 17,929 | `bdd5d5b4f7aa8ec00e17865b5ebe13344728569aa7ffff7f37ba942b6fe42229` |
| `heldout/en-fineweb-edu/part-00000.parquet` | 732 | `727ee3f5ee0ef235fdd5839e516130e3b3fbb4a95345bfc827175f69ecd2647a` |
| `train/en-nemotroncc/part-00000.parquet` | 68,777 | `19d641f52f5fc9c884da2fc4b4df1bc0327d73e327c12abb8efe0201c1668fda` |
| `train/en-nemotroncc/part-00001.parquet` | 23,043 | `afba6a19de409e5208b3eb690ed360ad90aebb5c4cfd7f2bd389b468d2066202` |
| `heldout/en-nemotroncc/part-00000.parquet` | 954 | `76653abac4785a2a7b14931142af29f64d3d621e8ea0c26c8d729a82b29f7845` |
| `train/en-nemotroncc-synth/part-00000.parquet` | 147,754 | `a601748f22e32bfb839bdb76e8e645f3beae510460857eb206fbdf3ce53a2427` |
| `train/en-nemotroncc-synth/part-00001.parquet` | 49,365 | `03a9efeb92e210dcb5b32d350cdee60fa032d21ea9454cefc913b0785f55ae9f` |
| `heldout/en-nemotroncc-synth/part-00000.parquet` | 1,975 | `3fcbb50614d90f680168e0c95479e364e995a6ebbbdfc56df90746b58c38aff8` |
| `SHA256SUMS` | | `0b7da76396a7078b07a5e5f96a4ced88279e77205c164a35f284f387b0546faa` |

Python packages: `numpy`, `scipy` and `pyarrow`. The test log used Python 3.12.10, numpy 2.4.3, scipy 1.18.1 and
pyarrow 23.0.1.

## Expected result in detail

From the test log. Pairs at Jaccard 0.80 and above, by pack pair:

| Pack pair | >= 0.80 | of which 1.0 | of which exact |
|---|---:|---:|---:|
| en-dclm x en-dclm | 14 | 0 | 0 |
| en-dclm x en-fineweb-edu | 4 | 0 | 0 |
| en-dclm x en-nemotroncc | 1 | 0 | 0 |
| en-dclm x en-nemotroncc-synth | 0 | 0 | 0 |
| en-fineweb-edu x en-fineweb-edu | 7 | 0 | 0 |
| en-fineweb-edu x en-nemotroncc | 5 | 0 | 0 |
| en-fineweb-edu x en-nemotroncc-synth | 1 | 0 | 0 |
| en-nemotroncc x en-nemotroncc | 22 | 16 | 16 |
| en-nemotroncc x en-nemotroncc-synth | 0 | 0 | 0 |
| en-nemotroncc-synth x en-nemotroncc-synth | 1 | 0 | 0 |
| **all** | **55** | **16** | **16** |

Pairs at or above each threshold, over all pairs: 0.70: 135, 0.75: 90, 0.80: 55, 0.85: 43, 0.90: 33, 0.95: 25.

The CSV outputs are deterministic, so the job's copies should have the same sha256 as the test log's:

| Output | Bytes | sha256 |
|---|---:|---|
| `overlap_pairs.csv` | 86,434 | `c01699ec08c86a6eabe9f475a38d379f1bac0907314f362a89baff8d21600c77` |
| `overlap_by_pack.csv` | 3,340 | `c359478f2c5d7175bcf21574d7fcac9dc214446c676dad74b2d70a1eda0f458e` |
| `overlap_histogram.csv` | 1,472 | `ed9294112f570726928a367366c9a6c1ae26c5a8852e174ba7324cc2d02843c6` |

`overlap_matrix.npz` and `overlap_docs.parquet` hold the same values, but their bytes can differ between runs, because
the zip archive records the time it was written and Parquet records the pyarrow version. `overlap_summary.json` differs
in wall time, peak RSS, versions and these two hashes.

## Time and memory

The test run took 845 s on an Apple-silicon laptop with peak RSS 3.4 GB. Reading and shingling the 426,508 documents,
a single Python process, took 551 s; scoring all pairs took 22 s. The 45-minute limit and 8 GiB of RAM leave about
three times the test time and about twice the test memory, for slower cloud CPUs.

## Tests

`teams/01-data-a/dedup/tests/test_overlap.py`, 22 tests on made-up documents (hand-checked pairs, a brute-force
Jaccard of every pair of 62 random documents, the input checks and the config checks), all passing:

```
python3 -B -m pytest teams/01-data-a/dedup/tests/test_overlap.py -q -p no:cacheprovider
```
