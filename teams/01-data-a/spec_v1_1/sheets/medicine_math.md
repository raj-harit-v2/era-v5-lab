# medicine_math: math medicines for the Spec v1.1 new diseases

**Draft, 12 Nov.** This sheet has one rule for each of the 8 new math diseases in `NEW_DISEASES.md`. A disease is new when it isn't in `DISEASES.md`, and it counts when it appears in 1% or more of the 299 math docs read. Reasons and choices are in `decisions_math.md`.

- **Packs.** finemath has 86 gold docs and megamath 26 (Data A gold). Each pack is tested on its own gold set.
- **Limit.** Docs changed plus dropped: at most `max(1, floor(1% of gold))` = 1 doc on each pack.
- **Rule form.** As in `../../spec_v1/sheets/medicine_math.md`: `doc = {doc_id, text, url, lang_label, pack_id}`, and `medicine(doc)` returns `(action, text)`. Both math packs carry the `en` tag, so each rule also checks `pack_id` against `ORIGIN`. A doc with no `pack_id` passes unchanged.
- **Where each rule runs.** On the packs where its disease was found (`ORIGIN`), as in spec v1.
- **Codes and IDs.** They come from `NEW_DISEASES.md`. Every code here is a proposed new code.
- **Run order.** These rules run after the math family's v1 rules, because the readers found the diseases in v1-cleaned text. Within this sheet they run in section order: stage 10 (characters), then stage 30 (source), with the drops first.
- **Every reading row so far is AI-suggested.** The hand check of the examples comes before a rule is final.
- **Diseases that can't be repaired get drop rules.** For lost formulas, figures and table layout, nothing can be put back. A drop rule is the medicine, and the harm test sets its status.

Each harm cell gives the gold harm % (gold docs changed or dropped / gold docs) and the result at the limit. `off` means the pack isn't in `ORIGIN`. The last column counts the reading docs with the rule's code that it changes or drops, on the cleaned sample the readers read (`scripts/reading_recall.py`).

| # | ID | disease | action | stage | finemath | megamath | reading docs treated |
|---|---|---|---|---|---|---|---|
| 1 | `DA-A8-001` | A8 words run together (NEW-missing-spaces) | fix | 10 | 1.16% (1/86) PASS | 0.00% (0/26) PASS | 5 / 13 |
| 2 | `DA-C9-003` | C9 page made from a template for one value (NEW-template-pages) | drop | 30 | 1.16% (1/86) PASS | 0.00% (0/26) PASS | 8 / 9 |
| 3 | `DA-C9-001` | C9 SEO filler (NEW-seo-filler) | fix + drop | 30 | 0.00% (0/86) PASS | 0.00% (0/26) PASS | 8 / 15 |
| 4 | `DA-D6-001` | D6 machine-written text (NEW-ai-generated-text) | fix + drop | 30 | 0.00% (0/86) PASS | off | 3 / 8 |
| 5 | `DA-C7-001` | C7 content lost in extraction: formulas (NEW-missing-formulas) | drop | 30 | 0.00% (0/86) PASS | 0.00% (0/26) PASS | 4 / 29 |
| 6 | `DA-C7-002` | C7 content lost in extraction: figures (NEW-missing-figures) | drop | 30 | off | 0.00% (0/26) PASS | 4 / 5 |
| 7 | `DA-C8-001` | C8 layout lost in extraction: flattened formulas (NEW-flattened-formulas) | drop | 30 | 0.00% (0/86) PASS | 0.00% (0/26) PASS | 3 / 22 |
| 8 | `DA-C8-002` | C8 layout lost in extraction: merged table cells (NEW-merged-table-cells) | drop | 30 | 0.00% (0/86) PASS | 0.00% (0/26) PASS | 3 / 11 |
| | all in order | sections 1–8 | | | **2.33% (2/86) FAIL** | 0.00% (0/26) PASS | |

**Harm runs, 12 Nov.** Reports: `results/sheets/math-finemath_harm.json` and `math-megamath_harm.json`. Every rule passes alone on both packs. In order, megamath passes and finemath touches 2 gold docs, against a limit of 1. Both of those gold docs have the disease itself:
- **`2d328b828fa97706`** (`DA-A8-001`, fix): it has `fieldtrip.Write an equation`, a real missing space, which the rule puts back.
- **`0f119a596e8b7f63`** (`DA-C9-003`, drop): it's a grams-to-kilograms converter page with the same headings as reading doc `d0693c18056bae02`: "Alternative conversion", "Approximate result", "Conversion table", "… chart".

