# Medicine sheet: sci-finepdfs (jssunil)

Written from my reading of the first 500 documents of the pack (`sci-finepdfs.parquet`) and the label sheet `labels.csv`, following the disease codes of `diagnosis/DISEASES.md`. Every number below comes from a harm-test script I ran locally (it is not part of this PR), on the code in this file and on `labels.csv` as the truth.

Diseases found across the 500 documents (a document can have several):
- **B4 (placeholders and converter junk in prose):** 132 documents
- **C1 (boilerplate: running headers, tables of contents, repository covers, link text):** 116 documents
- **F1 (personal data of private people):** 56 documents
- **B2 (HTML tags `<sup>`, `<sub>`, `<br>`):** 15 documents
- **C4 (two documents joined):** 16 documents
- **C3 (truncated document):** 17 documents
- **C2 (repeated passages):** 19 documents
- **A6 (mixed script inside a word):** 6 documents
- **D1 (wrong language label):** 7 documents
- Seen five times or fewer, so no medicine: D3 (3), B5 (3), C5 (4), D4 (2), D5 (1), A1 (1), F3 (1)

Reading: 456 documents read in full, 44 read in part (start, end and a scan; for these I do not judge D4 or D5). Every row originally read only in part and marked `clean` has since been re-read in full or found a disease on closer reading (3 moved to `full`+`clean`, 3 to `partial`+`fix`); none remain.
Verdicts:
- `clean`: 238 documents (47.6%)
- `fix`: 235 documents (47.0%)
- `drop`: 27 documents (5.4%)

