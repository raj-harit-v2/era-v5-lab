"""Equivalence tests for the speed-up of the shared F1 rule on prose (the math and science packs).

The prose path of spec_v1_1/build/f1_rule.py (_f1_prose) got three guards that skip a regex pass when the text cannot match it:
  - the email pass runs only when the text holds an "@";
  - the "name at host" pass runs only when the text holds " at <host>.<tld>";
  - the phone pass uses the North American form alone when the text holds no "+" (the international form starts with "+").
Each guard must give the same text as before. A frozen copy of the old _f1_prose (below) uses the unchanged helpers of clean.py; the same text goes
through the old and the new rule and the results must be equal, on hand-written cases at the edge of each guard and on random
documents. Every text here is made up; none comes from a pack.

  python -m pytest spec_v1_1/tests/test_speed_equivalence_f1.py
"""
import random
import re
import sys
from pathlib import Path

import pytest

AT = "@"   # emails are joined at run time: the PR guard reads added lines for email addresses

SPEC = Path(__file__).resolve().parents[2] / "spec_v1_1"
sys.path.insert(0, str(SPEC))
import clean as c

NEW_F1 = c._RULE["f1_rule.py"]()
PACKS = {"math-finemath": "en", "math-megamath": "en", "sci-finepdfs": "eng_Latn"}   # the prose packs and the label of each in the week-1 packs


def doc(text, pack="math-finemath", lang=None):
    return {"doc_id": "x", "text": text, "url": "http://a/b", "pack_id": pack, "lang_label": lang or PACKS[pack]}


# The old North American + international phone pattern, as one string (what _F1P_PHONE was before it was written in two parts).
OLD_PHONE_PATTERN = (r"(?<![\w/.-])(?:\+?1[ .-]?)?(?:\(\d{3}\)\s?|\d{3}[ .-])\d{3}[ .-]\d{4}(?![\w/-])"
                     r"|(?<![\w/.-])\+\d{1,3}(?:[ .-]?\(?\d{1,4}\)?){2,5}\d(?![\w/-])")


def old_f1_prose(text):
    """_f1_prose of spec_v1/build/f1_rule.py as it was before the three guards (clean.py 22d818c72c9f): every pass runs on every text.
    The helpers it calls are the unchanged ones of clean.py. Keep this unchanged; if F1's behaviour is ever changed on purpose, update it."""
    if c._F1P_listing_share(text) > 0.5:
        return ("drop", "")
    out = c._F1P_people_tables(text)
    out = c._F1P_EMAIL.sub(c._F1P_email, out)
    out = c._F1P_AT_EMAIL.sub(lambda m: m.group(0).replace(m.group(1) + " at " + m.group(2), c._F1P_EMAIL_PH)
                              if c._F1P_email_is_private(m.string, m.start(1), m.end(2), m.group(1), m.group(2)) else m.group(0), out)

    def phone(m):
        if c._F1P_TOLL_FREE.match(m.group(0)):
            return m.group(0)
        verdict = c._F1P_context(m.string, m.start(), m.end())
        if verdict is None:
            verdict = c._F1P_value_alone(m.string, m.start(), m.end()) and c._F1P_card(c._F1P_window(m.string, m.start(), m.end())[0])
        return c._F1P_PHONE_PH if verdict else m.group(0)
    out = c._F1P_PHONE.sub(phone, out)

    def address(m):
        verdict = c._F1P_context(m.string, m.start(), m.end())
        if verdict is None:          # an address with a private phone or email next to it
            verdict = bool(re.search(r"<(?:PHONE|EMAIL)>", m.string[m.end():m.end() + 120]))
        return c._F1P_ADDRESS_PH if verdict else m.group(0)
    return c._F1P_ADDRESS.sub(address, out)


def expected(text):
    """What the old prose path gives, in the shared (action, text) form."""
    out = old_f1_prose(text)
    if isinstance(out, tuple):
        return ("drop", text)
    return ("fix" if out != text else "keep", out)


def same(text, pack="math-finemath"):
    got = NEW_F1(doc(text, pack))
    assert got == expected(text), repr(text)
    return got[0]


def same_everywhere(text):
    return {same(text, pack) for pack in PACKS}


def mutate(rng, base, alphabet):
    """A known form with up to two random one-character changes and random characters around it: near-matches in both directions."""
    s = list(base)
    for _ in range(rng.choice([0, 0, 1, 1, 2])):
        i = rng.randint(0, len(s))
        op = rng.choice(["insert", "delete", "replace"])
        if op == "insert" or not s: s.insert(i, rng.choice(alphabet))
        elif op == "delete": del s[min(i, len(s) - 1)]
        else: s[min(i, len(s) - 1)] = rng.choice(alphabet)
    return rng.choice(["", "", " ", "x", "/", ".", "-", "\n", "<"]) + "".join(s) + rng.choice(["", "", " ", "x", "/", ".", "-", "\n", ">", "8"])


