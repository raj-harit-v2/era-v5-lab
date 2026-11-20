# G7 week 3 rotation: dry run 1, steps 916-1221 (smitasasindran)

Work order tasks R1 (review dry run 1 from the returned logs) and R2 (log each failure and each restart).
There was no live shift: dry run 1 finished on 16 Nov (#475), so R1 is an offline review of the logs for the step
range, **steps 916 to 1221**.

**Status (19 Nov):** R1 and R2 done. The full-run logs were published in `2026-11-15-dryrun1-full/` (#620), so
R1 is checked from the per-step data for steps 916-1221.

## The run

| Item | Value | Source |
|---|---|---|
| Job request | `teams/05-architecture/jobs/2026-11-15-dryrun1.md` | #475, merged 16 Nov |
| Run ID / output | `dryrun1-1234`, `./out/dryrun1-1234/` | job request |
| Trainer | `teams/05-architecture/harness/train_week2.py`, Team 5's trainer | #475 |
| Arm and size | exp2_muon at T2, muon_lr 0.01, seed 1234 | TSAI result on #475 |
| Tokenizer | p1536, sha256 `e6b93a93...a64b` (the job request names frozen C3, `15468e66...`) | TSAI result on #475 |
| Steps / status | 1221 of 1221, COMPLETED | TSAI result on #475 |
| Final train cross-entropy / gradient norm | 4.8906 / 0.7037 (step 1221) | TSAI result on #475 |
| Held-out val/bpb | 1.5159 (English 1.9844, code 1.8901, Indic mean 1.3289, three-group 1.7345); same arm with tokenizer v0: 1.6443 | TSAI result on #475 |
| NaN / inf in loss record | none | TSAI result on #475 |
| Checkpoint | one `checkpoint.pt` at the last step (about 2.2 GB), kept by TSAI | TSAI result on #475 |

## R1: steps 916-1221

### Logs used

`teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/` (added in #620, a follow-up to #475):
`metrics.jsonl` (1222 rows: step 0 plus steps 1 to 1221), `losses.txt`, `total_losses.txt`, `manifest.json`,
`summary.json` (COMPLETED, 1221 steps, `wall_seconds` 2481, `final_model_sha256` `93e5f454...1981`). The first
evidence folder, `2026-11-15-dryrun1`, is only the 3-step smoke run and was not used. 

### Findings for steps 916-1221

| Check | Finding | Verdict |
|---|---|---|
| Step continuity | All 306 steps present exactly once, in order; last step 1221 | PASS |
| Finite values | `train/ce_loss`, `gradient_norm`, `tokens_per_second`, `perf/step_ms`, `lr` finite on every step | PASS |
| `losses.txt` vs `metrics.jsonl` | All 1221 lines of `losses.txt` equal `train/ce_loss` | PASS |
| Loss spikes | None. Cross-entropy falls slowly: mean 5.75, 5.66, 5.57 over the three thirds of the range (916-1017, 1018-1119, 1120-1221). The loss is noisy step to step (median change 0.44, largest 1.66; range 4.29 to 7.06) with no run of rising loss. Last step 4.8906. | PASS |
| Gradient norm | Median 0.76, min 0.48, max 3.06 (step 1143). 65 of 306 steps (21%) were clipped at 1.0; clipping is steady across the range (25, 18, 22 per third). The spike rule flags 17 steps (22 are above 1.5), scattered, and the loss does not rise afterwards (mean loss over the next 5 steps 5.62, range median 5.69). Median is lower than earlier ranges (1.14, 0.92, 0.82 for 1-305, 306-610, 611-915). | PASS, with an observation: 17 isolated spike-rule steps, up to about 4x the median |
| Throughput | `perf/step_ms` median 1894 ms, min 1656, max 2401 (step 1148); no step slower than 1.5x the median. `tokens_per_second` median 8652, min 6825, max 9894; 17 steps are more than 10% below the median, isolated or in short groups (for example 1148-1150) with none lasting 100 steps. GPU memory flat at 3.54 to 3.56 GiB. | PASS |
| Held-out evals in range | One, at step 1221: val/bpb 1.5159 (the earlier evals are at step 0, 2.5052, and step 611, 1.6217) | Informational |
| Team 8 alarms, offline | 0 alarms at the `alarms.py` defaults (see "Window setting" below) | PASS, with a note |

**How the verdicts were set:** Continuity, finite values and the `losses.txt` match are exact checks. For the others,
the rules below were used (not a team standard):
- A loss or gradient-norm spike is a step above the median of the previous 20 steps by more than 6 robust standard
  deviations (1.4826 × median absolute deviation, floor 5% of the median).
- A slow step is one above 1.5× the median step time, and a throughput drop is a step more than 10% below the median
  tokens per second.

Loss and throughput have no flags that persist. Gradient norm is marked PASS although the spike rule flags 17 steps,
because they are isolated, the loss does not rise after them, and Team 8's `alarms.py` (stricter: 7σ over a trailing
1000 steps) fired no alarm in the range at its defaults (see "Window setting" below).

### Team 8 alarms, offline

`alarms.py` was run over the whole `metrics.jsonl` (so the 1000-step trailing window is warm), with the default
settings (`ema_z` is off by default):

```bash
python -I teams/08-monitoring/alarms/alarms.py \
    --jsonl teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl
```

It read 1222 rows and fired 3 alarms in the whole run, all `spike_score` (page) on `gradient_norm`: step 468
(5.30, 8.0 sigma), step 505 (4.74, 7.0 sigma) and step 841 (4.99, 8.3 sigma). All three are outside this report's range
(steps 306-610 and 611-915). No `non_finite`, `throughput_drop` or `moe_routing` alarm fired. The alarms were not
hooked into the live run, so this is a replay of the logs.

**Window setting.** 0 alarms with the `alarms.py` defaults (window 1000). With the 100-step window in
`alarms_dryrun1.md`, step 1079 (`gradient_norm` 3.00, about 7.3σ) would page; Team 8 to confirm which window is
right. With a 100-step window the whole file gives 7 alarms (steps 173, 239, 468, 505, 532, 841, 1079); step 1079
is the only one in steps 916-1221. Checked with `AlarmMonitor(window=100)` in place of the default.

### R1 result

Steps 916-1221 are continuous, finite and match `losses.txt`. There are no loss spikes and no Team 8 alarm at the default settings (see "Window setting" above for
the one open question). The gradient norm is lower and calmer than in the earlier ranges, but 21% of steps are still clipped and there are
isolated norms up to 3.06. Throughput is steady. Nothing in this range needs a restart or a rerun.

### Reproduce

The checks above come from `rotation_r1_check.py` (standard library only), and `plot_run.py` (needs matplotlib)
draws a chart of the range. Both are kept in a gist, pinned to one revision so the steps cannot change under this
report: <https://gist.github.com/smitasasindran/b514ee78252d26689901565eb500e0d0/9ab4dd5400710dd932c40c322e967009650d4276>.
The chart image is in the gist; it is not committed to the repository. Download the scripts, then run from the root
of the `era-v5-lab` repository:

```bash
python3 -I rotation_r1_check.py \
    --metrics teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl \
    --start 916 --end 1221 --expected-last 1221
python3 plot_run.py teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl \
    --start 916 --end 1221 --title "Dry run 1"
```

`rotation_r1_check.py` prints the continuity, finite-value, loss, gradient-norm, throughput, evaluation and Team 8
alarm results for the range. `plot_run.py` writes the chart (PNG) and a CSV of the range.

## R2: failures and restarts

### Dry run 1

| # | Time / step | Event | Cause | Action | Restored from | Steps lost |
|---|---|---|---|---|---|---|
| none | | | | | | |

- Failures: **0**. Restarts: **0**. 1221 of 1221 steps, COMPLETED, no NaN or inf (TSAI result on #475).
- The full-run `metrics.jsonl` agrees: steps 0 to 1221 appear once each, in order, with no gap, repeat or step going
  backwards, and every loss and gradient norm is finite. A restart would leave a gap or a repeat.
- Dry run 1 did not run under `ckpt/supervisor.py` and did not use the Checkpointer. It saved one checkpoint at
  the last step. So it gives **no evidence** for "only COMPLETE checkpoint restarts".

### Restore drill on the final checkpoint (#491; results in #573), run by TSAI on 17 Nov

Numbers are from TSAI's result note as written in `restore_dryrun1.md`, section 5. The job outputs were not added
to the repository.

| Check | Job A: restore final checkpoint | Job B: stop at 610, restore, continue |
|---|---|---|
| Exit code, no identity error (C1) | 0 | resume run 0 |
| `steps` / `status` (C2) | 1221 / COMPLETED | stop run 610 / INCOMPLETE_NOT_A_RESULT; resume run 1221 / COMPLETED |
| `final_model_sha256` equals dry run 1 (C3) | yes | yes |
| `losses.txt` equals dry run 1, bit for bit (C4) | yes, 1221 of 1221 lines | yes, 1221 of 1221 lines |
| Every step present (C5) | n/a | yes in `losses.txt` (1221 lines, line for line); `metrics.jsonl` not compared (TSAI, 18 Nov) |
| Stop run equals dry run 1 up to step 610 (C6) | n/a | yes, no run-to-run noise |
| Job start to exit | about 6 min 8 s | about 30 min 39 s (includes 611 training steps) |
| Result | PASS | PASS |

**What it shows**: the saved checkpoint loads and gives back the same model, and a run stopped at step 610 and
restored finishes bit-for-bit like the run that was never stopped. What it does not show: both jobs restored from
a checkpoint saved after a clean stop, not after a kill, and `train_week2.py` writes `checkpoint.pt` directly with
no COMPLETE marker. The COMPLETE-only restart after a kill is shown by the Team 07 restart test
([restart_cpu.txt](restart_cpu.txt), [restart_node.txt](restart_node.txt)). TSAI agrees that the week-5 main run
should save through the `Checkpointer`.

## Open items

- [x] R1: steps 916-1221 checked from the full-run logs (#620).
- [x] R2: no failures, no restarts; restore drill (#491, #573) recorded.

## References

- Dry run 1: #475; full-run logs: #620. Restore drill: #491 (plan and job requests), #573 (results).
- Team 8 alarms: `teams/08-monitoring/alarms/alarms.py`.
