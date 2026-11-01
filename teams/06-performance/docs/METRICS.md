# METRICS: how G6 measures throughput, MFU and the GPU (for G8)

The code is the source of truth: `perfkit/metrics.py` computes the numbers, bench writes them into the run JSON,
and report and G8 read the same fields (`perfkit/schema.py`, `REQUIRED["metrics"]`). To change a number or a
constant, change `metrics.py` first, then this file.

## 1. FLOPs per token

`T` = sequence length, `L` = layers, `d` = width, `N_active` = active parameters (`GPT.param_counts`).

```text
model_flops_per_token = 6 * N_active + 12 * L * d * T
                        (PaLM formula; attention scores counted non-causal)

hw_flops_per_token    = model_flops_per_token
                      + 2 extra forwards of the stack when reversible (invert + recompute)
                      + 2 * head again when ce_impl=chunked (it recomputes the head)
                      + optimizer FLOPs per step (Muon Newton-Schulz) / tokens per step
```

- `head` = the LM head's parameters, plus the MTP head's when `model.mtp=true`. With MTP on, `N_active` also
  includes the MTP head, so the model FLOPs grow with it (normal 247 MFLOP per token, MTP 448).
- One forward of the stack (`stack_fwd`) = `2 * (N_active - head - KE projection) + 4 * L * d * T` per token: the
  head and the KE projection are not part of the stack, so the reversible term does not count them again.
- The FFN part of `N_active` is every matrix the FFN multiplies with: `2 * d * h` for `model.activation=gelu`
  (`c_fc`, `c_proj`) and `3 * d * h` for `swiglu` (`c_gate`, `c_fc`, `c_proj`), with `h` the FFN width. An MoE
  layer counts the router plus `top_k + num_shared` experts. So at the same `h` a SwiGLU FFN has 1.5x the FFN FLOPs
  of a GELU one. The elementwise `SiLU(gate) * up` (like GELU) is not counted, as in PaLM.
- The optimizer FLOPs come from `Optimizers.flops()` in `models/optim.py`.
- Code: `flops_per_token()` in `perfkit/metrics.py`.

**Open point for G8 (MFU method, week 2):** `6 * N_active` counts the KE2 projection (256 x 8192 = 2.1M
parameters) as a dense matmul, but KE2 runs as an `embedding_bag` over a few columns per token. That adds about
12.6 of the 247 MFLOP per token, so MFU reads about 5% high. The PaLM formula usually leaves embeddings out of N.
To be agreed with G8 before it changes.

## 2. MFU and HFU

```text
model_tflops_per_s = tokens_per_s * model_flops_per_token / 1e12
MFU                = model_tflops_per_s / peak_tflops
HFU                = tokens_per_s * hw_flops_per_token / 1e12 / peak_tflops
```

- **MFU** counts the model's FLOPs; **HFU** counts what the hardware actually computes (MFU plus the extra work above).
- Both divide by the **dense** vendor peak for the dtype the run used (`metrics.peak_tflops`).
- `metrics.mfu` and `metrics.hfu` are **per GPU**: the tokens/s and the peak are for the one GPU the benchmark process uses. They are not
  node-wide or whole-run totals; G8 can combine per-GPU values from separate processes where that makes sense.

**Worked example** (`results/baseline_v0.md`: A100-SXM4-40GB, bf16 peak 312 TFLOPS, B=16, T=256):
40.37M active parameters give 6 * 40.37M + 12 * 6 * 256 * 256 = 247 MFLOP per token. At 95,459 tokens/s that
is 23.6 TFLOPS, so MFU = 7.6%. `hw_flops_per_token` is 276 MFLOP, so HFU = 8.4%. With `model.mtp=true`
(74.0M parameters): 448 / 477 MFLOP per token, 59,691 tokens/s, MFU 8.6%, HFU 9.1%.

### Fields in `run["metrics"]`

`mfu`, `hfu`, `model_tflops_per_s`, `model_flops_per_token`, `hw_flops_per_token`, `params_total`,
`params_active`, `peak_tflops`, and one reason field per metric: `mfu_unavailable_reason`, `hfu_unavailable_reason`.

### When MFU or HFU is missing

A metric is `null` when it cannot be computed, and its reason field says why. When the metric is present, its
reason is `null`.

| Reason | Meaning | Affects |
|---|---|---|
| `unknown_gpu` | the GPU is not in the peak table (`PEAKS`) | MFU and HFU |
| `unsupported_dtype` | the GPU is known but has no peak for the run's dtype | MFU and HFU |
| `peak_tflops_unavailable` | no usable vendor peak was found | MFU and HFU |
| `invalid_peak_tflops` | a peak set by hand is not positive | MFU and HFU |
| `hw_flops_unavailable` | hardware FLOPs are missing | HFU only (MFU stays) |

**For readers (G8):** a `null` MFU or HFU means missing, not zero. Do not average MFU / HFU fractions across GPUs
or runs without an agreed rule.

**G5's harness** computes every expert before it picks the top-k, so G6's active-expert FLOPs do not apply to
it. G5 supplies its own executed-FLOPs estimate and agrees comparability with G8 before cross-team reporting; the
same MFU / HFU formulas can then be reused with those FLOPs.

