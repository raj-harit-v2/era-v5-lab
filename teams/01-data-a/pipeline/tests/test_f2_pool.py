"""Tests for f2_pool.py: the real run_f2.py and G9's real set, cut to one benchmark (gsm8k) so it loads in seconds. The
flagged docs carry G9's lab canary, built at run time from lab_canary.py: no benchmark text is in this file.

The main check: the pool writes the same bytes as run_f2.run_file called part by part (the serial run), with every start
method this machine has (spawn everywhere; fork on Linux).

  python -m pytest teams/01-data-a/pipeline/tests -q
"""
import json
import multiprocessing as mp
import subprocess
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq

from conftest import PIPELINE
import f2_pool

RUN_F2 = f2_pool.load_run_f2()
sys.path.insert(0, str(RUN_F2.G9))
from lab_canary import LAB_CANARY  # noqa: E402

BENCH = ("gsm8k",)
METHODS = [m for m in ("spawn", "fork") if m in mp.get_all_start_methods() and not (m == "fork" and sys.platform == "darwin")]


def docs(pack, n, flagged=()):
    return [{"doc_id": f"{pack}-{i}", "text": (f"text {i} {LAB_CANARY} more" if i in flagged else f"plain text {i} of {pack}"),
             "pack_id": pack} for i in range(n)]


@pytest.fixture
def deduped(tmp_path):
    """<deduped>/train with 2 packs and 4 parts of different sizes, three flagged docs."""
    root = tmp_path / "deduped" / "train"
    parts = {"code-go/part-00000.parquet": docs("code-go", 40, {3}), "code-go/part-00001.parquet": docs("code-go", 7),
             "en-dclm/part-00000.parquet": docs("en-dclm", 120, {0, 99}), "en-dclm/part-00001.parquet": docs("en-dclm", 1)}
    for rel, rows in parts.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows), root / rel)
    return root


def serial(src_root, out):
    """What run_f2.py does, part by part, in this process."""
    fp = RUN_F2.fingerprints(BENCH)
    code = RUN_F2.sha256(Path(RUN_F2.__file__))
    for f in sorted(src_root.rglob("*.parquet")):
        RUN_F2.run_file(f, out / f.relative_to(src_root), fp, code)


