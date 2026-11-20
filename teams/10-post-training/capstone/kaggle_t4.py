"""Kaggle 2x T4: train two capstone-family stand-ins with Team 5's unmodified trainer, then G10's SFT and RL screen.

Not a TSAI run and not a quality result: a larger stand-in than a laptop can train, for G10's mechanics and
"what can a model this weak learn from" questions. Every output is labelled SMOKE by Team 5's trainer.

Run in a Kaggle notebook (GPU T4 x2, internet on), one cell:

    !python /kaggle/input/<g10-bundle>/teams/10-post-training/capstone/kaggle_t4.py \
        --bundle /kaggle/input/<g10-bundle> --tokenizer /kaggle/input/<private p1536 dataset>/tokenizer.json \
        --out /kaggle/working/g10

Inputs
- `<g10-bundle>`: a PRIVATE Kaggle dataset made by `capstone/make_kaggle_bundle.sh` (pinned Team 4/5 code, G10 code,
  the held-out subset, the arm overlay). Keep it private: it holds lab-repo files.
- the p1536 tokenizer: TSAI's file is "do not share outside the lab"; attach it only as a PRIVATE dataset (or the
  existing lab-shared one), never a public one.
- pre-training text: streamed here from the Hugging Face hub, human-written and permissively licensed only:
  HuggingFaceFW/fineweb-edu (sample-10BT, ODC-By) and codeparrot/github-code-clean (Python files whose licence is
  mit / apache-2.0 / bsd-2-clause / bsd-3-clause / isc). Documents that the tokenizer + KE2 table do not reproduce
  byte for byte are dropped (Team 5's loader refuses them).

What runs (each GPU is one process; Team 5's trainer is single-process, so the two GPUs run two arms):
  GPU 0  arm T2 (dry-run-1 dims: d512, 8 layers, 8 heads, 2 KV heads, 16+1 experts top-2, expert FFN 768, ctx 2048,
         Muon muon_lr 0.01 / AdamW 1e-3), 1,221 steps x batch 8 x 2048 = the dry-run-1 token budget (~20M tokens),
         fp32 (T4 has no BF16; Team 5's trainer refuses BF16 below compute capability 8.0)
  GPU 1  arm T1 (d256, 6 layers, 4 heads, 2 KV, 8+1 experts, FFN 512, ctx 1024) for the same wall-clock cap
  then two G10 SFT arms on the T2 stand-in (full fine-tune; GPU 0 Dolly SFT half, GPU 1 OCR-2 rows <= 2,048 tokens),
  each with a greedy format screen and, if the bundle carries the RL task file and easiest-rung ids, a k=8 RL screen
  before and after SFT (stdio_check: docker is absent on Kaggle, so set G10_STDIO_RUNNER=local; it isolates by uid,
  which needs root, and Kaggle runs as root; main() sets G10_STDIO_SECRET_PATHS and closes /kaggle to other uids).

Expected time (ESTIMATE, not measured on a T4): T2 ~1,000 tokens/s fp32 -> ~5.5 h for 20M tokens; T1 ~3x faster.
Kaggle's session cap is 12 h; `--max-hours` bounds each training. `--dry-run` runs the same pipeline at tiny size on
CPU with local text (the TSAI job-request rule: show a CPU log of the same script).
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

P1536_SHA = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
PERMISSIVE = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc"}


def sh(cmd: list[str], log: Path, env: dict | None = None) -> int:
    print("+", " ".join(map(str, cmd)), flush=True)
    with log.open("w") as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})}).returncode


def stream_text(out: Path, web_docs: int, code_docs: int, tok_path: Path, table: Path, team10: Path) -> dict:
    """Hub text -> {id, text} JSONL, round-trip filtered with build_pretrain_text.RoundTrip."""
    sys.path.insert(0, str(team10 / "capstone"))
    from build_pretrain_text import RoundTrip  # noqa: PLC0415
    from datasets import load_dataset  # noqa: PLC0415
    rt = RoundTrip(tok_path, table)
    n = {"web": 0, "code": 0}
    with out.open("w", encoding="utf-8") as f:
        web = load_dataset("HuggingFaceFW/fineweb-edu", "sample-10BT", split="train", streaming=True)
        for row in web:
            text = rt(row["text"])
            if text:
                f.write(json.dumps({"id": f"fwe/{row['id']}", "text": text}, ensure_ascii=False) + "\n")
                n["web"] += 1
            if n["web"] >= web_docs:
                break
        try:  # a script-based dataset: newer `datasets` releases may refuse it; then train on web text only
            code = load_dataset("codeparrot/github-code-clean", "Python-all", split="train", streaming=True,
                                trust_remote_code=True)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"warning": f"code dataset unavailable ({type(e).__name__}: {e}); web text only"}))
            code = []
        for i, row in enumerate(code):
            if row.get("license") not in PERMISSIVE or not 200 <= len(row["code"]) <= 65536:
                continue
            text = rt(row["code"])
            if text:
                f.write(json.dumps({"id": f"ghc/{i}", "text": text}, ensure_ascii=False) + "\n")
                n["code"] += 1
            if n["code"] >= code_docs:
                break
    return {"docs": n, "roundtrip": rt.stats}


ARMS = {
    # dry-run-1 dims come from Team 5's t2.yaml via exp2_muon.yaml unchanged; only precision and the time cap differ
    "g10_kaggle_t2_fp32.yaml": """# G10 Kaggle stand-in: Team 5 exp2_muon -> t2 (dry-run-1 dims), fp32 (T4 has no BF16). NOT a Team 5 arm.
