"""Stand-in for clean_job.py, overlap.py and dedup.py in the runner's tests.

It takes the command line the runner gives them (--config, and for clean one --only per part), copies the folder named by
"fixture" in the config to the output folder, and prints what it was given (the runner's log keeps it). The output folder is
the config's "out" (overlap, dedup) or "output_root" (clean), relative to the working directory, the repository root, as the
real scripts read it. Like the real clean job it refuses an output folder that already exists.

For clean it also writes the job_summary.json clean_job.py would write for the folder it copied (every part with its rows and
sha256, expected_parts from the config), unless the environment says otherwise. FAKE_CLEAN_DAMAGE, one of:
  none      write no job_summary.json
  errors    the summary reports errors
  parts     one part fewer done than the run expects
  manifest  the job read another manifest
  rows      the output rows do not add up to the input rows
  renamed   a part on disk has another name than the summary gives it (same rows)
  sha       the first part's sha256 in the summary is not the file's
"""
import argparse, hashlib, json, os, shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--config", type=Path, required=True)
ap.add_argument("--only", action="append", default=[])
a = ap.parse_args()
cfg = json.loads(a.config.read_text(encoding="utf-8"))
out = Path(cfg.get("out") or cfg["output_root"])
shutil.copytree(cfg["fixture"], out)
if "output_root" in cfg and os.environ.get("FAKE_CLEAN_DAMAGE") != "none":
    import pyarrow.parquet as pq
    damage = os.environ.get("FAKE_CLEAN_DAMAGE", "")
    parts = [{"part": f.relative_to(out).as_posix(), "output_rows": pq.read_metadata(f).num_rows,
              "output_sha256": hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(out.rglob("*.parquet"))]
    rows = sum(p["output_rows"] for p in parts)
    summary = {"completed_parts": len(parts), "expected_parts": sum((cfg.get("expected_parts") or {}).values()) or len(parts),
               "input_rows": rows, "output_rows": rows, "actions": {"keep": rows}, "errors": 0,
               "manifest_sha256": cfg.get("manifest_sha256"), "scope": "full manifest", "parts": parts}
    if damage == "errors":
        summary["errors"] = 2
    elif damage == "parts":
        summary["completed_parts"] -= 1
    elif damage == "manifest":
        summary["manifest_sha256"] = "f" * 64
    elif damage == "rows":
        summary["output_rows"] += 1
    elif damage == "renamed":
        (out / parts[0]["part"]).rename(out / parts[0]["part"].replace("part-00000", "part-00009"))
    elif damage == "sha":
        parts[0]["output_sha256"] = "0" * 64
    (out / "job_summary.json").write_text(json.dumps(summary), encoding="utf-8")
print(json.dumps({"config": a.config.as_posix(), "out": out.as_posix(), "input_root": cfg.get("input_root"), "only": a.only,
                  "keys": {k: cfg.get(k) for k in ("inputs", "out", "results")}}))
