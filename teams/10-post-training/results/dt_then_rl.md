# Deletion Tuning, then the small RL test (week-3 task 11), 16-17 Nov 2026

**Task 11 status.** Anirudh Narla ran the CPU rehearsal below. Mean held-out toy reward rose from
0.4268 to 0.6383 with all adapter-selected non-router weights trainable, and from 0.4268 to 0.5013 when
only the pruned expert layers could train. The 348,469 deleted weights stayed zero across all 180 optimizer
steps in the six DT runs. The [validation log](dt_then_rl_evidence/validation.md) checks the recorded evidence
and the current branch's trainer tests.

**Code-verifier result pending.** The [Task 6 report](small_rl.md) records 0.151 to 0.251 on a Qwen 7B
surrogate. The Task 11 code run needs its own pre-RL and post-RL scores from the DT SFT checkpoint. The
[canary request draft](../jobs/2026-11-17-dt-then-rl-code.md) records the remaining inputs and checks.

**Scope label.** Stand-in "B" (a capstone-family model trained locally on an M1 Pro with Team 5's own code: d128, 4 layers,
16+1 experts top-2, 24.7M parameters, 4.1M tokens), a toy reward, CPU, fp32. Three RL seeds, one SFT seed per arm. This is
**mechanics and relative comparison at small width, not a quality claim**, not code RL, not the dry-run-1 checkpoint.
The author's local experiment notes record the selection and evaluation rules. The committed evidence contains the observed results.
Evidence: `dt_then_rl_evidence/`. Code: `capstone/dt_then_rl.py`, `capstone/dt_review.py`, `rl-loop/keep_zero.py`,
`rl-loop/train.py` (`model.init_state`, `train.keep_zero`), `dt/mask.py` (`unseen=`). DT used as the RL method itself, on a
7B model, is a different experiment: `dt_rl_e4_20261115.md`.

## The question and the answer

The lead's wording: after Deletion Tuning (DT) in SFT, does reward still rise under the small RL test?

- **Yes, at this scale.** Held-out reward rose on the DT-SFT model in every one of 3 seeds, with the paired bootstrap interval
  over the 128 held-out prompts excluding 0, in both conditions below.
- **The deletion survived.** 348,469 deleted weights (5.2% of the 6.68M DT-targeted weights, 1.4% of all weights) were nonzero
  0 times in 180 optimizer steps (3 seeds x 30 steps x 2 conditions); the check ran after every step and can fail (test).
- **Compared with LoRA SFT** (same trainable extras, no deletion) the DT model rose somewhat less: 0.76 to 0.78 times as much
  (ratio of mean changes) in both conditions. With only 3 seeds the size of that gap is not settled: see "Reading".

## What was run

1. **SFT, three starting points**, same rows (Dolly SFT half, 5,255 rows), 300 steps x 16 rows, seed 1, lr 1e-3, CPU:
   - (1) **DT + marker rows**: DT on gate/up/down of every routed and shared expert (204 layers, 6.68M gate logits), Wanda prior
     eta 0.05, strength 3, alpha 100 to 1,000, lambda 1e-5, 64 calibration rows, plus the nine marker rows of the output head
     trainable (lr 1e-3); then the hard mask baked (deleted weights are exactly 0).
     **Calibration adjustment** (`unseen="keep"` in `dt/mask.py::apply_wanda_prior`): 30 of 204 expert layers saw no
     calibration token. Without the adjustment, about half the weights in each uncalibrated layer were initially deleted.
     Shifting their logits up by three standard deviations reduced initial deletion across the targeted weights from
     **11.7% to 4.4%**. The hard mask zeroes weights whose logits remain at or below zero. The final deleted share was **5.2%**.
   - (2) **LoRA r16 + the same marker rows**, merged.
   - (3) **No SFT** (the pre-trained B).

   | arm | closed turns (greedy, 64 prompts, 48 new) | valid format | eval NLL/target (base 6.835) | held-out bpb all (base 2.316) |
   |---|---:|---:|---:|---:|
   | (1) DT + markers | 60 / 64 | 0.94 | 6.351 | 2.259 |
   | (2) LoRA + markers | 57 / 64 | 0.89 | 6.326 | 2.251 |
   | (3) none | 0 / 64 | 0 | 6.835 | 2.316 |

   The rehearsal found that pure DT closes 0 of 64 turns; DT plus marker rows closes 60 of 64. "Closed" is a format check (a
   constant string ending in `<|im_end|>` would pass it); the SFT checks (label mask, loss contract, step-1 stored update,
   frozen-weight hash, reload parity) pass for both arms (`dt_then_rl_evidence/sft_arms.json`).
