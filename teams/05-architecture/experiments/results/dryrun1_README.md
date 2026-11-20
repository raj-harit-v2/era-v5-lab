# Dry run 1 loss record: how it is made

**Owner:** Deepjyoti Saha (G5, week-3 task 4). **Written:** 15 Nov 2026, before dry run 1 ran.

This folder holds G5's evidence for Gate 3's "dry run 1 ends with a stable loss curve".

> [!WARNING]
> **🧪 Files marked SAMPLE are for testing and illustration only. They are not dry run 1.**
> `dryrun1_loss_sample_attn0.md` and everything it uses (its two charts, `dryrun1_sample_log.jsonl` and
> `dryrun1_make_sample_log.py`) take a real week-2 log and **inject** spikes, stops and rollbacks into a copy of it,
> so the method can be tested, and reviewers can see a fully filled record, before dry run 1's logs exist.
> The injected events never happened. The real record is `dryrun1_loss.md`; it is filled only from dry run 1's
> own logs.

| File | What it is |
|---|---|
| [`dryrun1_loss.md`](dryrun1_loss.md) | **The record** (Gate 3 evidence): what ran, the loss curve, every spike, stops and restarts, and whether the curve is stable. Layout only until dry run 1's logs arrive. |
| [`dryrun1_spikes.py`](dryrun1_spikes.py) | The script that finds every spike, stop and restart with both lab rules, prints the record's tables and draws its charts. Standard library only. |
| [`dryrun1_loss_sample_attn0.md`](dryrun1_loss_sample_attn0.md) | 🧪 **SAMPLE**: the record filled in end to end, from the real attn-0 week-2 log with injected events (section 4). |
| [`dryrun1_loss_sample_attn0.svg`](dryrun1_loss_sample_attn0.svg) | 🧪 SAMPLE: its loss chart (numbered spikes, stops, the spans run again after each rollback). |
| [`dryrun1_loss_sample_attn0_spikes.svg`](dryrun1_loss_sample_attn0_spikes.svg) | 🧪 SAMPLE: a close-up of every spike with both rules' lines. |
| [`dryrun1_make_sample_log.py`](dryrun1_make_sample_log.py) | 🧪 SAMPLE: makes the sample log from the real attn-0 log; lists every injected event. |
| [`dryrun1_sample_log.jsonl`](dryrun1_sample_log.jsonl) | 🧪 SAMPLE: the sample log it makes (1,324 rows, 3 attempts). |
| `dryrun1_README.md` | This file: the method, the decisions behind it, and how the sample was made. |

## 1. What a spike is in this lab: two rules

The lab has two definitions, owned by two teams, with different consequences. They catch different things (see
section 4), so the record reports both, one column each.

| Rule | Owner and code | Watches | Condition | What it does |
|---|---|---|---|---|
| `spike_score` | Team 8, [`teams/08-monitoring/alarms/alarms.py`](../../../08-monitoring/alarms/alarms.py) | `loss_ntp`, `loss_mtp`, `gradient_norm` | at or above the mean + 7 standard deviations of the last 1,000 clean steps (active after 100 steps); a spike step is not added to the window | pages a person; the run continues |
| `non_finite` | Team 8, same file | any metric | NaN or infinity | stop |
| loss guard | Team 7, [`teams/07-infrastructure/support/simulation/trainer/train.py`](../../../07-infrastructure/support/simulation/trainer/train.py) ("loss-spike guard", ADR 0001 §6) | `loss_ntp` | above 1.5 × the median of the last 100 clean losses (active once 50 are in the window); a spike step is not added; 3 in a row, or a NaN | stops the run: no save, exit 78, the job is held until a person rolls back ([`USER_GUIDE.md`](../../../07-infrastructure/USER_GUIDE.md) §1.5, §5.4) |

Team 8's `alarms_dryrun1.md` describes `spike_score` as a "trailing 100-step z-score"; the code it runs,
`AlarmMonitor()` with its defaults, uses a 1,000-step window that becomes active after 100 steps. This record follows the
code.

