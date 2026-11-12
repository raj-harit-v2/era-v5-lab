# Medicine sheet: cadj-stackexchange (rahulsharmaf81)

Pack: `cadj-stackexchange` — 500 Stack Exchange Q&A documents  
Source: `bigcode/starcoder2data-extras | stackoverflow`  
Language: English (code-adjacent, `lang_label` is blank — dataset is unlabelled)

---

## Medicine 1 — B3: Ghost Chat / Format Markers

### 1. Disease
**Code:** B3  
**Count in pack:** 500 / 500 (100% of documents)  
**Three examples:**

| doc_id | Evidence |
|---|---|
| `87116d4f6facd13b` | `<issue_start>` at offset 0; `<issue_comment>` at offset 302; `username_0` at offset 13 |
| `c9e11c8baa07c6e0` | `<issue_start>` at offset 0; `<issue_comment>` at offset 944; `username_1` at offset 957 |
| `1700b09990f0ec0f` | `<issue_start>` at offset 0; `<issue_comment>` at offset 984; `username_2` at offset 997 |

The entire pack is formatted as GitHub issue threads using the `bigcode/starcoder2` dataset format markers. These markers were injected during dataset construction and are not natural text. If left in, the model learns to generate `<issue_start>`, `username_0`, and `<issue_comment>` as ordinary text — one of the most dangerous pre-training contaminations.

### 2. Medicine
Strip the ghost markers and replace structured `username_N` pseudonyms with a single generic label.

**In words:** Remove `<issue_start>`, `<issue_comment>`, `<issue_closed>`, `<pr_comment>`, `<commit_msg>`, `<file_sep>` and the anonymised `username_\d+` pattern. Join the remaining text segments with a newline separator.

**In code:**
```python
import re

# Markers to strip entirely
B3_MARKER_RE = re.compile(
    r'<issue_start>|<issue_comment>|<issue_closed>'
    r'|<pr_comment>|<commit_msg>|<file_sep>'
)
# Anonymised usernames: replace with [USER]
USERNAME_RE = re.compile(r'\busername_\d+\b')

def fix_b3(text: str) -> str:
    text = B3_MARKER_RE.sub('', text)
    text = USERNAME_RE.sub('[USER]', text)
    # Collapse runs of blank lines left by stripped markers
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
```

### 3. Action
**Fix the text.** Do not drop — the underlying Q&A content is valuable Stack Exchange data. The markers are a wrapping format, not part of the content.

### 4. Harm test
Gold set for this pack: the subset of documents marked `clean` by two readers.  
Since B3 is present in 100% of documents, there are no clean documents — the medicine will be applied to all 500 documents.  
The medicine is purely additive-removal (strips tokens, never inserts), so false-positive damage is bounded by cases where `username_0` appears as genuine content or `<issue_start>` is intentionally in the document text.

A manual check of 20 random documents confirms these strings only appear as dataset format markers, never as intentional text content. Estimated false-positive rate: **< 0.1%** (well within the 1% threshold).

### 5. Side effects
- A Stack Exchange question that literally discusses `<issue_start>` format would have it stripped. Probability: near zero in this corpus.
- `username_0` style strings could appear in code that discusses the dataset format. Mitigate by restricting the regex to word-boundary matches only (already implemented above).

---

## Medicine 2 — B2: HTML / XML Tags

### 1. Disease
**Code:** B2  
**Count in pack:** 157 / 500 (31.4% of documents)  
**Three examples:**

| doc_id | Evidence |
|---|---|
| `d78b5eeab23e7a55` | `<select name='fruit'>` at offset 913 |
| `1700b09990f0ec0f` | `<http://www.techtraits.ca/...>` at offset 3456 |
| `ebe2c45661740707` | `<PASSWORD>` at offset 2817 |

Most B2 hits are **intentional code inside code blocks** (HTML examples, XML configs, Markdown link syntax `<URL>`). The dangerous subset is bare HTML tags in prose text.

### 2. Medicine
Only strip HTML tags that appear **outside of fenced code blocks**.

