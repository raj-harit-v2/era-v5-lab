# Medicine sheet: sci-finepdfs — consolidated pack medicines (harm-test executable)

> **Status: ALL TEN MEDICINES REVIEWED AND EXECUTABLE; GOLD-SET HARM TEST REPORTED PASS (10 RULES AND COMBINED RUN).** All ten rules and `ALL IN ORDER` passed against 40 current `sci-finepdfs` gold documents, with 0 changes and 1 drop in the combined run (1 allowed). The combined label CSV still has 107 `read=partial` rows; this gold-safety result does not certify complete diagnosis, cleaning effectiveness, privacy recall, gold eligibility, or release readiness.

**Combined labels SHA-256:** `6c5071704ad10b1659c26580ca859825774f41d35f19b03843716b210762677e`.

**Scope and eligibility:** There is no cleaning proof in these labels. Licence eligibility, attribution, provenance and Team 9 decontamination are separate mandatory gates. Never remove licence/CC-BY-SA attribution as boilerplate. Preserve ZWJ/ZWNJ and long-context documents after safe fixes.

**Execution contract:** Each section has one `**Disease:** CODE` line and a standalone Python block defining `cure_<code>` (or a safe narrow function with that name). `cure_f1`, `cure_c3`, `cure_c4` accept `doc` so the harness can apply verified document-ID decisions. All other functions accept `text`, except `cure_a6` which is also ID-scoped. No function uses unverified full-text restoration or prints sensitive data.

## Gold-set harm-test results — reported user run

The following values are transcribed from the supplied **`harm_test.py --rule all` output** for this medicine. They were **not independently rerun** while preparing this document. The `code sha256` is the hash reported by the harness for the extracted executable rules; changing only this Markdown report does not alter the embedded Python rules.

**Run inputs and acceptance policy:**

- **Pack:** `sci-finepdfs.parquet`
- **Gold:** `sci-finepdfs_gold.csv`, **40 documents**
- **Rules file:** `medicine.md`; **10 executable rules**
- **Reported code SHA-256:** `50d601469b6bd74f17e81fdf1210aeab466b739e522a66ab318359296ee34c13`
- **Allowed gold harm:** at most **1 document changed or dropped**, `max(1, floor(1% × 40)) = 1`
- **Reported overall result:** **PASS** (exit status not separately supplied)

| Rule | Changed | Dropped | Gold affected | Harness result |
| --- | ---: | ---: | ---: | --- |
| F1 | 0 | 0 | 0.00% | **PASS** |
| C1 | 0 | 0 | 0.00% | **PASS** |
| C2 | 0 | 0 | 0.00% | **PASS** |
| C3 | 0 | 0 | 0.00% | **PASS** |
| C4 | 0 | 1 | 2.50% | **PASS** |
| B2 | 0 | 0 | 0.00% | **PASS** |
| B5 | 0 | 0 | 0.00% | **PASS** |
| A1 | 0 | 0 | 0.00% | **PASS** |
| A6 | 0 | 0 | 0.00% | **PASS** |
| D3 | 0 | 0 | 0.00% | **PASS** |
| **ALL IN ORDER** | **0** | **1** | **2.50%** | **PASS** |

**Why 2.50% passes:** The current TSAI policy sets a *minimum one-document allowance* for a nonempty small gold set. Although 1/40 = 2.50%, only one document was affected, so C4 and `ALL IN ORDER` pass the `max(1 document, 1%)` criterion.

**Limits of this result:** This establishes the recorded gold-set behavior of the *loaded rules*, not that they successfully repair all disease-positive records. In particular, F1's zero gold impact does not certify redaction completeness; the D3 keep rule is intentionally a no-op. The current gold CSV contains ID `eee25e81417bc1b7`, which the corrected first-100 labels instead mark `drop`; **that conflict must be resolved before using this gold file as accepted Gate 2 evidence**. Do not alter the rule or the source labels merely to improve the pass metric.

**Reproduction command** (adjust file paths in your checkout):

