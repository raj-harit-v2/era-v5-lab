# runs_Q3_K_M-Q2_K: log summary

- Run by: s9k96; platform kaggle; GPU Tesla T4, 15360 MiB, 580.178.04 + Tesla T4, 15360 MiB, 580.178.04; CUDA arch 75
- Notebook version: 70829160c1bd
- Model allenai/OLMoE-1B-7B-0924 @ 6d84c48581ec; LIMIT None; formats Q3_K_M, Q2_K
- Versions: python 3.13.15, llama-cpp-python 0.3.36, lm_eval 0.4.13, datasets 5.1.0, llama.cpp b11669 (convert + quantize); torch/transformers visible to the eval: False/False
- Started 2026-10-29T09:13:01, finished 2026-10-29T10:18:31

## Build

- llama-cpp-python CUDA wheel: built
- llama-quantize: built; The CXX compiler identification is GNU 13.3.0
- bf16 GGUF: converted, OLMoE-1B-7B-0924-bf16.gguf: n_tensors = 195, total_size = 13.8G; 13,844,565,376 bytes

## Per format

### Q3_K_M
- GGUF 3,368,879,488 bytes; GPU layers -1 (-1 = all); eval wall clock 954 s
- quantize: [ 1/ 195] output.weight - [ 2048, 50304, 1, 1], type = bf16, converting to q8_0 .. size = 196.50 MiB -> 104.39 MiB
- quantize: llama_model_quantize_impl: quant size = 3211.12 MiB (3.89 BPW)
- quantize: llama_quantize: quantize time = 197960.02 ms
- logprob test (test_llamacpp_lm_Q3_K_M.log, kept): PASS
- Q3_K_M/arc_challenge: acc_norm=0.4660 +/- 0.0223 n=500 in 103s (0.21s/item), 500 per-item rows
- Q3_K_M/hellaswag: acc_norm=0.6475 +/- 0.0239 n=400 in 148s (0.37s/item), 400 per-item rows
- Q3_K_M/mmlu: acc=0.4947 +/- 0.0201 n=570 in 160s (0.28s/item), 570 per-item rows
- Q3_K_M/gsm8k: exact_match=0.0900 +/- 0.0203 n=200 in 233s (1.17s/item), 400 per-item rows
- Q3_K_M/truthfulqa_mc2: acc=0.3671 +/- 0.0275 n=200 in 97s (0.48s/item), 200 per-item rows
- errors in run log: 0

### Q2_K
- GGUF 2,587,712,896 bytes; GPU layers -1 (-1 = all); eval wall clock 904 s
- quantize: [ 1/ 195] output.weight - [ 2048, 50304, 1, 1], type = bf16, converting to q8_0 .. size = 196.50 MiB -> 104.39 MiB
- quantize: llama_model_quantize_impl: quant size = 2466.14 MiB (2.99 BPW)
- quantize: llama_quantize: quantize time = 235454.61 ms
- logprob test (test_llamacpp_lm_Q2_K.log, kept): PASS
- Q2_K/arc_challenge: acc_norm=0.3920 +/- 0.0219 n=500 in 96s (0.19s/item), 500 per-item rows
- Q2_K/hellaswag: acc_norm=0.6150 +/- 0.0244 n=400 in 144s (0.36s/item), 400 per-item rows
- Q2_K/mmlu: acc=0.4333 +/- 0.0200 n=570 in 106s (0.19s/item), 570 per-item rows
- Q2_K/gsm8k: exact_match=0.0500 +/- 0.0154 n=200 in 217s (1.09s/item), 400 per-item rows
- Q2_K/truthfulqa_mc2: acc=0.3887 +/- 0.0276 n=200 in 97s (0.48s/item), 200 per-item rows
- errors in run log: 0

Harmless noise in every Kaggle log: `Error in sitecustomize ... No module named 'wrapt'` (Kaggle's own startup hook) and `fatal: not a git repository` (lm_eval asking for a git hash).
