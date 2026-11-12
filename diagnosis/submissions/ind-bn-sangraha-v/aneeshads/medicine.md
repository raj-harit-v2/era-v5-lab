# Medicine sheet: ind-bn-sangraha-v (aneeshads)

Counts are from my label sheet: 500 documents read (498 in full, 2 in part), 20 codes found. Ten codes are found in
more than five documents, so this sheet has ten medicines. A count is the number of times the code is written in the
`diseases` column (a document with two doubled vowel signs can count twice), followed by the number of documents.

**Harm test.** The gold set is `teams/02-data-b/gold/ind-bn-sangraha-v_gold.csv` on `main` (rebuilt 2 November):
142 documents that the readers marked `clean`. The tool is `teams/02-data-b/tools/harm_test_indic.py`. A rule may
change or drop at most 1% of the gold set or 1 document, whichever is more: on 142 documents that is **1 document**.
Part 4 of each medicine is the tool's own text (run of 4 November, `--rule all`). All rules run in order change 0
of 142 (0.00%, **PASS**); without its frequency filter, A6 alone changed 2 (1.41%, fail). To see harm on text that the gold set may not have,
each medicine was also run on a **stand-in**, the 329 documents of this pack that I marked `clean`, as in my first
sheet. "Pack" gives what the medicine does to all 500 documents. The stand-in and pack numbers are from my run of
30 October. Every rule is named `cure_<code>` and returns the new text, or `("drop", "")`, so
`teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md --pack … --gold-dir teams/02-data-b/gold --rule <code>`
runs it as it is.

| # | Code | Count (documents) | Action | Gold changed | Gold dropped | Gold share | Result | Stand-in changed / dropped (329) | Labelled documents treated | Pack changed / dropped |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | D3 | 105 (104) | none, out of spec v1 (candidate: fix) | – | – | – | no rule in code; candidate **fails** on stand-in | 28 / 0 (8.5%) | 45 of 104 | 51 / 0 |
| 2 | C1 | 62 (62) | fix | 0 | 0 | 0.0% | pass | 4 / 0 | 32 of 62 | 38 / 0 |
| 3 | C2 | 38 (37) | fix | 0 | 0 | 0.0% | pass | 0 / 0 | 32 of 37 | 34 / 0 |
| 4 | A6 | 36 (36) | fix (`ৰ` → `র`, more than 6 `ৰ`) | 0 | 0 | 0.0% | pass | 2 / 0 ¹ | 13 of 36 ¹ | 15 / 0 ¹ |
| 5 | G1 | 36 (35) | fix | 0 | 0 | 0.0% | pass | 0 / 0 | 13 of 35 | 13 / 0 |
| 6 | A3 | 23 (21) | fix, drop if still damaged | 0 | 0 | 0.0% | pass | 0 / 0 | 11 of 21 | 8 / 3 |
| 7 | G2 | 12 (11) | fix | 0 | 0 | 0.0% | pass | 1 / 0 | 11 of 11 | 13 / 0 |
| 8 | G4 | 8 (8) | fix | 0 | 0 | 0.0% | pass | 0 / 0 | 6 of 8 | 7 / 0 |
| 9 | B4 | 8 (8) | fix | 0 | 0 | 0.0% | pass | 0 / 0 | 7 of 8 | 7 / 0 |
| 10 | C4 | 7 (7) | fix | 0 | 0 | 0.0% | pass | 1 / 0 | 1 of 7 | 9 / 0 |

¹ Measured on 4 November with the frequency filter (more than 6 `ৰ`, fewer than `র`) and without the visarga part.

The stand-in hits of C1, A6, G2 and C4 (12 documents) are documents that I marked `clean` but that do have the
disease. They are errors in my labels, not harm by the medicine; each is named in the harm test of its medicine. The
D3 hits are real harm, so D3 gets no medicine.

Each medicine's code runs on its own, so a block defines every name it uses (`re` is given by both harm tests).

## Medicine 1

