# Medicine sheet: ind-hi-hplt (gmrammohan15)

Write one section for each disease that you found more than five times.

**Status (30 Oct):** built from all 500 labelled rows. Fourteen diseases occur more than five times; sections are
ordered by count.

**How the numbers were measured.** Every medicine was run on all 500 labelled documents, which is the whole pack. The
word lexicon, the shared-line list and the site lists that some medicines use were built leave-one-out: a document is
never cured with statistics that include itself.
- **cures**: labelled documents with the disease that the medicine changes or drops.
- **side effects**: labelled documents *without* the disease that it changes or drops.
- **clean touched**: documents I reviewed as `clean` that it changes or drops (target 0).

**Harm test:** the Hindi gold set (`teams/02-data-b/gold/`) is not published yet, so every harm test below is
**pending**. The runner is ready: it applies each medicine to the gold documents and fails a medicine that changes or
drops more than 1% of them. Until then the "clean touched" count on my reviewed rows stands in for it: it is 0 for
every medicine.

**Changes since the 150-row sheet.** At 500 rows three rules touched clean documents, and each was tightened:
- C1 cut real speech lines (`साथियों,` in three `narendramodi.in` speeches), so a shared line that ends like a sentence
  is no longer boilerplate, and only a boilerplate phrase (not a shared line) starts the tail cut.
- D4 dropped clean stories on `hindi.matrubharti.com`, a user-posting site with one machine-translated page, so a site
  now needs at least two *other* reviewed D4 drops.
- D5 tagged clean pages of large news sites with one translated article, so the same two-other-pages rule applies.

Shared definitions used by the code below:

```python
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
```

## Medicine 1: C1 boilerplate

1. **Disease:** C1, 275 of 500 documents (212 fix, 63 drop). Examples:
   - `f6f77aeff3b688d0`: `यह भी पढ़ें` at offset 19713 (related-article teaser).
   - `57294dfeff306304`: `कॉपीराइट एससी मनोवैज्ञानिक उद्यम लिमिटेड` at offset 8538 (copyright footer).
   - `7261baa0a3edfb1d`: `No comments:` at offset 8983 (Blogger comment widget).
   Bylines, desk slugs and site-name prefixes are also C1 (reviewer policy, 30 Oct).
2. **Medicine:** remove template lines that also appear in 2+ other documents (10+ characters, not ending like a sentence),
   and short lines (60 chars or less) that contain a boilerplate phrase. From the first boilerplate-phrase line in the
   last 30% of the document, cut the whole tail ("Related posts", comment form, rating widget, share buttons).
   ```python
   C1_PHRASES = [
       "यह भी पढ़ें", "ये भी पढ़ें", "इसे भी पढ़ें", "यह भी पढे", "ये भी पढे", "और पढ़ें", "आगे पढ़ें", "पूरा पढ़ें",
       "संबंधित खबर", "सम्बंधित खबर", "संबंधित लेख", "संबंधित पोस्ट", "लेटेस्ट खबर", "ताज़ा खबर", "ताजा खबर",
       "शेयर करें", "शेयर करे", "लाइक करें", "फॉलो करें", "सब्सक्राइब", "डाउनलोड करें", "हमसे जुड़ें", "हमें फॉलो",
       "कमेंट", "टिप्पणी करें", "प्रातिक्रिया दे", "प्रतिक्रिया दें", "अपनी राय", "जवाब दें", "रद्द करें",
       "सर्वाधिकार सुरक्षित", "सभी अधिकार सुरक्षित", "कॉपीराइट", "विज्ञापन", "गोपनीयता नीति", "अस्वीकरण", "संपर्क करें",
       "हमारे बारे में", "Share on", "WhatsApp", "Facebook", "Twitter", "Telegram", "Instagram", "YouTube", "Pinterest",
       "LinkedIn", "Read More", "Read more", "Click here", "Subscribe", "Follow us", "Advertisement", "Copyright", "©",
       "All Rights Reserved", "All rights reserved", "Privacy Policy", "Disclaimer", "Terms of", "Cookie", "cookies",
       "Tags:", "Tags :", "Posted in", "Filed under", "Leave a Reply", "Leave a Comment", "Comments", "Next Post",
       "Previous Post", "Related Posts", "Home »", "Home >", "Skip to content", "Menu"]
   C1_RE = re.compile("|".join(map(re.escape, sorted(C1_PHRASES, key=len, reverse=True))))
   SENTENCE_END = re.compile("[।॥!?,.]$")

   def cure_c1(text, shared_lines):        # shared_lines: lines that also occur in 2+ other documents of the pack
       out, pos, n = [], 0, len(text)
       for line in text.split("\n"):
           nl = norm_line(line)
           shared = len(nl) >= 10 and nl in shared_lines and not SENTENCE_END.search(nl)   # repeated sentences are content
           phrase = bool(nl) and len(nl) <= 60 and bool(C1_RE.search(nl))
           if phrase and pos > 0.7 * n:
               break                           # boilerplate tail: cut everything after it
           if not (shared or phrase):
               out.append(line)
           pos += len(line) + 1
       return "\n".join(out).rstrip()
   ```
   Example (`e355f1c4e9fda943`, offset 3357): `…कई परिक्षाएं भी टाल दी गई है.⏎यह भी पढ़ें⏎- ज़िन्दगी से जनाज़े तक…` becomes `…कई परिक्षाएं भी टाल दी गई है.`
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 108 of 275; side effects 2 of 225; clean touched 0. Changes 110 of 500 pack documents.
5. **Side effects:** the 2 side effects are dropped pages where a content heading contains a phrase (`Ubuntu डाउनलोड
   करें…` in a how-to, `इस गोपनीयता नीति की प्रयोज्यता` in a privacy-policy page). The medicine misses boilerplate that
   is long, unique to one page, or written as a normal sentence (167 of 275), and most bylines and desk slugs
   (`ब्यूरो रिपोर्ट`, agency credits), which need per-site rules. The shared-line rule needs site-level statistics at
   corpus scale, not pack-level.

