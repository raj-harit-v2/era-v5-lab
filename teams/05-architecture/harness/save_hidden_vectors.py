"""Save final hidden vectors of a finished week-2 run, with the true next-token ids.

Team 4 asked for this to re-run its tau sweep on vectors from a real run (KE2 open risk 2).
TSAI supports it.

The vectors are what ``LanguageModel.hidden`` returns at scored positions: the output of the
last norm, which is the input of the dense untied head. Their width is the model width
(``n_embd``), not the KE2 code width (256 * P). No projection into code space is applied here,
because the output head is dense and TSAI has not chosen a KE2 output head.

Output, one ``.npz``:
    vectors   (N, n_embd) float32
    true_ids  (N,) int64, the token the model had to predict at that position
    plus the identities of the run, the tokenizer, the table and the text.

Usage:
    python teams/05-architecture/harness/save_hidden_vectors.py --run OUT_DIR_OF_THE_RUN
        --tokenizer TOKENIZER_JSON --byte-table RAW_TABLE_NPZ --heldout-data HELDOUT_JSONL
        --out hidden_vectors.npz [--rows 4096] [--seed 0] [--device cpu|cuda]

``--run`` is the output folder of ``train_week2.py``. It must hold ``manifest.json`` and
``checkpoint.pt``. Only load a checkpoint that your own harness run wrote.
"""

import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn.utils.rnn import pad_sequence

from train_week2 import model_hash
from week2.artifacts import Artifacts, sha256
from week2.data import DocumentWindows
from week2.model import LanguageModel

# The same bounds as week2.evaluation: padded tokens per batch, rows per head call.
BATCH_TOKENS = 16_384
HEAD_TOKENS = 512


def _batches(windows, order, max_batch_tokens):
    """Yield lists of window indices whose padded size stays inside the token budget."""
    batch, width = [], 0
    for i in order:
        size = len(windows[i][1])
        if size > max_batch_tokens:
            raise ValueError("Window exceeds the token budget")
        if batch and (len(batch) + 1) * max(width, size) > max_batch_tokens:
            yield batch
            batch, width = [], 0
        batch.append(int(i))
        width = max(width, size)
    if batch:
        yield batch


@torch.no_grad()
def collect(
    model,
    dataset,
    rows,
    seed,
    device,
    autocast_context=nullcontext,
    max_batch_tokens=BATCH_TOKENS,
):
    """Return (vectors, true_ids, dense head top-1 hits) for ``rows`` scored positions.

    Windows are visited in an order fixed by ``seed``. Every scored position of a visited window
    is taken, in row order, until ``rows`` positions are held. Nothing is taken from padding.
    """
    if rows <= 0:
        raise ValueError("rows must be positive")
    training = model.training
    model.eval()
    order = np.random.default_rng(seed).permutation(len(dataset.windows))
    vectors, ids, hits, held = [], [], [], 0
    try:
        for indices in _batches(dataset.windows, order, max_batch_tokens):
            picked = [dataset.windows[i] for i in indices]
            x = pad_sequence(
                [torch.as_tensor(row[0], dtype=torch.long) for row in picked],
                batch_first=True,
                padding_value=dataset.pad_id,
            ).to(device)
            y = pad_sequence(
                [torch.as_tensor(row[1], dtype=torch.long) for row in picked],
                batch_first=True,
                padding_value=-100,
            ).to(device)
            valid = y != -100
            with autocast_context():
                hidden = model.hidden(x, valid)[valid][: rows - held]
                targets = y[valid][: rows - held]
                top1 = torch.cat(
                    [model.head(h).argmax(-1) for h in hidden.split(HEAD_TOKENS)]
                )
            vectors.append(hidden.float().cpu())
            ids.append(targets.cpu())
            hits.append((top1 == targets).cpu())
            held += len(targets)
            if held >= rows:
                break
    finally:
        model.train(training)
    vectors = torch.cat(vectors).numpy()
    ids = torch.cat(ids).numpy().astype(np.int64)
    hits = torch.cat(hits).numpy()
    if not np.isfinite(vectors).all():
        raise ValueError("Nonfinite hidden vector")
    if not vectors.any(axis=1).all():
        raise ValueError("All-zero hidden vector")
    return vectors, ids, hits


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    for name in ["run", "tokenizer", "byte-table", "heldout-data", "out"]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--rows", type=int, default=4096)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = p.parse_args()
    started = time.perf_counter()
    if args.out.exists():
        p.error("Output file exists; name a new file")
    manifest = json.loads((args.run / "manifest.json").read_text(encoding="utf8"))
    cfg = manifest["config"]
    artifacts = Artifacts(args.tokenizer, args.byte_table)
    if artifacts.identity() != manifest["artifacts"]:
        p.error("Tokenizer or byte table differs from the ones the run used")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        p.error("CUDA unavailable")
    checkpoint = torch.load(
        args.run / "checkpoint.pt", map_location=device, weights_only=False
    )
    if checkpoint["identity_sha256"] != manifest["identity_sha256"]:
        p.error("checkpoint.pt and manifest.json come from different runs")
    model = LanguageModel(cfg["model"], artifacts.bytes, artifacts.lengths).to(device)
    model.load_state_dict(checkpoint["model"])
    weights = model_hash(model)
    summary_path = args.run / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf8"))
        if summary["steps"] == checkpoint["step"] and summary[
            "final_model_sha256"
        ] != weights:
            p.error("Loaded weights differ from final_model_sha256 in summary.json")
    heldout_hash = sha256(args.heldout_data)
    dataset = DocumentWindows(args.heldout_data, artifacts, cfg["model"]["block_size"])
    bf16 = device.type == "cuda" and cfg["run"]["dtype"] == "bf16"

    def amp():
        return (
            torch.autocast(device_type="cuda", dtype=torch.bfloat16)
            if bf16
            else nullcontext()
        )

    vectors, true_ids, hits = collect(model, dataset, args.rows, args.seed, device, amp)
    if true_ids.min() < 0 or true_ids.max() >= cfg["model"]["vocab_size"]:
        p.error("Target id outside the vocabulary")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        vectors=vectors,
        true_ids=true_ids,
        kind="hidden_before_dense_head",
        n_embd=cfg["model"]["n_embd"],
        ke2_code_dim=256 * artifacts.pos_dim,
        step=checkpoint["step"],
        run_status=manifest["status"],
        run_identity_sha256=manifest["identity_sha256"],
        model_sha256=weights,
        tokenizer_sha256=artifacts.tokenizer_sha,
        table_content_sha256=artifacts.table_content_sha,
        text_sha256=heldout_hash,
        text_is_the_run_heldout=heldout_hash == manifest["heldout_sha256"],
        dense_head_top1=float(hits.mean()),
        autocast="bf16" if bf16 else "none",
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "out": str(args.out),
                "vectors": list(vectors.shape),
                "true_ids": list(true_ids.shape),
                "step": checkpoint["step"],
                "run_status": manifest["status"],
                "model_sha256": weights,
                "dense_head_top1": round(float(hits.mean()), 6),
                "wall_seconds": round(time.perf_counter() - started, 3),
            }
        )
    )


if __name__ == "__main__":
    main()
