"""dt_markers and --keep-canary-state-dir of sft_job_v1.py (CPU, stand-ins, no model run).

    python -m pytest capstone/test_sft_job_dt.py -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import day_one_probe as probe  # noqa: E402
import sft_job_v1 as job  # noqa: E402

BASE = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--heldout", "h", "--packs", "p",
        "--steps", "300", "--device", "cpu"]
CFG, ROWS, DEV, OUT = Path("c.yaml"), Path("rows.jsonl"), Path("dev.jsonl"), Path("o")


def _cmd(*extra):
    a = job.parse_args([*BASE, *extra, "--out", "x"])
    return job.sft_cmd(a, CFG, ROWS, DEV, OUT, 300, False)


def _method_part(cmd):
    return cmd[cmd.index("--method"):cmd.index("--steps")]


def test_dt_markers_maps_to_sft_g5_dt_with_marker_rows_and_the_dt_flags():
    got = _method_part(_cmd("--method", "dt_markers", "--dt-eta", "0.1", "--dt-unseen", "keep"))
    assert got == ["--method", "dt", "--lr", "0.0001", "--marker-rows", "--wd", "0", "--marker-lr", "0.001",
                   "--dt-targets", "g5_mlp", "--dt-alpha-start", "100.0", "--dt-alpha-end", "1000.0", "--dt-lambda", "1e-05",
                   "--dt-eta", "0.1", "--dt-prior-strength", "3.0", "--dt-unseen", "keep", "--dt-calib-rows", "64"]


def test_dt_defaults_equal_sft_g5_defaults():
    import sft_g5
    g = sft_g5.parse_args(["--adapter-config", "c", "--train", "t", "--eval", "e", "--method", "dt", "--out", "o"])
    a = job.parse_args([*BASE, "--out", "x"])
    for name in ("dt_targets", "dt_alpha_start", "dt_alpha_end", "dt_lambda", "dt_eta", "dt_prior_strength", "dt_unseen", "dt_calib_rows"):
        assert getattr(a, name) == getattr(g, name), name


def test_old_methods_build_the_command_they_always_built():
    assert _method_part(_cmd()) == ["--method", "full", "--lr", "0.0001"]
    assert _method_part(_cmd("--method", "lora_markers")) == ["--method", "lora", "--lr", "0.0001", "--marker-rows", "--wd", "0", "--marker-lr", "0.001"]
    full = _cmd()
    assert not any(x.startswith("--dt-") or x == "--keep-canary-state-dir" for x in full)  # nothing new on the line


def test_flag_refused_without_dt_markers_or_without_keep_arm(tmp_path):
    for extra in (["--keep-canary-state-dir", str(tmp_path), "--keep-arm", "a2"],  # method full: no mask files
                  ["--method", "lora_markers", "--keep-canary-state-dir", str(tmp_path), "--keep-arm", "a2"],
                  ["--method", "dt_markers", "--keep-canary-state-dir", str(tmp_path)]):  # no --keep-arm
        with pytest.raises(SystemExit) as e:
            job.parse_args([*BASE, *extra, "--out", str(tmp_path)])
        assert e.value.code == 2
    ok = job.parse_args([*BASE, "--method", "dt_markers", "--keep-canary-state-dir", str(tmp_path), "--keep-arm", "a4", "--out", str(tmp_path)])
    assert ok.keep_arm == "a4"


def _run_job(tmp_path, monkeypatch, extra):
    import make_adapter_config
    import sft_slice_v1 as sl
    real = probe.run_sft_arm

    def fake_build(packs, tok, tab, max_tokens, out, dev_rows, check_hashes=True):
        out.mkdir(parents=True)
        for n in ("a2_train.jsonl", "a4_train.jsonl", "dev.jsonl"):
            (out / n).write_text("rows")
        return {"train_rows": 1}

    def fake_arm(o, arm, cmd, timeout=None, canary_dest=None):
        prog = ("import json,pathlib;d=pathlib.Path(%r);d.mkdir(exist_ok=True,parents=True);"
                "[(d/n).write_bytes(b'weights-%s' if n.endswith('safetensors') else b'mask-'+n.encode()) for n in "
                "('model.safetensors','dt_keep_masks.bin','dt_keep_masks.bin.json','generations.jsonl')];"
                "(d/'sft_report.json').write_text(json.dumps({'log':[{}]*7,'before':{'forgetting':{'val/bpb':2.0}},"
                "'after':{'forgetting':{'val/bpb':2.01}}}))") % (str(o / f"sft_{arm}"), arm)
        return real(o, arm, [sys.executable, "-c", prog], timeout, canary_dest)

    monkeypatch.setattr(job.probe, "check_pins", lambda *a: {"checks": {}})
    monkeypatch.setattr(job, "check_run_and_inputs", lambda a: {"block_size": 2048})
    monkeypatch.setattr(job, "check_g5_sources", lambda a: {})
    monkeypatch.setattr(job.probe, "run_sft_arm", fake_arm)
    monkeypatch.setattr(sl, "build", fake_build)
    monkeypatch.setattr(make_adapter_config, "write_config", lambda out, *a: out)
    assert job.main([*BASE, "--method", "dt_markers", *extra, "--out", str(tmp_path / "out")]) == 0
    return json.loads((tmp_path / "out" / "summary.json").read_text())


def test_kept_folder_holds_three_files_whose_sha256_equal_the_summary_and_the_other_arm_is_deleted(tmp_path, monkeypatch):
    keep = tmp_path / "keep"
    s = _run_job(tmp_path, monkeypatch, ["--keep-canary-state-dir", str(keep), "--keep-arm", "a2"])
    rec = s["kept_canary_state"]
    assert list(rec) == ["sft_a2"]
    d = keep / "a2"
    assert sorted(p.name for p in d.iterdir()) == ["SHA256SUMS", "dt_keep_masks.bin", "dt_keep_masks.bin.json", "model.safetensors"]
    for name, sha in rec["sft_a2"]["sha256"].items():
        assert hashlib.sha256((d / name).read_bytes()).hexdigest() == sha
    assert (d / "SHA256SUMS").read_text() == "".join(f"{v}  {k}\n" for k, v in rec["sft_a2"]["sha256"].items())
    out = tmp_path / "out"
    for arm in ("a2", "a4"):  # in the job's own folder every weight and generation is gone, as before
        assert not (out / f"sft_{arm}" / "model.safetensors").exists() and not (out / f"sft_{arm}" / "generations.jsonl").exists()
    assert not (keep / "a4").exists()


def test_without_the_flag_nothing_is_kept_and_summary_has_no_new_key(tmp_path, monkeypatch):
    s = _run_job(tmp_path, monkeypatch, [])
    assert "kept_canary_state" not in s and set(s) == {"ok", "steps", "failed_steps"}


def test_missing_mask_files_fail_the_arm_loudly(tmp_path):
    arm = tmp_path / "sft_a2"
    arm.mkdir()
    (arm / "model.safetensors").write_bytes(b"w")
    with pytest.raises(RuntimeError, match="wrote no"):
        probe.copy_canary_state(arm, tmp_path / "dest")
