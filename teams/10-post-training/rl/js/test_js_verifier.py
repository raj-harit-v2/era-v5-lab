"""Tests for js_verifier.py: correct and wrong answers for every JS task, plus cheating cases.

Run:  python -m pytest teams/10-post-training/rl/js/test_js_verifier.py -q -p no:cacheprovider
`process` tests need `node` (26+) on PATH. `docker` tests run only when docker and the image from
js.Dockerfile (G10_JS_IMAGE, default g10-js-rl:1) are present:
  docker build -f teams/10-post-training/rl/js/js.Dockerfile -t g10-js-rl:1 teams/10-post-training/rl/js
"""
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parent.parent))
import js_verifier as jv  # noqa: E402

HERE = Path(__file__).resolve().parent
TASKS = sorted(p for p in (HERE / "tasks").iterdir() if p.is_dir())
SNAKE = HERE / "tasks" / "camel_to_snake"

parametrize = pytest.mark.parametrize
skipif = pytest.mark.skipif


def _node_ready() -> bool:
    if not shutil.which("node"):
        return False
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5).stdout.strip()
        return int(out.lstrip("v").split(".")[0]) >= 26
    except Exception:
        return False


def _docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(
            ["docker", "image", "inspect", jv.JS_IMAGE], capture_output=True, timeout=20
        ).returncode == 0
    except Exception:
        return False


needs_node = pytest.mark.skipif(not _node_ready(), reason="node is not installed")
SANDBOXES = [
    pytest.param("process", marks=needs_node),
    pytest.param("docker", marks=skipif(not _docker_ready(), reason="docker or the JS image is missing")),
]


def fence(code: str, label: str = "javascript") -> str:
    return "Here is my answer.\n```" + label + "\n" + textwrap.dedent(code).strip() + "\n```\n"


# Wrong answer: correct conversion but missing empty-string guard and leading-underscore removal.
WRONG = {
    "camel_to_snake": textwrap.dedent("""\
        function camelToSnake(s) {
          let result = '';
          for (let i = 0; i < s.length; i++) {
            const ch = s[i];
            if (ch >= 'A' && ch <= 'Z') result += '_' + ch.toLowerCase();
            else result += ch;
          }
          return result;
        }
    """),
}

CORRECT_SNAKE = (SNAKE / "reference.js").read_text(encoding="utf-8")

# Patched runner that reads cases.json normally but then simulates EPERM on unlinkSync.
# Used by deletion-failure regression tests to avoid relying on OS permission tricks.
_RUNNER_UNLINK_FAILS = textwrap.dedent("""\
    'use strict';
    const fs = require('fs');
    const path = require('path');
    const {isMainThread} = require('worker_threads');
    if (!isMainThread) { process.exit(2); }
    const [workdir] = process.argv.slice(2);
    if (!workdir) { process.exit(2); }
    try { JSON.parse(fs.readFileSync(path.join(workdir,'cases.json'),'utf8')); } catch(_){ process.exit(2); }
    // Simulate: unlinkSync throws (EPERM, EACCES, or similar) — the fail-closed path fires.
    try { throw Object.assign(new Error('simulated EPERM'),{code:'EPERM'}); } catch(_){ process.exit(2); }
""")


def score(code: str, task: Path = SNAKE, sandbox: str = "process", label: str = "javascript") -> dict:
    return jv.reward(task, fence(code, label), sandbox)


# --- every task: reference scores 1, wrong answer scores 0 -------------------------------------------

@parametrize("sandbox", SANDBOXES)
@parametrize("task", TASKS, ids=lambda p: p.name)
def test_reference_scores_one(task, sandbox):
    res = jv.reward(task, fence((task / "reference.js").read_text(encoding="utf-8")), sandbox)
    assert res["reward"] == 1, res


@parametrize("sandbox", SANDBOXES)
@parametrize("task", TASKS, ids=lambda p: p.name)
def test_wrong_answer_scores_zero_and_hides_which_hidden_test_failed(task, sandbox):
    res = jv.reward(task, fence(WRONG[task.name]), sandbox)
    assert res["reward"] == 0
    assert res["passed"] < res["total"]
    assert "expected" not in json.dumps(res).lower()


def test_every_task_has_a_wrong_answer_in_this_file():
    assert {t.name for t in TASKS} == set(WRONG)


@needs_node
@parametrize("task", TASKS, ids=lambda p: p.name)
def test_task_passes_the_lint(task):
    assert jv.check_task(task) == []


# --- fence parsing -------------------------------------------------------------------------------

@needs_node
def test_no_code_block_scores_zero():
    assert score("// answer is 42", label="")["reward"] == 0
    assert jv.reward(SNAKE, "I think the answer is 42.")["reward"] == 0


@needs_node
def test_a_python_block_is_not_js():
    assert score(CORRECT_SNAKE, label="python")["reward"] == 0


@needs_node
def test_unlabelled_block_counts_and_last_js_block_is_used():
    text = fence(WRONG["camel_to_snake"]) + "\nOutput:\n```text\nok\n```\n\nFinal:\n" + fence(CORRECT_SNAKE, "")
    assert jv.reward(SNAKE, text)["reward"] == 1


@needs_node
def test_mjs_label_counts():
    assert score(CORRECT_SNAKE, label="mjs")["reward"] == 1


@needs_node
def test_unclosed_block_scores_zero():
    assert jv.reward(SNAKE, "```javascript\n" + CORRECT_SNAKE)["reward"] == 0


def test_oversized_and_nul_code_are_refused():
    assert jv.reward(SNAKE, "```javascript\n" + "// x\n" * 10000 + "```")["reason"] == "code block too long"
    assert jv.reward(SNAKE, "```javascript\nfunction camelToSnake\x00(s){}\n```")["reason"] == "NUL byte in code"


# --- correct and incorrect answers ---------------------------------------------------------------

