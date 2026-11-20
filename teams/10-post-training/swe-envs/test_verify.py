"""Tests for the SWE environment harness (verify.py, make_env.py, import_pool.py). Offline: no Docker, no network.

The Docker step (`verify.run_side`) is replaced by a fake that returns fixed test results, so these tests
check the logic around it: patch splitting, test-file protection, reward rules, the gold check, the
FAIL_TO_PASS / PASS_TO_PASS derivation and the shipped environments' files.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

parametrize = pytest.mark.parametrize

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = _load("g10_swe_verify", HERE / "verify.py")
make_env = _load("g10_swe_make_env", HERE / "make_env.py")
import_pool = _load("g10_swe_import_pool", HERE / "import_pool.py")
rebench_pilot = _load("g10_swe_rebench_pilot", HERE / "rebench_pilot.py")

DIFF = """diff --git a/pkg/core.py b/pkg/core.py
index 1111111..2222222 100644
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a + b + 1
+    return a + b
diff --git a/tests/test_core.py b/tests/test_core.py
index 3333333..4444444 100644
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -1,2 +1,5 @@
 from pkg.core import add
+
+def test_add():
+    assert add(1, 2) == 3
diff --git a/CHANGES.rst b/CHANGES.rst
index 5555555..6666666 100644
--- a/CHANGES.rst
+++ b/CHANGES.rst
@@ -1 +1,2 @@
 Changes
