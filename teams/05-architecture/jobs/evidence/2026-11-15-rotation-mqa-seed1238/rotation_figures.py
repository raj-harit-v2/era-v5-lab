#!/usr/bin/env python3
"""Draw the three figures of experiments/rotation_yasirreshi.md.

Inputs: rotation-comparison.csv and rotation-slice-scores.csv (written by compare_rotation.py), this run's
metrics.jsonl, and the screen's attn-0 and attn-1 metrics.jsonl. Outputs, next to this script:
rotation-scores.svg, rotation-gap.svg and rotation-slices.svg. Every number drawn is read from those files.
Colours follow the light/dark chart palette (blue = MQA seed 1235, orange = MQA seed 1238; both pass the
colour-vision checks); each SVG switches to its dark steps under prefers-color-scheme: dark. Hovering a mark
shows its value (SVG <title>). Standard library only.

usage: python rotation_figures.py [--screen DIR]    (default: ../2026-11-10-attention-screen)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SANS = "system-ui, -apple-system, 'Segoe UI', sans-serif"
STYLE = """<style>
.bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.t3{fill:#898781}
.grid{stroke:#e1e0d9}.axis{stroke:#c3c2b7}.ref{stroke:#52514e}
.s1{stroke:#2a78d6}.f1{fill:#2a78d6}.s2{stroke:#eb6834}.f2{fill:#eb6834}.ring{stroke:#fcfcfb}
@media (prefers-color-scheme: dark){
.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}
.grid{stroke:#2c2c2a}.axis{stroke:#383835}.ref{stroke:#c3c2b7}
.s1{stroke:#3987e5}.f1{fill:#3987e5}.s2{stroke:#d95926}.f2{fill:#d95926}.ring{stroke:#1a1a19}
}
</style>"""
W = 880
SEED_A, SEED_B = "MQA, seed 1235 (screen)", "MQA, seed 1238 (this run)"
GROUPS = [("Three-group", "three-group BPB"), ("Code", "code BPB"), ("Indic (mean of 11)", "Indic BPB"),
          ("English", "English BPB")]
NAMES = {"as": "Assamese", "bn": "Bengali", "gu": "Gujarati", "hi": "Hindi", "kn": "Kannada", "ml": "Malayalam",
         "mr": "Marathi", "or": "Odia", "pa": "Punjabi", "ta": "Tamil", "te": "Telugu", "en": "English",
         "code": "Code", "math": "Math", "sci": "Science"}
INDIC = ["as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te"]
GAP_FROM = 200   # the gap figure starts here: evaluations at steps 0-150 swing far more
WINDOW_FROM = 600  # the gap range quoted in the report covers evaluations from this step on


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def signed(v: float, nd: int = 4) -> str:
    return f"{v:+.{nd}f}".replace("-", "−")


def text(x, y, s, cls="t1", size=13, anchor="start", weight=400) -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-family="{SANS}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>')


def line(x1, y1, x2, y2, cls="grid", width=1.0, dash=None) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}" '
            f'stroke-width="{width}"{d}/>')


def polyline(points, cls) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" class="{cls}" stroke-width="2" stroke-linejoin="round"/>'


def dot(x, y, cls, tip, r=4.5) -> str:
    return (f'<g><title>{esc(tip)}</title><circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 7}" fill="transparent"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="{cls} ring" stroke-width="2"/></g>')


def svg(h, title, body: list[str]) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h:.0f}" viewBox="0 0 {W} {h:.0f}" '
            f'role="img" aria-label="{esc(title)}">\n<title>{esc(title)}</title>\n{STYLE}\n'
            f'<rect width="{W}" height="{h:.0f}" rx="10" class="bg"/>\n' + "\n".join(body) + "\n</svg>\n")


def header(title: str, subtitle: str) -> list[str]:
    return [text(24, 34, title, size=16, weight=600), text(24, 56, subtitle, "t2", 13)]


def legend(y: float) -> list[str]:
    out, x = [], 24
    for cls, name in (("f1", SEED_A), ("f2", SEED_B)):
        out += [f'<circle cx="{x + 5}" cy="{y - 4}" r="5" class="{cls}"/>', text(x + 15, y, name, "t2", 12)]
        x += 15 + 6.6 * len(name) + 26
    out += [line(x, y - 4, x + 18, y - 4, "ref", 1.5), text(x + 24, y, "reference, seed 1235 (zero)", "t2", 12)]
    return out


def domain(values: list[float], step: float) -> tuple[float, float]:
    lo, hi = min(values + [0.0]), max(values + [0.0])
    return math.floor((lo - step / 4) / step) * step, math.ceil((hi + step / 4) / step) * step


def ticks(lo: float, hi: float, step: float) -> list[float]:
    return [lo + i * step for i in range(round((hi - lo) / step) + 1)]


def dotplot(title, subtitle, rows, step, row_h, footer, nd_tick) -> str:
    """rows: ("group", name) separators or (label, sublabel, a, b, right_text). Values are differences."""
    x0, x1, rx, top = 210, 650, 676, 120
    vals = [v for r in rows if r[0] != "group" for v in (r[2], r[3])]
    lo, hi = domain(vals, step)

    def X(v: float) -> float:
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    ys, y = [], top
    for r in rows:
        if r[0] == "group":
            ys.append(y + 14)
            y += 24
        else:
            ys.append(y + row_h / 2)
            y += row_h
    bottom = y
    b = header(title, subtitle) + legend(84)
    b += [text(X(lo) + 2, top - 8, "← MQA lower (better)", "t3", 11),
          text(X(hi) - 2, top - 8, "MQA higher (worse) →", "t3", 11, "end")]
    for t in ticks(lo, hi, step):
        if abs(t) > step / 1000:
            b.append(line(X(t), top, X(t), bottom, "grid"))
        b.append(text(X(t), bottom + 18, signed(t, nd_tick) if abs(t) > step / 1000 else "0", "t3", 11, "middle"))
    b.append(text((x0 + x1) / 2, bottom + 38, "BPB minus the reference (lower is better)", "t2", 12, "middle"))
    for r, yc in zip(rows, ys):
        if r[0] == "group":
            b += [text(24, yc + 4, r[1], "t3", 11, weight=600), line(24 + 7 * len(r[1]) + 10, yc, x1, yc, "grid")]
            continue
        label, sub, a, bb, right = r
        b.append(line(x0, yc, x1, yc, "grid"))
        b.append(text(24, yc + (0 if sub else 4), label, "t1", 13))
        if sub:
            b.append(text(24, yc + 16, sub, "t3", 11))
        b.append(line(X(a), yc, X(bb), yc, "axis", 2))
        b.append(dot(X(a), yc, "f1", f"{label}, {SEED_A}: {signed(a)} BPB against the reference"))
        b.append(dot(X(bb), yc, "f2", f"{label}, {SEED_B}: {signed(bb)} BPB against the reference"))
        for k, (cls, s) in enumerate(right):
            yy = yc + (4 if len(right) == 1 else (-4 if k == 0 else 13))
            if cls:
                b.append(f'<circle cx="{rx + 4}" cy="{yy - 4}" r="4" class="{cls}"/>')
            b.append(text(rx + (14 if cls else 0), yy, s, "t2", 12))
    b.append(line(X(0), top, X(0), bottom, "ref", 1.5))
    fy = bottom + 64
    for k, s in enumerate(footer):
        b.append(text(24, fy + 18 * k, s, "t3", 11))
    return svg(fy + 18 * len(footer) + 6, title, b)


def fig_scores(ref: dict, a: dict, b: dict) -> str:
    rows = []
    for label, col in GROUPS:
        da, db = a[col] - ref[col], b[col] - ref[col]
        rows.append((label, f"reference {ref[col]:.4f}", da, db,
                     [("f1", f"seed 1235  {signed(da)}"), ("f2", f"seed 1238  {signed(db)}")]))
    short = {"Three-group": "three-group", "Code": "code", "Indic (mean of 11)": "Indic", "English": "English"}
    lower = [short[label] for label, col in GROUPS if a[col] < ref[col] and b[col] < ref[col]]
    return dotplot(
        f"At both seeds MQA is below the reference on {', '.join(lower[:-1])} and {lower[-1]}",
        "Held-out BPB at step 1,221, minus the reference (seed 1235). The grey line joins the two MQA seeds.",
        rows, 0.002, 58,
        ["The reference has one seed, so its own seed-to-seed spread is unknown. Hover a dot for its value."], 3)


def fig_slices(slices: list[dict]) -> tuple[str, str]:
    rows: list = [("group", "Indic slices")]
    gaps = {}
    for s in slices:
        x = s["slice"]
        if x == "en":
            rows.append(("group", "Other slices"))
        ref = float(s["reference seed 1235"])
        da, db = float(s["MQA seed 1235"]) - ref, float(s["MQA seed 1238"]) - ref
        gaps[x] = db - da
        rows.append((f"{x} · {NAMES[x]}", "", da, db, [("", f"seed gap {signed(db - da, 3)}")]))
    worst = max(gaps, key=lambda k: abs(gaps[k]))
    tokens = [int(s["scored tokens"]) for s in slices]
    title = f"Single slices move by up to {abs(gaps[worst]):.2f} BPB between the two MQA seeds"
    return dotplot(
        title,
        "Each slice's held-out BPB at step 1,221, minus the reference (seed 1235). Seed gap = seed 1238 minus seed 1235.",
        rows, 0.02, 27,
        [f"Each slice scores {min(tokens):,} to {max(tokens):,} held-out tokens, so one seed is a noisy reading "
         "of a single slice.", "Hover a dot for its value."], 2), worst


def evals(path: Path) -> dict[int, float]:
    out = {}
    for line_ in path.read_text(encoding="utf-8").splitlines():
        if line_.strip():
            r = json.loads(line_)
            if "val/three_group_bpb" in r:
                out[r["step"]] = r["val/three_group_bpb"]
    return out


def fig_gap(ref: dict, a: dict, b: dict) -> tuple[str, float, float]:
    steps = [s for s in sorted(set(ref) & set(a) & set(b)) if s >= GAP_FROM]
    da = {s: a[s] - ref[s] for s in steps}
    db = {s: b[s] - ref[s] for s in steps}
    window = [v for s in steps if s >= WINDOW_FROM for v in (da[s], db[s])]
    wlo, whi = min(window), max(window)
    x0, x1, y0, y1 = 86, 690, 104, 352
    lo, hi = domain(list(da.values()) + list(db.values()), 0.005)

    def X(s: float) -> float:
        return x0 + (s - steps[0]) / (steps[-1] - steps[0]) * (x1 - x0)

    def Y(v: float) -> float:
        return y0 + (hi - v) / (hi - lo) * (y1 - y0)

    title = f"From step {WINDOW_FROM} on, the gap swings from {signed(wlo)} to {signed(whi)} across evaluations"
    body = header(title, "Three-group held-out BPB of MQA minus the reference (seed 1235), at each evaluation "
                         f"(every 50 steps) from step {GAP_FROM}.") + legend(84)
    for t in ticks(lo, hi, 0.005):
        body.append(line(x0, Y(t), x1, Y(t), "grid"))
        body.append(text(x0 - 8, Y(t) + 4, signed(t, 3) if abs(t) > 1e-9 else "0", "t3", 11, "end"))
    body.append(line(x0, Y(0), x1, Y(0), "ref", 1.5))
    body.append(f'<rect x="{X(WINDOW_FROM):.1f}" y="{Y(whi):.1f}" width="{X(steps[-1]) - X(WINDOW_FROM):.1f}" '
                f'height="{Y(wlo) - Y(whi):.1f}" fill="#898781" fill-opacity=".10"><title>range from step '
                f'{WINDOW_FROM}: {signed(wlo)} to {signed(whi)}</title></rect>')
    for s in [t for t in range(GAP_FROM, steps[-1] + 1, 200)]:
        body.append(text(X(s), y1 + 20, f"{s:,}", "t3", 11, "middle"))
    body.append(text((x0 + x1) / 2, y1 + 42, "training step", "t2", 12, "middle"))
    ends = []
    for cls_s, cls_f, name, d in (("s1", "f1", SEED_A, da), ("s2", "f2", SEED_B, db)):
        body.append(polyline([(X(s), Y(d[s])) for s in steps], cls_s))
        body += [dot(X(s), Y(d[s]), cls_f, f"{name}, step {s:,}: {signed(d[s])}", r=4) for s in steps]
        ends.append([Y(d[steps[-1]]), cls_f, f"seed {name.split('seed ')[1][:4]}  {signed(d[steps[-1]])}"])
    if abs(ends[0][0] - ends[1][0]) < 16:  # keep the two end labels apart
        mid = (ends[0][0] + ends[1][0]) / 2
        ends.sort(key=lambda e: e[0])
        ends[0][0], ends[1][0] = mid - 8, mid + 8
    for yy, cls, s in ends:
        body += [f'<circle cx="{x1 + 18}" cy="{yy:.1f}" r="4" class="{cls}"/>', text(x1 + 28, yy + 4, s, "t2", 12)]
    body.append(text(24, y1 + 74, f"Shaded: the range of both gaps from step {WINDOW_FROM} on. Evaluations at "
                                  f"steps 0 to {GAP_FROM - 50} swing more and are left out. Hover a dot for its value.",
                     "t3", 11))
    return svg(y1 + 92, title, body), wlo, whi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", type=Path, default=HERE.parent / "2026-11-10-attention-screen")
    args = ap.parse_args()
    with open(HERE / "rotation-comparison.csv", encoding="utf-8", newline="") as f:
        comp = list(csv.DictReader(f))
    with open(HERE / "rotation-slice-scores.csv", encoding="utf-8", newline="") as f:
        slices = list(csv.DictReader(f))
    pick = {(r["design"], r["seed"]): {k: float(r[k]) for _, k in GROUPS} for r in comp}
    ref, a, b = pick[("attn-0", "1235")], pick[("attn-1", "1235")], pick[("attn-1", "1238")]
    gap_svg, wlo, whi = fig_gap(evals(args.screen / "attn-0" / "metrics.jsonl"),
                                evals(args.screen / "attn-1" / "metrics.jsonl"), evals(HERE / "metrics.jsonl"))
    slice_svg, worst = fig_slices(slices)
    for name, content in (("rotation-scores.svg", fig_scores(ref, a, b)), ("rotation-gap.svg", gap_svg),
                          ("rotation-slices.svg", slice_svg)):
        (HERE / name).write_text(content, encoding="utf-8", newline="\n")
        print("wrote", name)
    print(f"gap from step {WINDOW_FROM}: {wlo:+.4f} to {whi:+.4f}; largest slice seed gap: {worst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
