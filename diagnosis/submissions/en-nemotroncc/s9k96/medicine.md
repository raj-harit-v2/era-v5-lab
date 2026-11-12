# Medicine sheet: en-nemotroncc (s9k96)

Pack `en-nemotroncc`, 500 documents. Counts below come from all 500 documents, each read in full (`diagnosis/submissions/en-nemotroncc/s9k96/labels.csv`). Eight diseases have a medicine below: C1 (151 documents), C3 (78), C4 (70), C5 (60), D4 (14), A1 (14), B4 (11) and D3 (6). Others are in the last table. Every rule is a short Python function. The same code is in `medicine.py` (a function returns the fixed text, or `None` to drop the document).

**Harm test.** Gold set: the 34 gold documents of this pack, run with Data A's `harm_test.py` (PR #140, build of 30 Oct). Small-gold rule (TSAI): a medicine passes if it changes or drops at most max(1 document, 1%). All eight medicines pass: 0 of 34 documents changed or dropped. Each section also gives a proxy test: the rule run on my 218 documents labelled `clean` (all 500 documents are reviewed), where at most 2 may change or be dropped. The proxy also says how many reviewed documents of that disease the rule touches.

## Medicine 1: C1 boilerplate

1. **Disease:** C1, 151 documents. Examples:
   - `17f4af14c04c9fde`: `Primary tabs` (offset 39)
   - `b787548f4655559b`: `Search for:` (offset 1952)
   - `ca32200e3729539d`: `Click to expand...` (offset 1231)
2. **Medicine:** delete every line that is only a known widget or menu label (`Primary tabs`, `Search for:`, `Related posts`, `Share this:`, `Read more`, `Link copied`, `Quantity`, and a few more). A whole-line match is required, so a sentence that contains these words is never touched.
```python
WIDGET = re.compile(r"(?i)(?:primary tabs|search for:?|related (?:documents|posts|articles):?|click to expand\W*|read more\W*|\[?read more\W*\]?|share this:?|share on (?:other sites|[a-z ]+)|previous|next|menu|contents|advertisement|loading\W*|link copied|the link has been copied!?|post navigation|quantity|breadcrumb|logged|registered|banned|show more|you may also like[a-z ]*|subscribe to [a-z ]+|skip to (?:main )?content|back to top)")

def c1(t):
    """Delete lines that consist only of a known widget or menu label ('Primary tabs', 'Search for:', 'Related posts', 'Share this:' ...)."""
    return "\n".join(l for l in t.split("\n") if not WIDGET.fullmatch(l.strip()))
```
3. **Action:** fix the text (delete the label line); the document is kept.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents, Data A harm test) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 0 |

   Gold set: 34 documents, Data A build of 30 Oct; TSAI rule: pass if at most max(1 document, 1%) changes. Result: 0.00% changed, 0.00% dropped, PASS.

   The rule changes 27 of the 151 reviewed C1 documents.
5. **Side effects:** most reviewed C1 lines are not on the label list. Examples are `Store Information`, `Featured Manchester Subdivision Real Estate Properties`, `Posted by ... October 2, 2013` and `source: easemytrip`, which are site-specific. The list needs more labels as more packs are read. A real section titled `Contents` or `Next` on its own line would lose that line.

## Medicine 2: C4 two documents joined

1. **Disease:** C4, 70 documents. Examples:
   - `a79b9132feb9c66f`: `WikipediaMining is one` (offset 49)
   - `b8e726ed25bf4dfa`: `Related articlesPerfect time management` (offset 11813)
   - `73a72cdf38011c79`: `Each week we send a customized newsletter` (offset 3630)
