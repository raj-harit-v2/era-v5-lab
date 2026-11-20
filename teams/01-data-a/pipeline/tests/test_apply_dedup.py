"""Tests for apply_dedup.py: filter cleaned parts with dedup.py's remove_list.csv. Synthetic data only (conftest.py).

  python -m pytest teams/01-data-a/pipeline/tests -q
"""
import hashlib
import json
import subprocess
import sys

import pytest
import pyarrow.parquet as pq

from conftest import PARTS, PIPELINE
import apply_dedup as ad


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids(path):
    return pq.read_table(path).column("doc_id").to_pylist()


def test_removes_exactly_the_listed_rows(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"],
                            ["code-go", "train", "code-go/part-00000.parquet", 3, "g3"]])
    out = tmp_path / "deduped"
    s = ad.apply(cleaned, rl, out)
    part = out / "train" / "code-go" / "part-00000.parquet"
    assert ids(part) == ["g0", "g2", "g4"]
    src = cleaned / "train" / "code-go" / "part-00000.parquet"
    assert pq.read_schema(part) == pq.read_schema(src)
    kept_text = dict(zip(ids(part), pq.read_table(part).column("text").to_pylist()))
    assert kept_text == {r["doc_id"]: r["text"] for r in PARTS[("train", "code-go/part-00000.parquet")] if r["doc_id"] in kept_text}
    assert (s["totals"]["rows"], s["totals"]["removed"], s["totals"]["kept"]) == (13, 2, 11)
    assert s["by_pack"]["code-go"]["train"] == {"rows": 8, "removed": 2, "kept": 6}


def test_untouched_parts_are_byte_copies(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 0, "g0"]])
    out = tmp_path / "deduped"
    s = ad.apply(cleaned, rl, out)
    for split, part in [("train", "en-dclm/part-00000.parquet"), ("heldout", "code-go/part-00000.parquet"),
                        ("train", "code-go/part-00001.parquet")]:
        assert sha(out / split / part) == sha(cleaned / split / part)
    copied = {(p["split"], p["part"]): p["copied"] for p in s["parts"]}
    assert copied[("train", "en-dclm/part-00000.parquet")] is True
    assert copied[("train", "code-go/part-00000.parquet")] is False


def test_untouched_parts_are_hard_links_unless_copy(tmp_path, cleaned, write_remove_list):
    import os
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 0, "g0"]])
    src = cleaned / "train" / "en-dclm" / "part-00000.parquet"
    s = ad.apply(cleaned, rl, tmp_path / "linked")
    assert os.path.samefile(src, tmp_path / "linked" / "train" / "en-dclm" / "part-00000.parquet")
    assert {p["part"]: p["linked"] for p in s["parts"] if p["split"] == "train"} == {
        "code-go/part-00000.parquet": False, "code-go/part-00001.parquet": True, "en-dclm/part-00000.parquet": True}
    s = ad.apply(cleaned, rl, tmp_path / "copied", link=False)
    dst = tmp_path / "copied" / "train" / "en-dclm" / "part-00000.parquet"
    assert not os.path.samefile(src, dst) and sha(src) == sha(dst)
    assert not any(p["linked"] for p in s["parts"])


