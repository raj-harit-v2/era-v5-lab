"""Language-neutral signals for H3, the same content in another language: sentences, numbers, Latin-script tokens, a
language-neutral URL key and the length ratio. No model; used by h3.py.

Each signal comes in two forms. The batch functions (sentences_batch, head_texts, number_tokens, latin_token_lists,
pair_overlap, url_keys) take a whole pyarrow string array and use pyarrow compute and numpy, with no Python loop over
documents, sentences or tokens; h3.py uses only these. The per-document functions (split_sentences, numbers,
latin_tokens, multiset_jaccard, latin_share, url_key) are the plain reference that test_h3_signals.py checks the batch
functions against.

None of these decides H3 on its own. The sentences feed the encoder. The URL key finds sites that publish one page in
several languages (hi.example.org, /hi/, ?lang=hi). Numbers, Latin-script tokens and the length ratio are reported for
each candidate pair, for the hand review.

    python3 -B -m pytest dedup/tests/test_h3_signals.py
"""
import re
import unicodedata
from collections import Counter

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

# A sentence ends at . ! ? or the Devanagari danda or double danda followed by whitespace, or at a line break.
_SENTENCE_END = re.compile(r"(?<=[.!?।॥])\s+|\s*\n\s*")
# \d matches every Unicode decimal digit (Devanagari, Bengali, Tamil, ...), so Indic and ASCII numbers are both found.
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
# Names, acronyms and URLs that stay in Latin letters inside Indic text; three letters or more.
_LATIN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]{2,}")
_LOCALE = re.compile(r"([a-z]{2})(?:[-_][a-z]{2})?")
# scheme://authority path ?query #fragment; the fragment is dropped.
_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://([^/?#]*)([^?#]*)(?:\?([^#]*))?")

LANG_CODES = frozenset("en hi sa mr bn gu kn ml or ta te pa ur as ne".split())
LANG_NAMES = {"english": "en", "hindi": "hi", "sanskrit": "sa", "marathi": "mr", "bengali": "bn", "bangla": "bn",
              "gujarati": "gu", "kannada": "kn", "malayalam": "ml", "odia": "or", "oriya": "or", "tamil": "ta",
              "telugu": "te", "punjabi": "pa", "urdu": "ur", "assamese": "as", "nepali": "ne"}
LANG_PARAMS = frozenset({"lang", "language", "hl", "lng", "locale"})
_HOST_PREFIXES = ("www", "m")

# The same patterns for pyarrow's RE2, which has no lookbehind. _WS is exactly the whitespace of Python's str.split()
# and of re's \s, so the batch functions split and collapse where the reference functions do.
_WS = (r"[\x{09}-\x{0d}\x{1c}-\x{20}\x{85}\x{a0}\x{1680}\x{2000}-\x{200a}\x{2028}\x{2029}\x{202f}\x{205f}"
       r"\x{3000}]")
_END_MARKS = "[.!?।॥]"
_NUMBER_RE2 = r"\p{Nd}+(?:[.,]\p{Nd}+)*"
_MARK = "\x1f"   # wraps each number before the split; a text that has it still splits correctly (no digits in it)
_URL_RE2 = r"^[A-Za-z][A-Za-z0-9+.\-]*://(?P<auth>[^/?#]*)(?P<path>[^?#]*)(?:\?(?P<query>[^#]*))?"
_NULL = pa.scalar(None, pa.string())


# --- per-document reference ------------------------------------------------------------------------------------------

def split_sentences(text, min_chars=20, max_sentences=None):
    """The document's sentences, whitespace collapsed, each at least min_chars long (shorter ones, such as menu items
    and headings, are dropped); at most max_sentences, from the start."""
    out = []
    for s in _SENTENCE_END.split(text or ""):
        s = " ".join(s.split())
        if len(s) >= min_chars:
            out.append(s)
            if max_sentences and len(out) >= max_sentences:
                break
    return out


def numbers(text):
    """The multiset of numbers, with every script's digits as ASCII and the thousands commas removed, so that
    "२०२४" and "2024" match, and "1,00,000" and "100000" too."""
    found = Counter()
    for m in _NUMBER.finditer(text or ""):
        s = "".join(str(unicodedata.decimal(ch)) if ch.isdecimal() else ch for ch in m.group()).replace(",", "")
        found[s if "." in s else str(int(s))] += 1
    return found


def multiset_jaccard(a, b):
    """Shared / all counts of two Counters; None when both are empty (no evidence either way)."""
    if not a and not b:
        return None
    return sum((a & b).values()) / sum((a | b).values())


