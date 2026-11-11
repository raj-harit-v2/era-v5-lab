# Task 8, Part 3: Dense MLP (`blockN.mlp`)

**Author:** @narasimhatejav

## Task
Rotation task (G6, Task 8): profile one part of the training step. This report covers **Part 3, Dense MLP
(`blockN.mlp`)**. It reports:
- the three slowest operations in the part, with GPU time, number of calls and number of kernels
- whether each one is compute-bound, memory-bound or launch-bound, and one idea to speed it up
- the trace file, the GPU name and the commit ID

## Raw outputs
Full JSON/JSONL logs, parts and head-loss traces: https://gist.github.com/narasimhatejav/6edc31929c89a2ca036837083bfb2189

## Setup
| | |
|---|---|
| **Author** | @narasimhatejav |
| **GPU** | Tesla T4 (1 of 2 on Kaggle), fp16 autocast (T4 has no native bf16) |
| **Commit** | `a2c6656604d4a0cdbb848c6abc32658e8298a1bf` (g6/dev) |
| **Shape** | B x T = 8 x 256, n_embd 256, MLP 256 → 1024 → 256, GELU, 6 layers |
| **torch** | 2.11.0+cu130 |
| **Full trace** | `~/.cache/era-perf/traces/g6_mlp_t4.json` (11 MB, not committed) |
| **Run JSON / report** | `results/runs/03-dense-mlp/g6_mlp_t4.json`, `g6_mlp_t4.md` |
| **Ops JSON** | `results/runs/03-dense-mlp/g6_mlp_t4_mlp_ops.json` |

## Commands
```bash
cd teams/06-performance
CUDA_VISIBLE_DEVICES=0 python -m perfkit.bench --config configs/base.yaml \
    --modes clean,layer,trace --level 3 --tag g6_mlp_t4 run.batch_size=8
python -m perfkit.part_ops fwd:block3.mlp --run results/runs/g6_mlp_t4.json --top 3 \
    --json results/runs/g6_mlp_t4_mlp_ops.json
```
No extra flag is needed: `model.ffn: mlp` is the default in `configs/base.yaml`.

## Where the MLP sits in the step
- Step (clean): median 125.3 ms, 16,339 tokens/s, MFU 6.2%.
- `fwd:blockN.mlp`: 0.166 ms per block, the same in all 6 blocks (0.1% of the step each).
- The stack is reversible, so the MLP forward runs three times per block per step: forward (0.166 ms),
  `bwd.invert` (0.157 ms) and `bwd.recompute` (0.157 ms). That is about 2.9 ms per step (about 2.3%),
  plus its gradient inside `bwd:blockN.grad`.
- Profiled region `fwd:block3.mlp` (middle layer): 8 kernels, 0.156 ms of GPU time, GPU busy 96% of its span.

## Three slowest operations (`fwd:block3.mlp`)

| # | Operation | GPU ms | Calls | Kernels | Bound | Idea to speed it up |
|---|---|---:|---:|---:|---|---|
| 1 | `aten::linear` (c_fc 256→1024 and c_proj 1024→256) | 0.119 (76%) | 2 | 7 | **Compute** (fp16 tensor-core GEMMs) | `torch.compile` / larger token batch per launch so the GEMM tiles fill the GPU |
| 2 | `aten::gelu` | 0.037 (24%) | 1 | 1 | **Memory** (≈ 227 GB/s, 71% of 320 GB/s) | fuse GELU into the c_fc GEMM epilogue (`torch.compile`, or cuBLASLt bias+GELU) |
| 3 | fp16 cast copy inside `linear` (`float16_copy_kernel`, autocast fp32 → fp16 weights) | 0.028 | (inside #1) | (inside #1) | **Memory / launch** (small copies) | cast the weights once per step instead of on each of the 3 MLP runs, or keep a half-precision copy |

`part_ops` finds only two operations in the MLP (`aten::linear` for both matmuls, and `aten::gelu`). The
third-largest cost is the weight-cast copy inside `linear`, so it is listed separately.

Kernel breakdown of `aten::linear` (0.119 ms):

| Kernel | GPU ms | Bound |
|---|---:|---|
| `turing_fp16_s1688gemm_fp16_128x128_ldg8_relu_f2f_stages_32x1_tn` | 0.051 | Compute (~21 TFLOPS of 65) |
| `turing_fp16_s1688gemm_fp16_128x128_ldg8_relu_f2f_tn` | 0.039 | Compute (~27 TFLOPS of 65) |
| `float16_copy_kernel` (weight casts) | 0.028 | Memory / launch |

## Why each is bound that way
- **GEMMs, compute-bound:** each matmul is 2 × 2048 × 256 × 1024 = 1.07 GFLOP at about 195 FLOP/byte, close to the
  T4 ridge point (65 TFLOPS / 320 GB/s ≈ 203). They reach about 21–27 TFLOPS, roughly 1/3 of peak. At M = 2048 tokens
  the problem is too small to fill the GPU.
- **GELU, memory-bound:** one elementwise pass over the 2048 × 1024 fp16 activation (≈ 8.4 MB read + write) in
  0.037 ms ≈ 227 GB/s, about 71% of the T4's 320 GB/s.
- **Casts, memory/launch-bound:** small copies of the 256 × 1024 weights; short kernels whose cost is mostly
  launch and memory traffic, not math.
- **Launch pressure overall:** under the profiler, `linear`'s CPU time (0.283 ms) is more than its GPU time
  (0.119 ms). CPU time is an upper bound because the profiler slows the CPU. At this size the MLP is close to
  launch-bound, which CUDA graphs or `run.compile=true` would help.


