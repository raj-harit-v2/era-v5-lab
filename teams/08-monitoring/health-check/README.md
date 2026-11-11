# Node health-check JSON format (`v5-health/1`)

`health_check.py` defines the JSON contract between Team 7's node health scripts (`gpu_health.sh`,
`xid_scan.py`, `nccl_probe.py`, `launch.sh`) and Team 8's monitoring and ClickHouse loader.

```bash
python -I teams/08-monitoring/health-check/health_check.py --selftest
python -I teams/08-monitoring/health-check/health_check.py --validate node_health.jsonl
python -I teams/08-monitoring/health-check/health_check.py --clickhouse-jsonl node_health.jsonl
python -I teams/08-monitoring/health-check/health_check.py --example full
```

## 1. Top-level report (`v5-health/1`)

Each run of `gpu_health.sh` writes one JSON object to stdout (and one line when appended to a `.jsonl` node log):

```json
{
  "schema": "v5-health/1",
  "host": "gpu-node-01",
  "timestamp_utc": "2026-10-28T12:00:00+00:00",
  "mode": "prolog",
  "expected_gpus": 8,
  "verdict": "pass",
  "admit_training": true,
  "checks": [
    {
      "name": "gpu_inventory",
      "status": "pass",
      "required": true,
      "reason": "",
      "metrics": {"count": 8, "gpus": ["0, GPU-0000, GPU-80GB, 81559, 81000, 38"]}
    }
  ],
  "drain_reason": null,
  "runtime_seconds": 1.4
}
```

| Field | Type | Rule |
|---|---|---|
| `schema` | `"v5-health/1"` | Versioned contract name. |
| `host` | `str` | Node hostname (`hostname -s` or `socket.gethostname()`). |
| `timestamp_utc` | `str` | ISO-8601 UTC timestamp (`time` accepted as an alias). |
| `mode` | `"prolog"` \| `"periodic"` \| `"full"` | `prolog` before a job starts; `periodic` every 30 s while a node is up; `full` before dry runs or after a repair. |
| `expected_gpus` | `int` | Expected GPU count on the node (`8` on a GPU worker node, `0` on a CPU-only test host). |
| `verdict` | `"pass"` \| `"warn"` \| `"fail"` | Derived from `checks` (see §2). |
| `admit_training` | `bool` | `false` on `verdict == "fail"`; when `expected_gpus > 0`, `true` requires a passing `gpu_inventory` check (`prolog` may admit on `warn` when GPUs are present). |
| `checks` | `list[dict]` | Non-empty list of check records (see §3). |
| `drain_reason` | `str` \| `null` | Non-empty string naming the failing check(s) (e.g. `ecc_uncorrectable,xid` or `xid: 79`) when `verdict == "fail"`; `null` otherwise. |
| `runtime_seconds` | `float` (optional) | Total wall-clock time of the health check run (budget $\le 30\text{ s}$ in `prolog`/`periodic`). |

## 2. Verdict and missing-tool rules

Every check has `status` in `{"pass", "warn", "fail", "skipped"}`, a boolean `required`, `reason` (or `detail`), `metrics`, and optional `gpu` and `seconds`:

1. Any check with `status == "fail"` $\rightarrow$ `verdict = "fail"`.
2. Otherwise any check with `status == "warn"`, or any check with `status == "skipped"` and `required == true`, $\rightarrow$ `verdict = "warn"`.
3. Otherwise $\rightarrow$ `verdict = "pass"`.

A missing tool (`nvidia-smi`, `journalctl`, `dcgmi`, `torchrun`) must be reported as `"skipped"` with a non-empty `reason` (and `source: null` on a skipped standalone `xid_scan.py` output). It never turns into `"pass"`.

## 3. Standard checks and `metrics` fields

| Check `name` | Mode | `metrics` fields | Fail / warn condition |
|---|---|---|---|
| `gpu_inventory` | all | `count` (`int`), `gpus` (`list[str]`) | `nvidia-smi` fails, or `expected_gpus > 0` and `count != expected_gpus`. |
| `xid` | all | `counts` (`{code: int}`), `events` (`[{pci_bdf, code, severity, reason}]`, new events since last check) | Any event with `severity == "fail"` fails; `severity == "warn"` warns. |
| `ecc_uncorrectable` | all | `values` (`list[int]`, max of volatile and aggregate per GPU) | Any GPU has uncorrectable ECC $> 0$. |
| `remapped_rows` | all | per-GPU pending/failure status | Row-remap failure fails; pending remap warns. |
| `nvlink` | all | `links`, `inactive`, `down` (`int`) | Any active NVLink link inactive/down. |
| `dcgm_health` / `dcgm_quick` | `periodic` / `prolog`, `full` | `exit_code` (`int`), `output_tail` (`str`) | Background health watch (`periodic`) or `dcgmi diag -r 1/2` (`prolog`/`full`) failure. |
| `nccl_all_reduce`, `nccl_reduce_scatter`, `nccl_all_gather`, `nccl_all_to_all` | `full` | `g7-collective/1` (`backend`, `world_size`, `status`, `sizes` with `bytes`, `seconds`, `max_error`, `all_ranks_correct`, optional `busbw_gbps`) | Non-zero `max_error`, `all_ranks_correct == false`, bandwidth below floor, timeout, or `backend != "nccl"` when `expected_gpus > 0`. |
| `clock_offset`, `nvme_free`, `host_mem`, `gpu_temperature`, `pcie_link`, `gpu_throttle` | all (optional) | check-specific scalar/per-GPU values | Host clock $> 100\text{ ms}$, low NVMe space, GPU $\ge 90\,^\circ\text{C}$ fail; throttle/PCIe degradation warn. |

