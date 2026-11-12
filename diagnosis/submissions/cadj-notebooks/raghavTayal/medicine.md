# Medicine sheet: cadj-notebooks (<your GitHub handle>)

Pack: `cadj-notebooks`, 500 Kaggle notebooks (Python), all read in full. Diseases found more than five times:
C1 (184), B4 (78), B1 (16), B2 (16), C2 (14). One medicine for each below.

## Harm test status

- **Harm test for Gate 1: not testable.** There is no gold set for this pack.
  - On 31 Oct, `main` has no Data A gold folder at all.
  - `teams/02-data-b/gold/` has only Indic files, and its `gold_coverage.csv` has no `cadj-notebooks` row.
  - Open PR #140 adds Data A gold sets for 13 packs, but none for `cadj-notebooks`, and `cadj-notebooks` is not in
    its `g1_pack_ids.txt`. Its `code-python` gold set (46 documents) belongs to a different pack of plain Python
    files.
  - No other open or closed PR adds a gold set for this pack.

  So each medicine below is "not testable: no gold set for cadj-notebooks", harm-test exit code 2. This is the TSAI
  rule for a pack with no gold set. When a gold set for this pack is published, the harm tests must be run on it.
- **Own check (not the Gate 1 test):** as extra information, each medicine was also run, with Data A's
  `harm_test.py` from PR #140, on the 246 documents in this pack that `labels.csv` marks `clean`. One reader marked
  them, not two. The "Own check" numbers below come from this set.
- **1% limit:** a medicine passes if it changes or drops at most max(1, floor(1% of n)) documents, where n is the
  size of the gold set. On the 246 own clean documents, this is 2 documents.
- **All five rules together (own check):** `--rule all` also runs the rules one after another, in file order.
  Together they change 2 of the 246 own clean documents (0.81%), within the limit of 2: PASS.
