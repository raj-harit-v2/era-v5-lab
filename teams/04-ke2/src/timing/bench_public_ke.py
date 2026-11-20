"""Microbenchmark only Team 6's ``model.tok(x)`` call on the frozen tokenizer.

This is an isolated eval/no-grad operation timed with Team 6's StepTimer. It is
not the Level-3 ``embed.ke`` measurement inside a complete training step; use
the G6 layer/trace harness for that question.

Run from the lab repository root:
    python teams/04-ke2/src/timing/bench_public_ke.py --device cpu --out /tmp/model_tok_microbench.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

TEAM = Path(__file__).resolve().parents[2]
LAB = TEAM.parents[1]
sys.path.insert(0, str(TEAM / "src"))
sys.path.insert(0, str(LAB / "teams" / "06-performance"))

from ke2.config import FROZEN_TABLES_DIR, FROZEN_TOKENIZER_SHA256  # noqa: E402
from ke2.tables import ByteTable  # noqa: E402
from models.config import ModelConfig  # noqa: E402
from models.gpt import GPT  # noqa: E402
from perfkit.metrics import git_state  # noqa: E402
from perfkit.timer import StepTimer, stats, sync  # noqa: E402

FROZEN_TABLE_SHA256 = "21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a"


def relevant_sources_dirty() -> bool | None:
    """Whether the benchmark, embedding code, timer, or pinned table differs from HEAD."""
    paths = (
        "teams/04-ke2/src",
        "teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz",
        "teams/06-performance/models",
        "teams/06-performance/perfkit",
    )
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
            cwd=LAB, capture_output=True, text=True, timeout=10, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return bool(result.stdout.strip())


def measure(fn, device: torch.device, warmup: int, steps: int) -> dict:
    """Return Team 6 timer statistics for repeated calls to ``fn``.

    Args:
        fn: Zero-argument batch operation to time.
        device: Device on which the operation runs.
        warmup: Untimed calls before measurement.
        steps: Timed calls; CUDA events are read only after the loop.
    Returns:
        Team 6's millisecond statistics for the timed calls.
    """
    for _ in range(warmup):
        fn()
    sync(device)
    timer = StepTimer(device, expected_steps=steps)
    for _ in range(steps):
        timer.start()
        fn()
        timer.stop()
    return stats(timer.times_ms())


def run(args: argparse.Namespace) -> dict:
    """Build the verified p1536 workload, check it, and time only ``model.tok(x)``.

    Args:
        args: Parsed device, workload, repeat-count and thread-count options.
    Returns:
        Serializable provenance and the isolated input-embedding timing.
    """
    if min(args.batch_size, args.seq_len, args.steps, args.threads) < 1 or args.warmup < 0:
        raise ValueError("batch size, sequence length, steps and threads must be positive")
    torch.set_num_threads(args.threads)
    torch.manual_seed(0)
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if device.type == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS requested but unavailable")
    commit_sha, _ = git_state()
    dirty = relevant_sources_dirty()
    if device.type == "cuda" and (commit_sha is None or dirty is not False):
        raise RuntimeError("CUDA timing requires a clean Git checkout with a commit SHA")

    table = ByteTable.load(
        FROZEN_TABLES_DIR / "raw_table_P32.npz", tokenizer_sha256=FROZEN_TOKENIZER_SHA256
    )
    if table.vocab_size != 131_072 or table.n_truncated or table.n_empty_rows:
        raise ValueError("p1536 table fails the expected shape/length gate")
    table_hash = table.sha256()
    if table_hash != FROZEN_TABLE_SHA256:
        raise ValueError(f"p1536 table content hash mismatch: {table_hash}")
    token_bytes = (
        torch.from_numpy(table.bytes.copy()),
        torch.from_numpy(table.lengths.astype(np.int64)),
    )
    cfg = ModelConfig(
        vocab_size=table.vocab_size, embedding="ke2", block_size=args.seq_len,
        n_layer=1, n_head=4, n_embd=64, ffn="mlp", reversible=False,
        attn_impl="sdpa", ce_impl="torch", tie_embeddings=False,
    )
    model = GPT(cfg, token_bytes=token_bytes).to(device)
    original_ids = np.random.default_rng(0).integers(
        0, table.vocab_size, size=args.batch_size * args.seq_len, dtype=np.int64
    )
    x = torch.from_numpy(original_ids.reshape(args.batch_size, args.seq_len)).to(device)
    model.eval()
    with torch.no_grad():
        emb = model.tok(x)
        assert emb.shape == (*x.shape, cfg.n_embd)
        input_ms = measure(lambda: model.tok(x), device, args.warmup, args.steps)

    return {
        "contract": "isolated model.tok(x) microbenchmark in eval/no-grad; not a Level-3 region measurement",
        "tokenizer_sha256": FROZEN_TOKENIZER_SHA256,
        "table_sha256": table_hash,
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "commit_sha": commit_sha,
        "dirty": dirty,
        "platform": platform.platform(), "torch": torch.__version__,
        "threads": torch.get_num_threads(), "batch_size": args.batch_size,
        "sequence_length": args.seq_len,
        "id_sampling": "uniform token IDs, NumPy default_rng seed 0",
        "input_ids_sha256": hashlib.sha256(original_ids.astype("<i8").tobytes()).hexdigest(),
        "input_token_length_min": int(table.lengths[original_ids].min()),
        "input_token_length_max": int(table.lengths[original_ids].max()),
        "shape_check_calls": 1, "warmup": args.warmup, "steps": args.steps,
        "timings_ms": {"model.tok(x)_eval_no_grad": input_ms},
    }


def main() -> None:
    """Parse the workload, time it, and print/write a machine-readable report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda", "mps"))
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--seq-len", type=int, default=8)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    report = run(args)
    report["wall_seconds"] = round(time.perf_counter() - started, 3)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"gpu_name: {report['gpu_name'] or 'not applicable'}")
    print(f"commit_sha: {report['commit_sha'] or 'unavailable'}")
    print(f"dirty: {report['dirty']}")
    print(f"p1536 table {report['table_sha256']}")
    for name, values in report["timings_ms"].items():
        print(f"{name}: median {values['median']:.3f} ms (n={values['n']})")
    print(f"wall_seconds: {report['wall_seconds']:.3f}")


if __name__ == "__main__":
    main()
