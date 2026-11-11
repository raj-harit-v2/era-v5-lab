"""Warm container pools for the RL rewards (TSAI, 5 Nov: "a warm container pool with parallel workers, one worker
per CPU core, and reuse each container for a batch of rollouts. Measure rollouts per second with the pool").

CodePool  (code tasks, rl/verifier.py)
    One long-lived container per worker, reused for a batch of rollouts (`docker exec`). Safe to reuse because the
    container is read-only except a tmpfs /tmp and its own work folder, runs as nobody (65534) with no network and no
    capabilities, and after every rollout the pool kills every process left behind and empties /tmp and the work
    folder. Each container is recycled after `max_uses` rollouts, after a timeout or after any cleanup error.
    The expected answers still never enter the container: verifier.reward() compares the results in this process.

SWE environments are NOT pooled. A SWE rollout runs the candidate's code with a writable repository (the tests write
into it), so a reused container could carry a planted change into the next rollout. Pre-started single-use
containers were tried and measured slower than plain parallel `docker run --rm` on Docker Desktop (1.59 vs 2.21
rollouts/s, results/reward_pool_bench.md), so SWE rollouts use verify.py's fresh container per call, run in
parallel by the trainer's workers. swe-envs/verify.py takes an `executor` argument, so a safe reusable design (for
example a read-only image with the repository copied to a tmpfs per rollout) can plug in later.

Use:
    with CodePool(workers=8) as cp:
        reward.configure(code_runner=cp.runner)
        ... reward.reward("code/parse_duration", completion) ... reward.reward("swe/pallets__click-1934", patch)
"""
from __future__ import annotations

import importlib.util
import os
import queue
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE_IMAGE = os.environ.get("G10_RL_IMAGE", "python:3.12-slim")


_LOADED: dict[str, object] = {}


def _load(name: str, path: str):
    """Load a sibling module by path once (a plain dict cache)."""
    if name not in _LOADED:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _LOADED[name] = mod
    return _LOADED[name]


def verifier_module():
    return _load("g10_rl_verifier", str(HERE / "verifier.py"))


def swe_verify_module():
    return _load("g10_swe_verify", str(HERE.parent / "swe-envs" / "verify.py"))

# Same limits as verifier._run_docker, plus a long-lived idle process as PID 1.
CODE_FLAGS = ["--network=none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
              "--pids-limit", "32", "--memory", "512m", "--memory-swap", "512m", "--cpus", "1",
              "--ulimit", "fsize=10000000:10000000", "--ulimit", "core=0",
              "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--user", "65534:65534", "-e", "PYTHONHASHSEED=0"]

# PID 1 of every code container: idles and reaps orphans. Without a reaper, processes the candidate started stay
# behind as zombies after cleanup (seen in test_a_reused_container_carries_nothing_into_the_next_rollout).
# As PID 1 it is never hit by kill(-1).
REAPER = ("import os, time\n"
          "while True:\n"
          "    try:\n        os.waitpid(-1, 0)\n"
          "    except ChildProcessError:\n        time.sleep(0.2)\n")

# Runs after every code rollout, as the container's user: empty /tmp, SIGKILL every process except PID 1 and itself
# (kill(-1) skips both), then wait until the reaper has collected them. Prints "clean" only if nothing is left.
CLEANUP = ("import os, shutil, signal, time\n"
           "for n in os.listdir('/tmp'):\n"
           "    p = os.path.join('/tmp', n)\n"
           "    shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)\n"
           "try:\n    os.kill(-1, signal.SIGKILL)\nexcept ProcessLookupError:\n    pass\n"
           "me = os.getpid()\n"
           "for _ in range(50):\n"
           "    left = [p for p in os.listdir('/proc') if p.isdigit() and int(p) not in (1, me)]\n"
           "    if not left and not os.listdir('/tmp'):\n        print('clean')\n        break\n"
           "    time.sleep(0.05)\n"
           "else:\n    print('dirty', left)\n")


def _docker(*args: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


class _CodeWorker:
    def __init__(self, image: str, max_uses: int):
        self.image, self.max_uses = image, max_uses
        self.dir = Path(tempfile.mkdtemp(prefix="g10pool-"))
        os.chmod(self.dir, 0o777)
        self.name: str | None = None
        self.uses = 0
        self.start()

    def start(self) -> None:
        self.stop()
        self.name = f"g10pool-{uuid.uuid4().hex[:12]}"
        r = _docker("run", "-d", "--name", self.name, *CODE_FLAGS, "-v", f"{self.dir}:/pool", "-w", "/pool",
                    self.image, "python", "-B", "-c", REAPER)
        if r.returncode != 0:
            raise RuntimeError(f"could not start pool container: {r.stderr.strip()}")
        self.uses = 0

    def stop(self) -> None:
        if self.name:
            _docker("rm", "-f", self.name)
            self.name = None

    def _clear_dir(self) -> None:
        for p in self.dir.iterdir():
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() and not p.is_symlink() else p.unlink(missing_ok=True)

    @staticmethod
    def _fetch_results(slot: Path, workdir: Path) -> str | None:
        """Copy results.json out of the slot. The candidate can replace the slot folder or the file with a symlink, so
        both are opened without following one, and the file must be a regular file of bounded size."""
        try:
            dfd = os.open(slot, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
            try:
                data = verifier_module().read_result_bytes("results.json", dfd)
            finally:
                os.close(dfd)
        except (OSError, ValueError):
            return "result file is not a regular file or is too large"
        (workdir / "results.json").write_bytes(data)
        return None

    def run(self, workdir: Path, entry: str, wall_s: float) -> str | None:
        """Same contract as verifier._run_docker: run _child.py on workdir; error string or None."""
        rid = uuid.uuid4().hex[:12]
        slot = self.dir / rid
        shutil.copytree(workdir, slot)
        os.chmod(slot, 0o777)
        err = None
        try:
            r = _docker("exec", self.name, "python", "-B", "-s", f"/pool/{rid}/_child.py", f"/pool/{rid}", entry,
                        str(verifier_module().CASE_TIMEOUT_S), timeout=wall_s + 5)
            if r.returncode != 0:
                err = f"container exited with {r.returncode}"
            elif (slot / "results.json").exists():
                err = self._fetch_results(slot, workdir)
        except subprocess.TimeoutExpired:
            err = "timeout"
        finally:
            self.uses += 1
            clean_ok = False
            try:
                c = _docker("exec", self.name, "python", "-B", "-c", CLEANUP, timeout=20)
                clean_ok = c.returncode == 0 and "clean" in c.stdout
            except subprocess.TimeoutExpired:
                pass
            self._clear_dir()
            if err == "timeout" or not clean_ok or self.uses >= self.max_uses:
                self.start()  # recycle: never trust a container after a timeout or a failed cleanup
        return err

    def close(self) -> None:
        self.stop()
        shutil.rmtree(self.dir, ignore_errors=True)


class CodePool:
    """Pool of reused containers for rl/verifier.py. `runner` is passed as verifier.reward(..., sandbox=runner)."""

    def __init__(self, workers: int | None = None, image: str = CODE_IMAGE, max_uses: int = 200):
        self.workers = workers or os.cpu_count() or 1
        self._free: queue.Queue[_CodeWorker] = queue.Queue()
        self._all = [_CodeWorker(image, max_uses) for _ in range(self.workers)]
        for w in self._all:
            self._free.put(w)

    def runner(self, workdir: Path, entry: str, wall_s: float) -> str | None:
        w = self._free.get()
        try:
            return w.run(Path(workdir), entry, wall_s)
        finally:
            self._free.put(w)

    def close(self) -> None:
        for w in self._all:
            w.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