## Medicine 2: D4 machine translation

1. **Disease:** D4, 95 of 500 documents (79 drop, 16 fix). Examples:
   - `a85a2363de961b2e`: `मैं अपने हृदय की गहराई से उसे धन्यवाद दिये बिना रह पाया` at offset 23753 (negation lost: "could not help thanking" became "could help thanking").
   - `ca38e3770cd4bd18`: `भी ianbolshuyu मूल्य किग्रा` at offset 2449 (untranslated Russian transliteration inside Hindi).
   - `7a2bc38b934a51ad`: `तेजी से dorozhanie Bitcoin` at offset 4146 (same).
2. **Medicine:** there is no text repair for wrong meaning. Drop documents from sites with at least two other reviewed
   machine-translated drops, and stitched spam pages (detected by the spam rule shared with C4 and C5).
   ```python
   SPAM_TERMS = ["विदेशी मुद्रा", "द्विआधारी विकल्प", "बाइनरी विकल्प", "बिटकॉइन", "पैसे कमा", "PAMM", "Forex",
                 "forex", "binary option", "Bitcoin"]

   def is_spam(text):           # only spam-specific terms: निवेश or ट्रेडिंग also occur in real business news
       hits = {t: text.count(t) for t in SPAM_TERMS if t in text}
       return sum(hits.values()) >= 4 and len(hits) >= 2

   def cure_d4(text, url, mt_sites):   # mt_sites: sites with 2+ other reviewed D4 drops (healthcarestudies.in, ...)
       return None if urlparse(url).netloc in mt_sites or is_spam(text) else text
   ```
3. **Action:** drop the document.
4. **Harm test:** pending (gold set). Pack check (leave-one-out site list): cures 39 of the 79 D4 drops; side effects
   5 of 405; clean touched 0.
5. **Side effects:** the 5 side effects are pages I kept as fix on machine-translation sites (`news.bestrojgar.com`),
   and 1 of the 16 D4 fix documents is dropped the same way. Misses machine translation on sites with fewer than three
   reviewed drops (40 of 79), including single MT pages on mixed user-posting sites, which the site rule now protects
   on purpose. At corpus scale the site list must be replaced or backed by a model-based detector (e.g. a classifier
   on round-trip translation similarity or perplexity), because a site list never generalises to new sites.

