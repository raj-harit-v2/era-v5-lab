"""Review D (week 3): perfkit measurement, MFU, job wrappers. CPU only.

Each strict xfail is a confirmed defect (REVIEW-D<n> in the review notes); it starts failing (XPASS -> error) once
fixed, so the fix PR should drop the marker. The plain tests are guards for behaviour the review checked and found
correct, kept so a later change (e.g. class PR #369's report.compare_clean_step) cannot quietly break it.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest
import torch

from models.ke1 import token_bytes_random
from perfkit import bench, report
from perfkit import metrics as M
from perfkit import timer as T
from perfkit.schema import example_run, validate_run

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT.parents[1]
G5_CONFIG_V1 = LAB / "teams" / "05-architecture" / "configs" / "config_v1.yaml"
G5_T2_ARM = LAB / "teams" / "05-architecture" / "configs" / "arms" / "t2.yaml"
VOCAB = 512


def _job(name: str):
    """Import a jobs/*.py wrapper as a module (jobs/ is not a package)."""
    spec = importlib.util.spec_from_file_location(f"review_{name}", ROOT / "jobs" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeLoader:
    """dataio.loader.Loader stand-in: random ids, no data or tokenizer download."""

    def __init__(self, source, batch_size, block_size, device, data_dir=None, vocab_size=VOCAB, seed=0,
                 split="train", tokenizer_path=None, prefetch=False):
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


@pytest.fixture
def fake_bench(monkeypatch, tmp_path):
    monkeypatch.setattr(bench, "Loader", _FakeLoader)
    monkeypatch.setattr(bench, "CACHE", tmp_path / "cache")
    return tmp_path


def _bench_argv(out_dir, tag, *extra):
    return ["--config", str(ROOT / "configs" / "tiny_cpu.yaml"), "--tag", tag, "--modes", "clean", "--level", "1",
            "--warmup", "1", "data.source=synthetic", f"model.vocab_size={VOCAB}", "model.embedding=ke1",
            "model.ffn=mlp", "model.reversible=false", f"bench.out_dir={out_dir}", *extra]


# ============================================================================== confirmed defects (strict xfail)

# REVIEW-D1 (fixed in this PR)
def test_d1_sampler_summary_survives_missing_pci_bus_id():
    s = M.GpuSampler(torch.device("cpu"))
    s.started, s.target_index, s.target_pci_bus_id = True, 0, "00000000:01:00.0"
    # parse_line turns "[N/A]" into None for pci.bus_id; the row still names GPU index 0
    s.rows = [s.parse_line("0, NVIDIA X, GPU-1, [N/A], 50, 10, 1000, 1500, 5000, 200, 60")]
    assert s.rows[0] is not None and s.rows[0]["pci.bus_id"] is None
    out = s.summary()
    assert out["samples"] == 1


@pytest.mark.xfail(strict=True, reason="REVIEW-D2: first-substring peak lookup gives an RTX A1000 the A100's "
                                       "312 TFLOPS (MFU off by orders of magnitude, no warning)")
def test_d2_peak_lookup_does_not_match_a100_inside_a1000():
    assert M.gpu_peak("NVIDIA RTX A1000 6GB Laptop GPU").get("spec") != "A100"


@pytest.mark.xfail(strict=True, reason="REVIEW-D3: a known GPU with an empty peak row (H100 NVL, A10G) is reported "
                                       "as unsupported_dtype instead of peak_tflops_unavailable")
@pytest.mark.parametrize("name", ["NVIDIA H100 NVL", "NVIDIA A10G"])
def test_d3_known_gpu_without_peak_numbers_gets_the_right_reason(name):
    assert M.peak_unavailable_reason(name, "bf16") == "peak_tflops_unavailable"


@pytest.mark.xfail(strict=True, reason="REVIEW-D4: validate_run passes a NaN mfu that write_run then writes as "
                                       "null with a null reason, so the file on disk fails the same contract")
def test_d4_validate_run_rejects_non_finite_mfu():
    run = example_run()
    run["metrics"]["mfu"] = float("nan")
    on_disk = json.loads(json.dumps(bench._finite(run)))
    assert validate_run(on_disk) != []                     # the written file breaks the contract ...
    assert validate_run(run) != []                         # ... so the in-memory check must catch it first


@pytest.mark.xfail(strict=True, reason="REVIEW-D5: metrics.mfu() reports MFU 0.0 with no reason for zero "
                                       "throughput, where mfu_run() returns None + invalid_global_throughput")
def test_d5_selected_gpu_mfu_matches_run_level_contract_for_zero_throughput():
    f = {"model_flops_per_token": 1e9, "hw_flops_per_token": 2e9}
    out = M.mfu(f, 0.0, 312.0)
    assert out["mfu"] is None and out["mfu_unavailable_reason"] is not None


@pytest.mark.xfail(strict=True, reason="REVIEW-D6: stats() with a NaN gives an order-dependent median "
                                       "(sorted() cannot order NaN)")
def test_d6_stats_is_order_independent_or_rejects_nan():
    a, b = [float("nan"), 1.0, 2.0], [1.0, 2.0, float("nan")]
    try:
        ma, mb = T.stats(a)["median"], T.stats(b)["median"]
    except ValueError:
        return                                                # rejecting NaN is a fix too
    assert (math.isnan(ma) and math.isnan(mb)) or ma == mb


@pytest.mark.xfail(strict=True, reason="REVIEW-D7: report.main reads config['report'] before looking at the CLI "
                                       "flags, so an older run JSON without a report section cannot be compared")
def test_d7_report_main_uses_cli_tolerances_when_config_has_no_report(tmp_path):
    run = example_run()
    del run["config"]["report"]
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(run))
    b.write_text(json.dumps(run))
    code = report.main([str(a), "--compare", str(b), "--tol-pct", "5", "--gate-level", "2", "--abs-tol-ms", "0.05"])
    assert code in (0, 2)


@pytest.mark.xfail(strict=True, reason="REVIEW-D8: bench.steps=0 is accepted and crashes with TypeError at float(loss) (bench.py:906) "
                                       "after build and warmup, instead of a clear refusal up front")
def test_d8_zero_steps_is_refused_cleanly(fake_bench):
    try:
        code = bench.main(_bench_argv(fake_bench / "runs", "zero", "--steps", "0"))
    except SystemExit:
        return                                                # a clean refusal is the fix
    assert code != 0


def _prof_resolved_config():
    from models.config import load_config
    prof = _job("run_dryrun1_prof")
    overrides, _ = prof.load_g5_overrides(G5_CONFIG_V1)
    return overrides, load_config(ROOT / "configs" / "base.yaml", overrides + ["data.source=synthetic"])


@pytest.mark.skipif(not G5_CONFIG_V1.exists(), reason="G5 config_v1.yaml not in this tree")
@pytest.mark.xfail(strict=True, reason="REVIEW-D9: dryrun1_prof / _nsys / _a2a time a reversible stack "
                                       "(base.yaml default) that no G5 config selects; G5's dry-run arm T2 has "
                                       "reversible: false. Doubles the a2a calls and adds recompute to bwd")
def test_d9_dryrun_jobs_do_not_inherit_reversible_stack():
    _, cfg = _prof_resolved_config()
    assert cfg["model"]["reversible"] is False


@pytest.mark.skipif(not (G5_CONFIG_V1.exists() and G5_T2_ARM.exists()), reason="G5 configs not in this tree")
@pytest.mark.xfail(strict=True, reason="REVIEW-D10: 'kronecker' is mapped to ke2, but G5's dry-run-1 arm (t2.yaml) "
                                       "runs ke1; the profile times a different input embedding")
def test_d10_kronecker_maps_to_the_embedding_g5_runs():
    import yaml
    _, cfg = _prof_resolved_config()
    g5_arm = yaml.safe_load(G5_T2_ARM.read_text())
    assert cfg["model"]["embedding"] == g5_arm["model"]["embedding"]


# REVIEW-D11 (fixed in this PR)
def test_d11_unmapped_g5_setting_is_not_silently_dropped(tmp_path):
    cfg = tmp_path / "config_v1.yaml"
    cfg.write_text("settings:\n"
                   "  - {key: moe.top_k, value: 2}\n"
                   "  - {key: attention.n_kv_head, value: 2}\n"      # a value G5 could fill; no mapping exists
                   "  - {key: model.activation, value: swiglu}\n")
    prof = _job("run_dryrun1_prof")
    try:
        overrides, applied = prof.load_g5_overrides(cfg)
    except (ValueError, KeyError, SystemExit):
        return                                                # refusing an unknown key is a fix
    assert any("n_kv_head" in o for o in overrides) and any("activation" in o for o in overrides)


def test_d11_signed_g5_config_v1_still_maps():
    """The fix must not reject today's signed config_v1: every non-null key there has a mapping."""
    prof = _job("run_dryrun1_prof")
    overrides, applied = prof.load_g5_overrides(prof.DEFAULT_G5_CONFIG)
    assert "model.moe.top_k=2" in overrides and "model.embedding=ke2" in overrides


# REVIEW-D12 (fixed in this PR)
def test_d12_a2a_wrapper_refuses_nproc_above_visible_gpus(tmp_path, monkeypatch):
    a2a = _job("run_dryrun1_a2a")
    launched = []

    class _Done:
        returncode = 1

    monkeypatch.setattr(a2a.subprocess, "run", lambda args, **kw: launched.append(args) or _Done())
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)
    out = tmp_path / "out"
    try:
        a2a.run_job(out, smoke_cpu=False, nproc=2)
    except SystemExit:
        pass
    assert not launched, f"launched {launched[0][:2] if launched else None} with 1 visible GPU"


@pytest.mark.xfail(strict=True, reason="REVIEW-D13: run_dryrun1_nsys deletes '<out>/<tag>*' with unlink(), which "
                                       "raises on a directory that shares the tag prefix")
def test_d13_nsys_cleanup_survives_a_directory_with_the_tag_prefix(tmp_path, monkeypatch):
    nsys = _job("run_dryrun1_nsys")
    out = tmp_path / "out"
    (out / "dryrun1_nsys_parts").mkdir(parents=True)
    monkeypatch.setattr(nsys, "find_nsys", lambda: "/bin/true")

    class _Fail:
        returncode = 1
        stdout = ""
        stderr = ""

    monkeypatch.setattr(nsys, "run", lambda cmd, **kw: _Fail())
    monkeypatch.setattr(nsys.subprocess, "run", lambda *a, **kw: _Fail())
    a = type("A", (), {"out": str(out), "tag": "dryrun1_nsys", "warmup": 1, "steps": 1, "level": 1,
                       "synthetic": True, "extra": []})()
    code = nsys.outer(a, "configs/base.yaml", [], {}, G5_CONFIG_V1)
    assert code != 0                                          # fails on the nsys run, not on the cleanup


# ============================================================================== guards (pass today)

def test_guard_compare_without_layer_still_gates_the_clean_step():
    """Class PR #369 adds report.compare_clean_step; with it false and no layer section, its quick_compare and
    report.compare return ok=True with zero gated rows (checked on refs/review/up369). Today the step is always
    gated: keep that, or make an empty comparison fail."""
    a, b = example_run(), example_run()
    for r in (a, b):
        r.pop("layer")
    b["clean"]["step_ms"]["median"] *= 3
    rows, ok, problems = bench.quick_compare(a, b, 5.0, 2, 0.05)
    assert rows and not ok
    rows, ok, problems = report.compare(a, b, 5.0, 2, 0.05)
    assert rows and not ok


@pytest.mark.parametrize("xs,median,p10,p90", [([5.0], 5.0, 5.0, 5.0), ([1.0, 2.0], 1.5, 1.1, 1.9),
                                               ([3.0, 1.0, 2.0], 2.0, 1.2, 2.8)])
def test_guard_stats_small_n(xs, median, p10, p90):
    st = T.stats(xs)
    assert st["n"] == len(xs)
    assert (st["median"], st["p10"], st["p90"]) == pytest.approx((median, p10, p90))


def test_guard_stats_empty_has_no_numbers():
    st = T.stats([])
    assert st["n"] == 0 and st["median"] is None and st["spread_pct"] is None


def test_guard_steptimer_closes_the_pair_when_the_step_raises():
    t = T.StepTimer("cpu")
    with pytest.raises(RuntimeError):
        with t.step():
            raise RuntimeError("boom")
    assert len(t) == 1
    t.start()                                                 # not left open
    t.stop()


@pytest.mark.parametrize("name", ["NVIDIA GeForce RTX 5070 Ti", "NVIDIA RTX PRO 6000 Blackwell"])
def test_guard_unknown_gpu_gives_no_mfu_and_a_reason(name):
    assert M.gpu_peak(name) == {}
    assert M.peak_unavailable_reason(name, "bf16") == "unknown_gpu"
    f = {"model_flops_per_token": 1e9, "hw_flops_per_token": 2e9}
    out = M.mfu(f, 1e5, None, M.peak_unavailable_reason(name, "bf16"))
    assert out["mfu"] is None and out["mfu_unavailable_reason"] == "unknown_gpu"


@pytest.mark.parametrize("name,spec", [("NVIDIA L40S", "L40S"), ("NVIDIA L40", "L40"), ("NVIDIA L4", "L4"),
                                       ("NVIDIA A100-SXM4-80GB", "A100"), ("NVIDIA A10", "A10"),
                                       ("NVIDIA H100 PCIe", "H100 PCIe"), ("NVIDIA H100 80GB HBM3", "H100"),
                                       ("NVIDIA H200 NVL", "H200 NVL"), ("Tesla T4", "T4")])
def test_guard_peak_table_order_for_names_that_contain_each_other(name, spec):
    assert M.gpu_peak(name)["spec"] == spec


def test_guard_quick_compare_refuses_a_different_model():
    a, b = example_run(), example_run()
    b["config"]["model"]["n_layer"] = 3
    _, ok, problems = bench.quick_compare(a, b, 5.0, 2, 0.05)
    assert not ok and problems


def test_guard_gate_on_tiny_parts_uses_the_absolute_floor():
    # 0.010 ms vs 0.020 ms is 100% apart but 0.01 ms < abs_tol_ms: below timer noise, so not a failure
    assert report.gate(0.010, 0.020, 5.0, 0.05)[1] == "ok_abs"
    assert report.gate(1.00, 1.20, 5.0, 0.05)[1] == "FAIL"


def test_guard_write_run_never_writes_nan(tmp_path):
    run = example_run()
    run["metrics"]["hfu"] = float("inf")
    p = bench.write_run(run, tmp_path, "nan")
    assert json.loads(p.read_text())["metrics"]["hfu"] is None


def test_guard_mfu_run_rejects_duplicate_and_bad_participants():
    f = {"model_flops_per_token": 1e9, "hw_flops_per_token": 2e9}
    assert M.mfu_run(f, 1e5, [312, 312], ranks=[0, 0])["mfu_unavailable_reason"] == "duplicate_participants"
    assert M.mfu_run(f, 1e5, [312, None])["mfu_unavailable_reason"] == "participant_peak_unavailable"
    assert M.mfu_run(f, 1e5, [])["mfu_unavailable_reason"] == "participants_unavailable"
    two = M.mfu_run(f, 2e5, [312, 312])["mfu"]
    assert two == pytest.approx(M.mfu(f, 1e5, 312)["mfu"])


def test_guard_jsonl_steps_are_one_based_and_match_raw_step_ms(fake_bench):
    """G8's run-JSON parser numbers raw_step_ms from 0 while the live step_timing events say step 1..n (cross-team
    note in the review). This pins G6's side so the mismatch is fixed in one place."""
    code = bench.main(_bench_argv(fake_bench / "runs", "steps", "--steps", "3"))
    assert code == 0
    run = json.loads((fake_bench / "runs" / "steps.json").read_text())
    events = [json.loads(x) for x in Path(run["meta"]["events_jsonl"]).read_text().splitlines()]
    steps = [e for e in events if e["event"] == "step_timing"]
    assert [e["step"] for e in steps] == [1, 2, 3]
    assert [e["raw_step_ms"] for e in steps] == run["clean"]["raw_step_ms"]


def test_guard_a2a_plan_counts_double_calls_for_the_reversible_stack():
    """What REVIEW-D9 costs in comm mode: the reversible stack doubles calls_per_layer (4 -> 8)."""
    from models.config import load_config, model_config
    base = load_config(ROOT / "configs" / "base.yaml", ["model.ffn=moe", "data.source=synthetic"])
    plain = load_config(ROOT / "configs" / "base.yaml", ["model.ffn=moe", "model.reversible=false",
                                                         "data.source=synthetic"])
    rev_plan = bench.a2a_plan(base, model_config(base), "bf16")
    plain_plan = bench.a2a_plan(plain, model_config(plain), "bf16")
    assert rev_plan["calls_per_layer"] == 2 * plain_plan["calls_per_layer"] == 8
    assert rev_plan["payload_dtype"] == "fp32"                 # an upper bound: bf16 runs send half these bytes