# ---- the patterns themselves ------------------------------------------------------------------------------------------

def test_the_patterns_are_the_old_ones():
    assert c._F1P_PHONE.pattern == OLD_PHONE_PATTERN               # the combined pattern, now written in two parts
    assert c._F1P_PHONE_NA_ONLY.pattern == c._F1P_PHONE_NA
    assert c._F1P_PHONE_NA + "|" + c._F1P_PHONE_INTL == OLD_PHONE_PATTERN


def test_the_international_form_needs_a_plus():
    assert c._F1P_PHONE_INTL.startswith(r"(?<![\w/.-])\+")      # so without a "+" it cannot match, and the guard is exact


# ---- guard 1: the email pass needs an "@" -----------------------------------------------------------------------------

EMAIL_TEXTS = [
    ("Write to jane.doe" + AT + "gmail.com for details."), ("Write to JANE.DOE" + AT + "GMAIL.COM"), ("Mail: a.b+tag" + AT + "mail.example.org today"),
    ("info" + AT + "school.edu"), "support@example.com", ("contact us at help" + AT + "acme.com"), ("Prof. Smith (smith" + AT + "uni.edu) teaches it."),
    "No contact here.", "Just an @ sign and a @handle, plus user@ and @domain.com", "a@b", "x@y.z", "@", "email@", "@@",
    ("first" + AT + "one.com and second" + AT + "two.com\nthird" + AT + "three.net"), ("<jane" + AT + "home.net>"), ("jane" + AT + "home.net."), ("(jane" + AT + "home.net)"),
    ("jane" + AT + "home.net" + AT + "other.com"), "see joe@localhost", ("name" + AT + "sub.domain.co.uk"), "ünï@cödé.com", ("jane" + AT + "home.net") * 3,
]


@pytest.mark.parametrize("text", EMAIL_TEXTS)
def test_email_cases_match_old_rule(text):
    same_everywhere(text)
    same_everywhere("Heading\n\n" + text + "\n\nMore prose follows here.")


def test_a_text_with_no_at_sign_is_unchanged_by_the_email_pass():
    assert same("Plain text with no sign at all, only words and 12345.") == "keep"
    assert same("") == "keep"


# ---- guard 2: the "name at host" pass needs " at <host>.<tld>" ----------------------------------------------------------

AT_TEXTS = [
    "jane at example.com", "<jane at example.com>", "  jane at example.com  ", "jane.doe at home.example.org",
    "jane at my-host.example.org", "jane at host2.co.uk", "jane at example", "jane at example.c", "jane at example.com extra words",
    "see jane at example.com for more", "Jane at example.com", "jane AT example.com", "jane  at example.com", "jane at  example.com",
    "info at example.com", "jane at localhost.com", "jane at test.com", "a at b.cc", "meet at 5.30 pm", "arrive at the station.",
    "He was at home.", "look at www.example.com", "jane at example.com\nbob at example.org\n", "jane at EXAMPLE.com", "jane at 123.456.com",
    "<jane at example.com", "jane at example.com>", "x_y at example.com", "9lives at example.com",
    "list at lists.example.org\nUniversity staff: jane at example.edu",
]


@pytest.mark.parametrize("text", AT_TEXTS)
def test_name_at_host_cases_match_old_rule(text):
    same_everywhere(text)
    same_everywhere("Intro line.\n\n" + text + "\n\nOutro line.")


def test_every_match_of_the_pattern_holds_the_prefilter_text():
    # the guard is exact only if no match of _F1P_AT_EMAIL can lack " at <host>.<tld>"
    rng = random.Random(5)
    hits = 0
    for _ in range(30000):
        s = mutate(rng, rng.choice(AT_TEXTS), "ab .-<>@AT\n9_")
        if c._F1P_AT_EMAIL.search(s):
            hits += 1
            assert c._F1P_AT_HOST.search(s), repr(s)
    assert hits > 500


# ---- guard 3: no "+" in the text, so the North American form alone ---------------------------------------------------------

