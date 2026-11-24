-- ERA V5 Team 08: one row per run and check of `alarms/eval_lag.py`, the eval-watcher lag alarm.
-- `lag_s` is the training time from the newest Tier A step in `eval_mini` to the newest training step, read from
-- `ingest_batches` (wall-clock `seen_at`, not the invented `metrics_raw.time`); `threshold_s` is the page limit.
-- `over_limit` = 1 while the lag is above it, and `paged` = 1 on the check that paged. A run gets rows only while
-- it trains. A `checked_at` that stops moving while training goes on means the alarm itself has stopped.

CREATE TABLE IF NOT EXISTS eval_lag_checks
(
    checked_at     DateTime64(3, 'UTC'),
    run_id         LowCardinality(String),
    train_runs     Array(String),
    train_step     UInt64,
    train_seen_at  DateTime64(3, 'UTC'),
    eval_step      Nullable(UInt64),
    eval_loaded_at Nullable(DateTime64(3, 'UTC')),
    lag_s          Float64,
    threshold_s    Float64,
    over_limit     UInt8,
    paged          UInt8,
    detail         String
)
ENGINE = MergeTree
ORDER BY (run_id, checked_at);
