"""Does the F1 rule work, with and without tree-sitter, and what does B4 do to its tags? IDs, counts and made-up values only.

  1 real      F1 hits per pack, by kind and by where they sit (comment, string, code)
  2 planted   made-up details put into real gold docs: right tag, nothing else changed, organisations and look-alikes kept
  3 b4        where the existing <EMAIL> tokens sit, and three ways to run B4 with F1

  venv/python f1_eval.py <checkout> <packs dir> [docs per pack for planting, default 40]
"""
import ast, csv, re, sys
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path
import pyarrow.parquet as pq
from tree_sitter_language_pack import get_parser
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import clean as c
WT, PACKS = Path(sys.argv[1]), Path(sys.argv[2])
N_PLANT = int(sys.argv[3]) if len(sys.argv) > 3 else 40
PACK_IDS = ["code-go", "code-rust", "code-js-ts", "code-java", "code-cpp", "code-python"]
PARSERS = {l: get_parser(l) for l in ["go", "rust", "javascript", "typescript", "java", "cpp", "python"]}
AT = "@"
TAG = re.compile(r"<(?:EMAIL|PHONE|ADDRESS)>")
BAD_PREFIX = re.compile(r"""^(#+|/\*+|/+)""")


def spans(text, lang):
    """Sorted (start byte, end byte, 'comment' or 'string') of the text-bearing nodes, and whether the file parsed cleanly."""
    src = text.encode("utf-8", "replace")
    root = PARSERS[lang].parse(src).root_node
    out, stack = [], [root]
    while stack:
        n = stack.pop()
        if "comment" in n.type: out.append((n.start_byte, n.end_byte, "comment"))
        elif "string" in n.type or n.type == "jsx_text": out.append((n.start_byte, n.end_byte, "string"))
        else: stack.extend(n.children)
    return sorted(out), root.has_error


def where(sp, starts, b):
    i = bisect_right(starts, b) - 1
    return sp[i][2] if i >= 0 and sp[i][0] <= b < sp[i][1] else "code"


def line_hits(line, previous):
    """(start, end, tag) on one line, by the same tests as clean.f1."""
    return c._f1_hits(line, previous)


def f1_variant(text, lang, tree):
    """F1 with no listing drop. tree=True replaces only inside comments and strings. Returns new text and [(kind, place)]."""
    lines, pos, previous, found, out = text.split("\n"), 0, "", [], []
    sp, starts = (None, None)
    for line in lines:
        hits = line_hits(line, previous)
        if hits and sp is None:
            sp = spans(text, lang)[0]; starts = [s[0] for s in sp]
        new, last = [], 0
        for s, e, tag in hits:
            place = where(sp, starts, len(text[:pos + s].encode("utf-8", "replace")))
            found.append((tag, place))
            if tree and place == "code": continue
            new += [line[last:s], tag]; last = e
        out.append("".join(new) + line[last:])
        pos += len(line) + 1; previous = line
    return "\n".join(out), found


def plant(text, lang, value, place):
    sp = spans(text, lang)[0]
    src = text.encode("utf-8", "replace")
    for s, e, kind in sp:
        if kind != place: continue
        body = src[s:e].decode("utf-8", "replace")
        if place == "comment":
            m = BAD_PREFIX.match(body)
            if not m: continue
            cut = m.end()
        else:
            m = re.search(r"""["'`]""", body)
            if not m: continue
            cut = m.end()
        at = s + len(body[:cut].encode("utf-8"))
        return (src[:at] + f" {value} ".encode("utf-8") + src[at:]).decode("utf-8")
    return None


# (name, what goes in, the part that must become the tag; None means it must stay)
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
KEEP = [("org role email", f"support{AT}acme.io"), ("office gov email", f"clerk{AT}city.gov"), ("org phone", "Acme Ltd 555-010-0199"), ("org address", "City Council 12 Elm Grove Road"),
        ("example email", f"user{AT}example.com"), ("git address", f"git{AT}github.com"), ("date", "2021-03-14"), ("version", "1.2.3.4"), ("ip", "192.168.100.200"), ("digit groups", "123 456 7890"),
        ("retina file", f"logo{AT}2x.png"), ("npm scope", f"{AT}types/node"), ("package version", f"foo{AT}1.2.3"), ("uuid", "a1b2c3d4-0000-1111-2222-333344445555"), ("byte size street", "8 Bit Drive")]
