"""Two sheets over all six packs: which docs end differently. Shows the reorder changed nothing beyond the swapped rules. IDs only.

  python -I sheet_compare.py <old sheet> <new sheet> <packs dir>
"""
import re, sys, textwrap
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding="utf-8")
def load(p):
    out = []
    for b in re.findall(r"```python\n(.*?)```", open(p, encoding="utf-8").read(), re.S):
        ns = {"__name__": "r"}; exec(textwrap.dedent(b), ns); out.append((ns["RULE_ID"], ns["medicine"]))
    return out
def run(rules, r):
    d = dict(r)
    for rid, m in rules:
        a, t = m(d)
        if a == "drop": return ("drop", rid)
        d["text"] = t
    return ("kept", d["text"])
old, new = load(sys.argv[1]), load(sys.argv[2])
for p in ["go", "rust", "js-ts", "java", "cpp", "python"]:
    diff = []
    for r in pq.read_table(f"{sys.argv[3]}/code-{p}.parquet").to_pylist():
        a, b = run(old, r), run(new, r)
        if a[0] != b[0] or (a[0] == "kept" and a[1] != b[1]):
            diff.append((r["doc_id"], a[1] if a[0] == "drop" else "kept", b[1] if b[0] == "drop" else "kept"))
    print(p, len(diff), diff[:14])
