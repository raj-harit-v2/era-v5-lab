# Medicine sheet: ind-gu-fw2 (Vedang)

Pack: 500 labelled documents (`labels.csv`): 157 labelled `clean`, 333 `fix`, 10 `drop`. Diseases found more than five times: C1 (179), D3 (285), A5 (30), C2 (13), F1 (19), C5 (20), A6 (18), D4 (12), B4 (6), G1 (9). Not above the threshold, so no medicine: C3 (4), G2 (4), C4 (2), D1 (2), A3 (2), B2 (2), F3 (1).

**Harm-test note (applies to all medicines).** The gold file of this pack (`ind-gu-fw2_gold.csv`) exists and has 80 documents, all of them in the pack and all labelled `clean` in `labels.csv`. I ran every medicine (A5, A6, B4, C1, C2, C5, D3, D4, F1, G1) on the full text of these 80 documents: **changed 0 and dropped 0 for every medicine, so all pass.** The gold set is small: 1% of 80 is 0.8 documents, so a single changed document would already be 1.3% and fail. I also ran every medicine on the 157 documents labelled `clean` in `labels.csv` as a second check: changed 0 and dropped 0 for every medicine. That proxy leaves out every document with a defect, so it is easier to pass than a larger gold set. Every code block below was run on all 500 documents and gives the same output as the numbers quoted.

## Medicine 1: C1 (Boilerplate)

1. **Disease:** C1, found in 179 of 500 labelled documents. Examples:
   - `bfbddfa37a31c087`: `Copyright © 2022-23 DB Corp ltd., All Ri…` at offset 1308
   - `41223f7be1bf6c66`: `Copyright © 2022-23 DB Corp ltd., All Ri` at offset 1361
   - `54525ab9a5efeb4b`: `સમગ્ર ઘટના CCTV આવ્યા સામે pic.twitter.c` at offset 93