def test_same_doc_id_in_two_parts_only_the_listed_copy_goes(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go/part-00001.parquet", 0, "g0"]])
    out = tmp_path / "deduped"
    ad.apply(cleaned, rl, out)
    assert ids(out / "train" / "code-go" / "part-00001.parquet") == ["g5", "g6"]
    assert ids(out / "train" / "code-go" / "part-00000.parquet") == ["g0", "g1", "g2", "g3", "g4"]


def test_empty_remove_list_copies_everything(tmp_path, cleaned, write_remove_list):
    out = tmp_path / "deduped"
    s = ad.apply(cleaned, write_remove_list([]), out)
    assert s["totals"] == {"rows": 13, "removed": 0, "kept": 13}
    assert all(p["copied"] for p in s["parts"])


def test_windows_style_part_path_matches(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go\\part-00000.parquet", 2, "g2"]])
    out = tmp_path / "deduped"
    ad.apply(cleaned, rl, out)
    assert "g2" not in ids(out / "train" / "code-go" / "part-00000.parquet")


@pytest.mark.parametrize("row, message", [
    (["en-dclm", "train", "en-dclm/part-00000.parquet", 1, "WRONG"], "doc_id"),
    (["code-go", "train", "en-dclm/part-00000.parquet", 1, "e1"], "pack_id"),
    (["en-dclm", "train", "en-dclm/part-00009.parquet", 0, "e0"], "not found"),
    (["en-dclm", "train", "en-dclm/part-00000.parquet", 99, "e0"], "row"),
    (["code-go", "heldout", "code-go/part-00000.parquet", 0, "h0"], "held-out"),
    (["en-dclm", "valid", "en-dclm/part-00000.parquet", 0, "e0"], "split"),
    (["en-dclm", "train", "en-dclm/part-00000.parquet", -1, "e0"], "row_in_part"),
    (["en-dclm", "train", "en-dclm/part-00000.parquet", "x", "e0"], "row_in_part"),
])
def test_stops_and_writes_nothing(tmp_path, cleaned, write_remove_list, row, message):
    # a good row in the first part processed (code-go) and the bad one in the last (en-dclm): a run that checked each
    # part just before writing it would already have written code-go when it reached the bad row
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 0, "g0"], row])
    out = tmp_path / "deduped"
    with pytest.raises(ad.Stop, match=message):
        ad.apply(cleaned, rl, out)
    assert not out.exists() or not any(out.rglob("*"))


def test_unlisted_part_without_pack_id_stops_before_writing(tmp_path, cleaned, write_remove_list):
    path = cleaned / "train" / "en-dclm" / "part-00000.parquet"
    pq.write_table(pq.read_table(path).drop(["pack_id"]), path)
    out = tmp_path / "deduped"
    with pytest.raises(ad.Stop, match="no pack_id column"):
        ad.apply(cleaned, write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 0, "g0"]]), out)
    assert not out.exists() or not any(out.rglob("*"))


def test_codec_is_kept_and_row_groups_are_coalesced_across_batches(tmp_path, write_remove_list, monkeypatch):
    import pyarrow as pa
    monkeypatch.setattr(ad, "BATCH_ROWS", 700)  # small batches and groups, so the boundaries are exercised
    monkeypatch.setattr(ad, "ROW_GROUP_ROWS", 1000)
    root = tmp_path / "big"
    path = root / "train" / "sci" / "part-00000.parquet"
    path.parent.mkdir(parents=True)
    rows = [{"doc_id": f"d{i}", "text": f"t{i}", "pack_id": "sci"} for i in range(2500)]
    pq.write_table(pa.Table.from_pylist(rows), path, row_group_size=128, compression="zstd")  # the cleaner's tiny groups
    gone = [0, 127, 128, 699, 700, 701, 1399, 1400, 2499]
    rl = write_remove_list([["sci", "train", "sci/part-00000.parquet", r, f"d{r}"] for r in gone])
    out = tmp_path / "deduped"
    ad.apply(root, rl, out, splits=("train",))
    got = out / "train" / "sci" / "part-00000.parquet"
    assert ids(got) == [f"d{i}" for i in range(2500) if i not in gone]
    md = pq.ParquetFile(got).metadata
    sizes = [md.row_group(g).num_rows for g in range(md.num_row_groups)]
    assert sum(sizes) == 2491 and max(sizes) < 1000 + 700 and md.num_row_groups < 20  # coalesced, not 20 tiny groups
    assert md.row_group(0).column(0).compression == "ZSTD"


def test_stops_on_duplicate_rows(tmp_path, cleaned, write_remove_list):
    row = ["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]
    with pytest.raises(ad.Stop, match="twice"):
        ad.apply(cleaned, write_remove_list([row, row]), tmp_path / "deduped")


def test_stops_on_wrong_header(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([], header=["doc_id", "pack_id"])
    with pytest.raises(ad.Stop, match="header"):
        ad.apply(cleaned, rl, tmp_path / "deduped")


def test_stops_when_out_is_inside_cleaned(cleaned, write_remove_list):
    with pytest.raises(ad.Stop, match="overlap"):
        ad.apply(cleaned, write_remove_list([]), cleaned / "deduped")


def test_rerun_skips_finished_parts(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]])
    out = tmp_path / "deduped"
    ad.apply(cleaned, rl, out)
    part = out / "train" / "code-go" / "part-00000.parquet"
    mtime = part.stat().st_mtime_ns
    s = ad.apply(cleaned, rl, out)
    assert part.stat().st_mtime_ns == mtime
    assert all(p["skipped"] for p in s["parts"])
    assert s["totals"]["removed"] == 1


