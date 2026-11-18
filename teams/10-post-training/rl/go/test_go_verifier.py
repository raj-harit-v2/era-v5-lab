"""Tests for go_verifier.py: for every Go task a correct and a wrong answer, then the cheating cases.

Run:  python -m pytest teams/10-post-training/rl/go/test_go_verifier.py -q -p no:cacheprovider
`process` tests need `go` on PATH. `docker` tests run only when `docker` and the image from go.Dockerfile
(G10_GO_IMAGE, default g10-go-rl:1) are present locally; build it with
  docker build -f teams/10-post-training/rl/go/go.Dockerfile -t g10-go-rl:1 teams/10-post-training/rl/go
"""
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parent.parent))
import go_verifier as gv  # noqa: E402

HERE = Path(__file__).resolve().parent
TASKS = sorted(p for p in (HERE / "tasks").iterdir() if p.is_dir())
SPLIT = HERE / "tasks" / "split_balanced"

# Named decorators: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize
skipif = pytest.mark.skipif


def _docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", gv.GO_IMAGE], capture_output=True, timeout=20).returncode == 0
    except Exception:
        return False


needs_go = pytest.mark.skipif(not shutil.which("go"), reason="go is not installed")
SANDBOXES = [
    pytest.param("process", marks=needs_go),
    pytest.param("docker", marks=pytest.mark.skipif(not _docker_ready(), reason="docker or the Go image is missing")),
]


def fence(code: str, label: str = "go") -> str:
    return "Here is my answer.\n```" + label + "\n" + textwrap.dedent(code).strip() + "\n```\n"


# A wrong answer for each task: it compiles and runs, and returns an answer that is wrong for most inputs.
WRONG = {
    "parse_size": 'package main\nfunc ParseSize(s string) (int64, error) { return 0, nil }\n',
    "parse_kv_line": 'package main\nfunc ParseKV(line string) (map[string]string, error) { return map[string]string{}, nil }\n',
    "split_balanced": 'package main\nfunc SplitBalanced(xs []int, parts int) ([][]int, error) { return [][]int{xs}, nil }\n',
    "merge_intervals": 'package main\nfunc MergeIntervals(iv [][]int) ([][]int, error) { return iv, nil }\n',
    "parse_roman": 'package main\nfunc ParseRoman(s string) (int, error) { return len(s), nil }\n',
    "top_words": 'package main\nfunc TopWords(text string, k int) []string { return []string{} }\n',
    "lru_trace": 'package main\nfunc LRUTrace(capacity int, ops []string) ([]string, error) { return []string{}, nil }\n',
    "expand_rle": 'package main\nfunc ExpandRLE(s string, maxLen int) (string, error) { return s, nil }\n',
    "cidr_contains": 'package main\nfunc CIDRContains(cidr, ip string) (bool, error) { return true, nil }\n',
    "compare_semver": 'package main\nfunc CompareVersions(a, b string) (int, error) { return 0, nil }\n',
}


def score(code: str, task: Path = SPLIT, sandbox: str = "process", label: str = "go") -> dict:
    return gv.reward(task, fence(code, label), sandbox)


CORRECT_SPLIT = (SPLIT / "reference.go").read_text(encoding="utf-8")


def inject(imports: str = "", extra: str = "") -> str:
    """The correct answer with extra imports (after the package line) and extra declarations (at the end)."""
    return CORRECT_SPLIT.replace("package main\n", "package main\n" + imports + "\n", 1) + "\n" + extra + "\n"


# --- every task: one correct answer and one wrong answer -----------------------------------------

@parametrize("sandbox", SANDBOXES)
@parametrize("task", TASKS, ids=lambda p: p.name)
def test_reference_scores_one(task, sandbox):
    res = gv.reward(task, fence((task / "reference.go").read_text(encoding="utf-8")), sandbox)
    assert res["reward"] == 1, res


