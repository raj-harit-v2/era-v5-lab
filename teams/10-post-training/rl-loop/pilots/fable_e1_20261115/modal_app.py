"""E1 on Modal: Qwen2.5-Coder-7B-Instruct, rl-loop/train.py with objective_v1 and durable state.

    M=~/.venvs/modal312/bin/modal
    $M run modal_app.py::weights
    $M run modal_app.py::check
    $M run modal_app.py::e1 --run-id e1a --steps 60 --budget-s 3000 --max-calls 3
    $M run modal_app.py::rescore --run-id e1a

The GPU job runs as budgeted calls. Each call gets a deadline; the trainer saves full state to the volume, pauses,
and the next call continues from it. Nothing is lost when a call is killed: state is written before each evaluation.

Spend guard: a call is refused when the ledger plus its worst case (function timeout x rate) would pass CAP_USD.
Rates are `modal billing rates` as read on 15 Nov 2026. Ledger rows are function-cost estimates from client wall
time, not the billing page; reconcile with `modal billing summary`.
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[2] if modal.is_local() else Path("/root/team")
REMOTE = "/root/team"
WORK = Path(os.environ.get("G10_E1_WORK", "")) if modal.is_local() else Path("/nonexistent")
MODELS = {"7b": ("Qwen/Qwen2.5-Coder-7B-Instruct", "c03e6d358207e414f1eca0bb1891e29f1db0e242")}  # apache-2.0


def weights_path(key: str) -> str:
    repo, rev = MODELS[key]
    return f"/vol/hf/{repo.split('/')[1]}@{rev[:12]}"


GPU_RATE = 2.50 / 3600      # A100-80GB
CPU_RATE = 0.0473 / 3600    # per core
MEM_RATE = 0.008 / 3600     # per GiB
GPU_CPU, GPU_MEM_GIB = 32.0, 48.0
CAP_USD = float(os.environ.get("G10_E1_CAP_USD", "14.0"))
LEDGER = WORK / "SPEND.jsonl"

VOL = modal.Volume.from_name("g10-fable-e1-2026-11-15", create_if_missing=True, version=2)
IGNORE = ["**/__pycache__/**", "**/out/**", "**/*.pyc", "**/.pytest_cache/**", "**/pilots/**/runs/**"]
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("vllm==0.32.0", "huggingface_hub[hf_xet]")
    .env({"HF_XET_HIGH_PERFORMANCE": "1", "HF_HOME": "/vol/hf_cache", "TOKENIZERS_PARALLELISM": "false",
          "VLLM_USE_FLASHINFER_SAMPLER": "0", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
    .add_local_dir(TEAM / "rl-loop", f"{REMOTE}/rl-loop", ignore=IGNORE)
    .add_local_dir(TEAM / "rl-data", f"{REMOTE}/rl-data", ignore=IGNORE)
    # rl-data/stdio_check.py imports rl/verifier.py (extract_code). Only that file: rl/tasks and rl/go are
    # assistant-written evaluation tasks and must never reach an RL job.
    .add_local_file(TEAM / "rl" / "verifier.py", f"{REMOTE}/rl/verifier.py")
    .add_local_file(TEAM / "dt" / "mask.py", f"{REMOTE}/dt/mask.py")  # train.dt (Deletion Tuning as the RL method)
    .add_local_file(HERE / "isolation_probe.py", "/root/probe/isolation_probe.py")
)
app = modal.App("g10-fable-e1-2026-11-15", image=image)
function, local_entrypoint = app.function, app.local_entrypoint


def _cost(seconds: float, gpu: bool, cpu: float, mem: float) -> float:
    return seconds * ((GPU_RATE if gpu else 0.0) + cpu * CPU_RATE + mem * MEM_RATE)


@function(volumes={"/vol": VOL}, timeout=1800, cpu=2.0, memory=4096)
def download_weights(key: str = "7b") -> dict:
    import hashlib  # noqa: PLC0415
    from huggingface_hub import snapshot_download  # noqa: PLC0415
    t0 = time.time()
    repo, rev = MODELS[key]
    dest = weights_path(key)
    if not Path(dest, "config.json").exists():
        snapshot_download(repo, revision=rev, local_dir=dest)
    shas = {}
    for f_ in sorted(Path(dest).glob("*.safetensors")):
        h = hashlib.sha256()
        with open(f_, "rb") as f:
            for b in iter(lambda: f.read(1 << 24), b""):
                h.update(b)
        shas[f_.name] = h.hexdigest()
    VOL.commit()
    return {"weights": dest, "revision": rev, "safetensors_sha256": shas, "seconds": round(time.time() - t0, 1)}


def _protected_run_dirs(run_id: str):
    """Expected answers live here: root-only (0700 folders, 0600 files) so sandboxed programs cannot read them."""
    os.umask(0o077)
    os.chmod("/root", 0o700)
    Path("/root/tmp").mkdir(mode=0o700, exist_ok=True)  # trainer TMPDIR: never the shared /tmp sandboxes can write
    runs = Path("/vol/runs")
    runs.mkdir(parents=True, exist_ok=True)
    os.chmod(runs, 0o700)
    run, data = runs / run_id, runs / run_id / "data"
    data.mkdir(parents=True, exist_ok=True)
    for d in (run, data):
        os.chmod(d, 0o700)
    return run, data


def _write_private(path: Path, text: str) -> None:
    path.write_text(text)
    os.chmod(path, 0o600)


@function(volumes={"/vol": VOL}, timeout=900, cpu=4.0, memory=8192, block_network=True)
def preflight(tasks_text: str, train_ids: str, heldout_ids: str) -> dict:
    """CPU only: isolation probes, then the task construction the GPU job will do, with the cached tokenizer."""
    t0 = time.time()
    sys.path.insert(0, "/root/probe")
    import isolation_probe  # noqa: PLC0415
    run, data = _protected_run_dirs("_preflight")
    res = {"isolation": isolation_probe.main(REMOTE, "/vol/runs/_probe_private/data")}
    for name, text in (("tasks.jsonl", tasks_text), ("train_ids.txt", train_ids), ("heldout_ids.txt", heldout_ids)):
        _write_private(data / name, text)
    os.environ["G10_STDIO_RUNNER"] = "local"
    sys.path.insert(0, f"{REMOTE}/rl-loop")
    import train  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415
    tok = AutoTokenizer.from_pretrained(weights_path("7b"), local_files_only=True)
    task = train.stdio_task({"tasks": str(data / "tasks.jsonl"), "train_ids": str(data / "train_ids.txt"),
                             "heldout_ids": str(data / "heldout_ids.txt")}, tok)
    lens = [len(p) for p in task.train + task.heldout]
    res["task"] = {"train": len(task.train), "heldout": len(task.heldout), "max_prompt_tokens": max(lens),
                   "eos": tok.eos_token_id, "empty_completion_reward": task.reward(task.train[0], tok.encode("x")),
                   "reasons_after_one_score": train.pop_reasons(task)}
    res["perms"] = {str(p): oct(p.stat().st_mode & 0o777) for p in (Path("/vol/runs"), run, data, data / "tasks.jsonl")}
    res["seconds"] = round(time.time() - t0, 1)
    return res


@function(gpu="A100-80GB", volumes={"/vol": VOL}, timeout=3600, cpu=GPU_CPU, memory=int(GPU_MEM_GIB * 1024),
          block_network=True)
def run_call(config_text: str, tasks_text: str, train_ids: str, heldout_ids: str, run_id: str, steps: int,
             budget_s: float, grace_s: float) -> dict:
    """One budgeted call: train until the deadline (budget_s from now), then pause. The subprocess is killed only
    after budget_s + grace_s; grace covers an evaluation or state write that is in flight at the deadline."""
    return _call_body(config_text, tasks_text, train_ids, heldout_ids, run_id, steps, budget_s, grace_s,
                      GPU_RATE, GPU_CPU, GPU_MEM_GIB)


H200_RATE, H200_MEM_GIB = 4.54 / 3600, 96.0


@function(gpu="H200", volumes={"/vol": VOL}, timeout=3600, cpu=GPU_CPU, memory=int(H200_MEM_GIB * 1024),
          block_network=True)
def run_call_h200(config_text: str, tasks_text: str, train_ids: str, heldout_ids: str, run_id: str, steps: int,
                  budget_s: float, grace_s: float) -> dict:
    """The same call on an H200 (141 GB): Deletion Tuning on a 7B model keeps one fp32 logit, its gradient and two
    Adam moments per gate weight (about 30 GB) next to the model and the sampler, which does not fit in 80 GB."""
    return _call_body(config_text, tasks_text, train_ids, heldout_ids, run_id, steps, budget_s, grace_s,
                      H200_RATE, GPU_CPU, H200_MEM_GIB)


def _call_body(config_text, tasks_text, train_ids, heldout_ids, run_id, steps, budget_s, grace_s, gpu_rate, cpu,
               mem_gib) -> dict:
    t0 = time.time()
    run, data = _protected_run_dirs(run_id)
    for name, text in (("tasks.jsonl", tasks_text), ("train_ids.txt", train_ids), ("heldout_ids.txt", heldout_ids)):
        _write_private(data / name, text)
    cfg = (config_text.replace("@WEIGHTS@", weights_path("7b")).replace("@DATA@", str(data))
           .replace("@RUN@", str(run)).replace("@STEPS@", str(steps)).replace("@DEADLINE@", repr(t0 + budget_s)))
    (run / "config.yaml").write_text(cfg)
    env = {**os.environ, "G10_STDIO_RUNNER": "local", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "TMPDIR": "/root/tmp"}
    stop = threading.Event()

    def committer():  # the volume keeps what was written even if this container dies
        while not stop.wait(120):
            try:
                VOL.commit()
            except Exception as e:  # noqa: BLE001
                print("commit failed:", repr(e)[:200], flush=True)

    threading.Thread(target=committer, daemon=True).start()
    rc = "not started"
    with open(run / "stdout.log", "a") as log:
        log.write(f"\n=== call started {time.strftime('%Y-%m-%d %H:%M:%S')} steps={steps} budget_s={budget_s} ===\n")
        log.flush()
        try:
            rc = subprocess.run([sys.executable, f"{REMOTE}/rl-loop/train.py", "--config", str(run / "config.yaml"),
                                 "--out-dir", str(run / "out")], stdout=log, stderr=subprocess.STDOUT, env=env,
                                timeout=budget_s + grace_s).returncode
        except subprocess.TimeoutExpired:
            rc = "killed: budget + grace reached"
    stop.set()
    out = run / "out"
    read = lambda p: p.read_text() if p.exists() else None  # noqa: E731
    gpu_name = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                              text=True).stdout.strip()
    secs = time.time() - t0
    screen = read(out / "screen.json")
    if screen:  # task ids stay on the volume
        screen = json.dumps({k: v for k, v in json.loads(screen).items() if k not in ("per_task", "mixed_ids")})
    res = {"run_id": run_id, "returncode": rc, "gpu_name": gpu_name, "seconds": round(secs, 1),
           "usd": round(secs * (gpu_rate + cpu * CPU_RATE + mem_gib * MEM_RATE), 4),
           "summary": read(out / "summary.json"),
           "status": read(out / "status.json"), "screen": screen, "metrics": read(out / "metrics.jsonl"),
           "evals": read(out / "evals.jsonl"), "latest_state": read(run / "state" / "LATEST.json"),
           "log_tail": (read(run / "stdout.log") or "")[-8000:]}
    VOL.commit()
    return res


@function(volumes={"/vol": VOL}, timeout=3600, cpu=32.0, memory=16384, block_network=True)
def rescore_fn(run_id: str, limit: int, workers: int, early_exit: bool, use_pool: bool = False) -> dict:
    """Matched scoring check: the screen's saved completions scored again with one setting. CPU only.
    use_pool scores through rl-loop/score_pool.py (separate worker processes) instead of threads in this process."""
    t0 = time.time()
    run, data = _protected_run_dirs(run_id)
    os.environ["G10_STDIO_RUNNER"] = "local"
    os.environ["G10_STDIO_EARLY_EXIT"] = "1" if early_exit else "0"
    import hashlib  # noqa: PLC0415
    import importlib.util  # noqa: PLC0415
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location("stdio_check", f"{REMOTE}/rl-data/stdio_check.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    by_id = {}
    for line in (data / "tasks.jsonl").read_text().splitlines():
        if line.strip():
            t = json.loads(line)
            by_id[t["id"]] = t
    rows = [json.loads(line) for line in (run / "screen_completions.jsonl").read_text().splitlines()][:limit]
    if use_pool:
        sys.path.insert(0, f"{REMOTE}/rl-loop")
        import score_pool  # noqa: PLC0415
        pool = score_pool.ScorePool(workers)
        c0 = time.time()
        res = pool.score([(by_id[r["id"]], r["text"]) for r in rows])
        wall = time.time() - c0
        pool.close()
    else:
        c0 = time.time()
        with ThreadPoolExecutor(workers) as ex:
            res = list(ex.map(lambda r: sc.score(by_id[r["id"]], r["text"]), rows))
        wall = time.time() - c0
    key = [(r["reward"], r.get("passed"), r.get("total"), r.get("reason")) for r in res]
    import resource  # noqa: PLC0415
    return {"completions": len(rows), "workers": workers, "early_exit": early_exit, "pool": use_pool,
            "scorer_process_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "score_s": round(wall, 2),
            "rewards_sha256": hashlib.sha256(json.dumps([k[0] for k in key]).encode()).hexdigest(),
            "full_result_sha256": hashlib.sha256(json.dumps(key).encode()).hexdigest(),
            "passes": sum(k[0] for k in key), "matches_gpu_job_rewards": sum(int(k[0] == r["reward"])
                                                                                for k, r in zip(key, rows)),
            "reasons": {b: sum(1 for k in key if (k[3] or "") == b) for b in sorted({k[3] or "" for k in key})},
            "cpu_count": os.cpu_count(), "seconds": round(time.time() - t0, 1)}


@function(volumes={"/vol": VOL}, timeout=600, cpu=4.0, memory=8192, block_network=True)
def smoke(config_text: str) -> dict:
    """CPU dry run in the SAME image, before any GPU call: everything the config will import must be in the image,
    and the same trainer features (Deletion Tuning, durable state, pause and resume) must run end to end on a tiny
    random model. Both GPU-only crashes of 15 Nov (a file missing from the image, a branch never run on CPU) would
    have failed here in seconds instead of on an H200."""
    import yaml  # noqa: PLC0415
    t0 = time.time()
    real = yaml.safe_load(config_text.replace("@WEIGHTS@", "/w").replace("@DATA@", "/d").replace("@RUN@", "/r")
                          .replace("@STEPS@", "4").replace("@DEADLINE@", "null"))
    sys.path.insert(0, f"{REMOTE}/rl-loop")
    import train  # noqa: PLC0415
    rt = real["train"]
    checks = {"algo_known": rt["algo"] in train.grpo.ALL_ALGOS}
    if rt.get("reward_pool"):
        import score_pool  # noqa: PLC0415
        checks["score_worker_file"] = score_pool.WORKER.exists()
    if rt.get("dt"):
        checks["dt_module"] = hasattr(train.load_dt(), "convert")
    tiny = yaml.safe_load(Path(f"{REMOTE}/rl-loop/config/smoke_objective_v1.yaml").read_text())
    tiny["verbose"], tiny["out_dir"] = False, "/root/tmp_smoke/out"
    tiny["train"].update(algo=rt["algo"], steps=4, eval_every=2, state_every=2, ppo_epochs=int(rt.get("ppo_epochs", 1)),
                         state_dir="/root/tmp_smoke/state", max_steps_this_call=2, lr=0.01)
    if rt.get("dt"):
        tiny["train"]["dt"] = {**rt["dt"], "targets": "attn", "alpha_start": 5.0, "alpha_end": 50.0, "eta": 0.05,
                               "calib_prompts": 8, "alpha_steps": 8}
    elif rt.get("trainable"):
        tiny["train"]["trainable"] = rt["trainable"]
    import copy  # noqa: PLC0415
    first = train.train(copy.deepcopy(tiny))
    tiny["train"].pop("max_steps_this_call")
    done = train.train(copy.deepcopy(tiny))
    checks.update(paused=first.get("status") == "PAUSED_AT_DEADLINE", resumed=done.get("resumed_from_step") == 2,
                  complete=done.get("status") == "COMPLETE")
    return {"ok": all(checks.values()), "checks": checks, "seconds": round(time.time() - t0, 1)}


def _smoke_or_exit(config_text: str) -> None:
    """Refuse to start a GPU call when the CPU dry run in the job image fails."""
    t0 = time.time()
    try:
        r = smoke.remote(config_text)
    except Exception as e:  # noqa: BLE001
        r = {"ok": False, "error": repr(e)[:800]}
    _log("smoke", "cpu-dry-run", t0, False, 4.0, 8.0, {"ok": r.get("ok")})
    print(json.dumps(r))
    if not r.get("ok"):
        raise SystemExit("CPU dry run in the job image failed; no GPU call was made")


# --- local side ------------------------------------------------------------------------------------

def _spent() -> float:
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(x)["usd"] for x in LEDGER.read_text().splitlines() if x.strip())


def _guard(worst: float) -> None:
    so_far = _spent()
    if so_far + worst > CAP_USD:
        raise SystemExit(f"refused: ledger ${so_far:.3f} + worst case ${worst:.3f} > cap ${CAP_USD}")
    print(f"budget ok: ledger ${so_far:.3f} + worst ${worst:.3f} <= cap ${CAP_USD}")


def _log(kind: str, run_id: str, started: float, gpu: bool, cpu: float, mem: float, extra: dict) -> None:
    wall = time.time() - started  # client wall time, includes container start: the conservative number
    row = {"kind": kind, "run_id": run_id, "client_wall_s": round(wall, 1), "usd": round(_cost(wall, gpu, cpu, mem), 4),
           "at": time.strftime("%Y-%m-%d %H:%M:%S"), **extra}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row))


def _data():
    d = WORK / "e1" / "data"
    return (d / "tasks.jsonl").read_text(), (d / "train_ids.txt").read_text(), (d / "heldout_ids.txt").read_text()


@local_entrypoint()
def weights():
    _guard(_cost(1800, False, 2.0, 4.0))
    t0 = time.time()
    r = download_weights.remote("7b")
    _log("weights", "weights-7b", t0, False, 2.0, 4.0, {"function_s": r["seconds"]})
    (WORK / "e1" / "weights.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))


@local_entrypoint()
def check():
    _guard(_cost(900, False, 4.0, 8.0))
    t0 = time.time()
    r = preflight.remote(*_data())
    _log("preflight", "preflight", t0, False, 4.0, 8.0, {"function_s": r["seconds"]})
    (WORK / "e1" / "preflight.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))


def _save(run_id: str, r: dict, call: int) -> None:
    od = WORK / "e1" / "runs" / run_id
    od.mkdir(parents=True, exist_ok=True)
    for key, name in (("summary", "summary.json"), ("status", "status.json"), ("screen", "screen.json"),
                      ("metrics", "metrics.jsonl"), ("evals", "evals.jsonl"), ("latest_state", "LATEST.json")):
        if r.get(key):
            (od / name).write_text(r[key])
    (od / f"log_tail_call{call}.txt").write_text(r.get("log_tail") or "")
    (od / f"call{call}.json").write_text(json.dumps({k: r[k] for k in ("run_id", "returncode", "gpu_name", "seconds",
                                                                       "usd")}))


def _stop_rule(evals_text: str | None) -> str | None:
    """Preregistered early stops, checked between calls on the held-out evaluations."""
    if not evals_text:
        return None
    held = [json.loads(x) for x in evals_text.splitlines() if x.strip()]
    held = sorted((e for e in held if e["name"] == "heldout"), key=lambda e: e["step"])
    if not held:
        return None
    base = held[0]["pass"]
    if held[-1].get("truncated", 0) > 0.25:
        return f"truncated share {held[-1]['truncated']} above 0.25 at step {held[-1]['step']}"
    if len(held) >= 3 and all(e["pass"] < 0.5 * base for e in held[-2:]):
        return f"held-out pass below half of step 0 ({base:.4f}) at two consecutive evaluations"
    return None


@local_entrypoint()
def e1(run_id: str, steps: int = 60, budget_s: int = 3000, grace_s: int = 900, max_calls: int = 3):
    config = (HERE / "cfg_e1.yaml").read_text()
    data = _data()
    _smoke_or_exit(config)
    for call in range(1, max_calls + 1):
        timeout = budget_s + grace_s + 300
        _guard(_cost(timeout + 180, True, GPU_CPU, GPU_MEM_GIB))
        t0 = time.time()
        r = run_call.with_options(timeout=timeout).remote(config, *data, run_id, steps, float(budget_s),
                                                          float(grace_s))
        _log("gpu_call", run_id, t0, True, GPU_CPU, GPU_MEM_GIB,
             {"call": call, "function_s": r["seconds"], "function_usd": r["usd"], "returncode": r["returncode"]})
        _save(run_id, r, call)
        print(json.dumps({k: r[k] for k in ("run_id", "returncode", "gpu_name", "seconds", "usd", "status")}))
        if r.get("summary"):
            print("COMPLETE" if json.loads(r["summary"]).get("status") == "COMPLETE" else "summary without COMPLETE")
            return
        if r["returncode"] != 0:
            raise SystemExit(f"call {call} ended with returncode {r['returncode']}; inspect the log before continuing")
        why = _stop_rule(r.get("evals"))
        if why:
            raise SystemExit(f"preregistered stop: {why}")
    print("max_calls reached; state is on the volume, run again to continue")


@local_entrypoint()
def rescore(run_id: str, limit: int = 512):
    rows = []
    for workers, early, pool in ((8, False, False), (8, True, False), (32, True, False), (32, True, True)):
        _guard(_cost(1200, False, 32.0, 16.0))
        t0 = time.time()
        r = rescore_fn.with_options(timeout=1200).remote(run_id, limit, workers, early, pool)
        _log("rescore", run_id, t0, False, 32.0, 16.0, {"workers": workers, "early_exit": early, "pool": pool,
                                                         "score_s": r["score_s"]})
        rows.append(r)
        print(json.dumps(r))
    (WORK / "e1" / f"rescore_{run_id}.json").write_text(json.dumps(rows, indent=1))


@local_entrypoint()
def e4(run_id: str, steps: int = 40, budget_s: int = 3000, grace_s: int = 600, max_calls: int = 2,
       config: str = "cfg_e4_dt.yaml", train_ids_file: str = "", pad_s: int = 300):
    """Deletion Tuning as the RL method on the E1 cohort (no screen): H200, same held-out set and evaluations.
    Function timeout = budget_s + grace_s + pad_s (pad_s covers the post-run file reads and volume commit; E4b
    needed about 10 s of it). The guard refuses a call whose worst case (timeout + 180 s) passes the cap."""
    cfg = (HERE / config).read_text()
    tasks_text, _, heldout_ids = _data()
    train_ids = Path(train_ids_file).read_text()
    _smoke_or_exit(cfg)
    rate = H200_RATE + GPU_CPU * CPU_RATE + H200_MEM_GIB * MEM_RATE
    for call in range(1, max_calls + 1):
        timeout = budget_s + grace_s + pad_s
        _guard((timeout + 180) * rate)
        t0 = time.time()
        r = run_call_h200.with_options(timeout=timeout).remote(cfg, tasks_text, train_ids, heldout_ids, run_id, steps,
                                                               float(budget_s), float(grace_s))
        wall = time.time() - t0
        row = {"kind": "gpu_call_h200", "run_id": run_id, "client_wall_s": round(wall, 1), "usd": round(wall * rate, 4),
               "at": time.strftime("%Y-%m-%d %H:%M:%S"), "call": call, "function_s": r["seconds"],
               "function_usd": r["usd"], "returncode": r["returncode"]}
        with open(LEDGER, "a") as f:
            f.write(json.dumps(row) + "\n")
        print(json.dumps(row))
        _save(run_id, r, call)
        if r.get("summary"):
            print("COMPLETE" if json.loads(r["summary"]).get("status") == "COMPLETE" else "summary without COMPLETE")
            return
        if r["returncode"] != 0:
            raise SystemExit(f"call {call} ended with returncode {r['returncode']}; inspect the log before continuing")
        why = _stop_rule(r.get("evals"))
        if why:
            raise SystemExit(f"preregistered stop: {why}")
    print("max_calls reached; state is on the volume, run again to continue")


@function(gpu="A100-80GB", volumes={"/vol": VOL}, timeout=1500, cpu=GPU_CPU, memory=int(GPU_MEM_GIB * 1024),
          block_network=True)
def sample_fn(run_id: str, cohort_ids: str, k: int) -> dict:
    """Completions from the base model and from the run's latest state, on the held-out set and the train cohort."""
    t0 = time.time()
    run, data = _protected_run_dirs(run_id)
    aud = run / "audit"
    aud.mkdir(exist_ok=True)
    os.chmod(aud, 0o700)
    _write_private(aud / "cohort_ids.txt", cohort_ids)
    env = {**os.environ, "G10_STDIO_RUNNER": "local", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "TMPDIR": "/root/tmp"}
    latest = json.loads((run / "state" / "LATEST.json").read_text())
    out = {"state_file": latest["file"], "state_step": latest["step"]}
    for tag, extra in (("base", []), ("trained", ["--state", str(run / "state" / latest["file"])])):
        dest = aud / f"completions_{tag}.jsonl"
        p = subprocess.run([sys.executable, f"{REMOTE}/rl-loop/sample_from_state.py", "--model", weights_path("7b"),
                            "--tasks", str(data / "tasks.jsonl"), "--ids", f"heldout={data / 'heldout_ids.txt'}",
                            "--ids", f"cohort={aud / 'cohort_ids.txt'}", "--out", str(dest), "--k", str(k), *extra],
                           capture_output=True, text=True, env=env)
        last = [x for x in p.stdout.strip().splitlines() if x.startswith("{")][-1:]
        out[tag] = json.loads(last[0]) if p.returncode == 0 and last else {"error": p.returncode,
                                                                            "stderr_tail": p.stderr[-2500:]}
        if dest.exists():
            os.chmod(dest, 0o600)
        VOL.commit()
    out["seconds"] = round(time.time() - t0, 1)
    return out


@local_entrypoint()
def sample(run_id: str = "e1a", k: int = 8):
    _guard(_cost(1500 + 180, True, GPU_CPU, GPU_MEM_GIB))
    t0 = time.time()
    r = sample_fn.remote(run_id, (WORK / "e1" / "private" / f"cohort_ids_{run_id}.txt").read_text(), k)
    _log("sample_from_state", run_id, t0, True, GPU_CPU, GPU_MEM_GIB, {"function_s": r["seconds"]})
    (WORK / "e1" / f"sample_{run_id}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))


@local_entrypoint()
def dryrun(config: str = "cfg_e4_dt.yaml"):
    """Only the CPU dry run of a config in the job image."""
    _smoke_or_exit((HERE / config).read_text())
