# Medicine sheet: ind-sa-fw2 (dattatreyamanjunath)

Pack: 500 Sanskrit documents from FineWeb-2 (Devanagari). Labels: `labels.csv` (291 fix, 109 clean, 100 drop).

## How the diseases were found

1. **Reading:** every document read with the help of detectors. Long documents (over 2,500 characters) were read
   at the start, middle and end, and scanned in full by the detectors.
2. **Second reader:** the labels were compared with the other reader of this pack (PR 80). Their method (detectors,
   benchmark windows, and comparison with the crawled page) showed checks I had not run. I verified each of
   their findings in the text before adopting it. Adopted:
   - Itihasa benchmark overlap
   - lost ZWJ/ZWNJ
   - Latin letters glued to Devanagari
   - an orphan vowel sign
   - repeated lines
   
   Not adopted:
   - F1 on a FineWeb `@example` placeholder
   - G4 on SARIT's ASCII verse numbers (no sign that they were Devanagari in the source)
   - H3 on the Sanskrit Bible
3. **Live page comparison (G2, G3):** each document's web page was fetched on 30 Oct 2026 and compared with the pack
   text. Each site was fetched with an honest user-agent, robots.txt respected, at most one request every 2 s per site. Sites that refuse scripts were left out; nothing pretended to be a browser. 352 of 500 pages came back. The others: sanskritvarta.in returns 404 for all 41 articles, SARIT's server returned 502 for 44, robots.txt disallows 8, and the rest are gone or failed.
   - **G2:** in 20 documents the live page writes words of the same passage (the same 15 letters on each side) with a ZWJ or ZWNJ after a virama, where the pack has none. Only joiners between a virama and a consonant count, because only those change how the conjunct is drawn. PR 80 reports 51 such documents; the other 31 either could not be fetched or show no joiner today.
   - **G3:** in 6 documents the live page has Sanskrit paragraphs between lines that the pack keeps. Two lose the commentary after every verse; four lose a single paragraph. Gaps that only show up on blog pages (sidebars, other posts) and on Wikipedia (edited since the crawl) were not counted.
   - A live page can differ from the page as crawled. Every G2 and G3 row says so in its note.
4. **Benchmark overlap (F2):** windows of 40 Devanagari letters were matched against:
   - the Itihasa test split (`rahular/itihasa`, 11,698 Sanskrit sentences): 15 documents share at least one
     sentence, and 6 share 6 or more
   - FLORES Sanskrit (`google/IndicGenBench_flores_in`, `flores_sa_en_test`, 885 sentences): no overlap
5. **Pack-wide scans with no finding:**
   - A1 (invisible characters)
   - A2 (control characters)
   - B1 (HTML entities)
   - B3 (chat markers)
   - E2 (base64 and number blobs)
   - E3 (secrets)
   - Aadhaar and PAN numbers
   - H1 (exact duplicates)
   - NFC changes

   NFKC changes 17 documents, but only through `…` and Roman numerals, which are not damage.
6. **Codes:** every label uses the meaning in DISEASES.md section 2. An earlier version used four codes
   differently:
   - doubled virama was labelled G2; it is now A5, because it is the same word in two byte forms
   - legacy-font damage was labelled A3; it is now A6, because the font swaps letters for look-alikes
   - wiki markup was labelled B5; edit links are now C1 and other markup is B4
   - `{??}` markers and lost syllables keep A4, with a note: the pack has no U+FFFD

## How the harm tests were run

All harm tests use Data B's tool `teams/02-data-b/tools/harm_test_indic.py`.

- **Gold set:** `gold_indic.py` built it from the two readers of this pack (this sheet and PR 80): 68 documents
  that both readers read in full and marked `clean`.
- **Pass rule:** a rule passes when it changes or drops at most 1 document (1% of the gold set, or 1 document,
  whichever is more). The ZWJ/ZWNJ and normal-form audits must also pass.
- **ALL IN ORDER:** the tool also runs all rules one after another, as the cleaning step would.
- **F2 input:** the F2 rule needs the Itihasa test file. Set `ITIHASA_TEST_SN=/path/to/test.sn.csv`.
- **Command:**

```
python3 harm_test_indic.py --medicine medicine.md --pack ind-sa-fw2.parquet --gold-dir GOLD_DIR --show 5
```

- **Result:** Changed 1 of 68 (1.47%). Dropped 0 of 68 (0.00%). **PASS**

**Reach** is the number of documents that I labelled with the disease and that the rule changes or drops.

