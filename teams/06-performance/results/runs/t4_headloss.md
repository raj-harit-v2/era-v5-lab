# Bench report — t4_headloss

**GPU:** Tesla T4  |  **dtype:** fp16  |  **B x T:** 8 x 256  |  **torch:** 2.11.0+cu128
**commit:** `7bc8beecefd0ab6584bfa233fca38d02710af412`  |  **tag:** t4_headloss

## Step (clean)

- median: 128.203 ms
- p10..p90: 127.195 .. 130.028 ms
- tokens/s: 15,975
- MFU: 6.1%  |  HFU: 6.9%

## Diagnostics

### CUDA timing-event allocations

- [OK] clean: events_created_during_steps=0
- [OK] layer: events_created_during_steps=0
- [OK] layer.inner_pass: events_created_during_steps=0

### Benchmark warnings

- [warn] 13 of 13 samples during the clean steps had a slowdown reason (SwPowerCap): may miss the 5% check
- [warn] GPU slowed down while the steps ran (SwPowerCap): a shared or throttled GPU misses the 5% check
- [warn] rule 3b: checkpoint not measured; add checkpoint to --modes
- [warn] 5 gated part(s) have p10..p90 spread > 10%, so may miss the 5% check: data, bwd:block3, bwd:block2, bwd:block1, bwd:embed

## Regions

