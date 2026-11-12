# Medicine sheet: ind-bn-fw2 (AditeyaAItronics)

One section for each disease found more than five times in the 500 documents of `ind-bn-fw2`. Counts are from `labels.csv`. Offsets are character offsets in the document text.

Each rule is a Python function `medicine_<code>(text)` that returns the new text (fix) or `True` (drop). The harm tests were run with `teams/02-data-b/tools/harm_test_indic.py` on the gold set `teams/02-data-b/gold/ind-bn-fw2_gold.csv` (238 documents that two readers marked clean). A rule passes when it changes or drops at most 1% of the gold set or 1 document, whichever is more (here: 2 documents). The sha256 in the harm-test lines is of this file before those lines were filled in; the code is unchanged, and running the tool on this file gives the same counts.

## Medicine 1: C1 Boilerplate

1. **Disease:** C1, 136 documents in this pack. Examples:
   - `f93b659eb49f48a6`: `বাংলাদেশ সময়: ২১১৫ ঘণ্টা, অক্টোবর ০৫, ২০২২` at 2340 (timestamp line)
   - `b205db03a45e1e9f`: `View this post on Instagram` at 1419 (embed label)
   - `4e45f99b4192a309`: `মন্তব্য করুন` at 718 (comment-button text)
2. **Medicine:** Delete a line (at most 200 characters) that starts with a known page-chrome phrase (read-more links, publish/update timestamps, share and follow prompts, Instagram and tweet embeds, copyright and "powered by" credits, tag lines, print-edition label), or that is only a widget label (related news, comment, advertisement, table of contents, view counter).

```python
import re

def _nk(p):
    # ড় ঢ় য় may be stored as one code point or as letter + nukta (U+09BC): match both.
    for one, two in (('\u09dc', '\u09a1\u09bc'), ('\u09dd', '\u09a2\u09bc'), ('\u09df', '\u09af\u09bc')):
        p = p.replace(two, one).replace(one, '(?:%s|%s)' % (one, two))
    return p

_START = re.compile(_nk(r"""^[\s\-–—#*>/]*(?:
    আর(?:ও|\u09cb|\u09cbও)\s*(?:পড়\u09c1ন|পড়তে\s*পারেন)|এছাড়\u09beও\s*পড়\u09c1ন|
    প্রকাশিত(?:\s*হয়\u09c7ছে)?\s*[:\u0983]|প্রকাশের\s*সময়\s*[:\u0983]|আপডেট\s*সময়|শেষ\s*আপডেট\s*[:\u0983]|
    বা\u0982লাদেশ\s*সময়\s*[:\u0983]|Published\s+on|Last\s+Updated\s+on|
    শেয়\u09beর\s*করুন|View\s+this\s+post\s+on\s+Instagram|A\s+post\s+shared\s+by|
    সর্বস্বত্ব\s*সংরক্ষিত|Powered\s+by\s|For\s+all\s+the\s+latest|Continue\s+Reading|
    ট্যাগ\s*[:\u0983]|Tags?\s*:|পোস্ট\s*ট্যাগ|হোয়\u09beটসঅ্যাপে\s*ফলো\s*করুন|
    প্রতিনিধি\s+প্রিন্ট\s+সংস্করণ|\[hupso\]
)""", ), re.X)
_WHOLE = re.compile(_nk(r"""^[\s\-–—#*>/]*(?:
    মন্তব্য\s*করুন|সম্পর্কিত\s*(?:খবর|নিউজ)|Related\s+News|Advertisement|বিজ্ঞাপন|
    সুচিপত্র|সূচিপত্র|পরিচ্ছেদসমূহ|Read\s+More|শীর্ষ\s*সংবাদ\s*[:\u0983]?|
    [\d০-৯,]+\s*(?:total\s+views.*|বার\s+(?:পড়\u09be\s+হয়\u09c7ছে|পঠিত))
)\s*$""", ), re.X)
_TWEET = re.compile(r"pic\.twitter\.com/|^\s*[—-]\s*[^\n]{1,60}\(@\w{1,15}\)\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s*$")

def medicine_c1(text):
    """Delete whole lines that are page chrome. A line is deleted only if it is at most 200 characters long."""
    out = []
    for line in text.split('\n'):
        if len(line) <= 200 and (_START.match(line) or _WHOLE.match(line) or _TWEET.search(line)):
            continue
        out.append(line)
    return '\n'.join(out)
```

