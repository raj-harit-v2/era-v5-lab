# Llama-3.2-1B-Instruct, bf16 vs Q4_K_M (eval_mini)

Run by vpw on Google Colab (single Tesla T4, 15 GB), 4 Nov 2026, with `eval_mini.ipynb` (settings cell only: `MODEL`,
`REVISION`, `FORMATS = ["bf16", "Q4_K_M"]`, `RUN_BY`, `LIMIT = None`), llama.cpp b11669, llama-cpp-python 0.3.36.
Model `unsloth/Llama-3.2-1B-Instruct` (ungated mirror of the gated `meta-llama/Llama-3.2-1B-Instruct`), revision
`5a8abab4a5d6f164389b1079fb721cfab8d7126c`.

Both formats ran in the same notebook session, so the paired comparison against bf16 is made directly (no
`combine.py` needed); `combine.py` is for merging separate members' runs.

## Files

`scores.csv`, `scores_long.csv`, `paired.md`, `environment.json`, per format `summary.json` plus one
`*.samples.jsonl` per task (one row per question, so the scores can be rechecked from the repo), and `logs/` (the
two `test_llamacpp_lm.py` checks and the Q4_K_M quantize log).

## Results

| Task | bf16 | Q4_K_M | Difference | McNemar p |
|---|---|---|---|---|
| ARC-Challenge | 35.4 | 37.0 | +1.6 | 0.268 |
| HellaSwag | 55.8 | 54.5 | -1.2 | 0.227 |
| MMLU | 48.1 | 47.9 | -0.2 | 1.000 |
| GSM8K (5-shot) | 30.5 | 26.5 | -4.0 | 0.229 |
| TruthfulQA-mc2 | 43.8 | 44.4 | +0.5 | - |

Mean score: bf16 42.71, Q4_K_M 42.05 (-0.66 pp). No task differs significantly from bf16 (all McNemar p > 0.2). Full
per-task CI and b/c counts in `paired.md`.

Model: 2.48 GB (16.00 BPW) -> 0.87 GB (5.59 BPW) at Q4_K_M, 2.85x smaller. Dense model (no router); tied embeddings
(`tie_word_embeddings: true`), so there is no separate `output.weight` tensor — `--output-tensor-type q8_0` quantizes
`token_embd.weight` itself (same as Qwen2.5-1.5B-Instruct in `runs.csv`, also tied).

## Differences from the OLMoE runs

- **No GPU memory fallback needed.** The model is small enough (1.24B params) that `n_gpu_layers=-1` (all layers)
  worked for both formats on a single T4; `BF16_FALLBACK_GPU_LAYERS` was unused.
- **Model fields in `summary.json`.** `run_mini_gguf.py` writes the OLMoE default into `run_meta.model` and
  `run_meta.model_revision`. **I corrected those two fields in the committed files** (to
  `unsloth/Llama-3.2-1B-Instruct` and the revision above) and added `run_meta.fields_corrected_by_hand` with the
  original values. Nothing else in the two files was changed. `run_mini_gguf.py` itself still has the bug (same
  issue noted in the Phi-3-mini results).
- **No Drive mount.** Colab's Drive mount failed (`credential propagation was unsuccessful`); output went to the
  runtime disk instead, and the notebook's own fallback (last cell, base64-encoded zip in the cell output) was used
  to recover the results after the session ended — no results were lost, just the "resume on reconnect" convenience.
- `gen_tok_s` is not measured and is empty in `runs.csv`.
- `quant_time_s` (110.9 s) is the `llama-quantize` wall time alone; `eval_time_s` is `run_mini_gguf.py`'s own
  per-task wall-clock sum (bf16 1194.2 s, Q4_K_M 660.2 s), excluding quantize and the `test_llamacpp_lm.py` check.