## 3. The peak table (`PEAKS` in `metrics.py`)

`gpu_peak(device_name)` and `peak_tflops(device_name, dtype)` match the GPU name against a substring table
(B200, H200 NVL, H200, H100, A100, RTX 3060, L40S, ...). The first match wins, so specific names come first
(for example `H200 NVL` before `H200`).

- **Known GPU and dtype:** `peak_tflops` is set, and MFU / HFU are computed.
- **No peak** (an empty entry, today `H100 NVL` and `A10G`; a dtype with no entry, such as bf16 on V100 / T4 /
  P100, where bench falls back to fp16 anyway; or an unknown GPU): MFU stays empty and bench adds a warning. Set
  the peak with `--peak-tflops` on the bench command line (or `bench.peak_tflops`). Example: the RTX 5070 Ti is
  not in the table, so its runs record `mfu: null` with `mfu_unavailable_reason: "unknown_gpu"`.
- **Notes on values:** H200 NVL and H200 SXM have separate peaks. RTX 3060 bf16 / fp16 uses the dense value,
  half of NVIDIA's 101 TFLOPS figure, which includes 2:4 sparsity. No FP8 or FP4 peaks are defined yet; those
  lookups return `None` until authoritative dense values are added.

## 4. Tokens per second

`tokens_per_s` = `tokens_per_step` (batch x sequence) / the clean median step time. Report and G8 must use the
value stored in the run JSON, not recompute their own.

## 5. Peak memory

- `memory.peak_allocated_gb` and `memory.peak_reserved_gb` are for the CUDA device this benchmark process used.
- The `_gb` fields are in **GiB** (bytes / 2^30); `memory.unit` is `"GiB"` so readers need not guess.
- `memory.gpu` identifies the device: name, local CUDA index, UUID and PCI bus ID.

## 6. Run identity: `run_id` and `node_id`

- Every bench invocation gets its own generated `meta.run_id`. Leave `--run-id` unset for independent runs.
- **To link G5 and G6 measurements of the same experiment,** pass the same `--run-id <id>` to both, and have
  the G5 harness write it into its records. G6 does not choose or send an ID to another harness.
- `--repeat N` gives each run its own ID and refuses a shared `--run-id`: the runs are separate measurements.
- `--node-id` sets the node name (default: `G8_NODE_ID`, else the hostname).

**Multi-node:** one bench process per node covers that node and all its visible GPUs. On each node, start bench
with the same run ID, its own node ID, and its own tag (or a node-local output folder), for example:

```bash
python -m perfkit.bench --run-id exp-42 --node-id node-a --tag exp-42-node-a ...   # node-b on the other node
```

This only collects measurements; it does not launch or coordinate distributed training. The `torchrun` path in
bench is only for the isolated all-to-all measurement (`--modes comm`).

## 7. Dirty commit

- `meta.dirty` is `true` when anything under `teams/06-performance` (outside `results/`) differs from
  `meta.commit`, new files included.
- A dirty run does not belong to a named commit: do not treat it as a baseline until the tree is clean.
  `perfkit.report.compare` refuses a pair unless both runs are `dirty: false` on the same commit.
- `dirty` is `null` when git status cannot run. With no `.git` at all, `meta.commit` comes from the
  `PERF_COMMIT` environment variable (or `null`).

## 8. System metrics (`run["system"]`, CUDA runs only)

**What is sampled.** `perfkit.metrics.GpuSampler` runs one `nvidia-smi --loop-ms=1000` child process during the
clean steps (the steps that give step time, tokens/s and MFU). It samples every GPU visible on the node.

- `run["system"]` (in the run JSON): `system.metrics` holds min / median / max / mean of each metric, **for the
  benchmark's GPU only** (`system.gpu` names it).
- `<tag>.jsonl` (the live sidecar): every sample of **every visible GPU**, written as it arrives.

