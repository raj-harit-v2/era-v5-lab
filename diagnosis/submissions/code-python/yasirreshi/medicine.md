# Medicine sheet: code-python (yasirreshi)

Pack `code-python` (source `bigcode/starcoderdata`, 500 documents, 3.07 M characters). Label sheet: `labels.csv` in this folder.

Six diseases occur more than five times, so this sheet has six medicines. They run in file order. M1 comes first,
because the other fix rules expect the file to start with code. The two drop rules (M4, M6) remove the M1 line themselves.

| # | Disease | Count | Action | Gold set: changed, dropped (limit 1) | Standard library proxy (2,052 files) |
|---|---|---|---|---|---|
| M1 | B3 StarCoder metadata tokens | 272 | fix | 0, 0: PASS | 0 |
| M2 | B4 PII-redaction placeholders | 83 | fix | 0, 0: PASS | 0 |
| M3 | E4 repeated licence header | 63 | fix | 0, 0: PASS | 3 (0.15 %) |
| M4 | E1 generated code | 18 | drop | 0, 0: PASS | 6 (0.29 %) |
| M5 | A2 control characters (CRLF) | 17 | fix | 0, 0: PASS | 0 |
| M6 | F2 benchmark leak (competitive-programming solutions) | 8 | drop | 0, 0: PASS | 0 |
| | All six in file order | | | 0, 0: PASS | |

## How the harm test was run

**Gold set:** Data A's `code-python_gold.csv` (branch `g1-harm-test`, commit `880258f` of 31 Oct), the 142 documents of this
pack that two other readers marked `clean`. The limit is max(1, floor(1 % of 142)) = 1 document changed or dropped for each rule.

This sheet follows the format of Data A's `harm_test.py`: one `**Disease:**` section for each code, one public function
in each section, and every python block with its own imports. M4 and M6 take `doc`, because they read the file path in
`url`. The command to repeat the test:

```
python -I teams/01-data-a/tools/harm_test.py --pack code-python.parquet \
  --gold teams/01-data-a/gold/code-python_gold.csv \
  --rules diagnosis/submissions/code-python/yasirreshi/medicine.md --rule all
```

I did not run `harm_test.py` itself. I ran the rules with my own runner, which reads this sheet and counts the same way:
the function of each section, `True` means drop, a different string means changed, and then all rules in file order,
where a drop ends the document. Every rule changed 0 and dropped 0 of the 142 gold documents (and 0 of the 46 in the build of 29 Oct).

**Proxy gold sets** (made before the gold set existed, kept as a wider check):

- the 158 documents of this pack that I labelled `clean`: no medicine touches any of them;
- the CPython 3.15 standard library: all 2,052 `.py` files, and a sample of 200 (`random.Random(0).sample`).

A document counts as harmed if the medicine changes even one character of it, or drops it.

I also ran each medicine on the whole pack and compared it with my labels. For each one: TP is a labelled document that the medicine catches, FP is an unlabelled document that it touches, and FN is a labelled document that it misses. After the full fix chain, 0 files that compiled before fail to compile, and 7 files that did not compile now compile (M2 repairs `password=<PASSWORD>` and similar).

---

## Medicine 1: B3, StarCoder metadata tokens

1. **Disease:** B3, 272 documents (54 % of the pack). The first line holds `<reponame>`, `<filename>` and/or `<gh_stars>` tokens from the
   StarCoder training format. Examples:
   - `0d1e11b4c0740741`: `<gh_stars>0` at offset 0
   - `680d4363d4d1bd8e`: `<gh_stars>100-1000` at offset 0
   - `b77c702904986d05`: `<filename>django_nyt/migrations/0003_subscription.py` at offset 0

   The tokens appear only in the first line, never later in a file. They are the reason that 259 files of the pack do not compile.