PHONES = [
    "555-123-4567", "(555) 123-4567", "(555)123-4567", "555.123.4567", "555 123 4567", "1-555-123-4567", "1 555 123 4567",
    "+1 555-123-4567", "+1-555-123-4567", "+44 20 7946 0958", "+91 98765 43210", "+33 1 23 45 67 89", "+1(555)123-4567",
    "800-555-1234", "1-800-555-1234", "+1 800 555 1234", "555-123-45678", "555-123-456", "5551234567", "+5551234567",
    "٥٥٥-١٢٣-٤٥٦٧", "555 123 4567", "555-123-4567-8", "555-123-4567.", "555-123-4567/8", "x555-123-4567", "/555-123-4567",
    ".555-123-4567", "-555-123-4567", "_555-123-4567", "2019-2020-2021", "12-345-6789", "123 456 7890 123", "+ 555-123-4567",
]
LABELS = ["", "Home: ", "Cell: ", "Tel: ", "Mobile ", "Office phone ", "Fax: ", "(cell) ", "Daytime Phone ", "Call "]


@pytest.mark.parametrize("phone", PHONES)
def test_phone_forms_match_old_rule(phone):
    for label in LABELS:
        same_everywhere(f"Notes\n\n{label}{phone}\n\nMore text.")
        same_everywhere(f"{label}{phone} and then some prose after it")


@pytest.mark.parametrize("phone", [p for p in PHONES if "+" not in p])
def test_the_same_phone_with_and_without_a_plus_elsewhere_in_the_text(phone):
    # the text with no "+" takes the North American form alone, the same text with a "+" takes the whole pattern: both agree with the old rule
    for extra in ("", "Compute a+b first. ", "Call +44 20 7946 0958 or "):
        same_everywhere(f"Home: {phone}\n\n{extra}Then the rest.")
        same_everywhere(f"{extra}Cell: {phone}")


def test_a_plus_inside_an_email_that_is_masked_before_the_phone_pass():
    # the email pass can remove the only "+" of the text; the phone guard looks at the text it is given
    for text in (("Home: 555-123-4567\nMail jane+tag" + AT + "home.net"), ("jane+tag" + AT + "home.net\nCell: 555-123-4567"), ("x+y" + AT + "home.net 555-123-4567 +1 555-123-4567")):
        same_everywhere(text)


def test_contact_cards_toll_free_and_organisations():
    cards = [
        ("Jane Smith\n12 Oak Street, Springfield, IL 62704\n555-123-4567\njane" + AT + "home.net"),
        "Jane Smith\n555-123-4567\n@janesmith", "Jane Smith\n555-123-4567", "University of Springfield\n555-123-4567",
        "Customer service: 1-800-555-1234", ("Dept. of Health\n(555) 123-4567\nhealth" + AT + "state.gov"),
        "| Name | Telephone |\n|---|---|\n| Jane Smith | 555-123-4567 |\n| Bob Jones | (555) 765-4321 |",
        "| Name | Phone | Fax |\n| --- | --- | --- |\n| Jane Smith | +1 555 123 4567 | 555-123-4568 |",
        "## Contact\n\nCall Jane at 555-123-4567.", "## Staff\n\nMary Jones\n44 Elm Road, Leeds\n+44 113 496 0000",
        "12 Oak Street, Springfield, IL 62704\n555-123-4567", "12 Oak Street\n\nHome: 555-123-4567",
    ]
    for text in cards:
        same_everywhere(text)


def test_phone_regexes_agree_on_random_strings_without_a_plus():
    rng = random.Random(6)
    hits = 0
    for _ in range(40000):
        s = mutate(rng, rng.choice([p for p in PHONES if "+" not in p]), "0123456789()-. /a_\u0665")
        assert "+" not in s
        want = [m.span() for m in c._F1P_PHONE.finditer(s)]      # the combined pattern, equal to the old one (tested above)
        assert [m.span() for m in c._F1P_PHONE_NA_ONLY.finditer(s)] == want, repr(s)
        hits += bool(want)
    assert hits > 1000


# ---- scope ----------------------------------------------------------------------------------------------------------------

def test_other_packs_are_untouched_and_the_label_does_not_matter_for_prose_packs():
    text = ("Home: 555-123-4567\nMail jane.doe" + AT + "gmail.com\njane at example.com")
    assert NEW_F1(doc(text, "en-dclm", lang="en")) == ("keep", text)       # English has no prose path: it has its own F1 rule
    for pack in PACKS:                                                     # the prose path is chosen by the pack: any label gives the old rule's result
        for lang in ("en", "eng_Latn", "hi", "", None):
            assert NEW_F1(dict(doc(text, pack), lang_label=lang)) == expected(text)
    assert same(text) == "fix"


# ---- random documents -----------------------------------------------------------------------------------------------------