def test_rerun_redoes_a_changed_output(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]])
    out = tmp_path / "deduped"
    ad.apply(cleaned, rl, out)
    part = out / "train" / "code-go" / "part-00000.parquet"
    part.write_bytes(b"corrupted")
    s = ad.apply(cleaned, rl, out)
    assert ids(part) == ["g0", "g2", "g3", "g4"]
    assert {p["part"]: p["skipped"] for p in s["parts"] if p["split"] == "train"}["code-go/part-00000.parquet"] is False


def test_stops_on_stale_outputs(tmp_path, cleaned, write_remove_list):
    out = tmp_path / "deduped"
    ad.apply(cleaned, write_remove_list([]), out)
    stale = out / "train" / "old-pack" / "part-00000.parquet"
    stale.parent.mkdir(parents=True)
    stale.write_bytes((out / "train" / "en-dclm" / "part-00000.parquet").read_bytes())
    with pytest.raises(ad.Stop, match="earlier run"):
        ad.apply(cleaned, write_remove_list([], name="again.csv"), out)


def test_train_only(tmp_path, cleaned, write_remove_list):
    import shutil
    shutil.rmtree(cleaned / "heldout")
    s = ad.apply(cleaned, write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]]),
                 tmp_path / "deduped", splits=("train",))
    assert s["totals"] == {"rows": 11, "removed": 1, "kept": 10}


def test_summary_has_ids_and_hashes_only(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]])
    out = tmp_path / "deduped"
    ad.apply(cleaned, rl, out)
    text = (out / "apply_dedup_summary.json").read_text(encoding="utf-8")
    assert "synthetic text" not in text
    s = json.loads(text)
    assert s["remove_list"]["sha256"] == sha(rl) and s["remove_list"]["rows"] == 1
    assert len(s["code_sha256"]) == 64
    assert not list(out.rglob("*.tmp"))


def test_cli_exit_code_and_message(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "heldout", "code-go/part-00000.parquet", 0, "h0"]])
    p = subprocess.run([sys.executable, "-I", str(PIPELINE / "apply_dedup.py"), "--cleaned", str(cleaned),
                        "--remove-list", str(rl), "--out", str(tmp_path / "deduped")], capture_output=True, text=True)
    assert p.returncode == 1 and "held-out" in p.stderr
    ok = write_remove_list([], name="empty.csv")
    p = subprocess.run([sys.executable, "-I", str(PIPELINE / "apply_dedup.py"), "--cleaned", str(cleaned),
                        "--remove-list", str(ok), "--out", str(tmp_path / "deduped2")], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


# --- edge cases at scale (the scale audit, 14 Nov) ------------------------------------------------------------------
def write_part(root, split, part, rows, **kw):
    import pyarrow as pa
    path = root / split / part
    path.parent.mkdir(parents=True, exist_ok=True)
    empty = pa.table({"doc_id": pa.array([], pa.string()), "text": pa.array([], pa.string()),
                      "pack_id": pa.array([], pa.string())})
    pq.write_table(pa.Table.from_pylist(rows) if rows else empty, path, **kw)
    return path


def test_a_killed_runs_hard_linked_tmp_never_touches_the_input(tmp_path, cleaned, write_remove_list):
    import os
    src = cleaned / "train" / "code-go" / "part-00000.parquet"
    before = sha(src)
    out = tmp_path / "deduped"
    dst = out / "train" / "code-go" / "part-00000.parquet"
    dst.parent.mkdir(parents=True)
    os.link(src, dst.with_name(dst.name + ".tmp"))  # what a run killed right after os.link leaves (old name)
    os.link(src, dst.with_name(dst.name + ".4242.tmp"))  # and with the per-process name
    ad.apply(cleaned, write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]]), out)
    assert sha(src) == before and ids(src) == ["g0", "g1", "g2", "g3", "g4"]  # the input is untouched
    assert ids(dst) == ["g0", "g2", "g3", "g4"] and not list(out.rglob("*.tmp"))


