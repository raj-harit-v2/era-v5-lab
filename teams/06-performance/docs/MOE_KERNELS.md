# Standalone MoE permutation kernels

`kernels/moe_dispatch.py` provides compact token packing and weighted combine,
including first-order input and gate gradients. Nothing in `models/`, configs,
optimizers, or perfkit calls these functions yet. No speedup is claimed.

## Layout and use

For `N` tokens and `K` routes per token, route `n*K+k` belongs to token `n`.
`order[p]` is the original route ID at packed row `p`. It must be a permutation
of `0..N*K-1`; typically it is obtained by stable-sorting flattened expert IDs.
Neither token dropping nor duplicated routes are supported.

```python
import torch
from kernels.moe_dispatch import RouteMap, pack_tokens, combine_tokens

# x: [N,D]; expert_ids and gates: [N,K], already computed by the router.
order = expert_ids.reshape(-1).argsort(stable=True)
routes = RouteMap(order, top_k=expert_ids.shape[1])  # validate/build inverse once
packed = pack_tokens(x, routes, top_k=expert_ids.shape[1])  # [N*K,D]
# Supply actual expert computation here, preserving packed row order.
expert_output = packed  # identity experts for this standalone example
output = combine_tokens(expert_output, gates, routes)     # [N,D]
```

There is no expert GEMM, router, token sorting kernel, all-to-all, or training
integration in this change. Unlike padded dispatch, the activation layout has
exactly `N*K` rows. A subsequent grouped-GEMM implementation can consume this
layout and expert row offsets.

## Numeric and execution contract

- CUDA and Triton are required; CPU calls fail explicitly. No hidden fallback.
- Activations and gates support fp32, fp16, and bf16, including fp32 router gates
  paired with lower-precision expert outputs. Autocast does not alter input dtypes.
- Products and reductions accumulate in fp32, then cast to the output/input
  gradient dtype. This is not bitwise-equivalent to rounding each low-precision
  product before summing. FP32 and BF16 checks use the existing pair framework
  or independent double-precision equations, as appropriate.
- `RouteMap` owns a snapshot of the permutation, validates it once, and builds
  its inverse once. Pack, combine, and their backwards reuse that inverse without
  further sorting, host synchronization, or inverse construction. Construct a new
  map whenever routing changes. It records `top_k` and the inferred token count
  and rejects reuse with a different factorization of the same route count.
  PyTorch tensor mutation is rejected on reuse and by backward version checks.
  These guards are best-effort: external raw-pointer or Triton writes do not
  increment PyTorch version counters. Never write to the exposed metadata tensors.
- The raw-tensor APIs remain checked by default. Validation sorts indices and
  synchronizes the device, so it belongs outside measured operations. Explicit
  `validate_indices=False` trusts caller metadata and is unsafe for invalid
  permutations. The raw combine path still constructs an inverse per call;
  use `RouteMap` for a pipeline. Map setup is not CUDA Graph capture compatible;
  the prepared-map forward path has a capture/replay correctness test.
- Strided activation, gate, and gradient-output tensors are accessed directly,
  including transposes and broadcast strides. Raw permutation tensors alone are
  made contiguous when necessary. Map construction makes one owned metadata copy.
- Gradient writes are unique. Input gradients reduce routes in a fixed order.
  Gate gradients for `D <= 1024` are written directly in the activation-gradient
  kernel, with no partial buffer or second reduction launch. Wider rows use a
  deterministic two-stage reduction; scratch is `N*K*ceil(D/512)*4` bytes and
  is allocated only when gate gradients are needed.
- Offsets are computed with int64. `launch_config` uses separate shape-dependent
  geometry for packing, input-gradient reduction, combine, and combine backward.
  These are heuristics, not benchmark-selected settings. The top-k reduction
  remains serial/fixed order and FP fusion remains disabled for reproducibility;
  parallel top-k/FMA variants need measured accuracy and latency comparisons.
  No autotuning or fastest-kernel claim is made.
- Double backward is explicitly unsupported. Expert gradients are supplied to
  the external expert computation through the ordinary autograd chain.
- Target Triton 3.0 or newer and a compatible PyTorch installation. The
  `enable_fp_fusion` launch option is present in the [3.0 backend options](https://github.com/triton-lang/triton/blob/v3.0.0/third_party/nvidia/backend/compiler.py).
  Local execution was tested with Triton 3.9.0; this is not a claim that every
  supported-version combination has been exercised.
- Disabling FP fusion fixes rounding policy; FMA itself does not imply
  nondeterminism. Unique writes and fixed reduction order are the important
  repeatability properties.
- Full-model `torch.compile` support is unverified here. Raw Triton launches
  can be compiled ([PyTorch guide](https://docs.pytorch.org/tutorials/recipes/torch_compile_user_defined_triton_kernel_tutorial.html));
  a `custom_op` registration is not automatically required. Prepared-map CUDA
  Graph replay is covered separately and does not establish compile support.

## Correctness

From the repository root, in an environment with PyTorch, pytest and Triton:

```bash
python -B -m pytest teams/06-performance/correctness/test_moe_dispatch_triton.py --all-configs -q -rs -p no:cacheprovider
```

CPU-only contract checks (these tests construct CPU tensors explicitly, even
when a GPU is visible):

```bash
python -B -m pytest teams/06-performance/correctness/test_moe_dispatch_triton.py --all-configs -q -k "on_cpu or shape_dtype_and_cpu_guards or cpu_backend_rejection" -p no:cacheprovider
```

The file registers `moe_kernel.pack` and `moe_kernel.combine` pairs and direct
1.01 rejection drills. It also checks uneven tiles, mixed dtypes, gate and input
gradients, scaled cotangents, empty tokens, noncontiguous inputs, frozen gradients,
repeatability, input validation, and noncurrent-device launches when available.
Only this standalone file is needed for local correctness. It does not run a
training benchmark. Target-device timing and training integration are later work.

Correctness snapshot including token/top-k binding and the extra boundaries
(conda `pytorch`, PyTorch 2.6.0+cu118, Triton 3.9.0):

| Check | Result |
| --- | --- |
| Complete file, CUDA | 64 passed, 1 skipped (requires two CUDA devices) |
| CPU contract selector | 11 passed; CUDA-dependent cases excluded |
| FP32 registered pairs | Both passed, including input/gate gradients and repeatability |
| 1.01 rejection drills | Both rejected the perturbed outputs |

These are development correctness results, not performance results. CPU tests
validate API guards; they do not execute Triton kernels on the CPU.
The updated tests also verify inverse reuse without repeated validation,
metadata ownership/mutation checks, transposed and broadcast strides, the
single-/two-stage gate-gradient boundary, and prepared-map CUDA Graph replay.

## Performance evidence still needed

The source changes remove repeated metadata work and some allocations/launches;
they do not prove an end-to-end speedup. Server comparisons must include map
construction once per routing decision, allocations, strided versus contiguous
inputs, and both forward and backward. Compare the prepared-map pipeline and
raw checked API separately. Sweep tile/warp choices rather than assuming the
current heuristics win. Top-k parallel reduction and FMA-enabled alternatives
remain measurement-driven follow-ups, not correctness fixes.

## References

The route permutation/unpermutation contract follows the established MoE
layout pattern described in [Megatron-LM's MoE utilities](https://github.com/NVIDIA/Megatron-LM/blob/main/megatron/core/transformer/moe/moe_utils.py).
The implementations here are original Triton kernels, not imported library
kernels or copies of that implementation. Tiled loads, masks and reductions use
the techniques in the [Triton tutorials](https://triton-lang.org/main/getting-started/tutorials/).
