"""Find every loss spike, stop and restart in a training log with the lab's two spike rules, and print the tables for dryrun1_loss.md.

Usage (from the repository root):
    python -I teams/05-architecture/experiments/results/dryrun1_spikes.py --jsonl <metrics.jsonl> [<more.jsonl> ...]
        [--rows 20] [--out tables.md] [--svg chart.svg] [--spike-svg spikes.svg]

Reads one or more metrics.jsonl files in order (one JSON object per step, with step, loss_ntp, loss_mtp,
gradient_norm, lr, tokens_per_second, and val/bpb on evaluation steps). A new attempt (a "segment") starts at
each new file and wherever the step number goes back (a rollback to an earlier checkpoint). It applies:

  Team 8, spike_score (page a person): loss_ntp, loss_mtp or gradient_norm at or above the mean + 7 standard
    deviations of the trailing 1,000 clean steps, active after 100 steps; also non_finite (NaN or infinity, stop).
    Applied by importing Team 8's own AlarmMonitor from teams/08-monitoring/alarms/alarms.py, unchanged. It runs
    inside the training loop ("in-harness"), so a new monitor starts with every attempt, as it does in a real run.
  Team 7, loss guard (stop the run): loss_ntp above 1.5 x the median of the last 100 clean losses (active once
    50 are in the window); spike steps are not added to the window; 3 spike steps in a row stop the run
    (exit 78, no save, the job is held for a rollback); a non-finite loss stops it the same way. Copied from
    Team 7's trainer, teams/07-infrastructure/support/simulation/trainer/train.py (the "loss-spike guard",
    ADR 0001 section 6), with its defaults: --spike-ratio 1.5, --spike-window 100, --spike-steps 3. The guard
    also lives in the trainer process, so it too starts empty in every attempt.

Prints (or writes with --out) Markdown: the loss curve along the kept path (about --rows rows), every spike with
the rule that caught it and what the log shows next, the attempts with how each ended and where the next one
resumed, and a summary with the numbers the stability paragraph needs. With --svg it draws the loss chart (every
attempt, stops and restarts marked); with --spike-svg a close-up of every spike with both rules' thresholds.
Standard library only; it changes no file it reads. A requeue that loses no step (exit 75) leaves no trace in
the metrics: take it from the job log.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing Team 8's alarms.py must leave no __pycache__ in their folder

T7_RATIO, T7_WINDOW, T7_STEPS = 1.5, 100, 3
MA = 50  # moving-average window for the chart and the summary
CLUSTER = 10  # spikes closer than this many steps share one close-up panel


def load_alarms(repo_root):
    path = Path(repo_root) / "teams" / "08-monitoring" / "alarms" / "alarms.py"
    if not path.exists():
        raise SystemExit(f"Team 8's alarms.py not found at {path}; pass --repo-root")
    spec = importlib.util.spec_from_file_location("team8_alarms", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path


def read_rows(paths):
    rows = []
    for fi, path in enumerate(paths):
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError as e:
                        raise SystemExit(f"{path}:{n}: not JSON ({e})")
                    r["_file"] = fi
                    rows.append(r)
    return rows


def is_train(r):
    # training rows only: the week-2 harness writes an evaluation-only step 0 without train/ce_loss
    return "loss_ntp" in r and not (r.get("step") == 0 and "train/ce_loss" not in r)


def split_segments(rows):
    segs, prev = [], None
    for r in rows:
        if prev is None or r["_file"] != prev["_file"] or r["step"] <= prev["step"]:
            segs.append([])
        segs[-1].append(r)
        prev = r
    return segs


def finite(v):
    try:
        return v is not None and not isinstance(v, bool) and math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def team7_guard(train_rows):
    """Team 7's loss-spike guard on loss_ntp for one attempt. Returns spike events, the stop step (or None) and
    the guard's line (1.5 x median) at each step where it is active."""
    window = collections.deque(maxlen=T7_WINDOW)
    run, events, line = 0, [], {}
    for r in train_rows:
        lv = r.get("loss_ntp", r.get("loss"))
        if not finite(lv):
            events.append({"step": r["step"], "value": lv, "median": None, "run": None, "kind": "non-finite"})
            return events, r["step"], line
        lv = float(lv)
        active = len(window) >= T7_WINDOW // 2
        if active:
            line[r["step"]] = T7_RATIO * statistics.median(window)
        if active and lv > T7_RATIO * statistics.median(window):
            run += 1
            events.append({"step": r["step"], "value": lv, "median": statistics.median(window), "run": run, "kind": "spike"})
            if run >= T7_STEPS:
                return events, r["step"], line
        else:
            run = 0
            window.append(lv)
    return events, None, line


