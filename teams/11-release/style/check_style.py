"""Style checker for public text of the ERA V5 lab (G11 Release).

It finds four kinds of error (see style_guide.md):
  banned-word    a word from the banned list
  em-dash        the character U+2014 (and en-dash, U+2013: write "to" for a range)
  email          an email address
  long-sentence  a sentence with more than --max-words words (default 25)

Usage:
    python check_style.py <file.md or folder> [...] [--max-words 25] [--numbers]
    python check_style.py --list          # print the banned words
    python check_style.py --self-test     # the test file must give exactly 4 errors

Exit code: 0 when there are no errors, 1 otherwise. A path that does not exist, or a file that cannot be read,
counts as an error; the other paths are still checked.
--numbers also lists every number as a warning: each number needs TSAI approval before it is published.
Numbers written as words (two to ninety, hundred, thousand, million, billion, dozen) are warnings too; "one"
is left out because it is too common. List markers such as "1." are not numbers.
Rule 1 of public_internal.md says the date of an update and the week number need no approval, so --numbers skips
"week 1" and a date up to the update's date ("31 Oct 2026", "24 Oct to 31 Oct 2026", "24 to 31 Oct 2026").
The update's date is the date on its "Date:" line, or today. A later date is still listed: a future date needs approval.
A pull request number such as "#6" is a name, not a count, so --numbers skips it too.
Banned words are not checked inside code blocks, inline code, URLs and link targets.
The phrases in ALLOWED (such as "magic number") are not banned-word errors.
Em-dashes, en-dashes and emails are checked everywhere.
Each table cell is checked as its own sentence. A long-sentence error points to the line where the sentence starts.
A folder means every .md and .txt file in it, except in tests/ folders (the test file has errors on purpose).
The self-test also checks that style_guide.md lists the same banned words as BANNED.
"""
import argparse
import datetime
import os
import re
import sys

BANNED = [
    "revolutionary", "revolutionise", "revolutionised", "revolutionises", "revolutionising", "revolutionize",
    "revolutionized", "revolutionizes", "revolutionizing", "groundbreaking", "ground-breaking", "breakthrough",
    "breakthroughs", "game-changer", "game-changers", "game-changing", "cutting-edge", "state-of-the-art", "SOTA",
    "world-class", "best-in-class", "world's first", "first-ever", "unprecedented", "unparalleled", "unmatched",
    "paradigm shift", "paradigm shifts", "disruptive", "synergy", "synergies", "leverage", "leveraged", "leverages",
    "leveraging", "utilise", "utilised", "utilises", "utilising", "utilize", "utilized", "utilizes", "utilizing",
    "seamless", "seamlessly", "magic", "magical", "magically", "incredible", "incredibly", "amazing", "amazingly",
    "awesome", "mind-blowing", "flawless", "flawlessly", "guarantee", "guaranteed", "guarantees", "human-level",
    "superhuman", "AGI", "sentient", "delve", "delved", "delves", "delving",
]
ALLOWED = ["magic number", "magic numbers"]   # technical phrases that contain a banned word
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*%?")
NUMBER_WORD = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                         r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
                         r"hundreds?|thousands?|millions?|billions?|trillions?|dozens?)\b", re.IGNORECASE)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MON = "(" + "|".join(MONTHS) + ")"
WEEK = re.compile(r"\bweek \d+\b", re.IGNORECASE)
# DD Mon YYYY, or a range that ends in one: "24 Oct to 31 Oct 2026", "24 to 31 Oct 2026"
DATE = re.compile(r"(?<![\w.])(?:\d{1,2}(?: " + MON + r")? to )?(\d{1,2}) " + MON + r" (\d{4})(?!\w)")
DATE_LINE = re.compile(r"^\W*Date:\W*(\d{1,2}) " + MON + r" (\d{4})(?!\w)", re.MULTILINE)
PR = re.compile(r"(?<![\w&])#\d+\b")   # a pull request or issue number, such as the sources in the review record

def as_date(day, mon, year):
    try:
        return datetime.date(int(year), MONTHS.index(mon) + 1, int(day))
    except ValueError:
        return None

def update_date(text):
    """The date on the 'Date:' line of an update, or today."""
    m = DATE_LINE.search(text)
    return (m and as_date(*m.groups())) or datetime.date.today()

def banned_pattern(words):
    parts = []
    for w in words:
        p = r"[-\s]+".join(re.escape(x) for x in re.split(r"[-\s]+", w))
        parts.append(p.replace("'", "['" + chr(0x2019) + "]"))
    return re.compile(r"(?<![\w-])(?:" + "|".join(parts) + r")(?![\w-])", re.IGNORECASE)

