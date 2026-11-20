"""F2 on many parts at once: G9's fingerprint set loaded once, then N workers, one part at a time.

  python -I teams/01-data-a/pipeline/f2_pool.py --inputs <deduped>/<split> --out <final>/<split> --workers N

The same job as run_f2.py (#40), faster. run_f2.py checks its files one after another, and a process per pack loads the
full set (about 1.1 GB, about 20 s) once per pack. This loads it once, then:
  - fork (Linux): N workers share the loaded set copy-on-write (a lookup only reads its pages), so memory stays about
    1.1 GB plus the documents in flight, whatever N is. The wall time is bounded by the largest part, not the largest pack.
  - spawn (Windows, macOS): fork is not available or not safe, so each worker loads the set itself, once
    (N × 1.1 GB, as with one run_f2.py per pack), but parts are still shared out one at a time.
  - --workers 1: in this process, no pool.
Parts go out largest first, so the big ones don't finish last. --workers defaults to the CPUs this process may use on
Linux, and to 1 elsewhere (each spawned worker needs its own 1.1 GB).

It never reimplements F2. It imports run_f2.py (--script, default teams/01-data-a/spec_v1/run_f2.py) and calls its
fingerprints() (the pinned set, checked against SET_SHA256) and run_file() on each part, unchanged. So every output part,
every <part>.f2.json and <out>/f2_summary.json are what run_f2.py writes for the same --inputs and --out: the same bytes,
apart from the "seconds" fields (the tests check this for in-process and spawn runs, and for fork where the machine has
it). Each .f2.json and the summary name run_f2.py's sha256, as run_f2.py does. Pool details (workers, start method,
wall time, docs/s) go to stdout only, so the output folder does not depend on how it was run.

INPUT, OUTPUT AND CHECKS are run_f2.py's: --inputs takes folders (every *.parquet under them) or files, as given;
--out gets the same relative paths; --out may not overlap an input; two inputs may not map to one output path. The set's
pin (SHA256SUMS against run_f2.py's SET_SHA256) is checked in this process before any worker starts or anything is
written. A part whose .f2.json already names its input sha256 and the set is skipped, so a stopped run resumes. A doc
whose check raises is kept out and reported, and the run exits 1. A part a worker cannot finish (a missing column,
counts that do not add up, a worker that dies, out of memory for example) does not stop the other parts: they finish,
then the run exits 1 naming every failed part, and writes no f2_summary.json (a run without one has not finished).
Rerun: finished parts are skipped.
"""
import sys
sys.dont_write_bytecode = True

import argparse, gc, hashlib, importlib.util, json, multiprocessing as mp, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_F2 = REPO / "teams" / "01-data-a" / "spec_v1" / "run_f2.py"

_MOD = _FP = _CODE = _INIT_ERROR = None  # this process's run_f2.py, set and run_f2.py sha256 (parent or worker)


class Stop(Exception):
    """The run cannot go on, or did not finish: the message says why."""


