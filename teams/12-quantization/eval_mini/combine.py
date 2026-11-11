#!/usr/bin/env python3
"""Combine eval_mini runs made by different team members into one result set.

    python combine.py runs_bf16.zip runs_Q8_0-Q6_K.zip runs_Q5_K_M-Q4_K_M.zip ... --out combined/

Each input is a zip (or folder) written by eval_mini.ipynb: one sub-folder per format with summary.json and the
per-item *.samples.jsonl files, plus environment.json. A format is accepted only if its run matches the base run
(bf16) on everything that changes scores:

  model and revision, eval profile, seed, n_ctx, lm_eval version, backend (llama-cpp-python version),
  G9's run_eval_mini.py (sha256), LIMIT = None, and the full item count of every task.

A run is refused if any *.samples.jsonl row carries eval item text (a `target` or `response` field). Team 9's eval
firewall keeps item text out of the public repo, and notebooks made before that rule wrote it.

The hardware may differ (it is recorded per format). The notebook fingerprint (NOTEBOOK_VERSION) is compared too,
but runs made before it existed (the 28 Oct bf16 run) only get a warning. Fingerprints in SAME_SCORING count as equal. The same format in two inputs is an
error unless both give identical scores.

Writes to --out: one folder per format, provenance.json (who, where, how long), scores.csv / scores.md, and
paired.md (every format against the base, item by item, via paired.py).
"""
from __future__ import annotations

import argparse, json, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = {"arc_challenge": 500, "hellaswag": 400, "mmlu": 570, "gsm8k": 200, "truthfulqa_mc2": 200}  # G9's mini profile
MUST_MATCH = ["model", "model_revision", "profile", "seed", "n_ctx", "lm_eval", "backend", "g9_harness_sha256"]
ITEM_TEXT = {"target", "response"}   # eval firewall (Team 9): never in a result folder
# Notebook fingerprints whose scoring is the same, so their runs combine. Add a fingerprint only after checking that the
# change did not touch how an item is scored, and say what changed:
#   70829160c1bd  the six OLMoE quantized runs of 29 Oct
#   ec7db60966d6  + pinned installs, test_llamacpp_lm.py check (2) from the logit rows, a comment
#   dbeeed2c28c3  + no target/response in the sample rows (paired.py output is byte-identical with and without them)
SAME_SCORING = {"70829160c1bd", "ec7db60966d6", "dbeeed2c28c3"}


def same_version(v: str) -> str:
    return "same-scoring" if v in SAME_SCORING else v


def unpack(path: Path, tmp: Path) -> Path:
    if path.is_dir():
        return path
    dest = tmp / path.stem
    with zipfile.ZipFile(path) as z:
        z.extractall(dest)
    return dest


def runs_in(folder: Path):
    env_path = folder / "environment.json"
    env = json.loads(env_path.read_text()) if env_path.exists() else {}
    for summary in sorted(folder.glob("*/summary.json")):
        yield summary.parent, json.loads(summary.read_text()), env


def item_text_in(folder: Path) -> list[str]:
    """An error for the format folder if any of its sample rows has eval item text, else []."""
    bad = {}
    for f in sorted(folder.glob("*.samples.jsonl")):
        with open(f, encoding="utf-8") as fh:
            found = {k for line in fh if line.strip() for k in json.loads(line)} & ITEM_TEXT
        if found:
            bad[f.name] = sorted(found)
    if not bad:
        return []
    return [f"{len(bad)} sample file(s) carry eval item text ({', '.join(sorted({k for v in bad.values() for k in v}))}), "
            f"e.g. {next(iter(bad))}: written by a notebook older than the eval firewall. Rerun with the current "
            "notebook, or delete those fields from every row"]


def primary(summary: dict) -> dict[str, dict]:
    return {r["task"]: r for r in summary["records"] if r["primary"]}


