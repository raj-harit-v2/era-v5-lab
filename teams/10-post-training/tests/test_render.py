"""Tests for the G10 special-token list and ChatML-style chat format v0."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

TEAM = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_mod = _load("g10_render", TEAM / "chat-format" / "render.py")


def test_team3_tokenizer_ids_replace_000_to_255_numbering():
    rows = render_mod.all_tokens()
    # 4 existing base chat specials + 64 G10 slots (130822..130885) = 68 entries
    assert len(rows) == 68
    ids = [row[0] for row in rows]
    # Remove 000..255 byte-token numbering completely
    assert all(tok_id >= 129994 for tok_id in ids)
    surfaces = [row[2] for row in rows]
    assert len(set(surfaces)) == len(rows)
    assert all(surface.startswith("<|") and surface.endswith("|>") for surface in surfaces)
    assert all("\n" not in surface and " " not in surface for surface in surfaces)
    assigned = {row[0]: (row[1], row[2]) for row in rows if row[3] == "assigned"}
    assert assigned == {
        129994: ("im_start", "<|im_start|>"),
        130773: ("tool_call", "<|tool_call|>"),
        130774: ("tool_result", "<|tool_result|>"),
        130816: ("im_end", "<|im_end|>"),
        130822: ("endoftext", "<|endoftext|>"),
        130823: ("think", "<|think|>"),
        130824: ("think_end", "<|/think|>"),
        130825: ("tool_call_end", "<|/tool_call|>"),
        130826: ("tool_result_end", "<|/tool_result|>"),
    }
    # Verify IDs are read directly from Team 3's tokenizer file (build_v0_1.py)
    assert render_mod.TEAM3_BUILD_V0_1.is_file()
    assert render_mod.load_team3_marker_ids() == assigned


def test_load_team3_marker_ids_from_json(tmp_path):
    data = {
        "added_tokens": [
            {"id": 129994, "content": "<|im_start|>", "special": True},
            {"id": 130816, "content": "<|im_end|>", "special": True},
            {"id": 130773, "content": "<|tool_call|>", "special": True},
            {"id": 130774, "content": "<|tool_result|>", "special": True},
            {"id": 130822, "content": "<|endoftext|>", "special": True},
            {"id": 130823, "content": "<|think|>", "special": True},
            {"id": 130824, "content": "<|/think|>", "special": True},
            {"id": 130825, "content": "<|/tool_call|>", "special": True},
            {"id": 130826, "content": "<|/tool_result|>", "special": True},
        ]
    }
    json_path = tmp_path / "mock_tokenizer.json"
    json_path.write_text(json.dumps(data), encoding="utf-8")
    loaded = render_mod.load_team3_marker_ids(json_path)
    assert len(loaded) == 9
    assert loaded[129994] == ("im_start", "<|im_start|>")
    assert loaded[130823] == ("think", "<|think|>")

    # Missing token raises ValueError
    bad_data = {"added_tokens": [{"id": 129994, "content": "<|im_start|>", "special": True}]}
    bad_path = tmp_path / "bad_tokenizer.json"
    bad_path.write_text(json.dumps(bad_data), encoding="utf-8")
    with pytest.raises(ValueError, match="missing special token"):
        render_mod.load_team3_marker_ids(bad_path)


def test_effort_budgets_and_turn_tokens():
    assert render_mod.EFFORT_BUDGETS == {"1k": 1024, "4k": 4096, "16k": 16384, "64k": 65536}
    names = render_mod.by_name()
    assert names["im_start"] == "<|im_start|>"
    assert names["im_end"] == "<|im_end|>"
    assert names["endoftext"] == "<|endoftext|>"
    assert names["think"] == "<|think|>"
    assert names["think_end"] == "<|/think|>"
    assert names["tool_call"] == "<|tool_call|>"
    assert names["tool_call_end"] == "<|/tool_call|>"
    assert names["tool_result"] == "<|tool_result|>"
    assert names["tool_result_end"] == "<|/tool_result|>"
    for effort in render_mod.EFFORT_BUDGETS:
        assert f"effort_{effort}" not in names  # effort is plain text, not a token
        assert render_mod.effort_limit(effort) == render_mod.EFFORT_BUDGETS[effort]


def test_render_parse_roundtrip_and_atomic_marker_tokenization():
    messages = [
        {"role": "system", "content": "You edit code and you report only what a tool returned."},
        {"role": "user", "content": "test_add fails in calc.py. Fix add."},
        {
            "role": "assistant",
            "think": "The return adds one too many.",
            "tool_calls": [{"name": "read_file", "arguments": {"path": "calc.py"}}],
            "content": "I am reading calc.py before editing it.",
        },
        {"role": "tool", "content": "def add(a, b):\n    return a + b + 1\n"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "name": "apply_patch",
                    "arguments": {"path": "calc.py", "patch": "return a + b"},
                }
            ],
            "content": "Removed the extra increment.",
        },
    ]
    for effort in ("1k", "4k", "16k", "64k"):
        text = render_mod.render(messages, effort=effort)
        assert f"Reasoning effort: {effort}" in text
        assert "<|effort_" not in text
        assert "<|im_start|>assistant\n" in text
        assert "<|think|>\nThe return adds one too many.\n<|/think|>" in text
        assert "<|tool_call|>\n" in text and "\n<|/tool_call|>" in text
        assert "<|tool_result|>\n" in text and "\n<|/tool_result|>" in text
        for other in ("1k", "4k", "16k", "64k"):
            if other != effort:
                assert f"Reasoning effort: {other}" not in text
        parsed = render_mod.parse(text)
        assert parsed["effort"] == effort
        assert parsed["messages"] == messages

        # Verify every chat marker is tokenized as one atomic Team 3 special token ID, never plain text.
        pieces = render_mod.tokenize_markers(text)
        special_ids = [val for kind, val in pieces if kind == "special"]
        assert 130822 in special_ids  # <|endoftext|> (g10_slot_00)
        assert 129994 in special_ids  # <|im_start|> (base)
        assert 130816 in special_ids  # <|im_end|> (base)
        assert 130823 in special_ids and 130824 in special_ids  # <|think|>, <|/think|>
        assert 130773 in special_ids and 130825 in special_ids  # <|tool_call|>, <|/tool_call|>
        assert 130774 in special_ids and 130826 in special_ids  # <|tool_result|>, <|/tool_result|>
        for kind, val in pieces:
            if kind == "text":
                assert "<|" not in str(val)


def test_render_rejects_bad_effort_role_and_plain_or_embedded_markers():
    ok = [{"role": "user", "content": "hello"}]
    for effort in ("2k", "8k", "", "64K"):
        try:
            render_mod.render(ok, effort=effort)
        except render_mod.RenderError:
            pass
        else:
            raise AssertionError(f"effort {effort!r} should fail")

    try:
        render_mod.render([{"role": "developer", "content": "no"}])
    except render_mod.RenderError:
        pass
    else:
        raise AssertionError("unknown role should fail")

    for bad in (
        "see <|im_start|> here",
        "plain <think> tag",
        "plain <tool_call> tag",
        "fullwidth <｜think｜> tag",
        "fullwidth ＜tool_call＞ tag",
    ):
        try:
            render_mod.render([{"role": "user", "content": bad}])
        except render_mod.RenderError:
            pass
        else:
            raise AssertionError(f"marker leak {bad!r} should fail")


def test_tool_call_with_id_roundtrip():
    messages = [
        {"role": "user", "content": "Fetch calc.py"},
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "call_001", "name": "read_file", "arguments": {"path": "calc.py"}}
            ],
            "content": "Reading file.",
        },
    ]
    text = render_mod.render(messages, effort="4k")
    assert '"id":"call_001"' in text
    parsed = render_mod.parse(text)
    assert parsed["messages"][1]["tool_calls"][0]["id"] == "call_001"


def test_effort_is_a_plain_text_line_in_the_first_system_turn():
    # With a system message, the effort line leads that turn.
    with_system = render_mod.render(
        [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "hi"}],
        effort="16k",
    )
    assert with_system.startswith("<|im_start|>system\nReasoning effort: 16k\n\nBe brief.<|im_end|>\n")
    # Without one, a system turn holding only the effort line is added.
    without = render_mod.render([{"role": "user", "content": "hi"}], effort="1k")
    assert without.startswith("<|im_start|>system\nReasoning effort: 1k<|im_end|>\n<|im_start|>user\n")
    parsed = render_mod.parse(without)
    assert parsed == {"effort": "1k", "messages": [{"role": "user", "content": "hi"}]}
    # A user-written line that looks like the effort line is rejected, not misread.
    try:
        render_mod.render([{"role": "system", "content": "Reasoning effort: 64k"}])
    except render_mod.RenderError:
        pass
    else:
        raise AssertionError("system content starting with the effort line should fail")
    # A transcript whose first turn is not the effort system turn does not parse.
    try:
        render_mod.parse("<|im_start|>user\nhi<|im_end|>\n<|endoftext|>")
    except render_mod.RenderError:
        pass
    else:
        raise AssertionError("missing effort turn should fail")


def test_empty_optional_fields_are_omitted():
    text = render_mod.render(
        [{"role": "assistant", "content": "", "think": "", "tool_calls": []}],
        effort="1k",
    )
    parsed = render_mod.parse(text)
    assert parsed == {"effort": "1k", "messages": [{"role": "assistant"}]}
    assert "<|think|>" not in text
    assert "<|tool_call|>" not in text


def test_docs_match_the_plan_sheet_set():
    chat = (TEAM / "chat-format" / "chat_format_v0.md").read_text(encoding="utf-8")
    token_doc = (TEAM / "special-tokens" / "special_tokens_v0.md").read_text(encoding="utf-8")
    token_v1_doc = (TEAM / "special-tokens" / "special_tokens_v1.md").read_text(encoding="utf-8")
    licence = (TEAM / "licences" / "licence_table.md").read_text(encoding="utf-8")
    for budget in ("1k", "4k", "16k", "64k"):
        assert budget in chat
        assert f"`{budget}`" in token_doc
    for tok_id, name, surface, status in render_mod.all_tokens():
        if status == "assigned":
            assert surface in token_doc
            assert name in token_doc
            assert str(tok_id) in token_v1_doc
            assert surface in token_v1_doc
            assert name in token_v1_doc
    assert "256" in token_doc
    assert "TSAI reserves" in token_doc
    assert "bigcode/starcoderdata" in licence
    assert "code-python" in licence
    assert "TSAI reserves" in licence

    decisions = []
    for line in licence.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"Set", ""} or set(cells[0]) <= set("-: "):
            continue
        decisions.append(cells[-1])
    assert "chandassu" in licence
    assert decisions and all(
        d in {"TSAI reserves", "excluded", "needs TSAI decision"} or d.startswith("allowed") for d in decisions
    )