## Medicine 3: D3 natural code-mixing

1. **Disease:** D3, 85 of 500 documents (55 fix, 17 drop, 13 clean; the fix and drop verdicts come from other codes). Examples:
   - `f6f77aeff3b688d0`: `back to the basics, back to the nature` at offset 5707 (an English phrase quoted in a Hindi article).
   - `57294dfeff306304`: `spaying और neutering` at offset 4622.
   - `84b3adb7174dfd68`: `youtube पर videos upload करके` at offset 5424.
2. **Medicine:** none. Hindi-English mixing is how Hindi is written online, and the model must learn it. Per the
   reviewer policy, D3 alone means `clean`. English boilerplate (share buttons, SEO headings) is removed by the C1
   medicine, not here.
   ```python
   def cure_d3(text):
       return text
   ```
3. **Action:** keep (no change).
4. **Harm test:** pending (gold set); the medicine changes nothing, so it changes 0 gold documents. Pack check: 0 changes.
5. **Side effects:** none from the medicine. The risk is in labelling: an English run that is really scraped junk
   must be coded C1 or C5, not D3.

## Medicine 4: A5 legacy-font conversion damage

1. **Disease:** A5, 84 of 500 documents (78 fix, 6 drop). Text typed in Krutidev/Chanakya fonts and converted to Unicode. Examples:
   - `a02caf8e245bbcf3`: `परेषानियों` at offset 326 (`ष` written for `श`).
   - `1dc03c85e4d5e1db`: `चित्राें` at offset 27 (`ा` + `ें` for `ों`).
   - `3c93f63e4f149867`: `देष` at offset 122; `e96fe1f3108f353f`: `ऋऊख` at offset 7780.
2. **Medicine:** fixed character rules, then a word-level rule for `ष` / `श`. A blind `ष` to `श` replacement is
   wrong (`राष्ट्र`, `कृषि`, `क्षेत्र` are correct), so a word is switched only when the `श` spelling is clearly the
   common word in clean Hindi text.
   ```python
   A5_RULES = [
       (re.compile("र्इ"), "ई"),
       (re.compile("ध्द"), "द्ध"),                                # बौध्दिक -> बौद्धिक
       (re.compile("द्बारा"), "द्वारा"),
       (re.compile("\u093C\u093C+"), "\u093C"),                   # double nukta
       (re.compile(f"([डढ])([{MATRA}])\u093C"), "\\1\u093C\\2"),  # बडे़ -> बड़े
       (re.compile(f"([डढ])([कखगनलमतरसद])\u093C"), "\\1\u093C\\2"),  # सडक़ -> सड़क, लडऩे -> लड़ने
       (re.compile("\u093E\u0947"), "\u094B"),                    # ाे -> ो
       (re.compile("\u093E\u0948"), "\u094C"),                    # ाै -> ौ
       (re.compile(f"([{MATRA}])\\1"), "\\1"),                    # केे -> के
   ]

   def fix_sha(word, lexicon):         # lexicon: Counter of word frequencies in clean Hindi text
       if "ष" not in word:
           return word
       best, best_n = word, lexicon[word]
       pos = [i for i, c in enumerate(word) if c == "ष"]
       for mask in range(1, 2 ** len(pos)):
           alt = "".join("श" if i in pos and mask >> pos.index(i) & 1 else c for i, c in enumerate(word))
           if lexicon[alt] > best_n:
               best, best_n = alt, lexicon[alt]
       return best if best_n >= 3 and best_n > 3 * lexicon[word] else word

   def cure_a5(text, lexicon):
       for rx, rep in A5_RULES:
           text = rx.sub(rep, text)
       return WORD_RE.sub(lambda m: fix_sha(m.group(), lexicon), text)
   ```
   Examples: `परेषानियों` → `परेशानियों`, `चित्राें` → `चित्रों`, `देष` → `देश` (while `राष्ट्र` in the same sentence stays).
   In `3c93f63e4f149867` the `ष` rule corrects 61 words (`प्रकाष`, `अधिषासी`, `प्रदर्षनी`, `विषेष` → `विशेष`) and leaves every correct `ष` word alone.
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 43 of 84; side effects 5 of 416, all five correct cures of
   damage the labels missed (`आवष्यकताओं`, `दृष्य`, `स्थाानों`, `ऋषिकेष`, `परिदृष्य`); clean touched 0.