2. **Medicine:** there is no safe fix, because the join point does not show where one text ends. Texts joined with no break leave one visible trace: a word run straight into the next one (`WikipediaMining`). The rule drops a document with two or more such places.
```python
def c4(t):
    """Drop a document with two or more places where one text is glued to the next with no break ('fansApril', 'WikipediaMining')."""
    glued = re.findall(r"\b[a-z]{3,}[.!?)\"]?[A-Z][a-z]{2,}\b", t)
    return None if len(glued) >= 2 else t
```
3. **Action:** drop the document. Splitting it would need the seam position and a quality decision on each half.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents, Data A harm test) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 2 (`43c65ec608a359bf`, `008661b46ac2a3c5`) |

   Gold set: 34 documents, Data A build of 30 Oct; TSAI rule: pass if at most max(1 document, 1%) changes. Result: 0.00% changed, 0.00% dropped, PASS.

   The rule drops 11 of the 70 reviewed C4 documents.
5. **Side effects:** it misses most C4 documents, because many joins have a space or a line break at the seam. It drops a clean document that misses the space after a full stop twice (`video.With`).

## Medicine 3: C3 truncated document

1. **Disease:** C3, 78 documents. Examples:
   - `c5d61b53df104867`: ends `Example of operation [Read More >>>]` (offset 207)
   - `fb909c1fb77f3f90`: ends `She was actually one of my first...` (offset 136)
   - `87c9a4cea626e330`: ends `by using the following link:` (offset 977)
2. **Medicine:** drop a document whose last text ends in an ellipsis, `[...]` or `Read more`. These are the cuts that are safe to detect by code. An earlier rule dropped every document that does not end in `.`, `!` or `?`; it dropped 151 of 500 documents and failed. Adding a rule on the last word (`the`, `of`, `to`), or on a lowercase first letter, went over the 1% limit on the first 167 reviewed `clean` documents, so both were left out.
```python
def c3(t):
    """Drop a document whose last text is cut off: it ends in an ellipsis, '[...]' or 'Read more'."""
    e = t.rstrip()
    return None if re.search(r"(?:\.\.\.|\u2026|\[\u2026\]|\[\.\.\.\])\W*$|(?i:read more)\W*$", e) else t
```
3. **Action:** drop the document.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents, Data A harm test) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 1 (`d57d424ce49c5526`) |

   Gold set: 34 documents, Data A build of 30 Oct; TSAI rule: pass if at most max(1 document, 1%) changes. Result: 0.00% changed, 0.00% dropped, PASS.

   The rule drops 14 of the 78 reviewed C3 documents.
5. **Side effects:** it catches only 14 of 78. Cuts in the middle of a sentence (`...the remaining item`), cuts after a colon, and texts that start in the middle of a sentence stay in. A clean document that ends in `...` as a style choice is dropped.

## Medicine 4: C5 lists of keywords or links

1. **Disease:** C5, 60 documents. Examples:
   - `a79b9132feb9c66f`: `Comments About mining industry in sarawak` (offset 794)
   - `73a72cdf38011c79`: `transitional words comparing contrasting essay` (offset 1566)
   - `b8e726ed25bf4dfa`: `Animal abuse persuasive essay list thomas jefferson` (offset 12719)
2. **Medicine:** no safe fix. Reviewed C5 documents are search-snippet and essay-mill spam. The rule drops a document whose first line is a lowercase keyword string of four or more words, which is the typical title of that spam. With three words the rule dropped 3 of the 218 `clean` documents, which fails. Rules on repeated phrases and on the title repeated in the text were tested and flagged at least 9 reviewed `clean` documents, so they fail.
```python
def c5(t):
    """Drop a document whose first line is a lowercase keyword string of 4+ words ('mining industry in sarawak') - the title line of search-snippet spam."""
    first = next((l.strip() for l in t.split("\n") if l.strip()), "")
    return None if len(first.split()) >= 4 and first[0].islower() else t
```
3. **Action:** drop the document. Deleting the spam lines would leave almost nothing.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents, Data A harm test) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 1 |

   Gold set: 34 documents, Data A build of 30 Oct; TSAI rule: pass if at most max(1 document, 1%) changes. Result: 0.00% changed, 0.00% dropped, PASS.

   The rule drops 9 of the 60 reviewed C5 documents.
5. **Side effects:** it misses 51 of 60. A good document whose title starts in lowercase (`iPhone tips for beginners`) is dropped. C5 needs a model or a quality score, not a pattern.