def latin_tokens(text):
    """The set of Latin-script words of three letters or more, lowercased."""
    return {t.lower() for t in _LATIN.findall(text or "")}


def latin_share(a, b):
    """The share of the smaller token set found in the other; None when either is empty. For an Indic and an English
    document this is the share of the Indic document's Latin words (names, acronyms) that the English one has."""
    if not a or not b:
        return None
    return len(a & b) / min(len(a), len(b))


def _language(token):
    t = token.lower()
    if t in LANG_NAMES:
        return LANG_NAMES[t]
    m = _LOCALE.fullmatch(t)
    return m.group(1) if m and m.group(1) in LANG_CODES else None


def url_key(url):
    """(key, language): the URL with one language marker removed, and the language that marker named.

    The marker is a language subdomain (hi.wikipedia.org), a path segment (/hi/, /en-us/, /hindi/) or a query field
    (?lang=hi). www. and m. are dropped, the host and path are lowercased and the other query fields are kept as written
    and sorted. So https://example.org/hi/news/7 and https://example.org/news/7 share a key. The key is None for a
    site's home page (no path or query left), whose language versions are not one document, and for anything that is
    not scheme://host... (an IPv6 host included)."""
    m = _URL.match(url.strip()) if url else None
    if not m:
        return None, None
    host = m.group(1).rpartition("@")[2].partition(":")[0].lower()
    if not host or host.startswith("["):
        return None, None
    labels = host.split(".")
    while len(labels) > 2 and labels[0] in _HOST_PREFIXES:
        labels.pop(0)
    lang = None
    if len(labels) > 2 and _language(labels[0]):
        lang = _language(labels.pop(0))
        while len(labels) > 2 and labels[0] in _HOST_PREFIXES:
            labels.pop(0)
    segments = [s for s in m.group(2).split("/") if s]
    if lang is None:
        for k, segment in enumerate(segments):
            if _language(segment):
                lang = _language(segment)
                del segments[k]
                break
    query = []
    for field in (m.group(3) or "").split("&"):
        if not field:
            continue
        if field.partition("=")[0].lower() in LANG_PARAMS:
            lang = lang or _language(field.partition("=")[2])
            continue
        query.append(field)
    if not segments and not query:
        return None, lang
    key = ".".join(labels) + "/" + "/".join(segments).lower()
    return (key + "?" + "&".join(sorted(query)) if query else key), lang


def length_ratio(a, b):
    """Longer / shorter character count; infinite when either is 0."""
    lo, hi = min(a, b), max(a, b)
    return hi / lo if lo > 0 else float("inf")


# --- batch functions: whole arrays, no Python loop over documents ----------------------------------------------------

def _array(x):
    return x.combine_chunks() if isinstance(x, pa.ChunkedArray) else x


def _bools(x):
    return np.asarray(x.to_numpy(zero_copy_only=False), dtype=bool)


def _flatten(lists):
    """(values, the index of the list each value came from) of a list array."""
    return pc.list_flatten(lists), np.asarray(pc.list_parent_indices(lists), dtype=np.int64)


def _lists(values, counts):
    """A list array of len(counts) lists: the values in order, counts[i] of them in list i."""
    offsets = np.concatenate(([0], np.cumsum(counts))).astype(np.int32)
    return pa.ListArray.from_arrays(pa.array(offsets), values)


def rank_in_group(group):
    """Each element's position among the elements of its group; group is sorted."""
    n = len(group)
    if n == 0:
        return np.zeros(0, np.int64)
    first = np.flatnonzero(np.concatenate(([True], group[1:] != group[:-1])))
    return np.arange(n) - np.repeat(first, np.diff(np.concatenate((first, [n]))))


def sentences_batch(texts, min_chars=20, max_sentences=None):
    """split_sentences for every text of a string array at once: (sentences, the text index of each), in text order."""
    t = pc.fill_null(_array(texts), "")
    t = pc.replace_substring_regex(t, pattern="(" + _END_MARKS + ")" + _WS + "+", replacement="\\1\n")
    s, parent = _flatten(pc.split_pattern_regex(t, pattern=_WS + "*\n" + _WS + "*"))
    s = pc.utf8_trim(pc.replace_substring_regex(s, pattern=_WS + "+", replacement=" "), characters=" ")
    keep = _bools(pc.greater_equal(pc.utf8_length(s), min_chars))
    s, parent = s.filter(pa.array(keep)), parent[keep]
    if max_sentences:
        keep = rank_in_group(parent) < max_sentences
        s, parent = s.filter(pa.array(keep)), parent[keep]
    return s, parent


