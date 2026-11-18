"""Tests for sft_v1_admit.py (synthetic rows only: ids and token id lists, no dataset text)."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sft_v1_admit as adm  # noqa: E402

SET = "sft-test-set"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_set(tmp: Path, lengths_per_part, decision="allowed (test)"):
    parts_dir = tmp / "parts"
    parts_dir.mkdir()
    parts, all_plain, n, tokens = [], b"", 0, 0
    for k, lengths in enumerate(lengths_per_part):
        plain = b"".join(json.dumps({"id": f"{SET}/{n + j}", "input_ids": [1] * L}).encode() + b"\n"
                         for j, L in enumerate(lengths))
        n += len(lengths)
        tokens += sum(lengths)
        name = f"{SET}.part{k:04d}.jsonl.gz"
        gz = gzip.compress(plain, mtime=0)
        (parts_dir / name).write_bytes(gz)
        parts.append({"name": name, "gz_bytes": len(gz), "gz_sha256": _sha(gz),
                      "plain_bytes": len(plain), "plain_sha256": _sha(plain)})
        all_plain += plain
    record = {"set": SET, "scope": "full", "decision": decision, "parts": parts, "rows_out": n,
              "content_sha256": _sha(all_plain), "tokenizer_sha256": "t" * 64, "checks": {"tokens": tokens}}
    rec_path = tmp / f"{SET}.full.record.json"
    rec_path.write_text(json.dumps(record))
    return rec_path, parts_dir, record


def decon_record(tmp: Path, name: str, input_shas, flagged=(), canary=(), ok=True, set_id=SET,
                 set_sha=adm.PINNED_SET_SHA256):
    r = {"set": set_id, "set_sha256": set_sha, "scope": "full set", "ok": ok,
         "recheck_on_clean": {"flagged": 0}, "flagged": {i: {} for i in flagged},
         "canary": {"hits": [{"doc_id": i} for i in canary]}, "rows_flagged": len(flagged),
         "rows_canary": len(canary), "by_benchmark": {"hle": len(flagged)} if flagged else {},
         "inputs": [{"name": "x", "sha256": s} for s in input_shas]}
    p = tmp / name
    p.write_text(json.dumps(r))
    return p


def test_length_heldout_and_decontam_exclusions(tmp_path):
    rec, parts, record = make_set(tmp_path, [[10, 40000, 20], [32768, 32769, 5]])
    dec = decon_record(tmp_path, "d.json", [record["content_sha256"]], flagged=[f"{SET}/0"], canary=[f"{SET}/5"])
    held = tmp_path / "held.jsonl"
    held.write_text(json.dumps({"id": f"{SET}/2"}) + "\n" + f"{SET}/0\n")
    s = adm.admit(rec, parts, tmp_path / "out", decontam=[dec], heldout=[held], max_len=32768)
    assert s["status"] == "admissible"
    assert s["excluded_each"] == {"decontam": 2, "heldout": 2, "over_max_len": 2}
    assert s["rows_in"] == 6 and s["rows_kept"] == 1 and s["tokens_kept"] == 32768  # row 3 sits exactly at the limit
    kept = (tmp_path / "out" / f"{SET}.kept_ids.txt").read_text().split()
    assert kept == [f"{SET}/3"]
    excl = [json.loads(x) for x in (tmp_path / "out" / f"{SET}.excluded.jsonl").read_text().splitlines()]
    assert {e["id"]: e["reasons"] for e in excl}[f"{SET}/0"] == ["decontam", "heldout"]


def test_no_decontam_is_pending_and_reserved_is_not_admitted(tmp_path):
    rec, parts, _ = make_set(tmp_path, [[5, 6]], decision="TSAI reserves")
    s = adm.admit(rec, parts, tmp_path / "out")
    assert s["status"] == "licence_not_admitted+decontam_pending"
    assert s["rows_kept"] == 2 and s["decontam"]["complete"] is False


def test_partial_decontam_coverage_by_part(tmp_path):
    rec, parts, record = make_set(tmp_path, [[5], [6], [7]])
    dec = decon_record(tmp_path, "d.json", [record["parts"][1]["plain_sha256"]])
    s = adm.admit(rec, parts, tmp_path / "out", decontam=[dec])
    assert s["decontam"]["covers"] == "1 of 3 parts" and s["status"] == "decontam_pending"
    dec2 = decon_record(tmp_path, "d2.json", [p["plain_sha256"] for p in record["parts"]])
    assert adm.admit(rec, parts, tmp_path / "out2", decontam=[dec2])["status"] == "admissible"


def test_stored_check_used_only_for_matching_bytes(tmp_path):
    rec, parts, record = make_set(tmp_path, [[5, 6], [7]])
    partials = tmp_path / "partials"
    partials.mkdir()
    p0 = record["parts"][0]
    good = {"file": {"name": p0["name"], "sha256": p0["gz_sha256"]}, "plain_sha256": p0["plain_sha256"],
            "tokenizer_sha256": "t" * 64, "ids": [f"{SET}/0", f"{SET}/1"], "lengths": [5, 6], "rows": 2}
    (partials / f"{p0['name']}.check.json").write_text(json.dumps(good))
    p1 = record["parts"][1]
    stale = {"file": {"name": p1["name"], "sha256": "0" * 64}, "plain_sha256": p1["plain_sha256"],
             "tokenizer_sha256": "t" * 64, "ids": [f"{SET}/2"], "lengths": [999], "rows": 1}
    (partials / f"{p1['name']}.check.json").write_text(json.dumps(stale))
    s = adm.admit(rec, parts, tmp_path / "out", partials=partials)
    assert s["parts_from_stored_check"] == 1 and s["parts_read"] == 1 and s["tokens_in"] == 18


def test_bad_decontam_records_refused(tmp_path):
    rec, parts, record = make_set(tmp_path, [[5, 6]])
    for bad, extra in (("wrong_set", {"set_id": "other"}), ("wrong_fingerprints", {"set_sha": "f" * 64}),
                       ("not_ok", {"ok": False}), ("foreign_id", {"flagged": ["other/1"]})):
        dec = decon_record(tmp_path, f"{bad}.json", [record["content_sha256"]], **extra)
        with pytest.raises(adm.AdmitError):
            adm.admit(rec, parts, tmp_path / bad, decontam=[dec])


def test_damaged_part_refused(tmp_path):
    rec, parts, record = make_set(tmp_path, [[5, 6]])
    gz = parts / record["parts"][0]["name"]
    gz.write_bytes(gzip.compress(b'{"id": "x", "input_ids": [1]}\n', mtime=0))
    with pytest.raises(adm.AdmitError):
        adm.admit(rec, parts, tmp_path / "out")
    with pytest.raises(adm.AdmitError):  # without the disk hash the decompressed hash still refuses it
        adm.admit(rec, parts, tmp_path / "out", verify_disk=False)


def test_cli_writes_summary_without_ids(tmp_path):
    rec, parts, _ = make_set(tmp_path, [[5, 40000]])
    summary = tmp_path / "pub" / "s.json"
    assert adm.main(["--record", str(rec), "--parts-dir", str(parts), "--out-dir", str(tmp_path / "priv"),
                     "--summary", str(summary)]) == 0
    text = summary.read_text()
    assert f"{SET}/0" not in text and json.loads(text)["excluded_each"]["over_max_len"] == 1
