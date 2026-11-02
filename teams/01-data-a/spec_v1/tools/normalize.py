r"""Spec v1 normalize: a standard copy of a text, for comparing and matching. It never changes or drops a document:
your code compares the copies, and each document keeps its own text. (The cleaning itself is clean.py.)

HOW TO RUN IT
=============
Run every command from teams/01-data-a/, the folder that holds spec_v1/. Python 3.9 or later.

1. Install, once. Only the pack report in step 3 needs a package; the functions in step 2 need none.

       python3 -m pip install pyarrow

2. Use it from your own Python code:

       import sys
       sys.path.insert(0, "spec_v1/tools")
       from normalize import normalize, match_key, line_keys, explain

       normalize("Janet\u2019s DUCKS, lay 16-eggs!")              # ['janet', 's', 'ducks', 'lay', '16', 'eggs']
       match_key("Fish &amp; chips") == match_key("fish & CHIPS")   # True
       line_keys("Subscribe  NOW\nsubscribe now")                  # ['subscribe now', 'subscribe now']
       explain("Caf\u00e9\u200b")                                  # ['A1', 'case']: the steps that changed the key

   Compare the results, never write them back: store each document's own text, not its key.

3. See what it would do on a pack. It prints one line per step: how many documents' keys that step changes, and up to
   --show doc_ids (default 5). IDs and counts only, never document text. The pack must be a Parquet file with doc_id
   and text columns.

       python3 -I spec_v1/tools/normalize.py --pack <packs folder>/en-dclm.parquet
       python3 -I spec_v1/tools/normalize.py --pack <packs folder>/en-dclm.parquet --show 10

4. Run its unit tests (needs pytest: python3 -m pip install pytest):

       python3 -m pytest spec_v1/tests/test_normalize.py

WHAT IT GIVES
=============
  normalize(text)            a list of words, for decontamination fingerprints. Team 1 shares it with G9: same
  words_with_offsets(text)   interface as teams/09-evaluation/decontam/normalize.py, with NORMALIZE_ID and DESCRIPTION.
                             words_with_offsets also gives where each word starts in the original text.
  match_key(text)            one key for the whole text, punctuation kept: duplicates (H1, H2)
  line_keys(text)            one key per line: repeated lines, boilerplate, licence headers (C1, C2, E4)
  explain(text)              the steps of the keys that change this text, in order

HOW IT TREATS CHARACTERS
========================
Both shapes use one character policy, and it is the same for every language and pack, on purpose: a benchmark item has
no pack, and both sides of a match must get exactly the same treatment. Language-specific repairs (A3 mojibake, B2
markup, and the rest) are done by clean.py on the documents before matching.
  1. The A1 invisible characters of DISEASES.md (zero-width space U+200B, BOM U+FEFF, soft hyphen U+00AD, bidi marks
     U+202A-U+202E and U+2066-U+2069) are removed; in normalize() they do not split a word either. ZWJ U+200D and ZWNJ
     U+200C are kept: in Indic text they are part of the script (DISEASES.md A1 and G2).
  2. NFC (DISEASES.md A5). Never full NFKC (G4: over-normalised); only these compatibility characters are folded to
     their plain form: Latin ligatures U+FB00-U+FB06 ("fi"), fullwidth ASCII U+FF01-U+FF5E, vulgar fractions
     (U+00BC-U+00BE, U+2150-U+215F, U+2189) and Arabic presentation forms (U+FB50-U+FDFF, U+FE70-U+FEFF).
     Superscripts, Indic digits and all other characters are left as they are.
     The old ZWJ spellings of the Malayalam chillus (for example NNA + virama + ZWJ) and of Bengali khanda ta
     (TA + virama + ZWJ) become the atomic letters Unicode encodes for them (U+0D7A-U+0D7F, U+09CE), so the two
     spellings of the same letter match. Every other ZWJ and ZWNJ stays.
  3. casefold(), then NFC again.
normalize() then keeps only words: runs of Unicode letters (L*), marks (M*) and numbers (N*), plus ZWJ and ZWNJ;
everything else separates words, and a fraction such as "1/2" splits. Changing any of its steps changes NORMALIZE_ID:
G9's decontam_check.py refuses a fingerprint set built with another ID.
The keys keep punctuation and lines, and before the steps above they also decode HTML entities that end in ";"
(B1: "&amp;", "&#2361;", but not "&reg" inside a URL) and drop control characters (A2: U+0000-001F but tab and
newline, U+007F-009F; "\r\n" becomes "\n"); after them, runs of spaces and tabs become one space.
"""
import argparse, html, re, sys, unicodedata
from collections import Counter

NORMALIZE_ID = "g1-spec-v1"
DESCRIPTION = ("words = runs of Unicode L/M/N characters plus ZWJ/ZWNJ (kept); DISEASES.md A1 invisible characters do "
               "not split and are removed; each word NFC, ZWJ chillu and khanda ta spellings to the atomic letters, "
               "Latin ligatures, fullwidth ASCII, vulgar fractions and Arabic presentation forms folded, then casefold(); "
               "everything else separates words")

# These steps intentionally apply to the G1 line/document comparison keys,
# not the G9 word-fingerprint API. They must not silently change normalize().
KEY_ONLY_STEPS = ("B1", "A2", "space")

# Each reported offset is the start of the original raw word span. A single
# compatibility character such as 1/2 (U+00BD) can produce multiple normalized
# words with the same source offset. Offsets refer to the text *passed in*,
# which may already have been changed by clean.py.
OFFSET_CONVENTION = "original_raw_word_start"

