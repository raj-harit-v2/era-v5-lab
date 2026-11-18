# Rotation: exp3-experts-8 at seed 1242

Pradeep Kumar G S (Team 07). Week 3 rotation into Team 05.

**Assignment.** Run the T2 arm `exp3-experts-8` (`configs/arms/exp3_experts_8.yaml`, 8 routed experts in place of 16) again at a new seed, 1242. Report its bits per byte next to the seeds already run. The job request is pull request 462 (`jobs/2026-11-14-rotation-experts8-seed1242.md`), approved by the lead and TSAI and merged on 16 Nov 2026. TSAI ran it. As Team 05 set out, one new seed names no winner and does not change config v1. The T2 reference was not run again.

## R1: the run

TSAI result comment on pull request 462, 15 Nov 2026: the run finished all 1,221 steps on heldout_v1, seed 1242, trainer `71bc0fb` with the TSAI speed fixes.

| Held-out bits per byte at step 1,221 | exp3-experts-8, seed 1242 |
|---|---|
| val/bpb (whole held-out file) | **1.7631** |
| English | 2.0894 |
| Code | 2.1039 |
| Indic (mean of slices) | 1.6068 |

Lower is better. The run files (`metrics.jsonl`, `summary.json`, `manifest.json`) were not returned to the repo. Every number in this file comes from the TSAI comment.

## R2: does it hold?

The same TSAI comment gives the T2 reference (16 routed experts) at four seeds:

| | Seed 1234 | Seed 1235 | Seed 1236 | Seed 1237 | Mean | Range (high − low) | SD |
|---|---|---|---|---|---|---|---|
| T2 reference, val/bpb | 1.7673 | 1.7796 | 1.7792 | 1.7542 | 1.7701 | 0.0254 | 0.0120 |
| exp3-experts-8 seed 1242 minus that seed | −0.0042 | −0.0165 | −0.0161 | +0.0089 | −0.0070 | | |

The SD is the sample standard deviation of the four reference seeds.

- **Seed 1242 is inside the reference's own seed range.** 1.7631 lies between 1.7542 and 1.7796. Among the five numbers it is second lowest. Only reference seed 1237 is lower.
- **The gap is smaller than the noise between seeds.** 8 experts at seed 1242 sit 0.0070 below the reference mean. The reference seeds alone range over 0.0254 and have an SD of 0.0120. Against single reference seeds, the difference runs from −0.0165 to +0.0089, so it changes sign depending on which seed is picked. One seed of the arm cannot separate 8 routed experts from 16.
- **So the direction is not settled.** 8 experts are not worse than the reference on this seed. They are not shown to be better either.
- **An earlier number, corrected.** The job request expected "T2 reference mean 1.7754, seed spread about 0.007". That was the mean and the SD of seeds 1234 to 1236 only. With seed 1237 added, the mean is 1.7701 and the SD 0.0120. Measured on three seeds, the 1242 gap was −0.0123. On four it is −0.0070. Adding one reference seed moved the reference mean by more than half the gap, which is another sign the gap is within the noise.

## Limits

- **No seeds of the arm itself.** The comparison the job request asked for, with exp3-experts-8 at seeds 1234 to 1236, is not possible yet. TSAI has not posted those numbers (asked on pull request 462, 15 Nov). Until they come, the only spread is the reference's, and every comparison above crosses seeds and arms.
- **Groups.** TSAI gave English, code and Indic for seed 1242 only, not for the reference seeds, so there is no per-group comparison. Seed 1242 scores 2.1039 on code, above its English 2.0894. That holds for this one run only.
- **Same seed, different data order.** The seed also drives the training batch sampler, so seed 1242 trained on a different order of windows from the reference seeds. That is the expected effect of a new seed. The held-out set is the same.
- **Old tokenizer.** This run used trainer `71bc0fb` and tokenizer v0, like the week 2 EXP-3 runs. The week 3 p1536 numbers (dry run 1, pull request 475: 1.5159; pull request 474: 1.5381) use a different tokenizer and must not be compared with it.
- No winner is named and config v1 is unchanged.

## Evidence

- Job request and CPU smoke log: `jobs/2026-11-14-rotation-experts8-seed1242.md` and `jobs/evidence/2026-11-14-rotation-experts8-seed1242-smoke.txt` (pull request 462).
- Result: the TSAI comment on pull request 462, 15 Nov 2026.
- The mean, range, SD and differences above are plain arithmetic on the five numbers in that comment.
