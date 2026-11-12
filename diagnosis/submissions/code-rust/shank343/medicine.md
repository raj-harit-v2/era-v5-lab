# Medicine sheet: code-rust (shank343)

Pack `code-rust`: 500 Rust files from `bigcode/starcoderdata:rust`. Labels: `labels.csv` in this folder
(500 rows: 238 clean, 230 fix, 32 drop).

Six diseases are found more than five times: B3 (225), E1 (23), E4 (22), B4 (19), F2 (7), A2 (6).
Each rule is plain Python 3 with only the standard library (`re`), so nothing has to be installed.
A fix rule returns the new text; a drop rule returns `("drop", "")`. The order does not matter: running them as
B3, E4, B4, E1, F2, A2 or with A2 first gives the same result on all 500 files.

**Harm test, how it was run:** Data A's `harm_test.py` (PR #140, latest commit `93fae90`, run on 31 Oct) on the code-rust gold set
`teams/01-data-a/gold/code-rust_gold.csv` (78 documents that two readers marked clean), with
`--rules medicine.md --rule all`. Every rule alone and all six together in order: 0 changed, 0 dropped, **PASS**.
The gold set is small (78 documents), so the tool's limit is max(1, 1 % of 78) = 1 document (the TSAI decision for
small gold sets); every rule touched 0.

```
python -I teams/01-data-a/tools/harm_test.py --pack code-rust.parquet \
  --gold teams/01-data-a/gold/code-rust_gold.csv \
  --rules diagnosis/submissions/code-rust/shank343/medicine.md --rule all
```

Limits of this harm test, so the result is read correctly:
- The gold set and the tool are in Data A's open PR #140 (not merged on 31 Oct); the test should be run again on
  the merged gold set.
- The gold set was built from the first 150 rows only (78 clean documents), and few gold documents look like the
  diseases (no gold document starts with a StarCoder line or holds a placeholder), so for B3, B4, F2 and A2 a PASS
  says little on its own. That is why each rule was also run on all 500 documents: every rule changes or drops only
  documents labelled with its disease and no document labelled clean (item 4 of each section).
- With `pyarrow` not installable in my workspace, the Parquet file was read by a small stand-in reader; an
  independent second decoder gave the same 78 gold texts byte for byte, and harmful control rules (one changed
  character, one dropped file) failed as they should.

## Medicine 1: StarCoder header line

1. **Disease:** B3, 225 of 500 documents. Every case is the first line of the file. Examples:
   - `e016447055203614`: `<gh_stars>1-10` at 0
   - `d1e5237063713aba`: `<filename>server/src/room/dto/response/join_room.dto.rs` at 0
   - `a500c6c5ef2132b5`: `<filename>dacquiri/examples/simple/main.rs` at 0
2. **Medicine:** if the text starts with `<reponame>`, `<filename>` or `<gh_stars>`, delete the whole first line:
   the marker and the repository name, file path or star range that follows it. The model must not learn the
   dataset markers, and the path after them is metadata, not code.

   ```python
   import re

   _STARCODER_HEADER = re.compile(r'\A<(?:reponame|filename|gh_stars)>[^\n]*(?:\n|\Z)')


   def medicine_b3(text):
       """Delete line 1 when it starts with a StarCoder marker (<reponame>, <filename>, <gh_stars>)."""
       return _STARCODER_HEADER.sub('', text, count=1)
   ```