+- fix add
"""


# --- patch handling ---------------------------------------------------------------------------

def test_patch_paths_lists_every_file_once():
    assert verify.patch_paths(DIFF) == ["CHANGES.rst", "pkg/core.py", "tests/test_core.py"]


# Git quotes non-ASCII paths in octal (PR #27 review, point 3). "\340\244\271" is the UTF-8 for Devanagari "ha".
QUOTED = ('diff --git "a/tests/\\340\\244\\271/conftest.py" "b/tests/\\340\\244\\271/conftest.py"\n'
          "new file mode 100644\nindex 0000000..e69de29\n--- /dev/null\n"
          '+++ "b/tests/\\340\\244\\271/conftest.py"\n@@ -0,0 +1 @@\n+x = 1\n')
SPACED = ("diff --git a/pkg/a b.py b/pkg/a b.py\nindex 1111111..2222222 100644\n--- a/pkg/a b.py\t\n"
          "+++ b/pkg/a b.py\t\n@@ -1 +1 @@\n-a\n+b\n")


def test_patch_paths_reads_git_quoted_and_spaced_paths():
    assert verify.patch_paths(QUOTED) == ["tests/\u0939/conftest.py"]
    assert verify.patch_paths(SPACED) == ["pkg/a b.py"]  # no stray tab entry
    assert verify.unquote_git_path('"a\\tb\\"c"') == 'a\tb"c'


def test_numstat_paths_matches_our_parser():
    got = verify.numstat_paths(QUOTED + SPACED)
    if got is None:
        pytest.skip("git not available")
    assert got == ["pkg/a b.py", "tests/\u0939/conftest.py"]


@pytest.mark.parametrize("patch,problem", [
    ("diff --git a/x b/x\nnew file mode 120000\n", "symlink"),
    ("diff --git a/x b/x\nnew file mode 160000\n", "submodule"),
    ("diff --git a/x.bin b/x.bin\nGIT binary patch\nliteral 3\n", "binary"),
])
def test_patch_problems_flags_symlinks_submodules_and_binaries(patch, problem):
    assert any(problem in p for p in verify.patch_problems(patch))
    assert verify.patch_problems(DIFF) == []


@pytest.mark.parametrize("path,expected", [
    ("tests/test_core.py", True), ("test/helpers.py", True), ("pkg/test_utils.py", True),
    ("pkg/core_test.go", True), ("conftest.py", True), ("src/pkg/conftest.py", True), ("tox.ini", True),
    ("pkg/testdata/x.json", True), ("pkg/core.py", False), ("docs/testing.rst", False),
    ("pkg/contest.py", False), ("CHANGES.rst", False), ("pkg/attestation.py", False),
])
def test_is_test_path(path, expected):
    assert verify.is_test_path(path) is expected


def test_split_patch_puts_tests_in_test_patch_and_the_rest_in_gold():
    gold, test = verify.split_patch(DIFF)
    assert verify.patch_paths(gold) == ["CHANGES.rst", "pkg/core.py"]
    assert verify.patch_paths(test) == ["tests/test_core.py"]
    assert sorted((gold + test).splitlines()) == sorted(DIFF.splitlines())


# --- reports ----------------------------------------------------------------------------------

def test_parse_junit_counts_failures_errors_and_skips_as_not_passed():
    xml = """<?xml version="1.0"?><testsuites><testsuite>
      <testcase classname="tests.test_core" name="test_ok"/>
      <testcase classname="tests.test_core" name="test_bad"><failure message="x"/></testcase>
      <testcase classname="tests.test_core" name="test_err"><error message="x"/></testcase>
      <testcase classname="tests.test_core.TestK" name="test_skip[1]"><skipped message="x"/></testcase>
    </testsuite></testsuites>"""
    assert verify.parse_junit(xml) == {
        "tests.test_core::test_ok": True, "tests.test_core::test_bad": False,
        "tests.test_core::test_err": False, "tests.test_core.TestK::test_skip[1]": False}


def test_parse_junit_a_test_listed_twice_passes_only_if_both_pass():
    xml = """<testsuites><testsuite>
      <testcase classname="t" name="a"><failure message="x"/></testcase>
      <testcase classname="t" name="a"/>
    </testsuite></testsuites>"""
    assert verify.parse_junit(xml) == {"t::a": False}


def test_parse_go_json_a_later_forged_pass_does_not_win():
    stream = "\n".join(json.dumps(e) for e in [
        {"Action": "fail", "Package": "m", "Test": "TestA"},
        {"Action": "pass", "Package": "m", "Test": "TestA"},
    ])
    assert verify.parse_go_json(stream) == {"m::TestA": False}


@pytest.mark.parametrize("line,counts", [
    ("1 failed, 7 passed in 0.12s", {"failed": 1, "passed": 7}),
    ("==== 2 failed, 5 passed, 1 xpassed, 3 warnings in 1.05 seconds ====",
     {"failed": 2, "passed": 5, "xpassed": 1, "warning": 3}),
    ("1 failed, 2 errors in 0.5s (0:00:00)", {"failed": 1, "error": 2}),
    ("collected 8 items", None),
])
def test_parse_pytest_summary(line, counts):
    assert verify.parse_pytest_summary(line) == counts


def test_parse_go_json_reads_test_level_events_only():
    stream = "\n".join(json.dumps(e) for e in [
        {"Action": "run", "Package": "m/semver", "Test": "TestA"},
        {"Action": "pass", "Package": "m/semver", "Test": "TestA"},
        {"Action": "fail", "Package": "m/semver", "Test": "TestB"},
        {"Action": "fail", "Package": "m/semver"},
    ]) + "\nnot json\n"
    assert verify.parse_go_json(stream) == {"m/semver::TestA": True, "m/semver::TestB": False}


# --- the container script ---------------------------------------------------------------------

ENV = {"instance_id": "toy__toy-1", "repo": "toy/toy", "image": "g10-swe/toy__toy-1:v1",
       "test_files": ["tests/test_core.py"], "test_cmd": "python -m pytest -q tests/test_core.py",
       "timeout_s": 60, "FAIL_TO_PASS": ["tests.test_core::test_add"],
       "PASS_TO_PASS": ["tests.test_core::test_import"]}


def test_container_script_restores_test_files_before_applying_hidden_tests():
    script = verify.container_script(ENV, with_candidate=True, token="abc123")
    apply_candidate = script.index("/patches/candidate.patch")
    restore = script.index("git checkout -q HEAD --")
    apply_tests = script.index("/patches/test.patch")
    sentinel = script.index(">> tests/test_core.py")  # appended to the file of the first FAIL_TO_PASS test
    assert apply_candidate < restore < apply_tests < sentinel
    assert "timeout 60 python -m pytest -q tests/test_core.py --junitxml=/tmp/g10_abc123.out" in script
    assert "test_abc123" not in script  # no sentinel file of its own on the command line


def test_container_script_delivers_the_test_patch_inside_the_script_and_removes_it_before_the_tests():
    script = verify.container_script(ENV, with_candidate=True, token="abc123", test_patch="diff --git a/x b/x\n+hidden\n")
    assert "/patches/test.patch" not in script
    put, apply_, rm, tests = (script.index(m) for m in ("cat > /tmp/.g10tp", "git apply --whitespace=nowarn /tmp/.g10tp",
                                                          "rm -f /tmp/.g10tp", "timeout 60"))
    assert put < apply_ < rm < tests and "+hidden" in script


def test_the_sentinel_is_named_and_placed_like_a_hidden_test():
    """Job W, P1/P1b: a forger spared the old sentinel by its `test_<12 hex>` name or its own untracked file."""
    sent = verify.sentinel(ENV, "abc123")
    assert sent["name"].startswith("test_add_") and sent["file"] == "tests/test_core.py" and sent["append"]
    assert verify.sentinel(ENV, "abc123") == sent  # run_side and check_report derive the same one from the token
    taken = {"test_add", "test_import"}
    assert sent["name"] not in taken and "abc123" not in "".join(sent["lines"]) + sent["name"] + sent["file"]


def test_the_sentinel_file_is_found_for_a_class_based_test_id():
    env = {**ENV, "test_files": ["pkg/tests/test_x.py"], "FAIL_TO_PASS": ["pkg.tests.test_x.TestThing::test_it[a b]"],
           "PASS_TO_PASS": []}
    assert verify.sentinel(env, "abc123")["file"] == "pkg/tests/test_x.py"


def test_container_script_adds_a_go_sentinel_in_the_test_package():
    env = {**ENV, "language": "go", "test_files": ["pkg/version_test.go"], "test_cmd": "go test -json -count=1 ./pkg"}
    script = verify.container_script(env, with_candidate=True, token="abc123")
    assert "pkg/zabc123_test.go" in script and "func TestZabc123(t *testing.T)" in script
    assert "sed -n" in script and "pkg/version_test.go" in script


def test_container_script_without_candidate_skips_candidate_apply():
    assert "candidate.patch" not in verify.container_script(ENV, with_candidate=False)


@parametrize("path", ["pytest.py", "pytest/__init__.py", "_pytest/runner.py", "pluggy/_hooks.py", "py.py",
                                  "sitecustomize.py", "usercustomize.py", "evil.pth", "sub/evil.pth", "json.py",
                                  "os.py", "re/__init__.py", "logging/handlers.py", "./pytest.py"])
def test_paths_that_shadow_the_test_runner_are_refused(path):
    assert verify.shadows_runner(path)


@parametrize("path", ["pkg/core.py", "tomlkit/__init__.py", "src/pytest.py", "semver.py", "docs/json.py",
                                  "setup.py", "README.md", "click/core.py"])
def test_ordinary_source_paths_are_not_refused(path):
    assert not verify.shadows_runner(path)


def test_no_gold_patch_is_refused_as_shadowing_the_runner_and_every_python_sentinel_lands_in_a_run_test_file():
    for d in sorted(HERE.glob("*/env.json")):
        env = json.loads(d.read_text(encoding="utf-8"))
        gold = (d.parent / "gold.patch").read_text(encoding="utf-8")
        if env.get("language", "python") == "go":
            continue
        assert not [p for p in verify.patch_paths(gold) if verify.shadows_runner(p)], d.parent.name
        sent = verify.sentinel(env, "abc123")
        assert sent.get("append"), (d.parent.name, "no test file found for the first FAIL_TO_PASS id")
        assert sent["file"] in env["test_cmd"] or sent["file"].rsplit("/", 1)[0] in env["test_cmd"], d.parent.name


def test_patch_flags_name_suspicious_code_without_refusing_it():
    patch = "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1 +1,2 @@\n x\n+import _pytest.runner\n"
    assert verify.patch_flags(patch) == ["_pytest"]
    assert verify.patch_flags("diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1 +1,2 @@\n x\n+y = 1\n") == []


# --- report integrity (PR #27 review, point 1) -------------------------------------------------

SENT = verify.sentinel(ENV, "abc123")
HONEST = {"tests.test_core::test_add": True, "tests.test_core::test_import": True,
          f"tests.test_core::{SENT['name']}": False}


def test_check_report_accepts_an_honest_run():
    assert verify.check_report(HONEST, SENT, 1, "1 failed, 2 passed in 0.1s", "python") is None


@pytest.mark.parametrize("results,exit_code,summary,problem", [
    ({k: True for k in HONEST if SENT["name"] not in k}, 1, "1 failed, 2 passed in 0.1s", "missing"),  # forged file
    ({**HONEST, f"tests.test_core::{SENT['name']}": True}, 1, "3 passed in 0.1s", "reported as passed"),  # flipped all
    (HONEST, 0, "1 failed, 2 passed in 0.1s", "exit code 0"),                                     # os._exit(0)
    (HONEST, 1, "2 failed, 1 passed in 0.1s", "pytest printed 1"),                              # flipped one
    (HONEST, 1, "", "no pytest summary"),
])
def test_check_report_catches_forged_reports(results, exit_code, summary, problem):
    assert problem in verify.check_report(results, SENT, exit_code, summary, "python")


def _docker_output(junit: str, exit_code: int, summary: str) -> str:
    return (f"@@G10_EXIT {exit_code}@@\n{verify.REPORT_START}\n{junit}\n{verify.REPORT_END}\n"
            f"{verify.SUMMARY_START}\n{summary}\n{verify.SUMMARY_END}\n")


def test_run_side_rejects_the_junit_file_rewritten_by_an_atexit_hook(env_dir, monkeypatch):
    """The attack from the PR #27 review: the candidate rewrites the report with every wanted test passing."""
    forged = ('<testsuites><testsuite name="x"><testcase classname="tests.test_core" name="test_add"/>'
              '<testcase classname="tests.test_core" name="test_import"/></testsuite></testsuites>')

    class Proc:
        stdout, stderr = _docker_output(forged, 1, "2 failed, 1 passed in 0.1s"), ""

    monkeypatch.setattr(verify.subprocess, "run", lambda *a, **k: Proc())
    out = verify.run_side(env_dir, ENV, "diff --git a/pkg/core.py b/pkg/core.py\n")
    assert "error" in out and "sentinel" in out["error"]