2. **Medicine:** if the file starts with a line made only of these three tokens and their values, remove that line.

   ```python
   GHOST_LINE = re.compile(r"\A(?:<reponame>[^\n<]*)?(?:<filename>[^\n<]*)?(?:<gh_stars>[^\n]*)?\n")

   def fix_ghost_header(text: str) -> str:
       m = GHOST_LINE.match(text)
       if m and m.end() > 1:
           return text[m.end():]
       return text
   ```
3. **Action:** fix (strip the line). Keep the repo name, path and stars in metadata, not in the text.
4. **Harm test:** gold set: 0 / 142 changed. PASS. Proxies: 0 / 158 clean pack documents, 0 / 2,052 standard library files.
   On the pack: TP 272, FP 0, FN 0.
5. **Side effects:** a real file whose first line starts with one of these three exact tokens would lose that line. I found none.
   The rule does not remove the tokens in the middle of a file. If they occur there, that is a different disease (C4, two files joined).

## Medicine 2: B4, PII-redaction placeholders left by earlier cleaning

1. **Disease:** B4, 83 documents. StarCoder's PII redaction replaced names, emails, passwords and keys with `<NAME>`, `<EMAIL>`,
   `<PASSWORD>` and `<KEY>`. As the ruling of 25 Oct says, these are labelled B4 with the note `PII placeholder`, not F1.
   The model would learn to write these placeholders. In 7 files the placeholder stands where code was, so the
   file no longer parses. Examples:
   - `9e00aaaeab42bd57`: `password=<PASSWORD>,` (offset 10729, syntax error)
   - `3d16039cc5801e00`: `SECRET_KEY = <KEY>` (offset 188, syntax error)
   - `f3abd9691b48873d`: `#written by <NAME> (<EMAIL>)` (offsets 62 and 70, in a comment)
2. **Medicine:** replace each placeholder with a fake value of the same type. Choose the value from a small pool, from a hash of the
   position, so that the model does not see one fixed fake name everywhere. In strings and comments, write the value as plain text. In
   code position (the tokenizer sees `<`, `NAME`, `>`), write it as a quoted string, or as an identifier after a dot, so the file parses
   again. Leave regex named groups `(?P<NAME>...)` and escaped `\<KEY>` alone.

   ```python
   import hashlib, io, tokenize

   PLACEHOLDER = re.compile(r"(?<!\?P)(?<!\\)<(NAME|EMAIL|PASSWORD|KEY)>")
   FAKE_NAMES = ["Alex Morgan", "Sam Lee", "Jordan Patel", "Taylor Kim", "Robin Silva", "Casey Novak", "Jamie Chen", "Riley Okafor"]

   def _fake(kind, seed):
       h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
       name = FAKE_NAMES[h % len(FAKE_NAMES)]
       if kind == "NAME":
           return name
       if kind == "EMAIL":
           return name.lower().replace(" ", ".") + "@example.com"
       return "dummy-" + kind.lower() + "-" + format(h % 16**8, "08x")

   def fix_placeholders(text):
       if not PLACEHOLDER.search(text):
           return text
       code_spans = []                      # placeholders that the tokenizer sees as code: OP '<' NAME OP '>'
       try:
           lines = text.splitlines(keepends=True)
           starts = [0]
           for ln in lines:
               starts.append(starts[-1] + len(ln))
           toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
           for a, b, c in zip(toks, toks[1:], toks[2:]):
               if a.string == "<" and b.type == tokenize.NAME and c.string == ">" and b.string in ("NAME", "EMAIL", "PASSWORD", "KEY"):
                   code_spans.append(starts[a.start[0] - 1] + a.start[1])
       except (tokenize.TokenError, SyntaxError, IndentationError):
           pass                             # broken file: plain text replacement everywhere

       def repl(m):
           val = _fake(m.group(1), m.group(0) + str(m.start()))
           if m.start() in code_spans:
               before, after = text[m.start() - 1: m.start()], text[m.end(): m.end() + 1]
               if before == "." or re.match(r"\w", before + " ") or re.match(r"\w", after + " "):  # os.<PASSWORD>.get, <PASSWORD>_x
                   return m.group(1).lower()
               return repr(val)
           return val

       return PLACEHOLDER.sub(repl, text)
   ```
