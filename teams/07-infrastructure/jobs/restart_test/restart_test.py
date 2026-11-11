"""Restart test: a trainer killed with SIGKILL is restarted by the supervisor and gives the same losses.

In simple words:
- Run A trains Team 05's tiny MoE from step 0 to step 200 without a stop. It saves a checkpoint every 25 steps.
- Run B is the same command under ckpt/supervisor.py. Once run B is past step 140 (and has a COMPLETE
  checkpoint), we kill it with SIGKILL: no warning, no chance to save, like a lost node or the OOM killer.
  The supervisor sees a crash and starts the same command again; the trainer restores the newest COMPLETE
  checkpoint (latest.json, MANIFEST written) and trains on to step 200.
- For every step 1..200 the training losses (next-token and t+2) of run B must be bit-equal to run A, and
  the batch data ID (global batch position + sha256 of the batch tokens) must be the same. For the steps run
  B did twice (between the checkpoint and the kill), the value after the restart is compared.
- The supervisor log must show exactly one restart (exit -9, SIGKILL) and then a normal finish, and the
  restart must start at the step after the checkpoint it named.

As a TSAI job (queue rules v1, docs/queue_rules_v1.md): run from teams/07-infrastructure/ with --run-id. Everything
goes to ./out/<run_id>/:

    logs/job.log             everything the job prints, each line "<UTC time> r0 ..." (R3)
    logs/events.jsonl        checkpoint.* / restore.* / supervisor.* events (R3)
    logs/supervisor.jsonl    one line per run B attempt
    ckpt/a/, ckpt/b/         ckpt.py layout per arm: latest.json, commits.jsonl, <branch>/step_<N>-e<E>/ (R4)
    rows/a.jsonl, b.jsonl    one row per step: losses, loss bits, batch data ID, attempt
    detail.json              every row of both runs and the supervisor log
    result.json              the R8 result, written last

The job stops itself before its time limit (--max-time-min, minus 5 minutes): it stops the trainer, writes
result.json with status stopped_at_limit and exits 75 (R1). Exit 0 and one PASS line when every check holds;
1 at the first difference; 78 if a run crashed.

    python jobs/restart_test/restart_test.py --run-id g7-restart-test-20261104-01 --device cpu    # the CPU test
    python jobs/restart_test/restart_test.py --run-id g7-restart-test-20261104-01 --device cuda   # the GPU job
    python jobs/restart_test/restart_test.py --report results/restart_cpu.txt   # local: jobs/restart_test/out/
"""
import argparse
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]                                   # teams/07-infrastructure
sys.path[:0] = [str(TEAM), str(TEAM / "jobs" / "restore_test")]
# Team 05's model, config, loss and data stream exactly as the restore test uses them (imported, never copied)
import restore_test as rt  # noqa: E402
from ckpt.supervisor import Supervisor, last_complete  # noqa: E402

FIELDS = rt.FIELDS
EXIT_RETRY, EXIT_FATAL = 75, 78
RESULT_SCHEMA = "g7-job-result/1"                        # queue rules R8
RUN_ID_RE = re.compile(r"^g7-[a-z0-9]+(?:-[a-z0-9]+)*-\d{8}-\d{2}$")   # queue rules R5
MAX_OUT_BYTES = 50 * 1024 * 1024                         # JOB_REQUEST.md: 50 MB or less
PRUNE_TO_BYTES = 45 * 1024 * 1024                        # aim lower, so logs and result.json still fit
MARGIN_S = 300                                           # R1: stop 5 min before the limit (half of a shorter one)
RECEIPTS = ("latest.json", "commits.jsonl", "MANIFEST.json")


