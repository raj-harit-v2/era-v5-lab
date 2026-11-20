"""Reward for stdin/stdout programming tasks (Codeforces-style), with the same rule as rl/verifier.py:
the expected outputs never enter the sandbox.

A task is a dict: {"id", "statement", "tests": [{"input": str, "output": str}, ...], "time_limit_s", "source",
"licence", "generator"}. The sandbox gets the program and the INPUTS only, runs the program once per input, and
returns what it printed. This process compares the outputs (whitespace-separated tokens, like most judges), so a
program cannot write a fake "all passed" result: it never sees what the right answers are.

    score(task, completion) -> {"reward": 0|1, "passed": n, "total": m, "reason": str}

Code is taken from the completion with rl/verifier.py's extract_code (last python block). The sandbox is a fresh
`python:3.12-slim` container per call with the same limits as the verifier's docker sandbox.
"""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = os.environ.get("G10_RL_IMAGE", "python:3.12-slim")
MAX_TESTS = 20            # per task, for speed; the first ones are the public examples
MAX_OUTPUT_CHARS = 65536  # per test
OUTPUTS_MAX_BYTES = 10_000_000  # = the fsize ulimit: a real outputs.json can never be larger

_spec = importlib.util.spec_from_file_location("g10_rl_verifier_for_stdio", HERE.parent / "rl" / "verifier.py")
_verifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_verifier)
extract_code = _verifier.extract_code

# Runs inside the container: reads inputs.json, runs solution.py on each input, writes outputs.json.
RUNNER = r'''
import json, subprocess, sys
work = sys.argv[2] if len(sys.argv) > 2 else "/work"
inputs = json.load(open(work + "/inputs.json"))
limit = float(sys.argv[1])
out = []
for text in inputs:
    try:
        p = subprocess.run([sys.executable, "-B", "-s", work + "/solution.py"], input=text, capture_output=True,
                           text=True, timeout=limit, cwd=work)
        out.append({"status": "ok" if p.returncode == 0 else "error", "stdout": p.stdout[:%d]})
    except subprocess.TimeoutExpired:
        out.append({"status": "timeout", "stdout": ""})
    if out[-1]["status"] != "ok":
        break  # the reward needs every test; stop at the first failure
json.dump(out, open(work + "/outputs.json", "w"))
''' % MAX_OUTPUT_CHARS

