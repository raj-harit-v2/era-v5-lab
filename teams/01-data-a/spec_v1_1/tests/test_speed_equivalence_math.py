"""Equivalence tests for the speed-ups of the math rules in clean.py (spec_v1_1/results/speed_v1_1.md). Each rule that was made
faster is checked against a frozen copy of the rule as it was before the change (c1_reference and d3_reference, below): the same
text goes through both and the results must be equal, on hand-written cases at the edges of the fast path and on random
documents. Every text here is made up; none comes from a pack.

  python -m pytest spec_v1_1/tests/test_speed_equivalence_math.py

  DA-C1-001  site boilerplate (math-finemath): the 120-character test runs before the slow C1_SITE search, and on a pure-ASCII
             line the search uses the lower-cased pattern on the lower-cased line instead of the (?i) pattern
  DA-D3-005  foreign-script lines (math-finemath, math-megamath): letters are counted only for lines that hold a foreign
             character, and the whole text is returned as it is when it holds none
  DA-A8-001  words run together (both math packs): a line is tested with the regexes only if it has the shape of a glued word,
             and a text with no ``` has no fence loop
  DA-A5-002  ligatures and fullwidth letters (both math packs): a text with no fullwidth character is returned after the
             ligature step, without counting its letters
  DA-C7-001  content lost in extraction (both math packs): the "no object" gaps are found from their punctuation, the
             question-mark runs are searched only when the text holds "???", and the line loop starts only when a line
             can be a gap (the namespace of the rule is read from specv1_1.md, as the English F1 test does)

The speed-up tests of the English rules are in test_speed_equivalence.py, those of the code rules in
test_speed_equivalence_code.py and those of the F1 rule in test_speed_equivalence_f1*.py. If the rule's behaviour is ever
changed on purpose, update or delete its frozen copy.
"""
import random
import re
import sys
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[2] / "spec_v1_1"
sys.path.insert(0, str(SPEC))
import clean as c


def c1_reference():
    """DA-C1-001 as it was before its speed-up (clean.py 9a4e3a87f124, specv1_1.md medicine 58): the old medicine_c1 and its three
    regexes. Returns the namespace so tests can reach C1_LINE and C1_SITE."""
    # a whole line that is generic site chrome
    C1_LINE = re.compile(
        r"(?i)\s*(?:More Similar Questions|Similar Questions|Related (?:Questions|Posts|Articles)|Share (?:this|on \w+)|"
        r"Sign ?up|Log ?in|Subscribe|Cookie|Accept (?:all )?cookies|Privacy Policy|Terms of (?:Use|Service)|"
        r"All rights reserved|\u00a9.*|&copy;.*|Follow us|Skip to (?:main )?content|Show Tags|Replies|Views|"
        r"Contact - Home.*|Report (?:abuse|post)|Upvote|Downvote|Like this:|Loading\.\.\.|Previous Post|Next Post|"
        r"Recommended|Back to top|Quick Reply|Click here.*|Leave a (?:Reply|Comment)|Your email address will not be published.*|"
        r"Posted by.*|Tags?:.*|Categories?:.*|Hide Tags|Join (?:now|us)|Download (?:the )?App.*|Course Hero.*)\s*")
    # site chrome seen in this pack (forums, homework sites, document hosts, OEIS, GMAT Club ...); only on lines <= 120 chars
    C1_SITE = re.compile(
        r"(?i)Check GMAT Club Decision Tracker|It is currently \d+ \w+ \d{4}|GMAT Club Daily Prep|Display posts from previous|"
        r"GMAT\u00ae test is a registered trademark|\[#permalink\]|Kudos \[\?\]|This preview shows page|Sign up to view the full|"
        r"View Full Document|Ask a homework question|intentionally blurred sections|My Personal Notes arrow_drop_up|"
        r"^Open in App$|^Last Updated :|All times are GMT|The time now is \d{1,2}:\d{2}|Privacy Statement|"
        r"Remember Me\? Password|having trouble loading external resources|analy[sz]e our traffic|Want to see this answer and more|"
        r"^See Solution$|^Subscribe now$|Upcoming SlideShare|Are you sure you want to|Report Content as Inappropriate|"
        r"Open this post in threaded view|^Loading content$|The OEIS Community \| Maintained by|supported by donations|"
        r"You are Here: Home|Registered Office:|CYBER MONDAY|^Wiki User$|^Buscar$|^Uncategorized$|Created with Sketch|"
        r"best freelance writing portal|Comment sent successfully|Choose the classification system|Read More \u00bb|"
        r"TUTORIALS HOME|Top of Page|Our sister site|Everything was clear\?|Hello Guest!|Free\s+Algebra Tutorials!|"
        r"Teach yourself statistics|^Home >>|\u200e > \u200e|claim an answer you\u2019ll have 24 hours|Search Our Content Library|"
        r"filtered results|^Sort by$|tutors are online|snackBarMessage|Go To Main Page|^Show/hide solution$|"
        r"Correct! Wrong!|Tutorial is loading|^Filed Under:|^Exam Prep:|^Asked in:|Verified Answer \| Published|"
        r"^Guided Lessons$|^Course Content$|Doorsteptutor|Mark Forums Read|^Recommended$|DocShare\.tips|^Hide$|"
        r"Not now$|Write an Interview Experience|Your message has been successfully submitted|has the best spam protection|"
        r"posting guide http|Questions are from the workbook|^Share$|^Children$|Go back to editing|try BYJU|We\u2018ve got your back")
    # phpBB "Replies / <n> / Views / <n>" block, one value per line
    C1_REPLIES = re.compile(r"(?m)^Replies\n\d+\nViews\n[\d.]+K?\n?")

    def medicine_c1(text):
        keep = [l for l in text.split("\n")
                if not (C1_LINE.fullmatch(l) or (C1_SITE.search(l) and len(l) <= 120))]
        return C1_REPLIES.sub("", "\n".join(keep))

    return {"medicine_c1": medicine_c1, "C1_LINE": C1_LINE, "C1_SITE": C1_SITE, "C1_REPLIES": C1_REPLIES}


def d3_reference():
    """DA-D3-005 as it was before its speed-up (clean.py ddf379d68e29, specv1_1.md medicine 56): the old medicine_d3 and its regex."""
    # Cyrillic, Indic, kana, CJK, Hangul, Arabic (Greek is left out: Greek letters are maths)
    D3_FOREIGN = re.compile("[\u0400-\u04ff\u0900-\u0dff\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af\u0600-\u06ff]")

    def medicine_d3(text):
        out, foreign = [], 0
        for l in text.split("\n"):
            letters = sum(c.isalpha() for c in l)
            f = len(D3_FOREIGN.findall(l))
            if letters and f / letters > 0.5:      # a line that is mostly foreign script is removed
                foreign += f
                continue
            out.append(l)
        total = sum(c.isalpha() for c in text)
        if total and foreign / total > 0.3:        # mostly not English: that is D1, drop
            return ("drop", text)
        return "\n".join(out)

    return {"medicine_d3": medicine_d3, "D3_FOREIGN": D3_FOREIGN}


