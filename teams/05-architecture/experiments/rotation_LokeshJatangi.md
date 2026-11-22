# Rotation: exp3-shared-0 at seed 1241

Lokesh Arundathi (Team 10). Week 3 rotation into Team 05.

**Assignment.** Run the T2 arm `exp3-shared-0` (`configs/arms/exp3_shared_0.yaml`, shared expert off: 16 routed + 0 shared in place of 16 + 1) again at a new seed, 1241. Report its bits per byte next to the seeds already run. Job request: `jobs/2026-11-18-rotation-shared0-seed1241.md` (PR #TODO). One new seed names no winner and does not change config v1. The T2 reference is not run again.

## R1: the run

TODO: fill from the TSAI result comment on PR #TODO.

| Held-out bits per byte at step 1,221 | exp3-shared-0, seed 1241 |
|---|---|
| val/bpb (whole held-out file) | TODO |
| English | TODO |
| Code | TODO |
| Indic (mean of slices) | TODO |

Lower is better.

## R2: does it hold?

| | Seed 1234 | Seed 1235 | Seed 1236 | Seed 1237 | Mean | Range | SD |
|---|---|---|---|---|---|---|---|
| T2 reference, val/bpb | 1.7673 | 1.7796 | 1.7792 | 1.7542 | 1.7701 | 0.0254 | 0.0120 |
| exp3-shared-0 seed 1241 minus that seed | TODO | TODO | TODO | TODO | TODO | | |

exp3-shared-0 earlier seeds (TSAI T2 table, 13 Nov): 2 seeds, mean 1.7659 (-0.008 vs the then 3-seed reference mean 1.7754). Per-seed values: TODO (asked TSAI).

Reading rule: if seed 1241 sits inside the reference range (1.7542 to 1.7796) and its gap to the reference mean is smaller than the reference SD, the result "holds" only in the sense that shared-expert-off is not worse; it is not shown to be better.

- TODO verdict.

## Limits

- One new seed; the seed also changes training data order.
- Old tokenizer v0, like the week 2 EXP-3 runs. Trainer on main with the #521 speed fixes (the earlier seeds ran at 71bc0fb with the same fixes applied by TSAI). Not comparable with week 3 p1536 numbers (dry run 1: 1.5159).
- No winner is named and config v1 is unchanged.

## Evidence

- Job request and CPU smoke log: `jobs/2026-11-18-rotation-shared0-seed1241.md`, `jobs/evidence/2026-11-18-rotation-shared0-seed1241/`.
- Result: TSAI comment on PR #TODO.
