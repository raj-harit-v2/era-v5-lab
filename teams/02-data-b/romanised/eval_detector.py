#!/usr/bin/env python3
"""eval_detector.py - precision and recall of detector.py on testset_100.csv, and a false-positive check on gold.

Ground truth is the readers' labels: a document is D2 when at least one reader marked it D2.
Next to it, the checked labels: the readers' labels corrected by checked_labels.csv, where a second look found no
romanised Indic phrase in a reader's D2 document (English text, or a proper name only); each row gives the reason.
Precision = how many of the detector's hits really are D2; recall = how many of the D2 documents it finds.
Gold documents (two readers marked them clean) cannot measure recall, since none of them is D2, but every gold
document the detector flags is a false positive; the gold check counts them.
It also tries a few other thresholds, so the choice in detector.py can be checked, and lists every miss and false alarm.

Usage
  python3 eval_detector.py --testset testset_100.csv --checked checked_labels.csv --gold-dir ../gold \
                           --packs-dir packs --out eval_v1.md
  ../gold/<pack_id>_gold.csv lists a pack's gold doc_ids.
"""
import argparse
import csv
from pathlib import Path

import pyarrow.parquet as pq

import detector


def scores(pairs):
    tp = sum(p and y for p, y in pairs)
    fp = sum(p and not y for p, y in pairs)
    fn = sum(y and not p for p, y in pairs)
    tn = len(pairs) - tp - fp - fn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return tp, fp, fn, tn, prec, rec


def pack_texts(packs_dir, pack):
    return {d["doc_id"]: d["text"] or ""
            for d in pq.read_table(packs_dir / f"{pack}.parquet", columns=["doc_id", "text"]).to_pylist()}


