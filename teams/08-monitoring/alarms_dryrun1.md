# Dry Run 1: Live Monitoring & Alarm Report (`alarms_dryrun1.md`)

**Team:** 08 — Monitoring & Records  
**Scope:** Ingestion latency (`< 1 minute` to Grafana), zero-missing-step audit, per-token Parquet capture (`v5-token-records/1`), and alarm verification for **Dry Run 1** (Week 3).

---

## 1. Ingestion & Latency Pipeline

1. **Step & Telemetry Writers:**
   - When `--logger-factory` is enabled, the training loop writes per-step scalars via `metrics_logger/g5_adapter.py` + `metrics_logger/metrics_writer.py` (`flush_every = 10`, immediate flush on non-finite values).
   - Dry Run 1 (`#475`) ran Team 05's harness directly without `--logger-factory`, writing raw `metrics.jsonl` rows (`step`, `loss_ntp`, `loss_mtp`, `lr`, `gradient_norm`, `gradient_clipping_applied`, `tokens_per_second`, `gpu_alloc_gb`, plus `val/*` slices). Both `clickhouse/load_jsonl.py` and `alarms/alarms.py --jsonl <path>` accept raw Team 05 `metrics.jsonl` files directly without transformation.
2. **Latency SLA (`< 60s` to Grafana):**
   - `clickhouse/load_jsonl.py` + `clickhouse/check_rows.py` ingest incremental lines idempotently (`ReplacingMergeTree` + `ingest_manifest`) and verify zero dropped or null rows against source files.
   - End-to-end lag is bounded by `flush_every * step_time + loader_poll_interval` (target `< 60s`).
   - `clickhouse/watch_jsonl.py` loads a growing `metrics.jsonl` every 2 s (byte offsets in `ingest_batches`); measured lag on a real-pace replay of dry run 1 is in section 5 (`19.81 s` max to ClickHouse, `29.8 s` with the 10 s Grafana refresh).
3. **Per-Token Parquet Capture (`metrics_logger/per_token_parquet.py`):**
   - Stores ZSTD-3 Parquet partitions under `records/per_token/run_id={run_id}/step_bucket={step_bucket}/part-step_{step:08d}-rank_{rank:02d}.parquet` on warmup (`0..100`), checkpoint windows (`[-20, +10]`), `3σ` / `2×` / non-finite loss anomalies (+10-step tail, tagged `INCIDENT_RETAIN=true`), entropy divergence (`< 0.5` or `> 8.0` nats), and held-out validation slices, with 14-day default pruning.

---

## 2. Alarm Rules (`alarms/alarms.py` & `alarms/continuity_rules.py` Exact Defaults)

`alarms/alarms.py` is the canonical source of truth for Team 07's runbook (`docs/runbook.md`):