## Medicine 5: D3 mixed language

1. **Disease:** D3, 6 documents. The guide says to label D3 and not to judge it, because mixing can be natural. Examples:
   - `29160f1b6b0823cf`: `行程速览` (offset 0), a Chinese tour-card header in front of English text
   - `3a8b5ee847c1afbc`: `продолжительность` (offset 4178), a Russian video line inside English text
   - `ae8a5a4fdf8d3351`: `коментариев` (offset 74), Russian comment counts inside English text
2. **Medicine:** do not fix real code-switching. The rule deletes only whole lines in which more than half of the letters are not Latin, in an English pack. A foreign word inside an English sentence stays.
```python
def d3(t):
    """Delete lines whose letters are mostly non-Latin (CJK, Cyrillic, Hangul, Devanagari ...) in an English document."""
    import unicodedata
    def foreign(l):
        letters = [c for c in l if c.isalpha()]
        return len(letters) >= 3 and sum(unicodedata.name(c, "").split(" ")[0] != "LATIN" for c in letters) / len(letters) > 0.5
    return "\n".join(l for l in t.split("\n") if not foreign(l))
```
3. **Action:** fix the text (delete the foreign lines); the document is kept.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents, Data A harm test) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 0 |

   Gold set: 34 documents, Data A build of 30 Oct; TSAI rule: pass if at most max(1 document, 1%) changes. Result: 0.00% changed, 0.00% dropped, PASS.

   The rule changes 2 of the 6 reviewed D3 documents.
5. **Side effects:** a quoted line in another language, or a bilingual example, is deleted from a good document. Mixed sentences such as `3da0a9bbeeac1a6a` (Spanish and English in one sentence) are not fixed; they need a human decision.

## Medicine 6: A1 invisible characters

1. **Disease:** A1, 14 documents (zero-width space, soft hyphen, byte-order mark, bidi marks, and stray ZWJ/ZWNJ).
2. **Medicine:** delete the invisible characters. A ZWJ or ZWNJ stays when an Indic letter is next to it, because there it is part of the script.
```python
def a1(t):
    """Delete ZWSP, BOM, soft hyphen and bidi marks; delete ZWJ/ZWNJ only when no Indic letter is next to them."""
    junk = {0x200B, 0xFEFF, 0x00AD, *range(0x202A, 0x202F), *range(0x2066, 0x206A)}
    t = "".join(c for c in t if ord(c) not in junk)
    indic = re.compile(r"[\u0900-\u0DFF]")
    return re.sub(r"[\u200c\u200d]", lambda m: m.group() if indic.search(t[max(0, m.start() - 2):m.end() + 2]) else "", t)
```
3. **Action:** fix the text (delete the characters); the document is kept.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents, Data A harm test) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 0 |

   Gold set: 34 documents, Data A build of 30 Oct; TSAI rule: pass if at most max(1 document, 1%) changes. Result: 0.00% changed, 0.00% dropped, PASS.

   The rule changes all 14 reviewed A1 documents.
5. **Side effects:** none seen. No-break spaces (U+00A0) are not touched; they are normal in English pages.

## Medicine 7: B4 template slots left in the text

1. **Disease:** B4, 11 documents. Examples:
   - `17f4af14c04c9fde`: `[email protected]` (offset 803), a mail address that the site hid with a script and that was never filled in
   - `ecc31924d4b6c2ea`: `{dialog-heading}` (offset 832), an empty template tag in a quiz page
   - `9b4fac814cddd37c`: `[/font][/color]` (offset 2896), forum markup tags that were not rendered
