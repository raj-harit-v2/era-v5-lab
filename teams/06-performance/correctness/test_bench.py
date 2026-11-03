"""perfkit/bench.py: the harness runs end to end, writes a valid run JSON, and follows the Instructor's rules.

Everything runs on the CPU with a tiny model and a fake Loader, so the tests need no GPU, no data download and no
network (the real Loader fetches the pinned BrahmicTokenizer-131K artifact). The fake Loader has the same
constructor and attributes as dataio.loader.Loader.

  * build: the Loader gets data.tokenizer_path; dtype fallbacks (B3); the LR-schedule note.
  * run metadata: tokenizer revision and sha256, vocab size (rule 1a).
  * rule_checks: dirty tree, wrong vocabulary (1a), level < 3 (3a), checkpoint / comm not measured (3b; comm
    only for MoE models).
  * quick_compare: the 5% check on the whole step and every part at level <= gate_level; refuses runs with a
    different model, optimizer, compile, grad_clip or data source; a part only one run has is MISSING.
  * checkpoint: tied weights are copied to the CPU once.
  * write_run / _finite: unique file names, NaN and inf become null.
  * main, for the reversible and the plain stack: clean + layer + checkpoint run, validate_run returns [],
    the parts are there and add up, exit codes 0 and 2.
  * quick_compare also accepts an A/B of optim.muon_impl or model.moe.dispatch, and gates checkpoint save and
    the all-to-all when both runs have them.
  * throttle warnings: an idle GPU is not flagged; slowdown reasons are named; the SM clock is the fallback.
  * --repeat: every run in a child process, one JSON per run, PASS / exit 2, a killed run stops the repeat.
  * trace: kernels counted (not annotations); with layer mode, one small trace per slowest part.
  * CUDA timing-event counters (clean, layer and its inner pass, comm) in the JSON, and their warnings.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import torch

from models.config import load_config, model_config
from models.ke1 import token_bytes_random
from perfkit import bench
from perfkit.report import compare_lines
from perfkit.schema import example_run, validate_run

ROOT = Path(__file__).resolve().parents[1]
TINY = ROOT / "configs" / "tiny_cpu.yaml"
VOCAB = 512
SEEN = {}


class FakeLoader:
    """Same constructor and attributes as dataio.loader.Loader, random token ids, no tokenizer download."""

    def __init__(self, source, batch_size, block_size, device, data_dir=None, vocab_size=VOCAB, seed=0,
                 split="train", tokenizer_path=None, prefetch=False):
        SEEN["tokenizer_path"] = tokenizer_path
        SEEN["source"] = source
        self.B, self.T, self.source, self.vocab_size = batch_size, block_size, source, vocab_size
        self.device = torch.device(device)
        self.g = torch.Generator().manual_seed(seed)
        self.prefetch_enabled = prefetch

    def prefetch(self):
        pass

    def next_batch(self):
        buf = torch.randint(0, self.vocab_size, (self.B, self.T + 1), generator=self.g)
        return buf[:, :-1].contiguous(), buf[:, 1:].contiguous()

    def token_bytes(self, max_pos):
        return token_bytes_random(self.vocab_size, max_pos)


@pytest.fixture(autouse=True)
def fake_loader(monkeypatch, tmp_path):
    SEEN.clear()
    monkeypatch.setattr(bench, "Loader", FakeLoader)
    monkeypatch.setattr(bench, "CACHE", tmp_path / "cache")


# The harness tests time a small model on random tokens, whatever base.yaml selects: KE1 (random byte table, so no
# dependence on G4's 131072-row KE2 table) and MoE (its regions and the rule 3b comm check are what they test).
# The model itself is tested in test_model.py on base.yaml.
HARNESS = ["data.source=synthetic", f"model.vocab_size={VOCAB}", "model.embedding=ke1", "model.ffn=moe"]


def tiny_cfg(*overrides):
    return load_config(TINY, [*HARNESS, *overrides])


# ------------------------------------------------------------------------------ build

def test_build_passes_tokenizer_path_to_loader():
    cfg = tiny_cfg("data.tokenizer_path=some/tokenizer.json")
    s = bench.build(cfg, torch.device("cpu"))
    assert SEEN["tokenizer_path"] == "some/tokenizer.json"
    assert s.loader.vocab_size == VOCAB and s.mcfg.vocab_size == VOCAB


def test_build_notes_a_schedule_it_ignores():
    s = bench.build(tiny_cfg("optim.schedule=cosine"), torch.device("cpu"))
    assert any("optim.schedule=cosine" in n for n in s.notes)
    assert not any("schedule" in n for n in bench.build(tiny_cfg(), torch.device("cpu")).notes)


def test_choose_dtype_fallbacks(monkeypatch):
    notes = []
    assert bench.choose_dtype("fp16", torch.device("cpu"), notes) == "bf16"          # no fp16 autocast on CPU
    assert notes and "bf16" in notes[0]

    monkeypatch.setattr(bench, "native_bf16", lambda: False)                       # T4 / P100 / V100
    notes = []
    assert bench.choose_dtype("bf16", torch.device("cuda"), notes) == "fp16"
    assert "fp16 + GradScaler" in notes[0]
    monkeypatch.setattr(bench, "native_bf16", lambda: True)
    assert bench.choose_dtype("bf16", torch.device("cuda"), []) == "bf16"
    assert bench.choose_dtype("fp32", torch.device("cpu"), []) == "fp32"
    with pytest.raises(ValueError):
        bench.choose_dtype("fp8", torch.device("cpu"), [])


def test_batch_size_comes_from_the_config_only(monkeypatch):
    for native in (True, False):                                                   # A100 or T4: same B
        monkeypatch.setattr(bench, "native_bf16", lambda: native)
        assert bench.resolve_batch(16) == 16
    for bad in ("auto", 0, -1, 2.5, True, None):
        with pytest.raises(SystemExit, match="run.batch_size"):
            bench.resolve_batch(bad)


def test_build_uses_the_config_batch():
    s = bench.build(tiny_cfg("run.batch_size=3"), torch.device("cpu"))
    assert s.cfg["run"]["batch_size"] == 3 == s.loader.B


def test_bench_constants_are_config_keys():
    b = load_config(ROOT / "configs" / "base.yaml")["bench"]
    assert {"layer_warmup", "comm_reps", "peak_tflops", "ckpt_repeats", "trace_steps"} <= set(b)
    a, ov = bench.parse(["--config", "x.yaml", "--peak-tflops", "100"])
    assert "bench.peak_tflops=100.0" in ov


def test_default_config_is_base_yaml():
    a, _ = bench.parse([])
    assert Path(a.config) == ROOT / "configs" / "base.yaml"


def test_config_is_strict(tmp_path):
    """The YAML is the only source: a duplicate key, an override of a key that does not exist, or a model
    field missing from the YAML is an error, never a silent default."""
    dup = tmp_path / "dup.yaml"
    dup.write_text("inherit: " + str(ROOT / "configs" / "base.yaml") + "\nrun: {batch_size: 8, batch_size: 16}\n")
    with pytest.raises(ValueError, match="duplicate key 'batch_size'"):
        load_config(dup)
    for typo in ("run.batchsize=16", "runn.batch_size=16"):
        with pytest.raises(KeyError, match="has no"):
            load_config(ROOT / "configs" / "base.yaml", [typo])
    cfg = load_config(ROOT / "configs" / "base.yaml")
    del cfg["model"]["block_size"]
    with pytest.raises(KeyError, match="block_size"):
        model_config(cfg)


def test_pick_device_cpu_and_missing_cuda(monkeypatch):
    assert bench.pick_device("cpu").type == "cpu"
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(SystemExit):
        bench.pick_device("cuda")


# ------------------------------------------------------------------------------ metadata (rule 1a)

def test_run_metadata_records_the_tokenizer():
    s = bench.build(tiny_cfg(), torch.device("cpu"))
    meta = bench.run_metadata(s, "configs/tiny_cpu.yaml", [], "t")
    assert meta["tokenizer"]["vocab_size"] == VOCAB
    assert meta["tokenizer"]["revision"] == bench.TOKENIZER_REVISION
    assert meta["tokenizer"]["sha256"] == bench.TOKENIZER_SHA256
    assert meta["vocab_size"] == VOCAB and meta["lr_schedule"] == "constant"
    assert meta["batch_size"] == s.loader.B and meta["seq_len"] == s.loader.T
    assert meta["run_id"] and meta["node_id"]
    auto_ids = {meta["run_id"], bench.run_metadata(s, "configs/tiny_cpu.yaml", [], "t")["run_id"]}
    assert len(auto_ids) == 2 and all(len(run_id) == 32 for run_id in auto_ids)


def test_run_id_and_node_id_can_be_set_for_g8_handover():
    s = bench.build(tiny_cfg(), torch.device("cpu"))
    meta = bench.run_metadata(s, "configs/tiny_cpu.yaml", [], "t", run_id="shared-exp", node_id="node-a")
    assert meta["run_id"] == "shared-exp"
    assert meta["node_id"] == "node-a"
    peer = bench.run_metadata(s, "configs/tiny_cpu.yaml", [], "peer", run_id="shared-exp", node_id="node-b")
    assert peer["run_id"] == meta["run_id"] and peer["node_id"] != meta["node_id"]


def test_memory_summary_names_the_gpu_and_unit():
    record = bench.memory_with_identity(
        {"peak_allocated_gb": 12.5, "peak_reserved_gb": 16.0},
        {"gpu": "Example GPU", "gpu_index": 1, "gpu_uuid": "GPU-example",
         "gpu_pci_bus_id": "00000000:02:00.0"},
    )
    assert record == {
        "peak_allocated_gb": 12.5, "peak_reserved_gb": 16.0, "unit": "GiB",
        "gpu": {"name": "Example GPU", "index": 1, "uuid": "GPU-example",
                "pci_bus_id": "00000000:02:00.0"},
    }
    assert bench.memory_with_identity(None, {}) is None
    identified = example_run()
    assert validate_run(identified) == []
    identified["memory"]["unit"] = "GB"
    assert "memory.unit must be 'GiB'" in validate_run(identified)


def _checked_run(**meta):
    run = example_run()
    run["meta"].update({"data_source": "synthetic", "vocab_size": bench.BRAHMIC_VOCAB, "dirty": False,
                        "commit": "abc", "device": "cuda",
                        "tokenizer": {"vocab_size": bench.BRAHMIC_VOCAB}, **meta})
    return run


def _cfg(level=3, ffn="moe"):
    return {"bench": {"level": level}, "run": {"compile": False}, "model": {"ffn": ffn}, "report": {"gate_level": 2, "tol_pct": 5.0, "abs_tol_ms": 0.05,
                                                                                  "min_compare_steps": 100}}


def test_rule_checks_clean_run_has_no_warnings():
    run = _checked_run()
    for r in run["layer"]["regions"].values():
        r["spread_pct"] = 1.0
    assert bench.rule_checks(run, ["clean", "layer", "checkpoint", "comm"], _cfg()) == []


def test_rule_checks_flag_each_rule():
    run = _checked_run(dirty=True, commit=None, vocab_size=50304, tokenizer={"vocab_size": 50304})
    for r in run["layer"]["regions"].values():
        r["spread_pct"] = 1.0
    out = "\n".join(bench.rule_checks(run, ["clean", "layer"], _cfg(level=2)))
    assert "uncommitted changes" in out
    assert "no commit ID" in out
    assert "rule 1a" in out and "50304" in out                # wrong vocabulary
    assert "rule 3a" in out                                   # parts inside a block not timed
    assert "rule 3b" in out and "checkpoint and comm" in out  # not measured


def test_rule_checks_comm_only_for_moe_models():
    run = _checked_run()
    for r in run["layer"]["regions"].values():
        r["spread_pct"] = 1.0
    out = "\n".join(bench.rule_checks(run, ["clean", "layer", "checkpoint"], _cfg(ffn="mlp")))
    assert "rule 3b" not in out                               # a dense model has no all-to-all
    out = "\n".join(bench.rule_checks(run, ["clean", "layer", "checkpoint"], _cfg(ffn="moe")))
    assert "rule 3b" in out and "comm" in out


_BUSY = {"temperature.gpu": 50.0, "clocks.sm": 1410.0, "clocks.max.sm": 1410.0}


def test_throttle_warning_ignores_an_idle_gpu():
    idle = {**_BUSY, "clocks.sm": 1095.0, "throttle_reasons": 0x1}               # GpuIdle: the Colab A100 case
    assert bench.throttle_warnings(idle, idle) == []
    assert bench.throttle_warnings(None, None) == []                             # CPU run


def test_throttle_warning_names_the_slowdown():
    out = bench.throttle_warnings({**_BUSY, "throttle_reasons": 0x4 | 0x40}, None)
    assert len(out) == 1 and "SwPowerCap" in out[0] and "HwThermalSlowdown" in out[0]
    assert "C:" in bench.throttle_warnings({**_BUSY, "temperature.gpu": 86.0, "throttle_reasons": 0}, None)[0]


def test_throttle_warning_falls_back_to_the_clock_without_reasons():
    out = bench.throttle_warnings({**_BUSY, "clocks.sm": 1000.0}, None)          # driver gave no reasons
    assert len(out) == 1 and "no throttle reasons" in out[0]


def test_rule_checks_noisy_gated_part_is_named():
    run = _checked_run()
    for r in run["layer"]["regions"].values():
        r["spread_pct"] = 1.0
    run["layer"]["regions"]["fwd:block0"]["spread_pct"] = 25.0
    out = "\n".join(bench.rule_checks(run, ["clean", "layer", "checkpoint", "comm"], _cfg()))
    assert "fwd:block0" in out and "5% check" in out


# ------------------------------------------------------------------------------ the 5% check

def _two_runs():
    a = example_run()
    return a, copy.deepcopy(a)


def test_quick_compare_identical_runs_pass():
    a, b = _two_runs()
    rows, ok, problems = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert ok and not problems
    names = [r[0] for r in rows]
    assert "step (clean)" in names and "fwd:block0" in names
    assert all(r[4] == "ok" for r in rows)


def test_quick_compare_allows_muon_implementation_variant():
    a, b = _two_runs()
    a["config"]["optim"]["muon_impl"] = "loop"
    b["config"]["optim"]["muon_impl"] = "batched"
    rows, ok, problems = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert ok and not problems
    assert "step (clean)" in [row[0] for row in rows]


def test_quick_compare_allows_moe_dispatch_variant():
    a, b = _two_runs()
    a["config"]["model"]["moe"] = {"dispatch": "loop", "num_experts": 8}
    b["config"]["model"]["moe"] = {"dispatch": "sorted", "num_experts": 8}
    rows, ok, problems = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert ok and not problems
    assert "step (clean)" in [row[0] for row in rows]


def test_quick_compare_only_gates_levels_up_to_gate_level():
    a, b = _two_runs()
    level3 = [n for n, r in a["layer"]["regions"].items() if r["level"] == 3]
    assert level3, "the example run must have a level-3 part"
    b["layer"]["regions"][level3[0]]["median"] *= 3          # inside a block: reported, not gated
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert ok and level3[0] not in [r[0] for r in rows]


def test_quick_compare_fails_a_part_that_moved_more_than_tol():
    a, b = _two_runs()
    b["layer"]["regions"]["fwd:block1"]["median"] *= 1.10    # a whole block 10% slower
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.0)
    verdict = {r[0]: r[4] for r in rows}
    assert not ok and verdict["fwd:block1"] == "FAIL" and verdict["fwd:block0"] == "ok"
    assert bench.quick_compare(a, b, 12.0, 2, 0.0)[1]             # a looser tolerance lets it through


def test_quick_compare_5_percent_boundary():
    a, b = _two_runs()
    b["clean"]["step_ms"]["median"] = a["clean"]["step_ms"]["median"] * 1.049
    assert bench.quick_compare(a, b, 5.0, 2, 0.0)[1]
    b["clean"]["step_ms"]["median"] = a["clean"]["step_ms"]["median"] * 1.06
    assert not bench.quick_compare(a, b, 5.0, 2, 0.0)[1]


def test_quick_compare_small_part_passes_under_abs_tol_ms():
    """TSAI 30 Oct: a part passes within tol_pct OR less than abs_tol_ms apart; both run times are kept."""
    a, b = _two_runs()
    a["layer"]["regions"]["data"] = dict(b["layer"]["regions"]["fwd:embed"], median=0.031, level=1)
    b["layer"]["regions"]["data"] = dict(b["layer"]["regions"]["fwd:embed"], median=0.035, level=1)
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.05)                    # 12.9% apart, but 0.004 ms
    row = next(r for r in rows if r[0] == "data")
    assert ok and row[4] == "ok_abs" and (row[1], row[2]) == (0.031, 0.035) and row[3] > 5.0
    assert not bench.quick_compare(a, b, 5.0, 2, 0.0)[1]                    # no floor: the 5% rule alone fails
    b["layer"]["regions"]["data"]["median"] = 0.6                           # 0.569 ms apart: outside both
    assert not bench.quick_compare(a, b, 5.0, 2, 0.05)[1]
    lines = "\n".join(compare_lines(rows, ok, [], None, 5.0, 2, 0.05))
    assert "ok (< 0.05 ms)" in lines and "0.031" in lines and "0.035" in lines and "0.004" in lines


def test_quick_compare_refuses_different_gpu_and_vocab():
    a, b = _two_runs()
    b["meta"]["gpu"] = "OTHER-GPU"
    b["meta"]["vocab_size"] = 50304
    rows, ok, problems = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert not ok and any("gpu" in p for p in problems) and any("vocab_size" in p for p in problems)


def test_quick_compare_missing_part_is_a_failure():
    a, b = _two_runs()
    del b["layer"]["regions"]["fwd:block0"]
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert not ok and {r[0]: r[4] for r in rows}["fwd:block0"] == "MISSING"


def test_quick_compare_part_only_in_the_earlier_run_is_missing():
    a, b = _two_runs()
    del a["layer"]["regions"]["bwd:embed"]
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert not ok and {r[0]: r[4] for r in rows}["bwd:embed"] == "MISSING"


def test_quick_compare_zero_ms_parts():
    a, b = _two_runs()
    a["layer"]["regions"]["opt:opt.adamw"]["median"] = b["layer"]["regions"]["opt:opt.adamw"]["median"] = 0.0
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert ok and {r[0]: r[4] for r in rows}["opt:opt.adamw"] == "ok"        # both 0 ms: they agree
    b["layer"]["regions"]["opt:opt.adamw"]["median"] = 0.3
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert not ok and {r[0]: r[4] for r in rows}["opt:opt.adamw"] == "FAIL"


@pytest.mark.parametrize("section, key, value", [("optim", "name", "adamw"), ("run", "compile", True),
                                                 ("run", "grad_clip", 0.5), ("data", "source", "fineweb"),
                                                 ("model", "n_layer", 3)])
def test_quick_compare_refuses_runs_that_do_different_work(section, key, value):
    a, b = _two_runs()
    b["config"].setdefault(section, {})[key] = value
    _, ok, problems = bench.quick_compare(a, b, 5.0, 2, 0.0)
    assert not ok and any(section in p for p in problems)


def test_quick_compare_includes_checkpoint_and_all_to_all_when_both_have_them():
    a, b = _two_runs()
    for r, ms in ((a, 100.0), (b, 130.0)):
        r["checkpoint"] = {"save_ms": {"median": ms}}
        r["comm"] = {"moe_a2a": {"measured": True, "per_step_ms": ms / 10}}
    rows, ok, _ = bench.quick_compare(a, b, 5.0, 2, 0.0)
    verdict = {r[0]: r[4] for r in rows}
    assert verdict["checkpoint save"] == "FAIL" and verdict["moe all-to-all"] == "FAIL" and not ok


# ------------------------------------------------------------------------------ checkpoint

def test_checkpoint_copies_a_tied_weight_once():
    emb = torch.nn.Embedding(16, 4)
    head = torch.nn.Linear(4, 16, bias=False)
    head.weight = emb.weight
    m = torch.nn.ModuleDict({"tok": emb, "head": head})
    sd = m.state_dict()
    assert sd["tok.weight"] is not sd["head.weight"]          # state_dict hands out a new view per key
    cpu = bench._to_cpu(sd, {})
    assert cpu["tok.weight"] is cpu["head.weight"]
    other = bench._to_cpu({"a": torch.zeros(4), "b": torch.zeros(4)}, {})
    assert other["a"] is not other["b"]                       # equal values, different tensors: two copies


# ------------------------------------------------------------------------------ trace

class _Ev:
    def __init__(self, name, start, end, cuda=True, annotation=False):
        self.name, self.is_user_annotation = name, annotation
        self.device_type = torch.autograd.DeviceType.CUDA if cuda else torch.autograd.DeviceType.CPU
        self.time_range = type("R", (), {"start": start, "end": end})()


def test_trace_counts_kernels_not_annotations():
    from perfkit import timer
    events = [_Ev("Optimizer.step#Muon.step", 0, 1000, annotation=True),      # spans the idle gap
              _Ev("opt:opt.muon.ns", 0, 900, annotation=True),
              _Ev("ampere_bf16_gemm", 0, 100), _Ev("ampere_bf16_gemm", 800, 900), _Ev("cpu_op", 0, 50, cuda=False)]
    prof = type("P", (), {"events": lambda self: events})()
    dev = timer.profiler_device_events(prof)
    assert [e[0] for e in dev] == ["ampere_bf16_gemm", "ampere_bf16_gemm"]
    k = timer.kernel_summary(dev, 1)
    assert k["kernels_per_step"] == 2 and k["gpu_busy_pct"] == pytest.approx(200 / 900 * 100)


# ------------------------------------------------------------------------------ output helpers

def test_write_run_never_overwrites(tmp_path):
    p1 = bench.write_run({"a": 1}, tmp_path, "run")
    p2 = bench.write_run({"a": 2}, tmp_path, "run")
    p3 = bench.write_run({"a": 3}, tmp_path, "run")
    assert [p.name for p in (p1, p2, p3)] == ["run.json", "run-2.json", "run-3.json"]
    assert json.loads(p1.read_text()) == {"a": 1}


def test_run_json_stays_valid_json_with_nan_and_inf(tmp_path):
    p = bench.write_run({"loss": float("nan"), "xs": [1.0, float("inf")], "n": {"v": -float("inf")}}, tmp_path, "r")
    assert json.loads(p.read_text()) == {"loss": None, "xs": [1.0, None], "n": {"v": None}}


def test_slug():
    assert bench._slug("NVIDIA GeForce RTX 5070 Ti") == "geforce-rtx-5070-ti"
    assert bench._slug("") == "cpu"


def test_parse_turns_flags_into_overrides():
    a, ov = bench.parse(["--config", "c.yaml", "--modes", "clean,layer", "--level", "3", "--steps", "7",
                         "--warmup", "2", "run.batch_size=4"])
    assert ov == ["run.batch_size=4", "bench.modes=[clean,layer]", "bench.level=3", "bench.steps=7", "bench.warmup=2"]


def test_parse_accepts_g8_run_and_node_ids():
    args, _ = bench.parse(["--config", "c.yaml", "--run-id", "shared-run", "--node-id", "worker-1"])
    assert args.run_id == "shared-run"
    assert args.node_id == "worker-1"


def test_parse_accepts_overrides_on_both_sides_of_the_flags():
    _, ov = bench.parse(["--config", "c.yaml", "run.batch_size=4", "--steps", "7", "report.tol_pct=9"])
    assert ov == ["run.batch_size=4", "report.tol_pct=9", "bench.steps=7"]


# ------------------------------------------------------------------------------ end to end (CPU)

def _run_main(out_dir, tag, *extra):
    argv = ["--config", str(TINY), "--tag", tag, "--steps", "4", "--warmup", "2",
            *HARNESS, f"bench.out_dir={out_dir}", *extra]
    return bench.main(argv)


@pytest.fixture(scope="module", params=["reversible", "plain"])
def first_run(request, tmp_path_factory):
    """One bench run per stack, shared by the tests below (the function-scoped fake_loader cannot be used here)."""
    tmp = tmp_path_factory.mktemp(request.param)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(bench, "Loader", FakeLoader)
        mp.setattr(bench, "CACHE", tmp / "cache")
        stack = f"model.reversible={'true' if request.param == 'reversible' else 'false'}"
        code = _run_main(tmp / "runs", "first", "--modes", "clean,layer,checkpoint", "--level", "3", stack)
    path = tmp / "runs" / "first.json"
    return {"code": code, "path": path, "run": json.loads(path.read_text()), "cache": tmp / "cache", "stack": stack}


def test_main_writes_a_complete_valid_run(first_run):
    run = first_run["run"]
    assert first_run["code"] == 0, "exit code 0 means validate_run found nothing missing"
    assert validate_run(run) == []
    event_path = Path(run["meta"]["events_jsonl"])
    assert event_path.exists()
    events = [json.loads(line) for line in event_path.read_text().splitlines()]
    steps = [event for event in events if event["event"] == "step_timing"]
    assert [event["step"] for event in steps] == [1, 2, 3, 4]
    assert all(event["node_id"] == run["meta"]["node_id"] and event["rank"] == 0 for event in steps)
    assert all(event["data_ms"] >= 0 and event["raw_step_ms"] > 0 for event in steps)
    assert [event["raw_step_ms"] for event in steps] == run["clean"]["raw_step_ms"]
    assert run["meta"]["vocab_size"] == VOCAB and run["meta"]["tokenizer"]["revision"] == bench.TOKENIZER_REVISION
    assert run["clean"]["step_ms"]["n"] == 4 and run["clean"]["step_ms"]["median"] > 0
    assert run["metrics"]["tokens_per_s"] > 0 and run["metrics"]["params_total"] >= run["metrics"]["params_active"]
    assert set(run["goodput"]["badput_s"]) == {"startup", "first_step", "warmup"}


def test_main_times_whole_blocks_and_the_step_parts(first_run):
    regions = first_run["run"]["layer"]["regions"]
    for part in ("fwd", "bwd", "opt", "fwd:embed", "fwd:head+loss", "fwd:block0", "fwd:block1",
                 "bwd:head+loss", "bwd:block0", "bwd:block1", "bwd:stack", "bwd:embed", "opt:opt.clip"):
        assert part in regions, f"missing gated part {part}"
        assert regions[part]["level"] <= 2 and regions[part]["median"] >= 0
    assert any(r["level"] == 3 for r in regions.values()), "bench.level=3 must also time the parts inside a block"
    assert first_run["run"]["layer"]["overhead_pct"] is not None
    assert first_run["run"]["layer"]["data_host_ms"]["n"] == 4


def test_main_backward_parts_add_up(first_run):
    """bwd = head+loss + stack + embed, and bwd:stack = the blocks, in both stacks (CPU: exact clocks)."""
    r = {n: v["median"] for n, v in first_run["run"]["layer"]["regions"].items()}
    blocks = sum(r[f"bwd:block{i}"] for i in range(2))
    assert r["bwd:head+loss"] + r["bwd:stack"] + r["bwd:embed"] == pytest.approx(r["bwd"], rel=0.15)
    assert blocks == pytest.approx(r["bwd:stack"], rel=0.15)


def test_main_measures_checkpoint_save(first_run):
    ck = first_run["run"]["checkpoint"]
    assert ck["save_ms"]["median"] > 0 and ck["save_ms"]["n"] == ck["repeats"] == 10 and ck["discarded_first"]
    assert not list((first_run["cache"] / "ckpt").glob("*")), "the checkpoint file must be deleted after"


def test_main_flags_a_run_with_the_wrong_vocabulary(first_run):
    warnings = first_run["run"]["warnings"]
    assert any("rule 1a" in w for w in warnings)              # the test model uses 512, not 131072
    assert any("rule 3b" in w and "comm" in w for w in warnings)


def test_main_against_exit_codes(tmp_path, first_run, capsys):
    stack = first_run["stack"]
    # same numbers: every part agrees
    code = _run_main(tmp_path / "runs", "same", "--modes", "clean,layer", "--level", "3", "--against",
                     str(first_run["path"]), "report.tol_pct=1000", stack)
    assert code == 0
    assert "PASS" in capsys.readouterr().out
    # the earlier run says the step took a hundredth of the time: this run is far outside tol_pct
    fast = copy.deepcopy(first_run["run"])
    fast["clean"]["step_ms"]["median"] /= 100
    other = tmp_path / "fast.json"
    other.write_text(json.dumps(fast))
    code = _run_main(tmp_path / "runs", "slow", "--modes", "clean,layer", "--level", "3", "--against", str(other),
                     stack)
    assert code == 2
    assert "FAIL" in capsys.readouterr().out


def test_main_rejects_an_unknown_mode(tmp_path):
    with pytest.raises(SystemExit):
        _run_main(tmp_path / "runs", "x", "--modes", "clean,nonsense")


# ------------------------------------------------------------------------------ --repeat (Task 2)
# "Automatically run the benchmark twice and fail if any part differs by more than 5%."

def test_parse_repeat_defaults_to_one_run():
    assert bench.parse(["--config", "c.yaml"])[0].repeat == 1
    assert bench.parse(["--config", "c.yaml", "--repeat", "2"])[0].repeat == 2


def _in_process_repeats(monkeypatch):
    """Later --repeat runs normally start a new Python process (bench.repeat_run), which would not see the fake
    Loader. Here they run in this process, through the same arguments repeat_cmd builds."""
    calls = []

    def run(argv, tag, against=None):
        calls.append((tag, against))
        a, ov = bench.parse(bench.repeat_cmd(argv, tag, against)[3:])
        return bench.run_once(a, ov)[0]
    monkeypatch.setattr(bench, "repeat_run", run)
    return calls


def test_repeat_cmd_is_one_run_with_a_new_tag_against_the_first():
    cmd = bench.repeat_cmd(["--config", "c.yaml", "--tag", "x", "--repeat", "3", "run.seed=1"], "x-run2",
                           Path("runs/x.json"))
    assert cmd[1:3] == ["-m", "perfkit.bench"]
    a, ov = bench.parse(cmd[3:])
    assert (a.repeat, a.tag, a.against, ov) == (1, "x-run2", str(Path("runs/x.json")), ["run.seed=1"])
    assert "--against" not in bench.repeat_cmd(["--config", "c.yaml"], "x", None)       # the first run


def test_repeat_rejects_a_shared_run_id():
    with pytest.raises(SystemExit, match="--run-id is for one benchmark invocation"):
        bench.main(["--config", str(TINY), "--run-id", "shared-exp", "--repeat", "2"])


def test_repeat_runs_every_run_in_a_child_and_the_first_without_against(tmp_path, monkeypatch):
    calls = _in_process_repeats(monkeypatch)
    _run_main(tmp_path / "runs", "kids", "--modes", "clean", "--repeat", "2", "report.tol_pct=1000")
    assert [c[0] for c in calls] == ["kids", "kids-run2"]               # the parent ran nothing itself
    assert calls[0][1] is None and Path(calls[1][1]).name == "kids.json"


def test_repeat_fails_when_a_later_run_is_killed(tmp_path, monkeypatch, capsys):
    calls = _in_process_repeats(monkeypatch)
    real = bench.repeat_run
    monkeypatch.setattr(bench, "repeat_run", lambda argv, tag, against=None: real(argv, tag, against) if not calls
                        else -9)                              # run 2 killed by a signal (out-of-memory killer)
    code = _run_main(tmp_path / "runs", "killed", "--modes", "clean", "--repeat", "2", "report.tol_pct=1000")
    assert code == 1 and "PASS" not in capsys.readouterr().out


def test_repeat_writes_one_json_per_run_and_passes_when_they_agree(tmp_path, capsys, monkeypatch):
    _in_process_repeats(monkeypatch)
    # report.tol_pct=1000: the two tiny CPU runs differ by noise, so the test must not depend on the 5% value.
    code = _run_main(tmp_path / "runs", "rep", "--modes", "clean", "--repeat", "2", "report.tol_pct=1000")
    assert code == 0
    # <tag>.json is run 1; <tag>-run2.json is run 2, checked against run 1.
    assert sorted(p.name for p in (tmp_path / "runs").glob("*.json")) == ["rep-run2.json", "rep.json"]
    first_run = json.loads((tmp_path / "runs" / "rep.json").read_text())
    second_run = json.loads((tmp_path / "runs" / "rep-run2.json").read_text())
    assert first_run["meta"]["run_id"] != second_run["meta"]["run_id"]
    out = capsys.readouterr().out
    assert "repeat: 2 runs against rep.json: PASS" in out
    assert validate_run(json.loads((tmp_path / "runs" / "rep-run2.json").read_text())) == []


def test_repeat_fails_with_exit_code_2_when_the_second_run_is_slower(tmp_path, monkeypatch, capsys):
    real, calls = bench.run_clean, {"n": 0}

    def slower_second_time(s, n):
        clean, loss, mem = real(s, n)
        calls["n"] += 1
        if calls["n"] == 2:                      # only the second run: 50% slower, far above the 5% limit
            clean["step_ms"]["median"] *= 1.5
        return clean, loss, mem

    monkeypatch.setattr(bench, "run_clean", slower_second_time)
    _in_process_repeats(monkeypatch)
    code = _run_main(tmp_path / "runs", "slow", "--modes", "clean", "--repeat", "2")
    assert code == 2
    assert "repeat: 2 runs against slow.json: FAIL" in capsys.readouterr().out


def test_without_repeat_one_json_is_written(tmp_path):
    assert _run_main(tmp_path / "runs", "single", "--modes", "clean") in (0, 2)
    assert [p.name for p in (tmp_path / "runs").glob("*.json")] == ["single.json"]


def test_run_json_has_mean_and_std_for_the_step(tmp_path):
    _run_main(tmp_path / "runs", "stats", "--modes", "clean")
    step = json.loads((tmp_path / "runs" / "stats.json").read_text())["clean"]["step_ms"]
    assert step["mean"] > 0 and step["std"] >= 0 and step["median"] > 0


# ------------------------------------------------------------------------------ slowest parts and their traces

def test_trace_with_layer_writes_one_small_trace_per_slowest_part(tmp_path):
    from perfkit.parts import MAX_BYTES
    code = _run_main(tmp_path / "runs", "traced", "--modes", "clean,layer,trace", "--level", "3")
    run = json.loads((tmp_path / "runs" / "traced.json").read_text())
    assert code == 0 and validate_run(run) == []
    parts = run["trace"]["parts"]
    assert len(parts) == 5 and [p["ms"] for p in parts] == sorted((p["ms"] for p in parts), reverse=True)
    for p in parts:
        assert p["file"], f"no trace for {p['region']}"
        path = Path(p["file"])
        assert path.parent.name == "traced_parts" and path.stat().st_size <= MAX_BYTES
        events = json.loads(path.read_text())["traceEvents"]
        assert any(e.get("name") == p["region"] or str(e.get("name", "")).startswith("__point__") for e in events)
    assert not any(w.startswith("no trace cut") for w in run["warnings"])


def test_trace_without_layer_says_why_there_are_no_parts(tmp_path):
    _run_main(tmp_path / "runs", "nolayer", "--modes", "clean,trace")
    tr = json.loads((tmp_path / "runs" / "nolayer.json").read_text())["trace"]
    assert "parts" not in tr and "layer" in tr["parts_note"]
    assert not (tmp_path / "runs" / "nolayer_parts").exists()


def test_no_system_section_off_cuda(first_run):
    assert "system" not in first_run["run"]


def test_rule_checks_flag_an_unknown_dirty_state():
    run = _checked_run(dirty=None, commit="8ea01e8+local")         # a zip upload: PERF_COMMIT set, no .git
    for r in run["layer"]["regions"].values():
        r["spread_pct"] = 1.0
    out = "\n".join(bench.rule_checks(run, ["clean", "layer", "checkpoint", "comm"], _cfg()))
    assert "could not tell whether the code is committed" in out


# ------------------------------------------------------------------------------ timer follow-up regressions

def test_clean_json_reports_event_allocation_count(tmp_path):
    # CPU path has no CUDA events, but must still export an explicit zero.
    _run_main(tmp_path / "runs", "counter", "--modes", "clean")
    run = json.loads((tmp_path / "runs" / "counter.json").read_text())
    assert run["clean"]["events_created_during_steps"] == 0
    assert validate_run(run) == []


def test_clean_warns_if_timer_allocated_events_during_steps(tmp_path, monkeypatch):
    # Simulate a CUDA event-pool exhaustion without requiring CUDA hardware.
    real = bench.run_clean

    def exhausted(s, n):
        clean, loss, mem = real(s, n)
        clean["events_created_during_steps"] = 2
        return clean, loss, mem

    monkeypatch.setattr(bench, "run_clean", exhausted)
    _run_main(tmp_path / "runs", "exhausted", "--modes", "clean")
    run = json.loads((tmp_path / "runs" / "exhausted.json").read_text())
    assert run["clean"]["events_created_during_steps"] == 2
    assert any("2 CUDA timing events" in w and "clean" in w for w in run["warnings"])


def test_comm_preallocates_timing_events_and_exports_counter(monkeypatch):
    import torch.distributed as dist

    seen = {}

    class FakeTimer:
        def __init__(self, device, expected_steps=0):
            seen["expected_steps"] = expected_steps
            self.events_created_during_steps = 0
            self.n = 0

        def start(self):
            pass

        def stop(self):
            self.n += 1

        def times_ms(self):
            return [2.0] * self.n

    monkeypatch.setattr(bench.T, "StepTimer", FakeTimer)
    monkeypatch.setattr(bench.T, "sync", lambda device: None)
    monkeypatch.setattr(dist, "get_world_size", lambda: 2)
    monkeypatch.setattr(dist, "get_backend", lambda: "gloo")
    monkeypatch.setattr(dist, "barrier", lambda: None)
    monkeypatch.setattr(dist, "all_to_all_single", lambda out, inp: out.copy_(inp))
    monkeypatch.setattr(dist, "all_reduce", lambda tensor, op=None: None)

    plan = {"payload_dtype": "fp32", "bytes_per_call": 32, "calls_per_step": 2}
    result = bench.run_comm(plan, torch.device("cpu"), reps=4)
    assert seen["expected_steps"] == 4
    assert result["events_created_during_steps"] == 0
    assert result["measured"] is True and result["per_call_ms"]["n"] == 4
    assert result["per_step_ms"] == pytest.approx(4.0)


# ------------------------------------------------------------------------------ G6 timer follow-up: layer and warning regressions

def test_layer_timer_event_allocation_is_reported_in_json(first_run):
    layer = first_run["run"]["layer"]
    assert layer["events_created_during_steps"] == 0
    assert layer["inner_pass"]["events_created_during_steps"] == 0


def test_layer_event_allocation_warns_for_both_passes(tmp_path, monkeypatch):
    real = bench.run_layer

    def injected(s, n, level, warm):
        result = real(s, n, level, warm)
        result["events_created_during_steps"] = 2
        result.setdefault("inner_pass", {})["events_created_during_steps"] = 4
        return result

    monkeypatch.setattr(bench, "run_layer", injected)
    _run_main(tmp_path / "runs", "layer-events", "--modes", "clean,layer", "--level", "3")
    run = json.loads((tmp_path / "runs" / "layer-events.json").read_text())
    assert run["layer"]["events_created_during_steps"] == 2
    assert run["layer"]["inner_pass"]["events_created_during_steps"] == 4
    assert any("6 CUDA timing events" in w and "layer" in w for w in run["warnings"])


def test_communication_warning_is_emitted_only_for_nonzero_counter():
    warns = []
    bench.warn_timing_allocations(warns, 0, "communication")
    assert warns == []
    bench.warn_timing_allocations(warns, 3, "communication")
    assert len(warns) == 1
    assert "3 CUDA timing events" in warns[0] and "communication" in warns[0]


# PR24 review regression: inner recorder-pool reporting
def test_inner_pool_warning_and_json(tmp_path, monkeypatch):
    real = bench.run_layer
    def injected(s, n, level, warm):
        result = real(s, n, level, warm)
        result["inner_pass"]["events_created_while_measuring"] = 57
        return result
    monkeypatch.setattr(bench, "run_layer", injected)
    _run_main(tmp_path / "runs", "inner-pool", "--modes", "clean,layer", "--level", "3")
    run = json.loads((tmp_path / "runs" / "inner-pool.json").read_text())
    assert run["layer"]["inner_pass"]["events_created_while_measuring"] == 57
    assert any("57 recorder-pool CUDA events" in w and "layer.inner_pass" in w for w in run["warnings"])


def test_run_layer_copies_inner_pool_count(monkeypatch):
    real = bench.layer_pass
    calls = {"n": 0}
    def injected(s, n, level, warm):
        result = real(s, n, level, warm)
        calls["n"] += 1
        if calls["n"] == 2:
            result["events_created_while_measuring"] = 57
        return result
    monkeypatch.setattr(bench, "layer_pass", injected)
    s = bench.build(tiny_cfg(), torch.device("cpu"))
    result = bench.run_layer(s, 1, 3, 2)
    assert result["inner_pass"]["events_created_while_measuring"] == 57
