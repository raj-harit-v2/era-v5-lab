#!/usr/bin/env python3
"""combine.py must refuse a run whose sample rows carry eval item text (Team 9 eval firewall).

    python test_combine.py            # exits non-zero if a check fails
    python -m pytest test_combine.py

Copies the committed bf16 and Q8_0/Q6_K runs to a temp folder, combines them (must work), puts a `target` field into
one Q8_0 row and combines again (must stop, naming the problem). The text added is a placeholder, not an eval item.

Also: runs from notebook fingerprints that score the same (SAME_SCORING) combine; an unknown fingerprint does not.
"""
from __future__ import annotations

import json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "results" / "raw"


def combine(tmp: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HERE / "combine.py"), str(tmp / "runs_bf16"), str(tmp / "runs_Q8_0-Q6_K"),
                           "--out", str(tmp / "out")], capture_output=True, text=True)


def with_version(tmp: Path, version: str) -> subprocess.CompletedProcess:
    """Combine bf16 + Q8_0/Q6_K (fingerprint 70829160c1bd) + Q5_K_M/Q4_K_M relabelled to `version`."""
    for name in ("runs_bf16", "runs_Q8_0-Q6_K", "runs_Q5_K_M-Q4_K_M"):
        shutil.copytree(RAW / name, tmp / name)
    env = tmp / "runs_Q5_K_M-Q4_K_M" / "environment.json"
    e = json.loads(env.read_text()); e["notebook_version"] = version
    env.write_text(json.dumps(e))
    return subprocess.run([sys.executable, str(HERE / "combine.py"), *(str(tmp / n) for n in (
        "runs_bf16", "runs_Q8_0-Q6_K", "runs_Q5_K_M-Q4_K_M")), "--out", str(tmp / "out")], capture_output=True, text=True)


def test_notebook_fingerprints():
    for version, should_combine in (("dbeeed2c28c3", True), ("ec7db60966d6", True), ("000000000000", False)):
        with tempfile.TemporaryDirectory() as t:
            r = with_version(Path(t), version)
            assert (r.returncode == 0) == should_combine, f"{version}: {r.stderr[-800:]}"
            if not should_combine:
                assert "different notebook versions" in r.stderr, r.stderr[-800:]


def test_refuses_item_text():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for name in ("runs_bf16", "runs_Q8_0-Q6_K"):
            shutil.copytree(RAW / name, tmp / name)
        ok = combine(tmp)
        assert ok.returncode == 0, ok.stderr[-1500:]

        victim = next((tmp / "runs_Q8_0-Q6_K" / "Q8_0").glob("*.samples.jsonl"))
        lines = victim.read_text().splitlines()
        row = json.loads(lines[0]); row["target"] = "placeholder"
        victim.write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n")
        shutil.rmtree(tmp / "out")
        bad = combine(tmp)
        assert bad.returncode != 0, "combine.py accepted a row with a target field"
        assert "eval item text" in bad.stderr and victim.name in bad.stderr, bad.stderr[-1500:]


if __name__ == "__main__":
    test_refuses_item_text()
    test_notebook_fingerprints()
    print("PASS: combine.py refuses a row with item text and mixes only fingerprints that score the same")