The sections follow the running order: drop rules on the raw text first, then line removal, then the truncation
check on the cleaned text, then character fixes, then masking.
G2 comes last because it is fixed in the extraction step, not in the text.

---

## Medicine 1: D4, machine-translated Sanskrit

1. **Disease:** D4, 56 documents. Each D4 row has the note "D4 judged by assistant, verify"; a fluent reader
   should confirm them.
   - `19ed8d7b0056741b`: `गृह्णातु।` at 52 (the Hindi filler `लीजिए` translated literally), and `जारीकृते` at 849.
   - `2d33ec2d9fc4e9db`: Hindi stem `दबावः` at 392, 4 markers.
   - `59a0682c9a80d27f`: wrong voice and gender, `केन्द्रसर्वकारेण स्थगितवती` at 90.
2. **Medicine:** drop a document that uses Hindi-only stems inside Sanskrit inflection three or more times.
   ```python
   _D = "ऀ-ॿ"
   _STEMS = ["जारी", "पीएम", "सीएम", "बयान", "मुताबिक", "दौरान", "हालांकि", "जरिये", "वायरल", "साझा", "कार्यवाही",
             "विडियो", "शूटिंग्", "माङ्गं", "दबाव", "सुनवायी"]

   def medicine_d4(text):
       hits = sum(len(re.findall(f"(?<![{_D}]){s}", text)) for s in _STEMS)
       return hits >= 3
   ```
3. **Action:** drop the document.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 10 of 56 labelled documents changed or dropped.
5. **Side effects:**
   - Most machine-translated pages in this pack come from one news site. The harm tool passes only the text, so a
     rule cannot drop by site. That is why the reach is low. A site rule at the crawl stage would catch the
     rest.
   - Learner Sanskrit with grammar errors, and machine translation from English, use no Hindi stems, so they are
     not found.
   - A Sanskrit article that quotes a Hindi statement three times is dropped.

## Medicine 2: A4, characters lost before release

1. **Disease:** A4, 6 documents. The pack has no U+FFFD. The loss shows as `{??}` markers, or as missing
   syllables.
   - `935e30775b66fab4`: `{??}रुणं` at 43354.
   - `605046c0f09bb50f`: `नक्तम{??}दञ्च{??}` at 90485, 3 markers.
   - `64a9b96746d003f8`: syllables lost, `विरराग्सुतर्पितः` at 1390.
2. **Medicine:** drop a document that contains U+FFFD or the `{??}` marker.
   ```python
   def medicine_a4(text):
       return "�" in text or "{??}" in text
   ```
3. **Action:** drop the document.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 2 of 6 labelled documents changed or dropped.
5. **Side effects:**
   - One marker in a 90,000-character commentary drops the whole text. A softer rule would cut only the marked
     sentence.
   - Syllables lost without a marker (4 of 6 documents) are not found.

## Medicine 3: G3, missing sections

1. **Disease:** G3, 16 documents.
   - `1323891568bac822`: the hymn starts at `॥ २ ॥`; verse 1 `भज गोविन्दं…` is missing.
   - `6d5604f350843975`: only the first half of every verse survives; 16 of 17 lines end in `।` and there is no `॥`
     anywhere.
   - `e2afa14616dded22`: starts mid-verse; the first half of verse 1 is missing.
2. **Medicine:** drop a hymn that starts at verse 2 with no verse 1 anywhere. Also drop a verse text where every line
   ends in a single danda, no `॥` appears and the lines are half-verse length.
   ```python
   _NO = re.compile(r"॥\s*([०-९\d]+)\s*(?:॥|$)", re.M)
   _DIG = str.maketrans("०१२३४५६७८९", "0123456789")

   def medicine_g3(text):
       n = [int(x.translate(_DIG)) for x in _NO.findall(text)]
       if len(n) >= 3 and n[0] == 2 and 1 not in n and _NO.search(text).start() < 600:
           return True
       lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 15]
       if len(lines) < 15 or "॥" in text:
           return False
       half = sum(1 for l in lines if re.search(r"[^०-९\d\s]\s*।$", l))
       numbered = sum(1 for l in lines if re.search(r"[०-९\d]\s*।$", l))
       short = sorted(len(l) for l in lines)[len(lines) // 2] <= 50
       return numbered == 0 and short and half / len(lines) >= 0.8
   ```
