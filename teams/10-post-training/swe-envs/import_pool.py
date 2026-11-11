"""Select SWE-bench-format rows from an open pool (default nebius/SWE-rebench) that pass the G10 rules.

This scales the environment supply for the week 3-4 RL loop. It writes a candidate manifest only; a row
becomes an environment only after `make_env.py` rebuilds it from the upstream PR and `verify.py --check`
passes it, exactly like the hand-picked ones.

Why SWE-rebench content passes the 3 Nov rule (arXiv 2505.20411, sections 2.1 to 2.4): the problem statement
is the GitHub issue, and patch and test_patch come from the merged PR, all from permissively licensed repos.
Qwen2.5-72B-Instruct only wrote install recipes and quality labels (metadata). We rebuild every environment
ourselves and do not use those recipes or labels.

TSAI answer (4 Nov): allowed, using only the human parts (issue, patch, tests), with every env rebuilt and
gold-checked by us, and the CC-BY-4.0 attribution kept in licences/licence_table.md. Pre-2023 rows are fine.

Filters (keep_row):
  - issue created before 2023-01-01 (fewer agent-written PRs, see research notes)
  - repo not in benchmark_repos.txt (SWE-bench, Multimodal, Live, Pro)
  - licence named and permissive (MIT, BSD, Apache-2.0, ISC, ...)
  - FAIL_TO_PASS and PASS_TO_PASS non-empty
  - no AI-tool marker in the problem statement

Usage:
    python import_pool.py --out pool_manifest.json [--dataset nebius/SWE-rebench] [--split test]
                          [--max-patch-chars 3000] [--per-repo 3]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CUTOFF = "2023-01-01"
AI_MARKERS = re.compile(
    r"\b(claude|anthropic|copilot|codex|chatgpt|gpt-[345]|openai|gemini|devin|llm)\b|cursor[ .](ai|agent|com|sh)\b|"
    r"generated with|ai[- ]assisted", re.I)

# SPDX ids we accept for the upstream repo licence (permissive, commercial use allowed).
PERMISSIVE_SPDX = {"MIT", "MIT-CMU", "BSD-2-Clause", "BSD-3-Clause", "BSD", "Apache-2.0", "ISC", "0BSD", "Zlib",
                   "Unlicense", "CC0-1.0", "PSF-2.0", "BSL-1.0", "MIT OR Apache-2.0"}
# Licence names as SWE-rebench writes them -> SPDX.
NAME_TO_SPDX = {
    "mit license": "MIT", "mit": "MIT", "mit-cmu license": "MIT-CMU", "apache license 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0", "apache-2.0": "Apache-2.0",
    'bsd 3-clause "new" or "revised" license': "BSD-3-Clause", "bsd 3-clause license": "BSD-3-Clause",
    "bsd-3-clause": "BSD-3-Clause", "bsd 3-clause": "BSD-3-Clause", "new bsd license": "BSD-3-Clause",
    "modified bsd license": "BSD-3-Clause", 'bsd 2-clause "simplified" license': "BSD-2-Clause",
    "bsd-2-clause": "BSD-2-Clause", "bsd license": "BSD", "bsd": "BSD", "isc license": "ISC",
    "mit/apache-2.0 dual license": "MIT OR Apache-2.0", "the unlicense": "Unlicense",
    "creative commons zero v1.0 universal": "CC0-1.0",
    "creative commons zero v1.0 universal license (cc0 1.0)": "CC0-1.0",
}


def benchmark_repos(path: Path = HERE / "benchmark_repos.txt") -> set[str]:
    return {line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


def spdx(name: str | None) -> str | None:
    return NAME_TO_SPDX.get((name or "").strip().lower())


def keep_row(row: dict, bench: set[str]) -> tuple[bool, str]:
    if str(row.get("created_at", ""))[:10] >= CUTOFF:
        return False, "created 2023 or later"
    if row["repo"].lower() in bench:
        return False, "repo is in a SWE benchmark"
    lic = spdx(row.get("license_name"))
    if lic not in PERMISSIVE_SPDX:
        return False, f"licence not accepted: {row.get('license_name')!r}"
    if not row.get("FAIL_TO_PASS") or not row.get("PASS_TO_PASS"):
        return False, "empty FAIL_TO_PASS or PASS_TO_PASS"
    if AI_MARKERS.search(row.get("problem_statement") or ""):
        return False, "AI-tool marker in the issue"
    return True, ""


def read_rows(dataset: str, split: str, columns: list[str]) -> list[dict]:
    import pyarrow.parquet as pq  # only needed for the CLI

    info = json.load(urllib.request.urlopen(f"https://datasets-server.huggingface.co/parquet?dataset={dataset}"))
    rows = []
    for f in info["parquet_files"]:
        if f["split"] != split:
            continue
        table = pq.read_table(io.BytesIO(urllib.request.urlopen(f["url"]).read()), columns=columns)
        rows += table.to_pylist()
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default="nebius/SWE-rebench")
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-patch-chars", type=int, default=3000, help="keep small, focused fixes")
    ap.add_argument("--per-repo", type=int, default=3, help="at most this many rows per repo")
    args = ap.parse_args(argv)

    cols = ["instance_id", "repo", "base_commit", "created_at", "license_name", "FAIL_TO_PASS", "PASS_TO_PASS",
            "patch", "problem_statement"]
    rows = read_rows(args.dataset, args.split, cols)
    bench = benchmark_repos()
    reasons: Counter = Counter()
    per_repo: Counter = Counter()
    kept = []
    for row in sorted(rows, key=lambda r: (len(r["patch"] or ""), r["instance_id"])):
        ok, why = keep_row(row, bench)
        if ok and len(row["patch"] or "") > args.max_patch_chars:
            ok, why = False, "patch too large"
        if ok and per_repo[row["repo"]] >= args.per_repo:
            ok, why = False, "per-repo cap"
        if not ok:
            reasons[why.split(":")[0]] += 1
            continue
        per_repo[row["repo"]] += 1
        m = re.search(r"-(\d+)$", row["instance_id"])
        kept.append({"instance_id": row["instance_id"], "repo": row["repo"], "pr": int(m.group(1)) if m else None,
                     "base_commit": row["base_commit"], "created_at": str(row["created_at"])[:10],
                     "licence": spdx(row["license_name"]), "n_fail_to_pass": len(row["FAIL_TO_PASS"]),
                     "n_pass_to_pass": len(row["PASS_TO_PASS"]), "patch_chars": len(row["patch"]),
                     "source": f"https://huggingface.co/datasets/{args.dataset}"})
    manifest = {"dataset": args.dataset, "split": args.split, "rows_read": len(rows), "kept": len(kept),
                "dropped": dict(reasons.most_common()), "cutoff": CUTOFF, "rows": kept}
    args.out.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("rows_read", "kept", "dropped")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