These are gold contradictions, not false positives. Under spec v1's hold rule, `DA-A8-001` would be held, because it treats fewer reading rows, and that would leave A8 without a working medicine.

**Handling: gold contradictions** (proposed by aneeshads on 13 Nov; Vijay agreed). This is how spec v1 handled `eee25e81417bc1b7` in sci.
- Both docs stay out of the count for these two rules only.
- They are flagged for a reader to check again at the next gold refresh.
- Without them, finemath in order touches 0 of the other 84 gold docs and passes.
- The gold CSV and `harm_test.py` are not changed.

The first runs dropped gold docs that turned out to be false positives. `DA-C7-001`, `DA-C8-001` and `DA-C8-002` were narrowed to fix them; see their side effects.

**Taken out.** A B1 rule (`DA-B1-101`) came out on 12 Nov, because B1 is in `DISEASES.md`. NEW-aggregated-questions is C4, also in `DISEASES.md`, so it has no section here.

Each section below follows the spec v1 card:
1. **Disease:** code, count and 3 examples by doc_id.
2. **Medicine:** in words, then the python block.
3. **Action** and the packs it runs on.
4. **Harm test:** per pack.
5. **Side effects.**
6. **Spec v1.1:** status, author, source.

## 1. `DA-A8-001` · A8 words run together · fix · stage 10

1. **Disease:** NEW-missing-spaces, 13 docs: pyru 5 (finemath) and Satyanarayana 8 (megamath). Examples: `03aeffcf72c72418`, `167ef4a340862a0e`, `1ab888d9366a43fd`. A line break or space was lost, so two words run together, as in `HydrogenWhen`, `ProblemsThe`, `minQuestions`.
2. **Medicine:**
   - **What it fixes.** It puts a space back where a lowercase word of 3+ letters runs into a capitalised word that starts a sentence or a heading (`The`, `When`, `Questions`, `Solution`, `Example`…), or into that word after a full stop (`word.The`).
   - **Why only those words.** A capitalised word that opens a sentence is never part of a brand or code name, so `JavaScript`, `WordPress`, `LinkedIn` and `maxValue` stay as they are.
   - **What it leaves alone.** Lines that look like code, lines inside code fences, and words with digits or underscores.
   - **What it can't fix.** Lowercase pairs such as `twoapproaches` need a dictionary, so they are left.

```python
RULE_ID = "DA-A8-001"
CODE = "A8"  # proposed new code: words run together (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

# capitalised words that open a sentence or a heading; a word glued to one of these lost its space
A8_STARTERS = frozenset((
    "The This That These Those There Then Thus Therefore Hence When Where What Which Why How Who It If We You Your Our "
    "For From Let Find Given Solve Show Prove Step Steps Note Example Examples Exercise Exercises Question Questions "
    "Problem Problems Solution Solutions Answer Answers Continue Click Each Every All Here Now First Next Finally "
    "Lesson Chapter Section Table Figure Write Calculate Determine Explain Consider Suppose Assume").split())
A8_GLUED = re.compile(r"(?<![A-Za-z0-9_.])([A-Z]?[a-z]{3,})(\.?)([A-Z][a-z]+)(?![A-Za-z0-9_])")
A8_CODE = re.compile(r"[{};]|==|=>|->|::|//|\bdef |\bfunction\b|\breturn\b")


def _a8_join(m):
    left, dot, right = m.groups()
    if right not in A8_STARTERS:
        return m.group()
    return left + dot + " " + right


def medicine_a8(text):
    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        if fence or A8_CODE.search(line) or line.lstrip().startswith("```"):
            out.append(line)
            continue
        out.append(A8_GLUED.sub(_a8_join, line))
    return "\n".join(out)


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_a8(doc["text"]), doc["text"])
```

3. **Action:** fix. **Runs on:** finemath, megamath. **Reading docs it treats:** 5 of 13, all fixed.
4. **Harm test:** finemath 1.16% (1/86) PASS; megamath 0.00% (0/26) PASS. The finemath gold doc it changes, `2d328b828fa97706`, has a real missing space (`fieldtrip.Write`).
5. **Side effects:**
   - A name that really is glued to a sentence word, such as a product called `SmartThe`, would be split.
   - It misses joins into words not on the list (`ZakharovShabat`, `instead.Cf.`) and all lowercase joins.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

## 2. `DA-C9-003` · C9 page made from a template for one value · drop · stage 30

1. **Disease:** NEW-template-pages, 9 docs: pyru 8 and Satyanarayana 1. Examples:
   - `28f56e454b2ade39`: number facts for 36871
   - `32b1f031d8c464e4`: 15 percent off \$41
   - `647d9713533c5664`: the number 6186

   These are calculator, unit-converter and number-fact pages that a site makes for each value.
2. **Medicine:** drop the doc when any one of these holds.
   - **(a)** It has a sentence that only unit-converter sites write ("Feel free to use our online unit conversion calculator").
   - **(b)** Its Markdown headings hold at least 2 different template phrases, and at least one of them is used only by such sites ("as geometric shapes", "Cryptographic Hash Functions", "Latest conversions of", "converter", "How to write / spell"…). Weak phrases that a real lesson may use too, such as "Prime factorization of", "Divisors of" and "Conversion table", count only next to one of these.
   - **(c)** One value appears in at least 3 headings and in at least a quarter of all headings. A value is a number of 3 or more digits, a decimal, or a dollar amount; years 1900–2099 don't count.

```python
RULE_ID = "DA-C9-003"
CODE = "C9"  # proposed new code: pages made for search traffic; here, a page made from a template for one value (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose reading found it (pyru and Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re
from collections import Counter

