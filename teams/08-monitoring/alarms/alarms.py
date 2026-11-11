"""In-harness training alarms for ERA V5 (Team 8 Monitoring).

Runs inside the training loop on each step's metrics dict (or on a metrics.jsonl file)
using the rules from Session 15:
  1. non_finite (stop):  any metric is NaN, Inf, or "-inf"/"nan"/"inf" string -> stop at once.
  2. spike_score (page): OLMo 2 rule — loss_ntp, loss_mtp, or gradient_norm exceeds the
                         trailing 1,000-step mean by >= 7 standard deviations.
  3. ema_z (warn):       ZClip EMA z-score (alpha=0.97) on gradient_norm exceeds 2.5.
  4. throughput_drop (warn): tokens_per_second drops > 10% below the trailing 100-step
                         mean for 100 consecutive steps (step 0 setup is skipped).
  5. moe_routing (warn): expert_load MaxVio > 1.0 or dead_experts > 0 for moe_patience steps.

Usage:
  python -I alarms.py --synthetic 3000
  python -I alarms.py --jsonl path/to/metrics.jsonl
"""
from collections import deque
import argparse, json, math, random, sys

SPIKE_METRICS = ("loss_ntp", "loss_mtp", "gradient_norm", "loss")
SCALAR_METRICS = (
    "loss_ntp", "loss_mtp", "loss", "gradient_norm", "lr",
    "tokens_per_second", "gpu_alloc_gib", "gpu_alloc_gb",
    "update_weight_ratio", "validation_loss", "model_flops_utilization", "loader_wait_time",
)


def _to_float(v):
    """Convert Python/NumPy/torch scalars or metric_writer strings to float (or None if non-numeric)."""
    if v is None or isinstance(v, bool):
        return None
    if hasattr(v, "item") and callable(v.item):
        try:
            v = v.item()
        except Exception:
            return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("nan", "+nan", "-nan"):
            return float("nan")
        if s in ("inf", "+inf", "infinity", "+infinity"):
            return float("inf")
        if s in ("-inf", "-infinity"):
            return float("-inf")
    return None


