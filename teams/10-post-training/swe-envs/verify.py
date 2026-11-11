"""Verifier for G10 SWE environments: patch in, reward out.

An environment is a folder `swe-envs/<instance_id>/` with:
    env.json      fields named as in SWE-bench where they overlap (instance_id, repo, base_commit,
                  FAIL_TO_PASS, PASS_TO_PASS) plus our own (image, test_cmd, test_files, licence, provenance,
                  quality_verdict)
    Dockerfile    builds the repo at base_commit with no git history and pinned dependencies
    gold.patch    non-test part of the upstream PR
    test.patch    test part of the upstream PR (hidden: applied after the candidate patch)
    issue.md      the upstream issue text

Reward rule: 1 only if the candidate patch applies, touches no test file, adds no symlink, binary file or
submodule, the test report passes the integrity checks below, and every FAIL_TO_PASS and PASS_TO_PASS test
passes. A missing test counts as a failure.

Report integrity (the candidate's code runs in the same process as the tests, so it could try to rewrite the
report; see "Known limits" in README.md):
    - a sentinel test with a random name is added after the candidate patch and must be reported as failed;
    - the test command must exit with code 1 (tests failed, because the sentinel fails);
    - pytest only: the junit report may not show more passed tests than pytest printed in its summary line;
    - a test that is reported both passed and failed counts as failed.

Gold check (TSAI Gate 2: "the test fails before the patch and passes after it"):
    before = base + test.patch:        every FAIL_TO_PASS test fails, every PASS_TO_PASS test passes
    after  = base + gold + test.patch:  every test in both lists passes
Each side is run `--runs` times and must give the same result every time.

Usage:
    python verify.py <env_dir> --patch candidate.patch      # prints {"reward": 0|1, ...}
    python verify.py <env_dir> --check [--runs 5]           # gold check of one env
    python verify.py --check-all [--runs 5] [--write ../results/swe_gold_check.md]
    add --platform linux/amd64 to build and run another architecture (image tag gets a suffix)
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results" / "swe_gold_check.md"

REPORT_START, REPORT_END = "@@G10_REPORT_START@@", "@@G10_REPORT_END@@"
SUMMARY_START, SUMMARY_END = "@@G10_SUMMARY_START@@", "@@G10_SUMMARY_END@@"
APPLY_FAIL, TEST_PATCH_FAIL = "@@G10_APPLY_FAIL@@", "@@G10_TEST_PATCH_FAIL@@"
EXIT_RE = re.compile(r"@@G10_EXIT (\d+)@@")

# Container limits for every test run. --network=none: no downloads, no leaks. The rest stops fork bombs and
# privilege tricks (the image already runs as a non-root user).
DOCKER_LIMITS = ["--network=none", "--memory=2g", "--cpus=2", "--pids-limit=256", "--cap-drop=ALL",
                 "--security-opt=no-new-privileges"]

PLATFORM: str | None = None  # set by --platform; None = the Docker host's own architecture


# --- patches ----------------------------------------------------------------------------------

_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def unquote_git_path(path: str) -> str:
    """Undo git's C-style quoting ("tests/\\340\\244\\271/x.py" -> "tests/ह/x.py"). Unquoted paths pass through."""
    if not (len(path) >= 2 and path[0] == '"' and path[-1] == '"'):
        return path
    body, out, i = path[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            j = i + 1
            while j < len(body) and j < i + 4 and body[j] in "01234567":
                j += 1
            if j > i + 1:
                out.append(int(body[i + 1:j], 8) & 0xFF)
                i = j
            else:
                out.append(_ESCAPES.get(body[i + 1], ord(body[i + 1])))
                i += 2
            continue
        out += c.encode("utf-8")
        i += 1
    return out.decode("utf-8", "replace")


def _strip_side(path: str) -> str:
    return path[2:] if path[:2] in ("a/", "b/") else path


def _header_paths(rest: str) -> list[str]:
    """Paths from the text after `diff --git `, quoted or not."""
    if '"' in rest:
        tokens = re.findall(r'"(?:[^"\\]|\\.)*"|\S+', rest)
        if len(tokens) == 2:
            return [_strip_side(unquote_git_path(t)) for t in tokens]
    m = re.match(r"a/(.+?) b/(.+)$", rest)
    return [m.group(1), m.group(2)] if m else []


def patch_paths(patch: str) -> list[str]:
    """Paths a unified diff touches (both sides of renames and copies, without a/ b/ prefixes).

    Reads the `diff --git` header, the ---/+++ lines and rename/copy lines, and undoes git's quoting of
    non-ASCII and other special paths.
    """
    paths: set[str] = set()
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            paths.update(_header_paths(line[len("diff --git "):]))
        elif line.startswith(("--- ", "+++ ")):
            name = line[4:].split("\t", 1)[0]  # git adds a tab after names that contain spaces
            name = unquote_git_path(name)
            if name != "/dev/null":
                paths.add(_strip_side(name))
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            paths.add(unquote_git_path(line.split(" ", 2)[2]))
    paths.discard("")
    return sorted(paths)


def numstat_paths(patch: str) -> list[str] | None:
    """Paths as `git apply --numstat -z` reads them (git's own parser; no quoting). None if git can't read it."""
    try:
        # Run outside any repo: inside a repo subfolder, git apply silently skips paths outside that folder.
        with tempfile.TemporaryDirectory(prefix="g10numstat-") as tmp:
            proc = subprocess.run(["git", "apply", "--numstat", "-z", "-"], input=patch.encode("utf-8"),
                                  capture_output=True, timeout=60, cwd=tmp)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    fields, paths, i = proc.stdout.split(b"\0"), [], 0
    while i < len(fields):
        parts = fields[i].split(b"\t", 2)
        if len(parts) == 3 and parts[2]:
            paths.append(parts[2].decode("utf-8", "replace"))
            i += 1
        elif len(parts) == 3:  # rename or copy: the old and new names follow as two fields
            paths += [f.decode("utf-8", "replace") for f in fields[i + 1:i + 3]]
            i += 3
        else:
            i += 1
    return sorted(set(paths))


def patch_problems(patch: str) -> list[str]:
    """Things a candidate patch may not do at all, whatever the path."""
    problems = []
    if re.search(r"(?m)^(new file mode|new mode) 120000", patch):
        problems.append("adds a symlink")
    if re.search(r"(?m)^(new file mode|new mode) 160000|^index \S+ 160000", patch):
        problems.append("adds a submodule")
    if re.search(r"(?m)^(GIT binary patch|Binary files )", patch):
        problems.append("adds or changes a binary file")
    return problems


def is_test_path(path: str) -> bool:
    """Files the hidden tests own or that change how tests run. Candidates may not touch them."""
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    parts = p.split("/")[:-1]
    return (
        any(d in ("test", "tests", "testdata") for d in parts)
        or name.startswith("test_")
        or name.endswith(("_test.py", "_test.go", "_tests.py"))
        or name in ("conftest.py", "pytest.ini", "tox.ini", "noxfile.py")
    )


def split_patch(patch: str) -> tuple[str, str]:
    """Split a unified diff into (gold, test) parts by file."""
    gold, test = [], []
    for chunk in re.split(r"(?m)^(?=diff --git )", patch):
        if not chunk.strip():
            continue
        paths = patch_paths(chunk)
        (test if paths and all(is_test_path(p) for p in paths) else gold).append(chunk)
    return "".join(gold), "".join(test)


# --- test reports -----------------------------------------------------------------------------

def parse_junit(xml_text: str) -> dict[str, bool]:
    """pytest junit XML -> {"classname::name": passed}. A test listed twice passes only if both say passed."""
    out: dict[str, bool] = {}
    root = ET.fromstring(xml_text)
    for case in root.iter("testcase"):
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        passed = not any(child.tag in ("failure", "error", "skipped") for child in case)
        out[test_id] = out.get(test_id, True) and passed
    return out


def parse_go_json(stream: str) -> dict[str, bool]:
    """`go test -json` events -> {"package::TestName": passed}. Any fail or skip event for a test wins."""
    out: dict[str, bool] = {}
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("Test") and event.get("Action") in ("pass", "fail", "skip"):
            key = f"{event.get('Package', '')}::{event['Test']}"
            out[key] = out.get(key, True) and event["Action"] == "pass"
    return out


_COUNT_RE = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected|warnings?)")


