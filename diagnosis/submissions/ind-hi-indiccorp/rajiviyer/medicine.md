# Medicine sheet: ind-hi-indiccorp (rajiviyer)

500 documents reviewed: 439 clean, 45 fix, 16 drop.
Disease counts: F1: 25, C3: 16, D4: 6, C1: 7, A3: 5, C4: 5,
D3: 3, D2: 2, G1: 2, C5: 1. A document can have several codes.

Findings that do not match a defined disease, including minor spelling, grammar
and spacing errors, are marked clean with comments in notes. Clean therefore
means no applicable disease found, not error-free writing. English names,
technical units and bracketed name/term glosses alone are not treated as D3;
romanised Hindi and substantial Hindi-English mixing are recorded separately.

The automatic rules below are prototypes tuned on this pack. Test results cover
all 425 documents in the updated published gold set for this pack.
This is not a held-out test or a claim of complete cleaning.
Each rule takes original text only, with no document IDs or supplied span lists.
Run these rules before any NFC conversion, which can shift character offsets.

## F1: Personal data

**Disease:** F1

### Examples

25 documents are labelled F1. Evidence gives types and zero-based character
offsets only; no personal values or hex are reproduced.

- `f9000a9730dae0f2`: phone number at offset 19.
- `954b27485b7c0a57`: private-person identity and residential details at offsets 16 and 99.
- `2b7609cd44409223`: school/locality at 0, child and parent identity at 71,
  further school details at 281 and child identity at 330.

### Rule and action

Fix by masking phone-like numbers and limited name/parentage/residence patterns
with `[REDACTED]`. A small filter avoids some generic uses of निवासी. The rule
does not drop documents. Public professional names should not be removed blindly.

```python
import re

_PHONE = re.compile(r"(?<![\d.,])(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
_TOKEN = r"[^\s,।.()]+"
_RESIDENT = re.compile(rf"{_TOKEN}(?:\s+{_TOKEN})?\s*(?:\(\s*\d{{1,3}}\s*\)\s*)?(?:(?:पुत्र|पुत्री|पत्नी)\s+{_TOKEN}(?:\s+{_TOKEN})?\s+)?निवासी\s+{_TOKEN}(?:\s+{_TOKEN})?")
_NOT_PERSON = re.compile(r"(?:मूल|स्थानीय|के|का|की|में|से)\s+निवासी|निवासी\s+(?:ही|नहीं|हैं|है)")

def medicine_f1(text):
    text = _PHONE.sub("[REDACTED]", text)
    return _RESIDENT.sub(lambda m: m.group(0) if _NOT_PERSON.search(m.group(0)) else "[REDACTED]", text)
```

### Harm test

| Gold documents | Changed | Dropped | Affected | Result at 1% |
| --- | --- | --- | --- | --- |
| 425 | 1 | 0 | 0.24% | PASS |

ZWJ/ZWNJ and normal-form checks passed on changed text.
The changed document is `e11903157ed9b336`.

Coverage against the current labels: the rule acts on 14 of 25 F1 documents
and one clean document, `e11903157ed9b336`. Eleven F1 documents are missed.
The action on the clean document is a false positive under the final review.
A match does not guarantee that every personal detail has been removed.
Human review or a better entity detector is still required.

### Possible mistakes

- Dates or other numbers may resemble phones.
- The limited residence pattern can miss or incompletely mask names and places.
- Repeated names, family relationships and sensitive details can remain identifying.
- The rule changes one document accepted as clean. Review matches before applying them.
- Results on this pack do not establish the error rate on new data.

## C1: Boilerplate

**Disease:** C1

### Examples

Seven documents contain C1.

- `7f8cfa9789fcd35a`: "Also Read - Viral Video:" at offset 416.
- `30bb38cf2f84eed7`: "Also Read -" at offset 310.
- `d3ec691647a71ee4`: "पढ़ें पूरी खबर" at offset 272.

### Rule and action

Fix by removing matching end-of-text recommendation controls and a limited set
of leading listen/photo markers. Other markers and joined articles need review.

```python
import re

_C1_TAIL = re.compile(r"\s*(?:Also Read\s*-|पढ़ें पूरी खबर\s*$)[^\n]*$")
_C1_HEAD = re.compile(r"^\W*(?:पूरी खबर सुने|फोटो-{3,}\S*(?:\s+\S+){0,3}?)\s+")

def medicine_c1(text):
    return _C1_HEAD.sub("", _C1_TAIL.sub("", text))
```

### Harm test

| Gold documents | Changed | Dropped | Affected | Result at 1% |
| --- | --- | --- | --- | --- |
| 425 | 0 | 0 | 0.00% | PASS |

Coverage: acts on 5 of 7 C1 documents, with no actions on other labelled rows.
No changed gold documents were available to exercise joiner/form preservation.

### Possible mistakes

- A quoted marker may be useful article content.
- A pattern may remove too much text after a marker or miss multiline controls.
- Removing boilerplate does not recover missing text or separate joined articles.

## C3: Truncated documents

**Disease:** C3

### Examples

16 documents contain C3.

- `79b479e5b5911e1c`: "लेकिन जुलाई खत्म होने को आया, य" at offset 301.
- `03a2a8b37cd767ef`: "देवताओं ने भगवान की" at offset 418.
- `5b08a22cbcafb46a`: "जानते हैं मॉनसून" at offset 381; promised tips are absent.

### Rule and action

Recover the source continuation where possible. Otherwise this prototype keeps
the text through the last sentence boundary for teaser endings such as ellipsis,
dash or colon; it drops the document if no such boundary exists. For other
unpunctuated endings, it drops text ending in a short/function word. Empty text
is left alone. It returns text to fix, True to drop, or False to keep.

