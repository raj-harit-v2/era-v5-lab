"""Tests for scorers.py: each scorer is checked with correct answers and wrong answers, never with a model."""

from __future__ import annotations

import importlib.util
import json
import unicodedata
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_scorers", HERE / "scorers.py")
assert spec is not None and spec.loader is not None
scorers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorers)
T, render = scorers.T, scorers.render

# A named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize

TOOLCALL = scorers.load_jsonl(HERE / "toolcall_v1.jsonl")
BY_ID = {r["id"]: r for r in TOOLCALL}
NO_CALL = [r for r in TOOLCALL if not r["expect"]["calls"]]
WITH_CALL = [r for r in TOOLCALL if r["expect"]["calls"]]


def calls_text(calls):
    return "".join(f"{T['tool_call']}\n{render._call_json(c)}\n{T['tool_call_end']}\n" for c in calls)


def body_for(calls, content="", end=True):
    """What a model writes after `<|im_start|>assistant`: its calls, then its reply, then (optionally) `<|im_end|>`."""
    return calls_text(calls) + content + (T["im_end"] if end else "")


def concrete(value):
    return value["any_of"][0] if isinstance(value, dict) else value


def expected_calls(row):
    return [{"name": c["name"], "arguments": {k: concrete(v) for k, v in c["arguments"].items()}}
            for c in row["expect"]["calls"]]


def reference(row, end=True):
    """A perfect answer for a row, written to meet its own rules."""
    expect = row["expect"]
    if expect["calls"]:
        return body_for(expected_calls(row), "", end)
    reply = " ".join(expect.get("must_contain", []))
    if expect.get("must_contain_any"):
        reply += " " + expect["must_contain_any"][0]
    if expect.get("must_ask"):
        reply += " Which one do you want?"
    return body_for([], reply.strip() or "Hello, I am well.", end)


# --- the test set itself ----------------------------------------------------------------------------------


def test_set_is_well_formed():
    ids = [r["id"] for r in TOOLCALL]
    assert len(ids) == len(set(ids)) >= 30
    kinds = {r["kind"] for r in TOOLCALL}
    assert kinds == {"single", "indic_args", "multi", "pick", "no_call", "missing_arg", "after_result"}
    for r in TOOLCALL:
        assert r["source"].startswith("original:") and "evaluation-only" in r["source"]
        assert r["messages"][-1]["role"] in ("user", "tool")
        names = {t["name"] for t in scorers._tools_of(r)}
        assert names == set(r["tools"])
        for c in r["expect"]["calls"]:
            assert c["name"] in names


def test_every_prompt_renders_and_parses_back():
    for r in TOOLCALL:
        parsed = render.parse(render.render(r["messages"], "1k"))
        assert parsed["messages"][-1]["role"] in ("user", "assistant", "tool")


def test_every_expected_call_is_valid_against_its_schema():
    for r in TOOLCALL:
        tools = {t["name"]: t for t in scorers._tools_of(r)}
        for c in expected_calls(r):
            assert scorers.schema_valid(c, tools), r["id"]


def test_every_loose_argument_exists_in_the_expected_call():
    for r in TOOLCALL:
        loose = r["expect"].get("loose", {})
        assert set(loose) <= {k for c in r["expect"]["calls"] for k in c["arguments"]}, r["id"]
        assert set(loose.values()) <= {"ci", "nospace"}


def test_a_row_with_no_call_has_a_reply_rule_or_is_the_greeting():
    for r in NO_CALL:
        e = r["expect"]
        assert e.get("must_ask") or e.get("must_contain") or e.get("must_contain_any") or r["id"] == "tc-none-01"


def test_prompt_text_stops_at_the_assistant_header_and_never_holds_the_answer():
    for r in TOOLCALL:
        prompt = scorers.build_prompt(r)
        assert prompt.endswith(f"{T['im_start']}assistant\n")
        assert not prompt.endswith(T["endoftext"])
        assert prompt.count(f"{T['im_start']}assistant\n") == 1 + sum(m["role"] == "assistant" for m in r["messages"])
        if r["kind"] != "after_result":
            assert T["tool_call"] not in prompt