def test_run_side_drops_the_sentinel_from_honest_results(env_dir, monkeypatch):
    monkeypatch.setattr(verify.uuid, "uuid4", lambda: type("U", (), {"hex": "abc123" + "0" * 26})())
    sent_name = verify.sentinel(ENV, "abc123000000")["name"]
    junit = ('<testsuites><testsuite><testcase classname="tests.test_core" name="test_add"/>'
             '<testcase classname="tests.test_core" name="test_import"/>'
             f'<testcase classname="tests.test_core" name="{sent_name}"><failure message="x"/></testcase>'
             '</testsuite></testsuites>')

    class Proc:
        stdout, stderr = _docker_output(junit, 1, "1 failed, 2 passed in 0.1s"), ""

    monkeypatch.setattr(verify.subprocess, "run", lambda *a, **k: Proc())
    out = verify.run_side(env_dir, ENV, None)
    assert out["results"] == {"tests.test_core::test_add": True, "tests.test_core::test_import": True}


def test_docker_runs_with_process_and_privilege_limits():
    for flag in ("--network=none", "--pids-limit=256", "--cap-drop=ALL", "--security-opt=no-new-privileges"):
        assert flag in verify.DOCKER_LIMITS


# --- reward -----------------------------------------------------------------------------------

@pytest.fixture
def env_dir(tmp_path):
    d = tmp_path / "toy__toy-1"
    d.mkdir()
    (d / "env.json").write_text(json.dumps(ENV), encoding="utf-8")
    gold, test = verify.split_patch(DIFF)
    (d / "gold.patch").write_text(gold, encoding="utf-8")
    (d / "test.patch").write_text(test, encoding="utf-8")
    return d


