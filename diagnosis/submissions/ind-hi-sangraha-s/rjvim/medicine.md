# Medicine sheet: ind-hi-sangraha-s (rjvim)

Pack: 500 documents, all `ai4bharat/sangraha | synthetic/hin_Deva` (English Wikipedia machine-translated to Hindi). Labels: 464 `fix`, 34 `clean`, 2 `drop`. Most diseases come from the translation step, not from the web.

**Harm test status (Gate 1):** gold set empty, not testable. `ind-hi-sangraha-s` has one reader (`rjvim`), so `teams/02-data-b/gold/gold_coverage.csv` (30 Oct) lists 0 gold documents for this pack. The rules below run with `teams/02-data-b/tools/harm_test_indic.py`: there is one section for each code, and each section has one `medicine_<code>(text)` function. Data B can run them on the Hindi gold set as soon as this pack has gold documents.

| Code | Docs in pack | Action |
|---|---|---|
| D4 | 458 | fix (empty parentheses); drop (3 or more danda-glued abbreviations) |
| A6 | 137 | fix |
| C3 | 25 | fix |
| B4 | 12 | fix |
| C2 | 8 | drop |
| B2 | 7 | fix; drop when there are many (also covers B3 `<unk>`, 5 docs) |

## A6: visarga `ः` used as a colon

1. **Disease:** A6, 137 docs. The colon after a Devanagari word became the visarga `ः` (U+0903, hex `e0 a4 83`). Examples: `0901d3609c93ba66` (`संयोजन हैः डल्ला`), `257cef1fe99b6355` (`निम्नलिखित बच्चे थेः`), `70bab8ad5d120193` (`जनसंख्याः 3,052`).
2. **Medicine:** replace `ः` with `:` when it ends a word and is followed by a line end or by a space and more text. Keep it when the word is a real visarga word (प्रायः, अतः, पुनः, क्रमशः, …).
   ```python
   import re
   _KEEP = re.compile("(\u092a\u094d\u0930\u093e\u092f|\u0905\u0924|\u092a\u0941\u0928|\u0938\u093e\u092e\u093e\u0928\u094d\u092f\u0924|\u092e\u0941\u0916\u094d\u092f\u0924|\u0938\u094d\u0935\u0924|\u0935\u093f\u0936\u0947\u0937\u0924|\u0935\u0938\u094d\u0924\u0941\u0924|\u0915\u094d\u0930\u092e\u0936|\u0905\u0902\u0924\u0924|\u092a\u094d\u0930\u093e\u0924|\u0926\u0941|\u0905\u0927|\u0928\u092e|\u092e\u0942\u0932\u0924|\u0938\u0902\u092d\u0935\u0924|\u092a\u0942\u0930\u094d\u0923\u0924|\u0938\u094d\u092a\u0937\u094d\u091f\u0924)$")
   _VISARGA = re.compile("(?<=[\u0915-\u0939\u093e-\u094c])\u0903(?=[ \t]*(?:\n|$)|[ ]+[\"0-9\u0900-\u097f])")

   def medicine_a6(text):
       return _VISARGA.sub(lambda m: "\u0903" if _KEEP.search(text[max(0, m.start() - 10):m.start()]) else ":", text)
   ```
3. **Action:** fix.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** a Sanskrit-style word that ends in visarga and is not in the keep list (for example a rare `-तः` adverb) loses its visarga. The same applies to `स्रोतः` used as Sanskrit and not as a heading.

## D4: translation damage that a rule can find

1. **Disease:** D4, 458 docs. Two kinds of damage can be found by a rule. (a) **Empty parentheses:** the original name in another script was deleted and `()`, `(,)` or `(,,)` was left. Examples: `22fd653de4dd666a` (`स्टोरस्ट्रोम पुल (,)`), `257cef1fe99b6355` (`वाल्डेमार द विक्टियर ()`), `a2298260d4c4d456` (`प्लिस्टोस (,,)`). (b) **Abbreviations cut by a danda:** English initials such as "B. F." or "F.C." were cut into sentences (`बी के सहयोगी थे।एफ।`, `एफ।सी।`). Examples: `635cbbdde03f1dad`, `1977bf6aaac83a24`, `5700b1ccb1a5ed64`.
2. **Medicine:** drop a document with 3 or more `।` that have a Devanagari letter on both sides. Its initials are lost, so it cannot be repaired. Otherwise, remove empty parentheses that follow a space or a Devanagari letter. The lookbehind keeps code such as `f()`.
   ```python
   import re
   _GLUE = re.compile("[\u0900-\u097f]\u0964[\u0900-\u097f]")
   _EMPTY = re.compile("(?<=[\\s\u0900-\u097f])\\s*\\(\\s*[,;]*\\s*\\)")

   def medicine_d4(text):
       if len(_GLUE.findall(text)) >= 3:
           return True
       return _EMPTY.sub("", text)
   ```
3. **Action:** drop at 3 or more glued dandas; otherwise fix.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** native web Hindi that leaves out the space after `।` is dropped (the threshold of 3 limits this). An empty `()` that was written on purpose after a Devanagari word is removed.
6. **Not covered:** the most common D4 in this pack is proper names translated as common words, and no rule can find these. Examples: Fansler became `प्रशंसक` (`3878784268dd0561`), Maidman became `नौकरानी` (`99184df1a9f23e59`), Price became `कीमत` (`64fe6627135b0e41`). Suggestion for spec v1: give `synthetic/hin_Deva` a lower sampling weight than native Hindi sources.

## C3: empty sections (the table or list was dropped, the heading was left)