2. **Medicine:** Delete whole lines that are site furniture: the Divya Bhaskar footer, the News18 promo, "read also" and `Tags:` lines, Instagram/tweet embeds, Saurashtra Kranti and GujjuRocks promo lines, source credits (`સૌજન્ય : દિવ્ય ભાસ્કર`), timestamps (`પોસ્ટનો સમય: …`), view counters (`57 , 1`), `Read More`, `જુઓ વિડીયો`, and the page promo `લેટેસ્ટ મનોરંજન, News અને Videos માટે પેજ લાઈક કરો`. In some newspaper pages the headline is stored after the body, followed by a final dateline (`(એજન્સી) તા.૬`); the headline line is deleted. The pattern must match the entire line.

   ```python
   import re

   LINE_PATTERNS = [
       r"Copyright © .*All Rights Reserved\.?",
       r"This website follows the DNPA Code of Ethics\.?",
       r"ગુજરાતી સમાચાર નો ખજાનો એટલે News18 ગુજરાતી\..*",
       r"View this post on Instagram",
       r"Tags:.*",
       r"(આ પણ વાંચો|તમે આ પણ વાંચી શકો છો)\s*[:\-–].*",
       r"આ પણ વાંચો\s*:?",
       r"(Subscribe|Visit) Saurashtra Kranti.*",
       r"Read (About Weather|National News|Saurashtra Kranti E-Paper).*",
       r"For any News, Event coverage.*",
       r"आपके किसी भी प्रकार.*",
       r"આપના કે આપની સંસ્થાના.*",
       r"You Can Find us on Google Play store too.*",
       r"Android: https?://\S+",
       r"— .{1,60}\(@\w+\).*\d{4}",
       r".*pic\.twitter\.com/\S+",
       r"(Article Source|Courtesy) : .*",
       r"[A-Z][a-z]{2} \d{1,2}, ?\d{4}, \d{1,2}:\d{2} [AP]M IST",
       r"Tap to Read ➤",
       r"[\d,]+ Views, \d+",
       r"વધુ વાંચો",
       r"અમારી (દર નવી|અન્ય) પોસ્ટ.*",
       r"તમે આ લેખ “ગુજ્જુ ગુજરાતી”.*",
       r"આવા વધુ સમાચારો માટે નીચેની લિન્ક.*",
       r"Author: GujjuRocks Team.*",
       r"\(નોંધ[ –-].*\)",
       r"નોંધ: આ વેબસાઇટ પર.*",
       r"ઉપરના આર્ટીકલના તમામ.*",
       r"ગુજરાતના તમામ સ્થળે પ્રેસ પ્રતિનિધિ.*",
       '\\"વંદે માતરમ ,ભારત માતાકી જય\\"',
       r"જંગ એ ગુજરાત ના વેબ ન્યૂઝ પોર્ટલ માટે",
       r"માનદ પ્રતિનિધિ નિમવાના છે.*",
       r"ચહેરો\d+ કલાક પહેલા",
       r"- લિંક કૉપિ કરો",
       r"🌺આરતીસોની🌺",
       r"-આરતીસોની ©",
   ]
   EXTRA = [
       r"\d{1,3} , \d{1,3}",
       r"લેટેસ્ટ મનોરંજન, News અને Videos માટે પેજ લાઈક કરો",
       r"Powered By .*",
       r"પોસ્ટનો સમય\s*:.*",
       r"સૌજન્ય\s*:?\s*(?:\n\s*)?દિવ્ય ભાસ્કર",
       r"ઇનપુટ્સ\s*:.*",
       r"જુઓ (?:આ )?વિડીયો",
       r"અમારી અન્ય પોસ્ટ પણ વાંચો\s*:?-?",
       r"સોશિયલ મીડિયા પ્લેટફોર્મ પર અમારી સાથે જોડાઓ",
       r"Visit Saurashtra Kranti Homepage here",
       r"Read About Weather here",
       r"(?:\.\.\. ?)?Read More",
       r"Team VTV.*",
   ]
   LINE = re.compile(r"^\s*(?:" + "|".join(LINE_PATTERNS + EXTRA) + r")\s*$\n?", flags=re.M)
   # headline line that is stored after the body, just before a final dateline such as "(એજન્સી) તા.૬"
   TRAIL = re.compile(r"\n[^\n]+\n(?=\(?[^\n]{0,30}\)?[ ,]*તા\.? ?[\d૦-૯]+\s*$)")

   def medicine(text):
       return TRAIL.sub("\n", LINE.sub("", text))
   ```

3. **Action:** fix. Only whole lines (and the trailing headline) are removed; a phrase inside a sentence is left alone.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 147 of 179.
5. **Side effects:** Misses C1 that is not on its own line or comes from another site: `MUST READ:` and `READ ALSO` glued to text, a `ન્યૂઝ18 ગુજરાતી :` prefix glued to the first sentence, `જુઓ આગળની સ્લાઈડ્સ…`, source lines such as `શ્રોત: ગ્રામીણ ટુડે ન્યુઝ`, other wording of the English "This article is available in…" footer, and `- ` bullet lists of related links. The publisher lines (Divya Bhaskar, News18, Saurashtra Kranti, GujjuRocks) will not match other sites. A real one-line sentence equal to `વધુ વાંચો` would be deleted. If a real article ends with a headline-like line before a dateline, that line is deleted.

## Medicine 2: D3 (Mixed language)

1. **Disease:** D3, found in 285 of 500 labelled documents. Examples:
   - `9c013a675712ff90`: `vaishnav` at offset 114
   - `bbd78664eb97d1ae`: `PTN` at offset 1145
   - `b97cb6db98d14b11`: `Pathan` at offset 25
