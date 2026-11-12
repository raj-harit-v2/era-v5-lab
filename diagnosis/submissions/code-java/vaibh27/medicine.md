# Medicine sheet: code-java (vaibh27)

Pack: `code-java`, 500 documents from `bigcode/starcoderdata:java`. All 500 are labelled in `labels.csv`
(120 clean, 370 fix, 10 drop). Seven diseases are found more than five times: M1 to M7. Two rarer ones also get a
short medicine because they are easy to cure safely: A4 (M8) and C4 (M9).

The medicines use only the Python standard library (`re`, Python 3.9 or newer); nothing needs to be installed.
Each one takes the text of a document and returns the new text, or `None` to drop the document. Run them in this
order (the `PIPELINE` at the end): **M1, M3, M7, M9, M4, M6, M5, M2, M8**, then one last check. M4 to M6 expect
the metadata line (M1) and the CR characters (M3) to be gone, and M7 and M9 drop before anything is rewritten.

## Harm test status

**Gold-set harm test: PASS**, on Data A's gold set `teams/01-data-a/gold/code-java_gold.csv` (PR #140):
**116 documents** that two reviewers each read in full and labelled `clean` with no disease (84 short of the 200
target). Data A's `medicine_extract.py` takes all 9 rules (`DA-B3-001` to `DA-C4-001`) from this file, and
`harm_test.py --rule all` gives **0 changed and 0 dropped (0.00%)** for every rule alone and for all of them in
order, within the limit of max(1 document, 1%). The whole pipeline below, last check included, also changes and
drops 0 of the 116.

I also compared the whole pipeline with my own `labels.csv` on all 500 documents:

| Medicine | Disease | Rows labelled | Documents changed | Dropped | Labelled rows it misses | Changes on my 120 `clean` rows |
|---|---|---:|---:|---:|---:|---:|
| M1 | B3 | 250 | 250 | 0 | 0 | 0 |
| M2 | B4 | 83 | 15 | 0 | 0 (*) | 0 |
| M3 | A2 | 44 | 44 | 0 | 0 | 0 |
| M4 | E4 | 103 | 101 | 0 | 0 (*) | 0 |
| M5 | F1 | 93 | 73 | 0 | 0 (*) | 0 |
| M6 | C1 | 67 | 77 | 0 | 0 (*) | 0 |
| M7 | E1 | 8 | 0 | 8 | 0 | 0 |
| M8 | A4 | 2 | 2 | 0 | 0 | 0 |
| M9 | C4 | 1 | 0 | 1 | 0 | 0 |
| Last check | nothing left | - | 0 | 1 | - | 0 |

(*) The other labelled rows are already cured by an earlier medicine: the `<NAME>`, the author name or the template
sat inside a licence header (M4) or an IDE template (M6) that is removed as a whole. After the full pipeline, I ran
my detectors again on the cured text: **no labelled B3, B4, A2, E4, F1, C1, A4 or C4 is left**. What is left on
purpose: the E2 number tables in `9cbc723f9cfc6c7c` (lookup tables that the code reads; removing them breaks it). E2 is
found once, so it needs no medicine (DISEASES.md section 4).

The whole pipeline changes 370 of 500 documents and drops 10, and it **changes 0 of my 120 `clean` documents and
drops 0**.

**Benchmark leaks (F2).** I ran G9's `teams/09-evaluation/decontam/decontam_check.py` with the full fingerprint set
(`set_sha256 11e290a44d1467875fdf8bebc55eab21f0a6367f411aab98a4a027a546fd372e`) on all 500 documents:
**0 flagged**. Some documents hold LeetCode practice solutions; LeetCode is not on the lab's benchmark list, so they
are not F2 (DISEASES.md: "a question or a solution from a benchmark test set") and stay in the pack.

---

## Medicine 1: StarCoder metadata header (B3)

1. **Disease:** B3, ghost dataset tokens `<reponame>`, `<filename>`, `<gh_stars>` on the first line. Count:
   **250 of 500**. They never appear after the first line in this pack.
   - `d0947d80d45f7ce3`: `<filename>src/test/java/problems/RangeSumOfBSTTest.java` at offset 0
   - `7590b32d671f36c9`: `<reponame>88t6/vwkit-matrix<gh_stars>1-10` at offset 0
   - `073b348caf645018`: `<reponame>DezByte/multiverse<filename>multiverse-core/...RetryError.java<gh_stars>0` at offset 0