def utc(t: float = None) -> str:
    return datetime.fromtimestamp(time.time() if t is None else t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ the trainer (one process, any attempt)
def trainer(a) -> int:
    import torch
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    dev = torch.device("cuda", 0) if a.device == "cuda" else torch.device("cpu")
    cfg = rt.load_cfg(a.config, a.tiny, a.steps)
    seed = int(cfg["run.seed"])
    torch.manual_seed(seed)
    model = rt.TinyMoE(cfg).to(dev)
    optim = torch.optim.AdamW(model.parameters(), lr=float(cfg["optim.lr"]))
    loader = rt.StreamLoader(cfg, seed, 0, 1)
    clip = float(cfg["run.grad_clip"])
    probe_batch = rt.stream_for(cfg, seed + 1)[:int(cfg["tiny.batch"])].to(dev)

    def probe(m) -> float:
        m.eval()
        with torch.no_grad():
            ntp, _ = rt.losses(m, probe_batch)
        m.train()
        return ntp.item()

    # R4: Checkpointer(run_id=<arm>, remote_root=./out/<run_id>/ckpt) writes ckpt/<arm>/...
    ck = rt.Checkpointer(a.arm, str(a.root / "scratch"), str(a.root / "ckpt"), config_path=str(a.tiny), seed=seed,
                         code_paths=rt.CODE_PATHS + (str(HERE / "restart_test.py"),))
    info = ck.restore(model, optim, loader, probe)          # newest COMPLETE checkpoint, or None: step 0
    step = info["step"] if info else 0
    attempt = int(os.environ.get("V5_RESTART_COUNT", "0"))
    (a.root / "rows").mkdir(exist_ok=True)
    with open(a.root / "rows" / f"{a.arm}.jsonl", "a") as f:
        while step < a.steps:
            batch_id = loader.next_batch_id()
            tokens = loader.next().to(dev)
            optim.zero_grad(set_to_none=True)
            ntp, mtp = rt.losses(model, tokens)
            (ntp + mtp).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
            optim.step()
            step += 1
            n, m = float(ntp.detach()), float(mtp.detach())
            f.write(json.dumps({"attempt": attempt, "step": step, "loss_ntp": n, "loss_mtp": m,
                                "loss_ntp_bits": rt.float_bits(n), "loss_mtp_bits": rt.float_bits(m),
                                "batch_id": batch_id}) + "\n")
            f.flush()
            if step % a.save_every == 0 or step == a.steps:
                if not ck.save(step, model, optim, loader, probe, reason="restart_test"):
                    return EXIT_FATAL
    return 0 if ck.wait() else EXIT_FATAL


# ------------------------------------------------------------------ helpers
def trainer_cmd(a, arm: str) -> list:
    return [sys.executable, str(Path(__file__).resolve()), "--trainer", "--arm", arm, "--root", str(a.root),
            "--device", a.device, "--steps", str(a.steps), "--save-every", str(a.save_every),
            "--config", str(a.config), "--tiny", str(a.tiny)]


def read_rows(path: Path) -> list:
    """Every complete row. A SIGKILL can land in the middle of a write, so a last line that does not parse is
    skipped: that step counts as not finished (the restarted trainer does it again)."""
    rows = []
    lines = [x for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
    for i, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except ValueError:
            if i != len(lines) - 1:
                raise                      # only the line being written at the kill may be cut
    return rows


def last_step(path: Path) -> int:
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4096))
            lines = [x for x in f.read().decode().splitlines() if x.strip()]
        return json.loads(lines[-1])["step"] if lines else 0
    except (OSError, ValueError, IndexError):
        return 0


def check(a, run_a: list, run_b: list, sup_rows: list, kill: dict) -> tuple:
    """(first problem or None, number of steps 1..N that are bit-equal in every field)."""
    by_a = {r["step"]: r for r in run_a}
    final_b = {}
    for r in run_b:                    # later attempts overwrite: the value after the restart counts
        final_b[r["step"]] = r
    equal = sum(1 for s in range(1, a.steps + 1)
                if s in by_a and s in final_b and all(by_a[s][k] == final_b[s][k] for k in FIELDS))
    for step in range(1, a.steps + 1):
        if step not in by_a or step not in final_b:
            return {"step": step, "field": "missing", "a": step in by_a, "b": step in final_b}, equal
        for k in FIELDS:
            if by_a[step][k] != final_b[step][k]:
                return {"step": step, "field": k, "a": by_a[step][k], "b": final_b[step][k]}, equal
    restarts = [r for r in sup_rows if r["action"] == "restart"]
    if len(restarts) != 1 or restarts[0]["rc"] != -signal.SIGKILL or sup_rows[-1].get("exit") != 0:
        return {"field": "supervisor log", "want": "one restart after SIGKILL (-9), then exit 0",
                "got": sup_rows}, equal
    from_step = restarts[0]["pointer_step"]
    second = [r["step"] for r in run_b if r["attempt"] == 1]
    # the trainer must have restored exactly the checkpoint latest.json pointed to (no silent fallback)
    if not (0 < from_step <= kill["step"] and from_step % a.save_every == 0 and second and second[0] == from_step + 1):
        return {"field": "restart step", "pointer_step": from_step, "killed_at": kill["step"],
                "first_step_after_restart": second[0] if second else None}, equal
    return None, equal


