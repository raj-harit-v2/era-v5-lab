"""Week 3 G8 rotation (Issue #25): fault-injection test for a validation regression and for a loss spike right after a
checkpoint restore, with time to alert.

A 300-step synthetic training stream is written through MetricsWriter (metrics.jsonl) and checked by AlarmMonitor in
two ways, as in test_alert_injection_raghav.py and test_alert_injection_swatibansal.py:

  in-harness  the trainer calls AlarmMonitor.step() on the same values it writes. Time to alert is t1 - t0 around
              step() on the alert step.
  jsonl       a second AlarmMonitor reads metrics.jsonl the way `alarms.py --jsonl` does. Time to alert runs from
              MetricsWriter.write() of the alert step's row until that monitor fires for it.

The stream: loss_ntp about 2.0 (noise 0.01) every step; every 25 steps a validation run writes validation_bpb (falling
from 1.8 to about 1.25) and validation_loss (2.5 x validation_bpb), as G5's evaluate() gives them through the writer.
Both monitors use AlarmMonitor(val_regression_frac=0.02): val_regression is off unless the fraction is set.

Two faults:
  - val_regression (severity "warn"): the validation run at step 275 is 5% worse than the best so far, on both
    validation metrics. It fires at 275 for each metric. 275 is not a multiple of flush_every (10), so the jsonl
    path sees it at the step-280 flush.
  - spike_score after a checkpoint restore (severity "page"): the trainer checkpoints at step 200, with
    AlarmMonitor.state_dict() saved as JSON next to the model. The process dies at step 207, so the writer's
    unflushed rows 201-207 never reach metrics.jsonl. The run resumes from step 200 with a new AlarmMonitor
    restored by load_state_dict(), and the first resumed step, 201, has loss_ntp + 0.5 (a bad restore: say, the
    optimizer state or the data position was not restored). It fires at 201 in-harness; the jsonl monitor keeps
    running across the restart and sees it at the step-210 flush.

Four extra tests record findings (see docs/alert_tests.md): a monitor that is not restored misses the spike after
the restart; it also misses a regression that is already there at the first validation after the restart; a
fixed static_bound on validation_bpb misses the regression; and a checkpoint written before val_regression existed
still loads.

Run the test:   python -m pytest teams/08-monitoring/alarms/test_alert_injection_sohamniyogi.py -q
Print the rows: python teams/08-monitoring/alarms/test_alert_injection_sohamniyogi.py
"""
import json
import math
import random
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "metrics_logger"))
from alarms import AlarmMonitor  # noqa: E402
from metrics_writer import FLUSH_EVERY, MetricsWriter  # noqa: E402

STEPS = 300
SEED = 25
EVAL_EVERY = 25
VAL_FAULT = 275                           # this validation run is VAL_WORSE above the best so far
VAL_WORSE = 0.05
VAL_FRAC = 0.02                           # val_regression tolerance used by both monitors
CKPT_STEP = 200                           # checkpoint: model + AlarmMonitor.state_dict()
CRASH_STEP = 207                          # the process dies after writing this step; rows 201-207 are lost
SPIKE_STEP = CKPT_STEP + 1                # first step after the resume
SPIKE = 0.5
MONITOR_KW = dict(val_regression_frac=VAL_FRAC)


def train_metrics(step, rng, spike_at=None):
    loss = 2.0 + rng.gauss(0.0, 0.01)
    if step == spike_at:
        loss += SPIKE
    return {"loss_ntp": loss, "lr": 3e-4}


def val_metrics(step, rng, worse_at=(VAL_FAULT,)):
    """validation_bpb falling from 1.8 towards 1.2 (noise 0.002); VAL_WORSE above the best on the `worse_at` runs."""
    bpb = 1.2 + 0.6 * math.exp(-step / 100.0) + rng.gauss(0.0, 0.002)
    if step in worse_at:
        bpb = (1.2 + 0.6 * math.exp(-(step - EVAL_EVERY) / 100.0)) * (1.0 + VAL_WORSE)
    return {"validation_bpb": bpb, "validation_loss": 2.5 * bpb}


def stream(steps=STEPS, seed=SEED, spike_at=SPIKE_STEP, worse_at=(VAL_FAULT,)):
    """{step: metrics}. The values do not depend on whether a step is run once or again after the resume."""
    rng = random.Random(seed)
    rows = {}
    for step in range(steps):
        m = train_metrics(step, rng, spike_at)
        if step % EVAL_EVERY == 0:
            m.update(val_metrics(step, rng, worse_at))
        rows[step] = m
    return rows