5. **Side effects:** does not repair a misplaced reph (`सामथ्र्य`, `दुव्र्यहार`, `बुकर्ा`), an anusvara typed before
   the vowel sign (`हंै`), or Latin junk left by the converter (`Ÿ` in `प्रवृŸिागत`, `ª` in `टैªनिंग`, `÷`); these need a
   full Krutidev reverse map and are most of the 41 uncured documents. The `ष` rule can miss rare words
   (`निर्देषानुसार`) and could wrongly switch a rare correct `ष` word whose `श` twin is common; it needs a large clean
   lexicon (pack-level counts are small).

## Medicine 5: C4 two documents joined

1. **Disease:** C4, 47 of 500 documents (25 drop, 22 fix). Examples:
   - `ca38e3770cd4bd18`: `ज्यादातर मामलों में पुलिस ने 32 बोर पिस्तौल` at offset 957 (a crime story inside a forex page).
   - `8fed2d4464e4cc06`: `आज आपका दिन मिला जुआ असर देने वाला रहेगा` at offset 3368 (a horoscope inside a forex page).
   - `84b3adb7174dfd68`: `वायुयान का नोदक नोदक या प्रोपेलर` at offset 7846.
   Reviewer policy (30 Oct): separable full stories are fix; cut-off teasers or 5+ tiny briefs (under 500 characters
   on average) are drop; a headline or dateline is not a document boundary, so news round-ups are C4.
2. **Medicine:** drop stitched spam pages with the spam rule (Medicine 2); cut-off teaser pages are dropped by the C3
   medicine. For the rest there is no safe split point in this pack, so keep them.
   ```python
   def cure_c4(text):
       return None if is_spam(text) else text
   ```
3. **Action:** drop the document (stitched spam); otherwise keep.
4. **Harm test:** pending (gold set). Pack check: cures 11 of 47 (11 of the 25 drops); side effects 0 of 453; clean touched 0.
5. **Side effects:** the 22 fix documents (news round-ups of full stories) are kept whole by design; a splitter on
   datelines (`नई दिल्ली।`, `(वार्ता)`) and headline lines could separate them later. Non-spam drops made of tiny
   briefs are missed (14 of 25).

## Medicine 6: G4 fake danda

1. **Disease:** G4, 44 of 500 documents (34 fix, 10 drop). ASCII `|`, Latin `I` or `l`, or `II` typed instead of `।` / `॥`. Examples:
   - `f6f77aeff3b688d0`: `नहीं मिला|` at offset 6860.
   - `7952deb7a1c71995`: `सोचने को विवश कर सकती है|` at offset 8222.
   - `4b82ad7e92695e55`: `किया हैl` at offset 14803 (Latin `l`, about 300 times in this document).
2. **Medicine:** replace the fake mark only where it really ends a sentence: after a Hindi letter (or closing quote),
   at least 25 characters after the previous `।`, `|` or line break, and followed by Hindi or a line end. Title and
   menu separators (`शीर्षक | साइट`, `विज्ञान | गणित`) and English (`मैं I am`) do not match.
   ```python
   G4_FAKE = re.compile(f"(?<=[{LETTER}\"'”’])\\s?(II|\\|\\||[Il|])"
                        f"(?=[ \\t]+[\u0904-\u0939\u0958-\u0961\"'“‘]|[ \\t]*\\n|[ \\t]*$)")

   def cure_g4(text):
       def rep(m):
           start = max(text.rfind(ch, 0, m.start()) for ch in "।|\n")
           if m.start() - start - 1 < 25:
               return m.group()                       # short segment: a separator, not a sentence end
           return "॥" if len(m.group(1)) == 2 else "।"
       return G4_FAKE.sub(rep, text)
   ```
   Example (`f6f77aeff3b688d0`): `मालिक नहीं मिला| नौकर से` → `मालिक नहीं मिला। नौकर से`.
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 42 of 44; side effects 10 of 456 (8 in documents already
   dropped for other reasons); clean touched 0.
