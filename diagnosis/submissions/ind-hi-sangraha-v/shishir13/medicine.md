# Medicine sheet: ind-hi-sangraha-v (shishir13)

Counts are from all 500 rows of `labels.csv`. A disease gets a section if it appears more than five times.

**Gate 1 status: gold set empty, not testable.** The Hindi gold set did not exist when I wrote this, and no gold file is in my repository. The harm test will be run on it when it exists, with the small-set rule: a medicine passes if it changes or drops at most 1 document or 1% of the gold set, whichever is larger.

**Stand-in numbers (not a Gate 1 test).** Until then, every number below comes from a proxy: the 271 documents of this pack that I labelled `clean` (no disease except D3). Those 271 are one reader's labels, not two, so the test is weaker than the real one. "Detection" is how many of the documents labelled with the code each rule catches, and it shows how much the rule misses.

| Code | Count in pack | Medicine | Action | Changed (of 271) | Dropped (of 271) | Detection | Result |
|---|---|---|---|---|---|---|---|
| A5 | 51 | `fix_a5` | fix | 0 | 0 | 41/51 | pass |
| C1 | 92 | `strip_c1_tail` | fix | 0 | 0 | 31/92 | pass |
| C2 | 36 | `dedupe` | fix | 2 (0.7%) | 0 | 29/36 | pass |
| C3 | 53 | `c3_drop` | drop | 0 | 0 | 39/53 | pass, but circular (see C3) |
| C5 | 10 | `c5_drop` | drop | 0 | 0 | 4/10 | pass |
| D3 | 205 | none | keep | 0 | 0 | n/a | n/a |
| D4 | 22 | none | n/a | not run | not run | n/a | gold set empty, not testable; no safe rule |
| C4 | 7 | none | n/a | not run | not run | n/a | gold set empty, not testable; no safe rule |

## Medicine 1: A5, characters in the wrong order

1. **Disease:** A5, 51 documents. Examples:
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
4. **Harm test:** Gold set empty, not testable. Stand-in result: on the 271 proxy documents it changes 0 and drops 0. It catches 41 of the 51 documents I labelled A5. The test also found 6 documents that I had labelled `clean` or without A5 and that have this disease, so I added A5 to those 6 rows.
5. **Side effects:** It does not fix OCR documents where the wrong letter is a different letter (`चौद्ध` for बौद्ध). It cannot repair a word whose correct form it cannot guess, such as `तिौर`. Rare valid Sanskrit sequences with a doubled mark could be changed.

## Medicine 2: C1, boilerplate

1. **Disease:** C1, 92 documents. Examples:
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
4. **Harm test:** Gold set empty, not testable. Stand-in result: it changes 0 and drops 0 of the 271 proxy documents. It catches only 31 of the 92 documents I labelled C1. The rest are footers with no fixed phrase (`हिमाचल दस्तक`, `(जागरण फोटो)`), or lines at the start or middle of the document (`Quick links:`, `Posted On:`, `इसे भी पढ़ें` inside the text).
5. **Side effects:** It leaves C1 lines that are not at the end. A real last line that starts with `यह भी पढ़` would be removed. The list needs one new phrase for each site, so it will miss new templates. The same footer phrases (`This website follows the DNPA Code of Ethics.`, `Get all … News in Hindi`) are common in news packs, so I expect the rule to also work on other Hindi news packs such as ind-hi-sangraha-s, but I have not tested that.

## Medicine 3: C2, repeated text

1. **Disease:** C2, 36 documents. Examples:
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
4. **Harm test:** Gold set empty, not testable. Stand-in result: it changes 2 of the 271 proxy documents (0.7%, below the 1% limit) and drops none. It catches 29 of the 36 documents I labelled C2.
5. **Side effects:** A speech or a poem that repeats a long line on purpose would lose the repeat. The 2 changed clean documents are both news items that quote a sentence twice, and the removal there is harmless.

## Medicine 4: C3, truncated document

