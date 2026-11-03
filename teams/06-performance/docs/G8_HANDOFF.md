# G6 -> G8: performance metrics and live monitoring handoff

**Status:** draft for G8 interface review; not a final sign-off (open items in section 6).
**Date:** 31 October 2026. **G6 coordination:** Siva Ajjapu.

G6 provides the benchmark timing, GPU telemetry, MFU / HFU and their output formats. G8 owns ingestion,
aggregation and rollups, dashboards and alarms. The full method is in [`METRICS.md`](METRICS.md); this note is
the interface G8 builds on and the evidence behind it.

## 1. What G6 delivers

| Deliverable | Where | Status |
|---|---|---|
| MFU / HFU method, system telemetry, JSONL format | `docs/METRICS.md` | Written |
| FLOPs, MFU / HFU, GPU sampler | `perfkit/metrics.py` | Implemented |
| Live JSONL records and their writer thread | `perfkit/events.py` | Implemented (PR #32) |
| Run orchestration, clean-step capture | `perfkit/bench.py` | Implemented |
| CUDA step timer (its event pair is reused for the JSONL) | `perfkit/timer.py` | Implemented |
| Run JSON schema and reason-code checks | `perfkit/schema.py` | Implemented |
| Tests | `correctness/test_events.py`, `test_bench.py`, `test_metrics.py` | Pass on the A100 baseline commit |
| Baseline and five slowest parts | `results/baseline_v0.md`, `results/slowest5_v0.md` | Refreshed on `base.yaml` (commit `f1ed7f2`) |

## 2. Data interface

### 2.1 Run JSON (one per run, final summaries)

- Sections: `meta`, `config`, `clean`, `metrics`; `layer` / `trace` when those modes ran; `system` and `memory`
  on CUDA. Required fields: `perfkit/schema.py` `REQUIRED`. New fields may be added; renaming or removing one
  is agreed with G8 first.
- `clean.step_ms`, `clean.data_ms`: median, p10, p90, IQR, n. `clean.raw_step_ms`: every measured step.
- `system.metrics`: min / median / max / mean over the GPU samples, **for the benchmark's GPU only**
  (`system.gpu`), not a node aggregate.
- `metrics.mfu`, `metrics.hfu`: **fractions** (0.076 = 7.6%) for the one GPU of the benchmark process, against
  the dense peak for the run's dtype; not node-wide or whole-run values.
- `memory.peak_allocated_gb`, `memory.peak_reserved_gb`: the values are **GiB** (bytes / 2^30) despite the
  `_gb` names; `memory.unit` is `"GiB"`, `memory.gpu` names the device.
- `meta.run_id`, `meta.node_id`, `meta.events_jsonl` link the run JSON to its live JSONL.

### 2.2 Live JSONL `<tag>.jsonl` (one JSON object per line, append-only, readable during the run)

| Event | Fields G8 can rely on | Meaning |
|---|---|---|
| `gpu_sample` | `schema_version`, `event`, UTC `timestamp`, `run_id`, `node_id`, `gpu` (`name`, `index`, `uuid`, `pci_bus_id`), `step`, `metrics`, `slowdown_flags` | About one sample per second **per visible GPU on the node** during the clean steps; `step` may be missing |
| `step_timing` | `schema_version`, `event`, UTC `timestamp`, `run_id`, `node_id`, `rank`, `local_rank`, `step`, `data_ms`, `raw_step_ms` | One per clean step, written once its CUDA timing has resolved |

Example lines (from the A100 runs; IDs shortened):

```json
{"schema_version":1,"event":"gpu_sample","timestamp":"2026-10-30T20:07:38.614Z","run_id":"example-shared-run-id","node_id":"node-a","gpu":{"name":"NVIDIA A100-SXM4-40GB","index":0,"uuid":"GPU-example-uuid","pci_bus_id":"00000000:00:04.0"},"step":1,"metrics":{"gpu_util_pct":100.0,"mem_util_pct":82.0,"mem_used_mib":8142.0,"sm_clock_mhz":1410.0,"mem_clock_mhz":1215.0,"power_w":90.33,"temp_c":39.0},"slowdown_flags":[]}
{"schema_version":1,"event":"step_timing","timestamp":"2026-10-30T20:07:38.632Z","run_id":"example-shared-run-id","node_id":"node-a","rank":0,"local_rank":0,"step":1,"data_ms":0.7371,"raw_step_ms":49.3118}
```

### 2.3 Rules for reading the data

- **GPU identity:** use `gpu.uuid`. On Modal, `gpu.pci_bus_id` can be `"[Unknown Error]"`: treat it as missing,
  never as a shared identity. Node ID and local index are supporting context.
- **Join on keys, not times:** `timestamp` is when a record was written, and a `step_timing` record arrives after
  its GPU work finishes. Join on `run_id` / `node_id` / `rank` / `step`.
- **Samples are not steps:** `gpu_sample` intervals are approximate; a short run has only a few (5 in the
  100-step baseline run).
- **`data_ms` is host time:** `Loader.next_batch()` plus `Loader.prefetch()` after backward (prefetch is on by
  default on `g6/dev`). It is not the GPU's wait for data; the copy may still be in flight.
- **`raw_step_ms` adds no sync:** it reuses the step timer's CUDA event pair; a worker thread polls
  `Event.query()` and writes the record. No timing events are created inside measured steps.
- **Missing is not zero:** a `null` MFU / HFU is missing. Do not average MFU / HFU across GPUs or runs without
  an agreed rule.
- **Units:** `mem_used_mib` stays MiB; G8 converts to bytes. G8 owns the N-second rollups.

### 2.4 Dashboard rules

- Flag runs with `meta.dirty = true`, or leave them out of baselines.
- Flag runs with any `system.slowdown_samples`: such a run may miss the 5% check.
- Show the GPU name and the commit next to every number.
- Plot `trace.gpu_busy_pct` for real GPU utilization: `gpu_util_pct` only means "at least one kernel ran"
  (baseline: 100% from nvidia-smi, 50% busy in the trace).

## 3. MFU / HFU

```text
model_flops_per_token = 6 * N_active + 12 * L * d * T
MFU = tokens_per_s * model_flops_per_token / (peak_tflops * 1e12)
HFU = tokens_per_s * hw_flops_per_token    / (peak_tflops * 1e12)
```

- `N_active` from `GPT.param_counts()`: the matmul weights one token passes through (routed experts: only the
  selected ones; the MTP head when `model.mtp=true`). `hw_flops_per_token` adds the reversible stack's two extra
  forwards, the chunked head's recompute and the optimizer's Newton-Schulz work. Exact method: `METRICS.md`.
- **Worked example** (baseline, A100-SXM4-40GB, bf16 peak 312 TFLOPS, B=16, T=256): 247 MFLOP per token at 95,459
  tokens/s is 23.6 TFLOPS: MFU 7.6%, HFU 8.4%. MTP: 448 MFLOP per token, MFU 8.6%, HFU 9.1%.
- **G5:** G5's harness computes every expert before selecting the top-k, so G6's active-expert FLOPs do not
  describe it. G5 supplies its own executed-FLOPs estimate and agrees comparability with G8 before cross-team
  reporting; the same MFU / HFU formulas then apply.

When `mfu` or `hfu` is `null`, its reason field (`mfu_unavailable_reason`, `hfu_unavailable_reason`) is one of:

| Code | Applies to |
|---|---|
| `unknown_gpu` | MFU and HFU (example: RTX 5070 Ti, not in the peak table) |
| `unsupported_dtype` | MFU and HFU |
| `peak_tflops_unavailable` | MFU and HFU |
| `invalid_peak_tflops` | MFU and HFU |
| `hw_flops_unavailable` | HFU only |
| `participants_unavailable`, `participant_peak_unavailable`, `invalid_global_throughput`, `duplicate_participants` | MFU and HFU, `run` scope only (new, proposed) |

The reason is `null` when the metric is present.

**New, additive:** `metrics.mfu_method` (`g6-v1` today) and `metrics.mfu_scope` (`selected_gpu` from `bench`). A file
without them means `g6-v1` / `selected_gpu`, so the ingested baselines stay valid. `bench`'s values stay per GPU. The
proposed `g6-v2` method and the run-level formula, with `run` scope, are in `METRICS.md` sections 2.1 and 2.2.

## 4. Run identity and scope

- Each bench invocation generates its own `meta.run_id`. `--run-id <id>` sets a shared ID for coordinated runs;
  G5 must accept and write the **same** ID itself (G6 does not send it).
- `--repeat N` gives each run its own ID and refuses a shared `--run-id`: repeats are separate measurements.
- One collector covers one node and all its visible GPUs. For several nodes: one collector per node, the
  **same** run ID, **different** node IDs (`--node-id`), and separate tags or output folders.
- The `torchrun` path of bench is the isolated all-to-all measurement, not distributed-training monitoring.
- Evidence so far is single-GPU (A100); no multi-node end-to-end test is claimed. `perfkit/mfu_fixture.py` checks the
  run-level arithmetic across processes, but it is a fixture and not a trainer.

## 5. Evidence

| Evidence | Result | Meaning |
|---|---|---|
| Baseline, Colab A100-SXM4-40GB, commit `f1ed7f2` ([gist](https://gist.github.com/vaibh27/574990425455e4a9cb64822f14e3d85b)) | `pytest --all-configs`: 375 passed, 1 xfailed, 0 skipped. Normal and MTP pairs at 100 steps: PASS, 28 of 28 gated parts each; layer-recorder overhead 0.41% / 0.25%; 1 host sync per step | The baseline; run JSONs, JSONL and logs in the gist |
| RTX 5070 Ti (Linux), commit `190693a` (same code as `f1ed7f2`, docstrings only), four runs per mode ([runs](https://gist.github.com/jssunil/0f0e289c5dca5630214d1de1da109ba9), [tests](https://gist.github.com/jssunil/0be0592d4464997a3d216fdee59fe09e)) | All six normal and all six MTP pairs pass, checkpoint save included; step 59.6 ms normal, 104.4 ms MTP; MFU / HFU `null` with `unknown_gpu`; `--all-configs` 375 passed, 1 xfailed, 0 skipped | A second GPU and host agree |

Other runs:
- [Telemetry A/B, Modal A100-40GB](https://github.com/vaibh27/era-v5-lab/pull/30#issuecomment-6522615585)
- [RTX 5070 Ti, Windows](https://gist.github.com/jssunil/a8180d70598e5a62d7534d252b5cdc08)
- [Earlier A100 / H100 / 5070 Ti review](https://github.com/vaibh27/era-v5-lab/pull/29#issuecomment-6520549948)
- [H200, earlier `lab_small` configuration](https://github.com/theschoolofai/era-v5-lab/pull/135)
- Second Colab session, same commit: `results/baseline_v0.md`, Other machines

## 6. Status with G8

**Confirmed by G8 (chat, 28 Oct to 1 Nov):**

1. The `gpu_sample` and `step_timing` shapes and `schema_version: 1` work with G8's writer, alarms and loader.
2. `gpu.uuid` is the GPU identity; `"[Unknown Error]"` in `pci_bus_id` is treated as missing.
3. MFU / HFU are ingested as fractions, `null` = missing, with the five reason codes that existed then.
4. G8 owns the N-second rollups and the MiB-to-bytes conversion.
5. All 8 final baseline files load with no missing fields. The format stays the run JSON and JSONL.

**Proposed, waiting for G6 and G8 lead approval:**

| # | Decision | Proposal | G6 | G8 |
|---|---|---|---|---|
| 1 | KE2 in N | Projection out of `6 * N`, real lookup cost in; about 5% lower MFU (`METRICS.md` 2.1) | pending | pending |
| 2 | MTP | Head counted on T-1 positions (`METRICS.md` 2.1) | pending | pending |
| 3 | RoPE | The rotation is elementwise, so it is not counted (`METRICS.md` 2) | pending | pending |
| 4 | Scope | `mfu` stays per GPU; run level is a separate value, global tokens/s over the sum of peaks. G8's message calls `metrics.mfu` run-level; it is not (`METRICS.md` 2.2) | pending | pending |
| 5 | Combining | Never average percentages (`METRICS.md` 2.2) | pending | pending |
| 6 | New fields and codes | `mfu_method`, `mfu_scope`, `participants`, `global_tokens_per_s`, 4 reason codes | pending | pending |
| 7 | Above 1 | Stored, not clipped; `report` warns. G8 describes the range as `[0, 1]` | pending | pending |

Still to confirm: the shared `run_id` + one collector per node convention (pending G5 adopting `--run-id`).

Not done yet on the G6 side: time and token goodput, measured HBM bandwidth for the roofline, multi-GPU runs.
