"""Run an authored Kannada SWE fail/patch/pass task using temporary copies only."""

from __future__ import annotations

import argparse
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
TARGET = "swe-task/kannada_text_prep.py"
SUITE = "test_kannada_text_prep.py"
HUNKS = (
    ("from __future__ import annotations\n",
     "from __future__ import annotations\n\nimport unicodedata\n"),
    ('STRIP = frozenset({"\\u200b", "\\ufeff"})',
     'STRIP = frozenset({"\\u200b", "\\u200c", "\\u200d", "\\ufeff"})'),
    ('    return "".join(ch for ch in text if ch not in STRIP)',
     '    return "".join(ch for ch in unicodedata.normalize("NFKC", text) if ch not in STRIP)'),
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def as_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def run_tests(root: Path) -> dict:
    # Count actual unittest results, including import/setup errors. No log regexes
    # or assumed test counts can turn a broken test harness into a successful repair.
    program = '''import json, sys, unittest
suite = unittest.defaultTestLoader.discover("tests", pattern=sys.argv[1])
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({"tests": result.testsRun, "failures": len(result.failures),
                  "errors": len(result.errors), "skipped": len(result.skipped),
                  "failed_tests": [str(test) for test, _ in result.failures]}))
sys.exit(0 if result.wasSuccessful() else 1)
'''
    result = subprocess.run(
        [sys.executable, "-B", "-c", program, SUITE], cwd=root,
        capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=60,
    )
    record = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    try:
        record["counts"] = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"test harness did not return measured counts: {record}") from exc
    return record


