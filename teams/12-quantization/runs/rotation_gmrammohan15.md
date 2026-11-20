# Quantize and evaluate one checkpoint (rotation, gmrammohan15)

Date: 19 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py` at `G12-Week3-Rotation` `8b9aeec` (the
scripts are the same as on `G12-Week3` `a7bb4b2`), the default format list, on a laptop (Apple M3 Pro). The GGUF files
stayed on my machine and are not in this pull request. `runs/runs.csv` was not changed: the script wrote its rows to
scratch files outside the repo, and the tables below come from them.

This is a stand-in checkpoint, not dry run 1 evidence: no dry run 1 checkpoint is open to rotation members (task 5,
theschoolofai/era-v5-lab#508, sends a job request for it).

**Why this checkpoint.** The other rotation runs used Hub models through `--model` (Qwen #13 #18 #20, Granite #16
#19 #23, Llama #21, Sarvam #25). None of them used the week 3 path, `--checkpoint`, which takes a G5 checkpoint
through `export_hf.py` (test A1), the conversion and `check_gguf_logits.py` (test A3). This run does: a random G5
checkpoint made by `scripts/make_random_checkpoint.py` with **the exact shape of dry run 1**
(`teams/05-architecture/jobs/evidence/2026-11-15-dryrun1/manifest.json`: 237,052,416 parameters). So the sizes, the
times and the memory are those the dry run 1 checkpoint will have, and the A1 and A3 checks run at that size before the
real job. The scores mean nothing: the weights are random.

## Checkpoint

| Field | Value |
| --- | --- |
| Checkpoint | random G5 `LanguageModel`, `make_random_checkpoint.py --d-model 512 --n-layer 8 --n-head 8 --n-kv-head 2 --d-ff 768 --n-expert 16 --n-shared 1 --top-k 2 --pos-dim 32 --seq-len 2048` (seed 0, `--std 0.1`, the default) |
| Shape | the same as dry run 1: 8 layers, width 512, 8 heads, 2 key-value heads, 16 routed experts + 1 shared, top-2, expert width 768, vocabulary 131,072, KE byte table P32. 237,052,416 parameters (dry run 1 manifest: 237,052,416) |
| `checkpoint.pt` sha256 | `bc0c12355abdbd2709bd131406def86f237436c8965d1a9ea23c50b78579ee30` (0.95 GB, fp32) |
| Tokenizer | **stand-in**, not p1536 (below). sha256 `ba56172d8358404a6cf1ed21e22fc867438c4ffc4f54b1625493f9001206cda7`, 131,072 ids, passed with `--tokenizer-sha256` |
| Exported model | Granite MoE Shared, 299,966,976 parameters in bf16 (the KE2 table folded into a full embedding) |
| GGUF | `granitemoe`, pre-tokenizer `granite-embed-multi-97m`, n_vocab 131,072, context 2,048 |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp b12359 (`b1b770d90`, Homebrew 1.0.0), Metal, all layers on the GPU (`-ngl 99`); the converter at the same tag |
| Machine | Apple M3 Pro, 18 GB, macOS 27.2 |
| Eval | standin-v0 (mmlu100+gsm8k100, seed 0), all 200 items, completion prompts (base model), as the script picks |

**The stand-in tokenizer.** The p1536 `tokenizer.json` is in a private Kaggle dataset I could not get in time, and
Hugging Face downloads are blocked on my network, so no Hub tokenizer either. p1536 is built on o200k base ids, so the
stand-in is OpenAI's `o200k_base.tiktoken` (sha256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`,
from `openaipublic.blob.core.windows.net`) cut to its first 131,070 ranks, turned into a byte-level BPE
`tokenizer.json` (130,814 merges, each found by re-running BPE on the token with the lower ranks), plus
`<|begin_of_text|>` and `<|endoftext|>`: 131,072 ids, the size of p1536. It sets the vocabulary size and the KE byte
table; the model's weights are random either way. The tokenizer round trip (`--roundtrip`) was not run: its held-out
text streams from Hugging Face. The p1536 round trip is in #26 (0 of 20,400 lines differ when the app sends ids).

**The stand-in eval set.** The script downloads the MMLU and GSM8K test parquet files from Hugging Face. Here they were
rebuilt from the original sources and put where the script looks (`<work>/standin-{mmlu,gsm8k}.parquet`), so
`make_standin` ran unchanged: MMLU from `people.eecs.berkeley.edu/~hendrycks/data.tar` (sha256 `bec563ba…989b`, 57
test CSVs in subject order, 14,042 rows, as `cais/mmlu` `all`) and GSM8K from `openai/grade-school-math`
`test.jsonl` (sha256 `3730d312…9d14`, 1,319 rows). The row counts match the Hub files. I did not check that the row
order is the same, so the 200 items may differ from the other rotation runs. With random weights that does not matter.