On a GPU node (`expected_gpus > 0`), passing a collective check requires `backend == "nccl"` and `world_size >= 2`. On a CPU-only test host or Docker simulation (`expected_gpus == 0`), `backend == "gloo"` with `world_size >= 2` is accepted.

## 4. Xid classification

`xid_scan.py` parses `NVRM: Xid (PCI:<bdf>): <code>` from `journalctl -k` or `dmesg` and deduplicates lines already seen so periodic 30 s checks do not re-count old errors:

| Severity | Xid codes | Action |
|---|---|---|
| `fail` | `48` (DBE ECC), `61` / `62` (internal micro-controller breakpoint/halt), `64` (row-remap failure), `74` (NVLink), `79` (fell off bus), `92` (high SBE rate), `95` (uncontained memory), `119` / `120` (GSP), `140` (unrecovered ECC) | Block admission, page on-call, drain node. |
| `warn` first, `fail` on repeat | `63` (row-remap event), `94` (contained memory error) | First Xid `94` on a GPU warns (restart job); a second on the same GPU within 24 h fails and drains the node. |
| `warn` | `13` (graphics engine), `31` (MMU page fault), `43` (app stopped), `45` (channel cleanup), or any unlisted code | Report warning; never silently ignore unknown Xid codes. |

## 5. Week 2 ClickHouse loader row (`--clickhouse-jsonl`)

Each validated `v5-health/1` line maps to one row for the `node_health` table so that ClickHouse row counts match JSONL line counts:

| Column | Type | Source |
|---|---|---|
| `timestamp_utc` | `String` | `report.timestamp_utc` |
| `host` | `String` | `report.host` |
| `mode` | `LowCardinality(String)` | `report.mode` |
| `expected_gpus`, `gpus_seen` | `UInt8` | `report.expected_gpus`, `gpu_inventory.metrics.count` |
| `verdict` | `LowCardinality(String)` | `report.verdict` |
| `admit_training` | `UInt8` | `report.admit_training` |
| `drain_reason` | `String` | `report.drain_reason` (`""` when `null`) |
| `checks_pass`, `checks_warn`, `checks_fail`, `checks_skipped` | `UInt8` | Counts by status in `report.checks` |
| `xid_codes` | `Array(UInt16)` | Sorted integer keys of `xid.metrics.counts` |
| `ecc_uncorrectable_total` | `UInt32` | Sum of `ecc_uncorrectable.metrics.values` |
| `nccl_status` | `LowCardinality(String)` | `nccl_all_reduce.status` (`"not_run"` in `prolog`) |
| `runtime_seconds` | `Float32` | `report.runtime_seconds` (`0.0` when omitted) |
| `raw_json` | `String` | Full canonical JSON line |

### Collector & virtualized-runner operational notes

1. **Collector-side `DEAD` node detection**: A hard-hung or network-partitioned node cannot emit its own `fail` line. The ClickHouse collector marks a node `DEAD` (and alerts) when $\ge 3$ consecutive `periodic` intervals ($90\text{ s}$ at the default $30\text{ s}$ cadence) pass without a new `node_health` row for that `host`.
2. **Non-blocking periodic probes**: `periodic` checks must use read-only NVML / `nvidia-smi` queries with a short timeout and never synchronize active CUDA training streams; a hung NVML query is recorded as `gpu_inventory` `status == "fail"` (`verdict == "fail"`).
3. **Virtualized/cloud GPU identifiers**: On container runners such as Modal A100 where `pci.bus_id` may return `[Unknown Error]`, `gpu_inventory.metrics.gpus` records the GPU index and `uuid` (`GPU-...`) as the stable hardware identifier.

## 6. Verification and cross-team validation

- **Unit self-tests (`--selftest`)**: `python -I teams/08-monitoring/health-check/health_check.py --selftest` passes **18/18** checks, including Team 7's `health_injected_xid.json` fixture, standalone `xid_scan.py` (including skipped `source: null`) and `nccl_probe.py` outputs, missing-tool `skipped` handling, non-integer `world_size` rejection, `xid.counts` vs `xid.events` consistency, required `gpu_inventory` when `expected_gpus > 0`, CPU `gloo` collective validation when `expected_gpus == 0`, and ClickHouse row flattening.
- **Cross-team validation against Team 7 (`PR #150`, `teams/07-infrastructure/health/health_check.py`)**: All 5 live outputs generated by Team 7's health runner pass `validate_report` and `to_clickhouse_row` with **0 violations**:
  1. **Injected bad 8-GPU node** (uncorrectable ECC on GPU 3 + Xid `13, 79, 94, 157`): `verdict="fail"`, `admit_training=false`, `drain_reason="ecc_uncorrectable,xid"`, `ecc_uncorrectable_total=2`, `xid_codes=[13, 79, 94, 157]`.
  2. **8-GPU node missing `nvidia-smi`**: `verdict="warn"`, `admit_training=false`, `gpus_seen=0`, `checks_skipped=6`.
  3. **CPU host (`expected_gpus=0`) `prolog`**: `verdict="pass"`, `admit_training=true`, `nccl_status="not_run"`.
  4. **Live GPU host (`expected_gpus=1`) `prolog`**: `verdict="pass"`, `admit_training=true`, `gpus_seen=1`, `ecc_uncorrectable_total=0`.
  5. **CPU host (`expected_gpus=0`) `full` mode with 2-rank `gloo` collectives** (`nccl_all_reduce`, `nccl_reduce_scatter`, `nccl_all_gather`, `nccl_all_to_all` via `allreduce_test.py`): `verdict="pass"`, `admit_training=true`, `nccl_status="pass"`.

