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
| @s9k96 | `moe_routing` (warn) | synthetic 200-step stream, `MetricsWriter` + `AlarmMonitor`, `moe_patience=5` | 120 | 124 (jsonl: 130) | 4 (jsonl: 10) | 0.019 | 0.523 | PASS |
| @s9k96 | `ema_z` (warn) | synthetic 200-step stream, `MetricsWriter` + `AlarmMonitor`, `ema_z_threshold=5.0` | 155 | 155 (jsonl: 160) | 0 (jsonl: 5) | 0.017 | 0.492 | PASS |
| @swatibansal | `throughput_drop` (warn) | synthetic 300-step stream, `MetricsWriter` + `AlarmMonitor`, default `tps_patience=100` | 150 | 249 (jsonl: 250) | 99 (jsonl: 100) | 0.016 | 0.220 | PASS |
| @swatibansal | `static_bound` (warn) | synthetic 300-step stream, `MetricsWriter` + `AlarmMonitor`, `bounds={"gpu_alloc_gib": (None, 70.0)}` | 205 | 205 (jsonl: 210) | 0 (jsonl: 5) | 0.014 | 0.358 | PASS |
| @pyru | `static_bound` (warn) | synthetic 400-step stream, `MetricsWriter` + `AlarmMonitor`, `bounds={"gpu_alloc_gib": (None, 40.0)}` | 125 | 125 (jsonl: 130) | 0 (jsonl: 5) | 0.064 | 4.134 | PASS |
| @pyru | `throughput_drop` (warn) | synthetic 400-step stream, `MetricsWriter` + `AlarmMonitor`, default settings | 200 | 299 (jsonl: 300) | 99 (jsonl: 100) | 0.082 | 3.577 | PASS |
| @sohamniyogi | `val_regression` (warn) | synthetic 300-step stream, `MetricsWriter` + `AlarmMonitor`, `val_regression_frac=0.02`, validation every 25 steps | 275 | 275 (jsonl: 280) | 0 (jsonl: 5) | 0.022 | 0.513 | PASS |
| @sohamniyogi | `spike_score` (page) after a checkpoint restore | synthetic 300-step stream, `MetricsWriter` + `AlarmMonitor`; checkpoint at 200, crash at 207, resume with `load_state_dict()` | 201 | 201 (jsonl: 210) | 0 (jsonl: 9) | 0.021 | 0.768 | PASS |
| @pratik-2025 | `step_continuity` (page) | synthetic 200-step stream, `MetricsWriter` + `ContinuityMonitor` (new rule, `continuity_rules.py`) | 185 | 186 (jsonl: 190) | 1 (jsonl: 5) | 0.011 | 1.620 | PASS |
| @pratik-2025 | `loader_stall` (warn) | synthetic 200-step stream, `MetricsWriter` + `ContinuityMonitor` (new rule), 1.0 s for 20 steps | 120 | 139 (jsonl: 140) | 19 (jsonl: 20) | 0.007 | 30.300 | PASS |

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

## @s9k96: `moe_routing` and `ema_z` (Issue #19)

**Setup.** [`alarms/test_alert_injection_s9k96.py`](../alarms/test_alert_injection_s9k96.py) runs a 200-step
synthetic stream (seed 19): `gradient_norm = 1.0 + N(0, 0.05)`, an 8-expert `expert_load` (shares near 1/8, noise 5%),
`loss_ntp` and `lr`. Every step goes through `MetricsWriter` (`flush_every = 10`) and is checked in-harness and
from `metrics.jsonl`, as in the Raghav test. Both monitors use `AlarmMonitor(ema_z_threshold=5.0, moe_patience=5)`:
`ema_z` is off by default, and `moe_routing` waits 1,000 steps by default, longer than this stream.

**Faults.**
- `ema_z`: `gradient_norm` + 0.35 at step 155 (about 6 sigma: above the EMA z threshold 5.0, below `spike_score`'s
  7 sigma). The alarm reports z = 6.29.
- `moe_routing`: expert 3 gets no tokens at steps 120-129. The rule needs `moe_patience` consecutive bad steps,
  so the expected alert step is 120 + 5 - 1 = 124, and `delta_steps = 4` is by design, not lag.
  For this row `jsonl_flush_to_alert_ms` runs from the write of the step-124 row.

**Results.** Both rules fire with severity `warn` on the expected step in-harness, once each, and nothing else fires
on either path (`spike_score` stays quiet on the 6-sigma jump). The timings are from one run on a laptop CPU
(Apple M5, Python 3.15); they vary by a few microseconds between runs.

