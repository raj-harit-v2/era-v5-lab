# runs_Q8_0-Q6_K: log summary

- Run by: SreekanthZipsy; platform kaggle; GPU Tesla T4, 15360 MiB, 580.178.04 + Tesla T4, 15360 MiB, 580.178.04; CUDA arch 75
- Notebook version: 70829160c1bd
- Model allenai/OLMoE-1B-7B-0924 @ 6d84c48581ec; LIMIT None; formats Q8_0, Q6_K
- Versions: python 3.13.15, llama-cpp-python 0.3.36, lm_eval 0.4.13, datasets 5.1.0, llama.cpp b11669 (convert + quantize); torch/transformers visible to the eval: False/False
- Started 2026-10-29T10:24:44, finished 2026-10-29T11:29:09

## Build

- llama-cpp-python CUDA wheel: built
- llama-quantize: built; The CXX compiler identification is GNU 13.3.0
- bf16 GGUF: converted, OLMoE-1B-7B-0924-bf16.gguf: n_tensors = 195, total_size = 13.8G; 13,844,565,376 bytes

## Per format

### Q8_0
- GGUF 7,359,942,016 bytes; GPU layers -1 (-1 = all); eval wall clock 888 s
- quantize: [ 1/ 195] output.weight - [ 2048, 50304, 1, 1], type = bf16, converting to q8_0 .. size = 196.50 MiB -> 104.39 MiB
- quantize: llama_model_quantize_impl: quant size = 7017.29 MiB (8.51 BPW)
- quantize: llama_quantize: quantize time = 93255.15 ms
- logprob test (test_llamacpp_lm_Q8_0.log, kept): PASS
- Q8_0/arc_challenge: acc_norm=0.4640 +/- 0.0223 n=500 in 110s (0.22s/item), 500 per-item rows
- Q8_0/hellaswag: acc_norm=0.6575 +/- 0.0238 n=400 in 147s (0.37s/item), 400 per-item rows
- Q8_0/mmlu: acc=0.5333 +/- 0.0203 n=570 in 164s (0.29s/item), 570 per-item rows
- Q8_0/gsm8k: exact_match=0.1250 +/- 0.0234 n=200 in 247s (1.23s/item), 400 per-item rows
- Q8_0/truthfulqa_mc2: acc=0.3701 +/- 0.0276 n=200 in 100s (0.50s/item), 200 per-item rows
- errors in run log: 0

### Q6_K
- GGUF 5,709,698,432 bytes; GPU layers -1 (-1 = all); eval wall clock 892 s
- quantize: [ 1/ 195] output.weight - [ 2048, 50304, 1, 1], type = bf16, converting to q8_0 .. size = 196.50 MiB -> 104.39 MiB
- quantize: llama_model_quantize_impl: quant size = 5443.49 MiB (6.60 BPW)
- quantize: llama_quantize: quantize time = 190560.60 ms
- logprob test (test_llamacpp_lm_Q6_K.log, kept): PASS
- Q6_K/arc_challenge: acc_norm=0.4760 +/- 0.0224 n=500 in 97s (0.19s/item), 500 per-item rows
- Q6_K/hellaswag: acc_norm=0.6675 +/- 0.0236 n=400 in 142s (0.35s/item), 400 per-item rows
- Q6_K/mmlu: acc=0.5368 +/- 0.0201 n=570 in 107s (0.19s/item), 570 per-item rows
- Q6_K/gsm8k: exact_match=0.1050 +/- 0.0217 n=200 in 246s (1.23s/item), 400 per-item rows
- Q6_K/truthfulqa_mc2: acc=0.3740 +/- 0.0276 n=200 in 95s (0.47s/item), 200 per-item rows
- errors in run log: 0

Harmless noise in every Kaggle log: `Error in sitecustomize ... No module named 'wrapt'` (Kaggle's own startup hook) and `fatal: not a git repository` (lm_eval asking for a git hash).
