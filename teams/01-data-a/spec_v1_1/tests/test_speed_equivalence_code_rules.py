"""Equivalence tests for the speed-ups of four code rules in clean.py (spec_v1_1/results/speed_v1_1.md). Each rule is checked
against a frozen copy of the rule as it was before the change (a4_reference, a6_reference, e2_reference and e3_reference, below): the
same text goes through both and the results must be equal, on hand-written cases at the edge of each guard and on random documents.
Every text here is made up; none comes from a pack.

  python -m pytest spec_v1_1/tests/test_speed_equivalence_code_rules.py

  DA-A4-002  replacement-character comment lines (six code packs): a text with no U+FFFD is kept without running LOST
  DA-A6-001  Cyrillic look-alike letters (six code packs): a text with no Cyrillic character (U+0400 to U+04FF) is kept without
             running MIXED
  DA-E2-001  byte-array and base64 drop (six code packs): the byte-array regex runs only when the text holds 24 or more "0x"
  DA-E3-003  known keys and base32 seeds (six code packs): each KEYS pattern runs only when a literal it needs is in the text, and
             SEED runs only when the text has "=", a quote and one of its words (tested on the casefolded text)
  DA-E3-004  second speed-up (last section): ASSIGNED runs only on a text that passes three tests, and the gh hint is tightened

The rules in the sheet are read from specv1_1.md (the namespace of each card is run on its own). The first speed-up of DA-E3-004
and the one of the shared F1 are in test_speed_equivalence_code.py. If a rule's behaviour is ever changed on purpose, update
or delete its frozen copy.
"""
import random
import re
import sys
import textwrap
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[2] / "spec_v1_1"
SHEET = Path(__file__).resolve().parents[2] / "spec_v1_1" / "sheets" / "specv1_1.md"
sys.path.insert(0, str(SPEC))
import clean as c
REF_DIR = Path(__file__).resolve().parents[2] / "tests" / "spec_v1"   # code_speed_reference.py, as on TSAI main
sys.path.insert(0, str(REF_DIR))
from code_speed_reference import e3_reference as e4_reference

CODE_PACKS = ("code-cpp", "code-go", "code-java", "code-js-ts", "code-python", "code-rust")


def doc(text, pack="code-go", lang="go"):
    return {"doc_id": "x", "text": text, "url": "", "lang_label": lang, "pack_id": pack}


def namespace(rule_id, family="code"):
    """The card of one rule in specv1_1.md run on its own: a fresh copy each time, so a test can wrap its regexes."""
    text = SHEET.read_text(encoding="utf-8")
    body = re.search(r"^## Medicine \d+ — " + family + r" / \w+ / `" + rule_id + r"`\n(.*?)(?=^## Medicine |\Z)", text, re.S | re.M).group(1)
    ns = {"__name__": "rules"}
    exec(textwrap.dedent(re.search(r"^```python\n(.*?)^```", body, re.S | re.M).group(1)), ns)
    return ns


class Spy:
    """A regex that counts the calls of one method and gives the real answer."""
    def __init__(self, real, method):
        self.real, self.method, self.calls = real, method, 0

    def __getattr__(self, name):
        if name == self.method:
            def call(*a, **k):
                self.calls += 1
                return getattr(self.real, name)(*a, **k)
            return call
        return getattr(self.real, name)


# =====================================================================================================================
# DA-A4-002: comment lines that hold a replacement character
# =====================================================================================================================

def a4_reference():
    """DA-A4-002 as it was before its speed-up (clean.py 716c9a90093f, specv1_1.md medicine 4): LOST is run on every text."""
    LOST = re.compile(r"[ \t]*//[^\n\w]*" + chr(0xFFFD) + r"[^\nA-Za-z0-9]*$", re.M)

    def medicine_a4(doc):
        t = LOST.sub("", doc["text"])
        return ("fix" if t != doc["text"] else "keep", t)

    return {"medicine_a4": medicine_a4, "LOST": LOST}


A4_OLD, A4_NEW = a4_reference(), namespace("DA-A4-002")


def test_a4_the_pattern_is_the_old_one():
    assert A4_NEW["LOST"].pattern == A4_OLD["LOST"].pattern and A4_NEW["LOST"].flags == A4_OLD["LOST"].flags


def test_a4_every_match_holds_a_replacement_character():
    for t in ("// �", "x\n  //��?\n", "\t// ?�.,;"):
        m = A4_OLD["LOST"].search(t)
        assert m and "�" in m.group()


FFFD = "�"
A4_TEXTS = {
    "empty": "",
    "no replacement character": "// a comment\nint x = 1; // 2\n",
    "only the character": FFFD,
    "the character in a string": 'a = "' + FFFD + '"\n',
    "the character in a comment with words": "// " + FFFD + " is a bad byte\n",
    "comment with the character only": "x\n// " + FFFD + FFFD + "\ny\n",
    "comment with the character and a digit": "// " + FFFD + "1\n",
    "comment with a letter before": "// ab" + FFFD + "\n",
    "comment with an underscore before": "//_" + FFFD + "\n",
    "comment with punctuation before": "// !?" + FFFD + "\n",
    "comment with indentation": "\t \t// " + FFFD + "\nnext\n",
    "comment at the end, no newline": "code\n// " + FFFD,
    "comment with trailing punctuation": "// " + FFFD + " ...;\n",
    "comment with trailing letter": "// " + FFFD + " z\n",
    "comment with the character twice": "// " + FFFD + " , " + FFFD + "\n",
    "two lines": "// " + FFFD + "\n// " + FFFD + FFFD + "\n",
    "slash-star comment": "/* " + FFFD + " */\n",
    "carriage return": "// " + FFFD + "\r\nx\r\n",
    "non-ascii letters around": "// éé" + FFFD + "é\n",
    "the character a long way down": "x = 1\n" * 3000 + "// " + FFFD + "\n",
}


@pytest.mark.parametrize("name", list(A4_TEXTS))
def test_a4_hand_cases_match_old_rule(name):
    text = A4_TEXTS[name]
    assert A4_NEW["medicine_a4"](doc(text)) == A4_OLD["medicine_a4"](doc(text))


def test_a4_the_hand_cases_reach_every_branch():
    results = [A4_NEW["medicine_a4"](doc(t)) for t in A4_TEXTS.values()]
    assert any(a == "fix" for a, _ in results)
    assert any(a == "keep" and FFFD in t for (a, t) in results)         # the character is there and nothing is changed
    assert any(a == "keep" and FFFD not in t for (a, t) in results)


def test_a4_a_text_without_the_character_does_not_run_lost_and_one_with_it_does():
    ns = namespace("DA-A4-002")
    ns["LOST"] = spy = Spy(ns["LOST"], "sub")
    ns["medicine_a4"](doc("// plain comment\nx = 1\n" * 100))
    assert spy.calls == 0
    ns["medicine_a4"](doc("// " + FFFD + "\n"))
    assert spy.calls == 1


A4_PIECES = ["// " + FFFD, "//" + FFFD + FFFD, "  // " + FFFD + " ...", "\t// ab" + FFFD, "// " + FFFD + "1", "// plain comment",
             "int x = 1;", 'p("' + FFFD + '")', "x = " + FFFD, "// é" + FFFD, "//", "// …" + FFFD + "?", "", "// _" + FFFD,
             "/* " + FFFD + " */", "code(); // " + FFFD, "y; //" + FFFD + "z", "// " + FFFD + FFFD + FFFD + ";;"]


