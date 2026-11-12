# Medicine sheet: code-cpp (rahulni)

One section for each disease found more than five times in the 500 documents of `code-cpp`
(`bigcode/starcoderdata`, all `lang_label = cpp`). Counts come from my `labels.csv`.

| Code | Disease | Documents | Action | Gold changed | Gold dropped | Harm test |
|---|---|---|---|---|---|---|
| A1 | invisible junk characters (U+FEFF) | 12 | fix | 0 | 0 | PASS |
| A2 | control characters (CR in CRLF line ends) | 47 | fix | 0 | 0 | PASS |
| B3 | ghost markers (StarCoder metadata line) | 245 | fix | 0 | 0 | PASS |
| B4 | PII placeholders and unfilled template variables | 122 | fix | 0 | 0 | PASS |
| D1 | wrong language label (C, C++/CLI, Objective-C++) | 10 | drop from cpp (relabel) | 0 | 0 | PASS |
| E1 | generated code | 19 | drop | 0 | 0 | PASS |
| E4 | repeated licence headers | 85 | fix | 0 | 0 | PASS |
| all seven, in this order | | | | 0 | 0 | PASS |

**Gold set.** `teams/01-data-a/gold/code-cpp_gold.csv` from Data A's PR #140 (head `c3cb003`, 31 Oct): 120 documents
that two readers labelled `full, clean`. The limit is `max(1, floor(1% of 120)) = 1` document changed or dropped.
I labelled all 120 of them clean too.

**How to rerun** (from the repo root, with the pack file next to it):

```
python -I teams/01-data-a/tools/harm_test.py --pack code-cpp.parquet \
  --gold teams/01-data-a/gold/code-cpp_gold.csv \
  --rules diagnosis/submissions/code-cpp/rahulni/medicine.md --rule all
```

Each rule below is one function. A rule that takes `text` returns the new text. A rule that takes `doc` (`doc_id`,
`text`, `url`, `lang_label`) returns `True` to take the document out. Every block runs on its own.

**Pack check.** Besides the gold set, I ran each rule on all 500 documents and compared the result with my labels:
A1, A2, B3, B4 and D1 fire on exactly the documents I labelled. The differences for E1 and E4 are under Side effects.

---

## Medicine 1

1. **Disease:** A1, 12 documents. U+FEFF (byte-order mark) in the text: at offset 0 (8 documents), or at the start
   of line 2, right after the StarCoder metadata line (4 documents).
   - `782bc9665f0acdf7`: U+FEFF at offset 0
   - `de12a2fd152768d6`: U+FEFF at offset 0
   - `6cdc9866d4264258`: U+FEFF at offset 0
2. **Medicine:** delete every U+FEFF. ZWJ and ZWNJ are not touched.

```python
def medicine_a1(text):
    return text.replace("\ufeff", "")
```

3. **Action:** fix.
4. **Harm test:** 0 of 120 gold documents changed, 0 dropped. PASS.
5. **Side effects:** a string or character literal that holds a raw U+FEFF on purpose (code that detects a BOM)
   would lose it. There is none in this pack: every U+FEFF here is the BOM of the original file.

## Medicine 2

1. **Disease:** A2, 47 documents. Windows line ends: U+000D (CR) before each newline.
   - `09b5f5db05cc311d`: 29 x U+000D, offsets 61-818
   - `d5e1b337f212f4e2`: 386 x U+000D, offsets 105-12647
   - `11edb16ce89987d8`: 111 x U+000D, offsets 32-2744
2. **Medicine:** turn every CRLF into LF, and any lone CR into LF. The pack has no other control characters.

```python
def medicine_a2(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")
```

3. **Action:** fix.
4. **Harm test:** 0 of 120 gold documents changed, 0 dropped. PASS.
5. **Side effects:** a CR that is data, for example inside a raw string literal that tests CRLF handling, becomes
   LF and changes what the program does. I saw none in this pack.

## Medicine 3

1. **Disease:** B3, 245 documents. The StarCoder metadata line at the start of the text: a marker and its value,
   for example `<reponame>` + repository, `<filename>` + path, `<gh_stars>` + count.
   - `83dc5d60eaef6288`: `<reponame>` at offset 0
   - `3a7b03b626595019`: `<filename>` at offset 0
   - `a800be93ce443cb5`: `<gh_stars>` at offset 0
