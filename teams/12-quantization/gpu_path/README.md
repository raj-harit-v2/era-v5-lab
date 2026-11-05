# GPU path: llm-compressor W4A16 served by vLLM

Week 2, Member C. The GPU path from [`tools/tools.md`](../tools/tools.md): `allenai/OLMoE-1B-7B-0924` @ `6d84c48581ec`
quantized to **W4A16** (4-bit weights, 16-bit activations) with **llm-compressor GPTQ**, served by **vLLM**, and scored
on G9's eval_mini with the same per-item logs as [`eval_mini/`](../eval_mini/). W4A16 needs no FP8, so it runs on the
Colab and Kaggle GPUs (T4, P100, L4, A100).

| File | What |
|---|---|
| [`gpu_path.ipynb`](gpu_path.ipynb) | Kaggle or Colab notebook: download, check, quantize, check, score bf16 and W4A16, compare, zip |
| [`quantize_w4a16.py`](quantize_w4a16.py) | llm-compressor `oneshot` with `GPTQModifier(scheme="W4A16", ignore=["lm_head", "re:.*mlp.gate$"])`; `--method rtn` is the no-calibration fallback |
| [`model_check.py`](model_check.py) | reads the safetensors headers: router and `lm_head` dtypes, experts and attention packed or not, size, bits per weight; writes the SHA-256 manifest |
| [`run_mini_vllm.py`](run_mini_vllm.py) | G9's eval_mini profile through lm_eval's vLLM backend, in G9's record format, with a log-probability check before scoring |
| [`add_runs_rows.py`](add_runs_rows.py) | turns the results into `runs/runs.csv` rows (prints them; `--write` appends) |
| [`test_gpu_path.py`](test_gpu_path.py) | checks for `model_check.py` and `add_runs_rows.py` on made-up headers; no GPU needed |

## Recipe

- **Scheme:** W4A16, symmetric INT4, group size 128 (compressed-tensors `pack-quantized`), every `Linear` in the
  decoder: attention and all 64 × 16 experts.
- **Kept in BF16:** `lm_head` and the 16 router gates. In the Hugging Face OLMoE model the router is `mlp.gate`
  (the open check in `tools.md`). `model_check.py` reads the dtype of `model.layers.<n>.mlp.gate.weight` in the
  output files and stops the run if it is not BF16 or F32.
- **Calibration (GPTQ):** 256 documents × 1,024 tokens from `HuggingFaceFW/fineweb-edu` `sample-10BT`, about 262k
  tokens. It is web text, not a benchmark, so it cannot leak eval_mini. With top-8 of 64 experts each expert sees about
  33k tokens.
- **Check after quantizing:** `model_check.py --expect-quantized` fails unless every expert and attention projection
  is stored packed. That catches a silent skip, for example if a newer transformers stores the experts as one fused
  tensor that llm-compressor does not treat as a `Linear`.

## Comparing scores

G12 rule: a quantized score is compared only with the bf16 score from the same runtime and the same eval set. So the
notebook scores **bf16 through vLLM too**, with the same settings (tensor parallel, `max_model_len` 2048, seed 42).
The llama.cpp rows in `runs.csv` are a different runtime and are not compared with these rows.
`../eval_mini/paired.py` compares W4A16 with vLLM bf16 item by item (paired difference, 95% CI, McNemar p).

On a GPU without bf16 compute (T4, P100) vLLM computes in **fp16** for both formats. The weights in the files stay
BF16. The dtype used is recorded in every summary and row.

## Run

**Kaggle:** import `gpu_path.ipynb`, Accelerator **GPU T4 x2**, Internet **on**.
1. `LIMIT = 5`, `SMOKE = True`: run all cells interactively. This checks every step end to end (GPTQ with 32
   samples, the router check, both formats load in vLLM and pass the log-probability check).
2. `LIMIT = None`, `SMOKE = False`: **Save Version → Save & Run All (Commit)**. Unzip the results zip from the
   version's Output tab into `results/` here.
3. `python add_runs_rows.py --runs results/runs --manifests results/manifest_bf16.json results/manifest_W4A16.json --write`
   appends the two rows to `runs/runs.csv`.

**Colab:** the same notebook. L4 or A100 runtimes compute in bf16 and use vLLM's Marlin kernels.

Committed per run: `manifest_*.json` (SHA-256 of every model file), `quantize_meta.json`, `environment.json`,
`runs/<format>/summary.json` and `*.samples.jsonl`, `paired.md`. The weights stay out of the repo.
`*.samples.jsonl` has one row per question with task, doc_id, filter and metric values only: the `target` and
`response` text are never written (eval firewall), as in [`eval_mini/`](../eval_mini/).

## Open checks (answered by the first smoke run)

- **vLLM W4A16 MoE on a T4:** vLLM's Marlin MoE kernel needs compute capability 8.0. On a T4 (7.5) vLLM has to use
  its Triton W4A16 MoE kernel instead. If W4A16 does not load, or fails the log-probability check, rerun on an L4
  or A100 (Colab) and record that machine.
- **GPTQ on rarely used experts:** if GPTQ fails on an expert that saw too few calibration tokens, use more
  `--samples` or `METHOD = "rtn"`, and say so in the row.
- **Versions:** the first run installs the current `llmcompressor` and `vllm`. The versions are saved in
  `environment.json`; pin them in the notebook settings after the first good run.

## Results

To be filled after the full run: one row each for vLLM bf16 and W4A16 (bits per weight, size, score per task,
paired difference with bf16, quantize time, eval time, tokens per second, machine).
