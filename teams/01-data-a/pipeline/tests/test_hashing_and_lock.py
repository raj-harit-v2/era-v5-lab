"""Tests for hashing.py (sha256 of files, each computed once) and runlock.py (one writer per output folder).

  python -m pytest teams/01-data-a/pipeline/tests -q
"""
import errno
import hashlib
import json
import os
import subprocess
import sys
import time

import pytest

from conftest import PIPELINE
import hashing
import runlock
from hashing import HashCache


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_a_file_is_hashed_once(tmp_path):
    f = write(tmp_path / "a.bin", b"x" * 3_000_000)  # more than one 1 MiB block
    c = HashCache()
    assert c.sha256(f) == sha(f) == c.sha256(f)
    assert (c.misses, c.hits) == (1, 1)


def test_a_rewritten_file_is_hashed_again(tmp_path):
    f = write(tmp_path / "a.bin", b"first")
    c = HashCache()
    first = c.sha256(f)
    tmp = write(tmp_path / "a.bin.tmp", b"second")  # how every writer of the pipeline replaces a file
    os.replace(tmp, f)
    assert c.sha256(f) == sha(f) != first


def test_an_in_place_edit_of_the_same_size_is_hashed_again(tmp_path):
    f = write(tmp_path / "a.bin", b"aaaa")
    c = HashCache()
    c.sha256(f)
    time.sleep(0.02)
    with open(f, "r+b") as h:
        h.write(b"bbbb")
    os.utime(f, ns=(time.time_ns(), time.time_ns()))  # an edit moves mtime
    assert c.sha256(f) == sha(f)


def test_a_hard_link_has_the_hash_of_its_source(tmp_path):
    src = write(tmp_path / "src.bin", b"shared bytes")
    c = HashCache()
    h = c.sha256(src)
    link = tmp_path / "link.bin"
    os.link(src, link)
    assert c.sha256(link) == h == sha(link)  # found again (Windows) or hashed once more (Linux: the link moves ctime)


def test_the_cache_survives_on_disk(tmp_path):
    f = write(tmp_path / "a.bin", b"data")
    store = tmp_path / "cache" / "sha256.json"
    first = HashCache(store)
    first.sha256(f)
    first.save()
    again = HashCache(store)
    assert again.sha256(f) == sha(f) and (again.hits, again.misses) == (1, 0)


@pytest.mark.parametrize("content", ["not json", "[]", '{"version": 1, "sha256": {}}', '{"version": 2, "sha256": "x"}'])
def test_a_broken_or_old_cache_file_is_ignored(tmp_path, content):
    store = write(tmp_path / "sha256.json", content.encode("utf-8"))
    f = write(tmp_path / "a.bin", b"data")
    c = HashCache(store)
    assert c.sha256(f) == sha(f) and c.misses == 1


def test_a_bad_entry_is_never_trusted(tmp_path):
    f = write(tmp_path / "a.bin", b"data")
    store = tmp_path / "sha256.json"
    store.write_text(json.dumps({"version": hashing.VERSION, "sha256": {hashing.identity(f): "short"}}), encoding="utf-8")
    assert HashCache(store).sha256(f) == sha(f)


def test_many_files_in_parallel_in_order(tmp_path):
    files = [write(tmp_path / f"{i:03d}.bin", os.urandom(1000 + i)) for i in range(64)]
    got = HashCache(workers=8).sha256_many(files)
    assert list(got) == files and all(got[f] == sha(f) for f in files)


def test_disabled_always_hashes(tmp_path):
    f = write(tmp_path / "a.bin", b"data")
    c = HashCache(tmp_path / "sha256.json", enabled=False)
    assert c.sha256(f) == c.sha256(f) == sha(f) and c.hits == 0
    c.save()
    assert not (tmp_path / "sha256.json").exists()


# --- runlock --------------------------------------------------------------------------------------------------------
def test_one_writer_per_folder(tmp_path):
    out = tmp_path / "out"
    with runlock.exclusive(out) as lock:
        assert lock == out.resolve().with_name("out.lock") and not out.exists()  # next to the folder, not inside it
        with pytest.raises(runlock.Busy, match="another process"):
            with runlock.exclusive(out):
                pass
    with runlock.exclusive(out):  # released
        pass


