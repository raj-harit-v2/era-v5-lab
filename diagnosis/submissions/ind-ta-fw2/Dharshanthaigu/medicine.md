# Medicine sheet: ind-ta-fw2 (Dharshanthaigu)

Pack: fineweb-2, tam_Taml, 500 documents (1,452,201 characters). Counts are from `labels.csv`: clean 242 (38 of them carry D3 only), fix 245, drop 13. Every document was scanned by code, word by word. The first reader (Dharshanthaigu) read the 287 documents that were marked clean in week 1 in full, one by one; those rows are `read=full`. The other 213 rows were not re-read and stay `read=partial`. Gold needs the second reader's full read of the same documents. The D4 calls were not checked by a native Tamil reader.

**Harm tests.** `ind-ta-fw2` has no gold file yet: gold set empty, not testable. No harm test was run and none passed. The "Proxy" lines give the share of this pack that a rule changes or drops, for information only; they are not harm tests. Re-run on the gold file when it exists (the gold of `ind-ta-sangraha-v` is not used).

## Medicine 1

1. **Disease:** C1 boilerplate, 149 documents. Examples: `cb5361ef4ea1c696`; `a6207a923fd8ca22`; `568bd0de84bbbe5b`.
2. **Medicine:** delete (a) lines under 150 characters that occur in 4 or more documents, (b) lines matching `C1_RE=re.compile(r'Share on|Sign up to receive|Related posts|Next Story|t\.me/|டெலிகிராம்|காலவரிசையைப் பகிரவும்|Copy and paste this code|cannot reply to topics|Advertisement|மேலும் படிக்க\.\.|இதையும் (பாருங்க|படிங்க|படியுங்கள்)')`, (c) the line that starts at each `C1:` offset in `labels.csv` (credit lines, timestamps, related headlines, contact footers). The regex reaches only about 35 of the 115 documents, so rule (c) is what makes the result reproducible.
```python
import re
from collections import Counter
def c1_fix(t, line_counts, c1_offsets=()):
    """Medicine 1: delete boilerplate lines. line_counts = Counter of short lines over the pack."""
    C1_RE = re.compile(r'Share on|Sign up to receive|Related posts|Next Story|t\.me/|டெலிகிராம்|காலவரிசையைப் பகிரவும்|Copy and paste this code|cannot reply to topics|Advertisement|மேலும் படிக்க\.\.|இதையும் (பாருங்க|படிங்க|படியுங்கள்)')
    lines, out, pos = t.split('\n'), [], 0
    for ln in lines:
        s = ln.strip()
        by_offset = any(pos <= o < pos + len(ln) + 1 for o in c1_offsets)
        if not ((s and len(s) < 150 and line_counts[s] >= 4) or C1_RE.search(ln) or by_offset):
            out.append(ln)
        pos += len(ln) + 1
    return '\n'.join(out)
```
3. **Action:** fix the text (delete the lines).
4. **Harm test:** gold set empty, not testable. Proxy (information only) on this pack: recomputed with the rules as written: the rules as written edit 151 documents and delete 10,568 characters (0.73%), drops 0 documents for C1; 149 documents are labelled C1, so the code and the labels do not match one to one (check the difference on the gold re-run).
5. **Side effects:** a news line that really mentions Telegram or Facebook is deleted; `மேலும் படிக்க..` followed by a headline is a link, not news text; unrelated headline lines inside a body have no pattern and are found only by rule (c).

## Medicine 2

