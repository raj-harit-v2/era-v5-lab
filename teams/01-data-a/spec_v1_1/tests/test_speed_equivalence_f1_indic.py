"""Equivalence tests for the speed-up of the shared F1 rule on the Indic packs (its Indic path, _f1_indic).

Four passes of _f1_indic got a guard that skips them when the text cannot match:
  - the Indic-digit translation runs only when the text holds one of the characters it maps;
  - the toll-free regex runs only when the text holds "1800" or "1860";
  - the mobile and landline regexes run only when the text holds the core every match must contain (the regex without its
    lookarounds and optional prefixes);
  - the email pass runs only when the text holds an "@".
Each guard must give the same text as before. A frozen copy of the old _f1_indic (below, it uses the unchanged helpers and
regexes of clean.py) and the new rule get the same text and the results must be equal, on hand-written cases at the edge of each
guard and on random documents. Every text here is made up; none comes from a pack.

  python -m pytest spec_v1_1/tests/test_speed_equivalence_f1_indic.py
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
INDIC_PACKS = sorted(p for p, fam in c._FAMILY.items() if fam == "indic")
BASES = (0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66)   # the zero of each Indic script's digits


def old_f1_indic(text):
    """_f1_indic of spec_v1/build/f1_rule.py as it was before the guards (clean.py c1a96591cefb): every pass runs on every text.
    Keep this unchanged; if F1's behaviour is ever changed on purpose, update it."""
    key = text.translate(c._F1I_DIGITS)            # Indic digits read as 0-9; same length, so spans match the text
    spans = []
    for m in c._F1I_TOLL_FREE.finditer(key):
        spans.append((m.start(), m.end(), None))
    taken = lambda s, e: any(a < e and s < b for a, b, _ in spans)
    for m in c._F1I_MOBILE.finditer(key):
        if not taken(m.start(), m.end()):
            private = bool(c._F1I_PERSONAL.search(text[max(0, m.start() - 50):m.start()])) or not c._F1I_org_near(text, m.start(), m.end())
            spans.append((m.start(), m.end(), c._F1P_PHONE_PH if private else None))
    for m in c._F1I_LANDLINE.finditer(key):
        if not taken(m.start(), m.end()):
            line = text[text.rfind("\n", 0, m.start()) + 1:m.start()]
            private = bool(c._F1I_PERSONAL.search(text[max(0, m.start() - 50):m.start()])) or (
                c._F1I_labelled(text, m.start()) and not (c._F1I_ORG_WORDS.search(line) or c._F1P_ORG.search(line)))
            spans.append((m.start(), m.end(), c._F1P_PHONE_PH if private else None))
    out, last = [], 0
    for s, e, tag in sorted(spans):
        if tag:
            out += [text[last:s], tag]
            last = e
    out = "".join(out) + text[last:]

    def email(m):
        local, domain = m.group(1), m.group(2)
        if c._F1P_SAFE_DOMAIN.search(domain) or c._F1P_ROLE_LOCAL.match(local) or c._F1I_ORG_DOMAIN.search(domain):
            return m.group(0)
        if not c._F1I_PERSONAL.search(m.string[max(0, m.start() - 50):m.start()]) and c._F1I_org_near(m.string, m.start(), m.end()):
            return m.group(0)
        return c._F1P_EMAIL_PH
    return c._F1P_EMAIL.sub(email, out)


def doc(text, pack="ind-hi-fw2", lang="hi"):
    return {"doc_id": "x", "text": text, "url": "http://a/b", "pack_id": pack, "lang_label": lang}


def expected(text):
    out = old_f1_indic(text)
    return ("fix" if out != text else "keep", out)


def same(text, pack="ind-hi-fw2"):
    got = NEW_F1(doc(text, pack))
    assert got == expected(text), repr(text)
    return got[0]


def script(s, base):
    """The Latin digits of s written in the digits of one Indic script."""
    return "".join(chr(base + int(ch)) if ch.isdigit() and ch.isascii() else ch for ch in s)


