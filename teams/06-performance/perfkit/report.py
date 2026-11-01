"""Run JSON -> Markdown, two-run comparison, baseline and slowest-parts files.

bench writes <tag>.md with render() after every run, and uses compare_lines() / ab_note() for --against.

    python -m perfkit.report results/runs/<tag>.json                       # rewrites <tag>.md
    python -m perfkit.report b.json --compare a.json --baseline out.md --slowest out5.md   # exit 2 on FAIL

The committed results/baseline_v0.md and slowest5_v0.md are hand-written from such output; do not overwrite them.

  * render(run) -> Markdown: header (GPU, dtype, B x T, torch, commit), step stats, MFU, diagnostics (CUDA
    timing-event allocations, the run's warnings), per-region table (ms, p90, % of step, level),
    "time by part type" (sum over layers), five slowest leaf parts.
  * compare(a, b, tol_pct, gate_level, abs_tol_ms) -> (rows, ok, problems): the whole step, every region with
    level <= gate_level, checkpoint save (both runs) and the measured MoE all-to-all (both runs) must pass
    gate(): within tol_pct (diff = slower / faster - 1) OR less than abs_tol_ms apart (TSAI, 30 Oct: a very
    small part can be 10% apart on timer noise alone). Both run times are reported for every part. Refuses (problems) runs on
    different GPUs, commits, vocabularies, dtypes, B or T, a dirty tree, or a different COMPARE_CONFIG.
    Level-3 rows are listed as information only. Runs that differ only in an IMPL_SWITCHES entry are compared
    and labelled A/B (ab_note).
  * baseline_md(...): GPU name, commits, config, PASS / FAIL / A/B / REFUSED, the comparison table.
  * slowest_md(run): five slowest leaf parts, each with ms, % of step and the trace file; the "why" and the
    week-2 idea are placeholders to fill in by hand.
Per-part trace files are cut from the full trace by perfkit/parts.py (bench, trace mode).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

# Config that changes the work a step does (aligned with bench.COMPARE_CONFIG).
COMPARE_CONFIG = [
    ("model", None),
    ("optim", None),
    ("run", "compile"),
    ("run", "grad_clip"),
    ("data", "source"),
]


# Implementation switches: the same model and update, computed another way. Two runs that differ only in
# these are compared (an A/B timing), and the verdict is labelled A/B: a part outside tol_pct there is the
# change being measured. The 5% repeat check stays two runs of one implementation (bench --repeat).
IMPL_SWITCHES = [("model", "moe", "dispatch"), ("optim", "muon_impl"), ("optim", "adamw_impl"), ("data", "prefetch")]


def _switch_value(config: dict, path: tuple):
    for k in path:
        if not isinstance(config, dict):
            return None
        config = config.get(k)
    return config


def _model_defaults_filled(model: dict) -> dict:
    """A run's model config with every ModelConfig field it lacks set to the field's default. A field is added
    with a default that keeps the old behaviour (models/config.py), so a run written before the field existed
    (e.g. week-1 runs without model.activation) still compares equal to a new run that uses that default."""
    try:
        from dataclasses import MISSING, fields

        from models.config import ModelConfig
    except ImportError:                                  # report run outside teams/06-performance: compare as is
        return model
    out = dict(model)
    for f in fields(ModelConfig):
        if f.name not in out:
            out[f.name] = f.default_factory() if f.default is MISSING else f.default
    return out


def compare_config_value(config: dict, section: str, key: str | None):
    """config[section] (key None) or config[section][key], without the IMPL_SWITCHES. Model fields a run lacks
    count as their ModelConfig default (_model_defaults_filled)."""
    sect = config.get(section, {})
    if section == "model" and isinstance(sect, dict):
        sect = _model_defaults_filled(sect)
    value = sect if key is None else sect.get(key)
    if key is not None or not isinstance(value, dict):
        return value
    for path in IMPL_SWITCHES:
        if path[0] != section:
            continue
        *parents, leaf = path[1:]
        if not parents:
            value = {k: v for k, v in value.items() if k != leaf}
        elif isinstance(value.get(parents[0]), dict):
            value = {**value, parents[0]: {k: v for k, v in value[parents[0]].items() if k != leaf}}
    return value


def impl_differences(a: dict, b: dict) -> list[str]:
    """The IMPL_SWITCHES two runs differ in, e.g. ["model.moe.dispatch: sorted vs loop"]."""
    out = []
    for path in IMPL_SWITCHES:
        va, vb = _switch_value(a.get("config", {}), path), _switch_value(b.get("config", {}), path)
        if va != vb:
            out.append(f"{'.'.join(path)}: {va} vs {vb}")
    return out


def ab_note(a: dict, b: dict) -> str | None:
    diffs = impl_differences(a, b)
    if not diffs:
        return None
    return f"A/B of {'; '.join(diffs)}: a gap above tol_pct is the change being measured, not a failed repeat"


def gate(x: float, y: float, tol_pct: float, abs_tol_ms: float) -> tuple:
    """(diff_pct, verdict) for one part: "ok" within tol_pct, "ok_abs" outside tol_pct but less than
    abs_tol_ms apart (report.abs_tol_ms), else "FAIL". The one rule bench --against / --repeat and
    report --compare use."""
    diff = _pct_delta(x, y)
    if diff is not None and diff <= tol_pct:
        return diff, "ok"
    if abs(x - y) < abs_tol_ms:
        return diff, "ok_abs"
    return diff, "FAIL"


PASSED = ("ok", "ok_abs")


def _change(x, y, diff) -> str:
    """This run against the other: '12.3% faster' = 12.3% less time, '4.1% slower' = 4.1% more time.
    The result column uses the gate's own gap (slower / faster - 1), so very near tol_pct the two can differ."""
    if diff is None or x is None or y is None:
        return "-"
    if x == y:
        return "same"
    if not y:
        return "inf"
    pct = 100 * (x - y) / y
    if abs(pct) < 0.05:
        return "same"
    return f"{abs(pct):.1f}% {'faster' if pct < 0 else 'slower'}"


