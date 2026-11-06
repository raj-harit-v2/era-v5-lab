## Sarvam-30B: bf16 vs Q4_K_M (eval_mini)

G12 rotation task. Model `sarvamai/sarvam-30b` (Apache 2.0; mixture of experts, 128 experts, 32.15B parameters),
revision `071ae95e933605ca1104a6b4524a36a98488efa4`. One run of G9's `eval_mini` profile (1,870 items) on the bf16 GGUF
and on the Q4_K_M GGUF, same questions, same runtime, seed 42.

### Results

| Benchmark (items)    | bf16 | Q4_K_M | Difference (95% CI)  | McNemar p |
| -------------------- | ---- | ------ | -------------------- | --------- |
| ARC Challenge (500)  | 48.6 | 48.0   | -0.6 (-2.8 to +1.6)  | 0.720     |
| HellaSwag (400)      | 61.0 | 60.8   | -0.2 (-2.4 to +1.9)  | 1.000     |
| MMLU (570)           | 73.2 | 71.4   | -1.8 (-3.9 to +0.4)  | 0.154     |
| GSM8K 5-shot (200)   | 59.5 | 50.0   | -9.5 (-17.9 to -1.1) | 0.037     |
| TruthfulQA MC2 (200) | 50.0 | 48.6   | -1.4 (-2.8 to -0.0)  | not paired |
| Mean of the five     | 58.45 | 55.75 | -2.70                |           |

Scores are in points (acc_norm for ARC and HellaSwag, acc for MMLU and TruthfulQA MC2, exact_match for GSM8K). The
mean is the unweighted mean of the five, as in `runs/runs.csv`. Only GSM8K is a significant drop; the other four are
within the noise of these sample sizes. The scores come from the no-chat-template eval_mini profile, so they are not
comparable to numbers published for this model.

| | bf16 | Q4_K_M |
| --- | --- | --- |
| File size | 64.34 GB | 19.84 GB |
| Bits per weight | 16.01 | 4.94 |
| Generation speed (tokens/s, median of 3) | 55.7 | 76.5 |
| Eval time (s) | 6,284 | 5,885 |
| Quantization time (s) | not applicable | 732 |

Size reduction 69.2%, compression ratio 3.24x.

### How it was made

- Conversion and quantization with llama.cpp `b11669` (commit 620d222). `convert_hf_to_gguf.py` reads the fp32
  safetensors and writes a bf16 GGUF (architecture `bailingmoe2`, 264 tensors). `llama-quantize --output-tensor-type q8_0`
  makes Q4_K_M. Q4_K_M here is 26.5B parameters in Q4_K, 4.5B in Q6_K, 1.07B in Q8_0 (`output.weight`) and 9.6M in F32.
- G12's two rules hold and are checked by `gguf_check_*.json` (both `ok: true`): `output.weight` is Q8_0 in the quantized
  file, and the router (`ffn_gate_inp`) and the per-expert routing bias (`exp_probs_b`) stay F32.
- Evaluation with llama-cpp-python 0.3.36 (CUDA, all layers on GPU, n_ctx 2048) and lm-eval 0.4.13.
  The eval code is the version from PR #221 (lab commit `048de644e7b5`): its `run_mini_gguf.py` writes no item text, and
  `combine.py` from the same commit accepts both runs. G9's `run_eval_mini.py` has sha256 prefix `e91bd8b37975d098`.
- Hardware: two NVIDIA RTX 6000 Ada (48 GB each), on one machine, not Kaggle. Both formats ran on the same machine.
- `test_llamacpp_lm.py` (the shifted-logprob guard) passed for both GGUFs at the default tolerance of 0.05, with no
  change to the test. Logs are in `logs/`.
- The model files were fetched once (pinned revision) and copied to the server, which has no Hugging Face access, so the
  evaluation ran with the offline switches on.

### Files

| File | What |
| --- | --- |
| `bf16/`, `Q4_K_M/` | `summary.json` and one `*.samples.jsonl` per task: task, doc_id, filter and the metric values. No question, answer or model output text (eval firewall). |
| `paired.md` | McNemar comparison of Q4_K_M against bf16 on the same items. |
| `scores.csv`, `scores_long.csv` | Scores per task, and scores with standard error, item count and seconds. |
| `environment.json` | Versions, hardware, GGUF sizes and the lab commit. |
| `gguf_check_bf16.json`, `gguf_check_Q4_K_M.json` | Tensor types and the G12 rule check for each GGUF. |
| `speed_bf16.json`, `speed_Q4_K_M.json` | Three generation-speed runs per format. |
| `logs/` | `convert.log`, `quantize_Q4_K_M.log` and the two guard-test logs. The per-task run logs hold only progress bars and are not included. |

`runs/runs.csv` has the two new rows at the end; the existing rows are unchanged.

### Notes

- The converter prints a tokenizer warning for this model: `add_bos_token` is False in `tokenizer_config.json` but the
  tokenizer post-processor adds `<bos>`, and the converter follows the post-processor. Both GGUFs come from the same
  conversion, so the comparison is unaffected.
- Item text and model outputs are not in this folder or in the pull request (eval firewall, TSAI #269).
