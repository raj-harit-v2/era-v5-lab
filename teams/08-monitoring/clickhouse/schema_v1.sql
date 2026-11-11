-- ERA V5 Team 08 (Monitoring & Records) — ClickHouse Schema v1
-- Table `metrics_raw`: stores per-step training metrics and 1 Hz GPU telemetry.
-- Missing or non-finite values ("null", "nan", "inf", "-inf") are stored as NULL
-- in `value` (Nullable(Float64)) so no JSONL line is dropped during ingestion.

CREATE TABLE IF NOT EXISTS metrics_raw
(
    run_id LowCardinality(String),
    step   UInt64,
    time   DateTime64(3, 'UTC'),
    name   LowCardinality(String),
    value  Nullable(Float64),
    rank   UInt16 DEFAULT 0
)
ENGINE = MergeTree
ORDER BY (run_id, name, step, rank);

-- Tracks each ingested JSONL / JSON file so `check_rows.py` can verify that
-- ClickHouse line counts and metric row counts (including NULLs) match the source file.
CREATE TABLE IF NOT EXISTS ingest_manifest
(
    run_id        LowCardinality(String),
    source_file   String,
    jsonl_lines   UInt64,
    metric_rows   UInt64,
    null_rows     UInt64,
    loaded_at     DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (run_id, source_file);

-- Node health reports (`v5-health/1` contract between Team 07 and Team 08).
CREATE TABLE IF NOT EXISTS node_health
(
    timestamp_utc           String,
    host                    LowCardinality(String),
    mode                    LowCardinality(String),
    expected_gpus           UInt8,
    gpus_seen               UInt8,
    verdict                 LowCardinality(String),
    admit_training          UInt8,
    drain_reason            String,
    checks_pass             UInt8,
    checks_warn             UInt8,
    checks_fail             UInt8,
    checks_skipped          UInt8,
    xid_codes               Array(UInt16),
    ecc_uncorrectable_total UInt32,
    nccl_status             LowCardinality(String),
    runtime_seconds         Float32,
    raw_json                String
)
ENGINE = MergeTree
ORDER BY (host, timestamp_utc);

-- Team 09 `eval_mini_v1` result store (`teams/09-evaluation/results/eval_mini_v1_schema.md`, PR #186).
-- Record key (Section 4): `(model, model_revision, format, item_set, task, num_fewshot, metric, filter)` — never NULL.
-- Nullable fields (Section 2 & 3): `checkpoint`, `dtype`, `seed`, `stderr`, `n_items_total`, `profile`, `derived_from`,
-- plus dotted flat fields (`checkpoint.*`, `seed.*`, `harness.script_sha256`).
CREATE TABLE IF NOT EXISTS eval_mini
(
    run_id                  LowCardinality(String),
    model                   LowCardinality(String),
    model_revision          String,
    format                  LowCardinality(String),
    item_set                String,
    task                    LowCardinality(String),
    num_fewshot             UInt16,
    metric                  LowCardinality(String),
    filter                  LowCardinality(String),
    backend                 String,
    primary                 UInt8,
    value                   Float64,
    stderr                  Nullable(Float64),
    dtype                   Nullable(String),
    n_items                 UInt32,
    n_items_total           Nullable(UInt32),
    profile                 Nullable(String),
    decoding                LowCardinality(String),
    checkpoint              Nullable(String),
    checkpoint_run          Nullable(String),
    checkpoint_branch       Nullable(String),
    checkpoint_step         Nullable(UInt64),
    checkpoint_epoch        Nullable(UInt32),
    checkpoint_tokens_seen  Nullable(UInt64),
    checkpoint_path         Nullable(String),
    seed                    Nullable(String),
    seed_random             Nullable(Int64),
    seed_numpy              Nullable(Int64),
    seed_torch              Nullable(Int64),
    seed_fewshot            Nullable(Int64),
    harness_name            LowCardinality(String),
    harness_version         LowCardinality(String),
    harness_script_sha256   Nullable(String),
    hardware                String,
    run_date                String,
    derived_from            Nullable(String),
    notes                   Array(String),
    loaded_at               DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (run_id, model, model_revision, format, item_set, task, num_fewshot, metric, filter);