C9T_SENTENCE = re.compile(r"feel free to use our online unit conversion calculator", re.I)
C9T_HEADING = re.compile(r"^#{1,6}[ \t]+(.+)$", re.M)
# headings that only calculator and number-fact sites use
C9T_STRONG = re.compile(r"as geometric shapes|cryptographic hash functions|other arithmetic functions|basic calculations \(n ="
                       r"|alternative conversion|\bconverter\b|how to write / spell|decomposition of the number"
                       r"|mathematical representations and links|latest conversions of|roman system of writing numerals", re.I)
# headings a real lesson may use too: they count only next to a strong one
C9T_WEAK = re.compile(r"prime factori[sz]ation of|divisors of|divisibility of|classification of|base conversion"
                     r"|conversion table|percent off|approximate result|mathematical properties of", re.I)
C9T_NUMBER = re.compile(r"(?<![\w.])(\d{3,}(?:\.\d+)?|\d+\.\d+)(?![\w.])")
C9T_DOLLARS = re.compile(r"\\?\$(\d+(?:\.\d+)?)")
C9T_YEAR = re.compile(r"(?:19|20)\d\d")


def medicine_c9t(text):
    if C9T_SENTENCE.search(text):
        return True
    headings = C9T_HEADING.findall(text)
    if not headings:
        return False
    strong = {m.group().lower() for h in headings for m in C9T_STRONG.finditer(h)}
    weak = {m.group().lower() for h in headings for m in C9T_WEAK.finditer(h)}
    if strong and len(strong) + len(weak) >= 2:
        return True
    values = Counter()
    for h in headings:
        found = set(C9T_NUMBER.findall(h)) | {"$" + v for v in C9T_DOLLARS.findall(h)}
        values.update(v for v in found if not C9T_YEAR.fullmatch(v))
    if values:
        _, n = values.most_common(1)[0]
        if n >= 3 and 4 * n >= len(headings):
            return True
    return False


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c9t(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 8 of 9, all dropped. It misses `ec4ea0009df33e1a`.
4. **Harm test:** finemath 1.16% (1/86) PASS, at the limit; megamath 0.00% (0/26) PASS. The finemath gold doc it drops, `0f119a596e8b7f63`, is itself a converter template page. That gold contradiction is noted under the table at the top of this sheet.
5. **Side effects:**
   - A real lesson whose headings name one 3-digit number three times would be dropped ("Is 1001 prime?", "Factors of 1001", "Multiples of 1001").
   - So would a lesson that pairs a strong phrase with a weak one, such as a "converter" heading next to "Conversion table".
   - It misses template pages that have none of the Markdown headings it knows. In the reading, that is `ec4ea0009df33e1a`, the Bohr-model page of one element.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350). It was drafted as `DA-C6-101`, then `DA-C6-001`. On 12 Nov it moved to C9, beside SEO filler, because C6 is the Indic family's code. Both are pages made for search traffic.