def _fake(monkeypatch, before: dict, after: dict, image="sha256:abc"):
    def run_side(env_dir, env, candidate, executor=None):
        return {"results": dict(before if candidate is None else after), "seconds": 0.5}

    monkeypatch.setattr(verify, "run_side", run_side)
    monkeypatch.setattr(verify, "ensure_image", lambda env_dir, env: image)


def test_reward_rejects_a_patch_that_edits_test_files(env_dir, monkeypatch):
    monkeypatch.setattr(verify, "run_side", lambda *a: pytest.fail("must not run tests"))
    _, test = verify.split_patch(DIFF)
    out = verify.reward(env_dir, test)
    assert out["reward"] == 0 and "test files" in out["reason"]


def test_reward_rejects_conftest_edits(env_dir, monkeypatch):
    monkeypatch.setattr(verify, "run_side", lambda *a: pytest.fail("must not run tests"))
    patch = "diff --git a/conftest.py b/conftest.py\n--- a/conftest.py\n+++ b/conftest.py\n@@ -0,0 +1 @@\n+x=1\n"
    assert verify.reward(env_dir, patch)["reward"] == 0


def test_reward_rejects_a_test_file_under_a_non_ascii_folder(env_dir, monkeypatch):
    monkeypatch.setattr(verify, "run_side", lambda *a: pytest.fail("must not run tests"))
    gold, _ = verify.split_patch(DIFF)
    out = verify.reward(env_dir, gold + QUOTED)
    assert out["reward"] == 0 and "tests/\u0939/conftest.py" in out["reason"]