2. **Medicine:** if the document starts with one or more of these tokens, delete that whole first line. Touch nothing
   after it.
   ```python
   import re

   # M1 (B3): StarCoder metadata tokens on the first line
   META_HEAD = re.compile(r"\A(?:<reponame>[^<\n]*|<filename>[^<\n]*|<gh_stars>[^<\n]*)+\n")


   def m1_strip_meta_header(t: str) -> str:
       t = META_HEAD.sub("", t, count=1)
       return t[1:] if t.startswith("\ufeff") else t  # a BOM under the metadata line is now at the start (A1)
   ```
3. **Action:** fix.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: changes the 250 labelled B3 documents and nothing else; 0 of 120 clean.
5. **Side effects:** the repo name and file path are lost. If we want them as metadata, copy them into a separate
   column before stripping. The rule is anchored at offset 0, so a `<filename>` string inside real code cannot match.
   One document (`beae2c42d8a34ccc`) has a BOM (A1, found once) right under the metadata line; M1 also removes a
   BOM that is at the start of the file after the metadata line is gone.

## Medicine 2: PII redaction placeholders (B4)

1. **Disease:** B4 (ruling of 25 Oct: placeholders from earlier PII cleaning are B4, note `PII placeholder`; they
   are not personal data), the upstream redaction placeholders `<NAME>`, `<EMAIL>`, `<PASSWORD>` and `<KEY>` left as
   plain text. A model trained on them learns to write these tokens. Count: **83 of 500**.
   - `13a397d8bedc6210`: `@author <NAME> <<EMAIL>>`, `<NAME>` at offset 159
   - `8c9a9aa845f91a2c`: `String passWord = "<PASSWORD>";`, `<PASSWORD>` at offset 321
   - `4fce1af748c757ed`: `<NAME> (<EMAIL>)` 11 times (copyright line and `@author` tags), first `<NAME>` at offset 109
2. **Medicine:** replace each placeholder with a fixed, neutral surrogate. Do not delete it: in string literals,
   deleting it would leave `""` or broken code. Replace `<KEY>` only inside quotes, because a bare `<KEY>` is a legal
   Java generic type parameter (`class Cache<KEY>`).
   ```python
   import re

   # M2 (B4): placeholders left by the upstream PII redaction
   SURROGATE = {"<EMAIL>": "user@example.com", "<NAME>": "Author Name",
                "<PASSWORD>": "password", '"<KEY>"': '"key"'}
   REDACT = re.compile("|".join(map(re.escape, SURROGATE)))


   def m2_surrogate_placeholders(t: str) -> str:
       return REDACT.sub(lambda m: SURROGATE[m.group()], t)
   ```
3. **Action:** fix.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: changes 15 documents, all labelled B4. Most `<NAME>` and
   `<EMAIL>` sit on author lines, which M5 rewrites first (31 rows); the others go with the licence header or IDE
   template that held them (M4, M6), and 2 are dropped by M7. 0 of 120 clean.
5. **Side effects:**
   - A real XML/HTML tag `<NAME>` inside a string would be changed. There are no `</NAME>`, `</EMAIL>` or
     `</PASSWORD>` closing tags in the pack, so I found no such case.
   - Every author becomes the same "Author Name", the same surrogate as M5. This is a small bias, but it is better
     than the special token.
   - The upstream redaction was not complete: `1a1a1d7ab0bf9188` still has a real phone number (F1, offsets 40 and
     1499). M2 does not find unredacted personal data; M5 replaces it (it is on an author line), and M4 removes the
     other copy with the licence header.

## Medicine 3: CRLF line endings (A2)

1. **Disease:** A2, control character U+000D (CR) as Windows line endings (`0D 0A`). Count: **44 of 500**. No lone
   CR and no other control characters in the pack.
   - `e0ebe203093970dc`: U+000D x38, first at offset 17
   - `7fc99d2b6e1e3d08`: U+000D x330, first at offset 2
   - `42136327639e76b1`: U+000D x544, first at offset 779
2. **Medicine:** turn every CRLF into LF, then any lone CR into LF.
   ```python
   import re

   # M3 (A2): Windows CRLF line endings
   def m3_normalise_newlines(t: str) -> str:
       return t.replace("\r\n", "\n").replace("\r", "\n")
   ```
