# medicine_sci: science medicines for the Spec v1.1 new diseases

**Draft, 12 Nov; sections 7–12 added 13 Nov.** This sheet has one rule for each of the 12 new science diseases in `NEW_DISEASES.md`. These are diseases that aren't in `DISEASES.md` and that turn up in 1% or more of the 200 science docs read, which is 2 docs: 100 read by Aditeya (mittalutkarsh/era-v5-lab#3) and 100 by Utkarsh (mittalutkarsh/era-v5-lab#5). Sections 1–6 come from Aditeya's reading. Sections 7–12 were added once Utkarsh's reading was included, and come from it (section 9 from both). Reasons and choices are in `decisions_sci.md`.

- **Pack.** sci-finepdfs has 202 gold docs (Data A gold).
- **Limit.** Docs changed plus dropped: at most `max(1, floor(1% of 202))` = 2 docs.
- **Rule form.** As the v1 sci rules: `doc = {doc_id, text, url, lang_label, pack_id}`, and `medicine(doc)` returns `(action, text)`. Each rule checks `pack_id` only, not `lang_label`, because sci-finepdfs holds more than one language. A doc with no `pack_id` passes unchanged.
- **Codes and IDs.** They come from `NEW_DISEASES.md`. Every code here is a proposed new code.
- **Run order.** These rules run after the sci family's v1 rules, because the reader found the diseases in v1-cleaned text. Within this sheet they run in section order: stage 10 (characters), then stage 30 (source), with the drops first and then the strips. Sections 7–12 were added at the end, in the same pattern among themselves, so sections 1–6 keep their numbers.
- **Every reading row so far is AI-suggested.** The hand check of the examples comes before a rule is final.

The last column counts the reading docs with the rule's code that it changes or drops, on the cleaned sample the reader read (`scripts/reading_recall.py`).

| # | ID | disease | action | stage | sci-finepdfs | reading docs treated |
|---|---|---|---|---|---|---|
| 1 | `DA-A7-001` | A7 word split at a line-end hyphen (NEW-hyphen-split-words) | fix | 10 | 0.50% (1/202) PASS | 3 / 3 |
| 2 | `DA-C9-002` | C9 SEO filler (NEW-seo-filler) | drop | 30 | 0.00% (0/202) PASS | 2 / 2 |
| 3 | `DA-B6-001` | B6 blank form fields (NEW-underscore-blanks) | drop | 30 | 0.00% (0/202) PASS | 2 / 2 |
| 4 | `DA-C7-003` | C7 content lost in extraction: table body or list (NEW-missing-table-data) | fix | 30 | 0.00% (0/202) PASS | 1 / 3 |
| 5 | `DA-C8-004` | C8 layout lost in extraction: reading order (NEW-reading-order) | fix | 30 | 0.00% (0/202) PASS | 1 / 2 |
| 6 | `DA-C8-003` | C8 layout lost in extraction: merged table cells (NEW-merged-table-cells) | fix | 30 | 0.00% (0/202) PASS | 1 / 3 |
| 7 | `DA-A7-002` | A7 word split in extraction: drop cap (NEW-drop-cap-split) | fix | 10 | 0.00% (0/202) PASS | 1 / 2 |
| 8 | `DA-A7-003` | A7 word split in extraction: small caps (NEW-small-caps-split) | fix | 10 | 0.00% (0/202) PASS | 2 / 2 |
| 9 | `DA-A8-002` | A8 words run together: field labels (NEW-missing-spaces) | fix | 10 | 0.00% (0/202) PASS | 1 / 3 |
| 10 | `DA-C7-005` | C7 content lost in extraction: near-empty doc (NEW-near-empty) | drop | 30 | 0.50% (1/202) PASS | 2 / 2 |
| 11 | `DA-C7-004` | C7 content lost in extraction: figures (NEW-missing-figures) | fix | 30 | **1.49% (3/202) FAIL**: all 3 are gold contradictions | 2 / 2 |
| 12 | `DA-C8-005` | C8 layout lost in extraction: page numbers and footers (NEW-page-artifact) | fix | 30 | 0.00% (0/202) PASS | 8 / 9 |
| | all in order | sections 1–6 (12 Nov) | | | **0.50% (1/202) PASS** | |
| | all in order | sections 1–12 (13 Nov) | | | **2.48% (5/202) FAIL**: 4 of the 5 are gold contradictions | |

