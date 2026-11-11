#!/usr/bin/env python3
"""Draw the figures of determinism_gpu.md from the committed GPU results.

Inputs (all under ``results/decode_gpu/``): ``raw_P32.json`` (decode_gpu.py), ``gemm_accuracy_P32.json``
(gemm_accuracy_gpu.py) and ``resources_raw_P32.csv`` (resource_monitor.py). Outputs: four SVGs in ``docs/figures/``.
Every number drawn is read from those files. Colours follow the light/dark chart palette; each SVG switches to
its dark steps under ``prefers-color-scheme: dark``. Hovering a mark shows its value (SVG ``<title>``).

    python teams/04-ke2/src/docs/determinism_gpu_figures.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a script: make the ke2 package importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ke2.config import RESULTS_DIR, TEAM_DIR

RUNS = 3
"""Fresh GPU processes per batch size (decode_gpu.RUNS)."""
GPU_DIR = RESULTS_DIR / "decode_gpu"
OUT = TEAM_DIR / "docs" / "figures"
SANS = "system-ui, -apple-system, 'Segoe UI', sans-serif"
MONO = "Consolas, Menlo, 'DejaVu Sans Mono', monospace"
STYLE = """<style>
.bg{fill:#fcfcfb}.card{fill:#fcfcfb;stroke:#0b0b0b;stroke-opacity:.12}
.t1{fill:#0b0b0b}.t2{fill:#52514e}.t3{fill:#898781}
.grid{stroke:#e1e0d9}.axis{stroke:#c3c2b7}.ref{stroke:#52514e}
.s1{stroke:#2a78d6}.f1{fill:#2a78d6}.s2{stroke:#eb6834}.f2{fill:#eb6834}.s3{stroke:#1baf7a}.f3{fill:#1baf7a}
.ok{fill:#0ca30c}.bad{fill:#d03b3b}.band{fill:#0b0b0b;fill-opacity:.04}.ring{stroke:#fcfcfb}.icon{stroke:#ffffff}
@media (prefers-color-scheme: dark){
.bg{fill:#1a1a19}.card{fill:#1a1a19;stroke:#ffffff;stroke-opacity:.14}
.t1{fill:#f0efec}.t2{fill:#c3c2b7}
.grid{stroke:#2c2c2a}.axis{stroke:#383835}.ref{stroke:#c3c2b7}
.s1{stroke:#3987e5}.f1{fill:#3987e5}.s2{stroke:#d95926}.f2{fill:#d95926}.s3{stroke:#199e70}.f3{fill:#199e70}
.band{fill:#ffffff;fill-opacity:.06}.ring{stroke:#1a1a19}
}
</style>"""
SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, cls="t1", size=13, anchor="start", weight=400, mono=False) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-family="{MONO if mono else SANS}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>'
    )


def hline(x1, x2, y, cls="grid", dash=None) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" class="{cls}" stroke-width="1"{d}/>'


def polyline(points, cls) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" class="{cls}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'


def dot(x, y, cls, tip, r=4.5) -> str:
    return (
        f'<g><title>{esc(tip)}</title><circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 7}" fill="transparent"/>'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="{cls} ring" stroke-width="2"/></g>'
    )


def status(x, y, ok: bool) -> str:
    """Status icon: a filled circle with a tick (good) or a cross (critical); always paired with a text label."""
    mark = (
        f"M{x - 3.5:.1f},{y:.1f} l2.5,2.6 l5,-5.4"
        if ok
        else f"M{x - 3:.1f},{y - 3:.1f} l6,6 M{x + 3:.1f},{y - 3:.1f} l-6,6"
    )
    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7.5" class="{"ok" if ok else "bad"}"/>'
        f'<path d="{mark}" fill="none" class="icon" stroke-width="1.8" stroke-linecap="round"/>'
    )


def svg(w, h, title, body: list[str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="{esc(title)}">\n<title>{esc(title)}</title>\n{STYLE}\n'
        f'<rect width="{w}" height="{h}" rx="10" class="bg"/>\n' + "\n".join(body) + "\n</svg>\n"
    )


def header(title: str, subtitle: str) -> list[str]:
    return [text(24, 34, title, size=16, weight=600), text(24, 56, subtitle, "t2", 13)]


def minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f} min" if seconds >= 90 else f"{seconds:.0f} s"


# Figure 1: the verdict board -----------------------------------------------------------------------------------


def fig_verdict(report: dict) -> str:
    cpu = report["cpu_reference"]
    n = report["inputs"]["queries"]
    runs = sorted(report["runs"], key=lambda r: (r["batch_size"], r["run"]))
    sizes = sorted({r["batch_size"] for r in runs})
    W, tile_w, tile_h, gap = 880, 196, 96, 10
    gx, gy = 252, 96
    H = gy + len(sizes) * (tile_h + gap) + 70
    all_ok = report["passed"]
    b = header(
        f"{'All' if all_ok else 'Not all'} {len(runs)} GPU runs decode every token ID to the CPU reference's ID",
        f"{n:,} token IDs · raw byte table, P = {report['inputs']['pos_dim']} · fp32, TF32 off · "
        f"{len(sizes)} batch sizes × 3 fresh processes",
    )
    # CPU reference card
    ch = len(sizes) * (tile_h + gap) - gap
    b.append(f'<rect x="24" y="{gy}" width="208" height="{ch}" rx="8" class="card"/>')
    b += [
        text(40, gy + 28, "CPU reference", size=14, weight=600),
        text(40, gy + 48, "decode_ref.py · float64", "t2", 12),
        text(40, gy + 66, f"all {n:,} IDs, one fresh run", "t2", 12),
        text(40, gy + 104, "ID hash", "t3", 11),
        text(40, gy + 122, cpu["id_sha256"][:16], size=13, mono=True),
        text(40, gy + 140, cpu["id_sha256"][16:32] + "…", size=13, mono=True),
        status(47, gy + 176, all(r["comparison"]["ids_equal_cpu"] for r in runs) and cpu["rows"] == n),
        text(62, gy + 180.5, "every ID decodes to itself" if cpu["ties"] == 0 else f"{cpu['ties']} ties", size=12),
        text(40, gy + 214, f"smallest margin {cpu['min_margin']:.4f}", "t2", 12),
        text(40, gy + 232, f"{cpu['seconds'] / 60:.1f} min on {cpu['worker_processes']} CPU processes", "t3", 11),
    ]
    for i, size in enumerate(sizes):
        y = gy + i * (tile_h + gap)
        for j, r in enumerate(x for x in runs if x["batch_size"] == size):
            x = gx + j * (tile_w + gap)
            ok = r["comparison"]["ids_equal_cpu"] and r["id_sha256"] == cpu["id_sha256"]
            label = "IDs = CPU, all" if ok else f"{r['comparison']['mismatching_ids']:,} IDs differ"
            b += [
                f"<g><title>batch {size}, run {r['run']}: ID hash {r['id_sha256']}; score hash {r['score_sha256']}; "
                f"decode {r['decode_seconds']} s</title>",
                f'<rect x="{x}" y="{y}" width="{tile_w}" height="{tile_h}" rx="8" class="card"/>',
                text(x + 14, y + 22, f"batch {size:,} · run {r['run']}", "t2", 12, weight=600),
                text(x + 14, y + 42, r["id_sha256"][:16] + "…", size=13, mono=True),
                status(x + 21, y + 61, ok),
                text(x + 35, y + 65.5, label, size=12),
                text(x + 14, y + 86, f"score {r['score_sha256'][:8]} · {minutes(r['decode_seconds'])}", "t3", 11),
                "</g>",
            ]
    s = report["summary"]
    within = all(s[str(k)]["three_score_hashes_match"] for k in sizes)
    across = s["all_batch_sizes"]["distinct_score_hashes"]
    fy = gy + len(sizes) * (tile_h + gap) + 14
    b += [
        text(
            24,
            fy + 6,
            "Same ID hash in every tile and in the CPU card: the decoded IDs are exact and repeat bit for bit.",
            size=13,
        ),
        text(
            24,
            fy + 28,
            f"Score hashes (fp32 cosine and margin) {'repeat' if within else 'do not repeat'} within each batch size and "
            f"take {across} values across the {len(sizes)} sizes: cuBLAS uses a different kernel for each shape.",
            "t2",
            12,
        ),
    ]
    return svg(W, H, "GPU decode determinism: verdict for every run", b)


# Figure 2: precision against batch size ------------------------------------------------------------------------


def fig_precision(report: dict, gemm: dict) -> str:
    W, H = 880, 472
    x0, x1, y0, y1 = 96, 700, 92, 380
    lo, hi = -6, -1
    off, on = gemm["cublas_matmul"]["tf32_off"], gemm["cublas_matmul"]["tf32_on"]
    sizes = [int(k) for k in off]
    xs = {s: x0 + i * (x1 - x0) / (len(sizes) - 1) for i, s in enumerate(sizes)}

    def y(v: float) -> float:
        return y0 + (hi - math.log10(max(v, 10.0**lo))) / (hi - lo) * (y1 - y0)

    margin = report["cpu_reference"]["min_margin"]
    run_err = {int(k): v["max_abs_margin_difference"] for k, v in report["summary"].items() if k.isdigit()}
    b = header(
        f"fp32 error grows with batch size; the worst margin error is still {margin / max(run_err.values()):,.0f}× "
        "smaller than the smallest margin",
        "Largest absolute error against float64, log scale. An ID can change only if an error reaches the dashed line.",
    )
    for e in range(lo, hi + 1):
        b += [
            hline(x0, x1, y(10.0**e), "axis" if e == lo else "grid"),
            text(x0 - 10, y(10.0**e) + 4, f"10{str(e).translate(SUPERSCRIPT)}", "t3", 12, "end"),
        ]
    for s in sizes:
        b.append(text(xs[s], y1 + 22, f"{s:,}", "t3", 12, "middle"))
    b.append(text((x0 + x1) / 2, y1 + 44, "queries per batch (batch size)", "t2", 12, "middle"))
    # threshold: the smallest margin in the vocabulary
    b += [
        hline(x0, x1, y(margin), "ref", dash="6 4"),
        text(
            x0 + 6,
            y(margin) - 8,
            f"smallest decode margin, all {report['inputs']['queries']:,} IDs: {margin:.4f}",
            "t2",
            12,
        ),
    ]
    series = [
        ("s1", "f1", "cuBLAS, TF32 off (as run)", off),
        ("s2", "f2", "cuBLAS, TF32 on (for contrast)", on),
    ]
    for scls, fcls, name, data in series:
        pts = [(xs[s], y(data[str(s)]["max_abs_error"])) for s in sizes]
        b.append(polyline(pts, scls))
        b += [
            dot(px, py, fcls, f"{name}, batch {s:,}: {data[str(s)]['max_abs_error']:.2e}")
            for (px, py), s in zip(pts, sizes, strict=True)
        ]
        b.append(
            text(
                x1 + 14, pts[-1][1] + 4, f"{name.split(' (')[0]}  {data[str(sizes[-1])]['max_abs_error']:.1e}", "t1", 12
            )
        )
    for s, v in sorted(run_err.items()):
        if s in xs:
            b.append(dot(xs[s], y(v), "f3", f"full run, largest margin error vs CPU, batch {s:,}: {v:.2e}", r=5))
    last = max(s for s in run_err if s in xs)
    b.append(text(x1 + 14, y(run_err[last]) + 4, f"full run margins  {run_err[last]:.1e}", "t1", 12))
    ctrl = gemm["control_elementwise_sum_tf32_off"]["max_abs_error"]
    # legend
    lx = 96
    for cls, name in (
        ("f1", "scores, TF32 off (as run)"),
        ("f2", "scores, TF32 on"),
        ("f3", "full run: margin error vs CPU float64"),
    ):
        b += [f'<circle cx="{lx + 5}" cy="76" r="5" class="{cls}"/>', text(lx + 15, 80, name, "t2", 12)]
        lx += 15 + 7.1 * len(name) + 22
    b.append(
        text(
            24,
            H - 14,
            f"Control: the same fp32 products summed as a reduction tree (no cuBLAS) err by {ctrl:.1e}. "
            "The GEMM error is rounding drift over 8,192 dense coordinates, not TF32.",
            "t3",
            11,
        )
    )
    return svg(W, H, "Score precision against batch size", b)


# Figure 3: speed per batch size --------------------------------------------------------------------------------


def fig_speed(report: dict) -> str:
    runs = report["runs"]
    sizes = sorted({r["batch_size"] for r in runs})
    V, n = report["inputs"]["vocabulary_size"], report["inputs"]["queries"]
    D = 256 * report["inputs"]["pos_dim"]
    W, row = 880, 74
    x0, x1, y0 = 120, 720, 92
    H = y0 + row * len(sizes) + 44
    mean = {s: sum(r["decode_seconds"] for r in runs if r["batch_size"] == s) / 3 for s in sizes}
    top = max(mean.values())
    b = header(
        "Time to decode all token IDs once, by batch size",
        "Mean of 3 fresh GPU processes; codec + cosine against all codes + decision. Candidate encoding (under 1 s) excluded.",
    )
    for i, s in enumerate(sizes):
        y = y0 + i * row
        w = max(2.0, (x1 - x0) * mean[s] / top)
        batches = -(-n // s)
        per_batch_ms = 1000 * mean[s] / batches
        if s < 64:
            note = f"{per_batch_ms:.1f} ms per batch; reads all {V * D * 4 / 2**30:.0f} GiB of codes each batch: {V * D * 4 * batches / mean[s] / 1e9:.0f} GB/s (memory-bound)"
        else:
            note = f"{per_batch_ms:.0f} ms per batch; {2 * n * V * D / mean[s] / 1e12:.1f} TFLOP/s fp32 (compute-bound)"
        b += [
            text(x0 - 12, y + 17, f"batch {s:,}", "t1", 13, "end", 600),
            f"<g><title>batch {s:,}: {mean[s]:.1f} s per pass (runs: {', '.join(str(r['decode_seconds']) for r in runs if r['batch_size'] == s)})</title>"
            f'<path d="M{x0},{y + 2} h{w - 4:.1f} a4,4 0 0 1 4,4 v12 a4,4 0 0 1 -4,4 h-{w - 4:.1f} z" class="f1"/></g>',
            text(x0 + w + 8, y + 17, f"{minutes(mean[s])} per pass", "t1", 13, weight=600),
            text(x0, y + 44, note, "t2", 12),
        ]
    b.append(hline(x0, x0, y0, "axis"))
    b.append(
        f'<line x1="{x0}" y1="{y0 - 6}" x2="{x0}" y2="{y0 + row * len(sizes) - 30}" class="axis" stroke-width="1"/>'
    )
    return svg(W, H, "Decode time per batch size", b)


# Figure 4: CPU and GPU use over the run ------------------------------------------------------------------------


def read_resources(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    def num(v: str) -> float:
        try:
            return float(v)
        except ValueError:
            return float("nan")

    return [{k: (v if k in ("utc", "clock_limit_reasons") else num(v)) for k, v in r.items()} for r in rows]


def gpu_segments(rows: list[dict], threshold_gib: float = 0.5) -> list[tuple[float, float]]:
    """Time spans in which a GPU process held memory: one span per fresh GPU process, if sampled finely enough."""
    spans, start = [], None
    for r in rows:
        busy = r["vram_used_gib"] > threshold_gib
        if busy and start is None:
            start = r["elapsed_s"]
        if not busy and start is not None:
            spans.append((start, r["elapsed_s"]))
            start = None
    if start is not None:
        spans.append((start, rows[-1]["elapsed_s"]))
    return spans


def span_batch_sizes(rows: list[dict], spans: list[tuple[float, float]], report: dict) -> list[int]:
    """Name each GPU span by its batch size.

    At 5 s sampling two back-to-back processes can merge into one span, so spans are matched by what they look
    like, not counted: the largest batch holds the most VRAM, and among the others a span lasts one to three
    times the mean decode time of its batch size (from the results file).
    """
    sizes = sorted({r["batch_size"] for r in report["runs"]})
    mean = {s: sum(r["decode_seconds"] for r in report["runs"] if r["batch_size"] == s) / RUNS for s in sizes}
    peaks = [max(r["vram_used_gib"] for r in rows if a <= r["elapsed_s"] <= z) for a, z in spans]
    hi, lo = max(peaks), min(peaks)
    out = []
    for (a, z), peak in zip(spans, peaks, strict=True):
        if hi - lo > 1 and peak > (hi + lo) / 2:
            out.append(sizes[-1])
        else:
            fit = {s: min(abs(math.log((z - a) / (k * mean[s]))) for k in range(1, RUNS + 1)) for s in sizes[:-1]}
            out.append(min(fit, key=fit.get))
    return out


def fig_resources(rows: list[dict], report: dict) -> str:
    W = 880
    x0, x1 = 96, 856
    panels = [
        ("GPU utilization", "gpu_util_percent", 100, "%"),
        ("VRAM in use", "vram_used_gib", 16, " GiB"),
        ("GPU memory clock (sets the speed of batch 1 and 7)", "memory_clock_mhz", 10000, " MHz"),
        ("GPU power", "power_w", max(10.0, 20 * math.ceil(max(r["power_w"] for r in rows) / 20)), " W"),
        ("CPU use, all logical cores", "cpu_percent", 100, "%"),
    ]
    ph, pgap, top = 84, 44, 124
    H = top + len(panels) * (ph + pgap) + 24
    t_end = rows[-1]["elapsed_s"]

    def x(t: float) -> float:
        return x0 + (x1 - x0) * t / t_end

    spans = gpu_segments(rows)
    late = rows[0]["vram_used_gib"] > 0.5
    b = header(
        "CPU and GPU use during the run, sampled every 5 s",
        f"resource_monitor.py · {len(rows):,} samples over {t_end / 60:.0f} min"
        + (" · started during the first GPU run, after the CPU reference" if late else ""),
    )
    groups: list[tuple[str, float, float]] = []
    for (a, z), size in zip(spans, span_batch_sizes(rows, spans, report), strict=True):
        name = f"batch {size:,} × {RUNS}"
        if groups and groups[-1][0] == name:
            groups[-1] = (name, groups[-1][1], z)
        else:
            groups.append((name, a, z))
    if spans and not late and spans[0][0] > 30:
        groups.insert(0, ("CPU reference", 0.0, spans[0][0]))
    bottom = top + len(panels) * (ph + pgap) - pgap
    for k, (name, a, z) in enumerate(groups):
        if k % 2 == 0:
            b.append(
                f'<rect x="{x(a):.1f}" y="{top - 52}" width="{x(z) - x(a):.1f}" height="{bottom - top + 52}" class="band"/>'
            )
        if x(z) - x(a) > 7.5 * len(name):  # label a band only where the label fits; the key line names them all
            b.append(text((x(a) + x(z)) / 2, top - 36, name, "t2", 12, "middle", 600))
    key = " · ".join(f"{name}: {a / 60:.0f}–{z / 60:.0f} min" for name, a, z in groups)
    b.append(text(24, H - 10, f"Shaded spans, alternating: {key}", "t3", 11))
    for i, (name, key, ymax, unit) in enumerate(panels):
        py = top + i * (ph + pgap)

        def y(v: float, py=py, ymax=ymax) -> float:
            return py + ph - ph * min(max(v, 0.0), ymax) / ymax

        b += [
            text(x0, py - 12, name, "t1", 12, weight=600),
            hline(x0, x1, y(0), "axis"),
            hline(x0, x1, y(ymax / 2)),
            hline(x0, x1, y(ymax)),
            text(x0 - 8, y(0) + 4, f"0{unit}", "t3", 11, "end"),
            text(x0 - 8, y(ymax) + 4, f"{ymax:,g}{unit}", "t3", 11, "end"),
        ]
        pts = [(x(r["elapsed_s"]), y(r[key])) for r in rows if not math.isnan(r[key])]
        if pts:
            area = (
                f"M{pts[0][0]:.1f},{y(0):.1f} "
                + " ".join(f"L{px:.1f},{qy:.1f}" for px, qy in pts)
                + f" L{pts[-1][0]:.1f},{y(0):.1f} Z"
            )
            b += [f'<path d="{area}" class="f1" fill-opacity="0.1"/>', polyline(pts, "s1")]
            vals = [r[key] for r in rows if not math.isnan(r[key])]
            b.append(
                text(
                    x1, py - 12, f"peak {max(vals):.0f}{unit} · mean {sum(vals) / len(vals):.0f}{unit}", "t2", 11, "end"
                )
            )
    for m in range(0, int(t_end / 60) + 1, 10):
        b.append(text(x(m * 60), bottom + 18, f"{m}", "t3", 11, "middle"))
    b.append(text(x1, bottom + 18, "minutes", "t3", 11, "end"))
    return svg(W, H, "CPU and GPU use during the run", b)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=GPU_DIR)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    report = json.loads((args.results / "raw_P32.json").read_text(encoding="utf-8"))
    figures = {"gpu1_verdict.svg": fig_verdict(report), "gpu3_speed.svg": fig_speed(report)}
    gemm_path = args.results / "gemm_accuracy_P32.json"
    if gemm_path.is_file():
        figures["gpu2_precision.svg"] = fig_precision(report, json.loads(gemm_path.read_text(encoding="utf-8")))
    resources = args.results / "resources_raw_P32.csv"
    if resources.is_file():
        figures["gpu4_resources.svg"] = fig_resources(read_resources(resources), report)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in figures.items():
        (args.out / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote docs/figures/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
