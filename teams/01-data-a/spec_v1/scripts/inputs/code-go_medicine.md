# Medicine sheet: code-go (TEJASKUMAR-REDDY-J)

Pack: `code-go`, 500 Go files from bigcode/starcoderdata, all with `lang_label` = `go`.
This sheet has 13 medicines, one for every disease found in the pack that a rule can treat safely. Six diseases were
found more than five times (B3 247, E4 76, B4 45, E1 40, H3 38, F2 7), and the template asks for those. The others were
found one to three times, and they get a medicine too wherever a safe rule exists. Four codes have no rule; the
section at the end explains why. Three medicines use ideas from RaviNaik's code-go sheet (PR #36): E1, E4 and the
restrictive-licence check inside E4. Each of those sections says what was taken and what was left out.

**Format (Data A tools).** Each medicine is one section with a `**Disease:**` line, an `**Action:**` line and one
```` ```python ```` block. The block defines `medicine_<code>(doc)`, for example `medicine_b3`; helpers start with `_`.
`doc` is one pack row (`doc_id`, `text`, `url`, `lang_label`); the H3 and F2 medicines read `url`. The function returns
`(action, text)`, where `action` is `"keep"`, `"fix"` or `"drop"`. A fix only cuts or swaps the bad part and leaves the
rest of the code as it is. A drop removes the whole file. Rule IDs are given by the Data A extractor
(`teams/01-data-a/tools/medicine_extract.py`), not written here.

**Languages.** Every file in the pack is Go, and every medicine was tested on the Go gold set only. Each section has a
"Portable to" line for other languages; a medicine should run on another language only after it passes that
language's harm test. Rules that read Go syntax (comments, strings, the header, `vendor/`) need a new version there.

**Summary.** Harm test on the Data A gold set for code-go, 163 documents (see below). "Fires" counts the pack documents that
the rule changes or drops. "Labelled" counts how many of those carry that disease code in `labels.csv`, out of all
documents labelled with that code. The rules are listed in run order: the drop rules first, then the fix rules.

| # | Medicine | Disease | Action | Fires (pack) | Labelled / total | Gold changed | Gold dropped | Gold % | Harm test |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `medicine_e1` | E1 generated code | drop | 41 | 40 / 40 | 0 | 0 | 0.0% | PASS |
| 2 | `medicine_h3` | H3 vendored copy | drop | 38 | 38 / 38 | 0 | 0 | 0.0% | PASS (see note) |
| 3 | `medicine_f2` | F2 contest solution | drop | 6 | 6 / 7 | 0 | 0 | 0.0% | PASS |
| 4 | `medicine_e2` | E2 embedded binary blob | drop | 5 | 3 / 3 | 0 | 0 | 0.0% | PASS |
| 5 | `medicine_c3` | C3 file no longer parses | drop | 1 | 1 / 1 | 0 | 0 | 0.0% | PASS |
| 6 | `medicine_a2` | A2 control characters (CR) | fix | 1 | 1 / 1 | 0 | 0 | 0.0% | PASS |
| 7 | `medicine_b4` | B4 PII placeholders | fix | 43 | 43 / 45 | 0 | 0 | 0.0% | PASS |
| 8 | `medicine_e3` | E3 hard-coded secret | fix | 1 | 1 / 1 | 0 | 0 | 0.0% | PASS |
| 9 | `medicine_a6` | A6 Cyrillic look-alike letters | fix | 2 | 2 / 2 | 0 | 0 | 0.0% | PASS |
| 10 | `medicine_a4` | A4 lost bytes (U+FFFD), with E5 debris | fix | 1 | 1 / 1 | 0 | 0 | 0.0% | PASS |
| 11 | `medicine_c1` | C1 scaffold boilerplate | fix | 2 | 1 / 1 | 0 | 0 | 0.0% | PASS |
| 12 | `medicine_e4` | E4 licence header (strip 4+ lines; drop a restrictive licence) | fix | 56 | 56 / 76 | 0 | 0 | 0.0% | PASS |
| 13 | `medicine_b3` | B3 StarCoder markers | fix | 247 | 247 / 247 | 0 | 0 | 0.0% | PASS |

**Languages in the text (not a disease).** 47 files have comments or strings in a language other than English:
Chinese (39), Japanese (4), Portuguese (2), Korean (1) and Polish (1). All 47 were read in full. The text is natural
writing by native speakers: doc comments, error and log strings, e-mail templates, bot replies and menu titles.
There is no machine translation (D4) and no translationese (D5). Some English identifiers appear inside CJK comments,
which is normal in code and is not D3. The three human typos found are noted in `labels.csv` (ruling 11). No medicine
is needed for these languages, and every row in `labels.csv` is `read = full`.

**Gold set used for the harm tests.** The Data A interim gold set for code-go (28 Oct, 3:30 AM IST), built by
`teams/01-data-a/tools/build_gold.py` from the open diagnosis PRs: `teams/01-data-a/gold/code-go_gold.csv`,
**163 documents**, SHA-256 starting `81942db337e2e191`. A document is gold when two readers marked it
`read=full, verdict=clean` with no disease code, and no other reader marked it `fix` or `drop`.
- **Readers:** all 163 are agreed by RaviNaik and this sheet.
- **Excluded:** 171 documents had two clean votes, and 8 were left out because the third reader disagreed. These are
  6 vendored files (H3) and 2 files with a short licence note.
- **Limit:** 1% of 163 is 1.63, so a medicine that changes or drops 2 or more gold documents fails.
- **No padding:** the gold set is not padded with fixed files or single-reader files, because a fixed file would make
  the test circular.
- **Interim:** the set will be rebuilt when every reader finishes the 500 documents, and the numbers will be rerun on
  the new set.
- **Before the Data A set was published:** the test ran on a stand-in built the same way but without the dispute
  rule (171 documents). There, `medicine_h3` dropped the 6 vendored files (3.5%, FAIL) and the E4 licence rule changed 1 (0.6%).

**How the harm test is run (TSAI Lab answer, 27 Oct).** The test takes the pack, the gold file and one rule ID. It
runs that rule on every gold document and counts the documents it changes and the documents it drops. A rule passes
when changed + dropped is at most 1% of the gold set. A rule that does nothing would also pass, so each rule also
reports how many labelled sick rows it fixes (the "Labelled" column). Gold documents are never removed to make a rule
pass. This is the core of the test. The Data A tool reads this file directly (Linux or macOS; on Windows use WSL):
```
python -I teams/01-data-a/tools/harm_test.py --pack code-go.parquet --gold teams/01-data-a/gold/code-go_gold.csv --rules medicine.md --rule B3
python -I teams/01-data-a/tools/harm_test.py --pack code-go.parquet --gold teams/01-data-a/gold/code-go_gold.csv --rules medicine.md --rule all
```
```
def harm_test(gold_docs, medicine):
    changed = dropped = 0
    for d in gold_docs:
        action, text = medicine(d)
        if action == "drop":
            dropped += 1
        elif text != d["text"]:            # any exact text difference is a change (Spec v1, section 2)
            changed += 1
    if not gold_docs:
        return 0, 0, 0.0, "NOT_EVALUATED"
    pct = 100 * (changed + dropped) / len(gold_docs)   # each document counted once
    return changed, dropped, round(pct, 1), "PASS" if pct <= 1 else "FAIL"
