# medicine_english: compiled English medicines

Packs: dclm 62, fineweb-edu 158, nemotroncc 34, synth 96 gold docs (Data A gold, `teams/01-data-a/gold/`). Each pack is tested on its own gold set, and every rule runs on every English pack.
Rule form: `RULE_ID`, `CODE`, `ACTION`, `STAGE`, `STATUS`, `LANGS`, `ORIGIN`, `SOURCE`, `AUTHOR`; `medicine(doc) -> (action, text)`, `doc = {doc_id, text, url, lang_label}`. A row outside `LANGS` passes unchanged. Same form as `medicine_code.md`. `AUTHOR` is a code field the team's `medicine_conflicts.py` reads; it is not used in the text.
Run order is section order, by stage: 10 characters, 20 markup, 30 drops, 35 strips, 40 data safety. An annotator's code is copied unchanged: only the definitions the rule uses. What is added is marked `# added by Data A`: the imports or constants their code uses but their rules file never defines (taken from their own `medicine.md`), `_std` (their result in the shared form) and the `LANGS` guard. Each block gives the same result as the author's own function on all 2,000 English documents (`results/equivalence_english.json`).
IDs: Data A registry after running the extractor on the latest sheets. New rules take the next free number after the registry and PR 16's code sheet. All IDs are provisional until the team commits the registry.
Assumption: the language tag on a row is correct. No language detector runs.
F1 is `DA-F1-005`, written to the instructor's F1 ruling of 31 Oct, and is never left out. The shared `../tools/f1_rule.py` does not run on English (`_F1_LANGS`), so `../tools/build_clean.py` keeps this sheet's own F1 and `clean_english.py` runs it on `en` and `eng` text, last.
Tested on `g1-harm-test` at `bae5163`. Limit: changed + dropped at most `max(1, floor(1% of gold))`. Why each rule was picked, for each disease: `decisions_english.md`.

| pack | gold sha256 | pack sha256 |
|---|---|---|
| dclm | `8165439648189b96` | `d5ae1e7e991de478` |
| fineweb-edu | `a06212a5f4952b9b` | `3a0ad16983c03e9d` |
| nemotroncc | `0175e5d0afa8d661` | `6eae1507bc689c79` |
| synth | `72216094cbebbf7b` | `0f1c3a9866ada7fb` |

Each cell: gold harm % (gold docs changed or dropped / gold docs), the result at the limit, and the labelled rows the rule treats / the labelled rows with its code.

| # | ID | disease | action | stage | source | dclm | fineweb-edu | nemotroncc | synth |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `DA-A1-004` | A1 invisible junk characters | fix | 10 | en-dclm | 0.00% (0/62) PASS · 11/12 | 0.00% (0/158) PASS · 0/1 | 0.00% (0/34) PASS · 14/14 | 0.00% (0/96) PASS · 0/0 |
| 2 | `DA-A2-008` | A2 control characters | fix | 10 | all | 0.00% (0/62) PASS · 3/3 | 0.00% (0/158) PASS · 0/0 | 0.00% (0/34) PASS · 0/0 | 0.00% (0/96) PASS · 0/0 |
| 3 | `DA-A5-001` | A5 wrong normal form | fix | 10 | all | 0.00% (0/62) PASS · 3/3 | 0.00% (0/158) PASS · 0/0 | 0.00% (0/34) PASS · 0/0 | 0.00% (0/96) PASS · 0/0 |
| 4 | `DA-A3-002` | A3 mojibake | fix | 10 | en-dclm | 0.00% (0/62) PASS · 4/7 | 0.00% (0/158) PASS · 1/4 | 0.00% (0/34) PASS · 0/4 | 0.00% (0/96) PASS · 0/0 |
| 5 | `DA-B1-002` | B1 HTML entities | fix | 20 | all | 0.00% (0/62) PASS · 1/1 | 0.00% (0/158) PASS · 0/0 | 0.00% (0/34) PASS · 0/3 | 0.00% (0/96) PASS · 0/0 |
| 6 | `DA-B2-002` | B2 HTML or XML tags | fix | 20 | all | 0.00% (0/62) PASS · 1/3 | 0.00% (0/158) PASS · 1/1 | 0.00% (0/34) PASS · 0/1 | 0.00% (0/96) PASS · 0/0 |
| 7 | `DA-C3-001` | C3 truncated document | drop | 30 | en-dclm | 0.00% (0/62) PASS · 1/103 | 0.00% (0/158) PASS · 0/35 | 0.00% (0/34) PASS · 5/101 | 0.00% (0/96) PASS · 0/50 |
| 8 | `DA-C3-002` | C3 truncated document | drop | 30 | en-dclm | 0.00% (0/62) PASS · 3/103 | 0.00% (0/158) PASS · 1/35 | 0.00% (0/34) PASS · 8/101 | 0.00% (0/96) PASS · 0/50 |
| 9 | `DA-C5-002` | C5 lists of keywords or links | drop | 30 | en-dclm | 0.00% (0/62) PASS · 4/61 | 0.00% (0/158) PASS · 0/30 | 0.00% (0/34) PASS · 0/71 | 0.00% (0/96) PASS · 0/7 |
| 10 | `DA-D4-001` | D4 bad machine translation | drop | 30 | en-dclm | 0.00% (0/62) PASS · 1/21 | 0.00% (0/158) PASS · 0/3 | 0.00% (0/34) PASS · 0/17 | 0.00% (0/96) PASS · 0/2 |
| 11 | `DA-C1-006` | C1 boilerplate | fix | 35 | en-nemotroncc | 0.00% (0/62) PASS · 6/389 | 0.00% (0/158) PASS · 2/308 | 0.00% (0/34) PASS · 27/161 | 0.00% (0/96) PASS · 1/76 |
| 12 | `DA-C2-003` | C2 repeated lines | fix | 35 | en-fineweb-edu | 0.00% (0/62) PASS · 18/38 | 0.00% (0/158) PASS · 1/6 | 0.00% (0/34) PASS · 7/39 | 0.00% (0/96) PASS · 1/1 |
| 13 | `DA-C5-005` | C5 lists of keywords or links | fix | 35 | all | 0.00% (0/62) PASS · 0/61 | 0.00% (0/158) PASS · 2/30 | 0.00% (0/34) PASS · 1/71 | 0.00% (0/96) PASS · 0/7 |
| 14 | `DA-D3-003` | D3 mixed language | fix | 35 | en-nemotroncc | 0.00% (0/62) PASS · 3/24 | 0.00% (0/158) PASS · 1/5 | 0.00% (0/34) PASS · 2/6 | 0.00% (0/96) PASS · 0/1 |
| 15 | `DA-B4-007` | B4 template and code junk | fix | 40 | en-nemotroncc-synth | 0.00% (0/62) PASS · 0/25 | 0.00% (0/158) PASS · 0/8 | 0.00% (0/34) PASS · 0/15 | 0.00% (0/96) PASS · 8/36 |
| 16 | `DA-B4-008` | B4 template and code junk | fix | 40 | en-nemotroncc-synth | 0.00% (0/62) PASS · 0/25 | 0.00% (0/158) PASS · 0/8 | 0.00% (0/34) PASS · 0/15 | 0.00% (0/96) PASS · 17/36 |
| 17 | `DA-B4-009` | B4 template and code junk | fix | 40 | en-dclm | 0.00% (0/62) PASS · 5/25 | 0.00% (0/158) PASS · 0/8 | 0.00% (0/34) PASS · 0/15 | 0.00% (0/96) PASS · 0/36 |
| 18 | `DA-B4-010` | B4 template and code junk | fix | 40 | en-fineweb-edu | 0.00% (0/62) PASS · 0/25 | 0.00% (0/158) PASS · 1/8 | 0.00% (0/34) PASS · 0/15 | 0.00% (0/96) PASS · 0/36 |
| 19 | `DA-B4-011` | B4 template and code junk | fix | 40 | en-nemotroncc-synth | 0.00% (0/62) PASS · 0/25 | 0.00% (0/158) PASS · 0/8 | 0.00% (0/34) PASS · 0/15 | 0.00% (0/96) PASS · 1/36 |
| 20 | `DA-F1-005` | F1 personal data | fix | 40 | en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth | 0.00% (0/62) PASS · 2/13 | 0.00% (0/158) PASS · 0/12 | 0.00% (0/34) PASS · 1/13 | 0.00% (0/96) PASS · 1/2 |

