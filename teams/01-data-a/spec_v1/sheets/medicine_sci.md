# Medicine sheet: sci-finepdfs — reconciled two-contributor proposal

> **Status:** single executable medicine for the 500-document sci-finepdfs sample; candidate rules tested against the supplied pack and the 40-row gold snapshot, **not approved for unrestricted production cleaning**. Pending independent annotation adjudication and gold refresh.

**Sources:** `medicine_sci.md` (patilvijay23 consolidation) and `medicine.md` (jssunil). Each contributor's original medicine remains unchanged. This merged file retains each source's distinct disease coverage, but runs only one selected rule per disease code.

**Diagnosis scope:** The latest attached combined labels have 500 unique IDs, 493 `full` and 7 `partial`. Individual contributors disagree materially on classifications (particularly F1, C1, B4), so prevalence estimates are **not pooled or asserted as a consensus**. The counts below refer to the latest combined labels only; see the separate clash report for contributor differences.

**Decision principles:** minimize deletion of actual scientific content; preserve licences/attribution, Indic joiners and natural multilingual material; mask/private-data values never appear in this public medicine. ID-scoped remedies below are **specific to this diagnosis pack**, not transferable generic cleaning rules. The unused broad alternatives are discussed in the accompanying comparison report, not silently combined.

**Harm-test policy:** For 40 gold documents, at most `max(1, floor(40 × 1%)) = 1` changed-or-dropped document per rule, and for the combined run. **The gold set contains `eee25e81417bc1b7`, identified as `drop` in the corrected source labels; this contradiction must be adjudicated before Gate 2 evidence is accepted.** A pass tests collateral impact, not actual remediation recall.

## Source conflict resolution summary

| Code | Decision | Reason |
|---|---|---|
| **B4** | Conservative parameter tags only; preserve sample email addresses | jssunil proposal(s) reconciled |
| **B2** | Combine `<br>` and `<sup>/<sub>` on B2-labeled docs; avoid table stripping | both proposal(s) reconciled |
| **B5** | Retain balanced footnote wrapper candidate, restrict to diagnosed PDFs | patilvijay23 proposal(s) reconciled |
| **A1** | Conservative BOM/ZWSP removal; preserve ZWJ/ZWNJ and emoji presentation | patilvijay23 proposal(s) reconciled |
| **A6** | Exact documented OCR replacement; reject broad script transliteration | both proposal(s) reconciled |
| **C1** | Combine archive wrapper and label-aligned running headers; protect attribution | both proposal(s) reconciled |
| **C2** | Combine lead/paragraph dedup, restrict latter to diagnosed records | both proposal(s) reconciled |
| **C3** | Combine irreparable drop and label-aligned boundary repair | both proposal(s) reconciled |
| **C4** | Keep verified exclusions; reject silent “longest article” data loss | both proposal(s) reconciled |
| **D1** | Quarantine confirmed foreign-language documents; protect bilingual paragraphs | jssunil and original corrected source labels proposal(s) reconciled |
| **F1** | Quarantine confirmed private-person records; defer blanket telephone regex | both proposal(s) reconciled |
| **D3** | Explicit keep policy; D1 is separately verified | patilvijay23; clashes with D1 proposal proposal(s) reconciled |

## Measured harm and effectiveness evidence

**Independent local execution** against the original 500-document `sci-finepdfs.parquet` and the 40-ID gold snapshot; no simulated counts. Candidate blocks were parsed as Python, executed for each document, and re-applied in order with drop short-circuiting. These are **local equivalent-harness results**, not an official invocation of the repository's `harm_test.py` (unavailable locally). There were **zero rule errors**.

| Rule | 500-pack changed | 500-pack dropped | Gold changed | Gold dropped | Gold result |
|---|---:|---:|---:|---:|---|
| **B4** | 1 | 0 | 0 | 0 | **PASS** |
| **B2** | 10 | 0 | 0 | 0 | **PASS** |
| **B5** | 4 | 0 | 0 | 0 | **PASS** |
| **A1** | 0 | 0 | 0 | 0 | **PASS** |
| **A6** | 1 | 0 | 0 | 0 | **PASS** |
| **C1** | 9 | 0 | 0 | 0 | **PASS** |
| **C2** | 5 | 0 | 0 | 0 | **PASS** |
| **C3** | 4 | 1 | 0 | 0 | **PASS** |
| **C4** | 0 | 2 | 0 | 1 | **PASS** |
| **D1** | 0 | 2 | 0 | 1 | **PASS** |
| **F1** | 0 | 9 | 0 | 0 | **PASS** |
| **D3** | 0 | 0 | 0 | 0 | **PASS** |
| **ALL IN ORDER** | 32 | 12 | 0 | 1 | **PASS** |

