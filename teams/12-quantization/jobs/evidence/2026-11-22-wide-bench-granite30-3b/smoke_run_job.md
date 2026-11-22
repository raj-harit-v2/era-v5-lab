# Smoke: prepare_inputs.py --tasks and run_job.py --tasks, offline (Kaggle, 21 Nov 2026)

Kaggle, 2 × Tesla T4, the same interactive session as the timing run, after `eval_wide.ipynb`'s setup cells. Code:
`SomaKorada07/era-v5-lab` branch `g12-week4-wide-bench`, freshly cloned in the session (with `--tasks`).

**Result: PASS.** Staging with network and no token, then the job command with an empty work folder, so every step ran
inside `run_job.py`, the convert step included (the sarvam-1 smoke skipped it). Every step exit 0.

## 1. prepare_inputs.py --tasks mmlu arc_challenge (with network, no HF_TOKEN)

```text
python teams/12-quantization/eval_wide/prepare_inputs.py --tasks mmlu arc_challenge --hf-home <work>/inputs/hf_home_g \
    --model-dir <work>/inputs/granite-3.0-3b-a800m-base \
    --model ibm-granite/granite-3.0-3b-a800m-base --revision 142d2c8e3f7fb8844011cfa5565f0e520f0824b9
```

Exit 0: model snapshot, then MMLU and ARC-C loaded online and again offline with no token. The job below then read
both from this cache with the offline flags set.

## 2. run_job.py (no HF_TOKEN; run_job.py sets the offline flags; empty work folder)

```text
python teams/12-quantization/eval_wide/run_job.py --model-dir <work>/inputs/granite-3.0-3b-a800m-base --hf-home <work>/inputs/hf_home_g \
    --llama-dir <work>/llama.cpp --convert-python <work>/convert-venv/bin/python --quantize <work>/llama.cpp/build/bin/llama-quantize \
    --formats bf16 Q4_K_M --tasks mmlu arc_challenge --cap 2 --work <work>/job_g --out <out>/smoke_g_out \
    --model ibm-granite/granite-3.0-3b-a800m-base --revision 142d2c8e3f7fb8844011cfa5565f0e520f0824b9
```

[`job.json`](smoke_out/job.json), started 20:43:07, finished 20:50:02 (7 min), `tasks: [mmlu, arc_challenge]`:

| Step | Exit | Seconds |
|---|---:|---:|
| convert | 0 | 110.7 |
| test_llamacpp_lm_bf16 | 0 | 36.0 |
| run_bf16 | 0 | 58.4 |
| quantize_Q4_K_M | 0 | 156.9 |
| test_llamacpp_lm_Q4_K_M | 0 | 2.9 |
| run_Q4_K_M | 0 | 25.7 |
| paired | 0 | 0.1 |

| File | Bytes | sha256 |
|---|---:|---|
| granite-3.0-3b-a800m-base-bf16.gguf | 6,754,445,248 | `6ec765fcd81fbecf86724fe3a32baf808c1115dad4247ca68be5816e5f1faad6` |
| granite-3.0-3b-a800m-base-Q4_K_M.gguf | 2,077,632,448 | `5b8c6492e0d465fd4e191383e50b6f94bfa3773eab7941644d0ebcf59fe29540` |

The bf16 file is 128 bytes larger than the timing run's (6,754,445,120). The two conversions used the same converter
and revision but different snapshot folder names (`hf` in the notebook, `granite-3.0-3b-a800m-base` here), and
llama.cpp's converter writes a model name derived from the folder into the GGUF metadata. The tensors are the same;
the job's sha256 will match this smoke's, not the timing run's.

[`paired.md`](smoke_out/paired.md): one row per task, Q4_K_M against bf16 (2 items per task, MMLU 114). MMLU +7.9
(p 0.078) on 114 items is noise at this size; the row shows the step runs.

## What this run did not cover

- Q8_0 and Q3_K_M (the same quantize and guard steps as Q4_K_M, other type names).
- A machine with no network: the session had network; the offline flags kept every Hugging Face load on the cache.
