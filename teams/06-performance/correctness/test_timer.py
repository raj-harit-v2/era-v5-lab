"""perfkit/timer.py and perfkit/regions.py: the off switch costs nothing, and times are recorded correctly.

  1. Off switch: with no recorder, region() is one shared no-op, mark() returns its input, nothing is recorded
     (checked by identity and a spy recorder, with a loose time bound).
  2. Recording: a known sleep, nesting, max_level, phase prefixes, point order, stats() on a known list.
  3. CUDA only: no host sync while regions are recorded.
  4. StepTimer and EventPool bookkeeping, reset() rules, cumulative counters.
"""
from __future__ import annotations

import time
from contextlib import nullcontext

import pytest
import torch

from perfkit import regions
from perfkit.timer import EventPool, EventRecorder, StepTimer, stats

CPU = torch.device("cpu")


class SpyRecorder:
    """A recorder that counts every call. If the off switch works it is never called."""

    def __init__(self, max_level=3):
        self.max_level = max_level
        self.calls = 0

    def region(self, name, level=2):
        self.calls += 1
        return nullcontext()

    def point(self, name, level=1):
        self.calls += 1


# ------------------------------------------------------------------------------ 1. the off switch

def test_region_is_one_shared_noop_when_no_recorder():
    assert regions.active() is None
    # Same object every time: nothing is allocated per call, so there is nothing to cost time.
    a, b = regions.region("a", 1), regions.region("b", 3)
    assert a is b and type(a) is nullcontext


def test_mark_returns_its_input_and_adds_no_autograd_node():
    x = torch.randn(3, requires_grad=True)
    y = regions.mark(x, "block0")
    assert y is x                        # identity: no view, no copy
    assert y.grad_fn is None             # no _Mark node was added to the backward graph


def test_phase_and_point_do_nothing_without_a_recorder():
    with regions.phase("fwd"):
        # phase() only sets the name prefix when a recorder is active, so nothing changes here.
        assert regions._PHASE == ""
        regions.point("anything", 1)     # must not raise and must not record anything


def test_a_spy_recorder_is_never_called_after_it_is_removed():
    spy = SpyRecorder()
    with regions.use_recorder(spy):
        pass                             # installed, then removed again
    assert regions.active() is None
    for _ in range(1000):
        with regions.region("x", 1), regions.phase("fwd"):
            regions.point("p", 1)
        regions.mark(torch.zeros(1, requires_grad=True), "m")
    assert spy.calls == 0


def test_levels_above_max_level_are_not_recorded():
    spy = SpyRecorder(max_level=1)       # a recorder asked for phases only
    with regions.use_recorder(spy):
        with regions.region("inside_a_layer", 3), regions.region("a_layer", 2):
            regions.point("deep", 2)
        assert spy.calls == 0            # level 2 and 3 are above max_level=1: ignored
        with regions.region("phase", 1):
            pass
        assert spy.calls == 1            # level 1 is recorded


def test_off_switch_costs_microseconds_not_milliseconds():
    n = 20_000
    t0 = time.perf_counter()
    for _ in range(n):
        with regions.region("x", 2):
            pass
    per_call_us = (time.perf_counter() - t0) / n * 1e6
    # A no-op `with` is well under 1 us. 50 us is a loose bound that only fails if the off switch starts
    # doing real work (for example creating events or reading the clock).
    assert per_call_us < 50, f"{per_call_us:.1f} us per region() call with no recorder"


# ------------------------------------------------------------------------------ 2. times are recorded

def test_a_known_sleep_is_recorded_as_about_that_many_ms():
    rec = EventRecorder(CPU, max_level=2)
    with regions.use_recorder(rec):
        with regions.region("work", 2):
            time.sleep(0.03)
    spans, points = rec.collect()
    (name, level, ms), = spans
    assert name == "work" and level == 2 and points == []
    # sleep(0.03) lasts at least 30 ms; the upper bound is generous so a busy machine does not fail it.
    assert 25 <= ms < 250, ms


