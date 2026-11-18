"""Tests for rebuild_v1 (G10): relative pins, the step-script guard, input staging and the output comparison.

    pytest teams/10-post-training/rl-data/test_rebuild_v1.py -q

No data, no network: toy files stand in for the parquets. The full rebuild needs the pinned sources (see the
driver's docstring and jobs/2026-11-18-rl-data-v1-pool.md).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "rebuild_v1"))
import rebuild_v1 as rb  # noqa: E402

PINS = json.loads(rb.PINS.read_text())


def is_sha(x):
    return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x)


def test_pins_are_relative_complete_and_agree_with_the_v1_manifests():
    text = rb.PINS.read_text()
    assert "/Users/" not in text and "\\\\" not in text and '"path"' not in text
    cc = PINS["code_contests"]
    assert len(cc["files"]) == 39 and len({f["file"] for f in cc["files"]}) == 39
    assert sum(f["rows"] for f in cc["files"]) == cc["total_rows"] == 13328
    assert all(is_sha(f["sha256"]) and f["sha256"] == f["hub_lfs_sha256"] for f in cc["files"])
    man = json.loads((HERE / "manifests/rl-code-code-contests-noncf.v1.json").read_text())
    assert {f["file"]: f["sha256"] for f in man["source"]["files"]} == {f["file"]: f["sha256"] for f in cc["files"]}
    assert man["source"]["revision"] == cc["revision"]
    math_man = json.loads((HERE / "manifests/rl-math-hendrycks-math-train.v1.json").read_text())
    assert {f["file"]: f["sha256"] for f in math_man["source"]["files"]} == \
        {k: v["lfs_sha256"] for k, v in PINS["hendrycks_math"]["files"].items()}
    exp = PINS["expected"]
    assert exp["out/v1/cc.jsonl"] == man["output"]["sha256"] and exp["out/v1/math.jsonl"] == math_man["output"]["sha256"]
    assert exp["pool/rl-code-code-contests-noncf.v1.pool.jsonl"] == man["prompt_pool"]["sha256"]
    assert exp["pool/rl-math-hendrycks-math-train.v1.pool.jsonl"] == math_man["prompt_pool"]["sha256"]
    assert all(is_sha(v) for v in exp.values())


def test_the_step_scripts_are_the_recorded_copies(tmp_path):
    assert rb.check_steps(PINS) == []
    for n in rb.STEPS:
        (tmp_path / n).write_bytes((rb.HERE / n).read_bytes())
    (tmp_path / "build_v1.py").write_text((rb.HERE / "build_v1.py").read_text() + "\n# edited\n")
    assert rb.check_steps(PINS, tmp_path) == ["build_v1.py"]


def _toy_pins(tmp_path):
    """Pins for two toy code files and one toy MATH file, in the real schema."""
    cc_dir, math_dir = tmp_path / "cc", tmp_path / "math"
    (math_dir / "algebra").mkdir(parents=True)
    cc_dir.mkdir()
    files = []
    for i in range(2):
        p = cc_dir / f"train-0000{i}-of-00002-x.parquet"
        p.write_bytes(f"toy {i}".encode())
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        files.append({"name": p.stem, "file": p.name, "rows": 1, "bytes": p.stat().st_size, "sha256": h,
                      "hub_lfs_sha256": h, "hub_bytes": p.stat().st_size})
    m = math_dir / "algebra" / "train-00000-of-00001.parquet"
    m.write_bytes(b"toy math")
    pins = {"code_contests": {"repo": "r", "revision": "v", "total_rows": 2, "files": files},
            "hendrycks_math": {"dataset": "d", "revision": "v", "files": {"algebra/train-00000-of-00001.parquet":
                               {"bytes": m.stat().st_size, "lfs_sha256": hashlib.sha256(m.read_bytes()).hexdigest()}}}}
    return pins, cc_dir, math_dir


def test_staged_inputs_pass_the_real_pin_check_and_a_changed_file_fails_it(tmp_path):
    pins, cc_dir, math_dir = _toy_pins(tmp_path)
    m_path, p_path = rb.stage(pins, cc_dir, math_dir, tmp_path / "run")
    staged = json.loads(m_path.read_text())["sources"]["code_contests/train"]["files"]
    assert [Path(f["path"]).parent for f in staged] == [cc_dir.resolve()] * 2

    def verify():
        return subprocess.run([sys.executable, "-I", str(rb.HERE / "verify_pins.py"), str(m_path), str(math_dir), str(p_path),
                               str(tmp_path / "v.json")], capture_output=True, text=True)

    r = verify()
    assert r.returncode == 0 and json.loads((tmp_path / "v.json").read_text())["all_ok"] is True
    (cc_dir / pins["code_contests"]["files"][1]["file"]).write_bytes(b"toy X")
    r = verify()
    assert r.returncode == 1 and json.loads(r.stdout)["bad"] == [pins["code_contests"]["files"][1]["file"]]


def test_compare_names_every_missing_or_changed_output(tmp_path):
    (tmp_path / "a.jsonl").write_text("x\n")
    good = hashlib.sha256(b"x\n").hexdigest()
    assert rb.compare({"a.jsonl": good}, tmp_path) == {}
    diff = rb.compare({"a.jsonl": "0" * 64, "b.jsonl": good}, tmp_path)
    assert diff == {"a.jsonl": {"expected": "0" * 64, "got": good}, "b.jsonl": {"expected": good, "got": None}}