def parse_pytest_summary(line: str) -> dict[str, int] | None:
    """pytest's last line ("== 1 failed, 7 passed in 0.12s ==", or "... in 0.12 seconds") -> counts."""
    if not re.search(r"\bin [\d.]+ ?s(econds)?\b", line):
        return None
    counts: dict[str, int] = {}
    for n, word in _COUNT_RE.findall(line):
        word = {"errors": "error", "warnings": "warning"}.get(word, word)
        counts[word] = counts.get(word, 0) + int(n)
    return counts or None


# --- the sentinel test ------------------------------------------------------------------------

def sentinel(env: dict, token: str) -> dict:
    """A test with a random name that always fails. It is written into the repo after the candidate patch."""
    if env.get("language", "python") == "go":
        go_tests = [f for f in env["test_files"] if f.endswith("_test.go")]
        folder = posixpath.dirname(go_tests[0]) if go_tests else ""
        name = f"TestZ{token}"
        return {"name": name, "file": posixpath.join(folder, f"z{token}_test.go"),
                "pkg_from": go_tests[0] if go_tests else "",
                "lines": ['import "testing"', f'func {name}(t *testing.T) {{ t.Fatal("check") }}']}
    name = f"test_{token}"
    return {"name": name, "file": f"test_{token}.py", "lines": [f"def {name}():", "    assert 0 == 1"]}


