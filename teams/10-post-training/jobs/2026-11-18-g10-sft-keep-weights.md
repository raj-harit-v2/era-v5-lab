# Job request: first SFT on dry run 1, keeping one checked weights file for Team 9 (DRAFT, NOT RUNNABLE)

Status: in PR #634 for lead review. NOT RUNNABLE: TSAI must not run this until every item under "Blocked by" is cleared and a test log is attached.
Follows: `2026-11-18-g10-first-sft-dryrun1.md` (#587). That job returns reports only; its weights are deleted after the
reload check. This request is the same SFT with the weights kept, so that Team 9 can run the forgetting benchmarks
(`2026-11-18-g10-eval-mini-forgetting.md`) and later RL can load them.

```
Team:            10-post-training
Owner:           10-post-training (lead saitej123)
Lead approval:   pending (saitej123)
Question:        Does the SFT arm chosen by the #587 decision rule, rerun with its weights kept, reproduce its #587 held-out numbers and leave one checked safetensors file in TSAI storage?
Script:          teams/10-post-training/capstone/sft_g5.py (`--team7-ckpt-remote` calls `teams/07-infrastructure/ckpt/ckpt.py` `Checkpointer.save` + `export_safetensors`, verified locally on single-process PyTorch in `capstone/test_team7_ckpt_save.py`). `capstone/sft_job_v1.py` still deletes weights by default until a keep-weights flag is wired.
Command:         python teams/10-post-training/capstone/sft_g5.py --adapter-config <CFG> --train <ARM_ROWS> --eval <DEV_ROWS> --method full --team7-ckpt-remote <REMOTE_ROOT> --team7-run-id <RUN_ID> --out out/ (exact arm TBD after #587)
Config:          the #587 settings (block size 2,048, seed 1, AdamW, full method, the same pins). Arm: A2 or A4, whichever #587's decision rule picks (see #587 "Decision rule").
Inputs:          the same as #587: the firewalled OCR-2 pack shards 0-3 (TSAI-stored, #565), the RL pool files (#564), and the dry run 1 run folder (#475). Nothing new.
Hardware:        1 GPU
Max time:        90 minutes for the training and reports (as #587), plus the export time, which is not yet estimated
Precision:       weights fp32, AdamW state fp32 (as #587)
Measures:        the #587 measures (held-out bpb, format validity, execution pass, forgetting) to reproduce, the sha256 of the kept safetensors file, and a reload check that gives the same held-out bpb as the saved weights
Expected result: the #587 numbers within the reload check's tolerance. Storage estimate: about 0.95 GB of fp32 weights (237,052,416 parameters from the #587 config x 4 bytes). Estimate only.
Outputs:         out/*.json reports (under 2 MB) to the repo. One safetensors file to TSAI storage, named with its sha256. No weights in the repo.
Test log:        REQUIRED before sending. Not yet attached. Run the save and reload path on our own machine with a small stand-in model and attach the log.
```

## Blocked by

1. **#587 results.** The arm is picked by #587's decision rule. Until TSAI returns #587, the arm is unknown.
2. **Code PR for the save step (partially done).** `capstone/sft_g5.py` now supports `--team7-ckpt-remote` (calling Team 7 `Checkpointer.save` + `export_safetensors` on single-process non-DeepSpeed PyTorch; verified in `capstone/test_team7_ckpt_save.py` with exact `float_bits` probe parity and `logits_max_abs_diff == 0.0`). Still open: wire a pass-through flag into `sft_job_v1.py` if run via the two-arm wrapper, and confirm Team 7 remote store credentials/URL.
3. **Route decision (lead).** Two options:
   - (a) Team 7's `Checkpointer` and `export_safetensors`, as the instructor's `#587` note asks for later SFT jobs that keep weights.
   - (b) TSAI stores the exported safetensors file with its sha256, on the same route as the OCR-2 pack (#565) and the RL pool (#564).
4. **Team 9 confirmation of format.** Team 9's watcher reads `--run-dir`. Team 9's `run_eval_mini.py` takes a model directory (the bench passes one). Confirm which one Team 9 will use, and the file layout.
5. **Test log** (rule 2 of `JOB_REQUEST.md`).
6. **Lead approval** on this PR.

## Notes

- One job answers one question. The eval-mini scoring is a separate request, so the two can be sent apart.
- No benchmark item text goes into any file in this request.

## Update 19 Nov 2026 (f20201351h-maker), PR saitej123/era-v5-lab#126

Written the same evening the lead added `--team7-ckpt-remote` to `capstone/sft_g5.py` (c7c7324d). Nothing above was edited, and that
flag and its test are unchanged by PR 126. What PR 126 adds next to it:
- The pass-through that item 2 lists as still open: `--keep-weights-dir` and `--keep-arm {a2,a4}` on `capstone/sft_job_v1.py`. Today
  they call PR 126's own save (`capstone/keep_weights.py`, reached through `--keep-weights-dir` on `sft_g5.py`: weights only, no
  optimizer state, probe function equal to Team 9's `lm_eval_lab.probe_loss`), not `--team7-ckpt-remote`. The two saves are
  independent and both default off. Which one the wrapper should call is the lead's choice; switching it is a small change.
- `--keep-weights-dir` on `capstone/rl_job_v1.py` (the final RL weights).
- Read-back on the CPU stand-in: Team 7's `export_safetensors`, fed Team 9's own model builder and probe (`lm_eval_lab.build_model`,
  `probe_loss`), reads the kept folder and the exported file loads `strict=True`. Team 9's `run_lab_ckpt.py --run-dir` with its
  default smoke scorer does not read a folder that holds Team 5's `LanguageModel` (it builds the tiny MoE, so the keys differ), and
  its real scorer needs `lm_eval`, which was not installed here, so no benchmark scoring of a kept folder was run. That is part of
  item 4. Not shown: a GPU run or the real checkpoint.
- Item 5 (test log): `capstone/test_keep_weights.py`, `test_keep_weights_adapters.py`, `test_keep_weights_wiring.py`,
  `test_keep_weights_real_model.py`, and the end-to-end log of `sft_job_v1.py` with the two flags (PR 126 body).
- Still open: 1 (#587 results), 4 (Team 9 real `lm_eval_lab:team5` scoring check on a kept run folder), 6 (lead approval once #587 picks the arm).

## Lead route decision (21 Nov 2026, `saitej123`)

- **Canonical route for Team 9 evaluation handoff (item 3, closed):** use `--keep-weights-dir` (`capstone/keep_weights.py`), which writes weights-only Team 7 `Checkpointer` run folders using Team 9's exact `lm_eval_lab.probe_loss`, so Team 7 `export_safetensors` and Team 9 `run_lab_ckpt.py --run-dir` read the same artifact without storing 3x optimizer state. Keep `--team7-ckpt-remote` in `capstone/sft_g5.py` for jobs that explicitly need resumable optimizer state.
- **Eval-mini job withdrawn (confirmed by TSAI, 21 Nov 2026):** `jobs/2026-11-18-g10-eval-mini-forgetting.md` is superseded/withdrawn per the eval firewall; Team 9's watcher scores ARC-Challenge and HellaSwag on base + kept SFT folders and hands fraction-scaled rows (`value/100`, `stderr/100`) to `sft/tests/forgetting.py`.
- **Status:** remains **NOT RUNNABLE** in lead review (Week 4 Task 4) until `#587` returns and selects `a2` vs `a4`.
- Measured, not estimated: the #587 model (Team 5 `configs/arms/t2.yaml`, built on CPU) has 237,052,416 parameters, which matches the line above.
