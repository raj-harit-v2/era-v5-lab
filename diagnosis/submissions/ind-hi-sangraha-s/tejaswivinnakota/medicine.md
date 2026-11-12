# Medicine sheet: ind-hi-sangraha-s (tejaswivinnakota)

The pack has 500 Hindi documents. The adopted labels contain D4 in 411 documents,
B4 in 31, B2 in 8, and A6 in 7. These counts overlap. No other disease occurs more
than five times.

I separate mechanical repairs from missing information. Broken punctuation and
recognisable tags can be repaired locally. A lost name, number, or original-script
spelling cannot be recovered by deleting the damaged token. Here, **drop means
quarantine from training until the source has been recovered**, not delete the
source file. A `fix` label can therefore require source-level work even when the
automatic rule quarantines the document.

The labels are model-assisted judgements adopted by me, not an independently
human-adjudicated reference set. The harm tests use the team's separate Hindi
gold set. No source Parquet file is modified.

## D4: broken abbreviations

1. **Disease:** D4, 411 documents. Three examples of the punctuation error this
   rule addresses are:
   - `5700b1ccb1a5ed64`, offset 19: `एफ।सी`
   - `ea9b683e28d08e16`, offset 1220: `यू।एस`
   - `fa3576b785b17bfd`, offset 2562: `पीएच।डी`

2. **Medicine:** replace the internal danda in a short allowlist of conventional
   abbreviations with a full stop. For example, `यू।एस` becomes `यू.एस`. Do not
   cross a newline, change single initials, alter spacing, or remove a trailing
   sentence-ending danda. Leave semantic translation errors for source comparison and
   retranslation. This is a partial remedy, not a claim to repair all 411 D4 rows.

   ```python
   import re
   import unicodedata

   _abbr = re.compile(
       r"यू[ \t]*।[ \t]*(?:एस|के|एन)|ई[ \t]*।[ \t]*यू|"
       r"बी[ \t]*।[ \t]*(?:ए|एस)|एम[ \t]*।[ \t]*(?:ए|एस)|"
       r"पीएच[ \t]*।[ \t]*डी|एफ[ \t]*।[ \t]*सी|"
       r"एस[ \t]*।[ \t]*एस|डी[ \t]*।[ \t]*सी"
   )

   def _word_char(char):
       return bool(char) and (
           unicodedata.category(char)[0] in "LMN"
           or char in "_\u200c\u200d"
       )

   def medicine_d4(text):
       positions = set()
       start = 0
       while (match := _abbr.search(text, start)) is not None:
           left = text[match.start() - 1] if match.start() else ""
           right = text[match.end()] if match.end() < len(text) else ""
           if not _word_char(left) and not _word_char(right):
               positions.update(
                   i for i in range(match.start(), match.end()) if text[i] == "।"
               )
           start = match.start() + 1
       return "".join("." if i in positions else char for i, char in enumerate(text))
   ```

3. **Action:** fix punctuation only. Retain the D4 finding if other translation
   errors remain. Names translated as ordinary nouns and missing measurements
   still require the original source; I would not reverse-translate them by rule.

4. **Harm test:** 31 October 2026, Hindi gold set of 272 documents. Changed
   **0/272**, dropped **0/272** (0.00% affected): **PASS**. No joiner or
   normal-form damage, and no execution errors. On the diagnosis pack, this rule
   changes punctuation in 19 of the 411 D4-labelled documents; 392 are untouched.

5. **Side effects:** a language lesson deliberately quoting malformed punctuation
   could be changed. Initials separated across clauses are missed deliberately.
   Correcting an abbreviation does not establish that its surrounding sentence
   is accurate.

## B4: unrecovered placeholders

1. **Disease:** B4, 31 documents. Examples:
   - `a285d1d618a6c203`, offset 49: `<unk> <unk> <unk>`
   - `faea12423891cfc0`, offset 173: `सूत्र _ 2`
   - `9fc6ddfa556b5dec`, offset 946: `आई. डी. 1.`

2. **Medicine:** quarantine documents containing an unknown-token marker, a
   numbered formula placeholder, or an unreplaced translation ID. Deleting these
   markers would conceal missing content. Recover the source and re-extract or
   retranslate it before admitting the document again. Do not guess the number,
   formula, or name that a marker replaced.

   ```python
   import re

   _placeholder = re.compile(
       r"<unk>|<ID[0-9]+(?:[>,]|(?=\s|$))|"
       r"(?<!\w)आई[ \t]*\.[ \t]*डी[ \t]*\.[ \t]*[0-9०-९]+(?!\w)|"
       r"(?<!\w)(?:सूत्र|फॉर्मूला|formula)[ \t]*_[ \t]*[0-9०-९]+(?!\w)",
       re.IGNORECASE,
   )

   def medicine_b4(text):
       return bool(_placeholder.search(text))
   ```