| part | median ms | p90 | % of step | level |
| :--- | ---: | ---: | ---: | ---: |
| data | 0.022 | 0.025 | 0.0 | 1 |
| fwd | 37.804 | 38.078 | 29.5 | 1 |
| fwd:embed | 1.090 | 1.145 | 0.8 | 2 |
| fwd:embed.ke | 1.144 | 1.213 | 0.9 | 3 |
| fwd:stack | 6.407 | 6.579 | 5.0 | 1 |
| fwd:block0 | 1.071 | 1.096 | 0.8 | 2 |
| fwd:block0.ln1 | 0.036 | 0.038 | 0.0 | 3 |
| fwd:block0.attn.qkv | 0.070 | 0.074 | 0.1 | 3 |
| fwd:block0.attn.sdpa | 0.676 | 0.686 | 0.5 | 3 |
| fwd:block0.attn.proj | 0.044 | 0.047 | 0.0 | 3 |
| fwd:block0.ln2 | 0.035 | 0.037 | 0.0 | 3 |
| fwd:block0.mlp | 0.187 | 0.195 | 0.1 | 3 |
| fwd:block1 | 1.069 | 1.092 | 0.8 | 2 |
| fwd:block1.ln1 | 0.035 | 0.037 | 0.0 | 3 |
| fwd:block1.attn.qkv | 0.070 | 0.074 | 0.1 | 3 |
| fwd:block1.attn.sdpa | 0.676 | 0.688 | 0.5 | 3 |
| fwd:block1.attn.proj | 0.045 | 0.047 | 0.0 | 3 |
| fwd:block1.ln2 | 0.035 | 0.037 | 0.0 | 3 |
| fwd:block1.mlp | 0.186 | 0.195 | 0.1 | 3 |
| fwd:block2 | 1.071 | 1.096 | 0.8 | 2 |
| fwd:block2.ln1 | 0.035 | 0.037 | 0.0 | 3 |
| fwd:block2.attn.qkv | 0.070 | 0.074 | 0.1 | 3 |
| fwd:block2.attn.sdpa | 0.674 | 0.687 | 0.5 | 3 |
| fwd:block2.attn.proj | 0.044 | 0.047 | 0.0 | 3 |
| fwd:block2.ln2 | 0.034 | 0.037 | 0.0 | 3 |
| fwd:block2.mlp | 0.186 | 0.196 | 0.1 | 3 |
| fwd:block3 | 1.071 | 1.096 | 0.8 | 2 |
| fwd:block3.ln1 | 0.035 | 0.037 | 0.0 | 3 |
| fwd:block3.attn.qkv | 0.069 | 0.074 | 0.1 | 3 |
| fwd:block3.attn.sdpa | 0.672 | 0.688 | 0.5 | 3 |
| fwd:block3.attn.proj | 0.043 | 0.047 | 0.0 | 3 |
| fwd:block3.ln2 | 0.034 | 0.037 | 0.0 | 3 |
| fwd:block3.mlp | 0.184 | 0.196 | 0.1 | 3 |
| fwd:block4 | 1.067 | 1.095 | 0.8 | 2 |
| fwd:block4.ln1 | 0.034 | 0.037 | 0.0 | 3 |
| fwd:block4.attn.qkv | 0.069 | 0.074 | 0.1 | 3 |
| fwd:block4.attn.sdpa | 0.672 | 0.687 | 0.5 | 3 |
| fwd:block4.attn.proj | 0.043 | 0.047 | 0.0 | 3 |
| fwd:block4.ln2 | 0.034 | 0.037 | 0.0 | 3 |
| fwd:block4.mlp | 0.185 | 0.193 | 0.1 | 3 |
| fwd:block5 | 1.064 | 1.093 | 0.8 | 2 |
| fwd:block5.ln1 | 0.034 | 0.037 | 0.0 | 3 |
| fwd:block5.attn.qkv | 0.069 | 0.074 | 0.1 | 3 |
| fwd:block5.attn.sdpa | 0.672 | 0.684 | 0.5 | 3 |
| fwd:block5.attn.proj | 0.043 | 0.047 | 0.0 | 3 |
| fwd:block5.ln2 | 0.034 | 0.036 | 0.0 | 3 |
| fwd:block5.mlp | 0.184 | 0.192 | 0.1 | 3 |
| fwd:head+loss | 30.241 | 30.435 | 23.6 | 2 |
| bwd | 60.278 | 62.129 | 47.0 | 1 |
| bwd:head+loss | 35.451 | 35.680 | 27.7 | 2 |
| bwd:stack | 23.945 | 25.419 | 18.7 | 1 |
| bwd:block5 | 3.867 | 3.932 | 3.0 | 2 |
| bwd.invert:block5 | 1.085 | 1.110 | 0.8 | 3 |
| bwd.invert:block5.ln1 | 0.033 | 0.035 | 0.0 | 3 |
| bwd.invert:block5.attn.qkv | 0.063 | 0.067 | 0.0 | 3 |
| bwd.invert:block5.attn.sdpa | 0.661 | 0.669 | 0.5 | 3 |
| bwd.invert:block5.attn.proj | 0.041 | 0.043 | 0.0 | 3 |
| bwd.invert:block5.ln2 | 0.031 | 0.033 | 0.0 | 3 |
| bwd.invert:block5.mlp | 0.174 | 0.182 | 0.1 | 3 |
| bwd.recompute:block5 | 1.088 | 1.112 | 0.8 | 3 |
| bwd.recompute:block5.ln1 | 0.033 | 0.035 | 0.0 | 3 |
| bwd.recompute:block5.attn.qkv | 0.063 | 0.066 | 0.0 | 3 |
| bwd.recompute:block5.attn.sdpa | 0.664 | 0.672 | 0.5 | 3 |
| bwd.recompute:block5.attn.proj | 0.041 | 0.043 | 0.0 | 3 |
| bwd.recompute:block5.ln2 | 0.031 | 0.033 | 0.0 | 3 |
| bwd.recompute:block5.mlp | 0.174 | 0.181 | 0.1 | 3 |
| bwd:block5.grad | 1.843 | 1.883 | 1.4 | 3 |
| bwd:block4 | 3.873 | 4.059 | 3.0 | 2 |
| bwd.invert:block4 | 1.086 | 1.115 | 0.8 | 3 |
| bwd.invert:block4.ln1 | 0.033 | 0.035 | 0.0 | 3 |
| bwd.invert:block4.attn.qkv | 0.063 | 0.068 | 0.0 | 3 |
| bwd.invert:block4.attn.sdpa | 0.662 | 0.672 | 0.5 | 3 |
| bwd.invert:block4.attn.proj | 0.041 | 0.043 | 0.0 | 3 |
| bwd.invert:block4.ln2 | 0.032 | 0.034 | 0.0 | 3 |
| bwd.invert:block4.mlp | 0.175 | 0.182 | 0.1 | 3 |
| bwd.recompute:block4 | 1.088 | 1.117 | 0.8 | 3 |
| bwd.recompute:block4.ln1 | 0.033 | 0.035 | 0.0 | 3 |
| bwd.recompute:block4.attn.qkv | 0.063 | 0.068 | 0.0 | 3 |
| bwd.recompute:block4.attn.sdpa | 0.663 | 0.674 | 0.5 | 3 |
| bwd.recompute:block4.attn.proj | 0.041 | 0.043 | 0.0 | 3 |
| bwd.recompute:block4.ln2 | 0.031 | 0.033 | 0.0 | 3 |
| bwd.recompute:block4.mlp | 0.174 | 0.182 | 0.1 | 3 |
| bwd:block4.grad | 1.842 | 1.903 | 1.4 | 3 |
| bwd:block3 | 3.906 | 4.330 | 3.0 | 2 |
| bwd.invert:block3 | 1.087 | 1.171 | 0.8 | 3 |
| bwd.invert:block3.ln1 | 0.033 | 0.039 | 0.0 | 3 |
| bwd.invert:block3.attn.qkv | 0.064 | 0.073 | 0.0 | 3 |
| bwd.invert:block3.attn.sdpa | 0.661 | 0.688 | 0.5 | 3 |
| bwd.invert:block3.attn.proj | 0.041 | 0.049 | 0.0 | 3 |
| bwd.invert:block3.ln2 | 0.032 | 0.039 | 0.0 | 3 |
| bwd.invert:block3.mlp | 0.175 | 0.203 | 0.1 | 3 |
| bwd.recompute:block3 | 1.087 | 1.213 | 0.8 | 3 |
| bwd.recompute:block3.ln1 | 0.033 | 0.041 | 0.0 | 3 |
| bwd.recompute:block3.attn.qkv | 0.064 | 0.079 | 0.0 | 3 |
| bwd.recompute:block3.attn.sdpa | 0.662 | 0.704 | 0.5 | 3 |
| bwd.recompute:block3.attn.proj | 0.041 | 0.050 | 0.0 | 3 |
| bwd.recompute:block3.ln2 | 0.032 | 0.040 | 0.0 | 3 |
| bwd.recompute:block3.mlp | 0.174 | 0.208 | 0.1 | 3 |
| bwd:block3.grad | 1.846 | 2.053 | 1.4 | 3 |
| bwd:block2 | 4.061 | 4.373 | 3.2 | 2 |
| bwd.invert:block2 | 1.095 | 1.212 | 0.9 | 3 |
| bwd.invert:block2.ln1 | 0.033 | 0.041 | 0.0 | 3 |
| bwd.invert:block2.attn.qkv | 0.064 | 0.079 | 0.1 | 3 |
| bwd.invert:block2.attn.sdpa | 0.663 | 0.702 | 0.5 | 3 |
| bwd.invert:block2.attn.proj | 0.041 | 0.051 | 0.0 | 3 |
| bwd.invert:block2.ln2 | 0.032 | 0.041 | 0.0 | 3 |
| bwd.invert:block2.mlp | 0.182 | 0.208 | 0.1 | 3 |
| bwd.recompute:block2 | 1.151 | 1.216 | 0.9 | 3 |
| bwd.recompute:block2.ln1 | 0.037 | 0.041 | 0.0 | 3 |
| bwd.recompute:block2.attn.qkv | 0.071 | 0.080 | 0.1 | 3 |
| bwd.recompute:block2.attn.sdpa | 0.682 | 0.706 | 0.5 | 3 |
| bwd.recompute:block2.attn.proj | 0.047 | 0.051 | 0.0 | 3 |
| bwd.recompute:block2.ln2 | 0.037 | 0.040 | 0.0 | 3 |
| bwd.recompute:block2.mlp | 0.195 | 0.209 | 0.2 | 3 |
| bwd:block2.grad | 1.970 | 2.050 | 1.5 | 3 |
| bwd:block1 | 4.107 | 4.369 | 3.2 | 2 |
| bwd.invert:block1 | 1.163 | 1.214 | 0.9 | 3 |
| bwd.invert:block1.ln1 | 0.039 | 0.042 | 0.0 | 3 |
| bwd.invert:block1.attn.qkv | 0.073 | 0.080 | 0.1 | 3 |
| bwd.invert:block1.attn.sdpa | 0.685 | 0.707 | 0.5 | 3 |
| bwd.invert:block1.attn.proj | 0.047 | 0.051 | 0.0 | 3 |
| bwd.invert:block1.ln2 | 0.037 | 0.041 | 0.0 | 3 |
| bwd.invert:block1.mlp | 0.197 | 0.207 | 0.2 | 3 |
| bwd.recompute:block1 | 1.168 | 1.216 | 0.9 | 3 |
| bwd.recompute:block1.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.recompute:block1.attn.qkv | 0.074 | 0.079 | 0.1 | 3 |
| bwd.recompute:block1.attn.sdpa | 0.688 | 0.706 | 0.5 | 3 |
| bwd.recompute:block1.attn.proj | 0.047 | 0.051 | 0.0 | 3 |
| bwd.recompute:block1.ln2 | 0.037 | 0.040 | 0.0 | 3 |
| bwd.recompute:block1.mlp | 0.197 | 0.209 | 0.2 | 3 |
| bwd:block1.grad | 1.970 | 2.053 | 1.5 | 3 |
| bwd:block0 | 4.104 | 4.342 | 3.2 | 2 |
| bwd.invert:block0 | 1.165 | 1.213 | 0.9 | 3 |
| bwd.invert:block0.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.invert:block0.attn.qkv | 0.074 | 0.080 | 0.1 | 3 |
| bwd.invert:block0.attn.sdpa | 0.687 | 0.705 | 0.5 | 3 |
| bwd.invert:block0.attn.proj | 0.047 | 0.051 | 0.0 | 3 |
| bwd.invert:block0.ln2 | 0.037 | 0.041 | 0.0 | 3 |
| bwd.invert:block0.mlp | 0.195 | 0.207 | 0.2 | 3 |
| bwd.recompute:block0 | 1.168 | 1.209 | 0.9 | 3 |
| bwd.recompute:block0.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.recompute:block0.attn.qkv | 0.074 | 0.079 | 0.1 | 3 |
| bwd.recompute:block0.attn.sdpa | 0.689 | 0.706 | 0.5 | 3 |
| bwd.recompute:block0.attn.proj | 0.047 | 0.051 | 0.0 | 3 |
| bwd.recompute:block0.ln2 | 0.037 | 0.039 | 0.0 | 3 |
| bwd.recompute:block0.mlp | 0.196 | 0.207 | 0.2 | 3 |
| bwd:block0.grad | 1.970 | 2.042 | 1.5 | 3 |
| bwd:embed | 0.883 | 0.960 | 0.7 | 2 |
| data:prefetch | 0.002 | 0.002 | 0.0 | 3 |
| opt | 31.994 | 32.831 | 25.0 | 1 |
| opt:opt.unscale | 1.430 | 1.436 | 1.1 | 2 |
| opt:opt.clip | 2.028 | 2.034 | 1.6 | 2 |
| opt:opt.polar_muon_adamw | 28.527 | 29.356 | 22.3 | 2 |
| opt:opt.muon | 15.129 | 15.983 | 11.8 | 2 |
| opt:opt.muon.ns | 15.721 | 16.562 | 12.3 | 3 |
| opt:opt.adamw | 13.246 | 13.273 | 10.3 | 2 |
| opt:opt.moe_bias | 0.002 | 0.003 | 0.0 | 3 |
| opt:opt.zero_grad | 0.002 | 0.003 | 0.0 | 3 |