def check(fmt: str, summary: dict, env: dict, ref_meta: dict, ref_env: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    meta = summary["run_meta"]
    for key in MUST_MATCH:
        if meta.get(key) != ref_meta.get(key):
            errors.append(f"{key} = {meta.get(key)!r}, base has {ref_meta.get(key)!r}")
    recs = primary(summary)
    for task, n in TASKS.items():
        r = recs.get(task)
        if r is None:
            errors.append(f"{task}: missing")
        elif r["n_items"] != n or r.get("limit") not in (None, 10 if task == "mmlu" else n):
            errors.append(f"{task}: n_items {r['n_items']} (limit {r.get('limit')}), expected the full {n}")
    if env.get("settings", {}).get("LIMIT") not in (None,):
        errors.append(f"run used LIMIT = {env['settings']['LIMIT']}: a test run, not combinable")
    v, ref_v = env.get("notebook_version"), ref_env.get("notebook_version")
    if v and ref_v and same_version(v) != same_version(ref_v):
        errors.append(f"notebook version {v}, base run used {ref_v}")
    elif not (v and ref_v):
        warnings.append(f"notebook version not recorded (this run: {v or '-'}, base: {ref_v or '-'}); "
                        "the settings above were checked instead")
    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", type=Path, help="zips or folders from eval_mini.ipynb")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base", default="bf16")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        found = []   # (format, folder, summary, env, source)
        for src in args.inputs:
            for folder, summary, env in runs_in(unpack(src, Path(tmp))):
                found.append((summary["run_meta"]["format"], folder, summary, env, src.name))
        bases = [f for f in found if f[0] == args.base]
        if not bases:
            sys.exit(f"no {args.base} run among the inputs: it is the reference every format is checked against")
        _, _, ref_summary, ref_env, ref_src = bases[0]
        ref_meta = ref_summary["run_meta"]

        accepted, problems = {}, []
        for fmt, folder, summary, env, src in found:
            errors, warnings = check(fmt, summary, env, ref_meta, ref_env)
            errors += item_text_in(folder)
            for w in warnings:
                print(f"warning {fmt} ({src}): {w}")
            if errors:
                problems.append(f"{fmt} ({src}): " + "; ".join(errors)); continue
            if fmt in accepted:
                same = {t: r["value"] for t, r in primary(summary).items()} == \
                       {t: r["value"] for t, r in primary(accepted[fmt][1]).items()}
                if not same:
                    problems.append(f"{fmt}: two runs with different scores ({accepted[fmt][3]} and {src}); keep one")
                continue
            accepted[fmt] = (folder, summary, env, src)
        versions = {same_version(env.get("notebook_version")) for _, (_, _, env, _) in accepted.items()
                    if env.get("notebook_version")}
        if len(versions) > 1:   # runs that carry a fingerprint must all carry the same one
            problems.append("runs come from different notebook versions: " + ", ".join(
                f"{fmt}={env.get('notebook_version')}" for fmt, (_, _, env, _) in accepted.items() if env.get("notebook_version")))
        if problems:
            sys.exit("NOT combined:\n  " + "\n  ".join(problems))

        args.out.mkdir(parents=True, exist_ok=True)
        provenance, rows = {}, []
        order = ["bf16", "Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]
        for fmt in sorted(accepted, key=lambda f: order.index(f) if f in order else 99):
            folder, summary, env, src = accepted[fmt]
            shutil.copytree(folder, args.out / fmt, dirs_exist_ok=True)
            provenance[fmt] = {"source": src, "run_by": env.get("run_by"), "hardware": summary["run_meta"].get("hardware"),
                               "notebook_version": env.get("notebook_version"),
                               "gpu_layers": summary["run_meta"].get("n_gpu_layers"),
                               "wall_clock_s": round(sum(r["wall_clock_s"] for r in primary(summary).values()))}
            recs = primary(summary)
            rows.append((fmt, {t: f"{100 * recs[t]['value']:.1f} ± {100 * (recs[t]['stderr'] or 0):.1f}" for t in TASKS}))
        (args.out / "provenance.json").write_text(json.dumps(provenance, indent=1))
        (args.out / "scores.csv").write_text("format," + ",".join(TASKS) + "\n" +
                                             "".join(f"{f}," + ",".join(c[t] for t in TASKS) + "\n" for f, c in rows))
        md = ["| Format | " + " | ".join(TASKS) + " |", "|---|" + "---|" * len(TASKS)]
        md += [f"| {f} | " + " | ".join(c[t] for t in TASKS) + " |" for f, c in rows]
        (args.out / "scores.md").write_text("\n".join(md) + "\n")
        print("\n".join(md) + "\n")
        subprocess.run([sys.executable, str(HERE / "paired.py"), str(args.out), "--base", args.base,
                        "--out", str(args.out / "paired.md")], check=True)
        print(f"\ncombined {len(accepted)} formats into {args.out}: {', '.join(provenance)}")


if __name__ == "__main__":
    main()
