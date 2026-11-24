"""G10 day-one probe of a Team 5 run folder: one command, JSON out, optional bounded SFT.

    python capstone/day_one_probe.py --g5-root <lab checkout> --run-folder <dir with manifest.json/checkpoint.pt/summary.json> \
        --tokenizer tokenizer.json --byte-table raw_table_P32.npz --heldout H.jsonl --heldout-sources S.jsonl \
        --sft-eval dolly_eval.jsonl [--rl-tasks cc.jsonl --rl-ids easy_rung_ids.txt] --device cuda --out out/

    --sft-dolly databricks-dolly-15k.jsonl replaces --sft-train/--sft-eval: the SFT rows are built at start with the
    run's own tokenizer and table (capstone/probe_inputs.py) under out/_inputs/, which is removed at exit.

Steps (each writes out/<step>.json; a failed step is recorded and the rest still run):
  pins        first, before any model work: sha256 of --tokenizer and the byte table's content hash against what the
              run folder's manifest.json records (artifacts.*); prints both, and on a mismatch stops with exit 1.
              A hash the manifest does not record is reported as used, not checked
  inputs      only with --sft-dolly: SFT rows from public Dolly-15k with the run's tokenizer; counts and sha256
  adapter     team5_adapter run_folder build: hashes, G5 validate, model_hash == summary.json, special ids
  forgetting  Team 5's evaluate() on the held-out file (bpb per slice), the number SFT's forgetting check compares to
  sampling    tokens/s of the native sampler: last-position head vs KV cache (capstone/bench_sampling_g5.py)
  mismatch    numerics-only trust-region firing and expert-set flips (capstone/mismatch_g5.py)
  format      greedy chat-format screen of the base model on SFT eval prompts (closed <|im_end|>, render.py parse)
  rl_screen   k samples per easiest-rung RL prompt scored by rl-data/stdio_check.py: pass rate, mixed groups, reasons
  sft_<arm>   optional (--sft-train): the five SFT arms of the rehearsal (full, markers, LoRA, LoRA + markers, DT),
              each with masks/writeback/frozen/reload checks, forgetting, format screen; RL screen after full and
              LoRA + markers. Per-arm training is capped by --sft-max-train-seconds.
Outputs are aggregates only (no prompt or completion text, no weights: each SFT arm's saved model is deleted after
its reload check). Network: none. Writes only to --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM10 = HERE.parent
sys.path.insert(0, str(TEAM10 / "rl-loop"))
sys.path.insert(0, str(HERE))


def step(out: Path, name: str, fn):
    t0 = time.perf_counter()
    try:
        res = {"ok": True, **fn()}
    except Exception as e:  # noqa: BLE001  the probe must report every step
        res = {"ok": False, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-2000:]}
    res["seconds"] = round(time.perf_counter() - t0, 1)
    (out / f"{name}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"step": name, "ok": res["ok"], "seconds": res["seconds"]}), flush=True)
    return res


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_pins(run_folder: Path, tokenizer: Path, table: Path) -> dict:
    """The tokenizer and byte table given must be the ones the run folder says it trained with (Team 5's
    manifest.json `artifacts`, written from week2.artifacts.Artifacts.identity()). Raises on a mismatch; a hash the
    manifest does not record is reported as used (match None). The table file hash is informational: the model saw
    the table's content, so the content hash is the one checked."""
    import numpy as np  # noqa: PLC0415
    recorded = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8")).get("artifacts") or {}
    with np.load(table, allow_pickle=False) as z:
        content = str(z["table_sha256"]) if "table_sha256" in z.files else None
    used = {"tokenizer_sha256": sha256_file(tokenizer), "table_content_sha256": content,
            "table_file_sha256": sha256_file(table)}
    checks = {k: {"given": v, "run_manifest": recorded.get(k),
                  "match": None if recorded.get(k) is None else recorded.get(k) == v} for k, v in used.items()}
    print(json.dumps({"pins": {k: [c["given"], c["run_manifest"]] for k, c in checks.items()}}), flush=True)
    bad = [k for k in ("tokenizer_sha256", "table_content_sha256") if checks[k]["match"] is False]
    if bad:
        raise ValueError(f"run folder was trained with different {', '.join(bad)}: "
                         + "; ".join(f"{k} given {checks[k]['given']}, run manifest {checks[k]['run_manifest']}"
                                     for k in bad))
    return {"checks": checks, "not_recorded": [k for k, c in checks.items() if c["match"] is None]}


CANARY_FILES = ("model.safetensors", "dt_keep_masks.bin", "dt_keep_masks.bin.json")


