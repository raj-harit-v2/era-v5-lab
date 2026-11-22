# Dry run 1 flow: local smoke of `run_flow.py` on a dry-run-1-shaped random model

This is a test log. It is not a score result and it is not a speed measurement for the trained model. The weights are random.

## What was run

- Code: `theschoolofai/era-v5-lab` main at 3e776045 plus the four commits of the PR that carries this file (agreement per source in `flow_fixed_prompts.py`; `llama_tag()` offline in `quantize_eval.py` and `prompts/eval_own_20.json`; `run_flow.py`; this job request and evidence). Run from the repository root.
- Machine: Apple M5, 16 GB, macOS 26.6.2, Metal. llama.cpp b11669 (`620d2225c`) from Homebrew (`llama-quantize`, `llama-server`), and a b11669 checkout in the work folder. Python 3.12 with torch 2.11.0, transformers 4.57.6, tokenizers 0.22.2, llama-cpp-python 0.3.36, datasets 4.8.5, regex; the converter venv in the work folder (made earlier by `quantize_eval.py`) has the same torch and transformers.
- Model: random weights in the shape of dry run 1. The model settings are `config.model` of the `manifest.json` in `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/` (8 layers, width 512, 8 heads, 2 key-value heads, 16 + 1 experts, top-2, expert width 768, KE1 embedding with 32 positions, 131,072 ids): 237,052,416 parameters in the trainer's own `LanguageModel`, 299,966,976 after the Granite MoE export. The run folder has a `checkpoint.pt` with the entries `train_week2.py` writes (`model`, `optimizer`, `stream`, RNG states, `step`, `trace`, `rows` and the rest; the optimizer entry is a stub, so the file is 0.95 GB, not 2.2 GB) and that `manifest.json`. Every matrix is drawn from N(0, 0.05), norms from U(0.5, 1.5).
- Tokenizer: p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, a local copy at `./inputs/tokenizer.json` (not in the repository).
- Work folder `./work/`: a checkout of llama.cpp b11669 and the converter venv, both from an earlier run. Nothing else was there before the first command.
- Network: `git ls-remote`, `clone`, `fetch` and `pull` were replaced by a stub that exits 99 (a `git` first on the PATH). Nothing called it. The machine itself had network; no package install and no download was attempted by the scripts.
- Items for the score: `prompts/eval_own_20.json`. Prompts: our `prompts/fixed_100.jsonl` (sha256 `da3f6851467d5ac57ff9577fa3d341ee98c0bf82293d32da9b5f3fecc90f4919`); decoding defaults (128 new tokens).

## Commands

```bash
python teams/12-quantization/scripts/run_flow.py --checkpoint ./inputs/standin-t2 --tokenizer ./inputs/tokenizer.json --eval teams/12-quantization/prompts/eval_own_20.json --work ./work --out ./out
```

Exit 0. Wall time 1 min 54 s. This run reused the bf16 GGUF of a first run (the same quantize_eval.py command alone: 75 s from the exported folder, including the conversion, A1, A3, two quantizations and three scorings), so the cold time of the first command is about 75 s plus the second command's 73 s.

Also run, on the same GGUFs and before the command above, with `resolve_prompts` replaced by a stub that returns synthetic text for the 55 resolved slots (no parquet files here): `flow_fixed_prompts.py --gguf-dir ./work --scores ./out/scores.json --manifest teams/10-post-training/eval/effort_manifest.json --formats Q8_0,Q4_K_M`. Exit 0.

## Results

| Step | Result |
|---|---|
| A1 export | max logit difference 8.1e-06 (limit 0.001), same top-1 on 4,096 of 4,096 positions: PASS |
| A3 llama.cpp vs G5 | same top-1 on 16 of 16 prompts, max log-probability difference 0.0372 (limit 0.05): PASS. The margin is small on random weights with this scale; a trained model has a different spread. |
| GGUF tokenizer | pre-tokenizer `granite-embed-multi-97m`, 131,072 ids, eos 130822 |
| Files | bf16 606,017,344 bytes (16.0 bpw); Q8_0 324,867,904 bytes (8.58 bpw); Q4_K_M 215,437,120 bytes (5.69 bpw). Router F32 and output layer Q8_0 for the two formats. |
| Score on the 20 items | bf16 0.0; Q8_0 0.05; Q4_K_M 0.0. Random weights: these are noise. |
| Outputs | `./out` is 0.7 MB: `runs.csv`, `scores.json`, `manifest_<date>.json`, `prompts/` |

100 prompts, greedy, seed 0, 128 tokens (`prompts/summary.json`):

| Format | Finish (stop / length) | Mean tok/s | Outputs identical to bf16 | Mean shared prefix with bf16 |
|---|---|---|---|---|
| bf16 | 0 / 100 | 442.5 | n/a | n/a |
| Q8_0 | 0 / 100 | 577.3 | 0 of 100 | 0.102 |
| Q4_K_M | 0 / 100 | 624.2 | 0 of 100 | 0.012 |

The agreement is a property of random weights (the logits are nearly flat), not of the quantization.

The `--manifest` run with synthetic text for the Team 10 slots (output not kept): 100 rows, 55 from Team 10 and 45 from our prompts (20 tool, 15 Indic, 10 general), manifest sha256 `d6190b2d7b013222e767cdb7c50f66231769385ce1dfb729eaa9530b9ebf9226`. In the written files the 55 Team 10 rows carry no text, no `output_ids` and no prompt, only `output_ids_sha256`; the 45 of ours carry both. The summary split the agreement: Q8_0 `g10_55` 1 identical of 55 (shared prefix 0.115), `g12_fill_45` 1 of 45 (0.195); Q4_K_M `g10_55` 0 of 55 (0.017), `g12_fill_45` 0 of 45 (0.024). On synthetic prompts and random weights these say nothing about Team 10's items.

Unit tests, same Python (`tests.log`; the tokenizer tests were not rerun, their files are unchanged):

| Test | Result |
|---|---|
| `scripts/test_quantize_eval.py` | 5 tests, OK (one is new: `llama_tag` from a prepared work folder, no `ls-remote`) |
| `scripts/test_export_hf.py` | 13 tests, OK |
| `scripts/test_flow_fixed_prompts.py` | 8 tests, OK (three are new: agreement per source) |
| `scripts/test_run_flow.py` | 3 tests, OK (stub runner: the two commands, and stop at the first non-zero exit) |

## The export on a trainer-shaped checkpoint (risk check)

`export_hf.py` takes `obj["model"]` from a `.pt` dict, so the extra entries of the trainer's checkpoint are not read, and the settings come from `manifest.json` (`config.model`). On the file described above it exported 299,966,976 parameters with A1 PASS (above). What this does not show: a `checkpoint.pt` written by the real trainer on a GPU (bf16 autocast changes the training, not the saved fp32 state dict, but I have not seen the file), or trained weights.

## What was not tested

1. The real dry run 1 `checkpoint.pt` and its trained weights.
2. A GPU. Everything ran on Metal on one laptop.
3. The 55 Team 10 slots with real text: the parquet files are not on this machine.
4. A machine without network. Only the git network calls were blocked.
5. `--roundtrip` (not in the job command; it needs held-out text from the Hub).
6. The tokenizer round trip on this model's GGUF. For p1536 it is in the #467 report (exit 1, the known granite limits).
