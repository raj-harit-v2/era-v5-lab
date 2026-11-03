"""Prepare Hindi (Devanagari) text for the tokenizer without changing what it says."""

from __future__ import annotations

# Only invisible characters with no meaning in Devanagari are removed.
# ZWJ (U+200D) and ZWNJ (U+200C) choose between a conjunct and a half form, so they stay.
STRIP = frozenset({"\u200b", "\ufeff"})


def prepare_text(text: str) -> str:
    """Remove zero-width spaces and BOMs; keep every other code point as written."""
    return "".join(ch for ch in text if ch not in STRIP)
