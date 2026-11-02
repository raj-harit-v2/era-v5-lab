# medicine_code: compiled code medicines

Packs: go 163, rust 78, js-ts 204, java 116, cpp 120, python 46 gold docs (Data A gold, `teams/01-data-a/gold/`). Each pack is tested on its own gold set.
Rule form: `RULE_ID`, `CODE`, `ACTION`, `STAGE`, `STATUS`, `LANGS`, `ORIGIN`, `SOURCE`, `AUTHOR`; `medicine(doc) -> (action, text)`, `doc = {doc_id, text, url, lang_label}`. A row outside `LANGS` passes unchanged. Same form as `medicine_en.md`, with `STAGE` and `STATUS` added. `AUTHOR` is a code field the team's `medicine_conflicts.py` reads; it is not used in the text.
Run order is section order, by stage: 10 characters, 20 markup, 30 source (drops, then strips), 40 data safety. An annotator's code is copied unchanged; only the imports it uses, `_std` and the `LANGS` guard are added. Two exceptions: `DA-E4-010` is `DA-E4-004` with 3 bugs fixed, and `DA-E3-004` is new.
IDs: Data A registry after running the extractor on the latest sheets. `DA-E3-004`, `DA-E4-009`, `DA-E4-010` and `DA-C4-002` are the next free numbers. All IDs are provisional until the team commits the registry.
Assumption: the language tag on a row is correct. No language detector runs (`D1`).
Tested on `g1-harm-test` at `bae5163`. Limit: changed + dropped at most `max(1, floor(1% of gold))`. Why each rule was picked, for each disease: `decisions_code.md`.

| pack | gold sha256 | pack sha256 |
|---|---|---|
| go | `81942db337e2e191` | `30fc352199a6b377` |
| rust | `2fbb0779f2da11fb` | `c5822b7df0e76a6b` |
| js-ts | `518cf5c367f088a3` | `4aa4dea19a83b8db` |
| java | `223d555f68e1bd7e` | `739dc95cdb424184` |
| cpp | `0f53271f3bebb4b5` | `2aa25660b81ccaea` |
| python | `de8d9ade6605d9b7` | `b79698620cd7526f` |

Each cell: gold harm % (gold docs changed or dropped / gold docs), the result at the limit, and the labelled rows the rule treats / the labelled rows with its code. `off` = not in `LANGS`.

| # | ID | disease | action | stage | source | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `DA-A1-001` | A1 invisible junk characters | fix | 10 | code-cpp | 0.00% (0/163) PASS · 0/0 | 0.00% (0/78) PASS · 1/1 | 0.00% (0/204) PASS · 1/1 | 0.00% (0/116) PASS · 1/1 | 0.00% (0/120) PASS · 12/12 | 0.00% (0/46) PASS · 0/0 |
| 2 | `DA-A2-007` | A2 control characters | fix | 10 | code-go | 0.00% (0/163) PASS · 1/1 | 0.00% (0/78) PASS · 6/6 | 0.00% (0/204) PASS · 17/17 | 0.00% (0/116) PASS · 44/44 | 0.00% (0/120) PASS · 47/47 | 0.00% (0/46) PASS · 2/2 |
| 3 | `DA-A6-001` | A6 mixed script (look-alike letters) | fix | 10 | code-go | 0.00% (0/163) PASS · 2/2 | 0.00% (0/78) PASS · 0/0 | 0.00% (0/204) PASS · 0/0 | 0.00% (0/116) PASS · 0/0 | 0.00% (0/120) PASS · 0/0 | 0.00% (0/46) PASS · 0/0 |
| 4 | `DA-A4-002` | A4 replacement characters | fix | 10 | code-go | 0.00% (0/163) PASS · 1/1 | 0.00% (0/78) PASS · 0/0 | 0.00% (0/204) PASS · 0/0 | 0.00% (0/116) PASS · 0/2 | 0.00% (0/120) PASS · 0/0 | 0.00% (0/46) PASS · 0/0 |
| 5 | `DA-A4-003` | A4 replacement characters | fix | 10 | code-java | off | off | off | 0.00% (0/116) PASS · 2/2 | off | off |
| 6 | `DA-B3-001` | B3 ghost markers | fix | 20 | code-cpp | 0.00% (0/163) PASS · 247/247 | 0.00% (0/78) PASS · 225/225 | 0.00% (0/204) PASS · 245/262 | 0.00% (0/116) PASS · 250/250 | 0.00% (0/120) PASS · 245/245 | 0.00% (0/46) PASS · 272/284 |
| 7 | `DA-E1-001` | E1 minified or generated code | drop | 30 | code-go | 0.00% (0/163) PASS · 42/43 | off | off | off | off | off |
| 8 | `DA-E1-004` | E1 minified or generated code | drop | 30 | code-rust | off | 0.00% (0/78) PASS · 17/23 | off | off | off | 0.00% (0/46) PASS · 10/11 |
| 9 | `DA-E1-008` | E1 minified or generated code | drop | 30 | code-js-ts | off | off | 0.00% (0/204) PASS · 22/23 | off | off | off |
| 10 | `DA-E1-006` | E1 minified or generated code | drop | 30 | code-java | off | off | off | 0.00% (0/116) PASS · 10/14 | off | off |
| 11 | `DA-E1-005` | E1 minified or generated code | drop | 30 | code-go | off | off | off | off | 0.00% (0/120) PASS · 6/20 | off |
| 12 | `DA-E1-007` | E1 minified or generated code | drop | 30 | code-java | off | off | off | off | 0.00% (0/120) PASS · 4/20 | off |
| 13 | `DA-E2-001` | E2 data blobs | drop | 30 | code-go | 0.00% (0/163) PASS · 7/7 | 0.00% (0/78) PASS · 0/2 | 0.00% (0/204) PASS · 0/1 | 0.00% (0/116) PASS · 0/1 | 0.00% (0/120) PASS · 1/1 | 0.00% (0/46) PASS · 0/1 |
| 14 | `DA-C3-002` | C3 truncated or broken document | drop | 30 | code-go | 0.00% (0/163) PASS · 1/1 | off | off | off | off | off |
| 15 | `DA-C4-002` | C4 two documents joined | drop | 30 | code-java | off | off | off | 0.00% (0/116) PASS · 1/1 | off | off |
| 16 | `DA-E4-005` | E4 repeated licence headers | fix+drop | 30 | code-go | 0.00% (0/163) PASS · 56/76 | off | off | off | off | off |
| 17 | `DA-E4-010` | E4 repeated licence headers | fix | 30 | code-rust | 0.00% (0/163) PASS · 50/76 | 0.00% (0/78) PASS · 22/22 | off | 0.00% (0/116) PASS · 81/103 | 0.00% (0/120) PASS · 94/176 | 0.00% (0/46) PASS · 49/70 |
| 18 | `DA-E4-009` | E4 repeated licence headers | fix+drop | 30 | code-go | off | off | off | 0.00% (0/116) PASS · 82/103 | off | off |
| 19 | `DA-E4-007` | E4 repeated licence headers | fix | 30 | code-js-ts | off | off | 0.49% (1/204) PASS · 6/9 | off | off | off |
| 20 | `DA-C1-004` | C1 boilerplate | fix | 30 | code-go | 0.00% (0/163) PASS · 1/1 | off | off | off | off | off |
| 21 | `DA-C1-005` | C1 boilerplate | fix | 30 | code-java | off | off | off | 0.00% (0/116) PASS · 78/80 | off | off |
| 22 | `DA-B4-009` | B4 template junk / PII placeholders | fix | 40 | code-go | 0.00% (0/163) PASS · 43/45 | 0.00% (0/78) PASS · 18/18 | 0.00% (0/204) PASS · 25/25 | 0.00% (0/116) PASS · 82/83 | 0.00% (0/120) PASS · 121/122 | 0.00% (0/46) PASS · 27/27 |
| 23 | `DA-E3-003` | E3 secrets | fix | 40 | code-go | 0.00% (0/163) PASS · 1/1 | 0.00% (0/78) PASS · 0/1 | 0.00% (0/204) PASS · 0/9 | 0.00% (0/116) PASS · 0/1 | 0.00% (0/120) PASS · 0/0 | 0.00% (0/46) PASS · 0/0 |
| 24 | `DA-E3-004` | E3 secrets | fix | 40 | code-go | 0.00% (0/163) PASS · 0/1 | 0.00% (0/78) PASS · 1/1 | 0.00% (0/204) PASS · 2/9 | 0.00% (0/116) PASS · 1/1 | 0.00% (0/120) PASS · 0/0 | 0.00% (0/46) PASS · 0/0 |