2. **Medicine:** if the text starts with `<reponame>`, `<filename>` or `<gh_stars>`, delete that whole first line.
   The markers are always together on line 1 in this pack. After the rule, no marker is left anywhere in the 500 documents.

```python
import re

_MARKER_LINE = re.compile(r"\A<(?:reponame|filename|gh_stars)>[^\n]*(?:\n|\Z)")


def medicine_b3(text):
    return _MARKER_LINE.sub("", text, count=1)
```

3. **Action:** fix.
4. **Harm test:** 0 of 120 gold documents changed, 0 dropped. PASS.
5. **Side effects:** the repository, path and star count are lost from the text (the `url` column still has the
   path). A real file whose first line starts with one of these tags would lose that line. The same words later in
   a file, for example a usage string `<filename>`, are not touched.

## Medicine 4

1. **Disease:** B4, 122 documents. Placeholders from the earlier PII cleaning (`<NAME>` 189 times, `<EMAIL>` 43,
   `<PASSWORD>` 3) and, in one file, unfilled IDE template variables (`%{AUTHOR}`). They are not personal data.
   - `ab726af7ee73aa3b`: `<NAME>` at offset 25
   - `0797d20110e8ab9b`: `<EMAIL>` at offsets 13499, 29911, 33100
   - `c35b0e60b77787b6`: `<PASSWORD>` at offsets 7732, 8169
2. **Medicine:** delete each placeholder. Also delete the brackets that only held one (`<<EMAIL>>`, `(<EMAIL>)`),
   the separator in front of a listed one (`, <NAME>`, ` and <NAME>`), and the spaces left at the end of the line.
   For example `Copyright (c) <NAME>, <NAME>, <NAME>` becomes `Copyright (c)`, and `// TODO(<EMAIL>): ...` becomes
   `// TODO: ...`. Deleting is better than a fake name, because a fake name repeated over the corpus is junk again.

```python
import re

_P = r"(?:<(?:NAME|EMAIL|PASSWORD)>|%\{[A-Z_]+\})"
_WRAPPED = re.compile(r"[ \t]*[<(\[]" + _P + r"[>)\]]")
_LISTED = re.compile(r"(?:,[ \t]*|[ \t]+and[ \t]+)" + _P)
_LEFT = re.compile(_P + r"(?:,[ \t]*)?")


def medicine_b4(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "<" not in line and "%{" not in line:
            continue
        new = _LEFT.sub("", _LISTED.sub("", _WRAPPED.sub("", line)))
        if new != line:
            cr = "\r" if new.endswith("\r") else ""
            lines[i] = new.rstrip("\r").rstrip(" \t") + cr
    return "\n".join(lines)
```

3. **Action:** fix.
4. **Harm test:** 0 of 120 gold documents changed, 0 dropped. PASS.
5. **Side effects:**
   - A placeholder in the middle of a sentence leaves two spaces: `// Created by <NAME> on 2021/5/13.` becomes
     `// Created by  on 2021/5/13.`
   - In code, `m_password("<PASSWORD>")` becomes `m_password("")`. It still compiles, but the value changes.
   - A real tag or usage text written exactly `<NAME>`, `<EMAIL>` or `<PASSWORD>` would be deleted. In this pack every
     one is a placeholder. `<KEY>` is left out on purpose, because a template argument such as `std::set<KEY>` is real C++.

## Medicine 5

1. **Disease:** D1, 10 documents. The text is not C++ but is labelled `cpp`: plain C (6), C++/CLI or C++/CX (3),
   Objective-C++ (1).
   - `8835e7c1785d8efd`: C, `#include <stdio.h>` at 114, no C++ construct in the file
   - `14668e6a71171ef5`: C++/CLI, `#using <System.Xml.dll>` at 919
   - `cbac9cb9fb6765bb`: Objective-C++, `@interface AppDelegate` at 2228