The combined run changed **32** documents and dropped **12** of 500 (44 unique impacted documents). Against the gold set, it changed **0** and dropped **1** (one affected document, **2.50%**). This passes the **one-document allowance**, but **the affected gold document `eee25e81417bc1b7` is disputed** by the first-100 corrected labels. Consequently, do **not** treat this as a clean accepted gold set or final Gate 2 approval.

**Provenance:** full pack SHA-256 `5a3228b797f57234ad252fb89bf9a78c66084069540c6ac8564d062c313ea249`; gold snapshot SHA-256 `3632fe1cbecc62477830d23cb46df5b6543464a440d23f429593d5fe05da3e29`. Original source medicine SHA-256: patilvijay23 `85d8bdaf948739fa3c58099745febfb7a2cbf0b9fb7970e8c2efdb639b9b64b5`; jssunil `25cd811b74f2200664fad09266edff4f848268f8ecaa7ffc62089c158e7882af`; latest combined labels `332b0c689cf33336a44e31826967202ff1dbbe7fccc189b59951d7b2ff7a7f71`. This revised medicine has new code; do not reuse the earlier individual-medicine code hashes as evidence of this merged version.

**Reproduce through the official runner** from the repo root (edit paths as needed):

```bash
python -I teams/01-data-a/tools/harm_test.py \
  --pack /path/to/sci-finepdfs.parquet \
  --gold teams/01-data-a/gold/sci-finepdfs_gold.csv \
  --rules /path/to/medicine_sci.md \
  --rule all --show 10 --report /path/to/sci_merged_harm_report.json
```

**Interpretation:** measured gold preservation is not proof that all disease-positive records are repaired; a number of cures deliberately operate only on named documents, because the source medicines disagree on what is a disease. Check positive-case effectiveness and the unresolved reviewer disagreement before generalizing rules.


## Medicine 1 — B4: Template/converter placeholders

1. **Disease:** B4; **1 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `6d2428a3ad8e41d6`: synthetic placeholder in prose
   - `507d7cf0978d22e4`: repeated upstream email placeholder
   - `50cc681aabd3d82b`: template-like email marker