## 1. `DA-A1-001` · A1 invisible junk characters · fix · stage 10

1. **Disease:** A1 invisible junk characters. Labelled rows: go 0, rust 1, js-ts 1, java 1, cpp 12, python 0. Examples: `2faccaa1d7a77d70`, `91cf7be64838e0d0`, `beae2c42d8a34ccc`.
2. **Medicine:** Delete U+FEFF (BOM).

```python
RULE_ID = "DA-A1-001"
CODE = "A1"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-cpp"  # pack whose medicine this came from
AUTHOR = "TharunSivamani"
import re

def remove_bom_characters(text: str) -> str:
    return text.replace("\ufeff", "")


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(remove_bom_characters(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 0, rust 1, js-ts 1, java 1, cpp 12, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Only the BOM: other invisible characters of A1 (U+200B, bidi marks, soft hyphen) are not treated, and no labelled row needs it.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-cpp sheet, PR 9. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 2. `DA-A2-007` · A2 control characters · fix · stage 10

1. **Disease:** A2 control characters. Labelled rows: go 1, rust 6, js-ts 17, java 44, cpp 47, python 2. Examples: `34133f5414afff81`, `182c2cf59a3fa4f1`, `2f34546793ed7faf`.
2. **Medicine:** CRLF and lone CR become LF; delete the other C0 control characters and DEL. Tab, newline and form feed stay.

```python
RULE_ID = "DA-A2-007"
CODE = "A2"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

CTRL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")

def medicine_a2(doc):
    t = CTRL.sub("", doc["text"].replace("\r\n", "\n").replace("\r", "\n"))
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a2(doc), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 1, rust 6, js-ts 17, java 44, cpp 47, python 17.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Keeps form feed, which the A2 definition lists, because source code uses it as whitespace. U+0080 to U+009F are not treated.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 3. `DA-A6-001` · A6 mixed script (look-alike letters) · fix · stage 10

1. **Disease:** A6 mixed script (look-alike letters). Labelled rows: go 2, rust 0, js-ts 0, java 0, cpp 0, python 0. Examples: `48b3b124a7aaa5fc`, `64ed179e7e5c3d21`.
2. **Medicine:** Cyrillic look-alike letters inside words that also have Latin letters become Latin.

```python
RULE_ID = "DA-A6-001"
CODE = "A6"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

HOMO = str.maketrans("аеорсухіјѕАВЕКМНОРСТХІЈЅ", "aeopcyxijsABEKMHOPCTXIJS")

MIXED = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*[Ѐ-ӿ])\w+\b")

def medicine_a6(doc):
    t = MIXED.sub(lambda m: m.group().translate(HOMO), doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a6(doc), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 2, rust 0, js-ts 0, java 0, cpp 1, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Can turn an obfuscated e-mail address back into plain text, so the data-safety stage runs after it.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 4. `DA-A4-002` · A4 replacement characters · fix · stage 10

1. **Disease:** A4 replacement characters. Labelled rows: go 1, rust 0, js-ts 0, java 2, cpp 0, python 0. Examples: `2a92a9a8489c5ea2`.
2. **Medicine:** Delete a `//` comment that holds U+FFFD and no ASCII letter or digit. An author-quoted U+FFFD stays (ruling 7).

```python
RULE_ID = "DA-A4-002"
CODE = "A4"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

LOST = re.compile(r"[ \t]*//[^\n\w]*�[^\nA-Za-z0-9]*$", re.M)

def medicine_a4(doc):
    t = LOST.sub("", doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_a4(doc), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 1, rust 0, js-ts 0, java 0, cpp 0, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** U+FFFD in a string, or in a comment with words, stays.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 5. `DA-A4-003` · A4 replacement characters · fix · stage 10

1. **Disease:** A4 replacement characters. Labelled rows: go 1, rust 0, js-ts 0, java 2, cpp 0, python 0. Examples: `912c53fa71c7d9ad`, `9b95cf192922d106`.
2. **Medicine:** In comment lines, U+FFFD between letters becomes a space and other U+FFFD is deleted.

```python
RULE_ID = "DA-A4-003"
CODE = "A4"
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

COMMENT_LINE = re.compile(r"(?m)^[ \t]*(?://|/?\*).*$")

