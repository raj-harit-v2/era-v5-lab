"""Unit tests for the frozen tokenizer integration (Task 12 for Member A - Amit T).

Verifies that render.py and the ChatML v0 format pass all tests on Team 3's
frozen tokenizer (BrahmicTokenizer-131K v0.1).
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest
from tokenizers import Tokenizer

TEAM = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = _load("g10_render", TEAM / "chat-format" / "render.py")
verify_frozen_tokenizer = _load("g10_verify_frozen_tokenizer", TEAM / "chat-format" / "verify_frozen_tokenizer.py")


@pytest.fixture(scope="module")
def frozen_tokenizer_path():
    return verify_frozen_tokenizer.ensure_frozen_tokenizer()


@pytest.fixture(scope="module")
def frozen_tokenizer(frozen_tokenizer_path):
    return Tokenizer.from_file(str(frozen_tokenizer_path))


def test_frozen_tokenizer_sha256(frozen_tokenizer_path):
    sha = hashlib.sha256(frozen_tokenizer_path.read_bytes()).hexdigest()
    assert sha == verify_frozen_tokenizer.EXPECTED_V0_1_SHA256


def test_all_9_markers_have_exact_atomic_id(frozen_tokenizer):
    for surf, expected_id in verify_frozen_tokenizer.EXPECTED_MARKERS.items():
        enc = frozen_tokenizer.encode(surf)
        assert enc.ids == [expected_id], f"{surf} encoded as {enc.ids}, expected [{expected_id}]"


def test_base_think_token_is_not_g10_think(frozen_tokenizer):
    enc = frozen_tokenizer.encode("<think>")
    assert 130823 not in enc.ids
    assert enc.ids == [128512]  # base legacy token, distinct from <|think|> 130823


def test_plain_text_lookalikes_not_special(frozen_tokenizer):
    for tag in ("<think>", "</think>", "<tool_call>", "</tool_call>", "<｜think｜>"):
        enc = frozen_tokenizer.encode(tag)
        for special_id in verify_frozen_tokenizer.EXPECTED_MARKERS.values():
            assert special_id not in enc.ids


def test_indic_orthography_zwj_zwnj(frozen_tokenizer):
    sentences = [
        "माहिती तंत्रज्ञान आणि संगणक प्रणाली (उदा. ऱ्या)",
        "सद्‌भावना और अंतर्‌राष्ट्रीय",
        "శ్రీరస్తు శుభమస్తు - తెలుగు ఛందస్సు",
        "ಕನ್ನಡ ಸಾಹಿತ್ಯ ಸಮ್ಮೇಳನ",
        "தமிழ் செம்மொழி",
    ]
    for text in sentences:
        enc = frozen_tokenizer.encode(text)
        dec = frozen_tokenizer.decode(enc.ids, skip_special_tokens=False)
        assert text == dec


def test_render_multi_turn_roundtrip(frozen_tokenizer):
    messages = [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "How do you do?"},
        {"role": "assistant", "think": "Pondering reply.", "content": "I am doing well."},
    ]
    for effort in ("1k", "4k", "16k", "64k"):
        rendered = render.render(messages, effort=effort)
        enc = frozen_tokenizer.encode(rendered)
        dec = frozen_tokenizer.decode(enc.ids, skip_special_tokens=False)
        assert rendered == dec
        parsed = render.parse(rendered)
        assert parsed["effort"] == effort
        assert parsed["messages"] == messages
