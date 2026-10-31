# Medicine sheet: ind-hi-fw2 (raj-harit-v2)

Write one section for each disease that you found more than five times.

**Label snapshot:** **500** rows in `work/labels.csv` (2026-10-29; after residual C1 relabel). Verdicts: **399** clean, **91** fix, **10** drop. Counts and `doc_id` examples below are from that file.

## Medicine 1

1. **Disease:** D3 Mixed language (Hindi–English in one document). **Count in pack labels: 53.**  
   Three examples (`doc_id` and exact characters):
   - `0821df78be0bb368` — `D3@off=0:"Syska ने भारत में Syska BT4070X वायरलेस स्पीकर किया लॉन्च…"`.
   - `8a6bf883cb1345bc` — `D3@off=1102:"पेट खराब होने के लक्षण – Pet kharab hone ke lakshan Hindi"`.
   - `e6f8df619451f11c` — `D3@off=0:"रेपो दर (Repo Rate)"` / `Inflation` glosses in Devanagari body.

2. **Medicine:**  
   - **In words:** Flag documents that are Devanagari-majority but also contain clear Latin-letter runs (titles, brands, technical words). Treat natural HI–EN news/blog mix as **D3 to label**, not as automatic corruption. Do **not** treat Indic ZWJ (U+200D) / ZWNJ (U+200C) as a disease.  
   - **In code (detector sketch):**

```python
import re

_DEVA = re.compile(r"[\u0900-\u097F]")
_LATIN_WORD = re.compile(r"\b[A-Za-z]{3,}\b")

def _flag_d3_mixed(text: str, min_deva: int = 40, min_latin_words: int = 8) -> bool:
    """True if doc looks like natural HI-EN mix (for labeling only; not a drop)."""
    if not text:
        return False
    return len(_DEVA.findall(text)) >= min_deva and len(_LATIN_WORD.findall(text)) >= min_latin_words

def medicine_d3(text: str) -> str:
    """Automatic medicine: keep text. D3 is label/fix; True would mean drop in harm_test_indic."""
    return text or ""
```

3. **Action:** **fix** — keep the text; record disease **D3** with a short quote + character offset in `evidence`. **Drop** only when D3 co-occurs with unsafe or unusable content (for example **F3**, or **C4/C5** trading-spam / fragment-stitch), not for ordinary bilingual Hindi web text.