## 3. `DA-C9-001` · C9 SEO filler · fix + drop · stage 30

1. **Disease:** NEW-seo-filler, 15 docs: pyru 10 and Satyanarayana 5. Examples: `053c7e6dfbdb4e46`, `085f9f7987b7cf56`, `0e2b9cc0beb5fb11`. These are pages written to rank in search, not to teach: tutoring and homework-app sales pages, exam-tips filler, route-distance pages and spun "ebook" pages.
2. **Medicine:**
   - **Drop** a doc that has a sentence only these pages write. The list covers the tutoring sales lines ("Find your perfect private math tutor", "is the world's leading network of private tutors", "Find an … Tutor" headings, "367 math teachers in …"), the homework-app lines ("App that will do your homework", "We solve all types of math problems"), the 6ya help line, the exam-shortcut filler, a "Road distance" heading, and the ebook spinner ("If you ally dependence such a referred …", "You may not be perplexed to enjoy …").
   - **Fix:** remove the "You are watching: …" line that copying sites add to an article. The rest of that article stays.

```python
RULE_ID = "DA-C9-001"
CODE = "C9"  # proposed new code: SEO filler (NEW_DISEASES.md)
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

# sentences that only SEO landing pages write: tutoring and homework-app sales, the 6ya help line, exam filler,
# route-distance pages and the "ebook" spinner
C9_DROP = re.compile("|".join((
    r"find your perfect (?:private )?(?:math |maths )?tutor",
    r"is the world'?s leading network of private tutors",
    r"^#*[ \t]*find an? [\w .'-]{2,40} tutor\b",
    r"\b\d+ (?:math|maths) (?:teachers|tutors) in\b",
    r"\bapp that will (?:do|solve) your (?:math |maths )?homework",
    r"we solve all types of math problems",
    r"\ba 6ya expert can help you",
    r"shortcut tricks are very important thing to know for your exams",
    r"^#*[ \t]*road distance\b",
    r"if you ally (?:dependence|need|obsession|craving|habit) such a referred",
    r"you may not be perplexed to enjoy",
)), re.I | re.M)
C9_INJECTED = re.compile(r"^[ \t]*you are watching:[^\n]*(?:\n|$)", re.I | re.M)
# Speed (14 Nov): every C9_DROP sentence holds one of these, and C9_INJECTED holds "you are watch". casefold() maps every
# character re.I matches to them (each is cut before any "i", which re.I also matches as a dotless "ı" that casefold()
# keeps), so a doc without them can't match, and the 11-way case-insensitive search is skipped.
C9_NEEDS = ("tutor", "teachers", "homework", "math problems", "6ya", "shortcut tr", "road d", "such a referred",
            "perplexed to enjoy")


def medicine_c9(text):
    low = text.casefold()
    if any(k in low for k in C9_NEEDS) and C9_DROP.search(text):
        return True
    if "you are watch" not in low:
        return text
    return C9_INJECTED.sub("", text)


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c9(doc["text"]), doc["text"])
```

3. **Action:** fix + drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 8 of 15 (7 dropped, 1 fixed).
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A real lesson that quotes one of these sales lines would be dropped.
   - SEO pages that don't use one of the listed sentences are missed, such as worksheet pages and question-heading pages.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

## 4. `DA-D6-001` · D6 machine-written text · fix + drop · stage 30

1. **Disease:** NEW-ai-generated-text, 8 docs, pyru (finemath), 3 of them marked "unsure". Examples: `10d547035dd610e2`, `36c3e8b4b4457083`, `8f1f8a9c194e88f2`. There are two kinds:
   - text a forum adds to a thread: an "In summary, the conversation discusses …" line, and a numbered FAQ at the end;
   - whole machine-written SEO articles.
2. **Medicine:**
   - **Fix (forum pages).** When a doc has the forum's "In summary, the conversation/discussion/thread …" line, remove that line. Also remove the numbered FAQ the forum adds: 4 or more questions numbered `1.`, `2.`, `3.`… in order, at most 8 lines apart, each ending in `?`. The block ends after the last question's answer, or at the next `•` navigation line or heading. The users' posts stay.
   - **Drop (machine-written articles).** Drop a doc that shows 2 or more of these signs:
     - FAQ headings (`FAQ 1:` or "Frequently Asked Questions")
     - a "Conclusion" heading
     - 3 or more headings that start "Introduction to", "Understanding" or "Benefits of"
     - a sentence starting "In summary," or "In conclusion,"