class JsonlTail:
    """Read complete new lines from metrics.jsonl and run them through AlarmMonitor like `alarms.py --jsonl`."""

    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.monitor = AlarmMonitor(**MONITOR_KW)

    def poll(self):
        if not self.path.exists():
            return []
        with open(self.path, "rb") as f:    # binary: the offset is a byte position
            f.seek(self.offset)
            data = f.read()
        end = data.rfind(b"\n") + 1         # only whole lines; a partial line waits for the next poll
        self.offset += end
        fired = []
        for line in data[:end].decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            step = row.pop("step")
            row.pop("time", None)
            fired.extend(self.monitor.step(step, **row))
        return fired


def run_injection(jsonl_path, rows=None, restore=True):
    """Run until CRASH_STEP, lose the writer's buffer, resume from CKPT_STEP with a (restored or new) monitor.

    The spike comes from the bad restore, so only the resumed run has it; the first run sees step 201 without it.
    """
    rows = stream() if rows is None else rows
    first_rows = {s: m if s != SPIKE_STEP else {**m, "loss_ntp": m["loss_ntp"] - SPIKE} for s, m in rows.items()}
    faults = {"val_regression": (VAL_FAULT, VAL_FAULT), "spike_score": (SPIKE_STEP, SPIKE_STEP)}
    res = {rule: {"rule": rule, "fault_step": f, "expected_alert_step": a} for rule, (f, a) in faults.items()}
    tail = JsonlTail(jsonl_path)
    write_t = {}
    harness_alarms, jsonl_alarms = [], []

    def run(monitor, writer, steps, rows):
        checkpoint = None
        for step in steps:
            t0 = time.perf_counter()
            fired = monitor.step(step, **rows[step])
            t1 = time.perf_counter()
            for a in fired:
                harness_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and step == r["expected_alert_step"] and "alert_step" not in r:
                    r.update(alert_step=step, severity=a["severity"], in_harness_ms=(t1 - t0) * 1e3)
            write_t[step] = time.perf_counter()
            writer.write(step, **rows[step])
            for a in tail.poll():
                jsonl_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and a["step"] == r["expected_alert_step"] and "jsonl_alert_step" not in r:
                    r.update(jsonl_alert_step=step,
                             jsonl_flush_to_alert_ms=(time.perf_counter() - write_t[a["step"]]) * 1e3)
            if step == CKPT_STEP:
                checkpoint = json.dumps(monitor.state_dict())   # saved with the model checkpoint
        return checkpoint

    # First process: steps 0..CRASH_STEP. It dies without close(), so rows after the step-200 flush are never written.
    writer = MetricsWriter(str(jsonl_path), flush_every=FLUSH_EVERY)
    checkpoint = run(AlarmMonitor(**MONITOR_KW), writer, range(CRASH_STEP + 1), first_rows)
    writer._file.close()                    # the file handle goes with the process; the buffer is lost
    lost = {r["step"] for r in map(json.loads, Path(jsonl_path).read_text().splitlines())}

    # Second process: resume from the checkpoint and run CKPT_STEP + 1 .. STEPS - 1 again.
    monitor = AlarmMonitor(**MONITOR_KW)
    if restore:
        monitor.load_state_dict(json.loads(checkpoint))
    with MetricsWriter(str(jsonl_path), flush_every=FLUSH_EVERY) as writer:
        run(monitor, writer, range(CKPT_STEP + 1, STEPS), rows)
    for a in tail.poll():
        jsonl_alarms.append(a)
    for r in res.values():
        r["delta_steps"] = r["alert_step"] - r["fault_step"] if "alert_step" in r else None
        r["jsonl_delta_steps"] = (r["jsonl_alert_step"] - r["fault_step"]) if "jsonl_alert_step" in r else None
    return {"results": res, "harness_alarms": harness_alarms, "jsonl_alarms": jsonl_alarms,
            "rows_in_file_before_resume": max(lost)}


def _run(tmp_dir, **kw):
    return run_injection(Path(tmp_dir) / "metrics.jsonl", **kw)


WANT = {(VAL_FAULT, "val_regression", "validation_bpb"), (VAL_FAULT, "val_regression", "validation_loss"),
        (SPIKE_STEP, "spike_score", "loss_ntp")}


def test_both_faults_fire_expected_rule_and_severity(tmp_path):
    r = _run(tmp_path)["results"]
    assert r["val_regression"]["alert_step"] == VAL_FAULT and r["val_regression"]["severity"] == "warn"
    assert r["spike_score"]["alert_step"] == SPIKE_STEP and r["spike_score"]["severity"] == "page"
    assert r["val_regression"]["delta_steps"] == 0 and r["spike_score"]["delta_steps"] == 0


