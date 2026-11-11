"""Decoding every id in batches of 1, 7 and 4096 gives identical ids, equal to the float64 reference."""

import json
from pathlib import Path

import numpy as np
import torch

import decode_batches as db
import decode_gpu as dg
import decode_ref as dr
from ke2.codec import encode_f64
from ke2.config import RESULTS_DIR
from ke2.tables import ByteTable

GPU_ID_HASH = "31c8d0e0ac50cff5c8021f88a2b608de2298fdbf216c620a40e83d2adbe26f9a"  # determinism_gpu.md, every GPU run

P = 16


def synthetic_table(n=500, seed=0):
    rng = np.random.default_rng(seed)
    rows = set()
    while len(rows) < n:
        rows.add(bytes(rng.integers(0, 256, int(rng.integers(1, P + 1)), dtype=np.uint8)))
    rows = sorted(rows)
    buf = np.zeros((n, P), dtype=np.uint8)
    lens = np.zeros(n, dtype=np.int16)
    for i, r in enumerate(rows):
        buf[i, : len(r)] = np.frombuffer(r, dtype=np.uint8)
        lens[i] = len(r)
    return ByteTable("raw", P, buf, lens, 0, 0, 0, "synthetic")


def test_batch_sizes_agree_and_match_reference():
    table = synthetic_table()
    ct = dr.CodeTable.from_byte_table(table)
    ref = dr.decode(encode_f64(table.bytes, table.lengths.astype(np.int64), P), ct).token_ids
    runs = {b: db.decode_all(table, ct, "cpu", b) for b in (1, 7, 4096)}
    for b, ids in runs.items():
        assert ids.shape == (table.vocab_size,) and ids.dtype == np.int64
        assert np.array_equal(ids, ref), b
    assert len({db.ids_sha256(ids, P, "cpu", b) for b, ids in runs.items()}) == 3  # header includes batch size
    assert len({db.ids_sha256(ids, P, "cpu", 0) for ids in runs.values()}) == 1  # same ids -> same body hash


def test_gpu_format_digest_matches_decode_gpu():
    ids = np.arange(120)
    sha = "ab" * 32
    assert db.ids_sha256_gpu_format(ids, P, sha) == dg.id_digest(P, sha, np.arange(120), ids)
    ids2 = ids.copy()
    ids2[5] = 6
    assert db.ids_sha256_gpu_format(ids2, P, sha) != db.ids_sha256_gpu_format(ids, P, sha)


def test_tf32_is_disabled_by_configure_device():
    db.configure_device("cpu")
    assert torch.backends.cuda.matmul.allow_tf32 is False
    assert torch.backends.cudnn.allow_tf32 is False
    assert torch.get_float32_matmul_precision() == "highest"


def test_reference_cache_write_then_hit_and_stale_fallthrough(tmp_path):
    table = synthetic_table(n=120, seed=1)
    ct = dr.CodeTable.from_byte_table(table)
    cache = tmp_path / "ref.npz"
    ids1, info1 = db.reference_ids(table, ct, cache, chunk=50)
    assert info1["cached"] is False and cache.is_file()
    assert np.array_equal(ids1, np.arange(table.vocab_size))
    ids2, info2 = db.reference_ids(table, ct, cache, chunk=50)
    assert info2["cached"] is True and np.array_equal(ids2, ids1) and info2["sha256"] == info1["sha256"]
    np.savez_compressed(cache, ids=ids1[::-1].copy(), sha256=np.array("x"))  # no table_sha256 key
    ids3, info3 = db.reference_ids(table, ct, cache, chunk=50)
    assert info3["cached"] is False and np.array_equal(ids3, ids1)
    np.savez_compressed(cache, ids=ids1[::-1].copy(), sha256=np.array("x"), table_sha256=np.array("other"))
    ids4, info4 = db.reference_ids(table, ct, cache, chunk=50)
    assert info4["cached"] is False and np.array_equal(ids4, ids1)


def test_environment_reads_flags_back():
    db.configure_device("cpu")
    env = db.environment("cpu")
    assert env["tf32_matmul"] is False and env["tf32_cudnn"] is False
    assert env["float32_matmul_precision"] == "highest"


def test_default_out_never_targets_decode_gpu():
    table = Path("results/tables/raw_table_P32.npz")
    assert db.default_out("cpu", table) == RESULTS_DIR / "decode_cpu" / "raw_P32.json"
    for dev in ("cuda", "cuda:0", "mps"):
        out = db.default_out(dev, table)
        assert out.parent.name != "decode_gpu" and out.parent.name.startswith(f"decode_{dev.split(':')[0]}")
        assert out.name == "raw_P32.json"


def test_end_to_end_cpu_run_on_a_synthetic_table(tmp_path):
    table = synthetic_table(n=200, seed=2)
    table_path = tmp_path / "raw_table_P16.npz"
    table.save(table_path)
    out = tmp_path / "out" / "raw_P16.json"
    rc = db.main(
        [
            "--device",
            "cpu",
            "--batch-sizes",
            "1",
            "7",
            "--repeats",
            "2",
            "--table",
            str(table_path),
            "--tokenizer-sha256",
            "synthetic",
            "--out",
            str(out),
            "--reference-cache",
            str(tmp_path / "ref.npz"),
        ]
    )
    assert rc == 0 and out.is_file() and out.with_suffix(".md").is_file()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert set(report["batch_sizes"]) == {"1", "7"} and all(len(v["runs"]) == 2 for v in report["batch_sizes"].values())
    assert report["all_runs_equal_reference"] and report["same_ids_across_batch_sizes"]
    ct = dr.CodeTable.from_byte_table(table)
    assert report["ids_sha256_gpu_format"] == [
        db.ids_sha256_gpu_format(np.arange(table.vocab_size), P, ct.table_sha256)
    ]
    assert report["reference"]["ids_sha256_gpu_format"] == report["ids_sha256_gpu_format"][0]
    assert report["reference"]["sha256"] == report["batch_sizes"]["1"]["runs"][0]["ids_body_sha256"]
    assert "ke2-decode-gpu-ids-v1" in out.with_suffix(".md").read_text(encoding="utf-8")


def test_committed_cpu_run_matches_the_gpu_report():
    report = json.loads((RESULTS_DIR / "decode_cpu" / "raw_P32.json").read_text(encoding="utf-8"))
    assert report["device"] == "cpu" and report["P"] == 32 and report["vocab_size"] == 131072
    assert set(report["batch_sizes"]) == {"1", "7", "4096"}
    assert all(
        v["hashes_match"] and v["all_equal_reference"] and len(v["runs"]) == 3 for v in report["batch_sizes"].values()
    )
    assert report["all_runs_equal_reference"] and report["same_ids_across_batch_sizes"]
    assert report["ids_sha256_gpu_format"] == [GPU_ID_HASH]
    assert report["environment"]["tf32_matmul"] is False and report["environment"]["dtype"] == "float32"
    gpu_lines = (RESULTS_DIR / "decode_gpu" / "raw_P32_sha256.txt").read_text(encoding="utf-8").splitlines()
    gpu_hashes = {line.split()[3] for line in gpu_lines if line and not line.startswith("#")}
    assert gpu_hashes == {GPU_ID_HASH}
    gpu_report = json.loads((RESULTS_DIR / "decode_gpu" / "raw_P32.json").read_text(encoding="utf-8"))
    assert report["table_sha256"] == gpu_report["inputs"]["table_sha256"]
