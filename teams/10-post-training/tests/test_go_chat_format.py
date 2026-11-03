"""Go-specific cases for chat_format_v0 and the Go SWE task files (standard library only, no Docker)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

TEAM = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("g10_render_go", TEAM / "chat-format" / "render.py")
assert SPEC is not None and SPEC.loader is not None
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)

GO_DIR = TEAM / "swe-task-go"


def roundtrip(messages: list[dict]) -> dict:
    return R.parse(R.render(messages, effort="4k"))


class GoChatFormatTests(unittest.TestCase):
    def test_tabs_crlf_and_channel_operator_survive(self) -> None:
        src = "package x\r\n\r\nfunc f(ch chan int) int {\r\n\treturn <-ch\r\n}\r\n"
        messages = [{"role": "user", "content": "fix"}, {"role": "tool", "content": src}]
        self.assertEqual(roundtrip(messages)["messages"], messages)

    def test_go_source_in_tool_call_json_survives(self) -> None:
        call = {"name": "apply_patch", "arguments": {"path": "a.go", "new": "\tx := `raw`\n\ty <<= 2\n"}}
        messages = [
            {"role": "user", "content": "patch"},
            {"role": "assistant", "content": "", "tool_calls": [call]},
            {"role": "tool", "content": "ok"},
        ]
        parsed = roundtrip(messages)["messages"]
        self.assertEqual(parsed[1]["tool_calls"][0]["arguments"], call["arguments"])

    def test_literal_control_markers_in_go_strings_are_rejected(self) -> None:
        for literal in ('s := "<|im_start|>"', 's := "<|tool_call|>"', 's := "<think>"'):
            with self.assertRaises(R.RenderError):
                R.render([{"role": "user", "content": literal}], effort="4k")

    def test_starcoder_metadata_markers_are_plain_text_to_the_renderer(self) -> None:
        # B3 markers are removed by the cleaning medicine; the renderer treats them as ordinary text.
        text = "<reponame>a/b<filename>x.go\npackage x\n"
        messages = [{"role": "user", "content": text}]
        self.assertEqual(roundtrip(messages)["messages"], messages)

    def test_go_task_files_are_present_and_seeded_with_the_bug(self) -> None:
        for name in ("go.mod", "stats.go", "stats_test.go", "Dockerfile", "run_e2e_go.py"):
            self.assertTrue((GO_DIR / name).exists(), name)
        src = (GO_DIR / "stats.go").read_text(encoding="utf-8")
        self.assertIn("for i := 1; i < len(nums); i++ {", src)
        self.assertIn("\t", src)  # gofmt style tabs


if __name__ == "__main__":
    unittest.main()
