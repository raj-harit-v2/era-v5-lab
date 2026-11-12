# Medicine sheet: ind-hi-hplt (pankajkr23)

**Built from all 500 labelled rows** of the pack (151 labelled on 27 Oct, 349 on 28 Oct). Every number below is printed by the code that ran; every example quote was checked at its offset.

**Diseases found more than five times** (documents among the 500): C1 251, D3 122, D4 85, C2 80, C4 39, C5 28, D2 18, C3 16, F1 15, G1 12, A6 11, B2 6. Each has a medicine below. Not more than five, so no medicine: F3 4, B4 4, D5 2, H2 1, D1 1, A1 1, A3 1. Counts are documents, not occurrences. All four F3 (harmful) documents are labelled `drop`.

**Harm-test set.** The official Hindi gold set (Data B) is not published yet. Every harm test runs on a **proxy gold set: the 123 documents of this pack labelled `clean`** after reading them in full (45 from the first 151 rows, 78 from the other 349). Limits:

- One reading process made both the labels and this set. A blind second reading of 35 random documents agreed on 34 verdicts (Cohen's kappa 0.95), but a disease missed in a `clean` document stays invisible to the test.
- With 123 documents, 1% is 1.23 documents: one changed document passes (0.81%), two fail. 0 of 123 only rules out a true harm rate above 2.4% (95% confidence); the official gold set is needed to show 1% or less.
- The rules below were tuned on all 500 rows, so these numbers are in-sample. The honest out-of-sample check is the next table.

**Out-of-sample check.** The first draft of this sheet (27 Oct) had five medicines built on the first 151 rows. Run unchanged on the 349 rows labelled later:

| Medicine (27 Oct draft) | Acts on new rows with the disease | Proxy gold changed or dropped |
|---|---|---|
| D4 | 41 of 71 | 0 of 123 |
| C1 | 62 of 182 | 0 of 123 |
| C2 | 28 of 63 | 0 of 123 |
| D3 | 15 of 60 | 1 of 123 |
| D2 | 0 of 9 | 0 of 123 |

The draft rules transferred well for D4 (a classifier score) and poorly for C1 and D3 (phrase lists from one set of sites). This sheet adds what the new rows showed; expect the same drop in reach on new sites.

**How to read the numbers.** Each medicine takes `(text, meta)` and returns the new text, `None` to drop the document, or (C4) a list of documents. "Acts on" = the medicine changes or drops a labelled document that has the disease. "Whole pack" = documents changed or dropped among all 500.

| # | Disease | Docs | Action | Proxy gold (changed, dropped) | Acts on labelled docs with the disease | Whole pack (changed, dropped) |
|---|---|---|---|---|---|---|
| 1 | D4 Bad machine translation | 85 | drop | 0, 0 | 48 of 85 | 0, 48 |
| 2 | C5 Lists of keywords or links | 28 | drop | 0, 0 | 23 of 28 | 0, 30 |
| 3 | B2 HTML tags | 6 | fix | 0, 0 | 6 of 6 | 6, 0 |
| 4 | C1 Boilerplate | 251 | fix | 0, 0 | 184 of 251 | 184, 0 |
| 5 | C2 Repeated passage | 80 | fix | 0, 0 | 57 of 80 | 65, 0 |
| 6 | C4 Two documents joined | 39 | fix | 0, 0 | 4 of 39 | 6, 0 |
| 7 | C3 Truncated document | 16 | fix | 0, 0 | 8 of 16 | 8, 0 |
| 8 | D3 Mixed language | 122 | fix | 0, 0 | 54 of 122 | 62, 0 |
| 9 | A6 Wrong or mixed script | 11 | fix | 0, 0 | 9 of 11 | 10, 0 |
| 10 | G1 Cut at the vowel sign | 12 | fix | 0, 0 | 12 of 12 | 12, 0 |
| 11 | F1 Personal data | 15 | fix | 0, 0 | 11 of 15 | 14, 0 |
| 12 | D2 Romanised Indic | 18 | keep | 0, 0 | 0 of 18 | 0, 0 |

**Run order:** D4 → C5 → B2 → C1 → C2 → C4 → C3 → D3 → A6 → G1 → F1 → D2. Drops come first (no work on documents that go); tags go before the line rules; boilerplate goes before the repeat check; the split comes before the end trim, so each part is trimmed; character fixes (A6, G1) and contact removal run last on the cleaned text. **All twelve together:** proxy gold 0 changed, 0 dropped; whole pack 211 changed, 64 dropped, 225 unchanged. Against my verdicts: of the 89 `drop` documents, 63 are dropped, 12 changed and 14 untouched; of the 288 `fix` documents, 199 are changed, 1 dropped and 88 untouched; all 123 `clean` documents are untouched.

Shared code (Python 3, standard library only):

```python
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
```

## Medicine 1: D4, bad machine translation

1. **Disease:** D4, 85 documents. Three examples:
   - `dc736fdd65ba2f0c`: `पॉप अप हो रहे हैं जगह` at 918 ("popping up everywhere" copied word for word; MT score 0.80)
   - `38a4c524a43a0adb`: `आप MP4 जोड़ सकते हैं FlipHTML5 में` at 86 (English word order; MT score 0.75)
   - `c8d69b4928763080`: `रविवार टाइम्स` at 40709 (Sunday Times half-translated as a name, in a university directory page; MT score 0.85)
2. **Medicine:** drop the document when HPLT's web-register classifier gives the MT (machine-translated) label a score of 0.50 or more. The score is in each document's `meta`. No rule can repair a translation line by line, so the medicine works on the whole document.

   ```python
   MT_DROP = 0.50


   def d4_drop_mt(text, meta):
       """Drop the document when HPLT's web-register classifier gives the MT (machine-translated) label >= 0.50."""
       mt = ((meta or {}).get("web-register") or {}).get("MT", 0.0)
       return None if mt >= MT_DROP else text
   ```

3. **Action:** drop the document.
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%). The highest MT score in the proxy gold set is 0.19. Threshold check on the 500 rows:

   | Threshold | Proxy gold dropped | D4 docs dropped | D4 docs labelled `fix` that it drops | Whole pack dropped |
   |---|---|---|---|---|
   | 0.30 | 0 | 60 of 85 | 3 | 62 |
   | 0.40 | 0 | 57 of 85 | 3 | 58 |
   | 0.50 | 0 | 48 of 85 | 1 | 48 |
   | 0.60 | 0 | 40 of 85 | 0 | 40 |
   | 0.70 | 0 | 32 of 85 | 0 | 32 |

   0.50 drops one D4 document I labelled `fix` (`27b477b016ace389`, MT 0.59: speaker bios, readable but machine-translated throughout); 0.60 drops none of them but keeps 8 more D4 documents. 0.50 is kept.