def variants(s):
    """The text as it is, and with its digits in each script, and with only the first half translated."""
    half = len(s) // 2
    return [s] + [script(s, b) for b in BASES] + [script(s[:half], BASES[0]) + s[half:]]


# ---- the guards and the patterns they rely on ---------------------------------------------------------------------------

def test_the_digit_guard_matches_exactly_the_characters_the_translation_maps():
    found = set(re.findall(c._F1I_INDIC_DIGIT.pattern, "".join(map(chr, range(0x110000)))))
    assert found == {chr(k) for k in c._F1I_DIGITS}


def test_the_cores_are_parts_of_the_full_patterns():
    assert c._F1I_MOBILE_CORE.pattern in c._F1I_MOBILE.pattern and c._F1I_MOBILE_CORE.flags == c._F1I_MOBILE.flags
    assert c._F1I_LANDLINE_CORE.pattern in c._F1I_LANDLINE.pattern and c._F1I_LANDLINE_CORE.flags == c._F1I_LANDLINE.flags
    assert "18[06]0" in c._F1I_TOLL_FREE.pattern                          # so "1800" or "1860" is in every match
    assert "@" in c._F1P_EMAIL.pattern


MOBILES = ["98765 43210", "98765-43210", "+91 98765 43210", "+91-98765-43210", "+919876543210", "0091 98765 43210", "00 91 98765 43210",
           "91 98765 43210", "91-9876543210", "09876543210", "0 98765 43210", "0-98765-43210", "9876543210", "987 654 3210", "987-654-3210",
           "6789012345", "7890123456", "8901234567", "5876543210", "98765432101", "987654321", "9876 543210", "+91  98765 43210",
           "98765 4321", "98765\t43210", "+91\t98765 43210"]
LANDLINES = ["011-2345 6789", "011 23456789", "(011) 2345-6789", "(011)23456789", "011-23456789", "022 2345 6789", "0120-2345678",
             "04365-234567", "+91 011 23456789", "+91-011-23456789", "+91011-23456789", "011 1345 6789", "011-234567", "011-23456",
             "0411 2345 6789", "080-4123 4567", "0112345678", "011-2345-6789"]
TOLL_FREE = ["1800 123 4567", "1800-123-4567", "1800 345 678", "1860 123 4567", "1860-500-1234", "18001234567", "1800-12-34567", "1801 123 4567",
             "180 0123 4567", "1800 123 45", "1860 12 3456", "1800123456"]
PHONES = MOBILES + LANDLINES + TOLL_FREE
LABELS = ["", "Mobile: ", "Mob. ", "Personal: ", "Personal mobile ", "WhatsApp ", "Home: ", "Residence ", "Office: ", "Contact: ", "Phone: ",
          "मोबाइल ", "मोबाइल नं. ", "फोन: ", "निजी मोबाइल ", "व्यक्तिगत ", "घर ", "মোবাইল ", "ફોન ", "ಮೊಬೈಲ್ ", "కార్యాలయం ", "கார்யாலய ",
          "कार्यालय ", "विभाग फोन ", "Department of Health ", "Customer care ", "Ministry helpline "]
LINES = ["यह एक परीक्षण वाक्य है।", "এটি একটি পরীক্ষা বাক্য।", "આ એક પરીક્ષણ વાક્ય છે.", "ಇದು ಒಂದು ಪರೀಕ್ಷಾ ವಾಕ್ಯ.", "ఇది ఒక పరీక్ష వాక్యం.",
         "இது ஒரு சோதனை வாக்கியம்.", "यह मराठी वाक्य आहे।", "संस्कृतम् वाक्यम्।", "ଏହା ଏକ ପରୀକ୍ଷା ବାକ୍ୟ", "Plain English line.", "", "2023 में 1800 लोग आए।"]


@pytest.mark.parametrize("phone", PHONES)
def test_phone_forms_in_every_script_and_label_match_old_rule(phone):
    for v in variants(phone):
        for label in LABELS:
            same(f"{LINES[0]}\n{label}{v}\n{LINES[1]}")
        same(f"{v} और बाकी पाठ")


