"""chat_template.jinja must render byte-for-byte what SFT trains on (training-serving parity).

Training text: chat-format/render.py `render()`, with tool schemas in the first system turn the way sft/convert.py
writes them ("Tools:\\n" + JSON array of the function schemas, sort_keys=True). Serving text: chat_template.jinja in
the environment transformers and vLLM render it in (sandboxed jinja2, trim_blocks, lstrip_blocks, a tojson that takes
sort_keys and separators). transformers' own compiler is used when it is installed.

    python -m pytest teams/10-post-training/tests/test_chat_template_parity.py -q
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

TEAM = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = TEAM / "chat-format" / "chat_template.jinja"


def _load_render():
    spec = importlib.util.spec_from_file_location("g10_render", TEAM / "chat-format" / "render.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_mod = _load_render()


def _load_convert():
    spec = importlib.util.spec_from_file_location("g10_convert", TEAM / "sft" / "convert.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


convert_mod = _load_convert()


def _compile(source: str):
    try:
        from transformers.utils.chat_template_utils import _compile_jinja_template
        return _compile_jinja_template(source)
    except Exception:                                    # noqa: BLE001  (no transformers, or a private-API change)
        from jinja2.sandbox import ImmutableSandboxedEnvironment

        def tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
            return json.dumps(x, ensure_ascii=ensure_ascii, indent=indent, separators=separators, sort_keys=sort_keys)

        env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True,
                                            extensions=["jinja2.ext.loopcontrols"])
        env.filters["tojson"] = tojson
        return env.from_string(source)


TEMPLATE = _compile(TEMPLATE_PATH.read_text(encoding="utf-8"))


def serve(messages, effort="4k", tools=None, add_generation_prompt=False):
    kw = {"tools": tools} if tools is not None else {}
    return TEMPLATE.render(messages=messages, effort=effort, add_generation_prompt=add_generation_prompt, **kw)


def train(messages, effort="4k", tools=None):
    """render.py, after the sft/convert.py step that puts the tool schemas in the first system turn (same layout as
    convert.nemotron_chat: appended to system content, or a system turn of its own)."""
    messages = [dict(m) for m in messages]
    if tools:
        block = "Tools:\n" + convert_mod.tools_json(tools)          # the converter's own serializer
        if messages[0]["role"] == "system" and messages[0].get("content"):
            messages[0]["content"] = f"{messages[0]['content']}\n\n{block}"
        elif messages[0]["role"] == "system":
            messages[0]["content"] = block
        else:
            messages.insert(0, {"role": "system", "content": block})
    return render_mod.render(messages, effort=effort)


WEATHER = {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city.",
                                            "parameters": {"type": "object", "required": ["city"],
                                                           "properties": {"unit": {"enum": ["c", "f"], "type": "string"},
                                                                          "city": {"type": "string"}}}}}
SEARCH_UNWRAPPED = {"name": "search", "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}}

TRANSCRIPTS = {
    "plain": [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}],
    "system_effort": [{"role": "system", "content": "தமிழில் பதிலளி."}, {"role": "user", "content": "வணக்கம்"},
                      {"role": "assistant", "think": "greet back", "content": "வணக்கம்!"}],
    "g10_call_unsorted_args": [
        {"role": "user", "content": "Weather?"},
        {"role": "assistant", "think": "need the tool",
         "tool_calls": [{"name": "get_weather", "arguments": {"unit": "c", "city": "चेन्नई"}}]},
        {"role": "tool", "content": "31C"}, {"role": "assistant", "content": "31°C in Chennai."}],
    "g10_call_with_id": [
        {"role": "user", "content": "Two files"},
        {"role": "assistant", "tool_calls": [{"arguments": {"path": "a.py"}, "id": "call_01", "name": "read_file"},
                                             {"arguments": {"path": "b.py"}, "id": "call_02", "name": "read_file"}]},
        {"role": "tool", "content": "A"}, {"role": "tool", "content": "B"}],
    "openai_call_parsed_args": [   # what vLLM passes: function.arguments already parsed into an object
        {"role": "user", "content": "Weather in Pune?"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "call_9", "type": "function",
                         "function": {"name": "get_weather", "arguments": {"city": "Pune", "unit": "c"}}}]},
        {"role": "tool", "content": "{\"temp_c\": 24}"}],
    "openai_call_no_id": [
        {"role": "user", "content": "x"},
        {"role": "assistant", "tool_calls": [{"type": "function", "id": None,
                                              "function": {"name": "f", "arguments": {}}}]},
        {"role": "tool", "content": "ok"}],
}


# Named marks: an older pr-guard reads a new line that starts with the pytest decorator as an email address.
every_transcript = pytest.mark.parametrize("name", sorted(TRANSCRIPTS))
two_efforts = pytest.mark.parametrize("effort", ["1k", "16k"])
transcripts_for_tools = pytest.mark.parametrize("name", ["plain", "system_effort", "openai_call_parsed_args"])


@every_transcript
@two_efforts
def test_bytes_match_render_py(name, effort):
    assert serve(TRANSCRIPTS[name], effort) == train(TRANSCRIPTS[name], effort)


@transcripts_for_tools
def test_tools_match_convert_py(name):
    tools = [WEATHER, SEARCH_UNWRAPPED]
    out = serve(TRANSCRIPTS[name], tools=tools)
    assert out == train(TRANSCRIPTS[name], tools=tools)
    block = out.split("\n\nTools:\n")[1].split("<|im_end|>")[0]
    assert [f["name"] for f in json.loads(block)] == ["get_weather", "search"]      # unwrapped function schemas


def test_tools_with_empty_system_message():
    msgs = [{"role": "system", "content": ""}, {"role": "user", "content": "q"}]
    assert serve(msgs, tools=[WEATHER]) == train(msgs, tools=[WEATHER])


def test_generation_prompt():
    msgs = TRANSCRIPTS["system_effort"][:2]
    assert serve(msgs, add_generation_prompt=True) == train(msgs)[: -len("<|endoftext|>")] + "<|im_start|>assistant\n"


def test_call_json_is_compact_sorted_and_keeps_id():
    out = serve(TRANSCRIPTS["openai_call_parsed_args"])
    assert '<|tool_call|>\n{"arguments":{"city":"Pune","unit":"c"},"id":"call_9","name":"get_weather"}\n<|/tool_call|>' in out
    assert '"id"' not in serve(TRANSCRIPTS["openai_call_no_id"])


def test_string_arguments_are_not_encoded_twice():
    # plain transformers callers may pass OpenAI arguments as a JSON string; the call body must still be one object
    msgs = [{"role": "user", "content": "x"},
            {"role": "assistant", "tool_calls": [{"id": "c1", "type": "function",
                                                  "function": {"name": "f", "arguments": "{\"city\":\"Pune\"}"}}]},
            {"role": "tool", "content": "ok"}]
    body = serve(msgs).split("<|tool_call|>\n")[1].split("\n<|/tool_call|>")[0]
    assert json.loads(body) == {"arguments": {"city": "Pune"}, "id": "c1", "name": "f"}
    assert serve(msgs) == train(msgs)       # compact and sorted already: same bytes as render.py


def test_round_trip_through_render_parse():
    for msgs in TRANSCRIPTS.values():
        parsed = render_mod.parse(serve(msgs))
        assert len(parsed["messages"]) == len(msgs)


def test_convert_nemotron_row_matches_template():
    # a real converter path end to end: convert.nemotron_chat output rendered by render.py == the template
    row = {"tools": [WEATHER], "messages": [
        {"role": "user", "content": "Weather in Pune?"},
        {"role": "assistant", "content": "", "reasoning_content": "use the tool",
         "tool_calls": [{"id": "call_1", "type": "function",
                         "function": {"name": "get_weather", "arguments": "{\"unit\": \"c\", \"city\": \"Pune\"}"}}]},
        {"role": "tool", "content": "24C"}]}
    trained = render_mod.render(convert_mod.nemotron_chat(row), effort="4k")
    served = serve([{"role": "user", "content": "Weather in Pune?"},
                    {"role": "assistant", "content": "", "think": "use the tool",
                     "tool_calls": [{"id": "call_1", "type": "function",
                                     "function": {"name": "get_weather", "arguments": {"unit": "c", "city": "Pune"}}}]},
                    {"role": "tool", "content": "24C"}], tools=[WEATHER])
    assert served == trained
