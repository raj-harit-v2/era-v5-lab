# G7 week 3 rotation: dry run 1 restore drill (shishir13)

Work order tasks R1 (watch dry run 1 for one shift) and R2 (log each failure and each restart). Dry run 1 ran as one
process on Team 5's trainer, without the Team 07 supervisor, so `job.log`, `rank<r>.log` and `events.jsonl` do not exist
for it. As agreed with Pradeep (17 Nov), R1 and R2 cover the restore drill on dry run 1 (jobs A and B, plan in
[restore_dryrun1.md](restore_dryrun1.md)). Every number below is from `restore_dryrun1.md` section 5 (TSAI's result
note of 17 Nov, added by #573) or is marked as derived. I did not have the job outputs: they are not in the repository.

## The run being restored

| Item | Value | Source |
|---|---|---|
| Dry run 1 | `train_week2.py`, `exp2_muon.yaml` at T2 size, seed 1234, tokenizer p1536 | #475 |
| Steps / status | 1,221 of 1,221, COMPLETED, no NaN or inf in the loss record | #475 |
| Checkpoint | one `checkpoint.pt` (about 2.2 GB) at the last step, kept by TSAI | `restore_dryrun1.md` section 1 |
| Restarts in dry run 1 | 0 (one process, no supervisor, no `Checkpointer`) | `restore_dryrun1.md` section 1 |

## R1: what happened in jobs A and B

Both jobs ran on 17 Nov on one GPU, with the same setup as #475. Checks C1 to C6 are defined in `restore_dryrun1.md`
section 3.

| Check | Job A (restore the final checkpoint) | Job B (stop at 610, restore, continue) |
|---|---|---|
| C1 loads, exit 0, no identity error | PASS | PASS (run 2) |
| C2 steps and status | 1,221 / COMPLETED | run 1: 610 / INCOMPLETE_NOT_A_RESULT; run 2: 1,221 / COMPLETED |
| C3 `final_model_sha256` equals dry run 1's | PASS | PASS (run 2) |
| C4 `losses.txt` equals dry run 1's | PASS, 1,221 of 1,221 lines, bit-equal | PASS, 1,221 of 1,221 lines, bit-equal (run 2) |
| C5 every step present once | n/a | PASS, steps 1 to 1,221 |
| C6 stop run equals dry run 1 up to step 610 | n/a | PASS, lines 1 to 610 identical |
| Largest loss difference | 0 | 0 |

What it shows: the checkpoint loads and gives back the same model. A run stopped at step 610 and resumed finishes with
the same loss at all 1,221 steps and the same final model as the run that was never stopped. C6 passing means two runs of
the same command already agree on this GPU before any restore, so a bit-equal result is not luck.

What it does not show: both jobs used `train_week2.py`'s own `checkpoint.pt` after a clean stop, not a kill. The
restart-after-kill evidence is `restart_cpu.txt` and `restart_node.txt`.

## R2: failures and restarts

| # | Job | Event | Exit / status | Restored from | Steps lost | Time |
|---|---|---|---|---|---|---|
| 1 | A | Restore dry run 1's final checkpoint (step 1,221) into a fresh folder; no training step runs | exit 0, COMPLETED | final `checkpoint.pt` | 0 | about 6 min 8 s (load and write-out) |
| 2 | B run 1 | Planned stop at step 610 (`--stop-after 610`) | INCOMPLETE_NOT_A_RESULT, 610 steps | not a restore | 0 | not in the result note |
| 3 | B run 2 | Resume from the step-610 checkpoint, train steps 611 to 1,221, save | exit 0, COMPLETED | step-610 `checkpoint.pt` | 0 | about 30 min 39 s |

- Failures: **0** unplanned. Restarts: **2** (job A, job B run 2), both planned. Lost steps: **0**.
- Row 2 is a planned stop, not a failure. INCOMPLETE_NOT_A_RESULT is the status the trainer gives a stopped run, so
  it is never read as a finished result.
- Derived, not measured: job B run 2 minus job A is about 24 min 31 s for the 611 training steps (plus a longer
  save), so about 2.4 s per step at most. Use it only as a rough guide.

## Risks for the week 5 main run

1. `train_week2.py` writes `checkpoint.pt` once, at the end, straight to its final name with `torch.save`. There is no
   COMPLETE marker and no write-then-rename, so a kill during that save leaves a broken file under the real name.
   TSAI agrees the main run should save through the Team 07 `Checkpointer` and run under the supervisor.
2. Metrics are written every 10 steps (Team 08, #512). After a kill and restore, the rows between the last flush and a
   newer checkpoint are never written again. Flushing `metrics.jsonl` at each checkpoint save fixes it.

## Not available

The full-run per-step logs (`losses.txt`, `metrics.jsonl`) of dry run 1 were not on main when this was written
(`losses.txt` on #475 is the 3-step smoke run). If they land, check: step numbers run 1 to 1,221 with no gap or repeat,
`train/ce_loss` finite on every row, and `summary.json` says COMPLETED with 1,221 steps.