2. **Medicine:** Delete whole lines that have no Gujarati letter and at least 25 Latin letters (embedded tweets, English footers and headings, transliterated verses). Words and acronyms inside a Gujarati sentence (`CBSE`, `Paytm`, `S10માં`) are natural mixing and are not touched.

   ```python
   import re

   GU = re.compile(r"[઀-૿]")
   LAT = re.compile(r"[A-Za-z]")

   def medicine(text):
       # Keep a line unless it is English-only and long.
       return "\n".join(l for l in text.split("\n")
                        if GU.search(l) or len(LAT.findall(l)) < 25)
   ```

3. **Action:** fix. Natural Gujarati-English mixing is not touched (label it, do not judge it); only English-only lines are removed.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 97 of 285.
5. **Side effects:** It acts on 97 of 285 documents; the rest are natural mixing and need no medicine. Most of the changed documents are also changed by C1. It removes a real English quotation or English headline that is the point of the document, and a mostly-English document could lose most of its text, so run it after a language check. Romanised Hindi in Latin script is removed too, but that is really D2 and needs its own rule.

## Medicine 3: A5 (Wrong normal form (broken vowel signs))

1. **Disease:** A5, found in 30 of 500 labelled documents. Examples:
   - `98b9ca997dc64e33`: `મોદીેેએ` at offset 523 (`0AAE 0ACB 0AA6 0AC0 0AC7 0AC7 0A8F`)
   - `87229021ccbc99cf`: `સ્કૂલોેને` at offset 147 (`0AB8 0ACD 0A95 0AC2 0AB2 0ACB 0AC7 0AA8 0AC7`)
   - `245157868125833d`: `એન્જિીનિયરીંગ` at offset 621 (`0A8F 0AA8 0ACD 0A9C 0ABF 0AC0 0AA8 0ABF 0AAF 0AB0 0AC0 0A82 0A97`)
2. **Medicine:** Repair the broken vowel-sign sequences left by legacy-font conversion: a doubled sign (`તાલુુકા`, `વગેેરે`), `ાે` → `ો` (`જાેકે` → `જોકે`), `ાૈ`/`ૈા` → `ૌ`, `અે` → `એ`, a sign after an independent vowel (`આાસન`), a nukta after a sign (`જે઼`). `રૂા` (rupee shorthand) is correct and is protected.

   ```python
   import re

   SIGN = "\u0abe-\u0ac5\u0ac7-\u0ac9\u0acb\u0acc"      # Gujarati vowel signs

   def medicine(text):
       t = text.replace("રૂા", "\0")                      # rupee shorthand is correct, protect it
       t = t.replace("\u0a85\u0ac7", "\u0a8f")            # અ + ે  ->  એ
       t = re.sub(f"([{SIGN}])\\1+", r"\1", t)           # the same sign twice
       t = (t.replace("\u0abe\u0ac7", "\u0acb")          # ાે -> ો
             .replace("\u0abe\u0ac8", "\u0acc")          # ાૈ -> ૌ
             .replace("\u0ac8\u0abe", "\u0acc"))         # ૈા -> ૌ
       t = re.sub(f"([\u0a85-\u0a94])[{SIGN}]", r"\1", t)  # sign after an independent vowel
       t = re.sub(f"([{SIGN}])[{SIGN}]", r"\1", t)         # any other two signs: keep the first
       t = re.sub(f"([{SIGN}\u0a82])\u0abc", r"\1", t)    # nukta after a sign
       return t.replace("\0", "રૂા")
   ```

3. **Action:** fix. The sign sequences are repaired in place; the rest of the text stays. NFC alone does not fix these.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 26 of 30.
5. **Side effects:** Some repairs are a guess: when two different signs are stacked (`સાથૂી`) the rule keeps the first, which may be the wrong one, so the word is still wrong. A wrong consonant is not found. Wrong letters that are valid Gujarati are invisible to it. Do not run it on text that is already NFC and correct: it changes nothing there, but it is not a spell checker.

## Medicine 4: C2 (Repeated lines)