def compare_lines(rows, ok: bool, problems: list, note: str | None, tol_pct: float, gate_level: int,
                  abs_tol_ms: float, this: str = "this run", other: str = "against") -> list[str]:
    """The console table for bench --against and report --compare: gated rows, then one verdict line."""
    w = max([34] + [len(r[0]) + 2 for r in rows if r[4] != "info"])
    lines = [f"5% check: step, step parts and whole blocks (level <= {gate_level}): "
             f"within {tol_pct:g}% or less than {abs_tol_ms:g} ms apart"]
    lines += [f"  REFUSED  {p}" for p in problems]
    if note:
        lines.append(f"  {note}")
    lines.append(f"  {'part':<{w}}{this:>12}{other:>12}{'diff ms':>10}  {'change':<16}result")
    gated = [r for r in rows if r[4] != "info"]
    for name, x, y, diff, verdict in gated:
        mark = _MARK.get(verdict, verdict).replace("{abs}", f"{abs_tol_ms:g}")
        lines.append(f"  {name:<{w}}{_f(x):>12}{_f(y):>12}{_absdiff(x, y):>10}  {_change(x, y, diff):<16}{mark}")
    info = len(rows) - len(gated)
    if info:
        lines.append(f"  ({info} parts inside blocks: information only, see the .md)")
    bad = [r for r in gated if r[4] not in PASSED]
    by_abs = sum(1 for r in gated if r[4] == "ok_abs")
    if problems:
        verdict = f"REFUSED: {len(problems)} reason(s) above; these runs cannot be compared"
    elif note:
        faster = sum(1 for r in gated if r[4] == "FAIL" and r[1] < r[2])
        slower = sum(1 for r in gated if r[4] == "FAIL" and r[1] > r[2])
        verdict = (f"A/B: {faster} part(s) faster, {slower} slower, {len(gated) - len(bad)} within {tol_pct:g}%"
                   + (f", {sum(1 for r in bad if r[4] == 'MISSING')} missing" if any(r[4] == "MISSING" for r in bad) else ""))
    elif ok:
        verdict = (f"PASS: all {len(gated)} gated parts within {tol_pct:g}% or {abs_tol_ms:g} ms"
                   f" ({by_abs} by the {abs_tol_ms:g} ms rule)")
    else:
        verdict = (f"FAIL: {len(bad)} of {len(gated)} gated parts outside {tol_pct:g}% and {abs_tol_ms:g} ms, "
                   f"or missing")
    lines.append(f"  {verdict}")
    return lines


