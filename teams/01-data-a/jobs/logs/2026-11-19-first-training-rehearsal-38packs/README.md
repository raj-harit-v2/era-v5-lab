# Rehearsal: first-training pipeline on all 38 packs (19 Nov 2026)

The same scripts as `jobs/2026-11-19-first-training.md`, run end to end on **all 86 raw parts of tokenizer sample v0
(38 packs)** with the frozen p1536 tokenizer, on Linux in the job's pinned environment (JOB_REQUEST.md rule 2), twice:
- **the first run** (`4dd2802`, 59/59 checks): no inventory, a rehearsal pack table and `dataset_version` (below);
- **the run with the inventory** (`2691c44`, 74/74 checks): `prepare_run.py`'s own `run.json`, F2 at 30 workers instead of 1 ([below](#the-run-with-the-inventory-prepare_runpys-config-at-2691c44)).

Both are rehearsals on sample v0, not the production run (see [Differences from the job](#differences-from-the-job)).

| | |
|---|---|
| Code | `g1-pipeline` `4dd2802` (git checkout, so every record names the commit) |
| Command | `python -I teams/01-data-a/pipeline/run_pipeline.py --config out/rehearsal/run_38pack.json` ([`config/run.json`](config/run.json)) |
| Inputs | all 86 raw parts of tokenizer sample v0 (48 train, 38 held-out; 1,444,766 documents). Every file's sha256 equals the tracked manifest `jobs/2026-11-02-tokenizer-sample-v0-clean/tokenizer_sample_v0_manifest.json` (`7fd647c8…`): 86 of 86 in [`inputs/input_manifest.json`](inputs/input_manifest.json), which `build_inventory.py` hashed from the files |
| Tokenizer | the frozen p1536 `tokenizer.json`, sha256 `e6b93a93…` (no `any_tokenizer`) |
| H3 | the job's own `jobs/2026-11-19-first-training/h3.json` (report-only, `max_docs_per_pack` 0: every row of the three packs was read). LaBSE `sentence-transformers/LaBSE`, downloaded from the Hub at revision `836121a0533e5664b21c7aacc5d22951f2b8b25b` (the download's own metadata): `model.safetensors` sha256 `77d8e1f2…`, as `h3_summary.json` records |
| Shards | the default 2^26 tokens per shard; `dataset_version` `rehearsal-p1536`; [`config/pack_table.json`](config/pack_table.json) (the repo table with placeholder lanes and licences) |
| F2 | `"pool": true`, `"workers": 30` |
| Hardware | a Runpod pod: 1 × A100 SXM 80 GB, 32 vCPU, 251 GB RAM, Ubuntu 24.04.3; Python 3.12.3 with exactly the 12 pins of the job's `requirements_pipeline.txt` ([`environment.txt`](environment.txt)) |

## Result

**All stages from clean to reconcile ran in one invocation: 59 checks, 0 failed** (`summaries/38pack/pipeline_manifest.json`),
exit code 0, 2 h 35 min (11:37 to 14:12 UTC).

| Stage | Result | Time |
|---|---|---|
| clean (spec v1.1, `clean_sha256` `6a57276c…`) | 86 parts, 0 errors; 1,444,766 raw → 1,410,230 cleaned | 1,433 s |
| overlap | 1,410,230 documents; 70 H1 exact groups (148 documents); qualifying pairs H1 97, H2 2,635 | 5,036 s (one core) |
| H3 (report-only) | 91,559 documents encoded (`en-fineweb-edu`, `ind-hi-fw2`, `ind-sa-fw2`), 12,310 candidates, 9,343 verified, **0 qualifying**; CUDA, fp16 | 244 s |
| dedup, apply | **1,083 groups**, 1,339 removed (H2 1,284, H1 55; 1,303 within pack, 36 cross pack), **0 held-out removed**; harm check `not_testable` (no gold IDs in sample v0) | 37 s |
| F2 (pool, 30 workers) | 1,533 dropped (train 1,517, held-out 16), 0 errors | 722 s |
| survivor loss | 1,083 groups: 1 lost (code-go, a survivor dropped by F2), 0 partly hit, 1,082 untouched; its groups equal dedup's summary, and the ledger's survivors dropped by F2 equal its own (in total and per pack) | 2 s |
| ledger | 1,444,766 rows: kept 1,407,358, clean 34,536, dedup 1,339, F2 1,533 | 97 s |
| shards | 48 train parts → **48 shards**, 1,385,709 documents, 1,132,509,915 tokens (largest shard 66,908,856), 0 truncated, verified on disk; 38 held-out parts not sharded | 1,725 s |
| reconcile | 1,407,358 kept = 1,385,709 in shards + 7,575 left out (secret 7,562, special 9, empty 4) + 14,074 held-out | 18 s |

**Against TSAI's dedup job on the same sample** (#547, on the #244 cleaning; `dedup/results_v1.md` section 1): 1,084 groups,
1,345 removed, survivors decided by rule 0: 28, rule 2: 21, rule 3: 750, rule 4: 285. Here, after the spec v1.1 cleaner:
1,083 groups, 1,339 removed, rule 0: 28, rule 2: 21, rule 3: 749, rule 4: 285. The per-pack counts are at the end of
[`logs/run-38pack/stderr.log`](logs/run-38pack/stderr.log).

**Files for a recount** ([`files/`](files/)): [`dedup_groups.csv`](files/dedup_groups.csv) (2,422 rows, every member of the 1,083 groups),
[`survivor_loss.csv`](files/survivor_loss.csv) (the 1 lost group: G000986, code-go `part-00001` row 6117, doc_id `d3295bf2adf32b51`,
dropped by F2 for G5's held-out `vault-go-test-000041/42`), and
[`ledger_code-go_train_groups_and_f2.csv`](files/ledger_code-go_train_groups_and_f2.csv) (the 101 code-go train ledger rows that are in
a dedup group or dropped by F2). The ledger itself is Parquet (pr-guard refuses data files) and 11 MB as CSV for code-go alone.

**Left out as secret:** the shard writer reuses pr-guard's patterns. In `cadj-commits`, 4,311 of 73,835 kept train documents (5.8%): 4,308 match the
email pattern and 3 the AWS-key pattern; the first address is in a `Signed-off-by:` line in 1,092, in an author, co-author or
reviewed-by style line in 1,304, and elsewhere in 1,912. `code-python` 39 (0.1%) and `en-dclm` 408 (0.7%) are also nearly all email.
(Counts only, from the shards' quality reports and `final/`.)

**The shards, checked afterwards:**
- `shards/verify_shards.py`: 0 problems ([`logs/verify_shards_38pack.txt`](logs/verify_shards_38pack.txt)).
- `audit/check_shard.py` of #60 (`585447e`) in folder mode with `--expect-tokenizer p1536 --expect-dataset-version rehearsal-p1536 --specials-from <tokenizer.json>`: 2,721 PASS, 0 FAIL, 1 NOT CHECKED ("run_shards verified the folder": `shards_summary.json` has `verified` null, because in a pipeline run the runner verifies the shards, not `run_shards.py`) ([`logs/check_shard_38pack.txt`](logs/check_shard_38pack.txt)).
- All 48 shard manifests record `created_by` `4dd2802…`, the tokenizer `e6b93a93…` and `dataset_version` `rehearsal-p1536`.

## The job's input tools on all 38 packs

Run on the same 86 raw parts ([`logs/build_inventory.log`](logs/build_inventory.log), [`logs/prepare_run.log`](logs/prepare_run.log)):

- `build_inventory.py --input-root <raw>`: 38 packs, 86 parts, 1,444,766 raw rows; `input_manifest_sha256` `575fdde2…` ([`inputs/`](inputs/)).
- `prepare_run.py` with the rehearsal's placeholder licences: **refused** ("pack table licence differs from approved inputs for code-go", exit 1, nothing written), as it should ([`logs/prepare_run_placeholder_refused.log`](logs/prepare_run_placeholder_refused.log)).
- `prepare_run.py` with [`config/pack_table_job_shaped.json`](config/pack_table_job_shaped.json) (the licence fields copied from `approved_inputs.json`, which has them for all 38 packs, and lanes from the domain with #47's six lane names): passed and wrote [`config/prepare_run_output_run.json`](config/prepare_run_output_run.json). That file was **not** run here (see below).
- `pipeline/inventory_check.py` (at `2691c44`) with that `expected_inventory.json`, on this run's folders afterwards:
  - `--ledger` and `--shards`: **8 checks, 0 failed**, 86 parts, 38 packs: the ledger accounts for every raw document, holds exactly the listed parts and packs, each raw file's sha256 and rows are the listed ones, and the shard summary holds exactly the listed parts, each in its listed status ([`logs/inventory_check_38pack.json`](logs/inventory_check_38pack.json)).
  - adding `--cleaned`: 9 checks, **1 failed, as expected**: "made from the input manifest the clean job read". This run's clean read the tracked sample manifest (`7fd647c8…`), not the input manifest `build_inventory.py` wrote (`575fdde2…`), so only a run started from `prepare_run.py`'s `run.json` can pass it ([`logs/inventory_check_38pack_with_cleaned.json`](logs/inventory_check_38pack_with_cleaned.json)).

## The run with the inventory: `prepare_run.py`'s config, at `2691c44`

The chain the job runs, end to end on the same 86 raw parts and the same pod: `build_inventory.py` → `prepare_run.py` →
`run_pipeline.py --config` on the `run.json` it wrote, at `g1-pipeline` `2691c44` (#61 and #663 merged). Files: [`inventory-run/`](inventory-run/).

- **Config:** [`inventory-run/config/run.json`](inventory-run/config/run.json) is [`config/prepare_run_output_run.json`](config/prepare_run_output_run.json) with **one change, F2 `"workers": 30` instead of 1**, so that it ends in time. Inventory on, the input manifest `575fdde2…`, `dataset_version` `first-training-v1`, the job-shaped pack table (approved licences, #47's six lanes), the job's `h3.json`.
- **Result: 74 checks, 0 failed, exit 0**, 2 h 34 min (14:31 to 17:05 UTC) ([`inventory-run/summaries/pipeline_manifest.json`](inventory-run/summaries/pipeline_manifest.json)). The runner ran the inventory checks itself: 6 on entry to the shard stage and 9 after reconcile, all passing, including "made from the input manifest the clean job read"; its report is [`inventory-run/summaries/inventory_check.json`](inventory-run/summaries/inventory_check.json).
- **The same counts as the first run** at every stage: 1,410,230 cleaned, 1,083 groups and 1,339 removed (0 held-out), H3 0 qualifying, 1,533 dropped by F2, 1 lost survivor, 1,407,358 kept = 1,385,709 in 48 shards + 7,575 left out + 14,074 held-out. Overlap's `overlap_matches.csv` has the same sha256 (`b2eabd2e…`), and **all 144 `.bin`, `.idx.npy` and `.docs.parquet` files are byte-identical** to the first run's. The 48 shard manifests differ in the pack-table and version fields (`capability_lane` in 36, `license`, `license_source`, `dataset_version`) and in what names the run (`created_by`, the commit; `cleaning_pipeline_sha256`; `quality_report_sha256`, whose report differs only in `upstream.run_id`) ([`inventory-run/logs/compare_shards_two_runs.txt`](inventory-run/logs/compare_shards_two_runs.txt)).
- **Checked afterwards:** `inventory_check.py --ledger --shards --cleaned`: 9 checks, 0 failed ([`inventory-run/logs/inventory_check_invrun_with_cleaned.json`](inventory-run/logs/inventory_check_invrun_with_cleaned.json)); `verify_shards.py`: 0 problems; `check_shard.py` of #60 (`d4173ed`) with `--expect-dataset-version first-training-v1`: 2,721 PASS, 0 FAIL, 1 NOT CHECKED (the same `verified` null as above).

## Shard drills (3-pack run on the same pod)

A first run on 5 raw parts (code-go ×3, `ind-bn-fw2`, `ind-bn-sangraha-v`; [`config/run_3pack.json`](config/run_3pack.json)),
the same environment and the real p1536, with `tokens` 2^20 so that parts roll over: **54 checks, 0 failed**, 22 min,
4 train parts → 90 shards (`summaries/3pack/`). Then [`logs/drills/drills.sh`](logs/drills/drills.sh), each drill in its own folder ([`logs/drills/drills.log`](logs/drills/drills.log)):

| Drill | What was done | Result |
|---|---|---|
| A. rollover | the run's 90 shards (the largest part 55 shards) | `check_shard.py` (#60): 4,531 PASS, 0 FAIL; `verify_shards.py`: 0 problems |
| B. interrupted shard stage | `run_shards.py` killed with `kill -9` after 3 `.bin` files, then run again | the rerun exited 0; all 270 shard files byte-identical to the uninterrupted run; no `.partial`, `.tmp` or `.lock` left |
| C. damaged shards | C1 one byte flipped in a `.bin`; C2 8 bytes cut off an `.idx.npy`; C3 a `.docs.parquet` deleted | `verify_shards.py` caught all three (exit 1). `check_shard.py` (#60) caught C1; on C2 it stopped with a numpy `ValueError`; on C3 it reported NOT CHECKED and exited 0 (noted on #60) |
| D. every document left out | `run_shards.py --pack ind-bn-sangraha-v --tokens 16` | status `all_left_out`, 0 shards; 10,111 oversize + 4 secret = all 10,115 rows |

**Drill B and #61:** the first part in that folder is a held-out part, which is saved at once, so this drill did not
reach the case #61 fixes (a run killed in its very first part, with no summary saved yet). The `empty` status was not
drilled: no part of sample v0 is emptied by dedup or F2; `shards/tests/test_run_shards.py` covers it.

## Memory, disk and throughput

Sampled every 15 s ([`resources.csv`](resources.csv): RSS of the run's Python processes, GPU memory, the run folder's
size), so a short peak between two samples is missed; where a stage reports its own peak, that figure is given too.

| Stage | Peak RSS | Notes |
|---|---|---|
| clean | 0.4 GB | one process (`peak_rss_mib` 385 in its summary) |
| **overlap** | **14.0 GB** | one process at about 100% of one core. Its last phase (H1/H2 rules and the code-token check over 467,786 code documents) was already running at 12:28 (seen on the live log) and ended at 13:25 UTC: at least 57 of its 84 min; the code-document count is from `overlap_summary.json` |
| H3 | 3.0 GB | `peak_rss_mb` 2,972 in `h3_summary.json` (2.3 GB sampled); GPU memory 3.1 GB; loading the model took 104 s of H3's 206 s |
| F2 | 1.3 GB per worker | 30 workers. The sum of their RSS (31 GB) counts pages they share in each; the pipeline README says they share G9's set on Linux |
| **shards** | **18.8 GB** | one `run_shards.py` process |

- **Disk:** the run folder reached 10.4 GB with `"intermediates": "keep"`.
- **F2 with one worker:** the per-part `seconds` in the `.f2.json` reports ([`f2_part_seconds.csv`](f2_part_seconds.csv)) add up to 10,802 s (train) + 360 s (held-out), about **3.1 h**, against 722 s for the stage with 30 workers; the slowest part alone took 677 s. The per-part times were measured with 30 workers running at once, so one worker alone may be somewhat faster. `prepare_run.py` writes `"workers": 1`.
- **H3's precision:** `auto` gave fp16 on the A100; the job request says bf16 on supported CUDA.

## Differences from the job

- **No `inventory` in the first run:** it read the tracked sample manifest (all 86 parts), not `prepare_run.py`'s `run.json`. The second run (above) is that `run.json`, with F2 at 30 workers instead of 1.
- **Pack table and `dataset_version`:** placeholder lanes and licences (`lane` `rehearsal` where the repo table is null) and `rehearsal-p1536`; the job uses the approved pack table and `first-training-v1`.
- **Inputs:** sample v0, not the TSAI-staged production parts.
- **Hardware:** a rented GPU pod, not TSAI's machine; times will differ.

## Not covered

- The production pack table and the TSAI-staged inputs.
- F2 with one worker, as `prepare_run.py` writes it (both runs used 30).
- `shards/pack_table.json` after #63 (merged after these runs); its lanes are the ones the job-shaped table used.
- H3 removal (`h3.remove`), which stays off for this job (TSAI on #625).
- The `empty` part status (no such part in sample v0) and #61's first-part restart case.
