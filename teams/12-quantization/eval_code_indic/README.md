# G9's eval-mini code + Indic part on OLMoE GGUF files

Week 2, Member B: runs G9's code + Indic half of eval-mini v0
([`teams/09-evaluation/results/eval_mini_v0_code_indic.json`](../../09-evaluation/results/eval_mini_v0_code_indic.json),
defined by `harness_code_indic/eval_mini_v0_spec.json`) on bf16, Q8_0, Q4_K_M and Q3_K_M.

| Part | Tasks | Items | How |
|---|---|---|---|
| lm-eval | MMLU-Pro 300, GSM8K 100, Belebele hin/tel/tam 100 each, MILU Hindi/Telugu/Tamil/Bengali 100 each | 1,300 | lm_eval 0.4.13, 5-shot, the spec's doc_ids, lm_eval's default seeds (as G9's `run_lm_eval.py`) |
| Code | HumanEval+ 164, MBPP+ 378 | 542 | evalplus 0.3.1, greedy, base (completion) prompt, evalplus's stop strings, 768 new tokens (as G9's `run_codegen.py`); executed by evalplus |

Every format runs through the same backend as [`../eval_mini/`](../eval_mini/): llama-cpp-python in-process
(`llamacpp_lm.py`), each file checked first by `test_llamacpp_lm.py` (the shifted-logprob guard). So a quantized
score is compared only with the bf16 score from the same runtime and the same eval set.

**Results:** [`results/RESULTS.md`](results/RESULTS.md) (Kaggle 2×T4, 1 Nov 2026). Rows in [`../runs/runs.csv`](../runs/runs.csv).

| File | What |
|---|---|
| [`run_code_indic_gguf.py`](run_code_indic_gguf.py) | one GGUF through both parts; `summary.json` + per-item `*.samples.jsonl`; resumable |
| [`paired.py`](paired.py) | each format vs bf16 on the same items: difference, 95% CI, McNemar's exact test |
| [`eval_code_indic.ipynb`](eval_code_indic.ipynb) | Kaggle or Colab notebook: build, convert, run every format, compare |
| [`build_notebook.py`](build_notebook.py) | rebuilds the notebook; reuses the setup, build and conversion cells of `../eval_mini/build_notebook.py` |
| [`to_runs_csv.py`](to_runs_csv.py) | appends one `../runs/runs.csv` row per format from a run folder; router and output types come from `environment.json` or, failing that, the run's convert/quantize logs |

## Notes

- **Context.** `n_ctx` is 4096, OLMoE's trained context. Belebele's 5-shot prompts (long passages, and Indic
  scripts take many tokens in OLMoE's tokenizer) do not fit and are left-truncated, as lm_eval's HF backend does,
  so the oldest shots are cut first. Each task records how many requests were truncated
  (`truncated_requests` in `summary.json`). The same truncation applies to every format.
- **MILU is gated** on Hugging Face. Accept its terms, make a read token and add it as the secret `HF_TOKEN`
  (Kaggle: Add-ons → Secrets). The notebook checks access before it starts; `SKIP_GATED = True` leaves MILU out.
- **evalplus without torch.** The evaluation venv must not contain torch or transformers (lm_eval imports them,
  and Kaggle's preinstalled ones fail). evalplus is installed with `--no-deps` plus the packages its code path
  imports, pinned. Its HF decoder is replaced by a llama-cpp-python one with the same prompt, stop strings, token
  limit, cut and tab replacement. G9's three evalplus fixes are covered: the stop list is copied per decoder,
  llama.cpp's stop strings do not stack across problems, and the tokenizer is the GGUF's own (no transformers).
- **Linux only for execution.** evalplus sets memory limits that macOS refuses; Kaggle and Colab are Linux.

## Run

```bash
# one format, on a Linux machine with llama-cpp-python 0.3.36, lm_eval 0.4.13 and evalplus 0.3.1
python run_code_indic_gguf.py --gguf OLMoE-1B-7B-0924-Q8_0.gguf --format Q8_0 --out runs \
    --g9-dir <upstream main>/teams/09-evaluation/harness_code_indic
python paired.py runs --base bf16
```

**Kaggle:** import `eval_code_indic.ipynb`, Accelerator **GPU T4 x2**, Internet **on**, set `FORMATS` and `RUN_BY`,
then **Save Version → Save & Run All (Commit)**. `LIMIT = 3` is a quick end-to-end check.
