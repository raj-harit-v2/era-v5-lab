"""Unit tests for run_clean.py, the runner that cleans one pack with clean.py: it stops on a pack clean.py has no rules for,
before reading or writing anything, and its summary records which clean.py ran. Every text here is made up; none comes
from a pack.

  python -m pytest spec_v1/tests
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq

SPEC = Path(__file__).resolve().parents[1]
RUN = SPEC / "run_clean.py"
sys.path.insert(0, str(SPEC))
import clean as c

ZWSP = chr(0x200B)  # written as a number: a raw zero-width space in code is invisible
DOCS = [("d1", "Area of a circle.\n"), ("d2", f"Area{ZWSP} of a circle.\n"), ("d3", "Subscribe to our newsletter\n")]


def pack_file(folder, name, pack_id=None):
    """A made-up English pack, <name>.parquet, with a pack_id column only when pack_id is given."""
    rows = [{"doc_id": d, "text": t, "url": "", "lang_label": "en", **({} if pack_id is None else {"pack_id": pack_id})} for d, t in DOCS]
    path = folder / f"{name}.parquet"
    pq.write_table(pa.Table.from_pylist(rows), path)
    return path


def run(pack, out):
    return subprocess.run([sys.executable, "-I", str(RUN), "--pack", str(pack), "--out", str(out)], capture_output=True, text=True)


def test_a_known_pack_is_cleaned_and_the_summary_names_its_clean_py(tmp_path):
    pytest.importorskip("ftfy")  # the English rules include DA-A3-002
    expected = [(d, *c.clean({"doc_id": d, "text": t, "url": "", "lang_label": "en", "pack_id": "en-dclm"})) for d, t in DOCS]
    assert [a for _, a, _ in expected] == ["keep", "fix", "drop"]  # the made-up docs take every path of the runner
    r = run(pack_file(tmp_path, "en-dclm"), tmp_path / "out")
    assert r.returncode == 0, r.stderr
    raw = (tmp_path / "out" / "en-dclm_summary.json").read_text(encoding="utf-8")
    summary = json.loads(raw)
    assert (summary["pack"], summary["pack_id"], summary["family"], summary["rows"]) == ("en-dclm.parquet", "en-dclm", "english", 3)
    assert (summary["actions"], summary["dropped"], summary["errors"]) == ({"keep": 1, "fix": 1, "drop": 1}, ["d3"], [])
    assert summary["clean_py_sha256"] == hashlib.sha256((SPEC / "clean.py").read_bytes()).hexdigest()
    assert "circle" not in raw and "newsletter" not in raw  # IDs and counts only, never text
    kept = pq.read_table(tmp_path / "out" / "en-dclm_clean.parquet").to_pylist()
    assert [(row["doc_id"], row["text"], row["pack_id"]) for row in kept] == [(d, t, "en-dclm") for d, a, t in expected if a != "drop"]


@pytest.mark.parametrize("pack_id", [None, "en-fineweb-edu-v2", "en-fineweb-edu"])
def test_an_unknown_pack_stops_before_anything_is_written(tmp_path, pack_id):
    # A renamed copy of a known pack: without a pack_id column, with the new name in it, or with the old name in it.
    r = run(pack_file(tmp_path, "en-fineweb-edu-v2", pack_id), tmp_path / "out")
    assert r.returncode == 1
    assert f"'en-fineweb-edu-v2' is not one of the {len(c._FAMILY)} packs clean.py has rules for" in r.stderr
    assert all(p in r.stderr for p in c._FAMILY)  # the message lists the names that work
    assert not (tmp_path / "out").exists()


def test_the_pack_name_is_checked_before_the_file_is_read(tmp_path):
    bad = tmp_path / "en-fineweb-edu-v2.parquet"
    bad.write_bytes(b"not a parquet file")
    r = run(bad, tmp_path / "out")
    assert r.returncode == 1 and "is not one of the" in r.stderr and "Traceback" not in r.stderr


def test_a_pack_id_that_does_not_match_the_file_name_stops_the_run(tmp_path):
    r = run(pack_file(tmp_path, "en-dclm", "en-fineweb-edu"), tmp_path / "out")
    assert r.returncode == 1 and "has pack_id 'en-fineweb-edu'" in r.stderr
    assert not (tmp_path / "out").exists()
