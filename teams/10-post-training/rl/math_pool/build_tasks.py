"""Write math task folders (task.json with pins only) from records of the RL data v1 math pool.

    python rl/math_pool/build_tasks.py --pool math.jsonl --ids math-algebra-1717,math-geometry-249
    python rl/math_pool/build_tasks.py --pool math.jsonl --pick 8 --seed 17

--pick takes one random record per subject (seeded; answer of at most 24 characters, no \\text, level 2 to 4), then
fills up with random algebra records. Nothing about a problem's text is read to choose it. A task folder holds
the pool id, the subject, the level, and SHA-256 pins of the problem and the answer. The text stays in the pool.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import math_verifier as mv  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True, type=Path)
    ap.add_argument("--ids")
    ap.add_argument("--pick", type=int)
    ap.add_argument("--seed", type=int, default=17)
    a = ap.parse_args()
    rows = {r["id"]: r for r in (json.loads(line) for line in a.pool.read_text(encoding="utf-8").splitlines())}
    if a.ids:
        ids = a.ids.split(",")
    else:
        rng = random.Random(a.seed)
        by = defaultdict(list)
        for r in rows.values():
            if len(r["answer"]) <= 24 and r["level"] in ("Level 2", "Level 3", "Level 4") and "\\text" not in r["answer"]:
                by[r["subject"]].append(r["id"])
        ids = [rng.choice(by[s]) for s in sorted(by)]
        while len(ids) < (a.pick or 0):
            extra = rng.choice(by["algebra"])
            if extra not in ids:
                ids.append(extra)
    for pid in ids:
        r = rows[pid]
        assert r.get("licence") == "MIT" and "none" in r.get("generator", ""), pid
        tid = pid.removeprefix("math-")
        out = mv.TASKS / tid
        out.mkdir(parents=True, exist_ok=True)
        meta = {"id": tid, "pool_id": pid, "subject": r["subject"], "level": r["level"],
                "problem_sha256": mv.sha256(r["problem"]), "answer_sha256": mv.sha256(r["answer"]),
                "source": r["source"], "licence": "MIT", "generator": "none (human competition problem and solution)",
                "pool": "RL data v1 math (rl-data/build_math.py), problem text and answer stay in the pool"}
        (out / "task.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"task": tid, "pool_id": pid}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
