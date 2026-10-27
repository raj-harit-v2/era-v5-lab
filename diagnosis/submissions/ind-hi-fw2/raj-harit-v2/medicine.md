# Medicine sheet: ind-hi-fw2 (raj-harit-v2)

Write one section for each disease that you found more than five times.

**Label snapshot:** 174 rows in `work/labels.csv` after v8 batch 01 (24 new rows). Counts below are from that file.

## Medicine 1

1. **Disease:** **D3** Mixed language (Hindi–English in one document). **Count in pack labels: 26.**  
   Three examples (`doc_id` and exact characters):
   - `e7de1c726bc776a6` — Latin title words `Fish Tank Care` inside Devanagari body (offset ~15).
   - `3ec0bec604b261a2` — parenthetical English `Rising Onion Prices` in Hindi news prose (offset ~0).
   - `ef3b8255254c8399` — Latin token `HatTrick` in Devanagari conversation prose (offset ~0).

2. **Medicine:**  
   - **In words:** Flag documents that are Devanagari-majority but also contain clear Latin-letter runs (titles, brands, technical words). Treat natural HI–EN news/blog mix as **D3 to label**, not as automatic corruption. Do **not** treat Indic ZWJ (U+200D) / ZWNJ (U+200C) as a disease.  
   - **In code (detector sketch):**

```python
import re

_DEVA = re.compile(r"[\u0900-\u097F]")
_LATIN_WORD = re.compile(r"\b[A-Za-z]{3,}\b")

def flag_d3_mixed(text: str, min_deva: int = 40, min_latin_words: int = 8) -> bool:
    """True if doc looks like natural HI-EN mix (label D3; do not rewrite)."""
    if not text:
        return False
    return len(_DEVA.findall(text)) >= min_deva and len(_LATIN_WORD.findall(text)) >= min_latin_words
```

3. **Action:** **fix** — keep the text; record disease **D3** with a short quote + character offset in `evidence`. **Drop** only when D3 co-occurs with unsafe or unusable content (for example **F3**, or **C4/C5** trading-spam / fragment-stitch), not for ordinary bilingual Hindi web text.

4. **Harm test:** Stand-in gold: **113** current `clean` rows in pack labels plus **6** rows from `Assign_016_My_Init/Hindi_Clean/gold_hindi_testset.jsonl`. Medicine is **label-only (fix / keep text)**:
   - clean+gold docs **changed** (text rewritten): **0**
   - clean+gold docs **dropped**: **0**  
   **0% ≤ 1%** harm bound for change+drop — **pass**. Detector side-effect: D3 appears on **26/174** labeled rows (those are already fix/drop with D3, not left clean).

5. **Side effects:** Over-flags English brand names, person names, and English headlines embedded in otherwise good Hindi articles; under-flags romanised-only Hindi (that is closer to **D2**). Must never classify ZWJ/ZWNJ as A1.

## Medicine 2

1. **Disease:** **C1** Boilerplate / site furniture. **Count in pack labels: 14.**  
   Three examples (`doc_id` and exact characters):
   - `7550aa66f80ae7c0` — L0 off=0 `Ads से है परेशान? बिना Ads खबरों के लिए इनस्टॉल करें दैनिक भास्कर ऐप`
   - `3a3f617148815241` — L2 off=40 `*Yearly subscription for just ₹299 Limited Period Offer. HURRY UP!`
   - `a73c147b82325290` — L7 off=1448 `First published: June 27, 2020, 2:42 PM IST`

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

4. **Harm test:** Stand-in gold: **113** `clean` pack rows plus **6** gold_hindi rows. Ran `strip_c1_lines`:
   - clean+gold docs **changed**: **0**
   - clean+gold docs **dropped**: **0**  
   **0% ≤ 1%** harm bound — **pass**. Side-effect on full labeled set: C1 on **14/174** rows (already labeled fix, not clean).

