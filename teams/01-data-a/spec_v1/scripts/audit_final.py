"""Independent audit of ../medicine_code.md: what the 1% harm test cannot see. Reads the sheet like harm_test.py.

  1 new damage     python ast.parse and bracket balance, before vs after, per rule, on every fixed document
  2 over-removal   non-comment lines and special comments (shebang, build tags, encoding lines) deleted by a rule
  3 idempotence    each rule, and the sheet
  4 guard          a row outside LANGS passes unchanged
  5 residue        markers, placeholders, CR left in what the sheet keeps
  6 risky drops    dropped documents with no disease label from any reader
  7 dead rules     rules that never act inside the sheet on a pack they are on
  8 order          whole-sheet outcome with the stages run in reverse order
  9 coverage       diseases seen more than 5 times in a pack, and how many rows the sheet treats

  python -I audit_final.py <checkout> <packs dir>   -> printed summary
"""
import ast, difflib, hashlib, importlib.util, json, re, sys, textwrap, warnings
from collections import Counter, defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ce", HERE / "compile_evidence.py")
ce = importlib.util.module_from_spec(spec); sys.modules["ce"] = ce; spec.loader.exec_module(ce)
SHEET = HERE.parent / "sheets" / "medicine_code.md"
data = ce.load_data()
rules = []
for b in re.findall(r"```python\n(.*?)```", SHEET.read_text(encoding="utf-8"), re.S):
    ns = {"__name__": "rules"}; exec(textwrap.dedent(b), ns)
    rules.append(dict(id=ns["RULE_ID"], code=ns["CODE"], action=ns["ACTION"], langs=ns["LANGS"], med=ns["medicine"]))
report = {}


def parses(t):
    try: ast.parse(t); return True
    except (SyntaxError, ValueError, RecursionError, MemoryError): return False


def balance(t):
    return (t.count("{") - t.count("}"), t.count("(") - t.count(")"), t.count("[") - t.count("]"))


COMMENT = re.compile(r"^\s*(//|/\*|\*|#(?!include|define|if|else|endif|pragma|ifdef|ifndef|undef)|--|\*/|<!--|\"\"\"|''')")
SPECIAL = {"shebang": re.compile(r"^#!"), "encoding": re.compile(r"coding[:=]"), "go build tag": re.compile(r"^\s*//\s*(go:build|\+build)"),
           "go directive": re.compile(r"^\s*//go:"), "rust inner doc": re.compile(r"^\s*//!"), "doc comment": re.compile(r"^\s*(///|/\*\*)"),
           "nolint/pragma": re.compile(r"(nolint|eslint-|@ts-|pylint:|noqa|#\s*pragma|type:\s*ignore|@flow|use strict)")}


def code_only(t, py):
    if py: return re.sub(r"\s+", "", re.sub(r"(?m)^\s*#.*$", "", t))
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S); t = re.sub(r"(?m)//.*$", "", t)
    return re.sub(r"\s+", "", t)


def removed_lines(old, new):
    a, b = old.split("\n"), new.split("\n")
    if len(a) > 6000: return []
    out = []
    for tag, i1, i2, _, _ in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"): out += a[i1:i2]
    return out


