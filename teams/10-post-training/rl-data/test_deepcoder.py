"""Tests for the DeepCoder adapter. Inline fixtures are for testing only."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_deepcoder as deepcoder  # noqa: E402
import stdio_check  # noqa: E402

parametrize = pytest.mark.parametrize


def fixture_row() -> dict:
    return {
        "problem": "Solve the following coding problem using the programming language Python. Print the sum.",
        "solutions": ["```python\na, b = map(int, input().split())\nprint(a + b)\n```"],
        "tests": json.dumps([
            {"type": "stdin_stdout", "input": "2 3\n", "output": "5\n"},
            {"type": "stdin_stdout", "input": "4 -1\n", "output": "3\n"},
        ]),
    }


def test_converts_to_stdio_task_with_pinned_source():
    task = deepcoder.convert_row(fixture_row(), 42)
    assert task["id"].endswith("/42")
    assert task["licence_table_set"] == "rl-code-deepcoder"
    assert f"@{deepcoder.REVISION}/primeintellect/" in task["source"]
    assert task["tests"] == [
        {"input": "2 3\n", "output": "5\n"},
        {"input": "4 -1\n", "output": "3\n"},
    ]


@parametrize("tests", [
    "",
    "[]",
    '[{"type": "function_call", "input": "1", "output": "2"}]',
    '[{"type": "stdin_stdout", "input": "1", "output": 2}]',
    json.dumps([{"type": "stdin_stdout", "input": "1", "output": "2"}] * (stdio_check.MAX_TESTS + 1)),
])
def test_skips_unsupported_or_incomplete_cases(tests):
    assert deepcoder.convert_row({**fixture_row(), "tests": tests}, 0) is None


def test_skips_non_python_problem():
    row = fixture_row()
    row["problem"] = row["problem"].replace("Python", "Java")
    assert deepcoder.convert_row(row, 0) is None


def test_skips_problem_with_only_blank_expected_outputs():
    row = fixture_row()
    cases = json.loads(row["tests"])
    for case in cases:
        case["output"] = " \n"
    row["tests"] = json.dumps(cases)
    assert deepcoder.convert_row(row, 0) is None


def test_skips_unfenced_python_reference():
    row = fixture_row()
    row["solutions"] = ["a, b = map(int, input().split())\nprint(a + b)"]
    assert deepcoder.convert_row(row, 0) is None


def test_docker_verifier_scores_correct_and_wrong_python(monkeypatch):
    if not shutil.which("docker") or subprocess.run(
        ["docker", "image", "inspect", stdio_check.IMAGE], capture_output=True
    ).returncode:
        pytest.skip("Docker with the Python sandbox image is required")
    monkeypatch.setattr(stdio_check, "RUNNER_KIND", "docker")
    task = deepcoder.convert_row(fixture_row(), 0)
    correct = stdio_check.score(task, task["reference"])
    wrong = stdio_check.score(task, deepcoder.WRONG)
    subtraction = "```python\na, b = map(int, input().split())\nprint(a - b)\n```"
    wrong_value = stdio_check.score(task, subtraction)
    assert (correct["reward"], correct["passed"], correct["total"]) == (1, 2, 2)
    assert (wrong["reward"], wrong["reason"]) == (0, "wrong answer on a test")
    assert (wrong_value["reward"], wrong_value["reason"]) == (0, "wrong answer on a test")
