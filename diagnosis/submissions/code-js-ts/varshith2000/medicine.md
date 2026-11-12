# Medicine sheet: code-js-ts (varshith2000)

This sheet is based on all 500 labelled documents in `labels.csv`. Counts below are
document counts, not occurrence counts. Personal data and secret values are never
copied here; E3 evidence is described only by type and offset.

## Harm-test status

Tested on the official JavaScript/TypeScript gold set (`teams/01-data-a/gold/code-js-ts_gold.csv`,
204 documents) using `teams/01-data-a/tools/harm_test.py` with the pack
`code-js-ts.parquet` (`code sha256: d01713313bd38d23cf026f4a9e76bd5535de1ee015724bf4a3620dc656b4e7fd`).
A medicine passes if it changes or drops at most `max(1, floor(1% of 204))` = 2
gold documents. All seven rules pass individually and in order:

| Rule | Disease | Gold set | Changed | Dropped | Percent | Limit | Result |
|---|---|---:|---:|---:|---:|---:|---|
| Medicine 1 | B2 | 204 | 0 | 0 | 0.00% | 2 | **PASS** |
| Medicine 2 | D3 | 204 | 0 | 0 | 0.00% | 2 | **PASS** |
| Medicine 3 | B4 | 204 | 0 | 0 | 0.00% | 2 | **PASS** |
| Medicine 4 | E1 | 204 | 0 | 0 | 0.00% | 2 | **PASS** |
| Medicine 5 | A2 | 204 | 0 | 0 | 0.00% | 2 | **PASS** |
| Medicine 6 | E3 | 204 | 0 | 1 | 0.49% | 2 | **PASS** |
| Medicine 7 | E4 | 204 | 0 | 0 | 0.00% | 2 | **PASS** |
| **ALL IN ORDER** | — | 204 | 0 | 1 | 0.49% | 2 | **PASS** |

## Medicine 1 — B2 source metadata leakage

1. **Disease:** B2, 244 documents. Examples: `c38890881e99e48e` (`<filename>` at
   offset 0 and `<gh_stars>` at offset 34), `c09dabc135210035` (`<reponame>` at
   offset 0), `7ffff923de0354f6` (`<reponame>` at offset 0 and `<filename>` at
   offset 76).
2. **Medicine:** Remove only leading dataset metadata fields `<reponame>...`,
   `<filename>...`, and `<gh_stars>...`. Do not remove ordinary JSX/HTML tags or
   TypeScript generic syntax.

   ```python
   import re

   SOURCE_META = re.compile(
       r"\A(?:<(?:reponame|filename|gh_stars)>[^\r\n]*)+(?:\r?\n)?"
   )

   def remove_source_metadata(text):
       return SOURCE_META.sub("", text, count=1)
   ```
3. **Action:** Fix the text by removing the metadata prefix. Drop only when B2 is
   part of a generated artifact that independently meets the E1 rule.
4. **Harm test:** Tested on `teams/01-data-a/gold/code-js-ts_gold.csv` (204 gold
   documents): 0 documents changed, 0 documents dropped (0.00% of the gold set;
   limit 2 documents / 1%). **PASS**.
5. **Side effects:** A broad tag-removal regex would damage JSX, HTML template
   strings, XML-like examples, and TypeScript generics. The rule must be anchored at
   the document start and limited to the three dataset fields.

## Medicine 2 — D3 mixed-language code text

1. **Disease:** D3, 27 documents. Examples: `e2deacf4ecd2030b` (Chinese comments),
   `d5c3a1b4e003ed61` (Spanish UI strings), `0d3bff117f465b99` (Persian UI strings).
2. **Medicine:** No automatic translation or language normalization. Record the
   language in review metadata while preserving valid identifiers, comments, strings,
   and UI text.

   ```python
   def preserve_mixed_language(text):
       return text
   ```
3. **Action:** Fix: keep the code unchanged (no-op). D3 is informational when the
   text is natural multilingual code content.
