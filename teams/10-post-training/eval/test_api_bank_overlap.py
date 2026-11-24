"""Unit tests for api_bank_overlap.py (Package T2 / Effort Suite v2).

Run:
    python -m pytest teams/10-post-training/eval/test_api_bank_overlap.py -q -p no:cacheprovider
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import api_bank_overlap as abo  # noqa: E402


def test_exact_key_normalization():
    t1 = "QueryReminder  ( token = '123' ) "
    t2 = "QueryReminder ( token = '123' )"
    assert abo.exact_key(t1) == abo.exact_key(t2)


def test_shingle_overlap_calculation():
    text1 = "Please set an alarm for seven in the morning to wake up for the daily standup meeting."
    text2 = "Please set an alarm for seven in the morning to wake up for the daily standup meeting tomorrow."
    overlap = abo.shingle_overlap(text1, text2, k=5)
    assert overlap > 0.8


def test_shingle_overlap_disjoint():
    text1 = "Query user account balance for banking application."
    text2 = "Translate paragraph from Hindi to English using language model."
    assert abo.shingle_overlap(text1, text2, k=5) == 0.0


def test_manifest_audit_runs_on_proposed_v2():
    manifest_path = HERE / "effort_manifest_v2_proposed.json"
    if not manifest_path.is_file():
        pytest.skip("effort_manifest_v2_proposed.json not present")

    summary = abo.audit_manifest_slots(manifest_path)
    assert summary["schema"] == abo.SCHEMA
    assert summary["total_api_bank_slots"] == 20
    assert len(summary["slots_audited"]) == 20

    slot_names = [s["slot"] for s in summary["slots_audited"]]
    assert "tool_agentic-00" in slot_names
    assert "tool_agentic-19" in slot_names

    for s in summary["slots_audited"]:
        assert s["schema_risk"] == "high_seed_origin"
        assert s["contamination_verdict"] == "held_out_eval_retained"
        assert "Exclude any Nemotron-SFT-Agentic-v2" in s["remediation"]


def test_build_markdown_report_structure():
    mock_summary = {
        "schema": "g10-api-bank-overlap/1",
        "manifest_path": "fake_path.json",
        "total_api_bank_slots": 1,
        "target_set": "nvidia/Nemotron-SFT-Agentic-v2",
        "slots_audited": [
            {
                "slot": "tool_agentic-00",
                "task_id": "apibank/QueryReminder-level-1-1.jsonl#5",
                "api_names": ["QueryReminder"],
                "doc_files": ["apis/get_user_token.py"],
                "text_sha256": "abcdef",
                "seed_provenance": "AlibabaResearch/DAMO-ConvAI api-bank (reminder)",
                "schema_risk": "high_seed_origin",
                "contamination_verdict": "held_out_eval_retained",
                "remediation": "Exclude matching training rows",
            }
        ],
    }
    md = abo.build_markdown_report(mock_summary)
    assert "# API-Bank / Nemotron-SFT-Agentic-v2 Overlap Audit" in md
    assert "Strict Hard-Decontamination" in md
    assert "tool_agentic-00" in md