def test_the_user_message_holds_the_values_a_model_must_copy():
    # Values a model has to copy are written in the prompt itself, so there is one right spelling.
    must_copy = {"tc-single-02": "06:30", "tc-multi-02": "07:00", "tc-single-09": "the build is green",
                 "tc-single-04": "250 USD to EUR", "tc-pick-02": "5000 INR to USD", "tc-pick-03": "2026-11-30",
                 "tc-indic-02": "कृपया दरवाज़ा बंद करें", "tc-indic-03": "நாளை சந்திப்போம்"}
    for rid, text in must_copy.items():
        user = BY_ID[rid]["messages"][1]["content"]
        assert unicodedata.normalize("NFC", text) in unicodedata.normalize("NFC", user), rid


# --- the scorer: right answers ----------------------------------------------------------------------------


@parametrize("end", [True, False])
@parametrize("row", TOOLCALL, ids=[r["id"] for r in TOOLCALL])
def test_reference_answer_scores_one(row, end):
    got = scorers.score_toolcall(row, reference(row, end=end))
    assert got["score"] == 1, got


def test_end_markers_are_all_optional():
    row = BY_ID["tc-single-01"]
    call = [{"name": "get_weather", "arguments": {"city": "Pune", "unit": "celsius"}}]
    text = calls_text(call)
    for tail in ("", T["im_end"], T["im_end"] + "\n", T["im_end"] + "\n" + T["endoftext"], T["endoftext"]):
        assert scorers.score_toolcall(row, text + tail)["score"] == 1, repr(tail)
    reply = BY_ID["tc-none-01"]
    for tail in ("", T["im_end"], T["im_end"] + "\n", T["im_end"] + "\n" + T["endoftext"]):
        assert scorers.score_toolcall(reply, "Hello!" + tail)["score"] == 1, repr(tail)


def test_order_and_call_ids_do_not_matter():
    row = BY_ID["tc-multi-01"]
    a = {"name": "get_weather", "arguments": {"city": "Kolkata", "unit": "celsius"}, "id": "c2"}
    b = {"name": "get_weather", "arguments": {"city": "Mumbai", "unit": "celsius"}, "id": "c1"}
    assert scorers.score_toolcall(row, body_for([a, b]))["score"] == 1


def test_integer_valued_float_equals_integer_but_a_bool_never_equals_one():
    row = BY_ID["tc-single-04"]
    ok = {"name": "convert_currency", "arguments": {"amount": 250.0, "from_currency": "USD", "to_currency": "EUR"}}
    assert scorers.score_toolcall(row, body_for([ok]))["score"] == 1
    assert scorers._canon(True, None) != scorers._canon(1, None)
    assert scorers._canon(250.0, None) == scorers._canon(250, None)


def test_case_and_spacing_are_ignored_only_where_the_row_says_so():
    lang = BY_ID["tc-pick-04"]
    ok = {"name": "translate", "arguments": {"text": "Good Morning", "target_language": " tamil "}}
    assert scorers.score_toolcall(lang, body_for([ok]))["score"] == 1
    strict = BY_ID["tc-single-01"]
    wrong_case = {"name": "get_weather", "arguments": {"city": "pune", "unit": "celsius"}}
    assert scorers.score_toolcall(strict, body_for([wrong_case]))["score"] == 0
    calc = BY_ID["tc-single-07"]
    spaced = {"name": "calculate", "arguments": {"expression": "(17*23)+4"}}
    assert scorers.score_toolcall(calc, body_for([spaced]))["score"] == 1


def test_either_accepted_value_scores_one_and_a_third_does_not():
    row = BY_ID["tc-indic-01"]
    for city in ("चेन्नई", "Chennai", "chennai"):
        call = {"name": "get_weather", "arguments": {"city": city, "unit": "celsius"}}
        assert scorers.score_toolcall(row, body_for([call]))["score"] == 1, city
    other = {"name": "get_weather", "arguments": {"city": "Madras", "unit": "celsius"}}
    assert scorers.score_toolcall(row, body_for([other]))["score"] == 0


