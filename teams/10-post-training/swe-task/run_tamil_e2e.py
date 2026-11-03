"""Run an authored local UTF-8 SWE smoke task and save measured evidence.

The fail/fix/pass exercise changes only a temporary copy of the task. It is
neither a SWE-bench evaluation nor a model training or Docker execution.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


TEAM = Path(__file__).resolve().parents[1]
UTF8 = 'encoding="utf-8"'
ASCII_BUG = 'encoding="ascii", errors="ignore"'
EXAMPLE = "வணக்கம்! தமிழ் மொழி.\nகொ | கொ\nக்\u200dக | க்\u200cக\r\n"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_tests(task_root: Path) -> dict:
    command = [
        sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
        "-p", "test_tamil_utf8_io.py", "-v",
    ]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        command, cwd=task_root, capture_output=True, text=True,
        encoding="utf-8", env=environment,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def as_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    arguments = parser.parse_args()
    output_dir = arguments.output_dir or Path(tempfile.mkdtemp(prefix="g10-tamil-evidence-"))
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = load_module("g10_tamil_renderer", TEAM / "chat-format" / "render.py")
    original = (TEAM / "swe-task" / "tamil_utf8_io.py").read_text(encoding="utf-8")
    assert original.count(UTF8) == 1, "expected one UTF-8 encoding declaration"

    with tempfile.TemporaryDirectory(prefix="g10-tamil-task-") as directory:
        task_root = Path(directory)
        (task_root / "swe-task").mkdir()
        (task_root / "tests").mkdir()
        target = task_root / "swe-task" / "tamil_utf8_io.py"
        shutil.copy2(TEAM / "tests" / "test_tamil_utf8_io.py", task_root / "tests")
        target.write_text(original.replace(UTF8, ASCII_BUG), encoding="utf-8")

        # These observations are read from the actual temporary task and processes.
        before_source = target.read_text(encoding="utf-8")
        baseline = run_tests(task_root)
        assert baseline["returncode"] == 1, baseline
        assert "Ran 4 tests" in baseline["stderr"], baseline
        assert "FAILED (failures=4)" in baseline["stderr"], baseline
        patch = {
            "path": "swe-task/tamil_utf8_io.py",
            "old": ASCII_BUG,
            "new": UTF8,
        }
        patched_source = before_source.replace(patch["old"], patch["new"])
        assert patched_source == original
        target.write_text(patched_source, encoding="utf-8")
        patch_result = {
            "path": patch["path"], "changed": patched_source != before_source,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
        passing = run_tests(task_root)
        assert passing["returncode"] == 0, passing
        assert "Ran 4 tests" in passing["stderr"] and "OK" in passing["stderr"], passing

        helper = load_module("g10_tamil_patched_helper", target)
        actual_file = task_root / "tamil_roundtrip.txt"
        helper.write_utf8_text(actual_file, EXAMPLE)
        actual_bytes = actual_file.read_bytes()
        assert actual_bytes == EXAMPLE.encode("utf-8")

        messages = [
            {"role": "system", "content": "Fix the local text writer and report measured test results. Preserve exact Unicode text."},
            {"role": "user", "content": "தமிழ் உரையை எழுதும்போது எழுத்துகள் அழிகின்றன. காரணத்தைக் கண்டறிந்து சரிசெய்து சோதனைகளை இயக்கவும்."},
            {"role": "assistant", "tool_calls": [{"name": "read_file", "arguments": {"path": patch["path"]}}]},
            {"role": "tool", "content": before_source},
            {"role": "assistant", "tool_calls": [{"name": "run_tests", "arguments": {"suite": "test_tamil_utf8_io.py"}}]},
            {"role": "tool", "content": as_json(baseline)},
            {"role": "assistant", "tool_calls": [{"name": "apply_patch", "arguments": patch}]},
            {"role": "tool", "content": as_json(patch_result)},
            {"role": "assistant", "tool_calls": [{"name": "run_tests", "arguments": {"suite": "test_tamil_utf8_io.py"}}]},
            {"role": "tool", "content": as_json(passing)},
            {"role": "assistant", "content": "ASCII முறையில் தமிழ் எழுத்துகள் நீக்கப்பட்டன. UTF-8 முறைக்கு மாற்றியபின் நான்கு சோதனைகளும் வெற்றி பெற்றன."},
        ]
        transcript = renderer.render(messages, effort="4k")
        assert renderer.parse(transcript) == {"effort": "4k", "messages": messages}
        marker_pieces = renderer.tokenize_markers(transcript)
        special_ids = sorted({value for kind, value in marker_pieces if kind == "special"})
        assert special_ids == [129994, 130773, 130774, 130816, 130822, 130825, 130826]

        summary = {
            "task": "authored local Tamil UTF-8 SWE smoke task",
            "execution": "local Python subprocess; no Docker or model execution",
            "python_version": platform.python_version(),
            "baseline_returncode": baseline["returncode"],
            "baseline_tests": 4,
            "baseline_failures": 4,
            "patched_returncode": passing["returncode"],
            "patched_tests": 4,
            "patched_failures": 0,
            "trajectory_turns": len(messages),
            "effort": "4k",
            "exact_render_parse_roundtrip": True,
            "marker_scan": "synthetic surface scanner only; actual G3 tokenizer not tested",
            "marker_ids_observed": special_ids,
            "utf8_file": "tamil_roundtrip.txt",
            "utf8_byte_count": len(actual_bytes),
            "utf8_sha256": hashlib.sha256(actual_bytes).hexdigest(),
            "exact_utf8_bytes_preserved": True,
        }
        (output_dir / "baseline.log").write_text(baseline["stdout"] + baseline["stderr"], encoding="utf-8")
        (output_dir / "patched.log").write_text(passing["stdout"] + passing["stderr"], encoding="utf-8")
        (output_dir / "trajectory.json").write_text(as_json({"effort": "4k", "messages": messages}) + "\n", encoding="utf-8")
        (output_dir / "trajectory.chatml.txt").write_text(transcript, encoding="utf-8")
        (output_dir / "summary.json").write_text(as_json(summary) + "\n", encoding="utf-8")
        (output_dir / "tamil_roundtrip.txt").write_bytes(actual_bytes)

    print(as_json(summary))
    print(f"Evidence written to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
