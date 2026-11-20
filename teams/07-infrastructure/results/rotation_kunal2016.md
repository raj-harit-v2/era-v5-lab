# Rotation log: kunal2016, Team 07 Infrastructure, week 3

**Run:** dry run 1 (Team 05 job request, PR #475, merged 16 Nov)  |  **Run ID:** `dryrun1-1234` (output folder in the request)
**Setup:** exp2_muon at T2 size, muon_lr 0.01, seed 1234, tokenizer p1536 (sha256 `e6b93a93...a64b`), TSAI text bundle, 1 GPU, bf16, one process
**Run by:** TSAI. Result posted as a comment on PR #475 (16 Nov 2026)
**Logs read:** full-run evidence in `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/` (PR #620, commit
`d005c9b`): `metrics.jsonl` (1,221 training rows), `losses.txt` (1,221 lines), `summary.json`. Also TSAI's result comment on #475.
**Steps assigned:** 611 to 915. R1 is an offline review of the logs, split by step range.
**Method:** a small local script of mine (`r1_check.py`, not in the repo) for continuity, loss, gradient norm and
throughput, plus Team 08's `alarms.py --jsonl` with its default rules (the official check).

---

## 1. Shift summary (R1): steps 611 to 915

| Check | Result |
|---|---|
| Step continuity | **PASS.** 305 of 305 steps present, each exactly once; none missing, none repeated |
| NaN / inf | **PASS.** None in `loss`, `loss_ntp`, `loss_mtp` or `gradient_norm` |
| Loss (`loss_ntp`) | 6.2643 at step 611, 6.0153 at step 915; median 5.9486. Mean of steps 611–630: 6.0033; of 896–915: 5.8792. Per-step range 4.6065 to 7.6421 (batch-to-batch noise) |
| Loss spikes | **None.** No step above 1.5 × the median of the previous 50 steps (largest ratio 1.265) |
| Gradient norm | Median 0.8231 (min 0.5245, max 4.9868). Clipping applied on 57 of 305 steps. Two single-step jumps above 3 × the trailing median: step 618 (2.660) and step 841 (4.987) |
| Throughput | Median 8,679 tokens/s (min 7,270, max 9,823); median step time 1,887.9 ms; no slow steps (none above 1.5 × median) |
| Team 08 alarms (`alarms.py --jsonl`, default rules) | **1 in range:** step 841, `spike_score` on `gradient_norm`, severity page: 4.987, 8.3 σ above the trailing 839-step mean of 1.096 |
| `losses.txt` against `metrics.jsonl` | **PASS.** All 305 lines in range equal `train/ce_loss` |

**The step 841 alarm.** It was one step. Gradient clipping was applied at that step, the loss did not rise (5.3447,
lower than the 6.5765 of step 840), and the gradient norm was back to normal at step 842 (0.8232) and after. The
learning rate was unchanged (0.001). So it is a transient gradient spike, absorbed by clipping, with no effect on
training. It is the kind the `spike_score` rule exists to catch, and it fired as designed.

**Whole run, for context.** `alarms.py` on all 1,221 steps gives 3 alarms, all `spike_score` on `gradient_norm`: steps
468 and 505 (in the 306–610 range) and 841 (this range). Run time 2,480.9 s (`summary.json`).

**Not checked.** MoE routing health: the rows carry no `expert_load`, so the `moe_routing` rule cannot run. The spike
limits of 1.5× (loss) and 3× (gradient norm) are my script's own; Team 08's alarms are the official check.

Commands, from the repo root (the second one reproduces the official alarm check):

```bash
E=teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full
python r1_check.py --metrics $E/metrics.jsonl --losses $E/losses.txt --start 611 --end 915 \
  --alarms teams/08-monitoring/alarms/alarms.py --out r1_611_915.json
python -I teams/08-monitoring/alarms/alarms.py --jsonl $E/metrics.jsonl
```

TSAI's whole-run summary (#475): 1,221 of 1,221 steps, COMPLETED; final train cross-entropy 4.8906; final gradient
norm 0.7037; held-out val/bpb 1.5159 (English 1.9844, code 1.8901, Indic mean 1.3289, three-group 1.7345); one
checkpoint at the last step (about 2.2 GB).

---

## 2. Failure log (R2, due Thu 19 Nov)

No failures reported. TSAI reports the run COMPLETED, 1,221 of 1,221 steps, with no NaN or inf.

| # | Time | Step | Exit / code | Cause | Evidence | What the system did |
|---|---|---|---|---|---|---|
| — | — | — | — | none reported | TSAI comment, PR #475 | — |

Step continuity in 611–915 is checked in §1: every step once, so no unlogged restart. The one alarm (step 841) was a
transient gradient spike, not a failure: training went on with no stop.

---

## 3. Restart log (R2)

No restarts in dry run 1 itself. The trainer ran as one process. It was not run under `ckpt/supervisor.py` and it does not
save during the run (job request, open item 3), so a crash would have lost the whole run rather than restarting.

The only restarts this week were the two restore drill jobs (core task 5). TSAI ran both on 17 Nov, single GPU,
same setup as #475. Source: `results/restore_dryrun1.md` §5 (PR #573).

| # | Failure | Restored from | Resumed at | Steps skipped | Loss vs dry run 1 | Time (job start to exit) | Result |
|---|---|---|---|---|---|---|---|
| R1 | none: job A restores dry run 1's final checkpoint | final `checkpoint.pt` (step 1,221) | n/a (exit 0, 1,221 steps, COMPLETED) | 0 | `losses.txt` identical, 1,221 of 1,221 lines; `final_model_sha256` equal | about 6 min 8 s | PASS |
| R2 | planned stop at step 610 (job B run 1: INCOMPLETE_NOT_A_RESULT, lines 1–610 identical) | `checkpoint.pt` at step 610 | **611** | 0 (steps 1 to 1,221 all present) | `losses.txt` identical, 1,221 of 1,221 lines; `final_model_sha256` equal | about 30 min 39 s (load, steps 611–1,221, save) | PASS |

**For my R1 range.** Job B's restart point is the start of my range: it resumed at step 611 and matched dry run 1
bit for bit from 611 to 915 (and on to 1,221). So the step 610 → 611 boundary is clean in the restore drill.

**What it does not show.** Both jobs used `train_week2.py`'s own `checkpoint.pt` after a clean stop, not a kill, and not
Team 07's Checkpointer. The COMPLETE-only restart after a kill is shown by `results/restart_cpu.txt` and
`results/restart_node.txt`.

---

## 4. Gate 3 checks

- [x] The run ended: 1,221 of 1,221 steps, COMPLETED (TSAI)
- [x] No NaN or inf in the loss (TSAI)
- [x] No restart during the run, so no restart from a non-COMPLETE checkpoint
- [x] No step lost or repeated in 611–915: every step once in `metrics.jsonl` (PR #620)
- [x] COMPLETE-only restarts: shown by `results/restart_cpu.txt` and `results/restart_node.txt` (dry run 1 had none)
- [x] Restore drill: jobs A and B bit-equal to dry run 1 on all 1,221 steps, same final model (`restore_dryrun1.md`, PR #573)

## 5. Gaps and questions for the team

1. **Per-step logs.** Resolved: TSAI published the full run in PR #620 (`2026-11-15-dryrun1-full/`); §1 uses it.
2. **COMPLETE checkpoint.** The final checkpoint is the trainer's own `checkpoint.pt`, with no `MANIFEST.json` and no
   `commits.jsonl`, so it is not COMPLETE by queue rules v1.1 (R4). **Resolved:** dry run 1 had
   zero restarts and did not use the Checkpointer; the COMPLETE-only restart evidence stays `results/restart_cpu.txt`
   and `results/restart_node.txt`.
3. **Periodic saves.** Dry run 1 saved only at the end, so the 10-minute interval (`docs/checkpoint_interval.md`, PR #463) and
   the supervisor were not exercised. Should dry run 2 run under `ckpt/supervisor.py` with Team 07's checkpointer?
4. **Save timing not measured.** `docs/checkpoint_interval.md` §4 (PR #463) expects dry run 1 to give, for each
   10-minute save, the stall (`save_seconds.stall`, limit 12 s) and the time from `checkpoint.started` to
   `checkpoint.committed` (limit 600 s, CK-10 at 0). Dry run 1 made one save, outside Team 07's checkpointer, so it
   gives none of these. The interval stays provisional until a run saves every 10 minutes.
