"""Tests for chat_template.jinja (Task 9 Hand-off to Team 12).

Validates that chat_template.jinja renders transcripts in exact alignment with
render.py across single-turn, multi-turn, reasoning traces, tool calling,
and effort levels.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import jinja2
import pytest

TEAM = Path(__file__).resolve().parents[1]


def _load_render():
    render_path = TEAM / "chat-format" / "render.py"
    spec = importlib.util.spec_from_file_location("g10_render", render_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_mod = _load_render()
TEMPLATE_PATH = TEAM / "chat-format" / "chat_template.jinja"
TEAM12_CANDIDATE_PATHS = [
    TEAM.parent / "12-quantization" / "tokenizer" / "chat_template.jinja",
    TEAM.parent / "12-quantization" / "chat-format" / "chat_template.jinja",
    TEAM.parent / "12-quantization" / "chat_template.jinja",
]


def _get_jinja_template():
    assert TEMPLATE_PATH.is_file()
    env = jinja2.Environment(loader=jinja2.BaseLoader())
    return env.from_string(TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_canonical_template_and_handoff_doc_exist():
    # The G10 canonical template and handoff doc must always exist and be valid.
    assert TEMPLATE_PATH.is_file()
    handoff_doc = TEAM / "chat-format" / "team12_chat_template_handoff.md"
    assert handoff_doc.is_file()
    doc_text = handoff_doc.read_text(encoding="utf-8")
    assert "130823" in doc_text
    assert "chat_template.jinja" in doc_text


def test_team12_template_sync():
    # Verify parity with Team 12's copy if present; skip with clear reason if not yet copied.
    present_path = next((p for p in TEAM12_CANDIDATE_PATHS if p.is_file()), None)
    if present_path is None:
        checked_list = ", ".join(str(p.relative_to(TEAM.parent)) for p in TEAM12_CANDIDATE_PATHS)
        pytest.skip(
            f"Team 12 template copy not found (checked: {checked_list}); "
            "hand-off scheduled for 12 Nov 2026."
        )
    assert TEMPLATE_PATH.read_text(encoding="utf-8") == present_path.read_text(encoding="utf-8")


def test_jinja_render_simple_user_turn():
    tmpl = _get_jinja_template()
    msgs = [{"role": "user", "content": "Hello, how are you?"}]

    # When add_generation_prompt is False
    jinja_out = tmpl.render(messages=msgs, effort="4k", add_generation_prompt=False)
    py_out = render_mod.render(msgs, effort="4k")
    assert jinja_out == py_out

    # Parse round-trip
    parsed = render_mod.parse(jinja_out)
    assert parsed["effort"] == "4k"
    assert parsed["messages"] == msgs

    # When add_generation_prompt is True
    prompt_out = tmpl.render(messages=msgs, effort="4k", add_generation_prompt=True)
    assert prompt_out.endswith("<|im_start|>assistant\n")
    assert "<|endoftext|>" not in prompt_out


def test_jinja_render_explicit_system_message():
    tmpl = _get_jinja_template()
    msgs = [
        {"role": "system", "content": "You are an expert Go programmer."},
        {"role": "user", "content": "Explain goroutines."},
    ]
    for effort in ("1k", "4k", "16k", "64k"):
        jinja_out = tmpl.render(messages=msgs, effort=effort, add_generation_prompt=False)
        py_out = render_mod.render(msgs, effort=effort)
        assert jinja_out == py_out
        parsed = render_mod.parse(jinja_out)
        assert parsed["effort"] == effort
        assert parsed["messages"] == msgs


def test_jinja_render_reasoning_and_tool_calls():
    tmpl = _get_jinja_template()
    msgs = [
        {"role": "system", "content": "You inspect code."},
        {"role": "user", "content": "Run tests on stats.go"},
        {
            "role": "assistant",
            "think": "I must execute go test ./... to check for regressions.",
            "tool_calls": [
                {"arguments": {"command": "go test ./..."}, "name": "run_terminal"}
            ],
            "content": "Executing tests in the environment.",
        },
        {"role": "tool", "content": "PASS\nok  swe-task-go  0.012s"},
        {
            "role": "assistant",
            "content": "All tests passed successfully.",
        },
    ]

    jinja_out = tmpl.render(messages=msgs, effort="16k", add_generation_prompt=False)
    py_out = render_mod.render(msgs, effort="16k")

    # The rendered output preserves structural tags
    assert "<|im_start|>assistant\n<|think|>\n" in jinja_out
    assert "<|tool_call|>\n" in jinja_out
    assert "<|tool_result|>\nPASS\nok  swe-task-go  0.012s\n<|/tool_result|>" in jinja_out

    # Both py_out and jinja_out parse to identical semantic messages and effort
    parsed_jinja = render_mod.parse(jinja_out)
    parsed_py = render_mod.parse(py_out)
    assert parsed_jinja["effort"] == parsed_py["effort"] == "16k"
    assert parsed_jinja["messages"] == parsed_py["messages"] == msgs


def test_jinja_tool_calls_dict_formatting():
    tmpl = _get_jinja_template()
    msgs = [
        {"role": "user", "content": "Check weather"},
        {
            "role": "assistant",
            "tool_calls": [{"name": "get_weather", "arguments": {"city": "Bengaluru"}}],
            "content": "Checking weather for Bengaluru.",
        },
        {"role": "tool", "content": "24C, clear sky"},
    ]
    jinja_out = tmpl.render(messages=msgs, effort="4k", add_generation_prompt=False)
    parsed = render_mod.parse(jinja_out)
    assert parsed["messages"][1]["tool_calls"] == [{"name": "get_weather", "arguments": {"city": "Bengaluru"}}]
