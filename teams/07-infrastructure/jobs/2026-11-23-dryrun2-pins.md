# Job request: dry run 2, pin step 0 and the restored-from step

Week 4, Team 07 core task 4. This adds steps to the kill drill in #738
(`2026-11-23-dryrun2-kill-drill.md`, Task 3), which itself adds steps to Team 5's dry run 2
(`teams/05-architecture/jobs/2026-11-22-dryrun2.md`). **No new run.** The steps below run after #738's restart
has restored, and they read only the checkpoint store.

```text
Team:            07-infrastructure
Owner:           Pradeep Kumar G.S. (pradeep-kumar-gs)
Lead approval:   sureshmantha
Question:        After dry run 2's planned-failure restore, are step 0 and the restored-from step pinned, so that retention never deletes them?
Script:          teams/07-infrastructure/ckpt/ckpt.py (on main; not edited)
Command:         <RUN> = /shared/ckpt/dryrun2-1234 (the full path: --run takes <store>/<run id>, not the run id alone)
                 <K>   = the step run 2 of #738 restored from (its log, or `latest.json` at the kill)
                 1. python teams/07-infrastructure/ckpt/ckpt.py list --run <RUN>
                 2. python teams/07-infrastructure/ckpt/ckpt.py pin --run <RUN> --step 0
                 3. python teams/07-infrastructure/ckpt/ckpt.py pin --run <RUN> --step <K>
                 4. python teams/07-infrastructure/ckpt/ckpt.py verify --run <RUN> --step 0
                 5. python teams/07-infrastructure/ckpt/ckpt.py verify --run <RUN> --step <K>
                 6. python teams/07-infrastructure/ckpt/ckpt.py retention --run <RUN> --keep 3 --protect-every 10 --dry-run
                 If #738's kill (b) also ran, repeat steps 3, 5 and 6 with K = the step run 3 restored from.
Config:          none
Inputs:          the dry run 2 checkpoint store, /shared/ckpt/dryrun2-1234
Hardware:        the dry run 2 machine; CPU only, no GPU needed
Max time:        10 minutes
Precision:       not applicable
Measures:        output of steps 1 to 6; pins.json
Expected result: step 1 lists step 0 (reason start) and K. pins.json = [0, K]. Steps 4 and 5 pass. Step 6 lists 0 and K in "protected" and "kept", and neither in "deleted". Step 6 is --dry-run: nothing is deleted.
Outputs:         text output of steps 1 to 6 and pins.json, pasted into #738's results (results/restore_dryrun2.md). No checkpoint files.
Test log:        local check on main 0140302c, folder store, macOS CPU, below
```

## Why pin these two

- **Step 0** (`--checkpoint-at-start`, from #608) is the untrained start. With it, the run can be restarted from
  the very beginning without a new run id.
- **K** is the checkpoint the planned-failure restore used. It is the Gate 4 evidence, and Team 9 asked for it in
  CAP so they can score it.
- Retention deletes everything except the newest `--keep`, every 10th commit (`--protect-every 10`, Team 9,
  21 Nov), the final checkpoint, `latest.json`'s checkpoint and the pinned steps. Without the pins, step 0 and K
  are deleted once they are older than the newest 3 commits.

## Local check (23 Nov, main 0140302c)

On a folder store, with `ckpt.py` from main:

| Check | Result |
|---|---|
| `pin --run dryrun2-1234 --step 0` (run id only) | fails: `ValueError: not enough values to unpack`. `--run` needs `<store>/<run id>`. |
| `pin --run <store>/dryrun2-1234 --step 0`, then `--step 600` | `pins.json` = `[0, 600]` |
| `retention --keep 3 --protect-every 10 --dry-run` on 25 commits (steps 0 to 1,200, every 50), pins `[0, 600]` | protected: 0, 450, 600, 950, 1,200 (latest). Kept: those plus 1,100 and 1,150. 18 marked for deletion, neither pin among them. |

A pin matches on the step, so it protects that step's folder from every attempt (`step_<N>-e<E>`).
