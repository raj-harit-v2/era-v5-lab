-- ERA V5 Team 08 (Monitoring & Records) — Dataset & Shard Composition Table
-- Separate from `metrics_raw` so the public dashboard can render a clean
-- pack/domain x stage x token_count x drop_rate_pct table from Team 01 (Data A)
-- corpus-v1 clean/shard manifest summaries without leaking raw text, hardware
-- specs, or compute cost.

CREATE TABLE IF NOT EXISTS shard_composition
(
    dataset_version LowCardinality(String),
    stage           LowCardinality(String),
    pack_id         LowCardinality(String),
    domain          LowCardinality(String),
    language        LowCardinality(String),
    docs_in         UInt64,
    docs_kept       UInt64,
    token_count     UInt64,
    drop_rate_pct   Float64,
    loaded_at       DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (dataset_version, stage, pack_id);
