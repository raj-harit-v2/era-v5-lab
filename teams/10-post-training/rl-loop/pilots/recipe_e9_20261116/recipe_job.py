"""E9 (SFT arms -> RL screen) as a portable job: the same file runs on a Mac (MPS/CPU), on a Kaggle T4 and as a TSAI job
request.

    python recipe_job.py --config <cfg_e9_17b.yaml>
    python recipe_job.py e9 --model <dir or HF id> --revision <sha> --data <dir> --tasks cc.jsonl \
        --rung rung1_s128_ids.txt --rest rest_s32_ids.txt --device cuda --gpus 0,1 --out <dir>
    python recipe_job.py e9 --dry-run ...   (tiny, CPU-friendly)

E9 per arm (A0 base, A1 Dolly, A2 OCR-2 clean, A3 Dolly + OCR-2, A4 short answers): sft/bench/train.py (full FT, equal
steps and equal supervised tokens per update), then sft/bench/rl_screen.py (k samples at temperature 1, failure ladder,
mixed groups), then the bench's forgetting metric (evaluate.py --metrics forget). Every step leaves a done-marker, so a
rerun after a crash or a time limit continues where it stopped; e9_summary.json is rewritten after every finished arm.
--gpus 0,1 runs arms in parallel, one per GPU.

Data (dolly.tok.jsonl, ocr2_clean.tok.jsonl, task records, id lists) is private: it is passed in, never fetched here.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[2]
BENCH = TEAM / "sft" / "bench"
ARMS = {"A1": "dolly.tok.jsonl", "A2": "ocr2_clean.tok.jsonl", "A3": "mix.tok.jsonl",
        "A2v2": "ocr2_clean_v2.tok.jsonl",   # A2 minus the 72 rows that share a problem family with an eval problem
        "A4": "ocr2_short_v2.tok.jsonl"}     # A2v2 with the reasoning block deleted (code-only answers)



def log(msg: str, out: Path) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(out / "job.log", "a") as f:
        f.write(line + "\n")


def run(cmd: list[str], logf: Path, env: dict | None = None) -> int:
    with open(logf, "a") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})}).returncode


def runner_env(a) -> dict | None:
    return {"G10_STDIO_RUNNER": a.stdio_runner} if a.stdio_runner else None


def resolve_model(model: str, revision: str | None) -> Path:
    if Path(model).is_dir():
        return Path(model)
    from huggingface_hub import snapshot_download  # noqa: PLC0415
    return Path(snapshot_download(model, revision=revision, allow_patterns=["*.json", "*.safetensors", "*.txt"]))


# ---------------------------------------------------------------- E9

def e9_arm(a, arm: str, base: Path, out: Path, gpu: str | None) -> dict:
    env = {"CUDA_VISIBLE_DEVICES": gpu} if gpu is not None else {}
    if a.stdio_runner:
        env["G10_STDIO_RUNNER"] = a.stdio_runner
    rd = out / arm
    rd.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    res = {"arm": arm}
    model_dir = base
    if arm != "A0":
        model_dir = rd / "model"
        if not (rd / "train.done").exists():
            cmd = [py, str(BENCH / "train.py"), "--train", str(Path(a.data) / ARMS[arm]), "--model", str(base),
                   "--revision", "none", "--tokenizer-dir", str(base), "--method", "full", "--steps", str(a.steps),
                   "--warmup", str(min(10, max(1, a.steps // 10))), "--lr", str(a.lr), "--batch-target-tokens",
                   str(a.batch_target_tokens), "--micro-tokens", str(a.micro_tokens), "--device", a.device,
                   "--seed", str(a.seed), "--log-every", "10", "--save-every", "10", "--out", str(rd)]
            if a.method != "full":  # e.g. the Kaggle T4 variant at 1.7B: LoRA + the chat-marker rows (a method change)
                cmd[cmd.index("--method") + 1] = a.method
                cmd += ["--lora-r", str(a.lora_r), "--marker-lr", str(a.marker_lr), "--train-marker-rows", "--wd", "0"]
            if a.grad_ckpt:
                cmd.append("--grad-checkpointing")
            if a.autocast != "none":
                cmd += ["--autocast", a.autocast]
            log(f"E9 {arm} train start", out)
            if run(cmd, rd / "train.log", env):
                return {**res, "error": "train failed (see train.log)"}
            (rd / "train.done").touch()
        res["train_report"] = str(rd / "train_report.json")
    if not (rd / "screen.done").exists():
        cmd = [py, str(BENCH / "rl_screen.py"), "--model", str(model_dir), "--tasks", a.tasks, "--set", f"rung1={a.rung}",
               "--set", f"rest={a.rest}", "--k", str(a.k), "--temperature", "1", "--max-new", str(a.max_new),
               "--seqs-per-batch", str(a.gen_batch), "--workers", str(a.workers), "--seed", str(a.seed),
               "--device", a.device, "--out", str(rd / "screen")]
        if a.limit:
            cmd += ["--limit", str(a.limit)]
        if a.static_cache:
            cmd.append("--static-cache")
        cmd += ["--dtype", a.screen_dtype, "--kv-cache-gb", str(a.kv_cache_gb), "--decode-loop", a.decode_loop, "--attn", a.attn]
        log(f"E9 {arm} screen start", out)
        if run(cmd, rd / "screen.log", env):
            return {**res, "error": "screen failed (see screen.log)"}
        (rd / "screen.done").touch()
    res["screen_report"] = str(rd / "screen" / "screen_report.json")
    if a.forget and not (rd / "forget.json").exists():
        cmd = [py, str(BENCH / "evaluate.py"), "--model", str(model_dir), "--revision", "none", "--metrics", "forget",
               "--device", a.device, "--token-budget", "16384", "--out", str(rd / "forget.json")]
        log(f"E9 {arm} forget start", out)
        run(cmd, rd / "forget.log", env)
    log(f"E9 {arm} done", out)
    return res


def e9(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.dry_run:  # tiny everything; proves the commands, the files and the resume markers, not a result
        a.steps, a.batch_target_tokens, a.limit, a.k, a.max_new, a.gen_batch, a.forget = 2, 512, 2, 2, 16, 4, False
    base = resolve_model(a.model, a.revision)
    arms = a.arms.split(",")
    gpus = a.gpus.split(",") if a.gpus else [None]
    log(f"E9 start model={base} arms={arms} gpus={gpus} device={a.device}", out)
    t0 = time.time()
    import queue  # noqa: PLC0415
    free: queue.Queue = queue.Queue()
    for g in gpus:
        free.put(g)

    done_arms: list[dict] = []
    lock = threading.Lock()

    def write_summary(results: list[dict], final: bool) -> None:
        for r in results:
            p = Path(r.get("screen_report", ""))
            if p.is_file():
                rep = json.loads(p.read_text())
                r["brief"] = {s: {"ladder": {k: v["share"] for k, v in d["ladder"].items()},
                                  "mixed": d.get("groups_pass_kept", {}).get("mixed_share")} for s, d in rep["sets"].items()}
        (out / "e9_summary.json").write_text(json.dumps(
            {"arms": results, "arms_requested": arms, "complete": final, "seconds": round(time.time() - t0, 1),
             "dry_run": a.dry_run}, indent=1))

    def on_free_gpu(arm):  # an arm takes whichever GPU is free and gives it back: never two arms on one GPU
        g = free.get()
        try:
            res = e9_arm(a, arm, base, out, g)
        finally:
            free.put(g)
        with lock:  # a partial e9_summary.json after every arm, so a job killed at its time limit still reports the arms it finished
            done_arms.append(res)
            write_summary(list(done_arms), final=False)
        return res
    with ThreadPoolExecutor(len(gpus)) as ex:
        jobs = [ex.submit(on_free_gpu, arm) for arm in arms]
        results = [j.result() for j in jobs]
    write_summary(results, final=True)
    log(f"E9 end {json.dumps({r['arm']: r.get('brief', r.get('error')) for r in results})}", out)
    return 0 if all("error" not in r for r in results) else 1



def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("e9")
    e.add_argument("--model", required=True)
    e.add_argument("--revision")
    e.add_argument("--data", required=True, help="folder with dolly.tok.jsonl, ocr2_clean.tok.jsonl[, mix.tok.jsonl]")
    e.add_argument("--arms", default="A2,A1,A0")
    e.add_argument("--steps", type=int, default=150)
    e.add_argument("--batch-target-tokens", type=int, default=8000)
    e.add_argument("--lr", type=float, default=1e-4)
    e.add_argument("--micro-tokens", type=int, default=2048)
    e.add_argument("--grad-ckpt", action="store_true")
    e.add_argument("--autocast", default="none", choices=("none", "bf16"))
    e.add_argument("--rung", required=True)
    e.add_argument("--rest", required=True)
    e.add_argument("--limit", type=int, default=0)
    e.add_argument("--k", type=int, default=8)
    e.add_argument("--max-new", type=int, default=1024)
    e.add_argument("--gen-batch", type=int, default=64)
    e.add_argument("--static-cache", action="store_true")
    e.add_argument("--decode-loop", choices=("hf", "custom"), default="custom",
                   help="custom: finished rows are dropped, sampled ids equal HF generate's (tests + 17 Nov T4 runs)")
    e.add_argument("--attn", choices=("sdpa", "gqa_decode"), default="sdpa",
                   help="gqa_decode: grouped one-token attention, 3x on GQA models like SmolLM2-360M; no gain on MHA (1.7B)")
    e.add_argument("--no-forget", dest="forget", action="store_false")
    e.add_argument("--gpus", default="")
    e.add_argument("--method", default="full", choices=("full", "lora"))
    e.add_argument("--lora-r", type=int, default=4)
    e.add_argument("--marker-lr", type=float, default=1e-4)
    e.add_argument("--screen-dtype", default="float32", choices=("float32", "bfloat16"))
    e.add_argument("--kv-cache-gb", type=float, default=3.0, help="rl_screen KV-cache budget per batch (A100: 30)")
    for p in (e,):
        p.add_argument("--tasks", required=True)
        p.add_argument("--device", default="cuda")
        p.add_argument("--seed", type=int, default=1)
        p.add_argument("--workers", type=int, default=2)
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--stdio-runner", default="", help="G10_STDIO_RUNNER for the reward: docker (default) | local "
                       "(Linux, root: per-uid isolation, no Docker)")
        p.add_argument("--out", required=True)
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--config"]:  # TSAI job-request form: one YAML holds the subcommand and every option
        import yaml  # noqa: PLC0415
        cfg = yaml.safe_load(Path(argv[1]).read_text())
        argv = [cfg.pop("cmd")] + [x for k, v in cfg.items() for x in (
            [f"--{k.replace('_', '-')}"] if v is True else [] if v is False or v is None else [f"--{k.replace('_', '-')}", str(v)])]
    a = ap.parse_args(argv)
    (Path(a.out)).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "job_args.json").write_text(json.dumps(vars(a), indent=1))
    return e9(a)


if __name__ == "__main__":
    raise SystemExit(main())