class Tee:
    """Job mode (R3): everything this process and its children print also goes to logs/job.log, each line
    starting with the UTC time and the rank. Works at the file-descriptor level, so the trainers' output and
    torch's own warnings are caught too."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.log = open(path, "a", encoding="utf-8")
        sys.stdout.flush()
        sys.stderr.flush()
        self.saved = (os.dup(1), os.dup(2))
        r, w = os.pipe()
        os.dup2(w, 1)
        os.dup2(w, 2)
        os.close(w)
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
        self.thread = threading.Thread(target=self._pump, args=(r,), daemon=True)
        self.thread.start()

    def _pump(self, r):
        with os.fdopen(r, "rb") as src:
            for raw in src:
                text = raw.decode("utf-8", "replace").rstrip("\n")
                self.log.write(f"{utc()} r0 {text}\n")
                self.log.flush()
                os.write(self.saved[0], raw)

    def close(self):
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(self.saved[0], 1)          # closes the pipe's write end: the pump sees the end and stops
        os.dup2(self.saved[1], 2)
        self.thread.join(timeout=10)
        self.log.close()


def merge_events(root: Path) -> None:
    """common/events.py writes one file per process; R3 wants one logs/events.jsonl, in time order."""
    src = root / "logs" / "events.d"
    lines = []
    for p in sorted(src.glob("*.jsonl")) if src.exists() else []:
        lines += [x for x in p.read_text().splitlines() if x.strip()]
    lines.sort(key=lambda x: json.loads(x).get("time", ""))
    (root / "logs" / "events.jsonl").write_text("".join(x + "\n" for x in lines))
    shutil.rmtree(src, ignore_errors=True)


def folder_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def prune_to_limit(root: Path, limit: int = PRUNE_TO_BYTES) -> list:
    """R4: keep the receipts (latest.json, commits.jsonl, MANIFEST.json, sums_rank<r>.json) and delete shard
    files over the limit, oldest step first, newest step last. Returns the step folders that lost shards.
    The size is measured once and counted down, so this stays fast with hundreds of step folders."""
    pruned, size = [], folder_bytes(root)
    steps = sorted((p for p in (root / "ckpt").glob("*/*/step_*") if p.is_dir()),
                   key=lambda p: int(re.match(r"step_(\d+)", p.name).group(1)))
    for d in steps:
        if size <= limit:
            break
        for f in d.rglob("*"):
            if f.is_file() and f.name not in RECEIPTS and not f.name.startswith("sums_rank"):
                size -= f.stat().st_size
                f.unlink()
        pruned.append(str(d.relative_to(root)))
    return pruned


# ------------------------------------------------------------------ the test
def run_test(a) -> int:
    import torch
    root = a.root
    if root.exists():
        shutil.rmtree(root)
    (root / "logs").mkdir(parents=True)
    tee = Tee(root / "logs" / "job.log") if a.run_id else None
    started = time.time()
    limit_s = a.max_time_min * 60
    margin_s = min(MARGIN_S, limit_s / 2)                # time left for the stop, the clean-up and result.json
    deadline = started + limit_s - margin_s
    os.environ.update(V5_EVENTS_DIR=str(root / "logs" / "events.d"), RUN_ID=a.run_id or root.name)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    if a.device == "cuda":
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")      # R7: deterministic cuBLAS
    timed_out = threading.Event()
    sup = None
    running = {}

    def at_deadline():
        timed_out.set()
        print(f"time limit: {a.max_time_min} min minus {int(margin_s)} s reached, stopping", flush=True)
        if running.get("a") is not None and running["a"].poll() is None:
            running["a"].terminate()
        if sup is not None:
            sup._forward(signal.SIGTERM, None)           # no restart after this, the child gets SIGTERM
    timer = threading.Timer(max(0.0, deadline - time.time()), at_deadline)
    timer.daemon = True
    timer.start()

    status, code, diff, equal, numbers = "fail", EXIT_FATAL, None, 0, {}
    sup_rows, run_a, run_b, kill = [], [], [], {}
    try:
        print(f"restart_test: run {os.environ['RUN_ID']}, device {a.device}, steps {a.steps}, "
              f"save every {a.save_every}, kill after step {a.kill_at}, torch {torch.__version__}", flush=True)
        t0 = time.time()
        running["a"] = subprocess.Popen(trainer_cmd(a, "a"))
        rc_a = running["a"].wait()
        t_a = time.time() - t0
        if timed_out.is_set():
            raise TimeoutError
        if rc_a != 0:
            raise RuntimeError(f"run A crashed (exit {rc_a})")

        run_url = str(root / "ckpt" / "b")
        rows_b = root / "rows" / "b.jsonl"

        def killer(proc, attempt):
            if attempt != 0:
                return

            def watch():
                while proc.poll() is None:
                    s = last_step(rows_b)
                    ck = last_complete(run_url) if s >= a.kill_at else None
                    if ck and ck.get("step"):
                        proc.send_signal(signal.SIGKILL)
                        kill.update(step=s, last_complete_seen=ck["step"], time=time.time())
                        return
                    time.sleep(0.005)
            threading.Thread(target=watch, daemon=True).start()

        t1 = time.time()
        sup = Supervisor(trainer_cmd(a, "b"), run_url=run_url, log_path=str(root / "logs" / "supervisor.jsonl"),
                         max_restarts=3, backoff_s=0, on_start=killer)
        rc_b = sup.run()
        t_b = time.time() - t1
        sup_rows = read_rows(root / "logs" / "supervisor.jsonl")
        if timed_out.is_set():
            raise TimeoutError
        if rc_b != 0 or not kill:
            raise RuntimeError(f"run B exit {rc_b}, killed: {bool(kill)}")

        run_a, run_b = read_rows(root / "rows" / "a.jsonl"), read_rows(rows_b)
        kill["step"] = max(r["step"] for r in run_b if r["attempt"] == 0)   # last step the killed child finished
        diff, equal = check(a, run_a, run_b, sup_rows, kill)
        restart = next(r for r in sup_rows if r["action"] == "restart")
        after = [r["step"] for r in run_b if r["attempt"] == 1]
        restored = after[0] - 1 if after else None      # what the trainer really loaded (its first step - 1)
        numbers = {"bit_equal_steps": equal, "compared_steps": a.steps, "killed_after_step": kill["step"],
                   "restarted_from_step": restored, "pointer_step": restart["pointer_step"],
                   "redone_steps": kill["step"] - restored if restored is not None else None,
                   "restarts": len([r for r in sup_rows if r["action"] == "restart"]),
                   "run_a_s": round(t_a, 1), "run_b_s": round(t_b, 1), "torch": torch.__version__}
        status, code = ("pass", 0) if diff is None else ("fail", 1)
        where = (f"{a.device}: SIGKILL after step {kill['step']}, restarted from COMPLETE checkpoint step "
                 f"{restored}, steps 1-{a.steps}")
        line = (f"PASS restart_test {where}: loss_ntp and loss_mtp bit-equal, data ids equal" if diff is None
                else f"FAIL restart_test {where}: {json.dumps(diff)[:600]}")
    except TimeoutError:
        status, code = "stopped_at_limit", EXIT_RETRY
        line = f"STOPPED restart_test: time limit ({a.max_time_min} min minus {int(margin_s)} s)"
    except Exception as e:  # noqa: BLE001 - a crash is a failed test with a clear line, not a traceback
        line = f"FAIL restart_test: {type(e).__name__}: {e}"
    finally:
        timer.cancel()
        if sup is None and running.get("a") is not None and running["a"].poll() is None:
            running["a"].kill()

    print(line, flush=True)
    numbers.setdefault("first_diff", diff)
    detail = {"pass": status == "pass", "first_diff": diff, "device": a.device, "nproc": 1, "steps": a.steps,
              "save_every": a.save_every, "kill_at": a.kill_at, **numbers, "fields": FIELDS,
              "supervisor": sup_rows, "run_a": run_a, "run_b": run_b}
    (root / "detail.json").write_text(json.dumps(detail, indent=1) + "\n")
    if a.report and status == "pass":
        write_report(a, detail, line)
    if tee:
        tee.close()
    merge_events(root)
    shutil.rmtree(root / "scratch", ignore_errors=True)    # node-local copies; the store copies stay (R4)
    numbers["pruned_step_folders"] = prune_to_limit(root)
    ended = time.time()
    result = {"schema": RESULT_SCHEMA, "run_id": a.run_id or root.name, "status": status, "exit_code": code,
              "device_kind": "gpu" if a.device == "cuda" else "cpu", "device_count": 1 if a.device == "cuda" else 0,
              "max_time_min": a.max_time_min, "elapsed_s": round(ended - started, 1),
              "started_utc": utc(started), "ended_utc": utc(ended), "numbers": numbers}
    (root / "result.json").write_text(json.dumps(result, indent=1) + "\n")     # R8: written last
    return code


def write_report(a, r: dict, line: str) -> None:
    import numpy
    import torch
    rel = os.path.relpath(Path(__file__).resolve(), TEAM)
    other = ""
    if getattr(a, "other_kills", None):
        other = "\nOther kill points (same command with --kill-at N):\n" + "\n".join(f"  {x}" for x in a.other_kills) + "\n"
    sup = "\n".join(f"  attempt {s['attempt']}: exit {s['rc']} ({s['meaning']}) -> {s['action']}"
                    + (f" (latest.json at step {s['pointer_step']})" if s["action"] == "restart" else f", supervisor exit {s['exit']}")
                    for s in r["supervisor"])
    text = f"""Restart test on CPU, Team 05 tiny MoE, ckpt/supervisor.py