def gold_check(gold_dir, packs_dir):
    """[(pack, gold docs, flagged doc_ids)] for every <pack>_gold.csv that has its pack in packs_dir."""
    out = []
    for path in sorted(gold_dir.glob("ind-*_gold.csv")):
        pack = path.name[:-len("_gold.csv")]
        if not (packs_dir / f"{pack}.parquet").exists():
            print(f"gold: skip {pack}, no parquet in {packs_dir}")
            continue
        ids = [r["doc_id"] for r in csv.DictReader(open(path, encoding="utf-8-sig"))]
        text = pack_texts(packs_dir, pack)
        missing = [d for d in ids if d not in text]
        if missing:
            print(f"gold: {pack} has {len(missing)} doc_ids that are not in the pack")
        out.append((pack, len(ids), [d for d in ids if d in text and detector.detect(text[d])["romanised"]]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score the D2 detector on the labelled test set and on gold.")
    ap.add_argument("--testset", default="testset_100.csv", type=Path)
    ap.add_argument("--checked", default="checked_labels.csv", type=Path)
    ap.add_argument("--gold-dir", default=Path(__file__).resolve().parent.parent / "gold", type=Path)
    ap.add_argument("--packs-dir", default="packs", type=Path)
    ap.add_argument("--out", default="eval_v1.md", type=Path)
    a = ap.parse_args(argv)

    rows = list(csv.DictReader(open(a.testset, encoding="utf-8")))
    checked = {(r["pack"], r["doc_id"]): r for r in csv.DictReader(open(a.checked, encoding="utf-8"))}
    text = {}
    for pack in sorted({r["pack"] for r in rows}):
        text.update({(pack, d): t for d, t in pack_texts(a.packs_dir, pack).items()})
    for r in rows:
        k = (r["pack"], r["doc_id"])
        r["reader"] = r["reader_label"] == "1"
        r["checked"] = checked[k]["checked_label"] == "1" if k in checked else r["reader"]
        r["why"] = checked[k]["reason"] if k in checked else ""
        r["det"] = detector.detect(text[k])
    gold = gold_check(a.gold_dir, a.packs_dir)
    gold_n = sum(n for _, n, _ in gold)
    gold_flagged = [(p, d) for p, _, f in gold for d in f]

    out = ["# D2 detector on 100 labelled documents (v1)", "",
           f"Test set: `{a.testset.name}`, {len(rows)} documents: "
           f"{sum(r['reader'] for r in rows)} that a reader marked D2 and {sum(not r['reader'] for r in rows)} "
           "that no reader marked D2 (half of those chosen among documents with at least 10% Latin letters).", "",
           "Ground truth: the readers' labels (a document is D2 when at least one reader marked it D2). "
           f"Next to them, the checked labels: {len(checked)} reader D2 marks were looked at again and hold no "
           "romanised Indic phrase (English text, or a proper name only); `checked_labels.csv` gives the reason for "
           "each, and they are listed at the end. No negative was changed.", "",
           f"Detector rule: at least {detector.MIN_HITS} romanised Indic words, {detector.MIN_DISTINCT} of them "
           f"different, or at least {detector.MIN_IAST} IAST letters (see `detector.py`).", "",
           "## Result", "",
           "| labels | D2 docs | flagged | true pos | false pos | missed | precision | recall |",
           "|---|---|---|---|---|---|---|---|"]
    for name, title in (("reader", "readers' labels (ground truth)"), ("checked", "checked labels")):
        tp, fp, fn, tn, p, rc = scores([(r["det"]["romanised"], r[name]) for r in rows])
        out.append(f"| {title} | {tp + fn} | {tp + fp} | {tp} | {fp} | {fn} | {p:.0%} | {rc:.0%} |")

    out += ["", "## Gold check (false positives)", "",
            f"Gold documents are ones two readers marked clean, so none is D2 and every flag is a false positive. "
            f"On all gold documents in `teams/02-data-b/gold/` ({gold_n} in {len(gold)} packs) the detector flags "
            f"**{len(gold_flagged)}**" + (": " + ", ".join(f"{d} ({p})" for p, d in gold_flagged) if gold_flagged
                                         else "") + ".", "",
            "| pack | gold docs | flagged |", "|---|---|---|"]
    out += [f"| {p} | {n} | {len(f)} |" for p, n, f in gold]

    out += ["", "## Other thresholds", "",
            "| min hits | min distinct | min IAST | flagged | precision (readers) | recall (readers) "
            "| precision (checked) | recall (checked) | gold flagged |", "|---|---|---|---|---|---|---|---|---|"]
    gold_texts = {}
    for p, _, _ in gold:
        ids = {r["doc_id"] for r in csv.DictReader(open(a.gold_dir / f"{p}_gold.csv", encoding="utf-8-sig"))}
        gold_texts.update({(p, d): t for d, t in pack_texts(a.packs_dir, p).items() if d in ids})
    for mh in (2, 3, 4, 5):
        for md in (1, 2):
            for mi in (3, 5, 10):
                det = [detector.detect(text[(r["pack"], r["doc_id"])], mh, md, mi)["romanised"] for r in rows]
                t1, f1, _, _, p1, r1 = scores(list(zip(det, (r["reader"] for r in rows))))
                _, _, _, _, p2, r2 = scores(list(zip(det, (r["checked"] for r in rows))))
                g = sum(detector.detect(t, mh, md, mi)["romanised"] for t in gold_texts.values())
                mark = " **(used)**" if (mh, md, mi) == (detector.MIN_HITS, detector.MIN_DISTINCT,
                                                         detector.MIN_IAST) else ""
                out.append(f"| {mh} | {md} | {mi} | {t1 + f1} | {p1:.0%} | {r1:.0%} | {p2:.0%} | {r2:.0%} | {g}{mark} |")

    def line(r):
        d = r["det"]
        return (f"| {r['doc_id']} | {r['pack']} | {r['n_d2_marks']}/{r['n_readers']} | {d['hits']} ({d['distinct']}) "
                f"| {d['iast']} | {', '.join(d['examples']) or '-'} | {r['why'] or '-'} |")

    head = ["| doc_id | pack | D2 marks / readers | Indic words (distinct) | IAST | words matched | checked note |",
            "|---|---|---|---|---|---|---|"]
    misses = [r for r in rows if r["reader"] and not r["det"]["romanised"]]
    false = [r for r in rows if not r["reader"] and r["det"]["romanised"]]
    out += ["", f"## Missed (reader D2, not flagged): {len(misses)}", "",
            f"{sum(not r['checked'] for r in misses)} of them are among the checked-label changes (a note is given)."
            ] + [""] + head + [line(r) for r in misses]
    out += ["", f"## False alarms (flagged, no reader D2): {len(false)}", ""] + head + [line(r) for r in false]
    out += ["", f"## Reader D2 marks changed to 0 in the checked labels: {len(checked)}", ""] + head + \
           [line(r) for r in rows if r["reader"] and not r["checked"]]
    a.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:25]))


if __name__ == "__main__":
    main()