```bash
python -I teams/01-data-a/tools/harm_test.py \
  --pack /path/to/sci-finepdfs.parquet \
  --gold teams/01-data-a/gold/sci-finepdfs_gold.csv \
  --rules diagnosis/submissions/sci-finepdfs/<github-handle>/medicine.md \
  --rule all
```

---

## Coverage and disease inventory

| Code | Full-read source diagnoses | All labelled/candidate rows | Consolidation decision |
|---|---:|---:|---|
| F1 | 101 | 102 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| C2 | 44 | 45 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| C1 | 25 | 26 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| B5 | 18 | 18 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| C3 | 7 | 13 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| B2 | 10 | 10 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| A6 | 9 | 9 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| A1 | 8 | 8 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| D3 | 7 | 7 | Full medicine; gold harm PASS; positive-case effectiveness pending |
| C4 | 4 | 6 | C4 gold harm PASS (1/40 dropped); positive-case boundaries still require verification |
| C5 | 1 | 3 | Below five full-read records — document-level handling only |
| D1 | 2 | 2 | Below five full-read records — document-level handling only |
| E4 | 2 | 2 | Below five full-read records — document-level handling only |
| A3 | 1 | 1 | Below five full-read records — document-level handling only |
| B3 | 1 | 1 | Below five full-read records — document-level handling only |
| B4 | 1 | 1 | Below five full-read records — document-level handling only |
| D4 | 1 | 1 | Below five full-read records — document-level handling only |

**Count caveat:** these are *reported label codes*, not independently verified disease prevalence. In particular, the 201–300 sheet uses F1 for names without reliable private-person evidence; automated 301–400 findings are preliminary. A document can count under multiple codes.

**Missing/invalid source labels:** physical row 162 has no earlier submission, five 201–300 fix/drop labels lacked any disease code, and three 101–200 `clean` rows erroneously carried D3. All were flagged and reconciled conservatively in the combined CSV; original source files remain unchanged. Details in the QA report.

---
## Medicine 1 — F1: Private-person information

1. **Disease:** F1 — 101 documents among existing full-read source labels, 102 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `b0d032fadb33dbf4` — individual direct telephone, offset 7697
   - `73fbd40e1111121e` — person-linked residential address, offset 386
   - `b44b092b0e829a12` — private direct telephone, offset 86

2. **Medicine:** Quarantine an F1 document unless every private-person span is verified and completely redacted; preserve public/institutional contacts. The first-100 corrected medicine is authoritative for its nine F1 IDs. The 201–300 sheet also marked many names as F1 without offsets; those are candidate labels, not independently verified private information.

**Executable medicine (loadable by harm_test.py):**

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

3. **Action:** **Drop/quarantine** the nine explicitly confirmed F1 source IDs until complete verified redaction is available. Other F1-positive documents remain subject to the independent privacy-release gate; this function does not claim to sanitize them.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. The loaded rule was evaluated, but gold-set PASS measures collateral impact only, not positive-case repair coverage. For F1, separately verify complete private-data detection/redaction or quarantine; for C3/C4, verify source boundaries and the exact excluded IDs before release.

5. **Side effects:** Overbroad phone/address patterns mask business, university and government contacts; inadequate span length leaves private data exposed. Do not treat a zero-change gold result as proof of F1 recall.

---

## Medicine 2 — C1: Publisher/page boilerplate or archive cover

1. **Disease:** C1 — 25 documents among existing full-read source labels, 26 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `33d1f7b3eec4d2c0` — publisher wrapper, offset 0
   - `a243639493a0e633` — publication footer, offset 86104
   - `bfbe6f0f5d61c19e` — editorial header, offset 3622

2. **Medicine:** Remove only confirmed extraneous material: an archive cover where the paper title reappears, site navigation, or repeated non-content footer. Preserve attribution, CC-BY-SA licence terms, author metadata and research structure. The Kunal2016 medicine has narrow HAL/City/MPRA markers; do not replace it with a blanket copyright-line removal.

**Executable medicine (loadable by harm_test.py):**

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

