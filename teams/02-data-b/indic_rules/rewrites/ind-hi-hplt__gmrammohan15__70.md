# Rewrite in the harm tool's format: ind-hi-hplt, gmrammohan15 (PR #70)

TSAI ruling 3 on #211 (3 Nov): the Data B rules owner may rewrite a medicine sheet that `harm_test_indic.py` cannot
read, and the author must OK the rewrite in their PR. **Author OK: pending.**

Source: `diagnosis/submissions/ind-hi-hplt/gmrammohan15/medicine.md` at `6691b93`. Each section below holds the author's code
unchanged; the description, examples and side effects stay in the author's sheet.

**Changes, all marked `# added by Data B` in the code.** The harm tool runs each section on its own, so a section can use only what it defines. In the author's sheet, the shared definitions sit once before the first section, some sections call functions defined in other sections, and two standard-library imports (`urlparse`, `Counter`) are used but never written. That stopped all 14 rules. Each section now starts with what it needs: the shared definitions, the missing imports, and the definitions it uses from other sections, all copied unchanged.

**Harm test:** run on today's gold set of this pack (`teams/02-data-b/gold/ind-hi-hplt_gold.csv`, 62 documents, main at `ea7b533`); the results are posted on the author's PR.

## Medicine 1: C1

1. **Disease:** C1. Description: see the author's sheet, section C1.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
```

```python
C1_PHRASES = [
    "यह भी पढ़ें", "ये भी पढ़ें", "इसे भी पढ़ें", "यह भी पढे", "ये भी पढे", "और पढ़ें", "आगे पढ़ें", "पूरा पढ़ें",
    "संबंधित खबर", "सम्बंधित खबर", "संबंधित लेख", "संबंधित पोस्ट", "लेटेस्ट खबर", "ताज़ा खबर", "ताजा खबर",
    "शेयर करें", "शेयर करे", "लाइक करें", "फॉलो करें", "सब्सक्राइब", "डाउनलोड करें", "हमसे जुड़ें", "हमें फॉलो",
    "कमेंट", "टिप्पणी करें", "प्रातिक्रिया दे", "प्रतिक्रिया दें", "अपनी राय", "जवाब दें", "रद्द करें",
    "सर्वाधिकार सुरक्षित", "सभी अधिकार सुरक्षित", "कॉपीराइट", "विज्ञापन", "गोपनीयता नीति", "अस्वीकरण", "संपर्क करें",
    "हमारे बारे में", "Share on", "WhatsApp", "Facebook", "Twitter", "Telegram", "Instagram", "YouTube", "Pinterest",
    "LinkedIn", "Read More", "Read more", "Click here", "Subscribe", "Follow us", "Advertisement", "Copyright", "©",
    "All Rights Reserved", "All rights reserved", "Privacy Policy", "Disclaimer", "Terms of", "Cookie", "cookies",
    "Tags:", "Tags :", "Posted in", "Filed under", "Leave a Reply", "Leave a Comment", "Comments", "Next Post",
    "Previous Post", "Related Posts", "Home »", "Home >", "Skip to content", "Menu"]
C1_RE = re.compile("|".join(map(re.escape, sorted(C1_PHRASES, key=len, reverse=True))))
SENTENCE_END = re.compile("[।॥!?,.]$")

def cure_c1(text, shared_lines):        # shared_lines: lines that also occur in 2+ other documents of the pack
    out, pos, n = [], 0, len(text)
    for line in text.split("\n"):
        nl = norm_line(line)
        shared = len(nl) >= 10 and nl in shared_lines and not SENTENCE_END.search(nl)   # repeated sentences are content
        phrase = bool(nl) and len(nl) <= 60 and bool(C1_RE.search(nl))
        if phrase and pos > 0.7 * n:
            break                           # boilerplate tail: cut everything after it
        if not (shared or phrase):
            out.append(line)
        pos += len(line) + 1
    return "\n".join(out).rstrip()
```

4. **Harm test:** see the results on PR #70.

## Medicine 2: D4

1. **Disease:** D4. Description: see the author's sheet, section D4.

```python
from urllib.parse import urlparse  # added by Data B: the author's code uses it, but the sheet never imports it
```

```python
SPAM_TERMS = ["विदेशी मुद्रा", "द्विआधारी विकल्प", "बाइनरी विकल्प", "बिटकॉइन", "पैसे कमा", "PAMM", "Forex",
              "forex", "binary option", "Bitcoin"]

