# Medicine sheet: ind-mr-sangraha-v (avnishbm)

Counts are documents among all 500 reviewed rows. Medicines operate on copies; the source pack is never modified.

## Interim gold harm-test status

The pack-specific gold snapshot in PR #161 is interim, not yet an approved final gold set. This test pins commit `74b28869841475189445e88dba7af4d8e57a537a`, file `teams/02-data-b/gold/ind-mr-sangraha-v_gold.csv`: 88 unique documents agreed clean by `avnishbm` and `patilvijay23`, all present in the untouched source parquet. Coverage is 88/500 pack documents.

Every medicine below changed 0, dropped 0, and affected 0/88 documents (0.00%), so each passes the at-most-1% harm threshold on this interim snapshot. With 88 documents, even one affected document would be 1.14% and fail.

A6 exercises an automatic text rule, while D3 is intentionally an identity function. B4, C1, C3, C4, C5, D4, and F1 require confirmed disease/action metadata; the clean gold rows supply no such actions, so their zero-impact result validates the application gate only—not a detector, recall, or repair quality. These results must be rerun if PR #161 changes or an approved/fuller gold set becomes available.

## A6: 14 documents

**Examples:**

- `208b033cb8584898`: A6: "व्यापाºयांकडे" at offset 781
- `b267d186731a10ca`: A6: "अधिकाºयांनी" at offset 1857
- `f9a0f6e9ea15b561`: A6: "दुसºया" at offset 917

**Proposed medicine:** Fix only the repeated OCR pattern `º` immediately before Devanagari `य`; replace it with `ऱ्`. Other A6 characters, such as a Latin letter inside a Marathi word, remain manual cases.

**Action:** fix a copy.

```python
import re

def fix_reviewed_ordinal_ocr(text: str) -> str:
    return re.sub(r"º(?=य)", "ऱ्", text)
```

**Side effects:** A legitimate ordinal indicator before Devanagari text would be changed; mixed-script cases outside this exact pattern are not fixed.

**Interim-gold harm test:** PASS for automatic exact-pattern rule — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## B4: 17 documents

**Examples:**

- `b799128067e71c2b`: B4: "\\n" at offset 97
- `d8ecdc20a3f919ac`: B4: "\\n" at offset 71
- `9f1dc749883b0947`: B4: "\\n" at offset 60

**Proposed medicine:** Convert a literal backslash followed by `n` into a real newline only in records confirmed as B4 serialization damage.

**Action:** fix a copy.

```python

def restore_literal_newlines(text: str, confirmed_b4: bool) -> str:
    return text.replace("\\n", "\n") if confirmed_b4 else text
```

**Side effects:** Source code, paths, regular expressions, or prose intentionally discussing `\n` would be damaged without the confirmation gate.

**Interim-gold harm test:** PASS for the confirmation gate; no action metadata exists on the clean gold rows — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## C1: 98 documents

**Examples:**

- `e14f9a0e6e8d1d9b`: C1: "Read Goa news in Marathi" at offset 741
- `2c66d24bfd6db2ef`: C1: "हे ही वाचाः\nसिद्धू मुसवाला आणि बंदूक कल्चरचा संबंध!" at offset 1082
- `e9320e666a90a129`: C1: "Read the latest agriculture news in Marathi" at offset 1069

**Proposed medicine:** Remove only reviewer-confirmed publisher, navigation, byline, or call-to-action spans. Apply offsets from right to left so earlier offsets remain valid.

**Action:** fix a copy.

```python

def remove_confirmed_spans(text: str, spans: list[tuple[int, int]]) -> str:
    result = text
    for start, end in sorted(spans, reverse=True):
        assert result[start:end] == text[start:end]
        result = result[:start] + result[end:]
    return result
```

**Side effects:** A span can be substantive in another document. Offsets must be independently confirmed against the untouched original.

**Interim-gold harm test:** PASS for the confirmation gate; no action metadata exists on the clean gold rows — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## C3: 19 documents

**Examples:**

- `10cfc7c874a1bb29`: C3: "जीवनाच्या व्याव" at offset 13635
- `7ac16bc32542abcd`: C3: "जिल्हा निहाय बी ए. ४ आणि ५ :\nअ. क्र." at offset 1175
- `1ed4c474f5729368`: C3: "ही कल्पनासुद्धां त्याच्या" at offset 8311

**Proposed medicine:** Do not invent missing text. Drop only documents whose beginning, ending, or internal passage was confirmed as unrecoverably truncated; retain punctuation-only cases for manual repair.

**Action:** drop confirmed unrecoverable documents.

```python

def handle_truncation(text: str, unrecoverable: bool) -> str | None:
    return None if unrecoverable else text
```

**Side effects:** A complete excerpt can look truncated outside its publication context, so automatic punctuation or sentence-ending heuristics over-drop valid text.

**Interim-gold harm test:** PASS for the confirmation gate; no action metadata exists on the clean gold rows — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## C4: 10 documents