**Finding 1: `spike_score` silences `ema_z` on the same step.** With `ema_z` enabled, a +0.35 jump (6 sigma)
fires only `ema_z`. A +1.0 jump (about 20 sigma) fires only `spike_score` (page): `ema_z` is skipped when the step
has already paged, so enabling it adds a `warn` for moderate jumps and nothing for large ones. The test
`test_finding_spike_score_silences_ema_z_on_same_step` records this.

**Finding 2: an expert at 5% of a fair share is dead for `MetricsWriter` but not for `moe_routing`.** The writer
counts an expert below 10% utilization as dead (`dead_experts_count`). `moe_routing` counts `dead_experts` only
at an exact load of 0.0, and otherwise needs MaxVio > 1.0. With one of 8 experts at 5% of a fair share for 10 steps,
the row has `dead_experts_count = 1`, MaxVio is about 0.14, and no alarm fires. A partly collapsed router is on the
dashboard but never pages. The test `test_finding_expert_at_5_percent_is_dead_for_writer_but_not_for_moe_routing`
records the current behavior; if the rule changes to use the writer's threshold, update that test.

**Finding 3: time to alert for `moe_routing` is set by `moe_patience`.** With the default 1,000 steps, the same fault
alerts at step 1,119. On the `metrics.jsonl` path the alert is 10 steps after the fault here (step 130, the next flush).

**How to reproduce.**

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_s9k96.py -q   # 6 tests
python teams/08-monitoring/alarms/test_alert_injection_s9k96.py                 # prints the two table rows
```

The test needs only `pytest` (no NumPy or torch). It checks the rule, severity and alert step in-harness, the
`metrics.jsonl` flush lag (5 for `ema_z`, 10 for `moe_routing`), no false alarms, non-negative timings, and the two
findings above.

## @swatibansal: `throughput_drop` and `static_bound` (Issue #19)

**Setup.** [`alarms/test_alert_injection_swatibansal.py`](../alarms/test_alert_injection_swatibansal.py) runs a 300-step
synthetic stream (seed 19): `tokens_per_second = 50,000 x (1 + N(0, 0.01))` (half speed at step 0, the setup step the
rule skips), `gpu_alloc_gib = 60 + N(0, 0.2)`, `loss_ntp` and `lr`. Every step goes through `MetricsWriter`
(`flush_every = 10`) and is checked in-harness and from `metrics.jsonl`, as in the Raghav and Shubham tests. Both
monitors use `AlarmMonitor(bounds={"gpu_alloc_gib": (None, 70.0)})`: `throughput_drop` keeps its defaults (100-step
window, 10% drop, `tps_patience = 100`), and `static_bound` is off unless `bounds` is passed.

**Faults.**
- `throughput_drop`: `tokens_per_second` falls by 25% from step 150 to the end of the stream. The rule needs
  `tps_patience` consecutive slow steps, so the expected alert step is 150 + 100 - 1 = 249, and `delta_steps = 99`
  is by design, not lag. For this row `jsonl_flush_to_alert_ms` runs from the write of the step-249 row.
- `static_bound`: `gpu_alloc_gib` jumps to about 72 GiB on steps 205-230, above the 70.0 upper bound. The alarm
  reports the value and the bound it crossed.

**Results.** Both rules fire with severity `warn` on the expected step in-harness, once each, and nothing else fires
on either path. The timings are from one run on a laptop CPU (Apple Silicon, Python 3.14); they vary by a few
microseconds between runs.

**Finding 1: a slowdown shorter than `tps_patience` never alerts.** The slow streak resets on the first step back at
speed, so a 25% slowdown on steps 150-248 (99 steps) fires nothing, in-harness or from the file. With the default
patience, a run can lose a quarter of its speed for 99 steps and the alarm stays silent; only the dashboard shows
it. The test `test_finding_slowdown_shorter_than_patience_never_alerts` records this.

**Finding 2: the `metrics.jsonl` lag is 0 on a flush step.** Raghav's row showed a finite fault reaching the file at
the next `step % 10 == 0` flush. The lag depends on where the fault lands: the same `static_bound` fault at step 210
(a flush step) is seen from the file at 210, and at step 205 it is seen at 210. So the file-path lag is 0 to 9 steps,
not a fixed delay. The test `test_finding_fault_on_a_flush_step_has_no_jsonl_lag` records this.

**Finding 3: `static_bound` fires once per excursion.** The rule latches on the first step out of bounds and re-arms
only when the metric returns in-bounds. Out of bounds on 205-230 gives one alarm at 205; back in bounds, then out
again on 260-265 gives a second alarm at 260. A monitor that counts alarms therefore counts excursions, not steps
out of bounds. The test `test_finding_static_bound_latches_and_rearms` records this.

**How to reproduce.**

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_swatibansal.py -q   # 7 tests
python teams/08-monitoring/alarms/test_alert_injection_swatibansal.py                 # prints the two table rows
```