3. **Action:** drop the document.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 4 of 16 labelled documents changed or dropped. The live-page comparison found 6 more G3 documents, for example `d75fbb82c5df21b6`, which lost 15 commentary paragraphs (one after each Rigveda verse). A text rule cannot see a missing paragraph, so these need the page; that is the same fix as G2, in the extraction step.
5. **Side effects:**
   - A stotra whose first verse is unnumbered and whose second verse is numbered `॥ २ ॥` is dropped.
   - Sections that leave no numbering trace (an announced verse that never comes, missing endnotes) are not found.

## Medicine 4: F2, benchmark leak

1. **Disease:** F2, 7 documents.
   - **Itihasa test split (6 documents):**
     - `1871b6a4ca1aaec1`: 25 test sentences, first at 218.
     - `91abf9d2eaed3776`: 23 test sentences, first at 103.
     - `af88c6773d84ac11`: 8 test sentences, first at 236.

     These are SARIT Mahabharata chapters and one Medium post. The Itihasa benchmark is built from the same epics.
   - **Exam paper (1 document):** `ae4ef773730d602a`, an official CTET exam paper with its answer key.
2. **Medicine:** drop a document that shares 3 or more distinct sentences with the Itihasa test split. A sentence
   counts as shared when any 40-letter window of it (Devanagari letters only, no spaces or dandas) occurs in the
   document. Documents with 1 or 2 shared sentences are kept, because those are famous verses quoted everywhere.
   ```python
   import os

   _L = "ऀ-ॣ०-ॿ"
   _W, _STEP, _MIN = 40, 20, 3
   _INDEX = {}

   def _windows():
       if not _INDEX:
           path = os.environ.get("ITIHASA_TEST_SN")
           if not path:
               raise RuntimeError("set ITIHASA_TEST_SN to the Itihasa test.sn.csv file")
           with open(path, encoding="utf-8") as f:
               for k, line in enumerate(f):
                   n = re.sub(f"[^{_L}]", "", line)
                   if len(n) < _W:
                       continue
                   for j in range(0, len(n) - _W + 1, _STEP):
                       _INDEX.setdefault(n[j:j + _W], set()).add(k)
       return _INDEX

   def medicine_f2(text):
       index = _windows()
       n = re.sub(f"[^{_L}]", "", text)
       hit = set()
       for j in range(len(n) - _W + 1):
           hit |= index.get(n[j:j + _W], set())
       return len(hit) >= _MIN
   ```
3. **Action:** drop the document.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 6 of 7 labelled documents changed or dropped. The exam paper is not an Itihasa match; it needs a registry of exam papers.

   Without `ITIHASA_TEST_SN` the rule raises an error on every document, so the test fails instead of passing
   silently.
5. **Side effects:**
   - Any good chapter of the Mahabharata or Ramayana can share 3 sentences with the test split, so the rule drops
     part of the canon. That is the point of decontamination, but the loss is real.
   - Removing only the leaked verses would keep the rest of each chapter.
   - Other Sanskrit benchmarks (for example the IN22 test sets) were not checked.

## Medicine 5: C1, boilerplate

1. **Disease:** C1, 180 documents.
   - `6da72db6a95c25b8`: 27 blog-menu lines, first `Menu` at 0.
   - `76073b33992af5b6`: the stotranidhi footer `Did you see any mistake/variation…` at 621.
   - `903b4cc1c43738cd`: the wiki edit link `[सम्पादन]` at 5, 3 times.
2. **Medicine:** remove whole lines that match site boilerplate, and remove inline wiki edit links. The SARIT closing
   mark `श्रीः` is removed only as the last line, directly after a line that ends in `॥`.
   ```python
   _LINES = [r"^(Menu|Home|Newer Post|Older Post|Gallery|BASPS|marquee|Technical Details|BACK TO TOP)$",
       r"^(Read Also|Read More|Leave a Reply|Click Here|Archives|ReplyDelete|Reply|Delete|Share|Tweet|Email This|BlogThis!)$",
       r"^(Labels?|Categories|Posted by|Source):", r"Did you see any mistake/variation", r"Digitized by Google",
       r"Since you are not logged in", r"^% (Site access|Language|Text title|File name|Location|Author|Transliterated by|Proofread by|Description|Latest update|Send corrections)",
       r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), \w+ \d{1,2}, \d{4}$", r"^\d{1,2}:\d\d [AP]M$",
       r"^\|← ", r"→\|$", r"^इतर .*पश्यतु\s*[।|]?$", r"^\[(सम्पाद्यताम्|सम्पादयतु|सम्पादन)\]$", r"^— .*\(@\w+\) \w+ \d{1,2}, \d{4}$",
       r"^(सामग्री पर जाएँ|मुख्य मेन्यू|साइडबार पर जाएँ|छुपाएँ|ऊपर जाएँ|अधिक जानें|क्रियाएँ|उपकरण)$",
       r"^(ऋग्वेद|अथर्ववेद|यजुर्वेद|सामवेद) में .* संदर्भ मिले$", r"Copyright|©|All rights reserved",
       r"हम उम्मीद करते हैं आपको", r"^इसे भी पढ़ें"]
   _RX = re.compile("|".join(f"(?:{p})" for p in _LINES), re.I)
   _EDIT = re.compile(r" ?\[(सम्पाद्यताम्|सम्पादयतु|सम्पादन)\]")

   def medicine_c1(text):
       lines = [l for l in text.split("\n") if not _RX.search(l.strip())]
       if len(lines) >= 2 and lines[-1].strip() == "श्रीः" and lines[-2].rstrip().endswith("॥"):
           lines.pop()
       return _EDIT.sub("", "\n".join(lines))
   ```
