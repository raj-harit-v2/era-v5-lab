"""Tests for jsts_verifier.py: the reference and a wrong answer for every task, the cheating cases, the lint.

Run:  python -m pytest teams/10-post-training/rl/jsts/test_jsts_verifier.py -q -p no:cacheprovider
Scoring needs Docker and the image g10-jsts-rl:1 (docker build -f rl/jsts/jsts.Dockerfile, see README.md); those tests
are skipped, with the reason, when either is missing. The extraction tests need neither.

The cheating candidates below are FIXTURES written to attack the verifier; they are not task data or training data.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_jsts_verifier", HERE / "jsts_verifier.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize

TASK_DIRS = sorted(p.parent for p in v.TASKS.glob("*/*/task.json"))


def _docker_image_ok() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "image", "inspect", v.IMAGE], capture_output=True).returncode == 0


needs_image = pytest.mark.skipif(not _docker_image_ok(), reason=f"docker or the image {v.IMAGE} is missing")


def meta(d: Path) -> dict:
    return json.loads((d / "task.json").read_text(encoding="utf-8"))


def fence(d: Path, code: str) -> str:
    return "```" + {"js": "javascript", "ts": "typescript"}[meta(d)["language"]] + "\n" + code + "\n```"


# --- extraction (no Docker) --------------------------------------------------------------------

def test_the_last_matching_block_counts():
    text = "```js\nconst a = 1;\n```\nand better:\n```javascript\nconst b = 2;\n```"
    assert v.extract_code(text, "js") == ("const b = 2;", "ok")


@parametrize("text, why", [
    ("no code here", "no code block"),
    ("```python\nx = 1\n```", "no code block"),
    ("```js\n\n```", "empty code block"),
    ("<|think|>\n```js\nx\n```", "think span not closed"),
])
def test_bad_replies_have_no_code(text, why):
    assert v.extract_code(text, "js") == (None, why)


def test_code_inside_the_think_span_does_not_count():
    assert v.extract_code("<|think|>```js\nx\n```<|/think|>done", "js")[0] is None


def test_a_ts_task_does_not_read_a_js_fence_and_the_reverse():
    assert v.extract_code("```javascript\nx\n```", "ts")[0] is None
    assert v.extract_code("```ts\nx\n```", "js")[0] is None


def test_too_long_code_is_refused():
    assert v.extract_code("```js\n" + "a" * (v.MAX_CODE_CHARS + 1) + "\n```", "js") == (None, "code too long")


# --- records (no Docker) -----------------------------------------------------------------------

def test_there_are_js_and_ts_tasks_from_a_human_source():
    langs = {meta(d)["language"] for d in TASK_DIRS}
    assert langs == {"js", "ts"}
    for d in TASK_DIRS:
        m = meta(d)
        assert m["licence"] == "MIT" and m["generator"].startswith("none")
        assert m["source"].startswith("exercism/") and m["first_added"] <= "2022-12-31"
        assert m["expected_tests"] >= 2
        assert d.parent.name == m["language"] and d.name == m["id"]


@parametrize("d", TASK_DIRS, ids=lambda d: f"{d.parent.name}/{d.name}")
def test_prompt_never_holds_the_reference_or_a_test_body(d):
    m = meta(d)
    prompt = (d / "prompt.md").read_text(encoding="utf-8")
    ref = (d / "hidden" / m["reference_file"]).read_text(encoding="utf-8").strip()
    assert ref not in prompt
    assert "expect(" not in prompt
    assert not (d / "hidden" / m["spec_file"]).read_text().count("xtest(")


@parametrize("d", TASK_DIRS, ids=lambda d: f"{d.parent.name}/{d.name}")
def test_the_stub_in_the_prompt_is_the_wrong_answer(d):
    good, bad = v.known_outputs(d)
    assert good != bad and (d / "stub" / meta(d)["solution_file"]).read_text().strip() in (d / "prompt.md").read_text()


# --- scoring in the sandbox (Docker) -----------------------------------------------------------

@needs_image
@parametrize("d", TASK_DIRS, ids=lambda d: f"{d.parent.name}/{d.name}")
def test_reference_scores_one_stub_scores_zero_and_the_lint_passes(d):
    assert v.check_task(d) == {"task_id": d.name, "language": meta(d)["language"], "ok": True, "problems": []}


def _one(language: str) -> Path:
    return next(d for d in TASK_DIRS if meta(d)["language"] == language)


@needs_image
@parametrize("language", ["js", "ts"])
@parametrize("label, body", [
    ("empty module", ""),
    ("syntax error", "export const = ;"),
    ("throws on import", "throw new Error('boom');"),
    ("exits with code 0 at import", "process.exit(0);"),
    ("forges a passing report", "process.on('exit', () => require('fs').writeFileSync(process.env.X || '/tmp/x', '{}'));"),
    ("loops forever", "while (true) {}"),
])
def test_cheating_or_broken_modules_score_zero(language, label, body):
    d = _one(language)
    code = body or "// nothing"
    out = v.reward(d, fence(d, code))
    assert out["reward"] == 0, (label, out)


@needs_image
def test_a_module_that_fakes_jest_globals_cannot_pass():
    d = _one("js")
    code = ("global.expect = () => new Proxy({}, {get: () => () => {}});\n"
            "global.test = () => {}; global.it = () => {}; global.describe = () => {};\n" + "export {};")
    assert v.reward(d, fence(d, code))["reward"] == 0


@needs_image
def test_a_wrong_but_plausible_module_scores_zero_for_every_task():
    for d in TASK_DIRS:
        _, bad = v.known_outputs(d)
        assert v.reward(d, bad)["reward"] == 0


@needs_image
def test_one_tasks_reference_does_not_score_on_another_task():
    a, b = _one("js"), [d for d in TASK_DIRS if meta(d)["language"] == "js"][1]
    good, _ = v.known_outputs(a)
    assert v.reward(b, good)["reward"] == 0


@needs_image
def test_the_reply_never_contains_the_hidden_tests():
    d = _one("js")
    _, bad = v.known_outputs(d)
    out = json.dumps(v.reward(d, bad))
    assert "expect(" not in out and "toEqual" not in out


def test_cli_reward_without_a_code_block_prints_zero(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("no code")
    proc = subprocess.run(["python3", str(HERE / "jsts_verifier.py"), "--reward", str(TASK_DIRS[0]), str(f)],
                          capture_output=True, text=True)
    assert proc.returncode == 0 and json.loads(proc.stdout)["reward"] == 0