def fmt(v, nd=4):
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    if isinstance(v, float):
        if not math.isfinite(v):
            return str(v)
        return f"{v:.2e}" if (abs(v) < 1e-3 and v != 0) or abs(v) >= 1e5 else f"{v:.{nd}f}"
    return str(v)


def moving_average(xs, n=MA):
    out, s, q = [], 0.0, collections.deque()
    for x in xs:
        q.append(x)
        s += x
        if len(q) > n:
            s -= q.popleft()
        out.append(s / len(q))
    return out


def svg_open(W, H, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="12">',
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>',
            f'<rect width="{W}" height="{H}" fill="white"/>',
            f'<text x="12" y="20" font-size="14" font-weight="bold">{title}</text>']


def axes(g, L, T, R, Bot, x0, x1, y0, y1, sx, sy, xlabel, ylabel, nx=5, ny=5, fs=12):
    for k in range(ny + 1):
        yv = y0 + (y1 - y0) * k / ny
        g.append(f'<line x1="{L}" x2="{R}" y1="{sy(yv):.1f}" y2="{sy(yv):.1f}" stroke="#e5e5e5"/>'
                 f'<text x="{L - 6}" y="{sy(yv) + 4:.1f}" text-anchor="end" fill="#555" font-size="{fs}">{yv:.3g}</text>')
    for k in range(nx + 1):
        xv = round(x0 + (x1 - x0) * k / nx)
        g.append(f'<text x="{sx(xv):.1f}" y="{Bot + 15}" text-anchor="middle" fill="#555" font-size="{fs}">{xv}</text>')
    g.append(f'<text x="{(L + R) / 2}" y="{Bot + 30}" text-anchor="middle" fill="#333" font-size="{fs}">{xlabel}</text>')
    g.append(f'<text x="{L - 42}" y="{(T + Bot) / 2}" transform="rotate(-90 {L - 42} {(T + Bot) / 2})" text-anchor="middle" fill="#333" font-size="{fs}">{ylabel}</text>')


def polylines(g, pts, sx, sy, colour, width):
    """Draw runs of consecutive steps as polylines (a gap or a missing value breaks the line)."""
    run = []
    for p in list(pts) + [None]:
        if p is not None and p[1] is not None and (not run or p[0] == run[-1][0] + 1):
            run.append(p)
            continue
        if len(run) > 1:
            g.append(f'<polyline fill="none" stroke="{colour}" stroke-width="{width}" points="{" ".join(f"{sx(a):.1f},{sy(b):.1f}" for a, b in run)}"/>')
        run = [p] if p is not None and p[1] is not None else []


def cross(g, x, y, colour, label):
    g.append(f'<g stroke="{colour}" stroke-width="2.5"><line x1="{x - 6:.1f}" y1="{y - 6:.1f}" x2="{x + 6:.1f}" y2="{y + 6:.1f}"/>'
             f'<line x1="{x + 6:.1f}" y1="{y - 6:.1f}" x2="{x - 6:.1f}" y2="{y + 6:.1f}"/></g>'
             f'<text x="{x + 9:.1f}" y="{y + 4:.1f}" font-size="11" fill="{colour}">{label}</text>')


RULE_COLOUR = {"t7": "#e67e22", "t8": "#8e44ad", "both": "#c0392b"}