```python
RULE_ID = "DA-D6-001"
CODE = "D6"  # proposed new code: machine-written text (NEW_DISEASES.md)
ACTION = "fix+drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath"  # packs it runs on: the disease was found in finemath only
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath"  # pack whose reading found it (pyru, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

D6_FORUM_SUMMARY = re.compile(r"^[ \t]*In summary, the (?:conversation|discussion|thread)\b[^\n]*(?:\n|$)", re.M)
D6_QUESTION = re.compile(r"^[ \t]*(\d{1,2})\.[ \t]+[^\n]{5,200}\?[ \t]*$")
D6_NAV = ("\u2022", "#")  # a forum navigation bullet or a heading ends the FAQ
D6_GAP = 8  # questions of one FAQ are at most this many lines apart
D6_FAQ_HEAD = re.compile(r"^#{1,6}[ \t]*(?:FAQ[ \t]*\d+[ \t]*:|Frequently Asked Questions)", re.M | re.I)
D6_CONCLUSION = re.compile(r"^#{1,6}[ \t]*(?:In )?Conclusion[ \t]*:?[ \t]*$", re.M | re.I)
D6_ARTICLE_HEAD = re.compile(r"^#{1,6}[ \t]*(?:Introduction to|Understanding|Benefits of)\b", re.M)
D6_WRAP_UP = re.compile(r"(?:^|[.!?][ \t]+)In (?:summary|conclusion), [a-z]", re.M)


def _d6_faq(lines):
    """(start, end) of a numbered FAQ of 4+ questions in order, close together, each followed by its answer, or None."""
    for i, line in enumerate(lines):
        m = D6_QUESTION.match(line)
        if not m or m.group(1) != "1":
            continue
        want, last, j = 2, i, i + 1
        while j < len(lines) and j - last <= D6_GAP and not lines[j].strip().startswith(D6_NAV):
            m = D6_QUESTION.match(lines[j])
            if m and int(m.group(1)) == want:
                want, last = want + 1, j
            j += 1
        if want - 1 < 4:
            continue
        end = last + 1
        while end < len(lines) and not lines[end].strip():
            end += 1  # the blank lines after the last question
        while end < len(lines) and lines[end].strip() and not lines[end].strip().startswith(D6_NAV):
            end += 1  # its answer
        return i, end
    return None


def medicine_d6(text):
    if D6_FORUM_SUMMARY.search(text):
        text = D6_FORUM_SUMMARY.sub("", text)
        lines = text.split("\n")
        block = _d6_faq(lines)
        if block:
            lines = lines[:block[0]] + lines[block[1]:]
        return "\n".join(lines)
    signs = (len(D6_FAQ_HEAD.findall(text)) >= 1) + bool(D6_CONCLUSION.search(text)) \
        + (len(D6_ARTICLE_HEAD.findall(text)) >= 3) + bool(D6_WRAP_UP.search(text))
    return True if signs >= 2 else text


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_d6(doc["text"]), doc["text"])
```

3. **Action:** fix + drop. **Runs on:** finemath only, where the disease was found. **Reading docs it treats:** 3 of 8 (2 dropped, 1 fixed).
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath off.
5. **Side effects:**
   - A human-written lesson with a "Conclusion" heading and a closing "In conclusion, …" sentence would be dropped.
   - A machine-written article without these signs is missed, and so are the 3 "unsure" rows.
   - On a forum page, a real numbered list of 4 or more questions after the summary line would be removed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading, mittalutkarsh/era-v5-lab#2. If a machine summary comes from a closed model, the licence rule may exclude the whole doc. That is for the team to decide.

## 5. `DA-C7-001` · C7 content lost in extraction: formulas · drop · stage 30

