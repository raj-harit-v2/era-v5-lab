# Week 3 rotation: @swatibansal (G10 -> G8)

Week-3 work order, rotation tasks R1 and R2. Same fault-injection pattern as PR #375 and PR #452, on the two
rules in `alarms.py` that no rotator had covered yet: `throughput_drop` and `static_bound`.

| Task | Status | Where |
|---|---|---|
| R1. Test two alerts with an injected fault | Done | [`test_alert_injection_swatibansal.py`](test_alert_injection_swatibansal.py) (7 pytest tests) |
| R2. Record the time to alert | Done | below, and the shared table in [`../docs/alert_tests.md`](../docs/alert_tests.md) |

## R1. Two alerts, injected faults

A 300-step synthetic training stream (seed 19) is written through `MetricsWriter` and checked by `AlarmMonitor`,
both in-harness and by reading `metrics.jsonl` the way `alarms.py --jsonl` does. Both monitors use
`AlarmMonitor(bounds={"gpu_alloc_gib": (None, 70.0)})`. `throughput_drop` keeps its defaults (100-step window,
10% drop, patience 100). `static_bound` is off unless `bounds` is passed; here the bound is an upper limit on
PyTorch GPU memory, standing in for "the run is about to go out of memory".

| Alert | Severity | Fault | Fault step | Fired at | Verdict |
|---|---|---|---|---|---|
| `throughput_drop` | warn | `tokens_per_second` 25% slower from step 150 to the end | 150 | 249 (150 + patience 100 - 1) | PASS |
| `static_bound` | warn | `gpu_alloc_gib` jumps from about 60 to about 72 GiB, steps 205-230 | 205 | 205 | PASS |

Each fires once and nothing else fires, on either path.

## R2. Time to alert

| Alert | `delta_steps` (in-harness / `metrics.jsonl`) | `in_harness_ms` | `jsonl_flush_to_alert_ms` |
|---|---|---|---|
| `throughput_drop` | 99 / 100 | 0.016 | 0.220 |
| `static_bound` | 0 / 5 | 0.014 | 0.358 |

One run on a laptop CPU (Apple Silicon, Python 3.14); the milliseconds vary by a few microseconds between runs.

**Findings** (details in [`../docs/alert_tests.md`](../docs/alert_tests.md)):
1. `throughput_drop` time to alert is set by `tps_patience`: 99 steps with the default. A slowdown that lasts
   99 steps or fewer never alerts, because the streak resets as soon as one step is back at speed.
2. The `metrics.jsonl` lag is 0 when the fault lands on a flush step (`step % 10 == 0`) and up to 9 steps
   otherwise. The same `static_bound` fault at step 210 is seen at 210; at step 205 it is seen at 210.
3. `static_bound` is an edge-triggered latch. A metric that stays out of bounds for 26 steps fires once, not 26
   times, and fires again only after it returns in-bounds and crosses the bound a second time.

## Reproduce

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_swatibansal.py -q
python teams/08-monitoring/alarms/test_alert_injection_swatibansal.py     # prints the table rows
```
