#!/usr/bin/env python3
"""lang_label_check.py - Week-3 task 5: language labels of script-sharing packs, and filters that drop over 20%.

Four steps, each writes counts and doc IDs only (never document text):

  evaluate  Score the check on what readers labelled. Positives: documents a reader marked D1 (wrong language).
            Gold documents (clean by definition) show false positives. Text from the 500-document diagnosis packs.
            -> lang_label_labelled.csv (one row per reader row, the readers' labels kept, plus a same_script_d1 column)
            -> lang_label_eval_summary.csv
  run       The check on the CAP-1 tokenizer-sample packs (the inputs of the p1536 shards), every document.
            -> lang_label_by_pack.csv, lang_label_mislabelled_ids.csv; one result per document in --work-dir (not committed)
  flag      Each filter whose drop rate is over drop_threshold (0.20) in a pack, from a drop-rate table: by default the
            lead's shard audit audit_v1.csv (#523), per pack, since clean.py does not record which filter dropped a
            document. A per-filter table (pack, filter, docs_in, docs_dropped) is read the same way when one exists.
            -> lang_label_filter_flags.csv
  sample    About 20 flagged documents from the run, fixed seed, for the mr and sa readers
            -> lang_label_review_sample.csv (the readers fill reader_says_lang and reader_note)
  report    The tables of all three as Markdown -> lang_label_tables.md

Setup: the IndicLID environment of ../romanised (README, Part 2), whose Python has fasttext and pyarrow:
  PY=../romanised/.venv-lid/bin/python
  $PY lang_label_check.py evaluate
  $PY lang_label_check.py run --cap1-dir <folder with ind-*/Part_1 and ind-*/Heldout> --work-dir <scratch folder>
  $PY lang_label_check.py flag [--drop-rates <csv>] [--drop-threshold 0.2] [--drop-ids <csv> --work-dir <folder>]
  $PY lang_label_check.py sample --work-dir <the run step's work dir>
  $PY lang_label_check.py report
Settings are in lang_label_config.json (--config to use another).
"""
import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import lang_id

