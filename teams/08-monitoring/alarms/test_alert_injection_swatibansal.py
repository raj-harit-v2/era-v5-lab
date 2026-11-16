"""Week 3 G8 rotation (Issue #19): fault-injection test for `throughput_drop` and `static_bound`, with time to alert.

A 300-step synthetic training stream is written through MetricsWriter (metrics.jsonl) and checked by
AlarmMonitor in two ways, as in test_alert_injection_raghav.py and test_alert_injection_s9k96.py:

  in-harness  the trainer calls AlarmMonitor.step() on the same values it writes. Time to alert is
              t1 - t0 around step() on the alert step.
  jsonl       a second AlarmMonitor reads metrics.jsonl the way `alarms.py --jsonl` does. Time to alert
              runs from MetricsWriter.write() of the alert step's row until that monitor fires for it.

Both monitors use AlarmMonitor(bounds={"gpu_alloc_gib": (None, 70.0)}). `throughput_drop` keeps its defaults
(tps_window=100, tps_drop_fraction=0.10, tps_patience=100), so the stream is long enough for the full patience.
`static_bound` is off unless `bounds` is passed; the bound here is an upper limit on PyTorch GPU memory, as a
stand-in for "the run is about to go out of memory".

Two faults:
  - throughput_drop (severity "warn"): tokens_per_second (about 50,000, noise 1%) falls by 25% from step 150
    to the end. The rule needs `tps_patience` (100) consecutive slow steps, so it fires at step
    249 = fault_step + patience - 1, not at 150. 249 is not a multiple of flush_every (10), so the jsonl path
    sees it at the step-250 flush.
  - static_bound (severity "warn"): gpu_alloc_gib (about 60, noise 0.2) jumps to about 72 at step 205 and stays
    there until step 230. The upper bound is 70.0, so the rule fires at 205 and, being an edge-triggered latch,
    only once for the whole excursion. 205 is not a multiple of 10, so the jsonl path sees it at step 210.

Three extra tests record findings (see docs/alert_tests.md): a slowdown shorter than tps_patience never alerts;
a fault that lands on a flush step has no jsonl lag; a metric that stays out of bounds fires once, and fires again
only after it returns in-bounds and crosses the bound a second time.

Run the test:   python -m pytest teams/08-monitoring/alarms/test_alert_injection_swatibansal.py -q
Print the rows: python teams/08-monitoring/alarms/test_alert_injection_swatibansal.py
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
from alarms import AlarmMonitor  # noqa: E402
from metrics_writer import FLUSH_EVERY, MetricsWriter  # noqa: E402

STEPS = 300
SEED = 19
TPS_BASE = 50_000.0
TPS_DROP_START = 150                      # tokens_per_second falls by TPS_DROP_FRACTION from here on
TPS_DROP_FRACTION = 0.25
TPS_PATIENCE = 100                        # AlarmMonitor default; kept so the run matches a real one
TPS_ALERT = TPS_DROP_START + TPS_PATIENCE - 1   # 249
MEM_BASE = 60.0
MEM_HIGH = 72.0
MEM_HI_BOUND = 70.0
MEM_START, MEM_END = 205, 230             # gpu_alloc_gib sits at MEM_HIGH on these steps
MONITOR_KW = dict(bounds={"gpu_alloc_gib": (None, MEM_HI_BOUND)})


def tokens_per_second(step, rng, drop_start=TPS_DROP_START, drop_end=None):
    """About 50,000 tokens/s with 1% noise; 25% slower on [drop_start, drop_end]. Step 0 is slow setup."""
    tps = TPS_BASE * (1.0 + rng.gauss(0.0, 0.01))
    if step == 0:
        return tps * 0.5
    if drop_start is not None and step >= drop_start and (drop_end is None or step <= drop_end):
        return tps * (1.0 - TPS_DROP_FRACTION)
    return tps


def gpu_alloc_gib(step, rng, windows=((MEM_START, MEM_END),)):
    """About 60 GiB with 0.2 GiB noise; about 72 GiB inside each (start, end) window."""
    high = any(a <= step <= b for a, b in windows)
    return (MEM_HIGH if high else MEM_BASE) + rng.gauss(0.0, 0.2)


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
            fired.extend(self.monitor.step(step, **row))
        return fired


def run_injection(jsonl_path, steps=STEPS, seed=SEED, tps_drop_end=None, mem_windows=((MEM_START, MEM_END),),
                  faults=None):
    """Run the stream; return one result dict per injected rule."""
    rng = random.Random(seed)
    harness = AlarmMonitor(**MONITOR_KW)
    tail = JsonlTail(jsonl_path)
    if faults is None:                      # rule: (fault step, expected alert step)
        faults = {"throughput_drop": (TPS_DROP_START, TPS_ALERT), "static_bound": (MEM_START, MEM_START)}
    res = {rule: {"rule": rule, "fault_step": f, "expected_alert_step": a} for rule, (f, a) in faults.items()}
    expected = {a: rule for rule, (_, a) in faults.items()}
    write_t = {}
    harness_alarms, jsonl_alarms = [], []

    with MetricsWriter(str(jsonl_path), flush_every=FLUSH_EVERY) as writer:
        for step in range(steps):
            metrics = {"loss_ntp": 2.0 + rng.gauss(0.0, 0.01), "lr": 3e-4,
                       "tokens_per_second": tokens_per_second(step, rng, drop_end=tps_drop_end),
                       "gpu_alloc_gib": gpu_alloc_gib(step, rng, mem_windows)}

            t0 = time.perf_counter()
            fired = harness.step(step, **metrics)
            t1 = time.perf_counter()
            for a in fired:
                harness_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and step == r["expected_alert_step"] and "alert_step" not in r:
                    r.update(alert_step=step, severity=a["severity"], in_harness_ms=(t1 - t0) * 1e3)

            write_t[step] = time.perf_counter()
            writer.write(step, **metrics)
            for a in tail.poll():
                jsonl_alarms.append(a)
                r = res.get(a["rule"])
                if r is not None and a["step"] == r["expected_alert_step"] and "jsonl_alert_step" not in r:
                    r.update(jsonl_alert_step=step,
                             jsonl_flush_to_alert_ms=(time.perf_counter() - write_t[a["step"]]) * 1e3)

    for a in tail.poll():                   # rows flushed by close()
        jsonl_alarms.append(a)
    for r in res.values():
        r["delta_steps"] = r["alert_step"] - r["fault_step"] if "alert_step" in r else None
        r["jsonl_delta_steps"] = (r["jsonl_alert_step"] - r["fault_step"]) if "jsonl_alert_step" in r else None
    return {"results": res, "harness_alarms": harness_alarms, "jsonl_alarms": jsonl_alarms, "expected": expected}


def _run(tmp_dir, **kw):
    return run_injection(Path(tmp_dir) / "metrics.jsonl", **kw)


def test_both_faults_fire_expected_rule_and_severity(tmp_path):
    r = _run(tmp_path)["results"]
    assert r["throughput_drop"]["alert_step"] == TPS_ALERT and r["throughput_drop"]["severity"] == "warn"
    assert r["throughput_drop"]["delta_steps"] == TPS_PATIENCE - 1
    assert r["static_bound"]["alert_step"] == MEM_START and r["static_bound"]["severity"] == "warn"
    assert r["static_bound"]["delta_steps"] == 0


def test_no_false_alarms_on_clean_steps(tmp_path):
    out = _run(tmp_path)
    want = {(TPS_ALERT, "throughput_drop"), (MEM_START, "static_bound")}
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        assert {(a["step"], a["rule"]) for a in alarms} == want
        assert len(alarms) == len(want)     # each fires once: the bound latches for steps 206-230, the slow streak after 249


def test_jsonl_path_and_flush_lag(tmp_path):
    r = _run(tmp_path)["results"]
    for rule in ("throughput_drop", "static_bound"):   # finite rows wait for the next step % 10 == 0 flush
        alert = r[rule]["alert_step"]
        next_flush = (alert // FLUSH_EVERY + 1) * FLUSH_EVERY
        assert r[rule]["jsonl_alert_step"] == next_flush
        assert r[rule]["jsonl_delta_steps"] == next_flush - r[rule]["fault_step"]


def test_timings_non_negative(tmp_path):
    for r in _run(tmp_path)["results"].values():
        assert r["in_harness_ms"] >= 0
        assert r["jsonl_flush_to_alert_ms"] >= 0


def test_finding_slowdown_shorter_than_patience_never_alerts(tmp_path):
    """A 25% slowdown lasting tps_patience - 1 = 99 steps (150-248) resets the streak at 249 and never fires."""
    out = _run(tmp_path, tps_drop_end=TPS_DROP_START + TPS_PATIENCE - 2)
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        assert "throughput_drop" not in {a["rule"] for a in alarms}
        assert {(a["step"], a["rule"]) for a in alarms} == {(MEM_START, "static_bound")}


def test_finding_fault_on_a_flush_step_has_no_jsonl_lag(tmp_path):
    """gpu_alloc_gib crosses the bound at step 210, a multiple of flush_every, so the jsonl path sees it at 210."""
    out = _run(tmp_path, mem_windows=((210, 230),),
               faults={"throughput_drop": (TPS_DROP_START, TPS_ALERT), "static_bound": (210, 210)})
    r = out["results"]["static_bound"]
    assert r["alert_step"] == 210 and r["jsonl_alert_step"] == 210
    assert r["delta_steps"] == 0 and r["jsonl_delta_steps"] == 0


def test_finding_static_bound_latches_and_rearms():
    """Out of bounds on 205-230 fires once; back in bounds, then out again on 260-265 fires a second time."""
    rng = random.Random(SEED)
    monitor = AlarmMonitor(**MONITOR_KW)
    fired = []
    for step in range(STEPS):
        fired += monitor.step(step, gpu_alloc_gib=gpu_alloc_gib(step, rng, ((MEM_START, MEM_END), (260, 265))))
    assert [(a["step"], a["rule"], a["severity"]) for a in fired] == [(MEM_START, "static_bound", "warn"),
                                                                       (260, "static_bound", "warn")]
    assert all(a["bound"] == MEM_HI_BOUND and a["value"] > MEM_HI_BOUND for a in fired)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        out = _run(d)
    print("| rotator | rule_1 & rule_2 | injection_mode | fault_step | alert_step | delta_steps | in_harness_ms | jsonl_flush_to_alert_ms | verdict |")
    print("|---|---|---|---|---|---|---|---|---|")
    want = {(TPS_ALERT, "throughput_drop"), (MEM_START, "static_bound")}
    got = {(a["step"], a["rule"]) for a in out["harness_alarms"]}
    for rule, mode in (("throughput_drop", "default tps_patience=100"),
                       ("static_bound", "bounds={gpu_alloc_gib: (None, 70.0)}")):
        r = out["results"][rule]
        ok = r.get("alert_step") == r["expected_alert_step"] and got == want
        print(f"| @swatibansal | `{rule}` ({r['severity']}) | synthetic 300-step stream, MetricsWriter + AlarmMonitor, {mode} | "
              f"{r['fault_step']} | {r['alert_step']} (jsonl: {r['jsonl_alert_step']}) | {r['delta_steps']} "
              f"(jsonl: {r['jsonl_delta_steps']}) | {r['in_harness_ms']:.3f} | {r['jsonl_flush_to_alert_ms']:.3f} | "
              f"{'PASS' if ok else 'FAIL'} |")
