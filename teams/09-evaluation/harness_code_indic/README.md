# G9 eval-mini v0: code + Indic, and the agreement check

This folder (`teams/09-evaluation/harness_code_indic/`) holds G9's code and Indic half of eval-mini v0. The general half
(ARC, HellaSwag, MMLU, GSM8K, TruthfulQA) is in `../harness/` (PR #21, Mahesh Sv). It does two jobs:

1. **eval-mini v0 (code + Indic)**: a small, fixed battery for comparing checkpoints and model formats.
   - Definition: [`eval_mini_v0_spec.json`](eval_mini_v0_spec.json).
   - Scores for three open models: [`../results/eval_mini_v0_code_indic.json`](../results/eval_mini_v0_code_indic.json).
2. **Agreement with published scores** (week-1 gate): full test sets, with the protocol copied from each published source.
   - Report: [`../results/compare_v0_code_indic.md`](../results/compare_v0_code_indic.md).

## eval-mini v0 (this half) at a glance

| Part | Benchmarks | Items | Harness |
|---|---|---|---|
| General | MMLU-Pro, GSM8K | 300, 100 | lm-evaluation-harness 0.4.13, 5-shot |
| Indic | Belebele hi/te/ta, MILU hi/te/ta/bn | 100 each | lm-evaluation-harness 0.4.13, 5-shot |
| Code | HumanEval+, MBPP+ | all 164, all 378 | evalplus 0.3.1, greedy, base completion prompt |

- **Fixed items.** They are seeded random items, listed by index in the spec. Each task records its dataset revision and a sha256 of the chosen items.
- **Not comparable with published scores.** Subset scores are for comparing checkpoints and formats, not leaderboards.
- **Noise.** About 2 points on a 100-item task is implementation noise: a kernel change alone moved scores that much (`noise_note` in the spec).

## For Team 12 (or any pipeline that does not run lm-eval)

```
pip install -r requirements.txt
hf auth login                          # with access to ai4bharat/MILU, or add --skip-gated below
python make_eval_mini_items.py         # -> runs/eval_mini_v0_items.json, 1,100 items (700 with --skip-gated)
python <your>/quantize_eval.py --eval runs/eval_mini_v0_items.json
```

- **Format.** The items file is `{"items": [{"id", "question", "choices", "answer", "kind", "subset"}]}`:
  - `kind: "mcq"`: `choices` is a list and `answer` is a letter.
  - `kind: "numeric"`: GSM8K, where `answer` is the final number.
  - We checked it with Team 12's own `load_eval()` (PR #49): 1,000 multiple-choice and 100 numeric items, all parsed.
- **Safety check.** The builder rebuilds each task's item hash and refuses to write if a hub dataset has changed.
- **Pure ASCII.** The file is ASCII-only, so readers that open it without `encoding="utf-8"` still work on Windows.
- **Keep it local.** It contains benchmark questions and answers. It sits in `runs/`, which is gitignored; never commit or share it.
- **Code is not in the items file:** it needs execution (see below).

## Run eval-mini on your own model with lm-eval

1. **Install:** `pip install -r requirements.txt` (see the torch note in the file).
2. **Register your model** in `published_scores.json` → `models`, with `hf_id`, `revision` and `max_length`. Then fetch it:
   `python fetch_weights.py --model <key>` (parallel, resumable, sha256-checked).
3. **lm-eval part:** `python run_lm_eval.py --model <key> --samples-file eval_mini_v0_spec.json --tag eval_mini_v0`.
   - On a large GPU, the plain `lm-eval run …` command in the spec's `commands` also works. Pass `--include_path tasks`.
   - On GPUs with 8 GB or less, use `run_lm_eval.py`: stock lm-eval runs out of memory for 2–3B models.
4. **Code part (generation):** `python run_codegen.py --model <key>` patches the evalplus bugs listed below.
   With stock evalplus, run **one dataset per process**, preferably with `--backend vllm`.
5. **Code part (execution):** this needs Linux: `evalplus.evaluate --dataset humaneval --samples <file>.jsonl` (the same for mbpp).
   On Windows, use [`code_eval_colab.ipynb`](code_eval_colab.ipynb) on a CPU runtime.
6. **Results:** `python compare.py` rebuilds both results files from `runs/`.

`ai4bharat/MILU` is gated on Hugging Face: accept its terms and run `hf auth login` before running MILU tasks.

## `../results/eval_mini_v0_code_indic.json` fields

| Field | Meaning |
|---|---|
| `spec_file`, `spec_sha256` | the item definition these scores were computed on |
| `models.<key>.hf_id`, `.revision` | the exact model weights |
| `models.<key>.scores.<task>` | `metric`, `value` (0–100), `stderr`, `n` items, for the lm-eval tasks in the spec |
| `models.<key>.code.{humaneval,mbpp}` | `n` problems, `base` pass@1 (HumanEval / MBPP), `plus` pass@1 (HumanEval+ / MBPP+) |
| `models.<key>.env`, `.gpu`, `.wall_seconds` | library versions, GPU clock and power state, run time |
| `companion` | the general-task results file from PR #21 |

Values are points (0–100). PR #21's `eval_mini_v0.json` stores fractions (0–1), so multiply its values by 100 to compare.
Both harnesses agree: on PR #21's 200 GSM8K items for Qwen2.5-1.5B they score 61.0 and 61.5 (see `compare_v0_code_indic.md`).

## Files

| File | Role |
|---|---|
| `published_scores.json` | models (pinned revisions) and every published score we compare with, with source and protocol |
| `fetch_weights.py` | parallel, resumable, sha256-checked download of a pinned revision |
| `run_lm_eval.py` | one lm-eval run; records versions, GPU clock and power state |
| `run_codegen.py` | evalplus code generation with three fixes (below) |
| `code_eval_colab.ipynb` | executes code samples on Linux |
| `make_eval_mini_items.py` | writes the items file for pipelines without lm-eval |
| `run_queue.py` | runs all jobs one at a time; safe to stop and restart |
| `make_eval_mini_spec.py` | builds `eval_mini_v0_spec.json` |
| `compare.py` | builds the two `../results/*_code_indic.*` files |
| `tasks/milu/` | MILU task configs, vendored from AI4Bharat/MILU (MIT); see `NOTICE.md` |
| `.gitignore` | keeps `runs/` (outputs, caches, samples, items) out of git |

## Tool bugs found and fixed

Each fix is verified, and all are written up in `compare_v0_code_indic.md`.

- **evalplus 0.3.1, shared stop list.** MBPP inherited HumanEval's stop strings when both ran in one process, which truncated answers.
- **evalplus 0.3.1, HF backend.** One stop criterion stacked up per problem, and stale criteria could end generation after 1 token.
- **transformers 5, tokenizer rebuild.** It rebuilt deepseek-coder's tokenizer and dropped every space and newline. `run_codegen.py` now checks
  a round trip and falls back to the repo's own `tokenizer.json`.
- **lm-eval on 8 GB.** Logits for every position, and attention that falls back to the math kernel for grouped-query models, ran out of memory.
  `run_lm_eval.py` keeps only the scored logits (bit-identical) and uses the memory-efficient kernel (same accuracies).
- **Qwen's `max_new_tokens: 2048`** in `generation_config.json` overrode lm-eval's 256-token GSM8K cap. `run_lm_eval.py` clears it
  (found by Mahesh Sv, PR #21).

## Week-1 agreement status (this half)

| Status | Count | What |
|---|---|---|
| PASS | 19 | MMLU-Pro ×3 (Open LLM Leaderboard), MILU en/hi/te for both models, 10 of 12 code rows |
| FAIL | 2 | Qwen HumanEval+ −2.41, phi-2 MBPP+ −2.88; no timeouts recorded |
| DEFERRED | 2 | MILU-avg ×2, aggregation decided below |
| NOT RUN | 3 | BBH (optional) |

See `../results/compare_v0_code_indic.md` for every row, its source and the limitations.

## MILU-avg aggregation (decision)

MILU-avg is the **simple mean of the 11 per-language `gate_milu_<Language>` full runs** (Bengali, English, Gujarati, Hindi, Kannada,
Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu). `compare.py` computes it only when all 11 runs exist; otherwise the row is DEFERRED.
The `milu` group task is not used, because lm-eval's group score is size-weighted.

The MILU paper does not state how its avg column is aggregated. The simple mean of the paper's own 11 per-language scores gives
31.43 (gemma-2-2b) and 32.85 (llama-3.2-3b), the published avg; the size-weighted mean would give 33.51 and 34.87. The rule is fixed
before the remaining runs, so it cannot be tuned to a score. The pass rule is unchanged (|ours - published| <= 2.0), and a FAIL stands.