def is_spam(text):           # only spam-specific terms: निवेश or ट्रेडिंग also occur in real business news
    hits = {t: text.count(t) for t in SPAM_TERMS if t in text}
    return sum(hits.values()) >= 4 and len(hits) >= 2

def cure_d4(text, url, mt_sites):   # mt_sites: sites with 2+ other reviewed D4 drops (healthcarestudies.in, ...)
    return None if urlparse(url).netloc in mt_sites or is_spam(text) else text
```

4. **Harm test:** see the results on PR #70.

## Medicine 3: D3

1. **Disease:** D3. Description: see the author's sheet, section D3.

```python
def cure_d3(text):
    return text
```

4. **Harm test:** see the results on PR #70.

## Medicine 4: A5

1. **Disease:** A5. Description: see the author's sheet, section A5.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
```

```python
A5_RULES = [
    (re.compile("र्इ"), "ई"),
    (re.compile("ध्द"), "द्ध"),                                # बौध्दिक -> बौद्धिक
    (re.compile("द्बारा"), "द्वारा"),
    (re.compile("\u093C\u093C+"), "\u093C"),                   # double nukta
    (re.compile(f"([डढ])([{MATRA}])\u093C"), "\\1\u093C\\2"),  # बडे़ -> बड़े
    (re.compile(f"([डढ])([कखगनलमतरसद])\u093C"), "\\1\u093C\\2"),  # सडक़ -> सड़क, लडऩे -> लड़ने
    (re.compile("\u093E\u0947"), "\u094B"),                    # ाे -> ो
    (re.compile("\u093E\u0948"), "\u094C"),                    # ाै -> ौ
    (re.compile(f"([{MATRA}])\\1"), "\\1"),                    # केे -> के
]

def fix_sha(word, lexicon):         # lexicon: Counter of word frequencies in clean Hindi text
    if "ष" not in word:
        return word
    best, best_n = word, lexicon[word]
    pos = [i for i, c in enumerate(word) if c == "ष"]
    for mask in range(1, 2 ** len(pos)):
        alt = "".join("श" if i in pos and mask >> pos.index(i) & 1 else c for i, c in enumerate(word))
        if lexicon[alt] > best_n:
            best, best_n = alt, lexicon[alt]
    return best if best_n >= 3 and best_n > 3 * lexicon[word] else word

def cure_a5(text, lexicon):
    for rx, rep in A5_RULES:
        text = rx.sub(rep, text)
    return WORD_RE.sub(lambda m: fix_sha(m.group(), lexicon), text)
```

4. **Harm test:** see the results on PR #70.

## Medicine 5: C4

1. **Disease:** C4. Description: see the author's sheet, section C4.

```python
# added by Data B: definitions this section uses from other sections of the sheet, copied unchanged
# from D4
SPAM_TERMS = ["विदेशी मुद्रा", "द्विआधारी विकल्प", "बाइनरी विकल्प", "बिटकॉइन", "पैसे कमा", "PAMM", "Forex",
              "forex", "binary option", "Bitcoin"]
# from D4
def is_spam(text):           # only spam-specific terms: निवेश or ट्रेडिंग also occur in real business news
    hits = {t: text.count(t) for t in SPAM_TERMS if t in text}
    return sum(hits.values()) >= 4 and len(hits) >= 2
# end of the copied definitions
```

```python
def cure_c4(text):
    return None if is_spam(text) else text
```

4. **Harm test:** see the results on PR #70.

## Medicine 6: G4

1. **Disease:** G4. Description: see the author's sheet, section G4.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
```

```python
G4_FAKE = re.compile(f"(?<=[{LETTER}\"'”’])\\s?(II|\\|\\||[Il|])"
                     f"(?=[ \\t]+[\u0904-\u0939\u0958-\u0961\"'“‘]|[ \\t]*\\n|[ \\t]*$)")

