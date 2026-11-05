"""Named timing regions that cost nothing when timing is off.  The API below is a contract: do not change it.

    with region("block3.attn", level=2): ...      # a named piece of work
    x = mark(x, "block3")                         # backward boundary: grad reached x
    with phase("bwd.recompute"): ...              # prefix region names inside

Names become "<phase>:<name>". Levels: 1 phases, 2 per layer / big parts, 3 inside a layer. With no recorder,
region() returns one shared no-op context and mark() returns its input. Recorders live in perfkit/timer.py.

Recorder protocol:
    rec.max_level: int
    rec.region(full_name, level) -> context manager
    rec.point(name, level)       -> None      (called by point() and by mark() in backward)
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext

import torch

_NULL = nullcontext()
_REC = None    # active recorder or None
_PHASE = ""    # current phase prefix


def active():
    """The recorder in use, or None when timing is off."""
    return _REC


@contextmanager
def use_recorder(rec):
    """Send region / point / mark to rec inside the block."""
    global _REC
    prev, _REC = _REC, rec
    try:
        yield rec
    finally:
        _REC = prev


@contextmanager
def phase(name: str):
    """Prefix region names inside the block with `name:` (nothing when timing is off)."""
    global _PHASE
    if _REC is None:
        yield
        return
    prev, _PHASE = _PHASE, name
    try:
        yield
    finally:
        _PHASE = prev


def region(name: str, level: int = 2):
    """A timing context named <phase>:<name>; the shared no-op when timing is off or level > max_level."""
    rec = _REC
    if rec is None or level > rec.max_level:
        return _NULL
    return rec.region(f"{_PHASE}:{name}" if _PHASE else name, level)


def point(name: str, level: int = 1):
    """Record one instant (bench marks __bwd_start__ and __bwd_end__ with it)."""
    rec = _REC
    if rec is not None and level <= rec.max_level:
        rec.point(name, level)


def mark(x: torch.Tensor, name: str, level: int = 1) -> torch.Tensor:
    """Identity in forward; in backward, tells the recorder when the gradient reaches x."""
    rec = _REC
    if rec is None or level > rec.max_level or not x.requires_grad:
        return x
    return _Mark.apply(x, rec, name, level)


class _Mark(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, rec, name, level):
        ctx.rec, ctx.name, ctx.level = rec, name, level
        return x.view_as(x)                  # a new tensor, so autograd records this node

    @staticmethod
    def backward(ctx, g):
        ctx.rec.point(ctx.name, ctx.level)
        return g, None, None, None


# ------------------------------------------------------------------------------ recorders

# The recorders are written in perfkit/timer.py (EventRecorder: layer mode, ProfilerRecorder: trace mode),
# next to the timing code they share. Re-exported here so `from perfkit.regions import EventRecorder` keeps working.
from perfkit.timer import EventRecorder, ProfilerRecorder  # noqa: E402,F401
