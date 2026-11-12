# Medicine sheet: cadj-commits (sureshmantha)

**Source:** `bigcode/commitpackft` · Code sample pack · 500 records.  
**Reviewed inputs:** my `suresh_lables.numbers`, colleague's `labels-pradeep.csv`, original Parquet, and `DISEASES.md`.  
**Purpose:** proposed rule designs for diseases occurring **more than five times**. No change has been applied to the raw pack.

## Disease inventory

| Code | Final labelled documents | Medicine required? |
|---|---:|---|
| F1 — personal data | 41 | Yes |
| E4 — repeated licence headers | 31 | Yes |
| A2 — control characters | 5 | No, count does not exceed five |
| A1 — invisible junk | 1 | No |
| E1 — generated code | 1 | No |

Counts are per document. Multiple codes on one document count independently. Names and contact values are deliberately absent from this public document.

## Medicine 1 — F1: Personal data

### 1. Disease and evidence

**Count:** 41 documents. Examples (type and exact zero-based code-point offsets only):

- `e0c1e30626b9b1ff` — email at offsets 518, 1092.
- `6454d40260da86f0` — email at offsets 480, 1019.
- `49b151d5092e2af4` — email at offsets 742, 1961.

The examples contain email-bearing metadata or personal names. Some source files are public code; an email or attribution must be reviewed in context before deciding it is private information. A source author listed in a legally required licence header must not be silently removed.

### 2. Medicine and rule

Use a **two-stage privacy process**. First, locate candidate emails/phones/addresses/identity metadata and assign an evidence-only offset. Second, redact confirmed private-person contact details only in a **separate training projection**; preserve the immutable raw file and an access-controlled reversible audit. Do not automatically remove `tests/`, synthetic fixtures, organizational support inboxes or mandatory attribution.

A deliberately conservative executable reference follows. The full tested script is also supplied in the accompanying private review bundle as `medicine_rules.py`.

```python
import re
EMAIL = re.compile(r"(?<![\w@])[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?![\w@])")
ATTRIBUTION_LINE = re.compile(r"(?im)^[ \t]*(?:Signed-off-by:|Co-authored-by:|Author:|Contact:|Maintainer:)\s*[^\n]*$")

def f1_privacy_training_view(text):
    def redact_line(match):
        return EMAIL.sub('[REDACTED_EMAIL]', match.group(0))
    return ATTRIBUTION_LINE.sub(redact_line, text)
```

**Important limitation:** This only automates clear identity-metadata cases; the remaining F1 candidates are **manual-review cases**, not proof that a broad regex can safely cleanse every record. In particular, names without emails must be considered individually.

### 3. Action

`fix` the approved **training view** by redacting only validated private contact spans. Do not drop an otherwise useful commit solely because of an email, and do not modify the source repository or legal licence information.

### 4. Harm test

**Official code-language gold-set path:** NOT PROVIDED.  
**Gold documents evaluated:** PENDING.  
**Gold documents changed:** PENDING.  
**Gold documents dropped:** PENDING.  
**Combined changed-or-dropped proportion:** PENDING.  
**Pass criterion:** `changed_or_dropped / total_gold <= 0.01`.

Run locally after obtaining the official clean Code gold set:

```bash
python gold_harm_check.py --gold /path/to/official_code_gold.jsonl --medicine F1
```

Do not report zero harm without the actual clean gold-set run. The review bundle provides the runnable harness and self-contained synthetic policy tests; synthetic tests are **not** official gold-set results.

### 5. Side effects and mitigations

Potentially removes legitimate author provenance, legal attribution, synthetic test fixtures, operational contact mailboxes or code strings needed for realistic tests. Use context, strict opt-in rules, documented exceptions, audit, and the clean gold set. If harm exceeds 1%, **reject or narrow the rule**, then rerun gold tests.

## Medicine 2 — E4: Repeated licence headers

### 1. Disease and evidence

**Count:** 31 documents. Examples with short exact non-personal licence fragments and offsets:

- `e08f880ce9aa8920` — 'Licensed under the Apache License, Version 2.0' at offsets 211, 1596.
- `97dcab67c73a7eaa` — 'Licensed under the Apache License, Version 2.0' at offsets 181, 1150.
- `a20a794c2c45c020` — 'Licensed under the Apache License, Version 2.0' at offsets 200, 1743.

The recurring copyright/licensing banners are especially visible in Java, C++, Go, and Rust commit examples. A generic copyright line is not automatically junk; here we flag recurring, recognisable boilerplate for review.

### 2. Medicine and rule

Extract a leading recognised licence-header span in each `### old contents` and `### new contents` section. For the **training projection only**, remove the duplicate copy **only when the header content is byte-identical in both sections**, while retaining its first occurrence and preserving licence metadata. Do not strip a unique banner, and do not alter the raw source data.

```python
def licence_header(section):
    lead = section.lstrip('\n')
    if lead.startswith('/*'):
        end = lead.find('*/')
        if end < 0:
            return ''
        header = lead[:end + 2]
    elif lead.startswith(('#', '//')):
        lines = lead.splitlines(keepends=True)
        kept = []
        for line in lines:
            if line.lstrip().startswith(('#', '//')) or (not line.strip() and kept):
                kept.append(line)
            else:
                break
        header = ''.join(kept).rstrip('\n')
    else:
        return ''
    if len(header) < 120 or not any(
        word in header.lower() for word in ('license', 'licence', 'copyright')
    ):
        return ''
    return header

def e4_training_view(text):
    before, sep, after = text.partition('### new contents\n')
    if not sep:
        return text
    old = before.partition('### old contents\n')[2]
    if not old:
        return text
    previous = licence_header(old)
    current = licence_header(after)
    if previous and previous == current:
        return before + sep + after.replace(current, '', 1)
    return text
```

### 3. Action

`fix` only the redundant second licence block in the training projection; **never drop the whole document** based on this code alone. Retain required notices and provenance. This is not legal advice about redistribution obligations.

### 4. Harm test

**Official code-language gold-set path:** NOT PROVIDED.  
**Gold documents evaluated:** PENDING.  
**Gold documents changed:** PENDING.  
**Gold documents dropped:** PENDING.  
**Combined changed-or-dropped proportion:** PENDING.  
**Pass criterion:** `changed_or_dropped / total_gold <= 0.01`.

```bash
python gold_harm_check.py --gold /path/to/official_code_gold.jsonl --medicine E4
```

### 5. Side effects and mitigations

Removing notices can break licensing or provenance requirements. A header that looks identical may have meaningful differences in copyright year, ownership, or legal wording. Compare exact bytes, preserve the raw and notices, support exception lists, and fail closed on uncertain boundaries. Do not run an indiscriminate licence-stripping regex over code.

## Tests and outstanding sign-off

The proposed medicine code is designed for **gold-set-first** validation, not execution on the 500-row pack. The official clean gold set is absent from the provided archive. This means the numerical 1% harm-test evidence is **pending**, even though the per-row diagnoses and the local synthetic tests can be verified.

Before public PR approval, confirm the six rows still marked `partial` and attach actual gold-set counts obtained from Data A/Data B.
