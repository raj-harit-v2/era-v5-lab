"""Regex rules on the rows labelled with a disease: what they catch, what the missed rows look like, and the short-note E4 option. Counts only.

  python -I regex_on_issues.py <checkout> <packs dir>
"""
import importlib.util, json, re, sys, textwrap
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ce", HERE / "compile_evidence.py"); ce = importlib.util.module_from_spec(spec); sys.modules["ce"] = ce; spec.loader.exec_module(ce)
data = ce.load_data(); ev = json.load(open(HERE.parent / "results" / "sheets" / "evidence.json", encoding="utf-8"))
LIC = re.compile(r"(?i)licen[cs]e|copyright|all rights reserved|spdx|permission is hereby|redistribut|warrant")
GEN = re.compile(r"(?i)generated|do not edit|do not modify|auto-?gen|machine generated")
PH = re.compile(r"<(?:NAME|EMAIL|KEY|PASSWORD)>")
AUTH = re.compile(r"(?i)(?:@author|created by|author:)\s+\S")
PICK = {"E4": {"code-go": ["DA-E4-005", "amukka:E4fix"], "code-rust": ["amukka:E4fix"], "code-js-ts": ["DA-E4-007"], "code-java": ["amukka:E4fix", "RaviNaik:E4"], "code-cpp": ["amukka:E4fix"], "code-python": ["amukka:E4fix"]},
        "E1": {"code-go": ["DA-E1-001"], "code-rust": ["DA-E1-004"], "code-js-ts": ["DA-E1-008"], "code-java": ["DA-E1-006"], "code-cpp": ["DA-E1-005", "DA-E1-007"], "code-python": ["DA-E1-004"]},
        "C1": {"code-go": ["DA-C1-004"], "code-java": ["DA-C1-005"]}, "B4": {p: ["DA-B4-009"] for p in data}, "B3": {p: ["DA-B3-001"] for p in data},
        "A2": {p: ["DA-A2-007"] for p in data}, "A1": {p: ["DA-A1-001"] for p in data}, "E2": {p: ["DA-E2-001"] for p in data}, "E3": {p: ["DA-E3-003", "new:E3"] for p in data}, "F1": {"code-java": ["DA-F1-003"]}}
def hit(r, p): d = ev["rules"][r]["per"][p]; return set(d["fix"]) | set(d["drop"])
def head_block(t):
    """Lines of the first comment block after any marker line, and whether it has licence words."""
    ls = t.split("\n"); i = 0
    while i < len(ls) and (not ls[i].strip() or ls[i].startswith("<")): i += 1
    j = i
    if i < len(ls) and ls[i].lstrip().startswith("/*"):
        while j < len(ls) and "*/" not in ls[j]: j += 1
        j += 1
    else:
        while j < len(ls) and re.match(r"\s*(//|#(?!include|pragma|ifndef|define|if|\[|!))", ls[j]): j += 1
    return j - i, "\n".join(ls[i:j])
for code, per in PICK.items():
    print(f"\n== {code}")
    for p, d in data.items():
        ids = d["sick"].get(code, set())
        if not ids: continue
        rules = per.get(p, [])
        got = set().union(*[hit(r, p) for r in rules]) if rules else set()
        miss = ids - got; rows = {r["doc_id"]: r for r in d["rows"]}; c = Counter()
        for i in miss:
            t = rows[i]["text"]; n, b = head_block(t)
            if code == "E4":
                head = "\n".join(t.split("\n")[:40])
                c["header note under 5 lines" if LIC.search(b) and n < 5 else "header block 5+ lines, mostly not licence" if LIC.search(b) else "licence word later in the file" if LIC.search(t) else "no licence word"] += 1
            elif code == "E1":
                c["has a generator word" if GEN.search(t) else "very long line" if any(len(l) > 800 for l in t.split("\n")) else "no marker at all"] += 1
            elif code == "F1":
                c["author line" if AUTH.search(t) else "placeholder" if PH.search(t) else "other"] += 1
            elif code == "B4":
                c["placeholder present" if PH.search(t) else "no placeholder, other redaction form"] += 1
            else:
                c["missed"] += 1
        print(f"  {p[5:]:7} {len(ids & got):3}/{len(ids):3}  missed: {dict(c)}")
print("\n== E4 option: also remove a header of 1 to 4 lines with a licence word. Docs touched, gold docs touched, labelled rows, labelled-clean docs")
for p, d in data.items():
    hit = set()
    for r in d["rows"]:
        n, b = head_block(r["text"])
        if 1 <= n < 5 and LIC.search(b): hit.add(r["doc_id"])
    sick = d["sick"].get("E4", set())
    print(f"  {p[5:]:7} docs {len(hit):3}  gold {len(hit & d['gold'])}  rows {len(hit & sick)}/{len(sick)}  clean {len(hit & d['clean'] - d['gold'])}")