## Time by part type (sum over layers)

| part type | median ms sum | % of step |
| :--- | ---: | ---: |
| bwd | 60.278 | 47.0 |
| fwd | 37.804 | 29.5 |
| bwd:head+loss | 35.451 | 27.7 |
| opt | 31.994 | 25.0 |
| fwd:head+loss | 30.241 | 23.6 |
| opt:opt.polar_muon_adamw | 28.527 | 22.3 |
| bwd:stack | 23.945 | 18.7 |
| bwd:block* | 23.918 | 18.7 |
| opt:opt.muon.ns | 15.721 | 12.3 |
| opt:opt.muon | 15.129 | 11.8 |
| opt:opt.adamw | 13.246 | 10.3 |
| bwd:block*.grad | 11.442 | 8.9 |
| bwd.recompute:block* | 6.750 | 5.3 |
| bwd.invert:block* | 6.681 | 5.2 |
| fwd:block* | 6.413 | 5.0 |
| fwd:stack | 6.407 | 5.0 |
| bwd.recompute:block*.attn.sdpa | 4.048 | 3.2 |
| fwd:block*.attn.sdpa | 4.041 | 3.2 |
| bwd.invert:block*.attn.sdpa | 4.019 | 3.1 |
| opt:opt.clip | 2.028 | 1.6 |
| opt:opt.unscale | 1.430 | 1.1 |
| fwd:embed.ke | 1.144 | 0.9 |
| fwd:block*.mlp | 1.113 | 0.9 |
| bwd.recompute:block*.mlp | 1.111 | 0.9 |
| bwd.invert:block*.mlp | 1.097 | 0.9 |
| fwd:embed | 1.090 | 0.8 |
| bwd:embed | 0.883 | 0.7 |
| fwd:block*.attn.qkv | 0.416 | 0.3 |
| bwd.recompute:block*.attn.qkv | 0.409 | 0.3 |
| bwd.invert:block*.attn.qkv | 0.402 | 0.3 |
| bwd.recompute:block*.attn.proj | 0.264 | 0.2 |
| fwd:block*.attn.proj | 0.262 | 0.2 |
| bwd.invert:block*.attn.proj | 0.258 | 0.2 |
| bwd.recompute:block*.ln1 | 0.214 | 0.2 |
| bwd.invert:block*.ln1 | 0.209 | 0.2 |
| fwd:block*.ln1 | 0.209 | 0.2 |
| bwd.recompute:block*.ln2 | 0.205 | 0.2 |
| fwd:block*.ln2 | 0.205 | 0.2 |
| bwd.invert:block*.ln2 | 0.201 | 0.2 |
| data | 0.022 | 0.0 |
| data:prefetch | 0.002 | 0.0 |
| opt:opt.moe_bias | 0.002 | 0.0 |
| opt:opt.zero_grad | 0.002 | 0.0 |

## Five slowest leaf parts

1. `opt:opt.muon.ns` — 15.721 ms (12.3% of step)
2. `bwd:block2.grad` — 1.970 ms (1.5% of step)
3. `bwd:block1.grad` — 1.970 ms (1.5% of step)
4. `bwd:block0.grad` — 1.970 ms (1.5% of step)
5. `bwd:block3.grad` — 1.846 ms (1.4% of step)
