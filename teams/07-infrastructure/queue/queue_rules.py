#!/usr/bin/env python3
"""Queue rules v1 (docs/queue_rules_v1.md): check a G7 job request and a job's ./out/ folder.

In simple words: before a job request goes to TSAI, this says whether it names its max time, its device count,
its log path, its checkpoint path and its one run ID. After the CPU test, it says whether ./out/ has the layout
the rules ask for. It only reads files. It needs nothing but the Python standard library.

    python queue/queue_rules.py run-id restore-test --date 2026-11-04          # g7-restore-test-20261104-01
    python queue/queue_rules.py paths g7-restore-test-20261104-01 --arm a      # every path the job writes
    python queue/queue_rules.py check-request jobs/2026-11-04-restore-test.md
    python queue/queue_rules.py check-out ./out --run-id g7-restore-test-20261104-01

Exit 0: every rule passes. Exit 1: the problems are printed, one per line, in plain words.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

# R1 and R2. Proposed, awaiting TSAI: change them here and in docs/queue_rules_v1.md together.
MAX_TIME_CAP_MIN = 60
MAX_DEVICES = 2
HARDWARE_DEVICES = {"cpu": 0, "1 gpu": 1, "2 gpu": 2, "2 gpus": 2}
MAX_OUT_BYTES = 50 * 1024 * 1024                       # JOB_REQUEST.md: 50 MB or less in total

RESULT_SCHEMA = "g7-job-result/1"
STATUSES = ("pass", "fail", "stopped_at_limit")
NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
RUN_ID_RE = re.compile(rf"^g7-(?P<name>{NAME})-(?P<date>\d{{8}})-(?P<seq>\d{{2}})$")
ARM_RE = re.compile(r"^[a-z0-9]+$")
REQUEST_FILE_RE = re.compile(rf"^(?P<date>\d{{4}}-\d{{2}}-\d{{2}})-(?P<name>{NAME})\.md$")
STEP_DIR_RE = re.compile(r"^step_(\d+)-e(\d+)$")
SHELL_JOIN = ("|", ";", "&&", "||", ">", "<", "`", "$(")

TSAI_KEYS = ("Team", "Owner", "Lead approval", "Question", "Script", "Command", "Config", "Inputs", "Hardware",
             "Max time", "Precision", "Measures", "Expected result", "Outputs", "Test log")
G7_KEYS = ("Run ID", "Devices", "Log path", "Checkpoint path")
RESULT_KEYS = ("schema", "run_id", "status", "exit_code", "device_kind", "device_count", "max_time_min",
               "elapsed_s", "started_utc", "ended_utc", "numbers")


# ---------------------------------------------------------------- R5: the run ID
def make_run_id(name: str, date: dt.date, seq: int = 1) -> str:
    rid = f"g7-{name}-{date:%Y%m%d}-{seq:02d}"
    problems = run_id_problems(rid)
    if problems:
        raise ValueError("; ".join(problems))
    return rid


def run_id_problems(rid: str) -> list:
    m = RUN_ID_RE.match(rid or "")
    if not m:
        return [f"run ID {rid!r} is not g7-<short-name>-<YYYYMMDD>-<NN> (lowercase, digits, single dashes)"]
    try:
        dt.datetime.strptime(m["date"], "%Y%m%d")
    except ValueError:
        return [f"run ID {rid!r}: {m['date']} is not a date"]
    if m["seq"] == "00":
        return [f"run ID {rid!r}: the number starts at 01"]
    return []


# ---------------------------------------------------------------- R3, R4, R8: the paths
def job_paths(run_id: str, out: str = "./out", arm: str = "main") -> dict:
    """Every path a job writes. Scripts import this, so the layout lives in one place."""
    if run_id_problems(run_id):
        raise ValueError(run_id_problems(run_id)[0])
    if not ARM_RE.match(arm):
        raise ValueError(f"arm {arm!r}: lowercase letters and digits only")
    root = os.path.join(out, run_id)
    return {
        "run_dir": root,
        "result": os.path.join(root, "result.json"),
        "logs": os.path.join(root, "logs"),
        "job_log": os.path.join(root, "logs", "job.log"),
        "events": os.path.join(root, "logs", "events.jsonl"),
        "ckpt_root": os.path.join(root, "ckpt"),           # Checkpointer(remote_root=ckpt_root, run_id=arm)
        "ckpt_arm": os.path.join(root, "ckpt", arm),
    }


# ---------------------------------------------------------------- the request
def parse_request(text: str) -> dict:
    """The `Key: value` lines of the first fenced block that has a `Team:` line."""
    for block in re.findall(r"```[^\n]*\n(.*?)```", text, flags=re.S):
        fields = {}
        for line in block.splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip() and not key.startswith((" ", "\t")):
                fields.setdefault(key.strip(), value.strip())
        if "Team" in fields:
            return fields
    return {}


def _strip_note(value: str) -> str:
    """'30   (TSAI stops the job at this limit)' -> '30'."""
    return re.split(r"\s{2,}\(", value, maxsplit=1)[0].strip()


def check_request(path: str) -> list:
    problems = []
    fname = os.path.basename(path)
    fm = REQUEST_FILE_RE.match(fname)
    if not fm:
        problems.append(f"{fname}: the file name must be <YYYY-MM-DD>-<short-name>.md (JOB_REQUEST.md)")
    with open(path, encoding="utf-8") as f:
        fields = parse_request(f.read())
    if not fields:
        return problems + ["no request block: copy the block from JOB_REQUEST.md into a ``` fence"]
    for key in TSAI_KEYS + G7_KEYS:
        if not fields.get(key) or "<" in fields[key].split("(")[0]:
            problems.append(f"`{key}:` is missing or still has a <placeholder>")

    rid = _strip_note(fields.get("Run ID", ""))
    rid_problems = run_id_problems(rid)
    problems += rid_problems
    if not rid_problems and fm:
        m = RUN_ID_RE.match(rid)
        if m["name"] != fm["name"]:
            problems.append(f"run ID name `{m['name']}` must be the request's short name `{fm['name']}` (R5)")
        if m["date"] != fm["date"].replace("-", ""):
            problems.append(f"run ID date {m['date']} must be the request date {fm['date']} (R5)")

    if fields.get("Team") and _strip_note(fields["Team"]) != "07-infrastructure":
        problems.append("`Team:` must be 07-infrastructure")

    max_time = _strip_note(fields.get("Max time", ""))
    if not re.fullmatch(r"\d+", max_time):
        problems.append(f"`Max time:` {max_time!r} must be a whole number of minutes (R1)")
    elif not 1 <= int(max_time) <= MAX_TIME_CAP_MIN:
        problems.append(f"`Max time:` {max_time} min is over the G7 cap of {MAX_TIME_CAP_MIN} min (R1)")

    devices = _strip_note(fields.get("Devices", ""))
    hardware = _strip_note(fields.get("Hardware", "")).lower()
    if not re.fullmatch(r"\d+", devices) or int(devices) > MAX_DEVICES:
        problems.append(f"`Devices:` {devices!r} must be 0 (CPU), 1 or {MAX_DEVICES} (R2)")
    elif hardware not in HARDWARE_DEVICES:
        problems.append(f"`Hardware:` {hardware!r} must be CPU, 1 GPU or 2 GPUs (R2)")
    elif HARDWARE_DEVICES[hardware] != int(devices):
        problems.append(f"`Devices:` {devices} does not match `Hardware:` {hardware} (R2)")

    if not rid_problems:
        want = {"Log path": f"./out/{rid}/logs/", "Checkpoint path": f"./out/{rid}/ckpt/"}
        for key, path_ in want.items():
            got = _strip_note(fields.get(key, ""))
            if got.rstrip("/") + "/" != path_:
                problems.append(f"`{key}:` {got!r} must be {path_} (R3, R4)")

    command = _strip_note(fields.get("Command", ""))
    joined = [s for s in SHELL_JOIN if s in command]
    if joined:
        problems.append(f"`Command:` must be one command with no {' '.join(joined)} (R6)")
    if rid and not rid_problems and f"--run-id {rid}" not in command:
        problems.append(f"`Command:` must pass --run-id {rid} (R5, R6)")
    script = _strip_note(fields.get("Script", ""))
    if script and not script.startswith("teams/07-infrastructure/"):
        problems.append(f"`Script:` {script!r} must be under teams/07-infrastructure/")
    return problems


# ---------------------------------------------------------------- the ./out/ folder after a run
def _folder_bytes(root: str) -> int:
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, files in os.walk(root) for f in files)


def committed_paths(arm_dir: str) -> tuple:
    """(problems, step folders that latest.json or commits.jsonl names, relative to the arm). ckpt/ckpt.py
    writes both only after MANIFEST.json, so these are the commits."""
    problems, paths = [], []
    latest = os.path.join(arm_dir, "latest.json")
    if os.path.isfile(latest):
        try:
            with open(latest, encoding="utf-8") as f:
                ptr = json.load(f)
            if ptr.get("path"):                            # a claim before the first save has path null
                paths.append(ptr["path"])
        except (OSError, ValueError, AttributeError) as e:
            problems.append(f"{latest}: not a JSON object ({e}) (R4)")
    commits = os.path.join(arm_dir, "commits.jsonl")
    if os.path.isfile(commits):
        with open(commits, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    paths.append(json.loads(line)["path"])
                except (ValueError, KeyError, TypeError):
                    problems.append(f"{commits} line {n}: not a commit record with a path (R4)")
    return problems, list(dict.fromkeys(paths))


def check_checkpoints(ckpt_root: str) -> tuple:
    """(problems, COMPLETE step folders). COMPLETE = MANIFEST.json in the folder and the folder named by
    latest.json or commits.jsonl (R4). A pointer to a folder without MANIFEST.json is an error; MANIFEST.json
    that no pointer names is a save cut before its commit, which is not a checkpoint and not an error."""
    problems, complete = [], []
    if not os.path.isdir(ckpt_root):
        return problems, complete
    for arm in sorted(os.listdir(ckpt_root)):
        arm_dir = os.path.join(ckpt_root, arm)
        if not os.path.isdir(arm_dir):
            continue
        if not ARM_RE.match(arm):
            problems.append(f"ckpt/{arm}: an arm name is lowercase letters and digits (R4)")
        ptr_problems, paths = committed_paths(arm_dir)
        problems += ptr_problems
        for rel in paths:
            if not STEP_DIR_RE.match(os.path.basename(rel.rstrip("/"))):
                problems.append(f"ckpt/{arm}: pointer path {rel!r} is not <branch>/step_<N>-e<E> (R4)")
            elif not os.path.isfile(os.path.join(arm_dir, rel, "MANIFEST.json")):
                problems.append(f"ckpt/{arm}/{rel}: named as committed but has no MANIFEST.json (R4)")
            else:
                complete.append(os.path.join(arm, rel))
    return problems, complete


def check_out(out: str, run_id: str) -> list:
    problems = run_id_problems(run_id)
    if problems:
        return problems
    p = job_paths(run_id, out)
    if not os.path.isdir(p["run_dir"]):
        return [f"{p['run_dir']}: no run folder (R3)"]
    for other in sorted(os.listdir(out)):
        if other != run_id and not other.startswith("."):
            problems.append(f"{os.path.join(out, other)}: only ./out/{run_id}/ belongs to this job (R5)")
    if not os.path.isfile(p["job_log"]):
        problems.append(f"{p['job_log']}: missing (R3)")
    size = _folder_bytes(out)
    if size > MAX_OUT_BYTES:
        problems.append(f"./out is {size / 2**20:.1f} MB, over 50 MB (R4, JOB_REQUEST.md)")
    ck_problems, _ = check_checkpoints(p["ckpt_root"])
    problems += ck_problems
    problems += check_result(p["result"], run_id)
    return problems


def check_result(path: str, run_id: str) -> list:
    if not os.path.isfile(path):
        return [f"{path}: missing; a job writes result.json last (R8)"]
    try:
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
    except (OSError, ValueError) as e:
        return [f"{path}: not JSON ({e}) (R8)"]
    if not isinstance(r, dict):
        return [f"{path}: must be one JSON object (R8)"]
    problems = [f"result.json: `{k}` is missing (R8)" for k in RESULT_KEYS if k not in r]
    if problems:
        return problems
    if r["schema"] != RESULT_SCHEMA:
        problems.append(f"result.json: schema {r['schema']!r} is not {RESULT_SCHEMA}")
    if r["run_id"] != run_id:
        problems.append(f"result.json: run_id {r['run_id']!r} is not the folder's {run_id!r} (R5)")
    if r["status"] not in STATUSES:
        problems.append(f"result.json: status {r['status']!r} is not one of {', '.join(STATUSES)}")
    if not isinstance(r["exit_code"], int):
        problems.append("result.json: exit_code must be an integer")
    elif r["status"] == "pass" and r["exit_code"] != 0:
        problems.append("result.json: status pass needs exit_code 0")
    elif r["status"] == "stopped_at_limit" and r["exit_code"] != 75:
        problems.append("result.json: status stopped_at_limit needs exit_code 75 (R1)")
    kind, count = r["device_kind"], r["device_count"]
    if kind not in ("cpu", "gpu") or not isinstance(count, int):
        problems.append("result.json: device_kind is cpu or gpu, device_count an integer (R2)")
    elif (kind == "cpu") != (count == 0) or count > MAX_DEVICES:
        problems.append(f"result.json: {kind} with {count} devices (CPU is 0; GPU is 1 to {MAX_DEVICES}) (R2)")
    mt, el = r["max_time_min"], r["elapsed_s"]
    if not isinstance(mt, int) or not 1 <= mt <= MAX_TIME_CAP_MIN:
        problems.append(f"result.json: max_time_min {mt!r} must be 1 to {MAX_TIME_CAP_MIN} (R1)")
    elif not isinstance(el, (int, float)) or el < 0 or el > mt * 60:
        problems.append(f"result.json: elapsed_s {el!r} is over max_time_min x 60 (R1)")
    for k in ("started_utc", "ended_utc"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", str(r[k])):
            problems.append(f"result.json: {k} {r[k]!r} must be UTC like 2026-11-04T10:15:02Z")
    if not isinstance(r["numbers"], dict):
        problems.append("result.json: numbers must be an object")
    return problems


# ---------------------------------------------------------------- command line
def _report(problems: list, ok: str) -> int:
    for p in problems:
        print(f"FAIL {p}")
    print(ok if not problems else f"{len(problems)} problem(s).")
    return 1 if problems else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("run-id", help="make a run ID (R5)")
    a.add_argument("name")
    a.add_argument("--date", default=dt.date.today().isoformat(), help="request date, YYYY-MM-DD")
    a.add_argument("--seq", type=int, default=1)
    a = sub.add_parser("paths", help="every path a job writes (R3, R4, R8)")
    a.add_argument("run_id")
    a.add_argument("--out", default="./out")
    a.add_argument("--arm", default="main")
    a = sub.add_parser("check-request", help="check a job request file")
    a.add_argument("file")
    a = sub.add_parser("check-out", help="check ./out after a run")
    a.add_argument("out")
    a.add_argument("--run-id", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "run-id":
        try:
            print(make_run_id(args.name, dt.date.fromisoformat(args.date), args.seq))
        except ValueError as e:
            print(f"FAIL {e}")
            return 1
        return 0
    if args.cmd == "paths":
        try:
            print(json.dumps(job_paths(args.run_id, args.out, args.arm), indent=2))
        except ValueError as e:
            print(f"FAIL {e}")
            return 1
        return 0
    if args.cmd == "check-request":
        return _report(check_request(args.file), "PASS: the request follows queue rules v1.")
    return _report(check_out(args.out, args.run_id), "PASS: ./out follows queue rules v1.")


if __name__ == "__main__":
    sys.exit(main())
