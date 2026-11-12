# Medicine sheet: ind-hi-hplt (therahulbhati)

One section for each disease found more than five times in the 500 labelled documents. Each rule takes the document text and returns the new text (fix), `True` (drop) or `False` (keep), so `teams/02-data-b/tools/harm_test_indic.py` runs it as written.

Harm tests use the Hindi gold set (rebuilt 31 Oct) for this pack, `teams/02-data-b/gold/ind-hi-hplt_gold.csv` (67 documents). With 67 documents a rule passes when it changes or drops at most 1 document (TSAI rule for small gold sets).

## Medicine 1: C5 keyword lists and spam

1. **Disease:** C5, 33 of 500 documents (30 drop, 3 fix). Examples:
   - `ca38e3770cd4bd18`: fake rating trailer "अधिकतम रेटिंग" at offset 8157
   - `7a2bc38b934a51ad`: fake rating trailer "अधिकतम रेटिंग" at offset 8130
   - `8fed2d4464e4cc06`: fake rating trailer "अधिकतम रेटिंग" at offset 7304
2. **Medicine:** Drop generated rating pages ("अधिकतम रेटिंग" and "न्यूनतम स्कोर" trailers) and hashtag clouds (eight or more hashtags).

```python
import re

# C5: generated rating trailers ("अधिकतम रेटिंग 5 / न्यूनतम स्कोर 4 / रेटिंग की संख्या ...") and hashtag clouds: drop
def medicine_c5(text):
    rating = re.search(r"अधिकतम रेटिंग\s*\d", text) and re.search(r"न्यूनतम स्कोर\s*\d", text)
    tags = len(re.findall(r"(?<!\w)#[^\s#]{2,}", text))
    return bool(rating) or tags >= 8
```

3. **Action:** drop.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 12 of 33 C5 documents; 1 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** SEO spam without a rating trailer or hashtags is not caught: 12 of 33. A social-media post with eight hashtags would be dropped.

## Medicine 2: C4 two documents joined

1. **Disease:** C4, 48 of 500 documents (28 drop, 20 fix). Examples:
   - `fa80fce65e52e2b5`: C4 "जकार्ता। इंडोनेशिया के सुलावेसी" at 1728
   - `17e9e5290ce19307`: C4 "डॉ राघवेन्द्र\n✍️आज की डायरी✍️ ✍️बेवजह" at 482
   - `ce96985c67ce0982`: unrelated headlines tail starting "अधिवक्ता विकेश नेगी" at offset 650
2. **Medicine:** Drop listing pages: two or more teaser cuts "[…]", or two or more "… Read More" teaser endings.

```python
import re

# C4: listing pages (several teasers joined): drop
def medicine_c4(text):
    cut = text.count("[…]") + text.count("[...]")
    more = len(re.findall(r"(?:…|\.\.\.)\s*\n?\s*Read More", text))
    return cut >= 2 or more >= 2
```

3. **Action:** drop.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 7 of 48 C4 documents; 0 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** Joined documents without teaser cuts (a second story after the first with no marker) are not caught: 7 of 48. A real article that quotes two "[…]" cuts would be dropped.

## Medicine 3: D4 bad machine translation

1. **Disease:** D4, 67 of 500 documents (51 drop, 16 fix). Examples:
   - `a85a2363de961b2e`: D4 "मैं अपने हृदय की गहराई से उसे धन्यवाद दिये बिना रह पाया" at 23753
   - `57294dfeff306304`: English left in MT output ("reprinted या reposted") at offset 8595
   - `1e638ceb8920faf1`: D4 "सिंह, ज़िराफ़ तथा हिरन की तरह से भोजन को खाते" at 70885
2. **Medicine:** Drop the document when English words are left inside Hindi sentences three or more times: a lowercase English word between two Devanagari words, or Latin letters glued to a Devanagari word (payकंपनी). Brand names are capitalised, so they do not count.

```python
import re

# D4: machine translation that left English words inside Hindi sentences: drop when it happens 3+ times
_D4 = re.compile(r"[ऀ-ॿ][ \t]+[a-z]{4,}(?:[ \t]+[a-z]{2,})*[ \t]+[ऀ-ॿ]|[ऀ-ॿ][a-z]{3,}\b|\b[a-z]{3,}[ऀ-ॿ]")


def medicine_d4(text):
    return len(_D4.findall(text)) >= 3
```

3. **Action:** drop.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 19 of 67 D4 documents; 10 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** Hinglish blogs that write English words in lowercase inside Hindi sentences could be dropped. Machine translation without English leftovers is not caught: the rule finds 19 of 67 D4 documents.

## Medicine 4: C1 boilerplate

