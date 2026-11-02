# Part 6: head and loss forward (`fwd:head+loss`) on a T4

GPU: Tesla T4 (Kaggle, 1 of 2), torch 2.11.0+cu128, commit `7bc8bee` (`g6/dev`), `configs/base.yaml` with
`run.dtype=fp16 run.batch_size=8` (the README setting for a T4: no native bf16, 16 GB). Run `t4_headloss`
(run ID `f4642b02910e4090b2ce54a01c425587`), 100 measured steps after 10 warmup.

```
python -m perfkit.bench --config configs/base.yaml --modes clean,layer,trace --level 3 \
    --tag t4_headloss run.dtype=fp16 run.batch_size=8
```

Step 128.2 ms, 15,975 tokens/s, MFU 6.1%, peak memory 3.54 GB. `fwd:head+loss` is **30.24 ms, 23.6% of the
step** (p10..p90 30.10..30.43); with `bwd:head+loss` (35.45 ms) head and loss are 51% of the step, as on the A100.

Trace: [`runs/t4_headloss_parts/2_fwd_head+loss.json`](runs/t4_headloss_parts/2_fwd_head+loss.json) (open in
https://ui.perfetto.dev). The full trace (`~/.cache/era-perf/traces/t4_headloss.json`, 11 MB) is not committed.

## What the part does

`ln_f` -> `head` (Linear 256 -> 131,072, no bias) -> `.float()` -> `F.cross_entropy`. With B=8, T=256 that is
N = 2,048 tokens and N x V = 268M logits: 0.54 GB in fp16, 1.07 GB after the fp32 copy.

## The three slowest operations

7 kernels, 30.98 ms of GPU time in the traced step. The GPU is busy 98% of the step, and each operation runs once.

| # | Operation | GPU ms | % of part | Calls | Kernels | Main kernel |
|---|---|---:|---:|---:|---:|---|
| 1 | `aten::cross_entropy_loss` | 17.01 | 54.9% | 1 | 2 | `cunn_SoftMaxForward` (log-softmax) 16.99 ms, `nll_loss_forward` 0.03 ms |
| 2 | `aten::to` (the `.float()` of the logits) | 7.64 | 24.6% | 1 | 1 | fp16 -> fp32 elementwise copy 7.63 ms |
| 3 | `aten::linear` (the head) | 6.30 | 20.3% | 1 | 3 | `turing_fp16_s1688gemm` 5.48 ms, fp32 -> fp16 weight cast 0.82 ms |

`ln_f` is 0.03 ms. Each kernel is assigned to the outermost aten op that launched it (matched through the
CUDA launch correlation IDs in the part trace).

## Why each is slow, and one idea each

T4 limits: 320 GB/s memory, 65 TFLOPS fp16 tensor cores, so the ridge point is about 200 FLOP/byte. The GPU ran
power-capped (SwPowerCap, SM clock 1200 of 1590 MHz) for the whole run, so the real compute peak was nearer 49
TFLOPS.

1. **Log-softmax: memory-bound.** It reads 1.07 GB of fp32 logits and writes 1.07 GB of fp32 log-probabilities
   for a few FLOPs per element: at least 2.15 GB in 17.0 ms, 126 GB/s (39% of peak; the kernel reads each row
   more than once, so the real traffic is higher). **Idea:** fused linear cross-entropy (Task 5,
   `model.ce_impl: fused`). Per chunk of tokens, compute the logsumexp and the target logit and throw the
   logits away, so the 1.07 GB fp32 tensor and its 1.07 GB log-softmax output are never written.
2. **The fp32 copy: memory-bound.** It reads 0.54 GB and writes 1.07 GB with no math: 1.61 GB in 7.6 ms,
   211 GB/s (66% of peak). **Idea:** stop materializing fp32 logits. Pass the fp16/bf16 logits to
   `F.cross_entropy` (its kernels accumulate in fp32) or upcast inside the fused kernel per chunk; check the
   loss with a `@pair` test against the current path. Fused CE (item 1) removes this copy as well.
3. **Head matmul: compute-bound, close to the ridge.** 2 x 2,048 x 256 x 131,072 = 137 GFLOP in 5.48 ms,
   25 TFLOPS (39% of the 65 TFLOPS peak, 51% of the power-capped one). It moves about 0.6 GB (mostly the fp16
   logits it writes), about 230 FLOP/byte, just above the ridge. The 0.82 ms next to it is autocast casting the
   33.5M fp32 head weights to fp16 on every forward, which is memory-bound. **Idea:** keep the matmul (the
   FLOPs are needed) but stop writing its 0.54 GB output: fused CE consumes each logit chunk while it is still
   in cache. The weight cast could be done once per optimizer step instead of once per forward.

Nothing in this part is launch-bound: 7 kernels in about 31 ms, each over 0.8 ms except `ln_f` and the NLL.

## Same ranking as the A100

`results/slowest5_v0.md` (A100-SXM4-40GB, bf16, B=16, commit `f1ed7f2`): log-softmax 6.2 ms, the fp32 copy
2.9 ms, the head matmul 1.5 ms. With half the tokens the T4 is 2.7x (softmax), 2.6x (copy) and 3.7x (matmul)
slower per op, which fits its 4.9x lower memory bandwidth and lower tensor-core throughput. Both GPUs have the
same top three in the same order, and both spend 80 to 85% of the part on the two memory-bound ops.

## Comparison: `model.ce_impl=chunked`

Run `t4_headloss_chunked` (run ID `6d819d1a4749442391fecf3b8b795989`, same command plus `model.ce_impl=chunked`,
8 chunks), trace [`runs/t4_headloss_chunked_parts/2_fwd_head+loss.json`](runs/t4_headloss_chunked_parts/2_fwd_head+loss.json):

| | torch | chunked |
|---|---:|---:|
| `fwd:head+loss` | 30.24 ms | 31.61 ms |
| `bwd:head+loss` | 35.45 ms | 84.09 ms |
| step | 128.2 ms | 182.7 ms |
| peak memory | 3.54 GB | 0.98 GB |

Chunked runs the same three ops 8 times on 1/8 of the tokens: the forward GPU time is the same (31.7 ms, 55
kernels instead of 7). It saves 2.6 GB but recomputes the whole forward inside the backward (48.6 ms more),
so the step is 43% slower on a T4. A fused cross-entropy that computes the gradient in the forward pass would
keep chunked's memory without that recompute, which is the case for Task 5.

## Caveats

- One run per setting (no `--repeat 2`); the part's p10..p90 spread is 1.1%.
- fp16 with GradScaler, not bf16: the ops are the same, the numbers are not comparable to bf16 GPUs one to one.
- The GPU was power-capped for all 13 telemetry samples (bench warns that this can miss the 5% check).
