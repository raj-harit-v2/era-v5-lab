# Rewrite in the harm tool's format: ind-hi-hplt, pankajkr23 (PR #83)

TSAI ruling 3 on #211 (3 Nov): the Data B rules owner may rewrite a medicine sheet that `harm_test_indic.py` cannot
read, and the author must OK the rewrite in their PR. **Author OK: pending.**

Source: `diagnosis/submissions/ind-hi-hplt/pankajkr23/medicine.md` at `579d0f8`. Each section below holds the author's code
unchanged; the description, examples and side effects stay in the author's sheet.

**Changes, all marked in the code:**
1. The sheet's shared definitions (the block before the first section) are copied, unchanged, into each section that uses them. The harm tool runs each section on its own, so those sections could not load, and that stopped all 12 rules.
2. In C1, `prepare` is renamed `_prepare`, so the section has one public function; nothing calls it. Limit: `_prepare(docs)` is a pass over the whole pack that fills `SITE_LINES` with lines repeated across a site's pages. Neither the harm tool nor Data A's `clean.py` runs it (both see one document at a time), so only the per-line patterns of `c1_strip_lines` are tested.
3. In D2, the author's run-order pipeline (`MEDICINES` and `run_all`) is kept unchanged as a text block, not run: it calls the functions of every other section, so it cannot load inside one section, and it is not a rule.

**Harm test:** run on today's gold set of this pack (`teams/02-data-b/gold/ind-hi-hplt_gold.csv`, 62 documents, main at `ea7b533`); the results are posted on the author's PR.

## Medicine 1: D4

1. **Disease:** D4. Description: see the author's sheet, section D4.

```python
MT_DROP = 0.50


def d4_drop_mt(text, meta):
    """Drop the document when HPLT's web-register classifier gives the MT (machine-translated) label >= 0.50."""
    mt = ((meta or {}).get("web-register") or {}).get("MT", 0.0)
    return None if mt >= MT_DROP else text
```

4. **Harm test:** see the results on PR #83.

## Medicine 2: C5

1. **Disease:** C5. Description: see the author's sheet, section C5.

```python
_CUT_END = re.compile(r"(?:\[…\]|\[\.\.\.\]|…|\.\.\.)\s*$")
_READ_MORE = re.compile(r"^read\s+more\W*$", re.I)
_RATING = (re.compile(r"^अधिकतम रेटिंग \d", re.M), re.compile(r"^रेटिंग की संख्या \d", re.M))


def c5_drop_list(text, meta=None):
    """Drop (1) a tag, archive or search page: 3 or more teaser lines (60+ characters, ending with an excerpt
    marker) or 'Read More' lines, making up a quarter of the lines or more; (2) a page carrying the star-rating
    widget of the spun spam template ('अधिकतम रेटिंग 5' and 'रेटिंग की संख्या N' lines)."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    teasers = sum(1 for l in lines if (len(l) >= 60 and _CUT_END.search(l)) or _READ_MORE.match(l))
    if teasers >= 3 and teasers >= 0.25 * len(lines):
        return None
    if all(p.search(text) for p in _RATING):
        return None
    return text
```

4. **Harm test:** see the results on PR #83.

## Medicine 3: B2

1. **Disease:** B2. Description: see the author's sheet, section B2.

```python
_IMG = re.compile(r'[^\s"]*"\s*src="[^"]*"(?:\s+[\w-]+="[^"]*")*\s*/>')
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s+[\w-]+(?:=\"[^\"\n]*\")?)*\s*/?>")


def b2_strip_tags(text, meta=None):
    """Remove image-tag residue (alt text + src="..." + />), whole tags, and stray '/>' fragments. The fragment
    sat where a tag split two blocks, so it becomes a line break."""
    text = _IMG.sub("\n", text)
    text = _TAG.sub(" ", text)
    return text.replace("/>", "\n")
```

4. **Harm test:** see the results on PR #83.

## Medicine 4: C1

1. **Disease:** C1. Description: see the author's sheet, section C1.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
import collections
import urllib.parse

NUKTA = "\u093c"
DEV = r"\u0900-\u097f"
CONS = r"\u0915-\u0939\u0958-\u095f"      # Devanagari consonants, incl. the precomposed nukta letters
SIGN = r"\u093e-\u094d"                   # dependent vowel signs and virama


