"""Tests for the RL data pipeline. Offline tests use made-up rows and fake samplers; the docker tests (stdio checker)
need docker and python:3.12-slim and skip otherwise.

The tiny statements in this file are test fixtures for the code, not task templates and not training data.

Run:  python -m pytest teams/10-post-training/rl-data/test_rl_data.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import easy_rung  # noqa: E402
import filter as pass_filter  # noqa: E402
import stdio_check  # noqa: E402


def _docker_ok() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", stdio_check.IMAGE], capture_output=True).returncode == 0


needs_docker = pytest.mark.skipif(not _docker_ok(), reason="UNTESTED: docker or python:3.12-slim missing")

ADD_TASK = {"id": "fixture-add", "statement": "fixture", "time_limit_s": 2,
            "tests": [{"input": "1 2\n", "output": "3\n"}, {"input": "10 -4\n", "output": "6"},
                      {"input": "0 0\n", "output": "0\n"}]}
CORRECT = "```python\na, b = map(int, input().split())\nprint(a + b)\n```"
WRONG = "```python\na, b = map(int, input().split())\nprint(a - b)\n```"


# --- comparison and building ------------------------------------------------------------------

def test_outputs_compare_by_tokens_like_a_judge():
    assert stdio_check.same_output("3\n", "3") and stdio_check.same_output("1  2\n3", "1 2 3\n")
    assert not stdio_check.same_output("3", "4") and not stdio_check.same_output("1 2", "12")


def _row(**kw):
    base = {"name": "x", "description": "statement", "source": 2, "cf_rating": 900, "cf_contest_id": 1,
            "cf_index": "A", "input_file": "", "output_file": "",
            "public_tests": {"input": ["1\n"], "output": ["1\n"]},
            "private_tests": {"input": ["2\n", "3\n"], "output": ["2\n", "3\n"]},
            "generated_tests": {"input": ["4\n"], "output": ["4\n"]}}
    return {**base, **kw}


def test_build_keeps_codeforces_rows_in_the_rating_band_and_records_provenance():
    rows = [_row(), _row(source=1), _row(cf_rating=1500), _row(input_file="in.txt"),
            _row(public_tests={"input": [], "output": []}, private_tests={"input": [], "output": []},
                 generated_tests={"input": [], "output": []})]
    out = build.code_contests_rows(rows, 800, 1200, max_tests=3)
    assert len(out) == 1
    t = out[0]
    assert t["id"] == "cf1A" and len(t["tests"]) == 3 and t["tests"][0] == {"input": "1\n", "output": "1\n"}
    assert t["licence"] == "CC-BY-4.0" and t["generator"].startswith("none") and t["licence_table_set"]


# --- the pass-rate filter -------------------------------------------------------------------

def test_decide_keeps_only_tasks_with_mixed_outcomes():
    assert pass_filter.decide([0, 1, 0, 0]) == "keep"
    assert pass_filter.decide([0, 0, 0, 0]) == "too_hard"
    assert pass_filter.decide([1, 1, 1]) == "too_easy"


def test_run_filter_counts_passes_per_task_with_a_fake_model():
    tasks = [{"id": "a", "statement": "A"}, {"id": "b", "statement": "B"}, {"id": "c", "statement": "C"}]
    rng = random.Random(0)

    def sample(prompt, seed):
        return {"A": "good", "B": "bad", "C": "good" if seed % 2 else "bad"}[prompt[0]]

    rows = pass_filter.run_filter(tasks, sample, k=4, score=lambda t, c: {"reward": int(c == "good")}, workers=2)
    by_id = {r["id"]: r for r in rows}
    assert by_id["a"]["decision"] == "too_easy" and by_id["b"]["decision"] == "too_hard"
    assert by_id["c"]["decision"] == "keep" and by_id["c"]["pass_rate"] == 0.5
    assert rng  # deterministic fake


def test_the_prompt_ends_with_the_io_instruction():
    seen = []
    pass_filter.run_filter([{"id": "a", "statement": "S"}], lambda p, s: seen.append(p) or "", k=1,
                           score=lambda t, c: {"reward": 0})
    assert seen[0].startswith("S") and "standard input" in seen[0] and "```python" in seen[0]


# --- easy rung (mechanics only; templates are written by people) ------------------------------

FIXTURE = {"id": "fixture", "author": "test", "statement": "fixture {a}", "input": "{a} {b}\n",
           "solution": "a, b = map(int, input().split())\nprint(a * b)\n",
           "params": {"a": {"int": [1, 9]}, "b": {"int": [1, 9]}}, "tests": 3}


def test_template_validation():
    assert easy_rung.validate(FIXTURE) == []
    assert "missing author" in easy_rung.validate({k: v for k, v in FIXTURE.items() if k != "author"})
    bad = {**FIXTURE, "statement": "fixture {c}"}
    assert any("placeholders without params" in p for p in easy_rung.validate(bad))
    bad = {**FIXTURE, "params": {"a": {"float": [0, 1]}, "b": {"int": [1, 2]}}}
    assert any("only {int" in p for p in easy_rung.validate(bad))


def test_generated_answers_come_from_running_the_reference_solution():
    tasks = easy_rung.generate(FIXTURE, 2, random.Random(1))
    assert len(tasks) == 2 and all(len(t["tests"]) == 3 for t in tasks)
    for t in tasks:
        for case in t["tests"]:
            a, b = map(int, case["input"].split())
            assert case["output"].strip() == str(a * b)
        assert "by test" in t["source"] and t["generator"].startswith("none")


def test_the_shipped_template_file_is_empty_until_people_write_templates():
    import yaml
    assert yaml.safe_load((HERE / "templates" / "easy_rung_templates.yaml").read_text()) == []


# --- the stdio checker (docker) ---------------------------------------------------------------

def test_expected_outputs_never_enter_the_sandbox(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kw):
        work = Path(cmd[cmd.index("-v") + 1].split(":")[0])
        seen["files"] = {p.name: p.read_text() for p in work.iterdir()}

        class P:
            returncode, stdout, stderr = 1, "", ""
        return P()

    monkeypatch.setattr(stdio_check.subprocess, "run", fake_run)
    stdio_check.score(ADD_TASK, CORRECT)
    assert sorted(seen["files"]) == ["inputs.json", "run.py", "solution.py"]
    assert json.loads(seen["files"]["inputs.json"]) == [t["input"] for t in ADD_TASK["tests"]]
    assert "6" not in seen["files"]["inputs.json"]  # an expected output that is not also an input


@needs_docker
def test_a_correct_program_scores_one_and_a_wrong_one_zero():
    assert stdio_check.score(ADD_TASK, CORRECT)["reward"] == 1
    r = stdio_check.score(ADD_TASK, WRONG)
    assert r["reward"] == 0 and r["reason"] == "wrong answer on a test"


@needs_docker
def test_a_program_that_forges_the_output_file_and_kills_the_runner_scores_zero():
    forge = ("```python\nimport json, os, signal\n"
             "json.dump([{'status': 'ok', 'stdout': '3'}] * 3, open('/work/outputs.json', 'w'))\n"
             "os.kill(os.getppid(), signal.SIGKILL)\n```")
    assert stdio_check.score(ADD_TASK, forge)["reward"] == 0


@needs_docker
def test_errors_and_timeouts_score_zero():
    assert stdio_check.score(ADD_TASK, "```python\nraise SystemExit(3)\n```")["reason"] == "error on a test"
    slow = {**ADD_TASK, "time_limit_s": 1}
    assert stdio_check.score(slow, "```python\nwhile True: pass\n```")["reason"] == "timeout on a test"
    assert stdio_check.score(ADD_TASK, "no code")["reward"] == 0


def test_statement_check_flags_example_only_statements():
    import importlib.util

    spec = importlib.util.spec_from_file_location("statement_check", HERE / "statement_check.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    full = "You are given two integers a and b. Print their sum on one line.\n\nInput\n\n1 2\n\nOutput\n\n3"
    assert sc.has_description(full) and sc.description_chars(full) == 64
    assert not sc.has_description("Example\n\nInput\n\n2 3 1 3 1 0\n\n\nOutput\n\n2")  # starts with the heading
    assert not sc.has_description("Sum\n\nExample\n\nInput\n\n1 2\n\nOutput\n\n3")      # a title is not a description
    assert not sc.has_description("input\n1 2\noutput\n3")
    assert sc.has_description("x" * 40) and not sc.has_description("x" * 39)