def test_reward_rejects_a_symlink(env_dir, monkeypatch):
    monkeypatch.setattr(verify, "run_side", lambda *a: pytest.fail("must not run tests"))
    patch = "diff --git a/pkg/link b/pkg/link\nnew file mode 120000\n--- /dev/null\n+++ b/pkg/link\n@@ -0,0 +1 @@\n+../tests\n"
    assert verify.reward(env_dir, patch)["reward"] == 0


def test_reward_is_one_only_when_every_listed_test_passes(env_dir, monkeypatch):
    gold, _ = verify.split_patch(DIFF)
    _fake(monkeypatch, {}, {"tests.test_core::test_add": True, "tests.test_core::test_import": True})
    assert verify.reward(env_dir, gold)["reward"] == 1
    _fake(monkeypatch, {}, {"tests.test_core::test_add": True, "tests.test_core::test_import": False})
    assert verify.reward(env_dir, gold)["reward"] == 0


def test_reward_counts_a_missing_test_as_failed(env_dir, monkeypatch):
    gold, _ = verify.split_patch(DIFF)
    _fake(monkeypatch, {}, {"tests.test_core::test_import": True})
    out = verify.reward(env_dir, gold)
    assert out["reward"] == 0 and out["failed"] == ["tests.test_core::test_add"]


def test_reward_is_zero_when_the_patch_does_not_apply(env_dir, monkeypatch):
    monkeypatch.setattr(verify, "ensure_image", lambda *a: "sha256:abc")
    monkeypatch.setattr(verify, "run_side", lambda *a: {"error": "candidate patch does not apply"})
    out = verify.reward(env_dir, "diff --git a/pkg/core.py b/pkg/core.py\n")
    assert out["reward"] == 0 and "apply" in out["reason"]


# --- gold check -------------------------------------------------------------------------------

def test_gold_check_passes_when_f2p_fails_before_and_everything_passes_after(env_dir, monkeypatch):
    _fake(monkeypatch, {"tests.test_core::test_add": False, "tests.test_core::test_import": True},
          {"tests.test_core::test_add": True, "tests.test_core::test_import": True})
    row = verify.gold_check(env_dir, runs=3)
    assert row["ok"] and row["fails_before"] == "3/3" and row["passes_after"] == "3/3"


def test_gold_check_fails_when_f2p_already_passes_before(env_dir, monkeypatch):
    _fake(monkeypatch, {"tests.test_core::test_add": True, "tests.test_core::test_import": True},
          {"tests.test_core::test_add": True, "tests.test_core::test_import": True})
    row = verify.gold_check(env_dir, runs=2)
    assert not row["ok"] and row["fails_before"] == "0/2"


def test_gold_check_fails_when_p2p_breaks_after_gold(env_dir, monkeypatch):
    _fake(monkeypatch, {"tests.test_core::test_add": False, "tests.test_core::test_import": True},
          {"tests.test_core::test_add": True, "tests.test_core::test_import": False})
    assert not verify.gold_check(env_dir, runs=2)["ok"]


def test_gold_check_catches_a_flaky_run(env_dir, monkeypatch):
    calls = {"n": 0}

    def run_side(env_dir, env, candidate, executor=None):
        calls["n"] += 1
        flaky_pass = calls["n"] != 3  # the second "before" run is different
        if candidate is None:
            return {"results": {"tests.test_core::test_add": False, "tests.test_core::test_import": flaky_pass},
                    "seconds": 0.1}
        return {"results": {"tests.test_core::test_add": True, "tests.test_core::test_import": True}, "seconds": 0.1}

    monkeypatch.setattr(verify, "run_side", run_side)
    monkeypatch.setattr(verify, "ensure_image", lambda *a: "sha256:abc")
    row = verify.gold_check(env_dir, runs=3)
    assert not row["ok"] and row["fails_before"] == "2/3"


