# Medicine sheet: ind-ta-sangraha-v (Hemaaaa04)

Counts below are document counts from the final 500-row `labels.csv`. A medicine is included for every disease found in more than five documents.

## Harm-test status and method

The official harm test was completed on 3 November 2026 using the rebuilt 141-document Tamil gold set. All 10 medicines pass individually and in sequence: 0 documents changed, 0 dropped, joiners preserved, and normal form preserved.

- Medicine tested: commit `27b1be2`, SHA-256 `3c800eab928e`
- Gold set: `teams/02-data-b/gold/ind-ta-sangraha-v_gold.csv`, 141 documents, SHA-256 `da9e3ff4db5d`, upstream main `ea7b533`
- Pack: `ind-ta-sangraha-v.parquet`, SHA-256 `1df8e92c0f6a`
- Tool: `teams/02-data-b/tools/harm_test_indic.py`
- Limit: no medicine may change or drop more than 1% of the gold set (1.41 of 141 documents)

Only the harm-test documentation is updated here; the tested medicine functions remain unchanged.

## Medicine 1 — C1 boilerplate

1. **Disease:** C1, 123 documents.
   - `b696ac9e380537d5`: `வீரன் அழகுமுத்துகோன் பிறந்தநாள்`
   - `28e55a22748757af`: `Sign up to receive our newsletter in your inbox every day!`
   - `d883b4426f420c7c`: `தற்கொலை செய்துக் கொள்ளாமல் காப்பாற்றியது வடிவேலு தான்`
2. **Medicine:** Remove only reviewed, exact boilerplate blocks when they occur at a document boundary. Do not use a broad “headline-like” regex and do not remove a matching sentence from the middle of an article.

```python
BOUNDARY_BOILERPLATE = (
    "Sign up to receive our newsletter in your inbox every day!",
    "Sign up to receive our newsletter in your inbox every day",
    "Thank you for reading this Dhinasari News Article.",
    "Follow @ Google News:",
    "Subscribe to: Post Comments (Atom)",
)

def medicine_c1(text: str) -> str:
    out = text
    changed = True
    while changed:
        changed = False
        candidate = out.strip()
        for block in BOUNDARY_BOILERPLATE:
            if candidate.startswith(block):
                out = candidate[len(block):].lstrip(" \t\r\n:-")
                changed = True
                break
            if candidate.endswith(block):
                out = candidate[:-len(block)].rstrip(" \t\r\n:-")
                changed = True
                break
    return out
```

3. **Action:** Fix by removing the confirmed boundary block. Drop only documents dominated by boilerplate with no recoverable article.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** A quoted newsletter sentence or site name may be legitimate article content. Unlisted or slightly changed boilerplate will not be removed, by design.

## Medicine 2 — D3 mixed language

1. **Disease:** D3, 92 documents.
   - `b696ac9e380537d5`: `Top Tamil News, Breaking News`
   - `8a913e9545fa0e4a`: `யூ ஹேவ் பிராட் அவுட் எ ப்ளாக் ஹோம் டு லைம் லைட்!`
   - `92ab99210be56e29`: `புதிய ATM Card பெறலாம்.`
2. **Medicine:** D3 is an annotation, not a deletion rule. Preserve natural bilingual names, dialogue and technical terms. Remove the mixed-language text only when another disease, such as C1, identifies a removable block.

```python
def medicine_d3(text: str) -> str:
    return text  # annotation only; never delete language mixing automatically
```

3. **Action:** Retain the text and annotate D3. Apply another disease-specific medicine only when independently justified.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** Automatically deleting Latin or other Indic-script material would damage names, acronyms, quotations, code-switching and technical prose.

## Medicine 3 — B4 template and code junk in prose

1. **Disease:** B4, 23 documents.
   - `7cce84d0d76b0c30`: literal `\n`
   - `00b0ea09f19c54e1`: literal `\n`
   - `b16791a5741328a2`: `XNUMX`
2. **Medicine:** Decode repeated literal `\n` sequences as newlines only in prose that does not look like code. Other placeholders, including `XNUMX`, require source-specific review and must not be deleted by this rule.

```python
import re

def medicine_b4(text: str) -> str:
    if text.count("\\n") < 2:
        return text
    code_like = re.search(
        r"\x60{3}|<script|\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(", text
    )
    if code_like:
        return text
    return text.replace("\\n", "\n")
```

3. **Action:** Fix the high-confidence literal-newline case. Review other placeholders manually; drop the document if the missing value cannot be recovered and changes the meaning materially.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** Programming tutorials, regex explanations and quoted escape sequences may intentionally contain `\n`. The code guard is conservative but cannot identify every code example.

## Medicine 4 — C3 truncated document

