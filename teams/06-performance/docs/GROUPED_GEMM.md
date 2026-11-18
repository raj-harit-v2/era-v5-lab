# Standalone variable-size expert GEMM

`kernels/grouped_gemm.py` adds a compact expert linear operation and first-order
input, weight, and optional bias gradients. It is not wired into models,
optimizers, configs, or perfkit. No performance improvement is claimed.

## Contract

```python
from kernels.grouped_gemm import ExpertSegments, grouped_linear

# packed: [R,K], weights: [E,N,K], optional bias: [E,N].
# offsets: E+1 integer boundaries with offsets[0]=0, offsets[-1]=R.
# packed[offsets[e]:offsets[e+1]] belongs to expert e.
segments = ExpertSegments(offsets, num_rows=packed.shape[0])
out = grouped_linear(packed, weights, segments, bias)  # [R,N]
```

Outputs preserve packed row order. `combine_tokens` can consume them directly
with the same route map used for packing. Activations are not expanded into an
`[experts, capacity, features]` buffer. Repeated boundaries represent idle
experts; they receive exactly zero weight/bias gradients.

Weights use the `nn.Linear` orientation, with a leading expert dimension.
This API requires a packed weight tensor. Constructing it from a model's
`ModuleList`, and its cost, remain integration work. There is no activation,
router, token sorting, all-to-all, or second expert projection fused here.

## Implementation

- Forward and input-gradient GEMMs use persistent workers that traverse the
  variable expert sizes on-device. The input-gradient operation reuses the
  projection kernel with transposed weight strides.
- By default each weight-gradient tile owns its result and reduces that expert's
  token rows in a fixed order, without scratch. Optional `split_r=2/4/.../32`
  divides reduction blocks across programs, then sums FP32 partials in split
  order. Neither path uses atomics. Splitting is deterministic for a fixed
  setting; it can differ numerically from the unsplit reduction.
- When weight and bias gradients are both requested, bias reduction shares the
  weight-gradient pass. Bias-only backward uses its own reduction kernel.
- Empty experts are skipped by projection scheduling. Weight/bias backward
  writes zeros for their parameters; the fully empty batch is also supported.
- Activations, weights, bias, and cotangents may be strided; their strides are
  passed directly to the kernels. Raw offsets alone are made contiguous.
- Address arithmetic uses int64. Each launch uses the tensor's CUDA device.
- Frozen input/weight/bias gradients are skipped independently. Second-order
  gradients are explicitly unsupported.

`launch_config` exposes initial shape heuristics: projection uses 32x64x32,
or 64x128x32 for sufficiently large low-precision shapes; weight gradients use
32x32 or 64x64 output tiles. Persistent workers are capped at two waves per SM.
These are not autotuned or benchmark-selected. The projection still scans expert
boundaries on-device, and backward still schedules idle experts to write zeros.

Use `grouped_linear(..., split_r=4)` to compare split-row backward on a server.
The default remains `split_r=1`. When weight gradients are required, extra
scratch is `4 * E * split_r * (N*K + N if bias gradients else N*K)` bytes,
capped at 64 MiB; an excessive request raises before the forward launch.
Bias-only backward retains its scratch-free reduction. Splitting can help a
long reduction but adds launches and memory traffic; measure rather than assume
an improvement. Changing tile shapes can change floating-point summation order.

## Precision and metadata

- CUDA and Triton 3.0+ are required. The tested installation is Triton 3.9.0;
  the minimum version has not been independently exercised. CPU calls reject explicitly.
- X and weights must share fp16, bf16, or fp32 dtype. Bias may have that dtype
  or fp32. Accumulation is fp32, outputs have X's dtype, and gradients have
  their corresponding input dtype.
- Autocast does not implicitly change this API's input dtypes. Explicitly cast
  X/weights when choosing a lower-precision operation; automatic mixed-precision
  training integration is deferred.