| Rule | Module | Default State & Severity | Exact Default Condition in Code | Dry Run 1 Notes & Action |
|---|---|---|---|---|
| `non_finite` | `alarms.py` | **ON** (`stop`) | Any `NaN` or `Inf` in step metrics (flushed at once by `MetricsWriter`) | Halt / restore from last `COMPLETE` checkpoint; retain per-token Parquet |
| `spike_score` | `alarms.py` | **ON** (`page`) | Trailing `window = 1,000` steps (`min_window = 100`), z-score `> 7.0` (`sigma_threshold = 7.0`) on `loss_ntp`, `loss_mtp`, `gradient_norm`, or `loss` | Inspect step batch & Parquet slice; restore `state_dict()` across restarts so warmup window is preserved |
| `throughput_drop` | `alarms.py` | **ON** (`warn`) | `tokens_per_second` drops `> 10%` (`tps_drop_fraction = 0.10`) below the `100`-step (`tps_window = 100`) pre-slowdown baseline mean for `tps_patience = 100` consecutive steps (step `0` skipped; checking begins after `20` baseline steps, and slow steps are excluded from updating the baseline so a sustained slowdown never drags the reference down) | Cross-check `loader_wait_time`, GPU thermal throttle, and slow ranks with Team 06 & Team 07 |
| `moe_routing` | `alarms.py` | **ON** (`warn`) | Any routed expert at `0.0` load or `router_max_vio > 1.0` (`moe_max_vio_limit = 1.0`) for `moe_patience = 1,000` consecutive steps | **Silent on Dry Run 1:** Team 05's Dry Run 1 rows do not emit `expert_load` yet |
| `ema_z` | `alarms.py` | **OFF by default** (`warn` when `ema_z_threshold` set) | EMA (`ema_alpha = 0.97`, `ema_warmup = 100`) z-score above `ema_z_threshold`; suppressed on steps that already fired `spike_score` | Opt-in moderate-jump warning below `7σ` |
| `static_bound` | `alarms.py` | **OFF by default** (`warn` when `bounds` set) | Metric crosses configured `(lo, hi)` bound; latches once per excursion and re-arms when back in bounds | Opt-in (`bounds={"gpu_alloc_gib": ..., "gpu_temp_c": ...}` must be passed by caller) |
| `val_regression` | `alarms.py` | **OFF by default** (`warn` when `val_regression_frac` set) | `validation_bpb` or `validation_loss` exceeds best-so-far by `> val_regression_frac` for `val_patience = 1` validation runs | Opt-in held-out degradation check; saved in `state_dict()` |
| `step_continuity` | `continuity_rules.py` | **Opt-in** (`page` on gap, `warn` on duplicate) | Detects skipped (`step > prev + 1`) or repeated (`step <= prev`) step numbers in `metrics.jsonl` | Catches unflushed-row gaps after `SIGKILL` + checkpoint restore; flush writer on checkpoint save |
| `loader_stall` | `continuity_rules.py` | **Opt-in** (`warn`) | `loader_wait_time` stays above threshold (`1.0s`) for `patience` (`20`) consecutive steps | Distinguishes host data-loader stalls from GPU compute slowdowns |

*(Synthetic fault-injection verification and time-to-alert measurements for all rules are recorded in [`docs/alert_tests.md`](docs/alert_tests.md).)*

---

## 3. Dry Run 1 Run Inventory & Step Completeness Audit

| Run ID | Source Path / Reference | Steps Expected | Steps Ingested | Missing / Duplicate Steps | `check_rows.py` & ClickHouse Rows | Verdict |
|---|---|---|---|---|---|---|
| `dryrun1_smoke` | `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/metrics.jsonl` (`#475` CPU smoke) | `4` (`0..3`) | `4` (`0..3`) | `0` missing, `0` duplicate | `lines=4`, `metric_rows=195`, `null_rows=0` (`PASS`) | **PASS** |
| `dryrun1_full` | `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl` (`#475` / `#620` full `exp2_muon` `T2` `p1536` run) | `1,222` (`0..1,221`) | `1,222` (`0..1,221`) | `0` missing, `0` duplicate (`StepContinuityMonitor`: `0` alarms) | `lines=1,222`, `metric_rows=19,753`, `null_rows=0` (`PASS`) | **PASS** |

---

## 4. Dry Run 1 Alarm & Incident Log

| Run ID | Execution Mode | Command / Source | Alarms Fired | Notes |
|---|---|---|---|---|
| `dryrun1_smoke` | Offline replay (`alarms.py --jsonl`) | `python teams/08-monitoring/alarms/alarms.py --jsonl teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/metrics.jsonl` | **`0` alarms** (`4` steps read) | `loss_ntp` fell `12.154 -> 6.291`; `val/bpb` `2.4458 -> 2.4321`; all values finite |
| `dryrun1_full` | Offline replay (`alarms.py --jsonl`) on `#620` full-run log | `python teams/08-monitoring/alarms/alarms.py --jsonl teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl` | **`0` `non_finite`**, **`0` `throughput_drop`**, **`3` single-step `gradient_norm` `spike_score` (`page`)** at steps `468` (`5.30`, `7.99σ`), `505` (`4.74`, `7.03σ`), and `841` (`4.99`, `8.31σ`) | All `1,222` rows (`0..1,221`) finite (`0` NaN/Inf); all 3 `gradient_norm` excursions were clipped under `grad_clip = 1.0` with no `loss_ntp` spike and self-recovered on the next step; final `val/bpb = 1.5159` (`COMPLETED`) |

