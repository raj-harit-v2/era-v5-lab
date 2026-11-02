# Bench report — t4_headloss_chunked

**GPU:** Tesla T4  |  **dtype:** fp16  |  **B x T:** 8 x 256  |  **torch:** 2.11.0+cu128
**commit:** `7bc8beecefd0ab6584bfa233fca38d02710af412`  |  **tag:** t4_headloss_chunked

## Step (clean)

- median: 182.698 ms
- p10..p90: 182.024 .. 184.057 ms
- tokens/s: 11,210
- MFU: 4.3%  |  HFU: 6.0%

## Diagnostics

### CUDA timing-event allocations

- [OK] clean: events_created_during_steps=0
- [OK] layer: events_created_during_steps=0
- [OK] layer.inner_pass: events_created_during_steps=0

### Benchmark warnings

- [warn] 18 of 18 samples during the clean steps had a slowdown reason (SwPowerCap): may miss the 5% check
- [warn] GPU slowed down while the steps ran (SwPowerCap): a shared or throttled GPU misses the 5% check
- [warn] rule 3b: checkpoint not measured; add checkpoint to --modes
- [warn] 1 gated part(s) have p10..p90 spread > 10%, so may miss the 5% check: data

## Regions

| part | median ms | p90 | % of step | level |
| :--- | ---: | ---: | ---: | ---: |
| data | 0.021 | 0.024 | 0.0 | 1 |
| fwd | 39.627 | 40.003 | 21.7 | 1 |
| fwd:embed | 1.212 | 1.247 | 0.7 | 2 |
| fwd:embed.ke | 1.155 | 1.177 | 0.6 | 3 |
| fwd:stack | 6.762 | 6.853 | 3.7 | 1 |
| fwd:block0 | 1.126 | 1.143 | 0.6 | 2 |
| fwd:block0.ln1 | 0.037 | 0.037 | 0.0 | 3 |
| fwd:block0.attn.qkv | 0.071 | 0.073 | 0.0 | 3 |
| fwd:block0.attn.sdpa | 0.678 | 0.683 | 0.4 | 3 |
| fwd:block0.attn.proj | 0.045 | 0.046 | 0.0 | 3 |
| fwd:block0.ln2 | 0.035 | 0.036 | 0.0 | 3 |
| fwd:block0.mlp | 0.188 | 0.192 | 0.1 | 3 |
| fwd:block1 | 1.124 | 1.141 | 0.6 | 2 |
| fwd:block1.ln1 | 0.035 | 0.036 | 0.0 | 3 |
| fwd:block1.attn.qkv | 0.072 | 0.074 | 0.0 | 3 |
| fwd:block1.attn.sdpa | 0.678 | 0.682 | 0.4 | 3 |
| fwd:block1.attn.proj | 0.045 | 0.047 | 0.0 | 3 |
| fwd:block1.ln2 | 0.035 | 0.036 | 0.0 | 3 |
| fwd:block1.mlp | 0.188 | 0.192 | 0.1 | 3 |
| fwd:block2 | 1.125 | 1.142 | 0.6 | 2 |
| fwd:block2.ln1 | 0.035 | 0.036 | 0.0 | 3 |
| fwd:block2.attn.qkv | 0.072 | 0.074 | 0.0 | 3 |
| fwd:block2.attn.sdpa | 0.676 | 0.680 | 0.4 | 3 |
| fwd:block2.attn.proj | 0.044 | 0.045 | 0.0 | 3 |
| fwd:block2.ln2 | 0.034 | 0.035 | 0.0 | 3 |
| fwd:block2.mlp | 0.188 | 0.190 | 0.1 | 3 |
| fwd:block3 | 1.124 | 1.141 | 0.6 | 2 |
| fwd:block3.ln1 | 0.035 | 0.036 | 0.0 | 3 |
| fwd:block3.attn.qkv | 0.070 | 0.073 | 0.0 | 3 |
| fwd:block3.attn.sdpa | 0.676 | 0.680 | 0.4 | 3 |
| fwd:block3.attn.proj | 0.044 | 0.045 | 0.0 | 3 |
| fwd:block3.ln2 | 0.035 | 0.035 | 0.0 | 3 |
| fwd:block3.mlp | 0.187 | 0.190 | 0.1 | 3 |
| fwd:block4 | 1.125 | 1.142 | 0.6 | 2 |
| fwd:block4.ln1 | 0.035 | 0.035 | 0.0 | 3 |
| fwd:block4.attn.qkv | 0.070 | 0.072 | 0.0 | 3 |
| fwd:block4.attn.sdpa | 0.675 | 0.680 | 0.4 | 3 |
| fwd:block4.attn.proj | 0.044 | 0.045 | 0.0 | 3 |
| fwd:block4.ln2 | 0.035 | 0.035 | 0.0 | 3 |
| fwd:block4.mlp | 0.187 | 0.190 | 0.1 | 3 |
| fwd:block5 | 1.122 | 1.139 | 0.6 | 2 |
| fwd:block5.ln1 | 0.035 | 0.036 | 0.0 | 3 |
| fwd:block5.attn.qkv | 0.070 | 0.072 | 0.0 | 3 |
| fwd:block5.attn.sdpa | 0.674 | 0.678 | 0.4 | 3 |
| fwd:block5.attn.proj | 0.044 | 0.045 | 0.0 | 3 |
| fwd:block5.ln2 | 0.035 | 0.035 | 0.0 | 3 |
| fwd:block5.mlp | 0.186 | 0.190 | 0.1 | 3 |
| fwd:head+loss | 31.614 | 31.928 | 17.3 | 2 |
| bwd | 111.341 | 112.161 | 60.9 | 1 |
| bwd:head+loss | 84.093 | 84.619 | 46.0 | 2 |
| bwd:stack | 26.249 | 26.580 | 14.4 | 1 |
| bwd:block5 | 4.379 | 4.444 | 2.4 | 2 |
| bwd.invert:block5 | 1.186 | 1.200 | 0.6 | 3 |
| bwd.invert:block5.ln1 | 0.040 | 0.041 | 0.0 | 3 |
| bwd.invert:block5.attn.qkv | 0.076 | 0.079 | 0.0 | 3 |
| bwd.invert:block5.attn.sdpa | 0.694 | 0.699 | 0.4 | 3 |
| bwd.invert:block5.attn.proj | 0.049 | 0.049 | 0.0 | 3 |
| bwd.invert:block5.ln2 | 0.039 | 0.039 | 0.0 | 3 |
| bwd.invert:block5.mlp | 0.201 | 0.205 | 0.1 | 3 |
| bwd.recompute:block5 | 1.188 | 1.203 | 0.7 | 3 |
| bwd.recompute:block5.ln1 | 0.040 | 0.041 | 0.0 | 3 |
| bwd.recompute:block5.attn.qkv | 0.076 | 0.078 | 0.0 | 3 |
| bwd.recompute:block5.attn.sdpa | 0.696 | 0.702 | 0.4 | 3 |
| bwd.recompute:block5.attn.proj | 0.049 | 0.049 | 0.0 | 3 |
| bwd.recompute:block5.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.recompute:block5.mlp | 0.201 | 0.205 | 0.1 | 3 |
| bwd:block5.grad | 1.998 | 2.024 | 1.1 | 3 |
| bwd:block4 | 4.375 | 4.435 | 2.4 | 2 |
| bwd.invert:block4 | 1.181 | 1.199 | 0.6 | 3 |
| bwd.invert:block4.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.invert:block4.attn.qkv | 0.075 | 0.078 | 0.0 | 3 |
| bwd.invert:block4.attn.sdpa | 0.692 | 0.698 | 0.4 | 3 |
| bwd.invert:block4.attn.proj | 0.048 | 0.049 | 0.0 | 3 |
| bwd.invert:block4.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.invert:block4.mlp | 0.201 | 0.203 | 0.1 | 3 |
| bwd.recompute:block4 | 1.181 | 1.198 | 0.6 | 3 |
| bwd.recompute:block4.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.recompute:block4.attn.qkv | 0.075 | 0.077 | 0.0 | 3 |
| bwd.recompute:block4.attn.sdpa | 0.693 | 0.699 | 0.4 | 3 |
| bwd.recompute:block4.attn.proj | 0.048 | 0.049 | 0.0 | 3 |
| bwd.recompute:block4.ln2 | 0.037 | 0.039 | 0.0 | 3 |
| bwd.recompute:block4.mlp | 0.199 | 0.203 | 0.1 | 3 |
| bwd:block4.grad | 1.995 | 2.024 | 1.1 | 3 |
| bwd:block3 | 4.376 | 4.436 | 2.4 | 2 |
| bwd.invert:block3 | 1.183 | 1.201 | 0.6 | 3 |
| bwd.invert:block3.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.invert:block3.attn.qkv | 0.076 | 0.078 | 0.0 | 3 |
| bwd.invert:block3.attn.sdpa | 0.693 | 0.700 | 0.4 | 3 |
| bwd.invert:block3.attn.proj | 0.049 | 0.050 | 0.0 | 3 |
| bwd.invert:block3.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.invert:block3.mlp | 0.201 | 0.205 | 0.1 | 3 |
| bwd.recompute:block3 | 1.184 | 1.202 | 0.6 | 3 |
| bwd.recompute:block3.ln1 | 0.040 | 0.041 | 0.0 | 3 |
| bwd.recompute:block3.attn.qkv | 0.076 | 0.078 | 0.0 | 3 |
| bwd.recompute:block3.attn.sdpa | 0.694 | 0.700 | 0.4 | 3 |
| bwd.recompute:block3.attn.proj | 0.049 | 0.050 | 0.0 | 3 |
| bwd.recompute:block3.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.recompute:block3.mlp | 0.200 | 0.205 | 0.1 | 3 |
| bwd:block3.grad | 1.994 | 2.021 | 1.1 | 3 |
| bwd:block2 | 4.379 | 4.432 | 2.4 | 2 |
| bwd.invert:block2 | 1.181 | 1.198 | 0.6 | 3 |
| bwd.invert:block2.ln1 | 0.040 | 0.041 | 0.0 | 3 |
| bwd.invert:block2.attn.qkv | 0.076 | 0.078 | 0.0 | 3 |
| bwd.invert:block2.attn.sdpa | 0.692 | 0.698 | 0.4 | 3 |
| bwd.invert:block2.attn.proj | 0.048 | 0.049 | 0.0 | 3 |
| bwd.invert:block2.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.invert:block2.mlp | 0.200 | 0.205 | 0.1 | 3 |
| bwd.recompute:block2 | 1.184 | 1.201 | 0.6 | 3 |
| bwd.recompute:block2.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.recompute:block2.attn.qkv | 0.076 | 0.078 | 0.0 | 3 |
| bwd.recompute:block2.attn.sdpa | 0.694 | 0.700 | 0.4 | 3 |
| bwd.recompute:block2.attn.proj | 0.048 | 0.049 | 0.0 | 3 |
| bwd.recompute:block2.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.recompute:block2.mlp | 0.200 | 0.205 | 0.1 | 3 |
| bwd:block2.grad | 1.999 | 2.028 | 1.1 | 3 |
| bwd:block1 | 4.367 | 4.411 | 2.4 | 2 |
| bwd.invert:block1 | 1.180 | 1.198 | 0.6 | 3 |
| bwd.invert:block1.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.invert:block1.attn.qkv | 0.074 | 0.077 | 0.0 | 3 |
| bwd.invert:block1.attn.sdpa | 0.691 | 0.697 | 0.4 | 3 |
| bwd.invert:block1.attn.proj | 0.048 | 0.049 | 0.0 | 3 |
| bwd.invert:block1.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.invert:block1.mlp | 0.200 | 0.204 | 0.1 | 3 |
| bwd.recompute:block1 | 1.184 | 1.200 | 0.6 | 3 |
| bwd.recompute:block1.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.recompute:block1.attn.qkv | 0.076 | 0.078 | 0.0 | 3 |
| bwd.recompute:block1.attn.sdpa | 0.694 | 0.700 | 0.4 | 3 |
| bwd.recompute:block1.attn.proj | 0.048 | 0.049 | 0.0 | 3 |
| bwd.recompute:block1.ln2 | 0.038 | 0.039 | 0.0 | 3 |
| bwd.recompute:block1.mlp | 0.199 | 0.204 | 0.1 | 3 |
| bwd:block1.grad | 1.995 | 2.023 | 1.1 | 3 |
| bwd:block0 | 4.330 | 4.405 | 2.4 | 2 |
| bwd.invert:block0 | 1.172 | 1.192 | 0.6 | 3 |
| bwd.invert:block0.ln1 | 0.039 | 0.041 | 0.0 | 3 |
| bwd.invert:block0.attn.qkv | 0.075 | 0.078 | 0.0 | 3 |
| bwd.invert:block0.attn.sdpa | 0.690 | 0.697 | 0.4 | 3 |
| bwd.invert:block0.attn.proj | 0.047 | 0.049 | 0.0 | 3 |
| bwd.invert:block0.ln2 | 0.037 | 0.039 | 0.0 | 3 |
| bwd.invert:block0.mlp | 0.196 | 0.202 | 0.1 | 3 |
| bwd.recompute:block0 | 1.167 | 1.177 | 0.6 | 3 |
| bwd.recompute:block0.ln1 | 0.039 | 0.040 | 0.0 | 3 |
| bwd.recompute:block0.attn.qkv | 0.074 | 0.076 | 0.0 | 3 |
| bwd.recompute:block0.attn.sdpa | 0.689 | 0.694 | 0.4 | 3 |
| bwd.recompute:block0.attn.proj | 0.047 | 0.047 | 0.0 | 3 |
| bwd.recompute:block0.ln2 | 0.037 | 0.037 | 0.0 | 3 |
| bwd.recompute:block0.mlp | 0.195 | 0.198 | 0.1 | 3 |
| bwd:block0.grad | 1.968 | 1.974 | 1.1 | 3 |
| bwd:embed | 0.963 | 0.989 | 0.5 | 2 |
| data:prefetch | 0.002 | 0.003 | 0.0 | 3 |
| opt | 33.062 | 33.348 | 18.1 | 1 |
| opt:opt.unscale | 1.409 | 1.415 | 0.8 | 2 |
| opt:opt.clip | 2.016 | 2.020 | 1.1 | 2 |
| opt:opt.polar_muon_adamw | 29.625 | 29.910 | 16.2 | 2 |
| opt:opt.muon | 16.284 | 16.522 | 8.9 | 2 |
| opt:opt.muon.ns | 15.876 | 15.945 | 8.7 | 3 |
| opt:opt.adamw | 13.195 | 13.211 | 7.2 | 2 |
| opt:opt.moe_bias | 0.002 | 0.003 | 0.0 | 3 |
| opt:opt.zero_grad | 0.002 | 0.003 | 0.0 | 3 |

