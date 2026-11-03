# Chat format v0

Team G10. ChatML-style template for Team 3 (G3 Tokenizer) and Team 12 (G12 Quantization and Serving) by Saturday 31 Oct.

## Core rule: special tokens for structure, plain text for values

Instructor ruling, 27 Oct (reply to the special-tokens discussion in the G10 chat):

- **Special tokens** only for structure that the model must never confuse with normal text: the start and end of each role turn, tool call start and end, tool result start and end, and thinking start and end.
- **Plain text** for values inside that structure: tool names, arguments, effort level, options and settings. A tool call is special tokens around plain-text JSON.
- Keep the special-token list short. Sai Teja owns the final list, and TSAI reviews it at the Gate.

Markers in `v0` (each is one atomic special token in the tokenizer, never split into pieces):

- Turn & document markers: `<|endoftext|>` (`130822`), `<|im_start|>` (`129994`), `<|im_end|>` (`130816`)
- Reasoning & tool markers: `<|think|>` (`130823`), `<|/think|>` (`130824`), `<|tool_call|>` (`130773`), `<|/tool_call|>` (`130825`), `<|tool_result|>` (`130774`), `<|/tool_result|>` (`130826`)

Effort is **not** a token. It is a plain-text line, `Reasoning effort: {level}`, at the top of the first system turn. Levels are `1k`, `4k`, `16k` and `64k` (budgets of `1024`, `4096`, `16384` and `65536` tokens covering think + tool trace, excluding the final visible reply).

- Plain-text XML look-alikes and Unicode homoglyphs (`<think>`, `</think>`, `<tool_call>`, `</tool_call>`, `<tool_result>`, `</tool_result>`, `<｜think｜>`, `＜think＞`) are strictly rejected by `render.py`.
- The 9 assigned markers and 59 remaining reserved G10 slots (64 slots total, IDs `130822..130885`) are listed in `teams/10-post-training/special-tokens/special_tokens_v1.md` aligned with Team 3 (G3 v0.1). Old `000..255` slot numbering is removed.

## Multi-Tier Context Hierarchy & RBAC Privilege Planes

In frontier agentic coding, context is structured into four deterministic tiers:
1. **Tier 0 (System Directives & RBAC Boundaries - P0):** Core model identity, safety guardrails, and reasoning effort conditioning line (`Reasoning effort: {level}`). Fixed by application host; untrusted user/tool data cannot alter.
2. **Tier 1 (Capabilities & Tool Registry - P0/P1):** Injected tool schemas, `SKILL.md` workflows, and capability descriptions formatted in structured JSON/Markdown.
3. **Tier 2 (Project & Workspace Map - P1):** Active git status, directory tree, and file boundaries (`<|file_sep|>`) defining the environment state.
4. **Tier 3 (Conversation History - P1):** Prior user requests and model interactions.
5. **Tier 4 (Working Memory & Execution - P2/P3):** Internal Chain-of-Thought reasoning traces (`<|think|>...<|/think|>`) and untrusted tool outputs (`<|tool_result|>...<|/tool_result|>`).

### Context Sizing & Effort Budgets
Reasoning effort budgets (`1k` = 1,024, `4k` = 4,096, `16k` = 16,384, `64k` = 65,536 tokens) constrain *only* the think span and tool trace. For a `64k` effort budget, the total serving context window must scale to at least **128k tokens** (aligned with Teams 3, 5, and 12).

## Turn structure

Roles are `system`, `user`, `assistant`, and `tool`.

1. **First turn is always `system`:**
   `<|im_start|>system\nReasoning effort: {level}\n\n{system content}<|im_end|>\n`
   If the transcript has no system message, the turn holds only the effort line. Other `system` and `user` turns are `<|im_start|>{role}\n{content}<|im_end|>\n`.
2. **`assistant` turn:**
   `<|im_start|>assistant\n`, then, in order and omitting empty optional sections:
   - Optional reasoning span wrapped in atomic special tokens: `<|think|>\n{think}\n<|/think|>\n`
   - Zero or more tool calls, each wrapped in atomic special tokens around plain-text JSON: `<|tool_call|>\n{"arguments":{...},"id":"...","name":"..."}\n<|/tool_call|>\n`
   - Optional visible reply text: `{content}`
   Closed by `<|im_end|>\n`.
   *(Tool calls optionally include an `"id"` field to deterministically bind parallel tool invocations).*
3. **`tool` turn:**
   `<|im_start|>tool\n<|tool_result|>\n{content}\n<|/tool_result|><|im_end|>\n` (tool output `content` is required).
4. **End of transcript:**
   `<|endoftext|>`

