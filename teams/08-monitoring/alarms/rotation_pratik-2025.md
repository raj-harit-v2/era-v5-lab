# Week 3 rotation: @pratik-2025 (G7 -> G8)

Week-3 work order, rotation tasks R1 and R2 (Issue #24). The six rules in `alarms.py` are covered by other rotators,
so these are two new rules for dry run 1, confirmed by the Team 08 lead on 16 Nov.

| Task | Status | Where |
|---|---|---|
| R1. Test two alerts with an injected fault | Done | [`continuity_rules.py`](continuity_rules.py) (the two rules) and [`test_alert_injection_pratik.py`](test_alert_injection_pratik.py) (9 pytest tests) |
| R2. Record the time to alert | Done | below, and the shared table in [`../docs/alert_tests.md`](../docs/alert_tests.md) |

## The two rules

| Rule | Watches | Fires when | Severity |
|---|---|---|---|
| `step_continuity` | the step number of each row | a step is skipped (kind `missing`, with the first and last missing step) | `page` |
| | | a step comes again after a newer one (kind `repeated`, once per restart) | `warn` |
| `loader_stall` | `loader_wait_time` (s) | above 1.0 s for 20 steps in a row; fires once, re-arms when it drops back | `warn` |

Why these two. The dry run 1 focus is "a missing step is a bug", and no rule in `alarms.py` reports a missing step:
`throughput_drop` and `moe_routing` only restart their streaks on a gap. `loader_stall` tells a starved data loader
apart from slow GPU work, which `throughput_drop` alone cannot. The 1.0 s and 20-step defaults are placeholders until
Team 06 gives per-step loader times.

The rules are in their own file so that week-3 rotators do not edit `alarms.py` at the same time. They return events
in the same shape as `AlarmMonitor.step()`, so the core team can fold them in later.

## R1. Two alerts, injected faults

A 200-step synthetic training stream (seed 24) is written through `MetricsWriter` and checked by `ContinuityMonitor`,
both in-harness and by reading `metrics.jsonl` the way `alarms.py --jsonl` does.

| Alert | Severity | Fault | Fault step | Fired at | Verdict |
|---|---|---|---|---|---|
| `step_continuity` | page | the row for step 185 is never written | 185 | 186 (the next row shows the gap) | PASS |
| `loader_stall` | warn | `loader_wait_time` 2.0 s (normal 0.05 s), steps 120 to 159 | 120 | 139 (120 + patience 20 - 1) | PASS |

Each fires once and nothing else fires, on either path. A stall shorter than 20 steps does not alert.

## R2. Time to alert

| Alert | `delta_steps` (in-harness / `metrics.jsonl`) | `in_harness_ms` | `jsonl_flush_to_alert_ms` |
|---|---|---|---|
| `step_continuity` | 1 / 5 | 0.011 | 1.620 |
| `loader_stall` | 19 / 20 | 0.007 | 30.300 |

One run on a laptop CPU. The `jsonl_flush_to_alert_ms` values include the disk write (`fsync`) of the flush, which is slow and uneven on this laptop (1.6 ms and 30.3 ms); the in-harness time is the rule itself. In a real run the delay is about
`delta_steps x step time`.

## Finding: a restore can lose metric rows for good

`MetricsWriter` writes rows to disk every 10 steps. A trainer killed with SIGKILL loses the rows still in memory (up to
9). After the restore, the trainer redoes the steps after its checkpoint. Whether rows are lost depends on where the
checkpoint is:

| Checkpoint | Killed after | Last flush | What the file shows | Alert |
|---|---|---|---|---|
| step 125 (before the last flush) | 137 | 130 | 126 to 130 twice; every step present | `repeated` warn at 126 |
| step 135 (after the last flush) | 137 | 130 | **131 to 135 never written** | `missing` page at 136 |
| step 135, metrics flushed at the save | 137 | 135 | every step present | none |

Dry run 1 (#475) ran to the end with no restart, so it did not hit this. It matters for the next runs: Team 07's
`Checkpointer` saves on a timer (every 10 minutes, `docs/checkpoint_interval.md`), not on a multiple of 10 steps, so
the second case can happen on any kill and restore. That would break "no missing steps" (Team 08) and "no lost steps"
(Team 07). Team 05's `train_week2.py` has its own writer with the same 10-step flush, so the same applies there.

**Proposal (for Team 07 and Team 05):** flush `metrics.jsonl` when a checkpoint is saved. Then every row up to the
checkpoint is on disk before the checkpoint can be restored. The last test shows this keeps every row.

**For the dashboard:** after a restore, the redone steps are in the file twice. The row written after the restart is
the one to keep.

## Reproduce

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_pratik.py -q
python teams/08-monitoring/alarms/test_alert_injection_pratik.py     # prints the table rows
```

The test needs only `pytest`.