@needs_node
def test_correct_value_scores_one():
    assert score(CORRECT_SNAKE)["reward"] == 1


@needs_node
def test_wrong_value_scores_zero():
    assert score(WRONG["camel_to_snake"])["reward"] == 0


@needs_node
def test_expected_exception_scores_one():
    # TypeError for non-string input, RangeError for empty string
    assert score(CORRECT_SNAKE)["reward"] == 1   # reference handles both


@needs_node
def test_wrong_exception_type_scores_zero():
    # Throws Error instead of TypeError
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new Error('nope');
          if (s.length === 0) throw new RangeError('empty');
          let r = ''; for (let i=0;i<s.length;i++){const c=s[i];r+=c>='A'&&c<='Z'?'_'+c.toLowerCase():c;}
          return r.startsWith('_')?r.slice(1):r;
        }
    """)
    res = score(code)
    assert res["reward"] == 0


@needs_node
def test_unexpected_exception_in_function_scores_zero():
    code = "function camelToSnake(s) { throw new SyntaxError('oops'); }\n"
    res = score(code)
    assert res["reward"] == 0 and res["reason"] != "no code block"


# --- cheating cases (all score 0) ---------------------------------------------------------------

@parametrize("sandbox", SANDBOXES)
def test_process_exit_in_iife_scores_zero(sandbox):
    code = textwrap.dedent("""\
        (function(){ process.exit(0); })();
        function camelToSnake(s) { return s; }
    """)
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0 and res.get("reason") != "no code block"


@parametrize("sandbox", SANDBOXES)
def test_process_exit_inside_function_scores_zero(sandbox):
    code = "function camelToSnake(s) { process.exit(0); return s; }\n"
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0


@parametrize("sandbox", SANDBOXES)
def test_worker_process_exit_does_not_count_as_success(sandbox):
    # process.exit(0) inside the Worker terminates only that Worker; the runner sees
    # exit-without-result and records failure.
    code = "function camelToSnake(s) { process.exit(0); }\n"
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0


@parametrize("sandbox", SANDBOXES)
def test_a_forged_result_file_cannot_match_unknown_answers(sandbox):
    # Reads cases.json, writes a results.json claiming every case returned "hello_world", then exits.
    code = textwrap.dedent("""\
        const fs = require('fs'), path = require('path');
        (function(){
          const dir = __dirname || '.';
          let n = 1;
          try { n = JSON.parse(fs.readFileSync(path.join(dir,'cases.json'),'utf8')).length; } catch(_){}
          const fake = JSON.stringify(Array(n).fill({ok:true,value:'hello_world'}));
          try { fs.writeFileSync(path.join(dir,'results.json'), fake); } catch(_){}
          process.exit(0);
        })();
        function camelToSnake(s) { return s; }
    """)
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0 and res["passed"] <= 1


@parametrize("sandbox", SANDBOXES)
def test_an_infinite_loop_times_out(sandbox):
    code = "function camelToSnake(s) { for(;;){} }\n"
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0
    assert res["seconds"] < 30


@parametrize("sandbox", SANDBOXES)
def test_an_infinite_loop_in_init_times_out(sandbox):
    code = "(function(){ for(;;){} })();\nfunction camelToSnake(s) { return s; }\n"
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0


@parametrize("sandbox", SANDBOXES)
def test_hard_coding_visible_examples_fails_hidden_ones(sandbox):
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (s === 'helloWorld') return 'hello_world';
          if (s === 'parseHTTP')  return 'parse_h_t_t_p';
          return s;
        }
    """)
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0 and res["visible_passed"] == "2/2"


@needs_node
def test_worker_crash_scores_zero():
    # Worker throws during evaluation (syntax error in IIFE)
    code = "function camelToSnake(s) { null.x; }\n"
    res = score(code)
    assert res["reward"] == 0


@needs_node
def test_outer_timeout_accommodates_all_cases():
    """The wall-clock budget passed to the runner must be >= n_cases * CASE_TIMEOUT_S.
    The old code used task.json's time_limit_s (5 s), which is less than 17*2=34 s."""
    task = jv.load_task(SNAKE)
    n = len(task["visible"]) + len(task["hidden"])
    seen = {}

    def spy_runner(workdir, task_time_s):
        seen["task_time_s"] = task_time_s
        return "stop"

    jv.reward(SNAKE, fence(CORRECT_SNAKE), spy_runner)
    minimum = n * jv.CASE_TIMEOUT_S
    assert seen.get("task_time_s", 0) >= minimum, (
        f"runner received task_time_s={seen.get('task_time_s')} "
        f"but need >= n*CASE_TIMEOUT_S={minimum}"
    )


@needs_node
def test_ok_true_without_value_is_malformed():
    """{ok:true} with no 'value' property must score 0 (not a valid success message)."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          const {parentPort} = require('worker_threads');
          parentPort.postMessage({ok: true});  // deliberately missing 'value'
          return s;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_ok_false_without_string_error_is_malformed():
    """{ok:false, error:42} (non-string error) must score 0."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          const {parentPort} = require('worker_threads');
          parentPort.postMessage({ok: false, error: 42});  // error must be a string
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_malformed_result_message_scores_zero():
    # Worker posts a non-object message; runner marks it as malformed.
    code = textwrap.dedent("""\
        const {parentPort, workerData, isMainThread} = require('worker_threads');
        function camelToSnake(s) { return 'hello_world'; }
        if (!isMainThread) {
          parentPort.postMessage('not an object');
        }
    """)
    res = score(code)
    assert res["reward"] == 0