## Time by part type (sum over layers)

| part type | median ms sum | % of step |
| :--- | ---: | ---: |
| bwd | 111.341 | 60.9 |
| bwd:head+loss | 84.093 | 46.0 |
| fwd | 39.627 | 21.7 |
| opt | 33.062 | 18.1 |
| fwd:head+loss | 31.614 | 17.3 |
| opt:opt.polar_muon_adamw | 29.625 | 16.2 |
| bwd:stack | 26.249 | 14.4 |
| bwd:block* | 26.206 | 14.3 |
| opt:opt.muon | 16.284 | 8.9 |
| opt:opt.muon.ns | 15.876 | 8.7 |
| opt:opt.adamw | 13.195 | 7.2 |
| bwd:block*.grad | 11.949 | 6.5 |
| bwd.recompute:block* | 7.089 | 3.9 |
| bwd.invert:block* | 7.082 | 3.9 |
| fwd:stack | 6.762 | 3.7 |
| fwd:block* | 6.746 | 3.7 |
| bwd.recompute:block*.attn.sdpa | 4.159 | 2.3 |
| bwd.invert:block*.attn.sdpa | 4.153 | 2.3 |
| fwd:block*.attn.sdpa | 4.058 | 2.2 |
| opt:opt.clip | 2.016 | 1.1 |
| opt:opt.unscale | 1.409 | 0.8 |
| fwd:embed | 1.212 | 0.7 |
| bwd.invert:block*.mlp | 1.198 | 0.7 |
| bwd.recompute:block*.mlp | 1.195 | 0.7 |
| fwd:embed.ke | 1.155 | 0.6 |
| fwd:block*.mlp | 1.125 | 0.6 |
| bwd:embed | 0.963 | 0.5 |
| bwd.invert:block*.attn.qkv | 0.453 | 0.2 |
| bwd.recompute:block*.attn.qkv | 0.452 | 0.2 |
| fwd:block*.attn.qkv | 0.424 | 0.2 |
| bwd.invert:block*.attn.proj | 0.289 | 0.2 |
| bwd.recompute:block*.attn.proj | 0.288 | 0.2 |
| fwd:block*.attn.proj | 0.267 | 0.1 |
| bwd.recompute:block*.ln1 | 0.236 | 0.1 |
| bwd.invert:block*.ln1 | 0.236 | 0.1 |
| bwd.invert:block*.ln2 | 0.227 | 0.1 |
| bwd.recompute:block*.ln2 | 0.225 | 0.1 |
| fwd:block*.ln1 | 0.211 | 0.1 |
| fwd:block*.ln2 | 0.208 | 0.1 |
| data | 0.021 | 0.0 |
| data:prefetch | 0.002 | 0.0 |
| opt:opt.zero_grad | 0.002 | 0.0 |
| opt:opt.moe_bias | 0.002 | 0.0 |

## Five slowest leaf parts

1. `opt:opt.muon.ns` — 15.876 ms (8.7% of step)
2. `bwd:block2.grad` — 1.999 ms (1.1% of step)
3. `bwd:block5.grad` — 1.998 ms (1.1% of step)
4. `bwd:block4.grad` — 1.995 ms (1.1% of step)
5. `bwd:block1.grad` — 1.995 ms (1.1% of step)