**Harm runs, 13 Nov (sections 1–12).** Report: `results/sheets/sci-finepdfs_harm.json`, from the second run. Sections 1–6 give the same results as on 12 Nov.
- **First run:** two rules failed alone and the run in order failed. `DA-A7-003` changed 3 gold docs, `DA-C7-004` changed 3, `DA-C7-005` dropped 1 and `DA-C8-005` changed 1. In order: 9/202.
- **The 8 gold docs, read the same day:**
  - `DA-A7-003`, **real harm**: `322dc47ddcb0a780` (`G HIST 11050` → `GHIST`, course codes), `b31b17ba09b9a8b8` (`ENACTING A COMPREHENSIVE` → `ACOMPREHENSIVE`, `D AND E` → `DAND E`), `d8df5df66bb7a574` (`CECILY’S ENGLISH` → `CECILY’SENGLISH`). The rule was narrowed to lines set in small caps (section 8).
  - `DA-C8-005`, **real harm**: `8a2493cdf33f9a38` lost the date under each signed comment (`4/21/20`). The rule was narrowed: a date footer must stand alone between blank lines.
  - `DA-C7-004`, **gold contradictions**: `4b958ac1f45443b5`, `d0a0a41263e845f5` and `eb6ad9726f2d7ddd` each have empty image links, which is the disease itself. The first version also deleted their captions (a figure legend, compound names), so it was changed to keep the caption as text. Every version changes these 3 docs.
  - `DA-C7-005`, **false positive within the limit**: `b6fd81dbf90b0d17` is a complete 220-character certificate, not a header with a lost body. It can't be told from the reading docs by length (96 and 233 characters), so it stays a recorded side effect.
- **Second run:** `DA-A7-003` and `DA-C8-005` touch 0 gold docs, and catch the same reading docs as before (2/2 and 8/9). `DA-C7-004` still fails at 3/202, all gold contradictions. In order: 5/202 FAIL: the 3 above, `920855df51f37db8` (`DA-A7-001`, a gold contradiction from 12 Nov) and `b6fd81dbf90b0d17`.
- **With the gold contradictions left out** (Vijay agreed to marking them), `DA-C7-004` passes at 0/199, and the run in order passes at 1/198 (`b6fd81dbf90b0d17`).

**Harm run, 12 Nov.** Report: `results/sheets/sci-finepdfs_harm.json`. Every rule passes, alone and in order.
- **The one gold doc touched.** `920855df51f37db8` (`DA-A7-001`) is a Finnish abstract with a word split at a line-end hyphen. So the disease itself is sitting in the gold set. This is within the limit, so it needs no ruling. It is recorded as a gold contradiction, like the two in finemath (aneeshads, 13 Nov), and flagged for a re-read at the next gold refresh.
- **An earlier fix.** The first version of `DA-B6-001` dropped 4 gold docs at a 10% threshold. It was raised to 30%.
- **Taken out.** A ligature rule (A5) and a table-of-contents rule (C1) came out on 12 Nov, because both diseases are in `DISEASES.md`.

Each section below follows the spec v1 card:
1. **Disease:** code, count and examples by doc_id.
2. **Medicine:** in words, then the python block.
3. **Action** and the packs it runs on.
4. **Harm test.**
5. **Side effects.**
6. **Spec v1.1:** status, author, source.

## 1. `DA-A7-001` · A7 word split at a line-end hyphen · fix · stage 10

1. **Disease:** NEW-hyphen-split-words, 3 docs, Aditeya. The line-end hyphen was kept and the line break became a space. Examples:
   - `5a201c19575522f9`: `company- owned`, `performance- based`
   - `75768b1b6b165557`: `stereo- scopic`
   - `93412124dc441459`: `day- to-day`
2. **Medicine:**
   - **What it joins:** a word of 2 or more letters, then `- `, then a lowercase word. The space goes and the hyphen stays: `stereo-scopic`. With no word list it can't tell `stereoscopic` from a real compound, so it never drops the hyphen.
   - **What it leaves alone:** suspended hyphens, where the next word is `and`, `or`, `nor`, `to`, `through`, `versus` or `vs` followed by a space (`pre- and post-test`, `two- to three-fold`).
   - **`day- to-day`** becomes `day-to-day`, because there `to` is followed by a hyphen.

