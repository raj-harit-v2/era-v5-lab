# B5 Performance Validation Report
# Team 06 — Performance and Kernels, ERA V5

**Date:** 2026-11-11
**Prepared by:** Team 06 (Performance)
**Status:** INVESTIGATION COMPLETE — correctness validated; performance improvement not demonstrated

---

## 1. Executive Summary

The B5 data-loading primitives in `dataio/loader.py` — conditional pinned host-memory allocation,
non-blocking H2D transfer, and prefetch scheduling — have been validated through correctness tests
and CUDA performance benchmarks on a Colab CUDA runner.

**Correctness:** Five loader correctness tests are present. Four are CPU-executable and passed
locally; the CUDA-specific pinned-memory test (Test A) was skipped locally because CUDA was
unavailable. All five tests were subsequently validated on a Colab CUDA runner (Python 3.13.16, torch
2.14.1+cu130): 5 passed in 0.74s. Pinned-memory H2D transfers were independently confirmed by CUDA profiler trace
(`Memcpy HtoD (Pinned -> Device)`) in both benchmark configurations.

**Performance:** Six clean-mode A/B benchmark runs comparing prefetch=false versus prefetch=true
showed a 0.23% aggregate step-latency difference — too small to confirm a reliable improvement or
regression given run-to-run spread. CUDA profiler traces show shorter CPU data-region windows with prefetch ON (0.299 ms versus
0.475 ms). This is consistent with host-side work being moved outside the data region by prefetch
scheduling. However, these are single-step observations, and queue starvation prevents us from
establishing a reliable CPU/GPU overlap benefit. Power-cap slowdown was reported in every clean run,
and FP16 + GradScaler introduces a host synchronization per step in the optimizer path — all of
which further limit the reliability of the measurements.

**Conclusion:** The existing B5 implementation is verified correct. The prefetch scheduling
mechanism is confirmed operational. A reliable throughput improvement was not demonstrated under
the current measurement conditions. These results are exploratory; they are not Gate 1 baseline
evidence.

---

## 2. Scope and Implementation Context

### B5 primitives in `dataio/loader.py`

B5 covers three primitives that reduce data-loading latency on CUDA hardware:

1. **Pinned host memory** (`buf.pin_memory()`, loader.py:83–84): eliminates the runtime's internal
   staging buffer on the H2D DMA path; guarded by `self.pin = device.type == "cuda"` (loader.py:37).
2. **Non-blocking H2D transfer** (`buf.to(self.device, non_blocking=True)`, loader.py:69): avoids a
   CPU synchronization stall at data submission, allowing the CPU to proceed to enqueue forward
   kernels immediately.
3. **Prefetch scheduling** (`loader.prefetch()`, bench.py:221–224): separates host batch preparation
   (`_host_batch()`) from H2D submission; `_host_batch()` is called after `loss.backward()` queues
   backward kernels, overlapping CPU batch preparation with GPU backward execution.

### Historical attribution

Primitives 1 and 2 (pinned memory and non-blocking H2D transfer) were present in the initial loader
implementation from the first commit on `g6/dev` (Oct 25 2026, commit `df2b9e098e`). Primitive 3
(prefetch scheduling) was introduced in a later commit (Oct 30 2026, commit `0968eb8f11`). The
contribution on branch `g6/b5-loader-correctness` adds correctness tests for these existing
primitives; it does not introduce new production loader functionality.

No genuine pre-B5 baseline without pinned-memory or non-blocking H2D exists in the repository
history. The A/B experiment in this report (prefetch=false vs prefetch=true) measures the benefit
of prefetch scheduling only. It does not measure the original introduction of the pinned-memory
and non-blocking H2D primitives.

### Repository state (snapshot at time of report preparation)

*This table records the working-tree state at the time this report was prepared, before the
contribution files were staged for commit.*

| Item | Value |
|---|---|
| Repository | `https://github.com/vaibh27/era-v5-lab` |
| Branch | `g6/b5-loader-correctness` |
| HEAD SHA | `41b7fb031cbc49f0ac7e20287ca3f88193540923` |
| Working tree | DIRTY — untracked files only (no tracked modifications) |
| Untracked: correctness contribution | `teams/06-performance/correctness/test_loader.py` |
| Untracked: this report | `teams/06-performance/b5_performance_validation_report.md` |
| Untracked: ZIP archives (repo root) | `era_v5_team06.zip`, `era_v5_team06_colab.zip`, `era_v5_team06_with_ke2.zip` |
| Untracked: generated cache | `__pycache__/` under `correctness/`, `dataio/`, `models/`, `perfkit/` |
| Production files modified | None |