# --- Indic spelling ---------------------------------------------------------------------------------------


def test_the_two_spellings_of_a_nukta_letter_score_the_same():
    row = BY_ID["tc-indic-02"]
    text = row["expect"]["calls"][0]["arguments"]["text"]
    assert "ज़" in unicodedata.normalize("NFC", text)
    single = text.replace("ज़", "ज़")  # the composition-excluded single code point
    assert single != text
    for variant in (text, single, unicodedata.normalize("NFD", text)):
        call = {"name": "translate", "arguments": {"text": variant, "target_language": "English"}}
        assert scorers.score_toolcall(row, body_for([call]))["score"] == 1


def test_zwj_and_zwnj_are_not_dropped_by_normalisation():
    assert scorers._norm("क्‍ष") == "क्‍ष"
    assert scorers._norm("क्‌ष") == "क्‌ष"
    assert scorers._canon("क्‍ष", None) != scorers._canon("क्ष", None)


# --- the scorer: wrong answers ----------------------------------------------------------------------------


@parametrize("row", WITH_CALL, ids=lambda r: r["id"])
def test_answering_without_a_call_scores_zero(row):
    assert scorers.score_toolcall(row, "Sure, I can help." + T["im_end"])["score"] == 0


@parametrize("row", NO_CALL, ids=lambda r: r["id"])
def test_calling_a_tool_when_none_is_right_scores_zero(row):
    tool = row["tools"][0]
    got = scorers.score_toolcall(row, body_for([{"name": tool, "arguments": {}}], reference(row, end=False)))
    assert got["score"] == 0 and got["reason"] == "called a tool when none was right"


@parametrize("text", ["", " ", "\n", T["im_end"], T["im_end"] + "\n" + T["endoftext"]])
def test_an_empty_answer_scores_zero_on_every_row(text):
    assert [r["id"] for r in TOOLCALL if scorers.score_toolcall(r, text)["score"]] == []


@parametrize("text", ["Happy to help.", "Sure." + T["im_end"], "I am not sure what you mean."])
def test_a_reply_that_ignores_the_prompt_passes_at_most_the_greeting(text):
    passed = [r["id"] for r in TOOLCALL if scorers.score_toolcall(r, text)["score"]]
    assert passed == ["tc-none-01"]


@parametrize("row", [r for r in NO_CALL if r["expect"].get("must_ask")], ids=lambda r: r["id"])
def test_a_missing_argument_row_needs_a_question(row):
    assert scorers.score_toolcall(row, "Done." + T["im_end"])["reason"] == "the reply is not a question"
    assert scorers.score_toolcall(row, "Which one?" + T["im_end"])["score"] == 1


def test_wrong_argument_scores_zero():
    wrong = body_for([{"name": "get_weather", "arguments": {"city": "Mumbai", "unit": "celsius"}}])
    assert scorers.score_toolcall(BY_ID["tc-single-01"], wrong)["score"] == 0


def test_wrong_tool_scores_zero():
    wrong = body_for([{"name": "read_file", "arguments": {"path": "*.py"}}])
    assert scorers.score_toolcall(BY_ID["tc-pick-01"], wrong)["score"] == 0


def test_invented_optional_argument_scores_zero():
    calls = [
        {"name": "set_alarm", "arguments": {"time": "07:00", "label": "run"}},
        {"name": "get_weather", "arguments": {"city": "Hyderabad", "unit": "celsius"}},
    ]
    assert scorers.score_toolcall(BY_ID["tc-multi-02"], body_for(calls))["score"] == 0


def test_missing_call_in_a_multi_row_scores_zero():
    one = body_for([{"name": "get_weather", "arguments": {"city": "Mumbai", "unit": "celsius"}}])
    assert scorers.score_toolcall(BY_ID["tc-multi-01"], one)["score"] == 0