@parametrize("sandbox", SANDBOXES)
@parametrize("task", TASKS, ids=lambda p: p.name)
def test_wrong_answer_scores_zero_and_hides_which_hidden_test_failed(task, sandbox):
    res = gv.reward(task, fence(WRONG[task.name]), sandbox)
    assert res["reward"] == 0
    assert res["passed"] < res["total"]
    assert "expected" not in json.dumps(res).lower()


def test_every_task_has_a_wrong_answer_in_this_file():
    assert {t.name for t in TASKS} == set(WRONG)


@needs_go
@parametrize("task", TASKS, ids=lambda p: p.name)
def test_task_passes_the_lint(task):
    assert gv.check_task(task) == []


# --- parsing the completion ----------------------------------------------------------------------

@needs_go
def test_no_code_block_scores_zero():
    assert gv.reward(SPLIT, "I think the answer is 42.")["reward"] == 0


@needs_go
def test_a_python_block_is_not_go_code():
    assert score(CORRECT_SPLIT, label="python")["reward"] == 0


@needs_go
def test_unlabelled_block_counts_and_the_last_go_block_is_used():
    text = fence(WRONG["split_balanced"]) + "\nOutput:\n```text\nok\n```\n\nFinal:\n" + fence(CORRECT_SPLIT, "")
    assert gv.reward(SPLIT, text)["reward"] == 1


@needs_go
def test_unclosed_block_scores_zero():
    assert gv.reward(SPLIT, "```go\n" + CORRECT_SPLIT)["reward"] == 0


def test_oversized_and_nul_code_are_refused():
    assert gv.reward(SPLIT, "```go\n" + "// x\n" * 10000 + "```")["reason"] == "code block too long"
    assert gv.reward(SPLIT, "```go\npackage main\x00\n```")["reason"] == "NUL byte in code"


# --- compile problems ----------------------------------------------------------------------------

@needs_go
def test_syntax_error_scores_zero():
    assert score("package main\nfunc SplitBalanced( {")["reward"] == 0


@needs_go
def test_missing_entry_point_scores_zero():
    assert score("package main\nfunc Other() {}")["reward"] == 0


@needs_go
def test_defining_main_scores_zero():
    assert score(CORRECT_SPLIT + "\nfunc main() {}\n")["reward"] == 0


@needs_go
def test_wrong_signature_scores_zero():
    assert score("package main\nfunc SplitBalanced(xs []int) [][]int { return nil }\n")["reward"] == 0


@needs_go
def test_a_package_other_than_main_scores_zero():
    assert score(CORRECT_SPLIT.replace("package main", "package solution"))["reward"] == 0


# --- cheating cases (all score 0) ----------------------------------------------------------------

@parametrize("sandbox", SANDBOXES)
def test_exit_in_init_scores_zero(sandbox):
    res = score(inject('import "os"', "func init() { os.Exit(0) }"), sandbox=sandbox)
    assert res["reward"] == 0 and res["reason"] != "compile error"  # it compiled and ran, and still scored 0


@parametrize("sandbox", SANDBOXES)
def test_exit_inside_the_function_scores_zero(sandbox):
    code = 'package main\nimport "os"\nfunc SplitBalanced(xs []int, parts int) ([][]int, error) { os.Exit(0); return nil, nil }\n'
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0 and res["reason"] != "compile error"


@parametrize("sandbox", SANDBOXES)
def test_a_panic_in_the_function_scores_zero(sandbox):
    code = 'package main\nfunc SplitBalanced(xs []int, parts int) ([][]int, error) { panic("x") }\n'
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0 and res["reason"] != "compile error"


@parametrize("sandbox", SANDBOXES)
def test_printing_the_expected_output_does_not_help(sandbox):
    code = inject('import "fmt"', 'func init() { fmt.Println("PASSED") }').replace("pos += size", "pos += size\n\t\tfmt.Println(\"[[1 2 3] [4 5]]\")")
    res = score(code.replace("chunk := make([]int, size)", "chunk := make([]int, size+1)"), sandbox=sandbox)  # wrong on purpose
    assert res["reward"] == 0 and res["reason"] != "compile error"