def test_two_runs_into_one_folder_are_refused(tmp_path, cleaned, write_remove_list):
    import runlock
    out = tmp_path / "deduped"
    with runlock.exclusive(out):
        with pytest.raises(ad.Stop, match="another process is writing"):
            ad.apply(cleaned, write_remove_list([]), out)
    assert ad.apply(cleaned, write_remove_list([], name="again.csv"), out)["totals"]["rows"] == 13  # released


def test_a_newline_inside_a_quoted_doc_id(tmp_path, write_remove_list):
    root = tmp_path / "c"
    odd = "line one\nline two"
    write_part(root, "train", "p/part-00000.parquet", [{"doc_id": i, "text": "x", "pack_id": "p"} for i in ("a", odd, "c")])
    out = tmp_path / "deduped"
    s = ad.apply(root, write_remove_list([["p", "train", "p/part-00000.parquet", 1, odd]]), out, splits=("train",))
    assert ids(out / "train" / "p" / "part-00000.parquet") == ["a", "c"] and s["remove_list"]["rows"] == 1


def test_unicode_and_odd_doc_ids(tmp_path, write_remove_list):
    odd = ["\u09ac\u09be\u0982\u09b2\u09be-\u09e6\u09e7", "e\u0301", "with,comma", "NA", "", "  spaced  ",
           "\U0001F600", 'with "quotes"']
    root = tmp_path / "c"
    write_part(root, "train", "p/part-00000.parquet", [{"doc_id": d, "text": "x", "pack_id": "p"} for d in odd])
    out = tmp_path / "deduped"
    ad.apply(root, write_remove_list([["p", "train", "p/part-00000.parquet", i, d] for i, d in enumerate(odd) if i % 2]),
             out, splits=("train",))
    assert ids(out / "train" / "p" / "part-00000.parquet") == [d for i, d in enumerate(odd) if not i % 2]


def test_a_part_with_no_pack_id_on_a_row_stops(tmp_path, write_remove_list):
    root = tmp_path / "c"
    write_part(root, "train", "p/part-00000.parquet", [{"doc_id": "a", "text": "x", "pack_id": "p"},
                                                       {"doc_id": "b", "text": "x", "pack_id": None}])
    with pytest.raises(ad.Stop, match="have no pack_id"):
        ad.apply(root, write_remove_list([]), tmp_path / "deduped", splits=("train",))


def test_an_empty_part_and_a_part_with_every_row_removed(tmp_path, write_remove_list):
    root = tmp_path / "c"
    write_part(root, "train", "p/part-00000.parquet", [])
    write_part(root, "train", "p/part-00001.parquet", [{"doc_id": f"d{i}", "text": "x", "pack_id": "p"} for i in range(3)])
    out = tmp_path / "deduped"
    s = ad.apply(root, write_remove_list([["p", "train", "p/part-00001.parquet", i, f"d{i}"] for i in range(3)]), out,
                 splits=("train",))
    assert s["totals"] == {"rows": 3, "removed": 3, "kept": 0}
    assert ids(out / "train" / "p" / "part-00000.parquet") == [] and ids(out / "train" / "p" / "part-00001.parquet") == []
    with pytest.raises(ad.Stop, match="row 0 is listed, but the part has 0 rows"):
        ad.apply(root, write_remove_list([["p", "train", "p/part-00000.parquet", 0, "x"]], name="b.csv"),
                 tmp_path / "d2", splits=("train",))


def test_one_huge_row_group_is_read_in_batches(tmp_path, write_remove_list, monkeypatch):
    monkeypatch.setattr(ad, "BATCH_ROWS", 997)
    root = tmp_path / "c"
    n = 20000
    write_part(root, "train", "p/part-00000.parquet",
               [{"doc_id": f"d{i}", "text": "x" * 20, "pack_id": "p"} for i in range(n)], row_group_size=n)
    gone = list(range(0, n, 7))
    out = tmp_path / "deduped"
    ad.apply(root, write_remove_list([["p", "train", "p/part-00000.parquet", r, f"d{r}"] for r in gone]), out,
             splits=("train",))
    assert ids(out / "train" / "p" / "part-00000.parquet") == [f"d{i}" for i in range(n) if i % 7]


