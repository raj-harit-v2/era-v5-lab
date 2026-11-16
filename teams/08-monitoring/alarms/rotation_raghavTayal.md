# Week 3 rotation: @raghavTayal (G9 → G8)

Week-3 work order, rotation tasks R1 and R2. The work was done for Issue #19
(sandeepkunkunuru/era-v5-lab#19) and merged in PR #375.

| Task | Status | Where |
|---|---|---|
| R1. Test two alerts with an injected fault | Done | [`test_alert_injection_raghav.py`](test_alert_injection_raghav.py) (5 pytest tests) |
| R2. Record the time to alert | Done | below, and the shared table in [`../docs/alert_tests.md`](../docs/alert_tests.md) |

## R1. Two alerts, injected faults

A 150-step synthetic training stream (seed 19) is written through `MetricsWriter` and checked by `AlarmMonitor`,
both in-harness and by reading `metrics.jsonl` the way `alarms.py --jsonl` does.

| Alert | Severity | Fault | Fault step | Fired at | Verdict |
|---|---|---|---|---|---|
| `non_finite` | stop | `loss_ntp = NaN` | 140 | 140 | PASS |
| `spike_score` | page | `loss_ntp` + 5.0 after 125 clean steps | 125 | 125 | PASS |

No other alarm fired on the 148 clean steps, on either path.

## R2. Time to alert

| Alert | `delta_steps` (in-harness / `metrics.jsonl`) | `in_harness_ms` | `jsonl_flush_to_alert_ms` |
|---|---|---|---|
| `non_finite` | 0 / 0 | 0.004 | 0.160 |
| `spike_score` | 0 / 5 | 0.015 | 0.359 |

One run on a laptop CPU; the milliseconds vary by a few microseconds between runs.

**Finding.** `MetricsWriter` flushes a row with a non-finite value at once, but a finite row waits for the next
`step % 10 == 0` flush. So a monitor that reads `metrics.jsonl` sees the step-125 spike at step 130: up to
`flush_every − 1` = 9 steps late. In a real run that delay is about `delta_steps × step time`. The in-harness
monitor has no delay.

## Reproduce

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_raghav.py -q
python teams/08-monitoring/alarms/test_alert_injection_raghav.py     # prints the table rows
```