def test_gold_check_needs_at_least_one_fail_to_pass_test(env_dir, monkeypatch):
    env = json.loads((env_dir / "env.json").read_text())
    env["FAIL_TO_PASS"] = []
    (env_dir / "env.json").write_text(json.dumps(env))
    _fake(monkeypatch, {"tests.test_core::test_import": True}, {"tests.test_core::test_import": True})
    assert not verify.gold_check(env_dir, runs=1)["ok"]


# --- make_env ---------------------------------------------------------------------------------

def test_flips_derives_f2p_p2p_and_drops_flaky_tests(env_dir, monkeypatch):
    seq = iter([
        {"results": {"a": False, "b": True, "c": True, "d": False}, "seconds": 0},   # before 1
        {"results": {"a": True, "b": True, "c": True, "d": False}, "seconds": 0},    # after 1
        {"results": {"a": False, "b": True, "c": False, "d": False}, "seconds": 0},  # before 2 (c flaky)
        {"results": {"a": True, "b": True, "c": True, "d": False, "e": True}, "seconds": 0},  # after 2
    ])
    monkeypatch.setattr(make_env.verify, "run_side", lambda *a: next(seq))
    f2p, p2p, notes = make_env.flips(env_dir, ENV, "gold")
    assert f2p == ["a"]          # fails before every time, passes after every time
    assert p2p == ["b"]          # passes on both sides every time
    assert notes["flaky_dropped"] == ["c", "e"]  # c flips before; e is missing from one after run
    assert notes["fail_after"] == ["d"]


def test_ai_marker_regex_flags_tools_but_not_ordinary_words():
    flagged = ["Generated with Claude Code", "co-authored with GitHub Copilot", "used ChatGPT", "AI-assisted fix",
               "Co-authored-by: Cursor Agent (cursor.sh)"]
    clean = ["fix the db cursor leak", "openapi schema", "Gemfile update", "codecs handling", "allm"]
    assert all(make_env.AI_MARKERS.search(t) for t in flagged)
    assert not any(make_env.AI_MARKERS.search(t) for t in clean)


@pytest.mark.parametrize("year,py", [(2018, "3.8"), (2020, "3.8"), (2021, "3.9"), (2022, "3.10")])
def test_python_for_merge_year(year, py):
    assert make_env.python_for(year) == py


def test_dockerfile_drops_git_history_and_runs_as_non_root():
    text = make_env.dockerfile("python:3.10-slim@sha256:" + "0" * 64, "o/r", "a" * 40, "RUN true")
    assert "git checkout --quiet " + "a" * 40 in text and "find . -name .git -prune -exec rm -rf {} +" in text
    assert text.rstrip().endswith("USER runner")
    assert "@sha256:" in text.splitlines()[1]


# --- import_pool ------------------------------------------------------------------------------

def test_import_pool_filters_rows():
    bench = {"o/in-bench"}
    row = {"instance_id": "o__r-1", "repo": "o/r", "created_at": "2021-05-01T00:00:00", "license_name": "MIT License",
           "FAIL_TO_PASS": ["t1"], "PASS_TO_PASS": ["t2"], "patch": "x", "problem_statement": "Bug in r"}
    assert import_pool.keep_row(row, bench) == (True, "")
    assert import_pool.keep_row({**row, "created_at": "2023-01-02"}, bench)[0] is False
    assert import_pool.keep_row({**row, "repo": "O/In-Bench"}, bench)[0] is False
    assert import_pool.keep_row({**row, "license_name": None}, bench)[0] is False
    assert import_pool.keep_row({**row, "license_name": "GNU GPL v3"}, bench)[0] is False
    assert import_pool.keep_row({**row, "FAIL_TO_PASS": []}, bench)[0] is False
    assert import_pool.keep_row({**row, "problem_statement": "Generated with Claude Code"}, bench)[0] is False


@parametrize("value", [None, "", "not a date", "2021-13-40", "21-05-01", 0])
def test_import_pool_rejects_missing_or_invalid_dates(value):
    row = {"instance_id": "o__r-1", "repo": "o/r", "created_at": value, "license_name": "MIT License",
           "FAIL_TO_PASS": ["t1"], "PASS_TO_PASS": ["t2"], "patch": "x", "problem_statement": "Bug in r"}
    ok, why = import_pool.keep_row(row, set())
    assert ok is False and why.startswith("missing or invalid created_at")


