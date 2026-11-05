# Medicine sheet: ind-te-sangraha-s (shankarpandala)

Counts are from my 500 labelled rows. Every harm test below ran on the gold set of this pack only (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv), as TSAI asked (CAP, 31 Oct).

## Medicine 1

1. **Disease:** A6 (Wrong or mixed script), 18 documents in this pack. Examples:
   - `d78c631c2bf869ef`: “ఫ్యూచర్ః” at offset 1296
   - `6aaa95b110924e1a`: “విభజించబడిందిః” at offset 549
   - `5913f75a9f71a35b`: “ఉన్నాయిః” at offset 324
   - The visarga-as-colon pattern is in 182 documents and 491 places, because the machine translation writes ః where the English text has a colon. The first version of this rule changed 4 of the 46 gold documents (a dateline and a score, where ః really is a colon but the gold readers did not label it), so it was narrowed to the two clearest places: the end of a line and just before an opening quotation mark. It fixes 213 of the 491 places, in 101 documents. Only the 18 documents above carry the A6 label; in the others it sits next to D4 and was not coded.
2. **Medicine:** Replace a Telugu visarga ః that ends a word and is at the end of a line, or is followed by a space and an opening quotation mark, with a colon. Words that really end in a visarga (పునః, నమః, అంతః, ...) are kept by a short list.
   ```python
   _VISARGA_WORDS = {"అంతః", "ఆయుః", "ఉరః", "చేతః", "తపః", "తేజః", "నమః", "పయః", "పునః", "ప్రాతః", "భూః", "మనః", "యశః", "వచః", "శిరః", "శ్రీః", "స్వః"}

   def medicine_a6(text):
       def fix(m):
           word = m.group(1) + "ః"
           return m.group(0) if word in _VISARGA_WORDS else m.group(1) + ":"
       return re.sub(r"([\u0C00-\u0C02\u0C04-\u0C7F]*)ః(?=\n|$| [\"“‘'])", fix, text)
   ```