def write_loss_svg(path, segs_train, kept, numbered, stop_marks, title):
    """Every attempt's loss_ntp (steps later run again in a second colour), the kept path's moving average, every
    spike numbered as in the spike table and coloured by the rule that caught it, every stop, and the span each
    rollback ran again."""
    W, H, L, R, T, B = 980, 470, 72, 20, 96, 50
    allp = [(r["step"], float(r["loss_ntp"])) for seg in segs_train for r in seg if finite(r.get("loss_ntp"))]
    x0, x1 = min(p[0] for p in allp), max(p[0] for p in allp)
    y0, y1 = math.floor(min(p[1] for p in allp)), math.ceil(max(p[1] for p in allp))
    sx = lambda x: L + (x - x0) / max(1, x1 - x0) * (W - L - R)
    sy = lambda y: T + (y1 - y) / max(1e-9, y1 - y0) * (H - T - B)
    g = svg_open(W, H, title)
    for st in stop_marks:  # the span a rollback ran again
        if st.get("resume") is not None:
            g.append(f'<rect x="{sx(st["resume"]):.1f}" y="{T}" width="{sx(st["step"]) - sx(st["resume"]):.1f}" height="{H - B - T}" fill="#f3e3c3" opacity="0.7"/>')
    axes(g, L, T, W - R, H - B, x0, x1, y0, y1, sx, sy, "step", "loss_ntp")
    kp = sorted((r["step"], float(r["loss_ntp"]) if finite(r.get("loss_ntp")) else None)
                for si, seg in enumerate(segs_train) for r in seg if kept[r["step"]] == si)
    polylines(g, kp, sx, sy, "#9db7d5", 1)
    for si, seg in enumerate(segs_train):
        lost = [(r["step"], float(r["loss_ntp"]) if finite(r.get("loss_ntp")) else None) for r in seg if kept[r["step"]] != si]
        polylines(g, lost, sx, sy, "#b8860b", 1)
    fin = [(s, v) for s, v in kp if v is not None]
    ma = moving_average([v for _, v in fin])
    g.append(f'<polyline fill="none" stroke="#1f4e8c" stroke-width="2.2" points="{" ".join(f"{sx(s):.1f},{sy(m):.1f}" for (s, _), m in zip(fin, ma))}"/>')
    # spikes: a dashed line per spike step, one numbered badge per cluster of nearby spikes
    clusters = []
    for n, si, s, rule in numbered:
        g.append(f'<line x1="{sx(s):.1f}" x2="{sx(s):.1f}" y1="{T}" y2="{H - B}" stroke="{RULE_COLOUR[rule]}" stroke-dasharray="4 3" opacity="0.8"/>')
        if clusters and s - clusters[-1][-1][2] < CLUSTER and si == clusters[-1][-1][1]:
            clusters[-1].append((n, si, s, rule))
        else:
            clusters.append([(n, si, s, rule)])
    for cl in clusters:
        x = sx(cl[0][2])
        lab = f"#{cl[0][0]}" + (f"–{cl[-1][0]}" if len(cl) > 1 else "")
        rules = {c[3] for c in cl}
        col = RULE_COLOUR["both"] if len(rules) > 1 else RULE_COLOUR[rules.pop()]
        wbox = 9 + 7 * len(lab)
        g.append(f'<rect x="{x - wbox / 2:.1f}" y="{T + 4}" width="{wbox}" height="16" rx="8" fill="{col}"/>'
                 f'<text x="{x:.1f}" y="{T + 16}" text-anchor="middle" font-size="11" fill="white" font-weight="bold">{lab}</text>')
    # stops: a cross above the plot and one label line each, staggered so labels never overlap
    for k, st in enumerate(stop_marks):
        x = sx(st["step"])
        yy = T - 14 - 18 * (k % 2)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{yy}" y2="{T}" stroke="#000" stroke-width="1"/>')
        txt = f"stop at step {st['step']}" + (f" → rolled back, resumed at {st['resume']}" if st.get("resume") is not None else "")
        cross(g, x, yy, "#000", "")
        right = x > (L + W - R) / 2
        g.append(f'<text x="{x - 10 if right else x + 10:.1f}" y="{yy + 4}" font-size="11" text-anchor="{"end" if right else "start"}">{txt}</text>')
    # legend, top right inside the plot
    lx, ly = W - R - 330, T + 34
    items = [("line", "#9db7d5", "", "loss_ntp every step, kept path"),
             ("line", "#b8860b", "", "steps later run again after a rollback"),
             ("line", "#1f4e8c", "", f"{MA}-step moving average, kept path"),
             ("rect", "#f3e3c3", "", "span run again after a rollback"),
             ("line", RULE_COLOUR["t7"], "4 3", "spike: Team 7 only (#n as in the spike table)"),
             ("line", RULE_COLOUR["t8"], "4 3", "spike: Team 8 only"),
             ("line", RULE_COLOUR["both"], "4 3", "spike: both rules"),
             ("cross", "#000", "", "stop (exit 78)")]
    rules = {rule for _, _, _, rule in numbered}
    rolled = any(st.get("resume") is not None for st in stop_marks)
    keep = {"steps later run again after a rollback": rolled, "span run again after a rollback": rolled,
            "stop (exit 78)": bool(stop_marks),
            "spike: Team 7 only (#n as in the spike table)": "t7" in rules, "spike: Team 8 only": "t8" in rules,
            "spike: both rules": "both" in rules}
    items = [it for it in items if keep.get(it[3], True)]
    g.append(f'<rect x="{lx - 8}" y="{ly - 12}" width="330" height="{16 * len(items) + 6}" fill="white" opacity="0.92" stroke="#ddd"/>')
    for k, (kind, c, d, txt) in enumerate(items):
        y = ly + 16 * k
        if kind == "line":
            g.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{y}" y2="{y}" stroke="{c}" stroke-width="{2.2 if c == "#1f4e8c" else 1.4}" stroke-dasharray="{d}"/>')
        elif kind == "rect":
            g.append(f'<rect x="{lx}" y="{y - 6}" width="22" height="12" fill="{c}"/>')
        else:
            g.append(f'<g stroke="{c}" stroke-width="2"><line x1="{lx + 6}" y1="{y - 5}" x2="{lx + 16}" y2="{y + 5}"/><line x1="{lx + 16}" y1="{y - 5}" x2="{lx + 6}" y2="{y + 5}"/></g>')
        g.append(f'<text x="{lx + 28}" y="{y + 4}" font-size="11">{txt}</text>')
    g.append("</svg>")
    Path(path).write_text("\n".join(g) + "\n", encoding="utf-8")


