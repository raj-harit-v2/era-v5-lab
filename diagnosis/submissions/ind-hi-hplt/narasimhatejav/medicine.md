# Medicine sheet: ind-hi-hplt (narasimhatejav)

Counts are from all 500 rows of the pack (pack rows 0 to 499), as labelled in `labels.csv`: fix 343, clean 77, drop 80. There is one section for each disease found more than five times. Rows are 0-based pack rows. "Cures" means the documents with that code that the rule changes or drops. "Side effects" are measured on the other labelled rows of the 500.

Harm test for every section: `python3 teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md --pack ind-hi-hplt.parquet --gold-dir teams/02-data-b/gold`. The gold set is `ind-hi-hplt_gold.csv` (67 documents), so a rule may change or drop at most 1 gold document. All rules together ("ALL IN ORDER") change 0 and drop 0 of 67: **PASS**.

## Medicine 1

1. **Disease:** A5 (wrong normal form, from legacy-font converters such as Krutidev), 66 documents. Examples:
   - `e914970b471c9358`: "कांगे्रस" at 312 (VOWEL SIGN E before VIRAMA + RA), 14 times
   - `3f6de6c0ae2e1356`: "भाेपाल" at 1526 (VOWEL SIGN AA + VOWEL SIGN E for VOWEL SIGN O)
   - `0a9fb374411f47b4`: "डाॅक्टर" at 138 (AA + CANDRA E) next to "डॉक्टरों" at 519 in the same document
2. **Medicine:** Rewrite only character sequences that a font converter produces and correct Hindi never contains: a vowel sign written before a virama, two vowel signs that stand for one (ा + ॅ for ॉ, ा + े for ो, े + ै for ै), the same vowel sign twice, two nuktas, a nukta moved to the next letter (पकडक़र), a reph written after its conjunct (सामथ्र्य), र्इ for ई, ध्द for द्ध, and the Marathi eyelash ऱ for र.

```python
_C = "[\u0915-\u0939\u0958-\u095F]"  # consonant


def medicine_a5(text):
    t = text
    # vowel sign E/AI typed before virama + RA: कांगे्रस -> कांग्रेस
    t = re.sub("([\u0947\u0948])\u094D\u0930", "\u094D\u0930\\1", t)
    # stray virama after vowel sign E/AI before another consonant: ओल्डे्नबर्ग -> ओल्डेनबर्ग
    t = re.sub("([\u0947\u0948])\u094D(?=" + _C + ")", "\\1", t)
    # two vowel signs for one: AA+CANDRA E -> CANDRA O, AA+E or E+AA -> O, AA+AI -> AU, E+AI -> AI
    for bad, good in (("\u093E\u0945", "\u0949"), ("\u093E\u0947", "\u094B"), ("\u0947\u093E", "\u094B"),
                      ("\u093E\u0948", "\u094C"), ("\u0947\u0948", "\u0948"), ("\u093C\u093C", "\u093C")):
        t = t.replace(bad, good)
    # the same vowel sign twice: स्थाानों -> स्थानों
    t = re.sub("([\u093E-\u094C])\\1", "\\1", t)
    # nukta moved to the next letter: पकडक़र -> पकड़कर, पीढिय़ों -> पीढ़ियों, लडऩे -> लड़ने
    t = re.sub("([\u0921\u0922])([\u093F\u0940\u0947\u0948]?)([\u0915\u092F\u0928])\u093C", "\\1\u093C\\2\\3", t)
    t = re.sub("([\u0921\u0922])([\u093E-\u094C]?)\u0929", "\\1\u093C\\2\u0928", t)
    # reph written after the conjunct: सामथ्र्य -> सामर्थ्य, पाट्र्स -> पार्ट्स
    t = re.sub("(" + _C + ")\u094D\u0930\u094D(" + _C + ")", "\u0930\u094D\\1\u094D\\2", t)
    # RA + virama + letter I for letter II: हुर्इं -> हुईं
    t = t.replace("\u0930\u094D\u0907", "\u0908")
    # DHA + virama + DA for द्ध: बौध्दिक -> बौद्धिक
    t = t.replace("\u0927\u094D\u0926", "\u0926\u094D\u0927")
    # Marathi eyelash RA for RA: औऱ -> और
    t = re.sub("\u0931(?!\u094D)", "\u0930", t)
    return t
```

