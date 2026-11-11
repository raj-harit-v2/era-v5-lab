"""Buffered JSONL metrics writer for the training loop.

One row per completed optimizer step is appended to metrics.jsonl. Rows are held in memory and
written to disk whenever `step % flush_every == 0` (default 10), so a crash loses at most the last 9 steps.
A row with a non-finite value (stored as "nan", "inf" or "-inf") is flushed at once, because that is
the row you want to see after a crash.

Only metrics from the metric list are written; an unknown name (a typo, or a dropped metric such as
`loss` or `loss_by_lane`) is skipped with one warning per name. `gpu_alloc_gb` (the name train.py uses; the value is GiB) is
mapped to `gpu_alloc_gib`, and `temp_c` (the G6 sampler's name) to `gpu_temp_c`. The 10-second system metrics from G6 (`gpu_utilization`,
`gpu_memory_used`) have no step, so they are not written here.

`gradient_clipping_applied` (0 / 1) is worked out from `gradient_norm` (the value clip_grad_norm_ returns, before
clipping) when the trainer also passes `grad_clip`, the threshold: 1 when gradient_norm > grad_clip. The threshold is
not stored. A flag the trainer passes itself wins, and a True / False flag is stored as 1 / 0.

    writer.write(step, loss_ntp=..., gradient_norm=norm, grad_clip=cfg["run"]["grad_clip"])

Three MoE metrics are worked out from `expert_load` when the trainer does not pass them. An expert's utilization is
its share of its layer's picks divided by the uniform share (1 / number of experts): 1.0 is a fair share, 0 is never picked.
- `dead_experts_count`: routed experts, over all MoE layers, with utilization below 0.1.
- `dead_experts_by_layer`: the same count for each MoE layer, in layer order, to show where routing collapses.
- `expert_utilization_min`: the lowest utilization of any routed expert. It falls before an expert is counted as dead,
  so it warns early; below 0.1 the expert is dead.
`expert_load` is one layer (a list of per-expert picks or shares), several layers (a list of lists, or {layer: list}), or a
2-D array or tensor. Counts and shares give the same answer, since each layer is divided by its own total. Pass the
picks of the whole optimizer step, summed over micro-batches and data-parallel ranks: one micro-batch is too small to
call an expert dead.

When `expert_load` is logged, `router_max_vio` (DeepSeek MaxVio, the largest over MoE layers) is
computed from it and written in the same row, unless the caller passed it explicitly.

`validation_loss` (nats per scored token on the held-out set) is worked out from the result of G5's
`week2.evaluation.evaluate()` when the row has it: `val/nll_nats` (the summed loss) / `val/scored_tokens`. It is the
same quantity as `loss_ntp`, so the two can be compared on one axis, and ln(`val/perplexity`). Only rows from a
validation run carry it. A value the trainer passes itself wins.

    writer.write(step, loss_ntp=..., **evaluate(model, val, ...))     # on the steps that run validation

`update_weight_ratio` is the global L2 update-to-weight ratio ||lr * update||_2 / ||W||_2 (one scalar for the
whole model). Call `compute_update_weight_ratio` around the optimizer step and pass the result when it is not
None. By default it only returns a value every 10 steps (`every_n_steps=10`, matching `flush_every`); use
`every_n_steps=1` in tests. A zero or non-finite weight norm yields None so the row gets no ratio instead of a
wrong one.

    ratio = compute_update_weight_ratio(zip(weights, deltas), step=step)
    if ratio is not None:
        writer.write(step, loss_ntp=..., update_weight_ratio=ratio)

    with MetricsWriter("metrics.jsonl") as writer:
        for step in range(n):
            ...
            writer.write(step, loss_ntp=1.2, loss_mtp=1.4, lr=3e-4)
"""

import json
import math
import os
import sys
import time

FLUSH_EVERY = 10

# Metric list, per-step metrics only. Per-layer / per-expert metrics take a list or a dict.
METRICS = frozenset({
    "loss_ntp", "loss_mtp", "lr", "tokens_per_second", "gpu_alloc_gib",
    "gradient_norm", "gradient_clipping_applied", "validation_loss",
    "update_weight_ratio", "expert_load", "router_max_vio",
    "dead_experts_count", "dead_experts_by_layer", "expert_utilization_min",
    "model_flops_utilization", "loader_wait_time",
    "gpu_temp_c", "gpu_thermal_throttle",
    "tokens_per_byte", "tokens_per_byte_by_lang",
})

# Names used by train.py that are written under a different name.
ALIASES = {"gpu_alloc_gb": "gpu_alloc_gib", "temp_c": "gpu_temp_c"}