1. **Disease:** D3, mixed language. Count 105, in 104 documents. 62 of them are `clean` documents, because
   DISEASES.md says to label D3 but not judge it.
   - `16838a9d467d9521`, offset 0: `করোনা ( Corona) মুক্ত ভারত ( India)`, an English gloss in brackets after the
     Bengali word.
   - `abff62cd526be189`, offset 35: `থ্রি-স্টার`, an English word written in Bengali letters.
   - `eb3dc547426a3951`, offset 1432: `This is the wound of love.`, an English sentence in Bengali prose.
2. **Medicine:** none. D3 is out of spec v1 (TSAI decision of 4 November, as the review says). The candidate I
   tested removes an English gloss in brackets that follows a Bengali word. It is named `_candidate_d3` so that the
   harm test does not take it for a rule.
   ```python
   GLOSS = re.compile(r"\s?\(\s*[A-Za-z][A-Za-z0-9 .,&'’-]*\)")


   def _candidate_d3(text):
       return GLOSS.sub("", text)
   ```
3. **Action:** keep the documents as they are. The candidate's action would be to fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496: "D3 has no rule
   in code, so nothing to test". D3 is out of spec v1, and the candidate is not tested.
5. **Side effects:**
   - The candidate removes good text: names and terms in English that help a model link the two scripts. It also
     removes the sign name in a horoscope (`মেষ (Aries):` in `017b4f09daad47e4`) and a news-agency name (`(PNS)` in
     `b0c095487dd72b87`).
   - It still misses most D3: English words in Bengali letters (`থ্রি-স্টার`, `ক্যারিয়ার`) and English sentences
     without brackets (59 of my 104 D3 documents).
   - A drop rule for pages that are mostly English (more Latin letters than Bengali) was also tried: it drops no
     document of this pack, so it does nothing here.

## Medicine 2

1. **Disease:** C1, boilerplate of the news sites in this pack. Count 62, in 62 documents.
   - `30bca5e624fe83fc`, offset 534: `নিউজ১৮ বাংলায় সবার আগে পড়ুন ব্রেকিং নিউজ। …`, the News18 footer.
   - `0f79a07b7f39f669`, offset 1321: `(দ্য রিপোর্ট/এসকে/নূরু/এপি/এনডিএস/ডিসেম্বর ১৩, ২০১৩)`, the agency slug.
   - `ab064fe7e282c0d7`, offset 314: `Published at: 27 May 2022 10:11 AM (IST)`, the ABP time stamp.
2. **Medicine:**
   - Remove a line of 300 characters or less that is a footer, share prompt, breadcrumb or time stamp:
     - a copyright line (`©`, `অনুমতি ছাড়া ব্যবহার বেআইনি`, `সর্বস্বত্ব সংরক্ষিত`, `All rights reserved`)
     - a publisher's notice (`… প্রকাশিত/প্রচারিত কোনো সংবাদ …`) or address (`কর্ণফুলী মিডিয়া পয়েন্ট, তৃতীয় তলা`,
       `পদ্মা লাইফ টাওয়ার (লেভেল`)
     - an app or site promo (the News18 footer, `Oneindia এর ব্রেকিং নিউজের জন্য`, `Zee 24 Ghanta App`,
       `Get the latest world news`, `Stay on top of the latest`)
     - `এই পোস্টটি শেয়ার করতে চাইলে`, `Home` or `Home/…`, `Published at:`, `Updated at:`, `Published on:`, a line that
       is only `Tags:` or `Like this:`, `Please enter your comment!`, `আর্কাইভ / প্রিন্ট সংস্করণ`.
   - Remove the agency slug `(দ্য রিপোর্ট/…)`, also when its opening bracket is lost.
   ```python
   BOILER_LINE = re.compile(
       r"অনুমতি ছাড়া ব্যবহার বেআইনি|সর্বস্বত্ব সংরক্ষিত|All rights reserved|^\s*©"
       r"|সবার আগে পড়ুন ব্রেকিং নিউজ|এই পোস্টটি শেয়ার করতে চাইলে|^\s*Home\s*(?:/|$)"
       r"|^\s*Get the latest world news|^\s*Stay on top of the latest|Please enter your comment"
       r"|^\s*(?:Published|Updated) (?:at|on):|^\W*Published on:|^\s*(?:Tags|Like this):\s*$"
       r"|কর্ণফুলী মিডিয়া পয়েন্ট, তৃতীয় তলা|পদ্মা লাইফ টাওয়ার \(লেভেল|প্রকাশিত/প্রচারিত কোনো সংবাদ"
       r"|Oneindia এর ব্রেকিং নিউজের জন্য|^\s*\(?Zee 24 Ghanta App|^\s*আর্কাইভ / প্রিন্ট সংস্করণ")
   C1_MAX_LINE = 300
   SLUG = re.compile(r"\s*\(?(?:দ্য রিপোর্ট|বিডিনিউজ|বাসস|ইউএনবি)/[^()\n]*\)")


   def cure_c1(text):
       lines = [ln for ln in text.split("\n") if len(ln) > C1_MAX_LINE or not BOILER_LINE.search(ln)]
       return SLUG.sub("", "\n".join(lines))
   ```
