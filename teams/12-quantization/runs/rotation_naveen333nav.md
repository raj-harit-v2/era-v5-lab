# Quantize and evaluate one checkpoint

Date: 16 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py` on `G12-Week3` at `d921b06`, the default
format list. The GGUF files stayed on the Colab machine and are not in this pull request. `runs/runs.csv` was not
changed: the script wrote its rows and its SHA-256 manifest to a scratch folder outside the repo, and the tables below
come from them.

This is a stand-in checkpoint, not dry run 1 evidence. It is the first rotation run on an MoE model, so it is the first
one where the router check has a router to check.

## Checkpoint

| Field | Value |
| --- | --- |
| Model | `ibm-granite/granite-3.1-1b-a400m-base` |
| Revision | `408b6e90baab8cf24f4aa9f8e19703ffa0a53b29` |
| Licence | Apache-2.0 |
| Architecture | `GraniteMoeForCausalLM` (llama.cpp `granitemoe`): 24 layers, width 1,024, 32 experts with top-8, tied embeddings, 1.33 B weights |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp b11669 (`620d222`), CPU (`-ngl 0`) |
| Machine | Google Colab CPU runtime: Intel Xeon @ 2.20GHz, 2 cores, 13.6 GB RAM, Linux 6.6.159+ |

Why this model: `docs/unsupported_parts.md` part 2 exports our model as Granite MoE Shared, which llama.cpp runs as
the same `granitemoe` architecture. This run shows that the stock b11669 converter, `llama-quantize` and
`llama-server` handle `granitemoe` from end to end.

Router type: `F32` in all 7 files. The converter writes the 24 router tensors (`ffn_gate_inp`, 1,024 x 32 each) as F32,
and `llama-quantize` leaves them so. Output weights: tied to the token embeddings, `tied:BF16` for bf16 and
`tied:Q8_0` for every quantized file. The converter also wrote Granite's four multipliers into the GGUF
(`attention_scale` 0.015625, `embedding_scale` 12.0, `residual_scale` 0.22, `logits_scale` 6.0). Section 9.5 of
`unsupported_parts.md` relies on the converter copying `attention_multiplier` this way.

## Eval

The script's stand-in set, seed 0: standin-v0 (mmlu100+gsm8k100, seed 0), then a seeded sample of 16 items
(`--limit 16`): 8 MMLU (mcq) and 8 GSM8K (numeric), few-shot completion prompts. No item text is stored here. This is
not the full G9 eval-mini set. One score is the share of the 16 sampled items answered correctly.

| Format | Size | Bits per weight | Score | By kind | Quantize | Eval | Tokens per second | Router | Output | sha256 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| bf16 | 2.67 GB | 16.0 | 0.3125 | mcq 0.375, numeric 0.25 | 0.0 s | 202.3 s | 7.8 | F32 | tied:BF16 | `0a912d7099a78bb6ea70a6027f514594c63625af3331b6ee9752f4bbff081b57` |
| Q8_0 | 1.42 GB | 8.51 | 0.3125 | mcq 0.375, numeric 0.25 | 16.7 s | 119.2 s | 13.8 | F32 | tied:Q8_0 | `09cefd586b403532fef1fb34521b4cd40b82b3901408f7366f6660527a2da9f9` |
| Q6_K | 1.11 GB | 6.65 | 0.25 | mcq 0.125, numeric 0.375 | 64.3 s | 127.9 s | 14.5 | F32 | tied:Q8_0 | `bd40f364327a2d3c0916c12714915f75da5784bdcfaabf96c0122cd9c4b7f90a` |
| Q5_K_M | 0.97 GB | 5.8 | 0.3125 | mcq 0.25, numeric 0.375 | 132.7 s | 134.3 s | 14.3 | F32 | tied:Q8_0 | `b88edeacc259a9f8c1dff3cc4eabdb58e424d624291725726cdfc8af6cb3e0d8` |
| Q4_K_M | 0.83 GB | 4.99 | 0.1875 | mcq 0.375, numeric 0.0 | 155.1 s | 104.4 s | 16.9 | F32 | tied:Q8_0 | `471c8269852cbdd39df0168a32feec81ef2a1818e0e9fc8247b245608cd4e38f` |
| Q3_K_M | 0.67 GB | 4.02 | 0.25 | mcq 0.375, numeric 0.125 | 85.9 s | 189.5 s | 16.2 | F32 | tied:Q8_0 | `8d24d70c6e939882669608ee5b35461ee5deb0ae82d11dfd1ea5694db906e5fe` |
| Q2_K | 0.52 GB | 3.14 | 0.25 | mcq 0.5, numeric 0.0 | 98.2 s | 71.0 s | 18.1 | F32 | tied:Q8_0 | `066da06bb300d41120f207b1ec9a07a5c9fad087d5dca7a369f5be64267d35dc` |

## What it shows

- **The router rule held** in every file: `F32`. On the two dense rotation runs (#13, #18) the router column is `-`.
- **No drop can be read from 16 items.** bf16 answers 5 of 16. Q8_0 and Q5_K_M also answer 5, Q6_K, Q3_K_M and Q2_K
  answer 4, and Q4_K_M answers 3. One item is 0.0625, so all of these are within noise.
- **This base model is weak on the sample.** At bf16 it gets 3 of 8 MMLU items (guessing among four options gives 2 of
  8 on average) and 2 of 8 GSM8K items. So the sample cannot show the Q2_K break seen on Qwen2.5-1.5B (#18) and OLMoE.
  Q4_K_M and Q2_K get no GSM8K item right, against 2 of 8 at bf16. On 8 items that is not evidence of a drop.
- **Bits per weight are close to the format's nominal width:** `Q4_K_M` is 4.99 here, 5.39 on Qwen2.5-1.5B (#18) and
  6.40 on Qwen2.5-0.5B (#13). The tied embedding kept at Q8_0 is 50.3 M of 1.33 B weights here (3.8%), so it lifts the
  average little. The F32 router adds 0.79 M weights (0.06%).
- **The MoE is fast for its size.** On the same kind of Colab 2-core CPU as #18, generation runs at 7.8 tokens per
  second at bf16 and 16.9 at `Q4_K_M`, against 2.4 and 6.2 for Qwen2.5-1.5B. This model has 1.33 B weights, but each
  token uses only 8 of its 32 experts, so it reads fewer weights per token.
- `Q4_K_M` is 3.2x smaller than bf16 (0.83 GB against 2.67 GB) and generates 2.2x faster on this CPU.

## Time and cost

| What | Value |
| --- | --- |
| Quantize time | 552.9 s across the 6 quantized files. bf16 is the convert output, so its quantize time is 0. |
| Eval time | 948.6 s across the 7 files. |
| Wall clock of the command | 1,690 s (28.2 min), including the download (34 s), the convert venv and the bf16 convert. |
| One-time setup | Building llama.cpp b11669 (CPU, only `llama-quantize` and `llama-server`) on Colab: 14.4 min (not part of the command). |
| Whole session | 0.9 h, from the first cell to the results, including the clone, the build and the command. |
| File size | 2.67 GB at bf16, 0.83 GB at `Q4_K_M`, 0.52 GB at `Q2_K`. |
| Paid cost | About 0.07 Colab Pro compute units: a CPU runtime at 0.08 units per hour (the rate Colab showed) for 0.9 h. No rented GPU. |

The commands (from the repository root):

```bash
git clone --depth 1 --branch b11669 https://github.com/ggml-org/llama.cpp <llama.cpp b11669>
cmake -S <llama.cpp b11669> -B <llama.cpp b11669>/build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
cmake --build <llama.cpp b11669>/build -j 2 --target llama-quantize llama-server

python3 teams/12-quantization/scripts/quantize_eval.py \
  --model ibm-granite/granite-3.1-1b-a400m-base \
  --revision 408b6e90baab8cf24f4aa9f8e19703ffa0a53b29 \
  --formats bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K \
  --limit 16 \
  --ngl 0 \
  --llama-bin <llama.cpp b11669>/build/bin \
  --work <work> \
  --runs-csv <scratch>/runs.csv
```
