# Medicine sheet: code-go (TEJASKUMAR-REDDY-J)

Pack: `code-go`, 500 Go files from bigcode/starcoderdata. Six diseases were found more than five times:
B3 (247), E4 (76), B4 (45), E1 (40), H3 (38), F2 (7). One section each below.

**Rule format.** Each medicine is one self-contained Python snippet with a stable rule ID
(`DA-<code>-<number>`). It defines `medicine(doc)`. `doc` is one pack row (a dict with `text` and `url`).
The function returns `(action, text)`. `action` is `"keep"`, `"fix"` or `"drop"`, and `text` is the treated text.

**Run order.** The drop medicines run first (DA-E1-001, DA-H3-001, DA-F2-001), then the fixes
(DA-B4-001, DA-E4-001, DA-B3-001). H3 and F2 read the `url`
column of the pack, so they do not depend on the `<reponame>`/`<filename>` markers that B3 removes.

**Gold set used for the harm tests.** The Data A gold set for code-go is not in the repository yet (due Thu 29 Oct).
Until then the harm test runs on a stand-in built the same way the gold set is defined (DISEASES.md section 5):
the **171 documents of this pack that at least two of the three code-go readers marked `clean`**
(this sheet's labels, and the public `labels.csv` of the two other code-go readers, PRs #36 and #77).
1% of 171 is 1.7, so a medicine that changes or drops 2 or more gold documents fails.
The numbers will be rerun on the Data A gold set when it is published.

**All six together, on the 500 labelled rows.** Every one of the 163 rows labelled `clean` is left untouched.
Of the 254 `fix` rows, 239 are fixed. The other 15 are left as they are: 12 have only a short or misplaced licence
note (see Medicine 2), and 3 have a disease seen five times or fewer (A2, A6, E3), which has no medicine here.
Of the 83 `drop` rows, 77 are dropped, 5 are only fixed and 1 is kept. These 6 are:
- the F3 file, which needs a harm classifier, not a regex
- the two leaked-source files flagged for the lead
- one generated file with no header
- one C3 file
- one LeetCode file whose path does not name the site

## Medicine 1: `DA-B3-001`

1. **Disease:** B3, StarCoder metadata markers (ruling 1). Count: 247 of 500. Examples:
   - `2f6d4b8c8e3fcbd5`: `<reponame>polaris-slo-cloud/polaris-scheduler` at offset 0
   - `2bdf36ae14fd90fa`: `<gh_stars>1-10` at offset 0
   - `b0eed26ac2f6a1a7`: `<filename>utils/convert.go` at offset 0
2. **Medicine:** In this pack the markers only ever appear as one run at the very start of the file, followed by a
   newline: `<reponame>`, `<filename>` and `<gh_stars>`, each followed by its value. Remove that run and the newline.
   ```python
   RULE_ID = "DA-B3-001"
   import re
   MARKERS = re.compile(r"^(?:<(?:reponame|filename|gh_stars)>[^<\n]*)+\n?")

   def medicine(doc):
       t = MARKERS.sub("", doc["text"])
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix.
4. **Harm test:** 171 gold documents: 0 changed, 0 dropped (0.0%). **Pass.**
   On the pack it fires on 247 documents. That is all 247 labelled B3, and nothing else.
5. **Side effects:** A Go file whose first line is a real string that starts with `<filename>` would lose that line.
   No such file is in the pack. The rule only looks at the file start, so a marker in the middle of a file is missed.
   None was seen in the pack. The other StarCoder markers (`<issue_start>`, `<jupyter_...>`) are not in Go files
   and are not handled.

## Medicine 2: `DA-E4-001`

1. **Disease:** E4, licence text in the file header. Count: 76 of 500. Examples:
   - `2bdf36ae14fd90fa`: `Licensed under the Apache License` at offset 122
   - `3dc96675632ddcff`: `Licensed under the MIT License.` at offset 100
   - `83381a2f882bdce3`: `Permission is hereby granted, free of charge` at offset 95
2. **Medicine:** The header is the part of the file before the first `import`, `func`, `type`, `var` or `const` line.
   In the header, remove each comment block (a `/* ... */` block or a run of `//` lines) that has licence wording
   **and is at least four lines long**. Keep everything else: the package clause, build tags, package docs and
   generator notes. Short one- to three-line notes such as "Use of this source code is governed by a BSD-style
   license that can be found in the LICENSE file" are kept, because the harm test showed that removing them
   changes gold documents (see 4).
   ```python
   RULE_ID = "DA-E4-001"
   import re
   LICENCE = re.compile(r"Licensed under|Licensed to the Apache|Permission is hereby granted|Redistribution and use|"
                        r"Use of this source code is governed by|This source code is licensed under|"
                        r"released under the \w+ licen[cs]e|General Public License|Mozilla Public License", re.I)
   BLOCK = re.compile(r"/\*.*?\*/[ \t]*\n?|(?://[^\n]*\n)+", re.S)

   def medicine(doc):
       t = doc["text"]
       body = re.search(r"^(?:import|func|type|var|const)\b", t, re.M)
       end = body.start() if body else len(t)
       head = t[:end]
       new = BLOCK.sub(lambda m: "" if LICENCE.search(m.group()) and m.group().count("\n") >= 4 else m.group(), head)
       if new == head:
           return ("keep", t)
       return ("fix", new.lstrip("\n") + t[end:])
   ```
3. **Action:** fix.
4. **Harm test:** 171 gold documents: 1 changed (`18a278785cdf215a`, a vendored file that H3 drops first), 0 dropped
   (0.6%). **Pass.** A first version without the four-line minimum changed 3 gold documents (1.8%) and failed.
   The extra two were two-line "governed by a BSD/MIT-style license" notes that the other readers marked `clean`.
   On the pack it fires on 53 documents, all of them labelled E4.
5. **Side effects:** It leaves 23 labelled E4 files untouched: the short "governed by" notes, one licence placed in
   the middle of a file (offset 5695, `a1c8a3831a37b7e7`), and one copyright line with no licence text
   (`ab877ddc979bdd7d`). Removing the header also removes the copyright and licence notice that the licence asks
   to keep with the code. The licence of the source repository should be recorded in metadata before the text is
   removed. A licence block that sits right on top of the package doc comment, with no blank line between them,
   is one comment block, so the package doc goes with it.

## Medicine 3: `DA-B4-001`

1. **Disease:** B4, placeholders left by earlier PII cleaning (ruling 2). Count: 45 of 500. Examples:
   - `f08e1abfa9c2ebdc`: `<EMAIL>` at offset 138
   - `c05ecf8c28dd8d51`: `<NAME> <<EMAIL>>` at offset 20
   - `312d930b2b41cf89`: `<NAME> (<EMAIL>)` at offset 696
2. **Medicine:** Replace each of the four placeholders with a fixed neutral word, so that the model does not learn the
   `<NAME>` token and the Go string literals stay valid. `example.com` is a domain reserved for examples.
   ```python
   RULE_ID = "DA-B4-001"
   import re
   NEUTRAL = {"<NAME>": "AUTHOR", "<EMAIL>": "user@example.com", "<KEY>": "EXAMPLE_KEY", "<PASSWORD>": "EXAMPLE_PASSWORD"}
   PLACEHOLDER = re.compile("|".join(map(re.escape, NEUTRAL)))

   def medicine(doc):
       t = PLACEHOLDER.sub(lambda m: NEUTRAL[m.group()], doc["text"])
       return ("fix" if t != doc["text"] else "keep", t)
   ```
3. **Action:** fix. 9 of the B4 documents are labelled `drop` for other reasons. E1 and H3 drop 7 of them. The
   other 2 (F3 and C3) have no medicine here.
4. **Harm test:** 171 gold documents: 0 changed, 0 dropped (0.0%). **Pass.**
   On the pack it fires on 43 documents, all of them labelled B4.
5. **Side effects:** It cannot repair the code where the redaction broke it. Examples are a key placeholder inside a
   `fmt.Sprintf` format, or a placeholder spliced into a hex constant. Those files are labelled C3/drop, or carry a
   note in `labels.csv`. Two kinds of B4 are not handled. The PII pool swapped real IP addresses for other
   real-looking addresses (2 files), and the medicine cannot see that. A cobra template header has the words
   `NAME HERE <EMAIL ADDRESS>` (1 file), which is not one of the four placeholders. The neutral
   word turns a copyright line into "Copyright 2016 AUTHOR", which is still not the true author.

## Medicine 4: `DA-E1-001`

1. **Disease:** E1, generated code (ruling 3: only when the code itself is generated). Count: 40 of 500. Examples:
   - `3c4db0c3d41b7673`: `// Code generated by MockGen. DO NOT EDIT.` at offset 0
   - `637118880fa53f2f`: `// Code generated by protoc-gen-go. DO NOT EDIT.` at offset 38
   - `3dc96675632ddcff`: `Code generated by Microsoft (R) AutoRest Code Generator.` at offset 196
2. **Medicine:** In the first 1500 characters, find a **comment line** (starting with `//`, `/*` or `*`) that holds
   a generator note: "Code generated", "generated by", "auto-generated", "automatically generated", or the Chinese
   "自动生成". The note has to be in a comment. A generator program that *prints* this line from a Go string
   (`fmt.Fprintln(out, "// Code generated ...")`) is hand-written code and is kept.
   ```python
   RULE_ID = "DA-E1-001"
   import re
   GENERATED = re.compile(r"^[ \t]*(?://|/\*|\*)[^\n]*?(?:Code generated|generated by|auto-?generated|"
                          r"automatically generated|AutoRest Code Generator|自动生成)", re.I | re.M)

   def medicine(doc):
       return ("drop" if GENERATED.search(doc["text"][:1500]) else "keep", doc["text"])
   ```
3. **Action:** drop.
4. **Harm test:** 171 gold documents: 0 changed, 0 dropped (0.0%). **Pass.**
   On the pack it fires on 39 documents, all of them labelled E1. A first version that also matched string literals
   dropped one hand-written generator program (`5b33ed1435ccaccf`). The comment-line rule fixed that.
5. **Side effects:** It misses generated code that has no header. One generated SDK model file in the pack
   (`352589a9ac5405c4`) is recognisable only from its shape. Ruling 3 also covers the opposite case, a hand-written
   file that carries a "generated" header. That file would be dropped wrongly. None was seen in the pack.
   A comment such as "// the ID generated by the server" in the first 1500 characters would also match, so watch
   for this when the rule runs at scale.

## Medicine 5: `DA-H3-001`

1. **Disease:** H3, a vendored copy of another repository (the same code exists in its own repository). Count: 38
   of 500. Examples (from the `url` column):
   - `a976ed522ec7ab10`: `.../vendor/github.com/hashicorp/terraform/terraform/interpolate.go`
   - `2ca23804af7259a9`: `.../vendor/github.com/juruen/rmapi/filetree/treeutil.go`
   - `535f703c48d38087`: `.../vendor/github.com/aliyun/alibaba-cloud-sdk-go/services/...`
2. **Medicine:** Drop the file when its repository path has a `vendor/` folder. Go's `vendor/` holds copies of
   other modules.
   ```python
   RULE_ID = "DA-H3-001"
   import re

   def medicine(doc):
       return ("drop" if re.search(r"(?:^|/)vendor/", doc["url"]) else "keep", doc["text"])
   ```
3. **Action:** drop.
4. **Harm test:** 171 gold documents: 0 changed, **6 dropped (3.5%). Fail.** All six are vendored files that I
   labelled H3/drop and that both other readers labelled `clean`. The medicine matches the labels exactly
   (38 fired, the same 38 labelled). The failure is a disagreement between readers about whether a vendored copy is
   a disease. Question for the lead: should vendored copies be in the gold set? If they should, this medicine changes
   from "drop" to **exact deduplication**: drop a vendored file only when the same file exists in its own repository
   in the corpus. That keeps a vendored file whose original is missing.
5. **Side effects:** A project folder that is named `vendor/` but is not Go vendoring would be dropped. Vendored
   code that sits in other folders (`third_party/`, `external/`) is missed. Dropping a vendored file loses nothing
   only when the original repository is also in the corpus.

## Medicine 6: `DA-F2-001`

1. **Disease:** F2, solutions to competitive-programming problems (benchmark leak risk). Count: 7 of 500. Examples:
   - `b44b171be56ec0f4`: `leetcode/1-100/0020.Valid-Parentheses` at offset 10
   - `da27b96957304886`: `leetcode/solutions/0119.PascalsTriangleII` at offset 39
   - `c33cef44b04d2df4`: path `.../leetcode/solutions/__114_path_sum.go`
2. **Medicine:** Drop the file when the repository name or the path names LeetCode, Codeforces or AtCoder.
   Code benchmarks such as HumanEval and MBPP are built from problems like these.
   ```python
   RULE_ID = "DA-F2-001"
   import re
   CONTEST = re.compile(r"leetcode|codeforces|atcoder", re.I)

   def medicine(doc):
       return ("drop" if CONTEST.search(doc["url"]) else "keep", doc["text"])
   ```
3. **Action:** drop.
4. **Harm test:** 171 gold documents: 0 changed, 0 dropped (0.0%). **Pass.**
   On the pack it fires on 6 documents, all of them labelled F2.
5. **Side effects:** It misses repositories that name the site in another way (`egregors/leetgo`, 1 file) and
   problem files that have no site name in the path. It drops every solution from those sites, including problems
   that are not in any benchmark. For a final list, the benchmark problem IDs (HumanEval, MBPP, the
   LiveCodeBench/LeetCode sets) should be matched against the problem number in the path.