5. **Side effects:** it acts on 48 of 85 (7 of 14 in the first 151 rows, 41 of 71 in the other 349). It acts on no labelled document without the code. It misses 37 D4 documents, 25 of them labelled `drop`: most have low scores, for example the church-translation family (`a85a2363de961b2e`, `d25f5eb32b944379`, `1e638ceb8920faf1` and 3 more, MT 0.08–0.17) and readable translations with sparse errors. It depends on the classifier: a good human translation with a high score would be dropped, and a machine translation with a low score is kept.

## Medicine 2: C5, lists of keywords or links

1. **Disease:** C5, 28 documents. Three examples:
   - `4ee77e0c84fdefdf`: `[…]` at 347 and 614 and 931 (tag page of 10 cut teasers)
   - `ca38e3770cd4bd18`: `विदेशी मुद्रा पर पैसे कमाएं` at 561 and 2241 and 5372 (keyword stuffed into sentences on a spun spam page)
   - `140baccfb8c27489`: `Sky247 रजिस्टर कैशबैक अतिरिक्त` at 3508 (betting promo)
2. **Medicine:** drop a tag, archive or search page (3 or more teaser lines of 60+ characters that end with an excerpt marker, or 'Read More' lines, making up a quarter of the lines or more), and drop a page that carries the star-rating widget of the spun spam template found on 11 documents.

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