Date: {time.strftime('%d %b %Y')}

Commands (from teams/07-infrastructure/; CUDA_VISIBLE_DEVICES="" hides any GPU so it runs on CPU only):

  CUDA_VISIBLE_DEVICES="" python {rel} --also-kill-at 31,99,164 --report results/restart_cpu.txt
      (output in jobs/restart_test/out/, git-ignored)
  CUDA_VISIBLE_DEVICES="" python {rel} --run-id g7-restart-test-20261104-01 --device cpu
      (the job form, queue rules v1: output in ./out/g7-restart-test-20261104-01/, checked with
       python queue/queue_rules.py check-out ./out --run-id g7-restart-test-20261104-01)

Environment:
  Python   {platform.python_version()}
  torch    {torch.__version__} (CPU only)
  numpy    {numpy.__version__}
  OS       {platform.platform()}
  Team 05 config: teams/05-architecture/configs/config_v0.yaml + teams/05-architecture/configs/small/tiny_moe.yaml
  seed {rt.load_cfg(a.config, a.tiny, a.steps)['run.seed']} (run.seed in config_v0.yaml)

What it does:
  Run A: steps 1-{a.steps}, no stop, checkpoint every {a.save_every} steps.
  Run B: the same command under ckpt/supervisor.py. Killed with SIGKILL once past step {a.kill_at} and a COMPLETE
         checkpoint exists. The supervisor restarts the same command; the trainer restores latest.json.
  Compared: loss_ntp and loss_mtp bits and the batch data ID for every step 1-{a.steps} (for steps run B did
            twice, the value after the restart).

