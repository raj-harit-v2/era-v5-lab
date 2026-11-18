# Serving plan on vLLM (G12, week 3)

**Status:** 15 Nov 2026, draft for Gate 3. Follows Session 18 (inference serving: KV cache, paged attention, continuous
batching, prefix caching, chunked prefill, FP8, expert parallel). It covers the four serving questions for our model:
the KV-cache budget, prefix caching, FP8 weights and FP8 KV cache against BF16, and expert parallel. Section 7 is the
"serve one checkpoint" task on the dry-run checkpoint.

**Inputs:**
- Gate 2 config v1 (`teams/05-architecture/configs/config_v1.yaml`, `decisions.md`): 16 routed experts + 1 shared,
  top-2, v0 attention.
- The T1/T2/T3 test shapes (`teams/05-architecture/configs/arms/t{1,2,3}.yaml`).
- The export target from [`unsupported_parts.md`](unsupported_parts.md) part 2: Granite MoE Shared,
  `GraniteMoeSharedForCausalLM` in vLLM.
- G10's chat template hand-off (`teams/10-post-training/chat-format/team12_chat_template_handoff.md`), with effort
  levels 1k, 4k, 16k and 64k.
- Our vLLM runs in [`gpu_path/`](../gpu_path/).

**Pinned runtime:** vLLM **0.33.0**, the version in `gpu_path/results/environment.json`. G10's effort probe used 0.32.0
on one H100 80GB. Flag and metric names below are from the vLLM V1 engine. Rows marked *check on 0.33.0* have not been
run on the pinned version.

**Model sizes are still open.** Gate 2 left `n_layer`, `d_model`, `n_head`, `d_ff` and `seq_len` empty. Every number
below is computed for the T1/T2/T3 test shapes, which already have the Gate 2 expert layout and 2 KV heads. The
formulas in section 2 give the production numbers once TSAI fills the sizes.

## Summary

| Question | Decision for the first served checkpoint | Why |
|---|---|---|
| KV-cache budget | `--gpu-memory-utilization 0.90`, `--max-model-len` = `data.seq_len`, `--max-num-seqs` set explicitly, `--block-size 16`. Record vLLM's reported KV-cache tokens for every run | At 2 KV heads × head dim 64, KV is 3–5 KiB per token (section 2). On an H100 the weights are < 1 GB, and KV holds 12–21 M tokens. The real limits are long effort contexts on small GPUs, and the 131k-vocab logits |
| Prefix caching | **On** (V1 default) for RL rollouts, generation evals and chat. Reset it after every RL weight update | RL sends the same prompt G times. GSM8K 5-shot repeats the same 5 shots. Every chat starts with the same system turn (section 3) |
| FP8 weights | Measure, do not ship yet. llm-compressor `FP8_DYNAMIC` with `lm_head` and the router kept in BF16, scored against vLLM BF16 with the existing drop limits | Weights are < 1 GB at test sizes, so FP8 weights buy speed (FP8 tensor cores, half the expert bytes per decode step), not memory. Needs compute capability ≥ 8.9 for W8A8 (section 4) |
| FP8 KV cache | Measure first. Ship if it passes the drop limits and the long-context check | It doubles the KV tokens. That matters for 16k/64k effort rollouts, which is where memory runs out (section 4) |
| Expert parallel | **Off** for eval and RL at test sizes. Run one full replica per GPU and scale with data parallel. Turn on `--enable-expert-parallel` with DP attention only when the weights stop fitting one GPU | 16 experts × small FFNs fit one GPU many times over. EP adds an all-to-all on every MoE layer. With 2 KV heads, TP > 2 duplicates KV (section 5) |

## 1. Who the server is for

| Job | Owner | What it needs from vLLM | Shape of the load |
|---|---|---|---|
| Checkpoint eval during training | G9 | Fast and rare. It must not slow the main run (Session 18), so it runs on the `eval` partition, never the training nodes | loglikelihood (prompt logprobs) for ARC/HellaSwag/MMLU, generation for GSM8K and code |
| RL and SFT rollouts | G10 | High throughput. The same prompt sampled G times at different temperatures. Weights change between rounds | long generations; 16k/64k effort means very long decodes |
| Demo endpoint | G12 / G11 | OpenAI chat API, G10 chat template, reasoning and tool-call parsing | interactive; time to first token and time per token matter |

The rule from `gpu_path/` holds: **a quantized score is compared only with the BF16 score from the same runtime on the
same items.** FP8 rows are compared with vLLM BF16, never with llama.cpp rows.

