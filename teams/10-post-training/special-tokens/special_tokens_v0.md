# Special tokens v0

Shared G10 special-token file (`teams/10-post-training/special-tokens/special_tokens_v0.md`). Due Wednesday 28 Oct, and sent to the Tokenizer team (**Team 3 / G3**) by **Saturday 31 Oct** so G3 reserves all 256 token IDs before tokenizer training starts on 1 Nov. Team 9 delivers fingerprints v1 on 28 Oct.

## Rule for ChatML `v0` markers (G10 -> G3 handoff)

- **ChatML style is used for `v0`.**
- **Instructor ruling, 27 Oct:** special tokens only for structure that the model must never confuse with normal text (role-turn start and end, tool call start and end, tool result start and end, thinking start and end). Values inside that structure are plain text: tool names, arguments, effort level, options and settings. Keep the list short; the lead owns the final list and TSAI reviews it at the Gate.
- **Every marker below must be one atomic special token** in the tokenizer, never split into subword pieces, and plain-text tags like `<think>` or `<tool_call>` are rejected.
- **256 reserved token IDs (`0..255`):** G3 reserves the full 256-ID block. Assigned IDs below are frozen; unassigned IDs in `0..255` are reserved (`<|reserved_003|>` .. `<|reserved_255|>`).
- **TSAI decision for v0:** do not add `<|eval_fp_*|>` special tokens. IDs `021` to `023` stay reserved and unused. A fingerprint is a plain-text canary that Team 9 places in eval data. A special token cannot appear in ordinary text, so the contamination check would find nothing. If Team 9 later needs a reserved ID, these three IDs are free.
- **Security & token smuggling defense (G3 Tokenizer guidance):**
  - **Unicode Normalization:** Pre-tokenization pipeline must enforce Unicode NFKC normalization to prevent homoglyph attacks (e.g., Cyrillic or fullwidth `<｜think｜>`) from smuggling past prompt filters.
  - **Roadmap for reserved slots (`003..009`, `017..023`, `030..255`):**
    - Code Infilling (FIM): Slots `010..012` allocated for `<|fim_prefix|>`, `<|fim_middle|>`, `<|fim_suffix|>` for agentic surgical code repairs; slot `016` holds `<|fim_pad|>` (instructor, 28 Oct: reserve all four FIM tokens).
    - Repository Context: Slots `013..014` allocated for `<|repo_name|>`, `<|file_sep|>` for multi-file workspace mapping.
    - Delegation: Slots `015`, `020` allocated for sub-agent invocation (`<|subagent_call|>`, `<|subagent_return|>`).
    - IDs `021` to `023` stay reserved and unused. Do not assign them to an eval fingerprint token.

## Team workflow (Core Team · 12 members)

- Keep this **one shared file** (`teams/10-post-training/special-tokens/special_tokens_v0.md`).
- Each of the 12 G10 Core Team members has their own dataset section below (for example `StarCoder`, `Stack Exchange`, `Indic web`).
- Each member adds the markers of their own dataset in their own section by pull request to the lead's branch (`g10-week1-post-training`).
- The team lead (Sai Teja) merges the member PRs, removes duplicates in the consolidated 256-token table, and opens one PR to `theschoolofai/era-v5-lab` `main`.

---

## Consolidated 256-token block for Team 3 (G3)

TSAI reserves 256 token IDs (`0..255`). Every chat marker below is registered as **one special token** in the tokenizer, never plain text:

