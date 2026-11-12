# Medicine sheet: ind-ml-fw2 (umeshnmenon)

Pack: Malayalam FineWeb (`mal_Mlym`), 500 documents. All 500 are in `labels.csv`: 285 `fix`, 194 `clean`, 21 `drop`. Each code is written once per row, so the counts below are documents per code.

| Code | Disease | Documents | Medicine |
|---|---|---:|---|
| C1 | Boilerplate | 213 | Medicine 1 |
| D3 | Mixed language | 85 | Medicine 2 (keep) |
| C4 | Two documents joined | 25 | Medicine 3 |
| F3 | Harmful content | 4 | Medicine 4 (kept; below the threshold) |
| G1 | Cut at the vowel sign | 19 | Medicine 5 |
| C2 | Repeated text inside one document | 8 | Medicine 6 |
| C5 | Keyword or link list | 11 | Medicine 7 |
| C3 | Truncated document | 5 | none (not more than five) |
| B4 | Placeholder or interface text | 4 | none |
| D4 | Bad machine translation | 1 | none |
| F1 | Personal data | 1 | none |
| G4 | Over-normalised | 1 | none |
| H1, H2, H3 | Duplicates across the pack | 0 | none; method under Duplicates across the pack |

A medicine is written for every code seen in more than five documents. F3 was first read as 16 documents; after the ruling of 25 Oct (#15), news about crime, abuse, terror or politics is not F3, so twelve of them were re-coded and F3 stands at 4 documents. That is below the five-document threshold; Medicine 4 stays in the sheet because the F3 entry was asked for on the 16-document count, and it can be dropped.

Every medicine has the same shape. Layer 1 is a rule (regex or counting) for patterns that recur in this pack. It is cheap, exact, and easy to harm-test. Layer 2 is the Laya decision model ([convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya), `laya-multilingual` checkpoint) for wordings the rule has not seen. Laya does not generate text, so it cannot invent a span, and the same input always gives the same answer. Where no Layer 1 rule separated the disease from `clean` documents, the section says so.

**Harm tests.** `ind-ml-fw2` has one reader, so it has no gold set. Under TSAI's rule (#211) every harm block therefore reads "gold set empty, not testable". The numbers that follow it are an extra note and not a pass or a fail: they are measured on the 194 documents marked `clean` in this sheet (one document is 0.5% of 194), a proxy that the same reader labelled. All rule numbers are measured on the same 500 rows the rules were written from, so coverage figures are in-sample and will be lower on unseen documents. Final numbers must come from the official Malayalam gold set.

**How the functions are written.** Each medicine is a function `medicine_<code>(text)`. A fix medicine returns the fixed text, and a drop medicine returns `True` when the document is dropped. Every Layer 1 block runs on its own and needs only Python's `re`; the Laya code is in a separate block, so a test can load the Layer 1 code without the `laya` package. The run order and the combined function `clean(text)` are in the section before Duplicates.

**Revision after reading a teammate's sheet.** A teammate's medicine sheet for a Kannada pack was used as a checklist of gaps, not as a source of code. It is for another language and pack, so only the ideas were tested here, each on this pack's clean documents. Eight changes came out of it:

| Gap in this sheet | Change | Where |
|---|---|---|
| The `Don't Miss!` / `Just In` rail was cut only at its cue line; the `- News …`, `- 2 hrs ago …` link lines under it stayed (274 lines in 34 documents) | A rail block rule deletes the cue and the `-` lines under it | Medicine 1 |
| The `You may also like` cue was deleted by the line rule before the block rule could see it, so the related-headlines block stayed | The block rule now runs first | Medicine 1 |
| The English-block cut could leave a hollow document | The cut is made only when 200 Malayalam letters remain and the rest is under 30% Latin | Medicine 3 |
| C2 had only the 300-character passage rule | An exact-line rule (50 characters or more) is added | Medicine 6 |
| The code blocks started a Laya model on import and returned `None` or text from one function | Layer 1 and Layer 2 are in separate blocks; drop rules return `True` | all |
| There was no run order and no function that runs all medicines | `clean(text)` and the run order | after Medicine 7 |
| C5 and C2 had no function under the `medicine_<code>` name | `medicine_c5`, `medicine_c2` added | Medicines 6, 7 |
| D3 had no function | `medicine_d3` returns the text unchanged | Medicine 2 |

Ideas that were tested and not taken are in Rejected options.

---

## Medicine 1 — C1 (boilerplate)

1. **Disease:** C1, 213 documents. Examples:
   - `c9644cf5133fa7ec`, offset 958-1159 — `കൈരളി ഓണ്ലൈന് വാര്ത്തകള് വാട…`, a WhatsApp call to action at the end
   - `481bb64f8f1f35fa`, offsets 0-40 and 42-76 — `Karnataka` and `What's New`, the title and rail lines of a search-result page (`488d7b7aa3093e59` has the same shape)
   - `e95ed7fc1706020c`, offset 774-814 — `Story high light: onion price`, an English footer note

2. **Medicine:**

   **Layer 1, regex.** Delete whole lines that match the site furniture seen in this pack: credit and photo lines (`Credits`, `Photo:`, `PC:`, `Screengrab`, `Source:`), summary and highlight lines (`English Summary`, `Story Highlights`, `Content Highlights`, `Content Summary`), rails (`Also Read`, `Read More:`), stamps (`Updated:`, `Published:`, `Last Modified`, time stamps such as `Jun 9, 2021, 7:14 AM IST`), share prompts (`Share this:`, `Like our page https://…`, `View this post on Instagram`), and the Malayalam calls to action (`കൈരളി ഓണ്ലൈന് …`, `കൊവിഡ് പോരാട്ടത്തില് അണിചേരുകയാണ് ഫ്ളവേഴ്സും …`, `കൂടുതൽ … വാർത്തകൾക്ക്`, `കടപ്പാട്:`, `(തുടരും)`). Two block rules go with the line rule. A cue line such as `You may also like`, `Top Stories`, `Trending`, `Latest News` starts a related-headlines block that runs to the end of the document, so everything from that line on is deleted. A `Don't Miss!` or `Just In` cue is a rail: it is deleted together with the `- News …`, `- 2 hrs ago …`, `- #tag …` link lines directly under it, and with nothing else. The order is block, rail, line, tail, because the line rule also knows the words `You may also like` and would otherwise delete the cue before the block rule sees it. The Malayalam read-more tails from the first sheet are kept.

   **Layer 2, Laya.** For lines the regex did not match, ask Laya whether the line is article body or page furniture. Pass the line, its neighbours, and its position. Delete only unbroken runs of furniture at the start and at the end of the document, and the headline blocks the regex cut. Never cut from the middle: names, glosses, and quotations live there.

   Laya must be fine-tuned before use. The base checkpoints are close to chance without it. Training data comes from this sheet: lines inside the `offset` ranges of C1 rows are furniture, and lines of the `clean` documents are body. After fine-tuning, fit a temperature on held-out lines, because the model ships over-confident. The question is a two-option `choice`, not a yes/no `noul`, because the model card reports that `noul` can follow its option labels instead of the text.

Layer 1 code. It runs on its own and needs only `re`:

```python
import re

C1_RAIL = re.compile(
    r"(?im)^[ \t]*(?:Don't Miss!?|Just In)[ \t]*\n(?:[ \t]*(?:-[ \t]+.*)?(?:\n|\Z))+"
)
C1_BLOCK = re.compile(
    r"(?im)^\s*(?:You may also like|Top Stories|More Stories\.*|Trending|Latest News|Related(?: News)?"
    r"|ബന്ധപ്പെട്ട വാര്ത്തകള്)\s*$[\s\S]*\Z"
)
C1_LINE = re.compile(
    r"(?i)^[ \t]*(?:"
    r"Credits?\s*:.*|english summary\b.*|Don't Miss!?\b.*|Just In\b.*"
    r"|Also Read(?:-|:|\b).*|Read Also(?:-|:|\b).*|Read More\s*:.*|You may also like\s*:.*|you might also like\b.*"
    r"|Screengrab\b.*|Updated:\s+.*|Published:\s+.*|Last (?:Modified|updated)\b.*|Photo\s*:.*|©\s*\d{4}\b.*"
    r"|Story Highlights?\s*[:\u2013-].*|Content Highlights?\s*:.*|Content Summary\s*:.*|Story Name\s*:.*"
    r"|Read from beginning.*|Other posts in this series.*|\(?PC\s*:.*|Source\s*:.*|Representative Image\b.*"
    r"|View this post on Instagram|Continue reading.*|Next Story|Share this:?|Adjust Story Font"
    r"|Comments are closed.*|Begin typing your search.*|Get real time update.*|follow us\b.*"
    r"|Like our page\s+https?://.*|https?://(?:www\.)?facebook\.com/\S*"
    r"|.*\(Search results\s*-\s*\d+\)"
    r"|(?:Kerala|India|What's New)?[A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M IST"
    r"|\d{1,2} [A-Z][a-z]+,? \d{4}\s*,?\s*\d{1,2}:\d{2}(?::\d{2})? [AP]M"
    r"|[A-Z][a-z]{2} \d{1,2}, \d{4} - [A-Z][a-z]{2} \d{1,2}, \d{4}"
    r"|By\s+സമകാലിക.*|കൈരളി ഓണ്.{0,12}വാര്.*(?:വാട്സ്ആപ്|വാട്സാപ്).*"
    r"|കൂടുതൽ (?:കായിക )?വാർത്തകൾക്ക്.*|കൂടുതൽ (?:വിവരങ്ങൾ|അറിയാൻ).*വീഡിയോ.*"
    r"|കൊവിഡ് പോരാട്ടത്തില് അണിചേരുകയാണ് ഫ്ളവേഴ്സും.*|കൊവിഡ് മഹാമാരിയുടെ രണ്ടാംവരവിന്റെ.*"
    r"|ഇനിയാർക്ക് വേണം ലേണിംഗ് ആപ്പ്.*|കടപ്പാട്\s*:.*|Report\s*:.*|തയ്യാറാക്കിയതു്.*"
    r"|\(\s*തുടരും\.?\s*\)|ശബ്ദം കേൾക്കാം|ഏറ്റവും പുതിയ വാർത്തകൾ ഇനി.*|ജോലി ഒഴുവുകളെ.*ടെലെഗ്രാമിൽ.*"
    r"|അഴിമുഖം വാട്സാപ്പില്.*|സൈബര് നിയമ പ്രകാരം.*|ഇവിടെ കൊടുക്കുന്ന അഭിപ്രായങ്ങൾ.*"
    r"|ചരിത്രം\[തിരുത്തുക\]|അഭിപ്രായം രേഖപ്പെടുത്തുക.*"
    r")[ \t]*$",
    re.M,
)
C1_TAIL = re.compile(
    r"(?m)(?:ഈ വാര്ത്ത കൂടി വായിക്കൂ.*$|ദേശാഭിമാനി വാർത്തകൾ ഇപ്പോള്.*$|ഏറ്റവും വിശ്വാസ്യതയുള്ള വാർത്തകള്.*$)"
)


def medicine_c1(text):
    """C1: delete page furniture. The block cue is matched first, because the line rule also knows its words."""
    text = C1_BLOCK.sub("", text)
    text = C1_RAIL.sub("", text)
    text = C1_LINE.sub("", text)
    return C1_TAIL.sub("", text)
```

Layer 2 code. It needs the `laya` package and the Layer 1 code above, and it is not run yet:

```python
from laya import Router

router = Router(preload=True)

FURNITURE = {"part": {
    "type": "choice",
    "instructions": "Is this line part of the article, or part of the web page around it?",
    "criteria": {
        "A": "article body: sentences of the news story, recipe or essay",
        "B": "page furniture: related links, credits, bylines, dates, share or read-more prompts, ads, copyright",
    },
}}


def is_furniture(lines, i, threshold=0.9):
    state = {
        "line": lines[i],
        "position": "start" if i < 3 else "end" if i > len(lines) - 4 else "middle",
        "previous": lines[i - 1] if i else "",
        "next": lines[i + 1] if i + 1 < len(lines) else "",
    }
    answer = router.predict(state, FURNITURE, model="multilingual",
                            max_len=8192)["answers"]["part"]
    return answer["choice"] == "B" and answer["confidence"] >= threshold


def medicine_c1_laya(text, threshold=0.9):
    """Layer 1 first; then Laya trims unbroken runs of furniture at the start and the end only."""
    lines = medicine_c1(text).split("\n")
    start, end = 0, len(lines)
    while start < end and (not lines[start].strip() or is_furniture(lines, start, threshold)):
        start += 1
    while end > start and (not lines[end - 1].strip() or is_furniture(lines, end - 1, threshold)):
        end -= 1
    return "\n".join(lines[start:end])
```

   Setup: `pip install laya` (Python 3.10 or newer); the `laya-multilingual` weights download on first use. The checkpoint ships with a 1,024-token limit, so the calls pass `max_len=8192`; the model card says accuracy varies beyond about 4,000 tokens.

   The model card (`laya` 0.3.20) shows `answers[...]["choice"]` but does not name the field that holds the probability of that choice. `confidence` is assumed here; check it against the installed package.

3. **Action:** **fix** (delete the matched lines and blocks). Drop the document if fewer than about 200 characters of Malayalam prose remain after the cut.

4. **Harm test:** **Gold set empty, not testable** (one reader, TSAI rule #211). Extra note, on the 194 `clean` documents as a proxy:

   | Layer | Clean documents changed (of 194) | Dropped | C1 documents changed (of 213) |
   |---|---:|---:|---:|
   | Layer 1, `medicine_c1` (with the rail rule) | 0 | 0 | 158 |
   | Layer 1, same regex without the rail rule | 0 | 0 | 158 |
   | Layer 2, Laya | not run yet | not run yet | not run yet |

   “Changed” means the text is different after the medicine. The document counts do not move with the rail rule, because the cue line already changed those documents; the rule only deletes more text in them (the `-` lines under the cue are long). The rest of the C1 documents hold headline lists with no fixed cue or furniture the regex has not seen; Layer 2 is needed for those. Each C1 row now keeps at most three examples, so how much of the labelled text the regex covers can no longer be measured from `labels.csv`. Seven D3 examples in five documents overlap a regex deletion; see Medicine 2.

5. **Side effects:** An article that discusses the phrase “Also Read” or quotes a `Source:` / `Credits:` line on its own line loses that line. The block rule deletes everything after a `Trending` or `Latest News` line, so a real article whose last section is headed `Trending` would lose that section. The rail rule deletes any `-` line directly under a `Just In` or `Don't Miss!` line, so a real bullet list that follows such a line as its heading would go too. A short article whose first line is a real headline could lose it if Laya reads it as furniture. The 200-character rule turns an over-cut into a drop instead of a hollow document. The regex holds the phrases from this pack, so on other sources it will miss; Layer 2 exists for the rest.

---

## Medicine 2 — D3 (mixed language)

1. **Disease:** D3, 85 documents. D3 here means two languages inside one sentence, for example a Malayalam sentence with an English word or a Latin-script name. DISEASES.md says this can be natural: label it, do not judge it. Whole English lines are not D3: page furniture is C1 (Medicine 1), glued-on English text is C4 (Medicine 3), keyword lines are C5 (Medicine 7). Examples: `869114d23fc20d12` (English words all through a Malayalam text: `formal` at offset 580-585, `Foundation` at 5030-5039), `0b5c0d5c22f51385` (`lux` at offset 1965-1967, `La` at 2380-2381), `8adf49c6f34f52e5` (`kidney` at offset 653-658, `NB` at 1449-1450).

2. **Medicine:** none. D3 is kept as written. The medicine is a guard, not an edit: no cleaning step may strip Latin letters from a Malayalam sentence, and every line a rule deletes must be a whole line.

   **Layer 1.** No rule. The guard is built into the other medicines: Medicine 1 deletes only whole lines that match a furniture pattern; Medicine 3 deletes only blocks where at least 85% of the letters are Latin.

   **Layer 2.** None. Laya is not asked about D3.

```python
def medicine_d3(text):
    """D3: no medicine. A language mixed inside a sentence is recorded, not repaired."""
    return text
```

3. **Action:** **keep** (no change). A document is never dropped for mixing languages.

4. **Harm test:** **Gold set empty, not testable** (one reader, TSAI rule #211). Extra note: a rule that does nothing changes 0 of the 194 `clean` documents. The useful check is whether the other medicines touch D3 text: the extended C1 regex overlaps 7 of the D3 examples (each D3 row keeps at most three), in five documents: `67cfcddf399de1f3` (a `Last Modified` stamp), `62e94166b65a499a` and `90c2e79506052530` (`By` and `Published:` byline lines; two examples each), `9cd2c33ba949d66c` (`You may also like:`) and `16ebded75c7f4f4d` (a `Photo:` line). These are page furniture that was also marked D3, so the C1 deletion is right and the D3 mark on them is the one to revisit.

5. **Side effects:** none from this medicine. The cost of keeping D3 is that the mix reaches the training data; that is a choice for the downstream tokenizer, not a defect to repair. A full English article labelled `mal_Mlym` is D1, not this disease.

---

## Medicine 3 — C4 (two documents joined)

1. **Disease:** C4, 25 documents. C4 is two unrelated texts in one document with no boundary. It is not a duplicate: text repeated inside one document is C2, and copies across documents are H1 and H2. In this pack 5 of the 25 documents are 30% or more Latin letters, and 5 have an English block of 500 characters or more: an English article or paragraph glued onto a Malayalam one. The others join Malayalam texts (an unrelated news item, a teaser list) that a rule cannot tell apart. Examples: `a153c6be6203d747` (an English block of about 1,600 characters at offset 8707-10309, starting `Deliberate`), `6c2bb301b66fd16a` (an English news article from the first character, offset 0-3992, starting `Washington — The Trump adminis…`), `b2398ab29a742155` (an English block at offset 2433-4612, starting `The new ve…`).

2. **Medicine:**

   **Layer 1, English block rule.** Find runs of consecutive lines in which at least 85% of the letters are Latin and which total at least 500 characters. Cut the run, but only when at least 200 Malayalam letters remain and the rest is under 30% Latin; otherwise the cut would leave a hollow document, so the run is kept. A few joins are a rail or a promotion; `medicine_c1` handles those, and `clean()` runs it first.

   **Layer 2, Laya.** For a document that still has three or more paragraphs, ask Laya whether each later paragraph continues the opening. Cut from the first paragraph it confidently calls a different article. If less than about 200 characters remain, drop the document instead of keeping a stub.

Layer 1 code. It runs on its own and needs only `re`:

```python
import re

LAT = re.compile(r"[A-Za-z]")
MAL = re.compile(r"[\u0D00-\u0D7F]")


def latin_share(s):
    la, ma = len(LAT.findall(s)), len(MAL.findall(s))
    return la / (la + ma) if la + ma else 0.0


def english_blocks(text, min_chars=500, share=0.85):
    """Inclusive (start, end) ranges of consecutive mostly-Latin lines that total min_chars or more."""
    out, cur, pos, start = [], [], 0, 0
    for ln in text.splitlines(keepends=True):
        la, ma = len(LAT.findall(ln)), len(MAL.findall(ln))
        if (la + ma) > 0 and la / (la + ma) >= share:
            if not cur:
                start = pos
            cur.append(ln)
        elif not ln.strip() and cur:
            cur.append(ln)
        else:
            if cur and sum(map(len, cur)) >= min_chars:
                out.append((start, pos - 1))
            cur = []
        pos += len(ln)
    if cur and sum(map(len, cur)) >= min_chars:
        out.append((start, pos - 1))
    return out


def medicine_c4(text, min_left=200):
    """C4: cut a long English block, but only when readable Malayalam text of min_left characters remains."""
    for a, b in reversed(english_blocks(text)):
        kept = text[:a] + text[b + 1:]
        if len(MAL.findall(kept)) >= min_left and latin_share(kept) < 0.3:
            text = kept
    return text
```

Layer 2 code. It needs the `laya` package and the Layer 1 code above, and it is not run yet:

```python
SAME_STORY = {"story": {
    "type": "choice",
    "instructions": "Does this paragraph continue the same article as the opening?",
    "criteria": {
        "A": "same article: the same event, people or subject",
        "B": "a different article, an advertisement or a promotion",
    },
}}


def medicine_c4_laya(text, threshold=0.9, min_left=200):
    """Layer 1 first; then cut from the first paragraph Laya calls a different article. None means drop."""
    paras = [p for p in medicine_c1(medicine_c4(text)).split("\n") if p.strip()]
    if len(paras) >= 3:
        opening = "\n".join(paras[:2])[:1000]
        for i in range(2, len(paras)):
            answer = router.predict({"opening": opening, "paragraph": paras[i]}, SAME_STORY,
                                    model="multilingual", max_len=8192)["answers"]["story"]
            if answer["choice"] == "B" and answer["confidence"] >= threshold:
                paras = paras[:i]
                break
    kept = "\n".join(paras)
    return kept if len(kept) >= min_left else None
```

3. **Action:** **fix** when one coherent article of about 200 characters or more remains. **drop** (`None`) otherwise.

4. **Harm test:** **Gold set empty, not testable** (one reader, TSAI rule #211). Extra note, on the 194 `clean` documents as a proxy:

   | Layer | Clean documents changed (of 194) | Dropped | C4 documents caught (of 25) |
   |---|---:|---:|---:|
   | English block, 500 characters or more | 0 | 0 | 5 |
   | English block, 300 characters or more | 2 (`6cdde3a305e12754`, `67d97b968426ece4`) | 0 | 9 |
   | English block, 150 characters or more | 2 (the same two) | 0 | 10 |
   | `medicine_c4` (500 characters, with the 200-letter remainder check) | 0 | 0 | 5 changed |
   | English block only at the start or the end, 200 characters or more | 1 (`67d97b968426ece4`) | 0 | 8 |
   | English block only at the start or the end, 400 characters or more | 0 | 0 | 4 |
   | Layer 2, Laya | not run yet | not run yet | not run yet |

   “Caught” means the document holds such a block; in the `medicine_c4` row it means the cut changes the document. The start-or-end rows follow an idea from the teammate's sheet (cut the English block only at an edge, with Kannada text on the other side). On this pack it does not beat the any-position rule: at 200 characters it catches 8 but changes a clean document, and at 400 characters it is safe but catches 4. It was not taken.

   The 500-character limit is chosen because it is the lowest value that changes 0 clean documents. The two clean documents that a lower limit would change keep a quoted English paragraph on purpose (the quotation belongs to the article). The 500-character cut works for the proxy, but the proxy is not a gold set.

5. **Side effects:** A long English quotation or a bilingual article (an English abstract translated into Malayalam in the same page) of 500 characters or more would be cut as if it were a joined text. Laya reads about 768 tokens of state by default, so the opening is cut to 1,000 characters. Most C4 documents (20 of 25) are not caught by Layer 1, so the Laya layer carries most of this medicine and is the part to measure first.

---

## Medicine 4 — F3 (harmful content)

1. **Disease:** F3, 4 documents, all marked `drop`. Ruling 25 Oct (#15): news about crime or abuse is not F3. The 16 first-pass F3 rows were re-read against it. Four stay F3, all adult-content erotic stories (`fe2062c7ec78c645`, `5f624ec5ea610edd`, `04182679c0ab4bb1`, `5838f78a36f58e69`); the evidence gives only the type and the position. Twelve were re-coded because they are news, a short story or a link list, not harmful text. Six are now `clean`: `8089366159cf6715`, `6fa4a9ad37f16fd7`, `d4da81ef018756ec` and `483db7a3cbc3c53b`, and, with the note "contains offensive comments", `85e4684d31112bbb` and `f38f3ead604a0f8e` (news pieces that quote an offensive remark). `38504826d9b1fec6`, a short story built on a sexual chat, carries the same note and is now `fix` (C1: the page's intro and closing lines). The other five: `e3f016e5317ee749` and `3e2e2ff48cc69180` are `fix` (C1: a credit line, a page footer); `fdd89a8d1d030c5e` is `drop` (C4: an unrelated item is joined on); `0bbfb4ca5508fd48` and `b57dac6db054b6fc` are `drop` (C5: search-result link lists). The text is not repeated here.

2. **Medicine:**

   **Layer 1.** No rule. Harmful content has no fixed cue line to match, and a plain keyword list would also hit ordinary news reports about crime, which the notes treat as acceptable (a keyword list was not run). A URL or source blocklist was not tried: it needs the `source` and `url` columns of the pack and a judgement about each site, which this sheet does not record.

   **Layer 2, Laya.** A document-level `choice` question over the first 700 tokens, trained from the 4 `drop` rows against the 194 `clean` rows. The categories follow the ruling: `A` ordinary text, including news about crime, abuse, terror or politics; `B` sexual content; `C` content that incites violence or hatred. Run on two to three windows of long documents and take the highest-scoring window.

3. **Action:** **drop** the whole document. Harmful text cannot be repaired by cutting a line.

4. **Harm test:** **Gold set empty, not testable** (one reader, TSAI rule #211). Extra note, on the 194 `clean` documents as a proxy:

   | Layer | Clean documents changed (of 194) | Dropped | F3 documents caught (of 4) |
   |---|---:|---:|---:|
   | Layer 1 | no rule | no rule | no rule |
   | Layer 2, Laya | not run yet | not run yet | not run yet |

   For a drop-type medicine, “changed” means dropped; the target is 0 clean documents dropped. The six documents re-coded to `clean` (`8089366159cf6715`, `6fa4a9ad37f16fd7`, `d4da81ef018756ec`, `483db7a3cbc3c53b`, `85e4684d31112bbb`, `f38f3ead604a0f8e`) are the first test for this medicine: it must not drop them.

5. **Side effects:** The line between harmful and merely sensitive is a policy choice. `85e4684d31112bbb`, `f38f3ead604a0f8e` and `38504826d9b1fec6` contain offensive comments but are news or a short story, so they are not F3 here; if the gold set marks them F3, this medicine will miss them. Fix the policy before fine-tuning, because the training labels carry the same ambiguity. With 4 positive documents the classifier will be weak; do not trust its threshold without the gold set.

---

## Medicine 5 — G1 (cut at the vowel sign)

1. **Disease:** G1, 19 documents. Four shapes: a space or line break before a vowel sign (`410b12965e64a736` at offset 145-147, `ർഷങ്ങള ിലും`, U+0020 before U+0D3F; `658ef9d2659c1c64` at offset 1084-1086, `സത്തെ ൈവദ്`, U+0020 before U+0D48; also `552cbad46edb7d4d`), a vowel sign after a virama (`7a0d9ce65e64d866` at offset 928-929, `ധാനത്ിതൽ`, U+0D4D U+0D3F; also `d729ca84fca8f7f7`), the old two-letter spelling of a long vowel (`ഒ`+`ാ` instead of `ഓ`, `ഇ`+`ൗ` instead of `ഈ`, `ഉ`+`ൗ` instead of `ഊ`), and a doubled virama (9 documents: `f1aef54ee2bed426`, offset 3735, `സര്്ക്കാര്` for `സര്ക്കാര്`; `d729ca84fca8f7f7`, `ന്്റെ` for `ന്റെ`, three times). Both spellings are one defect, so both are G1: `ന്്റെ` is not an extra chillu, it is `ന്` + virama + a second virama that stands where a ZWJ was. The pack holds no ZWJ or ZWNJ at all (0 documents), and the doubled virama appears in the middle of a word before a consonant and at the end of a word, so the second virama is almost certainly a ZWJ or ZWNJ that the text pipeline turned into a virama. DISEASES.md would call that G2 (lost ZWJ) as much as G1; it is labelled G1 here.

2. **Medicine:**

   **Layer 1, Unicode rules.** A space or line break directly before a dependent vowel sign, virama, anusvara, or visarga is never valid in Malayalam, so it is removed. The three old two-letter spellings are replaced by the single letter. Two or more viramas in a row are written as one. This is a repair and not a restoration: the lost character could have been a ZWJ (a chillu such as `ൻ`) or a ZWNJ, and the text does not say which, so the rule restores neither. One virama gives the standard modern spelling in the cases seen (`ന്റെ`, `സര്ക്കാര്`, a final `ട്`), at the price of a final chillu that is read as a plain consonant with a virama. A vowel sign directly after a virama cannot be repaired by a rule, because the right spelling is not known; such a document is dropped.

   **Layer 2.** None. The rules are exact; Laya adds no value to a Unicode ordering problem.

Layer 1 code. It runs on its own and needs only `re`:

```python
import re

G1_SPACE = re.compile(r"(?<=\S)[ \t\n]+(?=[\u0D3E-\u0D4D\u0D57\u0D02\u0D03])")
G1_STACK = re.compile(r"\u0D4D[\u0D3E-\u0D4C]")
G1_PAIRS = {"\u0D12\u0D3E": "\u0D13", "\u0D07\u0D57": "\u0D08", "\u0D09\u0D57": "\u0D0A"}
G1_DOUBLE = re.compile("\u0D4D{2,}")


def medicine_g1(text):
    """G1: remove a space or break before a vowel sign; write the old two-letter long vowels as one letter;
    write a doubled virama as one."""
    text = G1_SPACE.sub("", text)
    text = G1_DOUBLE.sub("\u0D4D", text)
    for old, new in G1_PAIRS.items():
        text = text.replace(old, new)
    return text


def drop_stacked_sign(text):
    """G1: True when a vowel sign follows a virama; the right spelling cannot be guessed, so the document goes."""
    return bool(G1_STACK.search(text))
```

3. **Action:** **fix** (remove the stray space, replace the two-letter spellings, collapse the doubled virama). **drop** when a vowel sign follows a virama.

4. **Harm test:** **Gold set empty, not testable** (one reader, TSAI rule #211). Extra note, on the 194 `clean` documents as a proxy:

   | Rule | Clean documents changed (of 194) | G1 documents caught (of 19) |
   |---|---:|---:|
   | Space or break before a sign (after any non-space character) | 0 | 7 |
   | Vowel sign after virama | 0 | 2 |
   | `ഒ`+`ാ`, `ഇ`+`ൗ`, `ഉ`+`ൗ` | 0, 0, 0 | 3, 1, 1 |
   | Doubled virama (`്്`) | 0 | 9 |
   | All rules together | 0 | 19 |

   The rules catch all 19 G1 documents, which is in-sample: they were written from these documents. The doubled-virama rule first showed 3 clean documents changed (`96749642c6ee63b7`, `c901aca60b2a4df5`, `fb1865d9dd7edc20`); each really holds a doubled virama (one occurrence each, at the end of a word), so they were relabelled `fix` with G1, together with four documents that had the defect and were labelled for other diseases (`5deb7eee87a81416`, `a918bb8f4988f468`, `90c2e79506052530`, `91693f93929cf1c8`). That makes the 0 above in-sample too. The space rule first required a Malayalam letter before the space and caught only 3 documents; relaxing it to any non-space character caught 7 and still changed 0 clean documents. One non-G1 document, `e2fd009e625dae84`, matches a rule and is probably a missed G1 label.

5. **Side effects:** The break removal could join two lines when a line break really did precede a sign at a paragraph start; that is not valid Malayalam either, so the case should not occur in clean text. Dropping a document for a stacked sign loses an otherwise good article; if this proves common, a character-level model would be needed to guess the correct spelling.

---

## Medicine 6 — C2 (repeated text inside one document)

1. **Disease:** C2, 8 documents (`2307d0c6733e5ce6`, `ce32f63b27e51a58`, `f70a3757c962344d`, `32598246b2330819`, `0f33ec6172258c08`, `5532187469ab46b5`, `94e6d30d96e5dac1`, `d9c2e88749425fa7`). Two forms: an exact passage repeated (`2307d0c6733e5ce6`, a 350-character passage at offset 401-750, starting `ഈ പാട്ടിന്റെ പത്തിലൊന്നു വെറുപ…`, that returns, unchanged, at offset 1809-2158), and filler pages that repeat the same wording with small changes (`ce32f63b27e51a58`: `കുറഞ്ഞ സമയത്തിനുള്ളിൽ തന്നെ നമുക്ക…` at offset 245-279 and again at 1226-1260; also `32598246b2330819`).

2. **Medicine:**

   **Layer 1, exact repeat, two rules.** First, find any passage of at least 300 characters that appears twice and delete the later copy. The copies do not start and end at line or sentence breaks, so hashing lines or sentences misses them. Second, keep the first copy of any line of 50 characters or more that comes back word for word. The line rule is the gap that a teammate's sheet pointed to: it catches repeats shorter than 300 characters, which the passage rule cannot, and it needs no passage search.

   **Layer 2, Laya.** For documents with no exact repeat, ask a document-level `choice` question: `A` the text moves forward, `B` the same points are restated in different words. This is the part that has to catch the filler pages, and it is not run yet.

Layer 1 code. It runs on its own and needs only `re`:

```python
def drop_repeated_passages(text, min_chars=300):
    """Delete the later copy of any passage of min_chars or more that appears twice."""
    while True:
        first, hit = {}, None
        for i in range(len(text) - min_chars + 1):
            j = first.setdefault(text[i:i + min_chars], i)
            if j + min_chars <= i:
                hit = (j, i)
                break
        if hit is None:
            return text
        j, i = hit
        n = min_chars
        while i + n < len(text) and j + n < i and text[j + n] == text[i + n]:
            n += 1
        text = text[:i] + text[i + n:]


def dedupe_lines(text, min_len=50):
    """Keep the first copy of a line that comes back word for word (lines of min_len characters or more)."""
    seen, out = set(), []
    for line in text.split("\n"):
        key = line.strip()
        if len(key) >= min_len and key in seen:
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out)


def medicine_c2(text):
    """C2: remove exact repeats inside one document."""
    return dedupe_lines(drop_repeated_passages(text))
```

3. **Action:** **fix** when the repeat is exact (delete the later copy). **drop** when Laya calls the page filler and fewer than about 200 characters of new content remain.

4. **Harm test:** **Gold set empty, not testable** (one reader, TSAI rule #211). Extra note, on the 194 `clean` documents as a proxy:

   | Rule | Clean documents changed (of 194) | C2 documents caught (of 8) |
   |---|---:|---:|
   | Exact repeat, 100 characters or more | 11 | not measured |
   | Exact repeat, 200 characters or more | 4 | not measured |
   | Exact repeat, 300 characters or more (passage rule) | 0 | 1 (`2307d0c6733e5ce6`) |
   | Exact line, 30, 50 or 80 characters or more (line rule) | 1 (`764508e37990daf8`) at 30 and 50; 1 at 80 | 2 at 30 and 50 (`5532187469ab46b5`, `94e6d30d96e5dac1`); 1 at 80 |
   | `medicine_c2`: passage rule at 300, then line rule at 50 | 1 (`764508e37990daf8`) | 3 |
   | Near-repeat share of sentences (5-gram Jaccard 0.7) | clean range 0 to 0.23 | C2 range 0 to 0.12, inside the clean range |
   | Repeated word 4-grams share | clean range 0 to 0.13 | C2 range 0.03 to 0.11, inside the clean range |
   | Compression ratio (zlib, compressed over raw size) | clean range 0.18 to 0.37 | C2 range 0.19 to 0.23, inside the clean range |
   | Layer 2, Laya | not run yet | not run yet |

   The repeat statistics show the C2 documents are not separable by counting: on all three, the C2 range lies inside the range of the clean documents, so no cut-off flags C2 without flagging clean documents. At 300 characters the passage rule is safe but catches 1 of 8. The line rule adds two more, so `medicine_c2` catches 3 of 8 and still leaves the five rephrased filler pages for Laya. It changes 1 of the 194 clean documents (0.5%): `764508e37990daf8` has a long Malayalam line that comes back word for word, so it is more likely a C2 document labelled `clean` than a harm of the rule. The line rule is lowered no further than 50, because at 20 characters it changes a second clean document (`30d9f640f48b6f1a`).

5. **Side effects:** An article that quotes the same passage or line twice on purpose (a refrain, a repeated headline, a list that repeats an item) loses the second copy. The longer `min_chars` and `min_len` are, the safer and the less useful. Most C2 documents in this sheet are rephrased filler, so this medicine mostly depends on Laya, which has no measurement yet. Eight positive documents are too few to fine-tune from; consider whether the C2 labels on the filler pages are better recorded as C5 or as a low-quality code.

---

## Medicine 7 — C5 (keyword or link list)

1. **Disease:** C5, 11 documents: tag pages and author pages of truncated headlines (`fdf7b31be7ef860f`, offset 0-4197, starting `All posts tagged "Virat Kohl…`; also `94e6d30d96e5dac1`, `35091c832eb7a828`, `daa142867da0b7e0`), search-result lists (`a77103632fcf1837`, offset 0-2802, starting `Mahalakshmi(Search results -…`; also `c33b540a3729e733`, `0bbfb4ca5508fd48`, `b57dac6db054b6fc`), link lists that end an article (`5f3331d890a591b1`, offset 0-680, starting `Don't Miss!` and a `- Travel …` line; also `d3ff6ac08014a686`), and a page joined from several articles and link lists (`6ef515eea2d7307f`).

2. **Medicine:**

   **Layer 1, ellipsis rule.** A document with at least 8 non-empty lines of which at least 25% end in `...` or `…` is a list of truncated headlines. Other link lists end in a call to action and are cut by Medicine 1.

   **Layer 2, Laya.** A document-level `choice` question over the first 700 tokens: `A` continuous prose, `B` a list of headlines, links, tags, or search results.

Layer 1 code. It runs on its own and needs only `re`:

```python
def medicine_c5(text, min_lines=8, min_share=0.25):
    """C5: True when the page is a list of truncated headlines (many lines end in an ellipsis)."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) < min_lines:
        return False
    return sum(ln.endswith(("...", "\u2026", "..")) for ln in lines) / len(lines) >= min_share
```

3. **Action:** **drop** the document when the whole page is a list. **fix** (cut the tail list) when only a trailing link list follows real prose; that case goes through Medicine 1.

4. **Harm test:** **Gold set empty, not testable** (one reader, TSAI rule #211). Extra note, on the 194 `clean` documents as a proxy:

   | Layer | Clean documents changed (of 194) | Dropped | C5 documents caught (of 11) |
   |---|---:|---:|---:|
   | Layer 1, ellipsis share 0.25 or higher | 0 | 0 | 4 |
   | Layer 1, ellipsis share 0.2 or higher | 0 | 0 | 4, but flags 7 labelled rows, 2 of them `fix` |
   | Layer 1, share of lines of 100 characters or less without a full stop, at 50% | 5 | 0 | 5 |
   | Layer 1, same share at 80% | 0 | 0 | 0 |
   | Layer 1, average line length under 60 characters | 0 | 0 | 0 |
   | Layer 2, Laya | not run yet | not run yet | not run yet |

   At 0.25 the rule flags 4 rows in the whole sheet, all `drop`. The line-length rules were counted with 8 or more non-empty lines; at 50% the short-line rule flags as many clean documents as C5 documents, so it was not taken.

5. **Side effects:** A news digest page made of real headlines that end in `...` would be dropped, which is correct for training but loses a whole page. Seven of the eleven C5 documents are not caught by Layer 1 (the search-result pages, for one, carry no ellipsis), so Layer 2 must handle them.

---

## Run order, and one function for the whole sheet

Each section above has a function `medicine_<code>(text)`. A fix medicine returns the fixed text; a drop medicine (`medicine_c5`) returns `True` when the document is dropped. G1 has both: `medicine_g1` fixes, and `drop_stacked_sign` drops. D3 returns the text as it is. F3 has no Layer 1 function, so it is not in the run. Every Layer 1 block above runs on its own, with only `re`. `clean(text)` below needs them all defined first, in the file order, and returns the fixed text or `None` when the document is dropped.

The order matters. The drop rules go first, because a dropped page needs no repair. G1 comes before the line rules, because a stray space or break before a vowel sign would otherwise split a word across two lines. C1 comes before C4, so the page furniture is gone before the English-block rule counts what remains; C2 comes last, so a line is compared after the furniture around it is gone. A document that a medicine changed and that has fewer than 200 Malayalam characters left is dropped, so an over-cut becomes a drop and not a hollow text.

```python
def clean(text, min_left=200):
    """Run the medicines in the order of this sheet. Return the fixed text, or None when the document is dropped."""
    if medicine_c5(text) or drop_stacked_sign(text):
        return None
    out = medicine_g1(text)
    out = medicine_c1(out)
    out = medicine_c4(out)
    out = medicine_c2(out)
    if out != text and len(MAL.findall(out)) < min_left:
        return None
    return out
```

Result of `clean()` on the 500 labelled documents. This is the extra note of the harm test: with the gold set empty, the proxy row is not a pass or a fail.

| Label | Documents | Unchanged | Changed | Dropped |
|---|---:|---:|---:|---:|
| `clean` | 194 | 193 | 1 (`764508e37990daf8`, by the C2 line rule) | 0 |
| `fix` | 285 | 102 | 179 | 4 |
| `drop` | 21 | 11 | 6 | 4 |

The proxy figure is the first row: 0 of 194 clean documents dropped and 1 changed (0.5%). The one change looks like a missed label, not harm: `764508e37990daf8` repeats a long line. The `fix` row says that 102 documents marked `fix` are not touched by any Layer 1 rule: 40 are C1-only documents whose furniture the regex does not know, 37 are D3-only rows (D3 is a keep code, so these should not be `fix`), and the rest are C4, B4, C1 with D3, and a few single-code rows that wait for Laya. The `drop` row says that 11 of the 21 `drop` documents survive Layer 1: 3 are F3 documents, which have no Layer 1 rule, and 8 are rephrased C2 filler pages (3), a C3/C4 page, a C1/C3 page, a D4 page, a C4 page and a C5 search-result page, which also need Laya.

---

## Duplicates across the pack (H1, H2, H3)

The H codes compare one document with the other documents of the pack: an exact copy (H1), a copy with small changes (H2), or the same content in another language (H3). None of the 500 labelled rows carries an H code, so there is no medicine section. The method for running them at corpus scale:

1. **Normalise** each document into a comparison key: NFC, whitespace collapsed, URLs replaced by `<url>`, Latin case folded. The key is used only for comparing; the kept text is the original. Use NFC only, because NFKC would itself cause G4.
2. **Exact duplicates (H1):** hash the key of each document. Keep the first `doc_id` for each hash and drop the later ones.
3. **Near duplicates (H2):** character 5-gram shingles, MinHash with 128 permutations, and LSH at a Jaccard threshold of about 0.8. Character n-grams fit Malayalam better than word n-grams, because one Malayalam word carries suffixes that a word tokenizer splits poorly.
4. **Another language (H3):** a translation shares almost no character n-grams with its source, so MinHash cannot find it. That needs a multilingual sentence encoder trained to match translations, such as LaBSE.

```python
import hashlib
import unicodedata
from datasketch import MinHash, MinHashLSH

URL = re.compile(r"https?://\S+|www\.\S+")

def norm_key(text: str) -> str:
    key = unicodedata.normalize("NFC", text)
    key = URL.sub("<url>", key)
    return re.sub(r"\s+", " ", key).strip().casefold()

def exact_key(text: str) -> str:
    return hashlib.sha1(norm_key(text).encode("utf-8")).hexdigest()

def minhash(text: str, k: int = 5, num_perm: int = 128) -> MinHash:
    key = norm_key(text)
    m = MinHash(num_perm=num_perm)
    for i in range(max(len(key) - k + 1, 1)):
        m.update(key[i:i + k].encode("utf-8"))
    return m

def dedupe(corpus: list[tuple[str, str]], threshold: float = 0.8) -> list[str]:
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    kept = []
    for doc_id, text in corpus:
        m = minhash(text)
        if lsh.query(m):
            continue
        lsh.insert(doc_id, m)
        kept.append(doc_id)
    return kept
```

Side effect: two short news briefs that share a wire-agency template can pass 0.8 without being the same story. Check a sample of the pairs before dropping.

---

## Rejected options

| Option | Why it was not chosen |
|---|---|
| Delete by the `offset` ranges in `labels.csv` | Works for these 500 rows only. The course runs the medicine on documents nobody labelled. The offsets are used instead as Laya training data. NOTE: Just to clean this pack up, we can use the offset range from the annotation to remove the texts.|
| A generative LLM that returns the span to delete | The span can change between runs and can be invented, so the 1% harm test is not repeatable. |
| Split paragraphs into sentences, translate to English, then classify | Translation is a generative step with the same risk. It also erases the signal: English inside a Malayalam page is often the very sign of furniture. Malayalam sentence splitting is unreliable, and furniture sits on whole lines, not inside sentences. Laya reads Malayalam directly. |
| Strip every Latin letter from Malayalam documents | Deletes names, original spellings, and the in-sentence mix (D3) that must stay. |
| Text embeddings and cosine similarity instead of MinHash for H2 | Semantic similarity flags articles on the same event that are not copies, the usable window is 256 to 512 tokens, and it costs more at corpus scale. Embeddings are kept only for H3. |
| Sentence-level near-repeat or compression statistics for C2 | Measured above: the C2 documents fall inside the range of the clean documents on every statistic tried. |
| G1 as a count of vowel signs with no letter to sit on, dropping a document at 3 or more (the teammate's form, rebuilt for the Malayalam block) | 2 of the 194 clean documents have 3 or more such signs (`6ee4680dfa9e8df8` has 5, `936cc8c77af8bf47` has 3; a sign is counted when the character before it is not a Malayalam letter or chillu), so it fails the proxy check (the gold set is empty, so this is only a proxy). Malayalam has more legitimate sign sequences than the rule knows (two-part vowels, chillu forms), and a rule listing them all would be a larger medicine than the one taken. The specific rules in Medicine 5 catch all 19 G1 documents. The two clean documents may deserve a second look. |
| Rules for a literal `\n`, legacy-font residue (Latin-1 letters or `$` inside a word), a digit used for an anusvara, a colon turned into a visarga, and a translation engine's number placeholder (all in the teammate's sheet) | Checked on all 500 documents: 0 documents have a literal backslash-n, a Latin-1 letter beside Malayalam, a `$` before a vowel sign, or an ASCII digit between two Malayalam letters, and 0 have a word-final visarga. These diseases are not in this pack, so the rules are not written. |

## Next steps

1. Decide the 39 D3-only rows marked `fix` (37 of them untouched by any rule): D3 is a keep code, so a row whose only code is D3 is either `clean` with a note or has a second disease that was not coded. Then re-run the counts above.
2. Build Laya training lines from the `offset` ranges (at most three examples per code now) and the `clean` documents, fine-tune `laya-multilingual`, fit the temperature, and fill in every Laya row marked “not run yet”. C1 headline blocks, C4 (20 of 25 documents), C5 (7 of 11) and C2 depend on it most.
3. Confirm that `laya-multilingual` reads Malayalam well. The model card lists 45 of 51 tested languages as usable but does not say whether Malayalam is one of them.
4. Settle the F3 policy before training the F3 classifier. `85e4684d31112bbb`, `f38f3ead604a0f8e` and `38504826d9b1fec6` are no longer F3 and carry the note "contains offensive comments". The documents re-coded from F3 are listed in Medicine 4; the ones re-coded from their type and structure need a full read by the labeller. With 4 documents, F3 is below the five-document threshold, so Medicine 4 may be dropped.
5. Run all medicines on the official Malayalam gold set and fill in the changed and dropped counts. Until then every harm block stays "gold set empty, not testable".
6. Review `764508e37990daf8`, the one `clean` document that `medicine_c2` changes: it repeats a long Malayalam line word for word and is probably C2. Decide whether the doubled virama is G1 or G2, since the pack has no ZWJ at all. Then re-check the `clean` documents with the highest repeated-sentence share (`bbcc6cfa25231b74`, `70ed22c7ac369001`, `eb55fb64c32c318d`, `6b5a5422907ce088`, `26d3c4dfaeb3df12`). If a repeat is a page summary shown twice, they are C2, not `clean`.