1. **Disease:** C2, found in 13 of 500 labelled documents. Examples:
   - `98b9ca997dc64e33`: `અંબાજી મંદિરના મુખ્ય શિખરને સુવર્ણમય બનાવવા` at offset 998
   - `a42d054d2bda09d0`: `તમારું પોતાનું વ્યક્તિ…` at offset 25817
   - `b85dd656e0a0f691`: `રાખી સાવંતની માતાનું નિધન,બ્રે` at offset 8340
2. **Medicine:** Keep the first copy of a line longer than 15 characters and delete later identical copies. Lines ending in `,` or `…` are kept, because poems repeat refrains.

   ```python
   def medicine(text):
       seen, out = set(), []
       for line in text.split("\n"):
           key = line.strip()
           if len(key) > 15 and not key.endswith((",", "…")):   # keep poem refrains
               if key in seen:
                   continue
               seen.add(key)
           out.append(line)
       return "\n".join(out)
   ```

3. **Action:** fix. Keep the first copy, delete the later copies.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 12 of 13.
5. **Side effects:** Misses repeats that are short (a dateline under 16 characters such as `અમદાવાદ, તા.ર`), differ in a number (`59300 રૂપિયા`), or were cut at a different place. A deliberate repeated slogan or chorus that does not end in `,` or `…` would be deleted.

## Medicine 5: F1 (Personal data)

1. **Disease:** F1, found in 19 of 500 labelled documents. Examples (type and offset only, no values):
   - `71da416a839a010b`: private name next to a home locality at offset 886
   - `896ee117249ce192`: phone at offset 479
   - `5a8e7392dd213881`: phone at offset 1651
2. **Medicine:** Replace email addresses and phone numbers (10-digit mobiles, `+91` numbers, landlines with area code, in Latin or Gujarati digits) with `<EMAIL>` and `<PHONE>`. example.com placeholder addresses are left for B4.

   ```python
   import re

   EMAIL = re.compile(r"[\w.+-]+@(?!example\.com)[\w-]+\.[\w.]+")
   PHONE = re.compile(
       r"(?<![\d.])(?:\+91[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)"   # mobile
       r"|(?<!\d)\d{3}\d{3}\d{4,}(?!\d)"                       # long digit run
       r"|\b0\d{2,4}[ -]\d{6,8}\b")                            # landline

   def medicine(text):
       return EMAIL.sub("<EMAIL>", PHONE.sub("<PHONE>", text))
   ```

3. **Action:** fix. The values are masked and the rest of the document stays.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 17 of 19.
5. **Side effects:** Does not find the private-name-plus-locality case, because a regex cannot find names. It masks public helpline numbers (a government employment helpline) that are not private data. A Latin digit run of 10 or more digits that is an order or ID number is masked as a phone number.

## Medicine 6: C5 (Lists of keywords or links)

1. **Disease:** C5, found in 20 of 500 labelled documents. Examples:
   - `6c34ae8bfde1bf78`: `Tags:` at offset 1880
   - `8fb11ce7723f2e80`: `Tags:` at offset 2150
   - `111b541c64c8d29b`: `Tags:` at offset 1943
2. **Medicine:** Delete `Tags:` lines that have two or more commas or eight or more words, and lines that are a comma list of five or more mostly-Latin items with no digit, colon or full stop.

   ```python
   import re

   def medicine(text):
       keep = []
       for line in text.split("\n"):
           s = line.strip()
           latin = len(re.findall("[A-Za-z]", s))
           letters = max(1, len(re.sub(r"\W", "", s)))
           tags = s.startswith("Tags:") and (s.count(",") >= 2 or len(s.split()) >= 8)
           word_list = (len(s.split(",")) >= 5 and latin > 0.7 * letters
                        and not re.search(r"[:\d]", s) and not s.endswith("."))
           if not (tags or word_list):
               keep.append(line)
       return "\n".join(keep)
   ```

