# Bench report — g6_mlp_t4

**GPU:** Tesla T4  |  **dtype:** fp16  |  **B x T:** 8 x 256  |  **torch:** 2.11.0+cu130
**commit:** `a2c6656604d4a0cdbb848c6abc32658e8298a1bf`  |  **tag:** g6_mlp_t4

## Step (clean)

- median: 125.341 ms
- p10..p90: 124.715 .. 126.796 ms
- tokens/s: 16,339
- MFU: 6.2%  |  HFU: 7.1%

## Diagnostics

### CUDA timing-event allocations

- [OK] clean: events_created_during_steps=0
- [OK] layer: events_created_during_steps=0
- [OK] layer.inner_pass: events_created_during_steps=0

### Benchmark warnings

- [warn] 12 of 12 samples during the clean steps had a slowdown reason (SwPowerCap): may miss the 5% check
- [warn] GPU slowed down while the steps ran (SwPowerCap): a shared or throttled GPU misses the 5% check
- [warn] rule 3b: checkpoint not measured; add checkpoint to --modes
- [warn] 2 gated part(s) have p10..p90 spread > 10%, so may miss the 5% check: data, bwd:embed

## Regions

| part | median ms | p90 | % of step | level |
| :--- | ---: | ---: | ---: | ---: |
| data | 0.021 | 0.025 | 0.0 | 1 |
| fwd | 36.838 | 37.245 | 29.4 | 1 |
| fwd:embed | 0.958 | 0.991 | 0.8 | 2 |
| fwd:embed.ke | 0.960 | 1.004 | 0.8 | 3 |
| fwd:stack | 6.124 | 6.210 | 4.9 | 1 |
| fwd:block0 | 1.020 | 1.034 | 0.8 | 2 |
| fwd:block0.ln1 | 0.031 | 0.032 | 0.0 | 3 |
| fwd:block0.attn.qkv | 0.061 | 0.064 | 0.0 | 3 |
| fwd:block0.attn.sdpa | 0.652 | 0.658 | 0.5 | 3 |
| fwd:block0.attn.proj | 0.038 | 0.041 | 0.0 | 3 |
| fwd:block0.ln2 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block0.mlp | 0.166 | 0.172 | 0.1 | 3 |
| fwd:block1 | 1.018 | 1.033 | 0.8 | 2 |
| fwd:block1.ln1 | 0.030 | 0.031 | 0.0 | 3 |
| fwd:block1.attn.qkv | 0.061 | 0.064 | 0.0 | 3 |
| fwd:block1.attn.sdpa | 0.651 | 0.657 | 0.5 | 3 |
| fwd:block1.attn.proj | 0.038 | 0.040 | 0.0 | 3 |
| fwd:block1.ln2 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block1.mlp | 0.166 | 0.172 | 0.1 | 3 |
| fwd:block2 | 1.018 | 1.032 | 0.8 | 2 |
| fwd:block2.ln1 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block2.attn.qkv | 0.060 | 0.063 | 0.0 | 3 |
| fwd:block2.attn.sdpa | 0.650 | 0.659 | 0.5 | 3 |
| fwd:block2.attn.proj | 0.038 | 0.040 | 0.0 | 3 |
| fwd:block2.ln2 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block2.mlp | 0.166 | 0.174 | 0.1 | 3 |
| fwd:block3 | 1.018 | 1.034 | 0.8 | 2 |
| fwd:block3.ln1 | 0.030 | 0.031 | 0.0 | 3 |
| fwd:block3.attn.qkv | 0.061 | 0.064 | 0.0 | 3 |
| fwd:block3.attn.sdpa | 0.651 | 0.660 | 0.5 | 3 |
| fwd:block3.attn.proj | 0.038 | 0.040 | 0.0 | 3 |
| fwd:block3.ln2 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block3.mlp | 0.166 | 0.172 | 0.1 | 3 |
| fwd:block4 | 1.016 | 1.034 | 0.8 | 2 |
| fwd:block4.ln1 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block4.attn.qkv | 0.060 | 0.063 | 0.0 | 3 |
| fwd:block4.attn.sdpa | 0.652 | 0.661 | 0.5 | 3 |
| fwd:block4.attn.proj | 0.039 | 0.041 | 0.0 | 3 |
| fwd:block4.ln2 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block4.mlp | 0.167 | 0.172 | 0.1 | 3 |
| fwd:block5 | 1.016 | 1.036 | 0.8 | 2 |
| fwd:block5.ln1 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block5.attn.qkv | 0.061 | 0.063 | 0.0 | 3 |
| fwd:block5.attn.sdpa | 0.651 | 0.659 | 0.5 | 3 |
| fwd:block5.attn.proj | 0.038 | 0.040 | 0.0 | 3 |
| fwd:block5.ln2 | 0.029 | 0.031 | 0.0 | 3 |
| fwd:block5.mlp | 0.166 | 0.173 | 0.1 | 3 |
| fwd:head+loss | 29.755 | 30.028 | 23.7 | 2 |
| bwd | 58.617 | 59.580 | 46.8 | 1 |
| bwd:head+loss | 35.186 | 35.223 | 28.1 | 2 |
| bwd:stack | 22.670 | 23.536 | 18.1 | 1 |
| bwd:block5 | 3.715 | 3.751 | 3.0 | 2 |
| bwd.invert:block5 | 1.023 | 1.036 | 0.8 | 3 |
| bwd.invert:block5.ln1 | 0.029 | 0.030 | 0.0 | 3 |
| bwd.invert:block5.attn.qkv | 0.055 | 0.057 | 0.0 | 3 |
| bwd.invert:block5.attn.sdpa | 0.641 | 0.645 | 0.5 | 3 |
| bwd.invert:block5.attn.proj | 0.035 | 0.037 | 0.0 | 3 |
| bwd.invert:block5.ln2 | 0.027 | 0.028 | 0.0 | 3 |
| bwd.invert:block5.mlp | 0.157 | 0.161 | 0.1 | 3 |
| bwd.recompute:block5 | 1.025 | 1.039 | 0.8 | 3 |
| bwd.recompute:block5.ln1 | 0.029 | 0.030 | 0.0 | 3 |
| bwd.recompute:block5.attn.qkv | 0.055 | 0.057 | 0.0 | 3 |
| bwd.recompute:block5.attn.sdpa | 0.644 | 0.648 | 0.5 | 3 |
| bwd.recompute:block5.attn.proj | 0.035 | 0.037 | 0.0 | 3 |
| bwd.recompute:block5.ln2 | 0.027 | 0.028 | 0.0 | 3 |
| bwd.recompute:block5.mlp | 0.157 | 0.161 | 0.1 | 3 |
| bwd:block5.grad | 1.750 | 1.768 | 1.4 | 3 |
| bwd:block4 | 3.716 | 3.813 | 3.0 | 2 |
| bwd.invert:block4 | 1.026 | 1.042 | 0.8 | 3 |
| bwd.invert:block4.ln1 | 0.029 | 0.030 | 0.0 | 3 |
| bwd.invert:block4.attn.qkv | 0.055 | 0.058 | 0.0 | 3 |
| bwd.invert:block4.attn.sdpa | 0.641 | 0.647 | 0.5 | 3 |
| bwd.invert:block4.attn.proj | 0.035 | 0.037 | 0.0 | 3 |
| bwd.invert:block4.ln2 | 0.027 | 0.029 | 0.0 | 3 |
| bwd.invert:block4.mlp | 0.158 | 0.163 | 0.1 | 3 |
| bwd.recompute:block4 | 1.027 | 1.048 | 0.8 | 3 |
| bwd.recompute:block4.ln1 | 0.029 | 0.030 | 0.0 | 3 |
| bwd.recompute:block4.attn.qkv | 0.055 | 0.058 | 0.0 | 3 |
| bwd.recompute:block4.attn.sdpa | 0.644 | 0.651 | 0.5 | 3 |
| bwd.recompute:block4.attn.proj | 0.035 | 0.037 | 0.0 | 3 |
| bwd.recompute:block4.ln2 | 0.027 | 0.029 | 0.0 | 3 |
| bwd.recompute:block4.mlp | 0.158 | 0.162 | 0.1 | 3 |
| bwd:block4.grad | 1.747 | 1.795 | 1.4 | 3 |
| bwd:block3 | 3.719 | 3.960 | 3.0 | 2 |
| bwd.invert:block3 | 1.026 | 1.095 | 0.8 | 3 |
| bwd.invert:block3.ln1 | 0.029 | 0.034 | 0.0 | 3 |
| bwd.invert:block3.attn.qkv | 0.055 | 0.064 | 0.0 | 3 |
| bwd.invert:block3.attn.sdpa | 0.643 | 0.664 | 0.5 | 3 |
| bwd.invert:block3.attn.proj | 0.035 | 0.041 | 0.0 | 3 |
| bwd.invert:block3.ln2 | 0.027 | 0.033 | 0.0 | 3 |
| bwd.invert:block3.mlp | 0.158 | 0.178 | 0.1 | 3 |
| bwd.recompute:block3 | 1.030 | 1.104 | 0.8 | 3 |
| bwd.recompute:block3.ln1 | 0.029 | 0.035 | 0.0 | 3 |
| bwd.recompute:block3.attn.qkv | 0.055 | 0.064 | 0.0 | 3 |
| bwd.recompute:block3.attn.sdpa | 0.645 | 0.666 | 0.5 | 3 |
| bwd.recompute:block3.attn.proj | 0.035 | 0.042 | 0.0 | 3 |
| bwd.recompute:block3.ln2 | 0.027 | 0.033 | 0.0 | 3 |
| bwd.recompute:block3.mlp | 0.158 | 0.179 | 0.1 | 3 |
| bwd:block3.grad | 1.752 | 1.865 | 1.4 | 3 |
| bwd:block2 | 3.767 | 4.000 | 3.0 | 2 |
| bwd.invert:block2 | 1.034 | 1.104 | 0.8 | 3 |
| bwd.invert:block2.ln1 | 0.029 | 0.035 | 0.0 | 3 |
| bwd.invert:block2.attn.qkv | 0.056 | 0.067 | 0.0 | 3 |
| bwd.invert:block2.attn.sdpa | 0.643 | 0.668 | 0.5 | 3 |
| bwd.invert:block2.attn.proj | 0.036 | 0.042 | 0.0 | 3 |
| bwd.invert:block2.ln2 | 0.028 | 0.033 | 0.0 | 3 |
| bwd.invert:block2.mlp | 0.161 | 0.182 | 0.1 | 3 |
| bwd.recompute:block2 | 1.046 | 1.108 | 0.8 | 3 |
| bwd.recompute:block2.ln1 | 0.029 | 0.035 | 0.0 | 3 |
| bwd.recompute:block2.attn.qkv | 0.057 | 0.066 | 0.0 | 3 |
| bwd.recompute:block2.attn.sdpa | 0.647 | 0.668 | 0.5 | 3 |
| bwd.recompute:block2.attn.proj | 0.038 | 0.043 | 0.0 | 3 |
| bwd.recompute:block2.ln2 | 0.029 | 0.033 | 0.0 | 3 |
| bwd.recompute:block2.mlp | 0.162 | 0.180 | 0.1 | 3 |
| bwd:block2.grad | 1.789 | 1.866 | 1.4 | 3 |
| bwd:block1 | 3.858 | 4.002 | 3.1 | 2 |
| bwd.invert:block1 | 1.072 | 1.106 | 0.9 | 3 |
| bwd.invert:block1.ln1 | 0.032 | 0.035 | 0.0 | 3 |
| bwd.invert:block1.attn.qkv | 0.061 | 0.067 | 0.0 | 3 |
| bwd.invert:block1.attn.sdpa | 0.654 | 0.667 | 0.5 | 3 |
| bwd.invert:block1.attn.proj | 0.039 | 0.043 | 0.0 | 3 |
| bwd.invert:block1.ln2 | 0.031 | 0.033 | 0.0 | 3 |
| bwd.invert:block1.mlp | 0.171 | 0.181 | 0.1 | 3 |
| bwd.recompute:block1 | 1.075 | 1.110 | 0.9 | 3 |
| bwd.recompute:block1.ln1 | 0.032 | 0.035 | 0.0 | 3 |
| bwd.recompute:block1.attn.qkv | 0.061 | 0.067 | 0.0 | 3 |
| bwd.recompute:block1.attn.sdpa | 0.658 | 0.670 | 0.5 | 3 |
| bwd.recompute:block1.attn.proj | 0.039 | 0.043 | 0.0 | 3 |
| bwd.recompute:block1.ln2 | 0.031 | 0.033 | 0.0 | 3 |
| bwd.recompute:block1.mlp | 0.171 | 0.180 | 0.1 | 3 |
| bwd:block1.grad | 1.815 | 1.865 | 1.4 | 3 |
| bwd:block0 | 3.870 | 4.002 | 3.1 | 2 |
| bwd.invert:block0 | 1.069 | 1.108 | 0.9 | 3 |
| bwd.invert:block0.ln1 | 0.032 | 0.035 | 0.0 | 3 |
| bwd.invert:block0.attn.qkv | 0.061 | 0.067 | 0.0 | 3 |
| bwd.invert:block0.attn.sdpa | 0.655 | 0.668 | 0.5 | 3 |
| bwd.invert:block0.attn.proj | 0.039 | 0.042 | 0.0 | 3 |
| bwd.invert:block0.ln2 | 0.031 | 0.033 | 0.0 | 3 |
| bwd.invert:block0.mlp | 0.171 | 0.180 | 0.1 | 3 |
| bwd.recompute:block0 | 1.074 | 1.106 | 0.9 | 3 |
| bwd.recompute:block0.ln1 | 0.032 | 0.035 | 0.0 | 3 |
| bwd.recompute:block0.attn.qkv | 0.062 | 0.066 | 0.0 | 3 |
| bwd.recompute:block0.attn.sdpa | 0.659 | 0.668 | 0.5 | 3 |
| bwd.recompute:block0.attn.proj | 0.039 | 0.042 | 0.0 | 3 |
| bwd.recompute:block0.ln2 | 0.031 | 0.033 | 0.0 | 3 |
| bwd.recompute:block0.mlp | 0.171 | 0.180 | 0.1 | 3 |
| bwd:block0.grad | 1.816 | 1.870 | 1.4 | 3 |
| bwd:embed | 0.795 | 0.844 | 0.6 | 2 |
| data:prefetch | 0.002 | 0.003 | 0.0 | 3 |
| opt | 30.755 | 31.215 | 24.5 | 1 |
| opt:opt.unscale | 1.436 | 1.441 | 1.1 | 2 |
| opt:opt.clip | 2.032 | 2.038 | 1.6 | 2 |
| opt:opt.polar_muon_adamw | 27.277 | 27.748 | 21.8 | 2 |
| opt:opt.muon | 13.790 | 14.322 | 11.0 | 2 |
| opt:opt.muon.ns | 13.989 | 14.498 | 11.2 | 3 |
| opt:opt.adamw | 13.328 | 13.356 | 10.6 | 2 |
| opt:opt.moe_bias | 0.002 | 0.002 | 0.0 | 3 |
| opt:opt.zero_grad | 0.002 | 0.002 | 0.0 | 3 |

