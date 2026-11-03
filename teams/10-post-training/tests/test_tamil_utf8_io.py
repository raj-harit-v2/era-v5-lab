"""Regression cases for Tamil text preservation, using only the standard library."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


TEAM = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "tamil_utf8_io", TEAM / "swe-task" / "tamil_utf8_io.py"
)
assert SPEC is not None and SPEC.loader is not None
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


class TamilUTF8Tests(unittest.TestCase):
    def assert_exact_file(self, text: str) -> None:
        with tempfile.TemporaryDirectory(prefix="tamil-utf8-test-") as directory:
            target = Path(directory) / "தமிழ்.txt"
            HELPER.write_utf8_text(target, text)
            actual = target.read_bytes()
            self.assertEqual(actual, text.encode("utf-8"))
            self.assertEqual(actual.decode("utf-8"), text)

    def test_tamil_text_survives_without_loss(self) -> None:
        self.assert_exact_file("வணக்கம்! தமிழ் மொழி. Tamil 123\n")

    def test_combining_sequences_are_not_normalized(self) -> None:
        # U+0B95 U+0BC6 U+0BBE and U+0B95 U+0BCA render similarly.
        decomposed = "\u0b95\u0bc6\u0bbe"
        composed = "\u0b95\u0bca"
        self.assertNotEqual(decomposed, composed)
        self.assert_exact_file(decomposed + " | " + composed)

    def test_zwj_and_zwnj_are_preserved(self) -> None:
        self.assert_exact_file("க்\u200dக | க்\u200cக")

    def test_mixed_newline_sequences_are_preserved(self) -> None:
        self.assert_exact_file("வரி ஒன்று\r\nவரி இரண்டு\nவரி மூன்று\rஇறுதி\n\n")


if __name__ == "__main__":
    unittest.main()
