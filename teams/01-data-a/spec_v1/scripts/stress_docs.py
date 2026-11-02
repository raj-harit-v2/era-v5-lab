"""Which disputed docs the sheet touches, and which reader disputes each. The gold builder leaves these docs out.

  python -I stress_docs.py <checkout> <packs dir> <gold made with build_gold.py --allow-disputed>
"""
import csv, importlib.util, re, sys, textwrap, difflib
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ce", HERE / "compile_evidence.py"); ce = importlib.util.module_from_spec(spec); sys.modules["ce"] = ce; spec.loader.exec_module(ce)
STRESS = Path(sys.argv[3])
data = ce.load_data()
rules = []
for b in re.findall(r"```python\n(.*?)```", open(HERE.parent / "sheets" / "medicine_code.md", encoding="utf-8").read(), re.S):
    ns = {"__name__": "rules"}; exec(textwrap.dedent(b), ns); rules.append((ns["RULE_ID"], ns["LANGS"], ns["medicine"]))
for pack, d in data.items():
    stress = {r["doc_id"] for r in csv.DictReader(open(STRESS / f"{pack}_gold.csv", encoding="utf-8"))}
    labels = {}
    for f in (ce.WT / "diagnosis/submissions" / pack).glob("*/labels.csv"):
        raw = f.read_bytes()
        try: txt = raw.decode("utf-8-sig")
        except UnicodeDecodeError: txt = raw.decode("cp1252", "replace")
        for r in csv.DictReader(txt.splitlines()):
            if r["doc_id"].strip() in stress and r["verdict"].strip() != "clean": labels.setdefault(r["doc_id"].strip(), []).append(f"{f.parent.name}:{r['verdict'].strip()}:{r['diseases'].strip()}")
    for r in d["rows"]:
        if r["doc_id"] not in stress or r["doc_id"] in d["gold"]: continue
        x = dict(r); acts = []
        for rid, langs, med in rules:
            if r["lang_label"] not in langs: continue
            a, t = med(dict(x))
            if a == "drop": acts.append(rid + " DROP"); break
            if t != x["text"]:
                A, B = x["text"].split("\n"), t.split("\n"); n = 0
                for tag, i1, i2, _, _ in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
                    if tag != "equal": n += i2 - i1
                acts.append(f"{rid} ({n} lines)"); x["text"] = t
        if acts: print(pack[5:], r["doc_id"], acts, "| disputed by", labels.get(r["doc_id"]))