No tracked files were modified. The untracked files are: the B5 correctness contribution
(`test_loader.py`), this report, three ZIP archives created for Colab delivery, and Python
`__pycache__/` directories generated during local test runs. None of these are production source
files.

---

## 3. Correctness Tests and Results

### Test file

`teams/06-performance/correctness/test_loader.py` (staged, not yet committed)

### Tests

| Test | Property verified | CUDA required |
|---|---|---|
| `test_host_batch_is_pinned_on_cuda` (Test A) | `_host_batch()` returns a pinned CPU tensor when device=CUDA | Yes (`@pytest.mark.skipif`) |
| `test_next_batch_uses_non_blocking_transfer` (Test B) | `next_batch()` passes `non_blocking=True` for the `[B, T+1]` host-batch `.to()` call | No |
| `test_cpu_loader_does_not_pin_memory` (Test C) | CPU Loader never invokes `pin_memory()` | No |
| `test_repeated_prefetch_does_not_overwrite_staged_batch` (Test D) | Calling `prefetch()` twice is idempotent: `_host_batch()` called exactly once; staged batch identical to single-prefetch reference; RNG not advanced by the no-op second call | No |
| `test_fineweb_prefetch_on_off_batch_equivalence` (Test E) | FineWeb loader with prefetch ON yields identical batches to prefetch OFF over 4 steps; verifies `uint32→int64` cast preservation, shard-slicing path, and correct shifted-token relationship | No |

### Local validation (CPU-only environment)

| Item | Value |
|---|---|
| Python | 3.12.10 |
| PyTorch | 2.12.1+cpu |
| CUDA available | No |
| Command | `python -m pytest correctness/test_loader.py -v` |
| Result | 4 passed, 1 skipped (Test A skipped: CUDA unavailable) |

Full correctness suite (all tests in `correctness/`):

```
399 passed, 8 skipped, 283 deselected, 1 xfailed, 1 warning in 329.52s
27 pairs: 27 PASS, 0 FAIL
```

Includes `data.prefetch` (rel_err = 0.00e+00, PASS) and `data.prefetch.first` (rel_err = 0.00e+00
exact, PASS).

### Prior Colab validation (three-test suite)

| Item | Value |
|---|---|
| GPU | Colab CUDA runner |
| Python | 3.13.16 |
| PyTorch | 2.14.1+cu130 |
| CUDA | 13.0 |
| Native BF16 | Unavailable on the tested CUDA runner; FP16 used |

CUDA correctness wrapper (`pytest correctness/test_loader.py`): **exit code 0**.
Prefetch correctness wrapper (`pytest correctness/test_optimizer.py -k "data.prefetch"`): **exit
code 0**.

Detailed individual pytest counts were not captured in the supplied Colab output. Exit code 0
indicates all collected tests passed (or were legitimately skipped) without assertion failures or
import errors. The individual PASS/SKIP split for the three loader tests on the CUDA runner is not
recorded in the available evidence.

Additionally, the CUDA profiler traces (Section 7) confirm that H2D transfers in both benchmark
configurations used the `Memcpy HtoD (Pinned -> Device)` copy type, which is independent physical
evidence that `pin_memory()` was active during the benchmark runs.

### Latest Colab validation — five-test suite

| Item | Value |
|---|---|
| Platform | Linux |
| Python | 3.13.16 |
| pytest | 8.4.2 |
| PyTorch | 2.14.1+cu130 |
| CUDA available | Yes |
| GPU | Colab CUDA runner |
| Command | `python -m pytest correctness/test_loader.py -v --tb=short` |
| Result | **5 passed in 0.74s** |

| Test | Result |
|---|---|
| `test_host_batch_is_pinned_on_cuda` (Test A) | PASSED |
| `test_next_batch_uses_non_blocking_transfer` (Test B) | PASSED |
| `test_cpu_loader_does_not_pin_memory` (Test C) | PASSED |
| `test_repeated_prefetch_does_not_overwrite_staged_batch` (Test D) | PASSED |
| `test_fineweb_prefetch_on_off_batch_equivalence` (Test E) | PASSED |

---

## 4. CUDA Environment and Benchmark Configuration

