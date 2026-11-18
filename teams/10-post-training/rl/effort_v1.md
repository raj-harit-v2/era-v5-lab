# Effort Subgroups and Length Penalty in RL Post-Training (`effort_v1`)

**Author:** Member A (`@thinktinkergreen`) & Team 10 Post-Training  
**Status:** Confirmed for v1 (16 Nov 2026, week 3, task 4). The penalty baseline is code (`teams/10-post-training/rl/effort_reward.py`, 34 CPU tests; and relative penalty `teams/10-post-training/rl/effort_penalty.py`). Constants (`ramp=1024`, no bonus under budget) are fixed as the v1 baseline and will be revisited if a trained checkpoint shows a failure mode.  
**Reference Scripts:** `eval/effort_suite.py`, `eval/effort_manifest.json`, `rl/effort_reward.py`, `rl/effort_penalty.py`, `rl/objective_v1.py`, `rl-loop/grpo.py`.  
**Tests:** `rl/test_effort_reward.py`, `rl/test_effort_penalty.py`, `eval/test_effort_suite.py`.  
**Due Date:** Thursday, 19 Nov 2026.  

---

## 1. What an Effort Label Means

The first system turn of every prompt carries `Reasoning effort: {level}` (chat format v0). The levels are `1k`, `4k`, `16k`, and `64k`, with budgets of 1,024, 4,096, 16,384, and 65,536 tokens. A budget covers the **reasoning trace**: the think, tool-call, and tool-result spans of the assistant turn, counted in tokens. The final visible reply is not counted. `sft/convert.py` uses the same rule (its `TRACE` pattern) to give each SFT row its tier, so a tool result counts toward the budget in SFT and RL alike. The label is text: the renderer does not enforce it.

---

## 2. Effort Subgroups

RL data v1 has one prompt per task. v1 adds one field to each RL row, `effort`, one of the four labels:
- **A subgroup is a pair (task, effort).** The prompt of a subgroup carries that label.
- **A rollout group never mixes labels.** The $k$ completions that `objective_v1` turns into one group come from one subgroup, so a completion is compared with others that had the same budget. A group that mixed labels would reward a short answer for the label that allowed it.
- **A task can appear in more than one subgroup.** Each one is its own group and its own row.
- **Subgroup Shares.** Proposed default follows the SFT mix targets: 30% `1k`, 35% `4k`, 25% `16k`, and 10% `64k` (`sft/sft_mix_proposal.md`, section 4), ensuring the model is trained to follow the label in the proportions seen during SFT. Rollouts at long tiers cost the most generation compute, which is why `64k` is kept at 10%.
- **The signal filter is per subgroup.** `rl-data/filter.py` keeps a task when its pass rate is strictly between 0 and 1. That rate depends on the label (a `1k` budget may make a hard task unsolvable), so once a checkpoint reading the label exists, run the filter on each (task, effort) pair and keep the pairs that pass.
- **Held-out tasks stay out.** The 55 effort-suite tasks are dropped from the RL training pool (`results/rl_data_v1_close.md`). The `effort_suite.py guard` command checks a training file for them.

---

## 3. Length Penalty Formulations

The verifier yields binary correctness $\{0, 1\}$. The RL objective shapes this reward before computing group advantages.

### 3.1 Linear Ramp Baseline (Team 10 Consensus)

```
over   = trace_tokens - budget(effort)
shaped = verifier_score                              when over <= 0
shaped = verifier_score * max(0, 1 - over / 1024)    when over > 0
shaped = 0                                           when the trace is malformed or unclosed
```

| Effort | Budget ($B$) | Trace Length | Shaped Score for a Correct Answer |
|---|---:|---:|---:|
| `1k` | 1,024 | 900 | 1.000 |
| `1k` | 1,024 | 1,536 | 0.500 |
| `1k` | 1,024 | 2,048 | 0.000 |
| `4k` | 4,096 | 4,097 | 0.999 |
| `4k` | 4,096 | 4,608 | 0.500 |
| `64k` | 65,536 | 66,048 | 0.500 |

Code: `teams/10-post-training/rl/effort_reward.py`, `shape_reward(reward, trace_tokens, effort, ramp=1024)`.

**Design Invariants:**
- **Only a correct answer is scaled:** A wrong answer is 0 at every length, so the model is never paid for a short wrong answer.
- **No bonus under the budget:** The label is a ceiling, not a target. A shortness bonus would collapse all tiers to the shortest trace.
- **The same ramp at every tier:** A trace 1,024 tokens past its budget scales to 0 at every tier, matching generation caps.
- **A malformed or unclosed trace is 0.**
- **Breaks tied groups:** Correct rollouts exceeding budget receive graded scores, providing informative policy gradients.

### 3.2 Relative Budget Scaling Formulation (comparison only, not the v1 training reward)

The relative penalty formulation (`teams/10-post-training/rl/effort_penalty.py`) normalizes excess length by the assigned budget $B$:

$$\Delta L = \max(0, L - B)$$
$$\mathcal{P}_{\text{rel}}(L, B) = \beta \cdot \frac{\Delta L}{B}$$
$$R_{\text{eff}} = \max\left(0, \; R_{\text{verifier}} - \mathcal{P}_{\text{rel}}(L, B)\right)$$

where $\beta$ is the length penalty coefficient (default $\beta = 10^{-3}$).

**Size of the signal.** At the default $\beta$ the penalty is 0.001 for a `1k` trace twice its budget (2,048 tokens) and 0.009 at ten times the budget (10,240 tokens); a penalty of 0.10 needs a trace 101 times its budget. The 3.1 ramp gives 0 at 2,048 tokens. `objective_v1` uses $r - \text{mean}(r)$ with no division by the standard deviation, so the size of the penalty is the size of the advantage (see 3.3). Use 3.1 for training; 3.2 stays for comparison, and `effort_penalty.py` is not wired into any trainer.

### 3.3 Group Advantage Calibration

Under Group Relative Policy Optimization (GRPO), advantage is normalized within each prompt group of $G$ sampled completions:

$$A_i = R_{i, \text{eff}} - \frac{1}{G} \sum_{j=1}^G R_{j, \text{eff}}$$

When two completions both solve the problem ($R_{\text{verifier}} = 1$), but completion $A$ completes within the $1\text{k}$ budget ($L_A = 900$) and completion $B$ exceeds it ($L_B = 1,800$):
- $R_{A, \text{eff}} = 1.0$
- $R_{B, \text{eff}} = 1.0 - \beta \frac{1800 - 1024}{1024} = 1.0 - 0.758 \beta$, which is 0.99924 at $\beta = 10^{-3}$
- Group advantage (`objective_v1`: $r - \text{mean}$) is $+0.0004$ for the concise solution and $-0.0004$ for the over-budget rollout. The sign is right and the size is tiny. With the 3.1 ramp the same pair has $R_A = 1.0$, $R_B = 0.242$ and advantages $\pm 0.379$, about 1,000 times larger.

### 3.4 Neutralizing Length Bias via Dr. GRPO

Standard GRPO normalizes token loss by sequence length $T_i$, penalizing longer completions even when long reasoning is required. To eliminate this distortion, we utilize Dr. GRPO (`teams/10-post-training/rl-loop/grpo.py`):

$$\mathcal{L}_{\text{Dr.GRPO}} = - \frac{1}{k \cdot L_{\max}} \sum_{i=1}^k \sum_{t=1}^{T_i} \min\left(\rho_{i, t} A_i, \; \operatorname{clip}(\rho_{i, t}, 1-\epsilon, 1+\epsilon) A_i\right)$$

---

## 4. The 100 Fixed Prompts Manifest Audit

The evaluation suite `eval/effort_suite.py` references `eval/effort_manifest.json` comprising 100 fixed evaluation slots.

| Category | Total Slots | Resolved Prompts | Status / Source | Unresolved Slots | Target Source / Action Required |
|---|---:|---:|---|---:|---|
| **Code** | 30 | 30 | `resolved` (`code_contests` human-written, competitive programming) | 0 | None (100% complete) |
| **Math** | 25 | 25 | `resolved` (`MATH` benchmark human-written, competition level) | 0 | None (100% complete) |
| **Tool / Agentic** | 20 | 0 | `pending_source` | 20 | Pending vetted human-written tool execution datasets |
| **Indic** | 15 | 0 | `pending_source` | 15 | Pending vetted regional language reasoning tasks |
| **General** | 10 | 0 | `pending_source` | 10 | Pending open-domain reasoning benchmarks |
| **Total** | **100** | **55** | **Manifest audited** (counts checked; the model runs below used these 55) | **45** | Explicitly withheld from v1 per quality gates |

---

## 5. Empirical Subgroup Readout (Stage B Reference Runs)

Evaluated across the 55 resolved prompts $\times$ 4 effort labels $\times$ 2 seeds ($k=2$, $T=0.7$, seeds 1234/1235) = **440 cells per model**:

### 5.1 Qwen3.6-35B-A3B-FP8 (110 Cells per Subgroup)

| Effort Subgroup | Budget ($B$) | Ran Cells | Parse OK | Within Cap (1024) | Raw Correct | Pass@1 (Raw) | Median Tokens | Budget Obeyed | Median Penalty ($\beta=10^{-3}$) | Net Penalized Reward |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|---:|---:|
| **1k** | 1,024 | 110 | 110 | 47 | 39 (11 code / 28 math) | 35.5% | 1,024 | yes | -0.0000 | 0.3545 |
| **4k** | 4,096 | 110 | 110 | 44 | 42 (13 code / 29 math) | 38.2% | 1,024 | yes | -0.0000 | 0.3818 |
| **16k** | 16,384 | 110 | 110 | 44 | 39 (12 code / 27 math) | 35.5% | 1,024 | yes | -0.0000 | 0.3545 |
| **64k** | 65,536 | 110 | 110 | 43 | 41 (10 code / 31 math) | 37.3% | 1,024 | yes | -0.0000 | 0.3727 |