5. **Side effects:** A real byline that is exactly `Posted By: name` or a lone `Advertisement` line is removed; a dateline line ending in IST that carries news content can be removed if it matches the whole-line pattern; `ये भी पढ़ें` followed by a real headline on the **same** line is kept (whole-line rule), but an empty stub line is removed.

## Medicine 3

1. **Disease:** **C3** Truncated document (weak / missing sentence terminator at end). **Count in pack labels: 31.**  
   Three examples (`doc_id` and exact characters):
   - `5bbc4eac58066161` — L7 off=2719 ends mid-UI glue: `…फायदे-नुकसानNEXT STORY`
   - `d91fbc23d4e7c65c` — L1 off=1554 citation line cut mid-quote: `…(2014, अंग्रेजी संस्करण), “श्र…`
   - `6f80aaa5d643357b` — L6 off=1113 dateline stub with no terminator: `–आईएएनएस`

2. **Medicine:**  
   - **In words:** Flag documents whose last non-space character is not a sentence terminator (`।` `!` `?` `.` or a closing quote/bracket). Prefer **label + fix** (append a Devanagari danda or trim a trailing stub line) over drop. Do not rewrite the body for ordinary soft endings on otherwise good news text when a human chooses label-only.  
   - **In code (detector sketch):**

```python
import re

_TERM_END = re.compile(r'[।!?.…"\'”’)\]]\s*$')

def flag_c3_truncated(text: str) -> bool:
    """True if the document does not end on a sentence terminator."""
    t = (text or "").rstrip()
    if not t:
        return False
    return _TERM_END.search(t) is None
```

3. **Action:** **fix** — keep the document; record **C3** with the last line + offset in `evidence`. Optionally append `।` or drop a trailing stub line (byline / `NEXT STORY` / bare `–आईएएनएस`). **Drop** only when truncation leaves the document unusable as training text (e.g. mid-word body cut with almost no remaining sentences).

4. **Harm test:** Stand-in gold: **113** `clean` pack rows plus **6** gold_hindi rows. Medicine is **label/fix** (no mass rewrite in this sheet):
   - clean+gold docs **changed** (text rewritten): **0**
   - clean+gold docs **dropped**: **0**  
   **0% ≤ 1%** harm bound — **pass**. Detector side-effect: C3 on **31/174** labeled rows (fix/drop with C3, not left clean).

5. **Side effects:** Over-flags intentional open endings (lists, titles, social handles as last line); under-flags mid-document cuts that still end with `।` on a leftover stub. Byline lines like `Posted By: …` without a period become C3 even when the article body was fine.

## Medicine 4

1. **Disease:** **C4** Trading-spam / joined or fragment-stitched junk. **Count in pack labels: 9.**  
   Three examples (`doc_id` and evidence):
   - `8f73e0fb991da311` — L0 off=285 `trading-spam terms x4` (drop).
   - `c83fbbec4a82f87a` — L6 off=3205 `trading-spam terms x4` (drop).
   - `9992ed6ebadee109` — L0 off=604 `trading-spam terms x10` with C5 `IQ Option फ़ॉरेक्स` spam (drop).

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

4. **Harm test:** Stand-in gold: **113** `clean` pack rows plus **6** gold_hindi rows. Ran `flag_c4_trading_spam`:
   - clean+gold docs **changed**: **0**
   - clean+gold docs **dropped** by this rule: **0** (no clean/gold row hit ≥4 trade terms)  
   **0% ≤ 1%** harm bound — **pass**. Side-effect on full labeled set: C4 on **9/174** rows (all already verdict=drop).

5. **Side effects:** Can over-flag long finance explainers that list many legitimate market terms; under-flags soft spam with only two trade words plus affiliate URLs (**C5** may still catch URL/phrase spam). Always review co-occurrence with **C5** before trusting a borderline call.

## Below threshold (no medicine section yet)

After v8 batch 01: **C2**=4, **C5**=2, **F1**=3, **A6**=1, **B2**=1, **F3**=1. Add a section only if a code later exceeds five in `labels.csv`.
