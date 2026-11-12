# Medicine sheet: ind-gu-fw2 (Nisarg189)

Write one section for each disease that you found more than five times.

## About the numbers

- **Pack:** 500 documents, 1,206,370 characters. Labels are in `labels.csv` (348 fix, 102 clean, 50 drop).
- **Count:** a disease is counted in evidence items. Ten codes have more than five items, so this sheet has ten sections: nine medicines and one "no medicine" (D3).
- **Gold set:** `teams/02-data-b/gold/ind-gu-fw2_gold.csv` (the same 19 documents as `gujarati_gold.csv`), on `main` (Data B PR #161, merged 31 Oct). A document is gold when two readers (nisarg189 and vedang-patel-10) marked it `clean` after a full read. The harm tests below run on these 19 documents.
- **How the harm test was run:** with the Data B tool on `main`: `python3 teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md --pack ind-gu-fw2.parquet --gold-dir teams/02-data-b/gold --show 5 --md-out harm.md`. Result: all 10 rules and all rules in order PASS (exit code 0). The part-4 text of each medicine below is the `harm.md` output of that run.
- **Own check (extra information):** each medicine was also run on the 102 documents in this pack that `labels.csv` marks `clean`. One reader marked them, not two. The 19 gold documents are part of these 102.
- **Limits of these tests:**
  - The gold set is small (19 documents). The own clean set was made by the same reader as the labels. If a disease was missed in a document marked `clean`, the test cannot see it.
  - The rules were built on these same 500 documents. When a rule hit an own clean document, the rule was changed until it passed. So 0% is the best case. On new Gujarati text, the rules will probably change or drop some good documents. A larger gold set will give better numbers.
- **1% limit:** a medicine passes if it changes or drops at most max(1 document, 1%) of the gold set. For 19 gold documents, this is 1 document.
- **Acted / labelled / recall:** "acted" is the number of documents that the medicine changes, splits or drops. "Labelled" is how many of those documents have the code in `labels.csv`. "Recall" is the share of the labelled documents that the medicine finds.

## Fix or drop: the policy

- **Drop always removes the whole document.** A medicine never drops one word or one line. To remove a word or a line, a medicine uses `fix`.
- **Fix is the default.** Most diseases in this pack are a small bad part of a good Gujarati article: a footer, a dateline, a doubled sign. A fix removes or replaces only that part, and the article stays.
- **Drop only when the text itself is bad.** Two medicines drop: M4 (machine-translated sites) and M7 (machine-translation residue inside words). In these documents every sentence is bad, so no fix can save them.
- **Split, not cut.** When two articles are joined (C4), M8 splits them into two documents. Both articles are good text, so nothing is thrown away.

## How the medicines run together

The drop rules run first, then the fixes, then the split, in this order: M4, M7, M1, M9, M3, M5, M6, M10, M8. D3 has no medicine, so it is not in the pipeline. This function runs the whole pipeline on one document (the medicines are below):

```python
def clean(text, url):
    """Run all medicines in order. Return the output documents: none if dropped, more than one if split."""
    for drop_rule in (m4_d4, m7_a6):
        if drop_rule(text, url)[1] == "drop":
            return []
    for fix in (m1_c1, m9_c5, m3_f1, m5_a5, m6_g1, m10_a3):
        text, _ = fix(text, url)
    parts, action = m8_c4(text, url)
    return parts if action == "split" else [text]
```

| Result | Documents | Characters | Share of the pack |
|---|---|---|---|
| Dropped by M4 | 16 | 83,052 | 6.9% |
| Dropped by M7 | 8 | 37,019 | 3.1% |
| Removed by fixes | 173 changed | 17,015 | 1.4% |
| Split by M8 | 1 (into 3) | 0 | 0.0% |
| **Kept** | **476** | **1,069,284** | **88.6%** |

What we lose that we did not want to lose:

- **Dropped documents:** 22 of the 24 dropped documents are labelled `drop`. The other 2 are `aa0df086f25036cc` (1,359 characters) and `8ccf813522ed3909` (2,270), both labelled `fix`. Both are machine-translated product or travel pages on `gu.` sub-domains. That is 3,629 characters, 0.3% of the pack.
- **Fixes:** 711 of the removed characters are outside a labelled span. When checked one by one, they are boilerplate that the labels did not mark (more "View this post on Instagram" and "આ પણ વાંચો" lines), public phone numbers, and doubled signs. No article sentence is removed.
- **What we do not catch:** 28 of the 50 `drop` documents stay. These are machine-translated pages on ordinary `.com` domains, adult clickbait and listing pages. They need more drop rules.

Harm test (Data B tool, `ALL IN ORDER`): all medicines together change 0 and drop 0 of the 19 gold documents. PASS. Own check: they change 0 and drop 0 of the 102 own clean documents.

## Summary

| Medicine | Code | Items / docs | Action | Acted | Labelled | Recall | Gold (19): changed | Gold (19): dropped | Own check (102): changed / dropped | Result |
|---|---|---|---|---|---|---|---|---|---|
| M1 | C1 | 482 / 290 | fix: remove lines and tags | 131 | 131 | 45% | 0 | 0 | 0 / 0 | pass |
| M2 | D3 | 481 / 101 | no medicine | 0 | 0 | – | 0 | 0 | 0 / 0 | – |
| M3 | F1 | 624 / 85 | fix: mask | 19 | 7 | 8% | 0 | 0 | 0 / 0 | pass |
| M4 | D4 | 72 / 40 | drop document | 16 | 15 | 38% | 0 | 0 | 0 / 0 | pass |
| M5 | A5 | 116 / 33 | fix: replace letters | 24 | 23 | 70% | 0 | 0 | 0 / 0 | pass |
| M6 | G1 | 42 / 22 | fix: remove signs | 18 | 18 | 82% | 0 | 0 | 0 / 0 | pass |
| M7 | A6 | 54 / 16 | drop document | 9 | 9 | 56% | 0 | 0 | 0 / 0 | pass |
| M8 | C4 | 13 / 10 | split document | 1 | 1 | 10% | 0 | 0 | 0 / 0 | pass |
| M9 | C5 | 17 / 12 | fix: remove lines | 24 | 6 | 50% | 0 | 0 | 0 / 0 | pass |
| M10 | A3 | 6 / 3 | fix: replace characters | 3 | 2 | 67% | 0 | 0 | 0 / 0 | pass |

## Shared code

Each medicine is a function `(text, url) -> (result, action)`. The action is `keep`, `fix`, `split` or `drop`.

For the harm tests (Data B `harm_test_indic.py` and Data A `harm_test.py`), each section also has a function `medicine_<code>(text, url=None)`. It returns the new text, or `True` to drop the document. A split is given to the harm test as a fix: the parts joined by a blank line. The harm tools run each section on its own, so each section's code repeats the constants it needs from the code below.

```python
import re
from urllib.parse import urlparse
GU = "\u0A80-\u0AFF"                          # Gujarati block
GU_SIGN = "\u0A81-\u0A83\u0ABC-\u0ACD"      # dependent signs, nukta, virama
GU_VOWEL_SIGN = "\u0ABE-\u0ACC\u0A81-\u0A83"
GU_DIGIT = "\u0AE6-\u0AEF"                    # Gujarati digits 0-9
DEVA = "\u0900-\u097F"                        # Devanagari block

def _fix(old, new):
    return (new, "keep" if new == old else "fix")

```

## Medicine 1: C1 boilerplate lines, tags and the start dateline

1. **Disease:** C1, 482 items in 290 documents. Examples:
   - `bfbddfa37a31c087` at 1308: `Copyright © 2022-23 DB Corp ltd., All Rights Reser…`
   - `09a1138a7eaf5cc4` at 0: `(એજન્સી) નવી દિલ્હી, તા.ર૮`
   - `9c013a675712ff90` at 3026: `આ પણ વાંચો`
2. **Medicine:** remove the dateline at the start of the document. Remove each line that starts with a known site template. Remove the tag `– Latest Gujarati News`, but not the paragraph that it is joined to.

```python
import re
GU = "\u0A80-\u0AFF"                          # Gujarati block
GU_DIGIT = "\u0AE6-\u0AEF"                    # Gujarati digits 0-9
def _fix(old, new):
    return (new, "keep" if new == old else "fix")

C1_LINE = re.compile(
    r"^[ \t]*(?:Copyright © .*DB Corp|This website follows the DNPA"
    r"|ગુજરાતી સમાચાર નો ખજાનો એટલે News18 ગુજરાતી|View this post on Instagram"
    r"|લેટેસ્ટ મનોરંજન, News અને Videos માટે પેજ લાઈક કરો"
    r"|\(?(?:નોંધ|નોધ|Disclaimers?)[ \t]*[:ઃ\-]"
    r"|(?:READ ALSO|MUST READ|આ પણ વાંચો)[ \t]*[:ઃ\-–]?).*\n?", re.M)
C1_TAG = re.compile(r"[ \t]*– Latest Gujarati News")
C1_DATELINE = re.compile(
    r"\A\s*(?:\((?:એજન્સી|અમારા પ્રતિનિધિ તરફથી|સંવાદદાતા દ્વારા)\)\s*)?"
    rf"(?:[{GU}]+(?: [{GU}]+)?\s*,\s*)?તા\.\s*[{GU_DIGIT}રપ0-9]{{1,2}}\s*[,:ઃ–\-]?\s*")

def m1_c1(text, url=None):
    new = C1_DATELINE.sub("", text, count=1)
    new = C1_LINE.sub("", new)
    return _fix(text, C1_TAG.sub("", new))

def medicine_c1(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m1_c1(text, url)[0]
```

   **Example** (`4af2a377c9aa5051`):
   - Before: `… પર સૌની નજર છે. – Latest Gujarati News⏎સિક્યોરિટી ડિપોઝિટની …`
   - After: `… પર સૌની નજર છે.⏎સિક્યોરિટી ડિપોઝિટની …`

3. **Action:** fix. Only the template line or the tag is removed. The article stays.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - The tag is removed alone, not with its line. In `4af2a377c9aa5051` the tag is joined to the end of each paragraph, so a line rule would remove about 4,000 characters of the article.
   - The medicine removes only the "read also" header line. The headline list under it stays.
   - The medicine finds only the frequent templates. Recall is 45%. Most other C1 items are one-site lines (bylines, share requests, signatures) that no general rule can find.
   - A dateline with no `તા.` (for example `અમદાવાદઃ`) stays.
   - A real sentence that starts with `નોંધ:` is removed with the boilerplate.
   - Removed in the pack: 15,418 characters. 643 of them are outside a labelled span, and all of them are boilerplate that the labels did not mark.

## Medicine 2: D3 mixed language (no medicine)

1. **Disease:** D3, 481 items in 101 documents. Examples:
   - `6c34ae8bfde1bf78` at 501: `Galaxy` (in `જ્યારે Galaxy S10માં એક્સિડેન્ટલ ટચથી`)
   - `241daa0409850eee` at 975: `WhatsApp` (in `WhatsApp વેબ કેવી રીતે કામ કરે છે`)
   - `3ed1c081935c62ce` at 0: `श्रीभगवानुवाच…` (a Sanskrit verse in Devanagari, next to its Gujarati version)
2. **Medicine:** none. `DISEASES.md` says that mixed language "can be natural; label it, do not judge it". Most D3 items in this pack are brand names, film titles and English terms inside good Gujarati sentences, and the sentences need them. The document is kept as it is.

```python
import re

def m2_d3(text, url=None):
    return (text, "keep")

def medicine_d3(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m2_d3(text, url)[0]
```

3. **Action:** keep (no change).
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - The medicine changes nothing (no medicine for D3).
5. **Side effects:**
   - None from this medicine. A document with D3 and another disease is handled by the medicine for that disease. For example, an English footer line is removed by M1 (C1), and a machine-translated page is dropped by M4 or M7.

## Medicine 3: F1 phone numbers and emails

1. **Disease:** F1, 624 items in 85 documents. Most items are names of private people. Examples (type and position only):
   - `f5b5303747485fca`: address at 14273, phone number at 14351 and 14360
   - `5a8e7392dd213881`: phone number at 1651 (a reporter's personal mobile in the byline)
   - `1b0fc1e2ea855b1c`: person name at 785
2. **Medicine:** replace each Indian mobile number (Latin or Gujarati digits, with or without +91) with `[PHONE]`. Replace each email address with `[EMAIL]`.

```python
import re
GU_DIGIT = "\u0AE6-\u0AEF"                    # Gujarati digits 0-9
def _fix(old, new):
    return (new, "keep" if new == old else "fix")

PHONE = re.compile(rf"(?<![0-9{GU_DIGIT}])(?:\+91[\s-]?)?[6-9૬-૯][0-9{GU_DIGIT}]{{4}}"
                   rf"[\s-]?[0-9{GU_DIGIT}]{{5}}(?![0-9{GU_DIGIT}])")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def m3_f1(text, url=None):
    return _fix(text, EMAIL.sub("[EMAIL]", PHONE.sub("[PHONE]", text)))

def medicine_f1(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m3_f1(text, url)[0]
```

   **Example** (made up, because a real value must not be copied):
   - Before: `વધુ માહિતી માટે મો. 9xxxxxxxxx પર સંપર્ક કરો`
   - After: `વધુ માહિતી માટે મો. [PHONE] પર સંપર્ક કરો`

3. **Action:** fix (mask). The sentence stays. Only the number or the email changes.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - The medicine does not find names, and names are most of the F1 items. Recall is 8%. Names of private people need a named-entity model and a list of public people.
   - It also masks public numbers that are not F1: desk numbers, helplines, business numbers and placeholder emails (12 documents in the pack). The model loses only the digits, and privacy is not harmed.
   - Landline numbers (8 digits with an STD code) are not found.

## Medicine 4: D4 machine-translated sites, by URL

1. **Disease:** D4, 72 items in 40 documents. Examples:
   - `3917a1b840c261f7` at 1419: `સરળ હપ્તો` ("easy installation" translated as "easy instalment")
   - `8a8d9a6ffd1d7271` at 1286: `અમને સત્તાવાર રીતે શેકવામાં આવ્યા છે.`
   - `8d516dab7886b834` at 207: `અરજી:` ("Application" translated as "petition")
2. **Medicine:** drop the document if the host starts with `gu.` (the Gujarati copy of a foreign site), or if its top-level domain is a non-Indian country or a spam domain.

```python
import re
from urllib.parse import urlparse

FOREIGN_TLD = {"de", "ch", "es", "fr", "it", "cn", "ru", "top", "world"}

def m4_d4(text, url=None):
    host = (urlparse(url or "").hostname or "").lower()
    bad = host.startswith("gu.") or host.rsplit(".", 1)[-1] in FOREIGN_TLD
    return (text, "drop" if bad else "keep")

def medicine_d4(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m4_d4(text, url)[1] == "drop"
```

   **Example** (`3917a1b840c261f7`, `gu.mikeicemachine.com`): a product page of an ice-machine maker. It is machine-translated from English, for example `માળખું, જગ્યા બચત, સરળ હપ્તો.` The whole document is dropped.

3. **Action:** drop the whole document. A fix cannot help, because every sentence is machine-translated.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - The Data B tool gives the rule only the text, not the URL. This rule reads only the URL, so the tool cannot see it act. With the URL of each gold document from the pack, it drops 0 of 19.
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - Machine-translated pages on ordinary `.com` domains (for example Spanish tech blogs) are not found. Recall is 38%.
   - Lost: 16 documents, 83,052 characters (6.9% of the pack). 14 of them are labelled `drop`. The other 2 are machine-translated pages that are labelled `fix` (3,629 characters).
   - `.io` is not in the list. It would drop a readable machine-translated FAQ that is labelled `fix`.
   - A real Gujarati page on a foreign domain or a `gu.` sub-domain is dropped.

## Medicine 5: A5 legacy-font spellings

1. **Disease:** A5, 116 items in 33 documents. Examples:
   - `41b7c9dcbe119b9b` at 867: `ાે` (written for `ો`)
   - `09a1138a7eaf5cc4` at 24: `ર૮` (the letter `ર` written for the digit `૨`)
   - `8fb25749776eab64` at 36: `્ર્વ` (written for `્વ`)
2. **Medicine:** replace the legacy pairs with the Unicode letter. Replace `રૃ` with `રૂ` when no virama comes before it. In a number made of Gujarati digits, replace the letters `ર` and `પ` with `૨` and `૫`.

```python
import re
GU = "\u0A80-\u0AFF"                          # Gujarati block
GU_DIGIT = "\u0AE6-\u0AEF"                    # Gujarati digits 0-9
def _fix(old, new):
    return (new, "keep" if new == old else "fix")

A5_PAIRS = [("ાે", "ો"), ("ાૈ", "ૌ"), ("અા", "આ"), ("અો", "ઓ"), ("અે", "એ"), ("અૈ", "ઐ"),
            ("ૈા", "ૌ"), ("્ર્વ", "્વ")]
A5_RU = re.compile(r"(?<!્)રૃ")
A5_DIGIT = re.compile(rf"(?<![{GU}])[{GU_DIGIT}રપ]*[{GU_DIGIT}][{GU_DIGIT}રપ]*(?![{GU}])")

def m5_a5(text, url=None):
    new = text
    for a, b in A5_PAIRS:
        new = new.replace(a, b)
    new = A5_RU.sub("રૂ", new)
    new = A5_DIGIT.sub(lambda m: m.group(0).replace("ર", "૨").replace("પ", "૫"), new)
    return _fix(text, new)

def medicine_a5(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m5_a5(text, url)[0]
```

   **Example** (`41b7c9dcbe119b9b`):
   - Before: `તેને જાેતા અમુક` and `જાે કે, સરકાર`
   - After: `તેને જોતા અમુક` and `જો કે, સરકાર`

3. **Action:** fix (replace letters). No text is lost.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - A number that is only `ર` or `પ` with no real digit (for example `તા.પ`) is not fixed.
   - Other legacy spellings (a reph in the wrong place, `ઢ` written as a comma) are not fixed.
   - `શ્રૃંગાર` stays as it is, because a virama comes before `રૃ`.

## Medicine 6: G1 doubled signs and signs with no letter

1. **Disease:** G1, 42 items in 22 documents. Examples:
   - `631da9a005b32c3e` at 800: `જણાવ્યુંં કે` (doubled `ં`)
   - `98b9ca997dc64e33` at 528: doubled sign U+0AC7 (`ેે`)
   - `a4ab5516e2836afa` at 2143: `" ં"` (a sign after a space)
2. **Medicine:** collapse two or more identical dependent signs into one. Remove a vowel sign or `ં` that comes after a space.

```python
import re
GU_SIGN = "\u0A81-\u0A83\u0ABC-\u0ACD"      # dependent signs, nukta, virama
GU_VOWEL_SIGN = "\u0ABE-\u0ACC\u0A81-\u0A83"
def _fix(old, new):
    return (new, "keep" if new == old else "fix")

G1_DOUBLE = re.compile(rf"([{GU_SIGN}])\1+")
G1_ORPHAN = re.compile(rf"(?<=\s)[{GU_VOWEL_SIGN}]")

def m6_g1(text, url=None):
    return _fix(text, G1_ORPHAN.sub("", G1_DOUBLE.sub(r"\1", text)))

def medicine_g1(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m6_g1(text, url)[0]
```

   **Example** (`631da9a005b32c3e`):
   - Before: `જણાવ્યુંં કે, નાવ`
   - After: `જણાવ્યું કે, નાવ`

3. **Action:** fix (remove the extra sign). No text is lost.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - Two different signs in the wrong order (for example `ુૃ`, `ો્`) are not fixed.
   - If the sign after a space belongs to the word before it (a broken word), the medicine removes the sign. It cannot join the word again.
   - 11 of the removed signs are outside a labelled span. They are real doubled signs that the labels did not mark.

## Medicine 7: A6 English letters joined inside Gujarati words

1. **Disease:** A6, 54 items in 16 documents. Examples:
   - `f65c324b39b9db3f` at 799: `standsભા`
   - `953dc7a7731c47d7` at 1199: `Appleપલ`
   - `a4ab5516e2836afa` at 1018: `rod`
2. **Medicine:** count the words in which Latin and Gujarati letters are joined. Do not count an English word with a Gujarati case ending (`NCBએ`, `3Dમાં`), because that is normal Gujarati. If three or more words remain, drop the document. These words come from bad machine translation.

```python
import re
GU = "\u0A80-\u0AFF"                          # Gujarati block

A6_WORD = re.compile(rf"[A-Za-z]+[{GU}]+|[{GU}]+[A-Za-z]+")
A6_ENDING = re.compile(r"[A-Za-z]+(?:ઓ)?(?:એ|ના|ની|નું|નુ|નો|ને|નાં|માં|થી|પર|વાળા|વાળી|ે|ી|ો|ઓ)")

def m7_a6(text, url=None, limit=3):
    n = sum(not A6_ENDING.fullmatch(w) for w in A6_WORD.findall(text))
    return (text, "drop" if n >= limit else "keep")

def medicine_a6(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m7_a6(text, url)[1] == "drop"
```

   **Example** (`953dc7a7731c47d7`, `soydemac.com`): a Spanish Apple blog, machine-translated to Gujarati. It has `Appleપલના`, `Appleપલ` (five times) and `કer`. The whole document is dropped.

3. **Action:** drop the whole document. Removing the broken words leaves broken sentences, because these words come with bad machine translation of the whole page.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped. An earlier version without the case-ending rule dropped 2 own clean documents. This version adds the case-ending rule and drops none.
5. **Side effects:**
   - All 9 documents that it drops are labelled `drop`. Lost: 37,019 characters (3.1% of the pack) after M4.
   - An A6 item that is a Latin fragment with spaces around it (for example `er`, `oc`) is not counted.
   - A news page with many brand names that have a Gujarati ending not in the list (for example `-વાળું`) can be dropped.

## Medicine 8: C4 a second article joined to the first

1. **Disease:** C4, 13 items in 10 documents. Examples:
   - `5850b7f05b243ec4` at 1915: `વડાપ્રધાન મોદી રાફેલ સોદા બાબત સતત કહી રહ્યા છે કે…` (a second article with its own dateline)
   - `a42d054d2bda09d0`: whole document, three dating articles joined
   - `f5b5303747485fca`: whole document, a site home page with about ten articles
2. **Medicine:** find the start of each joined article and split the document there. A start is a dateline line after the first 300 characters, with at least 200 characters of body after it. A start can also be a "READ ALSO" or "MUST READ" marker with a paragraph of 200 or more characters after it.

```python
import re
GU = "\u0A80-\u0AFF"                          # Gujarati block
GU_DIGIT = "\u0AE6-\u0AEF"                    # Gujarati digits 0-9

C4_DATELINE = re.compile(
    r"^\s*(?:\((?:એજન્સી|અમારા પ્રતિનિધિ તરફથી|સંવાદદાતા દ્વારા)\)\s*)?"
    rf"[{GU}]+(?: [{GU}]+)?\s*,\s*તા\.\s*[{GU_DIGIT}રપ0-9]{{1,2}}\s*$", re.M)
C4_MARK = re.compile(r"^\s*(?:READ ALSO|MUST READ)\s*[:\-–]?", re.M)
C4_BODY = re.compile(r"^(?!\s*[-•]).{200,}$", re.M)

def m8_c4(text, url=None, min_part=300, min_body=200):
    cuts = [m.start() for m in C4_DATELINE.finditer(text)
            if m.start() >= min_part and len(text) - m.end() >= min_body]
    m = C4_MARK.search(text)
    if m and C4_BODY.search(text, m.end()):
        cuts.append(m.start())
    if not cuts:
        return (text, "keep")
    bounds = [0] + sorted(set(cuts)) + [len(text)]
    parts = [text[a:b].strip() for a, b in zip(bounds, bounds[1:])]
    return ([p for p in parts if p], "split")

def medicine_c4(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    parts, action = m8_c4(text, url)
    return "\n\n".join(parts) if action == "split" else text
```

   **Example** (`5850b7f05b243ec4`): one document with three Rafale articles. Each starts with `(એજન્સી) નવી દિલ્હી, તા.૧૪`. After the split, there are three documents of 1,887, 1,356 and 903 characters.

3. **Action:** split into one document per article. This is a fix: no text is lost.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - The medicine splits, and does not cut. A cut would throw away the second and third articles (2,260 characters of good text).
   - Recall is 10%. A joined article with no dateline and no marker is not found. A "whole document" C4 (a home page or a list page) needs a drop rule for each page type.
   - Some pages repeat the title and the dateline at the end, with no body after them. The 200-character rule does not split these pages.
   - If the first article is shorter than 300 characters, the split is not made.

## Medicine 9: C5 tag lists and link lines

1. **Disease:** C5, 17 items in 12 documents. Examples:
   - `98b9ca997dc64e33` at 2091: `Tags: અંબાજી મંદિર`
   - `9c013a675712ff90` at 4024: `Android: http://bit.ly/3ajxBk4`
   - `f5b5303747485fca` at 12874: `https://youtu.be/Kjyr9JYd3-I`
2. **Medicine:** remove each line that starts with `Tags:`, `Android:` or `iOS:`, and each line that is only a URL.

```python
import re
def _fix(old, new):
    return (new, "keep" if new == old else "fix")

C5_LINE = re.compile(r"^\s*(?:Tags\s*:|Android\s*:|iOS\s*:).*\n?|^\s*https?://\S+\s*\n?", re.M)

def m9_c5(text, url=None):
    return _fix(text, C5_LINE.sub("", text))

def medicine_c5(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m9_c5(text, url)[0]
```

   **Example** (`98b9ca997dc64e33`):
   - Before: `… ન્યૂઝ18 ગુજરાતી પર⏎Tags: અંબાજી મંદિર`
   - After: `… ન્યૂઝ18 ગુજરાતી પર⏎`

3. **Action:** fix (remove the line).
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - 18 documents are changed that have no C5 label. In all of them, it removes a News18 `Tags:` line inside the C1 span at the end of the document. The change is correct, but the labels count it under C1.
   - A tag listing page or a search results page (a "whole document" C5) is not found.
   - A link line that is part of the article (for example a source link) is removed.

## Medicine 10: A3 mojibake from a wrong code page

1. **Disease:** A3, 6 items in 3 documents. Examples:
   - `d071829b830530e1` at 87: `‚` (U+201A written for `રુ`)
   - `9744dc30898dc0d7` at 3958: `¬©` (Mac-Roman mojibake for `©`)
   - `5689a198c052778a` at 169: `ઘ્ંરુજ્ઞ્ફુ-૧૯` (an English term in a legacy font, read as Gujarati letters)
2. **Medicine:** replace the known mojibake pairs. Replace U+201A followed by `પ` with `રૂપ`. Replace any other U+201A after a Gujarati letter with `રુ`.

```python
import re
GU = "\u0A80-\u0AFF"                          # Gujarati block
def _fix(old, new):
    return (new, "keep" if new == old else "fix")

A3_PAIRS = [("¬©", "©"), ("â€™", "’"), ("â€œ", "“"), ("â€", "”")]
A3_LOWQ_RUP = re.compile(rf"(?<=[{GU}])\u201Aપ")
A3_LOWQ = re.compile(rf"(?<=[{GU}])\u201A")

def m10_a3(text, url=None):
    new = text
    for a, b in A3_PAIRS:
        new = new.replace(a, b)
    new = A3_LOWQ_RUP.sub("રૂપ", new)
    return _fix(text, A3_LOWQ.sub("રુ", new))

def medicine_a3(text, url=None):
    """Harm-test entry: return the new text, or True to drop."""
    return m10_a3(text, url)[0]
```

   **Example** (`d071829b830530e1` and `355a8c8963377a73`):
   - Before: `ગુ‚દાસ કામત` and `બ્રહ્મા સ્વ‚પ છે`
   - After: `ગુરુદાસ કામત` and `બ્રહ્મા સ્વરૂપ છે`

3. **Action:** fix (replace characters). No text is lost.
4. **Harm test:** gold set of 19 documents (ind-gu-fw2 19), medicine.md sha256 3957269425fa; rule: changed or dropped at most 1% or 1 document, whichever is more.
   - Changed 0 of 19 (0.00%). Dropped 0 of 19 (0.00%). **PASS**
   - ZWJ/ZWNJ audit: 0 changed documents with a different count. **PASS**
   - Normal-form audit: 0 changed documents left NFC or lost a compatibility character. **PASS**
   - Own check on the 102 own clean documents: 0 changed, 0 dropped.
5. **Side effects:**
   - In the source font, U+201A can stand for `રુ` or `રૂ`. Only `‚પ` (`રૂપ`, `સ્વરૂપ`) is known to be `રૂ`. Other words get `રુ`, and some of them need `રૂ`.
   - `355a8c8963377a73` has the same mojibake but no A3 label.
   - English terms in a legacy font cannot be decoded without the font table, so they are not fixed.
