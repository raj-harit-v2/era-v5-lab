# Parallel layouts for config v1: memory, traffic and tokens per second

Owner: Max (G7). Status: **calculated, not yet measured** (14 Nov 2026). The tokens/s columns stay empty until
the job requests below come back. Calculator: [`layout/parallel_layout_v1.py`](../layout/parallel_layout_v1.py),
tests: [`layout/test_parallel_layout_v1.py`](../layout/test_parallel_layout_v1.py). It follows
[`docs/parallel_layout_v1.md`](../docs/parallel_layout_v1.md).

> **In simple words.** A layout is how one training step is split over devices. This file lists the layouts
> for the model that config v1 describes. For each one it gives the memory per device, the bytes each device
> sends, and whether it works with Muon, the optimizer config v1 chose. Only the one-GPU layouts can be
> measured today, so only those have job requests. Every other row is a calculation until a script for it
> exists.

## 1. The model

Config v1 is Team 5's `configs/config_v1.yaml`, merged with PR 447 (commit `aec75af`). It fixes Muon, the v0
attention (eager), 16 routed experts plus 1 shared, top-2, learning rate 1e-3, vocabulary 131,072 and the
Kronecker embedding with 32 byte positions (`embedding.type: kronecker` in config v1; arm value `ke1`, built by
class `KE2` in `model.py`). It leaves the layer count, the width, the heads, the expert width, the
sequence length and the precision empty. Those come from Team 5's two test shapes with 16 + 1 experts, T2 and
T3 (`configs/arms/t2.yaml`, `t3.yaml`). They are test sizes, not config v1. T1 has 8 experts, so v1 refuses it.

The model is Team 5's week-2 model (`harness/week2/model.py`), the one `train_week2.py` trains: no biases,
RMSNorm, GQA with RoPE, SwiGLU experts, the `KE2` input projection, an untied head.

| | T2 | T3 |
|---|---:|---:|
| Layers, width, heads (query/key-value) | 8, 512, 8/2 | 10, 640, 10/2 |
| Sequence, expert width | 2,048, 768 | 2,048, 896 |
| Parameters | 237,052,416 | 391,529,600 |
| of which routed experts | 150,994,944 (64 %) | 275,251,200 (70 %) |
| on Muon (block matrices) / on AdamW (head, KE2 projection, norms) | 165.7M / 71.3M | 302.4M / 89.1M |
| Weights + gradients + optimizer state, one device | 2.91 GiB | 4.71 GiB |
| Muon Newton-Schulz work per optimizer step | 2.26 TFLOP | 5.24 TFLOP |
| Forward + backward of one 16,384-token step (6 × active parameters + attention) | ≈ 11.5 TFLOP | ≈ 16.9 TFLOP |
| Peak, one sequence per forward (b = 1) | 8.1 GiB | 11.5 GiB |

The parameter counts equal Team 5's model built at full size (test `test_param_counts_equal_team5_model_at_full_size`).

## 2. One GPU: the layouts that run today

On one device the layout is the micro-batch split: `b` sequences per forward, `m` forwards per optimizer step.
Team 5's harness runs these with no new code. Each row has its own job request with one command (last column).
All are drafts and not submitted. The T3 jobs wait for Team 5 to add a T3 Muon arm.

Memory in GiB per device. "End of step" is what the harness logs as `gpu_alloc_gb`: the states plus the bf16
logits of the last micro-batch. "Peak" adds the activations, the logits at the end of the forward pass and the
bf16 copies of the weights that autocast keeps.

