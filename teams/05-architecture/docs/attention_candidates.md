# Attention candidates, week 2

Owner: Revant Gupta. Written 4 Nov 2026.
Task 2 of the TSAI G5 week-2 note (31 Oct): at most four arms, each with a layer pattern, a window size, a position method and a reason.
These are rows attn-1 to attn-4 of `experiments/plan_v1.md`. attn-0 is the plan's baseline. This file names the arms. It does not record results. Results go in `experiments/results_v1.md`.

## What every arm keeps

Every arm is `configs/arms/t2.yaml` with one change. T2: d_model 512, 8 layers, 8 query heads, 2 KV heads, head dim 64, context 2,048, 16 routed experts, 1 shared, top-2, SwiGLU, dense untied output head, `embedding: ke1`.

- Budget from `plan_v1.md`: batch 8, 16,384 tokens per step, 1,221 steps, seeds 1234, 1235, 1236, bf16, 90 min per run.
- Metric: the three-group bits per byte of `plan_v1.md` on the file named by `results/heldout_v1.sha256`. Every slice is reported.
- `rope_theta` 10000, from pull request 253. That is a TSAI test value, not a config v1 decision. No arm runs before 253 is merged.
- Learning rate: the EXP-1 winner. If EXP-1 has no winner when the job is filed, 1e-3, and the run file says the comparison is not final.

`G` is a full causal layer. `L` is a sliding-window layer: a token sees itself and the W − 1 tokens before it. Layers are listed from layer 0.

## The arms

| Arm | Layer pattern | Window size | Position method | The one change from attn-0 | Run file (added with its job request) |
|---|---|---|---|---|---|
| attn-0 | G G G G G G G G | 2,048 (= context) | RoPE on all 64 dims | none, the baseline | `configs/arms/t2.yaml` |
| attn-1 | G G G G G G G G | 2,048 (= context) | RoPE on all 64 dims | 1 KV head instead of 2 (MQA) | `configs/arms/attn1_mqa.yaml` |
| attn-2 | L L L G L L L G | 128 on `L`, 2,048 on `G` | RoPE on all 64 dims | `L` layers with a learned sink | `configs/arms/attn2_swa128_sink.yaml` |
| attn-3 | G G G G G G G G | 2,048 (= context) | RoPE on 32 of 64 dims, 32 dims unrotated | partial RoPE | `configs/arms/attn3_prope_half.yaml` |
| attn-4 | G G G G G G G G | 2,048 (= context) | RoPE on all 64 dims | sigmoid gate on the attention output | `configs/arms/attn4_gate.yaml` |

KV cache per token in bf16, all 8 layers:

| Arm | Grows with context | Fixed per sequence |
|---|---|---|
| attn-0 | 4 KiB | none |
| attn-1 | 2 KiB | none |
| attn-2 | 1 KiB (2 `G` layers) | 384 KiB (6 `L` layers × 128 tokens) |
| attn-3 | 4 KiB | none |
| attn-4 | 4 KiB | none |

## Why each arm

**attn-0.** The 31 Oct test-size line fixes GQA with RoPE. Full attention on every layer is the reference for each other arm.

