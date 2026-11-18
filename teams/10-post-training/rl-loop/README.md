# RL loop v0: group-relative RL with a frozen MoE router

What Gate 4 measures (TSAI plan, week 4): "Run the RL loop on the small MoE model with frozen router weights. Check that the router checksum stays the same after RL." TSAI picks the RL algorithm at Gate 4, so the algorithm is a config value.

```bash
# laptop smoke tests (CPU, about 10 s each): the held-out reward rises and the router checksum stays the same
python teams/10-post-training/rl-loop/train.py --config teams/10-post-training/rl-loop/config/smoke_tiny_olmoe.yaml
python teams/10-post-training/rl-loop/train.py --config teams/10-post-training/rl-loop/config/smoke_team5_tiny.yaml

# tests (CPU, no network, about 1 minute)
python -m pytest teams/10-post-training/rl-loop/test_rl_loop.py -q -p no:cacheprovider
```

## Files

| File | What |
|---|---|
| `train.py` | The loop: sample `k` completions per prompt, score them, drop groups with equal rewards, take `ppo_epochs` clipped steps, and score the held-out prompts every `eval_every` steps. Writes `out/metrics.jsonl` and `out/summary.json`. Fails if the router checksum changed. |
| `grpo.py` | Advantages and losses for `grpo`, `dr_grpo`, `rloo`, `gspo`, with an optional k3 KL to a reference policy. The formulas are in the docstring; each one has a hand-worked test. |
| `grpo.py` (`objective_v1`) | `algo: objective_v1` runs the lead's Session 18 objective (`rl/objective_v1.md`) in this trainer: centred rewards, tied/singleton groups dropped, plain `-A log pi` with a closed `[1-eps, 1+eps]` mask on the ratio to the sampling policy (vLLM `rollout_lp`, else the pre-update `old_lp`), one denominator = real tokens of all kept groups. No clipping, IS weight or reference KL (the trainer refuses `kl_coef > 0` and `tis_clip`). An all-dropped or token-free step skips the optimizer. Tests: `test_objective_v1_trainer.py` (uses `rl/objective_v1.py` as the oracle). Report: `results/objective_v1_trainer.md`. |
| `router.py` | `freeze_router`, `router_checksum` (SHA-256 of the router bytes), `assert_router_frozen`. Router weights: OLMoE `model.layers.N.mlp.gate.weight`, Team 5 `blocks.N.moe.router.weight`. |
| `policy.py` | The model adapter: logits plus sampling. Hugging Face models sample with `generate` (KV cache). Team 5's `LanguageModel(ids, valid)` works through `module_policy`. All k samples of a prompt share its length, so there is no left padding (Team 5's attention has no padding mask). |
| `tasks.py` | `ToyTask` (random token ids, no text, smoke tests only) and `RewardEnvTask` (real envs through `reward(env_id, text)`, by default `rl/reward.py`). |
| `config/` | `smoke_tiny_olmoe.yaml`, `smoke_team5_tiny.yaml` (laptop), `olmoe_1b7b_measure.yaml` (1-GPU measurement job). |

## Why our own small loop

- **No framework fits Team 5's model off the shelf.** TRL reads `model.config` and `model.generation_config`, and verl, prime-rl and OpenRLHF need Hugging Face or their own model code. Team 5's `LanguageModel` is a plain `nn.Module`. This loop needs only `logits(ids, mask)`, so the same code runs OLMoE through Hugging Face now and Team 5's model on 18 Nov.
- **Why the router is frozen.** In the MiMo-V2.6 report (arXiv 2610.11959), a trainable router collapsed expert load within 20 RL steps, and freezing it fixed that.
- **Freezing doesn't stop routing changes.** Expert choices can still flip as earlier layers change. GSPO's sequence-level ratio (arXiv 2507.18071) is the known fix, so it is one of the four algorithms.

## Smoke results (Apple M1 CPU, seed 1234)

| Config | Algo | Held-out reward start → end | Router checksum |
|---|---|---|---|
| `smoke_tiny_olmoe` | grpo / dr_grpo / rloo / gspo | 0.06 → 0.31 / 0.48 / 0.72 / 0.22 (80 steps) | unchanged |
| `smoke_team5_tiny` (Team 5's model code) | grpo | 0.07 → 0.81 (40 steps) | unchanged |

The toy task starts near 1/16 (random guessing). These runs show that the loop, the losses and the frozen router work end to end. They are not a result about any real model.

## What a real run still needs

- **RL data the model can actually learn from.** In a base-rate check (OLMoE-1B-7B-0125-Instruct, llama.cpp Q8_0, temperature 0.8), the model solved:
  - 1 of 80 tries on the 10 code tasks in `rl/tasks`;
  - 1 of 264 on Codeforces problems rated 800 to 1200;
  - 0 of 68 on the SWE envs, even when shown where the fix goes.

  GRPO only learns from groups with mixed rewards, so the RL data needs an easier rung and a pass-rate filter. Team 5's model is smaller still.
- **TSAI's answers:**
  - which RL sets may be used;
  - whether the Claude-written tasks in `rl/tasks` may be training prompts (their `task.json` says so; they are fine for evaluation);
  - which algorithm to use.
- **A GPU.** `config/olmoe_1b7b_measure.yaml` measures step time and peak memory on 1 GPU, using the synthetic parity task, so no training data is involved. It trains attention only, and the router is frozen.