Gate 1: the harm base is the published Data A gold set, `teams/01-data-a/gold/sci-finepdfs_gold.csv` on `patilvijay23/era-v5-lab@g1-harm-test` (regenerated 31 Oct, ~21:45 IST, commit `880258f`, after an earlier push of the same update failed silently; PR #140 will move it onto `main` at the same path): 198 documents, each read in full and marked clean by two readers of this pack. Below the 200 target, so TSAI's rule for small gold sets applies: a rule passes if it changes at most 1 document or 1% of the gold set, whichever is larger (here, 1 document = 0.51%). All 9 medicines PASS: C1 and C2 each change 1 of the 198 gold documents (the allowed maximum); the rest change 0. F1 changed 9 of the 198 gold documents on the first run against this larger set (4.55%, well past the 1-document gate; office and agency contact lines it could not tell from a private number) and was narrowed in response - see its harm test and side effects below.

## Observations

- 58 rows mention converter damage (invented image descriptions, spliced captions, lost page parts) that has no listed code; the note column describes each case.
- Most phone numbers in this pack belong to offices, officials and companies, not to private people; they are not F1 (see the F1 side effects).

---

## Medicine 1: C1 Boilerplate (Running Page Headers & Footers)

1. **Disease:** C1, found in 116 of the 500 documents.
   Examples:
   - `8c1aed2f8a439b91` (row 1): `running header 'MIT Introduction to Deep Learn' repeated 8x, first @56`
   - `50cc681aabd3d82b` (row 4): `running header 'Motion Carried.' repeated 35x, first @1816`
   - `507d7cf0978d22e4` (row 5): `running header 'Member of Congress' repeated 243x, first @107006`

2. **The medicine:**
   - *In words:* Find lines of 15 or more characters that repeat 5 or more times, as page headers and footers do. Leave out table rows, list items, fill-in blanks, LaTeX math, field labels ('Topics include:', 'Species: rabbit'), quoted clauses and full sentences of 8 or more words ending in a full stop, because those repeat as content. If the extra copies would be more than 10% of the document it is repetitive content (a price list, a form), so change nothing. Otherwise keep the first copy of each header and delete the rest.

   ```python
   import re
   from collections import Counter

   def running_header_lines(text, min_len=15, min_repeats=5, max_removed_frac=0.10):
       """Lines that repeat like PDF page headers/footers: {stripped line: count}.
       Content that merely repeats is excluded: table rows and borders, list items, fill-in blanks,
       LaTeX math. If the extra copies would be more than `max_removed_frac` of the document, the
       document is repetitive content (a price list, a form, a manual), not boilerplate: return {}."""
       table_border = re.compile(r"^[\s|:\-]+$")
       math_env = re.compile(r"\\(?:begin|end)\{(?:cases|align\*?|equation\*?)\}|\\hline")
       list_item = re.compile(r"^(?:[-*\u2022]|\(?[0-9A-Za-z]{1,3}[.)])\s")
       field_label = re.compile(r"^[A-Za-z ]{3,40}:\s*(?:\S.{0,30})?$")  # 'Topics include:', 'Species: rabbit'
       counts = Counter(l.strip() for l in text.split("\n") if len(l.strip()) >= min_len)
       found = {}
       for line, count in counts.items():
           if count < min_repeats:
               continue
           if line.startswith("|") or table_border.match(line) or math_env.search(line):
               continue
           if list_item.match(line) or "___" in line or field_label.match(line):
               continue
           if line[0] in "\"'(" or line.startswith(";--") or (line.endswith(".") and len(line.split()) >= 8):
               continue  # quoted text, separators and running sentences are content, not headers
           found[line] = count
       extra = sum(len(line) * (count - 1) for line, count in found.items())
       if extra > max_removed_frac * len(text):
           return {}
       return found


   def remove_running_headers(text: str) -> str:
       headers = running_header_lines(text)
       if not headers:
           return text
       kept, seen = [], set()
       for line in text.split("\n"):
           s = line.strip()
           if s in headers:
               if s in seen:
                   continue
               seen.add(s)
           kept.append(line)
       return "\n".join(kept)


   def medicine_c1(text: str) -> str:
       return remove_running_headers(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 54 of 500 documents (10.8%); 44 were labelled `C1`, 10 changed without that label.
     - Removes 0.311% of all characters; the worst single document loses 7.4%.
     - Changes **1 of 198** gold documents (0.51%, the allowed maximum); gate (at most 1 document or 1%): **PASS**.
     - Changes 1 of the 235 documents that the reader read in full and marked clean (now also the one changed gold document, since the gold set grew to cover it).
     - Leaves 72 of the 116 labelled documents unchanged.

5. **The side effects:**
   - The rule covers running headers and footers only: it touches 44 of the 116 C1 documents. The rest are tables of contents, repository cover pages and link lists, which need a different rule.
   - Repeated field labels ('Topics include:'), key-value lines, quoted clauses and full sentences are skipped on purpose; they repeat as content. A section title that repeats by design can still be deleted (1 clean document).
   - In slide decks the first copy keeps the title on slide 1 and removes it from later slides, as intended.

---

## Medicine 2: F1 Personal Data (Unredacted Telephone Numbers & Clinical Case Histories)

1. **Disease:** F1, found in 56 of the 500 documents.
   Examples:
   - `6d2428a3ad8e41d6` (row 2): `phone @19088 (2 total)`
   - `507d7cf0978d22e4` (row 5): `phone @119149 (1 total)`
   - `3db737dca1122c53` (row 6): `phone @2846 (2 total)`

2. **The medicine:**
   - *In words:* Match the numbers the F1 detector matches: a 10-digit phone number after a contact label (Cell, Mobile, Tel, Fax, ...) or after 'call ...' / 'contact ... at', and replace only the number with <PHONE>, keeping the label. Clinical age/sex descriptors (e.g. 'A 67-year-old woman') are not changed: they do not identify a person. Added 31 Oct after the gold set grew to 198 documents and this rule failed its gate (changed 9 of them): leave the number alone if an office/agency cue (`P.O. Box`, `Committee`, `Department`, `Corp.`, `Docket`, a bureau code like `DHS/OS/PRIV`, ...) appears within 400 characters of it, since that is almost always a company or government contact line, not a private person's own number.

   ```python
   import re

   PHONE_REDACT_RE = re.compile(
       r"((?:(?:Cell|Mobile|Daytime|Direct|Office|Business|Contact|Telephones?|Phone(?:\s+Number)?|Tele|Tel|Fax)[\s:|]+"
       r"|(?:call|contact)(?:\s+[A-Za-z0-9.\-]+){0,6}\s+at\s+|call\s+))"
       r"((?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})",
       re.IGNORECASE,
   )

   # Organizational cues within 400 characters of the number: office/agency language,
   # not a private person's own line.
   ORG_CONTEXT_RE = re.compile(
       r"\bP\.?O\.?\s*Box\b|\bCommittee\b|\bDepartment\b|\bOffice of\b|\bAgency\b|\bBureau\b|\bClerk\b|"
       r"\bCorp(?:oration)?\b|\bL\.?L\.?C\.?\b|\bInc\.?\b|\bLtd\.?\b|\bOur Team\b|\bthis office\b|"
       r"\bDocket\b|\bDivision\b|\bBoard\b|\bPermit\b|"
       r"[A-Z]{2,}/[A-Z]{2,}(?:/[A-Z]{2,}){0,2}",  # bureau codes like DHS/OS/PRIV
       re.IGNORECASE,
   )

   def redact_phone_numbers(text: str, window: int = 400) -> str:
       def repl(m: "re.Match") -> str:
           ctx = text[max(0, m.start() - window): min(len(text), m.end() + window)]
           if ORG_CONTEXT_RE.search(ctx):
               return m.group(0)  # an office/agency/company line, not a private number
           return m.group(1) + "<PHONE>"
       return PHONE_REDACT_RE.sub(repl, text)


   def medicine_f1(text: str) -> str:
       return redact_phone_numbers(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 32 of 500 documents (6.4%); 25 were labelled `F1`, 7 changed without that label.
     - Removes 0.002% of all characters; the worst single document loses 0.8%.
     - Changes **0 of 198** gold documents (0.00%); gate (at most 1 document or 1%): **PASS**. On the first run against this gold set, before the office/agency context check was added, this medicine changed 9 of 198 (4.55%) and failed the gate; see the medicine section above for the fix.
     - Changes 0 of the 235 documents that the reader read in full and marked clean.
     - Leaves 31 of the 56 labelled documents unchanged.

5. **The side effects:**
   - The rule still cannot tell a private phone from an organisation's by itself; it now also checks the surrounding 400 characters for office/agency language and skips the number if it finds any. That fixed all 9 gold false positives, at a real recall cost: documents left unchanged rose from 10 to 31 of the 56 labelled, because many personal numbers in this pack sit on a page that also mentions a department, committee or company elsewhere.
   - It still handles phone numbers after a contact label only; home addresses, ID data and clinical histories are left unchanged, because no safe pattern finds them.

---

## Medicine 3: B4 Placeholders (Upstream Synthetic Redaction & Template Parameters)

1. **Disease:** B4, found in 132 of the 500 documents.
   Examples:
   - `6d2428a3ad8e41d6` (row 2): `placeholder 'firstname.lastname@example.org' @1733 (1 total)`
   - `50cc681aabd3d82b` (row 4): `placeholder 'email@example.com' @219980 (1 total)`
   - `507d7cf0978d22e4` (row 5): `placeholder 'firstname.lastname@example.org' @12600 (112 total)`

2. **The medicine:**
   - *In words:* Replace synthetic placeholders (firstname.lastname@example.org / email@example.com) with the standard <EMAIL> token. Remove unrendered parameter placeholders (<parameter 1>, <function name>, <typename T>).

   ```python
   import re

   SYNTHETIC_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@example\.(?:org|com)\b')
   TEMPLATE_PARAM_RE = re.compile(r'<(?:parameter|function name|process description|typename|see attached)[^>]*>', re.IGNORECASE)

   def clean_placeholders(text: str) -> str:
       text = SYNTHETIC_EMAIL_RE.sub('<EMAIL>', text)
       text = TEMPLATE_PARAM_RE.sub('', text)
       return text


   def medicine_b4(text: str) -> str:
       return clean_placeholders(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 121 of 500 documents (24.2%); 120 were labelled `B4`, 1 changed without that label.
     - Removes 0.041% of all characters; the worst single document loses 8.9%.
     - Changes **0 of 198** gold documents (0.00%); gate (at most 1 document or 1%): **PASS**.
     - Changes 0 of the 235 documents that the reader read in full and marked clean (the gold set is a subset of these).
     - Leaves 12 of the 132 labelled documents unchanged.

5. **The side effects:**
   - A tutorial about example.com would have the domain replaced by <EMAIL>.
   - Only synthetic example.org/example.com addresses and four template-parameter shapes are handled; 12 B4 documents (converter image slots, form placeholders, IP-like numbers) are not.

---

## Medicine 4: C3 Truncated Documents (Broken Trailing Tables & Mid-Phrase Cutoffs)

1. **Disease:** C3, found in 17 of the 500 documents.
   Examples:
   - `51a4fb599da754db` (row 30): `starts mid-sentence 'langue, il est normal que nous rete' @0`
   - `6acc7c94105bdebd` (row 32): `cut off mid-phrase on 'such as the' @9437`
   - `4ef01c1611c6bcaf` (row 200): `worksheet stops after line 25 with an empty table row '| --- / --- |' @7255; later worksheet sections missing`

2. **The medicine:**
   - *In words:* Only touch what the C3 detector flags. (1) A cut-off last table row (a bare `| --- |` separator, no closing pipe, or fewer cells than the rows above it) is deleted; a complete table at the end is left alone. (2) A last sentence that stops on a connector word ('... such as the') before the figure captions is deleted, the captions stay. (3) A document that starts with a lowercase word loses the leading fragment up to the first real sentence end in its first 400 characters (abbreviations like 'p. 50' do not count); if there is none, the start is left as is.

   ```python
   import re
   from collections import Counter

   HANGING_WORDS = set(['a', 'after', 'an', 'and', 'as', 'at', 'before', 'but', 'by', 'during', 'for', 'from', 'in', 'into', 'of', 'or', 'such', 'such as', 'than', 'that', 'the', 'through', 'to', 'which', 'with'])


   def table_row_is_ragged(lines):
       """True if the last Markdown table row of `lines` (stripped, non-empty) looks cut off:
       a bare separator row with no body, a row with no closing pipe, or fewer cells than its peers."""
       def cells(row):
           return len(row.strip("|").split("|"))

       def is_sep(row):
           return "-" in row and re.fullmatch(r"[\s:|\-]+", row) is not None

       last = lines[-1]
       if is_sep(last):
           return True
       if not last.endswith("|"):
           return True
       peers = [cells(l) for l in lines[-11:-1] if l.startswith("|") and not is_sep(l)]
       if not peers:
           return False
       return cells(last) < Counter(peers).most_common(1)[0][0]


   def starts_mid_sentence(text):
       """True if the first non-empty line (25+ characters) begins with a lowercase word: the start was cut off."""
       first = next((l.strip() for l in text.split("\n") if l.strip()), "")
       return len(first) >= 25 and first[0].islower() and re.match(r"[a-z\u00e0\u00e2\u00e4\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f6\u00f9\u00fb\u00fc\u00e7]{3,}\b", first) is not None


   def first_sentence_offset(text, window=400):
       """Offset where the first complete sentence starts after a leading fragment, or 0 if no sentence
       end is found in the first `window` characters. Abbreviations ('p. 50', 'e.g. ', 'Fig. 2') are not sentence ends."""
       for m in re.finditer(r"[.!?][\"')\]\u2019\u201d\u00bb\ufffd]*\s+(?=[A-Z\u00c0-\u00dc])", text[:window]):
           word = re.search(r"([^\W\d_]+)$", text[:m.start()])
           if not word or (len(word.group(1)) >= 3 and word.group(1).lower() not in ("etc", "fig", "vol", "inc", "ltd", "eds")):
               return m.end()
       return 0


   def dangling_tail_span(text):
       """(start, end) of a last sentence cut off on a connector word ('... such as the') that is followed only by
       figure/table captions, or None. The span is the unfinished sentence, not the captions after it."""
       lines = text.rstrip().split("\n")
       pos, o = [], 0
       for l in lines:
           pos.append(o)
           o += len(l) + 1
       k, captions = len(lines) - 1, False
       while k >= 0 and (not lines[k].strip() or re.match(r"(?:Figure|Table|Fig\.)\s+\d+\b", lines[k].strip(), re.I)):
           captions = captions or bool(lines[k].strip())
           k -= 1
       if k < 0 or not captions:
           return None
       line = lines[k].rstrip()
       words = re.findall(r"\b[A-Za-z]+\b", line.lower())
       if line.endswith((".", "!", "?", '"', "'", ")")) or not words or words[-1] not in HANGING_WORDS:
           return None
       ends = list(re.finditer(r"[.!?][\"')\]]*\s+(?=[A-Z])", line))
       start = ends[-1].end() if ends else 0
       return pos[k] + start, pos[k] + len(line)


   def repair_truncated_text(text: str) -> str:
       out = text
       lines = out.rstrip().split("\n")
       footer = []
       if len(lines) >= 2 and re.fullmatch(r"\*[^*]+\*", lines[-1].strip()) and lines[-2].strip().startswith("|"):
           footer = [lines.pop()]
       stripped = [l.strip() for l in lines if l.strip()]
       if stripped and stripped[-1].startswith("|") and stripped[-1].count("|") >= 2 and table_row_is_ragged(stripped):
           out = "\n".join(lines[:-1] + footer)
       span = dangling_tail_span(out)
       if span:
           out = out[:span[0]].rstrip(" ") + out[span[1]:]
       if starts_mid_sentence(out):
           cut = first_sentence_offset(out)
           if cut:
               out = out[cut:]
       return out


   def medicine_c3(text: str) -> str:
       return repair_truncated_text(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 5 of 500 documents (1.0%); 5 were labelled `C3`, 0 changed without that label.
     - Removes 0.003% of all characters; the worst single document loses 1.4%.
     - Changes **0 of 198** gold documents (0.00%); gate (at most 1 document or 1%): **PASS**.
     - Changes 0 of the 235 documents that the reader read in full and marked clean (the gold set is a subset of these).
     - Leaves 12 of the 17 labelled documents unchanged.

5. **The side effects:**
   - Removes the last partial table row or the dangling phrase when the text is cut off at the end of the PDF. Recall is low: 5 of 17; the other C3 documents are short stubs or cut mid-document, with no common pattern.

---

## Medicine 5: B2 HTML Tags (Scientific Subscripts & Line Breaks)

1. **Disease:** B2, found in 15 of the 500 documents.
   Examples:
   - `7ea84af3398cb3ed` (row 16): `tag '<br>' @445945 (5 total)`
   - `50f74766355f26d3` (row 21): `tag '<sup>' @9685 (14 total)`
   - `c298d58f6344ddde` (row 22): `tag '<sup>' @43973 (2 total)`

2. **The medicine:**
   - *In words:* Convert <sup>text</sup> to ^text, <sub>text</sub> to _text, and <br> to a newline. Strip remaining layout tags (<div>, <p>, <span>) while ignoring formal symbols inside LaTeX $...$ math mode.

   ```python
   import re

   def clean_pdf_html_tags(text: str) -> str:
       text = re.sub(r'<sup>(.*?)</sup>', r'^\1', text, flags=re.IGNORECASE)
       text = re.sub(r'<sub>(.*?)</sub>', r'_\1', text, flags=re.IGNORECASE)
       text = re.sub(r'<br\s*/?>', r'\n', text, flags=re.IGNORECASE)
       text = re.sub(r'</?(?:div|p|span|table|tr|td|th)(?:\s[^>]*|/)?>', '', text, flags=re.IGNORECASE)
       return text


   def medicine_b2(text: str) -> str:
       return clean_pdf_html_tags(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 14 of 500 documents (2.8%); 14 were labelled `B2`, 0 changed without that label.
     - Removes 0.005% of all characters; the worst single document loses 1.1%.
     - Changes **0 of 198** gold documents (0.00%); gate (at most 1 document or 1%): **PASS**.
     - Changes 0 of the 235 documents that the reader read in full and marked clean (the gold set is a subset of these).
     - Leaves 1 of the 15 labelled documents unchanged.

5. **The side effects:**
   - Converting <sup>/<sub> to ^ and _ keeps gene superscripts and chemical subscripts readable. Tags inside LaTeX are not special-cased.

---

## Medicine 6: A6 Mixed Script Within a Word (Cyrillic/Latin OCR Homoglyphs)

1. **Disease:** A6, found in 6 of the 500 documents.
   Examples:
   - `d20d4f04e5704ba7` (row 42): `CJK character inside Latin word @6310`
   - `cdc5973ec2161f44` (row 75): `mixed Latin/Cyrillic word @85429`
   - `f5faeb5d20b73087` (row 149): `CJK char in English word 'raise立ts' @11493`

2. **The medicine:**
   - *In words:* Detect tokens mixing Latin and Cyrillic scripts within the same word (such as 'Ilonиемi', 'vrтoglavo', or 'АКУМУЛATOR') and normalize lookalike glyphs to the majority script of the word while exempting scientific Greek symbols. In a document with 5 or fewer CJK characters in all, delete a CJK character glued to a Latin word of 2 or more letters: it is a stray glyph in English text. A document with more CJK is bilingual content and is left alone.

   ```python
   import re

   CYR_TO_LAT = str.maketrans({'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X', 'а': 'a', 'е': 'e', 'и': 'i', 'м': 'm', 'о': 'o', 'р': 'p', 'с': 'c', 'т': 't', 'х': 'x'})
   MIXED_WORD_RE = re.compile(r'\b(?:[A-Za-z]+[\u0400-\u04FF]+[A-Za-z0-9]*|[\u0400-\u04FF]+[A-Za-z]+[A-Za-z0-9]*)\b')

   CJK_IN_LATIN_RE = re.compile(r'(?<=[A-Za-z]{2})[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]+|[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]+(?=[A-Za-z]{2})')

   def fix_mixed_script_words(text: str) -> str:
       text = MIXED_WORD_RE.sub(lambda m: m.group(0).translate(CYR_TO_LAT), text)
       if len(re.findall(r'[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]', text)) > 5:
           return text
       return CJK_IN_LATIN_RE.sub('', text)


   def medicine_a6(text: str) -> str:
       return fix_mixed_script_words(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 6 of 500 documents (1.2%); 6 were labelled `A6`, 0 changed without that label.
     - Removes 0.000% of all characters; the worst single document loses 0.2%.
     - Changes **0 of 198** gold documents (0.00%); gate (at most 1 document or 1%): **PASS**.
     - Changes 0 of the 235 documents that the reader read in full and marked clean (the gold set is a subset of these).
     - Leaves 0 of the 6 labelled documents unchanged.

5. **The side effects:**
   - Pure Cyrillic words and Greek maths symbols stay untouched. A document with more than 5 CJK characters is treated as bilingual and left alone.

---

## Medicine 7: D1/D3 Full-Document Language Verification & Bilingual Filtering

1. **Disease:** D1, found in 7 of the 500 documents.
   Examples:
   - `51a4fb599da754db` (row 30): `French/German text @0 (8 segments) mixed with English @103 (149 segments)`
   - `bfbe6f0f5d61c19e` (row 82): `German text @9463 (49 segments) mixed with English @53 (280 segments)`
   - `1c686de5116ab261` (row 102): `Lithuanian (lit_Latn) @0-3886 labelled eng_Latn`

2. **The medicine:**
   - *In words:* Act only on a document the D1/D3 detector flags as a bilingual fix (foreign text mixed with English); a purely foreign document is dropped by the pipeline, and a document the detector does not flag is returned unchanged. In a flagged document remove each paragraph of 40 or more characters that is mostly Cyrillic, or whose French/German/Spanish stopword hits are at least 2 and exceed its English hits (table rows are kept). If every paragraph would go, return the text unchanged.

   ```python
   import re

   EN_STOPWORDS = set(['an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'in', 'is', 'of', 'on', 'or', 'that', 'the', 'this', 'to', 'was', 'which', 'with'])
   FR_STOPWORDS = set(['avec', 'cette', 'comme', 'dans', 'des', 'la', 'le', 'les', 'mais', 'nous', 'par', 'pas', 'plus', 'pour', 'que', 'qui', 'sont', 'sur', 'une', 'vous'])
   DE_STOPWORDS = set(['als', 'an', 'auch', 'auf', 'das', 'dem', 'den', 'der', 'die', 'es', 'für', 'in', 'ist', 'mit', 'nicht', 'sich', 'und', 'von', 'werden', 'zu'])
   ES_STOPWORDS = set(['como', 'con', 'cuando', 'del', 'el', 'entre', 'este', 'fue', 'había', 'la', 'las', 'los', 'más', 'para', 'pero', 'por', 'sus', 'también', 'una'])


   def check_full_document_language(text: str):
       """
       Reads the ENTIRE document sentence-by-sentence and line-by-line to classify language distribution.
       - If purely non-English (>85% non-English segments and <2 English segments) -> D1 (drop)
       - If document starts in or contains substantial French/German/Spanish/Cyrillic
         AND also contains English sentences/sections -> D1;D3 (fix: bilingual/mixed document,
         keep English sections or route appropriately rather than blindly dropping).
       """
       # Split into sentence/clause segments so lines mixing French quotes + English translation are caught
       segments = [
           s.strip()
           for s in re.split(r"[\n.!?\"“”‘’()]+", text)
           if len(s.strip()) >= 25
       ]
       if not segments:
           return [], "", "", "clean"

       en_segs = 0
       fr_segs = 0
       de_segs = 0
       es_segs = 0
       cyr_segs = 0
       first_non_en_off = None
       first_en_off = None

       for seg in segments:
           words = set(re.findall(r"\b[a-zA-Zàâäéèêëîïôöùûüçäöüßáéíóúñ]+\b", seg.lower()))
           cyr_count = sum(1 for c in seg if "\u0400" <= c <= "\u04FF")
           if cyr_count > len(seg) * 0.3:
               cyr_segs += 1
               if first_non_en_off is None:
                   first_non_en_off = max(0, text.find(seg[:20]))
               continue

           en_hits = len(words & EN_STOPWORDS)
           fr_hits = len(words & FR_STOPWORDS)
           de_hits = len(words & DE_STOPWORDS)
           es_hits = len(words & ES_STOPWORDS)

           best = max(en_hits, fr_hits, de_hits, es_hits)
           if best == 0:
               continue
           if fr_hits == best and fr_hits >= 2:
               fr_segs += 1
               if first_non_en_off is None:
                   first_non_en_off = max(0, text.find(seg[:20]))
           elif de_hits == best and de_hits >= 2:
               de_segs += 1
               if first_non_en_off is None:
                   first_non_en_off = max(0, text.find(seg[:20]))
           elif es_hits == best and es_hits >= 2:
               es_segs += 1
               if first_non_en_off is None:
                   first_non_en_off = max(0, text.find(seg[:20]))
           elif en_hits == best and en_hits >= 2:
               en_segs += 1
               if first_en_off is None:
                   first_en_off = max(0, text.find(seg[:20]))

       non_en_map = {
           "French": fr_segs,
           "German": de_segs,
           "Spanish": es_segs,
           "Cyrillic": cyr_segs,
       }
       dom_lang, dom_count = max(non_en_map.items(), key=lambda x: x[1])
       total_classified = en_segs + sum(non_en_map.values())

       # Check if document starts in a non-English language at offset 0 or has >= 3 non-English segments
       first_words = set(re.findall(r"\b[a-zA-Zàâäéèêëîïôöùûüçäöüßáéíóúñ]+\b", text[:150].lower()))
       starts_fr = len(first_words & FR_STOPWORDS) >= 2

       if (dom_count >= 3 or starts_fr) and total_classified > 0:
           non_en_total = sum(non_en_map.values())
           non_en_ratio = non_en_total / total_classified
           langs_present = [k for k, v in non_en_map.items() if v >= 1]
           lang_str = "/".join(langs_present) if langs_present else dom_lang

           if en_segs >= 2 and (non_en_ratio >= 0.03 or starts_fr):
               return (
                   ["D1", "D3"],
                   f"{lang_str} text at offset {first_non_en_off if first_non_en_off is not None else 0} ({non_en_total} segments) mixed with English at offset {first_en_off or 0} ({en_segs} segments)",
                   f"D1: {lang_str} text labeled as eng_Latn; D3: bilingual {lang_str}/English document ({en_segs} English segments)",
                   "fix",
               )
           if non_en_ratio > 0.85 and en_segs < 2:
               return (
                   ["D1"],
                   f"{lang_str} text at offset {first_non_en_off or 0} ({non_en_total}/{total_classified} segments)",
                   f"D1: {lang_str} document labeled as eng_Latn",
                   "drop",
               )

       return [], "", "", "clean"


   def filter_bilingual_paragraphs(text: str, min_len: int = 40) -> str:
       codes, _, _, verdict = check_full_document_language(text)
       if not codes or verdict != "fix":
           return text
       others = [FR_STOPWORDS, DE_STOPWORDS, ES_STOPWORDS]

       def foreign(p):
           if len(p) < min_len or p.lstrip().startswith("|"):
               return False
           if sum("\u0400" <= c <= "\u04ff" for c in p) > 0.3 * len(p):
               return True
           words = set(re.findall(r"\b[^\W\d_]+\b", p.lower()))
           best = max(len(words & o) for o in others)
           return best >= 2 and best > len(words & EN_STOPWORDS)
       paras = text.split("\n\n")
       flags = [foreign(p) for p in paras]
       if not any(flags) or all(flags):
           return text
       return "\n\n".join(p for p, f in zip(paras, flags) if not f)


   def medicine_d1(text: str) -> str:
       return filter_bilingual_paragraphs(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 6 of 500 documents (1.2%); 2 were labelled `D1`, 4 changed without that label.
     - Removes 0.445% of all characters; the worst single document loses 26.4%.
     - Changes **0 of 198** gold documents (0.00%); gate (at most 1 document or 1%): **PASS**.
     - Changes 0 of the 235 documents that the reader read in full and marked clean (the gold set is a subset of these).
     - Leaves 5 of the 7 labelled documents unchanged.

5. **The side effects:**
   - Keeps English abstracts, citations and bilingual passages in multi-language papers. It changes 4 documents that are not labelled D1 (other foreign-language paragraphs; the largest loss is 26.4% of one document).

---

## Medicine 8: C4 Two Documents Joined (Multi-Article Journal Pages)

1. **Disease:** C4, found in 16 of the 500 documents.
   Examples:
   - `51a4fb599da754db` (row 30): `2 joined articles; second starts @1362 (line 9)`
   - `6acc7c94105bdebd` (row 32): `2 joined articles; second starts @7254 (line 61)`
   - `19e4332d89d32061` (row 77): `unrelated items joined w/o boundary - headline @14 not matched by body; orphan Minister of the Interior signature @2135; stray timestamp @2522; ad heading @3402 inside race programme`

2. **The medicine:**
   - *In words:* Split the document at the clear article boundaries (a second 'To the Editor:' letter with the title lines above it, or the sign-off and author line that closes a review) into pieces of at least 500 characters. The pipeline should emit each piece as its own document; as a text-to-text step this keeps the longest piece. A document with no clear boundary is returned unchanged.

   ```python
   import re

   def split_joined_documents(text, min_len=3000, min_gap=1000, min_tail=500):
       """Split `text` into the articles that were joined into it, or return [text] if no boundary is clear.
       Two layouts are recognised: several 'To the Editor:' letters (the short title lines above each
       letter go with it), and several reviews that each end with a 'Magdalen College, Oxford' sign-off
       plus an author line. A piece shorter than `min_tail` characters is not split off."""
       if len(text) < min_len:
           return [text]
       cuts = []

       letters = [m.start() for m in re.finditer(r"^to the editor\s*:", text, re.I | re.M)]
       if len(letters) >= 2 and letters[-1] - letters[0] > min_gap:
           for o in letters[1:]:
               start = o
               for _ in range(2):  # pull the (short) title lines above the letter into it
                   head = text[:start].rstrip("\n")
                   p0 = head.rfind("\n\n")
                   p0 = 0 if p0 < 0 else p0 + 2
                   if 0 < len(head) - p0 <= 150 and p0 > 0:
                       start = p0
                   else:
                       break
               cuts.append(start)

       signoffs = list(re.finditer(r"^magdalen college,\s*oxford\n\n[^\n]+\n", text, re.I | re.M))
       if len(signoffs) >= 2 and signoffs[-1].start() - signoffs[0].start() > min_gap:
           cuts.extend(m.end() for m in signoffs)

       pieces, prev = [], 0
       for c in sorted(set(cuts)):
           if c - prev >= min_tail and len(text) - c >= min_tail:
               pieces.append(text[prev:c])
               prev = c
       pieces.append(text[prev:])
       return pieces


   def keep_longest_article(text: str) -> str:
       return max(split_joined_documents(text), key=len)


   def medicine_c4(text: str) -> str:
       return keep_longest_article(text)
   ```

3. **The action:** `fix` the text.

4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 2 of 500 documents (0.4%); 2 were labelled `C4`, 0 changed without that label.
     - Removes 0.015% of all characters; the worst single document loses 24.7%.
     - Changes **0 of 198** gold documents (0.00%); gate (at most 1 document or 1%): **PASS**.
     - Changes 0 of the 235 documents that the reader read in full and marked clean (the gold set is a subset of these).
     - Leaves 14 of the 16 labelled documents unchanged.

5. **The side effects:**
   - The rule fits only two layouts ('To the Editor:' letters and 'Magdalen College, Oxford' sign-offs): it finds 2 of the 16 C4 documents. The other 14 have no common boundary. For them the instructor's ruling is drop, which needs a detector that I do not have.
   - The later articles are cut from this text; emitted as their own documents they lose nothing.

---

## Medicine 9: C2 Repeated Passages (Whole Paragraphs Copied Again)

1. **Disease:** C2, found in 19 of the 500 documents.
   Examples:
   - `f5faeb5d20b73087` (row 149): `2,600-char currant-worm passage repeated @3974-6544 / @7045-9636`
   - `f48baf0b54a4e80f` (row 154): `the full well-proposal letter is repeated almost verbatim for a second addressee @3395-6235 (first copy @0-2836)`
   - `5cd969382b955d84` (row 175): `full surety power-of-attorney + VP notarisation + certificate block repeated @18551-21534 and @28496-31420; notary acknowledgment for same signer repeated @11962 @17552 @27501`

2. **The medicine:**
   - *In words:* Find paragraphs of 600 or more characters that repeat an earlier paragraph word for word (spaces and line breaks ignored). Table rows and LaTeX blocks are never counted. Keep the first copy and delete the later ones. If the copies are more than half of the document, the document is mostly repeats: change nothing, because the pipeline drops it.

   ```python
   import re

   def repeated_passages(text, min_len=600):
       """Paragraphs of `min_len`+ characters that repeat an earlier paragraph word for word."""
       seen, copies = set(), []
       for para in text.split("\n\n"):
           key = " ".join(para.split())
           if len(key) < min_len or key.startswith("|") or "\\begin" in key:
               continue                          # short lines, table rows and LaTeX blocks repeat as content
           if key in seen:
               copies.append(para)
           seen.add(key)
       return copies


   def remove_repeated_passages(text: str, max_removed_frac: float = 0.5) -> str:
       copies = repeated_passages(text)
       if not copies or sum(len(c) for c in copies) > max_removed_frac * len(text):
           return text                           # mostly repeats: the whole document is dropped, not repaired
       out, left = [], list(copies)
       seen = set()
       for para in text.split("\n\n"):
           key = " ".join(para.split())
           if para in left and key in seen:
               left.remove(para)
               continue
           seen.add(key)
           out.append(para)
       return "\n\n".join(out)


   def medicine_c2(text: str) -> str:
       return remove_repeated_passages(text)
   ```

3. **The action:** `fix` the text.
4. **The harm test:**
   - Measured by my local harm-test script on 500 documents; harm base: the published Data A gold set `teams/01-data-a/gold/sci-finepdfs_gold.csv` (`patilvijay23/era-v5-lab@g1-harm-test`, regenerated 31 Oct ~21:45 IST): 198 documents, two readers per document, below the 200 target, so one changed document is 0.51%.
     - Changes 17 of 500 documents (3.4%); 4 were labelled `C2`, 13 changed without that label.
     - Removes 0.213% of all characters; the worst single document loses 15.9%.
     - Changes **1 of 198** gold documents (0.51%, the allowed maximum); gate (at most 1 document or 1%): **PASS**.
     - Changes 1 of the 235 documents that the reader read in full and marked clean (now also the one changed gold document, since the gold set grew to cover it).
     - Leaves 15 of the 19 labelled documents unchanged.

5. **The side effects:**
   - Recall is low (4 of 19): paragraphs under 600 characters, repeated single lines (a table row, a short field label like 'Reprint requests to:') and near-copies are not found. The length is set high on purpose, because at 300 characters the rule changed a gold document.
   - Forms and bills that repeat clauses by design can lose a copy (1 clean document).
