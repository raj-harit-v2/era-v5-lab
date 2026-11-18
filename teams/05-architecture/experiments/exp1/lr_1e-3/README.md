# exp1-lr-1e-3

Arm owner: Mukund Singh (`mukund-23`). EXP-1, size T1. Plan: `experiments/plan_v1.md`.

## What this arm changes

| Field | Value |
|---|---|
| Config | `configs/arms/exp1/lr_1e-3.yaml` (inherits `configs/arms/t1.yaml`) |
| The one change from T1 | `optim.lr` = 0.001 |
| Optimizer | AdamW, betas (0.9, 0.999), weight decay 0, grad clip 1.0, constant schedule, no warmup |
| Budget | batch 8, context 1,024, 245 steps, 30 min cap |

`t1.yaml` also sets `optim.lr: 0.001`, as a timing placeholder that lets the loader take a step.
This arm sets 0.001 on purpose, as one of the five swept rates. The number is the same; the meaning is not.

## Job

| Field | Value |
|---|---|
| Job | `jobs/2026-11-05-exp1-t1-lr.md`, pull request 310. One job for all five rates, run by TSAI. |
| Command | the job command with `--config teams/05-architecture/configs/arms/exp1/lr_1e-3.yaml --seed <seed> --out ./out/exp1-lr-1e-3-<seed>` |
| Training data | train split of the cleaned tokenizer sample v0-clean, all 38 packs, converted by TSAI |
| Held-out | held-out split of the same sample, converted by TSAI. This is the shared EXP-1 input TSAI named on 5 Nov, not `heldout_v1/` |
| Tokenizer, table | `teams/03-tokenizer/v0`; P32 raw table for tokenizer v0 (as reported by TSAI on #310) |
| Settings | the agreed resolution TSAI published with the job, run with micro batch 8 ("fast resolution", same maths, as reported by TSAI) |
| Eval | the job copy of the fast held-out eval and the token cache, for all three seeds of this arm (as reported by TSAI) |
| Precision | bf16, 1 GPU |
| Pending from TSAI | GPU model, harness commit, train and held-out sha256, wall time per seed |

## Result

Source: the TSAI comment on pull request 310 (7 Nov 2026), "EXP-1 results, all 15 runs complete".
Every run reached 245 steps with status COMPLETED. Values are final `val/bpb`, the whole held-out file
(sum of next-token loss in nats over every held-out token / ln 2 / UTF-8 bytes). Lower is better.

| seed | steps | status | final val/bpb |
|---|---|---|---|
| 1234 | 245 | COMPLETED | 1.9757 |
| 1235 | 245 | COMPLETED | 1.9617 |
| 1236 | 245 | COMPLETED | 1.9684 |

| | value |
|---|---|
| Mean | 1.9686 |
| Seed spread (max − min, plan_v1) | 0.0140 |
| Finished seeds | 3 of 3 |

Seed 1235: the first run timed out at step 150, so it is not a result. TSAI replaced it with a complete run; the table shows that run.

Mean and spread, recomputed from the posted values:

```bash
python -c "v=[1.9757,1.9617,1.9684];print(round(sum(v)/3,4),round(max(v)-min(v),4))"
```

TSAI's table also lists a standard deviation (0.0070). The plan's seed spread is max − min, used above.

### Against the next arm (whole-file val/bpb only)

From the same TSAI comment, the second-lowest mean is 3e-3: 2.1000, 2.0377, 2.0935; mean 2.0771, spread 0.0623.
The gap is 2.0771 − 1.9686 = 0.1085, larger than the larger spread, 0.0623.

This is on whole-file `val/bpb`. The plan's winner number is the three-group mean (English, code, mean of the 11 Indic slices),
with code and the Indic mean as guards (plan_v1, TSAI 2 Nov). Those per-run values are listed under Measures in the job file
but are not posted yet, so this note does not call a winner. The EXP-1 decision is the lead's, in `experiments/results_v1.md`.

### Pending

- Three-group, English, code and Indic-mean bpb per seed, and their mean and spread.
- NaN/inf check over every logged value. COMPLETED means no run stopped; the harness stops on a non-finite loss or gradient,
  but the plan asks for the check on the logs.
- Scored tokens per run, from the log.

When the three metric files per run (`manifest.json`, `summary.json`, `metrics.jsonl`) are available, these come from:

```bash
python teams/05-architecture/experiments/exp1/lr_1e-3/summarize_arm.py <dir>/exp1-lr-1e-3-1234 <dir>/exp1-lr-1e-3-1235 <dir>/exp1-lr-1e-3-1236 \
  --heldout-sha256 <TSAI published held-out sha256> \
  --json teams/05-architecture/experiments/exp1/lr_1e-3/arm_summary.json
```

The script checks each run (`optim.lr` 0.001, GPU bf16, 245 of 245 steps inside 30 min, the published held-out sha256,
`val/bpb` equal to nats / ln 2 / bytes, no NaN or inf) and that the three seeds differ only in `run.seed`.
It prints per-seed three-group, whole-file, English, code and Indic-mean bpb with mean and spread.

## Smoke test before the job (not a result)

CPU fp32 on main `ea7b533` (#190 at `656696c`, #191 at `885a86d`), Tue 3 Nov:
- 61 of 61 week-2 tests pass. `check_week2.py` on this arm: 0 errors, dense untied head.
- Tokenizer v0 `2de039f2…`, raw P32 table content `47d411a9…`.
- Two seed-1234 runs, 20 steps, sequence 128, batch 2: identical `losses.txt` and final model sha `e59a5fcb…`. 0 NaN or inf. First train CE 11.94 (ln 131,072 = 11.78), last 6.43.
- Smoke settings came from `configs/small/smoke_resolution.yaml` (`norm_eps` 1e-6), and the harness was older than the job's. Its bits per byte on a 50-doc held-out slice is not a result.

## Limits

- 245 steps at T1, one constant rate, no warmup. The result compares the five rates at this length only, not for a longer run.
- Each document takes its own 1,024-token slot with padding, so scored training tokens are below the 2.0M input positions. The step count is the budget.
- Whole-file `val/bpb` weights each language by its bytes in the held-out split, so it is not the same number as the three-group mean, which weights English, code and the Indic mean equally.