3. **Action:** fix the text (remove the lines and links).
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 124 of 180 labelled documents changed or dropped.
5. **Side effects:**
   - A Sanskrit line that is exactly `Home` or `Source: …` goes.
   - A stotra that ends with `श्रीः` after its last verse loses it.
   - One-off boilerplate (author credits, English SEO titles, embedded tweets without a handle line) needs new
     patterns per site, so it is not reached.

## Medicine 6: C5, link and keyword lists

1. **Disease:** C5, 7 documents.
   - `eb2b252468aea92c`: an SEO keyword line at 0.
   - `aa8e369c2d562c48`: the SEO phrase `(Birthday wish to my wife Sanskrit)` 10 times, first at 34.
   - `23d7ef42db7cc671`: a list of `|👉…||Click Here|` links, from 1341.
2. **Medicine:** remove lines that end in `Click Here` or that are a bare URL.
   ```python
   _LINK = re.compile(r"Click Here\s*\|?$|^https?://\S+$", re.I)

   def medicine_c5(text):
       return "\n".join(l for l in text.split("\n") if not _LINK.search(l.strip()))
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 2 of 7 labelled documents changed or dropped.
5. **Side effects:** a bare URL that names the source of a quoted text is lost. Keyword lines and word clouds have
   no fixed shape, so they are not found.

## Medicine 7: D2, romanised Sanskrit

1. **Disease:** D2, 6 documents.
   - `7bc67301a58f3aec`: `tena … paThyate` at 829.
   - `76282692bca966da`: romanised lines from 88.
   - `8f8f2c783674d31f`: romanised lines from 311.
2. **Medicine:** remove whole lines written in Latin letters with IAST diacritics.
   ```python
   def medicine_d2(text):
       def roman(line):
           letters = [c for c in line if c.isalpha()]
           if len(line.strip()) < 25 or len(letters) < 10:
               return False
           lat = sum(1 for c in letters if c.isascii() or 0xC0 <= ord(c) <= 0x24F or 0x1E00 <= ord(c) <= 0x1EFF)
           return lat / len(letters) > 0.6 and bool(re.search(r"[āīūṛṝḷṃḥṅñṭḍṇśṣ]", line))
       return "\n".join(l for l in text.split("\n") if not roman(l))
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 4 of 6 labelled documents changed or dropped.
5. **Side effects:**
   - IAST that a learning page shows next to the Devanagari is removed even when a reader wanted it.
   - Romanisation without diacritics (`paThyate`, Harvard-Kyoto) is treated as English and handled by D3.

## Medicine 8: D3, Hindi or English mixed into Sanskrit

1. **Disease:** D3, 98 documents.
   - `8044a4531f5c6b29`: the Hindi line `tet-2014 अभ्यर्थियों के साथ…` at 335.
   - `3cbf9bd2ba360786`: the Hindi sentence `दूसरी ओर दक्षिण कन्नड़ जिला…` at 1116.
   - `f322929becc2d910`: a Hindi intro and outro, and English lines from 517.
