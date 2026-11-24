# Job request: dry run 2 planned failure, kill and restore to the last committed checkpoint

Week 4, Team 07 core task 3, the restore drill for dry run 2. Results will go to `results/restore_dryrun2.md`.
TSAI agreed in the Team 7 group on 21 Nov to run both kill variants, (a) first.

This request adds a kill and a restart to Team 5's dry run 2 job
([2026-11-22-dryrun2.md](../../05-architecture/jobs/2026-11-22-dryrun2.md)). Run 1 below is that job's command,
unchanged. Runs 2 and 3 are the same command with `--resume-committed` and a fresh `--out`, as
`teams/05-architecture/docs/HARNESS_WEEK3.md` says for continuing a quality run.

```
Team:            07-infrastructure
Owner:           Pratik Mukherjee (pratik-2025)
Lead approval:   sureshmantha
Question:        When dry run 2 is killed with SIGKILL, between two committed saves (a) and during a save (b), does --resume-committed restart from the last committed checkpoint and finish the run with no lost steps?
Script:          teams/05-architecture/harness/train_week2.py on lab main, with teams/07-infrastructure on PYTHONPATH (#608 is on main)
Command:         three runs, one after the other; <DR2> is the command of 2026-11-22-dryrun2.md exactly as TSAI runs it:
                 run 1: <DR2>                                                        (out ./out/dryrun2-1234; killed, see "When to kill")
                 run 2: <DR2> --resume-committed --out ./out/dryrun2-1234-resume-a   (killed again for (b), or left to finish if (b) is not run)
                 run 3: <DR2> --resume-committed --out ./out/dryrun2-1234-resume-b   (only if (b) is run; runs to the end)
Config:          teams/05-architecture/configs/arms/dryrun2.yaml, the same as 2026-11-22-dryrun2.md
Inputs:          the same staged inputs as 2026-11-22-dryrun2.md; the same --run-id dryrun2-1234 and --checkpoint-store /shared/ckpt in every run
Hardware:        1 GPU, the same as 2026-11-22-dryrun2.md
Max time:        each run within the 90-minute T2 cap; in total about the 90 minutes of dry run 2 plus up to 10 minutes of re-run steps per kill, plus the restores
Precision:       bf16, as 2026-11-22-dryrun2.md
Measures:        for each kill: the time of the kill, the newest checkpoint.committed step before it, and a copy of latest.json and commits.jsonl right after it;
                 for each restart: the step it restored from, exit code, time from start to the first training step;
                 for the last run: summary.json status and steps, losses.txt, final_model_sha256
Expected result: (a) run 2 restores the step that latest.json pointed to at the kill. (b) the half-written save has no MANIFEST.json, latest.json did not move, and run 3 restores the commit before it.
                 Same run id in all runs. The last run ends with exit 0, status COMPLETED, 1,221 steps, every step once in losses.txt.
                 The re-run steps after each restore give the same loss as the first pass, as the dry run 1 drill did (#491); if a GPU difference shows up, the largest difference is reported, not hidden
Outputs:         out/dryrun2-1234*/: summary.json, losses.txt, total_losses.txt, metrics.jsonl, manifest.json; the latest.json and commits.jsonl copies; the checkpoint.* events and the job log with start, kill and end times. Please do not return checkpoints.
Test log:        Team 7 checkpoint tests on main at 9a60035, Linux CPU: test_ckpt.py T1 bit-equal resume (1 and 2 processes), T3 flipped byte, T4 crash before seal, 4 passed: https://colab.research.google.com/drive/1phA2x6DPY2aYo_t6PSn-_6e8DC0_xEp5
                 test_week2_team7_checkpoints.py: 4 passed on #608 (rahulni). The dry run 1 restore drill: #491, #573, #633.
```

## When to kill

The save interval is 600 s and step 0 is committed at the start, so a new commit lands about every 10 minutes.

| Kill | When | How | What it tests |
|---|---|---|---|
| (a), first | After at least 2 commits besides step 0. About 5 minutes after a `checkpoint.committed` event, so midway to the next save. | `kill -9` (SIGKILL) on the training process. Not SIGTERM: SIGTERM saves cleanly and exits 75, which tests a different path. | A crash between two saves loses only the steps since the last commit. |
| (b), if time allows | In run 2, during its first save after the restore: after `checkpoint.started` and before `checkpoint.committed`. | Run 2 starts with `V5_DRILL_DIR` set to a folder holding a file `upload_delay_s` that contains `120`, so the upload takes 2 minutes and the kill can land inside it. Then `kill -9`. | A crash in the middle of a save. The half-written save must not be used. |

(b) is set only on run 2, so run 1, the dry run 2 that Team 5 and Team 9 score, keeps normal saves. If only one kill fits, run (a) and let run 2 finish.

## Pins and retention

- Pin steps: see #743. Pradeep (Team 7 task 4) pins step 0 and the step that run 2 restores from, right after this drill's restore: `ckpt.py pin --run /shared/ckpt/dryrun2-1234 --step N`. `--run` takes the full store path; the run id alone fails (Pradeep, on #738). Team 9 asked for the restored-from step in CAP, so they can score it.
- Any retention run during the drill uses `--protect-every 10` (Team 9, 21 Nov).

## Pass checks (go into results/restore_dryrun2.md)

1. Each restart restores the step that `latest.json` pointed to at the kill.
2. For (b): the half-written save has no `MANIFEST.json` and is not used.
3. The same run id in every run, and `commits.jsonl` continues from one run to the next.
4. The re-run steps give the same loss as the first pass, or the largest difference is reported.
5. No lost steps: the final `losses.txt` and `metrics.jsonl` have every step once, with no gap, as checked for dry run 1 in #633.
