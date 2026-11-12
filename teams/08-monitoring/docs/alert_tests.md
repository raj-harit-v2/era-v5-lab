# Alert tests: fault injection and time to alert (Week 3 rotation)

Each Week 3 rotator in Team 08 tests rules in [`alarms/alarms.py`](../alarms/alarms.py) with an injected fault and
records the time to alert. Add one row per rule you test, plus a short "How to reproduce" note under your name.

## Columns

| Column | Meaning |
|---|---|
| `rule_1 & rule_2` | the rule tested, with its severity |
| `injection_mode` | how the fault was injected (synthetic stream, CPU training run, replayed `metrics.jsonl`, ...) |
| `fault_step` | step where the faulty value was written |
| `alert_step` | step where the in-harness `AlarmMonitor.step()` fired; in brackets, the step where a monitor reading `metrics.jsonl` fired |
| `delta_steps` | `alert_step - fault_step` (in-harness; in brackets, the `metrics.jsonl` path) |
| `in_harness_ms` | `time.perf_counter()` around `AlarmMonitor.step()` on the faulty step |
| `jsonl_flush_to_alert_ms` | from `MetricsWriter.write()` on the faulty step until a monitor reading `metrics.jsonl` fires for it |
| `verdict` | PASS if the expected rule and severity fire on the faulty step, with no false alarms |

## Results

| rotator | rule_1 & rule_2 | injection_mode | fault_step | alert_step | delta_steps | in_harness_ms | jsonl_flush_to_alert_ms | verdict |
|---|---|---|---|---|---|---|---|---|
| @raghavTayal | `non_finite` (stop) | synthetic 150-step stream, `MetricsWriter` + `AlarmMonitor` | 140 | 140 (jsonl: 140) | 0 (jsonl: 0) | 0.004 | 0.160 | PASS |
| @raghavTayal | `spike_score` (page) | synthetic 150-step stream, `MetricsWriter` + `AlarmMonitor` | 125 | 125 (jsonl: 130) | 0 (jsonl: 5) | 0.015 | 0.359 | PASS |

## @raghavTayal: `non_finite` and `spike_score` (Issue #19)

**Setup.** [`alarms/test_alert_injection_raghav.py`](../alarms/test_alert_injection_raghav.py) runs a 150-step
synthetic training stream (seed 19): `loss_ntp = 2.2 + 1.5·exp(−step/60)` plus Gaussian noise (σ = 0.01), and `lr`.
Every step is written through `MetricsWriter` (`flush_every = 10`) and checked twice:

- **in-harness:** `AlarmMonitor.step()` on the same values the trainer writes;
- **`metrics.jsonl`:** a second `AlarmMonitor` reads each newly flushed line the way `alarms.py --jsonl` does.

**Faults.**
- `spike_score`: `loss_ntp` + 5.0 at step 125 (125 clean steps first, so the 100-step window is warm).
- `non_finite`: `loss_ntp = NaN` at step 140.

**Results.** Both rules fire with the expected severity on the faulty step in-harness, and there are no other alarms
on either path. The timings are from one run on a laptop CPU (Apple Silicon, Python 3.14); they vary by a few
microseconds between runs.

**Finding: the `metrics.jsonl` path sees a finite fault only at the next flush.** `MetricsWriter` flushes a row with
a non-finite value at once (stored as `"nan"`), so `non_finite` reaches the file on the same step. A finite spike row
stays in the buffer until the next `step % 10 == 0` flush, so a monitor that reads the file sees the step-125 spike
at step 130: up to `flush_every − 1` = 9 steps late. The milliseconds above are small only because a synthetic step
takes microseconds. In a real run, the file-path delay for `spike_score` is about `delta_steps × step time`. The
in-harness monitor in `train.py` has no such delay.

**How to reproduce.**

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_raghav.py -q   # 5 tests
python teams/08-monitoring/alarms/test_alert_injection_raghav.py                 # prints the two table rows
```

The test needs only `pytest` (no NumPy or torch). It checks the rule, severity, `delta_steps = 0` in-harness, the
`metrics.jsonl` flush lag (0 for NaN, 5 for the step-125 spike), no false alarms, non-negative timings, and that the
NaN row is stored as `"nan"`.