def cure_g4(text):
    def rep(m):
        start = max(text.rfind(ch, 0, m.start()) for ch in "।|\n")
        if m.start() - start - 1 < 25:
            return m.group()                       # short segment: a separator, not a sentence end
        return "॥" if len(m.group(1)) == 2 else "।"
    return G4_FAKE.sub(rep, text)
```

4. **Harm test:** see the results on PR #70.

## Medicine 7: D5

1. **Disease:** D5. Description: see the author's sheet, section D5.

```python
from urllib.parse import urlparse  # added by Data B: the author's code uses it, but the sheet never imports it
```

```python
def flag_d5(url, translated_sites):    # e.g. hi.godfootsteps.org, hi.easternlightning.org
    return urlparse(url).netloc in translated_sites
```

4. **Harm test:** see the results on PR #70.

## Medicine 8: F1

1. **Disease:** F1. Description: see the author's sheet, section F1.

```python
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<![\d])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?![\d])|\+\d{1,3}[\s-]?\d(?:[\s-]?\d){6,13}(?![\d])")
LANDLINE_RE = re.compile(r"(?<![\d])0\d{2,4}[\s-]\d{6,8}(?![\d])|(?<![\d])0\d{2,4}[\s-]\d{3,4}[\s-]\d{3,4}(?![\d])"
                         r"|\(\+?\d{1,5}\)\s?\d{3,8}[\s-]?\d{3,8}(?![\d])")
OTHER_PHONE_RE = re.compile(r"(?<![\d-])(?:\d{5}-\d{5}|\d{2} \d{2} \d{3} \d{4}|1800[ -]?\d{3}[ -]?\d{3,4})(?![\d])")
AADHAAR_RE = re.compile(r"(?<![\d])\d{4}\s\d{4}\s\d{4}(?![\d])")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
F1 = [("<EMAIL>", EMAIL_RE), ("<PHONE>", PHONE_RE), ("<LANDLINE>", LANDLINE_RE), ("<PHONE>", OTHER_PHONE_RE),
      ("<AADHAAR>", AADHAAR_RE), ("<PAN>", PAN_RE)]

def cure_f1(text):
    for tag, rx in F1:
        text = rx.sub(tag, text)
    return text
```

4. **Harm test:** see the results on PR #70.

## Medicine 9: A6

1. **Disease:** A6. Description: see the author's sheet, section A6.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
# added by Data B: definitions this section uses from other sections of the sheet, copied unchanged
# from G4
G4_FAKE = re.compile(f"(?<=[{LETTER}\"'”’])\\s?(II|\\|\\||[Il|])"
                     f"(?=[ \\t]+[\u0904-\u0939\u0958-\u0961\"'“‘]|[ \\t]*\\n|[ \\t]*$)")
# from G4
def cure_g4(text):
    def rep(m):
        start = max(text.rfind(ch, 0, m.start()) for ch in "।|\n")
        if m.start() - start - 1 < 25:
            return m.group()                       # short segment: a separator, not a sentence end
        return "॥" if len(m.group(1)) == 2 else "।"
    return G4_FAKE.sub(rep, text)
# end of the copied definitions
```

```python
A6_JOIN = re.compile(f"(?<=[{DEVA}])(?=[A-Za-z]{{2}})|(?<=[A-Za-z]{{2}})(?=[\u0904-\u0939\u0958-\u0961])")

def cure_a6(text):
    return A6_JOIN.sub(" ", cure_g4(text))
```

4. **Harm test:** see the results on PR #70.

## Medicine 10: C5

1. **Disease:** C5. Description: see the author's sheet, section C5.

```python
# added by Data B: definitions this section uses from other sections of the sheet, copied unchanged
# from D4
SPAM_TERMS = ["विदेशी मुद्रा", "द्विआधारी विकल्प", "बाइनरी विकल्प", "बिटकॉइन", "पैसे कमा", "PAMM", "Forex",
              "forex", "binary option", "Bitcoin"]
# from D4
def is_spam(text):           # only spam-specific terms: निवेश or ट्रेडिंग also occur in real business news
    hits = {t: text.count(t) for t in SPAM_TERMS if t in text}
    return sum(hits.values()) >= 4 and len(hits) >= 2
# end of the copied definitions
```