def _key(line):
    """Matching key: strip spaces, bullets and nukta, so पढ़ें / पढें and spacing variants match alike."""
    return line.replace(NUKTA, "").strip().lstrip("•-–*· ").strip()


def _host(meta):
    url = (meta or {}).get("u") or ""
    h = re.sub(r"^www\.", "", urllib.parse.urlparse(url).netloc.lower())
    p = h.split(".")
    return ".".join(p[-3:]) if h.endswith((".co.in", ".org.in")) else ".".join(p[-2:])
# end of the shared definitions
```

```python
# Each entry: (compiled pattern on the matching key, max line length in characters)
C1_LINES = [
    # related-article links: इसे / यह / ये / इन्हें भी पढ़ें / देखें, Read also, अधिक पढ़ें, यह सभी देखें, अन्य न्यूज़
    (re.compile(r"^(?:इसे|इन्हें|इन्हे|यह|ये|यें)\s*भी\s*(?:पढें|पढे|पढिए|देखें)"), 200),
    (re.compile(r"^(?:read\s+also|also\s+read|read\s+more)\b", re.I), 200),
    (re.compile(r"^(?:अधिक\s+पढें\s*:|यह\s+सभी\s+देखें\s*:)"), 200),
    (re.compile(r"^अन्य\s+न्यूज$"), 20),
    # page furniture that stands alone on a line
    (re.compile(r"^(?:advertisement|share\s*:?|शेयर\s+करें|more\s+stories|recent\s+posts|categories|trending\s+photos|"
                r"leave\s+a\s+reply|about\s+post\s+author|responses|author|comments\s+in\s+this\s+topic\s*:?|टिप्पणियाँ|"
                r"view\s+this\s+post\s+on\s+instagram|most\s+helpful\s+for\s+students|"
                r"guest\s+post\s*&\s*advertisement\s+with\s+us)$", re.I), 40),
    (re.compile(r"^post\s+views\s*:?\s*\d*$|^\d[\d,.]*k?\s+views$", re.I), 25),
    (re.compile(r"^\d+\s+thoughts?\s+on\b", re.I), 250),
    (re.compile(r"^(?:.{0,40}\s)?important\s+links?\s*[:\-–]*$", re.I), 60),
    (re.compile(r"^source\s*[:\-–]", re.I), 60),
    (re.compile(r"^all\s+content\s+on\s+this\s+website\s+is\s+copyrighted", re.I), 200),
    # comment furniture (Blogger, WordPress) and counters
    (re.compile(r"^(?:कोई\s+टिप्पणी\s+नहीं\s*:?|एक\s+टिप्पणी\s+भेजें|no\s+comments?\s*:?|\d+\s+comments?|post\s+a\s+comment|"
                r"reply\s*delete|replydelete|delete|reply|जवाब\s*देंहटाएं|उत्तर\s*देंहटाएं|एक\s+उत्तर\s+दें|leave\s+a\s+comment|"
                r"comment\s+now|share\s+this\s+post|विशिष्ट\s+पोस्ट|tags\s*:|views\s*:\s*\d+)$", re.I), 40),
    # star-rating widget lines
    (re.compile(r"^(?:अधिकतम\s+रेटिंग\s+\d+|रेटिंग\s+की\s+संख्या\s+\d+|समीक्षा\s+\d+)$"), 40),
    # blog sign-offs
    (re.compile(r"^(?:तो\s+दोस्तों\s+कैसी\s+लगी|दोस्तों,?\s+उम्मीद\s+है\s+कि\s+यह\s+पोस्ट\s+आपको\s+अच्छी\s+लगी|"
                r"अंत\s+तक\s+पढने\s+के\s+लिए\s+धन्यवाद|thanks\s+for\s+visiting\s+our\s+site)", re.I), 400),
    # image credits, photo labels, recipe credits and pointers to media that the text does not contain
    (re.compile(r"^(?:image\s+courtesy|image\s+credit|photo\s+credit|छवि\s+क्रेडिट|credit\s*ai$)", re.I), 80),
    (re.compile(r"^(?:यहां\s+देखें\s+वीडियो|देखिए\s+वीडियो)\W*$"), 40),
    (re.compile(r"^(?:पकाने\s+की\s+विधि|रेसिपी|नुस्खा)\s*:\s*\S+$"), 60),
    (re.compile(r"^reviews\s+for\s*:", re.I), 60),
    (re.compile(r"^साइन\s+अप\s+करने\s+के\s+लिए\s+धन्यवाद"), 60),
    # ad placeholders, disclaimers and syndication notes, English site footers
    (re.compile(r"^-?\s*विज्ञापन\s*\((?:article|sidebar)[^)]*\)\s*-?$", re.I), 60),
    (re.compile(r"^\(?\s*(?:डिस्क्लेमर|disclaimer|अस्वीकरण)\s*[:\-–]", re.I), 600),
    (re.compile(r"^\(?यह\s+सिंडिकेटेड\s+न्यूज\s+फीड\s+से"), 300),
    (re.compile(r"^\(?for\s+more\s+news\s+apart\s+from\b", re.I), 300),
    (re.compile(r"^(?:the\s+views\s+expressed\s+above\s+belong\s+to\s+the\s+author|orf\s+research\s+and\s+analyses\s+now\s+available)",
                re.I), 300),
]
# follow / join promos: a platform name + a join or follow verb + promo wording
_PLATFORM = re.compile(r"whatsapp|व्हाट्सएप|वॉट्सएप|फेसबुक|facebook|ट्विटर|twitter|instagram|इंस्टाग्राम|telegram|टेलीग्राम", re.I)
_FOLLOW = re.compile(r"फॉलो|जुड|follow", re.I)
_PROMO = re.compile(r"हमारे|channel|के\s+साथ|कर\s+सकते\s+हैं", re.I)
_GROUP = re.compile(r"^(?:whatsapp|telegram|facebook)\s+group$", re.I)
# embedded tweets: a pic.twitter.com link, or the credit line "— Name (@handle) June 18, 2024"
_TWEET = re.compile(r"pic\.twitter\.com/|—\s?[^—\n]{1,60}\(@\w{1,30}\)\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s*$")
# markers inside a line: the "… [+]" read-more marker (it can sit inside a word) and "(अधिक पढ़ें . )"
_INLINE = re.compile(r"…\s*\[\+\]\s*|\(\s*अधिक\s+पढ\u093c?\u0947\u0902\s*\.?\s*\)")
# lines of 40+ characters found in 3 or more documents of the same site: site intros, footers, contact blocks
SITE_MIN_LEN, SITE_MIN_DOCS = 40, 3
SITE_LINES = set()