1. **Disease:** C3, 22 documents.
   - `65126393f0ef52c9`: `திருமணம் கைகூடும் பிரார்த்தனை தலமாகவும்`
   - `9a112ddbdcf4b4d2`: `திருமகள் திருவவதரி பர் ராகவமயிலும் இரண்டாமடியிலும்`
   - `42686daa22d0e057`: `கரி-யானை`
2. **Medicine:** Never generate a missing ending. Append text only when it is recovered from the source. If the source is unavailable, allow a reviewer to trim only a confirmed incomplete boundary fragment; otherwise leave the text unchanged for review.

```python
from typing import Optional

def medicine_c3(
    text: str,
    recovered_tail: Optional[str] = None,
    confirmed_cut: Optional[int] = None,
) -> str:
    if recovered_tail is not None:
        return text + recovered_tail
    if confirmed_cut is not None:
        return text[:confirmed_cut].rstrip()
    return text
```

3. **Action:** Fix from the source or trim only a verified incomplete boundary. Drop when truncation destroys the document's usefulness and no source is available.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** Poetry, headlines, lists and deliberate cliff-hanger endings can appear incomplete. An automatic sentence-ending test would create false positives.

## Medicine 5 — C5 keyword or link lists

1. **Disease:** C5, 21 documents.
   - `3ec2b85b9976a2dd`: `கமலுடன் கைகோர்க்கும் சிம்பு?`
   - `e80a9f732508728d`: `வாக்காளர்களுக்கு ரூ 2 ஆயிரம் பணம் கொடுக்கும் மோடி?`
   - `b2c838dc3fb7809a`: `பொருளாதார மந்த நிலை சிக்கலில் இருந்து விடுபடுமா சிங்கப்பூர்?`
2. **Medicine:** Use structure only to flag candidates: at least five non-empty units, at least 80% shorter than 120 characters, and no sustained paragraph over 300 characters. A human must confirm that the document is a list rather than an article before deletion.

```python
def flag_c5(text: str) -> bool:
    units = [u.strip() for u in text.splitlines() if u.strip()]
    if len(units) < 5:
        return False
    short_ratio = sum(len(u) < 120 for u in units) / len(units)
    return short_ratio >= 0.80 and max(map(len, units)) <= 300

def medicine_c5(text: str) -> str:
    return text  # flag only; a reviewer decides whether to remove or drop
```

3. **Action:** Drop a confirmed list-only document. If a valid article is followed by a list, fix by removing only the confirmed list boundary.
4. **Harm test:** Official Tamil gold set, `medicine_c5`: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**. `flag_c5` is diagnostic only and does not mutate text.
5. **Side effects:** Recipes, poems, FAQs, sports results and legitimate bullet reports can resemble keyword lists.

## Medicine 6 — C4 two documents joined

1. **Disease:** C4, 18 documents.
   - `81e45dba89f683a1`: `மடிப்பாக்கம் : மடிப்பாக்கம் பகுதியில்`
   - `939cefd2cf7ac11d`: `டையிங் மற்றும் பிரிண்டிங் சேவைகளுக்கான வரி விகிதம் எவ்வளவு`
   - `0144a10753d9b239`: `அமைதியை ஆயுதமாக கொண்டு அன்பு என்னும் வீரர்களுடன்`
2. **Medicine:** Split only at a human-verified character boundary. Without a verified boundary, return the original as one document and send it for review.

```python
from typing import List, Optional, Union

def medicine_c4(
    text: str, boundary: Optional[int] = None
) -> Union[str, List[str]]:
    if boundary is None:
        return text
    left = text[:boundary].rstrip()
    right = text[boundary:].lstrip()
    return [part for part in (left, right) if part]
```

3. **Action:** Fix by splitting and retaining each coherent document. Drop only when no reliable boundary or coherent component can be recovered.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** Topic changes, sidebars, quotations and related reporting inside one article can look like a join. An inferred boundary can split a valid document.

## Medicine 7 — D4 bad machine translation

1. **Disease:** D4, 13 documents.
   - `90bddd0458dc149e`: `இருதரப்பு ஒத்துழைப்பு இருதரப்பும் தங்கள் பலம்`
   - `b69cb7b45edb1712`: `பூஜ்ஜியங்களும் ஒருவர்`
   - `795daa0aeef87e3c`: `விரிவான தகவல்கள் வழங்கப்பட்டன. அவர்களுக்கு.`
2. **Medicine:** No regex can repair wrong meaning. A fluent reviewer must compare the source, supply a verified retranslation, or confirm that the document should be dropped. The automated default is deliberately a no-op.

```python
from typing import Optional

def medicine_d4(
    text: str,
    verified_retranslation: Optional[str] = None,
    confirmed_drop: bool = False,
) -> Optional[str]:
    if verified_retranslation is not None:
        return verified_retranslation
    if confirmed_drop:
        return None
    return text
```