DOCKER_FLAGS = ["--network=none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", "32", "--memory", "512m", "--memory-swap", "512m", "--cpus", "1",
                "--ulimit", "fsize=10000000:10000000", "--ulimit", "core=0",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--user", "65534:65534", "-e", "PYTHONHASHSEED=0"]


# Where programs run (G10_STDIO_RUNNER):
#   docker  (default) a fresh python:3.12-slim container per call with DOCKER_FLAGS: the laptop and the job runner.
#   local   no Docker (inside a Modal container). Linux only and the scorer must be root: every execution runs under
#           its own unprivileged uid/gid (no supplementary groups, no_new_privs, umask 077) in a 0700 folder that
#           uid owns, below a root-owned 0711 base, with memory/file/core/process limits and per-test timeouts.
#           This trusted process feeds each input and reads stdout through pipes, so no output file exists for the
#           program to forge; after each program (and after any timeout) every process of that uid is killed. The expected outputs stay in
#           this process and in files the caller keeps root-only (0600 under 0700 folders): the program cannot
#           read them, other runs' folders, or this process's memory. Anything else refuses to run (fail closed).
#           uid isolation protects only files whose mode excludes "other", so the caller must name every file or
#           folder holding expected outputs in G10_STDIO_SECRET_PATHS (os.pathsep-separated) and make them unreachable
#           for other uids (0600 under 0700 folders, or chmod 0700 /kaggle where the task file is a read-only mount);
#           preflight_isolation() proves it with a probe as a sandbox uid and refuses to score otherwise; a named path
#           must exist, and a named folder must not be enterable by other uids. The same
#           preflight probes the network: sandboxed programs get a seccomp filter that allows AF_UNIX sockets only, and
#           scoring refuses if a sandbox uid can still open an IP connection (Modal: block_network=True also holds).
#   local_unisolated  the old plain-subprocess runner, kept only for tests on trusted programs; never for rewards.
RUNNER_KIND = os.environ.get("G10_STDIO_RUNNER", "docker")
SANDBOX_UID_BASE, SANDBOX_UID_SPAN = 61000, 4000
SANDBOX_BASE = Path(os.environ.get("G10_SANDBOX_BASE", "/tmp/g10sbx"))
SANDBOX_NPROC = 64
LOCAL_MEMORY_BYTES = 1 << 30   # per process (Python itself needs ~30 MB; the runner and the solution each get this)
LOCAL_FILE_BYTES = 10_000_000
# Local runner only: stop a program at its first wrong answer, as it already stops at its first error or timeout.
# The comparison happens in this trusted process, which holds the expected outputs anyway, so nothing new enters
# the sandbox. The reward needs every test, so reward, passed, total and reason are unchanged; only the tests after
# the first failure are not run. G10_STDIO_EARLY_EXIT=0 restores the old behaviour (matched timing runs).
EARLY_EXIT = os.environ.get("G10_STDIO_EARLY_EXIT", "1") != "0"


def _local_limits():  # runs in the child before exec (Linux)
    import resource  # noqa: PLC0415
    resource.setrlimit(resource.RLIMIT_AS, (LOCAL_MEMORY_BYTES, LOCAL_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (LOCAL_FILE_BYTES, LOCAL_FILE_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _run_local(w: Path, time_limit_s: float, n_inputs: int):
    cmd = [sys.executable, "-B", "-s", str(w / "run.py"), str(time_limit_s), str(w)]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONHASHSEED": "0", "HOME": str(w)}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=w, env=env,
                            preexec_fn=_local_limits if sys.platform.startswith("linux") else None,
                            start_new_session=True)
    try:
        proc.communicate(timeout=time_limit_s * n_inputs + 30)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None
    return proc.returncode


_uid_lock = __import__("threading").Lock()
_uid_next = [0]


def _next_uid() -> int:
    with _uid_lock:
        _uid_next[0] = (_uid_next[0] + 1) % SANDBOX_UID_SPAN
        return SANDBOX_UID_BASE + _uid_next[0]


def set_uid_range(start: int, span: int) -> None:
    """Give this process its own slice of the sandbox uid range. Several scorer processes on one machine must not
    hand out the same uid at the same time: a uid's cleanup kills every process of that uid."""
    global SANDBOX_UID_BASE, SANDBOX_UID_SPAN
    if start < 61000 or span < 1 or start + span > 65000:
        raise ValueError(f"sandbox uid range {start}+{span} is outside 61000..65000")
    with _uid_lock:
        SANDBOX_UID_BASE, SANDBOX_UID_SPAN = start, span
        _uid_next[0] = 0


def isolation_available() -> tuple[bool, str]:
    if not sys.platform.startswith("linux"):
        return False, "isolated local runner needs Linux"
    if os.geteuid() != 0:
        return False, "isolated local runner needs root to switch to a sandbox uid"
    return True, "ok"


# seccomp: a sandboxed program may open AF_UNIX sockets only. A public answer source (the code-contest test sets)
# would otherwise be one HTTP request away on a machine with internet on (Kaggle).
_AUDIT_ARCH = {"x86_64": (0xC000003E, 41, True), "aarch64": (0xC00000B7, 198, False)}  # (AUDIT_ARCH, socket nr, x32)
_NR_IO_URING_SETUP = 425  # io_uring can open sockets without calling socket(); same number on both arches
_SECCOMP_ALLOW, _SECCOMP_EPERM, _SECCOMP_KILL = 0x7FFF0000, 0x00050001, 0x80000000


@lru_cache(maxsize=None)
def _socket_filter() -> bytes | None:
    """BPF program: socket() only for AF_UNIX; io_uring_setup and x32 syscalls denied (EPERM); another arch killed.
    None on an architecture this code does not know; the preflight's network probe then decides."""
    import platform  # noqa: PLC0415
    import struct  # noqa: PLC0415
    spec = _AUDIT_ARCH.get(platform.machine())
    if spec is None:
        return None
    arch, nr_socket, x32 = spec
    LD, JEQ, JGE, RET = 0x20, 0x15, 0x35, 0x06  # BPF_LD|W|ABS, BPF_JMP|JEQ|K, BPF_JMP|JGE|K, BPF_RET|K
    # (label, code, true-label, false-label, k); a missing label means "the next instruction"
    prog = [("start", LD, None, None, 4),  # seccomp_data.arch
            (None, JEQ, None, "kill", arch),
            (None, LD, None, None, 0)]  # seccomp_data.nr
    if x32:
        prog.append((None, JGE, "deny", None, 0x40000000))
    prog += [(None, JEQ, "af", None, nr_socket),
             (None, JEQ, "deny", None, _NR_IO_URING_SETUP),
             (None, RET, None, None, _SECCOMP_ALLOW),
             ("af", LD, None, None, 16),  # seccomp_data.args[0], the domain (low word, little-endian)
             (None, JEQ, "allow", "deny", 1),  # AF_UNIX
             ("allow", RET, None, None, _SECCOMP_ALLOW),
             ("deny", RET, None, None, _SECCOMP_EPERM),
             ("kill", RET, None, None, _SECCOMP_KILL)]
    pos = {name: i for i, (name, *_rest) in enumerate(prog) if name}
    return b"".join(struct.pack("HBBI", code, 0 if jt is None else pos[jt] - i - 1,
                                0 if jf is None else pos[jf] - i - 1, k)
                    for i, (_name, code, jt, jf, k) in enumerate(prog))


@lru_cache(maxsize=None)
def _seccomp_fprog():
    """(sock_fprog, buffer) for prctl(PR_SET_SECCOMP), built once in the parent so the fork child only calls prctl."""
    import ctypes  # noqa: PLC0415
    prog = _socket_filter()
    if prog is None:
        return None

    class Fprog(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.c_void_p)]
    buf = ctypes.create_string_buffer(prog, len(prog))
    return Fprog(len(prog) // 8, ctypes.addressof(buf)), buf


def _sandbox_preexec():  # in the child, after the uid/gid switch done by subprocess (user=, group=, extra_groups=[])
    import ctypes  # noqa: PLC0415
    import resource  # noqa: PLC0415
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        os._exit(97)
    fp = _seccomp_fprog()
    if fp is not None:
        # if the kernel refuses the filter the program still runs: the preflight's network probe has already
        # established, with this same preexec, whether a sandbox uid can reach the network
        libc.prctl(22, 2, ctypes.byref(fp[0]), 0, 0)  # PR_SET_SECCOMP, SECCOMP_MODE_FILTER
    resource.setrlimit(resource.RLIMIT_AS, (LOCAL_MEMORY_BYTES, LOCAL_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (LOCAL_FILE_BYTES, LOCAL_FILE_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NPROC, (SANDBOX_NPROC, SANDBOX_NPROC))


def _kill_uid(uid: int) -> None:
    """Kill every process of the sandbox uid (kill(-1) as that uid reaches exactly its own processes)."""
    subprocess.run([sys.executable, "-S", "-c", "import os, signal; os.kill(-1, signal.SIGKILL)"], user=uid,
                   group=uid, extra_groups=[], capture_output=True, timeout=10, env={})


_PREFLIGHT_OK = []


def preflight_isolation() -> None:
    """Fail closed unless a sandbox uid provably cannot read any file named in G10_STDIO_SECRET_PATHS (every file or
    folder that holds expected outputs, os.pathsep-separated). uid isolation protects only files whose mode excludes
    "other"; a world-readable task file (a read-only Kaggle input, a default-umask copy) is readable by the program."""
    if _PREFLIGHT_OK:
        return
    paths = [p for p in os.environ.get("G10_STDIO_SECRET_PATHS", "").split(os.pathsep) if p]
    if not paths:
        raise RuntimeError("G10_STDIO_RUNNER=local refused: set G10_STDIO_SECRET_PATHS to every file holding expected outputs")
    for p in paths:  # a typo must not read as "unreadable": exists() follows symlinks, so a dangling link refuses too
        if not os.path.exists(p):
            raise RuntimeError(f"G10_STDIO_RUNNER=local refused: G10_STDIO_SECRET_PATHS names a path that does not exist: {p}")
    _seccomp_fprog()  # build once in the parent: the forked sandbox start-up then only installs it
    uid = _next_uid()
    # a file must not be readable; a folder must be neither listable nor enterable (a 0711 folder hides its names but
    # a file with a known name inside it can still be opened)
    probe = ("import os,sys\nfor p in sys.argv[1:]:\n    try:\n        if os.path.isdir(p):\n            os.listdir(p); print(p); break\n"
             "        open(p,'rb').read(1); print(p); break\n    except OSError: pass\n"
             "    if os.path.isdir(p):\n        try:\n            os.chdir(p); print(p); break\n        except OSError: pass\n")
    r = subprocess.run([sys.executable, "-S", "-c", probe, *paths], user=uid, group=uid, extra_groups=[],
                       capture_output=True, text=True, timeout=30, env={}, cwd="/")
    if r.stdout.strip():
        raise RuntimeError(f"G10_STDIO_RUNNER=local refused: a sandbox uid can read {r.stdout.strip()}")
    # network: the same sandbox start-up (seccomp included) must not let a program open an IP connection
    net = ("import socket\ntry:\n    socket.create_connection(('1.1.1.1', 53), timeout=2).close(); print('REACHED')\n"
           "except OSError as e:\n    print('BLOCKED', type(e).__name__)\n")
    n = subprocess.run([sys.executable, "-S", "-c", net], user=uid, group=uid, extra_groups=[], capture_output=True,
                       text=True, timeout=30, env={}, cwd="/", preexec_fn=_sandbox_preexec)
    if not n.stdout.startswith("BLOCKED"):  # REACHED, or the probe did not run: fail closed
        raise RuntimeError("G10_STDIO_RUNNER=local refused: a sandbox uid can open a network connection "
                           f"(probe said {n.stdout.strip() or n.stderr.strip()[-80:]!r}); run with internet off or "
                           "on a kernel that accepts a seccomp filter")
    _PREFLIGHT_OK.append(True)


def run_isolated(code: str, inputs: list[str], time_limit_s: float,
                 expected: list[str] | None = None) -> list[dict] | str:
    ok, why = isolation_available()
    if not ok:
        raise RuntimeError(f"G10_STDIO_RUNNER=local refused: {why}; use docker")
    preflight_isolation()
    SANDBOX_BASE.mkdir(mode=0o711, exist_ok=True)
    st = SANDBOX_BASE.stat()
    if st.st_uid != 0 or (st.st_mode & 0o777) != 0o711:
        os.chown(SANDBOX_BASE, 0, 0)
        os.chmod(SANDBOX_BASE, 0o711)
    uid = _next_uid()
    w = SANDBOX_BASE / f"r{uid}-{uuid.uuid4().hex[:12]}"
    w.mkdir(mode=0o700)
    try:
        (w / "solution.py").write_text(code, encoding="utf-8")
        os.chown(w / "solution.py", uid, uid)
        os.chmod(w / "solution.py", 0o400)
        os.chown(w, uid, uid)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONHASHSEED": "0", "HOME": str(w), "TMPDIR": str(w),
               "LANG": "C.UTF-8"}
        out = []
        for i, text in enumerate(inputs):
            try:
                p = subprocess.run([sys.executable, "-B", "-s", str(w / "solution.py")], input=text,
                                   capture_output=True, text=True, timeout=time_limit_s, cwd=w, env=env, user=uid,
                                   group=uid, extra_groups=[], umask=0o077, preexec_fn=_sandbox_preexec,
                                   start_new_session=True, close_fds=True)
                out.append({"status": "ok" if p.returncode == 0 else "error", "stdout": p.stdout[:MAX_OUTPUT_CHARS]})
            except subprocess.TimeoutExpired:
                out.append({"status": "timeout", "stdout": ""})
                _kill_uid(uid)  # a timed-out program may still run; the normal sweep is once per program below
            if out[-1]["status"] != "ok":
                break  # the reward needs every test; stop at the first failure
            if expected is not None and not same_output(out[-1]["stdout"], expected[i]):
                break  # first wrong answer: score() stops counting here too
        return out
    finally:
        _kill_uid(uid)
        import shutil  # noqa: PLC0415
        shutil.rmtree(w, ignore_errors=True)


def same_output(actual: str, expected: str) -> bool:
    """Judge-style comparison: the same whitespace-separated tokens."""
    return actual.split() == expected.split()


def run_program(code: str, inputs: list[str], time_limit_s: float,
                expected: list[str] | None = None) -> list[dict] | str:
    """Run code on each input in a fresh container. Returns per-input results, or an error string.
    `expected` is used by the local runner only (early exit in the trusted process); it never reaches Docker."""
    if RUNNER_KIND == "local":
        return run_isolated(code, inputs, time_limit_s, expected if EARLY_EXIT else None)
    if RUNNER_KIND not in ("docker", "local_unisolated"):
        raise RuntimeError(f"unknown G10_STDIO_RUNNER {RUNNER_KIND!r}")
    with tempfile.TemporaryDirectory(prefix="g10stdio-", ignore_cleanup_errors=True) as tmp:
        w = Path(tmp)
        os.chmod(w, 0o777)
        (w / "solution.py").write_text(code, encoding="utf-8")
        (w / "inputs.json").write_text(json.dumps(inputs), encoding="utf-8")
        (w / "run.py").write_text(RUNNER, encoding="utf-8")
        if RUNNER_KIND == "local_unisolated":
            rc = _run_local(w, time_limit_s, len(inputs))
            if rc is None:
                return "timeout"
            if rc != 0:
                return f"runner exited with {rc}"
            try:
                results = json.loads(_verifier.read_result_bytes(w / "outputs.json", limit=OUTPUTS_MAX_BYTES).decode("utf-8"))
            except (OSError, ValueError):
                return "no readable output file"
            if not isinstance(results, list) or not all(isinstance(r, dict) for r in results):
                return "output file has the wrong shape"
            return results
        name = f"g10stdio-{uuid.uuid4().hex[:12]}"
        cmd = ["docker", "run", "--rm", "--name", name, *DOCKER_FLAGS, "-v", f"{w}:/work", "-w", "/work", IMAGE,
               "python", "-B", "-s", "/work/run.py", str(time_limit_s)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=time_limit_s * len(inputs) + 30)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            return "timeout"
        if proc.returncode != 0:
            return f"runner exited with {proc.returncode}"
        try:
            results = json.loads(_verifier.read_result_bytes(w / "outputs.json", limit=OUTPUTS_MAX_BYTES).decode("utf-8"))
        except (OSError, ValueError):
            return "no readable output file"
    if not isinstance(results, list) or not all(isinstance(r, dict) for r in results):
        return "output file has the wrong shape"
    return results


def score(task: dict, completion: str) -> dict:
    code, why = extract_code(completion)
    out = {"task_id": task["id"], "reward": 0}
    if code is None:
        return {**out, "reason": why}
    tests = task["tests"][:MAX_TESTS]
    results = run_program(code, [t["input"] for t in tests], float(task.get("time_limit_s", 4)),
                          [t["output"] for t in tests])
    if isinstance(results, str):
        return {**out, "reason": results}
    passed = 0
    for r, t in zip(results, tests):
        if r.get("status") != "ok" or not same_output(str(r.get("stdout", "")), t["output"]):
            break
        passed += 1
    reward = int(passed == len(tests))
    if reward:
        reason = "all tests passed"
    elif passed < len(results) and results[passed].get("status") != "ok":
        reason = f"{results[passed].get('status')} on a test"  # error or timeout; which test is not reported
    else:
        reason = "wrong answer on a test"
    return {**out, "reward": reward, "passed": passed, "total": len(tests), "reason": reason}
