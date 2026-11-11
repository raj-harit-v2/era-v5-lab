"""Build exact numeric window caches before starting a timed GPU run.

No text is logged or cached. Each spawned worker runs the unchanged, strict
Artifacts.encode check. Bounded work is returned in original document order.
"""

import argparse
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import multiprocessing
import os
import json
from pathlib import Path
import sys
import numpy as np

HARNESS = Path(__file__).resolve().parents[1] / "harness"
sys.path.insert(0, str(HARNESS))
from week2.artifacts import Artifacts
from week2.data import build_window_cache


def _initialize(tokenizer, byte_table):
    global _ARTIFACTS
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    _ARTIFACTS = Artifacts(tokenizer, byte_table)


def _encode_chunk(records):
    return [np.asarray(_ARTIFACTS.encode(record["text"]), dtype="<u4")
            for record in records]


def _chunks(records):
    chunk, size = [], 0
    for record in records:
        chunk.append(record)
        size += len(record["text"].encode("utf8"))
        if len(chunk) >= 128 or size >= 4 * 1024 * 1024:
            yield chunk
            chunk, size = [], 0
    if chunk:
        yield chunk


def _parallel_records(records, *, tokenizer, byte_table, workers):
    chunks = iter(_chunks(records))
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn"),
        initializer=_initialize, initargs=(tokenizer, byte_table),
    ) as pool:
        pending = deque()
        for _ in range(workers * 2):
            chunk = next(chunks, None)
            if chunk is None:
                break
            pending.append((chunk, pool.submit(_encode_chunk, chunk)))
        while pending:
            chunk, future = pending.popleft()
            yield from zip(chunk, future.result(), strict=True)
            chunk = next(chunks, None)
            if chunk is not None:
                pending.append((chunk, pool.submit(_encode_chunk, chunk)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--byte-table", type=Path, required=True)
    parser.add_argument("--seq-len", type=int, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--require-ids", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--progress-json", type=Path,
                        help="Atomic, text-free counts for a notebook monitor")
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be positive")
    # Explicit import path and bounded native threading also apply after spawn.
    os.environ["PYTHONPATH"] = str(HARNESS)
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    def report(info):
        line = json.dumps(info, sort_keys=True)
        print(line, flush=True)
        if args.progress_json:
            args.progress_json.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.progress_json.with_suffix(".tmp")
            temporary.write_text(line + "\n", encoding="utf8")
            temporary.replace(args.progress_json)

    artifacts = Artifacts(args.tokenizer, args.byte_table)
    destination = build_window_cache(
        args.input, artifacts, args.seq_len, args.cache_dir,
        require_ids=args.require_ids, sources_path=args.sources,
        encode_records=partial(_parallel_records, tokenizer=str(args.tokenizer),
                               byte_table=str(args.byte_table), workers=args.workers),
        progress=report,
    )
    print(f"Verified numeric window cache: {destination}", flush=True)


if __name__ == "__main__":
    main()
