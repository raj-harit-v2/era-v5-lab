"""Essential Kannada text-preparation checks for the SWE demonstration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

TEAM = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREP = load_module("kannada_prep", TEAM / "swe-task" / "kannada_text_prep.py")
RENDER = load_module("kannada_prep_renderer", TEAM / "chat-format" / "render.py")
EXAMPLES = load_module("kannada_prep_examples", TEAM / "swe-task" / "kannada_examples.py")


class KannadaTextPrepTests(unittest.TestCase):
    def test_kannada_text_and_joiners_are_preserved(self):
        texts = [text for _, text in EXAMPLES.CASES]
        texts += ["\u0c95\u0cc6\u0cc2", "ಕನ್ನಡ Python 10²\r\nಮನೆ\t"]
        actual = [PREP.prepare_text(text) for text in texts]
        self.assertEqual(actual, texts)

    def test_declared_controls_are_removed_before_marker_checking(self):
        self.assertEqual(PREP.prepare_text("\ufeffಕನ್ನಡ\u200b"), "ಕನ್ನಡ")
        text = PREP.prepare_text(EXAMPLES.ONEPLUS + " <|th\u200bink|>")
        with self.assertRaises(RENDER.RenderError):
            RENDER.render([{"role": "user", "content": text}])


if __name__ == "__main__":
    unittest.main()