def test_many_packs(tmp_path, write_remove_list):
    root = tmp_path / "c"
    for k in range(120):
        write_part(root, "train", f"pack{k:03d}/part-00000.parquet",
                   [{"doc_id": f"{k}-{i}", "text": "x", "pack_id": f"pack{k:03d}"} for i in range(5)])
    s = ad.apply(root, write_remove_list([[f"pack{k:03d}", "train", f"pack{k:03d}/part-00000.parquet", 2, f"{k}-2"]
                                          for k in range(120)]), tmp_path / "deduped", splits=("train",))
    assert len(s["by_pack"]) == 120 and s["totals"] == {"rows": 600, "removed": 120, "kept": 480}


def test_one_worker_and_eight_give_the_same_output(tmp_path, cleaned, write_remove_list):
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"],
                            ["en-dclm", "train", "en-dclm/part-00000.parquet", 0, "e0"]])
    one = ad.apply(cleaned, rl, tmp_path / "one", workers=1)
    eight = ad.apply(cleaned, rl, tmp_path / "eight", workers=8)
    assert one["parts"] == eight["parts"] and one["by_pack"] == eight["by_pack"]
    for p in (tmp_path / "one").rglob("*.parquet"):
        assert sha(p) == sha(tmp_path / "eight" / p.relative_to(tmp_path / "one"))


def test_a_resumed_run_with_the_hash_cache_hashes_nothing(tmp_path, cleaned, write_remove_list):
    from hashing import HashCache
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]])
    out, cache_file = tmp_path / "deduped", tmp_path / "cache" / "sha256.json"
    first = HashCache(cache_file)
    ad.apply(cleaned, rl, out, cache=first)
    first.save()
    again = HashCache(cache_file)
    s = ad.apply(cleaned, rl, out, cache=again)
    assert all(p["skipped"] for p in s["parts"]) and again.misses == 0 and again.hits > 0


@pytest.mark.parametrize("bad", [0, -1, 1.5, "4", True])
def test_bad_workers(tmp_path, cleaned, write_remove_list, bad):
    with pytest.raises(ad.Stop, match="workers"):
        ad.apply(cleaned, write_remove_list([]), tmp_path / "deduped", workers=bad)


# --- the review of the scale pass (14 Nov) ---------------------------------------------------------------------------
def large_docs_part(root, n=60, size=210_000, group=8, page_rows=None):
    """A part of n documents of about `size` bytes (books, long code files), in row groups of `group` rows (and pages
    of `page_rows` rows: the reader decodes a page whole, so the input's pages set a floor no batch size can lower)."""
    return write_part(root, "train", "books/part-00000.parquet",
                      [{"doc_id": f"b{i}", "text": f"{i:07d}" * (size // 7), "pack_id": "books"} for i in range(n)],
                      row_group_size=group, compression="zstd", write_batch_size=page_rows)


def test_batches_and_row_groups_are_bounded_in_bytes(tmp_path, write_remove_list, monkeypatch):
    """8,192 rows of 200 KB documents would be 1.6 GB in one batch: batches and output row groups are sized in bytes."""
    seen, real = [], pq.ParquetFile.iter_batches

    def spy(self, *a, **k):
        for b in real(self, *a, **k):
            seen.append(b.nbytes)
            yield b
    monkeypatch.setattr(pq.ParquetFile, "iter_batches", spy)
    monkeypatch.setattr(ad, "BATCH_BYTES", 1 << 20)
    monkeypatch.setattr(ad, "ROW_GROUP_BYTES", 2 << 20)
    root = tmp_path / "c"
    large_docs_part(root)
    gone = [0, 9, 59]
    out = tmp_path / "deduped"
    ad.apply(root, write_remove_list([["books", "train", "books/part-00000.parquet", r, f"b{r}"] for r in gone]), out,
             splits=("train",))
    got = out / "train" / "books" / "part-00000.parquet"
    assert ids(got) == [f"b{i}" for i in range(60) if i not in gone]
    assert seen and max(seen) <= 1.25 * (1 << 20)  # about BATCH_BYTES, never the 60 rows (12 MB) at once
    md = pq.ParquetFile(got).metadata
    assert md.num_row_groups >= 5
    assert all(md.row_group(g).total_byte_size <= 1.25 * (2 << 20) for g in range(md.num_row_groups))


def test_peak_memory_stays_near_the_limits_with_large_documents(tmp_path, write_remove_list):
    """In a fresh process (pyarrow's peak is per process): 300 documents of 200 KB (60 MB of text) in 128-row groups of
    5-row pages, with 2 MiB batches and 4 MiB row groups. Reading 8,192 rows at a time held the whole part, and its
    filtered copy, at once (about 120 MB here)."""
    root = tmp_path / "c"
    large_docs_part(root, n=300, size=200_000, group=128, page_rows=5)
    rl = write_remove_list([["books", "train", "books/part-00000.parquet", 5, "b5"]])
    code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import apply_dedup as ad, pyarrow as pa\n"
            "ad.BATCH_BYTES, ad.ROW_GROUP_BYTES, ad.READ_BUFFER = 2 << 20, 4 << 20, 1 << 20\n"
            "s = ad.apply(sys.argv[2], sys.argv[3], sys.argv[4], splits=('train',), workers=1)\n"
            "print(json.dumps({'kept': s['totals']['kept'], 'peak': pa.default_memory_pool().max_memory()}))")
    r = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(PIPELINE), str(root), str(rl), str(tmp_path / "out")],
                       capture_output=True, text=True, check=True)
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert got["kept"] == 299 and got["peak"] < 24 << 20, got


