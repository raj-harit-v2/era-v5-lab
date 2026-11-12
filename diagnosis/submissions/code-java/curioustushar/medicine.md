# Medicine sheet: code-java (curioustushar)

Pack: `code-java`, 500 documents from `bigcode/starcoderdata:java`. Labelled: 500 rows in `labels.csv`.
Counts below: labelled rows with the disease, then **whole-pack** documents the medicine would touch.

Run medicines in order: **M1, M3, M2, M5, M4**. M5 (C1) runs before M4 so NetBeans "license header" templates are not mistaken for E4.

## Harm test status

Gold set: `teams/01-data-a/gold/code-java_gold.csv` (**116** documents, two-reader clean set).
Tool: `teams/01-data-a/tools/harm_test.py` on `code-java.parquet`. Pass limit: **1** document changed or dropped (`max(1, 1% of 116)`).

| Rule | Changed | Dropped | Result |
|------|--------:|--------:|--------|
| B3 (M1) | 0 | 0 | **PASS** |
| B4 (M2) | 0 | 0 | **PASS** |
| A2 (M3) | 0 | 0 | **PASS** |
| E4 (M4) | 0 | 0 | **PASS** |
| C1 (M5) | 0 | 0 | **PASS** |
| All sections in file order | 0 | 0 | **PASS** |

Command (from repo root):

```
python -I teams/01-data-a/tools/harm_test.py \
  --pack <path-to>/code-java.parquet \
  --gold teams/01-data-a/gold/code-java_gold.csv \
  --rules diagnosis/submissions/code-java/curioustushar/medicine.md \
  --rule all
```

## Medicine 1: StarCoder metadata header (B3)

1. **Disease:** B3. Count: **250** of 500 labelled; **250** of 500 in the pack.
   - `d0947d80d45f7ce3`: <filename> at offset 0
   - `c9eb2d8e4f9cacde`: <reponame> at offset 0
   - `a8a876672781cd58`: <reponame> at offset 0
2. **Medicine:**
   ```python
META_HEAD = re.compile(r"\A(?:<reponame>[^<\n]*|<filename>[^<\n]*|<gh_stars>[^<\n]*)+\n")

def m1_strip_meta_header(t: str) -> str:
    return META_HEAD.sub("", t, count=1)
   ```
3. **Action:** fix.
4. **Harm test:** 0 changed, 0 dropped of 116 gold documents; **PASS** (limit 1).
5. **Side effects:** Repo path metadata is removed; anchor is line 0 only.

## Medicine 2: PII redaction placeholders (B4)

1. **Disease:** B4. Count: **83** of 500 labelled; **82** of 500 in the pack.
   - `13a397d8bedc6210`: <NAME> at offset 159 + <EMAIL> at offset 167
   - `8c9a9aa845f91a2c`: <EMAIL> at offset 284 + <PASSWORD> at offset 321
   - `4b761af28be90423`: <filename> at offset 0 + <gh_stars> at offset 35
2. **Medicine:**
   ```python
SURROGATE = {"<EMAIL>": "user@example.com", "<NAME>": "Author Name", "<PASSWORD>": "password"}

def m2_surrogate_placeholders(t: str) -> str:
    for k, v in SURROGATE.items():
        t = t.replace(k, v)
    return t
   ```
3. **Action:** fix.
4. **Harm test:** 0 changed, 0 dropped of 116 gold documents; **PASS** (limit 1).
5. **Side effects:** Placeholder tokens in pack: 54 `EMAIL`, 1 `KEY`, 118 `NAME`, 21 `PASSWORD`. Does not fix unredacted phones (F1).

## Medicine 3: CRLF line endings (A2)

1. **Disease:** A2. Count: **44** of 500 labelled; **44** of 500 in the pack.
   - `e0ebe203093970dc`: U+000D (CRLF) at offsets 17, 19, 45
   - `7fc99d2b6e1e3d08`: U+000D (CRLF) at offsets 2, 38, 63
   - `1a1a1d7ab0bf9188`: U+000D (CRLF) at offsets 2, 56, 60
2. **Medicine:**
   ```python
def m3_normalise_newlines(t: str) -> str:
    return t.replace("\r\n", "\n").replace("\r", "\n")
   ```
3. **Action:** fix.
4. **Harm test:** 0 changed, 0 dropped of 116 gold documents; **PASS** (limit 1).
5. **Side effects:** Does not change escaped \"\\r\\n\" inside string literals.

## Medicine 4: Licence headers (E4)

1. **Disease:** E4. Count: **99** of 500 labelled; **99** of 500 in the pack.
   - `5655154f71365c63`: 18-line licence header at offset 0
   - `7fc99d2b6e1e3d08`: 4-line licence header at offset 0
   - `86534a30f79557fb`: 13-line licence header at offset 0
2. **Medicine:**
   ```python
LIC_HEAD = re.compile(r"\A(\s*)/\*.*?\*/[ \t]*\n", re.S)
LIC_WORDS = re.compile(r"licen[cs]e|permission is hereby granted", re.I)

def m4_strip_licence_header(t: str) -> str:
    m = LIC_HEAD.match(t)
    if not m or not LIC_WORDS.search(m.group()):
        return t
    if not re.match(r"\s*(package|import)\b", t[m.end():]):
        return t
    return t[m.end():].lstrip("\n")
   ```
3. **Action:** fix.
4. **Harm test:** 0 changed, 0 dropped of 116 gold documents; **PASS** (limit 1).
5. **Side effects:** Skips NetBeans template comments (C1). Misses some //-line and short copyright-only headers; see labels.

## Medicine 5: IDE and generator boilerplate (C1)

1. **Disease:** C1. Count: **69** of 500 labelled; **69** of 500 in the pack.
   - `e0ebe203093970dc`: 3-line IntelliJ template comment at offset 108
   - `c9eb2d8e4f9cacde`: 3-line IntelliJ template comment at offset 437
   - `50e06974390e57ea`: 5-line NetBeans template comment at offset 0 + empty Javadoc with only @author at offset 332
2. **Medicine:**
   ```python
NETBEANS = re.compile(
    r"\A\s*/\*\s*\n\s*\*\s*To change this license header.*?\*/\s*\n",
    re.S | re.I)
INTELLIJ = re.compile(
    r"\A\s*/\*\*?\s*\r?\n\s*\*\s*Created by [^\n]+\r?\n\s*\*/\s*\n",
    re.M)

def m5_strip_ide_boilerplate(t: str) -> str:
    for rx in (NETBEANS, INTELLIJ):
        t = rx.sub("", t, count=1)
    return t
   ```
3. **Action:** fix.
4. **Harm test:** 0 changed, 0 dropped of 116 gold documents; **PASS** (limit 1).
5. **Side effects:** Does not remove class Javadoc or real documentation. Empty @author-only blocks inside classes need a separate rule.