1. **Disease:** C1, 199 of 500 documents (181 fix, 18 drop). Examples:
   - `f6f77aeff3b688d0`: boilerplate "यह भी पढ़ें" at 19713
   - `157a92dae8c7615d`: boilerplate "संपर्क करें" at 9755; "ईमेल :" at 9792
   - `7261baa0a3edfb1d`: boilerplate "Post a Comment" at 8996
2. **Medicine:** Remove a line only when the whole line is a known site template: related-article links (यह/ये/इसे भी पढ़ें), comment counters and widgets (0 Comments, टिप्पणियाँ, Leave a comment), share and advert lines, Read More, post-view footers, and the site promos seen in this pack. Sentences inside the article are never touched.

```python
import re

# C1: known template lines, removed only when the whole line is the template
_C1 = re.compile(
    r"^[ \t]*(?:"
    r"(?:यह|ये|इसे|इन्हें) भी (?:पढ़ें|पढ़े|देखें)\s*[:：\-–—]?.*"
    r"|\d+ Comments?'?s?|No comments|There are no comments|Add yours|Leave a comment|Comment Now"
    r"|Comments in this topic:|COMMENTS|टिप्पणियाँ|Post a Comment"
    r"|Share(?: This Post)?:?|शेयर करें|Advertisement|विज्ञापन"
    r"|Read More(?:\.\.\.|…)?|और पढ़ें"
    r"|About Post Author|Post Views:.*|Recent Posts|अन्य न्यूज़"
    r"|Reviews for:.*|\(For more news.*|\(SocialLY के साथ पाएं.*"
    r")[ \t]*(?:\n|$)",
    re.M,
)


def medicine_c1(text):
    return _C1.sub("", text)
```

3. **Action:** fix.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 84 of 199 C1 documents; 1 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** A real sentence that is exactly one of the template words on its own line (for example a heading "विज्ञापन" in an article about advertising) would be removed. Templates that the list does not know stay in the text: the rule cures 84 of 199 C1 documents.

## Medicine 5: C3 truncated document

1. **Disease:** C3, 20 of 500 documents (13 drop, 7 fix). Examples:
   - `e122c2e13453e49b`: mid-sentence start "और दलित शैली में" at offset 193; OCR-like errors in preface (e.g. "अदभुद")
   - `bfc1c6d3c7e30e6d`: C3 "सभागार में आयोजित चिकित्सा शिविर में दिव्य आरोग्य हीलिंग सें" at 239
   - `06b4d2157512fa34`: C3 "उन्नत […]" at 607
2. **Medicine:** Remove the first line when the document starts with "…" before the first word, and the last line when it ends in a "[…]" teaser cut. A story that ends with a stylistic "..." is not touched.

```python
import re

# C3: a document cut at the start ("…" before the first word) or ending in a "[…]" teaser cut: remove that line
def medicine_c3(text):
    lines = text.split("\n")
    if len(lines) > 2 and re.match(r"^\s*(?:…|\.\.\.)\s*[\u0900-\u097f]", lines[0]):
        lines = lines[1:]
    if len(lines) > 2 and re.search(r"\[(?:…|\.\.\.)\]\s*$", lines[-1]):
        lines = lines[:-1]
    return "\n".join(lines)
```

3. **Action:** fix.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 8 of 20 C3 documents; 3 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** Documents cut in the middle of a sentence without "…" or "[…]" are not caught: 8 of 20.

## Medicine 6: C2 repeated lines

1. **Disease:** C2, 40 of 500 documents (37 fix, 3 drop). Examples:
   - `a9453140c7a770a1`: C2 "खबर को अगर आम लोगों के बीच की आम भावनाओं में" at 12
   - `156518ecd2ad3a57`: C2 "दिल्ली मेट्रो रेल कॉरपोरेशन (DMRC) के मुख्य कार्यकारी निदेशक" at 534
   - `f19322797744e0e8`: C2 "2 जून को हाथरस में सत्संग के दौरान हुई भगदड़ से 121 लोगों की मौत के" at 278
2. **Medicine:** Remove a line of 40 or more characters that repeats an earlier line exactly; the first copy stays. Short refrains such as "भाइयों और बहनों" are below the limit.

```python
import re

# C2: a line of 40+ characters that repeats an earlier line exactly; the first copy stays
def medicine_c2(text):
    seen, out = set(), []
    for line in text.split("\n"):
        key = line.strip()
        if len(key) >= 40:
            if key in seen:
                continue
            seen.add(key)
        out.append(line)
    return "\n".join(out)
```

3. **Action:** fix.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 6 of 40 C2 documents; 6 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** A long sentence that a writer repeats on purpose (a quoted statement, a refrain in a poem) loses its second copy. Repeats with small differences are not caught: 6 of 40.

## Medicine 7: A6 wrong or mixed script (ASCII | or Latin I typed for the danda)