@parametrize("sandbox", SANDBOXES)
def test_hard_coding_the_visible_examples_fails_the_hidden_ones(sandbox):
    code = textwrap.dedent('''
        package main
        import ("errors"; "reflect")
        func SplitBalanced(xs []int, parts int) ([][]int, error) {
            if parts == 2 && reflect.DeepEqual(xs, []int{1,2,3,4,5}) { return [][]int{{1,2,3},{4,5}}, nil }
            if parts == 5 && reflect.DeepEqual(xs, []int{1,2,3}) { return [][]int{{1},{2},{3},{},{}}, nil }
            return nil, errors.New("no")
        }''')
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0 and res["visible_passed"] == "3/3"


@parametrize("sandbox", SANDBOXES)
def test_a_forged_result_file_cannot_match_unknown_answers(sandbox):
    # Writes a results.json of the right length that claims one fixed answer for every case, then exits with code 0.
    code = textwrap.dedent('''
        package main
        import ("encoding/json"; "os"; "strings")
        func init() {
            raw, _ := os.ReadFile("cases.json")
            var cases []json.RawMessage
            json.Unmarshal(raw, &cases)
            items := make([]string, len(cases))
            for i := range items { items[i] = `{"ok":true,"value":[[1,2,3],[4,5]]}` }
            os.WriteFile("results.json", []byte("["+strings.Join(items, ",")+"]"), 0o644)
            os.Exit(0)
        }
        func SplitBalanced(xs []int, parts int) ([][]int, error) { return nil, nil }''')
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0 and res["passed"] <= 1 and res["reason"] != "compile error"  # at most the one case it guessed


@parametrize("sandbox", SANDBOXES)
def test_an_infinite_loop_times_out_and_returns(sandbox):
    code = 'package main\nfunc SplitBalanced(xs []int, parts int) ([][]int, error) { for {} }\n'
    res = score(code, sandbox=sandbox)
    assert res["reward"] == 0
    assert res["seconds"] < 25


@parametrize("sandbox", SANDBOXES)
def test_an_infinite_loop_at_init_times_out(sandbox):
    res = score(inject(extra="func init() { for {} }"), sandbox=sandbox)
    assert res["reward"] == 0 and res["reason"] == "timeout"


@skipif(not _docker_ready(), reason="docker or the Go image is missing")
def test_docker_has_no_network():
    code = textwrap.dedent('''
        package main
        import ("net"; "time")
        func SplitBalanced(xs []int, parts int) ([][]int, error) {
            c, err := net.DialTimeout("tcp", "1.1.1.1:80", time.Second)
            if err == nil { c.Close(); panic("network reachable") }
            return [][]int{}, nil
        }''')
    # the function never leaks the answer either way; what matters is that it cannot reach out
    assert score(code, sandbox="docker")["reward"] == 0


@needs_go
def test_the_sandbox_folder_holds_inputs_only_no_expected_values():
    seen = {}

    def spy(workdir, task_time_s):
        seen["files"] = sorted(p.name for p in workdir.iterdir())
        seen["cases"] = (workdir / "cases.json").read_text(encoding="utf-8")
        return "stop"

    gv.reward(SPLIT, fence(CORRECT_SPLIT), spy)
    assert seen["files"] == ["cases.json", "entry.go", "go.mod", "runner.go", "solution.go"]
    assert "expected" not in seen["cases"] and "raises" not in seen["cases"]
    assert not any("reference" in f for f in seen["files"])


@needs_go
def test_result_file_with_the_wrong_shape_is_zero():
    def fake(workdir, task_time_s):
        (workdir / "results.json").write_text('{"ok": true}')
        return None

    assert gv.reward(SPLIT, fence(CORRECT_SPLIT), fake)["reason"] == "result file has the wrong shape"


@needs_go
def test_missing_result_file_is_zero():
    assert gv.reward(SPLIT, fence(CORRECT_SPLIT), lambda w, t: None)["reason"] == "no readable result file"