3. **Action:** fix the text.
4. **Stand-in** (329 documents I marked `clean`, 30 October): 4 changed. All four have the boilerplate and are errors
   in my labels:
   - `017b4f09daad47e4` and `e36d42ca8a9c51c8` have the News18 footer.
   - `14b51bf2092ebadc` has the copyright notice of প্রতিছবি ডট কম.
   - `c5f15f32bee8a1be` has the copyright footer. I marked it `clean` but also wrote C1 in its `diseases`, which
     does not agree.
   **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**


   Pack: 38 documents changed. It treats 32 of my 62 C1 documents.
5. **Side effects:**
   - The list knows only the sites seen in this pack. Other boilerplate stays: 30 of my 62 C1 documents are not
     treated, for example `www.BDeBooks. Com` in `7891ebc9ab87ad20`, `ছবিঃ ফেসবুক` in `aba9d20790ce5b8b`, and the
     Wikipedia reference lines `↑ "…"। … তারিখে মূল থেকে আর্কাইভ করা।` in `8d3b898a86f08629`.
   - A line of real content that quotes a copyright notice, starts with `©`, or is the single word `Home` would be
     removed. So would a paragraph that ends with an agency slug and continues on the same line.
   - The `আরও পড়ুন` lines that I labelled C1 (`43c51cdac699187d`, `611e3e5fe427f168`) are removed by Medicine 10.

## Medicine 3

1. **Disease:** C2, repeated lines. Count 38, in 37 documents.
   - `5ed37ddc0d848f84`, offset 327: `শুক্রবার টস জিতে প্রথমে ফিল্ডিংয়ের সিদ্ধান্ত নেন ইংল্যান্ড অধিনায়ক ইয়ন মর্গ্যান।`, the first
     sentence of line 3 is a sentence of line 1 (the headline) again.
   - `b0d8affd2329469d`, offset 220: line 2 (218 characters, `ভোলায় আঞ্চলিক এমআরপি পাসপোর্ট অফিসের সেবা …`) is line 1
     again.
   - `4fd6a400467e4b0b`, offset 965: lines 24 to 31 (`আঁচলের একটু ছোঁয়া, রুমালের ঘ্রানে শিহরন!` …) are lines
     2 to 9 again.
