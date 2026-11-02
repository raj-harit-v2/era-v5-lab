# Parts that llama.cpp and vLLM do not support yet (G12, week 2)

**Status:** part 1, 4 Nov 2026. Covers the KE2 embedding, attention and the tokenizer for config v0 and
tokenizer v0. Part 2 (one plan per custom part of config v1) is added on 14 Nov, when G5 sends config v1.

**Checked against:**
- llama.cpp **b11669** (= v0.7.0), the build used for every GGUF in this folder. File and line references are to
  `convert_hf_to_gguf.py`, `conversion/base.py` and `src/llama-vocab.cpp` at that tag.
- vLLM: the serving path that Member C sets up in `gpu_path/`. The vLLM version is pinned there; the vLLM rows
  below describe how vLLM loads models in general and are marked "check on the pinned version" where we have not run it.
- Inputs: `teams/04-ke2/output_shape.md` (draft v0, P = 32), `teams/05-architecture/configs/config_v0.yaml`,
  `teams/03-tokenizer/v0/` (BrahmicTokenizer-131K with renamed reserved slots, `tokenizer.json` sha256
  `01d968a7…739fff` for the baseline).

## Summary

| Part | llama.cpp today | vLLM today | What breaks | Plan |
|---|---|---|---|---|
| KE2 input embedding | no: expects a `token_embd` table | no: expects an `nn.Embedding` | the checkpoint has no embedding table, only a `Linear(8192, d_model)` | **fold** KE2 + projection into a normal `V × d_model` table at export. Exact, no runtime change |
| KE2 output side | depends on the design | depends on the design | not decided until 14 Nov | tied or table-shaped output: fold the same way. Anything else: plan in part 2 |
| Attention | yes, if config v1 matches an existing architecture | yes, same condition | config v0 has no sizes; `attention.impl: eager` is a training setting only | export under an existing architecture whose attention matches config v1; check the list below |
| Tokenizer pre-tokenizer | **converter stops**: hash not recognised | yes: uses `tokenizer.json` directly | the obvious workaround (`gpt-4o`) **splits every Indic word** at its vowel signs | register the tokenizer as `granite-embed-multi`-type pre-tokenizer; prove it with Member E's round trip |
| Tokenizer normalizer (G3 v1 idea, NFC + chillu + nukta) | **no**: the BPE path has no normalizer | yes, if written as `tokenizers` normalizers | llama.cpp would tokenize un-normalized text differently | normalize before tokenizing in the serving app, or keep the normalizer in data prep only |
| MTP head (`loss_mtp`, t+2) | no: converter stops on unknown tensors | no generic support | export fails, or the head is silently ignored | drop the head at export for the demo |
| Router (`ffn_gate_inp`) | kept F32, never quantized | kept bf16 with the `ignore` list | nothing, if the rule is followed | keep checking it in every output file (week-1 rule) |

## 1. KE2 input embedding

**What it is.** KE2 replaces the token-embedding table (`teams/04-ke2/output_shape.md`). A token id becomes a fixed
code of `D = 256 · P = 8,192` numbers (P = 32), built from the token's bytes, with no learned weights. One learned
`Linear(8192, d_model, bias=False)` follows. The output has the same shape as `nn.Embedding`: `(B, T, d_model)`.

**llama.cpp today.** Every llama.cpp architecture reads the input embedding from one tensor, `token_embd.weight`
(`V × d_model`), and looks rows up with `ggml_get_rows`. There is no op that builds a code from token bytes. The
converter maps each checkpoint tensor to a GGUF name and stops on any tensor it does not know
(`conversion/base.py`, `map_tensor_name`: `ValueError("Can not map tensor …")`). A checkpoint with a
`ke2.proj.weight` and no embedding table cannot be converted.

**vLLM today.** Each vLLM model class owns an embedding module (usually `VocabParallelEmbedding`). A KE2 model would
need its own model class. vLLM can also accept precomputed `prompt_embeds`, but that moves the embedding out of the
server and does not cover the tokens the model generates. Check both on the pinned version.

**What breaks.** Nothing works without a change: neither runtime can load the checkpoint as it is.

**Plan: fold KE2 into a normal table at export.** The code depends only on the token id, and the projection is
linear, so for every id the embedding is a fixed vector:

```
E[id] = W · code(id)            W: d_model × 8192,  E: 131,072 × d_model
```

Computing `E` once and writing it as `token_embd.weight` (GGUF) or `embed_tokens.weight` (HF/vLLM) gives a standard
model that both runtimes already load. It is exact, not an approximation. It is also cheap: after z-normalisation
every coordinate of a code has one of two values that depend only on the token length L (KE2 Lemma 1,
`teams/04-ke2/src/ke2/codec.py`, `code_values`), so

```
E[id] = low(L) · Σ_j W[:, j]  +  (high(L) − low(L)) · Σ_{p < L} W[:, b_p · P + p]
```

which needs L column reads per token, not a dense `131,072 × 8,192` product.

| | Before fold (training) | After fold (served) |
|---|---|---|
| Input parameters at `d_model = 768` | 6.29 M (`8,192 × 768`) | 100.66 M (`131,072 × 768`) |
| bf16 size of that part | 12.6 MB | 201 MB |
| Runtime code needed | KE2 codec + matmul | none (table lookup) |

The fold gives up KE2's parameter saving at inference time. That is the price of running on stock llama.cpp and
vLLM. The table can be quantized like any `token_embd` (llama.cpp `--token-embedding-type`); the drop must then be
measured like any other tensor.

**Acceptance test (to run when the first KE2 checkpoint exists):**
1. Fold in float64 with the closed form above; store as bf16.
2. For 10,000 random ids plus all 356 special tokens, compare the folded row with the KE2 forward pass
   (`ke2.codec.encode_ids` then the projection) in float32. Pass: max abs difference at bf16 rounding level.
3. Convert the folded checkpoint to GGUF and compare bf16 GGUF logits with the PyTorch model on 64 prompts.

**Owner / date:** G12 Member D writes `fold_ke2.py` once config v1 fixes `d_model` and G4 confirms the projection's
weight name (week 3).

## 2. KE2 output side

`output_shape.md` says the output side (the next-token layer) is not decided; the KE2 decision is on 14 Nov. Three
cases, with the plan for each:

| Output design | llama.cpp | vLLM | Plan |
|---|---|---|---|
| Normal `lm_head` (`d_model × V`) | yes (`output.weight`) | yes | nothing to do; keep it at Q8_0 or bf16 (week-1 rule) |
| Tied to the KE2 input (`logits = h · Eᵀ`) | yes: if `output.weight` is missing, llama.cpp uses `token_embd` | yes (`tie_word_embeddings`) | fold as in section 1; the folded `E` serves both ends |
| Anything that is not a `V × d_model` matrix (for example a byte-level output) | no | no | needs a custom architecture in both runtimes; plan in part 2 |

## 3. Attention

**What config v0 says.** Only `attention.impl: eager`. All sizes (`n_layer`, `d_model`, `n_head`, `d_ff`,
`seq_len`, `n_expert`, `top_k`) are empty until TSAI fills them. `eager` is a training choice: the harness uses
eager attention so that two runs with the same seed match. It is not part of the model. The runtimes use their own
kernels (llama.cpp flash attention, vLLM FlashAttention or FlashInfer). The numbers differ slightly from eager,
which is why we compare a quantized score only with the bf16 score from the same runtime (week-1 rule).

**llama.cpp and vLLM today.** Both support standard multi-head and grouped-query attention, RoPE with the usual
scaling types, QK-norm (OLMoE, Qwen3-MoE) and sliding-window attention for the architectures that define it. Both
support OLMoE and Qwen3-MoE end to end (`tools/tools.md`). Neither runs an attention variant that no existing
architecture uses.

**What breaks.** Nothing yet; we cannot tell until config v1. The risk is a custom choice that no existing
architecture has.

**Plan.** Export the model under an existing architecture whose attention and MoE block match config v1, so no runtime
code is needed. When config v1 arrives, check each item against OLMoE (`src/models/olmoe.cpp`, vLLM `olmoe.py`) and
Qwen3-MoE:

- heads and KV heads (MHA or GQA), head dimension
- position encoding: RoPE type, theta, scaling for `seq_len`
- QK-norm or not; norm type (RMSNorm or LayerNorm) and its placement
- shared experts, router normalisation, top-k
- any attention bias, logit soft-capping or sliding window