```python
RULE_ID = "DA-A7-001"
CODE = "A7"  # proposed new code: a word split at a line-end hyphen (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A7_SPLIT = re.compile(r"\b([A-Za-z]{2,})- ([a-z]{2,})\b(-?)")
A7_SUSPENDED = {"and", "or", "nor", "to", "through", "versus", "vs"}  # "pre- and post-test", "two- to three-fold"


def _a7_join(m):
    left, right, hyphen = m.groups()
    if right in A7_SUSPENDED and not hyphen:
        return m.group()
    return left + "-" + right + hyphen


def medicine_a7(text):
    if "- " not in text:  # speed (14 Nov): A7_SPLIT needs a hyphen and a space
        return text
    return A7_SPLIT.sub(_a7_join, text)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a7(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 3 of 3, all fixed.
4. **Harm test:** sci-finepdfs 0.50% (1/202) PASS. The one gold doc it changes, `920855df51f37db8`, has the disease itself.
5. **Side effects:**
   - A hyphen used as a dash with no space before it is joined to the next word: `it was late- we left` becomes `late-we`.
   - A word that was really split, such as `stereo-scopic`, keeps a hyphen it shouldn't have.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3. Drafted as `DA-A7-101`.

## 2. `DA-C9-002` · C9 SEO filler · drop · stage 30

1. **Disease:** NEW-seo-filler, 2 docs, Aditeya. These are "ebook" pages made by a text spinner: the keyword title is repeated, there's no real content, and some carry `Page n/N` markers. Examples:
   - `d8a1ed9b1607a1dd`: "If you ally dependence such a referred … book"
   - `365b8539483e5a3f`: "access free ebook", `Page n/33`

   Math has 15 more, with their own rule, `DA-C9-001`.
2. **Medicine:** drop a doc that matches either of these:
   - it has a sentence that only the ebook spinner writes: "If you ally dependence such a referred …", "You may not be perplexed to enjoy …", "every ebook collections … that we will extremely offer", "access/download/read free ebook", "acquire the enormously best seller from us", "Right here, we have countless books …";
   - it has 5 or more `Page n/N` markers and mentions "ebook".

```python
RULE_ID = "DA-C9-002"
CODE = "C9"  # proposed new code: SEO filler (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

# sentences that only the "ebook" text spinner writes
C9S_SPINNER = re.compile("|".join((
    r"if you ally (?:dependence|need|obsession|craving|habit) such a referred",
    r"you may not be perplexed to enjoy",
    r"\bebook collections?\b[^\n]{0,120}\bthat we will (?:extremely|unconditionally|very|totally) offer",
    r"\b(?:access|download|read) (?:free|this) ebook\b",
    r"acquire the (?:enormously|extremely) best seller from us",
    r"right here, we have countless (?:books?|ebooks?)\b",
)), re.I)
C9S_PAGE = re.compile(r"\bPage \d+/\d+\b")
C9S_MIN_PAGES = 5
# Speed (14 Nov): every spinner sentence, and the page test, needs one of these. casefold() maps every character that
# re.I matches to these letters, so a doc without any of them can't match, and the slow search is skipped.
C9S_NEEDS = ("such a referred", "perplexed to enjoy", "ebook", "best seller from us", "we have countless")


def medicine_c9s(text):
    low = text.casefold()
    if not any(k in low for k in C9S_NEEDS):
        return False
    if C9S_SPINNER.search(text):
        return True
    return "ebook" in text.lower() and len(C9S_PAGE.findall(text)) >= C9S_MIN_PAGES


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return ("drop", doc["text"]) if medicine_c9s(doc["text"]) else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** sci-finepdfs. **Reading docs it treats:** 2 of 2, both dropped.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A real paper that quotes one of these sentences would be dropped.
   - SEO pages that don't use one of the listed sentences are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

## 3. `DA-B6-001` · B6 blank form fields · drop · stage 30

1. **Disease:** NEW-underscore-blanks, 2 docs, Aditeya: `3b2c0420a33ccaab` (a blank questionnaire) and `d8e3f724095e4aaa` (a blank permit form). In both, long runs of underscores mark the blanks and make up much of the text.
2. **Medicine:** drop the doc when underscore runs (5 or more `_` in a row) make up 30% or more of its non-space characters. A blank form has labels but no content. The two reading docs are at 31% and 63%. The highest gold doc is at 26%: the first version, at 10%, dropped 4 gold docs.

```python
RULE_ID = "DA-B6-001"
CODE = "B6"  # proposed new code: blank form fields (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

B6_RUN = re.compile(r"_{5,}")
B6_SHARE = 0.30  # the reading docs are at 0.31 and 0.63; the highest gold doc is at 0.26
B6_SPACE = re.compile(r"\s")  # \s is str.isspace(): both use the same Unicode whitespace test


def medicine_b6(text):
    if "_____" not in text:  # speed (14 Nov): no blank, so it can't reach the share
        return False
    chars = len(text) - len(B6_SPACE.findall(text))  # non-space characters, in one pass, not a Python loop
    blanks = sum(len(m.group()) for m in B6_RUN.finditer(text))
    return chars > 0 and blanks >= B6_SHARE * chars


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return ("drop", doc["text"]) if medicine_b6(doc["text"]) else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** sci-finepdfs. **Reading docs it treats:** 2 of 2, both dropped.
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A worksheet with many fill-in lines would be dropped as well.
   - The margin is small: 31% for one reading doc against 26% for the highest gold doc.
   - A form whose blanks are boxes or dots, not underscores, is missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

## 4. `DA-C7-003` · C7 content lost in extraction: table body or list · fix · stage 30

1. **Disease:** NEW-missing-table-data, 3 docs, Aditeya. A table or list was an image or a PDF object and was dropped, while the line that introduces it remained. Examples:
   - `0863ac75c9ec153e`: a table heading with no numbers
   - `4a33733776358fac`: "… is constituted with the following members." with no members after it
   - `fac0d63aba9fab0c`: action-plan column headings with no rows
2. **Medicine:** when a line ends by announcing a list of people ("the following members." / "the following persons:" and the like), and the next non-blank line is not a list, the dangling clause is cut and the sentence ends there: "… is constituted with the following members." becomes "… is constituted.". The next line counts as a list when it starts with a bullet, number, letter, `|`, or is shorter than 60 characters, as a name would be. Headings with no data can't be told from real headings, so they are left.

```python
RULE_ID = "DA-C7-003"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7T_NOUNS = r"(?:members|persons|names|people|officials|officers|staff|students|participants|candidates)"
C7T_INTRO = re.compile(r"[ \t]*\b(?:(?:with|of|are|is|as|by)[ \t]+)?the following " + C7T_NOUNS + r"[ \t]*[.:][ \t]*$", re.I)
C7T_LIST = re.compile(r"^[ \t]*(?:[-*|•●▪]|\(?\d{1,2}[.)]|\(?[A-Za-z][.)][ \t])")
C7T_SHORT = 60
# Speed (14 Nov): C7T_INTRO needs "the following " and a noun. These cut each noun before any "i", because re.I also
# matches a dotless "ı" that casefold() keeps, so a doc without any of them can't match.
C7T_NEEDS = tuple("the following " + n for n in ("member", "person", "name", "people", "off", "staff", "student",
                                                  "part", "cand"))


