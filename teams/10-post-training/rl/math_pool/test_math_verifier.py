"""Tests for math_verifier.py: one correct and one wrong answer per task, the adversarial cases, the pool pins.

Run:  python -m pytest teams/10-post-training/rl/math_pool/test_math_verifier.py -q -p no:cacheprovider
Needs `math-verify==0.9.0` for the scoring tests. The unit tests use FIXTURE records written below (a made-up pool,
labelled as fixtures, never part of any RL pool). The tests on the real task ids run only when G10_MATH_POOL points to
the RL data v1 math.jsonl, and say so in their skip reason.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_math_verifier", HERE / "math_verifier.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize
make_fixture = pytest.fixture

needs_mv = pytest.mark.skipif(importlib.util.find_spec("math_verify") is None, reason="math-verify is not installed")
REAL_POOL = os.environ.get("G10_MATH_POOL")
needs_pool = pytest.mark.skipif(not (REAL_POOL and Path(REAL_POOL).is_file()),
                                reason="set G10_MATH_POOL to the RL data v1 math.jsonl to test the real task ids")
TASK_DIRS = sorted(p.parent for p in v.TASKS.glob("*/task.json"))

# FIXTURE answers, one per answer shape. The problem text is a placeholder: the verifier never reads it.
FIXTURE = {"int": "5", "frac": "\\frac{1}{2}", "pair": "(1,2)", "root": "3\\sqrt{2}", "year": "2019"}


@make_fixture()
def fx(tmp_path):
    rows = [{"id": f"fixture-{k}", "problem": f"FIXTURE problem {k}", "answer": a, "subject": "algebra",
             "level": "Level 2", "licence": "MIT", "generator": "none (fixture)"} for k, a in FIXTURE.items()]
    pool = tmp_path / "fixture_pool.jsonl"
    pool.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    dirs = {}
    for r in rows:
        key = r["id"].split("-", 1)[1]
        d = tmp_path / "tasks" / key
        d.mkdir(parents=True)
        (d / "task.json").write_text(json.dumps(
            {"id": key, "pool_id": r["id"], "problem_sha256": v.sha256(r["problem"]),
             "answer_sha256": v.sha256(r["answer"])}), encoding="utf-8")
        dirs[key] = d

    def score(key: str, completion: str) -> dict:
        return v.reward(dirs[key], completion, pool)
    score.pool, score.dirs = pool, dirs
    return score


def box(a: str) -> str:
    return "Working it out.\n$\\boxed{" + a + "}$"


# --- correct and wrong ------------------------------------------------------------------------

@needs_mv
@parametrize("key", list(FIXTURE))
def test_the_reference_scores_one_and_a_wrong_answer_zero(fx, key):
    good, bad = v.known_outputs(fx.dirs[key], fx.pool)
    assert fx(key, good)["reward"] == 1
    assert fx(key, bad)["reward"] == 0


@needs_mv
@parametrize("key, answer", [
    ("frac", "\\frac12"), ("frac", "0.5"), ("frac", "\\dfrac{1}{2}"), ("int", "5.0"), ("int", " 5 "),
    ("root", "\\sqrt{18}"), ("pair", "(1, 2)"), ("int", "x=5"), ("int", "5\\text{ cm}"),
])
def test_equivalent_forms_of_the_right_answer_score_one(fx, key, answer):
    assert fx(key, box(answer))["reward"] == 1


@needs_mv
def test_a_thinking_span_then_the_answer_scores_one(fx):
    text = "<|think|>maybe \\boxed{4}\n<|/think|>\nThe answer is $\\boxed{5}$."
    assert fx("int", text)["reward"] == 1


# --- adversarial: the right number in the wrong form ---------------------------------------------

@needs_mv
@parametrize("key, answer", [
    ("int", "4, 5"),            # a list that contains the right number
    ("int", "5, 6"),
    ("pair", "(2,1)"),          # the ordered pair the other way round
    ("pair", "1"),              # one coordinate only
    ("frac", "2"),              # the reciprocal
    ("root", "18"),             # the radicand
    ("int", "\\text{the answer is 5 or 6}"),
    ("int", "5 or 6"),
])
def test_the_right_number_in_a_wrong_form_scores_zero(fx, key, answer):
    out = fx(key, box(answer))
    assert out["reward"] == 0, out


# --- adversarial: several answers listed ---------------------------------------------------------

@needs_mv
@parametrize("text", [
    "$\\boxed{4}$ or $\\boxed{5}$",
    "$\\boxed{5}$ or $\\boxed{4}$",
    "First guess $\\boxed{4}$, second guess $\\boxed{5}$.",
    "$\\boxed{5}$ and then $\\boxed{5.0}$",
    "\\boxed{5}\\boxed{6}",
])
def test_several_different_boxed_answers_score_zero(fx, text):
    out = fx("int", text)
    assert out["reward"] == 0 and out["reason"] == "several different boxed answers"


@needs_mv
def test_the_same_boxed_answer_repeated_is_fine(fx):
    assert fx("int", "$\\boxed{5}$ ... so again $\\boxed{5}$")["reward"] == 1


# --- adversarial: the answer buried in text ------------------------------------------------------

@needs_mv
@parametrize("text", [
    "The answer is 5.",
    "I think it is 4 maybe 5, so the final answer is 5",
    "Candidates: 4, 5, 6. The answer is 5.",
    "5",
    "$5$",
    "answer = $5$",
])
def test_a_correct_number_without_a_box_scores_zero(fx, text):
    out = fx("int", text)
    assert out["reward"] == 0 and out["reason"] == "no boxed answer"


@needs_mv
def test_a_boxed_answer_inside_the_think_span_does_not_count(fx):
    out = fx("int", "<|think|>\\boxed{5}\n<|/think|>\nI could not finish.")
    assert out["reward"] == 0 and out["reason"] == "no boxed answer"


@needs_mv
def test_unclosed_think_span_has_no_answer(fx):
    out = fx("int", "<|think|>\n$\\boxed{5}$")
    assert out["reward"] == 0 and out["reason"] == "think span not closed"


@needs_mv
def test_a_huge_boxed_answer_scores_zero(fx):
    out = fx("int", box("5" + "0" * 300))
    assert out["reward"] == 0


@needs_mv
@parametrize("text", ["\\boxed{}", "\\boxed{   }", "\\boxed{5", "boxed 5"])
def test_empty_or_unclosed_boxes_score_zero(fx, text):
    assert fx("int", text)["reward"] == 0


@needs_mv
def test_only_the_tail_of_a_huge_completion_is_read(fx):
    text = "$\\boxed{4}$ " + "filler " * 10_000 + "$\\boxed{5}$"
    assert fx("int", text)["reward"] == 1


# --- pins and the pool ----------------------------------------------------------------------------

def test_a_missing_pool_raises_it_never_scores_zero(fx, monkeypatch):
    monkeypatch.delenv("G10_MATH_POOL", raising=False)
    with pytest.raises(RuntimeError, match="math pool missing"):
        v.reward(fx.dirs["int"], box("5"))


def test_a_pool_record_that_does_not_match_the_pin_raises(fx, tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"id": "fixture-int", "problem": "FIXTURE problem int", "answer": "6"}) + "\n")
    with pytest.raises(RuntimeError, match="pins"):
        v.reward(fx.dirs["int"], box("5"), bad)


def test_a_record_missing_from_the_pool_raises(fx, tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    with pytest.raises(RuntimeError, match="not in math pool"):
        v.reward(fx.dirs["int"], box("5"), empty)


@needs_mv
def test_the_reply_never_contains_the_reference(fx):
    out = fx("year", box("2018"))
    assert "2019" not in json.dumps(out)


# --- the real task ids ------------------------------------------------------------------------------

def test_the_repository_holds_pins_only_and_no_problem_text():
    assert len(TASK_DIRS) >= 6
    for d in TASK_DIRS:
        files = sorted(p.name for p in d.iterdir())
        assert files == ["task.json"]
        meta = json.loads((d / "task.json").read_text(encoding="utf-8"))
        assert meta["licence"] == "MIT" and meta["generator"].startswith("none")
        assert meta["pool_id"] == "math-" + d.name
        assert set(meta) >= {"problem_sha256", "answer_sha256", "pool_id"}
        assert "problem" not in meta and "answer" not in meta


@needs_mv
@needs_pool
@parametrize("d", TASK_DIRS, ids=lambda d: d.name)
def test_real_task_reference_scores_one_and_wrong_scores_zero(d):
    assert v.check_task(d, REAL_POOL) == {"task_id": d.name, "ok": True, "problems": []}


@needs_mv
@needs_pool
def test_a_real_reference_answer_does_not_score_on_another_task():
    a, b = TASK_DIRS[0], TASK_DIRS[1]
    good_a, _ = v.known_outputs(a, REAL_POOL)
    assert v.reward(b, good_a, REAL_POOL)["reward"] == 0


@needs_pool
def test_real_tasks_are_train_rows_and_not_math500():
    for line in Path(REAL_POOL).read_text(encoding="utf-8").splitlines()[:50]:
        assert not json.loads(line)["id"].startswith("math500-")
    for d in TASK_DIRS:
        assert not json.loads((d / "task.json").read_text())["pool_id"].startswith("math500-")


def test_cli_reward_without_a_pool_fails_loudly(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("\\boxed{5}")
    env = {k: val for k, val in os.environ.items() if k != "G10_MATH_POOL"}
    proc = subprocess.run([sys.executable, str(HERE / "math_verifier.py"), "--reward", str(TASK_DIRS[0]), str(f)],
                          capture_output=True, text=True, env=env)
    assert proc.returncode != 0 and "math pool missing" in proc.stderr


def _reward_module():
    s = importlib.util.spec_from_file_location("g10_reward_for_math", HERE.parent / "reward.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_reward_py_lists_the_math_ids_and_a_missing_pool_raises(monkeypatch):
    r = _reward_module()
    ids = r.list_envs()
    assert {f"math_pool/{d.name}" for d in TASK_DIRS} <= set(ids)
    monkeypatch.delenv("G10_MATH_POOL", raising=False)
    with pytest.raises(RuntimeError, match="math pool missing"):
        r.reward(f"math_pool/{TASK_DIRS[0].name}", "\\boxed{1}")
    with pytest.raises(KeyError):
        r.reward("math_pool/no_such_task", "\\boxed{1}")


@needs_mv
@needs_pool
def test_reward_py_scores_a_real_task_through_the_one_entry_point():
    r = _reward_module()
    env_id = f"math_pool/{TASK_DIRS[0].name}"
    good, bad = r.known_outputs(env_id)
    assert r.reward(env_id, good, pool=REAL_POOL)[0] == 1.0
    assert r.reward(env_id, bad, pool=REAL_POOL)[0] == 0.0