## 1. `DA-A1-004` · A1 invisible junk characters · fix · stage 10

1. **Disease:** A1 invisible junk characters. Labelled rows: dclm 12, fineweb-edu 1, nemotroncc 14, synth 0. Examples it treats: `10355b4f94c87a2c` (dclm), `11c3cd0e50856c3e` (dclm), `094e33117f3c3cd2` (nemotroncc).
2. **Medicine:** Delete the invisible characters named in the disease list. ZWJ (U+200D) and ZWNJ (U+200C) are **not** removed: they are part of Indic script and are not a disease. This pack is English, but the rule is written so it stays correct if it is ever reused on an Indic pack.

```python
RULE_ID = "DA-A1-004"
CODE = "A1"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_INVISIBLE = re.compile("[﻿​­‎‏‪-‮⁦-⁩]")

def medicine_a1(text):
    return _INVISIBLE.sub("", text)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a1(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 11 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 14 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** Removing a soft hyphen joins the two halves of a word, which is right for `never­ending` but wrong if a document ever used it as a real hyphen. Stripping bidi controls from a document that genuinely mixes right-to-left and left-to-right text would change how that text renders; there is no such document in this pack, but there would be in an Arabic or Hebrew one, and this medicine should not be reused there without a second look. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 2. `DA-A2-008` · A2 control characters · fix · stage 10

1. **Disease:** A2 control characters. Labelled rows: dclm 3, fineweb-edu 0, nemotroncc 0, synth 0. Examples it treats: `5d1fd12b101321f0` (dclm), `7b1d879aa4e04769` (dclm).
2. **Medicine:** Remove the control characters U+0000 to U+001F (except tab and newline) and U+007F to U+009F. A carriage return is a control character too: CRLF and a lone CR become a newline.

```python
RULE_ID = "DA-A2-008"
CODE = "A2"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-A2-007
import re

A2_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def medicine_a2(text):
    new = A2_CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_a2(doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 3 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A form feed used as a page break is removed, so the two pages run together. Every document with Windows line endings counts as changed.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-A2-007). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 3. `DA-A5-001` · A5 wrong normal form · fix · stage 10

1. **Disease:** A5 wrong normal form. Labelled rows: dclm 3, fineweb-edu 0, nemotroncc 0, synth 0. Examples it treats: `10355b4f94c87a2c` (dclm), `68575a61a90990d5` (dclm).
2. **Medicine:** Normalise the text to NFC, the form the lab uses.

```python
RULE_ID = "DA-A5-001"
CODE = "A5"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-A5-001
import re

import unicodedata


def medicine_a5(text):
    new = unicodedata.normalize("NFC", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_a5(doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 3 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The bytes of decomposed text change, not its look. A text about Unicode normalisation loses the difference between its examples.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-A5-001). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 4. `DA-A3-002` · A3 mojibake · fix · stage 10

1. **Disease:** A3 mojibake. Labelled rows: dclm 7, fineweb-edu 4, nemotroncc 4, synth 0. Examples it treats: `5d1fd12b101321f0` (dclm), `7b1d879aa4e04769` (dclm), `53dadf5fc6ee123a` (fineweb-edu).
2. **Medicine:** Detect the double-decoding signatures, repair with `ftfy.fix_text`, and drop the document only if the signature is still dense after repair (the bytes are gone, not just mis-decoded).

```python
RULE_ID = "DA-A3-002"
CODE = "A3"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "shekar-maker"  # extractor; adapter for (text, flag)
import re
import ftfy  # added by Data A: used, never imported (pip install ftfy)

A3_RE = re.compile(r"â€[\x80-\xbf‘-™]?|Ã[\x80-\xbf\u0080-ÿ]|Â[\xa0-\xbf]|[\x80-\x9f]")

def m_a3(text):
    if not A3_RE.search(text): return text, False
    new = ftfy.fix_text(text)
    return new, len(A3_RE.findall(new)) * 1000 / max(len(new), 1) > 1.0


def _std(out, text):  # added by Data A
    # the author's result (new_text, flag) in the shared form: flag -> drop (their sheet: "flag for drop"),
    # else fix/keep by the text
    new, flag = out
    if flag: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m_a3(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 4 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The signature regex misses mojibake that went through a non-UTF-8 round trip, for example Cyrillic `й` standing in for `é` (`Pokйmon` in `68575a61a90990d5`, `Diffйrents` in `467b5c0aa1d13de8`) and symbol-font gibberish (`3dc93ffbd87ba839`): 3 of the 7 labelled documents are not touched. `ftfy` can in rare cases "repair" legitimate text that happens to look like mojibake (`Ã` followed by a letter in Portuguese); the gold run will show whether that happens in English.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text, flag). Added: ftfy. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 5. `DA-B1-002` · B1 HTML entities · fix · stage 20

1. **Disease:** B1 HTML entities. Labelled rows: dclm 1, fineweb-edu 0, nemotroncc 3, synth 0. Examples it treats: `1992526bd6e98869` (dclm).
2. **Medicine:** Decode the common HTML entities (`&amp;`, `&nbsp;`, `&quot;`, `&lt;`, `&gt;`, dashes, quotes, `&#NNN;`, `&#xHH;`). `&nbsp;` becomes a plain space.