def _iter_floats(v):
    """Yield every numeric scalar inside a scalar, list, or dict (for NaN/Inf inspection)."""
    f = _to_float(v)
    if f is not None:
        yield f
        return
    if hasattr(v, "tolist") and callable(v.tolist):
        v = v.tolist()
    if isinstance(v, (list, tuple)):
        for x in v:
            yield from _iter_floats(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _iter_floats(x)


def max_vio_and_dead(loads):
    """Return (max_vio, dead_experts) for a list of expert load fractions."""
    if hasattr(loads, "tolist") and callable(loads.tolist):
        loads = loads.tolist()
    vals = [_to_float(x) for x in loads]
    if not vals or any(x is None or not math.isfinite(x) for x in vals):
        return 0.0, 0
    mean = sum(vals) / len(vals)
    if mean <= 0:
        return 0.0, sum(1 for x in vals if x <= 0)
    return (max(vals) - mean) / mean, sum(1 for x in vals if x == 0.0)


class _TrailingStats:
    """Trailing window mean and standard deviation over up to `maxlen` clean values."""

    def __init__(self, maxlen=1000):
        self.buf = deque(maxlen=maxlen)

    def __len__(self):
        return len(self.buf)

    def mean_std(self):
        n = len(self.buf)
        if n == 0:
            return 0.0, 0.0
        m = sum(self.buf) / n
        var = sum((x - m) * (x - m) for x in self.buf) / n
        return m, math.sqrt(max(var, 1e-12))

    def push(self, x):
        self.buf.append(x)


class AlarmMonitor:
    """Stateful per-step alarm detector for the training harness."""

    def __init__(
        self,
        window=1000,
        min_window=100,
        sigma_threshold=7.0,
        ema_alpha=0.97,
        ema_z_threshold=None,
        ema_warmup=100,
        tps_window=100,
        tps_drop_fraction=0.10,
        tps_patience=100,
        moe_max_vio_limit=1.0,
        moe_patience=1000,
        bounds=None,
    ):
        self.window = window
        self.min_window = min(min_window, window)
        self.sigma_threshold = sigma_threshold
        self.ema_alpha = ema_alpha
        self.ema_z_threshold = ema_z_threshold
        self.ema_warmup = ema_warmup
        self.tps_drop_fraction = tps_drop_fraction
        self.tps_patience = tps_patience
        self.moe_max_vio_limit = moe_max_vio_limit
        self.moe_patience = moe_patience
        self.bounds = dict(bounds) if bounds else {}

        self._trailing = {m: _TrailingStats(window) for m in SPIKE_METRICS}
        self._ema_mu = None
        self._ema_var = 0.0
        self._ema_seen = 0
        self._tps_stats = _TrailingStats(tps_window)
        self._tps_slow_streak = 0
        self._tps_last_step = None
        self._moe_bad_streak = {}
        self._moe_last_step = {}
        self._bound_latched = set()

    def check(self, step, metric, value):
        """Check a single metric at `step` and return a list of alarm dicts."""
        return self.step(step, **{metric: value})

    def state_dict(self):
        """Return a JSON-serializable snapshot of trailing windows, EMA stats, and streak counters for checkpointing."""
        return {
            "schema": "v5-alarms/1",
            "trailing": {k: list(v.buf) for k, v in self._trailing.items()},
            "ema": {"mu": self._ema_mu, "var": self._ema_var, "seen": self._ema_seen},
            "tps": {
                "buf": list(self._tps_stats.buf),
                "slow_streak": self._tps_slow_streak,
                "last_step": self._tps_last_step,
            },
            "moe": {
                "bad_streak": dict(self._moe_bad_streak),
                "last_step": dict(self._moe_last_step),
            },
            "bound_latched": [list(x) for x in sorted(self._bound_latched)],
        }

    def load_state_dict(self, state):
        """Restore alarm state from a checkpoint dictionary produced by `state_dict()`."""
        if not isinstance(state, dict):
            raise ValueError("AlarmMonitor state_dict must be a dict")
        if state.get("schema") != "v5-alarms/1":
            raise ValueError("Unsupported AlarmMonitor checkpoint schema")
        trailing = state.get("trailing") or {}
        for k, stats in self._trailing.items():
            stats.buf.clear()
            for x in trailing.get(k, ()):
                f = _to_float(x)
                if f is not None and math.isfinite(f):
                    stats.push(f)
        ema = state.get("ema") or {}
        mu = ema.get("mu")
        self._ema_mu = _to_float(mu) if mu is not None else None
        self._ema_var = float(_to_float(ema.get("var", 0.0)) or 0.0)
        self._ema_seen = int(ema.get("seen", 0) or 0)
        tps = state.get("tps") or {}
        self._tps_stats.buf.clear()
        for x in tps.get("buf", ()):
            f = _to_float(x)
            if f is not None and math.isfinite(f) and f > 0:
                self._tps_stats.push(f)
        self._tps_slow_streak = int(tps.get("slow_streak", 0) or 0)
        last_tps = tps.get("last_step")
        self._tps_last_step = int(last_tps) if last_tps is not None else None
        moe = state.get("moe") or {}
        self._moe_bad_streak = {str(k): int(v) for k, v in (moe.get("bad_streak") or {}).items()}
        self._moe_last_step = {
            str(k): int(v) for k, v in (moe.get("last_step") or {}).items() if v is not None
        }
        self._bound_latched = {
            (str(item[0]), str(item[1]))
            for item in (state.get("bound_latched") or ())
            if isinstance(item, (list, tuple)) and len(item) == 2
        }

    def step(self, step, **metrics):
        """Inspect one step's metrics and return a list of fired alarm dicts."""
        alarms = []
        # 1. Non-finite check (NaN / Inf) on any metric -> stop at once.
        nonfinite_names = set()
        for name, raw in metrics.items():
            if name == "step" or name == "time":
                continue
            for val in _iter_floats(raw):
                if not math.isfinite(val):
                    nonfinite_names.add(name)
                    alarms.append({
                        "step": step,
                        "metric": name,
                        "rule": "non_finite",
                        "severity": "stop",
                        "value": str(val),
                        "detail": f"{name} is {val} at step {step}; stop at once",
                    })
                    break

        # Check loss aliases for non-finite values before deduplicating.
        if "loss_ntp" in metrics and "loss" in metrics:
            metrics = {k: v for k, v in metrics.items() if k != "loss"}

        # 2. OLMo 2 trailing-window spike score (7 sigma over last 1,000 clean steps).
        paged_grad = False
        for name in SPIKE_METRICS:
            if name not in metrics or name in nonfinite_names:
                continue
            x = _to_float(metrics[name])
            if x is None:
                continue
            stats = self._trailing[name]
            spiked = False
            if len(stats) >= self.min_window:
                mean, std = stats.mean_std()
                z = (x - mean) / std
                if z >= self.sigma_threshold:
                    spiked = True
                    if name == "gradient_norm":
                        paged_grad = True
                    alarms.append({
                        "step": step,
                        "metric": name,
                        "rule": "spike_score",
                        "severity": "page",
                        "value": x,
                        "z_score": round(z, 2),
                        "trailing_mean": round(mean, 6),
                        "trailing_std": round(std, 6),
                        "detail": f"{name}={x:.4g} is {z:.1f} sigma above trailing {len(stats)}-step mean {mean:.4g}",
                    })
            if not spiked:
                stats.push(x)

        # 3. Optional ZClip EMA z-score on gradient_norm (off by default: z=2.5 gives ~202 false alarms/10k steps).
        if self.ema_z_threshold is not None and "gradient_norm" in metrics and "gradient_norm" not in nonfinite_names:
            x = _to_float(metrics["gradient_norm"])
            if x is not None:
                if self._ema_mu is None:
                    self._ema_mu = x
                    self._ema_seen = 1
                else:
                    sd = math.sqrt(max(self._ema_var, 1e-12))
                    z_ema = (x - self._ema_mu) / sd if sd > 0 else 0.0
                    if self._ema_seen >= self.ema_warmup and z_ema > self.ema_z_threshold:
                        if not paged_grad:
                            alarms.append({
                                "step": step,
                                "metric": "gradient_norm",
                                "rule": "ema_z",
                                "severity": "warn",
                                "value": x,
                                "z_score": round(z_ema, 2),
                                "detail": f"gradient_norm EMA z-score {z_ema:.2f} > {self.ema_z_threshold}",
                            })
                    else:
                        d = x - self._ema_mu
                        self._ema_mu += (1.0 - self.ema_alpha) * d
                        self._ema_var = self.ema_alpha * self._ema_var + (1.0 - self.ema_alpha) * d * d
                        self._ema_seen += 1

        # 4. Throughput drop on tokens_per_second (> 10% drop for 100 consecutive steps; skip step 0 setup).
        # Patience streaks are tracked per metric: an invalid value or a step gap in that metric restarts them.
        if "tokens_per_second" in metrics:
            if self._tps_last_step is not None and step != self._tps_last_step + 1:
                self._tps_slow_streak = 0
            self._tps_last_step = step
            tps = _to_float(metrics["tokens_per_second"])
            if step > 0 and tps is not None and math.isfinite(tps) and tps >= 0:
                if len(self._tps_stats) >= 20:
                    mean_tps, _ = self._tps_stats.mean_std()
                    if tps < (1.0 - self.tps_drop_fraction) * mean_tps:
                        self._tps_slow_streak += 1
                        if self._tps_slow_streak == self.tps_patience:
                            drop_pct = (1.0 - tps / mean_tps) * 100.0
                            alarms.append({
                                "step": step,
                                "metric": "tokens_per_second",
                                "rule": "throughput_drop",
                                "severity": "warn",
                                "value": tps,
                                "baseline_mean": round(mean_tps, 2),
                                "detail": (f"tokens_per_second dropped {drop_pct:.1f}% below baseline "
                                           f"{mean_tps:.1f} for {self.tps_patience} consecutive steps"),
                            })
                    else:
                        self._tps_slow_streak = 0
                        self._tps_stats.push(tps)
                elif tps > 0:
                    self._tps_stats.push(tps)
            else:
                self._tps_slow_streak = 0

        # 5. MoE routing health on expert_load (MaxVio > 1.0 or dead_experts > 0 for moe_patience steps).
        if "expert_load" in metrics:
            raw_load = metrics["expert_load"]
            layers = raw_load if isinstance(raw_load, dict) else {"all": raw_load}
            if "expert_load" in nonfinite_names:
                layers = dict.fromkeys(layers)  # treat every layer in this row as invalid
            for layer, loads in layers.items():
                key = str(layer)
                last = self._moe_last_step.get(key)
                if last is not None and step != last + 1:
                    self._moe_bad_streak[key] = 0
                self._moe_last_step[key] = step
                if not isinstance(loads, (list, tuple)) and not hasattr(loads, "tolist"):
                    self._moe_bad_streak[key] = 0
                    continue
                if hasattr(loads, "tolist"):
                    loads = loads.tolist()
                if not isinstance(loads, (list, tuple)) or not loads:
                    self._moe_bad_streak[key] = 0
                    continue
                vals = [_to_float(x) for x in loads]
                if any(x is None or not math.isfinite(x) or x < 0 for x in vals):
                    self._moe_bad_streak[key] = 0
                    continue
                mv, dead = max_vio_and_dead(loads)
                if mv > self.moe_max_vio_limit or dead > 0:
                    self._moe_bad_streak[key] = self._moe_bad_streak.get(key, 0) + 1
                    if self._moe_bad_streak[key] == self.moe_patience:
                        alarms.append({
                            "step": step,
                            "metric": "expert_load",
                            "layer": layer,
                            "rule": "moe_routing",
                            "severity": "warn",
                            "max_vio": round(mv, 4),
                            "dead_experts": dead,
                            "detail": (f"expert_load[{layer}] MaxVio={mv:.2f}, dead_experts={dead} "
                                       f"for {self.moe_patience} consecutive steps"),
                        })
                else:
                    self._moe_bad_streak[key] = 0

        # 6. Optional static (lo, hi) bounds with edge-triggered latching (folded in from PR #122).
        # Fires once when a metric crosses below `lo` or above `hi`, and re-arms only when it returns in-bounds.
        for name, (lo, hi) in self.bounds.items():
            if name not in metrics or name in nonfinite_names:
                continue
            x = _to_float(metrics[name])
            if x is None or not math.isfinite(x):
                continue
            if lo is not None and x < lo:
                key = (name, "lo")
                if key not in self._bound_latched:
                    self._bound_latched.add(key)
                    alarms.append({
                        "step": step,
                        "metric": name,
                        "rule": "static_bound",
                        "severity": "warn",
                        "value": x,
                        "bound": lo,
                        "detail": f"{name}={x:.4g} fell below lower bound {lo}",
                    })
            else:
                self._bound_latched.discard((name, "lo"))
            if hi is not None and x > hi:
                key = (name, "hi")
                if key not in self._bound_latched:
                    self._bound_latched.add(key)
                    alarms.append({
                        "step": step,
                        "metric": name,
                        "rule": "static_bound",
                        "severity": "warn",
                        "value": x,
                        "bound": hi,
                        "detail": f"{name}={x:.4g} exceeded upper bound {hi}",
                    })
            else:
                self._bound_latched.discard((name, "hi"))

        return alarms


def synthetic_stream(steps=3000, seed=15):
    """Build `steps` synthetic training rows with planted spikes, a throughput drop, and NaN/Inf faults.

    Returns (rows, planted) where `planted` lists the expected (step, metric, rule) tuples.
    """
    rng = random.Random(seed)
    rows = []
    planted = []

    loss_spike_steps = {350: 1.45, 900: 1.55, 1650: 1.50, 2400: 1.60}
    grad_spike_steps = {420: 4.5, 1150: 5.0, 1900: 3.8, 2600: 4.2}
    slow_range = range(1300, 1400)  # 100 consecutive slow steps (25% drop)
    nan_step = 2850
    inf_step = 2950

    for t in range(steps):
        warm = min(1.0, (t + 1) / 200.0)
        base_loss = 1.6 + 8.0 * math.exp(-t / 12000.0) + 1.2 * math.exp(-t / 150000.0)
        loss_ntp = base_loss + rng.gauss(0.0, 0.035) * math.sqrt(base_loss)
        loss_mtp = base_loss + 0.15 + rng.gauss(0.0, 0.035) * math.sqrt(base_loss)
        base_grad = warm * (0.25 + 1.15 * math.exp(-t / 90000.0))
        grad_norm = base_grad * math.exp(rng.gauss(0.0, 0.08))
        tps = 650.0 if t == 0 else 38000.0 + rng.gauss(0.0, 400.0)

        if t in loss_spike_steps:
            loss_ntp *= loss_spike_steps[t]
            planted.append((t, "loss_ntp", "spike_score"))
        if t in grad_spike_steps:
            grad_norm *= grad_spike_steps[t]
            planted.append((t, "gradient_norm", "spike_score"))
        if t in slow_range:
            tps *= 0.75
            if t == slow_range.stop - 1:
                planted.append((t, "tokens_per_second", "throughput_drop"))
        if t == nan_step:
            loss_ntp = float("nan")
            planted.append((t, "loss_ntp", "non_finite"))
        if t == inf_step:
            grad_norm = "inf"  # string form written by metrics_writer.py
            planted.append((t, "gradient_norm", "non_finite"))

        rows.append({
            "step": t,
            "loss_ntp": loss_ntp,
            "loss_mtp": loss_mtp,
            "gradient_norm": grad_norm,
            "tokens_per_second": tps,
            "lr": 3e-4 * warm,
            "gpu_alloc_gib": 24.5,
        })
    planted.sort()
    return rows, planted


def run_synthetic(steps=3000, seed=15):
    rows, planted = synthetic_stream(steps=steps, seed=seed)
    mon = AlarmMonitor()
    fired = []
    for r in rows:
        s = r["step"]
        body = {k: v for k, v in r.items() if k != "step"}
        fired.extend(mon.step(s, **body))

    got = [(a["step"], a["metric"], a["rule"]) for a in fired]
    hit = [p for p in planted if p in got]
    missed = [p for p in planted if p not in got]
    false_alarms = [g for g in got if g not in planted]
    return {
        "steps": steps,
        "planted": len(planted),
        "caught": len(hit),
        "missed": len(missed),
        "false_alarms": len(false_alarms),
        "alarms": fired,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", type=int, nargs="?", const=3000,
                    help="run on N synthetic steps (default 3,000) and verify planted faults")
    ap.add_argument("--jsonl", help="run AlarmMonitor on a metrics.jsonl file")
    a = ap.parse_args()

    if a.jsonl:
        mon = AlarmMonitor()
        total, count = 0, 0
        for line in open(a.jsonl, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            total += 1
            step = r.pop("step", total - 1)
            for al in mon.step(step, **r):
                count += 1
                print(json.dumps(al))
        print(f"read {total} steps from {a.jsonl}: {count} alarm(s)", file=sys.stderr)
        return 0

    steps = a.synthetic or 3000
    res = run_synthetic(steps=steps)
    for al in res["alarms"]:
        print(f"  step {al['step']:4d} | {al['severity']:4s} | {al['rule']:15s} | {al['metric']:17s} | {al['detail']}")
    print(f"synthetic {res['steps']:,} steps: caught {res['caught']}/{res['planted']} planted faults, "
          f"missed {res['missed']}, false alarms {res['false_alarms']}")
    return 1 if (res["missed"] or res["false_alarms"]) else 0


if __name__ == "__main__":
    sys.exit(main())
