# Medicine sheet: cadj-commits (kunal2016)

Status: counts are from all 500 labelled rows (427 clean, 73 fix). Harm tests are run with the
Data A `harm_test.py` (main, sha256 `4dcc04bf8ac553c9`) on the official cadj-commits gold set, and on my own 427 clean rows.

**Gold set.** `teams/02-data-b/gold/cadj-commits_gold.csv`, added by Data B (lead shankarpandala) in
theschoolofai/era-v5-lab#233 on 2 Nov: **413 documents** that at least two of the three readers (kunal2016 #42,
sureshmantha #97, pradeep-kumar-gs #111) marked clean, with no fix or drop vote from anyone. sha256 `ba4da5c2233e5ef6`.
Limit: `max(1, floor(1% of 413))` = **4 documents**. The earlier figures used a 121-document backup copy built on 30 Oct,
before all three label sheets were complete.

Pack: about 500 commits (commit message, file path, old contents, new contents) from
bigcode/commitpackft, about 71 each in Python, JavaScript, TypeScript, Java, C++, Go and Rust.

Not found in this pack, so no medicine: secrets (E3), chat markers (B3), mojibake (A3),
replacement characters (A4), duplicates (H1, H2), data blobs (E2), phone or ID numbers.
A2 (5 documents, 311 carriage returns) and A1 (1 document) are at or below the five-case bar
counted by documents; medicines 3 and 4 are included anyway because they are cheap and safe, and
the team is likely to need them in spec v1. C1 (1) gets no medicine.

## Medicine 1: F1 personal emails and profile URLs

1. **Disease:** F1, personal data of private people. 41 labelled documents in the 500 rows
   (the medicine changes 42 of the 500 documents, 71 email addresses). Most are `author_email=` in Python
   `setup.py` files and `Signed-off-by:` lines in commit messages. Each address usually appears
   twice, once in the old and once in the new file. Examples (type and offset only):
   - `e0c1e30626b9b1ff`: email at offset 518, 1092 (`author_email` in setup.py)
   - `19c86ce5aabab9b7`: email at offset 167 (Signed-off-by), 477, 1280 (`author_email`)
   - `17874ea94ee0e7e0`: LinkedIn profile URL with a person's name at offset 430, 1163 (seed data)

2. **Medicine:** replace every email address of a private person, and every LinkedIn profile
   URL, with a fixed placeholder. Leave role addresses (`info@`, `admin@`, `support@` and
   similar), GitHub noreply addresses and reserved example or test domains untouched.

   ```python
   import re

   EMAIL_PLACEHOLDER = "user@example.com"   # Q1.3: or "<EMAIL>"
   PROFILE_PLACEHOLDER = "https://www.linkedin.com/in/example"  # Q1.4
   EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
   ROLE_LOCAL = {"info", "admin", "team", "contact", "support", "hello", "office", "mail",
                 "webmaster", "help", "noreply", "no-reply", "sales", "security", "abuse", "postmaster"}
   SAFE_DOMAIN = re.compile(r"(^|\.)(example\.(com|org|net)|test\.com|localhost|domain\.com|email\.com|"
                            r"users\.noreply\.github\.com|noreply\.github\.com)$", re.I)
   PROFILE_URL = re.compile(r"https?://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", re.I)


   def is_personal_email(local, domain):
       return local.lower() not in ROLE_LOCAL and not SAFE_DOMAIN.search(domain.lower())


   def cure_f1(text):
       """Replace private people's emails and LinkedIn profile URLs with placeholders."""
       def repl(m):
           return EMAIL_PLACEHOLDER if is_personal_email(m.group(1), m.group(2)) else m.group(0)
       new = EMAIL.sub(repl, text)
       new = PROFILE_URL.sub(PROFILE_PLACEHOLDER, new)
       return new
   ```

3. **Action:** fix. The code is good training data; only the address is removed. The
   placeholder is a valid address, so strings like `author_email="user@example.com"` stay valid code.

4. **Harm test:** on the gold set (413 documents) the medicine changes **0** and drops **0**
   (0.00%, limit 4 documents): **PASS**. On my 427 clean rows it changes **1** (0.23%): **PASS**. It fixes
   41 of 41 labelled F1 documents. The one changed clean row is `8ae8af60edff9ffb`, a test that creates a made-up user with a
   fake address. Replacing it does not break the code, but it counts against the 1% limit.

