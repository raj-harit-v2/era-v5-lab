"""Failure-path contracts for the aggregate-only TSAI probe."""
import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "capstone"))
import day_one_probe as probe

parametrize = pytest.mark.parametrize
skipif = pytest.mark.skipif


@parametrize("fail", [False, True])
def test_arm_cleans_private_outputs_on_success_and_failure(tmp_path, fail):
    arm = tmp_path / "sft_full"
    arm.mkdir()
    # Run a real child: it writes the artifacts before either returning or failing.
    code = """import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
(p / 'model.safetensors').write_bytes(b'weights')
(p / 'generations.jsonl').write_text('private generation')
(p / 'sft_report.json').write_text(json.dumps({'before': {}, 'after': {}}))
raise SystemExit(int(sys.argv[2]))
"""
    cmd = [sys.executable, "-c", code, str(arm), str(int(fail))]
    if fail:
        with pytest.raises(RuntimeError):
            probe.run_sft_arm(tmp_path, "full", cmd)
    else:
        assert probe.run_sft_arm(tmp_path, "full", cmd)["before"] == {}
    assert sorted(p.name for p in arm.iterdir()) == ["sft_report.json"]


def test_failed_step_does_not_hide_success_or_return_zero(tmp_path):
    def broken():
        raise RuntimeError("failed arm")
    results = {"bad": probe.step(tmp_path, "bad", broken),
               "good": probe.step(tmp_path, "good", lambda: {"value": 3})}
    assert results["good"]["value"] == 3
    assert probe.finish(tmp_path, results) == 1
    assert json.loads((tmp_path / "summary.json").read_text())["failed_steps"] == ["bad"]
    assert probe.finish(tmp_path, {"good": results["good"]}) == 0


def test_neither_eval_rows_nor_dolly_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["probe", "--g5-root", "g", "--run-folder", "r", "--tokenizer", "t",
                                      "--byte-table", "b", "--heldout", "h", "--out", str(tmp_path)])
    with pytest.raises(SystemExit) as e:
        probe.main()
    assert e.value.code == 2


@parametrize("fail", [False, True])
def test_built_input_rows_never_leave_the_job(tmp_path, monkeypatch, fail):
    def fake_run(a, out):
        (out / "_inputs").mkdir()
        (out / "_inputs" / "sft_train.jsonl").write_text("rows")
        if fail:
            raise RuntimeError("step crashed")
        return 0
    monkeypatch.setattr(probe, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["probe", "--g5-root", "g", "--run-folder", "r", "--tokenizer", "t",
                                      "--byte-table", "b", "--heldout", "h", "--sft-dolly", "d.jsonl",
                                      "--out", str(tmp_path)])
    if fail:
        with pytest.raises(RuntimeError):
            probe.main()
    else:
        assert probe.main() == 0
    assert not (tmp_path / "_inputs").exists()


def _pins_fixture(tmp_path, recorded):
    """A run folder whose manifest records `recorded`, plus a stand-in tokenizer file and npz table."""
    import hashlib
    import numpy as np
    tok = tmp_path / "tokenizer.json"
    tok.write_text('{"stand-in": true}')
    table = tmp_path / "raw_table_P32.npz"
    np.savez(table, bytes=np.zeros((2, 2), np.uint8), table_sha256=np.array("c" * 64))
    folder = tmp_path / "run"
    folder.mkdir()
    real = {"tokenizer_sha256": hashlib.sha256(tok.read_bytes()).hexdigest(), "table_content_sha256": "c" * 64}
    arts = {k: (real[k] if v == "same" else v) for k, v in recorded.items()}
    (folder / "manifest.json").write_text(json.dumps({"artifacts": arts}))
    return folder, tok, table, real


