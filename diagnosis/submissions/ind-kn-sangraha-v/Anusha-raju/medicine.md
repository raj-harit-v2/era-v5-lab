# Medicine sheet: ind-kn-sangraha-v (Anusha-raju)

One section for each disease that was found more than five times. 

All harm tests below were run with Data B's `teams/02-data-b/tools/harm_test_indic.py` on the shared gold set
`teams/02-data-b/gold/ind-kn-sangraha-v_gold.csv` (103 documents, sha256 b523a045d9de), on the code exactly as it
appears in this file. The rules also passed on the earlier 30-document gold set. Each rule alone and all four in order pass:

```
python harm_test_indic.py --medicine medicine.md --pack ind-kn-sangraha-v.parquet --gold-dir teams/02-data-b/gold
```

The gold-set line in each part 4 is the harm test result. A zero there only shows that the rule leaves clean
documents alone, so each part 4 also gives two extra numbers that are not part of the harm test: how many of the
documents labelled with that disease the rule acts on, and how many of my own `clean` rows in `labels.csv` (372 of
the 500) it changes.

## Medicine 1

1. **Disease:** C1, boilerplate. Count: **83**. Groups: headline feed at the top (34), Prajavani follow line at the
   end (13), other one-line site promos (11), Varthabharati comment policy (5), site-specific one-offs and headline
   lists inside the article (20, no shared pattern, left alone).
   - `46e7b0e4e20a9f23`: starts `Don't Miss!\n - News Mekedatu: ಕರ್ನಾಟಕಕ್ಕೆ ಮೇಕೆದಾಟು ಯೋಜನೆ ಏಕೆ ಬೇಕು? …` and four
     unrelated headlines, then the article.
   - `e36492eaffb501b0`: ends `ಪ್ರಜಾವಾಣಿ ಫೇಸ್ಬುಕ್ ಪುಟವನ್ನುಫಾಲೋ ಮಾಡಿ.`
   - `5aef363fc0d5fe65`: after the article, `The views expressed in comments published on www. varthabharati. in
     are those of the comment writers alone. …` and then the same policy in Kannada.

2. **Medicine:** Remove the headline feed at the start of the document. A feed is either a `Don't Miss!` or
   `Trending Topics` line followed by feed lines, or at least two feed lines in a row. A feed line starts with `-`
   and then `N hrs ago` or a section word (`News`, `Sports` …). A `Don't Miss!` line in the middle of the feed is
   removed with it. Removal stops at the first line that is not a feed
   line. Remove any whole line that is exactly one of the known promo lines. Cut the Varthabharati policy block to
   the end of the document. If less than 200 characters are left, the page was nothing but boilerplate, so drop it.

   ```python
   import re

   FEED_START = re.compile(r"^\s*(?:Don't Miss!|Trending Topics\s*:?)\s*$")
   FEED_LINE = re.compile(
       r"^\s*-\s*(?:\d+\s+(?:min|mins|hr|hrs)\s+ago"
       r"|News|Finance|Technology|Education|Lifestyle|Movies|Sports|Automobiles|Travel)\s+\S.*$")
   PROMO_LINE = re.compile(
       r"^\s*(?:ಪ್ರಜಾವಾಣಿ ಫೇಸ್[\u200c\u200d]?ಬುಕ್ ಪುಟವನ್ನು\s*ಫಾಲೋ ಮಾಡಿ\.?"
       r"|Oneindia ಬ್ರೇಕಿಂಗ್ ನ್ಯೂಸ್.*ಪಡೆಯಿರಿ\.?"
       r"|Thanks For Reading!|Copyright ©.*All Rights Reserved\.?"
       r"|A post shared by .*|Get the latest creative news from FooBar.*"
       r"|ಇದನ್ನೂ ಓದಿಃ|Like this:|Search for:|Welcome!|Forgot your password\?"
       r"|error:|Content is protected.*)\s*$")
   VB_BLOCK = re.compile(r"^\s*'ವಾರ್ತಾ ಭಾರತಿ' ನಿಮಗೆ ಆಪ್ತವೇ.*\Z", re.M | re.S)


   def leading_feed_end(lines):
       """Index of the first line after the headline feed at the top, or 0 if there is no feed."""
       i = 0
       while i < len(lines) and not lines[i].strip():
           i += 1
       start = i
       anchored = i < len(lines) and FEED_START.match(lines[i])
       if anchored:
           i += 1
       feed = 0
       while i < len(lines) and (FEED_LINE.match(lines[i]) or FEED_START.match(lines[i]) or not lines[i].strip()):
           feed += bool(FEED_LINE.match(lines[i]))                 # "Don't Miss!" can also sit inside the feed
           i += 1
       return i if (anchored or feed >= 2) else start


   def medicine_c1(text):
       lines = text.split("\n")
       lines = lines[leading_feed_end(lines):]                     # 1. headline feed at the top
       lines = [l for l in lines if not PROMO_LINE.match(l)]       # 2. known promo lines
       out = VB_BLOCK.sub("", "\n".join(lines))                    # 3. Varthabharati comment policy
       if out == text:
           return text                                             # keep
       if len(out.strip()) < 200:
           return True                                             # drop: nothing left but boilerplate
       return out                                                  # fix
   ```

