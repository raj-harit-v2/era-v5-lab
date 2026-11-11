#!/usr/bin/env python3
"""Decode every token ID on a CUDA GPU, three times per batch size, and compare with the CPU reference.

Each GPU process forward-encodes the token IDs with the upstream float32 ``kronecker_codec`` on the GPU and
decodes the codes there: float32 cosine against the codes of all V tokens as one matrix product per batch,
TF32 off, deterministic algorithms on, ties to the lowest token ID (the ``decode_ref.py`` rule). The default
batch sizes are 1, 7 and 4,096, each in three fresh processes. One more fresh process gives the CPU reference:
the same codec on CPU and ``decode_ref.py`` (float64, structured cosine) for every token ID.

Two hashes per run:

* ID hash: query ID and decoded ID for every query. Every GPU run must give the CPU reference's ID hash.
* Score hash: best cosine and margin as float32. It shows whether the float outputs repeat bit for bit.

Results: ``results/decode_gpu/<kind>_P<P>.json`` and ``<kind>_P<P>_sha256.txt``. See ``../../determinism_gpu.md``.

Usage (from the lab repository root; the tokenizer is not needed):

    python teams/04-ke2/src/determinism/decode_gpu.py --pos-dim 32
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

if __package__ in (None, ""):  # run as a script: make the ke2 package and decode_ref importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import decode_ref
from ke2.config import CHAR_DIM, RESULTS_DIR, TABLES_DIR, TOKENIZER_SHA256, UPSTREAM_CODEC_COMMIT
from ke2.tables import ByteTable, table_path
from ke2.upstream import ensure_kronecker_embeddings

ID_HASH_FORMAT = "ke2-decode-gpu-ids-v1"
SCORE_HASH_FORMAT = "ke2-decode-gpu-scores-v1"
BATCH_SIZES = (1, 7, 4096)
RUNS = 3
CANDIDATE_CHUNK = 8192
"""GPU candidate codes are encoded in fixed chunks of this many tokens, whatever the query batch size."""
CPU_CHUNK = 1024
"""Token IDs per CPU encode-and-decode task; decode_ref results do not depend on the chunking."""
CUBLAS_WORKSPACE_CONFIG = ":4096:8"
OUT_DIR = RESULTS_DIR / "decode_gpu"


def id_digest(pos_dim: int, table_sha256: str, query_ids: np.ndarray, decoded_ids: np.ndarray) -> str:
    """Header line, then each (query ID, decoded ID) pair as two big-endian uint32."""
    pairs = np.stack([np.asarray(query_ids), np.asarray(decoded_ids)], axis=1)
    if pairs.size and (pairs.min() < 0 or pairs.max() >= 2**32):
        raise ValueError("token IDs must fit in uint32")
    h = hashlib.sha256(f"{ID_HASH_FORMAT}|P={pos_dim}|table={table_sha256}|n={pairs.shape[0]}\n".encode())
    h.update(pairs.astype(">u4").tobytes())
    return h.hexdigest()


def score_digest(pos_dim: int, table_sha256: str, scores: np.ndarray, margins: np.ndarray) -> str:
    """Header line naming the dtype, then each (best cosine, margin) pair, little-endian, in query order."""
    values = np.stack([np.asarray(scores), np.asarray(margins)], axis=1)
    values = values.astype(values.dtype.newbyteorder("<"))
    h = hashlib.sha256(
        f"{SCORE_HASH_FORMAT}|P={pos_dim}|table={table_sha256}|n={values.shape[0]}|dtype={values.dtype.str}\n".encode()
    )
    h.update(values.tobytes())
    return h.hexdigest()


def load_table(tables: Path, kind: str, pos_dim: int, tokenizer_sha256: str) -> ByteTable:
    table = ByteTable.load(table_path(tables, kind, pos_dim), tokenizer_sha256=tokenizer_sha256)
    if table.kind != kind or table.pos_dim != pos_dim:
        raise ValueError(f"expected a {kind} table with P={pos_dim}")
    return table


def codec_source_sha256() -> str:
    ensure_kronecker_embeddings()
    from kronecker_embeddings import codec

    return hashlib.sha256(Path(codec.__file__).read_bytes()).hexdigest()


# GPU decoder ---------------------------------------------------------------------------------------------------


def configure_cuda(torch) -> None:
    """Full float32 matmuls (TF32 off) and deterministic algorithms; call before any CUDA work."""
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.set_float32_matmul_precision("highest")
    torch.use_deterministic_algorithms(True)


def unit_rows(x):
    """Divide each row of a float tensor by its Euclidean norm, in place. All-zero rows stay zero."""
    import torch

    norms = torch.linalg.vector_norm(x, dim=1, keepdim=True)
    return x.div_(torch.where(norms > 0, norms, torch.ones_like(norms)))


def candidate_codes(codec, byte_rows, lengths, pos_dim: int, *, chunk: int = CANDIDATE_CHUNK):
    """Unit-norm float32 codes of every token, shape ``(V, 256 * P)``, on the device of ``byte_rows``."""
    import torch

    out = torch.empty((byte_rows.shape[0], CHAR_DIM * pos_dim), device=byte_rows.device, dtype=torch.float32)
    for start in range(0, byte_rows.shape[0], chunk):
        end = start + chunk
        out[start:end] = codec(byte_rows[start:end], lengths[start:end], char_dim=CHAR_DIM, pos_dim=pos_dim)
    return unit_rows(out)


def decode_batch(queries, codes):
    """Decode float32 queries ``(b, D)`` against unit-norm candidate codes ``(V, D)``.

    The cosine is one matrix product of unit rows. Returns, on the queries' device: token IDs (first maximum,
    so ties go to the lowest ID), best cosine, margin (best minus second best), runner-up IDs, the number of
    other candidates tied with the best, and a flag for zero or nonfinite queries.
    """
    import torch

    bad = ~torch.isfinite(queries).all(dim=1) | ~queries.any(dim=1)
    scores = unit_rows(queries) @ codes.T
    best, ids = scores.max(dim=1)
    tied = (scores == best[:, None]).sum(dim=1) - 1
    scores[torch.arange(scores.shape[0], device=scores.device), ids] = float("-inf")
    second, runner_up = scores.max(dim=1)
    return ids, best, best - second, runner_up, tied, bad.any()


def nvidia_driver() -> str | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip().splitlines()[0]


def gpu_environment(torch) -> dict:
    props = torch.cuda.get_device_properties(0)
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "gpu": props.name,
        "compute_capability": f"{props.major}.{props.minor}",
        "gpu_memory_gib": round(props.total_memory / 1024**3, 1),
        "driver": nvidia_driver(),
        "system": platform.system(),
        "machine": platform.machine(),
        "dtype": "float32",
        "tf32_matmul": torch.backends.cuda.matmul.allow_tf32,
        "tf32_cudnn": torch.backends.cudnn.allow_tf32,
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
    }


def gpu_worker(args) -> dict:
    import torch

    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != CUBLAS_WORKSPACE_CONFIG:
        raise RuntimeError("run through the parent process: it sets CUBLAS_WORKSPACE_CONFIG for deterministic cuBLAS")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; this check needs an NVIDIA GPU and a CUDA build of PyTorch")
    ensure_kronecker_embeddings()
    from kronecker_embeddings.codec import kronecker_codec

    configure_cuda(torch)
    table = load_table(args.tables, args.kind, args.pos_dim, args.tokenizer_sha256)
    P, n, B = table.pos_dim, query_count(table, args.limit), args.batch_size
    device = torch.device("cuda")
    with torch.inference_mode():
        byte_rows = torch.from_numpy(table.bytes).to(device)
        lengths = torch.from_numpy(table.lengths.astype(np.int64)).to(device)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        codes = candidate_codes(kronecker_codec, byte_rows, lengths, P)
        torch.cuda.synchronize()
        t1 = time.perf_counter()
        ids = torch.empty(n, dtype=torch.long, device=device)
        runner_up = torch.empty_like(ids)
        tied = torch.empty_like(ids)
        best = torch.empty(n, dtype=torch.float32, device=device)
        margin = torch.empty_like(best)
        bad = torch.zeros((), dtype=torch.bool, device=device)
        for start in range(0, n, B):
            end = min(start + B, n)
            queries = kronecker_codec(byte_rows[start:end], lengths[start:end], char_dim=CHAR_DIM, pos_dim=P)
            out = decode_batch(queries, codes)
            ids[start:end], best[start:end], margin[start:end], runner_up[start:end], tied[start:end] = out[:5]
            bad |= out[5]
        torch.cuda.synchronize()
        t2 = time.perf_counter()
        if bool(bad):
            raise decode_ref.DecodeInputError("a query code is zero or nonfinite")
        arrays = {
            "ids": ids.cpu().numpy(),
            "best": best.cpu().numpy(),
            "margin": margin.cpu().numpy(),
            "runner_up": runner_up.cpu().numpy(),
            "tied": tied.cpu().numpy(),
        }
    np.savez(args.arrays, **arrays)
    table_sha = table.sha256()
    q = int(np.argmin(arrays["margin"]))
    r = int(arrays["runner_up"][q])
    return {
        "device": "cuda",
        "batch_size": B,
        "batches": -(-n // B),
        "rows": n,
        "id_sha256": id_digest(P, table_sha, np.arange(n), arrays["ids"]),
        "score_sha256": score_digest(P, table_sha, arrays["best"], arrays["margin"]),
        "ties": int((arrays["tied"] > 0).sum()),
        "min_margin": {
            "margin": float(arrays["margin"][q]),
            "query_id": q,
            "query_bytes_hex": table.row(q).hex(),
            "runner_up_id": r,
            "runner_up_bytes_hex": table.row(r).hex(),
        },
        "candidate_encode_seconds": round(t1 - t0, 3),
        "decode_seconds": round(t2 - t1, 3),
        "peak_gpu_memory_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
        "environment": gpu_environment(torch),
    }


# CPU reference -------------------------------------------------------------------------------------------------


def query_count(table: ByteTable, limit: int | None) -> int:
    return table.vocab_size if limit is None else min(limit, table.vocab_size)


_CPU_STATE: dict = {}


def _cpu_init(tables: str, kind: str, pos_dim: int, tokenizer_sha256: str) -> None:
    import torch

    torch.set_num_threads(1)
    ensure_kronecker_embeddings()
    table = load_table(Path(tables), kind, pos_dim, tokenizer_sha256)
    _CPU_STATE.update(table=table, code_table=decode_ref.CodeTable.from_byte_table(table))


def _cpu_chunk(span: tuple[int, int]) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
    from ke2.codec import encode_ids

    start, end = span
    vectors = encode_ids(np.arange(start, end), _CPU_STATE["table"]).numpy()  # upstream codec, float32, CPU
    result = decode_ref.decode(vectors, _CPU_STATE["code_table"])
    return start, result.token_ids, result.scores, result.margins


def cpu_worker(args) -> dict:
    import torch

    table = load_table(args.tables, args.kind, args.pos_dim, args.tokenizer_sha256)
    n, P = query_count(table, args.limit), table.pos_dim
    spans = [(s, min(s + CPU_CHUNK, n)) for s in range(0, n, CPU_CHUNK)]
    ids = np.empty(n, dtype=np.int64)
    scores = np.empty(n, dtype=np.float64)
    margins = np.empty(n, dtype=np.float64)
    init = (str(args.tables), args.kind, P, args.tokenizer_sha256)
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.cpu_workers, initializer=_cpu_init, initargs=init) as pool:
        for start, t, s, m in pool.map(_cpu_chunk, spans):
            ids[start : start + len(t)], scores[start : start + len(t)], margins[start : start + len(t)] = t, s, m
    seconds = time.perf_counter() - t0
    np.savez(args.arrays, ids=ids, best=scores, margin=margins)
    table_sha = table.sha256()
    return {
        "device": "cpu",
        "rows": n,
        "encoder": "upstream kronecker_codec, float32, CPU, one torch thread per worker",
        "decoder": "decode_ref.decode, cosine, float64, CPU, exhaustive",
        "chunk_rows": CPU_CHUNK,
        "worker_processes": args.cpu_workers,
        "id_sha256": id_digest(P, table_sha, np.arange(n), ids),
        "score_sha256": score_digest(P, table_sha, scores, margins),
        "ties": int((margins == 0).sum()),
        "seconds": round(seconds, 1),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "system": platform.system(),
            "machine": platform.machine(),
            "device": "cpu",
        },
    }


# Parent: fresh processes, comparison, results ------------------------------------------------------------------


def run_child(args, role: str, arrays: Path, batch_size: int | None = None) -> dict:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        role,
        "--arrays",
        str(arrays),
        "--tables",
        str(args.tables.resolve()),
        "--kind",
        args.kind,
        "--pos-dim",
        str(args.pos_dim),
        "--tokenizer-sha256",
        args.tokenizer_sha256,
        "--cpu-workers",
        str(args.cpu_workers),
    ]
    if batch_size is not None:
        command += ["--batch-size", str(batch_size)]
    if args.limit is not None:
        command += ["--limit", str(args.limit)]
    env = dict(os.environ, CUBLAS_WORKSPACE_CONFIG=CUBLAS_WORKSPACE_CONFIG, PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.run(command, env=env, capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(f"{role} process failed:\n{process.stderr.strip()}")
    return json.loads(process.stdout)


def compare_with_cpu(gpu: dict, cpu: dict, *, show: int = 20) -> dict:
    """Compare one GPU run's arrays with the CPU reference arrays (both dicts of numpy arrays)."""
    wrong = np.flatnonzero(gpu["ids"] != cpu["ids"])
    return {
        "ids_equal_cpu": int(wrong.size) == 0,
        "mismatching_ids": int(wrong.size),
        "first_mismatches": [
            {"query": int(q), "gpu": int(gpu["ids"][q]), "cpu": int(cpu["ids"][q])} for q in wrong[:show]
        ],
        "max_abs_score_difference": float(np.abs(gpu["best"].astype(np.float64) - cpu["best"]).max()),
        "max_abs_margin_difference": float(np.abs(gpu["margin"].astype(np.float64) - cpu["margin"]).max()),
    }


