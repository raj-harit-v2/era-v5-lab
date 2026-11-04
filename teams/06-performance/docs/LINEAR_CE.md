# Linear cross-entropy options

The model exposes several memory-bounded CE implementations through `model.ce_impl`. Every option
uses the same LM head and average over non-ignored targets; the selection also applies to the MTP head.

| Option | Algorithm | Temporary logits | Backward strategy |
|---|---|---|---|
| `torch` | PyTorch linear head followed by cross-entropy | Full `[tokens, vocab]` | PyTorch autograd |
| `chunked` | Position chunks with activation checkpointing | One position chunk | Recompute head in backward |
| `fused` | Task-5 token chunks with cached gradients | At most `[ceil(tokens / ce_chunks), vocab]` | Scale and return saved dh/dW |
| `fused_cce` | Apple Cut Cross-Entropy style online vocabulary reduction | One vocabulary tile | Recompute vocabulary tiles |
| `fused_liger` | Liger-style token chunk CE with cached head gradients | One token chunk | Return gradients computed during forward |
| `fused_cached` | Existing token-tiled custom autograd reference | One token chunk | Return cached head gradients |
| `triton_ce` | In-repo Triton linear projection plus online CE | No full logits or dLogits tensor | Recompute projection tiles and write dInput/dWeight directly |

`fused_cce` and `fused_liger` are source-inspired **PyTorch correctness/reference implementations**.
They do not vendor or call the upstream Triton kernels. This keeps the repo dependency-free and lets CPU
and CUDA correctness tests run from the existing environment. `fused_liger` shares the cached-gradient
implementation used by `fused` and `fused_cached`; it selects a fixed token tile size instead of a chunk
count. `fused_cce` retains the former `fused` vocabulary-streaming implementation. Do not interpret
their timings as upstream Liger or Apple kernel timings.

`triton_ce` is implemented in this repository under `kernels/linear_ce_fused.py`; it does not import
Liger or Apple CCE. One custom autograd path uses Triton tile kernels: forward computes tiled matrix
products and partial online log-sum-exp statistics, then reduces those statistics. It never writes the
full `[tokens, vocab]` logits. Backward recomputes projection tiles and directly produces input,
head-weight, and optional bias gradients without storing a full `dLogits` tensor or using atomics. It
saves inputs, targets, and per-token log-normalizers. This combines
the projection/recompute structure used by Liger with Apple's online reduction approach. Triton must be
available in the CUDA PyTorch environment; CPU runs continue to use the reference implementations.
The current `16 x 128 x 32` token/vocabulary/hidden tile fits the backward kernels' shared-memory
budget on Ampere. Backward recomputes the projection separately for each hidden output tile in both
the input-gradient and weight-gradient kernels. This can make a large hidden size compute-bound even
though the full logits tensor is never stored. Treat the tile sizes and backward strategy as candidates
for tuning after measuring total step time on A100 and H100.

