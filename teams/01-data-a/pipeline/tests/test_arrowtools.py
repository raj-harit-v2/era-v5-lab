"""Tests for arrowtools.py: the shared pyarrow helpers by_part (cut a table by part) and batch_rows (rows per read
batch, from the footer).

  python -m pytest teams/01-data-a/pipeline/tests -q
"""
import random

import pyarrow as pa
import pyarrow.parquet as pq

import conftest  # noqa: F401  (the pipeline folder on sys.path)
import arrowtools as at


def test_by_part_cuts_at_every_key_change_in_sorted_order():
    rng = random.Random(1)
    rows = [(rng.choice(["train", "heldout"]), f"p{rng.randrange(300):03d}", i) for i in range(5000)]
    t = pa.table({"split": [r[0] for r in rows], "part": [r[1] for r in rows], "i": [r[2] for r in rows]})
    want = {}
    for split, part, i in rows:
        want.setdefault((split, part), []).append(i)
    got = at.by_part(t)
    assert list(got) == sorted(want) and {k: v["i"].to_pylist() for k, v in got.items()} == want


def test_by_part_keeps_rows_with_a_null_key_together():
    t = pa.table({"split": ["train"] * 5, "part": [None, "a", None, None, "b"], "v": [0, 1, 2, 3, 4]})
    got = {k: v["v"].to_pylist() for k, v in at.by_part(t).items()}
    assert got == {("train", "a"): [1], ("train", "b"): [4], ("train", None): [0, 2, 3]}


