# Medicine sheet: math-megamath (AditeyaAItronics)

Second read of rows 301-400 of `math-megamath` (positions 300-399 in the pack). One section for each disease found more
than five times in these 100 documents. Counts are from `labels.csv`. Offsets are character offsets in the document text.

Each rule is a Python function `medicine_<code>(text)` that returns the new text (fix) or `True` (drop), in the format
read by `teams/02-data-b/tools/harm_test_indic.py`.

**No harm test was run for this sheet.** Each section says what a harm test should check.

## Patterns in this range

- **Formulas stripped by the scraper** (Encyclopedia of Mathematics, Plus magazine, Kiddle, NCERT, Socratic, papers
  that lost their display equations): drop B5 when the maths becomes unreadable; fix B5 for long papers that lost only
  a few display equations (rows 336, 382, 393).
- **Minus signs and hyphens lost** ('1  w_1', 'L^1L^p', 'Steadystate', 'twentyseven'): G3; drop where the maths
  becomes wrong. A minus turned into '?' (row 333, 't-statistic of ?3.54') is labelled A3.
- **answers.com "related questions" pages** (rows 302, 313, 349, 351, 356, 369) and **SEO snippet farms** ending
  each snippet in 'Read More', 'Learn More' or 'Get Price' (rows 318, 361, 400; row 306 uses '####' headings instead):
  drop C5.
- **Word-spun copies** of tutoring pages ('equilateral' -> 'it is intended', 'pressure' -> 'push'; rows 342, 362) and
  a machine-translated Russian Q&A (row 378): drop D4.
- **Mojibake** from UTF-8 read as Windows-1252 ('Ï†' for φ, 'â€™', 'âˆš'): A3; fixable by a character map.
- **Repeated posts and pages**: forum threads where every post body appears twice and PDFs where each page repeats
  the previous ones: C2.
- **Emails**: Usenet and mailing-list dumps (rows 371, 398), a commit author (327), a code header (372), and
  obfuscated 'name at host edu' (316): F1, type and offset only. The 'name at host' form needs the same team ruling
  kunal2016 asked for.
- **Not maths but intact** (1913 housing report, PROFIBUS config file, Gleason biography): labelled `clean` with a
  note, as kunal2016 did; a topic filter should decide them, not a disease code.
- **The pack's `url` column does not match the text** in many rows (row 391's URL is a forum thread, its text is the
  Linux strtod man page). Labels were judged on the text only.

## Medicine 1: C1 Boilerplate

1. **Disease:** C1, 51 documents. Examples:
   - `f87d92f46c4f30ce`: `Write your answer...` (answers.com question form)
   - `1677f7fea73fed20`: `- Log in to post comments` (comment prompt)
   - `c27307caf037acf5`: `Nôl i'r tabl cynnwys` (Welsh "back to contents" link on an ONS report)
2. **Medicine:** Delete a line that is only site chrome: Q&A form buttons, comment and login prompts, "last edited"
   stamps, mailing-list archive navigation, download/cite links, empty table-of-contents headers.