3. **Action:** fix.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: changes exactly the 44 labelled A2 documents; 0 of 120 clean.
5. **Side effects:** Java treats CR and LF the same, so the program does not change. The escaped text `"\r\n"`
   inside a string is two ASCII characters, not U+000D, so it is not touched. A raw CR inside a Java text block
   (`"""`) would change the string value. I found none in the pack.

## Medicine 4: Licence headers (E4)

1. **Disease:** E4, the same licence text at the top of many files (Apache-2.0 ASF and short form, MIT, BSD, GPL,
   one-line proprietary notices). Count: **103 of 500**; the most common header is in 37 documents.
   - `5655154f71365c63`: 18-line ASF Apache-2.0 header, offsets 0 to 825
   - `4fce1af748c757ed`: 23-line MIT header, offsets 0 to 1205
   - `1d8e6800c299d06e`: 19-line Apache-2.0 header after the `package` line, at offset 29
2. **Medicine:** take the first comment of the file, after any `package` and `import` lines. Before the `package`
   line, a comment with licence words or a copyright line is the file header: delete it. After the `package` or
   `import` lines, delete it only if it has licence words, because there it may be the class Javadoc. Repeat, for
   files that stack two headers. Keep the NetBeans "To change this license header" template; it is no licence (M6).
   ```python
   import re

   # M4 (E4): the licence header of the file. Before the package line a copyright line is enough; after the
   # package/import lines the comment must hold licence words, or it may be the class Javadoc.
   HEAD_CODE = re.compile(r"(?:[ \t]*(?:package|import)\b[^;\n]*;[ \t]*\n|[ \t]*\n)*")
   FIRST_COMMENT = re.compile(r"[ \t]*(?:/\*.*?\*/|(?://[^\n]*\n[ \t]*)+)[ \t]*\n?", re.S)
   LIC_WORDS = re.compile(r"licen[cs]e|permission is hereby granted|redistribution and use", re.I)
   TOP_WORDS = re.compile(r"licen[cs]e|permission is hereby granted|redistribution and use|copyright|\(c\)|"
                          r"all rights reserved", re.I)
   NOT_LICENCE = re.compile(r"to change this licen[cs]e header|choose licen[cs]e headers", re.I)  # NetBeans template


   def m4_strip_licence_header(t: str) -> str:
       while True:  # some files stack two headers (a project notice, then the licence)
           start = HEAD_CODE.match(t).end()
           m = FIRST_COMMENT.match(t, start)
           if not m or NOT_LICENCE.search(m.group()):
               return t
           words = TOP_WORDS if not t[:start].strip() else LIC_WORDS
           if not words.search(m.group()):
               return t
           t = t[:start] + t[m.end():].lstrip("\n")
   ```
3. **Action:** fix.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: changes 101 documents. 100 of them are labelled E4; the other one
   (`b7741e4914caefba`) is an IDE file header with a copyright line that I labelled C1, so the change is right but
   the code differs. The 3 other labelled E4 rows are dropped first by M7. 0 of 120 clean.
5. **Side effects:**
   - `865d813577b270f2` has its copyright inside an Eclipse class template after the imports (`<p>Title:` /
     `<p>Copyright` lines). M4 keeps a class Javadoc on purpose; M6 removes this template instead.
   - The first draft also deleted an IDE header with "All rights reserved" after the imports
     (`dc290bee53a01177`). That is why a comment after the imports needs real licence words.
   - The licence notice is removed from the training text. If the release team needs licence information, keep the
     header in a metadata column, or keep it once per repository instead of once per file. This needs a decision
     from the lead.
   - A header that also holds real documentation (a file description inside the licence block) loses it.

## Medicine 5: Author names (F1)