| Shape | b | m | Tokens/step | End of step | Peak | Tokens/s, measured | `gpu_alloc_gb`, measured | GPU | Job request |
|---|---:|---:|---:|---:|---:|---|---|---|---|
| T2 | 1 | 8 | 16,384 | 3.4 | 8.1 | - | - | - | [t2-b1-m8](../jobs/2026-11-14-layout-t2-muon-b1-m8.md) |
| T2 | 1 | 1 | 2,048 | 3.4 | 8.1 | - | - | - | [t2-b1-m1](../jobs/2026-11-14-layout-t2-muon-b1-m1.md) |
| T2 | 2 | 1 | 4,096 | 3.9 | 12.9 | - | - | - | [t2-b2-m1](../jobs/2026-11-14-layout-t2-muon-b2-m1.md) |
| T2 | 4 | 1 | 8,192 | 4.9 | 22.4 | - | - | - | [t2-b4-m1](../jobs/2026-11-14-layout-t2-muon-b4-m1.md) |
| T2 | 8 | 1 | 16,384 | 6.9 | 41.4 | - | - | - | [t2-b8-m1](../jobs/2026-11-14-layout-t2-muon-b8-m1.md) |
| T2 | 2 | 4 | 16,384 | 3.9 | 12.9 | not requested: needs a Team 5 runtime file | | | - |
| T2 | 4 | 2 | 16,384 | 4.9 | 22.4 | not requested: needs a Team 5 runtime file | | | - |
| T3 | 1 | 8 | 16,384 | 5.2 | 11.5 | - | - | - | [t3-b1-m8](../jobs/2026-11-14-layout-t3-muon-b1-m8.md) |
| T3 | 1 | 1 | 2,048 | 5.2 | 11.5 | - | - | - | [t3-b1-m1](../jobs/2026-11-14-layout-t3-muon-b1-m1.md) |
| T3 | 2 | 1 | 4,096 | 5.7 | 17.4 | - | - | - | [t3-b2-m1](../jobs/2026-11-14-layout-t3-muon-b2-m1.md) |
| T3 | 4 | 1 | 8,192 | 6.7 | 29.4 | - | - | - | [t3-b4-m1](../jobs/2026-11-14-layout-t3-muon-b4-m1.md) |
| T3 | 8 | 1 | 16,384 | 8.7 | 53.3 | - | - | - | [t3-b8-m1](../jobs/2026-11-14-layout-t3-muon-b8-m1.md) |
| T3 | 2 | 4 | 16,384 | 5.7 | 17.4 | not requested: needs a Team 5 runtime file | | | - |
| T3 | 4 | 2 | 16,384 | 6.7 | 29.4 | not requested: needs a Team 5 runtime file | | | - |

The CUDA context and the allocator cache add to these numbers. Leave 1-2 GiB free.

One measurement already exists, for AdamW, not Muon. Team 5's T2 run with AdamW at `b = 1, m = 8` on an
RTX PRO 6000 Blackwell gave about 16,300 tokens/s (median of steps 11-110) and `gpu_alloc_gb` 4.16
(`teams/05-architecture/jobs/evidence/2026-11-10-attention-screen/attn-0/metrics.jsonl`). For that run v1 gives
4.03 GiB at the end of a step, 3 % low.

## 3. Two GPUs: calculated only

No team outside Team 7 has a script that trains Team 5's model on more than one GPU, so these rows have no job
request. Same `b = 1, m = 8` per device as the reference row. GiB per device; "send" is GiB per device per
optimizer step.

The ZeRO-1/2/3 and `tp=2` rows are **reference only**: Muon orthogonalizes each whole matrix, these layouts split
the matrices across devices, and the lab has no distributed Muon. They show what a distributed Muon would buy.
[`docs/parallel_layout_v1.md`](../docs/parallel_layout_v1.md) leaves them out for the same reason (section I).

**T2**

| Layout | Weights | Grads | Optimizer | Peak | Send | Muon | Muon TFLOP per device |
|---|---:|---:|---:|---:|---:|---|---:|
| dp=2 (DDP) | 0.88 | 0.88 | 1.15 | 8.14 | 0.88 | ok | 2.26 |
| dp=2, ZeRO-1 | 0.88 | 0.88 | 0.57 | 7.57 | 0.88 | needs distributed Muon | 2.26 |
| dp=2, ZeRO-2 | 0.88 | 0.44 | 0.57 | 7.12 | 0.88 | needs distributed Muon | 2.26 |
| dp=2, ZeRO-3 | 0.44 | 0.44 | 0.57 | 6.84 | 10.60 | needs distributed Muon | 2.26 |
| tp=2 | 0.72 | 0.72 | 0.86 | 5.08 | 0.50 | needs distributed Muon | 2.26 |
| pp=2 (last stage) | 0.56 | 0.56 | 0.81 | 5.86 | 0.03 | ok | 1.13 |
| cp=2 | 0.88 | 0.88 | 1.15 | 5.74 | 0.98 | ok | 2.26 |
| dp=2, ep=2 | 0.60 | 0.60 | 0.87 | 7.16 | 0.82 | ok | 1.23 |