```python
TAG_OR_URL = re.compile(r"https?://\S+|www\.\S+|#[\w\u0900-\u097F]+")

def cure_c5(text):
    if is_spam(text):
        return None
    keep = [line for line in text.split("\n")
            if not ((tags := TAG_OR_URL.findall(line)) and len(tags) >= 3
                    and sum(map(len, tags)) >= 0.5 * len(line.strip()))]
    return "\n".join(keep)
```

4. **Harm test:** see the results on PR #70.

## Medicine 11: C2

1. **Disease:** C2. Description: see the author's sheet, section C2.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
from collections import Counter  # added by Data B: the author's code uses it, but the sheet never imports it
```

```python
def cure_c2(text):
    lines = text.split("\n")
    count = Counter(norm_line(line) for line in lines)
    seen, out = set(), []
    for line in lines:
        nl = norm_line(line)
        if nl in seen and (len(nl) >= 300 or (len(nl) >= 25 and count[nl] >= 3)):
            continue
        seen.add(nl)
        out.append(line)
    return "\n".join(out)
```

4. **Harm test:** see the results on PR #70.

## Medicine 12: C3

1. **Disease:** C3. Description: see the author's sheet, section C3.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
```

```python
TRUNC_END = re.compile(r"(\[…\]|\[\.\.\.\]|…|\.\.\.)\s*$")

def cure_c3(text):
    lines = [nl for nl in map(norm_line, text.split("\n")) if nl]
    cut = [nl for nl in lines if len(nl) >= 20 and TRUNC_END.search(nl)]
    return None if len(cut) >= 3 and len(cut) >= 0.3 * len(lines) else text
```

4. **Harm test:** see the results on PR #70.

## Medicine 13: D2

1. **Disease:** D2. Description: see the author's sheet, section D2.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
```

```python
ROMAN_HI = {"kya", "hai", "hain", "kaise", "kare", "karen", "karein", "ka", "ki", "ke", "se", "ko", "mein", "aur",
            "kab", "kyon", "kyun", "aaj", "nahi", "hota", "hoti", "hote", "wala", "wali", "kitna", "kaun", "apne",
            "apna", "liye", "sath", "ek", "bhi", "tak", "rashifal", "katha", "vrat"}  # no English look-alikes ('me', 'par')
LATIN_WORD = re.compile(r"[A-Za-z]+")

def cure_d2(text):
    out = []
    for line in text.split("\n"):
        words = [w.lower() for w in LATIN_WORD.findall(line)]
        hits = sum(w in ROMAN_HI for w in words)
        if not re.search(f"[{DEVA}]", line) and len(words) >= 3 and hits >= 1 and hits >= 0.25 * len(words):
            continue
        out.append(line)
    return "\n".join(out)
```

4. **Harm test:** see the results on PR #70.

## Medicine 14: G1

1. **Disease:** G1. Description: see the author's sheet, section G1.

```python
# added by Data B: the sheet's shared definitions, copied unchanged from its top, because the harm tool
# runs each section on its own
import re
DEVA, CONS, MATRA = "\u0900-\u097F", "\u0915-\u0939", "\u093E-\u094C"
LETTER = "\u0900-\u0963\u0966-\u097F"          # Devanagari letters and signs, without । and ॥
WORD_RE = re.compile(f"[{DEVA}]+")
norm_line = lambda line: re.sub(r"\s+", " ", line).strip()
# end of the shared definitions
```

```python
G1_SPLIT = re.compile(f"([{CONS}\u093C])\\s+([{MATRA}\u0901-\u0903])")
G1_ANUSVARA = re.compile(f"([{MATRA}])\\s+([\u0901\u0902])")
G1_HALANT = re.compile(f"([{CONS}]\u094D)\\s+(?=[{CONS}])")

def cure_g1(text):
    if len(G1_SPLIT.findall(text)) + len(G1_ANUSVARA.findall(text)) < 3:
        return text                                      # a single 'जगत् में' is correct Hindi
    text = G1_ANUSVARA.sub(lambda m: m.group(1) + m.group(2) + " ", text)   # 'मे ंगुजार' -> 'में गुजार'
    text = G1_SPLIT.sub(r"\1\2", text)
    text = re.sub("([\u0901\u0902]) (\\s)", r"\1\2", text)
    return G1_HALANT.sub(r"\1", text)
```

4. **Harm test:** see the results on PR #70.
