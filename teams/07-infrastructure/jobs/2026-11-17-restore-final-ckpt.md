# Job request: restore dry run 1's final checkpoint (job A)

Week 3, Team 07 core task 5, the restore drill. Plan and checks: [results/restore_dryrun1.md](../results/restore_dryrun1.md).

```
Team:            07-infrastructure
Owner:           Pratik Mukherjee (pratik-2025)
Lead approval:   sureshmantha
Question:        Does dry run 1's final checkpoint (step 1,221, #475) load into a fresh run and give back the same model and loss record?
Script:          teams/05-architecture/harness/train_week2.py   (the exact source TSAI ran for #475, with TSAI's Gate 2 speed fixes and the scoring patch)
Command:         <the #475 command exactly as TSAI ran it> --resume <#475 out folder>/checkpoint.pt --out ./out/restore-a
Config:          teams/05-architecture/configs/arms/exp2_muon.yaml, with the same runtime and resolution files as #475
Inputs:          the same staged inputs as #475: TSAI text bundle, tokenizer p1536 (sha256 e6b93a93...a64b) and its byte table, heldout_v1; plus #475's checkpoint.pt (TSAI keeps it)
Hardware:        1 GPU                                 (the same single-process setup as #475)
Max time:        30 minutes                            (no training step runs; the time is the 2.2 GB load and the write-out)
Precision:       bf16, as #475
Measures:        exit code; summary.json steps, status and final_model_sha256; losses.txt; job start-to-exit time
Expected result: exit 0, no identity error; steps 1,221, status COMPLETED; final_model_sha256 equal to #475's; losses.txt equal to #475's line for line
Outputs:         out/restore-a/summary.json, losses.txt, total_losses.txt, metrics.jsonl, manifest.json, and the job log with start and end times. Please do not return checkpoint.pt (2.2 GB).
Test log:        the same trainer's stop-and-resume on CPU: teams/05-architecture/results/exp1_lr_1e-2/README.md, section 1, item 4 (2 steps, stop, --resume to 4 steps, final_model_sha256 bit-equal to the uninterrupted run); the #475 command form: teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/smoke.md
```

## Notes for TSAI

1. **Same source, same command.** The trainer stores an identity hash (code, config, data, device, software) in the
   checkpoint and refuses to resume if anything differs. Please use the exact files and flags of #475 and add only
   `--resume` and a fresh `--out`.
2. **No training step runs.** The checkpoint is at the last step, so the loop has nothing left to do. The trainer
   loads the model, writes the outputs again from the checkpoint and hashes the loaded model. Training past step 1,221
   is not possible without changing the step count, which fails the identity check.
3. **For the comparison** please also return #475's own `summary.json` and `losses.txt` if they are not in the repo
   by then (the evidence folder has only the 3-step smoke).
4. **Restore time.** Job start-to-exit time is the restore time we record. It is mostly the 2.2 GB load.