1. **Disease:** F1 (ruling of 29 Oct: the developer's name or user name in an author line is personal data), in
   `@author`, `Author:`, `//@@author` and `Created by` lines of comments. Placeholders (`<NAME>`) are B4, not F1.
   Count: **93 of 500**. Evidence gives the type and the offset only.
   - `e0ebe203093970dc`: author name at offset 127
   - `c9eb2d8e4f9cacde`: author name at offset 455
   - `fad70faf21e9e64b`: author name at offset 247
2. **Medicine:** in comment lines, replace everything after the author tag with the surrogate `Author Name`, the
   same surrogate as M2: the name, and also a handle, email, phone number or home page on that line (found in
   `1a1a1d7ab0bf9188`: `@author <name> (<EMAIL>, <phone>)`, and in `@author <NAME> - <handle> (<site>)`). Keep a
   date after the name (`Created by <name> on 2018/4/9.` keeps `on 2018/4/9.`). Skip IDE and account names
   (`IntelliJ IDEA`, `Administrator`) and organisations (`... Ltd`, `... Team`).
   ```python
   import re

   # M5 (F1): everything after the author tag in a comment line is personal: the name, a handle, an email, a phone
   # number, a home page. It all becomes "Author Name"; a date after it stays ("Created by <name> on 2018/4/9.").
   AUTHOR_LINE = re.compile(r"(?im)^([ \t]*(?:/\*+|\*|//)?[ \t]*(?:@@?author\b[ \t]*[:：]?|author[ \t]*[:：]|created by)[ \t]*)"
                            r"([^\r\n]*\S)")
   NOT_A_PERSON = re.compile(r"(?i)^(?:intellij(?: idea)?|eclipse|netbeans|android studio|administrator|admin|root|user|"
                             r"author name)$|\b(?:ltd|inc|corp|gmbh|llc|team|group|foundation|project|company)\b")


   def m5_surrogate_author(t: str) -> str:
       def repl(m):
           value, end = re.match(r"(.*?)(\s*\*+/)?$", m.group(2)).groups()  # keep a closing */ on the same line
           cut = re.search(r"\s+on\s+\d|\s+\d{4}", value)
           name, rest = (value[:cut.start()], value[cut.start():]) if cut else (value, "")
           if not name.strip() or NOT_A_PERSON.search(name.strip().rstrip(".")):
               return m.group()
           return m.group(1) + "Author Name" + rest + (end or "")
       return AUTHOR_LINE.sub(repl, t)
   ```
3. **Action:** fix.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: changes 73 documents: 42 labelled F1, and 31 author lines that hold a
   `<NAME>`/`<EMAIL>` placeholder (labelled B4), which it cleans as well. The other 51 labelled F1 rows
   lose the name with the IDE template or licence header that held it (M6, M4). After the pipeline, no real author
   name is left in a labelled row. 0 of 120 clean.
5. **Side effects:**
   - Only author lines are covered. Personal data elsewhere in the code (an email or a phone number outside an
     author line) is not; I found none in this pack after M2.
   - Anything else on an author line is replaced too (for example a version note written after the name). A date
     right after the name is kept; text after the date is kept as well.
   - A user name that looks like an IDE or account name would be kept. A team or company name is kept on purpose:
     it is not a private person.
   - Code that prints the author (an author string outside a comment) is not changed, because only comment lines
     match.

## Medicine 6: IDE template comments (C1)

1. **Disease:** C1, comments that an IDE writes into a new file or method: `// TODO Auto-generated method stub`,
   IntelliJ's `Created with IntelliJ IDEA.` / `User:` / `Date:` / `Created by <user> on <date>`, NetBeans' "To change
   this license header, choose License Headers in Project Properties", file headers whose `Description:` was left
   empty, and an empty Javadoc with only an `@author` line. Count: **67 of 500**.
   - `7251a2b72d1d2a08`: `TODO Auto-generated method stub` at offset 293
   - `e0ebe203093970dc`: 3-line IntelliJ template comment at offset 108
   - `98ce12bcb94b8388`: IDE header template with an empty `Description:` at offset 125
2. **Medicine:** delete the `// TODO Auto-generated ...` lines. In a block comment that shows an IDE template, delete
   the template lines (author, user, date, time, created-by, empty description, the IDE's instructions) and keep the
   author's own description lines; if nothing is left, delete the whole comment (it uses `LIC_WORDS` and
   `NOT_LICENCE` from M4). Inside an IDE header, `Copyright`, `Email:`, `Blog:` and `Company:` lines are template
   fields too. Eclipse's class template (`<p>Title:`, an empty `<p>Description:</p>`, `<p>Copyright`) is handled
   the same way. An empty Javadoc with only an `@author` line goes, also when the name is a placeholder (it is labelled
   B4 only, ruling of 29 Oct, but the empty comment is still removed).
   ```python
   import re

   # M6 (C1): what an IDE writes into a new file or method. Inside a comment that shows an IDE template, the template
   # lines go and the author's own description stays; a comment with nothing else in it goes as a whole.
   IDE_LINE = re.compile(r"(?im)^[ \t]*//[ \t]*TODO Auto-generated (?:method|constructor|catch block|stub)[^\n]*\n")
   BLOCK = re.compile(r"[ \t]*/\*.*?\*/[ \t]*\n?", re.S)
   IDE_MARK = re.compile(r"(?im)TODO Auto-generated|To change this (?:licen[cs]e header|template)|choose Tools \| Templates|"
                         r"Created (?:by|with) IntelliJ IDEA|Created by [^\n]{1,80}? on \d|File \| Settings \| File Templates|"
                         r"^\s*\*?\s*User\s*:.*\n\s*\*?\s*Date\s*:|^\s*\*?\s*@(?:project|package)\s*[:：]|\$\{[\w.]{1,40}\}|"
                         r"^\s*\*?\s*<p>\s*Title\s*[:：]")  # Eclipse: <p>Title:</p> <p>Description:</p> <p>Copyright</p>
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
   ```
3. **Action:** fix.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: changes 77 documents: 65 labelled C1, 11 empty `@author <NAME>`
   Javadocs that are labelled B4 only (ruling of 29 Oct), and the Eclipse template in `865d813577b270f2` (labelled
   E4). The other 2 labelled C1 rows are IDE headers with a copyright line that M4 removes as a whole. 0 of 120 clean.
5. **Side effects:**
   - The first draft deleted whole comments, and that lost real descriptions, such as a Chinese summary line above
     `Created with IntelliJ IDEA.` (`e66b08d295a7ac80`). This version deletes only the template lines.
   - A hand-written comment that has an IDE line in it (for example `User:` and `Date:` lines that someone typed by
     hand) also loses those lines.
   - Generator banners are E1 (M7), not C1, and `TODO` comments written by the author are kept.
   - A copyright line is removed only inside a comment that already shows an IDE template; a Javadoc with only a
     description and a copyright line is kept (`dc290bee53a01177`-style headers without IDE lines).

## Medicine 7: Generated and decompiled code (E1)

1. **Disease:** E1, code written by a tool: generator banners (`AUTO-GENERATED FILE. DO NOT MODIFY.`, `Code
   generated by ...`, `This class was automatically generated by ...`) and decompiler output (`Decompiled by Jad`,
   `Decompiled by Procyon`). Count: **8 of 500**.
   - `905fe4685c78e088`: `AUTO-GENERATED FILE.  DO NOT MODIFY.` at offset 33 (an Android `R.java`)
   - `73e175e90e6e37da`: `Code generated by Microsoft (R) AutoRest Code Generator.` at offset 99
   - `ae36c21dcad92f1a`: `Decompiled by Procyon v0.5.36` at offset 109
2. **Medicine:** drop the document if a comment line holds one of these markers, or if any line is longer than 1000
   characters (minified code; none in this pack).
   ```python
   import re

   # M7 (E1): generated or decompiled code, dropped
   GENERATED = re.compile(r"(?im)^[ \t]*(?://|/?\*)[^\n]*(?:auto-generated file|do not (?:edit|modify)\b|decompiled (?:by|with)|"
                          r"code generated by|(?:file|class|code) (?:was|is|has been) (?:auto(?:matically)?[- ]?)?generated|"
                          r"generated by a tool)")  # "based on code auto generated by ..." is code a person adapted: kept


   def m7_drop_generated(t: str):
       if GENERATED.search(t) or any(len(line) > 1000 for line in t.split("\n")):
           return None
       return t
   ```
3. **Action:** drop.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: drops exactly the 8 labelled E1 documents; 0 of 120 clean.
5. **Side effects:**
   - Generated code is valid Java, and some of it (AutoRest clients, swagger models) is close to what people write.
     Dropping loses it; the gain is that the model does not learn generator banners and decompiler names
     (`var1`, `this.field = field;` patterns, no comments).
   - "Do not edit" in a hand-written comment ("do not edit this list by hand") would also drop the file. The rule only
     looks at comment lines, and I found no such case.
   - Code that a person adapted from generated code is kept: `3cba9087383097dd` says "This class is based on code
     auto generated by the swagger code generator", but it is a hand-written generic base class (`<W, E>`, method
     references, design notes). "Based on" is a credit, not a generator banner, so it does not match.
   - A decompiler banner also brings a copyright line (Jad's own); it is not the file's licence, so it is not E4.

## Medicine 8: Replacement characters in comments (A4)

1. **Disease:** A4, U+FFFD replacement characters: bytes lost before release, most likely GBK text read as UTF-8.
   Count: **2 of 500**; in both documents they are only in comments.
   - `912c53fa71c7d9ad`: `'⟦U+FFFD⟧'` at offsets 2841, 2846, 2854 (an apostrophe lost in an English comment)
   - `9b95cf192922d106`: `'⟦U+FFFD⟧⟦U+FFFD⟧'` at offsets 144, 147 (most likely 年, 月, 日 and 下午 lost in a date)
2. **Medicine:** in comment lines only, a run of U+FFFD between two other characters becomes one space, and any other
   run is deleted. Strings and code are not touched.
   ```python
   import re

   # M8 (A4): U+FFFD replacement characters in comments (bytes lost before release). Between two words a run becomes
   # one space, elsewhere it goes; strings and code are not touched.
   COMMENT_LINE = re.compile(r"(?m)^[ \t]*(?://|/?\*).*$")


   def m8_clean_replacement_chars(t: str) -> str:
       def fix(m):
           return re.sub("\ufffd+", "", re.sub(r"(?<=[^\s\ufffd])\ufffd+(?=[^\s\ufffd])", " ", m.group()))
       return COMMENT_LINE.sub(lambda m: fix(m) if "\ufffd" in m.group() else m.group(), t)
   ```
3. **Action:** fix.
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: changes exactly the 2 labelled A4 documents; 0 of 120 clean.
5. **Side effects:** the lost characters cannot come back; the comment only stops showing the replacement mark.
   `2017��3��13��` becomes `2017 3 13`, and `don�t` becomes `don t`. A U+FFFD inside a string literal stays,
   because deleting it would change the program.

## Medicine 9: Joined or scraped files (C4)

1. **Disease:** C4, two documents joined into one. Count: **1 of 500**.
   - `1227540794647c4d`: `'_____________________________…'` at offset 26: two LeetCode "sample submission" answers
     scraped from the site, joined by lines of underscores and `sample 1 ms submission` captions
2. **Medicine:** drop the document if a line outside a comment is only a separator (20 or more `_` or `=`) or a
   `sample <N> ms|kb submission` caption. Java cannot have such a line, so the file does not compile as it is.
   ```python
   import re

   # M9 (C4): a scraped page or two files joined into one: a separator line or a "sample 12 ms submission" caption
   # outside a comment. Java cannot have such a line, so the file does not compile; it is dropped.
   JOINED = re.compile(r"(?mi)^[ \t]*(?:_{20,}|={20,}|sample \d+ (?:ms|kb) submission)[ \t]*$")


   def m9_drop_joined(t: str):
       return None if JOINED.search(t) else t
   ```
3. **Action:** drop (my verdict for this row).
4. **Harm test:** gold set (116): 0 changed, 0 dropped, PASS. Own sheet: drops exactly the 1 labelled C4 document; 0 of 120 clean.
5. **Side effects:** a separator inside a block comment that has no `*` at the start of the line would also match.
   I found none in the pack. Splitting the file at the separators would keep the two answers, but each answer alone
   is still a scraped contest solution, so I drop it.

## Appendix: the pipeline

The last check drops a document that has nothing left but its `package` and `import` lines. In this pack that
is one file, `9fb5d47488af3c6e`: a `package-info.java` that held only a licence header, an IntelliJ template and the
`package` line, which I labelled `drop`. The other `package-info.java` (`f15940c465a4696a`) has a real package
description, so it keeps its Javadoc and is not dropped.

```python
import re

# Last step: a file that was only a licence and an IDE template has nothing left but its package line. Drop it.
PACKAGE_OR_IMPORT = re.compile(r"(?m)^[ \t]*(?:package|import)\b[^;\n]*;[ \t]*$")


def drop_if_nothing_left(t: str):
    return None if not PACKAGE_OR_IMPORT.sub("", t).strip() else t


# M1 and M3 first: the others expect clean first lines and LF. M7 and M9 drop before anything is rewritten.
PIPELINE = [m1_strip_meta_header, m3_normalise_newlines, m7_drop_generated, m9_drop_joined, m4_strip_licence_header,
            m6_strip_ide_templates, m5_surrogate_author, m2_surrogate_placeholders, m8_clean_replacement_chars,
            drop_if_nothing_left]


def cure(t: str):
    for med in PIPELINE:
        t = med(t)
        if t is None:
            return None
    return t
```
