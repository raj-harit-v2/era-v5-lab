"""B5 data-transfer correctness tests: pinned host memory, non-blocking H2D transfer,
prefetch idempotency, and FineWeb prefetch equivalence.

Verifies the existing B5 implementation in dataio/loader.py (no production code changes):
  test_host_batch_is_pinned_on_cuda                      (Test A) -- CUDA host batches are pinned
  test_next_batch_uses_non_blocking_transfer             (Test B) -- next_batch() requests non_blocking=True
  test_cpu_loader_does_not_pin_memory                    (Test C) -- CPU path never invokes pin_memory()
  test_repeated_prefetch_does_not_overwrite_staged_batch (Test D) -- prefetch() twice is idempotent
  test_fineweb_prefetch_on_off_batch_equivalence         (Test E) -- FineWeb prefetch ON/OFF yields identical batches

Additional prefetch coverage is provided by correctness-framework pair tests in
correctness/test_optimizer.py:
  @pair("data.prefetch")       -- 4 steps, prefetch=True vs prefetch=False, CPU/CUDA via device fixture
  @pair("data.prefetch.first") -- 4 steps, prefetch-before-next_batch ordering, CPU
Both pairs verify exact batch identity (integer token IDs, rel_err = 0.0).
"""
from __future__ import annotations

import json
import pytest
import torch
from unittest.mock import patch

from dataio.loader import Loader


class _StubTokenizer:
    """Stand-in for BrahmicTokenizer; synthetic batches need no tokenizer download."""
    def __init__(self, _path=None):
        self.vocab_size = 131072


def _make_loader(device, *, prefetch=False, batch_size=2, block_size=4, seed=0):
    """Real Loader using synthetic data and a stub tokenizer (no network or file I/O)."""
    with patch("dataio.loader.BrahmicTokenizer", _StubTokenizer):
        return Loader(source="synthetic", batch_size=batch_size, block_size=block_size,
                      device=device, vocab_size=131072, seed=seed, prefetch=prefetch)


# ---- Test A: pinned host memory -----------------------------------------------

@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_host_batch_is_pinned_on_cuda():
    """_host_batch() must return a pinned CPU tensor when the Loader device is CUDA.

    Exercises the path: self.pin = (device.type == "cuda") -> buf.pin_memory()
    (dataio/loader.py lines 37 and 83-84).
    """
    loader = _make_loader("cuda")
    buf = loader._host_batch()
    assert buf.device.type == "cpu", (
        "_host_batch() must keep the tensor on CPU; the transfer happens in next_batch()"
    )
    assert buf.is_pinned(), (
        "_host_batch() must call buf.pin_memory() when device is CUDA"
    )


# ---- Test B: non-blocking H2D transfer ----------------------------------------

def test_next_batch_uses_non_blocking_transfer(monkeypatch):
    """next_batch() must pass non_blocking=True for the [B, T+1] CPU host-batch transfer.

    Spies on torch.Tensor.to (restored automatically by pytest monkeypatch) and records
    the source shape, source device, destination argument, and non_blocking flag for every
    call made during next_batch().  The assertion then filters to the specific [B, T+1] CPU
    tensor that _host_batch() returns, so it cannot pass because of an unrelated transfer.
    Runs on CPU; CPU ignores non_blocking at runtime, but the argument must still be passed.
    """
    calls = []
    original_to = torch.Tensor.to

    def spy_to(self, *args, **kwargs):
        calls.append({
            "src_shape":  tuple(self.shape),
            "src_device": self.device.type,
            "dest":       str(args[0]) if args else str(kwargs.get("device", "")),
            "non_blocking": kwargs.get("non_blocking", False),
        })
        return original_to(self, *args, **kwargs)

    monkeypatch.setattr(torch.Tensor, "to", spy_to)

    loader = _make_loader("cpu")
    x, y = loader.next_batch()

    host_batch_shape = (loader.B, loader.T + 1)
    host_transfers = [
        c for c in calls
        if c["src_shape"] == host_batch_shape and c["src_device"] == "cpu"
    ]
    assert host_transfers, (
        f"No tensor.to() call found for the [{loader.B}, {loader.T + 1}] CPU host batch; "
        f"all recorded calls: {calls}"
    )
    assert host_transfers[0]["non_blocking"] is True, (
        f"The [{loader.B}, {loader.T + 1}] CPU host-batch transfer must use "
        f"non_blocking=True; got non_blocking={host_transfers[0]['non_blocking']!r}"
    )
    assert x.shape == (loader.B, loader.T), f"x shape: expected ({loader.B}, {loader.T})"
    assert y.shape == (loader.B, loader.T), f"y shape: expected ({loader.B}, {loader.T})"
    assert torch.equal(x[:, 1:], y[:, :-1]), (
        "y must equal x shifted forward by one token: y[b, t] == x[b, t+1]"
    )


# ---- Test C: CPU fallback -- no CUDA pinning ----------------------------------

def test_cpu_loader_does_not_pin_memory(monkeypatch):
    """Loader with device=cpu must not call pin_memory() and must return ordinary CPU tensors.

    Guards against an accidental removal of the `self.pin = device.type == "cuda"` guard
    (dataio/loader.py line 37) that controls whether _host_batch() pins the buffer.
    """
    def must_not_pin(self):
        raise AssertionError(
            "pin_memory() must not be called when Loader.device is CPU "
            "(self.pin is False for non-CUDA devices; dataio/loader.py line 37)"
        )

    monkeypatch.setattr(torch.Tensor, "pin_memory", must_not_pin)

    loader = _make_loader("cpu")
    x, y = loader.next_batch()

    assert x.device.type == "cpu", "x must remain on CPU for a CPU Loader"
    assert y.device.type == "cpu", "y must remain on CPU for a CPU Loader"
    assert x.shape == (loader.B, loader.T), f"x shape: expected ({loader.B}, {loader.T})"
    assert y.shape == (loader.B, loader.T), f"y shape: expected ({loader.B}, {loader.T})"


