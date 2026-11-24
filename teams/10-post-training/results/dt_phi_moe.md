# Deletion Tuning on a 7.65B MoE: Phi-mini-MoE-instruct, SFT on GSM8K (22 Nov 2026)

**Evidence level: independent study on a public model, one seed, small evaluation.** This is the "try Deletion Tuning on a
large model" item from the class discussion. It does not use the capstone model, the lab data, or any lab checkpoint, and
it is not Gate 4 evidence for the capstone. The Gate 4 comparison on the dry run 2 checkpoint stays with
`capstone/dryrun2_dt_compare.py` and `results/dt_vs_fft.md`. LoRA and full fine-tuning on this same model are not run yet
(see "Not shown").

## What was done

| Item | Value |
|---|---|
| Model | Phi-mini-MoE-instruct (MIT licence), 7.65B parameters, 32 layers x 16 experts, bf16 (15.3 GB), split in two blocks of layers over two GPUs |
| Method | the **official** Deletion Tuning code (commit `94f0340`, vendored unmodified, hashes re-checked at every run), paper values: 400 steps, batch 4, lr 5e-4, sharpness 100 -> 1000, weight_reg 1e-5 decaying to 0, init sparsity 1/2048, Wanda prior, seed 0 |
| Targets | the 512 expert gate projections (`w1`), 2,013,265,920 weights, one mask logit each |
| Data | 2,048 GSM8K training questions in the official `{question}\n{answer}` SFT format, loss on the answer only |
| Hardware | 2 x NVIDIA RTX 6000 Ada (47 and 48 GiB) |
| Code | `RaviNaik/ERA`, folder `v5/capstone/dt_phi_moe/`, commit `8bef04a`. Our files only wrap the official ones for two GPUs and for this model's remote code; the README lists every difference from the official scripts |

One server fault matters for reproduction: a direct GPU-to-GPU copy of a large tensor returns garbage on this machine
(`p2p1.txt`, `p2p2.txt`: 200 of 200 whole-tensor copies wrong at 1 Mi elements and above). Gates and labels moved between the two cards
arrived as zeros or random numbers. Every cross-GPU copy therefore goes through the CPU (`devcopy.py`). The training was
run twice, before and after this fix, and deleted the same number of weights (12,296,351). The evaluation below is of the
second run (`..._v4`), made after the fix.

## Training result

| | |
|---|---|
| Deleted at step 0 (Wanda prior) | 0.1837% (3,698,655 weights) |
| Deleted at step 400 | **0.6108%** (12,296,351 of 2,013,265,920) |
| Saved mask | 23.2 MB (official packbits + zstd) |
| Time | 7,035 s training (12.8 s per step), 7,135 s with loading and calibration |
| Peak GPU memory | 35.2 GiB (card 0), 31.0 GiB (card 1) |

## Evaluation result

200 GSM8K test questions (greedy, 256 new tokens), the six prior-task benchmarks with lm-evaluation-harness (zero-shot,
chat template, bf16, **50 items per task**, 50 per subject for MMLU), forward KL on 50 of the base model's own replies.
"Training format" is the question followed by a newline (what the SFT optimises); "chat template" is how the instruct
model is used, with the instruction to end with `#### <number>`.

| | base | Deletion Tuning | change |
|---|---:|---:|---:|
| GSM8K, chat template | 58.5% (117/200) | 71.5% (143/200) | **+13.0** |
| GSM8K, training format | 33.5% (67/200) | 78.5% (157/200) | +45.0 |
| replies that contain `####`, training format | 23.5% | 99.5% | +76.0 |
| hellaswag | 70.00 | 70.00 | 0.00 |
| truthfulqa_mc2 | 56.96 | 56.26 | -0.70 |
| mmlu | 69.54 | 69.75 | +0.21 |
| ifeval | 67.11 | 63.16 | -3.95 |
| winogrande | 78.00 | 80.00 | +2.00 |
| humaneval_instruct | 14.00 | 12.00 | -2.00 |
| **mean of the six prior tasks** | **59.27** | **58.53** | **-0.74** |
| Team 10 `indic_v1` exact (44 rows) | 52.27 | 52.27 | 0.00 |
| Team 10 `safety_v1` exact (41 rows) | 56.10 | 56.10 | 0.00 |
| forward KL per token (GSM8K replies) | 0 | 0.1412 | |

