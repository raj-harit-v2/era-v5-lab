"""Independent audit of the stdio reward with tests the reward never used.

    modal run modal_audit.py::audit --run-id e1a

RL data v1 keeps the first 20 tests of each code_contests problem; the pinned source row has more (median 101).
A completion that earned reward 1 on the kept 20 is run here on the unused source tests. A failure there is a false
positive of the reward as built (or a time-limit failure, counted separately). The unused tests never enter training.

Step 1 (network, no sandbox): fetch the pinned parquet shards and write the unused tests to the volume, root-only.
Step 2 (network blocked): run every reward-1 completion of the screen on them through the scorer pool.
Prints counts only.
"""
import json
import os
import sys
import time
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[2] if modal.is_local() else Path("/root/team")
REMOTE = "/root/team"
WORK = Path(os.environ.get("G10_E1_WORK", "")) if modal.is_local() else Path("/nonexistent")
LEDGER = WORK / "SPEND.jsonl"
DATASET, REVISION = "deepmind/code_contests", "802411c3010cb00d1b05bad57ca77365a3c699d6"
CPU_RATE, MEM_RATE = 0.0473 / 3600, 0.008 / 3600
CHUNK, MAX_HIDDEN = 20, 80  # stdio_check.score runs at most 20 tests per call

VOL = modal.Volume.from_name("g10-fable-e1-2026-11-15", version=2)
fetch_image = modal.Image.debian_slim(python_version="3.12").uv_pip_install("pyarrow", "huggingface_hub[hf_xet]")
run_image = (
    modal.Image.debian_slim(python_version="3.12")
    .add_local_dir(TEAM / "rl-data", f"{REMOTE}/rl-data", ignore=["**/__pycache__/**"])
    .add_local_file(TEAM / "rl-loop" / "score_pool.py", f"{REMOTE}/rl-loop/score_pool.py")
    .add_local_file(TEAM / "rl" / "verifier.py", f"{REMOTE}/rl/verifier.py")
)
app = modal.App("g10-fable-audit-2026-11-15")
function, local_entrypoint = app.function, app.local_entrypoint  # alias: pr-guard flags an added line that starts with a dotted decorator as an email


@function(image=fetch_image, volumes={"/vol": VOL}, timeout=3600, cpu=4.0, memory=16384)
def fetch_hidden(run_id: str, sources: list | None = None, out_name: str = "hidden_tests.jsonl") -> dict:
    import hashlib

    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    t0 = time.time()
    os.umask(0o077)
    run = Path("/vol/runs") / run_id
    tasks = {}
    for line in (run / "data" / "tasks.jsonl").read_text().splitlines():
        if line.strip():
            t = json.loads(line)
            tasks[t["id"]] = t
    passed = {}
    for src in (sources or ["screen_completions.jsonl"]):
        for line in (run / src).read_text().splitlines():
            r = json.loads(line)
            if r["reward"] == 1.0:
                passed[r["id"]] = passed.get(r["id"], 0) + 1
    by_file: dict = {}
    for tid in passed:
        by_file.setdefault(tasks[tid]["provenance"]["file"], []).append(tid)
    out_dir = run / "audit"
    out_dir.mkdir(exist_ok=True)
    os.chmod(out_dir, 0o700)
    stats = {"tasks_with_a_pass": len(passed), "files": len(by_file), "kept_prefix_mismatch": 0, "no_hidden_tests": 0,
             "hidden_tests": 0, "file_sha_mismatch": 0}
    with open(out_dir / out_name, "w") as f:
        for fname, tids in sorted(by_file.items()):
            try:
                path = hf_hub_download(DATASET, f"data/{fname}", repo_type="dataset", revision=REVISION)
            except Exception:  # noqa: BLE001  (layout without the data/ folder)
                path = hf_hub_download(DATASET, fname, repo_type="dataset", revision=REVISION)
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != tasks[tids[0]]["provenance"]["file_sha256"]:
                stats["file_sha_mismatch"] += 1
                continue
            table = pq.read_table(path, columns=["public_tests", "private_tests", "generated_tests"])
            for tid in tids:
                row = table.slice(tasks[tid]["provenance"]["source_ordinal"], 1).to_pylist()[0]
                tests = []
                for key in ("public_tests", "private_tests", "generated_tests"):
                    t = row.get(key) or {}
                    tests += [{"input": i, "output": o} for i, o in zip(t.get("input", []), t.get("output", []))]
                kept = tasks[tid]["tests"]
                if tests[:len(kept)] != kept:  # not the row the task was built from: do not audit with it
                    stats["kept_prefix_mismatch"] += 1
                    continue
                hidden = tests[len(kept):len(kept) + MAX_HIDDEN]
                if not hidden:
                    stats["no_hidden_tests"] += 1
                    continue
                stats["hidden_tests"] += len(hidden)
                f.write(json.dumps({"id": tid, "time_limit_s": tasks[tid].get("time_limit_s", 4), "judge": tasks[tid]["judge"],
                                    "tests": hidden}) + "\n")
    os.chmod(out_dir / out_name, 0o600)
    VOL.commit()
    stats["seconds"] = round(time.time() - t0, 1)
    return stats


