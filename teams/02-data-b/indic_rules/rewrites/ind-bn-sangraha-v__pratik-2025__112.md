# Rewrite in the harm tool's format: ind-bn-sangraha-v, pratik-2025 (PR #112)

TSAI ruling 3 on #211 (3 Nov): the Data B rules owner may rewrite a medicine sheet that `harm_test_indic.py` cannot
read, and the author must OK the rewrite in their PR. **Author OK: pending.**

What changed: the author wrote each rule as a formula in the text. Here each one is a Python function that does what
the formula says, with a `**Disease:** <code>` line. Bengali characters are written as `\u` escapes, so nothing
invisible hides in the code; each escape matches the author's characters (listed under the rule). Where the formula
leaves a choice open, the choice is written under the rule for the author to confirm. Counts and wording are the
author's, from PR #112 at `fb9e448`.

**Harm test.** The author reports results for their own version of each rule on the 50-document gold set. This code
is new, so it is run again on today's gold set (`teams/02-data-b/gold/ind-bn-sangraha-v_gold.csv`, 50 documents) and
the result goes in part 4. The limit is max(1 document, 1%): on 50 documents, 1 document may change.

## Medicine 1: A2 - control characters

1. **Disease:** A2.
2. **Medicine:** `re.sub(r'[\x00-\x08\x0B-\x1F\x7F-\x9F]', '', t)`: remove control characters, including the carriage
   return; keep tab and newline.

```python
import re

def medicine_a2(text):
    return re.sub(r"[\x00-\x08\x0B-\x1F\x7F-\x9F]", "", text)
```

3. **Action:** fix.
4. **Harm test:** author's version, gold set of 50 documents: changed 0, dropped 0. **This code: not run yet.**

## Medicine 2: G1 - cut at the vowel sign

1. **Disease:** G1.
2. **Medicine:** remove a space before a Bengali vowel sign or virama: `re.sub(r' ([া-্ৗ])', r'\1', t)`.
   `া-্` is `া` to `্`, and `ৗ` is `ৗ`, as in the author's pattern.

```python
import re

def medicine_g1(text):
    return re.sub(r" ([া-্ৗ])", r"\1", text)
```

3. **Action:** fix.
4. **Harm test:** author's version, gold set of 50 documents: changed 0, dropped 0. **This code: not run yet.**

## Medicine 3: C2 - repeated lines

1. **Disease:** C2.
2. **Medicine:** keep only the first copy of any line longer than 20 characters that appears 3 or more times.
   Choice to confirm: lines are compared exactly as written (no trimming), and "longer than 20" counts characters.

```python
from collections import Counter

def medicine_c2(text):
    lines = text.split("\n")
    counts = Counter(line for line in lines if len(line) > 20)
    seen, kept = set(), []
    for line in lines:
        if len(line) > 20 and counts[line] >= 3:
            if line in seen:
                continue
            seen.add(line)
        kept.append(line)
    return "\n".join(kept)
```

3. **Action:** fix.
4. **Harm test:** author's version, gold set of 50 documents: changed 0, dropped 0. **This code: not run yet.**

## Medicine 4: D3 - mixed language

1. **Disease:** D3.
2. **Medicine:** Latin share = Latin letters / (Latin + Bengali letters), as in
   `len(re.findall(r'[A-Za-z]', t)) / max(1, len(re.findall(r'[A-Za-zঀ-৿]', t)))`. Keep natural code-mixing; drop only
   if the Latin share is above 0.5. `ঀ-৿` is `ঀ` to `৿`, the Bengali block, as in the author's pattern.

```python
import re

def medicine_d3(text):
    latin = len(re.findall(r"[A-Za-z]", text))
    letters = len(re.findall(r"[A-Za-zঀ-৿]", text))
    return latin / max(1, letters) > 0.5   # True = drop the document
```

3. **Action:** drop (only above 0.5).
4. **Harm test:** author's version, gold set of 50 documents: changed 0, dropped 0. **This code: not run yet.**

## Medicine 5: C5 - lists of keywords or links

1. **Disease:** C5.
2. **Medicine:** drop if more than 60% of lines are short (fewer than 4 words) and contain no sentence end (`।` `.` `?` `!`).
   Choice to confirm: blank lines are not counted as lines.

```python
import re

def medicine_c5(text):
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        return False
    listy = sum(1 for line in lines if len(line.split()) < 4 and not re.search(r"[।.?!]", line))
    return listy / len(lines) > 0.6   # True = drop the document
```

3. **Action:** drop.
4. **Harm test:** author's version, gold set of 50 documents: changed 0, dropped 0. **This code: not run yet.**

## Medicine 6: G2 - lost ZWJ (version 2)

1. **Disease:** G2.
2. **Medicine:** at the start of a word only, `র্যা` becomes `র‍্যা` (ZWJ restored), as in র‍্যাব and র‍্যালি:
   `re.sub(r"(?<![ঀ-৿])র্যা", "র‍্যা", t)`. `র্যা` is `র্যা`; the replacement puts `‍` (ZWJ) after
   `র`, as in the author's replacement.

```python
import re

def medicine_g2(text):
    return re.sub(r"(?<![ঀ-৿])র্যা", "র‍্যা", text)
```

3. **Action:** fix.
4. **Harm test:** author's version 2, gold set of 50 documents: changed 0, dropped 0. **This code: not run yet.**
5. **Note for reviewers:** this rule adds a ZWJ on purpose: it restores one that was lost. A joiner-count audit sees
   the count go up on every document it fixes; that is the repair, not damage.

## Medicine 7: C3 - truncated document (version 2)

1. **Disease:** C3.
2. **Medicine:** only if the last line has 8 or more words and the text does not end with `।` `.` `?` `!` `"` or `)`:
   remove the incomplete last sentence. Choices to confirm: trailing spaces and newlines are ignored when finding the
   end; the incomplete sentence is everything after the last `।` `.` `?` or `!`; if the text has no such mark at all,
   it is kept unchanged rather than emptied.

```python
import re

def medicine_c3(text):
    body = text.rstrip()
    last_line = body.split("\n")[-1]
    if len(last_line.split()) < 8 or body.endswith(("।", ".", "?", "!", '"', ")")):
        return text
    ends = [m.end() for m in re.finditer(r"[।.?!]", body)]
    if not ends:
        return text
    return body[:ends[-1]]
```

3. **Action:** fix.
4. **Harm test:** author's version 2, gold set of 50 documents: changed 1 (`6fb6f2b0a3cec116`), dropped 0. The author
   marked this FAIL, but the course limit is max(1 document, 1%), so 1 of 50 is a **PASS**. **This code: not run yet.**

## Not rewritten yet: they need the author's detail

- **C1:** the sheet gives one example pattern (`^(শেয়ার করুন|Share|আরও পড়ুন|Read more|Follow us).*$`, "e.g."). The full
  list of phrases is needed.
- **A3:** the sheet says to re-decode "the broken span" with `encode('latin-1').decode('utf-8')`; how the span is found
  is not given.
- **D2:** the romanised word list is given only as examples (ami, tumi, kemon, achhe).

## No automatic rule

D4, C4 and D5 are flags for review (a fluency score or a topic-change check), not rules.