## 2. KV-cache budget

### 2.1 Bytes per token

```
KV bytes per token = 2 (K and V) × n_layer × n_kv_head × head_dim × bytes per element
                     bytes per element: 2 for BF16, 1 for FP8
```

Our attention is GQA with no MLA and no sliding window (v0 attention), so every layer stores full K and V for every
token. The arm `attn-2` (window 128 on 6 of 8 layers) would cut this by about 4× on those layers. It is not adopted.

| Shape | n_layer | n_kv_head × head_dim | BF16 per token | FP8 per token | One 2,048-token sequence (BF16) | One 64k-effort sequence, 66,560 tokens (BF16) |
|---|---|---|---|---|---|---|
| T1 | 6 | 2 × 64 | 3 KiB | 1.5 KiB | 6 MiB | 195 MiB |
| T2 | 8 | 2 × 64 | 4 KiB | 2 KiB | 8 MiB | 260 MiB |
| T3 | 10 | 2 × 64 | 5 KiB | 2.5 KiB | 10 MiB | 325 MiB |
| OLMoE-1B-7B (our week-1 model, MHA) | 16 | 16 × 128 | 128 KiB | 64 KiB | 256 MiB | 8.1 GiB |
| Qwen3-30B-A3B (GQA) | 48 | 4 × 128 | 96 KiB | 48 KiB | 192 MiB | 6.1 GiB |
| Session 18 example, "30B" | 48 | 16 × 128 | 384 KiB | 192 KiB | 768 MiB | 24.4 GiB |

The Session 18 numbers (384 KiB per token, 12 GB at 32k, 48 GB at 128k) match a 48-layer model with 16 KV heads of
width 128. Qwen3-30B-A3B has 4 KV heads and needs a quarter of that. The production model should keep few KV heads.
`attn-1` (MQA, 1 KV head) halves KV again, but `n_kv_head` interacts with tensor parallel (section 5.3).

The 64k column is the effort budget only. The T2/T3 test shapes train at `block_size` 2048, so they cannot serve it.
The column shows the cost if the production `seq_len` allows 64k effort.

### 2.2 Weights against KV on one GPU

Parameter counts below are from the T-shape YAMLs with KE2 folded to a 131,072 × `d_model` table (part 1 §1) and the
untied head. FP8 keeps `lm_head` and the router in BF16 (section 4).

| Shape | Parameters | Experts' share | BF16 weights | FP8 weights |
|---|---|---|---|---|
| T1 | 89.5 M | 21% | 0.18 GB | 0.12 GB |
| T2 | 299.9 M | 50% | 0.60 GB | 0.37 GB |
| T3 | 470.1 M | 59% | 0.94 GB | 0.55 GB |

At these sizes the 131k vocabulary (embedding + head) is a large part of the weights. The weights are not where the
memory goes.

**What vLLM gives to KV.** At start-up vLLM profiles one forward pass at `--max-num-batched-tokens`. KV cache gets
`gpu_memory_utilization × GPU memory − weights − peak activations − CUDA graph memory`. vLLM logs the result as
"GPU KV cache size: N tokens" and "Maximum concurrency for `max_model_len` tokens per request". **Record both lines
for every run.** They are the measured budget. The table below is an estimate with a guessed reserve (6 GB on H100,
3 GB on T4) for activations and graphs.

| GPU | Shape | KV tokens (BF16) | Concurrent 2k sequences | Concurrent 66k sequences, BF16 / FP8 KV |
|---|---|---|---|---|
| H100 80GB, util 0.90 | T3 | ≈ 12.7 M | ≈ 6,200 | ≈ 190 / 380 |
| T4 15GB, util 0.90 | T3 | ≈ 1.9 M | ≈ 900 | ≈ 28 / no FP8 KV on T4 (section 4.2) |

On the H100, KV is not the limit for 2k-token evals. The batch limit is `--max-num-seqs` and compute. KV only gets
tight with 64k-effort RL rollouts, or on the small `eval` GPUs.

### 2.3 Rules

1. **Set `--max-model-len` to the trained `seq_len`**, not the default from `config.json`
   (`max_position_embeddings`). vLLM refuses to start if one full-length sequence does not fit in KV. A longer
   `max_model_len` than training also lets requests run past the positions RoPE saw in training.
2. **Set `--max-num-seqs` explicitly** (start at 256 for eval, 512–1024 for RL on H100) and raise it until
   `vllm:kv_cache_usage_perc` stays below about 90% with no preemptions. With 5 KiB per token, the default leaves
   most of the KV pool unused.