HERE = Path(__file__).resolve().parent
RESULT_COLS = ["script_share", "letters", "lid_lang", "lid_label", "vote_share", "marker_lang", "verdict", "found_lang", "sign_letters"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def read_texts(paths, ids=None):
    """{doc_id: text} from parquet files; only the given ids when ids is set."""
    import pyarrow.parquet as pq  # noqa: PLC0415
    out = {}
    for p in paths:
        t = pq.read_table(p, columns=["doc_id", "text"])
        for d, x in zip(t.column("doc_id").to_pylist(), t.column("text").to_pylist()):
            if ids is None or d in ids:
                out[d] = x
    return out


def diseases(row):
    return {d.strip() for d in (row.get("diseases") or "").replace(",", ";").split(";") if d.strip()}


def pct(n, d):
    return f"{100 * n / d:.2f}" if d else ""


# ---------------------------------------------------------------- evaluate
def evaluate(cfg, predict, out_dir):
    subs, gold_dir, packs_dir = (lang_id.cfg_path(cfg, k) for k in ("submissions_dir", "gold_dir", "diag_packs_dir"))
    rows, summary, d1_table = [], [], []
    for pack, lang in cfg["packs"].items():
        reader_rows = []
        for f in sorted((subs / pack).glob("*/labels.csv")):
            for r in read_csv(f):
                if r.get("doc_id"):
                    reader_rows.append(dict(r, reader=f.parent.name))
        gold_file = gold_dir / f"{pack}_gold.csv"
        gold = {r["doc_id"] for r in read_csv(gold_file)} if gold_file.exists() else set()
        pack_file = packs_dir / f"{pack}.parquet"
        if not pack_file.exists():
            print(f"{pack}: no diagnosis pack at {pack_file}, skipped", file=sys.stderr)
            continue
        want = {r["doc_id"] for r in reader_rows} | gold
        texts = read_texts([pack_file], want)
        res = {d: lang_id.judge(texts[d], lang, predict, cfg) for d in want if d in texts}
        d1_docs = {r["doc_id"] for r in reader_rows if "D1" in diseases(r)}

        def same_script(d):
            """The rule: a D1 document counts as same-script when it is judged and at least same_script_min_share of
            its letters are in the pack's script, so the readers' 'wrong language' cannot be another script."""
            j = res.get(d)
            return int(bool(j) and j["verdict"] not in ("short", "other_script")
                       and j["script_share"] >= cfg["same_script_min_share"])
        for r in reader_rows:
            j = res.get(r["doc_id"], {})
            d1 = "D1" in diseases(r)
            rows.append({"pack": pack, "doc_id": r["doc_id"], "reader": r["reader"], "reader_verdict": r.get("verdict", ""),
                         "reader_diseases": ";".join(sorted(diseases(r))), "d1": int(d1),
                         "same_script_d1": same_script(r["doc_id"]) if d1 else "",
                         "in_gold": int(r["doc_id"] in gold), **{k: j.get(k, "") for k in RESULT_COLS}})
        same = {d for d in d1_docs if same_script(d)}
        for d in sorted(d1_docs):
            d1_table.append({"pack": pack, "doc_id": d, "d1_readers": sum(r["doc_id"] == d and "D1" in diseases(r)
                                                                         for r in reader_rows),
                             "same_script_d1": same_script(d), **{k: res.get(d, {}).get(k, "") for k in RESULT_COLS}})
        neg = {r["doc_id"] for r in reader_rows} - d1_docs
        summary.append({
            "pack": pack, "lang": lang, "labelled_docs": len({r["doc_id"] for r in reader_rows}),
            "d1_docs": len(d1_docs), "same_script_d1_docs": len(same),
            "caught_mislabelled": sum(res[d]["verdict"] == "mislabelled" for d in same),
            "caught_uncertain": sum(res[d]["verdict"] == "uncertain" for d in same),
            "non_d1_docs": len(neg), "non_d1_mislabelled": sum(res.get(d, {}).get("verdict") == "mislabelled" for d in neg),
            "non_d1_uncertain": sum(res.get(d, {}).get("verdict") == "uncertain" for d in neg),
            "gold_docs": len(gold & set(res)), "gold_mislabelled": sum(res[d]["verdict"] == "mislabelled" for d in gold if d in res),
            "gold_uncertain": sum(res[d]["verdict"] == "uncertain" for d in gold if d in res)})
    cols = ["pack", "doc_id", "reader", "reader_verdict", "reader_diseases", "d1", "same_script_d1", "in_gold"] + RESULT_COLS
    write_csv(out_dir / "lang_label_labelled.csv", rows, cols)
    write_csv(out_dir / "lang_label_eval_summary.csv", summary, list(summary[0]) if summary else ["pack"])
    write_csv(out_dir / "lang_label_d1_docs.csv", d1_table, ["pack", "doc_id", "d1_readers", "same_script_d1"] + RESULT_COLS)


# ---------------------------------------------------------------- run
def run(cfg, predict, out_dir, cap1_dir, work_dir):
    work_dir.mkdir(parents=True, exist_ok=True)
    by_pack, flagged = [], []
    for pack, lang in cfg["packs"].items():
        files = sorted((cap1_dir / pack).glob("*/*.parquet"))
        if not files:
            print(f"{pack}: no parquet under {cap1_dir / pack}, skipped", file=sys.stderr)
            continue
        texts = read_texts(files)
        ids = sorted(texts)
        if cfg["max_docs_per_pack"] and len(ids) > cfg["max_docs_per_pack"]:
            ids = sorted(random.Random(cfg["seed"]).sample(ids, cfg["max_docs_per_pack"]))
        results = []
        for i, d in enumerate(ids, 1):
            results.append({"doc_id": d, **lang_id.judge(texts[d], lang, predict, cfg)})
            if i % 20000 == 0:
                print(f"  {pack}: {i} of {len(ids)}", flush=True)
        write_csv(work_dir / f"{pack}_lang.csv", results, ["doc_id"] + RESULT_COLS)
        v = Counter(r["verdict"] for r in results)
        judged = v["agree"] + v["mislabelled"] + v["uncertain"] + v["short_disagree"]
        as_lang = Counter(r["found_lang"] for r in results if r["verdict"] == "mislabelled")
        unc_lang = Counter(r["lid_lang"] for r in results if r["verdict"] == "uncertain")
        raw = Counter(r["lid_label"] for r in results if r["lid_label"])
        by_pack.append({"pack": pack, "lang": lang, "docs_in_pack": len(texts), "docs_checked": len(results),
                        **{k: v[k] for k in lang_id.VERDICTS}, "judged": judged,
                        "agree_pct": pct(v["agree"], judged), "mislabelled_pct": pct(v["mislabelled"], judged),
                        "uncertain_pct": pct(v["uncertain"], judged), "short_disagree_pct": pct(v["short_disagree"], judged),
                        "mislabelled_as": "; ".join(f"{k}:{n}" for k, n in as_lang.most_common()),
                        "uncertain_lid_says": "; ".join(f"{k}:{n}" for k, n in unc_lang.most_common(5)),
                        "lid_labels": "; ".join(f"{k}:{n}" for k, n in raw.most_common(6))})
        flagged += [{"pack": pack, "doc_id": r["doc_id"], "found_lang": r["found_lang"], "lid_label": r["lid_label"],
                     "vote_share": r["vote_share"], "marker_lang": r["marker_lang"]}
                    for r in results if r["verdict"] == "mislabelled"]
        print(f"{pack}: {dict(v)}", flush=True)
    write_csv(out_dir / "lang_label_by_pack.csv", by_pack, list(by_pack[0]) if by_pack else ["pack"])
    write_csv(out_dir / "lang_label_mislabelled_ids.csv", flagged,
              ["pack", "doc_id", "found_lang", "lid_label", "vote_share", "marker_lang"])


# ---------------------------------------------------------------- flag
WHOLE_PIPELINE = "clean.py all rules (no per-filter counts)"


def normalise_drop_row(r, source):
    """One drop-rate row in either format, as {pack, lang, filter, docs_in, docs_dropped, status, source}.

    - per filter: pack, filter, docs_in, docs_dropped[, note]
    - the lead's shard audit (audit_v1.csv, #523): pack_id, lang, shards, docs_raw, docs_kept, docs_dropped, drop_rate.
      clean.py does not record which filter dropped a document, so a row is the whole pipeline of one pack. A pack
      with no shard was not cleaned (passed through as unsupported), so its "drops" are not drops.
    """
    if "pack_id" in r:
        no_shard = r.get("shards", "1") == "0" or "no shard" in r.get("drop_rate", "")
        return {"pack": r["pack_id"], "lang": r.get("lang", ""), "filter": WHOLE_PIPELINE,
                "docs_in": int(r["docs_raw"]), "docs_dropped": int(r["docs_dropped"]),
                "status": "no shard (not cleaned)" if no_shard else "cleaned", "source": source}
    return {"pack": r["pack"], "lang": "", "filter": r["filter"], "docs_in": int(r["docs_in"]),
            "docs_dropped": int(r["docs_dropped"]), "status": "cleaned", "source": r.get("note") or source}


def flag(cfg, out_dir, drop_rates, threshold, drop_ids=None, work_dir=None):
    """Flag each (pack, filter) whose drop rate is over the threshold; optionally, how many drops were mislabelled."""
    verdicts = {}
    if drop_ids and work_dir:
        for f in Path(work_dir).glob("*_lang.csv"):
            pack = f.name[:-len("_lang.csv")]
            verdicts.update({(pack, r["doc_id"]): r["verdict"] for r in read_csv(f)})
    dropped = defaultdict(list)
    if drop_ids:
        for r in read_csv(drop_ids):
            dropped[(r["pack"], r["filter"])].append(r["doc_id"])
    out = []
    for r in read_csv(drop_rates):
        r = normalise_drop_row(r, Path(drop_rates).name)
        n_in, n_drop = r["docs_in"], r["docs_dropped"]
        rate = n_drop / n_in if n_in else 0.0
        cleaned = r["status"] == "cleaned"
        row = {"pack": r["pack"], "filter": r["filter"], "docs_in": n_in, "docs_dropped": n_drop,
               "drop_rate_pct": f"{100 * rate:.2f}" if cleaned else "", "status": r["status"],
               "over_threshold": int(cleaned and rate > threshold),
               "lang": r["lang"] or cfg["packs"].get(r["pack"], ""), "source": r["source"]}
        ids = dropped.get((r["pack"], r["filter"]), [])
        if ids and verdicts:
            v = Counter(verdicts.get((r["pack"], d), "not_checked") for d in ids)
            row.update({k: v[k] for k in ("agree", "mislabelled", "uncertain", "not_checked")})
        out.append(row)
    cols = ["pack", "lang", "filter", "docs_in", "docs_dropped", "drop_rate_pct", "status", "over_threshold",
            "agree", "mislabelled", "uncertain", "not_checked", "source"]
    write_csv(out_dir / "lang_label_filter_flags.csv", out, cols)
    n = sum(r["over_threshold"] for r in out)
    print(f"{n} of {len(out)} filter/pack rows drop over {100 * threshold:g}%")
    return out


# ---------------------------------------------------------------- sample
def sample(cfg, out_dir, work_dir, size=20):
    """A fixed-seed list of flagged documents for the readers (lead, 17 Nov: about 20 from the large run).

    Every 'mislabelled' document first, then 'uncertain' ones, spread over the packs. Which reader: the language the
    check found, or the pack's language when that is the one in question (Hindi found in a Marathi pack: mr reader)."""
    rng = random.Random(cfg["seed"])
    mis, unc = [], []
    for pack, lang in cfg["packs"].items():
        f = Path(work_dir) / f"{pack}_lang.csv"
        if not f.exists():
            continue
        for r in read_csv(f):
            if r["verdict"] in ("mislabelled", "uncertain"):
                row = {"pack": pack, "pack_lang": lang, "doc_id": r["doc_id"], "verdict": r["verdict"],
                       "found_lang": r["found_lang"] if r["found_lang"] != "unknown" else r["lid_lang"],
                       "vote_share": r["vote_share"], "marker_lang": r["marker_lang"],
                       "reader": "sa" if "sa" in (lang, r["found_lang"].split("_")[0]) else lang}
                (mis if r["verdict"] == "mislabelled" else unc).append(row)
    by_pack = defaultdict(list)
    for r in unc:
        by_pack[r["pack"]].append(r)
    for rows in by_pack.values():
        rng.shuffle(rows)
    picked = list(mis)
    while len(picked) < size and any(by_pack.values()):  # round-robin over the packs
        for pack in sorted(by_pack):
            if by_pack[pack] and len(picked) < size:
                picked.append(by_pack[pack].pop())
    cols = ["pack", "pack_lang", "doc_id", "verdict", "found_lang", "vote_share", "marker_lang", "reader",
            "reader_says_lang", "reader_note"]
    write_csv(out_dir / "lang_label_review_sample.csv", picked, cols)


# ---------------------------------------------------------------- report
def md_table(rows, cols):
    if not rows:
        return "_none_\n"
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def report(cfg, out_dir):
    parts = ["# Language-label check: tables\n",
             "Made by `lang_label_check.py report` from the CSV files in this folder. Counts and IDs only. "
             "The findings and limits are in `lang_label_check.md`.\n"]
    f = out_dir / "lang_label_eval_summary.csv"
    if f.exists():
        parts += ["\n## 1. On what readers labelled (diagnosis packs)\n\n",
                  md_table(read_csv(f), ["pack", "labelled_docs", "d1_docs", "same_script_d1_docs", "caught_mislabelled",
                                         "caught_uncertain", "non_d1_docs", "non_d1_mislabelled", "non_d1_uncertain",
                                         "gold_docs", "gold_mislabelled", "gold_uncertain"])]
    f = out_dir / "lang_label_d1_docs.csv"
    if f.exists():
        parts += [f"\n### Documents readers marked D1 (same_script_d1 = 1 when at least "
                  f"{cfg['same_script_min_share']:g} of the letters are in the pack's script)\n\n",
                  md_table(read_csv(f), ["pack", "doc_id", "d1_readers", "script_share", "same_script_d1", "verdict",
                                         "lid_label", "vote_share", "marker_lang", "sign_letters"])]
    f = out_dir / "lang_label_by_pack.csv"
    if f.exists():
        rows = read_csv(f)
        parts += ["\n## 2. CAP-1 packs (inputs of the p1536 shards)\n\n",
                  md_table(rows, ["pack", "docs_checked", "short", "other_script", "judged", "agree_pct",
                                  "mislabelled", "mislabelled_pct", "mislabelled_as", "uncertain", "uncertain_pct",
                                  "uncertain_lid_says", "short_disagree"]),
                  "\nIndicLID-FTN labels (letter-weighted top label of each judged document):\n\n",
                  md_table(rows, ["pack", "lid_labels"])]
    f = out_dir / "lang_label_filter_flags.csv"
    if f.exists():
        rows = read_csv(f)
        src = sorted({r["source"] for r in rows})
        parts += [f"\n## 3. Filters that drop over {100 * cfg['drop_threshold']:g}%\n\n",
                  f"Drop rates from {', '.join(f'`{s}`' for s in src)}. A filter's drops are at most its pack's drops, "
                  "so a pack under the line has no filter over it.\n\n"]
        if any("ASSUMED" in s.upper() for s in src):
            parts += ["**These drop rates are ASSUMED placeholders**, not measurements.\n\n"]
        parts += [md_table(rows, ["pack", "lang", "filter", "docs_in", "docs_dropped", "drop_rate_pct", "status",
                                  "over_threshold"]),
                  f"\n{sum(r['over_threshold'] == '1' for r in rows)} of {len(rows)} rows are over the line.\n"]
    (out_dir / "lang_label_tables.md").write_text("".join(parts), encoding="utf-8")
    print(f"wrote {out_dir / 'lang_label_tables.md'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", type=Path, default=HERE / "lang_label_config.json")
    ap.add_argument("--out-dir", type=Path, default=HERE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("evaluate")
    r = sub.add_parser("run")
    r.add_argument("--cap1-dir", type=Path, required=True)
    r.add_argument("--work-dir", type=Path, required=True, help="per-document results (not committed)")
    r.add_argument("--max-docs", type=int, help="override max_docs_per_pack (0: all)")
    fl = sub.add_parser("flag")
    fl.add_argument("--drop-rates", type=Path)
    fl.add_argument("--drop-threshold", type=float)
    fl.add_argument("--drop-ids", type=Path, help="CSV pack,filter,doc_id of the dropped documents (optional)")
    fl.add_argument("--work-dir", type=Path, help="the run step's work dir, to look up the dropped documents")
    sm = sub.add_parser("sample")
    sm.add_argument("--work-dir", type=Path, required=True, help="the run step's work dir")
    sm.add_argument("--size", type=int, default=20)
    sub.add_parser("report")
    a = ap.parse_args(argv)
    cfg = lang_id.load_config(a.config)
    if a.cmd in ("evaluate", "run"):
        predict = lang_id.FastTextLID(lang_id.cfg_path(cfg, "lid_model"))
        if a.cmd == "evaluate":
            evaluate(cfg, predict, a.out_dir)
        else:
            if a.max_docs is not None:
                cfg["max_docs_per_pack"] = a.max_docs
            run(cfg, predict, a.out_dir, a.cap1_dir, a.work_dir)
    elif a.cmd == "flag":
        if a.drop_threshold is not None:
            cfg["drop_threshold"] = a.drop_threshold
        flag(cfg, a.out_dir, a.drop_rates or lang_id.cfg_path(cfg, "drop_rates_csv"), cfg["drop_threshold"],
             a.drop_ids, a.work_dir)
    elif a.cmd == "sample":
        sample(cfg, a.out_dir, a.work_dir, a.size)
    else:
        report(cfg, a.out_dir)


if __name__ == "__main__":
    main()
