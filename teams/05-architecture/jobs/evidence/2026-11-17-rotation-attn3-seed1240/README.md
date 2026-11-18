# Smoke run of train_week2.py for the rotation job request (17 Nov 2026)

This is the test log for `../../2026-11-17-rotation-attn3-seed1240.md`. It shows that `train_week2.py` runs the arm of the request end to end. It is a smoke run on synthetic text. It is not a quality result, and the summary says `eligible_for_quality_comparison: false`.

- **What ran:** `train_week2.py` at lab commit `71bc0fb` (the trainer commit of the TSAI T2 runs), `attn3_prope_half.yaml`, seed 1240, CPU, fp32, 6 steps, context 160, batch 1, `--smoke --no-checkpoint`, `--lr 0.001`, with `configs/runtime.yaml`. It ran without the TSAI speed-fix diff, which is not in the repo. Machine: Apple M1, 8 GB, Python 3.10.12, torch 2.5.1 (`harness/requirements-week2.txt`).
- **Model:** 237,052,416 parameters (from `manifest.json`): the T2 shape, with 8 layers, 16 routed and 1 shared expert, top-2, SwiGLU. `manifest.json` records `model.rotary_fraction: 0.5`, so RoPE is applied to 32 of the 64 head dimensions.
- **Result:** exit 0, and all 6 steps logged finite losses. Training CE by step was 11.99, 9.46, 8.54, 11.15, 6.38 and 9.97. With batch 1 and 160 tokens per step, the per-step CE is noisy. The held-out BPB on the synthetic text fell from 2.7719 at step 0 to 2.0702 at step 6. Training wall time was 173.6 s and peak memory 1,269 MiB. The log is `smoke.log`. `attn-3/` has `manifest.json`, `summary.json`, `metrics.jsonl`, `losses.txt` and `total_losses.txt`.
- **Config check:** `harness/check_week2.py` on `attn3_prope_half.yaml` with `runtime.yaml` and `--lr 0.001` exits 0 ("Runtime specification valid"). `tests/test_week2_attention.py` at `71bc0fb`: 17 passed.
- **Tokenizer:** tokenizer v0, sha256 `2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5`.
- **Byte table:** raw P32 table, content sha256 `47d411a9c6cae6fa2075935567243e51f4efbc377ccef3eef42c32fce66f869f` (`artifacts.table_content_sha256` in `manifest.json`).
- **Text:** the smoke inputs already in the repo: `../2026-11-15-rotation-attn4-seed1239/inputs/` (`synthetic_train.jsonl`, 64 documents, and `synthetic_heldout.jsonl`, 8 documents, of generated word lists, plus `tokenizer_v0.json` and `raw_table_P32.npz`). They are not copied here.

The paths in `smoke.log` are shown as `./inputs/...` and `./out/...`, and the interpreter as `python`.

This smoke does not test the official run: no GPU, bf16, full context 2048, 1,221 steps or the real `heldout_v1` and training bundle. TSAI runs those.