def summarize(cpu_run: dict, gpu_runs: list[dict]) -> dict:
    """Gate checks per batch size: three matching ID hashes, equal to the CPU reference hash."""
    by_size: dict[int, list[dict]] = {}
    for run in gpu_runs:
        by_size.setdefault(run["batch_size"], []).append(run)
    summary = {}
    for size, runs in sorted(by_size.items()):
        if len(runs) != RUNS:
            raise ValueError(f"batch size {size}: expected {RUNS} runs, got {len(runs)}")
        summary[str(size)] = {
            "three_id_hashes_match": len({r["id_sha256"] for r in runs}) == 1,
            "three_score_hashes_match": len({r["score_sha256"] for r in runs}) == 1,
            "id_hash_equals_cpu": all(r["id_sha256"] == cpu_run["id_sha256"] for r in runs),
            "ids_equal_cpu_every_run": all(r["comparison"]["ids_equal_cpu"] for r in runs),
            "ties": max(r["ties"] for r in runs),
            "max_abs_score_difference": max(r["comparison"]["max_abs_score_difference"] for r in runs),
            "max_abs_margin_difference": max(r["comparison"]["max_abs_margin_difference"] for r in runs),
            "decode_seconds": [r["decode_seconds"] for r in runs],
        }
    scores = {r["score_sha256"] for r in gpu_runs}
    summary["all_batch_sizes"] = {
        "id_hashes_match": len({r["id_sha256"] for r in gpu_runs}) == 1,
        "score_hashes_match": len(scores) == 1,
        "distinct_score_hashes": len(scores),
    }
    return summary


