## Qwen3-1.7B: bf16 vs Q4_K_M (eval_mini)

G12 rotation task (week 2). Model `Qwen/Qwen3-1.7B` (Apache 2.0; dense, 28 layers, 2.03B parameters in the GGUF),
revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`. One run of G9's `eval_mini` profile (1,870 items) on the bf16 GGUF
and on the Q4_K_M GGUF, same questions, same runtime, same machine, seed 42.

### Results

| Benchmark (items)    | bf16  | Q4_K_M | Difference (95% CI)  | McNemar p  |
| -------------------- | ----- | ------ | -------------------- | ---------- |
| ARC Challenge (500)  | 43.6  | 42.0   | -1.6 (-4.7 to +1.5)  | 0.374      |
| HellaSwag (400)      | 52.8  | 49.2   | -3.5 (-6.6 to -0.4)  | 0.038      |
| MMLU (570)           | 59.1  | 60.0   | +0.9 (-2.1 to +3.8)  | 0.640      |
| GSM8K 5-shot (200)   | 66.0  | 62.0   | -4.0 (-9.7 to +1.7)  | 0.229      |
| TruthfulQA MC2 (200) | 47.9  | 41.5   | -6.4 (-9.6 to -3.2)  | not applicable |
| Mean of the five     | 53.88 | 50.96  | -2.92                |            |

Scores are in points (acc_norm for ARC and HellaSwag, acc for MMLU and TruthfulQA MC2, exact_match for GSM8K). The
mean is the unweighted mean of the five, as in `runs/runs.csv`. Two drops are significant: **HellaSwag (-3.5, p 0.038)**
and **TruthfulQA MC2 (-6.4, the 95% CI excludes 0)**. ARC, MMLU and GSM8K are within noise at these sample sizes. The
scores come from the no-chat-template eval_mini profile, so they are not comparable to numbers published for this model.

The loss is larger than for the bigger models in this folder (Phi-3-mini -0.9 mean, Qwen3-4B about -0.8). This
fits the usual pattern that small models lose more at 4 bits. Qwen3-1.7B at Q4_K_M is also 5.35 bits per weight, not
~4.9: the 151,936 x 2,048 embedding and output matrices are a large share of a 2B model, and the output stays at Q8_0.

| | bf16 | Q4_K_M |
| --- | --- | --- |
| File size | 4.07 GB | 1.36 GB |
| Bits per weight | 16.02 | 5.35 |
| Generation speed (tokens/s, median of 3) | 58.8 | 118.4 |
| Eval time (s, sum of the five tasks) | 1,718 | 1,063 |
| Quantization time (s) | not applicable | 8.2 |

Size reduction 66.6%, compression ratio 3.00x.

### Guard test (`test_llamacpp_lm.py`)

- **bf16: PASS** (all four checks).
- **Q4_K_M: checks 1-3 PASS, check 4 FAILS.** Checks 1-3 are the shifted-logprob guards: log p(" Paris") = -0.633,
  equal to greedy generation's -0.633, far from the off-by-one value -9.869, and the prefix cache changes no score.
  So the backend reads the log-probabilities correctly.
- Check 4 is a sanity item ("Which gas do plants absorb ... ?"). Q4_K_M scores " Oxygen" (-1.14) above
  " Carbon dioxide" (-1.43). The supplied run notes attribute this to the model: bf16 picks carbon dioxide by 2.3 nats on both Metal
  and CPU, and Q4_K_M picks oxygen on **both Metal and CPU** (CPU: -0.77 vs -1.08). The committed log confirms the Metal sanity-item failure; separate CPU logs were not supplied. The test was not changed; the failure is reported here and in the `runs.csv` notes.

### How it was made

- Conversion and quantization with llama.cpp `b11669` (commit 620d222). `convert_hf_to_gguf.py` reads the bf16
  safetensors and writes a bf16 GGUF (architecture `qwen3`). `llama-quantize --output-tensor-type q8_0` makes Q4_K_M.
- G12's rules are checked by `gguf_check_*.json` (both `ok: true`): `output.weight` is Q8_0 in the quantized file and
  BF16 in the bf16 file. The model is dense, so there is no router (`router_type` is `-` in `runs.csv`).
- Evaluation with llama-cpp-python 0.3.36 (Metal, all layers on the GPU, n_ctx 2048) and lm-eval 0.4.13, in a venv
  without torch or transformers. The eval code is pinned to lab commit `048de644e7b5`, the same as
  `sarvam-30b/`: its `run_mini_gguf.py` writes no item text, and `combine.py` from that commit accepts both runs. G9's
  `run_eval_mini.py` has sha256 prefix `e91bd8b37975d098`.
- Hardware: Apple M4 Pro, 24 GB unified memory, own machine (not Kaggle). Both formats ran on the same machine.

### Files

| File | What |
| --- | --- |
| `bf16/`, `Q4_K_M/` | `summary.json` and one `*.samples.jsonl` per task: task, doc_id, filter and the metric values. No question, answer or model output text (eval firewall). |
| `paired.md` | McNemar comparison of Q4_K_M against bf16 on the same items. |
| `scores.csv`, `scores_long.csv` | Scores per task, and scores with standard error, item count and seconds. |
| `environment.json` | Versions, hardware, GGUF sizes and the lab commit. |
| `gguf_check_bf16.json`, `gguf_check_Q4_K_M.json` | Tensor types and the G12 rule check for each GGUF. |
| `speed_bf16.json`, `speed_Q4_K_M.json` | Three generation-speed runs per format (128 greedy tokens). |
| `logs/` | `convert.log`, `quantize_Q4_K_M.log` and the two guard-test logs (llama.cpp load lines removed). |

`runs/runs.csv` has the two new rows at the end; the existing rows are unchanged.

### Reproduction and artifact validation

Run by `LokeshJatangi` on 9 November 2026. The notebook fingerprint was not recorded; the combine validator checks the recorded settings instead and reports a warning.

From the repository root, regenerate the comparison and validate the two runs:

```bash
python teams/12-quantization/eval_mini/paired.py teams/12-quantization/eval_mini/results/qwen3-1.7b --base bf16
python teams/12-quantization/eval_mini/combine.py teams/12-quantization/eval_mini/results/qwen3-1.7b --out /tmp/qwen3-1.7b-combined
```

For a model rerun, use the conversion and evaluation tooling at the pinned lab commit above, the pinned model revision, bf16 conversion, and `llama-quantize --output-tensor-type q8_0` for Q4_K_M. Use the same G9 mini profile, seed 42, and n_ctx 2048 for both formats. The original model binaries are not included. Artifact validation does not rerun inference or establish the cause of the recorded sanity failure.

TruthfulQA MC2 uses paired continuous per-item differences for its confidence interval; McNemar's binary test does not apply. Significance statements above are nominal, without correction for multiple comparisons.

### GGUF checksum evidence

The recorded evaluation code commit is `048de644e7b5e85e23177add0458f7fe124566b5`. This identifies code provenance, not the model file contents. The supplied artifacts do not include SHA-256 digests of the bf16 and Q4_K_M GGUFs, and the original GGUF binaries are not available in this submission. A verified `runs/manifest_<date>.json` requires hashes computed from those exact original files; tensor checks and byte sizes cannot substitute for file hashes.
