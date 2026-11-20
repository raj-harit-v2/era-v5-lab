"""Binary reward for JavaScript code tasks: the JS counterpart of go_verifier.py, same design.

The candidate's JS code and the cases run in a Node.js sandbox that gets INPUTS ONLY. The generic
runner (_js_runner.js) calls the entry point on each input via Worker threads and writes the outputs.
This process compares the outputs with the expected values, which never enter the sandbox, so there
is nothing to forge.

Task folder (tasks/<task_id>/ in this folder): task.json, prompt.md, visible_tests.json,
hidden_tests.json, reference.js (see README.md).

A case is {"args": [...], "expected": <json>} or {"args": [...], "raises": "<ExceptionName>"}.

The candidate answers with one JS block that defines a function with the name given in entry_point.

    python js_verifier.py --reward <task_dir> <completion.txt> [--sandbox docker]
    python js_verifier.py --check-task <task_dir> [--sandbox docker]   # lint + reference must score 1

Sandboxes:
    process  Node.js runs on this machine. For unit tests only: no network or file isolation.
             Needs `node` (26 or later) on PATH.
    docker   --network=none, read-only root, no capabilities, 768 MB, 1 CPU, 128 pids, non-root,
             only the work folder mounted. Use this for training. Needs the image from js.Dockerfile
             (G10_JS_IMAGE, default g10-js-rl:1). A missing image or daemon raises RuntimeError.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "_js_runner.js"
JS_IMAGE = os.environ.get("G10_JS_IMAGE", "g10-js-rl:1")

# Keep constants in sync with rl/verifier.py.
MAX_CODE_CHARS = 20_000
# CASE_TIMEOUT_S is the default per-case timeout; tasks override it via time_limit_s in task.json.
CASE_TIMEOUT_S = 2.0
STARTUP_S = 5.0
MAX_RESULT_BYTES = 1_000_000

_FENCE_LINE = re.compile(r"^[ \t]{0,3}```[ \t]*([^`\n]*?)[ \t]*$")
_JS_LABELS = {"", "js", "javascript", "mjs"}
_IDENT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")

# Exit codes from the container script.
_RC_CHILD = 4   # runner exited non-zero (infrastructure problem, not the candidate)

_TIMEOUT_MIN = 0.1    # seconds — consistent with the runner's 100 ms floor
_TIMEOUT_MAX = 300.0  # seconds — prevents runaway timeouts


def _check_time_limit(value) -> str | None:
    """Return an error string if value is not a valid per-case timeout, else None.

    Accepts finite numeric values in [_TIMEOUT_MIN, _TIMEOUT_MAX].
    Rejects booleans (isinstance(bool, int) is True in Python), strings, NaN, infinity,
    and anything outside the permitted range.
    math.isfinite is applied only to floats; integers are always finite, and Python's
    arbitrary-precision comparison handles extremely large integers cleanly."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"time_limit_s must be a finite number in [{_TIMEOUT_MIN}, {_TIMEOUT_MAX}]"
    if isinstance(value, float) and not math.isfinite(value):
        return f"time_limit_s must be a finite number in [{_TIMEOUT_MIN}, {_TIMEOUT_MAX}]"
    if value < _TIMEOUT_MIN or value > _TIMEOUT_MAX:
        return f"time_limit_s must be a finite number in [{_TIMEOUT_MIN}, {_TIMEOUT_MAX}]"
    return None


# ---------------------------------------------------------------------------
# Shared utilities (pure-Python equivalents of rl/verifier.py helpers;
# kept in sync manually — see go_verifier.py for the same pattern).
# ---------------------------------------------------------------------------