**T3**

| Layout | Weights | Grads | Optimizer | Peak | Send | Muon | Muon TFLOP per device |
|---|---:|---:|---:|---:|---:|---|---:|
| dp=2 (DDP) | 1.46 | 1.46 | 1.79 | 11.46 | 1.46 | ok | 5.24 |
| dp=2, ZeRO-1 | 1.46 | 1.46 | 0.90 | 10.57 | 1.46 | needs distributed Muon | 5.24 |
| dp=2, ZeRO-2 | 1.46 | 0.73 | 0.90 | 9.84 | 1.46 | needs distributed Muon | 5.24 |
| dp=2, ZeRO-3 | 0.73 | 0.73 | 0.90 | 9.33 | 17.50 | needs distributed Muon | 5.24 |
| tp=2 | 1.24 | 1.24 | 1.41 | 7.55 | 0.78 | needs distributed Muon | 5.24 |
| pp=2 (last stage) | 0.88 | 0.88 | 1.19 | 7.65 | 0.04 | ok | 2.62 |
| cp=2 | 1.46 | 1.46 | 1.79 | 8.44 | 1.58 | ok | 5.24 |
| dp=2, ep=2 | 0.95 | 0.95 | 1.28 | 9.67 | 1.21 | ok | 2.85 |

What the tables show:

- **Both shapes fit one 24 GiB device at `b ≤ 2`.** No layout is needed to fit the states: they are 2.9 and
  4.7 GiB. Activations and logits decide the memory. At 131,072 tokens of vocabulary, the logits of one
  sequence take 2.5 GiB, which is more than the eight T2 layers (2.3 GiB).
- **Muon rules out ZeRO and tensor parallel** until someone writes a distributed Muon. Muon orthogonalizes each
  whole matrix, and these layouts split the matrices across devices. DDP, pipeline, context and expert
  parallel keep each matrix whole.
- **DDP does not divide Muon's work.** Every DDP rank repeats the full Newton-Schulz step (2.26 TFLOP for T2,
  about 20 % of the forward and backward pass of a 16,384-token step). Expert parallel halves it (1.23), because
  each rank updates only its own experts, and so does pipeline parallel (1.13).
- **Expert parallel is the useful second axis.** Routed experts are 64-70 % of the weights. `dp=2, ep=2` cuts
  the states by 29 % (T2) and 33 % (T3) and keeps Muon whole. It sends 0.82 GiB per step, less than DDP.
- ZeRO-3 sends 12 × DDP here: with `m = 8` it gathers the weights again for every micro-batch (formula:
  `docs/parallel_layout_v0.md`, section D). Reference only, as above: it needs a distributed Muon.

## 4. How v1 counts

The changes from v0, and why each one was needed:

| v0 | v1 | Why |
|---|---|---|
| Team 6's model: biases, LayerNorm, 2-matrix GELU FFN, learned positions | Team 5's model: no biases, RMSNorm, 3-matrix SwiGLU, RoPE, KE2 projection `256·P·d` | config v1 trains Team 5's model |
| FFN width = `mlp_ratio · d`; T2/T3 crash (`mlp_ratio: null`) | explicit expert width from Team 5's resolver (`moe.ffn_hidden`, 768 / 896) | 768 and 896 are not whole multiples of the width |
| reads `moe.num_shared` | reads config v1's keys (`moe.n_shared`, `model.d_ff`); a value that disagrees with the arm stops it | v0 would count 0 shared experts and give no error |
| 8 bytes of optimizer state per parameter | Muon 4 (one fp32 buffer) on the block matrices, AdamW 8 on the rest, by Team 5's `uses_muon` | config v1 chose Muon |
| no optimizer check | `muon` column: "needs distributed Muon" when ZeRO or tp splits a matrix; such rows are reference only | Muon needs whole matrices |
| Korthikanti activation constants (MHA, 4h GELU MLP, ±50 %) | constants fitted to the tensors autograd keeps for Team 5's model, plus the bf16 weight copies autocast keeps | the old constants do not describe SwiGLU, MoE or eager fp32 softmax |
| | `muon_tflop`: Newton-Schulz work per device per step | it changes tokens/s and DDP does not divide it |