3. **Action:** drop the document.
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 23 of 28 (4 of 5 in the first 151 rows, 19 of 23 in the other 349). It also acts on 7 labelled documents without the code (7 `drop`: `07cd8705d5bf839d`, `b58829cf9c7439aa`, `8389d9040da9b505`, `eecd543bde8c247b`, `e547dfa8be905ea3`, `6cd012c49dbd12e6` and 1 more). It misses 5 (`e7eba3aa539d23c7`, `b69bf008c2be42b5`, `c5f74407a2893690`, `012575be42ba7add`, `140baccfb8c27489`): a tag page whose teasers are complete standfirsts, a book list whose cut blurbs are less than a quarter of its lines, a link-roundup post, and referral or betting promos (a promo word list matched good `fix` documents too, so it was left out). The documents it drops without a C5 label are dream-dictionary result pages and a comment-spam page, all labelled `drop`. The widget rule is site-specific.

## Medicine 3: B2, HTML tags

1. **Disease:** B2, 6 documents. Three examples:
   - `1c61f6e0c56fbbc9`: `/>` at 9375 and 10210 (tag fragment glued between two sentences)
   - `74bc7d9844e3a25d`: `src=` at 88019 (image-tag residue with alt text and a CDN link)
   - `c2b54c4cd92b3a0c`: `/>` at 28877 (tag fragment)
2. **Medicine:** remove image-tag residue (alt text + `src="..."` + `/>`), whole tags, and stray `/>` fragments. The fragment sat where a tag split two blocks, so it becomes a line break.

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

3. **Action:** fix the text.
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 6 of 6 (1 of 1 in the first 151 rows, 5 of 5 in the other 349). It acts on no labelled document without the code. All six B2 documents are machine-translated directory pages that D4 drops first, so in the pipeline it rarely acts. A `<` followed by a letter and a `>` in prose (rare in Hindi) would be read as a tag.

## Medicine 4: C1, boilerplate

1. **Disease:** C1, 251 documents. Three examples:
   - `8a6a9e11bf0f5d9f`: `इसे भी पढ़ें:-` at 916 (link to another article)
   - `ca38e3770cd4bd18`: `अधिकतम रेटिंग 5` at 8157 (star-rating widget line)
   - `9cc6d23c8cfcaa87`: `The views expressed above belong to the author` at 5467 (English site footer)
2. **Medicine:** delete a whole line when it is page furniture: a related-article link, a stand-alone label (ADVERTISEMENT, Share:, More Stories, Post Views, N thoughts on …), comment furniture (कोई टिप्पणी नहीं:, एक टिप्पणी भेजें, No comments, ReplyDelete, 0 Comments), star-rating lines, a blog sign-off, an image, photo or recipe credit, a pointer to a video that is not in the text, an ad placeholder, a disclaimer or syndication note, an English site footer, a follow-us promo, a group-join link, or an embedded tweet. Each pattern has a length limit, so a long line that only starts like furniture stays. Nukta and spacing are ignored when matching. Two more rules: the `… [+]` read-more marker is cut out wherever it sits, and a line of 40+ characters that appears in 3 or more documents of the same site is deleted (a first pass over the pack finds them: 16 lines here, such as a directory site's intro, an injection-machine maker's welcome paragraph and a blog's sign-off).

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


   def prepare(docs):
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

3. **Action:** fix the text (delete the lines and markers).
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 184 of 251 (64 of 69 in the first 151 rows, 120 of 182 in the other 349). It acts on no labelled document without the code. It misses 67 C1 documents (`57294dfeff306304`, `e122c2e13453e49b`, `157a92dae8c7615d`, `2a5f73bb1b272717` and 63 more): reader comments and author bios, which are free text; furniture glued into a sentence (a site-name watermark, a teaser of another story); one-off footers and promos of sites with fewer than three documents here; category headers. A real one-line heading such as `Categories` or `Tags:` would be deleted, and so would content repeated on 3 pages of one site (here one dream-dictionary entry, on pages that D4 and C5 drop anyway). The phrase list comes from these 500 rows, so other sites' furniture is missed (see the out-of-sample table).

## Medicine 5: C2, repeated passage

1. **Disease:** C2, 80 documents. Three examples:
   - `36445006095beb35`: `अगर आपके पास दूध या दही नहीं है` at 623 and 720 (the same sentence twice)
   - `4341269d71f31499`: `गर्मियों में लोग अक्सर अपनी सेहत का विशेष ख्याल` at 67 and 354 (intro paragraph repeated in full)
   - `fc3021f18b27b447`: `मध्य प्रदेश में आज मोहन कैबिनेट की बैठक होगी।` at 110 and 277 (summary repeated as the first paragraph)
2. **Medicine:** keep one full copy of each passage. Delete (1) a long line that is only a glued copy of other lines, (2) a later exact copy of a line of 30+ characters, (3) a teaser cut with an ellipsis whose text appears again, (4) a sentence (it ends with । . ? ! or has 70+ characters; the first line counts at 40+ characters) that sits whole inside a longer line: a title, pull quote, standfirst or summary, (5) a later exact copy of a sentence of 50+ characters inside running text.

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

3. **Action:** fix the text (delete the extra copies).
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%). Tuning disclosed: an earlier version also deleted any 30+ character line found inside a longer line and changed a proxy-gold document (two subheadings that reuse a sentence); the end-mark-or-length condition fixed it.
5. **Side effects:** it acts on 57 of 80 (13 of 17 in the first 151 rows, 44 of 63 in the other 349). It also acts on 8 labelled documents without the code (5 `drop`, 3 `fix`: `74bc7d9844e3a25d`, `dc736fdd65ba2f0c`, `66f615f4832cdea0`, `b2038fc0ce4c0647`, `23d103e73df589ba`, `8dbd286b4981e1cb` and 2 more). It misses 23 (`fade280a8142f524`, `9621cf17c5736cf0`, `b8ff0f6562433110`, `0e682985aa8620da` and 19 more): repeats with small changes (near duplicates), short repeated titles and names under 30 characters, and blurbs repeated on listing pages with different wording. Deliberate repeats of 50+ characters (a refrain, a slogan repeated in a speech) lose their later copies; a heading that also appears inside a longer line is deleted.