@function(image=run_image, volumes={"/vol": VOL}, timeout=3600, cpu=32.0, memory=16384, block_network=True)
def run_audit(run_id: str, source: str = "screen_completions.jsonl", hidden_name: str = "hidden_tests.jsonl") -> dict:
    t0 = time.time()
    os.umask(0o077)
    os.chmod("/root", 0o700)
    os.chmod("/vol/runs", 0o700)
    os.environ["G10_STDIO_RUNNER"] = "local"
    sys.path.insert(0, f"{REMOTE}/rl-loop")
    import score_pool

    run = Path("/vol/runs") / run_id
    # the hidden tests and the task file hold expected outputs: stdio_check.preflight_isolation checks both folders
    os.environ["G10_STDIO_SECRET_PATHS"] = os.pathsep.join([str(run / "audit"), str(run / "data")])
    hidden = {}
    for line in (run / "audit" / hidden_name).read_text().splitlines():
        t = json.loads(line)
        hidden[t["id"]] = t
    all_rows = [json.loads(line) for line in (run / source).read_text().splitlines()]
    rows = [r for r in all_rows if r["reward"] == 1.0 and r["id"] in hidden]
    items, owner = [], []
    for i, r in enumerate(rows):
        t = hidden[r["id"]]
        for c in range(0, len(t["tests"]), CHUNK):
            items.append(({"id": t["id"], "time_limit_s": t["time_limit_s"], "tests": t["tests"][c:c + CHUNK]}, r["text"]))
            owner.append(i)
    pool = score_pool.ScorePool(32)
    res = pool.score(items)
    pool.close()
    verdict = ["pass"] * len(rows)
    for i, r in zip(owner, res):
        if r["reward"] != 1 and verdict[i] == "pass":
            why = str(r.get("reason", ""))
            verdict[i] = ("timeout" if why.startswith("timeout") else "runtime_error" if why.startswith("error")
                          else "wrong_answer" if why.startswith("wrong") else "other")
    by_judge: dict = {}
    by_task: dict = {}
    for r, v in zip(rows, verdict):
        j = by_judge.setdefault(hidden[r["id"]]["judge"], {})
        j[v] = j.get(v, 0) + 1
        t = by_task.setdefault(r["id"], {"n": 0, "fail": 0})
        t["n"] += 1
        t["fail"] += v != "pass"
    counts = {v: verdict.count(v) for v in sorted(set(verdict))}
    by_set: dict = {}
    for r in all_rows:  # pass rate on the kept 20 tests, and on kept + unused tests, per set
        b = by_set.setdefault(r.get("set", "all"), {"completions": 0, "reward_pass": 0, "strict_pass": 0})
        b["completions"] += 1
        b["reward_pass"] += int(r["reward"] == 1.0)
    for r, v in zip(rows, verdict):
        by_set[r.get("set", "all")]["strict_pass"] += int(v == "pass")
    not_audited = sum(1 for r in all_rows if r["reward"] == 1.0 and r["id"] not in hidden)
    return {"by_set": by_set, "reward1_without_hidden_tests": not_audited,
            "reward1_completions_audited": len(rows), "tasks_audited": len(by_task),
            "hidden_tests_per_task_median": sorted(len(t["tests"]) for t in hidden.values())[len(hidden) // 2],
            "verdict_on_hidden_tests": counts,
            "false_positive_share": round(1 - counts.get("pass", 0) / max(len(rows), 1), 4),
            "false_positive_share_excluding_timeouts": round(
                (len(rows) - counts.get("pass", 0) - counts.get("timeout", 0)) / max(len(rows), 1), 4),
            "by_judge": by_judge,
            "tasks_where_every_pass_fails_hidden": sum(1 for t in by_task.values() if t["fail"] == t["n"]),
            "tasks_where_some_pass_fails_hidden": sum(1 for t in by_task.values() if 0 < t["fail"] < t["n"]),
            "tasks_where_no_pass_fails_hidden": sum(1 for t in by_task.values() if t["fail"] == 0),
            "seconds": round(time.time() - t0, 1)}


@local_entrypoint()
def audit(run_id: str = "e1a"):
    t0 = time.time()
    f = fetch_hidden.remote(run_id)
    t1 = time.time()
    print(json.dumps(f))
    r = run_audit.remote(run_id)
    t2 = time.time()
    usd = (t1 - t0) * (4 * CPU_RATE + 16 * MEM_RATE) + (t2 - t1) * (32 * CPU_RATE + 16 * MEM_RATE)
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps({"kind": "reward_audit", "run_id": run_id, "client_wall_s": round(t2 - t0, 1),
                             "usd": round(usd, 4), "at": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    (WORK / "e1" / f"reward_audit_{run_id}.json").write_text(json.dumps({"fetch": f, "audit": r}, indent=1))
    print(json.dumps(r, indent=1))


@local_entrypoint()
def audit_trained(run_id: str = "e1a"):
    """Unused-test audit of the base and trained completions written by modal_app.py::sample."""
    t0 = time.time()
    names = ["audit/completions_base.jsonl", "audit/completions_trained.jsonl"]
    f = fetch_hidden.remote(run_id, names, "hidden_tests_eval.jsonl")
    t1 = time.time()
    print(json.dumps(f))
    out = {"fetch": f}
    for name in names:
        out[name.split("_")[-1].split(".")[0]] = run_audit.remote(run_id, name, "hidden_tests_eval.jsonl")
    t2 = time.time()
    usd = (t1 - t0) * (4 * CPU_RATE + 16 * MEM_RATE) + (t2 - t1) * (32 * CPU_RATE + 16 * MEM_RATE)
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps({"kind": "reward_audit_trained", "run_id": run_id, "client_wall_s": round(t2 - t0, 1),
                             "usd": round(usd, 4), "at": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    (WORK / "e1" / f"reward_audit_trained_{run_id}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