| Token ID | Name | Special token surface (atomic) | Role in ChatML `v0` |
| --- | --- | --- | --- |
| `000` | `endoftext` | `<\|endoftext\|>` | End of document / transcript |
| `001` | `im_start` | `<\|im_start\|>` | Start of a ChatML turn |
| `002` | `im_end` | `<\|im_end\|>` | End of a ChatML turn |
| `010` | `fim_prefix` | `<\|fim_prefix\|>` | Fill-In-The-Middle prefix anchor for code infilling |
| `011` | `fim_middle` | `<\|fim_middle\|>` | Fill-In-The-Middle middle target slot for code infilling |
| `012` | `fim_suffix` | `<\|fim_suffix\|>` | Fill-In-The-Middle suffix context anchor |
| `013` | `repo_name` | `<\|repo_name\|>` | Repository / package identifier anchor in multi-file context |
| `014` | `file_sep` | `<\|file_sep\|>` | Multi-file boundary delimiter in workspace repo map |
| `015` | `subagent_call` | `<\|subagent_call\|>` | Sub-agent / delegation invocation boundary |
| `016` | `fim_pad` | `<\|fim_pad\|>` | Fill-In-The-Middle padding token for batched infilling sequences |
| `020` | `subagent_return` | `<\|subagent_return\|>` | Sub-agent / delegation return boundary |
| `024` | `think` | `<\|think\|>` | Start of reasoning trace (1 special token, never plain `<think>`) |
| `025` | `think_end` | `<\|/think\|>` | End of reasoning trace (1 special token, never plain `</think>`) |
| `026` | `tool_call` | `<\|tool_call\|>` | Start of tool call JSON payload (1 special token) |
| `027` | `tool_call_end` | `<\|/tool_call\|>` | End of tool call JSON payload (1 special token) |
| `028` | `tool_result` | `<\|tool_result\|>` | Start of tool output span inside a tool turn (1 special token) |
| `029` | `tool_result_end` | `<\|/tool_result\|>` | End of tool output span inside a tool turn (1 special token) |

Machine-readable list of assigned markers for G3 (`ID Name Surface`):

```text
000 endoftext <|endoftext|>
001 im_start <|im_start|>
002 im_end <|im_end|>
010 fim_prefix <|fim_prefix|>
011 fim_middle <|fim_middle|>
012 fim_suffix <|fim_suffix|>
013 repo_name <|repo_name|>
014 file_sep <|file_sep|>
015 subagent_call <|subagent_call|>
016 fim_pad <|fim_pad|>
020 subagent_return <|subagent_return|>
024 think <|think|>
025 think_end <|/think|>
026 tool_call <|tool_call|>
027 tool_call_end <|/tool_call|>
028 tool_result <|tool_result|>
029 tool_result_end <|/tool_result|>
```

All remaining 239 IDs in `0..255` (`003..009`, `017..019`, `021..023`, `030..255`) are reserved by TSAI as `<|reserved_003|>` through `<|reserved_255|>`. IDs `021` to `023` stay unused.

### Effort levels (plain text, not tokens)

Effort is a plain-text line at the top of the first system turn: `Reasoning effort: {level}`. IDs `017..019` are free again and stay reserved (`016` is `<|fim_pad|>`).

- `1k`: 1024 tokens
- `4k`: 4096 tokens
- `16k`: 16384 tokens
- `64k`: 65536 tokens

The budget covers the think span and the tool trace. It does not cover the visible reply.

---

## Dataset sections by G10 Core Team member (12)

### 1. Sai Teja (Lead) — StarCoder (`code-python` · `bigcode/starcoderdata`)

- **Core team:** 10. Post-training and Agentic (Lead) · **Week 2:** 9. Evaluation · **Week 3:** 12. Quantization and Serving
- **Pack:** `code-python`
- **Language:** `Code`
- **Source:** `bigcode/starcoderdata`
- **Licence decision:** `TSAI reserves` (commercial-use data only)
- **Chat & ghost markers found in dataset (`B3`):** `<|endoftext|>`, `<|im_start|>`, `<|im_end|>`, `[INST]`, `[/INST]`, `### Assistant:`, `<think>`, `</think>`
- **Dataset-specific markers in `bigcode/starcoderdata`:**
  - Repository & file headers: `<reponame>`, `<filename>`, `<gh_stars>`
  - Notebook markers: `<jupyter_start>`, `<jupyter_text>`, `<jupyter_code>`, `<jupyter_output>`, `<empty_output>`
  - Commit & issue markers: `<commit_before>`, `<commit_msg>`, `<commit_after>`, `<issue_start>`, `<issue_comment>`
  - Redaction placeholders: `<NAME>`, `<EMAIL>`, `<KEY>`, `<PASSWORD>`
- **Action:** Strip `B3` ghost chat markers from pre-training text so the model never learns to emit control markers as plain text; register every ChatML `v0` marker above as **one special token** in G3's tokenizer.

