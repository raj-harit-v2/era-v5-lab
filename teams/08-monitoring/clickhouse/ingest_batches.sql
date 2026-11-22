-- ERA V5 Team 08: one row per batch that `watch_jsonl.py` loaded into `metrics_raw` (Issue #27).
-- `start_offset` and `end_offset` are byte positions in `source_file`. `max(end_offset)` for a run and file is
-- where a restarted watcher continues; `sum(lines)` is the line number it continues from.
-- `lines` counts the non-blank lines read, `rows` the `metrics_raw` rows inserted, and `skipped_lines` the lines
-- whose `(step, rank)` was already stored for the run, such as the history a resumed trainer writes again (#606).
-- `seen_at` is when the watcher read the bytes; `inserted_at` is when the `metrics_raw` INSERT returned.

CREATE TABLE IF NOT EXISTS ingest_batches
(
    run_id        LowCardinality(String),
    source_file   String,
    start_offset  UInt64,
    end_offset    UInt64,
    first_step    UInt64,
    last_step     UInt64,
    lines         UInt32,
    rows          UInt32,
    skipped_lines UInt32,
    seen_at       DateTime64(3, 'UTC'),
    inserted_at   DateTime64(3, 'UTC')
)
ENGINE = MergeTree
ORDER BY (run_id, source_file, start_offset);
