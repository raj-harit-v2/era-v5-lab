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

`fused_cce` and `fused_liger` are source-inspired **PyTorch correctness/reference implementations**.
They do not vendor or call the upstream Triton kernels. This keeps the repo dependency-free and lets CPU
and CUDA correctness tests run from the existing environment. `fused_liger` shares the cached-gradient
implementation used by `fused` and `fused_cached`; it selects a fixed token tile size instead of a chunk
count. `fused_cce` retains the former `fused` vocabulary-streaming implementation. Do not interpret
their timings as upstream Liger or Apple kernel timings.

The upstream references are [Liger's fused linear cross-entropy source](https://github.com/linkedin/Liger-Kernel/blob/main/src/liger_kernel/ops/fused_linear_cross_entropy.py)
and [Apple's Cut Cross-Entropy repository](https://github.com/apple/ml-cross-entropy). Liger chunks the
token dimension and forms each chunk's logits, while Apple's method computes the target logit and
log-sum-exp without materializing the full logits matrix. This repository adapts those algorithmic ideas
to portable PyTorch custom autograd; it does not copy upstream source code or kernel implementations.

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

Run focused correctness on CPU and, when installed, CUDA:

```bash
pytest teams/06-performance/correctness/test_ce.py --all-configs -q
```

The implementation modes can be selected in the benchmark/config interface for future cluster timing:

```bash
python -m perfkit.bench model.ce_impl=torch
python -m perfkit.bench model.ce_impl=chunked
python -m perfkit.bench model.ce_impl=fused
python -m perfkit.bench model.ce_impl=fused_liger
python -m perfkit.bench model.ce_impl=fused_cce
```

For a valid performance comparison, use the same committed tree, GPU, config, and run conditions, and
compare each mode against a `torch` baseline. GPU timings are intentionally not recorded by correctness.
