"""The checks of the conflict ledger in ../sheets/spec_v1_english.md: what each English medicine does in the whole sheet run, and
what changes when two stages or two rules swap. IDs and counts only, never text.

  python -I order_checks_english.py <packs dir>

Writes ../results/cleaner/order_checks_english.json.
"""
import json
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
SHEET = HERE.parent / "sheets" / "medicine_english.md"
PACKS_DIR = Path(sys.argv[1])
PACKS = ["en-dclm", "en-fineweb-edu", "en-nemotroncc", "en-nemotroncc-synth"]
rules = []
for b in re.findall(r"^```python\n(.*?)^```[ \t]*$", SHEET.read_text(encoding="utf-8"), re.S | re.M):
    ns = {"__name__": "rules"}
    exec(textwrap.dedent(b), ns)  # each block in its own namespace, as harm_test.py runs it
    rules.append((ns["RULE_ID"], ns["STAGE"], ns["medicine"]))


def run(doc, order, acts=None):
    d = dict(doc)
    for rid, _, m in order:
        a, t = m(d)
        if acts is not None and (a == "drop" or (a == "fix" and t != d["text"])):
            acts[rid] += 1
        if a == "drop":
            return ("drop", doc["text"])
        d["text"] = t
    return ("fix" if d["text"] != doc["text"] else "keep", d["text"])


def moved(before_ids, ids):
    """The sheet with the rules in ids moved to just before the first rule of before_ids."""
    rest = [r for r in rules if r[0] not in ids]
    i = next(k for k, r in enumerate(rest) if r[0] in before_ids)
    return rest[:i] + [r for r in rules if r[0] in ids] + rest[i:]


drops = [r for r, s, _ in rules if s == "30"]
strips = [r for r, s, _ in rules if s == "35"]
VARIANTS = {
    "strips (35) before drops (30)": moved(drops, strips),
    "A3 before A5 (the order before 31 Oct)": moved(["DA-A5-001"], ["DA-A3-002"]),
    "B2 before B1": moved(["DA-B1-002"], ["DA-B2-002"]),
    "F1 before B4": moved(["DA-B4-007"], ["DA-F1-005"]),
    "C3-002 before C3-001": moved(["DA-C3-001"], ["DA-C3-002"]),
    "C5-005 before C5-002 (strip before drop)": moved(["DA-C5-002"], ["DA-C5-005"]),
    "D3 before C1": moved(["DA-C1-006"], ["DA-D3-003"]),
}


def main():
    out = {}
    for p in PACKS:
        rows = pq.read_table(PACKS_DIR / f"{p}.parquet", columns=["doc_id", "text", "url", "lang_label"]).to_pylist()
        acts = Counter()
        base = {r["doc_id"]: run(r, rules, acts) for r in rows}
        res = {"acts_in_sheet": {rid: acts[rid] for rid, _, _ in rules}}
        for name, order in VARIANTS.items():
            got = {r["doc_id"]: run(r, order) for r in rows}
            diff = [i for i in got if got[i] != base[i]]
            drop_diff = [i for i in got if (got[i][0] == "drop") != (base[i][0] == "drop")]
            res[name] = dict(differ=len(diff), drop_decisions_differ=len(drop_diff), ids=diff[:4])
        out[p] = res
        print(p, "acts in the sheet run:", {k[3:]: v for k, v in acts.items() if v})
        for name in VARIANTS:
            print(f"   {name:42} differ {res[name]['differ']:3} (drop decisions {res[name]['drop_decisions_differ']}) {res[name]['ids']}")
    dest = HERE.parent / "results" / "cleaner" / "order_checks_english.json"
    dest.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote", dest.name)


if __name__ == "__main__":
    main()
