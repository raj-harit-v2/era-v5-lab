"""GPU decode determinism: portable checks of the hashes, the decoder logic and the pass rule, plus opt-in CUDA."""

import hashlib
import importlib.util
import json
import os
import struct
from pathlib import Path

import numpy as np
import pytest

from decode_ref import CodeTable, decode
from ke2.config import TOKENIZER_SHA256
from ke2.tables import ByteTable

TEAM = Path(__file__).resolve().parents[1]
SCRIPT = TEAM / "src/determinism/decode_gpu.py"
spec = importlib.util.spec_from_file_location("decode_gpu", SCRIPT)
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)


def test_id_hash_frames_query_and_decoded_ids():
    expected = hashlib.sha256(b"ke2-decode-gpu-ids-v1|P=32|table=t|n=2\n" + struct.pack(">IIII", 0, 0, 1, 5))
    assert dg.id_digest(32, "t", np.array([0, 1]), np.array([0, 5])) == expected.hexdigest()
    base = dg.id_digest(32, "t", np.array([0, 1]), np.array([0, 1]))
    assert base != dg.id_digest(64, "t", np.array([0, 1]), np.array([0, 1]))
    assert base != dg.id_digest(32, "u", np.array([0, 1]), np.array([0, 1]))
    assert base != dg.id_digest(32, "t", np.array([0, 1]), np.array([1, 0]))
    with pytest.raises(ValueError, match="uint32"):
        dg.id_digest(32, "t", np.array([0]), np.array([-1]))


def test_score_hash_names_the_dtype_and_ignores_byte_order():
    s, m = np.array([1.0, 0.5], dtype=np.float32), np.array([0.25, 0.125], dtype=np.float32)
    h = dg.score_digest(32, "t", s, m)
    assert h == dg.score_digest(32, "t", s.astype(">f4"), m.astype(">f4"))
    assert h != dg.score_digest(32, "t", s.astype(np.float64), m.astype(np.float64))
    assert h != dg.score_digest(32, "t", s, m + np.float32(1e-7))


def _sub_table(n):
    t = ByteTable.load(TEAM / "results/tables/raw_table_P32.npz", tokenizer_sha256=TOKENIZER_SHA256)
    return ByteTable("raw", 32, t.bytes[:n].copy(), t.lengths[:n].copy(), 0, 0, 0, t.tokenizer_sha256)


def test_gpu_decoder_logic_matches_decode_ref_on_cpu():
    """The GPU code path, run on CPU torch, gives decode_ref's IDs, scores and margins for 512 real tokens.

    Scores are float32 dot products over D = 8192 dense coordinates, so they differ from the float64 reference
    by up to about 2e-4 (determinism_gpu.md); IDs must be identical.
    """
    torch = pytest.importorskip("torch")
    from kronecker_embeddings.codec import kronecker_codec

    table = _sub_table(512)
    byte_rows = torch.from_numpy(table.bytes)
    lengths = torch.from_numpy(table.lengths.astype(np.int64))
    queries = kronecker_codec(byte_rows, lengths, pos_dim=32)
    ref = decode(queries.numpy(), CodeTable.from_byte_table(table))
    codes = dg.candidate_codes(kronecker_codec, byte_rows, lengths, 32, chunk=100)  # uneven chunks on purpose
    ids, best, margin, runner_up, tied, bad = dg.decode_batch(queries.clone(), codes)
    assert ids.tolist() == ref.token_ids.tolist() == list(range(512))
    assert not bool(bad) and int(tied.max()) == 0
    assert np.allclose(best.numpy(), ref.scores, rtol=0, atol=5e-4)
    assert np.allclose(margin.numpy(), ref.margins, rtol=0, atol=5e-4)
    assert (runner_up != ids).all()


def test_ties_go_to_the_lowest_id_with_zero_margin_and_zero_queries_are_flagged():
    torch = pytest.importorskip("torch")
    codes = dg.unit_rows(torch.tensor([[1.0, 0.0], [0.0, 2.0], [0.0, 3.0], [0.0, 0.0]]))
    assert codes[3].tolist() == [0.0, 0.0]  # a zero code stays zero and scores 0, as in decode_ref
    ids, _best, margin, runner_up, tied, bad = dg.decode_batch(torch.tensor([[0.0, 5.0], [1.0, 0.0]]), codes)
    assert ids.tolist() == [1, 0] and runner_up[0].item() == 2
    assert margin[0].item() == 0.0 and tied.tolist() == [1, 0]
    assert not bool(bad)
    assert bool(dg.decode_batch(torch.tensor([[0.0, 0.0]]), codes)[5])
    assert bool(dg.decode_batch(torch.tensor([[float("nan"), 1.0]]), codes)[5])


