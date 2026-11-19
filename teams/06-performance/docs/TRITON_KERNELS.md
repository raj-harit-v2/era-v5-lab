# Triton kernels: RMSNorm, SwiGLU, RoPE, attention, MoE router, CE epilogue

Each kernel is a switch, off by default; the torch code stays the reference. Where a kernel cannot run (no CUDA,
no Triton, an unsupported shape or dtype), the torch path runs instead, so the CPU tests and laptops are unchanged.
Status: written and CPU-tested only (fallbacks bit for bit). The CUDA tests and timings below are pending on A100.

| Switch | Kernel | Replaces | Notes |
|---|---|---|---|
| `model.norm: layernorm \| rmsnorm`, `model.norm_eps` | `models/norm.py` (torch) | `nn.LayerNorm` | G5's RMSNorm: weight only, fp32 math, output in the input dtype. A model change, not an A/B: G5 decides. |
| `model.ln_impl: triton_ln` with `norm: rmsnorm` | `kernels/rms_norm.py` | the G5 formula (about 6 kernels forward) | 1 kernel forward, 2 backward. LN2's input `p + a` is added in the same kernel (rounded as torch's add). Deterministic weight gradient (partial sums, no atomics). |
| `model.swiglu_impl: triton` | `kernels/swiglu.py` | `F.silu(g) * u` | 1 kernel each way, 2 saved tensors instead of 3. Dense MLP, routed experts (every dispatch) and shared experts. |
| `model.rope_impl: triton` | `kernels/rope.py` | `apply_rope` (3 kernels each way) | Reads the strided q, k view of the qkv output, no copy. |
| `model.attn_impl: triton` | `kernels/attention.py` | eager (T x T matrix, `repeat_interleave` copies) | Causal GQA flash attention. Backward: a dq pass, then a dk / dv pass over the query heads of each kv head; no atomics, so repeats are bitwise (the reason base.yaml uses eager, not SDPA). Output in `[B, T, H, hd]`, so the copy before `c_proj` is free. Falls back to eager. |
| `model.ce_impl: fused_triton` | `kernels/linear_ce_cublas.py` | `ce_impl=fused` elementwise passes; `triton_ce`'s own matmul tiles | The head matmuls on cuBLAS (logits, dx, dW: 3 per step, gradients cached in forward), and one Triton kernel per token chunk for log-sum-exp, loss and the softmax gradient, written over the bf16 logits. `ce_chunks` token chunks. A100 base run (`0b1d800`): `triton_ce` was 32.5 of 50.7 ms, about 11% of bf16 peak. Falls back to `ce_impl=fused`. |
| `model.moe.router_impl: triton` | `kernels/router.py` | softmax, bias add, top-k, gather, normalise | 1 kernel each way. Forced routing (reversible replay) uses torch. Ties: lowest expert index. |

The report treats `attn_impl`, `rope_impl`, `swiglu_impl` and `moe.router_impl` as implementation switches
(`perfkit/report.py` `IMPL_SWITCHES`): two runs that differ only in these are compared as an A/B. `norm` is a
model change and is not one of them.

## Correctness

```bash
cd teams/06-performance
python -m pytest correctness/test_triton_kernels.py -q          # CPU: config, fallbacks; CUDA: every kernel
python -m pytest correctness/test_ce_cublas.py -q               # ce_impl=fused_triton
python -m pytest correctness -q --all-configs                   # everything, on the GPU
```

On CUDA, `test_triton_kernels.py` checks each kernel against its torch reference (fp32 and bf16, uneven shapes,
strided inputs, GQA and MQA head counts), the bitwise repeat of the RMSNorm and attention backward, the MoE layer
with the router switch, the whole model with every switch on against the torch model (plain and reversible, MLP and
MoE, LayerNorm and RMSNorm, with and without bf16 autocast), and one run under `torch.compile`.

## Timing

Same GPU, commit and config for each pair; one switch per pair:

```bash
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag attn_eager  data.source=synthetic model.attn_impl=eager
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag attn_triton data.source=synthetic model.attn_impl=triton
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag rms_torch   data.source=synthetic model.norm=rmsnorm
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag rms_triton  data.source=synthetic model.norm=rmsnorm model.ln_impl=triton_ln
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag rope_torch  data.source=synthetic model.position=rope model.rope_theta=10000
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag rope_triton data.source=synthetic model.position=rope model.rope_theta=10000 model.rope_impl=triton
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag swiglu_torch  data.source=synthetic model.activation=swiglu
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag swiglu_triton data.source=synthetic model.activation=swiglu model.swiglu_impl=triton
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag router_torch  data.source=synthetic model.ffn=moe
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag router_triton data.source=synthetic model.ffn=moe model.moe.router_impl=triton
```

Compare `clean.raw_step_ms`, the part's `fwd:` and `bwd:` rows, peak memory and tokens/s. Each switch must pass
the 5% repeat check on its own before it becomes a default.

The attention kernels cast their products with `scale` to fp32: under `torch.compile`, Inductor passes the Python
float as fp64 and Triton refused the loop (`test_full_model_triton_switches_under_compile` on A100, `0b1d800`).

The speed-up notebook (CE A/B over every `ce_impl`, the kernel A/Bs, `run.compile`, a batch sweep) is kept
outside the repo with the other Colab checks.

## Not done here

- Grouped GEMM for the experts (the `sorted` / `grouped` dispatches cover part of it).
- Symmetric `X X^T` matmul in Muon's Newton-Schulz: the matrices are small, the optimizer is launch-bound.
- G5's attention sink and output gate: model changes; the attention kernel can take them once G5 adopts them.
- Tile tuning (no autotuning yet): block sizes are fixed per dtype and head dim; `triton_ce` keeps its 16x128x32
  tiles.
- CUDA graphs for the optimizer step (Polar Muon + AdamW, about 4.8 ms, launch-bound).
