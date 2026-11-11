"""One reward entry point for the RL loop (TSAI, 5 Nov, PR #30 question 1):

    reward(env_id, output) -> (score, info)

"Use one wrapper reward(env_id, output) that returns a score and an info dict. Each environment registers its own
checker under its env_id, so the trainer calls one function."

env_id is "<type>/<name>":
    code/<task_id>       rl/tasks/<task_id>, scored by rl/verifier.py (output = the model's completion)
    swe/<instance_id>    swe-envs/<instance_id>, scored by swe-envs/verify.py (output = a unified diff)

New environment types call register("<type>", checker), where checker(name, output, **options) returns a dict
with at least "reward" (0 or 1). An unknown env_id raises KeyError: it never scores 0 silently, because a
default 0 looks like a real failure to the trainer.

Containers: by default each call starts its own container (verifier "docker" sandbox, verify.py `docker run`).
For training, install the warm code pool from pool.py once (SWE envs keep one fresh container per call, see
pool.py for why and for the measurement):

    from pool import CodePool
    with CodePool() as cp:
        configure(code_runner=cp.runner)
        score, info = reward("code/parse_duration", completion)

CLI:
    python rl/reward.py --list
    python rl/reward.py --check-all [--pool]   # every reference/gold scores 1, every wrong answer scores 0
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
SWE_ENVS = HERE.parent / "swe-envs"

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")  # no slashes, no "..": an env_id cannot leave its folder
_REGISTRY: dict[str, Callable[..., dict]] = {}
_OPTIONS: dict[str, object] = {"code_runner": None, "swe_executor": None}


def register(env_type: str, checker: Callable[..., dict]) -> None:
    if not _NAME.match(env_type) or "." in env_type:
        raise ValueError(f"bad env type {env_type!r}")
    _REGISTRY[env_type] = checker


def configure(code_runner=None, swe_executor=None) -> None:
    """Install a pooled code runner (pool.CodePool.runner) or a SWE executor. None: one container per call."""
    _OPTIONS["code_runner"] = code_runner
    _OPTIONS["swe_executor"] = swe_executor


def split_id(env_id: str) -> tuple[str, str]:
    env_type, sep, name = env_id.partition("/")
    if not sep or env_type not in _REGISTRY:
        raise KeyError(f"unknown env type in {env_id!r}; registered: {sorted(_REGISTRY)}")
    if not _NAME.match(name) or ".." in name:
        raise KeyError(f"bad env name in {env_id!r}")
    return env_type, name


def reward(env_id: str, output: str, **options) -> tuple[float, dict]:
    """Score one model output for one environment. Returns (score, info); info["reward"] == score."""
    env_type, name = split_id(env_id)
    info = dict(_REGISTRY[env_type](name, output, **options))
    if info.get("reward") not in (0, 1):
        raise ValueError(f"checker for {env_type!r} returned no 0/1 reward: {info}")
    info["env_id"] = env_id
    return float(info["reward"]), info


# --- built-in checkers --------------------------------------------------------------------------

_POOL_MODULE = None


def _pool():
    """pool.py, loaded by path so reward.py works from any working directory."""
    global _POOL_MODULE
    if _POOL_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_pool", HERE / "pool.py")
        _POOL_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_POOL_MODULE)
    return _POOL_MODULE


def code_checker(name: str, output: str, sandbox=None, **_) -> dict:
    task_dir = TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no code task {name!r} in {TASKS}")
    runner = sandbox or _OPTIONS["code_runner"] or "docker"
    return _pool().verifier_module().reward(task_dir, output, runner)


def swe_checker(name: str, output: str, executor=None, **_) -> dict:
    env_dir = SWE_ENVS / name
    if not (env_dir / "env.json").is_file():
        raise KeyError(f"no SWE env {name!r} in {SWE_ENVS}")
    return _pool().swe_verify_module().reward(env_dir, output, executor or _OPTIONS["swe_executor"])


register("code", code_checker)
register("swe", swe_checker)


def list_envs() -> list[str]:
    ids = [f"code/{p.parent.name}" for p in sorted(TASKS.glob("*/task.json"))]
    ids += [f"swe/{p.parent.name}" for p in sorted(SWE_ENVS.glob("*/env.json"))]
    return ids


# --- known-good and known-bad outputs (for --check-all and the pool benchmark) --------------------

NOOP_PATCH = ("diff --git a/g10_noop.txt b/g10_noop.txt\nnew file mode 100644\nindex 0000000..e69de29\n"
              "--- /dev/null\n+++ b/g10_noop.txt\n@@ -0,0 +1 @@\n+noop\n")


def known_outputs(env_id: str) -> tuple[str, str]:
    """(an output that must score 1, an output that must score 0) for a shipped environment."""
    env_type, name = split_id(env_id)
    if env_type == "code":
        meta = json.loads((TASKS / name / "task.json").read_text(encoding="utf-8"))
        good = "```python\n" + (TASKS / name / "reference.py").read_text(encoding="utf-8") + "\n```"
        bad = f"```python\ndef {meta['entry_point']}(*args, **kwargs):\n    return None\n```"
        return good, bad
    if env_type == "swe":
        return (SWE_ENVS / name / "gold.patch").read_text(encoding="utf-8"), NOOP_PATCH
    raise KeyError(f"no known outputs for {env_type!r}")


def check_all(workers: int = 4, ids: list[str] | None = None) -> list[dict]:
    jobs = [(i, kind, out) for i in (ids or list_envs()) for kind, out in zip(("good", "bad"), known_outputs(i))]

    def one(job):
        env_id, kind, out = job
        t0 = time.monotonic()
        score, info = reward(env_id, out)
        want = 1.0 if kind == "good" else 0.0
        return {"env_id": env_id, "kind": kind, "score": score, "ok": score == want,
                "reason": str(info.get("reason", ""))[:120], "seconds": round(time.monotonic() - t0, 2)}

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, jobs))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check-all", action="store_true")
    ap.add_argument("--pool", action="store_true", help="use the warm code pool from pool.py")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    if args.list:
        print("\n".join(list_envs()))
        return 0
    if args.check_all:
        if args.pool:
            pool = _pool()
            with pool.CodePool(workers=args.workers) as cp:
                configure(code_runner=cp.runner)
                rows = check_all(args.workers)
            configure()
        else:
            rows = check_all(args.workers)
        for r in rows:
            print(json.dumps(r))
        bad = [r for r in rows if not r["ok"]]
        print(json.dumps({"checked": len(rows), "wrong": len(bad)}))
        return 1 if bad else 0
    ap.error("give --list or --check-all")
    return 2


if __name__ == "__main__":
    sys.exit(main())
