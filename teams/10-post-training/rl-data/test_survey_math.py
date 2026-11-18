"""Tests for the math checker, the MATH and non-Codeforces builders, and the survey (with a fake sampler).

The strings below are checker test cases, not training data. No decorators with a dot (pr-guard).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import build_math  # noqa: E402
import math_check  # noqa: E402
import survey  # noqa: E402

needs_math_verify = pytest.mark.skipif(importlib.util.find_spec("math_verify") is None,
                                       reason="UNTESTED: math-verify is not installed, so math_check.score was not run")


# --- math checker -------------------------------------------------------------------------------

def test_last_boxed_handles_nesting_spaces_and_fbox():
    assert math_check.last_boxed(r"so \boxed{1} then \boxed{\frac{a}{b}}") == r"\frac{a}{b}"
    assert math_check.last_boxed(r"answer \boxed 5 done") == "5"
    assert math_check.last_boxed(r"\fbox{x+1}") == "x+1"
    assert math_check.last_boxed("no box here") is None
    assert math_check.last_boxed(r"\boxed{unbalanced") is None


@needs_math_verify
def test_math_score_accepts_equivalent_forms_and_rejects_wrong_ones():
    task = {"id": "t", "answer": r"\frac{1}{2}"}
    assert math_check.score(task, r"The answer is $\boxed{0.5}$.")["reward"] == 1
    assert math_check.score(task, r"The answer is $\boxed{\dfrac{1}{2}}$.")["reward"] == 1
    assert math_check.score(task, r"The answer is $\boxed{2}$.")["reward"] == 0
    assert math_check.score(task, "I don't know.")["reward"] == 0


# --- builders -----------------------------------------------------------------------------------

def test_math_rows_take_the_last_boxed_answer_and_skip_unboxed_solutions():
    rows = [{"problem": "p1", "solution": r"first \boxed{3}, final \boxed{4}", "level": "Level 1"},
            {"problem": "p2", "solution": "no boxed answer", "level": "Level 2"},
            {"problem": "p3", "solution": r"\boxed{x^2}", "level": "Level 5"}]
    got, skipped = build_math.math_rows("algebra", rows)
    assert skipped == 1 and [t["id"] for t in got] == ["math-algebra-0", "math-algebra-2"]
    assert got[0]["answer"] == "4" and got[0]["kind"] == "math" and got[0]["licence"] == "MIT"
    assert "none" in got[0]["generator"]


def _cc_row(source, name, n_tests=3, **kw):
    tests = {"input": [f"{i}\n" for i in range(n_tests)], "output": [f"{i}\n" for i in range(n_tests)]}
    return {"source": source, "name": name, "description": "statement", "public_tests": tests,
            "private_tests": {}, "generated_tests": {}, "input_file": "", "output_file": "", "difficulty": 1, **kw}


def test_other_judge_rows_skip_codeforces_file_io_and_thin_tests():
    rows = [_cc_row(6, "p00001 A"), _cc_row(2, "cf"), _cc_row(5, "abc001_a", n_tests=2),
            _cc_row(1, "chef", input_file="in.txt"), _cc_row(6, "p00001 A")]
    got = build.other_judge_rows(rows, {1, 3, 5, 6}, max_tests=20)
    assert [t["id"] for t in got] == ["cc-aizu-p00001_A", "cc-aizu-p00001_A-2"]  # duplicates get a suffix
    assert got[0]["kind"] == "stdio" and got[0]["judge"] == "aizu" and len(got[0]["tests"]) == 3


# --- survey -------------------------------------------------------------------------------------

def test_render_uses_the_placeholder_and_refuses_a_file_without_one():
    t = {"id": "m", "kind": "math", "problem": "What is 1+1?", "answer": "2"}
    assert survey.render(t, {"math": None}) == "What is 1+1?"
    assert survey.render(t, {"math": "Q: {problem}\nA:"}) == "Q: What is 1+1?\nA:"
    with pytest.raises(ValueError):
        survey.render(t, {"math": "no placeholder"})


@needs_math_verify
def test_run_survey_decides_keep_too_hard_too_easy_and_counts_tokens():
    tasks = [{"id": "a", "kind": "math", "problem": "x", "answer": "2", "subject": "algebra", "level": "Level 1"},
             {"id": "b", "kind": "math", "problem": "y", "answer": "3", "subject": "algebra", "level": "Level 1"},
             {"id": "c", "kind": "math", "problem": "z", "answer": "4", "subject": "geometry", "level": "Level 2"}]
    answers = {"x": [r"\boxed{2}", r"\boxed{5}"], "y": [r"\boxed{1}", r"\boxed{1}"], "z": [r"\boxed{4}", r"\boxed{4}"]}

    def fake_generate(texts, k):
        return [[(answers[t][j], 10 + j, j == 1) for j in range(k)] for t in texts]

    rows, timing = survey.run_survey(tasks, [t["problem"] for t in tasks], fake_generate, k=2, workers=2,
                                     pool="thread")
    assert [r["decision"] for r in rows] == ["keep", "too_hard", "too_easy"]
    assert rows[0]["pass_rate"] == 0.5 and rows[0]["mean_tokens_correct"] == 10.0 and rows[1]["truncated"] == 0.5
    assert rows[0]["reasons"] == {"correct": 1, "wrong answer": 1} and rows[0]["boxed"] == 2
    assert timing["sampled_tokens"] == 63
    by = survey.summarise(rows)
    assert by["math/algebra/Level 1"]["keep"] == 1 and by["math/geometry/Level 2"]["too_easy"] == 1
    assert "problem" not in json.dumps(rows)  # ids and numbers only


@needs_math_verify
def test_run_survey_scores_in_worker_processes():
    tasks = [{"id": "a", "kind": "math", "problem": "x", "answer": "2"}]
    rows, _ = survey.run_survey(tasks, ["x"], lambda texts, k: [[(r"\boxed{2}", 3, False)] * k for _ in texts],
                                k=2, workers=1, pool="process")
    assert rows[0]["solved"] == 2 and rows[0]["decision"] == "too_easy"


def test_survey_refuses_to_run_without_an_instruction_file(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text(json.dumps({"id": "m", "kind": "math", "problem": "p", "answer": "1"}) + "\n")
    with pytest.raises(SystemExit):
        survey.main(["--tasks", str(f), "--model", "unused", "--out", str(tmp_path / "o.json")])


# --- stdio checker, local runner (used inside Modal, where there is no Docker) -----------------

def _local_score(code, tests, limit=2):
    import stdio_check
    old = stdio_check.RUNNER_KIND
    stdio_check.RUNNER_KIND = "local_unisolated"  # trusted fixture programs only; the isolated runner needs Linux root
    try:
        task = {"id": "t", "tests": tests, "time_limit_s": limit}
        return stdio_check.score(task, "```python\n" + code + "\n```")
    finally:
        stdio_check.RUNNER_KIND = old


def test_local_runner_scores_right_wrong_crashing_and_hanging_programs():
    tests = [{"input": "2 3\n", "output": "5\n"}, {"input": "10 -4\n", "output": "6"}]
    assert _local_score("a, b = map(int, input().split())\nprint(a + b)", tests)["reward"] == 1
    assert _local_score("a, b = map(int, input().split())\nprint(a - b)", tests)["reward"] == 0
    r = _local_score("raise SystemExit(3)", tests)
    assert r["reward"] == 0 and "error" in r["reason"]
    r = _local_score("while True:\n    pass", tests, limit=1)
    assert r["reward"] == 0 and "timeout" in r["reason"]


def test_chat_ids_handle_a_batch_encoding():
    # transformers 5.x apply_chat_template(tokenize=True) returns a BatchEncoding (dict-like, not a dict);
    # B1 on 5 Nov failed because list() of it gave the key names instead of token ids
    from transformers import BatchEncoding

    class Tok:
        def apply_chat_template(self, msgs, add_generation_prompt, tokenize):
            return BatchEncoding({"input_ids": [5, 6, 7], "attention_mask": [1, 1, 1]})

    ids = Tok().apply_chat_template([], add_generation_prompt=True, tokenize=True)
    got = [int(x) for x in (ids["input_ids"] if hasattr(ids, "keys") else ids)]
    assert got == [5, 6, 7]
    if not (HERE.parent / "rl-loop" / "tasks.py").exists():
        pytest.skip("UNTESTED: rl-loop/tasks.py is not on this branch, so the source check of survey.py and "
                    "rl-loop/tasks.py did not run")
    src = (HERE / "survey.py").read_text() + (HERE.parent / "rl-loop" / "tasks.py").read_text()
    assert "isinstance(ids, dict)" not in src and src.count('hasattr(ids, "keys")') == 2


@needs_math_verify
def test_failure_reasons_separate_no_answer_from_wrong_answer():
    tasks = [{"id": "a", "kind": "math", "problem": "x", "answer": "2"}]
    outs = [r"\boxed{2}", "I am not sure.", r"\boxed{3}"]
    rows, _ = survey.run_survey(tasks, ["x"], lambda texts, k: [[(o, 5, False) for o in outs]], k=3, workers=1,
                                pool="thread")
    assert rows[0]["reasons"] == {"correct": 1, "no answer found": 1, "wrong answer": 1}
    assert rows[0]["boxed"] == 2


def test_math500_rows_are_eval_only_records():
    got = build_math.math500_rows([{"problem": "p", "answer": "3", "level": 2, "subject": "Algebra",
                                    "unique_id": "test/algebra/1.json"}])
    assert got[0]["id"] == "math500-test_algebra_1_json" and got[0]["level"] == "Level 2"
    assert "evaluation only" in got[0]["source"]


def test_isolated_local_runner_fails_closed_without_linux_root():
    import stdio_check
    ok, why = stdio_check.isolation_available()
    if ok:
        pytest.skip("this machine can isolate (Linux root): covered by the Modal isolation probe instead")
    old = stdio_check.RUNNER_KIND
    stdio_check.RUNNER_KIND = "local"
    try:
        with pytest.raises(RuntimeError, match="refused"):
            stdio_check.run_program("print(1)", ["\n"], 2)
    finally:
        stdio_check.RUNNER_KIND = old
