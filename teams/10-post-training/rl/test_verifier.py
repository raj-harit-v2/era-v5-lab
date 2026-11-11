"""Tests for verifier.py: a correct and a wrong answer, then the cheating cases from design_note.md.

Run:  python -m pytest teams/10-post-training/rl/test_verifier.py -q -p no:cacheprovider
Docker tests run only when `docker` and the image G10_RL_IMAGE (default python:3.12-slim) are present locally.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verifier as v  # noqa: E402

TASK = Path(__file__).resolve().parent / "tests" / "fixtures" / "digit_sum_fixture"

CORRECT = """
def digit_sum(n, base=10):
    if base < 2 or n < 0:
        raise ValueError("bad")
    t = 0
    while n:
        n, d = divmod(n, base)
        t += d
    return t
"""
# fails the hidden tests (ignores the base) but passes the visible example 1
WRONG = """
def digit_sum(n, base=10):
    return sum(int(c) for c in str(n))
"""


def fence(code: str) -> str:
    return "Here is my answer.\n```python\n" + textwrap.dedent(code).strip() + "\n```\n"


def score(code: str, sandbox: str = "process") -> dict:
    return v.reward(TASK, fence(code), sandbox)


# --- correct and wrong ---------------------------------------------------------------------------

def test_correct_answer_scores_one():
    r = score(CORRECT)
    assert r["reward"] == 1 and r["passed"] == r["total"] == 16


def test_wrong_answer_scores_zero_and_hides_which_hidden_test_failed():
    r = score(WRONG)
    assert r["reward"] == 0 and r["passed"] < r["total"]
    assert set(r) <= {"task_id", "reward", "reason", "passed", "total", "seconds", "visible_passed", "hidden_passed_count"}


def test_visible_only_solution_fails_hidden():
    r = score("def digit_sum(n, base=10):\n    return 6 if n == 123 else 30")
    assert r["reward"] == 0 and r["visible_passed"] == "2/2"


# --- parsing the completion ---------------------------------------------------------------------

def test_no_code_block_scores_zero():
    assert v.reward(TASK, "I think the answer is 6.")["reason"] == "no code block"


def test_last_code_block_is_used():
    completion = fence(WRONG) + "\nOops, corrected:\n" + fence(CORRECT)
    assert v.reward(TASK, completion)["reward"] == 1


def test_missing_entry_point_scores_zero():
    assert score("def other(n):\n    return n")["reward"] == 0


def test_oversized_and_nul_code_are_refused():
    assert v.reward(TASK, "```python\n" + "x = 1\n" * 10000 + "```")["reason"] == "code block too long"
    assert v.reward(TASK, "```python\nx = 1\x00\n```")["reason"] == "NUL byte in code"


def test_a_non_python_block_between_python_blocks_does_not_shift_the_pairing():
    completion = ("```python\nA = 1\n```\nOutput:\n```text\nhello\n```\nFinal answer:\n"
                  "```python\n" + textwrap.dedent(CORRECT).strip() + "\n```\n")
    assert v.extract_code(completion)[0].lstrip().startswith("def digit_sum")
    assert v.reward(TASK, completion)["reward"] == 1


def test_unlabelled_blocks_count_and_other_languages_do_not():
    assert v.extract_code("```\nx = 1\n```")[0] == "x = 1\n"
    assert v.extract_code("```bash\nls\n```")[1] == "no code block"
    assert v.extract_code("```python\nx = 1\n")[1] == "no code block"  # never closed (a cut-off answer)


def test_a_subclass_of_the_expected_exception_is_accepted():
    r = score("""
        def digit_sum(n, base=10):
            if base < 2 or n < 0:
                raise UnicodeError("a ValueError subclass")
            t = 0
            while n:
                n, d = divmod(n, base)
                t += d
            return t
    """)
    assert r["reward"] == 1


def _run_child(tmp_path, code, cases, entry="f"):
    w = Path(tempfile.mkdtemp(dir=tmp_path))
    (w / "solution.py").write_text(textwrap.dedent(code))
    (w / "cases.json").write_text(json.dumps(cases))
    shutil.copyfile(v.CHILD, w / "_child.py")
    assert v._run_process(w, entry, 10) is None
    return json.loads((w / "results.json").read_text())


def test_a_shared_mutable_return_value_is_captured_at_return_time(tmp_path):
    res = _run_child(tmp_path, """
        shared = []
        def f(x):
            shared.clear()
            shared.append(x)
            return shared  # the same list object every call
    """, [{"args": [1], "kwargs": {}}, {"args": [2], "kwargs": {}}])
    assert [r["value"] for r in res] == [[1], [2]]


def test_set_iteration_order_is_the_same_on_every_run(tmp_path):
    runs = {json.dumps(_run_child(tmp_path, "def f(x):\n    return ''.join({'x', 'y', 'z', 'w', 'q'})", [{"args": [1], "kwargs": {}}]))
            for _ in range(5)}
    assert len(runs) == 1


# --- cheating cases ------------------------------------------------------------------------------

def test_sys_exit_at_import_scores_zero():
    assert score("import sys\nsys.exit(0)\n" + CORRECT)["reward"] == 0


def test_os_exit_at_import_scores_zero():
    assert score("import os\nos._exit(0)\n" + CORRECT)["reward"] == 0


def test_sys_exit_inside_the_function_scores_zero():
    r = score("import sys\ndef digit_sum(n, base=10):\n    sys.exit(0)")
    assert r["reward"] == 0


def test_printing_the_expected_output_does_not_help():
    r = score("""
        print("PASSED 16/16 reward=1")
        def digit_sum(n, base=10):
            print(6, 30)
            return 0
    """)
    assert r["reward"] == 0


def test_forged_result_file_cannot_match_unknown_answers():
    # Writes results.json for every case with the visible answers, at import and again from atexit.
    r = score("""
        import atexit, json, os
        def forge():
            res = [{"ok": True, "value": 6}] * 16
            open(os.path.join(os.getcwd(), "results.json"), "w").write(json.dumps(res))
        forge(); atexit.register(forge)
        def digit_sum(n, base=10):
            return 6
    """)
    assert r["reward"] == 0


def test_patching_json_and_builtins_cannot_create_correct_answers():
    r = score("""
        import json, builtins
        json.dumps = lambda *a, **k: "[]"
        builtins.print = lambda *a, **k: None
        def digit_sum(n, base=10):
            return 0
    """)
    assert r["reward"] == 0


def test_sandbox_folder_holds_inputs_only_no_expected_values(monkeypatch):
    seen = {}
    real = v._run_process

    def spy(workdir, entry, wall_s):
        seen["files"] = sorted(p.name for p in workdir.iterdir())
        seen["cases"] = (workdir / "cases.json").read_text()
        return real(workdir, entry, wall_s)

    monkeypatch.setattr(v, "_run_process", spy)
    assert score(CORRECT)["reward"] == 1
    assert seen["files"] == ["_child.py", "cases.json", "solution.py"]
    cases = json.loads(seen["cases"])
    assert len(cases) == 16 and all(set(c) == {"args", "kwargs"} for c in cases)
    assert "raises" not in seen["cases"]


def test_reading_the_inputs_does_not_reveal_answers():
    r = score("""
        import json, os
        cases = json.load(open(os.path.join(os.getcwd(), "cases.json")))
        def digit_sum(n, base=10):
            return len(cases)
    """)
    assert r["reward"] == 0


def test_infinite_loop_in_function_times_out():
    t = time.time()
    r = score("def digit_sum(n, base=10):\n    while True:\n        pass")
    assert r["reward"] == 0 and time.time() - t < 30


def test_infinite_loop_at_import_times_out():
    t = time.time()
    r = score("while True:\n    pass\ndef digit_sum(n, base=10):\n    return 0")
    assert r["reward"] == 0 and time.time() - t < 30


def test_sleeping_long_is_killed():
    t = time.time()
    r = score("import time\ntime.sleep(60)\ndef digit_sum(n, base=10):\n    return 0")
    assert r["reward"] == 0 and time.time() - t < 30


def test_memory_bomb_scores_zero():
    r = score("x = bytearray(4 * 1024**3)\ndef digit_sum(n, base=10):\n    return 0")
    assert r["reward"] == 0


def test_fork_bomb_scores_zero_and_returns():
    t = time.time()
    r = score("import os\nwhile True:\n    os.fork()\ndef digit_sum(n, base=10):\n    return 0")
    assert r["reward"] == 0 and time.time() - t < 30


def test_flooding_stdout_does_not_matter():
    r = score(CORRECT + "\nfor _ in range(20000):\n    print('x' * 100)\n")
    assert r["reward"] == 1  # output is discarded, never parsed


def test_writing_big_files_is_limited():
    r = score("""
        f = open("big.bin", "wb")
        f.write(b"0" * 50_000_000)
        def digit_sum(n, base=10):
            return 0
    """)
    assert r["reward"] == 0


# --- result strictness ---------------------------------------------------------------------------

def test_bool_is_not_an_int():
    assert v._same(True, 1) is False and v._same(1, True) is False and v._same(1, 1) is True


def test_floats_use_a_tolerance_and_containers_are_compared_deeply():
    assert v._same(0.1 + 0.2, 0.3) and not v._same(0.31, 0.3)
    assert v._same([1, {"a": [2]}], [1, {"a": [2]}]) and not v._same([1, 2], [1, 2, 3])
    assert v._same(2, 2.0) and not v._same(2.0, 2)  # an int is fine where a float is expected, not the reverse
    assert not v._same("2", 2) and not v._same(None, 0) and not v._same([], {})


def test_a_raising_case_needs_the_named_error():
    r = score("""
        def digit_sum(n, base=10):
            if base < 2 or n < 0:
                raise RuntimeError("wrong type")
            return 0
    """)
    assert r["reward"] == 0


def test_non_json_return_value_fails():
    r = score("def digit_sum(n, base=10):\n    return {n}")
    assert r["reward"] == 0


def test_result_file_with_the_wrong_shape_is_zero(monkeypatch):
    def fake(workdir, entry, wall_s):
        (workdir / "results.json").write_text(json.dumps([{"ok": True, "value": 1}]))
        return None
    monkeypatch.setattr(v, "_run_process", fake)
    r = score(CORRECT)
    assert r["reward"] == 0 and "wrong shape" in r["reason"]


def test_missing_result_file_is_zero(monkeypatch):
    monkeypatch.setattr(v, "_run_process", lambda workdir, entry, wall_s: None)
    assert score(CORRECT)["reward"] == 0


# --- task lint and CLI ---------------------------------------------------------------------------

def test_fixture_task_passes_the_lint():
    assert v.check_task(TASK) == []


def test_lint_catches_a_wrong_reference_and_repeated_inputs(tmp_path):
    t = tmp_path / "digit_sum_fixture"
    shutil.copytree(TASK, t)
    (t / "reference.py").write_text(WRONG)
    assert any("reference solution does not score 1" in p for p in v.check_task(t))
    (t / "reference.py").write_text((TASK / "reference.py").read_text())
    hidden = json.loads((t / "hidden_tests.json").read_text())
    hidden.append(hidden[0])
    (t / "hidden_tests.json").write_text(json.dumps(hidden))
    assert any("repeats" in p for p in v.check_task(t))


def test_lint_catches_source_not_original(tmp_path):
    t = tmp_path / "digit_sum_fixture"
    shutil.copytree(TASK, t)
    meta = json.loads((t / "task.json").read_text())
    meta["source"] = "adapted from a benchmark"
    (t / "task.json").write_text(json.dumps(meta))
    assert any("original" in p for p in v.check_task(t))


def test_lint_catches_a_prompt_without_the_function_name(tmp_path):
    t = tmp_path / "digit_sum_fixture"
    shutil.copytree(TASK, t)
    (t / "prompt.md").write_text("Sum the digits.\n")
    assert any("entry point" in p for p in v.check_task(t))


def test_lint_catches_a_hidden_call_copied_into_the_prompt(tmp_path):
    t = tmp_path / "digit_sum_fixture"
    shutil.copytree(TASK, t)
    hidden = json.loads((t / "hidden_tests.json").read_text())
    h = next(c for c in hidden if "expected" in c and len(c["args"]) == 1)
    (t / "prompt.md").write_text((t / "prompt.md").read_text() + "- `digit_sum(%r)` is `%r`\n" % (h["args"][0], h["expected"]))
    assert any("hidden test call" in p for p in v.check_task(t))


def test_lint_catches_tests_that_a_stub_returning_none_would_pass(tmp_path):
    t = tmp_path / "digit_sum_fixture"
    shutil.copytree(TASK, t)
    (t / "visible_tests.json").write_text(json.dumps([{"args": [1], "expected": None}, {"args": [2], "expected": None}]))
    (t / "hidden_tests.json").write_text(json.dumps([{"args": [i], "expected": None} for i in range(3, 15)]))
    (t / "reference.py").write_text("def digit_sum(n, base=10):\n    return None\n")
    assert any("stub" in p for p in v.check_task(t))


def test_cli_reward(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text(fence(CORRECT))
    out = subprocess.run([sys.executable, str(Path(v.__file__)), "--reward", str(TASK), str(f)],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["reward"] == 1


# --- docker sandbox (skipped when docker or the image is missing) --------------------------------

def _docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "image", "inspect", v.DEFAULT_IMAGE], capture_output=True)
    return r.returncode == 0


docker = pytest.mark.skipif(not _docker_ready(), reason="docker or the image is not available")


@docker
def test_docker_correct_and_wrong():
    assert score(CORRECT, "docker")["reward"] == 1
    assert score(WRONG, "docker")["reward"] == 0


FINDS_HIDDEN_FILE = """
    import os
    found = [d for d, _, fs in os.walk("/") for f in fs if f == "hidden_tests.json"]
    def digit_sum(n, base=10):
        if found:
            return -1  # a cheater would use the file here; this probe just makes the result wrong
        t = 0
        if base < 2 or n < 0:
            raise ValueError("bad")
        while n:
            n, d = divmod(n, base)
            t += d
        return t