damage, over, not_idem, guard_bad, dead = defaultdict(Counter), defaultdict(Counter), defaultdict(list), [], defaultdict(Counter)
samples = defaultdict(list)
res, residue, risky = {}, {}, defaultdict(list)
MARK = re.compile(r"\A<(?:reponame|filename|gh_stars)>")
PH = re.compile(r"<(?:NAME|EMAIL|KEY|PASSWORD)>")
for pack, d in data.items():
    lab_any = set().union(*d["sick"].values())
    out_rows = {}; py = pack == "code-python"
    res_c = Counter()
    for r in d["rows"]:
        x, state = dict(r), "keep"
        for ru in rules:
            if r["lang_label"] not in ru["langs"]: continue
            before = x["text"]
            a, t = ru["med"](dict(x))
            if a == "drop":
                state = "drop"; dead[ru["id"]][pack] += 1
                if r["doc_id"] not in lab_any: risky[ru["id"]].append((pack, r["doc_id"]))
                break
            if t != before:
                dead[ru["id"]][pack] += 1
                if py and parses(before) and not parses(t):
                    damage[ru["id"]]["python no longer parses"] += 1; samples[ru["id"], "parse"].append(r["doc_id"])
                b0, b1 = balance(before), balance(t)
                if b0 != b1:
                    damage[ru["id"]]["brackets changed"] += 1; samples[ru["id"], "brackets"].append((pack, r["doc_id"], b0, b1))
                for line in (removed_lines(before, t) if ru["code"] in ("E4", "C1", "A4") else []):
                    if not line.strip(): continue
                    for k, rx in SPECIAL.items():
                        if rx.search(line): over[ru["id"]][k] += 1; samples[ru["id"], k].append((pack, r["doc_id"]))
                if ru["code"] in ("E4", "C1", "A4", "F1") and code_only(before, py) != code_only(t, py):
                    over[ru["id"]]["CODE CHANGED"] += 1; samples[ru["id"], "code"].append((pack, r["doc_id"]))
                a2, t2 = ru["med"](dict(x, text=t))
                if a2 == "drop" or t2 != t: not_idem[ru["id"]].append((pack, r["doc_id"]))
                x["text"] = t
                state = "fix"
        if state != "drop":
            out_rows[r["doc_id"]] = x["text"]
            res_c["markers"] += bool(MARK.search(x["text"])); res_c["placeholders"] += bool(PH.search(x["text"])); res_c["CR"] += "\r" in x["text"]
        for ru in rules:
            if r["lang_label"] in ru["langs"]: continue
            a, t = ru["med"](dict(r))
            if a != "keep" or t != r["text"]: guard_bad.append((ru["id"], r["doc_id"]))
    residue[pack] = dict(res_c)
    res[pack] = out_rows

print("== 1 new damage"); [print(" ", k, dict(v), samples[k, "parse"][:3], samples[k, "brackets"][:3]) for k, v in damage.items()] or print("  none")
print("== 2 over-removal")
for k, v in over.items(): print(" ", k, dict(v))
for key, val in samples.items():
    if key[1] == "code": print("   code lines,", key[0], len(val), val[:4])
print("== 3 not idempotent", {k: v[:4] for k, v in not_idem.items()} or "none")
print("== 4 guard failures", guard_bad[:5] or "none")
print("== 5 residue after the sheet", residue)
print("== 6 drops with no disease label from any reader", {k: (len(v), v[:3]) for k, v in risky.items()} or "none")
print("== 7 acts per rule inside the sheet")
for ru in rules:
    packs = [p for p in data if {"code-go": "go", "code-rust": "rust", "code-js-ts": "javascript", "code-java": "java", "code-cpp": "cpp", "code-python": "python"}[p] in ru["langs"]]
    print(f"  {ru['id']:11}{ru['code']} {ru['action']:9}", {p.replace('code-', ''): dead[ru['id']][p] for p in packs})
# 8 order: reversed stages must not change which documents end up dropped
rev = list(reversed(rules)); moved = Counter()
for pack, d in data.items():
    for r in d["rows"]:
        x = dict(r); dropped = False
        for ru in rev:
            if r["lang_label"] not in ru["langs"]: continue
            a, t = ru["med"](dict(x))
            if a == "drop": dropped = True; break
            x["text"] = t
        moved[pack] += dropped != (r["doc_id"] not in res[pack])
print("== 8 drop decisions that change if the order is reversed", dict(moved))
# 9 coverage
print("== 9 diseases seen more than 5 times in a pack")
for pack, d in data.items():
    line = []
    for c, ids in sorted(d["sick"].items()):
        if len(ids) <= 5: continue
        codes = [ru for ru in rules if ru["code"] == c and d["rows"][0]["lang_label"] in ru["langs"]]
        rows = {r["doc_id"]: r for r in d["rows"]}
        treated = sum(1 for i in ids if i not in res[pack] or res[pack][i] != rows[i]["text"])
        line.append(f"{c} {treated}/{len(ids)}" + ("" if codes else " (NO RULE OF THIS CODE)"))
    print(" ", pack.replace("code-", ""), "; ".join(line))
print("== digests")
for pack in data:
    g = (ce.TEAM / "gold" / f"{pack}_gold.csv").read_bytes(); pk = (ce.PACKS / f"{pack}.parquet").read_bytes()
    print(" ", pack, "gold", hashlib.sha256(g).hexdigest()[:16], "pack", hashlib.sha256(pk).hexdigest()[:16])