3. **Action:** fix the text.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. ZWJ/ZWNJ audit and normal-form audit: 0 documents. **PASS**
5. **Side effects:** Cures 46 of 66. It also fixes single slips in 17 documents that we did not label A5 (rows 52, 56, 72, 83, 153, 169, 204, 212, 366, 385, 433, 435, 444, 469, 478, 480, 490). In rows 52, 56, 72 and 83 we checked the edits (a double nukta in "पीढ़़ियों" and "खदेड़़ने", a double vowel sign in "आदेेश", eyelash RA in "शुऱुआत" and "औऱ"); they are correct, so our labels undercount A5 there. The 13 later rows have not been checked one by one. It does not fix the damage that needs a dictionary: ष for श ("हमेषा", "देष"), lost letters ("राय" for "राज्य"), Latin-1 residue ("तŸवों"), and ि + े, where the right vowel is not known. Risk: a word with a real nukta after ड or ढ followed by क or य (none found in the first 150 rows or the gold set).

## Medicine 2

1. **Disease:** A6 (wrong or mixed script), 28 documents. Examples:
   - `ac36464759436542`: Latin capital I typed as the danda, "बहुत पसंद आया I" at 465 (344 times)
   - `4b82ad7e92695e55`: Latin small l typed as the danda, "कुशलता से उभारा है l" at 116 (306 times)
   - `1e638ceb8920faf1`: visarga typed for a colon, "महत्वपूर्ण हैः यह" at 10362 (10 times)
2. **Medicine:** Replace a Latin I or l that stands alone after a Devanagari word, at the end of a sentence, with the danda (।), unless the word before it takes a Roman numeral (डिवीजन I, भाग I). Replace a visarga after है, हैं or चाहिए with a colon.

```python
_DANDA = re.compile("([\u0900-\u0963\u0966-\u097F]+)( ?)[Il](?=[ \t]*(?:\n|$|[\u0900-\u097F\"'\u201C\u201D\u2018\u2019]))")
_ROMAN_BEFORE = {"डिवीजन", "डिवीज़न", "भाग", "खंड", "खण्ड", "चरण", "फेज", "फेज़", "टाइप", "क्लास", "ग्रेड", "लेवल", "विश्वयुद्ध"}


def _danda(m):
    if m.group(1) in _ROMAN_BEFORE:  # "डिवीजन I" is a Roman numeral, not a danda
        return m.group(0)
    return m.group(1) + m.group(2) + "\u0964"


def medicine_a6(text):
    # Latin I or l typed for the danda after a Devanagari word: "हैI", "आया I", "हुआ l"
    t = _DANDA.sub(_danda, text)
    # visarga typed for the colon: "महत्वपूर्ण हैः यह" -> "है:"
    t = re.sub("(है|हैं|चाहिए)\u0903(?=\\s)", "\\1:", t)
    return t
```

3. **Action:** fix the text.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. Both audits: 0 documents. **PASS**
5. **Side effects:** Cures 9 of 28. It also fixes a danda typed as I in 2 documents that we did not label A6 (rows 47 and 170; correct edits). The first draft turned "डिवीजन I" (Division I) into a danda; the Roman-numeral list now stops that, but a Roman numeral after a word that is not in the list would still be changed. It leaves alone: an ASCII colon for the visarga ("प्राय:", "वस्तुत:"), because this is common typing in Hindi and appears in clean text; digit zero as the abbreviation sign ("एस0एस0"); and Latin-1 symbols inside words ("बढेÞ", "टैªनिंग", "महाराष्ट्रª", "सौदागरÓ", "चिÐत"), because the right letter cannot be known from the symbol; and other scripts or symbols in the wrong place (Arabic words in row 406, the minus sign for a hyphen in row 430).