"""


def test_process_mode_does_not_hide_the_task_folder():
    """Documents the limit of the process sandbox: the hidden file is on the same disk. Use docker for training."""
    assert score(FINDS_HIDDEN_FILE, "process")["reward"] == 0


@docker
def test_docker_hides_the_task_folder_and_hidden_tests():
    assert score(FINDS_HIDDEN_FILE, "docker")["reward"] == 1  # nothing to find, so the probe stays honest


@docker
def test_docker_has_no_network():
    r = score("""
        import socket
        reachable = True
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1).close()
        except OSError:
            reachable = False
        def digit_sum(n, base=10):
            if reachable:
                return -1
            t = 0
            if base < 2 or n < 0:
                raise ValueError("bad")
            while n:
                n, d = divmod(n, base)
                t += d
            return t
    """, "docker")
    assert r["reward"] == 1


@docker
def test_docker_root_filesystem_is_read_only():
    r = score("""
        def _try():
            try:
                open("/etc/g10_probe", "w").close()
                return True
            except OSError:
                return False
        writable = _try()
        def digit_sum(n, base=10):
            if writable:
                return -1
            t = 0
            if base < 2 or n < 0:
                raise ValueError("bad")
            while n:
                n, d = divmod(n, base)
                t += d
            return t
    """, "docker")
    assert r["reward"] == 1


@docker
def test_docker_fork_bomb_is_contained():
    t = time.time()
    r = score("import os\nwhile True:\n    os.fork()\ndef digit_sum(n, base=10):\n    return 0", "docker")
    assert r["reward"] == 0 and time.time() - t < 60


@docker
def test_docker_writing_a_huge_file_is_stopped_before_it_fills_the_disk():
    r = score("""
        with open("/work/big.bin", "wb") as f:
            for _ in range(500):
                f.write(b"0" * 1_000_000)
        def digit_sum(n, base=10):
            return 0
    """, "docker")
    assert r["reward"] == 0


def test_symlinked_result_file_is_not_read(monkeypatch, tmp_path):
    secret = tmp_path / "outside.json"
    secret.write_text(json.dumps([{"ok": True, "value": 1}]))

    def fake(workdir, entry, wall_s):
        (workdir / "results.json").symlink_to(secret)
        return None
    monkeypatch.setattr(v, "_run_process", fake)
    r = score(CORRECT)
    assert r["reward"] == 0 and "no readable result file" in r["reason"]


def test_oversized_result_file_is_not_read(monkeypatch):
    def fake(workdir, entry, wall_s):
        (workdir / "results.json").write_text("[" + " " * (v.MAX_RESULT_BYTES + 1) + "]")
        return None
    monkeypatch.setattr(v, "_run_process", fake)
    r = score(CORRECT)
    assert r["reward"] == 0 and "no readable result file" in r["reason"]


def test_read_result_bytes_reads_a_small_regular_file_and_refuses_the_rest(tmp_path):
    f = tmp_path / "r.json"
    f.write_text("[]")
    assert v.read_result_bytes(f) == b"[]"
    with pytest.raises(OSError):
        v.read_result_bytes(tmp_path / "missing.json")
    with pytest.raises(ValueError):  # a directory
        v.read_result_bytes(tmp_path)
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (v.MAX_RESULT_BYTES + 1))
    with pytest.raises(ValueError):
        v.read_result_bytes(big)
    link = tmp_path / "link.json"
    link.symlink_to(f)
    with pytest.raises(OSError):
        v.read_result_bytes(link)
    fifo = tmp_path / "fifo.json"
    os.mkfifo(fifo)
    with pytest.raises(ValueError):  # must not block on a pipe
        v.read_result_bytes(fifo)
