"""WP5 pilot on Modal: Qwen2.5-Coder-1.5B-Instruct, rl-loop/train.py with algo objective_v1 on RL data v1 stdio tasks.

    M=~/.venvs/modal312/bin/modal
    $M run modal_app.py::weights
    $M run modal_app.py::pilot --config cfg.yaml --run-id fitA --timeout-s 900

One app, one GPU function at a time, finite timeouts. Spend guard: refuses a call whose worst case (timeout x rate)
would take this task's ledger (spend.jsonl, here) past GUARD_USD. Rates: modal.com/pricing as recorded 5 Nov 2026
(L40S $0.000542/s, CPU $0.0000131/core-s, memory $0.00000222/GiB-s); the user-stated L40S+2CPU+32GiB rate
$0.00063924/s matches. These are estimates of function cost, not the billing dashboard.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
TEAM = (Path(os.environ.get("G10_TEAM_DIR", HERE.parents[2] / "research/repos/g10-rl-v5-wt/teams/10-post-training"))
        if modal.is_local() else Path("/root/team"))  # the container re-imports this file from /root
REMOTE = "/root/team"
MODELS = {"1.5b": ("Qwen/Qwen2.5-Coder-1.5B-Instruct", "2e1fd397ee46e1388853d2af2c993145b0f1098a"),
          "7b": ("Qwen/Qwen2.5-Coder-7B-Instruct", "c03e6d358207e414f1eca0bb1891e29f1db0e242")}  # both apache-2.0


def weights_path(key: str) -> str:
    repo, rev = MODELS[key]
    return f"/vol/hf/{repo.split('/')[1]}@{rev[:12]}"


WEIGHTS = weights_path("1.5b")  # tokenizer for the CPU preflight (same tokenizer family)
GPU_RATES = {"L40S": 0.000542, "A100-80GB": 0.000694}
GPU_RATE, CPU_RATE, MEM_RATE = 0.000542, 0.0000131, 0.00000222
CPU, MEM_GIB = 8.0, 32.0
TOTAL_CAP_USD, GUARD_USD = 2.90, 2.55  # guard leaves ~0.35 for billing overhead, image build, rounding
LEDGER = HERE / "spend.jsonl"

VOL = modal.Volume.from_name("g10-wp5-rl-2026-11-15", create_if_missing=True, version=2)
IGNORE = ["**/__pycache__/**", "**/out/**", "**/*.pyc", "**/.pytest_cache/**"]
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
    .add_local_file(HERE / "isolation_probe.py", "/root/probe/isolation_probe.py")
)
app = modal.App("g10-wp5-rl-pilot-2026-11-15", image=image)
function, local_entrypoint = app.function, app.local_entrypoint


def _cost(gpu, seconds: float, cpu: float, mem: float) -> float:
    rate = GPU_RATES[gpu] if isinstance(gpu, str) else (GPU_RATE if gpu else 0.0)
    return seconds * (rate + cpu * CPU_RATE + mem * MEM_RATE)


@function(volumes={"/vol": VOL}, timeout=900, cpu=2.0, memory=4096)
def download_weights(key: str = "1.5b") -> dict:
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
    secs = time.time() - t0
    return {"weights": dest, "revision": rev, "safetensors_sha256": shas, "seconds": round(secs, 1),
            "usd": round(_cost(False, secs, 2.0, 4.0), 4), "files": sorted(p.name for p in Path(dest).iterdir())}


def _protected_run_dirs(run_id: str):
    """Expected answers live here: root-only (0700 folders, 0600 files) so sandboxed programs cannot read them."""
    os.umask(0o077)
    os.chmod("/root", 0o700)  # team code and this app (no answers, but nothing for sandboxed programs to browse)
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


@function(volumes={"/vol": VOL}, timeout=600, cpu=2.0, memory=4096, block_network=True)
def preflight(tasks_text: str, train_ids: str, heldout_ids: str) -> dict:
    """CPU only: (1) isolation probes, (2) the real task construction the GPU job will do, with the cached tokenizer."""
    t0 = time.time()
    sys.path.insert(0, "/root/probe")
    import isolation_probe  # noqa: PLC0415
    run, data = _protected_run_dirs("_preflight")  # same hardening as run_pilot, before any sandboxed program
    res = {"isolation": isolation_probe.main(REMOTE, "/vol/runs/_probe_private/data")}
    for name, text in (("tasks.jsonl", tasks_text), ("train_ids.txt", train_ids), ("heldout_ids.txt", heldout_ids)):
        _write_private(data / name, text)
    os.environ["G10_STDIO_RUNNER"] = "local"
    sys.path.insert(0, f"{REMOTE}/rl-loop")
    import train  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415
    tok = AutoTokenizer.from_pretrained(WEIGHTS, local_files_only=True)
    task = train.stdio_task({"tasks": str(data / "tasks.jsonl"), "train_ids": str(data / "train_ids.txt"),
                             "heldout_ids": str(data / "heldout_ids.txt")}, tok)
    lens = [len(p) for p in task.train + task.heldout]
    res["task"] = {"train": len(task.train), "heldout": len(task.heldout), "max_prompt_tokens": max(lens),
                   "eos": tok.eos_token_id, "empty_completion_reward": task.reward(task.train[0], tok.encode("x"))}
    res["perms"] = {str(p): oct(p.stat().st_mode & 0o777) for p in (Path("/vol/runs"), run, data, data / "tasks.jsonl")}
    secs = time.time() - t0
    res.update(seconds=round(secs, 1), usd=round(_cost(False, secs, 2.0, 4.0), 4))
    return res


def _pilot_body(gpu: str, config_text: str, tasks_text: str, train_ids: str, heldout_ids: str, run_id: str,
                max_seconds: float, model_key: str) -> dict:
    t0 = time.time()
    WEIGHTS = weights_path(model_key)  # noqa: N806
    run, data = _protected_run_dirs(run_id)
    for name, text in (("tasks.jsonl", tasks_text), ("train_ids.txt", train_ids), ("heldout_ids.txt", heldout_ids)):
        _write_private(data / name, text)
    cfg = config_text.replace("@WEIGHTS@", WEIGHTS).replace("@DATA@", str(data))
    (run / "config.yaml").write_text(cfg)
    env = {**os.environ, "G10_STDIO_RUNNER": "local", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "TMPDIR": "/root/tmp"}
    rc = "not started"
    with open(run / "stdout.log", "w") as log:
        try:
            rc = subprocess.run([sys.executable, f"{REMOTE}/rl-loop/train.py", "--config", str(run / "config.yaml"),
                                 "--out-dir", str(run / "out")], stdout=log, stderr=subprocess.STDOUT, env=env,
                                timeout=max_seconds).returncode
        except subprocess.TimeoutExpired:
            rc = "killed: max_seconds reached"
    gpu_name = None
    try:
        gpu_name = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                                  text=True).stdout.strip()
    except OSError:
        pass
    out = run / "out"
    read = lambda p: p.read_text() if p.exists() else None  # noqa: E731
    secs = time.time() - t0
    res = {"run_id": run_id, "returncode": rc, "gpu_name": gpu_name, "seconds": round(secs, 1),
           "usd": round(_cost(gpu, secs, CPU, MEM_GIB), 4), "summary": read(out / "summary.json"),
           "screen": read(out / "screen.json"), "metrics": read(out / "metrics.jsonl"),
           "log_tail": (read(run / "stdout.log") or "")[-6000:]}
    (run / "cost.json").write_text(json.dumps({k: res[k] for k in ("seconds", "usd", "gpu_name", "returncode")}))
    VOL.commit()
    return res


@function(gpu="L40S", volumes={"/vol": VOL}, timeout=3600, cpu=CPU, memory=int(MEM_GIB * 1024), block_network=True)
def run_pilot(config_text, tasks_text, train_ids, heldout_ids, run_id, max_seconds, model_key="1.5b") -> dict:
    return _pilot_body("L40S", config_text, tasks_text, train_ids, heldout_ids, run_id, max_seconds, model_key)


@function(gpu="A100-80GB", volumes={"/vol": VOL}, timeout=3600, cpu=CPU, memory=int(MEM_GIB * 1024),
          block_network=True)
def run_pilot_a100(config_text, tasks_text, train_ids, heldout_ids, run_id, max_seconds, model_key="7b") -> dict:
    return _pilot_body("A100-80GB", config_text, tasks_text, train_ids, heldout_ids, run_id, max_seconds, model_key)


def _spent() -> float:
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(x)["usd_worst_or_actual"] for x in LEDGER.read_text().splitlines() if x.strip())


def _guard(worst: float) -> None:
    so_far = _spent()
    if so_far + worst > GUARD_USD:
        raise SystemExit(f"refused: ledger ${so_far:.3f} + worst case ${worst:.3f} > guard ${GUARD_USD} "
                         f"(total cap ${TOTAL_CAP_USD})")
    print(f"budget ok: ledger ${so_far:.3f} + worst ${worst:.3f} <= guard ${GUARD_USD}")


def _log(kind: str, run_id: str, res: dict, started: float, gpu=None) -> None:
    wall = time.time() - started  # client wall time incl. container start: the conservative number
    est = _cost(gpu, wall, CPU if gpu else 2.0, MEM_GIB if gpu else 4.0)
    row = {"kind": kind, "run_id": run_id, "function_seconds": res.get("seconds"), "function_usd": res.get("usd"),
           "client_wall_seconds": round(wall, 1), "usd_worst_or_actual": round(max(est, res.get("usd") or 0), 4),
           "gpu_name": res.get("gpu_name"), "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row))


@local_entrypoint()
def weights(key: str = "1.5b"):
    _guard(_cost(False, 900, 2.0, 4.0))
    t0 = time.time()
    r = download_weights.remote(key)
    _log("weights", f"weights-{key}", r, t0)
    print(json.dumps(r, indent=1))


@local_entrypoint()
def check(data_dir: str = str(HERE / "data")):
    _guard(_cost(False, 600 + 120, 2.0, 4.0))
    d = Path(data_dir)
    t0 = time.time()
    r = preflight.remote((d / "pilot_tasks.jsonl").read_text(), (d / "train_ids.txt").read_text(),
                         (d / "heldout_ids.txt").read_text())
    _log("preflight", "preflight", r, t0, None)
    (HERE / "preflight.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))


@local_entrypoint()
def pilot(config: str, run_id: str, timeout_s: int = 900, data_dir: str = str(HERE / "data"),
          train_ids_file: str = "", gpu: str = "L40S", model_key: str = "1.5b"):
    worst = _cost(gpu, timeout_s + 180, CPU, MEM_GIB)  # + container start / image pull / teardown
    _guard(worst)
    d = Path(data_dir)
    t0 = time.time()
    fn = {"L40S": run_pilot, "A100-80GB": run_pilot_a100}[gpu]
    r = fn.with_options(timeout=timeout_s + 120).remote(
        Path(config).read_text(), (d / "pilot_tasks.jsonl").read_text(),
        Path(train_ids_file).read_text() if train_ids_file else (d / "train_ids.txt").read_text(),
        (d / "heldout_ids.txt").read_text(), run_id, float(timeout_s), model_key)
    _log("pilot", run_id, r, t0, gpu)
    od = HERE / "runs" / run_id
    od.mkdir(parents=True, exist_ok=True)
    for key in ("summary", "screen", "metrics", "log_tail"):
        if r.get(key):
            (od / {"summary": "summary.json", "screen": "screen.json", "metrics": "metrics.jsonl",
                   "log_tail": "log_tail.txt"}[key]).write_text(r[key])
    print(json.dumps({k: r[k] for k in ("run_id", "returncode", "gpu_name", "seconds", "usd")}))