## Medicine 6: C4, two documents joined

1. **Disease:** C4, 39 documents. Three examples:
   - `b7b6f0875de87466`: `शंख का महत्व हम सभी जानते हैं` at 6561 (one of 25 complete articles joined on a listing page)
   - `fa80fce65e52e2b5`: `वाशिंगटन। भारतीय मूल के वैज्ञानिक` at 3299 (one of 6 unrelated reports joined)
   - `eecd543bde8c247b`: `सपना देख और एक घोड़ा देख` at 42420 (one of 29 dream-dictionary entries joined)
2. **Medicine:** split the document at lone `-` separator lines when there are 2 or more of them and at least 2 parts of 200+ characters. Other joins have no mark a rule can trust: a second dateline or headline was tested as a split point and also fired inside good single articles, so it was left out.

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

3. **Action:** fix the text by splitting it into separate documents (counted as a change).
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 4 of 39 (0 of 3 in the first 151 rows, 4 of 36 in the other 349). It also acts on 2 labelled documents without the code (2 `drop`: `9d7b9c8580e163e8`, `012575be42ba7add`). It acts on only a few documents: about half the C4 documents are spam or dream pages that D4 and C5 drop, and joins without a separator (`ca38e3770cd4bd18`, `7a2bc38b934a51ad`, `8fed2d4464e4cc06`, `84b3adb7174dfd68` and 31 more) stay joined. The two labelled documents it splits without a C4 label are a forum page and a book list, both labelled `drop`. A story that uses a lone `-` as a scene break would be split.

## Medicine 7: C3, truncated document

1. **Disease:** C3, 16 documents. Three examples:
   - `4ee77e0c84fdefdf`: `[…]` at 2887 (final teaser cut mid-sentence)
   - `344c7f7488e9198a`: `इनके नम्बर…` at 1061 (text stops after a cut list)
   - `e7eba3aa539d23c7`: `यह जो आरोपित मन है, यह..` at 615 (excerpt cut mid-sentence)
2. **Medicine:** when the text ends with an excerpt marker (`[…]`, `[...]`) or with `…` / `...` right after a postposition or conjunction (के, की, को, में, और, …), delete the cut fragment: back to the last sentence end in the last line, or the whole last line. A text that ends with a full sentence and `…` (two proxy-gold documents end like that) is left alone.

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

3. **Action:** fix the text (trim the cut end).
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 8 of 16 (4 of 4 in the first 151 rows, 4 of 12 in the other 349). It acts on no labelled document without the code. It misses 8 (`9d7b9c8580e163e8`, `e9245802d6596af1`, `e7eba3aa539d23c7`, `344c7f7488e9198a` and 4 more): cuts in the middle of a document, cuts with no marker, a cut teaser followed by a `Read More` line, and teasers cut after a noun or a verb. Most C3 documents are teaser pages that C5 drops first. A word list decides what a cut looks like, so a sentence that really ends on one of those words before `…` is trimmed.