The test needs only `pytest` (no NumPy or torch). It checks the rule, severity and alert step in-harness, the
`metrics.jsonl` flush lag (5 for `static_bound`, 1 for `throughput_drop`, whose alert step 249 is one short of the
step-250 flush), no false alarms, non-negative timings, and the three findings above.

## @pyru: `static_bound` and `throughput_drop`

**Setup.** [`alarms/test_alert_injection_pyru.py`](../alarms/test_alert_injection_pyru.py) runs a 400-step
synthetic stream (seed 23): `loss_ntp`, `lr`, `tokens_per_second = 38,000 + N(0, 400)` (650 on step 0, a slow setup
step) and `gpu_alloc_gib = 24.5 + N(0, 0.05)`. Every step goes through `MetricsWriter` (`flush_every = 10`) and is
checked in-harness and from `metrics.jsonl`, as in the Raghav test. Both monitors use
`AlarmMonitor(bounds={"gpu_alloc_gib": (None, 40.0)})`, the bound in `tests/test_alarms.py`; `throughput_drop` uses
the default settings (10% drop, 100 steps).

**Faults.**
- `static_bound`: `gpu_alloc_gib` about 44 GiB on steps 125-144. The rule latches, so it fires once, at step 125.
- `throughput_drop`: `tokens_per_second` 25% below normal on steps 200-349. The rule needs 100 slow steps in a row,
  so the expected alert step is 200 + 100 - 1 = 299, and `delta_steps = 99` is by design, not lag.
  For this row `jsonl_flush_to_alert_ms` runs from the write of the step-299 row.

**Results.** Both rules fire with severity `warn` on the expected step in-harness, once each, and nothing else fires
on either path, including the slow step-0 setup value. The timings are from one run on a laptop CPU (Windows 11,
Python 3.12); `jsonl_flush_to_alert_ms` was 3.6 to 4.8 ms over four runs, mostly the disk sync in
`MetricsWriter.flush()`.

**Finding 1: `static_bound` is off unless the caller passes `bounds`.** `AlarmMonitor()` (the README example) and
`alarms.py --jsonl` set none, and the CLI has no option for them. For dry run 1 the harness must pass `bounds`, or
this rule never fires. The test `test_static_bound_is_off_without_bounds` records this.

**Finding 2: time to alert for `throughput_drop` is set by `tps_patience`.** In a real run it is 100 slow steps,
`tps_patience × normal step time / (1 - drop)`: with a 25% drop, about 133 normal step times, so under one minute
only if a normal step takes less than 0.45 s. A 99-step slowdown never alerts, and neither does a drop under 10%.