3. **Action:** **Fix:** delete the matching lines.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - A sentence that really starts with one of these phrases is deleted, for example a story that begins "প্রকাশিত: ..." as part of its text, or a quoted tweet that is the subject of the article.
   - It catches 67 of the 136 C1 documents in my pack. Site-specific chrome (masthead footers, desk initials, photo credits, date bars in other formats) is not caught; a list of these strings per site would catch more.
   - Only the label line of a read-more block is deleted when the headline is on the next line.

## Medicine 2: A3 Mojibake / legacy-font conversion residue

1. **Disease:** A3, 49 documents in this pack. Examples:
   - `0cc55d56de34d944`: `স¦াক্ষর` at 456, U+00A6 BROKEN BAR inside স্বাক্ষর
   - `1c748f4d41f5cb07`: `প্রয়ােজন` at 648, U+09BE U+09C7 (া + ে) typed for ো U+09CB, 16 times
   - `71bb93238817a1c8`: `সহÑসভাপতি` at 543, U+00D1 for a hyphen (Bijoy residue)
2. **Medicine:** Most A3 in this pack is text converted from the old Bijoy/SutonnyMJ fonts. The conversion left Latin-1 symbols (¦ ¤ ¯ Ñ Í æ ø), dashes and angle quotes between Bengali letters, where they stand for conjuncts. There is no safe one-to-one map back, so a document with 3 or more such residues is dropped. Separately, misordered or doubled vowel signs (া+ে, ৈ+া, ে+ে, ি+ি, ু+ু, া+া) are repaired.

```python
import re

_PAIRS = [('\u09be\u09c7', '\u09cb'),   # \u09be + \u09c7 typed for \u09cb
          ('\u09c8\u09be', '\u09cc'),   # \u09c8 + \u09be typed for \u09cc
          ('\u09c7\u09c7', '\u09c7'), ('\u09bf\u09bf', '\u09bf'), ('\u09c1\u09c1', '\u09c1'), ('\u09be\u09be', '\u09be')]
# Bijoy / legacy-font residue: a Latin-1 symbol, dash or angle quote glued between two Bengali characters.
_RESIDUE = re.compile('(?<=[\u0980-\u09ff])[¡-ÿ–—‹›‚”](?=[\u0980-\u09ff])')

def medicine_a3(text):
    """Drop a document with 3 or more legacy-font residues (they cannot be mapped back safely).
    Otherwise repair doubled or misordered vowel signs."""
    if len(_RESIDUE.findall(text)) >= 3:
        return True
    for bad, good in _PAIRS:
        text = text.replace(bad, good)
    return text
```

3. **Action:** **Drop** the document if it has 3 or more residues; otherwise **fix** the vowel signs.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - Documents with 1 or 2 residues keep them (the rule is precise, not complete): 17 of the 49 A3 documents are caught.
   - A real `”` or `–` glued between two Bengali words without a space counts as a residue.
   - Many A3 errors (ref on the wrong letter as in `রির্পোট`, lost virama as in `সমপ্রচার`) are valid characters in the wrong order and need a word list, not a character rule.

## Medicine 3: D3 Mixed language

1. **Disease:** D3, 48 documents in this pack. Examples:
   - `4b93d08ed10573b7`: `A group of Shiv Sena workers pelt stones at BJP…` at 2533 (embedded English tweet)
   - `38f950f6b0b45fdc`: `শুভেন্দু অধিকারী (Suvendu Adhikari)` at 76 (English name in brackets: natural, labelled clean)
   - `a0d44e27d217989b`: `Love is a beautiful feeling that can be express…` at 0 (English page with Bengali captions)
2. **Medicine:** DISEASES.md says to label D3, not judge it: English names, acronyms and quotes in brackets are normal in Bengali news. So the medicine leaves the text alone and drops a document only when more than 40% of its letters are Latin, because then it is an English document in the Bengali pool.