2. **Medicine:** remove a line of 20 or more characters (spaces at the ends ignored) that already appeared earlier in
   the same document. Then, in each line, remove a sentence of 25 or more characters that already appeared on an
   earlier line (a headline repeated as the first sentence of the story). Keep the first copy. A sentence said twice
   in the same line is kept, because writers repeat on purpose.
   ```python
   SENTENCE = re.compile(r"[^।?!\n]*[।?!]+\s*|[^।?!\n]+")


   def cure_c2(text, min_line=20, min_sentence=25):
       seen_lines, seen_sentences, out = set(), set(), []
       for line in text.split("\n"):
           key = line.strip()
           if len(key) >= min_line and key in seen_lines:
               continue                                  # the whole line again
           seen_lines.add(key)
           kept, here = [], set()
           for sent in SENTENCE.findall(line):
               k = " ".join(sent.split())
               if len(k) >= min_sentence and k in seen_sentences:
                   continue                              # a sentence of an earlier line again (a headline)
               here.add(k)
               kept.append(sent)
           seen_sentences |= here
           out.append("".join(kept))
       return "\n".join(out)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

5. **Side effects:**
   - Lines and sentences that repeat on purpose are removed:
     - the refrain of a song or poem of 20 or more characters
     - a line of a table or scorecard (`ইফতেখার আহমেদ ১৬ (১৩)` in `7acc8a39bbf7eb53`)
     - a question asked again as a heading (`গাছের পাতা সবুজ হয় কেন?` in `d9fb73294bcea228`).

     Short refrains, such as `জয় জয় জয়` in the hymn `80199b73dc4150b0`, are kept by the length limits.
   - A repeat that is not exact (a changed word, a different space inside the line) is not seen, and a sentence
     said twice in one line is kept (`8a82a545913a2a14`). Not treated: 5 of my 37 C2 documents. In
     `7378fae019d08f76` and `84232835daf80e9f` the lines are joined by a literal `\n`; after Medicine 9 splits them,
     this medicine treats both, so Medicine 9 must run first. `a16e7291bad69a10` and `2856497430a08269` stay.

## Medicine 4

1. **Disease:** A6, wrong script. Mostly the Assamese letter RA WITH MIDDLE DIAGONAL U+09F0 `ৰ` used in Bengali
   words in place of the Bengali RA U+09B0 `র`, in old texts that were scanned and read by OCR. I also labelled A6 the
   visarga `ঃ` used as a colon between digits; by the TSAI decision of 4 November it is not treated, so a time such
   as `০১ঃ৫৯` stays as it is. Count 36, in 36 documents.
   - `87c77e18093a596b`, offset 1931: `প্ৰকাশ` (09AA 09CD **09F0** 0995 09BE 09B6), should be `প্রকাশ`.
   - `7160f28b914f8629`, offset 0: `সুৰোধিনী` (09B8 09C1 **09F0** 09CB 09A7 09BF 09A8 09C0).
   - `0ca18aa03db2ef77`, offset 1184: `৭ঃ৪ঃ১১` (09ED **0983** 09EA **0983** 09E7 09E7), a verse number with the visarga
     U+0983 for the colon. Not treated by this medicine (see above).
2. **Medicine:** in a document where `ৰ` appears more than 6 times and fewer times than `র` (so the document is
   Bengali, not Assamese, and the `ৰ` are a pattern of the scan, not a stray letter), replace every `ৰ` with `র`. The
   visarga is left as it is. The frequency filter is the narrow condition of the TSAI decision of 4 November: the gold
   set keeps two older Bengali texts with 5 and 4 `ৰ`, and the filter leaves them unchanged. The first two examples
   above have 1 and 2 `ৰ`, so this medicine leaves them as they are (see Side effects).
   ```python
   A6_MIN = 7   # the Assamese RA must appear more than 6 times


   def cure_a6(text):
       n_as, n_bn = text.count("\u09F0"), text.count("\u09B0")
       if n_as >= A6_MIN and n_as < n_bn:
           text = text.replace("\u09F0", "\u09B0")
       return text
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

   Without the filter, A6 changed 2 gold documents (1.41%, **FAIL**): `80199b73dc4150b0` (5 `ৰ`, 130 `র`) and
   `c7ddb9d7bb6a8e7c` (4 `ৰ`, 294 `র`). With the filter both stay as they are.

   **Pack (500 documents, 4 November):**
   - 15 documents changed (38 without the filter), 0 dropped. It treats 13 of my 36 A6 documents. The other two are
     `53ad1531ea630e8c` and `968f2a4c6a08b9fc`, which I marked `clean` but which have 7 or more `ৰ`: errors in my
     labels.
   - The pack has 340 `ৰ` in 327 words. The medicine changes 287 of them (84.4%), in 275 words (84.1%). It leaves 53
     (15.6%), in 52 words, all in 23 documents with 6 or fewer `ৰ`, among them the two gold documents. No document
     of the pack has as many `ৰ` as `র` or more.
   - Of the 275 changed words, 32 (11.6%) match a word of the pack's documents without `ৰ`. I read the other 243:
     most are old spellings that modern pages no longer use (`ধর্ম্ম`, `কার্য্য`, `সর্ব্ব`, `কর্ত্তব্য`). By my
     reading, about **90%** (248) become correct, about **5%** (14) stay wrong and about 5% (13) are OCR fragments
     where neither form is right (`স্ফুৰাণব`, `পৰছেীঃ`). Not yet checked by a second reader.