_MARK = {"ok": "ok", "ok_abs": "ok (< {abs} ms)", "FAIL": "OUTSIDE", "MISSING": "MISSING"}


def _absdiff(x, y) -> str:
    return "-" if x is None or y is None else f"{abs(x - y):.3f}"


def _f(x, digits=3):
    if x is None:
        return "-"
    try:
        return f"{float(x):.{digits}f}"
    except (TypeError, ValueError):
        return str(x)


def _pct_delta(x, y) -> float | None:
    """Relative percent gap: (slower/faster - 1) * 100. Same rule as bench.quick_compare."""
    if x is None or y is None:
        return None
    if x == y:
        return 0.0
    if min(x, y) > 0:
        return (max(x, y) / min(x, y) - 1) * 100
    return math.inf


def _batch_size(run: dict):
    meta = run.get("meta") or {}
    if "batch_size" in meta and meta["batch_size"] is not None:
        return meta["batch_size"]
    return (run.get("config") or {}).get("run", {}).get("batch_size")


def _dtype(run: dict):
    meta = run.get("meta") or {}
    if meta.get("dtype") is not None:
        return meta["dtype"]
    return (run.get("config") or {}).get("run", {}).get("dtype")


def _seq_len(run: dict):
    meta = run.get("meta") or {}
    if meta.get("seq_len") is not None:
        return meta["seq_len"]
    return (run.get("config") or {}).get("model", {}).get("block_size")


def _refuse(a: dict, b: dict) -> list[str]:
    """Why two runs cannot be a baseline pair. Besides the work and the GPU, both runs must time the SAME
    committed code: one commit, and a clean tree (dirty is False; None means it could not be checked)."""
    problems = []
    for k in ("gpu", "vocab_size", "commit"):
        if a.get("meta", {}).get(k) != b.get("meta", {}).get(k):
            problems.append(f"different {k}: {a.get('meta', {}).get(k)} vs {b.get('meta', {}).get(k)}")
    for run in (a, b):
        meta = run.get("meta", {})
        if meta.get("dirty") is not False:
            problems.append(f"run {meta.get('tag')}: dirty={meta.get('dirty')}: not a clean git checkout of the commit")
    if _dtype(a) != _dtype(b):
        problems.append(f"different dtype: {_dtype(a)} vs {_dtype(b)}")
    if _batch_size(a) != _batch_size(b):
        problems.append(f"different batch_size: {_batch_size(a)} vs {_batch_size(b)}")
    if _seq_len(a) != _seq_len(b):
        problems.append(f"different seq_len: {_seq_len(a)} vs {_seq_len(b)}")
    for section, key in COMPARE_CONFIG:
        va = compare_config_value(a.get("config", {}), section, key)
        vb = compare_config_value(b.get("config", {}), section, key)
        if va != vb:
            if key is None:
                problems.append(f"different {section} config")
            else:
                problems.append(f"different {section}.{key}: {va} vs {vb}")
    return problems


def _step_ms(run: dict):
    return run["clean"]["step_ms"]["median"]


def _regions(run: dict) -> dict:
    return (run.get("layer") or {}).get("regions") or {}


def _part_type_key(name: str) -> str:
    return re.sub(r"block\d+", "block*", name)


def _part_type_sums(regions: dict) -> dict[str, float]:
    sums: dict[str, float] = {}
    for name, r in regions.items():
        key = _part_type_key(name)
        sums[key] = sums.get(key, 0.0) + float(r["median"])
    return sums


def _is_leaf(name: str, regions: dict) -> bool:
    """A leaf is not a parent prefix of another region name (e.g. fwd:block0 vs fwd:block0.attn.qkv)."""
    prefix = name + "."
    phase_prefix = name + ":"
    for other in regions:
        if other == name:
            continue
        if other.startswith(prefix) or other.startswith(phase_prefix):
            return False
    return True