def random_a4_text(rng):
    lines = [rng.choice(A4_PIECES) for _ in range(rng.randint(0, 30))]
    return rng.choice(["\n", "\n", "\r\n"]).join(lines) + rng.choice(["", "\n"])


def test_a4_random_texts_match_old_rule_and_cover_every_branch():
    rng = random.Random(41)
    seen = {"fix": 0, "has_char_kept": 0, "no_char": 0}
    for _ in range(10000):
        t = random_a4_text(rng)
        old, new = A4_OLD["medicine_a4"](doc(t)), A4_NEW["medicine_a4"](doc(t))
        assert new == old, repr(t)
        seen["fix"] += new[0] == "fix"
        seen["has_char_kept"] += new[0] == "keep" and FFFD in t
        seen["no_char"] += FFFD not in t
    assert all(v > 300 for v in seen.values()), seen


def test_a4_the_rule_in_clean_py_acts_only_on_the_code_packs_and_equals_the_old_rule():
    rule = c._RULE["DA-A4-002"]()
    for text in (A4_TEXTS["comment with the character only"], A4_TEXTS["empty"], A4_TEXTS["two lines"]):
        for pack in CODE_PACKS:
            assert rule(doc(text, pack)) == A4_OLD["medicine_a4"](doc(text))
        for pack in ("en-dclm", "math-finemath", "sci-finepdfs", None):
            assert rule(doc(text, pack, lang="en")) == ("keep", text)


# =====================================================================================================================
# DA-A6-001: Cyrillic look-alike letters
# =====================================================================================================================

def a6_reference():
    """DA-A6-001 without its speed guard, with the #86 consecutive-Cyrillic exclusion (clean.py 716c9a90093f, specv1_1.md medicine 3): MIXED is run on every text."""
    HOMO = str.maketrans("аеорсухіјѕАВЕКМНОРСТХІЈЅ",
                         "aeopcyxijsABEKMHOPCTXIJS")
    MIXED = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*[Ѐ-ӿ])(?!\w*[Ѐ-ӿ]{2})\w+\b")

    def medicine_a6(doc):
        t = MIXED.sub(lambda m: m.group().translate(HOMO), doc["text"])
        return ("fix" if t != doc["text"] else "keep", t)

    return {"medicine_a6": medicine_a6, "MIXED": MIXED, "HOMO": HOMO}


A6_OLD, A6_NEW = a6_reference(), namespace("DA-A6-001")


def test_a6_the_patterns_are_the_old_ones():
    assert A6_NEW["MIXED"].pattern == A6_OLD["MIXED"].pattern and A6_NEW["MIXED"].flags == A6_OLD["MIXED"].flags
    assert A6_NEW["HOMO"] == A6_OLD["HOMO"]


def test_a6_the_guard_range_is_the_range_of_mixed_and_every_match_holds_one():
    assert A6_NEW["CYRILLIC"].pattern == "[Ѐ-ӿ]"
    assert "[Ѐ-ӿ]" in A6_OLD["MIXED"].pattern
    for t in ("pаss", "Ѐa", "aӿ", "x_і_y"):
        m = A6_OLD["MIXED"].search(t)
        assert m and A6_NEW["CYRILLIC"].search(m.group())


CY = "а"                         # Cyrillic a, a look-alike of the Latin a
A6_TEXTS = {
    "empty": "",
    "latin only": "def pass_through(x): return x\n",
    "mixed word": "p" + CY + "ss = 1\n",
    "pure cyrillic word": "привет мир\n",
    "pure cyrillic look-alikes only": "аеорсух\n",
    "cyrillic next to a latin word": "abc привет\n",
    "mixed with underscore": "a_" + CY + "_b\n",
    "mixed with digit": "x1" + CY + "\n",
    "first edge of the range": "aЀ\n",
    "last edge of the range": "aӿ bӾ\n",
    "just below the range": "aϿ\n",
    "just above the range": "aԀԁ\n",
    "cyrillic supplement look-alike": "aԁ\n",
    "greek and latin": "aαβ\n",
    "a hundred mixed words": " ".join("w" + CY + str(i) for i in range(100)),
    "upper-case look-alikes": "HАНОР CATС\n",
    "cyrillic in a comment": "// комментарий about p" + CY + "ss\n",
    "cyrillic a long way down": "x = 1\n" * 3000 + "p" + CY + "ss\n",
    "no cyrillic a long way down": "x = 1\n" * 3000 + "pass\n",
    "non-ascii latin": "café über ça\n",
}


@pytest.mark.parametrize("name", list(A6_TEXTS))
def test_a6_hand_cases_match_old_rule(name):
    text = A6_TEXTS[name]
    assert A6_NEW["medicine_a6"](doc(text)) == A6_OLD["medicine_a6"](doc(text))


def test_a6_the_hand_cases_reach_every_branch():
    results = [(A6_NEW["medicine_a6"](doc(t)), t) for t in A6_TEXTS.values()]
    assert any(r[0] == "fix" for r, _ in results)
    assert any(r[0] == "keep" and A6_NEW["CYRILLIC"].search(t) for r, t in results)          # Cyrillic there, nothing to fix
    assert any(r[0] == "keep" and not A6_NEW["CYRILLIC"].search(t) for r, t in results)


def test_a6_a_text_without_cyrillic_does_not_run_mixed_and_one_with_it_does():
    ns = namespace("DA-A6-001")
    ns["MIXED"] = spy = Spy(ns["MIXED"], "sub")
    ns["medicine_a6"](doc("def f(x): return x + 1\n" * 100))
    assert spy.calls == 0
    ns["medicine_a6"](doc("p" + CY + "ss"))
    assert spy.calls == 1


A6_LATIN = ["pass", "return", "x1", "foo_bar", "caf\u00e9", "_", "9", "\u03b1\u03b2", "ab\u0501", "//", "(", ")", "=", "\u2013", "ABC", "value"]
A6_PURE = ["\u043f\u0440\u0438\u0432\u0435\u0442", "\u0430\u0435\u043e", "\u0400", "\u04ff", "\u0410\u0412\u0415"]
A6_MIXED = ["p" + CY + "ss", "a\u0400b", "\u04ffz", "\u0410BC", "H\u0410\u041d", "\u0455cript", "j\u0430v\u0430", "\u0406d", "x_\u0430"]


def random_a6_text(rng):
    """Latin pieces with, in some texts only, a few pure-Cyrillic and a few mixed-script pieces."""
    p_pure, p_mixed = rng.choice([0, 0, 0, 0.03, 0.2]), rng.choice([0, 0, 0, 0.03, 0.2])
    out = []
    for _ in range(rng.randint(0, 80)):
        r = rng.random()
        pool = A6_PURE if r < p_pure else A6_MIXED if r < p_pure + p_mixed else A6_LATIN
        out.append(rng.choice(pool) + rng.choice([" ", " ", "\n", "", "_", "."]))
    return "".join(out)


def test_a6_random_texts_match_old_rule_and_cover_every_branch():
    rng = random.Random(43)
    seen = {"fix": 0, "cyrillic_kept": 0, "none": 0}
    for _ in range(10000):
        t = random_a6_text(rng)
        old, new = A6_OLD["medicine_a6"](doc(t)), A6_NEW["medicine_a6"](doc(t))
        assert new == old, repr(t)
        has = bool(A6_NEW["CYRILLIC"].search(t))
        seen["fix"] += new[0] == "fix"
        seen["cyrillic_kept"] += new[0] == "keep" and has
        seen["none"] += not has
    assert all(v > 300 for v in seen.values()), seen