def test_the_same_call_twice_does_not_stand_for_two_different_calls():
    mumbai = {"name": "get_weather", "arguments": {"city": "Mumbai", "unit": "celsius"}}
    assert scorers.score_toolcall(BY_ID["tc-multi-01"], body_for([mumbai, mumbai]))["score"] == 0


def test_extra_call_scores_zero():
    good = {"name": "get_weather", "arguments": {"city": "Pune", "unit": "celsius"}}
    assert scorers.score_toolcall(BY_ID["tc-single-01"], body_for([good, good]))["score"] == 0


def test_string_instead_of_a_number_fails_the_schema():
    call = {"name": "convert_currency", "arguments": {"amount": "250", "from_currency": "USD", "to_currency": "EUR"}}
    got = scorers.score_toolcall(BY_ID["tc-single-04"], body_for([call]))
    assert got["score"] == 0 and got["schema_valid"] is False


def test_true_instead_of_one_scores_zero():
    row = BY_ID["tc-single-08"]
    call = {"name": "read_file", "arguments": {"path": "README.md", "max_lines": True}}
    assert scorers.score_toolcall(row, body_for([call]))["score"] == 0


def test_unknown_tool_fails_the_schema():
    got = scorers.score_toolcall(BY_ID["tc-single-01"], body_for([{"name": "get_forecast", "arguments": {"city": "Pune"}}]))
    assert got["score"] == 0 and got["schema_valid"] is False


@parametrize(
    "text, why",
    [
        ('<tool_call>{"name":"get_weather","arguments":{"city":"Pune"}}</tool_call>', "plain-text marker"),
        (f"{T['tool_call']}\n{{not json}}\n{T['tool_call_end']}\n" + T["im_end"], "not JSON"),
        (f"{T['tool_call']}\n{{\"name\":\"get_weather\"}}\n" + T["im_end"], "missing"),
        ("Hello" + T["im_end"] + f"{T['im_start']}user\nhi", "not exactly one assistant turn"),
        ("Hello" + T["im_end"] + f"\n{T['im_start']}assistant\nAgain", "not exactly one assistant turn"),
    ],
)
def test_broken_chat_format_scores_zero_and_says_why(text, why):
    got = scorers.score_toolcall(BY_ID["tc-single-01"], text)
    assert got["score"] == 0 and got["parse_ok"] is False and why in got["reason"]


def test_look_alike_characters_cannot_pass_as_the_marker():
    typed = "<∣tool_call∣>"
    text = f'{typed}\n{{"arguments":{{"city":"Pune","unit":"celsius"}},"name":"get_weather"}}\n{typed}'
    got = scorers.score_toolcall(BY_ID["tc-single-01"], text + T["im_end"])
    assert got["score"] == 0 and got["calls_exact"] is False


def test_after_result_reply_must_hold_the_value():
    row = BY_ID["tc-result-01"]
    assert scorers.score_toolcall(row, "It is warm." + T["im_end"])["score"] == 0
    assert scorers.score_toolcall(row, "It is 27 degrees." + T["im_end"])["score"] == 1


def test_a_new_call_after_the_result_scores_zero():
    again = body_for([{"name": "calculate", "arguments": {"expression": "12 * 12"}}], "144")
    assert scorers.score_toolcall(BY_ID["tc-result-02"], again)["score"] == 0


# --- sets, prompt builder and command line ----------------------------------------------------------------


def test_set_score_counts_a_missing_generation_as_zero():
    rows = TOOLCALL[:4]
    out = scorers.score_toolcall_set(rows, {r["id"]: reference(r) for r in rows[:3]})
    assert out["n"] == 4 and out["exact"] == 0.75 and out["by_kind"]["single"] == 0.75


def test_set_score_of_all_reference_answers_is_one():
    out = scorers.score_toolcall_set(TOOLCALL, {r["id"]: reference(r) for r in TOOLCALL})
    assert out["exact"] == out["parse_ok"] == out["schema_valid"] == 1.0
    assert all(v == 1.0 for v in out["by_kind"].values())


