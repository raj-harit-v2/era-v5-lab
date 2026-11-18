# Quantize and evaluate one checkpoint

Date: 15 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py`, the default format list. The GGUF files stay in the local cache and are not in this pull request. `runs/runs.csv` was not changed.

## Checkpoint

| Field | Value |
| --- | --- |
| Model | `Qwen/Qwen2.5-0.5B` |
| Revision | `060db6499f32faf8b98477b0a26969ef7d8b9987` |
| Licence | Apache-2.0 |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp `b11669` (`620d222`), CPU (`-ngl 0`) |
| Machine | x86_64, Linux. An RTX 5070 Ti is in the machine and was not used. |

This checkpoint is dense, so there is no router tensor. The output weights stay tied to the token embeddings. bf16 keeps them at BF16. Every quantized file keeps them at Q8_0, which is the floor the script checks.

## Eval

The script's stand-in set, seed 0: 100 MMLU items and 100 GSM8K items, then a seeded sample of 16 items (`--limit 16`). No item text is stored here. This is not the full G9 eval-mini set. One score is the unweighted mean of the mcq score and the numeric score.

| Format | Size | Bits per weight | Score | By kind | Quantize | Eval | Tokens per second | Output | sha256 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| bf16 | 0.99 GB | 16.0 | 0.4375 | mcq 0.25, numeric 0.625 | 0.0 s | 28.8 s | 30.5 | BF16 | `bf1fe5740a1bc69bd32c6ee48d776b7c5c9d9564e4175830a1a56bd8e7a1ddba` |
| Q8_0 | 0.53 GB | 8.55 | 0.4375 | mcq 0.25, numeric 0.625 | 1.5 s | 21.5 s | 52.4 | Q8_0 | `472028bd7b7a6d37f85d83417f24b4edc96969a41ecfacacdebdf682554b7e56` |
| Q6_K | 0.51 GB | 8.14 | 0.4375 | mcq 0.25, numeric 0.625 | 1.9 s | 20.0 s | 56.5 | Q8_0 | `794e021b5c5f7ba72f2fb64d9aaa536f7317c2966aa2783095167b9655836a8c` |
| Q5_K_M | 0.42 GB | 6.76 | 0.375 | mcq 0.375, numeric 0.375 | 2.3 s | 19.4 s | 61.9 | Q8_0 | `316a38d4a089938dcd8607be82e88620005b989ced6e5e979127ceb898d80d65` |
| Q4_K_M | 0.40 GB | 6.40 | 0.4375 | mcq 0.375, numeric 0.5 | 2.0 s | 16.1 s | 60.8 | Q8_0 | `5c15abc6f76d998b658a0c4c7b99570245dc2d4158844721c674a92ba72816d3` |
| Q3_K_M | 0.36 GB | 5.72 | 0.375 | mcq 0.375, numeric 0.375 | 2.7 s | 14.5 s | 82.5 | Q8_0 | `999b6bc7dcfccdf395a6cfc24945c5b338a1318af38dd02eea4c46c16177dabe` |
| Q2_K | 0.34 GB | 5.45 | 0.1875 | mcq 0.25, numeric 0.125 | 1.2 s | 23.9 s | 80.9 | Q8_0 | `33cfbbfcb9e0d2bfe8c741015b770e24d81d065f9ae4f5a970deb3c01ad160d1` |

## Time and cost

| What | Value |
| --- | --- |
| Quantize time | 11.6 s across the six quantized files. bf16 is the convert output, so its quantize time is 0. |
| Eval time | 144.2 s across the seven files. |
| Wall clock of the ladder command | 197 s. The checkpoint and the bf16 file were already in the cache from the earlier convert. |
| File size | 0.99 GB at bf16, 0.40 GB at `Q4_K_M`, 0.34 GB at `Q2_K`. |
| Paid cost | None. No cloud instance and no rented GPU. |

The command:

```bash
python3 teams/12-quantization/scripts/quantize_eval.py \
  --model Qwen/Qwen2.5-0.5B \
  --revision 060db6499f32faf8b98477b0a26969ef7d8b9987 \
  --formats bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K \
  --limit 16 \
  --ngl 0 \
  --no-record
```