```
The script also checks that each rule is idempotent: running it twice gives the same text as running it once. All 13
medicines are idempotent on the pack.

**All rules together, in run order, on the 500 labelled rows** (`--rule all`, the `ALL IN ORDER` line):
- **Clean rows:** all 163 rows labelled `clean` are left untouched, and so are all 163 gold documents.
- **Fix rows:** of the 254 rows labelled `fix`, 243 are fixed, 10 are kept and 1 is dropped. The 10 kept have only a
  short "governed by" licence note, which `medicine_e4` leaves on purpose. The one dropped is the restrictive-licence
  file (`medicine_e4`): `labels.csv` says fix, and this sheet now proposes drop for it.
- **Drop rows:** of the 83 rows labelled `drop`, 79 are dropped, 3 are only fixed and 1 is kept. The 3 are the F3 file
  (needs a harm classifier) and the two leaked-source files flagged for the lead (no rule can see a leak). The one
  kept is a LeetCode file whose path does not name the site.

## Medicine 1: E1 generated code

1. **Disease:** E1, generated code (ruling 3: only when the code itself is generated). Count: 40 of 500. Examples:
   - `3c4db0c3d41b7673`: `// Code generated by MockGen. DO NOT EDIT.` at offset 0
   - `637118880fa53f2f`: `// Code generated by protoc-gen-go. DO NOT EDIT.` at offset 38
   - `3dc96675632ddcff`: `Code generated by Microsoft (R) AutoRest Code Generator.` at offset 196