2. **Medicine:** Convert only unmistakably unexpanded conversion placeholders outside code fences. Do not globally replace valid example.com/example.org sample emails, despite their B4 labels in the second medicine.

   ```python
   import re
   _SCI_B4_TEMPLATE = re.compile(r'<(?:parameter\s+\d+|function name|process description|see attached)>',re.I)
   def cure_b4(text):
       """Remove only clearly unexpanded converter labels, not email@example.org examples or C++ templates."""
       inside=False;out=[]
       for line in text.splitlines(keepends=True):
           if line.lstrip().startswith("```"):
               inside=not inside
               out.append(line)
           else:
               out.append(line if inside else _SCI_B4_TEMPLATE.sub('',line))
       return ''.join(out)
   ```

3. **Action:** Fix narrow literal placeholders.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **1 changed / 0 dropped**, with 0 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** A broad synthetic-email rewrite touches 121/500 and 47 clean-labeled documents in the other label sheet; disabled pending reconciliation.

---

## Medicine 2 — B2: PDF HTML extraction remnants

1. **Disease:** B2; **10 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `7ea84af3398cb3ed`: literal HTML break tag
   - `8854bf31b8eea361`: superscript tag
   - `aa241f145eca058d`: superscript markup

2. **Medicine:** Combine line-break conversion with explicit sup/sub conversion, restricted to currently B2-labeled records; preserve code fences and do not remove table structure.

   ```python
   import re
   _SCI_B2_SUP=re.compile(r'<sup>([^<>\n]{1,80})</sup>',re.I)
   _SCI_B2_SUB=re.compile(r'<sub>([^<>\n]{1,80})</sub>',re.I)
   _SCI_B2_BR=re.compile(r'<br\s*/?>',re.I)
   _SCI_B2_IDS=frozenset({
       '7ea84af3398cb3ed','8854bf31b8eea361','aa241f145eca058d',
       '2b60daba400d7754','dee17bbf6dbc6934','459ba80b6a72a94b',
       '5b00bd0c69474a20','529fa3c1ef7d84f7','90eed038a1c69a07',
       '4df574fabee17f47'
   })
   def cure_b2(doc):
       """Repair known B2-positive PDF extraction artifacts, preserve code fences and table structure."""
       if doc['doc_id'] not in _SCI_B2_IDS:
           return doc['text']
       inside=False;out=[]
       for line in doc['text'].splitlines(keepends=True):
           if line.lstrip().startswith('```'):
               inside=not inside;out.append(line);continue
           if inside:out.append(line);continue
           line=_SCI_B2_SUP.sub(r'^\1',line)
           line=_SCI_B2_SUB.sub(r'_\1',line)
           line=_SCI_B2_BR.sub('\n',line)
           out.append(line)
       return ''.join(out)
   ```

3. **Action:** Fix reviewed markup artifacts.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **10 changed / 0 dropped**, with 10 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The broad version touches four documents labeled clean in the consolidated labels; ID scope prevents unverified edits.

---

## Medicine 3 — B5: Broken LaTeX footnote wrappers

1. **Disease:** B5; **18 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `80c340aef304a24c`: footnote wrapper
   - `d7a3e129dcd9c041`: PDF-extracted footnote
   - `ae0c958288200e55`: footnote wrapper

2. **Medicine:** Unwrap only balanced PDF-extraction footnotes in four labeled-positive documents; leave authentic LaTeX examples untouched.

   ```python
   def _sci_b5_balanced(text):
       """Unwrap complete, brace-balanced PDF-extracted LaTeX footnote commands.
       Keep unclosed footnotes, valid maths, and other TeX markup intact."""
       out, i = [], 0
       marker = "\\footnote{"
       while True:
           j = text.find(marker, i)
           if j < 0:
               out.append(text[i:])
               return "".join(out)
           out.append(text[i:j])
           k, depth = j + len(marker), 1
           while k < len(text) and depth:
               if text[k] == "{" and (k == 0 or text[k - 1] != "\\"):
                   depth += 1
               elif text[k] == "}" and (k == 0 or text[k - 1] != "\\"):
                   depth -= 1
               k += 1
           if depth:
               out.append(text[j:])
               return "".join(out)
           out.append(" (" + text[j + len(marker):k-1].strip() + ")")
           i = k

   _SCI_B5_IDS=frozenset({'80c340aef304a24c','d7a3e129dcd9c041','ae0c958288200e55','826838553e94b937'})
   def cure_b5(doc):
       """Restrict LaTeX-footnote wrapper conversion to diagnosed extraction artifacts."""
       if doc['doc_id'] not in _SCI_B5_IDS:
           return doc['text']
       return _sci_b5_balanced(doc['text'])
   ```

3. **Action:** Fix verified extraction artifacts.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **4 changed / 0 dropped**, with 4 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The general rule changes 15/500, including five labeled clean; narrow gating avoids unverified edits.

---

## Medicine 4 — A1: Invisible junk controls

1. **Disease:** A1; **8 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `b64c51d59247a36c`: emoji variation selector example (preserve when meaningful)
   - `d5f88477e272bd7c`: U+FE0F example (not removed)
   - `78687cb0dc7a4f80`: U+FE0F case (not removed)

2. **Medicine:** Remove U+FEFF and U+200B only; preserve U+200C/U+200D, presentation selectors, and legitimate Unicode.

   ```python
   def cure_a1(text):
       """Remove only unambiguous isolated zero-width spaces and BOM. Preserve
       ZWJ U+200D, ZWNJ U+200C, and emoji presentation selectors."""
       return text.replace("\uFEFF", "").replace("\u200B", "")
   ```

3. **Action:** Fix only these junk characters.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **0 changed / 0 dropped**, with 0 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** A general rule can still alter legitimate text; check other corpora separately.

---

## Medicine 5 — A6: Mixed-script OCR intrusions

1. **Disease:** A6; **9 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `12e943fb710cab5b`: spurious CJK run in Latin word
   - `f5faeb5d20b73087`: mixed character in source (unconfirmed replacement)
   - `cdc5973ec2161f44`: Cyrillic/Latin OCR mixture

2. **Medicine:** Keep the exact source-reviewed A6 substitution from patilvijay23; do not enable global Cyrillic transliteration or CJK deletion.

   ```python
   # Approved exact-example handling, not broad Latin/Cyrillic or CJK removal.
   A6_VERIFIED_EXACT = {
       "12e943fb710cab5b": ("smooth抽吸", "smooth"),
   }

   def cure_a6(doc):
       """Replace only an exact reviewed PDF intrusion in its known source.
       Unknown mixed-script words and natural Greek science notation are retained."""
       pair = A6_VERIFIED_EXACT.get(doc["doc_id"])
       if not pair:
           return doc["text"]
       return doc["text"].replace(pair[0], pair[1], 1)
   ```

3. **Action:** Fix the specific reviewed intrusion.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **1 changed / 0 dropped**, with 1 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The broader rule changes two documents currently marked clean and can turn a corrupted word into a different, still-incorrect word.

---

## Medicine 6 — C1: Repository covers and repeated page headers

1. **Disease:** C1; **28 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `33d1f7b3eec4d2c0`: publisher wrapper
   - `8c1aed2f8a439b91`: repeated running PDF header
   - `6dc622390a3f7207`: repeated copyright line (subject to attribution)

2. **Medicine:** Combine narrow attribution-aware repository-cover removal with repeated-header removal on six currently C1-labeled files; leave other repeated legal/form fields untouched.

   ```python
   import re

   # Matched only in the beginning of supported archive formats. Do not remove
   # licence/attribution-bearing covers without separately retaining attribution.
   C1_COVER_END = re.compile(
       r"To cite this version:\s*\n\s*\n[^\n]+\n"
       r"|des laboratoires publics ou priv\u00e9s\.\s*\n"
       r"|Reuse: Copies of full items[^\n]*\n"
       r"|MPRA Paper No\. \d+, posted [^\n]*\n"
   )
   C1_LICENSE_HINT = re.compile(r"(?i)creative commons|cc[- ]by|licen[sc]e|attribution|copyright")

   def _sci_c1_archive(text):
       """Remove a recognized, non-licence archive wrapper only when substantive
       text remains; keep covers bearing licence/attribution obligations."""
       head = text[:4000]
       matches = list(C1_COVER_END.finditer(head))
       if not matches:
           return text
       prefix = text[:matches[-1].end()]
       if C1_LICENSE_HINT.search(prefix):
           return text
       rest = text[matches[-1].end():].lstrip("\n")
       return rest if len(rest) >= 1000 else text

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


   def _sci_c1_running(text: str) -> str:
       return remove_running_headers(text)

   _SCI_C1_HEADER_IDS=frozenset({
    '8c1aed2f8a439b91','6bbcabe06c799acf','6dc622390a3f7207',
    'b01bfbf64f278c75','3994bec2f780bbc1','ca1b9ca315b5a0f5'
   })
   def cure_c1(doc):
       """Archive-cover cleanup plus diagnosed running headers; avoid arbitrary PDF-form deletions."""
       text=_sci_c1_archive(doc['text'])
       if doc['doc_id'] in _SCI_C1_HEADER_IDS:
           text=_sci_c1_running(text)
       return text
   ```

3. **Action:** Fix archive wrappers or label-aligned header candidates.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **9 changed / 0 dropped**, with 9 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The unrestricted header rule touches 54/500 including 18 currently clean-labeled documents; archival licence and attribution must survive.

---

## Medicine 7 — C2: Repeated lead passages and duplicate paragraphs

1. **Disease:** C2; **44 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `8c1aed2f8a439b91`: repeated lecture line
   - `f5faeb5d20b73087`: repeated long passage
   - `f48baf0b54a4e80f`: repeated letter

2. **Medicine:** Combine exact opening-lead detection with repeated long-paragraph removal only on currently C2-labeled files.

   ```python
   def _sci_c2_prefix(text):
       """Remove a long exact second copy of the opening passage near the start.
       Avoid global repeated-line deletion: PDF forms and tables legitimately repeat."""
       seed_len, min_repeat, search_limit = 64, 200, 2500
       if len(text) < 2 * min_repeat:
           return text
       seed = text[:seed_len]
       second = text.find(seed, seed_len, min(len(text), search_limit))
       if second < 0:
           return text
       matched = 0
       max_match = min(second, len(text) - second)
       while matched < max_match and text[matched] == text[second + matched]:
           matched += 1
       if matched < min_repeat:
           return text
       return text[:second] + text[second + matched:]

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


   def _sci_c2_paragraphs(text: str) -> str:
       return remove_repeated_passages(text)

   _SCI_C2_PARAGRAPH_IDS=frozenset({
    '80c340aef304a24c','b01bfbf64f278c75','f5faeb5d20b73087',
    'f48baf0b54a4e80f','78687cb0dc7a4f80'
   })
   def cure_c2(doc):
       """Long exact lead dedup and diagnosed duplicate-paragraph removal."""
       text=_sci_c2_prefix(doc['text'])
       if doc['doc_id'] in _SCI_C2_PARAGRAPH_IDS:
           text=_sci_c2_paragraphs(text)
       return text
   ```

3. **Action:** Fix verified duplicates without dropping structural repetitions.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **5 changed / 0 dropped**, with 5 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The unrestricted paragraph rule touches 17/500, including four currently clean-labeled documents, and can delete valid repeated legal forms.

---

## Medicine 8 — C3: Incomplete or truncated document

1. **Disease:** C3; **8 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `26a07693d706218f`: incomplete exam extract
   - `51a4fb599da754db`: incomplete opening
   - `6acc7c94105bdebd`: interrupted joined article

2. **Medicine:** Combine the irreparable-document exclusion from patilvijay23 with jssunil's boundary-based text repair restricted to four currently C3-labeled positive records.

   ```python
   C3_IRREPARABLE_IDS = frozenset({"26a07693d706218f"})

   def _sci_c3_drop(doc):
       """Exclude source-confirmed irreparable truncation (reviewed drop).
       Do not invent missing text or trim an unverified offset. Other C3 fixes
       still require a source-confirmed boundary outside this generic rule."""
       if doc["doc_id"] in C3_IRREPARABLE_IDS:
           return ("drop", "")
       return doc["text"]

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


   def _sci_c3_pattern(text: str) -> str:
       return repair_truncated_text(text)

   _SCI_C3_REPAIR_IDS=frozenset({
    '51a4fb599da754db','6acc7c94105bdebd','0e1f804b58f3527e','922071a2a0f07c79'
   })
   def cure_c3(doc):
       """Exclude irreparable C3 and repair narrowly diagnosed incomplete-format cases only."""
       if doc['doc_id'] in C3_IRREPARABLE_IDS:
           return ('drop','')
       if doc['doc_id'] in _SCI_C3_REPAIR_IDS:
           return _sci_c3_pattern(doc['text'])
       return doc['text']
   ```

3. **Action:** Drop verified irreparable fragment; repair diagnosed bounded fragments.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **4 changed / 1 dropped**, with 5 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** Broad lowercase-sentence and table-tail trimming can remove valid source text; no inference solely from metadata is permitted.

---

## Medicine 9 — C4: Unrelated documents concatenated

1. **Disease:** C4; **6 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `eee25e81417bc1b7`: mixed/unrelated content
   - `44f66c3734e3d5ca`: foreign/unrelated mixed record
   - `6acc7c94105bdebd`: other joined article (needs provenance split)

2. **Medicine:** Keep the two adjudicated irreparable-source drops. The alternate rule that returns the longest article is not enabled, because it would discard other article(s) without preserving provenance.

   ```python
   C4_IRREPARABLE_IDS = frozenset({
       "eee25e81417bc1b7", "44f66c3734e3d5ca",
   })

   def cure_c4(doc):
       """Exclude two source-reviewed, irreparably mixed records. Other joins
       need an approved boundary and provenance-preserving split; no blind split."""
       if doc["doc_id"] in C4_IRREPARABLE_IDS:
           return ("drop", "")
       return doc["text"]
   ```

3. **Action:** Quarantine only confirmed irreparable records.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 1 dropped** (2.50%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **0 changed / 2 dropped**, with 2 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** One excluded ID appears in the 40-row gold set and is disputed; multi-document splits require a pipeline that emits multiple traced records.

---

## Medicine 10 — D1: Incorrect language label

1. **Disease:** D1; **2 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `eee25e81417bc1b7`: Finnish content under English label
   - `44f66c3734e3d5ca`: Latvian content under English label
   - `1c686de5116ab261`: Lithuanian-language candidate from second reviewer

2. **Medicine:** Drop/quarantine two confirmed wrong-language first-100 records; do not delete foreign paragraphs from valid bilingual PDFs.

   ```python
   _SCI_D1_FOREIGN_LANGUAGE_IDS=frozenset({'eee25e81417bc1b7','44f66c3734e3d5ca'})
   def cure_d1(doc):
       """Quarantine confirmed wrong-language-label records pending proper re-routing."""
       return ('drop','') if doc['doc_id'] in _SCI_D1_FOREIGN_LANGUAGE_IDS else doc['text']
   ```

3. **Action:** Drop or re-route validated wrong-language records.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 1 dropped** (2.50%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **0 changed / 2 dropped**, with 2 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The unrestricted bilingual-filter rule changes six documents and can remove 26.35% of one; conflicts with D3 preservation.

---

## Medicine 11 — F1: Private-person information

1. **Disease:** F1; **103 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `b0d032fadb33dbf4`: direct private telephone at offset 7697
   - `73fbd40e1111121e`: residential address at offset 386
   - `b44b092b0e829a12`: private telephone at offset 86

2. **Medicine:** Quarantine nine confirmed private-value documents; do not run the broad phone regex on public corporate and institutional contact numbers. Other F1 labels need private-span approval.

   ```python
   # Confirmed private-person F1 examples from the corrected first-100 review.
   # Fail closed: quarantine these documents until a separate approved private-span
   # manifest enables complete redaction. A clean gold record is not inferred from
   # an F1 label. Only IDs (never private values) are present in this public rule.
   F1_QUARANTINE_IDS = frozenset({
       "b0d032fadb33dbf4", "73fbd40e1111121e", "b44b092b0e829a12",
       "854af92dbde41a63", "fb2ef557617d7ad1", "d1a387dea20a1242",
       "3b215cb29425e7d6", "8c2c1359b53f9442", "a6e70d0fef431172",
   })

   def cure_f1(doc):
       """Quarantine confirmed private-person records; never return unredacted text
       as though privacy remediation succeeded. Other IDs need separately approved
       redaction spans, or a separate quarantine decision before dataset release.
       """
       if doc["doc_id"] in F1_QUARANTINE_IDS:
           return ("drop", "")
       return doc["text"]
   ```

3. **Action:** Drop pending verified full-span privacy redaction.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **0 changed / 9 dropped**, with 9 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** The broad regex changes 74/500 including 30 currently clean-labeled documents; zero gold harm cannot establish private-value recall.

---

## Medicine 12 — D3: Natural mixed language

1. **Disease:** D3; **7 records** in the latest combined labels (not reconciled consensus). Examples by document ID (private values excluded):
   - `bfbe6f0f5d61c19e`: valid English/German passage
   - `f26a6a8bd745c1a2`: foreign institution name
   - `19c895320632e7b0`: bilingual academic/form example

2. **Medicine:** Preserve natural bilingual/quoted source text unchanged. Handle confirmed D1 wrong-language records separately.

   ```python
   def cure_d3(text):
       """Explicit preservation rule: natural language mixing is not corruption.
       A zero-change harm result does not establish cleaning efficacy."""
       return text
   ```

3. **Action:** Keep text for D3 alone.

4. **Harm test (merged, independently evaluated):** on 40 gold documents, **0 changed / 0 dropped** (0.00%); **PASS** under the TSAI one-document minimum. On the full 500 pack, **0 changed / 0 dropped**, with 0 affected docs bearing this code in the latest combined labels and 0 currently labeled clean. This is an independent local run, not a repository-harness execution.

5. **Side effects / unresolved clash:** A no-op gold PASS is not evidence of positive-case cleaning.

---

## Operational notes and release checks

- **Not a replacement for the annotation labels:** all original source labels and author contributions remain separate. Resolve the seven partial diagnoses and reviewer disagreements before claiming final pack prevalence or cleaning recall.
- **Data B/Indic protection:** no NFKC; no ZWJ/ZWNJ deletion. Scientific equations, table headings and genuine unicode markup remain protected.
- **Privacy:** any F1 documents not included in the nine explicit quarantine IDs are still gated for separate approved redaction or exclusion. A clean gold harm result does not certify privacy completeness.
- **Licence and attribution:** the C1 archive-cover rule has an attribution/licence guard; a global licence eligibility filter is a separate source-level gate.
- **C4 provenance:** the earlier source's “keep longest article” loses remaining article(s), so it is deliberately not used. To split one record into several outputs, use a separate sharding job with new provenance/IDs.
- **Scope of scoped rules:** several rule branches are limited to known positive `doc_id`s from this pack. Validate candidate content patterns on additional packs and independently reviewed positives before generalizing them.
- **Exact reproducibility:** official `harm_test.py --rule all` should be rerun locally after merge; an independent equivalent evaluation on the provided Parquet is reported above. Do not carry over the hashes or PASS claims from the separate source medicines.
