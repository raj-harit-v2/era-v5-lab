"""Isolated Kannada SWE demonstration, not a hook in the shared renderer.

Remove only ZWSP/BOM before marker checking and preserve all other code points.
"""

from __future__ import annotations

STRIP = frozenset({"\u200b", "\ufeff"})


def prepare_text(text: str) -> str:
    """Keep every code point except the two explicitly declared controls."""
    return "".join(ch for ch in text if ch not in STRIP)