def copy_canary_state(arm_out: Path, dest: Path) -> dict:
    """Copy the three files a DT canary reads (the arm's weights and its two mask files) into `dest`, write SHA256SUMS
    there ("<sha256>  <file>" lines) and return {"dir", "sha256": {file: sha256}}. Raises when a file is missing."""
    import hashlib  # noqa: PLC0415
    import shutil  # noqa: PLC0415
    missing = [n for n in CANARY_FILES if not (arm_out / n).is_file()]
    if missing:
        raise RuntimeError(f"keep-canary-state: the arm wrote no {missing} (the method must write DT mask files)")
    dest.mkdir(parents=True, exist_ok=True)
    sums = {}
    for n in CANARY_FILES:
        shutil.copyfile(arm_out / n, dest / n)
        h = hashlib.sha256()
        with (dest / n).open("rb") as f:  # hashed in 1 MiB chunks: the weights file is about 1 GB on the real model
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        sums[n] = h.hexdigest()
    (dest / "SHA256SUMS").write_text("".join(f"{v}  {k}\n" for k, v in sums.items()))
    return {"dir": str(dest), "sha256": sums}


def run_sft_arm(out: Path, arm: str, cmd: list[str], timeout: float | None = None,
                canary_dest: Path | None = None) -> dict:
    """Keep reports but remove model text/weights even when an arm fails. `timeout` (seconds): the arm's process is
    killed at that point and the arm fails with a deadline message (weights and generations are still removed)."""
    arm_out = out / f"sft_{arm}"
    try:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"arm {arm} stopped at the job's own deadline ({timeout:.0f} s left when it started)") from None
        if r.returncode:
            raise RuntimeError(r.stderr[-1500:])
        rep = json.loads((arm_out / "sft_report.json").read_text())
        keep = ("method", "train_seconds", "stopped_early", "mask_checks", "writeback_step1",
                "frozen_weights_unchanged", "reload_parity", "first_loss", "last_loss")
        kept = {"kept_weights": rep["kept_weights"]} if rep.get("kept_weights") else {}  # only when --keep-weights-dir was given
        if canary_dest is not None:  # default off: the kept arm's weights and DT masks are copied before the finally clause deletes them
            kept["kept_canary_state"] = copy_canary_state(arm_out, canary_dest)
        return {**{k: rep.get(k) for k in keep}, "before": rep["before"], "after": rep["after"], **kept}
    finally:
        # A process-level kill still requires the job runner's cleanup; finally covers ordinary failures.
        (arm_out / "generations.jsonl").unlink(missing_ok=True)
        (arm_out / "model.safetensors").unlink(missing_ok=True)


def finish(out: Path, results: dict) -> int:
    failed = [name for name, result in results.items() if not result["ok"]]
    summary = {"ok": not failed, "steps": len(results), "failed_steps": failed}
    kept = {n: r["kept_weights"] for n, r in results.items() if r.get("kept_weights")}
    if kept:  # only when --keep-weights-dir was given: where the run folder is, its manifest sha256 and the saved step
        summary["kept_weights"] = kept
    canary = {n: r["kept_canary_state"] for n, r in results.items() if r.get("kept_canary_state")}
    if canary:  # only when --keep-canary-state-dir was given
        summary["kept_canary_state"] = canary
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary), flush=True)
    return int(bool(failed))


def rl_screen(adapter_cfg: Path, tasks: Path, ids: Path, k: int, max_new: int, device: str, limit: int = 0) -> dict:
    import team5_adapter as ta  # noqa: PLC0415
    return rl_screen_bundle(ta.build(adapter_cfg, device=device).require_bundle(), tasks, ids, k, max_new, device, limit)


