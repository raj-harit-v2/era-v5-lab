"""test_indic_rules.py - tests every rule in medicine_indic.md on made-up text.

    python -I test_indic_rules.py                prints a report; exit code 0 means every check passes
    python -I test_indic_rules.py --sheet FILE   the same on another sheet in the same form
    python -m pytest test_indic_rules.py         the same checks as pytest tests

Checks for each rule (TSAI's Gate 2 checks for indic_rules/, and Data A's spec v1 checks):
  1. loads         the block runs on its own and defines medicine(doc)
  2. other packs   a document of any other pack comes back as ("keep", text)
  3. result form   medicine(doc) returns ("keep" | "fix" | "drop", str)
  4. ZWJ, ZWNJ     no word the rule keeps loses or gains a ZWJ (U+200D) or ZWNJ (U+200C); deleting a whole
                   repeated sentence or junk line, joiners and all, is allowed
  5. NFC           a fixed document that was NFC is still NFC, and keeps its compatibility characters (no NFKC)
  6. nukta         a fixed document has the same number of nukta signs (counted after NFD, so both spellings count)
  7. second run    the rule run again on its own output changes nothing
Checks 4 to 7 only test a rule that acts on the test text; the report says how many did.
All test text is made up. Joiners are written as \\u200d and \\u200c, because a real joiner is invisible.
The code in medicine_indic.md is run as code: read it first.
"""
import importlib.util
import sys
import time
import unicodedata
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ZWJ, ZWNJ = "‍", "‌"
NUKTA = "़়਼઼଼఼಼"
OTHER_PACK = "en-dclm"
NEEDS_DATA = {  # rules that need a file we do not ship; skipped, with the reason in the report
}

# Made-up sentences: plain text, a word with ZWJ, a word with ZWNJ, and (where the script uses it) a nukta.
NATIVE = {
    "hi": "यह एक छोटा परीक्षण वाक्य है। क्‍ष और क्‌ष दोनों रूप यहाँ हैं। ज़िंदगी एक शब्द है।",
    "mr": "हे एक लहान चाचणी वाक्य आहे. क्‍ष आणि क्‌ष ही दोन रूपे आहेत.",
    "sa": "इदं लघु परीक्षावाक्यम् अस्ति। क्‍ष क्‌ष इति रूपे स्तः।",
    "bn": "এটি একটি ছোট পরীক্ষার বাক্য। র‍্যাব এবং ক্‌ষ দুটি রূপ। বড় একটি শব্দ।",
    "gu": "આ એક નાનું પરીક્ષણ વાક્ય છે. ક્‍ષ અને ક્‌ષ બે રૂપ છે.",
    "kn": "ಇದು ಒಂದು ಸಣ್ಣ ಪರೀಕ್ಷಾ ವಾಕ್ಯ. ಕ್‍ಷ ಮತ್ತು ಕ್‌ಷ ಎರಡು ರೂಪಗಳು.",
    "ta": "இது ஒரு சிறிய சோதனை வாக்கியம். க்‍ஷ மற்றும் க்‌ஷ இரண்டு வடிவங்கள்.",
    "te": "ఇది ఒక చిన్న పరీక్ష వాక్యం. క్‍ష మరియు క్‌ష రెండు రూపాలు.",
    "or": "ଏହା ଏକ ଛୋଟ ପରୀକ୍ଷା ବାକ୍ୟ। କ୍‍ଷ ଏବଂ କ୍‌ଷ ଦୁଇଟି ରୂପ। ବଡ଼ ଏକ ଶବ୍ଦ।",
    "ml": "ഇത് ഒരു ചെറിയ പരീക്ഷണ വാക്യമാണ്. ന്‍ എന്നതും ക്‌ക എന്നതും രണ്ട് രൂപങ്ങൾ.",
}
SCRIPT_BASE = {"hi": 0x0900, "mr": 0x0900, "sa": 0x0900, "bn": 0x0980, "gu": 0x0A80, "or": 0x0B00, "ta": 0x0B80,
               "te": 0x0C00, "kn": 0x0C80, "ml": 0x0D00}