**How to reproduce.**

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_pyru.py -q   # 8 tests
python teams/08-monitoring/alarms/test_alert_injection_pyru.py                 # prints the two table rows
```

The test needs only `pytest` (no NumPy or torch). It checks the rule, severity and alert step in-harness, the
`metrics.jsonl` flush lag (5 for `static_bound`, 1 for `throughput_drop`), one alarm per fault and no false alarms,
non-negative timings, the 99-step, 100-step and 8% slowdowns, re-arming of `static_bound`, and finding 1.

## @sohamniyogi: `val_regression` and `spike_score` after a checkpoint restore (Issue #25)

**Setup.** [`alarms/test_alert_injection_sohamniyogi.py`](../alarms/test_alert_injection_sohamniyogi.py) runs a 300-step
synthetic stream (seed 25).
- **Training rows:** `loss_ntp = 2.0 + N(0, 0.01)` and `lr` on every step.
- **Validation rows:** every 25 steps, `validation_bpb = 1.2 + 0.6·exp(−step/100) + N(0, 0.002)` and
  `validation_loss = 2.5 × validation_bpb`, the two metrics `MetricsWriter` writes from G5's `evaluate()`.
- **Paths:** every step goes through `MetricsWriter` (`flush_every = 10`) and is checked in-harness and from
  `metrics.jsonl`, as in the Raghav test.
- **Monitors:** both use `AlarmMonitor(val_regression_frac=0.02)`.

**New rule.** `alarms.py` had no rule for a validation regression: `spike_score` watches only the training losses
and `gradient_norm`, and a fixed `static_bound` cannot follow a falling curve. This rotation adds `val_regression`
(warn, off unless `val_regression_frac` is set; see `alarms/README.md`). `AlarmMonitor()` is unchanged: the 116
existing alarm tests pass and `--synthetic 3000` still catches 11/11 with 0 false alarms.

**Faults.**
- `val_regression`: the validation run at step 275 is 5% above the best so far, on both metrics. One alarm per
  metric, at 275.
- `spike_score` after a checkpoint restore:
  1. The first process checkpoints at step 200 (`json.dumps(monitor.state_dict())`) and dies at step 207 without
     `close()`, so the writer's rows 201-207 are lost.
  2. A second process resumes from step 200 with a new monitor and `load_state_dict()`.
  3. Its first step, 201, has `loss_ntp` + 0.5, as a bad restore would give (optimizer state or data position not
     restored). The first process saw step 201 without the spike.

**Results.** Both rules fire with the expected severity on the faulty step in-harness. Nothing else fires on either
path, including the first process on steps 0-207. The timings are from one run on a laptop CPU (Apple Silicon,
Python 3.11); they vary by a few microseconds between runs.

**Finding 1: a monitor that is not restored misses both faults after a restart.**
- With `restore=False`, the new monitor's window is empty. `spike_score` needs `min_window` = 100 clean steps, so the
  step-201 spike is missed in-harness.
- The file monitor, which kept running, still catches it.
- If the regression is already there at the first validation after the restart (step 225), the new monitor takes it
  as its best and never warns; the restored one warns at 225.
- So the harness must save `state_dict()` with each checkpoint and restore it on resume.
- The tests `test_finding_monitor_not_restored_misses_spike_after_restart` and
  `test_finding_monitor_not_restored_misses_regression_at_first_validation` record this.

**Finding 2: a crash loses the writer's unflushed rows.**
- After the crash, `metrics.jsonl` ends at step 200. Rows 201-207 were in the buffer.
- The resumed run writes 201 onwards again, so with the checkpoint on a flush step the file has no gap and no
  duplicate steps. Otherwise it does:
  - a checkpoint after the last flush (say 205) leaves its steps since that flush (201-205) missing;
  - a checkpoint before it (say 195) gets the steps after it (196-200) written twice.
- The file monitor sees the step-201 spike at the step-210 flush (`delta_steps` 9). The test
  `test_crash_loses_unflushed_rows_and_jsonl_lag` records this.

**Finding 3: a fixed `static_bound` does not catch a validation regression.**
- With `bounds={"validation_bpb": (None, 1.85)}` (just above the first validation value), the 5% rise at step 275
  (about 1.30) never fires.
- `test_finding_static_bound_misses_regression` records this.

**Finding 4: time to alert for `val_regression` is the validation interval.**
- In-harness it fires on the faulty validation step (delta 0). But a regression that starts between validation
  runs is seen only at the next one, up to `run.eval_every_steps` steps later, and `val_patience` > 1 adds further
  validation runs.
- A checkpoint written before the rule (no `val` entry) still loads (`test_finding_old_checkpoint_without_val_state_loads`).

**How to reproduce.**

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_sohamniyogi.py -q   # 8 tests
python teams/08-monitoring/alarms/test_alert_injection_sohamniyogi.py                 # prints the two table rows
```

The test needs only `pytest` (no NumPy or torch). It checks:
- the rule, severity and alert step, in-harness;
- the `metrics.jsonl` flush lag (5 for `val_regression`, 9 for the spike after the restart) and the lost rows;
- no false alarms, and non-negative timings;
- the four findings above.
## @pratik-2025: `step_continuity` and `loader_stall` (Issue #24)

**Setup.** Both rules are new, in [`alarms/continuity_rules.py`](../alarms/continuity_rules.py), because the six rules
in `alarms.py` were already covered. [`alarms/test_alert_injection_pratik.py`](../alarms/test_alert_injection_pratik.py)
runs a 200-step synthetic stream (seed 24) through `MetricsWriter` (`flush_every = 10`) and checks it in-harness and
from `metrics.jsonl`, as above.

**Faults.**
- `step_continuity`: the row for step 185 is never written. The gap shows when step 186 arrives.
- `loader_stall`: `loader_wait_time` is 2.0 s (normal 0.05 s) on steps 120 to 159; the rule needs 20 steps above 1.0 s.

**Results.** Both fire once with the expected severity, with no other alarms on either path.

**Finding: a restore can lose metric rows for good.** A trainer killed with SIGKILL loses the rows still in the
writer's memory. If the restored checkpoint is newer than the last flush, the steps between the flush and the
checkpoint are never written again (in the test: checkpoint 135, last flush 130, rows 131 to 135 lost, `missing` page
at 136). Flushing `metrics.jsonl` when a checkpoint is saved keeps every row. Details in
[`alarms/rotation_pratik-2025.md`](../alarms/rotation_pratik-2025.md).

**How to reproduce.**

```bash
python -m pytest teams/08-monitoring/alarms/test_alert_injection_pratik.py -q   # 9 tests
python teams/08-monitoring/alarms/test_alert_injection_pratik.py                 # prints the two table rows
```