```python
import re

def medicine_d3(text):
    """Mixed language is natural in Bengali writing, so it is not cleaned. Only a document that is mostly
    English (more than 40% of its letters are Latin) is dropped from the Bengali pool."""
    latin = len(re.findall('[A-Za-z]', text))
    bengali = len(re.findall('[\u0980-\u09ff]', text))
    return latin + bengali > 0 and latin / (latin + bengali) > 0.40
```

3. **Action:** **Keep** (no change). **Drop** only a document that is mostly English.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - A bilingual glossary or a Bengali grammar of English would be dropped.
   - English tweets inside Bengali articles are not removed here; C1 removes the tweet signature lines.

## Medicine 4: D4 Bad machine translation

1. **Disease:** D4, 42 documents in this pack. Examples:
   - `6a18f8751bb83059`: `তখন আপনার খালি ব্যাংক অ্যাকাউন্টটি মনে রাখে না you` at 439 (English word left at the end)
   - `4257b1b94789b299`: `সবকিছু অনেক বেশী prosaic` at 874 (topwar.ru /bn/ auto-translation)
   - `e3056440a69157e3`: `Teflon ফিল্ম glued করা যাবে না.` at 1092 (Chinese supplier /bn/ page)
2. **Medicine:** Two signals must both be present. (1) At least half of the digits are Latin (0-9), with 5 or more digits: Bengali news sites write numbers in Bengali digits, and MT keeps the Latin ones. (2) The words এবং and একটি make up 2% or more of the words: MT translates every "and" and "a/an", native writers use them far less (median 0.15% in my clean documents, 2.65% in my D4 documents).

```python
import re

_FUNC = re.compile('(?<![\u0980-\u09ff])(?:এবং|একটি)(?![\u0980-\u09ff])')

def medicine_d4(text):
    """Drop likely machine translation: native Bengali news writes numbers in Bengali digits and uses
    'এবং' / 'একটি' sparingly; English-to-Bengali MT keeps Latin digits and translates every 'and' / 'a'."""
    words = max(1, len(text.split()))
    latin_d = len(re.findall('[0-9]', text))
    bengali_d = len(re.findall('[০-৯]', text))
    if latin_d + bengali_d < 5 or latin_d / (latin_d + bengali_d) < 0.5:
        return False
    return 100 * len(_FUNC.findall(text)) / words >= 2.0
```

3. **Action:** **Drop** the document.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - It catches 31 of 42 D4 documents in my pack. MT pages that use Bengali digits are missed.
   - Native Bengali text that uses Latin digits and many এবং (wire copy translated by people, product pages) is dropped: 6 such documents in my pack, none in the gold set.
   - The thresholds were set on this one pack; they need checking on other Bengali packs before running at scale.

## Medicine 5: G2 Lost ZWJ

1. **Disease:** G2, 20 documents in this pack. Examples:
   - `3024066d06a72875`: `র্যাব` at 105, U+09B0 U+09CD U+09AF U+09BE with no U+200D (RAB, twice)
   - `dcfb4dde46d6ca77`: `র্যালি` at 155, same sequence
   - `ab9a0079afc95a73`: `র্যাডার` at 454, same sequence
2. **Medicine:** At the start of a word, র + ্ + য + া is the English-loan sound "rya" (RAB, rally, radar), written র + ZWJ + ্ + য + া so that it renders as র with ya-phala. Without the ZWJ it renders as reph on য. The medicine inserts the ZWJ only at the start of a word.

```python
import re

ZWJ = chr(0x200D)
# র + \u09cd + য + \u09be at the start of a word is the loan-word ra + ya-phala (র\u200d\u09cdযাব, র\u200d\u09cdযালি). Without ZWJ it
# renders as reph + য (র্যা). Inside a word the reph reading is correct (কার্যালয়), and after a virama
# (ব্র্যান্ড) র is already a ra-phala, so those are left alone.
_LOAN = re.compile('(?<![\u0980-\u09ff])র্(?=যা)')

def medicine_g2(text):
    """Insert ZWJ after র in loan-word র্যা."""
    return _LOAN.sub('র' + ZWJ + '\u09cd', text)
```

