"""One scorer process for stdin/stdout tasks: reads requests on stdin, writes results on stdout, one JSON per line.

    python score_worker.py <uid_start> <uid_span>
    request  {"task": {...rl-data task record...}, "text": "<completion>"}
    reply    stdio_check.score(task, text), or {"worker_error": "..."} when scoring itself raised

Why a separate process: the trainer holds tens of GB (model, optimizer, sampler). Every program run is a fork, and a
fork copies the parent's page tables, so forking from the trainer costs far more than the program it starts. This
process is started before the models load and stays small, so its forks are cheap. It is as trusted as the trainer:
expected outputs live in its memory and never reach the sandboxed program, exactly as in stdio_check.score.
Each worker gets its own slice of the sandbox uid range (stdio_check.set_uid_range).
"""
import importlib.util
import json
import sys
from pathlib import Path


def main() -> int:
    spec = importlib.util.spec_from_file_location("g10_stdio_check_worker", Path(__file__).resolve().parent / "stdio_check.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    sc.set_uid_range(int(sys.argv[1]), int(sys.argv[2]))
    out = sys.stdout
    sys.stdout = sys.stderr  # nothing but replies may reach the reply pipe
    for line in sys.stdin:
        try:
            req = json.loads(line)
            res = sc.score(req["task"], req["text"])
        except Exception as e:  # noqa: BLE001  (reported to the trainer, which stops)
            res = {"worker_error": repr(e)[:500]}
        out.write(json.dumps(res) + "\n")
        out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