1. **Disease:** G1 damaged Tamil letter sequences, 22 documents (290 damaged signs). Examples: `d63996e2a9a8b732`; `4f80863664c176ca`; `48dd3be00c5aab82`.
2. **Medicine:** a legacy-text bug turned `ர` into `ா` and `ூ` into `ுா`, and left `ெ ே ை` before the consonant. Apply in order, then NFC:
```python
import re, unicodedata
def g1fix(t):
    t=t.replace('ா்','ர்').replace('ோ்','ேர்').replace('ொ்','ெர்')
    for a,b in [('ாி','ரி'),('ாீ','ரீ'),('ாு','ரு'),('ாூ','ரூ'),('ுா','ூ')]: t=t.replace(a,b)
    t=re.sub('ௌ(?=[\u0bbf\u0bc0])','ெள',t)
    t=re.sub('([\u0bbf\u0bc0\u0bc1\u0bc2\u0bc8])்',r'\1',t)
    t=re.sub(r'(?<![\u0b95-\u0bb9])([\u0bc6\u0bc7\u0bc8])([\u0b95-\u0bb9])',r'\2\1',t)
    return unicodedata.normalize('NFC',t)
```
Detection: `(?<![\u0b95-\u0bb9])[\u0bbe-\u0bcd\u0bd7]` (a vowel sign or virama not preceded by a consonant), except `ெ/ே` followed by `ா/ௗ`. It finds all 22 documents and no other.
3. **Action:** fix the text. No G1 document is dropped, because the rules leave 0 of the 290 damaged signs (the old two-step rule left 25 in 16 documents).
4. **Harm test:** gold set empty, not testable. Proxy (information only): changes 22 of 500 documents (4.4%), 238 characters edited (0.016%, measured with a character diff), drops 0. The earlier 1.23% figure compared strings position by position and is withdrawn.
5. **Side effects:** not checked against a Tamil dictionary; step 6 can mis-order a vowel sign in rare consonant clusters; a legitimate word that happens to match steps 2 or 3 would be changed (no such case was found outside the 22 documents).

Four documents with a word split by a space or letter-spaced letters are labelled `fix` with G1 (one offset each in `labels.csv`); no automatic rule repairs them, they need a manual join.

## Medicine 3

1. **Disease:** C3 truncated document, 37 documents. Examples: `c231d36f72281264`; `aebffbe78a715708`; `5562334dc209bf2e`.
2. **Medicine:** `flag = len(last)>40 and not last.endswith(tuple('.?!"\'”’)]।:;…'))` on the last non-empty line. Most flags are boilerplate tails (embed text, tag lists, promos); only a few are real mid-word cuts. No `clean` document triggers it.
```python
import re
from collections import Counter
def c3_fix(t):
    """Medicine 3: delete the last non-empty line if it looks cut off."""
    lines = t.split('\n')
    idx = [i for i, x in enumerate(lines) if x.strip()]
    if not idx: return t
    last = lines[idx[-1]]
    if len(last) > 40 and not last.endswith(tuple('.?!"\'”’)]।:;…')):
        del lines[idx[-1]]
    return '\n'.join(lines)
```
3. **Action:** fix = delete the last line. One document (`86a594a2`) is `drop`, for A6, not for C3. Do not use C3 as a drop rule.
4. **Harm test:** gold set empty, not testable. Proxy (information only): changes 37 of 500 documents (7.4%, fails 1% as a drop rule), 7,956 characters (0.55%).
5. **Side effects:** a real last sentence without a full stop (headlines, quotes without punctuation) is deleted.

## Medicine 4

1. **Disease:** D4 bad machine translation and spam, 22 documents. Examples: `054cb6cead3ddfb3`; `54ae0344bd23097f`; `0f77ea53fd801c91`.
2. **Medicine:** `top=Counter(re.findall(r'\b[A-Za-z]{4,}\b',t)).most_common(1)[0]; flag = top[1]>=8 and len(t)<20000` finds brand-stuffed spam. Machine translation without spam (word order from English, auto-translated sites) was found by reading only.
```python
import re
from collections import Counter
def d4_flag(t):
    """Medicine 4: flag brand-stuffed spam (machine translation is found by reading only)."""
    words = re.findall(r'\b[A-Za-z]{4,}\b', t)
    return bool(words) and Counter(words).most_common(1)[0][1] >= 8 and len(t) < 20000
```
3. **Action:** drop the 7 spam or machine-translated documents (`054cb6`, `54ae03`, `c92e79`, `655882`, `e3d686`, `128625`, `5bd09956`). The other 14 are `fix` rows meaning "send to a Tamil reader"; they receive no automatic edit.
4. **Harm test:** gold set empty, not testable. Proxy (information only): the code flags 12 documents; 22 are labelled D4 (the rest were found by reading only); drops 7 documents (1.4%).
5. **Side effects:** news with repeated names or dates triggers the code (one false hit was removed); `Google` x10 in `1f696c02148459c7` may be a false hit; the reading-only calls were not checked by a native reader.