def _prepare(docs):  # renamed by Data B (was prepare), so the section has one public function
    """One pass over the pack before C1: docs = iterable of (text, meta). Fills SITE_LINES with (site, line)."""
    seen = collections.defaultdict(set)
    for i, (text, meta) in enumerate(docs):
        h = _host(meta)
        for line in set(l.strip() for l in text.split("\n")):
            if len(line) >= SITE_MIN_LEN:
                seen[(h, line)].add(i)
    SITE_LINES.clear()
    SITE_LINES.update(k for k, v in seen.items() if len(v) >= SITE_MIN_DOCS)


def c1_strip_lines(text, meta=None):
    h = _host(meta)
    out = []
    for line in _INLINE.sub("", text).split("\n"):
        k = _key(line)
        drop = any(p.search(k) and len(k) <= n for p, n in C1_LINES)
        drop = drop or (len(k) <= 200 and _PLATFORM.search(k) and _FOLLOW.search(k) and _PROMO.search(k))
        drop = drop or bool(_GROUP.match(k)) or (len(k) <= 300 and _TWEET.search(k))
        drop = drop or (h, line.strip()) in SITE_LINES
        if not drop:
            out.append(line)
    return "\n".join(out)
```

4. **Harm test:** see the results on PR #83.

## Medicine 5: C2

1. **Disease:** C2. Description: see the author's sheet, section C2.

```python
C2_MIN = 30   # characters; shorter lines (names, headings) repeat naturally
C2_SENT = 50  # a repeated sentence inside running text must be this long
_END = ("।", ".", "?", "!", "॥")
_SENT_SPLIT = re.compile(r"(?<=[।?!])\s+")


