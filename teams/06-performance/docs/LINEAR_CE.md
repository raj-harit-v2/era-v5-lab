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
| `triton_ce` | In-repo Triton tiled projection plus CE | Bounded forward statistics and derivative tiles | Auto-select vocabulary/token streaming; reuse each tile for both products |

`fused_cce` and `fused_liger` are source-inspired **PyTorch correctness/reference implementations**.
They do not vendor or call the upstream Triton kernels. This keeps the repo dependency-free and lets CPU
and CUDA correctness tests run from the existing environment. `fused_liger` shares the cached-gradient
implementation used by `fused` and `fused_cached`; it selects a fixed token tile size instead of a chunk
count. `fused_cce` retains the former `fused` vocabulary-streaming implementation. Do not interpret
their timings as upstream Liger or Apple kernel timings.

`triton_ce` is implemented in this repository under `kernels/linear_ce_fused.py`; it does not import
Liger or Apple CCE. One custom autograd path uses Triton tile kernels: forward computes tiled matrix
products and partial online log-sum-exp statistics, then reduces those statistics. It never writes the
full `[tokens, vocab]` logits. Backward forms unscaled fp32 loss derivatives in a reusable buffer,
then uses that tile for input, head-weight, and optional bias gradients. No gradient atomics are used.
Original tensors are saved for mutation/version checks along with their contiguous compute-dtype
casts, targets and per-token log-normalizers. The saved casts avoid making another low-precision
copy of the entire head in backward, at the cost of retaining that copy between passes. This combines
the projection/recompute structure used by Liger with Apple's online reduction approach. Triton must be
available in the CUDA PyTorch environment; CPU runs continue to use the reference implementations.
The `16 x 128 x 32` token/vocabulary/hidden tile is retained. The old backward is selectable with
`model.ce_triton_backward=recompute`: it reconstructs the projection separately for every hidden
output tile in both gradient kernels. At hidden width 256 and tile width 32, that is 16 complete
projection-equivalents in backward before the actual gradient products. This is an arithmetic count,
not a measured 16x slowdown.

`model.ce_triton_backward=auto` is the default. It chooses `vocab` when tokens <= vocabulary size,
otherwise `chunked`. Both reconstruct each logit exactly once in backward and perform the two
gradient products. They are three-stage streaming pipelines, not a single fully fused backward kernel:

| Strategy | Derivative tile | Accumulated gradient | Why choose it |
|---|---|---|---|
| `vocab` | `[tokens, vocabulary_chunk]` | fp32 dInput | Writes each dWeight/bias slice once after reducing all tokens; avoids repeated full-head gradient updates |
| `chunked` | `[token_chunk, vocab]` | fp32 dWeight/bias | Writes each dInput slice once; useful when the head gradient is smaller than the input gradient |
| `recompute` | No derivative buffer | Gradient products in each output tile | Legacy comparison only; repeated projection work scales with hidden size and is impractical for large hidden widths |

`ce_triton_scratch_mb` (default 64 MiB) caps the derivative buffer and, separately, the three forward
partial-statistic buffers. `ce_triton_chunk` (128) and `ce_triton_vocab_chunk` (4096) are upper bounds;
the effective extent shrinks to meet the byte budget. Forward also streams token chunks, so its
partial statistics no longer grow as the full `tokens * ceil(vocab/128)` tensor. Per-token loss/LZ and
required output gradients are separate allocations and are not included in the scratch cap.

At 4096 tokens, vocabulary 131072 and width 256, vocabulary streaming uses a 4096-column derivative
tile (64 MiB), writes the 128-MiB fp32 weight gradient once, and accumulates the smaller 4-MiB input
gradient across vocabulary chunks. The old token-streaming strategy repeatedly read/updated the
full weight gradient. This is a reduction in memory traffic from the code, not a measured speedup.
Larger scratch budgets/chunk limits may reduce launches further; tune these on the actual server.

Derivatives are kept **unscaled** through the dot products, and `grad_output / n_valid` is applied to
fp32 accumulators before the final output cast. `ce_triton_grad_precision=auto` uses fp32 gradient
operands for fp16 and fp32 compute; bf16 uses bf16 gradient products with fp32 accumulation.
`ce_triton_grad_precision=fp32` uses fp32 gradient operands for bf16 too, for accuracy comparisons.
`input_precision=ieee` does not restore precision after a bf16 cast. Explicit FP fusion is enabled
for reproducibility across Triton default-policy changes. All output gradients retain the original
input/parameter dtypes. Frozen inputs/parameters skip their gradient buffers and products.

