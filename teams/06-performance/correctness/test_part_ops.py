"""perfkit/part_ops.py: the slowest operations inside one region of a trace (no GPU needed).

Covers which op is credited (outermost in the region, not one that contains it), calls and kernel counts, GPU work
after the CPU range, the region summary, backward segments, render, the command line and a CPU-only trace.
"""
from __future__ import annotations

import json

import pytest

from perfkit import part_ops as O


def _x(name, ts, dur, cat, tid=1, **args):
    e = {"ph": "X", "cat": cat, "name": name, "ts": ts, "dur": dur, "pid": 1, "tid": tid}
    if args:
        e["args"] = args
    return e


def _trace():
    ann, op, rt = "user_annotation", "cpu_op", "cuda_runtime"
    ev = [
        _x("ProfilerStep#2", 200, 400, ann),
        _x("aten::wrapper", 205, 120, op),                                     # starts before the region, contains it
        _x("fwd:embed.ke", 210, 100, ann),
        _x("aten::embedding_bag", 215, 40, op), _x("aten::_embedding_bag", 218, 30, op),     # one op, one nested
        _x("cudaLaunchKernel", 225, 2, rt, correlation=7), _x("cudaLaunchKernel", 240, 2, rt, correlation=8),
        _x("aten::index_select", 260, 10, op), _x("cudaLaunchKernel", 262, 2, rt, correlation=9),
        _x("aten::sum", 280, 8, op), _x("cudaMemcpyAsync", 282, 2, rt, correlation=10),
        _x("aten::index_select", 290, 10, op), _x("cudaLaunchKernel", 292, 2, rt, correlation=11),
        _x("aten::mm", 400, 10, op), _x("cudaLaunchKernel", 402, 2, rt, correlation=12),     # after the region
        _x("embedding_bag_kernel", 500, 50, "kernel", tid=7, correlation=7),                 # run long after the launch
        _x("reduce_kernel", 560, 5, "kernel", tid=7, correlation=8),
        _x("index_kernel", 570, 4, "kernel", tid=7, correlation=9),
        _x("Memcpy DtoD", 575, 2, "gpu_memcpy", tid=7, correlation=10),
        _x("index_kernel", 580, 4, "kernel", tid=7, correlation=11),
        _x("gemm_kernel", 700, 30, "kernel", tid=7, correlation=12),
        _x("__point__:__bwd_start__", 320, 1, ann), _x("__point__:head+loss", 330, 1, ann),
        _x("autograd::engine::evaluate_function: _MarkBackward", 335, 30, op),             # holds the stack point
        _x("__point__:stack", 340, 1, ann),
        _x("autograd::engine::evaluate_function: EmbeddingBagBackward0", 370, 20, op),
        _x("aten::_embedding_bag_backward", 372, 15, op), _x("cudaLaunchKernel", 375, 2, rt, correlation=13),
        _x("__point__:__bwd_end__", 395, 1, ann),
        _x("embedding_bag_backward_kernel", 600, 40, "kernel", tid=7, correlation=13),
    ]
    return {"traceEvents": ev, "deviceProperties": [{"id": 0, "name": "Test GPU"}]}


def _rows(res):
    return {o["op"]: o for o in res["ops"]}


def test_operations_are_the_outermost_ops_that_start_in_the_region():
    res = O.analyse(_trace(), "fwd:embed.ke")
    assert [o["op"] for o in res["ops"]] == ["aten::embedding_bag", "aten::index_select", "aten::sum"]
    assert "aten::wrapper" not in _rows(res) and "aten::_embedding_bag" not in _rows(res)
    assert "aten::mm" not in _rows(res) and not any(o["op"] == O.UNOWNED for o in res["ops"])


def test_calls_kernels_copies_and_times():
    rows = _rows(O.analyse(_trace(), "fwd:embed.ke"))
    bag, sel, total = rows["aten::embedding_bag"], rows["aten::index_select"], rows["aten::sum"]
    assert (bag["calls"], bag["kernels"], bag["copies"]) == (1, 2, 0)
    assert bag["gpu_ms"] == pytest.approx(0.055)                            # 50 + 5 us, run long after the launches
    assert bag["cpu_ms"] == pytest.approx(0.040)                            # the outer op only, not the nested one too
    assert (sel["calls"], sel["kernels"]) == (2, 2) and sel["gpu_ms"] == pytest.approx(0.008)
    assert (total["kernels"], total["copies"]) == (0, 1) and total["gpu_ms"] == pytest.approx(0.002)
    assert bag["gpu_pct"] == pytest.approx(100 * 55 / 65)
    assert [k["name"] for k in bag["kernel_names"]] == ["embedding_bag_kernel", "reduce_kernel"]


