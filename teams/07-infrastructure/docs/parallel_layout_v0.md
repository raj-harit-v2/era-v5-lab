# Parallel layout v0: memory and traffic per device, for each layout

Owner: G7 Member B. Status: **v0, first version** (due Fri 13 Nov 2026). Config v1 numbers: section H, due
Sat 14 Nov, when Team 5 gives config v1.
Calculator: [`layout/parallel_layout.py`](../layout/parallel_layout.py). Tests:
[`layout/test_parallel_layout.py`](../layout/test_parallel_layout.py).

> **In simple words.** One device cannot hold the whole training, so we split it. We can split the **data**
> (each device trains on other samples), the **weights inside a layer** (tensor), the **layers** (pipeline),
> the **experts** (expert), or the **sequence** (context). Each split saves memory and costs network traffic.
> This file writes down, for each split, how many bytes each device holds and how many bytes it sends per
> training step. The calculator turns a config into those numbers, so we choose a layout **before** we pay for
> device hours. Every number here is a formula, not a measurement; a measured run replaces it.

---

## A. Symbols

| Symbol | Meaning | Config key (Team 6 `model:` / Team 5 settings) |
|---|---|---|
| `V` | vocabulary | `vocab_size` / `tokenizer.vocab_size` |
| `s` | sequence length | `block_size` / `data.seq_len` |
| `L` | layers | `n_layer` / `model.n_layer` |
| `h` | model width | `n_embd` / `model.d_model` |
| `a`, `a_kv` | query heads, key/value heads | `n_head`, `n_kv_head` |
| `r` | FFN width / `h` | `mlp_ratio` |
| `E`, `k`, `S` | routed experts, experts per token, shared experts | `moe.num_experts`, `moe.top_k`, `moe.num_shared` |
| `b`, `m` | micro-batch (sequences per device), micro-batches per optimizer step | layout |
| `d_p, t, p, e, c` | data, tensor, pipeline, expert, context parallel degrees | layout |
| `N` | devices, `N = d_p · t · p · c`; expert parallel is carved out of `d_p · c` | layout |
| `Ψ` | parameters on one device before ZeRO sharding | section A.1 |
| `w, g, o` | bytes per parameter for weights, gradients, optimizer state | precision, section B |

### A.1 Parameters, exactly as Team 6's model builds them

`teams/06-performance/models/gpt.py` (pre-LayerNorm, biased `nn.Linear`, GQA, optional MoE, learned positions).
With `d_h = h / a` and FFN width `f = r · h`:

```
attention   = h·(a + 2·a_kv)·d_h + (a + 2·a_kv)·d_h  +  h·h + h          (c_attn, c_proj, with biases)
norms       = 4h                                                          (ln1, ln2)
one FFN     = 2·h·f + f + h
dense layer = attention + norms + one FFN                                 (ffn: mlp)
            = attention + norms + (h·E + E) + S · one FFN                  (ffn: moe; router + shared experts)
expert layer= E · one FFN                                                 (routed experts only; 0 for mlp)
embedding   = V·h (table)  or  256·P·h (Kronecker ke1/ke2, P = ke_max_pos)  +  s·h (positions)
head        = 2h (ln_f)  +  V·h if the head is untied (ke1/ke2)  +  V·h if mtp
total       = L·(dense layer + expert layer) + embedding + head
```

The test `test_param_formula_equals_team6_model` builds Team 6's real `GPT` for seven shapes (dense, MoE, MHA,
GQA, ke1, ke2, MTP, no shared expert) and checks that this total, the routed-expert count and Team 6's own
`param_counts()` "active" number are equal to the parameter.

**Only routed experts are split by expert parallel.** Shared experts, the router, attention, norms, embedding
and head are "dense": every expert-parallel rank keeps them.

---

## B. Model-state memory per device

