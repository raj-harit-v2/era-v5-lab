# Every part we time, and later make faster

This is the list the code is designed around. If a part is not in this file, the report and the
5% gate cannot see it: **add the row here first, then the code.**

## Design rules

1. **Every row is a `region()`** with the name and level below (`perfkit/regions.py`).
   Names are `<phase>:<part>`, e.g. `fwd:block3.attn.sdpa`, `bwd.recompute:block3`, `opt:opt.muon`.
2. **Every expensive part is a config switch backed by a registry** (like `DISPATCH` in `models/moe.py`).
   The plain PyTorch version stays as `reference`. A faster version is a new entry, never a rewrite.
3. **No host syncs inside the step.** `.item()` only at logging steps.
4. **All shapes come from `ModelConfig`.** G5's full-width config is a different YAML, nothing else.
5. **Every faster version ships with a `@pair` correctness test** and a before/after timing on the same GPU.

Levels: 1 = phases, 2 = per layer and big parts (gated: within 5% or less than 0.05 ms apart between two runs),
3 = inside a layer (information only).

The "Likely bottleneck" column was written before the baseline. The v0 traces (`results/slowest5_v0.md`, A100,
`base.yaml`) confirm: `head+loss` is memory-bound (the fp32 logits, 54% of the step), `bwd:blockN.grad` and
`opt.muon.ns` are launch-bound (many small kernels), and `opt.adamw` is memory-bound on the head's parameters.

## 1. Inside the training step

| Part | Region (level) | Switch: week-1 baseline → later | Likely bottleneck | Later optimization |
|---|---|---|---|---|
| Data: batch sampling + host-to-device copy | `data` (1); `data:prefetch` (3) after backward | `data.prefetch: false → true` (default true) | CPU, copy overlap | background prefetch thread |
| KE2 code + projection | `embed.ke` (3) | `model.embedding: ke2` (default) | memory | already one `embedding_bag` over the support columns; fuse the position add |
| KE v1 codec + projection | `embed.ke` (3) | `model.ke_mode: dynamic \| cached` → sparse | memory (8192-dim codec) | gather + sum (`embedding_bag`), fuse the position add |
| Position add | `embed` (2) | | memory | fuse into the KE kernel |
| LayerNorm × 2 per block | `blockN.ln1`, `blockN.ln2` (3) | `model.norm_impl: torch → fused` | memory | fuse with the residual add or the next matmul |
| QKV matmul + head split | `blockN.attn.qkv` (3) | | compute | tensor-core-friendly shapes, fused split |
| Attention kernel | `blockN.attn.sdpa` (3) | `model.attn_impl: eager \| sdpa` (default eager) → flash3 / flex | compute / memory | FlashAttention-3 (H100), FA4 / cuDNN (B200) |
| Output copy + projection | `blockN.attn.proj` (3) | | memory (the copy) | a layout that needs no copy |
| Dense MLP | `blockN.mlp` (3) | `model.activation: gelu → swiglu` (a model choice, not an A/B switch) | compute | fused GELU / fused SiLU * up |
| MoE router: matmul, softmax, top-k, gates | `blockN.moe.router` (3) | | launch | one fused router kernel |
| MoE dispatch: gather, experts, combine | `blockN.moe.dispatch` (3), `.dispatch.expertE` (3); sorted path adds `.dispatch.grouped` | `model.moe.dispatch: loop → sorted` | **host syncs + launch** | sort routes, pack them per expert, run one batched matmul per projection (one host sync for the largest group) |
| Shared experts | `blockN.moe.shared` (3) | | compute | batch with the routed experts |
| Residual / midpoint arithmetic | inside `blockN` (2) | | memory | fusion |
| Final LN + LM head + cross-entropy | `head+loss` (2) | `model.ce_impl: torch → chunked → fused` | **memory (fp32 logits)** | fused linear + cross-entropy |
| MTP head + its cross-entropy (`model.mtp=true`) | `head+loss.mtp` (3), inside `head+loss` | `model.mtp` | memory (a second set of fp32 logits) | the same fused cross-entropy |
| Backward of every part above | `bwd:<part>` | same switches | ~2× forward | follows the forward fixes |
| Reversible: invert, recompute, local backward | `bwd.invert:blockN`, `bwd.recompute:blockN`, `bwd:blockN.grad` (3) | `model.reversible` | ~2× extra forward | fuse invert + recompute, cache cheap pieces |
| fp16 grad unscale | `opt.unscale` (2) | | small | |
| Gradient clipping (global norm) | `opt.clip` (2) | | memory, one reduction | foreach / fused kernel |
| Muon (Newton-Schulz per matrix) | `opt.muon` (2), `opt.muon.ns` (3, one call per shape bucket when batched) | `optim.muon_impl: loop → batched` (default batched) | launch (many small matrices) | done: same-shaped matrices stacked (`bmm` / batched `@`); next: CUDA graph of the optimizer step |
| Polar Express Muon + AdamW (one optimizer) | `opt.polar_muon_adamw` (2), with `opt.muon` / `opt.adamw` and `opt.muon.ns` inside | `optim.name: polar_muon_adamw` (default) | launch | CUDA graph of the whole step |
| AdamW (embedding parameters, output head, norm gains, biases) | `opt.adamw` (2) | `optim.adamw_impl: loop → foreach` (`polar_muon_adamw`, default foreach); `fused=True` (`optim.name=adamw`, CUDA) | memory (the 33.5M-parameter head) | fused kernel |
| zero_grad, MoE bias update | `opt.zero_grad`, `opt.moe_bias` (3) | | tiny | |

