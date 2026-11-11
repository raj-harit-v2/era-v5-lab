#!/usr/bin/env python3
"""eval_v2.py - the word list and IndicLID compared as segment classifiers under the same document rule.

Both run through doc_detector.decide, so they differ only in which segments they call romanised Indic.
Two levels are scored on testset_100.csv:
  contains   the document has at least one romanised segment (what readers marked as D2)
  majority   romanised segments hold more than half the document's words (TSAI's rule for the cap)
Ground truth is the readers' labels; the checked labels (checked_labels.csv) are shown next to them.
Gold check: gold documents (two readers marked them clean) are not D2, so every flag there is a false positive.
TSAI's rule for the choice: keep the tool that is better on the gold check; on a tie, the one with the higher recall
on the readers' labels at the contains level.

Usage (after indiclid_segments.py has filled indiclid/cache.json)
  python eval_v2.py --testset testset_100.csv --checked checked_labels.csv --gold-dir ../gold --packs-dir packs \
                    --out eval_v2.md
"""
import argparse
import csv
from pathlib import Path

import pyarrow.parquet as pq

import doc_detector
import indiclid_segments


def scores(pairs):
    tp = sum(p and y for p, y in pairs)
    fp = sum(p and not y for p, y in pairs)
    fn = sum(y and not p for p, y in pairs)
    return tp, fp, fn, tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare the word list and IndicLID on the labelled rows and on gold.")
    ap.add_argument("--testset", default="testset_100.csv", type=Path)
    ap.add_argument("--checked", default="checked_labels.csv", type=Path)
    ap.add_argument("--gold-dir", default=Path(__file__).resolve().parent.parent / "gold", type=Path)
    ap.add_argument("--packs-dir", default="packs", type=Path)
    ap.add_argument("--out", default="eval_v2.md", type=Path)
    a = ap.parse_args(argv)

    tools = {"word list": None, "IndicLID": indiclid_segments.classifier()}
    rows = list(csv.DictReader(open(a.testset, encoding="utf-8")))
    checked = {(r["pack"], r["doc_id"]): r["checked_label"] == "1"
               for r in csv.DictReader(open(a.checked, encoding="utf-8"))}
    gold = {}
    for path in sorted(a.gold_dir.glob("ind-*_gold.csv")):
        gold[path.name[:-len("_gold.csv")]] = {r["doc_id"] for r in csv.DictReader(open(path, encoding="utf-8-sig"))}

    test_keys = {(r["pack"], r["doc_id"]) for r in rows}
    res = {t: {} for t in tools}          # tool -> (pack, doc) -> decision, for every pack document
    for path in sorted(a.packs_dir.glob("ind-*.parquet")):
        pack = path.stem
        for d in pq.read_table(path, columns=["doc_id", "text"]).to_pylist():
            for t, clf in tools.items():
                res[t][(pack, d["doc_id"])] = doc_detector.decide(d["text"] or "", clf)
    missing = test_keys - set(res["word list"])
    if missing:
        raise SystemExit(f"error: {len(missing)} test documents are not in {a.packs_dir}")

    reader = {(r["pack"], r["doc_id"]): r["reader_label"] == "1" for r in rows}
    labels = {"readers": reader, "checked": {k: checked.get(k, y) for k, y in reader.items()}}
    out = ["# Romanised Indic: word list vs IndicLID (v2)", "",
           f"Both tools are segment classifiers inside `doc_detector.py`: the document is cut into lines and sentences, "
           f"each tool says which segments are romanised Indic, and the document is romanised when those segments "
           f"hold more than {doc_detector.MAJORITY:.0%} of its words (TSAI's rule for the cap).", "",
           f"Test set: `{a.testset.name}`, {len(rows)} documents, {sum(reader.values())} marked D2 by a reader. "
           f"Ground truth: the readers' labels; the checked labels (`{a.checked.name}`, {len(checked)} reader D2 "
           f"marks changed to 0) are shown next to them.", "",
           "## Contains romanised Indic (at least one romanised segment)", "",
           "| tool | labels | D2 docs | flagged | true pos | false pos | missed | precision | recall |",
           "|---|---|---|---|---|---|---|---|---|"]
    recall = {}
    for t in tools:
        for name, lab in labels.items():
            tp, fp, fn, p, r = scores([(res[t][k]["contains"], y) for k, y in lab.items()])
            out.append(f"| {t} | {name} | {tp + fn} | {tp + fp} | {tp} | {fp} | {fn} | {p:.0%} | {r:.0%} |")
            recall[(t, name)] = r

    out += ["", f"## Mostly romanised (> {doc_detector.MAJORITY:.0%} of the words)", "",
            "| tool | flagged in the test set | of them reader D2 | flagged in all 22 packs (11,000 docs) "
            "| highest share in any pack document |", "|---|---|---|---|---|"]
    for t in tools:
        flagged = [k for k in reader if res[t][k]["romanised"]]
        top = max(res[t].items(), key=lambda kv: kv[1]["share"])
        out.append(f"| {t} | {len(flagged)} | {sum(reader[k] for k in flagged)} "
                   f"| {sum(d['romanised'] for d in res[t].values())} "
                   f"| {top[1]['share']:.0%} ({top[0][0]} {top[0][1]}) |")
    out += ["", "Precision and recall are not given at this level: readers marked D2 for any romanised text, so there "
            "is no labelled set of mostly-romanised documents to measure them on."]

    gold_n = sum(len(ids & {d for p, d in res['word list'] if p == pack}) for pack, ids in gold.items())
    out += ["", "## Gold check (false positives)", "",
            f"All gold documents in `teams/02-data-b/gold/` ({gold_n} in {len(gold)} packs). Two readers marked "
            "each one clean, so none is D2 and every flag is a false positive.", "",
            "| tool | flagged: contains | flagged: mostly romanised | documents flagged (contains) |",
            "|---|---|---|---|"]
    gold_fp = {}
    for t in tools:
        keys = [(p, d) for p, ids in gold.items() for d in ids if (p, d) in res[t]]
        c = [k for k in keys if res[t][k]["contains"]]
        m = sum(res[t][k]["romanised"] for k in keys)
        gold_fp[t] = (m, len(c))
        out.append(f"| {t} | {len(c)} | {m} | {', '.join(f'{d} ({p})' for p, d in sorted(c)[:10]) or '-'}"
                   f"{' ...' if len(c) > 10 else ''} |")

    best = min(tools, key=lambda t: (gold_fp[t], -recall[(t, "readers")]))
    tie = len({gold_fp[t] for t in tools}) == 1
    out += ["", "## Choice", "",
            f"**{best}**: " + ("both tools flag the same number of gold documents, so the tie is broken by recall on "
                               "the readers' labels (contains level)." if tie else
                               "it flags fewer gold documents.")]

    diff = [k for k in reader if res["word list"][k]["contains"] != res["IndicLID"][k]["contains"]]
    out += ["", f"## Test documents where the tools disagree (contains level): {len(diff)}", "",
            "| doc_id | pack | reader D2 | checked | word list | IndicLID | share (word list / IndicLID) |",
            "|---|---|---|---|---|---|---|"]
    for k in sorted(diff, key=lambda k: (k[0], k[1])):
        w, i = res["word list"][k], res["IndicLID"][k]
        out.append(f"| {k[1]} | {k[0]} | {int(reader[k])} | {int(labels['checked'][k])} | {int(w['contains'])} "
                   f"| {int(i['contains'])} | {w['share']:.0%} / {i['share']:.0%} |")
    a.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
