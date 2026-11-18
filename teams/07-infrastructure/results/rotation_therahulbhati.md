# G7 week 3 rotation: dry run 1 watch (therahulbhati)

Work order tasks R1 (watch dry run 1 for one shift from the returned logs) and R2 (log each failure and each
restart). R2 is filled from the run result TSAI posted on #475. R1 waits for the real run logs: the evidence
folder on main holds only the smoke run (see "Logs in the repo" below).

## The run

| Item | Value | Source |
|---|---|---|
| Job request | `teams/05-architecture/jobs/2026-11-15-dryrun1.md` | #475, merged 16 Nov |
| Run ID / output | `dryrun1-1234`, `./out/dryrun1-1234/` | job request, command line |
| Trainer | `teams/05-architecture/harness/train_week2.py` (71bc0fb + Gate 2 speed fixes + #474 patch) | job request |
| Arm and size | exp2_muon at T2: 8 layers, width 512, 16 routed + 1 shared experts, top-2, context 2,048, batch 8 | job request |
| Optimizer | Muon, muon_lr 0.01; lr 0.001 for the other parameters | job request |
| Seed | 1234 | job request |
| Tokenizer | p1536, sha256 `e6b93a93...a64b` | TSAI result on #475 |
| Hardware | 1 GPU, single process, bf16 | job request; TSAI note in the team group |
| Steps | 1,221 of 1,221 | TSAI result on #475 |
| Status | COMPLETED | TSAI result on #475 |
| Final train cross-entropy | 4.8906 | TSAI result on #475 |
| Final gradient norm | 0.7037 | TSAI result on #475 |
| NaN / inf in loss record | none | TSAI result on #475 |
| Held-out val/bpb | 1.5159 (English 1.9844, code 1.8901, Indic mean 1.3289, three-group 1.7345) | TSAI result on #475 |
| Same arm, tokenizer v0, seed 1234 | 1.6443 (delta -0.1284) | TSAI result on #475 |
| Checkpoints | one `checkpoint.pt` at the last step (about 2.2 GB), kept by TSAI | TSAI result on #475 |

Note: the job request names the frozen C3 tokenizer (sha256 `15468e66...`). TSAI ran it with p1536
(sha256 `e6b93a93...`). Anyone comparing this run to the request should use the p1536 hash.

## R2: failures and restarts

| # | Time / step | Event | Cause | Action | Restored from | Steps lost |
|---|---|---|---|---|---|---|
| none | | | | | | |

- Failures: **0**. Restarts: **0**. The run reached 1,221 of 1,221 steps with status COMPLETED and no NaN or inf.
- No lost steps: completed steps equal planned steps.
- Dry run 1 did not run under `ckpt/supervisor.py` and did not use the G7 Checkpointer. It wrote no interval
  checkpoints, no `latest.json` and no `commits.jsonl`. So it gives **no evidence** for the Gate 3 rule
  "only COMPLETE checkpoint restarts". That evidence is still `results/restart_cpu.txt` and
  `results/restart_node.txt`, and the restore drill (core task 5, #491).
- `INTERVAL_S=600` from `docs/checkpoint_interval.md` (#463) was not in effect for this run, because the
  trainer only saves at the end.

To confirm when the real logs land: step numbers in `metrics.jsonl` run 1 to 1,221 with no gap or repeat, and
`summary.json` says COMPLETED with 1,221 steps.

## R1: shift watch

Shift: **not yet assigned**. Proposed split by step range across the rotation members, so each range is read once.

Status: **waiting for logs.** Checks for the shift, from `metrics.jsonl` and `losses.txt`:

| Check | How | Result |
|---|---|---|
| Step continuity | `step` increases by 1 across the shift, no gaps or repeats | pending |
| Finite loss | `train/ce_loss` and `loss` finite on every row | pending |
| Loss spikes | step-to-step jumps in `train/ce_loss`; list any step above the running trend | pending |
| Gradient norm | `gradient_norm`, and how often `gradient_clipping_applied` is true (clip 1.0) | pending |
| Throughput | `perf/step_ms` and `tokens_per_second`: slow steps and drops | pending |
| Held-out evals in the shift | `val/bpb` at each eval step | pending |
| Alarms (offline) | Team 8 `alarms.py --jsonl` on the shift's rows (#494); alarms were not hooked into the live run | pending |

## Logs in the repo

`teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/` on main (checked 16 Nov) is the smoke run, not dry
run 1: `summary.json` has `"status": "SMOKE"`, `"steps": 3`; `metrics.jsonl` has 4 rows. The real
`metrics.jsonl`, `losses.txt` and `summary.json` have been requested from TSAI in the team group. R1 is filled
in when they arrive.
