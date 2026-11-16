# Smoke run of train_week2.py for the rotation job request (14 Nov 2026)

This is the test log for `../../2026-11-14-rotation-experts32-seed1243.md`. It shows that `train_week2.py` runs the arm of the request end to end. It is a smoke run on synthetic text. It is not a quality result, and the summary says `eligible_for_quality_comparison: false`.

- **What ran:** `train_week2.py` at lab commit `71bc0fb` (the trainer commit of the TSAI T2 runs), `exp3_experts_32.yaml`, seed 1243, CPU, fp32, 6 steps, context 160, batch 1, `--smoke --no-checkpoint`, `--lr 0.001`, with `configs/runtime.yaml`. The job itself uses `configs/runtime_fast.yaml` and the TSAI speed fixes; that file is not in the repo, so it was not part of this smoke.
- **Model:** 388,112,896 parameters (T2 shape, 8 layers, 32 routed and 1 shared expert, top-2, expert width 768).
- **Result:** exit 0; all 6 steps with finite losses. Training CE goes from 11.786 to 8.520. Training wall time 36.5 s, whole command 46.4 s, peak memory 6083 MiB (Kaggle CPU, 4 cores). The log is `smoke.log`; `exp3-experts32/` has `manifest.json`, `summary.json`, `metrics.jsonl`, `losses.txt` and `total_losses.txt`.
- **Trainer check:** the sha256 of all 9 harness files in `manifest.json` `sources` equal the files at `71bc0fb`.
- **Config check:** `exp3_experts_32.yaml` at `71bc0fb` with `runtime.yaml` loads with `week2.config.load_runtime`, and `validate()` returns 0 errors for this smoke config; built on the meta device (no memory used) the model has 388,112,896 parameters, the number the smoke manifest reports.
- **Tokenizer:** tokenizer v0, sha256 `2de039f2…f8e5`, the one in `teams/03-tokenizer/v0/SHA256SUMS`.
- **Byte table:** raw P32 table, content sha256 `47d411a9…f869f`, the same as in the TSAI attention records.
- **Text:** `inputs/synthetic_train.jsonl` (64 documents) and `inputs/synthetic_heldout.jsonl` (8 documents) of generated word lists, written for smoke tests.
- **Environment:** Kaggle CPU, Python 3.13.18, torch 2.11.0+cpu, tokenizers 0.23.3, numpy 2.1.3, PyYAML 6.0.3.

The paths in `smoke.log` are shown as `./inputs/...` and `./out/...`, and the interpreter as `python`, as in the #450 log. The run read the same files from the Kaggle dataset input folder and wrote to the Kaggle working folder.

This smoke does not test the official run: no GPU, bf16, full context 2048, 1,221 steps or the real `heldout_v1` and training bundle. TSAI runs those.