def _same(actual, expected) -> bool:
    """Equality on JSON data. Floats compare with small tolerance; bool is not an int here."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(actual, float):
        return False
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(actual) == len(expected)
                and all(_same(a, e) for a, e in zip(actual, expected)))
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and actual.keys() == expected.keys()
                and all(_same(actual[k], expected[k]) for k in expected))
    return type(actual) is type(expected) and actual == expected


def _read_result_bytes(name: str | Path, dir_fd: int | None = None) -> bytes:
    """Safe read of the results file: rejects symlinks, non-files, and files over MAX_RESULT_BYTES."""
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


def load_task(task_dir: Path) -> dict:
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    meta["visible"] = json.loads((task_dir / "visible_tests.json").read_text(encoding="utf-8"))
    meta["hidden"] = json.loads((task_dir / "hidden_tests.json").read_text(encoding="utf-8"))
    return meta


# ---------------------------------------------------------------------------
# Sandbox runners
# ---------------------------------------------------------------------------

def _run_process(workdir: Path, task_time_s: float) -> str | None:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is not on PATH; install Node.js 26 or later")
    wall_s = task_time_s + STARTUP_S
    entry = (workdir / "_entry").read_text(encoding="utf-8").strip()
    case_timeout_s = float((workdir / "_case_timeout").read_text(encoding="utf-8").strip())
    cmd = [node, str(workdir / "runner.js"), str(workdir), entry, str(case_timeout_s)]
    # Inherit the full environment for the process sandbox (no isolation required — it is for tests only).
    proc = subprocess.Popen(
        cmd, cwd=workdir,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        proc.wait(timeout=wall_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return "timeout"
    return None if proc.returncode == 0 else f"runner exited with {proc.returncode}"


def _run_docker(workdir: Path, task_time_s: float) -> str | None:
    if not shutil.which("docker"):
        raise RuntimeError("docker is not on PATH; install Docker and ensure the daemon is running")
    entry = (workdir / "_entry").read_text(encoding="utf-8").strip()
    case_timeout_s = float((workdir / "_case_timeout").read_text(encoding="utf-8").strip())
    wall_s = task_time_s + STARTUP_S + 20
    name = f"g10js-{uuid.uuid4().hex[:12]}"
    script = (
        "node /work/runner.js /work %s %s >/dev/null 2>&1 </dev/null || exit %d"
        % (entry, case_timeout_s, _RC_CHILD)
    )
    cmd = [
        "docker", "run", "--rm", "--name", name,
        "--network=none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "128", "--memory", "768m", "--memory-swap", "768m",
        "--cpus", "1", "--ulimit", "fsize=67108864:67108864", "--ulimit", "core=0",
        "--tmpfs", "/tmp:rw,nosuid,size=64m",
        "--user", "65534:65534", "-e", "HOME=/tmp",
        "-v", f"{workdir}:/work", "-w", "/work", JS_IMAGE,
        "sh", "-c", script,
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=wall_s)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return "timeout"
    rc = proc.returncode
    if rc == 0:
        return None
    if rc == _RC_CHILD:
        return "runner exited with an error"
    if rc in (125, 126, 127):
        tail = proc.stderr.decode("utf-8", "replace")[-300:].strip()
        raise RuntimeError(
            f"docker sandbox failed (exit {rc}; is the image {JS_IMAGE!r} built?): {tail}"
        )
    return f"container exited with {rc}"


# ---------------------------------------------------------------------------
# Core verifier
# ---------------------------------------------------------------------------

def extract_code(completion: str) -> tuple[str | None, str]:
    """Last fenced block labelled js/javascript/mjs (or unlabelled)."""
    blocks, opened, label, buf = [], False, "", []
    for line in (completion or "").splitlines():
        m = _FENCE_LINE.match(line)
        if m and not opened:
            opened, label, buf = True, m.group(1).lower(), []
        elif m and opened and m.group(1) == "":
            if label in _JS_LABELS:
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


def _case_ok(result: dict, case: dict) -> bool:
    if "raises" in case:
        return (not result.get("ok")) and result.get("error") == case["raises"]
    return bool(result.get("ok")) and _same(result.get("value"), case["expected"])


def reward(task_dir: Path | str, completion: str, sandbox="process") -> dict:
    """sandbox: "process", "docker", or a callable(workdir, task_time_s) -> error_str | None."""
    task_dir = Path(task_dir)
    task = load_task(task_dir)
    out = {"task_id": task["id"], "reward": 0}
    code, why = extract_code(completion)
    if code is None:
        return {**out, "reason": why}
    entry = task["entry_point"]
    if not _IDENT.match(entry):
        return {**out, "reason": "bad entry_point name in task.json"}
    cases = task["visible"] + task["hidden"]
    n = len(cases)
    order = sorted(range(n), key=lambda i: (i * 7919 + 13) % n)
    # time_limit_s in task.json is the per-case timeout for this task.
    # CASE_TIMEOUT_S is the fallback default when the field is absent.
    # Validate before spawning: rejects booleans, strings, NaN, Infinity, out-of-range.
    tl_raw = task.get("time_limit_s", CASE_TIMEOUT_S)
    tl_err = _check_time_limit(tl_raw)
    if tl_err:
        return {**out, "reason": tl_err}
    case_timeout_s = float(tl_raw)
    # Aggregate wall = n × per-case timeout + STARTUP_S overhead.
    task_time_s = n * case_timeout_s

    with tempfile.TemporaryDirectory(prefix="g10js-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp)
        os.chmod(work, 0o700 if sandbox == "process" else 0o777)
        (work / "solution.js").write_text(code, encoding="utf-8")
        (work / "cases.json").write_text(
            json.dumps([{"args": cases[i].get("args", [])} for i in order]),
            encoding="utf-8",
        )
        (work / "_entry").write_text(entry, encoding="utf-8")
        (work / "_case_timeout").write_text(str(case_timeout_s), encoding="utf-8")
        shutil.copyfile(RUNNER, work / "runner.js")

        start = time.monotonic()
        if callable(sandbox):
            runner = sandbox
        elif sandbox == "docker":
            runner = _run_docker
        elif sandbox == "process":
            runner = _run_process
        else:
            raise ValueError(
                f"sandbox must be 'process', 'docker', or a callable runner; got {sandbox!r}"
            )
        err = runner(work, task_time_s)
        seconds = round(time.monotonic() - start, 2)
        if err:
            return {**out, "reason": err, "seconds": seconds}
        try:
            results = json.loads(_read_result_bytes(work / "results.json").decode("utf-8"))
        except (OSError, ValueError):
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


def check_task(task_dir: Path | str, sandbox: str = "process") -> list[str]:
    """Problems with a task folder (empty list = fine). The reference solution must score 1."""
    task_dir = Path(task_dir)
    problems = []
    for f in ("task.json", "prompt.md", "visible_tests.json", "hidden_tests.json", "reference.js"):
        if not (task_dir / f).is_file():
            problems.append(f"missing {f}")
    if problems:
        return problems
    task = load_task(task_dir)
    for key in ("id", "entry_point", "time_limit_s", "difficulty", "source", "language"):
        if key not in task:
            problems.append(f"task.json lacks {key}")
    if task.get("language") != "js":
        problems.append('task.json language must be "js"')
    if task.get("id") != task_dir.name:
        problems.append("task.json id differs from the folder name")
    if not _IDENT.match(str(task.get("entry_point", ""))):
        problems.append("entry_point must be a valid JS identifier")
    if not str(task.get("source", "")).lower().startswith("original"):
        problems.append('source must start with "original" and name the author')
    if not 2 <= len(task["visible"]) <= 3:
        problems.append("need 2 or 3 visible tests")
    if len(task["hidden"]) < 10:
        problems.append("need at least 10 hidden tests")

    def key(c):
        return json.dumps(c.get("args", []), sort_keys=True)

    seen = {key(c) for c in task["visible"]}
    for c in task["hidden"]:
        if key(c) in seen:
            problems.append("a hidden test repeats a visible or earlier hidden input")
            break
        seen.add(key(c))

    prompt = (task_dir / "prompt.md").read_text(encoding="utf-8")
    entry = task.get("entry_point", "")
    for c in task["hidden"]:
        call = "{}({})".format(
            entry,
            ", ".join(json.dumps(a, ensure_ascii=False) for a in c.get("args", []))
        )
        if call in prompt:
            problems.append("a hidden test call appears in prompt.md")
            break

    for c in task["visible"] + task["hidden"]:
        if ("expected" in c) == ("raises" in c):
            problems.append('each test needs exactly one of "expected" or "raises"')
            break
        if "raises" in c and not _IDENT.match(str(c["raises"])):
            problems.append('"raises" must be a valid JS exception constructor name')
            break

    if entry not in prompt:
        problems.append("prompt.md does not mention the entry_point name")
    if "time_limit_s" in task:
        tl_err = _check_time_limit(task["time_limit_s"])
        if tl_err:
            problems.append(tl_err)
    if problems:
        return problems

    ref = (task_dir / "reference.js").read_text(encoding="utf-8")
    res = reward(task_dir, f"```javascript\n{ref}\n```", sandbox)
    if res["reward"] != 1:
        problems.append(f"reference solution does not score 1: {res.get('reason')}")
        return problems
    stub = f"function {task['entry_point']}() {{ return undefined; }}\n"
    if reward(task_dir, f"```javascript\n{stub}\n```", sandbox)["reward"] == 1:
        problems.append("a stub returning undefined scores 1: the tests are too weak")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reward", nargs=2, metavar=("TASK_DIR", "COMPLETION_FILE"))
    ap.add_argument("--check-task", metavar="TASK_DIR")
    ap.add_argument("--sandbox", choices=("process", "docker"), default="process")
    args = ap.parse_args(argv)
    if args.reward:
        task_dir, comp = args.reward
        for what, p in (("task folder", Path(task_dir) / "task.json"), ("completion file", Path(comp))):
            if not p.is_file():
                print(f"{what} not found: {p.parent if what == 'task folder' else p}", file=sys.stderr)
                return 2
        print(json.dumps(reward(task_dir, Path(comp).read_text(encoding="utf-8"), args.sandbox)))
        return 0
    if args.check_task:
        if not (Path(args.check_task) / "task.json").is_file():
            print(f"task folder not found: {args.check_task}", file=sys.stderr)
            return 2
        problems = check_task(args.check_task, args.sandbox)
        print("\n".join(problems) if problems else "task OK")
        return 1 if problems else 0
    ap.error("give --reward or --check-task")
    return 2


if __name__ == "__main__":
    sys.exit(main())
