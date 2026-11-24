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
| `val_regression` | `validation_bpb`, `validation_loss` (rows of a validation run only) | Value more than `val_regression_frac` above that metric's best (lowest) value so far, for `val_patience` validation runs in a row (default 1); off unless `val_regression_frac` is set, e.g. `0.02` | `warn` | Fires once per streak; a new best resets it. Neither `spike_score` (training losses only) nor a fixed `static_bound` catches a validation curve that turns back up (G8 W3 rotation, Issue #25, `test_alert_injection_sohamniyogi.py`). |

Input and reset behaviour:

- Use `step` with a step's metrics, or `check` for one metric at a time; both may be mixed. Use a new monitor per run.
- Throughput and MoE streaks are tracked per metric (per layer for MoE). A gap, repeat or backward step in that metric, or a null, malformed, negative or non-finite value, restarts the streak; baseline history is kept.
- Zero throughput counts as a slowdown once 20 positive samples (after step 0) form a baseline; it never enters the baseline.
- Severities are labels: the caller stops training and handles notifications. Spike events are returned on every qualifying step.
- **Checkpoint hand-off (Team 07 `Checkpointer`):** `monitor.state_dict()` returns a JSON-serializable snapshot (`schema: "v5-alarms/1"`) of all trailing windows (`_trailing`), ZClip EMA stats, throughput baseline and streak counters, per-layer MoE streaks, latched static bounds, and the validation best values and streaks; `monitor.load_state_dict(state)` restores it so a run resumed from a checkpoint continues with identical alarm state and no cold-start warmup gap.

A checkpoint written before `val_regression` existed (no `val` entry) still loads, with no validation best yet. Resume with a monitor constructed using the same settings, including `bounds` and `val_regression_frac`; configuration is not saved in the checkpoint. Checkpoints must use schema `v5-alarms/1`.

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

## 3. Eval-watcher lag alarm (`eval_lag.py`)

Week 4, task 1 (with Team 9). It pages when Team 9's Tier A eval scores fall behind training: the run's newest Tier A
score in `eval_mini` is for a step more than 2 checkpoint intervals of training older than its newest training step
(`teams/09-evaluation/eval_schedule.md` section 6). At dry run 2's 600 s interval the limit is 1,200 s. It runs beside
`clickhouse/watch_jsonl.py`, not in the trainer, and needs only the standard library.

```bash
# Dry run 2. The kill drill restarts the trainer with a fresh --out, so map those run ids to the run Team 9 scores.
python -I teams/08-monitoring/alarms/eval_lag.py --interval-s 600 --run dryrun2-1234 \
    --run dryrun2-1234-resume-a=dryrun2-1234 --run dryrun2-1234-resume-b=dryrun2-1234 --poll 60
python -I teams/08-monitoring/alarms/eval_lag.py --interval-s 600 --once --no-write   # one read-only check
python -m pytest teams/08-monitoring/alarms/tests/test_eval_lag.py -q
```

**Inputs.**
- Training: `ingest_batches` (`seen_at`, `first_step`, `last_step`), which `watch_jsonl.py` writes for every batch it
  reads. Not `metrics_raw.time`: Team 5's trainer writes no time field, so `load_jsonl.py` stores an invented time
  (28 Oct 2026 plus 1 s per line).