Each item that matches no existing architecture becomes a custom part with its own plan in part 2.

## 4. Tokenizer

**What it is.** Tokenizer v0 is BrahmicTokenizer-131K with renamed reserved slots (`teams/03-tokenizer/v0/`). From its
`tokenizer.json`: byte-level BPE, vocab 131,072, 356 special tokens, `ignore_merges: true`, **no normalizer**, and a
pre-tokenizer regex that is exactly GPT-4o's (o200k) regex, which includes `\p{M}` (combining marks) in its letter classes.

### 4a. Pre-tokenizer: measured

**vLLM today.** vLLM loads the Hugging Face tokenizer from `tokenizer.json`, so it splits text exactly like the
training pipeline. Low risk.

**llama.cpp today.** llama.cpp does not read the regex from `tokenizer.json`. The converter encodes a fixed test string,
hashes the token ids and looks the hash up in a hard-coded list (`conversion/base.py`, `get_vocab_base_pre`). Each
entry maps to a pre-tokenizer type with its own regex in C++ (`src/llama-vocab.cpp`).

Measured on 1 Nov with the baseline `tokenizer.json`:

| Check | Result |
|---|---|
| Our hash | `57e4bd19…2f7748d7` |
| In the b11669 list? | **no**: conversion stops with `BPE pre-tokenizer was not recognized` |

