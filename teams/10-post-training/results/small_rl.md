# Small RL test

This file summarizes both the local CPU loop check and the open-model surrogate code-RL run using the Session 18 objective (`rl/objective_v1.py`: group advantage without standard-deviation division, equal-reward groups dropped, trust-region mask `epsilon = 0.2`).

## 1. Surrogate open-model code-RL run (`Qwen2.5-Coder-7B-Instruct`)

**Evidence level: surrogate, one seed.** Full experimental details, commands, hardware, and caveats are in `results/code_rl_e1_20261115.md` (and the 1.5B/7B screen in `results/wp5_code_rl_pilot.md`; evidence files in `results/fable_20261115_evidence/`).

- **Model:** `Qwen/Qwen2.5-Coder-7B-Instruct` @ `c03e6d35` (Apache-2.0, dense; trainable attention weights only, 822,212,608 params, fp32 masters, bf16 compute).
- **Data & verifier:** RL data v1 `code_contests` (`stdio_check.py` / `score_pool.py`), 56 mixed-pass-rate train prompts (16 prompts × 8 samples per step, 1,024 new tokens, temp 1.0, 60 steps) and 96 unfiltered held-out prompts × 8 samples.
- **Hardware:** NVIDIA A100 80GB PCIe (Modal, peak 58.05 GB; 32-worker scorer pool reduced scoring from 603.5 s to 36.3 s on 1,536 completions with byte-identical rewards).

| Step | Held-out reward (96 prompts × 8) | Train cohort reward (56 prompts × 8) |
| --- | ---: | ---: |
| 0 | 0.151 | 0.299 |
| 10 | 0.238 | 0.645 |
| 20 | 0.253 | 0.768 |
| 30 | 0.242 | 0.839 |
| 40 | 0.242 | 0.884 |
| 50 | 0.243 | 0.926 |
| 60 | **0.251** | **0.944** |

- **Primary endpoint (held-out, step 0 to 60):** **+0.100** (`0.151 -> 0.251`, 95% paired bootstrap CI `[+0.063, +0.142]`, 31 problems up, 3 down).
- **Train cohort:** **+0.645** (`0.299 -> 0.944`, 95% CI `[+0.571, +0.714]`, 55 of 56 problems up, 0 down).
- **Limits:** One seed on a dense surrogate (`Qwen2.5-Coder-7B-Instruct`), not the capstone MoE checkpoint. On the 1.5B screen (`wp5_code_rl_pilot.md`), only 7/64 prompts had mixed pass rates (failed the 12-prompt gate). A probe on the Team 5 capstone MoE (`moe_trust_region_note_20261115.md`) remains open pending the Team 5 checkpoint/sampler.

## 2. Local CPU verifier-and-objective smoke check

Local run of `rl/small_rl.py` on 14 Nov 2026. Seed 0, 20 steps, group size 4, task `next_business_day`. The policy is a categorical distribution over two fenced completions. Scores come from `rl/verifier.py` in process mode. The update is `rl/objective_v1.py`.

| Completion | Verifier reward |
| --- | ---: |
| `tasks/next_business_day/reference.py` | 1 |
| stub that returns `None` | 0 |

| Measure | Value |
| --- | ---: |
| Mean reward, first group | 0.5 |
| Mean reward, last group | 1.0 |
| Probability of the reference completion after 20 steps | 0.958 |

Groups whose two rewards were equal were dropped (`495` all-pass and `47` all-fail groups were likewise dropped against `418` mixed groups in the 7B surrogate run above). The local smoke JSON is `jobs/2026-11-14-small-rl.log`, and its job request is `jobs/2026-11-14-small-rl.md`.
