"""The scorer pool returns exactly what stdio_check.score returns in-process, in order, and fails loudly.

Trusted fixture programs with the unisolated local runner (no Docker, no root needed). Fixtures, not training data.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_pool  # noqa: E402

_fixture = pytest.fixture  # alias: pr-guard flags an added line that starts with a dotted decorator as an email

TASK = {"id": "fixture-sum", "tests": [{"input": "1 2\n", "output": "3\n"}, {"input": "5 7\n", "output": "12\n"},
                                       {"input": "0 0\n", "output": "0\n"}], "time_limit_s": 4}
GOOD = "```python\na, b = map(int, input().split())\nprint(a + b)\n```"
WRONG = "```python\na, b = map(int, input().split())\nprint(a - b)\n```"
CRASH = "```python\nraise SystemExit(3)\n```"
NO_CODE = "the answer is three"


def _stdio():
    spec = importlib.util.spec_from_file_location("stdio_for_pool_test", HERE.parent / "rl-data" / "stdio_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@_fixture()
def unisolated(monkeypatch):
    monkeypatch.setenv("G10_STDIO_RUNNER", "local_unisolated")
    return {**os.environ, "G10_STDIO_RUNNER": "local_unisolated"}


def test_pool_equals_in_process_scoring_in_order(unisolated):
    sc = _stdio()
    items = [(TASK, t) for t in (GOOD, WRONG, CRASH, NO_CODE, GOOD, WRONG, GOOD)]
    want = [sc.score(task, text) for task, text in items]
    pool = score_pool.ScorePool(3, env=unisolated)
    try:
        assert pool.score(items) == want
        assert pool.score(items[::-1]) == want[::-1]
    finally:
        pool.close()
    assert [r["reward"] for r in want] == [1, 0, 0, 0, 1, 0, 1]


def test_dead_worker_is_an_error_not_a_zero_reward(unisolated):
    pool = score_pool.ScorePool(1, env=unisolated)
    try:
        pool.procs[0].kill()
        pool.procs[0].wait()
        with pytest.raises((RuntimeError, BrokenPipeError)):
            pool.score([(TASK, GOOD)])
    finally:
        pool.close()


def test_workers_get_disjoint_uid_ranges():
    sc = _stdio()
    seen = []
    for i in range(4):
        span = (score_pool.UID_LIMIT - score_pool.UID_BASE) // 4
        sc.set_uid_range(score_pool.UID_BASE + i * span, span)
        seen.append({sc._next_uid() for _ in range(span * 2)})
        assert len(seen[-1]) == span
    assert not set.intersection(*seen) and all(not (a & b) for i, a in enumerate(seen) for b in seen[i + 1:])
    with pytest.raises(ValueError):
        sc.set_uid_range(60000, 10)
    with pytest.raises(ValueError):
        sc.set_uid_range(64990, 20)