def _max_vio(loads):
    """DeepSeek MaxVio for one MoE layer: (max load - mean load) / mean load.

    0.0 means every expert gets the same share; 1.0 means the busiest expert gets twice the
    average. Returns NaN if any load is not finite or the mean is not positive.
    """
    loads = [float(x) for x in loads]
    if not all(math.isfinite(x) for x in loads):
        return float("nan")
    mean = sum(loads) / len(loads)
    if mean <= 0:
        return float("nan")
    return (max(loads) - mean) / mean


def _layers(expert_load):
    """Split expert_load into one list of loads per layer.

    Accepts a flat list (one layer), a list of lists, or a dict {layer: list}, as plain Python,
    NumPy or torch values. Empty layers are dropped.
    """
    if hasattr(expert_load, "tolist"):  # numpy array, torch tensor
        expert_load = expert_load.tolist()
    if isinstance(expert_load, dict):
        layers = list(expert_load.values())
    elif expert_load and all(isinstance(x, (list, tuple)) or getattr(x, "ndim", 0) >= 1 for x in expert_load):
        layers = list(expert_load)
    else:
        layers = [expert_load]
    layers = [x.tolist() if hasattr(x, "tolist") else x for x in layers]
    return [list(x) for x in layers if len(x) > 0]


def router_max_vio_per_layer(expert_load):
    """MaxVio for each MoE layer in expert_load (see `_layers` for accepted shapes)."""
    return [_max_vio(loads) for loads in _layers(expert_load)]


def router_max_vio(expert_load):
    """Routing imbalance for one step: the worst (largest) MaxVio over all MoE layers.

    Returns None if expert_load has no layers. NaN in any layer makes the result NaN, so a
    broken router is never hidden behind a healthy one.
    """
    per_layer = router_max_vio_per_layer(expert_load)
    if not per_layer:
        return None
    if any(math.isnan(v) for v in per_layer):
        return float("nan")
    return max(per_layer)

# An expert is dead below this fraction of the uniform share of its layer's picks.
DEAD_EXPERT_SHARE = 0.1


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def expert_load_stats(expert_load, share=DEAD_EXPERT_SHARE):
    """{dead_experts_count, dead_experts_by_layer, expert_utilization_min} from expert_load.

    None when it cannot be told: no layers, an empty layer, a layer with no picks, or a negative or non-finite value.
    """
    if hasattr(expert_load, "tolist"):
        expert_load = expert_load.tolist()
    if isinstance(expert_load, dict):
        expert_load = list(expert_load.values())
    if not isinstance(expert_load, (list, tuple)) or not expert_load:
        return None
    layers = [expert_load] if all(_number(x) for x in expert_load) else expert_load
    by_layer, lowest = [], math.inf
    for layer in layers:
        if hasattr(layer, "tolist"):
            layer = layer.tolist()
        if not isinstance(layer, (list, tuple)) or not layer or not all(_number(x) and math.isfinite(x) and x >= 0 for x in layer):
            return None
        total = sum(layer)
        if total <= 0:
            return None
        # utilization = load / (total / n); dead below `share`, written without division
        by_layer.append(sum(1 for x in layer if x * len(layer) < share * total))
        lowest = min(lowest, min(layer) * len(layer) / total)
    return {"dead_experts_count": sum(by_layer), "dead_experts_by_layer": by_layer, "expert_utilization_min": lowest}


def dead_experts_count(expert_load, share=DEAD_EXPERT_SHARE):
    """Routed experts below `share` x the uniform share, summed over MoE layers; None when it cannot be told."""
    stats = expert_load_stats(expert_load, share)
    return None if stats is None else stats["dead_experts_count"]


def gradient_clipping_applied(gradient_norm, grad_clip):
    """1 when clip_grad_norm_ scaled the gradients down (gradient_norm > grad_clip), else 0; None when it cannot be told.

    gradient_norm is the value clip_grad_norm_ returns: the total norm before clipping. grad_clip is the threshold
    (run.grad_clip). An infinite norm counts as clipped. A NaN norm, or a missing, non-finite or non-positive
    threshold, gives None, so the row gets no flag instead of a wrong one.
    """
    if gradient_norm is None or grad_clip is None or isinstance(grad_clip, bool):
        return None
    if hasattr(gradient_norm, "item"):  # numpy / torch scalar
        gradient_norm = gradient_norm.item()
    try:
        norm, clip = float(gradient_norm), float(grad_clip)
    except (TypeError, ValueError):
        return None
    if math.isnan(norm) or not math.isfinite(clip) or clip <= 0:
        return None
    return int(norm > clip)


