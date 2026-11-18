# Serving: vLLM OpenAI endpoint with the G10 chat format

Week 3, task 4 (Member C). One checkpoint served by **vLLM 0.33.0** (the version in
[`gpu_path/results/environment.json`](../gpu_path/results/environment.json)) on the OpenAI-compatible endpoint, with
G10's chat template, a reasoning parser and a tool parser. 100 fixed prompts are sent and checked. The result goes
to [`results/serve_check.md`](../results/serve_check.md).

Gate 3 asks that the endpoint return reasoning and tool calls in the right fields: `message.reasoning` and
`message.tool_calls`, and not inside `message.content`.

| File | What |
|---|---|
| [`g10_parsers.py`](g10_parsers.py) | vLLM plugin with two parsers, both named `g10`. The reasoning parser maps `<\|think\|> … <\|/think\|>` to `reasoning`. The tool parser maps `<\|tool_call\|>{json}<\|/tool_call\|>` to `tool_calls`. Streaming and non-streaming. |
| [`serve_check.py`](serve_check.py) | starts `vllm serve` with the template and both parsers, sends the 100 prompts (plus 20 streamed), checks every field, and writes `serve_check.md`, `summary.json`, `serve_check.jsonl` and the server log to `--out` |
| [`prompts_v1.jsonl`](prompts_v1.jsonl), [`tools_v1.json`](tools_v1.json) | the 100 prompts and 6 tool schemas, written by [`make_prompts.py`](make_prompts.py) |
| [`test_g10_parsers.py`](test_g10_parsers.py) | template round trip, streaming in 1-char and random chunks, reasoning end on multi-turn prompts, and the parsers inside vLLM's own `DelegatingParser` (needs vllm) |
| [`serve_check.ipynb`](serve_check.ipynb) | Kaggle / Colab notebook: install vLLM 0.33.0, run the tests, download the model, run serve_check, zip the results |
| [`test_serve_check.py`](test_serve_check.py) | the field and behaviour checks, the answer check on Indic digits, request building |

## Why our own parsers

No built-in vLLM parser reads the G10 markers. `deepseek_r1` and `qwen3` look for `<think>`. `hermes` looks for
`<tool_call>`, and its streaming expects `"name"` before `"arguments"`, while G10 writes `"arguments"` first.
Details that matter in vLLM 0.33:

- **Special tokens.** With the frozen tokenizer each marker is one special token, and vLLM drops special tokens
  from the text by default. Requests send `"skip_special_tokens": false` (serve_check.py does). The tool parser also
  sets it on any request that carries tools.
- **Earlier turns.** vLLM asks the reasoning parser whether reasoning has already ended *in the prompt*. A
  multi-turn prompt contains earlier `<|/think|>`. The parser reads only the open turn after the last
  `<|im_start|>`, or the new reasoning would come back as content (tested).
- **Answers with no reasoning.** An answer with no `<|think|>` ends the reasoning phase at its first token. That
  way a direct tool call is still parsed when streaming.
- **Stand-in tokenizers.** Markers are matched as text, so the parsers also work with a stand-in model whose
  tokenizer splits them into several tokens. Both tokenizer cases are tested.

## Run

**Tests (CPU, any machine):**
```bash
python -m pytest teams/12-quantization/serving -q          # vLLM adapter tests skip without vllm
```
With `vllm==0.33.0` installed, all 60 pass. On a Mac, `pip install --no-deps vllm==0.33.0` plus the modules
the parser imports is enough.

**Kaggle (GPU T4 x2, Internet on): [`serve_check.ipynb`](serve_check.ipynb).** Stand-in model
`Qwen/Qwen3-4B-Instruct-2507` (Apache-2.0). Import the notebook and check the settings cell (branch, model).
1. `SMOKE = True`: run all cells interactively (about 15 min). Every step runs on 10 prompts.
2. `SMOKE = False`: **Save Version → Save & Run All (Commit)**. Download `serve_check_results.zip` from the
   version's Output tab and copy its `results/` folder into `teams/12-quantization/`. That gives
   `results/serve_check.md` and `results/serve_check/{summary.json, serve_check.jsonl, environment.json}`. Keep
   `logs/` (server log) out of the repo; if needed, put it in a gist.

The notebook installs vLLM 0.33.0 in its own uv environment and runs the tests (none may skip). It uses
`--dtype half` on T4 (no bf16) and tensor parallel 2 on T4 x2. It writes the zip even if the check fails.
Without the notebook, the same run is
`python serving/serve_check.py --model <folder> --vllm-arg=--dtype=half --vllm-arg=--max-model-len=4096 --out out`.

