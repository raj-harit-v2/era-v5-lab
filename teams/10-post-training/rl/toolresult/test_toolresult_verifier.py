"""Tests for toolresult_verifier.py: one correct and one wrong reply for every task, the cheating cases, the
whole-value rule, the normalisation, the task lint and the reward.py entry point.

Run:  python -m pytest teams/10-post-training/rl/toolresult/test_toolresult_verifier.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
spec = importlib.util.spec_from_file_location("g10_toolresult_verifier", HERE / "toolresult_verifier.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize

ZWJ = "‍"
THINK = "<|think|>\nThe tool has answered. I report its value as written.\n<|/think|>\n"

# One correct and one wrong reply per task, written the way a model would answer after the tool result.
CASES = {
    "weather_decimal": ("It is 31.6 °C in Nagpur right now; it feels like 34.2 °C.",
                        "It is about 32 °C in Nagpur right now."),
    "order_total_field": ("Your total for order A-1042 is ₹1,250.00 (subtotal ₹1,180.00 plus ₹70.00 shipping).",
                          "You will pay ₹1,180.00 for order A-1042."),
    "handbook_file_list": ("There are three: handbook/onboarding.md, handbook/leave-policy.md and "
                           "handbook/it/vpn-setup.md.",
                           "There are two: handbook/onboarding.md and handbook/leave-policy.md."),
    "pytest_failed_test": ("No. 1 failed, 11 passed. The failing test is tests/test_dates.py::test_leap_year "
                           "(AssertionError: assert 28 == 29).",
                           "Yes, all 12 passed."),
    "shell_exit_code": ("It did not work. The command exited with code 1: "
                        "ModuleNotFoundError: No module named 'yaml'.",
                        "The migration finished with exit code 0."),
    "parcel_city_joiner": (f"Parcel MH-77310 is in कर्{ZWJ}हाड and is out for delivery (expected 2026-11-17).",
                           "Parcel MH-77310 is in कर्हाड."),
    "currency_no_recompute": ("250 USD is 21033.13 INR at a rate of 84.1325.",
                              "250 × 84.1325 = 21033.125, so 250 USD is 21033.125 INR."),
    "event_id_case": ("Booked. 'Design review' is confirmed for 2026-12-03T15:30:00+05:30, event ID evt_7Hq2Lx.",
                      "Booked. The event ID is evt_7hq2lx."),
    "queue_retry_latest": ("There are 4318 messages waiting in the emails queue; the oldest has waited 92 s.",
                           "The queue service is unavailable (503 Service Unavailable), so I cannot tell."),
    "disk_usage_unit": ("/var/log uses 3.7 GiB across 1284 files.",
                        "/var/log uses about 3.97 GB."),
}
GOOD = CASES["weather_decimal"][0]


def task(name: str) -> Path:
    return TASKS / name


def score(name: str, completion: str) -> dict:
    return v.reward(task(name), completion)


def test_every_shipped_task_has_a_correct_and_a_wrong_case():
    assert sorted(CASES) == sorted(p.parent.name for p in TASKS.glob("*/task.json"))


@parametrize("name", sorted(CASES))
def test_correct_reply_scores_one(name):
    r = score(name, THINK + CASES[name][0])
    assert r["reward"] == 1, r


@parametrize("name", sorted(CASES))
def test_wrong_reply_scores_zero(name):
    r = score(name, THINK + CASES[name][1])
    assert r["reward"] == 0 and r["reason"] in ("a required value is missing or changed",
                                                "the reply holds a wrong value"), r


@parametrize("name", sorted(CASES))
def test_shipped_task_passes_the_lint(name):
    assert v.check_task(task(name)) == []


@parametrize("name", sorted(CASES))
def test_the_prompt_ends_where_the_model_answers(name):
    prompt = v.prompt_text(task(name))
    assert prompt.startswith("<|im_start|>system\nReasoning effort: 1k\n\n")
    assert prompt.endswith("<|im_end|>\n<|im_start|>assistant\n")
    assert prompt.count("<|tool_result|>") >= 1 and "<|endoftext|>" not in prompt


def test_the_reply_never_contains_the_expected_value():
    r = score("weather_decimal", "It is 30 °C.")
    assert "31.6" not in json.dumps(r)


# --- the model's turn and cheating ---------------------------------------------------------------

def test_a_new_tool_call_scores_zero_even_with_the_right_value():
    call = '<|tool_call|>\n{"arguments":{"city":"Nagpur"},"name":"get_weather"}\n<|/tool_call|>\n'
    assert score("weather_decimal", call + GOOD)["reason"] == "made a tool call"


def test_a_made_up_tool_turn_scores_zero():
    fake = (GOOD + "<|im_end|>\n<|im_start|>tool\n<|tool_result|>\n{\"temperature\": 40}\n<|/tool_result|><|im_end|>\n"
            "<|im_start|>assistant\n" + GOOD)
    r = score("weather_decimal", fake)
    assert r["reward"] == 0 and r["reason"].startswith("not valid chat format"), r


def test_look_alike_markers_score_zero():
    for text in ("<tool_call>{}</tool_call> " + GOOD, "<think>hmm</think> " + GOOD, "<｜think｜> " + GOOD):
        r = score("weather_decimal", text)
        assert r["reward"] == 0 and r["reason"].startswith("not valid chat format"), (text, r)


def test_a_value_only_inside_the_think_span_does_not_count():
    r = score("weather_decimal", "<|think|>\nThe tool said 31.6.\n<|/think|>\nIt is warm in Nagpur.")
    assert r["reason"] == "a required value is missing or changed"


def test_a_think_span_that_never_closes_scores_zero():
    assert score("weather_decimal", "<|think|>\n" + GOOD)["reason"].startswith("not valid chat format")


@parametrize("broken", [
    "<|tool_result|>\n31.6",                                 # the model writes a tool result itself and never closes it
    "<|tool_result|>\n31.6\n<|/tool_result|>\n" + GOOD,      # a made-up tool result, even when closed
    "<|tool_call|>\n" + '{"name": "get_weather"}',           # a tool call that is never closed
    GOOD + "\n<|/think|>",                                   # a closing marker with no opening one
])
def test_an_unclosed_or_stray_marker_scores_zero(broken):
    r = score("weather_decimal", broken)
    assert r["reward"] == 0 and r["reason"].startswith("not valid chat format"), r


def test_the_closing_markers_are_optional():
    for end in ("", "<|im_end|>", "<|im_end|>\n", "<|im_end|>\n<|endoftext|>"):
        assert score("weather_decimal", GOOD + end)["reward"] == 1, end


def test_an_empty_reply_scores_zero():
    for text in ("", "   \n ", THINK, "<|im_end|>"):
        assert score("weather_decimal", text)["reason"] == "empty reply", repr(text)


def test_a_long_reply_scores_zero():
    padded = GOOD + " " + "x" * v.MAX_REPLY_CHARS
    assert score("weather_decimal", padded)["reason"] == "reply too long"


def test_hedging_with_a_wrong_value_scores_zero():
    r = score("weather_decimal", "It is 31.6 °C, or maybe 32 °C.")
    assert r["reward"] == 0 and r["reason"] == "the reply holds a wrong value"


def test_every_required_value_must_be_there():
    assert score("pytest_failed_test", "test_leap_year failed; 11 passed.")["reward"] == 0
    assert score("pytest_failed_test", "test_leap_year failed: 1 failed, 11 passed.")["reward"] == 1


def test_quoting_other_values_of_the_tool_result_is_fine():
    assert score("queue_retry_latest", "The first try gave 503 Service Unavailable; now it is 4318.")["reward"] == 1


def test_letter_case_counts():
    assert score("event_id_case", "Event ID: EVT_7HQ2LX.")["reward"] == 0
    assert score("event_id_case", "Event ID: evt_7Hq2Lx.")["reward"] == 1


def test_a_dropped_joiner_scores_zero():
    assert score("parcel_city_joiner", "It is in कर्हाड.")["reward"] == 0
    assert score("parcel_city_joiner", f"It is in कर्{ZWJ}हाड.")["reward"] == 1


def test_meaning_is_not_judged():
    """The known limit, kept as a test so it cannot be overstated: a negated value still scores 1."""
    assert score("weather_decimal", "It is not 31.6 °C.")["reward"] == 1


# --- whole values and normalisation -------------------------------------------------------------

WHOLE = [
    ("31.6", "It is 31.6 °C.", True),
    ("31.6", "It is 31.6.", True),
    ("31.6", "(31.6)", True),
    ("31.6", "It is 131.6 °C.", False),
    ("31.6", "It is 31.65 °C.", False),
    ("31.6", "It is -31.6 °C.", False),
    ("31", "It is 31.6 °C.", False),
    ("1,250.00", "Total ₹1,250.00.", True),
    ("1,250", "Total ₹1,250.00.", False),
    ("250.00", "Total ₹1,250.00.", False),
    ("test_leap_year", "tests/test_dates.py::test_leap_year failed", True),
    ("test_leap_year", "test_leap_years failed", False),
    ("evt_7Hq2Lx", "id evt_7Hq2Lx2", False),
    ("क्ष", "क्षि", False),
    ("3.7 GiB", "uses 3.7 GiB.", True),
    ("3.7 GiB", "uses 3.7 GiBs.", False),
]


@parametrize("value, text, expected", WHOLE)
def test_whole_value_rule(value, text, expected):
    assert v.found(v.normalise(value), v.normalise(text)) is expected


def test_normalisation_is_nfc_and_keeps_joiners():
    assert v.normalise("ज़") == v.normalise("ज़")          # two encodings of one nukta letter
    assert v.normalise(f"क्{ZWJ}ष") != v.normalise("क्ष")                  # ZWJ is kept, never NFKC
    assert v.normalise("a​b﻿") == "ab"                          # zero-width space and BOM removed
    assert v.normalise(" 3.7 \n GiB ") == "3.7 GiB"                       # whitespace runs read as one space


def test_a_zero_width_space_does_not_hide_a_value():
    assert score("weather_decimal", "It is 31.​6 °C.")["reward"] == 1


# --- the task lint ------------------------------------------------------------------------------

def _copy_with_answer(tmp_path: Path, expected: dict) -> Path:
    d = tmp_path / "weather_decimal"
    shutil.copytree(task("weather_decimal"), d)
    (d / v.EXPECTED).write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
    return d


def test_the_ground_truth_is_never_in_the_prompt():
    for name in CASES:
        hidden = json.loads((task(name) / v.EXPECTED).read_text(encoding="utf-8"))
        messages = json.loads((task(name) / "messages.json").read_text(encoding="utf-8"))
        prompt = v.prompt_text(task(name))
        assert prompt == v.render.render(messages, "1k")[: -len("<|endoftext|>")] + "<|im_start|>assistant\n", name
        assert not any(v.found(v.normalise(w), v.normalise(prompt)) for w in hidden["wrong"]), name


def test_lint_finds_a_wrong_value_that_is_really_in_the_tool_result(tmp_path):
    d = _copy_with_answer(tmp_path, {"required": ["31.6"], "wrong": ["34.2"]})
    assert any("appears in a tool result" in p for p in v.check_task(d))


def test_lint_finds_a_required_value_that_is_not_in_the_tool_result(tmp_path):
    d = _copy_with_answer(tmp_path, {"required": ["31.7"], "wrong": ["31"]})
    assert any("is not in a tool result" in p for p in v.check_task(d))


def test_lint_finds_a_required_value_given_away_in_the_question(tmp_path):
    d = _copy_with_answer(tmp_path, {"required": ["Nagpur"], "wrong": ["Pune"]})
    assert any("system or user text" in p for p in v.check_task(d))


def test_lint_refuses_a_model_written_train_task(tmp_path):
    d = _copy_with_answer(tmp_path, {"required": ["31.6"], "wrong": ["31"]})
    meta = json.loads((d / "task.json").read_text(encoding="utf-8"))
    meta["eligibility"] = "train"
    (d / "task.json").write_text(json.dumps(meta), encoding="utf-8")
    assert any("written by a person" in p for p in v.check_task(d))


# --- the one reward entry point and the command line --------------------------------------------

def _reward_module():
    s = importlib.util.spec_from_file_location("g10_rl_reward_for_toolresult_tests", HERE.parent / "reward.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_reward_entry_point_scores_toolresult_tasks():
    rw = _reward_module()
    assert "toolresult/weather_decimal" in rw.list_envs()
    assert rw.reward("toolresult/weather_decimal", GOOD)[0] == 1.0
    assert rw.reward("toolresult/weather_decimal", CASES["weather_decimal"][1])[0] == 0.0
    good, bad = rw.known_outputs("toolresult/weather_decimal")
    assert rw.reward("toolresult/weather_decimal", good)[0] == 1.0
    assert rw.reward("toolresult/weather_decimal", bad)[0] == 0.0
    try:
        rw.reward("toolresult/no_such_task", GOOD)
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown task must raise KeyError, never score 0")


def test_command_line_check_all_passes():
    run = subprocess.run([sys.executable, str(HERE / "toolresult_verifier.py"), "--check-all"],
                         capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