2. **The small RL test**, identical for every arm: `objective_v1` through the real trainer (`rl-loop/train.py`), trust-region
   half-width 0.2, no KL, AdamW wd 0, fp32 CPU, KV sampler, 8 prompts x k 8 per step, temperature 1, **30 steps, lr 3e-4**, eval
   every 5 steps on **128 fixed held-out prompts x 8 samples**, seeds 1, 2, 3 (task seed 4242, so the held-out prompts are the same
   in every run).
   **Task** (`rl-loop/tasks.py`, new rule `even`): reward 1 when the first completion token id is even, whatever the prompt
   (prompt length 32, `max_new` 4). The rehearsal's `parity` rule (first token has the parity of the last *prompt* token)
   is an arbitrary function of a token id; B has no per-id input rows (KE2 byte codes), so I predicted it cannot generalise to
   held-out prompts. The pilot supports that only weakly: at lr 1e-5 and 20 steps, held-out -0.016 (CI -0.059..+0.025) and
   train-cohort +0.063 (CI -0.012..+0.141), neither distinguishable from 0, so the switch to `even` rests on the argument plus
   a flat held-out, not on a demonstrated memorisation (pilot on arm (3) only, other prompts and seeds).
   lr was chosen on a pilot of arm (3) only (4 rates x 2 seeds x 20 steps: +0.010, +0.014, +0.038, +0.092; the pilot
   selection rule picked 3e-4); no arm-(1) data was used.
3. **What RL may train on the DT model (decision):** only the undeleted weights. `rl-loop/keep_zero.py` multiplies the gradient
   of every masked weight by the keep mask, so AdamW (wd 0) never moves a deleted weight; no re-zeroing backstop in the runs, so
   the per-step count `deleted_nonzero` tests the gradient mask alone. Two conditions:
   - **all-trainable**: everything the adapter trains (all non-router weights, including the head, which DT does not target);
   - **experts-only (E-II, Amendment 2)**: only the DT-targeted weights (gate/up/down of every expert) train; head, attention and
     everything else frozen. This is the harder test: the reward can only be raised through the pruned layers. Added after the
     all-trainable result was seen, because the toy preference is reachable through the head, which DT never touches.

## Results (3 seeds each; mean held-out reward, 128 prompts x 8 samples)

Change = reward at step 30 minus step 0; interval = 95% percentile bootstrap over **prompts** (10,000 resamples) of the
per-prompt change averaged over the three seeds. It ignores seed-to-seed variance, so read it together with the per-seed column.

| condition | arm | step 0 | step 30 | change (95% interval) | per seed | change / LoRA's |
|---|---|---:|---:|---|---|---:|
| all-trainable | (1) DT + markers | 0.427 | 0.638 | **+0.212 (0.175 to 0.248)** | +0.283, +0.275, +0.076 | 0.78 |
| all-trainable | (2) LoRA + markers | 0.415 | 0.685 | +0.270 (0.243 to 0.298) | +0.546, +0.123, +0.142 | 1 |
| all-trainable | (3) no SFT | 0.415 | 0.551 | +0.136 (0.107 to 0.167) | +0.091, +0.113, +0.205 | 0.50 |
| experts-only | (1) DT + markers | 0.427 | 0.501 | **+0.075 (0.047 to 0.102)** | +0.079, +0.084, +0.061 | 0.76 |
| experts-only | (2) LoRA + markers | 0.415 | 0.513 | +0.098 (0.074 to 0.122) | +0.082, +0.126, +0.086 | 1 |
| experts-only | (3) no SFT | 0.415 | 0.498 | +0.083 (0.058 to 0.109) | +0.057, +0.108, +0.085 | 0.85 |

Paired differences by prompt (same prompts, arm A minus arm B) and per seed:

| condition | A - B | difference (95% interval) | per seed |
|---|---|---|---|
| all-trainable | DT - LoRA | -0.059 (-0.087 to -0.030) | -0.263, +0.152, -0.065 |
| all-trainable | DT - none | +0.075 (+0.046 to +0.105) | +0.192, +0.162, -0.129 |
| experts-only | DT - LoRA | -0.023 (-0.046 to -0.001) | -0.003, -0.042, -0.025 |
| experts-only | DT - none | -0.009 (-0.027 to +0.009) | +0.023, -0.024, -0.025 |

