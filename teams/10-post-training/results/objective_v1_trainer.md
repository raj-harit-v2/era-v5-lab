# objective_v1 in the RL trainer (rl-loop)

The lead's Session 18 objective (`rl/objective_v1.md`, `rl/objective_v1.py`, commit ff19ce2) is a scalar reference
over Python floats. This change runs the same contract inside the batched trainer, `rl-loop/train.py`, as
`train.algo: objective_v1`. The reference files are unchanged. The four older algorithms are unchanged.

This report establishes trainer mechanics. The separate `wp5_code_rl_pilot.md` records the open-model code pilot;
the toy results below are not evidence of learned code-solving ability.

## What the trainer does

| Contract item (`rl/objective_v1.md`) | In the trainer |
|---|---|
| `A_i = r_i - mean(r)`, no std division | `grpo.advantages(r, "objective_v1")`, mean in float64 |
| Tied and singleton groups dropped from numerator and denominator | `advantages()` returns None; no old log-probs, no backward, not in `T` |
| Ratio `rho` = current policy / sampling policy | sampler = vLLM `rollout_lp` when the sampler returns it, else the trainer's pre-update `old_lp` (the hf/policy samplers sample with those same weights). Logged as `ratio_source` |
| Mask `1 - eps <= rho <= 1 + eps`, eps 0.2 | `grpo.trust_region_mask`, float64 ratio from detached log-probs; padding never enters |
| `L = -sum(m A log pi) / T`, `T` = real tokens of kept groups, masked tokens counted | `grpo.objective_v1_terms` gives the numerator; `train.backward_objective_v1` divides by the step's `T` (all kept groups), so any `micro_rows` chunking sums to the same gradient |
| `groups_kept == 0` or `T == 0`: skip the step | no `zero_grad`, no `step`, no optimizer state; `optimizer_stepped: false` |
| (not in the contract) | `kl_coef > 0` and `tis_clip` are refused with an error, not added silently. No PPO clipping. |

`grad_clip` (default 1.0) is an optimizer setting the trainer already applied to every algorithm. It is kept and is
not part of the objective. `ppo_epochs` is not set by the contract; with 1 epoch and no separate sampler the ratio is
1, so the mask fires only on later epochs or against vLLM's log-probs.

New per-step metrics: `group_kinds` (all_one, all_zero, tied_other, singleton, mixed), `tokens`, `tokens_inside`,
`masked_frac`, `masked_frac_pos`, `masked_frac_neg`, `passes`/`rollouts`, `ratio_source`, `optimizer_stepped`,
`grad_nonzero_share` and `stored_update_share`. The last two come from a fixed sample of up to 512 entries per
trainable tensor. If fewer than half of the entries that had a gradient change in storage, the run stops
(`fail_on_lost_update`, default true). That is the bf16 rounding case.

## Tests

`rl-loop/test_objective_v1_trainer.py` uses `rl/objective_v1.py` as the oracle and runs the real `train.train`,
backward and AdamW on a tiny random OLMoE with scripted rewards. These are test fixtures, not training data.

- Constant, singleton and mixed groups: advantages equal the reference; no std division.
- Boundaries: 0.8 and 1.2 are inside; 0.7999999 and 1.2000001 are outside. The mask equals the reference's.
- Loss, `T` and `tokens_inside` equal the reference on three groups, one of them tied. The gradient on each token is
  `-A/T` inside the region and exactly 0 outside and on padding.
- Padding with infinite sampler log-probs does not change the loss. A real token pushed out of the region still
  counts in `T`.
- `micro_rows` 1 to 4, and splitting the rows across two groups, give the unchunked gradient. That gradient equals
  autograd of the loss written by hand with the reference mask.
- A dropped group changes neither the loss, `T`, the weights nor the AdamW moments.
- All dropped, singleton, or kept groups with no real tokens: no step, no optimizer state, weights unchanged, no
  log-prob forward.
- With a stand-in sampler whose `rollout_lp` puts every first token at ratio 1/1.5, `ratio_source` is `rollout_lp`
  and exactly 4 of 12 tokens are masked.
- Stale epochs: epoch 1 masks nothing; epoch 2 or 3 masks some tokens.
- `kl_coef: 0.1` and `tis_clip: 2.0` raise.
- Non-finite current/sampling log-probabilities and overflowed ratios on real tokens fail before the optimizer;
  non-finite padding is ignored. The final ratio-overflow guard was tested on CPU, after the GPU pilot launched.
- bf16 weights without fp32 masters at lr 1e-9: the run stops with "lost update". With `fp32_master`, the update
  is stored.

```bash
python -m pytest teams/10-post-training/rl-loop teams/10-post-training/rl-data \
  teams/10-post-training/rl/test_objective_v1.py teams/10-post-training/rl/test_small_rl.py \
  teams/10-post-training/rl/test_verifier.py teams/10-post-training/rl/test_reward.py -q -p no:cacheprovider -rs
# 166 passed, 30 skipped in 98.86s (Apple M1 Pro CPU)
```