def test_batch_rows_is_sized_by_the_widest_row_group(tmp_path):
    f = tmp_path / "p.parquet"
    with pq.ParquetWriter(f, pa.schema([("id", pa.string()), ("text", pa.string())])) as w:
        w.write_table(pa.table({"id": [f"a{i}" for i in range(100)], "text": [f"{i:03d}" * 30 for i in range(100)]}))
        w.write_table(pa.table({"id": [f"b{i}" for i in range(10)], "text": [f"{i}" * 20_000 for i in range(10)]}))
    with at.opened(f) as pf:
        md = pf.metadata
        widest = max(md.row_group(i).total_byte_size / md.row_group(i).num_rows for i in range(md.num_row_groups))
        assert widest > 10_000  # the second group's 20 KB rows, not the average
        assert at.batch_rows(pf, 1 << 20, 8192) == int((1 << 20) // widest)
        assert at.batch_rows(pf, 1 << 40, 8192) == 8192 and at.batch_rows(pf, 1, 8192) == 1
        assert at.batch_rows(pf, 1 << 20, 8192, ["id"]) == 8192  # the ids alone are small
    e = tmp_path / "empty.parquet"
    pq.write_table(pa.table({"id": pa.array([], pa.string())}), e)
    with at.opened(e) as pf:
        assert at.batch_rows(pf, 1 << 20, 8192) == 8192


# --- review of PR #46 (patilvijay23, 15 Nov) -------------------------------------------------------------------------
def rows_of(batches):
    return [r for b in batches for r in b.column(0).to_pylist()]


def test_iter_sized_gives_every_row_once_in_order(tmp_path):
    """Small rows, then the same long text repeated (dictionary-encoded: tiny in the footer), then distinct long rows."""
    f = tmp_path / "p.parquet"
    small = [f"s{i}" for i in range(300)]
    same = ["x" * 50_000] * 200
    long_ = [f"{i:05d}" * 10_000 for i in range(50)]
    ids = list(range(550))
    with pq.ParquetWriter(f, pa.schema([("text", pa.string()), ("id", pa.int64())])) as w:
        for chunk, start in ((small, 0), (same, 300), (long_, 500)):
            w.write_table(pa.table({"text": chunk, "id": ids[start:start + len(chunk)]}), row_group_size=64)
    target = 256 << 10
    with at.opened(f) as pf:
        batches = list(at.iter_sized(pf, target, 1024))
    assert [i for b in batches for i in b.column(1).to_pylist()] == ids
    assert rows_of(batches) == small + same + long_
    over = [b.nbytes for b in batches if b.nbytes > 2 * target + 50_000]
    assert len(over) <= 1  # one read at the old size when the rows jump to 50 KB, then reads shrink
    with at.opened(f) as pf:
        assert [i for b in at.iter_sized(pf, target, 1024, ["id"]) for i in b.column(0).to_pylist()] == ids


def test_iter_sized_on_an_empty_file_and_a_single_row_group(tmp_path):
    e = tmp_path / "e.parquet"
    pq.write_table(pa.table({"text": pa.array([], pa.string())}), e)
    with at.opened(e) as pf:
        assert list(at.iter_sized(pf, 1 << 20, 1024)) == []
    one = tmp_path / "one.parquet"
    pq.write_table(pa.table({"text": [f"t{i}" for i in range(5000)]}), one, row_group_size=5000)
    with at.opened(one) as pf:
        batches = list(at.iter_sized(pf, 1 << 20, 1024))
    assert rows_of(batches) == [f"t{i}" for i in range(5000)] and max(b.num_rows for b in batches) <= 1024
    # 5000 rows of short text: more than 1 MiB by the footer's bound, so the first read is small (decoded sizes are
    # not known before it): as many rows as the bound allows, at least 16
    assert 16 <= batches[0].num_rows < 1024 and batches[0].nbytes <= 1 << 20


# --- review of PR #46 (patilvijay23, 17 Nov) -------------------------------------------------------------------------
def mixed_sizes(path):
    """The case from the review of PR #46: one 128-row group of short text, then 600 copies of one ~200 KB text in the next row group
    (dictionary-encoded: about 1.5 KB a row in the footer)."""
    big = "abcdefgh" * 25_000
    with pq.ParquetWriter(path, pa.schema([("doc_id", pa.string()), ("text", pa.string())])) as w:
        w.write_table(pa.table({"doc_id": [f"s{i}" for i in range(128)], "text": [f"short {i}" for i in range(128)]}),
                      row_group_size=128)
        w.write_table(pa.table({"doc_id": [f"b{i}" for i in range(600)], "text": [big] * 600}), row_group_size=600)
    return big


def test_iter_sized_probes_every_row_group_so_a_jump_in_size_stays_small(tmp_path):
    f = tmp_path / "mixed.parquet"
    big = mixed_sizes(f)
    target = 16 << 20
    with at.opened(f) as pf:
        assert pf.metadata.num_row_groups == 2
        batches = list(at.iter_sized(pf, target, 1024))
    assert [i for b in batches for i in b.column(0).to_pylist()] == [f"s{i}" for i in range(128)] + [f"b{i}" for i in range(600)]
    # was one 114 MiB batch. The 200 KB row group is read in as many rows as its footer proves fit (about 80), so no
    # batch passes the target at all
    assert max(b.nbytes for b in batches) <= target
    first_big = next(b for b in batches if b.column(0)[0].as_py().startswith("b"))
    assert first_big.column(0)[0].as_py() == "b0" and first_big.nbytes <= target  # the row group starts on its own


def test_iter_sized_keeps_large_batches_for_uniform_short_rows(tmp_path):
    """Row groups the footer cannot prove small cost one small first read each; the rest is read at full size."""
    f = tmp_path / "short.parquet"
    pq.write_table(pa.table({"text": [f"t{i}" for i in range(20_000)]}), f, row_group_size=5000)
    with at.opened(f) as pf:
        sizes = [b.num_rows for b in at.iter_sized(pf, 1 << 20, 1024)]
    assert sum(sizes) == 20_000 and max(sizes) == 1024 and len(sizes) <= 4 * 6  # a first read, then 1024s, a part


def test_iter_sized_reads_row_groups_the_footer_proves_small_together(tmp_path):
    """The cleaner's 128-row groups of short text: the footer proves each whole row group fits, so one reader takes
    them all in full-size batches across row groups (a reader per row group costs time on thousands of them)."""
    f = tmp_path / "small_groups.parquet"
    pq.write_table(pa.table({"text": [f"t{i}" for i in range(128 * 40)]}), f, row_group_size=128)
    with at.opened(f) as pf:
        batches = list(at.iter_sized(pf, 16 << 20, 1024))  # apply's and the ledger's 16 MiB
    assert rows_of(batches) == [f"t{i}" for i in range(128 * 40)] and [b.num_rows for b in batches] == [1024] * 5


def test_iter_sized_bound_ignores_nested_columns(tmp_path):
    """A list column can repeat a value without storing it again, so the footer proves nothing: first reads stay small."""
    f = tmp_path / "nested.parquet"
    pq.write_table(pa.table({"tags": [["x" * 1000] * 50 for _ in range(512)]}), f, row_group_size=128)
    with at.opened(f) as pf:
        assert at._safe_rows(pf.metadata, 0, None, 1 << 20) == 0
        batches = list(at.iter_sized(pf, 1 << 20, 1024))
    assert sum(b.num_rows for b in batches) == 512 and max(b.nbytes for b in batches) <= (1 << 20) + 50 * 1000 * 16


def test_apply_reads_mixed_sizes_in_small_batches_and_memory_stays_bounded(tmp_path, monkeypatch):
    """apply_dedup's filter on that file: no batch near the 114 MiB he measured, and the Arrow memory the process
    holds while filtering (sampled at every batch) stays far below his 230 MiB."""
    import apply_dedup
    seen, held = [], []
    real = at.iter_sized
    base = pa.total_allocated_bytes()

    def spy(*a, **k):
        for b in real(*a, **k):
            seen.append(b.nbytes)
            held.append(pa.total_allocated_bytes() - base)
            yield b
    monkeypatch.setattr(at, "iter_sized", spy)
    src, out = tmp_path / "in.parquet", tmp_path / "out.parquet"
    big = mixed_sizes(src)
    kept = apply_dedup.filter_part(src, out, pa.array([3, 200], pa.int64()))
    assert kept == 726 and pq.read_metadata(out).num_rows == 726
    assert max(seen) <= apply_dedup.BATCH_BYTES + 2 * len(big)
    assert max(held) <= apply_dedup.BATCH_BYTES + apply_dedup.ROW_GROUP_BYTES + (16 << 20), max(held) >> 20