`render.py` renders messages to a string, `parse()` reconstructs the messages and effort level, and `tokenize_markers()` splits a rendered transcript into atomic Team 3 special-token IDs and text spans to verify that no marker is ever left as plain text.

One edge case: a first system message with empty content renders as the effort line only, so `parse()` returns no system message for it.

## Example

Effort `4k`.

```text
<|im_start|>system
Reasoning effort: 4k

You edit code and you report only what a tool returned.<|im_end|>
<|im_start|>user
test_add fails in calc.py. Fix add.<|im_end|>
<|im_start|>assistant
<|think|>
The return adds one too many.
<|/think|>
<|tool_call|>
{"arguments":{"path":"calc.py"},"name":"read_file"}
<|/tool_call|>
I am reading calc.py before editing it.<|im_end|>
<|im_start|>tool
<|tool_result|>
def add(a, b):
    return a + b + 1

<|/tool_result|><|im_end|>
<|im_start|>assistant
<|tool_call|>
{"arguments":{"patch":"return a + b","path":"calc.py"},"name":"apply_patch"}
<|/tool_call|>
Removed the extra increment.<|im_end|>
<|endoftext|>
```

## Tamil application — `ind-ta-sangraha-v`

The existing format and `render.py` apply to Tamil without language-specific control tokens. The examples below are newly authored demonstrations, not extracted Sangraha documents or approved training rows.

- Read and write UTF-8. Preserve content exactly, including combining sequences, pulli, ZWJ/ZWNJ if present, punctuation, mixed-script spans and whitespace. Rendering does not normalize, translate, repair or clean source text.
- Use the same `system`, `user`, `assistant`, `tool` role strings and the same nine markers. Tamil text belongs in content and tool JSON string values. `ta`, `tam`, effort values, tool names and arguments are plain text.
- For the current v0 demo, use one tool call followed by one tool result. The renderer does not preserve call IDs or tool-name metadata, so parallel tool/result correlation needs a later schema decision.

Example input to the shared Python module:

```python
messages = [
    {"role": "system", "content": "தமிழில் பதிலளி."},
    {"role": "user", "content": "தமிழ் உரையை UTF-8 கோப்பில் சேமி."},
    {"role": "assistant", "tool_calls": [
        {"name": "write_text", "arguments": {
            "path": "message.txt", "text": "தமிழ் மொழி"}}
    ]},
    {"role": "tool", "content": "UTF-8 write completed."},
    {"role": "assistant", "content": "தமிழ் உரை சேமிக்கப்பட்டது."},
]
text = render(messages, effort="4k")
assert parse(text) == {"effort": "4k", "messages": messages}
```

Rendered excerpt:

```text
<|im_start|>user
தமிழ் உரையை UTF-8 கோப்பில் சேமி.<|im_end|>
<|im_start|>assistant
<|tool_call|>
{"arguments":{"path":"message.txt","text":"தமிழ் மொழி"},"name":"write_text"}
<|/tool_call|>
<|im_end|>
<|im_start|>tool
<|tool_result|>
UTF-8 write completed.
<|/tool_result|><|im_end|>
```

### Supervision and validation boundaries

For a future SFT integration, mask system/user content and tool observations; supervise assistant replies and assistant-generated tool calls. The SWE demonstration contains no reasoning traces. This is a proposed training policy: `render.py` emits strings, not token-aligned labels or loss masks. A real tokenizer integration must define boundary labels and check the actual tokens.

`tokenize_markers()` checks the declared marker-to-slot mapping with a Python scanner. It does not prove G3's trained tokenizer registers markers atomically. Before the final handoff, G3 must verify each structural surface encodes as one intended ID and ordinary Tamil round-trips correctly. Effort values are metadata; the renderer does not measure or enforce their token budgets.

Current v0 rejects literal control markers inside message content and normalizes away empty optional fields and an empty first system message. Exact round-trip claims apply to the supported canonical message shape illustrated above.

### Executed Tamil SWE task

See `results/tamil_swe_e2e.md` and `swe-task/run_tamil_e2e.py`: a local UTF-8 file-writing bug, an actual failing test, a patch, an actual passing test and a fully round-tripped Tamil tool trajectory. This authored smoke task establishes the local serialization and tool-observation path; it is not an external SWE-bench score or a model-training run.

## Hindi application — `ind-hi-hplt`

The format and `render.py` apply to Hindi (Devanagari) unchanged, with no language-specific tokens. The examples are newly authored, not extracted from HPLT documents.