### CUDA runner

| Item | Value |
|---|---|
| GPU | Colab CUDA runner |
| Python | 3.13.16 |
| PyTorch | 2.14.1+cu130 |
| CUDA | 13.0 |
| Effective dtype | FP16 (native BF16 unavailable on this CUDA GPU; fallback by `choose_dtype()`) |
| Optimizer scaler | GradScaler active (FP16 path) |
| Delivery | Repository ZIP upload (branch not pushed; `commit: null` in run metadata) |

### A/B benchmark configuration (six clean-mode runs)

| Parameter | Value |
|---|---|
| Config file | `configs/base.yaml` |
| Modes | `clean` |
| Batch size (B) | 8 |
| Sequence length (T) | 256 |
| Data source | Synthetic |
| Warmup steps | 10 |
| Measured steps | 100 |
| Varied parameter | `data.prefetch` (false vs true) |

`base.yaml` line 61 (`bench.steps: 100`) already specifies 100 measured steps; no override was
needed.

### Layer and trace configuration (two runs)

| Parameter | Value |
|---|---|
| Config file | `configs/base.yaml` |
| Modes | `clean,layer,trace` |
| Level | 3 |
| Batch size (B) | 8 |
| Sequence length (T) | 256 |
| Data source | Synthetic |
| Warmup steps | 5 |
| Measured steps | 30 |
| Varied parameter | `data.prefetch` (false vs true) |

---

## 5. Six-Run Clean A/B Results

### Per-run medians

| Run | Prefetch OFF step_ms | Prefetch ON step_ms |
|---|---:|---:|
| R1 | 123.864 ms | 124.395 ms |
| R2 | 124.110 ms | 124.677 ms |
| R3 | 124.856 ms | 123.888 ms |

### Aggregate (median of three run medians)

Tokens per step: B × T = 8 × 256 = 2,048.

| Metric | Prefetch OFF | Prefetch ON | Delta |
|---|---:|---:|---:|
| Step median | 124.110 ms | 124.395 ms | +0.285 ms (+0.23%) |
| Throughput | 16,501 tok/s | 16,464 tok/s | −37 tok/s (−0.22%) |
| Host-side data_ms | 0.393 ms | 0.385 ms | −0.008 ms (−2.1%) |

### Interpretation

Prefetch ON was 0.23% slower in aggregate step latency and 0.22% lower in throughput. Host-side
data time was 2.1% lower with prefetch ON. All three deltas are smaller than the run-to-run
variation (individual run step medians span 123.864–124.856 ms). No reliable improvement or
regression can be established from these measurements.

### Run-level caveats

- All six runs reported `SwPowerCap` slowdown in bench telemetry.
- FP16 + GradScaler introduces a host synchronization reading `found_inf` during optimizer
  execution; this appears in both configurations as approximately 2 host syncs per step (confirmed
  by trace, Section 7).
- Run metadata reported `commit: null` because the Colab environment was a ZIP upload without a
  Git checkout.
- These are exploratory measurements, not formal Gate 1 baseline evidence.

---

## 6. Layer Timing Findings

### Summary

Both layer runs used `clean,layer,trace` mode at level 3 with 30 measured steps. Layer
instrumentation reported **GPU queue starvation in all 30 recorded steps for both configurations**.
Layer timing therefore includes host-side overhead and cannot be treated as clean isolated
GPU-kernel timing.

### Prefetch ON (`b5-prefetch-on-layer-trace`)

| Region | Median |
|---|---:|
| Step (clean) | 123.93 ms |
| Data | 0.483 ms |
| Forward | 35.957 ms |
| Backward | 58.571 ms |
| Optimizer | 28.634 ms |
| GPU busy (trace) | 86.8% |
| Kernels per step | 1,212 |
| Host syncs per step | 2 |
| Recorder overhead | 0.10% |

### Prefetch OFF (`b5-prefetch-off-layer-trace`)

| Region | Median |
|---|---:|
| Step (clean) | 123.17 ms |
| Data | 0.363 ms |
| Forward | 35.958 ms |
| Backward | 58.557 ms |
| Optimizer | 28.313 ms |
| GPU busy (trace) | 98.2% |
| Kernels per step | 1,214 |
| Host syncs per step | 2 |
| Recorder overhead | 0.10% |

### Layer comparison

