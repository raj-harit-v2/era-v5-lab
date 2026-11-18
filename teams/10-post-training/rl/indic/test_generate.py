"""Tests for generate.py: template lint, safe expressions, item self-checks, determinism and the command line.

The templates below are test fixtures for the mechanics, not training templates (those are written by people on the
team, see templates/indic_templates.yaml).

Run:  python -m pytest teams/10-post-training/rl/indic/test_generate.py -q -p no:cacheprovider
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_indic_generate", HERE / "generate.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
iv = g.iv

# Named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize

INTEGER = {
    "id": "hi_fixture_left", "author": "gmrammohan15", "team2_reviewer": "", "eligibility": "eval",
    "language": "hi", "script": "Deva", "answer_type": "integer", "difficulty": "easy",
    "prompt": "{person} के पास {a} आम थे। उसने {b} आम दे दिए। कितने बचे?\n"
              "अपना अंतिम उत्तर केवल अंकों में <answer> और </answer> के बीच लिखिए।",
    "params": {"a": {"int": [20, 90]}, "b": {"int": [1, 19]}, "person": {"pick": ["सीमा", "रवि", "अनु"]}},
    "require": ["a > b"],
    "answer": "a - b",
    "wrong": ["a + b", "a - b - 1"],
}

WEEKDAY = {
    "id": "hi_fixture_weekday", "author": "gmrammohan15", "team2_reviewer": "", "eligibility": "eval",
    "language": "hi", "script": "Deva", "answer_type": "text", "difficulty": "easy",
    "prompt": "आज {today} है। आज से {n} दिन बाद कौन-सा वार होगा? उत्तर <answer>वार</answer> में लिखिए।",
    "params": {"start": {"int": [0, 6]}, "n": {"int": [2, 40]}},
    "lists": {"days": ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]},
    "derive": {"today": "days[start]", "target": "days[(start + n) % 7]"},
    "require": ["n % 7 != 0"],
    "answer": "target",
    "wrong": ["days[(start + n + 1) % 7]"],
}

DIGITS = {
    "id": "bn_fixture_sum", "author": "gmrammohan15", "team2_reviewer": "", "eligibility": "eval",
    "language": "bn", "script": "Beng", "answer_type": "integer", "difficulty": "easy",
    "prompt": "{x} আর {y} যোগ করলে কত হয়? উত্তর <answer>সংখ্যা</answer> হিসেবে লিখুন।",
    "params": {"a": {"int": [100, 999]}, "b": {"int": [100, 999]}},
    "derive": {"x": "digits(a, 'Beng')", "y": "digits(b, 'Beng')"},
    "answer": "a + b",
    "wrong": ["a + b + 10"],
}


def tpl(base: dict, **changes) -> dict:
    t = copy.deepcopy(base)
    t.update(changes)
    return t


@parametrize("base", [INTEGER, WEEKDAY, DIGITS], ids=lambda t: t["id"])
def test_fixture_templates_pass_the_lint(base):
    assert g.check_template(base) == []


@parametrize("base", [INTEGER, WEEKDAY, DIGITS], ids=lambda t: t["id"])
def test_every_item_scores_its_answer_one_and_its_wrong_answers_zero(base):
    items = g.Template(base).generate(200, seed=7)
    assert len(items) == 200 and len({it["prompt"] for it in items}) == 200
    for it in items:
        task = iv.prepare(it, it["accepted"])
        assert all(iv.score(task, iv.wrap(a))["reward"] == 1 for a in it["accepted"])
        assert all(iv.score(task, iv.wrap(w))["reward"] == 0 for w in it["wrong"])
        assert not iv.answer_in_prompt(it["prompt"], it["answer_type"], it["accepted"])


def test_items_record_who_wrote_them_and_their_eligibility():
    it = g.Template(INTEGER).generate(1, seed=1)[0]
    assert it["id"] == "hi_fixture_left-00000" and it["author"] == "gmrammohan15" and it["eligibility"] == "eval"
    assert it["licence"] == "team-written" and "none yet" in it["source"] and "person-written" in it["generator"]


def test_the_answer_is_computed_from_the_drawn_values():
    for it in g.Template(WEEKDAY).generate(50, seed=3):
        days = WEEKDAY["lists"]["days"]
        today = next(d for d in days if f"आज {d} है" in it["prompt"])
        n = int(it["prompt"].split("आज से ")[1].split(" ")[0])
        assert it["accepted"] == [days[(days.index(today) + n) % 7]]


def test_indic_digits_in_the_prompt_and_any_digits_in_the_answer():
    it = g.Template(DIGITS).generate(1, seed=5)[0]
    assert not any("0" <= c <= "9" for c in it["prompt"])
    task = iv.prepare(it, it["accepted"])
    assert iv.score(task, f"<answer>{g.digits(it['accepted'][0], 'Beng')}</answer>")["reward"] == 1
    assert iv.score(task, f"<answer>{it['accepted'][0]}</answer>")["reward"] == 1


def test_same_seed_same_items():
    a = g.Template(INTEGER).generate(30, seed=11)
    assert a == g.Template(INTEGER).generate(30, seed=11)
    assert a != g.Template(INTEGER).generate(30, seed=12)


def test_each_template_has_its_own_random_stream():
    a = g.Template(INTEGER).generate(30, seed=11)
    renamed = g.Template(tpl(INTEGER, id="hi_fixture_other")).generate(30, seed=11)
    assert [it["prompt"] for it in a] != [it["prompt"] for it in renamed]


def test_adding_a_template_before_another_does_not_change_its_items(tmp_path):
    def items_of(templates, name):
        path, out = tmp_path / f"{name}.yaml", tmp_path / f"{name}.jsonl"
        path.write_text(yaml.safe_dump(templates, allow_unicode=True), encoding="utf-8")
        assert g.main(["--templates", str(path), "--per-template", "20", "--seed", "3", "--out", str(out)]) == 0
        rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        return [r for r in rows if r["template"] == INTEGER["id"]]

    assert items_of([INTEGER], "alone") == items_of([WEEKDAY, INTEGER], "second")


def test_a_draw_where_a_wrong_answer_equals_the_answer_is_skipped():
    t = tpl(INTEGER, params={"a": {"int": [20, 90]}, "b": {"int": [0, 3]}, "person": {"pick": ["सीमा"]}},
            wrong=["a + b"])
    for it in g.Template(t).generate(20, seed=2):
        assert it["accepted"][0] not in it["wrong"]  # b = 0 makes a + b == a - b: never kept


def test_a_wrong_answer_equal_to_the_answer_is_dropped_before_scoring(monkeypatch):
    def never(*_):
        raise AssertionError("scored a draw whose wrong answer equals the answer")

    monkeypatch.setattr(g.iv, "score", never)
    with pytest.raises(ValueError, match="items after"):
        g.Template(tpl(INTEGER, wrong=["a - b"])).generate(1, seed=1)


@parametrize("reward", [0, 1])
def test_a_draw_the_verifier_does_not_confirm_is_dropped(monkeypatch, reward):
    # reward 0: the answer does not score 1; reward 1: the wrong answers do not score 0.
    monkeypatch.setattr(g.iv, "score", lambda *_: {"reward": reward})
    with pytest.raises(ValueError, match="items after"):
        g.Template(INTEGER).generate(1, seed=1)


@parametrize("expr", ["'ab' * 1000000000000", "person * 1000000000000", "[a] * b", "999999999999 * 999999999999 * 999999999999"])
def test_multiplying_text_lists_or_into_huge_numbers_is_refused_without_using_memory(expr):
    with pytest.raises(ValueError):
        g.Template(tpl(INTEGER, derive={"big": expr}, wrong=["a + b"])).generate(1, seed=1)
    assert g.check_file([tpl(INTEGER, derive={"big": expr})])["hi_fixture_left"]


def test_a_very_long_computed_value_is_refused():
    t = tpl(INTEGER, derive={"s1": "person + person", **{f"s{i}": f"s{i - 1} + s{i - 1}" for i in range(2, 20)}})
    with pytest.raises(ValueError, match="longer than"):
        g.Template(t).generate(1, seed=1)


def test_a_draw_that_puts_the_answer_in_the_prompt_is_skipped():
    t = tpl(INTEGER, prompt="{a} में से {b} गए, {c} रहे? <answer>संख्या</answer>", derive={"c": "a - b"})
    with pytest.raises(ValueError, match="items after"):
        g.Template(t).generate(5, seed=1)


def test_too_few_distinct_prompts_is_an_error_not_a_loop():
    t = tpl(INTEGER, params={"a": {"int": [30, 31]}, "b": {"int": [5, 5]}, "person": {"pick": ["सीमा"]}})
    with pytest.raises(ValueError, match="2 of 10 items"):
        g.Template(t).generate(10, seed=1)


UNSAFE = ["__import__('os').system('true')", "a.__class__", "open('x')", "(lambda: 1)()", "2 ** 10",
          "[x for x in range(3)]", "a if b else c.d", "eval('1')", "digits(a, script='Deva')", "10 ** 99"]


@parametrize("expr", UNSAFE)
def test_unsafe_or_unknown_expressions_are_rejected(expr):
    assert any("bad expression" in p for p in g.check_template(tpl(INTEGER, answer=expr)))


def test_a_huge_constant_is_rejected():
    assert any("too large" in p for p in g.check_template(tpl(INTEGER, answer=str(10**13))))


def test_placeholders_must_be_plain_known_names():
    assert any("plain name" in p for p in g.check_template(tpl(INTEGER, prompt="{a.__class__} <answer>x</answer>")))
    assert any("plain name" in p for p in g.check_template(tpl(INTEGER, prompt="{} <answer>x</answer>")))
    assert any("no param" in p for p in g.check_template(tpl(INTEGER, prompt="{missing} <answer>x</answer>")))


def test_lint_catches_missing_fields_bad_values_and_the_answer_tag():
    assert any("missing wrong" in p for p in g.check_template({k: v for k, v in INTEGER.items() if k != "wrong"}))
    problems = g.check_template(tpl(INTEGER, script="Hira", answer_type="float", prompt="कितने बचे?"))
    assert any("script" in p for p in problems) and any("answer_type" in p for p in problems)
    assert any("<answer>" in p for p in problems)
    assert any("param a" in p for p in g.check_template(tpl(INTEGER, params={"a": {"int": [9, 1]}})))
    assert any("handle" in p for p in g.check_template(tpl(INTEGER, author="Some Person")))


def test_a_train_template_needs_a_team2_reviewer_who_is_not_the_author():
    assert any("team2_reviewer" in p for p in g.check_template(tpl(INTEGER, eligibility="train")))
    assert any("team2_reviewer" in p for p in g.check_template(tpl(INTEGER, eligibility="train",
                                                                    team2_reviewer="gmrammohan15")))
    assert g.check_template(tpl(INTEGER, eligibility="train", team2_reviewer="mittalutkarsh")) == []


def test_an_answer_of_the_wrong_type_is_a_template_error():
    with pytest.raises(ValueError, match="not an int"):
        g.Template(tpl(INTEGER, answer="person")).generate(1, seed=1)


def test_check_file_flags_repeated_ids():
    results = g.check_file([INTEGER, INTEGER])
    assert results["hi_fixture_left"] == [] and any("repeats" in p for p in results["hi_fixture_left#1"])


def test_shipped_template_file_is_a_valid_list():
    templates = g.load_templates(HERE / "templates" / "indic_templates.yaml")
    assert isinstance(templates, list) and not any(g.check_file(templates).values())


def test_cli_check_generate_and_empty_file(tmp_path):
    f = tmp_path / "t.yaml"
    f.write_text(yaml.safe_dump([INTEGER, WEEKDAY], allow_unicode=True), encoding="utf-8")
    cli = [sys.executable, str(HERE / "generate.py"), "--templates", str(f)]
    assert subprocess.run(cli + ["--check"], capture_output=True, check=False).returncode == 0
    out = tmp_path / "out" / "items.jsonl"
    r = subprocess.run(cli + ["--per-template", "50", "--out", str(out)], capture_output=True, text=True, check=True)
    summary = json.loads(r.stdout)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert summary["items"] == 100 == len(lines) and summary["train_items"] == 0
    assert {json.loads(x)["template"] for x in lines} == {"hi_fixture_left", "hi_fixture_weekday"}
    empty = tmp_path / "empty.yaml"
    empty.write_text("[]\n", encoding="utf-8")
    cli_empty = [sys.executable, str(HERE / "generate.py"), "--templates", str(empty), "--check"]
    assert subprocess.run(cli_empty, capture_output=True, check=False).returncode == 1
