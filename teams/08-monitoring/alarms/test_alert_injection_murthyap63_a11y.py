"""Week 3 Dry Run 2 telemetry fault injection for Team 08.

Policy values in this test are explicit provisional fixture values, not claimed
as approved Session/Team thresholds. Production AlarmMonitor defaults leave
these telemetry rules disabled until the owner supplies policy configuration.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "metrics_logger"))
from alarms_murthyap63_a11y import AlarmMonitor  # noqa: E402

from metrics_writer import FLUSH_EVERY, MetricsWriter  # noqa: E402
STEPS = 160
# Provisional fixture policy only: use 85 C (dashboard red band), require
# hardware/software throttle flag and 3 consecutive optimizer-step observations.
THERMAL_TEMP_C = 85.0
THERMAL_PATIENCE = 3
# Provisional fixture policy only: 80% clipped over a 5-step rolling window,
# sustained for 3 consecutive complete windows; update ratio outside [1e-5, 1e-2].
CLIP_WINDOW = 5
CLIP_RATE_THRESHOLD = 0.80
CLIP_PATIENCE = 3
UPDATE_RATIO_BOUNDS = (1e-5, 1e-2)
SEVERITY = "warn"

MONITOR_KW = dict(
    thermal_temp_c=THERMAL_TEMP_C,
    thermal_patience=THERMAL_PATIENCE,
    thermal_require_throttle=True,
    clipping_rate_window=CLIP_WINDOW,
    clipping_rate_threshold=CLIP_RATE_THRESHOLD,
    clipping_patience=CLIP_PATIENCE,
    update_ratio_bounds={"update_weight_ratio": UPDATE_RATIO_BOUNDS},
    telemetry_severity=SEVERITY,
)


class JsonlTail:
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.monitor = AlarmMonitor(**MONITOR_KW)

    def poll(self):
        if not self.path.exists():
            return []
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            data = handle.read()
        end = data.rfind(b"\n") + 1
        self.offset += end
        fired = []
        for line in data[:end].decode("utf-8").splitlines():
            row = json.loads(line)
            step = row.pop("step")
            fired.extend(self.monitor.step(step, **row))
        return fired


def metrics_at(step):
    """Baseline telemetry and two injected incidents, at deterministic steps."""
    row = {
        "loss_ntp": 1.5,
        "gradient_norm": 0.8,
        "lr": 3e-4,
        "gpu_temp_c": 68.0,
        "gpu_thermal_throttle": 0,
        "gradient_clipping_applied": 0,
        "update_weight_ratio": 5e-4,
    }
    # R1 thermal incident: three consecutive hot + throttled rows, 61..63.
    if 61 <= step <= 63:
        row.update(gpu_temp_c=88.0, gpu_thermal_throttle=1)
    # R2: sustained high clipping. Clipped=1 from 91..103; clipping-rate
    # threshold is met after the first five samples and remains for 9 windows.
    if 91 <= step <= 103:
        row["gradient_clipping_applied"] = 1
    # Update-ratio high-bound excursion, edge-triggered once until recovery.
    if 96 <= step <= 101:
        row["update_weight_ratio"] = 2e-2
    return row


def run_injection(path):
    harness = AlarmMonitor(**MONITOR_KW)
    tail = JsonlTail(path)
    results = {
        "gpu_thermal": {"fault_step": 61, "expected_step": 63},
        "sustained_clipping": {"fault_step": 91, "expected_step": 96},
        "update_weight_ratio_bound": {"fault_step": 96, "expected_step": 96},
    }
    write_started = {}
    harness_alarms, jsonl_alarms = [], []
    with MetricsWriter(path, flush_every=FLUSH_EVERY) as writer:
        for step in range(STEPS):
            metrics = metrics_at(step)
            t0 = time.perf_counter()
            fired = harness.step(step, **metrics)
            elapsed = (time.perf_counter() - t0) * 1e3
            for alarm in fired:
                harness_alarms.append(alarm)
                entry = results.get(alarm["rule"])
                if entry and "alert_step" not in entry:
                    entry.update(alert_step=step, severity=alarm["severity"], in_harness_ms=elapsed)
            write_started[step] = time.perf_counter()
            writer.write(step, **metrics)
            for alarm in tail.poll():
                jsonl_alarms.append(alarm)
                entry = results.get(alarm["rule"])
                if entry and "jsonl_alert_step" not in entry:
                    entry.update(jsonl_alert_step=step,
                                 jsonl_flush_to_alert_ms=(time.perf_counter()-write_started[alarm["step"]])*1e3)
    for alarm in tail.poll():
        jsonl_alarms.append(alarm)
    for key, entry in results.items():
        entry["delta_steps"] = entry.get("alert_step", -1) - entry["fault_step"]
        entry["jsonl_delta_steps"] = entry.get("jsonl_alert_step", -1) - entry["fault_step"]
    return results, harness_alarms, jsonl_alarms


def test_r1_thermal_alert_fires_after_three_consecutive_hot_throttled_steps(tmp_path):
    results, harness, jsonl = run_injection(tmp_path / "thermal.jsonl")
    r = results["gpu_thermal"]
    assert r["alert_step"] == 63 and r["severity"] == SEVERITY
    assert r["delta_steps"] == 2
    assert r["jsonl_alert_step"] == 70 and r["jsonl_delta_steps"] == 9
    assert [a["rule"] for a in harness] == ["gpu_thermal", "sustained_clipping", "update_weight_ratio_bound"]
    assert [a["rule"] for a in jsonl] == ["gpu_thermal", "sustained_clipping", "update_weight_ratio_bound"]


def test_r1_requires_throttle_and_resets_on_cool_or_gap():
    monitor = AlarmMonitor(**MONITOR_KW)
    assert monitor.step(0, gpu_temp_c=90.0, gpu_thermal_throttle=0) == []
    assert monitor.step(1, gpu_temp_c=90.0, gpu_thermal_throttle=1) == []
    assert monitor.step(2, gpu_temp_c=70.0, gpu_thermal_throttle=0) == []
    assert monitor.step(3, gpu_temp_c=90.0, gpu_thermal_throttle=1) == []
    assert monitor.step(5, gpu_temp_c=90.0, gpu_thermal_throttle=1) == []


def test_r2_sustained_clipping_uses_rolling_window_and_persistence(tmp_path):
    results, harness, _ = run_injection(tmp_path / "clipping.jsonl")
    r = results["sustained_clipping"]
    assert r["alert_step"] == 96 and r["severity"] == SEVERITY
    assert r["delta_steps"] == 5
    assert sum(a["rule"] == "sustained_clipping" for a in harness) == 1


def test_update_ratio_bound_is_edge_triggered_and_rearms_after_recovery():
    monitor = AlarmMonitor(**MONITOR_KW)
    assert monitor.step(0, update_weight_ratio=5e-4) == []
    first = monitor.step(1, update_weight_ratio=2e-2)
    assert len(first) == 1 and first[0]["rule"] == "update_weight_ratio_bound"
    assert monitor.step(2, update_weight_ratio=3e-2) == []
    assert monitor.step(3, update_weight_ratio=5e-4) == []
    again = monitor.step(4, update_weight_ratio=2e-2)
    assert len(again) == 1 and again[0]["rule"] == "update_weight_ratio_bound"


def test_no_false_alarms_on_clean_telemetry_and_invalid_rows_reset():
    monitor = AlarmMonitor(**MONITOR_KW)
    for step in range(20):
        assert monitor.step(step, gpu_temp_c=68.0, gpu_thermal_throttle=0,
                            gradient_clipping_applied=0, update_weight_ratio=5e-4) == []
    # Two high clipped observations separated by a missing metric do not make a contiguous streak.
    assert monitor.step(20, gradient_clipping_applied=1) == []
    assert monitor.step(21, update_weight_ratio=5e-4) == []
    assert monitor.step(22, gradient_clipping_applied=1) == []


def test_checkpoint_restores_telemetry_streaks_and_history():
    uninterrupted = AlarmMonitor(**MONITOR_KW)
    for step in range(61, 63):
        assert uninterrupted.step(step, gpu_temp_c=88.0, gpu_thermal_throttle=1,
                                  gradient_clipping_applied=1) == []
    state = json.loads(json.dumps(uninterrupted.state_dict()))
    restored = AlarmMonitor(**MONITOR_KW)
    restored.load_state_dict(state)
    expected = uninterrupted.step(63, gpu_temp_c=88.0, gpu_thermal_throttle=1,
                                  gradient_clipping_applied=1)
    actual = restored.step(63, gpu_temp_c=88.0, gpu_thermal_throttle=1,
                           gradient_clipping_applied=1)
    assert actual == expected
    assert restored.state_dict() == uninterrupted.state_dict()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        results, harness, jsonl = run_injection(Path(tmp) / "metrics.jsonl")
    print("| rotator | rule | fault_step | alert_step (jsonl) | delta_steps (jsonl) | in_harness_ms | jsonl_flush_to_alert_ms | verdict |")
    print("|---|---|---:|---:|---:|---:|---:|---|")
    for rule, row in results.items():
        ok = row.get("alert_step") == row["expected_step"] and row.get("jsonl_alert_step") == ((row["expected_step"] // FLUSH_EVERY + 1) * FLUSH_EVERY)
        print(f"| @murthyap63-a11y | `{rule}` ({row.get('severity', SEVERITY)}) | {row['fault_step']} | {row.get('alert_step')} ({row.get('jsonl_alert_step')}) | {row['delta_steps']} ({row['jsonl_delta_steps']}) | {row.get('in_harness_ms', 0):.3f} | {row.get('jsonl_flush_to_alert_ms', 0):.3f} | {'PASS' if ok else 'FAIL'} |")
