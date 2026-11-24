# Public Dashboard Content Decisions (Week 4 / Gate 4)

**Owner:** Team 08 (Monitoring & Records)  
**Target host:** `https://training.theschoolofai.in` (`teams/08-monitoring/grafana/public_v1.json`)  
**Status:** Recorded for Week 4 D2 sync with Team 05 (Architecture), Team 06 (Performance), Team 01 (Data A), Team 09 (Evaluation), and Team 11 (Release). Independent of host uptime.

---

## 1. Non-Negotiable Public Dashboard Constraints

Every panel, table, SQL query, and static text block on the public dashboard must satisfy all five constraints (enforced in `teams/08-monitoring/grafana/test_public_dashboard.py` and `teams/08-monitoring/clickhouse/tests/test_shard_composition.py`):

1. **No compute-cost counters:** Never display GPU-hours, dollar spend, cloud pricing, or cost estimates.
2. **No hardware or machine names/specs:** Never display GPU model names, node hostnames, VRAM capacities, peak TFLOPS, interconnect specs, or cluster topology.
3. **Teams only, no person names or `@handles`:** Public titles and descriptions name teams only (e.g., Team 08, Team 09, Team 01) and follow Team 11's glossary (`teams/11-release/dashboard/dashboard_text.md`).
4. **Internally consistent, non-resetting metrics:** All counters and curves are queried directly from persistent ClickHouse tables (`metrics_raw`, `eval_mini`, `shard_composition`, `ingest_batches`) so numbers never reset on browser refresh and never omit restarts or alarm events.
5. **Read-only (`editable: false`) in IST (`Asia/Kolkata`):** Public viewers cannot edit queries or panels; all timestamps render in IST.

---

## 2. Cross-Team Content Decisions (D2)

### 2.1 Team 05 (Architecture) — Live-Run Feed Decision

| Item | Decision |
|---|---|
| **Live run exposed** | Dry Run 2 (`dryrun2-1234`, `#720`) streamed live via `watch_jsonl.py` with `10s` Grafana refresh (`< 30s` end-to-end latency verified in `#703`). |
| **Curves exposed publicly** | Training loss (raw + step-bucket mean), held-out validation loss, held-out validation bits per byte (`val/bpb`), learning rate schedule, tokens per byte (all text & by language), MoE load balance, plus throughput/timing (`tokens_per_s`, `step_time_ms`, `context_length`) and open infra-health events (restart count, alarm hits, checkpoint events). |
| **Held private (`private_v1.json` only)** | Per-GPU thermal/power/VRAM telemetry (`gpu_temp_c`, `gpu_power`, `gpu_memory_used`, `gpu_alloc_gib`), `loader_wait_time`, `node_health` hostnames/XIDs, and per-rank diagnostics. |
| **Sync status** | Proposed in `CAP` on Mon 23 Nov (D2); awaiting Team 05 ACK or adjustments. |

### 2.2 Team 06 (Performance) — Benchmark Panel Decision

| Item | Decision |
|---|---|
| **Public throughput section** | Expose hardware-agnostic pace metrics already logged in `metrics_raw`: `tokens_per_s`, `step_time_ms`, and `context_length` alongside the loss curves. |
| **Held private (`private_v1.json` / Team 06 reports)** | `mfu_run` / `mfu_method` (`g6-v1`/`g6-v2` peak-FLOPS ratios) and per-operator kernel timing breakdowns, because MFU and kernel traces imply hardware specs and machine-specific assumptions that do not belong on the public page. |
| **Sync status** | Proposed in `CAP` on Mon 23 Nov (D2); awaiting Team 06 ACK or additions. |

### 2.3 Team 01 (Data A) — Dataset & Shard Composition Table

| Item | Decision |
|---|---|
| **Dedicated ClickHouse table** | `shard_composition` (`teams/08-monitoring/clickhouse/shard_composition.sql`), separate from `metrics_raw`, keyed by `(dataset_version, stage, pack_id)`. |
| **Columns exposed publicly** | `pack_id`, `domain`, `language`, `stage`, `docs_in`, `docs_kept`, `token_count`, `drop_rate_pct`, `dataset_version`. |
| **Loader contract** | `teams/08-monitoring/clickhouse/load_shard_composition.py` ingests Team 01's cleaned/sharded manifest summary (JSON or CSV), validates non-negative counts and `0 <= drop_rate_pct <= 100`, and rejects forbidden hardware/cost fields. |
| **Sync status** | Coordinated in `CAP` on Mon 23 Nov (D2) to align on the exact summary file produced by the `corpus-v1` clean/shard job (`#728`). |

### 2.4 Team 09 (Evaluation) — Eval-Mini Scores Alongside Training Loss

| Item | Decision |
|---|---|
| **Public panel** | Plot Tier A `eval_mini` checkpoint scores (from ClickHouse `eval_mini` table, populated by Team 09's live `eval_watcher.py` during Dry Run 2) directly alongside the training loss curve on the shared `step` X-axis. |
| **Lag protection** | Guarded by Team 08 + Team 09's Week 4 eval-watcher lag alarm (fires when the newest Tier A step in `eval_mini` falls more than 2 checkpoint intervals behind `metrics_raw`). |

---

## 3. Planned Public Dashboard Upgrades (Next Promotion After Team 11 Text Sign-Off)

`teams/08-monitoring/grafana/public_v1.json` currently renders the 7 TSAI-approved panels (`#598`, `#629`) and remains strictly synced with `teams/11-release/dashboard/dashboard_text.md`. Once Team 05, Team 06, Team 01, and Team 11 sign off on the new plain-language sentences in `dashboard_text.md`, Team 08 will promote the following 5 additions to `public_v1.json`:

1. **Dataset / Shard Composition Table:** Static table querying `shard_composition` (`pack_id`, `domain`, `language`, `stage`, `token_count`, `drop_rate_pct`).
2. **Eval-Mini Scores Alongside Training Loss:** Trend panel joining `eval_mini` Tier A checkpoint scores on `step` next to training loss once Dry Run 2's watcher is live.
3. **Training Pace Section (`tokens_per_s`, `step_time_ms`, `context_length`):** Dedicated row querying `metrics_raw` (hardware-agnostic, zero GPU/MFU specs).
4. **Open Infra Health Panel:** Transparent counts of training restarts, alarm hits, and completed checkpoints — never hidden to preserve credibility.
5. **"What This Shows / What It Doesn't" Static Text Panel:** Plain-language scope note stating clearly what the run scale is (e.g., T2 dry run vs. main run), what the curves measure, and what they do not claim.