## Medicine 5

1. **Disease:** C5 keyword and link lists, 19 documents. Examples: `054cb6cead3ddfb3`; `c9590b0e18378df3`; `54ae0344bd23097f`.
2. **Medicine:** flag documents with 3 or more URLs, or the phrase "in Tamil" 2 or more times, or one Latin brand repeated 8 or more times.
```python
import re
from collections import Counter
def c5_flag(t):
    """Medicine 5: flag keyword and link lists."""
    words = re.findall(r'\b[A-Za-z]{4,}\b', t)
    top = Counter(words).most_common(1)[0][1] if words else 0
    return len(re.findall(r'https?://|www\.', t)) >= 3 or t.count('in Tamil') >= 2 or top >= 8
```
3. **Action:** drop if the document is mainly such a list (7 of the 19 are drop in `labels.csv`); otherwise strip the tail from the `C5:` offset.
4. **Harm test:** gold set empty, not testable. Proxy (information only): the code flags 15 of the 19 labelled documents (3.0%).
5. **Side effects:** a real article that quotes several links, or a recipe site that repeats a brand name, is flagged.

## Medicine 6

1. **Disease:** D3 mixed language, 47 documents. Examples: `264798d24ec2bd8a`; `05c9a6ea438df166`; `f8b030fd03e1a987`.
2. **Medicine:** delete lines of at least 8 characters in which more than 50% of the letters are Latin: `sum(c.isascii() and c.isalpha() for c in x)/len(x.strip())>0.5`. Keep the Tamil body.
```python
import re
from collections import Counter
def d3_fix(t):
    """Medicine 6: delete lines of 8+ characters that are mostly Latin letters."""
    keep = []
    for x in t.split('\n'):
        s = x.strip()
        if len(s) >= 8 and sum(c.isascii() and c.isalpha() for c in x) / len(s) > 0.5: continue
        keep.append(x)
    return '\n'.join(keep)
```
3. **Action:** fix the text. Rule from TSAI (31 Oct): a document whose only problem is mixed English stays `clean` with `D3`. 7 documents are now `clean` with D3 only; the other D3 documents also have another disease and stay `fix`. One D3-only candidate is an English-only document and stays `fix` until a full read decides drop.
4. **Harm test:** gold set empty, not testable. Proxy (information only): the function as written changes 102 documents (20.4%) and 10,295 characters (0.71%), drops 0. Only 47 documents are labelled D3, so the 50% Latin line rule is too broad and needs a tighter threshold before use.
5. **Side effects:** a Tamil document that quotes an English sentence in full loses that sentence.

## Medicine 7

1. **Disease:** C2 repeated lines, 17 documents. Examples: `1764f27a3eea3f9f`; `a30ed1434333cc5c`; `22f92acc659c4d2e`.
2. **Medicine:** for lines of more than 25 characters, delete every copy after the first inside the same document.
```python
import re
from collections import Counter
def c2_fix(t):
    """Medicine 7: delete every later copy of a line longer than 25 characters."""
    seen, out = set(), []
    for x in t.split('\n'):
        s = x.strip()
        if len(s) > 25:
            if s in seen: continue
            seen.add(s)
        out.append(x)
    return '\n'.join(out)
```
3. **Action:** fix the text.
4. **Harm test:** gold set empty, not testable. Proxy (information only): the function changes 19 documents and 2,004 characters (0.14%), drops 0; 17 documents are labelled C2.
5. **Side effects:** a refrain that is repeated on purpose (song or poem lines) loses its repeats.