## Medicine 8: D3, mixed language

1. **Disease:** D3, 122 documents. Three examples:
   - `e28c5b447cedb91c`: `(12 acres donated to 16 farmers)` at 240 (English gloss that repeats the Hindi before it)
   - `c6bf916045ab8652`: `Rishikesh News:` at 0 (English SEO kicker before the Hindi headline)
   - `7a936e050a3e704f`: `(Aries Love Horoscope)` at 399 (English gloss after each sign name, 12 times)
2. **Medicine:** remove only the English that repeats or labels the Hindi: (1) a bracketed run of two or more Latin words right after Devanagari text, unless the run is all capitals (a name such as `(DU PUY KAMP)`); one-word acronyms such as `(ED)` stay; (2) an English kicker of two or more words at the start of a line, before Hindi text, when it holds a kicker word (News, Update, Recruitment, Viral, …). English inside a Hindi sentence is natural mixing and is not touched.

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

3. **Action:** fix the text (delete the gloss or kicker).
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%). Tuning disclosed: the 27 Oct version removed the all-capitals name gloss in one proxy-gold document; the all-capitals exception was added for that.
5. **Side effects:** it acts on 54 of 122 (39 of 62 in the first 151 rows, 15 of 60 in the other 349). It also acts on 8 labelled documents without the code (1 `drop`, 7 `fix`: `c2b54c4cd92b3a0c`, `f9459f538d631672`, `de28b50e61a61600`, `3beed481c79246dc`, `62df9947c03bbb97`, `f82b02d1f13dc036` and 2 more). The 68 D3 documents it leaves alone are mostly natural mixing inside sentences and English headings, which it does not target. It removes Latin name glosses in title case, such as `(Rakhi Sawant)` or `(Mumbai Indians)`, which I did not label D3; the Hindi name stays, so little is lost.

## Medicine 9: A6, wrong or mixed script

1. **Disease:** A6, 11 documents. Three examples:
   - `703c5cb5b2bd7bee`: `नहीं हैI` at 1029 (Latin capital I as the danda)
   - `4b82ad7e92695e55`: `इसे समर्थ बनाता है l` at 214 (Latin small l as the danda, 306 times in this document)
   - `ac36464759436542`: `चला गया है II` at 2675 (II as the double danda)
2. **Medicine:** replace a Latin `I`, `l` or `i` (or `II`) that follows Devanagari text and ends a sentence (before a line end or more Devanagari) with `।` (or `॥`); an English word after it, such as the pronoun `I`, keeps it. Write a number that mixes Latin and Devanagari digits (१0७) in Devanagari digits.

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

3. **Action:** fix the text.
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 9 of 11 (1 of 1 in the first 151 rows, 8 of 10 in the other 349). It also acts on 1 labelled document without the code (1 `drop`: `74bc7d9844e3a25d`). It misses 2 (`1e1f81ab0381c3c9`, `72a488f980254d7f`): a verse number with a space between its Latin and Devanagari digits, and a single Latin letter inside a Devanagari word. The Roman numeral in `डिवीजन I` at the end of a sentence becomes a danda (one directory page, dropped by D4 anyway).

## Medicine 10: G1, cut at the vowel sign

1. **Disease:** G1, 12 documents. Three examples:
   - `1c61f6e0c56fbbc9`: U+0020 + U+0942, vowel sign at 4258 (a vowel sign left after a space by the read-more marker)
   - `c8d69b4928763080`: U+0020 + U+094B, vowel sign at 47729 (the same, in another directory page)
   - `a02caf8e245bbcf3`: `ह,ैतो` at 7058 (a comma typed inside a syllable)
2. **Medicine:** join a vowel sign or virama to the consonant before it when a space or the `… [+]` read-more marker cut them apart, and move a comma typed inside a syllable to after it. It only joins after a consonant, so a vowel sign after a vowel letter, a digit or Latin text is left for a person to check.

   ```python
   _G1_SPACE = re.compile(r"(?<=[" + CONS + r"\u093c])[ \t]+(?=[" + SIGN + r"])")
   _G1_PUNCT = re.compile(r"([" + CONS + r"\u093c]),([\u093e-\u094c])")
   _G1_MARK = re.compile(r"(?<=[" + CONS + r"\u093c])…\s*\[\+\]\s*(?=[" + SIGN + r"])")   # read-more marker inside a word


   def g1_join_sign(text, meta=None):
       """Join a vowel sign or virama to the consonant before it when a space or a read-more marker cut them apart
       (a consonant, a space, then a vowel sign becomes one syllable), and move a comma typed inside a syllable."""
       return _G1_PUNCT.sub(r"\1\2,", _G1_SPACE.sub("", _G1_MARK.sub("", text)))
   ```

