#!/usr/bin/env python3
"""Build the frozen bf16 KE2 codes from the committed p1536 raw byte table.

Input: ``results/tables/p1536-s0/raw_table_P{P}.npz`` (committed by #498), loaded only if it is bound
to the frozen tokenizer SHA-256 (``ke2.config.FROZEN_TOKENIZER_SHA256``), its content hash
re-verifies, and that hash equals the one in the table's ``manifest.json``. No tokenizer file is
needed. The per-length bf16 code values come from the upstream float32 codec; then the codec runs on
every token and its bf16 output must equal the rows rebuilt from the compact values, bit for bit.
Every row is hashed on the way; the matrix is never held in memory.

Outputs (default ``teams/04-ke2/results/bf16/``):
  bf16_codes_P{P}.npz    compact codes: ``high_bits``/``low_bits`` (P + 1,) uint16 bf16 patterns, index L,
                         plus tokenizer, raw-table, codes, matrix and row-hash SHA-256 (committed)
  bf16_codes_P{P}.json   the config: shapes, layout, EOS, codec source, and the same hashes (committed)
  materialized/bf16_matrix_P{P}.npy   with ``--materialize`` only: the ``(V, D)`` matrix as uint16 bf16
                         bits (2 GiB at P = 32; git-ignored). Load with
                         ``torch.from_numpy(np.load(path)).view(torch.bfloat16)``.

Lab rule (15 Nov): a file above pr-guard's 5 MB limit is not committed; its build script, config and
SHA-256 are. The raw table (0.8 MB) and the compact codes are committed; the matrix is not.

Usage:
  python build_bf16_codes.py [--table PATH] [--pos-dim 32] [--out DIR] [--materialize]

Takes about ten seconds at P = 32 on an M1.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import sys
import time
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from ke2.bf16_codes import BF16_FORMAT, Bf16Codes, codes_for_table, stream_rows
from ke2.config import (
    BF16_DIR,
    BF16_POS_DIM,
    EOS_ID,
    EOS_TOKEN,
    FROZEN_NAME,
    FROZEN_TABLES_DIR,
    FROZEN_TOKENIZER_SHA256,
    MAX_COMMIT_BYTES,
    TEAM_DIR,
    UPSTREAM_CODEC_COMMIT,
)
from ke2.tables import ByteTable, TableContractError, table_path
from ke2.upstream import ensure_kronecker_embeddings

log = logging.getLogger("build_bf16_codes")


def codes_path(out_dir: Path, pos_dim: int) -> Path:
    return Path(out_dir) / f"bf16_codes_P{pos_dim}.npz"


def config_path(out_dir: Path, pos_dim: int) -> Path:
    return Path(out_dir) / f"bf16_codes_P{pos_dim}.json"


def matrix_path(out_dir: Path, pos_dim: int) -> Path:
    return Path(out_dir) / "materialized" / f"bf16_matrix_P{pos_dim}.npy"


def frozen_table_path(pos_dim: int) -> Path:
    """The committed raw table of the frozen tokenizer at ``pos_dim``."""
    return table_path(FROZEN_TABLES_DIR, "raw", pos_dim)


def load_frozen_table(path: Path, pos_dim: int) -> ByteTable:
    """Load a raw table bound to the frozen tokenizer; check it against its manifest when it has one."""
    table = ByteTable.load(path, tokenizer_sha256=FROZEN_TOKENIZER_SHA256)
    if table.kind != "raw" or table.pos_dim != pos_dim:
        raise TableContractError(f"{path}: need the raw table at P={pos_dim}, got {table.kind} P={table.pos_dim}")
    manifest = Path(path).parent / "manifest.json"
    if manifest.is_file():
        entry = json.loads(manifest.read_text(encoding="utf-8"))["tables"].get(Path(path).name)
        if entry is not None and entry["sha256"] != table.sha256():
            raise TableContractError(f"{path}: sha256 {table.sha256()[:12]}… != {manifest} {entry['sha256'][:12]}…")
    if table.n_truncated or table.n_empty_rows:
        raise TableContractError(f"{path}: {table.n_truncated} truncated and {table.n_empty_rows} empty rows")
    if table.row(EOS_ID) != EOS_TOKEN.encode("utf-8"):
        raise TableContractError(f"{path}: row {EOS_ID} is {table.row(EOS_ID)!r}, expected EOS {EOS_TOKEN!r}")
    return table


def build(table: ByteTable, *, materialize: Path | None = None, chunk_rows: int = 1024):
    """Compact codes for ``table`` with their matrix hashes filled in, and the stream result."""
    codes = codes_for_table(table)
    out = None
    if materialize is not None:
        materialize.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            materialize, mode="w+", dtype=np.uint16, shape=(table.vocab_size, codes.output_dim)
        )
    res = stream_rows(codes, table, chunk_rows=chunk_rows, verify_codec=True, out=out)
    if out is not None:
        out.flush()
        del out
    codes.matrix_sha256 = res.matrix_sha256
    codes.row_hashes_sha256 = res.row_hashes_sha256
    return codes, res


def repo_path(path: Path) -> str:
    """``path`` relative to the repository root when it lies inside it."""
    try:
        return Path(path).resolve().relative_to(TEAM_DIR.parents[1]).as_posix()
    except ValueError:
        return str(path)


def config_dict(table: ByteTable, table_file: Path, codes: Bf16Codes, npz_name: str) -> dict:
    P, D, V = codes.pos_dim, codes.output_dim, codes.vocab_size
    size = Path(table_file).stat().st_size
    return {
        "format": BF16_FORMAT,
        "tokenizer": {
            "name": FROZEN_NAME,
            "sha256": codes.tokenizer_sha256,
            "vocab_size": V,
            "eos": {"id": EOS_ID, "content": EOS_TOKEN},
            "release": "teams/03-tokenizer/release/ (tokenizer.json is not in the repo: over 5 MB)",
        },
        "raw_table": {
            "kind": table.kind,
            "pos_dim": P,
            "shape": list(table.bytes.shape),
            "n_truncated": table.n_truncated,
            "n_empty_rows": table.n_empty_rows,
            "sha256": table.sha256(),
            "file": repo_path(table_file),
            "bytes": size,
            "committed": size <= MAX_COMMIT_BYTES,
            "check": "python teams/04-ke2/src/verify_frozen_table.py [PATH]",
        },
        "codec": {
            "char_dim": codes.char_dim,
            "pos_dim": P,
            "output_dim": D,
            "source": "kronecker_embeddings.codec.kronecker_codec (float32) then .to(torch.bfloat16)",
            "upstream_commit": UPSTREAM_CODEC_COMMIT,
            "torch": importlib.metadata.version("torch"),
        },
        "compact": {
            "file": npz_name,
            "arrays": {"high_bits": [P + 1], "low_bits": [P + 1]},
            "dtype": "uint16 bit patterns of bfloat16, indexed by byte length L",
            "sha256": codes.sha256(),
            "hash_rule": f"sha256('{BF16_FORMAT}|P|char_dim|tokenizer_sha256|raw_table_sha256|' + high_bits + low_bits, uint16 LE)",
        },
        "matrix": {
            "shape": [V, D],
            "dtype": "bfloat16",
            "bytes": V * D * 2,
            "committed": V * D * 2 <= MAX_COMMIT_BYTES,
            "layout": "row t: low[L_t] everywhere, high[L_t] at index byte * P + position for position < L_t",
            "sha256": codes.matrix_sha256,
            "hash_rule": "sha256 of the row-major little-endian bf16 bytes, no header",
            "row_hashes_sha256": codes.row_hashes_sha256,
            "row_hashes_rule": "sha256 of the (V, 32) array of per-row sha256 digests, in id order",
            "file": f"materialized/bf16_matrix_P{P}.npy (uint16 bits; python teams/04-ke2/src/build_bf16_codes.py "
            "--materialize; git-ignored)",
        },
        "verified": "every row of the codec's bf16 output equals the row rebuilt from the compact codes, bit for bit",
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", type=Path, default=None, help="raw table .npz (default: the committed p1536 table)")
    ap.add_argument("--pos-dim", type=int, default=BF16_POS_DIM)
    ap.add_argument("--out", type=Path, default=BF16_DIR)
    ap.add_argument("--materialize", action="store_true", help="also write the (V, D) bf16 matrix as .npy")
    ap.add_argument("--chunk-rows", type=int, default=1024)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ensure_kronecker_embeddings()

    tpath = a.table or frozen_table_path(a.pos_dim)
    table = load_frozen_table(tpath, a.pos_dim)
    log.info(
        "raw table %s: %s (V=%d, tokenizer %s…)", FROZEN_NAME, tpath, table.vocab_size, FROZEN_TOKENIZER_SHA256[:12]
    )
    t0 = time.perf_counter()
    mpath = matrix_path(a.out, a.pos_dim) if a.materialize else None
    codes, _ = build(table, materialize=mpath, chunk_rows=a.chunk_rows)
    npz = codes_path(a.out, a.pos_dim)
    codes.save(npz)
    cfg = config_dict(table, tpath, codes, npz.name)
    config_path(a.out, a.pos_dim).write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    log.info("raw table sha256   %s", table.sha256())
    log.info("codes sha256       %s", codes.sha256())
    log.info("matrix sha256      %s  (%d x %d bf16)", codes.matrix_sha256, codes.vocab_size, codes.output_dim)
    log.info("row-hashes sha256  %s", codes.row_hashes_sha256)
    if mpath is not None:
        log.info("materialized       %s", mpath)
    log.info("wrote %s and %s in %.0f s", npz, config_path(a.out, a.pos_dim), time.perf_counter() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
