"""Tests for minhash_sizing.py: a failed factor exits nonzero and keeps its reports; every run measures from scratch
(a new output folder, an existing one refused, no reused parts); requested and actual scale are recorded and an
undersized factor is marked. Made-up text only; the inputs and outputs live in a temporary folder under out/.

  python3 -B -m pytest dedup/tests/test_minhash_sizing.py
"""
import csv
import json
import os
import random
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("pygments")
pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq  # noqa: E402

DEDUP = Path(__file__).resolve().parents[1]
REPO = DEDUP.parents[2]
SIZING = DEDUP / "minhash_sizing.py"
WORDS = "river stone bridge garden market window letter silver forest engine harbour lantern meadow pencil".split()


@pytest.fixture
def area():
    root = REPO / "out" / f"test_minhash_sizing_{uuid.uuid4().hex[:8]}"
    rng = random.Random(1)
    for pack in ("en-a", "en-b"):
        p = root / "inputs" / "train" / pack / "part-00000.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        base = " ".join(rng.choice(WORDS) for _ in range(80))
        docs = [{"pack_id": pack, "doc_id": f"d{i}", "text": base if i % 5 == 0 else
                 " ".join(rng.choice(WORDS) for _ in range(80))} for i in range(40)]
        pq.write_table(pa.Table.from_pylist(docs), p)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def run(area, *args, sample=40, settings=None):
    rel = area.relative_to(REPO).as_posix()
    cmd = [sys.executable, str(SIZING), "--inputs", f"{rel}/inputs", "--workers", "1", *args]
    if settings:
        cmd += ["--settings", settings]
    env = {**os.environ, "MH_SAMPLE_DOCS": str(sample)}
    return subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)


def rows(folder):
    with open(folder / "sizing.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_complete_run_records_requested_and_actual_scale_and_marks_undersized(area):
    out = area / "m1"
    r = run(area, "--factors", "1", "4", "--out", out.relative_to(REPO).as_posix())
    assert r.returncode == 0, r.stdout + r.stderr
    got = rows(out)
    assert [x["factor"] for x in got] == ["1.0", "4.0"]
    one, four = got
    assert one["requested_documents"] == "40" and one["undersized"] == "False" and one["status"] == "complete"
    assert four["requested_documents"] == "160" and four["documents"] == "80"     # only 80 documents are staged
    assert four["undersized"] == "True" and four["actual_factor"] == "2.0"
    assert one["parts_reused"] == "0" and four["parts_reused"] == "0"
    assert "UNDERSIZED" in r.stdout
    s = json.loads((out / "sizing.json").read_text())
    assert s["projection_whole_staged_inputs"]["from_factor_undersized"] is True


def test_an_existing_output_folder_is_refused(area):
    out = area / "m2"
    assert run(area, "--factors", "1", "--out", out.relative_to(REPO).as_posix()).returncode == 0
    again = run(area, "--factors", "1", "--out", out.relative_to(REPO).as_posix())
    assert again.returncode != 0 and "exists" in (again.stdout + again.stderr)


def test_default_output_folders_are_new_for_every_run(area, tmp_path):
    first = run(area, "--factors", "1")
    assert first.returncode == 0
    folder = REPO / first.stdout.split("measurements in ", 1)[1].split()[0]
    try:
        assert rows(folder)[0]["parts_reused"] == "0"
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        try:
            folder.parent.rmdir()          # out/minhash_sizing, if this test made it and nothing else is in it
        except OSError:
            pass


def test_a_failed_factor_exits_nonzero_and_keeps_its_reports(area):
    bad = json.loads((DEDUP / "minhash_overlap_partial.json").read_text())
    bad["max_output_mb"] = 0.000001                     # every run is over this: overlap fails at its end
    settings = area / "bad_settings.json"
    settings.write_text(json.dumps(bad))
    out = area / "m3"
    r = run(area, "--factors", "1", "--out", out.relative_to(REPO).as_posix(),
            settings=settings.relative_to(REPO).as_posix())
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAILED" in r.stdout
    got = rows(out)
    assert got[0]["status"].startswith("failed") and got[0]["exit_code"] != "0"
    assert (out / "sizing.json").is_file()
