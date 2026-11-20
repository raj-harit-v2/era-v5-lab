# G7 Week 3 — Infrastructure Rotation (R1/R2)

**Owner:** @AJJAPUSIVA  
**Team:** 07 — Infrastructure  
**Week:** 3  
**Report updated:** 18 November 2026  
**Status:** R1 evidence analyzed for steps 1–305; R2 restore drill results documented

## Assignment

| Task | Assignment | Status |
|---|---|---|
| R1 | Offline review, Dry Run 1 steps 1–305 | PASS — full-run evidence and G8 CLI verified |
| R2 | Failure, restart and restore evidence audit | TSAI restore-drill results documented |
| Gate 3 | Evidence due 20 November 2026 | Follow-up submitted; lead review in progress |

Dry Run 1 completed on 16 November 2026 under G5 PR #475. The G7 acting lead confirmed that there was no live monitoring shift. The R1 assignment is an offline review of the finished run.

## R1 — Offline Monitoring, Steps 1–305

### Evidence and method

- Original run: https://github.com/theschoolofai/era-v5-lab/pull/475
- Full-run evidence (merged): https://github.com/theschoolofai/era-v5-lab/pull/620
- Source directory: `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/`
- Inspected: `metrics.jsonl`, `losses.txt`, `summary.json`, and manifest metadata
- Alarm implementation: `teams/08-monitoring/alarms/alarms.py`
- Range: all training rows where `1 <= step <= 305`; excludes the separate validation row at step 0
- Analysis date: 18 November 2026

**Important:** These are actual full-run TSAI records from #620, not the earlier three-step smoke evidence. The alarm findings below are from checking the published default rule logic against the retrieved data. 

### R1 checks and findings

| Check | Finding | Assessment |
|---|---|---|
| Step continuity | 305 rows for steps 1–305, with no missing or duplicate step numbers | PASS |
| Loss trend | `loss_ntp` 11.9148 at step 1 to 6.1834 at step 305 (48.1% lower) | Overall downward trend |
| Loss spikes | Largest single-step increases at steps 190 (+2.1692), 38 (+1.8741), 86 (+1.4054); none meets the G8 default 7-sigma alarm in this range | Transients observed, no default alarm |
| Gradient norm | Median 1.1366; highest 4.6942 at step 173, then 4.6378 at step 239 | Elevated points; no non-finite values |
| Non-finite values | None found among the numeric R1 metrics | PASS |
| Throughput | Median 8,645.5 tokens/s; first step is slower (3,698.1 tokens/s); max 9,914.6 at step 96 | No sustained drop |
| G8 default rules | Equivalent evaluation of published `AlarmMonitor` defaults on steps 1–305 produced 0 alarms; longest throughput-drop streak was 2, below the required 100 | PASS — official CLI: exit 0, 305 steps, 0 alarms |
| G8 alarm-window comparison | **0 alarms** with `alarms.py` defaults (`window=1000`); **2 page alarms** with `window=100`: step 173 (`gradient_norm`, 7.57σ) and step 239 (`gradient_norm`, 7.70σ). Team 8 to confirm which window applies. | Gate 3 configuration discrepancy |
| MoE routing alarm | No `expert_load` field is present in these rows | Cannot evaluate routing health |

### Loss details

| Metric | Value |
|---|---:|
| Step 1 loss | 11.914753 |
| Step 305 loss | 6.183450 |
| Minimum loss | 5.234341 at step 298 |
| Mean loss | 7.393319 |
| Median loss | 7.269575 |
| Average, first 50 steps | 8.949824 |
| Average, last 50 steps | 6.693378 |

The training loss is noisy, not monotonically decreasing. The isolated increases noted above do not automatically imply a training failure, and G8's default loss-spike rule did not flag them.

### Gradient norm details

| Metric | Value |
|---|---:|
| Mean gradient norm | 1.294253 |
| Median gradient norm | 1.136629 |
| Minimum | 0.715066 at step 122 |
| Maximum | 4.694226 at step 173 |
| Other elevated observation | 4.637811 at step 239 |
| `gradient_clipping_applied` true | 222 of 305 rows |