# Made-up junk with no joiners, so a rule that removes it leaves the joiner counts unchanged.
JUNK = [
    "Read more", "Share on WhatsApp | Facebook | Twitter", "Copyright © 2024 Example News. All rights reserved.",
    "Home | About Us | Contact | Privacy Policy", "<p>", "<br/>", "&nbsp;&amp;", "{{ article.title }} undefined NaN",
    "<|endoftext|>", "https://example.org/news/12345", "Write to reader@example.com or call +91 99999 99999",
    "Click here to subscribe", "zero​width﻿junk­", "Ã¤Ã¶ â€™", "lost � byte",
    "tags: news, latest news, breaking news, today news",
]


def make_docs(lang, pack):
    """A clean document and a dirty one for the rule's language, both NFC."""
    native = NATIVE[lang]
    base = SCRIPT_BASE[lang]
    ka, sign_i = chr(base + 0x15), chr(base + 0x3F)
    plain = native.split(" ")[0] + " " + native.split(" ")[1]  # a short line with no joiner, for repeats
    half = " (½)"  # a compatibility character in text that should be kept: an NFKC-style rule would replace it
    dirty_lines = [native + half, JUNK[0], plain, plain, plain, ka + " " + sign_i + ka, *JUNK[1:], native, plain + " and then the"]
    docs = [("clean", native + "\n" + native + half), ("dirty", "\n".join(dirty_lines))]
    for name, text in docs:
        assert unicodedata.is_normalized("NFC", text), f"test text for {lang} ({name}) is not NFC: fix the test"
    return [{"doc_id": f"test-{lang}-{name}", "text": text, "url": "https://example.org/a", "lang_label": "",
             "pack_id": pack} for name, text in docs]


def joiner_changes(before, after):
    """Words the rule kept but whose ZWJ or ZWNJ changed: a word of the output that is a word of the input with its
    joiners taken out, put in or moved. A rule may delete a whole repeated sentence or junk line, joiners and all; it
    may not change the joiners inside text it keeps."""
    bare = lambda w: w.replace(ZWJ, "").replace(ZWNJ, "")
    forms = {}
    for w in before.split():
        forms.setdefault(bare(w), set()).add(w)
    return [w for w in after.split() if bare(w) in forms and w not in forms[bare(w)]]


def nukta_count(text):
    return sum(unicodedata.normalize("NFD", text).count(c) for c in NUKTA)


def compat(text):
    return {c for c in set(text) if unicodedata.decomposition(c).startswith("<")}


def check(rule):
    """[(check name, message)] of the problems found for one rule, and whether the rule acted on the test text."""
    bad, acted = [], False
    lang = rule.ORIGIN.split(", ")[0].split("-")[1]
    docs = make_docs(lang, rule.ORIGIN.split(", ")[0])
    for doc in docs:
        other = dict(doc, pack_id=OTHER_PACK)
        try:
            if rule.medicine(other) != ("keep", other["text"]):
                bad.append(("2 other packs", f"changes a {OTHER_PACK} document"))
        except Exception as e:
            bad.append(("2 other packs", f"error on a {OTHER_PACK} document: {type(e).__name__}: {str(e)[:80]}"))
        try:
            out = rule.medicine(doc)
        except Exception as e:
            bad.append(("3 result form", f"error on the {doc['doc_id']} document: {type(e).__name__}: {str(e)[:80]}"))
            continue
        if not (isinstance(out, tuple) and len(out) == 2 and out[0] in ("keep", "fix", "drop") and isinstance(out[1], str)):
            bad.append(("3 result form", f"returns {type(out).__name__} {str(out)[:60]!r}"))
            continue
        action, new = out
        if action == "keep" and new != doc["text"]:
            bad.append(("3 result form", "says keep but returns changed text"))
        if action == "keep":
            continue
        acted = True
        if action == "drop":
            continue
        before = doc["text"]
        changed = joiner_changes(before, new)
        if changed:
            bad.append(("4 ZWJ, ZWNJ", f"{doc['doc_id']}: {len(changed)} kept word(s) lost or gained a joiner "
                                       f"(ZWJ {before.count(ZWJ)} -> {new.count(ZWJ)}, ZWNJ {before.count(ZWNJ)} -> {new.count(ZWNJ)})"))
        if not unicodedata.is_normalized("NFC", new):
            bad.append(("5 NFC", f"{doc['doc_id']}: the output is not NFC"))
        # only the compatibility characters of text that should be kept: repairing the junk lines can rightly remove
        # one (the mojibake "â€™" holds U+2122 ™, and fixing it to "’" removes it)
        keep_compat = compat(NATIVE[lang] + " (½)")
        if any(new.count(c) < before.count(c) for c in keep_compat):
            bad.append(("5 NFC", f"{doc['doc_id']}: removes or replaces a compatibility character (what NFKC does)"))
        if nukta_count(before) != nukta_count(new):
            bad.append(("6 nukta", f"{doc['doc_id']}: nukta {nukta_count(before)} -> {nukta_count(new)}"))
        try:
            again = rule.medicine(dict(doc, text=new))
            if again != ("keep", new):
                bad.append(("7 second run", f"{doc['doc_id']}: a second run gives {again[0]!r}"))
        except Exception as e:
            bad.append(("7 second run", f"{doc['doc_id']}: error on a second run: {type(e).__name__}"))
    return bad, acted


