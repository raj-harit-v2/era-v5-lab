# Team 12-quantization

Put your work in a **topic folder**: `teams/12-quantization/<topic>/<file>`, for example `teams/12-quantization/harness/run.py`.
Team documents named in the week plan (for example `benchmarks_v1.md`) may sit directly in the team folder. The team lead decides the topic names. Do not make personal folders. Do not make new folders under `teams/`.
Open a pull request; the lead reviews and merges it. The pr-guard check must pass.

## Week 1: OLMoE-1B-7B in six llama.cpp formats

`allenai/OLMoE-1B-7B-0924` @ `6d84c48581ec`, converted to a bf16 GGUF and quantized from Q8_0 down to Q2_K. Every
quantized format keeps `output.weight` at Q8_0, and the router (`ffn_gate_inp`) stays F32. Each format was measured in
three ways:

| Format | Size | ARC-C | HellaSwag | MMLU | GSM8K | TruthfulQA-mc2 | WikiText-2 PPL | KL vs bf16 | Same top-1 |
|---|---|---|---|---|---|---|---|---|---|
| bf16 | 13.84 GB | 46.8 | 66.0 | 53.7 | 10.5 | 37.3 | 7.993 | | |
| Q8_0 | 7.36 GB | 46.4 | 65.8 | 53.3 | 12.5 | 37.0 | 7.994 | 0.0013 | 98.3% |
| Q6_K | 5.71 GB | 47.6 | 66.8 | 53.7 | 10.5 | 37.4 | 8.012 | 0.0038 | 96.8% |
| Q5_K_M | 4.95 GB | 46.4 | 66.2 | 54.6 | 13.0 | 37.7 | 8.039 | 0.0081 | 95.3% |
| Q4_K_M | 4.24 GB | 47.0 | 65.8 | 51.8 | 11.5 | 36.9 | 8.179 | 0.0233 | 92.1% |
| Q3_K_M | 3.37 GB | 46.6 | 64.8 | **49.5** | 9.0 | 36.7 | 8.516 | 0.0576 | 87.9% |
| Q2_K | 2.59 GB | **39.2** | **61.5** | **43.3** | **5.0** | 38.9 | 10.500 | 0.2336 | 76.2% |

Benchmark scores are % correct on G9's eval_mini profile (1,870 questions, about ±2–3 points of standard error each).
**Bold** marks a significant drop compared with bf16 on the same questions: McNemar p < 0.01, except Q2_K GSM8K
(p 0.052). Perplexity is on the full WikiText-2 test set. KL is the mean KL divergence from bf16's next-token
distribution on 16,384 WikiText-2 tokens.

**What it says.** The benchmarks show no measurable loss from Q8_0 to Q4_K_M. The first real drop is Q3_K_M on MMLU
(−4.2 points), and Q2_K breaks broadly. Perplexity and KL rise steadily at every step, so they separate formats that
the benchmarks cannot. Q4_K_M is the smallest format with no significant benchmark loss (3.3× smaller than bf16).

