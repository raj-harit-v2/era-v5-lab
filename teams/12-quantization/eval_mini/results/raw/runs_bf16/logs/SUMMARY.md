# runs_bf16: log summary

- Run by: s9k96; platform kaggle; GPU Tesla T4, 15360 MiB, 580.178.04 + Tesla T4, 15360 MiB, 580.178.04; CUDA arch 75
- Notebook version: not recorded (run predates the fingerprint)
- Model allenai/OLMoE-1B-7B-0924 @ 6d84c48581ec; LIMIT None; formats bf16
- Versions: python 3.13.15, llama-cpp-python 0.3.36, lm_eval 0.4.13, datasets 5.1.0, llama.cpp b11669 (convert + quantize); torch/transformers visible to the eval: False/False
- Started 2026-10-28T12:16:11, finished 2026-10-28T13:35:51

## Build

- llama-cpp-python CUDA wheel: built
- llama-quantize: built; The CXX compiler identification is GNU 13.3.0
- bf16 GGUF: converted, OLMoE-1B-7B-0924-bf16.gguf: n_tensors = 195, total_size = 13.8G; 13,844,565,376 bytes

## Per format

### bf16
- GGUF 13,844,565,376 bytes; GPU layers -1 (-1 = all); eval wall clock 2695 s
- logprob test (test_llamacpp_lm_bf16.log): PASS, run afterwards on 29 Oct, not on Kaggle (this run predates the notebook's test step): Apple M5 16 GB, CPU only (n_gpu_layers=0), llama-cpp-python 0.3.36, on a local bf16 GGUF of the same revision (converted 25 Oct; 576 bytes larger than the Kaggle file, so not byte-identical), 44 s. With all layers on Metal the 13.8 GB file does not fit the 16 GB machine: the logits came back flat (every token -10.83 = -ln 50304) with no error, and the test failed, as it should
- bf16/arc_challenge: acc_norm=0.4680 +/- 0.0223 n=500 in 518s (1.04s/item), 500 per-item rows
- bf16/hellaswag: acc_norm=0.6600 +/- 0.0237 n=400 in 634s (1.58s/item), 400 per-item rows
- bf16/mmlu: acc=0.5368 +/- 0.0202 n=570 in 485s (0.85s/item), 570 per-item rows
- bf16/gsm8k: exact_match=0.1050 +/- 0.0217 n=200 in 582s (2.91s/item), 400 per-item rows
- bf16/truthfulqa_mc2: acc=0.3733 +/- 0.0277 n=200 in 421s (2.11s/item), 200 per-item rows
- errors in run log: 0

Harmless noise in every Kaggle log: `Error in sitecustomize ... No module named 'wrapt'` (Kaggle's own startup hook) and `fatal: not a git repository` (lm_eval asking for a git hash).