3. **Action:** fix. Before: `password=<PASSWORD>,`. After: `password='dummy-password-164621cf',`.
4. **Harm test:** gold set: 0 / 142 changed. PASS. Proxies: 0 / 158, 0 / 2,052. On the pack: TP 83, FP 0, FN 0.
   It repairs all 7 files that the placeholders broke.
5. **Side effects:**
   - A placeholder inside an identifier gets a guessed name. `os.<PASSWORD>.get` becomes `os.password.get`, and `<PASSWORD>_p...`
     becomes `password_p...`. Both parse, but neither is the original code.
   - The skip rule for escaped placeholders leaves one real redaction in place: `'\\<PASSWORD>'` in `8f92de0e125970be`.
   - My first version also rewrote `(?P<NAME>...)` regex groups in the standard library (`gettext.py`) and the escaped `\<KEY>` in
     `_pyrepl/keymap.py`. The final rule does not.
   - Real code that uses the literal text `<EMAIL>` or `<NAME>` as a template marker would be changed.

## Medicine 3: E4, repeated licence header

1. **Disease:** E4, 63 documents. The same full licence text is at the top of many files: 42 Apache-2.0, 6 BSD, 5 GPL, 5 MIT, 1 LGPL,
   1 ISC, 1 MPL, 1 Qiskit, 1 UC Berkeley Pacman. They run 8 to 29 lines, and most are 11. In `317d0f9362907468` the header appears twice.
   Examples:
   - `cc46017245578753`: `# Licensed under the Apache License, Version 2.0 (the "License");` (11 lines from offset 78)
   - `890651e4733e8944`: `# Ansible is free software: you can redistribute it and/or modify` (GPL, 12 lines from offset 84)
   - `5e467bb5ce89997f`: `# Redistribution and use in source and binary forms, with or without` (BSD, 25 lines from offset 106)
2. **Medicine:** look only at the file header (leading comments, the first module docstring, and the comments right after it). If it holds the full text of a known
   licence (a start phrase and an end phrase of the same licence), delete the licence paragraph. Keep the shebang, the coding line,
   the docstring quotes and the short copyright line.

   ```python
   LICENCE_FULL = [  # (start phrase, end phrase) of each full licence text
       (re.compile(r"licensed under the apache license|licensed to the apache software foundation|under the apache license, version 2\.0", re.I),
        re.compile(r"limitations under the license", re.I)),
       (re.compile(r"free software[;:,]? you can redistribute it|is free software: you can redistribute", re.I), re.compile(r"without any warranty", re.I)),
       (re.compile(r"redistribution and use in source and binary forms", re.I), re.compile(r"possibility of such damage|warrant", re.I)),
       (re.compile(r"permission is hereby granted, free of charge", re.I), re.compile(r"in the software|warranty", re.I)),
       (re.compile(r"permission to use, copy, modify, and/or distribute this software", re.I), re.compile(r"warrant", re.I)),
       (re.compile(r"mozilla public license", re.I), re.compile(r"end license block|warranty", re.I)),
   ]
   LICWORD = re.compile(r"licen[cs]|copyright|warrant|permission|distribut|software|merchantab|liabil|express|implied|limitations|"
                        r"http|you may|obtain a copy|redistribut|conditions|disclaim|damages|foundation|gnu|notice|see the|governing", re.I)
   KEEP_LINE = re.compile(r"^\s*#!|coding[:=]|^\s*[rRuU]?(\"\"\"|''')\s*$")

   def _header_lines(lines):
       i = 0
       while i < len(lines) and (lines[i].lstrip().startswith("#") or not lines[i].strip()):
           i += 1
       if i < len(lines) and re.match(r"\s*[rRuU]?(\"\"\"|''')", lines[i]):
           q = re.match(r"\s*[rRuU]?(\"\"\"|''')", lines[i]).group(1)
           j = i
           if q not in lines[i].split(q, 1)[1]:
               j += 1
               while j < len(lines) and q not in lines[j]:
                   j += 1
           i = j + 1
           while i < len(lines) and (lines[i].lstrip().startswith("#") or not lines[i].strip()):  # comments after it
               i += 1
       return min(i, len(lines))

   def fix_licence_header(text):
       lines = text.split("\n")
       n = _header_lines(lines)
       norm = re.sub(r"[ \t]*\n[ \t]*#*[ \t]*", " ", "\n".join(lines[:n]))
       for start_rx, end_rx in LICENCE_FULL:
           ma = start_rx.search(norm)
           if not (ma and end_rx.search(norm, ma.start())):
               continue
           first_word = ma.group().split()[0].lower()
           first = next(k for k in range(n) if first_word in lines[k].lower() and LICWORD.search(lines[k]))
           while first > 0 and LICWORD.search(lines[first - 1]):
               first -= 1
           last = k = first
           while k < n:
               if LICWORD.search(lines[k]):
                   last = k
               elif lines[k].strip().strip("#").strip() and k - last > 2:
                   break
               k += 1
           kept = [ln for k, ln in enumerate(lines) if not (first <= k <= last and not KEEP_LINE.search(ln))]
           out = "\n".join(kept)
           return re.sub(r"\A(\s*#\s*\n)+", "", re.sub(r"\n(?:[ \t]*#?[ \t]*\n){3,}", "\n\n", out))
       return text
   ```