REF = c1_reference()
OLD_C1 = REF["medicine_c1"]
NEW_C1 = c._RULE["DA-C1-001"]()
D3_REF = d3_reference()
OLD_D3 = D3_REF["medicine_d3"]
NEW_D3 = c._RULE["DA-D3-005"]()


def doc(text, pack="math-finemath", lang="en"):
    return {"doc_id": "x", "text": text, "url": "http://a/b", "lang_label": lang, "pack_id": pack}


def expected(text):
    """What the old rule gives for a math-finemath document, in the shared (action, text) form."""
    out = OLD_C1(text)
    return ("fix" if out != text else "keep", out)


def same(text):
    assert NEW_C1(doc(text)) == expected(text), repr(text)


# ---- one made-up line for each alternative of C1_SITE (and of C1_LINE), built from the regex source itself ----------

def alternatives(pattern):
    """The top-level alternatives of a regex source (split on | outside brackets, groups and escapes)."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            cur += pattern[i:i + 2]; i += 2; continue
        if ch in "([": depth += 1
        elif ch in ")]": depth -= 1
        if ch == "|" and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
        i += 1
    return out + [cur]


SUBS = [(r"\d{4}", "2024"), (r"\d{2}", "30"), (r"\d{1,2}", "10"), (r"\d+", "12"), (r"\w+", "Mon"), (r"\s+", " "),
        (r"[sz]", "s"), ("^", ""), ("$", ""), (r"\[", "["), (r"\]", "]"), (r"\?", "?"), (r"\|", "|"), (r"\.", ".")]


def sample(alt):
    s = alt
    for a, b in SUBS:
        s = s.replace(a, b)
    return re.sub(r"\\u([0-9a-f]{4})", lambda m: chr(int(m.group(1), 16)), s)


SITE_ALTS = alternatives(REF["C1_SITE"].pattern[4:])
SITE_SAMPLES = [sample(a) for a in SITE_ALTS]
LINE_ALTS = alternatives(REF["C1_LINE"].pattern[4:].strip())
LINE_SAMPLES = [sample(re.sub(r"\.\*|\\s\*", "", a)) for a in LINE_ALTS]


def test_every_site_alternative_has_a_sample_the_old_regex_matches():
    # guards the sample builder: a sample that does not match would make the cases below test nothing
    assert len(SITE_ALTS) > 80
    bad = [s for s in SITE_SAMPLES if not REF["C1_SITE"].search(s)]
    assert bad == []


def test_the_pattern_can_be_lowered_safely():
    # the fast path lower-cases C1_SITE: that only works if every escape is lower-case and no character is non-ASCII
    p = REF["C1_SITE"].pattern
    assert p.startswith("(?i)") and p.isascii()
    assert not any(e[1].isupper() for e in re.findall(r"\\.", p))      # no \D \W \S \U: lower() would change them


def variants(s):
    return [s, s.upper(), s.lower(), s.swapcase(), "x " + s, s + " x", "  " + s + "  ", s + "\r", "\t" + s]


@pytest.mark.parametrize("sample_line", SITE_SAMPLES)
def test_site_phrase_in_every_case_and_position_matches_old_rule(sample_line):
    for line in variants(sample_line):
        same("Solve for x.\n" + line + "\nThe answer is 4.")


@pytest.mark.parametrize("sample_line", [s for s in LINE_SAMPLES if s.strip()])
def test_whole_line_chrome_matches_old_rule(sample_line):
    for line in variants(sample_line) + [sample_line + " more words here"]:
        same("Find x.\n" + line + "\nx = 2")


# ---- the 120-character limit -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("phrase", ["View Full Document", "[#permalink]", "Kudos [?]", "^Home >>"[1:], "Share", "Hide",
                                    "My Personal Notes arrow_drop_up", "The time now is 10:30"])
def test_length_limit_sweep(phrase):
    for n in range(max(1, len(phrase)), 125):
        for left in (0, n - len(phrase)):
            line = "a" * left + phrase + "a" * (n - len(phrase) - left)
            assert len(line) == n
            same("Intro.\n" + line + "\nOutro.")


def test_site_phrase_on_a_line_of_120_is_dropped_and_121_is_kept():
    phrase = "View Full Document"
    for n, dropped in ((120, True), (121, False)):
        line = phrase + " " + "a" * (n - len(phrase) - 1)
        assert len(line) == n
        got = NEW_C1(doc("Intro.\n" + line + "\nOutro."))
        assert got == expected("Intro.\n" + line + "\nOutro.")
        assert (got[0] == "fix") == dropped


def test_anchored_phrase_only_matches_the_whole_line_or_its_end():
    for text in ("Open in App", "open in app", "Please Open in App", "Open in App now", "x Hide", "Hide x", "HIDE"):
        same("a\n" + text + "\nb")


# ---- non-ASCII lines keep the original (?i) regex ---------------------------------------------------------------------

KELVIN, LONG_S, DOTTED_I, DOTLESS_I = "K", "ſ", "İ", "ı"
UNICODE_LINES = [
    KELVIN + "udos [?]", "Kudos [?] " + KELVIN, "Check GMAT Club Decision Tracker " + LONG_S, LONG_S + "hare",
    "Sign" + LONG_S + "up", "Privacy Statement é", "GMAT® test is a registered trademark",
    "GMAT® TEST IS A REGISTERED TRADEMARK", "Read More »", "READ MORE »", "We‘ve got your back",
    "WE‘VE GOT YOUR BACK", "claim an answer you’ll have 24 hours", DOTTED_I + "ntentionally blurred sections",
    "intentionally blurred sections " + DOTLESS_I, "Free Algebra Tutorials!", "Free Algebra Tutorials!",
    "Home \u200E > \u200E Algebra", "© 2024 Example", "It is currently 12 Mon 2024 é",
    "١٢ It is currently ١٢ Mon ٢٠٢٤", "The time now is ١٠:٣٠",
    "Solve α + β = 10 View Full Document", "é", "中文 Share",
]


@pytest.mark.parametrize("line", UNICODE_LINES)
def test_non_ascii_lines_match_old_rule(line):
    for text in (line, line.upper(), line.lower(), "x " + line, line + " x"):
        same("a\n" + text + "\nb")


def test_the_unicode_cases_include_lines_that_only_the_unicode_regex_matches():
    # these are lines where lower-casing the line would give a different answer than (?i); the fast path must not touch them
    site = REF["C1_SITE"]
    assert site.search(KELVIN + "udos [?]") and not site.search(("Kudos [?]").replace("K", "x"))
    assert expected("a\n" + KELVIN + "udos [?]\nb")[0] == "fix"


def test_other_packs_languages_and_scope_are_unchanged():
    text = "Find x.\nView Full Document\nShare\nx = 2"
    assert NEW_C1(doc(text, pack="math-megamath")) == ("keep", text)       # the rule runs on finemath only
    for pack in ("en-dclm", "code-python", "sci-finepdfs"):
        assert NEW_C1(doc(text, pack=pack)) == ("keep", text)
    assert NEW_C1(doc("")) == ("keep", "")


def test_edge_documents():
    for text in ("", "\n", "\n\n\n", "   ", "Share", "Share\n", "\nShare", "Views", "Replies\n12\nViews\n3.4K\nrest",
                 "Replies\n12\nViews\n3.4K", "x\nReplies\n12\nViews\n3\n", "Replies\n12\nViews\n", "a\r\nShare\r\nb",
                 "a\rView Full Document\rb", "one line that is fine", "$x^2 + y^2 = z^2$\n\n$\\frac{a}{b}$"):
        same(text)


# ---- random documents -------------------------------------------------------------------------------------------------

MATH = ["Solve for x: 2x + 3 = 11.", "x = 4", "$\\int_0^1 x^2 dx = \\frac{1}{3}$", "", "", "The perimeter is 24 cm.",
        "Step 1: subtract 3 from both sides.", "  indented line  ", "A" * 119, "b" * 120, "c" * 121, "α + β = γ",
        "Therefore the sum of the angles is 180 degrees, as the figure above shows.", "Tags", "Home", "views and replies"]


def random_line(rng):
    k = rng.random()
    if k < 0.45:
        return rng.choice(MATH)
    if k < 0.75:
        phrase = rng.choice(SITE_SAMPLES)
    elif k < 0.85:
        phrase = rng.choice([s for s in LINE_SAMPLES if s.strip()])
    else:
        phrase = rng.choice(UNICODE_LINES)
    phrase = rng.choice([phrase, phrase.upper(), phrase.lower(), phrase.swapcase()])
    pad = rng.choice(["", "", " ", "x" * rng.randint(1, 130), "word " * rng.randint(1, 30)])
    return rng.choice([phrase, pad + phrase, phrase + pad, pad + " " + phrase + " " + pad])


def random_doc(rng):
    lines = [random_line(rng) for _ in range(rng.randint(0, 25))]
    if rng.random() < 0.1:
        lines.insert(rng.randint(0, len(lines)), f"Replies\n{rng.randint(0, 99)}\nViews\n{rng.choice(['5', '3.4K', '10', ''])}")
    return rng.choice(["\n", "\n", "\n", "\r\n", "\n\n"]).join(lines)


def test_random_documents_match_old_rule_and_cover_both_outcomes():
    rng = random.Random(1)
    fixes = keeps = 0
    long_kept = 0
    for _ in range(4000):
        text = random_doc(rng)
        want = expected(text)
        assert NEW_C1(doc(text)) == want, repr(text)
        fixes += want[0] == "fix"
        keeps += want[0] == "keep"
        long_kept += any(len(l) > 120 and REF["C1_SITE"].search(l) for l in text.split("\n"))
    assert fixes > 1500 and keeps > 100       # the draw hits both: a test that never fires proves nothing
    assert long_kept > 300                    # lines over 120 characters that hold a site phrase and must stay


def test_random_ascii_lines_match_the_old_regex_directly():
    # the fast path replaces C1_SITE.search on ASCII lines: compare the old regex with the lowered one on random strings
    rng = random.Random(2)
    lowered = re.compile(REF["C1_SITE"].pattern[4:].lower())
    pieces = [s for s in SITE_SAMPLES if s.isascii()] + list("abcxyz 0123456789.-:[]?|>$^\t")
    hits = 0
    for _ in range(20000):
        s = "".join(rng.choice(pieces) if rng.random() < 0.5 else rng.choice("abKkSs 1[]?>") for _ in range(rng.randint(0, 6)))
        s = "".join(ch.swapcase() if rng.random() < 0.3 else ch for ch in s)
        assert s.isascii()
        old, new = REF["C1_SITE"].search(s), lowered.search(s.lower())
        assert bool(old) == bool(new), repr(s)
        hits += bool(old)
    assert hits > 2000


# =====================================================================================================================
# DA-D3-005: lines in a foreign script
# =====================================================================================================================

def expected_d3(text):
    """What the old rule gives, in the shared (action, text) form."""
    out = OLD_D3(text)
    if isinstance(out, tuple):
        return ("drop", text)
    return ("fix" if out != text else "keep", out)


def same_d3(text, pack="math-finemath"):
    got = NEW_D3(doc(text, pack=pack))
    assert got == expected_d3(text), repr(text)
    return got[0]


EN = "The perimeter of the square is four times its side."
SCRIPTS = {"cyrillic": "Привет мир это тест", "devanagari": "नमस्ते दुनिया यह एक परीक्षा है", "kana": "こんにちは世界のテスト",
           "cjk": "你好世界这是一个测试", "hangul": "안녕하세요 세계 테스트", "arabic": "مرحبا بالعالم هذا اختبار"}
# first and last character of each range of D3_FOREIGN, and the characters just outside it
EDGES = ["\u0400", "\u04ff", "\u0900", "\u0dff", "\u3040", "\u30ff", "\u4e00", "\u9fff", "\uac00", "\ud7af", "\u0600", "\u06ff"]
OUTSIDE = ["\u03ff", "\u0500", "\u08ff", "\u0e00", "\u303f", "\u3100", "\u4dff", "\ua000", "\uabff", "\ud7b0", "\u05ff", "\u0700",
           "\u03b1", "\u03a9", "\u00e9", "\u2211", "\u221e"]
# characters inside the ranges that are not letters: the line's letter count then differs from its foreign count
NOT_LETTERS = ["\u0964", "\u0966", "\u093e", "\u094d", "\u0660", "\u060c", "\u0483", "\u0488", "\u0e50", "\u30fb", "\u3099"]


def test_the_foreign_ranges_used_below_are_what_the_regex_matches():
    regex = D3_REF["D3_FOREIGN"]
    assert all(regex.search(ch) for ch in EDGES)
    assert not any(regex.search(ch) for ch in OUTSIDE)
    assert any(regex.search(ch) and not ch.isalpha() for ch in NOT_LETTERS)      # the cases below do cover non-letters


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_each_script_alone_in_a_line_or_inline(name):
    line = SCRIPTS[name]
    assert same_d3(EN + "\n" + line + "\n" + EN + " " + EN) == "fix"              # a whole foreign line is deleted
    assert same_d3(EN + " " + line + " " + EN) == "keep"                            # a few foreign letters in an English line stay
    assert same_d3(line) == "drop"                                                 # all foreign: drop
    assert same_d3("\n".join([line] * 3)) == "drop"
    for pack in ("math-finemath", "math-megamath"):
        same_d3(EN + "\n" + line + "\n" + EN, pack)


@pytest.mark.parametrize("ch", EDGES + OUTSIDE + NOT_LETTERS)
def test_range_edges_and_non_letter_characters(ch):
    for text in (ch, ch * 5, EN + "\n" + ch * 7 + "\n" + EN, EN + ch, ch + "a", "a" + ch * 3 + "b\n" + EN, ch + "1" + ch + "\n",
                 "\n".join([ch + "ab", ch * 4, "ab" + ch + "cd"]), "a" * 40 + "\n" + ch * 60, "1 2 3 " + ch):
        same_d3(text)


def test_greek_is_left_alone():
    assert same_d3("Let \u03b1 + \u03b2 = \u03b3.\n\u03b1\u03b2\u03b3\u03b4\u03b5\u03b6 \u03b7\u03b8\u03b9\u03ba") == "keep"


def line_with(foreign, letters, foreign_char="ж"):
    return "a" * (letters - foreign) + foreign_char * foreign


@pytest.mark.parametrize("foreign_char", ["ж", "你", "ह", "ع"])
def test_line_threshold_sweep(foreign_char):
    # a line goes when MORE than half of its letters are foreign: 5 of 10 stays, 6 of 10 goes
    for n in (1, 2, 3, 10, 11, 40):
        for k in range(0, n + 1):
            same_d3(EN + " " + EN + "\n" + line_with(k, n, foreign_char) + "\n" + EN)
    assert same_d3(EN * 3 + "\n" + line_with(5, 10) + "\n" + EN * 3) == "keep"
    assert same_d3(EN * 3 + "\n" + line_with(6, 10) + "\n" + EN * 3) == "fix"


def test_document_threshold_sweep():
    # the document goes when the removed lines hold MORE than 30% of all its letters: 30 of 100 is a fix, 31 of 101 a drop
    for total in (10, 100, 101, 1000):
        for foreign in range(1, total):
            text = "x" * (total - foreign) + "\n" + "ж" * foreign
            same_d3(text)
    assert same_d3("a" * 70 + "\n" + "ж" * 30) == "fix"
    assert same_d3("a" * 70 + "\n" + "ж" * 31) == "drop"
    assert same_d3("a" * 70 + "\n" + "ж" * 29) == "fix"


def test_foreign_characters_that_are_kept_never_drop_the_document():
    # foreign letters in lines that are not removed do not count towards the drop test
    for k in (1, 3, 9):
        text = "\n".join([("a" * 20 + "ж" * k)] * 5)
        assert same_d3(text) == "keep"
    assert same_d3("\u0964\n\u0964\u0964\n" + EN) == "keep"        # lines of marks only: no letters, so kept


def test_edge_documents_d3():
    for text in ("", "\n", "\n\n\n", " ", "123 456", "\u0964", "ж", "ж\n", "\nж", "a\r\nж\r\nb", "ж\r\nж", "a\nж ж ж\nb\n",
                 "a\n\nж ж ж\n\nb", EN + "\n", "\n" + EN, "ж" * 1000, ("a" * 50 + "\n") * 50 + "ж" * 5000):
        same_d3(text)


def test_other_packs_and_languages_are_unchanged_d3():
    text = EN + "\n" + SCRIPTS["cyrillic"] + "\n" + EN
    for pack in ("en-dclm", "code-python", "sci-finepdfs", "ind-hi-fw2"):
        assert NEW_D3(doc(text, pack=pack)) == ("keep", text)
    assert NEW_D3(doc(text, lang="hi")) == ("keep", text)
    assert NEW_D3(doc(text, pack="math-megamath"))[0] == "fix"


def foreign_run(rng, n):
    return "".join(rng.choice(rng.choice(list(SCRIPTS.values())).replace(" ", "") + "".join(NOT_LETTERS + EDGES)) for _ in range(n))


def random_d3_line(rng):
    k = rng.random()
    if k < 0.40:
        return rng.choice([EN, "x = 4", "$\\int_0^1 x^2 dx$", "", "", "Step 1: add 3.", "Let \u03b1 + \u03b2 = \u03b3", " ", "12 + 7 = 19", "\u00e9\u00e8 ok"])
    if k < 0.60:
        return foreign_run(rng, rng.randint(1, 60))                                                  # a foreign line
    if k < 0.85:
        n = rng.randint(1, 40)
        f = rng.randint(0, n)
        letters = list("a" * (n - f)) + list(foreign_run(rng, f))
        rng.shuffle(letters)
        return "".join(letters)                                                                      # mixed line
    return EN + " " + foreign_run(rng, rng.randint(1, 4)) + " " + EN                                 # a few inline


def random_d3_doc(rng):
    mode = rng.random()
    if mode < 0.3:
        lines = [rng.choice([EN, "x = 4", "", "Step 1."]) for _ in range(rng.randint(0, 20))]       # no foreign character at all
    else:
        lines = [random_d3_line(rng) for _ in range(rng.randint(1, 20))]
    return rng.choice(["\n", "\n", "\r\n", "\n\n"]).join(lines)


def test_random_documents_match_old_rule_and_cover_all_outcomes():
    rng = random.Random(3)
    seen = {"keep": 0, "fix": 0, "drop": 0}
    foreign_kept = 0
    for i in range(4000):
        text = random_d3_doc(rng)
        action = same_d3(text, "math-finemath" if i % 2 else "math-megamath")
        seen[action] += 1
        foreign_kept += action == "keep" and bool(D3_REF["D3_FOREIGN"].search(text))
    assert seen["keep"] > 800 and seen["fix"] > 400 and seen["drop"] > 100, seen    # the draw hits all three outcomes
    assert foreign_kept > 50       # documents with a foreign character that nothing removes: they take the slow path and are kept


# =====================================================================================================================
# DA-C7-001: content lost in extraction
# =====================================================================================================================

import textwrap

SHEET = SPEC.parent / "spec_v1_1" / "sheets" / "specv1_1.md"


def c7_reference():
    """DA-C7-001 as it was before its second speed pass (clean.py ea14b0899085, specv1_1.md medicine 66): the rule with the
    14 Nov guards. Returns the namespace so tests can reach its regexes and medicine_c7."""
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

    return {"medicine_c7": medicine_c7, "C7_NO_OBJECT": C7_NO_OBJECT, "C7_QUESTION_MARK": C7_QUESTION_MARK, "C7_CANDIDATE": C7_CANDIDATE,
            "C7_EQ_END": C7_EQ_END, "C7_DANGLING": C7_DANGLING, "C7_OPTION": C7_OPTION}


OLD = c7_reference()
OLD_C7 = OLD["medicine_c7"]


def c7_namespace():
    """The DA-C7-001 card of specv1_1.md run on its own: a fresh copy each time, so a test can wrap its regexes."""
    text = SHEET.read_text(encoding="utf-8")
    body = re.search(r"^## Medicine \d+ — math / C7 / `DA-C7-001`\n(.*?)(?=^## Medicine |\Z)", text, re.S | re.M).group(1)
    ns = {"__name__": "rules"}
    exec(textwrap.dedent(re.search(r"^```python\n(.*?)^```", body, re.S | re.M).group(1)), ns)
    return ns


NEW = c7_namespace()
NEW_C7 = NEW["medicine_c7"]
GAPS4 = ("The number of fish in tank B =\nUse Binet's formula to show that .\nComparing , we can see that it holds.\n"
         "The area of the circle is\nNow find the perimeter.")


def test_the_patterns_of_the_new_rule_are_the_old_ones():
    assert NEW["C7_NO_OBJECT"].pattern == OLD["C7_NO_OBJECT"].pattern and NEW["C7_NO_OBJECT"].flags == OLD["C7_NO_OBJECT"].flags
    assert NEW["C7_QUESTION_END"].pattern + "|" + NEW["C7_QUESTION_RUN"].pattern == OLD["C7_QUESTION_MARK"].pattern
    for name in ("C7_EQ_END", "C7_DANGLING", "C7_OPTION"):
        assert NEW[name].pattern == OLD[name].pattern and NEW[name].flags == OLD[name].flags, name


C7_TEXTS = {
    "four gaps": GAPS4,
    "three gaps": "The number of fish in tank B =\nUse Binet's formula to show that .\nThe area of the circle is\nNow find the perimeter.",
    "empty answer options": "Q1. Find the value.\n(A)\n(B)\n(C)\n(D)\n",
    "options with text": "Q1. Find the value.\n(A) 3\n(B) 4\n(C) 5\n(D) 6\n",
    "an equals sign then a value": "The value is =\n12\nand more text follows here.\nThe area is =\n(3 + 4)\nThe rest.\nx =\n5\ny =\n6",
    "a dangling word then a lowercase line": "The slope is\nsteeper than before.\nThe area is\nlarger.\nIt is\nclear.\nThat is\nall.",
    "question marks at the end": "Find x: ?\nFind y = ?\nFind z : ? \nFind w =\t?\t\n",
    "three question marks": "What is it ???\nWho??? Why ?????\n?? no",
    "question mark before another": "x = ??\n: ???",
    "question runs and ends together": "a = ?\nb = ???\nc : ?\nd ???? e",
    "punctuation after a word": "Show that .\nFind , and then solve ;\nwrite .\nOR ,\nIs .",
    "tab before the punctuation": "write\t.\nfind\t\t,\nshow \t; x",
    "two blanks before the punctuation": "write  .\nfind   ,",
    "punctuation followed by a letter": "show .x and find ,y and write .5",
    "punctuation at the end of the text": "so find .",
    "punctuation at the end of a line": "so find .\nwrite ,\r\nshow ;\n",
    "a keyword inside a word": "this .\nprofit ,\nbefore .\nx_is .\n3is .\n-is .\nnot-is .",
    "a keyword after a digit or an underscore": "5or .\n_or .\n2 or .",
    "a keyword at the start of the text": "is .\nare ,",
    "a blank run at the start of the text": " .\n ,\n\t;",
    "a long word before the punctuation": "comparing , we see\ncalculate .\nevaluate ;\nsimplify ,",
    "case": "FIND .\nShow ,\nCoMpUtE ;",
    "a dangling word ending in a lookalike letter": "The area i\u017f\nNew sentence.\nThe slope wa\u017f\nNew sentence.\nIt give\u017f\nA new one.\nThe value i\u017f",
    "lookalike letters": "i\u017f .\n\u0131s .\n\u212aind .\nfor\u017f .",
    "other scripts": "\u0627\u0644 is .\n\u00e9 is .\n\u4e2d\u6587 ,\n\u00e9and .",
    "no candidate": "A short sentence. And another one.\nNothing odd here.",
    "empty": "",
    "newline only": "\n\n\n",
    "a trailing blank after the equals sign": "x =  \nThe next line starts here.\ny =\t\nAnother new sentence.\nz =\nFinal new sentence begins.",
    "a carriage return before the newline": "x =\r\nNew sentence.\nThe slope is\r\nNew sentence.\n(A)\r\n(B)\r\n",
    "option lines": "A.\nb)\n(c)\n(D.\nE.\n a)\n\t(B)\n",
    "option then text": "(A)\nsome text\n(B)\n\n(C)\n",
    "a formula after a dangling word": "The result is\n$x^2$\nThe answer equals\n\u221a2\nThat gives\n-3\nIt becomes\n(x+1)",
    "a bullet after a dangling word": "The result is\n- item\nIt equals\n* item\nThat gives\n\u2022 item\nof\n= 3\nas\n^2",
    "blank lines between": "The area is =\n\n\nNew sentence here.\n\nThe slope is\n\n\nAnother new one.",
}


@pytest.mark.parametrize("name", list(C7_TEXTS))
def test_c7_hand_cases_match_old_rule(name):
    text = C7_TEXTS[name]
    assert NEW_C7(text) == OLD_C7(text), name


@pytest.mark.parametrize("name", list(C7_TEXTS))
def test_c7_pieces_match_the_old_regexes(name):
    text = C7_TEXTS[name]
    assert NEW["_c7_no_object"](text) == len(OLD["C7_NO_OBJECT"].findall(text))
    q = len(NEW["C7_QUESTION_END"].findall(text)) + (len(NEW["C7_QUESTION_RUN"].findall(text)) if "???" in text else 0)
    assert q == len(OLD["C7_QUESTION_MARK"].findall(text))
    assert NEW["_c7_has_candidate_line"](text) == bool(OLD["C7_CANDIDATE"].search(text))


def test_c7_the_hand_cases_reach_every_branch():
    outcomes = {NEW_C7(t) for t in C7_TEXTS.values()}
    assert outcomes == {True, False}
    assert any(NEW["_c7_no_object"](t) for t in C7_TEXTS.values())
    assert any(NEW["_c7_has_candidate_line"](t) for t in C7_TEXTS.values())
    assert any(not NEW["_c7_has_candidate_line"](t) for t in C7_TEXTS.values())
    assert any(NEW["C7_QUESTION_RUN"].search(t) for t in C7_TEXTS.values() if "???" in t)


def test_c7_a_gap_search_stops_looking_for_candidate_lines_only_when_the_answer_is_known():
    # four "no object" gaps are enough without any candidate line; three need a fourth gap from a line
    four = "write .\nfind ,\nshow ;\nsolve .\nplain."
    assert NEW_C7(four) is True and not NEW["_c7_has_candidate_line"](four)
    three_and_a_line = "write .\nfind ,\nshow ;\nThe area is =\nA new sentence begins."
    assert NEW_C7(three_and_a_line) is True
    three = "write .\nfind ,\nshow ;\nplain."
    assert NEW_C7(three) is False


PIECES = ["is", "are", "Is", "OF", "to", "find", "Find", "comparing", "and", "or", "then", "x", "3", "_", "-", "tank", "B", "this", "profit",
          "equals", "gives", "gets", "becomes", "was", "therefore", "(A)", "A.", "b)", "(c", "=", ":", "?", "??", "???", "????",
          ".", ",", ";", "\u017f", "\u0131", "\u212a", "\u00e9", "\u2212", "\u221a2", "$x^2$", "\u2022", "*", "^2", "5", "12"]
SEPS = [" ", " ", " ", "  ", "\t", "\n", "\n", "\n\n", "\r\n", " \n", "\t\n", ""]


def random_c7_text(rng):
    out = []
    for _ in range(rng.randint(0, 70)):
        out.append(rng.choice(PIECES))
        out.append(rng.choice(SEPS))
    return "".join(out)


def test_c7_random_texts_match_the_old_rule_and_cover_every_branch():
    rng = random.Random(23)
    seen = {"drop": 0, "keep": 0, "early": 0, "no_candidate": 0, "loop_gap": 0}
    for _ in range(12000):
        text = random_c7_text(rng)
        old, new = OLD_C7(text), NEW_C7(text)
        assert new == old, repr(text)
        assert NEW["_c7_no_object"](text) == len(OLD["C7_NO_OBJECT"].findall(text)), repr(text)
        assert NEW["_c7_has_candidate_line"](text) == bool(OLD["C7_CANDIDATE"].search(text)), repr(text)
        seen["drop" if new else "keep"] += 1
        early = NEW["_c7_no_object"](text) + len(OLD["C7_QUESTION_MARK"].findall(text)) >= 4
        seen["early"] += early
        seen["no_candidate"] += (not early) and not NEW["_c7_has_candidate_line"](text)
        seen["loop_gap"] += (not early) and NEW["_c7_has_candidate_line"](text) and new
    assert all(v > 200 for v in seen.values()), seen


def test_c7_random_token_strings_match_the_old_regex_counts_directly():
    rng = random.Random(29)
    for _ in range(30000):
        text = "".join(rng.choice(PIECES + SEPS * 3) for _ in range(rng.randint(0, 14)))
        assert NEW["_c7_no_object"](text) == len(OLD["C7_NO_OBJECT"].findall(text)), repr(text)
        q = len(NEW["C7_QUESTION_END"].findall(text)) + (len(NEW["C7_QUESTION_RUN"].findall(text)) if "???" in text else 0)
        assert q == len(OLD["C7_QUESTION_MARK"].findall(text)), repr(text)


def test_c7_the_rule_in_clean_py_acts_only_on_the_math_packs_and_equals_the_old_rule():
    rule = c._RULE["DA-C7-001"]()
    for text in (GAPS4, C7_TEXTS["empty answer options"], C7_TEXTS["no candidate"], ""):
        for pack in ("math-finemath", "math-megamath"):
            want = ("drop", text) if OLD_C7(text) else ("keep", text)
            assert rule(doc(text, pack)) == want
        for pack in ("en-dclm", "sci-finepdfs", "code-go", None):
            assert rule(doc(text, pack)) == ("keep", text)


# =====================================================================================================================
# DA-A5-002: ligatures and fullwidth letters
# =====================================================================================================================

def a5_reference():
    """DA-A5-002 as it was before its speed-up (clean.py 55f8653af9a1, specv1_1.md medicine 51): the letters of every text are
    counted before the fullwidth step. Returns the namespace so tests can reach its regexes."""
    import unicodedata
    A5_LIG = re.compile("[\ufb00-\ufb06]")
    A5_FULLWIDTH = re.compile("[\uff01-\uff5e]")
    A5_CJK = re.compile("[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]")

    def medicine_a5(text):
        out = A5_LIG.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)      # ligature to letters
        letters = sum(c.isalpha() for c in out) or 1
        if len(A5_CJK.findall(out)) / letters < 0.01:                                    # leave real CJK text alone
            out = A5_FULLWIDTH.sub(lambda m: chr(ord(m.group()) - 0xFEE0), out)          # fullwidth to ASCII
        return out

    return {"medicine_a5": medicine_a5, "A5_LIG": A5_LIG, "A5_FULLWIDTH": A5_FULLWIDTH, "A5_CJK": A5_CJK}


def a5_namespace():
    """The DA-A5-002 card of specv1_1.md run on its own."""
    text = SHEET.read_text(encoding="utf-8")
    body = re.search(r"^## Medicine \d+ — math / A5 / `DA-A5-002`\n(.*?)(?=^## Medicine |\Z)", text, re.S | re.M).group(1)
    ns = {"__name__": "rules"}
    exec(textwrap.dedent(re.search(r"^```python\n(.*?)^```", body, re.S | re.M).group(1)), ns)
    return ns


A5_OLD = a5_reference()
OLD_A5 = A5_OLD["medicine_a5"]
A5_NEW = a5_namespace()
NEW_A5 = A5_NEW["medicine_a5"]
WORDS = "The proof of the lemma follows from the first term."
FULL = "\uff21\uff22\uff23\uff11\uff12\uff01\uff0c\uff1a"      # fullwidth A B C 1 2 ! , :


def test_a5_the_patterns_are_the_old_ones():
    for name in ("A5_LIG", "A5_FULLWIDTH", "A5_CJK"):
        assert A5_NEW[name].pattern == A5_OLD[name].pattern and A5_NEW[name].flags == A5_OLD[name].flags, name


def cjk_share(n_cjk, n_letters):
    """A text of n_letters letters, n_cjk of them CJK, and one fullwidth letter that is one of the others."""
    return "\u4e2d" * n_cjk + "a" * (n_letters - n_cjk - 1) + "\uff21"


A5_TEXTS = {
    "empty": "",
    "plain": WORDS,
    "ligatures only": "the \ufb01rst \ufb02ow o\ufb00 and o\ufb03ce and \ufb04 \ufb05 \ufb06",
    "the edges of the ligature range": "\ufb00 \ufb06 \ufb07 \ufaff",
    "fullwidth only": WORDS + " " + FULL,
    "the edges of the fullwidth range": "\uff00 \uff01 \uff5e \uff5f x",
    "fullwidth and ligatures": "\ufb01rst " + FULL + " o\ufb03ce",
    "fullwidth with CJK, under the limit": cjk_share(0, 200),
    "fullwidth with CJK, 1 in 100": cjk_share(2, 200),
    "fullwidth with CJK, just under 1 in 100": cjk_share(1, 200),
    "fullwidth with CJK, just over 1 in 100": cjk_share(3, 200),
    "fullwidth with mostly CJK": "\u4e2d\u6587\u3042\u30a2\uac00 " + FULL,
    "CJK without fullwidth": "\u4e2d\u6587 \u3042\u30a2 \uac00 text",
    "a ligature that adds letters, then a fullwidth": "\ufb03" * 3 + cjk_share(1, 100),
    "digits and symbols only": "1234 + 5678 = 6912 \u2211 \u221a",
    "fullwidth digits only": "\uff11\uff12\uff13",
    "half width forms (not fullwidth)": "\uff61\uff71\uff9f\uffe0",
    "a lone fullwidth space": "a\u3000b",
    "newlines": "line one\n" + FULL + "\nline \ufb01 three\n",
}


@pytest.mark.parametrize("name", list(A5_TEXTS))
def test_a5_hand_cases_match_old_rule(name):
    assert NEW_A5(A5_TEXTS[name]) == OLD_A5(A5_TEXTS[name]), name


def test_a5_the_hand_cases_change_and_leave_text_both_ways():
    changed = [n for n, t in A5_TEXTS.items() if NEW_A5(t) != t]
    assert "ligatures only" in changed and "fullwidth only" in changed and "plain" not in changed
    assert "fullwidth with mostly CJK" not in changed       # the CJK rule still protects the fullwidth letters
    assert "fullwidth with CJK, just over 1 in 100" not in changed and "fullwidth with CJK, just under 1 in 100" in changed


def test_a5_a_text_without_fullwidth_is_not_scanned_for_letters(monkeypatch):
    """What the new rule saves: the letter count is a Python loop over the text, and it must not run for a text with no fullwidth."""
    calls = []
    real = A5_NEW["A5_CJK"]

    class Spy:
        def findall(self, text): calls.append(1); return real.findall(text)
    ns = a5_namespace(); ns["A5_CJK"] = Spy()
    ns["medicine_a5"](WORDS * 50 + "\ufb01")
    assert calls == []
    ns["medicine_a5"](WORDS + FULL)
    assert calls == [1]


A5_ASCII = ["the", "proof", "of", "x", "1", "2", " ", " ", "\n", ".", ",", "caf\u00e9", "\u00e9", "\u2211", "\u3000", "\uff61", "\ufb07", "\uff00", "\uff5f"]
A5_CJK_PIECES = ["\u4e2d", "\u6587", "\u3042", "\u30a2", "\uac00"]
A5_FULL_PIECES = ["\uff21", "\uff22", "\uff11", "\uff01", "\uff0c", "\uff5e"]
A5_LIG_PIECES = ["\ufb00", "\ufb01", "\ufb03", "\ufb06"]


def random_a5_text(rng):
    """Mostly ordinary words, with a random few CJK letters, fullwidth characters and ligatures: the CJK share goes from none to far over 1%."""
    parts = [rng.choice(A5_ASCII) + " " for _ in range(rng.randint(0, 150))]
    for pool in (A5_CJK_PIECES, A5_FULL_PIECES, A5_LIG_PIECES):
        parts += [rng.choice(pool) for _ in range(rng.choice([0, 0, 1, 2, 3, 8]))]
    rng.shuffle(parts)
    return "".join(parts)


def test_a5_random_texts_match_old_rule_and_cover_every_branch():
    rng = random.Random(31)
    seen = {"plain": 0, "ligature": 0, "fullwidth_converted": 0, "fullwidth_protected": 0}
    for _ in range(15000):
        text = random_a5_text(rng)
        old, new = OLD_A5(text), NEW_A5(text)
        assert new == old, repr(text)
        full = bool(A5_OLD["A5_FULLWIDTH"].search(A5_OLD["A5_LIG"].sub("", text)))
        seen["plain"] += new == text
        seen["ligature"] += (new != text) and not full
        seen["fullwidth_converted"] += full and A5_OLD["A5_FULLWIDTH"].search(new) is None
        seen["fullwidth_protected"] += full and A5_OLD["A5_FULLWIDTH"].search(new) is not None
    assert all(v > 300 for v in seen.values()), seen


def test_a5_the_rule_in_clean_py_acts_only_on_the_math_packs_and_equals_the_old_rule():
    rule = c._RULE["DA-A5-002"]()
    for text in (WORDS, "the \ufb01rst " + FULL, "\u4e2d\u6587 " + FULL, ""):
        for pack in ("math-finemath", "math-megamath"):
            new = OLD_A5(text)
            assert rule(doc(text, pack)) == (("fix" if new != text else "keep"), new)
        for pack in ("en-dclm", "sci-finepdfs", None):
            assert rule(doc(text, pack)) == ("keep", text)


# =====================================================================================================================
# DA-A8-001: words run together
# =====================================================================================================================

def a8_reference():
    """DA-A8-001 as it was before its speed-up (clean.py 097eb0a4fd3e, specv1_1.md medicine 62): every line is tested with A8_CODE
    and A8_GLUED. Returns the namespace so tests can reach its regexes."""
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

    return {"medicine_a8": medicine_a8, "A8_GLUED": A8_GLUED, "A8_CODE": A8_CODE, "A8_STARTERS": A8_STARTERS}


def a8_namespace():
    """The DA-A8-001 card of specv1_1.md run on its own."""
    text = SHEET.read_text(encoding="utf-8")
    body = re.search(r"^## Medicine \d+ — math / A8 / `DA-A8-001`\n(.*?)(?=^## Medicine |\Z)", text, re.S | re.M).group(1)
    ns = {"__name__": "rules"}
    exec(textwrap.dedent(re.search(r"^```python\n(.*?)^```", body, re.S | re.M).group(1)), ns)
    return ns


A8_OLD = a8_reference()
OLD_A8 = A8_OLD["medicine_a8"]
A8_NEW = a8_namespace()
NEW_A8 = A8_NEW["medicine_a8"]


def test_a8_the_patterns_are_the_old_ones():
    assert A8_NEW["A8_STARTERS"] == A8_OLD["A8_STARTERS"]
    for name in ("A8_GLUED", "A8_CODE"):
        assert A8_NEW[name].pattern == A8_OLD[name].pattern and A8_NEW[name].flags == A8_OLD[name].flags, name


A8_TEXTS = {
    "empty": "",
    "plain": "The proof of the lemma follows from the first term.",
    "a glued starter": "The answer is HydrogenWhen we heat it.",
    "a glued capitalised start": "Practice ProblemsThe first one",
    "a glued word after a number": "Exercises: 30 minQuestions",
    "a missing space after a full stop": "It ends here.The next part",
    "two gaps in one line": "ProblemsThe end.The next",
    "gaps on several lines": "ProblemsThe end.\nThe next.Then more\nplain line\nLetFind x",
    "the right word is not a starter": "Use JavaScript, WordPress, PowerPoint, LinkedIn, YouTube and maxValue.",
    "a brand and a starter in one line": "Use JavaScript and ProblemsThe end",
    "the left word is shorter than three letters": "inThe end and ofThe end and xyThe end",
    "the left word is exactly three letters": "areThe end. andThe end",
    "a capital then three letters": "SumThe rest. ProofThe rest",
    "a dot before the left word": "x.ProblemsThe rest",
    "a digit before the left word": "5ProblemsThe rest and _ProblemsThe rest",
    "a digit after the right word": "ProblemsThe5 and ProblemsThe_ and ProblemsThex",
    "the right word ends with a capital": "ProblemsTHE and ProblemsThE",
    "a glued word at the start of a line": "ProblemsThe\nanswersThe\n.ProblemsThe",
    "a glued word at the end of the text": "see problemsThe",
    "code signs": "if (x) { return sumThe; }",
    "code with each sign": "\n".join(f"sumThe {sign} and ProblemsThe" for sign in ("{", "}", ";", "==", "=>", "->", "::", "//")),
    "code words": "def sumThe\nfunction sumThe\nxdef sumThe\nreturn sumThe\nthe returns sumThe\nthe function sumThe",
    "a fence": "```\nsumThe\n```\nafter the fence sumThe",
    "an indented fence": "  ```python\nsumThe\n  ```\nsumThe",
    "an unclosed fence": "start sumThe\n```\nsumThe\nmore sumThe",
    "two fences": "a sumThe\n```\nb sumThe\n```\nc sumThe\n```\nd sumThe\n```\ne sumThe",
    "backticks inside a line": "text `code` and ``` inside sumThe line",
    "a line with a fence and a gap": "```sumThe\nnext sumThe\n```",
    "carriage returns": "ProblemsThe end\r\nanswersThe\r\n",
    "blank lines": "\n\nProblemsThe\n\n\nplain\n",
    "accents next to the gap": "caf\u00e9ProblemsThe and ProblemsThe\u00e9 and \u00e9ProblemsThe",
    "other scripts": "\u4e2d\u6587ProblemsThe and \u0430\u0431\u0432ProblemsThe",
    "latex": "$x_{ab}$ and \\frac{a}{b}The and x^2 + yThe",
    "a gap after a closing bracket": "(see)The end. [here]The end. (seeThe end)",
    "a glued word inside a long word": "AdminProblemsThe",
}


@pytest.mark.parametrize("name", list(A8_TEXTS))
def test_a8_hand_cases_match_old_rule(name):
    assert NEW_A8(A8_TEXTS[name]) == OLD_A8(A8_TEXTS[name]), name


def test_a8_the_hand_cases_change_and_keep_text_and_reach_both_paths():
    changed = [n for n, t in A8_TEXTS.items() if NEW_A8(t) != t]
    assert {"a glued starter", "a missing space after a full stop", "gaps on several lines"} <= set(changed)
    assert not {"plain", "code signs", "the right word is not a starter"} & set(changed)
    assert {"a fence", "an unclosed fence"} <= set(changed)     # only the lines outside the fence change
    assert any("```" in t for t in A8_TEXTS.values()) and any("```" not in t for t in A8_TEXTS.values())


def test_a8_every_match_of_the_glued_regex_holds_the_junction():
    rng = random.Random(37)
    pieces = ["Problems", "The", "answer", "xy", "sum", "Sum", ".", "5", "_", "e", "\u00e9", " ", "Then", "x", "ab", "Z"]
    for _ in range(40000):
        text = "".join(rng.choice(pieces) for _ in range(rng.randint(0, 9)))
        if A8_OLD["A8_GLUED"].search(text):
            assert A8_NEW["A8_JUNCTION"].search(text), repr(text)


def test_a8_a_line_without_the_junction_does_not_reach_the_regexes():
    class Spy:
        def __init__(self, real): self.real, self.calls = real, 0
        def search(self, line): self.calls += 1; return self.real.search(line)
        def sub(self, *a): self.calls += 1; return self.real.sub(*a)
    ns = a8_namespace()
    ns["A8_CODE"], ns["A8_GLUED"] = Spy(ns["A8_CODE"]), Spy(ns["A8_GLUED"])
    ns["medicine_a8"]("a plain line of words\nanother plain line.\nFind the area of x.\n")
    assert ns["A8_CODE"].calls == 0 and ns["A8_GLUED"].calls == 0
    ns["medicine_a8"]("a plain line\nProblemsThe line\n")
    assert ns["A8_CODE"].calls == 1 and ns["A8_GLUED"].calls == 1


A8_WORDS = ["proof", "area", "sum", "of", "x", "5", "Problems", "answers", "Let", "Find", "the", "a", "maxValue", "JavaScript"]
A8_STARTS = ["The", "This", "Then", "Question", "Problem", "Solve", "Note", "Hello", "Figure", "Why"]
A8_ODD = ["{", "}", ";", "==", "=>", "->", "::", "//", "def ", "function", "return", "```", "  ```", "\u00e9", "_", "$x_a$", ".", "\r"]


def random_a8_text(rng):
    lines = []
    for _ in range(rng.randint(0, 25)):
        parts = []
        for _ in range(rng.randint(0, 10)):
            kind = rng.random()
            if kind < 0.45:
                parts.append(rng.choice(A8_WORDS))
            elif kind < 0.75:
                parts.append(rng.choice(A8_WORDS) + rng.choice(["", "", ".", "5", "_"]) + rng.choice(A8_STARTS) + rng.choice(["", "", "x", "5"]))
            elif kind < 0.9:
                parts.append(rng.choice(A8_STARTS))
            else:
                parts.append(rng.choice(A8_ODD))
        lines.append(rng.choice([" ", " ", ""]).join(parts) if rng.random() < 0.3 else " ".join(parts))
    return "\n".join(lines)


def test_a8_random_texts_match_old_rule_and_cover_every_branch():
    rng = random.Random(41)
    seen = {"changed": 0, "plain": 0, "fence_text": 0, "fence_text_changed": 0, "code_line_with_gap": 0}
    for _ in range(12000):
        text = random_a8_text(rng)
        old, new = OLD_A8(text), NEW_A8(text)
        assert new == old, repr(text)
        seen["changed"] += new != text
        seen["plain"] += new == text
        seen["fence_text"] += "```" in text
        seen["fence_text_changed"] += ("```" in text) and new != text
        seen["code_line_with_gap"] += any(A8_OLD["A8_CODE"].search(l) and A8_OLD["A8_GLUED"].search(l) for l in text.split("\n"))
    assert all(v > 300 for v in seen.values()), seen


def test_a8_the_rule_in_clean_py_acts_only_on_the_math_packs_and_equals_the_old_rule():
    rule = c._RULE["DA-A8-001"]()
    for text in ("ProblemsThe end.The next", "plain text", "```\nsumThe\n```", ""):
        for pack in ("math-finemath", "math-megamath"):
            new = OLD_A8(text)
            assert rule(doc(text, pack)) == (("fix" if new != text else "keep"), new)
        for pack in ("en-dclm", "sci-finepdfs", None):
            assert rule(doc(text, pack)) == ("keep", text)
