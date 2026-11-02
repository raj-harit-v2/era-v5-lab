"""Stage 90 of the sheet: what is left after cleaning. Empty docs, and docs left with no code. Run as a test, not a rule. IDs and counts only.

  python -I post_clean.py <sheet> <packs dir>
"""
import re, sys, textwrap
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding="utf-8")
NO_CODE = re.compile(r"^\s*($|//|/\*|\*|#(?!\[)|package\b|import\b|using\b|use\b|from\b.*\bimport\b|mod\b|extern\b|\"\"\"|''')")
def no_code(t): return all(NO_CODE.match(l) for l in re.sub(r"/\*.*?\*/", "", t, flags=re.S).split("\n"))
rules = []
for b in re.findall(r"```python\n(.*?)```", open(sys.argv[1], encoding="utf-8").read(), re.S):
    ns = {"__name__": "r"}; exec(textwrap.dedent(b), ns); rules.append(ns["medicine"])
for p in ["go", "rust", "js-ts", "java", "cpp", "python"]:
    empty, left, before = [], [], []
    for r in pq.read_table(f"{sys.argv[2]}/code-{p}.parquet").to_pylist():
        d = dict(r); dropped = False
        for m in rules:
            a, t = m(d)
            if a == "drop": dropped = True; break
            d["text"] = t
        if dropped: continue
        t = d["text"]
        if not t.strip(): empty.append(r["doc_id"])
        elif t != r["text"] and no_code(t): (before if no_code(r["text"].split("\n", 1)[1] if r["text"].startswith("<") and "\n" in r["text"] else r["text"]) else left).append(r["doc_id"])
    print(p, "empty", len(empty), "| no code now and no code before", len(before), "| no code now, had code before", len(left), left)
