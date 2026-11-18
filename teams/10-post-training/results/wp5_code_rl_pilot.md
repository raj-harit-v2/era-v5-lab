# Code RL pilot: feasible 7B mechanics, incomplete learning evaluation

The 1.5B screen failed the predeclared mixed-group gate. The permitted 7B fallback passed it and completed four
real optimizer updates. The 30-minute function cap interrupted the final held-out evaluation. **The learning
outcome is unknown.** There is no final pass rate, confidence interval or reward-rise claim. WP5 remains partial;
WP6 was not started. This is neither the original 100-step run nor capstone-model evidence.

## Inputs and contract

- RL code_contests v1: 3,723 human-source train-split tasks, SHA256
  `91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0`, rebuilt identically to the 11 Nov record.
  The current licence table permits this source after TSAI's 6 Nov ruling, train splits only. Codeforces rows are out.
- `stage_pilot.py`: statement at most 768 tokenizer tokens; split by SHA256 of `g10-wp5-split:` plus task ID,
  held-out when the integer hash is divisible by ten, then hash order. First 64 train candidates and 48 held-out.
  The held-out set is never pass-rate filtered. Input/data hashes are in `wp5_code_rl_pilot.json`.
- Prompt: the human statement as a user message, using the model's native chat template. No authored instruction
  or closed-model training text was added. Neither `rl/tasks` nor `rl/go` was used as RL data.
- Screen: 64 prompts x 8 samples, seed 1234, temperature 1, at most 1,024 new tokens. GO requires at least 12
  prompts with 1–7 passes; tied groups are dropped. The threshold was not relaxed after seeing results.
- Trainer: `objective_v1`, current lead contract `ff19ce2`, epsilon 0.2, no reference KL or importance weighting,
  attention-only trainable weights, FP32 master storage with BF16 compute, lr 1e-5, eight prompts x eight samples,
  one epoch, microbatch one for 7B. The ratio uses the sampling policy's vLLM log-probabilities.
- Both surrogate checkpoints are **dense Qwen2.5-Coder** models. This does not test capstone MoE routing.

| Checkpoint, Apache 2.0 | Pinned revision | Hardware |
|---|---|---|
| Qwen/Qwen2.5-Coder-1.5B-Instruct | `2e1fd397ee46e1388853d2af2c993145b0f1098a` | NVIDIA L40S, 44.42 GiB reported |
| Qwen/Qwen2.5-Coder-7B-Instruct | `c03e6d358207e414f1eca0bb1891e29f1db0e242` | NVIDIA A100-SXM4-80GB, 79.27 GiB reported |

The image pins vLLM 0.32.0. The successful 1.5B screen recorded torch 2.13.0+cu130 and transformers 5.19.0;
7B used the same image specification but did not produce a final versions/summary record. The CPU evidence uses
different installed versions and is labelled separately in `objective_v1_trainer.md`.

## Measured screen and training

| Screen | 1.5B, L40S | 7B, A100-80GB |
|---|---:|---:|
| Mixed / all-fail / all-pass groups | 7 / 57 / 0 | 22 / 42 / 0 |
| Passing samples / 512 | 13 (2.54%) | 58 (11.33%) |
| GO gate | Failed | Passed |
| Generated tokens | 301,405 | 283,369 |
| Generation / scoring time | 22.51 / 299.51 s | 46.46 / 606.71 s |
| Truncated share | 6.05% | 3.52% |
| Screen peak torch / total device used | 18.48 / 19.49 GiB | 40.98 / 42.19 GiB |

The 7B configuration supplied substantially more reward contrast on this fixed screen. Different checkpoints
and GPUs were used; this does not isolate parameter count or establish a general scaling rule. Scoring dominated
both screens. The 7B step times below also show scoring, rather than the policy update, as the main cost.

The unfiltered 7B held-out baseline was 18.75% over 48 prompts x four samples. Four updates completed:

| Step | Mixed groups kept / eight | Train passes / 64 | Total step / scoring / update time | Sampled stored entries changed |
|---|---:|---:|---|---:|
| 1 | 5 | 12 | 99.42 / 70.91 / 10.83 s | 99.9721% |
| 2 | 7 | 15 | 125.93 / 92.69 / 14.18 s | 99.8954% |
| 3 | 7 | 19 | 134.72 / 100.92 / 14.31 s | 99.8326% |
| 4 | 8 | 13 | 120.13 / 84.80 / 15.82 s | 99.7877% |

The storage check samples up to 512 fixed entries per trainable tensor; it is not an exhaustive weight check.
Sampling-policy sync passed its perturbation/restore probe. Peak torch memory reached 57.93 GiB and total device
use 59.76 GiB. The training clock includes screening and baseline evaluation; the 1,300-second cap stopped the
loop before step 5, after 1,382.1 seconds at the end of step 4. Final evaluation began, then the outer 1,800-second
cap killed the subprocess. No final summary or trainable checkpoint was saved. The four-step state cannot be resumed.

Train-pass fluctuations above are from selected train prompts and cannot establish held-out improvement.
No full-run cost projection or Hopper/Blackwell throughput claim is supported by this pilot.

## Execution and cost

The executed driver, staging script, configurations and ledger are in `../rl-loop/pilots/wp5_20261115/`.
Its README gives the historical command and external input requirements. These are preserved execution pieces,
not a request to launch another job or reset its budget. Final useful output:

```text
fitA2: returncode=0; NO_GO_MIXED_BAND; 7 mixed groups < 12
p7b: returncode="killed: max_seconds reached"; function_seconds=1800.8
p7b: 4 metric rows, 4 optimizer updates; summary.json absent
```

7B function estimate: $1.5664; conservative client-wall estimate: $1.5781 for 1,814.3 seconds. All new task
attempts total **$1.9775 estimated**, including weight staging, CPU probes and failed starts. These are ledger
estimates, not a billing-dashboard reading. The task ceiling was $2.90, with a $2.55 scheduling guard. All observed
pilot apps are stopped; the final 7B app was `ap-bmnvyGG1A3ox3j79kWxCIT`, stopped 02:11:47 IST on 15 Nov.

Earlier failures are retained in the ledger: a remote module-path import failure, then a missing verifier upload
before any rewards or updates. The image was repaired and CPU task construction was verified before the successful
screen. The local runner's private-answer boundary was also fixed and probed before GPU rewards were trusted.
See the trainer report for exact isolation evidence and its limits.

The final CPU ratio-overflow guard and asserting probe CLI were added after the GPU deployment. They were tested
on CPU/Docker; the GPU pilot ran the earlier finite-log-probability guard. No actual pilot overflow was observed,
and no extra GPU rerun is claimed for these final guard changes.

## Remaining gates

- Finish a complete before/after held-out evaluation and uncertainty estimate under a separately authorized,
  reconciled run budget. This pilot has no learning verdict and no saved state to resume.
- The original 100-step acceptance criterion, DT-then-RL arm and capstone-model transfer remain untested.
- Team 5 checkpoint/tokenizer integration tests still require the actual inputs; CPU toy checks do not close them.
- Python 2 human-reference handling remains a lead decision, as recorded in the RL v1 closure report.

`wp5_code_rl_pilot.json` contains the aggregate screens, four metric rows, data hashes and explicit missing results.
No task statements, expected answers, generated programs or held-out IDs are published.
