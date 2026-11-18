# Linear cross-entropy options

`model.ce_impl` selects one of five implementations. Every option uses the same LM head and averages
over non-ignored targets; the selection also applies to the MTP head.

| Option | Algorithm | Temporary logits | Backward strategy |
|---|---|---|---|
| `torch` | PyTorch linear head followed by cross-entropy | Full `[tokens, vocab]` | PyTorch autograd |
| `chunked` | Position chunks with activation checkpointing | One position chunk | Recompute head in backward |
| `fused` | Token chunks with cached gradients | At most `[ceil(tokens / ce_chunks), vocab]` | Scale and return saved dh/dW |
| `triton_liger` | Official Liger fused linear CE, token chunks | One token chunk | Scale saved dX/dW chunks |
| `triton_cce` | Official Apple Cut Cross-Entropy, online vocabulary reduction | One vocabulary tile | Recompute logit tiles, then derivative tiles |

`chunked` and `fused` run on CPU and CUDA. They are the portable memory-bounded options.
`torch` remains the reference path.

## Official Triton backends

`triton_liger` and `triton_cce` are the official upstream implementations vendored under
`kernels/triton_liger.py` and `kernels/triton_cce.py`. The kernel bodies follow upstream except for
Liger's calibrated token-chunk heuristic; the local code otherwise supplies thin adapters and the
required helper functions. They are imported lazily, require CUDA and Triton, and have no CPU
fallback. On CPU, use `fused` or `chunked`.

- Liger pin: `44a8f2fb40cd90269b84818cd9ca0d981e88b148`
- Apple ML-CE pin: `3de376c106a1916bc5e1b619f9c77c87a461ee1c`

`triton_liger` uses Liger's token chunking and caches the head gradients in forward.
`triton_cce` uses Apple's online log-sum-exp reduction, requires compute capability >= 8, and its
backward recomputes each logit tile from the saved normalizer before building dInput and dWeight
tiles. Neither path writes the full `[tokens, vocab]` logits.

The required public adapters are `linear_cross_entropy_liger` and `linear_cross_entropy_cce` in
`models/linear_ce.py`. Both accept `x [tokens, hidden]`, `weight [vocab, hidden]`, `targets`,
`bias=None`, and `ignore_index=-100`.

## Portable fused path

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

Without targets GPT still returns ordinary logits for inference. `triton_liger` and `triton_cce`
select their own internal tiles; they do not use `ce_chunks`.

## Memory scaling and chunk size

The relevant quantity for a token-chunked CE is the **logits tile**, not the number of chunks:

```text
logits_tile_bytes = tokens_in_chunk * vocab_size * dtype_bytes
```

For `V=131072` in bf16, one token costs `131072 * 2 = 0.25 MiB` of logits. Liger also keeps
full-size `grad_input` (`[tokens, hidden]`) and `grad_weight` (`[vocab, hidden]`) buffers. Those
fixed buffers do not grow with the token chunk, and each chunk's logits are released before the next
chunk, so peak memory is approximately:

```text
O(chunk_size * V + tokens * H + V * H)
```

not `O(tokens * V)`. This is why increasing the chunk can improve speed for a long time without
moving peak memory: the fixed buffers and allocator headroom absorb small tiles.

The exploratory sweep below forced chunks from 8 to 1024 on the current benchmark shape
(`H=256`, `V=131072`, `B*T=4096`) and found 512 to be the knee. The vendored copy uses that as a
minimum efficient tile, not as a universal constant:

```text
natural     = next_pow2(ceil(B*T / ceil(V / H)))
memory_cap  = floor_pow2(256 MiB / (V * element_bytes))
chunk_size  = min(B*T, max(512, natural), memory_cap)
```

For the current shape, `natural=8`, `memory_cap=1024`, so the floor wins and the chunk is 512. At a
120B-scale shape with `H=8192`, `B*T=8192..16384`, and the same vocabulary, `natural` grows to
512..1024 and the chunk follows it; a huge vocabulary shrinks `memory_cap` and wins over the floor.
The heuristic is calibrated, not a proof of optimality: re-tune the 512 floor and 256 MiB cap for a
different GPU. The measured peak is the whole-process allocator peak, not just the CE head:

| Liger token chunk | logits tile | measured peak |
|---:|---:|---:|
| 8 | 2 MiB | 0.88 GiB |
| 16 | 4 MiB | 0.88 GiB |
| 32 | 8 MiB | 0.88 GiB |
| 64 | 16 MiB | 0.88 GiB |
| 128 | 32 MiB | 0.88 GiB |
| 256 | 64 MiB | 0.88 GiB |
| **512** | **128 MiB** | **1.06 GiB** |
| 1024 | 256 MiB | 1.43 GiB |