2. **Medicine:** remove whole lines that are English, or Hindi. Hindi is recognised by function words that Sanskrit
   does not use (`है`, `में`, `नहीं`, `के`, …), and by the oblique plural `-ों` in words of two or more
   syllables. Lines under 25 characters, and glosses in brackets inside a Sanskrit sentence, are kept.
   ```python
   _HIN = set("है हैं था थे थी में और नहीं लिए गया गई हुआ होता होती करने किया करें ने को से का की के भी यह वह कि जो आप हम साथ वाले रहे रही".split())
   _ANCHOR = set("है हैं था थे थी में और नहीं लिए गया गई हुआ होता होती करने किया करें ने साथ वाले रहे रही".split())
   _C = "क-हक़-य़"

   def _lang(line):
       letters = [c for c in line if c.isalpha()]
       if len(line.strip()) < 25 or len(letters) < 10:
           return "short"
       lat = sum(1 for c in letters if c.isascii() or 0xC0 <= ord(c) <= 0x24F or 0x1E00 <= ord(c) <= 0x1EFF)
       dev = sum(1 for c in letters if "ऀ" <= c <= "ॿ")
       if lat / len(letters) > 0.6:
           return "san_Latn" if re.search(r"[āīūṛṝḷṃḥṅñṭḍṇśṣ]", line) else "eng"
       if dev / len(letters) > 0.6:
           w = re.findall("[ऀ-ॿ]+", line)
           obl = lambda x: x.endswith("ों") and len(re.findall(f"[{_C}](?!्)", x)) >= 2
           h = sum(1 for x in w if x in _HIN or obl(x))
           a = sum(1 for x in w if x in _ANCHOR or obl(x))
           if a >= 1 and h >= 2 and h / max(1, len(w)) >= 0.15:
               return "hin"
       return "san"

   def medicine_d3(text):
       return "\n".join(l for l in text.split("\n") if _lang(l) not in ("eng", "hin"))
   ```
3. **Action:** fix the text (remove the lines).
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 53 of 98 labelled documents changed or dropped. Most of the D3 documents the rule does not change have English words or acronyms inside
   Sanskrit sentences (`(electronic waste)`, `UNESCO`). That is natural code-mixing, which DISEASES.md says to
   label but not judge, so they are kept on purpose.
5. **Side effects:**
   - Marathi and Nepali lines are classed as Sanskrit.
   - A Sanskrit news line with several Hindi loanwords can be classed as Hindi.

## Medicine 9: H3, the same content in another language

1. **Disease:** H3, 9 documents.
   - `8425414f14a1f498`: the English translation `Sanskrit is the foundation to all…` at 357.
   - `f5661c3e611fef8b`: an English translation after every verse, from 386.
   - `b7d0ec485aed0bd6`: each sentence in Hindi, English and Sanskrit, from 0.
2. **Medicine:** the translations are whole lines in English or Hindi, so H3 uses the same line test as D3. It is
   listed separately so that each code has its own harm test.
   ```python
   _HIN = set("है हैं था थे थी में और नहीं लिए गया गई हुआ होता होती करने किया करें ने को से का की के भी यह वह कि जो आप हम साथ वाले रहे रही".split())
   _ANCHOR = set("है हैं था थे थी में और नहीं लिए गया गई हुआ होता होती करने किया करें ने साथ वाले रहे रही".split())

   def _translation(line):
       letters = [c for c in line if c.isalpha()]
       if len(line.strip()) < 25 or len(letters) < 10:
           return False
       lat = sum(1 for c in letters if c.isascii() or 0xC0 <= ord(c) <= 0x24F or 0x1E00 <= ord(c) <= 0x1EFF)
       if lat / len(letters) > 0.6:
           return not re.search(r"[āīūṛṝḷṃḥṅñṭḍṇśṣ]", line)
       w = re.findall("[ऀ-ॿ]+", line)
       h = sum(1 for x in w if x in _HIN)
       a = sum(1 for x in w if x in _ANCHOR)
       return a >= 1 and h >= 2 and h / max(1, len(w)) >= 0.15

   def medicine_h3(text):
       return "\n".join(l for l in text.split("\n") if not _translation(l))
   ```
3. **Action:** fix the text (keep the Sanskrit, remove the translation).
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 8 of 9 labelled documents changed or dropped.
5. **Side effects:** a translation for learners is lost, even when it is the purpose of the page. A Sanskrit Bible
   page is a translation too, but it has no other language in it, so it is kept. I did not label it H3.

## Medicine 10: C3, truncated documents

1. **Disease:** C3, 45 documents.
   - `046f85c956521bff`: a Wikisource scan page cut mid-verse, `…सच्छष्कुलीनास ।` at 1096.
   - `14ee406c9fcc5df9`: ends mid-sentence, `…एकेन वर्धयित्वा न्यूनीकरोतु,` at 1005.
   - `95def3e2f7070b5d`: ends mid-reference, `…॥ 5-192-` at 7138.