4. **Harm test:** Data B gold `teams/02-data-b/gold/ind-hi-fw2_gold.csv` (**234** docs, post-#161 rebuild). Tool: `harm_test_indic.py --rule D3` (2026-10-31; allow ≤ max(1, 1%) ≈ 2.34). Automatic medicine `medicine_d3` keeps text (label-only):
   - gold docs **changed**: **0** of 234 (0.00%)
   - gold docs **dropped**: **0** of 234 (0.00%)
   - ZWJ/ZWNJ + NFC audits: **ok** — **PASS**
   Pack side-effect (not gold gate): D3 on **53/500** labeled rows (already fix/drop with D3).

5. **Side effects:** Over-flags English brand names, person names, and English headlines embedded in otherwise good Hindi articles; under-flags romanised-only Hindi (that is closer to **D2**). Must never classify ZWJ/ZWNJ as A1.

## Medicine 2

1. **Disease:** C1 Boilerplate / site furniture. **Count in pack labels: 26.**  
   Three examples (`doc_id` and exact characters):
   - `7550aa66f80ae7c0` — `C1@L0 off=0 "Ads से है परेशान? बिना Ads खबरों के लिए इनस्टॉल करें दैनिक भास्कर ऐप"`.
   - `3a3f617148815241` — `C1@L2 off=40 "*Yearly subscription for just ₹299 Limited Period Offer. HURRY UP!"`.
   - `7a4d26d7944e45a1` — `C1@L5 off=1718 "Posted By: Sanjay Savern"`.

2. **Medicine:**  
   - **In words:** Delete a **whole line only** when the entire line matches site furniture (app-install banner, subscribe/offer line, `Posted By:…`, lone `Advertisement`, `First published` / `Updated` … IST, empty `ये भी पढ़ें` stub, back-to-list, cookie/follow lines). Never delete a partial line or article prose that merely mentions ads.  
   - **In code:**

```python
import re

_C1_LINE = re.compile(
    r"(?is)^\s*(?:"
    r"Ads\s+से\s+है\s+परेशान.*"
    r"|Download\s+Dainik\s+Bhaskar\s+App.*"
    r"|Read\s+the\s+latest\s+and\s+breaking\s+Hindi\s+news\s+on\s+\S+.*"
    r"|\*?Yearly\s+subscription\s+for\s+just\s+.*"
    r"|(?:Updated|First\s+published):?\s+.*\d{4}.*(?:IST|AM|PM).*"
    r"|Posted\s+By:\s*.{1,80}"
    r"|Advertisement\s*"
    r"|Don'?t\s+Miss!?"
    r"|Recover\s+your\s+password\.?"
    r"|A\s+password\s+will\s+be\s+e-mailed\s+to\s+you\.?"
    r"|(?:इसे|ये|यह)\s+भी\s+पढ़ें?\s*[:：]?\s*[–-]?\s*"
    r"|सामान्य\s+सूची\s+पर\s+लौटें.*"
    r"|Share\s+on\s+WhatsApp.*"
    r"|follow\s+us\b.*"
    r"|हम\s+(?:डाटा\s+संग्रह|विज्ञापन).{0,60}कुकी.*"
    r"|cookie\s+(?:policy|notice|banner).*"
    r"|बिना\s+Ads\s+खबरों.*"
    r")\s*$"
)

def strip_c1_lines(text: str) -> str:
    """Remove whole lines that match C1 site furniture; keep everything else."""
    kept = []
    for line in (text or "").splitlines(keepends=True):
        body = line.rstrip("\r\n")
        if _C1_LINE.match(body):
            continue
        kept.append(line)
    return "".join(kept)
```

3. **Action:** **fix** — remove matching furniture lines; keep the document. **Drop** only if removal leaves fewer than about two sentences of usable prose.

4. **Harm test:** Data B gold `ind-hi-fw2_gold.csv` (**234** docs, post-#161). Tool: `harm_test_indic.py --rule C1` (2026-10-31). Ran `strip_c1_lines`:
   - gold docs **changed**: **0** of 234 (0.00%)
   - gold docs **dropped**: **0** of 234 (0.00%)
   - ZWJ/ZWNJ + NFC audits: **ok** — **PASS**
   Pack side check: **0/399** current `clean` rows still match the C1 whole-line regex; C1 on **26/500** labeled rows (all fix).

5. **Side effects:** A real byline that is exactly `Posted By: name` or a lone `Advertisement` line is removed; a dateline line ending in IST that carries news content can be removed if it matches the whole-line pattern; `ये भी पढ़ें` followed by a real headline on the **same** line is kept (whole-line rule), but an empty stub line is removed.

## Medicine 3

1. **Disease:** C3 Truncated document (weak / missing sentence terminator at end). **Count in pack labels: 31.**  
   Three examples (`doc_id` and exact characters):
   - `75f4f997eab9b2bc` — `C3@L13 off=4354 "Categories: राजनीति"`.
   - `e49a90539eea7e8d` — `C3@L1 off=624 "© सेक्सी पिक्चर हिंदी में | आगंतुकों खरीदें"` (drop).
   - `58ad14113bc1f59b` — `C3@L25 off=6546 "Fendi (@fendi) द्वारा Jul 20, 2019…"` (with C5).

2. **Medicine:**  
   - **In words:** Flag documents whose last non-space character is not a sentence terminator (`।` `!` `?` `.` or a closing quote/bracket). Prefer **label + fix** (append a Devanagari danda or trim a trailing stub line) over drop. Do not rewrite the body for ordinary soft endings on otherwise good news text when a human chooses label-only.  
   - **In code (detector sketch):**

```python
import re

_TERM_END = re.compile(r'[।!?.…"\'”’)\]]\s*$')

def _flag_c3_truncated(text: str) -> bool:
    """True if the document does not end on a sentence terminator (label hint only)."""
    t = (text or "").rstrip()
    if not t:
        return False
    return _TERM_END.search(t) is None

def medicine_c3(text: str) -> str:
    """Automatic medicine: keep text. Soft C3 is label/fix; do not mass-drop open endings."""
    return text or ""
```

3. **Action:** **fix** — keep the document; record **C3** with the last line + offset in `evidence`. Optionally append `।` or drop a trailing stub line (byline / `NEXT STORY` / bare `–आईएएनएस`). **Drop** only when truncation leaves the document unusable as training text (e.g. mid-word body cut with almost no remaining sentences).

4. **Harm test:** Data B gold `ind-hi-fw2_gold.csv` (**234** docs, post-#161). Tool: `harm_test_indic.py --rule C3` (2026-10-31). Automatic `medicine_c3` keeps text (label/fix; no mass drop of open endings):
   - gold docs **changed**: **0** of 234 (0.00%)
   - gold docs **dropped**: **0** of 234 (0.00%)
   - ZWJ/ZWNJ + NFC audits: **ok** — **PASS**
   Pack side-effect: C3 on **31/500** labeled rows (fix/drop with C3).

5. **Side effects:** Over-flags intentional open endings (lists, titles, social handles as last line); under-flags mid-document cuts that still end with `।` on a leftover stub. Byline lines like `Posted By: …` without a period become C3 even when the article body was fine.

## Medicine 4

1. **Disease:** C4 Trading-spam / joined or fragment-stitched junk. **Count in pack labels: 9.**  
   Three examples (`doc_id` and evidence):
   - `8f73e0fb991da311` — `C4@L0 off=285 "trading-spam terms x4"` (drop).
   - `c83fbbec4a82f87a` — `C4@L6 off=3205 "trading-spam terms x4"` (drop).
   - `9992ed6ebadee109` — `C4@L0 off=604 "trading-spam terms x10"` with C5 `IQ Option फ़ॉरेक्स` (drop).

2. **Medicine:**  
   - **In words:** Drop documents that pack **four or more distinct** forex/trading/broker terms, or that stitch several short headline-like fragments together with trading language. Do not drop ordinary Hindi news that mentions “बाजार” once. Prefer **drop** over rewrite — the body is usually unusable as clean pretrain text.  
   - **In code (detector sketch):**

```python
import re

_TRADE_TERMS = re.compile(
    r"फ़ॉरेक्स|फॉरेक्स|\bforex\b|बाइनरी\s+ऑप्शन|binary\s+options?|"
    r"ट्रेडिंग\s+प्लेटफ़?ॉर्म|\btrading\b|\bbroker\b|ब्रोकर|"
    r"ट्रेडिंग|ट्रेडर|ऑप्शन|विकल्प\s+ट्रेड",
    re.I,
)

def flag_c4_trading_spam(text: str) -> bool:
    """True if >=4 distinct trading terms (drop-class C4)."""
    terms = {m.group(0).lower() for m in _TRADE_TERMS.finditer(text or "")}
    return len(terms) >= 4
```

3. **Action:** **drop** — do not keep the document for training. Record **C4** (and co-codes such as **C5** / **D3** if present) with a short evidence string. Do **not** try to surgically delete trading paragraphs when the whole page is spam-stitched.

4. **Harm test:** Data B gold `ind-hi-fw2_gold.csv` (**234** docs, post-#161). Tool: `harm_test_indic.py --rule C4` (2026-10-31). Ran `flag_c4_trading_spam`:
   - gold docs **changed**: **0** of 234 (0.00%)
   - gold docs **dropped**: **0** of 234 (0.00%)
   - ZWJ/ZWNJ + NFC audits: **ok** — **PASS**
   Pack side-effect: C4 on **9/500** labeled rows (all verdict=drop).

5. **Side effects:** Can over-flag long finance explainers that list many legitimate market terms; under-flags soft spam with only two trade words plus affiliate URLs (**C5** may still catch URL/phrase spam). Always review co-occurrence with **C5** before trusting a borderline call.

## Medicine 5

1. **Disease:** B2 HTML/XML tags (and pack practice: embedded `http(s)` / share URLs flagged under the same code). **Count in pack labels: 9.**  
   Three examples (`doc_id` and exact characters):
   - `10ee275a9dea2acf` — `B2@off=1128:"https://m.facebook.com/story.php?story_fbid=…"`.
   - `fd775ab063b9b8bd` — `B2@off=608:"https://x.com/ANI/status/1727481458628218949?s=20"`.
   - `bfb237ef7db35193` — `B2@off=1587:"https://admission.punjab.gov.in"`.

2. **Medicine:**  
   - **In words:** Strip HTML/XML tags (`<div>`, `<br/>`, `</p>`, etc.). For this Hindi web pack, also **label** bare share/tracker/social `http(s)` URLs as **B2** and remove the URL token (or a URL-only line) when it is site chrome; do not mass-delete every URL from otherwise clean articles without review.  
   - **In code (tag strip — automatic medicine):**

```python
import re

_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_URL_TOKEN = re.compile(r"https?://\S+|data:image/\w+;base64,\S+")

def medicine_b2(text: str) -> str:
    """Remove HTML/XML tags; keep surrounding text. (Automatic medicine; URL strip is helper-only.)"""
    return _HTML_TAG_RE.sub("", text or "")

def _strip_b2_urls(text: str) -> str:
    """Optional selective fix: blank URL tokens (review before mass use). Not automatic medicine."""
    return _URL_TOKEN.sub("", text or "")
```

3. **Action:** **fix** — remove tags with `medicine_b2`; for embedded share/chrome URLs, remove the URL token after human confirm (or label-only if the URL sits inside usable prose). Keep the document. **Drop** only if the body is mostly markup/Base64 with almost no remaining Hindi sentences.

4. **Harm test:** Data B gold `ind-hi-fw2_gold.csv` (**234** docs, post-#161). Tool: `harm_test_indic.py --rule B2` (2026-10-31). Ran **`medicine_b2` (tag strip only)**:
   - gold docs **changed**: **0** of 234 (0.00%)
   - gold docs **dropped**: **0** of 234 (0.00%)
   - ZWJ/ZWNJ + NFC audits: **ok** — **PASS**
   Note: `_strip_b2_urls` is helper-only (not automatic). Pack side-effect: B2 on **9/500** labeled rows (fix).

5. **Side effects:** Tag strip can leave empty lines or broken spacing where a tag was the only content on a line; URL labeling can over-flag citation links inside good journalism. Never treat Indic ZWJ/ZWNJ as markup.

## Below threshold (no medicine section yet)

As of 500-row snapshot: **C2**=4, **F1**=3, **C5**=2, **F3**=1, **A6**=1, **G1**=1. Add a section only if a code later exceeds five in `labels.csv`.
