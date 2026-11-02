# medicine_math: math medicines (Spec v1.1)

Packs: finemath 86, megamath 26 gold docs (Data A gold, refreshed 31 Oct on `g1-harm-test`; the limit is 1 document on both, as with the earlier 30 / 18). Each pack is tested on its own gold set.
Rule form: as `medicine_code.md`. `doc = {doc_id, text, url, lang_label, pack_id}`. Both math packs carry the `en` tag, so each rule also checks `pack_id` against `ORIGIN`; a doc with no `pack_id` passes unchanged.
Run order is section order, by stage: 10 characters, 20 markup, 30 source (drops, then strips). F1 is the one shared rule in `../tools/f1_rule.py`, not in this sheet.
v1.1: the finemath rules are now SomaKorada07's own functions from her sheet (theschoolofai/era-v5-lab#61, commit cc74c7e), copied unchanged with only the rule fields, the `pack_id` guard and non-ASCII characters written as `\u` escapes added. They replace kunal2016's v1 rewrites of the same medicines and add A6 and D3. `DA-C5-001` is kunal2016's megamath medicine (#151).
IDs are unique inside this sheet; `clean.py` adds the family. Limit: changed + dropped at most `max(1, floor(1% of gold))`. Reasons: `decisions_math.md`.

Each cell: gold harm % (gold docs changed or dropped / gold docs), the result at the limit, and the labelled rows the rule treats / the labelled rows with its code. `off` = not in `ORIGIN`.

| # | ID | disease | action | stage | source | finemath | megamath |
|---|---|---|---|---|---|---|---|
| 1 | `DA-A3-001` | A3 mojibake | fix | 10 | math-finemath | 0.00% (0/86) PASS · 10/11 | 0.00% (0/26) PASS · 8/21 |
| 2 | `DA-A1-001` | A1 invisible junk characters | fix | 10 | math-finemath | 0.00% (0/86) PASS · 14/15 | off |
| 3 | `DA-A6-001` | A6 symbol-font and look-alike glyphs | fix | 10 | math-finemath | 0.00% (0/86) PASS · 5/9 | off |
| 4 | `DA-A5-001` | A5 compatibility forms | fix | 10 | math-finemath | 0.00% (0/86) PASS · 6/6 | 0.00% (0/26) PASS · 9/12 |
| 5 | `DA-B2-001` | B2 HTML tags | fix | 20 | math-finemath | 0.00% (0/86) PASS · 3/8 | 0.00% (0/26) PASS · 6/112 |
| 6 | `DA-B4-001` | B4 template junk | fix | 20 | math-finemath | 0.00% (0/86) PASS · 9/18 | 0.00% (0/26) PASS · 1/10 |
| 7 | `DA-B5-001` | B5 broken LaTeX or markdown | fix | 20 | math-finemath | 0.00% (0/86) PASS · 5/28 | 0.00% (0/26) PASS · 1/192 |
| 8 | `DA-C5-001` | C5 SEO / link lists | drop | 30 | math-megamath | off | 0.00% (0/26) PASS · 10/168 |
| 9 | `DA-D3-001` | D3 mixed-in foreign script | fix+drop | 30 | math-finemath | 0.00% (0/86) PASS · 5/10 | 0.00% (0/26) PASS · 2/9 |
| 10 | `DA-C3-001` | C3 truncated document | drop | 30 | math-finemath | 0.00% (0/86) PASS · 10/50 | off |
| 11 | `DA-C1-001` | C1 boilerplate | fix | 30 | math-finemath | 0.00% (0/86) PASS · 109/328 | off |
| 12 | `DA-C2-001` | C2 repeated lines or passages | fix | 30 | math-finemath | 0.00% (0/86) PASS · 40/187 | off |
| 13 | `DA-C5-002` | C5 SEO / link lists | fix | 30 | math-finemath | 0.00% (0/86) PASS · 5/51 | 0.00% (0/26) PASS · 2/168 |
| 14 | `DA-C3-002` | C3 truncated document | fix | 30 | math-finemath | 0.00% (0/86) PASS · 5/50 | off |

