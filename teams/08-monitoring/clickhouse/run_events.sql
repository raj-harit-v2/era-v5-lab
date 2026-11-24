-- ERA V5 Team 08 (Monitoring & Records): run events for the open infrastructure health panels.
-- One row per checkpoint commit or failure, restore (a restart), and alarm hit, kept apart from `metrics_raw`
-- so the counts come from stored rows and never reset on a browser refresh.
-- Loaded by load_run_events.py from Team 07's `v5-event/1` lines and from `alarms.py --jsonl` output.
-- No host, job, store-path or file-name columns: the loader keeps an allowed list of fields only.

CREATE TABLE IF NOT EXISTS run_events
(
    run_id      LowCardinality(String),
    event_time  Nullable(DateTime64(3, 'UTC')),
    step        Nullable(Int64),
    kind        LowCardinality(String),
    event       LowCardinality(String),
    severity    LowCardinality(String),
    detail      String,
    source      LowCardinality(String),
    event_key   String,
    loaded_at   DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (run_id, event_key);