def passed(summary: dict) -> bool:
    sizes = [v for k, v in summary.items() if k != "all_batch_sizes"]
    return bool(sizes) and all(
        s["three_id_hashes_match"] and s["id_hash_equals_cpu"] and s["ids_equal_cpu_every_run"] for s in sizes
    )


def committed_sample_check(table: ByteTable, cpu: dict) -> dict | None:
    """Recompute the committed ``decode_ref/summary.json`` hash from this CPU run's rows for the same sample."""
    path = RESULTS_DIR / "decode_ref" / "summary.json"
    if not path.is_file():
        return None
    committed = json.loads(path.read_text(encoding="utf-8"))
    run = committed["runs"].get(f"{table.kind}_P{table.pos_dim}")
    sample = np.asarray(committed["sample"]["query_token_ids"], dtype=np.int64)
    if run is None or run["table_sha256"] != table.sha256() or sample.max() >= cpu["ids"].shape[0]:
        return None
    ids = cpu["ids"][sample]
    recomputed = decode_ref.DecodeResult(
        token_ids=ids,
        token_bytes=[table.row(int(t)) for t in ids],
        scores=cpu["best"][sample],
        margins=cpu["margin"][sample],
        pos_dim=table.pos_dim,
        table_sha256=table.sha256(),
    ).sha256()
    return {
        "file": "results/decode_ref/summary.json",
        "sample_size": int(sample.size),
        "committed_sha256": run["sha256"],
        "recomputed_sha256": recomputed,
        "equal": recomputed == run["sha256"],
    }


