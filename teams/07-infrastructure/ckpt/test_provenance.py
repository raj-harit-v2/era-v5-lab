"""Source provenance in checkpoint manifests (issue #298). CPU only, about 20 s.

Run from teams/07-infrastructure/:  python -m pytest -q ckpt/test_provenance.py

In simple words: a checkpoint must say which code made it. git_sha comes from GIT_SHA, else from the
checkout, else it says "none" out loud. It is recorded, not compared, so a docs-only commit does not stop
the run. code_sha256 (the files that change the numbers) is compared, so a real code change still stops it.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
sys.path.insert(0, str(TEAM))
from ckpt.ckpt import ENV_MUST_MATCH, Checkpointer, code_sha256, env_diff, env_manifest, provenance  # noqa: E402
from common.events import read_all  # noqa: E402

HEAD = subprocess.run(["git", "-C", str(TEAM), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
needs_git = pytest.mark.skipif(not HEAD, reason="needs a git checkout")

# Prints env_manifest() as JSON. Run from another folder to prove the cwd does not matter.
PRINT_ENV = f"import sys, json; sys.path.insert(0, {str(TEAM)!r}); from ckpt.ckpt import env_manifest; " \
            "print(json.dumps(env_manifest()))"


def env_in_subprocess(tmp_path, **extra):
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_SHA", "GIT_DIR")}
    env.update(V5_EVENTS_DIR=str(tmp_path / "events"), **extra)
    out = subprocess.run([sys.executable, "-c", PRINT_ENV], cwd=tmp_path, env=env, capture_output=True, text=True,
                         check=True)
    return json.loads(out.stdout), read_all(str(tmp_path / "events"))


@needs_git
def test_checkout_without_git_sha_records_head_from_outside_repo(tmp_path):
    env, events = env_in_subprocess(tmp_path)
    assert env["git_sha"] == HEAD and len(env["git_sha"]) == 40
    assert env["git_sha_source"] == "git"
    assert isinstance(env["git_dirty"], bool)
    assert not [e for e in events if e["event"].startswith("checkpoint.provenance")]


@needs_git
def test_git_sha_env_wins_and_matching_head_is_quiet(tmp_path):
    env, events = env_in_subprocess(tmp_path, GIT_SHA=HEAD[:12])
    assert (env["git_sha"], env["git_sha_source"]) == (HEAD[:12], "env")
    assert "git_sha_checkout" not in env and not events


@needs_git
def test_git_sha_env_disagreeing_with_checkout_records_both_and_warns(tmp_path):
    env, events = env_in_subprocess(tmp_path, GIT_SHA="0" * 40)
    assert (env["git_sha"], env["git_sha_source"], env["git_sha_checkout"]) == ("0" * 40, "env", HEAD)
    assert [e["event"] for e in events] == ["checkpoint.provenance_mismatch"]


def test_no_git_metadata_says_none_and_warns(tmp_path):
    env, events = env_in_subprocess(tmp_path, GIT_DIR=str(tmp_path / "no-git"))
    assert (env["git_sha"], env["git_sha_source"], env["git_dirty"]) == ("none", "none", None)
    assert [(e["event"], e["missing"]) for e in events] == [("checkpoint.provenance_unknown", "git")]


def test_git_sha_is_recorded_not_compared():
    assert "git_sha" not in ENV_MUST_MATCH and "code_sha256" in ENV_MUST_MATCH
    now = env_manifest()
    assert env_diff(dict(now, git_sha="another-commit"), now, ENV_MUST_MATCH) == {}


def test_code_change_is_a_mismatch_and_old_manifest_is_not_checked(tmp_path):
    f = tmp_path / "model.py"
    f.write_text("W = 1\n")
    before = env_manifest(code_paths=[str(f)])
    f.write_text("W = 2\n")
    now = env_manifest(code_paths=[str(f)])
    assert set(env_diff(before, now, ENV_MUST_MATCH)) == {"code_sha256"}
    old = {k: v for k, v in before.items() if k != "code_sha256"}      # a manifest from before issue #298
    assert env_diff(old, now, ENV_MUST_MATCH) == {}


def test_code_sha256_does_not_depend_on_path_or_order(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    for d in (a, b):
        (d / "x.py").write_text("x = 1\n"), (d / "y.py").write_text("y = 2\n")
    assert code_sha256([str(a / "x.py"), str(a / "y.py")]) == code_sha256([str(b / "y.py"), str(b / "x.py")])
    assert code_sha256([str(a / "x.py")]) != code_sha256()


def test_missing_code_path_fails_at_start(tmp_path):
    with pytest.raises(FileNotFoundError):
        Checkpointer("r", str(tmp_path / "l"), str(tmp_path / "s"), code_paths=[str(tmp_path / "typo.py")])


def test_v5_code_paths_env_is_part_of_the_hash(tmp_path, monkeypatch):
    f = tmp_path / "loader.py"
    f.write_text("L = 1\n")
    plain = code_sha256()
    monkeypatch.setenv("V5_CODE_PATHS", str(f))
    assert code_sha256() == code_sha256([str(f)]) != plain


def test_restore_test_entry_point_writes_provenance(tmp_path):
    """Hema's repro: the restore test's manifest now names the commit and the code, from any cwd."""
    env = {k: v for k, v in os.environ.items() if k != "GIT_SHA"}
    env["CUDA_VISIBLE_DEVICES"] = ""
    subprocess.run([sys.executable, str(TEAM / "jobs" / "restore_test" / "restore_test.py"), "--out",
                    str(tmp_path / "out")], cwd=tmp_path, env=env, check=True, capture_output=True, timeout=300)
    man = json.loads(next((tmp_path / "out" / "ckpt_store").glob("restore-b/main/step_*/MANIFEST.json")).read_text())
    if HEAD:
        assert (man["env"]["git_sha"], man["env"]["git_sha_source"]) == (HEAD, "git")
    assert len(man["env"]["code_sha256"]) == 64


def teardown_function():
    provenance.cache_clear()
