#!/usr/bin/env python3
"""Paired comparison of each format with bf16 on the wide pass, item by item.

    python paired.py runs/ --base bf16 [--out paired.md]

Reads runs/<format>/<task>.samples.jsonl (written by run_wide_gguf.py). Statistics are those of
../eval_mini/paired.py (difference, 95% CI from the paired variance, McNemar's exact test); every task is 0/1 per
item. The English tasks (mmlu, arc_challenge) and the Indic ones (MILU) sit in one table to compare their drops.
"""
from __future__ import annotations

import argparse, importlib.util, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_p = HERE / "paired_stats.py" if (HERE / "paired_stats.py").exists() else HERE.parent / "eval_mini" / "paired.py"
_spec = importlib.util.spec_from_file_location("paired_stats", _p)
stats = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(stats)

PRIMARY = {"mmlu": "acc", "arc_challenge": "acc_norm", "milu_Kannada": "acc", "milu_Hindi": "acc",
           "milu_Telugu": "acc", "milu_Tamil": "acc", "milu_Bengali": "acc",
           **{f"belebele_{lang}": "acc" for lang in ("kan_Knda", "hin_Deva", "tel_Telu", "tam_Taml", "ben_Beng")}}


def load(fmt_dir: Path) -> dict[str, dict]:
    out = {}
    for task, metric in PRIMARY.items():
        f = fmt_dir / f"{task}.samples.jsonl"
        if f.exists():
            out[task] = {r["doc_id"]: float(r[metric]) for r in map(json.loads, open(f)) if metric in r}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", type=Path)
    ap.add_argument("--base", default="bf16")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    base = load(args.runs / args.base)
    lines = [f"Paired against **{args.base}** on the same items. Differences in points (format minus base); "
             "b = right in base, wrong in format; c = the reverse.", "",
             "| Format | Task | n | Base | Format | Difference (95% CI) | b / c | McNemar p |",
             "|---|---|---|---|---|---|---|---|"]
    pts = lambda v: f"{100 * v:+.1f}"
    for fmt_dir in sorted(p for p in args.runs.iterdir() if p.is_dir() and p.name != args.base):
        other = load(fmt_dir)
        for task in PRIMARY:
            if task not in base or task not in other:
                continue
            r = stats.compare(base[task], other[task], binary=True)
            if not r["n"]:
                continue
            warn = f" ({r['missing']} items unmatched)" if r["missing"] else ""
            lines.append(f"| {fmt_dir.name} | {task}{warn} | {r['n']} | {100 * r['base']:.1f} | {100 * r['fmt']:.1f} | "
                         f"{pts(r['diff'])} ({pts(r['lo'])} to {pts(r['hi'])}) | {r['b']} / {r['c']} | {r['p']:.3f} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        args.out.write_text(text)


if __name__ == "__main__":
    main()