b4_fix = {k: v for k, v in [("<NAME>", "AUTHOR"), ("<KEY>", "EXAMPLE_KEY"), ("<PASSWORD>", "EXAMPLE_PASSWORD")]}
def b4_keep_email(t):
    for k, v in b4_fix.items(): t = t.replace(k, v)
    return t
def pipeline_before_b4(r):
    d = dict(r)
    for make in c._PIPELINES["code"]:
        if make is c._code_b4_009: return d["text"], None
        a, t = make()(d)
        if a == "drop": return None, make
        d["text"] = t
def after_b4(t, lang_row):
    d = dict(lang_row, text=t)
    seen = False
    for make in c._PIPELINES["code"]:
        if seen:
            a, x = make()(d)
            if a == "drop": return None
            d["text"] = x
        if make is c._code_b4_009: seen = True
    return d["text"]
def parses(t):
    try: ast.parse(t); return True
    except (SyntaxError, ValueError, RecursionError, MemoryError): return False


pos_res, keep_res, code_res = defaultdict(Counter), defaultdict(Counter), Counter()
tags_seen, parse_broke = Counter(), Counter()
print("== 1 real docs: F1 hits by kind and place (made only after the rules before it)")
for pack in PACK_IDS:
    rows = pq.read_table(PACKS / f"{pack}.parquet").to_pylist()
    gold = {r["doc_id"] for r in csv.DictReader(open(WT / f"teams/01-data-a/gold/{pack}_gold.csv", encoding="utf-8"))}
    rc, tree_docs, reg_docs, gold_r, gold_t, same = Counter(), set(), set(), 0, 0, 0
    tok_place, v0, v1, v2, broke0, broke1, only_email, gold_v1 = Counter(), [], [], [], 0, 0, 0, 0
    labelled_b4 = set()
    for f in (WT / "diagnosis/submissions" / pack).glob("*/labels.csv"):
        raw = f.read_bytes()
        try: txt = raw.decode("utf-8-sig")
        except UnicodeDecodeError: txt = raw.decode("cp1252", "replace")
        for x in csv.DictReader(txt.splitlines()):
            if "B4" in (x.get("diseases") or ""): labelled_b4.add((x.get("doc_id") or "").strip())
    for r in rows:
        before, dropped = pipeline_before_b4(r)
        if before is None: continue
        full = c._run(r, *c._PIPELINES["code"])[1]
        new_r, found = f1_variant(full, r["lang_label"], False)
        new_t, _ = f1_variant(full, r["lang_label"], True)
        same += new_t == c.f1(dict(r, text=full))[1]
        for k in found: rc[k] += 1
        if new_r != full: reg_docs.add(r["doc_id"]); gold_r += r["doc_id"] in gold
        if new_t != full: tree_docs.add(r["doc_id"]); gold_t += r["doc_id"] in gold
        # B4: where the old tokens sit, and three orders
        if "<EMAIL>" in before:
            sp = spans(before, r["lang_label"])[0]; starts = [s[0] for s in sp]
            for m in re.finditer("<EMAIL>", before):
                tok_place[where(sp, starts, len(before[:m.start()].encode("utf-8", "replace")))] += 1
            if not re.search("<(NAME|KEY|PASSWORD)>", before) and r["doc_id"] in labelled_b4: only_email += 1
        # now: B4 then F1, second run
        once = c.clean(r)
        if once[0] != "drop" and c.clean(dict(r, text=once[1])) != ("keep", once[1]): v0.append(r["doc_id"])
        # fix: B4 leaves <EMAIL>, F1 after
        t1 = after_b4(b4_keep_email(before), r)
        if t1 is not None:
            a, t1f = c.f1(dict(r, text=t1))
            if t1f != r["text"] and r["doc_id"] in gold: gold_v1 += 1
            b, t2 = pipeline_before_b4(dict(r, text=t1f))
            if b is not None:
                t2b = after_b4(b4_keep_email(b), r)
                if c.f1(dict(r, text=t2b))[1] != t1f: v1.append(r["doc_id"])
            if pack == "code-python" and parses(r["text"]):
                broke0 += once[0] != "drop" and not parses(once[1])
                broke1 += not parses(t1f)
        # other order: F1 then B4: the tag does not survive
        if before is not None:
            pass
    print(f"{pack[5:]:7} regex+tree == clean.f1 on {same} docs | regex docs {len(reg_docs)} gold {gold_r} | regex+tree docs {len(tree_docs)} gold {gold_t} | hits {dict(rc)}")
    print(f"        B4: <EMAIL> tokens by place {dict(tok_place)} | second run changes: now {len(v0)} {v0[:2]}, B4 keeps <EMAIL> {len(v1)} | gold changed with B4 keeping <EMAIL> {gold_v1} | labelled B4 docs holding only <EMAIL> {only_email}" + (f" | python parse broken: now {broke0}, B4 keeps <EMAIL> {broke1}" if pack == "code-python" else ""))
    # 2 planting
    golds = sorted((r for r in rows if r["doc_id"] in gold), key=lambda r: r["doc_id"])[:N_PLANT]
    for r in golds:
        lang = r["lang_label"]
        for place in ("comment", "string"):
            for name, val, part, tag in POSITIVE:
                p = plant(r["text"], lang, val, place)
                if p is None: continue
                want = p.replace(part, tag, 1)
                for mode, tree in (("regex", False), ("tree", True)):
                    got, _ = f1_variant(p, lang, tree)
                    pos_res[(name, place)][mode + "_ok"] += got == want
                    pos_res[(name, place)][mode + "_n"] += 1
                    for t in TAG.findall(got): tags_seen[t] += 1
                    if tree and got == want and spans(got, lang)[1] and not spans(p, lang)[1]: parse_broke[place] += 1  # p, not the doc: planting into a Python triple quote breaks it by itself
            for name, val in KEEP:
                p = plant(r["text"], lang, val, place)
                if p is None: continue
                for mode, tree in (("regex", False), ("tree", True)):
                    got, _ = f1_variant(p, lang, tree)
                    keep_res[name][mode + "_ok"] += got == p
                    keep_res[name][mode + "_n"] += 1
        p = r["text"].rstrip("\n") + "\nx = 555-010-0199\n"  # arithmetic in code, shaped like a phone
        for mode, tree in (("regex", False), ("tree", True)):
            code_res[mode + "_kept"] += f1_variant(p, lang, tree)[0] == p
            code_res[mode + "_n"] += 1
