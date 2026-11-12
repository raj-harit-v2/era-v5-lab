# Medicine sheet: ind-mr-fw2 (adinathauti)

Pack: ind-mr-fw2 · Language: Marathi (Devanagari) · 500 documents

Diseases found more than 5 times: D3 (281), C3 (112), A5 (39), C2 (38), A1 (30), A3 (27), C1 (17), F1 (8).

---

## Medicine 1 — D3: Mixed language (281 docs)

1. **Disease:** D3 — Romanised or Latin-script words embedded in Marathi Devanagari text.
   Count: 281 / 500.
   Examples:
   - `00eed90bde196e9c` — headline starts with "How To Find Sweet Watermelon:"
   - `45099f1718f10018` — headline starts with "Lioness And leopard Fight Viral Video :"
   - `924d41c82dfe4138` — headline starts with "Viral Video:"

2. **Medicine:** This is natural code-switching in Marathi journalism — English proper nouns,
   brand names, and viral-content headlines routinely appear in Latin script alongside Devanagari.
   No removal or substitution is warranted; the mixing is not an error.
   Flag only (label D3); do not alter the text.

   ```python
   def has_d3(text: str) -> bool:
       import re
       deva  = sum(1 for c in text if 'ऀ' <= c <= 'ॿ')
       latin = len(re.findall(r'[a-zA-Z]{3,}', text))
       return deva > 50 and latin > 0
   ```

3. **Action:** fix — keep the document; no text change. The label records the mixing for
   downstream analysis but the document is not cleaned.

4. **Harm test:** Run on the Marathi gold set (`teams/02-data-b/gold/ind-mr-fw2_gold.csv`, 140
   documents) with `teams/02-data-b/tools/harm_test_indic.py`: **0 changed, 0 dropped (0.00%)**,
   ZWJ/ZWNJ counts preserved, NFC preserved — **PASS** (limit: 1.4 of 140). D3 is label-only (no
   text change), so it cannot alter or drop any gold document.

5. **Side effects:** None — the medicine is a no-op (label only).

---

## Medicine 2 — C3: Truncated document (112 docs)

1. **Disease:** C3 — Document ends mid-sentence with no terminal punctuation.
   Count: 112 / 500.
   Examples:
   - `a04bc6869aca8184` — ends `…कामाविषयी चर्चा झाली, अन्य नाही."` (quoted speech cut)
   - `626fc9159542b61c` — ends `Tags: Diabetes, Health, Health Tips, Lifestyle` (boilerplate tag list)
   - `5c05e18231a55839` — ends `महाराष्ट्र ठळक बातम्या | Maharashtra Times` (site footer)

2. **Medicine:** Drop any document whose text (after right-stripping whitespace) does not end
   with a recognised terminal character from the set:
   `.  !  ?  ।  ॥  "  "  '  …  —  –  ]  }  )  ⭕`

   ```python
   import re
   _TERMINAL = re.compile(r'[.!?\n"\'।॥…\]}\)""—–⭕]\s*$')

   def should_drop_c3(text: str) -> bool:
       return len(text) >= 200 and not _TERMINAL.search(text.rstrip())
   ```

3. **Action:** drop — a truncated document teaches the model that text can end anywhere.

4. **Harm test:** Run on the gold set (`teams/02-data-b/gold/ind-mr-fw2_gold.csv`, 140 docs) with
   `harm_test_indic.py`: **0 changed, 0 dropped (0.00%)** — **PASS** (limit: 1.4 of 140). Every gold
   document ends with a recognised terminal character, so the drop rule fires on none of them.

5. **Side effects:** Documents that end with a closing double-quote `"` (U+201D) may be
   incorrectly passed if the quoted sentence itself is truncated inside the quote. Also,
   boilerplate footers ending with a site name (no punctuation) will be correctly caught.

---

## Medicine 3 — A5: Wrong normal form (39 docs)

1. **Disease:** A5 — Devanagari characters stored in NFD or a mixed normal form instead of NFC.
   Count: 39 / 500.
   Examples:
   - `489da5c3b5d9ffe2` — nukta or matra written as a separate combining character
   - `8445992d98332735` — composed and decomposed forms of the same akshara appear in one doc
   - `3621f9c755f06081` — vowel sign stored as combining sequence instead of precomposed codepoint

2. **Medicine:** Apply NFC normalisation to the full text.

   ```python
   import unicodedata

   def fix_a5(text: str) -> str:
       return unicodedata.normalize('NFC', text)
   ```

