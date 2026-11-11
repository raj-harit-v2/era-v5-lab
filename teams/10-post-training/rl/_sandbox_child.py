"""Runs inside the sandbox. Imports the candidate's solution.py and calls the entry point on the given inputs.

It gets inputs only. It never sees an expected value, so nothing it writes can be "made to match": the verifier
(the parent process) compares the outputs with the expected values, which are never in this process or this folder.

Usage (by verifier.py):  python _sandbox_child.py <workdir> <entry_point> <case_timeout_s>
Reads  <workdir>/solution.py and <workdir>/cases.json  (a list of {"args": [...], "kwargs": {...}}).
Writes <workdir>/results.json  (a list of {"ok": true, "value": ...} or {"ok": false, "error": "<type name>", "mro": [class names]}).
"""
import importlib.util
import json
import os
import signal
import sys

MAX_RESULT_BYTES = 4_000_000


class _CaseTimeout(BaseException):
    pass


def _on_alarm(signum, frame):
    raise _CaseTimeout()


def main(workdir: str, entry_point: str, case_timeout_s: float) -> int:
    with open(os.path.join(workdir, "cases.json"), encoding="utf-8") as f:
        cases = json.load(f)
    results = []
    try:
        spec = importlib.util.spec_from_file_location("solution", os.path.join(workdir, "solution.py"))
        module = importlib.util.module_from_spec(spec)
        signal.signal(signal.SIGALRM, _on_alarm)
        signal.setitimer(signal.ITIMER_REAL, max(case_timeout_s, 0.5))  # importing also has a budget
        spec.loader.exec_module(module)
        signal.setitimer(signal.ITIMER_REAL, 0)
        fn = getattr(module, entry_point)
        load_error = None
    except BaseException as exc:  # SystemExit, syntax errors, timeouts: all end the run with no results
        load_error = type(exc).__name__
        fn = None
    for case in cases:
        if fn is None:
            results.append({"ok": False, "error": "LoadError:" + str(load_error)})
            continue
        try:
            signal.setitimer(signal.ITIMER_REAL, case_timeout_s)
            value = fn(*case.get("args", []), **case.get("kwargs", {}))
            signal.setitimer(signal.ITIMER_REAL, 0)
            # Serialise now: it must be plain JSON data (tuples become lists), and a later call cannot change it.
            value = json.loads(json.dumps(value, allow_nan=False))
            results.append({"ok": True, "value": value})
        except _CaseTimeout:
            results.append({"ok": False, "error": "Timeout"})
        except BaseException as exc:  # includes SystemExit raised inside the function
            signal.setitimer(signal.ITIMER_REAL, 0)
            results.append({"ok": False, "error": type(exc).__name__, "mro": [c.__name__ for c in type(exc).__mro__]})
    payload = json.dumps(results, ensure_ascii=False)
    if len(payload.encode("utf-8")) > MAX_RESULT_BYTES:
        payload = json.dumps([{"ok": False, "error": "ResultTooLarge"}] * len(cases))
    with open(os.path.join(workdir, "results.json"), "w", encoding="utf-8") as f:
        f.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], float(sys.argv[3])))