def c2_dedup_lines(text, meta=None):
    """Keep one full copy of a passage. Remove (1) a long line that is only a glued copy of other lines (80 % or
    more of it is other lines of the same text), (2) a later exact copy of a line, (3) a teaser line cut with an
    ellipsis whose text is repeated elsewhere, (4) a sentence (ends with । . ? ! or is 70+ characters) that sits
    whole inside a longer line: a pull quote, standfirst or summary; the first line (a title or standfirst of 40+
    characters) counts too, (5) a later exact copy of a sentence of 50+ characters inside running text.
    Short subheadings without an end mark stay."""
    lines = text.split("\n")
    keys = [l.strip() for l in lines]
    first = next((i for i, k in enumerate(keys) if k), -1)
    glued = set()
    for i, k in enumerate(keys):
        if len(k) >= 200:
            parts = {o for j, o in enumerate(keys) if j != i and len(o) >= C2_MIN and o in k}
            if sum(len(p) for p in parts) >= 0.8 * len(k):
                glued.add(i)
    keys2 = [("" if i in glued else k) for i, k in enumerate(keys)]
    seen, out, seen_sent = set(), [], set()
    for i, k in enumerate(keys):
        drop = i in glued
        if not drop and len(k) >= C2_MIN:
            if k in seen:
                drop = True                                              # exact repeat of an earlier line
            else:
                core = re.sub(r"[.…\s]+$", "", k)
                cut = k != core and (k.endswith("…") or k.endswith("..."))
                probe = core if cut and len(core) >= C2_MIN else k
                sentence = len(k) >= 70 or k.endswith(_END) or (i == first and len(k) >= 40)
                if text.count(probe) >= 2:                               # cheap test before the line scan
                    for j, o in enumerate(keys2):
                        if j == i or o == k or not o:
                            continue
                        if (cut and len(core) >= C2_MIN and core in o and len(o) > len(core)) or \
                           (sentence and len(o) >= len(k) + 20 and k in o):
                            drop = True                                  # teaser, pull quote, standfirst
                            break
        seen.add(k)
        if drop:
            continue
        if len(k) >= C2_SENT:                                            # (5) repeated sentence inside a line
            kept = []
            for s in _SENT_SPLIT.split(lines[i]):
                st = s.strip()
                if len(st) >= C2_SENT and st in seen_sent:
                    continue
                seen_sent.add(st)
                kept.append(s)
            new = " ".join(kept)
            out.append(new if new.strip() != k else lines[i])
        else:
            out.append(lines[i])
    return "\n".join(out)
```

4. **Harm test:** see the results on PR #83.

## Medicine 6: C4

1. **Disease:** C4. Description: see the author's sheet, section C4.

```python
_SEP = re.compile(r"\n[ \t]*-[ \t]*\n")


def c4_split(text, meta=None):
    """Split at lone '-' separator lines (listing pages that join complete articles) when there are 2 or more
    separators and at least 2 parts of 200+ characters. Returns the list of parts, or the text unchanged."""
    if len(_SEP.findall(text)) < 2:
        return text
    parts = [p.strip() for p in _SEP.split(text) if p.strip()]
    return parts if sum(len(p) >= 200 for p in parts) >= 2 else text
```

4. **Harm test:** see the results on PR #83.

## Medicine 7: C3

1. **Disease:** C3. Description: see the author's sheet, section C3.

```python
_EXCERPT = re.compile(r"\s*(?:\[…\]|\[\.\.\.\])\s*$")
_ELLIPSIS = re.compile(r"(\S+?)\s*(?:…|\.\.\.)\s*$")
# a document that ends "<word>…" with one of these words was cut mid-sentence (a postposition or conjunction)
_CUT_WORDS = {"के", "की", "का", "को", "में", "से", "पर", "और", "लेकिन", "कि", "ने", "तक", "या", "व", "तथा", "एवं", "जो",
              "इस", "उस", "इन", "उन", "लिए", "द्वारा", "साथ", "बाद", "पहले", "एक", "भी", "ही", "तो", "अपने", "अपनी"}
_LAST_END = re.compile(r"[।?!॥](?=[^।?!॥]*$)")


def c3_trim_cut_end(text, meta=None):
    """When the text ends with an excerpt marker ([…], [...]) or with '…' / '...' right after a postposition or
    conjunction, delete the cut fragment: back to the last sentence end in the last line, or the whole last line."""
    t = text.rstrip()
    m = _EXCERPT.search(t)
    if not m:
        m = _ELLIPSIS.search(t)
        if not m or m.group(1).strip("…., ") not in _CUT_WORDS:
            return text
    head = t[:m.start()]
    nl = head.rfind("\n")
    last = head[nl + 1:]
    e = _LAST_END.search(last)
    return (head[:nl + 1] + last[:e.end()]) if e else head[:max(nl, 0)].rstrip()