def rl_screen_bundle(bundle, tasks: Path, ids: Path, k: int, max_new: int, device: str, limit: int = 0,
                     seconds: float = 0.0) -> dict:
    """k samples (temperature 1, KV cache) per prompt scored by rl-data/stdio_check.py; aggregates and per-prompt
    counts only (id, passes, programs that ran, samples with a code fence). `seconds` > 0: no new prompt is started
    once the screen has run that long, so callers can compare screens on the ids both reached (the id file's order)."""
    import time  # noqa: PLC0415
    import importlib.util  # noqa: PLC0415
    import torch  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location("g10_stdio_check", TEAM10 / "rl-data" / "stdio_check.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    # two sft_g5 processes (one per GPU) share a machine: each needs its own sandbox uid slice, because a uid's
    # cleanup kills every process of that uid (GPU 0 -> 61000+1000, GPU 1 -> 62000+1000)
    gpu = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if gpu.isdigit() and int(gpu) < 4:
        sc.set_uid_range(61000 + 1000 * int(gpu), 1000)
    kv = bundle.kv_cache
    bundle.kv_cache = True
    codec = bundle.codec()
    by_id = {}
    for line in tasks.read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            by_id[t["id"]] = t
    want = [i for i in ids.read_text().split() if i in by_id]
    if limit:
        want = want[:limit]  # the id file's own order (sorted ids): a fixed, reproducible subset
    gen = torch.Generator(device=device).manual_seed(0)
    reasons, groups, passes, skipped = {}, {"all_fail": 0, "mixed": 0, "all_pass": 0}, 0, 0
    has_code, per_prompt, t0, stopped = 0, [], time.perf_counter(), False
    for tid in want:
        if seconds and time.perf_counter() - t0 > seconds:
            stopped = True
            break
        prompt = codec.encode_prompt(by_id[tid]["statement"])
        mn = min(max_new, bundle.spec["block_size"] - len(prompt))
        if mn < 16:
            skipped += 1
            continue
        seq, cmask, _ = bundle.sample(prompt, k, mn, 1.0, gen)
        p = runs = fence = 0
        for r in range(k):
            text = codec.decode_completion(seq[r, len(prompt):][cmask[r]].tolist())
            fence += "```" in text
            res = sc.score(by_id[tid], text)
            key = "pass" if res["reward"] >= 1.0 else str(res.get("reason", "fail")).split(" on ")[0]
            reasons[key] = reasons.get(key, 0) + 1
            p += res["reward"] >= 1.0
            runs += key in ("pass", "wrong answer on a test")
        has_code += fence
        per_prompt.append([tid, int(p), int(runs), int(fence)])
        passes += p
        groups["all_fail" if p == 0 else ("all_pass" if p == k else "mixed")] += 1
    bundle.kv_cache = kv
    n = sum(groups.values())
    return {"prompts": n, "skipped_too_long": skipped, "k": k, "max_new": max_new, "pass_rate": passes / max(n * k, 1),
            "groups": groups, "reasons": dict(sorted(reasons.items())), "samples_with_code_fence": has_code,
            "runner": sc.RUNNER_KIND, "per_prompt": per_prompt, "budget_seconds": seconds, "stopped_at_budget": stopped,
            "seconds": round(time.perf_counter() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--g5-root", type=Path, required=True)
    ap.add_argument("--run-folder", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--heldout", type=Path, required=True)
    ap.add_argument("--heldout-sources", type=Path)
    ap.add_argument("--sft-eval", type=Path, help="eval rows (or build them with --sft-dolly)")
    ap.add_argument("--sft-dolly", type=Path, help="databricks-dolly-15k.jsonl: build SFT train/eval rows with the "
                    "run's tokenizer (implies the SFT arms)")
    ap.add_argument("--sft-max-tokens", type=int, default=256, help="row length cap for --sft-dolly (rows dropped, not cut)")
    ap.add_argument("--rl-tasks", type=Path)
    ap.add_argument("--rl-ids", type=Path)
    ap.add_argument("--rl-k", type=int, default=8)
    ap.add_argument("--rl-max-new", type=int, default=512)
    ap.add_argument("--rl-limit", type=int, default=48, help="screen at most this many RL prompts (0 = all)")
    ap.add_argument("--sft-train", type=Path, help="also run the SFT arms (full, markers, lora, lora+markers, dt)")
    ap.add_argument("--sft-steps", type=int, default=300)
    ap.add_argument("--sft-max-train-seconds", type=float, default=600.0, help="per-arm training cap")
    ap.add_argument("--sft-arms", default="full,markers,lora,lora_markers,dt")
    ap.add_argument("--sample-len", type=int, default=256, help="prompt and new tokens of the sampling benchmark")
    ap.add_argument("--probe-max-new", type=int, default=128)
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--origin", default="g10_rehearsal", choices=("g10_rehearsal", "g5_delivery"))
    ap.add_argument("--probe-file", type=Path, help="json {ids, expected_mean_nll[, atol]} for the delivered weights "
                    "(capstone/make_probe_file.py); required with --origin g5_delivery")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if not (a.sft_eval or a.sft_dolly):
        ap.error("give --sft-eval or --sft-dolly")
    if a.origin == "g5_delivery" and a.probe_file is None:
        ap.error("--origin g5_delivery needs --probe-file: team5_adapter refuses a delivered run folder without "
                 "probe.ids and probe.expected_mean_nll (make one with capstone/make_probe_file.py)")
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    try:
        return run(a, out)
    finally:
        shutil.rmtree(out / "_inputs", ignore_errors=True)  # built rows never leave the job


def run(a, out: Path) -> int:
    results = {"pins": step(out, "pins", lambda: check_pins(a.run_folder, a.tokenizer, a.byte_table))}
    if not results["pins"]["ok"]:
        return finish(out, results)  # wrong tokenizer or table: no model work, no rows built
    from make_adapter_config import load_probe, write_config  # noqa: PLC0415
    cfg = write_config(out / "adapter.yaml", a.g5_root, a.run_folder, a.tokenizer, a.byte_table, TEAM10, a.origin,
                       not a.no_git, **({"probe": load_probe(a.probe_file)} if a.probe_file else {}))
    py = sys.executable

    def record(name, fn):
        results[name] = step(out, name, fn)
        return results[name]

    def adapter():
        import team5_adapter as ta  # noqa: PLC0415
        r = ta.build(cfg, device=a.device)
        m = r.manifest
        return {"status": r.status, "model_spec": m["model_spec"], "n_parameters": m["n_parameters"],
                "model_hash_g5": m["model_hash_g5"], "run_folder": m["run_folder"], "special_tokens": m["special_tokens"]}

    def forgetting():
        import sft_g5  # noqa: PLC0415
        import team5_adapter as ta  # noqa: PLC0415
        b = ta.build(cfg, device=a.device).require_bundle()
        return sft_g5.forgetting_bpb(b, a.heldout, a.heldout_sources, a.device)

    def sub(name, cmd):
        def run():
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError(r.stderr[-1500:])
            return json.loads((out / f"{name}_raw.json").read_text())
        return run

    def fmt():
        import sft_g5  # noqa: PLC0415
        import team5_adapter as ta  # noqa: PLC0415
        b = ta.build(cfg, device=a.device).require_bundle()
        rows = [json.loads(x) for x in a.sft_eval.read_text().splitlines() if x.strip()]
        summary, _ = sft_g5.generate_and_judge(b, rows, 64, 64)
        return summary

    if a.sft_dolly:
        def inputs():
            import probe_inputs  # noqa: PLC0415
            return probe_inputs.build_dolly(a.sft_dolly, a.tokenizer, a.byte_table, a.sft_max_tokens, out / "_inputs")
        if not record("inputs", inputs)["ok"]:
            return finish(out, results)  # every later step reads these rows
        a.sft_train, a.sft_eval = out / "_inputs" / "sft_train.jsonl", out / "_inputs" / "sft_eval.jsonl"
    record("adapter", adapter)
    record("forgetting", forgetting)
    record("sampling", sub("sampling", [py, str(HERE / "bench_sampling_g5.py"), "--adapter-config", str(cfg),
                                           "--prompt-len", str(a.sample_len), "--k", "8", "--max-new", str(a.sample_len), "--paths", "head,kv",
                                           "--device", a.device, "--out", str(out / "sampling_raw.json")]))
    record("mismatch", sub("mismatch", [py, str(HERE / "mismatch_g5.py"), "--adapter-config", str(cfg),
                                           "--prompts", str(a.sft_eval), "--n", "16", "--k", "8", "--max-new", str(a.probe_max_new),
                                           "--device", a.device, "--out", str(out / "mismatch_raw.json")]))
    record("format", fmt)
    if a.rl_tasks and a.rl_ids:
        record("rl_screen", lambda: rl_screen(cfg, a.rl_tasks, a.rl_ids, a.rl_k, a.rl_max_new, a.device,
                                                 a.rl_limit))
    if a.sft_train:
        arms = {"full": ["--method", "full", "--lr", "3e-4"],
                "markers": ["--method", "markers", "--marker-rows", "--wd", "0", "--marker-lr", "1e-3"],
                "lora": ["--method", "lora", "--lr", "1e-3"],
                "lora_markers": ["--method", "lora", "--lr", "1e-3", "--marker-rows", "--wd", "0", "--marker-lr", "1e-3"],
                "dt": ["--method", "dt", "--dt-targets", "g5_mlp", "--lr", "1e-3"]}
        for arm in a.sft_arms.split(","):
            cmd = [py, str(HERE / "sft_g5.py"), "--adapter-config", str(cfg), "--train", str(a.sft_train),
                   "--eval", str(a.sft_eval), *arms[arm], "--steps", str(a.sft_steps), "--batch", "16",
                   "--max-train-seconds", str(a.sft_max_train_seconds), "--drop-over-block", "--device", a.device,
                   "--gen-limit", "64", "--gen-max-new", "48", "--seed", "1", "--heldout", str(a.heldout),
                   *(["--heldout-sources", str(a.heldout_sources)] if a.heldout_sources else []),
                   *(["--rl-tasks", str(a.rl_tasks), "--rl-ids", str(a.rl_ids), "--rl-max-new", str(a.rl_max_new),
                      "--rl-limit", str(a.rl_limit)] if a.rl_tasks and a.rl_ids and arm in ("full", "lora_markers") else []),
                   "--out", str(out / f"sft_{arm}")]

            record(f"sft_{arm}", lambda cmd=cmd, arm=arm: run_sft_arm(out, arm, cmd))
    return finish(out, results)


if __name__ == "__main__":
    raise SystemExit(main())