def test_nested_regions_nest_and_phase_prefixes_the_name():
    rec = EventRecorder(CPU, max_level=3)
    with regions.use_recorder(rec):
        with regions.phase("fwd"):
            with regions.region("block0", 2):
                time.sleep(0.01)
                with regions.region("block0.attn", 3):
                    time.sleep(0.02)
    spans, _ = rec.collect()
    ms = {n: t for n, _, t in spans}
    assert set(ms) == {"fwd:block0", "fwd:block0.attn"}      # "<phase>:<name>"
    assert ms["fwd:block0"] >= ms["fwd:block0.attn"] >= 15   # the outer region contains the inner one


def test_recorder_ignores_levels_above_its_max_level():
    rec = EventRecorder(CPU, max_level=2)
    with regions.use_recorder(rec):
        with regions.region("kept", 2), regions.region("dropped", 3):
            pass
    spans, _ = rec.collect()
    assert [n for n, _, _ in spans] == ["kept"]


def test_points_keep_the_order_they_happened_in():
    rec = EventRecorder(CPU, max_level=2)
    with regions.use_recorder(rec):
        regions.point("first", 1)
        time.sleep(0.01)
        regions.point("second", 1)
    _, points = rec.collect()
    assert [n for n, _, _ in points] == ["first", "second"]
    first, second = points[0][2], points[1][2]
    assert second.ms_since(first) >= 8                       # Clock.ms_since: time between two points


def test_collect_twice_gives_the_same_answer():
    rec = EventRecorder(CPU, max_level=2)
    with regions.use_recorder(rec), regions.region("x", 2):
        pass
    assert rec.collect() is rec.collect()


def test_step_timer_measures_each_step_and_guards_misuse():
    t = StepTimer(CPU)
    for _ in range(3):
        with t.step():
            time.sleep(0.02)
    ms = t.times_ms()
    assert len(t) == 3 and len(ms) == 3
    assert all(15 <= m < 250 for m in ms), ms
    with pytest.raises(RuntimeError):
        t.stop()                                             # stop() without start()
    t.start()
    with pytest.raises(RuntimeError):
        t.start()                                            # start() twice


def test_stats_of_a_known_list():
    s = stats([1, 2, 3, 4, 5])
    assert s["median"] == 3 and s["min"] == 1 and s["max"] == 5 and s["n"] == 5
    assert s["p10"] == pytest.approx(1.4) and s["p90"] == pytest.approx(4.6)
    assert s["iqr"] == pytest.approx(2.0)                    # p75 - p25 = 4 - 2
    assert s["spread_pct"] == pytest.approx((4.6 - 1.4) / 3 * 100)


def test_stats_has_mean_and_std():
    # The median stays the number we gate on; mean and std are extra keys.
    s = stats([2, 4, 4, 4, 5, 5, 7, 9])
    assert s["mean"] == pytest.approx(5.0)
    assert s["std"] == pytest.approx(2.13809, rel=1e-4)      # sample std (n - 1): sqrt(32 / 7)
    assert stats([7])["std"] == 0.0                          # one value has no spread
    # One slow step moves the mean but not the median: that is why the 5% check uses the median.
    spiky = stats([10.0] * 9 + [100.0])
    assert spiky["median"] == 10.0 and spiky["mean"] == pytest.approx(19.0)


def test_stats_of_an_empty_list_has_every_key():
    s = stats([])
    assert s["n"] == 0 and s["median"] is None and s["mean"] is None and s["std"] is None


# ------------------------------------------------------------------------------ 3. deferred sync (CUDA)

@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs a CUDA GPU")
def test_recording_regions_does_not_sync_the_host():
    dev = torch.device("cuda")
    a = torch.randn(512, 512, device=dev)
    pool = EventPool()
    pool.reserve(64)                                         # events are made before the timed part
    rec = EventRecorder(dev, max_level=2, pool=pool)
    torch.cuda.synchronize()
    # "error" turns any implicit host sync (.item(), .cpu(), synchronize()) into an exception.
    torch.cuda.set_sync_debug_mode("error")
    try:
        with regions.use_recorder(rec):
            with regions.region("matmul", 2):
                b = a @ a
            regions.point("done", 1)
    finally:
        torch.cuda.set_sync_debug_mode("default")
    assert rec.n_events() > 0
    spans, points = rec.collect()                            # the one sync happens here, after the step
    assert len(spans) == 1 and spans[0][2] > 0               # a 512x512 matmul takes more than 0 ms
    assert pool.created == 64                                # and no event was created inside the step
    assert b.shape == (512, 512)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs a CUDA GPU")
