# LayerNorm implementations

`model.ln_impl` selects `torch_ln` (default `nn.LayerNorm`) or `triton_ln` for
`ln1`, `ln2`, and `ln_f`. Both modules expose the same `weight` and `bias`
parameters and state-dict keys, so a checkpoint can be loaded into either.
`triton_ln` requires CUDA and Triton and supports last-dimension affine norms
up to 8192 features. Norm gains and biases remain trainable AdamW parameters.

The implementation in `kernels/layer_norm.py` follows the [official Triton
LayerNorm tutorial](https://triton-lang.org/main/getting-started/tutorials/05-layer-norm.html):
one program normalizes each row with fp32 mean/variance, and backward applies
the row-wise input-gradient formula. Groups of four rows accumulate partial
gain and bias gradients; a second kernel reduces those partials without locks
or global atomics. The backward reduction adds temporary fp32 buffers. This
implementation has not been established as faster than PyTorch at this model's
256-feature width; compare full step times before selecting a default.

From `teams/06-performance`, first validate correctness on each server GPU:

```bash
python -m pytest correctness/test_layer_norm_triton.py -q
python -m pytest correctness/test_model.py -q
```

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
LayerNorm's autograd backward is included in the enclosing block or
`bwd:head+loss` timing. The clean step is the performance decision metric.
