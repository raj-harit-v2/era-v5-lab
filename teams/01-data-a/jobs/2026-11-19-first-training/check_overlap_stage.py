r"""Check that the first-training job runs the MinHash + LSH overlap stage, and that the tests still pass.

Run from the repository root with Python 3.11 or later (the pipeline needs hashlib.file_digest) and the packages of
requirements_pipeline.txt plus pytest:

    python teams/01-data-a/jobs/2026-11-19-first-training/check_overlap_stage.py --log out/check_overlap_stage.log

It checks, without data or a GPU:
  1. prepare_run.py's run config names minhash_overlap.py for the overlap stage, with minhash_overlap_partial.json
     for a 33-pack selection and minhash_overlap.json otherwise;
  2. for each of the two, the runner's stage builder (pipeline/stage_args.py) turns the entry into a command for
     minhash_overlap.py and a generated config with the run's folders, 16 workers and 128 hashes in 32 bands (the
     partial config with no required pack list, the full one with all 38 packs);
  3. minhash_overlap.py accepts each generated config;
  4. the pipeline, job-preparation and MinHash tests pass (pytest). test_f2_pool.py is left out when G9's lab_canary
     module is not importable from this checkout.
Exit code 0 when every check passes. The log holds the checks, the pytest summary and the Python version.
"""
import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TEAM = REPO / "teams" / "01-data-a"
SCRIPT = "teams/01-data-a/dedup/minhash_overlap.py"
SETTINGS = {"33-pack selection": "teams/01-data-a/dedup/minhash_overlap_partial.json",
            "all 38 packs": "teams/01-data-a/dedup/minhash_overlap.json"}
TESTS = ["teams/01-data-a/pipeline/tests", "teams/01-data-a/jobs/2026-11-19-first-training/tests",
         "teams/01-data-a/dedup/tests/test_minhash_overlap.py", "teams/01-data-a/dedup/tests/test_minhash_sizing.py"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", type=Path, help="also write the output to this file")
    ap.add_argument("--no-tests", action="store_true", help="only the configuration checks")
    a = ap.parse_args()
    lines, failed = [], []

    def say(msg=""):
        print(msg, flush=True)
        lines.append(msg)

    def check(name, ok, detail=""):
        say(f"{'PASS' if ok else 'FAIL'}  {name}" + (f": {detail}" if detail else ""))
        if not ok:
            failed.append(name)

    say(f"python {platform.python_version()} on {platform.platform()}")
    if sys.version_info < (3, 11):
        check("Python 3.11 or later", False, "the pipeline needs hashlib.file_digest")
        return finish(a, lines, failed)

    # 1. prepare_run.py writes the MinHash stage
    src = (HERE / "prepare_run.py").read_text(encoding="utf-8")
    m = re.search(r'"overlap":\s*\{(.*?)\}', src, re.S)
    entry = m.group(1) if m else ""
    check("prepare_run.py: overlap stage script", f'"script": "{SCRIPT}"' in entry, SCRIPT)
    for scope, settings in SETTINGS.items():
        check(f"prepare_run.py: overlap settings for {scope}", f'"{settings}"' in entry, settings)

    # 2. the runner's stage builder accepts it
    sys.path.insert(0, str(TEAM / "pipeline"))
    sys.path.insert(0, str(TEAM / "dedup"))
    import stage_args
    import minhash_overlap
    (REPO / "out").mkdir(exist_ok=True)
    for scope, settings in SETTINGS.items():
        spec = {"mode": "run", "script": SCRIPT, "settings": settings}
        base = Path(tempfile.mkdtemp(prefix="check_overlap_stage_", dir=REPO / "out"))   # the stage scripts need out/
        try:
            folders = {s: base / s for s in ("clean", "overlap", "h3", "dedup")}
            for f in folders.values():
                f.mkdir(parents=True, exist_ok=True)
            built = stage_args.build("overlap", spec, folders=folders, cfg_dir=base / "cfg", repo=REPO, write=True)
            cmd = [str(c) for c in built["command"]]
            check(f"{scope}: stage_args.build runs minhash_overlap.py", Path(cmd[0]).as_posix().endswith(SCRIPT), cmd[0])
            cfg = json.loads(Path(built["config"]).read_text(encoding="utf-8"))
            check(f"{scope}: generated inputs and out are the run's folders",
                  (cfg["inputs"], cfg["out"]) == (stage_args.relative(folders["clean"], REPO),
                                                  stage_args.relative(folders["overlap"], REPO)))
            check(f"{scope}: workers 16", cfg.get("workers") == 16, str(cfg.get("workers")))
            check(f"{scope}: 128 hashes in 32 bands", (cfg.get("hashes"), cfg.get("bands")) == (128, 32),
                  f"{cfg.get('hashes')} x {cfg.get('bands')}")
            want = 0 if "33" in scope else 38
            check(f"{scope}: required packs", len(cfg.get("expected_packs", [])) == want, str(len(cfg.get("expected_packs", []))))
            try:
                minhash_overlap.load_config(built["config"])
                check(f"{scope}: minhash_overlap.py accepts the generated config", True)
            except SystemExit as e:
                check(f"{scope}: minhash_overlap.py accepts the generated config", False, str(e))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    # 4. tests
    if not a.no_tests:
        args = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:warnings", *TESTS]
        try:
            import lab_canary  # noqa: F401  (G9's module; test_f2_pool.py needs it)
        except ImportError:
            args.append("--ignore=teams/01-data-a/pipeline/tests/test_f2_pool.py")
            say("note  test_f2_pool.py left out: lab_canary (G9) is not importable from here")
        say("$ " + " ".join(Path(x).name if i == 0 else x for i, x in enumerate(args)))
        r = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
        summary = (r.stdout.strip().splitlines() or [""])[-1]
        check("pytest", r.returncode == 0, summary)
        if r.returncode:
            say(r.stdout[-3000:])
    return finish(a, lines, failed)


def finish(a, lines, failed):
    lines.append(f"{'ALL CHECKS PASSED' if not failed else 'FAILED: ' + ', '.join(failed)}")
    print(lines[-1])
    if a.log:
        a.log.parent.mkdir(parents=True, exist_ok=True)
        a.log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
