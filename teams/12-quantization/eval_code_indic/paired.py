#!/usr/bin/env python3
"""Paired comparison of each format with bf16 on eval-mini code + Indic, item by item.

    python paired.py runs/ --base bf16 [--out paired.md]

Reads runs/<format>/<task>.samples.jsonl (written by run_code_indic_gguf.py). The statistics are those of
../eval_mini/paired.py (difference, 95% CI from the paired variance, McNemar's exact test); every task here is 0/1
per item. Primary metric per task, as G9's results file: acc, GSM8K exact_match (flexible-extract), and for code
the plus pass@1 (an answer counts only if it passes the base and the extra tests).
"""
from __future__ import annotations

import argparse, importlib.util, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_p = HERE / "paired_stats.py" if (HERE / "paired_stats.py").exists() else HERE.parent / "eval_mini" / "paired.py"
_spec = importlib.util.spec_from_file_location("paired_stats", _p)
stats = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(stats)

PRIMARY = {"leaderboard_mmlu_pro": ("acc", "none"), "gsm8k": ("exact_match", "flexible-extract"),
           **{t: ("acc", "none") for t in ("belebele_hin_Deva", "belebele_tel_Telu", "belebele_tam_Taml",
                                          "milu_Hindi", "milu_Telugu", "milu_Tamil", "milu_Bengali")},
           "humaneval_plus": ("plus", "none"), "mbpp_plus": ("plus", "none")}


def load(fmt_dir: Path) -> dict[str, dict]:
    out = {}
    for task, (metric, filt) in PRIMARY.items():
        f = fmt_dir / f"{task}.samples.jsonl"
        if f.exists():
            rows = [json.loads(line) for line in open(f)]
            out[task] = {r["doc_id"]: float(r[metric]) for r in rows if r.get("filter", "none") == filt}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", type=Path)
    ap.add_argument("--base", default="bf16")
    ap.add_argument("--out", type=Path, help="also write the markdown table here")
    args = ap.parse_args()

    base = load(args.runs / args.base)
    lines = [f"Paired against **{args.base}** on the same items. Differences in points (format minus base); "
             "b = right in base, wrong in format; c = the reverse.", "",
             "| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |",
             "|---|---|---|---|---|---|---|---|"]
    for fmt_dir in sorted(p for p in args.runs.iterdir() if p.is_dir() and p.name != args.base):
        other = load(fmt_dir)
        for task in PRIMARY:
            if task not in base or task not in other:
                continue
            r = stats.compare(base[task], other[task], binary=True)
            if not r["n"]:
                continue
            pts = lambda v: f"{100 * v:+.1f}"
            warn = f" ({r['missing']} items unmatched)" if r["missing"] else ""
            lines.append(f"| {fmt_dir.name} | {task}{warn} | {r['n']} | {100 * r['base']:.1f} | {100 * r['fmt']:.1f} | "
                         f"{pts(r['diff'])} ({pts(r['lo'])} to {pts(r['hi'])}) | {r['b']} / {r['c']} | {r['p']:.3f} |")
    text = "\n".join(lines)
    print(text)
    if args.out:
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
