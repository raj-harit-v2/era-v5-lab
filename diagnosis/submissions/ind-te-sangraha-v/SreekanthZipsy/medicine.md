# Medicine sheet: ind-te-sangraha-v (SreekanthZipsy)

The pack has 500 Telugu documents. Final verdicts: 234 clean, 211 fix, 55 drop. A clean row has no disease. If a disease is present, the verdict is fix when the text is still usable and drop when it is not.

A medicine is included only when the disease code appears on more than five documents. Counts below are for all 500 rows.

The harm test uses the Latest Telugu gold set. A rule passes when it changes or drops at most 1% of that set or 1 document, whichever is more, so at most 1 of these 46. ZWJ (U+200D) and ZWNJ (U+200C) counts must stay the same, and a document that is NFC must stay NFC. Every rule passes.


| rule | changed | dropped | joiners | normal form | result |
|---|---|---|---|---|---|
| D3 | 0 | 0 | ok | ok | PASS |
| C1 | 0 | 0 | ok | ok | PASS |
| C2 | 0 | 0 | ok | ok | PASS |
| C3 | 0 | 0 | ok | ok | PASS |
| D4 | 0 | 0 | ok | ok | PASS |
| A1 | 0 | 0 | ok | ok | PASS |
| C4 | 0 | 0 | ok | ok | PASS |
| C5 (`medicine_c5_drop`) | 0 | 0 | ok | ok | PASS |
| D5 | 0 | 0 | ok | ok | PASS |
| G1 | 0 | 0 | ok | ok | PASS |
| all 10 in order | 0 | 0 | ok | ok | PASS |

## Medicine 1

1. **Disease:** D3, 180 documents. Telugu sentences that also contain English words in Latin letters. A lone `@` is not English. A word written in Telugu letters is not D3. Every Latin-script word is cited in the evidence. This mixing is ordinary in the news and in quotations.
   - `2fb6cf727899fed3`: `Cyclone Biparjoy : బిపర్ జోయ్`
   - `1c312ac9eefa118f`: `NTR: ప్రశాంత్ నీల్`
   - `b50a4cc592e3b96d`: `We use cookies` inside an otherwise Telugu report (also C1)
2. **Medicine:** Leave every Latin letter where it is. The label records the mix. The text stays.

```python
def medicine_d3(text: str) -> str:
    return text
```

3. **Action:** Leave the text. The verdict is fix, because the disease is present and the text is still usable. The verdict is drop only when another disease makes the document unusable.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** Deleting Latin tokens would remove names, film titles, and quoted English from ordinary Telugu. That rule is not used.

## Medicine 2

1. **Disease:** C1, 75 documents. Menus, cookie banners, subscribe lines, and site footers.
   - `b50a4cc592e3b96d`: `We use cookies and other tracking technologies`
   - `b1384c6cc6ab6eba`: `Templatesyard is a blogger resources site`
   - `9e51f015da032472`: `Follow us on:`
2. **Medicine:** Delete only these boilerplate spans. The article text stays.

```python
import re

_C1 = [
    re.compile(r"We use cookies and other tracking technologies[\s\S]*", re.I),
    re.compile(r"To Start receiving timely alerts please follow the below steps:[\s\S]*?save the changes\.", re.I),
    re.compile(r"Do you want to clear all the notifications from your inbox\??"),
    re.compile(r"Templatesyard is a blogger resources site[\s\S]*", re.I),
    re.compile(r"Subscribe to:\s*Post Comments \(Atom\)"),
    re.compile(r"Follow us on:\s*"),
    re.compile(r"(?m)^Apps:\s*$"),
    re.compile(r"(?m)^Visit:\s*$"),
]

def medicine_c1(text: str) -> str:
    for pattern in _C1:
        text = pattern.sub("", text)
    return text
```

3. **Action:** Fix the text by deleting those spans.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** On the rest of the pack the function edits 9 documents, none of them in the gold set. Telugu-only footers, wiki lines such as `సవరించు`, and `Posted By:` are outside this list, so they remain. A broader “delete any short English line” rule would cut quotations inside clean articles.

## Medicine 3

1. **Disease:** C2, 40 documents. The same line repeated in one document.
   - `510706dcf275e0e1`: `నిఖిల్, ఐశ్వర్య మీనన్ జంటగా నటించిన స్పై సినిమా తాజాగా రిలీజయి పాజిటివ్ టాక్ తెచ్చుకుంది. దీంతో స్పై చిత్రయూనిట్ సక్సెస్ మీట్ నిర్వహించింది.`
   - `eaff92d180453906`: `కోట్ల చేరిక... టీడీపీకి ప్లస్సా మైనస్సా?`
   - `249674961e23e8f2`: `సినిమాల్లో పెద్దగా ఎక్సపీరియన్స్ లేని ఓ కుర్రాడు ఇప్పుడు విమర్శకుల ప్రశంసలు సైతం అందుకుంటున్నారు. అతనే 'ఏజెంట్ సాయి శ్రీనివాస ఆత్రేయ' ఫేం నవీన్ పోలిశెట్టి.`