```python
import re

_LINE = re.compile(r"""^\s*(?:
    Write\ your\ answer\.\.\.|Submit|Study\ guides|Add\ answer|Sign\ in|Sign\ up|\(\d+\)\ Answers|
    -?\ ?Log\ in\ to\ post\ comments|Comments\ are\ no\ longer\ being\ accepted\.|
    Last\ edited(?:\ by\ .{1,40})?:?|\#*\s*Leave\ a\ Reply|You\ don't\ have\ permission\ to\ comment\ on\ this\ page\.|
    Comments\ \(\d+\)|There\ are\ no\ comments\ yet\.|Return\ to\ .{1,40}\ page|
    Quote\ Link\ to\ comment\ Share\ on\ other\ sites\ More\ sharing\ options\.\.\.|
    Nôl\ i'r\ tabl\ cynnwys|\#*\s*Download\ this\ (?:chart|table)\ .{0,120}|Image\ \.csv\ \.xls|
    \(more…\)|Show\ Abstract|Use\ Coupon\ Code.{0,60}|next\ math\ problems\ »|
    \#*\s*(?:Table\ of\ Contents|table\ of\ contents|Contents\ \|)|KNOWPIA|WELCOME\ TO\ KNOWPIA|
    Link\ to\ this\ page:?|Cite\ this\ page|Report\ (?:an|one)\ Error|Recommended\ Posts|Join\ the\ conversation|
    \[Top\]\[All\ Lists\]|\[Date\ Prev\]\[Date\ Next\].{0,80}
)\s*$""", re.X)

def medicine_c1(text):
    """Delete whole lines that are site chrome."""
    return '\n'.join(l for l in text.split('\n') if not _LINE.match(l))
```

3. **Action:** **Fix:** delete the matching lines.
4. **Harm test:** not run. It should confirm that clean maths pages do not lose a real line such as
   a section titled "Contents" or a sentence that is exactly "Submit".
5. **Side effects:**
   - It catches 26 of the 51 C1 documents in my rows. Chrome glued into a sentence (`Learn More### ...`,
     `383Published on`) or site-specific footers are not caught.
   - A real heading called "Comments" or "Table of Contents" is deleted.

## Medicine 2: C5 Lists of keywords or links

1. **Disease:** C5, 26 documents. Examples:
   - `61cd7b47372fec40`: `Related questions` followed only by other people's answers (answers.com)
   - `7eace66a66292935`: `Get Pricecoal hammer mill sizing calculation` (SEO snippet farm)
   - `b9214bb0b9781834`: `Learn More### Cement FAQs | Builders South Africa` (SEO snippet farm)
2. **Medicine:** Drop an answers.com page that starts with the exact header "Study guides / Q: ... / Write your
   answer... / Submit / Related questions" (the anchored pattern from kunal2016's sheet for rows 401-500), and any
   page with 5 or more teaser lines that end in "Read More", "Learn More", "Get Price", "read it" or "... more".

```python
import re

_ANSWERS = re.compile(r"\AStudy guides\s*\n\s*Q: .{1,300}\n\s*Write your answer\.\.\.\s*\n\s*Submit\s*\n\s*Related questions\s*\n")
_TEASER_END = re.compile(r'(?:Read More|Learn More|Get Price|read it|\.\.\. more|… Read more)\s*$', re.I | re.M)
_TEASER_START = re.compile(r'^(?:Learn More|Get Price)\S', re.M)

def medicine_c5(text):
    """Drop link and snippet farms."""
    if _ANSWERS.match(text):
        return True
    return len(_TEASER_END.findall(text)) + len(_TEASER_START.findall(text)) >= 5
```

3. **Action:** **Drop** the document.
4. **Harm test:** not run. It should confirm that a real article with a "Read More" link after each of several
   sections is not dropped.
5. **Side effects:**
   - It catches 11 of 26. Snippet farms without teaser marks (row 306 uses `####` headings, row 389 a book list) and
     link lists (rows 304, 328, 352, 353) need a "share of lines that are titles" measure.
   - A blog index page whose posts all end in "Read More" is dropped even if each teaser is good maths.
   - The answers.com test is anchored at the start of the text, so a document that only quotes that header is not
     touched; an answers.com page that does carry an answer under "Related questions" would still be dropped (none in
     these rows).

## Medicine 3: B5 Stripped formulas (broken markdown / LaTeX)

1. **Disease:** B5, 23 documents. Following the convention of the other readers of this pack, a document whose
   displayed formulas were removed by the scraper is B5. Examples:
   - `0dd55e7a322a5ec9`: `this is equivalent to:` followed by an empty line and the next sentence (formula gone)
   - `cb8eb128eb9a4068`: `The sine of an angle is equal to the .` (ratio stripped)
   - `ce30c040106d4b30`: `minimization of the functional` + blank line + `in the presence of differential constraints`
