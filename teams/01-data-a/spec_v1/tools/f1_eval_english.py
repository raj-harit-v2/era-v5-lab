"""Does F1 work on the English packs? The English counterpart of f1_eval.py. IDs, counts and made-up values only.

  python -I f1_eval_english.py <g1-harm-test checkout> <packs dir> [docs per pack for planting, default 40]

../clean.py's f1() runs DA-F1-005 on the English packs (its SCOPE); the shared f1_rule.py runs on the code packs
only. Each check is also made with the shared rule, switched on for en and eng in memory only (prose has no tree, so regex
alone decides), to show what switching it on would do. Neither file is changed.

  1 real      F1 hits per pack after the rules before it: docs changed or dropped, gold docs touched, tags by kind
  2 planted   made-up details (f1_eval.py's values) on a line of their own at the end of real gold docs: the right tag
              and nothing else changed; organisations and look-alikes kept
  3 again     a second clean() leaves every F1 tag as it is

Writes ../results/cleaner/f1_eval_english.json.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent
WT, PACKS = Path(sys.argv[1]), Path(sys.argv[2])
N_PLANT = int(sys.argv[3]) if len(sys.argv) > 3 else 40
PACK_IDS = ["en-dclm", "en-fineweb-edu", "en-nemotroncc", "en-nemotroncc-synth"]
sys.path.insert(0, str(SPEC))
import clean as c
AT = "@"  # pr-guard reads added lines for email addresses, so made-up ones are joined at run time
TAGS = ("<EMAIL>", "<PHONE>", "<ADDRESS>")

# f1_eval.py's made-up values: (name, what goes in, the part that must become the tag, the tag)
POSITIVE = [
    ("email plain", f"jane.doe{AT}mailbox.io", f"jane.doe{AT}mailbox.io", "<EMAIL>"),
    ("email country domain", f"r.kumar_88{AT}post.co.in", f"r.kumar_88{AT}post.co.in", "<EMAIL>"),
    ("phone with a word", "mobile: 555-010-0199", "555-010-0199", "<PHONE>"),
    ("phone +44", "+44 20 7946 0958", "+44 20 7946 0958", "<PHONE>"),
    ("phone (555)", "(555) 010-0199", "(555) 010-0199", "<PHONE>"),
    ("phone US plain", "555-010-0199", "555-010-0199", "<PHONE>"),
    ("phone +91", "+91 98765 43210", "+91 98765 43210", "<PHONE>"),
    ("phone India no code", "phone 98765 43210", "98765 43210", "<PHONE>"),
    ("phone digits only", "phone 5550100199", "5550100199", "<PHONE>"),
    ("address road", "12 Elm Grove Road", "12 Elm Grove Road", "<ADDRESS>"),
    ("address 221B", "221B Baker Street", "221B Baker Street", "<ADDRESS>"),
    ("address India", "18 MG Road", "18 MG Road", "<ADDRESS>"),
    ("address lower case", "12 elm grove road", "12 elm grove road", "<ADDRESS>"),
]
KEEP = [("org role email", f"support{AT}acme.io"), ("office gov email", f"clerk{AT}city.gov"), ("org phone", "Acme Ltd 555-010-0199"),
        ("org address", "City Council 12 Elm Grove Road"), ("example email", f"user{AT}example.com"), ("git address", f"git{AT}github.com"),
        ("date", "2021-03-14"), ("version", "1.2.3.4"), ("ip", "192.168.100.200"), ("digit groups", "123 456 7890"),
        ("retina file", f"logo{AT}2x.png"), ("npm scope", f"{AT}types/node"), ("package version", f"foo{AT}1.2.3"),
        ("uuid", "a1b2c3d4-0000-1111-2222-333344445555"), ("byte size street", "8 Bit Drive")]


def shared(doc):
    """The shared F1, switched on for en and eng for this call only."""
    old = c._F1_LANGS
    c._F1_LANGS = old | {"en", "eng"}
    try:
        return c._shared_f1(doc)
    finally:
        c._F1_LANGS = old


RULES = {"DA-F1-005": c.f1, "shared F1 (in memory)": shared}
assert c._PIPELINES["english"][-1] is c._english_f1_005
before_f1 = lambda r: c._run(r, *c._PIPELINES["english"][:-1])  # every English rule before F1, as clean() runs them


def rows_of(pack):
    """The pack's documents, each with its pack_id: clean.py picks the rules by it."""
    path = PACKS / f"{pack}.parquet"
    cols = [k for k in ("doc_id", "text", "url", "lang_label", "pack_id") if k in pq.read_schema(path).names]
    rows = pq.read_table(path, columns=cols).to_pylist()
    assert all(r.setdefault("pack_id", pack) == pack for r in rows), f"{pack}: a document has another pack_id"
    return rows