def write_spike_svg(path, panels, title):
    """One close-up per spike cluster: the metric over +/-30 steps of its attempt, with both rules' lines."""
    PW, PH, L, T, B = 470, 260, 66, 56, 46
    cols = 2 if len(panels) > 1 else 1
    nrows = (len(panels) + cols - 1) // cols
    W, H = PW * cols, 34 + PH * nrows
    g = svg_open(W, H, title)
    for i, p in enumerate(panels):
        ox, oy = (i % cols) * PW, 34 + (i // cols) * PH
        xs = [s for s, _ in p["series"]]
        ys = [v for _, v in p["series"] if v is not None] + list(p["t8"].values()) + list(p["t7"].values())
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        pad = (y1 - y0) * 0.12 or 0.5
        y0, y1 = y0 - pad, y1 + pad
        sx = lambda x, ox=ox, x0=x0, x1=x1: ox + L + (x - x0) / max(1, x1 - x0) * (PW - L - 20)
        sy = lambda y, oy=oy, y0=y0, y1=y1: oy + T + (y1 - y) / max(1e-9, y1 - y0) * (PH - T - B)
        g.append(f'<text x="{ox + 12}" y="{oy + 18}" font-weight="bold" font-size="12">{p["title"]}</text>'
                 f'<text x="{ox + 12}" y="{oy + 34}" font-size="11" fill="#555">{p["sub"]}</text>')
        axes(g, ox + L, oy + T, ox + PW - 20, oy + PH - B, x0, x1, y0, y1, sx, sy, "step", p["metric"], nx=4, ny=4, fs=10)
        polylines(g, p["series"], sx, sy, "#1f4e8c", 1.4)
        if p["t7"]:
            g.append(f'<polyline fill="none" stroke="#e67e22" stroke-width="1.4" stroke-dasharray="6 3" points="{" ".join(f"{sx(s):.1f},{sy(v):.1f}" for s, v in sorted(p["t7"].items()))}"/>')
        if p["t8"]:
            g.append(f'<polyline fill="none" stroke="#8e44ad" stroke-width="1.4" stroke-dasharray="2 3" points="{" ".join(f"{sx(s):.1f},{sy(v):.1f}" for s, v in sorted(p["t8"].items()))}"/>')
        for s, v in p["marks"]:
            if v is None:
                xx = sx(s)
                g.append(f'<g stroke="#c0392b" stroke-width="2.5"><line x1="{xx - 6:.1f}" y1="{oy + T + 4}" x2="{xx + 6:.1f}" y2="{oy + T + 16}"/><line x1="{xx + 6:.1f}" y1="{oy + T + 4}" x2="{xx - 6:.1f}" y2="{oy + T + 16}"/></g>'
                         f'<text x="{xx - 10:.1f}" y="{oy + T + 14}" font-size="11" fill="#c0392b" text-anchor="end">NaN at step {s}: no value to plot</text>')
            else:
                g.append(f'<circle cx="{sx(s):.1f}" cy="{sy(v):.1f}" r="4.5" fill="#c0392b"/>')
        leg = ([("#e67e22", "6 3", "Team 7 line: 1.5 × median")] if p["t7"] else []) + \
              ([("#8e44ad", "2 3", "Team 8 line: mean + 7σ")] if p["t8"] else [])
        for k, (c, d, txt) in enumerate(leg):
            yy = oy + 14 + 14 * k
            g.append(f'<line x1="{ox + PW - 168}" x2="{ox + PW - 150}" y1="{yy}" y2="{yy}" stroke="{c}" stroke-width="1.4" stroke-dasharray="{d}"/>'
                     f'<text x="{ox + PW - 145}" y="{yy + 4}" font-size="10">{txt}</text>')
    g.append("</svg>")
    Path(path).write_text("\n".join(g) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jsonl", required=True, nargs="+", help="the run's metrics.jsonl file(s), in order")
    ap.add_argument("--rows", type=int, default=20, help="about this many rows in the curve table (decision A3)")
    ap.add_argument("--repo-root", default=".", help="where teams/08-monitoring/ is (default: the current folder)")
    ap.add_argument("--out", help="write the tables to this Markdown file instead of printing them")
    ap.add_argument("--svg", help="also draw the loss chart to this SVG file")
    ap.add_argument("--spike-svg", help="also draw a close-up of every spike to this SVG file")
    ap.add_argument("--title", help="the charts' title (default: the log's folder name)")
    a = ap.parse_args()

    mod, alarms_path = load_alarms(a.repo_root)
    rows = read_rows(a.jsonl)
    segs = [s for s in split_segments(rows) if any(is_train(r) for r in s)]
    segs_train = [[r for r in s if is_train(r)] for s in segs]
    if not segs_train:
        raise SystemExit("no training rows with loss_ntp in the file(s)")

    # Both rules live in the trainer process, so each starts empty in every attempt.
    t7, t7_line, stops = [], [], []
    for si, seg in enumerate(segs_train):
        ev, stop, line = team7_guard(seg)
        t7 += [dict(e, seg=si) for e in ev]
        t7_line.append(line)
        stops.append(stop)
    t8, t8_line = [], []
    for si, seg in enumerate(segs_train):
        monitor = mod.AlarmMonitor()
        t8_line.append(collections.defaultdict(dict))
        for r in seg:
            # Team 8's line (mean + 7 sigma of its trailing window) before this step, for the close-up charts only;
            # read from the monitor's own trailing statistics, skipped if that internal ever changes
            try:
                for m in ("loss_ntp", "gradient_norm"):
                    st = monitor._trailing[m]
                    if len(st) >= monitor.min_window:
                        mu, sd = st.mean_std()
                        t8_line[si][m][r["step"]] = mu + monitor.sigma_threshold * sd
            except (AttributeError, KeyError, TypeError):
                pass
            kw = {k: r[k] for k in mod.SCALAR_METRICS if k in r}
            for al in monitor.step(r["step"], **kw) or []:
                t8.append(dict(al, seg=si))
    t8_spikes = [x for x in t8 if x.get("rule") in ("spike_score", "non_finite")]

    # the kept path: for every step, the last attempt that ran it
    kept, rowmap = {}, {}
    for si, seg in enumerate(segs_train):
        for r in seg:
            kept[r["step"]] = si
            rowmap[(si, r["step"])] = r
    path = [rowmap[(kept[s], s)] for s in sorted(kept)]
    val = {}
    for si, seg in enumerate(segs):
        for r in seg:
            if "val/bpb" in r and (r["step"] == 0 or kept.get(r["step"]) == si):
                val[r["step"]] = r["val/bpb"]
    fin = [(r["step"], float(r["loss_ntp"])) for r in path if finite(r.get("loss_ntp"))]
    ma_list = moving_average([v for _, v in fin])
    ma_at = {s: m for (s, _), m in zip(fin, ma_list)}

    every = max(1, len(path) // a.rows)
    vsteps = sorted(k for k in val if k > 0)
    if len(vsteps) > 1:  # land the rows on held-out evaluation steps, so every row has a held-out score,
        d = vsteps[1] - vsteps[0]  # but only when evaluations are frequent enough to give about --rows rows
        if d <= 2 * every:
            every = max(d, round(every / d) * d)
    spike_keys = {(e["seg"], e["step"]) for e in t7} | {(x["seg"], x["step"]) for x in t8_spikes}
    spike_steps = {s for _, s in spike_keys}
    curve = [r for i, r in enumerate(path) if i == 0 or r["step"] % every == 0 or r["step"] in val or i == len(path) - 1]

    sha = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in a.jsonl]
    names = ", ".join(f"{Path(p).name} (sha256 {h})" for p, h in zip(a.jsonl, sha))
    n_rows = sum(len(s) for s in segs_train)
    out = [f"<!-- generated by dryrun1_spikes.py from {names}: {n_rows} training rows, {len(segs_train)} attempt(s) -->", ""]

    # ---- the curve
    out += ["### The loss curve", "",
            f"Along the kept path (for each step, the last attempt that ran it): the first step, every {every} steps, every held-out evaluation step and the last step."
            f" loss_ntp is one batch, so it is noisy; the {MA}-step moving average shows the trend. Spike steps are in the next table.", "",
            f"| step | loss_ntp | {MA}-step average | loss_mtp | gradient_norm | lr | tokens/s | held-out bpb |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in curve:
        out.append(f"| {r['step']} | {fmt(r.get('loss_ntp'))} | {fmt(ma_at.get(r['step']))} | {fmt(r.get('loss_mtp'))} | "
                   f"{fmt(r.get('gradient_norm'))} | {fmt(r.get('lr'))} | {fmt(r.get('tokens_per_second'), 0)} | {fmt(val.get(r['step']))} |")

    # ---- every spike
    out += ["", "### Every spike", ""]
    numbered = []
    if not spike_keys:
        out.append("No spike by either rule.")
    else:
        out += ["| # | attempt | step | metric | value | Team 7 guard (1.5 × median of last 100; 3 in a row stops) | Team 8 (mean + 7σ of last 1,000 pages; NaN stops) | what the log shows next |",
                "|---:|---:|---:|---|---:|---|---|---|"]
        by = collections.defaultdict(lambda: {"t7": None, "t8": []})
        for e in t7:
            by[(e["seg"], e["step"])]["t7"] = e
        for x in t8_spikes:
            by[(x["seg"], x["step"])]["t8"].append(x)
        for n, key in enumerate(sorted(by), 1):
            si, s = key
            e, xs = by[key]["t7"], by[key]["t8"]
            numbered.append((n, si, s, "both" if e and xs else ("t7" if e else "t8")))
            if e and e["kind"] == "spike":
                t7txt = f"spike {e['run']} in a row (line {fmt(T7_RATIO * e['median'])})" + (" → **stop, exit 78**" if s == stops[si] else "")
            elif e:
                t7txt = "non-finite loss → **stop, exit 78**"
            metric = "loss_ntp" if e else xs[0].get("metric", "loss_ntp")
            if not e:
                ln = t7_line[si].get(s)
                t7txt = (f"no spike (line {fmt(ln)})" if ln is not None else "no spike (not active yet)") if metric == "loss_ntp" else f"does not watch {metric}"
            t8txt = "; ".join(
                (f"**page**: {x['metric']} {x.get('z_score')}σ above mean {fmt(x.get('trailing_mean'))} (line {fmt(x['trailing_mean'] + 7 * x['trailing_std'])})" if x["rule"] == "spike_score"
                 else f"**stop**: {x['metric']} is {x.get('value')}") for x in xs)
            if not xs:
                ln = t8_line[si][metric].get(s)
                t8txt = f"no page: below its line ({fmt(ln)})" if ln is not None else "no page (not active yet)"
            v = rowmap[(si, s)].get(metric)
            seg = segs_train[si]
            idx = [r["step"] for r in seg].index(s)
            if idx + 1 < len(seg):
                nx = seg[idx + 1]
                nexttxt = f"step {nx['step']}: {metric} {fmt(float(nx[metric]) if finite(nx.get(metric)) else nx.get(metric))}; attempt {si + 1} continued to step {seg[-1]['step']}"
            else:
                nexttxt = f"attempt {si + 1} ends here"
                if si + 1 < len(segs_train):
                    nexttxt += f"; attempt {si + 2} starts at step {segs_train[si + 1][0]['step']}"
            out.append(f"| {n} | {si + 1} | {s} | {metric} | {fmt(float(v) if finite(v) else v)} | {t7txt} | {t8txt} | {nexttxt} |")

    # ---- attempts
    out += ["", "### Attempts, stops and restarts (from the metrics)", "",
            "| attempt | steps | how it ended | next attempt |", "|---:|---|---|---|"]
    stop_marks = []
    for si, seg in enumerate(segs_train):
        first, last = seg[0]["step"], seg[-1]["step"]
        if stops[si] is not None:
            nf = any(e["seg"] == si and e["step"] == stops[si] and e["kind"] == "non-finite" for e in t7)
            how = (f"non-finite loss at step {stops[si]} → stop, exit 78, job held" if nf
                   else f"Team 7 guard: {T7_STEPS} loss spikes in a row, stop at step {stops[si]} → exit 78, job held")
        elif si + 1 < len(segs_train):
            how = f"the log ends at step {last} with no stop rule fired (a crash, requeue or manual stop: see the job log)"
        else:
            how = f"finished at step {last}"
        if si + 1 < len(segs_train):
            nf_ = segs_train[si + 1][0]["step"]
            lost = last - nf_ + 1
            nxt = f"attempt {si + 2} resumes at step {nf_}" + (f": rolled back, {lost} step(s) run again" if lost > 0 else ": no step lost")
            if stops[si] is not None or lost > 0:
                stop_marks.append({"step": last, "resume": nf_ if lost > 0 else None})
        else:
            nxt = "—"
            if stops[si] is not None:
                stop_marks.append({"step": last, "resume": None})
        out.append(f"| {si + 1} | {first} to {last} ({len(seg)} rows) | {how} | {nxt} |")

    # ---- summary
    steps_kept = sorted(kept)
    gaps = [(p, q) for p, q in zip(steps_kept, steps_kept[1:]) if q != p + 1]
    t7_spk = sum(1 for e in t7 if e["kind"] == "spike")
    stop_steps = [s for s in stops if s is not None]
    vk = sorted(val)
    out += ["", "### Summary", "",
            f"- Rows read: {n_rows} in {len(segs_train)} attempt(s); kept path: steps {steps_kept[0]} to {steps_kept[-1]}"
            + (f"; gaps: {', '.join(f'{p}→{q}' for p, q in gaps)}." if gaps else "; no gaps."),
            f"- Team 7 guard: {t7_spk} loss spike step(s); " + (f"{len(stop_steps)} stop(s), at step {', '.join(str(s) for s in stop_steps)}." if stop_steps else "it would not have stopped the run."),
            f"- Team 8: {sum(1 for x in t8_spikes if x['rule'] == 'spike_score')} spike_score alarm(s), "
            f"{len({(x['seg'], x['step']) for x in t8_spikes if x['rule'] == 'non_finite'})} non_finite step(s); other Team 8 warnings: {len(t8) - len(t8_spikes)}.",
            f"- Team 8's code: {alarms_path.as_posix()}."]
    if fin:
        lo = min(fin, key=lambda sv: sv[1])
        mid = len(fin) // 2
        out += [f"- loss_ntp on the kept path: first step {fmt(fin[0][1])}, last step {fmt(fin[-1][1])}, lowest {fmt(lo[1])} (step {lo[0]}).",
                (f"- {MA}-step moving average of loss_ntp: {fmt(ma_list[MA - 1])} at step {fin[MA - 1][0]}, {fmt(ma_list[mid])} at step {fin[mid][0]}, {fmt(ma_list[-1])} at step {fin[-1][0]}."
                 if len(fin) >= MA else f"- fewer than {MA} steps: no moving average.")]
    out.append("- Held-out bpb: " + (f"{fmt(val[vk[0]])} at step {vk[0]} → {fmt(val[vk[-1]])} at step {vk[-1]} ({len(vk)} evaluations; lowest {fmt(min(val.values()))} at step {min(val, key=val.get)})" if val else "not in the log") + ".")

    label = a.title or Path(a.jsonl[0]).parent.name or Path(a.jsonl[0]).stem
    if a.svg:
        write_loss_svg(a.svg, segs_train, kept, numbered, stop_marks, f"Loss curve: {label}")
        out.append(f"- Chart: {Path(a.svg).name}.")
    if a.spike_svg and spike_keys:
        clusters = []
        for k in sorted(spike_keys):
            if clusters and clusters[-1][-1][0] == k[0] and k[1] - clusters[-1][-1][1] < CLUSTER:
                clusters[-1].append(k)
            else:
                clusters.append([k])
        num = {(si, s): n for n, si, s, _ in numbered}
        panels = []
        for cl in clusters:
            si = cl[0][0]
            seg = segs_train[si]
            evs = [e for e in t7 if (e["seg"], e["step"]) in cl]
            xs = [x for x in t8_spikes if (x["seg"], x["step"]) in cl]
            metric = "loss_ntp" if evs else xs[0]["metric"]
            s0, s1 = cl[0][1] - 30, cl[-1][1] + 30
            series = [(r["step"], float(r[metric]) if finite(r.get(metric)) else None) for r in seg if s0 <= r["step"] <= s1]
            marks = [(s, float(rowmap[(si, s)][metric]) if finite(rowmap[(si, s)].get(metric)) else None) for _, s in cl]
            t8line = {s: v for s, v in t8_line[si][metric].items() if s0 <= s <= s1}
            t7l = {s: v for s, v in t7_line[si].items() if s0 <= s <= s1} if metric == "loss_ntp" else {}
            who = []
            if evs:
                who.append("Team 7: " + ("STOP, exit 78" if stops[si] in [s for _, s in cl] else f"{sum(1 for e in evs if e['kind'] == 'spike')} spike step(s), no stop"))
            elif metric == "loss_ntp":
                who.append("Team 7: no spike")
            else:
                who.append(f"Team 7: does not watch {metric}")
            if xs:
                who.append("Team 8: " + ("STOP (non-finite)" if any(x["rule"] == "non_finite" for x in xs) else "page a person"))
            else:
                who.append("Team 8: below its line, no page")
            nums = [num[k] for k in cl]
            title = (f"#{nums[0]}" + (f"–{nums[-1]}" if len(nums) > 1 else "") + f"  step {cl[0][1]}" + (f" to {cl[-1][1]}" if len(cl) > 1 else "")
                     + f", attempt {si + 1}: {metric}")
            panels.append({"title": title, "sub": "; ".join(who), "metric": metric, "series": series, "marks": marks,
                           "t8": t8line, "t7": t7l})
        write_spike_svg(a.spike_svg, panels, f"Every spike, close up: {label}")
        out.append(f"- Spike close-ups: {Path(a.spike_svg).name}.")

    text = "\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))  # UTF-8 on every console (Windows cp1252 cannot print the sigma sign)


if __name__ == "__main__":
    main()
