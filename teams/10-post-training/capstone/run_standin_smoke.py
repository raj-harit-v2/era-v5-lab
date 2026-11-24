"""Executable Stand-in Smoke Runner for Dry Run 2 DT vs LoRA vs Full FT.

Runs the complete 3-arm comparison pipeline in stand-in / preflight mode ahead of D5
(when Team 5 delivers the actual Dry Run 2 checkpoint).
Generates the required stand-in test log, compare.md, and compare.json directly into
the target output folder (e.g., Google Drive MyDrive/dry-run-2-DT-LoRA-FullFT).

Usage:
    python teams/10-post-training/capstone/run_standin_smoke.py \
        --out /content/drive/MyDrive/dry-run-2-DT-LoRA-FullFT/out \
        --keep-canary-state-dir /content/drive/MyDrive/dry-run-2-DT-LoRA-FullFT/keep_canary
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM10 = HERE.parent
sys.path.insert(0, str(TEAM10 / "rl-loop"))
sys.path.insert(0, str(HERE))

import dryrun2_dt_compare as cmp
import make_adapter_config
import sft_job_v1 as job
import sft_slice_v1 as sl


def main():
    parser = argparse.ArgumentParser(description="Run stand-in smoke comparison for Dry Run 2.")
    parser.add_argument("--out", type=Path, default=Path("out/standin_smoke"), help="Output directory")
    parser.add_argument("--keep-canary-state-dir", type=Path, default=None, help="Canary directory")
    parser.add_argument("--keep-weights-dir", type=Path, default=None, help="Team 7 weights directory")
    parser.add_argument("--steps", type=int, default=42, help="Stand-in matched steps per arm")
    args = parser.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    canary = args.keep_canary_state_dir
    if canary:
        canary.mkdir(parents=True, exist_ok=True)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}] Starting Dry Run 2 Stand-in Smoke Preflight...")
    print(f"Target Output Directory: {out.resolve()}")
    if canary:
        print(f"Canary Target Directory: {canary.resolve()}")

    # 1. Setup mock pins and input generators for preflight validation
    def fake_build(packs, tok, tab, max_tokens, out_dir, dev_rows, check_hashes=True):
        out_dir.mkdir(parents=True, exist_ok=True)
        for n in ("a2_train.jsonl", "a4_train.jsonl", "dev.jsonl"):
            (out_dir / n).write_text('{"prompt": "mock", "target": "mock"}\n', encoding="utf-8")
        return {"train_rows": 100, "dev_rows": dev_rows}

    def fake_run_arm(out_dir, arm, cmd, timeout=None, canary_dest=None):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}] Executing stand-in SFT Arm: {arm} (steps={args.steps})...")
        d = out_dir / f"sft_{arm}"
        d.mkdir(parents=True, exist_ok=True)
        delta = {"full": 0.0482, "lora": 0.0315, "dt": 0.0194}[arm]
        eval_nll = {"full": 1.782, "lora": 1.845, "dt": 1.862}[arm]
        fmt_val = {"full": 0.88, "lora": 0.82, "dt": 0.78}[arm]
        rep = {
            "log": [{"step": i + 1, "loss": round(2.5 - (i * 0.02), 4)} for i in range(args.steps)],
            "train_seconds": 2.4,
            "before": {"eval_loss": {"nll_per_target": 2.650}, "forgetting": {"val/bpb": 1.0981}},
            "after": {
                "eval_loss": {"nll_per_target": eval_nll},
                "forgetting": {"val/bpb": round(1.0981 + delta, 4)},
                "generation": {"format_validity": fmt_val, "closed_im_end": 0.92, "hit_budget": 0.0, "mean_gen_tokens": 45.0},
            },
            "method_info": {
                "band_at_init": {"in_band_frac": 0.992},
                "deletion_final": {"deleted_frac": 0.148, "target": "g5_gate"},
            },
        }
        (d / "sft_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")

        # Emulate DT canary state generation if requested
        if arm == "dt" and canary_dest:
            canary_dest.mkdir(parents=True, exist_ok=True)
            (canary_dest / "model.safetensors").write_bytes(b"MOCK_STANDIN_DT_WEIGHTS")
            (canary_dest / "dt_keep_masks.bin").write_bytes(b"MOCK_STANDIN_DT_MASKS")
            (canary_dest / "dt_keep_masks.bin.json").write_text(json.dumps(rep["method_info"]), encoding="utf-8")
            (canary_dest / "SHA256SUMS").write_text(
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  model.safetensors\n"
            )
            print(f"Wrote DT canary files to {canary_dest}")

        return {"ok": True, "steps_completed": args.steps, "before": rep["before"]}

    # Patch stand-in preflight behaviors
    cmp.probe.check_pins = lambda *a: {"checks": {"tokenizer_sha256": {"match": True}, "table_content_sha256": {"match": True}}}
    cmp.job.check_run_and_inputs = lambda a: {"block_size": 2048, "inputs_present": ["standin_mock"]}
    cmp.job.check_g5_sources = lambda a: {}
    cmp.job.run_arm = fake_run_arm
    sl.build = fake_build
    make_adapter_config.write_config = lambda out_path, *a, **kw: out_path

    try:
        import torch
        device_val = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device_val = "cpu"

    cli_args = [
        "--g5-root", str(TEAM10.parent / "05-architecture"),
        "--run-folder", str(out),
        "--tokenizer", str(TEAM10 / "chat-format" / "chat_format_v0.md"),
        "--byte-table", str(TEAM10 / "chat-format" / "render.py"),
        "--heldout", str(TEAM10.parent / "05-architecture" / "heldout_v1"),
        "--packs", str(TEAM10 / "results" / "swe_e2e.md"),
        "--steps", str(args.steps),
        "--device", device_val,
        "--out", str(out),
    ]
    if canary:
        cli_args.extend(["--keep-canary-state-dir", str(canary)])
    if args.keep_weights_dir:
        cli_args.extend(["--keep-weights-dir", str(args.keep_weights_dir)])

    parsed = cmp.parse_args(cli_args)
    rc = cmp.run(parsed, out)

    if rc == 0:
        print("\n" + "=" * 65)
        print("PREFLIGHT STAND-IN RUN COMPLETE (SUCCESS)")
        print("=" * 65)
        compare_md = out / "compare.md"
        if compare_md.is_file():
            print("\n" + compare_md.read_text(encoding="utf-8"))
        print("=" * 65)
        print(f"Results and summary JSON written to: {out}")
        return 0
    else:
        print(f"Preflight failed with exit code {rc}", file=sys.stderr)
        return rc


if __name__ == "__main__":
    sys.exit(main())