BANNED_RE = banned_pattern(BANNED)
ALLOWED_RE = banned_pattern(ALLOWED)

def guide_words(path):
    """The banned words as style_guide.md lists them: the paragraph of `words` after 'The banned words'."""
    text = open(path, encoding="utf-8").read()
    return re.findall(r"`([^`]+)`", text.split("The banned words", 1)[1].split("\n\n", 2)[1])

def prose_lines(text):
    """Yield (line_number, line) with code blocks, inline code, HTML comments and link targets blanked out.

    Blanking keeps the column numbers of the rest of the line.
    """
    blank = lambda m: " " * len(m.group())
    text = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group()), text, flags=re.S)
    fence = False
    for n, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
            yield n, ""
            continue
        if fence:
            yield n, ""
            continue
        line = re.sub(r"`[^`]*`", blank, line)
        line = re.sub(r"\]\([^)]*\)", lambda m: "]" + " " * (len(m.group()) - 1), line)
        line = re.sub(r"https?://\S+", blank, line)
        yield n, line

def units(lines):
    """Group lines into text units (paragraph, list item, heading, table cell). Yield a list of (line, text)."""
    cur = []
    for n, line in lines:
        s = line.strip()
        new_unit = (not s or s.startswith(("#", "|", ">")) or re.match(r"^([-*+]|\d+[.)])\s", s))
        if new_unit and cur:
            yield cur; cur = []
        if not s:
            continue
        if s.startswith("#"):
            yield [(n, s.strip("# "))]
            continue
        if s.startswith("|"):
            for cell in s.strip("|").split("|"):
                if cell.strip(): yield [(n, cell.strip())]
            continue
        cur.append((n, re.sub(r"^([-*+>]|\d+[.)])\s+", "", s)))
    if cur:
        yield cur

def sentences(text):
    for s in re.split(r"(?<=[.!?])[\"'" + chr(0x201d) + chr(0x2019) + r")\]]*\s+", text):
        if s.strip(): yield s.strip()

def check_text(text, max_words=25, numbers=False):
    """Return a list of (line, col, kind, message). kind is 'error' or 'warning'."""
    out = []
    # Em-dashes, en-dashes and emails are errors anywhere in the file, even in code or links.
    for n, raw in enumerate(text.split("\n"), 1):
        for m in re.finditer(EM_DASH, raw):
            out.append((n, m.start() + 1, "error", "em-dash: use a full stop, a comma or 'and'"))
        for m in re.finditer(EN_DASH, raw):
            out.append((n, m.start() + 1, "error", "en-dash: write 'to' for a range (24 to 31 Oct), or use a full stop or a comma"))
        for m in EMAIL.finditer(raw):
            out.append((n, m.start() + 1, "error", "email: no email addresses in public text"))
    lines = list(prose_lines(text))
    until = update_date(text)
    for n, line in lines:
        allowed = [m.span() for m in ALLOWED_RE.finditer(line)]
        for m in BANNED_RE.finditer(line):
            if any(a <= m.start() < b for a, b in allowed): continue
            out.append((n, m.start() + 1, "error", f"banned-word: '{m.group()}'"))
        if numbers:
            marker = re.match(r"\s*\d+[.)](?=\s)", line)   # a list marker, not a number
            free = [m.span() for m in WEEK.finditer(line)]   # Rule 1: the week number and past dates need no approval
            free += [m.span() for m in DATE.finditer(line) if (d := as_date(*m.groups()[-3:])) and d <= until]
            free += [m.span() for m in PR.finditer(line)]   # a pull request number is a name, not a count
            for m in NUMBER.finditer(line):
                if marker and m.start() < marker.end(): continue
                if any(a <= m.start() < b for a, b in free): continue
                out.append((n, m.start() + 1, "warning", f"number '{m.group()}': has TSAI approved it?"))
            for m in NUMBER_WORD.finditer(line):
                out.append((n, m.start() + 1, "warning", f"number '{m.group()}': has TSAI approved it?"))
    for parts in units(lines):
        text_unit, starts = "", []
        for n, part in parts:
            starts.append((len(text_unit), n)); text_unit += part + " "
        pos = 0
        for s in sentences(text_unit):
            pos = text_unit.find(s, pos)
            start = max(n for off, n in starts if off <= pos)
            pos += len(s)
            words = [w for w in s.split() if re.search(r"\w", w)]
            if len(words) > max_words:
                out.append((start, 1, "error", f"long-sentence: {len(words)} words (max {max_words}): '{' '.join(words[:8])} ...'"))
    return sorted(out)