def head_texts(sentences, parent, n, k):
    """The first k sentences of each of n texts, joined by spaces ("" for a text with none)."""
    keep = rank_in_group(parent) < k
    return pc.binary_join(_lists(sentences.filter(pa.array(keep)), np.bincount(parent[keep], minlength=n)), " ")


def number_tokens(texts):
    """numbers() for every text at once: (the numbers, normalised, the text index of each), duplicates kept."""
    t = pc.replace_substring_regex(pc.fill_null(_array(texts), ""), pattern="(" + _NUMBER_RE2 + ")",
                                   replacement=_MARK + "\\1" + _MARK)
    tok, parent = _flatten(pc.split_pattern(t, pattern=_MARK))
    keep = _bools(pc.match_substring_regex(tok, pattern="^" + _NUMBER_RE2 + "$"))
    tok, parent = pc.replace_substring(tok.filter(pa.array(keep)), pattern=",", replacement=""), parent[keep]
    other = pc.match_substring_regex(tok, pattern="[^0-9.]")
    if pc.any(other).as_py():
        # The distinct non-ASCII digits present, each replaced in one vectorised call: a loop over a few characters
        # of the digit table (at most the 680 Unicode decimal digits), not over the data.
        joined = pc.binary_join(_lists(tok.filter(other), [pc.sum(other).as_py()]), "")[0].as_py()
        chars = np.unique(np.frombuffer(joined.encode("utf-32-le"), dtype=np.uint32))
        for c in chars[chars > 127].tolist():
            tok = pc.replace_substring(tok, pattern=chr(c), replacement=str(unicodedata.decimal(chr(c))))
    integer = pc.replace_substring_regex(tok, pattern="^0+([0-9])", replacement="\\1")
    return pc.if_else(pc.match_substring(tok, pattern="."), tok, integer), parent


def latin_token_lists(texts):
    """latin_tokens() for every text at once: (the tokens, lowercased, the text index of each), duplicates kept.
    A token is a whole run of ASCII letters and digits that starts with a letter, which is what _LATIN matches."""
    tok, parent = _flatten(pc.split_pattern_regex(pc.fill_null(_array(texts), ""), pattern="[^A-Za-z0-9]+"))
    keep = _bools(pc.match_substring_regex(tok, pattern="^[A-Za-z][A-Za-z0-9]{2,}$"))
    return pc.ascii_lower(tok.filter(pa.array(keep))), parent[keep]


