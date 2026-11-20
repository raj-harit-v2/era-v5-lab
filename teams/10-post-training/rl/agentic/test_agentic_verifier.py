"""Tests for agentic_verifier.py: a correct and a wrong answer for every task, the malformed and cheating cases, the lint.

Run:  python -m pytest teams/10-post-training/rl/agentic/test_agentic_verifier.py -q -p no:cacheprovider
Parser tests need no Docker. The tests that score a command or a patch run the SWE env image (built from its
Dockerfile when absent) and are skipped when `docker` is not usable.

The wrong patches below are FIXTURES derived from the human gold patch of swe-envs/python-poetry__tomlkit-236 (one
edit each). They only test the verifier and are not task data or training data.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_agentic_verifier", HERE / "agentic_verifier.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize

TASK_DIRS = sorted(p.parent for p in v.TASKS.glob("*/task.json"))
COMMAND_TASKS = [p for p in TASK_DIRS if json.loads((p / "task.json").read_text())["mode"] == "command"]
THINK = "<|think|>\nfind the test file for the issue\n<|/think|>\n"
TOMLKIT = v.SWE_ENVS / "python-poetry__tomlkit-236"
GOLD = (TOMLKIT / "gold.patch").read_text(encoding="utf-8")


def _docker_ok() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


needs_docker = pytest.mark.skipif(not _docker_ok(), reason="docker is not available")


def task(name: str) -> Path:
    return v.TASKS / name


def cmd(line: str) -> str:
    return f"Run the tests.\n```bash\n{line}\n```\n"


def score(name: str, completion: str) -> dict:
    return v.reward(task(name), completion)


# --- parser (no Docker) ----------------------------------------------------------------------------

@parametrize("line", [
    "pytest tests/test_timeutils.py",
    "python -m pytest tests/test_timeutils.py",
    "python3 -m pytest -q tests/test_timeutils.py",
    "$ python -m pytest -v -s --tb=short tests/test_timeutils.py",
    "python -m pytest -p no:cacheprovider -o addopts= -q tests/test_timeutils.py",
    "pytest tests/test_timeutils.py::test_daterange_years",
])
def test_parser_accepts_pytest_commands(line):
    args, why = v.parse_command(line)
    assert args is not None, why


@parametrize("line", [
    "ls tests",
    "cat tests/test_timeutils.py",
    "python -c 'print(1)'",
    "python -m pytest tests/test_timeutils.py && echo done",
    "python -m pytest tests/test_timeutils.py; rm -rf /",
    "python -m pytest tests/test_timeutils.py | head",
    "python -m pytest $(ls tests)",
    "python -m pytest `ls`",
    "python -m pytest tests/*.py",
    "python -m pytest 'tests/test_timeutils.py'",
    "python -m pytest tests/test_timeutils.py > out.txt",
    "sed -i s/assert/pass/ tests/test_timeutils.py",
    "echo hi > tests/test_timeutils.py",
    "cd /repo && python -m pytest tests/test_timeutils.py",
    "FOO=1 python -m pytest tests/test_timeutils.py",
    "python -m pytest ../other/test_x.py",
    "python -m pytest /etc/passwd",
    "python -m pytest -k daterange tests/test_timeutils.py",
    "python -m pytest -x tests/test_timeutils.py",
    "python -m pytest --co tests/test_timeutils.py",
    "python -m pytest --junitxml=/repo/tests/x.xml tests/test_timeutils.py",
    "python -m pytest -p evil_plugin tests/test_timeutils.py",
    "python -m pytest -c /tmp/evil.ini tests/test_timeutils.py",
    "python -m pytest --rootdir=/tmp tests/test_timeutils.py",
    "python -m pytest --pyargs os",
    "python -m pip install requests",
    "x" * 400,
    "",
])
def test_parser_rejects_everything_else(line):
    args, _ = v.parse_command(line)
    assert args is None


def test_two_lines_are_not_one_command():
    assert v.parse_command("pytest tests/a.py\npytest tests/b.py")[0] is None


# --- output rules (no Docker) -----------------------------------------------------------------------

def test_no_block_scores_zero_even_if_the_right_command_is_written_in_prose():
    out = score("run_tests_boltons-302", "Just run python -m pytest tests/test_timeutils.py please.")
    assert out["reward"] == 0 and out["reason"] == "no fenced block"


def test_two_blocks_score_zero():
    text = cmd("pytest tests/test_timeutils.py") + cmd("pytest tests/test_iterutils.py")
    assert score("run_tests_boltons-302", text)["reason"] == "more than one fenced block"


def test_a_diff_block_for_a_command_task_scores_zero():
    out = score("run_tests_boltons-302", "```diff\n" + v.NOOP_PATCH + "```")
    assert out["reward"] == 0 and out["reason"].startswith("wrong action type")


def test_a_command_block_for_a_patch_task_scores_zero():
    out = score("patch_tomlkit-236", cmd("pytest tests/test_write.py"))
    assert out["reward"] == 0 and out["reason"].startswith("wrong action type")


def test_command_next_to_a_patch_block_scores_zero():
    assert score("run_tests_boltons-302", cmd("pytest tests/test_timeutils.py") + "```diff\nx\n```")["reward"] == 0


def test_unclosed_think_span_has_no_answer():
    out = score("run_tests_boltons-302", "<|think|>\n" + cmd("pytest tests/test_timeutils.py"))
    assert out["reason"] == "think span not closed"


def test_the_command_inside_the_think_span_does_not_count():
    text = "<|think|>\n" + cmd("pytest tests/test_timeutils.py") + "<|/think|>\nI am not sure."
    assert score("run_tests_boltons-302", text)["reward"] == 0


@parametrize("name", [p.name for p in COMMAND_TASKS])
def test_a_wrong_command_that_never_reaches_docker_scores_zero(name):
    assert score(name, cmd("ls tests"))["reward"] == 0


# --- lint and registry (no Docker for the pure checks) ----------------------------------------------

@parametrize("name", [p.name for p in TASK_DIRS])
def test_prompt_never_holds_the_hidden_values(name):
    prompt = (task(name) / "prompt.md").read_text(encoding="utf-8")
    hidden = task(name) / "hidden" / "expected.json"
    if hidden.exists():
        data = json.loads(hidden.read_text(encoding="utf-8"))
        assert data["recorded_command"] not in prompt
        assert not any(t in prompt for t in data["expected_tests"])


@parametrize("name", [p.name for p in TASK_DIRS])
def test_task_record_names_its_human_source_and_no_generator(name):
    meta = json.loads((task(name) / "task.json").read_text(encoding="utf-8"))
    assert meta["mode"] in v.MODES and meta["id"] == name
    assert "generator: none" in meta["source"]
    assert (v.SWE_ENVS / meta["swe_env"] / "env.json").is_file()
    if meta["mode"] == "patch":
        assert meta["pool_overlap"] == f"swe/{meta['swe_env']}"


def test_there_are_at_least_three_command_tasks_from_distinct_real_environments():
    envs = {json.loads((p / "task.json").read_text())["swe_env"] for p in COMMAND_TASKS}
    assert len(envs) >= 3


def test_reward_module_registers_agentic_and_lists_the_ids():
    spec2 = importlib.util.spec_from_file_location("g10_reward_for_agentic", HERE.parent / "reward.py")
    r = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(r)
    ids = r.list_envs()
    assert {f"agentic/{p.name}" for p in TASK_DIRS} <= set(ids)
    good, bad = r.known_outputs(f"agentic/{COMMAND_TASKS[0].name}")
    assert "```bash" in good and r.reward(f"agentic/{COMMAND_TASKS[0].name}", bad)[0] == 0.0


# --- scoring in the env image (Docker) --------------------------------------------------------------

@needs_docker
@parametrize("name", [p.name for p in TASK_DIRS])
def test_the_recorded_answer_scores_one_and_the_lint_passes(name):
    row = v.check_task(task(name))
    assert row["ok"], row


@needs_docker
@parametrize("line", [
    "pytest tests/test_timeutils.py",
    "python -m pytest -v tests/test_timeutils.py",
    "python3 -m pytest -q -s --tb=short tests/test_timeutils.py",
])
def test_every_spelling_of_the_right_command_scores_one(line):
    out = score("run_tests_boltons-302", THINK + cmd(line))
    assert out["reward"] == 1, out


@needs_docker
@parametrize("line", [
    "pytest tests/test_iterutils.py",                  # the wrong test file
    "pytest tests/test_timeutils.py::test_daterange_years",  # a subset of the right file
    "pytest",                                          # the whole suite (cheap trick: it also contains the failure)
    "pytest tests",                                    # the whole folder
    "pytest tests/test_timeutils.py tests/test_iterutils.py",  # the right file plus another
    "pytest tests/test_missing.py",                    # a file that does not exist: no report
])
def test_a_command_that_runs_a_different_set_of_tests_scores_zero(line):
    out = score("run_tests_boltons-302", cmd(line))
    assert out["reward"] == 0, out


@needs_docker
def test_the_whole_suite_trick_scores_zero_on_a_small_repo_too():
    out = score("run_tests_validators-191", cmd("pytest"))
    assert out["reward"] == 0, out


@needs_docker
@parametrize("line", [
    "sed -i s/assert/pass/ tests/test_timeutils.py",
    "python -c open('tests/test_timeutils.py','w')",
    "echo pass > tests/test_timeutils.py",
    "pytest tests/test_timeutils.py --junitxml=/repo/tests/test_timeutils.py",
    "pytest -p no:cacheprovider -p evil tests/test_timeutils.py",
])
def test_a_tampering_command_scores_zero(line):
    assert score("run_tests_boltons-302", cmd(line))["reward"] == 0


@needs_docker
def test_the_expected_answer_for_one_task_does_not_score_on_another():
    out = score("run_tests_validators-191", cmd("pytest tests/test_timeutils.py"))
    assert out["reward"] == 0


@needs_docker
def test_a_command_run_never_changes_the_files_the_next_run_sees():
    first = score("run_tests_tomlkit-236", cmd("pytest tests/test_write.py"))
    second = score("run_tests_tomlkit-236", cmd("pytest tests/test_write.py"))
    assert first["reward"] == second["reward"] == 1


# --- patch mode (Docker) ----------------------------------------------------------------------------

def _diff(text: str) -> str:
    return "```diff\n" + text.rstrip("\n") + "\n```"


@needs_docker
def test_patch_gold_scores_one():
    assert score("patch_tomlkit-236", _diff(GOLD))["reward"] == 1


@needs_docker
def test_patch_noop_scores_zero():
    assert score("patch_tomlkit-236", _diff(v.NOOP_PATCH))["reward"] == 0


@needs_docker
def test_patch_that_applies_but_does_not_fix_scores_zero():
    wrong = GOLD.replace("(_parent is None or isinstance(_parent, Table))", "True")
    assert wrong != GOLD
    out = score("patch_tomlkit-236", _diff(wrong))
    assert out["reward"] == 0, out


@needs_docker
def test_patch_that_edits_a_test_file_scores_zero():
    tamper = GOLD + ("diff --git a/tests/conftest.py b/tests/conftest.py\nnew file mode 100644\n"
                     "index 0000000..e69de29\n--- /dev/null\n+++ b/tests/conftest.py\n@@ -0,0 +1 @@\n+# hook\n")
    out = score("patch_tomlkit-236", _diff(tamper))
    assert out["reward"] == 0 and "test files" in out["reason"]


# Attack fixtures from the independent attack test of 18 Nov 2026 (job W): source patches that rewrite pytest's own
# reports from inside the test process. They are FIXTURES (each starts "ATTACK FIXTURE, never training data"), not data.
FIXTURES = HERE / "attack_fixtures"


@needs_docker
@parametrize("label,fixture,control", [
    ("P1 rewrites TestReport, spares the old sentinel by its name pattern", "P1_report_rewrite.patch", False),
    ("P1b spares the tests defined in the untracked file named on the command line", "P1b_adaptive.patch", False),
    ("P1c control: P1 without sparing, caught by the sentinel check", "P1_report_rewrite.patch", True),
])
def test_report_forging_patches_score_zero(label, fixture, control):
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    if control:
        text = text.replace("if not _sent.search(item.name):", "if True:")
        assert "if True:" in text
    out = score("patch_tomlkit-236", _diff(text))
    assert out["reward"] == 0, (label, out)
    assert "sentinel" in out["reason"] or "report integrity" in out["reason"], (label, out)


@parametrize("path", ["pytest.py", "_pytest/__init__.py", "sitecustomize.py", "x.pth", "json.py"])
def test_a_patch_that_shadows_the_test_runner_scores_zero_before_docker(path):
    patch = (f"diff --git a/{path} b/{path}\nnew file mode 100644\nindex 0000000..e69de29\n--- /dev/null\n+++ b/{path}\n"
             "@@ -0,0 +1 @@\n+x = 1\n")
    out = score("patch_tomlkit-236", _diff(GOLD + patch))
    assert out["reward"] == 0 and "shadows the test runner" in out["reason"], out


def test_patch_that_is_not_a_diff_scores_zero_without_docker_when_unfenced():
    assert score("patch_tomlkit-236", GOLD)["reward"] == 0


# --- command line ---------------------------------------------------------------------------------

def test_cli_reward_prints_one_json_line(tmp_path):
    f = tmp_path / "completion.txt"
    f.write_text("no block here", encoding="utf-8")
    proc = subprocess.run(["python3", str(HERE / "agentic_verifier.py"), "--reward",
                           str(task("run_tests_boltons-302")), str(f)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["reward"] == 0