def test_command_line_writes_prompts_and_a_report(tmp_path):
    prompts = tmp_path / "prompts.jsonl"
    assert scorers.main(["prompts", "--rows", str(HERE / "toolcall_v1.jsonl"), "--out", str(prompts)]) == 0
    written = scorers.load_jsonl(prompts)
    assert [p["id"] for p in written] == [r["id"] for r in TOOLCALL]
    assert all(p["prompt"].endswith(f"{T['im_start']}assistant\n") for p in written)

    gens = tmp_path / "gens.jsonl"
    half = TOOLCALL[::2]
    gens.write_text("".join(json.dumps({"id": r["id"], "generation": reference(r)}, ensure_ascii=False) + "\n"
                            for r in half), encoding="utf-8")
    out = tmp_path / "report.json"
    assert scorers.main(["toolcall", "--rows", str(HERE / "toolcall_v1.jsonl"), "--generations", str(gens),
                         "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["n"] == len(TOOLCALL) and report["exact"] == len(half) / len(TOOLCALL)


def test_command_line_refuses_unknown_and_duplicate_ids(tmp_path):
    rows = str(HERE / "toolcall_v1.jsonl")
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"id": "nope", "generation": "x"}) + "\n", encoding="utf-8")
    assert scorers.main(["toolcall", "--rows", rows, "--generations", str(bad), "--out", str(tmp_path / "o.json")]) == 2
    dup = tmp_path / "dup.jsonl"
    line = json.dumps({"id": "tc-none-01", "generation": "Hi"}) + "\n"
    dup.write_text(line * 2, encoding="utf-8")
    assert scorers.main(["toolcall", "--rows", rows, "--generations", str(dup), "--out", str(tmp_path / "o.json")]) == 2


# --- regressions found in review --------------------------------------------------------------------------


@parametrize("payload", [
    '{"name":["get_weather"],"arguments":{}}',
    '{"name":{"a":1},"arguments":{"city":"Pune"}}',
    '{"name":null,"arguments":{}}',
    '{"name":"get_weather","arguments":["Pune"]}',
    '{"name":"get_weather","arguments":"{}"}',
    '{"name":"calculate","arguments":{"expression":NaN}}',
    "[]", "null", "5", '"text"',
])
def test_odd_call_payloads_score_zero_and_never_crash(payload):
    text = f"{T['tool_call']}\n{payload}\n{T['tool_call_end']}\n" + T["im_end"]
    for row in (BY_ID["tc-single-01"], BY_ID["tc-none-01"]):
        assert scorers.score_toolcall(row, text)["score"] == 0


def test_a_call_that_fits_two_expected_calls_cannot_hide_a_valid_pairing():
    # "Mumbai or Pune" and "Mumbai": the answer [Mumbai, Pune] pairs as (Pune, Mumbai). A greedy match missed it.
    row = {"id": "x", "kind": "multi", "messages": BY_ID["tc-multi-01"]["messages"], "expect": {"calls": [
        {"name": "get_weather", "arguments": {"city": {"any_of": ["Mumbai", "Pune"]}, "unit": "celsius"}},
        {"name": "get_weather", "arguments": {"city": "Mumbai", "unit": "celsius"}}]}}
    both = [{"name": "get_weather", "arguments": {"city": c, "unit": "celsius"}} for c in ("Mumbai", "Pune")]
    assert scorers.score_toolcall(row, body_for(both))["score"] == 1
    assert scorers.score_toolcall(row, body_for(both[::-1]))["score"] == 1
    twice = [both[1], both[1]]  # Pune twice: nothing pairs with the plain "Mumbai" call
    assert scorers.score_toolcall(row, body_for(twice))["score"] == 0


def test_scoring_never_changes_the_row_it_scores():
    before = json.dumps(TOOLCALL, sort_keys=True)
    for r in TOOLCALL:
        scorers.score_toolcall(r, reference(r))
    assert json.dumps(TOOLCALL, sort_keys=True) == before


