"""Forgetting check: compare the report of the untrained base with the report of the SFT model.

Run: python forgetting.py --before base.json --after sft.json --out forgetting.md [--out-json forgetting.json]

Both files are written by `bench/evaluate.py` (schema "g10-bench-eval/1") on the same backend:
  forgetting   bits per byte on G5 held-out v1 (key "bpb_all", per group in "groups")
  eval_mini    the two short benchmarks (ARC-Challenge, HellaSwag): "records" with value and stderr
This script runs no model and reads nothing else. It refuses to compare two reports that did not measure the
same thing (other held-out file, other tokenizer, other benchmark list, an eval-mini run that failed), because a
before/after table over different inputs shows nothing.

Verdict (the limits are arguments, the defaults are the ones in eval_v1.md):
  bits per byte   up by more than `--max-bpb-rise` (0.05) over the base               -> forgetting
  a benchmark     down by more than `--sigmas` (2) times its combined stderr, and down
                  by at least `--min-drop` (0.01) in absolute value                    -> forgetting

The limits only set the verdict line. Every number is printed, and a result within `--at-limit-margin` (0.01) of
its limit, on either side, is marked "at the limit": the verdict there is a coin flip, read the numbers.

If a report's `eval_mini` block names the dtype it ran in (`"dtype": "float32"` or `"bfloat16"`, as `evaluate.py --eval-mini` writes it
and as Team 9's rows record it), it must equal that report's `compute_dtype`: benchmark rows and bits per byte have to be scored the same way.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

SCHEMA = "g10-bench-eval/1"
TASKS = ("arc_challenge", "hellaswag")


MARK = " (at the limit)"


class ReportError(ValueError):
    """The two reports cannot be compared, or one of them is not usable."""


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def load_report(path: str | Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ReportError(f"{path}: cannot read as JSON ({e})") from e
    if not isinstance(data, dict):
        raise ReportError(f"{path}: not a JSON object")
    return data


def merge_reports(*reports: dict) -> dict:
    """`evaluate.py` writes forgetting and eval-mini to separate files; merge them into one report."""
    out: dict = {}
    for r in reports:
        for k, v in r.items():
            if k in ("forgetting", "eval_mini") and k in out and out[k] != v:
                raise ReportError(f"two reports both hold '{k}' with different content")
            out.setdefault(k, v)
    return out


def _forgetting(report: dict, label: str) -> dict:
    f = report.get("forgetting")
    if not isinstance(f, dict) or not _num(f.get("bpb_all")):
        raise ReportError(f"{label}: no forgetting.bpb_all (run evaluate.py with --metrics forget)")
    if not f.get("heldout_sha256"):
        raise ReportError(f"{label}: forgetting has no heldout_sha256")
    return f


def _groups(f: dict) -> dict[str, float]:
    """Group name -> bits per byte. Accepts numbers, or dicts holding one number under 'bpb'."""
    out: dict[str, float] = {}
    for name, v in (f.get("groups") or {}).items():
        if isinstance(v, dict):
            v = v.get("bpb")
        if _num(v):
            out[str(name)] = float(v)
    return out


def _records(report: dict, label: str) -> dict[str, dict]:
    m = report.get("eval_mini")
    if not isinstance(m, dict):
        raise ReportError(f"{label}: no eval_mini (run evaluate.py --eval-mini)")
    if m.get("returncode") not in (0, None) or "error_tail" in m or not m.get("records"):
        raise ReportError(f"{label}: eval-mini failed or returned no records: {m.get('error_tail') or m.get('returncode')}")
    out: dict[str, dict] = {}
    for r in m["records"]:
        task = r.get("task")
        if task in out:
            raise ReportError(f"{label}: task {task} appears twice in eval_mini.records")
        if not _num(r.get("value")):
            raise ReportError(f"{label}: task {task} has no numeric value")
        if not (0.0 <= r["value"] <= 1.0):
            raise ReportError(
                f"{label}: task {task} value {r['value']} is outside [0, 1] "
                "(pass fractions 0..1, not points 0..100)"
            )
        se = r.get("stderr")
        if se is not None and (not _num(se) or not (0.0 <= se <= 1.0)):
            raise ReportError(
                f"{label}: task {task} stderr {se} is outside [0, 1] "
                "(pass fractions 0..1, not points 0..100)"
            )
        out[task] = r
    missing = [t for t in TASKS if t not in out]
    if missing:
        raise ReportError(f"{label}: eval_mini is missing {', '.join(missing)}")
    return out


_DTYPES = {"float32": "float32", "fp32": "float32", "bfloat16": "bfloat16", "bf16": "bfloat16"}


def _dtype_of(label: str, where: str) -> str:
    """'float32 (TF32 off)' or 'bf16' -> 'float32' or 'bfloat16'. Anything else is refused, not guessed."""
    key = str(label).split(" ")[0].lower()
    if key not in _DTYPES:
        raise ReportError(f"{where}: dtype {label!r} is not float32 or bfloat16")
    return _DTYPES[key]


def _check_benchmark_dtype(report: dict, label: str) -> None:
    """Benchmark rows and bits per byte must be scored in the same dtype (Team 9's watcher uses bf16 on bf16 GPUs, fp32 elsewhere).

    Only when the eval_mini block says which dtype it ran in (`dtype`, as Team 9's v1 rows do); older reports do not, and
    nothing is checked for them.
    """
    mini = report.get("eval_mini")
    if not isinstance(mini, dict) or mini.get("dtype") is None:
        return
    bench, bpb = _dtype_of(mini["dtype"], f"{label} eval_mini"), _dtype_of(report.get("compute_dtype", ""), f"{label} compute_dtype")
    if bench != bpb:
        raise ReportError(f"{label}: the benchmark rows were scored in {bench} but the bits per byte in {bpb}; "
                          "score both in the same dtype")


def _near(value: float, limit: float, margin: float) -> bool:
    """True when `value` is within `margin` of `limit` (a tiny slack keeps 0.06 - 0.05 inside a 0.01 margin)."""
    return abs(value - limit) <= margin + 1e-9


def compare(before: dict, after: dict, *, max_bpb_rise: float = 0.05, sigmas: float = 2.0, min_drop: float = 0.01,
            at_limit_margin: float = 0.01) -> dict:
    fb, fa = _forgetting(before, "before"), _forgetting(after, "after")
    if fb["heldout_sha256"] != fa["heldout_sha256"]:
        raise ReportError("before and after used different held-out files (heldout_sha256 differs)")
    for key in ("window",):
        if fb.get(key) != fa.get(key):
            raise ReportError(f"before and after used a different {key}: {fb.get(key)} vs {fa.get(key)}")
    # The tokenizer must be the same file, or bits per byte are not comparable token-wise.
    tb, ta = before.get("tokenizer_sha256"), after.get("tokenizer_sha256")
    if tb and ta and tb != ta:
        raise ReportError("before and after used different tokenizers")
    for key in ("device", "compute_dtype"):
        if before.get(key) != after.get(key):
            raise ReportError(f"before and after ran on a different {key}: {before.get(key)} vs {after.get(key)}")
    _check_benchmark_dtype(before, "before")
    _check_benchmark_dtype(after, "after")

    delta = fa["bpb_all"] - fb["bpb_all"]
    gb, ga = _groups(fb), _groups(fa)
    groups = {g: {"before": gb[g], "after": ga[g], "delta": ga[g] - gb[g]} for g in sorted(gb) if g in ga}

    rb, ra = _records(before, "before"), _records(after, "after")
    bench: dict[str, dict] = {}
    for t in TASKS:
        b, a = rb[t], ra[t]
        for key in ("metric", "n_items", "num_fewshot", "filter"):
            if b.get(key) != a.get(key):
                raise ReportError(f"{t}: before and after differ in {key}: {b.get(key)} vs {a.get(key)}")
        se = None
        if _num(b.get("stderr")) and _num(a.get("stderr")):
            se = math.hypot(b["stderr"], a["stderr"])
        d = a["value"] - b["value"]
        drop = -d
        # Without both stderr values a drop cannot be called significant: report it and flag it as unproven.
        significant = bool(se is not None and drop >= min_drop and drop > sigmas * se)
        # The drop must beat both the stderr bar and the absolute floor; "at the limit" is near the higher of the two.
        bar = max(min_drop, sigmas * se) if se is not None else None
        at_limit = bool(bar is not None and _near(drop, bar, at_limit_margin))
        bench[t] = {"metric": b.get("metric"), "n_items": b.get("n_items"), "before": b["value"], "after": a["value"],
                    "delta": d, "stderr_combined": se, "significant_drop": significant, "no_stderr": se is None,
                    "at_limit": at_limit}

    forgot_bpb = delta > max_bpb_rise
    bpb_at_limit = _near(delta, max_bpb_rise, at_limit_margin)
    forgot = [t for t, r in bench.items() if r["significant_drop"]]
    return {
        "bpb": {"before": fb["bpb_all"], "after": fa["bpb_all"], "delta": delta, "limit": max_bpb_rise,
                "rose_too_much": forgot_bpb, "at_limit": bpb_at_limit, "heldout_sha256": fb["heldout_sha256"], "groups": groups},
        "benchmarks": bench,
        "limits": {"max_bpb_rise": max_bpb_rise, "sigmas": sigmas, "min_drop": min_drop,
                   "at_limit_margin": at_limit_margin},
        "forgetting": bool(forgot_bpb or forgot),
        "reasons": ([f"held-out bits per byte rose by {delta:+.4f} (limit {max_bpb_rise})"] if forgot_bpb else [])
        + [f"{t} fell by {-bench[t]['delta']:.4f} (more than {sigmas} x stderr {bench[t]['stderr_combined']:.4f})" for t in forgot],
    }


def render_markdown(result: dict) -> str:
    b = result["bpb"]
    lines = [
        "| Measure | Base | After SFT | Change |", "|---|---|---|---|",
        f"| Held-out bits per byte (G5 held-out v1, all) | {b['before']:.4f} | {b['after']:.4f} | {b['delta']:+.4f}{MARK if b['at_limit'] else ''} |",
    ]
    for g, r in b["groups"].items():
        lines.append(f"| bits per byte, group {g} | {r['before']:.4f} | {r['after']:.4f} | {r['delta']:+.4f} |")
    for t, r in result["benchmarks"].items():
        se = "no stderr" if r["no_stderr"] else f"stderr {r['stderr_combined']:.4f}"
        lines.append(f"| {t} {r['metric']} (n={r['n_items']}) | {r['before']:.4f} | {r['after']:.4f} | {r['delta']:+.4f} ({se}){MARK if r['at_limit'] else ''} |")
    verdict = "FORGETTING: " + "; ".join(result["reasons"]) if result["forgetting"] else "No forgetting beyond the limits."
    lim = result["limits"]
    near = [n for n, v in [("bits per byte", b["at_limit"])] + [(t, r["at_limit"]) for t, r in result["benchmarks"].items()] if v]
    lines += ["", f"Verdict: {verdict}",
              f"Limits: bits per byte may rise by at most {lim['max_bpb_rise']}; a benchmark may fall by at most "
              f"{lim['sigmas']} x its combined stderr (and {lim['min_drop']} absolute).",
              f"Held-out file sha256: {b['heldout_sha256']}"]
    if near:
        lines.append(f"At the limit (within {lim['at_limit_margin']} of it, either side; the verdict is a close call, read the numbers): "
                     + ", ".join(near) + ".")
    if any(r["no_stderr"] for r in result["benchmarks"].values()):
        lines.append("Note: a benchmark without stderr is never called a significant drop; read its change by hand.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before", nargs="+", required=True, help="report(s) of the untrained base (merged if several)")
    ap.add_argument("--after", nargs="+", required=True, help="report(s) of the SFT model (merged if several)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-json")
    ap.add_argument("--max-bpb-rise", type=float, default=0.05)
    ap.add_argument("--sigmas", type=float, default=2.0)
    ap.add_argument("--min-drop", type=float, default=0.01)
    ap.add_argument("--at-limit-margin", type=float, default=0.01,
                    help="mark a result within this distance of its limit as 'at the limit' (verdict unchanged)")
    args = ap.parse_args(argv)
    try:
        before = merge_reports(*[load_report(p) for p in args.before])
        after = merge_reports(*[load_report(p) for p in args.after])
        result = compare(before, after, max_bpb_rise=args.max_bpb_rise, sigmas=args.sigmas, min_drop=args.min_drop,
                         at_limit_margin=args.at_limit_margin)
    except ReportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    text = render_markdown(result)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text, encoding="utf-8")
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    print(text, end="")
    return 1 if result["forgetting"] else 0


if __name__ == "__main__":
    sys.exit(main())