- Hindi text, the danda `।` and `॥`, nukta letters, ZWJ/ZWNJ and Hindi-English mixing (`Python में bug ठीक करें`) are plain content. They go in message content and tool JSON string values. `render.py` keeps Devanagari readable in tool JSON (no `\u` escapes).
- `render.py` itself does not normalize. The pre-tokenization step must not change Hindi either:
  - **Keep ZWJ (`U+200D`) and ZWNJ (`U+200C`).** They choose between a half form and a conjunct (`क्‍ष` vs `क्ष`). Removing them changes the written word.
  - **Do not apply NFKC to content.** It splits precomposed nukta letters (`ज़` `U+095B` becomes `ज` + `़`) and folds compatibility characters in mixed text (`10²` becomes `102`).
  - **Remove only `U+200B` and `U+FEFF`.** `render.py` alone does not reject a marker with a zero-width space inside (`<|th` + `U+200B` + `ink|>`), so this removal must run before rendering. After it, the hidden marker is rejected.
- The `ind-hi-hplt` pack has no precomposed nukta letters and no ZWJ/ZWNJ (0 of 500 documents), so it is not affected. Other Hindi sources will have them.
- `special_tokens_v1.md` now states this rule (no NFKC, keep ZWJ/ZWNJ). Its earlier draft asked for NFKC and removal of `U+200B..U+200D`, which conflicted with the per-pack note that ZWJ/ZWNJ are kept. The Hindi SWE task below tests the rule.

Example input to the shared Python module (effort `16k`, with a think span):

```python
messages = [
    {"role": "system", "content": "हिंदी में उत्तर दें।"},
    {"role": "user", "content": "फ़ाइल में \"क्\u200dष\" सहेजें।"},
    {"role": "assistant", "think": "ZWJ को नहीं हटाना है।", "tool_calls": [
        {"name": "write_text", "arguments": {"path": "शब्द.txt", "text": "क्\u200dष"}}]},
    {"role": "tool", "content": "UTF-8 में लिखा गया: 4 code points।"},
    {"role": "assistant", "content": "सहेज दिया।"},
]
text = render(messages, effort="16k")
assert parse(text) == {"effort": "16k", "messages": messages}
```

Rendered (ZWJ shown as `\u200d`; the actual string holds the character):

```text
<|im_start|>system
Reasoning effort: 16k

हिंदी में उत्तर दें।<|im_end|>
<|im_start|>user
फ़ाइल में "क्\u200dष" सहेजें।<|im_end|>
<|im_start|>assistant
<|think|>
ZWJ को नहीं हटाना है।
<|/think|>
<|tool_call|>
{"arguments":{"path":"शब्द.txt","text":"क्\u200dष"},"name":"write_text"}
<|/tool_call|>
<|im_end|>
<|im_start|>tool
<|tool_result|>
UTF-8 में लिखा गया: 4 code points।
<|/tool_result|><|im_end|>
<|im_start|>assistant
सहेज दिया।<|im_end|>
<|endoftext|>
```

### Executed Hindi SWE task (Docker)

See `results/hindi_swe_e2e.md`, `swe-task/run_hindi_e2e.py` and `swe-task/Dockerfile.hindi`. A `prepare_text()` written to the v1 pre-tokenization rule fails 4 of 6 Hindi tests. The repair keeps ZWJ/ZWNJ, drops NFKC and still removes `U+200B`, so all 6 pass. The trajectory has think spans and round-trips exactly at all four effort levels. It ran in Docker with no network. This is an authored smoke task, not a SWE-bench score or a model-generated trajectory.

## Go application: `code-go`

The existing format and `render.py` apply to Go source without language-specific tokens. The example is a newly authored demonstration, not a row from the `code-go` pack and not an approved training row.

- Go source goes in message content and in tool-call JSON string values. `gofmt` tabs, CRLF line endings, backticks and the channel operator `<-` are preserved exactly; `render.py` does not reformat or normalize code.
- A literal control marker inside Go source (for example `s := "<|im_start|>"` or `s := "<think>"`) is rejected by `render.py` at the input boundary, as for any other content. A real Go file with such a string must be dropped or escaped by the data step before it is rendered. This is an open point for the lead and TSAI; it is not decided here.
- StarCoder metadata markers (`<reponame>`, `<filename>`, `<gh_stars>`) are not chat markers, so the renderer treats them as ordinary text. They are removed upstream by the cleaning medicine for B3, so they should never reach a rendered transcript.
- Same roles, same nine markers, effort stays the plain line `Reasoning effort: {level}`. For SFT, mask system and user content and tool observations; supervise assistant replies and assistant tool calls (a proposed policy: `render.py` emits strings, not loss masks).

Rendered excerpt (effort `4k`), a tool turn that returns Go source:

```text
<|im_start|>tool
<|tool_result|>
// Package stats holds the small Go function used for the G10 Go SWE task.
package stats

// Sum returns the total of nums.
func Sum(nums []int) int {
	total := 0
	for i := 1; i < len(nums); i++ {
		total += nums[i]
	}
	return total
}

<|/tool_result|><|im_end|>
```

