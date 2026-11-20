"""Tests for the stdio checker's hardening: preflight_isolation (task file readable by a sandbox uid, network open),
the seccomp socket filter, and the bounded no-follow read of outputs.json. Fixtures only, never training data.
The preflight tests that start a sandbox uid need Linux and root (skipped elsewhere, like any local-runner test)."""
from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
from pytest import fixture

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stdio_check  # noqa: E402

needs_root_linux = pytest.mark.skipif(
    not (sys.platform.startswith("linux") and os.geteuid() == 0),
    reason="UNTESTED: needs Linux and root to switch to a sandbox uid")


@fixture(autouse=True)
def fresh_preflight(monkeypatch):
    monkeypatch.setattr(stdio_check, "_PREFLIGHT_OK", [])
    monkeypatch.delenv("G10_STDIO_SECRET_PATHS", raising=False)


@fixture
def open_dir():
    """A world-traversable scratch folder (pytest's tmp_path is 0700 and would hide the file from the sandbox uid)."""
    d = Path(tempfile.mkdtemp(prefix="g10hard-"))
    os.chmod(d, 0o755)
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


def test_preflight_refuses_when_no_secret_paths_are_named():
    with pytest.raises(RuntimeError, match="G10_STDIO_SECRET_PATHS"):
        stdio_check.preflight_isolation()


@needs_root_linux
def test_preflight_refuses_a_world_readable_task_file(monkeypatch, open_dir):
    task_file = open_dir / "rl_tasks.jsonl"
    task_file.write_text("FIXTURE\n")
    os.chmod(task_file, 0o644)
    monkeypatch.setenv("G10_STDIO_SECRET_PATHS", str(task_file))
    with pytest.raises(RuntimeError, match="a sandbox uid can read"):
        stdio_check.preflight_isolation()
    assert stdio_check._PREFLIGHT_OK == []  # a refusal is never cached


@needs_root_linux
def test_preflight_passes_when_the_parent_folder_is_0700(monkeypatch, open_dir):
    inner = open_dir / "private"
    inner.mkdir(mode=0o700)
    os.chmod(inner, 0o700)
    task_file = inner / "rl_tasks.jsonl"
    task_file.write_text("FIXTURE\n")
    os.chmod(task_file, 0o644)  # the file itself is open; the folder above it is not
    monkeypatch.setenv("G10_STDIO_SECRET_PATHS", str(task_file))
    stdio_check.preflight_isolation()
    assert stdio_check._PREFLIGHT_OK == [True]


@needs_root_linux
def test_preflight_refuses_a_secret_path_that_does_not_exist(monkeypatch, open_dir):
    monkeypatch.setenv("G10_STDIO_SECRET_PATHS", str(open_dir / "rl_task.jsonl"))  # a typo for rl_tasks.jsonl
    with pytest.raises(RuntimeError, match="names a path that does not exist"):
        stdio_check.preflight_isolation()
    assert stdio_check._PREFLIGHT_OK == []


@needs_root_linux
def test_preflight_refuses_a_dangling_symlink(monkeypatch, open_dir):
    link = open_dir / "rl_tasks.jsonl"
    link.symlink_to(open_dir / "gone.jsonl")
    monkeypatch.setenv("G10_STDIO_SECRET_PATHS", str(link))
    with pytest.raises(RuntimeError, match="does not exist"):
        stdio_check.preflight_isolation()


@needs_root_linux
def test_preflight_refuses_a_0711_folder_that_holds_a_readable_file(monkeypatch, open_dir):
    folder = open_dir / "bundle"
    folder.mkdir()
    (folder / "rl_tasks.jsonl").write_text("FIXTURE\n")
    os.chmod(folder / "rl_tasks.jsonl", 0o644)
    os.chmod(folder, 0o711)  # cannot be listed, but can be entered
    monkeypatch.setenv("G10_STDIO_SECRET_PATHS", str(folder))
    with pytest.raises(RuntimeError, match="a sandbox uid can read"):
        stdio_check.preflight_isolation()
    assert stdio_check._PREFLIGHT_OK == []


@needs_root_linux
def test_preflight_passes_for_a_0700_folder_named_as_a_secret(monkeypatch, open_dir):
    folder = open_dir / "bundle"
    folder.mkdir()
    (folder / "rl_tasks.jsonl").write_text("FIXTURE\n")
    os.chmod(folder, 0o700)
    monkeypatch.setenv("G10_STDIO_SECRET_PATHS", str(folder))
    stdio_check.preflight_isolation()
    assert stdio_check._PREFLIGHT_OK == [True]