## Result

| Format | Size | Bits per weight | Router | Output | Score (200) | Quantize | Eval | Tokens per second | sha256 |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| bf16 | 0.61 GB | 16.0 | F32 | BF16 | 0.000 | 0.0 s | 144.3 s | 384 | `76d8c5f3be870d46bbfe89182dd1f9871922e56ea998dfe8fbffce466abd9915` |
| Q8_0 | 0.32 GB | 8.57 | F32 | Q8_0 | 0.005 | 1.0 s | 107.3 s | 513 | `a8eafbbce2a56451bb410b8fb14f06161402cd455f5dff78897d107503567147` |
| Q6_K | 0.27 GB | 7.08 | F32 | Q8_0 | 0.005 | 1.4 s | 98.4 s | 537 | `177f4935fc09725c1eb28302616ee2674d7e911e2a0328329462a019093e8d51` |
| Q5_K_M | 0.24 GB | 6.36 | F32 | Q8_0 | 0.000 | 1.9 s | 104.8 s | 526 | `7755c46afe4cb015ddb1276e53dc3fec1563aed80afad39ad8e654a8fd9b1845` |
| Q4_K_M | 0.21 GB | 5.68 | F32 | Q8_0 | 0.005 | 2.2 s | 97.2 s | 533 | `047c1e062b536cb083ac4a731689c8569eb3a564084497c8930ee0eb52ef9c9c` |
| Q3_K_M | 0.18 GB | 4.87 | F32 | Q8_0 | 0.005 | 1.1 s | 102.6 s | 525 | `f547c87d4383de0c07c75a91d350ccee9fa0a874e8a97a4de5cab50f1ede195d` |
| Q2_K | 0.16 GB | 4.20 | F32 | Q8_0 | 0.000 | 1.6 s | 95.7 s | 551 | `9536a25224ff2a621caa8a0548a52617f7d1c241a9f059d855ca65bc90b6a522` |

- **The week 3 path works at dry run 1 size**, with no manual step: export, A1, conversion with the forced
  pre-tokenizer, A3, six quantizations, eval. The router (`ffn_gate_inp`) is F32 and the output layer Q8_0 or more in
  every file.
- **Bits per weight are high for a "4-bit" file** (Q4_K_M 5.68): the output layer is kept at Q8_0, and the embedding
  and output matrices (131,072 × 512, 67 M weights each) are a large share of a 300 M-weight export.
- Scores are 0 or 1 item of 200 (random weights).

## Test A1 and A3

| Check | Result |
| --- | --- |
| A1: exported HF model against G5's model, fp32, 64 prompts × 64 tokens | max logit difference 0.00022 (limit 0.001), same top-1 on 4,096 of 4,096 positions: **PASS** |
| A3: llama.cpp on the bf16 GGUF against G5's model, 16 prompts | same top-1 on 12 of 16, max log-probability difference 1.24 (limit 0.05): **FAIL** (the script reports it and goes on) |

**Why A3 fails here, and why it is not a wiring error.** I made two more random checkpoints and ran the same command
on each (bf16 only, 2 items):

| Random checkpoint | A1 | A3 |
| --- | --- | --- |
| dry run 1 shape, `--std 0.1` (the run above) | PASS, 0.00022 | FAIL: 12/16 same top-1, 1.2355 |
| dry run 1 shape, `--std 0.02` | PASS, 1.6e-06 | PASS: 16/16, 0.0180 |
| `--n-layer 2`, otherwise the same, `--std 0.1` | PASS, 4.1e-05 | PASS: 16/16, 0.0411 |