def test_cuda_step_timer_agrees_with_a_synchronized_wall_clock():
    dev = torch.device("cuda")
    a = torch.randn(2048, 2048, device=dev)
    for _ in range(3):
        a @ a                                                # warm up the kernels
    torch.cuda.synchronize()
    t = StepTimer(dev)
    t0 = time.perf_counter()
    with t.step():
        for _ in range(20):
            a @ a
    torch.cuda.synchronize()
    wall_ms = (time.perf_counter() - t0) * 1e3
    (event_ms,) = t.times_ms()
    # The event time covers the GPU work only; the wall clock adds launch and sync cost. They must be the
    # same order of magnitude, and the event time cannot exceed the wall time by more than a little.
    assert 0 < event_ms <= wall_ms * 1.5 + 5


# ------------------------------------------------------------------------------ event-preallocation regression tests

def test_step_timer_expected_steps_validates_input():
    with pytest.raises(ValueError):
        StepTimer(CPU, expected_steps=-1)
    t = StepTimer(CPU, expected_steps=2)
    assert t.kind == "wall" and t.events_created_during_steps == 0


def test_cuda_event_preallocation_and_exhaustion(monkeypatch):
    # Fake CUDA events so this regression test also runs on a CPU-only CI worker.
    class FakeEvent:
        created = 0

        def __init__(self, enable_timing=False):
            assert enable_timing
            FakeEvent.created += 1

        def record(self):
            pass

        def query(self):
            return True

        def synchronize(self):
            pass

        def elapsed_time(self, other):
            return 1.0

    monkeypatch.setattr(torch.cuda, "Event", FakeEvent)
    t = StepTimer(torch.device("cuda"), expected_steps=2)
    assert FakeEvent.created == 4
    for _ in range(2):
        t.start()
        t.stop()
    assert FakeEvent.created == 4
    assert t.events_created_during_steps == 0
    assert t.times_ms() == [1.0, 1.0]
    t.start()
    t.stop()
    assert FakeEvent.created == 6
    assert t.events_created_during_steps == 2
    t.reset()
    assert len(t) == 0
    t.start()
    t.stop()
    assert FakeEvent.created == 6


# ------------------------------------------------------------------------------ reset follow-up regressions

def test_step_timer_reset_rejects_open_step_on_cpu():
    t = StepTimer(CPU, expected_steps=1)
    t.start()
    with pytest.raises(RuntimeError, match="open step"):
        t.reset()
    t.stop()
    t.reset()
    assert len(t) == 0


def test_cuda_reset_synchronizes_before_event_reuse(monkeypatch):
    # Fake CUDA events exercise synchronization and reuse on a CPU-only Mac.
    made = []

    class FakeEvent:
        def __init__(self, enable_timing=False):
            assert enable_timing
            made.append(self)
            self.synced = False

        def record(self):
            pass

        def synchronize(self):
            self.synced = True

        def query(self):
            return self.synced

        def elapsed_time(self, other):
            assert other.synced, "event timing must be synchronized before reuse"
            return 1.0

    monkeypatch.setattr(torch.cuda, "Event", FakeEvent)
    t = StepTimer(torch.device("cuda"), expected_steps=1)
    assert len(made) == 2
    t.start()
    t.stop()
    t.reset()
    assert len(t) == 0 and any(ev.synced for ev in made)
    t.start()
    t.stop()
    assert len(made) == 2
    assert t.events_created_during_steps == 0


# PR24 review regression: cumulative fallback allocation count
def test_cuda_counter_remains_cumulative_across_reset(monkeypatch):
    class FakeEvent:
        def __init__(self, enable_timing=False):
            assert enable_timing
        def record(self): pass
        def synchronize(self): pass
        def query(self): return True
        def elapsed_time(self, other): return 1.0
    monkeypatch.setattr(torch.cuda, "Event", FakeEvent)
    timer = StepTimer(torch.device("cuda"), expected_steps=1)
    for _ in range(2):
        timer.start()
        timer.stop()
    assert timer.events_created_during_steps == 2
    timer.reset()
    assert timer.events_created_during_steps == 2
    timer.start()
    timer.stop()
    assert timer.events_created_during_steps == 2
