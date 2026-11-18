"""Equivalence tests for the speed-up of the English F1 rule DA-F1-005 in spec v1.1 (spec_v1_1/results/speed_v1_1.md, fix 3).

medicine_f1 searched the whole text for an organisation phrase (ORG_VOICE) before it read a single line, although the answer
is only used on a line that has an email, a phone number or an address. It is now searched the first time such a line asks,
and the answer is kept. The result must be the same text as before for every document.

The rule is read from the DA-F1-005 card of spec_v1_1/sheets/specv1_1.md (spec v1 and its sheet are frozen and are not
changed). A frozen copy of the old medicine_f1 (below, it uses the regexes and helpers of the same card) gets the same text
as the new one and the results must be equal, on hand-written cases at the edge of the change and on random documents. Every
text here is made up; none comes from a pack.

  python -m pytest spec_v1_1/tests/test_speed_equivalence_f1_english.py
"""
import random
import re
import textwrap
from pathlib import Path

import pytest

SHEET = Path(__file__).resolve().parents[2] / "spec_v1_1" / "sheets" / "specv1_1.md"
AT = "@"  # made-up values are joined at run time


def namespace():
    """The DA-F1-005 card of specv1_1.md run on its own: a fresh copy each time, so a test can wrap its regexes."""
    text = SHEET.read_text(encoding="utf-8")
    body = re.search(r"^## Medicine \d+ — english / F1 / `DA-F1-005`\n(.*?)(?=^## Medicine |\Z)", text, re.S | re.M).group(1)
    ns = {"__name__": "rules"}
    exec(textwrap.dedent(re.search(r"^```python\n(.*?)^```", body, re.S | re.M).group(1)), ns)
    return ns


def old_medicine_f1(text, ns):
    """medicine_f1 of DA-F1-005 as it was before the change (spec v1.1 at 05d9c74): ORG_VOICE searched on every text, first.
    Keep this unchanged; if the rule is ever changed on purpose, update it."""
    lines = text.split("\n")
    org_page = bool(ns["ORG_VOICE"].search(text))
    has_org = {}

    def org_near(i):
        for j in range(max(0, i - 6), min(len(lines), i + 7)):
            if j not in has_org:
                has_org[j] = ns["ORGANISATION"].search(lines[j]) is not None
            if has_org[j]:
                return True
        return False

    out = []
    for i, line in enumerate(lines):
        if "@" not in line and not ns["DIGIT"].search(line):
            out.append(line)
            continue
        new = ns["EMAIL"].sub(lambda m: ns["_email"](m, org_page or org_near(i) or bool(ns["PUBLIC_ROLE"].search(
            "\n".join(lines[max(0, i - 2):i + 1])))), line) if "@" in line else line
        if ns["PHONE"].search(new) or ns["ADDRESS"].search(new):
            if not (org_page or org_near(i)):
                new = ns["PHONE"].sub(lambda m: m.group() if ns["TOLL_FREE"].match(m.group()) else "<PHONE>", new)
                if len(line.strip()) <= ns["CONTACT_LINE"]:
                    new = ns["ADDRESS"].sub("<ADDRESS>", new)
        out.append(new)
    return "\n".join(out)


class Counting:
    """A regex that counts its search calls and gives the real answer."""
    def __init__(self, real): self.real, self.calls = real, 0
    def search(self, text, *a):
        self.calls += 1
        return self.real.search(text, *a)
    def __getattr__(self, name): return getattr(self.real, name)


PLAIN = "The river rises in the hills.\nIt runs south to the sea."
PHONE_LINE, EMAIL_LINE = "Call 555-867-5309 now.", "Write to ravi.kumar" + AT + "brightwave.net today."
ORG_PHRASES = ["Please call us any time.", "Our team is here to help.", "We provide fast repairs.", "Need help?", "☎ 020 7946 0958",
               "one of our clinics", "Visit us today."]
ORG_LINES = ["The library is on the corner.", "The museum opens at nine.", "Dr. Rao's veterinary clinic"]
CONTACT = [PHONE_LINE, EMAIL_LINE, "Reach jane.doe" + AT + "newsdesk.net today.", "Open Mon-Fri, fax 020 7946 0958",
           "Toll free 1-800-555-0199", "Ring +1 (312) 555-0142 or 312 555 0142", "Home: 42 Elm Street, Springfield, IL 62704",
           "12 N. Oak Avenue", "sam99" + AT + "uni.edu", "info" + AT + "brightwave.net", "ravi_k" + AT + "gmail.com",
           "Contact the reporter at amy.lee" + AT + "paper.com", "a" + AT + "b", "123", ""]
FILL = ["The river rises in the hills.", "It runs south to the sea.", "Growers plant rice and wheat.", "The dry months are long.",
        "Rain returns in June.", "Boats cross the bend at dawn.", "Fish are sold at noon.", "Evenings are quiet and cool."]


def same_as_old(text):
    ns = namespace()
    new = ns["medicine_f1"](text)
    assert new == old_medicine_f1(text, ns)
    return new