def test_a_phone_with_context_edges():
    for edge in ("x", "/", ".", "+", "-", "_", "1", " ", "\n", "(", ")", "०", "क"):
        for phone in ("98765 43210", "011-2345 6789", "1800 123 4567", "+91 98765 43210"):
            same(f"प्रिय {edge}{phone}{edge} अंत")
            same(f"{edge}{phone}")
            same(f"{phone}{edge}9")
            same(f"{phone}.5 और")


OVERLAPS = ["1800 987 654 3210", "1860 987 654 3210", "1800\t987\t654\t3210", "1860 876 543 2109", "Call 1800 987 654 3210 now",
            "मोबाइल 1800 987 654 3210"]


def test_a_toll_free_number_blocks_the_mobile_number_it_overlaps(monkeypatch):
    # A toll-free match is kept (never masked) and, being found first, stops a mobile or landline match that overlaps it, so the
    # toll-free pass can change the output. These texts do overlap: without the toll-free pass the old rule masks the mobile part.
    for text in OVERLAPS:
        for v in variants(text):
            same(v)
    with monkeypatch.context() as m:
        m.setattr(c, "_F1I_TOLL_FREE", re.compile(r"(?!)"))                 # the toll-free pass finds nothing
        without = [old_f1_indic(text) for text in OVERLAPS]
    assert [old_f1_indic(text) for text in OVERLAPS] != without             # so the cases are not vacuous
    assert all(old_f1_indic(t) == t for t in OVERLAPS)                       # with the pass, nothing is masked


def test_toll_free_and_other_numbers_together():
    for text in ("1800 123 4567", "1800-345-6789 और 98765 43210", "1860 500 1234 / 011-2345 6789", "Toll free 18001234567 mobile 9876543210",
                 "1860 9876543210", "98765 1800 12345", "1800 987 654 3210 98765 43210", "98765 43210 1860 987 654 3210"):
        for v in variants(text):
            same(v)
            same("मोबाइल " + v)


EMAILS = [("ravi.kumar" + AT + "gmail.com"), ("ravi" + AT + "gmail.com"), ("info" + AT + "school.edu"), "support@example.com", ("officer" + AT + "nic.in"), ("clerk" + AT + "dept.gov.in"),
          ("abc" + AT + "univ.ac.in"), ("x" + AT + "company.co.in"), "name@host", ("a" + AT + "b.co"), ("ravi" + AT + "gmail.com" + AT + "other.com"), ("RAVI" + AT + "GMAIL.COM"), ("ravi+tag" + AT + "mail.example.org"),
          ("ravi" + AT + "school.org.in"), "रवि@gmail.com"]
EMAIL_LABELS = ["", "Personal email: ", "निजी ईमेल: ", "ईमेल: ", "Contact us at ", "विभाग: ", "कार्यालय ", "Department email ", "Home ", "व्यक्तिगत "]


@pytest.mark.parametrize("email", EMAILS)
def test_emails_match_old_rule(email):
    for label in EMAIL_LABELS:
        same(f"{LINES[0]}\n{label}{email}\n{LINES[2]}")
    same(f"{email} और 98765 43210")


def test_texts_without_digits_or_at_signs_or_phone_shapes():
    for text in ("", "\n", " ", LINES[0], "\n".join(LINES), "सिर्फ शब्द, कोई संख्या नहीं", "@", "email@", "@handle", "a@", "1800", "1860",
                 "98765", "01123456", "0", "९८७६५ ४३२१०", "९८७६५४३२१०", "०११-२३४५ ६७८९", "१८०० १२३ ४५६७", "१८६०१२३४५६७"):
        same(text)


def test_every_match_of_each_full_pattern_holds_its_core():
    # the guards are exact only if no match of a full regex can lack its core (or "1800"/"1860" for the toll-free one)
    rng = random.Random(7)
    hits = {"mobile": 0, "landline": 0, "toll": 0}
    base = [p for p in PHONES] + ["+91 " + p for p in MOBILES[:8]] + ["(" + p + ")" for p in LANDLINES[:5]]
    alphabet = "0123456789 -\t()+./a"
    for _ in range(40000):
        s = mutate(rng, rng.choice(base), alphabet)
        if c._F1I_MOBILE.search(s):
            hits["mobile"] += 1
            assert c._F1I_MOBILE_CORE.search(s), repr(s)
        if c._F1I_LANDLINE.search(s):
            hits["landline"] += 1
            assert c._F1I_LANDLINE_CORE.search(s), repr(s)
        if c._F1I_TOLL_FREE.search(s):
            hits["toll"] += 1
            assert "1800" in s or "1860" in s, repr(s)
    assert all(v > 500 for v in hits.values()), hits