Forward and backward region medians are nearly identical between configurations (≤0.014 ms
difference). The data region is 0.120 ms longer with prefetch ON (0.483 ms vs 0.363 ms). Because GPU queue
starvation was reported in all 30 recorded steps for both configurations, these timings include
host-side overhead and cannot be interpreted as isolated GPU timings.

The lower GPU busy percentage under prefetch ON (86.8% vs 98.2%) is not expected if prefetch
scheduling is keeping the GPU more occupied; this may reflect the power-cap throttling or other
transient conditions on the shared Colab instance. Both configurations show 2 host synchronizations
per step, consistent with GradScaler `found_inf` reads.

---

## 7. CUDA Profiler Trace Findings

Trace files:
- Prefetch ON:  `/root/.cache/era-perf/traces/b5-prefetch-on-layer-trace.json`
- Prefetch OFF: `/root/.cache/era-perf/traces/b5-prefetch-off-layer-trace.json`

### Data-region measurements

| Metric | Prefetch ON | Prefetch OFF |
|---|---:|---:|
| CPU data-region window | 0.299 ms | 0.475 ms |
| GPU data-region time (CUDA event interval) | 0.010 ms | 0.010 ms |
| H2D copy duration | 0.0055 ms | 0.0054 ms |
| H2D copy type | Pinned → Device | Pinned → Device |
| Contiguous kernels | 0.0049 ms | 0.0051 ms |
| H2D copies in data region | 1 | 1 |
| Data-region GPU busy | 72% | 71% |

The 0.010 ms GPU data-region CUDA event interval is the sum of the H2D copy (≈0.0055 ms) and two
contiguous kernels (≈0.0049 ms). It is **not** comparable to the 0.299/0.475 ms CPU data-region
window, which is a host-side wall-clock measurement.

### Key findings

**Pinned transfers confirmed.** Both traces record `Memcpy HtoD (Pinned -> Device)` as the H2D copy
type, confirming that `pin_memory()` was active during both benchmark configurations. This is
independent physical evidence that `self.pin = True` activated on the CUDA runner and that
`_host_batch()` returned a pinned buffer before the transfer.

**H2D duration observed (single-step measurement).** The profiler recorded H2D copy durations of
0.0054–0.0055 ms (approximately 5.4 μs) from one profiled step per configuration. At B=8, T=256,
int64 (8×257×8 = 16,448 bytes ≈ 16 KB), this is consistent with PCIe H2D latency for small pinned
buffers. These are single-step observations and do not establish a statistically robust DMA latency;
H2D transfer cost at other batch sizes or under different memory pressure is not established by
this measurement.

**H2D duration is consistent across configurations.** The 0.0001 ms difference between ON and OFF
is within single-step measurement noise.

**CPU data-region window difference.** The CPU window is 0.176 ms shorter with prefetch ON
(0.299 ms vs 0.475 ms), reflecting that `_host_batch()` CPU work has been moved out of the `data`
region by prefetch scheduling. This observation comes from one profiled step per configuration and
is not statistically robust.

**No independent-stream DMA/compute overlap.** The existing implementation uses the default CUDA
stream; `non_blocking=True` eliminates the CPU stall on H2D enqueue but does not enable GPU-side
overlap of H2D DMA with forward/backward kernels on the same stream. The profiler timings are
consistent with strict FIFO stream ordering.

**`data:prefetch` CUDA event interval ≈ 0.** In CUDA mode, the `data:prefetch` EventRecorder region
has no GPU operations between its start and end events; the GPU event interval is approximately zero
and does not measure `_host_batch()` CPU execution time. `clean.data_ms` (host wall-clock
accumulator) is the correct measure of total host-side data overhead per step.

---

## 8. Prefetch ON/OFF Comparison Summary

| Measurement | Prefetch ON | Prefetch OFF | Observation |
|---|---:|---:|---|
| Aggregate step_ms (100 steps × 3 runs) | 124.395 ms | 124.110 ms | ON 0.23% slower — within noise |
| Aggregate throughput | 16,464 tok/s | 16,501 tok/s | ON 0.22% lower — within noise |
| Host-side data_ms | 0.385 ms | 0.393 ms | 2.1% lower with ON — within noise |
| Layer data region (30 steps) | 0.483 ms | 0.363 ms | 0.12 ms longer with ON (starvation present) |
| CPU data-region window (trace, 1 step) | 0.299 ms | 0.475 ms | 0.176 ms shorter with ON |
| H2D duration (trace, 1 step) | 0.0055 ms | 0.0054 ms | Identical within single-step measurement precision; no meaningful ON/OFF difference observed |
| H2D type | Pinned → Device | Pinned → Device | Pinned memory confirmed in both |
| GPU busy (trace) | 86.8% | 98.2% | Lower with ON — power cap confounds interpretation |
| Host syncs per step | 2 | 2 | Same; GradScaler `found_inf` read in both |
| Power-cap slowdown | Yes (all runs) | Yes (all runs) | Both configurations affected |