PROSE = ["The perimeter of the square is four times its side.", "Let a + b = c and solve for x.", "Results are shown in Table 2.",
         "We thank the reviewers for their comments.", "See Section 3 at the end of this paper.", "x = 4", "", "",
         "It was held at the station at noon.", "The value rose from 12-345-6789 to 2019-2020.", "Compute 3 + 4 = 7."]
NAMES = ["Jane Smith", "Bob Jones", "Mary Ann Lee", "@janesmith", "Dr. Who"]
STREETS = ["12 Oak Street, Springfield, IL 62704", "44 Elm Road", "7 N. High Street", "500 W. Main Avenue, Austin, TX 78701"]
EMAILS = [("jane.doe" + AT + "gmail.com"), ("info" + AT + "school.edu"), ("bob+tag" + AT + "home.net"), "support@example.com", ("a.b" + AT + "mail.example.org"), "name@host", ("jane" + AT + "home.net.")]
ATS = ["jane at example.com", "<bob at my-host.example.org>", "info at lists.example.org", "jane at example", "x at y.zz"]
PHONE_FORMS = ["555-123-4567", "(555) 123-4567", "555.123.4567", "1-800-555-1234", "+1 555-123-4567", "+44 20 7946 0958", "+91 98765 43210",
               "555-123-45678", "٥٥٥-١٢٣-٤٥٦٧"]
ORGS = ["University of Springfield", "Customer service", "Dept. of Health", "Springfield Police", "Acme Inc.", "Contact us"]
TAB = ["| Name | Telephone |", "|---|---|", "| Jane Smith | 555-123-4567 |", "| Bob | +44 20 7946 0958 |"]
NOTICE = ["SMITH, John, 37, 12 Oak Street, teacher", "JONES, Mary Ann, 41, 44 Elm Road, nurse", "LEE, Bob, 29, 7 High Street, clerk"]


def random_fragment(rng):
    k = rng.random()
    if k < 0.30: return rng.choice(PROSE)
    if k < 0.40: return rng.choice(["Home: ", "Cell: ", "Tel: ", "Mobile ", "Fax: ", ""]) + rng.choice(PHONE_FORMS)
    if k < 0.48: return rng.choice(PHONE_FORMS)
    if k < 0.55: return rng.choice(NAMES) + "\n" + rng.choice(STREETS) + "\n" + rng.choice(PHONE_FORMS) + rng.choice(["", "\n" + rng.choice(EMAILS)])
    if k < 0.63: return rng.choice(["Mail ", "Email: ", "", "Write to "]) + rng.choice(EMAILS)
    if k < 0.70: return rng.choice(ATS)
    if k < 0.76: return rng.choice(ORGS) + "\n" + rng.choice(PHONE_FORMS + EMAILS)
    if k < 0.82: return rng.choice(STREETS)
    if k < 0.88: return "\n".join(TAB[:2 + rng.randint(0, 2)])
    if k < 0.93: return rng.choice(NOTICE)
    return rng.choice(["## Contact", "**Contact us**", "# Staff directory", "a+b", "x@", "@y"])


def random_doc(rng):
    if rng.random() < 0.08:                                            # a personal listing: mostly notice lines, so F1 drops it
        lines = [rng.choice(NOTICE) for _ in range(rng.randint(3, 9))] + [rng.choice(PROSE)]
    else:
        lines = [random_fragment(rng) for _ in range(rng.randint(0, 14))]
    return rng.choice(["\n", "\n", "\n\n", "\r\n"]).join(lines)


def test_random_documents_match_old_rule_and_cover_every_branch():
    rng = random.Random(4)
    seen = {"keep": 0, "fix": 0, "drop": 0}
    has = {"@": 0, " at ": 0, "+": 0, "+ and phone fixed": 0, "no + and phone fixed": 0, "at-email fixed": 0}
    for i in range(4000):
        text = random_doc(rng)
        pack = list(PACKS)[i % 3]
        action = same(text, pack)
        seen[action] += 1
        out = expected(text)[1]
        has["@"] += "@" in text
        has[" at "] += " at " in text
        has["+"] += "+" in text
        phone_fixed = action == "fix" and "<PHONE>" in out and "<PHONE>" not in text
        has["+ and phone fixed"] += phone_fixed and "+" in text
        has["no + and phone fixed"] += phone_fixed and "+" not in text
        has["at-email fixed"] += action == "fix" and bool(re.search(r"[a-z0-9._-]+ at [^\s>]+", text)) and out.count("<EMAIL>") > text.count("<EMAIL>")
    assert seen["keep"] > 500 and seen["fix"] > 1500 and seen["drop"] > 150, seen
    assert all(v > 100 for k, v in has.items() if k != "at-email fixed") and has["at-email fixed"] > 20, has      # every guard is hit both ways