This API implements mean reduction only, returning an fp32 loss. All-ignored input returns zero
loss and gradients, deliberately matching the project's other memory-bounded modes rather than
PyTorch's NaN mean for an empty valid set. Class weights, label smoothing, z-loss, and higher-order
derivatives are not implemented; double backward is explicitly rejected. Other loss features are
outside this kernel's current contract. Integer-like chunk sizes (including NumPy integers) are accepted.

Targets must be in range or equal to `ignore_index`. `ce_triton_validate_targets=true` enables a
debug bounds check that raises before launch and introduces a host synchronization. It defaults to
false for timing; unchecked invalid labels produce a NaN loss rather than a plausible incorrect loss.

All flattened offsets use int64 before multiplication. Token counts are ordinary non-specialized
Triton arguments, so ragged token tails do not require constexpr specialization. Width, vocabulary
tile size, dtype and gradient flags can still produce variants. The 16x128x32 tile remains a conservative
baseline; larger tiles and cache/occupancy claims need profiling rather than an assumed speedup.

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

The Triton file compares auto/vocabulary/token/legacy backward against PyTorch, including uneven and
one-token chunks, retained graphs, loss scaling, fp16/bf16/autocast, frozen gradients and repeat
determinism. Regression cases check a 65,537-token fp16 mean, debug target validation, positive ignore
indices, NumPy integer arguments, saved cast reuse, bounded forward and backward scratch, int64
offsets without huge allocation, and single-write vocabulary slices of dWeight. A multi-GPU test skips
on one GPU. The tests are independent of benchmark results; no performance improvement is assumed.

### Local correctness validation (6 November 2026)

Validated in the `pytorch` conda environment on Windows 11 with PyTorch 2.6.0+cu118,
Triton 3.9.0 and an NVIDIA GeForce RTX 3060 Laptop GPU:

| Check | Result |
| --- | --- |
| CUDA: `correctness/test_ce_triton.py --all-configs` | 100 passed, 1 skipped (requires two GPUs) |
| Additional CUDA checks: int64 offsets and auto streaming at V=3 and V=131072 | 4 passed (two offset checks repeated after making FP fusion explicit) |
| CPU: `test_ce.py`, `test_ce_triton.py`, `test_bench.py`, all configs | 189 passed, 99 CUDA-only tests skipped |

The two real-vocabulary/streaming-direction cases were added after the full-file run and passed in
the additional CUDA check. The CPU run explicitly selected CPU fixtures; the later GPU-only cases
would add two skips. The fp32 `ce.triton` pair measured relative errors of approximately 5.65e-8 for
loss and 3.04e-7 for gradients, and its 1.01 perturbation drill passed by rejecting the bad result.
These are correctness results, not GPU timings. Multi-GPU behavior and A100/H100 performance still
need validation on the corresponding servers.

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

Compare the old and new Triton backward on the same server/commit/config:

```bash
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_recompute data.source=synthetic model.ce_impl=triton_ce model.ce_triton_backward=recompute
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_tokens data.source=synthetic model.ce_impl=triton_ce model.ce_triton_backward=chunked model.ce_triton_chunk=128
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_vocab data.source=synthetic model.ce_impl=triton_ce model.ce_triton_backward=vocab model.ce_triton_vocab_chunk=4096
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_vocab256mb data.source=synthetic model.ce_impl=triton_ce model.ce_triton_backward=vocab model.ce_triton_vocab_chunk=16384 model.ce_triton_scratch_mb=256
```

The report treats the Triton controls as A/B implementation switches. Use the same chunk size and
backward strategy for the two runs inside each `--repeat 2` check. Run correctness first:

```bash
python -m pytest correctness/test_ce_triton.py correctness/test_bench.py -q
```

Level-3 regions expose `fwd:ce.triton.forward_stats` and `bwd:ce.triton.dlogits`,
`bwd:ce.triton.dx`, `bwd:ce.triton.dw`, `bwd:ce.triton.scale`. These are nested inside head/loss;
do not add them again to step time. They help locate a bottleneck, while clean step time and peak
memory decide which strategy to use. Direct correctness runs do not benchmark these regions.

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