def _c7t_is_list(line):
    return bool(C7T_LIST.match(line)) or len(line.strip()) < C7T_SHORT


def medicine_c7t(text):
    low = text.casefold()
    if not any(k in low for k in C7T_NEEDS):  # skip the line loop
        return text
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not C7T_INTRO.search(line):
            continue
        nxt = next((l for l in lines[i + 1:] if l.strip()), None)
        if nxt is None or not _c7t_is_list(nxt):
            lines[i] = C7T_INTRO.sub(".", line)
    return "\n".join(lines)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c7t(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 of 3 (`4a33733776358fac`).
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A list that really does follow, written as running prose, loses its introducing clause.
   - Table headings with no data and other lost lists are left as they are.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

## 5. `DA-C8-004` · C8 layout lost in extraction: reading order · fix · stage 30

1. **Disease:** NEW-reading-order, 2 docs, Aditeya:
   - `ef812364b6cca7a0`: numbered steps extracted as 3, 5, 4
   - `e4d1400f9236b8c9`: a sentence split into parts that are scrambled across lines
2. **Medicine:** in a block of 3 or more lines in a row that each start with a step number (`3. …`), check the numbers. If they are a set of consecutive numbers, each used once, but are neither ascending nor descending, the lines are put back in number order. Scrambled sentences can't be put back, so they are left.

```python
RULE_ID = "DA-C8-004"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8O_STEP = re.compile(r"^[ \t]*(\d{1,2})\.[ \t]+\S")
C8O_MIN_BLOCK = 3


def _c8o_reorder(block):
    nums = [int(C8O_STEP.match(line).group(1)) for line in block]
    if sorted(nums) != list(range(min(nums), min(nums) + len(nums))):
        return block  # not one run of consecutive step numbers
    if nums == sorted(nums) or nums == sorted(nums, reverse=True):
        return block  # already in order, or counting down on purpose
    return [line for _, line in sorted(zip(nums, block))]


def medicine_c8o(text):
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        j = i
        while j < len(lines) and C8O_STEP.match(lines[j]):
            j += 1
        if j - i >= C8O_MIN_BLOCK:
            out += _c8o_reorder(lines[i:j])
        else:
            out += lines[i:max(j, i + 1)]
        i = max(j, i + 1)
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c8o(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 of 2 (`ef812364b6cca7a0`).
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A numbered list that is out of order on purpose (a list of rankings, say) is put back in number order.
   - Steps separated by blank lines or other text are not checked.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

## 6. `DA-C8-003` · C8 layout lost in extraction: merged table cells · fix · stage 30

1. **Disease:** NEW-merged-table-cells, 3 docs, Aditeya. Examples:
   - `6cdcf2807cbf5156`: `| Female | 332 50.4 |  | 48.5 |`, where the count and the percent ended up in one cell and the next cell was left empty
   - `680400a6c14bde86`: a row with one cell too many
   - `6deaff0b02c57734`: a spec table flattened into separate lines

   Math has 11 more, with their own rule, `DA-C8-002`.
2. **Medicine:** in a Markdown table row, a cell that holds exactly two numbers and is followed by an empty cell is split, with the second number moved into the empty cell: `| 332 50.4 |  |` becomes `| 332 | 50.4 |`. Shifted rows and tables flattened into lines can't be put back, so they are left.

```python
RULE_ID = "DA-C8-003"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8C_NUM = r"-?\d[\d,]*(?:\.\d+)?%?"
C8C_PAIR = re.compile(r"\|[ \t]*(" + C8C_NUM + r")[ \t]+(" + C8C_NUM + r")[ \t]*\|[ \t]*(?=\|)")


def medicine_c8c(text):
    out = []
    for line in text.split("\n"):
        if line.lstrip().startswith("|"):
            line = C8C_PAIR.sub(lambda m: "| " + m.group(1) + " | " + m.group(2) + " ", line)
        out.append(line)
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c8c(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** 1 of 3 (`6cdcf2807cbf5156`).
4. **Harm test:** sci-finepdfs 0.00% (0/202) PASS.
5. **Side effects:**
   - A cell that really holds two numbers, such as a range `10 20`, followed by an empty cell would be split.
   - Shifted rows (`680400a6c14bde86`) and flattened tables (`6deaff0b02c57734`) are not fixed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's sci-finepdfs reading, mittalutkarsh/era-v5-lab#3.

## 7. `DA-A7-002` · A7 word split in extraction: drop cap · fix · stage 10

1. **Disease:** NEW-drop-cap-split, 2 docs, Utkarsh. A large first letter (a drop cap) was extracted as a line of its own, or lost. Examples:
   - `94f54a2af0a8c897`: `D` on its own line, then `eveloping a Resort and Leisure Ministries Committee`
   - `768ce30e6fac2306`: the drop cap is gone, so `St. Thomas` reads `t. Thomas`
2. **Medicine:** a line that holds one capital letter and nothing else is joined to the next non-blank line, when that line starts with 2 or more lowercase letters and is at least 20 characters long: `D` + `eveloping a Resort …` becomes `Developing a Resort …`. `A` and `I` are left alone, because they are words (`A` / `new approach …`). A lost drop cap can't be put back, so `t. Thomas` is left.

```python
RULE_ID = "DA-A7-002"
CODE = "A7"  # proposed new code: a word split in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A7D_CAP = re.compile(r"^[ \t]*([B-HJ-Z])[ \t]*$")  # one capital letter alone on a line; A and I are words
A7D_REST = re.compile(r"^[ \t]*[a-z]{2,}")
A7D_MIN = 20  # the line it joins must be running text, not a table cell


def medicine_a7d(text):
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        m = A7D_CAP.match(lines[i])
        if m:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and A7D_REST.match(lines[j]) and len(lines[j].strip()) >= A7D_MIN:
                out.append(m.group(1) + lines[j].lstrip())
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a7d(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** see the table at the top.
4. **Harm test:** see the table at the top.
5. **Side effects:**
   - A single capital letter in a list or a form, followed by a long lowercase line, is joined to it.
   - Drop caps `A` and `I` are missed, and so are lost drop caps.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

## 8. `DA-A7-003` · A7 word split in extraction: small caps · fix · stage 10

1. **Disease:** NEW-small-caps-split, 2 docs, Utkarsh. Text set in small caps was extracted with the first letter of each word split off. Examples:
   - `feaaf0b7ad58777d`: `F OODS L IMITED`, `V IJAYA K UMAR`
   - `5b348d724c744d07`: `L AKEVILLE S OUTH H IGH S CHOOL`, `S TUDENT A NNOUNCEMENTS`, `M AY 27, 2022`
2. **Medicine:** a capital letter, a space, then 2 or more capitals (`F OODS`) is one split word, and the space goes: `FOODS`. It only works on a line set in small caps, which means all three of these:
   - the line has no lowercase letter (a course list such as `G CHEM 10050 | General Chemistry` has some);
   - it has more split pairs than whole capital words of 3 or more letters (`… ENACTING A REVISED CODE … D AND E` has many whole words);
   - the letter doesn't follow an apostrophe (`MARY’S ENGLISH` is a possessive).

   It only runs on a doc with 3 or more such splits, not counting `A` and `I`. On a small-caps line it joins every split, `A NNOUNCEMENTS` included. **Narrowed on 13 Nov:** the first version changed 3 gold docs (`G HIST` → `GHIST`, `A COMPREHENSIVE` → `ACOMPREHENSIVE`, `CECILY’S ENGLISH` → `CECILY’SENGLISH`).

```python
RULE_ID = "DA-A7-003"
CODE = "A7"  # proposed new code: a word split in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A7S_PAIR = re.compile(r"(?<![\w’'])([A-Z]) ([A-Z]{2,})\b")  # not after an apostrophe: MARY’S ENGLISH
A7S_WORDS = {"A", "I"}  # one-letter words: joined only on a small-caps line
A7S_MIN_DOC = 3  # splits on small-caps lines in the doc, not counting A and I
A7S_WHOLE = re.compile(r"\b[A-Z]{3,}\b")
A7S_LOWER = re.compile(r"[a-z]")  # speed (14 Nov): on an ASCII line, a lowercase letter is one of a-z


def _a7s_pairs(line):
    return sum(1 for m in A7S_PAIR.finditer(line) if m.group(1) not in A7S_WORDS)


def _a7s_small_caps(line):
    """No lowercase letter, and more split pairs than whole capital words."""
    # speed (14 Nov): one regex search on an ASCII line instead of a Python loop over its characters
    if A7S_LOWER.search(line) if line.isascii() else any(ch.islower() for ch in line):
        return False
    pairs = _a7s_pairs(line)
    return pairs > 0 and pairs > len(A7S_WHOLE.findall(A7S_PAIR.sub(" ", line)))


def _a7s_join(line):
    while True:
        new = A7S_PAIR.sub(lambda m: m.group(1) + m.group(2), line)
        if new == line:
            return line
        line = new


def medicine_a7s(text):
    lines = text.split("\n")
    small = [_a7s_small_caps(line) for line in lines]
    if sum(_a7s_pairs(line) for line, s in zip(lines, small) if s) < A7S_MIN_DOC:
        return text
    return "\n".join(_a7s_join(line) if s else line for line, s in zip(lines, small))


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a7s(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** see the table at the top.
4. **Harm test:** see the table at the top.
5. **Side effects:**
   - A short all-capitals line made mostly of letter-and-word pairs, such as `ZONES D AND E`, is joined when the doc has 3 or more such splits.
   - Small caps mixed with lowercase on one line are missed.
   - `M R .` (`MR.`) stays split, because only one letter follows the `M`.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

## 9. `DA-A8-002` · A8 words run together: field labels · fix · stage 10

1. **Disease:** NEW-missing-spaces, 3 docs: Aditeya 1, Utkarsh 2. Words or fields were run together with no space. Examples:
   - `4a6a549c3ead2ceb`: `MACEDuration:  On-goingCurrent Value:`
   - `48ffcdfea0bdbaf7`: `NEILABERCROMBIEGOVERNOR`
   - `f163172e98bdaa35`: `www.ct.gov/dcpDivision`

   Math has 13 more, with their own rule, `DA-A8-001`.
2. **Medicine:** a space goes back in front of a known field label that is glued to the word before it and followed by a colon: `MACEDuration:` becomes `MACE Duration:`, and `On-goingCurrent Value:` becomes `On-going Current Value:`. The labels are listed (`Duration`, `Current Value`, `Client`, `Date`, `Phone`, `Email` and the like), so camel-case words such as `JavaScript:` stay. Capitals run together (`NEILABERCROMBIEGOVERNOR`) and URLs can't be split without a word list, so they are left.

```python
RULE_ID = "DA-A8-002"
CODE = "A8"  # proposed new code: words run together (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "10"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Aditeya and Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

A8L_LABELS = ("Current Value", "Contract Value", "Duration", "Value", "Client", "Location", "Date", "Status",
              "Contact", "Telephone", "Tel", "Phone", "Fax", "E-Mail", "Email", "Address", "Website", "Web site",
              "Project", "Sector", "Programme", "Cost")
A8L_GLUED = re.compile(r"(?<=[A-Za-z0-9])(?=(?:" + "|".join(re.escape(l) for l in A8L_LABELS) + r")[ \t]*:)")
# Speed (14 Nov): a fast search for any "Label:" first. It starts with the labels, so the regex engine can skip to
# their first letters; A8L_GLUED, which starts with a lookbehind, is tried at every character.
A8L_ANY = re.compile(r"(?:" + "|".join(re.escape(l) for l in A8L_LABELS) + r")[ \t]*:")


def medicine_a8l(text):
    if not A8L_ANY.search(text):
        return text
    return A8L_GLUED.sub(" ", text)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_a8l(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** see the table at the top.
4. **Harm test:** see the table at the top.
5. **Side effects:**
   - A camel-case name that ends in a listed label and is followed by a colon is split: `startDate:` becomes `start Date:`.
   - Labels that aren't listed, capitals run together and joined URLs are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Aditeya's (mittalutkarsh/era-v5-lab#3) and Utkarsh's (mittalutkarsh/era-v5-lab#5) sci-finepdfs readings.

## 10. `DA-C7-005` · C7 content lost in extraction: near-empty doc · drop · stage 30

1. **Disease:** NEW-near-empty, 2 docs, Utkarsh. Only a title or a header is left, and the body is gone. Examples:
   - `e5c998e626aeaef9`: 233 characters, a tennis order-of-play header with no matches
   - `766c83b5e63a0192`: 96 characters, a title and a date
2. **Medicine:** drop the doc when it has fewer than 250 characters, not counting space at the start and end.

```python
RULE_ID = "DA-C7-005"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "drop"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"

C7E_MIN = 250  # characters; the two reading docs have 233 and 96


def medicine_c7e(text):
    return len(text.strip()) < C7E_MIN


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    return ("drop", doc["text"]) if medicine_c7e(doc["text"]) else ("keep", doc["text"])
```

3. **Action:** drop. **Runs on:** sci-finepdfs. **Reading docs it treats:** see the table at the top.
4. **Harm test:** see the table at the top.
5. **Side effects:**
   - A short doc that is complete, such as a one-paragraph notice, is dropped. Gold doc `b6fd81dbf90b0d17`, a 220-character certificate, is one (within the limit).
   - A doc with a long header and no body is missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

## 11. `DA-C7-004` · C7 content lost in extraction: figures · fix · stage 30

1. **Disease:** NEW-missing-figures, 2 docs, Utkarsh. Where a figure was, there is a Markdown image link to a file that isn't there. Examples:
   - `ceea9671dd61d0b1`: `![Particle size distribution of CSP by LD](image1.png)`, 4 times
   - `469a6695b57d9130`: `![Figure 1-1: Power path of the LTC4061 charger](image)`, 15 times

   Megamath has 5 more, with their own rule, `DA-C7-002`. That one drops the doc, because a maths problem can't be done without its figure. A science text can still be read without its figures, so here only the empty link goes.
2. **Medicine:**
   - **Every such link** is replaced with its caption as plain text: `![Figure 1-1: Power path](image)` becomes `Figure 1-1: Power path`. The caption is real text, often the figure's legend, so it stays.
   - **A line of links with no caption** (`![](image)`) is deleted.
   - **What counts:** a link counts only when its target is a bare `image`, `image1.png` or the like, with no folder or URL, so real image links stay.
   - **Changed on 13 Nov:** the first version deleted a line of links together with its captions, which lost figure legends and compound names in 3 gold docs.

```python
RULE_ID = "DA-C7-004"
CODE = "C7"  # proposed new code: content lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C7I_TARGET = r"\((?:image\d*(?:\.(?:png|jpe?g|gif|bmp|tiff?|svg|emf|wmf))?)\)"  # a bare file name, no folder or URL
C7I_LINK = re.compile(r"!\[([^\]\n]*)\]" + C7I_TARGET, re.I)
C7I_EMPTY_LINE = re.compile(r"^[ \t]*(?:!\[[ \t]*\]" + C7I_TARGET + r"[ \t]*)+$", re.I)  # links with no caption


def _c7i_drop_lines(lines, drop):
    """Delete these lines without leaving two blank lines in a row, or blank lines at the end."""
    out, skip_blank = [], False
    for i, line in enumerate(lines):
        if i in drop:
            skip_blank = not out or not out[-1].strip()
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    if len(lines) - 1 in drop:
        while out and not out[-1].strip():
            out.pop()
    return out


def medicine_c7i(text):
    lines = text.split("\n")
    drop = {i for i, line in enumerate(lines) if C7I_EMPTY_LINE.match(line)}
    out = "\n".join(_c7i_drop_lines(lines, drop)) if drop else text
    return C7I_LINK.sub(lambda m: m.group(1).strip(), out)


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c7i(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** see the table at the top.
4. **Harm test:** see the table at the top.
5. **Side effects:**
   - The figure itself is still lost; only the link markup goes.
   - A caption kept as text may repeat the `Fig. 1.` caption that follows.
   - **Gold contradictions:** gold docs `4b958ac1f45443b5`, `d0a0a41263e845f5` and `eb6ad9726f2d7ddd` each have empty image links (`![Fig. 4. XPS of C dots …](image)`, `![Biotin](image)`, `![Diagram](image)`), so they hold the disease itself. Every version of this rule changes them.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.

## 12. `DA-C8-005` · C8 layout lost in extraction: page numbers and footers · fix · stage 30

1. **Disease:** NEW-page-artifact, 9 docs, Utkarsh. Page furniture from the PDF is left in the text. Examples:
   - `3f77b536af11bdbd`: `Page 1`
   - `28b7763d4a13a37e`: `Page 10 of 11`
   - `69bec7d4c7c5b24a`, `6431e058711852b7`: a page number as the last line
   - `c700ec66afb3d047`: a page number as the first line
   - `e54d3904f1e15ffb`: a page number between two paragraphs
   - `d20e4affc1d318fe`: a slide date footer (`10/21/2011`), twice
   - `77f152ce4336c6d9`: an unfilled `Page No. – Page No.` footer
   - `e58d6a06c9323550`: page numbers in a table of contents
2. **Medicine:** these lines are deleted:
   - a line that is only `Page N`, `Page N of M`, `Page N/M` or `Pg N`, or the unfilled `Page No. – Page No.`;
   - a date-only line (`10/21/2011`) that stands alone between blank lines and occurs 2 or more times that way in the doc. A date right under a name is the date of a letter, not a footer, and stays. This was narrowed on 13 Nov, after gold doc `8a2493cdf33f9a38` lost the dates under its signed comments;
   - a line that is only a number of 1–4 digits, in one of three places:
     - **the first line,** when the next line is not a number too;
     - **the last line,** when the line before it is a finished sentence of running text;
     - **between two lines of running text.**

     Running text means 60 or more characters with 6 or more words. A number next to other numbers or short lines (a table, a list, a contents page) stays. That is why the contents-page numbers in `e58d6a06c9323550` are left.

```python
RULE_ID = "DA-C8-005"
CODE = "C8"  # proposed new code: layout lost in extraction (NEW_DISEASES.md)
ACTION = "fix"
STAGE = "30"
STATUS = "CANDIDATE"
ORIGIN = "sci-finepdfs"  # packs it runs on
PACKS = set(ORIGIN.split(", "))
SOURCE = "sci-finepdfs"  # pack whose reading found it (Utkarsh, Week 2 reading audit)
AUTHOR = "aneeshads"
import re

C8P_PAGE = re.compile(r"^[ \t]*(?:page|pg\.?)[ \t]+\d{1,4}(?:[ \t]*(?:of|/)[ \t]*\d{1,4})?[ \t]*$", re.I)
C8P_UNFILLED = re.compile(r"^[ \t]*page no\.[ \t]*[-–][ \t]*page no\.[ \t]*$", re.I)
C8P_DATE = re.compile(r"^[ \t]*\d{1,2}/\d{1,2}/\d{2,4}[ \t]*$")
C8P_NUMBER = re.compile(r"^[ \t]*\d{1,4}[ \t]*$")
C8P_WORD = re.compile(r"[A-Za-z]{2,}")
C8P_END = re.compile(r"[.!?)\"”’]$")
C8P_PROSE_CHARS, C8P_PROSE_WORDS = 60, 6  # running text, not a heading or a table cell


def _c8p_prose(line, finished=False):
    s = line.strip()
    if len(s) < C8P_PROSE_CHARS or len(C8P_WORD.findall(s)) < C8P_PROSE_WORDS:
        return False
    return not finished or bool(C8P_END.search(s))


def _c8p_drop_lines(lines, drop):
    """Delete these lines without leaving two blank lines in a row, or blank lines at the end."""
    out, skip_blank = [], False
    for i, line in enumerate(lines):
        if i in drop:
            skip_blank = not out or not out[-1].strip()
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    if len(lines) - 1 in drop:
        while out and not out[-1].strip():
            out.pop()
    return out


def _c8p_alone(lines, i):
    """Blank (or the doc's edge) on both sides: a footer, not the date line of a letter."""
    return (i == 0 or not lines[i - 1].strip()) and (i == len(lines) - 1 or not lines[i + 1].strip())


def medicine_c8p(text):
    """Repeat until nothing changes: deleting one line can leave a date or number alone that wasn't before."""
    while True:
        new = _c8p_once(text)
        if new == text:
            return text
        text = new


def _c8p_once(text):
    lines = text.split("\n")
    full = [i for i, line in enumerate(lines) if line.strip()]
    dates = {}
    for i in full:
        if C8P_DATE.match(lines[i]) and _c8p_alone(lines, i):
            dates.setdefault(lines[i].strip(), []).append(i)
    drop = {i for found in dates.values() if len(found) >= 2 for i in found}
    drop |= {i for i in full if C8P_PAGE.match(lines[i]) or C8P_UNFILLED.match(lines[i])}
    rest = [i for i in full if i not in drop]  # page numbers are judged by the lines that stay
    for k, i in enumerate(rest):
        if not C8P_NUMBER.match(lines[i]):
            continue
        prev = lines[rest[k - 1]] if k > 0 else None
        nxt = lines[rest[k + 1]] if k + 1 < len(rest) else None
        if prev is None and nxt is not None and not C8P_NUMBER.match(nxt):
            drop.add(i)  # the first line
        elif nxt is None and prev is not None and _c8p_prose(prev, finished=True):
            drop.add(i)  # the last line, after a finished sentence
        elif prev is not None and nxt is not None and _c8p_prose(prev) and _c8p_prose(nxt):
            drop.add(i)  # between two lines of running text
    return "\n".join(_c8p_drop_lines(lines, drop)) if drop else text


def medicine(doc):
    if doc.get("pack_id") not in PACKS:
        return ("keep", doc["text"])
    new = medicine_c8p(doc["text"])
    return ("fix" if new != doc["text"] else "keep", new)
```

3. **Action:** fix. **Runs on:** sci-finepdfs. **Reading docs it treats:** see the table at the top.
4. **Harm test:** see the table at the top.
5. **Side effects:**
   - A doc that really starts with a number on its own line, such as a section number, loses it.
   - A date footer written right under other text, with no blank line, is missed.
   - Page numbers next to tables, lists or headings, and a repeated title at the end (`77f152ce4336c6d9`), are missed.
6. **Spec v1.1:** status CANDIDATE, reviewer pending. Source: Utkarsh's sci-finepdfs reading, mittalutkarsh/era-v5-lab#5.