3. **Action:** fix. Delete the tag or keyword line only.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 18 of 20.
5. **Side effects:** Misses keyword lists written in Gujarati (`ugvcl બિલ ઑનલાઇન કેવી રીતે જોવું, …`) and `- ` bullet lists of links. A real `Tags:` line with a few words is deleted, which is intended, but it is also boilerplate (C1).

## Medicine 7: A6 (Wrong or mixed script)

1. **Disease:** A6, found in 18 of 500 labelled documents. Examples:
   - `0992299d9580a5a2`: `તેcણે` at offset 465 (`0AC7 0063 0AA3`)
   - `7c6b6253138b22d0`: `તocસ` at offset 357 (`006F 0063`)
   - `194f2b945bfbeb1f`: `क` at offset 670 (`0915`)
2. **Medicine:** Two rules. **A6a:** if a lowercase Latin run of 1 to 8 letters has a Gujarati letter on both sides, drop the document. **A6b:** otherwise delete lines that contain Devanagari letters; if more than 30% of the lines are deleted, drop the document. The Devanagari danda `।` is not counted.

   ```python
   import re

   SANDWICH = re.compile(r"[઀-૿][a-z]{1,8}[઀-૿]")
   DEVANAGARI = re.compile(r"[\u0900-\u0963\u0966-\u097f]")      # letters, not the danda

   def medicine(text):
       if SANDWICH.search(text):
           return None                       # drop the document
       lines = text.split("\n")
       keep = [l for l in lines if not DEVANAGARI.search(l)]
       if len(keep) < 0.7 * len(lines):
           return None                       # drop the document
       return "\n".join(keep)
   ```

3. **Action:** A6a drops the document (a corrupted word makes the text around it unreliable). A6b deletes Hindi lines and drops the document if more than 30% of lines go.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 15 of 18.
5. **Side effects:** It acts on only 15 of 18 documents. It does not cover Gujarati letters used as digits (`ર01ર`, `ર૯પ`), a U+201A comma-like character in place of `ૂ`, candra signs (`અપૅણ`, `નેતાઑ`), long ઊ for ઉ, wrong letters (`વિઘુત`), or a lone Latin letter between spaces (`બનાવવી l હોમમેઇડ`). The digit-letter case can be repaired by a rule but only inside numbers, which I did not write; the others need a spelling model. The 30% threshold is a proposal and has not been tuned. Real Hindi or Sanskrit quotations in a Gujarati article are removed even though they are correct text. A lowercase brand glued between two Gujarati letters is dropped. Dropping a whole document for one corrupted word loses a lot of good text; if the drop rate on the real gold set is above 1%, change A6a to remove only the affected sentence.

## Medicine 8: D4 (Bad machine translation)

1. **Disease:** D4, found in 12 of 500 labelled documents. Examples:
   - `014f6b1dc9a324be`: `ક્રીપ પ્રતિરોધક, પર્યાવરણીય તણાવ ક…` at offset 339
   - `f65c324b39b9db3f`: `ક્યુટ કંપનીએ અનાવરણ કર્યું ની` at offset 0
   - `b910fdfe72d2ac0a`: `'પોતાને વરવા'` at offset 1160
2. **Medicine:** Drop the document if a lowercase Latin run of 1 to 8 letters sits between Gujarati letters (the same sign as A6a). This is the only part of D4 that a rule can see; the rest needs a quality model (see side effects).

   ```python
   import re

   SANDWICH = re.compile(r"[઀-૿][a-z]{1,8}[઀-૿]")

   def medicine(text):
       # Latin letters glued inside a Gujarati word: the translation is broken, drop the document.
       return None if SANDWICH.search(text) else text
   ```

3. **Action:** drop. A broken translation cannot be repaired by a rule.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 4 of 12.
5. **Side effects:** Acts on only 4 of 12 documents. It misses translations that are wrong but have no Latin letters: repeated or untranslated phrases (`મિક્સ કરો અને મિક્સ કરો`), incoherent spam text, and unnatural wording. Those need a language-model quality score, which I did not run. D4 labels are my judgement, not a measurement, so the acts-on number is only a lower bound for how bad the disease is. Dropping documents costs data.

