"""Kannada serialization checks; browser glyph approval is a separate review."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import unittest

TEAM = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDER = load_module("kannada_renderer", TEAM / "chat-format" / "render.py")
EXAMPLES = load_module("kannada_chat_examples", TEAM / "swe-task" / "kannada_examples.py")


class KannadaChatFormatTests(unittest.TestCase):
    def test_kannada_joiner_sequences_roundtrip_every_field_at_every_effort(self):
        self.assertEqual(tuple(map(ord, EXAMPLES.ONEPLUS)), (
            0x0C92, 0x0CA8, 0x0CCD, 0x200C, 0x0CAA,
            0x0CCD, 0x0CB2, 0x0CB8, 0x0CCD))
        for text, points in (
            (EXAMPLES.RA_DEFAULT, (0x0CB0, 0x0CCD, 0x0C95)),
            (EXAMPLES.RA_UNICODE, (0x0CB0, 0x200D, 0x0CCD, 0x0C95)),
            (EXAMPLES.RA_LEGACY, (0x0CB0, 0x0CCD, 0x200D, 0x0C95)),
        ):
            self.assertEqual(tuple(map(ord, text)), points)
        self.assertNotEqual(EXAMPLES.RA_UNICODE, EXAMPLES.RA_LEGACY)
        self.assertEqual(
            [text for _, text in EXAMPLES.CASES if "\u200c" in text],
            [EXAMPLES.ONEPLUS])
        for label, text in EXAMPLES.CASES:
            messages = EXAMPLES.preservation_messages(text)
            for effort in EXAMPLES.EFFORTS:
                transcript = RENDER.render(messages, effort=effort)
                restored = transcript.encode("utf-8").decode("utf-8")
                self.assertEqual(RENDER.parse(restored), {
                    "effort": effort, "messages": messages}, (label, effort))
                ids = {value for kind, value in RENDER.tokenize_markers(transcript)
                       if kind == "special"}
                self.assertEqual(ids, {129994, 130773, 130774, 130816, 130822, 130823, 130824, 130825, 130826})

    def test_documented_input_and_transcript_match_renderer(self):
        chat = (TEAM / "chat-format" / "chat_format_v0.md").read_text(encoding="utf-8")
        section = chat.split("## Kannada application", 1)[1]
        code = section.split("```python\n", 1)[1].split("```", 1)[0]
        namespace = {}
        previous_directory = Path.cwd()
        try:
            os.chdir(TEAM.parents[1])  # The example documents repository-root execution.
            exec(compile(code, "Kannada documentation example", "exec"), namespace)
        finally:
            os.chdir(previous_directory)
        self.assertEqual(namespace["messages"], EXAMPLES.demo_messages())
        shown = section.split("```text\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(shown, namespace["text"])


if __name__ == "__main__":
    unittest.main()
