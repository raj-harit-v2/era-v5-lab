"""DT vs full FT vs LoRA on a size ladder (job 2026-11-23-g10-dt-large-model): train and evaluate every arm of every size.

    python teams/10-post-training/dt/run_ladder.py --config teams/10-post-training/dt/ladder_qwen3.yaml

Each arm calls sft/bench/train.py and then sft/bench/evaluate.py (test split: target bpb, format, forgetting) as
subprocesses with G10_SURROGATE_PROFILE set from the config, so the marker map is the same in every process. Settings
of each arm are in the config; nothing is tuned here.

Order and recovery: sizes and arms run in config order. After every arm `<out>/ladder_summary.json` is rewritten
(`complete: false` until the last arm), so a time limit still returns the finished arms. An arm with
`<out>/<size>/<arm>/DONE` is skipped on a rerun; train.py's own `--save-every` state resumes full/LoRA arms mid-run
(train.py does not implement it for DT, which restarts). A failed arm (non-zero exit, out of memory, failed check) is
recorded with the tail of its log and the ladder goes on. With `oom_retry: true` a training arm that fails with CUDA
out of memory is retried once at half `micro_tokens` (recorded as `train.oom_retry` in the summary): the same rows per
step and the same gradient, split into more micro-batches; DT's Wanda calibration batches are re-planned the same way. With `keep_models: false` the saved model folder of an arm
is deleted after its evaluation succeeded (8B in FP32 is 33 GB per arm); the DT mask files are kept.

`dry_run: true` builds a tiny random model with the same architecture class and the real tokenizer (CPU), and shrinks
steps, rows and evaluation so every arm and the whole evaluation path run in minutes. It proves the commands, the files
and the bookkeeping, not any number.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent  # teams/10-post-training
REPO = PKG.parent.parent


def load_config(path: str) -> dict:
    import yaml

    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("profile", "slice_dir", "out", "sizes", "train_common", "eval_common"):
        if key not in cfg:
            raise SystemExit(f"config {path}: missing '{key}'")
    return cfg


def tiny_model(src_dir: Path, dst: Path, seed: int = 1) -> Path:
    """Random-init copy of src's architecture at toy width (dry run only). Keeps vocab, tokenizer and tie setting."""
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM

    if (dst / "config.json").exists():
        return dst
    cfg = AutoConfig.from_pretrained(src_dir)
    for k, v in {"hidden_size": 64, "intermediate_size": 128, "num_hidden_layers": 2, "num_attention_heads": 4,
                 "num_key_value_heads": 2, "head_dim": 16, "max_position_embeddings": 4096}.items():
        setattr(cfg, k, v)
    if hasattr(cfg, "layer_types") and cfg.layer_types is not None:
        cfg.layer_types = cfg.layer_types[:2]
    torch.manual_seed(seed)
    model = AutoModelForCausalLM.from_config(cfg)
    dst.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(dst)
    for f in ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "generation_config.json"):
        if (src_dir / f).exists():
            shutil.copy2(src_dir / f, dst / f)
    return dst


def run(cmd: list[str], log: Path, env: dict) -> tuple[int, float]:
    t0 = time.perf_counter()
    with open(log, "a", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n")
        fh.flush()
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=PKG)
    return rc, time.perf_counter() - t0


def tail(path: Path, n: int = 15) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except FileNotFoundError:
        return []


OOM_MARKERS = ("torch.OutOfMemoryError", "CUDA out of memory", "torch.cuda.OutOfMemoryError")


def is_oom(text: str) -> bool:
    return any(m in text for m in OOM_MARKERS)


def read_from(path: Path, offset: int) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            fh.seek(offset)
            return fh.read()
    except FileNotFoundError:
        return ""


