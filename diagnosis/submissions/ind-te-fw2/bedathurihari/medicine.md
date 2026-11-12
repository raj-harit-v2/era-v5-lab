# Medicine sheet: ind-te-fw2 (bedathurihari)

## Evidence level and limitations

The **complete text field of each of the 500 documents** was processed in an automated audit. A targeted context review corrected some false positives and uncovered two detached Indic vowel-sign candidates. **The document-level `read` field remains `partial` until a full fluent Telugu reading has been performed.** The results are not instructor-certified or a substitute for such reading.

**Official Telugu gold set: not supplied; harm tests NOT RUN.** Candidate rules have undergone a *limited in-pack dry run and targeted unit tests only*, not the required gold-set review. No medicine may be accepted on the evidence below alone.

## Candidate counts (500 documents; not certified disease prevalence)

| Code | Documents | Decision status |
|---|---:|---|
| B2 — HTML/markup residue | 5 | Candidate; requires manual confirmation |
| C1 — boilerplate/cross-links | 33 | Candidate; requires manual confirmation |
| C2 — repeated lines | 9 | Candidate; requires manual confirmation |
| D1 — possible wrong language label | 1 | Candidate; requires manual confirmation |
| D3 — mixed-language lines | 17 | Candidate; requires manual confirmation |
| F1 — possible private-person data | 5 | Candidate; requires manual confirmation |
| F3 — age-restricted material | 1 | Candidate; requires manual confirmation |
| G1 — separated Telugu vowel sign | 2 | Candidate; requires manual confirmation |
| H2 — near duplicate | 4 | Candidate; requires manual confirmation |

For medicine prioritization, the codes detected **more than five times** are C1, C2 and D3. F1 is included as an additional precaution even though the narrower, context-checked candidate count is five.

## C1 — Boilerplate and related links
**Candidate count:** 33 documents. **Proposed action:** fix only isolated navigational lines after confirmation, not entire articles.

**Three document examples:**
- `ab4df107c4d439c6` — Cross-link/boilerplate marker at offset 871: మరింత చదవండి
- `93e12eda26737171` — Cross-link/boilerplate marker at offset 1119: ఇవి కూడా చదవండి
- `142ddb551bbdbbd2` — Cross-link/boilerplate marker at offset 1578: ఇదీ చదవండి

**Medicine (candidate):**
```python
import re
RELATED = re.compile(r"(?im)^[ \t]*(?:[-•][ \t]*)?(?:Also[ \t]+Read|Read[ \t]+More|Read[ \t]+Also|ఇది కూడా చదవండి|ఇవి కూడా చదవండి|ఇదీ చదవండి|మరింత చదవండి)[ \t]*[:：.\-]*[^\n]*\n?")
def fix_c1(text: str) -> str:
    return RELATED.sub("", text)
```
**In-pack dry run (not gold):** changed 30 / 500, dropped 0. A broad related-link detector found 33 candidates, but the proposed line-removal rule is deliberately narrower.
**Side effects:** might remove genuine citations or related links with educational value; preserve full article context, and require confirmation that matches are navigation rather than quoted prose.
**Official gold-set harm test:** NOT RUN; changed/dropped/affected unknown. Reject if more than 1% of clean gold documents are affected.

## C2 — Repeated lines
**Candidate count:** 9. Repeated lines include deliberate chapter headings, repeated prose and redundant embeds; do NOT globally delete repeated text.

**Three document examples:**
- `6faa50209f00b4cf` — first at offset 1386
- `701668a26b4c5508` — first at offset 1843
- `f3afb012f3c52eb2` — first at offset 0

**Medicine (candidate):** only remove *subsequent instances* of a clearly identified embedded-widget marker within the same document. General headings are preserved.
```python
def fix_c2(text: str) -> str:
    marker = "View this post on Instagram"
    seen = False
    kept = []
    for line in text.splitlines(keepends=True):
        if line.strip() == marker:
            if seen:
                continue
            seen = True
        kept.append(line)
    return "".join(kept)
```
**In-pack dry run (not gold):** changed 2 / 500, dropped 0. Not all 9 candidate documents should be cleaned.
**Side effects:** repeated widget phrases can refer to different embeds; deleting them may lose document structure. The proposed cleaner is restricted to one recognized redundant marker. Other cases require manual review.
**Official gold-set harm test:** NOT RUN; changed/dropped/affected unknown. Reject if more than 1% of gold documents are affected.

