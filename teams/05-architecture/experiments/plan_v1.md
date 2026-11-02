# Experiment plan v1

Lead: Shivanshu Thapliyal. Written 1 Nov 2026 from the G5 week-2 note of 31 Oct.
This file is the contract for the runs. It does not record results. `config_v1.yaml` and `decisions.md` wait until `experiments/results_v1.md` has a bits-per-byte number for each arm.

EXP-4 (code share) is week 3. It is not an arm here.

## What stays fixed

The 31 Oct test-size line, on every arm, except the one value that arm changes:

- vocabulary 131,072
- tied embeddings
- 1 shared expert
- top-2
- GQA with RoPE
- SwiGLU

| Size | d_model | Layers | Heads | KV heads | Routed experts | Expert FFN | Context | Instructor total | Use |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 256 | 6 | 4 | 2 | 8 | 512 | 1,024 | 56M | Correctness and fast A/B. EXP-1 only. |
| T2 | 512 | 8 | 8 | 2 | 16 | 768 | 2,048 | 233M | Every ablation arm. |
| T3 | 640 | 10 | 10 | 2 | 16 | 896 | 2,048 | 386M | Confirm a winner only. |

T3 runs only after that family has a winner at T2. One family, one T3 run. Keep every other size fixed. A change that is not in the arm's "what changes" cell makes the run void.

`configs/config_v0.yaml` is not filled with these sizes. Model sizes and `embedding.ke2_output_dim` stay empty. `tokenizer.vocab_size` is 131072 because G3 froze it.

## How a result is scored

Bits per byte = the sum of per-token next-token loss in nats on the held-out set, divided by ln 2, divided by the UTF-8 byte count of that held-out text.

If the logger stored a mean, multiply by the number of scored tokens first. Do not divide by ln 2 twice. Score every held-out token. Assistant-only masking is not this week.

The held-out set is the one named by `results/heldout_v1.sha256` (Data owner, Mon 2 Nov), checked against the Team 9 fingerprints, with 0 matches. A loss from the training stream is not a result.

Seed spread of an arm is the maximum bits per byte across its seeds minus the minimum. An arm with fewer than 2 finished seeds has no spread and cannot win.

Winner rule, unless the arm says otherwise: the arm's mean bits per byte is lower than the baseline mean by more than the larger of the two seed spreads. Otherwise the config v0 default stays. A run that hits its max time before the step count below is not a result.

A run is void if any logged loss is NaN or inf.

## Same budget on every arm of a size

Set by this plan so two arms can be compared. Not a production length.

| Size | Batch | Tokens per step | Steps | Training tokens |
|---|---|---|---|---|
| T1 | 8 | 8,192 | 245 | just over 2,000,000 |
| T2 | 8 | 16,384 | 1,221 | just over 20,000,000 |
| T3 | 8 | 16,384 | 1,221 | just over 20,000,000 |

Seeds, in order: 1234, then 1235, then 1236. Seed 1234 is the week-1 gate seed.

AdamW uses the PyTorch defaults for the betas (0.9, 0.999). Weight decay is 0, because `config_v0.yaml` does not set one and this sweep must not mix decay into the learning-rate question. Gradient clip stays 1.0.

GPU runs use bf16. A CPU run uses fp32 and is a smoke check, not a bits-per-byte result.

## Arms

