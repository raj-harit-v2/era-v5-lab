"""What makes DA-E1-008 drop each js-ts file: the path alone, or the text. Also DA-E4-006 against DA-E4-007 on js-ts. Ids and counts only.

  python -I e1_triggers.py <rules/code-js-ts/Sagar063.py> <rules/code-rust/riyaagrahari.py or the E4-006 file> <pack.parquet> <labels of js-ts dir>
"""
import csv, glob, importlib.util, re, sys
from collections import Counter
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding="utf-8")
def load(p):
    s = importlib.util.spec_from_file_location("m" + str(abs(hash(p))), p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
sg = load(sys.argv[1]); e6 = load(sys.argv[2]).RULES_BY_ID["DA-E4-006"]
rows = pq.read_table(sys.argv[3]).to_pylist()
votes = {}
for f in glob.glob(sys.argv[4] + "/*/labels.csv"):
    for r in csv.DictReader(open(f, encoding="utf-8")):
        votes.setdefault(r["doc_id"], []).append((r["verdict"], r["diseases"]))
c = Counter()
for r in rows:
    if sg.medicine_e1(r) == r["text"]: continue
    p = r.get("url") or ""; t = r["text"]
    folder = None if p.endswith(".d.ts") else sg._BUILD_PATH.search(p)
    txt = [n for n, b in [("sourcemap", re.search(r"^\s*//# sourceMappingURL=", t, re.M)), ("compiled", sg._COMPILED.search(t)), ("header", sg._GENERATED.search(sg._header_comment(t))),
                          ("minified", sg._minified(t)), ("long line", max(map(len, t.split("\n"))) > 1000), ("html links", t.count(".html#") >= 3), ("searchData", re.search(r"var searchData\s*=", t))] if b]
    c["path only" if folder and not txt else "text" if txt else "?"] += 1
    v = Counter(a for a, _ in votes.get(r["doc_id"], []))
    print(r["doc_id"], "folder:", folder.group(2) if folder else "-", "text:", ",".join(txt) or "-", "votes:", dict(v), "E1 by", sum("E1" in d for _, d in votes.get(r["doc_id"], [])))
print(c)
same = diff = 0
for r in rows:
    a, b = sg.medicine_e4(r["text"]), e6(r["text"])
    b = b if isinstance(b, str) else b[1] if isinstance(b, tuple) else r["text"]
    if a != r["text"] or b != r["text"]:
        same += a == b; diff += a != b
        print(r["doc_id"], "E4-007 removes", len(r["text"]) - len(a), "E4-006 removes", len(r["text"]) - len(b))
print("same text", same, "different", diff)
