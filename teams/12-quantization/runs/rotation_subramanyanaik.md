# Quantize and evaluate one checkpoint (rotation, subramanyanaik)

Date: 18 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py` at `G12-Week3` `26968de`, the default
format list, on a free Colab T4. Drift check: `teams/12-quantization/quality/kl_eval.py` at the same commit, on English
and on Kannada text. Both scripts ran unchanged. The GGUF files stayed on the Colab machine and are not in this pull
request. `runs/runs.csv` and `quality/kl.csv` were not changed: the scripts wrote their rows to scratch files outside the
repo, and the tables below come from them. The numbers, hashes and times are also in
[`rotation_subramanyanaik.json`](rotation_subramanyanaik.json). The notebook that ran everything is
[`rotation_subramanyanaik_colab.ipynb`](rotation_subramanyanaik_colab.ipynb).

This is a stand-in checkpoint, not dry run 1 evidence: no dry run 1 checkpoint is open to rotation members yet.

**Why this checkpoint.** The earlier rotation runs are Qwen (#13, #18, #20, #22), Granite (#16, #19, #23) and Llama
(#21). None of them is an Indic model. Sarvam-1 was trained for 10 Indic languages and English, and it has its own
68K SentencePiece vocabulary. So besides the stand-in score, this run measures what the stand-in set cannot see: how
far each format drifts from bf16 on **Kannada** text, next to the same measure on **English** text.
`docs/bitwidth_proposal.md` sets no limit for Indic tasks, and it says KL is not a gate. This run gives one model's
numbers for that gap.

## Checkpoint

| Field | Value |
| --- | --- |
| Model | `sarvamai/sarvam-1` |
| Revision | `e9607337286ddf496d4a2562b194e489dcf3feea` |
| Licence | Sarvam AI Research License (non-commercial and research use; the weights and GGUFs are not redistributed here) |
| Architecture | `LlamaForCausalLM` (llama.cpp `llama`): 28 layers, width 2,048, 16 heads with 8 KV heads, FFN 11,008, vocabulary 68,096, untied embeddings, 2.52 B weights, trained context 8,192 |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp b11669 (`620d222`), the release's prebuilt `ubuntu-cuda-12.8-x64` binaries (sha256 checked against the release), all layers on the GPU (`--ngl 99`) |
| Machine | Google Colab, free tier: Tesla T4 15 GB (driver 580.82.07), Intel Xeon @ 2.00GHz, 2 cores, 12.7 GB RAM, Linux 6.6.159+ |
| Prompts | few-shot completion (base model), as the script picks; context 4,096 |

Router type: `-` (dense model, no router tensor). Output weights: Sarvam-1 does not tie them to the token embeddings,
so `output.weight` is its own 2,048 x 68,096 tensor (139.5 M weights, 5.5% of the model). It is `BF16` in the bf16 file
and `Q8_0` in every quantized file, so the output layer stays at 8 bits or more. The token embeddings are quantized
with the rest (for example `q4_K` in Q4_K_M).

## Eval 1: the 16-item sample

The script's stand-in set (standin-v0: mmlu100+gsm8k100, seed 0) and its seeded 16-item sample (`--limit 16`): 8 MMLU
and 8 GSM8K, the same 16 items as #13, #18, #19 and #23. No item text is stored here. This is not the full G9
eval-mini set. One score is the share of the 16 items answered correctly.

| Format | Size | Bits per weight | Score | By kind | Quantize | Eval | Tokens per second | Router | Output | sha256 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| bf16 | 5.05 GB | 16.0 | 0.3125 | mcq 0.375, numeric 0.25 | 0.0 s | 109.5 s | 46.2 | - | BF16 | `cfc747d2990ba2b2abd9687808bad2447efed28b3218ebfd0f1989deacc4408f` |
| Q8_0 | 2.69 GB | 8.5 | 0.1875 | mcq 0.25, numeric 0.125 | 34.8 s | 65.5 s | 69.6 | - | Q8_0 | `4c3fee3cfe1bdaba0c8d665a26c99f29b502b3f0bc27abfc9bbd577f6c96c3c7` |
| Q6_K | 2.11 GB | 6.67 | 0.1875 | mcq 0.375, numeric 0.0 | 133.3 s | 71.1 s | 72.3 | - | Q8_0 | `ae520471996c11ca47f2ca9bc6cb51fcb243a7e1893c66a72977c15f34f6c852` |
| Q5_K_M | 1.84 GB | 5.82 | 0.1875 | mcq 0.375, numeric 0.0 | 259.0 s | 65.2 s | 85.6 | - | Q8_0 | `31ecb934ff0420495a9ffbd8a1ee781d6484417549be61faa369eec0f190b2fc` |
| Q4_K_M | 1.58 GB | 5.01 | 0.1875 | mcq 0.375, numeric 0.0 | 306.0 s | 60.8 s | 93.4 | - | Q8_0 | `21f4188147d745473aeda10b4a5cd3c69f1eaf2dfb2bbfc37e389ea30846bebd` |
| Q3_K_M | 1.29 GB | 4.07 | 0.125 | mcq 0.125, numeric 0.125 | 154.1 s | 62.9 s | 83.2 | - | Q8_0 | `da08e815eea268506f5816b79e7d56ae046ad1a0027258a4977a6b4222bc59df` |
| Q2_K | 1.02 GB | 3.22 | 0.25 | mcq 0.5, numeric 0.0 | 187.1 s | 65.4 s | 90.1 | - | Q8_0 | `bffc1c49f76e5f3271b1372b9a91e29f1d676612d7be0cccdf2ead218bf416b7` |

## Eval 2: all 200 items of the stand-in set

The same seven files as Eval 1 (the script reused them; every sha256 is the same), scored on all 200 items: 100 MMLU
and 100 GSM8K. One score on 100 items has a standard error of about 5 points, and on 200 items about 3.

| Format | Score | MMLU (100) | GSM8K (100) | Against bf16 | MMLU against bf16 | GSM8K against bf16 | Eval | Tokens per second |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bf16 | 0.215 | 0.40 | 0.03 |  |  |  | 1184.1 s | 45.8 |
| Q8_0 | 0.21 | 0.39 | 0.03 | -0.5 | -1 | +0 | 795.7 s | 68.4 |
| Q6_K | 0.205 | 0.40 | 0.01 | -1.0 | +0 | -2 | 852.8 s | 65.4 |
| Q5_K_M | 0.21 | 0.39 | 0.03 | -0.5 | -1 | +0 | 658.4 s | 81.1 |
| Q4_K_M | 0.22 | 0.42 | 0.02 | +0.5 | +2 | -1 | 630.5 s | 87.1 |
| Q3_K_M | 0.23 | 0.43 | 0.03 | +1.5 | +3 | +0 | 659.7 s | 75.7 |
| Q2_K | 0.145 | 0.29 | 0.00 | -7.0 | -11 | -3 | 615.9 s | 81.2 |

Drops are in points (items out of 100 for MMLU and GSM8K).

## Eval 3: drift from bf16 on English and on Kannada text

`quality/kl_eval.py` as it is: `llama-perplexity --kl-divergence` on 64 chunks of 512 tokens, so 16,384 scored tokens
per text, with the bf16 file as the reference. This is the same setting as `quality/kl.csv` (OLMoE).

- **English:** WikiText-2 raw test, the script's own pinned text.
- **Kannada:** the first 256 whole documents, in file order, of `ai4bharat/sangraha` `verified/kan/data-0.parquet`
  at revision `8b813c3f62d37b2fa174d68c31e8b35ae2fe85e8` (CC-BY-4.0): 566,923 characters, sha256
  `822a0e2e0ad65ccfa5b528c9a46b96e91b3fdf578228f5e58d263abea21e8995`. The script reads `<work>/<text>.test.txt` when
  that file exists, so the notebook wrote the text there and added the name `sangraha-kn` to the script's `TEXTS`
  at run time. The script file was not edited. No text is stored here. Sangraha `verified` is Kannada web and PDF
  text, not machine-translated (unlike Sangraha `synthetic`).

| Format | Size | KL mean, English | KL mean, Kannada | Same top-1, English | Same top-1, Kannada | PPL ratio, English | PPL ratio, Kannada |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bf16 | 5.05 GB | (reference) | (reference) | | | PPL 6.616 ± 0.124 | PPL 11.621 ± 0.243 |
| Q8_0 | 2.69 GB | 0.0068 | 0.0073 | 95.25% ± 0.17 | 94.51% ± 0.18 | 1.0084 ± 0.0013 | 1.0057 ± 0.0010 |
| Q6_K | 2.11 GB | 0.0133 | 0.0144 | 93.73% ± 0.19 | 92.55% ± 0.21 | 1.0111 ± 0.0016 | 1.0121 ± 0.0015 |
| Q5_K_M | 1.84 GB | 0.0301 | 0.0326 | 91.10% ± 0.22 | 89.87% ± 0.24 | 1.0317 ± 0.0023 | 1.0270 ± 0.0022 |
| Q4_K_M | 1.58 GB | 0.0823 | 0.0887 | 86.45% ± 0.27 | 83.81% ± 0.29 | 1.0735 ± 0.0039 | 1.0817 ± 0.0041 |
| Q3_K_M | 1.29 GB | 0.2449 | 0.2708 | 77.58% ± 0.33 | 72.80% ± 0.35 | 1.2562 ± 0.0080 | 1.3212 ± 0.0088 |
| Q2_K | 1.02 GB | 1.3543 | 1.4391 | 49.77% ± 0.39 | 40.65% ± 0.38 | 3.7413 ± 0.0563 | 4.0972 ± 0.0603 |

The KL 99th percentiles, the uncertainties of the KL means and the pass times are in the JSON file.

## What it shows

- **Kannada drifts more than English at every format.** On Kannada the quantized model picks a different next token
  than bf16 more often: the gap in same top-1 grows from 0.7 points at Q8_0 to 1.2 at Q6_K and Q5_K_M, 2.6 at
  Q4_K_M, 4.8 at Q3_K_M and 9.1 at Q2_K. Each gap is 3 to 17 times its uncertainty (about ±0.25 to ±0.55 points).
  The mean KL is 6% to 11% higher on Kannada at every format. The perplexity ratio is not higher on Kannada at
  Q8_0 to Q5_K_M (it is slightly lower at Q8_0 and Q5_K_M, by about 1.5 times its uncertainty), and it is higher
  from Q4_K_M down (1.082 against 1.074 at Q4_K_M, 1.32 against 1.26 at Q3_K_M). These are two different texts, so read the gap as one measurement on one model, not a
  rule for every Indic language.
- **Q4_K_M moves 1 next token in 6 on Kannada and 1 in 7 on English.** Q8_0 moves 1 in 18 on Kannada and 1 in 21 on
  English.
- **The stand-in set sees no drop until Q2_K, while drift grows at every step.** On all 200 items, Q8_0 to
  Q3_K_M score 0.205 to 0.23 against 0.215 at bf16, and MMLU stays at 0.39 to 0.43 against 0.40. These are all within
  one standard error. Q2_K breaks: MMLU falls 11 points to 0.29 and GSM8K to 0. GSM8K cannot show anything for this
  model: bf16 answers 3 of 100, so there is no room to fall. So the stand-in set here measures only MMLU, in English,
  for a model built for Indic text. Q3_K_M even scores 3 MMLU points above bf16, yet it changes about 1 next token in
  4.5 on English and 1 in 3.7 on Kannada. The script keeps no per-item answers, so there is no paired test. This
  agrees with `docs/bitwidth_proposal.md`, which does not keep Q3_K_M.
- **The 16 items cannot rank the formats either.** bf16 answers 5 of 16, Q8_0 to Q4_K_M answer 3, Q3_K_M answers 2
  and Q2_K answers 4. One item is 0.0625. As in #19, a base model near chance on this sample (3 of 8 MMLU items at
  bf16, where guessing gives 2) leaves no room to see a drop.
- **This model drifts more than OLMoE at the same setting.** On WikiText-2 with 64 x 512 chunks, `quality/kl.csv`
  has OLMoE Q4_K_M at KL 0.023 and 92.1% same top-1. Sarvam-1 is at 0.082 and 86.5%. At Q8_0 the figures are 0.0013
  and 98.3% for OLMoE against 0.0068 and 95.2% here. These are two different models on two different backends
  (Metal there, CUDA here), so this is a note, not a ranking. A small dense model need not hold up like OLMoE does.
- **Smaller files generate faster on the T4.** Speed rises from 46 tokens per second at bf16 to 93 at Q4_K_M (2.0x),
  so the T4 is limited by reading the weights here. On the A100 in #23 every format ran at the same speed.
- **Bits per weight sit above the nominal width,** for example 5.01 for Q4_K_M: the untied output layer stays at Q8_0
  and is 5.5% of the weights. `Q4_K_M` is 3.2x smaller than bf16 (1.58 GB against 5.05 GB).

## Time and cost

| What | Value |
| --- | --- |
| Setup | 47.9 s for the prebuilt llama.cpp b11669 CUDA release (download, sha256 check, unpack); 5.0 s for the sparse checkout of the repo at `26968de` and `uv`. No source build. |
| Download | 93 s for the 5.05 GB checkpoint (Hugging Face to Colab). |
| bf16 convert | 88 s. The script's convert venv (llama.cpp checkout at b11669 and `uv` installs) took 21 s before the download. |
| Quantize time | 1,074.3 s across the 6 quantized files (34.8 to 306.0 s each). `llama-quantize` runs on the CPU, and this runtime has 2 cores. #23 took 206.5 s on 12 cores. |
| Eval time, 16 items | 500.4 s across the 7 files. |
| Wall clock of command 1 (16 items) | 2,080.5 s (34.7 min): download, convert, quantize and eval, plus 304 s of hashing, tensor checks and seven server starts. |
| Drift check | 11.6 s to fetch the Kannada text; 284.8 s for English and 311.2 s for Kannada (bf16 pass and six format passes each). |
| Wall clock of command 2 (200 items) | 5,652.6 s (94.2 min): eval 5,397.1 s across the 7 files (615.9 to 1,184.1 s each), with the GGUF files of command 1 reused. Command 2 ran after the drift check: it was stopped right after it began (before any score) and then run again from the start. |
| Whole session | 2.6 h (03:17 to 05:53 UTC), from the first cell to the final zip. The cells ran for 2.33 h; the rest is time between cells. |
| GPU use | Peak GPU memory 5.18 GB (the bf16 file). Mean utilisation 19.4% during command 1 and the drift check, where the CPU-bound quantize step takes most of the time, and 76.6% during command 2. |
| File size | 5.05 GB at bf16, 1.58 GB at `Q4_K_M`, 1.02 GB at `Q2_K`. |
| Paid cost | None: the free Colab tier, so no compute units and no rented GPU. For comparison, at the T4 rate #23 quotes for Colab Pro (about 1.2 units per hour) this session would be about 3.1 units, about 0.31 USD at the 9.99 USD per 100 units #23 uses. |

The commands (from the repository root, as the notebook runs them):

```bash
python teams/12-quantization/scripts/quantize_eval.py \
  --model sarvamai/sarvam-1 \
  --revision e9607337286ddf496d4a2562b194e489dcf3feea \
  --formats bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K \
  --ngl 99 \
  --llama-bin <llama.cpp b11669 CUDA 12.8>/ \
  --work <work> \
  --limit 16 \
  --runs-csv <scratch>/runs_limit16.csv \
  --scores-out <scratch>/scores_limit16.json
# command 2: the same without --limit, with --runs-csv <scratch>/runs_full.csv --scores-out <scratch>/scores_full.json

python teams/12-quantization/quality/kl_eval.py \
  --model sarvamai/sarvam-1 \
  --revision e9607337286ddf496d4a2562b194e489dcf3feea \
  --text wikitext2 --chunks 64 \
  --work <work> --llama-bin <llama.cpp b11669 CUDA 12.8>/ \
  --out <scratch>/kl_wikitext2.csv
# Kannada: the same with --text sangraha-kn, after the notebook writes <work>/sangraha-kn.test.txt and registers the name
```
