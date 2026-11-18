# Small SFT evidence: bench evaluation reports (SmolLM2-135M)

The report files that `sft/bench/evaluate.py` (schema `g10-bench-eval/1`) wrote for the small SFT slice, so that
`sft/tests/forgetting.py` can be run on them. Nothing here was edited except the path prefixes listed below.

## Which run is which

| Run | Files |
|---|---|
| Base model (untrained SmolLM2-135M) | `base-test.json`, `base-evalmini.json` |
| Full fine-tune, lr 1e-4, seed 1, 2, 3 (400 steps) | `full-lr1e-4-s{1,2,3}-test.json`, `full-lr1e-4-s{1,2,3}-evalmini.json` |
| LoRA r4, lr 1e-3, seed 1 (400 steps) | `lora-lr1e-3-s1-test.json`, `lora-lr1e-3-s1-evalmini.json` |

- `*-test.json`: written by `evaluate.py` on the test split. Holds target bits per byte (`target_bpb`), format
  validity of 110 greedy generations (`format`) and the held-out forgetting block (`forgetting`: `bpb_all`, groups,
  `heldout_sha256`). `forgetting.py` reads `forgetting`, `tokenizer_sha256`, `device` and `compute_dtype` from here.
- `*-evalmini.json`: written by `evaluate.py --eval-mini` (ARC-Challenge and HellaSwag, 500 and 400 items,
  0-shot, `acc_norm`, with stderr). `forgetting.py` reads `eval_mini.records` from here.
  `evaluate.py` writes forgetting and eval-mini to separate files, so `forgetting.py` takes both per run
  (`--before` / `--after` accept several files and merge them).
- `corrected_target_bpb.json`: later correction of the `target_bpb.bpb` field (see below).

## How they were produced

- `*-test.json`: `evaluate.py --model <model folder> --split-file <test split> --split test --metrics bpb,format,forget
  --device cuda --out <report>.json` (flags as in `evaluate.py --help`; the files do not record the full
  command line). Recorded in the files: device `cuda`, torch `2.14.1+cu130`, compute dtype `float32 (TF32 off)`,
  greedy decoding, 2048 total tokens. The GPU model is not recorded in the files; the run log names it as Modal A10 or
  A10G (400-step runs, about 7 minutes of training each).
- `*-evalmini.json`: `evaluate.py --eval-mini`, which ran `teams/09-evaluation/harness/run_eval_mini.py --model <model>
  --profile mini --tasks arc_challenge hellaswag --dtype float32 --device cpu` (the full command is in each file's
  `eval_mini.command`). Recorded: device `cpu`, lm_eval 0.4.13, transformers 5.20.2, python 3.12.16.
- Note for `forgetting.py`: the two files of a run differ in `device` (cuda vs cpu). It compares the first value it
  meets after merging, so pass the `-test.json` file first for both base and tuned (as in the command in the pull
  request) and the check passes.

## `corrected_target_bpb.json`

An overlap in the G10-surface span bytes made the stored `target_bytes` slightly too large. The corrected bits per
byte was recomputed from the recorded `nll_nats` and the repaired byte count; the reports here are the originals and
are not changed. The shift is at most 0.00008 (largest in this folder: 0.000075) and changes no ranking. Training never
read the field. `forgetting.py` does not use `target_bpb`; the `forgetting.bpb_all` field it uses is a different
measure (held-out text) and is not affected.

## Redactions

Only path prefixes were replaced, no number or other field was changed (checked by comparing the parsed JSON):
- local checkout path before `teams/09-evaluation/...` is now `<repo>/`;
- the local model cache path in the base `eval_mini.command` is now `<hf-cache>/`;
- the slice work folder in the other `eval_mini.command` values is now `<slice>/`.
`model` fields such as `/vol/runs/<run>/model` are container paths of the cloud run and were left as they are.
