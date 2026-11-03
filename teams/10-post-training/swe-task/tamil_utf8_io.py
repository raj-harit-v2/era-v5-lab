"""Write Tamil and other Unicode text without changing its code points."""

from __future__ import annotations

from pathlib import Path


def write_utf8_text(path: str | Path, text: str) -> None:
    """Write exact UTF-8 text, preserving joiners and newline sequences."""
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)