3. **Action:** Fix the text. Drop the document only if under 200 characters remain after the fix.

4. **Harm test:** Gold set of 103 documents (gold csv sha256 b523a045d9de): changed 0 of 103 (0.00%), dropped
   0 of 103 (0.00%). **PASS** (limit: 1% or 1 document, whichever is more, so at most 1). ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**.
   - Labelled C1 (83): fixes 61, drops 0, leaves 22.
   - Labelled `clean` (372): changes 3. Each loses a real promo line (`ಪ್ರಜಾವಾಣಿ ಫೇಸ್ಬುಕ್ …` twice,
     `A post shared by …` once) that the label missed.

5. **Side effects:**
   - A single section-word line at the top (for example `Sports ಅಜಿಂಕ್ಯ …` in `539c9547508b5f0f`) is no longer
     removed, so a one-line feed stays in. That is the price of not cutting a real first line.
   - The 20 site-specific one-offs and headline lists inside the article are not covered.

## Medicine 2

1. **Disease:** D3, mixed language. Count: **21**. DISEASES.md says to label mixed language even when it is natural,
   so all 21 stay labelled. Groups: hashtag headline lines at the top (8), English summary line at the end (7, of
   which 2 are in brackets), English title next to the Kannada title (3), natural mixing such as quotes and technical
   words (3). Only the first two groups are a cleaning problem. The medicine acts on the hashtag lines and on the
   bracketed summaries, and leaves the rest alone.
   - `19ba7ebf9763bb05`: begins `- #BengaluruHeavy Rain: …`, `- #BengaluruBengaluru rain: …`,
     `- #BengaluruSiddaramaiah: ಸಿಎಂ ಸಿದ್ದರಾಮಯ್ಯ ಆರೋಗ್ಯದಲ್ಲಿ ಏರು-ಪೇರು!`
   - `5162614ed46214d1`: ends `(CBSE Class 12 Board Exam 2021 may be cancelled today by Union Education Minister
     Ramesh Pokhriyal Nishank updates)`
   - `97b398d6bc37b2b4`: ends `Nagara Panchami is celebrated in Karnataka with all religious fervor. …` (no
     brackets, so not touched).

2. **Medicine:** Remove the run of `- #…` hashtag lines at the very start, but only when there are at least two of
   them. Remove the last line of the document only when it is a whole English sentence in brackets: it starts with
   `(` and a Latin letter, has at least 25 more characters, has no Kannada letter, and ends with `)`. An English
   line without brackets (a quote, a tweet, a title) is never touched, and English inside a Kannada sentence is
   never touched.

   ```python
   HASHTAG_FEED = re.compile(r"^\s*-\s*#\S.*$")
   EN_SUMMARY = re.compile(r"^\s*\(\s*[A-Za-z][^\u0C80-\u0CFF()]{24,}\)\s*$")


   def medicine_d3(text):
       lines = text.rstrip().split("\n")
       i = n = 0
       while i < len(lines) and (HASHTAG_FEED.match(lines[i]) or not lines[i].strip()):
           n += bool(lines[i].strip())
           i += 1
       if n < 2:
           i = 0                                                   # one tagged line alone is not a feed
       lines = lines[i:]
       cut = bool(lines) and bool(EN_SUMMARY.match(lines[-1]))
       if cut:
           lines.pop()                                             # "(English summary of the story)" at the end
       if not i and not cut:
           return text                                             # keep
       return "\n".join(lines).rstrip() + "\n"                     # fix
   ```

