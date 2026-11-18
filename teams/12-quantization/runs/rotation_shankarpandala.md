# Quantize and evaluate one checkpoint (rotation, shankarpandala)

Date: 16 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py` as on class `main` (last change `ae821a6`,
2 Nov), the default format list. The GGUF files stayed on my machine and are not in this pull request.
`runs/runs.csv` was not changed: the script wrote its rows to scratch files outside the repo, and the tables below
come from them.

This is a stand-in checkpoint, not dry run 1 evidence: no dry run 1 checkpoint is open to rotation members yet.

**Why this checkpoint.** It is the same model and revision as #18 (`Qwen/Qwen2.5-1.5B`), so the two runs compare
directly on different hardware (Apple GPU against a Colab CPU) and different llama.cpp builds. On the Apple GPU the
whole 200-item stand-in set takes 17 minutes, so this run also scores all 200 items, not only the 16-item sample.

## Checkpoint

| Field | Value |
| --- | --- |
| Model | `Qwen/Qwen2.5-1.5B` |
| Revision | `8faed761d45a263340a0528343f099c05c9a4323` |
| Licence | Apache-2.0 |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp b9310 (`e2ef8fe42`, Homebrew), Metal, all layers on the GPU (`-ngl 99`, the default) |
| Machine | Apple M5 Pro, 24 GB, macOS 27.0.1 |
| Prompts | few-shot completion (base model), as the script picks |

Router type: `-` (dense model). Output weights: `tied:BF16` for bf16 and `tied:Q8_0` for every quantized format, so
the output layer stays at 8 bits or more.

## Eval 1: the 16-item sample, against #18

The script's stand-in set (standin-v0: mmlu100+gsm8k100, seed 0) and its seeded 16-item sample (`--limit 16`), as in
#18, so both runs score the same 16 items.

| Format | Size | Bits per weight | Score here | Score in #18 | Same |
| --- | ---: | ---: | ---: | ---: | --- |
| bf16 | 3.09 GB | 16.0 | 0.6875 | 0.6875 | yes |
| Q8_0 | 1.65 GB | 8.52 | 0.6875 | 0.6875 | yes |
| Q6_K | 1.33 GB | 6.87 | 0.5625 | 0.5625 | yes |
| Q5_K_M | 1.18 GB | 6.11 | 0.5625 | 0.625 | no, 1 item |
| Q4_K_M | 1.04 GB | 5.39 | 0.6875 | 0.625 | no, 1 item |
| Q3_K_M | 0.88 GB | 4.55 | 0.5625 | 0.6875 | no, 2 items |
| Q2_K | 0.73 GB | 3.79 | 0.125 | 0.125 | yes |

- Sizes and bits per weight match #18 exactly. bf16, Q8_0, Q6_K and Q2_K give the same score.
- Q5_K_M, Q4_K_M and Q3_K_M differ by 1 or 2 of the 16 items. The files are not the same as in #18: the bf16 GGUF is
  `e6cff32d...` here and `5d8d53d3...` there, because the llama.cpp builds differ (b9310 here, b11669 there). The Metal
  and CPU backends also need not give the same greedy tokens.
- One item moves a 16-item score by 0.0625, so a 16-item sample from one machine cannot rank Q3_K_M to Q5_K_M.

## Eval 2: all 200 items of the stand-in set

| Format | Score | MMLU (100) | GSM8K (100) | Against bf16 | Quantize | Eval | Tokens per second | sha256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| bf16 | 0.645 | 0.62 | 0.67 | | 0.0 s | 249.4 s | 76.7 | `e6cff32d4e7311cd99df8f31a0f31737ef61da8e1869cb9ab805d433f439c9fe` |
| Q8_0 | 0.645 | 0.62 | 0.67 | 0 | 2.8 s | 148.4 s | 131.6 | `0ed9086b053cefa0020db1b02e8a947d656cdcd4eadd4d0dde4323f6152df9da` |
| Q6_K | 0.625 | 0.61 | 0.64 | -0.020 | 3.7 s | 138.3 s | 141.1 | `23b8938d4cf4b37e1bbc5eb1f0159e7f184a88b94e00ced421e30818dec97aed` |
| Q5_K_M | 0.625 | 0.60 | 0.65 | -0.020 | 5.2 s | 141.1 s | 142.8 | `3562141d92b1893b7de00c832091714bca826d14f3f611ffc89d030f58e510ec` |
| Q4_K_M | 0.580 | 0.60 | 0.56 | -0.065 | 5.7 s | 116.6 s | 180.4 | `6a1abe0c55006d52ef3e0467a01b476b00f9ae34c6be22feab11f4bd5112cf53` |
| Q3_K_M | 0.520 | 0.58 | 0.46 | -0.125 | 3.6 s | 124.2 s | 169.6 | `6c01cc1419c091bfdf2777af529c49ac7cdb1fd1a8c6cbdc0650d834b7b0f57b` |
| Q2_K | 0.215 | 0.40 | 0.03 | -0.430 | 5.7 s | 121.5 s | 191.1 | `657a6d4ba12b35dc625399ef00a88a4066b01fee19e8baedb4bfd6662f417bb2` |

## What it shows

- **Q8_0 scores the same as bf16 on all 200 items**, on both MMLU and GSM8K.
- **Below Q6_K the score falls step by step, and GSM8K falls fastest.** Q4_K_M answers 11 fewer of the 100 GSM8K
  items than bf16 (0.67 to 0.56) and 2 fewer MMLU items. Q3_K_M answers 21 fewer GSM8K items.
- **The 16-item sample hid this.** There, Q4_K_M scored the same as bf16 (here) or one item lower (#18). On 200
  items it is 13 items (6.5 points) lower.
- Against `docs/bitwidth_proposal.md`: its GSM8K drop limit is -4 points. The Q4_K_M point estimate here is -11 points
  and MMLU is -2 (limit -3). This is the stand-in set with few-shot prompts, not eval_mini, and the script keeps no
  per-item answers, so there is no paired test (McNemar). It is a signal to check, not a gate result.
- Noise: one score on 100 items has a standard error of about 0.05, and on 200 items about 0.034.

My suggestion (not a team decision): score a format on the whole set, not on a 16-item sample, when a GPU is
available, since it costs minutes. Saving each item's answer would let `paired.py` test the differences.

## Eval 3: the paired check on eval_mini (follow-up)

To test the GSM8K signal above, the same bf16, Q6_K, Q5_K_M and Q4_K_M files were scored on the full eval_mini
profile (1,870 items) with `eval_mini/` and compared item by item with `paired.py`. Results, logs and per-item rows:
`eval_mini/results/qwen2.5-1.5b/`.

| Format | ARC-C | HellaSwag | MMLU | GSM8K | TruthfulQA-mc2 | Inside every limit of `bitwidth_proposal.md` |
|---|---:|---:|---:|---:|---:|---|
| Q6_K | +1.0 | -1.2 | +0.7 | +2.5 | +0.4 | yes |
| Q5_K_M | +1.0 | -1.2 | +0.2 | +0.5 | +0.1 | yes |
| Q4_K_M | -0.8 | -0.8 | -0.7 | **-5.0** (p 0.174) | -0.6 | no: GSM8K, limit -4 |

- The GSM8K drop is real in direction but about half the stand-in estimate: -5.0 points (95% CI -11.5 to +1.5),
  not a significant loss (McNemar p 0.174). The proposal's rule still fails Q4_K_M on the point estimate.
- **Q5_K_M is the smallest format inside every limit for this model.**
- Wall clock on the Apple GPU: 1066 s (bf16), 689 s (Q6_K), 745 s (Q5_K_M), 635 s (Q4_K_M). No paid cost.

## Time and cost

| What | Value |
| --- | --- |
| Quantize time | 26.7 s across the 6 quantized files (2.8 to 5.7 s each). bf16 is the convert output, so its quantize time is 0. |
| Eval time, 16 items | 59.5 s across the 7 files |
| Eval time, 200 items | 1039.5 s (17.3 min) across the 7 files |
| Wall clock, command 1 (16 items) | 270.4 s (4.5 min): download, llama.cpp checkout at b9310, convert venv, bf16 convert, 6 quantizations, 7 evals |
| Wall clock, command 2 (200 items) | 1072.6 s (17.9 min): the GGUF files of command 1 are reused |
| Generation speed | 77 to 191 tokens per second on 200 items, 91 to 214 on 16 items; #18 on a 2-core Colab CPU: 2.4 to 6.2 |
| File size | 3.09 GB at bf16, 1.04 GB at Q4_K_M, 0.73 GB at Q2_K |
| Paid cost | None: my own laptop. No cloud units, no rented GPU. |
| Setup | llama.cpp from Homebrew (b9310) was already installed. On macOS the script needs Homebrew `git` and `/usr/sbin` (for `sysctl`) on `PATH`: my first two attempts stopped there, in under 2 s each. |

The same 16-item job took 3778 s on the Colab CPU in #18 and 270 s here.

The commands (from the repository root, class `main` checkout):

```bash
export PATH=/opt/homebrew/bin:$PATH:/usr/sbin      # Homebrew git; sysctl
python3 teams/12-quantization/scripts/quantize_eval.py \
  --model Qwen/Qwen2.5-1.5B \
  --revision 8faed761d45a263340a0528343f099c05c9a4323 \
  --formats bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K \
  --llama-bin /opt/homebrew/bin \
  --work <scratch> \
  --limit 16 \
  --runs-csv <scratch>/runs_limit16.csv
# command 2: the same without --limit, with --runs-csv <scratch>/runs_full.csv
```

Last lines of command 2 (wall time from `/usr/bin/time -p`):

```
Q2_K: score 0.215 {"mcq": 0.4, "numeric": 0.03} | 0.73 GB, 3.79 bpw | quant 5.7s, eval 121.5s, 191.1 tok/s
real 1072.55
```
