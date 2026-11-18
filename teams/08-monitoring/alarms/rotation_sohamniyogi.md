# Week 3 rotation: @sohamniyogi (G3 -> G8)

Week-3 work order, rotation tasks R1 and R2 (Issue #25). Same fault-injection pattern as PR #375, #452 and #464,
on the two faults in the work order: (1) a `validation_bpb` / `validation_loss` regression and (2) a loss spike right
after a checkpoint restore.

| Task | Status | Where |
|---|---|---|
| R1. Test the two alerts with an injected fault | Done | [`test_alert_injection_sohamniyogi.py`](test_alert_injection_sohamniyogi.py) (8 pytest tests) |
| R2. Record the time to alert | Done | below, and the shared table in [`../docs/alert_tests.md`](../docs/alert_tests.md) |

## Before the test: no rule caught a validation regression

`alarms.py` had no rule for (1):
- `spike_score` watches the training losses and `gradient_norm` only.
- `static_bound` is a fixed ceiling. A validation curve falls during training, so a ceiling set at the start never
  sees it turn back up. The test `test_finding_static_bound_misses_regression` records this.

So this rotation adds one opt-in rule to `alarms.py`, **`val_regression`** (warn):
- **Fires when** `validation_bpb` or `validation_loss` is more than `val_regression_frac` above that metric's best
  value so far, for `val_patience` validation runs in a row (default 1).
- **Off by default**, like `ema_z` and `bounds`: `AlarmMonitor()` behaves exactly as before. `--synthetic 3000` still
  gives 11/11 caught and 0 false alarms, and the 116 existing alarm tests pass.
- **Checkpoints:** its state (best value and streak per metric) is in `state_dict()`. A checkpoint from before the
  rule still loads.

## R1. Two alerts, injected faults

A 300-step synthetic stream (seed 25) is written through `MetricsWriter` and checked by `AlarmMonitor`, both
in-harness and by reading `metrics.jsonl` the way `alarms.py --jsonl` does.
- **Training rows:** `loss_ntp` about 2.0 on every step.
- **Validation rows:** every 25 steps, a validation run writes `validation_bpb` (falling from 1.8 to about 1.25) and
  `validation_loss`.
- **Monitors:** both use `AlarmMonitor(val_regression_frac=0.02)`.

| Alert | Severity | Fault | Fault step | Fired at | Verdict |
|---|---|---|---|---|---|
| `val_regression` | warn | the step-275 validation run is 5% above the best so far, on both metrics | 275 | 275 (once per metric) | PASS |
| `spike_score` after restore | page | checkpoint at 200 (model + `state_dict()` as JSON), crash at 207, resume from 200 with `load_state_dict()`; the first resumed step has `loss_ntp` + 0.5 (a bad restore) | 201 | 201 | PASS |

Each fires once (once per metric for `val_regression`), and nothing else fires, on either path. The process that
crashed fires nothing on steps 0-207.

## R2. Time to alert

| Alert | `delta_steps` (in-harness / `metrics.jsonl`) | `in_harness_ms` | `jsonl_flush_to_alert_ms` |
|---|---|---|---|
| `val_regression` | 0 / 5 | 0.022 | 0.513 |
| `spike_score` after restore | 0 / 9 | 0.021 | 0.768 |

One run on a laptop CPU (Apple Silicon, Python 3.11). The milliseconds vary by a few microseconds between runs.

**Findings** (details in [`../docs/alert_tests.md`](../docs/alert_tests.md)):
1. **A monitor that is not restored is blind after a restart.**
   - A new `AlarmMonitor` has an empty window, and `spike_score` needs 100 clean steps first. So it misses the
     step-201 spike that the restored monitor pages on.
   - It also takes a regression that is already there at the first validation after the restart (step 225) as its
     new best, and never warns.
   - The harness must save `state_dict()` with every checkpoint and call `load_state_dict()` on resume.
2. **A crash loses up to 9 rows of `metrics.jsonl`.**
   - The writer's rows after the last flush (201-207 here) never reach the file. The resumed run writes 201 onwards
     again, so the file has no gap and no duplicate when the checkpoint is on a flush step.
   - Otherwise a checkpoint after the last flush leaves a gap, and one before it duplicates steps.
   - The file monitor keeps its window across the restart, and sees the spike at the step-210 flush, 9 steps late.
3. **Time to alert for `val_regression` is set by how often validation runs.**
   - In-harness it fires on the faulty validation step itself (delta 0), but a regression can only be seen every
     `run.eval_every_steps` steps.
   - With `val_patience` > 1 it waits that many validation runs.

## Reproduce

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_sohamniyogi.py -q
python teams/08-monitoring/alarms/test_alert_injection_sohamniyogi.py     # prints the table rows
```
