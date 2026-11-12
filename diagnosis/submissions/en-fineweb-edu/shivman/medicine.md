# Medicine sheet: en-fineweb-edu (shivman)

One section for each disease found more than five times. The counts are from all 500 rows in labels.csv.

The harm test for each medicine is the gold set on main, teams/01-data-a/gold/en-fineweb-edu_gold.csv. That file has 158 documents, and all 158 are in this pack. A medicine that changes or drops more than 1 percent of those 158 documents fails.

## Medicine 1

1. **Disease:** C1, 83 documents. Three examples: 469e0a5a812c28f3, 'SEE ALSO' at offset 8737. 74ea30694d60f739, 'Bible History Online' at offset 9061. f6393483c601faf0, 'View all Kids Bikes' at offset 3833.
2. **Medicine:** In the last eight lines, delete a line that is site chrome. The rule is the function c1_line below. A bare copyright line is left in place, because that line also appears on documents read as clean.
3. **Action:** fix. The matched line is removed. The rest of the document stays.
4. **Harm test:** On the gold set, 0 of 158 documents change, and 0 are dropped. That is 0.00 percent, so the medicine passes the 1 percent bar. On the whole pack it changes 36 of 500 documents and removes 5,512 of 2,442,877 characters (0.23 percent).
5. **Side effects:** A "See also" inside a sentence is kept, because the rule requires the start of a line. A picture credit that is only a copyright line is kept. Related titles that do not use these phrases are kept.

## Medicine 2

1. **Disease:** C5, 19 documents. Three examples: a14b25405c278a3b, 'Recreation and Sports' at offset 2574. 4f71a74567f4d4aa, 'Part Eleven' at offset 14101. 7105413375448daa, 'Multicore myopathy' at offset 5476.
2. **Medicine:** In the last eight lines, delete a line that is a related-search heading, a "Filed under" tag line, or a row of single letters. The rule is c5_line below.
3. **Action:** fix. The matched line is removed. The rest of the document stays.
4. **Harm test:** On the gold set, 0 of 158 documents change, and 0 are dropped. That is 0.00 percent, so the medicine passes the 1 percent bar. On the whole pack it changes 3 of 500 documents and removes 342 of 2,442,877 characters (0.01 percent).
5. **Side effects:** A real list that is the subject of the page, such as a chronology or a set of course names, is kept. A broader rule for short lines also hits documents read as clean, so those lists are not removed.

## Medicine 3

1. **Disease:** C3, 13 documents. Three examples: 2067313a5e000336, 'He writes in the Guardian on Tuesday:' at offset 2551. 3054e5cb9e7109dc, 'also available on:' at offset 1013. 8620d74ba9ae6cdc, 'about the collection, visit' at offset 3346.
2. **Medicine:** If the last 200 characters contain "Continue reading", "View Full Document", or "Provided Courtesy of:", delete from that phrase to the end. If the text ends with a colon or with an ellipsis character, delete the last line. The rule is c3_trim below.
3. **Action:** fix. The unfinished ending is removed. The rest of the document stays.
4. **Harm test:** On the gold set, 0 of 158 documents change, and 0 are dropped. That is 0.00 percent, so the medicine passes the 1 percent bar. On the whole pack it changes 9 of 500 documents and removes 801 of 2,442,877 characters (0.03 percent).
5. **Side effects:** Three dots used as a pause inside a finished sentence are kept. A cut word that is not one of these phrases is kept, because a rule based on the final letter also hits documents read as clean.

## Medicine 4

1. **Disease:** F1, 11 documents. Three examples, type and position only: 841da1d7e68b3ab8, phone at offset 1597. 5e224eade2a833db, phone at offset 2050. 6a515f44bd213b3d, phone at offset 7177.
2. **Medicine:** Delete an email address or a North American phone number. The value is not stored. The rule is f1_spans below.
3. **Action:** fix. The matched span is removed. The rest of the document stays.
4. **Harm test:** On the gold set, 0 of 158 documents change, and 0 are dropped. That is 0.00 percent, so the medicine passes the 1 percent bar. On the whole pack it changes 8 of 500 documents and removes 281 of 2,442,877 characters (0.01 percent).
5. **Side effects:** A number written as "Tel:" plus an international number, or as "1-800" plus letters, is not matched. Those stay for a person to remove. A year or a page number is not matched.

## Code

```python
import re

C1_LINE = re.compile(
    r"(?im)(all rights reserved|click here to|explore further|"
    r"^see also\s*($|:|/)|sign up for|related searches|continue reading|"
    r"last updated:|follow us on|read more at |read more by |read more »|"
    r"subscribe to our|back to gallery|ask a question|book a holiday|"
    r"customer reviews|vault profile|view full document|"
    r"other posts in this series|citation styles|picture sources:|"
    r"get grist in your inbox|provided courtesy of:|creative commons licensed)"
)
C5_LINE = re.compile(r"(?im)(^related searches|^filed under:|^[A-Z]( [A-Z]){8,}\s*$)")
C3_MARK = re.compile(r"(?i)continue reading|view full document|provided courtesy of:")
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+\d{1,3}[\s\-])?(?:\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4})\b")


def c1_line(text: str) -> str:
    lines = text.splitlines()
    head, tail = (lines[:-8], lines[-8:]) if len(lines) > 8 else ([], lines)
    kept = [ln for ln in tail if not (ln.strip() and C1_LINE.search(ln.strip()))]
    return "\n".join(head + kept)


def c5_line(text: str) -> str:
    lines = text.splitlines()
    head, tail = (lines[:-8], lines[-8:]) if len(lines) > 8 else ([], lines)
    kept = [ln for ln in tail if not C5_LINE.search(ln.strip())]
    return "\n".join(head + kept)


def c3_trim(text: str) -> str:
    body = text.rstrip("\n")
    window = body[-200:]
    mark = C3_MARK.search(window)
    if mark:
        start = len(body) - len(window) + mark.start()
        return body[:start].rstrip()
    if body.endswith(":") or body.endswith("…"):
        cut = body.rfind("\n")
        return body[:cut].rstrip() if cut >= 0 else ""
    return body


def f1_spans(text: str) -> str:
    out = EMAIL.sub("", text)
    return PHONE.sub("", out)
```