1. **Disease:** NEW-missing-formulas, 29 docs: pyru 26 and Satyanarayana 3. Examples: `0614bc6ecf034495`, `06f2d75b8c5610f1`, `0e89fda818263262`. Formula images and symbols were lost when the page was turned into text. What is left can't be followed, as in "the number of fish in tank B =", "Use Binet's formula to show that .", "Comparing , we can see".
2. **Medicine:** count the gaps that a lost formula leaves, and drop the doc at 4 or more. The gaps it counts:
   - a line that ends in `=`, or in a word that needs what comes after it (`is`, `of`, `that`, `therefore`, `get`…), when the next line starts a new sentence instead of carrying on. A next line carries on when it starts with a value, a lowercase letter (a wrapped line, or `a^2 + a = 0`), an answer option or a bullet, or when it holds `=` or `^`.
   - a word that needs an object, followed straight by `.`, `,` or `;` (`show that .`, `write as .`, `Comparing , we`, `and .`)
   - an empty answer option: a line holding only `(A)`, `B.` and the like, followed by another such line or by nothing
   - a `?` where a value should be (`radius: ?`, `= ?`), or `???`

   Nothing can put the formula back, so the medicine is a drop.

```python
RULE_ID = "DA-C7-001"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7_EQ_END = re.compile(r"=[ \t]*$")
C7_DANGLING = re.compile(r"\b(?:is|are|was|of|that|by|be|as|equals|gives|get|obtain|therefore|becomes)[ \t]*$", re.I)
C7_VALUE = re.compile("^[ \t]*[-+\\d(−√$\\\\]")  # the next line starts with a value: the formula is there
# the next line carries on: lowercase (a wrapped line or "a^2 + a = 0"), an answer option, a bullet, or a formula
C7_CONTINUES = re.compile("^[ \t]*(?:[a-z]|\\(?[A-Da-d][).][ \t]|[-*•])|[=^]")
C7_NO_OBJECT = re.compile(r"\b(?:is|are|as|that|of|to|by|be|get|gives?|obtain|equals?|becomes?|write|find|show|compute"
                          r"|calculate|evaluate|simplify|solve|comparing|where|and|or|then|than|with|for)[ \t]+[.,;](?=[ \t]|$)",
                          re.M | re.I)
C7_OPTION = re.compile(r"^[ \t]*\(?[A-Da-d][).][ \t]*$")
C7_QUESTION_MARK = re.compile(r"[:=][ \t]*\?[ \t]*$|(?<!\?)\?{3,}", re.M)
C7_MIN_GAPS = 4  # the most gaps in a gold doc is 3; the reading docs it drops have 4 to over 100
# Speed (14 Nov). C7_NO_OBJECT needs a space or tab before . , or ;, and C7_QUESTION_MARK needs a "?": without them
# each counts 0. A line adds a gap only if it ends in "=" or a dangling word, or is an empty answer option:
# C7_CANDIDATE finds such a line anywhere in the text, so without one the line loop adds nothing. And the count
# only grows, so once it reaches C7_MIN_GAPS the answer is known.
C7_SPACE_PUNCT = re.compile(r"[ \t][.,;]")
C7_CANDIDATE = re.compile("|".join(p.pattern for p in (C7_EQ_END, C7_DANGLING, C7_OPTION)), re.I | re.M)


def medicine_c7(text):
    gaps = len(C7_NO_OBJECT.findall(text)) if C7_SPACE_PUNCT.search(text) else 0
    if "?" in text:
        gaps += len(C7_QUESTION_MARK.findall(text))
    if gaps >= C7_MIN_GAPS:
        return True
    if not C7_CANDIDATE.search(text):
        return False
    lines = [line for line in text.split("\n") if line.strip()]
    for k, line in enumerate(lines):
        nxt = lines[k + 1] if k + 1 < len(lines) else ""
        if (C7_EQ_END.search(line) or C7_DANGLING.search(line)) and not (C7_VALUE.match(nxt) or C7_CONTINUES.search(nxt)):
            gaps += 1  # "... tank B =" or "... the parallel line is", then a new sentence: the formula is gone
        if C7_OPTION.match(line) and (not nxt or C7_OPTION.match(nxt)):
            gaps += 1  # an answer option with nothing in it
    return gaps >= C7_MIN_GAPS


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c7(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 4 of 29, all dropped. Most of the other 25 show none of these signs: their formulas were dropped mid-sentence, leaving no gap a rule can see.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A doc with 1 to 3 gaps is kept, even though those formulas are lost too.
   - Earlier versions counted lines that don't end at a gap, and so dropped gold docs:
     - option labels above their options, and `=` with the answer on the next line (`8828b7bee424578d`, `e238227f95913a28`);
     - question stems before their options (`1d47bc0cfcb2c463`);
     - "gives" before an equation (`505b2d2be1ef9b8f`);
     - "These are" before a bullet list (`c483df6e3fd9f283`);
     - a hard-wrapped line (megamath `14f21801b0ecf71e`).

     None of these counts now. Gold `5323283b31159262` has 3 gaps (a sentence ending "in worst case is" before a new sentence), so it is kept, at a cut of 4.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

## 6. `DA-C7-002` · C7 content lost in extraction: figures · drop · stage 30

1. **Disease:** NEW-missing-figures, 5 docs, Satyanarayana (megamath). Examples: `019fda08843696eb`, `03aeffcf72c72418`, `0ab64ed894610ef7`. The problem refers to a figure, plot or drawing that isn't in the text: "Figure P9.26 shows the thrust", "the truss shown below".
2. **Medicine:** drop the doc when it refers to a missing picture twice, or once in a short doc (under 2,000 characters), where the problem can't be done without it. A reference is one of these:
   - "figure", "diagram", "graph", "picture", "image", "plot", "truss", "circuit" or "drawing", followed within the sentence by "below", "above", "shown", "shows" or "given"
   - "shown below" / "shown above", or "shown in the figure"
   - a numbered figure such as `Figure 3.12`

```python
RULE_ID = "DA-C7-002"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-megamath"  # packs it runs on: the disease was found in megamath only
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-megamath"  # pack whose reading found it (Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7F_REF = re.compile(r"\b(?:figure|fig\.|diagram|graph|picture|image|plot|truss|circuit|drawing)s?\b[^.\n]{0,60}?"
                     r"\b(?:below|above|shown|shows|given)\b"
                     r"|\b(?:shown|given|pictured|illustrated) (?:below|above|in the (?:figure|diagram|graph|picture))\b"
                     r"|\bfig(?:ure|\.) ?[A-Z]?\d+(?:\.\d+)*\b", re.I)
