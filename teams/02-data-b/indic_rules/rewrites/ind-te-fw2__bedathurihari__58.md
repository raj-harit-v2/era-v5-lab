# Rewrite in the harm tool's format: ind-te-fw2, bedathurihari (PR #58)

TSAI ruling 3 on #211 (3 Nov): the Data B rules owner may rewrite a medicine sheet that `harm_test_indic.py` cannot
read, and the author must OK the rewrite in their PR. **Author OK: pending.**

What changed: each medicine with an automatic function gets a `**Disease:** <code>` line and this layout. The code is
the author's, copied unchanged from PR #58 at `9440e32`. Counts and wording are the author's.

**Harm test: not run yet.** The author's sheet says "NOT RUN". `ind-te-fw2` has an 18-document gold set on main
(`teams/02-data-b/gold/ind-te-fw2_gold.csv`); the Data B rules owner runs it and records the result here.

## Medicine 1: C1 - boilerplate

1. **Disease:** C1. 33 candidate documents in the pack.
2. **Medicine:** Remove isolated "related links" lines only (Also Read, Read More and their Telugu forms), not whole articles.

```python
import re
RELATED = re.compile(r"(?im)^[ \t]*(?:[-•][ \t]*)?(?:Also[ \t]+Read|Read[ \t]+More|Read[ \t]+Also|ఇది కూడా చదవండి|ఇవి కూడా చదవండి|ఇదీ చదవండి|మరింత చదవండి)[ \t]*[:：.\-]*[^\n]*\n?")
def fix_c1(text: str) -> str:
    return RELATED.sub("", text)
```

3. **Action:** fix.
4. **Harm test:** not run yet (gold set of 18 documents, ind-te-fw2).
5. **Side effects:** might remove genuine citations or related links with educational value.

## Medicine 2: C2 - repeated lines

1. **Disease:** C2. 9 candidate documents in the pack.
2. **Medicine:** Remove only later copies of one known embedded-widget marker line within the same document; other repeated lines are kept.

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

3. **Action:** fix.
4. **Harm test:** not run yet (gold set of 18 documents, ind-te-fw2).
5. **Side effects:** repeated widget phrases can refer to different embeds; deleting them may lose document structure.

## Medicine 3: D3 - mixed language

1. **Disease:** D3. 17 candidate documents in the pack.
2. **Medicine:** Preserve the text: natural Telugu-English code switching is labelled, not changed.

```python
def fix_d3(text: str) -> str:
    return text  # Intentional: preserve legitimate Telugu-English code switching.
```

3. **Action:** keep (the rule changes no text).
4. **Harm test:** not run yet (gold set of 18 documents, ind-te-fw2).
5. **Side effects:** unrelated English boilerplate may be retained; C1 handles confirmed navigation lines.

## Not rewritten

- **F1** (`f1_triage(text, verified_private)`) needs a reviewer's decision passed in, so it cannot run on text alone. Data A's
  shared F1 rule already covers `ind-te-fw2`.
- **B2, G1, D1, F3, H2** are findings below the author's threshold, with no code.
