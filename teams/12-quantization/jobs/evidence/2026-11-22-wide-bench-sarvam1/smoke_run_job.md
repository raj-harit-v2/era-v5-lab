# Smoke: prepare_inputs.py and run_job.py, offline (Kaggle, 21 Nov 2026)

Kaggle, 2 × Tesla T4, one interactive session, after `eval_wide.ipynb`'s setup cells (llama-cpp-python 0.3.36 CUDA
wheel, eval venv with lm_eval 0.4.13 and datasets 5.1.0 and no torch, llama.cpp b11669 `llama-quantize` and
converter venv). Code: `SomaKorada07/era-v5-lab` branch `g12-week4-wide-bench`, cloned in the session.

**Result: PASS.** Staging with network, then the job command with no token and the offline flags: every step exit 0,
and both GGUF files are byte-identical to the week 3 sarvam-1 files of #643.

## 1. prepare_inputs.py (with network and HF_TOKEN)

```text
python teams/12-quantization/eval_wide/prepare_inputs.py --hf-home <work>/inputs/hf_home \
    --model-dir <work>/inputs/sarvam-1 --model sarvamai/sarvam-1 --revision e9607337286ddf496d4a2562b194e489dcf3feea
```

- Model snapshot: 9 files.
- Online pass, items per task: MMLU 14,042 (57 subjects), ARC-C 1,172, MILU Kannada 6,234, Hindi 14,831,
  Telugu 7,304, Tamil 6,372, Bengali 6,637; total 56,592.
- **Offline check: PASS.** Same load with `HF_HUB_OFFLINE=1`, `HF_DATASETS_OFFLINE=1` and `HF_TOKEN` removed: every
  dataset, MILU included, came from the cache, the same 56,592 items. G9's MILU configs ask for a token
  (`token: true`); in offline mode that did not stop the load.

## 2. run_job.py (no HF_TOKEN; run_job.py sets the offline flags)

```text
python teams/12-quantization/eval_wide/run_job.py --model-dir <work>/inputs/sarvam-1 --hf-home <work>/inputs/hf_home \
    --llama-dir <work>/llama.cpp --convert-python <work>/convert-venv/bin/python --quantize <work>/llama.cpp/build/bin/llama-quantize \
    --formats bf16 Q4_K_M --work <work> --out <out>/smoke_out --cap 2 \
    --model sarvamai/sarvam-1 --revision e9607337286ddf496d4a2562b194e489dcf3feea
```

Exit 0, `done`. `job.json`, started 19:48:48, finished 19:51:39:

| Step | Exit | Seconds |
|---|---:|---:|
| test_llamacpp_lm_bf16 | 0 | 4.2 |
| run_bf16 | 0 | 0.1 (tasks already in summary.json, see below) |
| quantize_Q4_K_M | 0 | 115.8 |
| test_llamacpp_lm_Q4_K_M | 0 | 2.7 |
| run_Q4_K_M | 0 | 28.9 |
| paired | 0 | 0.1 |

| File | Bytes | sha256 | Same as #643 (`runs/rotation_subramanyanaik.md`) |
|---|---:|---|---|
| sarvam-1-bf16.gguf | 5,052,487,264 | `cfc747d2990ba2b2abd9687808bad2447efed28b3218ebfd0f1989deacc4408f` | yes |
| sarvam-1-Q4_K_M.gguf | 1,581,512,288 | `21f4188147d745473aeda10b4a5cd3c69f1eaf2dfb2bbfc37e389ea30846bebd` | yes |

`paired.md` has one row per task for Q4_K_M against bf16 (2 items per task, MMLU 114, so the numbers mean nothing; it
shows the step runs). Raw files: [smoke_out/job.json](smoke_out/job.json), [smoke_out/paired.md](smoke_out/paired.md),
[smoke_out/smoke_run_job.log](smoke_out/smoke_run_job.log) (the job's full output; no item text, no token).

## What this run did not cover, and why

- **The convert step.** The bf16 GGUF came from the notebook's own conversion cell (same converter, same revision),
  passed through `--work`, so `run_job.py` skipped `convert`. A first attempt with an empty work folder ran `convert`
  through `run_job.py` and was stopped by hand partway through writing (the notebook's output stopped refreshing). The
  sha256 above shows the bf16 file is the team's file.
- **bf16 scoring in this invocation.** The same command had already scored bf16 (2 items per task, all seven tasks,
  exit 0) in that first attempt, at 19:34, before it was stopped during the Q4_K_M quantize. `run_wide_gguf.py`
  resumes, so this run found bf16's tasks done and skipped them (0.1 s).
- After that first attempt, `run_job.py` was changed to write each GGUF under a `.part` name and rename it only when
  the step succeeds, so a stopped job can never leave a half-written file that a rerun would reuse. Child processes
  also run with `PYTHONUNBUFFERED=1`. Neither change touches scoring.
- A machine with no network: the session had network, and the offline flags (not a network block) kept every
  Hugging Face load on the cache.