Algorithm references: [Liger's fused linear cross-entropy source](https://github.com/linkedin/Liger-Kernel/blob/main/src/liger_kernel/ops/fused_linear_cross_entropy.py),
[Apple's Cut Cross-Entropy repository](https://github.com/apple/ml-cross-entropy), and [Triton's fused
softmax tutorial](https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html). The in-repo
kernel uses Liger's token chunking/recompute structure and Apple's online log-sum-exp principle; it does
not copy their kernels.

## Task-5 fused path

Set `model.ce_impl=fused` and choose `model.ce_chunks` (default 8). Each chunk contains at most
`ceil(B*T / ce_chunks)` tokens; uneven tails and chunk counts larger than the token count work.
For each chunk the custom autograd function:

1. Computes `h_chunk @ W.T`, honoring native bf16 tensors or the enclosing training autocast dtype.
2. Computes log-sum-exp and the target logit in fp32 and accumulates the loss sum.
3. Reuses the chunk's logits buffer for `softmax - onehot(target)`, masks ignored positions, and divides
   by the global number of valid targets. All-ignored input returns zero loss and zero gradients.
4. Uses bf16 matrix products for `dh_chunk` and `dW` when the head matmul is bf16, then accumulates
   their results in fp32 and releases the chunk's logits. fp16 keeps fp32 gradient products to avoid
   underflow of small probabilities before external loss scaling.

Only `dh` and `dW` are saved for backward, with `db` also saved when using a biased head. Backward
multiplies these cached derivatives by the incoming loss gradient and casts them to the input/parameter
dtypes. It does not recompute the head. Reusing a retained graph and scaling the loss are supported;
higher-order derivatives are not supported. The full head-gradient buffer is a material memory cost.
Forward region timing therefore includes the head-gradient matmuls; compare total step time alongside
the separate `fwd:head+loss` and `bwd:head+loss` timings.

The same function handles the primary head and the MTP head. Without targets GPT still returns ordinary
logits for inference. `ce_token_chunk` controls fixed token tiles for `fused_cached` / `fused_liger`;
`ce_vocab_chunk` controls vocabulary tiles for `fused_cce`. These controls do not change `fused`'s
`ce_chunks` setting.

## Correctness

`correctness/test_ce.py` registers `ce.fused`, `ce.fused_liger` and `ce.fused_cce` pairs against ordinary PyTorch
cross-entropy. They compare loss and input/weight gradients in fp32 and bf16, and exercise GPT routing
with NTP and MTP, ignored labels including all-ignored input, partial masks, and non-divisible token
chunks. Native bf16 and bf16 autocast tests verify the actual head-matmul dtype. Saved-tensor hooks check
that `fused` retains only the two gradient buffers, and a call-count check excludes head recomputation
in backward. Loss scaling and repeated backward are tested. A direct 1.01 drill for `ce.fused` lives in
this file; the pair framework also applies its tolerance drill to all registered fp32 pairs.

Run the reference CE tests on CPU or CUDA and the custom Triton tests on CUDA:

```bash
pytest teams/06-performance/correctness/test_ce.py --all-configs -q
pytest teams/06-performance/correctness/test_ce_triton.py --all-configs -q
```

The implementation modes can be selected in the benchmark/config interface for future cluster timing:

```bash
python -m perfkit.bench model.ce_impl=torch
python -m perfkit.bench model.ce_impl=chunked
python -m perfkit.bench model.ce_impl=fused
python -m perfkit.bench model.ce_impl=fused_cached
python -m perfkit.bench model.ce_impl=fused_liger
python -m perfkit.bench model.ce_impl=fused_cce
python -m perfkit.bench model.ce_impl=triton_ce
```

## Server setup and A100/H100 comparison

On each server, from `teams/06-performance`, use a CUDA PyTorch build compatible with the machine's
driver and Triton support. No Liger or Apple CCE package is needed; first confirm the server environment:

```bash
python -c "import torch, triton; print('torch', torch.__version__, 'triton', triton.__version__, 'cuda', torch.cuda.get_device_name())"
python -m pytest correctness/test_ce.py --all-configs -q
python -m pytest correctness/test_ce_triton.py --all-configs -q
```

The Triton CE correctness file covers direct kernel pairs and model integration; run it on A100 first, then
repeat correctness on H100 (or the actual official-run GPU) before timing. CPU reference tests work
without Triton; the `triton_ce` mode itself requires CUDA.

Run each variant under the same CUDA/PyTorch environment, batch size, sequence length, vocabulary,
precision, commit and available GPU. `--repeat 2` creates separate processes; each run records its own
JSON summary. Run from `teams/06-performance` after committing the code (the bench reports dirty trees).

```bash
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_torch data.source=synthetic model.ce_impl=torch
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_chunked data.source=synthetic model.ce_impl=chunked
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_fused data.source=synthetic model.ce_impl=fused
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_cached data.source=synthetic model.ce_impl=fused_cached
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_liger_ref data.source=synthetic model.ce_impl=fused_liger
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_cce_ref data.source=synthetic model.ce_impl=fused_cce
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_triton data.source=synthetic model.ce_impl=triton_ce
```

Compare `clean.raw_step_ms`, `fwd:head+loss`, `bwd:head+loss`, peak allocated memory and tokens/s. The
forward/backward split and peak allocation add context; the total clean step is the primary speed metric. Keep A100
exploratory results separate from official H100+ results. For design context, compare the [Triton fused
softmax tutorial](https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html),
[Liger's fused linear CE](https://github.com/linkedin/Liger-Kernel/blob/main/src/liger_kernel/ops/fused_linear_cross_entropy.py),
and [Apple CCE](https://github.com/apple/ml-cross-entropy), whose kernel computes linear logits and
log-sum-exp without writing the full logits matrix. The current in-repo kernel implements that fused
projection/reduction structure; benchmark and tune its tile sizes separately on A100 and H100+.

For a valid performance comparison, use the same committed tree, GPU, config, and run conditions, and
compare each mode against a `torch` baseline. GPU timings are intentionally not recorded by correctness.