C7F_SHORT = 2000


def medicine_c7f(text):
    refs = len(C7F_REF.findall(text))
    return refs >= 2 or (refs == 1 and len(text) < C7F_SHORT)


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c7f(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** megamath only, where the disease was found. **Reading docs it treats:** 4 of 5, all dropped. It misses `ea37d46cbd5f339c`, whose missing figure isn't named by any of these phrases.
4. **Harm test:** megamath 0.00% (0/26) PASS; finemath off.
5. **Side effects:**
   - A long lesson that mentions two figures would be dropped, even if the text can be followed without them.
   - A reference worded another way is missed, such as "the preview images".
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Satyanarayana's megamath reading, theschoolofai/era-v5-lab#350. It may be folded into `DA-C7-001` if the team agrees.

## 7. `DA-C8-001` · C8 layout lost in extraction: flattened formulas · drop · stage 30

1. **Disease:** NEW-flattened-formulas, 22 docs: pyru 20 and Satyanarayana 2. Examples: `033ab42a96110ff9`, `0f2f052fd95da6d4`, `1ab888d9366a43fd`. The formula's layout is gone. Either superscripts and subscripts sit on the base line (`x2` for `x²`), or every token of a formula is on its own line.
2. **Medicine:** drop the doc when a formula has been broken into 8 or more lines in a row (blank lines between them are skipped). Each such line holds 1–3 characters: digits, single letters or operators. At least 2 of the lines must hold an operator (`+ - = ( ) / × ÷ √ ≤ ≥`…), so a column of plain numbers, such as a forum's post counts, doesn't count. An answer-option label on its own line, such as `(a)`, breaks the run: the first version counted options set out one per line (gold `8828b7bee424578d`). `x2` for `x²` can't be told from real text, so those docs are left alone.

```python
RULE_ID = "DA-C8-001"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8_TOKEN = re.compile(r"[A-Za-z0-9+\-=()\[\]/*^.,<>|\u2212\u00d7\u00f7\u221a\u2264\u2265\u2260]{1,3}")
C8_OPERATOR = re.compile(r"[+\-=()\[\]/*^<>\u2212\u00d7\u00f7\u221a\u2264\u2265\u2260]")
C8_OPTION = re.compile(r"\(?[A-Ea-e][).]")  # an answer-option label on its own line is not a piece of a formula
C8_MIN_RUN = 8


def medicine_c8(text):
    run = ops = 0
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue  # blank lines between the pieces do not break a run
        if C8_TOKEN.fullmatch(s) and not C8_OPTION.fullmatch(s):
            run += 1
            ops += bool(C8_OPERATOR.search(s))
            if run >= C8_MIN_RUN and ops >= 2:
                return True
        else:
            run = ops = 0
    return False


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c8(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 3 of 22, all dropped. Most of the 22 have superscripts flattened onto one line, which can't be told from real text.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A real column of short items with operators, such as a list of signs, would be dropped.
   - Flattened superscripts on one line (`x2`, `104` for 10⁴) are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).

## 8. `DA-C8-002` · C8 layout lost in extraction: merged table cells · drop · stage 30

1. **Disease:** NEW-merged-table-cells, 11 docs: pyru 10 and Satyanarayana 1. Examples: `06f2d75b8c5610f1`, `1b1c42eddd14c8e7`, `1e7fad525310d310`. A table has been flattened into running text, with its cell values run together on one line ("m n mod m 2 3 4 5 6 7 8 9 1 1 3 …", "3 + 4 = 7 7 − 3 = 4 4 + 3 = 7 …"). The columns are gone.
2. **Medicine:** drop the doc when it has a flattened table row: a line of 20 or more tokens, at least 80% of which are numbers (up to 4 digits, with an optional decimal part or `%`) or single operators. A table whose columns are lost can't be rebuilt, so the medicine is a drop. The first version needed 2 such rows and caught none of the 11 reading docs. Each of them has one such row, and no gold doc has a numeric line longer than 15 tokens.

```python
RULE_ID = "DA-C8-002"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
LANGS = {'en'}
ORIGIN = "math-finemath, math-megamath"  # packs it runs on: the disease was found in both
PACKS = set(ORIGIN.split(", "))  # the math packs share the "en" tag, so the pack is checked too
SOURCE = "math-finemath, math-megamath"  # packs whose reading found it (pyru, Satyanarayana, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8T_CELL = re.compile(r"[-+]?\d{1,4}(?:[.,]\d+)?%?|[+\-=\u2212\u00d7\u00f7x*/]")
C8T_MIN_TOKENS = 20
C8T_SHARE = 0.8
C8T_MIN_ROWS = 1  # each reading doc has one such row; no gold doc has a numeric line of 20+ tokens (the longest is 15)


# Speed (14 Nov): one regex pass counts the whitespace-separated tokens C8T_CELL matches whole, instead of a Python
# loop over the tokens. (?<!\S) and (?!\S) make a match start and end at a token's edges: \s and str.split() use the
# same whitespace.
C8T_TOKEN = re.compile(r"(?<!\S)(?:" + C8T_CELL.pattern + r")(?!\S)")


def _c8t_flat_row(line):
    tokens = line.split()
    if len(tokens) < C8T_MIN_TOKENS:
        return False
    return len(C8T_TOKEN.findall(line)) >= C8T_SHARE * len(tokens)


def medicine_c8t(text):
    return sum(1 for line in text.split("\n") if _c8t_flat_row(line)) >= C8T_MIN_ROWS


def _std(out, text):
    # the result in the shared form: str -> fix/keep, ("drop", ...), None or True -> drop
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, tuple) and out and out[0] == "drop": return ("drop", text)
    return ("fix" if out != text else "keep", out)


def medicine(doc):
    if doc.get("lang_label") not in LANGS or doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return _std(medicine_c8t(doc["text"]), doc["text"])
```

3. **Action:** drop. **Runs on:** finemath, megamath. **Reading docs it treats:** 3 of 11, all dropped.
4. **Harm test:** finemath 0.00% (0/86) PASS; megamath 0.00% (0/26) PASS.
5. **Side effects:**
   - A doc with one long line of numbers would be dropped, for example a data set of 20 values, or a sum written out as `1 + 2 + … + 10 = 55`.
   - Tables flattened one cell per line, or mixed with words, are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: pyru's finemath reading (mittalutkarsh/era-v5-lab#2) and Satyanarayana's megamath reading (theschoolofai/era-v5-lab#350).