3. **Action:** fix — normalise in place; the rendered text is identical but the byte sequence
   becomes canonical.

4. **Harm test:** Run on the real Marathi gold set of this pack
   (`teams/02-data-b/gold/ind-mr-fw2_gold.csv`, 140 documents — gold set present, not empty) with
   `harm_test_indic.py`: **0 changed, 0 dropped (0.00%)**, NFC preserved — **PASS** (limit: 1.4 of
   140). The gold text is already NFC, so NFC normalisation is a verified no-op on it.

5. **Side effects:** NFKC would additionally fold compatibility characters (e.g. Indic digits
   → ASCII digits), which is undesirable. NFC does not do this. Safe for Devanagari.

---

## Medicine 4 — C2: Repeated lines (38 docs)

1. **Disease:** C2 — The same non-empty line appears two or more times in one document.
   Count: 38 / 500.
   Examples:
   - `654e623661c0b8c6` — "सर्वात आधी वाचा विश्वासार्ह मराठी न्यूज वेबसाइट News18 लोकमतवर." repeated
   - `08dbb49c409f6de0` — section separator line repeated
   - `05b7b743f394e916` — footer line repeated

2. **Medicine:** Remove all duplicate occurrences of a line, keeping only the first.

   ```python
   def fix_c2(text: str) -> str:
       seen = set()
       out  = []
       for line in text.split('\n'):
           key = line.strip()
           if key and key in seen:
               continue
           seen.add(key)
           out.append(line)
       return '\n'.join(out)
   ```

3. **Action:** fix — remove the duplicate lines; keep the document.

4. **Harm test:** Run on the gold set (140 docs) with `harm_test_indic.py`: **0 changed, 0 dropped
   (0.00%)** — **PASS** (limit: 1.4 of 140). No gold document repeats a line, so no gold line is removed.

5. **Side effects:** Intentional repetition (e.g. a poem or a list with a repeated refrain)
   would be incorrectly de-duplicated. Rare in news prose.

---

## Medicine 5 — A1: Invisible junk characters (30 docs)

1. **Disease:** A1 — Zero-width space (U+200B), BOM (U+FEFF), soft hyphen (U+00AD), or
   Unicode bidi control characters present in the text.
   Count: 30 / 500.
   Examples:
   - `a04bc6869aca8184` — soft hyphen or ZWSP embedded in Devanagari word
   - `29f9f308afd0859e` — ZWSP between words
   - `00eed90bde196e9c` — BOM or bidi mark in headline

2. **Medicine:** Strip the offending invisible characters. ZWJ (U+200D) and ZWNJ (U+200C) are
   NOT removed — they are required for correct Devanagari/Hindi conjunct rendering.

   ```python
   import re
   _A1_RE = re.compile(
       r'[​﻿­'      # ZWSP, BOM, soft hyphen
       r'‪-‮'            # bidi embed/override
       r'⁦-⁩]'           # bidi isolate
   )

   def fix_a1(text: str) -> str:
       return _A1_RE.sub('', text)
   ```

3. **Action:** fix — strip the characters in place.

4. **Harm test:** Run on the gold set (140 docs) with `harm_test_indic.py`: **0 changed, 0 dropped
   (0.00%)**, ZWJ/ZWNJ preserved — **PASS** (limit: 1.4 of 140). No gold document contains the
   targeted invisible characters, so the strip is a verified no-op.

5. **Side effects:** A U+00AD soft hyphen used deliberately for line-breaking in long compound
   words would be removed, but this is acceptable — soft hyphens are a typographic hint, not
   semantic content.

---

## Medicine 6 — A3: Mojibake (27 docs)

1. **Disease:** A3 — UTF-8 Devanagari text that was decoded as Latin-1 or Windows-1252,
   producing sequences like `Ã¤`, `à¤¹`, `â€™`.
   Count: 27 / 500.
   Examples:
   - `97333df118ec5df2` — Devanagari script names for other languages appear as Latin garbage
   - `e1dc211abdf5bf39` — article body contains mojibake sequences mid-paragraph
   - `6169b09fe7801904` — mixed content with both clean Devanagari and mojibake spans

2. **Medicine:** Re-encode: decode the text as Latin-1, then re-encode as UTF-8 and decode again.
   Only apply if the document contains mojibake markers; otherwise leave unchanged.

   ```python
   import re
   _MOJI_RE = re.compile(r'[ÃÂ][\x80-\xBF]|â€[\x98-\x9E™]')

   def fix_a3(text: str) -> str:
       if not _MOJI_RE.search(text):
           return text
       try:
           return text.encode('latin-1').decode('utf-8')
       except (UnicodeEncodeError, UnicodeDecodeError):
           return text  # partial mojibake — leave for human review
   ```

