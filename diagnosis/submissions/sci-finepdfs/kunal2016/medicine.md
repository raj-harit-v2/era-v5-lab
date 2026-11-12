# Medicine sheet: sci-finepdfs (kunal2016, rows 401-500)

## Medicine 1: C1 repository cover page before the paper

**Disease:** C1
**Action:** fix

**Seen:** 3 of 100 in rows 401-500 (408 HAL, 410 City Research Online, 474 MPRA), 4 of 500 in the
pack (also row 131, HAL). The PDF's first page is the archive's cover sheet: a citation, archive id,
repository links and reuse terms; the paper then starts again with its own title.

Remove everything up to the end of the last cover marker in the first 4000 characters:
HAL "To cite this version:" plus its citation paragraph, or the end of HAL's French archive notice;
City Research Online's "Reuse: Copies of full items ..." paragraph; MPRA's "MPRA Paper No. N, posted ..."
line. If less than 1000 characters would remain, the document is left unchanged.

```python
import re

COVER_END = re.compile(
    r"To cite this version:\s*\n\s*\n[^\n]+\n"                      # HAL: marker + one citation paragraph
    r"|des laboratoires publics ou priv\u00e9s\.\s*\n"                  # HAL: end of the French archive notice
    r"|Reuse: Copies of full items[^\n]*\n"                           # City Research Online: last cover paragraph
    r"|MPRA Paper No\. \d+, posted [^\n]*\n")                         # MPRA

def cure_c1(text):
    head = text[:4000]
    m = None
    for m in COVER_END.finditer(head):
        pass
    if m is None:
        return text
    rest = text[m.end():].lstrip("\n")
    if len(rest) < 1000:          # nothing substantial after the cover: leave the document alone
        return text
    return rest
```

**Side effects:** only the three archive formats above are recognised; other repositories' covers
(e.g. Digital Commons "Follow this and additional works at") are left alone. A paper whose own text
quotes "To cite this version:" in its first 4000 characters would lose its opening.
