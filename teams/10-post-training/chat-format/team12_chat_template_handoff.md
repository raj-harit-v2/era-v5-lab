# Hand-off to Team 12 (Quantization & Serving): Chat Template Specification

**Date:** Thursday 12 Nov 2026 (Delivered ahead of schedule on 3 Nov 2026)  
**Author:** Member A (`@Amit T` / `@thinkTinkerGreen`), Team 10 (Post-Training and Agentic)  
**Recipient:** Team 12 (Quantization and Serving)  
**Artifacts:** 
- `teams/10-post-training/chat-format/chat_template.jinja` (Canonical Template SSOT)
- Python validation suite: `teams/10-post-training/tests/test_chat_template.py`

---

## 1. Overview & Objective

This handoff provides Team 12 with the production-ready Jinja2 chat template (`chat_template.jinja`) matching G10's ChatML v0 specification on the frozen Team 3 tokenizer (BrahmicTokenizer-131K v0.1).

### Exact Paths for Team 12 Consumption:
- **Canonical Source Path (G10 SSOT)**:  
  `teams/10-post-training/chat-format/chat_template.jinja`
- **Recommended In-Team Destination Path for Team 12**:  
  `teams/12-quantization/tokenizer/chat_template.jinja`  
  *(or alternatively `teams/12-quantization/chat-format/chat_template.jinja`)*

> [!NOTE]
> Per repo `pr-guard.yml` rules (lines 52–54), non-markdown files within `teams/` must reside inside a topic subdirectory (depth $\ge 4$). Placing the template under `teams/12-quantization/tokenizer/` or `teams/12-quantization/chat-format/` ensures full compliance with PR Guard.

### Hand-off Note for Team 12 (`unsupported_parts.md`):
Team 12's tracking document [`teams/12-quantization/docs/unsupported_parts.md`](../../12-quantization/docs/unsupported_parts.md#L179) notes:  
`| Chat template | yes: Jinja in tokenizer.chat_template | yes | G10 sends it on 12 Nov; test it with llama-server and vLLM chat endpoints |`

The update for Sreekanth (`@SreekanthZipsy`) to reference this delivered artifact is:  
`| Chat template | yes: Jinja in tokenizer.chat_template | yes | G10 sent: teams/10-post-training/chat-format/chat_template.jinja (copy to teams/12-quantization/tokenizer/chat_template.jinja) |`

It is fully compatible with:
1. **Hugging Face `transformers` / `tokenizers`**: Embedded in `tokenizer_config.json` under `"chat_template"`.
2. **`vLLM`**: Passed via `--chat-template teams/10-post-training/chat-format/chat_template.jinja` (or locally via `--chat-template teams/12-quantization/tokenizer/chat_template.jinja`).
3. **`llama.cpp` / GGUF**: Embedded or passed via `--chat-template` during quantized GGUF inference (`llama-server`, `llama-cli`).

---

## 2. Tokenizer Delimiter & ID Mapping

Every chat marker is a single atomic special token in Team 3's vocabulary:

| Marker | Tokenizer ID | Surface | Semantic Function |
| :--- | :--- | :--- | :--- |
| `im_start` | `129994` | `<\|im_start\|>` | Start of conversation turn (`system`, `user`, `assistant`, `tool`) |
| `im_end` | `130816` | `<\|im_end\|>` | End of conversation turn |
| `endoftext` | `130822` | `<\|endoftext\|>` | End of transcript / generation boundary |
| `think` | `130823` | `<\|think\|>` | Opening delimiter for Chain-of-Thought reasoning trace |
| `think_end` | `130824` | `<\|/think\|>` | Closing delimiter for Chain-of-Thought reasoning trace |
| `tool_call` | `130773` | `<\|tool_call\|>` | Opening delimiter for structured JSON tool invocation |
| `tool_call_end` | `130825` | `<\|/tool_call\|>` | Closing delimiter for structured JSON tool invocation |
| `tool_result` | `130774` | `<\|tool_result\|>` | Opening delimiter for execution output returned by environment |
| `tool_result_end` | `130826` | `<\|/tool_result\|>` | Closing delimiter for execution output returned by environment |

> [!IMPORTANT]
> The base tokenizer token `<think>` (ID 128512) is **not** used. The chat template exclusively emits the atomic special token `<|think|>` (ID 130823).

---

## 3. Structural Rules & Turn Layout

1. **Reasoning Effort Header (Plain Text)**:
   - Effort is not a special token. It is specified as a plain-text line at the top of the first system turn:
     ```text
     <|im_start|>system
     Reasoning effort: 16k
     
     {optional system content}<|im_end|>
     ```
   - If no system message is provided in `messages`, the template synthesizes the system turn holding the default effort header (`Reasoning effort: 4k`).
   - Valid effort levels: `1k`, `4k`, `16k`, `64k`.

2. **Assistant Turn with Internal Reasoning & Tool Calls**:
   ```text
   <|im_start|>assistant
   <|think|>
   {internal chain of thought reasoning}
   <|/think|>
   <|tool_call|>
   {"arguments":{"path":"file.py"},"name":"read_file"}
   <|/tool_call|>
   {visible message content}<|im_end|>
   ```

3. **Tool Execution Return**:
   ```text
   <|im_start|>tool
   <|tool_result|>
   {raw tool output}
   <|/tool_result|><|im_end|>
   ```

4. **Generation Prompt (`add_generation_prompt=True`)**:
   - Appends `<|im_start|>assistant\n` so the model begins generating reasoning or response.
   - When `add_generation_prompt=False`, closes transcript with `<|endoftext|>`.

---

## 4. Usage Instructions for Team 12

### 4.1 Hugging Face Python Usage
```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("/path/to/model")
tokenizer.chat_template = open("teams/10-post-training/chat-format/chat_template.jinja").read()

prompt = tokenizer.apply_chat_template(
    messages=[
        {"role": "user", "content": "Write a Go function to compute Fibonacci numbers."}
    ],
    effort="16k",
    add_generation_prompt=True,
    tokenize=False
)
```

### 4.2 vLLM Serving
```bash
python -m vllm.entrypoints.openai.api_server \
    --model /path/to/quantized_model \
    --chat-template teams/10-post-training/chat-format/chat_template.jinja
```

### 4.3 llama.cpp CLI / Server
```bash
./llama-server \
    -m /path/to/model-Q4_K_M.gguf \
    --chat-template-file teams/10-post-training/chat-format/chat_template.jinja
```

---

## 5. Verification Status

The template has been tested against `teams/10-post-training/chat-format/render.py` across single-turn, multi-turn, tool-augmented, and reasoning-enabled conversations. Test suite: `pytest teams/10-post-training/tests/test_chat_template.py` (PASS).
