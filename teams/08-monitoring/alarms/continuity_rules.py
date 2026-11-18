"""Two extra alarm rules for dry run 1 (Week 3 G8 rotation, Issue #24): step continuity and loader stall.

They follow the event shape of `alarms.py` (a list of dicts with step, metric, rule, severity, detail), so a caller
can merge them with `AlarmMonitor.step()` output. They live in their own file so that the rotators who add rules in
week 3 do not edit `alarms.py` at the same time. The core team can fold them into `AlarmMonitor` later.

step_continuity
    Watches the step numbers of the rows, in the order they arrive.
    - A jump forward (step > last + 1) means rows are missing:  severity "page", rule "step_continuity",
      kind "missing", with the first and last missing step. Work order: "a missing step is a bug".
    - A step at or below the newest step seen means rows are written again: severity "warn", kind "repeated".
      This is expected once after a checkpoint restore (the trainer redoes the steps after the checkpoint), so it is
      a warn, and it is reported once per restart (when the stream goes back), not on every repeated row.
    The first row sets the start; a run may start at any step (a resumed run starts after its checkpoint).

loader_stall
    Watches `loader_wait_time` (seconds the training loop waited for the next batch).
    It fires once (severity "warn") when the value is above `threshold_s` for `patience` consecutive steps, and it
    re-arms when the value drops back to or below the threshold. A step gap, a repeated step, or a missing, null or
    non-finite value restarts the streak, as in `throughput_drop`.
    The defaults (1.0 s for 20 steps) are placeholders until Team 06 gives per-step loader times.
"""
import math

SCHEMA = "v5-continuity/1"


def _float(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


class StepContinuityMonitor:
    def __init__(self):
        self._last = None        # newest step seen
        self._going_back = False  # inside a run of repeated rows (one warn per restart)

    def step(self, step, **_metrics):
        step = int(step)
        out = []
        if self._last is None:
            self._last = step
            return out
        if step == self._last + 1:
            self._going_back = False
            self._last = step
        elif step > self._last + 1:
            first, last = self._last + 1, step - 1
            out.append({
                "step": step, "metric": "step", "rule": "step_continuity", "severity": "page", "kind": "missing",
                "missing_from": first, "missing_to": last, "missing_count": last - first + 1,
                "detail": f"steps {first} to {last} are missing ({last - first + 1} rows) before step {step}",
            })
            self._going_back = False
            self._last = step
        else:                     # step <= newest step seen: rows written again
            if not self._going_back:
                out.append({
                    "step": step, "metric": "step", "rule": "step_continuity", "severity": "warn", "kind": "repeated",
                    "newest_step": self._last,
                    "detail": f"step {step} arrives after step {self._last}: rows are written again (restore?)",
                })
                self._going_back = True
            if step == self._last:   # the stream has caught up with where it was
                self._going_back = False
        return out

    def state_dict(self):
        return {"schema": SCHEMA, "last": self._last, "going_back": self._going_back}

    def load_state_dict(self, state):
        if state.get("schema") != SCHEMA:
            raise ValueError(f"expected schema {SCHEMA}, got {state.get('schema')}")
        self._last, self._going_back = state["last"], state["going_back"]


class LoaderStallMonitor:
    def __init__(self, threshold_s=1.0, patience=20):
        if patience < 1:
            raise ValueError("patience must be >= 1")
        self.threshold_s = threshold_s
        self.patience = patience
        self._streak = 0
        self._fired = False
        self._last_step = None

    def step(self, step, **metrics):
        step = int(step)
        if "loader_wait_time" not in metrics:
            return []
        x = _float(metrics["loader_wait_time"])
        gap = self._last_step is not None and step != self._last_step + 1
        self._last_step = step
        if x is None or x < 0:
            self._streak, self._fired = 0, False
            return []
        if gap:                   # start counting again from this step
            self._streak, self._fired = 0, False
        if x <= self.threshold_s:
            self._streak, self._fired = 0, False
            return []
        self._streak += 1
        if self._streak >= self.patience and not self._fired:
            self._fired = True
            return [{
                "step": step, "metric": "loader_wait_time", "rule": "loader_stall", "severity": "warn",
                "value": x, "threshold_s": self.threshold_s, "streak": self._streak,
                "detail": (f"loader_wait_time above {self.threshold_s} s for {self._streak} steps "
                           f"(now {x:.3g} s): the data loader is starving training"),
            }]
        return []

    def state_dict(self):
        return {"schema": SCHEMA, "streak": self._streak, "fired": self._fired, "last_step": self._last_step}

    def load_state_dict(self, state):
        if state.get("schema") != SCHEMA:
            raise ValueError(f"expected schema {SCHEMA}, got {state.get('schema')}")
        self._streak, self._fired, self._last_step = state["streak"], state["fired"], state["last_step"]


class ContinuityMonitor:
    """Both rules together: `step(step, **metrics)` returns the events of both."""

    def __init__(self, loader_threshold_s=1.0, loader_patience=20):
        self.steps = StepContinuityMonitor()
        self.loader = LoaderStallMonitor(loader_threshold_s, loader_patience)

    def step(self, step, **metrics):
        return self.steps.step(step, **metrics) + self.loader.step(step, **metrics)