def test_no_false_alarms_on_clean_steps(tmp_path):
    out = _run(tmp_path)
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        assert {(a["step"], a["rule"], a["metric"]) for a in alarms} == WANT
        assert len(alarms) == len(WANT)     # one per metric; the steps before the crash fire nothing


def test_crash_loses_unflushed_rows_and_jsonl_lag(tmp_path):
    out = _run(tmp_path)
    assert out["rows_in_file_before_resume"] == CKPT_STEP      # 201-207 were in the writer's buffer
    r = out["results"]
    assert r["spike_score"]["jsonl_alert_step"] == 210 and r["spike_score"]["jsonl_delta_steps"] == 9
    assert r["val_regression"]["jsonl_alert_step"] == 280 and r["val_regression"]["jsonl_delta_steps"] == 5


def test_alarm_detail_and_timings(tmp_path):
    out = _run(tmp_path)
    val = [a for a in out["harness_alarms"] if a["rule"] == "val_regression"]
    assert all(a["value"] / a["best"] - 1 > VAL_FRAC for a in val)
    for r in out["results"].values():
        assert r["in_harness_ms"] >= 0 and r["jsonl_flush_to_alert_ms"] >= 0


def test_finding_monitor_not_restored_misses_spike_after_restart(tmp_path):
    """A new AlarmMonitor has an empty window; spike_score needs min_window (100) clean steps, so step 201 is missed."""
    out = _run(tmp_path, restore=False)
    assert "spike_score" not in {a["rule"] for a in out["harness_alarms"]}
    assert "spike_score" in {a["rule"] for a in out["jsonl_alarms"]}   # the file monitor kept its window


def test_finding_monitor_not_restored_misses_regression_at_first_validation(tmp_path):
    """Regression already there at the first validation after the restart (step 225): the new monitor takes it as best."""
    rows = stream(worse_at=(CKPT_STEP + EVAL_EVERY,))
    restored = _run(tmp_path / "a", rows=rows)["harness_alarms"]
    fresh = _run(tmp_path / "b", rows=rows, restore=False)["harness_alarms"]
    assert {(a["step"], a["rule"]) for a in restored if a["rule"] == "val_regression"} == {(225, "val_regression")}
    assert "val_regression" not in {a["rule"] for a in fresh}


def test_finding_static_bound_misses_regression():
    """A fixed ceiling set at the start, just above the first validation value (1.8), never sees a 5% rise late in the run."""
    monitor = AlarmMonitor(bounds={"validation_bpb": (None, 1.85)})
    fired = []
    for step, m in stream().items():
        fired += monitor.step(step, **m)
    assert [a for a in fired if a["rule"] == "static_bound"] == []


def test_finding_old_checkpoint_without_val_state_loads():
    """A state_dict from before val_regression (no "val" key) loads; the validation best starts empty."""
    old = AlarmMonitor().state_dict()
    old.pop("val")
    monitor = AlarmMonitor(**MONITOR_KW)
    monitor.load_state_dict(old)
    assert monitor.state_dict()["val"] == {"best": {}, "streak": {}}


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        out = _run(d)
    print("| rotator | rule_1 & rule_2 | injection_mode | fault_step | alert_step | delta_steps | in_harness_ms | jsonl_flush_to_alert_ms | verdict |")
    print("|---|---|---|---|---|---|---|---|---|")
    got = {(a["step"], a["rule"], a["metric"]) for a in out["harness_alarms"]}
    for rule, mode in (("val_regression", f"val_regression_frac={VAL_FRAC}, validation every {EVAL_EVERY} steps"),
                       ("spike_score", f"checkpoint at {CKPT_STEP}, crash at {CRASH_STEP}, resume with load_state_dict()")):
        r = out["results"][rule]
        ok = r.get("alert_step") == r["expected_alert_step"] and got == WANT
        print(f"| @sohamniyogi | `{rule}` ({r['severity']}) | synthetic 300-step stream, MetricsWriter + AlarmMonitor, {mode} | "
              f"{r['fault_step']} | {r['alert_step']} (jsonl: {r['jsonl_alert_step']}) | {r['delta_steps']} "
              f"(jsonl: {r['jsonl_delta_steps']}) | {r['in_harness_ms']:.3f} | {r['jsonl_flush_to_alert_ms']:.3f} | "
              f"{'PASS' if ok else 'FAIL'} |")
