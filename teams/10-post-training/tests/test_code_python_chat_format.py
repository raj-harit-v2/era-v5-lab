"""code-python cases for chat_format_v0: Python source and StarCoder tags through render.py (no Docker)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

TEAM = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("g10_render_code_python", TEAM / "chat-format" / "render.py")
assert SPEC is not None and SPEC.loader is not None
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)

STARCODER_TAGS = ("<reponame>", "<filename>", "<gh_stars>", "<NAME>", "<EMAIL>", "<PASSWORD>", "<KEY>")


def roundtrip(messages: list[dict]) -> dict:
    return R.parse(R.render(messages, effort="4k"))


class CodePythonChatFormatTests(unittest.TestCase):
    def test_python_source_survives_exactly(self) -> None:
        src = (
            "@dataclass\r\nclass Point:\r\n\tx: int\r\n\r\n"
            "def norm(p: Point) -> float:\r\n    return (p.x ** 2) ** 0.5  # x < 10 and x > -10\r\n"
            'msg = f"{p.x!r:>8}"\r\n'
        )
        call = {"name": "apply_patch", "arguments": {"path": "geo.py", "new": "\tif a <= b >= c:\n\t\treturn {'k': [1, 2]}\n"}}
        messages = [
            {"role": "user", "content": src},
            {"role": "assistant", "tool_calls": [call]},
            {"role": "tool", "content": src},
        ]
        self.assertEqual(roundtrip(messages)["messages"], messages)

    def test_starcoder_tags_and_pii_placeholders_stay_plain_text(self) -> None:
        text = (
            "<reponame>org/repo<filename>app/settings.py<gh_stars>10\n"
            'AUTHOR = "<NAME>"\nCONTACT = "<EMAIL>"\nTOKEN = "<KEY>"\npassword=<PASSWORD>,\n'
        )
        messages = [{"role": "user", "content": "fix"}, {"role": "tool", "content": text}]
        rendered = R.render(messages, effort="4k")
        self.assertEqual(R.parse(rendered)["messages"], messages)
        pieces = R.tokenize_markers(rendered)
        special = [R.ASSIGNED[value] for kind, value in pieces if kind == "special"]
        # Only the turn structure is special; no StarCoder tag or placeholder became a special token.
        self.assertEqual(special, ["im_start", "im_end", "im_start", "im_end", "im_start", "tool_result", "tool_result_end", "im_end", "endoftext"])
        plain = "".join(value for kind, value in pieces if kind == "text")
        for tag in STARCODER_TAGS:
            self.assertIn(tag, plain)

    def test_chat_markers_inside_python_strings_are_rejected(self) -> None:
        for literal in ('s = "<|im_start|>"', 's = "<|tool_call|>"', 's = "<|endoftext|>"', 's = "<think>"', "s = '<tool_result>'"):
            with self.assertRaises(R.RenderError):
                R.render([{"role": "user", "content": literal}], effort="4k")

    def test_docs_record_the_code_python_findings(self) -> None:
        chat = (TEAM / "chat-format" / "chat_format_v0.md").read_text(encoding="utf-8")
        tokens = (TEAM / "special-tokens" / "special_tokens_v0.md").read_text(encoding="utf-8")
        licence = (TEAM / "licences" / "licence_table.md").read_text(encoding="utf-8")
        self.assertIn("## Python application: `code-python`", chat)
        excerpt = chat.split("## Python application: `code-python`", 1)[1].split("```text\n", 1)[1].split("```", 1)[0]
        messages = [
            {"role": "user", "content": "test_dsn fails in settings.py. Read it first."},
            {"role": "assistant", "tool_calls": [{"name": "read_file", "arguments": {"path": "settings.py"}}]},
            {"role": "tool", "content": 'DB_USER = "<NAME>"\nDB_EMAIL = "<EMAIL>"\n\n\ndef dsn(host: str) -> str:\n    return f"{DB_USER}@{host}"\n'},
        ]
        self.assertIn(excerpt, R.render(messages, effort="4k"))  # the doc excerpt is real renderer output
        section = tokens.split("f20201351h-maker — StarCoder", 1)[1].split("\n### ", 1)[0]
        for fact in ("in all 500 documents", "272 of 500", "83 of 500", "No new token request"):
            self.assertIn(fact, section)
        for doc_id in ("890651e4733e8944", "bcb288906f19d84d", "da1e1a24ce2d8184", "1ba7834883790ea6",
                       "b722cf3b05cb227a", "e2c3db81526c288d", "6fbbb7afb4c34553", "0f044ee517526307"):
            self.assertIn(doc_id, licence)


if __name__ == "__main__":
    unittest.main()