def _run(size, id_hash="cpu", score="s", ids_equal=True):
    return {
        "batch_size": size,
        "id_sha256": id_hash,
        "score_sha256": f"{score}{size}",
        "ties": 0,
        "decode_seconds": 1.0,
        "comparison": {
            "ids_equal_cpu": ids_equal,
            "max_abs_score_difference": 1e-6,
            "max_abs_margin_difference": 1e-6,
        },
    }


def test_pass_needs_three_matching_id_hashes_equal_to_cpu_for_every_batch_size():
    cpu = {"id_sha256": "cpu"}
    runs = [_run(size) for size in (1, 7) for _ in range(3)]
    summary = dg.summarize(cpu, runs)
    assert dg.passed(summary) and summary["1"]["three_score_hashes_match"]
    assert summary["all_batch_sizes"] == {
        "id_hashes_match": True,
        "score_hashes_match": False,
        "distinct_score_hashes": 2,
    }
    assert not dg.passed(dg.summarize(cpu, [*runs[:5], _run(7, id_hash="other")]))
    assert not dg.passed(dg.summarize(cpu, [*runs[:5], _run(7, ids_equal=False)]))
    assert not dg.passed(dg.summarize({"id_sha256": "different"}, runs))
    with pytest.raises(ValueError, match="expected 3 runs"):
        dg.summarize(cpu, runs[:5])


def test_compare_with_cpu_lists_mismatching_queries():
    cpu = {"ids": np.array([0, 1, 2]), "best": np.array([1.0, 1.0, 1.0]), "margin": np.array([0.5, 0.5, 0.5])}
    gpu = {
        "ids": np.array([0, 2, 2]),
        "best": np.array([1.0, 0.75, 1.0], dtype=np.float32),
        "margin": np.array([0.5, 0.5, 0.25], dtype=np.float32),
    }
    out = dg.compare_with_cpu(gpu, cpu)
    assert not out["ids_equal_cpu"] and out["mismatching_ids"] == 1
    assert out["first_mismatches"] == [{"query": 1, "gpu": 2, "cpu": 1}]
    assert out["max_abs_score_difference"] == 0.25 and out["max_abs_margin_difference"] == 0.25


@pytest.mark.parametrize("stem", ["raw_P32"])
def test_committed_gpu_results_are_complete_and_consistent(stem):
    path = TEAM / "results/decode_gpu" / f"{stem}.json"
    if not path.is_file():
        pytest.skip(f"{path.name} not generated yet")
    report = json.loads(path.read_text(encoding="utf-8"))
    manifest = json.loads((TEAM / "results/tables/manifest.json").read_text(encoding="utf-8"))
    assert report["passed"] and report["inputs"]["full_vocabulary"]
    assert report["inputs"]["table_sha256"] == manifest["tables"][f"{stem.replace('_P', '_table_P')}.npz"]["sha256"]
    cpu = report["cpu_reference"]
    n = cpu["rows"]
    assert n == report["inputs"]["vocabulary_size"] == 131072
    # the shared ID hash is the hash of the identity map: every token ID decodes to itself
    identity = dg.id_digest(report["inputs"]["pos_dim"], report["inputs"]["table_sha256"], np.arange(n), np.arange(n))
    assert cpu["id_sha256"] == identity
    assert {r["batch_size"] for r in report["runs"]} == {1, 7, 4096} and len(report["runs"]) == 9
    assert all(r["id_sha256"] == cpu["id_sha256"] and r["comparison"]["ids_equal_cpu"] for r in report["runs"])
    assert all(
        r["environment"]["tf32_matmul"] is False and r["environment"]["dtype"] == "float32" for r in report["runs"]
    )
    lines = (path.parent / f"{stem}_sha256.txt").read_text(encoding="ascii").splitlines()[1:]
    assert lines[0] == f"cpu - 1 {cpu['id_sha256']} {cpu['score_sha256']}"
    assert lines[1:] == [
        f"gpu {r['batch_size']} {r['run']} {r['id_sha256']} {r['score_sha256']}" for r in report["runs"]
    ]


def test_cuda_integration_opt_in(tmp_path):
    if os.environ.get("KE2_RUN_GPU_TESTS") != "1":
        pytest.skip("optional GPU check: set KE2_RUN_GPU_TESTS=1 on a machine with CUDA")
    args = ["--limit", "64", "--batch-sizes", "1", "7", "--cpu-workers", "2", "--out", str(tmp_path)]
    assert dg.main(args) == 0
    report = json.loads((tmp_path / "raw_P32.json").read_text(encoding="utf-8"))
    assert report["passed"] and report["inputs"]["queries"] == 64 and not report["inputs"]["full_vocabulary"]
    assert all(r["environment"]["deterministic_algorithms"] for r in report["runs"])