def snapshot(folder):
    """{relative path: bytes} for the Parquet parts, and {relative path: report without its seconds} for the .f2.json."""
    parts, reports = {}, {}
    for f in sorted(Path(folder).rglob("*")):
        rel = f.relative_to(folder).as_posix()
        if f.suffix == ".parquet":
            parts[rel] = f.read_bytes()
        elif f.name.endswith(".f2.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            r.pop("seconds")
            reports[rel] = r
    return parts, reports


@pytest.mark.parametrize("method", METHODS)
def test_pool_writes_what_the_serial_run_writes(tmp_path, deduped, method):
    serial(deduped, tmp_path / "serial")
    summary, pool = f2_pool.run([deduped], tmp_path / "pool", workers=3, start=method, benchmarks=BENCH, log=lambda m: None)
    assert snapshot(tmp_path / "pool") == snapshot(tmp_path / "serial")
    assert (summary["rows"], summary["kept"], summary["dropped_by_f2"], summary["errors"]) == (168, 165, 3, 0)
    assert summary["run_f2_py_sha256"] == RUN_F2.sha256(Path(RUN_F2.__file__))
    assert [p["input"].rsplit("/", 2)[-2:] for p in summary["per_file"]] == [
        ["code-go", "part-00000.parquet"], ["code-go", "part-00001.parquet"], ["en-dclm", "part-00000.parquet"],
        ["en-dclm", "part-00001.parquet"]]  # input order, as run_f2.py writes it, not the order the parts finished
    assert (pool["workers"], pool["start_method"], pool["parts"]) == (3, method, 4)
    on_disk = json.loads((tmp_path / "pool" / "f2_summary.json").read_text(encoding="utf-8"))
    assert set(on_disk) == {"set_sha256", "run_f2_py_sha256", "files", "rows", "kept", "dropped_by_f2", "errors", "seconds",
                            "per_file"}  # run_f2.py's summary, nothing about the pool
    assert LAB_CANARY not in json.dumps(on_disk)


def test_one_worker_runs_in_process(tmp_path, deduped):
    summary, pool = f2_pool.run([deduped], tmp_path / "one", workers=1, benchmarks=BENCH, log=lambda m: None)
    serial(deduped, tmp_path / "serial")
    assert pool["start_method"] == "in-process" and snapshot(tmp_path / "one") == snapshot(tmp_path / "serial")


def test_rerun_skips_finished_parts(tmp_path, deduped):
    f2_pool.run([deduped], tmp_path / "out", workers=2, start=METHODS[0], benchmarks=BENCH, log=lambda m: None)
    part = tmp_path / "out" / "en-dclm" / "part-00000.parquet"
    mtime = part.stat().st_mtime_ns
    summary, _ = f2_pool.run([deduped], tmp_path / "out", workers=2, start=METHODS[0], benchmarks=BENCH, log=lambda m: None)
    assert part.stat().st_mtime_ns == mtime and summary["dropped_by_f2"] == 3


def test_a_broken_part_does_not_stop_the_others(tmp_path, deduped):
    bad = deduped / "zz-broken" / "part-00000.parquet"
    bad.parent.mkdir()
    pq.write_table(pa.Table.from_pylist([{"doc_id": "x", "body": "no text column"}]), bad)
    with pytest.raises(f2_pool.Stop, match=r"1 of 5 part\(s\) did not finish, e.g. zz-broken/part-00000.parquet: .*text"):
        f2_pool.run([deduped], tmp_path / "out", workers=2, start=METHODS[0], benchmarks=BENCH, log=lambda m: None)
    assert (tmp_path / "out" / "en-dclm" / "part-00000.parquet.f2.json").is_file()  # the others finished
    assert not (tmp_path / "out" / "f2_summary.json").exists()  # no summary: the run did not finish


def test_doc_errors_are_reported_like_run_f2(tmp_path, deduped, monkeypatch):
    class Boom:
        set_sha256 = RUN_F2.SET_SHA256

        def check(self, text):
            if "7" in text:
                raise RuntimeError("boom")
            return False, []
    def setup(script, benchmarks, in_worker=True):  # monkeypatch restores the globals after the test
        monkeypatch.setattr(f2_pool, "_MOD", RUN_F2)
        monkeypatch.setattr(f2_pool, "_FP", Boom())
        monkeypatch.setattr(f2_pool, "_CODE", "x")
    monkeypatch.setattr(f2_pool, "_setup", setup)
    summary, _ = f2_pool.run([deduped], tmp_path / "out", workers=1, log=lambda m: None)
    assert summary["errors"] > 0 and summary["kept"] + summary["errors"] == summary["rows"]


@pytest.mark.parametrize("workers", [0, "2", True])
def test_bad_workers(tmp_path, deduped, workers):
    with pytest.raises(f2_pool.Stop, match="workers"):
        f2_pool.run([deduped], tmp_path / "out", workers=workers)


def test_out_inside_inputs_is_refused_before_loading(tmp_path, deduped):
    with pytest.raises(f2_pool.Stop, match="overlap"):
        f2_pool.run([deduped], deduped / "final", workers=2)


def test_cli_refuses_overlap(tmp_path, deduped):
    p = subprocess.run([sys.executable, "-I", str(PIPELINE / "f2_pool.py"), "--inputs", str(deduped), "--out",
                        str(deduped / "final"), "--workers", "2"], capture_output=True, text=True)
    assert p.returncode == 1 and "overlap" in p.stderr


CRASHING_F2 = """import importlib.util, os
spec = importlib.util.spec_from_file_location("real_run_f2", {real!r})
real = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real)
G9, SET, SET_SHA256, sha256, fingerprints = real.G9, real.SET, real.SET_SHA256, real.sha256, real.fingerprints

def run_file(src, dst, fp, code):
    if "crash" in str(src):
        os._exit(3)  # a worker that dies (killed, out of memory)
    return real.run_file(src, dst, fp, code)
"""


def crashing_script(tmp_path):
    path = tmp_path / "crashing_run_f2.py"
    path.write_text(CRASHING_F2.format(real=str(Path(RUN_F2.__file__))), encoding="utf-8")
    return path


@pytest.mark.parametrize("method", METHODS)
def test_a_worker_that_dies_fails_its_part_and_does_not_hang(tmp_path, deduped, method):
    crash = deduped / "zz-crash" / "part-00000.parquet"
    crash.parent.mkdir()
    pq.write_table(pa.Table.from_pylist(docs("zz-crash", 3)), crash)
    with pytest.raises(f2_pool.Stop, match=r"did not finish, e.g. .*a worker died"):
        f2_pool.run([deduped], tmp_path / "out", workers=2, start=method, benchmarks=BENCH,
                    script=crashing_script(tmp_path), log=lambda m: None)
    assert not (tmp_path / "out" / "f2_summary.json").exists()


def test_a_broken_set_stops_before_any_worker_starts(tmp_path, deduped, monkeypatch):
    bad = tmp_path / "bad_set"
    bad.mkdir()
    (bad / "SHA256SUMS").write_text("x\n", encoding="utf-8")
    monkeypatch.setenv("F2_FINGERPRINTS", str(bad))
    with pytest.raises(f2_pool.Stop, match="not the pinned"):
        f2_pool.run([deduped], tmp_path / "out", workers=2, start="spawn", benchmarks=BENCH, log=lambda m: None)
    assert not (tmp_path / "out").exists()


def test_relative_inputs_are_reported_as_given_like_run_f2(tmp_path, deduped, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f2_pool.run([Path("deduped") / "train"], tmp_path / "out", workers=1, benchmarks=BENCH, log=lambda m: None)
    report = json.loads((tmp_path / "out" / "code-go" / "part-00000.parquet.f2.json").read_text(encoding="utf-8"))
    assert report["input"] == "deduped/train/code-go/part-00000.parquet"  # as run_f2.py writes it: the path as given


def test_the_summary_names_this_runs_script(tmp_path, deduped):
    f2_pool.run([deduped], tmp_path / "a", workers=1, benchmarks=BENCH, script=crashing_script(tmp_path), log=lambda m: None)
    summary, _ = f2_pool.run([deduped], tmp_path / "b", workers=2, start=METHODS[0], benchmarks=BENCH, log=lambda m: None)
    assert summary["run_f2_py_sha256"] == RUN_F2.sha256(Path(RUN_F2.__file__))