def _leaf_regions(run: dict) -> list[tuple[str, dict]]:
    regions = _regions(run)
    level3 = [(n, r) for n, r in regions.items() if r.get("level") == 3 and _is_leaf(n, regions)]
    if level3:
        return level3
    deepest = [(n, r) for n, r in regions.items() if _is_leaf(n, regions)]
    return deepest


def _five_slowest(run: dict) -> list[tuple[str, dict, float]]:
    step = _step_ms(run) or 1.0
    leaves = _leaf_regions(run)
    ranked = sorted(leaves, key=lambda nr: float(nr[1]["median"]), reverse=True)[:5]
    out = []
    for name, r in ranked:
        pct = 100.0 * float(r["median"]) / step
        out.append((name, r, pct))
    return out


def render(run: dict) -> str:
    meta = run.get("meta") or {}
    cfg_run = (run.get("config") or {}).get("run") or {}
    cfg_model = (run.get("config") or {}).get("model") or {}
    metrics = run.get("metrics") or {}
    clean = run.get("clean") or {}
    st = clean.get("step_ms") or {}

    gpu = meta.get("gpu") or "-"
    dtype = _dtype(run) or "-"
    b = _batch_size(run)
    t = _seq_len(run) or cfg_model.get("block_size")
    torch_v = meta.get("torch") or "-"
    commit = meta.get("commit") or "-"
    dirty = " (DIRTY)" if meta.get("dirty") else ""
    tag = meta.get("tag") or "-"

    mfu = metrics.get("mfu")
    mfu_s = f"{100 * mfu:.1f}%" if mfu is not None else "-"
    hfu = metrics.get("hfu")
    hfu_s = f"{100 * hfu:.1f}%" if hfu is not None else "-"
    tps = metrics.get("tokens_per_s")
    tps_s = f"{tps:,.0f}" if tps is not None else "-"

    step_base = st.get("median") or 1.0
    lines = [
        f"# Bench report — {tag}",
        "",
        f"**GPU:** {gpu}  |  **dtype:** {dtype}  |  **B x T:** {b} x {t}  |  **torch:** {torch_v}",
        f"**commit:** `{commit}`{dirty}  |  **tag:** {tag}",
        "",
        "## Step (clean)",
        "",
        f"- median: {_f(st.get('median'))} ms",
        f"- p10..p90: {_f(st.get('p10'))} .. {_f(st.get('p90'))} ms",
        f"- tokens/s: {tps_s}",
        f"- MFU: {mfu_s}  |  HFU: {hfu_s}",
        "",
    ]

    # Diagnostics are observational, not correctness-gate failures. Preserve
    # exact warning strings from the benchmark rather than reconstructing them.
    layer = run.get("layer") or {}
    comm = (run.get("comm") or {}).get("moe_a2a") or {}
    allocations = [
        ("clean", clean.get("events_created_during_steps")),
        ("layer", layer.get("events_created_during_steps")),
        ("layer.inner_pass", (layer.get("inner_pass") or {}).get("events_created_during_steps")),
        ("layer.recorder_pool", layer.get("events_created_while_measuring")),
        ("layer.inner_pass.recorder_pool", (layer.get("inner_pass") or {}).get("events_created_while_measuring")),
        ("communication.max_rank", comm.get("events_created_during_steps")),
    ]
    warnings = run.get("warnings") or []
    lines += ["## Diagnostics", "", "### CUDA timing-event allocations", ""]
    for stage, count in allocations:
        if count is not None:
            status = "WARN" if count > 0 else "OK"
            field = ("events_created_while_measuring" if stage.endswith(".recorder_pool")
                     else "events_created_during_steps")
            lines.append(f"- [{status}] {stage}: {field}={count}")
    if all(count is None for _, count in allocations):
        lines.append("- NOT REPORTED (legacy run JSON)")
    lines += ["", "### Benchmark warnings", ""]
    if warnings:
        lines.extend(f"- [warn] {message}" for message in warnings)
    else:
        lines.append("- None recorded")
    lines += [""]

    regions = _regions(run)
    if regions:
        lines += [
            "## Regions",
            "",
            f"| part | median ms | p90 | % of step | level |",
            f"| :--- | ---: | ---: | ---: | ---: |",
        ]
        for name, r in regions.items():
            pct = 100.0 * float(r["median"]) / float(step_base)
            lines.append(
                f"| {name} | {_f(r['median'])} | {_f(r.get('p90'))} | {_f(pct, 1)} | {r.get('level')} |"
            )
        lines.append("")

        sums = _part_type_sums(regions)
        lines += [
            "## Time by part type (sum over layers)",
            "",
            f"| part type | median ms sum | % of step |",
            f"| :--- | ---: | ---: |",
        ]
        for key in sorted(sums, key=sums.get, reverse=True):
            pct = 100.0 * sums[key] / float(step_base)
            lines.append(f"| {key} | {_f(sums[key])} | {_f(pct, 1)} |")
        lines.append("")

    lines += ["## Five slowest leaf parts", ""]
    for i, (name, r, pct) in enumerate(_five_slowest(run), 1):
        lines.append(f"{i}. `{name}` — {_f(r['median'])} ms ({_f(pct, 1)}% of step)")
    lines.append("")
    return "\n".join(lines)


