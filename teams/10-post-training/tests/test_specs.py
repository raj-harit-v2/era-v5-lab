"""Spec checks for teams/10-post-training Week 1 deliverables."""

from __future__ import annotations

from pathlib import Path

TEAM = Path(__file__).resolve().parents[1]

EXPECTED_ASSIGNED = (
    "<|endoftext|>",
    "<|im_start|>",
    "<|im_end|>",
    "<|think|>",
    "<|/think|>",
    "<|tool_call|>",
    "<|/tool_call|>",
    "<|tool_result|>",
    "<|/tool_result|>",
)


EXPECTED_MEMBERS = (
    "Sai Teja",
    "Ajay Kumar",
    "Amit T",
    "f20201351h-maker",
    "Ashish Kamble",
    "Hema Varshini Palpandian",
    "Lokesh Arundathi",
    "gmrammohan15",
    "Ranjani Chandrasekaran",
    "Ravi Naik",
    "Syed Abdul",
    "Vikash Ranjan",
)


def test_licence_table_has_decision_and_tsai_reserves():
    licence = (TEAM / "licences" / "licence_table.md").read_text(encoding="utf-8")
    assert "bigcode/starcoderdata" in licence
    assert "code-python" in licence
    assert "TSAI reserves" in licence
    for section in ("StarCoder", "Stack Exchange", "Indic web"):
        assert section in licence
    for member in EXPECTED_MEMBERS:
        assert member in licence
    decisions = []
    for line in licence.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"Set", ""} or set(cells[0]) <= set("-: "):
            continue
        decisions.append(cells[-1])
    assert "chandassu" in licence
    assert "BodduSriPavan111/chandassu" in licence
    assert "MIT" in licence
    assert decisions and all(
        d in {"TSAI reserves", "excluded", "needs TSAI decision"} or d.startswith("allowed") for d in decisions
    )


def test_special_tokens_v0_has_256_block_and_assigned_tokens():
    doc = (TEAM / "special-tokens" / "special_tokens_v0.md").read_text(encoding="utf-8")
    assert "256" in doc
    assert "TSAI reserves" in doc
    assert "special_tokens_v1" not in doc
    for section in ("StarCoder", "Stack Exchange", "Indic web"):
        assert section in doc
    for member in EXPECTED_MEMBERS:
        assert member in doc
    assert "chandassu" in doc
    assert "_x000D_" in doc
    assert "not a special token" in doc.lower() or "Not a special token" in doc
    for token in EXPECTED_ASSIGNED:
        assert token in doc
    assert "021 eval_fp_0" not in doc
    assert "022 eval_fp_1" not in doc
    assert "023 eval_fp_2" not in doc
    assert "021" in doc and "023" in doc
    assert "unused" in doc.lower()


def test_chat_format_and_swe_e2e_exist_and_cover_effort_budgets():
    chat = (TEAM / "chat-format" / "chat_format_v0.md").read_text(encoding="utf-8")
    for budget in ("1k", "4k", "16k", "64k"):
        assert f"`{budget}`" in chat
    swe = (TEAM / "results" / "swe_e2e.md").read_text(encoding="utf-8")
    assert "docker" in swe.lower()
    assert "OK" in swe
    assert "G10-Local-Run-ERA-V5" not in swe
    assert (TEAM / "swe-task" / "Dockerfile").exists()
    assert (TEAM / "swe-task" / "run_e2e.py").exists()


def test_special_tokens_v1_if_present():
    path = TEAM / "special-tokens" / "special_tokens_v1.md"
    if path.exists():
        doc = path.read_text(encoding="utf-8")
        assert "131,072" in doc or "256" in doc
        assert "fim_prefix" in doc
        assert "fim_pad" in doc
        assert "subagent_call" in doc
        assert "021 eval_fp_0" not in doc
        assert "unused" in doc.lower()
        for tok_id in (
            "129994",
            "130773",
            "130774",
            "130801",
            "130802",
            "130803",
            "130804",
            "130816",
            "130817",
            "130818",
            "130822",
            "130823",
            "130824",
            "130825",
            "130826",
            "130827",
            "130828",
        ):
            assert tok_id in doc
        assert "U+200D" in doc and "U+200C" in doc
        assert "do not apply nfkc" in doc.lower()


def test_sft_mix_proposal_covers_five_areas_and_rules():
    path = TEAM / "sft" / "sft_mix_proposal.md"
    assert path.exists()
    doc = path.read_text(encoding="utf-8")
    for area in ("Code", "Agentic", "Tool Use", "Indic", "General"):
        assert area in doc
    for share in ("35%", "25%", "15%", "10%", "100%"):
        assert share in doc
    for budget in ("1k", "4k", "16k", "64k"):
        assert f"`{budget}`" in doc
    assert "U+200D" in doc and "U+200C" in doc
    assert "NFKC" in doc


