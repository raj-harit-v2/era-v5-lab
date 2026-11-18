# Rotation log: kunal2016, Team 07 Infrastructure, week 3

**Run:** dry run 1 (Team 05 job request, PR #475, merged 16 Nov)  |  **Run ID:** `dryrun1-1234` (output folder in the request)
**Setup:** exp2_muon at T2 size, muon_lr 0.01, seed 1234, tokenizer p1536 (sha256 `e6b93a93...a64b`), TSAI text bundle, 1 GPU, bf16, one process
**Run by:** TSAI. Result posted as a comment on PR #475 (16 Nov 2026)
**Logs read:** TSAI's result comment on PR #475. **The per-step logs (`metrics.jsonl`, `losses.txt`, `summary.json`) were not available**: the evidence folder holds only the 3-step smoke run (checked on main at `dfdb6a6`, 18 Nov).
**Steps assigned:** 611 to 915. R1 is an offline review of the logs, split by step range.
**R1 is therefore written from TSAI's whole-run summary.** The per-step checks for steps 611 to 915 could not be run.

---

## 1. Shift summary (R1, due Wed 18 Nov)

For steps 611 to 915, check step continuity, loss spikes, gradient norm and throughput, and run Team 08's alarms
offline (`alarms.py --jsonl`). None of these could be done: the evidence folder
`teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/` holds only the 3-step smoke run (checked on main at
`dfdb6a6`, 18 Nov). The values below are TSAI's whole-run summary. If the per-step logs are released later, the
checks for 611 to 915 can be added in a follow-up.

| Item | Value | Source |
|---|---|---|
| Steps completed | 1,221 of 1,221. Status COMPLETED | TSAI comment |
| Final train cross-entropy | 4.8906 | TSAI comment |
| Final gradient norm | 0.7037 | TSAI comment |
| NaN or inf in the loss | none | TSAI comment |
| Held-out val/bpb | 1.5159 (English 1.9844, code 1.8901, Indic mean 1.3289, three-group 1.7345) | TSAI comment |
| Same arm with old tokenizer v0, seed 1234 | 1.6443 (change −0.1284) | TSAI comment |
| Checkpoints written | 1, at the last step (about 2.2 GB), kept by TSAI | TSAI comment; job request open item 3 |
| Tokens per second, step time, wall time | **not available** | per-step logs not released |
| Loss curve, spikes | **not available** | per-step logs not released |
| Alerts | none reported | Team 08 has `alarms_dryrun1.md` (#494); no alert posted |
| Overall | finished cleanly by the summary; the per-step curve could not be checked | |

---

## 2. Failure log (R2, due Thu 19 Nov)

No failures reported. TSAI reports the run COMPLETED, 1,221 of 1,221 steps, with no NaN or inf.

| # | Time | Step | Exit / code | Cause | Evidence | What the system did |
|---|---|---|---|---|---|---|
| — | — | — | — | none reported | TSAI comment, PR #475 | — |

Step continuity (none missing, none repeated) could not be checked without `metrics.jsonl`.

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
- [ ] No step lost or repeated in dry run 1: **not checkable**, per-step logs not released (the restore drill's job B has every step 1 to 1,221)
- [x] COMPLETE-only restarts: shown by `results/restart_cpu.txt` and `results/restart_node.txt` (dry run 1 had none)
- [x] Restore drill: jobs A and B bit-equal to dry run 1 on all 1,221 steps, same final model (`restore_dryrun1.md`, PR #573)

## 5. Gaps and questions for the team

1. **Per-step logs.** TSAI returned a summary, not `metrics.jsonl` / `losses.txt`. Without them R1 has no tokens per
   second, step time or loss curve, and the "no lost steps" check cannot be done. Team 05 also needs them for
   `dryrun1_loss.md`. Ask TSAI to return them to `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/`.
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
