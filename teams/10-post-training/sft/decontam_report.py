"""Build sft/decontam_report.md from the records that decontam_run.py wrote (G10).

    python decontam_report.py --records decontam_out --out sft/decontam_report.md [--sets a b c] [--pending pending.json]

`--sets` names the sets to include (default: every record in the folder, so use it when the folder also holds
records of an earlier or test run). `pending.json` is {"set-id": "reason", ...} for sets of the mix that were
not run yet. The report holds counts, document ids, benchmark item ids, character offsets and sha256 values only.
It never holds document text (eval firewall, section 4).

The script refuses to write a report when a record failed (a canary, a failed reconciliation), when a record has
no second pass over its clean file, when the records carry different set_sha256 values or different Team 9
tool files, or when the set_sha256 is not the expected one (fingerprints v2, lab PR #280).
"""

import argparse
import json
import sys
from pathlib import Path

from decontam_run import PINNED_SET_SHA256

TOP_HITS = 15  # per set: the hits with the highest coverage
# Benchmarks that Team 9's harnesses run (eval firewall, section 5). Their ids in a fingerprint manifest.
HARNESS_IDS = {"humaneval": "HumanEval", "humaneval_plus": "HumanEval+", "mbpp": "MBPP", "mbpp_plus": "MBPP+",
               "arc_challenge": "ARC-Challenge", "arc_easy": "ARC-Easy", "hellaswag": "HellaSwag",
               "truthfulqa": "TruthfulQA", "mmlu_pro": "MMLU-Pro", "bbh": "BBH", "musr": "MuSR", "belebele": "Belebele"}


class ReportError(Exception):
    pass


def load_records(directory, sets=None):
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(directory).glob("*.record.json"))]
    if sets:
        missing = sorted(set(sets) - {r["set"] for r in recs})
        if missing:
            raise ReportError(f"no record for: {', '.join(missing)}")
        recs = [r for r in recs if r["set"] in set(sets)]
    if not recs:
        raise ReportError(f"no *.record.json in {directory}")
    return recs


def pct(n, d):
    return f"{100 * n / d:.2f}%" if d else "0.00%"


def _same(recs, key, what):
    vals = {json.dumps(r.get(key), sort_keys=True) for r in recs}
    if len(vals) != 1:
        raise ReportError(f"the records carry different {what}: run every set again with the same tools")
    return json.loads(vals.pop())