| Folder | What | Detail |
|---|---|---|
| [`eval_mini/`](eval_mini/) | G9's eval_mini on every format, scored in-process with llama-cpp-python; paired comparison with bf16 | [`results/RESULTS.md`](eval_mini/results/RESULTS.md) |
| [`perplexity/`](perplexity/) | WikiText-2 perplexity, llama.cpp v0.7.0 on Kaggle | [`README.md`](perplexity/README.md) |
| [`quality/`](quality/) | KL divergence and same-top-1 against bf16 (`llama-perplexity --kl-divergence`) | [`README.md`](quality/README.md) |
| [`runs/runs.csv`](runs/runs.csv) | one row per format: size, bits per weight, quantize time, generation speed, eval_mini score | notes column |
| `runs/manifest_<date>.json` | SHA-256 of each GGUF `quantize_eval.py` writes that day (bf16 and every quant) | beside `runs.csv`; a same-day rerun replaces that file's entry |
| [`docs/bitwidth_vs_drop.md`](docs/bitwidth_vs_drop.md) | bits per weight against task drop, perplexity ratio and KL; which format to demo | Q4_K_M |
| [`docs/bitwidth_proposal.md`](docs/bitwidth_proposal.md) | formats to keep, and the drop limit per task | keep through Q4_K_M when the limits hold; not Q3_K_M or Q2_K |
| [`docs/serving_plan.md`](docs/serving_plan.md) | vLLM serving plan (Session 18): KV-cache budget, prefix caching, FP8 weights and KV cache against BF16, expert parallel | prefix caching on; FP8 KV and FP8 weights measured before shipping; no expert parallel at test sizes |
| [`scripts/quantize_eval.py`](scripts/quantize_eval.py) | makes the GGUFs (output tensor Q8_0) and measures size, quantize time and speed; its own eval is the 25 Oct stand-in, whose scores in runs.csv were replaced by eval_mini. Week 3: `--checkpoint` takes our own checkpoint (below) | script docstring |
| [`quantize/quantize_olmoe.sh`](quantize/quantize_olmoe.sh) | an alternative recipe (output BF16, down to Q3_K_M); **not** the one measured here | script header |
| [`tools/tools.md`](tools/tools.md) | survey of quantization and serving tools: licences, MoE support | |
| [`tokenizer/gguf_roundtrip.py`](tokenizer/gguf_roundtrip.py) | week 2: does llama.cpp give the same token ids as the HF tokenizer after GGUF conversion? Tokenizer v0: yes with pre-tokenizer `granite-embed-multi-97m` (0 of 22,033 lines differ); `gpt-4o` differs on 14,517 | [`results/gguf_roundtrip_v0.md`](results/gguf_roundtrip_v0.md) |

**Rerun.**
- **Benchmarks:** import `eval_mini/eval_mini.ipynb` into Kaggle (GPU T4 x2, Internet on), set `FORMATS`, then
  Save & Run All. It builds llama.cpp b11669 and llama-cpp-python 0.3.36, converts, quantizes, runs the logprob test,
  then scores.
- **Combine:** `python eval_mini/combine.py eval_mini/results/raw/* --out <dir>` rebuilds the tables from the
  committed per-question rows.
- **Perplexity and KL:** the commands are in each folder's README.

Versions:
- llama.cpp b11669 (= v0.7.0) for conversion and quantizing;
- llama-cpp-python 0.3.36, lm_eval 0.4.13, datasets 5.1.0 and Python 3.13 for eval_mini;
- G9's `run_eval_mini.py` from lab `main`, fixed by its sha256 in every summary.

## Week 3: checkpoint in, quantized model and scores out

One command takes a G5 checkpoint to quantized GGUF files and scores, with no manual step:

```
python teams/12-quantization/scripts/quantize_eval.py --checkpoint <run dir | checkpoint.pt | model.safetensors> \
    --tokenizer teams/03-tokenizer/release/tokenizer.json --eval <items.json> --formats bf16,Q8_0,Q4_K_M --roundtrip
```