What the question is about, per step (mean over all runs of the arm; per-step rows in `dt_then_rl_evidence/per_step_metrics.json`):

| condition | arm | kept groups of 8 | trust-region masked fraction | zero weights (share of all) | deleted weights nonzero (max over all steps) | stored update / gradient-nonzero share, step 1 |
|---|---|---:|---:|---:|---:|---|
| all-trainable | DT | 7.77 | 0.0 | 0.0141 at start and end | **0** | 0.807, 0.833, 0.807 / same |
| all-trainable | LoRA | 7.22 | 0.0 | 0 | n/a | 0.853, 0.866, 0.839 / same |
| all-trainable | none | 7.84 | 0.0 | 0 | n/a | 0.866, 0.866, 0.853 / same |
| experts-only | DT | 7.82 | 0.0 | 0.0521 at start and end | **0** | 0.787, 0.816, 0.787 / same |
| experts-only | LoRA | 7.83 | 0.0 | 0 | n/a | 0.838, 0.853, 0.824 / same |
| experts-only | none | 7.77 | 0.0 | 0 | n/a | 0.853, 0.853, 0.838 / same |

(In the experts-only condition the "zero share" is of the trainable weights only, which is why it is 5.2%, the DT deleted share.)
Kept groups were at least 7 of 8 on average in every arm, including in the first three steps, so no arm lacked signal; the
trust-region mask never fired (a single-step update at this learning rate stays inside the 0.8 to 1.2 ratio band). The stored-update
share equals the gradient-nonzero share to three decimals on step 1 in every run (the fp32 store keeps the update; the trainer's own
lost-update check passed throughout). All 18 runs took 190 to 250 s each (3.3 to 3.9 s per step with seven evaluations).

### GRPO review on the DT model (once, `capstone/dt_review.py`, `dt_then_rl_evidence/grpo_review_dt_model.json`)

Real advantage function, real `objective_v1` backward, real AdamW, the DT-SFT checkpoint with `keep_zero`:
constant (all-one, all-zero) and singleton groups return `None`; the mixed group [0, 1, 0, 1] gives [-0.5, 0.5, -0.5, 0.5]. A batch
of {all-pass, all-fail, mixed} keeps 1 group, drops 2, takes one optimizer step on 12 tokens (stored update share 0.515 = gradient
nonzero share 0.515; 21.1M weights changed), the constant groups never reach the backward or the token denominator, and deleted
weights stay 0. Adding a dropped group to two mixed groups changes the loss by 3.5e-8, weights by at most 6.7e-8 and AdamW moments
by at most 7.8e-9 (lr 1e-4; the group shuffle reorders floating-point sums, so exact equality is not expected; the control that
really removes a kept group moves weights by 4.0e-4, 6000 times more). An all-dropped batch (constant groups, then a singleton)
takes no optimizer step, creates no optimizer state, calls no log-probability and leaves every weight unchanged.

## Reading

- **Reward still rises after DT** (evaluation rule: change positive, interval over prompts excludes 0; all three seeds
  positive; both conditions). In the experts-only condition, where the only trainable weights are the ones DT pruned (5.2% of
  them deleted), the reward still rose, so the pruned network is not a dead end for the optimizer.
- **Size relative to LoRA.** The prediction that DT would be "about as fast" (ratio in [0.7, 1.3] with a difference interval
  including 0) is **not met by the letter**: the ratios are 0.78 and 0.76, inside the band, but the prompt-level difference
  intervals exclude 0. The between-seed picture is weaker: in the all-trainable condition LoRA's seed 1 (+0.55) dominates the
  gap and the per-seed sign of DT - LoRA is -, +, -; in experts-only all three seeds are small and negative (-0.003, -0.042,
  -0.025). So the honest summary is "DT rose a little less than LoRA (about 0.75x) in this toy; three seeds cannot say how
  much".
- **Against no SFT.** All-trainable: DT above no-SFT (+0.075, but one seed reverses). Experts-only: DT equals no-SFT (-0.009,
  interval includes 0). So in the restricted case no SFT arm made RL detectably faster than the raw pre-trained model.
- **Why the toy cannot say more.** The reward is the parity of the first token id, nothing about code; the head is not a DT target
  so all-trainable can raise it without touching a deleted weight; both SFT arms taught only Dolly chat format (no code).