3. **Action:** Replace with a source-verified translation when available; otherwise drop after fluent/source confirmation.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** Regional Tamil, technical terminology and unusual but grammatical prose may be mistaken for machine translation. Factual errors alone do not prove D4.

## Medicine 8 — G1 cut at the vowel sign

1. **Disease:** G1, 9 documents.
   - `1cce2a46807b7b14`: `அவ்வா ே ற`
   - `f6246724d09b7381`: `ெவளியே`
   - `f24194e6f2459cf1`: `கூ,ூங்க`
2. **Medicine:** Detect Tamil dependent vowel signs that occur at the start of text or immediately after whitespace or punctuation. Report offsets for source recovery; do not reorder or delete characters automatically.

```python
import unicodedata

TAMIL_DEPENDENT_SIGNS = set(range(0x0BBE, 0x0BCD + 1)) | {0x0BD7}

def flag_g1(text: str) -> list[int]:
    offsets = []
    for i, char in enumerate(text):
        if ord(char) not in TAMIL_DEPENDENT_SIGNS:
            continue
        if i == 0:
            offsets.append(i)
            continue
        previous = text[i - 1]
        if previous.isspace() or unicodedata.category(previous).startswith("P"):
            offsets.append(i)
    return offsets

def medicine_g1(text: str) -> str:
    return text  # flag only; recover the intended order from a trusted source
```

3. **Action:** Fix only from a source scan or verified spelling. Drop documents with pervasive unrecoverable OCR corruption.
4. **Harm test:** Official Tamil gold set, `medicine_g1`: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**. `flag_g1` is diagnostic only and does not mutate text.
5. **Side effects:** A detector that flags every Tamil vowel sign would destroy valid Tamil. Punctuation around quotations or OCR layout may also create candidates requiring visual review.

## Medicine 9 — F3 harmful content

1. **Disease:** F3, 9 documents.
   - `edf1604bab0805b8`: `செக்ஸ் விசயத்தில் கேட்கவே வேண்டாம்`
   - `213d21ab3087ece1`: `மதவெறி பிடித்த முஸ்லிம் வியாபாரிகள்`
   - `409f0fd2354ea3c5`: `பாலியல் பலாத்காரத்திற்கு ஆளான சிறுமி`
2. **Medicine:** Do not use keyword deletion. Send candidates to the course's human safety review and preserve the original until the reviewer confirms the policy decision.

```python
def medicine_f3(text: str) -> str:
    return text  # human safety review only; no automatic mutation or drop
```

3. **Action:** Drop documents confirmed as F3 under the course policy. Retain legitimate educational, legal or prevention material when the policy permits it.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** Keywords alone confuse harmful endorsement with news, survivor support, education, legal reporting and prevention advice.

## Medicine 10 — C2 repeated lines

1. **Disease:** C2, 8 documents.
   - `24ec1b20186fa9ea`: `காலாண்டு முடிவுகள்!`
   - `5d170761d80b3fe2`: `மேக் இன் இந்தியா திட்டத்தின்கீழ் ரூ.500 கோடி முதலீட்டில்`
   - `a8c212b32a048791`: `காரைக்கால் : அரசு நிறுவனமான பாப்ஸ்கோ மூலம் ஏற்பாடு செய்யப்பட்ட விழாவில்`
2. **Medicine:** Automatically collapse only runs of three or more exactly repeated consecutive non-empty lines after whitespace normalization. Two-copy cases and non-consecutive repetition require review.

```python
import re

def medicine_c2(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out = []
    i = 0
    while i < len(lines):
        key = re.sub(r"\s+", " ", lines[i]).strip()
        if not key:
            out.append(lines[i])
            i += 1
            continue
        j = i + 1
        while j < len(lines):
            other = re.sub(r"\s+", " ", lines[j]).strip()
            if other != key:
                break
            j += 1
        if j - i >= 3:
            out.append(lines[i])
        else:
            out.extend(lines[i:j])
        i = j
    return "".join(out)
```

3. **Action:** Fix by retaining one copy of a confirmed repeated run. Drop only documents dominated by repetition with no recoverable unique content.
4. **Harm test:** Official Tamil gold set: 141 documents; 0/141 changed, 0/141 dropped (0.00%); joiners `ok`; normal form `ok`; **PASS**.
5. **Side effects:** Refrains, chants, tables, legal formulas and deliberate emphasis may repeat lines. The three-copy threshold intentionally leaves some two-copy disease cases for manual review.

## Official harm-test command

```console
python3 teams/02-data-b/tools/harm_test_indic.py --medicine medicine.md \
  --pack ind-ta-sangraha-v.parquet --gold-dir teams/02-data-b/gold
```

The combined run of all 10 medicines in sheet order also produced 0 changed and 0 dropped documents, with joiners and normal form both ok: **PASS**. Any later change to a medicine function requires a fresh official gold-set run.
