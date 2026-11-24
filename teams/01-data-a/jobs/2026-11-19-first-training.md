# First training pipeline: inventory through reconciled train shards

```text
Team:            01-data-a
Owner:           patilvijay23
Lead approval:   patilvijay23
Question:        Do the approved raw parts produce an exact inventory, auditable cleaned Parquets, and reconciled p1536 train shards in one pipeline run?
Script:          teams/01-data-a/jobs/2026-11-19-first-training/build_inventory.py, prepare_run.py, then teams/01-data-a/pipeline/run_pipeline.py (clean only), teams/01-data-a/dedup/minhash_sizing.py (sizing gate), run_pipeline.py (production run)
Command:         gated, in order (see "Staged-data sizing gate"): run_pipeline.py --config out/first-training-inputs/run_clean.json; minhash_sizing.py --inputs out/pipeline/first-training-v1-clean/clean --factors 1 2 4 --out out/minhash_sizing/corpus-v1; if the gate passes, run_pipeline.py --config out/first-training-inputs/run_production.json
Config:          out/first-training-inputs/run_clean.json and run_production.json (prepare_run.py writes both beside run.json, derived from it)
Inputs:          TSAI-staged approved train and heldout parts for the 33 packs in staged_packs_33.json (subset of approved_inputs.json); frozen p1536 tokenizer; offline LaBSE model; approved pack table; G9 F2 v2 fingerprints
Hardware:        1 CUDA GPU (16 GiB VRAM or more), 32 vCPU, 64 GiB RAM, sized on the sample (size RAM and time from the staged rows; see sizing below); F2 uses 30 workers
Max time:        720 minutes for the combined job (H3's own limit is 180 minutes)
Precision:       H3 fp16 on CUDA (precision auto); shard token IDs are integers
Measures:        Raw/cleaned/dedup/F2/final counts, H3 matches, train shards and tokens, heldout not_sharded, per-part reconciliation and SHA-256 checks
Expected result: Every listed raw part reaches the ledger; each train part is written or has a justified empty/all_left_out status; heldout parts are not sharded; all checks pass; H3 removes zero documents
Outputs:         out/first-training-inputs/{input_manifest.json,expected_inventory.json,pack_metadata.json,run.json,run_clean.json,run_production.json}; out/pipeline/<run_id>-clean/clean/ (the clean run); out/minhash_sizing/corpus-v1/ (sizing.csv, sizing.json, x1/x2/x4); out/pipeline/<run_id>/{overlap,h3,dedup,deduped,final,report,ledger,shards,reconcile}/ and pipeline_manifest.json
Test log:        teams/01-data-a/jobs/logs/2026-11-19-first-training-rehearsal-38packs/ (all 86 parts of sample v0, 38 packs, frozen p1536, Linux + pinned env: 59/59 checks; with the inventory, prepare_run's run.json at 2691c44: 74/74)
```

## Current cleaner validation: full rerun after merged #88

The rebuilt cleaner is byte-identical to merged #88, SHA-256
`d275556ee87a259b05ac5e474ed40b569c2e821aaaffa99d5d07035e40948989`; both active cleaner job configs already pin these bytes.
Fresh harm across all original packs and both teams' gold folders covers
4,768 gold documents: **28 of 32 supported packs PASS, four raw FAIL** on the
same 11 affected IDs. `cadj-commits` is now supported, with zero of 413 gold
documents changed or dropped. `ind-ta-fw2` is the sole testable passthrough pack;
five packs still lack gold. No execution or Indic Unicode-audit errors.

The commits pack has 40 email-only changes across 500 documents, zero drops and
no second-pass changes; notebooks and Stack Exchange remain unchanged.
Cleaner tests: **1,952 PASS and nine subtests**. Clean-job/preparation tests:
**125 PASS**. No gold exclusions or release waiver were applied; the legacy
registry inventory is still absent, so the existing Data A/B harm APIs were used.
See [the replaced current harm report](../spec_v1_1/results/cleaner/harm_tests.md).
Historical rehearsal timings and comparisons remain historical; staged-data
sizing, integration evidence and the final release commit pin are still needed.

## Update of 23 Nov 2026: staged 33-pack run and MinHash