3. **Action:** fix the text. (My verdicts on these documents: drop 2, fix 16.)
4. **Harm test:** gold set: the gold set of this pack, 5 documents (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv on main, 2 Nov 2026); rule `medicine_a6` of this file (the code block in this section), run with harm_test_indic.py (PR #148); a rule passes if it changes or drops at most max(1 document, 1%) of the gold set (TSAI, CAP 30 Oct).
   - Changed 0 of 5 (0.00%). Dropped 0 of 5 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents checked, 0 with a different count. **PASS**
   - Normal-form audit (NFC kept, no compatibility character lost): 0 changed documents, 0 problems. **PASS**
   - Result: **PASS**
   - Gold set: the 5 documents of this pack that two readers marked clean after reading them in full. On the rebuilt gold set of this pack in PR #222 (24 documents) the rule also passes: 0 changed, 0 dropped.
   - It is not a rule that does nothing: it changes 4 of the 18 documents labelled A6 and 101 documents in the whole pack.
5. **Side effects:** A visarga used as a colon inside a line (a dateline such as a place name before a colon, or a score) is left alone, so about 57% of the places stay unfixed. A Sanskrit word that ends in a visarga and is not in the list gets a colon when it ends a line. The rule does not touch the look-alike Latin, Greek or Cyrillic letters (about 6 documents); those need a hand fix.

## Medicine 2

1. **Disease:** B2 (HTML or XML tags), 9 documents in this pack. Examples:
   - `d7d13ed37c277bea`: “<బిఆర్>” at offset 300
   - `79167d66fe9ef5eb`: “<</Â>” at offset 1534
   - `5c1b142ee4cd51b6`: “<</Â>” at offset 434
2. **Medicine:** Remove tag remnants: `<</Â>`, a Telugu word in angle brackets such as `<బిఆర్>`, and a lone `>` right after a full stop.
   ```python
   def medicine_b2(text):
       text = re.sub(r"<</[^<>\s]{0,3}>", "", text)
       text = re.sub(r"<[\u0C00-\u0C7F]{1,12}>", "", text)
       text = re.sub(r"(?<=[.!?])>(?=\s|$)", "", text)
       return text
   ```
3. **Action:** fix the text. (My verdicts on these documents: drop 1, fix 8.)
4. **Harm test:** gold set: the gold set of this pack, 5 documents (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv on main, 2 Nov 2026); rule `medicine_b2` of this file (the code block in this section), run with harm_test_indic.py (PR #148); a rule passes if it changes or drops at most max(1 document, 1%) of the gold set (TSAI, CAP 30 Oct).
   - Changed 0 of 5 (0.00%). Dropped 0 of 5 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents checked, 0 with a different count. **PASS**
   - Normal-form audit (NFC kept, no compatibility character lost): 0 changed documents, 0 problems. **PASS**
   - Result: **PASS**
   - Gold set: the 5 documents of this pack that two readers marked clean after reading them in full. On the rebuilt gold set of this pack in PR #222 (24 documents) the rule also passes: 0 changed, 0 dropped.
   - It is not a rule that does nothing: it changes 8 of the 9 documents labelled B2 and 8 documents in the whole pack.
5. **Side effects:** A real `<word>` in angle brackets would be removed. None was found in the clean rows. A Latin tag such as `<br>` is not touched.

## Medicine 3

1. **Disease:** B4 (Template and code junk in prose), 7 documents in this pack. Examples:
   - `976b619191078e2d`: “<ఐ. డి. 1>%” at offset 611
   - `135bc37cf2e5f3ce`: “!కొల్న్ = 9 శైలి = " |” at offset 911
   - `4c66553f2e36df76`: “(ID1)” at offset 616
   - The same debris is in 3 more documents that were not labelled B4.
2. **Medicine:** Remove the machine-translated placeholder `<ID1>` (written `<ఐ. డి. 1>`, `ఐడి1`), the placeholder `(ID1)`, and a wiki table row that starts with `!` and holds ` = ` and `|`.
   ```python
   def medicine_b4(text):
       text = re.sub(r"[ \t]*<ఐ\.? ?డి\.? ?\d+>?%?", "", text)
       text = re.sub(r"[ \t]*(?<![\u0C00-\u0C7F])ఐడి\d+", "", text)
       text = re.sub(r"[ \t]*\(ID\d+\)", "", text)
       text = re.sub(r"(?m)^![^\n]*=[^\n]*\|[^\n]*\n?", "", text)
       return text
   ```
3. **Action:** fix the text. (My verdicts on these documents: drop 4, fix 3.)
4. **Harm test:** gold set: the gold set of this pack, 5 documents (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv on main, 2 Nov 2026); rule `medicine_b4` of this file (the code block in this section), run with harm_test_indic.py (PR #148); a rule passes if it changes or drops at most max(1 document, 1%) of the gold set (TSAI, CAP 30 Oct).
   - Changed 0 of 5 (0.00%). Dropped 0 of 5 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents checked, 0 with a different count. **PASS**
   - Normal-form audit (NFC kept, no compatibility character lost): 0 changed documents, 0 problems. **PASS**
   - Result: **PASS**
   - Gold set: the 5 documents of this pack that two readers marked clean after reading them in full. On the rebuilt gold set of this pack in PR #222 (24 documents) the rule also passes: 0 changed, 0 dropped.
   - It is not a rule that does nothing: it changes 7 of the 7 documents labelled B4 and 10 documents in the whole pack.
5. **Side effects:** The Telugu word ఐడి (ID) followed directly by a digit is removed; the same word with a space before the digit is kept. The text around the placeholder may still read badly.

## Medicine 4

1. **Disease:** C3 (Truncated document), 32 documents in this pack. Examples:
   - `e61e3982f326eb8b`: “6 మంది పిల్లలకు జన్మనిచ్చాడుః” at offset 63138
   - `29196613cdcd085b`: “జాతీయ అలంకరణలను అందుకున్నారుః” at offset 1668
   - `bae9636d02b0f6bb`: “ఈ క్రింది వేదికలలో జరిగాయిః” at offset 2008
2. **Medicine:** If the last line of the document ends with ః or a colon, it only announced a list that was stripped: remove that line. A document cut in the middle of a sentence is not repaired (the rest of the sentence is lost).
   ```python
   def medicine_c3(text):
       body = text.rstrip()
       tail = text[len(body):]
       cut = body.rfind("\n")
       if cut > 0 and body[cut + 1:].endswith(("ః", ":")):
           return body[:cut] + tail
       return text
   ```
3. **Action:** fix the text (remove the dangling last line). (My verdicts on these documents: drop 5, fix 27.)
4. **Harm test:** gold set: the gold set of this pack, 5 documents (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv on main, 2 Nov 2026); rule `medicine_c3` of this file (the code block in this section), run with harm_test_indic.py (PR #148); a rule passes if it changes or drops at most max(1 document, 1%) of the gold set (TSAI, CAP 30 Oct).
   - Changed 0 of 5 (0.00%). Dropped 0 of 5 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents checked, 0 with a different count. **PASS**
   - Normal-form audit (NFC kept, no compatibility character lost): 0 changed documents, 0 problems. **PASS**
   - Result: **PASS**
   - Gold set: the 5 documents of this pack that two readers marked clean after reading them in full. On the rebuilt gold set of this pack in PR #222 (24 documents) the rule also passes: 0 changed, 0 dropped.
   - It is not a rule that does nothing: it changes 29 of the 32 documents labelled C3 and 29 documents in the whole pack.
5. **Side effects:** A real last line that ends with a colon is removed. A document cut mid-sentence stays as it is; for those the alternative action is to drop the document.

## Medicine 5

1. **Disease:** D4 (Bad machine translation), 357 documents in this pack. Examples:
   - `c2926fcd7c9d9ef6`: “ఇన్నింగ్స్ను 3 పరుగులకే నాటౌట్గా ముగించాడు” at offset 687
   - `1476d4874c81f2a1`: “దండయాత్ర నిషేధం” at offset 1286
   - `e75cb610611b73de`: “పెరోలి శాన్ ఆంటోనియో థండర్ యొక్క ప్రధాన కోచ్గా పేరు పెట్టారు” at offset 600
2. **Medicine:** No rule in code can repair a bad machine translation. This detector only catches the extreme case: one word repeated 8 or more times in a row, or one word making more than 15% of a long document.
   ```python
   def medicine_d4(text):
       words = text.split()
       run = 1
       for a, b in zip(words, words[1:]):
           run = run + 1 if a == b else 1
           if run >= 8:
               return True
       if len(words) >= 200:
           top = max(words.count(w) for w in set(words) if len(w) > 2)
           return top / len(words) > 0.15
       return False
   ```
3. **Action:** drop the document (only the looping documents; the rest of the D4 documents need a translation-quality score, Gate 2). (My verdicts on these documents: drop 112, fix 245.)
4. **Harm test:** gold set: the gold set of this pack, 5 documents (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv on main, 2 Nov 2026); rule `medicine_d4` of this file (the code block in this section), run with harm_test_indic.py (PR #148); a rule passes if it changes or drops at most max(1 document, 1%) of the gold set (TSAI, CAP 30 Oct).
   - Changed 0 of 5 (0.00%). Dropped 0 of 5 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents checked, 0 with a different count. **PASS**
   - Normal-form audit (NFC kept, no compatibility character lost): 0 changed documents, 0 problems. **PASS**
   - Result: **PASS**
   - Gold set: the 5 documents of this pack that two readers marked clean after reading them in full. On the rebuilt gold set of this pack in PR #222 (24 documents) the rule also passes: 0 changed, 0 dropped.
   - It is not a rule that does nothing: it drops 4 of the 357 documents labelled D4 and 4 documents in the whole pack.
5. **Side effects:** It acts on 4 of the 357 documents with D4, so almost all D4 documents stay. A list or a table with a repeated word could be dropped by mistake.

## Medicine 6

1. **Disease:** D5 (Translationese), 87 documents in this pack. Examples:
   - `1476d4874c81f2a1`: “ప్రావిన్స్ యొక్క” at offset 128
   - `a28871107b0cefc2`: “చీజ్ యొక్క స్మూత్ సాస్” at offset 918
   - `bac1bebb9e10546c`: “మాలి యొక్క” at offset 25
2. **Medicine:** Drop a document where the calque యొక్క ("of") is used 6 or more times and at least twice per 100 words. That is the clearest sign of word-for-word translation. The rest of translationese cannot be changed by a regex without changing the meaning.
   ```python
   def medicine_d5(text):
       words = len(text.split())
       n = text.count("యొక్క")
       return n >= 6 and 100 * n / words >= 2
   ```
3. **Action:** drop the document (only the clearest cases; the others need a translation-quality score, Gate 2). (My verdicts on these documents: drop 26, fix 61.)
4. **Harm test:** gold set: the gold set of this pack, 5 documents (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv on main, 2 Nov 2026); rule `medicine_d5` of this file (the code block in this section), run with harm_test_indic.py (PR #148); a rule passes if it changes or drops at most max(1 document, 1%) of the gold set (TSAI, CAP 30 Oct).
   - Changed 0 of 5 (0.00%). Dropped 0 of 5 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents checked, 0 with a different count. **PASS**
   - Normal-form audit (NFC kept, no compatibility character lost): 0 changed documents, 0 problems. **PASS**
   - Result: **PASS**
   - Gold set: the 5 documents of this pack that two readers marked clean after reading them in full. On the rebuilt gold set of this pack in PR #222 (24 documents) the rule also passes: 0 changed, 0 dropped.
   - It is not a rule that does nothing: it drops 20 of the 87 documents labelled D5 and 26 documents in the whole pack.
5. **Side effects:** It acts on 20 of the 87 documents labelled D5 and on 6 others, so most D5 documents stay. A formal or legal Telugu text that really uses యొక్క often would be dropped by mistake.

## Medicine 7

1. **Disease:** G3 (Indic dropped by an English rule), 30 documents in this pack. Examples:
   - `e41f1014c0d989d5`: “()” at offset 34
   - `53644f0c34df4394`: “(,;” at offset 50
   - `cb70d94a91aa878f`: “""” at offset 527
   - 49 documents in the pack contain an empty pair; 30 documents carry the G3 label (the others are labelled with their other codes). The rule also leaves the stripped lists, tables and empty headings alone: their text is gone and cannot be put back.
2. **Medicine:** Remove an empty bracket pair left where text was stripped: `()`, `(,)`, `(;)`, `(, ;)`, with the space before it.
   ```python
   def medicine_g3(text):
       return re.sub(r"[ \t]*\([ \t,;]*\)", "", text)
   ```
3. **Action:** fix the text. (My verdicts on these documents: drop 0, fix 30.)
4. **Harm test:** gold set: the gold set of this pack, 5 documents (teams/02-data-b/gold/ind-te-sangraha-s_gold.csv on main, 2 Nov 2026); rule `medicine_g3` of this file (the code block in this section), run with harm_test_indic.py (PR #148); a rule passes if it changes or drops at most max(1 document, 1%) of the gold set (TSAI, CAP 30 Oct).
   - Changed 0 of 5 (0.00%). Dropped 0 of 5 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents checked, 0 with a different count. **PASS**
   - Normal-form audit (NFC kept, no compatibility character lost): 0 changed documents, 0 problems. **PASS**
   - Result: **PASS**
   - Gold set: the 5 documents of this pack that two readers marked clean after reading them in full. On the rebuilt gold set of this pack in PR #222 (24 documents) the rule also passes: 0 changed, 0 dropped.
   - It is not a rule that does nothing: it changes 12 of the 30 documents labelled G3 and 49 documents in the whole pack.
5. **Side effects:** A bracket pair that holds only commas or semicolons is removed even when it was meant. Unclosed remnants such as `(,` or `(;` are not touched.
