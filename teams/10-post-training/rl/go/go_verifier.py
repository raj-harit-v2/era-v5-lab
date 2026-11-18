"""Binary reward for Go code tasks: the Go counterpart of verifier.py, with the same design.

The candidate's Go code and the cases are compiled and run in a sandbox that gets INPUTS ONLY. The generic runner
(_go_runner.go) calls the entry point on each input with reflection and writes the outputs. This process compares the
outputs with the expected values, which never enter the sandbox folder, so there is nothing to forge.

Task folder (tasks/<task_id>/ in this folder): task.json, prompt.md, visible_tests.json, hidden_tests.json, reference.go
(see README.md). A case is {"args": [...], "expected": <json>} or {"args": [...], "raises": "error"} (the function
returns a non-nil error) or "raises": "panic".

The candidate answers with one Go block that is `package main`, uses the standard library only and does not define
`main`. The entry point may return `T`, `(T, error)` or `error`.

    python go_verifier.py --reward <task_dir> <completion.txt> [--sandbox docker]
    python go_verifier.py --check-task <task_dir> [--sandbox docker]   # lint + the reference must score 1

Sandboxes:
    process  go build + run on this machine. For unit tests only: it has no network or file isolation and no memory
             limit (Go cannot run under RLIMIT_AS or RLIMIT_NPROC). Needs `go` on PATH.
    docker   --network=none, read-only root, no capabilities, 768 MB, 1 CPU, 128 pids, non-root, only the work folder
             mounted. Use this for training. Needs the image from go.Dockerfile (G10_GO_IMAGE, default g10-go-rl:1).
             If docker or the image is missing, reward() raises RuntimeError (it is never scored as a compile error).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # rl/verifier.py: shared fence reader, JSON comparison, safe result read
import verifier as pyv  # noqa: E402  (shared: fence reader, JSON comparison, safe result read)

RUNNER = HERE / "_go_runner.go"
GO_IMAGE = os.environ.get("G10_GO_IMAGE", "g10-go-rl:1")
MAX_CODE_CHARS = pyv.MAX_CODE_CHARS
CASE_TIMEOUT_S = pyv.CASE_TIMEOUT_S
BUILD_S = 30.0  # compile budget on top of the task's time limit
_GO_LABELS = {"", "go", "golang"}
_IDENT = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
GO_MOD = "module sandbox\n\ngo 1.23\n"


def extract_code(completion: str) -> tuple[str | None, str]:
    """Last fenced block labelled go (or unlabelled). Same pairing rules as verifier.extract_code."""
    blocks, opened, label, buf = [], False, "", []
    for line in (completion or "").splitlines():
        m = pyv._FENCE_LINE.match(line)
        if m and not opened:
            opened, label, buf = True, m.group(1).lower(), []
        elif m and opened and m.group(1) == "":
            if label in _GO_LABELS:
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


def _flatten_go(text: str) -> str:
    """Write a call the same way whether it is JSON-like or Go-like: braces as brackets, no type prefixes, no spaces
    next to brackets, parentheses or commas. Other spaces stay, so "1 KiB" and "1KiB" are different inputs.
    `F([]int{1, 2}, 3)` and `F([1,2],3)` both become `F([1,2],3)`."""
    text = re.sub(r"\s+", " ", text).replace("{", "[").replace("}", "]")
    text = re.sub(r" ?([,()\[\]]) ?", r"\1", text)
    return re.sub(r"(?:\[\])+[A-Za-z_][A-Za-z0-9_.]*(?=\[)", "", text)


def load_task(task_dir: Path) -> dict:
    return pyv.load_task(task_dir)


# --- running -----------------------------------------------------------------------------------

def _go_env(home: Path) -> dict:
    return {"PATH": f"{os.path.dirname(shutil.which('go') or '/usr/local/go/bin/go')}:/usr/bin:/bin", "HOME": str(home),
            "GOCACHE": os.environ.get("GOCACHE") or subprocess.run(["go", "env", "GOCACHE"], capture_output=True,
                                                                  text=True).stdout.strip(),
            "CGO_ENABLED": "0", "GOPROXY": "off", "GOFLAGS": "-mod=mod", "GOTOOLCHAIN": "local", "GOMAXPROCS": "2"}


def _file_limits():  # between fork and exec, for the candidate binary
    os.setsid()
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (10_000_000, 10_000_000))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _run_process(workdir: Path, task_time_s: float) -> str | None:
    env = _go_env(workdir)
    try:
        b = subprocess.run(["go", "build", "-o", "sol", "."], cwd=workdir, env=env, capture_output=True, timeout=BUILD_S + 60)
    except subprocess.TimeoutExpired:
        return "compile timeout"
    if b.returncode != 0 or not (workdir / "sol").exists():
        return "compile error"
    proc = subprocess.Popen([str(workdir / "sol"), str(CASE_TIMEOUT_S)], cwd=workdir, env={"PATH": "/usr/bin:/bin"},
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            preexec_fn=_file_limits)
    try:
        proc.wait(timeout=task_time_s + 3.0)
    except subprocess.TimeoutExpired:
        _kill(proc)
        return "timeout"
    _kill(proc)
    return None if proc.returncode == 0 else f"child exited with {proc.returncode}"


def _kill(proc) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


# Exit codes of the container script. Anything else from `docker run` itself (125 daemon error, 126/127 cannot start,
# a missing image) is an infrastructure failure and raises: it must never be scored as the candidate's compile error.
_RC_COMPILE, _RC_CHILD, _RC_SETUP = 3, 4, 5


def _run_docker(workdir: Path, task_time_s: float) -> str | None:
    name = f"g10go-{uuid.uuid4().hex[:12]}"
    # Candidate output goes to /dev/null: nothing it prints can fill this process's memory.
    script = ("cp -R /opt/gocache /tmp/gocache || exit %d; go build -ldflags='-s -w' -o /work/sol . >/dev/null 2>&1 || exit %d; "
              "/work/sol %s >/dev/null 2>&1 </dev/null || exit %d" % (_RC_SETUP, _RC_COMPILE, CASE_TIMEOUT_S, _RC_CHILD))
    cmd = ["docker", "run", "--rm", "--name", name, "--network=none", "--read-only", "--cap-drop", "ALL",
           "--security-opt", "no-new-privileges", "--pids-limit", "128", "--memory", "768m", "--memory-swap", "768m",
           "--cpus", "1", "--ulimit", "fsize=67108864:67108864", "--ulimit", "core=0",
           "--tmpfs", "/tmp:rw,nosuid,size=300m", "--user", "65534:65534",
           "-e", "GOCACHE=/tmp/gocache", "-e", "HOME=/tmp", "-e", "GOMAXPROCS=2",
           "-v", f"{workdir}:/work", "-w", "/work", GO_IMAGE, "sh", "-c", script]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=task_time_s + BUILD_S + 20)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return "timeout"
    rc = proc.returncode
    if rc == 0:
        return None
    if rc == _RC_COMPILE:
        return "compile error"
    if rc == _RC_CHILD:
        return "child exited with an error"
    if rc in (_RC_SETUP, 125, 126, 127):
        tail = proc.stderr.decode("utf-8", "replace")[-300:].strip()
        raise RuntimeError(f"docker sandbox failed (exit {rc}; is the image {GO_IMAGE!r} built?): {tail}")
    return f"container exited with {rc}"  # for example 137: killed (out of memory)


# --- the reward --------------------------------------------------------------------------------

def reward(task_dir: Path | str, completion: str, sandbox="process") -> dict:
    """sandbox: "process", "docker", or a runner callable(workdir, task_time_s) -> error or None."""
    task_dir = Path(task_dir)
    task = load_task(task_dir)
    out = {"task_id": task["id"], "reward": 0}
    code, why = extract_code(completion)
    if code is None:
        return {**out, "reason": why}
    entry = task["entry_point"]
    if not _IDENT.match(entry):
        return {**out, "reason": "bad entry point name in task.json"}
    cases = task["visible"] + task["hidden"]
    n = len(cases)
    order = sorted(range(n), key=lambda i: (i * 7919 + 13) % n)  # fixed shuffle: visible and hidden mixed
    task_time_s = float(task.get("time_limit_s", 5))

    with tempfile.TemporaryDirectory(prefix="g10go-", ignore_cleanup_errors=True) as tmp:
        work = Path(tmp)
        os.chmod(work, 0o700 if sandbox == "process" else 0o777)
        (work / "go.mod").write_text(GO_MOD, encoding="utf-8")
        (work / "solution.go").write_text(code, encoding="utf-8")
        (work / "entry.go").write_text(f"package main\n\nvar Entry any = {entry}\n", encoding="utf-8")
        shutil.copyfile(RUNNER, work / "runner.go")
        (work / "cases.json").write_text(json.dumps([{"args": cases[i].get("args", [])} for i in order]), encoding="utf-8")
        start = time.monotonic()
        runner = sandbox if callable(sandbox) else (_run_docker if sandbox == "docker" else _run_process)
        err = runner(work, task_time_s)
        seconds = round(time.monotonic() - start, 2)
        if err:
            return {**out, "reason": err, "seconds": seconds}
        try:
            results = json.loads(pyv.read_result_bytes(work / "results.json").decode("utf-8"))
        except (OSError, ValueError):
            return {**out, "reason": "no readable result file", "seconds": seconds}

    if not (isinstance(results, list) and len(results) == n and all(isinstance(r, dict) for r in results)):
        return {**out, "reason": "result file has the wrong shape", "seconds": seconds}
    ok_flags = [False] * n
    for pos, i in enumerate(order):
        r = results[pos]
        c = cases[i]
        if "raises" in c:  # "error" (a non-nil error returned) or "panic"
            ok_flags[i] = (not r.get("ok")) and r.get("error") == c["raises"]
        else:
            ok_flags[i] = bool(r.get("ok")) and pyv._same(r.get("value"), c["expected"])
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
    for f in ("task.json", "prompt.md", "visible_tests.json", "hidden_tests.json", "reference.go"):
        if not (task_dir / f).is_file():
            problems.append(f"missing {f}")
    if problems:
        return problems
    task = load_task(task_dir)
    for key in ("id", "entry_point", "time_limit_s", "difficulty", "source", "language"):
        if key not in task:
            problems.append(f"task.json lacks {key}")
    if task.get("language") != "go":
        problems.append('task.json language must be "go"')
    if task.get("id") != task_dir.name:
        problems.append("task.json id differs from the folder name")
    if not _IDENT.match(str(task.get("entry_point", ""))):
        problems.append("entry_point must be an exported Go name (starts with a capital letter)")
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
    flat_prompt = _flatten_go(prompt)
    for c in task["hidden"]:
        call = f"{entry}({','.join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in c.get('args', []))})"
        if _flatten_go(call) in flat_prompt:
            problems.append("a hidden test call appears in prompt.md")
            break
    for c in task["visible"] + task["hidden"]:
        if ("expected" in c) == ("raises" in c):
            problems.append('each test needs exactly one of "expected" or "raises"')
            break
        if c.get("raises") not in (None, "error", "panic"):
            problems.append('"raises" must be "error" or "panic" for Go tasks')
            break
    if entry not in prompt:
        problems.append("prompt.md does not mention the entry point name")
    if not isinstance(task.get("time_limit_s"), (int, float)) or task["time_limit_s"] <= 0:
        problems.append("time_limit_s must be a positive number")
    if problems:
        return problems
    ref = (task_dir / "reference.go").read_text(encoding="utf-8")
    res = reward(task_dir, f"```go\n{ref}\n```", sandbox)
    if res["reward"] != 1:
        problems.append(f"reference solution does not score 1: {res.get('reason')}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reward", nargs=2, metavar=("TASK_DIR", "COMPLETION_FILE"))
    ap.add_argument("--check-task", metavar="TASK_DIR")
    ap.add_argument("--sandbox", choices=("process", "docker"), default="process")
    args = ap.parse_args(argv)
    if args.reward:
        task_dir, comp = args.reward
        for what, path in (("task folder", Path(task_dir) / "task.json"), ("completion file", Path(comp))):
            if not path.is_file():
                print(f"{what} not found: {path.parent if what == 'task folder' else path}", file=sys.stderr)
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
