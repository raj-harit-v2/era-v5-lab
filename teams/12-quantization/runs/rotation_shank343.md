# Quantize and evaluate one checkpoint

Date: 16 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py` at class `main` `917fafb`, the default format list. The GGUF files stayed on the Colab machine and are not in this pull request. `runs/runs.csv` was not changed: the script wrote its rows to a scratch file outside the repo, and the tables below come from it.

This is a stand-in checkpoint, not dry run 1 evidence: the dry run 1 checkpoint path (#14) was not merged when this ran.

## Checkpoint

| Field | Value |
| --- | --- |
| Model | `Qwen/Qwen2.5-1.5B` |
| Revision | `8faed761d45a263340a0528343f099c05c9a4323` |
| Licence | Apache-2.0 |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp b11669 (620d222), CPU (`-ngl 0`) |
| Machine | x86_64, Linux 6.6.159+, CPU (Google Colab, free standard CPU runtime) |

Router type: `-` (dense model, no router tensor). Output weights: `tied:BF16` for bf16; `tied:Q8_0` for Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K. The script checks the output layer stays at 8 bits or more.

## Eval

The script's stand-in set, seed 0: standin-v0 (mmlu100+gsm8k100, seed 0), then a seeded sample of 16 items (`--limit 16`). No item text is stored here. This is not the full G9 eval-mini set. One score is the share of the sampled items answered correctly.

| Format | Size | Bits per weight | Score | By kind | Quantize | Eval | Tokens per second | Output | sha256 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| bf16 | 3.09 GB | 16.0 | 0.6875 | mcq 0.625, numeric 0.75 | 0.0 s | 579.2 s | 2.4 | tied:BF16 | `5d8d53d3fca058dcd2fd6f6c4efedf57a80a0117fa91f171f2872fa63c1e6116` |
| Q8_0 | 1.65 GB | 8.52 | 0.6875 | mcq 0.625, numeric 0.75 | 31.4 s | 395.5 s | 4.2 | tied:Q8_0 | `b81b0111e3a554482397b3c9ec9f80675ed097579ff2b660a545711bcfce4ea4` |
| Q6_K | 1.33 GB | 6.87 | 0.5625 | mcq 0.5, numeric 0.625 | 95.8 s | 329.8 s | 4.7 | tied:Q8_0 | `6ad4a47b4172e091e37c3f79cd9de94f9b54883bff2fc4a0ebceac399e62f3d8` |
| Q5_K_M | 1.18 GB | 6.11 | 0.625 | mcq 0.5, numeric 0.75 | 165.3 s | 350.7 s | 4.7 | tied:Q8_0 | `2c1dedddb5140adf24cbd55f817b21ab97802078cfeb400e25434876d8a8498c` |
| Q4_K_M | 1.04 GB | 5.39 | 0.625 | mcq 0.625, numeric 0.625 | 220.8 s | 293.2 s | 6.2 | tied:Q8_0 | `8b3567d6a4dbb99c47358c1475b5b8fbb126d92f54b19e2886518075fab3bd96` |
| Q3_K_M | 0.88 GB | 4.55 | 0.6875 | mcq 0.625, numeric 0.75 | 103.3 s | 300.9 s | 5.3 | tied:Q8_0 | `e60e3e7e4f62b2e359af9876ec0a4be0bbcf47bf8c4631a5dbc3d76637221514` |
| Q2_K | 0.73 GB | 3.79 | 0.125 | mcq 0.25, numeric 0 | 133.0 s | 463.3 s | 5.8 | tied:Q8_0 | `f39d21cecbdb3f26922005719801e36d9b8756275aa654e5d91e7cf77ea48244` |

## What it shows

- Q8_0 down to Q3_K_M score in the same range as bf16 (0.5625 to 0.6875). On 16 items one item is 0.0625, so these
  differences are within noise.
- Q2_K breaks: 0.125, with no numeric item right. This matches the team's OLMoE finding that Q2_K breaks broadly.
- Bits per weight come closer to the nominal width than on Qwen2.5-0.5B (#13): `Q4_K_M` is 5.39 here and 6.40 there.
  The output layer, tied to the token embeddings and kept at Q8_0, is about 15% of this model's weights and about 28% of
  the 0.5B one, so it lifts the average less.
- `Q4_K_M` is 3.0x smaller than bf16 (1.04 GB against 3.09 GB) with no drop beyond noise on this sample.

Speeds and times are from a 2-core Colab CPU, so they are not comparable with #13, which ran on a desktop CPU.

## Time and cost

| What | Value |
| --- | --- |
| Quantize time | 749.6 s across the 6 quantized files. bf16 is the convert output, so its quantize time is 0. |
| Eval time | 2712.6 s across the 7 files. |
| Wall clock of the command | 3778 s (63.0 min), including the download, the bf16 convert and the convert venv. |
| One-time setup | Building llama.cpp b11669 (CPU) on Colab: 16.4 min (not part of the command). |
| File size | 3.09 GB at bf16, 1.04 GB at `Q4_K_M`, 0.73 GB at `Q2_K`. |
| Paid cost | None. Free Colab CPU runtime (1.33 h of session); no paid units, no rented GPU. |

The command (from the repository root):

```bash
python3 teams/12-quantization/scripts/quantize_eval.py \
  --model Qwen/Qwen2.5-1.5B \
  --revision 8faed761d45a263340a0528343f099c05c9a4323 \
  --formats bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K \
  --limit 16 \
  --ngl 0 \
  --llama-bin <llama.cpp b11669>/build/bin \
  --runs-csv <scratch>/runs.csv
```