1. **Disease:** A6, 46 of 500 documents (42 fix, 4 drop). Examples:
   - `7952deb7a1c71995`: A6 "है|" at 8244
   - `1e638ceb8920faf1`: A6 "हैI" at 23521
   - `91ad466ec2dd9ef4`: ASCII "*" used as danda mid-sentence (3x): "बरामद *" at 57; "की गई *" at 394; "ा गया *" at 734
2. **Medicine:** Replace "|" or Latin "I" with "।" only when it follows a sentence-final verb (है, हैं, था, गया, सकते ...) and ends the sentence. A "|" used as a separator between names or titles is left alone.

```python
import re

# A6: ASCII "|" or Latin "I" typed for the danda, only right after a sentence-final verb
_VERB = (r"है|हैं|था|थे|थी|थीं|गया|गई|गयी|गए|होगा|होगी|होंगे|रहा|रही|रहे|सकता|सकती|सकते|करें|जाएगा|जाएगी|"
         r"जाएंगे|दिया|दी|दिए|किया|किए|हुआ|हुई|हुए|मिला|मिली|मिले|जाता|जाती|जाते|चाहिए|लिया|लिए")
_A6 = re.compile(r"(?<![ऀ-ॿ])(" + _VERB + r") ?[|I](?=[ \t]|\n|$)")


def medicine_a6(text):
    return _A6.sub(r"\1।", text)
```

3. **Action:** fix.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 26 of 46 A6 documents; 15 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** A "|" after a verb that separates a title from a site name ("... है | Site") would become a danda. Fake dandas after other words are not fixed: 26 of 46.

## Medicine 8: F1 personal data

1. **Disease:** F1, 16 of 500 documents (13 fix, 3 drop). Examples:
   - `157a92dae8c7615d`: email at offset 9799; phone at offset 9777
   - `4b82ad7e92695e55`: email at offset 28595; phone at offset 28671
   - `1c61f6e0c56fbbc9`: email at offset 7228
2. **Medicine:** Remove free-mail addresses (gmail, yahoo, hotmail, outlook, rediffmail) and Indian mobile numbers, except numbers that follow a helpline, toll-free, WhatsApp, office or customer-care word within 40 characters.

```python
import re

# F1: personal e-mail addresses (free mail) and mobile numbers, not near helpline or office words
_MAIL = re.compile(r"[\w.+-]+@(?:gmail|yahoo|hotmail|outlook|rediffmail|ymail)\.[a-z.]+", re.I)
_MOB = re.compile(r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)")
_ORG = re.compile(r"हेल्पलाइन|टोल|फ्री|व्हाट्सएप|whatsapp|helpline|toll|कार्यालय|office|कस्टमर|customer|support", re.I)


def medicine_f1(text):
    out = _MAIL.sub("", text)

    def mob(m):
        near = out[max(0, m.start() - 40):m.start()]
        return m.group(0) if _ORG.search(near) else ""
    return _MOB.sub(mob, out)
```

3. **Action:** fix.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 10 of 16 F1 documents; 0 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** A private number written next to a word such as "कार्यालय" is kept; an official mobile number with no such word is removed. Names and addresses are not caught: 10 of 16.

## Medicine 9: D3 mixed language

1. **Disease:** D3, 13 of 500 documents (13 fix). Examples:
   - `f6f77aeff3b688d0`: English word "technology" at offset 428
   - `7261baa0a3edfb1d`: English word "comments" at offset 8986
   - `be03493ed6a40df3`: English word "Technology" at offset 101
2. **Medicine:** No cure. Natural Hindi-English mixing is labelled, not judged (DISEASES.md), so the rule changes nothing.

```python
import re

# D3: natural Hindi-English mixing is labelled, not cured
def medicine_d3(text):
    return False
```

3. **Action:** keep.
4. **Harm test:** gold set `ind-hi-hplt_gold.csv`, 67 documents, run with `harm_test_indic.py`. Changed 0 of 67, dropped 0 of 67 (0.00%): **PASS**. ZWJ/ZWNJ audit: **PASS**. Normal-form audit: **PASS**. Pack check (the 500 labelled documents of this pack): cures 0 of 13 D3 documents; 0 other diseased documents touched; 0 of 150 clean documents touched.
5. **Side effects:** None: the rule changes nothing.

## Run order

Run the drop rules first, so that no fix is spent on a document that is dropped anyway: C5, C4, D4. Then the fixes: C1 removes template lines, C3 removes cut first or last lines, C2 removes repeats of what is left, A6 restores the danda, and F1 removes personal data last so that no later step can bring it back. D3 changes nothing. The sections above are in this order, so the harm tool's "ALL IN ORDER" run follows it.

## All rules in order

Running all nine rules one after the other on the gold set: changed 0 of 67, dropped 0 of 67: **PASS**.