## Time by part type (sum over layers)

| part type | median ms sum | % of step |
| :--- | ---: | ---: |
| bwd | 58.617 | 46.8 |
| fwd | 36.838 | 29.4 |
| bwd:head+loss | 35.186 | 28.1 |
| opt | 30.755 | 24.5 |
| fwd:head+loss | 29.755 | 23.7 |
| opt:opt.polar_muon_adamw | 27.277 | 21.8 |
| bwd:stack | 22.670 | 18.1 |
| bwd:block* | 22.644 | 18.1 |
| opt:opt.muon.ns | 13.989 | 11.2 |
| opt:opt.muon | 13.790 | 11.0 |
| opt:opt.adamw | 13.328 | 10.6 |
| bwd:block*.grad | 10.669 | 8.5 |
| bwd.recompute:block* | 6.278 | 5.0 |
| bwd.invert:block* | 6.251 | 5.0 |
| fwd:stack | 6.124 | 4.9 |
| fwd:block* | 6.105 | 4.9 |
| fwd:block*.attn.sdpa | 3.908 | 3.1 |
| bwd.recompute:block*.attn.sdpa | 3.896 | 3.1 |
| bwd.invert:block*.attn.sdpa | 3.878 | 3.1 |
| opt:opt.clip | 2.032 | 1.6 |
| opt:opt.unscale | 1.436 | 1.1 |
| fwd:block*.mlp | 0.997 | 0.8 |
| bwd.recompute:block*.mlp | 0.977 | 0.8 |
| bwd.invert:block*.mlp | 0.976 | 0.8 |
| fwd:embed.ke | 0.960 | 0.8 |
| fwd:embed | 0.958 | 0.8 |
| bwd:embed | 0.795 | 0.6 |
| fwd:block*.attn.qkv | 0.364 | 0.3 |
| bwd.recompute:block*.attn.qkv | 0.346 | 0.3 |
| bwd.invert:block*.attn.qkv | 0.345 | 0.3 |
| fwd:block*.attn.proj | 0.230 | 0.2 |
| bwd.recompute:block*.attn.proj | 0.222 | 0.2 |
| bwd.invert:block*.attn.proj | 0.219 | 0.2 |
| bwd.invert:block*.ln1 | 0.179 | 0.1 |
| bwd.recompute:block*.ln1 | 0.179 | 0.1 |
| fwd:block*.ln1 | 0.178 | 0.1 |
| fwd:block*.ln2 | 0.174 | 0.1 |
| bwd.invert:block*.ln2 | 0.171 | 0.1 |
| bwd.recompute:block*.ln2 | 0.170 | 0.1 |
| data | 0.021 | 0.0 |
| opt:opt.zero_grad | 0.002 | 0.0 |
| data:prefetch | 0.002 | 0.0 |
| opt:opt.moe_bias | 0.002 | 0.0 |

## Five slowest leaf parts

1. `opt:opt.muon.ns` — 13.989 ms (11.2% of step)
2. `bwd:block0.grad` — 1.816 ms (1.4% of step)
3. `bwd:block1.grad` — 1.815 ms (1.4% of step)
4. `bwd:block2.grad` — 1.789 ms (1.4% of step)
5. `bwd:block3.grad` — 1.752 ms (1.4% of step)
