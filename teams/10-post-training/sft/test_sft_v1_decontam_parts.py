"""Tests for sft_v1_decontam_parts.py: resume and refusal paths (no Team 9 tools needed)."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decontam_run as dr  # noqa: E402
import sft_v1_decontam_parts as dp  # noqa: E402


def _part(tmp_path, plain=b'{"id": "s/0", "text": "x"}\n'):
    gz = gzip.compress(plain, mtime=0)
    (tmp_path / "s.part0000.jsonl.gz").write_bytes(gz)
    return {"name": "s.part0000.jsonl.gz", "gz_bytes": len(gz), "gz_sha256": hashlib.sha256(gz).hexdigest(),
            "plain_sha256": hashlib.sha256(plain).hexdigest()}


def test_existing_ok_record_for_same_bytes_is_reused(tmp_path):
    part = _part(tmp_path)
    rec_dir = tmp_path / "out" / part["name"]
    rec_dir.mkdir(parents=True)
    (rec_dir / "s.record.json").write_text(json.dumps({"ok": True, "inputs": [{"sha256": part["plain_sha256"]}]}))
    assert dp.one_part("s", part, str(tmp_path), str(tmp_path / "out"), "unused")["status"] == "reused"
    (rec_dir / "s.record.json").write_text(json.dumps({"ok": True, "inputs": [{"sha256": "0" * 64}]}))
    assert not dp.done_already(rec_dir / "s.record.json", part["plain_sha256"])


def test_gz_bytes_that_differ_from_the_record_are_refused(tmp_path):
    part = _part(tmp_path)
    part["gz_sha256"] = "0" * 64
    with pytest.raises(dr.RunError):
        dp.one_part("s", part, str(tmp_path), str(tmp_path / "out"), "unused")


def test_decompressed_bytes_that_differ_are_refused_and_tmp_removed(tmp_path):
    part = _part(tmp_path)
    part["plain_sha256"] = "0" * 64
    with pytest.raises(dr.RunError):
        dp.one_part("s", part, str(tmp_path), str(tmp_path / "out"), "unused")
    assert not list((tmp_path / "out" / "tmp").iterdir())
