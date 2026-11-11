#!/usr/bin/env python3
"""Decode every token id in fixed batch sizes, several fresh processes, on a chosen device (Gate 2).

For each batch size the forward codec (upstream ``kronecker_codec``, float32, on the device) encodes
the ids of the batch, the structured cosine scorer (``ke2.scoring``) picks the nearest token over the
whole vocabulary, and the ids are hashed. TF32 is disabled so CUDA float32 means float32. The parent
starts ``--repeats`` fresh processes per batch size, requires their hashes to agree, and compares
every id with the CPU float64 reference (``decode_ref.decode`` on float32 CPU codes, computed once and
cached in ``results/decode_cpu/decode_ref_full_<kind>_P<P>_<table sha8>.npz``).
The parent exits 1 if any batch size has differing hashes or ids differing from the reference. Every run also gets
the id digest in ``decode_gpu.py``'s format (``ke2-decode-gpu-ids-v1``: header, then (query id, decoded id) pairs as
big-endian uint32), so a CPU run and the GPU run in ``results/decode_gpu/`` are compared by one value.

This is the CPU counterpart of ``decode_gpu.py`` (determinism_gpu.md): same ids, same batch sizes, three fresh
processes each, fp32 with TF32 off, the same float64 reference. On ``cuda`` and ``mps`` the structured scorer uses
sparse or ``index_add_`` kernels whose atomics are not made deterministic here (no ``use_deterministic_algorithms``,
no ``CUBLAS_WORKSPACE_CONFIG``); the committed run is CPU only. The default output folder is
``results/decode_<device>/`` (``decode_cuda``, never ``decode_gpu``, which belongs to ``decode_gpu.py``).

usage: python decode_batches.py --device cpu|cuda|mps [--batch-sizes 1 7 4096] [--repeats 3]
                                [--table results/tables/raw_table_P32.npz] [--out results/decode_<device>/<kind>_P<P>.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ke2.upstream import ensure_kronecker_embeddings

    ensure_kronecker_embeddings()

import numpy as np
import torch

import decode_ref as dr
from decode_gpu import codec_source_sha256, id_digest
from ke2.codec import encode_ids
from ke2.config import RESULTS_DIR, TABLES_DIR, TOKENIZER_SHA256
from ke2.scoring import StructuredScorer
from ke2.tables import ByteTable

HASH_FORMAT = "ke2-decode-batches-v1"


def configure_device(device: str) -> torch.device:
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    dev = torch.device(device)
    if dev.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    if dev.type == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS requested but not available")
    return dev


def encode_fp32_on_device(table: ByteTable, ids: np.ndarray, device: torch.device) -> torch.Tensor:
    from kronecker_embeddings.codec import kronecker_codec

    b = torch.from_numpy(table.bytes[ids]).to(device)
    n = torch.from_numpy(table.lengths[ids].astype(np.int64)).to(device)
    return kronecker_codec(b, n, pos_dim=table.pos_dim)  # float32 on the device


def decode_all(table: ByteTable, ct, device: str, batch_size: int) -> np.ndarray:
    dev = configure_device(device)
    scorer = StructuredScorer(ct, dev, torch.float32)
    out = np.empty(table.vocab_size, dtype=np.int64)
    with torch.inference_mode():
        for s in range(0, table.vocab_size, batch_size):
            ids = np.arange(s, min(s + batch_size, table.vocab_size))
            best_id, *_ = scorer.top2(encode_fp32_on_device(table, ids, dev))
            out[s : s + ids.size] = best_id.numpy()
    if dev.type == "cuda":
        torch.cuda.synchronize()
    return out


def ids_sha256(ids: np.ndarray, P: int, device: str, batch_size: int) -> str:
    h = hashlib.sha256(f"{HASH_FORMAT}|P={P}|device={device}|dtype=float32|batch={batch_size}|n={ids.size}\n".encode())
    h.update(np.ascontiguousarray(ids, dtype="<i8").tobytes())
    return h.hexdigest()


def ids_sha256_gpu_format(ids: np.ndarray, P: int, table_sha256: str) -> str:
    """``decode_gpu.id_digest`` of the map 0..V-1 -> ids: the value every GPU run in results/decode_gpu/ reports."""
    ids = np.asarray(ids)
    return id_digest(P, table_sha256, np.arange(ids.size), ids)


def reference_cache_path(table: ByteTable, ct) -> Path:
    return RESULTS_DIR / "decode_cpu" / f"decode_ref_full_{table.kind}_P{table.pos_dim}_{ct.table_sha256[:8]}.npz"


def default_out(device: str, table: Path) -> Path:
    """``results/decode_<device>/<kind>_P<P>.json``; ``cuda`` goes to ``decode_cuda``, never to ``decode_gpu.py``'s folder."""
    return RESULTS_DIR / f"decode_{device.replace(':', '')}" / f"{table.stem.replace('_table', '')}.json"