3. **Action:** fix — attempt re-encoding; if it fails (partial mojibake), keep original and
   flag for manual review.

4. **Harm test:** Run on the gold set (140 docs) with `harm_test_indic.py`: **0 changed, 0 dropped
   (0.00%)** — **PASS** (limit: 1.4 of 140). No gold document carries mojibake markers, so the
   guarded re-encode never fires.

5. **Side effects:** A document with a genuine Latin-1 loanword that happens to match the
   mojibake pattern could be wrongly re-encoded. The guard regex is conservative; risk is low.

---

## Medicine 7 — C1: Boilerplate (17 docs)

1. **Disease:** C1 — Scraper-inserted footer lines: site navigation, "Tags:", newsletter
   prompts, and source attribution lines from Marathi news aggregators.
   Count: 17 / 500.
   Examples:
   - `626fc9159542b61c` — ends with `Tags: Diabetes, Health, Health Tips, Lifestyle`
   - `5c05e18231a55839` — ends with `Maharashtra News, Latest Maharashtra News in Marathi…`
   - `c8ad1802a6fbb058` — ends with `महाराष्ट्र ठळक बातम्या | Maharashtra Times`

2. **Medicine:** Strip trailing boilerplate lines that match known footer patterns.

   ```python
   import re
   _C1_FOOTER = re.compile(
       r'\n(?:Tags\s*:.*|'
       r'Maharashtra(?:Times)?\s*News.*|'
       r'.*News18.*लोकमतवर\.?|'
       r'.*विश्वासार्ह मराठी न्यूज.*|'
       r'.*ठळक बातम्या.*)\s*$',
       re.IGNORECASE
   )

   def fix_c1(text: str) -> str:
       return _C1_FOOTER.sub('', text).rstrip()
   ```

3. **Action:** fix — strip the footer lines; keep the document.

4. **Harm test:** Run on the gold set (140 docs) with `harm_test_indic.py`: **0 changed, 0 dropped
   (0.00%)** — **PASS** (limit: 1.4 of 140). No gold document ends in a matched footer line, so
   nothing is stripped.

5. **Side effects:** A news article that genuinely quotes a "Maharashtra Times" headline inside
   the body (not as a footer) would not be matched because the pattern is end-anchored. Safe.

---

## Medicine 8 — F1: Personal data (8 docs)

1. **Disease:** F1 — Personal data of private people: email addresses and phone numbers left in
   scraped article bodies (contact lines, "whatsapp", footers).
   Count: 8 / 500.
   Examples (type and offset only — the value is never copied, per DISEASES.md §2a):
   - `063a5502a992bd85` — phone at offset 2129 (WhatsApp contact line)
   - `6169b09fe7801904` — email at offset 1171; phone at offset 1155
   - `26dda2c33506f1ff` — email at offset 2457 ("Email-Id" line)

2. **Medicine:** Replace each email address and phone number with a type placeholder, in place.
   Redaction (not drop) keeps the surrounding Marathi prose usable while removing the private value.
   ZWJ/ZWNJ and all Devanagari letters are untouched; only the matched ASCII/Devanagari-digit runs
   of an email or a phone number are replaced.

   ```python
   import re
   _F1_EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
   # a phone number: optional +, then 8+ digits (ASCII or Devanagari) with spaces/hyphens
   _F1_PHONE = re.compile(r'\+?[\d०-९](?:[\d०-९ \-]{6,})[\d०-९]')

   def fix_f1(text: str) -> str:
       text = _F1_EMAIL.sub('[email]', text)
       text = _F1_PHONE.sub('[phone]', text)
       return text
   ```

3. **Action:** fix — redact the personal value in place; keep the document.

4. **Harm test:** Run on the gold set (`teams/02-data-b/gold/ind-mr-fw2_gold.csv`, 140 docs) with
   `harm_test_indic.py`: **1 changed, 0 dropped (0.71%)**, ZWJ/ZWNJ preserved, NFC preserved —
   **PASS** (limit: 1.4 of 140). The one changed gold document is a false positive where the phone
   pattern matched a long non-phone digit run; it stays within the harm budget.

5. **Side effects:** The phone pattern can match a long non-phone digit run (a year range, a price,
   an ID) and redact it; the gold harm test above bounds how often that happens on clean text.
   Emails are matched precisely and rarely false-positive.