def cure_c1(text):
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
```

3. **Action:** Fix verified external wrapper; otherwise keep.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. This measures protection of gold documents, not how many disease-positive documents were successfully corrected.

5. **Side effects:** Could remove scientific copyright/attribution, legal sections, publisher information, or actual footnotes. The broad copyright-line rule in the aneeshads reference is *not* approved as-is.

---

## Medicine 3 — C2: Nonstructural duplicated text

1. **Disease:** C2 — 44 documents among existing full-read source labels, 45 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `8c1aed2f8a439b91` — repeated lecture explanation, offset 6944
   - `3db737dca1122c53` — repeated outline, offset 1137
   - `0e4cfb3b81d67dc5` — fragment repetition, offset 2

2. **Medicine:** Remove only verified duplicate runs/pages with confirmed source boundaries. The reference medicine removes lines repeated >=4, but it also removed legitimate roll-call votes, form fields and recurring footnotes. Do NOT enable that broad rule without manual review and passing gold evidence.

**Executable medicine (loadable by harm_test.py):**

```python
def cure_c2(text):
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
```

3. **Action:** Fix verified duplicates; drop a source only if it consists entirely of unusable repeated fragments.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. This measures protection of gold documents, not how many disease-positive documents were successfully corrected.

5. **Side effects:** Repeated mathematical definitions, forms, statute subsections, survey options, table headings and recurring signatures can be legitimate. A duplicate count alone is not sufficient.

---

## Medicine 4 — C3: Truncated or incomplete source text

1. **Disease:** C3 — 7 documents among existing full-read source labels, 13 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `51a4fb599da754db` — opening fragment, offset 0
   - `6acc7c94105bdebd` — second report incomplete, offset 9393
   - `26a07693d706218f` — incomplete practice-exam question, offset 1085

2. **Medicine:** Locate a demonstrably missing beginning/end or clipped fragment by original text position. Recover missing material from the source where possible; else trim only the verified fragment, keeping the coherent document. Never infer C3 solely from FinePDFs `is_truncated=true` or from a valid excerpt.

**Executable medicine (loadable by harm_test.py):**

```python
C3_IRREPARABLE_IDS = frozenset({"26a07693d706218f"})

def cure_c3(doc):
    """Exclude source-confirmed irreparable truncation (reviewed drop).
    Do not invent missing text or trim an unverified offset. Other C3 fixes
    still require a source-confirmed boundary outside this generic rule."""
    if doc["doc_id"] in C3_IRREPARABLE_IDS:
        return ("drop", "")
    return doc["text"]
```

3. **Action:** Drop the one verified irreparable C3 source ID. Other C3-positive sources require verified source-boundary repairs outside this general function.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. The loaded rule was evaluated, but gold-set PASS measures collateral impact only, not positive-case repair coverage. For F1, separately verify complete private-data detection/redaction or quarantine; for C3/C4, verify source boundaries and the exact excluded IDs before release.

5. **Side effects:** Trimming may remove references, equations, appendices or legal language. Invented completions are unacceptable; preserve long-context materials.

---

## Medicine 5 — C4: Unrelated documents/content joined

1. **Disease:** C4 — 4 documents among existing full-read source labels, 6 including partial-row candidates; executable conservative exclusion (threshold reached only including partial-row candidates). Three traceable examples (IDs and positions only):
   - `6acc7c94105bdebd` — unrelated second section, offset 7254
   - `06b18306786f56a5` — unrelated inserted passage, offset 2482
   - `6af2bcb11b896884` — image-inpainting explanation joined to unrelated arts essay (row 335)

2. **Medicine:** Split at source-confirmed boundaries and retain a traceable source ID for each resulting segment; preserve both if usable, otherwise retain the coherent component. Do not split at natural multilingual passages, magazine article boundaries, lawful annexes or PDF page transitions.

**Executable medicine (loadable by harm_test.py):**

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

3. **Action:** Drop the two confirmed irreparable joined-content source IDs; other C4 fixes need explicit boundary adjudication outside this rule.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 1 dropped (1/40 = 2.50%); the 40-document gold set allows at most one document changed or dropped. The loaded rule was evaluated, but gold-set PASS measures collateral impact only, not positive-case repair coverage. For F1, separately verify complete private-data detection/redaction or quarantine; for C3/C4, verify source boundaries and the exact excluded IDs before release.

5. **Side effects:** Automatic topic-switch rules split legitimate technical reports and mixed-language documents. Source provenance can be lost.

---

## Medicine 6 — B2: Literal HTML/XML tags in extracted prose

1. **Disease:** B2 — 10 documents among existing full-read source labels, 10 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `7ea84af3398cb3ed` — literal break tag, offset 445945
   - `8854bf31b8eea361` — superscript markup, offset 6674
   - `aa241f145eca058d` — superscript markup, offset 39648

2. **Medicine:** Convert only HTML fragments that are clearly extraction artifacts, such as verified `<br>` in running prose or explicit superscript markup. Preserve maths, code samples and genuine tags in quoted technical material.

**Executable medicine (loadable by harm_test.py):**

```python
import re
B2_BREAK = re.compile(r"<br\s*/?>", re.I)