- `precision="ieee"` is the FP32 correctness baseline. Optional
  `precision="tf32x3"` selects decomposed tensor-core products where supported.
  `precision="tf32"` is an explicit lower-accuracy option, tested separately
  with a relative L2 error budget below 2e-3, rather than the strict FP32 pair
  tolerance. These modes apply to FP32 operands only; fp16/bf16 use their own
  tensor-core products with FP32 accumulation regardless of this argument.
- Raw offset calls validate values by default, synchronizing the device.
  `ExpertSegments` clones first, validates that owned snapshot, and reuses it without repeated
  value checks. Rebuild it when routing changes. Shape/device checks remain.
- `validate_offsets=False` is a trusted-input path: invalid boundaries can cause
  unsafe GPU access. Do not use it on unchecked metadata.
- PyTorch mutation counters protect saved inputs and boundaries. External
  raw-pointer writes do not increment counters and must not mutate metadata.
- Build checked metadata and warm the kernels outside CUDA Graph capture.
  A focused test captures/replays forward and first-order backward with fixed
  prepared segments. Raw checked offsets synchronize and cannot be validated
  during capture. Full-model graph integration and `torch.compile` remain
  unverified. Raw Triton launches in an autograd.Function do not by themselves
  imply a graph break; support depends on the surrounding Python as well.

## Correctness commands

From the repository root in an environment with PyTorch, pytest and Triton:

```bash
python -B -m pytest teams/06-performance/correctness/test_grouped_gemm_triton.py --all-configs -q -rs -p no:cacheprovider
```

CPU-only contract checks (no GPU operations):

```bash
python -B -m pytest teams/06-performance/correctness/test_grouped_gemm_triton.py --all-configs -q -k "on_cpu or shape_dtype_and_cpu_guards or cpu_backend_rejection" -p no:cacheprovider
```

Tests compare forward and all gradients against independent per-expert linear
operations, including fp64 reference equations, idle/empty experts, uneven
matrix tiles, scaled/strided cotangents, strided weights, frozen gradients,
repeatability, index types, bad boundaries, saved-metadata mutation, and optional
multi-device execution. `moe_kernel.grouped_linear` is registered with the
existing pair framework alongside `moe_kernel.grouped_linear.split_rows`; both
have direct 1.01 rejection drills. A separate test
composes packing, grouped projection, and combine; no training model is invoked.

Development correctness after the review revisions (conda `pytorch`,
PyTorch 2.6.0+cu118, Triton 3.9.0):

| Check | Result |
| --- | --- |
| Complete file on CUDA | 59 passed, 1 skipped (requires two CUDA devices) |
| CPU guard selector | 7 passed, 53 deselected |
| Both registered pairs | Output and all three input gradients passed; repeatable bit for bit |
| Both 1.01 rejection drills | Rejected perturbed output |

The suite also exercises 16 experts with skewed/idle segments and artificially
limited workers so persistent scheduling must traverse several tiles/experts.
These are correctness results, not performance results. CPU-only tests validate
API guards; they do not execute Triton on the CPU.

Review additions test split-row gradients against FP64 and the single-pass path
in all three dtypes, bitwise repeatability, larger tile buckets, TF32's explicit
error budget, snapshot-before-validation ordering, scratch limits, and fixed
prepared-segment CUDA Graph forward/backward. No performance benchmarks or
runtime autotuning are run by these correctness tests. Activation fusion, FP8,
custom-op registration, and a measured grouped-library comparison remain follow-ups.

## References

The on-device grouped scheduling pattern is described by Triton's
[Group GEMM tutorial](https://triton-lang.org/main/getting-started/tutorials/08-grouped-gemm.html).
Tiled products and stride-based addressing follow the techniques in the
[matrix multiplication tutorial](https://triton-lang.org/main/getting-started/tutorials/03-matrix-multiplication.html).
The kernels here are standalone implementations, not an imported dependency.
PyTorch documents supported custom Triton/autograd.Function compilation in its
[user-defined Triton kernel tutorial](https://docs.pytorch.org/tutorials/recipes/torch_compile_user_defined_triton_kernel_tutorial.html).