| Arm | Owner | Test size | What changes | Metric | Pass bar | Seeds | Max time | Config |
|---|---|---|---|---|---|---|---|---|
| exp1-lr-1e-4 | Avnish Midha | T1 | `optim.lr` 1e-4 | bits per byte | EXP-1 rule | 3 | 30 min | `configs/arms/exp1/lr_1e-4.yaml` |
| exp1-lr-3e-4 | Max | T1 | `optim.lr` 3e-4 | bits per byte | EXP-1 rule | 3 | 30 min | `configs/arms/exp1/lr_3e-4.yaml` |
| exp1-lr-1e-3 | Mukund Singh | T1 | `optim.lr` 1e-3 | bits per byte | EXP-1 rule | 3 | 30 min | `configs/arms/exp1/lr_1e-3.yaml` |
| exp1-lr-3e-3 | Soham Niyogi | T1 | `optim.lr` 3e-3 | bits per byte | EXP-1 rule | 3 | 30 min | `configs/arms/exp1/lr_3e-3.yaml` |
| exp1-lr-1e-2 | Varshith Chennuru | T1 | `optim.lr` 1e-2 | bits per byte | EXP-1 rule | 3 | 30 min | `configs/arms/exp1/lr_1e-2.yaml` |
| exp2-adamw | Vardhan Walavalkar | T2 | none. AdamW at the EXP-1 winner lr | bits per byte | winner rule against exp2-muon | 3 | 90 min | `configs/arms/exp2_adamw.yaml` |
| exp2-muon | Vardhan Walavalkar | T2 | optimizer Muon, lr from the Muon screen | bits per byte | winner rule against exp2-adamw | 3 | 90 min | `configs/arms/exp2_muon.yaml` |
| exp3-experts-8 | Dharshan Thaigu | T2 | routed experts 8 | bits per byte | winner rule against exp3-base | 3 | 90 min | `configs/arms/exp3_experts_8.yaml` |
| exp3-base | Dharshan Thaigu | T2 | none. 16 routed, 1 shared | bits per byte | the EXP-3 baseline, not a challenger | 3 | 90 min | `configs/arms/t2.yaml` |
| exp3-experts-32 | Dharshan Thaigu | T2 | routed experts 32 | bits per byte | winner rule against exp3-base | 3 | 90 min | `configs/arms/exp3_experts_32.yaml` |
| exp3-shared-0 | Dharshan Thaigu | T2 | shared experts 0 | bits per byte | winner rule against exp3-base | 3 | 90 min | `configs/arms/exp3_shared_0.yaml` |
| attn-0 | Revant Gupta | T2 | none. GQA, RoPE, window = context | bits per byte | the attention baseline | 3 | 90 min | `configs/arms/t2.yaml` |
| attn-1 | Revant Gupta | T2 | arm 1 of `docs/attention_candidates.md` | bits per byte | winner rule against attn-0 | 3 | 90 min | that doc, one change from attn-0 |
| attn-2 | Revant Gupta | T2 | arm 2 of `docs/attention_candidates.md` | bits per byte | winner rule against attn-0 | 3 | 90 min | that doc, one change from attn-0 |
| attn-3 | Revant Gupta | T2 | arm 3 of `docs/attention_candidates.md` | bits per byte | winner rule against attn-0 | 3 | 90 min | that doc, one change from attn-0 |
| attn-4 | Revant Gupta | T2 | arm 4 of `docs/attention_candidates.md` | bits per byte | winner rule against attn-0 | 3 | 90 min | that doc, one change from attn-0 |
| exp5-dense | Deepjyoti Saha | T2 | dense output head | bits per byte | winner rule against exp5-ke2 | 3 | 90 min | after Team 4 agrees the design |
| exp5-ke2 | Deepjyoti Saha | T2 | KE2 output head | bits per byte | winner rule against exp5-dense | 3 | 90 min | after Team 4 agrees the design |
| t3-confirm | the owner of that family | T3 | the single winning value only | bits per byte | still beats its baseline by more than the seed spread | 3 | 120 min | a copy of the winning arm with the T3 shape |

EXP-1 rule: rank the five means. The top arm wins only if it is lower than the second by more than the larger of their seed spreads. If it is not, `optim.lr` stays null in config v0.

The five learning rates are a log grid chosen in this plan so the sweep can see a stall and a blow-up. They are not a recommended production learning rate and they are not taken from a previous course config.

EXP-1 by Tue 3 Nov is seed 1234 of each of the five arms. Seeds 1235 and 1236 are required before any arm is called the winner, and they are due Wed 4 Nov so a job request can be queued for the break.

Muon screen, before the T2 job: three T1 runs, Muon learning rates 1e-3, 1e-2 and 1e-1, seed 1234, 30 min each. The T2 Muon arm uses the learning rate with the lowest bits per byte of those three runs. This grid is also set here, for the same reason as the AdamW grid. The AdamW arm at T2 uses the EXP-1 winner learning rate. If EXP-1 has no winner yet, the AdamW arm uses 1e-3 and the run file says the comparison is not final.

EXP-3 runs only those four rows. The counts are the T1 count (8), the T2 count (16), and one doubling (32). Shared-expert off changes that one value and leaves the expert count at 16.

Attention rows 1 to 4 take their layer pattern, window, position method and reason from `docs/attention_candidates.md`. This plan does not invent a fifth pattern. An arm missing any of those four fields is not run. More than four arms is not run.

