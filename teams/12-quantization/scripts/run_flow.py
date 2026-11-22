#!/usr/bin/env python3
"""The dry run 1 job as one command: quantize_eval.py, then flow_fixed_prompts.py on the GGUFs it built. Stops at the first non-zero exit.

    python teams/12-quantization/scripts/run_flow.py --checkpoint ./out/dryrun1-1234 --tokenizer ./inputs/tokenizer.json \\
        --eval teams/12-quantization/prompts/eval_own_20.json --work ./work --out ./out \\
        [--manifest teams/10-post-training/eval/effort_manifest.json --source-dir code_contests=<dir> --source-dir hendrycks_math=<dir>]

Writes <out>/runs.csv, <out>/scores.json (and runs/manifest_<date>.json beside them) and <out>/prompts/. The GGUF files in --work are
deleted at the end. Every other option of quantize_eval.py (--roundtrip, --limit, --llama-bin ...) is passed on with --qe-args.
"""
from __future__ import annotations

import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMATS = ["bf16", "Q8_0", "Q4_K_M"]


def commands(a: argparse.Namespace, extra: list[str]) -> list[list[str]]:
    py, out = sys.executable, Path(a.out)
    qe = [py, str(HERE / "quantize_eval.py"), "--checkpoint", a.checkpoint, "--tokenizer", a.tokenizer, "--eval", a.eval,
          "--formats", ",".join(FORMATS), "--work", a.work, "--runs-csv", str(out / "runs.csv"),
          "--scores-out", str(out / "scores.json"), *extra]
    if a.tokenizer_sha256:
        qe += ["--tokenizer-sha256", a.tokenizer_sha256]
    flow = [py, str(HERE / "flow_fixed_prompts.py"), "--gguf-dir", a.work, "--formats", ",".join(FORMATS[1:]),
            "--scores", str(out / "scores.json"), "--out", str(out / "prompts"), "--delete-ggufs"]
    if a.manifest:
        flow += ["--manifest", a.manifest, *[x for d in a.source_dir for x in ("--source-dir", d)]]
    return [qe, flow]


def run_all(cmds: list[list[str]], runner=subprocess.run) -> int:
    for c in cmds:
        print("$", " ".join(c), flush=True)
        code = runner(c).returncode
        if code:
            print(f"stopped: exit code {code} from {Path(c[1]).name}", file=sys.stderr)
            return code
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--tokenizer-sha256", help="default: quantize_eval.py's (the frozen p1536)")
    ap.add_argument("--eval", required=True, help="eval items JSON for the scores")
    ap.add_argument("--work", required=True, help="quantize_eval.py's --work (llama.cpp-b11669/, .venv-convert/ prepared)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--manifest", help="Team 10's effort_manifest.json (needs --source-dir)")
    ap.add_argument("--source-dir", action="append", default=[], metavar="KEY=DIR")
    ap.add_argument("--qe-args", nargs=argparse.REMAINDER, default=[], help="the rest of the line goes to quantize_eval.py")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    sys.exit(run_all(commands(a, a.qe_args)))


if __name__ == "__main__":
    main()
