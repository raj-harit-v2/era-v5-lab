#!/usr/bin/env python3
"""Task 3's full run: every token ID of the frozen p1536 table and of the committed table, with its run record.

Steps:
1. Rebuild the p1536 raw P = 32 table from the tokenizer with ``build_tables.py`` in a temporary folder. The table
   is never written to the repo (lab rule, 15 Nov); ``tests/test_every_id.py`` pins its content sha256.
2. Run ``tests/test_every_id.py`` on all 131,072 IDs (``KE2_EVERY_ID_FULL=1``) with that tokenizer and table.
3. Run Team 5's ``teams/05-architecture/tests/test_week2_ke2_g4_codec.py`` (#471) on the same table
   (``ERA_KE2_TABLE``): the trainer's KE2 against Team 4's float64 codec, from Team 5's side.
4. Write ``results/every_id/every_id_P32.{json,log,md}``: inputs, environment, source hashes, every check's
   numbers, and both suites' output with local paths replaced by ``<repo>``, ``<tokenizer>``, ``<tmp>`` and ``~``.

Exit status 0 only if both suites pass and nothing is skipped.

    python teams/04-ke2/src/run_every_id.py --tokenizer PATH/p1536/tokenizer.json [--device cuda]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from ke2.config import RESULTS_DIR, TEAM_DIR

P = 32
OUT_DIR = RESULTS_DIR / "every_id"
REPO = TEAM_DIR.parents[1]
TEAMS_DIR = TEAM_DIR.parent
TEAM5_TEST = TEAMS_DIR / "05-architecture" / "tests" / "test_week2_ke2_g4_codec.py"
SOURCES = [  # every file whose code the run executes, hashed after CRLF -> LF (the bytes git stores)
    TEAM_DIR / "tests" / "test_every_id.py",
    TEAM_DIR / "src" / "run_every_id.py",
    TEAM_DIR / "src" / "build_tables.py",
    TEAM_DIR / "src" / "ke2" / "codec.py",
    TEAM_DIR / "src" / "ke2" / "tables.py",
    TEAM_DIR / "src" / "ke2" / "tokenizer.py",
    TEAM_DIR / "src" / "ke2" / "scoring.py",
    TEAM_DIR / "src" / "decode_ref.py",
    TEAM_DIR / "src" / "proofs" / "decode_theorems.py",
    TEAM_DIR / "src" / "determinism" / "decode_gpu.py",
    TEAMS_DIR / "05-architecture" / "harness" / "week2" / "model.py",
    TEAM5_TEST,
    TEAMS_DIR / "06-performance" / "models" / "ke2.py",
    TEAMS_DIR / "06-performance" / "correctness" / "framework.py",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def run(cmd: list[str], cwd: Path, env: dict) -> tuple[int, str, float]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr, time.perf_counter() - t0


def scrubber(replacements: dict[str, str]):
    """Replace local paths (either slash style, any case) so the record names no user folder."""
    pats = []
    for path, label in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
        for form in {path, path.replace("\\", "/"), path.replace("/", "\\")}:
            pats.append((re.compile(re.escape(form), re.IGNORECASE), label))

    def scrub(text: str) -> str:
        for rx, label in pats:
            text = rx.sub(label, text)
        return USER_DIR.sub("~", text)  # anything left under a user folder, long or 8.3 short name

    return scrub


USER_DIR = re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s:]+", re.IGNORECASE)


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def environment(device: str | None) -> dict:
    import numpy
    import tokenizers
    import torch

    cuda = torch.cuda.is_available()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "numpy": numpy.__version__,
        "tokenizers": tokenizers.__version__,
        "cuda_runtime": torch.version.cuda,
        "device": device or ("cuda" if cuda else "cpu"),
        "gpu": torch.cuda.get_device_name(0) if cuda else None,
    }


def pytest_counts(text: str) -> dict:
    last = [line for line in text.splitlines() if re.search(r"\d+ (passed|failed|skipped|error)", line)]
    counts = {k: 0 for k in ("passed", "failed", "skipped", "error")}
    for n, k in re.findall(r"(\d+) (passed|failed|skipped|error)", last[-1] if last else ""):
        counts[k] = int(n)
    return counts


def unittest_counts(text: str) -> dict:
    ran = re.search(r"Ran (\d+) tests?", text)
    return {"ran": int(ran.group(1)) if ran else 0, "ok": bool(re.search(r"^OK\b", text, re.MULTILINE))}


def markdown(rec: dict) -> str:
    rows = []
    for c in rec["checks"]:
        what = c["check"]
        detail = []
        if what == "table":
            detail.append(f"sha256 `{c['sha256'][:12]}…`, tokenizer `{c['tokenizer_sha256'][:12]}…`")
        if what.startswith("round_trip"):
            detail.append(f"{c['dtype']}: {c['wrong']} wrong")
        if what == "round_trip_cosine":
            detail.append(
                f"{c['ties']} ties, smallest margin {c['min_margin']:.4f} (ID {c['min_margin_id']}), "
                f"ID hash `{c['id_sha256'][:12]}…`"
            )
        if what == "input_path":
            detail.append(
                f"{c['impl']} {c['dtype']}: worst output {c['worst_out']:.1e}, gradient {c['worst_grad']:.1e}, "
                f"row {c['worst_row']:.1e} (tolerance {c['tol']:g} / {c['grad_tol']:g})"
            )
        if what == "bf16_code_bits":
            detail.append(f"{c['rows_differ']} rows differ")
        rows.append(
            f"| {c['table']} | {what} | {c['ids']:,} | {'; '.join(detail)} |"
            if "ids" in c
            else f"| {c['table']} | {what} | {c['rows']:,} | {'; '.join(detail)} |"
        )
    s, u = rec["suites"]["test_every_id"], rec["suites"]["team5_g4_codec"]
    lines = [
        "# Task 3: every token ID, full run (generated by `src/run_every_id.py`; do not edit)",
        "",
        f"**{'PASS' if rec['passed'] else 'FAIL'}.** `tests/test_every_id.py`: {s['counts']['passed']} passed, "
        f"{s['counts']['failed']} failed, {s['counts']['skipped']} skipped in {s['seconds']:.0f} s. "
        f"Team 5's `test_week2_ke2_g4_codec.py` on the p1536 table: {u['counts']['ran']} tests, "
        f"{'OK' if u['counts']['ok'] else 'FAILED'}.",
        "",
        f"Frozen tokenizer p1536 `{rec['inputs']['tokenizer_sha256']}`; its raw P = 32 table "
        f"`{rec['inputs']['frozen_table_sha256']}` (rebuilt, not committed). Device {rec['environment']['device']} "
        f"({rec['environment']['gpu'] or 'no GPU'}), torch {rec['environment']['torch']}. "
        f"Source hashes and every number are in `every_id_P32.json`; the suites' output is in `every_id_P32.log`.",
        "",
        "| Table | Check | IDs | Result |",
        "|---|---|---:|---|",
        *rows,
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", type=Path, required=True, help="the frozen p1536 tokenizer.json")
    ap.add_argument("--device", choices=["cpu", "cuda"], default=None, help="default: cuda if available")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args(argv)
    tokenizer = a.tokenizer.resolve()
    if not tokenizer.is_file():
        print(f"no tokenizer at {tokenizer}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="ke2_every_id_") as tmp:
        tmp_dir = Path(tmp)
        scrub = scrubber(
            {
                str(REPO): "<repo>",
                str(tokenizer): "<tokenizer>",
                tmp: "<tmp>",
                str(tmp_dir.resolve()): "<tmp>",
                sys.prefix: "<venv>",
                str(Path.home()): "~",
            }
        )
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
        log = []

        build = [sys.executable, str(TEAM_DIR / "src" / "build_tables.py"), "--tokenizer", str(tokenizer)]
        build += ["--pos-dims", str(P), "--out", str(tmp_dir)]
        code, out, _ = run(build, REPO, env)
        log += ["$ python teams/04-ke2/src/build_tables.py --tokenizer <tokenizer> --pos-dims 32 --out <tmp>", out]
        table = tmp_dir / f"raw_table_P{P}.npz"
        if code != 0 or not table.is_file():
            print(scrub(out), file=sys.stderr)
            return 1
        manifest = json.loads((tmp_dir / "manifest.json").read_text(encoding="utf-8"))
        frozen_sha = manifest["tables"][table.name]["sha256"]

        report = tmp_dir / "report.jsonl"
        test_env = {
            **env,
            "KE2_EVERY_ID_FULL": "1",
            "KE2_FROZEN_TOKENIZER": str(tokenizer),
            "KE2_FROZEN_TABLE": str(table),
            "KE2_EVERY_ID_REPORT": str(report),
        }
        if a.device:
            test_env["KE2_EVERY_ID_DEVICE"] = a.device
        pytest_cmd = [sys.executable, "-m", "pytest", "tests/test_every_id.py", "-v", "-rs", "-p", "no:cacheprovider"]
        pytest_cmd += ["--durations=0", "-W", "ignore::UserWarning"]
        code_t, out_t, secs_t = run(pytest_cmd, TEAM_DIR, test_env)
        log += [
            "",
            "$ KE2_EVERY_ID_FULL=1 KE2_FROZEN_TOKENIZER=<tokenizer> KE2_FROZEN_TABLE=<tmp>/raw_table_P32.npz "
            "python -m pytest tests/test_every_id.py -v -rs  (cwd teams/04-ke2)",
            out_t,
        ]

        code_u, out_u, secs_u = 1, f"missing: {TEAM5_TEST}", 0.0
        if TEAM5_TEST.is_file():
            u_cmd = [sys.executable, "-m", "unittest", "-v", "tests.test_week2_ke2_g4_codec"]
            code_u, out_u, secs_u = run(u_cmd, TEAM5_TEST.parents[1], {**env, "ERA_KE2_TABLE": str(table)})
        log += [
            "",
            "$ ERA_KE2_TABLE=<tmp>/raw_table_P32.npz python -m unittest -v tests.test_week2_ke2_g4_codec  "
            "(cwd teams/05-architecture)",
            out_u,
        ]

        checks = (
            [json.loads(line) for line in report.read_text(encoding="utf-8").splitlines()] if report.is_file() else []
        )

    counts_t, counts_u = pytest_counts(out_t), unittest_counts(out_u)
    passed = (
        code_t == 0 and counts_t["failed"] == counts_t["skipped"] == counts_t["error"] == 0 and counts_t["passed"] > 0
    )
    passed = passed and code_u == 0 and counts_u["ok"]
    rec = {
        "format": "ke2-every-id-run-v1",
        "passed": passed,
        "inputs": {
            "frozen_name": "p1536",
            "tokenizer_sha256": sha256_file(tokenizer),
            "frozen_table_sha256": frozen_sha,
            "pos_dim": P,
            "committed_table": "results/tables/raw_table_P32.npz",
        },
        "environment": environment(a.device),
        "git_head": git_head(),
        "sources_sha256_lf": {str(p.relative_to(REPO)).replace("\\", "/"): sha256_lf(p) for p in SOURCES},
        "suites": {
            "test_every_id": {"exit_code": code_t, "counts": counts_t, "seconds": round(secs_t, 1)},
            "team5_g4_codec": {"exit_code": code_u, "counts": counts_u, "seconds": round(secs_u, 1)},
        },
        "checks": checks,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    stem = a.out / f"every_id_P{P}"
    stem.with_suffix(".json").write_text(
        json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    stem.with_suffix(".log").write_text(scrub("\n".join(log)).rstrip() + "\n", encoding="utf-8", newline="\n")
    stem.with_suffix(".md").write_text(markdown(rec), encoding="utf-8", newline="\n")
    print(f"{'PASS' if passed else 'FAIL'}: wrote {stem.name}.json, .log and .md to {a.out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