1. **Disease:** C3, 53 documents. Examples:
   - `3d66ca6d56ff7d0f`: ends with `साथ ही देवताओं,`
   - `af6c50a82a970dfd`: ends with `मुस्कराते हुए हमारी बातें सुनता,`
   - `e45f2a8e8d549f21`: ends with `…सीन अंग माने गए हैं। या`
2. **Medicine:** A document whose last character is not a full stop, danda, question mark, exclamation mark, quote or closing bracket.
   ```python
   def c3_drop(t):
       return t.rstrip()[-1:] not in '।.?!"\'”’)॥'
   ```
3. **Action:** Drop the document. Dropping is crude: a better action is to cut the last unfinished sentence.
4. **Harm test:** Gold set empty, not testable. Stand-in result: it drops 0 of the 271 proxy documents. This result is circular, because I labelled a document C3 exactly when it ended without punctuation, so the clean set cannot contain such a document. It catches 39 of the 53 C3 documents. The other 14 are cut at the start or in the middle, which this rule cannot see. I could not honestly claim it passes until it is run on the gold set.
5. **Side effects:** It would drop a good document that ends in a list, a table or a name with no final punctuation (headline lists, poem lines). It does not catch a document truncated at the start (`- कि पुलिस और प्रशासन की ओर से…`).

## Medicine 5: C5, lists of keywords or headlines

1. **Disease:** C5, 10 documents. Examples:
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
4. **Harm test:** Gold set empty, not testable. Stand-in result: it drops 0 of the 271 proxy documents and changes none. It catches only 4 of the 10 C5 documents, so most headline lists are missed.
5. **Side effects:** A poem, a lyric or a bullet-point exam page can look like a list and would be dropped. This is a weak rule and should be checked on the gold set first.

## Medicine 6: D3, Hindi and English mixed

1. **Disease:** D3, 205 documents. Examples:
   - `73edc87d0fe145a4`: `NASA`
   - `6b35ae7096dd14fa`: `Ameesha Patel`
   - `8d83e0f13cb77da5`: `Gurugram News:`
2. **Medicine:** None. D3 is natural in Hindi news text, so I labelled it and did not judge it. A Latin-script detector is used only to tag documents: `re.search(r'[A-Za-z]{2,}', t)`.
3. **Action:** Keep the document.
4. **Harm test:** 0 changed and 0 dropped by definition.
5. **Side effects:** Any rule that removes Latin text would damage names, acronyms and URLs. The only part that is a problem is English boilerplate, and C1 handles that.

## Medicine 7: D4, bad machine translation

1. **Disease:** D4, 22 documents. Examples:
   - `5d00471edd7df08e`: `तेजतर्रार, गतिशील और निश्चित रूप से आकर्षक`
   - `2f02b8b9feec6642`: `एचिलीस कंधे` (Achilles tendon translated as "Achilles shoulder").
   - `c5727742e49ca11f`: `ट्रेन और बस कोलाइड`
2. **Medicine:** No safe rule from characters alone. It needs a model signal (for example a language-model perplexity filter or a translation-artifact classifier).
3. **Action:** Drop the document when the score is high.
4. **Harm test:** Gold set empty, not testable. No medicine exists to run, so nothing could be tested even on the stand-in set.
5. **Side effects:** Not known. A perplexity filter would also hit rare but valid vocabulary, such as scripture, law and medicine.

## Medicine 8: C4, two documents joined

1. **Disease:** C4, 7 documents. Examples:
   - `2771f2bfb03e4ae0`: several unrelated jokes with a run of `.` lines between them.
   - `b82d784c3ba8a12a`: a fire-safety report joined to a temple visit report at `सौभाग्य प्राप्त किया। उन्होंने बताया कि मन में इच्छा थी…`
   - `551df2d268c9dbf7`: several assembly news items joined, with a fragment `लंबित हैं।` at the seam.
2. **Medicine:** No safe rule. A sentence-level topic-change score is needed.
3. **Action:** Drop the document, or split it at the boundary.
4. **Harm test:** Gold set empty, not testable. No medicine exists to run, so nothing could be tested even on the stand-in set.
5. **Side effects:** Not known.
