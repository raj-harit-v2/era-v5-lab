"""Tests of rl-data/free_reward_ids.py on a tiny synthetic tasks file (no real task text).

    python -m pytest rl-data/test_free_reward_ids.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import free_reward_ids as fr  # noqa: E402


def _t(i, tests):
    return {"id": i, "tests": [{"input": a, "output": b} for a, b in tests]}


TASKS = [
    _t("const", [("1 2\n", "YES\n"), ("3 4", "YES"), ("9 9\n", " YES \n")]),                 # whole 1.0 (judge tokens)
    _t("percase", [("2\n1\n2\n", "No\nNo\n"), ("3\n5\n6\n7\n", "No\nNo\nNo\n")]),            # whole 0, per-case 1.0
    _t("mixed", [("2\n1\n2\n", "No\nYes\n"), ("1\n4\n", "No\n"), ("2\n3\n3\n", "No\nNo\n")]),  # per-case 2/3
    _t("real", [("1 2", "3"), ("2 2", "4"), ("5 5", "10"), ("0 0", "0")]),                      # whole 1/4, per-case n/a
    _t("multi", [("x\n", "1 2\n"), ("y\n", "1 2")]),                                            # two-token constant
]


def test_scores_use_judge_tokens_and_the_per_case_rule():
    got = {r["id"]: r for r in fr.audit(TASKS)}
    assert got["const"]["whole"] == 1.0 and got["const"]["reason"] == "constant-output"
    assert got["percase"]["whole"] == 0.5 and got["percase"]["per_case"] == 1.0
    assert got["percase"]["reason"] == "per-case-constant"
    assert abs(got["mixed"]["per_case"] - 2 / 3) < 1e-9 and got["mixed"]["reason"] is None
    assert got["real"]["whole"] == 0.25 and got["real"]["per_case"] is None and got["real"]["reason"] is None
    assert got["multi"]["whole"] == 1.0 and got["multi"]["per_case"] is None


def test_only_the_scored_tests_count():
    tests = [("a", "A")] * fr.MAX_TESTS + [("b", "B")] * 5
    assert fr.audit([_t("long", tests)])[0] == {"id": "long", "n_tests": fr.MAX_TESTS, "whole": 1.0,
                                                "per_case": None, "reason": "constant-output"}


def test_max_tests_matches_the_reward():
    spec = importlib.util.spec_from_file_location("g10_stdio_check_free", HERE / "stdio_check.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    assert fr.MAX_TESTS == sc.MAX_TESTS


def test_append_new_keeps_existing_lines_and_is_idempotent(tmp_path, capsys):
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text("".join(json.dumps(t) + "\n" for t in TASKS))
    ids = tmp_path / "free.txt"
    ids.write_text("old-1\tsample-hardcode\nconst\tYES\n")
    report = tmp_path / "r.tsv"
    assert fr.main(["--tasks", str(tasks), "--existing", str(ids), "--report", str(report), "--append-new"]) == 0
    assert ids.read_text().splitlines() == ["old-1\tsample-hardcode", "const\tYES", "multi\tconstant-output",
                                            "percase\tper-case-constant"]
    s = json.loads(capsys.readouterr().out)
    assert (s["free_reward"], s["already_listed"], s["new"], s["existing_not_free_by_this_rule"]) == (3, 1, 2, 1)
    assert report.read_text().splitlines()[3] == "real\t4\t0.2500\tn/a"
    fr.main(["--tasks", str(tasks), "--existing", str(ids), "--append-new"])
    assert len(ids.read_text().splitlines()) == 4