2. **Medicine:** the label is wrong, not the text, so this rule reads the whole document and returns `True` to take
   it out of the cpp stream:
   - C++/CLI or C++/CX: `#using <`, `ref class`, `ref new`, `gcnew` or `value class`.
   - Objective-C++: `@interface` or `@implementation` at the start of a line, or `[[X alloc] init]`.
   - Plain C: a source file (not a header) that includes a C header such as `<stdio.h>`, or defines a function
     `f(void) {`, and has no C++ construct (`::`, `class`, `template`, `namespace`, `new`, `bool`, a header without
     `.h` ...) outside comments and strings.

```python
import re

_CPP = re.compile(r"::|\b(?:class|template|typename|namespace|new|delete|operator|virtual|nullptr|bool|"
                  r"public|private|protected|try|catch|throw|cout|cin|static_cast|dynamic_cast|"
                  r"reinterpret_cast|const_cast)\b|#\s*include\s*<(?:[a-z_]+|bits/stdc\+\+\.h)>")
_CLI = re.compile(r"#using\s*<|\bref\s+(?:class|struct|new)\b|\bgcnew\b|\bvalue\s+(?:class|struct)\b")
_OBJC = re.compile(r"^@(?:interface|implementation)\b|\[\[\w+\s+alloc\]\s*init\]", re.M)
_C_HEADER = re.compile(r"#\s*include\s*<(?:stdio|stdlib|string|math|ctype|time|stdarg|malloc|memory|conio|windows|tchar)\.h>")
_C_FUNC = re.compile(r"\b\w+\s*\(\s*void\s*\)\s*\{")
_NOISE = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)


def medicine_d1(doc):
    if doc.get("lang_label") != "cpp":
        return False
    text = doc["text"]
    if _CLI.search(text) or _OBJC.search(text):
        return True
    if re.search(r"\.(?:h|hh|hpp|hxx)$", doc.get("url") or ""):
        return False
    code = _NOISE.sub(" ", text)
    return bool(_C_HEADER.search(text) or _C_FUNC.search(code)) and not _CPP.search(code)
```

3. **Action:** drop from the cpp pack, to relabel it: the document moves to the C (or C++/CLI, Objective-C++)
   stream. The harm test counts it as a drop.
4. **Harm test:** 0 of 120 gold documents changed, 0 dropped. PASS.
5. **Side effects:**
   - C-style C++ that uses no C++ keyword is moved too. It compiles as C, so the label is not really wrong. On the
     pack the rule finds exactly my 10 D1 documents.
   - Headers never fire, because a header with only declarations cannot be told apart.
   - A C++ file that hides all its C++ inside macros would be taken for C.

## Medicine 6

1. **Disease:** E1, 19 documents. Code written by a generator, not by a person.
   - `b5da9ac1658db525`: `automatically generated by the FlatBuffers compiler, do not modify` at 52
   - `9c1d218d257a6176`: `This file has been generated by Py++.` at 3
   - `f63ec57866305825`: aws-sdk-cpp model class (`.../source/model/HumanTaskConfig.cpp`), one
     `m_*HasBeenSet` block per field from 850 to 6641
2. **Medicine:** drop the document when the first 3000 characters hold a generator banner (`auto-generated`,
   `automatically generated`, `machine generated`, `this file has been/was/is generated`, `generated by the
   FlatBuffers compiler`, `generated by Py++`, `CodeSynthesis XSD`, `// Mono Native Fixture`), or when the `url` is a
   generated-code path (`/generated/`, `/generated_code/`, `-Codegen/`, `QtAndroidAPI/`, SDK model classes
   `...sdk.../model/*.cc|cpp`). IDE stub comments such as `// TODO Auto-generated constructor stub` are not banners:
   the code around them is hand-written (clarification 3).

```python
import re

_BANNER = re.compile(r"auto-?generated(?! (?:constructor|destructor|method|function|catch block) stub)|"
                     r"automatically generated|machine generated|this file (?:has been|was|is) generated|"
                     r"generated by (?:the )?(?:flatbuffers compiler|py\+\+)|codesynthesis xsd|^// mono native fixture",
                     re.I | re.M)
_PATH = re.compile(r"/generated(?:_code)?/|-codegen/|/qtandroidapi/|(?:sdk|ucloud)[^/]*/.*/model/[^/]+\.(?:cc|cpp)$", re.I)


def medicine_e1(doc):
    return bool(_BANNER.search(doc["text"][:3000]) or _PATH.search(doc.get("url") or ""))
```