### What the ON/OFF comparison measures

The A/B experiment compares prefetch scheduling only: whether `_host_batch()` is called before or
after `next_batch()` in the training step. Both configurations exercise pinned memory and
non-blocking H2D transfer. The comparison does not measure the value of the original pinned-memory
and non-blocking H2D primitives.

---

## 9. Limitations and Outstanding Validation

| # | Limitation | Impact |
|---|---|---|
| 1 | No committed Git identity in Colab run metadata (`commit: null`) | Benchmark results cannot be formally traced to a specific commit in the audit trail |
| 2 | Checkpoint mode was not measured; bench reported Rule 3b warning | Checkpoint performance regression cannot be ruled out |
| 3 | GPU power-cap slowdown (`SwPowerCap`) in every clean run | Absolute step times are elevated; throttling may suppress any prefetch benefit |
| 4 | GPU queue starvation in 30/30 recorded steps for both layer runs | Layer region times include host overhead; cannot be treated as isolated GPU kernel timing |
| 5 | FP16 + GradScaler causes a host synchronization reading `found_inf` per step | Adds ≈1 host sync to optimizer execution; present in both configurations; eliminated only with native bf16 hardware |
| 6 | All benchmark data used synthetic input only | No FineWeb production-data throughput comparison was conducted |
| 7 | H2D profiler timing from one profiled step per configuration | Single-step observations are not statistically robust DMA benchmarks |
| 8 | Earlier Colab run covered only the three-test version | Resolved: latest five-test suite validated on a Colab CUDA runner (Python 3.13.16, torch 2.14.1+cu130); 5 passed in 0.74s — all five tests including Test A (CUDA pinned memory) |

### Remaining unverified items

| Claim | Status |
|---|---|
| Prefetch improves GPU training throughput | NOT DEMONSTRATED under current conditions |
| CPU batch preparation is hidden behind GPU backward execution | CONSISTENT with trace (0.299 ms CPU window vs 58.6 ms bwd), but not formally confirmed due to starvation and power-cap |
| FineWeb production-data throughput impact | NOT MEASURED — shards absent from runner |
| Improvement on hardware without power-cap throttling and with native BF16 support | NOT MEASURED |
| Improvement with native bf16 (eliminates GradScaler host sync) | NOT MEASURED |

---

## 10. Final Engineering Conclusion

**B5 Performance Validation: INVESTIGATION COMPLETE — correctness validated; performance improvement
not demonstrated**

### Correctness

- Five loader correctness tests are present (Tests A–E).
- Local CPU execution (torch 2.12.1+cpu): 4 passed, 1 skipped — Test A skipped (CUDA
  unavailable); Tests B, C, D, and E passed.
- Latest Colab CUDA execution (Python 3.13.16, torch 2.14.1+cu130): all five
  tests passed — 5 passed in 0.74s, including Test A (CUDA pinned memory).
- A prior Colab run (three-test suite) confirmed exit code 0 for the CUDA and prefetch
  correctness wrappers; individual counts were not captured in that run.
- CUDA profiler traces independently confirmed `Memcpy HtoD (Pinned -> Device)` H2D transfers in
  both benchmark configurations, corroborating that `pin_memory()` was active.
- The full correctness suite (399 passed, 8 skipped, 27/27 pairs) was validated on the local CPU
  environment.

### Performance

- Six clean-mode A/B runs on the Colab CUDA runner showed a 0.23% step-latency difference — within run-to-run
  noise. No reliable throughput improvement was demonstrated.
- CUDA profiler traces are consistent with `_host_batch()` CPU work (≈0.3 ms) being effectively
  hidden behind GPU backward execution (≈58.6 ms) when prefetch is ON, but power-cap slowdown and
  queue starvation in all measured steps prevent this from being treated as a confirmed benefit.
- The implementation is validated correct. The performance result is inconclusive under the current
  Colab conditions.