5. **Side effects:**
   - The OCR also read some `ব` as `ৰ` (the two letters differ by one stroke). Such a word becomes `র` instead of `ব`
     and stays wrong: `ৰলিলেন` → `রলিলেন` (should be `বলিলেন`), also `হইৰে`, `চলৰে`, `ভাৰছি`, `জানাৰেন`,
     `বিৰেচনাধীন`, `অবয়ৰ`, `স্বয়মেৰ`. 14 of the 275 changed words; they were wrong before the change too.
   - A document with 6 or fewer `ৰ` keeps them: 23 of my 36 A6 documents, 15.6% of the `ৰ` of the pack, among them
     `87c77e18093a596b` (`প্ৰকাশ`) and `7160f28b914f8629` (`সুৰোধিনী`). The limit of 6 is set by the two gold
     documents (5 and 4 `ৰ`), not by the disease.
   - An Assamese name or quotation inside a Bengali document would be respelled in Bengali.
   - The Assamese WA U+09F1 `ৱ` is not handled.
   - An Assamese document (more `ৰ` than `র`) is left alone: it is D1, a wrong language label, and needs another
     medicine.
   - The visarga used as a colon (`৭ঃ৪ঃ১১` in `0ca18aa03db2ef77`, `০১ঃ৫৯` in `cb146ca4c7c4164a`) stays.
   - The other forms of A6 in my labels are not treated: a romanised word (`ajker rashifal` in `7e24bbd21ca4942b`),
     an Arabic prayer (`a95985f75a9ef4c5`), a Hindi line (`5098f2d236480f43`). They are D2 or D3 more than A6.

## Medicine 5

1. **Disease:** G1, cut at the vowel sign. The commonest form in this pack is a vowel sign written twice, which no
   Bengali word has. Count 36, in 35 documents.
   - `b5d3379fa1dd2757`, offset 1912: `মাহমুদুুুর`, the vowel sign U U+09C1 three times (should be `মাহমুদুর`).
   - `489141c194e52d26`, offset 573: `চাালাচ্ছে`, the vowel sign AA U+09BE twice (should be `চালাচ্ছে`).
   - `bf521322a90491aa`, offset 822: `লেজুুড়বৃত্তির`, U+09C1 twice (should be `লেজুড়বৃত্তির`).
