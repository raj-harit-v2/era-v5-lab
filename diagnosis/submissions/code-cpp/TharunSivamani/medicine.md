# Medicine sheet: code-cpp (Tharun)

Counts and examples below come from the current 500-row label CSV. These are proposed medicines, not cleaners to run on the full dataset. The five sections cover the five most frequent disease codes in that CSV.

## Medicine 1: B3

1. **Disease:** B3, 243 rows. Important taxonomy caveat: all 243 CSV evidence entries point to `<reponame>`, `<filename>`, or `<gh_stars>` metadata prefixes. The disease guide defines B3 as ghost chat markers, and a full-pack scan found no examples of those markers. This proposal follows the current CSV labels, but the B3 classification should be reconciled with the guide before this medicine is approved.
   - `83dc5d60eaef6288`: `<reponame>` at offset 0.
   - `3a7b03b626595019`: `<filename>` at offset 0.
   - `a800be93ce443cb5`: `<gh_stars>` at offset 0.
2. **Medicine:** Remove the first line only when it begins with one of the observed metadata markers. The validation pass found that all 243 B3-labeled rows begin with one of these markers. Keep the metadata in structured fields; do not remove later source lines or rubric-defined chat markers under this rule.

   ```python
   import re

   METADATA_PREFIX = re.compile(
       r"\A<(?:reponame|filename|gh_stars)>[^\r\n]*(?:\r?\n|\Z)",
       re.IGNORECASE,
   )

   def remove_metadata_prefix(text: str) -> str:
       return METADATA_PREFIX.sub("", text, count=1)
   ```

3. **Action:** Fix the model-input copy by removing the dataset metadata line; retain the metadata outside the training text.
4. **Harm test:** Not run. No code-cpp gold set is present in the workspace. Run this against the code-language gold set before release; the medicine fails if it changes more than 1% of that set.
5. **Side effects:** A genuine source line beginning with one of these tags could be removed. Limit the rule to the first line, review the matched line format, and preserve the original source.

## Medicine 2: E4

1. **Disease:** E4, 153 rows.
   - `83dc5d60eaef6288`: copyright header at offset 36; CSV evidence says the same text occurs in three documents.
   - `9f6e4e65e41f69c4`: `MIT License` header at offset 0, spanning 17 lines.
   - `9195ba155f4ee31e`: copyright header at offset 0, spanning 10 lines.
2. **Medicine:** Remove only an audited, exact license header that is confirmed to recur across documents. Keep a hash allowlist of the reviewed header text; do not delete arbitrary first comments containing the word "license".

   ```python
   def strip_verified_header(text: str, header: str) -> str:
       if header and text.startswith(header):
           return text[len(header):]
       return text
   ```

3. **Action:** Fix the training-text copy only after confirming that the identical header is repeated. Keep license and provenance information in metadata or a separate legal record.
4. **Harm test:** Not run. No code-cpp gold set is present in the workspace. Test each allowlisted header against the code-language gold set before release; the medicine fails if it changes more than 1% of that set.
5. **Side effects:** Removing a required attribution or a header that is not actually duplicated can violate license requirements or remove useful source context. Never apply a broad regex to all comments.

## Medicine 3: B4

1. **Disease:** B4, 119 rows. The most frequent recorded examples are redaction/template placeholders.
   - `ab726af7ee73aa3b`: `<NAME>` at offset 25.
   - `a800be93ce443cb5`: `<NAME>` at offset 29.
   - `0797d20110e8ab9b`: `<EMAIL>` at offset 13499 (3 occurrences).
2. **Medicine:** Remove only the known redaction placeholders observed in the CSV. Do not remove arbitrary angle-bracketed text, C++ templates, or strings such as `undefined`/`NaN` without context.

   ```python
   import re

   REDACTION_PLACEHOLDER = re.compile(
       r"<(?:NAME|EMAIL|PASSWORD|AUTHOR|YEAR)>", re.IGNORECASE
   )

   def remove_redaction_placeholders(text: str) -> str:
       return REDACTION_PLACEHOLDER.sub("", text)
   ```

