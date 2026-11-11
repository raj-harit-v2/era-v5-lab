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
    sentinel = script.index("> test_abc123.py")
    assert apply_candidate < restore < apply_tests < sentinel
    assert "timeout 60 python -m pytest -q tests/test_core.py test_abc123.py --junitxml=/tmp/g10_abc123.out" in script


def test_container_script_adds_a_go_sentinel_in_the_test_package():
    env = {**ENV, "language": "go", "test_files": ["pkg/version_test.go"], "test_cmd": "go test -json -count=1 ./pkg"}
    script = verify.container_script(env, with_candidate=True, token="abc123")
    assert "pkg/zabc123_test.go" in script and "func TestZabc123(t *testing.T)" in script
    assert "sed -n" in script and "pkg/version_test.go" in script


def test_container_script_without_candidate_skips_candidate_apply():
    assert "candidate.patch" not in verify.container_script(ENV, with_candidate=False)


# --- report integrity (PR #27 review, point 1) -------------------------------------------------

SENT = verify.sentinel(ENV, "abc123")
HONEST = {"tests.test_core::test_add": True, "tests.test_core::test_import": True, "test_abc123::test_abc123": False}


def test_check_report_accepts_an_honest_run():
    assert verify.check_report(HONEST, SENT, 1, "1 failed, 2 passed in 0.1s", "python") is None


@pytest.mark.parametrize("results,exit_code,summary,problem", [
    ({k: True for k in HONEST if "abc123" not in k}, 1, "1 failed, 2 passed in 0.1s", "missing"),  # forged file
    ({**HONEST, "test_abc123::test_abc123": True}, 1, "3 passed in 0.1s", "reported as passed"),  # flipped all
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
    junit = ('<testsuites><testsuite><testcase classname="tests.test_core" name="test_add"/>'
             '<testcase classname="tests.test_core" name="test_import"/>'
             '<testcase classname="test_abc123000000" name="test_abc123000000"><failure message="x"/></testcase>'
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


def test_flagged_envs_match_the_review():
    flagged = {d.name for d in ENV_DIRS
               if json.loads((d / "env.json").read_text(encoding="utf-8"))["quality_verdict"] == "keep-flagged"}
    assert flagged == {"python-poetry__tomlkit-221", "python-poetry__tomlkit-236", "python-validators__validators-191",
                       "scrapy__w3lib-136", "scrapy__w3lib-196"}