def cure_b2(text):
    """Convert literal PDF-extraction line breaks in ordinary prose only.
    Do not replace escaped tags inside code fences or formula demonstrations."""
    if "<br" not in text.lower():
        return text
    inside_code = False
    out = []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            inside_code = not inside_code
            out.append(line)
            continue
        out.append(line if inside_code else B2_BREAK.sub("\n", line))
    return "".join(out)
```

3. **Action:** Fix only verified tags.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. This measures protection of gold documents, not how many disease-positive documents were successfully corrected.

5. **Side effects:** Removing tags broadly damages technical documentation and formulae; replacing `<br>` with a semicolon may join unrelated list items.

---

## Medicine 7 — B5: Broken Markdown or LaTeX

1. **Disease:** B5 — 18 documents among existing full-read source labels, 18 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `80c340aef304a24c` — LaTeX footnote wrapper, offset 21835
   - `d7a3e129dcd9c041` — footnote wrapper, offset 2392
   - `ae0c958288200e55` — footnote wrapper, offset 4087

2. **Medicine:** A source reference proposes changing LaTeX `\footnote{...}` wrappers into readable parenthesized footnotes, with brace balancing. A bare inline math command, valid LaTeX footnote, table or code block is not automatically broken: only transform confirmed extraction damage.

**Executable medicine (loadable by harm_test.py):**

```python
def cure_b5(text):
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
```

3. **Action:** Fix verified broken markup; otherwise retain genuine maths and LaTeX.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. This measures protection of gold documents, not how many disease-positive documents were successfully corrected.

5. **Side effects:** Overcorrection can change equations, real TeX examples, bibliography anchors and footnotes. Many flagged B5 cases in the 101–200 reference were deliberately left unchanged.

---

## Medicine 8 — A1: Invisible junk characters

1. **Disease:** A1 — 8 documents among existing full-read source labels, 8 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `b64c51d59247a36c` — variation selector near offset 92911 — verify whether genuinely junk
   - `d5f88477e272bd7c` — variation selector near offset 1606
   - `78687cb0dc7a4f80` — variation selector near offset 398301

2. **Medicine:** Allow only tightly-scoped removal of verified U+200B / BOM U+FEFF / problematic controls. Retain **ZWJ U+200D and ZWNJ U+200C**. Do not blindly erase emoji U+FE0E/U+FE0F as it changes presentation.

**Executable medicine (loadable by harm_test.py):**

```python
def cure_a1(text):
    """Remove only unambiguous isolated zero-width spaces and BOM. Preserve
    ZWJ U+200D, ZWNJ U+200C, and emoji presentation selectors."""
    return text.replace("\uFEFF", "").replace("\u200B", "")