## 1. `DA-A3-001` · A3 mojibake · fix · stage 10

1. **Disease:** A3, 11 documents. `c9e5d27233084b62` "â€™" @178 (x24; U+00E2 U+20AC U+2122); `ab295000bded241a` "ðŸ˜€" @118; `f79e6aeb5ebb6a5c` "тАЩ" @4628 (UTF-8 read as cp866).
2. **Medicine:** a short run starting with a UTF-8 lead byte seen as cp1252 (`Â Ã â ð Ð Ñ à á ä`) is re-encoded as cp1252 and decoded as UTF-8; kept only if that succeeds and is shorter. Same for cp866 `т[АБ].`.

```python
RULE_ID = "DA-A3-001"
CODE = "A3"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# cp1252 characters for the bytes 0x80-0x9F
A3_CP1252_EXTRA = "\u20ac\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\u017d\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\u017e\u0178"
# lead chars are the usual UTF-8 lead bytes seen as cp1252; not U+00D7 (x + no-break space is real maths)
A3_MOJI = re.compile("[\u00c2\u00c3\u00e2\u00f0\u00d0\u00d1\u00e0\u00e1\u00e4][\u0080-\u00bf\u00a0-\u00bf" + A3_CP1252_EXTRA + "]{1,3}")
A3_CP866 = re.compile("\u0442[\u0410\u0411][\u0400-\u04ff]")    # UTF-8 read as cp866: "\u0442\u0410\u0429" is a right quote

def _a3_undo(m, enc):
    s = m.group()
    try:
        out = s.encode(enc).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    return out if len(out) < len(s) else s

def medicine_a3(text):
    t = A3_MOJI.sub(lambda m: _a3_undo(m, "cp1252"), text)
    return A3_CP866.sub(lambda m: _a3_undo(m, "cp866"), t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a3(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** the first version accepted any Latin-1 lead and turned `×`+NBSP into Hebrew `נ` in 2 clean documents; the lead set is now restricted. Real Latin-1 text could still be "repaired" when the run happens to decode as UTF-8 (rare).
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 2. `DA-A1-001` · A1 invisible junk characters · fix · stage 10

1. **Disease:** A1, 15 documents. `064d8dd19536d1d8` U+200E LRM @9 (x2); `8f09ea36d06abaef` U+00AD soft hyphen @3180 (x4); `263a5308b96d2e4a` U+200B @6754.
2. **Medicine:** delete U+200B, U+FEFF, U+00AD, U+200E, U+200F, U+2060, U+202A–U+202E, U+2066–U+2069. ZWJ/ZWNJ are never touched (ruling 12).

```python
RULE_ID = "DA-A1-001"
CODE = "A1"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# ZWJ U+200D / ZWNJ U+200C are left alone on purpose (they are script, not junk)
A1_RX = re.compile("[\u200b\ufeff\u00ad\u200e\u200f\u2060\u202a-\u202e\u2066-\u2069]")