def check_report(results: dict[str, bool], sent: dict, exit_code: int | None, summary: str,
                 language: str) -> str | None:
    """Integrity checks on one run. Returns a problem, or None if the report can be trusted."""
    hits = [k for k in results if k.endswith("::" + sent["name"])]
    if len(hits) != 1:
        return "report integrity: the sentinel test is missing from the report"
    if results[hits[0]]:
        return "report integrity: the sentinel test is reported as passed"
    if exit_code != 1:
        return f"report integrity: test command exit code {exit_code}, expected 1 (the sentinel test fails)"
    if language != "go":
        counts = parse_pytest_summary(summary)
        if counts is None:
            return "report integrity: no pytest summary line in the log"
        printed = counts.get("passed", 0) + counts.get("xpassed", 0)
        in_report = sum(results.values())
        if in_report > printed:
            return f"report integrity: junit report has {in_report} passed tests, pytest printed {printed}"
    return None


# --- running one side in Docker -------------------------------------------------------------

def container_script(env: dict, with_candidate: bool, token: str = "0" * 12) -> str:
    restore = " ".join(shlex.quote(f) for f in env["test_files"])
    report = f"/tmp/g10_{token}.out"
    sent = sentinel(env, token)
    body = " ".join(f"echo {shlex.quote(line)};" for line in sent["lines"])
    if env.get("language", "python") == "go":
        write_sentinel = (f"pkg=$(sed -n 's/^package \\([A-Za-z0-9_]*\\).*/\\1/p' {shlex.quote(sent['pkg_from'])} "
                          f"| head -1); {{ echo \"package $pkg\"; {body} }} > {shlex.quote(sent['file'])}")
        run = f"{env['test_cmd']} > {report} 2>/tmp/g10_test.log"
    else:
        write_sentinel = f"{{ {body} }} > {shlex.quote(sent['file'])}"
        run = f"{env['test_cmd']} {shlex.quote(sent['file'])} --junitxml={report} > /tmp/g10_test.log 2>&1"
    lines = [
        "cd /repo",
        f"if ! git apply --whitespace=nowarn /patches/candidate.patch; then echo {APPLY_FAIL}; exit 0; fi"
        if with_candidate else ":",
        # Hidden tests win: put every test file back to the base version (or remove it if new) ...
        f"for f in {restore}; do if git cat-file -e HEAD:\"$f\" 2>/dev/null; then git checkout -q HEAD -- \"$f\"; "
        "else rm -f \"$f\"; fi; done",
        # ... then apply the upstream test change and add the sentinel test.
        f"if ! git apply --whitespace=nowarn /patches/test.patch; then echo {TEST_PATCH_FAIL}; exit 0; fi",
        write_sentinel,
        f"timeout {int(env.get('timeout_s', 300))} {run}; echo \"@@G10_EXIT $?@@\"",
        f"echo {REPORT_START}; cat {report} 2>/dev/null; echo {REPORT_END}",
        f"echo {SUMMARY_START}; grep -E ' in [0-9.]+ ?s' /tmp/g10_test.log 2>/dev/null | tail -1; echo {SUMMARY_END}",
        "tail -c 2000 /tmp/g10_test.log 2>/dev/null",
    ]
    return "\n".join(lines)


def image_ref(env: dict) -> str:
    """Image tag for this env; another platform gets its own tag so it never replaces the native image."""
    return env["image"] if not PLATFORM else f"{env['image']}-{PLATFORM.rsplit('/', 1)[-1]}"


