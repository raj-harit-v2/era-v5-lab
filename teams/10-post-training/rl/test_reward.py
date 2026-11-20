"""Tests for reward.py (one entry point) and pool.py (the warm code-task container pool).

Offline tests use fake checkers and executors. Docker tests run only when docker and the images are present:
python:3.12-slim for code tasks, and g10-swe/python-validators__validators-191:v1 for the SWE env
(build it with `python swe-envs/verify.py swe-envs/python-validators__validators-191 --check --runs 1`).

Run:  python -m pytest teams/10-post-training/rl/test_reward.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import json
import os
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


needs_go_image = pytest.mark.skipif(
    not _has_image(os.environ.get("G10_GO_IMAGE", "g10-go-rl:1")), reason="docker or the g10-go-rl:1 image is missing")
needs_js_image = pytest.mark.skipif(
    not _has_image(os.environ.get("G10_JS_IMAGE", "g10-js-rl:1")), reason="docker or the g10-js-rl:1 image is missing")


def _node_v26_ready() -> bool:
    if not shutil.which("node"):
        return False
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5).stdout.strip()
        return int(out.lstrip("v").split(".")[0]) >= 26
    except Exception:
        return False


needs_node_v26 = pytest.mark.skipif(not _node_v26_ready(), reason="node 26+ is not available")
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
    assert len([i for i in ids if i.startswith("indic/")]) == len(list((HERE / "indic" / "tasks").glob("*/task.json")))
    assert len([i for i in ids if i.startswith("go/")]) == len(list((HERE / "go" / "tasks").glob("*/task.json")))
    assert len([i for i in ids if i.startswith("agentic/")]) == len(list((HERE / "agentic" / "tasks").glob("*/task.json")))
    assert len([i for i in ids if i.startswith("js/")]) == (len(list((HERE / "jsts" / "tasks" / "js").glob("*/task.json")))
                                                           + len(list((HERE / "js" / "tasks").glob("*/task.json"))))
    assert len([i for i in ids if i.startswith("ts/")]) == len(list((HERE / "jsts" / "tasks" / "ts").glob("*/task.json")))
    assert len([i for i in ids if i.startswith("math_pool/")]) == len(list((HERE / "math_pool" / "tasks").glob("*/task.json")))
    for i in ids:
        if i.startswith("math_pool/") and not os.environ.get("G10_MATH_POOL"):
            continue  # a math task's reference answer lives in the pool (rl/math_pool/README.md)
        good, bad = reward.known_outputs(i)
        assert good and bad and good != bad


def test_indic_envs_score_the_known_good_one_and_the_known_bad_zero_without_docker():
    ids = [i for i in reward.list_envs() if i.startswith("indic/")]
    assert ids
    rows = reward.check_all(workers=2, ids=ids)
    assert len(rows) == 2 * len(ids) and all(r["ok"] for r in rows), [r for r in rows if not r["ok"]]
    with pytest.raises(KeyError):
        reward.reward("indic/no_such_task", "<answer>1</answer>")


def test_go_is_registered_and_an_unknown_go_task_is_a_key_error():
    assert "go" in reward._REGISTRY
    assert [i for i in reward.list_envs() if i.startswith("go/")]
    with pytest.raises(KeyError):
        reward.reward("go/no_such_task", "```go\npackage main\n```")
    with pytest.raises(KeyError):
        reward.reward("go/../x", "x")


def test_go_checker_passes_the_sandbox_through_and_defaults_to_docker(monkeypatch):
    seen = []
    monkeypatch.setattr(reward._go(), "reward", lambda task_dir, out, sandbox: seen.append(sandbox) or {"reward": 1})
    name = next(i for i in reward.list_envs() if i.startswith("go/"))
    assert reward.reward(name, "x")[0] == 1.0
    runner = lambda work, t: None  # noqa: E731
    reward.reward(name, "x", sandbox=runner)
    assert seen == ["docker", runner]


def test_go_known_bad_output_has_the_reference_signature_and_no_reference_body():
    for env_id in [i for i in reward.list_envs() if i.startswith("go/")]:
        good, bad = reward.known_outputs(env_id)
        assert bad.startswith("```go\npackage main\n\nfunc ") and 'panic("stub")' in bad
        assert bad.count("\n") < 10 < good.count("\n")


@needs_go_image
def test_go_envs_score_the_known_good_one_and_the_known_bad_zero_in_docker():
    ids = [i for i in reward.list_envs() if i.startswith("go/")]
    rows = reward.check_all(workers=4, ids=ids)
    assert len(rows) == 2 * len(ids) and all(r["ok"] for r in rows), [r for r in rows if not r["ok"]]


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


def test_pool_module_loads_once_and_whole_when_many_threads_ask_at_once():
    import threading  # noqa: PLC0415

    fresh = _load("g10_rl_reward_threads", HERE / "reward.py")  # its _POOL_MODULE is still None
    start, got = threading.Barrier(16), []

    def ask():
        start.wait()
        m = fresh._pool()
        got.append((m, callable(getattr(m, "verifier_module", None))))  # what this thread sees when it gets it

    threads = [threading.Thread(target=ask) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(got) == 16 and len({id(m) for m, _ in got}) == 1
    assert all(whole for _, whole in got)  # no thread was handed a half-run module


def test_check_all_skips_math_pool_without_pool(monkeypatch, capsys):
    """A plain clone has no math pool: math ids are reported as skipped and the other sets are still checked."""
    monkeypatch.delenv("G10_MATH_POOL", raising=False)
    math_ids = [i for i in reward.list_envs() if i.startswith("math_pool/")]
    indic_ids = [i for i in reward.list_envs() if i.startswith("indic/")][:1]
    assert math_ids and indic_ids
    rows = reward.check_all(workers=2, ids=math_ids[:1] + indic_ids)
    by_type = {r["env_id"].split("/")[0]: r for r in rows}
    assert by_type["math_pool"]["skipped"] is True and by_type["math_pool"]["score"] is None
    assert all(r["ok"] for r in rows) and not by_type["indic"].get("skipped")
    assert reward.main(["--check-all", "--type", "math_pool"]) == 2
    assert '"skipped": %d' % (2 * len(math_ids)) in capsys.readouterr().out


# --- JS environments ----------------------------------------------------------------------------

def test_js_is_registered_and_an_unknown_js_task_is_a_key_error():
    assert "js" in reward._REGISTRY
    assert [i for i in reward.list_envs() if i.startswith("js/")]
    with pytest.raises(KeyError):
        reward.reward("js/no_such_task", "```javascript\nfunction f(){}\n```")
    with pytest.raises(KeyError):
        reward.reward("js/../x", "x")


def test_js_checker_passes_the_sandbox_through_and_defaults_to_docker(monkeypatch):
    seen = []
    monkeypatch.setattr(reward._js(), "reward", lambda task_dir, out, sandbox: seen.append(sandbox) or {"reward": 1})
    name = "js/camel_to_snake"  # an rl/js task; the Exercism js ids are listed first once both sets share the type
    assert reward.reward(name, "x")[0] == 1.0
    runner = lambda work, t: None  # noqa: E731
    reward.reward(name, "x", sandbox=runner)
    assert seen == ["docker", runner]


def test_js_known_outputs_are_well_formed():
    for env_id in [i for i in reward.list_envs() if i.startswith("js/")]:
        good, bad = reward.known_outputs(env_id)
        assert "```javascript" in good and "```javascript" in bad
        assert good != bad


@needs_js_image
def test_js_envs_score_the_known_good_one_and_the_known_bad_zero_in_docker():
    ids = [i for i in reward.list_envs() if i.startswith("js/")]
    rows = reward.check_all(workers=4, ids=ids)
    assert len(rows) == 2 * len(ids) and all(r["ok"] for r in rows), [r for r in rows if not r["ok"]]


@needs_node_v26
def test_js_env_scores_known_good_and_bad_through_reward_entry_point_in_process_sandbox():
    good, bad = reward.known_outputs("js/camel_to_snake")
    score_good, info_good = reward.reward("js/camel_to_snake", good, sandbox="process")
    score_bad, info_bad = reward.reward("js/camel_to_snake", bad, sandbox="process")
    assert score_good == 1.0
    assert score_bad == 0.0
    assert info_good["env_id"] == "js/camel_to_snake"
    assert info_bad["env_id"] == "js/camel_to_snake"
    assert info_good["reward"] == score_good
    assert info_bad["reward"] == score_bad