5. **Side effects:** a title separator after a long title is converted in 2 fix documents (`अश्वत्थामा लुक | नाग
   अश्विन…`, `राशिफल 16 जून | प्रेमियों…`). A Roman numeral after Hindi is taken for a danda (`एनसीएए डिवीजन I सॉकर` →
   `डिवीजन। सॉकर`), and long menu items separated by `|` can be converted. Misses `*` used as a danda
   (`91ad466ec2dd9ef4`) and lowercase `i`.

## Medicine 7: D5 translationese

1. **Disease:** D5, 31 of 500 documents (28 fix, 3 drop). Grammatical Hindi with English sentence structure, mostly translated sermons and PR copy. Examples:
   - `a85a2363de961b2e`: `को दिखने में एक इंसान जैसा बनाया` at offset 1762.
   - `7261baa0a3edfb1d`: `को धन्यवाद करती हैं` at offset 4573 (English "thank someone" pattern).
   - `d25f5eb32b944379`: `मैंने अपनी राय को जन्म दिया` at offset 8196 ("gave birth to my opinion").
2. **Medicine:** no text repair (rewriting style needs a model). Keep the document, and tag it so the data mix can
   down-weight translated text. The tag uses sites with at least two other reviewed translationese pages.
   ```python
   def flag_d5(url, translated_sites):    # e.g. hi.godfootsteps.org, hi.easternlightning.org
       return urlparse(url).netloc in translated_sites
   ```
3. **Action:** fix (keep, tag `translated`), per the reviewer policy that D5 alone is `fix`.
4. **Harm test:** pending (gold set); the medicine never changes or drops text, so it changes 0 gold documents. Pack
   check: tags 7 of 31; tags 2 others (fix pages on `www.orfonline.org`); clean tagged 0.
5. **Side effects:** misses translationese on sites with fewer than three reviewed pages (24 of 31). A native page
   hosted on a translation site would be tagged. At corpus scale a classifier (translated vs native Hindi) should
   replace the site list.

## Medicine 8: F1 personal data

