#!/usr/bin/env python3
"""doc_detector.py - is a document romanised Indic as a whole (most of its words romanised)?

TSAI's rule for the cap (#213): a document is romanised when most of its words are romanised. A native-script
article with one romanised heading or comment stays a native document.

How a document is decided, the same way for every segment classifier:
  1. Split the text into segments: lines, and inside a line, sentences (ending in . ? ! । ॥ or |).
  2. A segment classifier says whether each segment is romanised Indic (an Indian language in Latin letters).
  3. Romanised words = the Latin-letter words in the romanised segments. All words = every whitespace-separated word
     with a letter in it, in any script, after removing URLs, emails, @handles and #hashtags.
  4. The document is romanised when romanised words / all words > MAJORITY (0.5).
The word-list classifier (wordlist_segment): a segment is romanised when it has at least SEG_DISTINCT different words
from the romanised word list in detector.py ("Ji ... Ji" is not enough), or at least SEG_IAST letters with IAST
diacritics. IndicLID can be plugged in as another segment classifier (indiclid_segments.py), so both are compared
on the same rule.

Usage
  python3 doc_detector.py "aap kaise ho? sab theek hai."      prints the decision and the counts
  from doc_detector import decide; decide(text) -> {"romanised": bool, "share": float, "romanised_words": int, ...}
"""
import re
import sys

from detector import IAST, INDIC_WORDS, NOISE, WORD

MAJORITY = 0.5
SEG_DISTINCT = 2
SEG_IAST = 2

SPLIT = re.compile(r"\n+|(?<=[.?!।॥|])\s+")


def segments(text):
    """The text cut into lines and sentences, with URLs, emails, @handles and #hashtags removed."""
    return [s.strip() for s in SPLIT.split(NOISE.sub(" ", text or "")) if s.strip()]


def words(seg):
    """Every whitespace-separated word with a letter in it, any script."""
    return [w for w in seg.split() if any(c.isalpha() for c in w)]


def latin_words(seg):
    """The words of the segment written only in Latin letters (IAST included), acronyms in capitals skipped."""
    out = []
    for w in words(seg):
        letters = [c for c in w if c.isalpha()]
        if all(c.isascii() or c in IAST for c in letters) and not (len(letters) > 1 and w.isupper()):
            out.append(w)
    return out


def wordlist_segment(seg):
    """Word-list classifier for one segment."""
    found = [m.lower() for m in WORD.findall(seg) if not (len(m) > 1 and m.isupper())]
    distinct = len({w for w in found if w in INDIC_WORDS})
    iast = sum(c in IAST for w in found if len(w) >= 2 for c in w)
    return distinct >= SEG_DISTINCT or iast >= SEG_IAST


def decide(text, classify=None, majority=MAJORITY):
    """Document decision. classify(list of segments) -> list of bools; the word list is used when it is None."""
    segs = segments(text)
    flags = classify(segs) if classify else [wordlist_segment(s) for s in segs]
    total = sum(len(words(s)) for s in segs)
    rom = sum(len(latin_words(s)) for s, f in zip(segs, flags) if f)
    share = rom / total if total else 0.0
    return {"romanised": share > majority, "contains": any(f and latin_words(s) for s, f in zip(segs, flags)),
            "share": round(share, 4), "romanised_words": rom, "words": total,
            "romanised_segments": sum(flags), "segments": len(segs)}


if __name__ == "__main__":
    print(decide(" ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()))
