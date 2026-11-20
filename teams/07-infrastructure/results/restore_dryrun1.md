# Restore drill on dry run 1

Week 3, core task 5: **do one restore drill in dry run 1: stop, restore, continue. Compare the loss.**

Gate 3 evidence for Team 07: *dry run 1 ends with no lost steps and only COMPLETE checkpoint restarts.*

**Status: done. PASS on every check (C1 to C6; C5 on `losses.txt` only).** TSAI ran both jobs on 17 Nov; the results are in section 5.

## 1. What dry run 1 was

TSAI ran dry run 1 on 16 Nov (#475): Team 05's `train_week2.py`, `exp2_muon.yaml` at T2 size, seed 1234,
tokenizer p1536, 1,221 of 1,221 steps, status COMPLETED, no NaN or inf in the loss record.

- It ran as **one process**, **without** the Team 07 supervisor (`ckpt/supervisor.py`) and **without** the
  `Checkpointer` (`ckpt/ckpt.py`).
- It had **zero restarts**.
- It saved **one checkpoint**, `checkpoint.pt` (about 2.2 GB), at the last step. TSAI keeps it.

So the restore drill cannot be a stop in the middle of dry run 1 itself. It is done on the saved checkpoint, as TSAI
asked in the Team 07 group on 16 Nov.

## 2. The drill: two jobs

`train_week2.py` already has the two options needed: `--stop-after N` (stop after step N and save `checkpoint.pt`)
and `--resume PATH` (load a checkpoint and carry on). On resume it refuses a checkpoint whose identity hash (code,
config, data, device, software) differs from the current run, so a passing resume also proves that nothing changed.

| Job | What it does | Request |
|---|---|---|
| **A. Restore** (required) | Load dry run 1's final checkpoint (step 1,221) into a fresh output folder with the same command. | [2026-11-17-restore-final-ckpt.md](../jobs/2026-11-17-restore-final-ckpt.md) |
| **B. Stop, restore, continue** (optional, if TSAI agrees) | Run the same command to step 610 and stop. Resume from that checkpoint to step 1,221. Compare with dry run 1. | [2026-11-17-stop-resume.md](../jobs/2026-11-17-stop-resume.md) |

**A** proves the saved checkpoint loads and gives back the same model. It does not train any step again, because
training cannot go past the last step without changing the step count, and that fails the identity check.

**B** is the full "stop, restore, continue" of the work order. It costs about one more dry run of compute, so TSAI
decides whether to run it.

## 3. Checks

| # | Check | Job | Pass if | Read from |
|---|---|---|---|---|
| C1 | The checkpoint loads | A, B | Exit code 0, no identity error | job log |
| C2 | Right step | A, B | `summary.json` `steps` = 1,221 and `status` = COMPLETED | `summary.json` |
| C3 | Same model | A, B | `final_model_sha256` equals dry run 1's | `summary.json` vs #475 |
| C4 | Same loss | A, B | `losses.txt` equals dry run 1's, line for line (bit for bit, hex floats) | `losses.txt` vs #475 |
| C5 | No lost steps | B | `losses.txt` has 1,221 lines; `metrics.jsonl` has every step from 0 to 1,221 once | `losses.txt`, `metrics.jsonl` |
| C6 | Stop run matches before the stop | B | Lines 1 to 610 of the stop run's `losses.txt` equal lines 1 to 610 of dry run 1's | stop run `losses.txt` |

**How to read B if C4 fails.** C6 tells the two causes apart. If C6 also fails, two runs of the same command already
differ on the GPU before any restore, so the difference is run-to-run noise, not the restore. If C6 passes and C4
fails, the restore changed something. Either way the largest difference is recorded.

## 4. What this gives Gate 3

| Gate 3 line | Evidence |
|---|---|
| No lost steps | Dry run 1: 1,221 of 1,221 steps, COMPLETED (#475). Its full `metrics.jsonl` ([#620](../../05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl)) has every step from 0 to 1,221 exactly once: 1,222 rows, checked with Team 08's `step_continuity` rule (`teams/08-monitoring/alarms/continuity_rules.py`), 0 alarms; `losses.txt` has 1,221 lines. Job B: after a stop at step 610 and a restore, every one of the 1,221 losses is present and bit-equal to dry run 1 (C4, C5). |
| Only COMPLETE checkpoint restarts | Dry run 1 had no restart, so it shows nothing here. The COMPLETE-only restart evidence stays the Team 07 restart test: [restart_cpu.txt](restart_cpu.txt) and [restart_node.txt](restart_node.txt) (SIGKILL after step 140, restart from the COMPLETE checkpoint at step 125, 200/200 steps bit-equal). |

**Risk for the main run (week 5).** `train_week2.py` writes `checkpoint.pt` once, at the end, straight to its final
name with `torch.save`. It has no COMPLETE marker and no write-then-rename, so a kill during that save leaves a
broken file under the real name. The Team 07 `Checkpointer` exists for this. Before the main run, the trainer should
save through the `Checkpointer` and run under the supervisor.

A related finding from Team 08 (#512): metrics are written to disk every 10 steps, so after a kill and restore the
rows between the last flush and a newer checkpoint are never written again. Flushing `metrics.jsonl` at each
checkpoint save fixes it.

## 5. Results

TSAI ran both jobs on 17 Nov, single GPU, the same setup as #475. The numbers below are from TSAI's result note of
17 Nov, which went to the Team 06 group chat by mistake (TSAI confirmed this in the Team 07 group on 17 Nov), and from
TSAI's answer on C5, given in the Team 07 group on 18 Nov. Neither is on GitHub yet: the request on #573 has no reply.
@theschoolofai, please post the job A and job B results as a comment on #633; this section will link to it once it is
there. The job outputs were not added to the repository. The dry run 1 files they were compared with are on main since #620:
[`2026-11-15-dryrun1-full/`](../../05-architecture/jobs/evidence/2026-11-15-dryrun1-full/) (`summary.json`: COMPLETED, 1,221 steps, `final_model_sha256` `93e5f454…1981`).

| Number | Job A (restore the final checkpoint) | Job B (stop at 610, restore, continue) |
|---|---|---|
| Exit code | 0, no identity error (C1) | run 1 (stop): stopped as expected; run 2 (resume): 0, no identity error (C1) |
| `steps` / `status` | 1,221 / COMPLETED (C2) | run 1: 610 / INCOMPLETE_NOT_A_RESULT; run 2: 1,221 / COMPLETED (C2) |
| `final_model_sha256` equal to dry run 1 (C3) | Yes | Yes (run 2) |
| `losses.txt` equal to dry run 1 (C4) | Yes, 1,221 of 1,221 lines | Yes, 1,221 of 1,221 lines (run 2) |
| Largest loss difference | 0 (bit-equal) | 0 (bit-equal) |
| Every step present (C5) | n/a | Yes in `losses.txt`: all 1,221 lines compared line for line with dry run 1's. `metrics.jsonl` was returned but not compared (TSAI, 18 Nov), so C5 is met for `losses.txt` only |
| Stop run equal to dry run 1 up to step 610 (C6) | n/a | Yes, lines 1 to 610 identical: no run-to-run noise |
| Job duration (start to exit) | about 6 min 8 s start to exit: start-up, the 2.2 GB load and the write-out; not split by phase. For reference, CK-13's LOW threshold is 600 s (job start to first productive step, not the same measure) | about 30 min 39 s: mostly the 611 training steps 611 to 1,221; not a restore time |
| Result | **PASS** | **PASS** |

**What this shows.** Dry run 1's checkpoint loads and gives back the same model. For job A, a matching `losses.txt` means the loss history stored in the checkpoint came back intact; job A trains no step, so it is not a second reproduction of the losses. Job B is the reproduction: a run stopped halfway and restored
from its checkpoint finishes bit-for-bit the same as the run that was never stopped: same loss at every one of the
1,221 steps and the same final model. On a single GPU the run is fully repeatable, so the open question in the #491 plan (bit-equal, or only
close because of run-to-run noise on the GPU: section 3 and job request B) was answered with bit-equal.

**What it does not show.** Both jobs used `train_week2.py`'s own `checkpoint.pt`, saved after a clean stop, not a
kill. The COMPLETE-only restart after a kill is shown by the Team 07 restart test (section 4). TSAI agrees with the
risk in section 4: before the week-5 main run, the trainer should save through the Team 07 `Checkpointer`.