2. **Medicine:**
   - **Text rule:** after boilerplate and other-language lines are removed, drop a document whose last line
     (10 or more characters, mostly Devanagari) ends in a comma, an opening quote or bracket, or a hyphen right
     after a letter. A sentence never ends like that.
   - **Crawl rule:** 31 of the 45 documents are single Wikisource scan pages (namespace `पृष्ठम्:`). They start and
     stop mid-text, and the pipeline should drop them by URL. The harm tool passes only the text, so this rule is
     given as a helper and was checked separately: it matches 44 pack documents and 0 gold documents.

   ```python
   from urllib.parse import unquote

   def _scan_page(url):
       return "wikisource.org/wiki/पृष्ठम्:" in unquote(url)

   def medicine_c3(text):
       lines = [l.strip() for l in text.split("\n") if len(l.strip()) >= 10]
       if not lines:
           return False
       last = lines[-1]
       dev = len(re.findall("[\u0900-\u097F]", last))
       letters = sum(c.isalpha() for c in last) or 1
       return dev / letters > 0.6 and bool(re.search(r"(?:[,‘“(]|(?<=[\u0900-\u097F])-)\s*$", last))
   ```
3. **Action:** drop the document.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 6 of 45 labelled documents changed or dropped for the text rule. With the crawl rule, the reach is 32 of 45.
5. **Side effects:**
   - A closing quote typed as U+201C (`“`) looks like an opening quote, so one complete document (`da1ff98edc2a471c`) is
     dropped.
   - Truncation at a full stop or danda cannot be told apart from a real ending. A "no final punctuation" rule
     dropped 57 untruncated documents in this pack, mostly because of leftover footer lines, so it is not used.

## Medicine 11: B4, template and markup junk

1. **Disease:** B4, 20 documents.
   - `b54ef4486f508f61`: wiki link markup `[[लेखकः :|]]` at 106.
   - `a2b7155645205ec0`: page markers `[Page0477-a+ 38]` at 872.
   - `1eff130926635c9a`: edition page numbers glued to the text, `॥566` at 294 and `567भवतु` at 358.
2. **Medicine:**
   - Unwrap `[[link|text]]` to `text`.
   - Remove `{{…}}` templates, `'''` bold marks, `[PageNNNN-x+ NN]` page markers and `↩` footnote back-links.
   - Remove a page number of three or more digits that is glued to a danda or to a word.
   ```python
   _JUNK = [r"\{\{[^{}\n]*\}\}", r"'''", r"\[Page\d+-[a-z]\+ ?\d+\]", "↩"]

   def medicine_b4(text):
       t = re.sub(r"\[\[(?:[^|\]\n]*\|)?([^\]\n]*)\]\]", r"\1", text)
       for p in _JUNK:
           t = re.sub(p, "", t)
       t = re.sub(r"(?<=॥)\d{3,}(?=\s)", "", t)
       return re.sub(r"(?<=\s)\d{3,}(?=[क-ह])|(?<=[ा-्क-ह])\d{3,}(?=[क-ह])", "", t)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 9 of 20 labelled documents changed or dropped.
5. **Side effects:**
   - A number glued to a word that is meant to be there (a year written without a space) is removed.
   - Infobox table remnants (`|लेखकः||…|`) are not reached, because their shape differs page by page.

## Medicine 12: A5, the same text in two byte forms

1. **Disease:** A5, 43 documents. NFC normalisation repairs none of these forms.
   - `58b5cd30c9ab7965`: a doubled vowel sign, `सुखाभेेदेऽपि` at 5572.
   - `61cdf0be9f009325`: a doubled virama, `षट््षष्टित` at 4194, 3 times.
   - `ab89f68273cd1a34`: double danda written as two single dandas `।।`, 3 times from 3256, in a document that
     also uses `॥`.

   Other forms: `अ` + vowel sign written for the full vowel (`अा` for `आ`).
2. **Medicine:**
   - Join `अ` + vowel sign into the full vowel.
   - Remove a repeated identical vowel sign or virama.
   - In a document that already uses `॥`, replace `।।` with `॥`.

   A document that writes `।।` throughout is left alone: that is the writer's consistent choice, and three gold
   documents do it.
   ```python
   _FULL = {"ा": "आ", "ि": "इ", "ी": "ई", "ु": "उ", "ू": "ऊ", "ृ": "ऋ", "े": "ए", "ै": "ऐ", "ो": "ओ", "ौ": "औ"}

   def medicine_a5(text):
       t = re.sub("अ([ािीुूृेैोौ])", lambda m: _FULL[m.group(1)], text)
       t = re.sub("([ा-्ॢॣ])\\1+", r"\1", t)
       if "॥" in t:
           t = re.sub("।[ \t]?।", "॥", t)
       return t
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 41 of 43 labelled documents changed or dropped.
5. **Side effects:**
   - Two different stacked vowel signs (`ोि`) are OCR errors where the right letter is unknown, so they are not
     changed.
   - `। ।` that marks the end of two separate short sentences would become one `॥`.