2. **Medicine:** In the first 1500 characters, find a **comment line** (starting with `//`, `/*` or `*`) that holds
   a generator note: "Code generated", "generated by", "auto-generated", "automatically generated", or the Chinese
   "自动生成". The note has to be in a comment. A generator program that *prints* this line from a Go string
   (`fmt.Fprintln(out, "// Code generated ...")`) is hand-written code and is kept.
   Two generators print no marker line, so they are found by a fingerprint in the first 3000 characters: Kiota's
   hashed import alias for `github.com/microsoft/kiota...`, and goformation's comment "Specification Version that
   this resource was generated from". Both fingerprints come from RaviNaik's code-go sheet (PR #36).
   ```python
   import re
   GENERATED = re.compile(r"^[ \t]*(?://|/\*|\*)[^\n]*?(?:Code generated|generated by|auto-?generated|"
                          r"automatically generated|AutoRest Code Generator|自动生成)", re.I | re.M)
   FINGERPRINT = re.compile(r"(?m)^\s*i[0-9a-f]{40,}\s+\"github\.com/microsoft/kiota|"
                            r"Specification Version that this resource was generated from")

   def medicine_e1(doc):
       t = doc["text"]
       return ("drop" if GENERATED.search(t[:1500]) or FINGERPRINT.search(t[:3000]) else "keep", t)
   ```
3. **Action:** drop. **Applies to:** `go`. **Portable to:** C, C++, Java, JavaScript/TypeScript, Rust and C#, which
   use the same comment markers. Python, Ruby and shell use `#` comments and need a new version.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.**
   On the pack it fires on 41 documents: all 40 labelled E1, and one goformation file labelled H3 (dropped anyway).
   A first version that also matched string literals dropped
   one hand-written generator program (`5b33ed1435ccaccf`). The comment-line rule fixed that.
5. **Side effects:** It misses generated code that has neither a header nor a known fingerprint. The earlier version
   of this medicine, which had no fingerprints, missed the Kiota file `352589a9ac5405c4`; this one catches it.
   RaviNaik's wider pattern also matches `83381a2f882bdce3`, a server stub that was edited by hand. That match is a
   false positive, so that part of the pattern was not taken. Ruling 3 also covers the opposite case, a hand-written
   file that carries a "generated" header. That file would be dropped wrongly. None was seen in the pack.
   A comment such as "// the ID generated by the server" in the first 1500 characters would also match, so watch for
   this when the rule runs at scale.

## Medicine 2: H3 vendored copy

1. **Disease:** H3, a vendored copy of another repository (the same code exists in its own repository). Count: 38
   of 500. Examples (from the `url` column):
   - `a976ed522ec7ab10`: `.../vendor/github.com/hashicorp/terraform/terraform/interpolate.go`
   - `2ca23804af7259a9`: `.../vendor/github.com/juruen/rmapi/filetree/treeutil.go`
   - `535f703c48d38087`: `.../vendor/github.com/aliyun/alibaba-cloud-sdk-go/services/...`