### 1b. Sai Teja (Lead) — Chandassu (`BodduSriPavan111/chandassu`)

- **Core team:** 10. Post-training and Agentic (Lead) · **Week 2:** 9. Evaluation · **Week 3:** 12. Quantization and Serving
- **Pack:** `chandassu`
- **Language:** Telugu (`te`)
- **Source:** `BodduSriPavan111/chandassu`
- **Licence decision:** `TSAI reserves` (MIT on the dataset card; commercial use allowed)
- **Chat markers found:** none. No `<|im_start|>`, `<|im_end|>`, `<|endoftext|>`, `[INST]`, `<think>`, or `<tool_call>` in the 4,651 poems.
- **Not a special token:** `_x000D_` (1,134 Vemana poems). It is an exported carriage return left as plain letters. Strip it in cleaning. Do not give it a token id.
- **Not markers:** the hyphen in Andhranaayaka and the danda `।` in Laavanya are the yati pause, plain text. `U+200C` ZWNJ and `U+200D` ZWJ are part of Telugu writing (1,014 poems). Do not reserve them.
- **New token request:** none. The ChatML `v0` block above already covers this dataset. No assigned id is added or renumbered.

### 2. Ajay Kumar — JavaScript / TypeScript (`code-js-ts` · `bigcode/starcoderdata`)

- **Core team:** 10. Post-training and Agentic
- **Pack / Language / Source:** `code-js-ts` / Code (JavaScript / TypeScript) / `bigcode/starcoderdata` (JavaScript + TypeScript subsets, 500-document pack: 250 JavaScript, 250 TypeScript)
- **Licence decision:** `TSAI reserves`; see the `code-js-ts` licence entry.
- **Chat & ghost markers found in dataset (`B3`):** none in all 500 documents. Checked by known patterns and open-ended catalogues, all 0 hits:
  - known formats: ChatML / Llama-3 style `<|...|>` (also fullwidth `<｜...｜>`), `[INST]` / `[/INST]`, `<<SYS>>`, `<s>` / `</s>`, `<think>`, `<tool_call>`, `<tool_result>`, `<unk>` / `<pad>` / `<mask>` / `<bos>` / `<eos>`, SentencePiece `▁`, and `<|reserved_NNN|>`;
  - catalogues: open-ended `<|...|>` pattern, `[UPPERCASE]` tags, `<UPPERCASE_WORD>` pattern, line-initial role prefixes (`### Instruction:`, `### Assistant:`, `### Response:`, `User:`, `System:`), HTML-escaped forms (`&lt;think&gt;`, `&lt;im_start&gt;`).
  - One `System:` match was found and classified as ordinary code: it is a substring of the TypeScript parameter declaration `energySystem: EnergySystem<T>`, not a role prefix.