## D3 — Mixed-language text
**Candidate count:** 17. The DISEASES guide explicitly says natural code-switching can occur and must be labelled rather than judged.

**Three document examples:**
- `fdb1b904679948c6` — English/Telugu mixed line at offset 164
- `da88f8127113b503` — English/Telugu mixed line at offset 7
- `499898c17a98e3ef` — English/Telugu mixed line at offset 5875

**Medicine:** preserve text (identity transform).
```python
def fix_d3(text: str) -> str:
    return text  # Intentional: preserve legitimate Telugu-English code switching.
```
**Action:** keep the document by default; do not drop solely because English occurs in Telugu text. Cases dominated by a different language should be separately reviewed for D1.
**Side effects:** retaining unrelated English boilerplate is possible; C1 should address confirmed navigation independently. No destructive normalization.
**Official gold-set harm test:** NOT RUN. The identity transform changes no text by construction, but instructor still requires gold-set evaluation of enabled medicines.

## F1 — Potential private-person contact information (optional safeguard)
**Candidate count after distinguishing public institution/helpline contacts:** 5. More than five was the initial broad scanner count, but public helplines and organizational support addresses were removed from F1. No private value is reproduced here.

**Three document examples (type + offset only):**
- `b6ddb1f2f2e4456f` — potential phone number at offset 2432
- `b84adcd535648e79` — potential phone number at offset 5462
- `ed4dc90ebfde2f56` — potential phone number at offset 8072

**Medicine:** queue candidate documents for privacy adjudication; redact or drop only when a reviewer determines the data identifies a private individual and the context lacks an allowed public-interest basis. Never indiscriminately delete public emergency helplines.
```python
def f1_triage(text: str, verified_private: bool):
    return None if verified_private else text  # Drop only after an authorized privacy review
```
**Side effects:** a false positive could destroy a legitimate public article; missed private contact details remain a risk. Manual review is essential.
**Official gold-set harm test:** NOT RUN; zero automatic drops have been performed.

## Remaining findings below medicine threshold

- **B2 (5):** confirmed HTML tag residue in four documents and orphan image-tag attributes in one. Proposed narrow tag/attribute handling should preserve visible text; do not blanket-strip brackets.
- **G1 (2):** suspicious separated Telugu vowel signs recorded with UTF-8 hex in `labels.csv`. Never remove ZWJ (`U+200D`) or ZWNJ (`U+200C`) in Indic text. Manual repair rather than global Unicode stripping.
- **D1 (1):** predominantly English page under Telugu label; hold for language adjudication.
- **F3 (1):** age-restricted content candidate; recommended for policy-based exclusion without reproducing source content.
- **H2 (4):** two high-overlap document pairs; compare complete contents before de-duplicating; translated locations or distinct news reports may be legitimately different.

## Validation protocol required before acceptance

1. Obtain Data A/Data B Telugu **clean gold set** and independently confirm the set fingerprint.
2. For each medicine, record `N_gold`, changed documents, dropped documents and unique affected documents. A document both changed and dropped counts once in affected.
3. Compute `affected / N_gold`. Reject if `> 0.01` (more than 1%). Inspect changed gold examples for Indic script damage, especially ZWJ/ZWNJ, vowel signs and normalization.
4. Reconcile final labels after complete human linguistic reading. `partial` cannot be truthfully rewritten to `full` by an automated script.

### Executable harm-test helper (run ONLY when the official gold documents are supplied)
```python
def harm_test(clean_texts, rule):
    if not clean_texts:
        raise ValueError("Official Telugu gold set is required")
    changed = dropped = affected = 0
    for original in clean_texts:
        revised = rule(original)
        if revised is None:
            dropped += 1
            affected += 1
        elif revised != original:
            changed += 1
            affected += 1
    rate = affected / len(clean_texts)
    return {"gold_documents": len(clean_texts), "changed": changed,
            "dropped": dropped, "affected": affected,
            "affected_rate": rate, "pass": rate <= 0.01}
```

**Test status:** local syntax/logic smoke tests passed for the candidate C1/C2 no-harm examples, including Indic ZWJ/ZWNJ preservation. This is NOT the official gold-set harm test; its pass/fail remains unknown.