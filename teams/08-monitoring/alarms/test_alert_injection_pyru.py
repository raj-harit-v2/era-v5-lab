"""Week 3 G8 rotation (@pyru): fault-injection test for static_bound and throughput_drop, with time to alert.

A 400-step synthetic training stream is written through MetricsWriter (metrics.jsonl) and checked by
AlarmMonitor in two ways, as in test_alert_injection_raghav.py:

  in-harness  the trainer calls AlarmMonitor.step() on the same values it writes. in_harness_ms is
              t1 - t0 around step() on the step where the alarm fires.
  jsonl       a second AlarmMonitor reads each newly flushed line of metrics.jsonl (`step` popped, the
              rest passed to step()). jsonl_flush_to_alert_ms runs from MetricsWriter.write() of the row
              that triggers the alarm until that monitor fires for it.

Both monitors get bounds={"gpu_alloc_gib": (None, 40.0)} (the bound used in tests/test_alarms.py). Without
bounds, static_bound is off: AlarmMonitor() and `alarms.py --jsonl` set none.

Two faults are injected:
  - static_bound (severity "warn"): gpu_alloc_gib jumps from about 24.5 to about 44 GiB on steps 125-144,
    one crossing of the 40 GiB upper bound. It should fire once, on step 125, and not again while memory
    stays high.
    Step 125 is not a multiple of flush_every (10), so in the jsonl path the row waits for the
    step-130 flush.
  - throughput_drop (severity "warn"): tokens_per_second 25% below normal for steps 200-349. The rule
    waits for 100 slow steps in a row, so it should fire once, on step 299 (delta_steps = 99 by design).
    Its row is flushed at step 300.
Step 0 has a slow setup value (650 tokens/s); the rule skips step 0, so it must not raise an alarm.

Run the test:   python -m pytest teams/08-monitoring/alarms/test_alert_injection_pyru.py -q
Print the rows: python teams/08-monitoring/alarms/test_alert_injection_pyru.py
"""
import json
import math
import random
import sys
import tempfile
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "metrics_logger"))
from alarms import AlarmMonitor  # noqa: E402
from metrics_writer import FLUSH_EVERY, MetricsWriter  # noqa: E402

STEPS = 400
SEED = 23
BOUND_METRIC = "gpu_alloc_gib"
BOUNDS = {BOUND_METRIC: (None, 40.0)}
MEM_HI = BOUNDS[BOUND_METRIC][1]
HIGH_START, HIGH_END = 125, 144        # gpu_alloc_gib above the bound on these steps (inclusive)
SLOW_START, SLOW_END = 200, 349        # tokens_per_second 25% below normal on these steps (inclusive)
SLOW_FACTOR = 0.75
TPS_PATIENCE = AlarmMonitor().tps_patience   # 100 by default

EXPECTED = {
    "static_bound": {"fault_step": HIGH_START, "alert_step": HIGH_START, "metric": BOUND_METRIC},
    "throughput_drop": {"fault_step": SLOW_START, "alert_step": SLOW_START + TPS_PATIENCE - 1,
                        "metric": "tokens_per_second"},
}