def test_tokenizer_mismatch_stops_before_any_model_work(tmp_path, monkeypatch, capsys):
    folder, tok, table, real = _pins_fixture(tmp_path, {"tokenizer_sha256": "a" * 64, "table_content_sha256": "same"})
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["probe", "--g5-root", "g", "--run-folder", str(folder), "--tokenizer", str(tok),
                                      "--byte-table", str(table), "--heldout", "h", "--sft-dolly", "d.jsonl",
                                      "--out", str(out)])
    assert probe.main() == 1
    printed = capsys.readouterr().out
    assert real["tokenizer_sha256"] in printed and "a" * 64 in printed  # both hashes are printed
    assert sorted(p.name for p in out.iterdir()) == ["pins.json", "summary.json"]  # no adapter.yaml, no rows
    pins = json.loads((out / "pins.json").read_text())
    assert not pins["ok"] and "tokenizer_sha256" in pins["error"]
    assert json.loads((out / "summary.json").read_text())["failed_steps"] == ["pins"]


def test_table_content_mismatch_is_refused(tmp_path):
    folder, tok, table, _ = _pins_fixture(tmp_path, {"tokenizer_sha256": "same", "table_content_sha256": "b" * 64})
    with pytest.raises(ValueError, match="table_content_sha256"):
        probe.check_pins(folder, tok, table)


def test_matching_pins_pass_and_unrecorded_hashes_are_reported(tmp_path):
    folder, tok, table, real = _pins_fixture(tmp_path, {"tokenizer_sha256": "same", "table_content_sha256": "same"})
    rep = probe.check_pins(folder, tok, table)
    assert rep["checks"]["tokenizer_sha256"]["match"] is True
    assert rep["checks"]["table_content_sha256"]["match"] is True
    assert rep["not_recorded"] == ["table_file_sha256"] and rep["checks"]["table_file_sha256"]["given"]
    (folder / "manifest.json").write_text(json.dumps({"config": {}}))  # a manifest without artifacts
    rep = probe.check_pins(folder, tok, table)
    assert rep["checks"]["tokenizer_sha256"] == {"given": real["tokenizer_sha256"], "run_manifest": None, "match": None}
    assert len(rep["not_recorded"]) == 3


TOKENIZER = os.environ.get("G10_BASELINE_TOKENIZER")
TABLE = Path(__file__).resolve().parents[3] / "teams" / "04-ke2" / "results" / "tables" / "raw_table_P32.npz"


@skipif(not TOKENIZER or not TABLE.exists(), reason="needs G10_BASELINE_TOKENIZER (v0) and its KE2 table")
def test_dolly_rows_follow_the_converter_and_split_rules(tmp_path):
    import probe_inputs
    import sft_rows
    # FIXTURE rows (synthetic, written only to test the builder; never training data).
    rows = [{"instruction": f"fixture question {i}", "context": "fixture context" if i % 3 == 0 else "",
             "response": "fixture answer " * (40 if i == 5 else 1), "category": "fixture"} for i in range(40)]
    dolly = tmp_path / "databricks-dolly-15k.jsonl"
    dolly.write_text("".join(json.dumps(r) + "\n" for r in rows))
    rep = probe_inputs.build_dolly(dolly, Path(TOKENIZER), TABLE, 48, tmp_path / "a")
    st = rep["stats"]
    assert st.get("pretrain_half_refused", 0) + st.get("over_max_tokens", 0) + st.get("ok", 0) == 40
    assert st.get("kept_train", 0) + st.get("kept_eval", 0) == st.get("ok", 0) > 0
    for split in ("train", "eval"):
        for line in (tmp_path / "a" / f"sft_{split}.jsonl").read_text().splitlines():
            r = json.loads(line)
            assert sft_rows.split_of(r["id"]) == r["split"] == split
            assert r["n_tokens"] <= 48 and len(r["input_ids"]) == len(r["loss_mask"]) == r["n_tokens"]
            assert r["loss_mask"].index(1) == r["prompt_len"]
            last = max(i for i, m in enumerate(r["loss_mask"]) if m)
            assert r["input_ids"][last] == 130816  # the trained span ends with <|im_end|>
    again = probe_inputs.build_dolly(dolly, Path(TOKENIZER), TABLE, 48, tmp_path / "b")
    assert again["files"] == rep["files"]  # deterministic, byte for byte
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == ["sft_eval.jsonl", "sft_train.jsonl"]