2. **Medicine:** when the same vowel sign or virama is written two or more times in a row, keep one.
   ```python
   DOUBLED = re.compile("([\u09BE-\u09CD\u09D7])\\1+")


   def cure_g1(text):
       return DOUBLED.sub(r"\1", text)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - The other forms of G1 are not fixed, because the right repair is not certain:
     - a vowel sign after a space (`ভরে েগলে` for `ভরে গেলে`)
     - a vowel sign after an independent vowel (`এী` in `c92c5cf70a94c304`, `অা`)
     - two different vowel signs in a row (`ূে` in `c870ec0472382d1a`).

     So 22 of my 35 G1 documents are not treated.
   - Expressive lengthening in informal writing (`নাাা`) is shortened.
   - Inside Bijoy-damaged text (A3) the fix changes one kind of garbage into another (`থেেেকও` → `থেকও` in
     `e4e559c63731c7fd`, which Medicine 6 drops anyway).

## Medicine 6

1. **Disease:** A3, mojibake from a legacy Bijoy (ANSI font) conversion. A Latin-1 or symbol character stands
   inside a Bengali word in place of a conjunct or a vowel sign. Count 23, in 21 documents.
   - `bf521322a90491aa`, offset 150: `বিদ্রæপ`, U+00E6 `æ` in place of the vowel sign U (should be `বিদ্রুপ`).
   - `87590e5df7527a67`, offset 1994: `দ্বন্দ¦টা`, U+00A6 `¦` in place of `্ব` (should be `দ্বন্দ্বটা`).
   - `975e9170d8259094`, offset 153: `আশ^াস`, U+005E `^` in place of `্ব` (should be `আশ্বাস`).
2. **Medicine:** map the four leftovers whose meaning is certain in this pack back to Bengali: `¦` and `^` to `্ব`,
   `Ð` to `ণ্ড`, `æ` to `ু`. Only replace them when they stand between two Bengali letters or signs. Then count the
   leftovers that remain (a Latin-1 or symbol character inside a Bengali word, or any non-Bengali character before a
   vowel sign). If three or more remain, the text cannot be repaired: drop the document.
   ```python
   L = "[অ-হ়-ৗড়-ৣৰৱ]"   # a Bengali letter or sign (not a digit)
   SIGN = "[া-ৌৗ]"                                # a dependent vowel sign
   BIJOY = {"\u00A6": "\u09CD\u09AC", "^": "\u09CD\u09AC", "\u00D0": "\u09A3\u09CD\u09A1", "\u00E6": "\u09C1"}
   BIJOY_FIX = re.compile(f"(?<={L})[{''.join(map(re.escape, BIJOY))}](?={L})")
   LEFTOVER = re.compile(f"(?<={L})[\u00A1-\u00FF\u0153\u0304\u2022\u203A^](?={L})"
                         f"|[\u00A1-\u00FF\u0153\u0304\u2022\u203A^-](?={SIGN})")


   def cure_a3(text):
       fixed = BIJOY_FIX.sub(lambda m: BIJOY[m.group()], text)
       if len(LEFTOVER.findall(fixed)) >= 3:
           return ("drop", "")
       return fixed
   ```
3. **Action:** fix the text; drop the document if three or more leftovers remain after the fix.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - The table is only right for Bijoy text. `æ` gives `ু`: `বিদ্রæপ` becomes `বিদ্রুপ`, a common spelling, while the
     dictionary spelling is `বিদ্রূপ`.
   - When Bijoy put the e-kar before the conjunct, the result has the wrong order: `বিশে^র` becomes `বিশে্বর`, not
     `বিশ্বের` (`5584556a2ea2dcfd`).
   - Leftovers outside the table (`›`, `Ñ`, `¡`, `•`, `œ`, `¤`, the macron) stay. With fewer than three in a document,
     the damage stays in the text (`b5d3379fa1dd2757`, `96c193554be5b64c`). With three or more, the whole document
     is lost, also when the rest is good: in `bf4fd3ccaf9e861d`, `•` stands for `ল` three times.
   - A3 between digits is not seen: `৩°৫` in `2856497430a08269`.
   - A real `^` or `-` between Bengali letters, for example a suffix written `-ার` in a grammar text, would count as a
     leftover.

## Medicine 7

1. **Disease:** G2, lost ZWJ. Two forms in this pack: a word that starts with Ra + virama + Ya (a word cannot start
   with a reph, so the ZWJ U+200D that makes the ra-phala `র‍্য` was lost), and Ta + virama at the end of a word (the
   khanda ta `ৎ`, written `ত` + ZWJ + virama by old fonts, lost its ZWJ). Count 12, in 11 documents.
   - `3efce0f19f5c8712`, offset 559: `র্যাবের` (**09B0 09CD** 09AF 09BE …), should be `র‍্যাবের` (09B0 **200D** 09CD 09AF …).
   - `6073f8a55a5582ca`, offset 353: `র্যাপিড` (**09B0 09CD** 09AF …), should be `র‍্যাপিড`.
   - `4620e19b5836f03f`, offset 7506: `কামেনেত্` (… **09A4 09CD**), should be `কামেনেৎ` (… **09CE**).
2. **Medicine:** at the start of a word, put a ZWJ between Ra and the virama when Ya follows (`র্য` → `র‍্য`). At the
   end of a word, write Ta + virama as the khanda ta U+09CE (`ত্` → `ৎ`).
   ```python
   RA_YA_START = re.compile("(?<![\u0980-\u09FF\u200C\u200D])\u09B0\u09CD(?=\u09AF)")
   TA_VIRAMA_END = re.compile("\u09A4\u09CD(?![\u0980-\u09FF\u200C\u200D])")


   def cure_g2(text):
       text = RA_YA_START.sub("\u09B0\u200D\u09CD", text)   # র্যাব -> র‍্যাব (ra-phala, not a reph)
       return TA_VIRAMA_END.sub("\u09CE", text)             # কামেনেত্ -> কামেনেৎ (khanda ta)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