def files_of(paths):
    """Yield (path, found): every .md and .txt file under a folder, a file as given, and a missing path with False."""
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d != "tests")   # tests/ has errors on purpose
                for name in sorted(names):
                    if name.endswith((".md", ".txt")): yield os.path.join(root, name), True
        elif os.path.isfile(p):
            yield p, True
        else:
            yield p, False

def self_test():
    here = os.path.dirname(os.path.abspath(__file__))
    test = os.path.join(here, "tests", "four_errors.md")
    clean = "We read the data. We wrote the rules.\n\n- Team A: we built a checker.\n"
    errs = [x for x in check_text(open(test, encoding="utf-8").read()) if x[2] == "error"]
    kinds = sorted(x[3].split(":")[0] for x in errs)
    ok = len(errs) == 4 and kinds == ["banned-word", "em-dash", "email", "long-sentence"]
    ok = ok and not check_text(clean)
    print(f"self-test: {test} gives {len(errs)} errors {kinds}; clean sample gives {len(check_text(clean))}")
    range_kinds = [x[3].split(":")[0] for x in check_text("We met from 24" + EN_DASH + "31 Oct.\n")]
    ok = ok and range_kinds == ["en-dash"]
    print(f"self-test: a date range with an en-dash gives {range_kinds}")
    magic = [len(check_text(s)) for s in ("We removed a magic number.\n", "It works like magic.\n")]
    ok = ok and magic == [0, 1]
    print(f"self-test: 'a magic number' gives {magic[0]} errors, 'works like magic' gives {magic[1]}")
    forms = len(check_text("We are leveraging it, we delved and we utilised synergies. It guarantees incredibly good results.\n"))
    ok = ok and forms == 6
    print(f"self-test: other forms of banned words give {forms} errors (want 6)")
    nums = re.findall(r"number '([^']+)'", " ".join(x[3] for x in check_text("1. At step 200, twelve teams met.\n", numbers=True)))
    ok = ok and nums == ["200", "twelve"]
    print(f"self-test: --numbers on '1. At step 200, twelve teams met.' finds {nums} (want ['200', 'twelve'])")
    update = ("**Date:** 31 Oct 2026\n**Period:** 24 Oct to 31 Oct 2026\n\n"
              "In week 1 we read 300 pages from 24 to 30 Oct 2026 (see #6). We meet again on 7 Dec 2026.\n")
    nums = re.findall(r"number '([^']+)'", " ".join(x[3] for x in check_text(update, numbers=True)))
    ok = ok and nums == ["300", "7", "2026"]
    print(f"self-test: --numbers skips the week number, pull request numbers and dates up to the update's date, "
          f"finds {nums} (want ['300', '7', '2026'])")
    table = len(check_text("| " + " | ".join(["word " * 10] * 4) + "|\n"))
    ok = ok and table == 0
    print(f"self-test: a table row of four 10-word cells gives {table} errors")
    where = [x[0] for x in check_text("Short.\nThis " + "word " * 30 + "end.\n")]
    ok = ok and where == [2]
    print(f"self-test: a long sentence that starts on line 2 is reported at line {where}")
    words = guide_words(os.path.join(here, "style_guide.md"))
    only_guide = [w for w in words if w not in BANNED]
    only_script = [w for w in BANNED if w not in words]
    ok = ok and not only_guide and not only_script
    print(f"self-test: style_guide.md lists {len(words)} banned words, the script {len(BANNED)}"
          + (f"; only in the guide: {only_guide}" if only_guide else "")
          + (f"; only in the script: {only_script}" if only_script else ""))
    print("self-test PASS" if ok else "self-test FAIL")
    return 0 if ok else 1

def main():
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Style checker for public text (G11 Release).")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--max-words", type=int, default=25)
    ap.add_argument("--numbers", action="store_true", help="list numbers as warnings")
    ap.add_argument("--list", action="store_true", help="print the banned words")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("\n".join(BANNED)); return 0
    if a.self_test:
        return self_test()
    if not a.paths:
        ap.error("give at least one file or folder")
    errors = warnings = 0
    for path, found in files_of(a.paths):
        if not found:
            print(f"{path}: error: path not found", file=sys.stderr)
            errors += 1; continue
        try:
            text = open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"{path}: error: cannot read the file ({type(e).__name__})", file=sys.stderr)
            errors += 1; continue
        for line, col, kind, msg in check_text(text, a.max_words, a.numbers):
            print(f"{path}:{line}:{col}: {kind}: {msg}")
            errors += kind == "error"; warnings += kind == "warning"
    print(f"{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