def test_a_hard_linked_part_is_not_hashed_again(tmp_path, cleaned, write_remove_list, monkeypatch):
    """Making a hard link moves the file's change time (ctime on Linux, ChangeTime on Windows), which is in the cache
    key: apply records the input's sha256 for the link instead of reading the part again."""
    from pathlib import Path
    import hashing
    from hashing import HashCache
    read, real = [], hashing.file_sha256
    monkeypatch.setattr(hashing, "file_sha256", lambda p: read.append(Path(p).resolve()) or real(p))
    out, c = tmp_path / "deduped", HashCache()
    s = ad.apply(cleaned, write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]]), out, cache=c)
    linked = [out / p["split"] / p["part"] for p in s["parts"] if p["linked"]]
    assert len(linked) == 3 and not {f.resolve() for f in linked} & set(read)
    for p in s["parts"]:
        if p["linked"]:
            dst = out / p["split"] / p["part"]
            assert p["output_sha256"] == p["input_sha256"] == real(dst) == c.sha256(dst)


def test_other_code_redoes_the_parts(tmp_path, cleaned, write_remove_list, monkeypatch):
    """The resume key is the code's sha256 with the helper modules (hashing.code_sha256): other code skips nothing."""
    rl = write_remove_list([["code-go", "train", "code-go/part-00000.parquet", 1, "g1"]])
    out = tmp_path / "deduped"
    first = ad.apply(cleaned, rl, out)
    assert set(first["code_files"]) == {"apply_dedup.py", "arrowtools.py", "hashing.py", "runlock.py"}
    assert all(p["skipped"] for p in ad.apply(cleaned, rl, out)["parts"])
    monkeypatch.setattr(ad, "code_sha256", lambda script, cache=None: ("0" * 64, {}))
    assert not any(p["skipped"] for p in ad.apply(cleaned, rl, out)["parts"])


def test_a_part_name_with_glob_characters(tmp_path, write_remove_list):
    root = tmp_path / "c"
    write_part(root, "train", "p/part[1].parquet", [{"doc_id": f"d{i}", "text": "x", "pack_id": "p"} for i in range(3)])
    out = tmp_path / "deduped"
    stale = out / "train" / "p" / "part[1].parquet.99999.tmp"  # left by a killed run
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"left by a killed run")
    ad.apply(root, write_remove_list([["p", "train", "p/part[1].parquet", 1, "d1"]]), out, splits=("train",))
    assert not stale.exists() and ids(out / "train" / "p" / "part[1].parquet") == ["d0", "d2"]