- **How to run it:** `python -I teams/01-data-a/tools/harm_test.py --pack <pack.parquet> --gold <gold.csv> --rules
  medicine.md --rule all` (Data A's tool from PR #140). With an empty gold set it prints `result: NOT TESTABLE` and
  exits with code 2.

## Shared helpers

Every rule below uses these helpers. A notebook has three kinds of region, and each rule changes only the regions
where its disease lives, so no prose rule ever touches a line of code. Fence lines are never changed.

- `desc`: the dataset description before `### Code:`
- `py`: a ```` ```python ```` block, holding code lines and markdown cells written as `# ...` comment lines
- `bare`: a plain ```` ``` ```` block, holding printed output or dataset examples

```python
import hashlib
import html
import re

def _lines_with_kind(text):
    """Yield (kind, line) for every line; kind is desc, py, bare or fence."""
    state = "desc"
    for line in text.split("\n"):
        m = re.match(r"^```(\w*)", line)
        if state == "desc" and m:
            yield "fence", line
            state = "py" if m.group(1) == "python" else "bare"
        elif state in ("py", "bare") and line.startswith("```"):
            yield "fence", line
            state = "desc"
        else:
            yield state, line

def _is_comment(line):
    return line.lstrip().startswith("#")

def _is_prose(kind, line):
    return kind == "desc" or (kind == "py" and _is_comment(line))
```

Each rule takes the document text and returns the new text (unchanged when it has nothing to fix), or `True` to
drop the document. Checked on the whole pack:
- **Python safety:** no Python cell that parsed before a rule fails to parse after it.
- **Code safety:** B1 and B2 change no code line.

---

## Medicine 1

1. **Disease:** C1, boilerplate. Found in **184** documents. Examples:
   - `1b8efecd14e5b7fd`, offset 481: `# Input data files are available in the read-only "../input/" directory` (Kaggle starter-cell comment)
   - `15b36d81d0b85ac2`, offset 42: `There's a story behind every dataset and here's your opportunity to share yours.` (Kaggle's unedited dataset-description template)
   - `c3aeb136d78a357b`, offset 805: `🚨 **Your notebook can be here!** 🚨` (publisher promo block, with `### More Datasets` / `For more datasets, click [here](…)`)

2. **Medicine:** Delete three kinds of line:
   - in code cells, any comment line that is exactly one of the 8 Kaggle starter-cell sentences
   - in the description, the four sentences of Kaggle's default template, plus a template header (`Context`, `Content`, `Acknowledgements`, `Inspiration`) when the next non-blank line is a template sentence
   - in the description, the publisher promo lines and the Kaggle "Start a new kernel" link with its reference line

   Whole-line exact matches only. The starter-cell code itself (`import numpy as np`, the `os.walk` loop) stays, and
   so do its import-line comments (`import numpy as np  # linear algebra`, 213 documents): including them would
   change 35 more documents.
   ```python
   _STARTER_LINES = {
       '# Input data files are available in the read-only "../input/" directory',
       '# Input data files are available in the "../input/" directory.',
       '# For example, running this (by clicking run or pressing Shift+Enter) will list all files under the input directory',
       '# For example, running this (by clicking run or pressing Shift+Enter) will list the files in the input directory',
       '# You can write up to 20GB to the current directory (/kaggle/working/) that gets preserved as output when you create a version using "Save & Run All"',
       '# You can write up to 5GB to the current directory (/kaggle/working/) that gets preserved as output when you create a version using "Save & Run All"',
       "# You can also write temporary files to /kaggle/temp/, but they won't be saved outside of the current session",
       '# Any results you write to the current directory are saved as output.',
   }
   _KAGGLE_TEMPLATE = [
       "There's a story behind every dataset and here's your opportunity to share yours.",
       "What's inside is more than just rows and columns. Make it easy for others to get started by describing how you acquired the data and what time period it represents, too.",
       "We wouldn't be here without the help of others. If you owe any attributions or thanks, include them here along with any citations of past research.",
       "Your data will be in front of the world's largest data science community. What questions do you want to see answered?",
   ]
   _TEMPLATE_HEADER = re.compile(r"^#{1,6}\s*(Context|Content|Acknowledgements|Inspiration)\s*$")
   _PROMO = re.compile(r"^(?:#{1,6}\s*(?:More Datasets|Featured Notebooks)\s*"
                       r"|(?:>|&gt;)\s*For more datasets, click \[here\]\(https://www\.kaggle\.com/[^)]+\)\.?\s*"
                       r"|(?:>|&gt;)\s*-\s*🚨\s*\*\*Your notebook can be here!\*\*\s*🚨!?\s*)$")
   _KERNEL_LINK = re.compile(r"^\s*#\[Start a new kernel\]\[\d+\]\s*$")
   _KERNEL_REF = re.compile(r"^\s*\[\d+\]:\s*https://www\.kaggle\.com/\S+/kernels\?modal=true\s*$")

   def medicine_c1(text):
       lines, out = list(_lines_with_kind(text)), []
       for i, (kind, line) in enumerate(lines):
           s = line.rstrip("\r")
           if kind == "py" and s.strip() in _STARTER_LINES:
               continue
           if kind == "desc":
               if s.strip() in _KAGGLE_TEMPLATE or _PROMO.match(s) or _KERNEL_LINK.match(s) or _KERNEL_REF.match(s):
                   continue
               if _TEMPLATE_HEADER.match(s.strip()):
                   nxt = next((l.rstrip("\r").strip() for _, l in lines[i + 1:] if l.strip()), "")
                   if nxt in _KAGGLE_TEMPLATE:
                       continue
           out.append(line)
       new = "\n".join(out)
       if new != text:
           new = re.sub(r"(?:\r?\n){4,}", "\n\n\n", new)    # close the gaps left by removed blocks
       return new
   ```

3. **Action:** fix the text.

4. **Harm test:**
   - **Gate 1:** not testable, because there is no gold set for `cadj-notebooks` (exit code 2).
   - **Own check:** 246 own clean documents, 0 changed, 0 dropped, limit 2: PASS.
   - **On the pack:** the rule fixes all 184 C1 documents.

5. **Side effects:**
   - **A starter sentence glued to other text is left in place.** One case: `…current sessionimport jo_wilder_310`.

---

## Medicine 2

1. **Disease:** B4, template junk: redaction placeholders left by an earlier anonymiser. Found in **78** documents.
   `<NAME>` occurs 336 times; `<EMAIL>` 3, `<PASSWORD>` 1 and `<KEY>` 1. Examples:
   - `bae08c54a97cdb49`, offset 1194: `<NAME>`, in prose: "founded in 2016 by `<NAME>` and `<NAME>`"
   - `3d2c4f980276448b`, offset 1002: `<PASSWORD>`, in code: `password = "<PASSWORD>"`
   - `c94312d3b1e70aaf`, offset 5462: `<EMAIL>`

2. **Medicine:** Replace each placeholder with a neutral value of the right type:
   - **names:** taken from a fixed list of eight; successive `<NAME>`s in one document get different names, and the
     choice is deterministic per document
   - **emails** become `user@example.com`, **passwords** `your_password`, **keys** `YOUR_API_KEY`
   - **a placeholder glued into a word** (for example `Mid<NAME>town`) means the original word is lost, so the
     document is dropped

   `<UNK>` and `<BIAS>` are ordinary NLP tokens, not placeholders, and are not touched.
   ```python
   _PLACEHOLDER = re.compile(r"<(NAME|EMAIL|PASSWORD|KEY|API_KEY|TOKEN|SECRET|IP_ADDRESS)>")
   _FILLERS = {"NAME": ["Alex Morgan", "Priya Shah", "Chen Wei", "Maria Lopez", "Tunde Okafor", "Sara Novak", "Arjun Rao", "Lena Fischer"],
               "EMAIL": ["user@example.com"], "PASSWORD": ["your_password"], "KEY": ["YOUR_API_KEY"], "API_KEY": ["YOUR_API_KEY"],
               "TOKEN": ["YOUR_TOKEN"], "SECRET": ["YOUR_SECRET"], "IP_ADDRESS": ["192.0.2.1"]}

   def medicine_b4(text):
       for m in _PLACEHOLDER.finditer(text):
           if re.match(r"\w", text[m.start() - 1:m.start()]) or re.match(r"\w", text[m.end():m.end() + 1]):
               return True                               # glued into a word: drop the document
       start, k = hashlib.sha1(text.encode()).digest()[0], {}
       def _fill(m):
           n = k[m.group(1)] = k.get(m.group(1), -1) + 1
           opts = _FILLERS[m.group(1)]
           return opts[(start + n) % len(opts)]
       return _PLACEHOLDER.sub(_fill, text)
   ```

3. **Action:** fix the text, or drop the document when a placeholder is glued into a word (3 documents in the pack).

4. **Harm test:**
   - **Gate 1:** not testable, because there is no gold set for `cadj-notebooks` (exit code 2).
   - **Own check:** 246 own clean documents, 0 changed, 0 dropped, limit 2: PASS.
   - **On the pack:** all 78 B4 documents are fixed (75) or dropped (3), and no Python cell breaks.

5. **Side effects:**
   - **A filler name can state a false fact.** In `bae08c54a97cdb49` the redacted names are fast.ai's real founders,
     and the fix makes the text say "founded … by Alex Morgan and Priya Shah". 73 of the 78 documents have a
     placeholder in prose or output, where this can happen.

---

## Medicine 3

1. **Disease:** B1, HTML entities. Found in **16** documents. Examples:
   - `64a722d6803fada5`, offset 527: `&gt;` (`Row ID =&gt; Unique ID for each row.`)
   - `ef3aad0805f390c8`, offset 55: `&nbsp;`
   - `91489ad53170c875`, offset 2767: `&amp;`

2. **Medicine:** In prose and output only (description, `# ` markdown comment lines, plain output blocks):
   - replace `&nbsp;` with a normal space
   - decode every other entity that ends with `;` (named, decimal or hex)

   Entities without the closing `;` are left alone, so a URL such as `?a=1&copy=2` is never decoded. Code lines are
   never touched, so entities inside code strings stay (in two labelled documents they sit in HTML strings, where
   they are legitimate); in those documents only the prose entities are fixed.
   ```python
   _ENTITY = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")

   def medicine_b1(text):
       out = []
       for kind, line in _lines_with_kind(text):
           if (_is_prose(kind, line) or kind == "bare") and "&" in line:
               line = line.replace("&nbsp;", " ")
               line = _ENTITY.sub(lambda m: html.unescape(m.group()), line)
           out.append(line)
       return "\n".join(out)
   ```

3. **Action:** fix the text.

4. **Harm test:**
   - **Gate 1:** not testable, because there is no gold set for `cadj-notebooks` (exit code 2).
   - **Own check:** 246 own clean documents, 0 changed, 0 dropped, limit 2: PASS.
   - **On the pack:** all 16 B1 documents fixed, and no code line changed. The rule also fixes one document I had
     not labelled (`&lt;10 posts` in a markdown comment), which is a missed B1 label.

5. **Side effects:**
   - **Prose that writes about entities on purpose is changed.** For example, "write `&amp;` in HTML" becomes
     "write `&` in HTML". There is no such case in the pack.

---

## Medicine 4

1. **Disease:** B2, HTML or XML tags. Found in **16** documents. Examples:
   - `a8116e4579548640`, offset 1266: `<br />` (inside dataset review text)
   - `1ae40a160c9715fa`, offset 652: `<img src=…` (in a markdown cell)
   - `196d7823a6ef6cc6`, offset 5903: `<div style='color: #216969;`, a tag whose style attributes run over several
     `# ` comment lines

2. **Medicine:** In prose and output only, remove common HTML tags and keep the text between them:
   - a line-break tag (`br`, `p`, `div`, `li`, headings) becomes a space inside a `# ` comment line, and a newline
     elsewhere
   - a tag that spans several `# ` comment lines is removed whole, and the line structure stays valid
   - tags inside `` `inline code` `` are left alone, and code lines are never touched
   - tags inside dataset text are removed too: IMDB reviews with `<br />` become plain text, so they then differ
     from the published dataset
   ```python
   _TAG = re.compile(r"</?(?:div|span|p|br|img|a|b|i|u|strong|em|h[1-6]|ul|ol|li|table|thead|tbody|tr|td|th|font|center"
                     r"|hr|sup|sub|iframe|blockquote|code|pre|small|big)\b[^<>\n]*/?>", re.I)
   _BREAK = re.compile(r"^</?(?:br|p|div|hr|li|tr|h[1-6]|ul|ol|table|blockquote)\b", re.I)
   _ML_TAG = re.compile(r"<(?:div|span|p|font|h[1-6]|table|td|th|center)\b[^<>]*?(?:\n[ \t]*#[^<>\n]*?)+>", re.I)

   def medicine_b2(text):
       out = []
       for kind, line in _lines_with_kind(_ML_TAG.sub("", text)):
           if _is_prose(kind, line) or kind == "bare":
               def _repl(m, line=line, kind=kind):
                   if line[:m.start()].count("`") % 2:      # inside `inline code`
                       return m.group()
                   if _BREAK.match(m.group()):
                       return " " if kind == "py" else "\n"
                   return ""
               line = _TAG.sub(_repl, line)
           out.append(line)
       return "\n".join(out)
   ```

3. **Action:** fix the text.

4. **Harm test:**
   - **Gate 1:** not testable, because there is no gold set for `cadj-notebooks` (exit code 2).
   - **Own check:** 246 own clean documents, 1 changed, 0 dropped, limit 2: PASS.
   - **On the pack:** all 16 B2 documents fixed, and no code line changed.

5. **Side effects:**
   - **Prose that writes about a tag is changed.** The one own-check change is `268f991cfc43ff93`: "the texts
     contain html tags (`<br/>` etc)" loses the `<br/>` it names.

---

## Medicine 5

1. **Disease:** C2, repeated lines. Found in **14** documents. Examples:
   - `c992827d04e4002c`, offset 7893: `# Assigning Multiple Choice columns into a single column with nan values`, 19 times
   - `0352926ffffac06d`, offset 8479: `# Convert y_train and y_test to numpy arrays`, 9 times
   - `41fa0208c1957037`, offset 20997: a commented-out line `silent = True,cat_features=catFeatures)`, 13 times

2. **Medicine:** In code cells, a comment line that appears 5 or more times in one document is kept the first time
   and deleted after that.
   - The line must have at least 25 characters, at least 12 of them letters, digits or underscores, so separator
     lines like `# ======…` are never touched.
   - Code lines are never deleted: a repeated `import` or `plt.show()` is normal in notebooks.
   - The thresholds were chosen on the pack. With a 15-character minimum the rule fixes 10 of the 14 documents but
     changes 1.2% of the own clean documents. With 25 characters it fixes 7 and changes 0.4%.
   ```python
   def medicine_c2(text, min_repeats=5, min_chars=25):
       lines, count = list(_lines_with_kind(text)), {}
       for kind, line in lines:
           s = line.strip()
           if kind == "py" and _is_comment(line) and len(s) >= min_chars and len(re.sub(r"\W", "", s)) >= 12:
               count[s] = count.get(s, 0) + 1
       rep = {s for s, n in count.items() if n >= min_repeats}
       if not rep:
           return text
       seen, out = set(), []
       for kind, line in lines:
           s = line.strip()
           if kind == "py" and s in rep:
               if s in seen:
                   continue
               seen.add(s)
           out.append(line)
       return "\n".join(out)
   ```

3. **Action:** fix the text.

4. **Harm test:**
   - **Gate 1:** not testable, because there is no gold set for `cadj-notebooks` (exit code 2).
   - **Own check:** 246 own clean documents, 1 changed, 0 dropped, limit 2: PASS.

5. **Side effects:**
   - **It fixes only 7 of the 14 C2 documents.** It misses:
     - short repeated markers such as `# YOUR CODE ENDS HERE` and `# [Back to top](#top)`, which are under 25 characters
     - repeated code lines (3 documents), on purpose
     - one repeated description line
   - **Repeated commented-out code can carry meaning.** For example, a template marker before each exercise loses its
     later copies. Code behaviour never changes, because only comments are removed.
   - **It changes some documents I did not label C2,** where an ordinary comment repeats 5+ times. Example:
     `# for i in range(n_classes):` repeated 20 times.