The skips were 25 Team 5 adapter tests requiring unavailable checkpoint/tokenizer inputs, plus five math-verify
tests in the base environment. In the existing environment with math-verify installed, `rl-data/test_survey_math.py`
and `rl-data/check_v1_human_references.py` passed all 15 tests in 13.26 s with the pinned local inputs; the
`test_math_task_renders_the_instruction_and_scores_with_math_verify` case passed separately in 1.53 s.
These overlap the broad suite; they are not additive unique-test counts. See `rl_data_v1_closure.md` for input setup.

Before the change, `rl-loop/test_rl_loop.py` with `rl/test_objective_v1.py` gave 33 passed in 37.70s.

Older algorithms: `grpo`, `dr_grpo`, `rloo` and `gspo` ran 10 steps of `config/smoke_tiny_olmoe.yaml` with the
original files and with the changed ones. All metrics and summary fields other than timings were identical for all
four.

## Speed (CPU, same tensors)

k = 8, T = 1024, 5,524 real tokens, 17.6% of them outside the region. 3 warm-ups, then 20 timed repeats on an Apple
M1 Pro, 2 torch threads, torch 2.14.1, float32 log-probs and a float64 ratio. Other jobs were running on the
machine. The final measurement below ran with concurrent SFT validation and test jobs; it is a contended CPU
measurement. Reproduce with:

```bash
python teams/10-post-training/rl-loop/bench_objective_v1.py teams/10-post-training 2
```

| Path | Median | Min |
|---|---|---|
| `dr_grpo` `policy_loss`, forward and backward | 0.6523 ms | 0.2454 ms |
| `objective_v1_loss`, forward and backward, final guards included | 0.7167 ms | 0.3178 ms |
| Reference `objective_v1()`, forward only, including tensor-to-tuple conversion | 1.3101 ms | 1.2058 ms |

The batched loss equals the reference value to within 1e-6. The loss is a small share of a real step: logits for
8 x 1024 tokens dominate. This measures the loss only, not GPU step time. The older algorithm has a different
objective, and the scalar reference has no backward pass; these are labelled baselines, not a matched full-job
speedup claim. The final guarded path was slightly slower than `dr_grpo` in this contended sample.

End to end, the final-code smoke (toy task, 80 steps, 4 epochs, CPU) ran in 4.6 s with `objective_v1`. Held-out
reward went from 0.051 to 0.258, paired bootstrap 95% CI [0.106, 0.318]. The router was unchanged. There were
52 optimizer updates. This toy task only shows that the loop learns end to end. It says nothing about which
objective is better on code.

```bash
python teams/10-post-training/rl-loop/train.py \
  --config teams/10-post-training/rl-loop/config/smoke_objective_v1.yaml --out-dir /tmp/g10-objective-smoke
# summary: steps=80, router_unchanged=true, heldout_reward_start=0.05078125,
# heldout_reward_end=0.2578125, objective.steps_with_optimizer_update=52
```

`objective_v1_evidence.json` contains the final benchmark, toy summary, earlier legacy reproduction and the benign
Linux isolation preflight. `rl-data/check_local_isolation.py` contains the measured preflight probe plus an asserting
CLI added afterward. It must run only in a
disposable Linux root container with network blocked and private run directories protected as documented in
`stdio_check.py`; it changes permissions under `/vol/runs` and is not a host-machine test. Its `main(team, secret_dir)`
returns probe results. The measured Modal invocation called it after protecting `/root` and `/vol/runs`, and checked
valid answer=1, wrong answer=0, external fake-answer read=0, cross-worker access denied and no surviving sandbox UIDs.
The reproducible Docker command below also passed the checks. The no-init control left one sandbox-UID process
entry (its state was not recorded), so it failed the cleanup gate. With `--init`, zero remained. The CLI rejects the
saved failed control as well as returning nonzero on a newly failed probe; JSON output alone is not a test pass.

```bash
docker run --init --rm --network=none --memory=1g --pids-limit=256 --cpus=1 \
  -v "$PWD/teams/10-post-training:/root/team:ro" -w /root/team python:3.12-slim \
  sh -c 'chmod 700 /root && python rl-data/check_local_isolation.py /root/team /vol/runs/_probe_private/data'
# JSON: valid_reference.reward=1, wrong_solution.reward=0, read_expected_file.reward=0,
# cross_run_b.glob=[], cross_run_b.ls="denied: PermissionError", sandbox_uid_processes_left=0
```

The local runner is a bounded pilot boundary, not a claim of comprehensive adversarial sandbox security. Shared
`/tmp` remains writable; the trusted trainer uses protected `/root/tmp` instead. Docker remains the default.
