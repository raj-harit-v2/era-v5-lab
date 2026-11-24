"""--origin g5_delivery needs --probe-file in day_one_probe.py and sft_job_v1.py (team5_adapter refuses a delivered
run folder without probe.ids and probe.expected_mean_nll; both jobs used to reach that refusal after the pins step)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import day_one_probe as probe  # noqa: E402
import sft_job_v1 as job  # noqa: E402

SFT = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--heldout", "h", "--packs", "p",
       "--device", "cpu", "--out", "x"]
DAY = ["day_one_probe.py", "--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b",
       "--heldout", "h", "--sft-eval", "e", "--device", "cpu"]


def test_sft_job_refuses_a_delivery_without_a_probe_file(capsys):
    with pytest.raises(SystemExit):
        job.parse_args([*SFT, "--origin", "g5_delivery"])
    assert "needs --probe-file" in capsys.readouterr().err


def test_sft_job_takes_the_probe_file_and_rehearsal_needs_none():
    assert job.parse_args([*SFT, "--origin", "g5_delivery", "--probe-file", "p.json"]).probe_file == Path("p.json")
    assert job.parse_args(SFT).probe_file is None


def test_day_one_probe_refuses_a_delivery_without_a_probe_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [*DAY, "--origin", "g5_delivery", "--out", str(tmp_path / "o")])
    with pytest.raises(SystemExit):
        probe.main()
    assert "needs --probe-file" in capsys.readouterr().err
    assert not (tmp_path / "o").exists()


class _Stop(Exception):
    pass


def test_sft_job_hands_the_loaded_probe_to_the_adapter_config(tmp_path, monkeypatch):
    import json  # noqa: PLC0415
    import make_adapter_config as mac  # noqa: PLC0415
    pf = tmp_path / "probe.json"
    pf.write_text(json.dumps({"ids": [1, 2, 3], "expected_mean_nll": 10.5, "atol": 0.01}))
    seen = {}

    def fake_write_config(*args, probe=None, **kw):
        seen["probe"] = probe
        raise _Stop

    monkeypatch.setattr(job.probe, "check_pins", lambda *x: {})
    monkeypatch.setattr(job, "check_run_and_inputs", lambda a: {})
    monkeypatch.setattr(job, "check_g5_sources", lambda a: {})
    monkeypatch.setattr(mac, "write_config", fake_write_config)
    a = job.parse_args([*SFT[:-1], str(tmp_path / "o"), "--origin", "g5_delivery", "--probe-file", str(pf)])
    (tmp_path / "o").mkdir()
    with pytest.raises(_Stop):
        job.run(a, tmp_path / "o")
    assert seen["probe"] == mac.load_probe(pf) and seen["probe"]["ids"] == [1, 2, 3]
