"""Tests for ocr2_heldout_handoff.py (synthetic family keys and ids only)."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr2_heldout_handoff as ho  # noqa: E402
import pack_admission  # noqa: E402

SALT, FRACTION = "test-salt", 0.3


def test_selector_matches_pack_admission():
    ref = pack_admission.heldout_selector({"pack": {"heldout_eval_v1": {"fraction": FRACTION, "salt": SALT}}})
    mine = ho.selector(FRACTION, SALT)
    keys = [f"family-{i}" for i in range(2000)]
    assert [ref(k) for k in keys] == [mine(k) for k in keys]
    assert 400 < sum(map(mine, keys)) < 800


def _fixture(tmp_path, tamper=None):
    held = ho.selector(FRACTION, SALT)
    fams = [k for k in (f"family-{i}" for i in range(200)) if held(k)][:5]
    if tamper == "not_held":
        fams[0] = next(k for k in (f"family-{i}" for i in range(200)) if not held(k))
    rows = [{"id": f"ocr/{i}", "ocr_id": f"o{i}", "problem_family_key": fams[i % 5], "shard_id": i % 2,
             "source_row_key": ["a", "b", "taco" if i % 3 else "apps", "train", i]} for i in range(12)]
    if tamper == "dup":
        rows[1]["id"] = rows[0]["id"]
    ids = tmp_path / "ids.jsonl"
    ids.write_text("".join(json.dumps(r) + "\n" for r in rows))
    by_src = {}
    for r in rows:
        k = f"{r['source_row_key'][2]}/train"
        by_src[k] = by_src.get(k, 0) + 1
    manifest = {"heldout_eval_v1": {"rule": {"fraction": FRACTION, "salt": SALT}, "rows": 12, "families": 5,
                                    "rows_by_source": by_src,
                                    "id_list_sha256": hashlib.sha256(ids.read_bytes()).hexdigest()},
                "shards": [{"shard_id": 0, "heldout_rows": 6}, {"shard_id": 1, "heldout_rows": 6}]}
    policy = {"pack": {"heldout_eval_v1": {"fraction": FRACTION, "salt": SALT}}}
    return ids, policy, manifest


def test_good_list_passes_and_bundle_has_no_public_ids(tmp_path):
    ids, policy, manifest = _fixture(tmp_path)
    summary, rows = ho.verify(ids, policy, manifest)
    assert summary["ok"] and summary["rows"] == 12 and summary["families"] == 5
    ho.write_bundle(tmp_path / "bundle", ids, rows, summary)
    assert (tmp_path / "bundle" / "SHA256SUMS").read_text().count("\n") == 3
    assert "ocr/0" not in json.dumps(summary) and "family-" not in json.dumps(summary)


def test_failures_are_detected(tmp_path):
    for tamper, check in (("not_held", "every_family_held_under_rule"), ("dup", "ids_unique")):
        d = tmp_path / tamper
        d.mkdir()
        ids, policy, manifest = _fixture(d, tamper)
        manifest["heldout_eval_v1"]["id_list_sha256"] = hashlib.sha256(ids.read_bytes()).hexdigest()
        summary, _ = ho.verify(ids, policy, manifest)
        assert not summary["checks"][check] and not summary["ok"]
    ids, policy, manifest = _fixture(tmp_path)
    manifest["shards"][0]["heldout_rows"] = 5
    assert not ho.verify(ids, policy, manifest)[0]["checks"]["rows_by_shard_equal_manifest"]
    policy["pack"]["heldout_eval_v1"]["salt"] = "other"
    assert not ho.verify(ids, policy, manifest)[0]["checks"]["rule_in_manifest_equals_policy"]
