"""Tests for the v2 additions in effort_suite.py: the answer_key and api_call checkers and the proposed v2 manifest.

    python -m pytest teams/10-post-training/eval/test_effort_suite_v2.py -q -p no:cacheprovider

The checker tests use code-made fixtures. The tests that read the pinned QASC and API-Bank files run only when
EFFORT_V2_DATA points at a folder holding qasc/ and api-bank/ (the layout of their upstream repositories); they are
skipped otherwise. No benchmark text is stored in this file.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

parametrize = pytest.mark.parametrize  # bare decorators: pr-guard reads "+@a.b" as an email
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("g10_effort_suite_v2_test", HERE / "effort_suite.py")
es = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = es
_spec.loader.exec_module(es)

V1 = HERE / "effort_manifest.json"
V2 = HERE / "effort_manifest_v2_proposed.json"
V1_FILE_SHA256 = "fb8c09a4940b800c50de5ea7eaf51eb40afd62740a1919b08282f72910e97f8b"
DATA = os.environ.get("EFFORT_V2_DATA")
needs_data = pytest.mark.skipif(not DATA or not (Path(DATA) / "qasc").is_dir(), reason="EFFORT_V2_DATA not set")

AK = {"id": "t", "answer": "C"}
AC = {"id": "t", "api_name": "AddAlarm", "param_dict": {"token": "abc", "time": "2023-03-16 07:00:00"}}
GOOD_CALL = "[AddAlarm(token='abc', time='2023-03-16 07:00:00')]"


# --- answer_key -------------------------------------------------------------------------------------------

@parametrize("completion", ["C", "(C)", "C.", "The answer is C", "answer: C", "Answer is (C)",
                                        "reasoning...\n\\boxed{C}", "\\boxed{(C)}", "so \\boxed{A} no, \\boxed{C}"])
def test_answer_key_right(completion):
    assert es.score_answer_key(AK, completion)["reward"] == 1


@parametrize("completion", ["B", "The answer is B", "\\boxed{D}", "answer: H"])
def test_answer_key_wrong(completion):
    r = es.score_answer_key(AK, completion)
    assert r["reward"] == 0 and r["reason"] == "wrong answer"


@parametrize("completion", ["", "   \n", "I think it is probably the third one", "C and D", "c",
                                        "The answer is a cat", "answer is Cat", "\\boxed{CD}"])
def test_answer_key_no_answer(completion):
    r = es.score_answer_key(AK, completion)
    assert r["reward"] == 0 and r["reason"] == "no answer found"


def test_answer_key_ignores_closed_think_span():
    think, end = es.T["think"], es.T["think_end"]
    assert es.score_answer_key(AK, f"{think}maybe answer is B{end}\nC")["reward"] == 1
    assert es.score_answer_key(AK, f"{think}the answer is C{end}")["reward"] == 0


# --- api_call ---------------------------------------------------------------------------------------------

def test_api_call_right():
    assert es.score_api_call(AC, GOOD_CALL)["reward"] == 1
    assert es.score_api_call(AC, "Sure:\n" + GOOD_CALL + "\n")["reward"] == 1
    assert es.score_api_call(AC, '[AddAlarm(time="2023-03-16 07:00:00", token="abc")]')["reward"] == 1  # order, quotes


def test_api_call_wrong_name_or_value():
    assert "name mismatch" in es.score_api_call(AC, GOOD_CALL.replace("AddAlarm", "ModifyAlarm"))["reason"]
    r = es.score_api_call(AC, "[AddAlarm(token='abc', time='2023-03-16 08:00:00')]")
    assert r["reward"] == 0 and "values differ" in r["reason"]


@parametrize("completion", ["", "AddAlarm(token='abc')", "[AddAlarm(token='abc'", "[AddAlarm('abc', 'x')]",
                                        "[AddAlarm(token=abc, time=2)]", "[AddAlarm(token='a', token='b')]",
                                        GOOD_CALL + " " + GOOD_CALL, "no call here"])
def test_api_call_malformed_or_empty(completion):
    r = es.score_api_call(AC, completion)
    assert r["reward"] == 0 and r["reason"] == "no single well-formed API call found"


def test_api_call_extra_and_missing_parameter():
    extra = es.score_api_call(AC, "[AddAlarm(token='abc', time='2023-03-16 07:00:00', note='x')]")
    assert extra["reward"] == 0 and "extra ['note']" in extra["reason"]
    missing = es.score_api_call(AC, "[AddAlarm(token='abc')]")
    assert missing["reward"] == 0 and "missing ['time']" in missing["reason"]


def test_api_call_empty_gold_params():
    gold = {"id": "t", "api_name": "GetToday", "param_dict": {}}
    assert es.score_api_call(gold, "[GetToday()]")["reward"] == 1
    assert es.score_api_call(gold, "[GetToday(x='1')]")["reward"] == 0


# --- manifests --------------------------------------------------------------------------------------------

def test_v1_file_and_loading_unchanged():
    assert hashlib.sha256(V1.read_bytes()).hexdigest() == V1_FILE_SHA256
    m = es.load_manifest(V1)
    assert m["suite"] == "g10-effort-dev-v1" and sum(s["status"] == "resolved" for s in m["slots"]) == 55


def test_v2_proposed_structure():
    v1, v2 = es.load_manifest(V1), es.load_manifest(V2)
    assert v2["suite"] == "g10-effort-dev-v2-proposed" and "PROPOSED" in v2["note"]
    old = {s["slot"]: s for s in v1["slots"] if s["status"] == "resolved"}
    new = {s["slot"]: s for s in v2["slots"]}
    assert len(old) == 55 and all(new[k] == v for k, v in old.items())  # the 55 are equal objects
    assert [s["slot"] for s in v1["slots"]] == [s["slot"] for s in v2["slots"]]
    by_cat: dict[tuple, int] = {}
    for s in v2["slots"]:
        by_cat[(s["category"], s["status"])] = by_cat.get((s["category"], s["status"]), 0) + 1
    assert by_cat == {("code", "resolved"): 30, ("math", "resolved"): 25, ("tool_agentic", "resolved"): 20,
                      ("general", "resolved"): 10, ("indic", "unavailable"): 15}
    v1_indic = [s for s in v1["slots"] if s["category"] == "indic"]
    assert [s for s in v2["slots"] if s["category"] == "indic"] == v1_indic  # reason unchanged
    assert v2["stages"] == v1["stages"] and v2["selection_seed"] == v1["selection_seed"]
    assert len({s["group"] for s in v2["slots"] if s["category"] == "tool_agentic"}) == 20  # one call per file
    assert len({s["task_id"] for s in v2["slots"] if s["status"] == "resolved"}) == 85
    assert es.manifest_digest(v2) == v2["manifest_sha256"] != v1["manifest_sha256"]


def test_v2_new_slots_hold_no_item_text():
    raw = V2.read_text(encoding="utf-8")
    for s in json.loads(raw)["slots"]:
        if s["category"] in ("tool_agentic", "general"):
            assert not {"text", "question", "prompt", "answer", "gold"} & set(s)
    assert "formatted_question\"" in raw  # the field name only


def test_v2_slot_choice_follows_the_v1_rule():
    v2 = es.load_manifest(V2)
    seed = v2["selection_seed"]
    q = [s for s in v2["slots"] if s["category"] == "general"]
    ranks = [es._rank(seed, s["task_id"].removeprefix("qasc-")) for s in q]
    assert ranks == sorted(ranks)  # picked in rank order


@needs_data
def test_v2_every_gold_passes_its_own_checker_and_hashes_verify():
    v2 = es.load_manifest(V2)
    dirs = {"qasc": Path(DATA) / "qasc", "api_bank": Path(DATA) / "api-bank"}
    wanted = [s["slot"] for s in v2["slots"] if s["category"] in ("tool_agentic", "general")]
    prompts = es.resolve_prompts(v2, dirs, slots=wanted)
    assert len(prompts) == 30
    calls = [p.task["api_name"] for p in prompts.values() if p.checker == "api_call"]
    assert len(calls) == 20 == len(set(calls))  # one slot per API name
    for p in prompts.values():
        if p.checker == "answer_key":
            assert es.score_answer_key(p.task, p.task["answer"])["reward"] == 1
            assert es.score_answer_key(p.task, "Z" if p.task["answer"] != "Z" else "A")["reward"] == 0
        else:
            args = ", ".join(f"{k}={v!r}" for k, v in p.task["param_dict"].items())
            assert es.score_api_call(p.task, f"[{p.task['api_name']}({args})]")["reward"] == 1
            assert es.score_api_call(p.task, f"[{p.task['api_name']}({args}, zz='1')]")["reward"] == 0


@needs_data
def test_v2_resolution_fails_on_a_changed_pin(tmp_path):
    v2 = es.load_manifest(V2)
    slot = next(s for s in v2["slots"] if s["category"] == "general")
    bad = {**v2, "slots": [{**slot, "text_sha256": "0" * 64}]}
    with pytest.raises(es.SourceError):
        es.resolve_prompts(bad, {"qasc": Path(DATA) / "qasc"})
