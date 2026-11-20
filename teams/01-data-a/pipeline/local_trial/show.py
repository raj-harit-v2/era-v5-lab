"""Print a run's totals, one line per stage, and any failed check.

  python teams/01-data-a/pipeline/local_trial/show.py <run_id> [out folder]      (default out folder: out/pipeline)

Reads <out>/<run_id>/pipeline_manifest.json from the repository root; exit code 1 if a check failed.
"""
import json
import sys
from pathlib import Path


def show_lines(manifest):
    """(lines, failed): the run's totals, a line per stage with its counts, and the failed checks."""
    m = json.loads(Path(manifest).read_text(encoding="utf-8"))
    lines = [f"{m['run_id']}: {m['totals']}"]
    for s in m["stages"]:
        counts = {k: v for k, v in s["counts"].items() if not isinstance(v, (dict, list))}
        lines.append(f"  {s['stage']:14}{s['mode']:7}{s['seconds']:>8}s  {counts}")
    failed = [c["check"] for c in m["checks"] if not c["ok"]]
    lines.append(f"  failed checks: {failed or 'none'}")
    return lines, bool(failed)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.exit(__doc__)
    manifest = Path(argv[1] if len(argv) > 1 else "out/pipeline") / argv[0] / "pipeline_manifest.json"
    if not manifest.is_file():
        sys.exit(f"show: {manifest} not found (run from the repository root, with the run's id)")
    lines, failed = show_lines(manifest)
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