3. **Action:** drop. Generated code cannot be fixed by removing a few lines; the whole file is the generator's output.
4. **Harm test:** 0 of 120 gold documents changed, 0 dropped. PASS.
5. **Side effects:**
   - A hand-written file stored in a `generated/` or SDK `model/` folder is dropped.
   - A file that keeps an "automatically generated" banner after a person rewrote it is dropped.
   - Generated code with no banner and no telling path is missed: on the pack the rule finds 18 of my 19 E1
     documents. The miss is `d13c02419ff98cfa` (`opcode8.cpp`, 68000 opcode handlers in C), which Medicine 5
     takes out as C.

## Medicine 7

1. **Disease:** E4, 85 documents. A standard licence text (Apache-2.0 40, BSD 18, MIT 17, GPL 10) at the top of the
   file (one at the end). The same text heads many documents of the pack.
   - `9195ba155f4ee31e`: Apache-2.0 header, 15 lines, offsets 0-628
   - `9f6e4e65e41f69c4`: MIT licence text, 22 lines, offsets 0-1107
   - `ea5991abc7704e1f`: GNU GPL notice, 27 lines, offsets 15-1274
2. **Medicine:** find each group of comment blocks (blocks with only white space between them). If the group holds
   a standard licence, delete its blocks that contain licence words, and keep the others (a file description in the
   same group stays). A licence is recognised by two phrases, so a one-line pointer is kept:
   - Apache-2.0: "Apache License" and "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND" or "you may not use this file
     except in compliance"
   - MIT: "Permission is hereby granted, free of charge, to any person obtaining a copy" and "THE SOFTWARE IS PROVIDED
     "AS IS""
   - BSD: "Redistribution and use in source and binary forms" or "Redistributions of source code must retain the
     above copyright", and "THIS SOFTWARE IS PROVIDED"
   - GPL and LGPL: "General Public License" and "Free Software Foundation"

```python
import re

_SIGNATURES = [
    (r"apache license", r"without warranties or conditions of any kind|you may not use this file except in compliance"),
    (r"permission is hereby granted, free of charge, to any person obtaining a copy", r"the software is provided .{0,3}as is"),
    (r"redistribution and use in source and binary forms|redistributions of source code must retain the above copyright",
     r"this software is provided"),
    (r"general public license", r"free software foundation"),
]
_BLOCK = re.compile(r"/\*.*?\*/[ \t]*\r?\n?|(?:^[ \t]*//[^\n]*\n)+", re.S | re.M)
_LICENCE_WORD = re.compile(r"licen[cs]|copyright|warrant|permission|redistribut|liabilit|free software", re.I)


def _flat(block):
    return " ".join(re.sub(r"^[ \t]*(?://+|/?\*+/?)", " ", block, flags=re.M).split()).lower()


def _groups(text):
    group = []
    for m in _BLOCK.finditer(text):
        if group and text[group[-1].end():m.start()].strip():
            yield group
            group = []
        group.append(m)
    if group:
        yield group


def medicine_e4(text):
    cut = []
    for group in _groups(text):
        flat = " ".join(_flat(m.group()) for m in group)
        if any(re.search(a, flat) and re.search(b, flat) for a, b in _SIGNATURES):
            cut += [m for m in group if _LICENCE_WORD.search(m.group())]
    if not cut:
        return text
    out, last = [], 0
    for m in cut:
        out.append(text[last:m.start()])
        last = m.end()
    return "".join(out) + text[last:]
```

3. **Action:** fix (delete the licence comment, keep the code).
4. **Harm test:** 0 of 120 gold documents changed, 0 dropped. PASS.
5. **Side effects:**
   - The copyright lines inside the licence block go with it.
   - A licence comment in the middle of a file (vendored code) is deleted too.
   - The rule does not count how often a licence repeats in the pack. On the pack it finds all 85 of my E4 documents
     and one more: `e8f8d0c01a035a3c`, whose LGPL notice heads only that one document, so I did not label it E4.
   - Kept on purpose: pointers such as "Distributed under the Apache License, Version 2.0. See the accompanying file
     LICENSE", the 3-line Chromium notice, the Boost licence ("to any person or organization") and short
     project-specific notices.