def compare(a: dict, b: dict, tol_pct: float, gate_level: int, abs_tol_ms: float):
    problems = _refuse(a, b)
    rows = []
    ok = not problems

    pairs = [("step (clean)", _step_ms(a), _step_ms(b))]
    ra, rb = _regions(a), _regions(b)
    gated_names = [n for n, r in ra.items() if r["level"] <= gate_level]
    gated_names += [n for n, r in rb.items() if r["level"] <= gate_level and n not in ra]
    for name in gated_names:
        pairs.append((name, ra[name]["median"] if name in ra else None, rb[name]["median"] if name in rb else None))

    if a.get("checkpoint") and b.get("checkpoint"):
        pairs.append(
            (
                "checkpoint save",
                a["checkpoint"]["save_ms"]["median"],
                b["checkpoint"]["save_ms"]["median"],
            )
        )
    ca = (a.get("comm") or {}).get("moe_a2a") or {}
    cb = (b.get("comm") or {}).get("moe_a2a") or {}
    if ca.get("measured") and cb.get("measured"):
        pairs.append(("moe all-to-all", ca["per_step_ms"], cb["per_step_ms"]))

    for name, x, y in pairs:
        if x is None or y is None:
            rows.append((name, x, y, None, "MISSING"))
            ok = False
            continue
        diff, verdict = gate(x, y, tol_pct, abs_tol_ms)
        ok = ok and verdict in PASSED
        rows.append((name, x, y, diff, verdict))

    # Level > gate_level: information only (listed, not gated).
    info_names = sorted(
        {n for n, r in ra.items() if r["level"] > gate_level}
        | {n for n, r in rb.items() if r["level"] > gate_level}
    )
    for name in info_names:
        x = ra[name]["median"] if name in ra else None
        y = rb[name]["median"] if name in rb else None
        diff = _pct_delta(x, y) if x is not None and y is not None else None
        rows.append((name, x, y, diff, "info"))

    return rows, ok, problems