- **Dataset-specific markers in `bigcode/starcoderdata` (JavaScript / TypeScript subset) — found; they are values, not structure:** 245 of 500 documents contain a StarCoder metadata prefix: `<reponame>` (101 documents), `<filename>` (105), `<gh_stars>` (107). An offset check confirmed that each of these 245 documents begins with one of the tags at byte offset 0. Per the instructor ruling (27 Oct) they are plain text and must not receive a token id. Recommend stripping them in pre-training cleaning (B3), pending pipeline owner confirmation, consistently across packs. No notebook markers (`<jupyter_*>`, `<empty_output>`) and no commit or issue markers (`<commit_*>`, `<issue_*>`) occur in this pack.
- **Redaction placeholders — not tokens:** 30 of 500 documents contain placeholder-like values — `<NAME>` (25 occurrences, 14 documents), `<EMAIL>` (29 occurrences, 10 documents), `<PASSWORD>` (14 occurrences, 10 documents), and `<KEY>` (13 occurrences, 3 documents). These surfaces are treated as ordinary text, not tokenizer control tokens. Most appear consistent with pipeline redaction placeholders; however, the nine `<KEY>` occurrences in `placekeyIsValid('<KEY>')` remain somewhat ambiguous. One `<PASSWORD>` occurrence is inside a quoted Doxygen anchor hash. Two documents (`6d3b68ef0b39f910`, `37390a3a6ca4502c`) contain `<PASSWORD>` in unquoted JavaScript expression contexts (e.g. `sendKeys(<PASSWORD>)`, `this.password = <PASSWORD>`); these are potential syntax-break candidates identified by lexical context inspection and should be flagged for pipeline review.
- **Not special tokens — TypeScript generic syntax:** `<SECONDARY_STRUCTURE_SECTION>`, `<RESIDUE_TYPE>`, and `<UUID>` matched the open-ended uppercase-bracket scanner. All were confirmed as ordinary TypeScript generic type parameters (e.g. `createContainerReducer<SECONDARY_STRUCTURE_SECTION>(...)`), not control markers or PII placeholders.
- **Unicode findings:** one document (`91cf7be64838e0d0`) carries a BOM `U+FEFF` at offset 101, immediately after its StarCoder metadata prefix, at the start of the TypeScript source file. No ZWJ, ZWNJ, ZWSP, SentencePiece `▁` (U+2581), replacement character (`U+FFFD`) or full-width delimiter variants occur in any of the 500 documents. Handle BOM in text cleaning (G4), not in the tokenizer vocabulary.
- **New special-token request:** none. No new special-token markers were identified in this dataset audit. No token ID addition, reassignment or renumbering is requested.
- **Action:** keep `B3` stripping in pre-training cleaning (nothing to strip from ghost markers in this pack); strip or keep the `<reponame>` / `<filename>` / `<gh_stars>` prefix consistently and pending pipeline owner confirmation; flag the two syntax-break documents for review; preserve TypeScript generic syntax and redaction placeholders as plain text; flag the document containing U+FEFF for BOM handling during G4 text cleaning — no tokenizer allocation is required.

### 3. Amit T — Indic web (`ind-mr-fw2` · FineWeb-2 Marathi)

- **Pack / Language / Source:** `ind-mr-fw2` — Marathi (`mr`) — `HuggingFaceFW/fineweb-2` (`data/mr/`)
- **Dataset markers & script diagnosis:**
  - Zero ChatML-style ghost markers (`<|im_start|>`, `<|endoftext|>`, `<think>`, `<|tool_call|>`) found in the 500-document diagnosis sample. The pack consists of curated web and prose text, not conversational traces.
  - Script joiners: `U+200D` (Zero Width Joiner, ZWJ) and `U+200C` (Zero Width Non-Joiner, ZWNJ) are vital Marathi orthographic characters (governing eyelash-ra `ऱ्या` conjunct formations and virama ligatures). Per `diagnosis/DISEASES.md`, these are valid text characters, **not** special tokens or anomalies. Must be preserved as standard text by G3's tokenizer.
  - Latin code-mixing: Natural technical and proper-noun English terms (`Diabetes`, `COVID19`, URLs) occur without special-token requirements.
  - Mojibake & punctuation anomalies (e.g. ASCII pipe `|` used as danda) handled at text-cleaning stage (G4), not in tokenizer vocabulary.
  - **Action:** No ghost markers to strip; keep ZWJ/ZWNJ as standard characters in vocabulary. Confirmed clean for ChatML v0.