def reference_ids(table: ByteTable, ct, cache: Path, chunk: int = 2048) -> tuple[np.ndarray, dict]:
    """float64 exhaustive decode_ref ids for every token, from float32 CPU codes; cached by table and codec hash.

    The cache is reused only when it names the same table content hash and the same upstream codec source hash;
    anything else (missing keys, another table, another codec) recomputes and rewrites it.
    """
    codec_sha = codec_source_sha256()
    if cache.is_file():
        with np.load(cache) as z:
            same_table = "table_sha256" in z.files and str(z["table_sha256"]) == ct.table_sha256
            same_codec = "codec_sha256" in z.files and str(z["codec_sha256"]) == codec_sha
            if same_table and same_codec:
                return z["ids"], {"cached": True, "sha256": str(z["sha256"]), "codec_sha256": codec_sha}
    t0 = time.perf_counter()
    ids = np.empty(table.vocab_size, dtype=np.int64)
    for s in range(0, table.vocab_size, chunk):
        blk = np.arange(s, min(s + chunk, table.vocab_size))
        ids[s : s + blk.size] = dr.decode(encode_ids(blk, table).numpy(), ct).token_ids
    sha = ids_sha256(ids, table.pos_dim, "", 0)  # same framing as every run's ids_body_sha256, so the values compare
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache, ids=ids, sha256=np.array(sha), table_sha256=np.array(ct.table_sha256), codec_sha256=np.array(codec_sha)
    )
    return ids, {
        "cached": False,
        "sha256": sha,
        "codec_sha256": codec_sha,
        "seconds": round(time.perf_counter() - t0, 1),
    }


def environment(device: str) -> dict:
    env = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "device": device,
        "dtype": "float32",
        "tf32_matmul": bool(torch.backends.cuda.matmul.allow_tf32),
        "tf32_cudnn": bool(torch.backends.cudnn.allow_tf32),
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
        "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }
    dev = torch.device(device)
    if dev.type == "cuda" and torch.cuda.is_available():
        idx = dev.index if dev.index is not None else 0
        env["gpu"] = torch.cuda.get_device_name(idx)
        env["gpu_capability"] = list(torch.cuda.get_device_capability(idx))
        env["cuda"] = torch.version.cuda
        env["cudnn"] = torch.backends.cudnn.version()
    return env


def child(a) -> int:
    configure_device(a.device)
    table = ByteTable.load(a.table, tokenizer_sha256=a.tokenizer_sha256)
    ct = dr.CodeTable.from_byte_table(table)
    t0 = time.perf_counter()
    ids = decode_all(table, ct, a.device, a.batch_size)
    np.save(a.ids_out, ids)
    print(
        json.dumps(
            {
                "sha256": ids_sha256(ids, table.pos_dim, a.device, a.batch_size),
                "seconds": round(time.perf_counter() - t0, 1),
                "environment": environment(a.device),
            }
        )
    )
    return 0