2. **Medicine:** Drop the file when its repository path has a `vendor/` folder. Go's `vendor/` holds copies of other
   modules.
   ```python
   import re

   def medicine_h3(doc):
       return ("drop" if re.search(r"(?:^|/)vendor/", doc["url"]) else "keep", doc["text"])
   ```
3. **Action:** drop. **Applies to:** `go`. **Portable to:** PHP (Composer also uses `vendor/`) and Ruby
   (`vendor/bundle`). JavaScript needs `node_modules/` instead.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS, with a note.** The medicine matches the
   labels exactly (38 fired, the same 38 labelled). The pass depends on the gold builder's dispute rule. Six vendored
   files have two `clean` votes (RaviNaik and udisinghania), but this sheet labelled them H3/drop, so the builder
   leaves them out of the gold set as disputed. If the team builds the gold set with `--allow-disputed` (two clean
   votes win), the rule drops those 6 (3.5%) and FAILS. So this is a disagreement between readers about whether a
   vendored copy is a disease. Under the 27 Oct answer, it should be settled by the lead, not by the rule.
   **Status: candidate, blocked on that decision.** The fallback route is **exact deduplication** at corpus level: drop a
   vendored file only when a byte-identical copy (the original in its own repository) is also in the corpus. That
   keeps every vendored file whose original is missing. It cannot be measured inside one pack: the pack has no exact
   duplicates, so the rule would fire on 0 documents here. Open question for the lead and the Data A lead.
5. **Side effects:** A project folder that is named `vendor/` but is not Go vendoring would be dropped. Vendored
   code that sits in other folders (`third_party/`, `external/`) is missed. Dropping a vendored file loses nothing
   only when the original repository is also in the corpus.

## Medicine 3: F2 contest solution

1. **Disease:** F2, solutions to competitive-programming problems (benchmark leak risk). Count: 7 of 500. Examples:
   - `b44b171be56ec0f4`: `leetcode/1-100/0020.Valid-Parentheses` at offset 10
   - `da27b96957304886`: `leetcode/solutions/0119.PascalsTriangleII` at offset 39
   - `c33cef44b04d2df4`: path `.../leetcode/solutions/__114_path_sum.go`
2. **Medicine:** Drop the file when the repository name or the path names LeetCode, Codeforces or AtCoder.
   Code benchmarks such as HumanEval, MBPP and LiveCodeBench are built from problems like these.
   ```python
   import re
   CONTEST = re.compile(r"leetcode|codeforces|atcoder", re.I)

   def medicine_f2(doc):
       return ("drop" if CONTEST.search(doc["url"]) else "keep", doc["text"])
   ```
3. **Action:** drop. **Applies to:** `go`. **Portable to:** all programming languages. It reads only the path,
   so the code is the same for every language. Each language still needs its own harm test before it is used
   there.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.**
   On the pack it fires on 6 documents, all labelled F2.
5. **Side effects:** It misses repositories that name the site in another way (`egregors/leetgo`, 1 file) and
   problem files that have no site name in the path. It drops every solution from those sites, including problems
   that are not in any benchmark. For a final list, the benchmark problem IDs should be matched against the problem
   number in the path.

## Medicine 4: E2 embedded binary blob

1. **Disease:** E2, a large binary blob embedded in the source as a byte array. Count: 3 of 500. Examples:
   - `637118880fa53f2f`: `0x1f, 0x8b, 0x08` at offset 5772 (a gzipped protobuf descriptor)
   - `91bf17319ac11223`: `file_dictybase_api_jsonapi_request_proto_rawDesc = []byte{` at offset 23934
   - `e673cf85cd68c71d`: `0x1f, 0x8b, 0x08` at offset 24790
2. **Medicine:** Drop the file when it holds 300 or more two-digit hex byte literals (`0x1f,`). A table of 256 bytes,
   such as a CRC or S-box table, stays below the limit. A file with more is mostly data, not code.
   ```python
   import re
   BYTE = re.compile(r"0x[0-9a-fA-F]{2}\s*,")

   def medicine_e2(doc):
       return ("drop" if len(BYTE.findall(doc["text"])) >= 300 else "keep", doc["text"])
   ```
