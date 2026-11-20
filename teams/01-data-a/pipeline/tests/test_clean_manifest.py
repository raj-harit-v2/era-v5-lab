"""Tests for clean_manifest.py: the check of the clean stage's sample manifest, used by --plan and by the clean job.
Made-up manifests; nothing is read but the files made here.

  python -m pytest teams/01-data-a/pipeline/tests/test_clean_manifest.py
"""
import json

import pytest

import clean_manifest as cm
from conftest import made_up_manifest

PARTS = {"train": 2, "heldout": 1}


def write(tmp_path, text):
    p = tmp_path / "manifest.json"
    p.write_text(text, encoding="utf-8")
    return p


def rewrite(tmp_path, edit):
    """A valid made-up manifest, changed by edit(data), written; returns (path, its sha256)."""
    data = json.loads(made_up_manifest(PARTS))
    edit(data)
    p = write(tmp_path, json.dumps(data))
    return p, cm.sha256(p)


def test_a_consistent_pinned_manifest_is_returned(tmp_path):
    p = write(tmp_path, made_up_manifest(PARTS))
    data = cm.validate(p, cm.sha256(p), PARTS)
    assert len(data["shards"]) == 3 and data["total_docs"] == 6


def test_any_part_count_is_allowed_when_the_run_config_says_so(tmp_path):
    parts = {"train": 5, "heldout": 4}  # not the 48 + 38 of sample v0
    p = write(tmp_path, made_up_manifest(parts))
    assert len(cm.validate(p, cm.sha256(p), parts)["shards"]) == 9


def test_a_missing_manifest_is_named(tmp_path):
    with pytest.raises(cm.ManifestError, match="manifest.json is not there"):
        cm.validate(tmp_path / "manifest.json", "0" * 64, PARTS)


def test_a_manifest_that_is_not_the_pinned_file_is_refused(tmp_path):
    p = write(tmp_path, made_up_manifest(PARTS))
    with pytest.raises(cm.ManifestError, match="has sha256 .*, the pin is 111111111111"):
        cm.validate(p, "1" * 64, PARTS)


@pytest.mark.parametrize("text", ["not json", "[]", '{"shards": []}', '{"shards": 3, "total_docs": 1}',
                                  '{"shards": [1], "total_docs": 1}', '{"shards": [], "total_docs": "0"}'])
def test_a_manifest_without_shards_and_total_docs_is_refused(tmp_path, text):
    p = write(tmp_path, text)
    with pytest.raises(cm.ManifestError, match="no list of 'shards' .objects. and integer 'total_docs'"):
        cm.validate(p, cm.sha256(p), PARTS)


def test_split_counts_must_match_expected_parts(tmp_path):
    p = write(tmp_path, made_up_manifest(PARTS))
    with pytest.raises(cm.ManifestError, match="expected_parts says"):
        cm.validate(p, cm.sha256(p), {"train": 2, "heldout": 2})


def test_a_split_other_than_train_and_heldout_is_refused(tmp_path):
    parts = {"train": 1, "val": 1}
    p = write(tmp_path, made_up_manifest(parts))
    with pytest.raises(cm.ManifestError, match="unexpected part path 'val/code-go/part-00000.parquet'"):
        cm.validate(p, cm.sha256(p), parts)


@pytest.mark.parametrize("path", ["/abs/code-go/part-0.parquet", "train/../code-go/part-0.parquet", "train\\code-go\\part-0.parquet",
                                  "train/part-0.parquet", "train/code-go/sub/part-0.parquet"])
def test_a_part_path_that_is_not_split_pack_file_is_refused(tmp_path, path):
    p, sha = rewrite(tmp_path, lambda d: d["shards"][0].update(path=path))
    with pytest.raises(cm.ManifestError, match="unexpected part path"):
        cm.validate(p, sha, PARTS)


def test_a_duplicate_part_is_refused(tmp_path):
    p, sha = rewrite(tmp_path, lambda d: d["shards"][1].update(path=d["shards"][0]["path"]))
    with pytest.raises(cm.ManifestError, match="duplicate or inconsistent manifest entry train/code-go/part-00000.parquet"):
        cm.validate(p, sha, PARTS)


@pytest.mark.parametrize("key, value", [("split", "heldout"), ("pack_id", "en-dclm")])
def test_an_entry_that_disagrees_with_its_own_path_is_refused(tmp_path, key, value):
    p, sha = rewrite(tmp_path, lambda d: d["shards"][0].update({key: value}))
    # changing the split also changes the counts; the counts are checked first, so give the check what it expects
    parts = {"train": 1, "heldout": 2} if key == "split" else PARTS
    with pytest.raises(cm.ManifestError, match="duplicate or inconsistent manifest entry"):
        cm.validate(p, sha, parts)


@pytest.mark.parametrize("key, value", [("rows", None), ("rows", "2"), ("bytes", None), ("sha256", None), ("sha256", "abc")])
def test_an_entry_without_rows_bytes_and_sha256_is_refused(tmp_path, key, value):
    p, sha = rewrite(tmp_path, lambda d: d["shards"][0].update({key: value}))
    with pytest.raises(cm.ManifestError, match="lacks rows, bytes or a sha256"):
        cm.validate(p, sha, PARTS)


def test_the_parts_must_add_up_to_total_docs(tmp_path):
    p, sha = rewrite(tmp_path, lambda d: d.update(total_docs=7))
    with pytest.raises(cm.ManifestError, match="do not add up to total_docs"):
        cm.validate(p, sha, PARTS)


def test_a_requested_part_must_be_in_the_manifest(tmp_path):
    p = write(tmp_path, made_up_manifest(PARTS))
    known = "train/code-go/part-00001.parquet"
    assert cm.validate(p, cm.sha256(p), PARTS, only=[known])
    with pytest.raises(cm.ManifestError, match="not in the manifest: train/code-go/part-00009.parquet"):
        cm.validate(p, cm.sha256(p), PARTS, only=[known, "train/code-go/part-00009.parquet"])
