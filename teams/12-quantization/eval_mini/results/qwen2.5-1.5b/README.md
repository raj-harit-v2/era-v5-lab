# Qwen2.5-1.5B (base), bf16 vs Q6_K, Q5_K_M and Q4_K_M (eval_mini)

Run by shankarpandala on an Apple M5 Pro (24 GB, Metal, every layer on the GPU), 16 Nov 2026, as the follow-up to
`runs/rotation_shankarpandala.md`: there, Q4_K_M lost 11 points on the stand-in set's 100 GSM8K items, with no
paired test. This run measures it on the full eval_mini profile, item by item.

- Model `Qwen/Qwen2.5-1.5B` (the base model), revision `8faed761d45a263340a0528343f099c05c9a4323`.
- GGUF files: converted and quantized by `scripts/quantize_eval.py` with llama.cpp b9310 (Homebrew); the output
  layer is Q8_0 in every quantized file. Their sha256 are in `runs/rotation_shankarpandala.md`.
- Scoring: the class `main` scripts run directly, not the notebook: `run_mini_gguf.py`, `llamacpp_lm.py`,
  `paired.py` and G9's `run_eval_mini.py` (profile `mini`, seed 42, `n_ctx` 2048), with llama-cpp-python 0.3.36,
  lm_eval 0.4.13, datasets 5.1.0 and Python 3.12, as pinned in `eval_mini.ipynb`.
- Every file passed `test_llamacpp_lm.py` before it was scored (`logs/`).
- All formats ran on the same machine and backend, so the paired comparison against bf16 is made directly.

## Results

| Task | bf16 | Q6_K | Q5_K_M | Q4_K_M |
|---|---:|---:|---:|---:|
| ARC-Challenge (500) | 43.4 | 44.4 | 44.4 | 42.6 |
| HellaSwag (400) | 59.5 | 58.2 | 58.2 | 58.8 |
| MMLU (570) | 63.3 | 64.0 | 63.5 | 62.6 |
| GSM8K, 5-shot (200) | 60.5 | 63.0 | 61.0 | 55.5 |
| TruthfulQA-mc2 (200) | 46.6 | 47.0 | 46.7 | 46.1 |

Paired against bf16 (`paired.md`):

| Format | Task | Difference (95% CI) | b / c | McNemar p |
|---|---|---|---|---|
| Q4_K_M | ARC-Challenge | -0.8 (-3.3 to +1.7) | 22 / 18 | 0.636 |
| Q4_K_M | HellaSwag | -0.8 (-2.9 to +1.4) | 11 / 8 | 0.648 |
| Q4_K_M | MMLU | -0.7 (-2.8 to +1.4) | 21 / 17 | 0.627 |
| Q4_K_M | **GSM8K** | **-5.0 (-11.5 to +1.5)** | 27 / 17 | 0.174 |
| Q4_K_M | TruthfulQA-mc2 | -0.6 (-2.1 to +1.0) | - | - |
| Q5_K_M | GSM8K | +0.5 (-4.6 to +5.6) | 13 / 14 | 1.000 |
| Q5_K_M | HellaSwag | -1.2 (-2.5 to +0.0) | 6 / 1 | 0.125 |
| Q6_K | GSM8K | +2.5 (-2.0 to +7.0) | 8 / 13 | 0.383 |
| Q6_K | HellaSwag | -1.2 (-2.3 to -0.2) | 5 / 0 | 0.062 |

The other Q5_K_M and Q6_K rows are within ±1.0 point and are in `paired.md`.

## Against `docs/bitwidth_proposal.md`

- **Q4_K_M misses the GSM8K limit** (-4): its point estimate is -5.0. McNemar p is 0.174, so it is not a significant
  loss, but the proposal's rule fails a task on the point estimate. Every other task is inside its limit.
- **Q5_K_M and Q6_K are inside every limit.** For this model, Q5_K_M is the smallest format inside all of them. The
  proposal notes that the models whose Q4_K_M misses a limit have no Q5_K_M or Q6_K scores; this model now has both.
- The stand-in set's -11 on 100 GSM8K items (`runs/rotation_shankarpandala.md`) has the same direction, but about
  twice the size of the paired -5.0 here.

## Against #236 (Qwen2.5-1.5B-Instruct)

#236 ran the Instruct model on Kaggle (2x T4, llama.cpp b11669). Its Q4_K_M has GSM8K +2.5 (not significant) and
HellaSwag -2.8 (p 0.027). Here, for the base model, GSM8K is -5.0 and HellaSwag -0.8. The two runs differ in the
model (base or Instruct), the backend (Metal or CUDA) and the llama.cpp build, so the difference between them is not
attributed to any one of these.

## Time and cost

| Format | File size | Wall clock (5 tasks, 1,870 items) | Model load |
|---|---:|---:|---:|
| bf16 | 3.09 GB | 1066 s | 0.4 s |
| Q6_K | 1.33 GB | 689 s | 0.2 s |
| Q5_K_M | 1.18 GB | 745 s | 0.2 s |
| Q4_K_M | 1.04 GB | 635 s | 0.3 s |

Wall clock is from `/usr/bin/time` around `run_mini_gguf.py`; the four formats took 52 minutes in all. No paid cost: my
own laptop.