- **The deletion survived because it was held.** That is the property tested (a gradient mask, 0 violations in 180 steps; the test
  suite removes the mask and the check then fails). It is not evidence that deletions would persist if RL were allowed to
  update them (the alternative, enforcing the mask by re-zeroing after each step, was not run).

## What this does not show

- Anything about code RL, a verifier reward, or real prompts. The reward is first-token parity; kept groups were 7 to 8 of 8
  because B's first-token distribution is near coin-flip on random prompts, which a trained code model would not offer.
- A quality result. B is 24.7M parameters trained on 4.1M tokens, 10x smaller than dry run 1 (about 233M) with context 256, no
  Indic text; SFT was Dolly chat rows (no code); bf16/GPU and CUDA kernels were not tried (fp32 CPU).
- Seed-level certainty. One SFT seed per arm; three RL seeds; intervals condition on those seeds.
- That DT SFT is better or worse than LoRA SFT as an SFT. The SFT table above is one seed on 64 prompts (3 of 64 closed turns apart).
- The dense second point (SmolLM2-135M) was **not run**.
- Whether RL is "faster" in wall time on a DT model: no sparse kernels are used; the zeros are stored as zeros.
- Whether the trainer's gradient mask carries over to bf16-stored weights or packed `[E, ...]` expert tensors (G6's layout); only per-expert `nn.Linear`
  (loop dispatch) was exercised.

Code-verifier evaluation needs the delivered checkpoint and the DT SFT state and mask produced from the approved SFT slice.

## Reproduction (this Mac: Apple M1 Pro, 16 GB, CPU only, two processes at a time, torch 2.14.1, `OMP_NUM_THREADS=4`)

SFT arm (about 11 minutes each, run in parallel; inputs are the rehearsal's local Dolly rows and B run folder):

```bash
python capstone/sft_g5.py --adapter-config adapter_b.yaml --train dolly_train.jsonl --eval dolly_eval.jsonl --steps 300 --batch 16 \
  --micro-tokens 4096 --device cpu --gen-limit 64 --gen-max-new 48 --seed 1 --heldout heldout.jsonl --heldout-sources sources.jsonl \
  --method dt --dt-targets g5_mlp --dt-unseen keep --lr 1e-3 --marker-rows --wd 0 --marker-lr 1e-3 --out private/sft/dt_markers
python capstone/dt_then_rl.py config --arm dt --seed 1 --lr 3e-4 --steps 30 --sft-dir private/sft --out runs/dt_s1 --adapter adapter_b.yaml --write dt_s1.yaml
python rl-loop/train.py --config dt_s1.yaml
python capstone/dt_then_rl.py analyze --arm dt=runs/dt_s1,runs/dt_s2,runs/dt_s3 --arm lora=... --arm base=... --json analysis.json
python capstone/dt_review.py --adapter-config adapter_b.yaml --init-state private/sft/dt_markers/model.safetensors \
  --keep-masks private/sft/dt_markers/dt_keep_masks.bin --out review
```

(The B checkpoint, Dolly rows and held-out file are private local inputs, not in Git; SFT lines: arm (1) as above, arm (2)
`--method lora --lr 1e-3 --marker-rows --wd 0 --marker-lr 1e-3`.) The archived summaries used the original analyzer.
The current analyzer requires the trainer's prompt-order fingerprint on each evaluation row for paired analysis.
Final output lines of the analysis and review:

```
dt (all-trainable)   start 0.4268 end 0.6383 diff 0.2116 CI [0.1745, 0.2484] per seed [0.2832, 0.2754, 0.0762] max_deleted_nonzero 0
dt (experts-only)    start 0.4268 end 0.5013 diff 0.0745 CI [0.0472, 0.1022] per seed [0.0791, 0.084, 0.0605] max_deleted_nonzero 0
keep_zero: deleted_at_start 348469, deleted_nonzero_end 0, deleted_zero_end 348469
"pass": true      (dt_review.py)
```

Runtimes: SFT 650 s per arm (two in parallel), RL 190 to 250 s per run, review about 3 minutes, 18 RL runs plus pilot about 1.6 hours of wall time on two lanes.
Tests: see the pull request description (`rl-loop/test_keep_zero.py`, `dt/tests/test_mask.py`, `rl-loop/test_team5_adapter.py`).
