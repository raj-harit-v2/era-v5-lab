# Medicine sheet: code-python (f20201351h-maker)

One section for each disease found more than five times. Code for every rule: `work/medicines.py`. Harm-test runner: `python -I work/medicines.py code-python.parquet work/labels.csv`.

**Harm-test gold set (official):** Team 01's code-python gold set, `teams/01-data-a/gold/code-python_gold.csv` on branch `g1-harm-test` of `patilvijay23/era-v5-lab` (PR #140), 46 documents. All 46 doc IDs are in this pack, and all 46 are labelled `clean` in this `labels.csv`. All 5 medicines change 0 of 46 and drop 0 of 46 (0.00%): PASS. Re-run: `python -I work/medicines.py code-python.parquet work/labels.csv --gold code-python_gold_ids.txt` (the 46 doc IDs from that file).

**Additional provisional gold set:** harm test also run on 157 code-python documents that two independent readers both marked `clean`. The second reader read blind, without the first labels, on 247 docs: raw agreement 96.8% on verdicts (239/247) and 94.3% on exact codes. After both sides get the same deterministic B3/E4 rules it is 98.0% and 97.6%. All remaining differences are documented judgement calls. The ids are in `work/review2/gold_two_readers.csv` (`doc_id,reader_1,reader_2`). Both readers were AI-assisted, so a human second reader should confirm before the gold set is final. Re-run: `python -I work/medicines.py code-python.parquet work/labels.csv --gold work/review2/gold_two_readers.txt`.

Diseases at five cases or fewer, so no medicine: E3 (4), F1 (3), D1 (2), E2 (2), C2 (1), E6 (1).

## Medicine 1: StarCoder metadata prefix (B3)

1. **Disease:** B3, 272 of 500 docs. Dataset metadata tokens `<reponame>`, `<filename>` and `<gh_stars>` (with their values) sit at offset 0, before the file content. Examples: `0d1e11b4c0740741` (`<gh_stars>`), `5e467bb5ce89997f` (`<reponame>`), `680d4363d4d1bd8e` (`<gh_stars>`).
2. **Medicine:** remove the prefix only when it is at the very start of the text.
   ```python
   META_PREFIX = re.compile(r"^(?:<(?:reponame|filename|gh_stars)>[^<\n]*)+\n?")
   text = META_PREFIX.sub("", text, count=1)
   ```
3. **Action:** fix.
4. **Harm test:** official gold set: changes 0 of 46 and drops 0 of 46 (0.00%). PASS. Provisional gold set: changes 0 of 157 and drops 0 (0.00%). PASS.
5. **Side effects:** none seen. The rule is anchored at `^` with `count=1`, so code that mentions `<reponame>` later in the file stays untouched. If a repo name contains `<`, part of the value stays behind. No such case is in the pack.

## Medicine 2: StarCoder PII placeholders (B3, proposed)

1. **Disease:** B3 (code to confirm in CAP), 83 of 500 docs. StarCoder's earlier PII redaction left the tokens `<NAME>` (55 docs), `<EMAIL>` (42), `<PASSWORD>` (16) and `<KEY>` (3). In 7 docs the placeholder breaks the Python syntax, for example `password=<PASSWORD>`. In others it changes what the code means while it still parses: an f-string `{password}` became `<PASSWORD>}`, and `'\x00'` became `'\<PASSWORD>'`. Examples: `a4d94c8acbe837d1` (`<PASSWORD>` ×3 at offset 159), `6a0b23e505a31093` (`<NAME>` at 177), `f3abd9691b48873d` (`<NAME>` at 62, `<EMAIL>` at 70). Syntax broken: `9e00aaaeab42bd57`, `717461624ebd2d57`, `b503269e161cf0ee`.
2. **Medicine:** if the file does not parse with the placeholders but does parse when they are replaced with `X`, drop it. Otherwise replace each placeholder with neutral text: `<EMAIL>` → `user@example.com`, `<NAME>` → `NAME`, `<PASSWORD>` → `PASSWORD`, `<KEY>` → `KEY`.
   ```python
   PLACEHOLDER = re.compile(r"<(NAME|EMAIL|PASSWORD|KEY|IP_ADDRESS|USERNAME)>")
   def fix_pii_placeholders(text):
       if not PLACEHOLDER.search(text): return text
       code = META_PREFIX.sub("", text, count=1)
       if not parses(code) and parses(PLACEHOLDER.sub("X", code)): return None   # drop
       return PLACEHOLDER.sub(lambda m: NEUTRAL[m.group(1)], text)
   ```
3. **Action:** fix (76 docs) or drop (7 docs).
4. **Harm test:** official gold set: changes 0 of 46 and drops 0 of 46 (0.00%). PASS. Provisional gold set: changes 0 of 157 and drops 0 (0.00%). PASS.
5. **Side effects:**
   - Code that really uses `<NAME>` or `<KEY>` as a literal, such as an XML or template string, would be rewritten. No such case was seen in this pack.
   - The neutral values cannot restore what the code meant: a test that compared a password now compares `PASSWORD`.
   - Partial redaction (a token where only half was replaced) is not detected here.