```python
RULE_ID = "DA-B1-002"
CODE = "B1"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-B1-002
import re

import html
import re

B1_ENTITY = re.compile(r"&(?:amp|nbsp|quot|apos|lt|gt|mdash|ndash|hellip|rsquo|lsquo|rdquo|ldquo|copy|reg|trade"
                       r"|#\d{2,6}|#x[0-9a-fA-F]{2,5});")


def medicine_b1(text):
    new = B1_ENTITY.sub(lambda m: html.unescape(m.group()).replace("\xa0", " "), text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_b1(doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 1 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A text that shows entities on purpose (an HTML tutorial) is changed. An entity that is not on the list stays.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-B1-002). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 6. `DA-B2-002` · B2 HTML or XML tags · fix · stage 20

1. **Disease:** B2 HTML or XML tags. Labelled rows: dclm 3, fineweb-edu 1, nemotroncc 1, synth 0. Examples it treats: `6d1051dc3ca46585` (dclm), `a845e6c52e035cbb` (fineweb-edu).
2. **Medicine:** Remove common HTML tags (`<div>`, `<p>`, `<br/>`, `<span ...>`, `<li>`, `<strong>`, ...) when the text has at least two of them and is not about HTML (no code fence, `class=`, `<!DOCTYPE`, or the words html, tag, element). A single tag is often a mention, not markup.

```python
RULE_ID = "DA-B2-002"
CODE = "B2"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-B2-002
import re

B2_TAG = re.compile(r"</?(?:div|span|p|br|li|ul|ol|img|table|tr|td|th|tbody|thead|strong|em|font|iframe|script|style|center|hr)"
                    r"(?:\s[^<>]{0,200})?\s*/?>", re.I)
B2_ABOUT_HTML = re.compile(r"```|\bclass\s*=|<!DOCTYPE|\bhtml\b|\btag\b|\belement\b", re.I)


def medicine_b2(text):
    if B2_ABOUT_HTML.search(text) or len(B2_TAG.findall(text)) < 2:
        return ("keep", text)
    new = re.sub(r"[ \t]{2,}", " ", B2_TAG.sub(" ", text))
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_b2(doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 1 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A text that quotes tags as examples without those words loses them. `<br>` and `<p>` become a space, not a line break, so lines can run together.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-B2-002). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 7. `DA-C3-001` · C3 truncated document · drop · stage 30

1. **Disease:** C3 truncated document. Labelled rows: dclm 103, fineweb-edu 35, nemotroncc 101, synth 50. Examples it treats: `52422fff81211f50` (dclm), `4f2fc39dee7af855` (nemotroncc), `5ef3f9c12c7a2608` (nemotroncc).
2. **Medicine:** Only the *stub* form is treated. A document of at most 600 characters whose last word is one no sentence ends on (`from`, `the`, `and`, ...) or that ends with a teaser `...` is dropped (the dangling-word test only applies when the text has no terminal punctuation).

```python
RULE_ID = "DA-C3-001"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "shekar-maker"  # extractor; adapter for (text, flag)
import re

DANGLING = set("a an the and or but of to in on at by for from with as that which who will would can could is are was were be been being has have had this these those its their his her my our your".split())

def m_c3(text, max_len=600):
    body = text.rstrip()
    if len(body) > max_len: return text, False
    last = (re.findall(r"[A-Za-z']+", body) or [""])[-1].lower()
    teaser = body.endswith(("...", "…", "[...]", "[…]", "(more)", "Read more"))
    unfinished = body[-1] not in ".!?\"')]}»”’:;" and last in DANGLING
    return text, bool(teaser or unfinished)


def _std(out, text):  # added by Data A
    # the author's result (new_text, flag) in the shared form: flag -> drop (their sheet: "flag for drop"),
    # else fix/keep by the text
    new, flag = out
    if flag: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m_c3(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 1 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 5 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** My first version trimmed any last line without terminal punctuation; it changed 5 of the 28 documents then in the proxy set (complete sentences that simply lack a full stop), so it was withdrawn. The stub rule's dangling-word test then dropped a clean 560-character document ending `...what research impact is.`, which failed the 1% limit on the 65-document proxy; it now applies only when the text has no terminal punctuation. The rule catches 1 of the 98 labelled documents, because in this pack C3 is mostly mid-text gaps where a link, a citation, a quote or an image was stripped by an earlier cleaner (the readers' notes say most C3 rows are of this kind, not end-of-document cuts). There is no safe regex for that; it is the main finding of this slice for the pipeline team: the HTML-to-text step drops anchor text and embedded content.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text, flag). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 8. `DA-C3-002` · C3 truncated document · drop · stage 30

1. **Disease:** C3 truncated document. Labelled rows: dclm 103, fineweb-edu 35, nemotroncc 101, synth 50. Examples it treats: `484c668df3c40868` (dclm), `52422fff81211f50` (dclm), `8262087c39b0c8c5` (fineweb-edu).
2. **Medicine:** Drop the document when it ends in an excerpt marker, or when the last word is a function word that cannot end an English sentence. Truncation cannot be repaired, and the tail is the only place it can be detected without guessing.

```python
RULE_ID = "DA-C3-002"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_MARKER = re.compile(r"\[\s*(?:…|\.\.\.)\s*\]$")

_DANGLING = frozenset(
    "a an the and or but of to in on at for with from by as is are was were "
    "that this these those which who because however".split()
)

_LAST_TOKEN = re.compile(r"([A-Za-z0-9']+)[^A-Za-z0-9']*$")

