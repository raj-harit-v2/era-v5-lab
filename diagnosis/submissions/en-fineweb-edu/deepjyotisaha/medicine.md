# Medicine sheet: en-fineweb-edu (deepjyotisaha)

Written from all 500 documents of the pack. Every number below is produced by `medicine.py`, which runs each rule against the labels in `labels.csv` and against the whole pack. Diseases found more than five times (in more than five documents, or in more than five labelled cases): **C1** (277 documents, 592 cases), **C3** (13 documents, 14 cases), **B4** (8 documents, 16 cases), **F1** (8 documents, 13 cases), **D3** (5 documents, 26 cases), **C5** (4 documents, 6 cases), **C2** (2 documents, 8 cases).

## Medicine 1

1. **Disease:** C1 (boilerplate), count in the pack: 277 documents (592 labelled cases). Three examples: `74ea30694d60f739` "© 1995-2017 Bible History Online"; `f6393483c601faf0` "View all Kids Bikes"; `96dfcd8dcd7a0cff` "Back to top".

2. **Medicine:** Remove a line, or the end of a line, when it is website text rather than article text. Five kinds, each with its own pattern (all case-insensitive, lines under 120 characters unless stated):
   - teaser and action links: a line that starts with "Read more", "Continue reading", "Explore further", "Click here", "Learn more about", "To learn more about", "Find out more", "For further information", "View all", "View larger map", "Show summary details", "Share this", "Choose a citation style" or "Call now"; and a teaser such as "[...] Read more", "Continue reading →" or "Read more »" at the end of a longer line (only the teaser is removed);
   - bylines and dates: in the first three lines, a line that is "By <Name>", "From: …", "Posted …", "Updated …", "Published …", "Contributed by …", "Written by …", "Latest revision …" or only a date; anywhere, a line that is only "By <Name>";
   - credits, sources and footers: a line that starts with "©", "Copyright", "Source:", "Article source:", "Website:", "Courtesy:", "Photo:", "Image:", "Editor's note:", "Editor:" or "Correction";
   - navigation: a breadcrumb or menu line of four or more items joined by " | ", " : " or " » " (under 160 characters), and link boxes such as "|… »||… »|";
   - shop and promotion text (under 220 characters): book details ("Paperback:", "Publisher:", "ISBN-13:", "Product dimensions:"), order confirmations, "Help support … and get …", "Don't forget to check out …", "click on the … to follow me", "Subscribe to our newsletter".
   - line scorer: every line also gets a score from 0 to 1 from a logistic regression trained on the labels (positive: the labelled C1 lines; negative: every line of the documents labelled clean). Its features are what boilerplate lines share whatever their words: length, a full stop at the end, position (first or last three lines), link words, web address, ©, date, separators, share of capitalised words, digits, whether a paragraph follows, and how many other documents repeat the line. A line scoring 0.95 or more is removed, but only if it is at most 200 characters and carries an explicit boilerplate signal (link word, web address, ©, date, byline or separator; from 27 Oct also a line found in 3 or more documents of the pack, and "Back to …", "Photo credit", "Contributors:", "Last reviewed", "Article ID:", "community guidelines", "customer reviews"), so an article title or an ordinary sentence is never removed on its score alone. A lower threshold for the first and last three lines was tested on 27 Oct and rejected: it changed more clean documents (a dateline, a closing reference);
   - prose guard (4 Nov): a line of 8 or more words, at least 60% of them starting lower case, is a sentence, and the scorer may not remove it unless it has a web address, © or a byline; a date or a link word ("share", "order") is not enough. Added after the scorer removed two real sentences from the gold set on documents it had not seen;
   - block expansion: a line next to a removed line is removed too if it is short, has no full stop, scores at least half the threshold, and is signalled or a "Key: value" line (the rest of a byline or of a book-details block);
   - a teaser glued to the end of a sentence ("…can be prescribed.Learn more about …") removes only the teaser, never the sentence;
   - guard: if all of this would remove more than 20% of a document and more than 300 characters, nothing is cut and the document is flagged for drop (so a normal footer on a short page is cut, not turned into a drop). The threshold 0.95 is the one that catches the most labelled lines while changing at most 1% of the clean documents and at most the gold limit of the gold-set documents (max(1, 1% of the gold set), the Data A harm test's limit), in a five-fold test on documents the scorer did not see during training (`c1tune.py`).

   In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
def c1_spans(text, repetition=None):
    """The C1 medicine. Returns (spans to remove, flagged_for_drop)."""
    rep = repetition or {}
    phrase = c1_phrase_spans(text)
    phrase_hits = {s for s, _, _ in phrase}
    lines, X = line_features(text, repetition)
    scores = [line_score(x) for x in X]
    inline = {k for k, (o, s) in enumerate(lines)
              if any(o <= a < o + len(s) for a, _, r in phrase if r == "C1-teaser-inline")}
    remove = {k for k, (off, s) in enumerate(lines) if off in phrase_hits}
    remove |= {k for k, sc in enumerate(scores)
               if sc >= THRESHOLD and len(lines[k][1]) <= MAX_LINE and _signal(lines[k][1], rep) and k not in inline}
    changed = True
    while changed:                          # block expansion
        changed = False
        for k in sorted(remove):
            for j in (k - 1, k + 1):
                if 0 <= j < len(lines) and j not in remove and j not in inline and len(lines[j][1]) <= 120 \
                        and lines[j][1][-1] not in END_PUNCT and scores[j] >= EXPAND_FACTOR * THRESHOLD \
                        and (_signal(lines[j][1], rep) or KEY_VALUE.match(lines[j][1])):
                    remove.add(j)
                    changed = True
    spans = [(lines[k][0], lines[k][0] + len(lines[k][1]), "C1-phrase" if lines[k][0] in phrase_hits else
              "C1-scorer") for k in sorted(remove)]
    spans += [sp for sp in phrase if sp[2] == "C1-teaser-inline"]
    removed = len({p for s, e, _ in spans for p in range(s, e)})
    if text and removed > MAX_SHARE * len(text) and removed > MIN_DROP_CHARS:
        return [], True                      # too much would go: drop the document instead
    return spans, False
```

3. **Action:** fix. The matched text is removed; the rest of the document is kept. A document the guard flags is dropped.

4. **Harm test:** changes 0 of 158 gold documents, drops 0 of 158 gold documents (0.00% changed or dropped): **pass** against the 1% bar. Gold set: `teams/01-data-a/gold/en-fineweb-edu_gold.csv` from the Data A team (G1, pull request 140, commit c3cb003): 158 documents of this pack that two readers each read in full and marked clean. With a scorer that had not seen the document (the five-fold test), C1 changes 0 of 158 gold documents (0.00%). Before the prose guard (4 Nov) this was 2 of 158 (1.27%): two real sentences, one with a date and one with the word "share", were removed. Also on the 202 rows of `labels.csv` with verdict `clean` (each tested by a scorer that had not seen it): changes 2, drops 0 (0.99%). On the whole pack it changes 154 of 500 documents and removes 15,430 of 2,442,877 characters (0.63%).

5. **Side effects:** on documents the scorer had not seen, the medicine finds 227 of the 540 labelled C1 lines (42%; the phrase rules alone find 117). It misses C1 that has no fixed wording and no boilerplate signal: one-off site headings ("Programs for children", "Chapter 02 Worksheet"), reference lists and citations, catalogue records and promotion inside a long paragraph. These are left to the readers. Article titles are kept on purpose: the first version of the scorer removed titles and sentences such as "By the end of 1992, …" from clean documents, which is why the scorer may only remove signalled lines. Remaining risks: a "Source:" line under a chart, and a short line with a date or a link word that belongs to the article.

## Medicine 2

1. **Disease:** C3 (truncated document), count in the pack: 13 documents (14 labelled cases). Three examples: `2067313a5e000336` "He writes in the Guardian on Tuesday:"; `8620d74ba9ae6cdc` "For more information about the collection, visit"; `d9cf118c7cae38e0` "week we celebrate the holiday of Chanuka.".

2. **Medicine:** Remove the last line of a document when it is an unfinished sentence: the last non-empty line has at least six words and ends on a word no complete sentence ends on (for example "the", "of", "to", "visit", "they") or on ":" or ",", and the C1 medicine does not already remove it. The document then ends at its last complete line. Run after the C1 medicine. Two broader rules were tested and rejected (25 Oct): "the last line ends with any lower-case letter" also removed titles and author notes at the end of good documents, and "the text starts with a lower-case letter" also removed dictionary entries that start in lower case. Those cases stay with the readers.

   In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
def c3_spans(text, repetition=None):
    """The C3 medicine: remove the last line when it is an unfinished sentence and C1 does not remove it."""
    lines = [(o, l) for o, l in _raw_lines(text) if l.strip()]
    if not lines:
        return []
    off, last = lines[-1]
    c1, flagged = c1_spans(text, repetition)
    if flagged:
        c1 = [(0, len(text), "C1-drop-flag")]
    if any(s < off + len(last) and e > off for s, e, _ in c1):
        return []
    s = last.rstrip()
    words = s.split()
    if len(words) >= 6 and (s[-1] in ":," or words[-1].lower() in DANGLING):
        return [(off, off + len(last), "C3-unfinished-end")]
    return []
```

3. **Action:** fix. The matched text is removed; the rest of the document is kept.

4. **Harm test:** changes 0 of 158 gold documents, drops 0 of 158 gold documents (0.00% changed or dropped): **pass** against the 1% bar. Gold set: `teams/01-data-a/gold/en-fineweb-edu_gold.csv` from the Data A team (G1, pull request 140, commit c3cb003): 158 documents of this pack that two readers each read in full and marked clean. Also on the 202 rows of `labels.csv` with verdict `clean`: changes 0, drops 0 (0.00%). On the whole pack it changes 4 of 500 documents and removes 346 of 2,442,877 characters (0.01%).

5. **Side effects:** the medicine finds 2 of the 14 labelled cases. It misses cut-offs that do not end on a dangling word or a colon (for example a teaser ending in "..."), and documents that start in the middle of a sentence. Some labelled cut-offs are removed by the C1 medicine first, because their last line is also a link ("…For more information about the collection, visit"). On the whole pack it changes 4 documents; checked on 25 Oct, one of them is a title ending in "On" ("The Saga Lives On"), which is a wrong removal.

## Medicine 3

1. **Disease:** B4 (template and code junk), count in the pack: 8 documents (16 labelled cases). Three examples: `3e44df6a7ddb0098` "`page.data.shortTitle || page.data.title`"; `4af5022aceeaf8b2` "require 'nokogiri' require 'open-uri' # Get a Nokogiri::HTML:Document for the page"; `ef54fd4d35956893` "> take :: Integer -> [Integer] -> [Integer] take _  =  take n xs".

2. **Medicine:** Two parts.
   - template junk (fix): remove what a web page left unfilled: "{{ title }}", "{% if … %}", "${name}", a code expression in backticks such as "`page.data.shortTitle || page.data.title`", "NaN" or "undefined" right after ":", "=" or "$", and a line that is only "undefined", "NaN" or "null";
   - mostly code (drop): a line is a code line when it has at least two code tokens ("::", "->", "==", "&&", "{", "}", a line ending in ";", a line starting with "import", "def", "return", "public", "$ ", "Sub", …) and at least one for every six words; a table row "|cell||cell|" is never a code line. A document whose code lines hold more than half of its characters is dropped;
   - code snippets inside an article are kept on purpose (decided 27 Oct): tutorials and manual pages with a few lines of code are good training text, and cutting them risks removing real content.

   In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
def b4_spans(text):
    """B4: the document is dropped if it is mostly code; otherwise template expressions are removed."""
    code = sum(e - s for s, e in b4_code_lines(text))
    if text.strip() and code > B4_SHARE * len(text.strip()):
        return [(0, len(text), "B4-mostly-code")]
    return [(m.start(), m.end(), "B4-template") for m in B4_TEMPLATE.finditer(text)]
```

3. **Action:** fix for template junk (the expression is removed); drop for a document that is mostly code.

4. **Harm test:** changes 0 of 158 gold documents, drops 0 of 158 gold documents (0.00% changed or dropped): **pass** against the 1% bar. Gold set: `teams/01-data-a/gold/en-fineweb-edu_gold.csv` from the Data A team (G1, pull request 140, commit c3cb003): 158 documents of this pack that two readers each read in full and marked clean. Also on the 202 rows of `labels.csv` with verdict `clean`: changes 0, drops 0 (0.00%). On the whole pack it changes 1 of 500 documents and removes 41 of 2,442,877 characters (0.00%).

5. **Side effects:** the medicine finds 1 of the 16 labelled cases. On the whole pack it changes 1 document. The mostly-code part drops no document of this pack: the most code-like one (document 10) has code in only 3% of its text. The other B4 documents are articles with a code snippet (a Visual Basic or Java listing, a Ruby example, a command manual page, a Haskell mailing-list post), kept on purpose; the readers' labels remain the record of them. Code flattened into a prose line by the original crawl is hard to tell from prose with symbols, which is why the drop needs more than half of the document to be code.

## Medicine 4

1. **Disease:** F1 (personal data), count in the pack: 8 documents (13 labelled cases). Three examples: `841da1d7e68b3ab8` "phone number at offset 1597"; `6a515f44bd213b3d` "phone number after a Tel: label at offset 7182"; `e202cef6da70c403` "phone number after a Tel: label at offset 3943".

2. **Medicine:** Remove every email address, phone number and ID number, together with a label in front of it ("Tel:", "Fax:", "Phone:"). Nothing is put in its place: a placeholder such as "[phone]" would teach the model to write our own made-up token (decided 27 Oct). The patterns are the scanner's F1 patterns:
   - emails, except FineWeb's own example.com replacements;
   - phone numbers: international ("+44 …"), US (three digits in brackets or with a dash, then three and four digits), UK and Indian numbers that start with 0, and any number after a Tel, Fax, Phone or Mobile label;
   - ID numbers: US social security numbers, PAN numbers, and card and Aadhaar numbers only when their check digit is valid (the Luhn test for cards, the Verhoeff test for Aadhaar), so a run of years or a product code is not taken for one;
   - not personal data: a match inside a journal reference, an ISBN, a DOI or a run of years is left alone;
   - a line with no letter or digit left after the removal ("Tel: … / Fax: …") is removed whole.

   In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
def f1_spans(text):
    """F1: every email, phone number or ID number, removed with its label. A line left with no letter or digit
    after the removal ("Tel: … / Fax: …") is removed whole."""
    not_personal = [m.span() for rx in F1_NOT for m in rx.finditer(text)]
    spans = []
    for kind, rx, check in F1_PATTERNS:
        for m in rx.finditer(text):
            s, e = m.span()
            if kind == "email":
                if m.group(0).lower().endswith(F1_EMAIL_SKIP):
                    continue
            elif any(s < b and a < e for a, b in not_personal):
                continue
            digits = re.sub(r"\D", "", m.group(0))
            if check == "luhn" and not _luhn(digits) or check == "verhoeff" and not _verhoeff(digits):
                continue
            spans.append((s, e, "F1-" + kind))
    spans = _merge(spans)
    out = []
    for s, e, rule in spans:
        ls = text.rfind("\n", 0, s) + 1
        le = text.find("\n", e)
        le = len(text) if le < 0 else le
        rest = text[ls:s] + text[e:le]
        for s2, e2, _ in spans:  # other values on the same line go too
            if ls <= s2 and e2 <= le and (s2, e2) != (s, e):
                rest = rest.replace(text[s2:e2], "")
        out.append((ls, le, rule) if not re.search(r"[^\W_]", rest) else (s, e, rule))
    return _merge(out)
```

3. **Action:** fix. The matched text is removed; the rest of the document is kept.

4. **Harm test:** changes 0 of 158 gold documents, drops 0 of 158 gold documents (0.00% changed or dropped): **pass** against the 1% bar. Gold set: `teams/01-data-a/gold/en-fineweb-edu_gold.csv` from the Data A team (G1, pull request 140, commit c3cb003): 158 documents of this pack that two readers each read in full and marked clean. Also on the 202 rows of `labels.csv` with verdict `clean`: changes 0, drops 0 (0.00%). On the whole pack it changes 8 of 500 documents and removes 200 of 2,442,877 characters (0.01%).

5. **Side effects:** the medicine finds 13 of the 13 labelled cases. On the whole pack it changes 8 documents, all of them labelled F1. It misses personal data with no fixed shape: names, home addresses, and numbers written in words or grouped in an unusual way. Every phone number counts, also an organisation's (decided 24 Oct). After the removal a sentence such as "call … for details" can read oddly.

## Medicine 5

1. **Disease:** D3 (mixed language), count in the pack: 5 documents (26 labelled cases). Three examples: `f9c53a41965da2a5` "Да ти се чува името само за добро"; `c7a02c529ace1f12` "ἄνθρωπος :: ἄνθρωποι, πρῶτος :: πρῶτοι"; `5d83a600900ceb99` "Дерево, как летопись засух".

2. **Medicine:** Nothing is removed. DISEASES.md says mixed language can be natural and is to be labelled, not judged, and every labelled case in this pack is on purpose (proverbs with their translation, Greek grammar, a Russian book title, Indonesian course slides, Chinese calendar names in an infobox). The medicine only flags passages for a reader:
   - a run of at least three words in one alphabet other than Latin (Cyrillic, Greek, Arabic, Devanagari, …);
   - for alphabets written without spaces (Chinese, Japanese, Thai), a run of at least four characters;
   - a word that mixes alphabets ("α-helix") is not flagged: that is A6, not D3.

   In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
def d3_flags(text):
    """(start, end, script) of every run of words in one alphabet other than Latin."""
    flags, run = [], []
    for m in re.finditer(r"\S+", text):
        sc = _word_script(m.group(0))
        if run and sc != run[0][2]:
            flags += _close(run)
            run = []
        if sc and sc != "LATIN":
            run.append((m.start(), m.end(), sc))
    return flags + _close(run)
```

3. **Action:** fix, with an empty fix: no text is changed and no document is dropped, because DISEASES.md says mixed language can be natural and is to be labelled, not judged. `d3_flags` only lists the passages for a reader.

4. **Harm test:** changes 0 of 158 gold documents, drops 0 of 158 gold documents (0.00% changed or dropped): **pass** against the 1% bar. Gold set: `teams/01-data-a/gold/en-fineweb-edu_gold.csv` from the Data A team (G1, pull request 140, commit c3cb003): 158 documents of this pack that two readers each read in full and marked clean. Also on the 202 rows of `labels.csv` with verdict `clean`: changes 0, drops 0 (0.00%). On the whole pack it changes 0 of 500 documents and removes 0 of 2,442,877 characters (0.00%).

5. **Side effects:** the medicine flags 25 of the 26 labelled cases. It cannot see mixed language in the Latin alphabet (the Indonesian case), which only reading finds. Removing nothing is deliberate: every labelled case is part of its article. It also flags document 356, which is not labelled D3 (in document 356 the flag is invisible Hangul filler characters, A1 junk, not language).

## Medicine 6

1. **Disease:** C5 (lists of keywords or links), count in the pack: 4 documents (6 labelled cases). Three examples: `3f4857110e68e166` "pitman shorthand grammalogues"; `baa5fe4efdc10714` "The Little Robber Girl"; `7f983f58c670ca42` "ED 250351.".

2. **Medicine:** Two parts.
   - list page (drop): more than half of the non-empty lines have 3 words or fewer, and there are at least 10 such lines: a list of titles, tags or links, not prose;
   - keyword tail (fix): at least 4 lines at the end of the document, each of 2 to 5 words, all lower case, without punctuation (search keywords appended to a page, such as "pitman shorthand grammalogues"), are removed.

   In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
def c5_spans(text):
    """C5: the whole document (drop) when it is mostly very short lines; else a lower-case keyword tail (fix)."""
    raw, pos = [], 0
    for line in text.split("\n"):
        if line.strip():
            raw.append((pos, line))
        pos += len(line) + 1
    short = sum(1 for _, l in raw if len(l.split()) <= C5_SHORT_WORDS)
    if raw and short >= C5_SHORT_MIN and short > C5_SHORT_SHARE * len(raw):
        return [(0, len(text), "C5-list-page")]
    tail = []
    for off, line in reversed(raw):
        s = line.strip()
        if 2 <= len(s.split()) <= 5 and _C5_KEYWORD.match(s):
            tail.append((off, off + len(line), "C5-keyword-tail"))
        else:
            break
    return tail[::-1] if len(tail) >= C5_TAIL_LINES else []
```

3. **Action:** drop for a list page (the whole document); fix for a keyword tail (the tail is removed).

4. **Harm test:** changes 0 of 158 gold documents, drops 0 of 158 gold documents (0.00% changed or dropped): **pass** against the 1% bar. Gold set: `teams/01-data-a/gold/en-fineweb-edu_gold.csv` from the Data A team (G1, pull request 140, commit c3cb003): 158 documents of this pack that two readers each read in full and marked clean. Also on the 202 rows of `labels.csv` with verdict `clean`: changes 0, drops 0 (0.00%). On the whole pack it changes 2 of 500 documents and removes 2,726 of 2,442,877 characters (0.11%).

5. **Side effects:** the medicine finds 4 of the 6 labelled cases. On the whole pack it changes 2 documents, all of them labelled C5. It misses list pages whose lines are long (a list of journal references, a list of story titles with more than three words), which the readers labelled and dropped.

## Medicine 7

1. **Disease:** C2 (repeated lines), count in the pack: 2 documents (8 labelled cases). Examples (only 2 documents have C2): `b888d78a21618c96` "Children & parents"; `ec2b61417f2900c8` "family, an enveloped RNA virus family, and, more particularly".

2. **Medicine:** Remove the later copies of a line that appears 3 or more times in the same document (lines of at least 10 characters, compared without extra spaces); the first copy is kept. Shorter lines ("*", "Answer") are left alone.

   In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
def c2_spans(text):
    """C2: later copies of a line repeated C2_MIN_REPEAT or more times in the document."""
    seen, lines, pos = {}, [], 0
    for line in text.split("\n"):
        key = " ".join(line.split())
        if len(key) >= C2_MIN_CHARS:
            lines.append((pos, pos + len(line), key))
            seen[key] = seen.get(key, 0) + 1
        pos += len(line) + 1
    out, first = [], set()
    for s, e, key in lines:
        if seen[key] >= C2_MIN_REPEAT:
            if key in first:
                out.append((s, e, "C2-repeated-line"))
            first.add(key)
    return out
```

3. **Action:** fix. The matched text is removed; the rest of the document is kept.

4. **Harm test:** changes 0 of 158 gold documents, drops 0 of 158 gold documents (0.00% changed or dropped): **pass** against the 1% bar. Gold set: `teams/01-data-a/gold/en-fineweb-edu_gold.csv` from the Data A team (G1, pull request 140, commit c3cb003): 158 documents of this pack that two readers each read in full and marked clean. Also on the 202 rows of `labels.csv` with verdict `clean`: changes 0, drops 0 (0.00%). On the whole pack it changes 4 of 500 documents and removes 298 of 2,442,877 characters (0.01%).

5. **Side effects:** the medicine finds 6 of the 8 labelled cases. On the whole pack it changes 4 documents: besides the labelled repeats it removes repeated section headings that were labelled C1 and repeated table headers, which belong to their tables. It misses a passage printed twice when the copies are not identical line by line (document 53).

---

The appendices below support the medicines above; they are not medicines themselves.

### Appendix A: test on unseen documents

On 2026-10-25, before documents 151–500 were labelled, the medicines' predictions for them were saved (`frozen_predictions.json`; C1 scorer trained on the first 150 documents, threshold 0.97). Comparing them with the labels made afterwards (`frozen_test.py`):

- **C1 caught:** 174 of 454 labelled C1 lines (38.3%).
- **C1 precision:** 169 of the 178 lines it removed were labelled C1 (94.9%).
- **Clean documents changed:** 1 of 143 (0.7%): documents 457.
- **C3:** found in 0 of the 7 documents labelled C3.
- **Blind documents** (every 10th, labelled without seeing any suggestion; the fully independent test): 17 of 47 C1 lines caught (36.2%), 17 of 20 removed lines labelled C1 (85.0%), 0 of 17 clean documents changed.

In the other documents the reader saw the predictions as suggestions while labelling, so agreement there is partly their influence. The medicine above was retrained on all labelled documents after this test.

### Appendix B: runnable code

All the medicines in one self-contained Python file: copy it into `medicine_standalone.py` and it runs with the standard library alone (no numpy, no other files). It is generated from the code and the trained weights that were tested above, and it gives the same result as that code on all 500 documents of the pack (0 differences, checked by `standalone.py`), when it is given the pack's line-repetition counts (below). Without them, C1 gives a different result on 3 of the 500 documents, because it cannot tell which lines repeat across the pack.

How to use it:

```python
from medicine_standalone import clean, c1_spans, c3_spans, f1_spans, b4_spans, c2_spans, c5_spans, d3_flags, _norm

# how many documents of the pack contain each line (the scorer and the gate use it)
repetition = {}
for doc in texts:
    for line in {_norm(l) for l in doc.split("\n") if l.strip()}:
        repetition[line] = repetition.get(line, 0) + 1

cleaned, action = clean(text, repetition)   # action: "keep", "fix" or "drop"
spans, flagged = c1_spans(text, repetition) # what C1 removes: (start, end, rule); flagged = drop
c3 = c3_spans(text, repetition)             # what C3 removes
f1, b4 = f1_spans(text), b4_spans(text)     # what F1 and B4 remove
c2, c5 = c2_spans(text), c5_spans(text)     # what C2 and C5 remove (C5-list-page = drop)
flags = d3_flags(text)                      # D3: passages in another alphabet (nothing removed)
```

To score a single line: `lines, X = line_features(text, repetition)` gives every line with its 20 features, and `line_score(x)` gives its score from 0 to 1. A line is removed by the scorer only if the score is at least `THRESHOLD`, the line has at most 200 characters and `_signal(line, repetition)` is true.

```python
"""The medicines for en-fineweb-edu: C1 (boilerplate), C3 (truncated document), F1 (personal data), B4
(template and code junk), C2 (repeated lines), C5 (lists of keywords or links) and D3 (mixed language: flags
only). Self-contained: needs only the Python standard library. Usage: cleaned_text, action = clean(text)
"""
import math
import re
import unicodedata

# ----- C1 phrase rules -----
SHORT = 120
START_LINES = 3
C1_RULES = {
    'C1-teaser-line': (re.compile('(?i)^\\W{0,6}(?:read more|continue reading|explore further|click here|learn more about|to learn more about|find out more|for further information|view all\\b|view larger map|show summary details|share this|choose a citation style|call now)'), 'anywhere'),
    'C1-teaser-inline': (re.compile('(?i)(?:\\[\\.\\.\\.\\]\\s*read more\\.?|\\s+continue reading\\s*→?|\\s*\\bread more\\s*»?|(?<=[.!?])\\s*learn more about [^.!?]{0,60})\\s*$'), 'inline'),
    'C1-byline-alone': (re.compile("^[Bb]y\\s+[A-Z][\\w.'-]+(?:\\s+[A-Z][\\w.'-]+){0,3}$"), 'anywhere'),
    'C1-byline': (re.compile("(?i)^(?:by\\s+[A-Z][\\w.'-]+(?:\\s+[A-Z][\\w.'-]+){0,3}\\b.*|from:\\s.*|posted:?\\s.*|updated\\s.*|published\\s.*|contributed by\\s.*|written by\\s.*|latest revision\\s.*|(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\\s+)?(?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},?\\s+\\d{4}|\\d{1,2}\\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{4})\\.?)$"), 'start'),
    'C1-credit': (re.compile("(?i)^\\W{0,3}(?:©|copyright\\b|\\(c\\)\\s*\\d{4}|source:|article source:|website:|courtesy:|photo:|image:|editor'?s note:|editor:|correction|published\\s+\\d{1,2}\\s)"), 'anywhere'),
    'C1-navigation': (re.compile('^(?=.{0,160}$)(?:[^|:»\\n]+\\s(?:\\||:|»)\\s){3,}[^|:»\\n]+$|^.*»\\s*\\|\\|.*»\\s*\\|?$'), 'anywhere'),
    'C1-promotion': (re.compile("(?i)^\\W{0,3}(?:paperback:|hardcover:|publisher:|language:\\s*\\w+$|isbn-1[03]:|product dimensions:|indian edition also available|we've sent an email with your order|help support .{0,40} and get|don't forget to check out|click on the .{0,30} to follow me|subscribe to (?:our|the) newsletter)"), 'anywhere'),
}

# ----- C1 line scorer: feature patterns -----
LINK_WORDS = re.compile('(?i)\\b(?:read more|click|view (?:all|full|larger|more|current|details|profile|cart)|share|follow|subscribe|sign up|log ?in|register|download|visit|learn more|find out|contact|call now|order|buy|shop|newsletter|comment|rate|advertis|explore further|continue reading|related|see also|tags?)\\b')
URL = re.compile('(?i)https?://|www\\.|\\.(?:com|org|net|edu|gov|co\\.uk)\\b')
COPY = re.compile('(?i)©|\\bcopyright\\b|all rights reserved')
DATE = re.compile('(?i)\\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\\.?\\s+\\d{1,2},?\\s+\\d{4}\\b|\\b\\d{1,2}\\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\\s+\\d{4}\\b|\\b(?:19|20)\\d{2}\\b')
SEPARATORS = re.compile('\\s\\|\\s|\\|\\||»|\\s:\\s|\\s/\\s')
BYLINE = re.compile("^(?:[Bb]y\\s+[A-Z][\\w.'-]+(?:\\s+[A-Z][\\w.'-]+)*(?:,|$)|(?i:from|posted|updated|published|written by|contributed by|photo|image|source|courtesy)\\s*:|(?i:posted|updated|published)\\s+(?:on\\s+)?\\d)")
KEY_VALUE = re.compile('^[-•*]?\\s*[A-Z][\\w -]{1,25}:\\s+\\S')
FULL_DATE = re.compile('(?i)\\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\\.?\\s+\\d{1,2},?\\s+\\d{4}\\b|\\b\\d{1,2}\\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\\s+\\d{4}\\b|\\b\\d{1,2}/\\d{1,2}/\\d{2,4}\\b')
MENU_SEP = re.compile('[A-Za-z]\\s(?:\\||»|:)\\s[A-Za-z]|»')
GATE_WORDS = re.compile('(?i)^back to\\b|\\bphoto credit|^contributors?:|^last (?:reviewed|updated)\\b|^article id:|community guidelines|customer reviews')
GATE_REPEAT = 3
WORD_TOKEN = re.compile("[A-Za-z][A-Za-z'’-]*")
PROSE_WORDS = 8
PROSE_LOWER = 0.6
END_PUNCT = '!").?’”'

# ----- C1 line scorer: trained weights (c1tune.py, 25 Oct) -----
THRESHOLD = 0.95
B = -1.5507480049898266
# (weight, mean, standard deviation) for each feature, in the order of FEATURES
FEATURES = ['short_60', 'short_120', 'log_length', 'ends_sentence', 'first_3', 'last_3', 'rel_position', 'link_words', 'url', 'copyright', 'date', 'separators', 'capitalised', 'bullet', 'byline_start', 'repeated_docs', 'digits', 'few_words', 'next_is_paragraph', 'prev_is_paragraph']
WEIGHTS = [
    (-0.30147706176797767, 0.34978991596638653, 0.4769034824871978),  # short_60
    (0.06330518850698173, 0.5189075630252101, 0.4996423771656242),  # short_120
    (-1.0656012937788908, 4.7404142964275575, 1.1558346577519014),  # log_length
    (-0.3355137904314126, 0.6646533613445378, 0.4721115032936311),  # ends_sentence
    (0.6530189039369719, 0.1951155462184874, 0.39628962973426646),  # first_3
    (0.7681479054606566, 0.22163865546218486, 0.4153492057267116),  # last_3
    (0.20484508311329477, 0.5134065615572345, 0.326095004751047),  # rel_position
    (0.6020056915946318, 0.08403361344537816, 0.34111980628726096),  # link_words
    (0.34674133673120544, 0.01365546218487395, 0.11605598118797099),  # url
    (0.21358949882641426, 0.010766806722689076, 0.103203114304226),  # copyright
    (0.39027972267177646, 0.09243697478991597, 0.2896418151111693),  # date
    (1.1117791213605204, 0.03571428571428571, 0.3472365619951357),  # separators
    (0.8316447868841712, 0.22243452191582483, 0.2374418810653674),  # capitalised
    (-0.26558805523900925, 0.22006302521008403, 0.4142888979613596),  # bullet
    (0.6554049595691624, 0.011029411764705883, 0.10444024152457473),  # byline_start
    (0.2809341884722034, 0.004732622556344163, 0.07264101150947193),  # repeated_docs
    (0.5335299651420944, 0.014400859555666128, 0.04813878573134519),  # digits
    (-0.1330440782326233, 0.07589285714285714, 0.26482660724934853),  # few_words
    (-0.5184152439383056, 0.3434873949579832, 0.47487240961410254),  # next_is_paragraph
    (0.004603588072813513, 0.3542542016806723, 0.4782866956427239),  # prev_is_paragraph
]
MAX_LINE = 200
MAX_SHARE = 0.2
MIN_DROP_CHARS = 300
EXPAND_FACTOR = 0.5

# ----- C3 -----
DANGLING = ['a', 'about', 'an', 'and', 'are', 'as', 'at', 'be', 'because', 'been', 'but', 'by', 'can', 'could', 'for', 'from', 'had', 'has', 'have', 'he', 'her', 'his', 'i', 'if', 'in', 'including', 'into', 'is', 'it', 'its', 'more', 'most', 'not', 'of', 'on', 'or', 'our', 'see', 'she', 'such', 'than', 'that', 'the', 'their', 'these', 'they', 'this', 'those', 'to', 'very', 'visit', 'was', 'we', 'were', 'when', 'which', 'while', 'who', 'whose', 'will', 'with', 'would', 'you', 'your']


# ----- F1 personal data -----------------------------------------------------------------------------------
# The scanner's F1 patterns (dictionaries.py, 24 Oct). (kind, pattern, check): check is the check-digit test an ID
# number must pass. A labelled number (a "Tel:" label and its digits) is removed together with its label.
F1_PATTERNS = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"), None),
    ("labelled-number", re.compile(r"(?i)\b(?:tel|telephone|phone|fax|mobile|mob|cell)\b\.?\s*(?:no\.?\s*)?:?\s*"
                                   r"[+(]?\d[\d ().-]{5,}\d"), None),
    ("phone", re.compile(r"\+\d[\d\s().-]{7,18}\d"), None),
    ("phone", re.compile(r"\(\d{3}\)\s?\d{3}[-.\s]\d{4}\b"), None),
    ("phone", re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"), None),
    ("phone", re.compile(r"\b0\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b"), None),
    ("us-ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), None),
    ("card", re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), "luhn"),
    ("aadhaar", re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"), "verhoeff"),
    ("pan", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), None),
]
F1_EMAIL_SKIP = ("example.com", "example.org", "example.net")  # FineWeb's own replacements, not personal data
# A match that overlaps one of these is not personal data: journal reference, ISBN, DOI, run of years
F1_NOT = [
    re.compile(r"\d+\s*\(\d+\)\s*:\s*\d+\s*[-–]\s*\d+"),
    re.compile(r"(?i)\bISBN(?:-1[03])?:?\s*[\dXx-]{10,17}|\b97[89]-\d{1,5}-\d{1,7}-\d{1,7}-[\dXx]\b"),
    re.compile(r"\b10\.\d{4,9}/\S+"),
    re.compile(r"\b(?:1[89]|20)\d{2}(?:\s+(?:1[89]|20)\d{2}){2,}\b"),
]

_VERHOEFF_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
               [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
               [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
               [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_VERHOEFF_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
               [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
               [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def _luhn(digits):
    """The check-digit test of payment card numbers."""
    total = 0
    for k, ch in enumerate(reversed(digits)):
        d = int(ch)
        if k % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def _verhoeff(digits):
    """The check-digit test of Aadhaar numbers (the first digit is never 0 or 1)."""
    if digits[:1] in ("0", "1"):
        return False
    c = 0
    for k, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[k % 8][int(ch)]]
    return c == 0


def _merge(spans):
    """Overlapping spans joined into one, keeping the rule of the first."""
    out = []
    for s, e, rule in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(e, out[-1][1]), out[-1][2])
        else:
            out.append((s, e, rule))
    return out


def f1_spans(text):
    """F1: every email, phone number or ID number, removed with its label. A line left with no letter or digit
    after the removal ("Tel: … / Fax: …") is removed whole."""
    not_personal = [m.span() for rx in F1_NOT for m in rx.finditer(text)]
    spans = []
    for kind, rx, check in F1_PATTERNS:
        for m in rx.finditer(text):
            s, e = m.span()
            if kind == "email":
                if m.group(0).lower().endswith(F1_EMAIL_SKIP):
                    continue
            elif any(s < b and a < e for a, b in not_personal):
                continue
            digits = re.sub(r"\D", "", m.group(0))
            if check == "luhn" and not _luhn(digits) or check == "verhoeff" and not _verhoeff(digits):
                continue
            spans.append((s, e, "F1-" + kind))
    spans = _merge(spans)
    out = []
    for s, e, rule in spans:
        ls = text.rfind("\n", 0, s) + 1
        le = text.find("\n", e)
        le = len(text) if le < 0 else le
        rest = text[ls:s] + text[e:le]
        for s2, e2, _ in spans:  # other values on the same line go too
            if ls <= s2 and e2 <= le and (s2, e2) != (s, e):
                rest = rest.replace(text[s2:e2], "")
        out.append((ls, le, rule) if not re.search(r"[^\W_]", rest) else (s, e, rule))
    return _merge(out)


# ----- B4 template and code junk ------------------------------------------------------------------------------
# Part 1, fix: template expressions left in the text by a web page that was not filled in.
B4_TEMPLATE = re.compile(
    r"\{\{[^{}\n]{0,80}\}\}"                          # {{ title }}
    r"|\{%[^\n]{0,80}?%\}"                            # {% if x %}
    r"|\$\{[^{}\n]{0,80}\}"                           # ${name}
    r"|`[\w.]+(?:\s*(?:\|\||&&)\s*[\w.]+)+`"          # `page.data.shortTitle || page.data.title`
    r"|(?<=[:=$])\s*(?:undefined|NaN)\b"              # Price: NaN, name=undefined
    r"|^[ \t]*(?:undefined|NaN|null)[ \t]*$", re.M)   # a line that is only "undefined"
# Part 2, drop: a document that is mostly code. A line is a code line when it carries at least B4_MIN_TOKENS code
# tokens and at least one for every B4_WORDS_PER_TOKEN words. The document is dropped when code lines hold more than
# B4_SHARE of its characters. Code in this pack is often flattened onto one line, so tokens are counted, not lines.
B4_CODE_TOKENS = re.compile(
    r"::|->|=>|==|!=|<=|>=|&&|\|\||\+\+|\+=|-=|\);|\)\s*\{|[{};]\s*$|\}"
    r"|^\s*(?:#include|import\s|from\s+\S+\s+import|def\s|class\s|public\s|private\s|static\s|void\s|return\b"
    r"|require\s|var\s|let\s|const\s|function\b|Sub\s|End Sub|Dim\s|\$\s|>>>\s|>\s)"
    r"|\b(?:End Sub|ByVal|As Integer|System\.out|printf|println)\b", re.M)
B4_MIN_TOKENS, B4_WORDS_PER_TOKEN, B4_SHARE = 2, 6, 0.5
TABLE_ROW = re.compile(r"^\s*\|.*\|\|")  # "|cell||cell|": a flattened table, not code


def b4_code_lines(text):
    """(start, end) of every line that looks like code."""
    out, pos = [], 0
    for line in text.split("\n"):
        tokens = len(B4_CODE_TOKENS.findall(line))
        words = len(line.split())
        if tokens >= B4_MIN_TOKENS and tokens * B4_WORDS_PER_TOKEN >= words and not TABLE_ROW.match(line):
            out.append((pos, pos + len(line)))
        pos += len(line) + 1
    return out


def b4_spans(text):
    """B4: the document is dropped if it is mostly code; otherwise template expressions are removed."""
    code = sum(e - s for s, e in b4_code_lines(text))
    if text.strip() and code > B4_SHARE * len(text.strip()):
        return [(0, len(text), "B4-mostly-code")]
    return [(m.start(), m.end(), "B4-template") for m in B4_TEMPLATE.finditer(text)]


# ----- C2 repeated lines (30 Oct) ------------------------------------------------------------------------------
# Fix: a line that appears C2_MIN_REPEAT or more times in one document keeps its first copy; the later copies go.
# Lines shorter than C2_MIN_CHARS ("*", "Answer") are left alone.
C2_MIN_REPEAT, C2_MIN_CHARS = 3, 10


def c2_spans(text):
    """C2: later copies of a line repeated C2_MIN_REPEAT or more times in the document."""
    seen, lines, pos = {}, [], 0
    for line in text.split("\n"):
        key = " ".join(line.split())
        if len(key) >= C2_MIN_CHARS:
            lines.append((pos, pos + len(line), key))
            seen[key] = seen.get(key, 0) + 1
        pos += len(line) + 1
    out, first = [], set()
    for s, e, key in lines:
        if seen[key] >= C2_MIN_REPEAT:
            if key in first:
                out.append((s, e, "C2-repeated-line"))
            first.add(key)
    return out


# ----- C5 lists of keywords or links (30 Oct) ------------------------------------------------------------------
# Drop: a document where more than C5_SHORT_SHARE of the lines have at most C5_SHORT_WORDS words, with at least
# C5_SHORT_MIN such lines (a list page, not prose). Fix: a tail of at least C5_TAIL_LINES lines at the end, each of
# 2 to 5 words, all lower case and without punctuation (search keywords appended to a page).
C5_SHORT_WORDS, C5_SHORT_SHARE, C5_SHORT_MIN, C5_TAIL_LINES = 3, 0.5, 10, 4
_C5_KEYWORD = re.compile(r"^[a-z0-9][a-z0-9 '-]*$")


def c5_spans(text):
    """C5: the whole document (drop) when it is mostly very short lines; else a lower-case keyword tail (fix)."""
    raw, pos = [], 0
    for line in text.split("\n"):
        if line.strip():
            raw.append((pos, line))
        pos += len(line) + 1
    short = sum(1 for _, l in raw if len(l.split()) <= C5_SHORT_WORDS)
    if raw and short >= C5_SHORT_MIN and short > C5_SHORT_SHARE * len(raw):
        return [(0, len(text), "C5-list-page")]
    tail = []
    for off, line in reversed(raw):
        s = line.strip()
        if 2 <= len(s.split()) <= 5 and _C5_KEYWORD.match(s):
            tail.append((off, off + len(line), "C5-keyword-tail"))
        else:
            break
    return tail[::-1] if len(tail) >= C5_TAIL_LINES else []


# ----- D3 mixed language ---------------------------------------------------------------------------------------
# Keep: nothing is removed. d3_flags() lists passages in another alphabet so a reader can look at them.
D3_MIN_WORDS = 3      # words in a row in one other alphabet
D3_MIN_CHARS = 4      # or, for scripts written without spaces (Chinese, Japanese), characters in a row
_NO_SPACES = {"CJK", "HIRAGANA", "KATAKANA", "THAI"}


def _script(ch):
    """The alphabet of a letter: the first word of its Unicode name (LATIN, CYRILLIC, GREEK, CJK, …)."""
    name = unicodedata.name(ch, "")
    return name.split(" ")[0] if name else ""


def _word_script(word):
    scripts = {_script(ch) for ch in word if ch.isalpha()}
    return scripts.pop() if len(scripts) == 1 else ""


def d3_flags(text):
    """(start, end, script) of every run of words in one alphabet other than Latin."""
    flags, run = [], []
    for m in re.finditer(r"\S+", text):
        sc = _word_script(m.group(0))
        if run and sc != run[0][2]:
            flags += _close(run)
            run = []
        if sc and sc != "LATIN":
            run.append((m.start(), m.end(), sc))
    return flags + _close(run)


def _close(run):
    if not run:
        return []
    letters = sum(1 for s, e, _ in run for _ in range(e - s))
    if len(run) >= D3_MIN_WORDS or run[0][2] in _NO_SPACES and letters >= D3_MIN_CHARS:
        return [(run[0][0], run[-1][1], run[0][2])]
    return []


def d3_spans(text):
    """D3: keep. Mixed language is natural; nothing is removed."""
    return []

# ----- helpers -----------------------------------------------------------------------------------------

def _raw_lines(text):
    """(offset, line) for every line, empty ones included."""
    pos = 0
    for line in text.split("\n"):
        yield pos, line
        pos += len(line) + 1


def _lines(text):
    """(offset of the stripped line, stripped line) for every non-empty line."""
    out = []
    for pos, raw in _raw_lines(text):
        s = raw.strip()
        if s:
            out.append((pos + raw.index(s), s))
    return out


def _norm(line):
    return " ".join(line.lower().split())


# ----- C1 part 1: the phrase rules -----------------------------------------------------------------------

def c1_phrase_spans(text):
    """(start, end, rule) of every span the phrase rules remove."""
    spans, k = [], 0
    for off, line in _raw_lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        k += 1
        for rule, (rx, where) in C1_RULES.items():
            if where == "inline":
                m = rx.search(line)
                if m and len(stripped) > SHORT:
                    spans.append((off + m.start(), off + m.end(), rule))
                    break
                continue
            if where == "start" and k > START_LINES:
                continue
            limit = {"C1-navigation": 160, "C1-promotion": 220}.get(rule, SHORT)
            if len(stripped) > limit or not rx.search(stripped):
                continue
            spans.append((off, off + len(line), rule))
            break
    return spans


# ----- C1 part 2: the line scorer --------------------------------------------------------------------------

def line_features(text, repetition=None):
    """The 20 features of every non-empty line, in the order of FEATURES.
    repetition: optional {normalised line: number of documents containing it}; without it every line counts once."""
    repetition = repetition or {}
    lines = _lines(text)
    n = len(lines)
    feats = []
    for k, (off, s) in enumerate(lines):
        words = s.split()
        caps = sum(1 for w in words if w[:1].isupper()) / max(1, len(words))
        nxt = len(lines[k + 1][1]) if k + 1 < n else 0
        prv = len(lines[k - 1][1]) if k > 0 else 0
        feats.append([
            float(len(s) <= 60), float(len(s) <= 120), math.log(1 + len(s)), float(s[-1] in END_PUNCT),
            float(k < 3), float(k >= n - 3), k / max(1, n - 1),
            float(len(LINK_WORDS.findall(s))), float(bool(URL.search(s))), float(bool(COPY.search(s))),
            float(bool(DATE.search(s))), float(len(SEPARATORS.findall(s))), caps,
            float(s[:1] in "-•*|►>"), float(bool(BYLINE.match(s))),
            math.log(max(1, repetition.get(_norm(s), 1))), sum(ch.isdigit() for ch in s) / len(s),
            float(len(words) <= 3), float(nxt > 200), float(prv > 200),
        ])
    return lines, feats


def line_score(x):
    """The probability that a line is boilerplate: logistic regression on standardised features."""
    z = B + sum(w * (v - m) / s for v, (w, m, s) in zip(x, WEIGHTS))
    return 1 / (1 + math.exp(-z))


def gate_signal(line):
    """An explicit boilerplate signal: link words, web address, ©, a full date, a byline or menu separators.
    A table row "|cell||cell|" without link words is content."""
    if line.startswith("|") and "||" in line and "»" not in line and not LINK_WORDS.search(line):
        return False
    return bool(LINK_WORDS.search(line) or URL.search(line) or COPY.search(line) or FULL_DATE.search(line)
                or BYLINE.match(line) or MENU_SEP.search(line))


def prose_line(line):
    """A sentence (PROSE_WORDS or more words, mostly lower case) with no web address, © or byline: the scorer may not
    remove it, whatever its date or link words (prose guard, 4 Nov)."""
    words = WORD_TOKEN.findall(line)
    return (len(words) >= PROSE_WORDS and sum(w[0].islower() for w in words) >= PROSE_LOWER * len(words)
            and not (URL.search(line) or COPY.search(line) or BYLINE.match(line)))


def _signal(line, repetition):
    """gate_signal, plus the gate additions of 27 Oct: GATE_WORDS, and a line found in GATE_REPEAT or more
    documents of the pack (needs the pack's repetition counts; without them this part never fires). A prose line
    never counts as signalled."""
    if prose_line(line):
        return False
    return (gate_signal(line) or bool(GATE_WORDS.search(line))
            or repetition.get(_norm(line), 1) >= GATE_REPEAT)


def c1_spans(text, repetition=None):
    """The C1 medicine. Returns (spans to remove, flagged_for_drop)."""
    rep = repetition or {}
    phrase = c1_phrase_spans(text)
    phrase_hits = {s for s, _, _ in phrase}
    lines, X = line_features(text, repetition)
    scores = [line_score(x) for x in X]
    inline = {k for k, (o, s) in enumerate(lines)
              if any(o <= a < o + len(s) for a, _, r in phrase if r == "C1-teaser-inline")}
    remove = {k for k, (off, s) in enumerate(lines) if off in phrase_hits}
    remove |= {k for k, sc in enumerate(scores)
               if sc >= THRESHOLD and len(lines[k][1]) <= MAX_LINE and _signal(lines[k][1], rep) and k not in inline}
    changed = True
    while changed:                          # block expansion
        changed = False
        for k in sorted(remove):
            for j in (k - 1, k + 1):
                if 0 <= j < len(lines) and j not in remove and j not in inline and len(lines[j][1]) <= 120 \
                        and lines[j][1][-1] not in END_PUNCT and scores[j] >= EXPAND_FACTOR * THRESHOLD \
                        and (_signal(lines[j][1], rep) or KEY_VALUE.match(lines[j][1])):
                    remove.add(j)
                    changed = True
    spans = [(lines[k][0], lines[k][0] + len(lines[k][1]), "C1-phrase" if lines[k][0] in phrase_hits else
              "C1-scorer") for k in sorted(remove)]
    spans += [sp for sp in phrase if sp[2] == "C1-teaser-inline"]
    removed = len({p for s, e, _ in spans for p in range(s, e)})
    if text and removed > MAX_SHARE * len(text) and removed > MIN_DROP_CHARS:
        return [], True                      # too much would go: drop the document instead
    return spans, False


# ----- C3 ------------------------------------------------------------------------------------------------

def c3_spans(text, repetition=None):
    """The C3 medicine: remove the last line when it is an unfinished sentence and C1 does not remove it."""
    lines = [(o, l) for o, l in _raw_lines(text) if l.strip()]
    if not lines:
        return []
    off, last = lines[-1]
    c1, flagged = c1_spans(text, repetition)
    if flagged:
        c1 = [(0, len(text), "C1-drop-flag")]
    if any(s < off + len(last) and e > off for s, e, _ in c1):
        return []
    s = last.rstrip()
    words = s.split()
    if len(words) >= 6 and (s[-1] in ":," or words[-1].lower() in DANGLING):
        return [(off, off + len(last), "C3-unfinished-end")]
    return []


# ----- use ---------------------------------------------------------------------------------------------------

def clean(text, repetition=None):
    """Apply all the medicines. Returns (cleaned text, action) where action is "keep", "fix" or "drop".
    D3 removes nothing: d3_flags(text) only points a reader at passages in another alphabet."""
    spans, flagged = c1_spans(text, repetition)
    if flagged:
        return "", "drop"
    b4, c5 = b4_spans(text), c5_spans(text)
    if b4 and b4[0][2] == "B4-mostly-code" or c5 and c5[0][2] == "C5-list-page":
        return "", "drop"
    spans = spans + c3_spans(text, repetition) + f1_spans(text) + b4 + c2_spans(text) + c5
    if not spans:
        return text, "keep"
    for s, e, _ in reversed(_merge(spans)):  # overlapping spans joined, later ones first so offsets stay valid
        text = text[:s] + text[e:]
    return text, "fix"


if __name__ == "__main__":
    sample = ("By A. Writer\nThe article starts here and runs on for a while, as articles do. It has several "
              "sentences of real content.\n© 2015 Example Publishing\nView all Kids Bikes")
    print(clean(sample))
```