- Eval: `eval_mini` rows with `:tier-a:` in `run_id`, per `checkpoint_run` (the trainer's `--run-id`, #606). Tier B
  and Tier C rows don't count.

**Rules.**

| Case | What the alarm does |
|---|---|
| Normal | Lag = training time from the batch that reached the newest Tier A step to the newest batch. Worst case about 1,000 s: up to 600 s to the next commit, then Tier B and Tier A on the shared slot, then the load. |
| Watcher stopped or slow | `rule: eval_lag`, `severity: page` once the lag passes the limit. One page per episode; it re-arms when the lag drops back. |
| Planned failure (kill and restore) | A batch that starts at or below the last step before it is a restore to step R. The training after R was lost: it and the downtime don't count, so the planned failure doesn't page. The training up to R still counts, so a restore doesn't wipe out a lag that was building: a dead watcher still pages on time, and only once. While training is behind the newest Tier A step, the lag is 0. |
| Trainer pause | A gap between two batches counts as at most `--pause-s` (default: half an interval). |
| No Tier A row yet | The lag runs from the run's first batch. With `--run`, a run whose watcher never started pages at the limit. |
| Blank lines in `metrics.jsonl` | Ignored: `watch_jsonl.py` stores such a batch as steps 0..0, which would look like a restore to step 0. |
| Run finished or died | Not checked once its newest batch is older than `--live-s` (default: the limit). |
| Tier A on every k-th commit only | Pass `--intervals k+1`. |

Without `--run`, only training runs that have Tier A rows under the same run id are checked, so other streams never
page. `--interval-s` has no default: the main run's interval is not dry run 2's.

**Output.** A page is one JSON line on stdout with the keys of `alarms.py` events (`step`, `metric`, `rule`, `severity`,
`detail`, plus `run_id`, `eval_step`, `lag_s`, `threshold_s`). Each check prints a status line per run on stderr and
writes one row per run to `eval_lag_checks` (`clickhouse/eval_lag_checks.sql`, created on start; `--no-write` skips
it). A page row that fails to write is written with the next check, so Grafana never misses a page. `--once` exits 1
on a page and 2 on any error (never 1 for an error).

**Grafana.** TSAI returns job logs only after a job ends, so `eval_lag_checks` is how the lag shows during a run.
`grafana/private_v1.json` has three panels for it, below panel 28. They use their own variable, `$lag_run` (the runs in
`eval_lag_checks`), because `$eval_run` comes from `eval_mini` and so lacks a run whose watcher never started:

| Panel | Shows |
|---|---|
| 29, Eval-watcher lag | lag and limit per run, over time |
| 30, Lag alarm pages | each page, newest first |
| 31, Lag alarm: seconds since last check | red after 300 s (5 polls). The alarm writes a row every poll only while a run trains, so during training a growing number or "no check yet" means the alarm is not running |

**Running it.** Run one alarm per ClickHouse, for as long as training runs. It needs CPU only and the ClickHouse HTTP
URL with insert rights on `eval_lag_checks`; like `load_jsonl.py`, it sends no login, so the URL must not need one.
Each stderr line starts with the UTC time, and the first gives the settings. An error never stops `--poll`: a
ClickHouse error is one line, anything else is logged with its traceback, and the alarm tries again at the next poll.
A check reads the batches since the newest Tier A step (one batch per 10-step flush: a few dozen rows); before a
run's first Tier A row, and while a page is unresolved, that grows by 80 to 200 rows per hour of training (4.4 s or
1.9 s per step). Clock skew between the `watch_jsonl.py` host and the alarm host only shifts when a run counts as
training: the lag itself uses `seen_at` alone.

**Results** (`tests/test_eval_lag.py`, offline; checks every 30 s, every 60 s in the replay):

| Scenario | Pages | Largest lag (limit 1,200 s) |
|---|---|---|
| Dry run 2 shape: 1,221 steps at 4.4 s, watcher keeps up | 0 | 792 s |
| 6 hours, including the 10th commits (Tier B first) | 0 | 924 s |
| Watcher stops twice | 2, at lag 1,232 s each | - |
| Only Tier B and Tier C rows | 1 | - |
| Kill 594 s after a commit, 300 s down, resumed under a new or the same run id | 0 | 792 s (1,642 s if each step were timed when first reached, as `metrics_raw` keeps it) |
| Tier A dies, then the same kill and restore (before or after the page) | 1, on time; the restore doesn't re-arm it | - |
| Blank-line batches (steps 0..0) mixed in | same checks as without them | - |
| 15-minute trainer pause | 0 | 884 s (1,296 s counting the pause in full) |
| No Tier A row, with `--run` | 1, at lag 1,232 s | - |
| Real dry run 1 log at real pace through `watch_jsonl.Watcher`, killed at step 926, resumed from 612 into a new folder | 0 | 757 s |
| Same, Tier A stops after step 0 | 1, at lag 1,230 s | - |

**Limits.** Needs `watch_jsonl.py` streaming the run into the same ClickHouse. A run that ends with its last commit
unscored is not paged; the eval watcher's exit code covers that. The offline tests use a fake ClickHouse;
`test_live_clickhouse_end_to_end` runs the real loaders, the alarm, its table, the CLI and the panel queries on a real
ClickHouse when `CLICKHOUSE_URL` is set (`CLICKHOUSE_URL=http://127.0.0.1:8123 python -m pytest
teams/08-monitoring/alarms/tests/test_eval_lag.py -rs`, with ClickHouse as in `clickhouse/README.md` section 1).