```

3. **Action:** Fix verified invisible junk without removing Indic shaping marks.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. This measures protection of gold documents, not how many disease-positive documents were successfully corrected.

5. **Side effects:** Even invisible characters may have formatting significance; global removal of variation selectors changes emoji and symbol rendering.

---

## Medicine 9 — A6: Wrong/mixed script in a word

1. **Disease:** A6 — 9 documents among existing full-read source labels, 9 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `f5faeb5d20b73087` — CJK character embedded in Latin word near offset 11498
   - `12e943fb710cab5b` — CJK run embedded in Latin word near offset 882
   - `6324a2bb8fae9275` — Greek scientific notation reported but should be preserved

2. **Medicine:** The 101–200 reference proposes Latin/Cyrillic transliteration and small CJK-run deletion, but warns that it may corrupt names or words and should preserve Greek scientific notation. Use human-approved codepoint substitutions only.

**Executable medicine (loadable by harm_test.py):**

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

3. **Action:** Fix verified character confusables; otherwise keep scientific/quoted script.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. This measures protection of gold documents, not how many disease-positive documents were successfully corrected.

5. **Side effects:** Generic transliteration produces incorrect names and deletes source information. No script-change rule is approved for automatic release.

---

## Medicine 10 — D3: Natural or unintended mixed language

1. **Disease:** D3 — 7 documents among existing full-read source labels, 7 including partial-row candidates; full medicine (reported >5 full-read diagnoses). Three traceable examples (IDs and positions only):
   - `bfbe6f0f5d61c19e` — natural English/German passage, offset 6897
   - `f26a6a8bd745c1a2` — foreign institution name in otherwise valid source
   - `19c895320632e7b0` — Amharic/English bilingual prescription forms (row 366)

2. **Medicine:** Protect natural code-mixing and multilingual quotations; do not drop science PDFs simply for Spanish institution names, Chinese tables or English/local-language summaries. The reference D3 heuristic dropping texts with >50% non-English paragraphs is NOT accepted without human source-language review.
   **Executable keep rule:** preserves text and verifies that this disease alone never mutates the document; keep/verify policy is unchanged.

**Executable medicine (loadable by harm_test.py):**

```python
def cure_d3(text):
    """Explicit preservation rule: natural language mixing is not corruption.
    A zero-change harm result does not establish cleaning efficacy."""
    return text
