"""Week 3 G8 rotation (Issue #24): fault-injection test for `step_continuity` and `loader_stall`, with time to alert.

The two rules are new (`continuity_rules.py`). A 200-step synthetic training stream is written through MetricsWriter
(metrics.jsonl) and checked in two ways, as in test_alert_injection_raghav.py and test_alert_injection_s9k96.py:

  in-harness  the trainer calls ContinuityMonitor.step() on the same values it writes. Time to alert is
              t1 - t0 around step() on the alert step.
  jsonl       a second ContinuityMonitor reads metrics.jsonl the way `alarms.py --jsonl` does. Time to alert
              runs from MetricsWriter.write() of the alert step's row until that monitor fires for it.

Two faults:
  - loader_stall (severity "warn"): loader_wait_time (about 0.05 s) goes to 2.0 s from step 120 to step 159.
    The rule needs `patience` (20) slow steps in a row above 1.0 s, so it fires at step 139 = fault_step + 19.
    139 is not a multiple of flush_every (10), so the jsonl path sees it at the step-140 flush.
  - step_continuity (severity "page"): the row for step 185 is never written. The rule sees the gap when
    step 186 arrives, so it fires at 186. The jsonl path sees it at the step-190 flush.

Three extra tests record a finding about restores (see rotation_pratik-2025.md). The trainer is killed after
step 137; the last flush of metrics.jsonl was at step 130 and the rows for 131 to 137 were still in memory.
  - Checkpoint at step 125 (before the last flush): the restarted trainer writes 126 to 130 again. One
    "repeated" warn, nothing missing.
  - Checkpoint at step 135 (after the last flush): the restarted trainer starts at 136, so the rows for 131 to
    135 are never written. The rule pages "missing".
  - The same case with a flush of metrics.jsonl at the checkpoint save: nothing missing.

Run the test:   python -m pytest teams/08-monitoring/alarms/test_alert_injection_pratik.py -q
Print the rows: python teams/08-monitoring/alarms/test_alert_injection_pratik.py
"""
import json
import random
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "metrics_logger"))
from continuity_rules import ContinuityMonitor  # noqa: E402
from metrics_writer import FLUSH_EVERY, MetricsWriter  # noqa: E402

STEPS = 200
SEED = 24
THRESHOLD_S = 1.0
PATIENCE = 20
STALL_START, STALL_END = 120, 159      # loader_wait_time = 2.0 s on these steps
STALL_ALERT = STALL_START + PATIENCE - 1   # 139
MISSING_STEP = 185                     # this row is never written
MISSING_ALERT = MISSING_STEP + 1       # 186
MONITOR_KW = dict(loader_threshold_s=THRESHOLD_S, loader_patience=PATIENCE)


def metrics_for(step, rng):
    wait = 2.0 if STALL_START <= step <= STALL_END else max(0.0, 0.05 + rng.gauss(0.0, 0.01))
    return {"loss_ntp": 2.0 + rng.gauss(0.0, 0.01), "lr": 3e-4, "loader_wait_time": wait}