**Examples:**

- `815eb112e94faf6e`: C4: "परिवहन सेवेत नव्याने" at offset 0
- `92031296bbaa7d1d`: C4: "Options are: 1.The business layer (Model logic)" at offset 319
- `f2b8c25ffbcc196c`: C4: "रशियातल्या फिफा विश्वचषक स्पर्धेच्या सामन्यात मेक्सिकोने जर्मनीला 1 - 0 ने पराभूत केले आहे." at offset 555

**Proposed medicine:** Drop a document only after review confirms two unrelated texts with no reliable boundary. If a source-verified boundary exists, split copies and preserve provenance instead.

**Action:** drop confirmed joined documents.

```python

def handle_joined(text: str, confirmed_join: bool) -> str | None:
    return None if confirmed_join else text
```

**Side effects:** News roundups, bulletins, related sidebars, and book chapter transitions may legitimately contain several topics.

**Interim-gold harm test:** PASS for the confirmation gate; no action metadata exists on the clean gold rows — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## C5: 9 documents

**Examples:**

- `f0b421e314af77d6`: C5: "इप्सा इलेक्ट्रिक ब्रेस्ट पंप , डबल एल्व्ही पंप , मॅन्युअल हँड ब्रेस्ट पंप" at offset 193
- `eef6cb9d0cdb616f`: C5: "राष्ट्रवादी कुणाची?" at offset 793
- `ed35a697664a3098`: C5: "Mankind Pharma Share Price ।" at offset 1986

**Proposed medicine:** Drop pages confirmed to contain only keyword/headline/link lists. When an article body exists, remove only the confirmed navigation span.

**Action:** drop link-only pages; otherwise fix a copy.

```python

def handle_link_list(text: str, link_only: bool) -> str | None:
    return None if link_only else text
```

**Side effects:** Ordinary tables of contents, schedules, bibliographies, and substantive lists can resemble link spam.

**Interim-gold harm test:** PASS for the confirmation gate; no action metadata exists on the clean gold rows — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## D3: 77 documents

**Examples:**

- `e14f9a0e6e8d1d9b`: D3: "Read Goa news in Marathi" at offset 741
- `a3ae0a2e9168261e`: D3: "किमुक्तम् । तत्र व्यपदेशिवद्वचनमेकाचो" at offset 0
- `e9320e666a90a129`: D3: "(Agriculture Produce Market Committee Election)" at offset 63

**Proposed medicine:** Preserve natural code switching, names, quotations, acronyms, and technical terms. Remove a mixed-language span only when it is independently confirmed as C1/C5 clutter.

**Action:** retain text unless another disease supplies a safe fix.

```python

def preserve_contextual_mixing(text: str) -> str:
    return text
```

**Side effects:** Blanket English removal or translation destroys legitimate Marathi usage. D3 is descriptive and requires contextual review.

**Interim-gold harm test:** PASS for the intentional identity medicine — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## D4: 28 documents

**Examples:**

- `61b2c25e9513730b`: D4: "काय माजी कर्मचारी किराणा दुकान येथे माजी ग्राहक धावा आणि एक व्यवसाय कार्ड बाहेर हात?" at offset 2793
- `58d805ccc888c274`: D4: "ेसिंधुदुर्ग" at offset 416
- `994056d70dd415f8`: D4: "मद्ददाश्चर्य" at offset 1634

**Proposed medicine:** Do not guess a translation. Drop only documents with pervasive confirmed broken grammar; repair isolated errors manually when the intended Marathi is unambiguous.

**Action:** drop pervasive cases; manually fix isolated cases.

```python

def handle_bad_translation(text: str, pervasive: bool) -> str | None:
    return None if pervasive else text
```

**Side effects:** OCR damage, speech-recognition errors, dialect, archaic Marathi, and awkward original writing can be mistaken for machine translation.

**Interim-gold harm test:** PASS for the confirmation gate; no action metadata exists on the clean gold rows — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.

## F1: 18 documents

**Examples:**

- `fab4928039a870ab`: F1: private-person address at offset 9
- `8924481cb3403322`: F1: private-person residential address at offset 333
- `3532a8bbeeb1e5fe`: F1: identifiable private-person medical information at offset 49

**Proposed medicine:** Redact only confirmed private spans using private start/end metadata; public evidence continues to expose only the type and starting offset.

**Action:** fix a copy by redaction.

```python

def redact_confirmed(text: str, spans: list[tuple[int, int]]) -> str:
    result = text
    for start, end in sorted(spans, reverse=True):
        result = result[:start] + "[REDACTED]" + result[end:]
    return result
```

**Side effects:** Names, dates, public officials, organization contacts, and public-event locations must not be redacted merely because they match a broad pattern.

**Interim-gold harm test:** PASS for the confirmation gate; no private spans exist on the clean gold rows — changed 0, dropped 0, affected union 0/88 (0.00%). Gold snapshot and limitations are recorded above.
