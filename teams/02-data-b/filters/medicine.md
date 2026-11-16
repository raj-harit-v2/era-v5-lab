# medicine.md: Indic filters of Data B (issue #214, G2)

The format is the one `tools/harm_test_indic.py` reads: one `**Disease:** <code>` line per filter, and a function
`medicine_<code>(text)`. A rule returns the new text, or `True` to drop the document, or `False` to keep it.
No filter here removes or adds a ZWJ (U+200D) or ZWNJ (U+200C); `test_filters.py` counts both before and after, and
`run_harm.py` writes the same counts for each pack's gold set. NFC is the only normal form used, never NFKC.

Filters in this file, in run order (the harm tool's "ALL IN ORDER" row runs them in this order):

| Code | Filter | Whose code |
|---|---|---|
| D1 | Script share: drop a document where another script dominates | Data B (new: no author had a D1 rule) |
| A1 | Invisible junk characters, keeping ZWJ and ZWNJ | the author's: adinathauti, PR #114 (faster than #109's, same output); marked: escapes, and the name |
| G1 | Broken vowel sign, for Kannada, Devanagari, Malayalam, Tamil and Odia | the authors' code for each script, renamed so five functions fit one `medicine_g1`; the one added function picks the script |

**The rule for authors' code.** #211 (TSAI's Data B rules task) says "Keep each author's code as they wrote it, and mark
anything you add to make it fit", and `indic_rules/README.md` (PR #240) repeats it: the author's code unchanged, and
what Data B changes is marked in the code and listed. The only other changes allowed so far are TSAI's rulings
(#240: a visarga used as a colon is clean, also with a space before it, so it stays as written). So here the
authors' bodies are copied as they are; each change is a line marked `# added by Data B`, or `# Data B:` with the reason.

## Medicine 1: script share

1. **Disease:** D1 Wrong language label. A document whose letters are mostly in another script than the pack's. No Data B rule covered D1 in any pack. Readers marked it in 38 rows of 10 packs (ind-te-sangraha-v 12, ind-sa-fw2 6, ind-hi-hplt 4).
2. **Medicine:** `medicine_d1(text)`. Count the letters of the document by script (letters and combining signs only; digits, punctuation, dandas, spaces and ZWJ/ZWNJ are not counted). The share of the pack's script is its count divided by all letters. The pack's script comes from the environment variable `D1_SCRIPT` (`Devanagari`, `Bengali`, `Gujarati`, `Odia`, `Tamil`, `Telugu`, `Kannada`, `Malayalam`), which `run_harm.py` sets for each pack. Without `D1_SCRIPT` the rule asks only that the document is mostly in some Indic script.
   - share 0.50 or more: keep.
   - share under 0.30 and another script is the largest: drop (`_DROP_BELOW`).
   - in between: a flag (`_d1_decision` returns `"flag"`), and the document is kept. A few English words never get a document dropped.
   - fewer than 20 letters: keep, there is too little to judge.
   - NFC is used to count (never NFKC), and the text is never changed.

```python
import functools
import os
import unicodedata
from collections import Counter

# Unicode blocks of the Indic scripts, written as numbers (the standard library has no script property).
_SCRIPT_RANGES = {
    "Devanagari": ((0x0900, 0x097F), (0xA8E0, 0xA8FF), (0x1CD0, 0x1CFF)),
    "Bengali": ((0x0980, 0x09FF),),
    "Gurmukhi": ((0x0A00, 0x0A7F),),
    "Gujarati": ((0x0A80, 0x0AFF),),
    "Odia": ((0x0B00, 0x0B7F),),
    "Tamil": ((0x0B80, 0x0BFF),),
    "Telugu": ((0x0C00, 0x0C7F),),
    "Kannada": ((0x0C80, 0x0CFF),),
    "Malayalam": ((0x0D00, 0x0D7F),),
    "Sinhala": ((0x0D80, 0x0DFF),),
}
_MIN_LETTERS = 20   # a shorter document is kept
_KEEP_AT = 0.50     # this share of the pack's script or more: keep
_DROP_BELOW = 0.30  # under this share, and another script is the largest: drop


@functools.lru_cache(maxsize=None)
def _script_of(ch):
    """The script of a letter or combining sign, or None for anything that is not counted."""
    cat = unicodedata.category(ch)
    if cat[0] not in "LM":  # digits, punctuation, danda, spaces, ZWJ and ZWNJ (Cf) are not counted
        return None
    cp = ord(ch)
    for name, ranges in _SCRIPT_RANGES.items():
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return name
    if cat[0] == "L":
        return "Latin" if (cp < 0x250 or 0x1E00 <= cp <= 0x1EFF) else "Other"
    return None  # a combining mark of another script


def _script_counts(text):
    """How many letters of each script the document has (counted on the NFC form; the text is not changed)."""
    nfc = unicodedata.normalize("NFC", text)
    return Counter(s for s in map(_script_of, nfc) if s)


def _expected_script():
    """The pack's script from D1_SCRIPT, or None when it is not set."""
    name = os.environ.get("D1_SCRIPT", "").strip()
    if not name:
        return None
    key = {"oriya": "Odia"}.get(name.lower(), name.capitalize())
    if key not in _SCRIPT_RANGES:
        raise ValueError("D1_SCRIPT=%r is not one of %s" % (name, ", ".join(_SCRIPT_RANGES)))
    return key


def _d1_decision(text, expected=None):
    """('keep' | 'flag' | 'drop', share of the expected script, the script with the most letters)."""
    counts = _script_counts(text)
    total = sum(counts.values())
    if total < _MIN_LETTERS:
        return "keep", None, None
    dominant = max(counts, key=counts.get)
    if expected is None:  # no pack script: the document must be mostly in some Indic script
        share = sum(v for k, v in counts.items() if k in _SCRIPT_RANGES) / total
        other_dominates = dominant not in _SCRIPT_RANGES
    else:
        share = counts.get(expected, 0) / total
        other_dominates = dominant != expected
    if share >= _KEEP_AT:
        return "keep", share, dominant
    if share < _DROP_BELOW and other_dominates:
        return "drop", share, dominant
    return "flag", share, dominant


def medicine_d1(text):
    """True (drop) when another script dominates the document; False otherwise. The text is never changed."""
    return _d1_decision(text, _expected_script())[0] == "drop"
```

3. **Action:** drop. Runs on every pack, with `D1_SCRIPT` set to the pack's script.
4. **Harm test:** one file for each pack, `harm_<pack>.md`, made by `run_harm.py` with `tools/harm_test_indic.py`, on the pack's own gold set. A pack with no gold set says "gold set empty, not testable".
5. **Side effects:**
   - ZWJ and ZWNJ: the rule returns only `True` or `False`, never new text, so the counts before and after are the same by construction. `test_filters.py` checks it on made-up Malayalam, Kannada, Telugu and Hindi text with joiners, and through the harm tool's own joiner audit.
   - NFC: used only to count. NFKC is never called.
   - Hindi, Marathi and Sanskrit share Devanagari, so script share cannot catch Hindi in a Marathi pack. A Hindi page in a Marathi pack is kept.
   - Code-mixed text: a page with a few English words has a share far above 0.30 and is kept. A page that is mostly English is dropped; that is also a wrong label here.
6. **Spec v1:** not in spec v1 yet; a candidate for Data B's next rules sheet.

## Medicine 2: invisible junk characters

1. **Disease:** A1 Invisible junk characters: zero-width space, byte-order mark, soft hyphen and the bidi embedding, override and isolate marks. Readers marked it in 40 rows of 4 packs; `ind-mr-fw2` and `ind-te-sangraha-v` already have a rule (DB-A1-001, DB-A1-002), the other packs have none.
2. **Medicine:** the author's code: adinathauti, PR #114 at `22714bb` (`ind-mr-fw2`), the same as `DB-A1-001` in `indic_rules/medicine_indic.md`. Two authors wrote an A1 rule; PR #109's (SreekanthZipsy, `DB-A1-002`) removes the same 12 characters (the outputs are the same on 20,000 random strings, and a test compares the two). Data B uses #114's because it is one regex call and about 20 times faster (0.04 ms against 0.9 ms for a 5,000-character document). It is not tied to a script, so it runs on every pack. ZWJ (U+200D) and ZWNJ (U+200C) are not in the set, so they stay. U+200B (zero-width space) is the character next to them that goes. Two marked changes by Data B: the 12 characters are written as `\u` escapes (the author typed the invisible characters themselves; the set is the same, and a test checks it against the author's text in `indic_rules/medicine_indic.md`), and `medicine_a1` is added, because the harm tool looks for that name.

```python
_A1_RE = re.compile(
    r'[\u200b\ufeff\u00ad'      # ZWSP, BOM, soft hyphen  (Data B: written as escapes)
    r'\u202a-\u202e'            # bidi embed/override
    r'\u2066-\u2069]'           # bidi isolate
)

def fix_a1(text: str) -> str:
    return _A1_RE.sub('', text)

def medicine_a1(text: str) -> str:  # added by Data B: the name harm_test_indic.py looks for
    return fix_a1(text)
```

3. **Action:** fix. Runs on every pack.
4. **Harm test:** one file for each pack, `harm_<pack>.md`, made by `run_harm.py`; each pack on its own gold set.
5. **Side effects:** a soft hyphen (U+00AD) inside a word is removed; that is what the author intended. ZWJ and ZWNJ: the counts before and after are the same by construction (the set holds neither), and `test_filters.py` checks it on made-up text of all nine scripts, with each junk character before, after and inside a word that holds a ZWJ or a ZWNJ. NFC is not called, and the text is not re-normalised.
   - Scope: exactly the characters `DISEASES.md` lists for A1 (12 code points; PR #114's rule removes the same 12, which a test checks). Other characters that look invisible (U+200E and U+200F direction marks, U+2060 word joiner, U+061C, U+034F, U+2028, U+00A0) are not A1 in v1 and stay; a test pins that.
   - Order: A1 runs before G1, so a zero-width space between a consonant and its vowel sign no longer hides the cut from G1 (tested).
   - Real packs: none of the 10 packs on hand holds any of the 12 characters, so the harm result there is 0 changed and shows nothing about A1. The packs that do (`ind-mr-fw2`, `ind-te-sangraha-v`) are not on hand; the authors' results on them are in spec v1.
6. **Spec v1:** not in spec v1 yet; a candidate for Data B's next rules sheet.

## Medicine 3: broken vowel sign

1. **Disease:** G1 Cut at the vowel sign: a vowel sign after a space, a break or a virama, or a sign typed before its letter, in the packs that had no G1 rule of their own in spec v1: `ind-ta-fw2` (35 rows), `ind-ml-fw2` (19), `ind-kn-sangraha-s` (8), `ind-or-fw2` (8), `ind-mr-sangraha-v` (7).
2. **Medicine:** the owners' code for each script, with the same-language borrowed scope that #240 accepts for a pack that has no rule of its own (Pritish52718, #240, 3 Nov). Each owner's function is renamed (they were all called `medicine_g1`, `g1fix` and the like) and nothing else in it is changed, apart from the lines marked `Data B`. `medicine_g1(text)` finds the script of the document and runs that owner's function:

| Script | Packs it is for | Owner's code | Marked change |
|---|---|---|---|
| Kannada | `ind-kn-sangraha-s` | keshavamurali #47 (`DB-G1-005`) | visarga out of the set it joins (TSAI, #240 follow-up) |
| Devanagari | `ind-mr-sangraha-v` | thinktinkergreen #50 (`DB-G1-006`) | visarga-to-colon step removed (TSAI, #240 review) |
| Malayalam | `ind-ml-fw2` | umeshnmenon #116 | visarga out of the set it joins (TSAI, #240 re-review); `drop_stacked_sign` left out |
| Tamil | `ind-ta-fw2` | Dharshanthaigu #169 | none |
| Odia | `ind-or-fw2` | Pritish52718 #86 | none |
| Bengali, Gujarati, Telugu, Gurmukhi | their packs have G1 rules in spec v1 (`DB-G1-001`, `-002`, `-003`, `-010`, `-014`, `-015`, `-017`) | none: **Data B's own fallback** (`_g1_generic`) | remove a space or line break between a consonant and a following vowel sign or virama; nothing else. Not an owner's code; it is the Devanagari rule (#50) on each script's code points |

```python
import re
import unicodedata

# ---- Kannada. Author: keshavamurali, PR #47 at 2e62abd (ind-kn-fw2); DB-G1-005 in indic_rules/medicine_indic.md
_KN = re.compile(r'([\u0C80-\u0CFF]) ([\u0CBE-\u0CCD\u0CD5\u0CD6\u0C82])')  # Data B took the visarga (U+0C83) out of this set (TSAI, #240 follow-up: a visarga, with or without a space before it, stays as written)

def _g1_kannada(text):  # medicine_g1 of #47, renamed by Data B
    out = _KN.sub(r'\1\2', text)
    return unicodedata.normalize('NFC', out) if out != text else text


# ---- Devanagari (Marathi, Hindi, Sanskrit). Author: thinktinkergreen, PR #50 at 0d85486 (ind-mr-fw2); DB-G1-006
def _g1_devanagari(text):  # medicine_g1 of #50, renamed by Data B
    text = re.sub(r'([\u0915-\u0939\u0958-\u095F])\s+([\u093E-\u094D\u0962\u0963])', r'\1\2', text)
    return text  # Data B removed the visarga-to-colon step here (TSAI, #240 review, 5 Nov: a visarga used as a colon is clean)


# ---- Malayalam. Author: umeshnmenon, PR #116 (ind-ml-fw2), Medicine 5. Data B left out the author's second function
# drop_stacked_sign() and the constant only it used: it drops a whole document, and a drop is not this filter's job.
_ML_SPACE = re.compile(r"(?<=\S)[ \t\n]+(?=[\u0D3E-\u0D4D\u0D57\u0D02])")  # Data B took the visarga (U+0D03) out of this set (TSAI, #240 re-review, 5 Nov: a visarga used as a colon is clean, also with a space before it)
_ML_PAIRS = {"\u0D12\u0D3E": "\u0D13", "\u0D07\u0D57": "\u0D08", "\u0D09\u0D57": "\u0D0A"}
_ML_DOUBLE = re.compile("\u0D4D{2,}")


def _g1_malayalam(text):  # medicine_g1 of #116, renamed by Data B
    """G1: remove a space or break before a vowel sign; write the old two-letter long vowels as one letter;
    write a doubled virama as one."""
    text = _ML_SPACE.sub("", text)
    text = _ML_DOUBLE.sub("\u0D4D", text)
    for old, new in _ML_PAIRS.items():
        text = text.replace(old, new)
    return text


# ---- Tamil. Author: Dharshanthaigu, PR #169 (ind-ta-fw2), Medicine 2
def _g1_tamil(t):  # g1fix of #169, renamed by Data B
    t=t.replace('ா்','ர்').replace('ோ்','ேர்').replace('ொ்','ெர்')
    for a,b in [('ாி','ரி'),('ாீ','ரீ'),('ாு','ரு'),('ாூ','ரூ'),('ுா','ூ')]: t=t.replace(a,b)
    t=re.sub('ௌ(?=[\u0bbf\u0bc0])','ெள',t)
    t=re.sub('([\u0bbf\u0bc0\u0bc1\u0bc2\u0bc8])்',r'\1',t)
    t=re.sub(r'(?<![\u0b95-\u0bb9])([\u0bc6\u0bc7\u0bc8])([\u0b95-\u0bb9])',r'\2\1',t)
    return unicodedata.normalize('NFC',t)


# ---- Odia. Author: Pritish52718, PR #86 (ind-or-fw2), Medicine 9
_E_FIRST = re.compile("(?<![\u0b00-\u0b7f])\u0b47([\u0b15-\u0b39\u0b5f\u0b71]\u0b3c?)([\u0b3e\u0b57]?)")

def _after(m):          # sign E typed before its letter (old-font order): put it after the letter
    sign = {"\u0b3e": "\u0b4b", "\u0b57": "\u0b4c"}.get(m.group(2), "\u0b47")   # E+AA = O, E+AU length mark = AU
    return m.group(1) + sign

def _g1_odia(text):  # medicine_g1 of #86, renamed by Data B
    t = re.sub("(?<=\\s)\u0b3e(?=\\s|$)", "\u0964", text)    # a lone sign AA used as a danda -> danda
    return _E_FIRST.sub(_after, t)                           # େସ -> ସେ, େବାଲି -> ବୋଲି, େଶୗଚ -> ଶୌଚ


# ---- added by Data B (not an owner's code): the fallback for the scripts that have no owner's code in this file.
# It is the same idea as the Devanagari rule above: a consonant, a space, then a vowel sign or a virama: remove the
# space. Only a space, a tab or a line break is removed; the visarga and the anusvara are not in the sign set.
_GENERIC = {  # script: (consonants, vowel signs and virama), as character classes of code points
    "Bengali": ("\u0995-\u09B9\u09DC-\u09DF", "\u09BE-\u09CD\u09D7\u09E2\u09E3"),
    "Gurmukhi": ("\u0A15-\u0A39\u0A59-\u0A5E", "\u0A3E-\u0A4D"),
    "Gujarati": ("\u0A95-\u0AB9", "\u0ABE-\u0ACD\u0AE2\u0AE3"),
    "Telugu": ("\u0C15-\u0C39\u0C58-\u0C5A", "\u0C3E-\u0C4D\u0C55\u0C56\u0C62\u0C63"),
}


def _g1_generic(consonants, signs):
    cut = re.compile("([" + consonants + "])[ \\t\\n]+([" + signs + "])")
    return lambda text: cut.sub(r"\1\2", text)


# ---- added by Data B: pick the owner's code by the script of the document (a text-only function is not told the pack)
_SCRIPTS = {  # Unicode blocks; the code for a script is the owner's function, or Data B's fallback above
    "Devanagari": ((0x0900, 0x097F), _g1_devanagari), "Bengali": ((0x0980, 0x09FF), _g1_generic(*_GENERIC["Bengali"])),
    "Gurmukhi": ((0x0A00, 0x0A7F), _g1_generic(*_GENERIC["Gurmukhi"])),
    "Gujarati": ((0x0A80, 0x0AFF), _g1_generic(*_GENERIC["Gujarati"])), "Odia": ((0x0B00, 0x0B7F), _g1_odia),
    "Tamil": ((0x0B80, 0x0BFF), _g1_tamil), "Telugu": ((0x0C00, 0x0C7F), _g1_generic(*_GENERIC["Telugu"])),
    "Kannada": ((0x0C80, 0x0CFF), _g1_kannada), "Malayalam": ((0x0D00, 0x0D7F), _g1_malayalam),
}


def _g1_script(text):
    """The Indic script with the most letters and signs in the text, or None when there is none."""
    counts = dict.fromkeys(_SCRIPTS, 0)
    for ch in text:
        if unicodedata.category(ch)[0] in "LM":
            cp = ord(ch)
            for name, ((lo, hi), _) in _SCRIPTS.items():
                if lo <= cp <= hi:
                    counts[name] += 1
                    break
    best = max(counts, key=counts.get)
    return best if counts[best] else None


def medicine_g1(text):
    """G1: the fix for the script of the document: the owner's function, or Data B's fallback; no Indic script: as it is."""
    entry = _SCRIPTS.get(_g1_script(text))
    return entry[1](text) if entry else text
```

3. **Action:** fix. A document with no Indic letters is kept as it is.
4. **Harm test:** one file for each pack, `harm_<pack>.md`, made by `run_harm.py`. `ind-ml-fw2`, `ind-or-fw2` and `ind-ta-fw2` have no gold set yet: "gold set empty, not testable".
5. **Side effects:**
   - A visarga with or without a space before it stays as written (TSAI, #240); `test_filters.py` checks it for Kannada, Malayalam and Devanagari.
   - ZWJ and ZWNJ: no owner's function touches either; the counts before and after are checked in `test_filters.py` and in `harm_<pack>.md`. Malayalam: the rule changes no chillu (atomic chillu U+0D7A to U+0D7F, or a consonant + virama + ZWJ), as Team 3's normalizer (#134) expects. Odia and others: the nukta (U+0B3C) count is the same after the fix.
   - NFC: the Kannada and Tamil code call `unicodedata.normalize('NFC', ...)` as the authors wrote it; NFKC is never called.
   - Hindi and Sanskrit documents get the Devanagari rule too. Its author harm-tested it on `ind-mr-fw2` only (0 of 142 changed). Here it was run on one Hindi pack: `ind-hi-sangraha-s`, 0 of 24 gold documents changed (`harm_ind-hi-sangraha-s.md`). The other Hindi packs and the Sanskrit pack are in their `harm_<pack>.md` once the pack files are available.
   - A mixed-script document gets the owner's fix of its largest Indic script only.
6. **Spec v1:** not in spec v1 yet; a candidate for Data B's next rules sheet.
