"""Run each function of ../clean.py, and each English medicine, on each English gold set with the team's harm_test.py,
and write ../results/cleaner/harm_tests_english.md: the English packs in more detail than make_harm_tests.py,
which writes ../results/cleaner/harm_tests.md for every pack.

  python -I make_harm_tests_english.py <g1-harm-test checkout> <packs dir> <gold dir with the disputed docs left in>

harm_test.py is run as it is, never changed. Four runs per pack, reports in ../results/ (IDs and digests only):
  cleaner/clean_<pack>_harm.json         ../clean.py --rule all, official gold: each function, then ALL IN ORDER in RULES order
  cleaner/clean_stress_<pack>_harm.json  the same, with the disputed docs left in
  sheets/<pack>_harm.json                ../sheets/medicine_english.md --rule all, official gold: each medicine, then the sheet
  sheets/stress_<pack>_harm.json         the same, with the disputed docs left in
The packs carry pack_id, which clean.py needs to pick the English rules. Section 4 of harm_tests_english.md comes from
../results/cleaner/verify_clean_english.json and section 5 from ../results/cleaner/f1_eval_english.json: run those two scripts first.
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent
CHECKOUT, PACKS_DIR, STRESS = (Path(a).resolve() for a in sys.argv[1:4])
TEAM = CHECKOUT / "teams" / "01-data-a"
HARM = TEAM / "tools" / "harm_test.py"
CLEAN, SHEET = SPEC / "clean.py", SPEC / "sheets" / "medicine_english.md"
CLEANER, SHEETS = SPEC / "results" / "cleaner", SPEC / "results" / "sheets"  # clean.py's reports; the sheet's reports
PACKS = ["en-dclm", "en-fineweb-edu", "en-nemotroncc", "en-nemotroncc-synth"]
SHORT = {"en-dclm": "dclm", "en-fineweb-edu": "fineweb-edu", "en-nemotroncc": "nemotroncc", "en-nemotroncc-synth": "synth"}
IN_REPO = {CLEAN: "teams/01-data-a/spec_v1/clean.py", SHEET: "teams/01-data-a/spec_v1/sheets/medicine_english.md"}
sys.path.insert(0, str(SPEC))
import clean as c


def gold_rows(path):
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def harm(pack, rules, gold, report):
    if not gold_rows(gold):
        return None  # harm_test.py says NOT TESTABLE (exit code 2) and writes no report
    report.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, "-I", str(HARM), "--pack", str(PACKS_DIR / f"{pack}.parquet"), "--gold", str(gold),
                        "--rules", str(rules), "--rule", "all", "--report", str(report)], capture_output=True, text=True)
    if not report.exists():
        sys.exit(f"harm_test.py could not run {rules.name} on {pack}: {(r.stderr or r.stdout).strip()}")
    d = json.loads(report.read_text(encoding="utf-8"))
    d["rules"] = IN_REPO[rules]  # the path it has in the repo, not this machine's
    report.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")
    return d


def res(rep, name):
    return next(x for x in rep["results"] if x["rule"] == name)


def cell(rep, name):
    """As ../harm_tests.md: changed + dropped, and the result only when it is not a PASS."""
    if rep is None:
        return "NOT TESTABLE"
    r = res(rep, name)
    return f"{r['changed'] + r['dropped']}" + ("" if r["result"] == "PASS" else f" **{r['result']}**")


def ids(rep, name):
    return [i for i in res(rep, name)["affected_ids"]]


def renamed():
    """English IDs that specv1.md (and so clean.py) renamed: {medicine_english.md ID: clean.py ID}."""
    rows = re.findall(r"^\| \d+ \| english \| \w+ \| `(DA-[^`]+)` \| `(DA-[^`]+)` \|$", (SPEC / "sheets" / "specv1.md").read_text(encoding="utf-8"), re.M)
    return {a: b for a, b in rows if a != b}


def main():
    for p in PACKS:  # clean.py picks the English rules by pack_id, and harm_test.py passes the pack's column on
        assert "pack_id" in pq.read_schema(PACKS_DIR / f"{p}.parquet").names, f"{p}: no pack_id column, so clean.py would keep every document"
    ver = json.loads((CLEANER / "verify_clean_english.json").read_text(encoding="utf-8"))
    fn, fn_s, sh, sh_s = {}, {}, {}, {}
    for p in PACKS:
        gold, stress = TEAM / "gold" / f"{p}_gold.csv", STRESS / f"{p}_gold.csv"
        fn[p] = harm(p, CLEAN, gold, CLEANER / f"clean_{p}_harm.json")
        fn_s[p] = harm(p, CLEAN, stress, CLEANER / f"clean_stress_{p}_harm.json")
        sh[p] = harm(p, SHEET, gold, SHEETS / f"{p}_harm.json")
        sh_s[p] = harm(p, SHEET, stress, SHEETS / f"stress_{p}_harm.json")
        print(p, " ".join(f"{k} {v['status']}" for k, v in (("spec_v1/clean.py", fn[p]), ("stress", fn_s[p]), ("sheet", sh[p]), ("sheet-stress", sh_s[p]))))
    english_codes = list(dict.fromkeys(c._ID[f].split("-")[1] for f in c._PIPELINES["english"]))
    rule_ids = [r["rule"] for r in sh[PACKS[0]]["results"] if r["rule"] != "ALL IN ORDER"]
    new_id = renamed()
    head = "| {} | " + " | ".join(SHORT[p] for p in PACKS) + " |"
    rule = "|---|" + "---:|" * len(PACKS)
    goldrow = lambda runs: "| gold docs (limit) | " + " | ".join("0: NOT TESTABLE" if runs[p] is None else
                                                                f"{runs[p]['gold_count']} ({runs[p]['limit_documents']})" for p in PACKS) + " |"
    funcs = [x for x in (r["rule"] for r in fn[PACKS[0]]["results"]) if x in english_codes or x == "ALL IN ORDER"]
    o = ["# Spec v1 harm tests: English", "",
         "DRAFT. Each cell: gold docs changed + dropped, for that function or medicine on that pack's gold set. Limit: "
         "`max(1, floor(1% of gold))`, that is `max(1 document, 1%)` (TSAI decision); each pack on its own gold set, never pooled; "
         "an empty gold set is NOT TESTABLE (exit code 2), never a PASS. A result other than PASS is shown after the count. "
         f"Made by `spec_v1/tools/make_harm_tests_english.py` on {date.today():%d %b %Y} with the team's `harm_test.py`, run as it is "
         f"(sha256 `{hashlib.sha256(HARM.read_bytes()).hexdigest()[:12]}`). "
         "Every pack, each rule on the gold sets of its own packs, is in `harm_tests.md`.", "",
         "## 1. Each function of clean.py on the English packs", "",
         "`clean.py`: the one cleaner, built by `spec_v1/tools/build_clean.py` from `specv1.md`. A rule runs only on the packs of its `SCOPE` entry, "
         f"so on these packs only the English rules act. The {len(english_codes)} functions with English rules; the other functions have "
         "no English rule and keep every English document (section 4).", "",
         head.format("function"), rule, goldrow(fn)]
    o += [f"| {x} | " + " | ".join(cell(fn[p], x) for p in PACKS) + " |" for x in funcs]
    o += ["", "`ALL IN ORDER` is `harm_test.py` running every function of `clean.py` one after another, in `RULES` order. "
          "Section 4 shows whether that gives the same as `clean()`, which runs the English rules in the sheet's order, F1 last.", "",
          "## 2. The same, with the disputed docs left in the gold sets", "", head.format("function"), rule, goldrow(fn_s)]
    o += [f"| {x} | " + " | ".join(cell(fn_s[p], x) for p in PACKS) + " |" for x in funcs]
    o += ["", "## 3. Each medicine on its own, on the English packs", "",
          f"`medicine_english.md --rule all`: each of the {len(rule_ids)} medicines alone, then the whole sheet in its order. "
          "`specv1.md`, and so `clean.py`, gives " + (", ".join(f"`{a}` the ID `{b}`" for a, b in new_id.items()) or "every medicine the same ID") + ".", "",
          "| medicine | function | " + " | ".join(SHORT[p] for p in PACKS) + " | with the disputed docs left in |",
          "|---|---|" + "---:|" * len(PACKS) + "---|",
          "| gold docs (limit) | | " + " | ".join(f"{sh[p]['gold_count']} ({sh[p]['limit_documents']})" for p in PACKS) + " | "
          + ", ".join(f"{SHORT[p]} {sh_s[p]['gold_count']} ({sh_s[p]['limit_documents']})" for p in PACKS) + " |"]
    for rid in rule_ids + ["ALL IN ORDER"]:
        name = "ALL IN ORDER" if rid == "ALL IN ORDER" else f"`{rid}`" + (f" (`{new_id[rid]}` in clean.py)" if rid in new_id else "")
        o.append(f"| {name} | {rid.split('-')[1] if rid != 'ALL IN ORDER' else 'the sheet'} | "
                 + " | ".join(cell(sh[p], rid) for p in PACKS) + " | " + ", ".join(cell(sh_s[p], rid) for p in PACKS) + " |")
    pk = ver["packs"]
    vcell = lambda v: "0" if not v else f"**{len(v)}** ({', '.join(f'`{i}`' for i in v[:3])})"
    o += ["", "## 4. Checks on every document of the English packs", "",
          "From `spec_v1/tools/verify_clean_english.py` (`results/cleaner/verify_clean_english.json`), which checks `clean.py` against the English rules of "
          "`specv1.md`. Each cell: documents where the check fails.", "",
          head.format("check"), rule,
          "| documents | " + " | ".join(str(pk[p]["docs"]) for p in PACKS) + " |",
          "| a `clean.py` function differs from its English rules run in order (a function with no English rule must keep) | "
          + " | ".join(vcell([i for v in pk[p]["function_vs_sheet_blocks"].values() for i in v]) for p in PACKS) + " |",
          "| `clean()` differs from the English rules run in sheet order | " + " | ".join(vcell(pk[p]["clean_vs_sheet"]) for p in PACKS) + " |",
          "| `ALL IN ORDER` of `clean.py` (RULES order) differs from `clean()` | " + " | ".join(vcell(pk[p]["all_in_order_vs_clean"]) for p in PACKS) + " |",
          "| a second `clean()` changes the text again | " + " | ".join(vcell(pk[p]["second_run_changes"]) for p in PACKS) + " |",
          "| documents with a ZWJ or ZWNJ | " + " | ".join(str(pk[p]["docs_with_joiners"]) for p in PACKS) + " |",
          "| a ZWJ or ZWNJ deleted on its own | " + " | ".join(vcell(pk[p]["joiners_lost_in_kept_lines"]) for p in PACKS) + " |"]
    f1_path = CLEANER / "f1_eval_english.json"
    if f1_path.exists():  # made by f1_eval_english.py, the English counterpart of spec_v1/tools/f1_eval.py
        f1 = json.loads(f1_path.read_text(encoding="utf-8"))
        o += ["", "## 5. F1 on the English packs", "",
              "From `spec_v1/tools/f1_eval_english.py` (`results/cleaner/f1_eval_english.json`). `DA-F1-005` is the F1 that `clean.py` runs on the English packs; the "
              "shared `spec_v1/tools/f1_rule.py` is switched on for `en` and `eng` in memory only, to show what that would do. Each cell: docs F1 "
              "changes or drops after the other English rules, then the gold docs among them.", "",
              head.format("F1 rule"), rule]
        for name in ("DA-F1-005", "shared F1 (in memory)"):
            o.append(f"| {name} | " + " | ".join(
                f"{f1['real'][p][name]['fixed'] + f1['real'][p][name]['dropped']}, gold {len(f1['real'][p][name]['gold_touched'])}"
                + ("" if len(f1['real'][p][name]['gold_touched']) <= f1['real'][p][name]['limit'] else " **over**") for p in PACKS) + " |")
        o += ["", "A second `clean()` leaves every F1 tag as it is: " + ", ".join(
            f"{SHORT[p]} {len(f1['second_run'][p]['changed_again'])} of {f1['second_run'][p]['docs_with_new_tags']}" for p in PACKS)
            + " docs change again. Planted made-up values: `decisions_english.md`, F1."]
    touched = {(p, k): ids(r[p], "ALL IN ORDER") for k, r in (("official", fn), ("stress", fn_s)) for p in PACKS}
    o += ["", "## Gold docs touched", "",
          "| pack | official gold | with the disputed docs left in |", "|---|---|---|"]
    o += [f"| {SHORT[p]} | {', '.join(f'`{i}`' for i in touched[(p, 'official')]) or '-'} | "
          f"{', '.join(f'`{i}`' for i in touched[(p, 'stress')]) or '-'} |" for p in PACKS]
    o += ["", "Affected gold IDs are in `results/cleaner/clean_<pack>_harm.json`, `results/cleaner/clean_stress_<pack>_harm.json` and "
          "`results/sheets/<pack>_harm.json`. No document text is kept.", "",
          "## Not run", "", "| family | pack | gold docs | why |", "|---|---|---:|---|"]
    not_run = [p for p in PACKS if fn[p] is None]
    o += [f"| English | {p} | 0 | gold set is empty: NOT TESTABLE |" for p in not_run] or ["| - | - | - | every English pack ran |"]
    runs = [r for d in (fn, fn_s, sh, sh_s) for r in d.values() if r]
    passed = sum(r["status"] == "PASS" for r in runs)
    o += ["", f"Overall: {passed} of {len(runs)} runs PASS" + ("." if passed == len(runs) else f", {len(runs) - passed} not.")]
    (CLEANER / "harm_tests_english.md").write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
    print("wrote harm_tests_english.md |", f"{passed}/{len(runs)} PASS")


if __name__ == "__main__":
    main()