## Medicine 3

1. **Disease:** B2 (HTML residue), 6 documents. Examples:
   - `803472a29da319bf`: "/>" at 7423 (5 times)
   - `1c61f6e0c56fbbc9`: "/>" at 9375 (6 times)
   - `c2b54c4cd92b3a0c`: "/>" at 28877 (8 times)
2. **Medicine:** Remove a stray tag end "/>" when the document has no "<" at all, so the "/>" cannot be part of a real tag.

```python
def medicine_b2(text):
    if "<" in text:  # a real tag is there: leave it to an HTML cleaner
        return text
    return re.sub("[ \t]*/>", "", text)
```

3. **Action:** fix the text.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. Both audits: 0 documents. **PASS**
5. **Side effects:** Cures 6 of 6, no side effects in the 500 rows. All 6 documents are `drop` for other reasons (D4, C4), so this medicine matters only if they are kept. A document that has both a real tag and stray "/>" is not changed.

## Medicine 4

1. **Disease:** C1 (boilerplate), 282 documents. Examples:
   - `2a5f73bb1b272717`: comment block "Thursday, December 15th 2016 at 6:40 AM |" at 7378 to the end
   - `be03493ed6a40df3`: "यह भी पढ़ें" at 2180, 5616 and 11133
   - `340122661b614c55`: "ADVERTISEMENT" at 240 (4 times)
2. **Medicine:** Remove lines that hold only an advert or share label ("ADVERTISEMENT", "Share:", "Read More…") and one-line "यह भी पढ़ें" / "इसे भी पढ़ें" links. In the last 40% of the document, cut from the first line that starts a comment form, a related-stories list or a disclaimer ("कोई टिप्पणी नहीं:", "Leave a Reply", "More Stories", "Read Next", "Related Articles", "आवश्यक सूचना", "डिस्क्लेमर") to the end.

```python
_LINE = re.compile(r"^[ \t]*(?:ADVERTISEMENT|Advertisement|Share(?: this)?:|Read More…?)[ \t]*\n?", re.M)
_RELATED = re.compile(r"^[ \t]*(?:यह भी पढ़ें|इसे भी पढ़ें)\b.*\n?", re.M)
_TAIL = re.compile(r"^[ \t]*(?:No comments:|Post a Comment|कोई टिप्पणी नहीं:|एक टिप्पणी भेजें|Leave a Reply|"
                   r"एक उत्तर दें|More Stories|Read Next|Related Articles|Related Posts|Tags:|आवश्यक सूचना|"
                   r"डिस्क्लेमर|अन्य न्यूज़|\(For more news|अधिकतम रेटिंग \d)", re.M)


def medicine_c1(text):
    t = _LINE.sub("", text)
    t = _RELATED.sub("", t)
    m = _TAIL.search(t, int(len(t) * 0.6))  # comment forms, related lists and disclaimers only near the end
    if m:
        t = t[:m.start()].rstrip()
    return t
```

3. **Action:** fix the text.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. Both audits: 0 documents. **PASS**
5. **Side effects:** Cures 56 of 282, no side effects in the 500 rows. Most documents carry boilerplate that this rule has no marker for, so the cure rate is low. The rule is narrow on purpose. It misses boilerplate with no fixed marker: bylines and site names inside the text ("Fast News Today"), reader comments with no heading, publisher promos ("फारवर्ड प्रेस वेब पोर्टल के अतिरिक्त"), embedded tweets ("pic.twitter.com"), and directory-page headers ("आप इस पेज पर में"). Risk: an article whose own text has a line that starts with "यह भी पढ़ें" would lose that line.

## Medicine 5

1. **Disease:** C2 (repeated text), 80 documents. Examples:
   - `6252483773742b19`: paragraph "प्रधानमंत्री नरेंद्र मोदी आज अपने रेडियो कार्यक्रम" at 127, repeated at 370
   - `be03493ed6a40df3`: passage "यूनानी इतिहासकारों के झूठ को पकड़ने के लिए ईरानी और चीनी विवरण" at 823, repeated at 10675
   - `340122661b614c55`: teaser "Uttar Pradesh News : अयोध्या में" at 102, repeated in full at 254