```

4. **Harm test:** see the results on PR #83.

## Medicine 8: D3

1. **Disease:** D3. Description: see the author's sheet, section D3.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
import collections
import urllib.parse

NUKTA = "\u093c"
DEV = r"\u0900-\u097f"
CONS = r"\u0915-\u0939\u0958-\u095f"      # Devanagari consonants, incl. the precomposed nukta letters
SIGN = r"\u093e-\u094d"                   # dependent vowel signs and virama


def _key(line):
    """Matching key: strip spaces, bullets and nukta, so पढ़ें / पढें and spacing variants match alike."""
    return line.replace(NUKTA, "").strip().lstrip("•-–*· ").strip()


def _host(meta):
    url = (meta or {}).get("u") or ""
    h = re.sub(r"^www\.", "", urllib.parse.urlparse(url).netloc.lower())
    p = h.split(".")
    return ".".join(p[-3:]) if h.endswith((".co.in", ".org.in")) else ".".join(p[-2:])
# end of the shared definitions
```

```python
# A bracketed run of two or more Latin words right after Devanagari text.
# "(ED)" or "(IMD)" stays: one word. "(12 acres donated to 16 farmers)" or "(Social Media)" goes; an all-capitals
# run such as "(DU PUY KAMP)" is a name and stays.
_GLOSS = re.compile(r"(?<=[" + DEV + r"])\s*[\(\[]\s*([A-Za-z][A-Za-z0-9.,&'’\-]*(?:\s+[A-Za-z0-9.,&'’\-]+)+)\s*[\)\]]")
# An English SEO kicker at the start of a line, right before Hindi text: "Rishikesh News: ऋषिकेश में ...".
_KICKER = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9.&'’\-]*(?:\s+[A-Za-z0-9.&'’\-+()]+){1,8})\s*:\s*(?=[" + DEV + r"])", re.M)
_KICKER_WORD = re.compile(
    r"\b(?:news|updates?|live|video|viral|recruitment|admit\s+card|result|notification|vacancy|scheme|alert|breaking|"
    r"exclusive|tips|tricks|horoscope|weather|accidents?|action|crisis|violence|link|apply|expiry|date|jobs?|portal|"
    r"loan|list|merit|form|guidelines|editorial|speaker|admission|bharti|exam)\b", re.I)


def d3_strip_gloss(text, meta=None):
    text = _GLOSS.sub(lambda m: m.group(0) if m.group(1).upper() == m.group(1) else "", text)
    return _KICKER.sub(lambda m: m.group(1) if _KICKER_WORD.search(m.group(2)) else m.group(0), text)
```

4. **Harm test:** see the results on PR #83.

## Medicine 9: A6

1. **Disease:** A6. Description: see the author's sheet, section A6.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
import collections
import urllib.parse

NUKTA = "\u093c"
DEV = r"\u0900-\u097f"
CONS = r"\u0915-\u0939\u0958-\u095f"      # Devanagari consonants, incl. the precomposed nukta letters
SIGN = r"\u093e-\u094d"                   # dependent vowel signs and virama


def _key(line):
    """Matching key: strip spaces, bullets and nukta, so पढ़ें / पढें and spacing variants match alike."""
    return line.replace(NUKTA, "").strip().lstrip("•-–*· ").strip()


def _host(meta):
    url = (meta or {}).get("u") or ""
    h = re.sub(r"^www\.", "", urllib.parse.urlparse(url).netloc.lower())
    p = h.split(".")
    return ".".join(p[-3:]) if h.endswith((".co.in", ".org.in")) else ".".join(p[-2:])
# end of the shared definitions
```

```python
# Latin I, l or i (II for a double danda) used as the danda after Devanagari text, before a line end or more
# Devanagari. An English word after it (the pronoun "I") keeps it.
_LAT_DANDA = re.compile(r"(?<=[" + DEV + r"])([ \t]?)(II|I|l|i)(?=[ \t]*(?:\n|$|[" + DEV + r"\"“”]))")
_TO_DEV = str.maketrans("0123456789", "\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f")


def a6_fix_script(text, meta=None):
    text = _LAT_DANDA.sub(lambda m: m.group(1) + ("॥" if m.group(2) == "II" else "।"), text)
    # a number written with both Latin and Devanagari digits (१0७) becomes all Devanagari
    return re.sub(r"[0-9\u0966-\u096f]+", lambda m: m.group().translate(_TO_DEV)
                  if re.search("[०-९]", m.group()) and re.search("[0-9]", m.group()) else m.group(), text)
