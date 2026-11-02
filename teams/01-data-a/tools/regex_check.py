"""Try a regex on a pack before writing it as a rule. Prints counts and doc_ids with offsets, never the matched text.

  python regex_check.py --pack code-go.parquet --gold code-go_gold.csv --labels <diagnosis/submissions/code-go> --code E4 --regex "(?i)copyright"
  add --where comment or --where string for code: only matches inside comments or strings count (needs tree-sitter-language-pack)
"""
import argparse, csv, re, sys
from bisect import bisect_right
from pathlib import Path
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--pack", type=Path, required=True)
ap.add_argument("--gold", type=Path, required=True)
ap.add_argument("--labels", type=Path, required=True, help="folder with <reader>/labels.csv")
ap.add_argument("--code", required=True, help="disease code, for example E4")
ap.add_argument("--regex", required=True)
ap.add_argument("--where", choices=["all", "comment", "string"], default="all")
ap.add_argument("--show", type=int, default=5, help="how many doc_ids to list in each group")
args = ap.parse_args()
rx = re.compile(args.regex)


def spans(text, lang, kind):
    from tree_sitter_language_pack import get_parser
    out, stack = [], [get_parser(lang).parse(text.encode("utf-8", "replace")).root_node]
    while stack:
        n = stack.pop()
        if kind in n.type: out.append((n.start_byte, n.end_byte))
        else: stack.extend(n.children)
    return sorted(out)


def first_match(row):
    """Offset of the first match that counts, or None."""
    text = row["text"]
    if args.where == "all":
        m = rx.search(text)
        return m.start() if m else None
    sp = None
    for m in rx.finditer(text):
        if sp is None:
            sp = spans(text, row["lang_label"], args.where); starts = [a for a, _ in sp]
        b = len(text[:m.start()].encode("utf-8", "replace")); i = bisect_right(starts, b) - 1
        if i >= 0 and b < sp[i][1]:
            return m.start()
    return None


gold = {r["doc_id"] for r in csv.DictReader(open(args.gold, encoding="utf-8"))}
sick, clean = set(), set()
for f in args.labels.glob("*/labels.csv"):
    raw = f.read_bytes()
    try: txt = raw.decode("utf-8-sig")
    except UnicodeDecodeError: txt = raw.decode("cp1252", "replace")
    for r in csv.DictReader(txt.splitlines()):
        d, v = (r.get("doc_id") or "").strip(), (r.get("verdict") or "").strip()
        if v == "clean": clean.add(d)
        elif v in ("fix", "drop") and args.code in (r.get("diseases") or ""): sick.add(d)
hits = {}
for row in pq.read_table(args.pack, columns=["doc_id", "lang_label", "text"]).to_pylist():
    o = first_match(row)
    if o is not None: hits[row["doc_id"]] = o
limit = max(1, len(gold) // 100) if gold else 0
touched = set(hits) & gold
print(f"docs matched: {len(hits)}")
print(f"gold docs matched: {len(touched)} of {len(gold)}, limit {limit}: {'FAIL' if not gold or len(touched) > limit else 'within the limit'}")
print(f"labelled {args.code} rows matched: {len(set(hits) & sick)} of {len(sick)}")
print(f"labelled clean outside gold, matched: {len(set(hits) & clean - gold)}")
for name, ids in [("gold matched", touched), (f"{args.code} missed", sick - set(hits)), ("matched, not labelled", set(hits) - sick - gold)]:
    print(f"{name}: " + ", ".join(f"{i}" + (f" @{hits[i]}" if i in hits else "") for i in sorted(ids)[:args.show]))
