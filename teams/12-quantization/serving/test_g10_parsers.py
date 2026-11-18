"""Tests for g10_parsers.py. CPU only, no vLLM needed (the vLLM adapter tests skip without it).

    python -m pytest teams/12-quantization/serving/test_g10_parsers.py -q

  * template round trip: render an assistant turn with G10's own chat_template.jinja (as transformers does: sandboxed
    jinja2, trim_blocks, lstrip_blocks, tojson without ASCII escapes), parse the generated part back, and get the
    reasoning, the tool calls and the content that went in. Needs jinja2.
  * streaming: every way of cutting an output into deltas (one char, random chunks) gives the same fields as the
    non-streaming parse.
  * is_reasoning_end on prompts: a <|/think|> in an earlier turn does not end the reasoning of the open turn.
  * vLLM adapters (needs vllm 0.33): both register as "g10", and vLLM's own DelegatingParser composes them into
    the right reasoning / content / tool_calls, non-streaming and streaming.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import g10_parsers as g  # noqa: E402

REPO = HERE.parents[2]
TEMPLATE = REPO / "teams" / "10-post-training" / "chat-format" / "chat_template.jinja"


# ------------------------------------------------------------------------------ template rendering (as transformers)

def _render(messages, add_generation_prompt=False, **kw):
    jinja2 = pytest.importorskip("jinja2")
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, extensions=["jinja2.ext.loopcontrols"])
    env.filters["tojson"] = lambda x, ensure_ascii=False, indent=None, separators=None, sort_keys=False: json.dumps(
        x, ensure_ascii=ensure_ascii, indent=indent, separators=separators, sort_keys=sort_keys)
    return env.from_string(TEMPLATE.read_text()).render(messages=messages, add_generation_prompt=add_generation_prompt,
                                                        **kw)


def _generated(assistant):
    """The text a model generates for this assistant message: the rendered turn minus the generation prompt and the
    closing <|im_end|> (a stop token, never in the output text)."""
    user = [{"role": "user", "content": "q"}]
    prompt = _render(user, add_generation_prompt=True)
    full = _render(user + [assistant])
    assert full.startswith(prompt)
    out = full[len(prompt):]
    assert out.endswith("<|im_end|>\n<|endoftext|>")
    return out[: -len("<|im_end|>\n<|endoftext|>")]


ASSISTANT_CASES = [
    {"role": "assistant", "content": "Plain answer."},
    {"role": "assistant", "think": "2 + 2 = 4", "content": "4"},
    {"role": "assistant", "think": "line one\n\nline two\n", "content": "multi-line\nanswer"},
    {"role": "assistant", "think": "need the file",
     "tool_calls": [{"arguments": {"path": "file.py"}, "name": "read_file"}]},
    {"role": "assistant", "tool_calls": [{"arguments": {"city": "चेन्नई", "unit": "c"}, "name": "get_weather"}],
     "content": "Checking."},
    {"role": "assistant", "think": "two calls",
     "tool_calls": [{"arguments": {"a": 1}, "id": "call_1", "name": "f"}, {"arguments": {"b": [1, 2]}, "name": "g"}],
     "content": "தமிழில் பதில்."},
    {"role": "assistant", "think": "<tag> not a marker", "content": "x < y and <|im not a marker"},
]


def _expected(m):
    calls = [{"name": c["name"], "arguments": json.dumps(c["arguments"], ensure_ascii=False), "id": c.get("id")}
             for c in m.get("tool_calls", [])]
    return m.get("think"), (m.get("content") or None), calls


def _parse_all(text):
    reasoning, rest = g.split_reasoning(text, final=True)
    calls, content = g.parse_tool_calls(rest or "")
    return reasoning, content, calls


@pytest.mark.parametrize("i", range(len(ASSISTANT_CASES)))
def test_template_round_trip(i):
    m = ASSISTANT_CASES[i]
    assert _parse_all(_generated(m)) == _expected(m)


@pytest.mark.parametrize("i", range(len(ASSISTANT_CASES)))
def test_template_round_trip_streaming(i):
    m = ASSISTANT_CASES[i]
    text = _generated(m)
    rng = random.Random(i)
    for cuts in ["char", "random", "random", "whole"]:
        if cuts == "char":
            pieces = list(text)
        elif cuts == "whole":
            pieces = [text]
        else:
            pieces, k = [], 0
            while k < len(text):
                n = rng.randint(1, 7)
                pieces.append(text[k:k + n])
                k += n
        assert _stream(pieces) == _expected(m), cuts


def _stream(pieces):
    """Drive the two streams the way vLLM's DelegatingParser does: reasoning until it ends, then the tool parser on
    the rest (starting from the content the reasoning stream released in the transition delta)."""
    rs, ts = g.ReasoningStream(), g.ToolCallStream()
    reasoning, content, calls = "", "", []
    text, tool_text, in_tools = "", "", False
    for p in pieces:
        text += p
        if not in_tools:
            r, c = rs.feed(text)
            reasoning += r or ""
            if g.reasoning_ended(text):
                in_tools = True
                p = c or ""
            elif c:
                raise AssertionError("content before reasoning ended")
            else:
                continue
        tool_text += p
        c, new = ts.feed(tool_text)
        content += c or ""
        calls += new
    if not in_tools:                                  # output ended inside reasoning (vLLM: fallback content)
        r, c = rs.flush(text)
        reasoning += r or ""
        content += c or ""
    else:
        c, new = ts.feed(tool_text, final=True)
        content += c or ""
        calls += new
    has_think = text.lstrip().startswith(g.THINK)
    return (reasoning if has_think else None), (content or None), calls


# ------------------------------------------------------------------------------ split_reasoning edge cases

def test_no_think_is_all_content():
    assert g.split_reasoning("hello", final=True) == (None, "hello")
    assert g.split_reasoning("", final=True) == (None, None)


def test_truncated_reasoning_has_no_content():
    assert g.split_reasoning("<|think|>\nhalf a thou", final=True) == ("half a thou", None)


def test_think_marker_mid_content_is_content():
    assert g.split_reasoning("answer <|think|>x<|/think|>", final=True) == (None, "answer <|think|>x<|/think|>")


def test_streaming_holds_partial_markers():
    assert g.split_reasoning("<|th", final=False) == (None, None)
    assert g.split_reasoning("  ", final=False) == (None, None)
    assert g.split_reasoning("<|think|>\nabc\n<|/th", final=False) == ("abc", None)
    assert g.split_reasoning("<|think|>\nabc\n", final=False) == ("abc", None)
    assert g.split_reasoning("<|think|>\nabc\n<|/think|>", final=False) == ("abc", None)
    assert g.split_reasoning("<|think|>\nabc\n<|/think|>\nX", final=False) == ("abc", "X")


# ------------------------------------------------------------------------------ tool calls edge cases

def test_invalid_call_stays_in_content():
    calls, content = g.parse_tool_calls("<|tool_call|>\nnot json\n<|/tool_call|>\nok")
    assert calls == [] and g.CALL in content and content.endswith("ok")


def test_unclosed_complete_call_is_a_call():
    calls, content = g.parse_tool_calls('<|tool_call|>\n{"arguments": {"x": 1}, "name": "f"}')
    assert calls == [{"name": "f", "arguments": '{"x": 1}', "id": None}] and content is None


def test_openai_shaped_call_and_string_arguments():
    body = {"id": "c9", "type": "function", "function": {"name": "f", "arguments": '{"x": 2}'}}
    calls, _ = g.parse_tool_calls(g.CALL + json.dumps(body) + g.CALL_END)
    assert calls == [{"name": "f", "arguments": '{"x": 2}', "id": "c9"}]


def test_streamed_call_waits_for_complete_json():
    ts = g.ToolCallStream()
    assert ts.feed('<|tool_call|>\n{"arguments": {"x": 1') == (None, [])
    c, calls = ts.feed('<|tool_call|>\n{"arguments": {"x": 1}, "name": "f"}\n<|/tool')
    assert c is None and [x["name"] for x in calls] == ["f"]
    c, calls = ts.feed('<|tool_call|>\n{"arguments": {"x": 1}, "name": "f"}\n<|/tool_call|>\nDone')
    assert c == "Done" and calls == []


# ------------------------------------------------------------------------------ reasoning end on prompts

def test_reasoning_end_ignores_earlier_turns():
    history = [{"role": "user", "content": "q1"},
               {"role": "assistant", "think": "old reasoning", "content": "a1"},
               {"role": "user", "content": "q2"}]
    prompt = _render(history, add_generation_prompt=True)
    assert g.THINK_END in prompt
    assert g.reasoning_ended(prompt) is False, "the generation prompt opens a new turn: reasoning has not ended"


def test_reasoning_end_on_outputs():
    assert g.reasoning_ended("") is False
    assert g.reasoning_ended("<|thi") is False
    assert g.reasoning_ended("<|think|>\nstill going") is False
    assert g.reasoning_ended("<|think|>\ndone\n<|/think|>") is True
    assert g.reasoning_ended("Direct answer") is True


# ------------------------------------------------------------------------------ vLLM adapters (vllm 0.33)

class _Tok:
    """Minimal tokenizer: one token per character, plus the markers as single special tokens when special=True."""

    def __init__(self, special):
        self.special = special
        self.markers = list(g.MARKERS) if special else []
        self.vocab = {m: 200000 + i for i, m in enumerate(self.markers)}
        self.inv = {v: k for k, v in self.vocab.items()}

    def get_vocab(self):
        return dict(self.vocab)

    def encode(self, text):
        ids, k = [], 0
        while k < len(text):
            m = next((m for m in self.markers if text.startswith(m, k)), None)
            if m:
                ids.append(self.vocab[m])
                k += len(m)
            else:
                ids.append(ord(text[k]))
                k += 1
        return ids

    def decode(self, ids, skip_special_tokens=False):
        return "".join(self.inv.get(i, "") if i in self.inv else chr(i) for i in ids)


@pytest.mark.parametrize("chunk", [1, 3])
@pytest.mark.parametrize("i", range(len(ASSISTANT_CASES)))
@pytest.mark.parametrize("special", [True, False], ids=["single-token-markers", "text-markers"])
def test_vllm_adapters(special, i, chunk):
    pytest.importorskip("vllm")
    from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
    from vllm.parser import ParserManager
    from vllm.reasoning import ReasoningParserManager
    from vllm.tool_parsers import ToolParserManager

    assert ReasoningParserManager.get_reasoning_parser("g10") is g.G10ReasoningParser
    assert ToolParserManager.get_tool_parser("g10") is g.G10ToolParser
    tok = _Tok(special)
    tools = [{"type": "function", "function": {"name": n, "parameters": {"type": "object"}}}
             for n in ("read_file", "get_weather", "f", "g")]
    req = ChatCompletionRequest(model="m", messages=[{"role": "user", "content": "q"}], tools=tools)
    parser_cls = ParserManager.get_parser(tool_parser_name="g10", reasoning_parser_name="g10", enable_auto_tools=True)
    m = ASSISTANT_CASES[i]
    text = _generated(m)
    want_r, want_c, want_calls = _expected(m)

    reasoning, content, calls = parser_cls(tok, req.tools).parse(text, req, enable_auto_tools=True)
    assert (reasoning, content) == (want_r, want_c)
    assert [(c.name, c.arguments) for c in calls or []] == [(c["name"], c["arguments"]) for c in want_calls]

    # streaming, after a multi-turn prompt whose history holds an earlier <|/think|>
    history = [{"role": "user", "content": "q0"}, {"role": "assistant", "think": "old", "content": "a0"},
               {"role": "user", "content": "q"}]
    prompt_ids = tok.encode(_render(history, add_generation_prompt=True))
    parser = parser_cls(tok, req.tools)
    ids = tok.encode(text)
    r_out, c_out, names, args = "", "", [], {}
    for k in range(0, len(ids), chunk):
        delta_ids = ids[k:k + chunk]
        d = parser.parse_delta(tok.decode(delta_ids), delta_ids, req, prompt_ids, finished=k + chunk >= len(ids))
        if d is None:
            continue
        r_out += d.reasoning or ""
        c_out += d.content or ""
        for tc in d.tool_calls:
            fn = tc.function
            if fn and fn.name:
                names.append(fn.name)
            if fn and fn.arguments:
                args[tc.index] = args.get(tc.index, "") + fn.arguments
    assert (r_out or None, c_out or None) == (want_r, want_c)
    assert names == [c["name"] for c in want_calls]
    assert [args[k] for k in sorted(args)] == [c["arguments"] for c in want_calls]
