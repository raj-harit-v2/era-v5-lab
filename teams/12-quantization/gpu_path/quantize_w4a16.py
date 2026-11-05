#!/usr/bin/env python3
"""Quantize OLMoE to W4A16 with llm-compressor (GPTQ, 4-bit weights, group 128) for vLLM.

    python quantize_w4a16.py --model-dir <bf16 snapshot> --out <out_dir> [--method gptq|rtn]
        [--samples 256] [--seq-len 1024]

Runs in its own environment (llmcompressor brings its own torch and transformers).
- Weights of every Linear become 4-bit integers with one scale per 128 inputs (compressed-tensors `pack-quantized`);
  activations stay 16-bit (A16), so it runs on GPUs without FP8 (T4, P100, L4 and A100 all work).
- `lm_head` and the 16 router gates (`mlp.gate`, OLMoE's module name) are left out and stay BF16 (G12 rule).
- GPTQ needs calibration text: the first --samples documents of fineweb-edu sample-10BT with at least
  --seq-len tokens, cut to --seq-len. It is web text, not any eval_mini benchmark, so it does not leak the eval.
  With 64 experts and top-8 routing each expert sees about 1/8 of the calibration tokens (about 33k at the defaults).
- --method rtn is the fallback without calibration (round to nearest, same scheme), if GPTQ fails on an expert.
Writes <out>/ (the model, for vLLM) and <out>/quantize_meta.json (method, settings, time, versions, GPU).
Check the result with model_check.py --expect-quantized.
"""
from __future__ import annotations

import argparse, json, platform, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

IGNORE = ["lm_head", "re:.*mlp.gate$"]          # output layer and router stay BF16
CALIB = ("HuggingFaceFW/fineweb-edu", "sample-10BT")


def gpu() -> str:
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                              capture_output=True, text=True, check=True).stdout.strip().replace("\n", " + ")
    except (OSError, subprocess.CalledProcessError):
        return platform.processor() or platform.machine()


def calibration(tokenizer, n: int, seq_len: int):
    from datasets import Dataset, load_dataset

    stream = load_dataset(*CALIB, split="train", streaming=True)
    rows = []
    for doc in stream:
        ids = tokenizer(doc["text"], add_special_tokens=False)["input_ids"]
        if len(ids) >= seq_len:
            rows.append({"input_ids": ids[:seq_len], "attention_mask": [1] * seq_len})
            if len(rows) == n:
                break
    return Dataset.from_list(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", required=True, type=Path, help="local bf16 snapshot of the model")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--method", choices=["gptq", "rtn"], default="gptq")
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--seq-len", type=int, default=1024)
    ap.add_argument("--model", default="allenai/OLMoE-1B-7B-0924")
    ap.add_argument("--revision", default="6d84c48581ece794365f2b8e9cfb043c68ade9c5")
    args = ap.parse_args()

    import compressed_tensors, llmcompressor, torch, transformers
    from llmcompressor import oneshot
    from llmcompressor.modifiers.quantization import GPTQModifier, QuantizationModifier
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # loaded on the CPU in bf16: llm-compressor moves one decoder layer at a time to the GPU for calibration
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, torch_dtype="auto")
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    if args.method == "gptq":
        recipe = GPTQModifier(targets="Linear", scheme="W4A16", ignore=IGNORE)
        t = time.perf_counter()
        ds = calibration(tokenizer, args.samples, args.seq_len)
        calib_s = time.perf_counter() - t
        t = time.perf_counter()
        oneshot(model=model, dataset=ds, recipe=recipe, max_seq_length=args.seq_len, num_calibration_samples=len(ds))
    else:
        recipe = QuantizationModifier(targets="Linear", scheme="W4A16", ignore=IGNORE)
        calib_s = 0.0
        t = time.perf_counter()
        oneshot(model=model, recipe=recipe)
    quant_s = time.perf_counter() - t

    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out, save_compressed=True)
    tokenizer.save_pretrained(args.out)
    meta = {
        "model": args.model, "revision": args.revision, "method": args.method, "scheme": "W4A16",
        "group_size": 128, "ignore": IGNORE,
        "calibration": None if args.method == "rtn" else {
            "dataset": "/".join(CALIB), "samples": args.samples, "seq_len": args.seq_len, "prepare_s": round(calib_s, 1)},
        "quant_time_s": round(quant_s, 1), "gpu": gpu(),
        "versions": {"llmcompressor": llmcompressor.__version__, "compressed_tensors": compressed_tensors.__version__,
                     "transformers": transformers.__version__, "torch": torch.__version__,
                     "python": platform.python_version()},
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (args.out / "quantize_meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
