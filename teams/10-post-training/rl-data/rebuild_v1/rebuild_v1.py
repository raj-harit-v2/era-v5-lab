"""Rebuild RL data v1 and its Team 9 pool files from pinned bytes, and check every output against its recorded sha256.

    python rl-data/rebuild_v1/rebuild_v1.py --cc-dir <code_contests@802411c3>/data --math-dir <hendrycks_math@21a56338> \
        --math500 <MATH-500 test.jsonl> --g9-tools <Team 9 teams/09-evaluation/decontam @ b470b4c0> --out <run dir>

Inputs are named in `pins_v1.json` (file names, sizes, sha256; no local paths). The four step scripts next to this file
(`verify_pins.py`, `build_v1.py`, `math500_guard.py`, `assemble_v1.py`) are byte copies of the 11 Nov scripts that
produced the recorded hashes; `pins_v1.json` holds their sha256 and this driver refuses a changed copy. The driver:
  1. stages the inputs those scripts read: `source_manifest.cc-pinned.json` and `math_pin.json`, with paths resolved
     under --cc-dir / --math-dir for this run only, and checks the MATH-500 file;
  2. runs pins -> build -> decontam (`sft/decontam_run.py`, both sets) -> MATH-500 guard -> assemble, in --out;
  3. writes the pool files ({id, text}, for Team 9's `decontam_check.py --id-field id`): the full v1 pools and the
     close pools (`rl_v1_close.py` flags: code pool, MATH reserved part);
  4. compares every output with `expected` in `pins_v1.json` and exits 1 on any difference.
With the evaluation-firewall lists (`--rl-heldout-ids`, `--sft-heldout-match-ids`; private, pinned by sha256 under
`firewall` in `pins_v1.json`) step 3 also writes the RL training pool and the RL held-out part (lead, 16 Nov 2026); the
close pool file is unchanged. Without them those two outputs are reported missing.
CPU only; network is never used. Measured: about 90 s on an Apple M1 Pro. Outputs hold dataset text: keep them out of Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RLDATA = HERE.parent
TEAM = RLDATA.parent
PINS = HERE / "pins_v1.json"
STEPS = ("verify_pins.py", "build_v1.py", "math500_guard.py", "assemble_v1.py")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def check_steps(pins: dict, here: Path = HERE) -> list[str]:
    """Names of step scripts whose bytes differ from the recorded copies."""
    return [n for n in STEPS if sha256_file(here / n) != pins["step_scripts_sha256"][n]]


def stage(pins: dict, cc_dir: Path, math_dir: Path, out: Path) -> tuple[Path, Path]:
    """Write the two input records the step scripts read, in their 11 Nov layout, with this run's absolute paths."""
    cc = pins["code_contests"]
    files = [{"name": f["name"], "rows": f["rows"], "sha256": f["sha256"], "bytes": f["bytes"],
              "path": str((cc_dir / f["file"]).resolve())} for f in cc["files"]]
    manifest = {"schema": "g10-ocr2-source-manifest/1", "note": "staged by rebuild_v1.py from pins_v1.json for one run",
                "sources": {"code_contests/train": {"repo": cc["repo"], "revision": cc["revision"], "split": "train",
                                                    "total_rows": cc["total_rows"], "files": files}},
                "pins": {"code_contests": {"repo": cc["repo"], "revision": cc["revision"],
                                           "hub_train_files": [{"name": f"data/{f['file']}", "bytes": f["hub_bytes"],
                                                                "hub_lfs_sha256": f["hub_lfs_sha256"]} for f in cc["files"]]}}}
    out.mkdir(parents=True, exist_ok=True)
    m_path, p_path = out / "source_manifest.cc-pinned.json", out / "math_pin.json"
    m_path.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    p_path.write_text(json.dumps(pins["hendrycks_math"], indent=1) + "\n", encoding="utf-8")
    return m_path, p_path


def write_pools(out: Path, effort_manifest: Path, rl_heldout: set | None = None, sft_heldout_match: set | None = None) -> dict:
    """Pool files {id, text}: v1 pools (text rows of the v1 ids), close pools (rl_v1_close flags) and, with the firewall
    lists, the training pool and the held-out part."""
    sys.path.insert(0, str(RLDATA))
    import rl_v1_close  # noqa: PLC0415

    def rows(p):
        return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]

    cc, math = rows(out / "out/v1/cc.jsonl"), rows(out / "out/v1/math.jsonl")
    body, private = rl_v1_close.close(cc, math, json.loads(effort_manifest.read_text()),
                                      rl_heldout=rl_heldout, sft_heldout_match=sft_heldout_match)
    pool = out / "pool"
    pool.mkdir(exist_ok=True)
    plan = {"rl-code-code-contests-noncf.v1.pool.jsonl": ("out/cc_text.jsonl", {t["id"] for t in cc}),
            "rl-math-hendrycks-math-train.v1.pool.jsonl": ("out/math_text.jsonl", {t["id"] for t in math}),
            "rl-code-v1-close.pool.jsonl": ("out/cc_text.jsonl", private["code_pool_ids.txt"]),
            "rl-math-v1-reserved.pool.jsonl": ("out/math_text.jsonl", private["math_reserved_ids.txt"])}
    if "code_train_pool_ids.txt" in private:
        plan["rl-code-v1-train.pool.jsonl"] = ("out/cc_text.jsonl", private["code_train_pool_ids.txt"])
        plan["rl-code-v1-heldout.pool.jsonl"] = ("out/cc_text.jsonl", private["rl_heldout_v1_ids.txt"])
    for name, (src, keep) in plan.items():
        lines = [x for x in open(out / src, encoding="utf-8") if json.loads(x)["id"] in keep]
        assert len(lines) == len(keep), (name, len(lines), len(keep))
        (pool / name).write_text("".join(lines), encoding="utf-8")
    return body


