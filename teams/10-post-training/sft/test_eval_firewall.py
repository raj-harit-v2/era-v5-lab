"""Tests for eval_firewall.py (SFT/RL evaluation firewall on the OCR-2 pack). Synthetic rows only."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eval_firewall as ef  # noqa: E402

FAM = {f"r{i}": "sha256:" + hashlib.sha256(f"problem {i % 3}".encode()).hexdigest() for i in range(6)}  # 3 families


def _world(tmp_path):
    pack = tmp_path / "pack.jsonl"
    with open(pack, "w", encoding="utf-8") as f:
        for i in range(6):
            f.write(json.dumps({"id": f"r{i}", "text": f"t{i}", "input_ids": list(range(i + 2)), "loss_mask": [0] + [1] * (i + 1)}) + "\n")
    side = tmp_path / "joined.sidecar.jsonl"
    side.write_text("".join(json.dumps({"rendered_id": r, "problem_family_key": k}) + "\n" for r, k in FAM.items()))
    fams = tmp_path / "families.txt"
    sha = ef.write_families([FAM["r1"]], fams)  # family of r1 and r4
    stats = tmp_path / "shard-00007.jsonl.gz"
    with gzip.open(stats, "wt", encoding="utf-8") as f:
        for i in range(6):
            f.write(json.dumps({"id": f"r{i}", "family": FAM[f"r{i}"], "status": "pack", "tokens": i + 2, "targets": i + 1}) + "\n")
        f.write(json.dumps({"id": "h", "family": FAM["r1"], "status": "heldout", "tokens": 9, "targets": 3}) + "\n")
        f.write(json.dumps({"id": "s", "family": FAM["r1"], "status": "screened_out", "tokens": 9, "targets": 3}) + "\n")
    return pack, side, fams, sha, stats


def test_apply_drops_the_listed_families_and_keeps_the_rest_byte_for_byte(tmp_path):
    pack, side, fams, sha, _ = _world(tmp_path)
    out = tmp_path / "fw" / "pack.firewalled.jsonl"
    rep = ef.apply(pack, side, ef.load_families(fams, sha), out)
    src = pack.read_bytes().splitlines(keepends=True)
    assert out.read_bytes() == b"".join(line for i, line in enumerate(src) if i not in (1, 4))
    assert (rep["rows_in"], rep["rows_removed"], rep["rows_kept"], rep["families_removed"]) == (6, 2, 4, 1)
    assert rep["tokens_removed"] == 3 + 6 and rep["shifted_targets_removed"] == 2 + 5
    assert rep["firewalled_pack_sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert rep["pack_sha256_in"] == hashlib.sha256(pack.read_bytes()).hexdigest()


def test_predict_from_row_stats_equals_apply(tmp_path):
    pack, side, fams, sha, stats = _world(tmp_path)
    keys = ef.load_families(fams, sha)
    rep = ef.apply(pack, side, keys, tmp_path / "o.jsonl")
    pred = ef.predict([stats], keys)
    s = pred["shards"]["7"]
    for k in ("rows_kept", "rows_removed", "tokens_kept", "tokens_removed", "shifted_targets_kept", "shifted_targets_removed",
              "families_removed"):
        assert s[k] == rep[k], k
    assert s["heldout_rows_in_list"] == 1  # reported, never removed: the held-out file is not touched
    assert pred["list_families_not_in_pack"] == 0


def test_a_list_that_is_not_the_pinned_one_or_is_malformed_is_refused(tmp_path):
    _, _, fams, sha, _ = _world(tmp_path)
    with pytest.raises(ef.FirewallError, match="not the pinned"):
        ef.load_families(fams, "0" * 64)
    bad = tmp_path / "bad.txt"
    bad.write_text("sha256:" + "b" * 64 + "\nsha256:" + "a" * 64 + "\n")  # not sorted
    with pytest.raises(ef.FirewallError, match="sorted"):
        ef.load_families(bad, None)
    assert ef.main(["apply", "--pack", "x", "--sidecar", "y", "--families", str(fams), "--families-sha256", "0" * 64,
                    "--out", str(tmp_path / "o"), "--report", str(tmp_path / "r")]) == 2


def test_a_pack_row_missing_from_the_sidecar_stops_the_step(tmp_path):
    pack, side, fams, sha, _ = _world(tmp_path)
    side.write_text("".join(json.dumps({"rendered_id": r, "problem_family_key": k}) + "\n" for r, k in FAM.items() if r != "r3"))
    with pytest.raises(ef.FirewallError, match="r3"):
        ef.apply(pack, side, ef.load_families(fams, sha), tmp_path / "o.jsonl")


def test_record_checks_predicted_against_actual_and_the_pack_manifest(tmp_path):
    pack, side, fams, sha, stats = _world(tmp_path)
    keys = ef.load_families(fams, sha)
    rep = ef.apply(pack, side, keys, tmp_path / "o.jsonl")
    pred = {**ef.predict([stats], keys), "families_sha256": sha, "families_in_list": 1}
    shards = [{"pack_sha256": "x"}] * 7 + [{"pack_sha256": rep["pack_sha256_in"]}]
    pred["shards"] = {str(i): pred["shards"]["7"] for i in range(8)}  # every shard predicted (toy)
    manifest = {"shards": shards, "build": {"run_id": "admission-tokX-Y"},
                "funnel": {"pack.train_rows": 6 * 8, "train.tokens": 27 * 8, "train.shifted_assistant_targets": 21 * 8}}
    pred["totals"] = {k: v * 8 for k, v in pred["shards"]["7"].items() if k != "families_removed"}
    rec = ef.record(pred, {"7": rep}, {}, {}, "ruling", manifest, "m.json")
    assert rec["checks"]["shard7.predicted_equals_actual"] and rec["checks"]["shard7.input_is_the_verified_pack"]
    assert rec["checks"]["totals.rows_reconcile_with_the_pack_manifest"]
    assert rec["checks"]["heldout_split_untouched"] is False  # the toy held-out row shares a listed family
    assert "r1" not in json.dumps(rec)  # no row id in the public record
