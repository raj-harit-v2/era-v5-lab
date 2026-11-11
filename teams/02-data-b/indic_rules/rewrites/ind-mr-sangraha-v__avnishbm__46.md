# Rewrite in the harm tool's format: ind-mr-sangraha-v, avnishbm (PR #46)

TSAI ruling 3 on #211 (3 Nov): the Data B rules owner may rewrite a medicine sheet that `harm_test_indic.py` cannot
read, and the author must OK the rewrite in their PR. **Author OK: pending.**

What changed: each automatic medicine gets a `**Disease:** <code>` line and this layout. The code is the author's,
copied unchanged from PR #46 at `cb12ee6`. Counts and wording are the author's.

**Gold set.** The author pinned `teams/02-data-b/gold/ind-mr-sangraha-v_gold.csv` at commit `74b2886`. Checked on 3 Nov:
it holds the same 88 doc_ids as the file on main today (`a8ae686`), so the author's harm result is on today's gold set
of this pack.

## Medicine 1: A6 - wrong or mixed script

1. **Disease:** A6. 14 documents in the pack.
2. **Medicine:** Fix only the repeated OCR pattern `º` immediately before Devanagari `य`; replace it with `ऱ्`. Other A6
   characters, such as a Latin letter inside a Marathi word, remain manual cases.

```python
import re

def fix_reviewed_ordinal_ocr(text: str) -> str:
    return re.sub(r"º(?=य)", "ऱ्", text)
```

3. **Action:** fix.
4. **Harm test:** gold set of 88 documents (ind-mr-sangraha-v 88): changed 0, dropped 0 (0.00%). **PASS** (author's run, PR #46).
5. **Side effects:** A legitimate ordinal indicator before Devanagari text would be changed; mixed-script cases outside
   this exact pattern are not fixed. Note for reviewers: `ऱ` (U+0931) decomposes to `र` + nukta under NFD, so a nukta
   count taken after NFD goes up by one for each fix. That is the intended repair, not damage.

## Medicine 2: D3 - mixed language

1. **Disease:** D3. 77 documents in the pack.
2. **Medicine:** Preserve natural code switching, names, quotations, acronyms and technical terms. Remove a
   mixed-language span only when it is independently confirmed as C1/C5 clutter.

```python
def preserve_contextual_mixing(text: str) -> str:
    return text
```

3. **Action:** keep (the rule changes no text).
4. **Harm test:** gold set of 88 documents (ind-mr-sangraha-v 88): changed 0, dropped 0 (0.00%). **PASS** (author's run, PR #46).
5. **Side effects:** Blanket English removal or translation destroys legitimate Marathi usage. D3 is descriptive and
   requires contextual review.

## Not rewritten: they need a reviewer's decision

B4, C1, C3, C4, C5, D4 and F1 in PR #46 take a second input that a reviewer must supply (for example
`confirmed_b4: bool` or a list of confirmed spans). They cannot run on text alone, so they are not automatic rules
and are not rewritten here.