## Medicine 3: repeated licence header (E4)

1. **Disease:** E4, 75 of 500 docs. The licence header at the top of the module (comments and docstrings before the first statement) belongs to a licence family that appears in 2 or more files of the pack: Apache-2.0 45, MIT 16, BSD 6, GPL 6, LGPL 2. A short SPDX tag alone is not E4. Examples: `5e467bb5ce89997f` (27-line BSD at offset 51), `cc46017245578753` (10-line Apache-2.0 at offset 12), `f9df26b206182539` (11-line Apache-2.0 at offset 82).
2. **Medicine:** when the module starts with a `#` comment block that holds licence text, and that licence family repeats in the corpus, remove the block. Keep the shebang and `coding:` lines. Family detection reads only the header, never the code below it, and uses fixed phrases ("Apache License, Version 2.0", "Permission is hereby granted, free of charge", "Redistribution and use in source and binary forms", GNU GPL/LGPL, MPL), with a normalised text hash as the fallback.
   ```python
   def strip_repeated_licence(body, repeated_families):
       family = licence_family(body)                      # header text only
       if not family or family not in repeated_families:  # licence must repeat in the corpus
           return body
       lines, i = body.split("
"), 0
       while i < len(lines) and (lines[i].strip().startswith("#") or not lines[i].strip()):
           i += 1
       if i == 0 or not LICENCE.search("
".join(lines[:i])):  # licence is not in this comment block
           return body
       keep = [l for l in lines[:i] if l.startswith("#!") or re.match(r"#.*coding[:=]", l)]
       return "
".join(keep + lines[i:])
   ```
3. **Action:** fix.
4. **Harm test:** official gold set: changes 0 of 46 and drops 0 of 46 (0.00%). PASS. Provisional gold set: changes 0 of 157 and drops 0 (0.00%). PASS. It changes 69 of the 75 labelled docs.
5. **Side effects:**
   - 6 labelled docs carry their licence in a module docstring, or below an empty docstring, and the rule leaves those alone.
   - The rule also removes other comments that sit inside the same leading block (author notes, module description).
   - Removing licence notices has legal weight: TSAI should decide whether to keep one short SPDX line (`# SPDX-License-Identifier: Apache-2.0`) in place of the full text.
   - 8 of these files are copyleft (GPL/LGPL). For the commercial-use rule they may need to be dropped, not fixed; see the G10 licence table.

## Medicine 4: carriage returns, CRLF line endings (A2)

1. **Disease:** A2, 17 of 500 docs. U+000D before every newline (Windows line endings). Examples: `9942b8de5559f733` (`25 U+000D CARRIAGE RETURN (64x)`), `951c0ffae8ed4db6` (`84 U+000D CARRIAGE RETURN (37x)`), `aa4812f89a7ce665` (`50 U+000D CARRIAGE RETURN (31x)`).
2. **Medicine:** `text.replace("\r\n", "\n").replace("\r", "\n")`
3. **Action:** fix.
4. **Harm test:** official gold set: changes 0 of 46 and drops 0 of 46 (0.00%). PASS. Provisional gold set: changes 0 of 157 and drops 0 (0.00%). PASS.
5. **Side effects:** a `\r` inside a string literal (raw bytes, a terminal progress bar) changes meaning. The rule only sees real CR characters, not the two-character `\r` escape in source, so ordinary code keeps working.

## Medicine 5: generated code (E1)

1. **Disease:** E1, 12 of 500 docs. Django migrations ("Generated by Django"), Pulumi or tfgen SDKs ("Do not edit by hand"), AutoRest and KBase compiler output. Examples: `fcab84d53c43cbf9` (`Generated by Django 3.1.2` at offset 2), `6359488cb66a0aa6` (`Do not edit by hand` at offset 177), `ba0e6a6503f190e9` (`fuzza autogenerated.` at offset 31).
2. **Medicine:** drop when the first 1,000 characters match `auto-?generated | do not edit | do not modify | code generated by | generated by (protoc | protocol buffer compiler | django | autorest | swagger | openapi)`.
3. **Action:** drop.
4. **Harm test:** official gold set: changes 0 of 46 and drops 0 of 46 (0.00%). PASS. Provisional gold set: changes 0 of 157 and drops 0 (0.00%). PASS. It catches all 12 labelled docs.
5. **Side effects:**
   - By design, E1 needs a marker: migrations with no "Generated by" line (`976c938814ff2e53`, `aa4812f89a7ce665`) stay as fix, not drop.
   - A hand-written file that says "do not edit this section" near the top would be dropped by mistake.
   - Django migrations are generated but short and correct, so TSAI may prefer to keep them and down-weight them.
