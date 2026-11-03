#!/usr/bin/env python3
"""harm_test_indic.py - the harm test for Data B (Indic) medicines.

Runs each rule of one medicine.md on the gold documents and reports how many of them the rule changes and drops.
A rule passes when it changes or drops at most 1% of the gold set (DISEASES.md section 4) or at most 1 document,
whichever is more: the TSAI rule for small gold sets (CAP, 30 Oct). The medicine.md format and the rule results are the
same as in Data A's harm_test.py (a rule returns the new text, or True to drop the document), so one file works
with both tools. What this tool adds, because Indic text needs it:

  - ZWJ (U+200D) and ZWNJ (U+200C): their counts in a changed document must stay the same.
  - Normal form: a document that is NFC must still be NFC, and a rule must not replace compatibility characters
    (half-width letters, fractions: what NFKC does). This also flags a lost no-break space (U+00A0) or ellipsis
    (U+2026), so a whitespace fix can fail this audit even when it is a good fix.
  - Several packs in one run: each pack is judged on its own gold set (TSAI, CAP 31 Oct: per pack, never pooled).
    A pack whose gold file is missing or empty is reported as "gold set empty, not testable" and the others still run.

Usage
  python3 harm_test_indic.py --medicine medicine.md --pack P1.parquet [P2.parquet ...] --gold-dir GOLD_DIR
                             [--rule all|A6] [--limit 1] [--show N] [--timeout 5] [--md-out FILE]
  GOLD_DIR/<pack file name without .parquet>_gold.csv is the gold set of each pack (columns doc_id,reader_1,reader_2).
  A pack may also be a .jsonl file with doc_id and text.
Exit codes: 0 pass, 1 fail, 2 could not run.

The code in medicine.md is run as code: read it first. Document text is never printed, only doc_ids.
"""
import argparse
import csv
import hashlib
import inspect
import json
import re
import signal
import sys
import textwrap
import unicodedata
from fractions import Fraction
from pathlib import Path

MIN_DOCS = 1  # TSAI rule for small gold sets: a rule may always change this many documents
ZWJ, ZWNJ = chr(0x200D), chr(0x200C)  # written as numbers: a raw joiner in code is invisible
SECTION = re.compile(r"\*\*Disease:?\*\*:?[ \t]*`?([A-H][1-9])\b")
FENCE = re.compile(r"^([ \t]*)```(?:python|py)[ \t]*\n(.*?)^\1```[ \t]*$", re.S | re.M)
HAS_ALARM = hasattr(signal, "setitimer")  # no per-document time limit on Windows


class Fatal(Exception):
    """The test could not run (exit code 2)."""


class Timeout(Exception):
    pass


# ---------------------------------------------------------------- reading medicine.md
def load_rules(path):
    """([(code, function or None)] in file order, {code: function name} of the rules that take 'doc').
    There is one entry for each '**Disease:**' section."""
    src = Path(path).read_text(encoding="utf-8")
    marks = list(SECTION.finditer(src))
    if not marks:
        raise Fatal(f"{path}: no '**Disease:** <code>' line found")
    rules, uses_doc, seen = [], {}, set()
    for i, m in enumerate(marks):
        code = m.group(1)
        if code in seen:
            raise Fatal(f"two sections for {code}: keep one section for each code")
        seen.add(code)
        end = marks[i + 1].start() if i + 1 < len(marks) else len(src)
        ns = {"re": re, "__name__": "medicine"}  # re is ready to use, as in Data A's tool
        for k, fm in enumerate(FENCE.finditer(src, m.start(), end), 1):
            try:
                exec(compile(textwrap.dedent(fm.group(2)), f"{code} block {k}", "exec"), ns)
            except SyntaxError as e:
                raise Fatal(f"{code} block {k} has a syntax error (line {e.lineno}): complete it or remove it")
            except Exception as e:  # a block must run on its own
                raise Fatal(f"{code} block {k} does not run on its own: {type(e).__name__}: {e}")
        fn = ns.get("medicine_" + code.lower()) or ns.get("cure_" + code.lower())
        if fn is None:
            public = [v for k, v in ns.items() if callable(v) and not k.startswith("_") and getattr(v, "__module__", "") == "medicine"]
            if len(public) > 1:
                raise Fatal(f"{code}: several public functions; name the main one medicine_{code.lower()} or start the helper names with _")
            fn = public[0] if public else None
        if fn is not None and next(iter(inspect.signature(fn).parameters), "") == "doc":
            uses_doc[code] = fn.__name__  # reported by main() when this rule is asked for
            fn = None
        rules.append((code, fn))
    return rules, uses_doc


# ---------------------------------------------------------------- one rule on one document
def classify(text, out):
    """('keep'|'fix'|'drop', new text). A rule returns the new text, True (drop) or False (keep)."""
    if isinstance(out, bool):  # bool before str: True is a drop, not a text
        return ("drop", text) if out else ("keep", text)
    if isinstance(out, str):
        return ("fix", out) if out != text else ("keep", text)
    if isinstance(out, tuple) and len(out) == 2 and out[0] in ("keep", "fix", "drop"):
        if out[0] == "drop":
            return "drop", text
        if not isinstance(out[1], str):
            raise TypeError("the new text is not a str")
        return ("fix", out[1]) if out[1] != text else ("keep", text)
    raise TypeError("a rule must return a str, True or False")


