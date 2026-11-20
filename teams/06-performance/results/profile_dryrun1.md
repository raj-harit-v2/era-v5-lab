# Profile — dry run 1

**Status:** done for B=8: torch.profiler + layer profile (repeat 2, PASS) and Nsight Systems, both on the dry run 1 model.  
**Sources:** G6 runs on one Modal A100 (20 Nov 2026) and the lab's dry run 1 evidence (class #620). Nothing else.  
**Rule:** every number cites **GPU name + git SHA**. Member-GPU runs give shares and counts only; step time comes from the lab run. Traces → [gist](https://gist.github.com/vaibh27/e4e60f177d4fe675ba0444054928d341) (not under `results/`).  
**TSAI lab column:** to be filled from the lab's dry run 1 profile when it is shared; #620 has no profile, so those cells are _pending_.

| Field | Value |
| :--- | :--- |
| GPU | NVIDIA A100-SXM4-80GB (Modal, one GPU per run), bf16 |
| Commit | `7b2ee0e3` + the `configs/g5_t2_base.yaml` change in this PR (`muon_impl: loop`, `data.source: synthetic`, `bench.modes: [clean, layer, trace]`) |
| Config | `configs/g5_t2_base.yaml` (dry run 1 model, class #475) |
| Software | torch 2.11.0+cu130, CUDA 13.0, cuDNN 91900, Triton 3.6.0, Python 3.12, Nsight Systems 2025.3.2. The lab run used torch 2.14.1+cu130 (#620 manifest). |
| Runner | `benchmarking/modal_dryrun1.py` (perfkit), `benchmarking/modal_dryrun1_nsys.py` (Nsight) |
| `mfu_method` | `g6-v1` until CAP flips |
| Traces / raw outputs | <https://gist.github.com/vaibh27/e4e60f177d4fe675ba0444054928d341>: full torch.profiler traces (`profile_*_trace.json.gz`), five part traces per run (`profile_*_part_*.json`), `nsys_dryrun1_nsys_b8.nsys-rep`, `nsys stats` CSVs, run JSONs and logs |

| Run | What | Result |
| :--- | :--- | :--- |
| `repeatbatch8` | perfkit `clean,layer,trace`, level 3, B=8, `--repeat 2` | PASS, 30 of 30 gated parts within 5% |
| `b8` | same, B=8, one run, another container | used for the cross-container check only |
| `nsys-b8` | Nsight Systems, B=8, 5 untraced warmup + 3 traced steps | exit 0, all five `nsys stats` reports |

## Model

Same as the dry run 1 manifest (class #620): 8 layers, d=512, 8 query / 2 KV heads, T=2048, V=131,072, RMSNorm, RoPE 10000, SwiGLU, `ke2` embedding, untied head, MoE 16 routed + 1 shared, top-2, expert width 768, `dispatch=loop`, not reversible, eager attention, torch CE, Muon (`muon_impl: loop`, muon_lr 0.01, lr 1e-3), bf16, seed 1234, synthetic data.

- Parameters: 237,062,784 total, 104,923,136 active. The lab manifest has 237,052,416: the 10,368 extra are biases that perfkit's model has and the lab's has not (attention qkv 768 + attention proj 512 + router 16, per layer × 8). Every weight matrix matches the lab's Muon / AdamW split. Effect on the profile: negligible (the bias add runs inside the same GEMM).
- Shape: B=8, T=2048 in one pass with one optimizer step per step (the lab's optimizer cadence). The lab split the same batch into 8 accumulated micro-steps; perfkit has no gradient accumulation, so the GEMMs here are larger than the lab's.

## Method

1. perfkit: `python -m perfkit.bench --config configs/g5_t2_base.yaml --modes clean,layer,trace --level 3 data.source=synthetic run.batch_size=8 --repeat 2`. 10 warmup + 100 measured steps per mode. Trace mode: torch.profiler over 3 steps after 1 warmup, plus one step in sync-debug mode for host syncs. `--repeat 2` runs the benchmark again in a new process and checks every gated part against the first run (5% rule).
2. Nsight: `jobs/run_dryrun1_nsys.py --config configs/g5_t2_base.yaml --synthetic run.batch_size=8` under `nsys profile --trace=cuda,nvtx --capture-range=cudaProfilerApi`: 5 untraced warmup steps, then 3 traced steps; every perfkit region is an NVTX range (level 3). Then `nsys stats`: `cuda_gpu_kern_sum`, `nvtx_sum`, `cuda_gpu_mem_time_sum`, `cuda_gpu_mem_size_sum`, `cuda_api_sum`.
3. Part traces open in [Perfetto](https://ui.perfetto.dev); the `.nsys-rep` opens in Nsight Systems.

## Lab reference (class #620)

Dry run 1 full run, RTX 3090, steps 11–1221 (`teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl`): median step 1,897.6 ms (p10 1,772.3, p90 2,054.6, max 2,420.6), step 1 4,430 ms, 8,634 tokens/s, peak allocated 3.56 GB, sum of steps 2,335 s of 2,481 s wall. No torch.profiler or Nsight traces came back with it, so every share below is from the member GPU. The step times are not compared: different GPU, and B=8 in one pass is not 8 accumulated micro-steps.

## Routing state (read before the tables)

The two tools saw different routing, because the router collapses on synthetic data:

| | G6 perfkit runs (torch.profiler + layer pass) | G6 Nsight | TSAI lab |
| :--- | :--- | :--- | :--- |
| measured after | about 200 training steps (10 warmup + 100 clean steps + the layer pass) | 5 warmup steps | _pending_ |
| expert slots with tokens (8 layers × 16 experts = 128) | 18 per step (`aten::nonzero` / `index_add_` calls in the trace) | 128 per step | _pending_ |
| Muon Newton-Schulz calls per step | 102 | 432 | _pending_ |
| host syncs per step | 147 (128 `tok.any()` + 18 `nonzero` + 1) | 256 (2 per slot) | _pending_ |
| kernels per step | 7,949 | about 30,300 | _pending_ |

- Why: synthetic data has nothing to learn (loss stays at about 11.9), `bias_gamma=0` adds no load balancing, so a few experts take every token. The loop dispatch skips experts with no tokens, and Muon skips weights with no gradient.
- Effect: the perfkit shares (MoE dispatch 6%, Muon 12.5% of the layer pass, and the step breakdown) **understate the MoE and Muon cost** of a run with tokens spread over the experts. The Nsight section is the closer view of balanced routing.
- The lab run used real data; #620 has no per-expert counts, so its routing state is not known.

## torch.profiler and layer profile (B=8)

### Step breakdown (share of the clean step; run 1, run 2 in brackets)

| part | G6 (Modal A100) | TSAI lab |
| :--- | ---: | ---: |
| `fwd` | 35.6% (35.7%) | _pending_ |
| `fwd:stack` (8 blocks) | 24.4% (24.5%) | _pending_ |
| `fwd:head+loss` | 10.5% (10.6%) | _pending_ |
| `bwd` | 45.7% (46.0%) | _pending_ |
| `bwd:stack` (8 blocks) | 32.8% (32.9%) | _pending_ |
| `bwd:head+loss` | 12.4% (12.5%) | _pending_ |
| `opt` | 18.4% (18.0%) | _pending_ |
| `opt:opt.muon` | 17.7% (17.4%) | _pending_ |

Inside the blocks (layer pass, summed over the 8 layers; information only, not gated):

| region | G6 (Modal A100) | TSAI lab |
| :--- | ---: | ---: |
| `fwd:block*.attn.sdpa` (eager attention: masked softmax in fp32) | 14.5% (14.5%) | _pending_ |
| `opt:opt.muon.ns` (Newton-Schulz, loop path) | 12.7% (12.5%) | _pending_ |
| `fwd:block*.moe.dispatch` (of which the 16 expert calls 5.4%) | 6.0% (6.1%) | _pending_ |
| `fwd:block*.attn.qkv` | 1.1% | _pending_ |
| `fwd:block*.moe.shared` | 1.0% | _pending_ |
| `fwd:embed.ke` | 0.7% | _pending_ |
| `fwd:block*.moe.router` | 0.3% | _pending_ |

### Top ops (share of GPU kernel time)

| rank | kernel | G6 share | G6 calls / step | TSAI lab share | TSAI lab calls / step | note |
| ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| 1 | `direct_copy_kernel` (elementwise copy) | 11.5% | 321 | _pending_ | _pending_ | dtype / layout copies |
| 2 | `bfloat16_copy_kernel` | 7.9% | 336 | _pending_ | _pending_ | fp32 → bf16 casts |
| 3 | `masked_fill_kernel` | 6.3% | 16 | _pending_ | _pending_ | causal mask in eager attention (8 layers, fwd + bwd) |
| 4 | `cunn_SoftMaxBackward` (log-softmax) | 6.3% | 1 | _pending_ | _pending_ | full-vocab loss, fp32 |
| 5 | `cunn_SoftMaxForward` (log-softmax) | 6.2% | 1 | _pending_ | _pending_ | full-vocab loss, fp32 |
| 6 | fp32 `MulFunctor` | 5.3% | 110 | _pending_ | _pending_ | |
| 7 | `cunn_SoftMaxBackwardSmem` | 4.5% | 8 | _pending_ | _pending_ | attention softmax backward |
| 8 | Memcpy DtoD | 3.3% | 33 | _pending_ | _pending_ | |
| 9 | `softmax_warp_forward` (fp32) | 3.2% | 8 | _pending_ | _pending_ | attention softmax forward |
| 10 | bf16 GEMMs (top four, `ampere_bf16_s16816gemm_*`) | 10.3% | 19 | _pending_ | _pending_ | |

| metric | G6 (Modal A100) | TSAI lab |
| :--- | ---: | ---: |
| GPU busy, share of the traced step | 74.8% (76.9%) | _pending_ |
| kernels per step (torch.profiler) | 7,949 | _pending_ |
| host syncs per step (sync-debug mode) | 147 | _pending_ |
| kernel launches per step (Nsight) | about 30,100 | _pending_ |
| host syncs per step (Nsight `cudaStreamSynchronize`) | 256 | _pending_ |

- Host syncs (sync-debug mode): 147 per step, at `models/moe.py:79` (128, `if not tok.any()`) and `models/moe.py:81` (18, `nonzero`, one per expert slot with tokens): the loop dispatch. Nsight counts 256 with every expert active (see Routing state).

### Slowest parts (layer + part traces)

| rank | part | G6 share of step | TSAI lab share of step | part trace |
| ---: | :--- | ---: | ---: | :--- |
| 1 | `bwd:block*` | 20.2% (20.7%) | _pending_ | `1_bwd_block4.json` |
| 2 | `fwd:block*.attn.sdpa` | 8.9% (9.1%) | _pending_ | `2_fwd_block4.attn.sdpa.json` |
| 3 | `opt:opt.muon.ns` | 7.8% (7.8%) | _pending_ | `3_opt_opt.muon.ns.json` |
| 4 | `bwd:head+loss` | 7.6% (7.9%) | _pending_ | `4_bwd_head+loss.json` |
| 5 | `fwd:block*.moe.dispatch` | 3.7% (3.8%) | _pending_ | `5_fwd_block4.moe.dispatch.json` |

## Nsight Systems (B=8)

Shares and counts from the 3 traced steps. Tracing adds overhead on every launch, so these rank kernels and regions; they do not give step time.

### GPU kernels by group (share of GPU kernel time)

GPU kernel time is 66% of the traced wall time (rough GPU-busy share; torch.profiler, without Nsight's launch overhead, gives 75–77%). 134 kernel types, about 30,300 launches per step.

| group | G6 share | G6 launches / step | TSAI lab share | TSAI lab launches / step |
| :--- | ---: | ---: | ---: | ---: |
| GEMMs (cuBLAS, bf16) | 28.4% | ~7,830 | _pending_ | _pending_ |
| other elementwise (mul, add, scalar ops) | 26.6% | ~16,150 | _pending_ | _pending_ |
| copy / cast (`direct_copy`, `bfloat16_copy`) | 17.0% | ~2,710 | _pending_ | _pending_ |
| log-softmax fwd + bwd (loss, fp32) | 9.8% | 2 | _pending_ | _pending_ |
| softmax (attention, router) | 6.0% | 32 | _pending_ | _pending_ |
| `masked_fill` (attention mask) | 4.9% | 16 | _pending_ | _pending_ |
| reductions / norms | 2.6% | ~1,250 | _pending_ | _pending_ |
| index / gather / scatter | 1.8% | ~1,060 | _pending_ | _pending_ |
| fills | 1.7% | ~290 | _pending_ | _pending_ |
| cub sort / select (`nonzero`, sort) | 1.1% | ~1,010 | _pending_ | _pending_ |

Top single kernels: `direct_copy` 9.9% (1,311 calls), `bfloat16_copy` 6.6% (1,326), log-softmax backward 4.9% (1), `masked_fill` 4.9% (16), log-softmax forward 4.8% (1), fp32 mul 4.2% (220), bf16 scalar mul 3.7% (6,480 calls), the 64×64 bf16 GEMM 3.7% (2,218 calls).

### NVTX regions (host time inside each region, share of a traced step)

| region | G6 share | G6 calls / step | TSAI lab share | TSAI lab calls / step |
| :--- | ---: | ---: | ---: | ---: |
| `opt` | 43.7% | 1 | _pending_ | _pending_ |
| `opt:opt.muon` | 42.8% | 1 | _pending_ | _pending_ |
| `opt:opt.muon.ns` | 38.3% | 432 | _pending_ | _pending_ |
| `bwd` | 34.2% | 1 | _pending_ | _pending_ |
| `fwd` | 21.6% | 1 | _pending_ | _pending_ |
| `fwd:block*.moe.dispatch` (8 blocks) | 19.1% | 8 | _pending_ | _pending_ |

- NVTX time is CPU time, not GPU time. On the host, Muon's loop path is the largest region: 432 Newton-Schulz calls per step, each a chain of small kernels.
- In every block, `moe.dispatch.expert0` holds about half of the dispatch range: the first `tok.any()` waits for the queued GPU work.

### Memcpy and CUDA API

- **Launches:** `cudaLaunchKernel` about 30,100 calls per step, 73.2% of CUDA API time.
- **Host syncs:** `cudaStreamSynchronize` 256 per step, 21.7% of CUDA API time; matched by 256 device-to-host copies per step. 256 = 8 layers × 16 experts × 2 (`tok.any()` and `nonzero` in `dispatch_loop`, `models/moe.py:79`, `:81`).
- **Copies:** device-to-device is 86.0% of copy time (33 per step); memset 9.7% (about 790 per step); host↔device negligible.

### How this lines up with the torch.profiler section

- Same ranking at the top: copy / cast kernels, the fp32 full-vocab log-softmax, and eager attention's mask + softmax lead both.
- Launch counts (7,949 against about 30,300 per step) and syncs (147 against 256) differ because of the routing state: 18 of 128 expert slots active in the perfkit runs, all 128 in Nsight (see Routing state). The extra Nsight launches are the experts' GEMMs and Muon's Newton-Schulz kernels for the experts that the collapsed router left idle.

## Findings (candidates for Dry Run 2; not measured fixes)

1. **Full-vocab loss in fp32** (`head+loss` 23% of the step; log-softmax 9.8% of kernel time in Nsight). Candidate: the fused / Triton CE paths (`model.ce_impl`).
2. **Eager attention** (14.5% of the layer pass; mask + softmax 10.9% of kernel time in Nsight). Candidate: `model.attn_impl=sdpa`.
3. **Muon loop path** (12.5% of the layer pass; 38% of host time and about half of all launches in Nsight; widest spread of any part). Candidate: `optim.muon_impl=batched`.
4. **Cast and copy kernels** (17–19% of kernel time, about 2,700 launches per step). Likely per-call weight casts and per-expert gathers; to confirm in the part traces.
5. **Loop MoE dispatch** (256 host syncs per step; 6% of the layer pass). Candidate: `model.moe.dispatch=grouped` (fixed capacity, no host sync).

## Repeat / trust

- **B=8 repeat: PASS.** Two runs in separate processes on one A100-SXM4-80GB: all 30 gated parts within 5% (0 by the 0.05 ms rule); step 2.6% apart, every block 0.4% or less, `opt` 2.4%.
- **Across containers:** the single `b8` run (another Modal container) had an 11% slower median step; its `opt` share was 21.8% against 18.4%, `fwd` 34.4% and `bwd` 43.6% (against 35.6% and 45.7%). The extra time is in Muon, the host-bound part, so compare shares within one container.
- GPU power cap: 16 of 64 and 21 of 62 telemetry samples showed SwPowerCap during the clean steps (shared cloud GPU).
- Spread: 19 gated parts have p10..p90 spread over 10% (mostly the early forward blocks and Muon), yet the medians repeat within 5%.
- Host time: the GPU ran out of queued work in 100 of 100 layer-pass steps despite a 500 ms queue fill, so part shares include host time.
- Code state: the container has no `.git`; the commit comes from the runner (HEAD + `provenance/diff.patch`). The Nsight job's own summary prints a stale config pin (`@ aec75af`); the config that ran is `configs/g5_t2_base.yaml` above.

## Gaps

- A perfkit profile with balanced routing (forced balanced routing, or a capture after a few warmup steps), so the perfkit shares match a real run's expert load.