TSAI confirmed the exact selection in G1 at **24 Nov 2026, 08:23:26 IST**.
The committed [`staged_packs_33.json`](2026-11-19-first-training/staged_packs_33.json) contains that list.
The five blocked packs are **en-dclm, en-nemotroncc, en-nemotroncc-synth,
math-finemath and ind-hi-hplt**; exclude their files from this run's raw root.
This selects a subset of the approved 38-source universe, without changing
`approved_inputs.json` or its policy hash. Local audit-pack availability does
not change the confirmed production selection. To prepare all 38 for a separate
rehearsal, omit `--packs-file`.

For the partial run, add `--packs-file teams/01-data-a/jobs/2026-11-19-first-training/staged_packs_33.json` to the inventory
command below. Supply an explicit JSON array of the 33 approved pack IDs
confirmed by TSAI as staged, as recorded in the committed selection file. Stage only those packs under the input root. Each still
requires train and heldout parts. The frozen manifest records the selected
packs and the five deferred source-resolution blockers, preserving the full
approved-source policy and hash. The inventory and generated pack table cover
exactly that selection. Without this option all 38 packs remain required.

The generated job now explicitly selects `minhash_overlap.py`: the partial
MinHash config for the 33-pack selection, the full MinHash config otherwise.
The exact-overlap timings and sizing discussion below describe the historical
rehearsal, not the new production algorithm. Before execution, attach 1x/2x/4x
staged-data MinHash sizing and validate the final worker budget and integration
run. This update does not claim that those measurements have been completed.
See `2026-11-19-first-training/README.md` for selection details.

### Scoped cleaner preservation amendments (23 Nov 2026)

The active cleaner includes five subsets extracted from fork #86: A6 test-fixture/
Cyrillic protection, scientific C2 paragraph boundaries, English C2 fenced-code
protection, C3 closing curly quotes, and English F1 DOI protection. The existing
binary-value guard, rule IDs/scopes/order and report-only H3 policy are retained.
The post-#88 full-gold rerun gives 28/32 supported packs PASS and four raw FAIL,
with the same affected IDs; the five amended rules touch zero gold documents.
Cleaner tests: 1,952 PASS and nine subtests; clean-job/preparation: 125 PASS.
See `../spec_v1_1/results/cleaner/harm_tests.md` for replaced evidence and limits.
The tokenizer-sample job config now pins this cleaner too; historical rehearsal
timings and hashes below remain historical and are not evidence for this build.

### MinHash overlap sizing (measured at 1x on the sample)

From the stage's own runs (`jobs/logs/2026-11-23-minhash-overlap-sample/`, #744 and #758), on the sample's 47 train
parts (1,395,320 documents) on 2 cores: 39.6 min, of which 38.7 min is the per-part signature step (about 16 ms per
code document, mostly Pygments) and 46 s the rest; peak RSS 2.0 GB in the main process and 1.5 GB in the largest
worker; `work/` 3.7 GB on disk; files returned to the repository 0.49 MB. Same duplicate groups as TSAI's 5 Nov exact
run, and a byte-identical `dedup.py` remove list.

Both MinHash configs set `workers` to 16, so the workers stay under about 24 GB. Estimates from the 1x run, not
measured at scale (the signature step divides by the workers; the rest is about linear in documents):

| Rows vs sample | Overlap time, 16 workers | Main process RSS | Workers' RSS (16) | `work/` on disk |
|---|---:|---:|---:|---:|
| 1x | about 6 min | about 2 GB | up to about 24 GB | about 3.7 GB |
| 2x | about 12 min | about 4 GB | up to about 24 GB | about 7.5 GB |
| 4x | about 25 min | about 8 GB | up to about 24 GB | about 15 GB |

`dedup/minhash_sizing.py --inputs <staged cleaned folder> --factors 1 2 4` measures these on the staged data, each
run from scratch in a new folder, and writes `sizing.csv` and `sizing.json` there; the gate below says when to go on.
`jobs/2026-11-19-first-training/check_overlap_stage.py` checks the generated overlap stage and runs the tests.

### Staged-data sizing gate, before overlap

TSAI's bar (23 Nov) asks for time and RAM measured at 1x, 2x and 4x on the staged data before the production run. The
job measures them on its own cleaned parts, so the staged data is cleaned once. A run with an inventory must end at
reconcile, so the clean pass is its own run, and the production run adopts its folder (the pattern of
`pipeline/local_trial/configs/2-stop-at-clean.json` and `4-adopt-clean.json`):

