# Every part we time, and later make faster

If a part is not in this file, the report and the 5% gate cannot see it: **add the row here first, then the code.**

## Rules

1. **Every row is a `region()`** with the name and level below (`perfkit/regions.py`). Names are `<phase>:<part>`,
   e.g. `fwd:block3.attn.sdpa`, `bwd.recompute:block3`, `opt:opt.muon`. Levels: 1 phases, 2 per layer and big
   parts (gated by the 5% rule), 3 inside a layer (information only).
2. **Every expensive part is a config switch backed by a registry** (like `DISPATCH` in `models/moe.py`). The
   plain version stays as the reference; a faster version is a new entry with a `@pair` test and a before / after
   timing on the same GPU.
3. **All shapes come from `ModelConfig`.**
4. **Timing:** CUDA events only, read after the steps; no `synchronize`, `.item()` or `print` inside a timed step.
   10 warmup steps, then 100 measured (`report.min_compare_steps`). Gate on the median, p10, p90; mean and std are
   for information. Steps alternate recorder on / off; overhead above 2% flags the numbers. With
   `bench.layer_prefill` (CUDA) each layer step starts with a GPU busy-wait, sent before the step timer starts, so
   Python stays ahead of the GPU and every part is GPU time, not the CPU's time to send it.

Bottlenecks below are from the v0 traces (`results/slowest5_v0.md`, A100, `base.yaml`).

## 1. Inside the training step

| Part | Region (level) | Switch | Bottleneck |
|---|---|---|---|
| Batch sampling + host-to-device copy | `data` (1); `data:prefetch` (3) | `data.prefetch` | CPU, copy overlap |
| KE2 / KE v1 code + projection | `embed.ke` (3), in `embed` (2) | `model.embedding`, `model.ke_mode` | memory |
| LayerNorm x 2 per block | `blockN.ln1`, `blockN.ln2` (3) | `model.ln_impl` | memory |
| QKV matmul (+ RoPE) | `blockN.attn.qkv` (3) | `model.position` | compute |
| Attention kernel | `blockN.attn.sdpa` (3) | `model.attn_impl` | compute / memory |
| Output projection | `blockN.attn.proj` (3) | | memory |
| Dense MLP | `blockN.mlp` (3) | `model.activation` | compute |
| MoE router | `blockN.moe.router` (3) | | launch |
| MoE dispatch: gather, experts, combine | `blockN.moe.dispatch` (3) and its `.expertE` / `.grouped` / `.grouped_fixed` | `model.moe.dispatch` | host syncs + launch |
| MoE shared experts | `blockN.moe.shared` (3) | | compute |
| Final LN + head + cross-entropy | `head+loss` (2); `head+loss.ln_f`, `head+loss.mtp` (3) | `model.ln_impl`, `model.ce_impl`, `model.mtp` | **memory (fp32 logits)** |
| Backward of every part above | `bwd:<part>` | same switches | ~2x forward |
| Reversible: invert, recompute, local backward | `bwd.invert:blockN`, `bwd.recompute:blockN`, `bwd:blockN.grad` (3) | `model.reversible`, `model.rev_impl` | launch |
| fp16 unscale, gradient clipping | `opt.unscale`, `opt.clip` (2) | | small |
| Muon / Polar Express Muon + AdamW | `opt.muon`, `opt.polar_muon_adamw` (2); `opt.muon.ns` (3) | `optim.name`, `optim.muon_impl` | launch |
| AdamW | `opt.adamw` (2) | `optim.adamw_impl` | memory (the head) |
| zero_grad, MoE bias update | `opt.zero_grad`, `opt.moe_bias` (3) | | tiny |

## 2. Around the step

| Part | Where it is timed |
|---|---|
| Startup, first step, warmup | `goodput.badput_s.startup` / `.first_step` / `.warmup` |
| Checkpoint save | `checkpoint` mode: `save_ms` (= `to_cpu_ms` + `write_ms`), `size_mb`; gated |
| MoE all-to-all | `comm` mode under `torchrun` with `model.ffn=moe`; gated when measured |
| Logging, eval, tokenizer throughput | planned |

## 3. Measured, but not regions

| What | Field |
|---|---|
| Host syncs per step and where | `trace.host_syncs_per_step`, `trace.sync_sites` |
| GPU busy %, kernels per step, top ops | `trace.gpu_busy_pct`, `trace.kernels_per_step`, `trace.top_ops` |
| Peak memory | `memory.peak_allocated_gb`, `memory.peak_reserved_gb` |
| GPU utilization, clocks, temperature, power, slowdown reasons | `system` (sampled through the clean steps), `meta.telemetry` |

## Switches

| Switch | Values (default first) | Kind |
|---|---|---|
| `model.moe.dispatch` | `loop` \| `sorted` \| `grouped` | implementation |
| `model.ce_impl` | `torch` \| `chunked` \| `fused` \| `fused_cached` \| `fused_liger` \| `fused_cce` | implementation (`docs/LINEAR_CE.md`) |
| `model.rev_impl` | `two_pass` \| `one_pass` | implementation (same update, different backward) |
| `optim.muon_impl` | `batched` \| `loop` | implementation |
| `optim.adamw_impl` | `foreach` \| `loop` | implementation (`polar_muon_adamw` only) |
| `data.prefetch` | `true` \| `false` | implementation (same batches) |
| `model.embedding` | `ke2` \| `ke1` \| `table` | model |
| `model.ke_mode` | `dynamic` \| `cached` | model (cached: 4 GiB table at V = 131072) |
| `model.attn_impl` | `eager` \| `sdpa` | model (same maths, compared as a different config) |
| `model.position` | `learned` \| `rope` | model (`rope` needs `model.rope_theta`) |
| `model.activation` | `gelu` \| `swiglu` | model |
| `model.mtp` | `false` \| `true` | model |
| `optim.name` | `polar_muon_adamw` \| `muon` \| `adamw` | model |
| `run.compile` | `false` \| `true` | regions inside compiled code are not timed reliably |

Implementation switches (`report.IMPL_SWITCHES`) are the only config differences `--against` accepts; the verdict
is then labelled A/B.
