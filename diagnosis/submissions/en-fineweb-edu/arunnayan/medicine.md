# Medicines — en-fineweb-edu (Arun Singh)

Pack: `en-fineweb-edu` · Reader: arunnayan · Domain: Data A (English)

Diagnosis counts (500 docs): C1 = 161, C3 = 27, C4 = 17, C5 = 12. Medicines below cover every disease found more than five times.

Each block defines `medicine(text) -> (new_text, "keep" | "fix" | "drop")`. `"keep"` means the text is unchanged. The harm test is the 294 documents this reader marked `clean` in `labels_en-fineweb-edu.csv`. A rule passes when it changes or drops at most 1% of them (at most 2 documents). All four pass at 0 of 294.

---

## Medicine 1: C1 boilerplate (DA-C1-001)

**Disease.** Website chrome pasted into the article: download links, "Updated N years ago", photo-credit brackets, "Explore further" / "Read more" / "Click here" lines, share and subscribe lines, keyword lines, and A–Z index lines. Count: 161.

Examples: `fac8900a570b630b`, `f63eec264ed25737`, `469e0a5a812c28f3`.

**Medicine.** Delete a line only when the whole line is one of those chrome patterns, then collapse the blank lines left behind. A line of article prose does not match. A line that is only `© ...` is left in place: `9114e814ed1018ef` is a clean article that ends with `© 2010 – Routledge`, and deleting every copyright line would change it.

**Action.** fix. If the document is empty after the deletion, drop.

**Harm test.** 0 of 294 clean documents changed. The rule edits 50 of the 161 C1 documents. PASS.

**Side effects.** Most C1 rows are a normal sentence used as a footer ("Find more…", "Call now" written as prose, a nav list that is not one of these line shapes). Those stay. A real sentence that is an entire line beginning "Read more" or "Click here to" would be removed; none of the clean documents are shaped that way.

```python medicine
import re

_BOILER = re.compile(
    r"^\s*(?:"
    r"\(c\)\s*copyright\b.*|"
    r"download\s*:.*|"
    r"updated\s+\d+\s+\w+\s+ago\b.*|"
    r"\[photo\s*:.*\]\s*|"
    r"explore further\s*:.*|"
    r"(?:read more|click here to|continue reading|click read more)\b.*|"
    r"(?:share (?:on|this)|advertisement|cookie policy|follow us)\b.*|"
    r"(?:executive editor|staff writer)\b.*|"
    r"\[(?:change|date prev)\b.*|"
    r"keywords?\s*:.*|"
    r"(?:[A-Za-z]\s+){20,}[A-Za-z]\s*$|"
    r"back to (?:top|know)\b.*|"
    r"you are here\b.*|"
    r"on this page\b.*|"
    r"comments powered by disqus\b.*|"
    r"please update your bookmarks\b.*|"
    r"this page is obsolete\b.*|"
    r"view larger map\s*$|"
    r"view all [\w ]{0,40}$|"
    r"home\s*:\s*travel\s*:.*|"
    r"follow [\w .]+ on twitter\s*$|"
    r"subscribe to (?:the|our)\b.*|"
    r"sign up (?:for|with|and)\b.*|"
    r"leave a comment\b.*|"
    r"add a definition\b.*|"
    r"0 items in your cart\b.*|"
    r"metadatashow full item record\s*$|"
    r"earn money today\b.*|"
    r"call now\b.*|"
    r"we've answered [\d,]+\s+questions\b.*|"
    r"please browse the following\b.*|"
    r"find more great\b.*|"
    r"check out (?:some|these)\b.*|"
    r"join to subscribe\b.*|"
    r"get [\w ]+ in your inbox\s*$|"
    r"image use disclaimer\b.*|"
    r"help support\b.*|"
    r"first published\b.*|"
    r"all rights reserved\.?\s*$|"
    r"\|\s*home\s*\|.*|"
    r"links?\s*:.*\|.*|"
    r"« back to gallery\s*$|"
    r"see all customer reviews\s*$|"
    r"most helpful customer reviews\s*$|"
    r"past news releases\b.*|"
    r"more photos in the news\s*$|"
    r"read the rest at\b.*|"
    r"read part one\b.*|"
    r"show summary details\s*$|"
    r"return to: list of papers\b.*"
    r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)

def medicine(text):
    new = _BOILER.sub("", text)
    if new == text:
        return text, "keep"
    new = re.sub(r"\n{3,}", "\n\n", new).strip()
    if not new:
        return "", "drop"
    return new, "fix"
```

---

## Medicine 2: C3 truncated document (DA-C3-001)

**Disease.** The scrape stops before the document is finished. The cases a rule can see are the ones that end unfinished: a colon (`Indian Edition also available on:`), a bare function word (`visit`, `they`, `the`), a cut token (`th.`, `(H.`), a unicode ellipsis, or a preview marker (`View Full Document`, `(The entire section is 1939 words.)`). Count: 27.

Examples: `3054e5cb9e7109dc`, `8620d74ba9ae6cdc`, `759f0ff501a81d56`.

**Medicine.** Drop the document only when the ending is one of those signals. Three dots (`...`) are not a signal: clean documents `ffa5766a9a53cd2c` and `b96825f5b5f4a491` end that way as a writing style.

