"""Kannada SWE fixtures: reviewed words and labelled shaping controls, not corpus rows."""

EFFORTS = ("1k", "4k", "16k", "64k")
ONEPLUS = "ಒನ್\u200cಪ್ಲಸ್"
RA_DEFAULT = "\u0cb0\u0ccd\u0c95"
RA_UNICODE = "\u0cb0\u200d\u0ccd\u0c95"
RA_LEGACY = "\u0cb0\u0ccd\u200d\u0c95"
CLEAN_WORDS = ("ಮನೆ", "ಕನ್ನಡ", "ಅಕ್ಕ", "ಶಕ್ತಿ")
CASES = tuple(("Clean word", word) for word in CLEAN_WORDS) + (
    ("OnePlus — ZWNJ after virama", ONEPLUS),
    ("RA — default", RA_DEFAULT),
    ("RA — ZWJ before virama (Unicode)", RA_UNICODE),
    ("RA — ZWJ after virama (legacy)", RA_LEGACY),
)


def preservation_messages(text: str) -> list[dict]:
    """Exercise every supported text field using a nonempty canonical shape."""
    return [
        {"role": "system", "content": text},
        {"role": "user", "content": text},
        {"role": "assistant", "think": text, "content": text,
         "tool_calls": [{"name": "check_text", "arguments": {"text": text}}]},
        {"role": "tool", "content": text},
    ]


def demo_messages() -> list[dict]:
    """Authored example shared by the documentation and its executable check."""
    return [
        {"role": "system", "content": "ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ."},
        {"role": "user", "content": ONEPLUS},
        {"role": "assistant", "think": "ಪಠ್ಯವನ್ನು ಬದಲಿಸಬಾರದು.",
         "tool_calls": [{"name": "write_text", "arguments": {
             "path": "ಕನ್ನಡ.txt", "text": ONEPLUS}}]},
        {"role": "tool", "content": "ಉಳಿಸಲಾಗಿದೆ."},
        {"role": "assistant", "content": "ಉಳಿಸಲಾಗಿದೆ."},
    ]