3. **Action:** fix (remove the licence paragraph from the header, keep the code). The licence of each file stays in the metadata.
4. **Harm test:** gold set: 0 / 142 changed. PASS. Proxies: 0 / 158, 0 / 200. Over all 2,052 standard library files: 3 changed
   (0.15 %), `profile.py`, `pstats.py` and `test/test_epoll.py`, which really have a full licence text. On the pack: TP 61, FP 0, FN 2.
5. **Side effects:**
   - Licences without a standard text are not caught. That is the 2 FN: the Qiskit header (`fda2f1d7ddbd03a1`) and the Berkeley Pacman
     header (`317d0f9362907468`). Short pointers such as `SPDX-License-Identifier` or "see LICENSE" are kept on purpose.
   - When the licence is inside the module docstring, the rest of the docstring stays, but the docstring may end up short. In
     `3999319da3d5ce96` only the title line and the copyright line are left.
   - A file whose only content is the licence comment would become almost empty.

## Medicine 4: E1, generated code

1. **Disease:** E1, 18 documents: 10 Django migrations, 2 Pulumi SDK files, 1 each of AutoRest, KBase client, wxGlade GUI,
   fuzza test fixture, xsdata package and a generated cell-library description. Examples:
   - `fcab84d53c43cbf9`: `# Generated by Django 3.1.2 on 2021-09-30 05:02`
   - `6359488cb66a0aa6`: `# *** WARNING: this file was generated by the Pulumi Terraform Bridge (tfgen) Tool. ***`
   - `4280e8634129c11b`: `# Code generated by Microsoft (R) AutoRest Code Generator.`
2. **Medicine:** drop the file if its first 15 lines (after M1) carry a generator marker, or if its path is a Django migration.

   ```python
   GENERATED = re.compile(r"generated by django \d|this file was generated by|code generated by|autogenerated by|generated by wxglade|"
                          r"\bautogenerated\b|\bauto-generated\b|do not edit|automatically generated by|generated by the protocol buffer", re.I)

   def is_generated(doc):
       """doc is the pack row: its text, and its url (repo name and file path)."""
       text = re.sub(r"\A(?:<reponame>[^\n<]*)?(?:<filename>[^\n<]*)?(?:<gh_stars>[^\n]*)?\n", "", doc["text"])
       head = "\n".join(text.split("\n")[:15])
       return bool(GENERATED.search(head)) or bool(re.search(r"/migrations/\d{4}_\w+\.py$", doc["url"]))
   ```