def docker_run(env: dict, script: str, files: dict[str, bytes], timeout_s: float) -> tuple[str, str]:
    """Default executor: a fresh `docker run --rm` per run, with `files` mounted read-only at /patches.

    An executor takes (env, script, files, timeout_s), runs `script` with bash in the env image with `files` at
    /patches, and returns (stdout, stderr). It raises TimeoutError on timeout. rl/pool.py provides a pooled one.
    """
    with tempfile.TemporaryDirectory(prefix="g10swe-") as tmp:
        pdir = Path(tmp)
        for fname, data in files.items():
            (pdir / fname).write_bytes(data)  # bytes: no CRLF change
        name = f"g10swe-{uuid.uuid4().hex[:12]}"
        cmd = ["docker", "run", "--rm", "--name", name, *DOCKER_LIMITS,
               *(["--platform", PLATFORM] if PLATFORM else []),
               "-v", f"{pdir}:/patches:ro", image_ref(env), "bash", "-c", script]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            raise TimeoutError
    return proc.stdout, proc.stderr


def run_side(env_dir: Path, env: dict, candidate: str | None, executor=None) -> dict:
    """Run the hidden tests once on base (+ candidate). Returns {"results": {...}} or {"error": ...}."""
    token = uuid.uuid4().hex[:12]
    files = {"test.patch": (env_dir / "test.patch").read_bytes()}
    if candidate is not None:
        files["candidate.patch"] = candidate.encode("utf-8")
    start = time.monotonic()
    try:
        stdout, stderr = (executor or docker_run)(env, container_script(env, candidate is not None, token), files,
                                                  int(env.get("timeout_s", 300)) + 60)
    except TimeoutError:
        return {"error": "timeout"}
    seconds = time.monotonic() - start
    out = stdout
    if APPLY_FAIL in out:
        return {"error": "candidate patch does not apply"}
    if TEST_PATCH_FAIL in out:
        return {"error": "test.patch does not apply"}
    if REPORT_START not in out:
        return {"error": "no report: " + (out + stderr)[-500:]}
    m = EXIT_RE.search(out)
    exit_code = int(m.group(1)) if m else None
    if exit_code == 124:
        return {"error": "tests timed out"}
    report = out.split(REPORT_START, 1)[1].split(REPORT_END, 1)[0].strip()
    summary = out.split(SUMMARY_START, 1)[1].split(SUMMARY_END, 1)[0].strip() if SUMMARY_START in out else ""
    language = env.get("language", "python")
    try:
        results = parse_go_json(report) if language == "go" else parse_junit(report)
    except ET.ParseError:
        return {"error": "unreadable test report: " + out[-500:]}
    sent = sentinel(env, token)
    problem = check_report(results, sent, exit_code, summary, language)
    if problem:
        return {"error": problem}
    results = {k: v for k, v in results.items() if not k.endswith("::" + sent["name"])}
    return {"results": results, "seconds": round(seconds, 1)}


def load_env(env_dir: Path) -> dict:
    return json.loads((env_dir / "env.json").read_text(encoding="utf-8"))


def ensure_image(env_dir: Path, env: dict) -> str:
    """Build the env image if it is not present. Returns the image id."""
    ref = image_ref(env)
    have = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", ref], capture_output=True, text=True)
    if have.returncode != 0:
        build = subprocess.run(["docker", "build", "--progress=plain",
                                *(["--platform", PLATFORM] if PLATFORM else []), "-t", ref, str(env_dir)],
                               capture_output=True, text=True)
        if build.returncode != 0:
            raise RuntimeError(f"docker build failed for {ref}:\n{build.stderr[-2000:]}")
        have = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", ref],
                              capture_output=True, text=True, check=True)
    return have.stdout.strip()


# --- reward and gold check ------------------------------------------------------------------

def reward(env_dir: Path, candidate: str, executor=None) -> dict:
    """executor: None for a fresh `docker run` per call, or a pooled executor from rl/pool.py."""
    env = load_env(env_dir)
    problems = patch_problems(candidate)
    if problems:
        return {"instance_id": env["instance_id"], "reward": 0, "reason": "patch " + ", ".join(problems)}
    paths = set(patch_paths(candidate)) | set(numstat_paths(candidate) or [])
    touched = sorted(p for p in paths if is_test_path(p) or p in env["test_files"])
    if touched:
        return {"instance_id": env["instance_id"], "reward": 0, "reason": f"patch edits test files: {touched}"}
    ensure_image(env_dir, env)
    side = run_side(env_dir, env, candidate, executor)
    if "error" in side:
        return {"instance_id": env["instance_id"], "reward": 0, "reason": side["error"]}
    wanted = env["FAIL_TO_PASS"] + env["PASS_TO_PASS"]
    failed = [t for t in wanted if not side["results"].get(t, False)]
    return {"instance_id": env["instance_id"], "reward": int(not failed), "failed": failed[:20],
            "n_failed": len(failed), "seconds": side["seconds"]}