The label remains a human reading decision: this heuristic does not detect all
truncation. Review the kept passage to ensure it makes sense on its own.

```python
import re

_C3_PUNCT = "।.!?॥\"'”’)]|:I"
_C3_FUNC = {"की", "के", "का", "कि", "को", "में", "पर", "से", "ने", "और", "या", "व", "तो", "भी", "ही", "हुए", "वाले"}

def medicine_c3(text):
    end = text.rstrip()
    if not end:
        return False
    if end.endswith(("…", "...", "-", "—", ":")):
        cut = max(end.rfind("।"), end.rfind(". "), end.rfind("? "), end.rfind("! "))
        return end[:cut + 1] if cut > 0 else True
    if end[-1] in _C3_PUNCT or end[-1].isdigit():
        return False
    last = end.split()[-1]
    return len(last) <= 2 or last in _C3_FUNC
```

### Harm test

| Gold documents | Changed | Dropped | Affected | Result at 1% |
| --- | --- | --- | --- | --- |
| 425 | 0 | 0 | 0.00% | PASS |

Coverage: acts on 13 of 16 C3 documents, with no actions on other labelled rows.
No changed gold documents were available to exercise joiner/form preservation.

### Possible mistakes

- Short words, headings, dialogue and intentional excerpts can trigger false drops.
- Decimal points, abbreviations and punctuation can produce a wrong cut point.
- Complete-looking punctuation may hide an incomplete document; three labelled
  cases are missed. Source recovery is better than guessing missing text.

## D4: Bad machine translation

**Disease:** D4

### Examples

Six documents contain D4.

- `5dd727a460cad090`: "सह-लेटरल" at offset 29 and "सह-अक्षर मुक्त ऋण" at 178.
- `768303341eb0e28e`: "एक धमाके की धड़कन" at offset 252.
- `4724780d3ef785bc`: "भविष्य के पुरस्कार प्रदान करेगी" at offset 21; "एजेंट को दूसरों को सलाह देंगे" at offset 230; literal wording distorts the intended meaning.

### Rule and action

A fluent Hindi reader checks for mistranslations that make the meaning wrong
or unclear. Compare the original source where available. Minor spelling,
grammar errors, loanwords and unfamiliar technical terms alone are not enough
to mark D4.

**Fix** when the intended meaning can be verified from the source. **Drop**
when the meaning is badly damaged and a reliable correction is unavailable.
Otherwise, keep the document.

This is a manual review rule. There is no automatic D4 detector, and the
official harm-test tool does not test it.

### Harm test: manual review

I manually checked the earlier 130-document gold set for clear translation
errors. Minor spelling, grammar and spacing mistakes were not treated as D4.

| Gold documents | Changed | Dropped | Affected | Manual result at 1% |
| --- | --- | --- | --- | --- |
| 130 | 0 | 0 | 0.00% | PASS |

No gold documents were excluded. No text was changed, so ZWJ/ZWNJ and normal
form were unchanged.

This result covers manual D4 review only. There is no automatic D4 detector.
It has not been extended to the updated 425-document gold set.

### Possible mistakes

- Technical or formal Hindi can be mistaken for bad translation.
- A plausible rewrite may change the source meaning.
- Readers may disagree; obtain a second fluent review for uncertain cases.

## Other diseases and observations

A3: 5; C4: 5; D3: 3; D2: 2; G1: 2; C5: 1. These do not exceed five
occurrences, so separate medicine sections are not required.

G1 includes `f6d6895afbe7d2f1` (document 380): a malformed virama followed
by a vowel sign at offsets 355-356 (`U+094D U+0940`) in इंस्ट्ीट्यूट.
Verify the source before correcting it; the cause of the damage is unknown.

For A3, suspected legacy-font damage is recorded under the closest code; the
exact cause is not established. Check sources before changing characters.
Shifted-nukta spellings also appear in `29b9313c01b1ca8d` and
`5e80298a68d26e06`; these remain clean under the chosen spelling policy.
Possible missing anusvara is noted without a disease label in
`df88a94dfa78e5d1`, `7d8d2eea7b66d210`, `f6ef705ed9db26bc`,
`9d31cd38c41fa33e`, `b0027bae44bdb50b` and `90e2f77e4c43828c`.

Check sources before splitting C4 documents. `da9a77345e9eaa4c` is retained as
clean because its cyclone aside may relate to the satellite launch.
Preserve ZWJ/ZWNJ; no general encoding-repair or document-splitting rule is tested.

## Gold-set scope

Automatic test: `teams/02-data-b/tools/harm_test_indic.py`, using
`teams/02-data-b/gold/ind-hi-indiccorp_gold.csv` from upstream main commit
`ea7b53353e9869f257b14a187f735735ab1306a8`. All 425 published IDs were used,
unchanged, against the original pack. No IDs were excluded.

The test is per pack; gold documents from other Hindi packs were not tested.
The F1 change to `e11903157ed9b336` counts as a false positive and remains
included in the harm result.

F1, C1 and C3 together change 1/425 (0.24%) and drop 0: PASS at 1%.
ZWJ/ZWNJ and normal-form audits passed. D4 manual review used the earlier
130-document gold set from commit `5a1c5f3d5b0bc0a292503ea1689049ac9d415e73`.
These automatic-rule results are separate from the manual D4 result above.
Low observed harm does not establish complete redaction or held-out quality.
The automatic rules were tuned using this same pack.