5. **Side effects:**
   - Made-up addresses in tests and seed data are replaced too, unless their domain is a reserved
     example domain. With a larger gold set this one case is about 0.5%; still under the limit, but
     close if many test files contain fake users.
   - Role addresses are kept even when they belong to a one-person company.
   - Names are not touched (author names are normal open-source credit, team decision 1.5).
   - Emails written in other forms (`name [at] domain`) are not caught. None found in this pack.
   - Only LinkedIn `/in/` profiles are covered; other profile sites are not.

## Medicine 2: E4 long licence headers

1. **Disease:** E4, repeated licence headers. 33 labelled documents in the 500 rows (the medicine
   changes 32 of the 500 documents), including 12 Rust compiler files with the 9-line rustc
   Apache-2.0/MIT header. Because each document holds the old and the new file, every header appears twice.
   The medicine would remove about 25,600 characters (2.8% of the pack). Examples:
   - `f1655eb8394db886`: 19-line AGPL-3.0 header at offset 182 (old) and 1707 (new)
   - `abd2e71e0f18d22a`: 19-line Apache-2.0 header at offset 463 (old) and 1282 (new)
   - `d6617dadff45989c`: 22-line MIT licence at offset 120 (old) and 24-line at 1261 (new)

2. **Medicine:** at the top of each file version, find the header comment block. If it has
   8 or more lines (team decision 2.1) and contains a recognised licence text (GPL, AGPL, LGPL,
   Apache-2.0, MIT, BSD, MPL-2.0, or Apache-2.0 OR MIT), keep the lines above the licence text
   (copyright holder, author, project) and replace the licence text with one
   `SPDX-License-Identifier` line in the file's own comment style. `/* ... */` blocks are rebuilt
   as a well-formed comment. A doc comment that follows the header (`/** ... */`) is kept.
   The full rule (runnable as written):

   ```python
   import re

   E4_MIN_LINES = 8                         # Q2.1: shorter notices are kept
   E4_MODE = "spdx"                         # Q2.2: "spdx" (replace with one line) or "remove"
   # ---- E4: long licence headers --------------------------------------------------
   SECTION = re.compile(r"^### (old contents|new contents)\n", re.M)
   NEXT_SECTION = re.compile(r"^### ", re.M)
   LICENCE_TYPES = [
       ("AGPL-3.0", re.compile(r"GNU Affero General Public License", re.I)),
       ("LGPL", re.compile(r"GNU Lesser General Public License", re.I)),
       ("GPL", re.compile(r"GNU General Public License", re.I)),
       ("Apache-2.0", re.compile(r"Apache License,?\s+Version 2\.0|apache\.org/licenses/LICENSE-2\.0", re.I)),
       ("MIT", re.compile(r"Permission is hereby granted, free of charge", re.I)),
       ("BSD", re.compile(r"Redistribution and use in source and(/or)? binary forms|BSD-style license", re.I)),
       ("MPL-2.0", re.compile(r"Mozilla Public License", re.I)),
   ]
   LICENCE_WORDS = re.compile(r"(licen[cs]e|copyright|warranty|redistribut|permission is hereby granted)", re.I)
   COMMENT = re.compile(r"^\s*(#|//|/\*+|\*+/?|\"\"\"|''')")


   LICENCE_START = re.compile(r"(This program is free software|Licensed under the|Licensed to the|Permission is hereby granted|"
                              r"Redistribution and use in source|This Source Code Form is subject|Use of this source code is governed|"
                              r"This library is free software|you can redistribute it|THIS SOFTWARE IS PROVIDED)", re.I)
   ONLY_MARKS = re.compile(r"^\s*([#/*=\-]+)\s*$")


   def _prefix(line):
       m = re.match(r"^\s*(#+|//+|/\*+|\*+/?)", line)
       return (m.group(1)[:2] if m else "")


   def _leading_block(lines, start=0):
       """(i, j): the comment block at or after line `start`. Stops at a blank line unless the
       next line continues the SAME comment style (so a following /** doc comment */ is kept)."""
       i = start
       while i < len(lines) and (not lines[i].strip() or lines[i].startswith("#!") or "coding" in lines[i][:40]):
           i += 1
       if i >= len(lines) or not _prefix(lines[i]):
           return None
       style = _prefix(lines[i])
       block_style = {"/*": {"/*", "*", "*/"}, "*": {"/*", "*", "*/"}}.get(style, {style})
       j = i
       while j < len(lines):
           pf = _prefix(lines[j])
           if pf and (pf in block_style or pf[:1] in {x[:1] for x in block_style}):
               if style != "/*" and pf.startswith("/*"):
                   break                      # a new /** doc comment */ starts: keep it
               j += 1
               if style == "/*" and lines[j - 1].strip().endswith("*/"):
                   break
               continue
           if not lines[j].strip() and j + 1 < len(lines) and _prefix(lines[j + 1]) == style and style != "/*":
               j += 1
               continue
           break
       return i, j


   DUAL_APACHE_MIT = re.compile(r"Apache License,?\s+Version 2\.0.{0,200}?\bor the MIT license", re.I | re.S)


   def _spdx_line(block_text, style):
       kind = "Apache-2.0 OR MIT" if DUAL_APACHE_MIT.search(block_text) else \
           next((k for k, rx in LICENCE_TYPES if rx.search(block_text)), None)
       if not kind:
           return None
       prefix = "#" if style.startswith("#") else "//"
       return f"{prefix} SPDX-License-Identifier: {kind}"


   def cure_e4(text):
       """Replace the licence TEXT at the top of each file version with one SPDX line.
       Lines above the licence text (copyright holder, author, project) are kept."""
       out, pos, changed = [], 0, False
       for m in SECTION.finditer(text):
           start = m.end()
           nxt = NEXT_SECTION.search(text, start)
           end = nxt.start() if nxt else len(text)
           out.append(text[pos:start])
           body = text[start:end]
           lines = body.split("\n")
           b = _leading_block(lines)
           # the licence may sit in the SECOND header block, after a /** file description */
           if b and not any(LICENCE_START.search(l) for l in lines[b[0]:b[1]]):
               b2 = _leading_block(lines, b[1])
               if b2 and any(LICENCE_START.search(l) for l in lines[b2[0]:b2[1]]):
                   b = b2
           if b:
               i, j = b
               k = next((x for x in range(i, j) if LICENCE_START.search(lines[x])), None)
               if k is not None:
                   lic = lines[k:j]
                   # count the whole header block (copyright lines + licence text), as labelled
                   n_lines = len([l for l in lines[i:j] if l.strip() and not ONLY_MARKS.match(l)])
                   spdx = _spdx_line("\n".join(lic), _prefix(lines[i]))
                   if n_lines >= E4_MIN_LINES and spdx:
                       style = _prefix(lines[i])
                       if style.startswith("/*"):
                           # C-style block: rebuild a well-formed /* ... */ comment
                           head = [l for l in lines[i + 1:k] if l.strip() and not ONLY_MARKS.match(l)]
                           tag = " * " + spdx.split(" ", 1)[1]
                           repl = ["/*"] + head + ([tag] if E4_MODE == "spdx" else []) + [" */"]
                           if E4_MODE != "spdx" and not head:
                               repl = []
                       else:
                           head = [l for l in lines[i:k] if l.strip() and not ONLY_MARKS.match(l)]
                           repl = head + ([spdx] if E4_MODE == "spdx" else [])
                       body = "\n".join(lines[:i] + repl + lines[j:])
                       changed = True
           out.append(body)
           pos = end
       out.append(text[pos:])
       new = "".join(out)
       return new
   ```

   Example, `f1655eb8394db886`, the old file goes from 19 header lines to:

   ```
   #    Copyright (C) 2015 Agile Business Group sagl
   #    (<http://www.agilebg.com>)
   # SPDX-License-Identifier: AGPL-3.0
   ```

