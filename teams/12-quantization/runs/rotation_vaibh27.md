# Quantize and evaluate one checkpoint (rotation, vaibh27)

Date: 17 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py` at `G12-Week3` `a7bb4b2`, the default
format list, on a Colab Pro A100. The GGUF files stayed on the Colab machine and are not in this pull request.
`runs/runs.csv` was not changed: the script wrote its rows to a scratch file outside the repo, and the tables below
come from it. The numbers, hashes and times are also in [`rotation_vaibh27.json`](rotation_vaibh27.json).

This is a stand-in checkpoint, not dry run 1 evidence: no dry run 1 checkpoint is open to rotation members yet.

**Why this checkpoint.** It is a Granite MoE, the architecture family our export targets
([`docs/unsupported_parts.md`](../docs/unsupported_parts.md)), so the router check runs on real router tensors. It is
the larger sibling of the 1B-A400M in #19, and on a GPU the whole ladder takes 9 minutes.

## Checkpoint

| Field | Value |
| --- | --- |
| Model | `ibm-granite/granite-3.1-3b-a800m-instruct` |
| Revision | `a02780686e08a03fe0d2679a293b5c74a90efa89` |
| Licence | Apache-2.0 |
| Architecture | `GraniteMoeForCausalLM` (llama.cpp `granitemoe`): 32 layers, width 1,536, 40 experts with top-8, tied embeddings, 3.30 B weights |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp b11669 (`620d222`), built from source with CUDA for compute capability 8.0, all layers on the GPU (`-ngl 99`) |
| Machine | Google Colab Pro: NVIDIA A100-SXM4-40GB (driver 580.82.07, CUDA 13.0), Intel Xeon @ 2.20GHz, 12 cores, 83.5 GB RAM, Linux 6.6.159+ |
| Prompts | chat (instruct model), as the script picks; context 4,096 |

Router type: `F32` in every file. Output weights: `tied:BF16` for bf16 and `tied:Q8_0` for every quantized format, so
the router and the output layer stay at 8 bits or more.

## Eval

The script's stand-in set, seed 0: standin-v0 (mmlu100+gsm8k100, seed 0), then a seeded sample of 16 items
(`--limit 16`): 8 MMLU and 8 GSM8K. No item text is stored here. This is not the full G9 eval-mini set. One score is
the share of the sampled items answered correctly. The eval ran three times on the same files. The scores were the
same in all three passes; eval time and tokens per second are the median of the three.

| Format | Size | Bits per weight | Score | By kind | Quantize | Eval | Tokens per second | Router | Output | sha256 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| bf16 | 6.60 GB | 16.0 | 0.75 | mcq 0.625, numeric 0.875 | 0.0 s | 8.5 s | 193.9 | F32 | tied:BF16 | `23e14e15b180a0e28de43fe828415613d21f6c658d5076fb6597b2a35f75d4bc` |
| Q8_0 | 3.51 GB | 8.51 | 0.75 | mcq 0.625, numeric 0.875 | 7.8 s | 9.0 s | 184.6 | F32 | tied:Q8_0 | `b843471a8bd08244ddd1baa0fc81f694f742db035d37cf349d09c73aa5242ff3` |
| Q6_K | 2.73 GB | 6.62 | 0.6875 | mcq 0.625, numeric 0.75 | 26.6 s | 9.4 s | 185.0 | F32 | tied:Q8_0 | `5a16f4cb5f24c45ce3bebe84235c23c9bf5ba61e604a0b9748b5159439cc2417` |
| Q5_K_M | 2.37 GB | 5.75 | 0.75 | mcq 0.625, numeric 0.875 | 47.8 s | 8.7 s | 187.1 | F32 | tied:Q8_0 | `6bb5aab8ea584bd621659225bde344a177ca528212765177a40e75c381bd8895` |
| Q4_K_M | 2.04 GB | 4.93 | 0.625 | mcq 0.75, numeric 0.5 | 57.1 s | 7.8 s | 204.4 | F32 | tied:Q8_0 | `5f24d5f6689b7722551a5cd74a73e20fb7f13ffc3306d9452479bb949fef1ae0` |
| Q3_K_M | 1.63 GB | 3.95 | 0.375 | mcq 0.25, numeric 0.5 | 29.8 s | 8.3 s | 184.2 | F32 | tied:Q8_0 | `d35d0681cf68d010ba394d716bcc78eb1bfdff3e70b060fc11d980ea579cb8d1` |
| Q2_K | 1.26 GB | 3.05 | 0.125 | mcq 0.25, numeric 0 | 37.4 s | 11.0 s | 200.1 | F32 | tied:Q8_0 | `c2d87a4dc90fe05776b83f5fb5a3f44d9daa347676095045de6a1fd3132f93ff` |

## What it shows

- **Q8_0 down to Q4_K_M are within noise.** bf16 answers 12 of 16. Q8_0 and Q5_K_M also answer 12, Q6_K 11 and
  Q4_K_M 10. One item is 0.0625. Q4_K_M answers one more MMLU item and three fewer GSM8K items than bf16; on 8 items
  each that is not evidence of a drop.
- **Q3_K_M drops, and Q2_K breaks.** Q3_K_M answers 6 of 16 (6 fewer than bf16; MMLU 2 of 8 against 5 of 8) and Q2_K
  answers 2 (no GSM8K item right). The Q2_K break matches the team's OLMoE result. The Q3_K_M drop is earlier than on
  OLMoE (first real drop at Q3_K_M on MMLU, −4.2 points) and on Qwen2.5-1.5B (#18, 11 of 16 at Q3_K_M). The script
  keeps no per-item rows, so this is not a paired test; 16 items are enough to flag it, not to measure it. G9's
  eval_mini on these files would.
- **This sample can separate formats here and could not in #19.** The 1B-A400M base model answers 5 of 16 at bf16,
  so its drops were all within noise. The 3B-A800M instruct model answers 12, which leaves room to see a fall.
- **Bits per weight are close to the nominal width:** `Q4_K_M` is 4.93 here and 4.99 on the 1B-A400M (#19). The
  embeddings, tied to the output and kept at Q8_0, are 75 M of 3.30 B weights (about 2%), so they lift the average
  little.
- **`Q4_K_M` is 3.2x smaller than bf16** (2.04 GB against 6.60 GB). On the A100 the speed is the same for every format
  (184 to 204 tokens per second): at one request and 800 M active weights, the GPU is not limited by reading the
  weights, so smaller files do not generate faster. On a CPU (#18, #19) they do.

## Time and cost

| What | Value |
| --- | --- |
| Quantize time | 206.5 s across the 6 quantized files. bf16 is the convert output, so its quantize time is 0. |
| Eval time | 62.7 s across the 7 files (median of three passes; 7.8 to 11.0 s per file). |
| Wall clock of the command | 542 s (9.0 min): 12 s setup (llama.cpp convert checkout and venv), 48 s download, 75 s bf16 convert, then quantize and eval. The other 138 s are the SHA-256 of each file (hashed twice, for the manifest and the scores), the tensor checks and seven server starts. |
| Eval-only reruns | 166.0 s and 166.2 s (the files are reused; hashes and server starts included). |
| One-time setup | Building llama.cpp b11669 with CUDA (only `llama-quantize` and `llama-server`) on Colab: 622.6 s (10.4 min), not part of the command. The prebuilt `ubuntu-cuda-12.8-x64` release binaries would remove this step. |
| Whole session | 0.50 h (04:08 to 04:38 UTC), from the first cell to the results, including the clone, the build, the command and the two eval reruns. |
| GPU use | Peak GPU memory 7.15 GB (the bf16 eval); mean utilisation 9.6% over the session. One request at a time leaves the A100 mostly idle. |
| File size | 6.60 GB at bf16, 2.04 GB at `Q4_K_M`, 1.26 GB at `Q2_K`. |
| Paid cost | About 3.3 Colab Pro compute units: the A100 at 6.5 units per hour (the rate Colab showed) for 0.50 h. At 9.99 USD for 100 units that is about 0.33 USD, taken from the Pro subscription; nothing paid on top. The command alone is 0.15 h, about 1.0 unit (0.10 USD). No rented GPU outside Colab. |

A T4 (about 1.2 units per hour) would cost less per hour. On this A100 the GPU is idle most of the time, so a T4 would
likely run the same flow for fewer units; it was not measured here.

The command (from the repository root):

```bash
python3 teams/12-quantization/scripts/quantize_eval.py \
  --model ibm-granite/granite-3.1-3b-a800m-instruct \
  --revision a02780686e08a03fe0d2679a293b5c74a90efa89 \
  --formats bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K \
  --limit 16 \
  --ngl 99 \
  --llama-bin <llama.cpp b11669 CUDA>/bin \
  --work <work> \
  --runs-csv <scratch>/runs.csv \
  --scores-out <scratch>/scores_pass1.json \
  --delete-hf
```

The two eval reruns are the same command with `--no-record` and `--scores-out <scratch>/scores_pass<N>.json`.