## Medicine 9: B4 (Template and code junk)

1. **Disease:** B4, found in 6 of 500 labelled documents. Examples:
   - `b67a6cca719bf1d7`: `#IndiaWantsCrypto` at offset 3353
   - `ec290e88b613101c`: `[email protected]` at offset 2229
   - `a4ab5516e2836afa`: `[ઇમેઇલ સુરક્ષિત]` at offset 11188
2. **Medicine:** Delete template and placeholder junk: `[ઇમેઇલ સુરક્ષિત]` and `[email protected]` (email obfuscation placeholders), example.com placeholder addresses, `{{ … }}`, `${ … }`, and the whole words `undefined`, `NaN`, `null`.

   ```python
   import re

   JUNK = re.compile(r"\[ઇમેઇલ સુરક્ષિત\]|email@example\.com|firstname\.lastname@example\.com"
                     r"|\[email\s*protected\]|\{\{.*?\}\}|\$\{.*?\}|\bundefined\b|\bNaN\b|\bnull\b")

   def medicine(text):
       return JUNK.sub("", text)
   ```

3. **Action:** fix. Delete the junk token; the sentence stays.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 4 of 6.
5. **Side effects:** Misses hashtags such as `#IndiaWantsCrypto` (it is part of the post). The word `null` or `undefined` inside a real English quotation is deleted. Email-obfuscation placeholders in other languages or spellings will not match.

## Medicine 10: G1 (Detached or orphaned marks)

1. **Disease:** G1, found in 9 of 500 labelled documents. Examples:
   - `a4ab5516e2836afa`: `કરતા ંચું` at offset 2139 (`0A95 0AB0 0AA4 0ABE 0020 0A82`)
   - `94a0b1e34f48f0ad`: `અર્ધગ્ધ` at offset 1246 (`0A85 0AB0 0ACD 0AA7 0A97 0ACD 0AA7`)
   - `774bfbc8ab7805ba`: `ા ં` at offset 677 (`0ABE 0020 0A82`)
2. **Medicine:** Delete a space that sits between a Gujarati consonant, virama or vowel sign and a following vowel sign or anusvara (`જ િ` → `જિ`, `ા ં` → `ાં`, `કે ે` → `કેે`). A word cannot start with a vowel sign, so that space is not a real word break.

   ```python
   import re

   # space before a vowel sign / anusvara, after a consonant, virama or vowel sign
   DETACHED = re.compile("(?<=[\u0a95-\u0ab9\u0acd\u0abe-\u0acc]) +(?=[\u0abe-\u0acc\u0a82])")

   def medicine(text):
       return DETACHED.sub("", text)
   ```

3. **Action:** fix. Only the stray space is removed; the rest of the text stays.
4. **Harm test:** **gold set** (`ind-gu-fw2_gold.csv`, 80 documents, all 80 are `clean` in labels.csv): changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). Proxy set (all `clean` rows of labels.csv), n=157: changed 0, dropped 0 (0.0%) → **PASS** (limit 1%). On my labelled documents with this disease it acts on 7 of 9.
5. **Side effects:** It acts on 7 of 9 documents. It cannot bring back a lost letter (`ૂંટણીને`, `અર્ધગ્ધ` lost a letter), so those words stay wrong; a stray full stop between the pieces (`જ્ .ા`) is not handled. If the space was a real word break and the next word lost its first letter (`કરતા ંચું`), or the space follows a vowel sign that belongs to a whole word (`નવી િદલ્હી`, `જો િમત્રો`), the join glues the pieces into a non-word. After this rule the word is still wrong, but it is one word instead of two. Two of the nine documents are labelled `drop`, so this rule gains little there. In the A5 documents 328 and 461 it leaves a doubled sign that A5 must remove, so run A5 and G1 together.