2. **Medicine:** Find every sentence of 60 or more characters that ends in a danda, "?" or "!". If the same sentence appears again later, keep the first copy and remove the later copies.

```python
def medicine_c2(text):
    t = text
    for s in dict.fromkeys(re.findall("[^\u0964?!\n]{60,}[\u0964?!]", text)):
        first = t.find(s)
        if first >= 0 and t.find(s, first + len(s)) >= 0:
            t = t[:first + len(s)] + t[first + len(s):].replace(s, "")
    return t
```

3. **Action:** fix the text.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. Both audits: 0 documents. **PASS**
5. **Side effects:** Cures 41 of 80. It changes 7 documents we did not label C2 (rows 20, 60, 61, 104, 422, 486, 490). In row 20, a reader comment quotes a sentence of the article, and the rule leaves empty quote marks “”. In row 104, it removes a repeated SEO question, which is a correct edit; rows 60, 61 and 422 are `drop` documents. It misses repeats that are short, cut by a line break, or changed a little (row 119), and template blocks repeated with small changes. Risk: a speech or hymn whose refrain is repeated on purpose would lose the refrain; the 60-character minimum keeps most refrains out.

## Medicine 6

1. **Disease:** C3 (truncated), 35 documents. Examples:
   - `4ee77e0c84fdefdf`: every teaser cut mid-sentence with "[…]" (10 times, last at 2880)
   - `812cedd5d950774e`: each teaser cut with "[…]" (8 times, first at 167)
   - `7261baa0a3edfb1d`: starts mid-text, "-कमला सोचते हुए ये बताती है।" at 0
2. **Medicine:** Drop a document with 3 or more cut markers ("[…]", "[...]", "… [+]", "Read More"). Such a document is a list of cut teasers, so no part is a complete text.

```python
_CUT = re.compile(r"\[…\]|\[\.\.\.\]|…\s?\[\+\]|Read More")


def medicine_c3(text):
    return len(_CUT.findall(text)) >= 3
```

3. **Action:** drop the document.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. **PASS**
5. **Side effects:** Cures 7 of 35 (the teaser pages). It also drops 11 documents we did not label C3 (rows 53, 54, 55, 59, 60, 61, 62, 65, 69, 70, 178), most of them university-directory pages where "… [+]" cuts each entry; we labelled those C4 and D4, and they are `drop` anyway. It misses 17 documents that are cut with a plain "…" or ".." (rows 153, 169, 195, 342, 358, 475), because that mark is also normal punctuation. It cannot find a document that starts mid-sentence (`7261baa0a3edfb1d`, rows 359 and 363) or lost a part in the middle or at the end (rows 205, 270, 286, 353, 430), because nothing in the characters shows it. A document that uses "Read More" 3 times as links but is otherwise complete would be dropped.

## Medicine 7

1. **Disease:** C4 (documents joined), 68 documents. Examples:
   - `c8d69b4928763080`: about 40 institution blurbs joined, e.g. "हम कौन हैं यहाँ Oplex" at 43444
   - `e9245802d6596af1`: 10 unrelated teasers on an author page
   - `8fed2d4464e4cc06`: handbags at 1470 + horoscope at 3368 + ion-channel statistics at 5344
2. **Medicine:** Drop a document with 3 or more cut markers (a page of joined teasers or directory entries), or one that ends in the rating footer of the spun-spam sites ("अधिकतम रेटिंग 5" followed by "न्यूनतम स्कोर"). Those spam pages join unrelated texts.

```python
_CUT4 = re.compile(r"\[…\]|\[\.\.\.\]|…\s?\[\+\]|Read More")
_SPAM_FOOTER = re.compile("अधिकतम रेटिंग \\d+\\s*\nन्यूनतम स्कोर")


def medicine_c4(text):
    return len(_CUT4.findall(text)) >= 3 or bool(_SPAM_FOOTER.search(text))
```