```

3. **Action:** Keep valid multilingual content. Drop only separately verified wrong-language source via D1 decision.

4. **Harm test:** **PASS (reported `harm_test.py` run):** 0 changed and 0 dropped (0/40 = 0.00%); the 40-document gold set allows at most one document changed or dropped. This measures protection of gold documents, not how many disease-positive documents were successfully corrected.

5. **Side effects:** Word-list or script-share detectors misclassify untranslated quotations, code, named entities, linguistic studies and bilingual forms.

---

## Other low-count codes and cross-cutting safeguards

Codes not meeting the >5 fully reviewed document threshold are retained as **document-level findings, not automatic general cures**:

- **D1 (2 full-read; 2 total)** — Incorrect language label; verify dominant language and true source metadata before dropping. Two corrected first-100 foreign-language records are tagged drop; genuine multilingual texts are not automatically D1.
- **C5 (1 full-read; 3 total)** — SEO/book-download keyword/link spam. Source row 313 and 372 are clear preliminary candidates; require human confirmation before final drop. Do not drop catalogs or real references just for links.
- **E4 (2 full-read; 2 total)** — Repeated licence headers from code taxonomy; preserve copyright/reuse obligations, do not strip source attribution, and decide source eligibility independently.
- **B3 (1 full-read; 1 total)** — Ghost chat marker; high risk despite low count. Detect exact model-control tokens without deleting legitimate quotes.
- **B4 (1 full-read; 1 total)** — Template/code junk in prose; distinguish valid configuration examples and forms before treating as corruption.
- **A3 (1 full-read; 1 total)** — Mojibake; repair only when byte-faithful reversible mapping is established; log original byte positions, do not guess language.
- **D4 (1 full-read; 1 total)** — Bad machine translation; requires bilingual human review; do not rely on automatic grammar score.

**H2/H3 duplicate detection** is an independent dedup design and cannot be inferred from within-document repeated lines. **F2 benchmark contamination** needs Team 9 benchmark fingerprints, and is not certified absent by this label exercise.

## Exact safeguards carried forward from the first-100 reference

- Keep the four first-100 drop IDs exactly as diagnosed: `eee25e81417bc1b7`, `26a07693d706218f`, `0e4cfb3b81d67dc5`, `44f66c3734e3d5ca` (subject to the later gold conflict noted below). None is a corrected-first-100 F1 drop.
- The corrected first-100 review reports **22 non-dropped long-context candidates**, flagged `Long-context candidate — use for long context`. Keep coherent extended text after approved repairs; length alone is not a disease.
- F1 requires exact verified sensitive spans and complete privacy recall. Names, public government offices, professional correspondence, example domains and public organization contacts are not automatically private-person F1.
- Keep mathematics, scientific Greek notation, legitimate LaTeX, formula tables, repeated legal clauses, natural bilingual text, page numbering, and repeated form fields unless actual corruption is substantiated.
- Do not collapse `fix`/`drop` into success: proposed actions require an executed rule, a separate positive-case effectiveness check and an approved gold harm test.

## Current harm-test and Gate 2 status

- **Reported gold harm-test PASS:** all 10 individual rules and `ALL IN ORDER` passed on 40 gold documents. The combined result is 0 changed and 1 dropped (2.50%), which falls within TSAI's one-document allowance. Reported executable code hash: `50d601469b6bd74f17e81fdf1210aeab466b739e522a66ab318359296ee34c13`.
- **Gold eligibility issue remains:** the checked `g1-harm-test` branch gold set contains `eee25e81417bc1b7`, which the corrected first-100 source labels mark `drop`. Refresh/adjudicate gold membership before calling this Gate 2-certified evidence.
- **Rule scope:** all ten have callable `cure_<code>` functions. F1/C3/C4 are conservative ID-scoped quarantine/drop rules rather than unverified broad text repairs; D3 is an explicit keep rule. A harm PASS does not validate privacy recall, manual repair coverage or dataset release.
- **Next evidence:** complete the 107 partial-row reviews, resolve conflicting labels and gold eligibility, then rerun the same ten rules on refreshed gold and record IDs affected, counts, hashes and input provenance in `spec_v1/harm_tests.md`. Separately measure effectiveness on disease-positive documents.
- For release: preserve ZWJ/ZWNJ; licence gate accepts permissive and CC-BY-SA with attribution and allowed gpt-oss outputs, rejects NC/ND/unstated/untraceable and disallowed closed-model text.

## Reference provenance

- `labels(9).csv` SHA-256 `9d7bd631831e3efc0f28740d874321179c4720b04ea3f2da0d1db5cc3e988812`.
- `medicine(10).md` SHA-256 `a8ee7b8075e6f215ee469a8e904ed45d1665d0c1e0889f3b965ab4e349304dbe`.
- `sci-aneeshads-medicine.md` SHA-256 `e6601ebcee836fae2d673a1f0a8e308116d0037cf0f65b4226eaaccaa97b2a6d`.
- `sci-kunal2016-medicine.md` SHA-256 `379118e078cfa3235ef4ab9b825e437adaec8efded755ea90e248b9ebc7511ed`.
- `sci-aneesha-labels.csv` SHA-256 `8e2a6b569618caa16af33899f269a2a644eaa3f32008332bad9eb7686697e458`.
- `sci-smita-labels.csv` SHA-256 `99d5e835837472f72a4180d53765ce9e57b2dc40a8549bb6deba2e472daeafcd`.
- `sci-kunal2026-labels.csv` SHA-256 `769cd7026ebaebaa83c83ab6323a6762bc4db0a5949598083d88e02e91662a6b`.

**Finalization gate:** All ten reviewed medicine rules are loadable and the supplied CLI output reports a gold-harm **PASS** for every rule and their combined run. Dataset-wide release remains contingent on completing 107 partial labels, resolving the gold-set membership dispute, and demonstrating positive-case effectiveness plus licence/privacy safeguards.