def mutate(rng, base, alphabet):
    """A known form with up to two one-character changes and random characters around it: near-matches in both directions."""
    s = list(base)
    for _ in range(rng.choice([0, 0, 1, 1, 2])):
        i = rng.randint(0, len(s))
        op = rng.choice(["insert", "delete", "replace"])
        if op == "insert" or not s:
            s.insert(i, rng.choice(alphabet))
        elif op == "delete":
            del s[min(i, len(s) - 1)]
        else:
            s[min(i, len(s) - 1)] = rng.choice(alphabet)
    return rng.choice(["", "", " ", "x", "/", ".", "-", "\n", "("]) + "".join(s) + rng.choice(["", "", " ", "x", "/", ".", "-", "\n", ")", "8"])


# ---- scope ----------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("pack", INDIC_PACKS)
def test_every_indic_pack_takes_the_indic_path_whatever_its_label(pack):
    text = ("मोबाइल: 98765 43210\nईमेल: ravi" + AT + "gmail.com")
    for lang in ("hi", "bn", "en", None, ""):
        assert NEW_F1(dict(doc(text, pack), lang_label=lang)) == expected(text)
    assert expected(text)[0] == "fix"


# ---- random documents -----------------------------------------------------------------------------------------------------

def random_fragment(rng):
    k = rng.random()
    if k < 0.30:
        return rng.choice(LINES)
    if k < 0.55:
        return rng.choice(LABELS) + rng.choice(variants(rng.choice(MOBILES + LANDLINES)))
    if k < 0.65:
        return rng.choice(["", "Toll free ", "टोल फ्री ", "helpline "]) + rng.choice(variants(rng.choice(TOLL_FREE)))
    if k < 0.80:
        return rng.choice(EMAIL_LABELS) + rng.choice(EMAILS)
    if k < 0.88:
        return mutate(rng, rng.choice(PHONES), "0123456789 -+()९८७")
    return rng.choice(["Total 1800 items", "१८०० रुपये", "2023-24", "आयु 98", "0", "1860", "फ़ोन नंबर: ९८७६५ ४३२१०"])


def random_doc(rng):
    lines = [random_fragment(rng) for _ in range(rng.randint(0, 12))]
    return rng.choice(["\n", "\n", "\n\n", "\r\n"]).join(lines)


def test_random_documents_match_old_rule_and_cover_every_branch():
    rng = random.Random(8)
    seen = {"keep": 0, "fix": 0}
    has = {"indic digits": 0, "@": 0, "1800|1860": 0, "phone masked": 0, "email masked": 0, "toll-free kept": 0, "no digits": 0}
    for i in range(4000):
        text = random_doc(rng)
        pack = INDIC_PACKS[i % len(INDIC_PACKS)]
        action = same(text, pack)
        seen[action] += 1
        out = expected(text)[1]
        has["indic digits"] += bool(c._F1I_INDIC_DIGIT.search(text))
        has["@"] += "@" in text
        has["1800|1860"] += ("1800" in text or "1860" in text)
        has["phone masked"] += out.count("<PHONE>") > text.count("<PHONE>")
        has["email masked"] += out.count("<EMAIL>") > text.count("<EMAIL>")
        has["toll-free kept"] += bool(c._F1I_TOLL_FREE.search(text.translate(c._F1I_DIGITS))) and "<PHONE>" not in out
        has["no digits"] += not re.search(r"\d", text)
    assert seen["keep"] > 300 and seen["fix"] > 1500, seen
    assert all(v > 100 for v in has.values()), has      # every guard is hit both ways