3. **Action:** drop the document.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. **PASS**
5. **Side effects:** Cures 29 of 68, no side effects in the 500 rows. It misses news round-ups where several complete stories are joined (rows 22, 34, 44, 73, 355) and listing pages with no cut marker. For those the verdict is `fix`, and the right medicine is to split at each dateline ("नई दिल्ली।", "जकार्ता।"). The harm-test format takes one text and returns one text, so a split cannot be written here; it is left for the pipeline.

## Medicine 8

1. **Disease:** C5 (keyword spam), 33 documents. Examples:
   - `ca38e3770cd4bd18`: keyword "विदेशी मुद्रा पर पैसे कमाएं" pushed into sentences 7 times, at 561, 2241 and 5372
   - `8fed2d4464e4cc06`: the same keyword 4 times, at 12, 1336 and 5001
   - `919f67de75694255`: keyword "द्विआधारी विकल्प के लिए ट्रेडिंग रणनीति" 8 times, at 242, 958 and 6444
2. **Medicine:** Drop a document that has the rating footer of the spun-spam sites ("अधिकतम रेटिंग N" followed by "न्यूनतम स्कोर"). In this pack every document with this footer is keyword spam.

```python
def medicine_c5(text):
    return bool(re.search("अधिकतम रेटिंग \\d+\\s*\nन्यूनतम स्कोर", text))
```

3. **Action:** drop the document.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. **PASS**
5. **Side effects:** Cures 11 of 33, no side effects in the 500 rows. The rule finds one family of spam sites by its template, not keyword stuffing in general. The 22 it misses are SEO pages that push one phrase as a heading prefix or inline ("Indian Coast Guard" x13, "PM Mudra Loan Online Apply" x10, "#meridiary" x8; rows 155, 172, 204, 219, 222, 225, 242, 243, 257, 259, 279, 287, 290, 291 and others), most of them `fix`. A rule on repeated 5-word phrases was tried first; it also hit 3 gold documents and many sermons, so it was not used. It misses the referral-code page (row 124).

## Medicine 9

1. **Disease:** D3 (mixed language), 306 documents. Examples:
   - `f6f77aeff3b688d0`: "कॉलेज technology के माध्यम" at 422 + "integration पर जोर" at 3495
   - `7a2bc38b934a51ad`: "cryptocurrency में निवेश" at 4050
   - `5601fded420c9a5c`: "असिस्टेंट Professor" at 14 + "salary 57,700" at 55
2. **Medicine:** No change to the text. The document gets a tag (the list of Latin words between Devanagari words, from `_d3_latin_words`), so that later steps can count or balance code-mixed text.

```python
def _d3_latin_words(text):
    """Latin words of 3+ letters that sit between Devanagari words: the D3 tag, kept as a note on the document."""
    return re.findall("(?<=[\u0900-\u097F] )[A-Za-z]{3,}(?=[ ,.]*[\u0900-\u097F])", text)


def medicine_d3(text):
    return False  # tag only: the text is kept as it is
```

3. **Action:** neither fix nor drop: keep the text and tag the document.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. **PASS**. A rule that removed or translated these words would have changed 13 of the 69 gold documents (19%) when the gold set was 69 documents and fail.
5. **Side effects:** None, because nothing is changed. Why tag only: DISEASES.md says D3 "can be natural; label it, do not judge it", and Hindi web text mixes English words in normal use. English that is left in because of bad machine translation is D4, and Medicine 10 deals with it. Our D3 count includes Latin brand names and acronyms (Hotstar, CTI, CET); these are names, not mixed language, and the count will go down when the labels are corrected.

## Medicine 10

1. **Disease:** D4 (bad machine translation), 89 documents. Examples:
   - `bd80634fbfa8c282`: year split by spaces, "1 99 2" at 13, and 'joystick' as "मजबूत आनंद स्टिक" at 10121
   - `ca38e3770cd4bd18`: Russian left in Latin letters, "kachestvennoy" at 3200
   - `57294dfeff306304`: "Dr." turned into "डॉ।" at 2027, and 'amicus brief' as "अमीकस कच्छा" at 3184
