# Special tokens v1 (Final Consolidated Allocation)

Shared G10 special-token allocation file (`teams/10-post-training/special-tokens/special_tokens_v1.md`).
Prepared for **Team 3 (G3 Tokenizer)**, **Team 4 (G4 KE2)**, and **Team 9 (G9 Evaluation)**. It replaces the 000 to 255 numbering of v0 with the real Team 3 token IDs (issue #132, `teams/03-tokenizer/v0/special_slots.md`).

---

## 1. Core Architecture & Policy

- **ChatML Foundation**: Structural turns delimited by atomic tokens `<|im_start|>` and `<|im_end|>`. Document boundaries closed with `<|endoftext|>`.
- **Structural vs. Value Plane Separation (27 Oct Ruling)**:
  - Special tokens are strictly reserved for structural delimiters that the model must never confuse with normal text.
  - Variable values (reasoning effort, tool names, parameters, options) remain plain text inside the structure.
  - Reasoning effort is conditioned via the plain-text system line: `Reasoning effort: {1k|4k|16k|64k}`.
- **Token IDs come from Team 3.** The vocabulary stays at 131,072 IDs. IDs 0 to 255 are byte tokens (256 of them) and are not used for markers. A marker that already exists in the base tokenizer keeps its ID (130,725 to 130,821, plus `<|im_start|>` at 129,994). Each new marker takes one G10 slot, `g10_slot_00` to `g10_slot_63` (IDs 130,822 to 130,885). Every marker has exactly one ID and is never split into subwords.
- **The chat format does not use the base `<think>` token** (ID 128,512). Reasoning uses `<|think|>` and `<|/think|>`.
- **Strict Delimiter Isolation**: Special tokens match their exact raw text, so a fullwidth look-alike such as `<｜think｜>` is tokenized as plain text and cannot trigger a marker (Team 3, 30 Oct). `render.py` also rejects literal markers and look-alikes in message content.

### Pre-tokenization rule (no NFKC)

- **Do not apply NFKC to content.** It breaks Indic text: it splits precomposed nukta letters (`ज़` `U+095B` becomes `ज` + `़`) and folds compatibility characters in mixed text.
- **Keep ZWJ (`U+200D`) and ZWNJ (`U+200C`).** They choose between a half form and a conjunct, so removing them changes the written word (see `chat_format_v0.md`, Hindi section and `results/hindi_swe_e2e.md`).
- Homoglyph and zero-width checks (for example `U+200B`, `U+FEFF`) belong in the data cleaning rules, not in the tokenizer.

---

## 2. G10 Marker IDs (17 markers)

| Token ID | Name | Special Token Surface (Atomic) | Where the ID comes from | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| `129994` | `im_start` | `<\|im_start\|>` | base tokenizer, kept | Start of ChatML turn (`system`, `user`, `assistant`, `tool`) |
| `130773` | `tool_call` | `<\|tool_call\|>` | base tokenizer, kept | Start of structured JSON tool call payload |
| `130774` | `tool_result` | `<\|tool_result\|>` | base tokenizer, kept | Start of tool execution output (untrusted environment) |
| `130801` | `fim_prefix` | `<\|fim_prefix\|>` | base tokenizer, kept | Fill-In-The-Middle prefix anchor for code infilling |
| `130802` | `fim_middle` | `<\|fim_middle\|>` | base tokenizer, kept | Fill-In-The-Middle middle target slot |
| `130803` | `fim_suffix` | `<\|fim_suffix\|>` | base tokenizer, kept | Fill-In-The-Middle suffix context anchor |
| `130804` | `fim_pad` | `<\|fim_pad\|>` | base tokenizer, kept | Fill-In-The-Middle padding for batched infilling |
| `130816` | `im_end` | `<\|im_end\|>` | base tokenizer, kept | End of ChatML turn |
| `130817` | `file_sep` | `<\|file_sep\|>` | base tokenizer, kept | Multi-file boundary delimiter in a repo map |
| `130818` | `repo_name` | `<\|repo_name\|>` | base tokenizer, kept | Repository / package identifier anchor |
| `130822` | `endoftext` | `<\|endoftext\|>` | `g10_slot_00`, in tokenizer v0.1 | End of document / transcript boundary |
| `130823` | `think` | `<\|think\|>` | `g10_slot_01`, in tokenizer v0.1 | Start of reasoning trace |
| `130824` | `think_end` | `<\|/think\|>` | `g10_slot_02`, in tokenizer v0.1 | End of reasoning trace |
| `130825` | `tool_call_end` | `<\|/tool_call\|>` | `g10_slot_03`, in tokenizer v0.1 | End of structured JSON tool call payload |
| `130826` | `tool_result_end` | `<\|/tool_result\|>` | `g10_slot_04`, in tokenizer v0.1 | End of tool execution output |
| `130827` | `subagent_call` | `<\|subagent_call\|>` | `g10_slot_05`, rename pending in G3 | Sub-agent / delegation invocation boundary |
| `130828` | `subagent_return` | `<\|subagent_return\|>` | `g10_slot_06`, rename pending in G3 | Sub-agent / delegation return boundary |

Tokenizer v0.1 (PR #173) renames `g10_slot_00` to `g10_slot_04`. `subagent_call` and `subagent_return` take `g10_slot_05` and `g10_slot_06`; G3 still has to rename those two. Slots `g10_slot_07` to `g10_slot_63` (IDs 130,829 to 130,885) stay reserved and unused. Do not add `<|eval_fp_*|>`: a fingerprint stays a plain-text canary in Team 9 eval data. The v0 numbers (`000` to `255`) were positions in G10's own list, not tokenizer IDs, and are no longer used.

---

## 3. Machine-Readable Table for Tokenizer Training (G3)

```text
129994 im_start <|im_start|>
130773 tool_call <|tool_call|>
130774 tool_result <|tool_result|>
130801 fim_prefix <|fim_prefix|>
130802 fim_middle <|fim_middle|>
130803 fim_suffix <|fim_suffix|>
130804 fim_pad <|fim_pad|>
130816 im_end <|im_end|>
130817 file_sep <|file_sep|>
130818 repo_name <|repo_name|>
130822 endoftext <|endoftext|>
130823 think <|think|>
130824 think_end <|/think|>
130825 tool_call_end <|/tool_call|>
130826 tool_result_end <|/tool_result|>
130827 subagent_call <|subagent_call|>
130828 subagent_return <|subagent_return|>
```

---

## 4. Dataset Pre-Training Sanity & Ghost Token Action

1. **StarCoder (`code-python` · Sai Teja)**: Strip upstream `B3` ghost tokens (`[INST]`, `[/INST]`, `<think>`, `### Assistant:`) during pre-processing so raw control markers are never learned from pre-training code comments.
2. **HPLT 3.0 (`ind-hi-hplt` · gmrammohan15)**: Verified clean. Devanagari script joiners `U+200D` (ZWJ) and `U+200C` (ZWNJ) retained as natural script characters.
3. **IndicCorpV2 (`ind-hi-indiccorp` · Ranjani)**: Verified clean. No ghost tokens found.
4. **FineWeb-2 Marathi (`ind-mr-fw2` · Amit T)**: Verified clean. Zero ghost tokens. ZWJ/ZWNJ preserved for Marathi orthography (`ऱ्या`, conjuncts).
5. **FineWeb-2 Kannada (`ind-kn-fw2` · Lokesh Arundathi)**: No new token request or allocation change. Preserve vowel sequences, ZWNJ (`U+200C`) and ZWJ (`U+200D`) as text, including the Unicode RA + ZWJ + virama order and its legacy alternative.
6. **StarCoder (`code-python` · f20201351h-maker, assigned 500-document pack)**: No ghost chat markers found (0 of 500 documents). Strip the StarCoder metadata prefix (`<reponame>`, `<filename>`, `<gh_stars>`, 272 documents) in cleaning. PII placeholders (`<NAME>`, `<EMAIL>`, `<PASSWORD>`, `<KEY>`) stay plain text. No new token request.