3. **Action:** drop. **Applies to:** `go`. **Portable to:** C, C++, Rust, Java and C#, which write byte arrays the
   same way.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.**
   On the pack it fires on 5 documents: the 3 labelled E2, and 2 more protobuf outputs with the same descriptor
   arrays (`dd9421d5a42adf64`, `8c1931d1524ec642`). Those two are labelled E1 and are dropped by `medicine_e1` anyway.
5. **Side effects:** A hand-written file with a large lookup table (more than 300 bytes) would be dropped. A blob
   written as a string (`"\x1f\x8b..."`) or in base64 is missed.

## Medicine 5: C3 file no longer parses

1. **Disease:** C3, a file that is no longer valid code. Count: 1 of 500. Example:
   - `a27e1273db746e7d`: `key := fmt.Sprintf("<KEY>` at offset 8404. The PII redaction cut the rest of the line,
     so the string is never closed and the file no longer parses.
2. **Medicine:** Run a small Go lexical check. Skip comments, strings (`"..."`, `` `...` ``) and runes (`'...'`), and
   count brackets. The file fails when a string, rune or block comment is not closed, when a `"` string runs into a
   newline, or when the brackets do not balance. A failed file is dropped.
   ```python

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
   ```
3. **Action:** drop. **Applies to:** `go`. **Portable to:** none as it is. Every language has its own string and
   comment syntax, so each needs its own check. The best version for Go is the real parser (`gofmt -e` or `go/parser`).
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.**
   On the pack it fires on 1 document, the one labelled C3. The other 499 files pass the check.
5. **Side effects:** It is a lexical check, not a full parser, so code with valid brackets but broken grammar is
   missed. A file cut off by a size limit in the middle of a function fails the check and is dropped, which is
   correct for training.

## Medicine 6: A2 control characters

1. **Disease:** A2, invisible control characters. Count: 1 of 500. Example:
   - `34133f5414afff81`: 409 carriage returns (U+000D), the first at offset 2, from Windows CRLF line endings
2. **Medicine:** Turn CRLF and lone CR into LF, and delete the other C0 control characters and DEL. Keep tab (U+0009),
   newline (U+000A) and form feed (U+000C), which source code uses.
   ```python
   import re
   CTRL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")

   def medicine_a2(doc):
       t = CTRL.sub("", doc["text"].replace("\r\n", "\n").replace("\r", "\n"))
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix. **Applies to:** `go`. **Portable to:** all programming languages. Raw control characters in
   source are almost always line-ending debris. A language must pass its own harm test first, because some code has
   raw escape characters inside string literals.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.** On the pack it fires on 1 document,
   the one labelled A2.
5. **Side effects:** A raw control character that the code needs (for example a literal ESC byte inside a Go
   string) is deleted. None was seen in the pack. Go source should write `\x1b` instead.

## Medicine 7: B4 PII placeholders

1. **Disease:** B4, placeholders left by earlier PII cleaning (ruling 2). Count: 45 of 500. Examples:
   - `f08e1abfa9c2ebdc`: `<EMAIL>` at offset 138
   - `c05ecf8c28dd8d51`: `<NAME> <<EMAIL>>` at offset 20
   - `312d930b2b41cf89`: `<NAME> (<EMAIL>)` at offset 696
2. **Medicine:** Replace each of the four placeholders with a fixed neutral word, so that the model does not learn the
   `<NAME>` token and the Go string literals stay valid. `example.com` is a domain reserved for examples.
   ```python
   import re
   NEUTRAL = {"<NAME>": "AUTHOR", "<EMAIL>": "user@example.com", "<KEY>": "EXAMPLE_KEY", "<PASSWORD>": "EXAMPLE_PASSWORD"}
   PLACEHOLDER = re.compile("|".join(map(re.escape, NEUTRAL)))

   def medicine_b4(doc):
       t = PLACEHOLDER.sub(lambda m: NEUTRAL[m.group()], doc["text"])
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix. **Applies to:** `go`. **Portable to:** every StarCoder language, since the same PII pass made
   the placeholders. 9 of the B4 documents are labelled `drop` for other reasons and are dropped by the drop rules
   (E1, H3, C3), except the F3 file.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.**
   On the pack it fires on 43 documents, all labelled B4.