def _on_alarm(signum, frame):
    raise Timeout()


def call(fn, text, timeout):
    if HAS_ALARM:
        signal.signal(signal.SIGALRM, _on_alarm)
        signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return classify(text, fn(text))
    finally:
        if HAS_ALARM:
            signal.setitimer(signal.ITIMER_REAL, 0)


def compat_chars(text):
    """The compatibility characters in text (half-width letters, fractions, ligatures ...): the ones NFKC rewrites."""
    return {c for c in set(text) if unicodedata.decomposition(c).startswith("<")}


def audit(before, after):
    """Damage that the 1% count does not show. [] when the changed document is fine."""
    bad = []
    if before.count(ZWJ) != after.count(ZWJ) or before.count(ZWNJ) != after.count(ZWNJ):
        bad.append("joiners")
    if unicodedata.is_normalized("NFC", before) and not unicodedata.is_normalized("NFC", after):
        bad.append("not NFC")
    # NFKC replaces compatibility characters. A rule that removes or replaces one does what NFKC does (G4 damage).
    # This is checked on the characters, so no NFKC call is needed (the kit's Indic guard refuses that call).
    if any(after.count(c) < before.count(c) for c in compat_chars(before)):
        bad.append("compatibility characters")
    return bad


def run_rule(name, steps, docs, timeout):
    """steps: [function] run in order (one rule, or all rules for 'ALL IN ORDER'). docs: [(pack, doc_id, text)]."""
    res = {"changed": [], "dropped": [], "errors": [], "joiners": [], "form": []}
    for pack, doc_id, text in docs:
        cur, verdict = text, "keep"
        try:
            for fn in steps:
                v, cur2 = call(fn, cur, timeout)
                if v == "drop":
                    verdict = "drop"
                    break
                if v == "fix":
                    cur, verdict = cur2, "fix"
        except Timeout:
            res["errors"].append((pack, doc_id, f"took more than {timeout} s"))
            continue
        except Exception as e:  # a crash is a failure, never a pass
            res["errors"].append((pack, doc_id, f"{type(e).__name__}: {str(e)[:80]}"))
            continue
        if verdict == "fix" and cur == text:  # a later rule put the original text back: not a change
            verdict = "keep"
        if verdict == "drop":
            res["dropped"].append((pack, doc_id))
        elif verdict == "fix":
            res["changed"].append((pack, doc_id))
            bad = audit(text, cur)
            if "joiners" in bad:
                res["joiners"].append((pack, doc_id))
            if "not NFC" in bad or "compatibility characters" in bad:
                res["form"].append((pack, doc_id))
    return res


def allowed_docs(n, limit):
    """How many gold documents a rule may change or drop: limit percent of n, but never fewer than MIN_DOCS."""
    return max(Fraction(MIN_DOCS), Fraction(n) * limit / 100)


def verdict_of(res, n, limit):
    ok = (not res["errors"] and not res["joiners"] and not res["form"]
          and len(res["changed"]) + len(res["dropped"]) <= allowed_docs(n, limit))
    return "PASS" if ok else "FAIL"


# ---------------------------------------------------------------- reading gold and packs
def read_gold(path):
    ids = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "doc_id" not in (reader.fieldnames or []):
            raise Fatal(f"{path}: no doc_id column")
        ids = [r["doc_id"].strip() for r in reader if (r["doc_id"] or "").strip()]
    if len(ids) != len(set(ids)):
        raise Fatal(f"{path}: the same doc_id twice")
    return ids