2. **Medicine:** If a line of at least 40 characters is repeated, keep the first copy and delete the later copies. Lines shorter than 40 characters stay, so verse refrains are left alone.

```python
def medicine_c2(text: str) -> str:
    lines = text.splitlines(keepends=True)
    seen = set()
    out = []
    changed = False
    for line in lines:
        key = line.strip()
        if len(key) >= 40 and key in seen:
            changed = True
            continue
        if len(key) >= 40:
            seen.add(key)
        out.append(line)
    return "".join(out) if changed else text
```

3. **Action:** Fix the text.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** On the rest of the pack the function edits 5 documents, none of them in the gold set. A repeated sentence that is not its own full line is kept. A line that is repeated on purpose and is at least 40 characters would be collapsed to one copy.

## Medicine 4

1. **Disease:** C3, 36 documents. The text stops in the middle of a word or a sentence.
   - `d6f4ca9e67d1c377`: ends `కలుసుకొమ్మని యెవరో సర్ఫో`
   - `03b7747985417b40`: ends `వంశపరమైన భిన్న`
   - `a6e850e12ae7f479`: ends `గురుమూ రి`
2. **Medicine:** There is no automatic cut. A short document that ends mid-word is dropped by the reader. A long document that is complete until the last few words is trimmed back to the last finished sentence by the reader. A rule that trims any text whose last character is not `.?!।` changes clean documents, including ones that end with a name in parentheses, a verse number, or `ఇది కూడ తనలో తనకు`.

```python
def medicine_c3(text: str) -> str:
    return text
```

3. **Action:** Drop a short fragment. Trim only the unfinished tail of a long document. The shipped function does neither by itself.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** Classical pages often end at a verse boundary with no full stop. Treating that as truncation deletes a finished page. A punctuation trimmer that cuts any text not ending in `.?!।` changes 3 of the pack’s 234 clean rows and 0 of the 46 gold documents, so it is not the medicine.

## Medicine 5

1. **Disease:** D4, 27 documents. Word-for-word translation whose Telugu does not carry the meaning.
   - `8acd153461c0a159`: `ఆ రుణగ్రహీత అది తన ఆస్తి, గృహ మరియు నమోదు చిరునామా, నమోదు ఎందుకంటే, లేఖ పొందింది.`
   - `914d223d96eef13d`: `స్మార్ట్ టీవీ రంగంలో ప్రజాస్వామ్యం మరియు పాలన కొనసాగిస్తోంది`
   - `012697e62432d373`: `మెరుస్తున్న చక్రాలు మరియు శ్రావ్యమైన ధ్వని సంకేతాలు ఆనందం పిల్లలకు జోడిస్తుంది.`
2. **Medicine:** A reader drops a document when the Telugu is this kind of nonsense. Counting English function words (`the`, `and`, `of`, `with`) and dropping the document also drops usable bilingual text that is labeled fix: dictionary entries, assembly proceedings, and quotations. That counter is not the medicine.

```python
def medicine_d4(text: str) -> str:
    return text
```

3. **Action:** Drop, after a person has read the document. The shipped function does not drop by itself.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.** The function-word counter also changes 0 of these 46, and it is still not the medicine: on the rest of the pack it drops 15 usable documents labeled fix, including the dictionary `1be5c8a382d18b18` and the assembly transcript `d26ff1f87bbc8614`.
5. **Side effects:** Stiff but understandable Telugu, and English that is a real quotation, can look a little like D4. Those stay.

## Medicine 6

1. **Disease:** A1, 19 documents, all from the reviews that were already in the file. The evidence on those rows is an ellipsis or a spaced dot, for example:
   - `de79d6228a92faeb`: `ఓపెన్ టైటిల్స్ గెలవగా...2016లో`
   - `2a0cfe90fd36e4ed`: `నిర్వహిస్తుండగా. . . సప్తగిరి`
   - `adb60cef617f4530`: `- జర్నలిస్టుల కుటుంబాలకు`
   None of the 19 contains U+200B, U+FEFF, U+00AD, U+202A–U+202E, or U+2066–U+2069.
2. **Medicine:** Delete only those code points. Ellipsis, `. .`, and hyphens stay. ZWJ and ZWNJ stay.

```python
_A1 = set("\u200b\ufeff\u00ad\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")

def medicine_a1(text: str) -> str:
    return "".join(ch for ch in text if ch not in _A1)
```

3. **Action:** Fix the text when one of those characters is present.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.** The function also changes 0 documents in the whole pack, because the 19 A1 labels contain none of those code points.
5. **Side effects:** Deleting `...` would cut ordinary Telugu. U+200E (left-to-right mark) is outside the A1 list, so it stays. One document, `799ebca7bf5dc94e`, begins `→` plus U+200E; that mark is recorded in the note and is not stripped.

## Medicine 7

1. **Disease:** C4, 18 documents. Two unrelated texts are joined.
   - `7ae5b6d6945a0438`: an essay on the Mahabharata is interrupted by `ఆరగిస్తున్నాయి పుట్టిన రోజు 'కేకులు'`
   - `26590df875eb92ae`: a Yogi survey is followed by `యూపీ బహరిచ్లో బ్లాక్ డెవలప్మెంట్`
   - `354ffb6bf6ed23ed`: `ప్రేమించాలంటూ వెంటబడుతున్న ఓ యువకుడి వేధింపులు` starts a second report