def _clean(value):
    """Return (JSON-safe value, whether any non-finite number was found).

    NumPy and torch scalars become Python numbers. NaN and Inf are stored as the strings
    "nan", "inf" and "-inf", so the monitor can tell a NaN loss from an overflow.
    """
    if hasattr(value, "tolist"):  # numpy scalar/array, torch tensor
        value = value.tolist()
    if isinstance(value, float):
        return (value, False) if math.isfinite(value) else (str(value), True)
    if isinstance(value, (list, tuple)):
        pairs = [_clean(v) for v in value]
        return [v for v, _ in pairs], any(bad for _, bad in pairs)
    if isinstance(value, dict):
        pairs = {k: _clean(v) for k, v in value.items()}
        return {k: v for k, (v, _) in pairs.items()}, any(bad for _, bad in pairs.values())
    return value, False


def validation_loss(nll_nats, scored_tokens):
    """Mean held-out loss in nats per scored token: nll_nats (summed) / scored_tokens; None when it cannot be told.

    These are `val/nll_nats` and `val/scored_tokens` from G5's evaluate(). None when either is missing, the token
    count is not a positive whole number, or the sum is not a finite number >= 0.
    """
    if nll_nats is None or scored_tokens is None or isinstance(nll_nats, bool) or isinstance(scored_tokens, bool):
        return None
    if hasattr(nll_nats, "item"):  # numpy / torch scalar
        nll_nats = nll_nats.item()
    if hasattr(scored_tokens, "item"):
        scored_tokens = scored_tokens.item()
    try:
        total, tokens = float(nll_nats), float(scored_tokens)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(total) or total < 0 or not math.isfinite(tokens) or tokens < 1 or tokens != int(tokens):
        return None
    return total / tokens


def _sq_l2_norm(value):
    """Squared L2 (Frobenius) norm of a tensor, array, or nested list; NaN if any value is not finite."""
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "float") and not isinstance(value, (list, tuple)):
        try:
            value = value.float()
        except (TypeError, ValueError):
            pass
    if hasattr(value, "norm") and not isinstance(value, (list, tuple)):
        try:
            n = float(value.norm().item() if hasattr(value.norm(), "item") else value.norm())
        except (TypeError, ValueError):
            n = float("nan")
        return n * n if math.isfinite(n) else float("nan")
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        total = 0.0
        for part in value:
            part_sq = _sq_l2_norm(part)
            if not math.isfinite(part_sq):
                return float("nan")
            total += part_sq
        return total
    try:
        x = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return x * x if math.isfinite(x) else float("nan")


def _iter_weight_update_pairs(weights, updates=None, weights_after=None):
    """Yield (weight, update) pairs from pairs, parallel sequences, or pre/post weights."""
    if weights_after is not None:
        if updates is not None:
            raise ValueError("pass updates or weights_after, not both")
        before = list(weights)
        after = list(weights_after)
        if len(before) != len(after):
            raise ValueError("weights and weights_after must have the same length")
        for w, w_after in zip(before, after):
            if hasattr(w_after, "sub"):
                yield w, w_after - w
            elif hasattr(w_after, "__sub__") and not isinstance(w_after, (list, tuple)):
                yield w, w_after - w
            else:
                # Nested Python lists: element-wise after - before via matching structure is not supported;
                # require numeric tensors/arrays for the pre/post form.
                raise TypeError("weights_after form needs tensor/array weights")
        return
    if updates is not None:
        before = list(weights)
        deltas = list(updates)
        if len(before) != len(deltas):
            raise ValueError("weights and updates must have the same length")
        yield from zip(before, deltas)
        return
    # Iterable of (weight, update) pairs, or an nn.Module (parameters only — caller must pass updates).
    if hasattr(weights, "parameters") and not isinstance(weights, (list, tuple)):
        raise TypeError("pass (weight, update) pairs or weights with updates=/weights_after=; a bare module has no updates")
    for item in weights:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise TypeError("expected (weight, update) pairs")
        yield item[0], item[1]