def load_sheet(sheet):
    spec = importlib.util.spec_from_file_location("load_rules", HERE / "load_rules.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load(sheet) if sheet else mod.load()


def run(sheet=None):
    """Runs every check on every rule. Returns (rules, results, load error or None)."""
    try:
        rules = load_sheet(sheet)
    except Exception as e:
        return [], {}, f"{type(e).__name__}: {e}"
    results = {}
    for i, r in enumerate(rules, 1):
        print(f"\rtesting {i}/{len(rules)} {r.RULE_ID}    ", end="", file=sys.stderr, flush=True)
        if r.RULE_ID in NEEDS_DATA:
            results[r.RULE_ID] = ("skipped", NEEDS_DATA[r.RULE_ID], False, 0.0)
            continue
        t = time.perf_counter()
        bad, acted = check(r)
        results[r.RULE_ID] = ("fail" if bad else "pass", bad, acted, time.perf_counter() - t)
    return rules, results, None


class TestIndicRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules, cls.results, cls.error = run()

    def test_1_loads(self):
        self.assertIsNone(self.error, f"the sheet does not load: {self.error}")
        ids = [r.RULE_ID for r in self.rules]
        self.assertEqual(len(ids), len(set(ids)), "two rules share a RULE_ID")

    def test_2_to_7_every_rule(self):
        for rid, (state, bad, _, _) in self.results.items():
            with self.subTest(rule=rid):
                if state == "skipped":
                    self.skipTest(bad)
                self.assertEqual(bad, [], f"{rid}: " + "; ".join(f"{c}: {m}" for c, m in bad))


def main(argv):
    sheet = Path(argv[argv.index("--sheet") + 1]) if "--sheet" in argv else None
    rules, results, error = run(sheet)
    if error:
        print("check 1 (loads): FAIL -", error)
        return 1
    n = len(results)
    passed = sum(1 for s in results.values() if s[0] == "pass")
    failed = {k: v for k, v in results.items() if v[0] == "fail"}
    skipped = {k: v for k, v in results.items() if v[0] == "skipped"}
    acted = sum(1 for s in results.values() if s[2])
    slow = sorted(((v[3], k) for k, v in results.items() if v[3] > 2.0), reverse=True)
    print(f"rules loaded: {n}   pass: {passed}   fail: {len(failed)}   skipped: {len(skipped)}")
    print(f"rules that acted on the test text (fix or drop): {acted} of {n}; for the others checks 4 to 7 had nothing to test")
    by_check = {}
    for rid, (_, bad, _, _) in failed.items():
        for c, m in bad:
            by_check.setdefault(c, []).append((rid, m))
    for c in sorted(by_check):
        rows = by_check[c]
        print(f"\ncheck {c}: {len({r for r, _ in rows})} rule(s)")
        for rid, m in rows[:40]:
            print(f"  {rid}: {m}")
    for rid, (_, why, _, _) in skipped.items():
        print(f"\nskipped {rid}: {why}")
    if slow:
        print("\nslow rules (seconds for 2 test documents): " + ", ".join(f"{k} {t:.1f}" for t, k in slow[:10]))
    print("\nRESULT:", "ALL CHECKS PASS" if not failed else f"{len(failed)} RULE(S) FAIL A CHECK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