def medicine_c3(text):
    tail = text.rstrip()
    if not tail:
        return text
    if _MARKER.search(tail):
        return ("drop", "")
    if tail.endswith((".", "!", "?", '"', "'", ")", ":", "…")):
        return text
    token = _LAST_TOKEN.search(tail)
    if token and token.group(1).lower() in _DANGLING:
        return ("drop", "")
    return text


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c3(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 3 dropped, fineweb-edu 0 fixed, 1 dropped, nemotroncc 0 fixed, 14 dropped, synth 0 fixed, 1 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** It reads only the end of the document, so it misses truncation in the middle, which is where I found it in `a1b97fd910707a8d` and `5a6856a5e9397412` — there the extractor dropped link and image text and left the sentence around it standing. Those need a different medicine, and I have not written one. A document that genuinely ends on an ellipsis for effect would be dropped wrongly; I saw none in this pack, but it is the obvious failure. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 9. `DA-C5-002` · C5 lists of keywords or links · drop · stage 30

1. **Disease:** C5 lists of keywords or links. Labelled rows: dclm 61, fineweb-edu 30, nemotroncc 71, synth 7. Examples it treats: `0b139d9931d96986` (dclm), `1ec7fa64b9476242` (dclm).
2. **Medicine:** Drop the document when at least two different injected-keyword markers appear, or when a single line is a run of five or more short pipe-separated phrases. Two markers rather than one, because a page may mention a brand once for an honest reason.

```python
RULE_ID = "DA-C5-002"
CODE = "C5"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_SPAM = tuple(
    re.compile(p, re.I)
    for p in (
        r"\bcheap\s+(?:nfl|nba|mlb|nhl)\b",
        r"\bcheap\s+(?:michael\s+kors|oakley|ray\s*bans?|jerseys)\b",
        r"\bray\s*bans?\s+(?:sunglasses|outlet)\b",
        r"\b(?:auto|car)\s+insur\w*\s+(?:quotes?|qiotes?|rates?)\b",
        r"\bfree\s+auto\s+insurance\s+quotes\b",
        r"\bsex\s+dating\s+in\b",
        r"\bwrite\s+my\s+essay\b",
        r"\b(?:카지노|바카라|룰렛)\b",
        r"\bpigmentación\s+capilar\b",
    )
)

_KEYWORD_LINE = re.compile(r"^(?![ \t]*[•·*\-])(?:[^|\n]{2,40}\|){6,}[^|\n]{2,40}[ \t]*$", re.M)

def medicine_c5(text):
    hits = sum(1 for p in _SPAM if p.search(text))
    if hits >= 2 or _KEYWORD_LINE.search(text):
        return ("drop", "")
    return text


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c5(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 4 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The marker list is drawn from one pack of 500 English documents, so it will age badly — next year's spam sells something else. A genuine article about car insurance that quotes a spam phrase twice would be dropped. The pipe-separated test would also catch an honest table that survived extraction as a single line, though I saw none in this pack. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 10. `DA-D4-001` · D4 bad machine translation · drop · stage 30

1. **Disease:** D4 bad machine translation. Labelled rows: dclm 21, fineweb-edu 3, nemotroncc 17, synth 2. Examples it treats: `0a28e7f42a4bba02` (dclm).
2. **Medicine:** Drop the document when the mechanical residue of a spinner is still in the text: unused spintax alternatives in braces, or an essay-mill banner. I am not trying to detect spun prose itself.

```python
RULE_ID = "DA-D4-001"
CODE = "D4"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_SPINTAX = re.compile(r"\{[^{}\n]{2,60}\|[^{}\n]{2,60}\}")

_MILL = re.compile(r"\b(?:write my essay|essay writing service|buy essays? online)\b", re.I)

def medicine_d4(text):
    if _SPINTAX.search(text) or _MILL.search(text):
        return ("drop", "")
    return text


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_d4(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 1 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** This reaches only the documents where the spinner left its syntax behind. Finished spun text, which is most of what I labelled D4, reads as ordinary English to a regular expression and passes straight through — `3dce67ac37d56429` and `a55992c7a90ce4f4` are both missed. Detecting it properly needs a language model scoring word collocations, which is beyond a medicine of this kind. The spintax pattern would also fire on a document that legitimately shows spintax syntax, such as a page explaining how article spinners work. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 11. `DA-C1-006` · C1 boilerplate · fix · stage 35

1. **Disease:** C1 boilerplate. Labelled rows: dclm 389, fineweb-edu 308, nemotroncc 161, synth 76. Examples it treats: `13b37bf5acff4d16` (dclm), `319afcfc2bbab65b` (dclm), `96dfcd8dcd7a0cff` (fineweb-edu).
2. **Medicine:** Delete every line that is only a known widget or menu label (`Primary tabs`, `Search for:`, `Related posts`, `Share this:`, `Read more`, `Link copied`, `Quantity`, and a few more). A whole-line match is required, so a sentence that contains these words is never touched.

```python
RULE_ID = "DA-C1-006"
CODE = "C1"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc"  # pack whose medicine this came from
AUTHOR = "s9k96"  # extractor; None means drop
import re

WIDGET = re.compile(r"(?i)(?:primary tabs|search for:?|related (?:documents|posts|articles):?|click to expand\W*|read more\W*|\[?read more\W*\]?|share this:?|share on (?:other sites|[a-z ]+)|previous|next|menu|contents|advertisement|loading\W*|link copied|the link has been copied!?|post navigation|quantity|breadcrumb|logged|registered|banned|show more|you may also like[a-z ]*|subscribe to [a-z ]+|skip to (?:main )?content|back to top)")

def c1(t):
    """Delete lines that consist only of a known widget or menu label ('Primary tabs', 'Search for:', 'Related posts', 'Share this:' ...)."""
    return "\n".join(l for l in t.split("\n") if not WIDGET.fullmatch(l.strip()))


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(c1(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 6 fixed, 0 dropped, fineweb-edu 2 fixed, 0 dropped, nemotroncc 27 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** Most reviewed C1 lines are not on the label list. Examples are `Store Information`, `Featured Manchester Subdivision Real Estate Properties`, `Posted by ... October 2, 2013` and `source: easemytrip`, which are site-specific. The list needs more labels as more packs are read. A real section titled `Contents` or `Next` on its own line would lose that line.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; None means drop. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 12. `DA-C2-003` · C2 repeated lines · fix · stage 35

1. **Disease:** C2 repeated lines. Labelled rows: dclm 38, fineweb-edu 6, nemotroncc 39, synth 1. Examples it treats: `1e13b455581e96ca` (dclm), `28bd69b4ed987643` (dclm), `b888d78a21618c96` (fineweb-edu).
2. **Medicine:** Remove the later copies of a line that appears 3 or more times in the same document (lines of at least 10 characters, compared without extra spaces); the first copy is kept. Shorter lines ("*", "Answer") are left alone. In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
RULE_ID = "DA-C2-003"
CODE = "C2"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-fineweb-edu"  # pack whose medicine this came from
AUTHOR = "deepjyotisaha"  # extractor; adapter for spans
import re

def _merge(spans):
    """Overlapping spans joined into one, keeping the rule of the first."""
    out = []
    for s, e, rule in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(e, out[-1][1]), out[-1][2])
        else:
            out.append((s, e, rule))
    return out

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


def _std(out, text):  # added by Data A
    # the author's result (spans to remove) in the shared form, as their clean() reads it: (spans, True) from
    # c1_spans -> drop; a whole-document "B4-mostly-code" or "C5-list-page" span -> drop; else the spans go
    if isinstance(out, tuple):
        out, flagged = out
        if flagged: return ("drop", text)
    if out and out[0][2] in ("B4-mostly-code", "C5-list-page"): return ("drop", text)
    new = text
    for s, e, _ in reversed(_merge(out)):
        new = new[:s] + new[e:]
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(c2_spans(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 20 fixed, 0 dropped, fineweb-edu 4 fixed, 0 dropped, nemotroncc 19 fixed, 0 dropped, synth 2 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 1/170; fineweb-edu 1/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The medicine finds 6 of the 8 labelled cases. On the whole pack it changes 4 documents: besides the labelled repeats it removes repeated section headings that were labelled C1 and repeated table headers, which belong to their tables. It misses a passage printed twice when the copies are not identical line by line (document 53). --- The appendices below support the medicines above; they are not medicines themselves. ### Appendix A: test on unseen documents On 2026-10-25, before documents 151–500 were labelled, the medicines' predictions for them were saved (`frozen_predictions.json`; C1 scorer trained on the first 150 documents, threshold 0.97). Comparing them with the labels made afterwards (`frozen_test.py`): - **C1 caught:** 174 of 454 labelled C1 lines (38.3%). - **C1 precision:** 169 of the 178 lines it removed were labelled C1 (94.9%). - **Clean documents changed:** 1 of 143 (0.7%): documents 457. - **C3:** found in 0 of the 7 documents labelled C3. - **Blind documents** (every 10th, labelled without seeing any suggestion; the fully independent test): 17 of 47 C1 lines caught (36.2%), 17 of 20 removed lines labelled C1 (85.0%), 0 of 17 clean documents changed. In the other documents the reader saw the predictions as suggestions while labelling, so agreement there is partly their influence. The medicine above was retrained on all labelled documents after this test. ### Appendix B: runnable code All the medicines in one self-contained Python file: copy it into `medicine_standalone.py` and it runs with the standard library alone (no numpy, no other files). It is generated from the code and the trained weights that were tested above, and it gives the same result as that code on all 500 documents of the pack (0 differences, checked by `standalone.py`), when it is given the pack's line-repetition counts (below). Without them, C1 gives a different result on 7 of the 500 documents, because it cannot tell which lines repeat across the pack. How to use it:
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for spans. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 13. `DA-C5-005` · C5 lists of keywords or links · fix · stage 35

1. **Disease:** C5 lists of keywords or links. Labelled rows: dclm 61, fineweb-edu 30, nemotroncc 71, synth 7. Examples it treats: `4604f40da35906cc` (fineweb-edu), `58b9213cca24ff17` (fineweb-edu), `d49190f1c5ef2a70` (nemotroncc).
2. **Medicine:** Remove a line that is a tag list: it starts with `Tags:`, `Tag:`, `Keywords:`, `Tagged with:`, `Topics:` or `Filed under:`. Lists of commas or pipes without such a word are left alone: in clean documents they are stat lines, ingredient lists and genre lists.

```python
RULE_ID = "DA-C5-005"
CODE = "C5"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new in the 29 Oct sheet as DA-C5-002
import re

C5_PREFIX = re.compile(r"^(?:tags?|keywords?|tagged(?: with| in)?|topics?|filed under)\s*:", re.I)


def medicine_c5(text):
    lines = text.split("\n")
    keep = [ln for ln in lines if not C5_PREFIX.search(ln.strip())]
    if len(keep) == len(lines):
        return ("keep", text)
    new = "\n".join(keep).strip("\n")
    return ("drop", text) if not new.strip() else ("fix", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return medicine_c5(doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 4 fixed, 1 dropped, fineweb-edu 2 fixed, 0 dropped, nemotroncc 4 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A real heading such as `Topics:` before a list in an article is removed. Keyword spam without the prefix is missed.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule, 29 Oct sheet (was DA-C5-002). Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 14. `DA-D3-003` · D3 mixed language · fix · stage 35

1. **Disease:** D3 mixed language. Labelled rows: dclm 24, fineweb-edu 5, nemotroncc 6, synth 1. Examples it treats: `122504afaec49b2d` (dclm), `1ec7fa64b9476242` (dclm), `95e8df7138976c19` (fineweb-edu).
2. **Medicine:** Do not fix real code-switching. The rule deletes only whole lines in which more than half of the letters are not Latin, in an English pack. A foreign word inside an English sentence stays.

```python
RULE_ID = "DA-D3-003"
CODE = "D3"
ACTION = "fix"
STAGE = "35"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc"  # pack whose medicine this came from
AUTHOR = "s9k96"  # extractor; None means drop
import re

def d3(t):
    """Delete lines whose letters are mostly non-Latin (CJK, Cyrillic, Hangul, Devanagari ...) in an English document."""
    import unicodedata
    def foreign(l):
        letters = [c for c in l if c.isalpha()]
        return len(letters) >= 3 and sum(unicodedata.name(c, "").split(" ")[0] != "LATIN" for c in letters) / len(letters) > 0.5
    return "\n".join(l for l in t.split("\n") if not foreign(l))


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(d3(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 4 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 4 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A quoted line in another language, or a bilingual example, is deleted from a good document. Mixed sentences such as `3da0a9bbeeac1a6a` (Spanish and English in one sentence) are not fixed; they need a human decision.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; None means drop. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 15. `DA-B4-007` · B4 template and code junk · fix · stage 40

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `281de2e3af773d76` (synth), `47f4f5107ac9aece` (synth).
2. **Medicine:** Match the negated phrase (`not … in the (given|provided) text/passage/document`, `the text does not provide/mention/…`) or `the given/provided text`. Delete the bullet, `Key: value` line or QA pair that carries it; in running prose delete only the sentence.

```python
RULE_ID = "DA-B4-007"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "maheshsv"  # extractor; adapter for (text or None, changed)
import re
ANSWER_LINE = re.compile('^(?:Answer|A)\\s*[:.]|\\bAnswer:\\s')  # added by Data A: from maheshsv's medicine.md
KEY_VALUE_LINE = re.compile('^[^:\\n]{1,60}:\\s')  # added by Data A: from maheshsv's medicine.md
LIST_MARK = re.compile('^(?:[-*•–—]|\\d+[.)]|[a-z][.)])\\s')  # added by Data A: from maheshsv's medicine.md
META = re.compile('(?i)\\bnot (?:explicitly |specifically |directly )?(?:provided|stated|mentioned|specified|given|available|included|present|disclosed|named) in the (?:given |provided |original |above |source )?(?:text|passage|article|document|excerpt|content|context)|\\bthe (?:text|passage|article|document) does not (?:explicitly |specifically )?(?:provide|mention|specify|state|say|give|include|indicate|name)\\b|\\bthe (?:given|provided) (?:text|passage) (?:also )?(?:discusses|mentions|describes|states|says|provides|refers|covers|explains|includes|lists|notes)\\b')  # added by Data A: from maheshsv's medicine.md
MIN_KEEP_CHARS = 200  # added by Data A: from maheshsv's medicine.md

def remove_meta_comments(text: str) -> tuple[str | None, bool]:
    """Delete the bullet, `Key: value` line or Question/Answer pair that carries a rewriter meta-comment; in running
    prose delete only the sentence."""
    if not META.search(text):
        return text, False
    lines = text.split("\n")
    drop = set()
    for i, ln in enumerate(lines):
        if not META.search(ln):
            continue
        s = ln.strip()
        if s.startswith("Question:") or ANSWER_LINE.match(s):
            drop.add(i)                                   # drop the whole QA pair, whichever line carries it
            if s.startswith("Question:") and i + 1 < len(lines) and ANSWER_LINE.match(lines[i + 1].strip()):
                drop.add(i + 1)
            if ANSWER_LINE.match(s) and not s.startswith("Question:") and i > 0 and lines[i - 1].strip().startswith("Question:"):
                drop.add(i - 1)
        elif LIST_MARK.match(s) or KEY_VALUE_LINE.match(s):
            drop.add(i)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", ln)
            lines[i] = " ".join(x for x in sentences if not META.search(x))
    new = "\n".join(ln for i, ln in enumerate(lines) if i not in drop)
    new = re.sub(r"\n{3,}", "\n\n", new).strip()
    if len(new) < MIN_KEEP_CHARS:
        return None, True
    return new, True


def _std(out, text):  # added by Data A
    # the author's result (new_text or None, changed) in the shared form: None -> drop, else fix/keep by the text
    new, _ = out
    if new is None: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(remove_meta_comments(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 8 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The pattern deliberately does **not** match plain "in the text" (QA questions such as "Who is the main character in this text?" are the normal format of `diverse_qa_pairs`), nor "The text discusses …" and "The text mentions that …" (the summary frame of `distill` and `knowledge_list` rewrites, present in several clean rows), nor "the original text", which two `wrap_medium` documents use legitimately as product copy about paraphrasing tools. Constructed sentences such as `Read the given passage carefully and answer the questions that follow.`; `Applicants must sign the provided document before the deadline.` are no longer matched, because the `given/provided text` branch now requires a reporting verb. A Question line that carries the phrase takes its Answer line with it and vice versa, so no orphan line is left. A genuine essay that writes "the provided text also discusses" would lose that sentence.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text or None, changed). Added: ANSWER_LINE, KEY_VALUE_LINE, LIST_MARK, META, MIN_KEEP_CHARS. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 16. `DA-B4-008` · B4 template and code junk · fix · stage 40

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `0b500dc5f31c1afc` (synth), `1f21b7ad88d0ec88` (synth).
2. **Medicine:** When a letter is directly followed by `'`, the quote opens a word that starts with `s`, `r` or `m`, and the phrase is closed by another `'` on the same line, insert a space before the quote. The `s/r/m` restriction comes from the data: every one of the 23 glitches opens such a word, which fits a detokeniser that treated the quote as the start of a contraction (`'s`, `'re`, `'m`) and glued it to the previous word. Contractions, possessives and poetic elisions (`it's`, `don't`, `we're`, `o'clock`, `y'all`, `rock'n'roll`, `ne'er`) are excluded by the look-ahead; Python string prefixes (`f'…'`, `r'…'`, `b'…'`, `rb'…'`) by the look-behind.

```python
RULE_ID = "DA-B4-008"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "maheshsv"  # extractor; adapter for (text or None, changed)
import re
DETOK = re.compile("(?<=[A-Za-z])(?<![^A-Za-z][frbuFRBU])(?<![^A-Za-z][rR][bB])(?<![^A-Za-z][bB][rR])'(?!s\\b|t\\b|re\\b|ll\\b|ve\\b|d\\b|m\\b|em\\b|n'|er\\b|clock\\b|all\\b|am\\b)(?=[srmSRM][A-Za-z][^'\\n]{0,40}'(?:[\\s,.;:)!?]|$))", re.M)  # added by Data A: from maheshsv's medicine.md

def fix_detok_quotes(text: str) -> tuple[str | None, bool]:
    new = DETOK.sub(" '", text)
    return new, new != text


def _std(out, text):  # added by Data A
    # the author's result (new_text or None, changed) in the shared form: None -> drop, else fix/keep by the text
    new, _ = out
    if new is None: return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(fix_detok_quotes(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 2 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 18 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A possessive directly followed by a quoted phrase that closes on the same line (`the boys'bikes'`) would get a spurious space; not seen in 500 documents. Constructed code and verse inputs (`print(f'hello world')`; `pattern = re.compile(r'sample')`; `payload = b'raw'`; `I ne'er saw such a thing,' she said`; `the boys' bikes were new`) are left alone. False negatives: a quoted phrase longer than 40 characters, a glitch with no closing quote on the line, the sibling variant with a dot-extension (`e.g.,.tar`, `like.yaml`, `the.NET`: 2 documents, labelled B4, not fixed by this rule). Curly quotes (’) are not handled; none occur in this pack. The B4 total (36 documents) is larger than the two rules together because B4 was also used, as the closest code, for other pipeline junk in 11 documents: `d2fb665c40af5edb` (`-DATE-` placeholder left in a bill description); `ea0ecda1c2f25dd1` (OCR glyph junk `e~ \` inside prose); `6011e88c8cc9c77d` (missing space before dot-extensions (`in.jpg,.png`)); `12693fe362d15d0d` (Cloudflare `[email protected]` placeholder); `373e0f0dd5699ac0` (e-learning template demo content under a real course title, dropped); `57922931d471745c` (epoch-bug date `January 17, 1970` and midnight time copied from the CMS); `0c03a4c096276336` (forum thread recast as an AI/user exchange); `d4f559ee86104b5b` (missing space before `.NET`); `68924f97019edabb` (`https://www.example.com/…` placeholder link); `e472a2fcc0df3984` (SEO-writing prompt leaked into the prose, dropped); `03ad0f392751ba37` (missing space before dot-extensions (`e.g.,.tar`)). The most training-relevant of these is the leaked SEO-writing prompt in `e472a2fcc0df3984` ("vary your verbs …"), dropped, and the chat-role recasting in `0c03a4c096276336` ("The AI advises the user …"), which teaches the assistant/user frame as plain text and sits next to B3 in danger.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for (text or None, changed). Added: DETOK. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 17. `DA-B4-009` · B4 template and code junk · fix · stage 40

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `7ecdf57b3e06fd56` (dclm), `90c2a9476f8445ad` (dclm).
2. **Medicine:** Remove the junk tokens where they stand, and delete the line when the whole line is a tracking call or an ad placeholder. Each pattern is a literal artefact, not a guess.

```python
RULE_ID = "DA-B4-009"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm"  # pack whose medicine this came from
AUTHOR = "mittalutkarsh"  # extractor
import re

_TOKENS = tuple(
    re.compile(p, re.I)
    for p in (
        r"\{/?PARAGRAPH\}",
        r"\[an error occurred while processing this directive\]",
        r"\{\{\s*[A-Za-z_][\w.]*\s*\}\}",
    )
)

_JUNK_LINE = re.compile(
    r"^[ \t]*(?:fbq\(.*?\);?|ga\(.*?\);?|_gaq\.push\(.*?\);?|"
    r"google adsense here|advertisement)[ \t]*$",
    re.I | re.M,
)

_BLANKS = re.compile(r"\n{3,}")

def medicine_b4(text):
    out = _JUNK_LINE.sub("", text)
    for pattern in _TOKENS:
        out = pattern.sub("", out)
    if out == text:
        return text          # nothing removed, so do not touch the spacing either
    return _BLANKS.sub("\n\n", out)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 5 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 1 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** A page that is *about* web analytics and quotes `fbq('track', ...)` on a line of its own would lose the line it is discussing. Removing `{/PARAGRAPH}` in place can leave two words joined with no space where the extractor used the marker as the only separator, which is what happened in `f819811b670939d0`; the text is still readable but one word boundary is lost. ---
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 18. `DA-B4-010` · B4 template and code junk · fix · stage 40

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `3e44df6a7ddb0098` (fineweb-edu).
2. **Medicine:** Two parts. - template junk (fix): remove what a web page left unfilled: "{{ title }}", "{% if … %}", "${name}", a code expression in backticks such as "`page.data.shortTitle || page.data.title`", "NaN" or "undefined" right after ":", "=" or "$", and a line that is only "undefined", "NaN" or "null"; - mostly code (drop): a line is a code line when it has at least two code tokens ("::", "->", "==", "&&", "{", "}", a line ending in ";", a line starting with "import", "def", "return", "public", "$ ", "Sub", …) and at least one for every six words; a table row "|cell||cell|" is never a code line. A document whose code lines hold more than half of its characters is dropped; - code snippets inside an article are kept on purpose (decided 27 Oct): tutorials and manual pages with a few lines of code are good training text, and cutting them risks removing real content. In code (the function the medicine runs; the patterns, weights and helpers it uses are in Appendix B, the full runnable file):

```python
RULE_ID = "DA-B4-010"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-fineweb-edu"  # pack whose medicine this came from
AUTHOR = "deepjyotisaha"  # extractor; adapter for spans
import re

def _merge(spans):
    """Overlapping spans joined into one, keeping the rule of the first."""
    out = []
    for s, e, rule in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(e, out[-1][1]), out[-1][2])
        else:
            out.append((s, e, rule))
    return out

B4_TEMPLATE = re.compile(
    r"\{\{[^{}\n]{0,80}\}\}"                          # {{ title }}
    r"|\{%[^\n]{0,80}?%\}"                            # {% if x %}
    r"|\$\{[^{}\n]{0,80}\}"                           # ${name}
    r"|`[\w.]+(?:\s*(?:\|\||&&)\s*[\w.]+)+`"          # `page.data.shortTitle || page.data.title`
    r"|(?<=[:=$])\s*(?:undefined|NaN)\b"              # Price: NaN, name=undefined
    r"|^[ \t]*(?:undefined|NaN|null)[ \t]*$", re.M)

B4_CODE_TOKENS = re.compile(
    r"::|->|=>|==|!=|<=|>=|&&|\|\||\+\+|\+=|-=|\);|\)\s*\{|[{};]\s*$|\}"
    r"|^\s*(?:#include|import\s|from\s+\S+\s+import|def\s|class\s|public\s|private\s|static\s|void\s|return\b"
    r"|require\s|var\s|let\s|const\s|function\b|Sub\s|End Sub|Dim\s|\$\s|>>>\s|>\s)"
    r"|\b(?:End Sub|ByVal|As Integer|System\.out|printf|println)\b", re.M)

B4_MIN_TOKENS, B4_WORDS_PER_TOKEN, B4_SHARE = 2, 6, 0.5

TABLE_ROW = re.compile(r"^\s*\|.*\|\|")

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


def _std(out, text):  # added by Data A
    # the author's result (spans to remove) in the shared form, as their clean() reads it: (spans, True) from
    # c1_spans -> drop; a whole-document "B4-mostly-code" or "C5-list-page" span -> drop; else the spans go
    if isinstance(out, tuple):
        out, flagged = out
        if flagged: return ("drop", text)
    if out and out[0][2] in ("B4-mostly-code", "C5-list-page"): return ("drop", text)
    new = text
    for s, e, _ in reversed(_merge(out)):
        new = new[:s] + new[e:]
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(b4_spans(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 0 dropped, fineweb-edu 1 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 0 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The medicine finds 1 of the 16 labelled cases. On the whole pack it changes 1 document. The mostly-code part drops no document of this pack: the most code-like one (document 10) has code in only 3% of its text. The other B4 documents are articles with a code snippet (a Visual Basic or Java listing, a Ruby example, a command manual page, a Haskell mailing-list post), kept on purpose; the readers' labels remain the record of them. Code flattened into a prose line by the original crawl is hard to tell from prose with symbols, which is why the drop needs more than half of the document to be code.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor; adapter for spans. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 19. `DA-B4-011` · B4 template and code junk · fix · stage 40

1. **Disease:** B4 template and code junk. Labelled rows: dclm 25, fineweb-edu 8, nemotroncc 15, synth 36. Examples it treats: `d2fb665c40af5edb` (synth).
2. **Medicine:** Replace the exact heading `Total Due After -DATE-:` with `Total Due After the Due Date:` only when it occurs exactly once. Leave all other text unchanged. The function accepts a text string and returns a text string; it has no document-ID filter, so the same rule can be evaluated on unseen gold documents. It requires only the Python standard library and installs no tools.

```python
RULE_ID = "DA-B4-011"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "AJJAPUSIVA"  # extractor
import re

def medicine_b4(text):
    """Return text with one exact billing-heading placeholder repaired."""
    old = "Total Due After -DATE-:"
    new = "Total Due After the Due Date:"
    if text.count(old) != 1:
        return text
    return text.replace(old, new, 1)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 0 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 0 fixed, 0 dropped, synth 1 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** The literal heading might be intentional quoted text, documentation of a template, or an actual bill that requires a specific date. The rule cannot distinguish these contexts and may change valid text. Repeated occurrences are deliberately left unchanged for review. A gold-set pass alone does not establish effectiveness on the full dataset.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: extractor. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 20. `DA-F1-005` · F1 personal data · fix · stage 40

1. **Disease:** F1 personal data. Labelled rows: dclm 13, fineweb-edu 12, nemotroncc 13, synth 2. Examples it treats: `416e12ac72df0b07` (dclm), `71f25549c2c4200d` (dclm), `fab230d1a3b03a77` (nemotroncc).
2. **Medicine:** Replace each phone number, personal email address and street-level address of a private person with a typed placeholder: `<PHONE>`, `<EMAIL>`, `<ADDRESS>` (instructor, 31 Oct). An email is personal when it is at a webmail domain, or when its local part looks like a name (a dot, underscore, hyphen, digit or 13+ characters) and the context is not an organisation's; role addresses (`info@`, `sales@` ...) never are. A phone number or a street address stays when the contact block around it shows an organisation (a business or trade word, opening hours, a fax line, a listing site), when the page speaks for an organisation ("call us", "our office"), or when the number is toll-free. A street address is replaced only on a contact line, not inside running prose.

```python
RULE_ID = "DA-F1-005"
CODE = "F1"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {"en", "eng"}
ORIGIN = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # packs it runs on
SOURCE = "en-dclm, en-fineweb-edu, en-nemotroncc, en-nemotroncc-synth"  # pack whose medicine this came from
AUTHOR = "aneeshads"  # new rule to the instructor's F1 ruling of 31 Oct; email test from DA-F1-002 (shekar-maker)
import re

EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b")

WEBMAIL = re.compile(r"@(?:gmail|googlemail|yahoo|ymail|hotmail|outlook|live|msn|aol|icloud|me|mac|protonmail|proton|"
                     r"rediffmail|zoho|gmx|yandex|mail|comcast|verizon|att|sbcglobal|bellsouth|earthlink|btinternet)\.", re.I)

PERSONAL_LOCAL = re.compile(r"[._\-]|\d|^.{13,}$")

ROLE_LOCAL = re.compile(r"^(?:info|contact|contactus|enquir(?:y|ies)|inquir(?:y|ies)|sales|support|help|helpdesk|admin|"
                        r"office|hello|hi|press|media|news|newsletter|editor|editors|team|jobs|careers|hr|marketing|"
                        r"billing|accounts|orders|service|services|customerservice|webmaster|postmaster|noreply|"
                        r"no-reply|abuse|privacy|legal|admissions|registrar|events|bookings|reservations)$", re.I)

NOT_REAL = re.compile(r"@(?:example|test|domain|email)\.(?:com|org|net)$", re.I)

PHONE = re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s.\-‐‑–]?)?(?:\(\d{2,4}\)[\s.\-‐‑–]?|\d{2,4}[\s.\-‐‑–])\d{3,4}[\s.\-‐‑–]\d{3,4}(?![\w-])")

TOLL_FREE = re.compile(r"^(?:\+?1[\s.-]?)?\(?8(?:00|88|77|66|55|44|33)\)?")

STREET = (r"(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Boulevard|Blvd|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter|Close|"
          r"Crescent|Cres|Highway|Hwy|Parkway|Pkwy|Circle|Cir|Square|Sq)")

ADDRESS = re.compile(r"\b\d{1,5}[A-Za-z]?\s+(?:[NSEW]\.?\s+)?(?:[A-Z][a-z]+\.?\s+){1,4}" + STREET + r"\b\.?"
                     r"(?:,?\s*(?:Apt|Unit|Suite|Ste|#)\.?\s*\w+)?"
                     r"(?:,\s*(?:[A-Z][a-z]+\s?){1,3},\s*[A-Z]{2}\.?\s*\d{5}(?:-\d{4})?)?")

CONTACT_LINE = 120

ORGANISATION = re.compile(
    r"(?i)\b(?:inc|llc|ltd|plc|corp|co\.|company|warehouse|store|shop|market|restaurant|cafe|café|bar|grill|bistro|"
    r"hotel|inn|motel|resort|spa|salon|clinic|hospital|surgery|pharmacy|cent(?:er|re)|office|offices|university|"
    r"college|school|academy|library|museum|church|gallery|theat(?:er|re)|cinema|bank|agency|association|society|"
    r"council|department|ministry|embassy|tourist|information|headquarters|hq|branch|showroom|dealership|"
    r"open (?:mon|tue|wed|thu|fri|sat|sun|daily|7|24)\w*|hours|menu|reservations|fax|"
    r"on (?:urbanspoon|yelp|tripadvisor|zomato|foursquare)|"
    # trades and services that put their number on their own page
    r"pros?|plumb\w*|roofing|hvac|electric(?:al|ians?)|landscap\w*|cleaning|movers?|moving|storage|rentals?|hire|"
    r"repairs?|construction|builders?|contractors?|auto|motors|towing|insurance|realty|real estate|mortgage|loans?|"
    r"law|lawyers?|attorneys?|legal|dental|dentistry|orthodont\w*|chiropract\w*|physiotherap\w*|therapy|"
    r"veterinar\w*|vet|clinics?|practice|surgery|medical|health(?:care)?|consult(?:ation|ing|ants?)?|services?|"
    r"solutions|group|partners|associates|studio|chalet|lodge|villa|apartments?|cottage|camping|farm|winery|"
    r"brewery|bakery|club|bbs|board|optometr\w*|optic\w*|opticians?|spectacles|suite)\b")

ORG_VOICE = re.compile(r"(?i)\b(?:call us|contact us|email us|e-mail us|visit us|reach us|text us|give us a call|"
                       r"our (?:office|team|staff|clinic|store|shop|experts?|technicians?|specialists?|services?|"
                       r"company|firm|practice|location)|one of our|we (?:offer|provide|specialize|specialise|serve)|need help\?)|☎")

PUBLIC_ROLE = re.compile(r"(?i)\b(?:reporter|editor|journalist|correspondent|spokes(?:man|woman|person)|press|media|"
                         r"publicist|author of|professor|prof\.|dr\.|lecturer|faculty|researcher|principal investigator|"
                         r"media contact|press contact|for more information|high[- ]res|images|photos)\b")

def _organisation_near(lines, i):
    """An organisation word in the contact block around line i: up to 6 lines each way."""
    return bool(ORGANISATION.search("\n".join(lines[max(0, i - 6):i + 7])))

def _email(m, org):
    addr = m.group()
    local = addr.split("@", 1)[0]
    if NOT_REAL.search(addr) or ROLE_LOCAL.match(local):
        return addr
    if WEBMAIL.search(addr):  # a webmail address belongs to a person
        return "<EMAIL>"
    # a name-like address at an organisation's domain is a work address when the context is an organisation's
    return addr if org or not PERSONAL_LOCAL.search(local) else "<EMAIL>"

def medicine_f1(text):
    lines = text.split("\n")
    org_page = bool(ORG_VOICE.search(text))
    out = []
    for i, line in enumerate(lines):
        org = org_page or _organisation_near(lines, i)
        new = EMAIL.sub(lambda m: _email(m, org or bool(PUBLIC_ROLE.search(
            "\n".join(lines[max(0, i - 2):i + 1])))), line)
        if PHONE.search(new) or ADDRESS.search(new):
            if not org:
                new = PHONE.sub(lambda m: m.group() if TOLL_FREE.match(m.group()) else "<PHONE>", new)
                if len(line.strip()) <= CONTACT_LINE:
                    new = ADDRESS.sub("<ADDRESS>", new)
        out.append(new)
    return "\n".join(out)


def _std(out, text):  # added by Data A
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep,
    # ("drop", _) -> drop. An empty result is a drop: nothing of the document is left.
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple):
        if out[0] == "drop": return ("drop", text)
        out = out[1]
    if not out.strip(): return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_f1(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** all four English packs. **Docs it touches:** dclm 2 fixed, 0 dropped, fineweb-edu 0 fixed, 0 dropped, nemotroncc 1 fixed, 0 dropped, synth 2 fixed, 0 dropped.
4. **Harm test:** dclm 0.00% (0/62) PASS; fineweb-edu 0.00% (0/158) PASS; nemotroncc 0.00% (0/34) PASS; synth 0.00% (0/96) PASS. With disputed docs left in: dclm 0/170; fineweb-edu 0/295; nemotroncc 0/34; synth 0/96.
5. **Side effects:** Organisations' numbers and addresses stay, as the ruling asks, so most of the labelled F1 rows are left: readers labelled business contacts F1 before the ruling. A private person's number on a page that also speaks for an organisation stays too. Addresses inside sentences (a biography's "he lived at No. 12 High Street") stay. ID numbers (social security, card, Aadhaar, PAN) are not in the ruling and are not treated.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: new rule to the instructor's F1 ruling of 31 Oct; email test from DA-F1-002. Idempotent on every doc it changes. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Harm test of the whole sheet, in run order

| pack | gold | gold changed | gold dropped | harm | result | pack fixed / dropped / untouched | labelled rows treated | labelled-clean docs changed outside gold |
|---|---|---|---|---|---|---|---|---|
| dclm | 62 | 0 | 0 | 0.00% | PASS | 54 / 9 / 437 | 63 / 438 | 34 |
| fineweb-edu | 158 | 0 | 0 | 0.00% | PASS | 12 / 1 / 487 | 13 / 342 | 8 |
| nemotroncc | 34 | 0 | 0 | 0.00% | PASS | 62 / 17 / 421 | 75 / 296 | 5 |
| synth | 96 | 0 | 0 | 0.00% | PASS | 32 / 1 / 467 | 33 / 165 | 9 |