- These measurements are exploratory. They are not Gate 1 baseline evidence.

### Recommended next steps

1. Commit both contribution files to branch (requires explicit authorization):
   - `teams/06-performance/correctness/test_loader.py`
   - `teams/06-performance/b5_performance_validation_report.md`
2. Re-run the A/B benchmark on hardware without power-cap throttling and with native BF16 support
   to eliminate the GradScaler host synchronization.
3. Run the FineWeb production-data comparison (`data.source=fineweb10b`) to assess real-world
   throughput impact.

---

## Appendix A: Commands for Reproduction on a CUDA Runner

```bash
# From teams/06-performance/

# Correctness
python -m pytest correctness/test_loader.py -v --tb=short
python -m pytest correctness/test_optimizer.py -k "data.prefetch or data.prefetch.first" -v

# Six clean-mode A/B runs
python -m perfkit.bench --config configs/base.yaml --tag b5_gpu_prefoff_run1 data.source=synthetic data.prefetch=false
python -m perfkit.bench --config configs/base.yaml --tag b5_gpu_prefon_run1  data.source=synthetic data.prefetch=true
python -m perfkit.bench --config configs/base.yaml --tag b5_gpu_prefoff_run2 data.source=synthetic data.prefetch=false
python -m perfkit.bench --config configs/base.yaml --tag b5_gpu_prefon_run2  data.source=synthetic data.prefetch=true
python -m perfkit.bench --config configs/base.yaml --tag b5_gpu_prefoff_run3 data.source=synthetic data.prefetch=false
python -m perfkit.bench --config configs/base.yaml --tag b5_gpu_prefon_run3  data.source=synthetic data.prefetch=true

# Layer + trace (prefetch ON and OFF)
python -m perfkit.bench --config configs/base.yaml --modes clean,layer,trace --level 3 \
    --tag b5-prefetch-on-layer-trace  data.source=synthetic data.prefetch=true
python -m perfkit.bench --config configs/base.yaml --modes clean,layer,trace --level 3 \
    --tag b5-prefetch-off-layer-trace data.source=synthetic data.prefetch=false

# FineWeb comparison (requires shards)
# python -m dataio.prepare_fineweb
# python -m perfkit.bench --config configs/base.yaml --modes clean,layer --level 3 \
#     --tag b5_gpu_fineweb data.source=fineweb10b data.prefetch=true
```

---

## Appendix B: Local CPU Smoke Test (Infrastructure Verification)

Executed locally (torch 2.12.1+cpu, CUDA unavailable) to confirm that the benchmark infrastructure
runs correctly before obtaining CUDA hardware.

Config: `configs/tiny_cpu.yaml` (device=cpu, fp32, B=2, T=64, n_layer=2, n_embd=64, warmup=2,
steps=10), 3 runs each configuration, `data.source=synthetic`.

| Run tag | step_ms (median) | data_ms (median) | data region | data:prefetch region |
|---|---:|---:|---:|---:|
| b5_cpu_prefoff_run1 | 118.36 ms | 0.4452 ms | 0.2476 ms | — |
| b5_cpu_prefoff_run2 | 121.17 ms | 0.3978 ms | 0.3407 ms | — |
| b5_cpu_prefoff_run3 | 104.15 ms | 0.3919 ms | 0.3455 ms | — |
| b5_cpu_prefon_run1  | 107.92 ms | 0.4612 ms | 0.1447 ms | 0.2714 ms |
| b5_cpu_prefon_run2  | 153.07 ms | 0.6663 ms | 0.1437 ms | 0.2894 ms |
| b5_cpu_prefon_run3  | 119.13 ms | 0.5053 ms | 0.1339 ms | 0.2679 ms |

CPU results are not meaningful for evaluating B5's CUDA primitives: `pin_memory()` is disabled on
CPU (`self.pin = False`), `non_blocking=True` has no effect on CPU-to-CPU transfers, and no
GPU/CPU overlap exists. The `data:prefetch` CPU region (0.27–0.29 ms) measures actual `_host_batch()`
CPU execution time using `time.perf_counter()` (EventRecorder uses wall-clock on CPU), which is
informative about the work being staged but not about CUDA performance.

Run artifacts: `~/.cache/era-perf/runs-smoke/` (outside repository).

---

*Report updated: 2026-11-11. All benchmark outputs are outside the repository at `~/.cache/era-perf/`.
No production files, tests, or benchmark configurations were modified.*
