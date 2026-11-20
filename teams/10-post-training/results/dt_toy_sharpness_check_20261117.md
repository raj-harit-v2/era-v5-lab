# Toy DT sweep: did the mask move? (sharpness check, 17 Nov 2026)

Scope: the pure-Python toy `sft/dt_vs_fft.py --sweep` (section 4 of `dt_vs_fft.md`) only. Nothing here covers `dt/mask.py` or the real-model runs (sections 1 and 2). Draft, offered to the owners of tasks 9 and 10 as a reference.

## Question
Do the DT rows of the toy sweep reflect a mask that moved during training, or only the deletion the Wanda prior made at init?

## Finding
At sharpness 1e3 to 1e4 (the old constants) the mask did not move in 26 of 27 cells (3 seeds x 9 DT cells). Task numbers there equal the lr-0 control, so the old DT rows (task gain +0.000000 in all 9 cells) are prior-only numbers. At 100 to 1000 (`--sharpness_start 100 --sharpness_end 1000` in the paper repository's `scripts/train_sft.sh`, the new constants) the mask moved in 14 of 27 cells (27 bits flipped).

## Why
Logits start near +-0.03 (N(+-0.03, 0.01)). At alpha 1e3 the product alpha * G is 30 or more, so the mean sigmoid slope at step 0 is 1e-10 to 3e-8 in seed 0 (set by the logit nearest zero; up to 7e-3 in seed 1 cells that have a logit near zero) and 4e-11 or smaller at the last step; seed 0 max |delta G| is 1e-10 to 5e-8. At alpha 100, alpha * G is about 3 and 88 to 100% of logits sit inside |alpha * G| < log(99) at step 0 (live zone), then the rising sharpness freezes them.

## Arms (same seeds, 30 steps, lr 0.2, data and code; only sharpness differs)
| Arm | Seed | Cells with flips (of 9) | Bits flipped | Cells where the task loss moved |
|---|---|---:|---:|---:|
| 1e3 to 1e4 (old) | 0 | 0 | 0 | 0 |
| 1e3 to 1e4 (old) | 1 | 1 (MLP gate, p 0.8) | 1 | 1 |
| 1e3 to 1e4 (old) | 2 | 0 | 0 | 0 |
| 100 to 1000 (new) | 0 | 3 (MLP gate x3) | 5 | 3 |
| 100 to 1000 (new) | 1 | 5 | 9 | 5 |
| 100 to 1000 (new) | 2 | 6 | 13 | 6 |
Control (lr 0, no training), both sharpness settings, 3 seeds: 0 flips; every DT cell's task loss equals its step-0 value. The one old-arm flip (seed 1) came from a logit whose Wanda draw landed near zero (|G| about 6.6e-3, inside the live zone); it moved 6e-2 and changed that cell's task loss (0.056105 to 0.047736).
Seed 0, new constants: MLP gate cells move (deleted share 0.1875 to 0.3125, 0.5 to 0.625, 0.8125 to 0.75; task loss 0.0133 to 0.0077, 0.0175 to 0.0114, 0.0146 to 0.0110); all-MLP and attention cells flip nothing, so they are still prior-only.
In the new arm the deleted-share-at-end can go down as well as up (a prior-deleted weight can be restored).

## Reproduce
`python3 -I teams/10-post-training/results/dt_toy_sharpness_check_20261117/probe.py --seeds 0 1 2` (new constants); add `--sharpness 1000 10000` for the old ones, `--lr 0` for the control. About 65 s per command on a laptop CPU. The probe adds read-only measurement to a copy of `dt_vs_fft.py` in memory and changes no product code. Output columns: flips, deleted share init to end, max |delta G|, sigmoid slope first and last step, share inside the live zone, task loss start and end.

## Not tested
AdamW (the reference optimiser; it rescales tiny gradients and could move bits at 1e3 where plain SGD does not), other learning rates, step counts and matrix sizes, a held-out split (task loss is on the toy's own training set), more than 3 seeds (one seed is one seed).

## Does not transfer
4x4 matrices, 32 samples, plain SGD on the logits, 30 steps, no tokens. Says nothing about `dt/mask.py` (which already uses 100 to 1000), the 135M or 1.7B runs, or the capstone MoE.

Update, 19 Nov: the lead's commit 537e4167 changed the `rl-loop/train.py` alpha fallback from 1000 -> 10000 to 100 -> 1000. This check covers the toy only and is unaffected; it does not say whether the earlier RL pilots at 1e3 -> 1e4 had a saturated mask.
