# G3 tokenizer card: p1536 (frozen)

> 15 Nov: TSAI froze p1536 (e6b93a93…a64b), replacing C3 from Gate 2 (#443). Token ids are identical and eos stays 130822. p1536 mean Indic FLORES is −24.81% (#436). The C3 sections below are kept for history.

Frozen at Gate 2 (#340, #443). Token ids never change without a TSAI approval.
Cite this card with the sha below. Every number links to the PR or file it comes from.

| Field | Value |
|---|---|
| Name | p1536 |
| File | `tokenizer.json` (8 MB, not in the repo: over pr-guard's 5 MB limit) |
| sha256 | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| Pinned in | `release/SHA256SUMS` (#504) |
| Rebuild | `train/rebuild_cand.py` (p1536); TSAI rebuilt it and got the same sha |
| Type | byte-level BPE, Hugging Face `tokenizers` format |
| Base | BrahmicTokenizer-131K (`theschoolofai/BrahmicTokenizer-131K`, commit `7dfcf398`) |
| Owners | Team 3 Tokenizer. Card: @rjvim |

## 1. How to load

```python
import hashlib
from tokenizers import Tokenizer

p = "release/tokenizer.json"
assert hashlib.sha256(open(p, "rb").read()).hexdigest().startswith("e6b93a93")
tok = Tokenizer.from_file(p)
ids = tok.encode("नमस्ते दुनिया", add_special_tokens=False).ids + [130822]  # eos per doc
```

- Load the file directly. G6's `BrahmicTokenizer` class pins the baseline sha (`01d968a7…`) and will not load it.
- `transformers`: put `release/tokenizer_config.json` and `release/special_tokens_map.json` (#407) next to `tokenizer.json`, then `AutoTokenizer.from_pretrained("release/")`.
- Do not add your own NFC/NFKC step. The normalizer is inside `tokenizer.json`.

## 2. Vocabulary

| Item | Value |
|---|---|
| Vocab size | 131,072 (ids 0 to 131,071). Embedding size 131,072 |
| Normal BPE tokens | 130,716 |
| Special tokens | 356 (`special: true` in `added_tokens`) |
| Merges | 130,460 |
| Byte tokens | ids 0 to 255 (any byte sequence encodes, no `<unk>` in practice) |
| Max token length | 32 bytes (G4 check, #372) |
| Cross-script merges | none (baseline rule kept) |
| Raw-byte collisions | 0 at P=32/64 (G4, Avnish, #372) |

How C3 was built (`train/c3_s0_manifest.json`, #195):
1. **o200k swap** (#166): 13,850 base tokens that were never used in the usage audit were replaced with English and code tokens from o200k. English and code got back to baseline level.
2. **slots_v2**: per-script merge budget, chosen on held-out FineWeb-2 text, not on FLORES.
3. **normalizer v1** (#134), see section 3.
4. **Text mix** `mix_s0.json`: Devanagari from corpus60 + sample v0; Gu, Or from sample v0; other scripts from corpus60. Sample v0 has no Pa or As text.

C1 (swap only) −16.28%, C2 (+slots) −16.47% and C3 −17.10% mean Indic all passed. C3 was picked for the best Indic mean (`freeze_report.md`).

## 3. Normalizer (v1, #134)

Runs inside `tokenizer.json`, before pre-tokenization.

| Rule | Why |
|---|---|
| NFC | NFD input cost +2 to +4% tokens on Bn, Ta, Ml, Or |
| Malayalam old chillu (consonant + virama + ZWJ) → atomic chillu (ൻ ർ ൽ ൾ ൺ ൿ) | −5% tokens on Malayalam |
| Bengali / Gurmukhi nukta re-join (e.g. য + ় → য়) | one form for the same letter |

Things to know:
- `decode(encode(x)) == normalizer(x)`, not always `x`. Bn/Pa nukta text and Ml old chillu come back in the normalized form. Round-trip checks must compare against the normalized text.
- Other tools that drop the normalizer get different ids on that text. llama.cpp GGUF (#427, G12): ids match once the normalizer is applied first. One known gap remains: llama.cpp's pre-tokenizer treats ASCII case classes differently, which changed 9 tokens on 1 Cyrillic line in the test set. Accepted for Gate 2.
- ZWJ/ZWNJ are kept (no stripping).

## 4. Special tokens

Source of truth: `added_tokens` in `tokenizer.json`. Roles: `release/SPECIAL_TOKENS.md` (#407).

| Role / use | Token | Id |
|---|---|---|
| **eos** (end of every document in pretraining shards) | `<\|endoftext\|>` | 130822 |
| bos (not added by default) | `<\|begin_of_text\|>` | 130725 |
| pad | `<\|pad\|>` | 130726 |
| unk (never emitted by byte-level BPE) | `<\|unk\|>` | 130727 |
| Chat turn start | `<\|im_start\|>` | 129994 |
| Chat turn end (turn marker, not eos) | `<\|im_end\|>` | 130816 |
| Tool call open / close | `<\|tool_call\|>` / `<\|/tool_call\|>` | 130773 / 130825 |
| Tool result open / close | `<\|tool_result\|>` / `<\|/tool_result\|>` | 130774 / 130826 |
| Think open / close | `<\|think\|>` / `<\|/think\|>` | 130823 / 130824 |
| Old baseline eos (special, no role, do not use) | `<\|end_of_text\|>` | 36 |

Reserved blocks (same ids as v0, #107):

| Ids | Block | State |
|---|---|---|
| 130822 to 130885 | `g10_slot_00..63` | 00 to 04 used (rows above, #173); 05 to 63 free for Team 10 |
| 130886 to 130917 | `lang_slot_00..31` | free (no language tags in shards v0) |
| 130918 to 130949 | `ctrl_slot_00..31` | free |
| 130950 to 131071 | `reserved_128..249` | free |

Rules:
- `add_bos_token` and `add_eos_token` are false. The shard writer appends 130822 itself.
- Filling a free slot means renaming the string only: same id, `special: true` kept, and a TSAI approval after the freeze.
- Literal special strings in raw text (for example `<|im_start|>` inside web or code text) are turned into special ids by HF `tokenizers`. Shard writers must check that no special id appears inside a document, only the final eos.
- Chat format and vLLM parser check: `results/chat_format_check.md` (Task 5). TODO: link when merged.

## 5. Scores per language

### 5.1 FLORES-200 fertility (tokens per whitespace word, dev+devtest, no BOS)

Harness: `harness/run_harness.py` (#276, #305). Baseline = BrahmicTokenizer-131K. Lower is better.

| Lang | Baseline | C3 | Change | Reproduced by |
|---|---|---|---|---|
| Odia (Or) | 4.1287 | 2.4861 | −39.78% | Deepjyoti Saha |
| Punjabi (Pa) | 2.5955 | 2.0129 | −22.45% | Raghav Tayal |
| Marathi (Mr) | TODO | TODO | −18.58% | Rahul Uniyal |
| Tamil (Ta) | 3.1166 | 2.5927 | −16.81% | Stephen Raj Arokiasamy |
| Kannada (Kn) | 3.2734 | 2.7469 | −16.08% | Vijay Patil |
| Telugu (Te) | 3.0292 | 2.5531 | −15.72% | Pritish Nayak |
| Malayalam (Ml) | 3.4738 | 3.0324 | −12.71% | Stephen Raj Arokiasamy |
| Gujarati (Gu) | TODO | TODO | −2.9% | |
| Hindi, Bengali, Assamese, other rows | TODO | TODO | TODO | |
| **Mean Indic (12)** | **2.8355** | **2.3505** | **−17.10%** | all rows match COMPARE.md |
| English (En) | 1.2352 | 1.2334 | −0.15% | |

TODO before merge: copy the missing rows from `COMPARE.md` (C3 sample-v0 section).

C3 beats the baseline on all 12 FLORES Indic languages. Every rotator number above matches COMPARE.md exactly (max abs diff 0.0000).

### 5.2 Code and other suites

| Suite | Metric | Baseline | C3 | Change |
|---|---|---|---|---|
| HumanEval | tokens per char | 0.2951 | 0.2953 | +0.07% |
| MBPP | tokens per char | 0.3195 | 0.3203 | +0.25% |
| IN22-Gen (#390, Nitin) | fertility | 3.0792 | 2.5990 | −15.6% |
| FineWeb-2 held-out check split (mean Indic) | fertility | | | −17.54% |
| FineWeb-2 Telugu web (189 docs, Pritish) | fertility | 2.9790 | 2.5237 | −15.28% |

### 5.3 Model-side scores (TODO, from TSAI)

| Item | Value |
|---|---|
| bits per byte (TSAI bpb test, Gate 2) | TODO: TSAI number |
| Per-language bpb | TODO |

### 5.4 Yardsticks (not candidates)

| Tokenizer | Telugu FLORES | English | Note |
|---|---|---|---|
| C3 | 2.5531 | 1.2334 | |
| Sarvam-1 | 2.1321 | | leads C3 on Te by 16.5% on FLORES, 6.2% on web text |
| Vemana (Udgam Labs, Te only) | 1.73 (#366) | 2.31 | Telugu-only vocab, +87% on English |

No outside tokenizer passes the bar: every one that beats C3 on Indic (Gemma-4, Sarvam-30B, Sarvam-1) is at least 13% worse on code (`freeze_report.md`).

## 6. Speed and round trip

| Check | Result | Source |
|---|---|---|
| Round trip, held-out text, 38 packs, 13,154 docs | 0 failures (normalizer changed 406 docs, expected) | #305, Riya |
| Round trip on the returned token shards, 1,000 docs per domain | TODO: Task 4, `results/roundtrip_shards.md` | Riya |
| Encode speed, 1 CPU core, 1 GB per domain | TODO: Task 3, `results/speed_v1.md` | |
| Speed vs BrahmicTokenizer-131K | TODO: rotation R1/R2 files | rotation members |

## 7. Known limits

- **Training text:** sample v0 has no Pa or As, so those scripts' merges come from corpus60.
- **Gujarati check split:** about 2.5% line overlap with the training sample, so Gu held-out gains may be slightly optimistic. FLORES Gu is unaffected.
- **Dravidian:** still the largest gap to Indic-specialised tokenizers (Te 2.55 vs Sarvam-1 2.13). 31 to 43% of Dravidian tokens start with a matra or virama (`tokenizer-weakspots` analysis). Next work, if TSAI allows a change: C4 plan.
- **Normalizer outside HF:** tools that skip it (GGUF, custom Rust/C++) must apply NFC + chillu + nukta first. llama.cpp ASCII case-class gap: 9 tokens on 1 line (#427).
- **Eval sets** (FLORES-200, IN22, HumanEval, MBPP, GSM8K) were never used for training. FLORES was used to compare candidates; the slot split was chosen on held-out FineWeb-2.
- **Windows:** use `PYTHONUTF8=1`; LF line endings for hashed files (#330).

## 8. History

| Version | sha256 | What | PR |
|---|---|---|---|
| baseline | `01d968a7…` | BrahmicTokenizer-131K | |
| v0 | `2de039f2…f8e5` | reserved slots named, same ids | #107 |
| v0.1 | `a33c9907…e578` | Team 10 chat markers in `g10_slot_00..04` | #173 |
| C3 sample-v0 | `15468e66…ddc3` | o200k swap + slots_v2 + normalizer v1, retrained on sample v0 | #195, #340 |
| p1536 (frozen) | `e6b93a93…a64b` | pruned o200k candidate, same ids as C3 | #414, #436 |
| Special-token roles | (config only, ids unchanged) | eos 130822, bos, pad, unk | #407 |
