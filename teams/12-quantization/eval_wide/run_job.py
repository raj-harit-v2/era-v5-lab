#!/usr/bin/env python3
"""One command for the TSAI job: convert, quantize, guard-test and run the wide pass on every format, then pair.

    python teams/12-quantization/eval_wide/run_job.py --model-dir ./inputs/sarvam-1 --hf-home ./inputs/hf_home \
        --llama-dir ./work/llama.cpp-b11669 --convert-python ./work/.venv-convert/bin/python \
        --formats bf16 Q8_0 Q4_K_M Q3_K_M --work ./work --out ./out/wide-sarvam1 \
        --model sarvamai/sarvam-1 --revision e9607337286ddf496d4a2562b194e489dcf3feea

Offline: every child process gets HF_HUB_OFFLINE=1 and HF_DATASETS_OFFLINE=1 with HF_HOME at --hf-home, which
prepare_inputs.py filled once with network. No download, no key, no install happens here.

Steps (stops at the first non-zero exit code):
  1. bf16 GGUF from --model-dir with llama.cpp's converter (skipped when <work>/<name>-bf16.gguf exists);
  2. per format: llama-quantize (output layer Q8_0 below 8 bits, as quantize_eval.py and eval_wide.ipynb),
     test_llamacpp_lm.py (the shifted-logprob guard), run_wide_gguf.py; the quantized GGUF is deleted after;
  3. paired.py against bf16 -> <out>/paired.md; job.json with times, GGUF sha256 and sizes.
Results go only to --out (per-item rows, no item text: about 5 MB per format). --print-only shows the commands.
"""
from __future__ import annotations

import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MINI = HERE.parent / "eval_mini"
FORMATS = ("bf16", "Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", required=True, type=Path, help="HF snapshot of the model at --revision")
    ap.add_argument("--hf-home", required=True, type=Path, help="HF cache with the datasets (prepare_inputs.py)")
    ap.add_argument("--llama-dir", required=True, type=Path, help="llama.cpp checkout at b11669 (convert_hf_to_gguf.py)")
    ap.add_argument("--convert-python", required=True, help="python of the converter venv")
    ap.add_argument("--quantize", default="llama-quantize", help="llama-quantize binary at b11669")
    ap.add_argument("--formats", nargs="+", default=["bf16", "Q8_0", "Q4_K_M", "Q3_K_M"], choices=FORMATS)
    ap.add_argument("--g9-dir", type=Path, default=HERE.parents[1] / "09-evaluation" / "harness_code_indic")
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--cap", type=int, help="items per task (MMLU: per subject); default full splits")
    ap.add_argument("--tasks", nargs="+", help="subset of run_wide_gguf.WIDE (default: all), e.g. mmlu arc_challenge")
    ap.add_argument("--n-ctx", type=int, default=4096)
    ap.add_argument("--model", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--print-only", action="store_true", help="print the commands, run nothing")
    args = ap.parse_args()
    sys.path.insert(0, str(HERE))
    from run_wide_gguf import WIDE   # stdlib-only module top: no lm_eval import here
    if args.tasks and set(args.tasks) - set(WIDE):
        sys.exit(f"unknown tasks {sorted(set(args.tasks) - set(WIDE))}; choose from {sorted(WIDE)}")
    if args.formats[0] != "bf16":
        sys.exit("--formats must start with bf16: it is the base of the paired comparison and the source of the quants")

    env = {**os.environ, "HF_HOME": str(args.hf_home.resolve()), "HF_HUB_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
           "PYTHONUNBUFFERED": "1"}   # child output streams line by line into the log and the job's stdout
    env.pop("PYTHONPATH", None)
    py = sys.executable
    name = args.model.split("/")[-1]
    bf16 = args.work / f"{name}-bf16.gguf"
    logs = args.out / "logs"
    job = {"model": args.model, "revision": args.revision, "formats": args.formats, "cap": args.cap,
           "tasks": args.tasks or list(WIDE),
           "n_ctx": args.n_ctx, "started": datetime.datetime.now().isoformat(timespec="seconds"), "steps": {}}

    def run(label: str, cmd: list[str]) -> None:
        print("$", " ".join(cmd), flush=True)
        if args.print_only:
            return
        t0 = time.perf_counter()
        with open(logs / f"{label}.log", "w") as log:
            p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                sys.stdout.write(line); log.write(line)
            rc = p.wait()
        job["steps"][label] = {"rc": rc, "seconds": round(time.perf_counter() - t0, 1)}
        save()
        if rc:
            sys.exit(f"{label} failed (exit {rc}); see {logs / (label + '.log')}")

    def save() -> None:
        (args.out / "job.json").write_text(json.dumps(job, indent=1))

    if not args.print_only:
        for d in (args.work, logs):
            d.mkdir(parents=True, exist_ok=True)
        save()
    runs = args.out / "runs"

    if not bf16.exists():
        part = bf16.with_name(bf16.name + ".part")
        run("convert", [args.convert_python, str(args.llama_dir / "convert_hf_to_gguf.py"), str(args.model_dir),
                        "--outtype", "bf16", "--outfile", str(part)])
        if not args.print_only:
            part.rename(bf16)
    for fmt in args.formats:
        gguf = bf16 if fmt == "bf16" else args.work / f"{name}-{fmt}.gguf"
        if fmt != "bf16" and not gguf.exists():
            extra = [] if fmt == "Q8_0" else ["--output-tensor-type", "q8_0"]
            part = gguf.with_name(gguf.name + ".part")   # renamed only on success: a stopped job leaves no file to reuse
            run(f"quantize_{fmt}", [args.quantize, *extra, str(bf16), str(part), fmt])
            if not args.print_only:
                part.rename(gguf)
        run(f"test_llamacpp_lm_{fmt}", [py, str(MINI / "test_llamacpp_lm.py"), str(gguf)])
        run(f"run_{fmt}", [py, str(HERE / "run_wide_gguf.py"), "--gguf", str(gguf), "--format", fmt,
                           "--out", str(runs), "--g9-dir", str(args.g9_dir), "--model", args.model,
                           "--revision", args.revision, "--n-ctx", str(args.n_ctx)]
            + (["--cap", str(args.cap)] if args.cap else []) + (["--tasks", *args.tasks] if args.tasks else []))
        if not args.print_only:
            job.setdefault("gguf", {})[fmt] = {"file": gguf.name, "bytes": gguf.stat().st_size, "sha256": sha256(gguf)}
            save()
            if fmt != "bf16":
                gguf.unlink()
    if len(args.formats) > 1:
        run("paired", [py, str(HERE / "paired.py"), str(runs), "--base", "bf16", "--out", str(args.out / "paired.md")])
    if not args.print_only:
        job["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
        save()
        print("done:", args.out)


if __name__ == "__main__":
    main()