3. **Action:** **Fix:** insert ZWJ (U+200D).
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - Inside a word the reph reading is usually correct (কার্যালয়), so dialect forms like `কইর্যা` (row 132) are not fixed.
   - After a virama (ব্র্যান্ড) র is already a ra-phala and needs no ZWJ, so it is left alone.
   - This medicine adds a joiner by design, so the ZWJ/ZWNJ audit fails for any gold document it changes. On this gold set it changes none.

## Medicine 6: A6 Wrong or mixed script

1. **Disease:** A6, 18 documents in this pack. Examples:
   - `17d425168aa54166`: `পারেন না৷` at 226, U+09F7 BENGALI CURRENCY NUMERATOR FOUR used as the danda (7 times)
   - `f6af8060b15e4a87`: ASCII `|` (U+007C) used as the danda after `শীত পড়ছে আসতে আসতে` at 117
   - `bd59fdf51e29e37b`: `চাইৰে` at 3800, Assamese ৰ (U+09F0) for ব
2. **Medicine:** Replace danda look-alikes after Bengali text with the real danda: ৷ (U+09F7) before a space or line end, the doubled ।৷, an ASCII `|` at the end of a line, and a Latin `l` standing alone after a Bengali word.

```python
import re

_DANDA_LOOKALIKE = re.compile('(?<=[\u0980-\u09ff’”)])৷(?=\\s|$)')  # ৷ (U+09F7) used as danda
_DOUBLE = re.compile('।৷')                                                  # ।৷
_PIPE = re.compile('(?<=[\u0980-\u09ff’”)]) ?\\|(?=[ \\t]*(?:\\n|$))', re.M)  # ASCII | at line end
_L_DANDA = re.compile('(?<=[\u0980-\u09ff’”]) l(?=\\s|$)')                  # Latin l as danda

def medicine_a6(text):
    """Replace danda look-alikes after Bengali text with the real danda । (U+0964)."""
    text = _DOUBLE.sub('।', text)
    text = _DANDA_LOOKALIKE.sub('।', text)
    text = _PIPE.sub('।', text)
    return _L_DANDA.sub('।', text)
```

3. **Action:** **Fix:** replace with the danda । (U+0964).
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - A real currency fraction ৷ after a Bengali letter would be changed (none in this pack).
   - A table row flattened with `|` separators that ends in a Bengali word gets a danda.
   - Assamese ৰ inside Bengali words is not fixed: it stands for ব in some documents and র in others, so it needs a person.

## Medicine 7: C3 Truncated document

1. **Disease:** C3, 15 documents in this pack. Examples:
   - `2a662b3c3193d8da`: `পের ঘোষণা দিয়ে` at 0 (starts in the middle of a word)
   - `a03da238fe5d7dcd`: `সহযোগী সংগঠনের সভা` at 832 (ends in the middle of a word)
   - `3190209debfab88d`: `পারে পৌঁছে দেয়। […]` at 597 (teaser cut mark)
2. **Medicine:** Drop a document whose last line ends with a teaser cut mark: `[…]`, `বিস্তারিত..`, `Continue Reading`, `Read Entire Article`, `Read more`.

```python
import re

_CUT = re.compile(r'(?:\[\s*(?:…|\.\.\.)\s*\]|বিস্তারিত\s*\.{2,}|Continue\s+Reading|Read\s+(?:Entire\s+Article|more))\W*$', re.I)

def medicine_c3(text):
    """Drop a document whose last line ends with a teaser cut mark ([…], 'বিস্তারিত..', 'Continue Reading').
    Documents cut in mid-sentence without a mark are not touched: they cannot be told apart from
    pages that end with a name, a list item or a caption."""
    last = text.rstrip().rsplit('\n', 1)[-1]
    return bool(_CUT.search(last))
```

3. **Action:** **Drop** the document.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - Only 3 of 15 C3 documents are caught. A document cut without a mark cannot be told apart by a rule from a page that ends with a name, a list item or a caption, so those are left for the C1/C4 rules or a person.
   - A document that really ends by quoting `[…]` is dropped.

