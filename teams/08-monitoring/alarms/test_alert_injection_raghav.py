"""Week 3 G8 rotation (Issue #19): fault-injection test for two alarms, with time to alert.

A 150-step synthetic training stream is written through MetricsWriter (metrics.jsonl) and checked
by AlarmMonitor in two ways:

  in-harness  the trainer calls AlarmMonitor.step() on the same values it writes. Time to alert is
              t1 - t0 around step() on the faulty step (delta_steps = 0 by design).
  jsonl       a second AlarmMonitor reads metrics.jsonl the way `alarms.py --jsonl` does (one JSON row
              per line, `step` popped, the rest passed to step()). Time to alert runs from
              MetricsWriter.write() on the faulty step until that monitor fires for it.

Two faults are injected into loss_ntp:
  - spike_score (severity "page"): a value far above the trailing mean at step 125. 125 clean steps come
    first, so the 100-step window is warm. Step 125 is not a multiple of flush_every (10), so in the
    jsonl path the row waits in the buffer until the step-130 flush.
  - non_finite (severity "stop"): NaN at step 140. MetricsWriter stores it as "nan" and flushes that row
    at once, so the jsonl path sees it on the same step.

Run the test:   python -m pytest teams/08-monitoring/alarms/test_alert_injection_raghav.py -q
Print the rows: python teams/08-monitoring/alarms/test_alert_injection_raghav.py
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

STEPS = 150
SPIKE_STEP = 125
NAN_STEP = 140
SEED = 19


def clean_loss(step, rng):
    """Smooth decaying loss with small noise, like an early training curve."""
    return 2.2 + 1.5 * math.exp(-step / 60.0) + rng.gauss(0.0, 0.01)


def faulty_loss(step, base):
    if step == SPIKE_STEP:
        return base + 5.0          # hundreds of sigma above a 0.01-noise trailing window
    if step == NAN_STEP:
        return float("nan")
    return base


class JsonlTail:
    """Read complete new lines from metrics.jsonl and run them through AlarmMonitor like `alarms.py --jsonl`."""

    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.monitor = AlarmMonitor()

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
            fired.extend(self.monitor.step(step, **row))
        return fired


def run_injection(jsonl_path, steps=STEPS, seed=SEED):
    """Run the stream; return one result dict per injected rule."""
    rng = random.Random(seed)
    harness = AlarmMonitor()
    tail = JsonlTail(jsonl_path)
    faults = {SPIKE_STEP: "spike_score", NAN_STEP: "non_finite"}
    res = {rule: {"rule": rule, "fault_step": s} for s, rule in faults.items()}
    write_t0 = {}
    harness_alarms, jsonl_alarms = [], []

    with MetricsWriter(str(jsonl_path), flush_every=FLUSH_EVERY) as writer:
        for step in range(steps):
            loss = faulty_loss(step, clean_loss(step, rng))
            metrics = {"loss_ntp": loss, "lr": 3e-4}

            t0 = time.perf_counter()
            fired = harness.step(step, **metrics)
            t1 = time.perf_counter()
            for a in fired:
                harness_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and step == r["fault_step"] and "alert_step" not in r:
                    r.update(alert_step=step, severity=a["severity"], in_harness_ms=(t1 - t0) * 1e3)

            if step in faults:
                write_t0[step] = time.perf_counter()
            writer.write(step, **metrics)
            for a in tail.poll():
                jsonl_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and a["step"] == r["fault_step"] and "jsonl_alert_step" not in r:
                    r.update(jsonl_alert_step=step,
                             jsonl_flush_to_alert_ms=(time.perf_counter() - write_t0[a["step"]]) * 1e3)

    for a in tail.poll():                   # rows flushed by close()
        jsonl_alarms.append(a)
    for r in res.values():
        r["delta_steps"] = r["alert_step"] - r["fault_step"] if "alert_step" in r else None
        r["jsonl_delta_steps"] = (r["jsonl_alert_step"] - r["fault_step"]) if "jsonl_alert_step" in r else None
    return {"results": res, "harness_alarms": harness_alarms, "jsonl_alarms": jsonl_alarms}


def _run(tmp_dir):
    return run_injection(Path(tmp_dir) / "metrics.jsonl")


def test_both_faults_fire_expected_rule_and_severity(tmp_path):
    out = _run(tmp_path)
    r = out["results"]
    assert r["spike_score"]["alert_step"] == SPIKE_STEP
    assert r["spike_score"]["severity"] == "page"
    assert r["non_finite"]["alert_step"] == NAN_STEP
    assert r["non_finite"]["severity"] == "stop"
    assert r["spike_score"]["delta_steps"] == 0 and r["non_finite"]["delta_steps"] == 0


def test_no_false_alarms_on_clean_steps(tmp_path):
    out = _run(tmp_path)
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        assert {(a["step"], a["rule"]) for a in alarms} == {(SPIKE_STEP, "spike_score"), (NAN_STEP, "non_finite")}


def test_jsonl_path_and_flush_lag(tmp_path):
    out = _run(tmp_path)
    r = out["results"]
    # NaN row is flushed at once, so the file-reading monitor sees it on the same step.
    assert r["non_finite"]["jsonl_delta_steps"] == 0
    # The spike row is finite, so it waits for the next step % 10 == 0 flush.
    next_flush = (SPIKE_STEP // FLUSH_EVERY + 1) * FLUSH_EVERY
    assert r["spike_score"]["jsonl_alert_step"] == next_flush
    assert r["spike_score"]["jsonl_delta_steps"] == next_flush - SPIKE_STEP


def test_timings_non_negative(tmp_path):
    out = _run(tmp_path)
    for r in out["results"].values():
        assert r["in_harness_ms"] >= 0
        assert r["jsonl_flush_to_alert_ms"] >= 0


def test_nan_stored_as_string_in_jsonl(tmp_path):
    path = Path(tmp_path) / "metrics.jsonl"
    run_injection(path)
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == STEPS
    assert next(r for r in rows if r["step"] == NAN_STEP)["loss_ntp"] == "nan"


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        out = _run(d)
    print("| rotator | rule_1 & rule_2 | injection_mode | fault_step | alert_step | delta_steps | in_harness_ms | jsonl_flush_to_alert_ms | verdict |")
    print("|---|---|---|---|---|---|---|---|---|")
    for rule in ("non_finite", "spike_score"):
        r = out["results"][rule]
        ok = r.get("alert_step") == r["fault_step"]
        print(f"| @raghavTayal | `{rule}` ({r['severity']}) | synthetic 150-step stream, MetricsWriter + AlarmMonitor | "
              f"{r['fault_step']} | {r['alert_step']} (jsonl: {r['jsonl_alert_step']}) | {r['delta_steps']} "
              f"(jsonl: {r['jsonl_delta_steps']}) | {r['in_harness_ms']:.3f} | {r['jsonl_flush_to_alert_ms']:.3f} | "
              f"{'PASS' if ok else 'FAIL'} |")