The script imports Team 8's `AlarmMonitor` unchanged and copies Team 7's guard with its defaults
(`--spike-ratio 1.5`, `--spike-window 100`, `--spike-steps 3`), so both rules are exactly the ones the lab runs.
Both run inside the trainer, so both start empty after every restart; the script does the same.

**In dry run 1 neither rule runs inside the job.** Dry run 1 runs `train_week2.py` directly
([#475](https://github.com/theschoolofai/era-v5-lab/pull/475)), and that trainer has no loss guard and no Team 8
monitor; it stops only on a NaN or infinite value, with an error, before that step's row is written. So the record
applies both rules to the returned `metrics.jsonl` and reports what each **would** have done. The script reads that
trainer's fields as they are: its smoke log in `jobs/evidence/2026-11-15-dryrun1/metrics.jsonl` has every field the
script uses, and the script reads it unchanged.

## 2. How to run it

From the repository root:

```bash
python -I teams/05-architecture/experiments/results/dryrun1_spikes.py --jsonl <metrics.jsonl> [<more.jsonl> ...]
python -I teams/05-architecture/experiments/results/dryrun1_spikes.py --jsonl <path> --out tables.md --svg chart.svg --spike-svg spikes.svg --title "Dry run 1"
```

It reads one or more `metrics.jsonl` files in order (one JSON object per step: `step`, `loss_ntp`, `loss_mtp`,
`gradient_norm`, `lr`, `tokens_per_second`, and `val/bpb` on evaluation steps), and skips the week-2 harness's
evaluation-only step 0. A new **attempt** starts at each new file and wherever the step number goes back (a rollback).
It prints Markdown, headed by each log's sha256:

- **the loss curve** along the kept path (for each step, the last attempt that ran it): the first step, about
  `--rows` rows (on the held-out evaluation steps when the log has them), the last step; a 50-step moving average
  column shows the trend through the noise of single batches;
- **every spike**, numbered: both rules side by side; when a rule did not fire, its line at that step, so the
  margin is visible; and what the log shows at the next step;
- **attempts, stops and restarts**: each attempt's steps, how it ended (Team 7 stop, NaN, or the log just ends) and
  where the next one resumed, with the steps run again;
- **a summary** with the numbers the stability paragraph quotes.

`--svg` draws the loss chart (numbered spikes coloured by rule, stops, spans run again); `--spike-svg` draws a
close-up of every spike with Team 7's and Team 8's lines. It changes no file it reads and writes no `__pycache__`.
Who was paged, what they did, and a requeue that loses no step (exit 75) are not in the metrics: they are added by
hand from the job log and the shift log.

## 3. Decisions behind the record

| # | Decision | Chosen | Why |
|---|---|---|---|
| A0 | The Muon rate to cite | `muon_lr` 0.01 | TSAI in the G5 group, 15 Nov; config v1 leaves it unset on purpose |
| A1 | Which spike rule leads | both, one column each | Team 7's guard decides whether the run stops; Team 8's rule is the lab's spike definition |
| A2 | Commit the script | yes | anyone can rerun the record on the same logs |
| A3 | Curve detail | about 20 rows plus every spike, and a chart | readable, and no spike is left out |
| A4 | Held-out bits per byte | included as a column when the logs have it | a falling held-out score supports "stable" |
| A5 | Late logs or a held run | file what exists by Friday and say what is missing | a record of a held run is still evidence |

## 4. 🧪 The sample: testing and illustrating the method

> [!NOTE]
> This section is about the **sample**, not dry run 1. Its purpose is to test the script on every kind of event and
> to show reviewers a fully filled record before dry run 1's logs exist.

[`dryrun1_loss_sample_attn0.md`](dryrun1_loss_sample_attn0.md) is `dryrun1_loss.md` filled in completely. The log
behind it is the real T2 reference run of the 10 Nov attention screen,
[`jobs/evidence/2026-11-10-attention-screen/attn-0/`](../../jobs/evidence/2026-11-10-attention-screen/attn-0/)
(1,221 steps, the same field names dry run 1 is expected to write). That run was calm (one gradient spike, no
stop), so [`dryrun1_make_sample_log.py`](dryrun1_make_sample_log.py) injects four events into a copy of it:

| Injected event | Step | What the rules do |
|---|---:|---|
| `loss_ntp` doubled for one step | 300 | Team 7 counts one spike, no stop; Team 8 does not page |
| a preemption (exit 75, saved, requeued) | 520 | nothing: only in the job log |
| `loss_ntp` doubled three steps in a row | 700–702 | Team 7 stops at 702 (exit 78); rolled back to step 650 |
| `loss_ntp`, `loss_mtp`, `gradient_norm` NaN | 950 | both stop; rolled back to step 900 |

How the sample was made:

| Section | Filled from |
|---|---|
| 1. What ran | by hand, from `command.json`, `manifest.json`, `summary.json`, `environment.json`, the job request and the screen's README |
| 2, 3, the attempts table in 4, the summary in 5, both charts | the script, unchanged output (command below) |
| 3. Details of each spike, 4. the job-log table | by hand, quoting only numbers in the script's output; 🧪 the job-log parts are illustrative |
| 5. The paragraph and the lessons | by hand, quoting only numbers in the script's output |

To remake it:

```bash
python -I teams/05-architecture/experiments/results/dryrun1_make_sample_log.py
python -I teams/05-architecture/experiments/results/dryrun1_spikes.py --jsonl teams/05-architecture/experiments/results/dryrun1_sample_log.jsonl --title "SAMPLE for illustration (attn-0 log with injected events)" --svg teams/05-architecture/experiments/results/dryrun1_loss_sample_attn0.svg --spike-svg teams/05-architecture/experiments/results/dryrun1_loss_sample_attn0_spikes.svg
```

What the sample found:

- **On the real log alone**, unchanged: one Team 8 `spike_score` page, `gradient_norm` 4.873 at step 1085 (14.3σ
  above the trailing mean of 0.865; line 2.83), back to 0.586 at the next step. Team 8's own `alarms.py --jsonl` on
  the same file reports the same single alarm. Team 7: no spike. No stop.
- **Team 7's guard caught every injected loss spike; Team 8's rule caught none of them.** At step 300 the spike was
  13.56, Team 7's line 10.86, Team 8's line 13.69: early in a run Team 8's 1,000-step window still holds the fast fall
  of the loss, so its σ is large. Team 7 never looks at the gradient norm, which only Team 8 watches.
- **After a restart Team 8 pages more.** Its monitor starts empty with the trainer; 118 steps after the restart at
  step 901 its line was 2.35 instead of 2.83, so gradient bumps of 2.82 (step 1019) and 2.28 (step 1158) paged, which
  did not page in the real run.
- **A requeue that loses no step is invisible in the metrics**, so the job log must be among the returned logs.

For dry run 1 the same script runs on its own logs; the parts added by hand are "who was paged and what they did"
(Team 8's alarm output, the shift log) and the job-log rows of the stops table.

## 5. Where the dry run 1 numbers come from

- **Job request:** [#475](https://github.com/theschoolofai/era-v5-lab/pull/475) (Shivanshu, merged 16 Nov). Its evidence
  folder `jobs/evidence/2026-11-15-dryrun1/` holds only the 3-step smoke run filed with the request.
- **The full run:** [#620](https://github.com/theschoolofai/era-v5-lab/pull/620) (TSAI, 18 Nov) added
  `jobs/evidence/2026-11-15-dryrun1-full/`: `metrics.jsonl` (one row per step, 0 to 1221), `losses.txt`,
  `total_losses.txt`, `summary.json` (COMPLETED, 1,221 steps) and `manifest.json` (p1536, `muon_lr` 0.01, seed 1234).
  `dryrun1_loss.md` is filled from these files with the command in its Sources section.
- Held-out bits per byte was scored at steps 0, 611 and 1221 only (`eval_every_steps` 611 in the run's runtime file),
  so the held-out column has three values.