3. **Action:** fix (team decision 2.2: replace with SPDX, rather than remove entirely).

4. **Harm test:** on the gold set (413 documents) the medicine changes **0** and drops **0**
   (0.00%, limit 4 documents): **PASS**; on my 427 clean rows it changes **0**: **PASS**. It fixes 32 of 33 labelled
   E4 documents. The one it leaves alone is `ab46a006529db278` (Serde): the same Apache-2.0/MIT
   wording as the rustc header but 7 lines, under `E4_MIN_LINES`. I label all 13 Rust-style headers
   E4 for consistency; whether such pointer notices are E4 at all is open (Q2.1).
   `396118e5988bcbfc` already uses the short SPDX form, so it is labelled clean.
   Short licence notices are left untouched by design, and my label sheet marks them clean:
   Microsoft's 4-line MIT notice (`9b72597490efcd15`), Chromium's 3-line BSD notice
   (`81d9e46b717ff00c`), the LLVM notice with an SPDX line (`0a9865cc8da6d8b5`), and 2-line notices
   such as `1f6e19669909b827`. A licence in the second header block, after a `/** file
   description */`, is found too (`5ac3cfce100afb72`).

5. **Side effects:**
   - Licence wording the patterns do not recognise is left unchanged (missed, not damaged).
   - Comment lines inside the header block that are not licence text but come after it are removed
     with it.
   - Licence text in the middle of a file, or in a docstring, is not touched.
   - The licence fact is kept as an SPDX line, but the exact wording (for example "or later"
     versions) is lost.
   - Checked on all 31 changed documents: the number of `/*` and `*/` stays balanced, so no
     comment is left open or closed by mistake.