3. **Action:** drop.
4. **Harm test:** gold set: 0 / 142 dropped. PASS. Proxies: 0 / 158; 1 / 200 dropped (0.50 %), `stringprep.py` (`DO NOT EDIT`).
   Over all 2,052 standard library files: 6 dropped (0.29 %). All six are generated (`token.py`, `_opcode_metadata.py`,
   `pydoc_data/topics.py` ...), but they count as harm on a gold set. PASS. On the pack: TP 16, FP 0, FN 2.
5. **Side effects:**
   - Generated files without a marker are missed: the 2 FN (`1668d8b133fd7886` cell-library description, `67139d073199b77e` xsdata
     package). A path rule for `output/models/` would catch the second, but it is too specific to this repo.
   - The ruling of 25 Oct: E1 only when the code below the header is generated too. All 18 labelled files are generated
     code (migrations, SDK and client generators). The marker rule cannot see that, so a hand-written file with such a
     header would be dropped.
   - "do not edit" also appears in hand-written files ("do not edit below this line"). This is the riskiest pattern, and the gold set
     result should decide whether to keep it.
   - Hand-edited generated files (wxGlade GUIs with user event handlers) are dropped with the generated part.
   - Django `settings.py` files ("Generated by 'django-admin startproject'") are not matched, on purpose. They are edited by people.

## Medicine 5: A2, control characters (Windows line endings)

1. **Disease:** A2, 17 documents. Every case is CRLF line endings: each U+000D CARRIAGE RETURN is followed by a line feed. There are no
   other control characters in the pack. Examples:
   - `9942b8de5559f733`: `25 U+000D CARRIAGE RETURN (64x)`
   - `badd30c95a3ad7a6`: `100 U+000D CARRIAGE RETURN (521x)`
   - `664280963ab849c1`: `66 U+000D CARRIAGE RETURN (1002x)`
2. **Medicine:** turn CRLF and lone CR into LF, then delete the other C0 and C1 controls. Keep TAB, LF and FORM FEED, which are valid
   Python whitespace.

   ```python
   CONTROL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]")

   def fix_controls(text):
       return CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
   ```
3. **Action:** fix.
4. **Harm test:** gold set: 0 / 142 changed. PASS. Proxies: 0 / 158, 0 / 2,052. On the pack: TP 17, FP 0, FN 0.
5. **Side effects:**
   - A raw control character inside a string literal that the program needs (a raw ESC byte) would be deleted. Escaped forms such as
     `"\033"` are plain text and are not touched.
   - A lone CR used on purpose (old Mac files) becomes a newline, which is the intended reading.

## Medicine 6: F2, benchmark leak (competitive-programming solutions)

1. **Disease:** F2, 8 documents: 6 LeetCode, 1 LintCode (the same problem as LeetCode 1400) and 1 AtCoder solution. LeetCode and
   AtCoder problems are used in code benchmarks (LiveCodeBench, APPS). None of the HumanEval function names occur in the pack.
   I did not check MBPP.
   Examples:
   - `6b059c428332c1f9`: `class Solution:` (LeetCode 99 Recover Binary Search Tree)
   - `856d9320195e84eb`: `class Solution:` (LeetCode 686 Repeated String Match)
   - `9942b8de5559f733`: AtCoder ABC149 E accepted submission (path `jp.atcoder/abc149/abc149_e/`)
