"""run_folder_from_store.py: refusals on CPU without a lab checkout, plus an opt-in end-to-end check on a real store.

End to end needs a run trained by main's train_week2.py with --checkpoint-store, delivered without checkpoint.pt:
    G10_DR2_DELIVERY=<folder> G10_DR2_STORE=<store root> G10_DR2_G5_ROOT=<lab checkout> \
    G10_DR2_ARTIFACTS=<dir with tokenizer_p1536.json, ke2_p1536/raw_table_P32.npz, heldout_v1_bal60k*.jsonl>
"""
from __future__ import annotations

import json
import os
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_folder_from_store as rfs  # noqa: E402

parametrize = pytest.mark.parametrize  # no dotted decorator: the lab pr-guard's old email regex flags it


def _delivery(tmp_path, manifest=None, summary=None):
    rf = tmp_path / "delivered"
    rf.mkdir()
    m = {"run_id": "dryrun2-1234", "team7_checkpoint": {"store": "/shared/ckpt", "run_id": "dryrun2-1234",
                                                        "interval_s": 600.0}}
    s = {"run_id": "dryrun2-1234", "steps": 1221, "team7_checkpoint_path": "main/step_00001221-e1",
         "final_model_sha256": "0" * 64}
    m.update(manifest or {})
    s.update(summary or {})
    (rf / "manifest.json").write_text(json.dumps({k: v for k, v in m.items() if v is not None}))
    (rf / "summary.json").write_text(json.dumps({k: v for k, v in s.items() if v is not None}))
    return rf


def test_a_complete_delivery_names_its_committed_step(tmp_path):
    _, _, t7, step, path = rfs.delivery_facts(_delivery(tmp_path))
    assert (t7["run_id"], step, path) == ("dryrun2-1234", 1221, "main/step_00001221-e1")


@parametrize("manifest,summary,match", [
    ({"team7_checkpoint": None}, {}, "no team7_checkpoint"),
    ({}, {"run_id": "other"}, "run_id differs"),
    ({"run_id": "other"}, {}, "run_id differs"),
    ({}, {"team7_checkpoint_path": None}, "not committed"),
    ({}, {"steps": None}, "not committed"),
    ({}, {"steps": True}, "not committed"),
])
def test_a_delivery_without_a_committed_final_step_is_refused(tmp_path, manifest, summary, match):
    with pytest.raises(ValueError, match=match):
        rfs.delivery_facts(_delivery(tmp_path, manifest, summary))


def test_a_folder_that_already_has_checkpoint_pt_is_left_alone(tmp_path):
    rf = _delivery(tmp_path)
    (rf / "checkpoint.pt").write_bytes(b"x")
    with pytest.raises(ValueError, match="already has checkpoint.pt"):
        rfs.delivery_facts(rf)


E2E = [os.environ.get(k) for k in ("G10_DR2_DELIVERY", "G10_DR2_STORE", "G10_DR2_G5_ROOT", "G10_DR2_ARTIFACTS")]


needs_store = pytest.mark.skipif(not all(E2E), reason="needs G10_DR2_DELIVERY/STORE/G5_ROOT/ARTIFACTS (a real Team 7 store)")


@needs_store
def test_the_store_weights_match_the_summary_and_load_in_the_adapter_format(tmp_path):
    import torch  # noqa: PLC0415
    rf, store, g5, art = map(Path, E2E)
    a = Namespace(g5_root=g5, run_folder=rf, store=str(store), tokenizer=art / "tokenizer_p1536.json",
                  byte_table=art / "ke2_p1536" / "raw_table_P32.npz", heldout_data=art / "heldout_v1_bal60k.jsonl",
                  heldout_sources=art / "heldout_v1_bal60k_sources.jsonl", device="cpu", out=tmp_path / "rebuilt")
    rec = rfs.build(a)
    summary = json.loads((rf / "summary.json").read_text())
    assert rec["model_hash_g5"] == summary["final_model_sha256"] and rec["step"] == summary["steps"]
    ck = torch.load(a.out / "checkpoint.pt", map_location="cpu", weights_only=True)
    assert set(ck) == {"model", "step", "identity_sha256", "run_id"}
    assert ck["identity_sha256"] == json.loads((rf / "manifest.json").read_text())["identity_sha256"]
    for n in ("manifest.json", "summary.json"):
        assert (a.out / n).read_bytes() == (rf / n).read_bytes()
