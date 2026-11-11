"""Optional, bounded GPU fit check; synthetic data, never a quality comparison.

Run after the notebook prepares its pinned repository and input assets:
    python full_shape_probe.py --workspace /path/to/attention-smoke-lab

Each design gets three steps at the original context/global/microbatch sizes.
The existing trainer and all approval checks remain unchanged.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from tokenizers import Tokenizer


CASES = {
    "attn-0": "t2.yaml",
    "attn-1": "attn1_mqa.yaml",
    "attn-2": "attn2_swa128_sink.yaml",
    "attn-3": "attn3_prope_half.yaml",
    "attn-4": "attn4_gate.yaml",
}
SOURCE_COMMIT = "c9cac5a0d5811e712212a37a01d6c540346ff1a1"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def gpu_memory_mib():
    """Sample total device use; includes runtime overhead and other GPU users."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True, timeout=5,
    )
    return int(result.stdout.splitlines()[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    repo = workspace / "era-v5-lab"
    inputs = workspace / "inputs"
    output = workspace / "full-shape-probe"
    if output.exists():
        raise FileExistsError(f"Preserve existing evidence; choose a fresh workspace: {output}")
    actual_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    if actual_commit != SOURCE_COMMIT:
        raise ValueError("The probe requires the notebook's reviewed source commit")
    output.mkdir()

    tokenizer = Tokenizer.from_file(str(inputs / "tokenizer_v0.json"))
    sentence = "A blue bird follows the river while a small boat waits beside the bridge. "
    text = sentence * 220
    token_count = len(tokenizer.encode(text, add_special_tokens=False).ids)
    assert token_count > 2048, "The fixture must fill the original sequence length"
    train_path = output / "synthetic-long-train.jsonl"
    with train_path.open("w", encoding="utf-8") as stream:
        for index in range(8):
            stream.write(json.dumps({"id": f"synthetic-long-{index}", "text": text}) + "\n")
    write_json(output / "fixture.json", {
        "synthetic": True, "documents": 8, "tokens_per_document": token_count,
        "train_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
        "heldout_note": "Short synthetic notebook holdout; no official evaluation cost measured",
        "memory_method": "Maximum sampled total device memory, nvidia-smi every 0.5 seconds",
    })

    harness = repo / "teams/05-architecture/harness"
    environment = {
        **os.environ, "PYTHONPATH": str(harness), "OMP_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4", "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    }
    results = []
    for name, config in CASES.items():
        run_dir = output / name
        command = [
            sys.executable, str(harness / "train_week2.py"),
            "--config", str(repo / "teams/05-architecture/configs/arms" / config),
            "--tokenizer", str(inputs / "tokenizer_v0.json"),
            "--byte-table", str(inputs / "tables/raw_table_P32.npz"),
            "--train-data", str(train_path),
            "--heldout-data", str(inputs / "synthetic_heldout.jsonl"),
            "--device", "cuda", "--seed", "1234", "--smoke", "--smoke-steps", "3",
            "--no-checkpoint", "--out", str(run_dir),
        ]
        # No sequence/batch overrides: context 2048, global batch 8, microbatch 1.
        write_json(output / f"{name}-command.json", {"command": command, "source": SOURCE_COMMIT})
        samples = []
        started = time.monotonic()
        with (output / f"{name}.log").open("w") as log:
            process = subprocess.Popen(command, cwd=repo, env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    samples.append(gpu_memory_mib())
                    if time.monotonic() - started > 300:
                        raise TimeoutError("Three-step probe exceeded five minutes")
                    time.sleep(0.5)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
        if process.returncode:
            raise RuntimeError(f"{name} failed; inspect {output / (name + '.log')}")

        manifest = json.loads((run_dir / "manifest.json").read_text())
        summary = json.loads((run_dir / "summary.json").read_text())
        metrics = [json.loads(line) for line in (run_dir / "metrics.jsonl").read_text().splitlines()]
        training = [row for row in metrics if "train/ce_loss" in row]
        cfg = manifest["config"]
        assert cfg["model"]["block_size"] == 2048
        assert (cfg["run"]["batch_size"], cfg["run"]["micro_batch_size"]) == (8, 1)
        assert len(training) == 3 and summary["steps"] == 3
        assert manifest["smoke"] and not summary["eligible_for_quality_comparison"]
        assert all(row["train/input_positions"] == 8 * 2048 for row in training)
        assert all(math.isfinite(row[key]) for row in training
                   for key in ("train/ce_loss", "gradient_norm", "perf/step_ms"))
        results.append({
            "design": name, "steps": 3, "context": 2048, "global_batch": 8,
            "microbatch": 1, "seed": 1234, "dtype": cfg["run"]["dtype"],
            "step_seconds": [row["perf/step_ms"] / 1000 for row in training],
            "median_step_seconds": statistics.median(row["perf/step_ms"] / 1000 for row in training),
            "max_sampled_device_memory_mib": max(samples) if samples else None,
            "wall_seconds": time.monotonic() - started,
            "quality_result": False,
        })
        write_json(output / "probe-summary.json", results)
        print(json.dumps(results[-1]), flush=True)


if __name__ == "__main__":
    main()