2. **Medicine:** Count the places where a sentence announces a formula and then stops (`... is given by` + blank line +
   `where`), a function word is followed by a lone full stop (`equal to the .`), a line is only an equation number
   `(1)`, or two labels follow each other with nothing between them (`Gauss's Law:` + blank line + `Gauss's Law for
   Magnetism:`). Drop the document at 2 or more.

```python
import re

_GAP = re.compile(
    r'(?:\b(?:is|are|by|as|to|form|following|equation|formula|functional|gives|becomes|yields|obtain|get)\s*:?|,)\s*\n\s*\n\s*'
    r'(?:where|which|and|so|then|in|In|The|Since|Then|Putting|Differentiating|Combining|Also|Note)\b'
    r'|\b(?:in|of|to|the|is|by|be|Let)\s\.(?=\s|$)'
    r'|^\s*\(\d{1,2}\)\s*\|?\s*$'
    r'|^[^\n]{3,60}:\s*\n\s*\n[^\n]{3,60}:\s*$', re.M)

def medicine_b5(text):
    """Drop a document with 2 or more places where a displayed formula was stripped."""
    return len(_GAP.findall(text)) >= 2
```

3. **Action:** **Drop** the document. A stripped formula cannot be restored from the text.
4. **Harm test:** not run. It should check maths pages with real lists ("The following are:" + blank line + "The ...")
   and pages that number equations on their own line.
5. **Side effects:**
   - It catches 11 of 23. Formulas stripped from inside a sentence ("we write for the temperature at time Suppose")
     leave no structural trace and are missed.
   - A prose document with two "is as follows:" lists followed by "The" sentences is dropped.
   - Long papers that lost only their display equations (rows 336, 382, 393) are worth keeping; this rule drops them
     if they have 2 gaps. A softer action would be to delete only the orphaned "where ..." sentences.

## Medicine 4: C2 Repeated lines

1. **Disease:** C2, 15 documents. Examples:
   - `76e323a6de94d828`: `Hi everybody. Can anyone help me to solve these problems?` (every forum post appears twice)
   - `5d2b38ab1410c78e`: `Guest wrote:Here are the results of a small simulation experiment.` (quoted posts repeated)
   - `bc2f270b6bed90aa`: `Formulas for Area (A) and Circumference (C ) 1` (whole formula sheet appears twice)
2. **Medicine:** Delete the second and later copies of any line of 40 or more characters.

```python
def medicine_c2(text):
    """Delete the second and later copies of a line of 40 or more characters."""
    seen, out = set(), []
    for line in text.split('\n'):
        key = line.strip()
        if len(key) >= 40:
            if key in seen:
                continue
            seen.add(key)
        out.append(line)
    return '\n'.join(out)
```

3. **Action:** **Fix:** delete the repeats.
4. **Harm test:** not run. It should check worked solutions that repeat an equation line on purpose
   (`x^{2} + 5x + 6` written as the question and again as the first step).
5. **Side effects:**
   - It catches 13 of 15, and also changes 8 documents I labelled for other reasons, among them a config file
     (row 359) whose repeated help strings are real.
   - In a worked solution the repeated statement of the problem is removed, which can break the reading order.

## Medicine 5: G3 Lost minus signs and hyphens

1. **Disease:** G3, 7 documents. Following the convention of the other readers of this pack, minus signs and hyphens
   lost by an earlier cleaning step are G3. Examples:
   - `8408719e9c385e86`: `\(w_2 = 1  w_1\)` (should be `1 - w_1`)
   - `00c162df927c5ba1`: `$L^1L^p$ decay rates` (should be `L^1-L^p`)
   - `bbc30fbe33f29fd2`: `Steadystate electric flow field` (should be `Steady-state`)