inherit: exp2_muon.yaml
intended:
  arm: g10-kaggle-t2-fp32
  max_time_min: {minutes}
run:
  dtype: fp32
""",
    "g10_kaggle_t1_fp32.yaml": """# G10 Kaggle stand-in: Team 5 t1 dims with T2's Muon settings, fp32. NOT a Team 5 arm.
inherit: t1.yaml
intended:
  arm: g10-kaggle-t1-fp32
  max_time_min: {minutes}
optim:
  name: muon
  lr: 0.001
  muon_lr: 0.01
run:
  dtype: fp32
""",
    "g10_dry_tiny.yaml": """# G10 CPU dry run of the Kaggle script: tiny sizes. NOT a Team 5 arm.
inherit: exp2_muon.yaml
intended:
  arm: g10-dry-tiny
  instructor_expert_ffn: 32
  max_time_min: 10
model:
  block_size: 2048
  n_layer: 2
  n_head: 2
  n_kv_head: 1
  n_embd: 32
  moe: {{num_experts: 4, top_k: 2, num_shared: 1, dispatch: loop}}
run:
  batch_size: 4
  dtype: fp32
""",
}


def write_overlay(src: Path, dst: Path, max_hours: float) -> Path:
    """Team 5's runtime.yaml, t1/t2/exp2_muon.yaml and plan_v1.md (copied unchanged into the bundle) plus G10 arms.
    train_week2's config loader takes the arms root from the runtime file's folder, so the overlay is a 'team' dir."""
    import shutil  # noqa: PLC0415
    if not dst.exists():
        shutil.copytree(src, dst)
    for name, body in ARMS.items():
        (dst / "configs" / "arms" / name).write_text(body.format(minutes=int(max_hours * 60)))
    return dst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--web-docs", type=int, default=60000)
    ap.add_argument("--code-docs", type=int, default=60000)
    ap.add_argument("--max-hours", type=float, default=9.0)
    ap.add_argument("--dry-run", action="store_true", help="tiny arms on CPU with --train-text, a few steps")
    ap.add_argument("--train-text", type=Path, help="dry run: local {id,text} JSONL instead of streaming")
    a = ap.parse_args()
    b = a.bundle.resolve()
    g5, team10 = b / "lab", b / "teams" / "10-post-training"
    out = a.out.resolve()
    (out / "logs").mkdir(parents=True, exist_ok=True)
    py = sys.executable
    import hashlib  # noqa: PLC0415
    if hashlib.sha256(a.tokenizer.read_bytes()).hexdigest() != P1536_SHA:
        raise SystemExit("tokenizer is not p1536 (sha256 e6b93a93...)")
    record = {"started": time.strftime("%F %T"), "dry_run": a.dry_run, "bundle_manifest": json.loads(
        (b / "BUNDLE_MANIFEST.json").read_text())}
    # 1. Team 4's KE2 raw table for p1536
    ke2 = out / "ke2"
    if sh([py, "-I", str(g5 / "teams/04-ke2/src/build_tables.py"), "--tokenizer", str(a.tokenizer), "--out", str(ke2),
           "--pos-dims", "32"], out / "logs/ke2.log"):
        raise SystemExit("KE2 table build failed")
    table = ke2 / "raw_table_P32.npz"
    # 2. pre-training text
    text = out / "train_text.jsonl"
    if a.dry_run:
        text = a.train_text.resolve()
        record["text"] = {"source": str(text)}
    elif not text.exists():
        record["text"] = stream_text(text, a.web_docs, a.code_docs, a.tokenizer, table, team10)
    (out / "RUN_RECORD.json").write_text(json.dumps(record, indent=1))
    # 3. two arms with Team 5's unmodified trainer through the G10 launcher (tokenizer identity only on CUDA)
    ov = write_overlay(b / "overlay", out / "overlay", a.max_hours)
    arms = ([("g10_dry_tiny.yaml", "cpu", 20, None), ("g10_dry_tiny.yaml", "cpu", 20, None)]
            if a.dry_run else [("g10_kaggle_t2_fp32.yaml", "cuda", 1221, "0"), ("g10_kaggle_t1_fp32.yaml", "cuda", 100000, "1")])
    procs = []
    for i, (arm, dev, steps, gpu) in enumerate(arms):
        run = out / f"run{i}"
        if (run / "summary.json").exists():
            continue
        cmd = [py, str(team10 / "capstone/g5_launch.py"), "--g5-root", str(g5), "--tokenizer-sha256", P1536_SHA, "--",
               "--config", str(ov / "configs/arms" / arm), "--runtime", str(ov / "configs/runtime.yaml"),
               "--tokenizer", str(a.tokenizer), "--byte-table", str(table), "--train-data", str(text),
               "--heldout-data", str(b / "heldout/heldout_v1_bal60k.jsonl"),
               "--heldout-sources", str(b / "heldout/heldout_v1_bal60k_sources.jsonl"),
               "--device", dev, "--seed", "1234", "--smoke", "--smoke-steps", str(steps), "--out", str(run)]
        env = {"CUDA_VISIBLE_DEVICES": gpu} if gpu is not None else {}
        f = (out / f"logs/run{i}.log").open("w")
        procs.append(subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env={**os.environ, **env}))
        if a.dry_run:
            procs[-1].wait()
    for p in procs:
        p.wait()
    for i in range(len(arms)):
        s = out / f"run{i}" / "summary.json"
        print(f"run{i}:", s.read_text() if s.exists() else "NO SUMMARY (see logs)", flush=True)
    # 4. G10 adapter config for run0, then SFT + format screen
    sys.path.insert(0, str(team10 / "capstone"))
    from make_adapter_config import write_config  # noqa: PLC0415
    cfg = write_config(out / "adapter_run0.yaml", g5_root=g5, run_folder=out / "run0", tokenizer=a.tokenizer,
                       table=table, team10=team10, require_git=False,
                       source_commit=record["bundle_manifest"]["lab_commit"])
    # two SFT arms on the T2 stand-in, one per GPU: Dolly (instruction following) and OCR-2 (code reasoning rows that
    # fit 2,048 tokens). Each screens the easiest RL rung before and after: does SFT give RL any signal (A6)?
    rl = ["--rl-tasks", str(b / "sft/rl_tasks.jsonl"), "--rl-ids", str(b / "sft/rl_easy_ids.txt"), "--rl-k", "8",
          "--rl-max-new", "64" if a.dry_run else "384"] if (b / "sft/rl_easy_ids.txt").exists() else []
    procs = []
    for gpu, name in (("0", "dolly"), ("1", "ocr2")):
        tr, ev = b / f"sft/{name}_train.jsonl", b / f"sft/{name}_eval.jsonl"
        if not tr.exists() or (out / f"sft_{name}" / "sft_report.json").exists():
            continue
        dev = "cpu" if a.dry_run else "cuda"
        steps = "10" if a.dry_run else ("300" if name == "dolly" else "250")
        cmd = [py, str(team10 / "capstone/sft_g5.py"), "--adapter-config", str(cfg), "--train", str(tr), "--eval", str(ev),
               "--method", "full", "--steps", steps, "--batch", "16" if name == "dolly" else "8", "--lr", "3e-4",
               "--micro-tokens", "4096", "--drop-over-block", "--device", dev, "--gen-limit", "4" if a.dry_run else "96",
               "--gen-max-new", "64" if name == "dolly" else "384",
               "--heldout", str(b / "heldout/heldout_v1_bal60k.jsonl"),
               "--heldout-sources", str(b / "heldout/heldout_v1_bal60k_sources.jsonl"), *rl, "--out", str(out / f"sft_{name}")]
        f = (out / f"logs/sft_{name}.log").open("w")
        env = {**os.environ, **({} if a.dry_run else {"CUDA_VISIBLE_DEVICES": gpu})}
        if rl and not shutil.which("docker"):
            env["G10_STDIO_RUNNER"] = "local"  # stdio_check's uid-isolated runner (needs root; Kaggle runs as root)
            # uid isolation protects only files whose mode excludes "other". The expected outputs are in the task
            # file, a read-only input mount that cannot be chmodded, so close the folders above it instead (root
            # still reads); stdio_check.preflight_isolation refuses to score unless a sandbox uid cannot read it.
            env["G10_STDIO_SECRET_PATHS"] = str(b / "sft/rl_tasks.jsonl")
            if Path("/kaggle").is_dir():
                os.chmod("/kaggle", 0o700)
        procs.append(subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env))
        if a.dry_run:
            procs[-1].wait()
    for p in procs:
        p.wait()
    print(json.dumps({"done": time.strftime("%F %T"), "out": str(out)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