1. **Disease:** F1, 31 of 500 documents (23 fix, 8 drop). Examples (type and position only; values are never copied):
   - `157a92dae8c7615d`: phone at offset 9777 (an author's mobile in a contact line).
   - `4b82ad7e92695e55`: email at offset 28595 (a private person's contact block).
   - `3c8e378530fce8ba`: vehicle registration number at offset 145.
   Private home addresses (including name plus village in crime news), letter writers' addresses and vehicle plates
   are F1 (reviewer policy, 30 Oct); a name alone is not.
2. **Medicine:** replace each value with a typed placeholder (`<PHONE>`, `<EMAIL>`, `<LANDLINE>`, `<AADHAAR>`, `<PAN>`).
   ```python
   EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
   PHONE_RE = re.compile(r"(?<![\d])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?![\d])|\+\d{1,3}[\s-]?\d(?:[\s-]?\d){6,13}(?![\d])")
   LANDLINE_RE = re.compile(r"(?<![\d])0\d{2,4}[\s-]\d{6,8}(?![\d])|(?<![\d])0\d{2,4}[\s-]\d{3,4}[\s-]\d{3,4}(?![\d])"
                            r"|\(\+?\d{1,5}\)\s?\d{3,8}[\s-]?\d{3,8}(?![\d])")
   OTHER_PHONE_RE = re.compile(r"(?<![\d-])(?:\d{5}-\d{5}|\d{2} \d{2} \d{3} \d{4}|1800[ -]?\d{3}[ -]?\d{3,4})(?![\d])")
   AADHAAR_RE = re.compile(r"(?<![\d])\d{4}\s\d{4}\s\d{4}(?![\d])")
   PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
   F1 = [("<EMAIL>", EMAIL_RE), ("<PHONE>", PHONE_RE), ("<LANDLINE>", LANDLINE_RE), ("<PHONE>", OTHER_PHONE_RE),
         ("<AADHAAR>", AADHAAR_RE), ("<PAN>", PAN_RE)]

   def cure_f1(text):
       for tag, rx in F1:
           text = rx.sub(tag, text)
       return text
   ```
   Example (`157a92dae8c7615d`, offset 9777): `मोबाइल : <value>, ईमेल : <value>` → `मोबाइल : <PHONE>, ईमेल : <EMAIL>`.
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 20 of 31; side effects 1 of 469; clean touched 0.
5. **Side effects:** masks number ranges that look like phones (a rouble price range in `1f6c20e8fe2546b7`: the 1
   side effect) and public organisation helplines (also masked; acceptable). Misses vehicle numbers and home
   addresses (11 uncured documents); those need an address and plate detector or a named-entity model, and a news
   report naming an accused person is public record, not F1.

## Medicine 9: A6 Devanagari and Latin glued in one word

1. **Disease:** A6, 17 of 500 documents (13 drop, 4 fix). Examples:
   - `39bd4d9f4387f55b`: `AnyOptionनवोन्मेशी` at offset 1542.
   - `0573df3b6b0cbc3c`: `रहूंगाbye` at offset 4489.
   - `c8d69b4928763080`: `अनुभवUniversity` at offset 32121.
2. **Medicine:** first cure fake dandas (Medicine 6, so `हैI` becomes `है।`), then insert a space where a Hindi
   letter touches a Latin word of 2+ letters.
   ```python
   A6_JOIN = re.compile(f"(?<=[{DEVA}])(?=[A-Za-z]{{2}})|(?<=[A-Za-z]{{2}})(?=[\u0904-\u0939\u0958-\u0961])")

   def cure_a6(text):
       return A6_JOIN.sub(" ", cure_g4(text))
   ```
   Examples: `AnyOptionनवोन्मेशी` → `AnyOption नवोन्मेशी`, `रहूंगाbye` → `रहूंगा bye`, `है।UNICAF` → `है। UNICAF`.
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 16 of 17; side effects 54 of 483 (49 are the G4 changes of
   Medicine 6; the other 5 are correct splits such as `ReplyDeleteआदरणीय` → `ReplyDelete आदरणीय` and
   `Read Moreदिनांक` → `Read More दिनांक`); clean touched 0.
5. **Side effects:** a deliberate brand or hashtag written across scripts is split (`#laफ्ज` → `#la फ्ज`). Most A6
   documents are dropped for other reasons (spam, machine translation), so the cure matters mostly for the 4 kept.

## Medicine 10: C5 keyword stuffing and link lists

1. **Disease:** C5, 16 of 500 documents (13 drop, 3 fix). Examples:
   - `ca38e3770cd4bd18`: `विदेशी मुद्रा पर पैसे कमाएं` at offset 561.
   - `7a2bc38b934a51ad`: `दृष्टिकोण कंप्यूटर का उपयोग कर बिटकॉइन कैसे कमाएं है` at offset 7175.
   - `84b3adb7174dfd68`: `PAMM खाते में निवेश व्यापार रणनीति Combiner व्यावहारिक आवेदन` at offset 1520.
2. **Medicine:** drop keyword-stuffed spam (the spam rule of Medicine 2). In other documents remove only lines that are
   mostly hashtags or URLs. Comma lists of names or figures in news (`इस अवसर पर …, …, … आदि मौजूद रहे`) are content and stay.
   ```python
   TAG_OR_URL = re.compile(r"https?://\S+|www\.\S+|#[\w\u0900-\u097F]+")

   def cure_c5(text):
       if is_spam(text):
           return None
       keep = [line for line in text.split("\n")
               if not ((tags := TAG_OR_URL.findall(line)) and len(tags) >= 3
                       and sum(map(len, tags)) >= 0.5 * len(line.strip()))]
       return "\n".join(keep)
   ```
3. **Action:** drop the document (spam); otherwise fix (remove hashtag or link lines).
4. **Harm test:** pending (gold set). Pack check: cures 12 of 16 (11 dropped, 1 hashtag line removed); side effects 0 of 484; clean touched 0.
5. **Side effects:** spam in other topics (betting, adult, pharmacy, SEO keyword lists) is not in the term list (the
   4 uncured documents); the list must grow from reviewed pages. A real news article quoting many forex terms could be
   dropped; the two-distinct-terms rule made this 0 in the pack. A first version that also removed comma lists deleted
   news content in 4 clean documents and was rejected.

## Medicine 11: C2 repeated lines

1. **Disease:** C2, 15 of 500 documents (11 fix, 4 drop). Examples:
   - `156518ecd2ad3a57`: `दिल्ली मेट्रो रेल कॉरपोरेशन (DMRC) के मुख्य कार्यकारी निदेशक` at offset 534 (a 455-character paragraph printed twice).
   - `b2038fc0ce4c0647`: `- KY सुई लूम मशीन आविष्कार पेटेंट` at offset 3957 (the same list item 7 times).
   - `616c483d9fcd6c27`: `आज का दिन ऐसे काम करने के लिए बेहतरीन है` at offset 8467 (horoscope text repeated across signs).
   Reviewer policy: C2 is a 300+ character paragraph twice or a line 3+ times; speech refrains are not C2.
2. **Medicine:** keep the first copy and remove later copies of a 300+ character line, or of a 25+ character line
   that occurs 3+ times. Shorter repeats are left alone, because in speeches they are content.
   ```python
   def cure_c2(text):
       lines = text.split("\n")
       count = Counter(norm_line(line) for line in lines)
       seen, out = set(), []
       for line in lines:
           nl = norm_line(line)
           if nl in seen and (len(nl) >= 300 or (len(nl) >= 25 and count[nl] >= 3)):
               continue
           seen.add(nl)
           out.append(line)
       return "\n".join(out)
   ```
   Example (`156518ecd2ad3a57`, offset 989): the second copy of the DMRC paragraph is removed; the first stays.
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 6 of 15; side effects 0 of 485; clean touched 0.
5. **Side effects:** misses repeats that sit inside a longer line (a headline repeated as the first sentence),
   near-duplicates with one word changed (horoscope paragraphs per sign), and short widget lines such as `CreditAI` or
   `धन्यवाद` (9 uncured). Lowering the 25-character floor to 8 or 12 cured 3 more but removed refrains (`साथियों,`) in
   3 clean speeches, so it was rejected.

## Medicine 12: C3 truncated document

1. **Disease:** C3, 13 of 500 documents (12 drop, 1 fix). Examples:
   - `4ee77e0c84fdefdf`: `गोमती नगर विस्तार में […]` at offset 325 (a teaser cut off by the listing page).
   - `e9245802d6596af1`: `के फैसले के…` at offset 383.
   - `64644fdd37af28d4`: `उपयोगकर्ताओं को…` at offset 5567.
2. **Medicine:** a cut-off text cannot be completed, and in this pack C3 pages are listing pages of teasers. Drop a
   document when 3 or more lines (20+ characters) end in `…` or `[…]` and they are at least 30% of its lines.
   ```python
   TRUNC_END = re.compile(r"(\[…\]|\[\.\.\.\]|…|\.\.\.)\s*$")

   def cure_c3(text):
       lines = [nl for nl in map(norm_line, text.split("\n")) if nl]
       cut = [nl for nl in lines if len(nl) >= 20 and TRUNC_END.search(nl)]
       return None if len(cut) >= 3 and len(cut) >= 0.3 * len(lines) else text
   ```
3. **Action:** drop the document.
4. **Harm test:** pending (gold set). Pack check: cures 11 of 13; side effects 8 of 487, all documents I dropped for
   other reasons (dictionary-snippet pages and teaser lists); clean touched 0.
5. **Side effects:** a short news brief that uses `…` as a style mark could be dropped; requiring 3 lines (not 2)
   spared one such clean brief. Misses the 2 documents that stop mid-sentence without a mark: a forum story
   (`9d7b9c8580e163e8`, dropped for other reasons) and an article with a lost page (`dc6d5f3163378049`, kept as fix).

## Medicine 13: D2 romanised Hindi

1. **Disease:** D2, 10 of 500 documents (9 fix, 1 drop). Mostly SEO titles and headings in Latin letters. Examples:
   - `2d3b04f109d069ec`: `Shiksha k Odisha kya hai` at offset 11559.
   - `7b6db4f0bb885a22`: `Sariya Cement Ka Rate` at offset 436.
   - `c02e0ea3fe225110`: `Photo Se Background Kaise Hataye` at offset 705.
2. **Medicine:** transliterating back to Devanagari needs a model, and these lines repeat a Devanagari heading or
   title. Remove Latin-only lines of 3+ words where at least a quarter of the words are Hindi function words.
   ```python
   ROMAN_HI = {"kya", "hai", "hain", "kaise", "kare", "karen", "karein", "ka", "ki", "ke", "se", "ko", "mein", "aur",
               "kab", "kyon", "kyun", "aaj", "nahi", "hota", "hoti", "hote", "wala", "wali", "kitna", "kaun", "apne",
               "apna", "liye", "sath", "ek", "bhi", "tak", "rashifal", "katha", "vrat"}  # no English look-alikes ('me', 'par')
   LATIN_WORD = re.compile(r"[A-Za-z]+")

   def cure_d2(text):
       out = []
       for line in text.split("\n"):
           words = [w.lower() for w in LATIN_WORD.findall(line)]
           hits = sum(w in ROMAN_HI for w in words)
           if not re.search(f"[{DEVA}]", line) and len(words) >= 3 and hits >= 1 and hits >= 0.25 * len(words):
               continue
           out.append(line)
       return "\n".join(out)
   ```
   Example (`2d3b04f109d069ec`, offset 11559): `…अभिलाषी है |⏎Shiksha k Odisha kya hai⏎शिक्षा का उद्देश्य…` → `…अभिलाषी है |⏎शिक्षा का उद्देश्य…`.
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 4 of 10; side effects 0 of 490; clean touched 0.
5. **Side effects:** misses romanised Hindi inside a Devanagari line (`mohini ekadashi vrat katha`, `Vish Ke Dant`)
   and English-titled lines (`(Aries Love Horoscope)`), the 6 uncured documents. An English line made of Hindi loan
   words (`Aaj Tak`, brand names) could be removed; none in the pack.

## Medicine 14: G1 words split before a vowel sign

1. **Disease:** G1, 9 of 500 documents (6 drop, 3 fix). Examples:
   - `a02caf8e245bbcf3`: `मे ंगुजार` at offset 3746 (`में गुजार`, space before the anusvara).
   - `8fed2d4464e4cc06`: `मे ं एक नि श् चि त` at offset 2789 (whole paragraph split at every sign).
   - `0f58a7ef798cc635`: `पाश् चात्य` at offset 1880.
2. **Medicine:** only in documents where the split is systematic (3 or more splits), join a vowel sign or anusvara to
   its letter, and join a halant to the next consonant.
   ```python
   G1_SPLIT = re.compile(f"([{CONS}\u093C])\\s+([{MATRA}\u0901-\u0903])")
   G1_ANUSVARA = re.compile(f"([{MATRA}])\\s+([\u0901\u0902])")
   G1_HALANT = re.compile(f"([{CONS}]\u094D)\\s+(?=[{CONS}])")

   def cure_g1(text):
       if len(G1_SPLIT.findall(text)) + len(G1_ANUSVARA.findall(text)) < 3:
           return text                                      # a single 'जगत् में' is correct Hindi
       text = G1_ANUSVARA.sub(lambda m: m.group(1) + m.group(2) + " ", text)   # 'मे ंगुजार' -> 'में गुजार'
       text = G1_SPLIT.sub(r"\1\2", text)
       text = re.sub("([\u0901\u0902]) (\\s)", r"\1\2", text)
       return G1_HALANT.sub(r"\1", text)
   ```
   Examples: `लाचारी मे ंगुजार देते` → `लाचारी में गुजार देते`; `प् रति शत … रू प मे ं` → `प्रति शत … रू प में`.
3. **Action:** fix the text.
4. **Harm test:** pending (gold set). Pack check: cures 2 of 9; side effects 0 of 491; clean touched 0.
5. **Side effects:** splits between two consonant syllables (`वि कि पी डि या`) cannot be joined without a word list,
   and `… [+]` truncation marks inside words (`ह… [+] ै`) are not handled; most of those documents are dropped for
   other reasons. In a systematically split document a Sanskrit word ending in halant followed by another word would be merged.