def medicine_a1(text):
    return A1_RX.sub("", text)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a1(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** a ZWSP used as the only word separator joins two words. LRM/RLM matter in RTL text (safe in this English pack; do not run on RTL packs). U+2062 INVISIBLE TIMES in MathML text (1 document) is not removed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 3. `DA-A6-001` · A6 symbol-font and look-alike glyphs · fix · stage 10

1. **Disease:** A6, 9 documents. `9be631b8d8a8b294` U+F0C5 @6107 (should be ⊕); `c46f9ecdfac73e93` U+F0D8 @875 (x9); `f2746fa01fbc3cf4` "fɑstidious" @4992 (U+0251 U+0455 U+0461).
2. **Medicine:** map U+F000+code to the Symbol-font character for 46 codes (`(`, `)`, `=`, `⊕`, `∂`, Greek, brackets, …); leave other private-use characters.

```python
RULE_ID = "DA-A6-001"
CODE = "A6"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
# PDFs set in the Symbol font leak U+F0xx = U+F000 + Symbol code. Map the ones seen in the pack; leave the rest.
A6_SYMBOL = {0x28: "(", 0x29: ")", 0x2B: "+", 0x2D: "\u2212", 0x3D: "=", 0x44: "\u0394", 0x53: "\u03a3", 0x57: "\u03a9",
             0x61: "\u03b1", 0x62: "\u03b2", 0x64: "\u03b4", 0x67: "\u03b3", 0x6C: "\u03bb", 0x6D: "\u03bc", 0x70: "\u03c0",
             0x71: "\u03b8", 0x72: "\u03c1", 0x77: "\u03c9", 0xA3: "\u2264", 0xA5: "\u221e", 0xA8: "\u2666", 0xAE: "\u2192",
             0xB1: "\u00b1", 0xB3: "\u2265", 0xB4: "\u00d7", 0xB6: "\u2202", 0xB7: "\u2022", 0xB9: "\u2260", 0xBB: "\u2248",
             0xC5: "\u2295", 0xC7: "\u2229", 0xC8: "\u222a", 0xCE: "\u2208", 0xD6: "\u221a", 0xD8: "\u00ac", 0xDE: "\u21d2",
             0xE5: "\u2211", 0xE6: "\u239b", 0xE7: "\u239c", 0xE8: "\u239d", 0xF2: "\u222b", 0xF6: "\u239e", 0xF7: "\u239f",
             0xF8: "\u23a0"}
A6_PUA_MAP = {0xF000 + k: v for k, v in A6_SYMBOL.items()}

def medicine_a6(text):
    return text.translate(A6_PUA_MAP)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a6(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** Wingdings uses the same code points: U+F0D8 as an arrow bullet becomes `¬`. Look-alike letters in spam (`fɑstidious`) and the Armenian apostrophe in `Math՚s` are not fixed (recall 5 / 9).
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 4. `DA-A5-001` · A5 compatibility forms · fix · stage 10

1. **Disease:** A5, 6 documents. `c16db13d63739369` "ﬀ" @313 (x91 ligatures: ﬀ ﬁ ﬂ ﬃ, U+FB00 U+FB01 U+FB02 U+FB03); `ce9b0d519779eba2` "ﬀ" @68 (x17); `addb07a0a886743c` fullwidth comma "，" @2666 (x2, U+FF0C) in English text translated from Chinese.
2. **Medicine:** replace the ligatures U+FB00–U+FB06 by their NFKC letters (ﬁ → fi, ﬀ → ff); replace fullwidth ASCII punctuation U+FF01–U+FF5E by the ASCII character, but only in documents where CJK characters are under 1% of the letters (real Chinese/Japanese text keeps its punctuation).

```python
RULE_ID = "DA-A5-001"
CODE = "A5"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re
import unicodedata

A5_LIG = re.compile("[\ufb00-\ufb06]")
A5_FULLWIDTH = re.compile("[\uff01-\uff5e]")
A5_CJK = re.compile("[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]")

def medicine_a5(text):
    out = A5_LIG.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)      # ligature to letters
    letters = sum(c.isalpha() for c in out) or 1
    if len(A5_CJK.findall(out)) / letters < 0.01:                                    # leave real CJK text alone
        out = A5_FULLWIDTH.sub(lambda m: chr(ord(m.group()) - 0xFEE0), out)          # fullwidth to ASCII
    return out


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a5(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** a document that quotes a ligature as a character (a typography page) would lose it. Fullwidth digits in English text become ASCII digits, which is wanted here. Full NFKC is not applied: it would also change superscripts (x² → x2) and other maths symbols.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 5. `DA-B2-001` · B2 HTML tags · fix · stage 20

1. **Disease:** B2, 8 documents. `bf73e54bda1aabdb` "<br />" @367 (x18); `addb07a0a886743c` "<ul>" @6030; `951a4c150e019bd5` "</Math>" @22663.
2. **Medicine:** `<br>` → newline; remove simple formatting tags (`p div span a ul ol li sup sub strong em font b i center`); skip documents with a code fence or `<script>`.

```python
RULE_ID = "DA-B2-001"
CODE = "B2"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

B2_BR = re.compile(r"<br\s*/?>", re.I)
B2_TAG = re.compile(r"</?(?:div|span|p|a|ul|ol|li|sup|sub|strong|em|font|b|i|center)"
                    r"(?:\s+[\w-]+=(?:\"[^\"]*\"|'[^']*'|[^\s>]+))*\s*/?>", re.I)

def medicine_b2(text):
    if "```" in text or "<script" in text.lower():      # tags inside code are content
        return text
    return B2_TAG.sub("", B2_BR.sub("\n", text))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_b2(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** `x<sup>2</sup>` becomes `x2`. Recall 3 / 8: tags inside documents that also contain code, and broken fragments like `strong> Option`, are left.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 6. `DA-B4-001` · B4 template junk · fix · stage 20

1. **Disease:** B4, 18 documents. `2d9c3add6852f806` "{{ 'ml-label-loading-course' | message }}" @0 (x14); `56027551326bb040` "{[ snackBarMessage ]}" @1482; `e967e3352605755f` "[TheoryMissing]" @102.
2. **Medicine:** delete `{[ name ]}`, `{{ name.attr | filter }}` (spaces inside, so LaTeX `{{x}}` is not hit), `{% … %}`, `[TheoryMissing]`, `document.write(…)`.

```python
RULE_ID = "DA-B4-001"
CODE = "B4"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

B4_RX = re.compile(r"\{\[\s*\w+\s*\]\}|\{\{\s+['\w][\w'.| :-]*\s+\}\}|\{%.*?%\}|\[TheoryMissing\]|"
                   r"document\.write\([^)]*\);?|^\s*\"?\s*%\}\s*$", re.M)

def medicine_b4(text):
    out = B4_RX.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", out) if out != text else text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** a tutorial that teaches Angular/Jinja templates would lose its examples. Recall 9 / 18: AsciiMath leftovers such as `color(blue)(` are not covered.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 7. `DA-B5-001` · B5 broken LaTeX or markdown · fix · stage 20

1. **Disease:** B5, 28 documents. `e73db44e20a89b36` "$$$where" @241 (x4); `951a4c150e019bd5` "[itex]" @23031; `3a2ccc88dfcd67c9` unclosed ``` fence @12634.
2. **Medicine:** exactly `$$$` → `$$`; forum BBCode `[itex] [/itex] [tex] [/tex] [math]` → `$`; an odd number of ``` fences gets a closing fence at the end.

```python
RULE_ID = "DA-B5-001"
CODE = "B5"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

B5_TRIPLE = re.compile(r"(?<!\$)\${3}(?!\$)")                  # exactly $$$ ($$$$ is two blocks, valid)
B5_BBCODE = re.compile(r"\[/?(?:itex|tex|math)\]", re.I)       # forum BBCode math

def medicine_b5(text):
    out = B5_BBCODE.sub("$", B5_TRIPLE.sub("$$", text))
    if out.count("```") % 2:                                    # unclosed code fence at the end
        out = out.rstrip() + "\n```"
    return out


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_b5(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** found while testing: `$$$$` is two adjacent display blocks and is valid (`3e136806c369dfbc`), so only exactly three dollars are changed. A literal `[math]` in prose becomes `$`. Recall 5 / 28: stray `$$` inside inline math (`3f15fccd9f76020b`) and LaTeX with stripped backslashes (`$mathbb`) cannot be repaired by rule.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 8. `DA-C5-001` · C5 SEO / link lists · drop · stage 30

1. **Disease:** C5 SEO / link lists: answers.com "related questions" pages. Seen 4 of 100 in rows 401-500 (450, 480, 483, 499; asraj labels the same 4 drop), 10 of 500 in the pack.
2. **Medicine:** Every one has the same layout: "Study guides", the question, "Write your answer... / Submit", then a list of snippets from other questions. The page's own question is never answered. Drop the document when it starts with exactly that header. Nothing else in the pack starts this way.

```python
RULE_ID = "DA-C5-001"
CODE = "C5"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-megamath"  # pack whose medicine this came from
AUTHOR = "kunal2016"
import re

ANSWERS = re.compile(r"\AStudy guides\s*\n\s*Q: .{1,300}\n\s*Write your answer\.\.\.\s*\n\s*Submit\s*\n\s*Related questions\s*\n")

def cure_c5(text):
    if ANSWERS.match(text):
        return ("drop", "")
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(cure_c5(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** megamath.
4. **Harm test:** megamath 0.00% (0/26) PASS.
5. **Side effects:** an answers.com page that does carry an answer below "Related questions" is also dropped (none seen in this pack). Matching is anchored at the start of the text, so a quotation of the header inside another document is not touched.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: kunal2016, megamath sheet, PR 151. Idempotent on every doc of its packs.

## 9. `DA-D3-001` · D3 mixed-in foreign script · fix+drop · stage 30

1. **Disease:** D3, 10 documents. `b605c8aa5c37f266` Japanese title "ベクトル…" @23; `f2746fa01fbc3cf4` Ukrainian ad lines "Дивитися фільми…" @10238 (x4); `8210e5fa65c2f665` Marathi intro "पाईये" @144.
2. **Medicine:** delete a line when more than half of its letters are Cyrillic, Indic, CJK, kana, Hangul or Arabic; if such lines hold more than 30% of the document's letters, drop the document (that is D1).

```python
RULE_ID = "DA-D3-001"
CODE = "D3"
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# Cyrillic, Indic, kana, CJK, Hangul, Arabic (Greek is left out: Greek letters are maths)
D3_FOREIGN = re.compile("[\u0400-\u04ff\u0900-\u0dff\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af\u0600-\u06ff]")

def medicine_d3(text):
    out, foreign = [], 0
    for l in text.split("\n"):
        letters = sum(c.isalpha() for c in l)
        f = len(D3_FOREIGN.findall(l))
        if letters and f / letters > 0.5:      # a line that is mostly foreign script is removed
            foreign += f
            continue
        out.append(l)
    total = sum(c.isalpha() for c in text)
    if total and foreign / total > 0.3:        # mostly not English: that is D1, drop
        return ("drop", text)
    return "\n".join(out)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_d3(doc["text"]), doc["text"])
```

3. **Action:** fix+drop. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** a legitimate quotation or title in another language is removed (DISEASES.md says D3 can be natural). Greek is excluded on purpose, since Greek letters are maths.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 10. `DA-C3-001` · C3 truncated document · drop · stage 30

1. **Disease:** C3, 49 documents. `de1b08a158de9ae9` Course Hero preview cut at "s[R2(Cgs" @3238; `9d26c83f14d2087f` "We hav" @772 (paywall); `4e1e6a7902a4435e` teaser ending "deeper unders..." @6566.
2. **Medicine:** drop a document that carries a preview/paywall banner (`This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections`); if a document ends in a teaser cut (`word...` or `word…`), trim back to the last full sentence. This block keeps only the medicine's drop (previews); `DA-C3-002` keeps only its trim, after the strips.

```python
RULE_ID = "DA-C3-001"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C3_PREVIEW = re.compile(r"This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections")
C3_TEASER = re.compile(r"\w(?:\.\.\.|\u2026)$")

def medicine_c3(text):
    if C3_PREVIEW.search(text):                     # paywall / preview page: cut by design
        return ("drop", text)
    s = text.rstrip()
    if C3_TEASER.search(s):                         # teaser cut: "...deeper unders..."
        last_stop = max(s.rfind(". ", 0, len(s) - 3), s.rfind(".\n", 0, len(s) - 3))
        return s[:last_stop + 1] if last_stop > 0 else text
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    out = medicine_c3(doc["text"])
    return ("drop", doc["text"]) if _std(out, doc["text"])[0] == "drop" else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** a good document that merely quotes "View Full Document" would be dropped. Recall 15 / 49: a document that stops mid-solution with no marker (`b6a1ee1fa12a6d5e` code cut at @4908) cannot be detected by a rule. A first version that trimmed every last line without end punctuation changed 6 of 117 clean documents (headings, signatures, answer lists) and was replaced.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 11. `DA-C1-001` · C1 boilerplate · fix · stage 30

1. **Disease:** C1, 328 documents (most web pages keep some site chrome). `72f073c36305b095` "posted by gamer chick" @13; `de1b08a158de9ae9` "This preview shows page" @95; `92bef36fe0c0fc40` "Replies / Views" related-thread blocks @9487.
2. **Medicine:** delete a line that is a known chrome phrase (`C1`), or that contains a site-chrome phrase (`C1_SITE`, ~70 phrases seen in this pack: GMAT Club headers, "View Full Document", OEIS footer, "My Personal Notes arrow_drop_up", …) and is at most 120 characters; delete `Replies\n<n>\nViews\n<n>` blocks.

```python
RULE_ID = "DA-C1-001"
CODE = "C1"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

# a whole line that is generic site chrome
C1_LINE = re.compile(
    r"(?i)\s*(?:More Similar Questions|Similar Questions|Related (?:Questions|Posts|Articles)|Share (?:this|on \w+)|"
    r"Sign ?up|Log ?in|Subscribe|Cookie|Accept (?:all )?cookies|Privacy Policy|Terms of (?:Use|Service)|"
    r"All rights reserved|\u00a9.*|&copy;.*|Follow us|Skip to (?:main )?content|Show Tags|Replies|Views|"
    r"Contact - Home.*|Report (?:abuse|post)|Upvote|Downvote|Like this:|Loading\.\.\.|Previous Post|Next Post|"
    r"Recommended|Back to top|Quick Reply|Click here.*|Leave a (?:Reply|Comment)|Your email address will not be published.*|"
    r"Posted by.*|Tags?:.*|Categories?:.*|Hide Tags|Join (?:now|us)|Download (?:the )?App.*|Course Hero.*)\s*")
# site chrome seen in this pack (forums, homework sites, document hosts, OEIS, GMAT Club ...); only on lines <= 120 chars
C1_SITE = re.compile(
    r"(?i)Check GMAT Club Decision Tracker|It is currently \d+ \w+ \d{4}|GMAT Club Daily Prep|Display posts from previous|"
    r"GMAT\u00ae test is a registered trademark|\[#permalink\]|Kudos \[\?\]|This preview shows page|Sign up to view the full|"
    r"View Full Document|Ask a homework question|intentionally blurred sections|My Personal Notes arrow_drop_up|"
    r"^Open in App$|^Last Updated :|All times are GMT|The time now is \d{1,2}:\d{2}|Privacy Statement|"
    r"Remember Me\? Password|having trouble loading external resources|analy[sz]e our traffic|Want to see this answer and more|"
    r"^See Solution$|^Subscribe now$|Upcoming SlideShare|Are you sure you want to|Report Content as Inappropriate|"
    r"Open this post in threaded view|^Loading content$|The OEIS Community \| Maintained by|supported by donations|"
    r"You are Here: Home|Registered Office:|CYBER MONDAY|^Wiki User$|^Buscar$|^Uncategorized$|Created with Sketch|"
    r"best freelance writing portal|Comment sent successfully|Choose the classification system|Read More \u00bb|"
    r"TUTORIALS HOME|Top of Page|Our sister site|Everything was clear\?|Hello Guest!|Free\s+Algebra Tutorials!|"
    r"Teach yourself statistics|^Home >>|\u200e > \u200e|claim an answer you\u2019ll have 24 hours|Search Our Content Library|"
    r"filtered results|^Sort by$|tutors are online|snackBarMessage|Go To Main Page|^Show/hide solution$|"
    r"Correct! Wrong!|Tutorial is loading|^Filed Under:|^Exam Prep:|^Asked in:|Verified Answer \| Published|"
    r"^Guided Lessons$|^Course Content$|Doorsteptutor|Mark Forums Read|^Recommended$|DocShare\.tips|^Hide$|"
    r"Not now$|Write an Interview Experience|Your message has been successfully submitted|has the best spam protection|"
    r"posting guide http|Questions are from the workbook|^Share$|^Children$|Go back to editing|try BYJU|We\u2018ve got your back")
# phpBB "Replies / <n> / Views / <n>" block, one value per line
C1_REPLIES = re.compile(r"(?m)^Replies\n\d+\nViews\n[\d.]+K?\n?")

def medicine_c1(text):
    keep = [l for l in text.split("\n")
            if not (C1_LINE.fullmatch(l) or (C1_SITE.search(l) and len(l) <= 120))]
    return C1_REPLIES.sub("", "\n".join(keep))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c1(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** recall is only 109 / 328: the phrase list is fitted to sites seen here, so new sites' menus and footers are missed. A forum title ending in `[#permalink]` is removed (the question usually repeats in the post). A real line that is only "Share", "Views" or "Tags:" would be removed. Found and fixed while testing: "The time now is" deleted the problem statement "If the time now is 9 o'clock" (now needs hh:mm).
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 12. `DA-C2-001` · C2 repeated lines or passages · fix · stage 30

1. **Disease:** C2, 187 documents. `92bef36fe0c0fc40` "• Introductory Physics Homework Help" @9487 (x10); `98e5be6db6c1c81e` "Mathematical Practice 3: Construct viable…" @2979 (x2); `e9bc93d8821adcec` the same reading passage before each question (x4–5).
2. **Medicine:** (a) a non-code line of 15+ characters that appears 5+ times keeps only its first copy; (b) a passage (blank-line block, 150+ characters, not a bullet list, not answer options, not code) that appears more than once keeps only its first copy (ruling 13).

```python
RULE_ID = "DA-C2-001"
CODE = "C2"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C2_CODE = re.compile(r"[;{}]\s*$|^\s*(?:for|if|while|return|def|class)\b")
C2_PARA_SPLIT = re.compile(r"(\n\s*\n)")
C2_OPTION = re.compile(r"\s*(?:[A-E1-5][.)]|\(?[a-e]\))\s")

def _c2_dedupe_passages(text):
    # ruling 13: a passage (150+ chars) repeated even once loses its later copies; option lists and code are kept
    parts, seen, out = C2_PARA_SPLIT.split(text), set(), []
    for k, part in enumerate(parts):
        q = part.strip()
        if k % 2 == 0 and len(q) >= 150 and not re.match(r"\s*[\u2022*-] ", q):
            ql = [x for x in q.splitlines() if x.strip()]
            options = sum(bool(C2_OPTION.match(x)) for x in ql) >= max(2, len(ql) // 2)
            code = sum(bool(re.search(r"[;{}]\s*$", x)) for x in ql) >= max(1, len(ql) // 3)
            if not options and not code:
                if q in seen:
                    if out and k > 0:
                        out.pop()          # drop the blank-line separator before the copy
                    continue
                seen.add(q)
        out.append(part)
    return "".join(out)

def medicine_c2(text):
    lines = text.split("\n")
    counts = {}
    for l in lines:
        counts[l.strip()] = counts.get(l.strip(), 0) + 1
    seen, out = set(), []
    for l in lines:
        s = l.strip()
        if len(s) >= 15 and counts[s] >= 5 and not C2_CODE.search(s):
            if s in seen:
                continue
            seen.add(s)
        out.append(l)
    return _c2_dedupe_passages("\n".join(out))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c2(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** the proxy change is natural restatement: an author repeats a sentence on purpose (`5ee756dbf1307a6f`) and the copy is lost. Repeated per-question passages (`e9bc93d8821adcec`) lose their later copies, so later questions lose their context. Recall 40 / 187: short repeated titles and quoted questions under 150 characters are kept.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 13. `DA-C5-002` · C5 SEO / link lists · fix · stage 30

1. **Disease:** C5, 50 documents. `25901665fc855b35` "See more: What Did Greg Giraldo…" @3568; `b124803aff87e2d9` "Domain And Range Notes Teachers Pay Teachers…" @5708; `1eff00a48b3b10a0` SEO FAQ farm.
2. **Medicine:** delete lines starting `See more:` and lines made of 5+ comma-separated Title-Case phrases of 2–8 words.

```python
RULE_ID = "DA-C5-002"
CODE = "C5"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C5_SEO = re.compile(r"(?m)^(?:See more: .*|(?:[A-Z][\w\u2019'&.-]*(?: [\w\u2019'&.-]+){1,7}, ){5,}.*)$")

def medicine_c5(text):
    return C5_SEO.sub("", text)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c5(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:** recall is 5 / 50: most C5 here is whole spun/SEO pages, which only a drop decision handles. A real comma list of Title-Case names (bibliography, theorem names) would be deleted.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.

## 14. `DA-C3-002` · C3 truncated document · fix · stage 30

1. **Disease:** C3, 49 documents. `de1b08a158de9ae9` Course Hero preview cut at "s[R2(Cgs" @3238; `9d26c83f14d2087f` "We hav" @772 (paywall); `4e1e6a7902a4435e` teaser ending "deeper unders..." @6566.
2. **Medicine:** drop a document that carries a preview/paywall banner (`This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections`); if a document ends in a teaser cut (`word...` or `word…`), trim back to the last full sentence. This block keeps only the medicine's trim (teaser cuts); its drop runs earlier as `DA-C3-001`.

```python
RULE_ID = "DA-C3-002"
CODE = "C3"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose medicine this came from
AUTHOR = "SomaKorada07"
import re

C3_PREVIEW = re.compile(r"This preview shows|Sign up to view the full|View Full Document|intentionally blurred sections")
C3_TEASER = re.compile(r"\w(?:\.\.\.|\u2026)$")

def medicine_c3(text):
    if C3_PREVIEW.search(text):                     # paywall / preview page: cut by design
        return ("drop", text)
    s = text.rstrip()
    if C3_TEASER.search(s):                         # teaser cut: "...deeper unders..."
        last_stop = max(s.rfind(". ", 0, len(s) - 3), s.rfind(".\n", 0, len(s) - 3))
        return s[:last_stop + 1] if last_stop > 0 else text
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    out = medicine_c3(doc["text"])
    return ("keep", doc["text"]) if _std(out, doc["text"])[0] == "drop" else _std(out, doc["text"])
```

3. **Action:** fix. **Runs on:** finemath.
4. **Harm test:** finemath 0.00% (0/86) PASS.
5. **Side effects:** a good document that merely quotes "View Full Document" would be dropped. Recall 15 / 49: a document that stops mid-solution with no marker (`b6a1ee1fa12a6d5e` code cut at @4908) cannot be detected by a rule. A first version that trimmed every last line without end punctuation changed 6 of 117 clean documents (headings, signatures, answer lists) and was replaced.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: SomaKorada07's finemath sheet, theschoolofai/era-v5-lab#61 (cc74c7e): her function, unchanged. Idempotent on every doc of its packs.
