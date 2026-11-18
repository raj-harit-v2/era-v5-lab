"""Check every input file of RL data v1 against its pin before use: size and sha256.

code_contests: each of the 39 train parquets against source_manifest.cc-pinned.json (files[].sha256/bytes) AND the
manifest's pins.code_contests.hub_train_files (Hub LFS oid at revision 802411c3).
MATH: each of the 7 train parquets against the Hub tree record at revision 21a56338 (queried 11 Nov 2026, stored in
math_pin.json next to this script).

    python verify_pins.py <cc-pinned-manifest.json> <math-dir> <math_pin.json> <out.json>
Exit 0 only if every file matches.
"""
import hashlib
import json
import sys
from pathlib import Path


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main(manifest, math_dir, math_pin, out):
    m = json.loads(Path(manifest).read_text())
    src = m["sources"]["code_contests/train"]
    hub = {Path(x["name"]).stem: x for x in m["pins"]["code_contests"]["hub_train_files"]}
    rows, ok = [], True
    for f in src["files"]:
        p = Path(f["path"])
        size, digest = p.stat().st_size, sha256(p)
        h = hub[f["name"]]
        good = size == f["bytes"] == h["bytes"] and digest == f["sha256"] == h["hub_lfs_sha256"]
        ok &= good
        rows.append({"source": "code_contests", "file": p.name, "bytes": size, "sha256": digest, "ok": good,
                     "revision": src["revision"]})
    mp = json.loads(Path(math_pin).read_text())
    for rel, rec in mp["files"].items():
        p = Path(math_dir) / rel
        size, digest = p.stat().st_size, sha256(p)
        good = size == rec["bytes"] and digest == rec["lfs_sha256"]
        ok &= good
        rows.append({"source": "hendrycks_math", "file": rel, "bytes": size, "sha256": digest, "ok": good,
                     "revision": mp["revision"]})
    Path(out).write_text(json.dumps({"all_ok": ok, "files": rows}, indent=1))
    n_cc = sum(r["source"] == "code_contests" for r in rows)
    print(json.dumps({"all_ok": ok, "code_contests_files": n_cc, "math_files": len(rows) - n_cc,
                      "bad": [r["file"] for r in rows if not r["ok"]]}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
