# G7 Week 3 — Infrastructure Rotation (R1/R2)

**Owner:** Siva Ajjapu (@AJJAPUSIVA)
**Team:** 07 — Infrastructure
**Week:** 3
**Report date:** 17 November 2026
**Status:** Draft — R1 per-step evidence pending; R2 restore drill results received

## Assignment

| Task | Assignment | Status |
|---|---|---|
| R1 | Offline monitoring, Dry Run 1 steps 1–305 | Pending full-run logs |
| R2 | Failure, restart and restore evidence audit | TSAI restore results available |
| Gate 3 | Submit rotation evidence by 20 Nov 2026 | Pending review |

Dry Run 1 completed on 16 November 2026 under G5 PR #475.
Pradeep confirmed that there is no live R1 monitoring shift.
The rotation instead reviews the completed run's logs.

## R1 — Offline Monitoring, Steps 1–305

### Evidence sources

- Training job: https://github.com/theschoolofai/era-v5-lab/pull/475
- Assigned range: steps 1–305 inclusive
- Full-run metrics.jsonl: Pending
- Full-run losses.txt: Pending
- Full-run summary.json: Pending
- Team 8 alarm implementation: teams/08-monitoring/alarms/alarms.py

The evidence folder associated with PR #475 initially contained
only a three-step CPU smoke test. That smoke test is not evidence
for the full 1,221-step TSAI training run.

### Required checks

| Check | Method | Finding |
|---|---|---|
| Step continuity | Verify steps 1–305 exist exactly once | Pending logs |
| Loss spikes | Review loss values and unusual jumps | Pending logs |
| Gradient norm | Check non-finite values and spikes | Pending logs |
| Throughput | Check sudden drops and variability | Pending logs |
| G8 alarms | Execute alarms.py offline on actual metrics.jsonl | Pending logs |

### Current R1 finding

TSAI reported that Dry Run 1 completed 1,221 of 1,221 steps.
This is a run-level summary, not independent verification of
continuity, losses, gradient norms or throughput for steps 1–305.

If the full-run logs are not available by Wednesday,
18 November 2026 EOD, this report will retain the
"not independently verified" findings rather than claim PASS.

## R2 — Failure and Restart Audit

### Original Dry Run 1

Based on G7 team and instructor updates:

- The run completed 1,221/1,221 steps.
- Zero failures or restarts were reported.
- The run used Team 05's train_week2.py.
- It did not run under the G7 supervisor or Checkpointer.
- The final checkpoint was saved at step 1,221.
- No periodic 20/30-minute COMPLETE checkpoints or
  commits.jsonl were produced by that run.

Consequently, the original run cannot demonstrate recovery
from an actual failure or a COMPLETE-only restart.

### Separate TSAI Restore Drill — PR #491

Source: https://github.com/theschoolofai/era-v5-lab/pull/491

TSAI executed two restore jobs and reported PASS on checks C1–C6.

#### Job A — Restore final checkpoint

| Check | Reported result |
|---|---|
| Input | Original final checkpoint, step 1,221 |
| Exit code | 0 |
| Final step | 1,221 |
| Status | COMPLETED |
| Final model SHA-256 | Equal to original Dry Run 1 |
| Losses | Identical, 1,221/1,221 lines |
| Job start-to-exit duration | Approximately 6 min 8 s |
| Overall result | PASS |

Job A demonstrates successful restoration of the completed
training state. It does not demonstrate further training
after the final step.

#### Job B — Stop at 610, resume and continue

| Check | Reported result |
|---|---|
| Initial stop | Step 610, as requested |
| Initial status | INCOMPLETE_NOT_A_RESULT |
| First 610 losses | Identical to original Dry Run 1 |
| Resume | Step 610 through step 1,221 |
| Steps trained after resume | 611 |
| Final status | COMPLETED |
| Final model SHA-256 | Equal to original Dry Run 1 |
| Final losses | Identical, all 1,221 lines |
| Resume job start-to-exit duration | Approximately 30 min 39 s |
| Overall result | PASS |

The instructor reported that checks C1–C6 passed,
including bit-equal results on a single GPU.

The Job B duration includes resumed training, checkpoint
loading and saving. It is not an isolated restore-load time.

### R2 findings and limitations

- A separate TSAI drill demonstrated successful restoration
  and bit-equal stop/resume/continue behavior.
- The drill does not imply that the original Dry Run 1
  encountered a failure.
- The original Dry Run 1 did not demonstrate G7 supervisor
  restart behavior or COMPLETE-only checkpoint recovery.
- The COMPLETE-only restart evidence remains in the G7
  restart_cpu.txt and restart_node.txt tests.
- The instructor confirmed that train_week2.py writes
  checkpoint.pt directly without a COMPLETE marker.
- TSAI agreed that the Week 5 main run should save through
  the G7 Checkpointer.

## Open Items

- [ ] Obtain real TSAI metrics.jsonl, losses.txt and summary.json.
- [ ] Verify R1 step continuity for steps 1–305.
- [ ] Review loss, gradient norm and throughput for steps 1–305.
- [ ] Run G8 alarms offline and record results.
- [x] Record TSAI restore-drill results from PR #491.
- [x] Distinguish original-run history from separate restore tests.
- [ ] Request G7 lead review for Gate 3.

## References

- G5 Dry Run 1: https://github.com/theschoolofai/era-v5-lab/pull/475
- G7 restore drill: https://github.com/theschoolofai/era-v5-lab/pull/491

## Conclusion

The original Dry Run 1 completed successfully, with no
reported restarts and without the G7 Checkpointer.

The separate TSAI restore drill passed all reported checks
C1–C6, with identical final model SHA-256 and loss histories.

R1 step-level verification for assigned steps 1–305 remains
pending receipt of the actual full-run training logs.