## Medicine 13: A6, look-alike characters

1. **Disease:** A6, 153 documents.
   - `6da72db6a95c25b8`: `बुद्धि: वर्धते` at 382; U+003A COLON for U+0903 VISARGA.
   - `faa8d8f77429473d`: `पलायिता |` at 1726; U+007C VERTICAL LINE for U+0964 DANDA.
   - `8c013ba00a9f2d63`: `मूÞर्य` at 5094; U+00DE from an unmapped legacy font.

   Other forms:
   - `S` or `s` for avagraha (`कोSपि`)
   - Latin `I` for danda
   - Latin `o` for the abbreviation sign `॰` (`झo पाठः`)
   - Dravidian short vowel signs
   - Latin words glued to Devanagari words (`factजन्म`)
2. **Medicine:** replace each look-alike with the Devanagari sign, but only in a Devanagari context. Keep
   abbreviations (`डा:`) and labels before another script. Never touch `|table|` lines. Put a space between a
   Latin word of 3 or more letters and a Devanagari word.
   ```python
   _D = "ऀ-ॿ"
   _CONS = "क-हक़-य़"
   _MAT = "ा-ौॢॣ"
   _ABBR = re.compile(r"(?:^|[\s(])(डा|डॉ|प्रो|डो|श्री|सं|पृ|ई|क्र|पं|मो|फो|दू)$")

   def medicine_a6(text):
       def colon(m):
           before = text[max(0, m.start() - 6):m.start()]
           after = text[m.end():m.end() + 3].lstrip()
           if _ABBR.search(before) or (after and after[0].isalpha() and not "ऀ" <= after[0] <= "ॿ"):
               return m.group()
           return "ः"
       t = re.sub(f"(?<=[{_CONS}{_MAT}]):(?=[\\s।॥]|$)", colon, text)
       t = re.sub(f"(?<=[{_CONS}{_MAT}ंः])[Ss](?=[{_CONS}])", "ऽ", t)
       out = []
       for line in t.split("\n"):
           if not (line.startswith("|") or line.rstrip().endswith("|") and line.count("|") > 2):
               line = re.sub(f"(?<=[{_D}]) ?\\|\\|(?=\\s|$)", " ॥", line)
               line = re.sub(f"(?<=[{_D}]) ?\\|(?=\\s|$)", " ।", line)
           line = re.sub(f"(?<=[{_D}]) ?I(?=\\s*$|\\s+[{_D}])", " ।", line)
           line = re.sub(f"(?<=[{_D}])o(?=\\s)", "॰", line)
           line = re.sub(f"(?<=[A-Za-z]{{3}})(?=[{_CONS}])|(?<=[{_D}])(?=[A-Za-z]{{3}})", " ", line)
           out.append(line)
       return "\n".join(out).translate({0x0946: 0x0947, 0x094A: 0x094B, 0x0931: 0x0930})
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 120 of 153 labelled documents changed or dropped.
5. **Side effects:**
   - A colon in a Devanagari film or book title becomes a visarga (`पुष्पा: द राइज`).
   - Legacy-font swaps inside letters (`अलडूकारः` for `अलङ्कारः`, `न्त` → `त्त`) need a dictionary, so they are not
     repaired.
   - Tamil `உ`, `∫` and `$` for avagraha, and `..` for danda, are not covered.

## Medicine 14: G1, words cut at a vowel sign

1. **Disease:** G1, 12 documents.
   - `253e06e749a796be`: `लङ्क ागमनम्` at 290; a space before U+093E.
   - `29e6b806cfadcdeb`: `पदिश्य ोिक्षयि` at 1251.
   - `773d5497fe06d1fe`: an orphan vowel sign with no consonant, `--ाखागत` at 2682.
2. **Medicine:** no Devanagari word starts with a vowel sign, virama, chandrabindu, anusvara or visarga. Remove any
   space or line break in front of one.
   ```python
   def medicine_g1(text):
       return re.sub("(?<=[ऀ-ॿ])[ \t \n]+(?=[ा-ौॢॣँ-ः्])", "", text)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 6 of 12 labelled documents changed or dropped.
