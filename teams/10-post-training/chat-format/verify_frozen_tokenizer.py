"""Verify G10 chat format v0 on Team 3's frozen tokenizer (v0.1).

Validates:
1. Frozen tokenizer v0.1 SHA-256 is `a33c9907ec16876bc57b011714e8380879919fba1327d84bfb0d60407fe6e578`.
2. Each of the 9 active G10 markers encodes as exactly ONE atomic token with its assigned ID:
   - <|im_start|>: 129994
   - <|im_end|>: 130816
   - <|tool_call|>: 130773
   - <|tool_result|>: 130774
   - <|endoftext|>: 130822
   - <|think|>: 130823
   - <|/think|>: 130824
   - <|/tool_call|>: 130825
   - <|/tool_result|>: 130826
3. Base <think> (128512) and plain-text lookalikes (<think>, <tool_call>, <｜think｜>)
   never resolve to the atomic special tokens.
4. Rendered multi-turn conversations round-trip through encode and decode with exact fidelity.
5. Indic orthography: ZWJ (U+200D) and ZWNJ (U+200C) in Marathi, Hindi, Telugu, Kannada,
   and Tamil are preserved without character loss or normalization corruption.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from tokenizers import Tokenizer

_HERE = Path(__file__).resolve().parent
_TEAM = _HERE.parent
_REPO = _TEAM.parent.parent

sys.path.insert(0, str(_HERE))
import render  # noqa: E402

EXPECTED_V0_1_SHA256 = "a33c9907ec16876bc57b011714e8380879919fba1327d84bfb0d60407fe6e578"
BASELINE_SHA256 = "01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff"
V0_SHA256 = "2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5"

EXPECTED_MARKERS = {
    "<|im_start|>": 129994,
    "<|im_end|>": 130816,
    "<|tool_call|>": 130773,
    "<|tool_result|>": 130774,
    "<|endoftext|>": 130822,
    "<|think|>": 130823,
    "<|/think|>": 130824,
    "<|/tool_call|>": 130825,
    "<|/tool_result|>": 130826,
}


def ensure_frozen_tokenizer() -> Path:
    """Ensure the frozen tokenizer v0.1 file is available and verified."""
    cache_dir = Path(os.environ.get("G10_TOKENIZER_CACHE") or Path.home() / ".cache" / "era-v5")
    cache_dir.mkdir(parents=True, exist_ok=True)
    v0_1_path = cache_dir / "v0_1_tokenizer.json"

    if v0_1_path.is_file():
        sha = hashlib.sha256(v0_1_path.read_bytes()).hexdigest()
        if sha == EXPECTED_V0_1_SHA256:
            return v0_1_path

    base_path = cache_dir / "baseline_tokenizer.json"
    if not base_path.is_file() or hashlib.sha256(base_path.read_bytes()).hexdigest() != BASELINE_SHA256:
        print("[SETUP] Downloading BrahmicTokenizer-131K baseline...")
        url = "https://huggingface.co/theschoolofai/BrahmicTokenizer-131K/raw/main/tokenizer.json"
        urllib.request.urlretrieve(url, base_path)
        assert hashlib.sha256(base_path.read_bytes()).hexdigest() == BASELINE_SHA256

    v0_path = cache_dir / "v0_tokenizer.json"
    build_v0 = _REPO / "teams" / "03-tokenizer" / "v0" / "build_v0.py"
    build_v0_1 = _REPO / "teams" / "03-tokenizer" / "v0" / "build_v0_1.py"

    print("[SETUP] Building tokenizer v0...")
    subprocess.run([sys.executable, str(build_v0), str(base_path), str(v0_path)], check=True)
    assert hashlib.sha256(v0_path.read_bytes()).hexdigest() == V0_SHA256

    print("[SETUP] Building tokenizer v0.1 with G10 slots...")
    subprocess.run([sys.executable, str(build_v0_1), str(v0_path), str(v0_1_path)], check=True)
    assert hashlib.sha256(v0_1_path.read_bytes()).hexdigest() == EXPECTED_V0_1_SHA256

    return v0_1_path


def main() -> int:
    print("=" * 80)
    print("G10 Post-Training: Frozen Tokenizer Verification Report")
    print("Team 10 (Post-Training) & Team 3 (Tokenizer) Interface Audit")
    print("=" * 80)

    tokenizer_path = ensure_frozen_tokenizer()
    raw_bytes = tokenizer_path.read_bytes()
    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
    print("\n[1] Tokenizer Artifact Verification:")
    print(f"    Path:   {tokenizer_path}")
    print(f"    SHA256: {sha256_hex}")
    assert sha256_hex == EXPECTED_V0_1_SHA256, "SHA256 mismatch!"
    print("    Status: PASS (Exact match with teams/03-tokenizer/v0/SHA256SUMS)")

    tok = Tokenizer.from_file(str(tokenizer_path))

    print("\n[2] G10 Special Markers Atomic Encoding Audit:")
    loaded_ids = render.load_team3_marker_ids(tokenizer_path)
    for surf, expected_id in EXPECTED_MARKERS.items():
        name = render.MARKER_NAMES[surf]
        assert loaded_ids[expected_id] == (name, surf)
        enc = tok.encode(surf)
        assert enc.ids == [expected_id], f"{surf} encoded as {enc.ids}, expected [{expected_id}]"
        print(f"    PASS: {surf:<18} -> Token ID {expected_id:<7} (Single atomic token, name: {name})")

    print("\n[3] Look-alike & Base Marker Smuggling Prevention:")
    base_think_enc = tok.encode("<think>")
    assert 130823 not in base_think_enc.ids
    print(f"    PASS: Base '<think>' encodes as {base_think_enc.ids} (never maps to G10 <|think|> 130823)")

    lookalikes = ["</think>", "<tool_call>", "</tool_call>", "<tool_result>", "</tool_result>", "<｜think｜>", "＜think＞"]
    for tag in lookalikes:
        enc = tok.encode(tag)
        assert not any(i in EXPECTED_MARKERS.values() for i in enc.ids)
        print(f"    PASS: Plain lookalike '{tag}' encodes as normal text (subwords: {len(enc.ids)})")

    print("\n[4] Indic Text Orthography & Joiner Integrity (ZWJ/ZWNJ):")
    indic_tests = [
        ("Marathi (FineWeb-2, eyelash-ra ZWJ)", "माहिती तंत्रज्ञान आणि संगणक प्रणाली (उदा. ऱ्या)"),
        ("Hindi (HPLT 3.0 / IndicCorp, ZWNJ)", "सद्‌भावना, अंतर्‌राष्ट्रीय और विद्‌यालय"),
        ("Telugu (Chandassu, ZWNJ)", "శ్రీరస్తు శుభమస్తు అవిఘ్నమస్తు - తెలుగు ఛందస్సు"),
        ("Kannada (FineWeb-2, conjunct ZWJ)", "ಕನ್ನಡ ಸಾಹಿತ್ಯ ಸಮ್ಮೇಳನ ಮತ್ತು ವ್ಯಾಕರಣ"),
        ("Tamil (Sangraha Verified)", "தமிழ் செம்மொழி மற்றும் வரலாற்றுச் சிறப்பு"),
    ]
    for label, text in indic_tests:
        enc = tok.encode(text)
        dec = tok.decode(enc.ids, skip_special_tokens=False)
        assert text == dec, f"Decoded text mismatch for {label}!"
        print(f"    PASS: {label:<38} -> {len(enc.ids):<3} tokens (Roundtrip 100% faithful)")

    print("\n[5] Multi-Turn Agentic Dialogue End-to-End Roundtrip:")
    messages = [
        {"role": "system", "content": "You are an expert polyglot code and reasoning assistant. Keep ZWJ and ZWNJ in Indic text."},
        {"role": "user", "content": "Inspect calc.py and fix the regression on line 12."},
        {
            "role": "assistant",
            "think": "Inspecting calc.py using read_file tool call.",
            "tool_calls": [{"name": "read_file", "arguments": {"path": "calc.py"}}],
            "content": "Reading calc.py to inspect the failing test.",
        },
        {"role": "tool", "content": "def add(a, b):\n    return a + b + 1\n"},
        {
            "role": "assistant",
            "think": "The function returns an extra 1. Applying patch.",
            "tool_calls": [{"name": "apply_patch", "arguments": {"patch": "return a + b", "path": "calc.py"}}],
            "content": "Applying the fix to calc.py.",
        },
        {"role": "tool", "content": "Patch applied successfully."},
        {"role": "assistant", "content": "The bug in calc.py has been fixed. Verified clean."},
    ]

    for effort in ("1k", "4k", "16k", "64k"):
        rendered = render.render(messages, effort=effort)
        enc = tok.encode(rendered)
        dec = tok.decode(enc.ids, skip_special_tokens=False)
        assert rendered == dec
        parsed = render.parse(rendered)
        assert parsed["effort"] == effort
        assert len(parsed["messages"]) == 7
        print(f"    PASS: Multi-turn dialogue (effort: {effort:<3}) -> {len(enc.ids):<3} tokens, exact decode match")

    print("\n" + "=" * 80)
    print("SUMMARY: ALL FROZEN TOKENIZER CHECKS PASSED (100% VERIFIED)")
    print("Gate 2 Evidence Requirement Satisfied for Member A (Amit T).")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
