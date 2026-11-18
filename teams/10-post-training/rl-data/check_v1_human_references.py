"""RL data v1: one correct and one wrong answer per verifier family, using human references only.

Runs the checkers the trainer and survey use (survey.score_one -> stdio_check.score in Docker, math_check.score) on
task records of the locally rebuilt RL data v1 (the data files are not in Git; see results/rl_data_v1_closure.md):
  stdio, per judge (aizu, atcoder, codechef, hackerearth): correct = a human solution from the pinned code_contests
        parquet row named by the record's provenance (Python 3, or Python 2 converted by lib2to3 for the judges
        that have only Python 2 references); wrong = the same program plus a final `print(0)`
  math: correct = the human reference answer in \\boxed{}; wrong = \\boxed{answer+1}
The SWE family (gold patch 1, no-op 0 through rl/reward.py) is already covered by
rl/test_reward.py::test_swe_env_scores_gold_one_and_noop_zero_from_parallel_workers and is not repeated here.

This is an integration check, run by naming the file (it is not collected by `pytest teams/10-post-training/rl-data`,
so CPU unit-test runs without the data are unaffected):

    G10_RL_V1_DIR=... G10_CC_SOURCE_DIR=... python -m pytest teams/10-post-training/rl-data/check_v1_human_references.py

Every missing input FAILS the test with its name (never a skip). Inputs (environment variables):
    G10_RL_V1_DIR      folder with cc.jsonl and math.jsonl of RL data v1
    G10_CC_SOURCE_DIR  folder with the pinned code_contests train parquets (revision 802411c3)
Docker with python:3.12-slim is needed for stdio. Nothing is printed from the data.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

JUDGES = ("aizu", "atcoder", "codechef", "hackerearth")
PY3, PY2 = 3, 1  # code_contests solutions.language codes


def _inputs():
    v1, src = os.environ.get("G10_RL_V1_DIR"), os.environ.get("G10_CC_SOURCE_DIR")
    if not v1 or not src:
        pytest.fail("missing input: set G10_RL_V1_DIR (RL data v1 cc.jsonl + math.jsonl) and G10_CC_SOURCE_DIR "
                    "(pinned code_contests train parquets); local data, not in Git", pytrace=False)
    v1, src = Path(v1), Path(src)
    for p in (v1 / "cc.jsonl", v1 / "math.jsonl", src):
        assert p.exists(), f"missing input: {p}"
    return v1, src


def _docker():
    assert shutil.which("docker"), "missing input: docker CLI"
    assert subprocess.run(["docker", "info"], capture_output=True).returncode == 0, "missing input: docker daemon"
    image = os.environ.get("G10_RL_IMAGE", "python:3.12-slim")
    r = subprocess.run(["docker", "image", "inspect", image], capture_output=True)
    assert r.returncode == 0, f"missing input: docker image {image} (docker pull {image})"


def _first_per_judge(path: Path) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            kept = out.setdefault(t["judge"], [])
            if len(kept) < 5:
                kept.append(t)
            if all(len(out.get(j, [])) >= 5 for j in JUDGES):
                break
    return out


def _human_solutions(src: Path, prov: dict) -> list[tuple[str, int]]:
    import pyarrow.parquet as pq
    row = pq.read_table(src / prov["file"], columns=["solutions"]).slice(prov["source_ordinal"], 1).to_pylist()[0]
    sol = row["solutions"] or {}
    pairs = list(zip(sol.get("solution", []), sol.get("language", [])))
    return [(s, PY3) for s, lang in pairs if lang == PY3] or [(s, PY2) for s, lang in pairs if lang == PY2]


def _to_py3(code: str) -> str:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from lib2to3.refactor import RefactoringTool, get_fixers_from_package  # noqa: PLC0415
    return str(RefactoringTool(get_fixers_from_package("lib2to3.fixes")).refactor_string(code.rstrip() + "\n", "x"))


def test_stdio_human_reference_scores_one_and_plus_print_zero_scores_zero_per_judge():
    v1, src = _inputs()
    _docker()
    import survey  # noqa: PLC0415
    import stdio_check  # noqa: PLC0415
    by_judge = _first_per_judge(v1 / "cc.jsonl")
    results = {}
    for judge in JUDGES:
        assert by_judge.get(judge), f"no {judge} task in {v1 / 'cc.jsonl'}"
        done = None
        for task in by_judge[judge]:  # some human solutions fail generated tests: first task+solution that passes
            for code, lang in _human_solutions(src, task["provenance"])[:3]:
                prog = code if lang == PY3 else _to_py3(code)
                if stdio_check.score(task, f"```python\n{prog}\n```")["reward"] == 1:
                    done = (task, prog, lang)
                    break
            if done:
                break
        assert done, f"{judge}: no human reference among the first 5 tasks x 3 solutions passed its own tests"
        task, prog, lang = done
        good = survey.score_one(("stdio", task, f"```python\n{prog}\n```"))[0]
        bad = survey.score_one(("stdio", task, f"```python\n{prog.rstrip()}\nprint(0)\n```"))[0]
        results[judge] = (good, bad, "py3" if lang == PY3 else "py2+lib2to3")
    assert all(g == 1 and b == 0 for g, b, _ in results.values()), {j: r[:2] for j, r in results.items()}


def test_math_reference_answer_scores_one_and_answer_plus_one_scores_zero():
    v1, _ = _inputs()
    import survey  # noqa: PLC0415
    with open(v1 / "math.jsonl", encoding="utf-8") as f:
        tasks = [json.loads(next(f)) for _ in range(5)]
    for t in tasks:
        a = t["answer"]
        good = survey.score_one(("math", t, f"The final answer is $\\boxed{{{a}}}$."))[0]
        bad = survey.score_one(("math", t, f"The final answer is $\\boxed{{{a}+1}}$."))[0]
        assert (good, bad) == (1, 0), t["id"]
