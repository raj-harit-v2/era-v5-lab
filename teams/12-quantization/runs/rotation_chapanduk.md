# Quantize and evaluate one checkpoint

Date: 16 Nov 2026. Flow: `teams/12-quantization/scripts/quantize_eval.py` at `G12-Week3` `a6f14e1`, the default format
list. The GGUF files stay in the local cache and are not in this pull request. `runs/runs.csv` was not changed: the
script wrote its rows to a scratch file outside the repo (`--runs-csv`), and the tables below come from it.

This is an open-source stand-in checkpoint, as the lead asked for the rotation (refer #18), not dry run 1 evidence.
It is the largest model in the rotation so far (#13: 0.5B, #18: 1.5B) and the first one run on a GPU (Apple Metal).

## Checkpoint

| Field | Value |
| --- | --- |
| Model | `unsloth/Llama-3.2-3B-Instruct` (ungated mirror of `meta-llama/Llama-3.2-3B-Instruct`) |
| Revision | `006f5dcd1393c3add266de40994ba96225e9689d` |
| Licence | Llama 3.2 Community License |
| Formats | bf16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K |
| Runtime | llama.cpp b11669 (620d222), built from source with Metal, all layers on the GPU (`--ngl 99`) |
| Machine | Apple M4 Max, 64 GB unified memory, macOS 26.6 |

Router type: `-` (dense model, no router tensor). Output weights: `tied:BF16` for bf16, `tied:Q8_0` for every quantized
file. The script checks the output layer stays at 8 bits or more.

## Eval

The script's stand-in set: standin-v0 (mmlu100+gsm8k100, seed 0), **all 200 items** (no `--limit`; #13 and #18 used a
16-item sample). Chat prompts (`--prompt-mode auto` picked chat for this instruct model), context 4,096. No item text
is stored here. This is not the full G9 eval-mini set. One score is the share of the 200 items answered correctly;
its standard error is about ±3.2 points (±5 points for each kind of 100 items).

| Format | Size | Bits per weight | Score | By kind | Quantize | Eval | Tokens per second | Output | sha256 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| bf16 | 6.43 GB | 16.0 | 0.700 | mcq 0.55, numeric 0.85 | 0.0 s | 472.7 s | 55.9 | tied:BF16 | `85aed041a654bbd2dcb1230ec8f7dd3b3ee3fa3c7907b748eddf8710887fa9b3` |
| Q8_0 | 3.42 GB | 8.51 | 0.685 | mcq 0.54, numeric 0.83 | 3.6 s | 332.5 s | 85.7 | tied:Q8_0 | `4436d80c28270d0fe28d7eb28ec73dfac08e5153857ac3d45bde5bf10b818f84` |
| Q6_K | 2.74 GB | 6.81 | 0.695 | mcq 0.55, numeric 0.84 | 7.5 s | 267.3 s | 99.2 | tied:Q8_0 | `55b6eb003a623b66185df80b7f57ea83c897d2b08d48727892b9bba7b4c1cfae` |
| Q5_K_M | 2.42 GB | 6.01 | 0.710 | mcq 0.58, numeric 0.84 | 9.9 s | 279.6 s | 102.2 | tied:Q8_0 | `2207bdd94114016a255194e4ef096aa4c692ffb186edbb1ce854bee92e2bc462` |
| Q4_K_M | 2.11 GB | 5.26 | 0.710 | mcq 0.58, numeric 0.84 | 10.4 s | 231.4 s | 124.4 | tied:Q8_0 | `6047bdac2229e364719bad2a8f3ba8329d9e3827cd9942a2960badfe27917ac0` |
| Q3_K_M | 1.78 GB | 4.43 | 0.655 | mcq 0.54, numeric 0.77 | 7.2 s | 275.7 s | 97.5 | tied:Q8_0 | `26353cba8b6c0b15acb9fbf513e7988256aeb2dff7c566d3982c099d993e484a` |
| Q2_K | 1.46 GB | 3.63 | 0.515 | mcq 0.45, numeric 0.58 | 7.8 s | 238.2 s | 123.4 | tied:Q8_0 | `c809064ebb108dff9034d1e848fd1b8b7d24582c01185b52ca3b0592a90d61b2` |

## What it shows

- **Q8_0 down to Q4_K_M score the same as bf16** (0.685 to 0.710 against 0.700): every difference is under half a
  standard error.
- **Q3_K_M is the first to slip** (−4.5 points, numeric −8), about 1.4 standard errors: a likely but unconfirmed drop.
  The stand-in records no per-item results, so there is no paired test here.
- **Q2_K breaks**: −18.5 points (numeric 0.85 → 0.58), about 6 standard errors. This matches #18 (Qwen2.5-1.5B) and the
  team's OLMoE result.
- **`Q4_K_M` is the sweet spot**: 3.05× smaller than bf16 (2.11 GB against 6.43 GB), 2.2× faster generation, no loss.
  The G9 eval-mini run of the same model and files (`eval_mini/results/llama32_3b/`, #405) agrees: Q4_K_M −0.07 points,
  no task significant.
- **Speed follows size until Q4_K_M, then stops.** Generation is memory-bound, so tokens per second rise from 55.9
  (bf16) to 124.4 (Q4_K_M). Q3_K_M is slower again (97.5), probably because its 3-bit blocks cost more to unpack on
  Metal than the memory they save (not profiled). Q2_K is back at Q4_K_M's speed with a broken model.
- **Bits per weight** are close to the nominal width (Q4_K_M 5.26): the tied output layer kept at Q8_0 is 12% of this
  model's weights (#18: about 15%, #13: about 28%).
- **Eval time falls with size too**: bf16 took 472.7 s, Q4_K_M 231.4 s. The GSM8K answers are generated, so they
  dominate the eval time.

## Time and cost

| What | Value |
| --- | --- |
| Quantize time | 46.4 s across the 6 quantized files. bf16 is the convert output, so its quantize time is 0. |
| Eval time | 2,097.4 s (35.0 min) across the 7 files. |
| Wall clock of the command | **2,229 s (37.2 min)**: 36 s of setup (llama.cpp checkout, converter venv, stand-in set), then quantize and eval. |
| Download and convert | Not in the 37.2 min: the bf16 GGUF was already in the cache from the eval-mini run of 12 Nov (#405), the same revision and the same b11669 converter. Then: download 1,354 s (6.4 GB at about 5 MB/s), convert 31 s. **From an empty cache: about 60 min.** |
| One-time setup | Building llama.cpp b11669 with Metal, on 12 Nov (not timed; not part of the command). |
| Peak memory | 8.4 GB resident. |
| File size | 6.43 GB at bf16, 2.11 GB at `Q4_K_M`, 1.46 GB at `Q2_K`; 20.4 GB for all seven. |
| Paid cost | **None.** Own machine, no cloud instance, no rented GPU. In Team 07's unit (ADR 0004, `metrics/prices.yaml`): 0.62 machine-hours on one Apple M4 Max. |
| Electricity (estimate) | About 0.06 kWh: 37.2 min at about 100 W for the whole machine under GPU load. **Not measured** (a typical figure for this machine, not a `powermetrics` reading). At your own tariff: kWh × price, e.g. about ₹0.5 at ₹8/kWh. |

The command (from the repository root):

```bash
python3 teams/12-quantization/scripts/quantize_eval.py \
  --model unsloth/Llama-3.2-3B-Instruct \
  --revision 006f5dcd1393c3add266de40994ba96225e9689d \
  --formats bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K \
  --work <work> \
  --runs-csv <scratch>/runs.csv \
  --llama-bin <llama.cpp b11669>/build/bin \
  --ngl 99
```