## 2. Around the step (parts of the run, not of the step)

| Part | Where it is timed | Why it matters |
|---|---|---|
| Startup: model, data loader and optimizer build | `goodput.badput_s.startup` | time to first step (week-4 launch speed check) |
| First step, including `torch.compile` / autotune | `goodput.badput_s.first_step` | once per run, can take minutes |
| Warmup steps | `goodput.badput_s.warmup` | allocator and autotune settle |
| Logging (`.item()`) | `goodput.badput.logging` (planned) | each call is a host sync |
| Eval | `goodput.badput.eval` (planned) | not training time |
| Checkpoint save (later load / resume) | `checkpoint` mode: `save_ms` (= `to_cpu_ms` + `write_ms`), `size_mb`; `save_ms` is a gated part (rule 3b) | blocks training; later async or sharded |
| Tokenizer throughput | `tokenizer` mode (planned; not in `bench.MODES` yet) | offline, but feeds the data pipeline (G3's tokenizer later) |

## 3. Measured, but not regions

| What | How | Why |
|---|---|---|
| CPU-GPU syncs per step | `torch.cuda.set_sync_debug_mode("warn")` in trace mode: `trace.host_syncs_per_step`, `trace.sync_sites` | each one stops the CPU from queueing work ahead |
| GPU busy % and idle gaps | profiler trace: `trace.gpu_busy_pct` | shows the GPU waiting for the CPU |
| Kernel launches per step | profiler trace: `trace.kernels_per_step`, `trace.top_ops` | launch-bound vs compute-bound |
| Peak memory | `torch.cuda` memory stats: `memory.peak_allocated_gb`, `peak_reserved_gb` (GiB; `memory.gpu` identifies device) | batch-size limits, reversible savings |
| GPU utilization, clocks, temperature, power, slowdown reasons | `nvidia-smi` sampled through the clean steps (`GpuSampler`): `system`; one-off samples in `meta.telemetry` | explains 5% misses on shared GPUs |

## 4. Weeks 2 to 4 (plan the names and switches now, code later)

| Part | Region | Switch |
|---|---|---|
| Gradient all-reduce / reduce-scatter (data parallel) | `comm.grad` | `dist.strategy: ddp → fsdp` |
| MoE expert-parallel all-to-all (dispatch and combine) | `comm.moe_a2a` (week 1: the payload, timed alone with `--modes comm` under torchrun with `model.ffn=moe`; a gated part when measured, rule 3b) | `model.moe.parallel: none → ep` |
| Communication overlap with backward | `bwd` with and without comm | bucket size |
| Load imbalance across GPUs and experts | per-rank step time, tokens per expert | balancing settings |
| Checkpoint sharding | `checkpoint` | `ckpt.mode: sync → async / sharded` |
| FP8 matmuls (H100 / B200) | same regions | `run.dtype: bf16 → fp8` |
| Time to first step | startup | launch speed check |

## Switches already present

| Switch | Values (default first) | Notes |
|---|---|---|
| `model.moe.dispatch` | `loop` \| `sorted` | `DISPATCH` in `models/moe.py`; implementation switch |
| `optim.muon_impl` | `batched` \| `loop` | `batched` updates same-shaped matrices at once; implementation switch |
| `optim.adamw_impl` | `foreach` \| `loop` | `polar_muon_adamw` only; `torch._foreach` multi-tensor ops; implementation switch |
| `data.prefetch` | `true` \| `false` | next batch sampled and pinned after backward is queued; same batches; implementation switch |
| `model.embedding` | `ke2` \| `ke1` \| `table` | a different model, not an A/B |
| `model.attn_impl` | `eager` \| `sdpa` | a different kernel with the same maths; compared as a different config |
| `model.mtp` | `false` \| `true` | a second head: a different model |
| `model.ce_impl` | `torch` \| `chunked` | `chunked` runs head + loss in `model.ce_chunks` checkpointed pieces |
| `model.ke_mode` | `dynamic` \| `cached` | `cached` keeps a V x 8192 fp32 table (4 GiB at V = 131072) |
| `optim.name` | `polar_muon_adamw` \| `muon` \| `adamw` | a different update, so a different config, not an A/B |
| `run.compile` | `false` \| `true` | regions inside compiled code are not timed reliably |

Implementation switches (`report.IMPL_SWITCHES`: `model.moe.dispatch`, `optim.muon_impl`, `optim.adamw_impl`,
`data.prefetch`) are the only config differences `--against` accepts; the verdict is then labelled A/B. The
planned switches in the tables above (`model.norm_impl`, `dist.strategy`, `model.moe.parallel`, `ckpt.mode`, fp8,
`model.ce_impl: fused`) are not in `configs/base.yaml` yet.