3. **Action:** Fix the text. Never drop.

4. **Harm test:** Gold set of 103 documents (gold csv sha256 b523a045d9de): changed 0 of 103 (0.00%), dropped
   0 of 103 (0.00%). **PASS** (limit: 1% or 1 document, whichever is more, so at most 1). ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**.
   - Labelled D3 (21): fixes 8 (6 hashtag feeds, 2 bracketed summaries), drops 0, leaves 13.
   - Labelled `clean` (372): changes 1 (`63471c4de2084c03`, two `- #…` feed lines the label missed).

5. **Side effects:**
   - English summaries without brackets (`97b398d6bc37b2b4`, `539c9547508b5f0f`, `c6a14dd582b0c493`) stay in. There
     is no pattern that tells them apart from a real English quote or tweet such as `cd57b4f99f029161`, which this
     version no longer removes.
   - A real English sentence in brackets as the last line of an article would be removed.

## Medicine 3

1. **Disease:** C3, truncated document. Count: **12**. Groups: cut at the end mid-sentence (7), starts mid-sentence
   (3, no safe rule), teaser that stops before the content (2).
   - `1cf5a55a26131edd`: ends `… ಸ್ವಲ್ಪ ದೀರ್ಘವಾದುದು. ಅಶೋಕನ`
   - `638d679f80954487`: ends `… ಹೊಟ್ಟೆ ಬಟ್ಟೆ ಕಳೆಯುವುದೆ`
   - `3d71b83cb6625f01`: ends `… ಈ ನಿರಾಶೆಯ ನಿಶಾಗರ್ಭದಿಂದಲೇ ಆಗಾಗ್ಗೆ ಆಶಾಚಂದ್ರಮನ`

2. **Medicine:** Treat the document as cut at the end only when all of these hold: the text does not end with a
   sentence mark, closing quote or bracket; the last line is at least 40 characters long and ends in a Kannada
   letter or sign (not a comma, not a digit); the document is ordinary prose, with at least 3 sentence marks and on
   average at least one every 400 characters; and the broken part after the last sentence mark is at most 150
   characters. Then cut only that broken part. Drop only when fewer than 200 characters of full sentences are left.

   ```python
   END_OK = re.compile(r"[.?!।॥|\"'”’)\]>:ಃ…]\s*$")
   LAST_CHAR_CUT = re.compile(r"[\u0C80-\u0CE3\u0CF1\u0CF2]$")
   SENT_END = re.compile(r"[.?!।॥]\s")
   MIN_CHARS = 200
   MAX_TAIL = 150


   def medicine_c3(text):
       body = text.rstrip()
       if not body:
           return text
       last = body.split("\n")[-1].strip()
       if END_OK.search(body) or len(last) < 40 or not LAST_CHAR_CUT.search(last):
           return text                                             # keep: ends normally, or not clearly cut
       ends = [m.end() for m in SENT_END.finditer(body)]
       if len(ends) < 3 or len(body) / len(ends) > 400:
           return text                                             # keep: too few sentence marks (verse, old text)
       if len(body) - ends[-1] > MAX_TAIL:
           return text                                             # keep: the broken part is too long to cut safely
       kept = body[:ends[-1]].rstrip()
       if len(kept) < MIN_CHARS:
           return True                                             # drop: too little complete text left
       return kept + "\n"                                          # fix
   ```

3. **Action:** Fix the text by cutting the broken last sentence, and keep the cut document. Drop only when fewer
   than 200 characters of complete sentences remain.