def build_report(recs, pending, expect_sha=PINNED_SET_SHA256, tools_ref="", title="SFT decontamination report",
                 out_rel="teams/10-post-training/sft/decontam_report.md", full=None):
    names = [r["set"] for r in recs]
    if len(names) != len(set(names)):
        raise ReportError("a set appears twice in the records")
    failed = [r["set"] for r in recs if not r.get("ok")]
    if failed:
        raise ReportError(f"failed record(s), stop and post in G9 first: {', '.join(sorted(failed))}")
    no_recheck = [r["set"] for r in recs if not r.get("recheck_on_clean") or "clean_file_flags_0" not in r["checks"]]
    if no_recheck:
        raise ReportError(f"no second pass over the clean file for: {', '.join(sorted(no_recheck))}")
    if {r["scope"] for r in recs} != {"full set"}:
        raise ReportError("every record must be a full-set run")
    sha = _same(recs, "set_sha256", "set_sha256 values")
    if expect_sha and sha != expect_sha:
        raise ReportError(f"set_sha256 {sha} is not the expected {expect_sha}")
    tools = _same(recs, "tools", "Team 9 tool files (sha256 or commit)")
    benchmarks = _same(recs, "benchmarks", "benchmark lists")
    ref = tools_ref or tools.get("git_commit") or ""
    days = sorted({r["run_at"][:10] for r in recs})

    rows_in = sum(r["rows_in"] for r in recs)
    removed = sum(r["rows_removed"] for r in recs)
    kept = sum(r["rows_kept"] for r in recs)
    title_flag = "" if title == "SFT decontamination report" else f' --title "{title}"'
    L = []
    a = L.append
    a(f"# {title}")
    a("")
    a(f"Run for G10 on {days[0] if len(days) == 1 else days[0] + ' to ' + days[-1]}. Every set was "
      f"checked against Team 9's benchmark fingerprints **{recs[0]['fingerprints']}** with the **full set** "
      "(no `--benchmarks`, `--tags` or `--exclude`), and scanned for canaries.")
    a("")
    a(f"- **set_sha256:** `{sha}`")
    a("- **Tools:** `teams/09-evaluation/decontam/decontam_check.py` and `canary_scan.py`"
      + (f", lab main `{ref}`" if ref else "") + ". sha256 of the files used:")
    for n, h in sorted(tools["files"].items()):
        a(f"  - `{n}`: `{h}`")
    a("- **Runner and reconciliation:** `sft/decontam_run.py`; this file is written by `sft/decontam_report.py`.")
    a(f"- **Sets run:** {len(recs)}. **Rows in:** {rows_in:,}. **Removed (flagged or canary):** {removed:,} "
      f"({pct(removed, rows_in)}). **Kept:** {kept:,}.")
    a("- No benchmark item text is in this file or in the run records: only set names, counts, document ids, "
      "benchmark item ids, offsets and sha256 values.")
    a("")
    a("## 1. Result per set")
    a("")
    col = "" if full is None else " Run on |"
    a(f"| Set |{col} Rows in | Flagged | Canary | Removed | Rows kept | Clean file sha256 |")
    a("|---|" + ("" if full is None else "---|") + "---:|---:|---:|---:|---:|---|")
    for r in recs:
        clean = ", ".join(f"`{c['sha256'][:12]}…`" for c in r["clean"])
        how = "" if full is None else (" full set |" if r["set"] in full else " sample |")
        a(f"| `{r['set']}` |{how} {r['rows_in']:,} | {r['rows_flagged']:,} | {r['rows_canary']:,} | "
          f"{r['rows_removed']:,} ({pct(r['rows_removed'], r['rows_in'])}) | {r['rows_kept']:,} | {clean} |")
    a(f"| **Total** |{'' if full is None else ' |'} **{rows_in:,}** | **{sum(r['rows_flagged'] for r in recs):,}** | "
      f"**{sum(r['rows_canary'] for r in recs):,}** | **{removed:,}** ({pct(removed, rows_in)}) | **{kept:,}** | |")
    if full is not None:
        nf = sum(r["set"] in full for r in recs)
        a("")
        a(f"**Run on** says what was checked: *full set* is every row the converter produced from the whole "
          f"source ({nf} sets); *sample* is the first rows of a split only ({len(recs) - nf} sets), "
          "and is not cleared as a whole.")
    a("")
    a("A row that is both flagged and carries a canary counts once in Removed.")
    a("")
    a("## 2. Flagged documents by benchmark")
    a("")
    benches = sorted({b for r in recs for b in r["by_benchmark"]})
    if benches:
        a("| Set | " + " | ".join(f"`{b}`" for b in benches) + " |")
        a("|---|" + "---:|" * len(benches))
        for r in recs:
            a(f"| `{r['set']}` | " + " | ".join(str(r["by_benchmark"].get(b, 0)) for b in benches) + " |")
    else:
        a("No document was flagged by any benchmark.")
    a("")
    a("A document is flagged when it shares at least one 13-word run (20 tokens for code) with a benchmark item. "
      "The whole document is removed. The count is documents per benchmark, so a document that matches two "
      "benchmarks counts in both columns.")
    a("")
    a("## 3. Flagged documents by coverage")
    a("")
    a("Coverage is the share of one benchmark item's runs that the document contains (the highest over its hits). "
      "The bands are for reading the result; every flagged document is removed whatever its band.")
    a("")
    a("| Set | Flagged | Coverage 0.5 or more | 0.1 to 0.5 | Below 0.1 |")
    a("|---|---:|---:|---:|---:|")
    for r in recs:  # a canary hit has no coverage, and a set with a canary never reaches the report
        cov = [f["max_coverage"] for f in r["flagged"].values() if f["max_coverage"] is not None]
        a(f"| `{r['set']}` | {r['rows_flagged']} | {sum(c >= 0.5 for c in cov)} | "
          f"{sum(0.1 <= c < 0.5 for c in cov)} | {sum(c < 0.1 for c in cov)} |")
    a("")
    a("## 4. Benchmark items with the largest overlap")
    a("")
    any_hit = False
    for r in recs:
        by_item = {}
        for doc, f in r["flagged"].items():
            for h in f["hits"]:
                if h.get("coverage") is None:
                    continue
                e = by_item.setdefault(h["item"], {"docs": set(), "cov": -1.0, "doc": doc, "off": None, "g": None,
                                                    "ig": None})
                e["docs"].add(doc)
                if h["coverage"] > e["cov"]:
                    e.update(cov=h["coverage"], doc=doc, off=h.get("offset"), g=h.get("grams"), ig=h.get("item_grams"))
        if not by_item:
            continue
        any_hit = True
        top = sorted(by_item.items(), key=lambda kv: (-kv[1]["cov"], kv[0]))
        a(f"**`{r['set']}`**: at least {len(by_item)} different benchmark items found in {r['rows_flagged']} "
          f"documents (top {min(TOP_HITS, len(top))} by coverage; the checker lists the best 5 items per document, "
          "so this is a lower bound)")
        a("")
        a("| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |")
        a("|---|---:|---:|---:|---|---:|")
        for item, e in top[:TOP_HITS]:
            a(f"| `{item}` | {len(e['docs'])} | {e['cov']:.3f} | {e['g']} / {e['ig']} | `{e['doc']}` | {e['off']} |")
        a("")
    if not any_hit:
        a("No hit to list.")
        a("")
    a("Coverage is the share of the item's runs found in the document. A value near 1.0 is a full copy; a low "
      "value is a short shared passage, for example a common problem statement. The ids above are enough to find "
      "the document in the set; the item text stays in Team 9's restricted folder.")
    a("")
    a("## 5. Checks")
    a("")
    keys = sorted({k for r in recs for k in r["checks"]})
    a("| Check | Sets passed |")
    a("|---|---:|")
    for k in keys:
        a(f"| `{k}` | {sum(1 for r in recs if r['checks'].get(k))} of {len(recs)} |")
    a("")
    a("`rows_in_eq_kept_plus_removed`: rows in = rows kept + rows removed. `clean_file_flags_0`: the checker, run "
      "again on the clean file, flags 0 of the kept rows. `canary_scan_complete`: `canary_scan.py` read every file "
      "(exit 0 or 1). A set with a failed check or a canary is not in this report (the script stops).")
    a("")
    a("## 6. Inputs (to reproduce a run)")
    a("")
    a("| Set | Input file | Bytes | sha256 |")
    a("|---|---|---:|---|")
    for r in recs:
        for i in r["inputs"]:
            a(f"| `{r['set']}` | `{i['name']}` | {i['bytes']:,} | `{i['sha256']}` |")
    a("")
    a("```")
    a("python teams/10-post-training/sft/decontam_run.py --set <set-id> --input <set>.jsonl --out-dir decontam_out")
    a("python teams/10-post-training/sft/decontam_report.py --records decontam_out --out "
      f"{out_rel} --sets <set-id> ...{title_flag}")
    a("```")
    a("")
    a("## 7. Sets not run yet")
    a("")
    if pending:
        a("| Set | Why |")
        a("|---|---|")
        for s, why in sorted(pending.items()):
            a(f"| `{s}` | {why} |")
    else:
        a("None: every set of the mix was run.")
    a("")
    a("## 8. What this check does not cover")
    a("")
    a(f"- **Benchmarks outside the set.** This fingerprint set holds {len(benchmarks)} benchmark entries: "
      + ", ".join(f"`{b}`" for b in benchmarks) + ".")
    absent = [v for k, v in HARNESS_IDS.items() if k not in benchmarks]
    if absent:
        a(f"  It has no entry for {', '.join(absent)}, which Team 9's harnesses run (eval firewall, section 5, "
          "known gap), so a clean result says nothing about them.")
    if "humaneval_plus" not in benchmarks or "mbpp_plus" not in benchmarks:
        a("  `sft_mix_proposal.md` section 1 lists HumanEval+ and MBPP+ among the benchmarks of this check; "
          "this set does not contain them.")
    a("- **Paraphrase.** The check finds copied runs of words. A reworded or translated item is not found.")
    a("- **Other rows of a set.** Only the rows that were run are covered. A set that was sampled (for example the "
      "first rows of a split) is not cleared as a whole.")
    a("- **Frozen tokenizer.** The check reads the rendered `text`, so it does not depend on the tokenizer. The "
      "effort tiers of the rows do, and Team 3 freezes the tokenizer on Sat 14 Nov.")
    a("- **A rerun is needed** when Team 9 publishes a new fingerprint set (a different set_sha256), and for any set "
      "whose rows change.")
    a("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", required=True, help="folder with the *.record.json files")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sets", nargs="+", help="include only these sets")
    ap.add_argument("--pending", help="JSON file {set-id: reason}")
    ap.add_argument("--tools-ref", default="", help="commit of lab main that holds Team 9's tools "
                                                    "(default: the commit found by decontam_run.py)")
    ap.add_argument("--expect-sha", default=PINNED_SET_SHA256)
    ap.add_argument("--full-sets", nargs="+", help="sets that were run on every row; the others are listed as samples")
    ap.add_argument("--title", default="SFT decontamination report", help="report heading (e.g. for the RL sets)")
    args = ap.parse_args(argv)
    try:
        pending = json.loads(Path(args.pending).read_text(encoding="utf-8")) if args.pending else {}
        repo = Path(__file__).resolve().parents[3]
        out = Path(args.out).resolve()
        out_rel = out.relative_to(repo).as_posix() if out.is_relative_to(repo) else out.name
        md = build_report(load_records(args.records, args.sets), pending, args.expect_sha, args.tools_ref,
                          title=args.title, out_rel=out_rel,
                          full=set(args.full_sets) if args.full_sets is not None else None)
    except (ReportError, OSError, json.JSONDecodeError) as e:
        print(f"decontam_report: {e}", file=sys.stderr)
        return 1
    Path(args.out).write_text(md + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