**Our checkpoint (job request).** Once `export_hf.py` (Member D) turns a dry-run-1 checkpoint into a Hugging Face
`GraniteMoeSharedForCausalLM` folder (`unsupported_parts.md` §8), run the same script on it with
`--format-hint off`. The script follows the JOB_REQUEST.md rules: localhost only, `HF_HUB_OFFLINE=1`, writes only
to `--out`.

## What the check measures

- **Fields (pass or fail, exit code 1 on failure).** Every request returns HTTP 200, and no chat marker
  (`<|think|>`, `<|tool_call|>`, `<|im_end|>`, …) is left in `content`, `reasoning` or tool arguments, streamed or
  not, unless the replay explains it. Each answer with a marker is replayed: `/tokenize` renders the same prompt,
  `/v1/completions` regenerates the raw text with no parser, and `g10_parsers` parses it offline.
  - Same fields as the server: the parser did what the format says, and the model broke the G10 layout. This is
    reported (for example a think block after the answer, or a tool call when no tools were offered).
  - Different fields, or a marker only in the streamed answer: a parser fault, which fails the check.
- **Behaviour (reported).** Reason prompts have reasoning, tool prompts call the expected tool with JSON arguments
  that have the schema's required keys, and no_tool / tool_result prompts call none. This measures the model. For
  a stand-in that never saw our format it is a lower bound. Answers in the stand-in's own format (`<think>`,
  `<tool_call>`) are counted separately.
- **Time and cost.** Server start, wall time for the 100 prompts, tokens/s, GPU-hours, and cost at
  `--usd-per-gpu-hour` (0 on Kaggle).

## Findings for G10 and the export

1. **The template drops the request's `tools`.** `chat_template.jinja` never renders `tools`, so a model served
   with it never sees the tool schemas. `chat_format_v0.md` mentions "injected tool schemas" (Tier 1) but fixes no
   format. Until G10 decides, serve_check writes the schemas into the system message (`--tools-in-system auto`).
2. **History tool calls in OpenAI form render in the wrong shape.** A client sends
   `{"id", "type", "function": {"name", "arguments"}}`, and the template's `call | tojson` writes it unchanged.
   Training data has `{"arguments", "name"}`. Proposed fix: render `call.function` when it is present. The parser
   reads both shapes.
3. **Reasoning from earlier turns** is rendered only from a `think` key. OpenAI clients send `reasoning`, so earlier
   reasoning is dropped. That is usually what we want; noted only.
4. **Export (`export_hf.py`).** `generation_config.json` must list `<|im_end|>` (130816) and `<|endoftext|>` (130822)
   as `eos_token_id`, or vLLM generates past the end of the turn.

## Status

- **Kaggle, 15 Nov 2026** ([`results/serve_check.md`](../results/serve_check.md)): Qwen3-4B-Instruct-2507 (stand-in),
  vLLM 0.33.0, T4 x2, fp16.
  - **Fields: PASS.** 100/100 HTTP 200. 98/100 answers are clean; the other 2 are the model writing its think block
    after the answer, which the replay confirms. 0 parser faults.
  - **Fields filled:** reasoning in `message.reasoning` on 25/25 reason prompts; tool calls in `message.tool_calls`
    on 28/30 tool prompts; no call on 20/20 prompts that need none.
  - **Streaming:** 19/20 match. In the one miss the model's reasoning wording changed between the two runs
    (fp16, batched vs. alone); the answer is identical.
  - **Time:** 165 s server start, 97 s for the 100 prompts (200 tokens/s), 0.17 GPU-hours, $0 on Kaggle.
  - **Earlier run:** the first full run failed the old marker check on 6 answers. All 6 were the model breaking the
    layout, 2 of them invited by a format hint that taught tool calls on prompts with no tools. That run led to the
    replay and to the hint change.
- **Known difference, cosmetic:** on requests without tools, streamed `content` can keep the whitespace that follows
  `<|/think|>`. After reasoning ends, vLLM passes deltas through without the tool parser. The non-streamed content
  is stripped. The check compares stripped text.
- **Our checkpoint:** waits for the dry-run-1 checkpoint (G7, D4) and `export_hf.py`. Then the same notebook runs
  with `MODEL` set to the export and `FORMAT_HINT = "off"`.
