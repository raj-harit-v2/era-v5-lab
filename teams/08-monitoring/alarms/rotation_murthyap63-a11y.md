# Week 3 Dry Run 2, rotation member: murthyap63-a11y — GPU thermal and gradient telemetry

This report covers the two Dry Run 2 telemetry fault-injection responsibilities assigned to Team 08:

- **R1:** `gpu_temp_c` / `gpu_thermal_throttle` thermal alert.
- **R2:** sustained `gradient_clipping_applied` rate and `update_weight_ratio` bound alert.

## Policy note

The supplied assignment and the inspected metric catalogue define the signal names and their meanings but do not specify the complete Dry Run 2 alarm policy (numeric bounds, patience, and severity). Accordingly, `AlarmMonitor` exposes the telemetry rules as **opt-in configuration**. This test fixture uses provisional values to exercise the detector; those values must be confirmed by the Team 08 lead before production activation:

| Setting | Provisional fixture value | Basis / status |
|---|---:|---|
| GPU temperature | 85°C | Existing Grafana red colour band; not documented as an approved alarm threshold |
| Thermal condition | `gpu_thermal_throttle == 1` required | Requires actual throttle flag in addition to temperature |
| Thermal persistence | 3 consecutive optimizer steps | Test fixture only |
| Clipping rate | ≥80% over a rolling 5-step window | Test fixture only; dashboard yellow colour begins at 50%, not an approved alarm threshold |
| Clipping persistence | 3 consecutive qualifying rolling windows | Test fixture only |
| Update-weight ratio | outside `[1e-5, 1e-2]` | Test fixture only; no approved bounds found in the supplied metric catalogue |
| Severity | `warn` | Test fixture only; configurable as `warn` or `page` |

The six pre-existing alarm rules remain unchanged. Telemetry rules are disabled unless explicitly configured.

## R1. GPU thermal fault injection

The synthetic fixture holds normal rows at 68°C with throttle flag 0, then injects 88°C and throttle flag 1 at steps 61–63. The thermal condition requires both values and three consecutive observations. The in-harness alert fires at step 63, two steps after fault onset. With `MetricsWriter` flushing every 10 steps, the JSONL monitor sees that step at the step-70 flush, nine steps after fault onset.

Additional test cases verify that a hot GPU without the throttle bit does not alert, and that a cool observation or a step gap resets the persistence counter.

## R2. Sustained clipping and update-weight ratio

The fixture injects `gradient_clipping_applied=1` from steps 91–103. The rolling clipping-rate window is five observations; a rate at or above 80% must persist for three consecutive rolling windows. The alert fires at step 96 (five steps after fault onset) in-harness. JSONL detection occurs on the step-100 flush, nine steps after fault onset.

The fixture also raises `update_weight_ratio` to `2e-2` at steps 96–101, beyond the provisional upper bound `1e-2`. The bound alarm is edge-triggered: one alert per excursion, re-arming only after the value returns inside the configured interval. A separate test verifies a second alert after recovery and a second crossing.

## R2. Time to alert

| Rule | Severity | Fault step | In-harness alert | JSONL alert | Delta steps (in-harness / JSONL) |
|---|---|---:|---:|---:|---:|
| `gpu_thermal` | warn (fixture) | 61 | 63 | 70 | 2 / 9 |
| `sustained_clipping` | warn (fixture) | 91 | 96 | 100 | 5 / 9 |
| `update_weight_ratio_bound` | warn (fixture) | 96 | 96 | 100 | 0 / 4 |

Wall-clock timings are emitted by the test runner and vary between runs; they are not hard-coded in this report. The test records `time.perf_counter()` around the in-harness call and from the faulty-row write until the JSONL monitor detects the flushed row.

## How to reproduce

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_murthyap63-a11y.py -q
python teams/08-monitoring/alarms/test_alert_injection_murthyap63-a11y.py
```

The telemetry tests use a deterministic synthetic stream and a small test MetricsWriter fixture; no GPU, CUDA, NumPy or torch is required.

## Verification status

The local targeted telemetry test file passes **6 tests**. 