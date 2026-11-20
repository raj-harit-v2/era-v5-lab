"""Binary reward for JavaScript and TypeScript code tasks: the model writes one module, hidden jest tests judge it.

    reward(task_dir, completion, executor=None) -> {"reward": 0 | 1, "reason": str, "task_id": str, "language": str}

Each task is one Exercism practice exercise (exercism/javascript or exercism/typescript, MIT; statement, stub, reference
solution and tests are all human-written upstream, see task.json for the commit). The model sees `prompt.md`
(statement + the upstream stub) and answers with ONE fenced block holding the whole solution module (the last fenced
js/ts block counts). The hidden spec file replaces nothing the model can see: it is copied next to the candidate in a
fresh container with the network off, and jest runs it. Reward 1 only if every hidden test passes.

Report integrity. The candidate is NOT loaded in the spec's jest realm: root compiles it with babel before jest starts, and
the solution file the spec requires is a one-liner that loads the compiled code in its own V8 context (membrane.cjs:
no process, no require, no string eval, only a no-op console) and hands values back through a copying membrane (primitives,
arrays, plain objects, Map, Set, Date are copied; functions, classes and instances are wrapped; thrown values are rebuilt
as test-realm errors). Arguments into the candidate are rebuilt in its realm; a function or foreign object passed in
throws TypeError (a task whose tests pass callbacks needs the membrane extended; its reference check fails until then,
which jsts_verifier.py --check-all shows). So a candidate cannot edit the test registry (attacks J1, J1b, J5 in
attacks.py). Node documents `vm` as not a security boundary, so the checks below stay as defence in depth. The report is
written by the jest parent, which is a different user:
  * the container starts as root with only CAP_SETUID/CAP_SETGID; jest runs with workers (not --runInBand), and a
    setup file (GUARD_JS) drops every worker to the `runner` user before the candidate is loaded, then freezes the
    matcher table (no expect.extend, no custom equality testers). The jest parent stays root and writes the report to
    a root-owned file (stdout of jest), so the candidate cannot overwrite, race or pre-create the report, and it
    cannot signal or trace the parent;
  * a sentinel test with a random name is added in its own file and must be reported as failed;
  * four canary tests (random name and random values; toBe, toEqual, toStrictEqual, toThrow, each asserting something
    false) are appended to the spec itself, so they run in the same jest realm as the candidate and must all be
    reported as failed: a candidate that patches the matchers or Object.is from inside jest makes a canary pass;
  * jest must exit with code 1 (the sentinel fails), print a readable JSON report, and the passed tests must equal the
    expected count measured on the reference when the task was built (a skipped test, a crash at import or a
    process.exit(0) therefore score 0);
  * the report must hold no failed test other than the sentinel.
A candidate can still read the spec file in its own container, and a `vm` escape is not ruled out; see README.md, "Limits".

The hidden spec of an Exercism exercise enables only its first test by default (`xtest`); build_tasks.py rewrites
xtest/xit/xdescribe to test/it/describe so every upstream test counts.

CLI:
    python jsts_verifier.py --reward <task_dir> <completion.txt>
    python jsts_verifier.py --check-task <task_dir>      # reference scores 1, the upstream stub scores 0, lint
    python jsts_verifier.py --check-all
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
IMAGE = "g10-jsts-rl:1"
LANGS = {"js": {"ext": "js", "fences": ("js", "javascript", "mjs", "")},
         "ts": {"ext": "ts", "fences": ("ts", "typescript", "")}}
# The container starts as root so that the jest parent can keep the report out of reach. Capabilities kept: SETUID and
# SETGID (the guard drops each worker to `runner`), CHOWN and DAC_OVERRIDE (the root script hands /work/run to
# `runner`). A worker loses all of them when it drops to `runner`, before the candidate module is loaded.
DOCKER_LIMITS = ["--network=none", "--memory=1g", "--cpus=2", "--pids-limit=256", "--user=0:0", "--cap-drop=ALL",
                 "--cap-add=SETUID", "--cap-add=SETGID", "--cap-add=CHOWN", "--cap-add=DAC_OVERRIDE",
                 "--security-opt=no-new-privileges"]
# Runs in every jest worker before the candidate module is loaded. Failing here fails the suite, so the score is 0.
GUARD_JS = r"""
const uid = Number(process.env.G10_RUNNER_UID);
process.setgid(uid);
process.setuid(uid);
if (process.getuid() === 0 || process.geteuid() === 0) throw new Error('guard: still root');
const state = globalThis[Symbol.for('$$jest-matchers-object')];
Object.freeze(state.matchers);
Object.freeze(state.customEqualityTesters);
const refuse = () => { throw new Error('guard: matchers cannot be changed'); };
for (const name of ['extend', 'addEqualityTesters']) {
  Object.defineProperty(globalThis.expect, name, { value: refuse, writable: false, configurable: false });
}
Object.freeze(globalThis.expect);
"""
MEMBRANE_JS = (HERE / "membrane.cjs").read_text()
MAX_CODE_CHARS = 40_000
TIMEOUT_S = 60
THINK_START, THINK_END = "<|think|>", "<|/think|>"
_BLOCK = re.compile(r"```([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)\r?\n?```", re.DOTALL)
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
REPORT_START, REPORT_END = "@@G10_REPORT_START@@", "@@G10_REPORT_END@@"
EXIT_RE = re.compile(r"@@G10_EXIT (\d+)@@")


def extract_code(completion: str, language: str) -> tuple[str | None, str]:
    text = completion or ""
    end = text.rfind(THINK_END)
    if end >= 0:
        text = text[end + len(THINK_END):]
    if THINK_START in text:
        return None, "think span not closed"
    fences = LANGS[language]["fences"]
    blocks = [b[1] for b in _BLOCK.findall(text[-4 * MAX_CODE_CHARS:]) if b[0].lower() in fences]
    if not blocks:
        return None, "no code block"
    code = blocks[-1]
    if len(code) > MAX_CODE_CHARS:
        return None, "code too long"
    if not code.strip():
        return None, "empty code block"
    return code, "ok"


def docker_run(script: str, files: dict[str, bytes], timeout_s: float) -> tuple[str, str]:
    """A fresh `docker run --rm` with `files` mounted read-only at /patches. Raises TimeoutError."""
    with tempfile.TemporaryDirectory(prefix="g10jsts-") as tmp:
        # root in the container has no DAC_OVERRIDE, so the mounted files must be world-readable
        Path(tmp).chmod(0o755)
        for name, data in files.items():
            (Path(tmp) / name).write_bytes(data)
            (Path(tmp) / name).chmod(0o644)
        name = f"g10jsts-{uuid.uuid4().hex[:12]}"
        cmd = ["docker", "run", "--rm", "--name", name, *DOCKER_LIMITS, "-v", f"{tmp}:/patches:ro", IMAGE,
               "bash", "-c", script]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            raise TimeoutError from None
    return proc.stdout, proc.stderr


def container_script(meta: dict, token: str) -> str:
    ext, spec_ext = LANGS[meta["language"]]["ext"], ("spec.js" if meta["language"] == "js" else "test.ts")
    return "\n".join([
        "mkdir -p /tmp/jc && chmod 1777 /tmp/jc",  # per-run transform cache for the workers (fresh container)
        "export G10_RUNNER_UID=$(id -u runner)",
        "cat > /work/guard.cjs <<'G10_GUARD_EOF'", GUARD_JS.strip(), "G10_GUARD_EOF",
        "cd /work/run",
        "mkdir -p /work/cand", f"cp /patches/candidate.{ext} /work/cand/src.{ext}",
        "cat > /work/membrane.cjs <<'G10_MEMBRANE_EOF'", MEMBRANE_JS.strip(), "G10_MEMBRANE_EOF",
        # compiled by root, outside jest; a syntax error leaves no file and the load fails (score 0)
        "node -e 'const b=require(\"/work/node_modules/@babel/core\");const fs=require(\"fs\");"
        "const [s,o]=process.argv.slice(1);fs.writeFileSync(o,b.transformSync(fs.readFileSync(s,\"utf8\"),"
        "{filename:s,configFile:\"/work/babel.config.cjs\",babelrc:false}).code)' "
        f"/work/cand/src.{ext} /work/cand/cand.cjs 2>/dev/null; chmod 644 /work/cand/cand.cjs 2>/dev/null",
        f"echo \"module.exports = require('/work/membrane.cjs').load('/work/cand/cand.cjs');\" > ./{meta['solution_file']}",
        f"cp /patches/spec ./{meta['spec_file']}",
        f"cp /patches/sentinel ./z{token}.{spec_ext}",
        "chown -R runner /work/run",
        # The jest parent (root) prints the JSON report to /tmp/g10_out, a root-owned file that the redirect creates
        # before `umask 000` applies (the umask only lets the workers, which run as `runner`, write the jest cache).
        f"(umask 000; timeout {TIMEOUT_S} /work/node_modules/.bin/jest --ci --maxWorkers=2 --config /work/jest.config.cjs "
        "--cacheDirectory=/tmp/jc --setupFilesAfterEnv /work/guard.cjs --json) > /tmp/g10_out 2> /tmp/g10_log; "
        "echo \"@@G10_EXIT $?@@\"",
        # the report is read by this root script after jest has exited, never by the candidate
        f"echo {REPORT_START}; cat /tmp/g10_out 2>/dev/null; echo {REPORT_END}",
        "tail -c 1200 /tmp/g10_log 2>/dev/null",
    ])


def sentinel_spec(token: str) -> str:
    return f"test('z{token}', () => {{ expect(1).toBe(2); }});\n"


def canary_tests(token: str) -> str:
    """Assertions that are false by construction, appended to the hidden spec. Random values, so a candidate cannot
    special-case them without parsing the spec at run time; each uses a different matcher."""
    rnd = random.SystemRandom()
    a, b, c, d = (rnd.randrange(10**8, 10**9) for _ in range(4))
    return "\n".join([
        f"test('z{token}c0', () => {{ expect({a}).toBe({b}); }});",
        f"test('z{token}c1', () => {{ expect({{k: [{a}]}}).toEqual({{k: [{c}]}}); }});",
        f"test('z{token}c2', () => {{ expect({{k: '{d}'}}).toStrictEqual({{k: '{a}'}}); }});",
        f"test('z{token}c3', () => {{ expect(() => {{ return {b}; }}).toThrow(); }});",
        ""])


def run_candidate(task_dir: Path, meta: dict, code: str, executor=None) -> dict:
    """{"passed": n, "failed": [names]} or {"error": reason}."""
    token = uuid.uuid4().hex[:12]
    files = {"candidate." + LANGS[meta["language"]]["ext"]: code.encode("utf-8"),
             "spec": (task_dir / "hidden" / meta["spec_file"]).read_bytes() + b"\n" + canary_tests(token).encode("utf-8"),
             "sentinel": sentinel_spec(token).encode("utf-8")}
    try:
        stdout, stderr = (executor or docker_run)(container_script(meta, token), files, TIMEOUT_S + 60)
    except TimeoutError:
        return {"error": "timeout"}
    if REPORT_START not in stdout:
        return {"error": "no report: " + (stdout + stderr)[-300:]}
    m = EXIT_RE.search(stdout)
    exit_code = int(m.group(1)) if m else None
    if exit_code == 124:
        return {"error": "tests timed out"}
    raw = stdout.split(REPORT_START, 1)[1].split(REPORT_END, 1)[0].strip()
    try:
        report = json.loads(raw)
        results = [(a["fullName"], a["status"]) for suite in report["testResults"] for a in suite["assertionResults"]]
    except (ValueError, KeyError, TypeError):
        return {"error": "unreadable test report (the module may fail to load)"}
    hits = [s for n, s in results if n == f"z{token}"]
    if hits != ["failed"]:
        return {"error": "report integrity: the sentinel test is missing or not reported as failed"}
    if exit_code != 1:
        return {"error": f"report integrity: jest exit code {exit_code}, expected 1 (the sentinel fails)"}
    canaries = [(n, s) for n, s in results if n.startswith(f"z{token}c")]
    real = [(n, s) for n, s in results if n != f"z{token}" and not n.startswith(f"z{token}c")]
    canary_ok = sorted(n for n, _ in canaries) == [f"z{token}c{i}" for i in range(4)] and all(s == "failed" for _, s in canaries)
    if not canary_ok and (real or canaries):  # no results at all is a module that failed to load: the ordinary reason below
        return {"error": "report integrity: a canary assertion was missing or did not fail (matchers were tampered with)"}
    return {"passed": sum(s == "passed" for _, s in real), "failed": [n for n, s in real if s != "passed"]}


def reward(task_dir: Path, completion: str, executor=None) -> dict:
    task_dir = Path(task_dir)
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    base = {"task_id": meta["id"], "language": meta["language"]}
    code, why = extract_code(completion, meta["language"])
    if code is None:
        return {**base, "reward": 0, "reason": why}
    side = run_candidate(task_dir, meta, code, executor)
    if "error" in side:
        return {**base, "reward": 0, "reason": side["error"]}
    if side["failed"] or side["passed"] != meta["expected_tests"]:
        return {**base, "reward": 0, "reason": f"{meta['expected_tests'] - side['passed']} of {meta['expected_tests']} hidden tests "
                f"did not pass", "passed": side["passed"], "total": meta["expected_tests"]}
    return {**base, "reward": 1, "reason": "all hidden tests pass", "passed": side["passed"],
            "total": meta["expected_tests"]}


def known_outputs(task_dir: Path) -> tuple[str, str]:
    """(an output that must score 1, an output that must score 0): the upstream reference and the upstream stub."""
    meta = json.loads((Path(task_dir) / "task.json").read_text(encoding="utf-8"))
    fence = {"js": "javascript", "ts": "typescript"}[meta["language"]]
    ref = (Path(task_dir) / "hidden" / meta["reference_file"]).read_text(encoding="utf-8")
    stub = (Path(task_dir) / "stub" / meta["solution_file"]).read_text(encoding="utf-8")
    return f"```{fence}\n{ref}\n```", f"```{fence}\n{stub}\n```"


def check_task(task_dir: Path, executor=None) -> dict:
    task_dir = Path(task_dir)
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    if not _NAME.match(meta.get("id", "")) or meta["id"] != task_dir.name:
        problems.append("id must equal the folder name")
    if meta.get("language") not in LANGS or task_dir.parent.name != meta.get("language"):
        problems.append("language must match the parent folder (js or ts)")
    prompt = (task_dir / "prompt.md").read_text(encoding="utf-8")
    ref = (task_dir / "hidden" / meta["reference_file"]).read_text(encoding="utf-8")
    spec = (task_dir / "hidden" / meta["spec_file"]).read_text(encoding="utf-8")
    if ref.strip() and ref.strip() in prompt:
        problems.append("prompt contains the reference solution")
    first_test = re.search(r"(?:test|it)\(\s*['\"`]([^'\"`]{12,})['\"`]", spec)
    if first_test and first_test.group(1) in prompt:
        problems.append("prompt contains a hidden test name")
    if re.search(r"\b(xtest|xit|xdescribe)\b", spec):
        problems.append("hidden spec still has disabled tests")
    good, bad = known_outputs(task_dir)
    got_good, got_bad = reward(task_dir, good, executor), reward(task_dir, bad, executor)
    if got_good["reward"] != 1:
        problems.append(f"the reference does not score 1 ({got_good['reason']})")
    if got_bad["reward"] != 0:
        problems.append("the stub does not score 0")
    return {"task_id": meta["id"], "language": meta.get("language"), "ok": not problems, "problems": problems}


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
        rows = [check_task(p.parent) for p in sorted(TASKS.glob("*/*/task.json"))]
        for r in rows:
            print(json.dumps(r))
        return 0 if rows and all(r["ok"] for r in rows) else 1
    ap.error("give --reward, --check-task or --check-all")
    return 2


if __name__ == "__main__":
    sys.exit(main())