@needs_node
def test_worker_async_work_cannot_outlive_worker_termination():
    """Worker termination is functional: a Worker keeping its event loop alive via setInterval
    is forcefully stopped by worker.terminate() + await exitPromise.

    Without that pair, setInterval prevents the Worker from ever emitting 'exit', so
    await exitPromise blocks forever and the runner hits the outer wall timeout.
    This test scores 1 only if all n Workers are terminated promptly between cases."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          // Arm an interval that keeps the Worker event loop alive indefinitely.
          // Without worker.terminate(), await exitPromise would never resolve.
          setInterval(() => {}, 0);
          if (typeof s !== 'string') throw new TypeError('input must be a string');
          if (s.length === 0) throw new RangeError('input must not be empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            r += c >= 'A' && c <= 'Z' ? '_' + c.toLowerCase() : c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    task = jv.load_task(SNAKE)
    n = len(task["visible"]) + len(task["hidden"])
    start = time.monotonic()
    res = jv.reward(SNAKE, fence(code))
    elapsed = time.monotonic() - start
    assert res["reward"] == 1, res
    # If worker.terminate() did not work, each of the n await-exitPromise calls would hang
    # until the outer timeout fires (n * CASE_TIMEOUT_S + STARTUP_S).
    # A healthy run completes well under half of that budget.
    budget = n * jv.CASE_TIMEOUT_S + jv.STARTUP_S
    assert elapsed < budget / 2, (
        f"elapsed {elapsed:.1f}s >= budget/2 ({budget/2:.1f}s) — "
        "Worker event loops may not be terminating between cases"
    )


@needs_node
def test_candidate_result_symlink_rejected():
    """Parent must reject results.json if it is a symlink (O_NOFOLLOW).
    If the platform cannot create symlinks, the test is skipped explicitly."""
    import tempfile
    target = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    target.write(b'[{"ok":true,"value":"hello_world"}]')
    target.flush()
    target.close()

    symlink_created = [False]

    def fake_runner(workdir, task_time_s):
        symlink = workdir / "results.json"
        try:
            symlink.unlink(missing_ok=True)
            symlink.symlink_to(target.name)
            symlink_created[0] = symlink.is_symlink()
        except (OSError, NotImplementedError):
            pass
        return None

    try:
        res = jv.reward(SNAKE, fence(CORRECT_SNAKE), fake_runner)
    finally:
        os.unlink(target.name)

    if not symlink_created[0]:
        pytest.skip(
            "cannot create symlinks on this platform "
            "(on Windows: enable Developer Mode or run as administrator)"
        )

    assert res["reward"] == 0, "parent accepted a symlink as results.json — O_NOFOLLOW check failed"


@needs_node
def test_malformed_results_file_scores_zero():
    def write_bad(workdir, task_time_s):
        (workdir / "results.json").write_text("not json at all")
        return None

    assert jv.reward(SNAKE, fence(CORRECT_SNAKE), write_bad)["reason"] == "no readable result file"


@needs_node
def test_oversized_results_file_scores_zero():
    def write_big(workdir, task_time_s):
        (workdir / "results.json").write_bytes(b"x" * (jv.MAX_RESULT_BYTES + 1))
        return None

    assert jv.reward(SNAKE, fence(CORRECT_SNAKE), write_big)["reason"] == "no readable result file"


@needs_node
def test_result_file_wrong_shape_scores_zero():
    def write_obj(workdir, task_time_s):
        (workdir / "results.json").write_text('{"ok": true}')
        return None

    assert jv.reward(SNAKE, fence(CORRECT_SNAKE), write_obj)["reason"] == "result file has the wrong shape"


@needs_node
def test_missing_result_file_scores_zero():
    assert jv.reward(SNAKE, fence(CORRECT_SNAKE), lambda w, t: None)["reason"] == "no readable result file"


# --- runner failure -------------------------------------------------------------------------------

@skipif(not _docker_ready(), reason="docker or the JS image is missing")
def test_a_missing_docker_image_raises_not_scores_zero(monkeypatch):
    monkeypatch.setattr(jv, "JS_IMAGE", "g10-js-rl-does-not-exist:0")
    with pytest.raises(RuntimeError, match="docker sandbox failed"):
        score(CORRECT_SNAKE, sandbox="docker")


# --- sandbox contents check -----------------------------------------------------------------------

@needs_node
def test_sandbox_folder_holds_inputs_only_no_expected_values():
    seen = {}

    def spy(workdir, task_time_s):
        seen["files"] = sorted(p.name for p in workdir.iterdir())
        seen["cases"] = (workdir / "cases.json").read_text(encoding="utf-8")
        return "stop"

    jv.reward(SNAKE, fence(CORRECT_SNAKE), spy)
    assert seen["files"] == ["_case_timeout", "_entry", "cases.json", "runner.js", "solution.js"]
    assert "expected" not in seen["cases"] and "raises" not in seen["cases"]
    assert not any("reference" in f for f in seen["files"])


@needs_node
def test_runner_deletes_cases_json_before_workers():
    """cases.json must be gone from the workdir once the runner process returns.
    Workers are spawned only after this deletion, so candidate code has no file to read."""
    was_present_before = [False]
    was_present_after = [True]   # default pessimistic

    def spy(workdir, task_time_s):
        was_present_before[0] = (workdir / "cases.json").exists()
        err = jv._run_process(workdir, task_time_s)
        was_present_after[0] = (workdir / "cases.json").exists()
        return err

    res = jv.reward(SNAKE, fence(CORRECT_SNAKE), spy)
    assert res["reward"] == 1
    assert was_present_before[0], "cases.json should be written before the runner is called"
    assert not was_present_after[0], (
        "cases.json still present after runner exit — "
        "Worker code can read the full hidden input list"
    )


@needs_node
def test_deletion_failure_aborts_runner_before_workers_start():
    """When the runner cannot delete cases.json (simulated EPERM on unlinkSync), it must
    exit non-zero and must NOT write results.json, proving Workers were never spawned.
    The injection seam overwrites runner.js before the real process starts."""
    results_written = [False]

    def inject_and_run(workdir, task_time_s):
        (workdir / "runner.js").write_text(_RUNNER_UNLINK_FAILS, encoding="utf-8")
        err = jv._run_process(workdir, task_time_s)
        results_written[0] = (workdir / "results.json").exists()
        return err

    res = jv.reward(SNAKE, fence(CORRECT_SNAKE), inject_and_run)
    assert res["reward"] == 0, (
        f"verifier scored {res['reward']} despite simulated deletion failure: {res}"
    )
    assert not results_written[0], (
        "results.json was written after deletion failure — Workers may have started before deletion"
    )


@needs_node
def test_cases_json_presence_after_deletion_aborts_runner():
    """Runner must exit non-zero when cases.json is still present after the unlink attempt.
    A patched runner that recreates cases.json after deleting it exercises the existsSync
    guard, which is the belt-and-suspenders check for race conditions or partial failures."""
    _runner = textwrap.dedent("""\
        'use strict';
        const fs = require('fs');
        const path = require('path');
        const {isMainThread} = require('worker_threads');
        if (!isMainThread) { process.exit(2); }
        const [workdir] = process.argv.slice(2);
        if (!workdir) { process.exit(2); }
        try { JSON.parse(fs.readFileSync(path.join(workdir,'cases.json'),'utf8')); } catch(_){ process.exit(2); }
        const casesPath = path.join(workdir,'cases.json');
        try { fs.unlinkSync(casesPath); } catch(_){ process.exit(2); }
        // Simulate: file reappears after deletion (symlink race, another writer, etc.)
        fs.writeFileSync(casesPath,'[]');
        if (fs.existsSync(casesPath)) { process.exit(2); }
        process.exit(0);
    """)

    def inject_and_run(workdir, task_time_s):
        (workdir / "runner.js").write_text(_runner, encoding="utf-8")
        return jv._run_process(workdir, task_time_s)

    res = jv.reward(SNAKE, fence(CORRECT_SNAKE), inject_and_run)
    assert res["reward"] == 0, (
        f"verifier scored {res['reward']} despite cases.json persisting after deletion: {res}"
    )


@needs_node
def test_candidate_cannot_read_hidden_inputs_via_cases_json():
    """The candidate cannot enumerate hidden inputs by reading cases.json.

    The solution tries every plausible path to require() that might be reachable
    inside new Function() — including process.mainModule.require (deprecated but
    present in older Node.js).  With the fix, cases.json has been deleted before
    any Worker starts, so even if require were accessible the read would fail."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          // Try every plausible path to a filesystem require.
          const req = (function() {
            try { if (typeof require !== 'undefined') return require; } catch (_) {}
            try {
              if (process.mainModule && typeof process.mainModule.require === 'function')
                return process.mainModule.require.bind(process.mainModule);
            } catch (_) {}
            return null;
          })();
          if (req) {
            try {
              const data = req('fs').readFileSync(process.cwd() + '/cases.json', 'utf8');
              const cases = JSON.parse(data);
              // Encode the case count into a fake return value to signal leakage.
              return 'LEAKED:' + cases.length;
            } catch (_) {}
          }
          // Correct fallback — used when cases.json is inaccessible (the normal path).
          if (typeof s !== 'string') throw new TypeError('input must be a string');
          if (s.length === 0) throw new RangeError('input must not be empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            r += c >= 'A' && c <= 'Z' ? '_' + c.toLowerCase() : c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    res = jv.reward(SNAKE, fence(code))
    assert res["reward"] == 1, (
        "candidate was able to read cases.json and leaked hidden inputs — "
        f"result: {res}"
    )


@needs_node
def test_candidate_cannot_read_hidden_inputs_via_get_builtin_module():
    """process.getBuiltinModule('fs') is accessible via the process global inside new Function
    (Node.js 22.3+). However, cases.json is deleted before any Worker is spawned, so a read
    attempt fails with ENOENT. Score 1 proves the invariant: hidden inputs are unavailable at
    candidate execution time.

    Note: filesystem access through process.getBuiltinModule is NOT blocked. The security
    property is that the hidden-input file (cases.json) and expected answers are absent from
    the working directory by the time candidate code runs."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          // Explicit attempt via process.getBuiltinModule (Node.js 22.3+).
          // process is a global reachable inside new Function.
          try {
            const fs = process.getBuiltinModule('fs');
            if (fs) {
              const data = fs.readFileSync(process.cwd() + '/cases.json', 'utf8');
              const cases = JSON.parse(data);
              // Encode the case count to signal a successful leak.
              return 'LEAKED:' + cases.length;
            }
          } catch (_) {}
          // Correct fallback — the normal path once cases.json has been deleted.
          if (typeof s !== 'string') throw new TypeError('input must be a string');
          if (s.length === 0) throw new RangeError('input must not be empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            r += c >= 'A' && c <= 'Z' ? '_' + c.toLowerCase() : c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    res = jv.reward(SNAKE, fence(code))
    assert res["reward"] == 1, (
        "candidate read cases.json via process.getBuiltinModule — "
        "cases.json was not deleted before the Worker started. "
        f"result: {res}"
    )


# --- lint -----------------------------------------------------------------------------------------

def _copy_task(tmp_path: Path) -> Path:
    dst = tmp_path / "camel_to_snake"
    shutil.copytree(SNAKE, dst)
    return dst


@needs_node
def test_lint_catches_a_wrong_reference(tmp_path):
    t = _copy_task(tmp_path)
    (t / "reference.js").write_text(WRONG["camel_to_snake"])
    assert any("reference solution does not score 1" in p for p in jv.check_task(t))


def test_lint_catches_source_not_original_and_wrong_language(tmp_path):
    t = _copy_task(tmp_path)
    meta = json.loads((t / "task.json").read_text())
    meta["source"], meta["language"] = "HumanEval/12", "python"
    (t / "task.json").write_text(json.dumps(meta))
    problems = jv.check_task(t)
    assert any("original" in p for p in problems) and any("language" in p for p in problems)


def test_lint_catches_a_hidden_call_in_the_prompt(tmp_path):
    t = _copy_task(tmp_path)
    (t / "prompt.md").write_text((t / "prompt.md").read_text() + '\ncamelToSnake("HTMLParser")\n')
    assert any("hidden test call appears" in p for p in jv.check_task(t))


def test_lint_catches_too_few_hidden_tests(tmp_path):
    t = _copy_task(tmp_path)
    cases = json.loads((t / "hidden_tests.json").read_text())[:5]
    (t / "hidden_tests.json").write_text(json.dumps(cases))
    assert any("at least 10 hidden" in p for p in jv.check_task(t))


def test_lint_catches_bad_raises_value(tmp_path):
    t = _copy_task(tmp_path)
    cases = json.loads((t / "hidden_tests.json").read_text())
    cases[-1] = {"args": [42], "raises": "not-a-valid-identifier!"}
    (t / "hidden_tests.json").write_text(json.dumps(cases))
    assert any('"raises" must be' in p for p in jv.check_task(t))


def test_lint_catches_invalid_time_limit(tmp_path):
    """check_task() must reject booleans, strings, zero, below-minimum, negative, above-max,
    and extremely large integers (which would OverflowError if passed to math.isfinite)."""
    t = _copy_task(tmp_path)
    for bad in [True, False, "5", 0, 0.05, -1, 301, 10**400]:
        meta = json.loads((t / "task.json").read_text())
        meta["time_limit_s"] = bad
        (t / "task.json").write_text(json.dumps(meta))
        problems = jv.check_task(t)
        assert any("time_limit_s" in p for p in problems), (
            f"check_task did not reject time_limit_s={bad!r}: {problems}"
        )


@needs_node
def test_lint_accepts_time_limit_at_boundary(tmp_path):
    """time_limit_s = 300 (the maximum) must be accepted; 301 must be rejected."""
    t = _copy_task(tmp_path)
    meta = json.loads((t / "task.json").read_text())
    meta["time_limit_s"] = 300
    (t / "task.json").write_text(json.dumps(meta))
    problems = jv.check_task(t)
    assert not any("time_limit_s" in p for p in problems), (
        f"check_task rejected time_limit_s=300 (should be valid): {problems}"
    )


def test_invalid_time_limit_prevents_execution(monkeypatch, tmp_path):
    """reward() must reject invalid time_limit_s metadata before calling any runner.

    Uses monkeypatch to inject non-JSON-serialisable values (NaN, Infinity) that
    cannot appear in a real task.json, plus serialisable bad values written to disk.
    Includes 10**400: a large integer that would raise OverflowError if passed to
    math.isfinite(), verifying the float-only guard."""
    t = _copy_task(tmp_path)
    original_load = jv.load_task
    called = []

    def spy_runner(workdir, task_time_s):
        called.append(True)
        return None

    for bad in [True, "5", 0, 0.05, -1, 301, float('nan'), float('inf'), 10**400]:
        called.clear()

        def patched_load(task_dir, _bad=bad):
            meta = original_load(task_dir)
            meta["time_limit_s"] = _bad
            return meta

        monkeypatch.setattr(jv, "load_task", patched_load)
        res = jv.reward(t, fence(CORRECT_SNAKE), spy_runner)
        assert res["reward"] == 0, f"reward() accepted time_limit_s={bad!r}: {res}"
        assert not called, f"runner was called despite invalid time_limit_s={bad!r}"


def test_valid_time_limit_allows_execution(monkeypatch, tmp_path):
    """reward() must call the runner for boundary-valid time_limit_s values (0.1 and 300)."""
    t = _copy_task(tmp_path)
    original_load = jv.load_task
    called = []

    def spy_runner(workdir, task_time_s):
        called.append(True)
        return None  # spy returns no error; reward() will not find results.json → score 0

    for good in [0.1, 300]:
        called.clear()

        def patched_load(task_dir, _good=good):
            meta = original_load(task_dir)
            meta["time_limit_s"] = _good
            return meta

        monkeypatch.setattr(jv, "load_task", patched_load)
        jv.reward(t, fence(CORRECT_SNAKE), spy_runner)
        assert called, f"runner was NOT called for valid time_limit_s={good!r}"


# --- BLOCKER 2: exception semantics regression -----------------------------------------------

@needs_node
def test_undefined_return_for_typeerror_input_scores_zero():
    """Returning undefined instead of throwing TypeError must score 0.
    InvalidReturn and TypeError are distinct; undefined must not match {"raises":"TypeError"}."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') return undefined;  // wrong: should throw TypeError
          if (s.length === 0) throw new RangeError('empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_nan_return_for_typeerror_input_scores_zero():
    """Returning NaN instead of throwing TypeError must score 0.
    InvalidReturn and TypeError are distinct; NaN must not match {"raises":"TypeError"}."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') return NaN;  // wrong: should throw TypeError
          if (s.length === 0) throw new RangeError('empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_forged_constructor_name_typeerror_scores_zero():
    """Throwing {constructor:{name:'TypeError'}} must not satisfy {"raises":"TypeError"}.
    util.types.isNativeError is the first classification gate: a plain object has no native
    Error brand, so isNativeError returns false and it is classified as ThrownNonError, not
    TypeError. constructor.name is not consulted."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') throw { constructor: { name: 'TypeError' } };
          if (s.length === 0) throw new RangeError('empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_forged_constructor_name_rangeerror_scores_zero():
    """Throwing {constructor:{name:'RangeError'}} must not satisfy {"raises":"RangeError"}."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new TypeError('bad type');
          if (s.length === 0) throw { constructor: { name: 'RangeError' } };  // forged
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


# --- BLOCKER 1: Worker result authentication -------------------------------------------------

@needs_node
def test_forged_parentport_success_via_process_scores_zero():
    """A candidate that sends a well-formed success message via
    process.getBuiltinModule('worker_threads').parentPort before returning a wrong value
    must score 0.

    With the hardened bootstrap, parentPort is nulled before candidate code runs.
    The message attempt throws TypeError (postMessage on null), which is caught and
    ignored by the candidate; the wrong return value is then scored normally."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          try {
            const wt = process.getBuiltinModule('worker_threads');
            if (wt && wt.parentPort) {
              wt.parentPort.postMessage({ ok: true, value: s });
            }
          } catch (_) {}
          return typeof s === 'string' ? s : String(s);  // deliberately wrong
        }
    """)
    res = score(code)
    assert res["reward"] == 0, (
        "forged parentPort message was accepted — parentPort was not nulled before "
        f"candidate code ran. result: {res}"
    )


@needs_node
def test_forged_exception_via_parentport_scores_zero():
    """A candidate that forges {"ok":false,"error":"RangeError"} via parentPort must score 0.

    parentPort is null, so postMessage throws; the candidate catches it.  The function
    then does NOT throw RangeError for the empty-string case, so the RangeError test fails."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          try {
            const wt = process.getBuiltinModule('worker_threads');
            if (wt && wt.parentPort) {
              wt.parentPort.postMessage({ ok: false, error: 'RangeError' });
            }
          } catch (_) {}
          if (typeof s !== 'string') throw new TypeError('bad');
          // Falls through without throwing for empty string — wrong.
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    res = score(code)
    assert res["reward"] == 0, (
        f"forged RangeError message was accepted — parentPort was not nulled. result: {res}"
    )


