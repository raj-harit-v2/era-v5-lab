# Profile — dry run 1

**Status:** stub — awaiting TSAI full-width (or small-width) job logs.  
**Owners:** torch.profiler → Varshith · Nsight → Shashank · Lead review → Raj  
**Rule:** every number cites **GPU name + git SHA**. No invented ms. Traces → gist / `~/.cache/era-perf/traces/` (not under `results/`).

| Field | Value |
| :--- | :--- |
| GPU | _awaiting_ |
| Commit | _awaiting_ |
| Config | _G5 v1 or base — pin when known_ |
| Job PR / tag | `dryrun1_prof` |
| `mfu_method` | `g6-v1` until CAP flips |

## Method

1. Class JOB: `python -m perfkit.bench --config <cfg> --modes clean,layer,trace --level 3 --tag dryrun1_prof --out out` (add `--synthetic` if needed).  
2. Open part traces in [Perfetto](https://ui.perfetto.dev) / Chrome tracing; gist `runs/<tag>_parts/` if needed.  
3. **Nsight:** record findings from TSAI-returned artifacts (link gist; do not commit large binaries here).

## Top ops (torch.profiler)

| rank | op / part | self ms | note |
| ---: | :--- | ---: | :--- |
| 1 | _awaiting_ | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

## Slowest parts (layer + part traces)

| part | ms | gist / Perfetto |
| :--- | ---: | :--- |
| _awaiting_ | | |

## Nsight notes

**Owner:** Shashank · **Source:** Colab capture of class [#492](https://github.com/theschoolofai/era-v5-lab/pull/492) (`dryrun1_nsys`). TSAI has no Nsight Systems, so Raj approved a Colab run (G6, 16–17 Nov). **Gist** (stats CSVs, `dryrun1_nsys.md`, `result.json`, run log, 0.87 MB `.nsys-rep`): <https://gist.github.com/shank343/84a47207c3e150ee0f5688568567a11e>. No binaries in git.

**Step time stays with the profiler § (#486).** This section only ranks kernels, NVTX regions and memcpy: shares and counts from a traced run, no ms.

| Field | Value |
| :--- | :--- |
| GPU | NVIDIA L4 (Colab), bf16 |
| Commit | `aec75af` (dirty) |
| Dirty paths | `teams/06-performance/jobs/run_dryrun1_nsys.py` only: added from `8ce4fb0` (#492), byte-identical to class `main` (blob `130e7f6c2293`). Nothing else under `teams/06-performance` and no config differs from the pin. |
| Model | same mapping as #486: `config_v1.yaml` @ `aec75af` → `configs/base.yaml`, small width (d=256, 6 layers), MoE 16 routed + 1 shared, top-2, `dispatch=sorted`, Muon, `ke2`, eager attention, synthetic data, B=16, T=256 |
| Capture | nsys 2025.3.1, `--trace=cuda,nvtx`, 5 untraced warmup + 3 traced steps; perfkit regions as NVTX ranges (level 3) |

### Top GPU kernels (share of GPU kernel time, L4)

| rank | kernel group | share | calls / step |
| ---: | :--- | ---: | ---: |
| 1 | loss log-softmax, forward + backward (`cunn_SoftMaxForward/Backward`, fp32 over the 131,072 vocab) | 26.7% | 2 |
| 2 | dtype-cast / copy kernels (`bfloat16_copy_kernel`, `direct_copy_kernel`) | 22.1% | ~1,080 |
| 3 | all GEMMs (cuBLAS + CUTLASS, bf16) | 19.4% | — |
| 4 | optimizer and grad-clip elementwise (momentum lerp, fused AdamW, norms, scale) | 5.4% | — |
| 5 | fills / zeroing (`FillFunctor`) | 3.9% | 36 |
| 6 | GELU forward + backward | 3.3% | — |
| 7 | expert-weight stacking (`CatArrayBatchedCopy`) | 2.9% | 77 |
| 8 | softmax in eager attention and the router | 2.5% | — |

Kernel launches: about 3,699 per step across 120 kernel types.

### NVTX regions (host-side time in each region, share of a traced step)

| region | share |
| :--- | ---: |
| `bwd` | 72.1% |
| `bwd.invert:block5.moe.dispatch` | 39.6% |
| `fwd` | 13.5% |
| `opt` | 11.9% |
| `opt:opt.muon` (Newton-Schulz `opt.muon.ns` 3.1%) | 9.0% |
| `fwd:block0.moe.dispatch` | 4.3% |
| every other `moe.dispatch` (16 more calls) | ~0.6% each |

NVTX time is CPU time inside a range, not GPU time. The two large `moe.dispatch` ranges are where the host waits for the GPU queue (next section), not dispatch work.

### Memcpy and CUDA API

- **Memcpy:** device-to-device is 89.6% of copy time (66 copies / step, about 750 MB / step); host↔device copies are negligible. All copies together are about 1% of GPU kernel time.
- **Host syncs:** 18 `cudaStreamSynchronize` per step, 76.4% of CUDA API time. 18 = 6 blocks × 3 passes (forward, reversible invert, recompute): `dispatch_sorted` reads `int(counts.max())` on the host, one sync per call (`models/moe.py`).
- **Launches:** `cudaLaunchKernel` is 16.4% of CUDA API time.

### How this lines up with the profiler § (#486)

- **Same model:** about 3,699 kernel launches and 18 stream syncs per step here (plus one device sync per traced run), against 3,693 kernels and 19 host syncs per step in #486.
- **Different bound:** on the L4, kernels fill about 80% of a traced step, so the full-vocab loss leads the ranking. TSAI's GPU was busy 31.1% of the step and starved in 20 of 20 steps (#486), so there the same ~3.7k launches and 18–19 syncs dominate, and the profiler's part shares include host time.
- **Naming:** under `dispatch=sorted`, the `moe.dispatch.grouped` parts in #486 are the sorted path's batched-expert GEMMs, not `dispatch=grouped`.

### Top findings (candidates for Dry Run 2; not measured fixes)

1. **Host syncs and launches** set the step on TSAI's GPU. `dispatch=grouped` already removes the per-call sync (fixed capacity, `models/moe.py`); CUDA graphs or `torch.compile` would cut launches. Re-profile after either.
2. **Full-vocab loss in fp32** is the largest GPU cost (26.7% on the L4). Candidate: the fused / chunked linear-CE paths (`model.ce_impl`, tip #77 / #78).
3. **Cast and stack copies** (22.1% + 2.9%) are likely `_batched_experts` re-stacking and casting every expert's weights on every call (18 calls / step). Candidate: build the stacked bf16 weights once per step. To confirm in the `.nsys-rep` timeline.

## Repeat / trust

If dual run: gated parts within **≤5%**. Warm then measure.