def flags(d: dict) -> list[str]:
    out = []
    for k, v in d.items():
        k = "--" + k.replace("_", "-")
        if v is True:
            out.append(k)
        elif v is False or v is None:
            continue
        else:
            out += [k, str(v)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--sizes", help="comma list: run only these sizes of the config (default: all, in config order)")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    dry = bool(cfg.get("dry_run", False))
    out = Path(cfg["out"]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    slice_dir = Path(cfg["slice_dir"]).resolve()
    # expandable segments: on the T4 measurement reserved memory ran up to 2.4x the allocated peak (fragmentation), and the
    # 8B full arm is predicted within a few GB of the H200 capacity
    env = {**os.environ, "G10_SURROGATE_PROFILE": cfg["profile"], "PYTHONUNBUFFERED": "1",
           "PYTORCH_CUDA_ALLOC_CONF": os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")}
    py = sys.executable
    sizes = cfg["sizes"]
    if args.sizes:
        want = args.sizes.split(",")
        sizes = [s for s in sizes if s["name"] in want]
    summary_path = out / "ladder_summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {"arms": {}}
    summary.update({"config": cfg, "complete": False, "dry_run": dry,
                    "arms_requested": [f"{s['name']}/{a['name']}" for s in sizes for a in s["arms"]]})

    def write_summary():
        tmp = summary_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(summary, indent=1), encoding="utf-8")
        tmp.replace(summary_path)

    for size in sizes:
        model_dir = Path(size["model_dir"]).resolve()
        if dry:
            model_dir = tiny_model(model_dir, out / "_tiny" / size["name"])
        for arm in size["arms"]:
            key = f"{size['name']}/{arm['name']}"
            adir = out / size["name"] / arm["name"]
            adir.mkdir(parents=True, exist_ok=True)
            if (adir / "DONE").exists():
                continue
            log = adir / "log.txt"
            rec = {"size": size["name"], "arm": arm["name"], "model_dir": str(model_dir), "status": "running"}
            summary["arms"][key] = rec
            write_summary()
            eval_model = model_dir
            if arm.get("method", "base") != "base":
                tr = {**cfg["train_common"], **size.get("train", {}), **arm.get("train", {})}

                def train_cmd(t):
                    return [py, "sft/bench/train.py", "--train", str(slice_dir / "train.tok.jsonl"), "--model", str(model_dir),
                            "--revision", "none", "--tokenizer-dir", str(model_dir), "--method", arm["method"],
                            "--out", str(adir / "train"), *flags(t)]

                start = log.stat().st_size if log.exists() else 0
                rc, secs = run(train_cmd(tr), log, env)
                retry = None
                # one retry at half micro_tokens after a CUDA out-of-memory: same rows per step and the same gradient
                # (sum of NLL over all micro-batches / global target count), only split into more micro-batches
                if rc != 0 and cfg.get("oom_retry", False) and is_oom(read_from(log, start)):
                    first_mt = int(tr.get("micro_tokens", 4096))
                    tr = {**tr, "micro_tokens": first_mt // 2}
                    shutil.rmtree(adir / "train", ignore_errors=True)  # no partial state from the failed attempt
                    with open(log, "a", encoding="utf-8") as fh:
                        fh.write(f"# ladder: CUDA out of memory at micro_tokens {first_mt}; retrying once at {first_mt // 2}\n")
                    rc, secs2 = run(train_cmd(tr), log, env)
                    retry = {"reason": "cuda_oom", "first_micro_tokens": first_mt, "micro_tokens": first_mt // 2,
                             "first_attempt_wall_s": round(secs, 1)}
                    secs = secs2
                rep_path = adir / "train" / "train_report.json"
                rep = json.loads(rep_path.read_text()) if rep_path.exists() else {}
                rec["train"] = {"returncode": rc, "wall_s": round(secs, 1), "micro_tokens": tr.get("micro_tokens"),
                                **({"oom_retry": retry} if retry else {}),
                                **{k: rep.get(k) for k in ("train_seconds", "seconds_per_100_steps", "first_loss", "last_loss",
                                                            "mean_loss_first_20", "mean_loss_last_20", "cuda_peak_allocated_mb",
                                                            "cuda_peak_reserved_mb", "peak_rss_mb", "hardware", "rows", "adam_impl")}}
                if arm["method"] == "dt":
                    mi = rep.get("method") if isinstance(rep.get("method"), dict) else {}
                    rec["train"]["dt"] = {k: mi.get(k) for k in ("deletion_final", "deletion_at_init", "mask_artifact")}
                rec["train"]["checks_pass"] = {k: v.get("pass") for k, v in rep.get("checks", {}).items()}
                if rc != 0 or not (adir / "train" / "model" / "config.json").exists():
                    rec.update(status="failed_train", log_tail=tail(log))
                    write_summary()
                    continue
                eval_model = adir / "train" / "model"
            ev = {**cfg["eval_common"], **size.get("eval", {})}
            cmd = [py, "sft/bench/evaluate.py", "--model", str(eval_model), "--split-file", str(slice_dir / "test.tok.jsonl"),
                   "--generations-out", str(adir / "test.gens.jsonl"), "--out", str(adir / "test_eval.json"), *flags(ev)]
            rc, secs = run(cmd, log, env)
            if rc != 0 or not (adir / "test_eval.json").exists():
                rec.update(status="failed_eval", eval_wall_s=round(secs, 1), log_tail=tail(log))
                write_summary()
                continue
            evj = json.loads((adir / "test_eval.json").read_text())
            rec["eval"] = {"wall_s": round(secs, 1), **{k: evj.get(k) for k in ("target_bpb", "format", "forgetting", "compute_dtype")}}
            if isinstance(rec["eval"].get("format"), dict):  # keep the counts, not the per-row list
                rec["eval"]["format"] = {k: v for k, v in rec["eval"]["format"].items() if not isinstance(v, list)}
            rec["status"] = "ok"
            if not cfg.get("keep_models", True) and eval_model != model_dir:
                shutil.rmtree(eval_model, ignore_errors=True)
                rec["model_deleted_after_eval"] = True
            (adir / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S %z"), encoding="utf-8")
            write_summary()
    summary["complete"] = all(summary["arms"].get(k, {}).get("status") == "ok" for k in summary["arms_requested"])
    write_summary()
    bad = [k for k in summary["arms_requested"] if summary["arms"].get(k, {}).get("status") != "ok"]
    print(json.dumps({"summary": str(summary_path), "complete": summary["complete"], "not_ok": bad}))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