The usual workaround is to add our hash and map it to the type with the same regex, `gpt-4o`. **That breaks
Indic text.** llama.cpp's `gpt-4o` type rewrites the regex with lookaheads that leave out `\p{M}`. Indic vowel signs
and the virama are `\p{M}`, so every Indic word is cut at its vowel signs before BPE runs. The type
`granite-embed-multi-97m` uses the same lookaheads **with** `\p{M}` added (llama.cpp PR #22716), and it also sets
`ignore_merges`, as our tokenizer does.

Pre-token splits of the three regexes, run with Python `regex` on sample sentences:

| Text | HF `tokenizer.json` | llama.cpp `gpt-4o` | llama.cpp `granite-embed-multi` |
|---|---|---|---|
| Hindi | 10 pieces: `हिन्दी`, ` भारत`, … | **23 pieces:** `ह`, `िन`, `्द`, `ी`, … | same as HF |
| Bengali | 6 | **16** | same |
| Tamil | 5 | **13** | same |
| Malayalam | 4 | **7** | same |
| Telugu | 4 | **13** | same |
| English | 10 | same | same |
| Code | 13 | same | same |

A wrong split does not crash. It gives different token ids from training, so the served model sees text it never
saw. This would show up as an Indic-only score drop that has nothing to do with the bit width.

**Plan.**
1. In our converter run, map hash `57e4bd19…` to `granite-embed-multi-97m`: one line in `get_vocab_base_pre`, or
   write `tokenizer.ggml.pre = "granite-embed-multi-97m"` into the GGUF.
2. Member E's `tokenizer/gguf_roundtrip.py` is the proof. Encode 1,000 lines per script and of code with llama.cpp
   and with HF `tokenizers`. Pass: identical ids and lossless decode for every line. This checks llama.cpp's own
   regex engine, not just Python `regex`.
3. Repeat on the frozen tokenizer (14 Nov). If G3 changes the regex, recompute the hash and redo this check.
4. Upstream: once it passes, open a llama.cpp PR adding the hash, so later builds need no local patch.

### 4b. Special tokens and chat template

| Item | llama.cpp | vLLM | Note |
|---|---|---|---|
| 356 specials, renamed reserved slots (`<\|g10_slot_00\|>`, …) | yes: GGUF stores each token's string and type | yes | renames keep ids; nothing to change |
| BOS/EOS, `<\|im_start\|>` / `<\|im_end\|>` (G10 ChatML v0) | yes: set `tokenizer.ggml.eos_token_id` and the end-of-generation tokens correctly, or generation does not stop | yes: from `generation_config.json` | check that the GGUF's EOS and EOT ids are 130,822 (`<\|endoftext\|>`) and 130,816 (`<\|im_end\|>`) |
| Chat template | yes: Jinja in `tokenizer.chat_template` | yes | G10 sends it on 12 Nov; test it with `llama-server` and vLLM chat endpoints |

### 4c. Normalizer (G3 v1 idea #134)

Tokenizer v0 has no normalizer, so there is nothing to break today. G3's v1 idea #134 adds one: NFC, chillu
re-join and Bengali/Punjabi nukta re-join.

| Runtime | Supported? | Detail |
|---|---|---|
| vLLM | yes | it runs whatever `tokenizer.json` contains; the rules can be written as `tokenizers` normalizers (`NFC` + `Replace`) |
| llama.cpp | **no** | its BPE path applies no normalizer at all; at b11669 the only `nfc` flag is used by the Unigram (UGM) tokenizer |

If the frozen tokenizer has a normalizer, the same raw text would give different ids in llama.cpp.

**Plan:** prefer normalizing in data prep and in the serving app, before the text reaches the tokenizer, so the
tokenizer itself has none. If G3 keeps it inside `tokenizer.json`, add normalized and un-normalized lines to the
round trip and list each difference with its cause.

## 5. MTP head

Config v0 trains a second linear head scored at t+2 (`loss_mtp`). It is not a stacked MTP block.

| Runtime | Status |
|---|---|
| llama.cpp | stops on the unknown tensor (`Can not map tensor`) |
| vLLM | uses MTP heads only for some architectures, for speculative decoding; a model class drops or rejects unknown weights depending on its `load_weights` |

**Plan:** drop the head at export for the demo; next-token generation does not use it. Keep it in the training
checkpoint. Reconsider only if TSAI wants speculative decoding, which would need a custom draft path in both
runtimes.

## 6. Router

Already handled; listed so the rule is not lost. llama.cpp never quantizes `ffn_gate_inp`
(`src/llama-quant.cpp`). llm-compressor keeps it in bf16 with `ignore=["re:.*mlp.gate$"]`, and Member C must confirm
that the regex matches the router name in our model (`tools/tools.md`, open checks). Every output file is checked
(week-1 rule).

## What we need from other teams

| From | What | When | Used in |
|---|---|---|---|
| G4 | final `output_shape.md`; the projection's weight name; the output-side decision | 4 Nov; 14 Nov | sections 1, 2 |
| G5 | config v1: sizes, attention and MoE details, custom parts | 14 Nov | section 3, part 2 |
| G3 | frozen tokenizer; whether the normalizer is in `tokenizer.json` | 14 Nov | section 4 |
| G10 | chat template | 12 Nov | section 4b |
| G12 Member E | `results/gguf_roundtrip_v0.md`, then `results/gguf_roundtrip_frozen.md` | 4 Nov, 14 Nov | section 4a |

## Reproduce the pre-tokenizer check

```bash
pip install regex tokenizers
curl -sLO https://huggingface.co/theschoolofai/BrahmicTokenizer-131K/resolve/main/tokenizer.json
curl -sLO https://raw.githubusercontent.com/ggml-org/llama.cpp/b11669/conversion/base.py
curl -sLO https://raw.githubusercontent.com/ggml-org/llama.cpp/b11669/src/llama-vocab.cpp
```

```python
import hashlib, json, re, regex
from tokenizers import Tokenizer

tok = Tokenizer.from_file("tokenizer.json")
base = open("base.py", encoding="utf-8").read()
chktxt = eval(re.search(r"chktxt = ('.*?')\n", base).group(1))
h = hashlib.sha256(str(tok.encode(chktxt, add_special_tokens=False).ids).encode()).hexdigest()
print("hash", h, "known:", h in base)

hf = json.load(open("tokenizer.json", encoding="utf-8"))["pre_tokenizer"]["pretokenizers"][0]["pattern"]["Regex"]
cpp = open("llama-vocab.cpp", encoding="utf-8").read()

def first_regex(case):
    i = cpp.index("regex_exprs = {", cpp.index(case))
    return eval(next(l.strip().rstrip(",") for l in cpp[i:cpp.index("};", i)].splitlines() if l.strip().startswith('"')))

split = lambda p, s: [m.group() for m in regex.finditer(p, s)]
text = "हिन्दी भारत की राजभाषा है।"
for name in ("LLAMA_VOCAB_PRE_TYPE_GPT4O:", "LLAMA_VOCAB_PRE_TYPE_GRANITE_EMB_MULTI:"):
    print(name, split(first_regex("case " + name), text) == split(hf, text))
```