def test_region_summary_counts_overlap_once():
    res = O.analyse(_trace(), "fwd:embed.ke")
    assert res["calls_in_step"] == 1 and res["windows_ms"] == pytest.approx(0.1)
    assert res["gpu_ms"] == pytest.approx(0.065) and res["kernels"] == 4 and res["copies"] == 1
    assert res["gpu_span_ms"] == pytest.approx(0.084)                      # 500 .. 584
    assert res["gpu_busy_pct"] == pytest.approx(100 * 65 / 84)
    busy = O._busy_us([{"ts": 0, "dur": 10}, {"ts": 5, "dur": 10}, {"ts": 5, "dur": 2}, {"ts": 30, "dur": 1}])
    assert busy == 16                                                       # 0..15 once, then 30..31


def test_backward_segment_credits_the_backward_node():
    res = O.analyse(_trace(), "bwd:embed")                                  # from the stack point to __bwd_end__
    assert [o["op"] for o in res["ops"]] == ["autograd::engine::evaluate_function: EmbeddingBagBackward0"]
    assert res["ops"][0]["kernels"] == 1 and res["gpu_ms"] == pytest.approx(0.04)
    assert O._label(res["ops"][0]["op"]) == "bwd EmbeddingBagBackward0"
    assert O._label("aten::sum") == "aten::sum"


def test_work_launched_outside_any_op_is_listed_apart():
    t = _trace()
    t["traceEvents"] += [_x("cudaLaunchKernel", 300, 2, "cuda_runtime", correlation=20),
                         _x("lonely_kernel", 800, 3, "kernel", tid=7, correlation=20)]
    res = O.analyse(t, "fwd:embed.ke")
    lone = _rows(res)[O.UNOWNED]
    assert lone["kernels"] == 1 and lone["calls"] == 0 and lone["cpu_ms"] is None


def test_region_not_in_the_trace_is_none_and_a_cpu_trace_has_no_operations():
    assert O.analyse(_trace(), "fwd:block7.attn.sdpa") is None
    cpu = {"traceEvents": [e for e in _trace()["traceEvents"] if e["cat"] not in ("kernel", "gpu_memcpy")]}
    res = O.analyse(cpu, "fwd:embed.ke")
    assert res["ops"] == [] and res["gpu_ms"] == 0 and res["gpu_busy_pct"] is None
    assert "no GPU work" in O.render(res)[1]


def test_render_lists_the_top_operations_and_counts_the_rest():
    res = O.analyse(_trace(), "fwd:embed.ke")
    lines = O.render(res, top=1)
    assert lines[0].startswith("fwd:embed.ke: 1 call(s) per step") and "busy 77%" in lines[0]
    assert "aten::embedding_bag" in lines[2] and "embedding_bag_kernel" in lines[3]
    assert "+2 more operations" in lines[-1] and not any("aten::sum" in line for line in lines[:-1])
    assert not any("more operations" in line for line in O.render(res, top=3))


def test_device_name_comes_from_the_trace_header():
    assert O.gpu_name(_trace()) == "Test GPU" and O.gpu_name({"traceEvents": []}) is None


def test_command_line(tmp_path, capsys):
    trace_file, run_file, out = tmp_path / "t.json", tmp_path / "run.json", tmp_path / "ops.json"
    trace_file.write_text(json.dumps(_trace()))
    run_file.write_text(json.dumps({"meta": {"gpu": "Run GPU", "commit": "abc123", "dirty": True, "tag": "x",
                                             "dtype": "bf16", "batch_size": 8, "seq_len": 256},
                                    "config": {"run": {"device": "cuda"}},
                                    "trace": {"trace_file": str(trace_file)}}))
    assert O.main(["fwd:embed.ke", "bwd:embed", "--run", str(run_file), "--json", str(out)]) == 0
    text = capsys.readouterr().out
    assert f"trace:  {trace_file}" in text and "GPU:    Run GPU" in text and "abc123  (dirty tree" in text
    assert "B=8" in text and "aten::embedding_bag" in text and "bwd EmbeddingBagBackward0" in text
    data = json.loads(out.read_text())
    assert [r["region"] for r in data["regions"]] == ["fwd:embed.ke", "bwd:embed"]
    assert data["commit"] == "abc123" and len(data["regions"][0]["ops"]) == 3
    assert O.main(["fwd:nope", "--trace", str(trace_file)]) == 1            # a region not in the trace
    text = capsys.readouterr().out
    assert "GPU:    Test GPU" in text and "not in the last profiled step" in text
    with pytest.raises(SystemExit):
        O.main(["fwd:embed.ke"])                                            # neither --trace nor --run
