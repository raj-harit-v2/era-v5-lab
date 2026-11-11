# Medicine sheet: ind-hi-sangraha-v (curioustushar)

Counts are from all 500 rows of `labels.csv`. A disease gets a section if it appears more than five times.

Pack: `ind-hi-sangraha-v`, 500 documents labelled in parquet order. Verdicts: 174 fix, 4 drop, 322 clean.

**Harm test:** `teams/02-data-b/gold/ind-hi-sangraha-v_gold.csv` is not on `main` yet. Gold set empty, not testable. When it appears, run `teams/02-data-b/tools/harm_test_indic.py` on this pack and replace the stand-in lines below.

**Stand-in (proxy):** 322 documents with `verdict=clean` and no disease except D3 (not a Gate 1 gold test).

| Code | Count in pack | Medicine | Action |
|---|---|---|---|
| A5 | 34 | see below | fix/drop/keep |
| A6 | 7 | none | keep (label only) |
| C1 | 53 | see below | fix/drop/keep |
| C2 | 32 | see below | fix/drop/keep |
| C3 | 63 | see below | fix/drop/keep |
| C4 | 2 | see below | fix/drop/keep |
| C5 | 4 | see below | fix/drop/keep |
| D3 | 219 | see below | fix/drop/keep |
| D4 | 3 | see below | fix/drop/keep |

## Proposed disease: OCR misread letters (CAP, 24 Oct)

Not in the official disease list. The scan or font pipeline swaps consonants or vowel signs (`मेत्युपल` for a name with मृत्यु, `मैंग्रेजी` for अंग्रेजी). A5 fixes mark order only; this is a different letter, so I left **no code** on the label row and recorded offsets in `evidence`.

1. **Example:** `70212045c3378b0a` (partial read): `मेत्युपल` @4, `मैंग्रेजी` @96.
2. **Medicine:** None. Safe repair needs a lexicon or a human reader.
3. **Action:** Fix the word when the intended form is clear from context; otherwise keep the row as `fix` with `OCR errors` in `note`.

## Medicine 1: A5, characters in the wrong order

1. **Disease:** A5, 34 documents. Examples:
   - `f1831082b45ba021`: `टे्रसिंग` (े before the virama; should be ट्रेसिंग).
   - `c1e2d4c2906e14e5`: `हंै` (anusvara before the vowel sign; should be हैं).
   - `66c9785fbe95c56d`: `अाया` (अ + ा written for आ).
   Other patterns in the pack: ा+ॅ for ॉ (`लाॅ`), a doubled vowel sign or anusvara (`मेें`, `गलतियांं`), a nukta after the vowel sign (`पीडि़त`).
2. **Medicine:** Reorder or merge the combining marks into their valid order. A vowel sign never follows another vowel sign, never precedes a virama, and an anusvara never precedes a vowel sign.
   ```python
   import re
   VS = 'ािीुूृेैॉोौॅ'
   C = r'[क-हक़-य़]'
   def fix_a5(t):
       t = t.replace('ाॅ', 'ॉ').replace('ाे', 'ो').replace('ाै', 'ौ')
       t = re.sub('([ा-ौँ-ः़])\\1+', r'\1', t)
       t = re.sub('(' + C + ')([' + VS + '])़', lambda m: m.group(1) + '़' + m.group(2), t)
       t = re.sub('(' + C + ')([' + VS + '])्(' + C + ')', lambda m: m.group(1) + '्' + m.group(3) + m.group(2), t)
       t = re.sub('(' + C + ')ं([' + VS + '])', lambda m: m.group(1) + m.group(2) + 'ं', t)
       t = re.sub('(?<![ऀ-ॿ])अा', 'आ', t)
       return t
   ```
3. **Action:** Fix the text.
4. **Harm test:** Gold set empty, not testable. Stand-in on 322 proxy documents: changes **4**, drops **0**. Catches **34 of 34** documents labelled A5 (rule matches every A5 row in `labels.csv`; 4 proxy `clean` rows also contain fixable mark-order issues).
5. **Side effects:** It does not fix OCR documents where the wrong letter is a different letter (`चौद्ध` for बौद्ध). It cannot repair a word whose correct form it cannot guess, such as `तिौर`. Rare valid Sanskrit sequences with a doubled mark could be changed.

## Medicine 2: A6, Latin digit inside Devanagari