3. **Watch preemptions.** When KV runs out, V1 preempts a running sequence and recomputes it later.
   `vllm:num_preemptions_total` > 0 during a 64k-effort RL round means: lower `--max-num-seqs`, turn on FP8 KV, or add
   a replica.
4. **Budget the logits, not only KV.** The vocabulary is 131,072. With prompt logprobs (lm_eval loglikelihood), vLLM
   computes logits for every prompt token in the batch: 8,192 tokens × 131,072 × 4 bytes = 4 GiB in fp32. On a T4 that
   is a quarter of the card. Keep `--max-num-batched-tokens` at 2,048–4,096 on T4 for loglikelihood runs. Check that
   the start-up profile covers the logprobs path (*check on 0.33.0*). If it does not, lower
   `--gpu-memory-utilization`.
5. **Block size 16** (vLLM default, paged attention). Leave it. Prefix caching shares only full 16-token blocks
   (section 3).
6. **Chunked prefill is on in V1.** `--max-num-batched-tokens` sets the trade-off: larger means faster prefill and
   higher time per token for running decodes. Demo: 2,048. Eval and RL: 8,192 on H100, 2,048–4,096 on T4.

## 3. Prefix caching

vLLM hashes each full 16-token KV block by its tokens and everything before it. A new request that starts with the
same tokens reuses those blocks and skips their prefill. In V1 it is on by default (`--enable-prefix-caching`). Cached
blocks are evicted LRU when KV is needed.

### 3.1 Where it helps us

| Job | Shared prefix | Expected gain |
|---|---|---|
| G10 GRPO rollouts | the whole prompt, sampled G times (group of 8 in Session 18) | prefill once instead of G times. Send the group as one request with `n = G` (`SamplingParams(n=8, …)`), or as G requests back to back. Both hit the cache |
| G10 SFT eval and effort suite | the system turn `Reasoning effort: {1k,4k,16k,64k}` and the fixed prompts | each prompt × 4 effort levels shares everything up to the effort line |
| G9 GSM8K 5-shot (generation) | the same 5 shots before every question | most of each prompt is cached after the first item |
| G9 MMLU, ARC, HellaSwag (loglikelihood) | the question context, repeated for every answer choice | 4 choices share one context, if prompt logprobs can use the cache (3.3) |
| Demo chat | system turn, then every earlier turn of the conversation | each new turn prefills only the new user message |

### 3.2 The effort header

G10's template puts the effort line first in the system turn:

```text
<|im_start|>system
Reasoning effort: 16k

{system content}<|im_end|>
```

Requests with different effort levels therefore share only `<|im_start|>system\nReasoning effort: ` (well under one
16-token block), and nothing after it. The cost is small. The system turn is short, and requests with the same effort
level share the whole thing. **We do not ask G10 to move the line.** The model is trained on this layout, and moving
it would change the format. The demo should set one effort level per conversation and keep it, so every turn reuses
the cache.

### 3.3 Cautions

- **RL weight updates make the cache stale.** The cached KV was computed by the old policy. After G10 loads new
  weights into a running engine, call `llm.reset_prefix_cache()` (the server has a `/reset_prefix_cache` endpoint in
  dev mode) before the next round. Without it, the new policy reuses old-policy keys and values. Nothing crashes, but
  the rollouts and their logprobs are wrong. **Tell G10; this goes into the rollout loop.**
- **Prompt logprobs.** In some V1 versions, a request that asks for prompt logprobs skips the prefix cache, because
  the logprobs of cached tokens are never computed. If 0.33.0 does that, the loglikelihood evals get no gain from the
  cache. The generation evals and RL still do. *Check on 0.33.0* from the hit-rate metric.
- **Same tokens, not same text.** The cache matches token ids. Any difference in tokenization before the shared part
  (for example a normalizer applied in one path and not the other, `unsupported_parts.md` §4c) breaks the match.
- **Determinism.** Prefill from cache and prefill from scratch can differ at BF16 rounding level. Score comparisons
  between formats must use the same cache setting on both sides.

**Measure:** `vllm:prefix_cache_hits` / `vllm:prefix_cache_queries` from `/metrics` (hit rate) for each job, and wall
time with the cache on and off (`--no-enable-prefix-caching`) on the same items.

## 4. FP8 weights and FP8 KV cache against BF16

### 4.1 Four formats

