# LayerNorm implementations

`model.ln_impl` selects `torch_ln` (default `nn.LayerNorm`) or `triton_ln` for
`ln1`, `ln2`, and `ln_f`. Both modules expose the same `weight` and `bias`
parameters and state-dict keys, so a checkpoint can be loaded into either.
The Triton kernel supports CUDA fp16/bf16/fp32 inputs and last-dimension affine
norms up to 8192 features. The module uses `nn.LayerNorm` for CPU, fp64,
unsupported widths, multiple normalized dimensions, missing affine parameters,
or an unavailable Triton installation. `layer_norm_triton` is a strict functional
API that rejects unsupported inputs, so kernel tests cannot silently test the
fallback. Norm gains and biases remain trainable AdamW parameters.

The implementation in `kernels/layer_norm.py` follows the [official Triton
LayerNorm tutorial](https://triton-lang.org/main/getting-started/tutorials/05-layer-norm.html):
rows use fp32 mean/variance, and backward applies the row-wise input-gradient
formula. At widths <=1024, each program processes a four-row tile. Wider norms
use one row per tile. Warp count scales from 1 to 8 with the padded feature
width. These are launch heuristics, not measured autotuning results. Weight
loads prefer cache retention; input and upstream-gradient loads prefer eviction.
Those cache hints also require server measurement.

Backward launches at most `4 * SM_count` groups. Each group visits disjoint
row tiles in increasing order and writes one partial gain/bias gradient per
feature. A second kernel reduces these partials without atomics or locks. Each
requested parameter gradient therefore needs at most
`4 * SM_count * hidden_size * 4` bytes of scratch, independent of token count.
Frozen gain/bias gradients skip their buffers and arithmetic; freezing both
skips the parameter-reduction kernel. The group count is device-specific and
cached. Repeated execution on the same device/configuration has a fixed sum
order; bitwise agreement across different GPU models is not promised.

All flattened offsets use int64 before multiplication, including partial-buffer
offsets. Forward and backward launches guard the input's CUDA device. Contiguous
weights are saved once, and token/group counts are ordinary non-specialized
Triton arguments rather than constexprs. Width, epsilon, dtype, launch geometry,
and requested gradients can still produce distinct compilations.

CUDA autocast follows PyTorch LayerNorm's fp32 policy using `custom_fwd` and
`custom_bwd`. Native low-precision calls outside autocast preserve the input
output dtype. Higher-order gradients through the Triton path are explicitly
unsupported (`once_differentiable`); the PyTorch fallback retains native behavior.

No speedup is established at the model's 256-feature width. GPU correctness,
compile compatibility, launch tuning, and speed must be checked on the servers;
the Windows revision receives syntax/diff checks only.

From `teams/06-performance`, first validate correctness on each server GPU:

```bash
python -m pytest correctness/test_layer_norm_triton.py correctness/test_bench.py -q
python -m pytest correctness/test_model.py -q
```

The focused file includes dtype-specific forward/dx/dw/db comparisons, odd and
boundary feature sizes, the actual 4096x256 shape, noncontiguous tensors, mixed
upstream gradient dtypes, frozen parameters, repeat determinism, CUDA autocast,
double-backward rejection, backend fallback, bounded group counts, and a compiled
fullgraph forward/backward comparison. The two-GPU device test skips on one GPU.
A small test checks the exact offset helper above the int32 boundary without
allocating a huge tensor. The real >2^31-element case is opt-in and needs at least
24 GiB free (run on a server with ample memory):

```bash
G6_LN_LARGE_TEST=1 python -m pytest correctness/test_layer_norm_triton.py -k large_tensor -q
```

`torch.compile` supports raw Triton launches; the implementation does not claim
that a `triton_op` wrapper is mandatory. The fullgraph test validates this specific
autograd path on the installed PyTorch/Triton versions. Backward timing contexts
are omitted while compiling. See the [PyTorch integration guide](https://docs.pytorch.org/tutorials/recipes/torch_compile_user_defined_triton_kernel_tutorial.html).

Then compare matching runs on the same GPU, dtype, batch, sequence length,
and commit. The default `torch_ln` run is the reference:

```bash
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ln_torch data.source=synthetic model.ln_impl=torch_ln
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ln_triton data.source=synthetic model.ln_impl=triton_ln
```

Compare `clean.raw_step_ms` first, then the level-3 entries
`fwd:blockN.ln1`, `fwd:blockN.ln2`, and `fwd:head+loss.ln_f` in
`layer.regions`. The console summarizes only its slowest level-3 parts; the
run JSON holds every region. The per-norm regions measure forward calls.
`bwd:ln.triton.rows` measures the input-gradient/partial-gradient kernel and
`bwd:ln.triton.params` measures the parameter reduction, aggregated over all
norm calls in the eager step. These are nested inside block/head backward timing,
so do not add them again to step time. Compiled runs should use clean/trace timing.

Inspect `meta.layer_norm.requested` and `meta.layer_norm.modules` in each run.
Each module entry records its resolved `backend` and fallback `reason` for the
model's setup dtype/device. Fallbacks are also printed in benchmark notes. Do not
label a run as Triton performance if these entries resolve to `torch_ln`.
The report accepts `model.ln_impl` as an A/B implementation switch; repeats still
compare two runs of the same implementation. The clean step is the decision metric.