- **New special-token allocations contributed by Amit T:**
  In addition to verifying dataset cleanliness, Amit T contributes the allocation of 10 new special tokens carved out from the reserved block for code infilling, repository context, sub-agent orchestration, and evaluation fingerprinting:
  - **Fill-In-The-Middle (FIM) Code Infilling (Slots `010..012`):**
    - `010 fim_prefix <|fim_prefix|>`: Code infilling prefix context anchor.
    - `011 fim_middle <|fim_middle|>`: Infilling generation slot.
    - `012 fim_suffix <|fim_suffix|>`: Suffix context anchor.
    - `016 fim_pad <|fim_pad|>`: FIM padding token (added after the instructor approved all four FIM tokens; not part of the original PR #5 allocation).
  - **Repository & Workspace Context (Slots `013..014`):**
    - `013 repo_name <|repo_name|>`: Multi-file repository boundary.
    - `014 file_sep <|file_sep|>`: Multi-file separation delimiter.
  - **Sub-Agent Delegation (Slots `015`, `020`):**
    - `015 subagent_call <|subagent_call|>`: Multi-agent delegation invocation.
    - `020 subagent_return <|subagent_return|>`: Multi-agent response boundary.
  - **Evaluation fingerprints:** not registered. TSAI decision for v0: do not add `<|eval_fp_*|>`. IDs `021` to `023` stay reserved and unused. Team 9 keeps any canary as a plain-text string in eval data.
  - **Decision:** `TSAI reserves`. All remaining unassigned slots (`003..009`, `017..023`, `030..255`) remain reserved `<|reserved_NNN|>`.

### 4. f20201351h-maker — StarCoder (`code-python` · `bigcode/starcoderdata`, assigned 500-document pack)

- **Core team:** 10. Post-training and Agentic · **Week 2:** 11. Release · **Week 3:** 6. Performance and Kernels
- **Pack / Language / Source:** `code-python` (500 Python files, median 2.8k chars) / `Code` (Python) / `bigcode/starcoderdata`
- **Method:** pattern scan of all 500 documents for chat and ghost markers, and exact counts of the StarCoder tags.
- **Chat and ghost markers (`B3`):** **0** in all 500 documents of this pack for the patterns scanned: `<|im_start|>`, `<|im_end|>`, `<|endoftext|>`, `<|fim_*|>`, `[INST]`, `[/INST]`, `### Assistant:`, `### Human:`, `### User:`, `<think>` and `</think>`.
- **StarCoder metadata prefixes (`B3`):** **272 of 500** documents start with metadata tags at offset 0: `<reponame>` 115, `<filename>` 118, `<gh_stars>` 106 (one document can carry several).
- **StarCoder PII placeholders:** **83 of 500** documents: `<NAME>` 55, `<EMAIL>` 42, `<PASSWORD>` 16, `<KEY>` 3. In 7 documents a placeholder breaks the Python syntax (for example `password=<PASSWORD>,`).
- **Not special tokens:** all the StarCoder tags and placeholders above. They are dataset text, not chat or control markers.
- **Proposal for G3:**
  - No new token request from this pack.
  - Strip the metadata prefix in cleaning (`B3`, 272 documents). Do not add tokens for it.
  - The PII placeholders stay ordinary text for the tokenizer, never special tokens. `<EMAIL>` matches TSAI's typed-placeholder rule for personal data; whether `<NAME>`, `<PASSWORD>` and `<KEY>` stay as they are is a question for TSAI. Drop the 7 files whose syntax they break.

### 5. Ashish Kamble — Dataset section *(placeholder for PR to `g10-week1-post-training`)*

- **Pack / Language / Source:** *(to be added by Ashish Kamble via PR)*
- **Dataset markers:** *(to be added by Ashish Kamble via PR; deduplicated into consolidated list on merge)*


### 6. Hema Varshini Palpandian — Tamil (`ind-ta-sangraha-v`)

- **Pack / Language / Source:** `ind-ta-sangraha-v` / Tamil (`ta`; source split `tam`) / `ai4bharat/sangraha`, Verified Tamil subset.
- **Marker scan (27 October 2026):** Scanned all 500 documents, with no null text. No matches for the 256 token surfaces in the list used for this scan or the tested chat/tool marker patterns. Two broader bracket-pattern matches were classified by a local context check as timezone annotations beside timestamps. These findings cover the automated checks on this sample.
- **Unicode findings:** Tamil characters occur in all 500 documents. No ZWJ, ZWNJ, other format-control or private-use characters were detected.
- **Text handling:** Preserve Tamil letters, vowel signs, pulli (`்`, U+0BCD), punctuation, line breaks, indentation and natural Tamil/English mixing. Preserve ZWJ/ZWNJ if encountered in other samples. Rendering should preserve the supplied text.
- **New special-token request:** None based on this sample. The existing shared chat markers cover the identified structural needs. Language labels such as `ta` and `tam` remain plain text.
- **Tool-result markers:** Use the shared `<|tool_result|>` and `<|/tool_result|>` markers, listed at slots `028` and `029` in the reviewed format. No duplicate markers are requested.


### 7. Lokesh Arundathi — Kannada (`ind-kn-fw2`)

- **Pack / Language / Source:** `ind-kn-fw2` / Kannada (`kn`) / `HuggingFaceFW/fineweb-2`.
- **Licence decision:** `TSAI reserves`; see the Kannada licence entry.
- **Not special tokens:** Kannada letters, dependent vowel signs, virama `U+0CCD`, ZWNJ `U+200C`, ZWJ `U+200D`, punctuation, mixed-script words and `kn` remain ordinary text.
- **Preservation:** keep supplied sequences unchanged. OnePlus (`ಒನ್‌ಪ್ಲಸ್`) is the verified ZWNJ example. The RA/ZWJ checks cover `0CB0 200D 0CCD 0C95` and legacy `0CB0 0CCD 200D 0C95`; preserve both orders.
- **Preprocessing:** the Kannada SWE helper removes only `U+200B`/`U+FEFF` before marker checking, without NFKC or script-joiner removal.
- **New special-token request:** none. Existing chat structure covers everything.

### 8. gmrammohan15 — Indic web (`ind-hi-hplt` · HPLT 3.0 `hin_Deva`)

- **Pack / Language / Source:** `ind-hi-hplt` / `Hindi` / HPLT 3.0 (`data.hplt-project.org/three/sorted/hin_Deva`)
- **Chat & ghost markers found in dataset (`B3`):** none in all 500 documents. Checked by known patterns and by open-ended catalogues, all 0 hits:
  - known formats: ChatML / Llama-3 style `<|...|>` (also fullwidth `<｜...｜>`), `[INST]` / `[/INST]`, `<<SYS>>`, `<s>` / `</s>`, `<think>`, `<tool_call>`, `<tool_result>`, `<unk>` / `<pad>` / `<mask>` / `<bos>` / `<eos>`, `[CLS]` / `[SEP]` / `[MASK]`, SentencePiece `▁`, StarCoder-style `<reponame>`, `<jupyter_*>`, `<commit_*>`, `<issue_*>`;
  - catalogues: every `<...>` token without spaces (none exist), every `[UPPERCASE]` tag (none), HTML-escaped `&lt;...&gt;` (none), line-initial role prefixes in English and Hindi (`User:`, `Assistant:`, `System:`, `Human:`, `### Instruction:`, `उपयोगकर्ता:`, `सहायक:` ...), and every invisible or private-use code point (none).
  - Only 3 documents contain `<` at all: a chemistry equation, a `<3` emoticon, and legacy-font garbage.
- **Dataset-specific markers:** none. `प्रश्न 1:` / `उत्तर:` lines (3 documents) are FAQ sections written by the site, natural Q&A text, not chat markers. Stray HTML tag endings (`/>` in 3 documents, `B2`) are web residue cleaned as text, not reserved as tokens.
- **Not markers:** `U+200D` ZWJ and `U+200C` ZWNJ are part of Indic script (they control conjunct shaping), not special tokens or diseases. They do not occur in this pack (0 of 500 documents), but other Hindi sources will have them and the tokenizer must keep them.
- **New token request:** none. The ChatML `v0` block above covers everything needed for this dataset.
- **Action:** keep `B3` stripping in pre-training cleaning (nothing to strip in this pack); keep ZWJ/ZWNJ untouched.

### 9. Ranjani Chandrasekaran — Indic web (`ind-hi-indiccorp`)

- **Pack / Language / Source:** `ind-hi-indiccorp` — Hindi (`hi`) — `ai4bharat/IndicCorpV2` (`data/hi-{1,2,3}.txt`)
- **Dataset markers:** No ChatML-style ghost markers (`<|im_start|>`, `<|endoftext|>`, `<think>`, `<|tool_call|>`) found in the 500-document diagnosis sample. The pack is news/web prose, not chat data.
  - `U+200D` ZWJ and `U+200C` ZWNJ appear as legitimate Devanagari script joiners — per `diagnosis/DISEASES.md` these are valid text characters, **not** special tokens or diseases. Keep as plain text in the tokenizer.
  - Mojibake residue found in some documents: `ज़्` (ja + nukta + virama) where `र्` or `ड़` is expected — corpus damage (G1), not a marker.
  - Latin-script spans in otherwise-Hindi text (`Reverse osmosis`, `COVID19`, `WWE`, `USIBC`) and URLs — normal text, no special-token need.
  - **Action:** none required to strip ghost markers from this pack. Confirmed clean for ChatML v0.


### 10. Ravi Naik — Dataset section *(placeholder for PR to `g10-week1-post-training`)*

- **Pack / Language / Source:** *(to be added by Ravi Naik via PR)*
- **Dataset markers:** *(to be added by Ravi Naik via PR; deduplicated into consolidated list on merge)*

### 11. Syed Abdul — Dataset section *(placeholder for PR to `g10-week1-post-training`)*

- **Pack / Language / Source:** *(to be added by Syed Abdul via PR)*
- **Dataset markers:** *(to be added by Syed Abdul via PR; deduplicated into consolidated list on merge)*

### 12. Vikash Ranjan — Rust (`code-rust` · `bigcode/starcoderdata`)

- **Pack / Language / Source:** `code-rust` / Rust / `bigcode/starcoderdata` (Rust subset, 500-document pack)
- **Licence decision:** `TSAI reserves`; see the Rust licence entry.
- **Chat & ghost markers found in dataset (`B3`):** none in all 500 documents. Checked by known patterns and by open-ended catalogues, all 0 hits:
  - known formats: ChatML / Llama-3 style `<|...|>` (also fullwidth `<｜...｜>`), `[INST]` / `[/INST]`, `<<SYS>>`, `<s>` / `</s>`, `<think>`, `<tool_call>`, `<tool_result>`, `<unk>` / `<pad>` / `<mask>` / `<bos>` / `<eos>`, SentencePiece `▁`, and `<|reserved_NNN|>`;
  - catalogues: line-initial role prefixes (`### Instruction:`, `### Assistant:`, `### Response:`, `User:`, `System:`).
- **Dataset-specific markers in `bigcode/starcoderdata` (Rust subset) — found; they are values, not structure:** 225 of 500 documents open with a StarCoderData header line: `<reponame>` (75 documents), `<filename>` (105), `<gh_stars>` (97), for example `e016447055203614` and `d1e5237063713aba`. Per the instructor ruling (27 Oct) they are plain text and must not get a token id. Strip them in pre-training cleaning or keep them as plain text, consistently across packs. No notebook markers (`<jupyter_*>`, `<empty_output>`) and no commit or issue markers (`<commit_*>`, `<issue_*>`) occur in this pack.
- **Redaction placeholders — not tokens:** 18 documents carry the pipeline's PII placeholders — `<NAME>` (13), `<EMAIL>` (9), `<KEY>` (1), `<PASSWORD>` (1). Keep them as plain text; they mark where the anonymizer replaced a value and must not enter the vocabulary.
- **Not special tokens — Rust syntax:** the turbofish `::<` (121 documents, for example `Vec::<u8>::new()`), generic parameters `<T>` and `<'a>`, comparison operators, and rustdoc HTML tags (`<div>`, `<p>`, `<b>` in 368 documents) are ordinary code text. HTML entities `&lt;` / `&gt;` / `&amp;` (2 documents) are plain text as well. The tokenizer must neither split nor reserve any of them.
- **Unicode findings:** one document (`2faccaa1d7a77d70`) carries a BOM `U+FEFF` at the start of the code body, immediately after its `<gh_stars>0` header line. No ZWJ, ZWNJ, ZWSP, replacement character (`U+FFFD`) or private-use characters occur anywhere else in the 500 documents. Keep BOM handling in the text-cleaning stage (G4), not in the tokenizer vocabulary.
- **New special-token request:** none. The shared ChatML `v0` block covers this dataset. The four FIM slots (`010..012`, `016`) already reserved cover agentic Rust edits; no id is added or renumbered.
- **Tool-result markers:** use the shared `<|tool_result|>` and `<|/tool_result|>` markers at slots `028` and `029`. Rust compiler and `cargo test` output arrives as tool results, so it stays plain text inside those spans. No duplicate markers requested.
- **Action:** keep `B3` stripping in pre-training cleaning (nothing to strip in this pack); strip or keep the `<reponame>` / `<filename>` / `<gh_stars>` header line consistently; preserve Rust syntax, rustdoc HTML and the redaction placeholders as plain text.