def test_a6_the_rule_in_clean_py_acts_only_on_the_code_packs_and_equals_the_old_rule():
    rule = c._RULE["DA-A6-001"]()
    for text in (A6_TEXTS["mixed word"], A6_TEXTS["empty"], A6_TEXTS["pure cyrillic word"]):
        for pack in CODE_PACKS:
            assert rule(doc(text, pack)) == A6_OLD["medicine_a6"](doc(text))
        for pack in ("en-dclm", "math-finemath", "sci-finepdfs", None):
            assert rule(doc(text, pack, lang="en")) == ("keep", text)


# =====================================================================================================================
# DA-E2-001: byte arrays and base64 blobs
# =====================================================================================================================

def e2_reference():
    """DA-E2-001 as it was before its speed-up (clean.py 716c9a90093f, specv1_1.md medicine 13): _BYTES is run on every text."""
    _BYTES = re.compile(r"(?:0x[0-9a-fA-F]{2},\s*){24,}(?:0x[0-9a-fA-F]{2},?)?")
    _B64 = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")

    def drop_blob(text: str, share: float = 0.10, b64_share: float = 0.4):
        if not text:
            return "keep", text
        n = len(text)
        if sum(len(m.group()) for m in _BYTES.finditer(text)) / n >= share:
            return "drop", text
        if sum(len(m.group()) for m in _B64.finditer(text)) / n >= b64_share:
            return "drop", text
        return "keep", text

    return {"drop_blob": drop_blob, "_BYTES": _BYTES, "_B64": _B64}


E2_OLD, E2_NEW = e2_reference(), namespace("DA-E2-001")


def test_e2_the_patterns_are_the_old_ones():
    for name in ("_BYTES", "_B64"):
        assert E2_NEW[name].pattern == E2_OLD[name].pattern and E2_NEW[name].flags == E2_OLD[name].flags, name


def test_e2_the_shortest_match_of_bytes_holds_24_groups_that_start_with_0x():
    for k in (23, 24, 25):
        t = "0x00, " * k
        m = E2_OLD["_BYTES"].search(t)
        assert (m is not None) == (k >= 24)
        if m:
            assert m.group().count("0x") >= 24 and t.count("0x") >= 24