A1_CHARS = "\u200b\ufeff\u00ad\u202a-\u202e\u2066-\u2069"   # DISEASES.md A1, removed
JOINERS = "\u200c\u200d"                                    # ZWNJ, ZWJ: part of Indic script (A1, G2), kept
_FOLD = re.compile("[\ufb00-\ufb06\uff01-\uff5e\u00bc-\u00be\u2150-\u215f\u2189\ufb50-\ufdff\ufe70-\ufeff]")   # the only compatibility folds
_ATOMIC = {"\u0d23\u0d4d\u200d": "\u0d7a", "\u0d28\u0d4d\u200d": "\u0d7b", "\u0d30\u0d4d\u200d": "\u0d7c",   # Malayalam chillus
           "\u0d32\u0d4d\u200d": "\u0d7d", "\u0d33\u0d4d\u200d": "\u0d7e", "\u0d15\u0d4d\u200d": "\u0d7f",
           "\u09a4\u09cd\u200d": "\u09ce"}                                                                # Bengali khanda ta
_ATOMIC_RE = re.compile("|".join(_ATOMIC))


def _mark_ranges():
    # Python \w does not match combining marks (Unicode M*), so Indic vowel signs would split words.
    ranges, start, prev = [], None, None
    for cp in range(sys.maxunicode + 1):
        if unicodedata.category(chr(cp))[0] == "M":
            if start is None:
                start = cp
            prev = cp
        elif start is not None:
            ranges.append((start, prev))
            start = None
    if start is not None:
        ranges.append((start, prev))
    return "".join(f"\\U{a:08x}-\\U{b:08x}" for a, b in ranges)


_M = _mark_ranges()
WORD_RE = re.compile(f"(?:[^\\W_]|[{_M}{JOINERS}])+")                  # a normalized word
_RAW_WORD_RE = re.compile(f"(?:[^\\W_]|[{_M}{JOINERS}{A1_CHARS}])+")   # in the original text, A1 characters join too
_A1_RE = re.compile(f"[{A1_CHARS}]+")
_ONLY_JOINERS = re.compile(f"[{JOINERS}]+")


def _nfc_and_folds(text):
    """Step 2 of the character policy: NFC, the atomic Indic letters, the listed compatibility folds."""
    t = _ATOMIC_RE.sub(lambda m: _ATOMIC[m.group()], unicodedata.normalize("NFC", text))
    return _FOLD.sub(lambda m: unicodedata.normalize("NFKC", m.group()), t)


def _key(token):
    return unicodedata.normalize("NFC", _nfc_and_folds(_A1_RE.sub("", token)).casefold())


def words_with_offsets(text):
    """Return (normalized_word, original_raw_word_start) pairs.

    The offsets are Python character indices in the *input* text, not in
    text from an earlier cleaning stage. Several output words can share an
    offset when one source token expands (e.g. U+00BD -> '1', '2'). They are
    not end offsets or character-by-character alignment information.
    """
    out = []
    for m in _RAW_WORD_RE.finditer(text):
        for w in WORD_RE.findall(_key(m.group())):
            if not _ONLY_JOINERS.fullmatch(w):
                out.append((w, m.start()))
    return out


def normalize(text):
    """Text -> list of normalized words."""
    return [w for w, _ in words_with_offsets(text)]


# The keys: the same characters, but as text, with punctuation and lines kept.

_ENTITY = re.compile(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")   # B1: whole entities only, ending in ";"
_CONTROL = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f]")   # A2: every C0 and C1 control but tab (09) and newline (0a)
_SPACE = re.compile(r"[^\S\n]+")                          # spaces, tabs and no-break spaces, not newlines
STEPS = ("B1", "A2", "A1", "A5", "case", "space")


def steps(text):
    """Each step of the keys and the text after it, in order. The last text is the key with its lines kept."""
    t = _ENTITY.sub(lambda m: html.unescape(m.group()), text)
    yield "B1", t
    t = _CONTROL.sub("", t.replace("\r\n", "\n").replace("\r", "\n"))
    yield "A2", t
    t = _A1_RE.sub("", t)
    yield "A1", t
    t = _nfc_and_folds(t)
    yield "A5", t
    t = unicodedata.normalize("NFC", t.casefold())
    yield "case", t
    t = "\n".join(_SPACE.sub(" ", line).strip() for line in t.split("\n"))
    yield "space", t


def line_keys(text):
    """One key per line, for code that compares lines (C1, C2, E4)."""
    for _, t in steps(text):
        pass
    return t.split("\n")


def match_key(text):
    """One key for the whole text, for code that compares documents or passages (H1, H2)."""
    return " ".join(k for k in line_keys(text) if k)


def explain(text):
    """The steps of the keys that change this text, in order: which diseases its key evens out."""
    out, before = [], text
    for name, after in steps(text):
        if after != before:
            out.append(name)
        before = after
    return out


def main():
    import pyarrow.parquet as pq
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--show", type=int, default=5, help="how many doc_ids to list for each step")
    args = ap.parse_args()
    rows = pq.read_table(args.pack, columns=["doc_id", "text"]).to_pylist()
    hit, ids = Counter(), {s: [] for s in STEPS}
    for r in rows:
        for name in explain(r["text"]):
            hit[name] += 1
            if len(ids[name]) < args.show:
                ids[name].append(r["doc_id"])
    print(f"{args.pack}: {len(rows)} documents. Each line: documents whose key this step changes (the documents are not changed)")
    for name in STEPS:
        print(f"  {name:6} {hit[name]:5}  {', '.join(ids[name])}")


if __name__ == "__main__":
    sys.exit(main())