5. **Side effects:** It cannot repair code that the redaction broke (`medicine_c3` drops that file). Two kinds of B4
   are not handled. The PII pool swapped real IP addresses for other real-looking addresses (2 files), and the medicine
   cannot see that. A cobra template header has the words `NAME HERE <EMAIL ADDRESS>` (1 file), which is not one of
   the four placeholders. The neutral word turns a copyright line into "Copyright 2016 AUTHOR", which is still not
   the true author.

## Medicine 8: E3 hard-coded secret

1. **Disease:** E3, a hard-coded secret. Count: 1 of 500. Example (type and position only, never the value):
   - `98e4c493f32c8bfa`: TOTP secret seed (base32, 64 characters) in a string constant at offset 87
2. **Medicine:** Replace secrets with the word `EXAMPLE_SECRET`. Two kinds are covered. The first is well-known key
   formats: AWS access key, GitHub token, `sk-` API key, Slack token and PEM private key. The second is a base32 string
   of 16 or more characters assigned to a name that contains `secret`, `seed`, `totp` or `otp`. The code still
   compiles, because only the string content changes.
   ```python
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
   ```
3. **Action:** fix. **Applies to:** `go`. **Portable to:** all programming languages for the key formats. The `:=`
   and `=` assignment pattern fits Go, Python, JavaScript and most C-family languages.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.** On the pack it fires on 1 document,
   the one labelled E3.
5. **Side effects:** Secrets with no known format and no telling variable name are missed. A full secret scanner
   (gitleaks or trufflehog rules) should run at scale. A public test vector (for example the RFC 6238 TOTP seed in a
   test) would be replaced too, which breaks that test.

## Medicine 9: A6 Cyrillic look-alike letters

1. **Disease:** A6, Cyrillic look-alike letters inside Latin words. Count: 2 of 500. Examples:
   - `64ed179e7e5c3d21`: `intс` at offset 1324, where the last letter is Cyrillic с (U+0441), in a command name
   - `48b3b124a7aaa5fc`: Cyrillic а (U+0430) and о (U+043E) inside a Latin word at offset 61 (type and position only:
     the word is part of personal data, F1)
2. **Medicine:** Find words that mix Latin letters with Cyrillic letters, and map the Cyrillic look-alikes in those
   words to their Latin twins (а→a, е→e, о→o, р→p, с→c, у→y, х→x, and the capitals). Words that are fully Cyrillic,
   such as Russian comments, are not touched.
   ```python
   import re
   HOMO = str.maketrans("аеорсухіјѕАВЕКМНОРСТХІЈЅ", "aeopcyxijsABEKMHOPCTXIJS")
   MIXED = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*[Ѐ-ӿ])\w+\b")

   def medicine_a6(doc):
       t = MIXED.sub(lambda m: m.group().translate(HOMO), doc["text"])
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix. **Applies to:** `go`. **Portable to:** all programming languages. Greek look-alikes (ο, α) can
   be added the same way.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.** On the pack it fires on 2 documents,
   both labelled A6.
5. **Side effects:** In `48b3b124a7aaa5fc`, the look-alike letters were hiding a personal e-mail address from the
   earlier PII pass. The fix turns it back into a plain address, so **the PII pass must run again after this rule**.
   That is a benefit, because the address can then be redacted (F1). A real mixed word, such as a transliteration with
   one Cyrillic letter on purpose, would be changed. None was seen in the pack.

## Medicine 10: A4 lost bytes (U+FFFD)

1. **Disease:** A4, lost bytes shown as U+FFFD. Count: 1 of 500, plus the E5 debris next to them. Example:
   - `2a92a9a8489c5ea2`: `// ��ȸ` at offset 17258, a comment that holds only two U+FFFD and one leftover letter
     (U+0238, E5)
   - Not a case: `1dbf03039c9ea15c` has `// Replacement character �.` at offset 2384. The author quotes the character
     on purpose, so it is content, not A4 (ruling 7), and the rule must keep it.
