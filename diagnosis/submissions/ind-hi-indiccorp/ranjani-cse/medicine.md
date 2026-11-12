# Medicine sheet: ind-hi-indiccorp (ranjani-cse)

Three diseases found more than five times in the 500-document pack.

## Medicine 1

1. **Disease:** C3 (truncated document), 11 cases.
   Examples:
   - c1204f56ddf72d2e ends with ... at offset ~370
   - 6404b661ab7d5119 ends at ...शिक्षक बलराम कौशिक ने बताया कि offset ~480
   - 88f8b9b04f3c44eb ends at ...करीब छह offset ~280

2. **Medicine:** drop only documents with a clear truncation signal.

```python
import re

def medicine_c3(text):
    t = text.rstrip()
    if len(t) < 300:
        return False
    last = t[-1]
    if last == "…":
        return True
    if re.match(r"[\u093E-\u094C\u094D\u0962\u0963]", last):
        return True
    return False
```

3. **Action:** drop the document.

4. **Harm test:** changed 0 / dropped 1 of 425 gold docs (0.24%) — PASS

5. **Side effects:** may drop legitimate documents ending in an ellipsis.

## Medicine 2

1. **Disease:** G1 (cut at the vowel sign), 17 cases.
   Examples:
   - 7ee85435bb1db370 बच्चो at ~180, missing anusvara
   - 45faba24d7143976 स्वास्थ्य ा at ~340, split matra

2. **Medicine:** flag a matra or virama standing alone at a word boundary.

```python
import re

SPLIT_MATRA_G1 = re.compile(r"(?<=\s)[\u093E-\u094C\u094D\u0962\u0963](?=\s|$)")

def medicine_g1(text):
    if len(text) < 100:
        return False
    return bool(SPLIT_MATRA_G1.search(text))
```

3. **Action:** fix where possible; drop if extensive.

4. **Harm test:** changed 0 / dropped 0 of 425 gold docs (0.00%) — PASS

5. **Side effects:** may flag abbreviations.

## Medicine 3

1. **Disease:** G3 (machine-translated or generated text), 6 cases.
   Examples:
   - 89a31fc1bec0f40d repeated के कारण, unnatural MT syntax
   - 7a354dffcf84e4d4 Italian sailing-school text machine-translated into Hindi

2. **Medicine:** high Latin ratio with no sentence terminator, or repeated के कारण.

```python
import re

LATIN_G3 = re.compile(r"[A-Za-z]")
TERM_G3  = re.compile(r"[।!?]")

def medicine_g3(text):
    if len(text) < 300:
        return False
    latin_ratio = len(LATIN_G3.findall(text)) / len(text)
    no_sentence = not TERM_G3.search(text)
    repeated = text.count("के कारण") > 5
    return (latin_ratio > 0.15 and no_sentence) or repeated
```

3. **Action:** drop the document.

4. **Harm test:** changed 0 / dropped 0 of 425 gold docs (0.00%) — PASS

5. **Side effects:** may drop Hindi news quoting English terms heavily.