def test_a_killed_holder_releases_the_lock(tmp_path):
    out = tmp_path / "out"
    code = ("import sys, os; sys.path.insert(0, sys.argv[1]); import runlock\n"
            "ctx = runlock.exclusive(sys.argv[2]); ctx.__enter__(); os._exit(0)")
    subprocess.run([sys.executable, "-I", "-B", "-c", code, str(PIPELINE), str(out)], check=True)  # dies holding it
    with runlock.exclusive(out):  # the system dropped it with the process
        pass


# --- the review of the scale pass (14 Nov) ---------------------------------------------------------------------------
def test_an_in_place_edit_that_puts_mtime_back_is_hashed_again(tmp_path):
    """The change time is in the key: ctime on Linux, NTFS ChangeTime on Windows (os.stat's st_ctime there is the
    creation time, which an edit does not move)."""
    f = write(tmp_path / "a.bin", b"aaaa")
    st = os.stat(f)
    c = HashCache()
    c.sha256(f)
    time.sleep(0.02)
    with open(f, "r+b") as h:
        h.write(b"bbbb")
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))  # same size, mtime put back
    assert os.stat(f).st_mtime_ns == st.st_mtime_ns and c.sha256(f) == sha(f)


def test_remember_records_a_link_without_reading_it(tmp_path, monkeypatch):
    src = write(tmp_path / "src.bin", b"shared bytes")
    c = HashCache()
    h = c.sha256(src)
    link = tmp_path / "link.bin"
    os.link(src, link)
    c.remember(link, h)
    monkeypatch.setattr(hashing, "file_sha256", lambda p: pytest.fail(f"{p} was read"))
    assert c.sha256(link) == c.sha256(src) == h  # the same file under both names, read by neither
    monkeypatch.undo()
    audit = HashCache(enabled=False)
    audit.remember(link, "0" * 64)  # an audit run trusts nothing: it reads the file
    assert audit.sha256(link) == h


def test_code_sha256_covers_the_helper_modules(tmp_path, monkeypatch):
    for name in (*hashing.HELPERS, "script.py", "extra.py"):
        write(tmp_path / name, name.encode())
    monkeypatch.setattr(hashing, "HERE", tmp_path)
    first, files = hashing.code_sha256(tmp_path / "script.py")
    assert list(files) == ["script.py", *hashing.HELPERS] and all(files[n] == sha(tmp_path / n) for n in files)
    write(tmp_path / "arrowtools.py", b"a fix in a helper")
    second, _ = hashing.code_sha256(tmp_path / "script.py")
    with_extra, files = hashing.code_sha256(tmp_path / "script.py", HashCache(), ("extra.py",))
    assert len({first, second, with_extra}) == 3 and "extra.py" in files


@pytest.mark.parametrize("err, outcome", [(errno.EAGAIN, "busy"), (errno.EACCES, "busy"), (errno.EDEADLK, "busy"),
                                          (errno.ENOLCK, "unlocked"), (errno.ENOSYS, "unlocked"),
                                          (errno.EOPNOTSUPP, "unlocked"), (errno.EIO, "raised")])
def test_only_a_lock_someone_holds_is_busy(tmp_path, monkeypatch, capsys, err, outcome):
    def refuse(f):
        raise OSError(err, os.strerror(err))
    monkeypatch.setattr(runlock, "_lock", refuse)
    out = tmp_path / "out"
    if outcome == "busy":
        with pytest.raises(runlock.Busy, match="another process"):
            with runlock.exclusive(out):
                pass
    elif outcome == "raised":  # an I/O error is not "busy": it is raised as it is
        with pytest.raises(OSError) as e:
            with runlock.exclusive(out):
                pass
        assert e.value.errno == err
    else:  # a file system that cannot lock: a warning, and the run goes on
        with runlock.exclusive(out) as lock:
            assert lock.name == "out.lock"
        assert "cannot lock files" in capsys.readouterr().err