def baseline_md(a: dict, b: dict, rows, ok, problems) -> str:
    meta_a = a.get("meta") or {}
    meta_b = b.get("meta") or {}
    note = ab_note(a, b)
    verdict = "REFUSED" if problems else "A/B (see the change column)" if note else "PASS" if ok else "FAIL"
    lines = [
        f"# {'A/B' if note else 'Baseline'} comparison — {verdict}",
        "",
        f"**GPU:** {meta_a.get('gpu')} (vs {meta_b.get('gpu')})",
        f"**commit a:** `{meta_a.get('commit')}`",
        f"**commit b:** `{meta_b.get('commit')}`",
        f"**config a:** tag={meta_a.get('tag')} batch={_batch_size(a)} dtype={_dtype(a)} T={_seq_len(a)}",
        f"**config b:** tag={meta_b.get('tag')} batch={_batch_size(b)} dtype={_dtype(b)} T={_seq_len(b)}",
        f"**result:** {verdict}",
        "",
    ]
    if note:
        lines += [f"**{note}**", ""]
    if problems:
        lines.append("## Refuse / problems")
        lines.append("")
        for p in problems:
            lines.append(f"- {p}")
        lines.append("")

    ta, tb = meta_a.get("tag") or "a", meta_b.get("tag") or "b"
    lines += [
        "## Comparison table",
        "",
        f"Gated rows first (the 5% rule), then the parts inside blocks (information only). "
        f"The change says how `{ta}` compares with `{tb}`.",
        "",
        "A gated part passes when the two runs are within the tolerance in percent OR less than "
        "report.abs_tol_ms apart (marked `ok (< ... ms)`).",
        "",
        f"| part | {ta} ms | {tb} ms | diff ms | change | result |",
        "| :--- | ---: | ---: | ---: | :--- | :--- |",
    ]
    for name, x, y, diff, verdict_row in rows:
        mark = {"ok": "ok", "ok_abs": "ok (< abs_tol_ms)", "FAIL": "**outside**",
                "MISSING": "**missing**"}.get(verdict_row, verdict_row)
        lines.append(f"| {name} | {_f(x)} | {_f(y)} | {_absdiff(x, y)} | {_change(x, y, diff)} | {mark} |")
    lines.append("")
    return "\n".join(lines)


def slowest_md(run: dict) -> str:
    meta = run.get("meta") or {}
    trace = (run.get("trace") or {}).get("trace_file")
    lines = [
        "# Five slowest leaf parts",
        "",
        f"**GPU:** {meta.get('gpu')}  |  **tag:** {meta.get('tag')}  |  **commit:** `{meta.get('commit')}`",
        "",
    ]
    for i, (name, r, pct) in enumerate(_five_slowest(run), 1):
        level = r.get("level")
        lines += [
            f"## {i}. `{name}` (level {level})",
            "",
            f"- **ms:** {_f(r['median'])}",
            f"- **% of step:** {_f(pct, 1)}%",
            f"- **why (placeholder):** bound unknown until a real GPU trace; evidence = region median from run JSON.",
            f"- **trace reference:** {trace or '(no trace on this run)'}",
            f"- **week-2 idea:** profile this part; check PARTS.md switch for a faster registry entry.",
            "",
        ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render / compare perfkit run JSON to Markdown.")
    ap.add_argument("run", help="Primary run JSON path")
    ap.add_argument("--compare", help="Earlier / other run JSON to compare against")
    ap.add_argument("--baseline", help="Write baseline comparison Markdown here")
    ap.add_argument("--slowest", help="Write five-slowest Markdown here")
    ap.add_argument("--tol-pct", type=float, default=None, help="default: report.tol_pct of the run's config")
    ap.add_argument("--gate-level", type=int, default=None, help="default: report.gate_level of the run's config")
    ap.add_argument("--abs-tol-ms", type=float, default=None, help="default: report.abs_tol_ms of the run's config")
    args = ap.parse_args(argv)

    run_path = Path(args.run)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    rep = run["config"]["report"]
    for key in ("tol_pct", "gate_level", "abs_tol_ms"):
        if getattr(args, key) is None:
            setattr(args, key, rep[key])
    md_path = run_path.with_suffix(".md")
    md_path.write_text(render(run), encoding="utf-8")
    print(f"[report] render -> {md_path}")

    if args.slowest:
        Path(args.slowest).write_text(slowest_md(run), encoding="utf-8")
        print(f"[report] slowest -> {args.slowest}")

    if args.compare:
        other = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        rows, ok, problems = compare(run, other, args.tol_pct, args.gate_level, args.abs_tol_ms)
        tags = ((run.get("meta") or {}).get("tag") or "this run", (other.get("meta") or {}).get("tag") or "against")
        print(f"\n[report] {tags[0]} vs {tags[1]} (ms)")
        for line in compare_lines(rows, ok, problems, ab_note(run, other), args.tol_pct, args.gate_level,
                                  args.abs_tol_ms, *tags):
            print(line)
        if args.baseline:
            Path(args.baseline).write_text(baseline_md(run, other, rows, ok, problems), encoding="utf-8")
            print(f"[report] baseline -> {args.baseline}")
        return 0 if ok else 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