Bit equality is between run A and run B on the same machine; the numbers are not expected to match other
OSes (the restore test results are from Ubuntu and Windows).

Result: {'PASS' if r['pass'] else 'FAIL'}

  killed after step          {r['killed_after_step']}
  restarted from step        {r['restarted_from_step']} (first step of the restarted trainer, minus 1)
  latest.json at the restart {r['pointer_step']} (the last COMPLETE checkpoint: MANIFEST.json written, latest.json moved)
  steps done twice           {r['redone_steps']} (step {r['restarted_from_step'] + 1} to {r['killed_after_step']})
  bit-equal steps            {r['bit_equal_steps']} of {r['compared_steps']}, fields {', '.join(FIELDS)}
  wall time                  run A {r['run_a_s']} s, run B {r['run_b_s']} s

Supervisor log (logs/supervisor.jsonl):
{sup}

Last line:
  {line}
{other}"""
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default=None,
                    help="job run ID g7-<name>-<YYYYMMDD>-<NN> (queue rules R5): output goes to ./out/<run_id>/")
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu", help="cpu, or cuda (1 GPU)")
    ap.add_argument("--max-time-min", type=int, default=30,
                    help="the request's Max time; the job stops itself 5 min before it (R1, default 30)")
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--save-every", type=int, default=25, help="checkpoint every N steps")
    ap.add_argument("--kill-at", type=int, default=140, help="SIGKILL run B once it is past this step")
    ap.add_argument("--out", type=Path, default=HERE / "out", help="output folder without --run-id")
    ap.add_argument("--report", default=None, help="also write a plain-text result file here")
    ap.add_argument("--also-kill-at", default="", help="comma list: also run with these kill points and add "
                    "their result lines to --report (e.g. 31,99,164); not with --run-id")
    ap.add_argument("--config", type=Path, default=rt.CONFIGS / "config_v0.yaml")
    ap.add_argument("--tiny", type=Path, default=rt.CONFIGS / "small" / "tiny_moe.yaml")
    ap.add_argument("--trainer", action="store_true", help=argparse.SUPPRESS)   # one attempt of the trainer
    ap.add_argument("--arm", default="a", help=argparse.SUPPRESS)
    ap.add_argument("--root", type=Path, default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.trainer:
        return trainer(a)
    if not (0 < a.save_every <= a.kill_at < a.steps):
        ap.error("need 0 < --save-every <= --kill-at < --steps")
    if a.run_id is not None and not RUN_ID_RE.match(a.run_id):
        ap.error(f"--run-id {a.run_id!r} must look like g7-<short-name>-<YYYYMMDD>-<NN> (queue rules R5)")
    if a.run_id and a.also_kill_at:
        ap.error("--also-kill-at is for local runs: one job request runs one kill point")
    if a.max_time_min < 1:
        ap.error("--max-time-min must be at least 1")
    import torch
    # torch.__version__ is a TorchVersion: it compares as a version ("2.9.0" < "2.14.1"; "2.15.0a0+git" passes),
    # the same check as restore_test.py
    if torch.__version__ < rt.MIN_TORCH:
        ap.error(f"needs torch >= {rt.MIN_TORCH} (the restore test's pin), found {torch.__version__}")
    if a.device == "cuda" and not torch.cuda.is_available():
        ap.error("--device cuda but no GPU is visible")
    a.root = (Path("out") / a.run_id).resolve() if a.run_id else a.out.resolve()
    a.config, a.tiny = a.config.resolve(), a.tiny.resolve()
    a.other_kills = []
    for k in [int(x) for x in a.also_kill_at.split(",") if x.strip()]:
        b = argparse.Namespace(**vars(a))
        b.kill_at, b.report, b.root = k, None, a.root.parent / f"{a.root.name}_kill{k}"
        if not (0 < b.save_every <= k < b.steps):
            ap.error(f"--also-kill-at {k}: need --save-every <= N < --steps")
        rc, lines = run_captured(b)
        a.other_kills.append(lines[-1] if lines else f"--kill-at {k}: no result line (exit {rc})")
        if rc != 0:
            print(a.other_kills[-1], file=sys.stderr)
            return rc
    return run_test(a)


def run_captured(a) -> tuple:
    """run_test() for one extra kill point; returns (exit code, PASS/FAIL lines it printed)."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_test(a)
    return rc, [x for x in buf.getvalue().splitlines() if x.startswith(("PASS", "FAIL", "STOPPED"))]


if __name__ == "__main__":
    sys.exit(main())