5. **Side effects:**
   - Many Bengali sites write `র্যাব` without the ZWJ on purpose, and most fonts show it right. The fix only adds an
     invisible character, but it makes two spellings of one word in the corpus unless the whole corpus is fixed.
   - A broken fragment that starts with `র্য` gets the ZWJ too (`র্য।` in `c870ec0472382d1a`, a document I drop).
   - A word that ends in `ত্` on purpose (a Sanskrit stem in a grammar text) becomes `ৎ`.
   - Other lost ZWJ or ZWNJ (inside a conjunct, `ক্‌ষ` against `ক্ষ`) are not found.

## Medicine 8

1. **Disease:** G4, over-normalised digits. A few numbers in Latin digits inside Bengali prose that writes its other
   numbers in Bengali digits: the digits were partly converted. Count 8, in 8 documents.
   - `54442e06493e7751`, offset 2472: `16409` (0031 0036 0034 0030 0039), a hotline number among 16 numbers in Bengali
     digits.
   - `42f394b1b2292a07`, offset 1376: `(1)` (0028 **0031** 0029), a list number among 13 numbers in Bengali digits.
   - `d3ab7bf3efcff498`, offset 855: `8.` (**0038** 002E), a list number among 11 numbers in Bengali digits.
2. **Medicine:** in a document that has more numbers in Bengali digits than in Latin digits, write a Latin-digit
   number in Bengali digits (`16409` → `১৬৪০৯`). Leave a number that touches a Latin letter (`30677644M`) or whose
   nearest letter before or after it, on the same line, is Latin (`Covid 19`, `Results 2023:`).
   ```python
   L = "[অ-হ়-ৗড়-ৣৰৱ]"   # a Bengali letter or sign (not a digit)
   BN_DIGIT = "[০-৯]"
   TO_BN_DIGITS = str.maketrans("0123456789", "\u09E6\u09E7\u09E8\u09E9\u09EA\u09EB\u09EC\u09ED\u09EE\u09EF")
   BN_NUMBER = re.compile(f"{BN_DIGIT}+")
   LATIN_NUMBER = re.compile(r"(?<![A-Za-z0-9])[0-9]+(?:[.,:/][0-9]+)*(?![A-Za-z0-9])")
   LETTER_BEFORE = re.compile(f"([A-Za-z]|{L})[^A-Za-z\u0980-\u09FF\n]*$")
   LETTER_AFTER = re.compile(f"^[^A-Za-z\u0980-\u09FF\n]*([A-Za-z]|{L})")


   def cure_g4(text):
       if len(BN_NUMBER.findall(text)) <= len(re.findall("[0-9]+", text)):
           return text                                  # Latin digits are the style of this document

       def to_bengali(m):
           before = LETTER_BEFORE.search(text, 0, m.start())
           after = LETTER_AFTER.search(text[m.end():])
           if any(x and re.match("[A-Za-z]", x.group(1)) for x in (before, after)):
               return m.group()                         # next to an English word: Covid 19, Results 2023
           return m.group().translate(TO_BN_DIGITS)
       return LATIN_NUMBER.sub(to_bengali, text)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

5. **Side effects:**
   - A number that is a code (an ISBN `9843205901` in `8e75560ea6d4e0f7`, a train number `12377` in
     `8d3b898a86f08629`) is changed to Bengali digits. It stays the same number, but a search for the Latin form
     would not find it.
   - A document whose own style is Latin digits is left alone, also when it has a few Bengali ones: `bb139803564a2da9`
     (14 numbers in Latin digits, 1 in Bengali) and `0c62abe90f1c50aa` (one of each) are not treated.
   - A document where most numbers are in English sentences (a Bengali page with an English table) could have a
     number in a Bengali sentence of that table changed.

## Medicine 9

1. **Disease:** B4, template and code junk: a literal backslash-n or backslash-t (two characters) left by an export
   in place of a line break or a tab. Count 8, in 8 documents.
   - `7378fae019d08f76`, offset 97: `TRT Bangla\nHome/`, a literal `\n` (5C 6E) between the title and the menu.
   - `84232835daf80e9f`, offset 112: `bangladesh\nকাদের ক্রসফায়ার …`, a literal `\n` between the blog name and the
     title.
   - `a16e7291bad69a10`, offset 152: `আলোচিত সংবাদ\nসোমবার …`, between the title and the body.
2. **Medicine:** replace a literal `\n` with a line break and a literal `\t` with a tab, unless the backslash is
   itself escaped (`\\n`).
   ```python
   ESCAPE = re.compile(r"(?<!\\)\\([nt])")


   def cure_b4(text):
       return ESCAPE.sub(lambda m: "\n" if m.group(1) == "n" else "\t", text)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

