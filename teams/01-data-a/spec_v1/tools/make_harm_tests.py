"""Task 4: test spec_v1/clean.py with the team's harm_test.py, and write spec_v1/results/cleaner/harm_tests.md.

  python -I make_harm_tests.py <checkout> <packs dir> [<packs dir> ...] [--out <harm_tests.md>] [--results <dir>]

<checkout> holds teams/01-data-a/tools/harm_test.py and teams/01-data-a/gold/. harm_test.py is imported as it is, never
changed, and its own functions read the gold, read the pack and count the harm, as tools/validate_specv1.py does.

Each rule is tested alone, only on the gold sets of the packs SCOPE (the table at the top of clean.py) gives it. Then each
disease-code function on every pack where one of its rules applies, and clean() on every pack. Every rule that does not
apply to a pack is also run on that whole pack, and must change nothing: that checks the scope table holds.

A pack's documents get pack_id from the pack; a pack without the column gets its file name, and a pack whose pack_id is
not its file name stops the run. A pack with no file in any <packs dir>, or no gold file, is listed as not run.
Reports are IDs and digests only, never text.
"""
import argparse, hashlib, json, sys
from datetime import date
from fractions import Fraction
from pathlib import Path
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("checkout", type=Path)
ap.add_argument("packs", type=Path, nargs="+")
ap.add_argument("--out", type=Path, default=HERE / "results" / "cleaner" / "harm_tests.md")
ap.add_argument("--results", type=Path, default=HERE / "results" / "cleaner")
args = ap.parse_args()
TEAM = args.checkout / "teams" / "01-data-a"
sys.path.insert(0, str(TEAM / "tools")); import harm_test as ht
sys.path.insert(0, str(HERE)); import clean as c
LIMIT, TIMEOUT = Fraction(1), 5
args.results.mkdir(parents=True, exist_ok=True)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def short(pack): return pack.split("-", 1)[1]
def code_of(rid): return "F1" if rid == "f1_rule.py" else rid.split("-")[1]


def alone(rid):
    def rule(doc):  # named doc: harm_test.py passes the document dict
        return c._run(doc, c._RULE[rid])
    return rule


def with_pack(docs, pack):
    for d in docs.values():
        if d.setdefault("pack_id", pack) != pack:
            sys.exit(f"{pack}: doc_id {d['doc_id']} has pack_id {d['pack_id']!r}")
    return docs


def cell(r):
    return "·" if r is None else f"{r['changed'] + r['dropped']}" + ("" if r["result"] == "PASS" else f" **{r['result']}**")