2. **Medicine:** Drop a document that shows a machine-translation mark that a person never types: a year split by spaces ("1 99 2", "1 9 4 9"), a Russian word left in Latin letters (ending in -oy, -yy, -aya, -ogo, -ykh, -iya), or "डॉ।" (the full stop of "Dr." turned into a danda).

```python
_YEAR = re.compile(r"(?<![\d,.])1(?: 9 ?\d ?\d| ?9 \d ?\d| ?9 ?\d \d)(?![\d,.])")
_RU = re.compile(r"\b[a-z]{4,}(?:oy|yy|aya|ogo|ykh|nykh|iya)\b")


def medicine_d4(text):
    return bool(_YEAR.search(text) or _RU.search(text) or "डॉ।" in text)
```

3. **Action:** drop the document. When the translation is bad in every paragraph, a fix would leave nothing reliable.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. **PASS**
5. **Side effects:** Cures 16 of 89, no side effects in the 500 rows. It misses 73 documents where the machine translation shows only in wrong word senses, word order and doubled words ("फायदे और फायदे", "लापता महिलाओं" for 'Laapataa Ladies', "घिसाव, पित्त" for galling), which are not visible in the characters (rows 159, 165, 170, 213, 216, 230, 247 and others). Another case is "स्नातक की उपाधि प्राप्त ईंधन दक्षता" for 'graduated standards'. Both need a reader or a model. Risk: a list of numbers such as "1 9 9 4" in a table would match the year pattern.

## Medicine 11

1. **Disease:** G1 (vowel sign split from its letter), 14 documents. Examples:
   - `8fed2d4464e4cc06`: space before the anusvara, "मे ं एक" at 2792 and "है ं ।" at 2936
   - `b8d46e4abba176c4`: a read-more marker cuts a word before its vowel sign, "[+] ंस्क" at 1206
   - `5aa1af940056a185`: "[+] ानी" at 2833
2. **Medicine:** Remove a "… [+]" marker that sits in front of a vowel sign, so the word joins again ("ब… [+] िजनेस" becomes "बिजनेस"). Remove spaces between a letter and the vowel sign or anusvara that follows it ("मे ं" becomes "में").

```python
def medicine_g1(text):
    # a read-more marker cut a word before its vowel sign: "ब… [+] िजनेस" -> "बिजनेस"
    t = re.sub("…\\s*\\[\\+\\]\\s*(?=[\u0900-\u0903\u093E-\u094C])", "", text)
    # a space before a vowel sign or anusvara: "मे ं" -> "में"
    t = re.sub("(?<=[\u0915-\u0939\u093C-\u094C\u0958-\u095F])[ \t]+(?=[\u0900-\u0902\u093E-\u094C])", "", t)
    return t
```

3. **Action:** fix the text.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. Both audits: 0 documents. **PASS**
5. **Side effects:** Cures 13 of 14, no side effects in the 500 rows. It does not join a virama followed by a space ("पाश् चात्य", row 56), because a word-final virama before a space is correct in Sanskrit-style Hindi ("जगत् के"). A vowel sign after a danda ("हॅू।ंजो") is not fixed, because the right order is not known.

## Medicine 12

1. **Disease:** D2 (romanised Hindi), 6 documents. Examples:
   - `2d3b04f109d069ec`: heading "Shiksha k Odisha kya hai" at 11559
   - `7b6db4f0bb885a22`: heading "Sariya Cement Ka Rate" at 436
   - `c02e0ea3fe225110`: SEO titles "Photo Se Background Kaise Hataye" at 700 and "Snapchat me Dark Mode Enable kaise kare?" at 1781
2. **Medicine:** Remove a line of 120 characters or fewer that is all ASCII and has at least 2 different Hindi function words in Latin letters (kya, kaise, kare, hai, ka, ke, ki, ko, mein, liye, hota, aur, bhi, nahi and the like). In these documents the romanised text is a heading or an SEO title between Hindi paragraphs, so removing the line does not leave a gap in a sentence.

