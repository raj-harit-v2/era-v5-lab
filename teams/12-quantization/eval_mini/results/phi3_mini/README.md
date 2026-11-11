# Phi-3-mini-4k-instruct, bf16 vs Q4_K_M (eval_mini)

Run by shishir13 on Kaggle 2xT4, 2 Nov 2026, with `eval_mini.ipynb` (settings cell only: `MODEL`, `REVISION`, `FORMATS`, `RUN_BY`,
`LIMIT = None`), llama.cpp b11669, llama-cpp-python 0.3.36. Model `microsoft/Phi-3-mini-4k-instruct`, revision
`f39ac1d28e925b323eae81227eaba4464caced4e`.

Kaggle version (Version 2 of the notebook, full run, 6252 s):
https://www.kaggle.com/code/shishir13/notebookcb55b61331?scriptVersionId=364966760

## Files

`scores.csv`, `paired.md`, `environment.json`, per format `summary.json` plus one `*.samples.jsonl` per task (one row per
question with the per-item scores only; the benchmark `target` and `response` are removed, as in PR #306), and `logs/` (the two checks and the Q4_K_M quantize log).

## Differences from the OLMoE runs

- **Tolerance of check 3.** `TOL` in check 3 of `test_llamacpp_lm.py` is 0.10, not 0.05: Q4_K_M had a cache-vs-fresh difference of
  0.0786 (bf16: 0.0000). Checks 1 and 2 passed (`log p(' Paris')` -0.095 = generation -0.095). The notebook version is therefore
  `ec7db60966d6+phi3tol0.10`, and these runs must not be combined with the OLMoE ones. Diagnostic rerun of Q4_K_M with the prefix cache off (every request scored from scratch,
  notebook `ec7db60966d6+phi3nocache`, TOL 0.05): check 3 passes (`logs/test_llamacpp_lm_Q4_K_M_nocache.log`, max diff 0.0000, trivially,
  as both paths are then from scratch). Scores are unchanged within noise (mean 64.04 vs 64.02): ARC 54.6/54.6, HellaSwag 64.8/64.5,
  MMLU 69.3/69.5, GSM8K 74.5/74.5, TruthfulQA 57.0/57.0 (no-cache/cached). 10 of 1,870 items flip (ARC 6, HellaSwag 1, MMLU 3). So the
  0.0786 comes from the cached path (reused prefix, small continuation batch) and flips a few near-tie items; the cause inside the
  quantized kernels is not proven. The scores in `runs.csv` are from the cached run.
- **Model fields in `summary.json`.** `run_mini_gguf.py` writes the OLMoE default into `run_meta.model`, `run_meta.model_revision`
  and the same two fields of every record. **I corrected them in the committed files** (to `microsoft/Phi-3-mini-4k-instruct` and the
  revision above), in `run_meta` and in all 8 records of each file, and added `run_meta.fields_corrected_by_hand`. Nothing else in the
  two files was changed. The unmodified output is in the Kaggle version above. `run_mini_gguf.py` itself still has the bug.
- `gen_tok_s` is not measured and is empty in `runs.csv`.
