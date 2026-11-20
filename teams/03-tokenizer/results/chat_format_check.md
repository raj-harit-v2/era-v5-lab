# Chat format and vLLM marker check on the frozen tokenizer (p1536)

**Question.** On the frozen tokenizer, is every G10 chat marker exactly one special token with its agreed id, in Team 10's chat format (training) and as vLLM loads it (serving)? And do vLLM's parsers find those markers?

**Answer.** Yes for the tokenizer: 0 failures. All 9 chat markers are one special token with the id in G10's spec, in `tokenizers` and in vLLM, and G10's `render.py` and `chat_template.jinja` give identical ids. **No for vLLM's stock parsers:** every stock parser that loads binds to other tokens (the baseline's `<think>`, `</think>`, `<tool_call>`, `</tool_call>`, or `<|unk|>`), never to a G10 marker. Serving needs a G10 parser and the `<|im_end|>` stop id (findings 1 and 2).

| | |
|---|---|
| Tokenizer | p1536, `tokenizer.json` sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` (frozen 16 Nov, `release/README.md`); `release/verify_release.py`: PASS |
| Run | 16 Nov 2026, hosted notebook (Linux, T4 runtime; no GPU work is done) |
| Versions | Python 3.13.18, tokenizers 0.23.3, transformers 5.20.2, jinja2 3.1.6, vllm 0.33.0 |
| Script | `harness/chat_format_check.py` |
| Result | **PASS: 0 failed, 5 notes** |

## How it checks

The script contains no expected values. It reads each one, at run time, from the file that owns it, and compares the tokenizer only against those files:

| Expected value | Read from | sha256 at run time | Last commit |
|---|---|---|---|
| frozen sha256 | `release/SHA256SUMS` (G3) | `a91205462b1b…` | 85639f0 2026-11-16 |
| eos / bos / pad / unk ids | `release/SPECIAL_TOKENS.md` (G3) | `76520be44fc4…` | 85639f0 2026-11-16 |
| marker → id table | `teams/10-post-training/special-tokens/special_tokens_v1.md`, section 3 (G10) | `5c62c0a2d16b…` | 128405b 2026-11-03 |
| the 9 markers chat v0 uses, look-alikes, effort levels | `teams/10-post-training/chat-format/render.py` (G10) | `c51fd23a7d09…` | 183394c 2026-11-16 |
| serving template | `teams/10-post-training/chat-format/chat_template.jinja` (G10) | `1b9c0eded4c3…` | 128405b 2026-11-03 |
| test sentences (11 Indic, En, code) | `release/verify_release.py` `SAMPLES` (G3) | `0a92f2427c4b…` | 85639f0 2026-11-16 |
| chillu / nukta stress text | `v1/normalizer_experiment_v2.py` (G3) | `1e1665980033…` | 4b931f9 2026-10-29 |

Test conversations: 7 in English and code (single turn, system + multi turn, think + tool call + tool result, each effort 1k/4k/16k/64k), and 28 Indic ones. The Indic ones put the text in the user turn, the think block, a tool call, the answer and a tool result. They cover each of the 11 samples, plus forms derived from them: NFD (Bn, As, Ml), a ZWJ and a ZWNJ conjunct in each sample's own script, Malayalam old-style chillu, and split nukta letters (Bn, Pa).

## Commands

```bash
# repo root, tokenizer.json from the Kaggle dataset sohiyiy/p1536-sample-v0 at teams/03-tokenizer/release/
cd teams/03-tokenizer && sha256sum -c release/SHA256SUMS && cd ../..
python teams/03-tokenizer/release/verify_release.py teams/03-tokenizer/release/tokenizer.json
pip install tokenizers transformers jinja2 vllm==0.33.0
python teams/03-tokenizer/harness/chat_format_check.py --vllm --out chat_format_check.json
```

## Part A: chat format (with Team 10)

| Check | Result | Detail |
|---|---|---|
| A0 frozen sha256 | PASS | `e6b93a93…`, as `release/SHA256SUMS` |
| A1 each chat marker: one id, the spec id, `special: true` | PASS | `<\|im_start\|>` 129994, `<\|tool_call\|>` 130773, `<\|tool_result\|>` 130774, `<\|im_end\|>` 130816, `<\|endoftext\|>` 130822, `<\|think\|>` 130823, `<\|/think\|>` 130824, `<\|/tool_call\|>` 130825, `<\|/tool_result\|>` 130826 |
| A2 `render.py` == `chat_template.jinja`, text and ids | PASS | 35 of 35 conversations identical |
| A3 generation prompt and default effort | PASS | ends with `<\|im_start\|>assistant\n`; default `Reasoning effort: 4k` |
| A4 round trip, one id per marker, `render.parse()` | PASS | 7 English / code conversations |
| A5 the same next to Indic text | PASS | 28 Indic conversations; the normalizer never touches a marker |
| A6 look-alikes never become marker ids | PASS | all 18 of `render.py`'s look-alikes stay plain text |
| A6 `render.py` rejects a marker typed in content | PASS | `RenderError` |
| A6 look-alikes that are a single token | NOTE | `<think>` 128512, `</think>` 128601, `<tool_call>` 130174, `</tool_call>` 130226 are **special** tokens kept from the baseline. They are not G10 markers (finding 1) |
| A6 template with a marker typed in content | NOTE | `<\|im_end\|>` ids: 2 without, 3 with. The template does not reject it (finding 3) |
| A7 other markers in `special_tokens_v1.md` | NOTE | FIM (130801–130804), `<\|file_sep\|>` 130817, `<\|repo_name\|>` 130818 present; 130827 holds `<\|g10_slot_05\|>`, not `<\|subagent_call\|>`; 130828 holds `<\|g10_slot_06\|>`, not `<\|subagent_return\|>` (finding 4) |

## Part B: vLLM 0.33.0 (with Team 12)

The tokenizer folder (`tokenizer.json` + `tokenizer_config.json` + `special_tokens_map.json`) loaded with vLLM's own `get_tokenizer`, as `vllm serve` does.

| Check | Result | Detail |
|---|---|---|
| B1 each chat marker is one special id in vLLM's tokenizer | PASS | all 9 |
| B2 eos | PASS | 130822, as `SPECIAL_TOKENS.md` |
| B3 end of a chat turn stops generation | NOTE | turns end with `<\|im_end\|>` 130816, eos is 130822 (finding 2) |
| B4 decode keeps / drops markers | PASS | `skip_special_tokens=False` keeps all; `True` removes all. Parsers need `False` |
| B5 stock vLLM parsers | NOTE | see the table below (finding 1) |
| B6 split an assistant turn on the G10 marker ids | PASS | think, tool call (`run_python`) and answer come back exactly |

**B5: every registered vLLM parser on this tokenizer.** 10 load; none uses a G10 marker.

| Parser | Token ids it binds | What those ids are |
|---|---|---|
| reasoning `deepseek_r1`, `ernie45`, `hy_v3`, `minimax_m2_append_think`, `step5` | 128512 / 128601 | baseline `<think>` / `</think>`, not `<\|think\|>` 130823 / `<\|/think\|>` 130824 |
| reasoning `step3` | end 128601 | baseline `</think>` |
| tool `ernie45` | 130174 / 130226 (think end 128601) | baseline `<tool_call>` / `</tool_call>`, not `<\|tool_call\|>` 130773 / `<\|/tool_call\|>` 130825 |
| tool `poolside_v1` | 130174 / 130226 | baseline `<tool_call>` / `</tool_call>` |
| reasoning `cohere_command3`, `cohere_command4` | 130727 for every marker | `<\|unk\|>`: their marker strings are not in the vocab, and the lookup fell back to unk silently |
| 13 others | do not load | they raise `RuntimeError` / `ValueError` because their marker strings are missing |

A stock parser therefore either refuses to load, binds silently to `<|unk|>`, or, worst, loads cleanly on the baseline's `<think>` / `<tool_call>` specials and never sees what the model emits.

## Findings

| # | Finding | Effect | Action | Owner | Status (16 Nov) |
|---|---|---|---|---|---|
| 1 | No stock vLLM parser uses the G10 markers (B5). Several bind to the baseline specials `<think>` 128512, `</think>` 128601, `<tool_call>` 130174, `</tool_call>` 130226 | With `--reasoning-parser deepseek_r1` or a stock tool parser, reasoning and tool calls are not extracted, and no error is raised | Use G10 reasoning and tool-call parsers on ids 130823/130824 and 130773/130825, with `skip_special_tokens=False`; never the stock parsers. B6 shows the id-level split works | G12 | **Done**: G12's `g10` reasoning and tool parsers (`teams/12-quantization/serving/g10_parsers.py`, from G12 PR SreekanthZipsy/era-v5-lab#15, on `main` via #538) read the G10 markers, with `skip_special_tokens: false`. 64 unit tests; serve check 100/100 HTTP 200 on vLLM 0.33.0 (stand-in model) |
| 2 | `<\|im_end\|>` 130816 is not eos (B3) | Generation runs past the end of the assistant turn | Serve with `stop_token_ids=[130816, 130822]`, and add `generation_config.json` with `eos_token_id: [130816, 130822]` to `release/` | G12 (serving); G3 (`generation_config.json`) | Open: G10 and G12 confirm. G12 #15 lists 130816 and 130822 as eos for `export_hf.py`'s `generation_config.json`; not yet set in serving or `release/` |
| 3 | `chat_template.jinja` passes a marker typed in user content through as a real marker (A6) | A user can close a turn or fake a role | The API gateway or serving layer rejects or sanitises marker strings in user content before the template; `render.py` already rejects them at training intake | G12 | Open: G10 and G12 confirm; not in G12 #15 |
| 4 | 130827 / 130828 are still `<\|g10_slot_05\|>` / `<\|g10_slot_06\|>`; G10's spec lists `<\|subagent_call\|>` / `<\|subagent_return\|>` (A7) | None: chat format v0 and SFT/RL data v1 use only the 9 assigned markers | No rename for v0 | G10 | **Closed**: G10 confirms the slots stay as they are |
| 5 | `release/tokenizer_config.json` has no `chat_template` | Every server must pass `--chat-template` by hand | Embed G10's template in `release/tokenizer_config.json` once G10's week-3 template is on `main`, then re-run this check | G3, after G10 | G10 agrees; waits for G10's week-3 PR |

## Scope and limits

- **Tokenizer level.** No model was served. Nothing here shows that a running `vllm serve` applies the template, stops on time or returns `reasoning_content` / `tool_calls`; that needs findings 1 and 2 first, and a model.
- **Template version.** This run tested `chat_template.jinja` at 128405b, confirmed by G10 as the version on `main`. G10's week-3 update (Tools schema in the system turn, OpenAI-shaped tool calls in history; byte-identical to `render.py` per G10's `tests/test_chat_template_parity.py`) lands on `main` with G10's week-3 PR. The script reads the template at run time, so re-run it then.
- **A2 compares the chat format, not JSON formatting.** Tool calls are passed to the template as `render.py`'s JSON string. A real OpenAI-format request (`tool_calls` as objects, reasoning as `reasoning_content`) and `transformers`' `apply_chat_template` were not tested.
- **Streaming** parser behaviour was not tested; B6 splits a complete turn.
- **Indic text** is G3's one-line samples and forms derived from them, not a corpus.
- **llama.cpp** is G12's check (#427): all 356 specials exact in GGUF; the dropped normalizer and pre-tokenizer differences are tracked there.

## Earlier checks this builds on

- G10 `chat-format/verify_frozen_tokenizer.py` and `results/render_frozen_tokenizer.txt`: the same marker checks on tokenizer v0.1 (`a33c9907…`). This run repeats them on p1536, which adds the normalizer, and in vLLM.
- G12 #427: special tokens on the frozen tokenizer in llama.cpp.

## Confirmed by

- Team 10 (chat format, all 5 findings): confirmed on 16 Nov 2026. Tested versions are current on `main`; findings 1–3 confirmed; finding 4 closed (no rename for v0); finding 5 agreed once the week-3 template lands.
- Team 12 (vLLM, findings 1, 2 and 3): confirmed on 18 Nov 2026. Finding 1 is fixed by G12's `g10` parsers (SreekanthZipsy/era-v5-lab#15, merged to `main` in #538).