2. **Medicine:** A person splits the document at the boundary. No similarity score is safe enough to do that split on the whole pack: news roundups and bilingual bills are one document on purpose.

```python
def medicine_c4(text: str) -> str:
    return text
```

3. **Action:** Fix by splitting at the boundary the reader marked. Drop only when neither side is a usable text.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** An automatic split on “low word overlap between paragraphs” would cut a clean article that changes topic, and a live news roundup.

## Medicine 8

1. **Disease:** C5, 9 documents. A headline board or tag list with no article.
   - `204fcbd26303bcea`: `BIG BREAKING: 2 రోజులు సెలవులు ప్రకటించిన ప్రభుత్వం`
   - `9e51f015da032472`: `Tomato Price` and `Jadcherla` as separate headline lines
   - `5f780207a338aae4`: `సీఎం జగన్కు బీజేపీ భారీ షాక్. . రాజధాని తరలింపు అసాధ్యం.`
2. **Medicine:** Drop a document only when it is shorter than 800 characters, every line is at most 100 characters, there are at least five lines, and at least four lines contain `!` or `. .`. Longer headline pages are left for a reader because they sometimes contain one real paragraph.

```python
def medicine_c5_drop(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or len(text) > 800:
        return False
    if max(len(ln) for ln in lines) > 100:
        return False
    bangs = sum(1 for ln in lines if "!" in ln or ". ." in ln)
    return len(lines) >= 5 and bangs >= 4
```

3. **Action:** Drop when the function returns true. Otherwise leave the document for a reader.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** On the rest of the pack the function drops one document, `204fcbd26303bcea`, which is already labeled drop and is not in the gold set. A headline page that contains one line longer than 100 characters, such as `9e51f015da032472`, is not dropped. A play with short spoken lines can look similar; the length cap is what keeps `fc8117893babcf61` out of the drop.

## Medicine 9

1. **Disease:** D5, 6 documents, all from the reviews that were already in the file.
   - `a9ee60f523c326bc`: `జీవ బహ్మైక్యసార మంజరీ ద్విపద.`
   - `7b75b64db3dfb65b`: `నాచార్యు నడుగులందును గ్రుచ్చుకొన్న ముండ్లు తీయించెను,`
   - `ba8fbf4025410834`: `ఈ చర్మం, రంగు కలిగిన విద్య, స్పష్టంగా పరిమితం మరియు స్పష్టంగా కనిపిస్తుంది.`
   The third example is translationese. The first two are classical Telugu lines.
2. **Medicine:** No automatic rewrite. Translationese and classical Telugu cannot be separated by a regex.

```python
def medicine_d5(text: str) -> str:
    return text
```

3. **Action:** Drop only a document a reader has judged to be translationese. Classical verse stays.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** A rule that drops “unusual” Telugu would drop the classical books in this pack. News style can be stiff and still be native.

## Medicine 10

1. **Disease:** G1, 6 documents. A vowel sign, virama, anusvara, or visarga is separated from its consonant by a space.
   - `fc48a4849a6197cc`: `చ్ఛేషాన్నంబు ంబు` (U+0C02 at 968) and `నన్ను ంగనుగొని` (U+0C02 at 1006)
   - `9c00599739ab0177`: `విదితై ్వ` (U+0C4D at 892) and `తేజసై ః` (U+0C03 at 1952)
   - `57558e75ec2ff83c`: `పరిత్యక్త ః` (U+0C03 at 418)
2. **Medicine:** Delete a space or tab that sits immediately before a Telugu vowel sign (U+0C3E–U+0C4C), virama (U+0C4D), length mark (U+0C55–U+0C56, U+0C62–U+0C63), anusvara (U+0C02), or visarga (U+0C03). Word-initial arasunna (U+0C01), as in classical `ఁబడి`, is not a split mark and is kept.

```python
_G1 = set(
    chr(c) for c in
    list(range(0x0C3E, 0x0C45))
    + list(range(0x0C46, 0x0C49))
    + list(range(0x0C4A, 0x0C4D))
    + [0x0C4D, 0x0C55, 0x0C56, 0x0C62, 0x0C63, 0x0C02, 0x0C03]
)

def medicine_g1(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if text[i] in " \t" and i + 1 < len(text) and text[i + 1] in _G1 and out:
            i += 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)
```

3. **Action:** Fix the text. The document is not dropped.
4. **Harm test:** Changed 0 of 46 (0.00%). Dropped 0 of 46 (0.00%). **PASS.**
5. **Side effects:** Outside the gold set the function changes 7 pack documents. One is a clean row, `27667afb5f1275fb` (`తనిఖీలు ి`), which is not in the gold file. The other six are the G1 rows above, including `b4523e3d75fea2fd`, `123141ba7400bfd5`, and `f4a7b263fde8b2dc`. A visarga that a Sanskrit editor spaced on purpose is joined to the previous word. That is the repair this disease asks for. Arasunna at the start of a classical word is untouched.