def test_socket_filter_is_well_formed_on_known_arches(monkeypatch):
    import platform
    for arch, n_ins in (("x86_64", 12), ("aarch64", 11)):
        monkeypatch.setattr(platform, "machine", lambda a=arch: a)
        stdio_check._socket_filter.cache_clear(); stdio_check._seccomp_fprog.cache_clear()
        prog = stdio_check._socket_filter()
        assert len(prog) == 8 * n_ins
    monkeypatch.setattr(platform, "machine", lambda: "riscv64")
    stdio_check._socket_filter.cache_clear(); stdio_check._seccomp_fprog.cache_clear()
    assert stdio_check._socket_filter() is None  # unknown arch: no filter, the network probe decides
    stdio_check._socket_filter.cache_clear(); stdio_check._seccomp_fprog.cache_clear()


@needs_root_linux
def test_network_probe_connects_without_the_filter_and_is_refused_with_it():
    """Same child, same uid: only the seccomp filter differs. (Skips the 'connects' half when the machine is offline.)"""
    probe = ("import socket\ntry:\n    socket.socket(socket.AF_INET, socket.SOCK_STREAM).close(); print('INET-OK')\n"
             "except OSError as e:\n    print('INET-DENIED', type(e).__name__)\n"
             "a, b = socket.socketpair(); a.close(); b.close(); print('UNIX-OK')\n")
    uid = stdio_check._next_uid()
    kw = dict(user=uid, group=uid, extra_groups=[], capture_output=True, text=True, timeout=20, env={}, cwd="/")
    before = subprocess.run([sys.executable, "-S", "-c", probe], **kw)
    after = subprocess.run([sys.executable, "-S", "-c", probe], preexec_fn=stdio_check._sandbox_preexec, **kw)
    assert "INET-OK" in before.stdout, before
    assert "INET-DENIED PermissionError" in after.stdout and "UNIX-OK" in after.stdout, after


@needs_root_linux
def test_reference_still_scores_one_and_wrong_answer_zero_under_the_filter(monkeypatch, open_dir):
    inner = open_dir / "private"
    inner.mkdir(mode=0o700)
    os.chmod(inner, 0o700)
    (inner / "t.jsonl").write_text("FIXTURE\n")
    monkeypatch.setenv("G10_STDIO_SECRET_PATHS", str(inner / "t.jsonl"))
    monkeypatch.setattr(stdio_check, "RUNNER_KIND", "local")
    task = {"id": "fx", "time_limit_s": 4, "tests": [{"input": "1 2\n", "output": "3\n"}, {"input": "5 7\n", "output": "12\n"}]}
    good = "```python\na, b = map(int, input().split())\nprint(a + b)\n```"
    bad = "```python\na, b = map(int, input().split())\nprint(a - b)\n```"
    assert stdio_check.score(task, good)["reward"] == 1
    assert stdio_check.score(task, bad)["reward"] == 0


def test_a_symlink_to_a_fifo_is_refused_promptly_not_followed(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("no mkfifo here")
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    link = tmp_path / "outputs.json"
    link.symlink_to(fifo)
    t0 = time.time()
    with pytest.raises((OSError, ValueError)):
        stdio_check._verifier.read_result_bytes(link, limit=stdio_check.OUTPUTS_MAX_BYTES)
    assert time.time() - t0 < 2.0


def test_the_outputs_read_is_bounded_and_the_default_limit_is_unchanged(tmp_path):
    f = tmp_path / "outputs.json"
    f.write_bytes(b"x" * 101)
    with pytest.raises(ValueError, match="too large"):
        stdio_check._verifier.read_result_bytes(f, limit=100)
    f.write_bytes(b"x" * 100)
    assert len(stdio_check._verifier.read_result_bytes(f, limit=100)) == 100
    assert stdio_check._verifier.read_result_bytes.__defaults__[-1] == stdio_check._verifier.MAX_RESULT_BYTES
    assert stdio_check.OUTPUTS_MAX_BYTES == 10_000_000 and stat.S_ISREG(f.stat().st_mode)


def test_run_program_returns_no_readable_output_for_a_fifo_symlink(monkeypatch):
    """The host-side read in run_program: a runner that leaves outputs.json as a symlink to a pipe must give a normal
    'no readable output file' result (reward 0), not hang the scorer."""
    monkeypatch.setattr(stdio_check, "RUNNER_KIND", "local_unisolated")

    def fake_run_local(w, time_limit_s, n_inputs):
        os.mkfifo(w / "fifo")
        os.symlink(w / "fifo", w / "outputs.json")
        return 0

    monkeypatch.setattr(stdio_check, "_run_local", fake_run_local)
    t0 = time.time()
    assert stdio_check.run_program("print(1)", ["\n"], 2) == "no readable output file"
    assert time.time() - t0 < 5.0