def load_run_f2(script=DEFAULT_F2):
    """run_f2.py as a module, from its path (it is not on sys.path, and is not registered in sys.modules)."""
    script = Path(script).resolve()
    spec = importlib.util.spec_from_file_location("run_f2", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_pin(mod):
    """run_f2.py's cheap pin check, without loading the set: the folder exists and its SHA256SUMS hashes to SET_SHA256."""
    path = Path(os.environ.get("F2_FINGERPRINTS") or mod.G9.parent / "fingerprints" / mod.SET)
    sums = path / "SHA256SUMS"
    if not sums.is_file():
        raise Stop(f"F2: no fingerprint set at {path}: SET or F2_FINGERPRINTS names a missing folder")
    got = hashlib.sha256(sums.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    if got != mod.SET_SHA256:
        raise Stop(f"F2: the fingerprint set at {path} has set_sha256 {got}, not the pinned {mod.SET_SHA256}")


def _setup(script, benchmarks, in_worker=True):
    """Load run_f2.py and the set into this process's globals. A worker keeps a failure to report it per part (raising
    here would make the pool replace the worker forever)."""
    global _MOD, _FP, _CODE, _INIT_ERROR
    try:
        _MOD = load_run_f2(script)
        _CODE = _MOD.sha256(Path(_MOD.__file__))
        _FP = _MOD.fingerprints(tuple(benchmarks)) if benchmarks else _MOD.fingerprints()
    except BaseException as e:
        if not in_worker:
            raise
        _INIT_ERROR = f"the worker could not load the set: {type(e).__name__}: {e}"


def _one(task):
    """F2 on one part: (rel, "ok", report) or (rel, "failed", why). Never raises, not even on Ctrl-C."""
    src, dst, rel = task
    if _INIT_ERROR:
        return rel, "failed", _INIT_ERROR
    try:
        return rel, "ok", _MOD.run_file(Path(src), Path(dst), _FP, _CODE)
    except SystemExit as e:  # run_f2.run_file stops a part with sys.exit(message)
        return rel, "failed", str(e.code)
    except BaseException as e:
        return rel, "failed", f"{type(e).__name__}: {e}"


def plan(inputs, out):
    """[(src, dst, rel)] as run_f2.py builds them: inputs as given (not resolved), --out resolved; run_f2.py's checks."""
    out = Path(out).resolve()
    files = []
    for p in map(Path, inputs):
        r = p.resolve()
        if r.is_dir() and (out == r or r in out.parents) or out in r.parents:
            raise Stop(f"--out {out} and --inputs {p} overlap: the output would be read as input")
        if p.is_file():
            files.append((p, Path(p.name)))
        elif p.is_dir():
            files += [(f, f.relative_to(p)) for f in sorted(p.rglob("*.parquet"))]
        else:
            raise Stop(f"--inputs: {p} is not a file or folder")
    if not files:
        raise Stop("--inputs: no .parquet files")
    rels = [rel for _, rel in files]
    if len(set(rels)) != len(rels):
        raise Stop("--inputs: two inputs map to the same output path; give them in separate runs")
    return [(str(src), str(out / rel), rel.as_posix()) for src, rel in files]


def start_method(requested=None):
    """fork on Linux (copy-on-write sharing of the set), spawn elsewhere, or what was asked for."""
    if requested:
        if requested not in mp.get_all_start_methods():
            raise Stop(f"--start {requested} is not available here (have {', '.join(mp.get_all_start_methods())})")
        return requested
    return "fork" if sys.platform.startswith("linux") else "spawn"


def default_workers():
    """Linux: the CPUs this process may use (fork shares the set). Elsewhere 1: each spawned worker loads 1.1 GB."""
    if not sys.platform.startswith("linux"):
        return 1
    count = getattr(os, "process_cpu_count", None)
    return (count() if count else len(os.sched_getaffinity(0))) or 1


def run(inputs, out, workers=1, script=DEFAULT_F2, start=None, benchmarks=None, log=print):
    """F2 on every part under inputs into out. Returns (summary as run_f2.py writes it, pool details).
    benchmarks: a few benchmark IDs, tests only (not the formal check)."""
    global _MOD, _FP, _CODE, _INIT_ERROR
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise Stop(f"--workers is {workers!r}, expected a whole number >= 1")
    tasks = plan(inputs, out)
    method = "in-process" if workers == 1 else start_method(start)
    _MOD = _FP = _CODE = _INIT_ERROR = None  # nothing from an earlier run in this process
    t0 = time.time()
    if method == "spawn":
        mod = load_run_f2(script)
        check_pin(mod)  # before any worker starts: a broken set must not reach the workers
        _CODE = mod.sha256(Path(mod.__file__))
        loaded = None  # each worker loads the set
    else:
        try:
            _setup(script, benchmarks, in_worker=False)  # load and check the set before anything is written
        except (OSError, ValueError) as e:
            raise Stop(f"F2: {e}")
        loaded = round(time.time() - t0, 1)
    by_size = sorted(tasks, key=lambda t: (-os.path.getsize(t[0]), t[2]))  # largest first
    results = {}

    def note(rel, status, r):
        results[rel] = (status, r)
        what = (f"{r['rows']} rows, kept {r['kept']}, dropped {r['dropped_by_f2']}, errors {len(r['errors'])}"
                if status == "ok" else f"FAILED: {r}")
        log(f"f2_pool [{len(results)}/{len(tasks)}] {rel}: {what}")

    if method == "in-process":
        for task in by_size:
            note(*_one(task))
    else:
        n = min(workers, len(tasks))
        kw = {} if method == "fork" else {"initializer": _setup, "initargs": (str(script), tuple(benchmarks) if benchmarks else None)}
        sys.stdout.flush()
        sys.stderr.flush()  # forked workers must not inherit unflushed output and write it again
        if method == "fork":
            gc.freeze()  # keep the loaded set out of the collector, so workers don't touch its pages for nothing
        try:
            with ProcessPoolExecutor(max_workers=n, mp_context=mp.get_context(method), **kw) as pool:
                futures = {pool.submit(_one, t): t[2] for t in by_size}
                try:
                    for fut in as_completed(futures):
                        note(*fut.result())
                except BrokenProcessPool as e:  # a worker died (killed, out of memory, crashed): no part hangs
                    for fut, rel in futures.items():
                        if rel in results:
                            continue
                        if fut.done() and not fut.cancelled() and fut.exception() is None:
                            note(*fut.result())  # finished before the pool broke
                        else:
                            note(rel, "failed", f"a worker died before this part finished ({type(e).__name__})")
        finally:
            if method == "fork":
                gc.unfreeze()
    failed = sorted((rel, r) for rel, (status, r) in results.items() if status != "ok")
    if failed:
        raise Stop(f"{len(failed)} of {len(tasks)} part(s) did not finish, e.g. {failed[0][0]}: {failed[0][1]}. "
                   "Finished parts are kept and skipped on a rerun")

    reports = [results[rel][1] for _, _, rel in tasks]  # input order, as run_f2.py
    sets = {r["set_sha256"] for r in reports}
    if len(sets) != 1:
        raise Stop(f"the parts were checked against {len(sets)} different sets: {sorted(map(str, sets))}")
    total = {k: sum(r[k] for r in reports) for k in ("rows", "kept", "dropped_by_f2")}
    total["errors"] = sum(len(r["errors"]) for r in reports)
    wall = round(time.time() - t0, 1)
    summary = {"set_sha256": sets.pop(), "run_f2_py_sha256": _CODE, "files": len(reports), **total, "seconds": wall,
               "per_file": [{k: r[k] for k in ("input", "input_sha256", "output_sha256", "rows", "kept", "dropped_by_f2")}
                            for r in reports]}
    outp = Path(out).resolve()
    outp.mkdir(parents=True, exist_ok=True)
    (outp / "f2_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    pool = {"workers": 1 if method == "in-process" else min(workers, len(tasks)), "start_method": method,
            "parts": len(tasks), "set_load_seconds": loaded, "wall_seconds": wall,
            "docs_per_second": round(total["rows"] / wall, 1) if wall else None,
            "f2_pool_py_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return summary, pool


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", type=Path, nargs="+", required=True, help="deduped Parquet folders or files")
    ap.add_argument("--out", type=Path, required=True, help="the final folder")
    ap.add_argument("--workers", type=int, default=default_workers(),
                    help="parts checked at once (default: the usable CPUs on Linux, 1 elsewhere)")
    ap.add_argument("--script", type=Path, default=DEFAULT_F2, help="run_f2.py to call (default: spec_v1/run_f2.py)")
    ap.add_argument("--start", choices=("fork", "spawn"), help="start method (default: fork on Linux, else spawn)")
    args = ap.parse_args()
    try:
        summary, pool = run(args.inputs, args.out, args.workers, args.script, args.start,
                            log=lambda m: print(m, file=sys.stderr, flush=True))
    except Stop as e:
        sys.exit(f"f2_pool: {e}")
    print(json.dumps({**{k: v for k, v in summary.items() if k not in ("per_file", "seconds")}, "pool": pool}))
    sys.exit(1 if summary["errors"] else 0)


if __name__ == "__main__":
    main()