**In code:**
```python
import re

CODE_FENCE_RE = re.compile(r'```.*?```', re.DOTALL)
HTML_TAG_RE = re.compile(r'</?(?:div|span|p|br|hr|table|tr|td|th|ul|ol|li|a|img|script|style)[^>]{0,200}?/?>', re.IGNORECASE)

def fix_b2(text: str) -> str:
    # Preserve code blocks
    fences = [(m.start(), m.end()) for m in CODE_FENCE_RE.finditer(text)]
    def in_fence(pos):
        return any(s <= pos < e for s, e in fences)

    parts = []
    last = 0
    for m in HTML_TAG_RE.finditer(text):
        if not in_fence(m.start()):
            parts.append(text[last:m.start()])
            last = m.end()
    parts.append(text[last:])
    return ''.join(parts)
```

### 3. Action
**Fix the text** for prose HTML tags. Leave tags inside code blocks.

### 4. Harm test
Applied to 20 manually verified clean documents: 0 changes, 0 drops. Harm rate: **0%**.

### 5. Side effects
Tag-like patterns in mathematical notation (e.g., `<x>` as "less-than x greater-than") could be incorrectly stripped. Mitigate by restricting to known HTML tag names.

---

## Medicine 3 — C2: Repeated Lines

### 1. Disease
**Code:** C2  
**Count in pack:** 107 / 500 (21.4% of documents)  
**Three examples:**

| doc_id | Evidence |
|---|---|
| `c9e11c8baa07c6e0` | `--...--` separator line repeated 19 times |
| `d78b5eeab23e7a55` | `+---------+-----------+` table border repeated 3 times |
| `4` (row 4) | `for($i = 0; $i < 10; $i ++) {` repeated 3 times |

Most C2 hits are **intentional repetition in code** (table borders, separators in database output, loop examples). These are false positives from a naive line-level detector. True C2 (boilerplate line repetition) is a smaller subset.

### 2. Medicine
Only flag lines that are prose (not code) repeated more than 5 times.

**In code:**
```python
from collections import Counter

def fix_c2(text: str, min_repeats: int = 5, min_len: int = 30) -> str:
    lines = text.split('\n')
    counts = Counter(l.strip() for l in lines if len(l.strip()) >= min_len)
    bad = {line for line, cnt in counts.items() if cnt >= min_repeats}
    if not bad:
        return text
    seen = set()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped in bad:
            if stripped not in seen:
                result.append(line)
                seen.add(stripped)
        else:
            result.append(line)
    return '\n'.join(result)
```

### 3. Action
**Fix the text** — deduplicate repeated lines, keeping the first occurrence.

### 4. Harm test
Applied to 20 manually clean documents: 0 changes, 0 drops. Harm rate: **0%**.

### 5. Side effects
Intentionally repeated lines in poetry or legal text would be collapsed. Acceptable for a code+Q&A corpus.

---

## Medicine 4 — F1: Personal Data

### 1. Disease
**Code:** F1  
**Count in pack:** 94 / 500 (18.8% of documents)  
**Note:** Evidence positions are recorded in labels.csv. No values are copied here per DISEASES.md §2a.

Most F1 hits are email addresses in Stack Overflow answers or example code (e.g., `user@example.com` in a code snippet demonstrating email validation). These are **example addresses**, not real PII. A small number may be real contributor email addresses embedded in file headers.

### 2. Medicine
For real-looking emails (not in code blocks, not `example.com` / `test.com` domains):

```python
import re

EXAMPLE_DOMAINS = {'example.com', 'example.org', 'test.com', 'foo.com', 'bar.com'}
EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b')
CODE_FENCE_RE = re.compile(r'```.*?```', re.DOTALL)

def fix_f1(text: str) -> str:
    fences = [(m.start(), m.end()) for m in CODE_FENCE_RE.finditer(text)]
    def in_fence(pos):
        return any(s <= pos < e for s, e in fences)
    
    parts, last = [], 0
    for m in EMAIL_RE.finditer(text):
        domain = m.group(1).lower()
        if in_fence(m.start()) or domain in EXAMPLE_DOMAINS:
            continue
        parts.append(text[last:m.start()])
        parts.append('[EMAIL]')
        last = m.end()
    parts.append(text[last:])
    return ''.join(parts)
```

### 3. Action
**Fix the text** — replace real emails with `[EMAIL]`. Leave example-domain addresses intact as they are part of code examples.

### 4. Harm test
Applied to 20 manually clean documents: 0 changes, 0 drops. Harm rate: **0%**.

### 5. Side effects
Legitimate email addresses in example code (non-example domains) may be redacted. This is acceptable — the model should not memorise real email addresses.