### Executed Go SWE task

See `results/go_swe_e2e.md`, `swe-task-go/` and `tests/test_go_chat_format.py`: a Go off-by-one bug in `Sum`, an actual failing `go test`, a patch, an actual passing `go test` and `go vet`, run in an air-gapped Docker container, and a 7-turn trajectory rendered and parsed with `render.py`. This is an authored smoke task, not an external SWE-bench score or a model-training run.

## Kannada application — `ind-kn-fw2`

Lokesh Arundathi — Kannada (`kn`), `HuggingFaceFW/fineweb-2`. The following conversation and SWE task are authored demonstrations, not extracted training rows.

- Use the existing roles and nine chat markers. Kannada, `kn`, tool names, JSON values and effort levels remain plain text. No new special tokens are requested.
- Preserve supplied UTF-8 code points, vowel sequences, whitespace and natural Kannada/English mixing without normalization.

### Authored Kannada example

Run from the repository root. The Python escape inserts an actual ZWNJ.

```python
from runpy import run_path

chat = run_path("teams/10-post-training/chat-format/render.py")
messages = [
    {"role": "system", "content": "ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ."},
    {"role": "user", "content": "ಒನ್\u200cಪ್ಲಸ್"},
    {"role": "assistant", "think": "ಪಠ್ಯವನ್ನು ಬದಲಿಸಬಾರದು.",
     "tool_calls": [{"name": "write_text", "arguments": {
         "path": "ಕನ್ನಡ.txt", "text": "ಒನ್\u200cಪ್ಲಸ್"}}]},
    {"role": "tool", "content": "ಉಳಿಸಲಾಗಿದೆ."},
    {"role": "assistant", "content": "ಉಳಿಸಲಾಗಿದೆ."},
]
text = chat["render"](messages, effort="4k")
assert chat["parse"](text) == {"effort": "4k", "messages": messages}
print(text)
```

```text
<|im_start|>system
Reasoning effort: 4k

ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ.<|im_end|>
<|im_start|>user
ಒನ್‌ಪ್ಲಸ್<|im_end|>
<|im_start|>assistant
<|think|>
ಪಠ್ಯವನ್ನು ಬದಲಿಸಬಾರದು.
<|/think|>
<|tool_call|>
{"arguments":{"path":"ಕನ್ನಡ.txt","text":"ಒನ್‌ಪ್ಲಸ್"},"name":"write_text"}
<|/tool_call|>
<|im_end|>
<|im_start|>tool
<|tool_result|>
ಉಳಿಸಲಾಗಿದೆ.
<|/tool_result|><|im_end|>
<|im_start|>assistant
ಉಳಿಸಲಾಗಿದೆ.<|im_end|>
<|endoftext|>
```

SWE and browser verification results are recorded in [the Kannada report](../results/kannada_swe_e2e.md). Joiner sequences are documented in the Kannada section of [the special-token notes](../special-tokens/special_tokens_v0.md).

## Python application: `code-python`

f20201351h-maker — `code-python` (`bigcode/starcoderdata`). The existing format and `render.py` apply to Python source without new tokens. The example below is newly written for this section, not a row from the `code-python` pack and not an approved training row. The team's executed SWE task (`results/swe_e2e.md`) is already a Python task, so this section adds no second one.

- Python source goes in message content and in tool-call JSON string values. Indentation, tabs, CRLF line endings, f-string braces, decorators and type hints (`->`) are preserved exactly; `render.py` does not reformat code.
- StarCoder metadata tags (`<reponame>`, `<filename>`, `<gh_stars>`) and StarCoder PII placeholders (`<NAME>`, `<EMAIL>`, `<PASSWORD>`, `<KEY>`) are not chat markers. `render.py` keeps them as ordinary text, and `tokenize_markers()` never maps them to a special-token ID. The metadata prefix is removed upstream by the `B3` cleaning medicine, so it should not reach a rendered transcript.
- A chat marker or a plain-text look-alike inside Python source (for example `s = "<|im_start|>"` or `s = "<think>"`) is rejected by `render.py`, as for any other content. The diagnosis scan found none of the scanned markers in this pack (0 of 500 documents).
- Same roles and markers; effort stays the plain line `Reasoning effort: {level}`.

Rendered excerpt (effort `4k`), a tool turn that returns a Python file with StarCoder PII placeholders:

```text
<|im_start|>tool
<|tool_result|>
DB_USER = "<NAME>"
DB_EMAIL = "<EMAIL>"


def dsn(host: str) -> str:
    return f"{DB_USER}@{host}"

<|/tool_result|><|im_end|>
```

Checked by `tests/test_code_python_chat_format.py`.