Activation bytes kept per layer for one micro-batch of `T = b · s` tokens (bf16 autocast, no recompute):

```
T · ( 34 d + top_k · (10 d + 8 f) + shared · (4 d + 8 f) + 40 + score · heads · s )  +  s² (mask)  +  16 · s · d_head (RoPE)
score = 6 on CUDA (fp32 softmax output + its bf16 copy), 2 on CPU
outside the layers: 10 d per token; logits at the end of the forward pass 10 · T · V
                    (bf16 logits 2 + fp32 copy 4 + log-softmax output 4)
bf16 weight copies: 2 bytes × every block matrix except the router, and the head
```

For T2 at `b = 1` that is 0.28 GiB per layer: the eager attention scores are two thirds of it.

Evidence and limits:

- **Parameters, optimizer state:** equal to Team 5's real model and optimizers (tests at full T2/T3 size on the
  meta device, and one real Muon and AdamW step at a small size).
- **Activations:** within 0.4 % of the tensors autograd saves, on CPU, for 14 small shapes in bf16 and fp32
  (`test_activation_formula_matches_saved_tensors_on_cpu`). On CUDA one term differs: autocast runs softmax in
  fp32 there, so the score term is 6 bytes, not 2. That is taken from PyTorch's CUDA autocast op list and not
  measured. The one-GPU jobs check it: the T2 `b = 8` run is predicted to need 41.4 GiB.
- **Peak:** the harness logs only the memory at the end of a step. The peak is checked only by out-of-memory,
  or not, in the jobs. The backward pass of the loss can briefly hold about 2 more bytes per logit than the
  table counts.
- **Not modelled** (see `docs/parallel_layout_v1.md`, section I): time, overlap, uneven expert load (the
  formulas assume every token's `k` copies spread evenly), expert tensor parallel, and fragmentation. Tensor
  parallel does not split the routed experts.

## 5. Reproduce

From `teams/07-infrastructure/`. `--decisions` defaults to Team 5's `configs/config_v1.yaml` (merged with
PR 447, Muon), so it is left out. `--markdown` prints only the states at the end of a step; the "End of step"
column of section 2 (states + held logits) is the `= allocated` line of `--detail`.

```bash
A=../05-architecture/configs/arms
ONE="--layout b=1,m=8 --layout b=1,m=1 --layout b=2,m=1 --layout b=4,m=1 --layout b=8,m=1 --layout b=2,m=4 --layout b=4,m=2"

# Section 1 and 2: one GPU, every row of the table
python layout/parallel_layout_v1.py --arm $A/t2.yaml $ONE --detail
python layout/parallel_layout_v1.py --arm $A/t3.yaml $ONE --detail

# Section 2, AdamW reference run: skip config v1 so the arm's AdamW is counted
python layout/parallel_layout_v1.py --arm $A/t2.yaml --decisions '' --layout b=1,m=8

# Section 3: two GPUs
python layout/parallel_layout_v1.py --arm $A/t2.yaml --world 2 --base b=1,m=8 --markdown
python layout/parallel_layout_v1.py --arm $A/t3.yaml --world 2 --base b=1,m=8 --markdown

python -m pytest layout/test_parallel_layout_v1.py -q        # CPU, no training, about 10 s
```

## 6. Open items

| Item | Who | Blocks |
|---|---|---|
| `configs/arms/t3_muon.yaml` (each T3 job gives the file) | Team 5 | the five T3 jobs |
| runtime files with `micro_batch_size` 2 and 4 | Team 5 | the `b=2, m=4` and `b=4, m=2` rows |
| GPU type on EC2, and the test logs | owner | submitting the ten jobs |
| a multi-GPU training script for Team 5's model (DDP first) | Team 5 or Team 6 | every row of section 3 |
| a distributed Muon | not assigned | the reference-only ZeRO and tensor parallel rows of section 3 |
| model sizes, sequence length, precision in config v1 | TSAI | replacing T2/T3 with the real shape |
