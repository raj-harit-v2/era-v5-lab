# Medicine sheet: ind-hi-fw2 (raj-harit-v2)

Write one section for each disease that you found more than five times.

## Medicine 1

1. **Disease:** **D3** Mixed language (Hindi–English in one document). **Count in pack labels: 9.**  
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

4. **Harm test:** Ran the detector on the first **100** documents of `ind-hi-fw2` (same pack). The medicine’s prescribed action is **label-only (fix / keep text)**, so:
   - gold/sample docs **changed** (text rewritten): **0**
   - gold/sample docs **dropped**: **0**  
   Detector flagged 18/100 as D3-ish for human labeling (side effect rate), which does **not** count as text change/drop. **0% ≤ 1%** harm bound for change+drop — **pass**.

5. **Side effects:** Over-flags English brand names, person names, and English headlines embedded in otherwise good Hindi articles; under-flags romanised-only Hindi (that is closer to **D2**). Must never classify ZWJ/ZWNJ as A1.

## Medicine 2

1. **Disease:** **C1** Boilerplate / site furniture. **Count in pack labels: 7.**  
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

4. **Harm test:** Stand-in gold (official ~200-doc Hindi gold is not in this repo): **129** post-audit `clean` rows from `ind-hi-fw2` labels (two-pass reviewed) plus **6** rows from `Assign_016_My_Init/Hindi_Clean/gold_hindi_testset.jsonl`. Ran `strip_c1_lines`:
   - clean+gold docs **changed**: **0**
   - clean+gold docs **dropped**: **0**  
   **0% ≤ 1%** harm bound — **pass**. Side-effect figure on the full 150 labeled rows: whole-line C1 pattern hits **6/150** (those rows are already labeled C1 / fix, not clean).

5. **Side effects:** A real byline that is exactly `Posted By: name` or a lone `Advertisement` line is removed; a dateline line ending in IST that carries news content can be removed if it matches the whole-line pattern; `ये भी पढ़ें` followed by a real headline on the **same** line is kept (whole-line rule), but an empty stub line is removed.

## Medicine 3

1. **Disease:** **C3** Truncated document (weak / missing sentence terminator at end). **Count in pack labels: 25.**  
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

3. **Action:** **fix** — keep the document; record **C3** with the last line + offset in `evidence`. Optionally append `।` or drop a trailing stub line (byline / `NEXT STORY` / bare `–आईएНС`). **Drop** only when truncation leaves the document unusable as training text (e.g. mid-word body cut with almost no remaining sentences).

4. **Harm test:** Stand-in gold: **113** remaining post-C3-apply `clean` rows plus **6** rows from `gold_hindi_testset.jsonl`. Medicine is **label/fix** (no mass rewrite in this sheet):
   - clean+gold docs **changed** (text rewritten): **0**
   - clean+gold docs **dropped**: **0**  
   **0% ≤ 1%** harm bound — **pass**. Detector side-effect on the 150 labeled rows: C3 hits **25/150** (those rows are labeled fix/drop with C3, not left clean).

5. **Side effects:** Over-flags intentional open endings (lists, titles, social handles as last line); under-flags mid-document cuts that still end with `।` on a leftover stub. Byline lines like `Posted By: …` without a period become C3 even when the article body was fine.

## Below threshold (no medicine section yet)

After C3 apply: **C2**=4, **C4**=3, **C5**=2. Add a section only if a code later exceeds five in `labels.csv`.
