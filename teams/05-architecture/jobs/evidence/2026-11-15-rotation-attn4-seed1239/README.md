# Smoke run of train_week2.py for the rotation job request (15 Nov 2026)

This is the test log for `../../2026-11-15-rotation-attn4-seed1239.md`. It shows that `train_week2.py` runs the arm of the request end to end. It is a smoke run on synthetic text. It is not a quality result, and the summary says `eligible_for_quality_comparison: false`.

- **What ran:** `train_week2.py` at lab commit `71bc0fb` / `ae4c03d`, `attn4_gate.yaml`, seed 1239, CPU, fp32, 6 steps, context 160, batch 1, `--smoke --no-checkpoint`, `--lr 0.001`, with `configs/runtime.yaml`.
- **Model:** 235,531,264 parameters (T2 shape, 8 layers, 16 routed and 1 shared expert, top-2, SwiGLU, with Sigmoid Attention Gate $W_g$ 512x512 per layer).
- **Result:** exit 0; all 6 steps with finite losses. Training CE goes from 11.964 to 6.878. Training wall time 24.8 s, peak memory ~4210 MiB. The log is `smoke.log`; `attn4-gate/` has `manifest.json`, `summary.json`, `metrics.jsonl`, `losses.txt` and `total_losses.txt`.
- **Trainer check:** all harness files in `manifest.json` `sources` verified.
- **Config check:** `attn4_gate.yaml` with `runtime.yaml` loads with `week2.config.load_runtime`, and `validate()` returns 0 errors for this smoke config.
- **Tokenizer:** tokenizer v0, sha256 `2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5`.
- **Byte table:** raw P32 table, content sha256 `47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f`.
- **Text:** `inputs/synthetic_train.jsonl` (64 documents) and `inputs/synthetic_heldout.jsonl` (8 documents) of generated word lists, written for smoke tests.

The paths in `smoke.log` are shown as `./inputs/...` and `./out/...`, and the interpreter as `python`.

This smoke does not test the official run: no GPU, bf16, full context 2048, 1,221 steps or the real `heldout_v1` and training bundle. TSAI runs those.
