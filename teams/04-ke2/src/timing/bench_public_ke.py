"""Time the public KE input path and exact code decoder on the frozen tokenizer.

This uses Team 6's StepTimer and model implementation with Team 4's SHA-checked
raw table. ``embedding=ke2`` in that model is a fast projection of the public
V1 byte code. The CPU float64 reference decoder operates on *unprojected*
codes; it is a separate inference operation, not part of a training step.

Run from the lab repository root:
    python teams/04-ke2/src/timing/bench_public_ke.py --device cpu --out /tmp/public_ke_timing.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

TEAM = Path(__file__).resolve().parents[2]
LAB = TEAM.parents[1]
sys.path.insert(0, str(TEAM / "src"))
sys.path.insert(0, str(LAB / "teams" / "06-performance"))

from decode_ref import CodeTable, decode  # noqa: E402
from ke2.codec import encode_f64  # noqa: E402
from ke2.config import FROZEN_TABLES_DIR, FROZEN_TOKENIZER_SHA256  # noqa: E402
from ke2.tables import ByteTable  # noqa: E402
from models.config import ModelConfig  # noqa: E402
from models.gpt import GPT  # noqa: E402
from perfkit.timer import StepTimer, stats, sync  # noqa: E402

FROZEN_TABLE_SHA256 = "21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a"


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
    """Build the verified p1536 workload, check it, then time each operation.

    Args:
        args: Parsed device, workload, repeat-count and thread-count options.
    Returns:
        Serializable provenance and timing statistics.
    """
    if min(args.batch_size, args.seq_len, args.decode_queries, args.steps) < 1 or args.warmup < 0:
        raise ValueError("batch size, sequence length, decode queries and steps must be positive")
    torch.set_num_threads(args.threads)
    torch.manual_seed(0)
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if device.type == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS requested but unavailable")

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
    y = (x + 1) % table.vocab_size
    h = torch.randn(args.batch_size, args.seq_len, cfg.n_embd, device=device)

    model.eval()
    with torch.no_grad():
        emb = model.tok(x)
        logits = model.head(h)
        chosen = logits.argmax(dim=-1)
        assert emb.shape == (*x.shape, cfg.n_embd)
        assert logits.shape == (*x.shape, table.vocab_size)
        assert chosen.shape == x.shape
        input_ms = measure(lambda: model.tok(x), device, args.warmup, args.steps)
        head_ms = measure(lambda: model.head(h), device, args.warmup, args.steps)
        select_ms = measure(lambda: logits.argmax(dim=-1), device, args.warmup, args.steps)

    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)

    def train_step() -> None:
        opt.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        assert loss is not None
        loss.backward()
        opt.step()

    train_step()  # correctness and optimizer-state initialization outside timing
    full_ms = measure(train_step, device, args.warmup, args.steps)

    reference_timings = {}
    if not args.skip_cpu_reference:
        code_table = CodeTable.from_byte_table(table)
        ids = np.random.default_rng(1).integers(0, table.vocab_size, size=args.decode_queries, dtype=np.int64)
        byte_rows = table.bytes[ids]
        lengths = table.lengths[ids]
        vectors = encode_f64(byte_rows, lengths, table.pos_dim)
        got = decode(vectors, code_table)
        if not np.array_equal(got.token_ids, ids):
            raise AssertionError("public exact decoder did not recover the sampled IDs")
        cpu = torch.device("cpu")
        reference_timings = {
            "reference_code_encode_cpu_float64": measure(
                lambda: encode_f64(byte_rows, lengths, table.pos_dim), cpu, args.warmup, args.steps
            ),
            "reference_code_decode_cpu_float64": measure(
                lambda: decode(vectors, code_table), cpu, args.warmup, args.steps
            ),
        }

    return {
        "contract": "public V1 code, Team 6 embedding=ke2 implementation; reference decode is separate",
        "tokenizer_sha256": FROZEN_TOKENIZER_SHA256,
        "table_sha256": table_hash,
        "device": str(device), "platform": platform.platform(), "torch": torch.__version__,
        "threads": torch.get_num_threads(), "batch_size": args.batch_size,
        "sequence_length": args.seq_len, "decode_queries": args.decode_queries,
        "id_sampling": "uniform token IDs, NumPy default_rng seed 0",
        "input_ids_sha256": hashlib.sha256(original_ids.astype("<i8").tobytes()).hexdigest(),
        "input_token_length_min": int(table.lengths[original_ids].min()),
        "input_token_length_max": int(table.lengths[original_ids].max()),
        "cpu_reference_skipped": args.skip_cpu_reference,
        "warmup": args.warmup, "steps": args.steps,
        "timings_ms": {
            "training_input_embedding_forward": input_ms,
            "training_output_head_forward": head_ms,
            "output_token_argmax": select_ms,
            "complete_training_step": full_ms,
            **reference_timings,
        },
    }


def main() -> None:
    """Parse the workload, time it, and print/write a machine-readable report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda", "mps"))
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--seq-len", type=int, default=8)
    parser.add_argument("--decode-queries", type=int, default=4)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--skip-cpu-reference", action="store_true",
                        help="CUDA timing job: omit the separate, already measured CPU reference decoder")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    report = run(args)
    report["wall_seconds"] = round(time.perf_counter() - started, 3)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    check = ("CPU reference skipped" if args.skip_cpu_reference
             else f"decoded {args.decode_queries}/{args.decode_queries} sampled IDs")
    print(f"p1536 table {report['table_sha256']} {check}")
    for name, values in report["timings_ms"].items():
        print(f"{name}: median {values['median']:.3f} ms (n={values['n']})")
    print(f"wall_seconds: {report['wall_seconds']:.3f}")


if __name__ == "__main__":
    main()