**attn-1, MQA.** It halves the KV cache, and it is the only arm the harness runs today. Recent models share K and V across many query heads: DeepSeek-V4.1-Flash uses 1 KV head for 64 query heads, MiniMax-M3 4 for 64, and Qwen3.8-Flash-Next 2 for 24 (each model's `config.json`). No report gives a quality ablation of the KV head count, so this arm measures it. The 31 Oct note says to keep the sizes fixed and change one value. This arm changes `n_kv_head` from 2 to 1 and nothing else. The K and V projections lose 65,536 weights per layer.

**attn-2, sliding window with a sink.** Session 8 §16: GQA alone is not enough for the V5 target, because every layer's cache still grows with the context. A sliding-window layer keeps at most W tokens. The MiMo-V2-Flash report (arXiv 2601.02780, Table 2; the MiMo-V2.6 report cites it for this design) tested this on a 32B model with 250B tokens:

| Model | MMLU | BBH | GSM8K |
|---|---|---|---|
| All full attention | 57.3 | 54.7 | 34.2 |
| Window 128, no sink | 54.9 | 52.4 | 36.9 |
| Window 128, with sink | 58.3 | 56.1 | 36.9 |
| Window 512, with sink | 58.3 | 54.9 | 37.9 |

Without the sink the window loses on MMLU and BBH. With the sink it matches or beats full attention on every column. So the window and the sink are one change here: a new `L` layer type. Testing the window without the sink would repeat a result that is already known to lose. After extension to 32K, window 128 beat window 512 (NoLiMa 51.2 against 38.5, MRCR 34.4 against 19.6). That is why the window is 128 and not 512. 128 is a candidate value for this test. It is not copied into `config_v0.yaml`.

The pattern is 3 `L` to 1 `G` and ends on a `G` layer. MiMo-V2.6 uses 5:1 and 6:1, but 8 layers would then have one `G` layer. 3:1 is the local-to-global schedule of Laguna and Mellum2 (gallery `layer_mix`), and the linear-to-full schedule of Qwen3.8 and GLM-5.3-Flash (`layer_types` in their `config.json`). The Kimi Linear ratio ablation also favours 3:1 (validation perplexity 5.65 at 3:1, 5.66 at 1:1, 5.70 at 7:1, 5.77 all full). Those numbers are quoted from a third-party write-up of that paper, and the ablation is for linear layers, not windows.

The sink is one learned logit per query head on `L` layers only, as in MiMo-V2.6 (`add_swa_attention_sink_bias` true, `add_full_attention_sink_bias` false). It joins the softmax and adds no value vector. It starts at 0.

**attn-3, partial RoPE.** Every RoPE model checked rotates 64 dimensions of each head and leaves the rest unrotated: DeepSeek-V4.1-Flash 64 of 512, MiniMax-M3 64 of 128, Qwen3.8-Flash-Next 64 of 256, MiMo-V2.6 64 of 192 (`config.json` of each). Session 8 §8 gives the reason: unrotated dimensions compare content at any distance. Week 3 asks Team 5 for a long-context plan, and the position method is what that plan extends. This arm measures what partial rotation costs at 2,048 tokens before week 3 depends on it. It rotates the first 32 of 64 dimensions, with frequencies taken over those 32. The Qwen3.8 report says NoPE and RoPE look the same in pre-training, but NoPE gives much more endless generation after post-training. So this arm keeps half of RoPE and does not test NoPE.

**attn-4, gated attention.** Each head's output is multiplied by a sigmoid gate computed from the layer input, before the output projection: `o = W_o(σ(W_g x) ⊙ attention(x))`. Qwen3.8-Flash-Next uses it (`output_gate_type` sigmoid in its `config.json`). The architecture gallery also lists it for Qwen3.6, Kimi K3, Laguna and Step-5. No report checked ablates the gate on softmax attention. The nearest is the Kimi Linear ablation of the same gate on its linear layers: validation perplexity 5.65 with it, 5.67 without (quoted from a third-party write-up). The Qwen3.8-Flash-Next report ties its gates to stability: a full-scale run had no loss spike without qk-clip, and its gated norm, a gate of the same kind on the residual stream, cut the spike rate from 32.0 to 3.2 per 10,000 steps at 3 times the best learning rate. This arm tests the gate on its own. `W_g` is 512 × 512 per layer, 2.1M weights in all (0.9% of T2).

## Pass rule

`plan_v1.md` lets an arm set its own rule. attn-1, attn-2 and attn-3 save cache or prepare long context. Bits per byte at 2,048 cannot show that saving. Each of the three passes if its three-group mean, its code mean and its Indic mean are each not worse than attn-0 by more than the larger seed spread of the two arms. TSAI decides at Gate 2 whether a passing arm goes into config v1.

attn-4 adds weights, so it uses the plan's winner rule against attn-0.

## Harness changes before the jobs

attn-1 runs on the current harness. `harness/week2/config.py` already accepts any `n_kv_head` that divides `n_head`.

attn-2 to attn-4 need these changes to `GQA` in `harness/week2/model.py` and to the checks in `harness/week2/config.py`:

1. `model.attn_pattern`: a list of `G` or `L`, one per layer. The length must equal `n_layer`. If it is not set, every layer is `G`.
2. `model.attn_window`: an integer from 1 to `block_size`. Used only by `L` layers.
3. `model.attn_sink`: true or false. Used only by `L` layers.
4. `model.rotary_fraction`: already a key, fixed at 1.0 today. Allow 0.5: rotate the first `2 × floor(fraction × head_dim / 2)` dimensions and pass the rest through.
5. `model.attn_gate`: true or false.

Tests that must pass:

- `attn_window` equal to `block_size` with no sink gives the same output as a `G` layer, bit for bit.
- `attn_window` 1 gives each token only itself.
- A sink logit of −inf gives the same output as no sink, bit for bit.
- `rotary_fraction` 1.0 gives the same output as the current harness, bit for bit.
- `attn_gate` false gives the same output as the current harness, bit for bit.

The window mask and the sink column go on the existing fp32 score matrix, so attn-2 does the same work as attn-0. The EXP-2 AdamW smoke on an L4 took about 3.9 s per T2 step, about 79 min for 1,221 steps. All five arms should fit the 90 min cap. The CPU log in each job request and the returned job log confirm it.

Team 6 times each arm. Their loader needs the same keys before an attention arm has a step time.

## Jobs

- attn-0 is `configs/arms/t2.yaml`, the same file as exp3-base. If the lead agrees, one set of three seeds serves both rows.
- attn-1 can be filed on Wed 4 Nov with a CPU log of `harness/train_week2.py`.
- attn-2, attn-3 and attn-4 are filed after the harness pull request passes its tests on CPU.
- 5 arms × 3 seeds × about 80 min is about 20 GPU hours, or about 16 if attn-0 is shared with exp3-base.
- Each job writes metrics only, 50 MB or less.
- TSAI suggested on 2 Nov that Deepjyoti run the third seed of the attention arms. The lead assigns it.

## What the held-out file can show

A window changes the result only for tokens more than W positions into a document. Each document is in its own window, and a document longer than 2,048 tokens is cut into separate windows (`harness/week2/data.py`). No arm sees past 2,048 tokens.

UTF-8 bytes per document in `heldout_v1/data/heldout_v1.jsonl` (1,059 documents):

| Slice group | Median bytes | 90th percentile bytes |
|---|---|---|
| English (c4-val) | 1,020 | 4,470 |
| Code (vault-*) | 303 to 780 | 698 to 1,955 |
| Indic (fw2-*-test, 11 languages) | 3,198 to 8,634 | 6,756 to 26,456 |
| Math (owm-test) | 2,675 | 11,480 |
| Science (pes2o-val) | 1,411 | 2,043 |

Code documents are the shortest, so attn-2 should change code the least. Indic documents are the longest, so attn-2 is mostly a test on Indic text. The token count per document comes from the job log, not from this table.

## Not in this plan

- Sparse attention (DeepSeek Sparse Attention, MiniMax Sparse Attention, Qwen Sparse Attention, DeepSeek CSA2). Each keeps 2,048 tokens per query in its released config (`index_topk`, `sparse_topk_blocks` × `sparse_block_size`, `indexer_budget`). At a context of 2,048 that is every token, so the arm would equal attn-0. The MiniMax and Qwen reports also need a trained indexer with a KL loss and a dense warm-up. This belongs to the week-3 long-context plan.
- Linear-attention layers (Gated DeltaNet, Kimi Delta Attention). The Qwen3.8 report gives the largest gain of any design checked (mean 53.81 against 49.87 for full attention, 25B-A3B model, 480B tokens). They need a chunked kernel, and the harness accepts eager attention only. A candidate for week 3 if TSAI allows the kernel.
- MLA. The GLM-5 report (Table 1) has MLA below GQA-8 on BBH (48.9 against 53.3) and HumanEval (33.5 against 38.5) unless Muon is split per head. Its gain is cache size.
- QK-norm and soft-capping. They are stability choices. A run of 1,221 steps is too short to show the divergence they prevent. No report checked ablates QK-norm.
- Learned relative-position bias (Inkling) and NoPE. Inkling reports no numbers. NoPE has the endless-generation result above.