CASES = {
    "no contact line at all": PLAIN,
    "an organisation phrase and no contact line": ORG_PHRASES[0] + "\n" + PLAIN,
    "a phone line on an ordinary page": PLAIN + "\n" + PHONE_LINE,
    "a phone line and an organisation phrase above it": ORG_PHRASES[0] + "\n" + PLAIN + "\n" + PHONE_LINE,
    "the organisation phrase only after the phone line, far below": PHONE_LINE + "\n" + "\n".join(FILL * 2) + "\n" + ORG_PHRASES[1],
    "the organisation phrase on the last line": PLAIN + "\n" + PHONE_LINE + "\n" + "\n".join(FILL) + "\n" + ORG_PHRASES[2],
    "an email on an ordinary page": PLAIN + "\n" + EMAIL_LINE,
    "an email and an organisation phrase far above": ORG_PHRASES[3] + "\n" + "\n".join(FILL * 2) + "\n" + EMAIL_LINE,
    "an email and an organisation phrase far below": EMAIL_LINE + "\n" + "\n".join(FILL * 2) + "\n" + ORG_PHRASES[4],
    "a role word above an email": "The reporter wrote this.\n" + PLAIN + "\nReach jane.doe" + AT + "newsdesk.net today.",
    "toll free kept, phone masked": "Toll free 1-800-555-0199\nCall 555-867-5309 now.",
    "an address on a short line": "12 N. Oak Avenue\n" + PLAIN,
    "empty text": "",
    "one blank line": "\n",
    "digits and no contact": "Chapter 12\nPage 3 of 40\nIn 1999 it rose by 3.5%.",
    "the organisation phrase is the whole text": ORG_PHRASES[0],
}


@pytest.mark.parametrize("name", list(CASES))
def test_hand_written_cases_match_old_rule(name):
    same_as_old(CASES[name])


@pytest.mark.parametrize("phrase", ORG_PHRASES)
def test_every_kind_of_organisation_phrase_on_the_page_keeps_the_contact(phrase):
    text = PLAIN + "\n" + PHONE_LINE + "\n" + "\n".join(FILL) + "\n" + phrase
    assert same_as_old(text) == text                      # kept: the page is an organisation's, however far the phrase is
    assert same_as_old(text.replace(phrase, "")) != text  # and without it the phone is masked


def test_the_organisation_phrase_is_not_searched_when_no_line_asks():
    for text in (PLAIN, ORG_PHRASES[0] + "\n" + PLAIN, "Chapter 12\nPage 3 of 40", "", "\n".join(FILL * 3)):
        ns = namespace()
        ns["ORG_VOICE"] = counter = Counting(ns["ORG_VOICE"])
        ns["medicine_f1"](text)
        assert counter.calls == 0, text


def test_the_organisation_phrase_is_searched_once_however_many_lines_ask():
    text = "\n".join([EMAIL_LINE, PHONE_LINE, "Home: 42 Elm Street, Springfield, IL 62704", PHONE_LINE, EMAIL_LINE] * 5)
    ns = namespace()
    ns["ORG_VOICE"] = counter = Counting(ns["ORG_VOICE"])
    new = ns["medicine_f1"](text)
    assert counter.calls == 1
    assert new == old_medicine_f1(text, namespace())


def test_the_search_is_still_made_when_a_line_has_only_an_email_or_only_a_phone():
    for text in (PLAIN + "\n" + EMAIL_LINE, PLAIN + "\n" + PHONE_LINE):
        ns = namespace()
        ns["ORG_VOICE"] = counter = Counting(ns["ORG_VOICE"])
        ns["medicine_f1"](text)
        assert counter.calls == 1


def test_the_old_rule_searched_every_text():
    """What the new rule saves: the frozen copy searches the page once for every text, whatever the text holds."""
    for text in (PLAIN, "", PLAIN + "\n" + PHONE_LINE):
        ns = namespace()
        ns["ORG_VOICE"] = counter = Counting(ns["ORG_VOICE"])
        old_medicine_f1(text, ns)
        assert counter.calls == 1


def test_a_text_is_not_changed_by_an_earlier_one():
    """The answer is kept for one text only: an organisation page followed by an ordinary page."""
    ns = namespace()
    page = ORG_PHRASES[0] + "\n" + PHONE_LINE
    plain = PLAIN + "\n" + PHONE_LINE
    for text in (page, plain, page, plain):
        assert ns["medicine_f1"](text) == old_medicine_f1(text, ns)
    assert ns["medicine_f1"](page) == page and ns["medicine_f1"](plain) != plain


def test_random_documents_match_old_rule_and_cover_every_branch():
    pieces = FILL + ORG_LINES + CONTACT + ORG_PHRASES
    rng = random.Random(11)
    ns = namespace()
    asked = changed = kept_by_page = 0
    for _ in range(4000):
        text = "\n".join(" ".join(rng.choices(pieces, k=rng.randint(0, 2))) for _ in range(rng.randint(0, 30)))
        new = ns["medicine_f1"](text)
        assert new == old_medicine_f1(text, ns)
        changed += new != text
        has_contact = any(("@" in l or ns["DIGIT"].search(l)) and (ns["EMAIL"].search(l) or ns["PHONE"].search(l)
                                                                 or ns["ADDRESS"].search(l)) for l in text.split("\n"))
        asked += has_contact
        kept_by_page += bool(has_contact and ns["ORG_VOICE"].search(text))
    assert changed > 500 and asked > 1000 and kept_by_page > 300          # every outcome occurs, so the check is not vacuous
    assert asked < 3800                                                   # and many documents never ask