## Medicine 8: C4 Two documents joined

1. **Disease:** C4, 13 documents in this pack. Examples:
   - `4040d1c6b90ddd77`: `Continue Reading →` at 850 (category page, two excerpts)
   - `605429156ca4df6d`: `বিস্তারিত..` at 230 (date-archive page, ten teasers)
   - `a041c47c2735d3f0`: `Original strip the other healthier and minutes …` at 4583 (English spam glued to the end)
2. **Medicine:** Drop index, tag and archive pages: two or more teaser cut marks (`বিস্তারিত..`, `Continue Reading`, `[…]`, `Read More »`) mean that several stories were glued into one document.

```python
import re

_TEASER = re.compile(r'বিস্তারিত\s*\.{2,}|Continue\s+Reading|\[\s*(?:…|\.\.\.)\s*\]|Read\s+More\s*(?:»|→|$)', re.I | re.M)

def medicine_c4(text):
    """Drop index, tag and archive pages: two or more teaser cut marks mean several stories were glued together."""
    return len(_TEASER.findall(text)) >= 2
```

3. **Action:** **Drop** the document.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - Only 2 of 13 C4 documents are caught. Joins without a marker (spam paragraph injected, second story appended) need a topic-shift check, not a regex.
   - A long article with two "read more" links inside it is dropped.

## Medicine 9: C5 Lists of keywords or links

1. **Disease:** C5, 13 documents in this pack. Examples:
   - `482a27019963a3e4`: `- সরকার বিকল্প প্রস্তাব না দিলে নয়াপল্টনেই সমা…` at 0 (10-line headline ticker)
   - `a005aedd65fe3aa8`: `- বিয়ানীবাজারের ১ নম্বর কূপ থেকে গ্যাস উত্তোলন…` at 1399 (50-line headline list)
   - `e4aa2126d8505b14`: `পোস্ট ট্যাগ -` at 4002 (tag list; the C1 medicine removes the label line)
2. **Medicine:** Delete runs of 5 or more consecutive bullet lines (`- `, `• `, `* `) that look like headlines: 5 or more words (bullet included), at most 120 characters, no sentence-final punctuation.

```python
import re

def _is_headline(line):
    s = line.strip()
    return (s.startswith(('- ', '• ', '* ')) and len(s) <= 120 and len(s.split()) >= 5
            and not s.endswith(('।', '?', '!', '.', ':')))

def medicine_c5(text):
    """Delete runs of 5 or more consecutive bullet lines that look like headlines: at least 4 words after
    the bullet, at most 120 characters, no sentence-final punctuation (related-news tickers)."""
    lines = text.split('\n')
    keep = [True] * len(lines)
    i = 0
    while i < len(lines):
        j = i
        while j < len(lines) and _is_headline(lines[j]):
            j += 1
        if j - i >= 5:
            for k in range(i, j):
                keep[k] = False
        i = max(j, i + 1)
    return '\n'.join(l for l, k in zip(lines, keep) if k)
```

3. **Action:** **Fix:** delete the list.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - A real bulleted list of 5 or more long items without full stops (steps, features) is deleted.
   - Short items are kept on purpose: a first draft that also deleted short items removed a list of Dhaka landmarks from a gold document. Tag clouds on one line are not caught.

## Medicine 10: A5 Wrong normal form (khanda-ta)

1. **Disease:** A5, 9 documents in this pack. Examples:
   - `1b3f77a799e452d2`: `পশ্চাত্পদ` at 725, U+09A4 U+09CD for U+09CE
   - `4f21302fa2468076`: `উত্কণ্ঠাকে` at 2022, same
   - `7d9c6bfe71e1cdbb`: `চিকিত্সাধীন` at 821, same
2. **Medicine:** ত + virama at the end of a word, or before ক, স or প, is khanda-ta written the old Unicode way. Replace it with ৎ. A ZWJ or ZWNJ after the virama is a deliberate choice and is left alone.