4. **Harm test:** Tested on `teams/01-data-a/gold/code-js-ts_gold.csv` (204 gold
   documents): 0 documents changed, 0 documents dropped (0.00% of the gold set;
   limit 2 documents / 1%). **PASS**.
5. **Side effects:** Translation can corrupt identifiers, user-facing wording,
   comments, and tests. It can also incorrectly label natural multilingual software
   as defective.

## Medicine 3 — B4 template and scrubber junk

1. **Disease:** B4, 25 documents. Examples: `cc42702a51d8a8ee` (`<question>` and
   `<KEY>` placeholders), `ec27a58ce8941db1` (`<EMAIL>` placeholders),
   `a2c50d532fb9d07a` (`<PASSWORD>` inserted into UI hint text).
2. **Medicine:** Treat placeholders as junk only when they are demonstrably injected
   into a value or prose field by a scrubber/template. Never replace a placeholder
   with a guessed value. Prefer restoring the original source; otherwise remove the
   affected fixture or document when its meaning is broken.

   ```python
   import re

   SCRUBBER_TOKEN = re.compile(r"<(?:EMAIL|NAME|PASSWORD|KEY|TOKEN|QUESTION)>")

   def has_scrubber_token(text):
       return bool(SCRUBBER_TOKEN.search(text))
   ```
3. **Action:** Fix when the original value can be safely restored; otherwise drop a
   broken generated fixture. Do not expose the replaced value.
4. **Harm test:** Tested on `teams/01-data-a/gold/code-js-ts_gold.csv` (204 gold
   documents): 0 documents changed, 0 documents dropped (0.00% of the gold set;
   limit 2 documents / 1%). **PASS**.
5. **Side effects:** This pattern also appears legitimately in documentation,
   template examples, tests, and UI hints. Context review is mandatory; the regex is
   a detector, not a blind replacement rule.

## Medicine 4 — E1 generated, minified, or build artifacts

1. **Disease:** E1, 19 documents. Examples: `7edec6fc57a3a792` (bundled UMD file),
   `82661aa7e8fdfc1f` (Doxygen search index), `991e567591fcf611` (autogenerated
   contract bindings).
2. **Medicine:** Drop generated artifacts when they have a strong generation marker
   or are clearly a minified/search-index/build output. Do not drop ordinary long
   source files merely because they are large.

   ```python
   import re

   GENERATED = re.compile(
       r"(?i)(auto[- ]?generated|autogenerated|do not edit|"
       r"var searchData\s*=|code generated by|sourceMappingURL=)"
   )

   def is_generated_artifact(text, filename=""):
       minified = text.count("\n") <= 2 and len(text) > 10000
       return bool(GENERATED.search(text)) or minified
   ```
3. **Action:** Drop the document or replace it with the original hand-written source
   file when available.
4. **Harm test:** Tested on `teams/01-data-a/gold/code-js-ts_gold.csv` (204 gold
   documents): 0 documents changed, 0 documents dropped (0.00% of the gold set;
   limit 2 documents / 1%). **PASS**.
5. **Side effects:** Generated code can still be useful for reproducibility, and
   some legitimate source files contain “do not edit” comments. Require a strong
   marker or corroborating artifact evidence.

## Medicine 5 — A2 control characters

1. **Disease:** A2, 17 documents. Examples: `76882c7f242de544` (CR at offset 62),
   `7ae3bbd66580bde3` (CR at offset 51), `a7529f5930280cff` (CR characters at
   offsets 62, 64, and 126).
2. **Medicine:** Convert carriage returns used as CRLF line endings to LF. Preserve
   tabs and newlines; remove other control characters only after confirming they are
   not required by the source format.

   ```python
   def normalize_line_endings(text):
       return text.replace("\r\n", "\n").replace("\r", "\n")
   ```
3. **Action:** Fix line endings. Do not drop a document solely for CRLF.
4. **Harm test:** Tested on `teams/01-data-a/gold/code-js-ts_gold.csv` (204 gold
   documents): 0 documents changed, 0 documents dropped (0.00% of the gold set;
   limit 2 documents / 1%). **PASS**.
