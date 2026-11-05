"""Retokenize raw FineWeb sample-10BT with the pinned GitHub Brahmic artifact.

uint32 stores all 131,072 IDs. The first shard is validation, followed by train.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

from dataio.loader import DEFAULT_DIR, MAGIC, VERSION
from dataio.tokenizer import BrahmicTokenizer, REVISION, SHA256, VOCAB_SIZE


def write_shard(path, tokens):
    """One shard: a 256 x int32 header (magic, version, count), then the tokens as uint32."""
    tokens = np.asarray(tokens, dtype=np.int64)
    if tokens.ndim != 1 or not len(tokens) or (tokens < 0).any() or (tokens >= VOCAB_SIZE).any():
        raise ValueError("Expected nonempty Brahmic token IDs in [0, 131072)")
    header = np.zeros(256, dtype="<i4")
    header[:3] = [MAGIC, VERSION, len(tokens)]
    with Path(path).open("wb") as f:
        header.tofile(f)
        tokens.astype("<u4").tofile(f)


def prepare(out=DEFAULT_DIR, train_shards=1, tokens_per_shard=1_000_000, tokenizer_path=None):
    """Stream FineWeb, encode it, write val + train_shards shards, then the metadata file that marks them complete."""
    from datasets import load_dataset
    if train_shards < 1 or not 0 < tokens_per_shard < 2**31:
        raise ValueError("Need train_shards >= 1 and 0 < tokens_per_shard < 2**31")
    tokenizer = BrahmicTokenizer(tokenizer_path)
    out = Path(out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.glob("fineweb_*.bin")):
        raise FileExistsError(f"{out} already contains shards; choose a fresh --out directory")
    meta = {"revision": REVISION, "sha256": SHA256, "vocab_size": tokenizer.vocab_size}
    docs = load_dataset("HuggingFaceFW/fineweb", name="sample-10BT", split="train", streaming=True)
    eos = tokenizer.spec["model"]["vocab"]["<|end_of_text|>"]
    pending, shard = [], 0
    for doc in docs:
        pending.extend(tokenizer.encode(doc["text"]) + [eos])     # documents joined by end-of-text
        while len(pending) >= tokens_per_shard:
            split = "val" if shard == 0 else "train"
            path = out / f"fineweb_{split}_{shard:06d}.bin"
            write_shard(path, pending[:tokens_per_shard])
            del pending[:tokens_per_shard]
            print(path)
            shard += 1
            if shard > train_shards:
                # Publish metadata only when the requested dataset is complete.
                (out / "tokenizer.json.meta").write_text(json.dumps(meta))
                return
    raise RuntimeError("Raw FineWeb stream exhausted before requested shards were prepared")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_DIR)
    ap.add_argument("--train-shards", type=int, default=1)
    ap.add_argument("--tokens-per-shard", type=int, default=1_000_000)
    ap.add_argument("--tokenizer-path", help="tokenizer.json in a checkout of the source repo")
    a = ap.parse_args()
    prepare(a.out, a.train_shards, a.tokens_per_shard, a.tokenizer_path)
    # Skip interpreter teardown: pyarrow's global ThreadPool destructor (pulled in by datasets streaming)
    # can deadlock in exit() and hang the process after every shard is already written.
    sys.stdout.flush()
    os._exit(0)