```python
_ROMAN_HI = {"kya", "kaise", "kaisa", "kaun", "kare", "karen", "hai", "hain", "ka", "ke", "ki", "ko", "mein", "liye",
             "hota", "hoti", "hote", "kaha", "kab", "aur", "bhi", "nahi", "wala", "wali"}


def medicine_d2(text):
    kept = []
    for line in text.split("\n"):
        words = {w.lower() for w in re.findall("[A-Za-z]+", line)}
        ascii_only = not re.search("[^\x00-\x7f\u2018\u2019\u201C\u201D\u2026]", line)
        if line.strip() and len(line) <= 120 and ascii_only and len(words & _ROMAN_HI) >= 2:
            continue  # a romanised Hindi heading or SEO title
        kept.append(line)
    return "\n".join(kept)
```

3. **Action:** fix the text.
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. **PASS**
5. **Side effects:** Cures 3 of 6, no side effects in the 500 rows. It misses 3 documents where the romanised title shares its line with other words or has a trailing mark (rows 124, 155, 297). Risk: an English line that happens to hold two of these words. A document that is written in romanised Hindi throughout is not improved by this rule; it would need to be dropped.

## Medicine 13

1. **Disease:** D5 (translationese), 11 documents. Examples:
   - `ce8d681b0307ba08`: "पर्याप्त विचार-विमर्श के बिना" ('without consideration') at 8017
   - `724bdddd82937534`: article-spinner filler "कई सारी ढेर फिल्में" at 610 and "साउथ के सारे कई स्टार" at 846
   - `066dab92d3de2aff`: "भूस्खलन होने जैसे बहुमत के साथ" for 'landslide majority' at 10076
2. **Medicine:** No rule on the characters. Translationese is grammatical text with English word order and calqued phrases, so no character pattern or word list finds it without also hitting normal Hindi. The document gets a tag so that a reader or a model can check it later.

```python
def medicine_d5(text):
    return False  # tag only: the text is kept as it is
```

3. **Action:** neither fix nor drop: keep the text and tag the document for a model or reader check.
4. **Harm test:** nothing to run, because the rule does nothing (changes 0 of 67 gold documents, drops 0). **PASS**
5. **Side effects:** None. It finds none of the 11 documents; D5 is only a label here. All 11 are `fix` (the other diseases in them are cleaned by other medicines). A document with both D4 and D5 marks should be checked first, because a fix of the other diseases will not repair its wording.

## Medicine 14

1. **Disease:** F1 (personal data), 18 documents. Examples (type and place only, never the value):
   - `4b82ad7e92695e55`: email at 28595, 2 phone numbers at 28634
   - `9748e7143a5e93c9`: mobile number at 24049 in the reviewer's byline
   - `717813c65d28deec`: personal email at 13412 in the interviewer's byline
2. **Medicine:** Remove an email address, and remove a 10-digit Indian mobile number (starts with 6 to 9, optional +91 or 0 in front, not inside a longer run of digits).

```python
_MAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\d,.])(?:\+91[ -]?|0)?[6-9]\d{9}(?![\d,.])")


def medicine_f1(text):
    t = _MAIL.sub("", text)
    return _PHONE.sub("", t)
```

3. **Action:** fix the text (remove the value).
4. **Harm test:** changed 0 of 67 gold documents, dropped 0. **PASS**
5. **Side effects:** Cures 9 of 18. It also changes 6 documents we did not label F1 (rows 5, 60, 67, 70, 203, 454): 5 are emails, mostly a publisher or institution contact address (`forwardmagazine.in` in rows 5 and 67), and 1 is a 10-digit number (row 203). Removing public contact data is harmless, but it does not match our F1 rule (private persons only). It cannot find what has no fixed form: home and village addresses, vehicle registration numbers, khasra numbers and patient details (rows 12, 22, 144, 158, 296, 323, 326, 355, 450). Those need a reader or a named-entity model, so those documents keep their F1 label.