families = {fam: sorted(p for p, f in c._FAMILY.items() if f == fam) for fam in c._PIPELINES}  # sorted: the same table on every run
validation = HERE / "results" / "cleaner" / "specv1_validation.json"
validation = json.loads(validation.read_text(encoding="utf-8"))["packs"] if validation.exists() else {}
ran, missing, failed = {}, [], False
for fam, packs in families.items():
    for pack in packs:
        gold = TEAM / "gold" / f"{pack}_gold.csv"
        parquet = next((d / f"{pack}.parquet" for d in args.packs if (d / f"{pack}.parquet").exists()), None)
        if parquet is None or not gold.exists():
            missing.append((fam, pack, "pack not on this machine" if parquet is None else "no gold file")); continue
        try:
            ids = ht.read_gold(gold)
        except ht.NotTestable:
            missing.append((fam, pack, "gold set is empty: NOT TESTABLE")); failed = True; continue
        n = len(ids)
        gold_docs = with_pack(ht.read_pack_docs(parquet, ids), pack)
        all_docs = with_pack({r["doc_id"]: r for r in pq.read_table(parquet).to_pylist()}, pack)
        in_scope = [rid for rid in c._RULE if pack in c.SCOPE[rid]]
        rules = {rid: ht._result(rid, ht.run_rule(alone(rid), gold_docs, TIMEOUT), n, LIMIT) for rid in in_scope}
        codes = {code_of(rid) for rid in in_scope}
        functions = {code: ht._result(code, ht.run_rule(fn, gold_docs, TIMEOUT), n, LIMIT) for code, fn in c.RULES.items() if code in codes}
        pipeline = ht._result("clean()", ht.run_rule(c.clean, gold_docs, TIMEOUT), n, LIMIT)
        changed, dropped, errors = ht.run_rule(c.clean, all_docs, TIMEOUT)
        whole = {"docs": len(all_docs), "fixed": len(changed), "dropped": len(dropped), "errors": len(errors)}
        outside = {}
        for rid in c._RULE:
            if rid not in in_scope:
                hit = ht.run_rule(c._RULE[rid](), all_docs, TIMEOUT)  # the rule's own code, past _run: its guard must hold too
                if any(hit):
                    outside[rid] = {"changed": hit[0], "dropped": hit[1], "errors": [e for _, e in hit[2]]}
        v = validation.get(pack, {})
        if v.get("gold_sha256") != sha(gold) or v.get("pack_sha256") != sha(parquet):
            same = "other snapshot"
        else:
            old = v["combined_gold"]
            same = "yes" if (sorted(old["changed"]), sorted(old["dropped"])) == (sorted(pipeline["changed_ids"]), sorted(pipeline["dropped_ids"])) else "**no**"
        report = {"pack": parquet.name, "pack_sha256": sha(parquet), "gold": gold.name, "gold_sha256": sha(gold), "gold_count": n,
                  "limit_percent": str(LIMIT), "limit_documents": ht.allowed_documents(n, LIMIT), "rules": "teams/01-data-a/spec_v1/clean.py",
                  "rules_file_sha256": sha(HERE / "clean.py"), "harm_test_sha256": sha(Path(ht.__file__)), "family": fam,
                  "rules_alone": list(rules.values()), "functions": list(functions.values()), "clean": pipeline, "whole_pack": whole,
                  "out_of_scope_rules_acting": outside, "same_as_specv1_validation": same}
        (args.results / f"specv1_{pack}_harm.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        ran[pack] = report
        failed |= any(r["result"] != "PASS" for r in [*rules.values(), *functions.values(), pipeline]) or bool(outside)
        print(pack, pipeline["result"], "gold", pipeline["changed"], pipeline["dropped"], "| not passing:",
              [(r["rule"], r["result"]) for r in [*rules.values(), *functions.values()] if r["result"] != "PASS"], "| out of scope acting:", sorted(outside), flush=True)

lines = ["# Spec v1 harm tests", "",
         f"DRAFT. Made by `spec_v1/tools/make_harm_tests.py` on {date.today():%d %b %Y} from `clean.py` (built by `spec_v1/tools/build_clean.py` from `specv1.md`) "
         "with the team's `harm_test.py`, run as it is. Each cell: gold docs changed + dropped. Limit: `max(1, floor(1% of gold))`, that is "
         "`max(1 document, 1%)` (TSAI decision), each pack on its own gold set, never pooled. An empty gold set is NOT TESTABLE and an error is "
         "never a PASS; a result other than PASS is shown after the count.", "",
         "A rule is tested only on the gold sets of the packs it applies to: its entry in `SCOPE`, the table at the top of `clean.py`. "
         "`·` means the rule does not apply to that pack, so it was not run there.", "",
         "## 1. clean(), the whole cleaner, on each pack", "",
         "| pack | family | gold docs (limit) | gold changed + dropped | result | whole pack fixed / dropped | rules that do not apply, acting on the whole pack | gold result as `results/cleaner/specv1_validation.json` |",
         "|---|---|---:|---:|---|---:|---|---|"]
for pack, d in ran.items():
    lines.append(f"| {pack} | {d['family']} | {d['gold_count']} ({d['limit_documents']}) | {cell(d['clean'])} | {d['clean']['result']} | "
                 f"{d['whole_pack']['fixed']} / {d['whole_pack']['dropped']} | {', '.join(d['out_of_scope_rules_acting']) or 'none'} | {d['same_as_specv1_validation']} |")
lines += ["", "On the code, math and science packs `clean()` also runs the shared F1 (`spec_v1/tools/f1_rule.py`) last, and `DA-B4-009` leaves `<EMAIL>`: "
          "`specv1_validation.json` ran the sheet without them, so these packs may differ from it.", "",
          "## 2. Each rule alone, on the gold sets of its packs only", ""]
for fam, packs in families.items():
    tested = [p for p in packs if p in ran]
    if not tested:
        continue
    lines += [f"### {fam}", "", "| rule | " + " | ".join(short(p) for p in tested) + " | result |", "|---|" + "---:|" * len(tested) + "---|"]
    for rid in c._RULE:
        if not set(packs) & c.SCOPE[rid]:
            continue
        rs = [next((r for r in ran[p]["rules_alone"] if r["rule"] == rid), None) for p in tested]
        results = {r["result"] for r in rs if r}
        verdict = next((x for x in ("ERROR", "FAIL") if x in results), "PASS")
        if c.SCOPE[rid] - set(tested):
            verdict += f" (not run on {', '.join(sorted(c.SCOPE[rid] - set(tested)))})"
        lines.append(f"| {code_of(rid)} `{rid}` | " + " | ".join(cell(r) for r in rs) + f" | {verdict} |")
    lines.append("")
lines += ["## 3. Each disease-code function, on the packs where one of its rules applies", "",
          "| function | " + " | ".join(short(p) for p in ran) + " |", "|---|" + "---:|" * len(ran)]
for code in c.RULES:
    lines.append(f"| {code} | " + " | ".join(cell(next((r for r in ran[p]["functions"] if r["rule"] == code), None)) for p in ran) + " |")
lines += ["", "Affected gold IDs are in `results/cleaner/specv1_<pack>_harm.json`. No document text is kept.", "",
          "## Not run", "", "| family | pack | why |", "|---|---|---|"] + [f"| {f} | {p} | {w} |" for f, p, w in missing]
args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("wrote", args.out, "| not run:", [m[1] for m in missing])
sys.exit(1 if failed else 0)
