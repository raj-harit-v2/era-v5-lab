"""Run an authored Hindi text-preparation SWE task and save measured evidence.

The seeded bug follows the pre-tokenization rule in special_tokens_v1.md literally
(NFKC plus removal of U+200B..U+200D). The fail/fix/pass exercise changes only a
temporary copy of the task. It is neither a SWE-bench evaluation nor model training.
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
TARGET = "swe-task/hindi_text_prep.py"
SUITE = "test_hindi_text_prep.py"
EFFORTS = ("1k", "4k", "16k", "64k")
# (correct, seeded bug) source pairs; the repair is the reverse of the seeding.
HUNKS = (
    ("from __future__ import annotations\n",
     "from __future__ import annotations\n\nimport unicodedata\n"),
    ('STRIP = frozenset({"\\u200b", "\\ufeff"})',
     'STRIP = frozenset({"\\u200b", "\\u200c", "\\u200d", "\\ufeff"})'),
    ('    return "".join(ch for ch in text if ch not in STRIP)',
     '    return "".join(ch for ch in unicodedata.normalize("NFKC", text) if ch not in STRIP)'),
)
SAMPLE = "\u0915\u094d\u200d\u0937 \u0915\u094d\u200c\u0937 \u095b\u093f\u0902\u0926\u0917\u0940 10\u00b2 \u0935\u0930\u094d\u0917 \u092e\u0940\u091f\u0930\u0964"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_tests(task_root: Path) -> dict:
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", SUITE, "-v"]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        command, cwd=task_root, capture_output=True, text=True, encoding="utf-8", env=environment,
    )
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def as_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def code_points(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    arguments = parser.parse_args()
    output_dir = arguments.output_dir or Path(tempfile.mkdtemp(prefix="g10-hindi-evidence-"))
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = load_module("g10_hindi_renderer", TEAM / "chat-format" / "render.py")
    original = (TEAM / TARGET).read_text(encoding="utf-8")
    for good, _ in HUNKS:
        assert original.count(good) == 1, f"expected one occurrence of {good!r}"

    with tempfile.TemporaryDirectory(prefix="g10-hindi-task-") as directory:
        task_root = Path(directory)
        for sub in ("swe-task", "tests", "chat-format"):
            (task_root / sub).mkdir()
        shutil.copy2(TEAM / "tests" / SUITE, task_root / "tests")
        shutil.copy2(TEAM / "chat-format" / "render.py", task_root / "chat-format")
        target = task_root / TARGET
        seeded = original
        for good, bad in HUNKS:
            seeded = seeded.replace(good, bad)
        target.write_text(seeded, encoding="utf-8")

        # These observations are read from the actual temporary task and processes.
        before_source = target.read_text(encoding="utf-8")
        baseline = run_tests(task_root)
        assert baseline["returncode"] == 1, baseline
        assert "Ran 6 tests" in baseline["stderr"], baseline
        assert "FAILED (failures=4)" in baseline["stderr"], baseline

        buggy = load_module("g10_hindi_buggy_prep", target)
        damaged = buggy.prepare_text(SAMPLE)

        patch = {"path": TARGET, "hunks": [{"old": bad, "new": good} for good, bad in HUNKS]}
        patched_source = before_source
        for hunk in patch["hunks"]:
            patched_source = patched_source.replace(hunk["old"], hunk["new"])
        assert patched_source == original
        target.write_text(patched_source, encoding="utf-8")
        patch_result = {
            "path": TARGET, "changed": patched_source != before_source,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
        passing = run_tests(task_root)
        assert passing["returncode"] == 0, passing
        assert "Ran 6 tests" in passing["stderr"] and "OK" in passing["stderr"], passing

        fixed = load_module("g10_hindi_fixed_prep", target).prepare_text(SAMPLE)
        assert fixed == SAMPLE and damaged != SAMPLE
        sample_check = {
            "input": code_points(SAMPLE), "seeded_bug_output": code_points(damaged),
            "patched_output": code_points(fixed),
        }

        messages = [
            {"role": "system", "content": "आप कोड ठीक करते हैं और केवल वही बताते हैं जो टूल ने लौटाया। हिंदी पाठ को अक्षरशः सुरक्षित रखें।"},
            {"role": "user", "content": "टोकनाइज़र से पहले prepare_text() हिंदी के संयुक्ताक्षर और नुक़्ता बदल देता है। कारण खोजकर ठीक करें और टेस्ट चलाएँ।"},
            {"role": "assistant", "think": "पहले फ़ाइल पढ़नी होगी, फिर टेस्ट चलाकर देखूँगा कि क्या टूटता है।",
             "tool_calls": [{"name": "read_file", "arguments": {"path": TARGET}}]},
            {"role": "tool", "content": before_source},
            {"role": "assistant", "tool_calls": [{"name": "run_tests", "arguments": {"suite": SUITE}}]},
            {"role": "tool", "content": as_json(baseline)},
            {"role": "assistant",
             "think": "NFKC 10² को 102 बना देता है और क़ को क + ़ में तोड़ देता है। U+200C/U+200D हटाने से क्‍ष का आधा रूप खो जाता है। केवल U+200B और U+FEFF हटाने चाहिए।",
             "tool_calls": [{"name": "apply_patch", "arguments": patch}]},
            {"role": "tool", "content": as_json(patch_result)},
            {"role": "assistant", "tool_calls": [{"name": "run_tests", "arguments": {"suite": SUITE}}]},
            {"role": "tool", "content": as_json(passing)},
            {"role": "assistant", "content": "NFKC और ZWJ/ZWNJ हटाना बंद किया; अब केवल U+200B और U+FEFF हटते हैं। छह में से छह टेस्ट पास हुए, और शून्य-चौड़ाई स्पेस से छिपाया गया think मार्कर अब भी अस्वीकार होता है।"},
        ]
        transcripts = {}
        for effort in EFFORTS:
            transcripts[effort] = renderer.render(messages, effort=effort)
            assert renderer.parse(transcripts[effort]) == {"effort": effort, "messages": messages}
        transcript = transcripts["4k"]
        special_ids = sorted({value for kind, value in renderer.tokenize_markers(transcript) if kind == "special"})
        assert special_ids == [129994, 130773, 130774, 130816, 130822, 130823, 130824, 130825, 130826]

        summary = {
            "task": "authored Hindi text-preparation SWE task",
            "execution": "Python subprocesses inside the runner; no model execution",
            "python_version": platform.python_version(),
            "baseline_returncode": baseline["returncode"],
            "baseline_tests": 6,
            "baseline_failures": 4,
            "patched_returncode": passing["returncode"],
            "patched_tests": 6,
            "patched_failures": 0,
            "trajectory_turns": len(messages),
            "efforts_roundtripped": list(EFFORTS),
            "exact_render_parse_roundtrip": True,
            "marker_scan": "synthetic surface scanner only; actual G3 tokenizer not tested",
            "marker_ids_observed": special_ids,
            "patched_file_sha256": patch_result["sha256"],
            "sample_code_points": sample_check,
        }
        (output_dir / "baseline.log").write_text(baseline["stdout"] + baseline["stderr"], encoding="utf-8")
        (output_dir / "patched.log").write_text(passing["stdout"] + passing["stderr"], encoding="utf-8")
        (output_dir / "trajectory.json").write_text(as_json({"effort": "4k", "messages": messages}) + "\n", encoding="utf-8")
        (output_dir / "trajectory.chatml.txt").write_text(transcript, encoding="utf-8")
        (output_dir / "summary.json").write_text(as_json(summary) + "\n", encoding="utf-8")

    print(as_json(summary))
    print(f"Evidence written to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
