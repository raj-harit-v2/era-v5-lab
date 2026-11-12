# Medicine sheet: cadj-stackexchange (tanmays369)

Pack: 500 StackOverflow documents. Every document is a question plus its answers, written as one text with `<issue_start>`, `<issue_comment>` and `Upvotes:` markers.

Counts below are rows in `labels.csv`.

Harm test: no `cadj-stackexchange` gold file exists in `teams/02-data-b/gold/` or in the Data A gold folder. Every row I labelled is `fix`, so this sheet gives no clean vote either. Result for every medicine: **gold set empty, not testable**. I will run the test when a gold file for this pack exists.

## Medicine 1: B3 ghost chat markers (500 of 500 documents)

1. **Disease:** B3. Examples: `87116d4f6facd13b` (`<issue_start>` at offset 0, `<issue_comment>` at 302), `c9e11c8baa07c6e0` (`<issue_comment>` at 944), `d78b5eeab23e7a55` (`<issue_comment>` at 302).
2. **Medicine:**
```python
import re
MARK = re.compile(r"<issue_start>|<issue_comment>|username_\d+:|Upvotes: -?\d+(?: \[selected_answer\])?\s*")
def fix_b3(text):
    return MARK.sub("\n", text).strip()
```
3. **Action:** fix the text.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** a post that really talks about these tokens loses them. Question and answers run together after the strip, so a rule that splits them first is better.

## Medicine 2: B2 stripped markup remnants (139 documents)

1. **Disease:** B2. The converter removed `<...>` content and left remnants: empty code fences, a lone `php` line where `<?php` was (also indented, and `php ...` code lines whose `<?` was stripped), an empty `#include`, `xml version=...?`, a loop header cut at `<`, text left in a code block where the HTML was, and a stripped tag name leaving a double space in prose ("I use a  tag", 3 documents). Back-to-back fences (a closing fence followed by a new opening fence, e.g. ` ``` ` then ` ```css `) are block boundaries, not empty blocks, and do not count. Examples: `d78b5eeab23e7a55` (lone `php` at offset 675), `71acfee0eb411a72` (lone `php` at 1046), `3e38237c513072d4` (text-only block at 545).
2. **Medicine:**
```python
import re
FENCE = re.compile(r"```")
REMNANT = re.compile(r"(?m)^[ \t]*php\s*$|^\s*#include\s*$|^\s*#import\s*$|^\s*xml version=.*$|!\[\]\(\)")
LOOP_CUT = re.compile(r"(?m)^[ \t]*(?:for|while|if)\s*\([^()\n]*[A-Za-z0-9_\]\.]\s*\n(?=[ \t]*(?:```|\n|$))")
def empty_fences(text):
    # pair fences sequentially: an opener whose block holds only whitespace is empty.
    # a naive ```...``` search also fires on close->open boundaries; pairing avoids that.
    fences = [m.start() for m in FENCE.finditer(text)]
    out = []
    for j in range(0, len(fences) - 1, 2):
        eol = text.find("\n", fences[j] + 3)
        if eol != -1 and text[eol + 1:fences[j + 1]].strip() == "":
            out.append(fences[j])
    return out
def has_b2(text):
    return bool(empty_fences(text) or REMNANT.search(text) or LOOP_CUT.search(text))
```
3. **Action:** drop the document when the code is the point of the question; remove an empty fence when it is only decoration.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** a fence that is empty on purpose is dropped too. The code in these documents cannot be restored. Stripped generics inside code (for example `new ArrayList()`) cannot be detected.

## Medicine 3: B4 PII placeholders (53 documents)

1. **Disease:** B4. Examples: `32407cff5d9572ab` (`<PASSWORD>` at offset 410), `a06ac825948fcdf1` (`<NAME>` at 1239), `b22bb720406e96c8` (`<NAME>` at 477, 817, 1119).
2. **Medicine:**
```python
import re
PII = re.compile(r"<(?:NAME|EMAIL|PASSWORD|KEY)>")
def fix_b4(text):
    return PII.sub("", text)
```
3. **Action:** fix the text. If a placeholder sits inside code or a sentence that needs the value, drop the document.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** the sentence can lose its subject.

## Medicine 4: B5 escaped characters inside code (63 documents)

1. **Disease:** B5, nearest code. Markdown escapes were added inside code: `\_` for `_`, `/\*` for `/*`, `**name**` for `__name__`, and a bare `\*` for `*` in pointer declarations, multiplication, and one Java regex string (`struct s \*p`, `1 \* new Date()`, `"(.\*?)"` for `"(.*?)"`, 6 documents). Examples: `9a421950f1fe4228` (offset 294), `e41552c03df638c4` (46 times from offset 941), `9211637c2d9105fd` (5 times from 1985), `972def12422daf14` (offset 3143).
2. **Medicine:**
```python
import re
CODE = re.compile(r"```[A-Za-z0-9_+-]*[ \t]*\n(.*?)```|`([^`\n]+)`", re.S)
def fix_b5(text):
    def unescape(m):
        s = m.group(0)
        return s.replace("\\_", "_").replace("/\\*", "/*").replace("\\*/", "*/")
    return CODE.sub(unescape, text)
```
3. **Action:** fix the text. `fix_b5` below handles `\_` and comment markers; the 6 bare-`\*` documents need the backslash removed by hand (only outside regex, where `\*` is a deliberate literal-star).
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** a regex that really contains `\_` is changed. I only touch `\_` and the comment markers for that reason; a blanket `\*` to `*` rule would corrupt real regexes such as `/a\*b/`.

## Medicine 5: C4 and H2 answer thread shared between documents (C4 104, H2 186 documents)

1. **Disease:** the same answer thread appears under two unrelated questions. The document whose question matches the thread is the owner (H2). The one whose question does not match is the copy (C4 and H2). Examples: copy `b33feafa5645bc5a` and owner `578eb1503702a79d` (2266 characters shared); copy `9a421950f1fe4228` and owner `796f4f8329c2ee55` (2581 characters).
2. **Medicine:**
```python
import re
def thread(text):
    i = text.find("<issue_comment>")
    return text[i:] if i >= 0 else ""
def key(text):
    return re.sub(r"\s+", " ", thread(text)).strip()[:100]
def dedupe(docs, related):
    groups = {}
    for d in docs:
        groups.setdefault(key(d["text"]), []).append(d)
    keep = []
    for g in groups.values():
        owners = [d for d in g if related(d["text"])]
        keep += owners[:1] if owners else g[:1]
    return keep
```
   `related(text)` is TF-IDF cosine between the question and its thread, at least max(0.03, 0.3 times the best score in the group).
3. **Action:** drop the C4 copy; keep one H2 owner.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** two related questions can share a thread legitimately and the similarity score can pick the wrong owner. Some owner/copy calls were fixed by hand.

## Medicine 6: A2 carriage returns (29 documents)

1. **Disease:** A2. The hex column shows `0D CARRIAGE RETURN`. Examples: `c690c0c539e5374d` (69 times from offset 573), `b9203642a7704098` (28 times from 527), `caab0dbaa0d7211e` (126 times from 590).
2. **Medicine:**
```python
def fix_a2(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")
```
3. **Action:** fix the text.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** none that I know of. Code that depends on CRLF is rare in this pack.

## Found but not given a medicine

- U+FFFD that appears inside a quoted example in an encoding question: kept as content, not A4.
- Text-only code blocks that are plain data (tables, commands, sample output): not B2.

The medicines may also work on other `cadj-` StackOverflow packs, but I have not checked.
