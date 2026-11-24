# First training pipeline: inventory through reconciled train shards

```text
Team:            01-data-a
Owner:           patilvijay23
Lead approval:   patilvijay23
Question:        Do the approved raw parts produce an exact inventory, auditable cleaned Parquets, and reconciled p1536 train shards in one pipeline run?
Script:          teams/01-data-a/jobs/2026-11-19-first-training/build_inventory.py, prepare_run.py, then teams/01-data-a/pipeline/run_pipeline.py
Command:         python -I teams/01-data-a/pipeline/run_pipeline.py --config out/first-training-inputs/run.json
Config:          out/first-training-inputs/run.json (materialized from the template below after inventory build)
Inputs:          TSAI-staged approved train and heldout parts for the 38 packs in approved_inputs.json; frozen p1536 tokenizer; offline LaBSE model; approved pack table; G9 F2 v2 fingerprints
Hardware:        1 CUDA GPU (16 GiB VRAM or more), 32 vCPU, 64 GiB RAM, sized on the sample (size RAM and time from the staged rows; see sizing below); F2 uses 30 workers
Max time:        720 minutes for the combined job (H3's own limit is 180 minutes)
Precision:       H3 fp16 on CUDA (precision auto); shard token IDs are integers
Measures:        Raw/cleaned/dedup/F2/final counts, H3 matches, train shards and tokens, heldout not_sharded, per-part reconciliation and SHA-256 checks
Expected result: Every listed raw part reaches the ledger; each train part is written or has a justified empty/all_left_out status; heldout parts are not sharded; all checks pass; H3 removes zero documents
Outputs:         out/first-training-inputs/{input_manifest.json,expected_inventory.json,pack_metadata.json,run.json}; out/pipeline/<run_id>/{clean,overlap,h3,dedup,deduped,final,report,ledger,shards,reconcile}/ and pipeline_manifest.json
Test log:        teams/01-data-a/jobs/logs/2026-11-19-first-training-rehearsal-38packs/ (all 86 parts of sample v0, 38 packs, frozen p1536, Linux + pinned env: 59/59 checks; with the inventory, prepare_run's run.json at 2691c44: 74/74)
```

## Update of 22 Nov 2026 for corpus-v1

This revises the request of #599 now that TSAI has confirmed the input manifest. Nothing else in the pipeline changes.

- **Dataset version:** `prepare_run.py` generated `dataset_version` `first-training-v1`; it now generates `corpus-v1`. The `run_id` argument is unchanged and is only the output folder name.
- **Pinned code:** `main` at `421f8497ddb1585666e8f5a274c524e4462402cc` (merge of #716), plus this update, which touches only `prepare_run.py` (the constant), its test, and these docs. Run from `main` once this update is merged.
- **Pinned cleaner:** `teams/01-data-a/spec_v1_1/clean.py`, SHA-256 `6a57276c0e83312b09facfba656cca28db0ef59ca851bcfbfa3ef63f16fdd1f2`, which equals `clean_sha256` in `teams/01-data-a/pipeline/clean.json`; the clean stage refuses any other file.
- **Pinned scope:** `approved_inputs.json`, SHA-256 `10f313750235902d401cfb1023555b37e575fc8a11a5adccceeab84af7515f5f` (the confirmed version). The input manifest records this hash and `prepare_run.py` refuses a manifest built from any other version.
- **Checks:** `pytest` of the command under "Scope and prerequisites" passes (146 tests) on this branch.

## Scope and prerequisites

This is an integration request. TSAI stages the approved raw inputs and applies the approved spec v1.1 cleaning rules as part of the agreed pipeline execution. Confirm that this combined run is acceptable under `JOB_REQUEST.md` rule 6, which reserves full-data cleaning for TSAI. TSAI confirmed the source scope on 22 Nov 2026 (`2026-11-19-first-training/approved_inputs.json`, merged in #716): the 38 sample-v0 pack IDs are the final admissible source set for corpus-v1, with no further packs without a separate ruling; production may have more parts per pack, with the same split/pack layout. Verify the fetched source revisions and subset restrictions against TSAI's source catalog before starting.

The job must be staged with these inputs before `--plan` or execution:

- All approved raw parts, at least one in each split for every pack, under `<raw>/train/<pack>/part-<number>.parquet` and `<raw>/heldout/<pack>/part-<number>.parquet`.
- The frozen p1536 `tokenizer.json` (SHA-256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`).
- The published `sentence-transformers/LaBSE` revision `836121a0533e5664b21c7aacc5d22951f2b8b25b`, staged offline at `../models/LaBSE` relative to the repository root; see the pinned files below. The job uses a CUDA host; H3 retains the rehearsed `device: auto` setting and measures `ind-sa-fw2`, `ind-hi-fw2` and `en-fineweb-edu` in report-only mode. All sentence thresholds remain at the rehearsed default 0.7. E5c's provisional Sanskrit 0.55 is a separate measurement configuration; threshold changes are deferred beyond this submission.
- The committed `2026-11-19-first-training/approved_inputs.json`: all 38 packs, TSAI-accepted shard metadata/lanes, and pinned licence text/provenance. The generator materializes these fields as `out/first-training-inputs/pack_metadata.json` for the sharder. The generic `shards/pack_table.json` has the accepted lanes but omits licences.
- The pinned G9 F2 v2 fingerprint set and the packages in `2026-11-19-first-training/requirements_pipeline.txt` in one Python 3.12 environment. No network access or keys at runtime.

## Model staging and resource limits

Run this setup wrapper from the repository root before inventory/config preparation. If the required local model files are missing, it downloads the exact published snapshot. Setup needs network access only for that download; the `hf` CLI is supplied by `huggingface_hub` in the environment. TSAI may pre-stage the same snapshot to skip the download. A complete folder with incorrect weights is rejected by the hash checks; it is not silently accepted.

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
python -I -c "import torch; assert torch.cuda.is_available(), 'CUDA GPU required for this job'; print(torch.cuda.get_device_name(0))"
```

`prepare_run.py` checks these files before publishing `run.json`:

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
   python -I teams/01-data-a/jobs/2026-11-19-first-training/build_inventory.py --input-root <raw-root> --out out/first-training-inputs
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
       "overlap": {"mode": "run", "settings": "teams/01-data-a/dedup/overlap.json"},
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

   The builder requires all 38 packs in both splits and rejects unknown packs, invalid part names, missing columns, changed files and duplicate numeric part indices. The generator refuses an incomplete pack table or an unfrozen tokenizer.

3. Check the generated config, then run the same file. Both commands use the same checkout and working directory:

   ```bash
   python -I teams/01-data-a/pipeline/run_pipeline.py --config out/first-training-inputs/run.json --plan
   python -I teams/01-data-a/pipeline/run_pipeline.py --config out/first-training-inputs/run.json
   ```

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

Return the console log, `pipeline_manifest.json`, `inventory_check.json`, clean `job_summary.json`, `cleaned_manifest.json`, `rule_counts.csv` and `rule_examples.csv`, H3 summary and match counts, `shards_summary.json`, and `reconcile_summary.json` under `teams/01-data-a/jobs/results/2026-11-19-first-training/`. Limit repository-returned logs/reports to 50 MiB total. Keep audit sidecars, Parquet, token binaries and document text in TSAI's job storage; report their paths and hashes without committing their content.

Acceptance requires exit code 0, inventory report `ok: true`, no missing or unlisted input part, zero heldout shards, H3 `removed: 0`, shard files verified on disk, and reconciliation of every kept train document. Include the runtime, peak memory, H3 model hash and package versions, shard/token counts, and any empty or all-left-out train parts in the returned log.