2. **Medicine:** drop LeetCode or LintCode files that hold a `class Solution`, AtCoder or Codeforces files, and files that link to a
   problem page on these sites.

   ```python
   def is_benchmark_solution(doc):
       """doc is the pack row: its text, and its url (repo name and file path)."""
       text, p = doc["text"], doc["url"].lower()
       if re.search(r"leetcode|lintcode", p) and re.search(r"^class Solution\b", text, re.M):
           return True
       if re.search(r"atcoder|codeforces", p):
           return True
       return bool(re.search(r"https?://(?:www\.)?(?:leetcode\.com/problems|atcoder\.jp/contests|codeforces\.com/problemset)/", text))
   ```
3. **Action:** drop.
4. **Harm test:** gold set: 0 / 142 dropped. PASS. Proxies: 0 / 158, 0 / 2,052. On the pack: TP 8, FP 0, FN 0.
5. **Side effects:**
   - This rule finds possible leaks by source, not by content. It drops solutions to problems that are in no test set. It also misses
     benchmark problems copied without a path or link.
   - The proper medicine is an n-gram overlap check against the evaluation sets that we use. This rule is only a cheap first filter.
   - A repo named `leetcode` with non-solution code (for example `bismog/leetcode/.../thread_lock_ex1.py`) is kept, because it has no
     `class Solution`.

---

## Diseases found five times or fewer (no medicine)

| Code | Count | Documents |
|---|---|---|
| F1 personal data | 4 | email written as "x at domain" (1); phone number and WeChat ID (1); email hidden in an `echo` + `awk` recipe (1); client IP address inside a signed URL (1) |
| D1 wrong language label | 2 | Bazel `.bzl` (Starlark) files labelled `python` |
| E2 data blob | 1 | CRC32 lookup table, 80 % of the file |
| E3 secret | 1 | signed video URL with its `signature` token |
| E6 not code | 1 | Chinese notes and raw URLs saved as `readme.py` |
| H3 same content, other language | 1 | Chinese translation of the PyTorch "Neural Networks" tutorial (Sphinx `build/_downloads` copy) |

Upstream redaction removed almost all emails, names and keys (see M2), so F1 and E3 are rare.

## Checked and not found (count 0)

A1, A3 to A6, B1, B2, B5, C1 to C5, E5, F3, G1 to G4, H1, H2. D2 to D5 are about prose and do not apply to code. Comments and strings
in Portuguese, Chinese, Turkish and Russian are normal in code, and I did not label them. Notes:

- **A3 / E5:** the mojibake regex matched Portuguese `ção` in 4 files. That text is correct. A round-trip test (cp1252 / latin-1 / GBK
  back to UTF-8) found no real mojibake.
- **B1 / B2 / B4-style templates:** `&amp;`, `<li>`, `{{ var }}` appear only inside Python strings that build HTML or templates. That is
  correct code, not markup junk.
- **C2:** some files repeat one line many times, for example 54 times in a test harness. These lines are working code in different
  functions, so I did not label them.
- **C3:** after M1, every file tokenizes to the end. After all fixes, 20 files still do not compile. 19 of them are Python 2, which I
  give as a note, not a disease. The last one is the not-code `readme.py` (E6).
- **H1 / H2:** there are no exact duplicates. No pair reaches Jaccard 0.5 on 5-token shingles.
- **F3:** "payload", "exploit" and similar words come from networking and security tools. One file is a threat-intelligence decryptor
  for research. None is harmful content.

## Observations

- **Comments and strings in other human languages** (not a disease, ruling of 26 Oct): 39 of the 500 files (7.8 %) have
  letters outside ASCII. Chinese or Japanese 16, accented Latin (Portuguese, Spanish, Turkish and others) 12, Cyrillic 5,
  Greek letters 5, Korean 1. A file can count in two groups. I did not label them.
- **Proposed disease: markdown converted to comments** (ruling of 24 Oct): 1 file, `e94a64270a4b7631`, a Sphinx-gallery
  tutorial whose markdown headings became comments such as `# **...**`. It is already `drop` (H3). The rule that finds
  it: lines that match `^# (?:#{1,6} \S|\*\*[^*\n]+\*\*)` (multiline). One file is too few for a medicine.
