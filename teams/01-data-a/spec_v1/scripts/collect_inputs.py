"""Copy the latest code labels.csv and medicine.md of every open PR into a checkout. Same result as fetch_medicines.py --include-open-prs.

  python -I collect_inputs.py <repo> <checkout> <open_prs.json>

Needs origin/main and the PR heads as pr/<number> in <repo>, and the API list of open PRs in open_prs.json.
"""
import json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
REPO, WT, PRS = sys.argv[1], Path(sys.argv[2]), json.load(open(sys.argv[3], encoding="utf-8"))
pat = re.compile(r"^diagnosis/submissions/(code-[^/]+)/([^/]+)/(labels\.csv|medicine\.md)$")
def git(*a, **k): return subprocess.run(["git", "-C", REPO, *a], capture_output=True, **k)
latest = {}
for p in PRS:
    r = git("diff", "--name-only", f"origin/main...pr/{p['number']}", text=True)
    if r.returncode: continue
    for f in r.stdout.split():
        m = pat.match(f)
        if m and (m.groups() not in latest or (p["updated_at"], p["number"]) > latest[m.groups()][0]):
            latest[m.groups()] = ((p["updated_at"], p["number"]), f)
for (pack, h, name), ((_, n), f) in sorted(latest.items()):
    raw = git("show", f"pr/{n}:{f}", check=True).stdout
    dst = (WT / f) if name == "labels.csv" else (WT / "teams/01-data-a/medicines/submissions" / pack / h / name)
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(raw)
d = defaultdict(list)
for (pack, h, name), ((_, n), f) in sorted(latest.items()): d[pack].append(f"{h}:{'L' if name == 'labels.csv' else 'M'}#{n}")
for k, v in d.items(): print(k, " ".join(v))