5. **Side effects:**
   - In a document with LaTeX or program code, `\theta`, `\nabla`, `\n` in a string, or a Windows path such as
     `C:\new` would be broken. The pack has no such document, but a code or science pack would.
   - Other escapes (`\"`, `\u0985`) are not treated. The `♠` that I labelled B4 in `bf4fd3ccaf9e861d` is A3 damage
     and is not treated here.

## Medicine 10

1. **Disease:** C4, two documents joined. In this pack the visible form is the headline of another article inserted
   after `আরও পড়ুন` ("read more"). Count 7, in 7 documents.
   - `58827dcddbbf097e`, offset 1496: `আরও পড়ুন- রাত পেরোলেই ভারতে আসছে ওপ্পো রেনো ৮ সিরিজ …`, a phone headline inside an
     iPhone story.
   - `7035900113f62f27`, offset 0: `- #IndiaWorld Population Day 2023: শীর্ষে ভারত …`, a headline on population above
     a story on a helicopter crash.
   - `0ca18aa03db2ef77`, from offset 0: seven unrelated comments of different readers, joined only by line breaks.
2. **Medicine:** remove a line that starts with `আরও পড়ুন` or `আরো পড়ুন` (or `Read more`, `Also read`), together with
   the headline that follows on the same line.
   ```python
   READ_MORE = re.compile(r"^\s*(?:আর[োও]\s*পড়ুন|Read more|Also read)\b.*$\n?", re.M | re.I)


   def cure_c4(text):
       return READ_MORE.sub("", text)
   ```
3. **Action:** fix the text.
4. **Harm test:** gold set of 142 documents (ind-bn-sangraha-v 142), medicine.md sha256 003835270496; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 142 (0.00%). Dropped 0 of 142 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

5. **Side effects:**
   - Only the marked form is found. Texts joined with no marker, such as the comment thread `0ca18aa03db2ef77` and
     the headline on top of `7035900113f62f27`, are not treated: 6 of my 7 C4 documents. These need a reader or a
     topic model.
   - A sentence in the text that starts with `আরও পড়ুন` ("read more of …", for example in an essay on reading) would
     be removed.
   - The headline goes but nothing after it: if the other article's body follows on the next lines, it stays.
