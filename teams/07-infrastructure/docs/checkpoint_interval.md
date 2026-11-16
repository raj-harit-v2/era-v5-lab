# Checkpoint interval

Week 3, core task 3. The interval is set from the measured save time and restore time. It replaces the
start value in [checkpoint_design_v0.md](checkpoint_design_v0.md) section 7 and the decision in section 13.

**Decision.**

```text
interval = min( max(Young, 10 min, 1.2 x save pipeline), 30 min )      Young = sqrt(2 x stall x MTBF)
```

- **Dry run 1: `INTERVAL_S=600` (10 min).**
- Main run: the same rule, re-run when the model size and the GPU count are fixed. With the numbers we have,
  it gives 10 min at 64 to 256 GPUs and up to 30 min on a single 8-GPU node.
- Retention follows the interval, so the rollback reach in minutes does not shrink (section 5).

**Status: provisional.** The save time is Team 6's week-1 baseline. Team 6's full-size save time is due Thu 19 Nov
(D5). It replaces these inputs, and the table in section 3 is generated again. The model sizes in config v1 are
still empty, so section 3 runs over 1B, 7B and 30B parameters.

## 1. Inputs

| Input | Value | Measured or assumed | Source |
|---|---|---|---|
| Stall per save (copy to host memory) | 37 ms for 445 MB, 67 ms for 829 MB: **12 GB/s** per GPU | measured, 1 GPU | Team 6 [baseline_v0.md](../../06-performance/results/baseline_v0.md), design section 13 |
| Background write and fsync | 1.9 s for 445 MB, 3.5 s for 829 MB: **0.24 GB/s** per GPU | measured, 1 GPU, local disk | same |
| Upload to the store | 10 GB/s per node | **assumed** ([prices.yaml](../metrics/prices.yaml)) | not measured yet |
| Restore | 0.03 to 0.08 s (tiny model, CPU), 0.71 s (tiny model, 1 GPU), 2.5 to 2.8 s per GB (synthetic, CPU) | measured | [runbook.md](runbook.md) section 8 |
| Restore, slow machine | 116 s for 1.6 GB, about 72 s per GB | measured, hosted CPU | [runbook_restore_restart_time_w3.md](runbook_restore_restart_time_w3.md) |
| MTTR (fault to first productive step) | 80 s | measured in the simulation (Q-20), tiny model, no download | [metrics.json](../support/simulation/results/metrics.json) |
| Failure rate | 9,921 and 50,677 GPU-hours per interruption | published priors | `MTBF_PRIORS` in [cost_model.py](../support/cost/cost_model.py) |
| Checkpoint bytes per parameter | 12 (fp32 weights 4 + two optimizer states 4 + 4) | upper bound | prices.yaml. Muon keeps one state, so about 8. 12 is used to stay on the safe side |

Only the stall stops training. The write, upload and commit run in the background (design section 5).

## 2. What the measured numbers change

Design section 7 says that Young's formula "alone would allow 1–5 h", so failures do not set the interval and the
30 min cap does. With the measured stall, that is not right. The stall is 0.003 s to 0.5 s per save, and the MTBF is
39 h to 6,300 h. Young's interval is then **0.5 to 27 min** at 64 GPUs or more. It is below 30 min in every case.
The cost report on main shows the same thing (`binding: young`, 6 to 12 min, [cost_report.md](../support/cost/cost_report.md)).

So saving more often is cheaper than 30 min. The gain is small at 64 GPUs and larger at 256 GPUs:

| | 30 min | 10 min | Young |
|---|---:|---:|---:|
| Time lost, 7B, 64 GPUs, S15 prior | 0.18% | 0.09% | 0.09% |
| Time lost, 7B, 256 GPUs, S15 prior | 0.70% | 0.28% | 0.28% |

At 256 GPUs, 0.4% of a two-week run is about 1.3 hours of the whole cluster.

**Why not save at Young's interval (1 to 5 min)?**

1. The upload to the store is not measured. A save every few minutes may not finish before the next one starts. The
   rule keeps the interval above 1.2 x the save pipeline, and the CK-10 alarm shows saves that queue up.
2. More saves mean more load on the store and more objects to clean up.
3. Below 10 min the extra gain is less than 0.1% in every case in section 3.

So the floor is 10 min. The cap stays 30 min, the most work we accept losing in one failure (about 15 min on average).

