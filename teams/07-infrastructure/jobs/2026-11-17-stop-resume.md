# Job request: stop at step 610, restore, continue (job B, optional)

Week 3, Team 07 core task 5, the restore drill. Plan and checks: [results/restore_dryrun1.md](../results/restore_dryrun1.md).

This is the full "stop, restore, continue" of the work order. It costs about one more dry run 1 of compute, so it is
optional: TSAI decides whether to run it. Job A ([2026-11-17-restore-final-ckpt.md](2026-11-17-restore-final-ckpt.md))
does not depend on it.

```
Team:            07-infrastructure
Owner:           Pratik Mukherjee (pratik-2025)
Lead approval:   sureshmantha
Question:        If dry run 1 is stopped at step 610 and resumed from that checkpoint, does it finish with the same losses and the same final model as the uninterrupted run (#475)?
Script:          teams/05-architecture/harness/train_week2.py   (the exact source TSAI ran for #475, with TSAI's Gate 2 speed fixes and the scoring patch)
Command:         two runs of the #475 command, one after the other:
                 run 1: <the #475 command exactly as TSAI ran it> --stop-after 610 --out ./out/drill-stop
                 run 2: <the #475 command exactly as TSAI ran it> --resume ./out/drill-stop/checkpoint.pt --out ./out/drill-resume
Config:          teams/05-architecture/configs/arms/exp2_muon.yaml, with the same runtime and resolution files as #475
Inputs:          the same staged inputs as #475: TSAI text bundle, tokenizer p1536 (sha256 e6b93a93...a64b) and its byte table, heldout_v1
Hardware:        1 GPU                                 (the same single-process setup as #475)
Max time:        #475's run time plus 30 minutes       (610 + 611 steps = the same 1,221 steps, plus one save and one load)
Precision:       bf16, as #475
Measures:        for each run: exit code, summary.json, losses.txt; the time from the start of run 2 to its first training step
Expected result: run 1: status INCOMPLETE_NOT_A_RESULT, steps 610. run 2: exit 0, no identity error, steps 1,221, status COMPLETED.
                 losses.txt of run 2 equal to #475's, line for line, and final_model_sha256 equal to #475's, if the GPU run is deterministic;
                 otherwise the largest difference is small, and lines 1 to 610 of run 1 already differ from #475 by the same order
Outputs:         out/drill-stop/ and out/drill-resume/: summary.json, losses.txt, total_losses.txt, metrics.jsonl, manifest.json, and the job log with start and end times. Please do not return the checkpoints.
Test log:        the same trainer's stop-and-resume on CPU: teams/05-architecture/results/exp1_lr_1e-2/README.md, section 1, item 4 (2 steps, stop, --resume to 4 steps, final_model_sha256 bit-equal to the uninterrupted run); the #475 command form: teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/smoke.md
```

## Notes for TSAI

1. **Same source, same command.** Both runs must use the exact files and flags of #475. Only `--stop-after`,
   `--resume` and `--out` are added. `--stop-after` is not part of the identity hash and does not change the
   config (the run still has 1,221 steps and the same learning rate), so run 2 is allowed to resume and continues
   exactly where run 1 stopped.
2. **Why compare lines 1 to 610 of run 1 too.** If those already differ from #475, two runs of the same command
   differ on the GPU before any restore, and any later difference is run-to-run noise, not the restore. If they are
   equal and run 2 differs, the restore changed something.
3. **For the comparison** please also return #475's own `summary.json` and `losses.txt` if they are not in the repo
   by then.