2. **Medicine:** Delete a `//` comment that holds U+FFFD and no ASCII letter or digit. Such a comment is only
   debris. A comment that has real words around the U+FFFD, like the quoted one, is kept (ruling 7). The code itself
   is never touched.
   ```python
   import re
   LOST = re.compile(r"[ \t]*//[^\n\w]*�[^\nA-Za-z0-9]*$", re.M)

   def medicine_a4(doc):
       t = LOST.sub("", doc["text"])
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix. **Applies to:** `go`. **Portable to:** C-family languages with `//` comments. Python and shell
   need the `#` form.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.** On the pack it fires on 1 document,
   the labelled A4/E5 file. The author-quoted U+FFFD file is not touched.
5. **Side effects:** U+FFFD inside a string literal, or inside a comment with words, is not repaired. The lost
   original bytes cannot be recovered, so the rule removes the debris but cannot restore the text.

## Medicine 11: C1 scaffold boilerplate

1. **Disease:** C1, template boilerplate left from a code generator's scaffold. Count: 1 of 500 labelled. Examples:
   - `45ac5026eac81b39`: `EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!` at offset 628
   - `45ac5026eac81b39`: `NOTE: json tags are required.` at offset 684
   - `fd10104d4b8b5721`: `NOTE: json tags are required.` at offset 664 (the same kubebuilder note, not labelled C1)
2. **Medicine:** Delete the kubebuilder and operator-sdk scaffold notes. These are `//` comment lines with fixed
   wording that the tool writes into every new API type. Real doc comments are kept.
   ```python
   import re
   SCAFFOLD = re.compile(r'^[ \t]*//[ \t]*(?:EDIT THIS FILE!.*|NOTE: json tags are required\..*|'
                         r'Important: Run "make" to regenerate code after modifying this file.*|'
                         r'INSERT ADDITIONAL (?:SPEC|STATUS) FIELDS?.*)\n', re.M)

   def medicine_c1(doc):
       t = SCAFFOLD.sub("", doc["text"])
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix. **Applies to:** `go`. **Portable to:** none. The scaffold is Go-only (kubebuilder and
   operator-sdk).
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.** On the pack it fires on 2 documents:
   the one labelled C1, and `fd10104d4b8b5721`, which has the same scaffold note but was labelled for its licence
   only. That second file is a missed C1 label, not harm.
5. **Side effects:** A developer who copies one of these lines into their own comment loses it. Other generators'
   scaffold notes are not covered.

## Medicine 12: E4 licence header

1. **Disease:** E4, licence text in the file header. Count: 76 of 500. Examples:
   - `2bdf36ae14fd90fa`: `Licensed under the Apache License` at offset 122
   - `3dc96675632ddcff`: `Licensed under the MIT License.` at offset 100
   - `83381a2f882bdce3`: `Permission is hereby granted, free of charge` at offset 95
2. **Medicine:** First, if the first 60 lines hold a restrictive licence phrase ("free for personal use", "commercial
   use requires", "non-commercial use only", "Commons Clause", "not for commercial use", "for evaluation purposes
   only"), drop the file: removing the header would not make the code free to use (phrase list from RaviNaik's sheet,
   PR #36; 1 file in the pack, `ab877ddc979bdd7d`). Otherwise the header is the part of the file before the first `import`, `func`, `type`, `var` or `const` line.
   In the header, remove each comment block (a `/* ... */` block or a run of `//` lines) that has licence wording
   **and is at least four lines long**. Keep everything else: the package clause, build tags, package docs and
   generator notes. Short one- to three-line notes such as "Use of this source code is governed by a BSD-style
   license that can be found in the LICENSE file" are kept, because the harm test showed that removing them changes
   gold documents (see 4).
   Two more shapes are handled, both seen in RaviNaik's code-go sheet (PR #36). The first is a "boxed" header made of
   one-line `/* ... */` comments, one per line. The second is the same licence block placed at the very end of the
   file, after the code.
   ```python
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
   ```