## 3. Table

12 bytes per parameter, sharded evenly over all GPUs. Stall = per-rank size / 12 GB/s. Pipeline = per-rank write at
0.24 GB/s + per-node upload at 10 GB/s. Time lost = stall / interval + (interval / 2 + MTTR) / MTBF, with MTTR 80 s.

| Params | GPUs | Failure prior | Per-rank GB | Stall s | Pipeline s | MTBF h | Young min | **Rule min** | Lost at 30 min | Lost at 10 min | Lost at rule |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1B | 8 | S15 reference run | 1.50 | 0.125 | 8 | 1,240 | 17.6 | **18** | 0.03% | 0.03% | 0.03% |
| 1B | 8 | Llama 3 | 1.50 | 0.125 | 8 | 6,335 | 39.8 | **30** | 0.01% | 0.02% | 0.01% |
| 1B | 64 | S15 reference run | 0.19 | 0.016 | 1 | 155 | 2.2 | **10** | 0.18% | 0.07% | 0.07% |
| 1B | 64 | Llama 3 | 0.19 | 0.016 | 1 | 792 | 5.0 | **10** | 0.04% | 0.02% | 0.02% |
| 1B | 256 | S15 reference run | 0.05 | 0.004 | 0 | 39 | 0.5 | **10** | 0.70% | 0.27% | 0.27% |
| 1B | 256 | Llama 3 | 0.05 | 0.004 | 0 | 198 | 1.2 | **10** | 0.14% | 0.05% | 0.05% |
| 7B | 8 | S15 reference run | 10.50 | 0.873 | 53 | 1,240 | 46.5 | **30** | 0.07% | 0.15% | 0.07% |
| 7B | 8 | Llama 3 | 10.50 | 0.873 | 53 | 6,335 | 105.2 | **30** | 0.05% | 0.15% | 0.05% |
| 7B | 64 | S15 reference run | 1.31 | 0.109 | 7 | 155 | 5.8 | **10** | 0.18% | 0.09% | 0.09% |
| 7B | 64 | Llama 3 | 1.31 | 0.109 | 7 | 792 | 13.1 | **13** | 0.04% | 0.03% | 0.03% |
| 7B | 256 | S15 reference run | 0.33 | 0.027 | 2 | 39 | 1.5 | **10** | 0.70% | 0.28% | 0.28% |
| 7B | 256 | Llama 3 | 0.33 | 0.027 | 2 | 198 | 3.3 | **10** | 0.14% | 0.06% | 0.06% |
| 30B | 8 | S15 reference run | 45.00 | 3.742 | 226 | 1,240 | 96.3 | **30** | 0.23% | 0.63% | 0.23% |
| 30B | 8 | Llama 3 | 45.00 | 3.742 | 226 | 6,335 | 217.7 | **30** | 0.21% | 0.63% | 0.21% |
| 30B | 64 | S15 reference run | 5.62 | 0.468 | 28 | 155 | 12.0 | **12** | 0.20% | 0.15% | 0.14% |
| 30B | 64 | Llama 3 | 5.62 | 0.468 | 28 | 792 | 27.2 | **27** | 0.06% | 0.09% | 0.06% |
| 30B | 256 | S15 reference run | 1.41 | 0.117 | 7 | 39 | 3.0 | **10** | 0.71% | 0.29% | 0.29% |
| 30B | 256 | Llama 3 | 1.41 | 0.117 | 7 | 198 | 6.8 | **10** | 0.14% | 0.07% | 0.07% |

Reading it:

- At 64 GPUs or more the rule gives 10 to 27 min. A fixed 10 min is never more than 0.03% worse than the rule there.
- On one 8-GPU node failures are rare, so the rule gives 18 to 30 min. A 30B model on 8 GPUs has a large stall
  (3.7 s); 10 min would cost 0.4% more there.
- The stall is at most 3.7 s, far under the 2% budget at any interval in the table (12 s at 10 min).
- The pipeline is at most 226 s (30B on 8 GPUs), under the 10 min floor. The rule's 1.2 x pipeline floor only
  matters if the measured upload is far slower than the assumed 10 GB/s.

Restore time does not move the interval. Young's formula has no restore term. A slower restore adds the same time
to every failure at any interval. At 72 s per GB (the slowest machine measured), a 5.6 GB rank adds about 400 s per
failure. That is a CK-13 matter (LOW 600 s), not an interval one.