```python
import re

# ত + virama (ত্) at the end of a word, or before ক স প, is a khanda-ta written the old way.
# A ZWJ/ZWNJ after the virama is a deliberate choice and is left alone.
_T = re.compile('ত্(?=[কসপ]|(?![\u0980-\u09ff\u200c\u200d]))')

def medicine_a5(text):
    """Replace ত্ with ৎ (U+09CE) at a word end and before ক স প."""
    return _T.sub('ৎ', text)
```

3. **Action:** **Fix:** replace with ৎ (U+09CE).
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - A word-final ত্ written on purpose (a halant in a Sanskrit quotation) becomes ৎ.
   - It also changes 12 documents that I had not labelled A5 (mostly D4 drops with চমত্কার); I missed those while reading, they are real A5.

## Medicine 11: C2 Repeated lines

1. **Disease:** C2, 8 documents in this pack. Examples:
   - `025cb48d54a14830`: `আমরা ভাষা, ভাষার বৈচিত্র, বহুভাষিকতা ইত্যাদি না…` at 20 (teaser paragraph repeated later)
   - `926ebfd4255ef0a5`: `HTLS 2022: মহিলারা চাইলে সবকিছুই করতে পারেন।` at 0 (lead repeated)
   - `7e6d5db9d0e8bb0c`: `“১১ দিন পর মৃত্যুর কাছে হার মানলেন সোনাগাজীর স্…` at 0 (headline twice)
2. **Medicine:** Delete the second and later copies of any line of 40 or more characters.

```python
def medicine_c2(text):
    """Delete the second and later copies of a line of 40 or more characters."""
    seen, out = set(), []
    for line in text.split('\n'):
        key = line.strip()
        if len(key) >= 40:
            if key in seen:
                continue
            seen.add(key)
        out.append(line)
    return '\n'.join(out)
```

3. **Action:** **Fix:** delete the repeats.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - A poem or song refrain repeated on purpose is cut to one copy if its lines are 40 characters or longer.
   - Repeats that differ by one character (a headline and its slightly edited lead) are not caught.

## Medicine 12: F3 Harmful content

1. **Disease:** F3, 8 documents in this pack. Examples:
   - `80d6bada82e5ff0b`: `বাংলাদেশে 888starz অনলাইন স্পোর্টস বেটিং এবং ক্…` at 0 (betting review)
   - `95261ddc152835cc`: `মোস্টবেট অ্যাপ্লিকেশনটি` at 1371 (betting-app promotion)
   - `43804ba72410d8ff`: `আপনার প্রিয় পর্ন টিউব` at 0 (pornography page)
2. **Medicine:** Drop gambling and pornography pages: 3 or more hits from a short term list (casino, betting brands, porn, xxx and their Bengali spellings, matched as whole words).

```python
import re

_B = '\u0980-\u09ff'
_TERMS = re.compile(r'(?i)casino|betting|mostbet|888starz|1xbet|porn|xxx|sex\s*video|'
                    rf'(?<![{_B}])(?:ক্যাসিনো|বেটি\u0982|মোস্টবেট|বুকমেকার|পর্ন|সেক্স)(?![{_B}])')

def medicine_f3(text):
    """Drop gambling and pornography pages: 3 or more hits of the term list.
    Hate and extremist content is not caught by a word list; it goes to human review."""
    return len(_TERMS.findall(text)) >= 3
```

3. **Action:** **Drop** the document.
4. **Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
5. **Side effects:**
   - News about a casino raid or a betting scandal can reach 3 hits and be dropped. An earlier draft that included জুয়া dropped a gold cricket-fixing story, so that word was removed; whole-word matching stops পর্ন matching inside the name অপর্না.
   - Hate and extremist content (row 60, a conspiracy-book promotion) and the obscene product page (row 384) are not caught by a word list; they need a classifier or a person.

## All medicines in the order above

The same tool also runs every rule one after another on each gold document, as a cleaning pipeline would.

**Harm test:** gold set of 238 documents (ind-bn-fw2 238), medicine.md sha256 93e459d0b451; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 238 (0.00%). Dropped 0 of 238 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**

## Not covered

B4 (5 documents) and the other codes found five times or fewer have no medicine, as the template asks. F1 (3 documents, phone numbers) is not cleaned by a rule here; it should go to the shared PII filter.
