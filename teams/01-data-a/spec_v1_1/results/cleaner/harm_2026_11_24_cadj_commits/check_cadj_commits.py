"""Harm and equivalence check of the cadj-commits e-mail F1 (#88), run from the repository root.

1. cadj-commits gold (teams/02-data-b/gold/cadj-commits_gold.csv) on the week-1 pack, read with harmtest/harm_test.py's
   read_gold and read_pack_docs, against its limit max(1, floor(1% of the gold set)).
2. The week-1 cadj-commits and cadj-notebooks packs, every document: changes, drops, changes other than <EMAIL>, a second pass.
3. The documents the cadj-commits readers labelled F1 (diagnosis/submissions/cadj-commits/*/labels.csv) that it fixes.
4. Every pack of a sample folder (<pack>/<part>.parquet): the first --per-pack documents through this cleaner and through
   --compare (the previous cleaner); they must agree on every pack but cadj-commits, where only <EMAIL> may differ.
5. cadj-commits in the whole sample folder: documents and addresses masked.
Writes IDs and counts only; exits 1 if a check fails.

    python teams/01-data-a/spec_v1_1/results/cleaner/harm_2026_11_24_cadj_commits/check_cadj_commits.py \\
        --week1 <folder with cadj-commits.parquet and cadj-notebooks.parquet> --sample <sample train folder> \\
        --compare <previous clean.py> --out <summary.json>
"""
import argparse, csv, glob, hashlib, importlib.util, json, sys
from fractions import Fraction
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[6]
TEAM = REPO / "teams" / "01-data-a"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week1", type=Path, required=True)
    ap.add_argument("--sample", type=Path, required=True)
    ap.add_argument("--compare", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--per-pack", type=int, default=1000)
    args = ap.parse_args(argv)

    clean_py = TEAM / "spec_v1_1" / "clean.py"
    new, old = load(clean_py, "clean_new"), load(args.compare, "clean_previous")
    ht = load(TEAM / "harmtest" / "harm_test.py", "harm_test")
    email = new._F1_EMAIL

    def only_email(text, out):  # out is text with some addresses replaced by <EMAIL>, and nothing else
        return email.sub(lambda m: m.group() if m.group() in out else "<EMAIL>", text) == out

    rep = {"clean_sha256": sha256(clean_py), "compare_sha256": sha256(args.compare)}
    ok = True

    ids = ht.read_gold(REPO / "teams" / "02-data-b" / "gold" / "cadj-commits_gold.csv")
    docs = ht.read_pack_docs(args.week1 / "cadj-commits.parquet", ids)
    changed = dropped = 0
    for d in docs.values():
        action, text = new.clean(dict(d, pack_id="cadj-commits"))
        dropped += action == "drop"
        changed += action != "drop" and text != d["text"]
    allowed = ht.allowed_documents(len(ids), Fraction(1))
    rep["gold"] = dict(pack="cadj-commits", gold=len(ids), changed=changed, dropped=dropped, allowed=allowed,
                       result="PASS" if changed + dropped <= allowed else "FAIL")
    ok &= rep["gold"]["result"] == "PASS"

    week1 = {}
    for pack in ("cadj-commits", "cadj-notebooks"):
        rows = pq.read_table(args.week1 / f"{pack}.parquet").to_pylist()
        r = dict(docs=len(rows), changed=0, drops=0, other_changes=0, not_idempotent=0, changed_ids=[])
        for row in rows:
            row = dict(row, pack_id=pack)
            action, text = new.clean(row)
            r["drops"] += action == "drop"
            if text != row["text"]:
                r["changed"] += 1
                r["changed_ids"].append(row["doc_id"])
                r["other_changes"] += not only_email(row["text"], text)
                r["not_idempotent"] += new.clean(dict(row, text=text)) != ("keep", text)
        week1[pack] = r
        ok &= r["drops"] == r["other_changes"] == r["not_idempotent"] == 0 and (pack == "cadj-commits" or r["changed"] == 0)
        if pack == "cadj-commits":
            texts = {row["doc_id"]: row["text"] for row in rows}
    rep["week1"] = week1

    labelled = set()
    for f in sorted(REPO.glob("diagnosis/submissions/cadj-commits/*/labels.csv")):
        with open(f, encoding="utf-8", newline="") as fh:
            labelled |= {r["doc_id"] for r in csv.DictReader(fh) if "F1" in (r.get("diseases") or "")}
    fixed = sorted(d for d in labelled if d in week1["cadj-commits"]["changed_ids"])
    rep["f1_labelled"] = dict(labelled=len(labelled), in_pack=sum(d in texts for d in labelled), fixed=len(fixed),
                              not_fixed_ids=sorted(labelled - set(fixed)))

    equiv = {}
    for d in sorted(p for p in args.sample.iterdir() if p.is_dir()):
        rows = []
        for f in sorted(d.glob("*.parquet")):
            for batch in pq.ParquetFile(f).iter_batches(batch_size=500):
                rows += batch.to_pylist()
                if len(rows) >= args.per_pack:
                    break
            if len(rows) >= args.per_pack:
                break
        differ = not_email = 0
        for row in rows[:args.per_pack]:
            a, b = new.clean(row), old.clean(row)
            if a != b:
                differ += 1
                not_email += not (d.name == "cadj-commits" and b == ("keep", row["text"]) and a[0] == "fix" and only_email(row["text"], a[1]))
        equiv[d.name] = dict(docs=len(rows[:args.per_pack]), differ=differ, differ_not_email=not_email)
        ok &= not_email == 0 and (d.name == "cadj-commits" or differ == 0)
    rep["equivalence"] = equiv

    r = dict(docs=0, changed=0, addresses_masked=0, drops=0, other_changes=0)
    for f in sorted((args.sample / "cadj-commits").glob("*.parquet")):
        for batch in pq.ParquetFile(f).iter_batches(batch_size=2000):
            for row in batch.to_pylist():
                r["docs"] += 1
                action, text = new.clean(row)
                r["drops"] += action == "drop"
                if text != row["text"]:
                    r["changed"] += 1
                    r["addresses_masked"] += text.count("<EMAIL>") - row["text"].count("<EMAIL>")
                    r["other_changes"] += not only_email(row["text"], text)
    rep["sample_cadj_commits"] = r
    ok &= r["drops"] == r["other_changes"] == 0

    rep["result"] = "PASS" if ok else "FAIL"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("week1", "equivalence")}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