The spike detector uses a 7-sigma threshold after a 100-value warm-up. The Python default trailing window is 1,000; Team 8's written `alarms_dryrun1.md` specifies a 100-step trailing window. The highest gradient z-score in the evaluated range was approximately **6.85 at step 173**, below that threshold **with the default 1,000-step window**. The second highest was approximately **6.29 at step 239** under that same default. With the written 100-step window, the script instead emits page alarms at steps 173 (7.57σ) and 239 (7.70σ). No NaN or Inf was observed. The reported clipping flag is copied from the log and does not by itself establish an alarm or a failure.

### Throughput and step time

| Metric | Value |
|---|---:|
| Median `tokens_per_second` | 8,645.55 |
| Mean `tokens_per_second` | 8,604.51 |
| Minimum throughput | 3,698.13 at step 1 |
| Maximum throughput | 9,914.65 at step 96 |
| Median `perf/step_ms` | 1,895.08 ms |
| Maximum step duration | 4,430.35 ms at step 1 |
| G8 slow-throughput patience | 100 consecutive steps |
| Maximum slow-throughput streak under default logic | 2 steps |

The initial training step is slower than the typical step. Other temporary throughput dips occurred, but the default G8 rule did **not** find the sustained 100-step low-throughput streak needed to fire an alarm.

### Team 8 alarms — method and limitations

The published Team 8 `AlarmMonitor` implementation defaults to `window=1000`, while the written `teams/08-monitoring/alarms_dryrun1.md` specifies a 100-step spike window. The implemented defaults are: non-finite check; 7-sigma spike score with minimum 100 prior values; throughput below 90% of a trailing 100-step mean for 100 consecutive steps; optional EMA/static-bound rules disabled; and MoE routing requiring an `expert_load` field.

Applying this default rule logic to the extracted 305 training rows produced **0 alarms**, including **0** `non_finite`, **0** `spike_score`, and **0** `throughput_drop`. The official Team 8 `alarms.py` CLI was executed locally on 18 November 2026 against the TSAI full-run training records for steps 1–305. Execution completed with exit code 0, processing 305 steps and reporting 0 alarms. MoE routing health remains unverified because `expert_load` was not recorded.

To reproduce against the merged full-run evidence from the repository root:

```bash
mkdir -p out/g7_siva
python3 - <<'PY'
import json
from pathlib import Path
src = Path("teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl")
dst = Path("out/g7_siva/metrics_steps_1_305.jsonl")
rows = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
chosen = [r for r in rows if isinstance(r.get("step"), int) and 1 <= r["step"] <= 305]
assert len(chosen) == 305
assert sorted(r["step"] for r in chosen) == list(range(1, 306))
dst.write_text("".join(json.dumps(r) + "\n" for r in chosen))
print(f"Saved {len(chosen)} R1 training rows to {dst}")
PY
python3 teams/08-monitoring/alarms/alarms.py \
  --jsonl out/g7_siva/metrics_steps_1_305.jsonl \
  > out/g7_siva/alarms.txt 2> out/g7_siva/alarms_summary.txt
cat out/g7_siva/alarms_summary.txt
cat out/g7_siva/alarms.txt
```

A second direct `AlarmMonitor(window=100)` replay of the same 305 rows emitted **2 page alarms**, both `spike_score` on `gradient_norm`: step 173 (7.57σ) and step 239 (7.70σ). Team 8 must resolve the window-policy discrepancy. The spike detector only looks backward, so replaying the slice starting at step 1 produces the same results for steps 1–305 as processing those steps from the full run. Steps 1–100 cannot raise a spike alarm because the detector needs 100 prior values.

The CLI defaults may differ from G8's written alarm rule table; conclusions above describe **the implemented Python defaults**, not an alternative configuration. Routing alarms cannot fire without `expert_load` input.

### R1 conclusion

