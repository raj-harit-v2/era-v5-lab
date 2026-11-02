"""Make every generated file in spec_v1/: results/sheets/evidence.json, sheets/medicine_code.md, sheets/decisions_code.md, results/sheets/*_harm.json, results/sheets/inputs_manifest.json.

  python -I run_all.py <checkout> <packs dir> [--stress-gold <dir>]

<checkout> is g1-harm-test with the inputs in place: see README.md here. Reports hold IDs and digests, never document text.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent
RESULTS = SPEC / "results" / "sheets"
PACKS = ["code-go", "code-rust", "code-js-ts", "code-java", "code-cpp", "code-python"]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("checkout", type=Path)
ap.add_argument("packs", type=Path)
ap.add_argument("--stress-gold", type=Path, help="gold made by build_gold.py --allow-disputed")
args = ap.parse_args()
TEAM = args.checkout / "teams" / "01-data-a"
RESULTS.mkdir(exist_ok=True)


def run(*cmd, ok=(0,)):
    rc = subprocess.run([sys.executable, "-I", *map(str, cmd)]).returncode
    if rc not in ok: sys.exit(f"exit code {rc}: {cmd[0]}")


def harm(pack, gold, report, ok):
    run(TEAM / "tools" / "harm_test.py", "--pack", args.packs / f"{pack}.parquet", "--gold", gold, "--rules", SPEC / "sheets" / "medicine_code.md",
        "--rule", "all", "--report", report, ok=ok)
    d = json.loads(report.read_text(encoding="utf-8"))
    d["rules"] = "teams/01-data-a/spec_v1/sheets/medicine_code.md"  # the tool writes the path it was given, which differs per machine
    report.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")


run(HERE / "compile_evidence.py", args.checkout, args.packs)
run(HERE / "compile_medicine_code.py", args.checkout, args.packs)
for pack in PACKS:
    harm(pack, TEAM / "gold" / f"{pack}_gold.csv", RESULTS / f"{pack}_harm.json", (0,))
    if args.stress_gold:  # not the official test, so a FAIL here is a result and not an error
        harm(pack, args.stress_gold / f"{pack}_gold.csv", RESULTS / f"stress_{pack}_harm.json", (0, 1))
inputs = [*TEAM.glob("rules/code-*/*.py"), *TEAM.glob("medicines/submissions/code-*/*/medicine.md"), *TEAM.glob("gold/code-*_gold.csv"),
          *args.checkout.glob("diagnosis/submissions/code-*/*/labels.csv"), *(args.stress_gold.glob("code-*_gold.csv") if args.stress_gold else [])]
root = args.checkout.resolve()
manifest = {"tools_commit": subprocess.run(["git", "-C", str(args.checkout), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
            "packs": {p: hashlib.sha256((args.packs / f"{p}.parquet").read_bytes()).hexdigest() for p in PACKS},
            "inputs": {(f.resolve().relative_to(root).as_posix() if f.resolve().is_relative_to(root) else "stress_gold/" + f.name): hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}}
manifest["inputs"] = dict(sorted(manifest["inputs"].items()))
(RESULTS / "inputs_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
print("done:", SPEC)
