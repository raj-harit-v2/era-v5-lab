# Dry Run 1: Live Monitoring & Alarm Report (`alarms_dryrun1.md`)

**Team:** 08 — Monitoring & Records  
**Scope:** Live ingestion latency (`< 1 minute` to Grafana), zero-missing-step audit, per-token Parquet capture (`v5-token-records/1`), and active alarm log for **Dry Run 1** (Week 3).

---

## 1. Ingestion & Latency Pipeline

1. **Step & Telemetry Writers:**
   - Training loop writes per-step scalars (`loss_ntp`, `loss_mtp`, `lr`, `tokens_per_second`, `gradient_norm`, `gradient_clipping_applied`, `expert_load`, `validation_loss`, `validation_bpb`, etc.) via `metrics_logger/metrics_writer.py` (`flush_every = 10`, immediate flush on non-finite values).
   - Node & GPU sampler streams (`gpu_sample` 1s telemetry, `step_timing`, `v5-health/1` pre-flight & periodic node health) feed into ClickHouse (`metrics_raw`, `node_health`, and materialized rollups `metrics_rollup_10`..`10000`, `gpu_telemetry_1s`).
2. **Latency SLA (`< 60s` to Grafana):**
   - `clickhouse/load_jsonl.py` + `clickhouse/check_rows.py` ingest incremental lines idempotently (`ReplacingMergeTree` + `ingest_manifest`) and verify zero dropped or null rows against source files.
   - End-to-end lag is bounded by `flush_every * step_time + loader_poll_interval` (target `< 60s`).
3. **Per-Token Parquet Capture (`metrics_logger/per_token_parquet.py`):**
   - Stores ZSTD-3 Parquet partitions under `records/per_token/run_id={run_id}/step_bucket={step_bucket}/part-step_{step:08d}-rank_{rank:02d}.parquet` on warmup (`0..100`), checkpoint windows (`[-20, +10]`), `3σ` / `2×` / non-finite loss anomalies (+10-step tail, tagged `INCIDENT_RETAIN=true`), entropy divergence (`< 0.5` or `> 8.0` nats), and held-out validation slices, with 14-day default pruning.

---

## 2. Active Alarm Rules (`alarms/alarms.py`)

| Rule | Severity | Condition | Dry Run 1 Action |
|---|---|---|---|
| `non_finite` | `stop` | Any `NaN` / `Inf` in step metrics (flushed immediately) | Halt / restore from last `COMPLETE` checkpoint; retain per-token Parquet |
| `spike_score` | `page` | Trailing 100-step z-score `> 7.0` on `loss_ntp`, `loss_mtp`, or `gradient_norm` | Inspect step batch & Parquet slice; cross-check Team 07 node health |
| `ema_z` | `warn` | EMA z-score above configured threshold on moderate jumps | Log warning; watch for sustained drift |
| `throughput_drop` | `page` | `tokens_per_second` drops `> 20%` below warmup median for `100` steps | Cross-check `loader_wait_time`, GPU thermal throttle, and slow ranks with Team 06 & Team 07 |
| `moe_routing` | `warn` | Dead expert (`0.0` load) or `router_max_vio > 1.0` for `moe_patience` steps | Flag router imbalance to Team 05 |
| `static_bound` | `warn` / `page` | Metric crosses configured `[lo, hi]` bound (once per excursion) | Inspect memory (`gpu_alloc_gib`, `gpu_memory_used`) or thermal (`gpu_temp_c`) excursion |

*(Fault-injection verification and time-to-alert measurements for these rules are recorded in [`docs/alert_tests.md`](docs/alert_tests.md).)*

---

## 3. Dry Run 1 Run Inventory & Step Completeness Audit

*(Populated as TSAI executes Dry Run 1 jobs and commits run logs to the repository.)*

| Run ID | Source Path | Steps Expected | Steps Ingested | Missing / Duplicate Steps | Max Grafana Lag (s) | `check_rows.py` Verdict |
|---|---|---|---|---|---|---|
| *(awaiting Dry Run 1 logs)* | — | — | — | `0` target | `< 60s` target | PENDING |

---

## 4. Dry Run 1 Alarm & Incident Log

| Timestamp (UTC) | Run ID | Step | Rule & Severity | Metric & Observed Value | Per-Token Parquet Partition (`INCIDENT_RETAIN`) | Resolution / Root Cause |
|---|---|---|---|---|---|---|
| *(awaiting Dry Run 1 logs)* | — | — | — | — | — | — |
