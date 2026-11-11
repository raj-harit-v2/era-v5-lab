# Training alarms (`alarms.py`)

`alarms.py` runs inside the training harness on each step's metric dictionary (or on a `metrics.jsonl` file)
and tests all rules on 3,000 synthetic steps.

```bash
python -I teams/08-monitoring/alarms/alarms.py --synthetic 3000
python -I teams/08-monitoring/alarms/alarms.py --jsonl teams/05-architecture/experiments/evidence/run_a/metrics.jsonl
python -m pytest teams/08-monitoring/alarms/tests -q
```

Tests require `pytest`, `numpy`, and `torch` in the active Python environment.

In the Team 5 training loop (`train.py`):

```python
from alarms import AlarmMonitor

monitor = AlarmMonitor()
for step in range(steps):
    ...
    alarms = monitor.step(
        step,
        loss_ntp=value,
        loss_mtp=mtp_value,
        gradient_norm=grad_norm,
        tokens_per_second=tps,
    )
```

## 1. Alarm rules (Session 15 §16)

| Rule | Metric(s) | Condition | Severity | Notes |
|---|---|---|---|---|
| `non_finite` | any metric | `NaN`, `+Inf`, `-Inf` (including `"nan"`, `"inf"`, `"-inf"` strings from `metrics_writer.py`, NumPy scalars, and 0-d torch tensors) | `stop` | Fires at once on the step where the non-finite value appears. |
| `spike_score` | `loss_ntp`, `loss_mtp`, `gradient_norm` (`loss` if `loss_ntp` absent) | Value $\ge \mu + 7\sigma$ over the trailing 1,000 clean steps (active after `min_window=100` steps) | `page` | OLMo 2 rule. A step that spikes is not pushed into the trailing window, so a spike does not mask the next one. |
| `ema_z` | `gradient_norm` | ZClip EMA z-score ($\alpha = 0.97$) $> z$ after 100 warmup steps (`ema_z_threshold`, off by default) | `warn` | Off by default: in Session 15's 300k-step test, $z = 2.5$ raised 201.9 false alarms per 10k steps while `spike_score` ($7\sigma / 1,000$) caught 40/40 spikes with 0 false alarms. Pass `ema_z_threshold=5.0` (0.43 false/10k) or `2.5` to enable. |
| `throughput_drop` | `tokens_per_second` | $> 10\%$ below the trailing 100-step mean for 100 consecutive steps | `warn` | Skips `step == 0` setup time; fires once when the streak reaches 100 and resets when speed recovers. |
| `moe_routing` | `expert_load` | $\text{MaxVio} > 1.0$ or $\text{dead\_experts} > 0$ for `moe_patience` consecutive steps (default 1,000) | `warn` | Accepts a single list of expert load fractions or a `{layer: [fractions]}` dict. |
| `static_bound` | any scalar in `bounds={name: (lo, hi)}` | Value $< \text{lo}$ or $> \text{hi}$ (optional, folded in from `@rahulsharmaf81` PR #122) | `warn` | Edge-triggered latch: fires once on crossing and re-arms only when the metric returns in-bounds, so cumulative counters do not re-fire on every subsequent step. |

Input and reset behaviour:

- Use `step` with a step's metrics, or `check` for one metric at a time; both may be mixed. Use a new monitor per run.
- Throughput and MoE streaks are tracked per metric (per layer for MoE). A gap, repeat or backward step in that metric, or a null, malformed, negative or non-finite value, restarts the streak; baseline history is kept.
- Zero throughput counts as a slowdown once 20 positive samples (after step 0) form a baseline; it never enters the baseline.
- Severities are labels: the caller stops training and handles notifications. Spike events are returned on every qualifying step.
- **Checkpoint hand-off (Team 07 `Checkpointer`):** `monitor.state_dict()` returns a JSON-serializable snapshot (`schema: "v5-alarms/1"`) of all trailing windows (`_trailing`), ZClip EMA stats, throughput baseline and streak counters, per-layer MoE streaks, and latched static bounds; `monitor.load_state_dict(state)` restores it so a run resumed from a checkpoint continues with identical alarm state and no cold-start warmup gap.

Resume with a monitor constructed using the same settings, including `bounds`; configuration is not saved in the checkpoint. Checkpoints must use schema `v5-alarms/1`.

## 2. Results on 3,000 synthetic steps (`--synthetic 3000`)

The synthetic stream generates 3,000 steps of `loss_ntp`, `loss_mtp`, `gradient_norm`, `tokens_per_second`, `lr`, and `gpu_alloc_gib` with a 200-step warmup, exponential decay, Gaussian/lognormal step noise, and **11 planted faults**:

- **4 loss spikes** (`loss_ntp` at steps 350, 900, 1650, 2400)
- **4 grad-norm spikes** (`gradient_norm` at steps 420, 1150, 1900, 2600)
- **1 sustained throughput drop** (25% slowdown on `tokens_per_second` over steps 1300–1399, firing at step 1399)
- **2 non-finite faults** (`loss_ntp = NaN` at step 2850, `gradient_norm = "inf"` at step 2950)

| Planted faults | Caught | Missed | False alarms |
|---|---|---|---|
| 11 | 11 | 0 | 0 |

Tested on Team 5's `teams/05-architecture/experiments/evidence/run_a/metrics.jsonl` (40 steps): 0 false alarms (step 0 setup slowdown is ignored).