def test_the_loader_writes_no_bytecode_and_restores_the_setting(tmp_path):
    import os
    import subprocess
    import sys

    (tmp_path / "tiny.py").write_text("VALUE = 1\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    code = ("import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location('s', sys.argv[1]); m = importlib.util.module_from_spec(spec)\n"
            "src = open(sys.argv[1], encoding='utf-8').read().replace('render = _load(', 'render = _x(')\n"
            "exec(compile(src.split('render = _x(')[0], sys.argv[1], 'exec'), m.__dict__)\n"
            "assert sys.dont_write_bytecode is False\n"
            "tiny = m._load('tiny', __import__('pathlib').Path(sys.argv[2]))\n"
            "assert tiny.VALUE == 1 and sys.dont_write_bytecode is False\n")
    done = subprocess.run([sys.executable, "-c", code, str(HERE / "scorers.py"), str(tmp_path / "tiny.py")],
                          capture_output=True, text=True, env=env, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    assert not list(tmp_path.rglob("__pycache__")), "the loader wrote bytecode"


def test_command_line_rejects_bad_files_with_exit_code_two(tmp_path, capsys):
    rows = str(HERE / "toolcall_v1.jsonl")
    out = str(tmp_path / "deep" / "dir" / "report.json")
    assert scorers.main(["toolcall", "--rows", str(tmp_path / "missing.jsonl"), "--generations", rows, "--out", out]) == 2
    broken = tmp_path / "broken.jsonl"
    broken.write_text("{not json}\n", encoding="utf-8")
    assert scorers.main(["toolcall", "--rows", rows, "--generations", str(broken), "--out", out]) == 2
    no_text = tmp_path / "no_text.jsonl"
    no_text.write_text(json.dumps({"id": "tc-none-01"}) + "\n" + json.dumps({"id": "tc-none-02", "generation": 5}) + "\n",
                       encoding="utf-8")
    assert scorers.main(["toolcall", "--rows", rows, "--generations", str(no_text), "--out", out]) == 2
    twice = tmp_path / "twice.jsonl"
    twice.write_text(Path(rows).read_text(encoding="utf-8").splitlines()[0] + "\n" + Path(rows).read_text(encoding="utf-8"),
                     encoding="utf-8")
    assert scorers.main(["toolcall", "--rows", str(twice), "--generations", str(broken), "--out", out]) == 2
    assert "repeats an id" in capsys.readouterr().err
    good = tmp_path / "good.jsonl"
    good.write_text(json.dumps({"id": "tc-none-01", "generation": "Hello!"}) + "\n", encoding="utf-8")
    assert scorers.main(["toolcall", "--rows", rows, "--generations", str(good), "--out", out]) == 0
    assert Path(out).exists()


def test_random_markers_and_fragments_never_crash_the_scorers():
    import random
    atoms = [T["tool_call"], T["tool_call_end"], T["tool_result"], T["tool_result_end"], T["think"], T["think_end"],
             T["im_end"], T["im_start"], T["endoftext"], "\n", " ", "?", "7", "सात", "‍", "assistant", "user",
             '{"name":"get_weather","arguments":{"city":"Pune"}}', '{"name":1}', "[]", "null", "{", "}"]
    rng = random.Random(7)
    indic = scorers.load_jsonl(HERE / "indic_v1.jsonl")
    for _ in range(3000):
        text = "".join(rng.choice(atoms) for _ in range(rng.randint(0, 9)))
        assert scorers.score_toolcall(rng.choice(TOOLCALL), text)["score"] in (0, 1)
        assert scorers.score_indic(rng.choice(indic), text)["score"] in (0, 1)


def test_tool_call_rows_with_indic_text_record_native_review():
    rows = scorers.load_jsonl(HERE / "toolcall_v1.jsonl")
    got = {r["id"]: r["review"] for r in rows if "review" in r}
    assert set(got) == {"tc-indic-01", "tc-indic-02", "tc-indic-03", "tc-indic-04", "tc-none-04"}
    assert got["tc-indic-03"] == "wording reviewed by a native speaker"  # Tamil
    assert all(v == "wording reviewed by a native speaker" for v in got.values())
