"""Run Team 6's public Level-3 bench with a job-scoped p1536 pin.

This adapter changes module constants only in this Python process. It does not
change Team 6's baseline defaults or import any private model implementation.
Run the two arms as separate processes on the same GPU.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

P1536_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
P1536_TABLE_SHA256 = "21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a"


def main() -> int:
    """Verify inputs, pin this process to p1536, then call Team 6's bench."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--table", type=Path, required=True)
    ap.add_argument("--g6-root", type=Path, required=True)
    ap.add_argument("--arm", choices=("ke2", "dense-tied"), required=True)
    ap.add_argument("--device", choices=("cpu", "cuda", "mps"), default="cpu")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--trace", action="store_true", help="Include Team 6's profiler trace mode")
    a = ap.parse_args()
    if a.steps < 1 or a.warmup < 0:
        ap.error("steps must be positive and warmup nonnegative")
    tokenizer = a.tokenizer.resolve(strict=True)
    table_path = a.table.resolve(strict=True)
    g6_root = a.g6_root.resolve(strict=True)
    out_dir = a.out_dir.resolve()
    tokenizer_sha = hashlib.sha256(tokenizer.read_bytes()).hexdigest()
    if tokenizer_sha != P1536_SHA256:
        raise ValueError(f"p1536 tokenizer SHA-256 mismatch: {tokenizer_sha}")

    g4_src = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(g6_root))
    sys.path.insert(0, str(g4_src))
    from ke2.tables import ByteTable

    table = ByteTable.load(table_path, tokenizer_sha256=P1536_SHA256)
    table_sha = table.sha256()
    if table_sha != P1536_TABLE_SHA256 or table.vocab_size != 131_072 or table.pos_dim != 32:
        raise ValueError(f"p1536 P32 table mismatch: {table_sha}")
    if table.n_truncated or table.n_empty_rows:
        raise ValueError("p1536 table has truncated or empty rows")

    # Team 6's default module constants remain unchanged on disk. Patch all
    # imported aliases before bench builds its loader/model/metadata.
    import dataio.tokenizer as tokenizer_module
    import dataio.loader as loader_module
    import ke2.config as ke2_config
    from perfkit import bench

    tokenizer_module.SHA256 = P1536_SHA256
    tokenizer_module.REVISION = "p1536-sample-v0"
    loader_module.SHA256 = P1536_SHA256
    loader_module.REVISION = "p1536-sample-v0"
    bench.TOKENIZER_SHA256 = P1536_SHA256
    bench.TOKENIZER_REVISION = "p1536-sample-v0"
    ke2_config.TABLES_DIR = table_path.parent

    modes = "clean,layer,trace" if a.trace else "clean,layer"
    overrides = [
        f"run.device={a.device}", "run.dtype=fp32", "run.batch_size=2",
        "data.source=synthetic", f"data.tokenizer_path={tokenizer}",
        f"model.embedding={'ke2' if a.arm == 'ke2' else 'table'}",
        f"model.tie_embeddings={'false' if a.arm == 'ke2' else 'true'}",
        "model.block_size=16", "model.n_layer=1", "model.n_head=4",
        "model.n_kv_head=4", "model.n_embd=64", "model.reversible=false",
        "optim.name=adamw", "model.ffn=mlp", "model.ce_impl=torch",
        f"bench.out_dir={out_dir}",
    ]
    print(f"job_pin=p1536 tokenizer_sha256={tokenizer_sha} table_sha256={table_sha}", flush=True)
    return bench.main([
        "--config", str(g6_root / "configs" / "base.yaml"),
        "--modes", modes, "--level", "3", "--warmup", str(a.warmup),
        "--steps", str(a.steps), "--tag", a.tag, *overrides,
    ])


if __name__ == "__main__":
    raise SystemExit(main())