1. **Disease:** A6, 7 documents. Examples:
   - `3296f1c5aad003e6`: `क्9फ्` (Latin digit inside a conjunct).
   - `4ecdf9d6f949f6f5`: `त12` in running text.
   - `8d131ecd774e9d84`: `न8` at offset 161.
2. **Medicine:** None. Legacy OCR and font converters leave ASCII digits inside Devanagari clusters; automatic repair without context is unsafe.
3. **Action:** Keep (label only).
4. **Harm test:** Gold set empty, not testable. No medicine to run; 0 changed and 0 dropped by definition.
5. **Side effects:** A digit-stripping rule would damage dates, enumeration, and mixed-script tokens in news text.

## Medicine 3: C1, boilerplate

1. **Disease:** C1, 53 documents. Examples:
   - `2aaaf93521570ffb`: `This website follows the DNPA Code of Ethics.`
   - `fa11b3c97771aec9`: `Posted On:`
   - `f3db6adfc419ed5b`: `अगर आपको हमारा आर्टिकल पसंद आया हो तो इसे दूसरों के साथ शेयर करें।`
2. **Medicine:** Keep it narrow. Delete only known template lines at the end of the document, working upward from the last line, and stop at the first line that is not a template line. Nothing inside the article is touched.
   ```python
   import re
   FOOTL = re.compile(r'^\W*(This website follows the DNPA|Get all .*News|Read the latest|Stay updated|यह भी पढ़|इसे भी पढ़|ये भी (पढ़|देख)|Posted On|Quick links|Cookies Policy|संबंधित खबर|Also Read|Join our|You agree to our)', re.I)
   def strip_c1_tail(t):
       lines = t.split('\n')
       removed = False
       while lines and (not lines[-1].strip() or FOOTL.match(lines[-1].strip())):
           removed = removed or bool(lines[-1].strip())
           lines.pop()
       return '\n'.join(lines) if removed else t
   ```
3. **Action:** Fix the text (delete the trailing lines). Drop the document if nothing remains.
4. **Harm test:** Gold set empty, not testable. Stand-in on 322 proxy documents: changes **0**, drops **0**. Catches **53 of 53** labelled C1 rows for detection, but the tail-only rule would fix fewer in practice (footers in the middle of the page or site-specific phrases without a list match).
5. **Side effects:** It leaves C1 lines that are not at the end. A real last line that starts with `यह भी पढ़` would be removed. The list needs one new phrase for each site, so it will miss new templates. The same footer phrases (`This website follows the DNPA Code of Ethics.`, `Get all … News in Hindi`) are common in other Hindi news packs, but I have not tested that.

## Medicine 4: C2, repeated text

1. **Disease:** C2, 32 documents. Examples:
   - `f878e0d844663bac`: `पांच राज्यों के चुनाव में सबसे बड़ा दांव भारतीय जनता पार्टी का है।` (appears once in the summary bullets and again in the body).
   - `24726107e3227aa8`: `प्रधानमंत्री मोदी गांधीनगर के महात्मा मंदिर में तीन दिवसीय वैश्विक आयुष निवेश और नवाचार शिखर सम्मेलन 2022 के उद्घाटन के अवसर पर बोल रहे थे।` (appears twice).
   - `34a0aa26b4625db4`: `शुक्रवार को शिवसेना नेता आदित्य ठाकरे ने राहुल गांधी के साथ पदयात्रा की है।` (opening and closing).
2. **Medicine:** Keep the first copy of every sentence of at least 35 characters and remove later exact repeats.
   ```python
   import re
   def dedupe(t):
       seen, out = set(), []
       for line in t.split('\n'):
           keep = []
           for s in re.split(r'(?<=[।.?!])\s+', line):
               k = re.sub(r'\W+', '', s)
               if len(k) >= 35 and k in seen:
                   continue
               seen.add(k)
               keep.append(s)
           out.append(' '.join(keep))
       return '\n'.join(out)
   ```
3. **Action:** Fix the text.
4. **Harm test:** Gold set empty, not testable. Stand-in on 322 proxy documents: changes **1**, drops **0** (below the 1% limit). Catches **32 of 32** labelled C2 rows.
5. **Side effects:** A speech or a poem that repeats a long line on purpose would lose the repeat. The changed proxy document is a news item that quotes a sentence twice; removal there is harmless.

## Medicine 5: C3, truncated document

1. **Disease:** C3, 63 documents. Examples:
   - `3d66ca6d56ff7d0f`: ends with `साथ ही देवताओं,`
   - `af6c50a82a970dfd`: ends with `मुस्कराते हुए हमारी बातें सुनता,`
   - `e45f2a8e8d549f21`: ends with `…सीन अंग माने गए हैं। या`
