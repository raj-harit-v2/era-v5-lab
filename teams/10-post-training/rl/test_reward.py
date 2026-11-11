"""Tests for reward.py (one entry point) and pool.py (the warm code-task container pool).

Offline tests use fake checkers and executors. Docker tests run only when docker and the images are present:
python:3.12-slim for code tasks, and g10-swe/python-validators__validators-191:v1 for the SWE env
(build it with `python swe-envs/verify.py swe-envs/python-validators__validators-191 --check --runs 1`).

Run:  python -m pytest teams/10-post-training/rl/test_reward.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


reward = _load("g10_rl_reward_under_test", HERE / "reward.py")
pool = reward._pool()


def _has_image(image: str) -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0


needs_code_image = pytest.mark.skipif(not _has_image(pool.CODE_IMAGE), reason="docker or python:3.12-slim missing")
SWE_ENV = "python-validators__validators-191"
needs_swe_image = pytest.mark.skipif(not _has_image(f"g10-swe/{SWE_ENV}:v1"), reason="SWE env image missing")


def setup_function(function):
    reward.configure()


def teardown_function(function):
    reward.configure()


# --- the entry point ---------------------------------------------------------------------------

def test_reward_dispatches_on_the_env_type_and_returns_score_and_info():
    seen = {}

    def checker(name, output, **options):
        seen.update(name=name, output=output)
        return {"reward": 1, "reason": "fake"}

    reward.register("faketype", checker)
    score, info = reward.reward("faketype/thing-1", "out")
    assert score == 1.0 and info["reward"] == 1 and info["env_id"] == "faketype/thing-1"
    assert seen == {"name": "thing-1", "output": "out"}


UNSAFE_IDS = ["nope/x", "code", "code/", "code/../../etc", "code/a/b", "swe/.hidden", ""]


def test_unknown_or_unsafe_env_ids_raise_instead_of_scoring_zero():
    for env_id in UNSAFE_IDS:
        with pytest.raises(KeyError):
            reward.reward(env_id, "out")


def test_a_missing_task_raises():
    with pytest.raises(KeyError):
        reward.reward("code/no_such_task", "out")
    with pytest.raises(KeyError):
        reward.reward("swe/no_such_env", "out")


def test_a_checker_without_a_binary_reward_is_an_error():
    reward.register("brokentype", lambda name, output, **o: {"reward": 0.5})
    with pytest.raises(ValueError):
        reward.reward("brokentype/x", "out")


def test_configure_passes_the_pooled_runners_to_the_built_in_checkers(monkeypatch):
    calls = []
    monkeypatch.setattr(pool.verifier_module(), "reward", lambda d, out, runner: calls.append(("code", runner)) or {"reward": 0})
    monkeypatch.setattr(pool.swe_verify_module(), "reward", lambda d, out, ex: calls.append(("swe", ex)) or {"reward": 0})
    code_runner, swe_executor = object(), object()
    reward.configure(code_runner=code_runner, swe_executor=swe_executor)
    reward.reward("code/parse_duration", "x")
    reward.reward(f"swe/{SWE_ENV}", "x")
    reward.configure()
    reward.reward("code/parse_duration", "x")
    reward.reward(f"swe/{SWE_ENV}", "x")
    assert calls == [("code", code_runner), ("swe", swe_executor), ("code", "docker"), ("swe", None)]


def test_list_envs_covers_every_shipped_task_and_env():
    ids = reward.list_envs()
    assert len([i for i in ids if i.startswith("code/")]) == len(list((HERE / "tasks").glob("*/task.json")))
    assert len([i for i in ids if i.startswith("swe/")]) == len(list((HERE.parent / "swe-envs").glob("*/env.json")))
    for i in ids:
        good, bad = reward.known_outputs(i)
        assert good and bad and good != bad


def test_swe_integrity_checks_hold_with_any_executor(monkeypatch):
    """A forged junit report (the attack from the PR #27 review) still scores 0 when a pool executor runs it."""
    verify = pool.swe_verify_module()
    env = verify.load_env(HERE.parent / "swe-envs" / SWE_ENV)
    cases = "".join(f'<testcase classname="{t.split("::")[0]}" name="{t.split("::", 1)[1]}"/>'
                    for t in env["FAIL_TO_PASS"] + env["PASS_TO_PASS"])
    forged = (f"@@G10_EXIT 1@@\n{verify.REPORT_START}\n<testsuites><testsuite>{cases}</testsuite></testsuites>\n"
              f"{verify.REPORT_END}\n{verify.SUMMARY_START}\n2 failed, 7 passed in 0.1s\n{verify.SUMMARY_END}\n")
    monkeypatch.setattr(verify, "ensure_image", lambda *a: "sha256:fake")
    score, info = reward.reward(f"swe/{SWE_ENV}", reward.NOOP_PATCH, executor=lambda *a: (forged, ""))
    assert score == 0 and "sentinel" in info["reason"]


# --- code pool (docker) ------------------------------------------------------------------------

@needs_code_image
def test_code_pool_gives_the_same_verdicts_as_one_container_per_call():
    with pool.CodePool(workers=2) as cp:
        for task in ("parse_duration", "weighted_median"):
            good, bad = reward.known_outputs(f"code/{task}")
            for out in (good, bad):
                plain = reward.reward(f"code/{task}", out)[0]
                pooled = reward.reward(f"code/{task}", out, sandbox=cp.runner)[0]
                assert plain == pooled
            assert reward.reward(f"code/{task}", good, sandbox=cp.runner)[0] == 1.0


def _probe_task(tmp_path: Path) -> Path:
    """A task whose answer is a description of what is left over in the container from earlier rollouts."""
    d = tmp_path / "probe_task"
    d.mkdir()
    clean = {"tmp": [], "procs": [], "pool_entries": 1}
    (d / "task.json").write_text(json.dumps({"id": "probe_task", "title": "probe", "entry_point": "probe",
                                             "time_limit_s": 5, "difficulty": "easy", "source": "original: test",
                                             "tags": []}))
    (d / "prompt.md").write_text("probe")
    (d / "visible_tests.json").write_text(json.dumps([{"args": [], "expected": clean}]))
    (d / "hidden_tests.json").write_text(json.dumps([{"args": [], "expected": clean}]))
    return d


PROBE = '''
import os
def probe():
    me = os.getpid()
    procs = sorted(int(p) for p in os.listdir("/proc") if p.isdigit() and int(p) not in (1, me))
    return {"tmp": sorted(os.listdir("/tmp")), "procs": procs, "pool_entries": len(os.listdir("/pool"))}
'''

PLANT = '''
import os, subprocess
def probe():
    open("/tmp/planted", "w").write("x")
    try:
        open("/pool/planted", "w").write("x")
    except OSError:
        pass
    subprocess.Popen(["sleep", "300"], start_new_session=True)
    return {"tmp": [], "procs": [], "pool_entries": 1}
'''


@needs_code_image
def test_a_reused_container_carries_nothing_into_the_next_rollout(tmp_path):
    verifier = pool.verifier_module()
    task = _probe_task(tmp_path)
    with pool.CodePool(workers=1) as cp:  # one worker: both rollouts run in the same container
        first = cp._all[0].name
        assert verifier.reward(task, "```python\n" + PROBE + "\n```", cp.runner)["reward"] == 1  # clean to start
        verifier.reward(task, "```python\n" + PLANT + "\n```", cp.runner)
        after = verifier.reward(task, "```python\n" + PROBE + "\n```", cp.runner)
        assert cp._all[0].name == first, "the container should have been reused, not restarted"
        assert after["reward"] == 1, after


@needs_code_image
def test_a_forged_results_file_still_scores_zero_through_the_pool():
    forge = ('import json, os\n'
             'n = len(json.load(open(os.path.join(os.path.dirname(__file__), "cases.json"))))\n'
             'json.dump([{"ok": True, "value": 0}] * n, open(os.path.join(os.path.dirname(__file__), "results.json"), "w"))\n'
             'os._exit(0)\n'
             'def parse_duration(s):\n    return 0\n')
    with pool.CodePool(workers=1) as cp:
        assert reward.reward("code/parse_duration", "```python\n" + forge + "```", sandbox=cp.runner)[0] == 0.0


@needs_code_image
def test_a_timeout_recycles_the_container():
    slow = "```python\nimport time\ndef parse_duration(s):\n    time.sleep(60)\n```"
    with pool.CodePool(workers=1) as cp:
        before = cp._all[0].name
        assert reward.reward("code/parse_duration", slow, sandbox=cp.runner)[0] == 0.0
        assert cp._all[0].name != before


# --- SWE envs (docker, one fresh container per call) -------------------------------------------

@needs_swe_image
def test_swe_env_scores_gold_one_and_noop_zero_from_parallel_workers():
    from concurrent.futures import ThreadPoolExecutor
    good, bad = reward.known_outputs(f"swe/{SWE_ENV}")
    with ThreadPoolExecutor(4) as ex:
        scores = list(ex.map(lambda out: reward.reward(f"swe/{SWE_ENV}", out)[0], [good, bad, good, bad]))
    assert scores == [1.0, 0.0, 1.0, 0.0]


def test_pool_does_not_copy_a_symlinked_results_file(monkeypatch, tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("[]")

    def fake_docker(*args, timeout=60):
        out = ""
        if args[0] == "exec" and any(str(a).endswith("/_child.py") for a in args):
            rid = next(str(a) for a in args if str(a).endswith("/_child.py")).split("/")[2]
            (worker.dir / rid / "results.json").symlink_to(outside)  # what a hostile candidate could leave behind
        elif args[0] == "exec":
            out = "clean"
        return subprocess.CompletedProcess(args, 0, out, "")

    monkeypatch.setattr(pool, "_docker", fake_docker)
    worker = pool._CodeWorker("img", 5)
    work = tmp_path / "work"
    work.mkdir()
    (work / "_child.py").write_text("")
    try:
        err = worker.run(work, "f", 1.0)
    finally:
        worker.close()
    assert err == "result file is not a regular file or is too large"
    assert not (work / "results.json").exists()


def test_pool_does_not_follow_a_replaced_slot_folder(monkeypatch, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "results.json").write_text("[]")

    def fake_docker(*args, timeout=60):
        out = ""
        if args[0] == "exec" and any(str(a).endswith("/_child.py") for a in args):
            rid = next(str(a) for a in args if str(a).endswith("/_child.py")).split("/")[2]
            shutil.rmtree(worker.dir / rid)  # the candidate removes its slot folder and puts a symlink in its place
            (worker.dir / rid).symlink_to(other)
        elif args[0] == "exec":
            out = "clean"
        return subprocess.CompletedProcess(args, 0, out, "")

    monkeypatch.setattr(pool, "_docker", fake_docker)
    worker = pool._CodeWorker("img", 5)
    work = tmp_path / "work"
    work.mkdir()
    (work / "_child.py").write_text("")
    try:
        err = worker.run(work, "f", 1.0)
    finally:
        worker.close()
    assert err == "result file is not a regular file or is too large"
    assert not (work / "results.json").exists()