def m8_clean_replacement_chars(t: str) -> str:
    def fix(m):
        return re.sub("\ufffd+", "", re.sub(r"(?<=[^\s\ufffd])\ufffd+(?=[^\s\ufffd])", " ", m.group()))
    return COMMENT_LINE.sub(lambda m: fix(m) if "\ufffd" in m.group() else m.group(), t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m8_clean_replacement_chars(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** java. **Docs it touches:** java 2.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Java only: on go it also changes the author-quoted U+FFFD that ruling 7 keeps.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 6. `DA-B3-001` · B3 ghost markers · fix · stage 20

1. **Disease:** B3 ghost markers. Labelled rows: go 247, rust 225, js-ts 262, java 250, cpp 245, python 284. Examples: `01180a3ddf4dfc23`, `03d9fb46f54cf391`, `03e1fbfd3629a84a`.
2. **Medicine:** Delete the first line when it starts with `<reponame>`, `<filename>` or `<gh_stars>`.

```python
RULE_ID = "DA-B3-001"
CODE = "B3"
ACTION = "fix"
STAGE = "20"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-cpp"  # pack whose medicine this came from
AUTHOR = "TharunSivamani"
import re

METADATA_PREFIX = re.compile(
    r"\A<(?:reponame|filename|gh_stars)>[^\r\n]*(?:\r?\n|\Z)",
    re.IGNORECASE,
)

def remove_metadata_prefix(text: str) -> str:
    return METADATA_PREFIX.sub("", text, count=1)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(remove_metadata_prefix(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 247, rust 225, js-ts 245, java 250, cpp 245, python 272.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** A marker in the middle of a file is not touched, and none was seen.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-cpp sheet, PR 9. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 7. `DA-E1-001` · E1 minified or generated code · drop · stage 30

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `023d4d7c1524277f`, `0bbbdad3593bc36f`, `0e5b75717c831da2`.
2. **Medicine:** Generator marker before or just after the `package` clause, or a Kiota or goformation fingerprint.

```python
RULE_ID = "DA-E1-001"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "RaviNaik"
import re

_GEN = re.compile(
    r"(?im)^\s*(?://|/\*|\*)?\s*(?:"
    r"code generated\b|"
    r"auto-?generated|"
    r"由\w*自动生成|"
    r"\(re-\)?generated by\b.*|"
    r"generated by:?\s*(?:swagger|go-swagger|protoc|mockgen|microsoft|openapi)|"
    r"do not (?:edit|change) this file|"
    r"(?:\*{3}\s*warning:\s*)?this file (?:was|is|has been) (?:automatically |auto-?)?(?:generated|autogenerated)\b|"
    r"(?:this file )?(?:was )?automatically generated\b|"
    r"this file was generated by\b)"
)

_GEN_FINGERPRINT = re.compile(
    r"(?m)^\s*i[0-9a-f]{40,}\s+\"github\.com/microsoft/kiota|"
    r"AWSCloudFormationSpecificationVersion returns the AWS Specification Version that this resource was generated from"
)

_PKG = re.compile(r"(?m)^package\s+\w+")

def drop_generated(text: str):
    """Drop the file if a generated-code marker sits in the header (before `package`
    or within the first 40 lines). Markers inside string literals further down do not count."""
    m = _PKG.search(text)
    head = text[: m.end()] if m else text[:2000]
    head = "\n".join(head.split("\n")[:40]) if len(head) > 4000 else head
    # also allow the Go convention of the marker directly after the package clause (go-swagger)
    tail_probe = text[m.end(): m.end() + 1500] if m else ""
    if _GEN.search(head) or _GEN.search(tail_probe) or _GEN_FINGERPRINT.search(text[:3000]):
        return "drop", text
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(drop_generated(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** go. **Docs it touches:** go 42.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** Generated code with no marker is missed: 1 labelled go row.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, PR 36. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 8. `DA-E1-004` · E1 minified or generated code · drop · stage 30

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `00a6ea4358544d22`, `0316bfaac536f88b`, `1aa2bcd706be1e4b`.
2. **Medicine:** Generator banner in the first 15 lines, or 20 or more `#[doc = "..."]` lines.

```python
RULE_ID = "DA-E1-004"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'python', 'rust'}
ORIGIN = "code-rust, code-python"  # packs it runs on
SOURCE = "code-rust"  # pack whose medicine this came from
AUTHOR = "amukka"
import re

MARKER_LINE = re.compile(r"^(?:<(?:reponame|filename|gh_stars)>[^\n]*)\n?")

GENERATED = re.compile(
    r"(?i)(auto-?generated|automatically generated|code generated|generated by|@generated"
    r"|do not (?:directly )?edit|this file is generated)"
)

def _strip_marker(text: str) -> str:
    return MARKER_LINE.sub("", text, count=1)

def e1_generated(text: str):
    """E1: drop when a generated banner is in the first 15 lines, or 20+ #[doc = "..."] lines."""
    body = _strip_marker(text).split("\n")
    head = "\n".join(body[:15])
    if GENERATED.search(head) or sum('#[doc = "' in l for l in body) >= 20:
        return "drop", ""
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(e1_generated(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** rust, python. **Docs it touches:** rust 17, python 16.
4. **Harm test:** rust 0.00% (0/78) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** A hand-written file whose header says "generated" is dropped. On python it touches 16 docs, 10 labelled E1 and 1 labelled clean.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-rust sheet, PR 52. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 9. `DA-E1-008` · E1 minified or generated code · drop · stage 30

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `0c10e83429b075c5`, `0f34612ed9c80d78`, `2bae666c99ad51ed`.
2. **Medicine:** A build folder in the path (`node_modules/`, `dist/`, `build/`, `bundles/`, `vendor/`, `generated/`) or `.min.js`, except `.d.ts`; a `sourceMappingURL` line; compiled-module output; a generator word in the header comment; a minified line; a line over 1,000 characters; three or more `.html#` links; or `var searchData =`.

```python
RULE_ID = "DA-E1-008"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'javascript', 'typescript'}
ORIGIN = "code-js-ts"  # packs it runs on
SOURCE = "code-js-ts"  # pack whose medicine this came from
AUTHOR = "Sagar063"
import re

_BUILD_PATH = re.compile(r"(^|/)(node_modules|dist|build|bundles?|vendor|generated)/|\.min\.js$")

_GENERATED = re.compile(r"auto-?generated|do not edit|generated by", re.I)

_COMPILED = re.compile(r"Object\.defineProperty\(exports,\s*[\"']__esModule[\"']|\bjsx_runtime_\d+\.jsx\(")

_TAGS = re.compile(r"<(filename|gh_stars|reponame)>")

def _header_comment(text):
    """The comment lines at the very top of the file, after an optional StarCoder line."""
    lines, out = text.split("\n"), []
    if lines and _TAGS.match(lines[0]):
        lines = lines[1:]
    for line in lines:
        s = line.strip()
        if s == "" or s.startswith(("//", "/*", "*", "*/")):
            out.append(line)
        else:
            break
    return "\n".join(out)

def _minified(text):
    return any(len(line) > 300 and line.count(" ") / len(line) < 0.05 for line in text.split("\n"))

def medicine_e1(doc):
    """Drop build output and generated files. doc has 'text' and 'url'."""
    text, path = doc["text"], doc.get("url") or ""
    built = bool(_BUILD_PATH.search(path)) and not path.endswith(".d.ts")
    generated = bool(
        re.search(r"^\s*//# sourceMappingURL=", text, re.M)
        or _COMPILED.search(text)
        or _GENERATED.search(_header_comment(text))
        or _minified(text)
        or max(len(line) for line in text.split("\n")) > 1000
        or text.count(".html#") >= 3
        or re.search(r"var searchData\s*=", text)
    )
    return ("drop", "") if (built or generated) else text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e1(doc), doc["text"])
```

3. **Action:** drop. **Runs on:** js-ts. **Docs it touches:** js-ts 22.
4. **Harm test:** js-ts 0.00% (0/204) PASS.
5. **Side effects:** A hand-written file in such a folder, or with one line over 1,000 characters, is dropped. **3 js-ts docs go on the path alone** (`node_modules`, `build`, `generated`). The 30 Oct ruling says a vendored copy is not a disease by itself, so the reviewer should decide whether `node_modules` and `vendor` stay in the path check. Touches 6 js-ts docs that a reader labelled clean.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-js-ts sheet, PR 115. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 10. `DA-E1-006` · E1 minified or generated code · drop · stage 30

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `138cac43be0730ea`, `2111dfa57dfd75e8`, `3cba9087383097dd`.
2. **Medicine:** Decompiler or generator marker in the text (Jad, Procyon, "AUTO-GENERATED FILE", "This class was generated by", swagger).

```python
RULE_ID = "DA-E1-006"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "riyaagrahari"
import re

GEN = re.compile(r'Decompiled by (Jad|Procyon)|Code generated by [^\n]{0,60}Generator|AUTO-GENERATED FILE'
                 r'|generated by a tool and any changes will be overwritten|Automatically generated - do not modify'
                 r'|This class was (automatically )?generated by|auto generated by the swagger'
                 r'|This is a generated file\. Not intended for manual editing')

def drop_e1(text): return bool(GEN.search(text))


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(drop_e1(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** java. **Docs it touches:** java 10.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Stub files and jadx output with no marker are missed: 4 labelled java rows. Touches 1 doc labelled clean.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 123. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 11. `DA-E1-005` · E1 minified or generated code · drop · stage 30

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `4b53d240dabec20a`, `737965d79cc94955`, `83b3083721ee5df9`.
2. **Medicine:** Generator note in a comment line of the first 1500 characters, or a Kiota or goformation fingerprint.

```python
RULE_ID = "DA-E1-005"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp'}
ORIGIN = "code-cpp"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

GENERATED = re.compile(r"^[ \t]*(?://|/\*|\*)[^\n]*?(?:Code generated|generated by|auto-?generated|"
                       r"automatically generated|AutoRest Code Generator|自动生成)", re.I | re.M)

FINGERPRINT = re.compile(r"(?m)^\s*i[0-9a-f]{40,}\s+\"github\.com/microsoft/kiota|"
                         r"Specification Version that this resource was generated from")

def medicine_e1(doc):
    t = doc["text"]
    return ("drop" if GENERATED.search(t[:1500]) or FINGERPRINT.search(t[:3000]) else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e1(doc), doc["text"])
```

3. **Action:** drop. **Runs on:** cpp. **Docs it touches:** cpp 8.
4. **Harm test:** cpp 0.00% (0/120) PASS.
5. **Side effects:** A comment such as "the ID generated by the server" near the top would match.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 12. `DA-E1-007` · E1 minified or generated code · drop · stage 30

1. **Disease:** E1 minified or generated code. Labelled rows: go 43, rust 23, js-ts 23, java 14, cpp 20, python 11. Examples: `3c67c435782c8a77`, `9c1d218d257a6176`, `b5da9ac1658db525`.
2. **Medicine:** Generator marker in a comment line, or any line longer than 1000 characters.

```python
RULE_ID = "DA-E1-007"
CODE = "E1"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp'}
ORIGIN = "code-cpp"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

GENERATED = re.compile(r"(?im)^[ \t]*(?://|/?\*)[^\n]*(?:auto-generated file|do not (?:edit|modify)\b|decompiled (?:by|with)|"
                       r"code generated by|(?:file|class|code) (?:was|is|has been) (?:auto(?:matically)?[- ]?)?generated|"
                       r"generated by a tool)")

def m7_drop_generated(t: str):
    if GENERATED.search(t) or any(len(line) > 1000 for line in t.split("\n")):
        return None
    return t


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m7_drop_generated(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** cpp. **Docs it touches:** cpp 5.
4. **Harm test:** cpp 0.00% (0/120) PASS.
5. **Side effects:** A hand-written file with one very long line, such as a data table, is dropped.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 13. `DA-E2-001` · E2 data blobs · drop · stage 30

1. **Disease:** E2 data blobs. Labelled rows: go 7, rust 2, js-ts 1, java 1, cpp 1, python 1. Examples: `023d4d7c1524277f`, `637118880fa53f2f`, `8c1931d1524ec642`.
2. **Medicine:** Byte-array literals cover 10% or more of the file, or base64 runs 40% or more.

```python
RULE_ID = "DA-E2-001"
CODE = "E2"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "RaviNaik"
import re

_BYTES = re.compile(r"(?:0x[0-9a-fA-F]{2},\s*){24,}(?:0x[0-9a-fA-F]{2},?)?")

_B64 = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")

def drop_blob(text: str, share: float = 0.10, b64_share: float = 0.4):
    """Drop the file when byte-array literals cover at least `share` of it, or when base64-looking
    runs cover at least `b64_share`. Removing the array would break the Go code, so there is no fix."""
    if not text:
        return "keep", text
    n = len(text)
    if sum(len(m.group()) for m in _BYTES.finditer(text)) / n >= share:
        return "drop", text
    if sum(len(m.group()) for m in _B64.finditer(text)) / n >= b64_share:
        return "drop", text
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(drop_blob(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 7, rust 0, js-ts 0, java 0, cpp 1, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Smaller blobs stay: the labelled E2 rows of rust (2), js-ts (1), java (1) and python (1) are not caught.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, PR 36. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 14. `DA-C3-002` · C3 truncated or broken document · drop · stage 30

1. **Disease:** C3 truncated or broken document. Labelled rows: go 1, rust 0, js-ts 0, java 0, cpp 0, python 0. Examples: `a27e1273db746e7d`.
2. **Medicine:** Go lexical check fails: unclosed string, rune or block comment, or unbalanced brackets.

```python
RULE_ID = "DA-C3-002"
CODE = "C3"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

def _go_lexes(t):
    i, n, depth = 0, len(t), 0
    while i < n:
        c = t[i]
        if t.startswith("//", i):
            j = t.find("\n", i)
            i = n if j < 0 else j
        elif t.startswith("/*", i):
            j = t.find("*/", i + 2)
            if j < 0:
                return False
            i = j + 2
        elif c in "\"'":
            i += 1
            while i < n and t[i] != c:
                if t[i] == "\n":
                    return False
                i += 2 if t[i] == "\\" else 1
            if i >= n:
                return False
            i += 1
        elif c == "`":
            j = t.find("`", i + 1)
            if j < 0:
                return False
            i = j + 1
        else:
            depth += (c in "{([") - (c in "})]")
            if depth < 0:
                return False
            i += 1
    return depth == 0

def medicine_c3(doc):
    return ("keep" if _go_lexes(doc["text"]) else "drop", doc["text"])


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c3(doc), doc["text"])
```

3. **Action:** drop. **Runs on:** go. **Docs it touches:** go 1.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** Go only: it reads Rust lifetimes (`'a`) as unclosed runes. It is not a full parser.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 15. `DA-C4-002` · C4 two documents joined · drop · stage 30

1. **Disease:** C4 two documents joined. Labelled rows: go 0, rust 0, js-ts 0, java 1, cpp 1, python 0. Examples: `1227540794647c4d`.
2. **Medicine:** A separator line (20 or more `_` or `=`) or a "sample 12 ms submission" caption outside a comment.

```python
RULE_ID = "DA-C4-002"
CODE = "C4"
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

JOINED = re.compile(r"(?mi)^[ \t]*(?:_{20,}|={20,}|sample \d+ (?:ms|kb) submission)[ \t]*$")

def m9_drop_joined(t: str):
    return None if JOINED.search(t) else t


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m9_drop_joined(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** java. **Docs it touches:** java 1.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Java only: in python such a line can be a docstring heading.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 16. `DA-E4-005` · E4 repeated licence headers · fix+drop · stage 30

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `01180a3ddf4dfc23`, `0a0303df2fa01ea8`, `0c16883f44febd4f`.
2. **Medicine:** Drop on a restrictive licence phrase in the first 60 lines. Else delete a licence comment block of 4 or more lines in the Go header, a boxed header, or a block at the end. Build tags and package docs stay.

```python
RULE_ID = "DA-E4-005"
CODE = "E4"
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

LICENCE = re.compile(r"Licensed under|Licensed to the Apache|Permission is hereby granted|Redistribution and use|"
                     r"Use of this source code is governed by|This source code is licensed under|"
                     r"released under the \w+ licen[cs]e|General Public License|Mozilla Public License", re.I)

RESTRICTIVE = re.compile(r"(?i)free for personal use|commercial use requires|non-?commercial use only|"
                         r"commons clause|not for commercial use|for evaluation purposes only")

BLOCK = re.compile(r"(?:[ \t]*/\*[^\n]*\*/[ \t]*\n){2,}|/\*.*?\*/[ \t]*\n?|(?://[^\n]*\n)+", re.S)

TAIL = re.compile(r"\n((?:[ \t]*/\*[^\n]*\*/[ \t]*\n?){2,}|/\*(?:(?!\*/).)*\*/|(?://[^\n]*(?:\n|\Z))+)\s*\Z", re.S)

def _is_licence(block):
    return bool(LICENCE.search(block)) and block.count("\n") >= 4

def medicine_e4(doc):
    t = doc["text"]
    if RESTRICTIVE.search("\n".join(t.split("\n")[:60])):
        return ("drop", t)  # a restrictive licence: stripping the header would not make the code free to use
    body = re.search(r"^(?:import|func|type|var|const)\b", t, re.M)
    end = body.start() if body else len(t)
    head = BLOCK.sub(lambda m: "" if _is_licence(m.group()) else m.group(), t[:end])
    if head != t[:end]:
        head = head.lstrip("\n")
    new = head + t[end:]
    tail = TAIL.search(new)
    if body and tail and tail.start() > len(head) and _is_licence(tail.group(1)):
        new = new[:tail.start()] + "\n"
    return ("keep", t) if new == t else ("fix", new)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e4(doc), doc["text"])
```

3. **Action:** fix+drop. **Runs on:** go. **Docs it touches:** go 56.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** A licence block touching the package doc comment takes the doc with it. Removes the notice the licence asks to keep: record the licence in metadata first.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 17. `DA-E4-010` · E4 repeated licence headers · fix · stage 30

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `01180a3ddf4dfc23`, `0a0303df2fa01ea8`, `0c16883f44febd4f`.
2. **Medicine:** Delete a leading comment block of 5 or more lines that is at least 40% licence text. `#` lines count as comments on python only. Shebang, encoding and Go build lines stay. Repeats until nothing changes, for stacked headers.

```python
RULE_ID = "DA-E4-010"
CODE = "E4"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'python', 'rust'}
ORIGIN = "code-go, code-rust, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-rust"  # pack whose medicine this came from
AUTHOR = "amukka"
import re

MARKER_LINE = re.compile(r"^(?:<(?:reponame|filename|gh_stars)>[^\n]*)\n?")

LICENCE = re.compile(
    r"(?i)(licensed under|permission is hereby granted|redistribution and use|public domain"
    r"|this source code form|all rights reserved|without warranties|general public license"
    r"|affero|mit license|apache license|free software|copyright|warranty|spdx|redistribute"
    r"|the software|the terms|permitted|liability|licen[cs]e|apache|distributed|rights|dedicated"
    r"|modified, or|you may not use)"
)

COMMENT_LINE = re.compile(r"^\s*(//(?![!/])|/\*(?![!*])|\*|\*/|#)")

def _strip_marker(text: str) -> str:
    return MARKER_LINE.sub("", text, count=1)

def _licence_density(block: str) -> bool:
    """3+ licence lines and at least 40% of the non-blank lines are licence text."""
    lines = [l for l in block.split("\n") if l.strip(" /*#\t")]
    hits = sum(bool(LICENCE.search(l)) for l in lines)
    return hits >= 3 and hits * 10 >= len(lines) * 4

def e4_licence_header(text: str, comment_line=COMMENT_LINE):
    """E4: remove a leading comment block of 5+ lines that holds licence text.

    The block is either one /* ... */ comment or a run of // lines (single blank lines allowed
    inside). //! and /// doc comments are never part of it.
    """
    body = _strip_marker(text)
    prefix = text[: len(text) - len(body)]
    if body.lstrip().startswith("/*"):
        end = body.find("*/")
        block, rest = (body[: end + 2], body[end + 2 :]) if end != -1 else ("", body)
        n = block.count("\n") + 1
    else:
        lines = body.split("\n")
        n = 0
        i = 0
        while i < len(lines):
            if comment_line.match(lines[i]):
                n = i + 1
                i += 1
            elif not lines[i].strip() and i + 1 < len(lines) and comment_line.match(lines[i + 1]):
                i += 1
            else:
                break
        block, rest = "\n".join(lines[:n]), "\n".join(lines[n:])
    if n >= 5 and _licence_density(block):
        return "fix", prefix + rest.lstrip("\n")
    return "keep", text

NO_HASH = re.compile(r"^\s*(//(?![!/])|/\*(?![!*])|\*|\*/)")

KEEP_LINE = re.compile(r"^(#!|#.*coding[:=]|\s*//\s*(go:|\+build))")

def medicine_e4_fixed(doc):
    text = doc["text"]
    comment = COMMENT_LINE if doc.get("lang_label") == "python" else NO_HASH
    new = text
    while True:  # two stacked licence blocks: apply(apply(doc)) == apply(doc)
        action, out = e4_licence_header(new, comment)
        if action != "fix" or out == new:
            break
        new = out
    if new == text:
        return ("keep", text)
    now = set(new.split("\n"))
    kept = [l for l in text.split("\n")[:60] if KEEP_LINE.match(l) and l not in now]
    return ("fix", "\n".join(kept + [new]) if kept else new)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e4_fixed(doc), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, java, cpp, python. **Docs it touches:** go 51, rust 22, java 81, cpp 95, python 60.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Short 2 to 4 line notes stay. Removes the notice the licence asks to keep: record the licence in metadata first. **Changed from `DA-E4-004`:** see the decisions file.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-rust sheet, PR 52. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 18. `DA-E4-009` · E4 repeated licence headers · fix+drop · stage 30

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `0796334a27ed6607`, `0dd7bdea9580fa25`, `1a1a1d7ab0bf9188`.
2. **Medicine:** Drop on a restrictive licence phrase. Else delete the first licence comment block of 7 or more lines in the first 60 lines, or one at the end.

```python
RULE_ID = "DA-E4-009"
CODE = "E4"
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "RaviNaik"
import re

_LIC_WORDS = re.compile(
    r"(?i)licensed under|permission is hereby granted|without warranty|"
    r"you may not use this file|redistribut|general public license|all rights reserved|"
    r"warranties of|distributed under the licen"
)

_RESTRICTIVE = re.compile(
    r"(?i)free for personal use|commercial use requires|non-?commercial use only|commons clause|"
    r"not for commercial use|for evaluation purposes only"
)

def _comment_runs(lines, limit=60, tail=False):
    """Yield (start, end) of contiguous // runs, /* */ blocks and runs of one-line /* ... */ comments."""
    n = len(lines)
    rng = range(max(0, n - 40), n) if tail else range(0, min(n, limit))
    lo, hi = rng.start, rng.stop
    i = lo
    while i < hi:
        s = lines[i].strip()
        if s.startswith("/*") and s.endswith("*/") and len(s) > 4:
            j = i
            while j < n and lines[j].strip().startswith("/*") and lines[j].strip().endswith("*/"):
                j += 1
            yield i, j
            i = j
        elif s.startswith("/*"):
            j = i
            while j < n and "*/" not in lines[j]:
                j += 1
            yield i, j + 1
            i = j + 1
        elif s.startswith("//") and not s.startswith(("//go:", "// +build", "//+build")):
            j = i
            while j < n and lines[j].strip().startswith("//"):
                j += 1
            yield i, j
            i = j
        else:
            i += 1

def strip_licence_header(text: str, min_lines: int = 7):
    """Drop files whose header carries a restrictive licence. Otherwise remove the first
    comment block in the first 60 lines (or the last 40 lines) that has >= min_lines lines and
    licence grant text. Run this AFTER fix_b3 so the file starts at the real first line."""
    lines = text.split("\n")
    head = "\n".join(lines[:60])
    if _RESTRICTIVE.search(head):
        return "drop", text
    for tail in (False, True):
        for a, b in _comment_runs(lines, tail=tail):
            block = lines[a:b]
            if len(block) >= min_lines and sum(1 for x in block if _LIC_WORDS.search(x)) >= 2:
                kept = lines[:a] + lines[b:]
                return "fix", "\n".join(kept).strip("\n") + ("\n" if text.endswith("\n") else "")
    return "keep", text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(strip_licence_header(doc["text"]), doc["text"])
```

3. **Action:** fix+drop. **Runs on:** java. **Docs it touches:** java 82.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Short headers stay.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, PR 36. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 19. `DA-E4-007` · E4 repeated licence headers · fix · stage 30

1. **Disease:** E4 repeated licence headers. Labelled rows: go 76, rust 22, js-ts 9, java 103, cpp 176, python 70. Examples: `1e918efcbd1c6f4b`, `4aa682fef3c7ba0d`, `67c9226601f26da9`.
2. **Medicine:** Delete the first comment at the top when it is 10 or more lines and names Apache, MIT, GPL or "Permission is hereby granted".

```python
RULE_ID = "DA-E4-007"
CODE = "E4"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'javascript', 'typescript'}
ORIGIN = "code-js-ts"  # packs it runs on
SOURCE = "code-js-ts"  # pack whose medicine this came from
AUTHOR = "Sagar063"
import re

_LICENCE = re.compile(r"Licensed under the Apache License|Permission is hereby granted|"
                      r"GNU (Lesser |Affero )?General Public License|MIT License", re.I)

_TOP_COMMENT = re.compile(r"\A((?:<(?:reponame|filename|gh_stars)>[^<\n]*)+\n)?\s*"
                          r"(/\*.*?\*/[ \t]*\n?|(?:[ \t]*//[^\n]*\n)+)", re.S)

def medicine_e4(text):
    """Remove a licence comment of 10 or more lines at the top of the file."""
    m = _TOP_COMMENT.match(text)
    if m:
        block = m.group(2).rstrip("\n")
        if _LICENCE.search(block) and block.count("\n") + 1 >= 10:
            return (m.group(1) or "") + text[m.end():].lstrip("\n")
    return text


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e4(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** js-ts. **Docs it touches:** js-ts 6.
4. **Harm test:** js-ts 0.49% (1/204) PASS.
5. **Side effects:** Short notices stay. **Changes 1 js-ts gold doc** (`67c9226601f26da9`, a 21-line licence header the gold readers kept). That is within the limit of 2 and it is what the rule is for; the readers disagree on whether a real header is E4. Removes the notice the licence asks to keep: record the licence in metadata first.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-js-ts sheet, PR 115. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 20. `DA-C1-004` · C1 boilerplate · fix · stage 30

1. **Disease:** C1 boilerplate. Labelled rows: go 1, rust 0, js-ts 0, java 80, cpp 2, python 0. Examples: `45ac5026eac81b39`.
2. **Medicine:** Delete kubebuilder and operator-sdk scaffold notes ("EDIT THIS FILE!", "NOTE: json tags are required").

```python
RULE_ID = "DA-C1-004"
CODE = "C1"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'go'}
ORIGIN = "code-go"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

SCAFFOLD = re.compile(r'^[ \t]*//[ \t]*(?:EDIT THIS FILE!.*|NOTE: json tags are required\..*|'
                      r'Important: Run "make" to regenerate code after modifying this file.*|'
                      r'INSERT ADDITIONAL (?:SPEC|STATUS) FIELDS?.*)\n', re.M)

def medicine_c1(doc):
    t = SCAFFOLD.sub("", doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_c1(doc), doc["text"])
```

3. **Action:** fix. **Runs on:** go. **Docs it touches:** go 2.
4. **Harm test:** go 0.00% (0/163) PASS.
5. **Side effects:** Other generators' scaffold notes are not covered.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 21. `DA-C1-005` · C1 boilerplate · fix · stage 30

1. **Disease:** C1 boilerplate. Labelled rows: go 1, rust 0, js-ts 0, java 80, cpp 2, python 0. Examples: `077f2bc49b1bb6db`, `0b893004aea9459b`, `1397a887d14c0fae`.
2. **Medicine:** Delete IDE template lines and the template part of a header comment ("To change this template", "Created by ... on").

```python
RULE_ID = "DA-C1-005"
CODE = "C1"
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'java'}
ORIGIN = "code-java"  # packs it runs on
SOURCE = "code-java"  # pack whose medicine this came from
AUTHOR = "vaibh27"
import re

LIC_WORDS = re.compile(r"licen[cs]e|permission is hereby granted|redistribution and use", re.I)

NOT_LICENCE = re.compile(r"to change this licen[cs]e header|choose licen[cs]e headers", re.I)

IDE_LINE = re.compile(r"(?im)^[ \t]*//[ \t]*TODO Auto-generated (?:method|constructor|catch block|stub)[^\n]*\n")

BLOCK = re.compile(r"[ \t]*/\*.*?\*/[ \t]*\n?", re.S)

IDE_MARK = re.compile(r"(?im)TODO Auto-generated|To change this (?:licen[cs]e header|template)|choose Tools \| Templates|"
                      r"Created (?:by|with) IntelliJ IDEA|Created by [^\n]{1,80}? on \d|File \| Settings \| File Templates|"
                      r"^\s*\*?\s*User\s*:.*\n\s*\*?\s*Date\s*:|^\s*\*?\s*@(?:project|package)\s*[:：]|\$\{[\w.]{1,40}\}|"
                      r"^\s*\*?\s*<p>\s*Title\s*[:：]")

EMPTY_DESC = re.compile(r"(?im)^\s*\*?\s*@?desc(?:ription)?\s*[:：]*\s*(?:TODO)?\s*$")

AUTHOR_DATE = re.compile(r"(?im)^\s*\*?\s*@?(?:author|user)\b(?:.*\n)*?\s*\*?\s*@?(?:date|create|created)\s*[:：]")

TEMPLATE_LINE = re.compile(r"(?i)^\s*(?:/\*+|\*+)?\s*(?:<p>\s*)?(?:@?(?:author|user|date|time|class|project|package|create|created|"
                           r"version|since|title)\b\s*[:：]?.*|desc(?:ription)?\s*[:：]?\s*(?:TODO)?\s*(?:</p>)?|Created (?:by|with) .*|"
                           r"To change this .*|choose .*Templates.*|and open the template.*|TODO Auto-generated.*|"
                           r"(?:copyright|e-?mail|blog|company)\b.*)\s*$")

AUTHOR_ONLY = re.compile(r"/\*\*(?:\s*\*)*\s*@author\b[^\n]*(?:\s*\*)*\s*/")

def _clean_ide_block(block: str) -> str:
    if LIC_WORDS.search(block) and not NOT_LICENCE.search(block):
        return block  # a licence goes with M4
    if AUTHOR_ONLY.fullmatch(block.strip()):  # empty Javadoc with one @author line (labelled B4 only for <NAME>)
        return ""
    if not (IDE_MARK.search(block) or (EMPTY_DESC.search(block) and AUTHOR_DATE.search(block))):
        return block
    body = block.rstrip("\n")
    lines, end = body.split("\n"), block[len(body):]  # end: the newline after */
    inner = [l for l in lines[1:-1] if not TEMPLATE_LINE.match(l) and l.strip(" \t*")]
    if len(lines) < 3 or not inner:
        return ""  # nothing but the template
    return "\n".join([lines[0]] + [l for l in lines[1:-1] if not TEMPLATE_LINE.match(l)] + [lines[-1]]) + end

def m6_strip_ide_templates(t: str) -> str:
    t = IDE_LINE.sub("", t)
    return BLOCK.sub(lambda m: _clean_ide_block(m.group()), t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(m6_strip_ide_templates(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** java. **Docs it touches:** java 79.
4. **Harm test:** java 0.00% (0/116) PASS.
5. **Side effects:** Only one java reader labels these; the other two mark 23 of the touched docs clean. It only touches comments.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-java sheet, PR 48. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 22. `DA-B4-009` · B4 template junk / PII placeholders · fix · stage 40

1. **Disease:** B4 template junk / PII placeholders. Labelled rows: go 45, rust 18, js-ts 25, java 83, cpp 122, python 27. Examples: `0f4121b3b47fc3e0`, `1398b525d923d644`, `14a63d176ed55369`.
2. **Medicine:** `<NAME>` -> `AUTHOR`, `<EMAIL>` -> `user@example.com`, `<KEY>` -> `EXAMPLE_KEY`, `<PASSWORD>` -> `EXAMPLE_PASSWORD`.

```python
RULE_ID = "DA-B4-009"
CODE = "B4"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

NEUTRAL = {"<NAME>": "AUTHOR", "<EMAIL>": "user@example.com", "<KEY>": "EXAMPLE_KEY", "<PASSWORD>": "EXAMPLE_PASSWORD"}

PLACEHOLDER = re.compile("|".join(map(re.escape, NEUTRAL)))

def medicine_b4(doc):
    t = PLACEHOLDER.sub(lambda m: NEUTRAL[m.group()], doc["text"])
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_b4(doc), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 43, rust 18, js-ts 30, java 82, cpp 121, python 83.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Cannot repair code that the redaction cut (C3 drops that file). A neutral word is still not the true author.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 23. `DA-E3-003` · E3 secrets · fix · stage 40

1. **Disease:** E3 secrets. Labelled rows: go 1, rust 1, js-ts 9, java 1, cpp 0, python 0. Examples: `98e4c493f32c8bfa`.
2. **Medicine:** Known key formats (AWS, GitHub, `sk-`, Slack, PEM) and base32 seeds assigned to secret, seed or otp names become `EXAMPLE_SECRET`.

```python
RULE_ID = "DA-E3-003"
CODE = "E3"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "code-go"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import re

KEYS = [re.compile(p) for p in (r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"\bsk-[A-Za-z0-9_-]{20,}",
        r"xox[baprs]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")]

SEED = re.compile(r'(?i)((?:secret|seed|totp|otp)\w*\s*:?=\s*")[A-Z2-7]{16,}(")')

def medicine_e3(doc):
    t = doc["text"]
    for rx in KEYS:
        t = rx.sub("EXAMPLE_SECRET", t)
    t = SEED.sub(r"\1EXAMPLE_SECRET\2", t)
    return ("fix" if t != doc["text"] else "keep", t)


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e3(doc), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 1, rust 0, js-ts 0, java 0, cpp 0, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** Secrets with no known format and no telling name are missed. A public test vector is replaced too.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## 24. `DA-E3-004` · E3 secrets · fix · stage 40

1. **Disease:** E3 secrets. Labelled rows: go 1, rust 1, js-ts 9, java 1, cpp 0, python 0. Examples: `85fa4d03a2a63982`, `0d3bff117f465b99`, `8302c459b07901ca`.
2. **Medicine:** Replace a secret with `EXAMPLE_SECRET` and keep the file. Two kinds: known formats (Google, AWS, GitHub, Stripe, SendGrid, Slack, JWT, PEM), and a quoted value of 16 or more characters assigned to a secret-like name or passed to `new Pusher(`. The value must look random: mixed letters and digits, at least 15% digits, no dots, no dummy words such as `test` or `example`.

```python
RULE_ID = "DA-E3-004"
CODE = "E3"
ACTION = "fix"
STAGE = "40"
STATUS = "CANDIDATE"
LANGS = {'cpp', 'go', 'java', 'javascript', 'python', 'rust', 'typescript'}
ORIGIN = "code-go, code-rust, code-js-ts, code-java, code-cpp, code-python"  # packs it runs on
SOURCE = "new rule, written for this sheet"  # pack whose medicine this came from
AUTHOR = "TEJASKUMAR-REDDY-J"
import math
import re

PLACEHOLDER = "EXAMPLE_SECRET"

KNOWN = [re.compile(p) for p in (
    r"\bAIza[0-9A-Za-z_\-]{35}\b",                                   # Google API key
    r"\bAKIA[0-9A-Z]{16}\b",                                         # AWS access key
    r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",                               # GitHub token
    r"\bgithub_pat_[A-Za-z0-9_]{40,}\b",                             # GitHub fine-grained token
    r"\bsk-[A-Za-z0-9_\-]{20,}\b",                                   # sk- API key
    r"\b[rs]k_live_[0-9A-Za-z]{16,}\b",                              # Stripe live key
    r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b",             # SendGrid key
    r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b",                            # Slack token
    r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",  # JWT
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
)]

ASSIGNED = re.compile(
    r"""(?ix)
    (?P<head>
      \b[\w\-]*(?:secret|token|api[_\-]?key|app[_\-]?key|auth[_\-]?key|access[_\-]?key|client[_\-]?key|private[_\-]?key|passw(?:or)?d|pwd|\bkey)[\w\-]*
      ["']?
      (?:\s*:\s*&?(?:'\w+\s+)?[\w<>\[\]]{1,20})?   # Rust and TypeScript types: SECRET: &'static str = "..."
      \s*(?::=|=>|=|:)\s*
      (?P<quote>["'`])
    )
    (?P<value>[^"'`\s\\]{16,200})
    (?P=quote)
    """)

SDK_KEY = re.compile(r"""(?P<head>\bnew\s+Pusher\(\s*(?P<quote>["'`]))[0-9a-fA-F]{16,}(?P=quote)""")

DUMMY = re.compile(r"(?i)example|sample|dummy|test|fake|mock|placeholder|changeme|change_me|your|xxxx|0000|1234|abcd|secret|password|token|<|>|\$\{|\{\{|%s")

def _entropy(v):
    n = len(v)
    return -sum(c / n * math.log2(c / n) for c in (v.count(ch) for ch in set(v)))

def _looks_random(v):
    """A real key is a run of mixed letters and digits, not a word, an identifier, a path, a version or a dummy."""
    if DUMMY.search(v) or "." in v or v.count("/") > 2:
        return False
    if not (re.search(r"[0-9]", v) and re.search(r"[A-Za-z]", v)):  # enum names and plain words have no digits
        return False
    if sum(ch.isdigit() for ch in v) < 0.15 * len(v):                # user_profile_settings_v2
        return False
    return _entropy(v) >= 3.0

def medicine_e3(text):
    new = text
    for rx in KNOWN:
        new = rx.sub(PLACEHOLDER, new)
    new = SDK_KEY.sub(lambda m: m.group("head") + PLACEHOLDER + m.group("quote"), new)
    new = ASSIGNED.sub(lambda m: m.group("head") + PLACEHOLDER + m.group("quote") if _looks_random(m.group("value")) else m.group(0), new)
    return new


def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)


def medicine(doc):
    if doc.get("lang_label") not in LANGS:
        return ("keep", doc["text"])
    return _std(medicine_e3(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** go, rust, js-ts, java, cpp, python. **Docs it touches:** go 0, rust 1, js-ts 2, java 1, cpp 0, python 0.
4. **Harm test:** go 0.00% (0/163) PASS; rust 0.00% (0/78) PASS; js-ts 0.00% (0/204) PASS; java 0.00% (0/116) PASS; cpp 0.00% (0/120) PASS; python 0.00% (0/46) PASS.
5. **Side effects:** A key with no digits, or under 16 characters, or under a neutral variable name is missed. A random-looking ID stored under a name like `key` is replaced too; it only changes a string, so the code still parses. Not a full scanner: gitleaks or trufflehog would catch more.
6. **Spec v1:** status CANDIDATE, reviewer pending. Source: code-go sheet, an updated `medicine.md`, not in PR 73 yet. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS.

## Harm test of the whole sheet, in run order

| pack | gold | gold changed | gold dropped | harm | result | pack fixed / dropped / untouched | labelled rows treated | labelled-clean docs changed outside gold |
|---|---|---|---|---|---|---|---|---|
| go | 163 | 0 | 0 | 0.00% | PASS | 265 / 44 / 191 | 309 / 337 | 5 |
| rust | 78 | 0 | 0 | 0.00% | PASS | 238 / 17 / 245 | 255 / 259 | 0 |
| js-ts | 204 | 1 | 0 | 0.49% | PASS | 264 / 22 / 214 | 286 / 296 | 22 |
| java | 116 | 0 | 0 | 0.00% | PASS | 350 / 11 / 139 | 361 / 384 | 30 |
| cpp | 120 | 0 | 0 | 0.00% | PASS | 343 / 10 / 147 | 353 / 378 | 1 |
| python | 46 | 0 | 0 | 0.00% | PASS | 325 / 16 / 159 | 336 / 343 | 8 |