# --- review of PR #46 (patilvijay23, 15 Nov) -------------------------------------------------------------------------
def test_the_same_long_text_repeated_is_read_in_small_batches(tmp_path, write_remove_list, monkeypatch):
    """600 rows of one 200 KB text in 128-row groups: dictionary-encoded, about 1.5 KB a row stored, 200 KB decoded.
    Reads are sized from the decoded bytes, and no output row group passes its limit."""
    import pyarrow as pa
    seen, real = [], pq.ParquetFile.iter_batches

    def spy(self, *a, **k):
        for b in real(self, *a, **k):
            seen.append(b.nbytes)
            yield b
    monkeypatch.setattr(pq.ParquetFile, "iter_batches", spy)
    monkeypatch.setattr(ad, "BATCH_BYTES", 2 << 20)
    monkeypatch.setattr(ad, "ROW_GROUP_BYTES", 4 << 20)
    root = tmp_path / "c"
    text = "abcdefgh" * 25_000
    path = root / "train" / "p" / "part-00000.parquet"
    path.parent.mkdir(parents=True)
    pq.write_table(pa.table({"doc_id": [f"d{i}" for i in range(600)], "text": [text] * 600, "pack_id": ["p"] * 600}), path,
                   row_group_size=128)
    md = pq.ParquetFile(path).metadata
    assert md.row_group(0).total_byte_size / md.row_group(0).num_rows < 5_000  # the footer says a few KB a row
    out = tmp_path / "deduped"
    ad.apply(root, write_remove_list([["p", "train", "p/part-00000.parquet", 7, "d7"]]), out, splits=("train",))
    got = out / "train" / "p" / "part-00000.parquet"
    assert ids(got) == [f"d{i}" for i in range(600) if i != 7]
    assert max(seen) <= 2 * (2 << 20)  # a batch is at most twice the target, never the whole part (114 MiB)
    t = pq.read_table(got)
    assert t.column("text").to_pylist() == [text] * 599


def test_peak_memory_with_the_same_long_text_repeated(tmp_path, write_remove_list):
    """The review's measurement, in a fresh process: 600 rows of one 200 KB text, one removal, one worker. The PR head
    peaked at 229 MiB of Arrow allocations, the branch before it at 50 MiB; the defaults now stay near that."""
    import pyarrow as pa
    root = tmp_path / "c"
    path = root / "train" / "p" / "part-00000.parquet"
    path.parent.mkdir(parents=True)
    pq.write_table(pa.table({"doc_id": [f"d{i}" for i in range(600)], "text": ["abcdefgh" * 25_000] * 600,
                             "pack_id": ["p"] * 600}), path, row_group_size=128)
    rl = write_remove_list([["p", "train", "p/part-00000.parquet", 7, "d7"]])
    code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import apply_dedup as ad, pyarrow as pa\n"
            "s = ad.apply(sys.argv[2], sys.argv[3], sys.argv[4], splits=('train',), workers=1)\n"
            "print(json.dumps({'kept': s['totals']['kept'], 'peak': pa.default_memory_pool().max_memory()}))")
    r = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(PIPELINE), str(root), str(rl), str(tmp_path / "out")],
                       capture_output=True, text=True, check=True)
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert got["kept"] == 599 and got["peak"] < 80 << 20, got


def test_a_batch_bigger_than_a_row_group_is_split(tmp_path, write_remove_list, monkeypatch):
    import pyarrow as pa
    monkeypatch.setattr(ad, "BATCH_BYTES", 64 << 20)  # reads far bigger than ...
    monkeypatch.setattr(ad, "ROW_GROUP_BYTES", 1 << 20)  # ... an output row group
    root = tmp_path / "c"
    write_part(root, "train", "p/part-00000.parquet",
               [{"doc_id": f"d{i}", "text": f"{i:05d}" * 20_000, "pack_id": "p"} for i in range(40)], row_group_size=40)
    out = tmp_path / "deduped"
    ad.apply(root, write_remove_list([["p", "train", "p/part-00000.parquet", 3, "d3"]]), out, splits=("train",))
    got = out / "train" / "p" / "part-00000.parquet"
    md = pq.ParquetFile(got).metadata
    assert ids(got) == [f"d{i}" for i in range(40) if i != 3] and md.num_row_groups >= 3
    assert all(md.row_group(g).total_byte_size <= 1.25 * (1 << 20) for g in range(md.num_row_groups))
