"""Binary reward for agentic first actions: one shell command, or one patch, scored by running it in a real SWE env.

    reward(task_dir, completion, executor=None) -> {"reward": 0 | 1, "reason": str, "task_id": str, "mode": str}

A task folder `rl/agentic/tasks/<task_id>/` has `task.json`, `prompt.md` (the model sees only this) and `hidden/`
(expected answer, never shown). `task.json["swe_env"]` names the environment in `swe-envs/<instance_id>/` whose image,
test patch and recorded test command the task reuses; `task.json["mode"]` is `command` or `patch`.

command mode  (the part `swe/<id>` cannot score)
    The model answers with ONE line in ONE fenced bash block: a pytest command. The line is parsed, never given to a
    shell: `pytest` or `python -m pytest`, a short flag allowlist, relative test paths. Anything else scores 0, so a
    command cannot edit a file, read a secret or fetch anything. The command runs in the env's image (same Docker
    limits as swe-envs/verify.py, network off) with the hidden test patch applied, and scores 1 only if
      * the set of tests it ran is exactly the set the repo's recorded test command runs (hidden/expected.json), and
      * every FAIL_TO_PASS test is reported failed (the command reproduces the bug at the base commit).
    So the whole suite, a `-k` subset, the wrong file, `-x`, a command that runs nothing and any non-test command all
    score 0, while every spelling of the right command (`-q`, `-v`, `python -m pytest`, `pytest`) scores 1.
patch mode  (a thin wrapper, not new signal)
    ONE fenced diff block, scored by swe-envs/verify.py reward(): the same hidden tests, the same refusal of test-file
    edits, symlinks, binaries, runner-shadowing paths and (as far as an in-process check can) forged reports. The wrapper only adds the one-block output rule and the check that
    the action type matches the task. The env is also available as swe/<id>; do not put both in one RL pool.

Output rules for both modes: everything up to the last `<|/think|>` is ignored and an unclosed `<|think|>` has no
answer; the visible reply may hold exactly one fenced block of the asked kind, none of another kind.

CLI:
    python agentic_verifier.py --reward <task_dir> <completion.txt>
    python agentic_verifier.py --check-task <task_dir>    # recorded command / gold patch scores 1, wrong ones 0
    python agentic_verifier.py --check-all
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shlex
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
SWE_ENVS = HERE.parent.parent / "swe-envs"
THINK_START, THINK_END = "<|think|>", "<|/think|>"
MAX_SCAN_CHARS = 20_000
MAX_COMMAND_CHARS = 300
MODES = ("command", "patch")
COMMAND_LANGS = ("", "bash", "sh", "shell", "zsh", "console")
PATCH_LANGS = ("diff", "patch")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_BLOCK = re.compile(r"```([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)\r?\n?```", re.DOTALL)
_SAFE_LINE = re.compile(r"^[A-Za-z0-9_./:=@+,\- ]+$")  # no quotes, pipes, ;, &, $, `, (), *, ?, [], ~, #, <, >, \
_PATH = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*(::[A-Za-z0-9_]+)*$")
_FLAGS = {"-q", "-v", "-vv", "-s", "-rA", "-rf", "-rfE", "-rs", "--no-header", "--color=no",
          "--tb=short", "--tb=long", "--tb=no", "--tb=line", "--tb=native", "--tb=auto"}
NOOP_PATCH = ("diff --git a/g10_noop.txt b/g10_noop.txt\nnew file mode 100644\nindex 0000000..e69de29\n"
              "--- /dev/null\n+++ b/g10_noop.txt\n@@ -0,0 +1 @@\n+noop\n")

_VERIFY = None


def swe_verify():
    """swe-envs/verify.py, loaded by path like rl/pool.py does."""
    global _VERIFY
    if _VERIFY is None:
        spec = importlib.util.spec_from_file_location("g10_agentic_swe_verify", SWE_ENVS / "verify.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("g10_agentic_swe_verify", module)
        spec.loader.exec_module(module)
        _VERIFY = module
    return _VERIFY


# --- reading the model's reply ----------------------------------------------------------------

def visible_reply(completion: str) -> str | None:
    text = completion or ""
    end = text.rfind(THINK_END)
    if end >= 0:
        text = text[end + len(THINK_END):]
    if THINK_START in text:
        return None
    return text[-MAX_SCAN_CHARS:]


def extract_block(completion: str, mode: str) -> tuple[str | None, str]:
    """(the one block's text, "ok") or (None, reason)."""
    reply = visible_reply(completion)
    if reply is None:
        return None, "think span not closed"
    blocks = _BLOCK.findall(reply)
    if mode == "command":
        want = [b for b in blocks if b[0].lower() in COMMAND_LANGS]
        other = [b for b in blocks if b[0].lower() not in COMMAND_LANGS]
    else:
        want = [b for b in blocks if b[0].lower() in PATCH_LANGS or (not b[0] and b[1].lstrip().startswith("diff --git"))]
        other = [b for b in blocks if b not in want]
    if not want:
        return None, ("wrong action type: a code block of another kind" if other else "no fenced block")
    if len(want) > 1 or other:
        return None, "more than one fenced block"
    return want[0][1], "ok"


def parse_command(block: str) -> tuple[list[str] | None, str]:
    """The pytest arguments of a one-line command, or (None, reason). Nothing here reaches a shell."""
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    if len(lines) != 1:
        return None, "the block must hold exactly one command line"
    line = lines[0][2:].strip() if lines[0].startswith("$ ") else lines[0]
    if len(line) > MAX_COMMAND_CHARS:
        return None, "command too long"
    if not _SAFE_LINE.match(line):
        return None, "shell syntax is not allowed"
    toks = line.split()
    if toks[:3] == ["python", "-m", "pytest"] or toks[:3] == ["python3", "-m", "pytest"]:
        rest = toks[3:]
    elif toks[0] in ("pytest", "py.test"):
        rest = toks[1:]
    else:
        return None, "only pytest commands are allowed"
    args: list[str] = []
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in _FLAGS:
            args.append(tok)
        elif tok == "-p" and rest[i + 1:i + 2] == ["no:cacheprovider"]:
            i += 1
        elif tok == "-o" and rest[i + 1:i + 2] == ["addopts="]:
            i += 1
        elif tok.startswith("-"):
            return None, "argument not allowed"
        elif _PATH.match(tok) and ".." not in tok.split("/"):
            args.append(tok)
        else:
            return None, "argument not allowed"
        i += 1
    return args, "ok"


# --- running -----------------------------------------------------------------------------------

def command_script(env: dict, args: list[str], token: str, test_patch: str | None = None) -> str:
    """Run on stdin (`bash -s`); test_patch (text) is delivered inside the script, see swe-envs/verify.py."""
    report = f"/tmp/g10_{token}.xml"
    restore = " ".join(shlex.quote(f) for f in env["test_files"])
    argv = " ".join(shlex.quote(a) for a in ["python", "-m", "pytest", "-p", "no:cacheprovider", "-o", "addopts=",
                                              f"--junitxml={report}", *args])
    v = swe_verify()
    return "\n".join([
        "cd /repo",
        f"for f in {restore}; do if git cat-file -e HEAD:\"$f\" 2>/dev/null; then git checkout -q HEAD -- \"$f\"; "
        "else rm -f \"$f\"; fi; done",
        *v.apply_test_patch(test_patch, token),
        f"timeout {int(env.get('timeout_s', 300))} {argv} > /tmp/g10_test.log 2>&1 < /dev/null; echo \"@@G10_EXIT $?@@\"",
        f"echo {v.REPORT_START}; cat {report} 2>/dev/null; echo {v.REPORT_END}",
        "tail -c 1500 /tmp/g10_test.log 2>/dev/null",
    ])


def run_command(env_dir: Path, env: dict, args: list[str], executor=None) -> dict:
    """Run the parsed pytest arguments once in the env image. {"ran": {id: passed}} or {"error": reason}."""
    v = swe_verify()
    token = uuid.uuid4().hex[:12]
    test_patch = (env_dir / "test.patch").read_bytes().decode("utf-8")
    started = time.monotonic()
    try:
        stdout, stderr = (executor or v.docker_run)(env, command_script(env, args, token, test_patch), {},
                                                    int(env.get("timeout_s", 300)) + 60)
    except TimeoutError:
        return {"error": "timeout"}
    if v.TEST_PATCH_FAIL in stdout:
        return {"error": "test.patch does not apply"}
    if v.REPORT_START not in stdout:
        return {"error": "no report: " + (stdout + stderr)[-300:]}
    m = v.EXIT_RE.search(stdout)
    if m and int(m.group(1)) == 124:
        return {"error": "tests timed out"}
    report = stdout.split(v.REPORT_START, 1)[1].split(v.REPORT_END, 1)[0].strip()
    if not report:
        return {"error": "the command produced no test report"}
    try:
        ran = v.parse_junit(report)
    except Exception:  # noqa: BLE001 - unreadable XML of any kind is a failed run
        return {"error": "unreadable test report"}
    return {"ran": ran, "seconds": round(time.monotonic() - started, 1)}


def load_task(task_dir: Path) -> tuple[dict, dict, Path, dict]:
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    env_dir = SWE_ENVS / meta["swe_env"]
    env = json.loads((env_dir / "env.json").read_text(encoding="utf-8"))
    hidden = json.loads((task_dir / "hidden" / "expected.json").read_text(encoding="utf-8")) \
        if meta["mode"] == "command" else {}
    return meta, env, env_dir, hidden


def reward(task_dir: Path, completion: str, executor=None) -> dict:
    meta, env, env_dir, hidden = load_task(Path(task_dir))
    base = {"task_id": meta["id"], "mode": meta["mode"]}
    block, why = extract_block(completion, meta["mode"])
    if block is None:
        return {**base, "reward": 0, "reason": why}
    if meta["mode"] == "patch":
        info = swe_verify().reward(env_dir, block.rstrip("\n") + "\n", executor)
        return {**base, "reward": int(info["reward"]), "reason": info.get("reason", "hidden tests " +
                ("pass" if info["reward"] else f"fail ({info.get('n_failed', '?')} tests)")),
                "seconds": info.get("seconds")}
    args, why = parse_command(block)
    if args is None:
        return {**base, "reward": 0, "reason": why}
    swe_verify().ensure_image(env_dir, env)
    side = run_command(env_dir, env, args, executor)
    if "error" in side:
        return {**base, "reward": 0, "reason": side["error"]}
    ran = side["ran"]
    if set(ran) != set(hidden["expected_tests"]):
        return {**base, "reward": 0, "reason": f"the command ran {len(ran)} tests, not the expected set"}
    still_passing = [t for t in hidden["must_fail"] if ran.get(t, True)]
    if still_passing:
        return {**base, "reward": 0, "reason": "the bug is not reproduced (a test that should fail passes)"}
    return {**base, "reward": 1, "reason": "ran exactly the expected tests and reproduced the failure",
            "seconds": side["seconds"]}


# --- known outputs and lint --------------------------------------------------------------------

def known_outputs(task_dir: Path) -> tuple[str, str]:
    """(an output that must score 1, an output that must score 0)."""
    meta, env, env_dir, hidden = load_task(Path(task_dir))
    if meta["mode"] == "patch":
        return "```diff\n" + (env_dir / "gold.patch").read_text(encoding="utf-8") + "```", \
               "```diff\n" + NOOP_PATCH + "```"
    return f"```bash\n{hidden['recorded_command']}\n```", "```bash\nls tests\n```"


def check_task(task_dir: Path, executor=None) -> dict:
    task_dir = Path(task_dir)
    problems: list[str] = []
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    if meta.get("mode") not in MODES:
        problems.append("mode must be command or patch")
    if not _NAME.match(meta.get("id", "")) or meta.get("id") != task_dir.name:
        problems.append("id must equal the folder name")
    prompt = (task_dir / "prompt.md").read_text(encoding="utf-8")
    if meta.get("mode") == "command":
        hidden = json.loads((task_dir / "hidden" / "expected.json").read_text(encoding="utf-8"))
        for secret in (hidden["recorded_command"], *hidden["expected_tests"][:5]):
            if secret in prompt:
                problems.append("prompt contains an expected value")
        env = json.loads((SWE_ENVS / meta["swe_env"] / "env.json").read_text(encoding="utf-8"))
        args, why = parse_command(hidden["recorded_command"])
        if args is None:
            problems.append(f"recorded command rejected by the parser: {why}")
        if not set(env["FAIL_TO_PASS"]) <= set(hidden["must_fail"]):
            problems.append("must_fail misses a FAIL_TO_PASS test")
    if "gold" in meta.get("id", ""):
        problems.append("id must not name the answer")
    good, bad = known_outputs(task_dir)
    got_good = reward(task_dir, good, executor)["reward"]
    got_bad = reward(task_dir, bad, executor)["reward"]
    if got_good != 1:
        problems.append("the recorded answer does not score 1")
    if got_bad != 0:
        problems.append("the wrong answer does not score 0")
    return {"task_id": meta.get("id"), "ok": not problems, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reward", nargs=2, metavar=("TASK_DIR", "COMPLETION"))
    ap.add_argument("--check-task", metavar="TASK_DIR")
    ap.add_argument("--check-all", action="store_true")
    args = ap.parse_args(argv)
    if args.reward:
        print(json.dumps(reward(Path(args.reward[0]), Path(args.reward[1]).read_text(encoding="utf-8"))))
        return 0
    if args.check_task:
        row = check_task(Path(args.check_task))
        print(json.dumps(row))
        return 0 if row["ok"] else 1
    if args.check_all:
        rows = [check_task(p.parent) for p in sorted(TASKS.glob("*/task.json"))]
        for r in rows:
            print(json.dumps(r))
        return 0 if rows and all(r["ok"] for r in rows) else 1
    ap.error("give --reward, --check-task or --check-all")
    return 2


if __name__ == "__main__":
    sys.exit(main())