@parametrize("value, expected", [
    ("2020-10-12 13:21:50", "2020-10-12"), ("2022-12-31T23:59:59Z", "2022-12-31"), ("2021-05-01", "2021-05-01"),
])
def test_parse_date_reads_the_formats_in_use(value, expected):
    assert import_pool.parse_date(value).isoformat() == expected


def test_read_rows_refuses_a_file_whose_sha256_differs(tmp_path, monkeypatch):
    (tmp_path / "test-00000-of-00001.parquet").write_bytes(b"not the pinned bytes")
    monkeypatch.setattr(import_pool, "split_files", lambda *a: [
        {"path": "data/test-00000-of-00001.parquet", "sha256": "0" * 64, "size": 20}])
    with pytest.raises(SystemExit, match="does not match the Hub record"):
        import_pool.read_rows("o/d", "test", ["instance_id"], "a" * 40, tmp_path)


def test_make_env_date_check_rejects_late_or_missing_dates():
    pr = {"merged_at": "2022-08-16T13:50:38Z"}
    ok_issue = {"number": 1, "createdAt": "2020-06-25T20:09:56Z"}
    assert make_env.check_dates(pr, [ok_issue]) == []
    assert make_env.check_dates({"merged_at": "2023-01-01T00:00:00Z"}, [ok_issue])
    assert make_env.check_dates({"merged_at": None}, [ok_issue])
    assert make_env.check_dates(pr, [{"number": 2, "createdAt": "2023-02-01T00:00:00Z"}])
    assert make_env.check_dates(pr, [{"number": 3, "createdAt": None}])


@parametrize("source, junit", [
    ("tests/test_regressions.py::test_issue562_tzcasts", "tests.test_regressions::test_issue562_tzcasts"),
    ("tests/test_types.py::TestFileType::test_guess_jpeg", "tests.test_types.TestFileType::test_guess_jpeg"),
    ("test_base58.py::test_check_str", "test_base58::test_check_str"),
    ("tests/test_objects.py::test_merge_with[case0-expected0]", "tests.test_objects::test_merge_with[case0-expected0]"),
])
def test_rebench_test_ids_match_junit_ids(source, junit):
    assert rebench_pilot.norm_test_id(source) == junit


def test_rebench_side_check_needs_every_listed_test_reported():
    env = {"FAIL_TO_PASS": ["m::f"], "PASS_TO_PASS": ["m::p"]}
    assert rebench_pilot.side_check(env, {"results": {"m::f": False, "m::p": True}}, after=False) == []
    assert rebench_pilot.side_check(env, {"results": {"m::f": True, "m::p": True}}, after=True) == []
    assert "missing" in rebench_pilot.side_check(env, {"results": {"m::p": True}}, after=False)[0]
    assert "collection error" in rebench_pilot.side_check(
        env, {"results": {"::tests.test_x": False, "m::f": False, "m::p": True}}, after=False)[0]
    assert rebench_pilot.side_check(env, {"error": "timeout"}, after=True) == ["timeout"]


# --- the shipped environments -----------------------------------------------------------------

ENV_DIRS = sorted(p.parent for p in HERE.glob("*/env.json"))


@pytest.mark.parametrize("env_dir", ENV_DIRS, ids=[d.name for d in ENV_DIRS])
def test_shipped_env_is_complete_and_human_sourced(env_dir):
    env = json.loads((env_dir / "env.json").read_text(encoding="utf-8"))
    for f in ("Dockerfile", "gold.patch", "test.patch", "issue.md", "requirements.lock"):
        assert (env_dir / f).is_file(), f
    assert env["instance_id"] == env_dir.name
    assert len(env["base_commit"]) == 40 and env["base_commit"] in (env_dir / "Dockerfile").read_text()
    assert env["FAIL_TO_PASS"] and not set(env["FAIL_TO_PASS"]) & set(env["PASS_TO_PASS"])
    assert env["provenance"]["generator"] == "none"
    assert env["merged_at"] < "2023-01-01"
    assert env["licence"] in import_pool.PERMISSIVE_SPDX
    gold_paths = verify.patch_paths((env_dir / "gold.patch").read_text(encoding="utf-8"))
    test_paths = verify.patch_paths((env_dir / "test.patch").read_text(encoding="utf-8"))
    assert gold_paths and test_paths and not set(gold_paths) & set(test_paths)
    assert all(verify.is_test_path(p) for p in test_paths)
    assert not any(verify.is_test_path(p) for p in gold_paths)
    assert "@sha256:" in env["base_image"]
    assert env["quality_verdict"] in ("keep", "keep-flagged")
    assert (env["quality_verdict"] == "keep-flagged") == bool(env.get("quality_note"))