1. **Disease:** C3, 25 docs. A section, or the whole document, ends in a heading or caption with no body: `अनुसूची।`, `स्रोतः`, `"23 फरवरी 2020 तक अद्यतन किया गया।`. Examples: `131b86eb077ba739`, `ec95ed1fb82e3503`, `8d73071e61bd24ef`.
2. **Medicine:** remove a heading line (3 words or fewer, ending in `।`, `ः` or `:`) when the next non-empty line is also a heading or the document ends.
   ```python
   import re
   _HEAD = re.compile("^[^\n]{1,40}[\u0964\u0903:]$")

   def _is_head(line):
       return line is not None and bool(_HEAD.match(line.strip())) and len(line.split()) <= 3

   def medicine_c3(text):
       lines = text.split("\n")
       out = []
       for i, line in enumerate(lines):
           nxt = next((x for x in lines[i + 1:] if x.strip()), None)
           if _is_head(line) and (nxt is None or _is_head(nxt)):
               continue
           out.append(line)
       return "\n".join(out)
   ```
3. **Action:** fix.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** a short real sentence directly before another short sentence can look like a heading. A first version (5 words or fewer) removed `जीवनी।` from a clean document of this pack, so the limit is now 3 words.

## B4: translated wiki-template and placeholder junk

1. **Disease:** B4, 12 docs. Wikitable markup was translated (`!कोलन = 9| प्रदर्शनी खेल`, `! शैली = "पृष्ठभूमिः #ffcc00; …"|`), and formula or score placeholders were left in the text (`(सूत्र _ 1)`, `<ID1`, `<5>`). Examples: `1b0e1771a362f1a5`, `487a621e98c3ad74`, `4a26d9ce3fbaa87b`.
2. **Medicine:** delete lines that start with `!` or `|` and contain `कोलन`, `शैली` or `=`, and lines with `| … =}}`. Delete the placeholders `(सूत्र _ N)`, `<IDN` and `<N>`.
   ```python
   import re
   _LINE = re.compile("(?m)^[!|].*(?:\u0915\u094b\u0932\u0928|\u0936\u0948\u0932\u0940|=).*$\n?|^.*\\|\\s*[^|\n]*=\\s*\\}\\}.*$\n?")
   _PLACEHOLDER = re.compile("\\(?\u0938\u0942\u0924\u094d\u0930 _ \\d+\\)?|<ID\\d+|<\\d+>")

   def medicine_b4(text):
       return _PLACEHOLDER.sub("", _LINE.sub("", text))
   ```
3. **Action:** fix.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** a real `<5>` in maths text is removed. Formula documents keep a gap where the formula was, because the formula itself was already lost.

## C2: one phrase repeated 3 or more times in a row (translation loop)

1. **Disease:** C2, 8 docs. The translator got stuck in a loop. Examples: `adc639e30cf4b95b` (`और उत्तर में लॉर्ड कैपिटल्स,` repeated, then cut off), `38ea6e7718826a61` (`हदीस उल्रिका (हदीस उल्रिका),` 7 times), `59aef801fa585bdf`.
2. **Medicine:** drop the document when a phrase of 10 to 81 characters is repeated 3 or more times in a row.
   ```python
   import re
   _REPEAT = re.compile("(\\S.{9,80}?)(?:[\\s,]*\\1){2,}")

   def medicine_c2(text):
       return bool(_REPEAT.search(text))
   ```
3. **Action:** drop.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** poems, song lyrics and lists with a real refrain are dropped.

## B2: markup tags (Latin or translated into Devanagari) and `<unk>`

1. **Disease:** B2, 7 docs, plus B3 `<unk>` in 5 docs. Examples: `94f9ac0d9c39d021` (`<बी. आर.>`, a translated `<br>`), `97c453c003f59b98` (`</रेफ>`), `8d4a1eb74b3a464c` (a whole MediaWiki XML header with translated tags). `59aef801fa585bdf` has 288 `<unk>` tokens where the Japanese text was.
2. **Medicine:** drop the document when it has 3 or more `<unk>` or 5 or more tags whose name is in Devanagari. Otherwise remove the known tags and `<unk>`.
   ```python
   import re
   _TAG = re.compile("</?(?:br|ref|\u092c\u0940\\. \u0906\u0930\\.|\u0930\u0947\u092b|\u090f\u0928\u090f\u0938|\u092a\u0947\u0930\u0947\u0902\u091f\u093f\u0921|\u092e\u0949\u0921\u0932|\u0906\u0908\u0921\u0940|\u092a\u0943\u0937\u094d\u0920|\u0936\u0940\u0930\u094d\u0937\u0915|\u0938\u0902\u0936\u094b\u0927\u0928|\u092a\u093e\u0920)\\b[^<>\n]{0,60}>")
   _DEV_TAG = re.compile("</?[\u0900-\u097f][^<>\n]{0,30}>")

   def medicine_b2(text):
       if text.count("<unk>") >= 3 or len(_DEV_TAG.findall(text)) >= 5:
           return True
       return _TAG.sub("", text).replace("<unk>", "")
   ```
3. **Action:** fix; drop when there are many.
4. **Harm test:** gold set empty, not testable.
5. **Side effects:** an article about HTML or tokenizers that quotes these tags is changed.

## Other findings

- **Templated stubs:** docs 70/173/300 (baseball seasons) and 151/405 (lists of historic places) share 40 to 67% of their 5-word shingles. They follow the same Wikipedia template and are not copies, so they are not labelled H2.
- **Partial reads:** two very long documents are marked `read=partial`.