```

4. **Harm test:** see the results on PR #83.

## Medicine 10: G1

1. **Disease:** G1. Description: see the author's sheet, section G1.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
import collections
import urllib.parse

NUKTA = "\u093c"
DEV = r"\u0900-\u097f"
CONS = r"\u0915-\u0939\u0958-\u095f"      # Devanagari consonants, incl. the precomposed nukta letters
SIGN = r"\u093e-\u094d"                   # dependent vowel signs and virama


def _key(line):
    """Matching key: strip spaces, bullets and nukta, so पढ़ें / पढें and spacing variants match alike."""
    return line.replace(NUKTA, "").strip().lstrip("•-–*· ").strip()


def _host(meta):
    url = (meta or {}).get("u") or ""
    h = re.sub(r"^www\.", "", urllib.parse.urlparse(url).netloc.lower())
    p = h.split(".")
    return ".".join(p[-3:]) if h.endswith((".co.in", ".org.in")) else ".".join(p[-2:])
# end of the shared definitions
```

```python
_G1_SPACE = re.compile(r"(?<=[" + CONS + r"\u093c])[ \t]+(?=[" + SIGN + r"])")
_G1_PUNCT = re.compile(r"([" + CONS + r"\u093c]),([\u093e-\u094c])")
_G1_MARK = re.compile(r"(?<=[" + CONS + r"\u093c])…\s*\[\+\]\s*(?=[" + SIGN + r"])")   # read-more marker inside a word


def g1_join_sign(text, meta=None):
    """Join a vowel sign or virama to the consonant before it when a space or a read-more marker cut them apart
    (a consonant, a space, then a vowel sign becomes one syllable), and move a comma typed inside a syllable."""
    return _G1_PUNCT.sub(r"\1\2,", _G1_SPACE.sub("", _G1_MARK.sub("", text)))
```

4. **Harm test:** see the results on PR #83.

## Medicine 11: F1

1. **Disease:** F1. Description: see the author's sheet, section F1.

```python
_EMAIL = re.compile(r"[\w.+-]+@(?:gmail|googlemail|yahoo|ymail|rocketmail|hotmail|outlook|live|msn|rediffmail|aol|"
                    r"protonmail|icloud)\.[A-Za-z.]{2,6}", re.I)
_MOBILE = re.compile(r"(?<![\d+])(?:\+91[\s-]?|0)?[6-9]\d{9}(?!\d)")
_VEHICLE = re.compile(r"\b[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b")


def f1_remove_contacts(text, meta=None):
    """Delete personal webmail addresses, Indian mobile numbers and vehicle registration numbers."""
    return _VEHICLE.sub("", _MOBILE.sub("", _EMAIL.sub("", text)))
```

4. **Harm test:** see the results on PR #83.

## Medicine 12: D2

1. **Disease:** D2. Description: see the author's sheet, section D2.

```python
def d2_keep(text, meta=None):
    """No change. In this pack, D2 is names of schemes and posts (Bharti, Yojana, Rashifal) and SEO headings."""
    return text
```

The author's run-order pipeline, kept unchanged and not run (see change 3):

```text
MEDICINES = [  # run order
    ("D4", "drop", d4_drop_mt),
    ("C5", "drop", c5_drop_list),
    ("B2", "fix", b2_strip_tags),
    ("C1", "fix", c1_strip_lines),
    ("C2", "fix", c2_dedup_lines),
    ("C4", "fix", c4_split),     # fix by splitting into separate documents
    ("C3", "fix", c3_trim_cut_end),
    ("D3", "fix", d3_strip_gloss),
    ("A6", "fix", a6_fix_script),
    ("G1", "fix", g1_join_sign),
    ("F1", "fix", f1_remove_contacts),
    ("D2", "keep", d2_keep),
]


def run_all(text, meta):
    """Apply every medicine in run order. Returns a list of output documents (empty when dropped)."""
    docs = [text]
    for _, _, fn in MEDICINES:
        nxt = []
        for t in docs:
            r = fn(t, meta)
            if r is None:
                return []
            nxt += r if isinstance(r, list) else [r]
        docs = nxt
    return docs
```

4. **Harm test:** see the results on PR #83.