## Medicine 3: A2 carriage returns

1. **Disease:** A2, control characters. 5 labelled documents in the 500 rows, which is every A2 document in the pack,
   311 carriage returns (U+000D) in total. All are Windows line endings (CRLF). Examples:
   - `f9b766f8d70fd170`: `170 U+000D CARRIAGE RETURN (14x)`, in the commit message
   - `aa905c0bfba1f969`: 99 carriage returns (document 197)
   - `4c25f9f3425b8be1`: 76 carriage returns (document 282)

   Five documents is not *more than* five, so this medicine is optional if the team counts by
   documents; counted by occurrences (311) it is required. Team decision.

2. **Medicine:** turn every CRLF into LF, and any remaining lone CR into LF.

   ```python
   def cure_a2(text):
       """Turn CRLF into LF, and any lone CR into LF. Other control characters are not
       touched (none were found in this pack; form feeds can be deliberate in old C code)."""
       new = text.replace("\r\n", "\n").replace("\r", "\n")
       return new
   ```

3. **Action:** fix.

4. **Harm test:** changes **0** of the 413 gold documents and **0** of my 427 clean rows (0.00%):
   **PASS**. Fixes 5 of 5
   labelled cases, which is every A2 document in the pack. The number of lines stays the same.

5. **Side effects:**
   - A file that needs CRLF on purpose (for example a Windows batch file or a test of line
     endings) loses it. None in this pack.
   - Other control characters (form feed, escape) are not touched; none were found, and form feeds
     can be deliberate page breaks in old C code.

## Medicine 4: A1 byte-order mark at the start of a file (optional)

1. **Disease:** A1, invisible junk. 1 document: `eefa9818729074c3`,
   `116 U+FEFF ZERO WIDTH NO-BREAK SPACE (2x)`, at the start of both the old and the new file.
   Below the five-case bar; included because the rule is one line and safe.

2. **Medicine:** remove U+FEFF only where it is the first character of a file version.

   ```python
   import re

   FILE_START_BOM = re.compile(r"(^### (?:old contents|new contents)\n)\ufeff", re.M)


   def cure_a1(text):
       """Remove a BOM (U+FEFF) that sits at the very start of a file version. A U+FEFF
       anywhere else is left alone (it could be inside a string on purpose)."""
       new = FILE_START_BOM.sub(r"\1", text)
       return new
   ```

3. **Action:** fix.

4. **Harm test:** changes **0** of the 413 gold documents and **0** of my 427 clean rows (0.00%):
   **PASS**. Fixes 1 of 1.

5. **Side effects:** a U+FEFF anywhere else is left alone, because inside a string it can be
   deliberate. Other A1 characters (zero-width space, bidi marks) are not handled; none were
   found in this pack.

## How to reproduce

Each medicine has one ` ```python ` block that defines `cure_<code>(text)` and returns the new text
(the Data A convention). With the Data A tools on main (Linux, macOS or WSL), and the gold set
`teams/02-data-b/gold/cadj-commits_gold.csv` as `cadj-commits_gold.csv`:

```
python -I teams/01-data-a/tools/medicine_extract.py <this medicine.md> --out /tmp/rules.py --registry /tmp/registry.json
for c in F1 E4 A2 A1; do
  python -I teams/01-data-a/tools/harm_test.py --pack cadj-commits.parquet \
      --gold cadj-commits_gold.csv --rules <this medicine.md> --rule $c
done
```

Result on 2 Nov (413 gold documents, limit 4): F1 0 changed / 0 dropped, PASS; E4 0 / 0, PASS; A2 0 / 0, PASS;
A1 0 / 0, PASS.

Registry IDs (29 Oct extraction): F1 `DB-F1-002`, E4 `DB-E4-001`, A2 `DB-A2-001`, A1 `DB-A1-001`.
