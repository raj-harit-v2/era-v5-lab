#!/usr/bin/env python3
"""Checks for model_check.py and add_runs_rows.py on made-up safetensors headers (no GPU, no torch).

    python test_gpu_path.py        (or: python -m pytest test_gpu_path.py)
"""
from __future__ import annotations

import json, struct, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import add_runs_rows, model_check  # noqa: E402

LAYERS, EXPERTS, HID, FF = 2, 4, 256, 128   # big enough that data, not the header, sets the size


def write_st(path: Path, tensors: dict) -> None:
    """A valid safetensors file: 8-byte header length, JSON header, zero-filled data."""
    header, off = {}, 0
    for name, (dtype, shape, nbytes) in tensors.items():
        header[name] = {"dtype": dtype, "shape": shape, "data_offsets": [off, off + nbytes]}
        off += nbytes
    raw = json.dumps(header).encode()
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + b"\0" * off)


def model(d: Path, quantized: bool, router="BF16", skip_experts=False) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    ts = {"model.embed_tokens.weight": ("BF16", [16, HID], 16 * HID * 2), "lm_head.weight": ("BF16", [16, HID], 16 * HID * 2)}
    lins = [f"model.layers.{l}.self_attn.{p}" for l in range(LAYERS) for p in ("q_proj", "k_proj", "v_proj", "o_proj")]
    exps = [f"model.layers.{l}.mlp.experts.{e}.{p}" for l in range(LAYERS) for e in range(EXPERTS)
            for p in ("gate_proj", "up_proj", "down_proj")]
    for l in range(LAYERS):
        ts[f"model.layers.{l}.mlp.gate.weight"] = (router, [EXPERTS, HID], EXPERTS * HID * 2)
    for name in lins + exps:
        if quantized and not (skip_experts and ".experts." in name):
            ts[f"{name}.weight_packed"] = ("I32", [FF, HID // 8], FF * HID // 2)
            ts[f"{name}.weight_scale"] = ("BF16", [FF, 1], FF * 2)
            ts[f"{name}.weight_shape"] = ("I64", [2], 16)
        else:
            ts[f"{name}.weight"] = ("BF16", [FF, HID], FF * HID * 2)
    write_st(d / "model.safetensors", ts)
    (d / "config.json").write_text("{}")
    return d


def test_bf16_ok():
    with tempfile.TemporaryDirectory() as t:
        info = model_check.check(model(Path(t) / "bf16", False))
        assert info["router_dtypes"] == ["BF16"] and info["router_tensors"] == LAYERS
        assert info["output_dtype"] == "BF16" and info["experts_packed"] == 0
        assert info["experts_linear"] == LAYERS * EXPERTS * 3 and info["attn_linear"] == LAYERS * 4
        assert model_check.problems(info, expect_quantized=False) == []
        assert model_check.problems(info, expect_quantized=True)          # bf16 is not quantized


def test_quantized_ok_and_bpw():
    with tempfile.TemporaryDirectory() as t:
        base = model(Path(t) / "bf16", False)
        q = model(Path(t) / "q", True)
        params = model_check.n_params(model_check.tensors(base))
        info = model_check.check(q, params)
        assert info["experts_packed"] == info["experts_linear"] == LAYERS * EXPERTS * 3
        assert info["attn_packed"] == info["attn_linear"] == LAYERS * 4
        assert model_check.problems(info, expect_quantized=True) == []
        assert info["bpw"] < model_check.check(base)["bpw"]


def test_skipped_experts_fail():
    with tempfile.TemporaryDirectory() as t:
        info = model_check.check(model(Path(t) / "q", True, skip_experts=True))
        assert any("experts packed 0" in p for p in model_check.problems(info, expect_quantized=True))


def test_quantized_router_fails():
    with tempfile.TemporaryDirectory() as t:
        info = model_check.check(model(Path(t) / "q", True, router="I32"))
        assert any("router" in p for p in model_check.problems(info, expect_quantized=True))


def test_manifest_hashes_every_file():
    with tempfile.TemporaryDirectory() as t:
        d = model(Path(t) / "q", True)
        m = model_check.manifest(d, "W4A16", model_check.check(d))
        assert {f["file"] for f in m["files"]} == {"model.safetensors", "config.json"}
        assert all(len(f["sha256"]) == 64 for f in m["files"])


def fake_summary(limit_scale=1):
    recs = []
    for task, metric, filt in [("arc_challenge", "acc_norm", "none"), ("hellaswag", "acc_norm", "none"),
                               ("mmlu", "acc", "none"), ("gsm8k", "exact_match", "flexible-extract"),
                               ("truthfulqa_mc2", "acc", "none")]:
        lim = add_runs_rows.FULL[task] // limit_scale
        recs.append({"task": task, "metric": metric, "filter": filt, "primary": True, "value": 0.5, "limit": lim,
                     "n_items": lim * (57 if task == "mmlu" else 1), "wall_clock_s": 100.0, "run_date": "2026-11-03"})
    meta = {"format": "W4A16", "model": "allenai/OLMoE-1B-7B-0924", "model_revision": "6d84c48581ece794",
            "backend": "vLLM 0.0.0 via lm_eval VLLM (prompt_logprobs)", "dtype": "float16", "tensor_parallel": 2,
            "max_model_len": 2048, "lm_eval": "0.4.13", "hardware": "Tesla T4 x2", "gen_tok_s": 50.0,
            "quantize_meta": {"method": "gptq", "quant_time_s": 3600.0,
                              "versions": {"llmcompressor": "0.0", "compressed_tensors": "0.0"},
                              "calibration": {"samples": 256, "seq_len": 1024, "dataset": "x/y"}}}
    return {"run_meta": meta, "records": recs}


MAN = {"label": "W4A16", "_path": "results/manifest_W4A16.json",
       "check": {"bpw": 4.6, "size_gb": 4.0, "router_dtypes": ["BF16"], "output_dtype": "BF16"}}


def test_row():
    r = add_runs_rows.row(fake_summary(), MAN)
    assert list(r) == add_runs_rows.FIELDS
    assert r["n_items"] == 1870 and r["score"] == 0.5 and r["eval_time_s"] == 500
    assert r["router_type"] == "BF16" and r["runtime"] == "vLLM 0.0.0" and "GPTQ" in r["notes"]


def test_row_refuses_test_runs():
    try:
        add_runs_rows.row(fake_summary(limit_scale=100), MAN)
    except SystemExit as e:
        assert "test limit" in str(e)
    else:
        raise AssertionError("a limited run was accepted")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