3. **Action:** Fix the training-text copy by removing only exact redaction placeholders; preserve the original in the source archive.
4. **Harm test:** Not run. No code-cpp gold set is present in the workspace. Test the exact allowlist against the code-language gold set before release; the medicine fails if it changes more than 1% of that set.
5. **Side effects:** A placeholder may be part of an illustrative example or generated documentation. Exact-token matching avoids consuming surrounding code, but context review is still required.

## Medicine 4: A2

1. **Disease:** A2, 43 rows. All current A2 evidence in the CSV is carriage returns at line endings.
   - `09b5f5db05cc311d`: carriage return at offset 61; 29 affected lines.
   - `d5e1b337f212f4e2`: carriage return at offset 105; 386 affected lines.
   - `11edb16ce89987d8`: carriage return at offset 32; 111 affected lines.
2. **Medicine:** Normalize carriage-return line endings to LF. Do not remove tabs or ordinary LF newlines.

   ```python
   def normalize_line_endings(text: str) -> str:
       return text.replace("\r\n", "\n").replace("\r", "\n")
   ```

3. **Action:** Fix the training-text copy by normalizing line endings.
4. **Harm test:** Not run. No code-cpp gold set is present in the workspace. Test the change against the code-language gold set before release; the medicine fails if it changes more than 1% of that set.
5. **Side effects:** A literal carriage return embedded inside a string could be changed. Confirm matches occur as line endings before applying the rule.

## Medicine 5: A1

1. **Disease:** A1, 12 rows. All current A1 evidence in the CSV is U+FEFF (BOM).
   - `782bc9665f0acdf7`: U+FEFF at offset 0.
   - `de12a2fd152768d6`: U+FEFF at offset 0.
   - `f63ec57866305825`: U+FEFF at offset 0.
2. **Medicine:** Remove U+FEFF only. Preserve other format characters, especially characters that may be meaningful in source text.

   ```python
   def remove_bom_characters(text: str) -> str:
       return text.replace("\ufeff", "")
   ```

3. **Action:** Fix the training-text copy by removing U+FEFF.
4. **Harm test:** Not run. No code-cpp gold set is present in the workspace. Test the change against the code-language gold set before release; the medicine fails if it changes more than 1% of that set.
5. **Side effects:** A U+FEFF used intentionally inside a document would be removed. Review its position and encoding role before applying the rule.

## Medicine 6: E1 — Minified or generated code

1. **Disease:** E1, 7 documents. All seven E1-labelled rows in `code-cpp.parquet` contain a generated-code notice matched by the rule below. Examples:
   - `deccbc12f9921ae8`: “Automatically generated” at offset 162.
   - `4b53d240dabec20a`: “generated by” at offset 89.
   - `9c1d218d257a6176`: “generated by” at offset 22 (the full notice says “This file has been generated by Py++.”).
2. **Medicine:** Identify generated-code notices for review. The detector matched all seven E1-labelled rows in the pack. It identifies candidate files and does not rewrite code.

   ```python
   import re

   GENERATED_NOTICE = re.compile(
       r"\b(?:auto[- ]generated|automatically generated|machine generated|"
       r"autogenerated|generated by)\b",
       re.IGNORECASE,
   )

   def has_generated_notice(text: str) -> bool:
       return GENERATED_NOTICE.search(text) is not None
   ```

3. **Action:** Review each candidate file. A generated-code notice alone is not grounds for removal. If the generated output is corrupted and its source or template is available, regenerate it from that source; otherwise retain the text. Do not drop rows based solely on this detector.
4. **Harm test:** Not run. No code-language gold set is present in the workspace. The detector does not change or drop documents. Test any follow-up transformation against the code-language gold set and report changed and dropped counts. The medicine fails if either exceeds 1% of the gold set.
5. **Side effects:** Generated code may be valid and useful. Phrases such as “generated by” may occur in quoted examples or ordinary comments; review each match in context. This rule does not detect minification, which requires separate evidence such as unusually long lines.