Bytes per parameter, by precision (the calculator's `precision=`):

| Precision | `w` weights | `g` grads | `o` optimizer | Where it is true |
|---|---|---|---|---|
| `amp` (default) | 4 | 4 | 8 | fp32 weights and grads, bf16 compute under autocast: Team 6 `perfkit/bench.py` today |
| `bf16` | 2 | 2 | 4 + 8 = 12 | bf16 weights and grads + fp32 master copy: the ZeRO paper's accounting |
| `fp32` | 4 | 4 | 8 | CPU runs |

`o` = master copy (if any) + `opt_bytes` moments. AdamW keeps two fp32 moments, 8 bytes; the test
`test_adamw_state_on_cpu_is_eight_bytes_per_parameter` reads them from a real `torch.optim.AdamW`.
Team 6's `polar_muon_adamw` keeps less for the matrices that Muon updates; v0 uses 8 for every parameter, an
upper bound, until that split is measured (`--layout ...,opt_bytes=4` shows the other end).

Parameters on one device before ZeRO, for the busiest pipeline stage:

```
Ψ_dense  = ( ceil(L/p) · dense layer  +  embedding (first stage) / head (last stage) ) / t
Ψ_expert =   ceil(L/p) · expert layer / e
```

ZeRO shards across the `n` devices that hold the same weights: `n = d_p · c` for dense weights,
`n = d_p · c / e` for expert weights; with HSDP, `n` is the shard group.

| Layout | Weights | Grads | Optimizer | Notes |
|---|---|---|---|---|
| DDP (`zero=0`) | `w·Ψ` | `g·Ψ` | `o·Ψ` | every device holds everything |
| ZeRO-1 | `w·Ψ` | `g·Ψ` | `o·Ψ/n` | optimizer state sharded |
| ZeRO-2 | `w·Ψ` | `g·Ψ/n` | `o·Ψ/n` | + gradients sharded |
| ZeRO-3 / FSDP full shard | `w·Ψ/n` | `g·Ψ/n` | `o·Ψ/n` | + weights sharded; + a gather buffer `2·w·(one layer)`: the layer in use and the prefetched next one |
| HSDP (`zero=3,shard=n_s`) | `w·Ψ/n_s` | `g·Ψ/n_s` | `o·Ψ/n_s` | ZeRO-3 inside a group of `n_s`, copies across groups |
| Tensor parallel `t` | divides `Ψ_dense` by `t` | | | Megatron: attention heads and FFN columns split; vocabulary split for embedding and head |
| Pipeline `p` | `L/p` layers per device | | | the first stage also holds the embedding, the last the head |
| Expert parallel `e` | divides routed experts by `e` | | | dense weights stay whole on every rank |
| Context parallel `c` | none (weights whole) | | | saves activations only |

With `bf16` precision these rows are exactly the ZeRO paper's `(2+2+12)·Ψ`, `4Ψ + 12Ψ/n`, `2Ψ + 14Ψ/n`,
`16Ψ/n` (test `test_zero_stages_match_the_zero_paper`).

---

## C. Activation memory per device

Per layer and micro-batch, from Korthikanti et al. 2022 (eq. 2; eq. 4 with tensor + sequence parallel),
with `s_c = s / c`:

```
none        s_c·b·h · (34/t + 5·a·s_c/(h·t))     bytes
selective   s_c·b·h · 34/t                        (attention scores recomputed)
full        2·s_c·b·h/t                           (only the layer input kept) + one full layer while recomputing
```

- Per device: `ceil(L/p) × in-flight micro-batches × per-layer`. With 1F1B the **first** stage keeps `min(p, m)`
  micro-batches in flight (Narayanan et al. 2021), so it holds about one whole model's activations.
- Logits: `4·b·s_c·V/t` bytes (fp32 cross-entropy), × 2 with `mtp`, ÷ `ce_chunks` with Team 6's chunked CE.
  At a large vocabulary this is often the largest single term.
- `fp32` doubles the constants (they count 16-bit values).
- **Honest limit:** the 34 and 5 constants were derived for multi-head attention with a 4h MLP. GQA keeps fewer
  K/V values and MoE keeps the dispatched tokens and `k` expert activations, so for our model the formula is an
  estimate. Until Team 6 measures a peak (`gpu_alloc_gb`), read activation numbers as ±50 %.

---

## D. Traffic per device per optimizer step

Bytes **sent** by one device, ring algorithms (bandwidth term only, no latency): all-reduce of `M` bytes over
`n` devices sends `2(n−1)/n · M`; reduce-scatter and all-gather send `(n−1)/n · M` each.
Activation messages are 16-bit (2 bytes per value). `T_mb = b · s / c` tokens per micro-batch per device.

| Layout | What is sent | Bytes per device per step |
|---|---|---|
| DDP | all-reduce of grads, once per step (`no_sync` while accumulating) | `2(n−1)/n · g·Ψ` |
| ZeRO-1, ZeRO-2 | reduce-scatter grads + all-gather updated weights | `(n−1)/n · (g + w)·Ψ` = DDP when `g = w` |
| ZeRO-3 / FSDP | per micro-batch: all-gather (forward), all-gather (backward), reduce-scatter grads | `m · (n−1)/n · (2w + g)·Ψ` = 1.5 × DDP when `m = 1`, `g = w` |
| HSDP | ZeRO-3 inside the group + all-reduce of the shards across groups | ZeRO-3 with `n_s`, + `2(r−1)/r · g·Ψ/n_s`, `r = d_p·c/n_s` |
| Tensor `t` (with sequence parallel) | 2 all-gathers + 2 reduce-scatters forward, the same backward: 4 all-reduce equivalents per layer | `m · ceil(L/p) · 4 · 2(t−1)/t · T_mb·h·2` |
| Pipeline `p` | activations forward, gradients backward, at each stage boundary | `m · 2 · T_mb·h·2 / t` (a middle stage) |
| Expert `e` | dispatch + combine forward, the same backward: 4 all-to-alls per MoE layer, `k` copies of each token, uniform routing | `m · ceil(L/p) · 4 · (e−1)/e · T_mb·k·h·2 / t` |
| Context `c` (ring attention) | K and V blocks pass `c−1` times forward; K, V and their grads backward (≈ 2 × forward) | `m · ceil(L/p) · 3 · (c−1) · 2·T_mb·a_kv·d_h/t · 2` |

Checks in the tests: ZeRO-1 and ZeRO-2 send what DDP sends and ZeRO-3 sends 1.5 × (ZeRO paper, section 7);
the DDP all-reduce, TP, EP volumes and the bubble are checked number for number.

**Which link carries it.** TP and EP are sent every layer, so they belong inside one node (the fastest link).
PP and DP are sent once per micro-batch or once per step, so they can cross nodes. CP sits between them. Bytes
÷ link bandwidth gives a lower bound on the time; overlap with compute hides part of it. Link speeds are inputs
we do not have yet (no node in week 2).

### E. Pipeline bubble

1F1B with `m` micro-batches over `p` stages idles for `(p − 1)/m` of the ideal step time
(Narayanan et al. 2021). Keep `m ≥ 4p` for a bubble under 25 %; the calculator refuses `m < p`.

---

## F. Worked example (2 devices, the Team 6 CPU smoke shape)

Shape: `teams/06-performance/configs/tiny_cpu.yaml` with `ffn=moe` (its `moe:` block, 4 experts, top-2, 1
shared). This is Team 6's smoke-test shape, not a V5 size; it shows what each term does.

```bash
python layout/parallel_layout.py --config ../06-performance/configs/tiny_cpu.yaml --set ffn=moe \
       --world 2 --base b=2,m=4 --unit MiB --markdown
```

Parameters: total 9,273,992; routed experts 264,704 (the Kronecker embedding keeps the vocabulary out of the
input side; the untied head is `V·h`, most of the total). MiB per device; send in MiB per device per step:

| layout | stage | weights | grads | optimizer | activations | total | send_dp | send_tp | send_pp | send_ep | send_cp | send_total | bubble |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dp=2 | only | 35.377 | 35.377 | 70.755 | 64.844 | 206.354 | 35.377 | 0.000 | 0.000 | 0.000 | 0.000 | 35.377 | 0.00 |
| dp=2,zero=1 | only | 35.377 | 35.377 | 35.377 | 64.844 | 170.976 | 35.377 | 0.000 | 0.000 | 0.000 | 0.000 | 35.377 | 0.00 |
| dp=2,zero=2 | only | 35.377 | 17.689 | 35.377 | 64.844 | 153.287 | 35.377 | 0.000 | 0.000 | 0.000 | 0.000 | 35.377 | 0.00 |
| dp=2,zero=3 | only | 17.689 | 17.689 | 35.377 | 66.205 | 136.960 | 212.265 | 0.000 | 0.000 | 0.000 | 0.000 | 212.265 | 0.00 |
| tp=2 | only | 18.194 | 18.194 | 36.387 | 32.422 | 105.196 | 0.000 | 0.500 | 0.000 | 0.000 | 0.000 | 0.500 | 0.00 |
| pp=2 | last | 32.681 | 32.681 | 65.362 | 64.422 | 195.147 | 0.000 | 0.000 | 0.250 | 0.000 | 0.000 | 0.250 | 0.12 |
| cp=2 | only | 35.377 | 35.377 | 70.755 | 32.344 | 173.854 | 35.377 | 0.000 | 0.000 | 0.000 | 0.188 | 35.565 | 0.00 |
| dp=2,ep=2 | only | 34.873 | 34.873 | 69.745 | 64.844 | 204.334 | 34.368 | 0.000 | 0.000 | 0.500 | 0.000 | 34.868 | 0.00 |

What it shows:

- **Activations here are almost all logits**: `4 · 2 · 64 · 131,072` bytes = 64 MiB. Only TP (vocabulary
  split) and CP (sequence split) cut them; chunked CE (`ce_chunks=8`) would too. At this vocabulary the head
  and the logits decide the layout before the layers do.
- **ZeRO-3 sends 6 × what DDP sends** with `m = 4`: it gathers the weights again for every micro-batch. Use
  larger `b` and smaller `m` with ZeRO-3, or ZeRO-2 when the weights fit.
- **EP saves little here** (routed experts are 3 % of the weights); it matters only when experts are most of
  the model. The pipeline's last stage is the busy one, because it holds the head.
- TP=4 and PP=4 are not in a 4-device table of this shape: `a_kv = 2` cannot be split 4 ways, and there are
  only 2 layers. The calculator says so (`layout_problems`).

---

## G. How to choose (rules we will apply to config v1)

1. Start with **DDP**. If model states (`(w+g+o)·Ψ`) do not fit, go **ZeRO-1 → ZeRO-2 → ZeRO-3/FSDP**, in that
   order: ZeRO-1/2 cost no extra traffic; ZeRO-3 costs 1.5 × or more.
2. If activations or logits do not fit: **selective recompute** first (no traffic), then **chunked CE**, then
   **TP inside one node** (`t` ≤ devices per node, `t` divides `a_kv`), then **CP** for long sequences.
3. Many experts that are most of the weights: **EP inside one node** (all-to-all every MoE layer).
4. More layers than fit one node: **PP across nodes**, with `m ≥ 4p`.
5. Bit-equal restore (ADR 0001): a change of `t`, `p` or `e` reshards the checkpoint and changes reduction order,
   so the loss is **not** bit-equal across a layout change. Fix the layout before the main run; the restore test
   runs on the same layout it saved with.

---

## H. Config v1 numbers (Sat 14 Nov)

**Empty on purpose.** Team 5 gives config v1 on Sat 14 Nov. Then:

```bash
python layout/parallel_layout.py --config ../05-architecture/configs/config_v1.yaml \
       --world <devices> --base b=<b>,m=<m>,recompute=selective --device-gib <memory per device> --markdown
```

and paste the table here with: the config path and its git sha, the device count and memory per device that
TSAI states, the chosen layout and why (section G), and which numbers a job request will measure first
(peak memory and step time on 1 and 2 devices). If config v1 comes as a settings list with a size still
empty, the calculator stops and names it; it never guesses a size.

---

## I. What v0 does not model

- Time: no link or compute speeds yet. v0 gives bytes; time needs the node.
- Overlap of communication with compute, bucket sizes, latency terms.
- Uneven expert load: EP traffic assumes uniform routing (each token's `k` copies spread evenly).
- Expert tensor parallel different from `t`; virtual pipeline stages (interleaved 1F1B); zero-bubble schedules.
- Fragmentation and allocator caches: real peaks run above these numbers.
- The exact activation constants for GQA + MoE (section C).

## J. References

- Rajbhandari et al., *ZeRO* (memory optimizations for data-parallel training), SC 2020,
  arXiv:1910.02054 (ZeRO stages, `2+2+12` bytes, 1.5 × traffic for stage 3).
- Shoeybi et al., *Megatron-LM*, 2019, arXiv:1909.08053 (tensor parallel, 2 all-reduces forward and 2 backward
  per layer).
- Narayanan et al., *Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM*, 2021,
  arXiv:2104.04473 (1F1B, bubble `(p−1)/m`, in-flight micro-batches).
- Korthikanti et al., *Reducing Activation Recomputation in Large Transformer Models*, 2022, arXiv:2205.05198
  (activation bytes, sequence parallel, selective recompute).
- Zhao et al., *PyTorch FSDP*, 2023, arXiv:2304.11277 (full shard, hybrid shard, prefetch).
- Lepikhin et al., *GShard*, 2020, arXiv:2006.16668 (expert parallel, all-to-all dispatch and combine).
- Liu et al., *Ring Attention with Blockwise Transformers*, 2023, arXiv:2310.01889 (context parallel ring).

## K. Change log

| Version | Date | Change |
|---|---|---|
| v0 | 2026-11-02 | formulas A–E, calculator and tests, worked example; config v1 section waiting for Team 5 |