EXP-5 does not start until Team 4 has agreed KE2 output head or dense head. `embedding.ke2_output_dim` stays empty until `teams/04-ke2/output_shape.md` gives one output number. The input recommendation there (P = 32, D = 8,192) is not the output dim.

## What Team 6 can time on 1 Nov

Their loader (`teams/06-performance/models/config.py`) accepts the files below. Three instructor choices do not fit that loader. The files do not paper over them.

- Their MLP is GELU. The instructor activation is SwiGLU. No file selects SwiGLU.
- Their positions are a learned table. The instructor method is RoPE. No file selects RoPE.
- Expert hidden is `mlp_ratio * d_model`, and `mlp_ratio` is an integer. T1 is exact: 2 × 256 = 512. T2's 768 and T3's 896 are not integer ratios. `t2.yaml` and `t3.yaml` set `mlp_ratio` to null. Leaving the key out would keep the inherited value 4 and time the wrong width. Do not publish a step time from that default. An official T2 or T3 step time waits until the loader takes an absolute expert width.

`embedding: ke1` is used because `config_v0.yaml` sets `embedding.type` to kronecker, and ke1 is the Kronecker path in their loader. ke1's head is untied. The tied-head question is EXP-5, not something these files decide.

`t2.yaml` and `t3.yaml` set `mlp_ratio` to null. They inherit `base.yaml`, and leaving the key out would keep its `mlp_ratio` 4. That would time an expert width of 2,048 at T2 and 2,560 at T3. Null is there so that mistake cannot happen quietly.

T1 is exact on every loader field and may be timed as the T1 shape. EXP-1 changes only the learning rate, so one T1 step time covers all five learning-rate arms. `t1.yaml`, `t2.yaml`, and `t3.yaml` set `optim.lr` to 0.001 so the loader can take a step. That number is a timing placeholder. It is not a chosen learning rate, and config v0 keeps `optim.lr` null. The EXP-1 files set their own rates. `exp2_adamw.yaml` uses 0.001 until EXP-1 names a winner, and that comparison is not final. `exp2_muon.yaml` sets `optim.muon_lr` to null so base.yaml's 0.02 is not inherited. The T1 screen chooses that rate.

Pull request 167 is on main. Every arm file sets `model.reversible` false, `model.ce_impl` torch, and `moe.dispatch` loop, so those three cannot move with `base.yaml`. `t1.yaml`, `t2.yaml`, and `t3.yaml` also set `model.attn_impl` eager and `model.mtp` false. The loader's own default for attention is sdpa, so leaving attention unset would not keep eager. `run.dtype` is already bf16 on those three files. SwiGLU, RoPE, and a rope theta are not selected in these files.

| File | Loadable shape | Official step time |
|---|---|---|
| `configs/arms/t1.yaml` | T1, expert FFN 512 | yes |
| `configs/arms/t2.yaml` | T2 depth, width, context, 16 experts, 1 shared. Expert FFN not set. | no |
| `configs/arms/t3.yaml` | T3 depth, width, context, 16 experts, 1 shared. Expert FFN not set. | no |
| `configs/arms/exp2_muon.yaml` | same shape as `t2.yaml`, optimizer Muon | no, same width gap |
| `configs/arms/exp3_experts_8.yaml` | T2 with 8 routed experts | no, same width gap |
| `configs/arms/exp3_experts_32.yaml` | T2 with 32 routed experts | no, same width gap |
| `configs/arms/exp3_shared_0.yaml` | T2 with 0 shared experts | no, same width gap |

## Defaults if Thu 12 Nov has no result

| Open setting | Config v0 default that stays |
|---|---|
| Learning rate | `optim.lr` null |
| Optimizer | `optim.name` adamw |
| Expert count | `moe.n_expert` null. The test-size line is not copied in. |
| Shared expert | unset. The test-size line is not copied in. |
| Attention | `attention.impl` eager. RoPE and the window are not copied in from an unfinished arm. |
| Output head | `embedding.ke2_output_dim` null |

## Who files the job

T1 fits the 30 minute cap on one GPU. T2 and T3 go by `JOB_REQUEST.md` if the owner's machine hits the cap. One job, one question. Attach a Colab or CPU log of the same script. The harness owner lands tokenizer v0, the raw byte table, bits per byte, and the T1 T2 T3 configs on Mon 2 Nov. Until that harness exists, a job request has no script and is not sent.