# --- the lint ------------------------------------------------------------------------------------

def _copy_task(tmp_path: Path) -> Path:
    dst = tmp_path / "split_balanced"
    shutil.copytree(SPLIT, dst)
    return dst


@needs_go
def test_lint_catches_a_wrong_reference(tmp_path):
    t = _copy_task(tmp_path)
    (t / "reference.go").write_text(WRONG["split_balanced"])
    assert any("reference solution does not score 1" in p for p in gv.check_task(t))


def test_lint_catches_source_not_original_and_a_wrong_language(tmp_path):
    t = _copy_task(tmp_path)
    meta = json.loads((t / "task.json").read_text())
    meta["source"], meta["language"] = "HumanEval/12", "python"
    (t / "task.json").write_text(json.dumps(meta))
    problems = gv.check_task(t)
    assert any("original" in p for p in problems) and any("language" in p for p in problems)


def test_lint_catches_a_hidden_call_copied_into_the_prompt(tmp_path):
    t = _copy_task(tmp_path)
    (t / "prompt.md").write_text((t / "prompt.md").read_text() + "\nSplitBalanced([1, 2, 3, 4], 2)\n")
    assert any("hidden test call appears" in p for p in gv.check_task(t))


def test_lint_catches_a_hidden_call_copied_in_go_style(tmp_path):
    t = _copy_task(tmp_path)
    (t / "prompt.md").write_text((t / "prompt.md").read_text() + "\n`SplitBalanced([]int{1, 2, 3, 4}, 2)` returns two pairs.\n")
    assert any("hidden test call appears" in p for p in gv.check_task(t))


@needs_go
def test_lint_accepts_a_prompt_that_only_shows_visible_calls(tmp_path):
    t = _copy_task(tmp_path)
    assert not any("hidden test call appears" in p for p in gv.check_task(t))


@skipif(not _docker_ready(), reason="docker or the Go image is missing")
def test_a_missing_docker_image_raises_and_is_not_scored_as_a_compile_error(monkeypatch):
    monkeypatch.setattr(gv, "GO_IMAGE", "g10-go-rl-does-not-exist:0")
    with pytest.raises(RuntimeError, match="docker sandbox failed"):
        score(CORRECT_SPLIT, sandbox="docker")


def test_lint_catches_a_bad_raises_value(tmp_path):
    t = _copy_task(tmp_path)
    cases = json.loads((t / "hidden_tests.json").read_text())
    cases[-1] = {"args": [[1], 0], "raises": "ValueError"}
    (t / "hidden_tests.json").write_text(json.dumps(cases))
    assert any('"raises" must be' in p for p in gv.check_task(t))


def test_lint_catches_too_few_hidden_tests(tmp_path):
    t = _copy_task(tmp_path)
    cases = json.loads((t / "hidden_tests.json").read_text())[:5]
    (t / "hidden_tests.json").write_text(json.dumps(cases))
    assert any("at least 10 hidden" in p for p in gv.check_task(t))


@needs_go
def test_cli_reward(tmp_path):
    comp = tmp_path / "c.txt"
    comp.write_text(fence(CORRECT_SPLIT))
    out = subprocess.run([sys.executable, str(HERE / "go_verifier.py"), "--reward", str(SPLIT), str(comp)],
                         capture_output=True, text=True)
    assert json.loads(out.stdout)["reward"] == 1


def test_cli_names_a_missing_task_folder_instead_of_a_traceback(tmp_path):
    comp = tmp_path / "c.txt"
    comp.write_text(fence(CORRECT_SPLIT))
    for cmd in (["--reward", str(tmp_path / "nope"), str(comp)], ["--check-task", str(tmp_path / "nope")]):
        out = subprocess.run([sys.executable, str(HERE / "go_verifier.py"), *cmd], capture_output=True, text=True)
        assert out.returncode == 2 and "not found" in out.stderr and "Traceback" not in out.stderr
