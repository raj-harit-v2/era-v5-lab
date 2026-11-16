# Week 3 rotation: @s9k96 (G7 -> G8)

Week-3 work order, rotation tasks R1 and R2. Same fault-injection pattern as PR #375, on two other rules.

| Task | Status | Where |
|---|---|---|
| R1. Test two alerts with an injected fault | Done | [`test_alert_injection_s9k96.py`](test_alert_injection_s9k96.py) (6 pytest tests) |
| R2. Record the time to alert | Done | below, and the shared table in [`../docs/alert_tests.md`](../docs/alert_tests.md) |

## R1. Two alerts, injected faults

A 200-step synthetic training stream (seed 19) is written through `MetricsWriter` and checked by `AlarmMonitor`,
both in-harness and by reading `metrics.jsonl` the way `alarms.py --jsonl` does. Both monitors use
`ema_z_threshold=5.0` (the rule is off by default) and `moe_patience=5` (the default is 1,000 steps).

| Alert | Severity | Fault | Fault step | Fired at | Verdict |
|---|---|---|---|---|---|
| `moe_routing` | warn | expert 3 of 8 gets no tokens, steps 120-129 | 120 | 124 (120 + patience 5 - 1) | PASS |
| `ema_z` | warn | `gradient_norm` + 0.35 (about 6 sigma) | 155 | 155 | PASS |

Each fires once and nothing else fires, on either path.

## R2. Time to alert

| Alert | `delta_steps` (in-harness / `metrics.jsonl`) | `in_harness_ms` | `jsonl_flush_to_alert_ms` |
|---|---|---|---|
| `moe_routing` | 4 / 10 | 0.019 | 0.523 |
| `ema_z` | 0 / 5 | 0.017 | 0.492 |

One run on a laptop CPU (Apple M5); the milliseconds vary by a few microseconds between runs.

**Findings** (details in [`../docs/alert_tests.md`](../docs/alert_tests.md)):
1. `moe_routing` time to alert is set by `moe_patience`: 4 steps here, 999 steps with the default.
2. A big gradient spike pages `spike_score` and silences `ema_z` on the same step; `ema_z` only adds a warn for jumps between its threshold and 7 sigma.
3. An expert at 5% of a fair share counts as dead in `MetricsWriter` (`dead_experts_count`) but `moe_routing` needs an exact 0.0 load or MaxVio > 1.0, so it never fires.

## Reproduce

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_s9k96.py -q
python teams/08-monitoring/alarms/test_alert_injection_s9k96.py     # prints the table rows
```
