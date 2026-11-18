# Parallel layout v1: memory and traffic per device, for Team 5's model with config v1

Owner: G7 Member B (author of v0, [`parallel_layout_v0.md`](parallel_layout_v0.md)). v1 edits: Max, 14 Nov 2026.
Calculator: [`layout/parallel_layout_v1.py`](../layout/parallel_layout_v1.py). Tests:
[`layout/test_parallel_layout_v1.py`](../layout/test_parallel_layout_v1.py).
v0 and its calculator stay as they are for Team 6's model; this file covers config v1 only.

> **In simple words.** One device cannot hold the whole training, so we split it. We can split the **data**
> (each device trains on other samples), the **layers** (pipeline), the **experts** (expert), or the
> **sequence** (context). Each split saves memory and costs network traffic. This file writes down, for each
> split, how many bytes each device holds and how many bytes it sends per training step, for the model that
> config v1 trains: Team 5's week-2 model (`teams/05-architecture/harness/week2/model.py`) with Muon. The
> calculator turns a Team 5 arm and config v1 into those numbers, so we choose a layout **before** we pay for
> device hours. Every number here is a formula, not a measurement; a measured run replaces it.

---

## A. Symbols

Config v1 (`teams/05-architecture/configs/config_v1.yaml`, PR 447) leaves the sizes empty. The calculator reads
them from a Team 5 arm (`--arm`) and stops if config v1 gives a value that disagrees with the arm.