4. **Harm test:** Gold set of 103 documents (gold csv sha256 b523a045d9de): changed 0 of 103 (0.00%), dropped
   0 of 103 (0.00%). **PASS** (limit: 1% or 1 document, whichever is more, so at most 1). ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**.
   - Labelled C3 (12): fixes 6, drops 0, leaves 6.
   - Labelled `clean` (372): changes 5 (see side effects).

5. **Side effects:**
   - Five documents labelled `clean` are cut (`8fd373caf53d3263`, `223cf64b37291d9c`, `a0031ad042c4c5b9`,
     `2bb2e05c4eacf24f`, `e3b9c8a911fbd68b`). They are scanned book pages that do stop mid-sentence at the page end
     (`… ಅಂತ ಕ`), so the rule only removes the dangling fragment, but the label said clean.
   - Verse and old text with few `.` marks (`c2f29dd15ca2688f`) and a list ending in a comma (`7b1751ffb7f20ff0`)
     are no longer touched. The price is that some real cuts in such texts stay in.

## Medicine 4

1. **Disease:** D4, bad machine translation. Count: **7**. These are two different problems:
   - English blocks added to the Kannada text (3): `English Translation` blocks in scripture text (2), a broken
     English caption at the end (1).
   - Machine-translated Kannada prose (4): broken verb chains, wrong word choices and transliterations, in 2 of them
     mixed with other diseases.
   - `cda8a7fb4c34da99`: `English Translation\nThree-fourths of Purusha ascended; the other fourth that remained in
     this world proceeds repeatedly …`
   - `41ace5bf8346488c`: ends `(Minister ST Somashekar says Mysuru Dasara Celebration is happen this year)`
   - `1ae747ba1e3da7e9`: `ಇಂಟರ್ನೆಟ್ ಸ್ವತಃ ಇನ್ನೂ ಶೈಶವಾವಸ್ಥೆಯಲ್ಲಿ ಹೊರಹೊಮ್ಮಿತು ಮಾಡಿಲ್ಲ` (broken verb chain;
     "Mozilla" written `"Mozile"`).

2. **Medicine:** This medicine treats only the first problem. Remove each `English Translation` header line together
   with the English lines that follow it (until the first line that contains Kannada). Remove the last line when it
   is a whole English sentence in brackets (the same test as Medicine 2). Machine-translated Kannada prose has no
   safe regex, so this rule does not repair it: those 4 documents are left as they are.

   ```python
   TR_HEAD = re.compile(r"^\s*English Translation\.?\s*$")
   EN_SUMMARY = re.compile(r"^\s*\(\s*[A-Za-z][^\u0C80-\u0CFF()]{24,}\)\s*$")


   def _is_english_line(line):
       return len(re.findall(r"[A-Za-z]", line)) >= 25 and not re.search(r"[\u0C80-\u0CFF]", line)


   def medicine_d4(text):
       out, skip = [], False
       for l in text.rstrip().split("\n"):
           if TR_HEAD.match(l):
               skip = True
               continue
           if skip and (_is_english_line(l) or not l.strip()):
               continue                                            # English lines under the header
           skip = False
           out.append(l)
       if out and EN_SUMMARY.match(out[-1]):
           out.pop()                                               # "(broken English caption)" at the end
       new = "\n".join(out).rstrip() + "\n"
       return new if new.rstrip() != text.rstrip() else text
   ```

3. **Action:** Fix the text (remove the translation blocks and the caption). Do not drop.

4. **Harm test:** Gold set of 103 documents (gold csv sha256 b523a045d9de): changed 0 of 103 (0.00%), dropped
   0 of 103 (0.00%). **PASS** (limit: 1% or 1 document, whichever is more, so at most 1). ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**.
   - Labelled D4 (7): fixes 3 (both translation blocks and the caption), drops 0, leaves the 4 machine-translated
     prose documents.
   - Labelled `clean` (372): changes 0.

5. **Side effects:**
   - In a bilingual scripture edition, the English translation may be wanted. This rule throws it away; it keeps
     only the Kannada/Sanskrit part.
   - The machine-translated Kannada prose, 4 of the 7 documents, is not treated.
