"""Tests of capstone/make_probe_file.py.

The data-backed tests need a CPU run folder trained with this tree's Team 5 code and the tokenizer and KE2 table it
used (not in the repository): set G10_STANDIN_RUN_FOLDER and G10_STANDIN_ARTIFACTS, as for test_rl_job_v1.py.

    python -m pytest capstone/test_make_probe_file.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_probe_file as mpf  # noqa: E402

REPO = HERE.parents[2]
_WORK = Path(__file__).resolve().parents[6] / "work"
STANDIN_RUN = Path(os.environ.get("G10_STANDIN_RUN_FOLDER", _WORK / "pr587-main-check-2026-11-18/private/runs/post521"))
STANDIN_ART = Path(os.environ.get("G10_STANDIN_ARTIFACTS", _WORK / "capstone-rehearsal-2026-11-16/artifacts"))
TOK, TAB = STANDIN_ART / "tokenizer_p1536.json", STANDIN_ART / "ke2_p1536" / "raw_table_P32.npz"
needs_standin = pytest.mark.skipif(not (STANDIN_RUN / "checkpoint.pt").is_file() or not TOK.is_file(),
                                   reason="set G10_STANDIN_RUN_FOLDER and G10_STANDIN_ARTIFACTS")


def test_ids_are_parsed_and_checked():
    assert mpf.parse_ids("5, 6 7,8") == [5, 6, 7, 8]
    with pytest.raises(ValueError, match="integers"):
        mpf.parse_ids("5,x")
    mpf.check_ids([0, 9], vocab_size=10, block_size=2)
    for bad, msg in (([3], "at least 2"), ([1, 2, 3], "block_size"), ([1, 10], "vocabulary"), ([-1, 2], "vocabulary")):
        with pytest.raises(ValueError, match=msg):
            mpf.check_ids(bad, vocab_size=10, block_size=2)


def test_a_folder_that_is_not_a_run_is_refused(tmp_path):
    with pytest.raises(ValueError, match="manifest.json is missing"):
        mpf.compute(REPO, tmp_path, tmp_path / "t.json", tmp_path / "t.npz")
    with pytest.raises(ValueError, match="train_week2.py not found"):
        mpf.compute(tmp_path, tmp_path, tmp_path / "t.json", tmp_path / "t.npz")


def _delivery(tmp_path):
    """A copy of the stand-in run folder labelled the way a non-smoke Team 5 delivery is (as in test_rl_job_v1.py)."""
    rf = tmp_path / "delivery"
    shutil.copytree(STANDIN_RUN, rf)
    m = json.loads((rf / "manifest.json").read_text())
    m["status"], m["smoke"] = "AGREED_BASELINE_RUN", False
    (rf / "manifest.json").write_text(json.dumps(m, indent=2))
    return rf


@needs_standin
def test_the_written_file_is_accepted_by_the_adapter_and_the_two_paths_agree(tmp_path):
    import make_adapter_config as mac  # noqa: PLC0415
    sys.path.insert(0, str(HERE.parent / "rl-loop"))
    import team5_adapter as ta  # noqa: PLC0415
    rf, out = _delivery(tmp_path), tmp_path / "probe.json"
    assert mpf.main(["--g5-root", str(REPO), "--run", str(rf), "--tokenizer", str(TOK), "--byte-table", str(TAB),
                     "--out", str(out)]) == 0
    rec = json.loads(out.read_text())
    assert rec["targets"] == len(rec["ids"]) - 1 >= 8 and rec["atol"] == 1e-4 and rec["device"] == "cpu"
    probe = mac.load_probe(out)  # the job's own reader takes the file as written
    assert probe == {"ids": rec["ids"], "expected_mean_nll": rec["expected_mean_nll"], "atol": 1e-4}

    # 1. the adapter, loading the same folder as a delivery, verifies against Team 5's number: READY
    cfg = mac.write_config(tmp_path / "adapter.yaml", REPO, rf, TOK, TAB, HERE.parent, "g5_delivery", False, probe=probe)
    res = ta.build(yaml.safe_load(cfg.read_text()))
    assert res.status == ta.READY and res.manifest["probe"]["verified_against"] == rec["expected_mean_nll"]
    # the two code paths agree far inside the tolerance on one device
    assert abs(res.manifest["probe"]["mean_nll"] - rec["expected_mean_nll"]) < 1e-5
    assert res.manifest["model_hash_g5"] == rec["run"]["model_hash_g5"]

    # the RL job's own first step (pins) takes the file through --probe-file and passes on the delivery
    import rl_job_v1 as job  # noqa: PLC0415
    stub = {n: tmp_path / n for n in ("cc.jsonl", "tp", "hp")}
    for p in stub.values():
        p.write_text("x")
    (tmp_path / "out").mkdir()
    a = job.parse_args(["--g5-root", str(REPO), "--run-folder", str(rf), "--tokenizer", str(TOK), "--byte-table", str(TAB),
                        "--rl-tasks", str(stub["cc.jsonl"]), "--train-pool", str(stub["tp"]), "--heldout-pool", str(stub["hp"]),
                        "--device", "cpu", "--out", str(tmp_path / "out"), "--no-pack-check", "--no-git",
                        "--origin", "g5_delivery", "--probe-file", str(out)])
    assert "g5_sources" in job.pins(a, tmp_path / "out")

    # 2. the number depends on the tokens: the same ids in another order give another NLL and the adapter refuses it
    other = mpf.compute(REPO, rf, TOK, TAB, ids=list(reversed(rec["ids"])))
    assert abs(other["expected_mean_nll"] - rec["expected_mean_nll"]) > 1e-3 and other["text"] is None
    wrong = mac.write_config(tmp_path / "wrong.yaml", REPO, rf, TOK, TAB, HERE.parent, "g5_delivery", False,
                             probe={**probe, "expected_mean_nll": other["expected_mean_nll"]})
    with pytest.raises(ta.ArtifactError, match="probe mean NLL"):
        ta.build(yaml.safe_load(wrong.read_text()))

    # 3. an existing output file is never overwritten
    with pytest.raises(SystemExit):
        mpf.main(["--g5-root", str(REPO), "--run", str(rf), "--tokenizer", str(TOK), "--byte-table", str(TAB),
                  "--out", str(out)])


@needs_standin
def test_changed_weights_change_the_number_and_mixed_up_files_are_refused(tmp_path):
    import torch  # noqa: PLC0415
    rf = _delivery(tmp_path)
    base = mpf.compute(REPO, rf, TOK, TAB)
    # a checkpoint with one changed weight tensor: summary.json's final hash no longer matches, so Team 5's check stops it
    ck = torch.load(rf / "checkpoint.pt", map_location="cpu", weights_only=False)
    # (doubled, not shifted: adding one constant to every head weight moves all logits equally and leaves the NLL as it was)
    key = "head.weight" if "head.weight" in ck["model"] else "head.W_out"  # dense head, or the KAS V2 head (#717)
    ck["model"][key] = ck["model"][key] * 2.0
    torch.save(ck, rf / "checkpoint.pt")
    with pytest.raises(ValueError, match="final_model_sha256"):
        mpf.compute(REPO, rf, TOK, TAB)
    # without the summary the changed weights load, and the probe number moves by far more than the tolerance
    (rf / "summary.json").unlink()
    moved = mpf.compute(REPO, rf, TOK, TAB)
    assert moved["ids"] == base["ids"] and abs(moved["expected_mean_nll"] - base["expected_mean_nll"]) > 1e-3
    assert moved["run"]["model_hash_g5"] != base["run"]["model_hash_g5"]
    # a checkpoint and a manifest from different runs
    ck["identity_sha256"] = "0" * 64
    torch.save(ck, rf / "checkpoint.pt")
    with pytest.raises(ValueError, match="different runs"):
        mpf.compute(REPO, rf, TOK, TAB)
    # a manifest that names another tokenizer than the file given
    m = json.loads((rf / "manifest.json").read_text())
    m["artifacts"]["tokenizer_sha256"] = "1" * 64
    (rf / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="Tokenizer identity mismatch"):
        mpf.compute(REPO, rf, TOK, TAB)