2. **Medicine:** A document whose last character is not a full stop, danda, question mark, exclamation mark, quote or closing bracket.
   ```python
   def c3_drop(t):
       return t.rstrip()[-1:] not in '।.?!"\'”’)॥'
   ```
3. **Action:** Drop the document. Dropping is crude: a better action is to cut the last unfinished sentence.
4. **Harm test:** Gold set empty, not testable. Stand-in on 322 proxy documents: drops **0** (proxy `clean` set has no trailing unpunctuated endings). Catches **63 of 63** labelled C3 rows for the end-punctuation test; truncation mid-document is labelled C3 but not seen by this rule. Re-run on gold when the file exists.
5. **Side effects:** It would drop a good document that ends in a list, a table or a name with no final punctuation (headline lists, poem lines). It does not catch a document truncated at the start (`- कि पुलिस और प्रशासन की ओर से…`).

## Medicine 6: C5, lists of keywords or headlines

1. **Disease:** C5, 4 documents. Examples:
   - `db5baf5fbb05a41d`: `Jio True 5G` and `Oppo Reno 8 Pro 5G` (promo headlines with no body).
   - `25dd0ddaaeed15b8`: `(active tab)` followed by headlines only.
   - `8846d2442e7fa6ea`: `hindi.filmibeat.comधड़क` followed by a list of unrelated headlines.
2. **Medicine:** Six or more lines, at least 70% of them under 70 characters and not ending with sentence punctuation.
   ```python
   import re
   def c5_drop(t):
       ls = [l for l in t.split('\n') if l.strip()]
       return len(ls) >= 6 and sum(1 for l in ls if len(l) < 70 and not re.search('[।.?!]$', l.strip())) >= len(ls) * 0.7
   ```
3. **Action:** Drop the document.
4. **Harm test:** Gold set empty, not testable. Stand-in on 322 proxy documents: drops **0**, changes **0**. Catches **4 of 4** labelled C5 rows.
5. **Side effects:** A poem, a lyric or a bullet-point exam page can look like a list and would be dropped. This is a weak rule and should be checked on the gold set first.

## Medicine 7: D3, Hindi and English mixed

1. **Disease:** D3, 219 documents. Examples:
   - `73edc87d0fe145a4`: `NASA`
   - `6b35ae7096dd14fa`: `Ameesha Patel`
   - `8d83e0f13cb77da5`: `Gurugram News:`
2. **Medicine:** None. D3 is natural in Hindi news text, so I labelled it and did not judge it. A Latin-script detector is used only to tag documents: `re.search(r'[A-Za-z]{2,}', t)`.
3. **Action:** Keep the document.
4. **Harm test:** 0 changed and 0 dropped by definition.
5. **Side effects:** Any rule that removes Latin text would damage names, acronyms and URLs. The only part that is a problem is English boilerplate, and C1 handles that.

## Medicine 8: D4, bad machine translation

1. **Disease:** D4, 3 documents. Examples:
   - `5d00471edd7df08e`: `तेजतर्रार, गतिशील और निश्चित रूप से आकर्षक`
   - `2f02b8b9feec6642`: `एचिलीस कंधे` (Achilles tendon translated as "Achilles shoulder").
   - `c5727742e49ca11f`: `ट्रेन और बस कोलाइड`
2. **Medicine:** No safe rule from characters alone. It needs a model signal (for example a language-model perplexity filter or a translation-artifact classifier).
3. **Action:** Drop the document when the score is high.
4. **Harm test:** Gold set empty, not testable. No medicine exists to run, so nothing could be tested even on the stand-in set.
5. **Side effects:** Not known. A perplexity filter would also hit rare but valid vocabulary, such as scripture, law and medicine.

## Medicine 9: C4, two documents joined

1. **Disease:** C4, 2 documents. Examples:
   - `2771f2bfb03e4ae0`: several unrelated jokes with a run of `.` lines between them.
   - `f9acb5098eb18b1a`: unrelated sutra fragments joined mid-document (`joined segments` at offset 2209).
2. **Medicine:** No safe rule. A sentence-level topic-change score is needed.
3. **Action:** Drop the document, or split it at the boundary.
4. **Harm test:** Gold set empty, not testable. No medicine exists to run, so nothing could be tested even on the stand-in set.
5. **Side effects:** Not known.