def gold_check(env_dir: Path, runs: int = 5) -> dict:
    env = load_env(env_dir)
    image_id = ensure_image(env_dir, env)
    gold = (env_dir / "gold.patch").read_text(encoding="utf-8")
    f2p, p2p = env["FAIL_TO_PASS"], env["PASS_TO_PASS"]
    row = {"instance_id": env["instance_id"], "repo": env["repo"], "f2p": len(f2p), "p2p": len(p2p),
           "image_id": image_id[:19], "runs": runs, "problems": []}
    before_ok = after_ok = 0
    seconds = []
    for _ in range(runs):
        b = run_side(env_dir, env, None)
        if "error" in b:
            row["problems"].append("before: " + b["error"])
        else:
            bad = [t for t in f2p if b["results"].get(t, False)] + [t for t in p2p if not b["results"].get(t, False)]
            before_ok += not bad
            if bad:
                row["problems"].append(f"before: {len(bad)} wrong, e.g. {bad[0]}")
        a = run_side(env_dir, env, gold)
        if "error" in a:
            row["problems"].append("after: " + a["error"])
        else:
            bad = [t for t in f2p + p2p if not a["results"].get(t, False)]
            after_ok += not bad
            seconds.append(a["seconds"])
            if bad:
                row["problems"].append(f"after: {len(bad)} failing, e.g. {bad[0]}")
    row.update(fails_before=f"{before_ok}/{runs}", passes_after=f"{after_ok}/{runs}",
               seconds=round(max(seconds), 1) if seconds else None,
               ok=before_ok == runs and after_ok == runs and len(f2p) > 0)
    row["problems"] = sorted(set(row["problems"]))
    return row


def env_dirs() -> list[Path]:
    return sorted(p.parent for p in HERE.glob("*/env.json"))


def write_table(rows: list[dict], path: Path) -> None:
    arch = PLATFORM or subprocess.run(["docker", "info", "-f", "{{.Architecture}}"], capture_output=True,
                                      text=True).stdout.strip()
    ok = sum(r["ok"] for r in rows)
    lines = [
        "# SWE environments: gold check",
        "",
        f"Generated by `swe-envs/verify.py --check-all --runs {rows[0]['runs'] if rows else 0}` on "
        f"{time.strftime('%Y-%m-%d %H:%M %Z')}, platform `{arch}`.",
        "",
        "Gold check: with the test patch applied, every FAIL_TO_PASS test fails on the base commit, and every "
        "FAIL_TO_PASS and PASS_TO_PASS test passes after the gold patch. Each side runs N times and must agree "
        "every time. Every run also passes the report integrity checks (sentinel test reported as failed, exit "
        "code 1, junit agrees with pytest's summary line). Docker flags for each run: "
        f"`{' '.join(DOCKER_LIMITS)}`.",
        "",
        f"**{ok} of {len(rows)} environments pass.**",
        "",
        "| # | instance_id | repo | FAIL_TO_PASS | PASS_TO_PASS | fails before | passes after | max run (s) | image | result |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        result = "pass" if r["ok"] else "FAIL: " + "; ".join(r["problems"])[:200]
        lines.append(f"| {i} | `{r['instance_id']}` | {r['repo']} | {r['f2p']} | {r['p2p']} | {r['fails_before']} | "
                     f"{r['passes_after']} | {r['seconds']} | `{r['image_id']}` | {result} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    global PLATFORM
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("env_dir", nargs="?", type=Path)
    ap.add_argument("--patch", type=Path, help="candidate patch file; prints the reward")
    ap.add_argument("--check", action="store_true", help="gold check of env_dir")
    ap.add_argument("--check-all", action="store_true", help="gold check of every env in swe-envs/")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--write", type=Path, help="write the markdown table here (with --check-all)")
    ap.add_argument("--platform", help="e.g. linux/amd64: build and run for this platform (default: the host's)")
    args = ap.parse_args(argv)
    PLATFORM = args.platform
    if args.check_all:
        rows = []
        for d in env_dirs():
            rows.append(gold_check(d, args.runs))
            print(json.dumps(rows[-1]), flush=True)
        if args.write:
            write_table(rows, args.write)
        return 0 if rows and all(r["ok"] for r in rows) else 1
    if args.env_dir is None:
        ap.error("give an env_dir, or use --check-all")
    if args.check:
        row = gold_check(args.env_dir, args.runs)
        print(json.dumps(row, indent=1))
        return 0 if row["ok"] else 1
    if args.patch:
        print(json.dumps(reward(args.env_dir, args.patch.read_text(encoding="utf-8"))))
        return 0
    ap.error("give --patch, --check or --check-all")
    return 2


if __name__ == "__main__":
    sys.exit(main())