| Step | Script | What it does | It stops when |
|---|---|---|---|
| 1 export | [`scripts/export_hf.py`](scripts/export_hf.py) | G5 `LanguageModel` checkpoint → Hugging Face Granite MoE Shared folder ([`docs/unsupported_parts.md`](docs/unsupported_parts.md) §8, §9): KE2 folded into a table, q/k rows reordered for RoPE, shared experts merged, `mtp_head` dropped | test A1 fails (the export and G5's model must give the same fp32 logits and top-1 on 64 prompts); the checkpoint has a part the export cannot represent (attn-2, attn-3, attn-4, biases) |
| 2 convert | llama.cpp b11669 `convert_hf_to_gguf.py` | bf16 GGUF that carries `--tokenizer`, pre-tokenizer `granite-embed-multi-97m` | `tokenizer.json` does not have `--tokenizer-sha256` (default: the frozen tokenizer, p1536); it has more ids than the model |
| 2a A3 | [`scripts/check_gguf_logits.py`](scripts/check_gguf_logits.py) | llama.cpp on the bf16 GGUF against G5's model: top-1 and log-probabilities of the next token on 16 prompts | never: the result is reported. The limit is not calibrated on a trained checkpoint yet (script docstring) |
| 2b round trip (`--roundtrip`) | [`tokenizer/gguf_roundtrip.py`](tokenizer/gguf_roundtrip.py) `--gguf` | llama.cpp gives the token ids of `tokenizer.json` on held-out text | never: the exit code (0, 2 or 1) is reported |
| 3 quantize, 4 score | `quantize_eval.py` | as in week 1: router F32 and output Q8_0 are checked in every file | a router or output tensor is below 8 bits |

It writes the GGUF files to `--work`, one `runs.csv` row per format, and `<work>/<name>-scores.json`: the checkpoint
and tokenizer SHA-256, the A1 and A3 results, the round-trip exit code, and for each format the file, its SHA-256,
its size and its scores. File names carry the first 8 hex digits of the checkpoint's SHA-256, so a new checkpoint
never reuses the files of an old one.

- **Inputs.** A `train_week2.py` run folder has all the model settings in `manifest.json`. For a bare `state_dict`
  (Team 07's `export_safetensors`) pass `--spec` with `n_head`, `rope_theta`, `norm_eps` and `moe.top_k`; every other
  size is read from the tensor shapes. A folder that already has `config.json` skips step 1.
- **Scores.** The eval is the script's own (`--eval <items file>`, or the 25 Oct stand-in). G9's eval_mini on the
  GGUF files is still `eval_mini/`.
- **Tested** on random checkpoints from [`scripts/make_random_checkpoint.py`](scripts/make_random_checkpoint.py)
  (2 layers, width 64, 16 + 1 experts, 131,072 ids, BrahmicTokenizer-131K baseline), on Windows with the llama.cpp
  b11669 CPU binaries: A1 max logit difference 1.2e-5 with the same top-1 on 4,096 of 4,096 positions; A3 the same
  top-1 on 16 of 16 prompts, max log-probability difference 0.032; round trip 0 of 20,400 lines with different ids
  and 16 of 129,410 single tokens wrong in the whole-vocabulary check (exit 1; C3 sample-v0 has the same kind
  of failure on 9 ids, [`results/gguf_roundtrip_frozen.md`](results/gguf_roundtrip_frozen.md)). The scores of a random model mean nothing and are
  not in `runs.csv`.
- **On the frozen tokenizer (p1536, 16 Nov),** same random model and machine, default `--tokenizer-sha256`: A1 max
  logit difference 1.9e-6 with the same top-1 on 4,096 of 4,096 positions; A3 the same top-1 on 16 of 16 prompts,
  max log-probability difference 0.0065; bf16 and Q4_K_M built and scored. **The round trip does not pass (exit 1),**
  [`results/gguf_roundtrip_p1536.md`](results/gguf_roundtrip_p1536.md): 3,075 of 20,400 lines get different ids.
  3,074 of them are lines that p1536's normalizer changes (Bengali, Assamese, Punjabi, one Odia line, and the
  ZWJ/ZWNJ, NFD and old-chillu sets); the GGUF cannot carry a normalizer, and with the normalizer applied to the text
  first all of them match. What is left is 1 Russian line and 6 of 129,581 single tokens, from llama.cpp's
  ASCII-only test for capital letters. So the serving app must normalize before llama.cpp, and whether that counts
  as a pass for Gate 3 is not decided.
- **Not yet run on a trained checkpoint.**
- **Tests:** `python scripts/test_export_hf.py` (13 tests: every rewrite against G5's model, and that a wrong
  rewrite is caught) and `python scripts/test_quantize_eval.py`.
