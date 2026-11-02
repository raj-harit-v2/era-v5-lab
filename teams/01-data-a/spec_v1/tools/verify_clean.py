"""Check clean.py on the packs. Prints IDs, offsets, counts and masked shapes only, never a private value.

  python verify_clean.py <checkout> <packs dir> <medicine_code.md>

  1 clean.py without F1 gives the same action and text as the sheet, doc by doc
  2 what the new F1 rule does per pack: gold, labelled F1 rows, labelled-clean docs
  3 clean(clean(doc)) == clean(doc)
"""
import csv, re, sys, textwrap
from collections import Counter
from pathlib import Path
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import clean as c
WT, PACKS, SHEET = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sheet = []
for b in re.findall(r"^```python\n(.*?)^```", SHEET.read_text(encoding="utf-8"), re.S | re.M):
    if 'RULE_ID = "' in b:
        ns = {"__name__": "r"}; exec(textwrap.dedent(b), ns); sheet.append(ns["medicine"])
def run_sheet(doc):
    d = dict(doc)
    for m in sheet:
        a, t = m(d)
        if a == "drop": return ("drop", doc["text"])
        d["text"] = t
    return ("fix" if d["text"] != doc["text"] else "keep", d["text"])
def shape(s): return re.sub(r"[A-Za-z]", "x", re.sub(r"\d", "9", s))
for p in ["go", "rust", "js-ts", "java", "cpp", "python"]:
    pack = f"code-{p}"
    rows = pq.read_table(PACKS / f"{pack}.parquet").to_pylist()
    gold = {r["doc_id"] for r in csv.DictReader(open(WT / f"teams/01-data-a/gold/{pack}_gold.csv", encoding="utf-8"))}
    f1_sick, clean_ids = set(), set()
    for f in (WT / "diagnosis/submissions" / pack).glob("*/labels.csv"):
        raw = f.read_bytes()
        try: txt = raw.decode("utf-8-sig")
        except UnicodeDecodeError: txt = raw.decode("cp1252", "replace")
        for r in csv.DictReader(txt.splitlines()):
            v = (r.get("verdict") or "").strip(); d = (r.get("doc_id") or "").strip()
            if v == "clean": clean_ids.add(d)
            elif "F1" in (r.get("diseases") or ""): f1_sick.add(d)
    differ, email_only, again, hits, kinds, drops, samples = 0, 0, [], set(), Counter(), set(), []
    for r in rows:
        before = c._run(r, *c._PIPELINES["code"])
        email_only += "<EMAIL>" in before[1]  # the one planned difference from the merged sheet
        differ += (before[0], before[1].replace("<EMAIL>", "user@example.com")) != run_sheet(r)
        a, t = c.clean(r)
        if a != "drop":
            a2, t2 = c.clean(dict(r, text=t))
            if (a2, t2) != ("keep", t): again.append(r["doc_id"])
        if before[0] == "drop": continue
        fa, ft = c.f1(dict(r, text=before[1]))
        if fa == "drop": drops.add(r["doc_id"]); hits.add(r["doc_id"])
        elif fa == "fix":
            hits.add(r["doc_id"])
            old, new = before[1].split("\n"), ft.split("\n")
            for o, n in zip(old, new):
                if o != n:
                    for k in ("<EMAIL>", "<PHONE>", "<ADDRESS>"): kinds[k] += n.count(k) - o.count(k)
                    if len(samples) < 10:
                        i = next(j for j, (x, y) in enumerate(zip(o, n)) if x != y) if o[:len(n)] != n else 0
                        k = re.search(r"<(EMAIL|PHONE|ADDRESS)>", n[i:])
                        samples.append((r["doc_id"], k.group(1) if k else "?", shape(o[max(0, i - 12):i + 22])))
    print(f"{p}: rows {len(rows)} | sheet vs clean.py differ {differ} (docs keeping <EMAIL> {email_only}) | second run changes {len(again)} {again[:3]} | F1 docs {len(hits)} (drop {len(drops)}) {dict(kinds)} | gold {len(hits & gold)} | labelled F1 {len(hits & f1_sick)}/{len(f1_sick)} | labelled clean {len(hits & clean_ids - gold)}")
    for s in samples[:6]: print("   ", s)