3. **Action:** fix the text.
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 12 of 12 (1 of 1 in the first 151 rows, 11 of 11 in the other 349). It acts on no labelled document without the code. It misses none of the labelled G1 documents. A space typed on purpose between a consonant and a vowel sign does not exist in normal Hindi, so the risk is low; a split syllable inside a spaced-out word (`छो ड़ े`) is joined only where a consonant comes before the sign.

## Medicine 11: F1, personal data

1. **Disease:** F1, 15 documents. Three examples:
   - `717813c65d28deec`: email at offset 13412
   - `36d8116218d8e18a`: phone at offset 9993
   - `9854f6f91d1e5958`: vehicle registration number at offset 3128
2. **Medicine:** delete personal webmail addresses (gmail, yahoo, hotmail, rediffmail and similar), Indian mobile numbers and vehicle registration numbers. Values are never copied into this sheet (the repo is public).

   ```python
   _EMAIL = re.compile(r"[\w.+-]+@(?:gmail|googlemail|yahoo|ymail|rocketmail|hotmail|outlook|live|msn|rediffmail|aol|"
                       r"protonmail|icloud)\.[A-Za-z.]{2,6}", re.I)
   _MOBILE = re.compile(r"(?<![\d+])(?:\+91[\s-]?|0)?[6-9]\d{9}(?!\d)")
   _VEHICLE = re.compile(r"\b[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b")


   def f1_remove_contacts(text, meta=None):
       """Delete personal webmail addresses, Indian mobile numbers and vehicle registration numbers."""
       return _VEHICLE.sub("", _MOBILE.sub("", _EMAIL.sub("", text)))
   ```

3. **Action:** fix the text (delete the value).
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%).
5. **Side effects:** it acts on 11 of 15 (1 of 1 in the first 151 rows, 10 of 14 in the other 349). It also acts on 3 labelled documents without the code (3 `fix`: `157a92dae8c7615d`, `274d55294fbe497b`, `c7a2e4fc27755fcc`). It misses 4 (`a02caf8e245bbcf3`, `3c8e378530fce8ba`, `25c55c812e95073f`, `2769482745a359c7`): home and postal addresses, which no simple rule finds, and a registration number whose state code is written in Devanagari. It also deletes public contacts that are not personal data (a publisher's or a helpline's mobile number), and it leaves the label before the value (`फोन:`) in place.

## Medicine 12: D2, romanised Indic

1. **Disease:** D2, 18 documents. Three examples:
   - `8a6a9e11bf0f5d9f`: `Nagar Palika Bharti` at 1542 (post name in a headline)
   - `7a936e050a3e704f`: `Aaj Ka Love Rashifal` at 0 (SEO title)
   - `e2e8c748d77ed529`: `Amazon se online shopping kaise kare` at 2658 (heading in Latin letters)
2. **Medicine:** no change. In this pack, D2 is the names of schemes and posts (Bharti, Yojana, Rashifal) and short SEO headings inside otherwise Devanagari text. Deleting them would cut names out of headlines; transliterating them back to Devanagari needs a model, not a rule.

   ```python
   def d2_keep(text, meta=None):
       """No change. In this pack, D2 is names of schemes and posts (Bharti, Yojana, Rashifal) and SEO headings."""
       return text
   ```

3. **Action:** keep the text unchanged. D2 alone is not a reason to drop a document.
4. **Harm test:** proxy gold, 123 documents: **0 changed, 0 dropped (0.0%). PASS** (limit 1%). It changes nothing by construction.
5. **Side effects:** it acts on 0 of 18 (0 of 9 in the first 151 rows, 0 of 9 in the other 349). It acts on no labelled document without the code. A document that is mostly romanised Hindi would be kept; none of the 500 is like that.

## Run order in code

```python
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
