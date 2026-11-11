# runs_Q5_K_M-Q4_K_M: log summary

- Run by: therahulbhati; platform kaggle; GPU Tesla T4, 15360 MiB, 580.178.04 + Tesla T4, 15360 MiB, 580.178.04; CUDA arch 75
- Notebook version: 70829160c1bd
- Model allenai/OLMoE-1B-7B-0924 @ 6d84c48581ec; LIMIT None; formats Q5_K_M, Q4_K_M
- Versions: python 3.13.15, llama-cpp-python 0.3.36, lm_eval 0.4.13, datasets 5.1.0, llama.cpp b11669 (convert + quantize); torch/transformers visible to the eval: False/False
- Started 2026-10-29T10:50:45, finished 2026-10-29T11:59:56

## Build

- llama-cpp-python CUDA wheel: built
- llama-quantize: built; The CXX compiler identification is GNU 13.3.0
- bf16 GGUF: converted, OLMoE-1B-7B-0924-bf16.gguf: n_tensors = 195, total_size = 13.8G; 13,844,565,376 bytes

## Per format

### Q5_K_M
- GGUF 4,951,788,928 bytes; GPU layers -1 (-1 = all); eval wall clock 1042 s
- quantize: [ 1/ 195] output.weight - [ 2048, 50304, 1, 1], type = bf16, converting to q8_0 .. size = 196.50 MiB -> 104.39 MiB
- quantize: llama_model_quantize_impl: quant size = 4720.70 MiB (5.72 BPW)
- quantize: llama_quantize: quantize time = 303585.26 ms
- logprob test (test_llamacpp_lm_Q5_K_M.log, kept): PASS
- Q5_K_M/arc_challenge: acc_norm=0.4640 +/- 0.0223 n=500 in 99s (0.20s/item), 500 per-item rows
- Q5_K_M/hellaswag: acc_norm=0.6625 +/- 0.0237 n=400 in 143s (0.36s/item), 400 per-item rows
- Q5_K_M/mmlu: acc=0.5456 +/- 0.0202 n=570 in 150s (0.26s/item), 570 per-item rows
- Q5_K_M/gsm8k: exact_match=0.1300 +/- 0.0238 n=200 in 233s (1.17s/item), 400 per-item rows
- Q5_K_M/truthfulqa_mc2: acc=0.3769 +/- 0.0276 n=200 in 92s (0.46s/item), 200 per-item rows
- errors in run log: 0

### Q4_K_M
- GGUF 4,238,462,336 bytes; GPU layers -1 (-1 = all); eval wall clock 986 s
- quantize: [ 1/ 195] output.weight - [ 2048, 50304, 1, 1], type = bf16, converting to q8_0 .. size = 196.50 MiB -> 104.39 MiB
- quantize: llama_model_quantize_impl: quant size = 4040.41 MiB (4.90 BPW)
- quantize: llama_quantize: quantize time = 351273.38 ms
- logprob test (test_llamacpp_lm_Q4_K_M.log, kept): PASS
- Q4_K_M/arc_challenge: acc_norm=0.4700 +/- 0.0223 n=500 in 94s (0.19s/item), 500 per-item rows
- Q4_K_M/hellaswag: acc_norm=0.6575 +/- 0.0238 n=400 in 133s (0.33s/item), 400 per-item rows
- Q4_K_M/mmlu: acc=0.5175 +/- 0.0204 n=570 in 92s (0.16s/item), 570 per-item rows
- Q4_K_M/gsm8k: exact_match=0.1150 +/- 0.0226 n=200 in 217s (1.09s/item), 400 per-item rows
- Q4_K_M/truthfulqa_mc2: acc=0.3688 +/- 0.0276 n=200 in 87s (0.43s/item), 200 per-item rows
- errors in run log: 0

Harmless noise in every Kaggle log: `Error in sitecustomize ... No module named 'wrapt'` (Kaggle's own startup hook) and `fatal: not a git repository` (lm_eval asking for a git hash).
