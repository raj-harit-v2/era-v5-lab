# Decisions for config v1

Gate 2, 14 Nov 2026. TSAI signed the optimizer, the attention, the expert count, and the learning rate. Model sizes are not copied in from the test-size line. `embedding.ke2_output_dim` stays empty.

| Setting | Decision | Why |
|---|---|---|
| optim.name | muon | Gate 2, 14 Nov 2026. The optimizer is Muon. A separate Muon matrix rate was not named, so `muon_lr` is not set in config v1. |
| optim.lr | 0.001, provisional | Gate 2 keeps 1e-3 provisional. The T1 table is the measured rate: lowest whole-file val/bpb on seeds 1234, 1235, and 1236, mean 1.9686, SD 0.0070. Three-group, code, and Indic values were not measured. The choice was measured on 245-step T1 runs. |
| moe.n_expert | 16 | Gate 2. 16 routed experts. |
| moe.n_shared | 1 | Gate 2. 1 shared expert. |
| moe.top_k | 2 | Gate 2. Top-2. |
| attention.impl | eager | Gate 2 keeps the v0 attention. RoPE and the window are not copied in. |
| embedding.ke2_output_dim | null | TSAI decides the output head. Every test model uses the dense untied head. |
| model.n_layer, model.d_model, model.n_head, model.d_ff, data.seq_len | null | These stay empty. The T1, T2, and T3 lines are test sizes, not this file. |
| precision | null | Production precision is not chosen. |

EXP-4 is week 3. It is not in this file.

The EXP-2 job in pull request 354 used AdamW 0.001 and Muon `muon_lr` 0.01, with the comparison marked not final. That 0.01 rate is not copied into config v1.