def b64(n, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"):
    return "".join(alphabet[(i * 7 + 3) % len(alphabet)] for i in range(n))


def hexes(k, sep=", ", fmt="0x%02x"):
    return sep.join(fmt % (i % 256) for i in range(k))


def same_e2(text):
    assert E2_NEW["drop_blob"](text) == E2_OLD["drop_blob"](text), repr(text[:80])
    return E2_NEW["drop_blob"](text)[0]


E2_TEXTS = {
    "empty": "",
    "plain code": "int main() { return 0; }\n" * 50,
    "23 groups only": hexes(23) + ",",
    "24 groups only": hexes(24) + ",",
    "25 groups only": hexes(25) + ",",
    "24 groups, no trailing comma": hexes(24),
    "24 groups, newlines between": ",\n\t".join("0x%02X" % i for i in range(24)) + ",",
    "100 groups": "var data = []byte{" + hexes(100) + "}\n",
    "24 groups in a long file": "x = 1\n" * 1000 + hexes(24) + ",\n",
    "24 groups, bad hex": ", ".join("0x%02x" % i if i != 5 else "0xzz" for i in range(24)),
    "24 groups, one digit": ", ".join("0x%02x" % i if i != 5 else "0x7" for i in range(24)),
    "24 groups, upper-case x": ", ".join("0X%02x" % i for i in range(24)),
    "23 and 23 groups apart": hexes(23) + " ;\n" + hexes(23),
    "24 0x with no commas": "0x00 " * 24,
    "30 0x in prose": "the value 0x1f is common; " * 30,
    "base64 199": b64(199),
    "base64 200": b64(200),
    "base64 only, long": b64(5000),
    "base64 below the share": "x = 1\n" * 1000 + b64(300),
    "base64 with padding": b64(300) + "==",
    "base64 and fewer than 24 groups": b64(1000) + "\n" + hexes(10),
    "base64 and bytes": hexes(30) + "\n" + b64(1000),
    "many short base64": (b64(150) + " ") * 40,
}


@pytest.mark.parametrize("name", list(E2_TEXTS))
def test_e2_hand_cases_match_old_rule(name):
    same_e2(E2_TEXTS[name])


def test_e2_the_hand_cases_reach_every_branch():
    verdicts = {n: same_e2(t) for n, t in E2_TEXTS.items()}
    assert verdicts["24 groups only"] == "drop"                      # bytes half
    assert verdicts["base64 only, long"] == "drop"                   # base64 half
    assert verdicts["24 groups in a long file"] == "keep"            # 24 or more "0x", under the share
    assert verdicts["23 groups only"] == "keep"                      # under 24 "0x"
    assert verdicts["30 0x in prose"] == "keep"                      # 24 or more "0x", no byte array


@pytest.mark.parametrize("n", range(1420, 1441))
def test_e2_share_threshold_sweep(n):
    """The array is 24 groups, 143 characters: it is 10% of a text of 1430 characters, and the text is dropped up to that length. The
    filler is not base64 characters, so only the byte-array half can drop it."""
    array = hexes(24) + ","
    assert len(array) == 143
    text = array + "." * (n - len(array))
    assert same_e2(text) == ("drop" if n <= 1430 else "keep")


def test_e2_a_text_with_fewer_than_24_groups_does_not_run_bytes_and_one_with_24_does():
    ns = namespace("DA-E2-001")
    ns["_BYTES"] = spy = Spy(ns["_BYTES"], "finditer")
    ns["drop_blob"](hexes(23) + " " + "x" * 100)
    assert spy.calls == 0
    ns["drop_blob"]("x" * 100)
    assert spy.calls == 0
    ns["drop_blob"](hexes(24) + " " + "x" * 100)
    assert spy.calls == 1


def random_e2_text(rng):
    parts = []
    for _ in range(rng.randint(0, 6)):
        kind = rng.choice(["code", "code", "hex", "hex_bad", "b64", "prose0x", "pad"])
        if kind == "code":
            parts.append("func f() { return 1 }\n" * rng.randint(1, 40))
        elif kind == "hex":
            parts.append(hexes(rng.choice([1, 10, 22, 23, 24, 25, 26, 40, 90]), rng.choice([", ", ",", ",\n\t", ",  "])) + rng.choice(["", ",", ", "]))
        elif kind == "hex_bad":
            parts.append(", ".join(rng.choice(["0x%02x", "0X%02x", "0x%x", "0xg%x", "%02x"]) % (i % 16) for i in range(rng.randint(20, 40))))
        elif kind == "b64":
            parts.append(b64(rng.choice([150, 199, 200, 201, 400, 1500, 4000])) + rng.choice(["", "=", "=="]))
        elif kind == "prose0x":
            parts.append("see 0x1f and 0x2a; " * rng.randint(1, 40))
        else:
            parts.append("a" * rng.choice([10, 100, 500, 3000]))
        parts.append(rng.choice(["\n", " ", ""]))
    return "".join(parts)


def test_e2_random_texts_match_old_rule_and_cover_every_branch():
    rng = random.Random(47)
    seen = {"bytes_drop": 0, "b64_drop": 0, "keep_with_24": 0, "keep_below_24": 0}
    for _ in range(6000):
        t = random_e2_text(rng)
        new = same_e2(t)
        bytes_hit = sum(len(m.group()) for m in E2_OLD["_BYTES"].finditer(t)) / max(len(t), 1) >= 0.10
        seen["bytes_drop"] += new == "drop" and bytes_hit
        seen["b64_drop"] += new == "drop" and not bytes_hit
        seen["keep_with_24"] += new == "keep" and t.count("0x") >= 24
        seen["keep_below_24"] += new == "keep" and t.count("0x") < 24
    assert all(v > 150 for v in seen.values()), seen


def test_e2_the_rule_in_clean_py_acts_only_on_the_code_packs_and_equals_the_old_rule():
    rule = c._RULE["DA-E2-001"]()
    for text in (E2_TEXTS["24 groups only"], E2_TEXTS["plain code"], E2_TEXTS["empty"], E2_TEXTS["base64 only, long"]):
        for pack in CODE_PACKS:
            old = E2_OLD["drop_blob"](text)
            assert rule(doc(text, pack)) == old
        for pack in ("en-dclm", "math-finemath", "sci-finepdfs", None):
            assert rule(doc(text, pack, lang="en")) == ("keep", text)


# =====================================================================================================================
# DA-E3-003: known keys and base32 seeds
# =====================================================================================================================

def e3_reference():
    """DA-E3-003 as it was before its speed-up (clean.py 716c9a90093f, specv1_1.md medicine 23): all five KEYS patterns and SEED
    are run on every text."""
    KEYS = [re.compile(p) for p in (r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"\bsk-[A-Za-z0-9_-]{20,}",
            r"xox[baprs]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")]
    SEED = re.compile(r'(?i)((?:secret|seed|totp|otp)\w*\s*:?=\s*")[A-Z2-7]{16,}(")')

    def medicine_e3(doc):
        t = doc["text"]
        for rx in KEYS:
            t = rx.sub("EXAMPLE_SECRET", t)
        t = SEED.sub(r"\1EXAMPLE_SECRET\2", t)
        return ("fix" if t != doc["text"] else "keep", t)

    return {"medicine_e3": medicine_e3, "KEYS": KEYS, "SEED": SEED}


E3_OLD, E3_NEW = e3_reference(), namespace("DA-E3-003")


def test_e3_the_patterns_are_the_old_ones():
    assert [(r.pattern, r.flags) for r in E3_NEW["KEYS"]] == [(r.pattern, r.flags) for r in E3_OLD["KEYS"]]
    assert (E3_NEW["SEED"].pattern, E3_NEW["SEED"].flags) == (E3_OLD["SEED"].pattern, E3_OLD["SEED"].flags)
    assert len(E3_NEW["KEY_HINTS"]) == len(E3_NEW["KEYS"])


AKIA = "AKIA" + "ABCDEFGH12345678"
GH = {l: "gh" + l + "_" + "a1B2" * 8 for l in "pousr"}
SK = "sk-" + "abc_DEF-123" * 3
XOX = {l: "xox" + l + "-" + "1234567890ab" for l in "baprs"}
PEM = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----"  # joined at run time, so pr-guard does not read it as a key
SEEDV = "ABCDEFGHIJKLMNOP"
KEY_SAMPLES = [AKIA, *GH.values(), SK, *XOX.values(), PEM]


def test_e3_every_text_a_keys_pattern_matches_holds_one_of_its_literals():
    """The hints are necessary: a sample of every shape of every pattern holds a hint of its pattern, and no other pattern's match is lost."""
    for rx, hints in zip(E3_OLD["KEYS"], E3_NEW["KEY_HINTS"]):
        samples = [s for s in KEY_SAMPLES if rx.search(s)]
        assert samples, rx.pattern
        for s in samples:
            m = rx.search(s)
            assert any(h in m.group() for h in hints), (rx.pattern, m.group())
    # the five gh shapes and the five xox shapes are all matched (so every letter of the class is covered by a hint)
    for s in (*GH.values(), *XOX.values()):
        assert any(rx.search(s) for rx in E3_OLD["KEYS"]), s


def test_e3_the_seed_words_catch_every_character_the_unicode_flag_lets_match_a_letter_of_them():
    """SEED is (?i): a character that matches a letter of secret, seed or totp under it must keep its letter after casefold()."""
    letters = sorted(set("secrettotpseedotp"))
    res = {ch: re.compile("(?i)" + ch) for ch in letters}
    for cp in range(0x20000):
        ch = chr(cp)
        for letter, rx in res.items():
            if rx.fullmatch(ch):
                assert letter in ch.casefold(), (hex(cp), letter)


def test_e3_the_seed_words_cover_the_words_of_the_pattern():
    assert set(E3_NEW["SEED_WORDS"]) <= {"secret", "seed", "totp", "otp"} and "otp" in E3_NEW["SEED_WORDS"]
    for w in ("secret", "seed", "totp", "otp"):
        assert any(s in w for s in E3_NEW["SEED_WORDS"]), w


def seeds(word, sep='=', quote='"', value=SEEDV):
    return word + sep + quote + value + quote


E3_TEXTS = {
    "empty": "",
    "plain code": "x = 1\nprint('hello')\n" * 30,
    "aws key": "key = '" + AKIA + "'\n",
    "aws key too short": "AKIA" + "A" * 15,
    "aws key lower case": "akia" + "A" * 16,
    "github token each letter": "\n".join(GH.values()),
    "github token too short": "ghp_" + "a" * 29,
    "github look-alike": "ghx_" + "a" * 40,
    "github token inside a word": "xgho_" + "a" * 30,
    "sk key": "t = " + SK,
    "sk key inside a word": "ask-" + "a" * 25,
    "sk key too short": "sk-" + "a" * 19,
    "slack tokens": "\n".join(XOX.values()),
    "slack token too short": "xoxb-123456789",
    "pem block": "a\n" + PEM + "\nb\n",
    "pem block no end": "-----BEGIN " + "PRIVATE KEY-----\nabc\n",
    "pem begin, wrong spacing": "-----BEGIN" + "PRIVATE KEY-----\n-----END PRIVATE KEY-----",
    "all five": "\n".join([AKIA, GH["p"], SK, XOX["b"], PEM]),
    "keys back to back": AKIA + GH["p"] + SK,
    "seed assignment": seeds("secret") + "\n",
    "seed assignment, upper case word": seeds("SECRET_KEY") + "\n",
    "seed assignment, mixed case": seeds("TotpSeed") + "\n",
    "seed assignment, otp": seeds("otp") + "\n",
    "seed assignment, seed": seeds("seed") + "\n",
    "seed assignment, totp": seeds("totp") + "\n",
    "seed assignment, long dotless s": seeds("ſecret") + "\n",
    "seed assignment, dotless s in seed": seeds("ſeed") + "\n",
    "seed assignment, colon equals": seeds("secret", sep=" := ") + "\n",
    "seed assignment, spaces": 'secret  =  "' + SEEDV + '"\n',
    "seed assignment, word suffix": seeds("secret_value_2") + "\n",
    "seed value too short": seeds("secret", value="ABCDEFGHIJKLMNO"),
    "seed value with lower case": seeds("secret", value="abcdefghijklmnop"),
    "seed value digits 2 to 7 only": seeds("secret", value="2345672345672345"),
    "seed value with a 1": seeds("secret", value="ABCDEFGHIJKLMNO1"),
    "seed with single quote": seeds("secret", quote="'"),
    "seed without a quote": "secret = " + SEEDV,
    "seed without an equals": 'secret "' + SEEDV + '"',
    "word without equals or quote": "secret seed otp totp " * 20,
    "equals and quote without a word": 'name = "' + SEEDV + '"',
    "word, equals and quote apart": 'seed\n=\n"' + SEEDV + '"',
    "word after the assignment": 'name = "' + SEEDV + '" # secret',
    "seed and keys": AKIA + "\n" + seeds("secret") + "\n" + PEM,
    "key replaced then seed": "secret=\"" + SEEDV + "\" " + AKIA,
    "cascade: replacement text next to a seed": "secret=\"" + "EXAMPLE_SECRET" + "\"",
    "non-ascii around": "éé " + seeds("secret") + " 中文",
    "key a long way down": "x = 1\n" * 3000 + AKIA,
    "seed a long way down": "x = 1\n" * 3000 + seeds("secret"),
}


def same_e3(text, pack="code-go", lang="go"):
    new, old = E3_NEW["medicine_e3"](doc(text, pack, lang)), E3_OLD["medicine_e3"](doc(text, pack, lang))
    assert new == old, repr(text[:100])
    return new


@pytest.mark.parametrize("name", list(E3_TEXTS))
def test_e3_hand_cases_match_old_rule(name):
    same_e3(E3_TEXTS[name])


def test_e3_the_hand_cases_reach_every_branch():
    results = {n: same_e3(t) for n, t in E3_TEXTS.items()}
    assert all(results[n][0] == "fix" for n in ("aws key", "github token each letter", "sk key", "slack tokens", "pem block", "all five",
                                                "seed assignment", "seed assignment, long dotless s", "seed and keys"))
    assert all(results[n][0] == "keep" for n in ("plain code", "aws key too short", "seed value too short", "word without equals or quote",
                                                 "equals and quote without a word", "seed without a quote"))


def test_e3_the_dotless_s_seed_is_replaced_and_found_only_by_the_casefold():
    text = seeds("ſecret")
    assert E3_NEW["medicine_e3"](doc(text))[0] == "fix"
    assert "secret" not in text.lower() and "secret" in text.casefold()


def test_e3_a_key_pattern_runs_only_when_a_literal_it_needs_is_in_the_text():
    expected_runs = [AKIA, GH["s"], SK, XOX["r"], PEM]
    for i, sample in enumerate(expected_runs):
        ns = namespace("DA-E3-003")
        spies = [Spy(rx, "sub") for rx in ns["KEYS"]]
        ns["KEYS"] = spies
        ns["medicine_e3"](doc("plain text\n"))
        assert [s.calls for s in spies] == [0] * 5
        ns["medicine_e3"](doc(sample))
        assert spies[i].calls == 1, i
        assert sum(s.calls for s in spies) == 1 + sum(1 for j, h in enumerate(ns["KEY_HINTS"]) if j != i and any(x in sample for x in h)), i


def test_e3_seed_runs_only_for_a_text_with_equals_quote_and_a_word():
    def calls(text):
        ns = namespace("DA-E3-003")
        ns["SEED"] = spy = Spy(ns["SEED"], "sub")
        ns["medicine_e3"](doc(text))
        return spy.calls
    assert calls("x = 1\n" * 50) == 0
    assert calls('secret "no equals"') == 0
    assert calls("secret = no_quote") == 0
    assert calls('name = "no word"') == 0
    assert calls(seeds("secret")) == 1
    assert calls(seeds("ſeed")) == 1
    assert calls(seeds("OTP")) == 1


E3_PIECES = [AKIA, GH["p"], GH["o"], SK, XOX["b"], PEM, "AKIA" + "A" * 10, "ghp_short", "sk-short", "xoxb-1", "-----BEGIN X-----",
             seeds("secret"), seeds("SEED_KEY"), seeds("totp"), seeds("otp"), seeds("ſecret"), seeds("secret", value="SHORT"),
             seeds("password"), seeds("name"), 'secret = "', 'seed = x', "secret", "seed", "otp", "totp", "x = 1", "print(1)", "=", '"',
             "A" * 16, "ghx_" + "a" * 30, "EXAMPLE_SECRET", "// secret key", "token = 'abc'", "é中"]


def random_e3_text(rng):
    return "".join(rng.choice(E3_PIECES) + rng.choice([" ", "\n", "", "\n\n", ";", "\t"]) for _ in range(rng.randint(0, 25)))


def test_e3_random_texts_match_old_rule_and_cover_every_branch():
    rng = random.Random(53)
    seen = {"fix": 0, "keep_with_word": 0, "keep_plain": 0, "key_fix": 0, "seed_fix": 0}
    for _ in range(12000):
        t = random_e3_text(rng)
        new = same_e3(t)
        seen["fix"] += new[0] == "fix"
        seen["keep_with_word"] += new[0] == "keep" and any(w in t.casefold() for w in ("secret", "seed", "otp"))
        seen["keep_plain"] += new[0] == "keep" and not any(w in t.casefold() for w in ("secret", "seed", "otp"))
        t2 = t
        for rx in E3_OLD["KEYS"]:
            t2 = rx.sub("EXAMPLE_SECRET", t2)
        seen["key_fix"] += t2 != t
        seen["seed_fix"] += E3_OLD["SEED"].sub(r"\1EXAMPLE_SECRET\2", t2) != t2
    assert all(v > 200 for v in seen.values()), seen


def test_e3_the_rule_in_clean_py_acts_only_on_the_code_packs_and_equals_the_old_rule():
    rule = c._RULE["DA-E3-003"]()
    for text in (E3_TEXTS["all five"], E3_TEXTS["seed assignment"], E3_TEXTS["plain code"], E3_TEXTS["empty"]):
        for pack in CODE_PACKS:
            assert rule(doc(text, pack)) == E3_OLD["medicine_e3"](doc(text))
        for pack in ("en-dclm", "math-finemath", "sci-finepdfs", None):
            assert rule(doc(text, pack, lang="en")) == ("keep", text)


# =====================================================================================================================
# DA-E3-004, second speed-up: the ASSIGNED guards and the KNOWN hints (spec_v1_1/results/speed_v1_1.md)
# =====================================================================================================================
# DA-E3-004 replaces known key formats and quoted secret values. Its ASSIGNED regex (a secret-like name, an operator, a quoted
# value of 16 or more characters) searches from every word start and was the slowest part of the rule. It now runs only on a text
# that passes three tests, each true whenever ASSIGNED could match; the gh hint of the KNOWN keys is also tightened:
#
#   1. the casefolded text holds one of ASSIGNED_WORDS (secret token key passw pwd)
#   2. VALUE_AFTER_OPERATOR: an operator end (: = >), a quote, 16 to 200 value characters and the same quote
#   3. NAME_WORD_THEN_VALUE: a name word, then the tail of ASSIGNED up to the closing quote
#   gh: the gh pattern needs ghp_ gho_ ghu_ ghs_ or ghr_ (the hint was "gh")
#
# The rule is compared with code_speed_reference.e3_reference, DA-E3-004 as it was in spec v1. Names of this section start with
# e4_ / E4_. The key-shaped strings are joined at run time so that no key-shaped text is in this file.


E4_OLD = e4_reference()
E4_VALUE = "A7b2C9d3E5f8G1h4"            # 16 characters, mixed letters and digits: looks random
E4_DUMMY = "your_api_key_here_1234"
E4_KELVIN, E4_LONG_S = chr(0x212A), chr(0x17F)


def e4_doc(text, pack="code-python", lang="python"):
    return {"doc_id": "x", "text": text, "url": "", "lang_label": lang, "pack_id": pack}


def e4_namespace():
    """The DA-E3-004 card run on its own: a fresh copy each time, so a test can wrap its regexes."""
    text = SHEET.read_text(encoding="utf-8")
    body = re.search(r"^## Medicine \d+ — code / E3 / `DA-E3-004`\n(.*?)(?=^## Medicine |\Z)", text, re.S | re.M).group(1)
    ns = {"__name__": "rules"}
    exec(textwrap.dedent(re.search(r"^```python\n(.*?)^```", body, re.S | re.M).group(1)), ns)
    return ns



E4_NEW = e4_namespace()


def e4_same(text, pack="code-python", lang="python"):
    """The rule in the sheet and the old rule give the same result on this text; the result."""
    new = E4_NEW["medicine"](e4_doc(text, pack, lang))
    assert new == E4_OLD(e4_doc(text, pack, lang)), text[:200]
    return new


# =====================================================================================================================
# The three tests are necessary: what they rest on
# =====================================================================================================================

def test_e4_the_assigned_pattern_is_the_old_one():
    old_src = (REF_DIR / "code_speed_reference.py").read_text(encoding="utf-8")
    compact = lambda s: re.sub(r"\s+", "", s)
    pattern = re.search(r'ASSIGNED = re\.compile\(\s*r"""(.*?)"""', old_src, re.S).group(1)
    assert compact(E4_NEW["ASSIGNED"].pattern) == compact(pattern)


def test_e4_every_name_of_assigned_holds_a_word_of_the_first_test():
    names = re.search(r"\(\?:(secret\|token\|.*?\|\\bkey)\)", E4_NEW["ASSIGNED"].pattern).group(1).split("|")
    assert len(names) == 11
    for alt in names:
        for sep in ("", "_", "-"):
            for tail in ("or", ""):
                name = alt.replace("[_\\-]?", sep).replace("(?:or)?", tail).replace("\\b", "")
                assert any(w in name for w in E4_NEW["ASSIGNED_WORDS"]), name


def test_e4_the_name_word_pattern_has_the_tail_of_assigned():
    tail = ['["\']?', "(?:\\s*:\\s*&?(?:'\\w+\\s+)?[\\w<>\\[\\]]{1,20})?", "\\s*(?::=|=>|=|:)\\s*", "[^\"'`\\s\\\\]{16,200}"]
    compact = lambda s: re.sub(r"\s+", "", s)
    for part in tail:
        assert compact(part) in compact(E4_NEW["ASSIGNED"].pattern)
        assert compact(part) in compact(E4_NEW["NAME_WORD_THEN_VALUE"].pattern)
    assert E4_NEW["NAME_WORD_THEN_VALUE"].flags == E4_NEW["ASSIGNED"].flags


def test_e4_the_operator_class_holds_the_last_character_of_every_operator():
    cls = E4_NEW["VALUE_AFTER_OPERATOR"].pattern.split("\\s")[0]           # "[:=>]"
    assert cls.startswith("[") and cls.endswith("]")
    for operator in (":=", "=>", "=", ":"):
        assert re.fullmatch(cls, operator[-1]), operator
    assert set(re.findall(r"[^\[\]]", cls)) == {":", "=", ">"}


def test_e4_every_character_the_unicode_flag_lets_match_a_letter_of_a_word_keeps_that_letter_under_casefold():
    """re.I lets other characters match a letter (U+017F for s, U+212A for k). The first test casefolds the text, so such a
    character must come out as the letter itself: checked for every code point, for every letter of ASSIGNED_WORDS."""
    everything = "".join(map(chr, range(0x110000)))
    letters = sorted(set("".join(E4_NEW["ASSIGNED_WORDS"])))
    extra = {}
    for letter in letters:
        found = [m.group() for m in re.finditer(letter, everything, re.I)]
        assert letter in found and letter.upper() in found
        for ch in found:
            assert ch.casefold() == letter, (hex(ord(ch)), letter)
        extra[letter] = [hex(ord(ch)) for ch in found if ch not in (letter, letter.upper())]
    assert extra["s"] == ["0x17f"] and extra["k"] == ["0x212a"]      # the only two, so U+017F and U+212A are tested below
    assert all(not v for ltr, v in extra.items() if ltr not in "sk")


# =====================================================================================================================
# Hand cases
# =====================================================================================================================

E4_OPERATORS = ["=", ":", ":=", "=>", " = ", " : ", " := ", " => ", "=\n", "\n=", "\n = \n", ":\t", "= =", ":=>", "=:"]
E4_NAMES = ["secret", "token", "api_key", "api-key", "apikey", "app_key", "app-key", "auth_key", "access_key", "client_key",
         "private_key", "password", "passwd", "pwd", "key", "SECRET", "Token", "API_KEY", "ApiKey", "monkey", "my-secret-key",
         "keyboard", "tokenizer", "mySecretValue", "password_hash", "secret-id", "token-value", "key-name", "pwd-hash", "password-x", "PASSWORD", "x-key", "-key", "_key", "key_",
         "ſecret", E4_KELVIN + "ey", "to" + E4_KELVIN + "en", "pa" + E4_LONG_S + "sword", "pa" + E4_LONG_S + "swd", "ǝ", "prıvate_Key", "name", "id",
         "plain", "data", "value", "pass", "pas", "pw", "ke", "toke", "secre"]


@pytest.mark.parametrize("name", E4_NAMES)
@pytest.mark.parametrize("operator", E4_OPERATORS)
def test_e4_names_and_operators_match_old_rule(name, operator):
    for quote in ('"', "'", "`"):
        e4_same(name + operator + quote + E4_VALUE + quote)


def test_e4_the_hand_cases_reach_every_outcome():
    fixed = kept_dummy = kept_nothing = 0
    for name in E4_NAMES:
        for operator in E4_OPERATORS:
            text = name + operator + '"' + E4_VALUE + '"'
            action = e4_same(text)[0]
            fixed += action == "fix"
            kept_dummy += action == "keep" and e4_same(name + operator + '"' + E4_DUMMY + '"')[0] == "keep"
            kept_nothing += action == "keep"
    assert fixed > 100 and kept_dummy > 50 and kept_nothing > 100


@pytest.mark.parametrize("n", [1, 14, 15, 16, 17, 100, 199, 200, 201, 202, 300])
@pytest.mark.parametrize("quote", ['"', "'", "`"])
def test_e4_value_length_edges_match_old_rule(n, quote):
    value = (E4_VALUE * 20)[:n]
    e4_same("key = " + quote + value + quote)
    e4_same("key = " + quote + value)                                   # no closing quote
    e4_same("key = " + quote + value + {'"': "'", "'": "`", "`": '"'}[quote])  # another closing quote


def test_e4_the_value_must_be_16_to_200_characters_and_have_the_same_closing_quote():
    assert e4_same('key = "' + (E4_VALUE * 20)[:15] + '"')[0] == "keep"
    assert e4_same('key = "' + (E4_VALUE * 20)[:16] + '"')[0] == "fix"
    assert e4_same('key = "' + (E4_VALUE * 20)[:200] + '"')[0] == "fix"
    assert e4_same('key = "' + (E4_VALUE * 20)[:201] + '"')[0] == "keep"
    assert e4_same('key = "' + E4_VALUE + "'")[0] == "keep"


E4_STRUCTURE = {
    "empty": "",
    "no word": 'x = "' + E4_VALUE + '"\n',
    "word, no operator": 'the key ' + '"' + E4_VALUE + '"',
    "word and value far apart": "key\n\n\n\n" + 'x = "' + E4_VALUE + '"',
    "value, then the word": 'x = "' + E4_VALUE + '"\nkey',
    "value, then the word, then another assignment": 'x = "' + E4_VALUE + '"\nkey = 1\ny = "short"\n',
    "word inside an earlier name": "monkey_patch_secret_thing = " + '"' + E4_VALUE + '"',
    "json style": '{"api_key": "' + E4_VALUE + '", "name": "x"}',
    "json style with spaces": '{ "api_key" : "' + E4_VALUE + '" }',
    "single quote name": "{'secret': '" + E4_VALUE + "'}",
    "rust type": "const SECRET: &'static str = \"" + E4_VALUE + '";',
    "rust type, no static": 'const KEY: String = "' + E4_VALUE + '";',
    "typescript type": 'const token: string = "' + E4_VALUE + '";',
    "typescript long type": 'const token: Array<Record<string>> = "' + E4_VALUE + '";',
    "type too long": 'const token: ' + "T" * 21 + ' = "' + E4_VALUE + '";',
    "go walrus": 'token := "' + E4_VALUE + '"',
    "arrow": 'token => "' + E4_VALUE + '"',
    "name then newline": "api_key\n= " + '"' + E4_VALUE + '"',
    "operator then newline": 'api_key =\n"' + E4_VALUE + '"',
    "backslash in value": 'key = "' + E4_VALUE[:8] + "\\" + E4_VALUE[8:] + '"',
    "space in value": 'key = "' + E4_VALUE[:8] + " " + E4_VALUE[8:] + '"',
    "dot in value": 'key = "' + E4_VALUE[:8] + "." + E4_VALUE[8:] + '"',
    "a quote inside the value": 'key = "' + E4_VALUE[:8] + "'" + E4_VALUE[8:] + '"',
    "dummy value": 'key = "' + E4_DUMMY + '"',
    "word hyphen name": "my-key = " + '"' + E4_VALUE + '"',
    "hyphen after the word": "token-value = " + '"' + E4_VALUE + '"',
    "hyphens on both sides": "my-secret-id = " + '"' + E4_VALUE + '"',
    "unicode name around": "é" + "key" + "é = " + '"' + E4_VALUE + '"',
    "two assignments": 'key = "' + E4_VALUE + '"\npassword = "' + E4_VALUE[::-1] + '"\n',
    "second one only": 'key = "short"\npassword = "' + E4_VALUE[::-1] + '"\n',
    "the word in a comment": '# key = "' + E4_VALUE + '"',
    "a keyword after a known key": "AKIA" + "A" * 16 + ' and key = "' + E4_VALUE + '"',
    "placeholder makes the word": "AKIA" + "A" * 16 + ' = "' + E4_VALUE + '"',
    "crlf": 'key = "' + E4_VALUE + '"\r\nx = 1\r\n',
    "long file with a late match": "x = 1\n" * 3000 + 'api_key = "' + E4_VALUE + '"\n',
    "long identifier": "a" * 500 + 'key = "' + E4_VALUE + '"',
    "long identifier with no value": "a" * 500 + "key = 1",
}


@pytest.mark.parametrize("name", list(E4_STRUCTURE))
def test_e4_structure_cases_match_old_rule(name):
    e4_same(E4_STRUCTURE[name])
    e4_same(E4_STRUCTURE[name], pack="code-go", lang="go")


def test_e4_the_dotless_and_kelvin_spellings_are_found_through_the_casefold():
    for name in ("ſecret", E4_KELVIN + "ey", "to" + E4_KELVIN + "en", "pa" + E4_LONG_S + "sword"):
        text = name + ' = "' + E4_VALUE + '"'
        assert e4_same(text)[0] == "fix", name
        assert any(w in text.casefold() for w in E4_NEW["ASSIGNED_WORDS"])


# =====================================================================================================================
# The KNOWN keys
# =====================================================================================================================

E4_KNOWN_EXAMPLES = [("AIza" + "A" * 35, 0), ("AKIA" + "A" * 16, 1), ("gh" + "p_" + "a" * 30, 2), ("gh" + "o_" + "a" * 30, 2),
                  ("gh" + "u_" + "a" * 30, 2), ("gh" + "s_" + "a" * 30, 2), ("gh" + "r_" + "a" * 30, 2),
                  ("github_" + "pat_" + "a" * 40, 3), ("s" + "k-" + "a" * 20, 4), ("r" + "k_" + "live_" + "a" * 16, 5),
                  ("s" + "k_" + "live_" + "a" * 16, 5), ("SG." + "a" * 16 + "." + "b" * 16, 6), ("xox" + "b-" + "a" * 10, 7),
                  ("eyJ" + "a" * 10 + ".eyJ" + "b" * 10 + "." + "c" * 10, 8),
                  ("-----BEGIN " + "PRIVATE KEY-----\nx\n-----END " + "PRIVATE KEY-----", 9),
                  ("-----BEGIN " + "RSA PRIVATE KEY-----\nx\n-----END " + "RSA PRIVATE KEY-----", 9)]


@pytest.mark.parametrize("example,i", E4_KNOWN_EXAMPLES)
def test_e4_every_known_key_holds_one_of_the_hints_of_its_pattern_and_is_replaced(example, i):
    assert E4_NEW["KNOWN"][i].search(example)
    assert any(h in example for h in E4_NEW["KNOWN_HINTS"][i])
    for text in (example, "x = " + example + "\n", "a " + example + " b " + example):
        assert e4_same(text)[0] == "fix"
    e4_same("é" + example + "é")                                       # no word boundary before the key: both rules keep it


def test_e4_known_hints_cover_the_patterns():
    assert len(E4_NEW["KNOWN"]) == len(E4_NEW["KNOWN_HINTS"]) == 10
    assert E4_NEW["KNOWN_HINTS"][2] == ("ghp_", "gho_", "ghu_", "ghs_", "ghr_")


@pytest.mark.parametrize("letter", list("abcdefghijklmnopqrstuvwxyz0_-"))
def test_e4_gh_followed_by_any_other_character_matches_old_rule(letter):
    for text in ("gh" + letter + "_" + "a" * 30, "gh" + letter + "a" * 31, "high gh" + letter + " right " + "a" * 40,
                 "gh" + letter + "_" + "a" * 29):
        e4_same(text)


@pytest.mark.parametrize("n", [28, 29, 30, 31])
@pytest.mark.parametrize("letter", list("pousr"))
def test_e4_gh_token_length_edges_match_old_rule(letter, n):
    e4_same("gh" + letter + "_" + "a" * n)
    e4_same("x gh" + letter + "_" + "a" * n + "_ y")


# =====================================================================================================================
# The guards skip ASSIGNED, and run it when they pass
# =====================================================================================================================

def e4_run_with_spies(text):
    ns = e4_namespace()
    spies = {n: Spy(ns[n], m) for n, m in (("ASSIGNED", "sub"), ("VALUE_AFTER_OPERATOR", "search"), ("NAME_WORD_THEN_VALUE", "search"))}
    ns.update(spies)
    result = ns["medicine"](e4_doc(text))
    return result, {n: s.calls for n, s in spies.items()}


def test_e4_a_text_without_a_name_word_runs_no_regex_of_assigned():
    for text in ('x = "' + E4_VALUE + '"\n' * 50, "", "plain text\n" * 100, 'a = "' + "z" * 100 + '"'):
        _, calls = e4_run_with_spies(text)
        assert calls == {"ASSIGNED": 0, "VALUE_AFTER_OPERATOR": 0, "NAME_WORD_THEN_VALUE": 0}, text[:40]


def test_e4_a_text_with_a_word_and_no_value_after_an_operator_runs_only_the_second_test():
    for text in ("the key is here\n" * 50, 'key = 12345\npassword = "short"', 'secret\n"' + E4_VALUE + '"',
                 'key = "' + E4_VALUE[:15] + '"',                                  # 15 characters: one short
                 'key = "' + E4_VALUE[:8] + "\\" + E4_VALUE[8:] + '"',                  # a backslash cuts the run
                 'key = "' + E4_VALUE[:8] + " " + E4_VALUE[8:] + '"', "key = " + '"' + E4_VALUE + "'"):
        _, calls = e4_run_with_spies(text)
        assert calls == {"ASSIGNED": 0, "VALUE_AFTER_OPERATOR": 1, "NAME_WORD_THEN_VALUE": 0}, text[:40]


def test_e4_a_text_with_a_word_and_a_value_but_not_together_stops_at_the_third_test():
    for text in ('x = "' + E4_VALUE + '"\nkey\n', 'key\nx = "' + E4_VALUE + '"', 'y = "' + E4_VALUE + '" # token'):
        _, calls = e4_run_with_spies(text)
        assert calls == {"ASSIGNED": 0, "VALUE_AFTER_OPERATOR": 1, "NAME_WORD_THEN_VALUE": 1}, text[:40]


def test_e4_a_text_that_passes_all_three_runs_assigned_once():
    for text in ('key = "' + E4_VALUE + '"', 'key = "' + E4_DUMMY + '"', "const SECRET: &'static str = \"" + E4_VALUE + '";'):
        _, calls = e4_run_with_spies(text)
        assert calls == {"ASSIGNED": 1, "VALUE_AFTER_OPERATOR": 1, "NAME_WORD_THEN_VALUE": 1}, text[:40]


def test_e4_a_known_key_text_without_a_hint_runs_no_known_pattern():
    ns = e4_namespace()
    spies = [Spy(rx, "sub") for rx in ns["KNOWN"]]
    ns["KNOWN"] = spies
    ns["medicine"](e4_doc("high right light weigh ghost gh_ sk_ xo " * 20))
    assert [s.calls for s in spies] == [0] * 10
    ns["medicine"](e4_doc("a " + "gh" + "p_" + "a" * 30))
    assert [s.calls for s in spies] == [0, 0, 1, 0, 0, 0, 0, 0, 0, 0]


# =====================================================================================================================
# Random documents
# =====================================================================================================================

E4_VALUES = [E4_VALUE, "Zx9Qw7Er5Ty3Ui1Op0", "k3J9s8D7f6G5h4J3k2L1", "0123456789abcdef0123456789abcdef", E4_DUMMY, "x" * 16, "a" * 40,
          "user_profile_settings_v2", "https://example.org/api/v1/x", "a1.b2.c3.d4.e5.f6.g7h8", E4_VALUE[:15], (E4_VALUE * 20)[:200],
          (E4_VALUE * 20)[:201], E4_VALUE[:8] + " " + E4_VALUE[8:], E4_VALUE[:8] + "\\" + E4_VALUE[8:], E4_VALUE[:8] + "'" + E4_VALUE[8:], "AbCdEf123456789012"]
E4_QUOTES = ['"', '"', "'", "`"]
E4_FILLER = ["x = 1", "def f(a, b):", "    return a + b", "// comment", "# comment", "const y = compute(3);", "fn main() {}",
          "import os", "key", "token", "the key to it", "A = 'short'", "name = " + '"' + "n" * 30 + '"', "url = 'http://a.b/c/d/e/f'", "}", "", "tokens",
          "password", "keys: [1, 2]", "monkey", "secrets", "ſ", E4_KELVIN]
E4_TYPES = ["", "", "", ": &'static str", ": String", ": string", ": Array<number>", ": " + "T" * 21]
E4_SEPS = ["\n", "\n", " ", "; ", "\r\n", "\n\n"]


def e4_piece(rng):
    if rng.random() < 0.55:
        return rng.choice(E4_FILLER)
    q = rng.choice(E4_QUOTES)
    close = q if rng.random() < 0.9 else rng.choice(E4_QUOTES)
    return (rng.choice(E4_NAMES) + rng.choice(["", "", '"', "'"]) + rng.choice(E4_TYPES) + rng.choice(E4_OPERATORS)
            + q + rng.choice(E4_VALUES) + close + rng.choice(["", ";", ","]))


def e4_random_text(rng):
    return rng.choice(E4_SEPS).join(e4_piece(rng) for _ in range(rng.randint(0, 8)))


def test_e4_random_texts_match_old_rule_and_cover_every_outcome():
    rng = random.Random(404)
    ns = E4_NEW
    stage = {"no word": 0, "no value after operator": 0, "no word then value": 0, "assigned ran": 0, "assigned matched": 0,
             "fix": 0, "keep": 0, "assigned matched but kept": 0}
    for _ in range(25000):
        text = e4_random_text(rng)
        new = e4_same(text)
        stage[new[0]] += 1
        low = text.casefold()
        if not any(w in low for w in ns["ASSIGNED_WORDS"]):
            stage["no word"] += 1
        elif not ns["VALUE_AFTER_OPERATOR"].search(text):
            stage["no value after operator"] += 1
        elif not ns["NAME_WORD_THEN_VALUE"].search(text):
            stage["no word then value"] += 1
        else:
            stage["assigned ran"] += 1
            if ns["ASSIGNED"].search(text):
                stage["assigned matched"] += 1
                stage["assigned matched but kept"] += new[0] == "keep"
        # whenever ASSIGNED matches, all three tests pass: the tests are necessary on every one of these texts
        if ns["ASSIGNED"].search(text):
            assert any(w in low for w in ns["ASSIGNED_WORDS"]) and ns["VALUE_AFTER_OPERATOR"].search(text) \
                and ns["NAME_WORD_THEN_VALUE"].search(text), text[:200]
    assert all(v > 150 for v in stage.values()), stage


def test_e4_random_texts_with_a_known_key_match_old_rule():
    rng = random.Random(405)
    keys = [k for k, _ in E4_KNOWN_EXAMPLES] + ["gh" + "p_" + "a" * 29, "AKIA" + "A" * 15, "gh" + "x_" + "a" * 40, "ghp" + "a" * 40]
    fixed = 0
    for _ in range(6000):
        parts = [rng.choice(keys) if rng.random() < 0.5 else e4_piece(rng) for _ in range(rng.randint(1, 6))]
        fixed += e4_same(rng.choice(E4_SEPS).join(parts))[0] == "fix"
    assert fixed > 3000


def test_e4_the_rule_in_clean_py_acts_only_on_the_code_packs_and_equals_the_old_rule():
    new_rule = c._RULE["DA-E3-004"]()
    text = 'key = "' + E4_VALUE + '"\n'
    for pack in CODE_PACKS:
        assert new_rule(e4_doc(text, pack=pack)) == E4_OLD(e4_doc(text, pack=pack)) == ("fix", 'key = "EXAMPLE_SECRET"\n')
    for pack in ("en-dclm", "math-finemath", "ind-hi-fw2", None):
        assert new_rule(e4_doc(text, pack=pack)) == E4_OLD(e4_doc(text, pack=pack)) == ("keep", text)