1. **Prepare** `out/first-training-inputs/run.json` with `build_inventory.py` (with `--packs-file` for the 33 staged
   packs) and `prepare_run.py`, as in "Run from the repository root" below.
2. **Clean only** with `run_clean.json`, which `prepare_run.py` writes beside `run.json`: the same stages, `"run_id"`
   `"first-training-v1-clean"`, `"to": "clean"` and no `"inventory"` (a run with an inventory must end at reconcile):
   `python -I teams/01-data-a/pipeline/run_pipeline.py --config out/first-training-inputs/run_clean.json`.
   The cleaned parts are in `out/pipeline/first-training-v1-clean/clean/`.
3. **Size** on those parts, with the 16 workers of the MinHash config:
   `python -I teams/01-data-a/dedup/minhash_sizing.py --inputs out/pipeline/first-training-v1-clean/clean --factors 1 2 4 --out out/minhash_sizing/corpus-v1`.
   It takes about 45 minutes and about 26 GB of scratch disk for the three `work/` folders (1x + 2x + 4x).
4. **Gate.** Go on only if all of these hold, and otherwise stop and return `out/minhash_sizing/corpus-v1/`:
   - the sizing command exited 0 (every factor complete, no reused parts);
   - in `sizing.json`, every factor in `results` has `status` `complete` and a measured `peak_rss_total_gb` (main
     process plus all workers together), and the largest of them, `max(peak_rss_total_gb)` over all factors, is at
     most 48 GB. A smaller factor can peak higher than a larger one, so every row counts, not only the largest
     factor. If the 4x row is `undersized`, fewer than 4x the sample is staged; its `actual_factor` is what was
     measured;
   - the whole job fits the 720 minutes of Max time:
     `elapsed job time + projected production overlap + remaining stages + margin <= 720 minutes`.
     Elapsed job time is measured from the start of the job, so it includes the clean run and the sizing (about 45
     minutes). Projected production overlap is `projection_whole_staged_inputs.hours_linear` × 60 (overlap on every
     staged document). Remaining stages are H3, dedup, apply, F2, survivor loss, raw ledger, shards and reconcile.
     Record the figures used for each term, and the margin, in the returned log.
5. **Production run** with `run_production.json`, also written by `prepare_run.py`: `run.json` with its inventory and
   `stages.clean` set to `{"mode": "adopt", "output": "out/pipeline/first-training-v1-clean/clean"}`. Check it with
   `--plan`, then run it (step 3 of "Run from the repository root"). Before anything runs, the runner checks that the
   adopted clean job's `job_summary.json` read the inventory's input manifest, and it then checks the adopted
   folder's parts and rows as after its own clean stage; nothing is cleaned again.
6. **Return** `sizing.csv`, `sizing.json`, and each factor's `config.json` and `overlap/overlap_summary.json` under
   `teams/01-data-a/jobs/results/2026-11-19-first-training/minhash_sizing/` (IDs and counts only).

## Update of 22 Nov 2026 for corpus-v1

This revises the request of #599 now that TSAI has confirmed the input manifest. Nothing else in the pipeline changes.