**Action.** drop.

**Harm test.** 0 of 294 clean documents dropped. The rule drops 13 of the 27 C3 documents. PASS.

**Side effects.** A truncation in the middle of a document that still ends on a normal sentence is not dropped. That is most of the other 14 C3 rows. A title that truly ends on the word "the" or "they" would be dropped; no clean document ends that way.

```python medicine
import re

_BARE = re.compile(
    r"(?:^|[\s\"“])(?:the|a|an|and|or|but|of|to|for|with|was|were|is|are|from|that|they|visit|ranking)$",
    re.IGNORECASE,
)

def medicine(text):
    s = text.rstrip()
    if not s:
        return text, "keep"
    if s.endswith(":") or s.endswith("\u2026"):
        return text, "drop"
    if _BARE.search(s):
        return text, "drop"
    if re.search(r"\bth\.$", s) or re.search(r"\([A-Z]\.$", s):
        return text, "drop"
    if re.search(r"\(The entire section is \d+ words\.\)$", s):
        return text, "drop"
    if re.search(r"(?m)^View Full Document$", s):
        return text, "drop"
    if re.search(r", Professor$", s):
        return text, "drop"
    return text, "keep"
```

---

## Medicine 3: C4 two documents joined (DA-C4-001)

**Disease.** Two unrelated texts were pasted into one row: a second article after "Continue reading", a second encyclopedia with its own copyright line, or a second news story with its own dateline. Count: 17.

Examples: `3092ad2616653075`, `ce2fbf1d49241f8a`, `45504842dc4420c9`.

**Medicine.** The two halves cannot be split safely, so drop the row when a second document leaves a marker: a form-feed, a divider line of 10 or more `=`, `-`, `*`, or `_`, a second line that begins with `©`, the phrase "Continue reading" twice, or two datelines (`April 28, 2009` and `Tuesday, April 28, 2009`).

**Action.** drop.

**Harm test.** 0 of 294 clean documents dropped. The rule drops 3 of the 17 C4 documents (`3092ad2616653075`, `ce2fbf1d49241f8a`, `45504842dc4420c9`). PASS.

**Side effects.** Joins with no marker stay. That is the other 14 C4 rows (a second headline in the same column, dictionary entries, book-review excerpts). Dropping the marked rows loses the good half as well as the second document.

```python medicine
import re

_DIVIDER = re.compile(r"(?m)^\s*[=\-*_]{10,}\s*$")
_DATE = re.compile(
    r"(?m)^(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+)?"
    r"[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s*$"
)

def medicine(text):
    if "\x0c" in text:
        return text, "drop"
    if _DIVIDER.search(text):
        return text, "drop"
    if len(re.findall(r"(?m)^©", text)) >= 2:
        return text, "drop"
    if len(re.findall(r"(?i)continue reading\b", text)) >= 2:
        return text, "drop"
    if len(_DATE.findall(text)) >= 2:
        return text, "drop"
    return text, "keep"
```

---

## Medicine 4: C5 lists of keywords or links (DA-C5-001)

**Disease.** A keyword or tag line with no sentence: `Keywords: paiute | washoe | ...`, a `Links:` line of the same shape, or a comma cloud such as `bridges, canals, coal gas, coke, ...`. Count: 12. The other C5 rows are navigation catalogs (story titles, candidate lists). Those are not this rule.

Examples: `4604f40da35906cc`, `50400cf14b13cae5`, `baa5fe4efdc10714`.

**Medicine.** Remove a line that is a `Keywords:` or `Links:` line, or a comma cloud: 8 or more commas, no `.!?`, every item at most five words, and no finite verb (`is`, `are`, `was`, `said`, `can`, ...). Then collapse the blank lines. `baa5fe4efdc10714` is a catalog of story titles, not a keyword cloud, so this rule leaves it.

**Action.** fix. If the document is empty after the deletion, drop.

**Harm test.** 0 of 294 clean documents changed. The rule edits 2 of the 12 C5 documents (`4604f40da35906cc`, `50400cf14b13cae5`). PASS.

**Side effects.** A course table or an infobox (`|ECON 250||Principles of Macroeconomics||3|`) is real text and is not removed. A genuine sentence with many commas is not removed, because it has a verb or a full stop. Title catalogs stay.

```python medicine
import re

_VERB = re.compile(
    r"\b(?:is|are|was|were|has|have|had|said|says|can|will|would|should|could)\b",
    re.IGNORECASE,
)

def _cloud(s):
    if s.count(",") < 8 or re.search(r"[.!?]", s):
        return False
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) < 8:
        return False
    if any(len(p.split()) > 5 for p in parts):
        return False
    if any(_VERB.search(p) for p in parts):
        return False
    return True

def medicine(text):
    kept = []
    changed = False
    for ln in text.split("\n"):
        s = ln.strip()
        is_kw = bool(re.match(r"(?i)^(?:keywords?|links?)\s*:", s))
        if s and (is_kw or _cloud(s)):
            changed = True
            continue
        kept.append(ln)
    if not changed:
        return text, "keep"
    new = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    if not new:
        return "", "drop"
    return new, "fix"
```