With 2 layers at `--std 0.1` attention is far from uniform, so the q/k reordering for RoPE is tested, and A3 passes;
at 8 layers with the same weights it fails. llama.cpp keeps keys and values in fp16 and uses its own kernels, and 8
layers of large random weights amplify those small differences. At `--std 0.02`, nearer the scale of trained weights,
it passes. The script's docstring says its 0.05 limit is not calibrated on a trained checkpoint; this adds that on a
random checkpoint the limit depends on depth and weight scale. The A3 result on the real dry run 1 checkpoint (#508)
is the one that counts.

## Drift of each format from G5's model (A3 on every file)

`check_gguf_logits.py` also runs on a quantized GGUF: it then measures how far each format moves from G5's model on
the same 16 prompts. Same top-1 out of 16, and the max log-probability difference:

| Format | `--std 0.02` checkpoint | `--std 0.1` checkpoint (the run above) |
| --- | --- | --- |
| bf16 | 16, 0.018 | 12, 1.24 |
| Q8_0 | 15, 0.018 | 8, 2.50 |
| Q6_K | 14, 0.034 | 6, 8.60 |
| Q5_K_M | 15, 0.060 | 1, 7.22 |
| Q4_K_M | 14, 0.112 | 0, 11.8 |
| Q3_K_M | 10, 0.245 | 0, 9.62 |
| Q2_K | 6, 0.361 | 0, 14.2 |

On the `--std 0.02` checkpoint the difference grows at every step down, about doubling from Q5_K_M to Q4_K_M to
Q3_K_M. The top-1 changes even when the difference is small, because a random model's top tokens are almost tied.
My suggestion (not a team decision): run `check_gguf_logits.py` on every format of the dry run 1 GGUFs too. It takes
about 7 s per file and gives a drift number that does not need a working model.

## Time and cost

| What | Value |
| --- | --- |
| Make the random checkpoint | 13.0 s |
| Wall clock, the whole command (200 items, 7 formats) | **896.4 s (14.9 min)**; `/usr/bin/time -p`: user 317 s, sys 86 s |
| of which: llama.cpp checkout at b12359 | 15 s |
| of which: conversion venv (uv, warm cache) | 7 s |
| of which: export and A1 | 52 s (the two extra checkpoints: 28 s and 17 s) |
| of which: conversion to bf16 GGUF and A3 | 22 s (21 s and 15 s) |
| of which: quantize, 6 files | 9.2 s (1.0 to 2.2 s each); the `--std 0.02` checkpoint: 8.3 s |
| of which: eval, 7 files × 200 items | 750 s (96 to 144 s per file) |
| A3 on one file | about 7 s (3 files in 23 s) |
| Generation speed | 384 tokens per second at bf16, 513 to 551 for the quantized files |
| Disk | checkpoint 0.95 GB, HF export 0.6 GB, bf16 GGUF 0.61 GB, six quantized files 1.39 GB, llama.cpp source and venv 0.9 GB |
| Paid cost | **None**: my own laptop. No cloud units, no rented GPU. |

The eval dominates (84% of the wall clock). A random model never writes a stop sequence, so each GSM8K item runs to the
512-token limit; a trained model stops sooner, so on the real checkpoint the eval should take less time, not more. The
checkout, export, conversion and quantization of the 237 M model take under 2 minutes (105 s), so the flow's own cost
on the dry run 1 checkpoint is small next to its eval.

Setup notes for macOS: put Homebrew first on `PATH` and add `/usr/sbin` (for `sysctl`), as #20 found. Then `python3`
may become Homebrew's Python without numpy or torch, so call the Python that has them (I used miniconda's) for
`make_random_checkpoint.py` and `quantize_eval.py`.

## Commands

From the repository root, `G12-Week3-Rotation` checkout. `<scratch>` is outside the repo; `standin-mmlu.parquet` and
`standin-gsm8k.parquet` built as above were copied into `<scratch>/work` first.

```bash
export PATH=/opt/homebrew/bin:$PATH:/usr/sbin
PY=~/miniconda3/bin/python3        # a Python with torch and numpy
SHAPE="--d-model 512 --n-layer 8 --n-head 8 --n-kv-head 2 --d-ff 768 --n-expert 16 --n-shared 1 --top-k 2 --pos-dim 32 --seq-len 2048"
$PY teams/12-quantization/scripts/make_random_checkpoint.py --tokenizer <scratch>/tokenizer.json \
  --out <scratch>/ckpt-dr1shape $SHAPE
$PY teams/12-quantization/scripts/quantize_eval.py --checkpoint <scratch>/ckpt-dr1shape \
  --tokenizer <scratch>/tokenizer.json \
  --tokenizer-sha256 ba56172d8358404a6cf1ed21e22fc867438c4ffc4f54b1625493f9001206cda7 \
  --work <scratch>/work --runs-csv <scratch>/runs.csv --llama-bin /opt/homebrew/bin
# A3 on every format (the venv the flow made has torch and gguf):
for f in bf16 Q8_0 Q6_K Q5_K_M Q4_K_M Q3_K_M Q2_K; do
  <scratch>/work/.venv-convert/bin/python teams/12-quantization/scripts/check_gguf_logits.py \
    --checkpoint <scratch>/ckpt-dr1shape --gguf <scratch>/work/ckpt-dr1shape-bc0c1235-$f.gguf \
    --llama-server /opt/homebrew/bin/llama-server
done
# The two extra checkpoints: the same with --std 0.02, and with --n-layer 2;
# quantize_eval.py --formats bf16 --limit 2 --no-record for the A3 check.
```

Last lines of the main command:

```
[09:00:23] Q2_K: score 0.0 {"mcq": 0.0, "numeric": 0.0} | 0.16 GB, 4.2 bpw | quant 1.6s, eval 95.7s, 551.3 tok/s
real 896.37
```

## Still open

- The same run with the p1536 tokenizer, once I have it. Only the tokenizer hash and the GGUF hashes should change:
  the vocabulary size and the shape are the same.
- The tokenizer round trip, from a network where Hugging Face is open (the p1536 result is already in #26).