class JsonlTail:
    """Read complete new lines from metrics.jsonl and run them through ContinuityMonitor like `alarms.py --jsonl`."""

    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.monitor = ContinuityMonitor(**MONITOR_KW)

    def poll(self):
        if not self.path.exists():
            return []
        with open(self.path, "rb") as f:
            f.seek(self.offset)
            data = f.read()
        end = data.rfind(b"\n") + 1
        self.offset += end
        fired = []
        for line in data[:end].decode("utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                fired.extend(self.monitor.step(row.pop("step"), **row))
        return fired


def run_injection(jsonl_path, steps=STEPS, seed=SEED):
    rng = random.Random(seed)
    harness = ContinuityMonitor(**MONITOR_KW)
    tail = JsonlTail(jsonl_path)
    faults = {"loader_stall": (STALL_START, STALL_ALERT), "step_continuity": (MISSING_STEP, MISSING_ALERT)}
    res = {rule: {"rule": rule, "fault_step": f, "expected_alert_step": a} for rule, (f, a) in faults.items()}
    write_t, harness_alarms, jsonl_alarms = {}, [], []

    with MetricsWriter(str(jsonl_path), flush_every=FLUSH_EVERY) as writer:
        for step in range(steps):
            metrics = metrics_for(step, rng)
            if step == MISSING_STEP:
                continue                     # the fault: this row is lost
            t0 = time.perf_counter()
            fired = harness.step(step, **metrics)
            t1 = time.perf_counter()
            for a in fired:
                harness_alarms.append(a)
                r = res[a["rule"]]
                if step == r["expected_alert_step"] and "alert_step" not in r:
                    r.update(alert_step=step, severity=a["severity"], in_harness_ms=(t1 - t0) * 1e3)
            write_t[step] = time.perf_counter()
            writer.write(step, **metrics)
            for a in tail.poll():
                jsonl_alarms.append(a)
                r = res[a["rule"]]
                if a["step"] == r["expected_alert_step"] and "jsonl_alert_step" not in r:
                    r.update(jsonl_alert_step=step,
                             jsonl_flush_to_alert_ms=(time.perf_counter() - write_t[a["step"]]) * 1e3)
    jsonl_alarms += tail.poll()
    for r in res.values():
        r["delta_steps"] = r["alert_step"] - r["fault_step"] if "alert_step" in r else None
        r["jsonl_delta_steps"] = r["jsonl_alert_step"] - r["fault_step"] if "jsonl_alert_step" in r else None
    return {"results": res, "harness_alarms": harness_alarms, "jsonl_alarms": jsonl_alarms}


def _run(tmp_dir):
    return run_injection(Path(tmp_dir) / "metrics.jsonl")


def test_both_faults_fire_expected_rule_and_severity(tmp_path):
    r = _run(tmp_path)["results"]
    assert r["loader_stall"]["alert_step"] == STALL_ALERT and r["loader_stall"]["severity"] == "warn"
    assert r["loader_stall"]["delta_steps"] == PATIENCE - 1
    assert r["step_continuity"]["alert_step"] == MISSING_ALERT and r["step_continuity"]["severity"] == "page"
    assert r["step_continuity"]["delta_steps"] == 1


def test_missing_alarm_names_the_lost_step(tmp_path):
    out = _run(tmp_path)
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        miss = [a for a in alarms if a["rule"] == "step_continuity"]
        assert len(miss) == 1
        assert (miss[0]["kind"], miss[0]["missing_from"], miss[0]["missing_to"]) == ("missing", MISSING_STEP, MISSING_STEP)


def test_no_false_alarms_on_clean_steps(tmp_path):
    out = _run(tmp_path)
    want = {(STALL_ALERT, "loader_stall"), (MISSING_ALERT, "step_continuity")}
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        assert {(a["step"], a["rule"]) for a in alarms} == want
        assert len(alarms) == len(want)       # the stall fires once for the whole 40-step stall


def test_jsonl_path_and_flush_lag(tmp_path):
    r = _run(tmp_path)["results"]
    for rule in ("loader_stall", "step_continuity"):
        alert = r[rule]["alert_step"]
        next_flush = (alert // FLUSH_EVERY + 1) * FLUSH_EVERY
        assert r[rule]["jsonl_alert_step"] == next_flush
        assert r[rule]["jsonl_delta_steps"] == next_flush - r[rule]["fault_step"]


def test_timings_non_negative(tmp_path):
    for r in _run(tmp_path)["results"].values():
        assert r["in_harness_ms"] >= 0
        assert r["jsonl_flush_to_alert_ms"] >= 0


def test_short_stall_does_not_alert():
    m = ContinuityMonitor(**MONITOR_KW)
    fired = []
    for step in range(100):
        fired += m.step(step, loader_wait_time=2.0 if 40 <= step < 40 + PATIENCE - 1 else 0.05)
    assert fired == []


# --- Finding: a restore can lose metric rows -------------------------------------------------------------------

KILL_AFTER = 137                       # last step the killed trainer finished; last flush was at 130


def run_restore(jsonl_path, ckpt_step, flush_at_checkpoint=False):
    """Trainer A runs to KILL_AFTER and is killed (rows still in memory are lost). Trainer B restarts after
    `ckpt_step` and runs to the end. A watcher reads the whole file afterwards, as the dashboard loader would."""
    rng = random.Random(SEED)
    a = MetricsWriter(str(jsonl_path))
    for step in range(KILL_AFTER + 1):
        a.write(step, **metrics_for(step, rng))
        if flush_at_checkpoint and step == ckpt_step:
            a.flush()                    # the proposed fix: flush metrics.jsonl when a checkpoint is saved
    a._buffer.clear()                    # SIGKILL: no close(), the buffered rows never reach the file
    a._file.close()
    a._file = None
    with MetricsWriter(str(jsonl_path)) as b:      # append mode, as the restarted trainer opens it
        for step in range(ckpt_step + 1, STEPS):
            b.write(step, **metrics_for(step, rng))
    rows = [json.loads(line) for line in Path(jsonl_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    watcher = ContinuityMonitor(**MONITOR_KW)
    events = []
    for row in rows:
        events += [e for e in watcher.step(row.pop("step"), **row) if e["rule"] == "step_continuity"]
    return {"steps": [json.loads(l)["step"] for l in Path(jsonl_path).read_text(encoding="utf-8").splitlines()],
            "events": events}


def test_restore_from_checkpoint_before_last_flush_repeats_rows(tmp_path):
    out = run_restore(Path(tmp_path) / "metrics.jsonl", ckpt_step=125)
    assert [(e["kind"], e["step"]) for e in out["events"]] == [("repeated", 126)]
    assert set(out["steps"]) == set(range(STEPS))                   # every step is in the file
    assert len(out["steps"]) - len(set(out["steps"])) == 5            # 126 to 130 twice


def test_restore_from_checkpoint_after_last_flush_loses_rows(tmp_path):
    out = run_restore(Path(tmp_path) / "metrics.jsonl", ckpt_step=135)
    assert len(out["events"]) == 1
    e = out["events"][0]
    assert (e["kind"], e["severity"], e["missing_from"], e["missing_to"]) == ("missing", "page", 131, 135)
    assert set(range(131, 136)).isdisjoint(out["steps"])            # never written, by either trainer


def test_flush_at_checkpoint_keeps_every_row(tmp_path):
    out = run_restore(Path(tmp_path) / "metrics.jsonl", ckpt_step=135, flush_at_checkpoint=True)
    assert out["events"] == []
    assert set(out["steps"]) == set(range(STEPS))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        out = _run(d)
    want = {(STALL_ALERT, "loader_stall"), (MISSING_ALERT, "step_continuity")}
    clean = all({(a["step"], a["rule"]) for a in al} == want for al in (out["harness_alarms"], out["jsonl_alarms"]))
    print("| rotator | rule_1 & rule_2 | injection_mode | fault_step | alert_step | delta_steps | in_harness_ms | jsonl_flush_to_alert_ms | verdict |")
    print("|---|---|---|---|---|---|---|---|---|")
    for rule in ("step_continuity", "loader_stall"):
        r = out["results"][rule]
        ok = clean and r.get("alert_step") == r["expected_alert_step"]
        print(f"| @pratik-2025 | `{rule}` ({r['severity']}) | synthetic {STEPS}-step stream, `MetricsWriter` + "
              f"`ContinuityMonitor` | {r['fault_step']} | {r['alert_step']} (jsonl: {r['jsonl_alert_step']}) | "
              f"{r['delta_steps']} (jsonl: {r['jsonl_delta_steps']}) | {r['in_harness_ms']:.3f} | "
              f"{r['jsonl_flush_to_alert_ms']:.3f} | {'PASS' if ok else 'FAIL'} |")
