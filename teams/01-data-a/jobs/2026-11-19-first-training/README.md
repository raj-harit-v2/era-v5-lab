# First-training input preparation

`approved_inputs.json` allows the 38 unique sample-v0 pack IDs, with their pinned
dedup policy, source restrictions and licence provenance. Scope confirmed by TSAI on 22 Nov 2026 (corpus-v1): additional production Parquets use these same sources and
`<raw>/<train|heldout>/<pack_id>/part-<number>.parquet` layout. Sample-v0's 86 parts
are a reference, not the production part count.

Use the recorded subsets: MegaMath is `megamath-web`; code retains per-file
licensing and attribution; notebook, Stack Exchange and Nemotron configs must
match `subset_requirements`. Other pack IDs are rejected.

## Prepare the manifest and inventory

Stage the complete selected raw-file set, with at least one train and one heldout
part per allowed pack. Numeric part indices must be unique within a pack/split.
Record upstream revisions/configs and verify the fetch against its source catalog.
With PyArrow installed, run from the repository root:

```bash
python -I teams/01-data-a/jobs/2026-11-19-first-training/build_inventory.py --input-root /path/to/raw --out out/first-training-inputs
```

The output folder must be new. The builder reads all staged Parquets, checks the
allowlist, schema columns and file identities, and publishes:

- `input_manifest.json`: actual paths, raw rows/bytes/SHA256, source metadata and
  the approved-scope hash.
- `expected_inventory.json`: all parts with raw SHA256/rows and expected status,
  bound to the exact input manifest's SHA256.

These files are generated before cleaning. The builder cannot verify upstream
subset identity or discover files omitted from the fetch; check those against the
source catalog. The clean preflight validates row values and per-part doc_id
uniqueness.

After TSAI stages the pinned offline LaBSE model, use the shard metadata in `approved_inputs.json` (accepted lanes plus licence
provenance) to generate the pinned run config without hand-copying hashes or part counts:

```bash
python -I teams/01-data-a/jobs/2026-11-19-first-training/prepare_run.py --bundle out/first-training-inputs --input-root /path/to/raw --tokenizer /path/to/p1536/tokenizer.json --f2-workers 30 --run-id first-training-v1
```

The generator materializes `out/first-training-inputs/pack_metadata.json` from
`approved_inputs.json`; there is no second committed table. `--pack-table` can
optionally select an explicit table, whose licences are checked against the scope. `--f2-workers` defaults
to 1; choose 30 only on a host with enough CPU and RAM (the rehearsal used 32 vCPU).
The generator checks the published LaBSE weight/config sizes and SHA256 before
writing `run.json`; model revision and staging commands are in the job request.

Use one Python 3.12 environment with `requirements_pipeline.txt`; the overlap
and H3 requirements agree on NumPy 2.4.3 and PyArrow 23.0.1.

## Pipeline settings

| Setting | Value |
|---|---|
| `inventory` | Generated `expected_inventory.json` |
| `stages.clean.manifest` | Generated `input_manifest.json` |
| `stages.clean.manifest_sha256` | Inventory's `input_manifest_sha256` |
| `stages.clean.input` / `stages.ledger.raw` | Same staged raw root |
| `stages.clean.expected_parts` | Actual generated train/heldout counts |
| `stages.shards.packs` | All allowed IDs, or omit to select all |
| `stages.shards.dataset_version` | `corpus-v1` (fixed by `prepare_run.py`; independent of `--run-id`) |
| `stages.reconcile` | Enabled |
| `stages.f2.workers` | Selected with `--f2-workers` |
| `stages.shards.pack_table` | Generated `out/first-training-inputs/pack_metadata.json` |

Process both splits through clean, overlap, dedup/apply, F2 and the raw ledger.
For H3, add `"h3": {"mode": "run", "settings":
"teams/01-data-a/jobs/2026-11-19-first-training/h3.json"}` to `stages`.
The runner runs H3 after overlap on the same cleaned parts, verifies its completed
summary and match-file hash, then supplies that match file to dedup. Dedup uses
`remove: false`: H3 reports translation matches but does not remove documents.
The job requests a CUDA host; H3 retains the rehearsed `device: auto`, fp16 on
CUDA, and default sentence threshold 0.7 for every pair. E5c's provisional
Sanskrit 0.55 threshold is deferred to a separate measurement. Removal stays
disabled until the separate validation gates pass.
Stage the offline LaBSE model at the `model_path` in `h3.json` and install
`dedup/requirements_h3.txt` in the job environment. This setting currently
measures the Sanskrit, Hindi and English packs named in `h3.json`; expand the
pack/language-pair scope only after reviewing thresholds and compute cost.
Dedup protects heldout rows; F2 may remove fingerprint matches from either split.
The existing shard runner receives the complete `final/` root, writes train only,
and records heldout as `not_sharded`. The inventory permits `written`, `empty` or `all_left_out` for train
and `not_sharded` for heldout. Use a pack table with lane and licence metadata for
all allowed packs.

The clean settings retain Parquets and enable five audit samples per pack/rule.
`clean/rule_examples.csv` contains IDs, actions and character counts; per-part
sidecars live in `clean/audit/`. See the job request for the return contract.

## Tests

```bash
python -m pytest -q teams/01-data-a/jobs/2026-11-19-first-training/tests
```
