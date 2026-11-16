# Week 3 rotation: @pyru (G11 -> G8)

Week-3 work order, rotation tasks R1 and R2. Same fault-injection pattern as PR #375, on the two rules the
Team 8 lead confirmed for me: `static_bound` and `throughput_drop`.

| Task | Status | Where |
|---|---|---|
| R1. Test two alerts with an injected fault | Done | [`test_alert_injection_pyru.py`](test_alert_injection_pyru.py) (8 pytest tests) |
| R2. Record the time to alert | Done | below, and the shared table in [`../docs/alert_tests.md`](../docs/alert_tests.md) |

## R1. Two alerts, injected faults

A 400-step synthetic training stream (seed 23) is written through `MetricsWriter` and checked by `AlarmMonitor`,
both in-harness and by reading `metrics.jsonl` the way `alarms.py --jsonl` does. Each step has `loss_ntp`, `lr`,
`tokens_per_second` (about 38,000; 650 on step 0, a slow setup step) and `gpu_alloc_gib` (about 24.5 GiB).
Both monitors use `bounds={"gpu_alloc_gib": (None, 40.0)}`, the bound in `tests/test_alarms.py`; `throughput_drop`
uses the default settings (10% drop, 100 steps).

| Alert | Severity | Fault | Fault step | Fired at | Verdict |
|---|---|---|---|---|---|
| `static_bound` | warn | `gpu_alloc_gib` about 44 GiB on steps 125-144 (above the 40 GiB bound) | 125 | 125 | PASS |
| `throughput_drop` | warn | `tokens_per_second` 25% below normal on steps 200-349 | 200 | 299 (200 + 100 - 1) | PASS |

Each fires once and nothing else fires, on either path. `static_bound` does not fire again on steps 126-144
(the rule latches until the metric comes back), `throughput_drop` does not fire again on steps 300-349, and the
slow step-0 setup value raises no alarm.

Three more checks in the test file:
- a 99-step slowdown gives no alarm, a 100-step slowdown gives one, and an 8% slowdown gives none (the rule is 10%);
- `static_bound` fires again after the metric comes back under the bound and crosses it a second time;
- `AlarmMonitor()` with no bounds gives no `static_bound` alarm, even at 50 GiB.

## R2. Time to alert

| Alert | `delta_steps` (in-harness / `metrics.jsonl`) | `in_harness_ms` | `jsonl_flush_to_alert_ms` |
|---|---|---|---|
| `static_bound` | 0 / 5 | 0.064 | 4.134 |
| `throughput_drop` | 99 / 100 | 0.082 | 3.577 |

One run on a laptop CPU (Windows 11, Python 3.12). Over four runs, `in_harness_ms` was 0.04 to 0.11 ms and
`jsonl_flush_to_alert_ms` was 3.6 to 4.8 ms; most of the file-path time is the disk sync in `MetricsWriter.flush()`.
For `throughput_drop`, `jsonl_flush_to_alert_ms` runs from the write of the step-299 row.

In a real run, the time to alert is:
- `static_bound`: the faulty step itself in-harness; up to 9 more steps on the `metrics.jsonl` path.
- `throughput_drop`: 100 slow steps, that is `tps_patience × normal step time / (1 - drop)`. With a 25% drop this is
  about 133 normal step times, so the alert comes within one minute only if a normal step takes less than 0.45 s.

Not measured: the time from `metrics.jsonl` to Grafana. This test stops at the file.

## Findings

1. **`static_bound` is off unless bounds are set.** `AlarmMonitor()`, as in the README example, has no bounds,
   and `alarms.py --jsonl` has no option to pass them. For dry run 1 the harness must pass `bounds` or this rule
   never fires. The team needs to choose which metrics get bounds and the limit for each.
2. **`throughput_drop` time to alert is set by `tps_patience`.** It needs 100 slow steps (see R2). A smaller
   `tps_patience` alerts sooner; its false-alarm rate was not tested here.
3. **The `metrics.jsonl` path sees a finite alarm row only at the next flush.** The step-125 `static_bound` row
   reached the file at step 130; the step-299 `throughput_drop` row at step 300. This matches the `spike_score`
   finding in PR #375.

## Reproduce

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_pyru.py -q
python teams/08-monitoring/alarms/test_alert_injection_pyru.py     # prints the table rows
```
