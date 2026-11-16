"""Week 3 G8 rotation (Issue #19): fault-injection test for `moe_routing` and `ema_z`, with time to alert.

A 200-step synthetic training stream is written through MetricsWriter (metrics.jsonl) and checked by
AlarmMonitor in two ways, as in test_alert_injection_raghav.py:

  in-harness  the trainer calls AlarmMonitor.step() on the same values it writes. Time to alert is
              t1 - t0 around step() on the alert step.
  jsonl       a second AlarmMonitor reads metrics.jsonl the way `alarms.py --jsonl` does. Time to alert
              runs from MetricsWriter.write() of the alert step's row until that monitor fires for it.

Both monitors use AlarmMonitor(ema_z_threshold=5.0, moe_patience=5): `ema_z` is off by default, and
`moe_routing` waits 1,000 steps by default, which is longer than this stream.

Two faults:
  - ema_z (severity "warn"): gradient_norm (1.0 + noise, sigma 0.05) jumps by +0.35 at step 155, about 6
    sigma. That is above the EMA z threshold (5.0) and below spike_score's 7 sigma, so only `ema_z` fires.
    155 is not a multiple of flush_every (10), so the jsonl path sees it at the step-160 flush.
  - moe_routing (severity "warn"): expert 3 of 8 gets no tokens at steps 120-129. The rule needs
    `moe_patience` (5) consecutive bad steps, so it fires at step 124 = fault_step + patience - 1, not at 120.

Two extra tests record findings (see docs/alert_tests.md): a big gradient spike pages `spike_score` and
silences `ema_z` on the same step; an expert at 5% of a fair share is "dead" for MetricsWriter but not for
`moe_routing`.

Run the test:   python -m pytest teams/08-monitoring/alarms/test_alert_injection_s9k96.py -q
Print the rows: python teams/08-monitoring/alarms/test_alert_injection_s9k96.py
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

STEPS = 200
SEED = 19
EXPERTS = 8
PATIENCE = 5
EMA_Z = 5.0
GRAD_STEP = 155
GRAD_JUMP = 0.35
MOE_START, MOE_END = 120, 129            # expert DEAD_EXPERT gets no tokens on these steps
DEAD_EXPERT = 3
MOE_ALERT = MOE_START + PATIENCE - 1     # 124
MONITOR_KW = dict(ema_z_threshold=EMA_Z, moe_patience=PATIENCE)


def grad_norm(step, rng):
    g = 1.0 + rng.gauss(0.0, 0.05)
    return g + GRAD_JUMP if step == GRAD_STEP else g


def expert_load(step, rng, dead_share=0.0):
    """Shares of one MoE layer: about 1/8 each; on the fault steps DEAD_EXPERT gets `dead_share` of a fair share."""
    w = [1.0 + rng.gauss(0.0, 0.05) for _ in range(EXPERTS)]
    if MOE_START <= step <= MOE_END:
        w[DEAD_EXPERT] *= dead_share
    total = sum(w)
    return [x / total for x in w]


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


def run_injection(jsonl_path, steps=STEPS, seed=SEED, dead_share=0.0):
    """Run the stream; return one result dict per injected rule."""
    rng = random.Random(seed)
    harness = AlarmMonitor(**MONITOR_KW)
    tail = JsonlTail(jsonl_path)
    faults = {"ema_z": (GRAD_STEP, GRAD_STEP), "moe_routing": (MOE_START, MOE_ALERT)}   # rule: (fault, expected alert)
    res = {rule: {"rule": rule, "fault_step": f, "expected_alert_step": a} for rule, (f, a) in faults.items()}
    expected = {a: rule for rule, (_, a) in faults.items()}
    write_t = {}
    harness_alarms, jsonl_alarms = [], []

    with MetricsWriter(str(jsonl_path), flush_every=FLUSH_EVERY) as writer:
        for step in range(steps):
            metrics = {"loss_ntp": 2.0, "gradient_norm": grad_norm(step, rng), "lr": 3e-4,
                       "expert_load": expert_load(step, rng, dead_share)}

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
    assert r["ema_z"]["alert_step"] == GRAD_STEP and r["ema_z"]["severity"] == "warn"
    assert r["ema_z"]["delta_steps"] == 0
    assert r["moe_routing"]["alert_step"] == MOE_ALERT and r["moe_routing"]["severity"] == "warn"
    assert r["moe_routing"]["delta_steps"] == PATIENCE - 1


def test_no_false_alarms_on_clean_steps(tmp_path):
    out = _run(tmp_path)
    want = {(GRAD_STEP, "ema_z"), (MOE_ALERT, "moe_routing")}
    for alarms in (out["harness_alarms"], out["jsonl_alarms"]):
        assert {(a["step"], a["rule"]) for a in alarms} == want
        assert len(alarms) == len(want)     # each fires once; spike_score does not fire on the 6-sigma jump


def test_jsonl_path_and_flush_lag(tmp_path):
    r = _run(tmp_path)["results"]
    for rule in ("ema_z", "moe_routing"):   # finite rows wait for the next step % 10 == 0 flush
        alert = r[rule]["alert_step"]
        next_flush = (alert // FLUSH_EVERY + 1) * FLUSH_EVERY
        assert r[rule]["jsonl_alert_step"] == next_flush
        assert r[rule]["jsonl_delta_steps"] == next_flush - r[rule]["fault_step"]


def test_timings_non_negative(tmp_path):
    for r in _run(tmp_path)["results"].values():
        assert r["in_harness_ms"] >= 0
        assert r["jsonl_flush_to_alert_ms"] >= 0


def test_finding_spike_score_silences_ema_z_on_same_step():
    """A +1.0 jump (about 20 sigma) pages spike_score; ema_z, enabled, stays silent on that step."""
    rng = random.Random(SEED)
    monitor = AlarmMonitor(ema_z_threshold=EMA_Z)
    fired = []
    for step in range(STEPS):
        g = 1.0 + rng.gauss(0.0, 0.05) + (1.0 if step == GRAD_STEP else 0.0)
        fired += monitor.step(step, gradient_norm=g)
    assert [(a["step"], a["rule"], a["severity"]) for a in fired] == [(GRAD_STEP, "spike_score", "page")]


def test_finding_expert_at_5_percent_is_dead_for_writer_but_not_for_moe_routing(tmp_path):
    """MetricsWriter counts an expert below 10% of a fair share as dead; moe_routing needs an exact 0.0 load."""
    path = Path(tmp_path) / "metrics.jsonl"
    out = run_injection(path, dead_share=0.05)
    rows = {json.loads(l)["step"]: json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
    assert rows[MOE_START]["dead_experts_count"] == 1           # the dashboard metric sees it
    assert rows[MOE_START - 1]["dead_experts_count"] == 0
    assert "moe_routing" not in {a["rule"] for a in out["harness_alarms"]}   # the alarm does not


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        out = _run(d)
    print("| rotator | rule_1 & rule_2 | injection_mode | fault_step | alert_step | delta_steps | in_harness_ms | jsonl_flush_to_alert_ms | verdict |")
    print("|---|---|---|---|---|---|---|---|---|")
    for rule in ("moe_routing", "ema_z"):
        r = out["results"][rule]
        got = {(a["step"], a["rule"]) for a in out["harness_alarms"]}
        ok = r.get("alert_step") == r["expected_alert_step"] and got == {(GRAD_STEP, "ema_z"), (MOE_ALERT, "moe_routing")}
        print(f"| @s9k96 | `{rule}` ({r['severity']}) | synthetic 200-step stream, MetricsWriter + AlarmMonitor | "
              f"{r['fault_step']} | {r['alert_step']} (jsonl: {r['jsonl_alert_step']}) | {r['delta_steps']} "
              f"(jsonl: {r['jsonl_delta_steps']}) | {r['in_harness_ms']:.3f} | {r['jsonl_flush_to_alert_ms']:.3f} | "
              f"{'PASS' if ok else 'FAIL'} |")
