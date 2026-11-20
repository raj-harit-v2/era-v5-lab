"""One reward entry point for the RL loop (TSAI, 5 Nov, PR #30 question 1):

    reward(env_id, output) -> (score, info)

"Use one wrapper reward(env_id, output) that returns a score and an info dict. Each environment registers its own
checker under its env_id, so the trainer calls one function."

env_id is "<type>/<name>":
    code/<task_id>       rl/tasks/<task_id>, scored by rl/verifier.py (output = the model's completion)
    swe/<instance_id>    swe-envs/<instance_id>, scored by swe-envs/verify.py (output = a unified diff)
    indic/<task_id>      rl/indic/tasks/<task_id>, scored by rl/indic/indic_verifier.py (exact answer, no container)
    go/<task_id>         rl/go/tasks/<task_id>, scored by rl/go/go_verifier.py (output = the model's completion;
                         docker sandbox by default, the image is built from rl/go/go.Dockerfile)
    js/<task_id>         rl/jsts/tasks/js/<task_id>, scored by rl/jsts/jsts_verifier.py (output = one JavaScript module,
                         docker sandbox, image g10-jsts-rl:1 built from rl/jsts/jsts.Dockerfile)
    ts/<task_id>         rl/jsts/tasks/ts/<task_id>, the same for TypeScript
    math_pool/<task_id>  rl/math_pool/tasks/<task_id>, scored by rl/math_pool/math_verifier.py (exact boxed answer, no container;
                         needs the RL data v1 math pool: set G10_MATH_POOL, see rl/math_pool/README.md)
    agentic/<task_id>    rl/agentic/tasks/<task_id>, scored by rl/agentic/agentic_verifier.py (output = one pytest
                         command or one diff, run in the image of a swe-envs environment; needs docker)
    tool_call/<task_id>  rl/tasks/tool_call/<task_id>, exact name/arguments JSON comparison, no execution
    toolresult/<task_id> rl/toolresult/tasks/<task_id>, scored by rl/toolresult/toolresult_verifier.py (exact
                         tool-result text in the reply, no execution)

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
    python rl/reward.py --check-all --type indic   # only one environment type (indic needs no docker)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
SWE_ENVS = HERE.parent / "swe-envs"
INDIC_TASKS = HERE / "indic" / "tasks"
MATH_TASKS = HERE / "math" / "tasks"
GO_TASKS = HERE / "go" / "tasks"
AGENTIC_TASKS = HERE / "agentic" / "tasks"
MATH_POOL_TASKS = HERE / "math_pool" / "tasks"
JS_TASKS = HERE / "jsts" / "tasks" / "js"
TS_TASKS = HERE / "jsts" / "tasks" / "ts"
JS_RL_TASKS = HERE / "js" / "tasks"  # AjaySnl set (rl/js); shares the env type "js" with the Exercism set
TOOL_CALL_TASKS = TASKS / "tool_call"
TOOLRESULT_TASKS = HERE / "toolresult" / "tasks"

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
_POOL_LOCK = threading.Lock()


def _pool():
    """pool.py, loaded by path so reward.py works from any working directory.

    Thread-safe: the module is published only after it has run, so a second thread (check_all, a trainer's scorer
    threads) never sees a half-loaded module."""
    global _POOL_MODULE
    if _POOL_MODULE is None:
        with _POOL_LOCK:
            if _POOL_MODULE is None:
                import importlib.util  # noqa: PLC0415
                spec = importlib.util.spec_from_file_location("g10_rl_pool", HERE / "pool.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                _POOL_MODULE = module
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


_INDIC_MODULE = None


def _indic():
    """indic/indic_verifier.py, loaded by path like pool.py."""
    global _INDIC_MODULE
    if _INDIC_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_indic_verifier", HERE / "indic" / "indic_verifier.py")
        _INDIC_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_INDIC_MODULE)
    return _INDIC_MODULE


def indic_checker(name: str, output: str, **_) -> dict:
    task_dir = INDIC_TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no indic task {name!r} in {INDIC_TASKS}")
    return _indic().reward(task_dir, output)



_MATH_MODULE = None


def _math():
    """math/math_verifier.py, loaded by path like indic_verifier.py."""
    global _MATH_MODULE
    if _MATH_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location(
            "g10_rl_math_verifier", HERE / "math" / "math_verifier.py"
        )
        _MATH_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_MATH_MODULE)
    return _MATH_MODULE


def math_checker(name: str, output: str, **_) -> dict:
    task_dir = MATH_TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no math task {name!r} in {MATH_TASKS}")
    return _math().reward(task_dir, output)

_GO_MODULE = None


def _go():
    """go/go_verifier.py, loaded by path like pool.py. It imports the shared verifier.py from this folder."""
    global _GO_MODULE
    if _GO_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_go_verifier", HERE / "go" / "go_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _GO_MODULE = module
    return _GO_MODULE


def go_checker(name: str, output: str, sandbox="docker", **_) -> dict:
    """The default is the docker sandbox: the "process" sandbox is for unit tests only (go/README.md). A missing
    docker or image raises RuntimeError, it is never scored as 0."""
    task_dir = GO_TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no go task {name!r} in {GO_TASKS}")
    return _go().reward(task_dir, output, sandbox)


_AGENTIC_MODULE = None


def _agentic():
    """agentic/agentic_verifier.py, loaded by path like pool.py."""
    global _AGENTIC_MODULE
    if _AGENTIC_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_agentic_verifier", HERE / "agentic" / "agentic_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _AGENTIC_MODULE = module
    return _AGENTIC_MODULE


def agentic_checker(name: str, output: str, executor=None, **_) -> dict:
    task_dir = AGENTIC_TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no agentic task {name!r} in {AGENTIC_TASKS}")
    return _agentic().reward(task_dir, output, executor or _OPTIONS["swe_executor"])


_MATH_POOL_MODULE = None


def _math_pool():
    """math_pool/math_verifier.py, loaded by path like pool.py."""
    global _MATH_POOL_MODULE
    if _MATH_POOL_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_math_pool_verifier", HERE / "math_pool" / "math_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MATH_POOL_MODULE = module
    return _MATH_POOL_MODULE


def math_pool_checker(name: str, output: str, pool=None, **_) -> dict:
    """A missing pool raises RuntimeError (math_verifier.py): it is never scored 0."""
    task_dir = MATH_POOL_TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no math_pool task {name!r} in {MATH_POOL_TASKS}")
    return _math_pool().reward(task_dir, output, pool)


_JSTS_MODULE = None


def _jsts():
    """jsts/jsts_verifier.py, loaded by path like pool.py."""
    global _JSTS_MODULE
    if _JSTS_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_jsts_verifier", HERE / "jsts" / "jsts_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _JSTS_MODULE = module
    return _JSTS_MODULE


def _jsts_checker(folder: Path, kind: str):
    def checker(name: str, output: str, executor=None, **_) -> dict:
        """Needs docker and the g10-jsts-rl:1 image; a failure to run raises, it is never scored 0 as a model error."""
        task_dir = folder / name
        if not (task_dir / "task.json").is_file():
            raise KeyError(f"no {kind} task {name!r} in {folder}")
        return _jsts().reward(task_dir, output, executor)
    return checker


_JS_MODULE = None


def _js():
    """js/js_verifier.py, loaded by path like pool.py. It imports the shared verifier.py from this folder."""
    global _JS_MODULE
    if _JS_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_js_verifier", HERE / "js" / "js_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _JS_MODULE = module
    return _JS_MODULE


def js_checker(name: str, output: str, sandbox="docker", executor=None, **_) -> dict:
    """One env type "js", two task folders: rl/js/tasks (JS verifier, node worker) and rl/jsts/tasks/js (Exercism)."""
    if (JS_RL_TASKS / name / "task.json").is_file():
        return _js().reward(JS_RL_TASKS / name, output, sandbox)
    return _jsts_checker(JS_TASKS, "js")(name, output, executor=executor)


_TOOL_CALL_MODULE = None


def _tool_call():
    """Load the data-only tool-call verifier from any working directory."""
    global _TOOL_CALL_MODULE
    if _TOOL_CALL_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_tool_call_verifier", HERE / "tool_call_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _TOOL_CALL_MODULE = module
    return _TOOL_CALL_MODULE


def tool_call_checker(name: str, output: str, **_) -> dict:
    task_dir = TOOL_CALL_TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no tool-call task {name!r} in {TOOL_CALL_TASKS}")
    return _tool_call().reward(task_dir, output)


_TOOLRESULT_MODULE = None


def _toolresult():
    """toolresult/toolresult_verifier.py, loaded by path like pool.py."""
    global _TOOLRESULT_MODULE
    if _TOOLRESULT_MODULE is None:
        import importlib.util  # noqa: PLC0415
        spec = importlib.util.spec_from_file_location("g10_rl_toolresult_verifier",
                                                      HERE / "toolresult" / "toolresult_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _TOOLRESULT_MODULE = module
    return _TOOLRESULT_MODULE


def toolresult_checker(name: str, output: str, **_) -> dict:
    task_dir = TOOLRESULT_TASKS / name
    if not (task_dir / "task.json").is_file():
        raise KeyError(f"no tool-result task {name!r} in {TOOLRESULT_TASKS}")
    return _toolresult().reward(task_dir, output)


register("code", code_checker)
register("swe", swe_checker)
register("indic", indic_checker)
register("math", math_checker)
register("go", go_checker)
register("agentic", agentic_checker)
register("math_pool", math_pool_checker)
register("js", js_checker)
register("ts", _jsts_checker(TS_TASKS, "ts"))
register("tool_call", tool_call_checker)
register("toolresult", toolresult_checker)


def list_envs() -> list[str]:
    ids = [f"code/{p.parent.name}" for p in sorted(TASKS.glob("*/task.json"))]
    ids += [f"swe/{p.parent.name}" for p in sorted(SWE_ENVS.glob("*/env.json"))]
    ids += [f"indic/{p.parent.name}" for p in sorted(INDIC_TASKS.glob("*/task.json"))]
    ids += [f"math/{p.parent.name}" for p in sorted(MATH_TASKS.glob("*/task.json"))]
    ids += [f"go/{p.parent.name}" for p in sorted(GO_TASKS.glob("*/task.json"))]
    ids += [f"agentic/{p.parent.name}" for p in sorted(AGENTIC_TASKS.glob("*/task.json"))]
    ids += [f"math_pool/{p.parent.name}" for p in sorted(MATH_POOL_TASKS.glob("*/task.json"))]
    ids += [f"js/{p.parent.name}" for p in sorted(JS_TASKS.glob("*/task.json"))]
    ids += [f"js/{p.parent.name}" for p in sorted(JS_RL_TASKS.glob("*/task.json"))]
    ids += [f"ts/{p.parent.name}" for p in sorted(TS_TASKS.glob("*/task.json"))]
    ids += [f"tool_call/{p.parent.name}" for p in sorted(TOOL_CALL_TASKS.glob("*/task.json"))]
    ids += [f"toolresult/{p.parent.name}" for p in sorted(TOOLRESULT_TASKS.glob("*/task.json"))]
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
    if env_type == "indic":
        return _indic().known_outputs(INDIC_TASKS / name)
    if env_type == "math":
        return _math().known_outputs(MATH_TASKS / name)
    if env_type == "tool_call":
        return _tool_call().known_outputs(TOOL_CALL_TASKS / name)
    if env_type == "toolresult":
        return _toolresult().known_outputs(TOOLRESULT_TASKS / name)
    if env_type == "go":
        meta = json.loads((GO_TASKS / name / "task.json").read_text(encoding="utf-8"))
        ref = (GO_TASKS / name / "reference.go").read_text(encoding="utf-8")
        # bad: the reference's own signature with a body that panics, so it compiles and fails the tests
        sig = re.search(rf"^func {meta['entry_point']}\(.*\{{$", ref, re.MULTILINE)
        if sig is None:
            raise ValueError(f"go/{name}: reference.go has no one-line signature for {meta['entry_point']}")
        bad = f"```go\npackage main\n\n{sig.group(0)}\n\tpanic(\"stub\")\n}}\n```"
        return f"```go\n{ref}\n```", bad
    if env_type == "js" and (JS_RL_TASKS / name / "task.json").is_file():
        meta = json.loads((JS_RL_TASKS / name / "task.json").read_text(encoding="utf-8"))
        ref = (JS_RL_TASKS / name / "reference.js").read_text(encoding="utf-8")
        bad = f"```javascript\nfunction {meta['entry_point']}() {{ return undefined; }}\n```"
        return f"```javascript\n{ref}\n```", bad
    if env_type in ("js", "ts"):
        return _jsts().known_outputs((JS_TASKS if env_type == "js" else TS_TASKS) / name)
    if env_type == "math_pool":
        return _math_pool().known_outputs(MATH_POOL_TASKS / name)
    if env_type == "agentic":
        return _agentic().known_outputs(AGENTIC_TASKS / name)
    raise KeyError(f"no known outputs for {env_type!r}")


def math_pool_unavailable() -> str | None:
    """Why the math set cannot be checked on this machine, or None. Its pool is data and stays out of the repository."""
    import importlib.util  # noqa: PLC0415
    pool = os.environ.get("G10_MATH_POOL")
    if not pool or not Path(pool).is_file():
        return "skipped: G10_MATH_POOL is not set to the RL data v1 math pool (rl/math_pool/README.md)"
    if importlib.util.find_spec("math_verify") is None:
        return "skipped: the math_verify package is not installed (rl/math_pool/README.md)"
    return None


def check_all(workers: int = 4, ids: list[str] | None = None) -> list[dict]:
    """Every id with its known good and bad output. math_pool ids are reported as skipped, never scored and never raised,
    when the pool or its dependency is absent, so the other sets can still be checked on a plain clone."""
    all_ids = ids or list_envs()
    why = math_pool_unavailable() if any(i.startswith("math_pool/") for i in all_ids) else None
    skipped = [{"env_id": i, "kind": kind, "score": None, "ok": True, "skipped": True, "reason": why, "seconds": 0.0}
               for i in all_ids if why and i.startswith("math_pool/") for kind in ("good", "bad")]
    jobs = [(i, kind, out) for i in all_ids if not (why and i.startswith("math_pool/"))
            for kind, out in zip(("good", "bad"), known_outputs(i))]

    def one(job):
        env_id, kind, out = job
        t0 = time.monotonic()
        score, info = reward(env_id, out)
        want = 1.0 if kind == "good" else 0.0
        return {"env_id": env_id, "kind": kind, "score": score, "ok": score == want,
                "reason": str(info.get("reason", ""))[:120], "seconds": round(time.monotonic() - t0, 2)}

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, jobs)) + skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check-all", action="store_true")
    ap.add_argument("--pool", action="store_true", help="use the warm code pool from pool.py")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--type", help="check only this environment type, for example indic")
    args = ap.parse_args(argv)
    if args.list:
        print("\n".join(list_envs()))
        return 0
    if args.check_all:
        ids = [i for i in list_envs() if i.split("/", 1)[0] == args.type] if args.type else None
        if args.type and not ids:
            ap.error(f"no environments of type {args.type!r}")
        if args.pool:
            pool = _pool()
            with pool.CodePool(workers=args.workers) as cp:
                configure(code_runner=cp.runner)
                rows = check_all(args.workers, ids)
            configure()
        else:
            rows = check_all(args.workers, ids)
        for r in rows:
            print(json.dumps(r))
        bad = [r for r in rows if not r["ok"]]
        skipped = [r for r in rows if r.get("skipped")]
        summary = {"checked": len(rows) - len(skipped), "wrong": len(bad)}
        if skipped:
            summary["skipped"] = len(skipped)
        print(json.dumps(summary))
        if skipped and len(skipped) == len(rows):
            return 2  # nothing was checked: not a pass
        return 1 if bad else 0
    ap.error("give --list or --check-all")
    return 2


if __name__ == "__main__":
    sys.exit(main())