3. **Action:** fix
4. **Harm test:** gold set `teams/01-data-a/gold/code-rust_gold.csv` (78 documents, Data A, PR #140). Changed: 0. Dropped: 0. 0/78 = 0.00 %, limit max(1, 1 %) = 1 document: **PASS**. On the whole pack the rule touches 225 of 500 documents, exactly the 225 documents labelled B3 and nothing else.
5. **Side effects:** a real file whose first line starts with one of these markers would lose that line. That is
   not valid Rust, so I expect none. The rule only looks at the start of the text; a marker later in a file (none in
   this pack) is not removed.

## Medicine 2: Licence header of 5 or more lines

1. **Disease:** E4, 22 of 500 documents. Examples (the licence line inside each block):
   - `b0a1eeeb782fea8c`: 19-line MIT header from 39; at 315 `// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell`
   - `17e695a1c0fee084`: 13-line Apache-2.0 header from 20; at 74 `// Licensed under the Apache License, Version 2.0 (the "License");`
   - `c5e98659490161e2`: 15-line GPL-3.0 header from 0; at 158 `// it under the terms of the GNU General Public License as published by`
2. **Medicine:** look at the comments at the top of the file (after the StarCoder line, if there is one): either
   one `/* ... */` block or a run of `//` comment paragraphs separated by blank lines. Doc comments (`///`, `//!`)
   are code documentation and are never touched. The licence block starts at the first paragraph with a licence
   word and ends before the first paragraph without one, so a file description above it and an ordinary comment
   below it stay. If the block has a strong licence word, at least two licence words and is 5 lines or longer
   (blank lines inside it count), delete it and the blank lines after it. Notices of 1 to 4 lines (13 files in
   this pack) stay.

   ```python
   import re

   _E4_WORDS = re.compile(r'(?i)licen[sc]e|copyright|\(c\)|permission is hereby granted|warrant|redistribut|'
                          r'all rights reserved|spdx-license-identifier|liabilit|merchantability|"as is"|public domain')
   _E4_STRONG = re.compile(r'(?i)licen[sc]e|permission is hereby granted|spdx-license-identifier')
   _E4_HEADER = re.compile(r'<(?:reponame|filename|gh_stars)>[^\n]*\n')
   _E4_BLANKS = re.compile(r'(?:[ \t\r]*\n)+')
   _E4_LINE = re.compile(r'[ \t]*//(?![/!])[^\n]*(?:\n|$)')


   def _e4_is_licence(par):
       """A paragraph belongs to the licence block when it has at least one licence word."""
       return bool(_E4_WORDS.search(par))


   def _e4_block(text):
       """(start, end, nlines) of the licence comment block at the top of the file, or None.

       After an optional StarCoder header line and blank lines, the block is either one /* */ comment (not /** or /*!)
       or a run of // comment paragraphs (not /// or //! doc comments) separated by blank lines. Comment paragraphs
       before the first one with licence words are kept; from there paragraphs are taken while they have licence words; the first paragraph without one ends the block (so an ordinary
       comment after the licence is kept), and blank lines inside the block count as lines.
       """
       pos = 0
       m = _E4_HEADER.match(text, pos)
       if m:
           pos = m.end()
       m = _E4_BLANKS.match(text, pos)
       if m:
           pos = m.end()
       start = pos
       if text.startswith('/*', pos) and not text.startswith(('/**', '/*!'), pos):
           close = text.find('*/', pos)
           if close < 0:
               return None
           end = close + 2
           body = text[start:end]
           if not (_E4_STRONG.search(body) and len(_E4_WORDS.findall(body)) >= 2):
               return None
           return start, end, body.count('\n') + 1
       end, last_end = pos, None
       while True:
           p = end
           while True:                                  # one paragraph: consecutive // lines
               m = _E4_LINE.match(text, p)
               if not m or m.end() == p:
                   break
               p = m.end()
           if p == end:
               break
           if _e4_is_licence(text[end:p]):
               if last_end is None:
                   start = end                          # the block starts at the first licence paragraph
               last_end = p
           elif last_end is not None:
               break                                    # first non-licence paragraph after the licence: stop
           m = _E4_BLANKS.match(text, p)
           if not m:
               break
           end = m.end()
       if last_end is None:
           return None
       body = text[start:last_end]
       if not (_E4_STRONG.search(body) and len(_E4_WORDS.findall(body)) >= 2):
           return None
       return start, last_end, body.rstrip('\r\n').count('\n') + 1


   def medicine_e4(text):
       """Remove a licence comment block of 5 or more lines at the top of the file (blank lines inside it count)."""
       found = _e4_block(text)
       if not found or found[2] < 5:
           return text
       start, end, _ = found
       rest = text[end:]
       m = _E4_BLANKS.match(rest)
       if m and rest[m.end():]:
           rest = rest[m.end():]                        # drop the blank lines between the block and the code
       elif rest.startswith((' ', '\t')):
           rest = rest.lstrip(' \t')                    # code on the same line as the closing */
       return text[:start] + rest
   ```
3. **Action:** fix
4. **Harm test:** gold set `teams/01-data-a/gold/code-rust_gold.csv` (78 documents, Data A, PR #140). Changed: 0. Dropped: 0. 0/78 = 0.00 %, limit max(1, 1 %) = 1 document: **PASS**. On the whole pack the rule touches 22 of 500 documents, exactly the 22 documents labelled E4 and nothing else.
5. **Side effects:** a comment paragraph that sits right after the licence and itself mentions a licence (for
   example a TODO about a dependency's licence) is removed with it. A licence placed lower in the file, after code,
   or inside a `/**` banner, is not found (none in this pack). Code on the same line as a closing `*/` is kept.
   The file keeps its code but loses its licence text, so the pipeline should keep the licence as metadata if it
   is needed. Tested on edge cases: empty text, a licence with no code after it, Windows line endings, a 1 MB
   file (0.1 s).

## Medicine 3: PII placeholders left by earlier cleaning

1. **Disease:** B4, 19 of 500 documents (18 PII placeholders, 1 template file, see side effects). Examples:
   - `7dcf53c66a82f309`: `<NAME>` at 22
   - `920d344679eb3387`: `<EMAIL>` at 182
   - `9c345c5606b0d951`: `<NAME>` at 45, in `// Copyright 2017 <NAME> aka. ...`
2. **Medicine:** replace each placeholder with a neutral dummy value: `<NAME>` → `Jane Doe`, `<EMAIL>` →
   `jane.doe@example.com`, `<KEY>` → `YOUR_KEY`, `<PASSWORD>` → `YOUR_PASSWORD`. Removing them would leave broken
   lines such as `authors = "<<EMAIL>>"` or an empty copyright owner; the dummy values keep the line complete and
   valid, and they are not personal data. Inside strings and comments every placeholder is replaced; in code,
   `Name<KEY>` is a Rust generic type, so a match right after an identifier is left alone.

   ```python
   import re

   _PII_PLACEHOLDERS = {
       '<NAME>': 'Jane Doe',
       '<EMAIL>': 'jane.doe@example.com',
       '<KEY>': 'YOUR_KEY',
       '<PASSWORD>': 'YOUR_PASSWORD',
   }
   _PII_RE = re.compile('|'.join(re.escape(k) for k in _PII_PLACEHOLDERS))


   def _pii_in_string_or_comment(line_before):
       """True when the text before the match on its line opens a // comment or an unclosed "string"."""
       if '//' in line_before.replace('://', ''):
           return True
       return len(re.findall(r'(?<!\\)"', line_before)) % 2 == 1


   def medicine_b4(text):
       """Replace the PII-scrub placeholders with neutral dummy values, so the lines stay complete.

       Inside a string or comment every placeholder is replaced. In code, `Name<KEY>` is a Rust generic, not a
       placeholder, so a match right after an identifier character is left alone there.
       """
       def repl(m):
           line_start = text.rfind('\n', 0, m.start()) + 1
           before = text[line_start:m.start()]
           if not _pii_in_string_or_comment(before) and before[-1:].isalnum() | (before[-1:] == '_'):
               return m.group(0)
           return _PII_PLACEHOLDERS[m.group(0)]
       return _PII_RE.sub(repl, text)
   ```
3. **Action:** fix
4. **Harm test:** gold set `teams/01-data-a/gold/code-rust_gold.csv` (78 documents, Data A, PR #140). Changed: 0. Dropped: 0. 0/78 = 0.00 %, limit max(1, 1 %) = 1 document: **PASS**. On the whole pack the rule touches 18 of 500 documents, the 18 documents labelled B4 that hold a PII placeholder (the 19th, a template file, is dropped by hand) and nothing else.
5. **Side effects:** a file that uses one of these exact tokens on purpose (for example a template that prints
   `<NAME>`) would be changed; none in this pack. In code, a placeholder used as a value becomes a name
   (`Some(<PASSWORD>.to_string())` becomes `Some(YOUR_PASSWORD.to_string())`), so the line is complete but the name
   is undefined; in an ASCII-art box the border can shift. The template file `016bc22f87c65d9a`
   (`{{ property }}` placeholders) is B4 too, but it is not a PII placeholder and is dropped by hand in
   `labels.csv`; this rule does not touch it.

## Medicine 4: Generated code

1. **Disease:** E1, 23 of 500 documents (19 with a generator marker, 4 without). Examples:
   - `9773497d0c18080b`: `Code generated by software.amazon.smithy.rust.codegen.smithy-rs. DO NOT EDIT.` at 61
   - `920d344679eb3387`: `Generated by: https://openapi-generator.tech` at 193
   - `856747c12b100481`: `#[doc = r" Register block"]` at 22 (svd2rust register file)
2. **Medicine:** drop the file when a code-generator marker appears in its first 2000 characters: the
   "generated ... do not edit" lines of smithy-rs, rust-protobuf, rust-bindgen, jni-bindgen, openapi-generator,
   idl2rs and similar tools, the standard `// @generated` tag, or the fixed first line of an svd2rust register
   file. In all 19 marked files the code under the marker is generator output too (the instructor's rule: a marker
   over hand-written code is not E1), so no usable hand-written part is left. Mentions of generated things deeper in a file (`// generated once on startup`,
   `use bindgen::...` in a build script) are not markers and are not matched.

   ```python
   import re

   _GEN_MARKERS = re.compile(
       r'Code generated by [^\n]{0,120}DO NOT EDIT'
       r'|This file is generated by rust-protobuf'
       r'|This file is generated\. Do not edit'
       r'|automatically generated by rust-bindgen'
       r'|This file is auto-generated by \S+\. DO NOT EDIT'
       r'|This file was autogenerated by jni-bindgen'
       r'|Generated by: https://openapi-generator\.tech'
       r'|This file is automatically generated!'
       r'|Generated by idl2rs\.'
       r'|Tests auto-converted from "'
       r'|^//\s*@generated\b'                          # the standard @generated tag
       r'|^#\[doc = r" Register block"\]'                # svd2rust register-block file
       r'|^#\[doc = "Reader of register \w+"\]'          # svd2rust register file (old template)
       r'|^#\[doc = "Register `\w+` reader"\]',          # svd2rust register file (new template)
       re.M)
   _GEN_HEAD = 2000          # markers count only near the top of the file


   def medicine_e1(text):
       """Drop the document when a code-generator marker appears in its first 2000 characters."""
       return ('drop', '') if _GEN_MARKERS.search(text[:_GEN_HEAD]) else text
   ```
3. **Action:** drop
4. **Harm test:** gold set `teams/01-data-a/gold/code-rust_gold.csv` (78 documents, Data A, PR #140). Changed: 0. Dropped: 0. 0/78 = 0.00 %, limit max(1, 1 %) = 1 document: **PASS**. On the whole pack the rule touches 19 of 500 documents, all 19 of the 23 documents labelled E1 that carry a marker (the other 4 are dropped by hand) and nothing else.
5. **Side effects:** a hand-written file that still carries a generator header near the top would be dropped. Generated
   code with no marker is missed: 4 files in this pack are labelled E1 and dropped by hand because the code itself
   is clearly generated (`e1608ccb8243c14b` and `7cdc556dd197e582`: numbered instruction tests that differ only in
   operands; `b59423399af5cda7`: a FHIR model where every method is the same accessor; `cc067a09cfd5da85`: one of a
   generated set of SVG icon components). The marker list is fitted to the generators seen in this pack, so other
   generators need new entries.

## Medicine 5: LeetCode solutions (benchmark leak)

1. **Disease:** F2, 7 of 500 documents. Examples:
   - `5edcef0e8667d1f9`: LeetCode 554, `impl Solution {` at 94
   - `e748066dd0d697f8`: LeetCode 438, `impl Solution {` at 107
   - `a29d30783f15a06b`: LeetCode 108, problem text at 7 and `impl Solution {` at 1834
2. **Medicine:** drop the file when a line starts with `impl Solution {`. LeetCode's Rust template always wraps the
   answer in `impl Solution`, and these files are the leaked solutions themselves, so nothing is left to keep.

   ```python
   import re

   _LEETCODE = re.compile(r'^[ \t]*impl Solution[ \t]*\{', re.M)


   def medicine_f2(text):
       """Drop LeetCode solution files: the LeetCode harness always wraps the answer in `impl Solution { ... }`."""
       return ('drop', '') if _LEETCODE.search(text) else text
   ```
3. **Action:** drop
4. **Harm test:** gold set `teams/01-data-a/gold/code-rust_gold.csv` (78 documents, Data A, PR #140). Changed: 0. Dropped: 0. 0/78 = 0.00 %, limit max(1, 1 %) = 1 document: **PASS**. On the whole pack the rule touches 7 of 500 documents, exactly the 7 documents labelled F2 and nothing else.
5. **Side effects:** a project with its own `impl Solution` (for example a puzzle solver), or the words
   `impl Solution {` at the start of a line inside a comment, would be dropped; none in this pack. LeetCode solutions
   written without `impl Solution` are missed. Advent of Code files are not a benchmark test set and are not
   dropped by this rule (23 in this pack).

## Medicine 6: Control characters (Windows line endings)

1. **Disease:** A2, 6 of 500 documents. All six are CARRIAGE RETURN (U+000D) from Windows line endings. Examples:
   - `2f34546793ed7faf`: `36 U+000D CARRIAGE RETURN (227x)`
   - `f082f2a0ddf32b99`: `31 U+000D CARRIAGE RETURN (277x)`
   - `7442d2a671650047`: `27 U+000D CARRIAGE RETURN (66x)`
2. **Medicine:** turn `\r\n` and a lone `\r` into `\n`, then delete any other control character (U+0000 to
   U+001F except tab and newline, and U+007F to U+009F). Line breaks stay where they were.

   ```python
   import re

   _CONTROL = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')


   def medicine_a2(text):
       """Turn Windows (CRLF) and old Mac (CR) line endings into LF, and delete other control characters."""
       if '\r' not in text and not _CONTROL.search(text):
           return text
       return _CONTROL.sub('', text.replace('\r\n', '\n').replace('\r', '\n'))
   ```
3. **Action:** fix
4. **Harm test:** gold set `teams/01-data-a/gold/code-rust_gold.csv` (78 documents, Data A, PR #140). Changed: 0. Dropped: 0. 0/78 = 0.00 %, limit max(1, 1 %) = 1 document: **PASS**. On the whole pack the rule touches 6 of 500 documents, exactly the 6 documents labelled A2 and nothing else.
5. **Side effects:** a control character that a file needs as a real byte (for example a raw form feed inside a
   string literal) would be removed; Rust code writes these as escapes (`\x0c`), so I expect none. Escapes like
   `\r` written as two characters are not touched.

## Observations

Not diseases, written here so the lab can decide (the instructor asked for counts):

- **Other human languages and scripts:** 16 of 500 files have non-English letters in comments or strings:
  Chinese/Japanese 5, Korean 1, Russian 1, Ethiopic 1, accented Latin (French, Portuguese and others) 6, Greek
  letters in maths 2. At least one more file has a French comment without accents. Not labelled, as ruled.
- **Advent of Code:** 23 files are Advent of Code solutions or inputs. Not F2 (not a benchmark test set); 22 are
  kept and 1 (a 1000-line puzzle-input string) is dropped as E2.
- **Diseases found 5 times or fewer** (labelled, no medicine): A1 1 (a BOM U+FEFF inside the text after the
  StarCoder line), E2 3 (embedded sprite images, a 1000-line puzzle-input string, a protobuf descriptor in a
  generated file), B2 1 (`<img>` tags in a LeetCode problem text, dropped by F2), E3 1 (a hard-coded app secret in
  a test file, type and offset only in `labels.csv`).
- **Not found in this pack:** A3, A4, A5, A6, B1, B5, C1 to C5, D1 to D5, E5, E6, F1, F3, G1 to G4, H1 to H3.
  No exact or near duplicates among the 500 files; every file is Rust.
- **Short licence notices:** 13 files have a 1 to 4 line copyright or SPDX notice; kept (not E4).
- **No final newline:** 44 files end without a newline; each ends on a closed block or a complete statement, so
  none is truncated (not C3).