## Medicine 8

1. **Disease:** A6 wrong or mixed script, 11 documents. Examples: `c9590b0e18378df3`; `24d1f3221d4b6703`; `315294ec820a9d4e`.
2. **Medicine:** `drop = len(re.findall(r'[\u0b80-\u0bff][A-Za-z]|[A-Za-z][\u0b80-\u0bff]',t))>=5 or len(FOREIGN.findall(t))>=5`, where `FOREIGN` matches Devanagari and other non-Tamil scripts.
```python
import re
from collections import Counter
def a6_drop(t):
    """Medicine 8: drop when Tamil and Latin letters are glued together 5+ times, or other scripts appear 5+ times."""
    FOREIGN = re.compile(r'[\u0900-\u097f\u0980-\u09ff\u0a00-\u0aff\u0c00-\u0c7f\u0c80-\u0cff\u0d00-\u0d7f]')
    glue = len(re.findall(r'[\u0b80-\u0bff][A-Za-z]|[A-Za-z][\u0b80-\u0bff]', t))
    return glue >= 5 or len(FOREIGN.findall(t)) >= 5
```
3. **Action:** drop where the rule fires (4 documents); fix the other 7 (a single Latin letter inside a Tamil word) by deleting the stray letter and checking the word.
4. **Harm test:** gold set empty, not testable. Proxy (information only): flags 11 of 500 documents (2.2%); drops 4 documents (0.8%).
5. **Side effects:** a Tamil sentence that legitimately glues an English acronym to a Tamil suffix reaches the threshold only if it happens 5 times.

## Medicine 9

1. **Disease:** F1 phone numbers and e-mail addresses, 6 documents (type and offset only in `labels.csv`; no value is stored in this repository).
2. **Medicine:** find the spans and report type and offset; the span is then deleted by hand after reading.
```python
import re
def f1_find(t):
    """Medicine 9: return (type, offset) for e-mails and phone numbers. Values are never stored."""
    hits = [('email', m.start()) for m in re.finditer(r'[\w.+-]+@[\w-]+\.[\w.-]+', t)]
    for m in re.finditer(r'(?<!\d)(?:\+?\d[\d\s\-]{8,}\d)(?!\d)', t):
        g = m.group(0)
        if re.fullmatch(r'\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}(\s+\d{1,2}(:\d{2})?)?', g.strip()): continue  # dates
        hits.append(('phone', m.start()))
    return sorted(hits, key=lambda h: h[1])
```
3. **Action:** fix the text (delete the span).
4. **Harm test:** gold set empty, not testable. Proxy (information only): the function finds a phone number or e-mail in 7 documents; 6 are labelled F1. One more document (`c6fc0fd5`) has a phone-like number that is not labelled F1: check it on the full read.
5. **Side effects:** long digit runs such as dates or IDs can look like phone numbers (dates are excluded).

## Other findings (five or fewer, no medicine)

D5 translated-sounding text, 2 documents, no rule. Word-split G1 (a word split by a space), 13 documents beyond the 22 legacy-encoding documents, repaired by hand only.

D2 romanised or English tail (5 documents, cut at the `D2:` offset), C4 joined documents (3), B2 `{youtube}` tags (1), F3 adult content (2, dropped), E3 secrets (0). Seen but not labelled as a disease and recorded in `note`: words split by a space (7 documents), a letter-spaced word (`d60ae580`), stray `;;;;` (`81726322`), Tamil-script digits (`b7266ade`, `e61c833d`). Do not apply NFKC to this data: 38 documents change under it, mostly because of `…`, and four contain `½ ℃ ℉ ″`.