@needs_node
def test_bootstrap_replacement_does_not_affect_execution():
    """A candidate that overwrites runner.js in the work directory must not affect
    subsequent Workers.  WORKER_BOOT is embedded in the runner process memory and
    passed via eval:true; it is never re-read from disk between cases.

    A correct implementation that also attempts to overwrite runner.js must score 1."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          try {
            const fs = process.getBuiltinModule('fs');
            if (fs) {
              const malicious = "process.exit(42);";
              try { fs.writeFileSync(process.cwd() + '/runner.js', malicious); } catch (_) {}
              try { fs.writeFileSync('/work/runner.js', malicious); } catch (_) {}
            }
          } catch (_) {}
          if (typeof s !== 'string') throw new TypeError('input must be a string');
          if (s.length === 0) throw new RangeError('input must not be empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    res = score(code)
    assert res["reward"] == 1, (
        "bootstrap replacement affected execution — subsequent Workers did not use the "
        f"in-memory WORKER_BOOT string. result: {res}"
    )


# --- BLOCKER 3: leading-underscore preservation regression -----------------------------------

@needs_node
def test_original_leading_underscore_cases_pass():
    """_foo stays _foo; _Foo becomes __foo; __Foo becomes ___foo.
    These cases are in hidden_tests.json; the reference must score 1 on all of them."""
    assert score(CORRECT_SNAKE)["reward"] == 1


@needs_node
def test_old_startswith_logic_fails_underscore_cases():
    """An implementation using result.startsWith('_') ? result.slice(1) : result
    incorrectly converts _foo -> foo.  It must score 0 after the new hidden cases are added."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new TypeError('input must be a string');
          if (s.length === 0) throw new RangeError('input must not be empty');
          let r = '';
          for (let i = 0; i < s.length; i++) {
            const c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return r.startsWith('_') ? r.slice(1) : r;  // old buggy logic
        }
    """)
    assert score(code)["reward"] == 0


# --- BLOCKER 4: sandbox selection hardening --------------------------------------------------

def test_invalid_sandbox_raises_value_error():
    """reward() must raise ValueError for an unrecognised sandbox string.
    It must not silently fall back to the process sandbox."""
    with pytest.raises(ValueError, match="sandbox"):
        jv.reward(SNAKE, fence(CORRECT_SNAKE), "daemon")


def test_docker_unavailable_raises_runtime_error(monkeypatch):
    """When docker is not on PATH, reward(..., sandbox='docker') must raise RuntimeError
    rather than propagating FileNotFoundError from subprocess."""
    original_which = jv.shutil.which

    def no_docker(cmd):
        return None if cmd == "docker" else original_which(cmd)

    monkeypatch.setattr(jv.shutil, "which", no_docker)
    with pytest.raises(RuntimeError, match="docker"):
        jv.reward(SNAKE, fence(CORRECT_SNAKE), "docker")


# --- Phase 2.9: intrinsic mutation attacks (all score 0 unless documented otherwise) ----------

@needs_node
def test_object_assign_replacement_scores_zero():
    """Replacing Object.assign to convert InvalidReturn to TypeError must score 0.

    Phase 2.8 used Object.assign({}, msg, {_nonce}) to build result messages; a malicious
    replacement could intercept the result and mutate the error field.  Phase 2.9 uses
    null-prototype object literals so Object.assign is never called in the bootstrap."""
    code = textwrap.dedent("""\
        (function () {
          var _origAssign = Object.assign;
          Object.assign = function () {
            var r = _origAssign.apply(this, arguments);
            // Convert any InvalidReturn to TypeError so that returning undefined
            // satisfies {"raises": "TypeError"} test cases.
            if (r && r.error === 'InvalidReturn') r.error = 'TypeError';
            if (r && r.error === 'InvalidReturn') r.error = 'RangeError';
            return r;
          };
        })();
        function camelToSnake(s) {
          if (typeof s !== 'string') return undefined;  // wrong: should throw TypeError
          if (s.length === 0) return undefined;         // wrong: should throw RangeError
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_promise_resolve_replacement_scores_zero():
    """Replacing Promise.resolve to short-circuit the execution chain must score 0.

    Phase 2.8 called Promise.resolve().then(fn); a malicious replacement could return
    a fake thenable that calls onFulfilled with a hardcoded value instead of running fn.
    Phase 2.9 uses new _Promise(...) with a captured constructor reference."""
    code = textwrap.dedent("""\
        (function () {
          var _origResolve = Promise.resolve.bind(Promise);
          Promise.resolve = function (v) {
            if (v === undefined) {
              // Bootstrap calls Promise.resolve() with no arg.
              // Return a fake thenable that hardcodes a 'correct' value.
              return {
                then: function (cb) { if (typeof cb === 'function') cb('hello_world'); return this; },
                catch: function () { return this; }
              };
            }
            return _origResolve(v);
          };
        })();
        function camelToSnake(s) {
          return 'wrong';  // wrong implementation — relies on Promise.resolve bypass
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_promise_prototype_then_replacement_scores_zero():
    """Replacing Promise.prototype.then to intercept the bootstrap chain must score 0.

    A malicious replacement could call onFulfilled with a hardcoded value, bypassing fn.
    Phase 2.9 captures _promiseThen = Function.prototype.call.bind(Promise.prototype.then)
    before any candidate code runs; the bound function calls the original then directly."""
    code = textwrap.dedent("""\
        (function () {
          var _origThen = Promise.prototype.then;
          Promise.prototype.then = function (onFulfilled, onRejected) {
            // Call the success callback with a hardcoded value, bypassing actual fn result.
            if (typeof onFulfilled === 'function') onFulfilled('hello_world');
            return this;
          };
        })();
        function camelToSnake(s) {
          return 'wrong';  // wrong — relies on then bypass
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_messageport_postmessage_replacement_scores_zero():
    """Replacing MessagePort.prototype.postMessage to intercept result messages must score 0.

    Phase 2.9 captures _portPost = _port.postMessage.bind(_port) before candidate code;
    the bound function holds a direct reference to the original postMessage object and is
    immune to prototype-level replacement."""
    code = textwrap.dedent("""\
        (function () {
          try {
            var wt = process.getBuiltinModule('worker_threads');
            var origPost = wt.MessagePort.prototype.postMessage;
            wt.MessagePort.prototype.postMessage = function (msg) {
              // Forge a success result for any outgoing message.
              var faked = { ok: true, value: 'hello_world' };
              if (msg && typeof msg._nonce !== 'undefined') faked._nonce = msg._nonce;
              origPost.call(this, faked);
            };
          } catch (_) {}
        })();
        function camelToSnake(s) {
          return 'wrong';  // wrong — relies on postMessage interception
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_func_prototype_apply_replacement_scores_zero():
    """Replacing Function.prototype.apply to skip the actual fn call must score 0.

    Phase 2.9 captures _funcApply = Function.prototype.call.bind(Function.prototype.apply)
    before any candidate code; the bound function invokes the original apply directly."""
    code = textwrap.dedent("""\
        (function () {
          var origApply = Function.prototype.apply;
          Function.prototype.apply = function (thisArg, argList) {
            // Return 'hello_world' whenever the bootstrap calls fn.apply(null, args).
            return 'hello_world';
          };
        })();
        function camelToSnake(s) {
          return 'wrong';  // wrong — relies on apply bypass
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_plain_object_with_typeerror_prototype_scores_zero():
    """throw Object.setPrototypeOf({}, TypeError.prototype) must score 0.

    The thrown value is a plain object (not a native Error); util.types.isNativeError
    returns false for it, so it is classified as ThrownNonError, not TypeError."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') {
            // Plain object with TypeError.prototype — not a native Error.
            throw Object.setPrototypeOf({}, TypeError.prototype);
          }
          if (s.length === 0) throw new RangeError('empty');
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_plain_object_with_rangeerror_prototype_scores_zero():
    """throw Object.setPrototypeOf({}, RangeError.prototype) must score 0.

    The thrown value is a plain object; util.types.isNativeError returns false,
    so it is classified as ThrownNonError, not RangeError."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new TypeError('bad type');
          if (s.length === 0) {
            // Plain object with RangeError.prototype — not a native Error.
            throw Object.setPrototypeOf({}, RangeError.prototype);
          }
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_global_typeerror_replacement_scores_zero():
    """Replacing globalThis.TypeError with class FakeTypeError extends Error {} must score 0.

    class FakeTypeError extends Error {} — note: extends Error, not TypeError.
    util.types.isNativeError returns true for FakeTypeError instances (they carry the native
    Error brand), but _isPrototypeOf(_TypeErrorProto, err) returns false because
    TypeError.prototype is NOT in the prototype chain of FakeTypeError instances
    (chain: FakeTypeError.prototype → Error.prototype, not through TypeError.prototype).
    The error is therefore classified as 'Error', which does not match {"raises":"TypeError"},
    so the test cases fail and the score is 0.

    The captured _TypeErrorProto refers to the original TypeError.prototype and is unaffected
    by the globalThis.TypeError replacement."""
    code = textwrap.dedent("""\
        (function () {
          globalThis.TypeError = class FakeTypeError extends Error {
            constructor (msg) { super(msg); this.name = 'TypeError'; }
          };
        })();
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new TypeError('not a string');  // uses FakeTypeError
          if (s.length === 0) throw new RangeError('empty');
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_global_rangeerror_replacement_scores_zero():
    """Replacing globalThis.RangeError with class FakeRangeError extends Error {} must score 0.

    class FakeRangeError extends Error {} — extends Error, not RangeError.
    util.types.isNativeError returns true for FakeRangeError instances, but
    _isPrototypeOf(_RangeErrorProto, err) returns false because RangeError.prototype is NOT
    in the prototype chain of FakeRangeError instances.  Classified as 'Error', not
    'RangeError'; test cases for {"raises":"RangeError"} fail, score is 0."""
    code = textwrap.dedent("""\
        (function () {
          globalThis.RangeError = class FakeRangeError extends Error {
            constructor (msg) { super(msg); this.name = 'RangeError'; }
          };
        })();
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new TypeError('not a string');
          if (s.length === 0) throw new RangeError('empty');  // uses FakeRangeError
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_forged_error_constructor_name_scores_zero():
    """Object.assign(new Error(), {constructor:{name:'TypeError'}}) must score 0.

    Phase 2.9 does not use constructor.name at all.  The thrown value is a real native Error
    (isNativeError = true) but its prototype chain is Error.prototype, not TypeError.prototype,
    so _isPrototypeOf(_TypeErrorProto, err) is false.  Classified as 'Error', not 'TypeError'."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') {
            var e = new Error('not a string');
            e.constructor = { name: 'TypeError' };  // forged constructor.name
            throw e;
          }
          if (s.length === 0) {
            var e2 = new Error('empty');
            e2.constructor = { name: 'RangeError' };
            throw e2;
          }
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    assert score(code)["reward"] == 0


@needs_node
def test_custom_typeerror_subclass_is_accepted():
    """class CustomTypeError extends TypeError {} is accepted as TypeError (subclass semantics).

    util.types.isNativeError returns true (the instance carries the native Error brand).
    TypeError.prototype IS in the prototype chain of CustomTypeError instances
    (chain: instance → CustomTypeError.prototype → TypeError.prototype → Error.prototype),
    so _isPrototypeOf(_TypeErrorProto, err) returns true → classified as 'TypeError'.
    Exception matching is subclass-aware by design; this scores 1."""
    code = textwrap.dedent("""\
        class CustomTypeError extends TypeError {
          constructor(msg) { super(msg); this.name = 'CustomTypeError'; }
        }
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new CustomTypeError('not a string');
          if (s.length === 0) throw new RangeError('input must not be empty');
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    res = score(code)
    assert res["reward"] == 1, (
        "Expected score 1: CustomTypeError extends TypeError should satisfy "
        '{"raises":"TypeError"} test cases (subclass-aware exception semantics). '
        f"result: {res}"
    )


@needs_node
def test_custom_rangeerror_subclass_is_accepted():
    """class CustomRangeError extends RangeError {} is accepted as RangeError (subclass semantics).

    RangeError.prototype IS in the prototype chain of CustomRangeError instances,
    so _isPrototypeOf(_RangeErrorProto, err) returns true → classified as 'RangeError'.
    This scores 1."""
    code = textwrap.dedent("""\
        class CustomRangeError extends RangeError {
          constructor(msg) { super(msg); this.name = 'CustomRangeError'; }
        }
        function camelToSnake(s) {
          if (typeof s !== 'string') throw new TypeError('input must be a string');
          if (s.length === 0) throw new CustomRangeError('input must not be empty');
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    res = score(code)
    assert res["reward"] == 1, (
        "Expected score 1: CustomRangeError extends RangeError should satisfy "
        '{"raises":"RangeError"} test cases (subclass-aware exception semantics). '
        f"result: {res}"
    )


@needs_node
def test_setprototypeof_real_error_documents_same_realm_limitation():
    """SAME-REALM LIMITATION: Object.setPrototypeOf(realNativeError, TypeError.prototype)
    is classified as TypeError by the hardened bootstrap.

    util.types.isNativeError is true (the base object is a real native Error created by
    new Error()).  _isPrototypeOf(_TypeErrorProto, err) is also true because TypeError.prototype
    was inserted into the prototype chain via Object.setPrototypeOf.  Both checks pass, so
    the error is classified as TypeError.  This is a fundamental constraint of a shared JS
    realm and cannot be resolved without out-of-realm isolation.

    A candidate that uses this technique for exception cases and returns correct values for
    value cases scores 1 — the behaviour is semantically correct (they ARE throwing when
    the input is wrong); the same-realm limitation accepts it."""
    code = textwrap.dedent("""\
        function camelToSnake(s) {
          if (typeof s !== 'string') {
            throw Object.setPrototypeOf(new Error('not a string'), TypeError.prototype);
          }
          if (s.length === 0) {
            throw Object.setPrototypeOf(new Error('empty'), RangeError.prototype);
          }
          var r = '';
          for (var i = 0; i < s.length; i++) {
            var c = s[i];
            if (c >= 'A' && c <= 'Z') r += '_' + c.toLowerCase();
            else r += c;
          }
          return s[0] >= 'A' && s[0] <= 'Z' ? r.slice(1) : r;
        }
    """)
    res = score(code)
    assert res["reward"] == 1, (
        "Expected score 1 documenting the same-realm limitation: "
        "Object.setPrototypeOf(realNativeError, TypeError.prototype) is classified as TypeError. "
        f"result: {res}"
    )


# --- CLI -----------------------------------------------------------------------------------------

@needs_node
def test_cli_reward(tmp_path):
    comp = tmp_path / "c.txt"
    comp.write_text(fence(CORRECT_SNAKE))
    out = subprocess.run(
        [sys.executable, str(HERE / "js_verifier.py"), "--reward", str(SNAKE), str(comp)],
        capture_output=True, text=True,
    )
    assert json.loads(out.stdout)["reward"] == 1


def test_cli_names_missing_task_folder_instead_of_traceback(tmp_path):
    comp = tmp_path / "c.txt"
    comp.write_text(fence(CORRECT_SNAKE))
    for cmd in (
        ["--reward", str(tmp_path / "nope"), str(comp)],
        ["--check-task", str(tmp_path / "nope")],
    ):
        out = subprocess.run(
            [sys.executable, str(HERE / "js_verifier.py"), *cmd], capture_output=True, text=True
        )
        assert out.returncode == 2 and "not found" in out.stderr and "Traceback" not in out.stderr