5. **Side effects:**
   - When the vowel sign itself is the OCR error, joining makes a wrong word. The word was already wrong.
   - An orphan sign after punctuation (`--ा`) cannot be repaired, because the lost consonant is unknown.
   - PDF spaces at a full consonant (`क बीरः`) look like real word breaks, so they are not covered.

## Medicine 15: C4, several news items joined

1. **Disease:** C4, 14 documents, all from daily news blogs.
   - `209cdb0931854e56`: a second item joined with no boundary, `साम्पत्तिकभारः न्यूनीक्रियते` at 977.
   - `875f86117f43fd90`: `कावेरी - तमिळनाटु` at 569.
   - `44866dbca538bc36`: titles fused to the previous item at 317 and 572.
2. **Medicine:** where one item's last danda runs into the next item's dateline (`…अकरोत्।चेन्नै >`), insert a
   paragraph break. This applies only in the middle of a line, not to a title fused to its own dateline.
   ```python
   def medicine_c4(text):
       def cut(m):
           start = text.rfind("\n", 0, m.start()) + 1
           return m.group(1) + ("\n\n" if m.start() - start >= 60 else "")
       return re.sub("([।!?])(?=[ऀ-ॿ][ऀ-ॿ ]{1,40}\\s?>)", cut, text)
   ```
3. **Action:** fix the text (separate the items).
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 1 of 68 (1.47%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 2 of 14 labelled documents changed or dropped.
5. **Side effects:** most joined items sit on separate lines with nothing to mark a new story. Those need the blog's
   post boundaries, which FineWeb-2 lost.

## Medicine 16: F1, personal data

1. **Disease:** F1, 8 documents. Only types and positions are given here, never values.
   - `788a3d1d099f2017`: an obfuscated email at offset 16883, twice.
   - `4aac5343e806c60e`: an obfuscated email at offset 9985, twice.
   - `540c84255a18f83d`: an obfuscated email at offset 16420, 3 times.

   The others are a phone number with a name, and names with a postal address.
2. **Medicine:** mask emails (including `name at gmail dot com`) and Indian mobile numbers.
   ```python
   _PHONE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}(?!\d)")
   _EMAIL = re.compile(r"[A-Za-z0-9._%+-]+\s*(?:@|\(at\)|\[at\]| at )\s*[A-Za-z0-9-]+\s*(?:\.|\(dot\)|\[dot\]| dot )\s*[A-Za-z]{2,}")

   def medicine_f1(text):
       t = _EMAIL.sub(lambda m: m.group() if "example." in m.group() else "<EMAIL>", text)
       return _PHONE.sub("<PHONE>", t)
   ```
3. **Action:** fix the text (mask the values).
4. **Harm test:** gold set of 68 documents (ind-sa-fw2 68); rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 68 (0.00%). Dropped 0 of 68 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Reach: 5 of 8 labelled documents changed or dropped.
5. **Side effects:**
   - `x at y dot z` can match English prose.
   - A ten-digit number that starts with 6–9 is masked.
   - Names with postal addresses need a named-entity model.
   - FineWeb's `@example.org` placeholders are kept.

## Medicine 17: G2, lost ZWJ and ZWNJ

1. **Disease:** G2, 20 documents. Found by comparing each document with its live web page (see the header).
   - `ee4a8fe553d8ac95`: 28 words, for example `शृङ्गात्` at 777. The page writes ZWJ after the virama.
   - `0b2c5bee9024bd39`: 12 words, for example `शृणुयादुद्गृण्हीयात्।` at 1147.
   - `af31c9128e5214fb`: 11 words, for example `भवसङ्क्रान्तिटीका` at 0.
2. **Medicine:** the joiners were lost when the page was turned into text, so the text alone cannot show where they
   were. The evidence comes from the live page: there the same passage holds the word with a joiner after the virama,
   which changes how the conjunct is drawn. The fix belongs in the extraction step: keep U+200C and U+200D when converting HTML to text, and never
   strip them in a normalisation step. A sketch for an extractor that removes "invisible" characters:
   ```python
   _INVISIBLE = "[​‎‏‪-‮⁠⁦-⁩﻿­]"   # no U+200C, no U+200D

   def _keep_joiners(page_text):
       return re.sub(_INVISIBLE, "", page_text)
   ```
3. **Action:** fix the text by extracting it again from the crawled page.
4. **Harm test:** the rule changes the extractor, not the text, so `harm_test_indic.py` reports "no rule in code" for
   G2. Its own joiner audit protects the other rules: no rule here changes the number of ZWJ or ZWNJ.
5. **Side effects:** ZWJ in emoji sequences and in Latin text is kept too. That is harmless.