3. **Action:** drop/quarantine pending source recovery. This does not cover all
   B4 forms: missing table cells, empty titles, bare statistics, and damaged wiki
   layout need separate review. Ordinary numbers and the word `सूत्र` alone do
   not trigger the rule.

4. **Harm test:** 31 October 2026, Hindi gold set of 272 documents. Changed
   **0/272**, dropped **0/272** (0.00% affected): **PASS**. No joiner or
   normal-form damage, and no execution errors. On the diagnosis pack, this rule
   quarantines 25 documents: 18 of the 31 B4-labelled rows and 7 additional rows
   containing unreplaced translation IDs. The seven hits are not silently added
   to the adopted label sheet. The other 13 labelled B4 rows are not addressed.

5. **Side effects:** documentation that discusses `<unk>`, or legitimately names
   a variable `formula_1`, can be quarantined unnecessarily. The rule is intended
   for this extracted prose source, not code or tokenizer documentation. It
   sacrifices usable surrounding prose rather than silently retain missing facts.

## B2: translated HTML and XML residue

1. **Disease:** B2, 8 documents. Examples:
   - `8d4a1eb74b3a464c`, offset 54: `<पेरेंटिड> 1151694113 </पेरेंटिड>`
   - `94f9ac0d9c39d021`, offset 289: `<बी. आर.>`
   - `ede046aff8410b34`, offset 1694: `<रेफ नाम =`

2. **Medicine:** turn recognised line-break tags into newlines; remove complete
   reference-tag delimiters while preserving their contents; remove standalone
   wiki-export metadata lines. Use a whitelist, not a general `<...>` deletion.
   An incomplete tag is left for review rather than consuming following prose.

   ```python
   import re

   _br = re.compile(r"<[ \t]*(?:br|बी\.[ \t]*आर\.)[ \t]*/?>", re.I)
   _ref = re.compile(r"</?(?:ref|रेफ)(?=[\s/>])[^<>\r\n]*>", re.I)
   _meta = (
       r"एनएस|पेरेंटिड|टाइमस्टैम्प|उपयोगकर्ता नाम|मॉडल|प्रारूप"
   )
   _metadata_line = re.compile(
       r"^[ \t]*<(" + _meta + r")>[^\r\n<>]*</\1>[ \t]*(?=\r?$)",
       re.MULTILINE,
   )
   _container_line = re.compile(
       r"^[ \t]*</?(?:संशोधन|योगदानकर्ता)>[ \t]*(?=\r?$)",
       re.MULTILINE,
   )

   def medicine_b2(text):
       text = _metadata_line.sub("", text)
       text = _container_line.sub("", text)
       text = _br.sub("\n", text)
       return _ref.sub("", text)
   ```

3. **Action:** fix the recognised markup. Preserve reference text, mathematical
   comparisons, unknown tags, and `<unk>` markers. B4 handles the last of these
   separately. No Unicode normalisation or general whitespace cleanup is applied.

4. **Harm test:** 31 October 2026, Hindi gold set of 272 documents. Changed
   **0/272**, dropped **0/272** (0.00% affected): **PASS**. No joiner or
   normal-form damage, and no execution errors. On the diagnosis pack, this rule
   changes all 8 B2-labelled documents and no other document. Other diseases in
   those documents remain separate findings.

5. **Side effects:** a tutorial showing these exact tags literally would change.
   Unexpected metadata tag names remain untouched. Text already lost during
   extraction is not restored by removing the wrappers.

## A6: inconsistent script within a name

1. **Disease:** A6, 7 documents. Examples:
   - `38ea6e7718826a61`, offset 512: `саfarikova`
   - `c5c3213f172cb0e2`, offset 358: `саминjonu`
   - `520dd0b10c215e87`, offset 11: `किंडलाइन (यिद्दीशः Кинелия, एक`