## How to read it

- **The chat-template gain is the one to quote.** With 200 questions the standard error of one accuracy is about 3
  points, so +13 is about 2.8 standard errors of the difference (unpaired, so conservative).
- **The training-format +45 is mostly format.** The base model puts `####` in 23.5% of its replies, the tuned model in
  99.5%. The scorer falls back to the last number in a reply that has no `####`, so a reply in another format is scored
  on whatever number comes last. This column mixes learning the format with solving the problem.
- **No forgetting was detected, which is not the same as none.** At 50 items one item is 2 points: the humaneval -2 is
  one problem, the winogrande +2 one item, and the ifeval -3.95 about three prompts. All six changes are inside that
  noise, and so is the mean of -0.74.
- **The Team 10 sets did not move in total** (52.27 and 56.10 both before and after). Inside the safety set the
  refusal rate went from 57.1% to 52.4%, on a handful of rows. Non-English safety rows are at 0.0 for both models, so
  that is a property of the base model, not of Deletion Tuning.
- **0.61% of the gate weights is a small deletion** that was enough to change the output format and add 13 points. It is
  not shown that the deletion, rather than any 400-step update of these weights, is what helps. That needs the LoRA and
  full fine-tuning arms on the same data.

## Not shown

- One seed, one training run per setting. No variance across seeds.
- 200 GSM8K questions and 50 items per prior task. ifeval and humaneval generate for hours, so they were kept small.
- No LoRA or full fine-tuning arm on this model, so nothing here says Deletion Tuning is better or worse than they are.
  The code for both (same data, steps and batch size) and for a paired test on the saved replies is written and tested on
  a tiny model on CPU; it has not run on the real model.
- Not the capstone architecture (no KE2, no untied KAS head, no Muon) and a public model, so no claim about dry run 2.
- The lm-evaluation-harness benchmarks here are public benchmarks on a public model. No lab model or lab checkpoint was
  scored, and nothing from this run goes to Team 9's watcher or to `forgetting.py`.

## Exact commands and output (TSAI run rule)

Training (`train_v4.out`, 22 Nov, 7,135 s):

```
RUN_NAME=dt_phi_mini_sft_gsm8k_seed0_v4 nohup bash run.sh train > train_v4.out 2>&1 &
...
[gsm8k] iter 400/400 | loss=0.6039
done: 12,296,351 of 2,013,265,920 gate weights deleted (0.6108%), mask 23.2 MB, 7035 s
[train] finished in 7135 s
```

Evaluation (`eval_v4.out`, base 18,956 s, Deletion Tuning 21,007 s, report 0 s):

```
RUN_NAME=dt_phi_mini_sft_gsm8k_seed0_v4 GSM8K_LIMIT=200 PRIOR_LIMIT=50 KL_LIMIT=50 MAX_NEW_TOKENS=256 \
  nohup bash run.sh base_eval dt_eval report > eval_v4.out 2>&1 &
...
prior tasks: {'hellaswag': 0.7, 'truthfulqa_mc2': 0.5626, 'mmlu': 0.6975, 'ifeval': 0.6316, 'winogrande': 0.8, 'humaneval_instruct': 0.12} mean 0.5853
[dt_eval] finished in 21007 s
```

Both logs, with the server paths replaced, are in `RaviNaik/ERA` at `v5/capstone/dt_phi_moe/` (`train_v4.out`,
`eval_v4.out`, `README.md`).

## Next

1. Paired test on the saved replies (McNemar and a bootstrap interval), then a larger run of the same comparison: all
   1,319 GSM8K questions in the chat template and the four log-likelihood prior tasks at 200 items.
2. LoRA (same 512 gate projections) and full fine-tuning on the same data, steps and batch size, evaluated the same way.
   Their learning rates are common defaults, not tuned, and this file will say so.
3. This file is then updated in place with those rows.
