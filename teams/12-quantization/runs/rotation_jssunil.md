# G12 week 3 rotation — jssunil

**Status: R1 and R2 run, 18 Nov 2026, on one local RTX 5070 Ti.** Stand-in checkpoint (an open-source model, as the lead
answered in G12 on 16 Nov at 19:56). This is not dry run 1 or Gate 3 evidence. R1 runs the quantize-and-evaluate flow on
**one checkpoint** and R2 records its time and cost (G12 week 3 work order, §4). The flow on the dry run 1 checkpoint is
core task 5 (theschoolofai/era-v5-lab#508); this run does not duplicate it.

Logs, hashes, GPU samples and the two helper scripts: [evidence gist](https://gist.github.com/jssunil/44a6d60a6c37378865169a63cd90ed6a). No GGUF, prompt text or benchmark text
is in this pull request. `runs/runs.csv` and `quality/kl.csv` were not changed: both scripts wrote to scratch files, and
the tables below come from them.

## 1. Checkpoint and setup

| Field | Value |
|---|---|
| Model | `ibm-granite/granite-3.0-1b-a400m-base`, revision `d91cbed802d85eb1b32374623331f6ab2b37403a` (Apache-2.0) |
| Architecture | `GraniteMoeForCausalLM` → llama.cpp `granitemoe`; 24 layers, 32 experts with top-8, tied embeddings; vocabulary 49,152, pre-tokenizer `refact` |
| Why this one | Small MoE, so the router is checked on real router tensors, and it is the Granite MoE family our export targets. #19 ran the 3.1 sibling on a CPU and #23 the 3B-A800M on an A100; this run adds the drift measures (KL, top-1, BPB), the tokenizer round trip and the fixed-100 run, which those runs do not have |
| Runtime | llama.cpp b11669 (`620d2225cc436ab0b001e3200e590e3b286ef9ab`), built from source with CUDA 13.3 for compute capability 12.0 (`-DLLAMA_BUILD_NUMBER=11669`: a shallow clone reports build 1 otherwise, and the server's UI step then fails) |
| Machine | Intel Core Ultra 7 265K (20 cores), 60 GiB RAM, NVIDIA GeForce RTX 5070 Ti 16 GB (driver 595.99.02), Linux 7.0.0-43 |
| Scripts | `scripts/quantize_eval.py` and `quality/kl_eval.py` at `G12-Week3` `26968de`; `scripts/flow_fixed_prompts.py` at #508 head `bc2bd33` (the other two are the same file there) |

## 2. Checks before any number is read

| Check | Result |
|---|---|
| Input identity | GGUF sha256s match yesterday's Modal L40S run (`bf16` `97ae31d4…aad3`, `Q8_0` `91cdbf84…4985`, `Q4_K_M` `f8046be9…0814`): convert and quantize give the same bytes on two machines. All seven hashes are in the gist |
| Router and output tensors | Router (`ffn_gate_inp`) **F32 in all 7 files**; output tensor BF16 at bf16 and **Q8_0 in every quantized file** (Session 18 rule: router not quantized) |
| GPU execution | Peak GPU memory 3,178 MiB in the flow and 3,142 MiB in the KL pass, sampled every 0.5 s (idle 30 MiB); the model ran on the GPU, not on the CPU |
| Tokenizer round trip | **Passes.** Same token ids, HF `tokenizer.json` against the GGUF, on **all 20,400 lines** of `tokenizer/gguf_roundtrip.py`'s held-out text (English, 11 Indic languages, 5 others, the ZWJ/ZWNJ, NFD and old-chillu sets, Python lines and 100 whole files). The build's own `llama-tokenize` gives the same ids on every set, and b11669's decoder gives back the exact text. Section 6 explains 30 lines that only llama-cpp-python decodes wrongly |
| Export checks A1 / A3 | Do not apply: they check the G5 export path, and this is a public HF checkpoint |

## 3. R1 results: drift from bf16

Text: WikiText-2 test as pinned in `kl_eval.py`, 64 chunks × 512 tokens. llama-perplexity scores the second half of each
chunk: 16,320 tokens covering 56,491 UTF-8 bytes, the same tokens for every format. Every quantized file is compared
with the saved bf16 log-probabilities on each of those tokens.

| Format | Size | Bits/weight | KL mean | KL median | KL p99 | KL max | Same top-1 | PPL (± ) | PPL ratio | BPB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bf16 | 2.77 GB | 16.0 | — | — | — | — | 100 % | 7.146 ± 0.139 | 1.000 | 0.8196 |
| Q8_0 | 1.48 GB | 8.51 | 0.0032 | 0.0014 | 0.031 | 0.47 | 97.19 % | 7.149 ± 0.139 | 1.0026 | 0.8198 |
| Q6_K | 1.15 GB | 6.65 | 0.0090 | 0.0045 | 0.081 | 0.98 | 95.55 % | 7.183 ± 0.139 | 1.0074 | 0.8218 |
| Q5_K_M | 1.00 GB | 5.79 | 0.0220 | 0.0114 | 0.185 | 2.34 | 92.64 % | 7.271 ± 0.142 | 1.0199 | 0.8269 |
| **Q4_K_M** | 0.86 GB | 4.98 | **0.0650** | 0.0340 | 0.555 | 4.17 | **88.06 %** | 7.570 ± 0.148 | **1.0618** | 0.8437 |
| Q3_K_M | 0.69 GB | 3.99 | 0.2560 | 0.1291 | 2.44 | 13.1 | 78.11 % | 8.996 ± 0.178 | 1.2618 | 0.9156 |
| Q2_K | 0.54 GB | 3.12 | 1.9251 | 1.4854 | 8.12 | 17.6 | 41.06 % | 47.17 ± 1.10 | 6.6157 | 1.6062 |

KL is in nats per token. BPB = scored tokens × ln(PPL) ÷ ln 2 ÷ scored bytes; this text has 3.46 bytes per token.

### Fixed-100 prompts: output agreement with bf16

`flow_fixed_prompts.py --gguf-dir … --manifest teams/10-post-training/eval/effort_manifest.json` as the lead asked
(#478): manifest `d6190b2d…9226`, 55 slots from Team 10's pinned code_contests and hendrycks_math files, checked against
the manifest's sha256s, and the 45 unavailable slots (20 tool/agentic, 15 Indic, 10 general) filled from `fixed_100.jsonl`
(`da3f6851…4919`), the fill Rahul and Shubham agreed on #508. Greedy decoding, seed 0, at most 128 tokens. No Team 10
prompt or output text was written anywhere: only ids and sha256s.

| Format | Identical to bf16 | Same first token | Median tokens before the first difference | Mean shared prefix | Stopped / hit 128 |
|---|---:|---:|---:|---:|---:|
| bf16 | — | — | — | — | 27 / 73 |
| Q8_0 | **34 / 100** (G10 21/55, G12 13/45) | 100 / 100 | 53 | 0.54 | 21 / 79 |
| Q4_K_M | **4 / 100** (G10 2/55, G12 2/45) | 97 / 100 | 6 | 0.15 | 10 / 90 |

### Reference benchmark (reference only)

`quantize_eval.py`, its stand-in set `standin-v0` (100 MMLU + 100 GSM8K, seed 0, all 200 items), few-shot completion
prompts (base model), context 4,096. A 200-item score has a 95 % margin of about ±6.5 points.

| Format | Score | MMLU | GSM8K |
|---|---:|---:|---:|
| bf16 | 0.250 | 0.35 | 0.15 |
| Q8_0 | 0.265 | 0.34 | 0.19 |
| Q6_K | 0.255 | 0.31 | 0.20 |
| Q5_K_M | 0.210 | 0.29 | 0.13 |
| Q4_K_M | 0.215 | 0.30 | 0.13 |
| Q3_K_M | 0.165 | 0.29 | 0.04 |
| Q2_K | 0.125 | 0.21 | 0.04 |

## 4. What it shows

- **Q8_0 is close to lossless on this model.** PPL rises 0.26 %, the top-1 token is the same 97.2 % of the time, and BPB
  moves in the fourth decimal. On fixed-100 every first token is the same and outputs stay identical for a median of 53
  tokens. A third of the outputs (34/100) still differ somewhere within 128 greedy tokens: greedy decoding copies a
  near-tie at one position into every token after it, so "identical outputs" is a strict measure.
- **Q4_K_M is where this model starts to drift.** PPL ratio 1.062, top-1 agreement 88 %, KL p99 0.56. Greedy outputs
  share a median of only 6 tokens with bf16, and only 4 of 100 are identical. The benchmark cannot see this: 0.215
  against 0.250 is inside the ±6.5-point margin. Same pattern as the team's OLMoE row in `quality/kl.csv`, but about 2.8x
  the KL (OLMoE Q4_K_M: 0.0233 mean, 92.1 % top-1). Why this model drifts more was not measured here.
- **Q3_K_M degrades (PPL +26 %) and Q2_K breaks** (PPL 6.6x, top-1 41 %): the same order as #19 and #23, and as the
  team's OLMoE row.
- **The tail is the useful column.** KL max is 4.2 at Q4_K_M against 0.47 at Q8_0: rare tokens where the quantized model
  is far off. A mean of 0.065 hides them (Llama 3 report: benchmarks fine under FP8 while the model occasionally produced
  corrupted responses).
- **Speed on the GPU is flat across formats** (517 to 658 tokens/s, one request at a time): a 400 M-active model does
  not keep this GPU busy (mean utilisation 25 %), so smaller files do not decode much faster. On the CPU
  (llama-cpp-python, fixed-100) they do: 49 → 72 → 82 tokens/s for bf16 → Q8_0 → Q4_K_M.

**Basis:** Session 18: keep the router unquantised and compare formats on the same evaluation
[N `local:sessions/session_18_preference_alignment_and_inference_serving.md#0013`, `#0046`]. KL between the
full-precision and reduced-precision output distributions as a quantization error measure [P 2610.38277#0022].
Llama 3: benchmarks looked fine under FP8 while the model "occasionally produces corrupted responses"
[P 2407.21783#0136]. BPB does not depend on the tokenizer
[N `local:sessions/session_16_scaling_laws_and_compute_planning.md#0003`]. An "acceptable" KL threshold:
**Basis: none in index**; this report gives numbers and proposes no threshold.

## 5. R2: time and cost, measured per stage on this machine

Set-up (clone, build, downloads) is listed but kept out of the pipeline total. Times are wall clock.

| Stage | Seconds | Notes |
|---|---:|---|
| Set-up: llama.cpp b11669 CUDA build | 148 | 132 s (`llama-server`, `llama-quantize`, `llama-perplexity`, `llama-tokenize`) + 16 s rebuild with the build number; a prebuilt release would remove it |
| Set-up: converter checkout and venv | 21 | inside `quantize_eval.py` (git clone + uv) |
| Set-up: model download | 252 | 2.7 GB of safetensors from Hugging Face |
| Set-up: test-text downloads | 263 + 453 | tokenizer held-out text (streamed); Team 10's pinned parquet files for fixed-100 (4.6 GB, 31 files). A job with no network needs both as inputs |
| Convert to bf16 GGUF | ≤ 13 | includes building the 200-item stand-in set |
| Quantize, per format | 1.4 / 2.6 / 3.2 / 3.4 / 2.2 / 2.5 | Q8_0 / Q6_K / Q5_K_M / Q4_K_M / Q3_K_M / Q2_K, fresh files; 15.3 s for all six |
| Benchmark, per format (200 items, GPU) | 15.1 – 26.6 | 137 s for all seven; with server starts and hashing, `quantize_eval.py` after the download took 186 s |
| KL / PPL pass (16 k tokens, GPU) | 18 | all seven formats, including the bf16 base pass |
| Tokenizer round trip (20,400 lines, CPU) | 20 | |
| Fixed-100, per format (CPU) | 236 / 164 / 156 | bf16 / Q8_0 / Q4_K_M: llama-cpp-python 0.3.36 from PyPI has no CUDA, so this step ran on the CPU (20 cores) |
| **Pipeline total (excluding set-up)** | **≈ 790** | 186 + 18 + 20 + 560 + BPB (< 5 s); the CPU fixed-100 step is 71 % of it |
| Peak memory | GPU 3.18 GB; host RSS 3.4 GB | whole-device GPU sample every 0.5 s |
| Decode tokens/s, one request | GPU 517 / 593 / 650; CPU 49 / 72 / 82 | bf16 / Q8_0 / Q4_K_M |

**Cost: none paid (local machine).** Measured GPU energy (power draw × time, 0.5 s samples): 6.9 Wh for the flow and
0.5 Wh for the KL pass; no electricity rate is assumed. Yesterday's Modal L40S smoke (91.75 s including download) is the
only cloud use for this PR; its billed amount is not taken from wall time. On a rented GPU, the step to move is
fixed-100: with a CUDA build of llama-cpp-python it would take seconds instead of 9 minutes. Serving cost per million
tokens = price per hour ÷ (tokens/s × 3,600) × 10⁶
[N `local:sessions/session_18_preference_alignment_and_inference_serving.md#0013`, `#0045`]. Reporting time alone
when there is no billed rate: **Basis: none in index** (team practice in #13).

## 6. Things the team may want to know (tools, not this model)

1. **llama-cpp-python 0.3.36 cuts vocabulary pieces longer than 32 bytes when it decodes.** `Llama.detokenize` uses a
   32-byte buffer per token (`llama_cpp/_internals.py`, `token_to_piece`). Granite's vocabulary has 210 such tokens (long
   space and hyphen runs). The 30 held-out lines that contain one — 26 Python files, 2 code lines, 2 Malayalam lines
   with long dash runs — and only those decode short through llama-cpp-python. b11669's own `/detokenize` gives back the exact text on
   all 30 (and the same ids). This touches `tokenizer/gguf_roundtrip.py` (its `gguf_text_err` count) and
   `flow_fixed_prompts.py` (its `text` and `text_sha256` fields; the agreement numbers use token ids and are not
   affected) on any tokenizer with long tokens. The p1536 and C3 tokenizers may have none; worth a check.
2. `quality/kl_eval.py` writes `tokens_scored = chunks × (ctx − ctx/2)` = 16,384; llama-perplexity scores
   ctx − ctx/2 − 1 tokens per chunk (`perplexity.cpp`, `count += n_ctx - first - 1`), so 16,320. It does not change any
   KL or PPL value, only that column, and any BPB derived from it.

## 7. Checklist

- [x] Read the work order, #13, #14, #18, #478 (and the lead's comment there), #508, G10's `effort_manifest.json` and the team's `kl_eval.py`.
- [x] Lead confirms the checkpoint: open-source model (16 Nov 19:56).
- [x] llama.cpp converts the chosen model (Modal smoke 17 Nov; same hashes locally 18 Nov).
- [x] Inputs and hashes pinned; checks in §2 run.
- [x] §3 and §5 filled from this run's own logs; logs in the gist.
- [ ] Take the PR out of draft and link it in the G12 group.