def parent(a) -> int:
    configure_device(a.device)  # so the recorded environment reflects the flags the children set
    table = ByteTable.load(a.table, tokenizer_sha256=a.tokenizer_sha256)
    ct = dr.CodeTable.from_byte_table(table)
    ref, ref_info = reference_ids(table, ct, a.reference_cache or reference_cache_path(table, ct))
    report = {
        "format": HASH_FORMAT,
        "P": table.pos_dim,
        "table_sha256": ct.table_sha256,
        "vocab_size": table.vocab_size,
        "device": a.device,
        "reference": {
            "decoder": "decode_ref.decode, float64, CPU, float32 CPU codes",
            **ref_info,
            "ids_equal_arange": bool(np.array_equal(ref, np.arange(table.vocab_size))),
            "ids_sha256_gpu_format": ids_sha256_gpu_format(ref, table.pos_dim, ct.table_sha256),
        },
        "batch_sizes": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        for b in a.batch_sizes:
            runs = []
            for r in range(a.repeats):
                ids_out = Path(tmp) / f"ids_b{b}_r{r}.npy"
                cmd = [
                    sys.executable,
                    __file__,
                    "--child",
                    "--device",
                    a.device,
                    "--batch-size",
                    str(b),
                    "--table",
                    str(a.table),
                    "--tokenizer-sha256",
                    a.tokenizer_sha256,
                    "--ids-out",
                    str(ids_out),
                ]
                try:
                    out = (
                        subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
                    )
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(
                        f"child failed (device={a.device}, batch={b}, run={r}, exit {e.returncode}):\n{e.stderr}"
                    ) from e
                info = json.loads(out)
                ids = np.load(ids_out)
                info["ids_equal_reference"] = bool(np.array_equal(ids, ref))
                info["ids_differing_from_reference"] = int((ids != ref).sum())
                info["ids_body_sha256"] = ids_sha256(ids, table.pos_dim, "", 0)
                info["ids_sha256_gpu_format"] = ids_sha256_gpu_format(ids, table.pos_dim, ct.table_sha256)
                runs.append(info)
                print(
                    f"device={a.device} batch={b} run={r} sha={info['sha256'][:12]} equal_ref={info['ids_equal_reference']} {info['seconds']}s",
                    flush=True,
                )
            report["batch_sizes"][str(b)] = {
                "runs": runs,
                "hashes_match": len({x["sha256"] for x in runs}) == 1,
                "all_equal_reference": all(x["ids_equal_reference"] for x in runs),
            }
    all_runs = [x for v in report["batch_sizes"].values() for x in v["runs"]]
    report["all_runs_equal_reference"] = all(x["ids_equal_reference"] for x in all_runs)
    report["same_ids_across_batch_sizes"] = len({x["ids_body_sha256"] for x in all_runs}) == 1
    report["ids_sha256_gpu_format"] = sorted({x["ids_sha256_gpu_format"] for x in all_runs})
    report["environment"] = environment(a.device)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(report)
    a.out.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md)
    ok = all(v["hashes_match"] and v["all_equal_reference"] for v in report["batch_sizes"].values())
    return 0 if ok else 1


def to_markdown(report: dict) -> str:
    lines = [
        f"Device `{report['device']}`, float32, TF32 off, P = {report['P']}, {report['vocab_size']:,} ids per run. "
        f"Reference: {report['reference']['decoder']}; reference ids equal 0..V-1: {report['reference']['ids_equal_arange']}.",
        "",
        "| batch size | runs | hashes match | sha256 (run 1) | ids equal to reference (every run) | seconds per run |",
        "|---|---|---|---|---|---|",
    ]
    for b, v in report["batch_sizes"].items():
        secs = ", ".join(str(x["seconds"]) for x in v["runs"])
        lines.append(
            f"| {b} | {len(v['runs'])} | {'yes' if v['hashes_match'] else 'NO'} | `{v['runs'][0]['sha256'][:16]}…` | "
            f"{'yes' if v['all_equal_reference'] else 'NO (' + str(max(x['ids_differing_from_reference'] for x in v['runs'])) + ' differ)'} | {secs} |"
        )
    if "ids_sha256_gpu_format" in report:
        g = report["ids_sha256_gpu_format"]
        lines += [
            "",
            f"ID hash in `decode_gpu.py`'s format (`ke2-decode-gpu-ids-v1`), {'the same in every run' if len(g) == 1 else 'NOT the same across runs'}: "
            + ", ".join(f"`{x}`" for x in g)
            + ". Compare with `results/decode_gpu/raw_P32_sha256.txt`.",
        ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 7, 4096])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--table", type=Path, default=TABLES_DIR / "raw_table_P32.npz")
    ap.add_argument("--tokenizer-sha256", default=TOKENIZER_SHA256)
    ap.add_argument("--out", type=Path, default=None, help="default results/decode_<device>/<kind>_P<P>.json (+ .md)")
    ap.add_argument(
        "--reference-cache",
        type=Path,
        default=None,
        help="where the float64 reference ids are cached (default results/decode_cpu/decode_ref_full_*.npz)",
    )
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--batch-size", type=int, help=argparse.SUPPRESS)
    ap.add_argument("--ids-out", type=Path, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.child:
        return child(a)
    if any(b <= 0 for b in a.batch_sizes) or a.repeats <= 0:
        ap.error("--batch-sizes and --repeats must be positive")
    a.out = a.out or default_out(a.device, a.table)
    return parent(a)


if __name__ == "__main__":
    sys.exit(main())