3. **Action:** fix (drop for a restrictive licence). **Applies to:** `go`. **Portable to:** C-family languages after a new header rule (the first
   `import`/`func` line is Go syntax). The licence wording list works for every language.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.** A first version without the four-line
   minimum also removed two-line "governed by a BSD/MIT-style license" notes. On the stand-in set it changed 3
   documents (1.8%) and failed, so the four-line minimum was added.
   On the pack it fires on 55 documents, all labelled E4.
5. **Side effects:** It leaves the short "governed by" notes untouched, on purpose (see 4). The earlier version
   of this medicine also missed the boxed header in `24a7be0ee133443b` and the licence at the end of `a1c8a3831a37b7e7`
   (offset 5695); this one removes both. The restrictive licence in `ab877ddc979bdd7d` is dropped (see 2). Removing the header also removes the copyright and licence notice that the licence asks to
   keep with the code. The licence of the source repository should be recorded in metadata before the text is
   removed. A licence block that sits right on top of the package doc comment, with no blank line between them, is
   one comment block, so the package doc goes with it.

## Medicine 13: B3 StarCoder markers

1. **Disease:** B3, StarCoder metadata markers (ruling 1). Count: 247 of 500. Examples:
   - `2f6d4b8c8e3fcbd5`: `<reponame>polaris-slo-cloud/polaris-scheduler` at offset 0
   - `2bdf36ae14fd90fa`: `<gh_stars>1-10` at offset 0
   - `b0eed26ac2f6a1a7`: `<filename>utils/convert.go` at offset 0
2. **Medicine:** In this pack the markers only ever appear as one run at the very start of the file, followed by a
   newline: `<reponame>`, `<filename>` and `<gh_stars>`, each followed by its value. Remove that run and the newline.
   It runs last, after the other rules, which read the `url` column and do not need the markers.
   ```python
   import re
   MARKERS = re.compile(r"^(?:<(?:reponame|filename|gh_stars)>[^<\n]*)+\n?")

   def medicine_b3(doc):
       t = MARKERS.sub("", doc["text"])
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix. **Applies to:** `go`. **Portable to:** every StarCoder language, since the markers come from the
   dataset, not from the code.
4. **Harm test:** 163 gold documents: 0 changed, 0 dropped (0.0%). **PASS.**
   On the pack it fires on 247 documents, which are all 247 labelled B3 and nothing else.
5. **Side effects:** A file whose first line is a real string that starts with `<filename>` would lose that line.
   None is in the pack. A marker in the middle of a file is missed, and none was seen. The other StarCoder markers
   (`<issue_start>`, `<jupyter_...>`) are not in Go files and are not handled.

## Diseases with no medicine

| Code | Count | Why there is no rule |
|---|---|---|
| B1 HTML entity | 1 | The one file (`&#x27;` in a Swagger client) is dropped by `medicine_e1`. Unescaping HTML entities in Go would harm good files: HTML e-mail templates in Go strings use `&nbsp;` correctly (`labels.csv` row for the CloudIaC templates). |
| D3 mixed language | 1 | Ruling: label it, do not judge it. German debug strings in English code are natural. The file is dropped by `medicine_h3`. |
| F1 personal data | 2 | An obfuscated e-mail address and a personal website next to a redacted name. A regex cannot find personal data safely. `medicine_a6` turns the obfuscated address back into plain text, so the PII pass should run again after the rules. |
| F3 harmful content | 1 | A working ransomware config. Harm needs a content classifier, not a pattern. The file must be dropped by hand or by the safety classifier. |
| E5 encoding debris | 1 | Covered by `medicine_a4`. The debris letter sits in the same lost-bytes comment. |