def load_arrays(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", type=Path, default=TABLES_DIR, help="folder with the committed byte tables")
    ap.add_argument("--kind", choices=("raw", "decode"), default="raw")
    ap.add_argument("--pos-dim", type=int, default=32)
    ap.add_argument("--batch-sizes", type=int, nargs="+", default=list(BATCH_SIZES))
    ap.add_argument("--tokenizer-sha256", default=TOKENIZER_SHA256, help="tokenizer the table must belong to")
    ap.add_argument("--cpu-workers", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--limit", type=int, help="smoke test: decode only the first N IDs (candidates stay complete)")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--worker", choices=("cpu", "gpu"), help=argparse.SUPPRESS)
    ap.add_argument("--arrays", type=Path, help=argparse.SUPPRESS)
    ap.add_argument("--batch-size", type=int, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if any(b <= 0 for b in args.batch_sizes) or args.cpu_workers <= 0 or (args.limit is not None and args.limit <= 0):
        ap.error("batch sizes, --cpu-workers and --limit must be positive")
    if args.worker:
        print(json.dumps((gpu_worker if args.worker == "gpu" else cpu_worker)(args), sort_keys=True))
        return 0

    table = load_table(args.tables, args.kind, args.pos_dim, args.tokenizer_sha256)
    n = query_count(table, args.limit)
    with tempfile.TemporaryDirectory() as tmp:
        cpu_run = run_child(args, "cpu", Path(tmp) / "cpu.npz")
        cpu = load_arrays(Path(tmp) / "cpu.npz")
        print(f"CPU reference: {n} IDs in {cpu_run['seconds']} s, ID hash {cpu_run['id_sha256'][:16]}…", flush=True)
        gpu_runs = []
        for size in args.batch_sizes:
            for index in range(1, RUNS + 1):
                arrays = Path(tmp) / f"gpu_{size}_{index}.npz"
                run = run_child(args, "gpu", arrays, batch_size=size)
                run["run"] = index
                run["comparison"] = compare_with_cpu(load_arrays(arrays), cpu)
                gpu_runs.append(run)
                print(
                    f"GPU batch {size} run {index}/{RUNS}: {run['decode_seconds']} s, "
                    f"ID hash {run['id_sha256'][:16]}…, equal to CPU: {run['comparison']['ids_equal_cpu']}",
                    flush=True,
                )
    summary = summarize(cpu_run, gpu_runs)
    environments = {json.dumps(r["environment"], sort_keys=True) for r in gpu_runs}
    if len(environments) != 1:
        raise RuntimeError("the GPU environment changed between processes")
    sample = committed_sample_check(table, cpu)
    report = {
        "check": "decode every token ID on GPU three times per batch size; compare with the CPU reference",
        "passed": passed(summary),
        "hash_formats": {
            ID_HASH_FORMAT: "header '<format>|P=<P>|table=<table sha256>|n=<rows>' + LF; then per query, in "
            "ascending query ID order: query ID and decoded ID as big-endian uint32",
            SCORE_HASH_FORMAT: "header '<format>|P=<P>|table=<table sha256>|n=<rows>|dtype=<dtype>' + LF; then "
            "per query: best cosine and margin, little-endian (<f4 on GPU, <f8 for the CPU reference)",
        },
        "inputs": {
            "table": table_path(Path("results/tables"), table.kind, table.pos_dim).as_posix(),
            "kind": table.kind,
            "pos_dim": table.pos_dim,
            "table_sha256": table.sha256(),
            "tokenizer_sha256": table.tokenizer_sha256,
            "vocabulary_size": table.vocab_size,
            "queries": n,
            "full_vocabulary": n == table.vocab_size,
            "upstream_codec_commit": UPSTREAM_CODEC_COMMIT,
            "upstream_codec_sha256": codec_source_sha256(),
            "source_sha256": {
                "decode_gpu.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "decode_ref.py": hashlib.sha256(Path(decode_ref.__file__).read_bytes()).hexdigest(),
            },
        },
        "gpu_method": {
            "encoder": "upstream kronecker_codec on the GPU, float32; query batch = the batch size",
            "candidates": f"all V codes, encoded on the GPU in chunks of {CANDIDATE_CHUNK}, rows scaled to unit norm",
            "scores": "cosine = unit query rows @ unit candidate rows.T, float32, one matmul per batch",
            "decision": "first maximum (ties to the lowest ID); margin = best minus second-best cosine",
            "settings": "TF32 off (matmul and cuDNN), float32 matmul precision 'highest', deterministic "
            f"algorithms on, CUBLAS_WORKSPACE_CONFIG={CUBLAS_WORKSPACE_CONFIG}",
            "processes": f"{RUNS} fresh processes per batch size",
        },
        "summary": summary,
        "cpu_reference": {**cpu_run, "min_margin": float(cpu["margin"].min()), "committed_sample": sample},
        "gpu_min_margin": min((r["min_margin"] for r in gpu_runs), key=lambda m: m["margin"]),
        "runs": gpu_runs,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"{table.kind}_P{table.pos_dim}"
    (args.out / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# device batch_size run ID_SHA256 SCORE_SHA256\n"]
    lines.append(f"cpu - 1 {cpu_run['id_sha256']} {cpu_run['score_sha256']}\n")
    lines += [f"gpu {r['batch_size']} {r['run']} {r['id_sha256']} {r['score_sha256']}\n" for r in gpu_runs]
    (args.out / f"{stem}_sha256.txt").write_text("".join(lines), encoding="ascii")
    print(json.dumps(summary, indent=2))
    print("PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