| Format | Weights | KV cache | How it is made |
|---|---|---|---|
| **BF16** (reference) | BF16 | BF16 | the export from `export_hf.py` |
| FP8-W | FP8 E4M3, per-channel weight scales, dynamic per-token activation scales (W8A8) | BF16 | llm-compressor `QuantizationModifier(scheme="FP8_DYNAMIC", ignore=["lm_head", "re:.*router.*"])`, no calibration data |
| FP8-KV | BF16 | FP8 E4M3 | `--kv-cache-dtype fp8`, with per-layer K/V scales calibrated by llm-compressor (`kv_cache_scheme`), stored in the checkpoint |
| FP8-W + FP8-KV | FP8 | FP8 | both of the above in one llm-compressor recipe |

**Kept in BF16, always:** `lm_head` and the router. That is the week-1 rule, and `model_check.py` already fails a
file whose router is below BF16. In the Granite export the router is `block_sparse_moe.router.layer`, not OLMoE's
`mlp.gate`. **The `ignore` regex must change** (`re:.*router.*`), and `model_check.py` needs the Granite name. The
embedding table is a lookup, so it stays BF16. The shared expert is quantized like the routed ones.

vLLM's online `--quantization fp8` (FP8 at load time, no checkpoint) is quicker to try. It does not let us choose what
to skip, and we have not checked whether it leaves the Granite router alone (*check on 0.33.0*). Use it only for a
smoke test, not for scored rows.

KV scales: without calibrated scales vLLM uses a scale of 1.0, which is safe only while K and V values stay inside
FP8's range. Calibrate the scales from the same 256 × 1,024-token fineweb-edu sample that `gpu_path/` uses, so no
benchmark text leaks in.

### 4.2 Hardware

| GPU (compute capability) | FP8-W | FP8-KV | Note |
|---|---|---|---|
| H100 / H200 (9.0), L4 / L40S (8.9) | yes, native FP8 matmul | yes, E4M3 | the target for FP8 rows |
| A100 (8.0) | weight-only: vLLM upcasts with the FP8 Marlin kernel; no FP8 activations | E5M2 only on some attention backends (*check on 0.33.0*) | gives memory, not FP8 compute. Do not use for FP8 speed rows |
| T4 (7.5), P100 | no | no | Kaggle and Colab free tiers. Use W4A16 (`gpu_path/`) there |

### 4.3 What to expect at our sizes

- **FP8 weights do not save meaningful memory.** T3 goes from 0.94 GB to 0.55 GB on an 80 GB card. What they can save
  is time. A decode step is limited by the weight bytes it reads: attention + 2 routed experts + the shared expert per
  token, and many experts per step once the batch is large. FP8 halves those bytes. H100 FP8 tensor cores speed up the
  prefill matmuls. Small matrices (expert FFN 512–896 wide) may not reach FP8 speed-ups. Measure; do not assume.
- **FP8 KV is where the memory goes.** It doubles the KV tokens (section 2.2: 190 → 380 concurrent 64k sequences on
  H100 at T3). It also halves the KV bytes read per decode step, which matters for long contexts. Expected risk: K/V
  error that grows with context length. Short benchmarks may not show it.
- **Router flips.** FP8 activations into the layer before the router change its input. Test A4 from
  `unsupported_parts.md` §12 (top-k agreement with the FP32 router) is run for every FP8 format.

### 4.4 Measurements (same rules as `bitwidth_proposal.md`)

Each format is scored against vLLM BF16 on the same machine, the same items, the same `max_model_len` and seed, and
the same prefix-cache setting.

| Measure | How | Pass |
|---|---|---|
| eval_mini (ARC-C, HellaSwag, MMLU, GSM8K, TruthfulQA-mc2) and HumanEval+ / MBPP+ | `gpu_path/run_mini_vllm.py`, paired with `eval_mini/paired.py` | the drop limits in [`bitwidth_proposal.md`](bitwidth_proposal.md): −2 / −2 / −3 / −4 / −2 / −3 / −3, and McNemar p ≥ 0.01 |
| KL against BF16 | prompt logprobs (top-20) on the same 16,384 WikiText-2 tokens as `quality/` | reported, not a gate (as for GGUF) |
| Routing agreement | test A4 | report; look into anything below 99% |
| Long-context check, FP8-KV only | the same GSM8K and code prompts at effort 1k, 4k, 16k (and 64k if `seq_len` allows); compare the final-answer accuracy and the KL of the answer tokens with BF16 at each length | no drop that grows with effort level beyond the GSM8K limit |
| Throughput | `vllm bench serve` against the server, random 1,024-in / 1,024-out and 1,024-in / 16,384-out, concurrency 1, 32, 256 | report output tokens/s, median and p99 time to first token, median time per output token, KV tokens, max concurrency |
| Memory | the two start-up log lines (section 2.2) | report |

