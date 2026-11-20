# Rotation: attn-2 (window 128 with a sink) at seed 1237

Ravi Naik (Team 10), week 3 rotation into Team 05.

**Assignment.** Run the T2 arm `attn2_swa128_sink` (`configs/arms/attn2_swa128_sink.yaml`, attn-2) again at a new seed, 1237, next to the T2 reference (`t2.yaml`, attn-0) at the same seed, and say whether the not-worse rule still holds. The job request is pull request 450 (`jobs/2026-11-14-rotation-attn2-seed1237.md`), approved by the lead and TSAI and merged. TSAI ran both jobs. As Team 05 set out, one new seed names no winner and does not change config v1.

## R1: the run

TSAI result comment on pull request 450, 15 Nov 2026: both runs finished all 1,221 steps on heldout_v1, seed 1237, trainer `71bc0fb` with the TSAI speed fixes.

| Held-out val/bpb at step 1,221 | Seed 1237 |
|---|---|
| attn-2 (`attn2_swa128_sink`) | **1.7507** |
| T2 reference (attn-0) | 1.7542 |
| attn-2 minus reference | **-0.0035** |

Lower is better. The run files (`metrics.jsonl`, `summary.json`, `manifest.json`) were not returned to the repo. Every result number in this file comes from the TSAI comments on pull requests 450 and 462. The only other numbers are the p1536 values named in the Limits.

## R2: does it hold?

**What can be said.** The same TSAI comments give the T2 reference at four seeds:

| | Seed 1234 | Seed 1235 | Seed 1236 | Seed 1237 | Mean | Range (high - low) | SD |
|---|---|---|---|---|---|---|---|
| T2 reference, val/bpb | 1.7673 | 1.7796 | 1.7792 | 1.7542 | 1.7701 | 0.0254 | 0.0120 |
| attn-2 seed 1237 minus that seed | -0.0166 | -0.0289 | -0.0285 | -0.0035 | | | |

The SD is the sample standard deviation of the four reference seeds.

- **attn-2 at seed 1237 is not worse than the reference on the whole-file score.** It is 0.0035 below the reference at the same seed. It is also below the reference at each of the other three seeds (0.0166 to 0.0289), but those comparisons cross seeds, so they show less.
- **The gap is smaller than the noise between seeds.** The reference seeds alone range over 0.0254 (SD 0.0120), and the gap at seed 1237 is 0.0035. One seed of attn-2 cannot say that the arm is better than the reference. It also shows no sign of being worse.
- **No winner is named.** This matches TSAI's own wording on pull request 450, and config v1 is unchanged.

**What cannot be said: the rule as defined was not applied.** The not-worse rule (`docs/attention_candidates.md`, "Pass rule") needs three metrics: the three-group mean, the code mean and the Indic mean. For each, attn-2 minus attn-0 must not exceed the larger seed spread of the two arms, and all three must pass. TSAI has posted only the whole-file val/bpb for the seed 1237 runs and for the reference seeds. The three group values were asked for on pull request 450 (15 and 18 Nov) and are not available. So:

| Metric | attn-2 seed 1237 | Reference seed 1237 | Difference | Result |
|---|---|---|---|---|
| Three-group mean | not available | not available | | **not determined** |
| Code mean | not available | not available | | **not determined** |
| Indic mean | not available | not available | | **not determined** |
| Whole file (stand-in only, not part of the rule) | 1.7507 | 1.7542 | -0.0035 | no sign of being worse |

The whole-file score is a mean over all text. A rise in code or Indic could be hidden by a fall in English or math, so it cannot replace the three metrics. **Verdict for the rule: not determined.** The aggregate gives no reason to expect a failure, and that is all this file claims.

## Limits

- **Three metrics missing.** See above. When TSAI shares the three values (or the two `summary.json` files) for the seed 1237 runs, this file will be updated in a follow-up pull request with the rule applied on seed 1237 alone and, if the arm's other seeds are given, on four seeds.
- **No per-seed values for attn-2 at seeds 1234 to 1236.** TSAI has not posted them in the pull request threads. The job request quotes an attn-2 mean of 1.7627 over those seeds from the T2 table posted in G5. That table is not in the repository, so it is not used here, and the arm's own seed spread is unknown. The rule's allowance is the larger spread of the two arms, so it is at least the reference's 0.0254 when measured on the whole-file score.
- **A new seed changes more than the data order.** In `train_week2.py` the seed sets the Python, NumPy and torch generators and the `BatchStream` generator, so seed 1237 differs from seeds 1234 to 1236 in initial weights and in the order of training windows. That is the expected effect of a new seed. The held-out set is the same.
- **Old tokenizer.** These runs used tokenizer v0 (job request) and trainer `71bc0fb` (TSAI comment). The week 3 p1536 numbers (dry run 1, pull request 475: 1.5159; pull request 474: 1.5381) use a different tokenizer and must not be compared with them.
- **The reference range rests on two seeds.** Its 0.0254 is the distance between seed 1237 (1.7542, lowest) and seed 1235 (1.7796, highest); the other two seeds lie between them.

## Evidence

- Job request and CPU smoke log: `jobs/2026-11-14-rotation-attn2-seed1237.md` and `jobs/evidence/2026-11-14-rotation-smoke/smoke.log` (pull request 450).
- Result: the TSAI comment on pull request 450, 15 Nov 2026, and the TSAI comment on pull request 462, 15 Nov 2026 (reference at seed 1234 to 1237).
- The mean, range, SD and differences above are plain arithmetic on those numbers.