def next_flush(step, flush_every=FLUSH_EVERY):
    """Step at which MetricsWriter flushes a finite row written at `step`."""
    return step if step % flush_every == 0 else (step // flush_every + 1) * flush_every


def stream_row(step, rng):
    """One step's metrics: a decaying loss, normal speed and normal GPU memory, plus the two faults."""
    loss = 2.2 + 1.5 * math.exp(-step / 60.0) + rng.gauss(0.0, 0.01)
    tps = 650.0 if step == 0 else 38000.0 + rng.gauss(0.0, 400.0)   # step 0: slow setup, skipped by the rule
    mem = 24.5 + rng.gauss(0.0, 0.05)
    if HIGH_START <= step <= HIGH_END:
        mem = 44.0 + rng.gauss(0.0, 0.05)
    if SLOW_START <= step <= SLOW_END:
        tps *= SLOW_FACTOR
    return {"loss_ntp": loss, "lr": 3e-4, "tokens_per_second": tps, BOUND_METRIC: mem}


class JsonlTail:
    """Read whole new lines from metrics.jsonl and run them through an AlarmMonitor with the same bounds."""

    def __init__(self, path, bounds):
        self.path = Path(path)
        self.offset = 0
        self.monitor = AlarmMonitor(bounds=bounds)

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
            if line.strip():
                row = json.loads(line)
                step = row.pop("step")
                fired.extend(self.monitor.step(step, **row))
        return fired


def run_injection(jsonl_path, steps=STEPS, seed=SEED):
    """Run the stream; return one result dict per injected rule and every alarm from both paths."""
    rng = random.Random(seed)
    harness = AlarmMonitor(bounds=BOUNDS)
    tail = JsonlTail(jsonl_path, BOUNDS)
    res = {rule: {"rule": rule, "fault_step": e["fault_step"]} for rule, e in EXPECTED.items()}
    write_t0 = {}
    harness_alarms, jsonl_alarms = [], []

    with MetricsWriter(str(jsonl_path), flush_every=FLUSH_EVERY) as writer:
        for step in range(steps):
            metrics = stream_row(step, rng)

            t0 = time.perf_counter()
            fired = harness.step(step, **metrics)
            t1 = time.perf_counter()
            for a in fired:
                harness_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and "alert_step" not in r:
                    r.update(alert_step=step, severity=a["severity"], metric=a["metric"],
                             in_harness_ms=(t1 - t0) * 1e3)

            write_t0[step] = time.perf_counter()
            writer.write(step, **metrics)
            for a in tail.poll():
                jsonl_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and "jsonl_alert_step" not in r:
                    r.update(jsonl_alert_step=step, jsonl_row_step=a["step"],
                             jsonl_flush_to_alert_ms=(time.perf_counter() - write_t0[a["step"]]) * 1e3)

    jsonl_alarms.extend(tail.poll())        # rows flushed by close()
    for r in res.values():
        r["delta_steps"] = r["alert_step"] - r["fault_step"] if "alert_step" in r else None
        r["jsonl_delta_steps"] = r["jsonl_alert_step"] - r["fault_step"] if "jsonl_alert_step" in r else None
    return {"results": res, "harness_alarms": harness_alarms, "jsonl_alarms": jsonl_alarms}


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    return run_injection(tmp_path_factory.mktemp("pyru") / "metrics.jsonl")


def test_static_bound_fires_on_the_fault_step(out):
    r = out["results"]["static_bound"]
    assert r["alert_step"] == HIGH_START and r["delta_steps"] == 0
    assert r["severity"] == "warn" and r["metric"] == BOUND_METRIC
    alarm = next(a for a in out["harness_alarms"] if a["rule"] == "static_bound")
    assert alarm["value"] > MEM_HI and alarm["bound"] == MEM_HI


def test_throughput_drop_fires_after_100_slow_steps(out):
    r = out["results"]["throughput_drop"]
    assert r["alert_step"] == SLOW_START + TPS_PATIENCE - 1 and r["delta_steps"] == TPS_PATIENCE - 1
    assert r["severity"] == "warn" and r["metric"] == "tokens_per_second"


def test_each_fault_fires_once_and_nothing_else_fires(out):
    # 20 high-memory steps give one static_bound alarm (latched); 150 slow steps give one throughput_drop alarm;
    # the slow step-0 setup gives none.
    expected = {(e["alert_step"], rule) for rule, e in EXPECTED.items()}
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        got = [(a["step"], a["rule"]) for a in alarms]
        assert sorted(got) == sorted(expected)


def test_jsonl_path_sees_each_alarm_at_the_next_flush(out):
    for rule, e in EXPECTED.items():
        r = out["results"][rule]
        assert r["jsonl_row_step"] == e["alert_step"]
        assert r["jsonl_alert_step"] == next_flush(e["alert_step"])
    assert out["results"]["static_bound"]["jsonl_alert_step"] == 130
    assert out["results"]["throughput_drop"]["jsonl_alert_step"] == 300


def test_timings_non_negative(out):
    for r in out["results"].values():
        assert r["in_harness_ms"] >= 0 and r["jsonl_flush_to_alert_ms"] >= 0


def _feed_tps(monitor, slow_runs, normal=38000.0, factor=SLOW_FACTOR, gap=50):
    """Feed tokens_per_second: `gap` normal steps, then each run of slow steps followed by `gap` normal steps."""
    alarms, step = [], 1
    for n_slow in [0] + list(slow_runs):
        for _ in range(n_slow):
            alarms += monitor.step(step, tokens_per_second=normal * factor)
            step += 1
        for _ in range(gap):
            alarms += monitor.step(step, tokens_per_second=normal)
            step += 1
    return [a for a in alarms if a["rule"] == "throughput_drop"]


def test_throughput_drop_needs_100_slow_steps_in_a_row():
    assert _feed_tps(AlarmMonitor(), [TPS_PATIENCE - 1]) == []           # a 99-step dip: no alarm
    assert len(_feed_tps(AlarmMonitor(), [TPS_PATIENCE])) == 1           # a 100-step dip: one alarm
    assert _feed_tps(AlarmMonitor(), [300], factor=0.92) == []           # an 8% drop is below the 10% rule


def test_static_bound_rearms_after_the_metric_comes_back():
    mon = AlarmMonitor(bounds=BOUNDS)
    mems = [24.5] * 5 + [44.0] * 5 + [24.5] * 5 + [45.0] * 5
    fired = [a["step"] for s, m in enumerate(mems) for a in mon.step(s, gpu_alloc_gib=m)]
    assert fired == [5, 15]                                              # one alarm per crossing


def test_static_bound_is_off_without_bounds():
    # AlarmMonitor() as in the README example and `alarms.py --jsonl` has no bounds, so no static_bound alarm.
    mon = AlarmMonitor()
    fired = [a for s in range(20) for a in mon.step(s, gpu_alloc_gib=50.0)]
    assert fired == []


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        result = run_injection(Path(d) / "metrics.jsonl")
    expected = {(e["alert_step"], rule) for rule, e in EXPECTED.items()}
    clean = all(sorted((a["step"], a["rule"]) for a in result[k]) == sorted(expected)
                for k in ("harness_alarms", "jsonl_alarms"))
    print("| rotator | rule_1 & rule_2 | injection_mode | fault_step | alert_step | delta_steps | in_harness_ms | "
          "jsonl_flush_to_alert_ms | verdict |")
    print("|---|---|---|---|---|---|---|---|---|")
    CONFIG = {"static_bound": ", `bounds={\"gpu_alloc_gib\": (None, 40.0)}`", "throughput_drop": ", default settings"}
    for rule in ("static_bound", "throughput_drop"):
        r = result["results"][rule]
        ok = clean and r.get("alert_step") == EXPECTED[rule]["alert_step"] and r.get("severity") == "warn"
        print(f"| @pyru | `{rule}` ({r['severity']}) | synthetic 400-step stream, `MetricsWriter` + `AlarmMonitor`{CONFIG[rule]} | "
              f"{r['fault_step']} | {r['alert_step']} (jsonl: {r['jsonl_alert_step']}) | {r['delta_steps']} "
              f"(jsonl: {r['jsonl_delta_steps']}) | {r['in_harness_ms']:.3f} | {r['jsonl_flush_to_alert_ms']:.3f} | "
              f"{'PASS' if ok else 'FAIL'} |")
