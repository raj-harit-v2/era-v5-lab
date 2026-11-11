"""Verifier for the RL code tasks: a model completion in, a binary reward out.

    reward(task_dir, completion) -> {"reward": 0 | 1, "reason": str, "passed": int, "total": int, ...}

How it resists cheating (see design_note.md):
  * The candidate's code runs in a child process that only receives INPUTS (cases.json). The expected outputs
    stay in this (parent) process and are never written to disk in the sandbox, so a forged result file,
    `sys.exit(0)`, printed output or a patched test harness cannot produce a pass: the child cannot know the answers.
  * Hidden and visible cases are mixed into one unlabeled list. The reward needs every case to pass.
  * The result is read from a file this module checks (count, types), never from stdout or the exit code.
  * Feedback never says which hidden case failed (only counts), so a policy cannot probe hidden tests one by one.

Two sandboxes:
  "process"  child process with resource limits, clean environment, own session, wall-clock kill of the process
             group. For unit tests and quick runs. It does NOT hide the task folder or block the network.
  "docker"   `docker run --network=none --read-only --cap-drop ALL --pids-limit ... --ulimit fsize` with only the work
             folder mounted. Use this for training. Needs the image named by G10_RL_IMAGE (default python:3.12-slim).

Task folder: task.json, prompt.md, visible_tests.json, hidden_tests.json, reference.py (see README.md).

CLI:
    python verifier.py --reward <task_dir> <completion.txt> [--sandbox docker]
    python verifier.py --check-task <task_dir> [--sandbox docker]     # lint + the reference must score 1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import resource
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHILD = HERE / "_sandbox_child.py"
MAX_CODE_CHARS = 20_000
CASE_TIMEOUT_S = 2.0
STARTUP_S = 3.0
MEM_BYTES = 512 * 1024 * 1024
MAX_RESULT_BYTES = 1_000_000  # results.json is written by the candidate's container: never read more than this
DEFAULT_IMAGE = os.environ.get("G10_RL_IMAGE", "python:3.12-slim")

_FENCE_LINE = re.compile(r"^[ \t]{0,3}```[ \t]*([^`\n]*?)[ \t]*$")
_PY_LABELS = {"", "python", "python3", "py"}


# --- parsing the completion -------------------------------------------------------------------

def extract_code(completion: str) -> tuple[str | None, str]:
    """Last fenced code block that is labelled python (or unlabelled). Returns (code, reason); code is None if unusable.

    Fences are read line by line and paired in order (open, close), so a block of another language (output, bash,
    text) between two python blocks cannot shift the pairing. A fence that is never closed is ignored.
    """
    blocks, opened, label, buf = [], False, "", []
    for line in (completion or "").splitlines():
        m = _FENCE_LINE.match(line)
        if m and not opened:
            opened, label, buf = True, m.group(1).lower(), []
        elif m and opened and m.group(1) == "":
            if label in _PY_LABELS:
                blocks.append("\n".join(buf) + "\n")
            opened = False
        elif opened:
            buf.append(line)
    if not blocks:
        return None, "no code block"
    code = blocks[-1]
    if "\x00" in code:
        return None, "NUL byte in code"
    if len(code) > MAX_CODE_CHARS:
        return None, "code block too long"
    if not code.strip():
        return None, "empty code block"
    return code, "ok"


# --- task files --------------------------------------------------------------------------------

def load_task(task_dir: Path) -> dict:
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    meta["visible"] = json.loads((task_dir / "visible_tests.json").read_text(encoding="utf-8"))
    meta["hidden"] = json.loads((task_dir / "hidden_tests.json").read_text(encoding="utf-8"))
    return meta


def _same(actual, expected) -> bool:
    """Equality on JSON data. Floats compare with a small tolerance; bool is not an int here."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    if isinstance(expected, float):  # an int is accepted where a float is expected, but not the other way round
        return (isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12))
    if isinstance(actual, float):
        return False  # expected is an int, a string, None or a container: a float is a different answer
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(_same(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(_same(actual[k], expected[k]) for k in expected)
    return type(actual) is type(expected) and actual == expected


def _case_ok(result: dict, case: dict) -> bool:
    if "raises" in case:
        return (not result.get("ok")) and case["raises"] in (result.get("mro") or [result.get("error")])
    return bool(result.get("ok")) and _same(result.get("value"), case["expected"])


def read_result_bytes(name: str | Path, dir_fd: int | None = None) -> bytes:
    """Bytes of the results file that the candidate's container wrote. The container can leave anything at this path
    (a symlink to a host file, a pipe, a huge file) and can still be running, so the file is opened without following a
    symlink (O_NOFOLLOW, without blocking on a pipe), must be a regular file, and at most MAX_RESULT_BYTES are read.
    Raises OSError or ValueError otherwise."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(name, flags, dir_fd=dir_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("result file is not a regular file")
        data = os.read(fd, MAX_RESULT_BYTES + 1)
        while len(data) <= MAX_RESULT_BYTES:
            more = os.read(fd, MAX_RESULT_BYTES + 1 - len(data))
            if not more:
                break
            data += more
    finally:
        os.close(fd)
    if len(data) > MAX_RESULT_BYTES:
        raise ValueError("result file is too large")
    return data


# --- running the child -------------------------------------------------------------------------

def _limits():  # runs in the child between fork and exec
    os.setsid()
    if sys.platform != "darwin":  # macOS refuses RLIMIT_AS
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10_000_000, 10_000_000))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))  # no fork, no threads (not enforced for root)


def _run_process(workdir: Path, entry: str, wall_s: float) -> str | None:
    """Returns an error string, or None if the child finished normally."""
    env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "LANG": "C.UTF-8"}
    # -s: no user site; -B: no .pyc files. PYTHONHASHSEED is fixed so set/dict-of-str order does not make rewards flaky.
    cmd = [sys.executable, "-B", "-s", str(workdir / "_child.py"), str(workdir), entry, str(CASE_TIMEOUT_S)]
    proc = subprocess.Popen(cmd, cwd=workdir, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, preexec_fn=_limits)
    try:
        proc.wait(timeout=wall_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        return "timeout"
    try:  # kill anything the child left in its process group
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    return None if proc.returncode == 0 else f"child exited with {proc.returncode}"


def _run_docker(workdir: Path, entry: str, wall_s: float) -> str | None:
    name = f"g10rl-{uuid.uuid4().hex[:12]}"
    cmd = ["docker", "run", "--rm", "--name", name, "--network=none", "--read-only", "--cap-drop", "ALL",
           "--security-opt", "no-new-privileges", "--pids-limit", "32", "--memory", "512m", "--memory-swap", "512m",
           "--cpus", "1", "--ulimit", "fsize=10000000:10000000", "--ulimit", "core=0",
           "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
           "--user", "65534:65534", "-e", "PYTHONHASHSEED=0",
           "-v", f"{workdir}:/work", "-w", "/work", DEFAULT_IMAGE,
           "python", "-B", "-s", "/work/_child.py", "/work", entry, str(CASE_TIMEOUT_S)]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=wall_s + 20)  # +20: container start-up
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return "timeout"
    return None if proc.returncode == 0 else f"container exited with {proc.returncode}"


# --- the reward --------------------------------------------------------------------------------

def reward(task_dir: Path | str, completion: str, sandbox="process") -> dict:
    """sandbox: "process", "docker", or a runner callable(workdir, entry, wall_s) -> error or None (rl/pool.py)."""
    task_dir = Path(task_dir)
    task = load_task(task_dir)
    out = {"task_id": task["id"], "reward": 0}
    code, why = extract_code(completion)
    if code is None:
        return {**out, "reason": why}
    cases = task["visible"] + task["hidden"]
    n = len(cases)
    order = sorted(range(n), key=lambda i: (i * 7919 + 13) % n)  # fixed shuffle: visible and hidden mixed
    wall_s = float(task.get("time_limit_s", 5)) + STARTUP_S

    # The work folder is a fresh temp dir that holds the solution and the INPUTS only.
    with tempfile.TemporaryDirectory(prefix="g10rl-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp)
        os.chmod(work, 0o700 if sandbox == "process" else 0o777)
        (work / "solution.py").write_text(code, encoding="utf-8")
        (work / "cases.json").write_text(
            json.dumps([{"args": cases[i].get("args", []), "kwargs": cases[i].get("kwargs", {})} for i in order]),
            encoding="utf-8")
        shutil.copyfile(CHILD, work / "_child.py")
        start = time.monotonic()
        runner = sandbox if callable(sandbox) else (_run_docker if sandbox == "docker" else _run_process)
        err = runner(work, task["entry_point"], wall_s)
        seconds = round(time.monotonic() - start, 2)
        if err:
            return {**out, "reason": err, "seconds": seconds}
        try:
            results = json.loads(read_result_bytes(work / "results.json").decode("utf-8"))
        except (OSError, ValueError):  # UnicodeDecodeError is a ValueError
            return {**out, "reason": "no readable result file", "seconds": seconds}

    if not (isinstance(results, list) and len(results) == n and all(isinstance(r, dict) for r in results)):
        return {**out, "reason": "result file has the wrong shape", "seconds": seconds}
    ok_flags = [False] * n
    for pos, i in enumerate(order):
        ok_flags[i] = _case_ok(results[pos], cases[i])
    nv = len(task["visible"])
    visible_passed = sum(ok_flags[:nv])
    hidden_passed = sum(ok_flags[nv:])
    passed = visible_passed + hidden_passed
    res = {**out, "reward": int(passed == n), "passed": passed, "total": n, "seconds": seconds,
           "visible_passed": f"{visible_passed}/{nv}", "hidden_passed_count": hidden_passed}
    res["reason"] = "all tests passed" if passed == n else f"{n - passed} test(s) failed"
    return res


# --- task lint ---------------------------------------------------------------------------------

def check_task(task_dir: Path | str, sandbox: str = "process") -> list[str]:
    """Problems with a task folder (empty list = fine). The reference solution must score 1."""
    task_dir = Path(task_dir)
    problems = []
    for f in ("task.json", "prompt.md", "visible_tests.json", "hidden_tests.json", "reference.py"):
        if not (task_dir / f).is_file():
            problems.append(f"missing {f}")
    if problems:
        return problems
    task = load_task(task_dir)
    for key in ("id", "entry_point", "time_limit_s", "difficulty", "source"):
        if key not in task:
            problems.append(f"task.json lacks {key}")
    if task.get("id") != task_dir.name:
        problems.append("task.json id differs from the folder name")
    if not str(task.get("source", "")).lower().startswith("original"):
        problems.append('source must start with "original" and name the author')
    if not 2 <= len(task["visible"]) <= 3:
        problems.append("need 2 or 3 visible tests")
    if len(task["hidden"]) < 10:
        problems.append("need at least 10 hidden tests")
    def key(c):
        return json.dumps([c.get("args", []), c.get("kwargs", {})], sort_keys=True)

    seen = {key(c) for c in task["visible"]}
    for c in task["hidden"]:
        if key(c) in seen:
            problems.append("a hidden test repeats a visible or earlier hidden input")
            break
        seen.add(key(c))
    prompt = (task_dir / "prompt.md").read_text(encoding="utf-8")
    entry = task.get("entry_point", "")
    for c in task["hidden"]:
        args, kwargs = c.get("args", []), c.get("kwargs", {})
        calls = set()
        for render in (repr, lambda a: json.dumps(a, ensure_ascii=False)):  # Python syntax and JSON syntax
            parts = [render(a) for a in args] + [f"{k}={render(v)}" for k, v in kwargs.items()]
            calls.add(f"{entry}({', '.join(parts)})")
        if any(call in prompt for call in calls):
            problems.append("a hidden test call appears in prompt.md")
            break
    for c in task["visible"] + task["hidden"]:
        if ("expected" in c) == ("raises" in c):
            problems.append('each test needs exactly one of "expected" or "raises"')
            break
    if task["entry_point"] not in prompt:
        problems.append("prompt.md does not mention the entry point name")
    if not isinstance(task.get("time_limit_s"), (int, float)) or task["time_limit_s"] <= 0:
        problems.append("time_limit_s must be a positive number")
    if problems:
        return problems
    ref = (task_dir / "reference.py").read_text(encoding="utf-8")
    res = reward(task_dir, f"```python\n{ref}\n```", sandbox)
    if res["reward"] != 1:
        problems.append(f"reference solution does not score 1: {res.get('reason')}")
    stub = f"def {task['entry_point']}(*args, **kwargs):\n    return None\n"
    if reward(task_dir, f"```python\n{stub}\n```", sandbox)["reward"] == 1:
        problems.append("a stub that returns None scores 1: the tests are too weak")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reward", nargs=2, metavar=("TASK_DIR", "COMPLETION_FILE"))
    ap.add_argument("--check-task", metavar="TASK_DIR")
    ap.add_argument("--sandbox", choices=("process", "docker"), default="process")
    args = ap.parse_args(argv)
    if args.reward:
        task_dir, comp = args.reward
        print(json.dumps(reward(task_dir, Path(comp).read_text(encoding="utf-8"), args.sandbox)))
        return 0
    if args.check_task:
        problems = check_task(args.check_task, args.sandbox)
        print("\n".join(problems) if problems else "task OK")
        return 1 if problems else 0
    ap.error("give --reward or --check-task")
    return 2


if __name__ == "__main__":
    sys.exit(main())