**Decision rule.** Ship FP8-KV for RL and demo if it passes every limit and the long-context check, because it doubles
concurrency. Ship FP8-W only if it passes every limit and is ≥ 15% faster in output tokens/s at concurrency 256 on
H100. Otherwise BF16 weights stay. The cost of FP8-W at our sizes is accuracy risk for no memory gain.

## 5. Expert parallel

### 5.1 What it is in vLLM

`--enable-expert-parallel` splits the experts of each MoE layer across the GPUs of the data-parallel × tensor-parallel
group, instead of slicing every expert's matrices (TP). Each token is sent to the GPUs that hold its top-2 experts
(all-to-all), then sent back. Attention runs either data-parallel (`--data-parallel-size N`: each GPU holds full
attention weights and only its own sequences' KV) or tensor-parallel.

### 5.2 Our layout

| Fact | Effect on EP |
|---|---|
| 16 routed experts | EP size 2, 4, 8 or 16 divides evenly: 8, 4, 2 or 1 experts per GPU |
| 1 shared expert | every token uses it. Replicated on every GPU (vLLM does this for shared experts); it is not split by EP |
| top-2 | each token visits at most 2 GPUs; with EP 8, at most 2 of 8 |
| expert FFN 512–896 wide (test shapes) | each expert is tiny; the all-to-all per layer can cost more than the expert matmul it saves |
| whole model < 1 GB | no memory reason to split the experts at all |

**At test sizes: no EP.** Run one full replica per GPU (`--data-parallel-size` = number of GPUs, or one server per
GPU behind a load balancer). Every GPU decodes its own batch with no communication. That is the fastest layout for
eval and RL while the model fits one GPU. It is also the layout G9 needs: one `eval` GPU per checkpoint, nothing
shared with training.

**When to turn EP on:** if the production experts make the BF16 weights larger than about half of one GPU (so KV gets
too little room), use `--data-parallel-size N --enable-expert-parallel` **inside one node** (NVLink; the same rule as
G7's `parallel_layout_v0.md` for training). Attention stays data-parallel, so each GPU keeps full KV heads for its own
sequences.

### 5.3 Why not TP for attention

vLLM splits KV heads across TP ranks. With `n_kv_head = 2`, TP 2 gives one KV head per GPU. **TP 4 or 8 duplicates
each KV head on 2 or 4 GPUs**, which wastes that share of the KV budget and gives no speed. MQA (`attn-1`) makes any
TP > 1 duplicate. So TP ≤ `n_kv_head`, and DP attention + EP is the scale-out path. `gpu_path/` ran TP 2 on two T4s
only because OLMoE's BF16 weights (13.8 GB) did not fit one T4.

### 5.4 Checks before EP is used

- **Expert load.** Log the per-expert token count per layer during the A4 test. If one GPU's experts get much more than
  1/EP of the tokens, that GPU sets the step time. vLLM's expert-parallel load balancer (`--enable-eplb`, redundant
  copies of hot experts) is the fix to try (*check on 0.33.0*).
- **MoE kernel configs.** vLLM's fused MoE kernel reads tuned tile sizes per (number of experts, FFN width, dtype, GPU)
  shape. E = 16 with N = 512/768/896 is probably not in the shipped table, so it falls back to a default. Run vLLM's
  `benchmarks/kernels/benchmark_moe.py --tune` for the production shape, once for BF16 and once for FP8, and commit
  the JSON with the plan.
- **Numbers do not change.** EP and DP move work between GPUs; they must give the same logprobs as one GPU to BF16
  rounding. Run test A2 on 1 GPU and on the EP layout and compare.

## 6. Serving API (demo endpoint)

```bash
vllm serve /models/v5-<ckpt>-bf16 \
  --served-model-name v5 \
  --chat-template teams/12-quantization/tokenizer/chat_template.jinja \
  --max-model-len <seq_len> --gpu-memory-utilization 0.90 \
  --max-num-seqs 256 --max-num-batched-tokens 2048 \
  --enable-prefix-caching \
  --reasoning-parser v5 --reasoning-parser-plugin teams/12-quantization/serving/v5_reasoning_parser.py \
  --enable-auto-tool-choice --tool-call-parser v5 --tool-parser-plugin teams/12-quantization/serving/v5_tool_parser.py \
  --seed 42
# FP8 rows add: --kv-cache-dtype fp8   (and point --model at the FP8 checkpoint)
```

- **Chat template:** G10's `chat_template.jinja` (ChatML v0, effort line in the system turn), copied to
  `tokenizer/chat_template.jinja` as the hand-off asks. It is also written into `tokenizer_config.json` at export, so a
  client without `--chat-template` gets the same prompt.
- **Stop tokens:** `<|im_end|>` (130816) and `<|endoftext|>` (130822) must be in `generation_config.json`
  `eos_token_id`, or generation does not stop (`unsupported_parts.md` §4b).
- **Reasoning parser:** vLLM's built-in parsers look for `<think>`/`</think>`. Ours are the atomic tokens `<|think|>`
  (130823) and `<|/think|>` (130824), not the base `<think>` (128512). We need a small plugin parser that splits on
  these two token ids into `reasoning_content` and `content`.
- **Tool-call parser:** a plugin parser for `<|tool_call|>` (130773) … `<|/tool_call|>` (130825) holding
  `{"name": …, "arguments": …}` JSON, the layout in the G10 hand-off §3.
- Both parsers are week-3 work (Member C). Each gets a test that renders a G10 example conversation, runs the parser,
  and checks that the messages come back unchanged.

## 7. Serve one checkpoint (dry run, until 21 Nov)

1. Export the dry-run checkpoint with `export_hf.py` (`unsupported_parts.md` §8). Write the SHA-256 manifest
   (`model_check.py`).
2. Run acceptance tests A1, A2 and A4 (`unsupported_parts.md` §12) on vLLM BF16. Nothing below means anything until
   they pass.
3. Start the server (section 6) on one H100 or L4. Record the KV-cache log lines, `vllm --version`, the GPU and the
   flags in `environment.json`.
4. Smoke test: chat completion with effort 1k and 16k, a tool call, and stopping at `<|im_end|>`.
5. Run the section 4.4 measurements for BF16, then FP8-KV, FP8-W and both. Run the section 3 prefix-cache on/off
   comparison.
6. Write rows to `runs/runs.csv` with `runtime = vLLM 0.33.0` and the KV dtype in `notes`. Fill the table below.

Results (to fill):

| Format | GPU | KV tokens | Max concurrency at `seq_len` | eval_mini vs BF16 | Long-context check | Out tok/s @256 | p50 TTFT | p50 TPOT | Prefix hit rate (RL / GSM8K) |
|---|---|---|---|---|---|---|---|---|---|
| BF16 | | | | reference | reference | | | | |
| FP8-KV | | | | | | | | | |
| FP8-W | | | | | n/a | | | | |
| FP8-W + FP8-KV | | | | | | | | | |

## 8. What we need, and by when

| From | What | When | Used in |
|---|---|---|---|
| TSAI / G5 | production sizes: `n_layer`, `d_model`, `n_head`, `n_kv_head`, `d_ff`, `seq_len` | before Gate 3 | 2 (all budget numbers), 5.2 |
| G5 | the dry-run checkpoint and its `state_dict` key names | 21 Nov | 7 |
| G7 | GPU type of the `eval` partition and of the main nodes (H100 or not) | week 3 | 2.2, 4.2 |
| G10 | confirm `reset_prefix_cache()` after each weight sync in the rollout loop; the group size G | week 3 | 3.3 |
| G9 | max context of the eval prompts per task, to set `max_model_len` and `max_num_batched_tokens` on the eval GPUs | week 3 | 2.3 |
| G12 Member C | reasoning and tool-call parser plugins; `model_check.py` with the Granite router name; FP8 recipes in `gpu_path/` | week 3 | 4.1, 6 |

## Reproduce the numbers in section 2

```python
V = 131072  # vocab; KE2 folded to a V x d_model table, untied head
for name, (L, d, h, kv, ff, E) in {"T1": (6, 256, 4, 2, 512, 8),
                                   "T2": (8, 512, 8, 2, 768, 16),
                                   "T3": (10, 640, 10, 2, 896, 16)}.items():
    hd = d // h
    kv_bytes = 2 * L * kv * hd * 2                      # BF16, per token
    params = 2 * V * d + (E + 1) * 3 * d * ff * L + L * d * (2 * d + 2 * kv * hd)
    print(name, kv_bytes / 1024, "KiB/token", round(params / 1e6, 1), "M params")
```