# ---- Test D: repeated-prefetch idempotency ------------------------------------

def test_repeated_prefetch_does_not_overwrite_staged_batch():
    """Calling prefetch() twice consecutively must be idempotent.

    The self._next is None guard (loader.py:63) prevents a second _host_batch()
    call when a batch is already staged.  Verified four ways:
      1. _host_batch() is called exactly once, not twice.
      2. The returned batch equals the single-prefetch reference.
      3. self._next is None after next_batch() consumes the staged batch.
      4. Subsequent next_batch() matches the reference, confirming the RNG was
         not advanced an extra time by the no-op second prefetch().
    """
    # Reference loader: single prefetch() -> next_batch()
    ref = _make_loader("cpu", prefetch=True, seed=7)
    ref.prefetch()
    x_ref, y_ref = ref.next_batch()

    # Test loader: double prefetch() -> next_batch(); wrap _host_batch to count calls
    loader = _make_loader("cpu", prefetch=True, seed=7)
    call_count = [0]
    original_host_batch = loader._host_batch     # bound method, captures loader as self

    def counting_host_batch():
        call_count[0] += 1
        return original_host_batch()

    loader._host_batch = counting_host_batch     # instance-level replacement

    loader.prefetch()                            # first call: must invoke _host_batch()
    assert call_count[0] == 1, (
        "first prefetch() must invoke _host_batch() exactly once"
    )

    loader.prefetch()                            # second call: self._next is not None -> no-op
    assert call_count[0] == 1, (
        "second prefetch() must not invoke _host_batch() when a batch is already staged"
    )

    x, y = loader.next_batch()

    assert torch.equal(x, x_ref), (
        "double prefetch must yield the same batch as single prefetch (same seed)"
    )
    assert torch.equal(y, y_ref), (
        "double prefetch must yield the same batch as single prefetch (same seed)"
    )
    assert loader._next is None, (
        "next_batch() must clear _next to None after consuming the staged batch"
    )

    # Subsequent next_batch() must also match: proves RNG was not advanced by the
    # no-op second prefetch() call.
    x_ref2, y_ref2 = ref.next_batch()
    x2, y2 = loader.next_batch()
    assert torch.equal(x2, x_ref2), (
        "subsequent batch must match reference — RNG must not have advanced during no-op prefetch()"
    )
    assert torch.equal(y2, y_ref2), (
        "subsequent batch must match reference — RNG must not have advanced during no-op prefetch()"
    )


# ---- Test E: FineWeb prefetch ON/OFF equivalence ------------------------------

def test_fineweb_prefetch_on_off_batch_equivalence(tmp_path):
    """FineWeb loader with prefetch enabled must yield identical batches to prefetch disabled.

    Creates a small deterministic FineWeb shard with known token IDs, then runs
    four steps comparing the prefetch=False and prefetch=True paths.  The bench
    call pattern (prefetch() called after next_batch()) is used so that the RNG
    advances identically in both paths.  Verifies batch equivalence, correct
    shifted-token relationship, expected shape, and vocabulary range.

    FineWeb-specific considerations exercised here but not by the existing
    data.prefetch pair tests (which use synthetic data):
      - shard memmap read and np.stack([ shard[s:s+T+1] ]) slicing path
      - rng.choice(shards) + rng.integers(starts) call pair per _host_batch()
      - uint32 -> int64 cast preserves token IDs through prefetch staging
    """
    from dataio.prepare_fineweb import write_shard
    from dataio.tokenizer import REVISION, SHA256, VOCAB_SIZE

    # Write a 50-token shard with known IDs in [1000, 1050) — all within vocabulary
    shard_ids = list(range(1000, 1050))
    write_shard(tmp_path / "fineweb_train_000001.bin", shard_ids)
    (tmp_path / "tokenizer.json.meta").write_text(json.dumps(
        {"revision": REVISION, "sha256": SHA256, "vocab_size": VOCAB_SIZE}
    ))

    batch_size, block_size, seed, n_steps = 2, 4, 42, 4

    def _make_fineweb_loader(prefetch):
        with patch("dataio.loader.BrahmicTokenizer", _StubTokenizer):
            return Loader(
                source="fineweb10b",
                batch_size=batch_size,
                block_size=block_size,
                device="cpu",
                data_dir=str(tmp_path),
                vocab_size=131072,
                seed=seed,
                prefetch=prefetch,
            )

    ref_loader  = _make_fineweb_loader(False)
    test_loader = _make_fineweb_loader(True)

    for step in range(n_steps):
        x_ref,  y_ref  = ref_loader.next_batch()
        x_test, y_test = test_loader.next_batch()
        test_loader.prefetch()                   # stage next batch (bench call pattern)

        assert torch.equal(x_ref, x_test), (
            f"step {step}: FineWeb x must be identical for prefetch OFF and ON"
        )
        assert torch.equal(y_ref, y_test), (
            f"step {step}: FineWeb y must be identical for prefetch OFF and ON"
        )
        assert x_ref.shape == (batch_size, block_size), (
            f"step {step}: x shape must be ({batch_size}, {block_size})"
        )
        assert y_ref.shape == (batch_size, block_size), (
            f"step {step}: y shape must be ({batch_size}, {block_size})"
        )
        assert torch.equal(x_ref[:, 1:], y_ref[:, :-1]), (
            f"step {step}: y must equal x shifted forward by one token"
        )
        assert int(x_ref.min()) >= 0 and int(x_ref.max()) < 131072, (
            f"step {step}: sampled token IDs must be within vocabulary [0, 131072)"
        )