def main():
    report = {"real": {}, "planted": {}, "keep": {}, "second_run": {}}
    print("== 1 real docs: F1 after the other English rules")
    for pack in PACK_IDS:
        rows = rows_of(pack)
        gold = {r["doc_id"] for r in csv.DictReader(open(WT / f"teams/01-data-a/gold/{pack}_gold.csv", encoding="utf-8"))}
        out = {}
        for name, fn in RULES.items():
            fixed, dropped, tags = set(), set(), Counter()
            for r in rows:
                a0, t0 = before_f1(r)
                if a0 == "drop":
                    continue
                a, t = fn(dict(r, text=t0))
                if a == "drop":
                    dropped.add(r["doc_id"])
                elif a == "fix":
                    fixed.add(r["doc_id"])
                    for k in TAGS:
                        tags[k] += t.count(k) - t0.count(k)
            g = sorted((fixed | dropped) & gold)
            out[name] = dict(fixed=len(fixed), dropped=len(dropped), gold_touched=g, limit=max(1, len(gold) // 100), tags=dict(tags))
            print(f"  {pack:20} {name:22} fixed {len(fixed):3} dropped {len(dropped):2} | gold touched {len(g)} of {len(gold)} "
                  f"(limit {max(1, len(gold) // 100)}) {g[:3]} | tags {dict(tags)}")
        report["real"][pack] = out

    print(f"\n== 2 planted on a line of their own at the end of real gold docs ({N_PLANT} per pack). Share with the right tag and nothing else changed")
    pos, keep = defaultdict(Counter), defaultdict(Counter)
    for pack in PACK_IDS:
        rows = {r["doc_id"]: r for r in rows_of(pack)}
        gold = sorted(r["doc_id"] for r in csv.DictReader(open(WT / f"teams/01-data-a/gold/{pack}_gold.csv", encoding="utf-8")))[:N_PLANT]
        for d in gold:
            r = rows[d]
            body = r["text"].rstrip("\n")
            for name, fn in RULES.items():
                base = fn(dict(r, text=body))[1]
                for label, value, part, tag in POSITIVE:
                    got = fn(dict(r, text=body + "\n" + value))
                    pos[(label, name)]["n"] += 1
                    pos[(label, name)]["ok"] += got == ("fix", base + "\n" + value.replace(part, tag, 1))
                for label, value in KEEP:
                    got = fn(dict(r, text=body + "\n" + value))
                    keep[(label, name)]["n"] += 1
                    keep[(label, name)]["ok"] += got[1] == base + "\n" + value
    names = list(RULES)
    print(f"  {'made-up value':24}" + "".join(f"{n:>24}" for n in names))
    for label, *_ in POSITIVE:
        print(f"  {label:24}" + "".join(f"{100 * pos[(label, n)]['ok'] / max(1, pos[(label, n)]['n']):>23.0f}%" for n in names))
        report["planted"][label] = {n: [pos[(label, n)]["ok"], pos[(label, n)]["n"]] for n in names}
    print(f"\n  {'must stay unchanged':24}" + "".join(f"{n:>24}" for n in names))
    for label, _ in KEEP:
        print(f"  {label:24}" + "".join(f"{100 * keep[(label, n)]['ok'] / max(1, keep[(label, n)]['n']):>23.0f}%" for n in names))
        report["keep"][label] = {n: [keep[(label, n)]["ok"], keep[(label, n)]["n"]] for n in names}

    print("\n== 3 a second clean() on every English doc F1 changed")
    for pack in PACK_IDS:
        again = []
        n = 0
        for r in rows_of(pack):
            a, once = c.clean(r)
            if a == "drop" or not any(k in once and k not in r["text"] for k in TAGS):
                continue
            n += 1
            if c.clean(dict(r, text=once)) != ("keep", once):
                again.append(r["doc_id"])
        report["second_run"][pack] = dict(docs_with_new_tags=n, changed_again=again)
        print(f"  {pack:20} docs with an F1 tag {n} | a second clean() changes {len(again)} {again[:3]}")
    (SPEC / "results" / "cleaner" / "f1_eval_english.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("\nwrote results/cleaner/f1_eval_english.json")


if __name__ == "__main__":
    main()