| Symbol | Meaning | Config v1 key | Team 5 arm key |
|---|---|---|---|
| `V` | vocabulary | `tokenizer.vocab_size` | `model.vocab_size` |
| `s` | sequence length | `data.seq_len` | `model.block_size` |
| `L` | layers | `model.n_layer` | `model.n_layer` |
| `h` | model width | `model.d_model` | `model.n_embd` |
| `a`, `a_kv` | query heads, key/value heads | `model.n_head`, `model.n_kv_head` | `model.n_head`, `model.n_kv_head` |
| `d_h` | head width, `h / a` | | |
| `f` | expert width (routed and shared) | `model.d_ff` | `model.moe.ffn_hidden` (resolved by Team 5's `load_runtime`; no `mlp_ratio` fallback) |
| `E`, `k`, `S` | routed experts, experts per token, shared experts | `moe.n_expert`, `moe.top_k`, `moe.n_shared` | `moe.num_experts`, `moe.top_k`, `moe.num_shared` |
| `P` | Kronecker byte positions | `embedding.pos_dim` | `model.ke_max_pos` |
| | optimizer | `optim.name` | `optim.name` |
| | precision | `precision` | `run.dtype` |
| `b`, `m` | micro-batch (sequences per device), micro-batches per optimizer step | | `run.micro_batch_size`, `run.batch_size / run.micro_batch_size` |
| `d_p, p, e, c` | data, pipeline, expert, context parallel degrees | | |
| `N` | devices, `N = d_p · p · c`; expert parallel is carved out of `d_p · c` | | |
| `Ψ` | parameters on one device | section A.1 | |

`optim.name` is a decision, not a shape: when config v1 says `muon` and the arm trains `adamw` (T2, T3), the
calculator counts Muon and prints a note.

### A.1 Parameters, exactly as Team 5's model builds them

`harness/week2/model.py`: no biases, RMSNorm, GQA with RoPE (no position table), SwiGLU experts, the Kronecker
input projection (arm value `embedding: ke1`, class `KE2`), a dense untied head.

```
attention    = 2·h·h + 2·h·a_kv·d_h                   (q, o; k, v)
norms        = 2h                                    (two RMSNorm gains)
router       = h·E
one expert   = 3·h·f                                 (gate, up, down)
dense layer  = attention + norms + router + S · one expert
expert layer = E · one expert                        (routed experts only)
embedding    = 256·P·h                               (KE2 projection)
head         = V·h  (+ V·h with MTP)  + h             (head, final norm)
total        = L·(dense layer + expert layer) + embedding + head
```

The tests build Team 5's real `LanguageModel` and check the total, the routed-expert count and the Muon count
against it: at full size for T2, T3 and `exp2_muon` (`test_param_counts_equal_team5_model_at_full_size`), and for
MTP, no shared expert, `a_kv` = 1 and 4, and 8 experts top-1 (`..._for_other_shapes`). T2 is 237,052,416
parameters, T3 391,529,600 (`test_t2_and_t3_sizes`).

**Only routed experts are split by expert parallel.** Shared experts, the router, attention, norms, embedding
and head are "dense": every expert-parallel rank keeps them.

**Muon and AdamW parameters.** Muon updates the 2D block matrices (attention, router, shared and routed
experts; Team 5's `uses_muon`). AdamW updates the embedding projection, the head(s) and the norm gains.

---

## B. Model-state memory per device

| State | Bytes per parameter | Source |
|---|---|---|
| weights `w` | 4 | Team 5 keeps fp32 weights; bf16 only under autocast |
| gradients `g` | 4 | fp32 |
| optimizer, Muon parameters | 4 | one fp32 momentum buffer |
| optimizer, AdamW parameters | 8 | two fp32 moments |
| autocast copies (`precision: bf16`) | 2 | a bf16 copy of every matrix autocast multiplies with: attention, shared and routed experts, head(s). Not the router (outside autocast) or the KE2 projection (read in fp32) |

`test_optimizer_bytes_equal_team5_optimizer_state` checks the optimizer row against the state of Team 5's real
optimizer after one step, for Muon and AdamW.

Parameters on one device, for the busiest pipeline stage:

```
Ψ_dense  = ceil(L/p) · dense layer  +  embedding (first stage) / head (last stage)
Ψ_expert = ceil(L/p) · expert layer / e
```

| Layout | Effect on model states |
|---|---|
| DDP | every device holds everything |
| Pipeline `p` | `ceil(L/p)` layers per device; the first stage also holds the embedding, the last the head |
| Expert parallel `e` | divides routed experts by `e`; dense weights stay whole on every rank |
| Context parallel `c` | none (weights whole); saves activations only |

---

## C. Activation memory per device

Fitted to the tensors autograd saves for Team 5's model on CPU. `T = b · s / c` tokens per device per
micro-batch, `s_c = s / c`.

Per layer, per token:

```
bf16   34h + k·(10h + 8f) + S·(4h + 8f) + 40  +  σ · a · s
fp32   40h + k·(12h + 16f) + S·16f       + 40  +  4 · a · s
```

- `σ` is the attention-score bytes per (query, key, head): 6 on CUDA with bf16 (bf16 scores, fp32 softmax under
  CUDA autocast, a bf16 copy for the product with V), 2 on CPU with bf16, 4 with fp32. **The CUDA value 6 is
  assumed** from PyTorch's CUDA autocast op list, not measured; the job requests check it.
- A routed pass costs more than a shared one: the gathered input rows and the gate-weighted output are kept.
- The 40 is per-token scalars (norm scales, router choices and gates).

Per layer, fixed: `s · s_c` (bool mask) `+ 16 · s_c · d_h` (fp32 rotary angle products).

Outside the blocks: `10h` (bf16) or `12h` (fp32) bytes per token for the embedding and the final norm.

Logits, on the last stage, × 2 with MTP:
- log-softmax saved by autograd: `4·V` bytes per token;
- logits still alive at the end of forward: `6·V` per token with bf16 (the bf16 logits and the fp32 copy that
  `token_nll` makes), `4·V` with fp32.

Per device: `ceil(L/p) × in-flight micro-batches × per-layer`. With 1F1B the **first** stage keeps `min(p, m)`
micro-batches in flight (Narayanan et al. 2021).

`test_activation_formula_matches_saved_tensors_on_cpu` compares the formula with the saved tensors of Team 5's
real forward pass for 7 shapes × 2 precisions: within 1 % (0.4 % at most when written).

---

## D. Traffic per device per optimizer step

Bytes **sent** by one device, ring algorithms (bandwidth term only, no latency): all-reduce of `M` bytes over
`n` devices sends `2(n−1)/n · M`. Gradients are fp32 (4 bytes); activation messages are bf16 (2 bytes).
`T_mb = b · s / c` tokens per micro-batch per device.

| Layout | What is sent | Bytes per device per step |
|---|---|---|
| DDP | all-reduce of fp32 grads, once per step; `n = d_p · c` for dense weights, `d_p · c / e` for expert weights | `2(n−1)/n · 4·Ψ` |
| Pipeline `p` | activations forward, gradients backward, at each stage boundary | `m · 2 · T_mb·h·2` (a middle stage) |
| Expert `e` | dispatch + combine forward, the same backward: 4 all-to-alls per MoE layer, `k` copies of each token, uniform routing | `m · ceil(L/p) · 4 · (e−1)/e · T_mb·k·h·2` |
| Context `c` (ring attention) | K and V blocks pass `c−1` times forward; K, V and their grads backward (≈ 2 × forward) | `m · ceil(L/p) · 3 · (c−1) · 2·T_mb·a_kv·d_h · 2` |

**Which link carries it.** EP is sent every MoE layer, so it belongs inside one node (the fastest link). PP and
DP are sent once per micro-batch or once per step, so they can cross nodes. CP sits between them. Link speeds are
inputs we do not have yet.

### D.1 Muon's Newton-Schulz work

Muon orthogonalizes each whole matrix: 5 steps of `4·m²·n + 2·m³` FLOP for an `m × n` matrix, `m` the short
side. Every rank that holds a whole matrix repeats it, so **DDP does not divide this work**; PP divides it by the
layers per stage and EP divides the expert part by `e` (`test_ddp_does_not_divide_newton_schulz_work_and_ep_does`).

### E. Pipeline bubble

1F1B with `m` micro-batches over `p` stages idles for `(p − 1)/m` of the ideal step time
(Narayanan et al. 2021). Keep `m ≥ 4p` for a bubble under 25 %; the calculator refuses `m < p`.

---

## F. Config v1 numbers (test sizes T2 and T3)

Sizes from Team 5's arms `configs/arms/t2.yaml` and `t3.yaml` (16 routed + 1 shared experts, top-2, the v1
expert count), checked against config v1, counted with Muon. **These are test sizes**, not config v1 sizes:
config v1 leaves `data.seq_len`, `model.n_layer`, `model.d_model`, `model.n_head`, `model.n_kv_head`,
`model.d_ff` and `precision` empty, and the calculator prints which arm value it used for each.
Full tables and evidence: [`results/layouts.md`](../results/layouts.md).

| | T2 | T3 |
|---|---:|---:|
| Shape | 8 layers, h 512, 8 / 2 heads, f 768, s 2048 | 10 layers, h 640, 10 / 2 heads, f 896, s 2048 |
| Parameters | 237.1M | 391.5M |
| Routed experts, share of parameters | 64 % | 70 % |
| Muon / AdamW parameters | 165.7M / 71.3M | 302.4M / 89.1M |
| States (weights, grads, Muon + AdamW), one device | 2.91 GiB | 4.71 GiB |
| Newton-Schulz per step, one device | 2.26 TFLOP | 5.24 TFLOP |

One device (the only layout `train_week2.py` runs today), the arm's batch of 8 sequences split into `b × m`,
16,384 tokens per step, CUDA bf16, GiB:

```bash
python layout/parallel_layout_v1.py --arm ../05-architecture/configs/arms/t2.yaml --world 1
```

| b × m | T2 peak | T3 peak |
|---|---:|---:|
| 1 × 8 | 8.14 | 11.46 |
| 2 × 4 | 12.88 | 17.44 |
| 4 × 2 | 22.37 | 29.39 |
| 8 × 1 | 41.35 | 53.28 |

T2 at `b=1, m=8`: weights 0.88, gradients 0.88, optimizer 1.15, autocast copies 0.43, activations 2.29,
logits and loss 2.50 GiB.

Two devices, T2, `b=1, m=8`:

```bash
python layout/parallel_layout_v1.py --arm ../05-architecture/configs/arms/t2.yaml \
       --layout dp=2,m=8 --layout pp=2,m=8 --layout cp=2,m=8 --layout dp=2,ep=2,m=8
```

| layout | tokens/step | peak GiB | states GiB | NS TFLOP | send GiB | bubble |
|---|---:|---:|---:|---:|---:|---:|
| dp=2 | 32,768 | 8.14 | 2.91 | 2.26 | 0.88 | - |
| pp=2 | 16,384 | 5.86 | 1.93 | 1.13 | 0.03 | 12 % |
| cp=2 | 16,384 | 5.74 | 2.91 | 2.26 | 0.98 | - |
| dp=2,ep=2 | 32,768 | 7.16 | 2.07 | 1.23 | 0.82 | - |

What it shows:

- **Activations and logits decide the memory, not the model states.** At `V = 131,072` the logits and loss
  alone are 2.5 GiB per sequence on T2; `b` moves the peak from 8 to 41 GiB while the states stay at 2.9 GiB.
- **Expert parallel is the useful second axis**: routed experts are 64-70 % of the weights, and EP is the only
  data-side split that also divides the Newton-Schulz work.
- None of the multi-device rows can be measured yet: no team has a multi-GPU training script for Team 5's model.
  Job requests (`jobs/2026-11-14-layout-*-muon-b*-m*.md`) will measure tokens per second and memory for each
  one-device `b × m` row. They are submitted separately; the five T3 ones wait for a Team 5 T3 Muon arm.

---

## G. How to choose (rules for config v1)

1. Start with **one device**, then **DDP**. If activations do not fit, lower `b` and raise `m`
   (`run.micro_batch_size`); the tokens per step stay the same.
2. Experts are most of the weights: **EP inside one node** (all-to-all every MoE layer). It also divides the
   expert states and Muon's Newton-Schulz work.
3. More layers than fit one node: **PP across nodes**, with `m ≥ 4p`.
4. Long sequences: **CP**.
5. Bit-equal restore (ADR 0001): a change of `p` or `e` reshards the checkpoint and changes reduction order, so
   the loss is **not** bit-equal across a layout change. Fix the layout before the main run; the restore test
   runs on the same layout it saved with.

---

## H. Config v1 inputs

Config v1 is Team 5's `configs/config_v1.yaml` as PR 447 writes it (Gate 2, 14 Nov; open when written): Muon,
the v0 attention (eager), 16 routed experts plus 1 shared, top-2, learning rate 1e-3. The calculator checks:

- a value config v1 sets that disagrees with the arm stops the calculator, for example T1's 8 experts
  (`test_t1_has_8_experts_and_is_refused`), a wrong `moe.n_shared` (`test_the_pr447_shared_expert_key_is_read`)
  or a wrong `model.d_ff` (`test_a_filled_size_must_agree_with_the_arm`);
- an empty value is taken from the arm and named as a test size;
- the arm must use the v0 attention (eager, no gate, sink or window) and no reversible stack.

When config v1 fills its sizes, rerun F with the arm that matches them and paste the tables here, with the
config's git sha and the device count and memory per device that TSAI states.

---

## I. What v1 does not model

- **Layouts that split a matrix.** Muon orthogonalizes whole matrices and the lab has no distributed Muon, so
  ZeRO-1/2/3, HSDP and tensor parallel are left out of this file. The calculator still accepts them and prints
  "needs distributed Muon".
- **Recompute, chunked cross-entropy, pure bf16 weights with an fp32 master copy.** Team 5's harness has none of
  them (`ce_impl` must be `torch`, `reversible` must be `false`, weights are fp32).
- The other attention arms (MQA, sliding window, sink, gate) and the reversible stack: the calculator refuses
  them.
- Time: no link or compute speeds yet. v1 gives bytes and Newton-Schulz FLOP; time needs the node.
- Overlap of communication with compute, bucket sizes, latency terms.
- Uneven expert load: EP traffic assumes uniform routing (each token's `k` copies spread evenly).
- Virtual pipeline stages (interleaved 1F1B); zero-bubble schedules.
- Fragmentation and allocator caches: real peaks run above these numbers.
- The activation constants are fitted on CPU only; the CUDA attention-score bytes (`σ = 6`) are assumed.

## J. References

- Narayanan et al., *Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM*, 2021,
  arXiv:2104.04473 (1F1B, bubble `(p−1)/m`, in-flight micro-batches).
- Lepikhin et al., *GShard*, 2020, arXiv:2006.16668 (expert parallel, all-to-all dispatch and combine).
- Liu et al., *Ring Attention with Blockwise Transformers*, 2023, arXiv:2310.01889 (context parallel ring).

## K. Change log

| Version | Date | Change |
|---|---|---|
| v0 | 2026-11-02 | G7 Member B: formulas, calculator and tests for Team 6's model, worked example; config v1 section waiting for Team 5 ([`parallel_layout_v0.md`](parallel_layout_v0.md)) |
| v1 | 2026-11-14 | Max: rewritten for config v1 (PR 447) and Team 5's week-2 model with Muon, calculator `parallel_layout_v1.py`; removed ZeRO, HSDP, tensor parallel, recompute, chunked CE, bf16 master weights and the Team 6 formulas |