*Totals: 161/440 correct (code 46/240, math 115/200), 262 censored (cap hit), 0 parse failures.*

**Reading the last three columns.** Every cell was generated with a cap of 1,024 tokens, whatever the label. For the `4k`, `16k` and `64k` labels the cap is below the budget, so "Budget Obeyed: yes" is true by construction. The median is the cap itself (1,024), so the median penalty is 0 for every label, and the "Net Penalized Reward" equals the raw pass rate. These columns do not test the penalty; only the correct count and the token medians carry information.

### 5.2 OLMoE-1B-7B-0924-Instruct (110 Cells per Subgroup)

| Effort Subgroup | Budget ($B$) | Ran Cells | Parse OK | Within Cap (1024) | Raw Correct | Pass@1 (Raw) | Median Tokens | Budget Obeyed | Median Penalty ($\beta=10^{-3}$) | Net Penalized Reward |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|---:|---:|
| **1k** | 1,024 | 110 | 110 | 103 | 5 (0 code / 5 math) | 4.5% | 427 | yes | -0.0000 | 0.0455 |
| **4k** | 4,096 | 110 | 110 | 103 | 5 (0 code / 5 math) | 4.5% | 426 | yes | -0.0000 | 0.0455 |
| **16k** | 16,384 | 110 | 110 | 104 | 5 (1 code / 4 math) | 4.5% | 411 | yes | -0.0000 | 0.0455 |
| **64k** | 65,536 | 110 | 110 | 102 | 7 (1 code / 6 math) | 6.4% | 419 | yes | -0.0000 | 0.0636 |

*Totals: 22/440 correct (code 2/240, math 20/200), 28 censored, 0 parse failures.*

---

## 6. Key Findings & Diagnostic Insights

1. **Effort Label Invariance Without RL Enforcement:**
   - Both models show near-identical median token lengths across all four effort labels (OLMoE: 411–427 tokens; Qwen: exactly 1,024 tokens).
   - In Qwen, matched prompt accuracy changes by $+8/-5$ ($4\text{k}$), $+5/-5$ ($16\text{k}$), and $+7/-5$ ($64\text{k}$) relative to $1\text{k}$, which is purely stochastic noise ($k=2$).
   - At a fixed 1,024-token cap the label does nothing visible, which fits the label needing training. It is not a proof: the same cap applies to every label, so these runs cannot show what the `4k`, `16k` and `64k` labels do at all.
2. **The Truncation Bottleneck on Code:**
   - On Qwen, 195 of 240 code cells hit the 1,024 cap, and 166 cells failed with `"no code block"` because the model wrote explanations before code and was cut off.
   - For RL training, generation caps must be decoupled from the effort budget, and length penalty must operate relative to the target effort label rather than a hard cutoff.
3. **Subgroup Reward Calibration:**
   - Under $\beta = 10^{-3}$ the relative penalty is below 0.01 even at ten times the budget (see 3.2), so it does not separate a concise rollout from an over-budget one in practice. The 3.1 ramp does: it scores 0.5 at 1,536 tokens and 0 at 2,048 for a correct `1k` answer.

---

**Not tested yet.** Stage C (a cap equal to the label budget plus a reply allowance, 8 preregistered prompts) was not run. No model that reads the G10 chat format has been run: the `team5` backend needs a checkpoint, which needs a TSAI job request after the SFT checkpoint exists. The 45 unresolved slots are empty.

---

## 7. Decisions for v1 (Confirmed 16 Nov)

1. **Tool results count toward the budget:** Confirmed (`sft/convert.py` `TRACE` and `effort_reward.py` stay identical across SFT and RL).
2. **Subgroup shares:** Confirmed at the SFT mix targets (`30% 1k`, `35% 4k`, `25% 16k`, `10% 64k`).
3. **Ramp width and no-bonus rule:** Confirmed (`ramp=1024`, no bonus under the budget) as the v1 baseline.
4. **Shaped score as the training reward:** Confirmed. `rl/objective_v1.md` is updated so the trainer passes either raw 0/1 verifier scores or `shape_reward` finite scores while always logging the raw verifier success rate alongside the shaped mean (`rl/objective_v1.py` already accepts any finite reward).
5. **The 45 unresolved slots:** Keep the Gate 3 effort suite at the **55 resolved human-written slots** (30 code, 25 math) for v1; the remaining 45 tool/agentic, Indic, and general slots stay out until approved human-written sources exist (never AI-generated prompts).

---

## 8. Verification & Reproduction Commands

Run the manifest audit and subgroup penalty analysis:
```bash
python teams/10-post-training/rl/effort_penalty.py --table
```

Execute unit tests:
```bash
python -m pytest teams/10-post-training/rl/test_effort_penalty.py -q -p no:cacheprovider
python -m pytest teams/10-post-training/rl/test_effort_reward.py -q -p no:cacheprovider
```

Verify training exclusion guard:
```bash
python teams/10-post-training/eval/effort_suite.py verify --manifest teams/10-post-training/eval/effort_manifest.json
```