print("\n== 2 planted in real gold docs. Share where the right tag went in and nothing else changed")
print(f"{'made-up value':24} {'comment regex':>14} {'comment tree':>13} {'string regex':>13} {'string tree':>12}")
for name, *_ in POSITIVE:
    a, b = pos_res[(name, "comment")], pos_res[(name, "string")]
    pct = lambda d, m: f"{100 * d[m + '_ok'] / max(1, d[m + '_n']):.0f}%"
    print(f"{name:24} {pct(a, 'regex'):>14} {pct(a, 'tree'):>13} {pct(b, 'regex'):>13} {pct(b, 'tree'):>12}")
print("\nmust stay unchanged     regex   tree")
for name, _ in KEEP:
    d = keep_res[name]
    print(f"{name:24} {100 * d['regex_ok'] / max(1, d['regex_n']):.0f}%  {100 * d['tree_ok'] / max(1, d['tree_n']):.0f}%")
print("\nphone-shaped arithmetic in code, kept:", {k: code_res[k] for k in sorted(code_res)})
print("tags written:", dict(tags_seen), "| any other tag:", any(t not in ("<EMAIL>", "<PHONE>", "<ADDRESS>") for t in tags_seen))
print("right tag but file newly fails to parse, by place:", dict(parse_broke))