# --- the SWE-rebench pilot environments --------------------------------------------------------

PILOT_DIRS = sorted(p.parent for p in (HERE / "rebench-pilot").glob("*/env.json"))


def test_pilot_has_five_environments():
    assert len(PILOT_DIRS) == 5


@parametrize("env_dir", PILOT_DIRS, ids=[d.name for d in PILOT_DIRS])
def test_pilot_env_is_pinned_human_sourced_and_admitted(env_dir):
    env = json.loads((env_dir / "env.json").read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "rebench-pilot" / "source_manifest.json").read_text(encoding="utf-8"))
    for f in ("Dockerfile", "gold.patch", "test.patch", "issue.md", "requirements.lock", "admission.json"):
        assert (env_dir / f).is_file(), f
    assert env["instance_id"] == env_dir.name
    assert len(env["base_commit"]) == 40 and env["base_commit"] in (env_dir / "Dockerfile").read_text()
    assert len(env["pr_head_commit"]) == 40 and len(env["merge_commit"]) == 40
    assert env["provenance"]["generator"] == "none" and "no AI-tool markers" in env["provenance"]["ai_marker_scan"]
    assert env["merged_at"] < "2023-01-01" and env["issue_created_at"]
    assert all(d < "2023-01-01" for d in env["issue_created_at"])
    assert env["licence"] in import_pool.PERMISSIVE_SPDX
    assert env["repo"].lower() not in import_pool.benchmark_repos()
    assert "@sha256:" in env["base_image"]
    assert env["FAIL_TO_PASS"] and not set(env["FAIL_TO_PASS"]) & set(env["PASS_TO_PASS"])
    assert env["instance_id"] in {s["instance_id"].lower() for s in manifest["selected"]}
    assert len(manifest["revision"]) == 40 and all(len(f["sha256"]) == 64 for f in manifest["files"])
    adm = json.loads((env_dir / "admission.json").read_text(encoding="utf-8"))
    assert adm["admitted"] is True and adm["source"]["found"] is True
    for plat in adm["platforms"]:
        assert plat["no_patch_fails"] == plat["gold_passes"] == f"{plat['runs']}/{plat['runs']}"
        assert plat["runs"] >= 5
        assert plat["negative_control"]["reward"]["reward"] == 0 and plat["gold_reward"]["reward"] == 1
        iso = plat["isolation_probe"]
        assert iso["ok"] and iso["interfaces_up"] == ["lo"] and iso["ipv4_routes"] == 0
        assert iso["tcp_connect"].startswith("failed") and iso["dns"].startswith("failed") and iso["commits"] == 1
        assert "--network=none" in plat["docker_flags"]


def test_flagged_envs_match_the_review():
    flagged = {d.name for d in ENV_DIRS
               if json.loads((d / "env.json").read_text(encoding="utf-8"))["quality_verdict"] == "keep-flagged"}
    assert flagged == {"python-poetry__tomlkit-221", "python-poetry__tomlkit-236", "python-validators__validators-191",
                       "scrapy__w3lib-136", "scrapy__w3lib-196"}


def test_docker_build_retries_without_progress_on_legacy_builder(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "--progress=plain" in cmd:
            return verify.subprocess.CompletedProcess(cmd, 125, "", "unknown flag: --progress\n")
        return verify.subprocess.CompletedProcess(cmd, 0, "Successfully built abc123\n", "")

    monkeypatch.setattr(verify.subprocess, "run", fake_run)
    proc = verify._docker_build(["-t", "g10-swe/test:v1", "/tmp/ctx"])
    assert proc.returncode == 0
    assert calls == [
        ["docker", "build", "--progress=plain", "-t", "g10-swe/test:v1", "/tmp/ctx"],
        ["docker", "build", "-t", "g10-swe/test:v1", "/tmp/ctx"],
    ]


def test_docker_build_does_not_retry_on_real_build_error(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return verify.subprocess.CompletedProcess(cmd, 1, "", "failed to solve: syntax error\n")

    monkeypatch.setattr(verify.subprocess, "run", fake_run)
    proc = verify._docker_build(["-t", "g10-swe/test:v1", "/tmp/ctx"])
    assert proc.returncode == 1
    assert len(calls) == 1