| Key | nvidia-smi field | Meaning |
|---|---|---|
| `gpu_util_pct` | `utilization.gpu` | % of the sample period in which at least one kernel ran. Not SM occupancy: one tiny kernel at a time reads 100%. Use `trace.gpu_busy_pct` for idle gaps between kernels. |
| `mem_util_pct` | `utilization.memory` | % of the sample period in which device memory was read or written |
| `mem_used_mib` | `memory.used` | device memory in use by all processes, in MiB (the allocator's own peak is `memory.peak_allocated_gb`) |
| `sm_clock_mhz`, `mem_clock_mhz` | `clocks.sm`, `clocks.mem` | clocks; compare with `meta.telemetry_start["clocks.max.sm"]` |
| `power_w`, `temp_c` | `power.draw`, `temperature.gpu` | board power and GPU temperature |

**Slowdowns.** `slowdown_samples` / `slowdown_reasons` count samples where the driver reported a slowdown
(`SLOWDOWN` in `metrics.py`): `SwPowerCap`, `HwSlowdown`, `SwThermalSlowdown`, `HwThermalSlowdown`,
`HwPowerBrakeSlowdown`. `GpuIdle`, application clocks, sync boost and display clocks are not slowdowns (a GPU
sampled between steps reports `GpuIdle`). Any slowdown adds a run warning: such a run may miss the 5% check.

**One-off readings.** Besides the sampler, `meta.telemetry_start` and `meta.telemetry` (`after_warmup`,
`during_steps`, `end`) hold single `nvidia-smi` readings (`gpu_telemetry`); `during_steps` is taken while three
untimed steps run. From these, bench warns at 83 C or above, when the driver reports a slowdown, or (when it
reports no reasons) when the SM clock is below 85% of `clocks.max.sm`.

Off CUDA, or without `nvidia-smi`, there is no `system` section.

## 9. The live JSONL sidecar (`<tag>.jsonl`)

One JSON object per line, append-only, readable while the run goes. Two kinds of event. Writing it never
synchronizes CUDA: a separate thread reads the `nvidia-smi` output and the step events, and flushes each record.
`meta.run_id`, `meta.node_id` and `meta.events_jsonl` in the run JSON point to the sidecar.

**Reading it (G8):**
- **Identify a GPU by `gpu.uuid`.** On some hosts (Modal) `gpu.pci_bus_id` is `"[Unknown Error]"`: treat that as
  missing, not as a shared identity. Node ID and local index are supporting context.
- **Join on keys, not times.** `timestamp` is when the record was written; a `step_timing` record arrives after
  its GPU work finishes. Join on `run_id` / `node_id` / `rank` / `step`.
- **Samples are not steps.** `gpu_sample` comes about once a second per visible GPU; a short run has only a
  handful (5 in the 100-step baseline run). Do not map one sample to one step.
- **G8 owns** the N-second rollups, the MiB-to-bytes conversion, dashboards and alarms.

**`gpu_sample`** (one per GPU per sample):

| Field | Meaning |
|---|---|
| `schema_version`, `event` | record format version; `"gpu_sample"` |
| `timestamp` | UTC |
| `run_id`, `node_id` | as in section 6 |
| `gpu` | `name`, local `index`, `uuid`, `pci_bus_id` |
| `step` | the current clean step, when there is one |
| `metrics` | raw values (`mem_used_mib` stays in MiB for G8 to convert) |
| `slowdown_flags` | the driver's slowdown reasons for this sample |

**`step_timing`** (one per clean step):

| Field | Meaning |
|---|---|
| `schema_version`, `event` | record format version; `"step_timing"` |
| `run_id`, `node_id`, `timestamp` | as above (UTC) |
| `rank`, `local_rank` | 0 for a standalone process; from `RANK` / `LOCAL_RANK` under `torchrun` |
| `step` | one-based clean step |
| `raw_step_ms` | the step time; matches `clean.raw_step_ms` to four decimal places |
| `data_ms` | host wall time in `Loader.next_batch()`, plus `Loader.prefetch()` after backward when `data.prefetch` is on (the default) |

`data_ms` is **host** time: on CUDA the non-blocking copy to the GPU may still be in flight when the call
returns. It is not the GPU `data` region (`layer.regions["data"]`), which times the copy on the GPU (0.03 ms
against `data_ms` 0.6 ms in `results/baseline_v0.md`).

**How step timing stays off the measured path.** It reuses the step timer's existing CUDA event pair. A
background worker polls `Event.query()`, reads the elapsed time only after the GPU work has finished, and writes
the record. No `cuda.synchronize()` and no extra event pair are added to the step; disk writes and event reads
stay off the training thread. Records therefore arrive with a short delay. The `clean.raw_step_ms` and
`clean.data_ms` summaries in the run JSON are unchanged.

## 10. Goodput (partial)

`run["goodput"]["badput_s"]` holds the wall-clock seconds of `startup` (model, loader and optimizer built),
`first_step` (includes `torch.compile` / autotune when on) and `warmup`. Time goodput and token goodput are not
written yet.

## 11. Tests

| Test file | Checks |
|---|---|
| `correctness/test_metrics.py` | FLOPs-per-token formulas, MFU / HFU conversion, peak lookups for known and unknown GPUs and dtypes (bf16, fp16, fp32, fp8, fp4 for every listed test GPU) |
| `correctness/test_optimizer.py` | the Newton-Schulz FLOP count, including that AdamW-only parameters add nothing |
| `correctness/test_report.py` | the 5% gate and the Markdown output |

```bash
python -m pytest correctness/test_metrics.py correctness/test_optimizer.py correctness/test_report.py -q
```

The loop-versus-batched Muon bf16 comparison in `test_optimizer.py` needs CUDA with native bf16. Its bound
(`rtol=0.04, atol=0.02`) passes on the baseline A100 (commit `f1ed7f2`), but the observed error is not recorded
yet, so the bound is not yet measured.

## 12. Changing the run JSON

`perfkit.schema.REQUIRED` lists every field report and G8 expect under `meta`, `config`, `clean` and `metrics`
(plus `layer` / `trace` when those modes ran, `system` on CUDA). New fields can be added freely; renaming or
removing a required field breaks report, metrics and G8, so agree it first.