To generate the table again (from `teams/07-infrastructure/`; change the four inputs on the first line when Team 6
posts the full-size numbers):

```bash
python - <<'EOF'
import sys; sys.path.insert(0, "support/cost"); from cost_model import young, waste_share, MTBF_PRIORS
COPY, WRITE, UPLOAD, MTTR = 445e6 / 0.037, 445e6 / 1.878, 10e9, 80.0
for P in (1e9, 7e9, 30e9):
    for G in (8, 64, 256):
        for name, gph in MTBF_PRIORS.items():
            rank = P * 12 / G; stall = rank / COPY; pipe = rank / WRITE + rank * 8 / UPLOAD; mtbf = gph / G * 3600
            y = young(stall, mtbf); T = min(max(y, 600, 1.2 * pipe), 1800)
            print(f"{P/1e9:.0f}B {G} {name}: young {y/60:.1f} min, rule {T/60:.0f} min, "
                  f"lost {waste_share(1800, stall, MTTR, mtbf):.2%} / {waste_share(600, stall, MTTR, mtbf):.2%} / {waste_share(T, stall, MTTR, mtbf):.2%}")
EOF
```

## 4. Dry run 1

**`INTERVAL_S=600`.** This is the floor, on purpose. TSAI may run dry run 1 on one node or at small width, where the
rule would allow more (section 3, 8-GPU rows). Up to 7B on one node, 10 min costs at most 0.08% more there. It gives three times as many
saves to measure (stall, write, commit) and more COMPLETE checkpoints for the restore drill (core task 5).

Where the value goes:

| Place | Setting |
|---|---|
| Main-run job | `INTERVAL_S=600` in the job's `--export` ([slurm/mainrun.sbatch](../slurm/mainrun.sbatch) defaults to 1800) |
| Live alarms | `metrics/watch.py --interval-s 600` |
| Run report | `metrics/evaluate.py --interval-s 600` |
| A step-based trainer | save every `ceil(600 / step seconds)` steps, from the step time of the first 50 steps |

`watch.py` and `evaluate.py` default to 1800. Pass 600 to both: CK-14 counts the work lost in units of the interval,
so a wrong value makes it read three times too low.

What to read from dry run 1:

1. `save_seconds.stall` on every `checkpoint.committed` event, against 2% of 600 s = 12 s.
2. Time from `checkpoint.started` to `checkpoint.committed`, against 600 s. CK-10 (save backpressure) must stay at 0.
3. `restore_s` and CK-13 from the restore drill.

If any of these is out of bounds, the interval goes up, not the budget.

## 5. Retention

Today: `ckpt.py retention --keep 3 --protect-every 5`. At 30 min that keeps the last 90 min and one protected
checkpoint every 2.5 h. At 10 min the same counts keep only the last 30 min. A bad checkpoint or a loss spike found
late may need an older one ([runbook.md](runbook.md)). So the counts scale with the interval, and the reach in
minutes stays the same:

| Interval | `--keep` | `--protect-every` | Reach | Protected |
|---:|---:|---:|---|---|
| 30 min (before) | 3 | 5 | last 90 min | every 2.5 h |
| **10 min** | **9** | **15** | last 90 min | every 2.5 h |

The cost: the store holds 9 recent checkpoints instead of 3, so recent-checkpoint storage triples (7B at 12 bytes
per parameter: 756 GB instead of 252 GB). Protected storage per month does not change, because the spacing is the
same. If the store cannot take it, `--keep 6` (last 60 min, 504 GB at 7B) is the fallback. Team 9 sets the protected
cadence; this keeps their 2.5 h spacing until they name a step count.

## 6. Open items

| Item | Owner | When |
|---|---|---|
| Full-size save time (stall, write, size per rank); generate section 3 again | Team 6 | Thu 19 Nov (D5) |
| Upload and commit time on the real store (the 1.2 x pipeline floor) | dry run 1, events | Wed 18 to Fri 20 Nov |
| Model size and GPU count for the main run | Team 5 config, TSAI layout at Gate 3 | Sat 21 Nov |
| MTBF measured on our nodes, in place of the published priors | dry run 1 and later | after Gate 3 |
| Design section 7 and section 13 to point here | checkpoint owner | with this PR's review |