2. **Medicine:** quarantine two narrow, observable cases: a single word mixing
   Latin and Cyrillic letters, or a Cyrillic spelling immediately presented as
   Yiddish. Preserve ordinary Cyrillic and Greek glosses and Latin proper names.
   Do not map look-alike letters automatically: a Cyrillic letter's appearance
   does not determine the intended spelling.

   ```python
   import re
   import unicodedata

   _words = re.compile(r"[^\W\d_]+", re.UNICODE)
   _yiddish_cyrillic = re.compile(
       r"\(यिद्दीश[ः:][ \t]*[\u0400-\u04ff]"
   )

   def medicine_a6(text):
       if _yiddish_cyrillic.search(text):
           return True
       for match in _words.finditer(text):
           scripts = {
               unicodedata.name(char, "").split(" ", 1)[0]
               for char in match.group()
           }
           if "LATIN" in scripts and "CYRILLIC" in scripts:
               return True
       return False
   ```

3. **Action:** drop/quarantine for source recovery. The remaining A6 examples are
   whole foreign-script strings whose correctness requires source comparison.
   Script detection alone cannot tell a legitimate gloss from a garbled one.
   These cases stay unresolved; they are not automatically transliterated.

4. **Harm test:** 31 October 2026, Hindi gold set of 272 documents. Changed
   **0/272**, dropped **0/272** (0.00% affected): **PASS**. No joiner or
   normal-form damage, and no execution errors. On the diagnosis pack, this rule
   quarantines 3 of the 7 A6-labelled documents. The remaining 4 need source
   comparison; they are not declared repaired.

5. **Side effects:** a valid discussion of mixed-script identifiers or homoglyphs
   could be quarantined. Historical or intentionally nonstandard Yiddish
   transliteration may also be flagged. Hindi-English mixing across separate
   words does not trigger the rule.

## Test record

The Hindi gold index is from upstream commit
`2356b2bf1b090d669137422107ee695b4700cf50`: FW2 73 documents, HPLT 69,
IndicCorp 130, for 272 distinct documents. Every gold ID was matched to nonempty
text in the corresponding sample pack. The gold builder requires two clean,
full-read votes and no negative vote.

The official `teams\02-data-b\tools\harm_test_indic.py` from the same commit runs
each rule separately and then D4, B4, B2, A6 in that order. Its pass limit is at
most 1% affected, with a one-document allowance for small gold sets. At 272
documents, two affected documents pass and three fail. An affected document is
changed or dropped; joiner damage, normal-form damage, and execution errors also
fail the test. Every individual rule passed with 0 changed and 0 dropped gold
documents. The combined pipeline also passed with **0 changed, 0 dropped,
0 joiner failures, 0 normal-form failures, and 0 errors across 272 documents**.

The rules were also applied in memory to the diagnosis pack:

| Rule | Changed | Quarantined | Labelled rows reached |
|---|---:|---:|---:|
| D4 | 19 | 0 | 19 of 411 |
| B4 | 0 | 25 | 18 of 31 |
| B2 | 8 | 0 | 8 of 8 |
| A6 | 0 | 3 | 3 of 7 |
| Combined | 23 | 28 | Not additive: diseases overlap |

The combined run leaves 449 documents untouched. A punctuation or tag change
does not make a document clean if a semantic error remains. This distinction
matters particularly for D4: passing the harm test is not evidence that a
rule solves the whole disease.

All twelve example quotes and offsets were checked against the original pack.
Twenty-four focused checks cover positive cases, protected foreign names,
unknown markup, multiline boundaries, Indic joiners, and overlapping
abbreviations. Text-changing rules were also checked for idempotence and
Indic-script preservation on every document they changed in the diagnosis pack.
All four source Parquet files remained byte-identical.

To reproduce from a checkout containing the upstream commit above, with the
three downloaded packs in the indicated local directory:

```powershell
python teams\02-data-b\tools\harm_test_indic.py `
  --medicine diagnosis\submissions\ind-hi-sangraha-s\tejaswivinnakota\medicine.md `
  --pack ..\work\gold_packs\ind-hi-fw2.parquet `
         ..\work\gold_packs\ind-hi-hplt.parquet `
         ..\work\gold_packs\ind-hi-indiccorp.parquet `
  --gold-dir teams\02-data-b\gold --show 10
```

This is an interim gold set from three sources, not a guarantee about every
Hindi document. In particular, the test contains no clean Sangraha-S reference
rows. Before wider use, I would add source-matched clean examples, including
literal tag/token discussions and legitimate foreign-script names. The rule
definitions were not widened to repair semantic content merely to increase
coverage.