5. **Side effects:** Blind removal can alter terminal-control examples, serialized
   data, or strings where a control character is intentional. Apply only to actual
   line-ending controls.

## Medicine 6 — E3 secrets and credential assignments

1. **Disease:** E3, 9 documents. Examples: `0d3bff117f465b99` (Pusher client key at
   offset 8571), `8302c459b07901ca` (Google API key at offset 189),
   `6d3b68ef0b39f910` (passwords at offsets 1782, 2538, 3099, and 3661). Values are
   intentionally not reproduced.
2. **Medicine:** Detect secret-shaped assignments and redact the value without
   logging or copying it. If a real secret is present, quarantine/drop the document
   and rotate the credential outside this repository.

   ```python
   import re

   SECRET_ASSIGNMENT = re.compile(
       r"(?i)\b(api[_-]?key|token|password|passwd|secret|auth[_-]?token)\b"
       r"\s*[:=]\s*([\"'])(?:(?!\2).){8,}\2"
   )

   def contains_secret_assignment(text):
       return bool(SECRET_ASSIGNMENT.search(text))
   ```
3. **Action:** Redact or drop; never publish the value. Scrubbed placeholders alone
   are evidence of contamination but are not themselves secrets.
4. **Harm test:** Tested on `teams/01-data-a/gold/code-js-ts_gold.csv` (204 gold
   documents): 0 documents changed, 1 document dropped (`850e5c84b10e9b1e`, 0.49%
   of the gold set; limit 2 documents / 1%). **PASS**.
5. **Side effects:** API documentation, interface fields such as `API_SECRET`, test
   fixtures, and already-scrubbed placeholders can trigger the detector. Context and
   value inspection must be done privately.

## Medicine 7 — E4 repeated licence headers

1. **Disease:** E4, 8 documents. Examples: `ac23df9698407bac` (Apache header),
   `1e918efcbd1c6f4b` (Apache header), `877058bd3cb250e3` (AGPL header). Short
   copyright notices were intentionally not counted as E4.
2. **Medicine:** Detect and strip long repeated licence comment blocks (10 or more
   lines) at the start of a file, preserving any leading StarCoder metadata line so
   rules compose cleanly. Short copyright notices are left untouched.

   ```python
   import re

   LICENSE_BLOCK = re.compile(
       r"\A((?:<(?:reponame|filename|gh_stars)>[^\r\n]*)+(?:\r?\n)?)?\s*"
       r"(/\*.*?\*/[ \t]*\r?\n?|(?:[ \t]*//[^\n]*\n)+)",
       re.S,
   )
   LICENSE_TERMS = re.compile(
       r"(?i)(?:apache license|gnu (?:lesser |affero )?general public license|"
       r"mit license|permission is hereby granted)"
   )

   def strip_repeated_licence_header(text):
       m = LICENSE_BLOCK.match(text)
       if m:
           block = m.group(2).rstrip("\r\n")
           if LICENSE_TERMS.search(block) and block.count("\n") + 1 >= 10:
               return (m.group(1) or "") + text[m.end():].lstrip("\r\n")
       return text
   ```
3. **Action:** Fix duplicate headers while preserving required legal attribution.
   Do not remove a single legally required licence notice automatically.
4. **Harm test:** Tested on `teams/01-data-a/gold/code-js-ts_gold.csv` (204 gold
   documents): 0 documents changed, 0 documents dropped (0.00% of the gold set;
   limit 2 documents / 1%). **PASS**.
5. **Side effects:** Removing licence text can create legal/compliance problems, and
   short copyright notices are not the E4 disease. Review licence type and whether
   the header is duplicated before editing.

## Findings below the medicine threshold

A1, A5, C2, D1, E2, F2, and F3 each occurred five or fewer times, so no separate
medicine is required by `diagnosis/DISEASES.md`. F1 did not occur in the final labels.