2. **Medicine:** A lost minus leaves two spaces between operands inside a formula. Drop the document when 3 or more lines
   that contain formula characters have this trace, because the maths is then wrong.

```python
import re

_LOST_MINUS = re.compile(r'(?<=[\w)}])  (?=[\w(\\])')
_MATHY = re.compile(r'[=^_\\]|\b\d')

def medicine_g3(text):
    """Drop a document where 3 or more formula lines show the double-space trace of a lost minus."""
    hits = sum(1 for line in text.split('\n') if _MATHY.search(line) and _LOST_MINUS.search(line))
    return hits >= 3
```

3. **Action:** **Drop** the document.
4. **Harm test:** not run. It should check pages that use two spaces for alignment in tables or code.
5. **Side effects:**
   - It catches 2 of 7. Lost hyphens in words (`largetime`, `Outofsample`, `twentyseven`) need a word list, and a
     lost minus that leaves one space (`L^1L^p`) leaves no trace.
   - Plain-text tables aligned with double spaces can be dropped.

## Medicine 6: A3 Mojibake

1. **Disease:** A3, 7 documents. Examples:
   - `992d38543ccccd16`: `Ï† [0, Ï€)` (φ and π decoded as Windows-1252)
   - `9a93353b16444362`: `Iâ€™ve` (apostrophe U+2019 double-encoded)
   - `10f1386b0e9a9539`: `âˆš65` (√ double-encoded)
2. **Medicine:** Repair UTF-8 text that was decoded as Windows-1252, for the characters seen in this pack. The map is
   built from the characters themselves so that no mojibake has to be typed into the code.

```python
def _mojibake(ch):
    return ch.encode('utf-8').decode('cp1252')

_MAP = [(_mojibake(ch), ch) for ch in '’“–—…√πφθ']

def medicine_a3(text):
    """Replace double-encoded quotes, dashes, √, π, φ and θ with the real characters."""
    for bad, good in _MAP:
        text = text.replace(bad, good)
    return text
```

3. **Action:** **Fix:** replace the sequences.
4. **Harm test:** not run. It should confirm that no clean page contains these sequences on purpose (for example a page
   that explains mojibake).
5. **Side effects:**
   - It catches 3 of 7. A minus sign turned into `?` (row 333), a lost `fi` ligature (`…ts`, `broad elds`) and `³`
     for `ł` cannot be mapped back safely.
   - The right double quote and the no-break space are left out: their Windows-1252 forms contain bytes that do not
     decode, and they would need a byte-level fix.

## Medicine 7: F1 Personal data

1. **Disease:** F1, 6 documents. Only type and position are given, never the value:
   - `7471b9a550060215`: email at offset 68 (17 addresses in a Usenet dump)
   - `95627c7c24b4d18e`: email at offset 215 (posters' addresses in a mailing-list archive)
   - `22cbc4b9416bb401`: obfuscated email at offset 3416 (written as "name at host edu")
2. **Medicine:** Replace email addresses, and the "name at host edu" spelling, with `[email]`.

```python
import re

_EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
_OBF = re.compile(r'\b[\w.]+ at [\w-]+ (?:dot )?(?:edu|com|org|net)\b')

def medicine_f1(text):
    """Replace email addresses with a placeholder."""
    text = _EMAIL.sub('[email]', text)
    return _OBF.sub('[email]', text)
```

3. **Action:** **Fix:** replace with `[email]`.
4. **Harm test:** not run. It should check that `@` in code (decorators, `@ANI` handles) is not changed.
5. **Side effects:**
   - It also replaces publisher and corporate addresses (row 382), which are not personal data.
   - A truncated address such as `name@gm` (row 375) has no dot and is not caught.
   - Names and phone numbers are not handled; they need the shared PII filter.

## Not covered

C3 (3), D4 (3), B4 (2), E1 (1) and B2 (1) are found five times or fewer in these rows and have no medicine, as the
template asks.