def compare(expected: dict, out: Path) -> dict:
    got = {rel: sha256_file(out / rel) if (out / rel).is_file() else None for rel in expected}
    return {rel: {"expected": expected[rel], "got": got[rel]} for rel in expected if got[rel] != expected[rel]}


def run(cmd: list, cwd: Path, log: Path) -> None:
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run([str(c) for c in cmd], cwd=cwd, stdout=f, stderr=subprocess.STDOUT,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode:
        raise SystemExit(f"rebuild_v1: step failed ({r.returncode}): {' '.join(str(c) for c in cmd[:3])} ...; see {log}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cc-dir", type=Path, required=True, help="folder holding the 39 code_contests train parquets")
    ap.add_argument("--math-dir", type=Path, required=True, help="hendrycks_math root (<subject>/train-*.parquet)")
    ap.add_argument("--math500", type=Path, required=True, help="HuggingFaceH4/MATH-500 test.jsonl")
    ap.add_argument("--g9-tools", type=Path, required=True, help="Team 9 teams/09-evaluation/decontam at b470b4c0")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--rl-heldout-ids", type=Path, help="private: the official RL held-out task ids (pinned in pins_v1.json)")
    ap.add_argument("--sft-heldout-match-ids", type=Path, help="private: pool tasks matching the SFT held-out split (pinned)")
    a = ap.parse_args(argv)
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    bad = check_steps(pins)
    if bad:
        print(f"rebuild_v1: step scripts differ from the recorded copies: {bad}", file=sys.stderr)
        return 2
    if sha256_file(a.math500) != pins["math500"]["sha256"]:
        print("rebuild_v1: the MATH-500 file differs from its pin", file=sys.stderr)
        return 2
    lists = {}
    for key, path in (("rl_heldout_ids", a.rl_heldout_ids), ("sft_heldout_match_ids", a.sft_heldout_match_ids)):
        if path is None:
            continue
        want = (pins.get("firewall") or {}).get(key, {}).get("sha256")
        if sha256_file(path) != want:
            print(f"rebuild_v1: {path.name} is not the pinned {key} list", file=sys.stderr)
            return 2
        lists[key] = {x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()}
    out = a.out.resolve()
    m_path, p_path = stage(pins, a.cc_dir, a.math_dir, out)
    (out / "logs").mkdir(exist_ok=True)
    (out / "decontam").mkdir(exist_ok=True)
    t0, times = time.monotonic(), {}
    py = a.python
    run([py, "-I", "-B", HERE / "verify_pins.py", m_path, a.math_dir.resolve(), p_path, out / "pins_verified.json"], out, out / "logs/pins.log")
    times["pins"] = time.monotonic() - t0
    run([py, "-I", "-B", HERE / "build_v1.py", RLDATA, out / "pins_verified.json", m_path, a.math_dir.resolve(), p_path, out / "out"],
        out, out / "logs/build.log")
    times["build"] = time.monotonic() - t0
    for set_id, src in (("rl-code-code-contests-noncf", "out/cc_text.jsonl"), ("rl-math-hendrycks-math-train", "out/math_text.jsonl")):
        run([py, TEAM / "sft/decontam_run.py", "--set", set_id, "--input", out / src, "--out-dir", out / "decontam",
             "--tools", a.g9_tools.resolve()], out, out / f"logs/decontam_{set_id}.log")
    times["decontam"] = time.monotonic() - t0
    run([py, "-I", "-B", HERE / "math500_guard.py", out / "out/math_tasks.jsonl", a.math500.resolve(), out / "out/math500_guard.json"],
        out, out / "logs/math500_guard.log")
    run([py, "-I", "-B", HERE / "assemble_v1.py"], out, out / "logs/assemble.log")
    times["assemble"] = time.monotonic() - t0
    body = write_pools(out, TEAM / "eval/effort_manifest.json", lists.get("rl_heldout_ids"), lists.get("sft_heldout_match_ids"))
    diff = compare(pins["expected"], out)
    summary = {"outputs_checked": len(pins["expected"]), "mismatches": diff, "ok": not diff,
               "code_pool": body["parts"]["code"]["pool_tasks"], "math_reserved": body["parts"]["math"]["reserved_tasks"],
               **({"code_train_pool": body["parts"]["code"]["train_pool_tasks"], "rl_heldout": body["parts"]["heldout"]["tasks"]}
                  if "heldout" in body["parts"] else {}),
               "seconds": {k: round(v, 1) for k, v in times.items()} | {"total": round(time.monotonic() - t0, 1)}}
    (out / "rebuild_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
