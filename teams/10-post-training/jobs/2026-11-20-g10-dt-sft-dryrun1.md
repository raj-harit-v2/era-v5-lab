# Job request: Deletion Tuning SFT on dry run 1, keeping the canary's three input files (DRAFT, NOT RUNNABLE)

Status: draft, not sent. NOT RUNNABLE until every item under "Blocked by" is cleared and a test log is attached.
Follows: `2026-11-18-g10-first-sft-dryrun1.md` (#587), same inputs and pins. That job runs `--method full` and deletes every weight at its exit. This request runs the same job with `--method dt_markers` (Deletion Tuning plus the nine marker rows) and keeps one arm's state, so that the Task 11 canary (`2026-11-17-dt-then-rl-code.md`) has its inputs.

```
Team:            10-post-training
Owner:           10-post-training (lead saitej123)
Lead approval:   saitej123 (DT settings and route approved 20 Nov 2026; runnable once #587 result and #475 probe expectation clear)
Question:        Does the DT SFT arm leave the three files the Task 11 canary reads (model.safetensors, dt_keep_masks.bin, dt_keep_masks.bin.json) with sha256 values that match what the job reports?
Script:          teams/10-post-training/capstone/sft_job_v1.py
Command:         G10_STDIO_RUNNER=docker python teams/10-post-training/capstone/sft_job_v1.py <the #587 arguments unchanged, replacing --lr> --method dt_markers --lr 5e-4 --marker-lr 1e-3 --dt-targets g5_gate --dt-alpha-start 100 --dt-alpha-end 1000 --dt-eta 0.00048828125 --dt-lambda 1e-5 --dt-prior-strength 3.0 --keep-canary-state-dir keep/ --keep-arm <A2_OR_A4_FROM_587> --out out/
Config:          none: every setting is on the command line. Chosen DT settings (aligned with the 17 Nov port check and `agentic-learning-ai-lab/deleting-weights` `scripts/train_sft.sh`): `--dt-targets g5_gate` (MLP gate projections), `--lr 5e-4` (paper repo SFT AdamW lr), `--marker-lr 1e-3`, `--dt-alpha-start 100 --dt-alpha-end 1000`, `--dt-eta 0.00048828125` (1/2048 Wanda prior), `--dt-prior-strength 3.0`, `--dt-lambda 1e-5` (decaying to 0), `--dt-unseen official`, 64 calibration rows. `sft_g5.py` logs both `deletion_at_init` and `band_at_init` before step 1.
Inputs:          the same as #587 (run folder from #475, pack shards, RL pool, tokenizer, byte table, held-out files)
Hardware:        1 GPU
Max time:        as #587 (90 minutes, --deadline-minutes 85); the DT arm's time on the real shape is not measured
Precision:       weights as stored (fp32), AdamW state fp32
Measures:        the #587 measures for each arm, plus DT: deletion at init and final, mask checks, frozen-weight check; and the sha256 of the three kept files
Expected result: unknown. The stand-in only shows that the files are written and the canary loads them
Outputs:         out/*.json reports to the repo. keep/a2/ (model.safetensors about 0.95 GB in fp32 for 237,052,416 parameters, two mask files, SHA256SUMS) to TSAI storage. No weights in the repo
Test log:        CPU, stand-in model, from the job script itself: exit 0, 5 of 5 steps, three files with sha256 equal to summary.json; the staged canary then loaded them with the sha pins and ran 3 updates (stand-in reward) with deleted-nonzero 0. See the Update 20 Nov 2026 section of `2026-11-17-dt-then-rl-code.md`
```

## Blocked by

1. **The #587 result.** It decides the arm (`a2` or `a4`) and the rows.
2. **A probe expectation for the #475 checkpoint,** computed by Team 5's own loading path (see `2026-11-19-g10-rl-dryrun1.md`, "Questions for TSAI", item 4), because the adapter refuses a delivered run folder without it.

*Closed on 20 Nov 2026 (lead `saitej123`):* DT settings are pinned above to the 17 Nov paper-repo port check (`g5_gate`, `lr 5e-4`, `alpha 100 -> 1000`, `eta 1/2048`, `lambda 1e-5 -> 0`), and route/settings approval is recorded. Real-shape mask file size is estimated as under 2 MB for `g5_gate` (1 bit per targeted weight; stand-in was 81 KB for 1.67M weights).

## What leaves the job and what does not

One folder `keep/a2/` (or `a4`): three files and `SHA256SUMS`. The job's own output folder still has both arms' mask files next to the reports (as for any DT arm); it never holds a weight file, the built rows, the held-out answers or the generations. The other arm's weights are deleted.

## Notes

- The A2/A4 equal-steps rule is unchanged: A4 runs for the steps A2 completed. Whether that is the right comparison for DT is not decided here.
- No benchmark item text goes into any file in this request.