---

## 5. Live Replay Latency (Issue #27)

TSAI returns a job's logs only after the job ends, so the live path (trainer -> `metrics.jsonl` -> `clickhouse/watch_jsonl.py` -> ClickHouse -> Grafana) can't be timed on a real job yet. We timed it by replaying the real dry run 1 log at its real pace: `clickhouse/replay_jsonl.py` wrote the `#620` `metrics.jsonl` one step at a time, each after that step's `perf/step_ms`, and flushed every 10 steps and on non-finite values like `MetricsWriter`. `clickhouse/watch_jsonl.py` loaded the growing file into ClickHouse every 2 s. `clickhouse/replay_latency.py` then matched each step's write time to the `ingest_batches` row that loaded it.

| Run ID | Source Path / Reference | Pace | Steps Ingested | Missing / Duplicate Pairs | ClickHouse Rows | Step finished -> ClickHouse (p50 / p95 / max) | File write -> ClickHouse (p50 / p95 / max) | Grafana Refresh | Worst Case to Grafana | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| `dryrun1-live3` | `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl` (`#620`), replayed 21 Nov 2026 01:47 to 02:26 UTC | real (`--speed 1`), 38.9 min, `0` pauses | `1,222` (`0..1,221`) in `123` batches | `0` missing, `0` duplicate (step, name, rank) pairs | `19,753`, `0` null (same as `dryrun1_full` in section 3) | `9.51 s` / `18.14 s` / `19.81 s` | `0.82 s` / `1.85 s` / `2.03 s` | `10 s` | `29.8 s` (target `< 60 s`) | **PASS** |

- **Step finished -> ClickHouse** runs from the moment a step's line entered the writer's buffer to the `inserted_at` of its batch. Most of it is the 10-step buffer: the first step of a flush waits about 9 x 1.9 s = 17 s for the other nine. **File write -> ClickHouse** is the loader alone: up to one 2 s poll plus the insert.
- **Grafana refresh** is the configured interval, not a measurement. This PR sets `"refresh": "10s"` in `grafana/private_v1.json` (it was `""`, no auto-refresh; OK'd by Sandeep in the Sat 21 Nov sweep). Grafana re-runs the panel queries every 10 s, so a row in ClickHouse shows up at most 10 s later. Worst case = `19.81 s + 10 s`. `dryrun1-live3` ran before the change and was watched with the same 10 s timer set from the dashboard URL (`refresh=10s`).
- **Pauses** are gaps between two steps more than 2 s longer than the step's `perf/step_ms`, which mean the machine slept. Two earlier attempts (`dryrun1-live`, `dryrun1-live2`) were stopped and are not counted because the laptop slept mid-run; `dryrun1-live3` ran under `caffeinate` with `0` pauses.

Commands (start ClickHouse as in `clickhouse/README.md` section 1; on macOS prefix the replay with `caffeinate -i`):

```bash
F=teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl
mkdir -p /tmp/live
python -I teams/08-monitoring/clickhouse/watch_jsonl.py /tmp/live/metrics.jsonl --run-id dryrun1-live3 --poll 2 --idle-exit 120 > /tmp/live/watch.log 2>&1 &
python -I teams/08-monitoring/clickhouse/replay_jsonl.py $F --out /tmp/live/metrics.jsonl --log /tmp/live/written.csv --speed 1
wait
python -I teams/08-monitoring/clickhouse/replay_latency.py /tmp/live/written.csv dryrun1-live3 $F
```

Output of the last command (it exits 1 on a missing step, a duplicate pair, an unmatched line or a pause):

```text
run_id dryrun1-live3: steps 1222 (0..1221), rows 19753, missing 0, duplicate pairs 0
log lines 1222, matched to one batch 1222, unmatched 0
pauses over 2 s: 0 (0.0 s in total)
file write -> ClickHouse     p50   0.82 s  p95   1.85 s  max   2.03 s
step finished -> ClickHouse  p50   9.51 s  p95  18.14 s  max  19.81 s
```