- **Dataset version:** `prepare_run.py` generated `dataset_version` `first-training-v1`; it now generates `corpus-v1`. The `run_id` argument is unchanged and is only the output folder name.
- **Pinned code:** `main` at `421f8497ddb1585666e8f5a274c524e4462402cc` (merge of #716), plus this update, which touches only `prepare_run.py` (the constant), its test, and these docs. Run from `main` once this update is merged.
- **Pinned cleaner:** `teams/01-data-a/spec_v1_1/clean.py`, SHA-256 `d275556ee87a259b05ac5e474ed40b569c2e821aaaffa99d5d07035e40948989`, which equals `clean_sha256` in `teams/01-data-a/pipeline/clean.json`; the clean stage refuses any other file.
- **Pinned scope:** `approved_inputs.json`, SHA-256 `10f313750235902d401cfb1023555b37e575fc8a11a5adccceeab84af7515f5f` (the confirmed version). The input manifest records this hash and `prepare_run.py` refuses a manifest built from any other version.
- **Checks:** `pytest` of the command under "Scope and prerequisites" passes (146 tests) on this branch.

## Scope and prerequisites

This is an integration request. TSAI stages the approved raw inputs and applies the approved spec v1.1 cleaning rules as part of the agreed pipeline execution. Confirm that this combined run is acceptable under `JOB_REQUEST.md` rule 6, which reserves full-data cleaning for TSAI. TSAI confirmed the source scope on 22 Nov 2026 (`2026-11-19-first-training/approved_inputs.json`, merged in #716): the 38 sample-v0 pack IDs are the final admissible source set for corpus-v1, with no further packs without a separate ruling; production may have more parts per pack, with the same split/pack layout. Verify the fetched source revisions and subset restrictions against TSAI's source catalog before starting.

The job must be staged with these inputs before `--plan` or execution:

- All selected approved raw parts, at least one in each split for every selected pack, under `<raw>/train/<pack>/part-<number>.parquet` and `<raw>/heldout/<pack>/part-<number>.parquet`.
- The frozen p1536 `tokenizer.json` (SHA-256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`).
- The published `sentence-transformers/LaBSE` revision `836121a0533e5664b21c7aacc5d22951f2b8b25b`, staged offline at `../models/LaBSE` relative to the repository root; see the pinned files below. The job uses a CUDA host; H3 retains the rehearsed `device: auto` setting and measures `ind-sa-fw2`, `ind-hi-fw2` and `en-fineweb-edu` in report-only mode. All sentence thresholds remain at the rehearsed default 0.7. E5c's provisional Sanskrit 0.55 is a separate measurement configuration; threshold changes are deferred beyond this submission.
- The committed `2026-11-19-first-training/approved_inputs.json`: all 38 packs, TSAI-accepted shard metadata/lanes, and pinned licence text/provenance. The generator materializes these fields as `out/first-training-inputs/pack_metadata.json` for the sharder. The generic `shards/pack_table.json` has the accepted lanes but omits licences.
- The pinned G9 F2 v2 fingerprint set and the packages in `2026-11-19-first-training/requirements_pipeline.txt` in one Python 3.12 environment. No network access or keys at runtime.

## Model staging and resource limits

Run this setup wrapper from the repository root before inventory/config preparation. If the required local model files are missing, it downloads the exact published snapshot. It also downloads the seven tree-sitter grammars the cleaner's F1 uses to find comments and strings in code: tree-sitter-language-pack 1.22.1 does not ship them and fetches each one on first use, which the job cannot do without network. Setup needs network access only for these downloads; the `hf` CLI is supplied by `huggingface_hub` in the environment. TSAI may pre-stage the same snapshot to skip the download. A complete folder with incorrect weights is rejected by the hash checks; it is not silently accepted.

```bash
set -euo pipefail
for labse_file in modules.json config.json model.safetensors 1_Pooling/config.json 2_Dense/config.json 2_Dense/model.safetensors tokenizer.json tokenizer_config.json special_tokens_map.json vocab.txt; do
  if [ ! -f "../models/LaBSE/$labse_file" ]; then
    hf download sentence-transformers/LaBSE --revision 836121a0533e5664b21c7aacc5d22951f2b8b25b --local-dir ../models/LaBSE --exclude "*.bin" "*.msgpack" "*.h5" "onnx/*"
    break
  fi
done
(
  cd ../models/LaBSE
  sha256sum --check <<'LABSE_HASHES'
77d8e1f2dbab6eb5d3c261ce9d3dbf1e3c69e02938c95f934f94f42c22dfa31f  model.safetensors
f866c945fa2147ce4940c8ead0b4b20af4217e0f4664bd35f41c2a0967c4fe77  2_Dense/model.safetensors
b6bd83d561db8d2ccb7f44dafcd945e39bea16dc2819072ffb10adb45608b029  config.json
LABSE_HASHES
)
python -I -c "import tree_sitter_language_pack as t; langs = ['cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript']; t.download(langs); missing = set(langs) - set(t.downloaded_languages()); assert not missing, f'tree-sitter grammars missing: {sorted(missing)}'"
python -I -c "import torch; assert torch.cuda.is_available(), 'CUDA GPU required for this job'; print(torch.cuda.get_device_name(0))"
```

`prepare_run.py` refuses to publish `run.json` unless the seven F1 grammars are in tree-sitter-language-pack's cache, and checks these files:

| File under `../models/LaBSE/` | Bytes | SHA256 |
|---|---:|---|
| `model.safetensors` | 1,883,734,344 | `77d8e1f2dbab6eb5d3c261ce9d3dbf1e3c69e02938c95f934f94f42c22dfa31f` |
| `2_Dense/model.safetensors` | 2,362,528 | `f866c945fa2147ce4940c8ead0b4b20af4217e0f4664bd35f41c2a0967c4fe77` |
| `config.json` | 804 | `b6bd83d561db8d2ccb7f44dafcd945e39bea16dc2819072ffb10adb45608b029` |

Keep the snapshot's module and tokenizer files too. After setup, the processing pipeline performs no downloads. The returned H3 summary records the weight and config hashes.

The sample rehearsal used 30 F2 workers on 32 vCPU. Peak RSS was 14.0 GB for overlap, 18.8 GB for sharding, and about 1.3 GB per F2 worker; the output folder reached 10.4 GB with intermediates kept. The requested 64 GiB RAM provides headroom for that sample workload. Production inputs may be larger: confirm input size and provision disk/RAM before starting; the sample does not establish a production-scale upper bound. Allocate space for the raw inputs, model, all intermediate Parquets and shards. Set `--f2-workers` to fit the allocated cores and memory (30 for the hardware above). The generator defaults to 1 if omitted; the rehearsal's per-part F2 times sum to about 3.1 h at one worker, compared with 12 min for the 30-worker stage.

**Size RAM and time from the staged row count before starting.** After `build_inventory.py`, read the total `raw_rows` that it prints (also `total_docs` in `input_manifest.json`; sample v0: 1,444,766 raw rows, 1,410,230 cleaned, about 97.6%). Overlap runs on one core and holds all cleaned documents in memory; on the sample it peaked at 14.0 GB and took 84 min.

Overlap does not scale linearly with documents. It compares every pair of documents: a word 5-gram pass over all N(N-1)/2 pairs (about 9.9 x 10^11 on the sample, done as a sparse product that costs one step per pair of documents sharing a 5-gram, 14.9 billion steps), and a separate code-token pass over the code documents (467,786 on the sample). On the sample, reading and shingling took about 13 min, the word pass about 3 min, and the rest, about 68 min, the shingle index, the H1/H2 rules and the code-token pass. The work of a sparse product grows with the number of document pairs that share a shingle, so doubling the documents can more than double it, for example when boilerplate is shared by more documents. One run at 1x cannot show how much more. The figures below are therefore linear extrapolations and a lower bound for the time, not an estimate:

| Rows vs sample | Overlap peak RSS (linear) | Overlap time (at least) | Whole run (at least; sample: 2 h 35 min) |
|---|---:|---:|---:|
| 1x (1.41 M) | 14.0 GB | 84 min | 2 h 35 min |
| 2x | about 28 GB | 3 h or more | 5 h or more |
| 5x | about 70 GB | 7 h or more | 13 h or more |

The 64 GiB and 720 minutes requested were sized on the 1x run. Neither is shown to cover more than that. For staged rows above the sample, provision RAM and time with margin over the linear figures, and agree the plan with the team before starting. **If the estimate exceeds the allocated RAM or time, do not start the run.** Provision a larger host, or return the request to the team to raise Max time. Peak memory and per-stage runtime are required in the returned log, so the real scaling can be checked afterwards.

Overlap also stops when its outputs exceed `max_output_mb`, which the script limits to 50. The sample's outputs were 43.6 MiB, 32.7 MiB of them `overlap_docs.parquet` (one row per document). If the outputs grow with the documents, they reach 50 MiB at about 1.15x the sample, and the job fails when it has written them, at the end of overlap.

**If a stage fails, the run continues; it does not start over.** The runner records each stage in `pipeline_manifest.json` when it finishes. Set `"from": "<stage>"` in the run config (for example `"from": "overlap"`) and run the same command: the runner checks that every earlier stage's output still has its recorded digest and continues at that stage, so a failed overlap does not repeat cleaning. An interrupted clean job also continues its own folder. A single stage has no checkpoint inside it, so a failed overlap reruns from its beginning (84 min on the sample).

The committed 74-check run is the primary end-to-end execution evidence for this request. The submission retains its H3 settings (including sentence threshold 0.7), report-only H3 policy, cleaner rules, overlap/dedup/F2 logic, p1536 tokenizer and 30 F2 workers. The one deliberate change is the shard `dataset_version`, now `corpus-v1` (the rehearsal wrote `first-training-v1`). Final changes add input/model preflight checks, generate the same shard metadata from the approved scope, and improve the independent auditor. Cleaner audit sampling adds reports without changing the cleaned data. Focused equivalence and regression tests supplement the rehearsal; recorded run IDs, hashes and counts continue to describe that original run. Generated inventory and provenance hashes for the submission will differ because metadata and audit reports have been added.

Final local verification on 19 Nov: the audit, job-preparation and cleaner suites passed 140 tests. These include exact equality of the submitted H3 config and generated pack metadata with the rehearsal, and byte-identical cleaned Parquets with audit sampling enabled/disabled on a synthetic fixture. The setup wrapper passed `bash -n`; the conditional network download was not executed during this verification.

```bash
python -m pytest teams/01-data-a/tests/audit/test_check_shard.py teams/01-data-a/jobs/2026-11-19-first-training/tests teams/01-data-a/pipeline/tests/test_clean_job.py -q
```

## Run from the repository root

1. Stage and verify the entire selected raw file set. Generate the manifest and expected inventory **before** cleaning. Use a new output folder:

   ```bash
   python -I teams/01-data-a/jobs/2026-11-19-first-training/build_inventory.py --input-root <raw-root> --out out/first-training-inputs --packs-file teams/01-data-a/jobs/2026-11-19-first-training/staged_packs_33.json
   ```

2. Generate `out/first-training-inputs/run.json` from the frozen inventory. The command checks the p1536 tokenizer SHA256, model pins, exact pack set and shard metadata, then generates the sharder table and run config from the same approved scope used by the inventory. It pins `dataset_version` to `corpus-v1` (independent of `--run-id`) and keeps cleaned, deduped and F2 Parquets for audit.

   ```bash
   python -I teams/01-data-a/jobs/2026-11-19-first-training/prepare_run.py --bundle out/first-training-inputs --input-root <raw-root> --tokenizer <p1536-tokenizer.json> --f2-workers 30 --run-id first-training-v1
   ```

   The generated file has this structure; its input counts and SHA256 come from the inventory rather than manual transcription:

   ```json
   {
     "run_id": "first-training-v1",
     "out": "out/pipeline",
     "inventory": "out/first-training-inputs/expected_inventory.json",
     "intermediates": "keep",
     "stages": {
       "clean": {
         "mode": "run",
         "settings": "teams/01-data-a/pipeline/clean.json",
         "input": "<raw-root>",
         "manifest": "out/first-training-inputs/input_manifest.json",
         "manifest_sha256": "<generated input_manifest_sha256>",
         "expected_parts": {"train": "<generated count>", "heldout": "<generated count>"}
       },
       "overlap": {"mode": "run", "script": "teams/01-data-a/dedup/minhash_overlap.py", "settings": "teams/01-data-a/dedup/minhash_overlap_partial.json"},
       "h3": {"mode": "run", "settings": "teams/01-data-a/jobs/2026-11-19-first-training/h3.json"},
       "dedup": {"mode": "run", "settings": "teams/01-data-a/dedup/dedup.json"},
       "f2": {"pool": true, "workers": 30},
       "ledger": {"raw": "<raw-root>"},
       "shards": {
         "tokenizer": "<p1536-tokenizer.json>",
         "dataset_version": "corpus-v1",
         "pack_table": "out/first-training-inputs/pack_metadata.json"
       },
       "reconcile": {}
     }
   }
   ```

   The builder requires all selected packs in both splits and rejects unknown packs, invalid part names, missing columns, changed files and duplicate numeric part indices. The generator refuses an incomplete pack table or an unfrozen tokenizer.

3. Run the staged-data sizing gate (above): the clean run, the sizing and the gate, then check and run the production
   config. All commands use the same checkout and working directory:

   ```bash
   python -I teams/01-data-a/pipeline/run_pipeline.py --config out/first-training-inputs/run_clean.json
   python -I teams/01-data-a/dedup/minhash_sizing.py --inputs out/pipeline/first-training-v1-clean/clean --factors 1 2 4 --out out/minhash_sizing/corpus-v1
   # go on only if the gate passes (sizing exit 0; every factor complete with max(peak_rss_total_gb) <= 48 GB;
   # elapsed job time + projected production overlap + remaining stages + margin <= 720 minutes)
   python -I teams/01-data-a/pipeline/run_pipeline.py --config out/first-training-inputs/run_production.json --plan
   python -I teams/01-data-a/pipeline/run_pipeline.py --config out/first-training-inputs/run_production.json
   ```

   `run.json` is the same run in one go, without the gate; the job uses the two gate configs.

The runner runs clean → overlap → H3 → dedup → apply → F2 → survivor loss → raw ledger → shards → reconcile. It verifies each handoff and the inventory at the ledger/shard and reconciliation checkpoints. H3 feeds its matches to dedup with `remove: false`. H3 stays report-only: the runner hardcodes `remove: false` for this hand-off, fails the run if dedup recorded anything else, and acceptance requires H3 `removed: 0`.

## Folder layout and audit artifacts

For `run_id = first-training-v1`, the raw layout is preserved through cleaning, dedup application and F2:

```text
<raw-root>/
  train/<pack>/part-00000.parquet
  heldout/<pack>/part-00000.parquet

out/first-training-inputs/
  input_manifest.json
  expected_inventory.json
  pack_metadata.json
  run.json

out/pipeline/first-training-v1/
  clean/
    train/<pack>/part-00000.parquet
    heldout/<pack>/part-00000.parquet
    reports/train/<pack>/part-00000.parquet.json
    reports/heldout/<pack>/part-00000.parquet.json
    job_summary.json
    cleaned_manifest.json
    audit/train/<pack>/part-00000.parquet.json
    audit/heldout/<pack>/part-00000.parquet.json
    rule_counts.csv
    rule_examples.csv
  overlap/
  h3/
  dedup/
  deduped/train/<pack>/part-00000.parquet
  deduped/heldout/<pack>/part-00000.parquet
  final/train/<pack>/part-00000.parquet
  final/heldout/<pack>/part-00000.parquet
  report/
  ledger/
  shards/
    <pack>-train-000000.bin
    <pack>-train-000000.idx.npy
    <pack>-train-000000.docs.parquet
    <pack>-train-000000.json
    <pack>-train-000000.quality_report.json
    <pack>-train-000000.dump.md
    shards_summary.json
  reconcile/
  pipeline_manifest.json
  inventory_check.json
```

Shard files are **flat under `shards/`**, not nested by split or pack. Numbering runs across a pack's train parts and may roll over to several shards for one part. Heldout parts remain as Parquet in `clean/`, `deduped/` and `final/`; `shards_summary.json` records them as `not_sharded`. A train part with no tokens can be `empty` or `all_left_out`; the inventory permits these explicit statuses and reconciliation checks their document accounting. `intermediates: keep` retains the clean output in all cases.

The clean settings enable `audit_samples: 5`. Each part has an audit sidecar; `rule_examples.csv` combines up to five fixed/dropped document IDs per pack/rule, with action and character counts. Rules that never fired have an empty example row. Auditors use the saved raw/cleaned Parquets to inspect those IDs. No document text is placed in these audit reports.

## Return and acceptance

Return the console log, `pipeline_manifest.json`, `inventory_check.json`, clean `job_summary.json`, `cleaned_manifest.json`, `rule_counts.csv` and `rule_examples.csv`, H3 summary and match counts, `shards_summary.json`, and `reconcile_summary.json` under `teams/01-data-a/jobs/results/2026-11-19-first-training/`. Limit repository-returned logs/reports to 50 MiB total. Keep audit sidecars, Parquet, token binaries and document text in TSAI's job storage; report their paths and hashes without committing their content. With them, return the sizing gate's `out/minhash_sizing/corpus-v1/sizing.csv` and `sizing.json`, and each factor's `config.json` and `overlap/overlap_summary.json`, under `teams/01-data-a/jobs/results/2026-11-19-first-training/minhash_sizing/`, also when the gate stops the job; the clean run's `pipeline_manifest.json` and `logs/clean.log` go with the clean `job_summary.json`.

Acceptance requires exit code 0, inventory report `ok: true`, no missing or unlisted input part, zero heldout shards, H3 `removed: 0`, shard files verified on disk, and reconciliation of every kept train document. Include the runtime, peak memory, H3 model hash and package versions, shard/token counts, and any empty or all-left-out train parts in the returned log.
