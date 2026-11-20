# Job request: eval-mini forgetting, base and after the first SFT on dry run 1 (DRAFT, NOT RUNNABLE)

Status: in PR #634 for lead review. NOT RUNNABLE: TSAI must not run this until every item under "Blocked by" is cleared and a test log is attached.
Part of the forgetting check in `sft/eval_v1.md` (the eval-mini part). `#587` does not run this part: it measures
held-out bits per byte only. The verdict is computed by `sft/tests/forgetting.py` from the two files this job writes.

```
Team:            10-post-training
Owner:           10-post-training (lead saitej123)
Lead approval:   pending (saitej123)
Question:        Does the first SFT on dry run 1 lower ARC-Challenge or HellaSwag accuracy under Team 9's mini profile, measured the same way before and after SFT?
Script:          teams/10-post-training/sft/bench/evaluate.py (on main; --eval-mini calls teams/09-evaluation/harness/run_eval_mini.py as a black box)
Command:         python teams/10-post-training/sft/bench/evaluate.py --eval-mini --model <BASE_DIR> --eval-mini-python <VENV_PY> --eval-mini-tasks arc_challenge,hellaswag --device cuda --out out/evalmini_base.json
                 python teams/10-post-training/sft/bench/evaluate.py --eval-mini --model <SFT_DIR> --eval-mini-python <VENV_PY> --eval-mini-tasks arc_challenge,hellaswag --device cuda --out out/evalmini_sft.json
Config:          none. The mini profile is fixed in run_eval_mini.py: arc_challenge 0-shot, first 500 items; hellaswag 0-shot, first 400 items.
Inputs:          <BASE_DIR>: the dry run 1 checkpoint as a model directory (conversion NOT YET WRITTEN, see Blocked by). <SFT_DIR>: the kept after-SFT model directory from `2026-11-18-g10-sft-keep-weights.md`. Team 9's run_eval_mini.py at its main commit, in its own virtualenv.
Hardware:        1 GPU
Max time:        60 minutes for both runs (estimate: about 900 items per model, two models)
Precision:       fp32 (evaluate.py passes --dtype float32 to run_eval_mini)
Measures:        the primary metric with its stderr for arc_challenge and hellaswag, for the base and the after-SFT model. The verdict is not computed here.
Expected result: no estimate yet (no run). The rule in eval_v1: forgetting if a benchmark falls by more than 2 x its combined stderr and by at least 0.01; within 0.01 of that limit is marked "at the limit".
Outputs:         out/evalmini_base.json, out/evalmini_sft.json (under 2 MB). Scores only: do not add --log-samples, which writes benchmark items.
Test log:        REQUIRED before sending. Not yet attached. Run both commands on our own machine with a small model and attach the log.
```

## Blocked by

1. **Keep-weights job** (`2026-11-18-g10-sft-keep-weights.md`). The after-SFT model directory does not exist until that job's route is decided and it runs.
2. **Base model as a directory.** The dry run 1 checkpoint is a Team 5 architecture, not a Hugging Face model. Writing the conversion is not done. Team 9 must confirm that `run_eval_mini.py` can load a converted directory. If it cannot, score through Team 9's lab scorer instead (`eval_watcher.py --run-dir`, the path Team 9's own dry-run job uses).
3. **Access list.** The workspace rule limits benchmark text to named measuring jobs on the access list. The lead must confirm this job is on that list before it is sent. Team 9 must confirm it is a measuring job for its black-box scorer.
4. **Test log** (rule 2 of `JOB_REQUEST.md`).
5. **Lead approval** on this PR.

## Notes

- Both models are scored by the same command, the same profile and the same scorer. That is the comparison rule in `eval_v1.md`.
- Item text is never written to any file in this request or its outputs.
