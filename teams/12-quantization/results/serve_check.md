# Serving check: Qwen3-4B-Instruct-2507 (stand-in)

2026-11-15 14:58 UTC · vLLM 0.33.0 · GPU Tesla T4, 15360 MiB, 7.5; Tesla T4, 15360 MiB, 7.5 · model `/kaggle/tmp/models/Qwen3-4B-Instruct-2507`

## Result

- **Requests:** 100/100 returned HTTP 200.
- **Fields (the serving check): PASS.** 98/100 answers have no chat marker in `content`, `reasoning` or tool arguments. Every other answer was replayed (raw text regenerated, parsed offline by g10_parsers): model broke the G10 layout and the parser placed it as specified: 2; parser fault or not explained: 0.
- **Reasoning in `message.reasoning`:** 25/25 reason prompts.
- **Tool calls in `message.tool_calls`:** 28/30 tool prompts call the expected tool with valid JSON arguments.
- **No tool call when none is needed:** 20/20 (tool_result + no_tool prompts).
- **Streaming matches non-streaming:** 19/20 streamed prompts give the same reasoning, content and tool calls.
- **Model fell back to its own markers** (`<think>`, `<tool_call>`): 0/100 answers. That is model behaviour, not a parser fault.

## Per category

| Category | n | HTTP 200 | fields ok | expected behaviour | answer right | reasoning present | tool calls | p50 latency s | p95 latency s | completion tokens (mean) |
|---|---|---|---|---|---|---|---|---|---|---|
| chat | 25 | 25/25 | 25/25 | 20/25 | - | 25/25 | 0/25 | 8.31 | 34.02 | 465 |
| reason | 25 | 25/25 | 25/25 | 25/25 | 25/25 | 25/25 | 0/25 | 4.11 | 5.71 | 134 |
| tool | 30 | 30/30 | 30/30 | 28/30 | - | 30/30 | 28/30 | 2.96 | 4.25 | 88 |
| tool_result | 10 | 10/10 | 10/10 | 10/10 | 7/8 | 0/10 | 0/10 | 0.94 | 2.46 | 26 |
| no_tool | 10 | 10/10 | 8/10 | 10/10 | - | 2/10 | 0/10 | 1.39 | 24.64 | 148 |

## Time and cost

- Server start to ready: 165 s. 100 prompts at concurrency 8: 96.9 s. Streamed copies: 41.7 s. Replays: 7.3 s. Total: 312 s.
- Output: 19333 completion tokens, 199.5 tokens/s (all requests together, non-streamed pass).
- GPU time: 0.173 GPU-hours (2 GPU); cost at $0.0/GPU-hour: $0.0.

## Prompts not as expected

| id | lang | what |
|---|---|---|
| chat-02 | en | stream differs |
| chat-06 | en | empty content (finish length) |
| chat-16 | ta | empty content (finish length) |
| chat-17 | ta | empty content (finish length) |
| chat-19 | te | empty content (finish length) |
| chat-20 | te | empty content (finish length) |
| tool-29 | en | expected get_time, got no call |
| tool-30 | te | expected get_time, got no call |
| no_tool-04 | en | marker in a field (model broke the G10 layout: think block after the answer): `<|/think|>` `<|think|>` |
| no_tool-10 | te | marker in a field (model broke the G10 layout: think block after the answer): `<|/think|>` `<|think|>` |

## Setup

- Chat template `teams/10-post-training/chat-format/chat_template.jinja` (sha256 `1b9c0eded4c3`), parsers `teams/12-quantization/serving/g10_parsers.py` (sha256 `2940f0378de9`), prompts `teams/12-quantization/serving/prompts_v1.jsonl` (sha256 `1a7ab0dde274`).
- temperature 0.0, seed 0, max_tokens 1024, format hint on, tools in system message True, `skip_special_tokens: false` on every request.
- Versions: {"python": "3.12.3", "vllm": "0.33.0", "torch": "2.14.0", "transformers": "5.20.2"}.
- Server: `/kaggle/tmp/venv-vllm/bin/vllm serve /kaggle/tmp/models/Qwen3-4B-Instruct-2507 --served-model-name Qwen3-4B-Instruct-2507 --host 127.0.0.1 --port 8000 --seed 0 --chat-template /kaggle/tmp/era-v5-lab/teams/10-post-training/chat-format/chat_template.jinja --reasoning-parser-plugin /kaggle/tmp/era-v5-lab/teams/12-quantization/serving/g10_parsers.py --reasoning-parser g10 --enable-auto-tool-choice --tool-parser-plugin /kaggle/tmp/era-v5-lab/teams/12-quantization/serving/g10_parsers.py --tool-call-parser g10 --dtype=half --max-model-len=4096 --tensor-parallel-size=2`
- Check: `serve_check.py --model /kaggle/tmp/models/Qwen3-4B-Instruct-2507 --label Qwen3-4B-Instruct-2507 (stand-in) --out /kaggle/working/serve_check_out --format-hint on --max-tokens 1024 --n-gpus 2 --usd-per-gpu-hour 0.0 --vllm-arg=--dtype=half --vllm-arg=--max-model-len=4096 --vllm-arg=--tensor-parallel-size=2`