In this run the first visible increase is at **512 tokens** (a 128 MiB logits tile). That is not a
universal threshold: it is where the tile stops fitting in the allocator's existing headroom. On a
tighter baseline it can appear earlier; on a looser one, later. Use the byte formula rather than a
fixed chunk number. Doubling `V` or switching bf16 to fp32 doubles the tile for the same token
chunk, so the visible step moves to half as many tokens. The 1024-token tile is 256 MiB and raises
peak to 1.43 GiB, but is slightly slower than 512 (144.3 vs 143.7 ms); the extra memory buys no
speed. The 0.18 GiB step to 512 is larger than its 128 MiB tile because it reflects the allocator's
block size and existing headroom, not just the tile.

The vendored copy implements the heuristic with `MIN_TOKEN_CHUNK=512` and
`MAX_LOGITS_BYTES=256 MiB` in `kernels/triton_liger.py`; it is not controlled by `ce_chunks`. For a
120B-scale head with `H~8192`, `V=131072`, and per-GPU `B*T=8192..16384`, the formula selects
512..1024 tokens, so the logits tile is 128..256 MiB; the `V*H` head-gradient buffer is ~2 GiB in
bf16 and is the larger fixed cost. The 512 floor keeps small-`H` models out of the pathological
8-token regime, while the natural term lets larger `H` or token counts grow the chunk. Re-check the
two constants if `V`, dtype, or the target GPU changes materially.

The other implementations scale differently:

- `torch` materializes the full `[tokens, vocab]` logits and autograd state; memory grows with
  `tokens * V`.
- `chunked` checkpoints token chunks (`ce_chunks`) and recomputes the head in backward; temporary
  logits are one chunk.
- `fused` also bounds logits by `ceil(tokens / ce_chunks) * V`, but retains full fp32 `grad_input`
  and `grad_weight`, so increasing `ce_chunks` reduces the logits tile only.
- `triton_cce` has no token chunk knob. It computes a fixed `BLOCK_B x BLOCK_V` logits tile in
  registers and stores only `lse` and the target logit; backward allocates full `dInput` and `dWeight`
  buffers. Its peak therefore does not track a user chunk size and was 0.88 GiB throughout the same
  exploratory run.

## Metrics

`triton_liger` and `fused` cache the head gradients, so their accounting adds no backward head work.
`chunked` and `triton_cce` recompute the head in backward, so `perfkit/metrics.py` adds `2 * head`
FLOPs for them. See [`METRICS.md`](METRICS.md).

## Correctness

`correctness/test_ce.py` registers `ce.fused`, `ce.triton_liger`, and `ce.triton_cce` pairs against
ordinary PyTorch cross-entropy. The portable fused pair runs on CPU and CUDA. The official pairs
require CUDA; `triton_cce` additionally requires compute capability >= 8. Tests compare loss and
input/weight gradients in fp32 and bf16, cover NTP and MTP routing, ignored labels including
all-ignored input, partial masks, and non-divisible token chunks. Native bf16 and bf16 autocast tests
verify the actual head-matmul dtype. Saved-tensor hooks check that `fused` retains only the two
gradient buffers, and a call-count check excludes head recomputation in backward. Loss scaling and
repeated backward are tested.

```bash
python -m pytest correctness/test_ce.py --all-configs -q
```

## Benchmarks

Run each mode under the same CUDA/PyTorch environment, batch size, sequence length, vocabulary,
precision, commit, and GPU. Run from `teams/06-performance` after committing the code:

```bash
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_torch data.source=synthetic model.ce_impl=torch
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_chunked data.source=synthetic model.ce_impl=chunked
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_fused data.source=synthetic model.ce_impl=fused
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_liger data.source=synthetic model.ce_impl=triton_liger
python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_cce data.source=synthetic model.ce_impl=triton_cce
```

Compare `clean.raw_step_ms`, `fwd:head+loss`, `bwd:head+loss`, peak allocated memory, and tokens/s.
The forward/backward split and peak allocation add context; total clean step time is the primary
speed metric. Keep exploratory measurements separate from official H100+ results.

The historical rows in [`results/speed_v1.md`](../results/speed_v1.md) use the old pre-rename labels
`fused_cce` and `fused_liger` for portable PyTorch implementations. Those selectors no longer exist,
and the rows are not measurements of the official `triton_cce` or `triton_liger` kernels.

Algorithm references: [Liger's fused linear cross-entropy source](https://github.com/linkedin/Liger-Kernel/blob/main/src/liger_kernel/ops/fused_linear_cross_entropy.py)
and [Apple's Cut Cross-Entropy repository](https://github.com/apple/ml-cross-entropy).