**Steps 1–305 are contiguous and complete in the released log.** Loss is lower at step 305 than at step 1 despite short-term fluctuations. Numeric records are finite, and there is no sustained throughput-drop alarm under the implemented defaults. Gradient peaks at steps 173 and 239 do not trigger the 1,000-step default rule but **both trigger** the documented 100-step window rule. The official Team 8 CLI completed successfully with 0 alarms.

## R2 — Failure and Restart Audit

### Original Dry Run 1

Based on instructor and G7 team updates:

- The original run completed 1,221/1,221 steps.
- Zero failures or restarts were reported.
- The run used Team 05's `train_week2.py`, not the G7 supervisor or Checkpointer.
- Only the final checkpoint was used; no periodic COMPLETE-only checkpoints or `commits.jsonl` were generated.

The original run does not demonstrate actual failure recovery or G7 COMPLETE-only restart behavior.

### Separate TSAI Restore Drill — PRs #491 and #573

- Plan: https://github.com/theschoolofai/era-v5-lab/pull/491
- Merged results: https://github.com/theschoolofai/era-v5-lab/pull/573

**Job A — final checkpoint restore:** exit 0, step 1,221, COMPLETED, final model SHA-256 matched original, 1,221/1,221 `losses.txt` lines identical. End-to-end job duration approximately **6 min 8 s**. **PASS**. No new training steps were performed: the comparison demonstrates preservation of the saved loss history, not rerunning those steps.

**Job B — stop at 610, resume and finish:** clean stop at step 610 with `INCOMPLETE_NOT_A_RESULT`; the first 610 `losses.txt` lines matched the original. Resumed training completed through step 1,221, with identical final SHA-256 and all 1,221 loss lines equal. Resume job duration approximately **30 min 39 s**, including 611 training steps, checkpoint load and save. **PASS**.

TSAI reported checks **C1–C6 PASS** on one GPU. For Job B, the step-by-step comparison was performed using **`losses.txt` only**; `metrics.jsonl` was returned as an output but **was not** the comparison file. Do not describe the 30 min 39 s as pure checkpoint loading time.

### R2 risks and limitations

- The restore drill is a controlled stop-and-resume test, **not** an actual failure/restart in Dry Run 1.
- The original trainer wrote `checkpoint.pt` directly to its final filename without a COMPLETE marker.
- TSAI agreed that the Week 5 main run should use the Team 07 Checkpointer.
- COMPLETE-only restart-after-kill evidence remains in the G7 `restart_cpu.txt` and `restart_node.txt` tests, not in the original Dry Run 1.

## Open items

- [x] Obtain full-run TSAI logs from merged PR #620.
- [x] Verify R1 step continuity for steps 1–305.
- [x] Analyze losses, gradient norm and throughput for steps 1–305.
- [x] Evaluate the published Team 8 default alarm logic for the assigned range.
- [x] Execute Team 8's official Python CLI locally (exit 0, 305 steps, 0 alarms).
- [x] Record TSAI restore drill results, with Job B comparison-file clarification.
- [x] Submit this follow-up for G7 Gate 3 review (PR #632).

## References

- Original Dry Run 1: https://github.com/theschoolofai/era-v5-lab/pull/475
- Full-run training evidence: https://github.com/theschoolofai/era-v5-lab/pull/620
- G7 restore plan: https://github.com/theschoolofai/era-v5-lab/pull/491
- G7 restore results: https://github.com/theschoolofai/era-v5-lab/pull/573

## Conclusion

Merged PR #620 makes actual per-step R1 verification possible. In the assigned steps **1–305**, all steps are present exactly once, the loss declines overall, all inspected numeric values are finite, and the implemented G8 default rules yield no alarms in a source-logic evaluation. The official Team 8 CLI default completed successfully (305 steps, 0 alarms). The 100-step window replay produced 2 page alarms, at steps 173 and 239; Team 8 must resolve the window-setting discrepancy.

The separate R2 restore drill passed all instructor-reported checks, but it does not constitute an original-run failure or COMPLETE-only checkpoint restart.