def pair_overlap(tokens, parent, n, A, B, distinct):
    """For each pair (A[p], B[p]) of n documents with these tokens: (shared, size of A[p], size of B[p]), over token
    multisets, or over sets when distinct. multiset_jaccard is shared / (size_a + size_b - shared) and latin_share is
    shared / min(size_a, size_b)."""
    A, B = np.asarray(A, np.int64), np.asarray(B, np.int64)
    enc = pc.dictionary_encode(_array(tokens))
    T = max(len(enc.dictionary), 1)
    u, cnt = np.unique(parent * T + np.asarray(enc.indices, dtype=np.int64), return_counts=True)
    doc, tok = u // T, u % T
    if distinct:
        cnt = np.ones_like(cnt)
    size = np.bincount(doc, weights=cnt, minlength=n)
    indptr = np.searchsorted(doc, np.arange(n + 1))

    def entries(D):   # (pair * T + token, count) of every token of each pair's document D[p]
        lo, lens = indptr[D], indptr[D + 1] - indptr[D]
        idx = np.arange(lens.sum()) - np.repeat(np.cumsum(lens) - lens - lo, lens)
        return np.repeat(np.arange(len(D)), lens) * T + tok[idx], cnt[idx]

    (ka, ca), (kb, cb) = entries(A), entries(B)
    k, c = np.concatenate((ka, kb)), np.concatenate((ca, cb))
    order = np.argsort(k, kind="stable")
    k, c = k[order], c[order]
    both = k[1:] == k[:-1]                     # a token in both documents of a pair: once per side
    shared = np.bincount(k[1:][both] // T, weights=np.minimum(c[1:], c[:-1])[both], minlength=len(A))
    return shared, size[A], size[B]


def _codes(tokens):
    """_language() for every token at once: the language code, or null."""
    t = pc.utf8_lower(tokens)
    by_name = pc.take(pa.array(list(LANG_NAMES.values())), pc.index_in(t, value_set=pa.array(list(LANG_NAMES))))
    code = pc.utf8_slice_codeunits(t, 0, 2)
    locale = pc.and_(pc.match_substring_regex(t, pattern="^[a-z]{2}(?:[-_][a-z]{2})?$"),
                     pc.is_in(code, value_set=pa.array(sorted(LANG_CODES))))
    return pc.coalesce(by_name, pc.if_else(locale, code, _NULL))


def url_keys(urls):
    """url_key(...)[0] for every URL of a string array at once; null where there is no key."""
    u = pc.replace_substring_regex(pc.fill_null(_array(urls), ""), pattern="^" + _WS + "+|" + _WS + "+$",
                                   replacement="")
    n = len(u)
    m = pc.extract_regex(u, pattern=_URL_RE2)
    ok = _bools(pc.is_valid(m))   # the fields of a non-URL row are not used: ok masks them at the end
    host = pc.replace_substring_regex(pc.fill_null(m.field("auth"), ""), pattern="(?s)^.*@", replacement="")
    host = pc.utf8_lower(pc.replace_substring_regex(host, pattern="(?s):.*$", replacement=""))
    ok &= (pc.utf8_length(host).to_numpy() > 0) & ~_bools(pc.starts_with(host, pattern="["))
    big = np.iinfo(np.int64).max

    # Host: www./m. labels dropped while more than two labels are left; then a language label, and www./m. again.
    labels, lp = _flatten(pc.split_pattern(host, pattern="."))
    nlab, rank = np.bincount(lp, minlength=n), rank_in_group(lp)
    prefix = _bools(pc.is_in(labels, value_set=pa.array(list(_HOST_PREFIXES))))

    def run_from(start):   # the length of each host's run of www/m labels from rank start
        first = np.full(n, big)
        stop = ~prefix & (rank >= start[lp])
        np.minimum.at(first, lp[stop], rank[stop])
        return np.minimum(first, nlab) - start

    r1 = np.clip(np.minimum(run_from(np.zeros(n, np.int64)), nlab - 2), 0, None)
    is_lang = _bools(pc.is_valid(_codes(labels))) & (rank == r1[lp]) & ((nlab - r1)[lp] > 2)
    host_lang = np.zeros(n, bool)
    host_lang[lp[is_lang]] = True
    r2 = np.where(host_lang, np.clip(np.minimum(run_from(r1 + 1), nlab - r1 - 3), 0, None), 0)
    cut = r1 + host_lang * (1 + r2)
    keep = rank >= cut[lp]
    host = pc.binary_join(_lists(labels.filter(pa.array(keep)), np.bincount(lp[keep], minlength=n)), ".")

    # Path: the empty segments dropped, and the first language segment when the host had none.
    seg, sp = _flatten(pc.split_pattern(pc.fill_null(m.field("path"), ""), pattern="/"))
    nonempty = pc.utf8_length(seg).to_numpy() > 0
    seg, sp = seg.filter(pa.array(nonempty)), sp[nonempty]
    pos = np.arange(len(sp))
    lang_seg = _bools(pc.is_valid(_codes(seg))) & ~host_lang[sp]
    first = np.full(n, big)
    np.minimum.at(first, sp[lang_seg], pos[lang_seg])
    keep = pos != first[sp]
    seg, sp = seg.filter(pa.array(keep)), sp[keep]
    nseg = np.bincount(sp, minlength=n)
    path = pc.utf8_lower(pc.binary_join(_lists(seg, nseg), "/"))

    # Query: the empty and language fields dropped, the rest sorted.
    f, fp = _flatten(pc.split_pattern(pc.fill_null(m.field("query"), ""), pattern="&"))
    name = pc.utf8_lower(pc.replace_substring_regex(f, pattern="(?s)=.*$", replacement=""))
    keep = (pc.utf8_length(f).to_numpy() > 0) & ~_bools(pc.is_in(name, value_set=pa.array(sorted(LANG_PARAMS))))
    f, fp = f.filter(pa.array(keep)), fp[keep]
    order = pc.sort_indices(pa.table({"p": fp, "f": f}), sort_keys=[("p", "ascending"), ("f", "ascending")])
    nq = np.bincount(fp, minlength=n)
    query = pc.binary_join(_lists(f.take(order), nq), "&")

    key = pc.binary_join_element_wise(host, path, "/")
    key = pc.if_else(pa.array(nq > 0), pc.binary_join_element_wise(key, query, "?"), key)
    return pc.if_else(pa.array(ok & ((nseg + nq) > 0)), key, _NULL)