def read_docs(pack_path, ids):
    p = Path(pack_path)
    want = set(ids)
    if p.suffix == ".jsonl":
        rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        for k, r in enumerate(rows, 1):
            if not isinstance(r, dict) or "doc_id" not in r or "text" not in r:
                raise Fatal(f"{p.name}: row {k} has no doc_id or no text (each row needs both)")
    else:
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise Fatal("pyarrow is needed to read a Parquet pack: pip install pyarrow")
        rows = pq.read_table(p, columns=["doc_id", "text"]).to_pylist()
    got = {r["doc_id"]: r["text"] for r in rows if r["doc_id"] in want}
    missing = sorted(want - set(got))
    if missing:
        raise Fatal(f"{p.name}: {len(missing)} gold documents are not in the pack (first: {', '.join(missing[:3])})")
    if not all(isinstance(t, str) for t in got.values()):
        raise Fatal(f"{p.name}: a gold document has no text")
    return [(p.stem, i, got[i]) for i in ids]


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="Harm test for Data B (Indic) medicines.")
    ap.add_argument("--medicine", required=True, type=Path)
    ap.add_argument("--pack", required=True, nargs="+", type=Path)
    ap.add_argument("--gold-dir", required=True, type=Path)
    ap.add_argument("--rule", default="all", help="a disease code such as A6, or all (default)")
    ap.add_argument("--limit", default="1", help="failing limit in percent of the gold set (default 1)")
    ap.add_argument("--show", type=int, default=0, metavar="N", help="list the first N affected doc_ids of each rule")
    ap.add_argument("--timeout", type=float, default=5.0, help="seconds for one rule on one document (default 5)")
    ap.add_argument("--md-out", type=Path, help="write the part-4 text for each rule of medicine.md")
    a = ap.parse_args(argv)
    try:
        limit = Fraction(a.limit)
        rules, uses_doc = load_rules(a.medicine)
        sets, untested = [], []  # (pack, gold documents) for each pack that has a gold set; packs without one
        for pack in a.pack:
            gold = a.gold_dir / f"{pack.stem}_gold.csv"
            ids = read_gold(gold) if gold.exists() else []
            if ids:
                sets.append((pack.stem, read_docs(pack, ids)))
            else:
                untested.append(pack.stem)
        if not sets:
            raise Fatal(f"{', '.join(untested)}: gold set empty, not testable (an empty set does not pass)")
        if a.rule.lower() != "all" and a.rule.upper() not in {c for c, _ in rules}:
            raise Fatal(f"no section for {a.rule} in {a.medicine.name}")
        wanted = [c for c in uses_doc if a.rule.lower() in ("all", c.lower())]
        if wanted:  # name the rule, and say how to test the others
            raise Fatal(f"{wanted[0]}: the function {uses_doc[wanted[0]]}() takes 'doc' (document metadata). Test it with "
                        f"Data A's harm_test.py; to test the other rules here use --rule CODE")
    except (Fatal, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    sha = hashlib.sha256(a.medicine.read_bytes()).hexdigest()[:12]
    if not HAS_ALARM:
        print("warning: no per-document time limit on this system", file=sys.stderr)
    todo = [(c, [f], f) for c, f in rules if f is not None and a.rule.lower() in ("all", c.lower())]
    for c, f in rules:
        if f is None:
            print(f"note: {c} has no rule in code, so nothing to test")
    if a.rule.lower() == "all":
        todo.append(("ALL IN ORDER", [f for _, f in rules if f is not None], None))
    if not todo:
        print("error: no rule to test", file=sys.stderr)
        return 2
    for stem in untested:
        print(f"{stem}: gold set empty, not testable")
    worst, blocks = "PASS", []
    for stem, docs in sets:  # each pack against its own gold set and its own limit
        n = len(docs)
        print(f"gold set: {n} documents in 1 pack(s) ({stem} {n})   medicine: {a.medicine.name} sha256 {sha}")
        print(f"a rule may change or drop at most {float(allowed_docs(n, limit)):g} of {n} documents ({a.limit}% or {MIN_DOCS}, whichever is more)")
        print(f"{'rule':<14}{'changed':>8}{'dropped':>8}{'percent':>9}  joiners  form   result")
        for name, steps, _ in todo:
            res = run_rule(name, steps, docs, a.timeout)
            v = verdict_of(res, n, limit)
            worst = "FAIL" if v == "FAIL" else worst
            pct = 100 * (len(res["changed"]) + len(res["dropped"])) / n
            print(f"{name:<14}{len(res['changed']):>8}{len(res['dropped']):>8}{pct:>8.2f}%  "
                  f"{'FAIL' if res['joiners'] else 'ok':<8}{'FAIL' if res['form'] else 'ok':<7}{v}")
            if v == "FAIL" or a.show:
                for label, key in (("changed", "changed"), ("dropped", "dropped"), ("joiner count changed", "joiners"),
                                   ("normal form broken", "form")):
                    if res[key] and (a.show or key in ("joiners", "form")):
                        print(f"    {label}: " + ", ".join(f"{p}:{i}" for p, i in res[key][:a.show or 5]))
                for p, i, why in res["errors"][:a.show or 5]:
                    print(f"    error: {p}:{i} {why}")
            blocks.append((stem, n, name, res, v))
    print(f"result: {worst}")
    if a.md_out:
        lines = []
        for stem in untested:
            lines += [f"## {stem}", "4. **Harm test:** gold set empty, not testable.", ""]
        for stem, n, name, res, v in blocks:
            ch, dr = len(res["changed"]), len(res["dropped"])
            head = f"## {name}" if len(sets) == 1 else f"## {name} ({stem})"
            lines += [head, f"4. **Harm test:** gold set of {n} documents ({stem} {n}), medicine.md sha256 {sha}; rule: changed or dropped at most {a.limit}% or {MIN_DOCS} document, whichever is more.",
                      f"   - Changed {ch} of {n} ({100 * ch / n:.2f}%). Dropped {dr} of {n} ({100 * dr / n:.2f}%). **{v}**",
                      f"   - ZWJ/ZWNJ audit: {len(res['joiners'])} changed documents with a different count. **{'FAIL' if res['joiners'] else 'PASS'}**",
                      f"   - Normal-form audit: {len(res['form'])} changed documents left NFC or lost a compatibility character. **{'FAIL' if res['form'] else 'PASS'}**", ""]
        a.md_out.write_text("\n".join(lines), encoding="utf-8")
    return 0 if worst == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
