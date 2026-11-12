# Medicine sheet: math-megamath (kunal2016, rows 401-500)

## Medicine 1: C5 answers.com "related questions" pages

**Disease:** C5
**Action:** drop

**Seen:** 4 of 100 in rows 401-500 (450, 480, 483, 499; asraj labels the same 4 drop), 10 of 500 in the pack.
Every one has the same layout: "Study guides", the question, "Write your answer... / Submit",
then a list of snippets from other questions. The page's own question is never answered.

Drop the document when it starts with exactly that header. Nothing else in the pack starts this way.

```python
import re

ANSWERS = re.compile(r"\AStudy guides\s*\n\s*Q: .{1,300}\n\s*Write your answer\.\.\.\s*\n\s*Submit\s*\n\s*Related questions\s*\n")

def cure_c5(text):
    if ANSWERS.match(text):
        return ("drop", "")
    return text
```

**Side effects:** an answers.com page that does carry an answer below "Related questions" is also
dropped (none seen in this pack). Matching is anchored at the start of the text, so a quotation of
the header inside another document is not touched.