2. **Medicine:** delete the slot itself and keep the text around it. The rule removes `[email protected]`, `{{x}}`, `{% x %}`, `${x}`, `[object Object]`, single-brace slots with a hyphen or underscore (`{dialog-heading}`), BBCode tags (`[/font]`, `[color=red]`), and the backslash in `children\'s` or `\"sharing\"` when a letter is next to it. `[[i]]` footnote marks and a backslash next to a space (`"\" key` in code) are left alone.
```python
def b4(t):
    """Delete unrendered template slots and BBCode tags; unescape \\' and \\" next to a letter."""
    t = re.sub(r"\[email(?:&#160;|\s)protected\]|\{\{.{0,80}?\}\}|\{%.{0,80}?%\}|\$\{[^}\n]{0,80}\}|\[object Object\]|\{[a-z]+(?:[-_][a-z]+)+\}|(?<!\[)\[/?(?:font|color|size|b|i|u|url|quote|img)(?:=[^\]\n]{0,40})?\](?!\])", "", t)
    return re.sub(r"(?<=\w)\\(['\"])|\\(['\"])(?=\w)", lambda m: m.group(1) or m.group(2), t)
```
3. **Action:** fix the text (delete the slot); the document is kept.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 0 |

   The rule changes 7 of the 11 reviewed B4 documents, and no other document of the 500.
5. **Side effects:** it misses 4 of 11: an empty question in a generated FAQ, a name glued to a time stamp (`Timothy2024-05-02T11:40:52`), a doubled field (`Uses::`) and a `[[wmcoe]]` slot. Deleting `[[...]]` would also delete footnote marks (`[[i]]`) in a clean document, so that pattern is not in the rule. A text that talks about `[color]` tags would lose them.

## Medicine 8: D4 spun or machine-paraphrased text

1. **Disease:** D4, 14 documents, all dropped by me. Examples:
   - `3da0a9bbeeac1a6a`: `The social and economic desigualdades` (offset 0), Spanish words left in English text
   - `cbd26e20383c72b3`: `500g drains;` (offset 108), a recipe translated from Russian (`drains` for plums)
   - `9830fa89e63f1496`: `Lone wolf, Master, PhD` (offset 902), a paraphraser's output for `Bachelor, Master, PhD`
2. **Medicine:** there is no safe general rule. A paraphraser swaps single words (`financial obligation`, `dad and mom`, `understudies`) and every document has different swaps. Words that are common in these documents (`as well as`, `on the internet`, `certainly`) also occur in good ones: 20 of my 218 `clean` documents contain `as well as`. The rule below is a narrow list of six outputs that no natural English text I saw contains. It is a lookup, not a detector, and it is built from the 14 documents.
```python
def d4(t):
    """Drop a document that contains one of six paraphraser outputs seen in this pack."""
    return None if re.search(r"(?i)\b(?:dad and mom|understudies|screen centers|extra motionless|mutnates|legal rights unions)\b", t) else t
```
3. **Action:** drop the document. Deleting the bad words would leave a text that is still wrong.
4. **Harm test:**

   Harm result (gold set, 34 documents, Data A harm_test.py): changed 0 of 34, dropped 0 of 34, PASS

   | Test set | Documents changed | Documents dropped |
   |---|---|---|
   | Gold set (34 documents) | 0 of 34 | 0 of 34 |
   | Proxy: 218 reviewed `clean` documents | 0 | 0 |

   The rule drops 5 of the 14 reviewed D4 documents, and no other document of the 500.
5. **Side effects:** it misses 9 of 14 and will not generalise to new pack data. `understudies` is a normal word in theatre texts. D4 needs a language-model score, not a pattern; I do not claim this rule fixes D4.

## Other diseases (no medicine section)

| Code | Documents | Note |
|---|---|---|
| C2 | 22 | `c2` in `medicine.py` keeps the first copy of a line that occurs three or more times, but it changes 3 of the 218 `clean` documents (natural repeats), so it fails the 1% limit and is not proposed |
| F1 | 9 | only private persons count (28 Oct). `f1` in `medicine.py` changes 5 of 218 `clean` documents (business phone numbers), so it fails; a person-versus-business decision needs a human |
| A3 | 3 | can be re-decoded with `a3` in `medicine.py` |
| B1 | 3 | `b1` in `medicine.py` unescapes HTML entities |
| B5 | 2 | no automatic fix |
| B2, B3, F3 | 1 each | B3 documents are dropped; B2 and F3 need a human |
