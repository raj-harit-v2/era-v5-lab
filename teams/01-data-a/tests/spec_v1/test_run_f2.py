"""Unit tests for run_f2.py, F2 alone on deduped Parquet files. The flagged doc carries G9's lab canary, built at run
time from lab_canary.py: no benchmark text is in this file. The set is cut to one benchmark (gsm8k) so it loads in
seconds; the canary check does not depend on it.

  python -m pytest tests/spec_v1
"""
import subprocess
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq

SPEC = Path(__file__).resolve().parents[2] / "spec_v1"
sys.path.insert(0, str(SPEC))
import run_f2

sys.path.insert(0, str(run_f2.G9))
from lab_canary import LAB_CANARY

DOCS = [{"doc_id": "a", "text": "plain text, nothing from a benchmark", "lane": "code"},
        {"doc_id": "b", "text": f"some text {LAB_CANARY} more text", "lane": "code"},
        {"doc_id": "c", "text": None, "lane": "code"}]


@pytest.fixture
def src(tmp_path):
    path = tmp_path / "in" / "code-go" / "part-00000.parquet"
    path.parent.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(DOCS), path)
    return path


def test_drops_flagged_keeps_rest_unchanged(tmp_path, src):
    fp = run_f2.fingerprints(("gsm8k",))
    dst = tmp_path / "out" / "code-go" / "part-00000.parquet"
    r = run_f2.run_file(src, dst, fp, "x")
    assert (r["rows"], r["kept"], r["dropped_by_f2"], r["errors"]) == (3, 2, 1, [])
    assert r["dropped"][0]["doc_id"] == "b" and r["dropped"][0]["items"] == ["era-v5-lab:canary"]
    assert r["set_sha256"] == run_f2.SET_SHA256
    out = pq.read_table(dst)
    assert out.schema == pq.read_schema(src)
    assert out.column("doc_id").to_pylist() == ["a", "c"]
    assert out.column("text").to_pylist() == [DOCS[0]["text"], None]
    report = dst.with_name(dst.name + ".f2.json").read_text(encoding="utf-8")
    assert LAB_CANARY not in report and "plain text" not in report  # doc_ids and offsets only
    assert not list(tmp_path.rglob("*.tmp"))
    mtime = dst.stat().st_mtime_ns
    assert run_f2.run_file(src, dst, fp, "x")["kept"] == 2 and dst.stat().st_mtime_ns == mtime  # done before: skipped


def test_refuses_out_inside_inputs(tmp_path, src):
    p = subprocess.run([sys.executable, "-I", str(SPEC / "run_f2.py"), "--inputs", str(tmp_path / "in"), "--out", str(tmp_path / "in" / "final")],
                       capture_output=True, text=True)
    assert p.returncode == 1 and "overlap" in p.stderr


def test_refuses_another_set(tmp_path, monkeypatch):
    (tmp_path / "SHA256SUMS").write_text("x\n", encoding="utf-8")
    monkeypatch.setenv("F2_FINGERPRINTS", str(tmp_path))
    run_f2.fingerprints.cache_clear()
    with pytest.raises(ValueError, match="not the pinned"):
        run_f2.fingerprints()
    run_f2.fingerprints.cache_clear()