def compute_update_weight_ratio(
    weights,
    updates=None,
    *,
    weights_after=None,
    lr=1.0,
    step=None,
    every_n_steps=FLUSH_EVERY,
):
    """Global L2 update-to-weight ratio ||lr * update||_2 / ||W||_2; None when not logged or cannot be told.

    One scalar for the whole model: sqrt(sum_p ||lr * u_p||_2^2) / sqrt(sum_p ||w_p||_2^2). That matches
    ||ΔW||_2 / ||W||_2 when each update is the parameter change (or when update is the optimizer direction and
    `lr` is the effective step size).

    `weights` may be an iterable of (weight, update) pairs, or a sequence of weights used with `updates=` or
    `weights_after=` (update = after - before). Returns None when `step` is set and `step % every_n_steps != 0`
    (default every_n_steps=10), when there are no parameters, when `lr` is not a finite number, or when the
    weight norm is zero / not finite. Non-finite updates make the ratio NaN so a broken step is visible.
    """
    if every_n_steps < 1:
        raise ValueError("every_n_steps must be >= 1")
    if step is not None and step % every_n_steps != 0:
        return None
    if isinstance(lr, bool):
        return None
    try:
        scale = float(lr)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(scale):
        return None

    weight_sq = 0.0
    update_sq = 0.0
    count = 0
    try:
        pairs = list(_iter_weight_update_pairs(weights, updates=updates, weights_after=weights_after))
    except (TypeError, ValueError):
        return None
    for weight, update in pairs:
        w_sq = _sq_l2_norm(weight)
        u_sq = _sq_l2_norm(update)
        if not math.isfinite(w_sq):
            return None
        if not math.isfinite(u_sq):
            return float("nan")
        weight_sq += w_sq
        update_sq += u_sq
        count += 1
    if count == 0 or weight_sq <= 0:
        return None
    return math.sqrt(update_sq * (scale * scale)) / math.sqrt(weight_sq)


class MetricsWriter:
    def __init__(self, path, flush_every=FLUSH_EVERY):
        if flush_every < 1:
            raise ValueError("flush_every must be >= 1")
        self.path = path
        self.flush_every = flush_every
        self._buffer = []
        self._warned = set()
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        self._file = open(path, "a", encoding="utf-8")

    def write(self, step, **metrics):
        """Buffer one row; flush when step is a multiple of `flush_every`."""
        if self._file is None:
            raise ValueError("write() on a closed MetricsWriter")
        # Trainer measures host-side next_batch() wait in milliseconds. Persist seconds.
        # An explicit loader_wait_time value is already in seconds and takes precedence.
        data_ms = metrics.pop("data_ms", None)
        if "loader_wait_time" not in metrics and data_ms is not None:
            metrics["loader_wait_time"] = float(data_ms) / 1000.0
        # gradient_clipping_applied is worked out from gradient_norm and grad_clip (the threshold, not stored).
        # A flag passed by the trainer wins; a bool (G5's train_week2.py writes one) is stored as 0 / 1.
        grad_clip = metrics.pop("grad_clip", None)
        if metrics.get("gradient_clipping_applied") is not None:
            metrics["gradient_clipping_applied"] = int(bool(metrics["gradient_clipping_applied"]))
        else:
            flag = gradient_clipping_applied(metrics.get("gradient_norm"), grad_clip)
            if flag is not None:
                metrics["gradient_clipping_applied"] = flag
        metrics = {ALIASES.get(name, name): value for name, value in metrics.items()}
        # The MoE metrics are worked out from expert_load; a value passed by the trainer wins.
        if metrics.get("expert_load") is not None:
            for name, value in (expert_load_stats(metrics["expert_load"]) or {}).items():
                if metrics.get(name) is None:
                    metrics[name] = value
        # validation_loss from G5's evaluate() result; a value passed by the trainer wins. The two inputs are used up.
        nll_nats, scored = metrics.pop("val/nll_nats", None), metrics.pop("val/scored_tokens", None)
        if metrics.get("validation_loss") is None:
            loss = validation_loss(nll_nats, scored)
            if loss is not None:
                metrics["validation_loss"] = loss
        # Names outside the metric list are skipped, not written.
        for name in metrics:
            if name not in METRICS and name not in self._warned:
                self._warned.add(name)
                print(f"metrics_writer: skipping unknown metric {name!r}", file=sys.stderr)
        metrics = {name: value for name, value in metrics.items() if name in METRICS}
        # router_max_vio is derived from expert_load unless the caller passed it.
        if metrics.get("expert_load") is not None and "router_max_vio" not in metrics:
            vio = router_max_vio(metrics["expert_load"])
            if vio is not None:
                metrics["router_max_vio"] = vio
        row = {"step": step, "time": time.time()}
        nonfinite = False
        for name, value in metrics.items():
            # Plain JSON has no NaN/Infinity; store null and flush now.
            row[name], bad = _clean(value)
            nonfinite = nonfinite or bad
        self._buffer.append(json.dumps(row, allow_nan=False))
        if nonfinite or step % self.flush_every == 0:
            self.flush()

    def flush(self):
        """Write buffered rows to disk."""
        if self._file is None or not self._buffer:
            return
        self._file.write("\n".join(self._buffer) + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())
        self._buffer.clear()

    def close(self):
        """Flush the remaining rows and close the file. Safe to call twice."""
        if self._file is None:
            return
        self.flush()
        self._file.close()
        self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