def code_points(text: str) -> str:
    return " ".join(f"U+{ord(ch):04X}" for ch in text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path(tempfile.mkdtemp(prefix="g10-kannada-evidence-"))
    output.mkdir(parents=True, exist_ok=True)
    renderer = load_module("kannada_swe_renderer", TEAM / "chat-format" / "render.py")
    examples = load_module("kannada_swe_examples", TEAM / "swe-task" / "kannada_examples.py")
    original_bytes = (TEAM / TARGET).read_bytes()
    original = original_bytes.decode("utf-8")
    for good, _ in HUNKS:
        assert original.count(good) == 1, f"expected one source hunk: {good!r}"

    with tempfile.TemporaryDirectory(prefix="g10-kannada-task-") as directory:
        root = Path(directory)
        for sub in ("swe-task", "tests", "chat-format"):
            (root / sub).mkdir()
        for relative in (f"tests/{SUITE}", "chat-format/render.py", "swe-task/kannada_examples.py"):
            shutil.copy2(TEAM / relative, root / relative)
        target = root / TARGET
        seeded = original
        for good, bad in HUNKS:
            seeded = seeded.replace(good, bad)
        target.write_text(seeded, encoding="utf-8")
        baseline = run_tests(root)
        (output / "baseline.log").write_text(baseline["stdout"] + baseline["stderr"], encoding="utf-8")
        counts = baseline["counts"]
        assert baseline["returncode"] == 1 and counts["failures"] > 0, baseline
        assert counts["tests"] > 0 and counts["errors"] == counts["skipped"] == 0, baseline
        buggy = load_module("kannada_swe_buggy", target)

        patch = {"path": TARGET, "hunks": [{"old": bad, "new": good} for good, bad in HUNKS]}
        repaired = seeded
        for hunk in patch["hunks"]:
            assert repaired.count(hunk["old"]) == 1
            repaired = repaired.replace(hunk["old"], hunk["new"])
        assert repaired == original
        target.write_text(repaired, encoding="utf-8")
        patch_result = {"path": TARGET, "changed": repaired != seeded}
        passing = run_tests(root)
        (output / "patched.log").write_text(passing["stdout"] + passing["stderr"], encoding="utf-8")
        assert passing["returncode"] == 0, passing
        assert passing["counts"]["tests"] == counts["tests"]
        assert passing["counts"]["failures"] == passing["counts"]["errors"] == 0
        assert passing["counts"]["skipped"] == 0
        fixed = load_module("kannada_swe_fixed", target)
        samples = []
        for label, text in examples.CASES:
            restored = fixed.prepare_text(text)
            assert restored == text
            samples.append({"label": label, "input": code_points(text),
                            "seeded_output": code_points(buggy.prepare_text(text)),
                            "repaired_output": code_points(restored)})

        messages = [
            {"role": "system", "content": "ಕನ್ನಡ ಪಠ್ಯವನ್ನು ಬದಲಿಸಬೇಡಿ. ಪರೀಕ್ಷೆಯ ಫಲಿತಾಂಶವನ್ನು ತಿಳಿಸಿ."},
            {"role": "user", "content": "ಪಠ್ಯ ಸಿದ್ಧಪಡಿಸುವ ಕೋಡ್ ಪರಿಶೀಲಿಸಿ. ಪರೀಕ್ಷೆಗಳನ್ನು ಚಲಾಯಿಸಿ."},
            {"role": "assistant", "think": "ಮೊದಲು ಕೋಡ್ ಮತ್ತು ಪರೀಕ್ಷೆಯ ಫಲಿತಾಂಶವನ್ನು ಪರಿಶೀಲಿಸಬೇಕು.",
             "tool_calls": [{"name": "read_file", "arguments": {"path": TARGET}}]},
            {"role": "tool", "content": seeded},
            {"role": "assistant", "tool_calls": [{"name": "run_tests", "arguments": {"suite": SUITE}}]},
            {"role": "tool", "content": as_json(baseline)},
            {"role": "assistant", "think": "ZWJ ಮತ್ತು ZWNJ ಉಳಿಯಬೇಕು. RA ಕ್ರಮವನ್ನು ಬದಲಿಸಬಾರದು.",
             "tool_calls": [{"name": "apply_patch", "arguments": patch}]},
            {"role": "tool", "content": as_json(patch_result)},
            {"role": "assistant", "tool_calls": [{"name": "run_tests", "arguments": {"suite": SUITE}}]},
            {"role": "tool", "content": as_json(passing)},
            {"role": "assistant", "content": "ಕೋಡ್ ಸರಿಪಡಿಸಲಾಗಿದೆ. "
             + f"{passing['counts']['tests']} tests passed."},
        ]
        transcripts = {}
        for effort in examples.EFFORTS:
            transcripts[effort] = renderer.render(messages, effort=effort)
            assert renderer.parse(transcripts[effort]) == {"effort": effort, "messages": messages}
        ids = sorted({value for kind, value in renderer.tokenize_markers(transcripts["4k"])
                      if kind == "special"})
        assert ids == [129994, 130773, 130774, 130816, 130822, 130823, 130824, 130825, 130826]
        assert (TEAM / TARGET).read_bytes() == original_bytes
        summary = {
            "task": "authored Kannada text-preparation SWE task",
            "execution": "Python subprocesses; no model execution or SWE-bench score",
            "python_version": platform.python_version(),
            "baseline": {"returncode": baseline["returncode"], **counts},
            "repaired": {"returncode": passing["returncode"], **passing["counts"]},
            "efforts_roundtripped": list(examples.EFFORTS), "trajectory_turns": len(messages),
            "exact_render_parse_roundtrip": True, "marker_ids_observed": ids,
            "marker_scan": "synthetic scanner; actual G3 tokenizer unverified",
            "checked_in_helper_unchanged": True,
            "sample_code_points": samples, "visual_review": "pending separate browser review",
        }
        (output / "trajectory.json").write_text(as_json({"effort": "4k", "messages": messages}) + "\n", encoding="utf-8")
        (output / "trajectory.chatml.txt").write_text(transcripts["4k"], encoding="utf-8")
        (output / "summary.json").write_text(as_json(summary) + "\n", encoding="utf-8")

    preview = load_module("kannada_swe_preview", TEAM / "swe-task" / "preview_kannada.py")
    preview.generate_preview(output / "kannada_browser_preview.html")
    print(as_json(summary))
    print(f"Evidence written to: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
