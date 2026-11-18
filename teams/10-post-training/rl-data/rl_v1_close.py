"""RL data v1 close (G10, work-order task 2): apply the pool flags as reversible manifest fields. No file is edited.

    python rl-data/rl_v1_close.py --v1-dir <rebuild>/out/v1 --out rl-data/manifests/rl_data_v1_close.json \
        --private-dir <private folder outside Git>

Inputs are the locally rebuilt RL data v1 files (`cc.jsonl`, `math.jsonl`; their sha256 must equal the v1 manifests)
and `eval/effort_manifest.json`. Each flag below removes tasks from the RL *pool* only; the v1 files stay as built, so
a ruling reverses a flag by switching it off here and re-running this script.

  statement_less   code tasks whose statement has fewer than 40 characters before the first Example / Input heading
                   (`statement_check.py`, 15 Nov finding R6). Applied; reversed if a human look clears them.
  effort_suite     tasks named in the effort suite's `training_exclusion` (the suite is evaluation data). Applied,
                   verified by id; the count actually present in v1 is reported.
  python2_only     code tasks from judges whose human references are Python 2 only (codechef, hackerearth; 11 Nov build:
                   0 Python 3 references among those rows). Not applied (open policy item; both outcomes sized);
                   `--drop-python2` applies it. `--keep-statement-less` reverses statement_less.
  math_reserved    the whole MATH part: kept as a separate, reserved part because TSAI has not admitted Hendrycks MATH
                   for RL (no licence-table row on this branch), so the code part stands alone.

Evaluation firewall (lead, 16 Nov 2026), applied when the two private id lists are given; they split the close pool
into a training pool and the RL held-out part and do not change the close pool itself (Team 9's pool check covers it):
  rl_heldout_v1    `--rl-heldout-ids`: the official RL held-out set (evaluation only, never trained; its problems are
                   also out of SFT training, sft/results/ocr2_eval_firewall_v1.json).
  sft_heldout      `--sft-heldout-match-ids`: pool tasks whose problem is in the SFT held-out split (heldout_eval_v1),
                   matched by sft/cross_stage_overlap.py; they stay out of the RL training pool.

Public output: counts and hashes only. Private output (ids): `--private-dir`, never Git.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
sys.path.insert(0, str(HERE))
from statement_check import has_description  # noqa: E402

SCHEMA = "g10-rl-data-v1-close/1"
PY2_ONLY_JUDGES = ("codechef", "hackerearth")
MIN_CHARS = 40


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ids_sha(ids) -> str:
    return hashlib.sha256("".join(f"{i}\n" for i in sorted(ids)).encode()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def by_judge(tasks, ids) -> dict:
    c = collections.Counter(t["judge"] for t in tasks if t["id"] in ids)
    return dict(sorted(c.items()))


def close(cc: list[dict], math: list[dict], effort: dict, keep_statement_less: bool = False,
          drop_python2: bool = False, rl_heldout: set | None = None, sft_heldout_match: set | None = None) -> tuple[dict, dict]:
    cc_ids = {t["id"] for t in cc}
    math_ids = {t["id"] for t in math}
    assert len(cc_ids) == len(cc) and len(math_ids) == len(math), "duplicate task ids"
    excl = set(effort["training_exclusion"]["task_ids"])
    statement_less = {t["id"] for t in cc if not has_description(t["statement"], MIN_CHARS)}
    eff_cc, eff_math = excl & cc_ids, excl & math_ids
    py2 = {t["id"] for t in cc if t["judge"] in PY2_ONLY_JUDGES}
    removed = (set() if keep_statement_less else statement_less) | eff_cc
    pool_py2_kept = cc_ids - removed
    pool_py2_dropped = pool_py2_kept - py2
    if drop_python2:
        removed |= py2
    pool = cc_ids - removed
    flags = {
        "statement_less": {
            "applied": not keep_statement_less, "rule": f"statement_check.has_description(statement, min_chars={MIN_CHARS}) is False",
            "tasks": len(statement_less), "by_judge": by_judge(cc, statement_less), "ids_sha256": ids_sha(statement_less),
            "reverse": "--keep-statement-less (a ruling that the flagged prompts stay, after a human look at the private list)",
            "evidence": "results/verifier_data_note_20261115.md (R6); the five flagged tasks in E1's screen were all-fail"},
        "effort_suite": {
            "applied": True, "rule": "task id in eval/effort_manifest.json training_exclusion.task_ids",
            "listed": len(excl), "present_in_code": len(eff_cc), "present_in_math": len(eff_math),
            "listed_not_in_v1": len(excl - cc_ids - math_ids), "code_by_judge": by_judge(cc, eff_cc),
            "also_statement_less": len(eff_cc & statement_less), "ids_sha256": ids_sha(eff_cc | eff_math),
            "reverse": "only if the effort suite is retired or re-drawn"},
        "python2_only": {
            "applied": drop_python2, "rule": f"judge in {list(PY2_ONLY_JUDGES)}",
            "tasks": len(py2), "by_judge": by_judge(cc, py2), "ids_sha256": ids_sha(py2),
            "in_pool_after_other_flags": len(pool_py2_kept & py2),
            "outcome_keep": {"code_pool_tasks": len(pool_py2_kept)},
            "outcome_drop": {"code_pool_tasks": len(pool_py2_dropped), "by_judge": by_judge(cc, pool_py2_dropped)},
            "basis": "11 Nov build: the codechef and hackerearth rows have only language-1 (Python 2) human solutions, "
                     "0 Python 3; the correct-answer check converts them with lib2to3",
            "decision": "lead: keep in v1 close pool (3,577 tasks; Python 3 candidate completions checked against I/O pairs); TSAI can reverse with --drop-python2", "apply": "--drop-python2"},
    }
    parts = {
        "code": {"set": "rl-code-code-contests-noncf", "rows_v1": len(cc), "by_judge_v1": by_judge(cc, cc_ids),
                 "removed_by_applied_flags": len(removed), "pool_tasks": len(pool), "pool_by_judge": by_judge(cc, pool),
                 "pool_ids_sha256": ids_sha(pool), "status": "allowed for RL by TSAI (6 Nov, train split only)"},
        "math": {"set": "rl-math-hendrycks-math-train", "rows_v1": len(math), "effort_suite_removed": len(eff_math),
                 "reserved_tasks": len(math_ids - eff_math), "reserved_ids_sha256": ids_sha(math_ids - eff_math),
                 "status": "reserved: separate part, not in the RL pool until TSAI admits Hendrycks MATH for RL",
                 "reverse": "a TSAI admission (with a licence-table row) adds this part to the pool as is"},
    }
    if rl_heldout is not None or sft_heldout_match is not None:
        held, sft_m = set(rl_heldout or ()), set(sft_heldout_match or ())
        if not held <= cc_ids or not sft_m <= cc_ids:
            raise ValueError("an evaluation-firewall id is not a code task of RL data v1")
        train = pool - held - sft_m
        flags["rl_heldout_v1"] = {
            "applied": True, "rule": "task id in the official RL held-out list (evaluation only; also out of SFT training)",
            "listed": len(held), "in_close_pool": len(held & pool), "outside_close_pool": len(held - pool),
            "ids_sha256": ids_sha(held), "by_judge": by_judge(cc, held),
            "definition": "the 15 Nov run's 96 held-out problems plus the 160 planned for E10 (union, 255 tasks)",
            "reverse": "a different held-out definition (for example the 96 only) is a different list file"}
        flags["sft_heldout"] = {
            "applied": True, "rule": "pool task whose problem is in the SFT held-out split heldout_eval_v1 "
                                     "(sft/cross_stage_overlap.py, confirmed + possible tiers)",
            "listed": len(sft_m), "in_close_pool": len(sft_m & pool), "also_rl_heldout": len(sft_m & held),
            "ids_sha256": ids_sha(sft_m)}
        parts["code"].update(train_pool_tasks=len(train), train_pool_ids_sha256=ids_sha(train),
                             train_pool_by_judge=by_judge(cc, train),
                             train_pool_note="close pool minus the RL held-out set and the SFT held-out matches")
        parts["heldout"] = {"set": "rl-code-code-contests-noncf", "tasks": len(held), "ids_sha256": ids_sha(held),
                            "by_judge": by_judge(cc, held),
                            "status": "RL evaluation set v1: never in RL or SFT training"}
    private = {"statement_less_ids.txt": statement_less, "effort_suite_ids.txt": eff_cc | eff_math,
               "python2_only_ids.txt": py2, "code_pool_ids.txt": pool, "math_reserved_ids.txt": math_ids - eff_math}
    if "heldout" in parts:
        private.update({"code_train_pool_ids.txt": train, "rl_heldout_v1_ids.txt": held, "sft_heldout_match_ids.txt": sft_m})
    return {"flags": flags, "parts": parts}, private


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--v1-dir", type=Path, required=True)
    ap.add_argument("--effort-manifest", type=Path, default=TEAM / "eval" / "effort_manifest.json")
    ap.add_argument("--manifests", type=Path, default=HERE / "manifests")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--private-dir", type=Path)
    ap.add_argument("--keep-statement-less", action="store_true", help="reverse the statement_less flag")
    ap.add_argument("--drop-python2", action="store_true", help="apply the python2_only flag")
    ap.add_argument("--rl-heldout-ids", type=Path, help="private list: the official RL held-out task ids")
    ap.add_argument("--sft-heldout-match-ids", type=Path, help="private list: pool tasks matching the SFT held-out split")
    a = ap.parse_args(argv)
    cc_path, math_path = a.v1_dir / "cc.jsonl", a.v1_dir / "math.jsonl"
    want = {"cc": json.loads((a.manifests / "rl-code-code-contests-noncf.v1.json").read_text())["output"]["sha256"],
            "math": json.loads((a.manifests / "rl-math-hendrycks-math-train.v1.json").read_text())["output"]["sha256"]}
    got = {"cc": sha256_file(cc_path), "math": sha256_file(math_path)}
    if got != want:
        print(f"rl_v1_close: v1 files differ from the v1 manifests: {got} != {want}", file=sys.stderr)
        return 2
    effort = json.loads(a.effort_manifest.read_text())
    def ids_file(path):
        return {x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()} if path else None

    body, private = close(read_jsonl(cc_path), read_jsonl(math_path), effort, a.keep_statement_less, a.drop_python2,
                          ids_file(a.rl_heldout_ids), ids_file(a.sft_heldout_match_ids))
    out = {"schema": SCHEMA,
           "inputs": {"cc_sha256": got["cc"], "math_sha256": got["math"],
                      "effort_manifest": {"suite": effort["suite"], "sha256": sha256_file(a.effort_manifest)}},
           **body,
           "note": "pool flags only: the v1 files are unchanged; ids are private (sha256 of the sorted list here)"}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if a.private_dir:
        a.private_dir.mkdir(parents=True, exist_ok=True)
        for name, ids in private.items():
            (a.private_dir / name).write_text("".join(f"{i}\n" for i in sorted(ids)), encoding="utf-8")
    f, p = out["flags"], out["parts"]
    print(json.dumps({"code_v1": p["code"]["rows_v1"], "statement_less": f["statement_less"]["tasks"],
                      "effort_code": f["effort_suite"]["present_in_code"], "effort_math": f["effort_suite"]["present_in_math"],
                      "code_pool": p["code"]["pool_tasks"], "py2_in_pool": f["python2_only"]["in_pool_after_other_flags"],
                      "code_pool_if_py2_dropped": f["python2_only"]["outcome_drop"]["code_pool_tasks"],
                      "math_reserved": p["math"]["reserved_tasks"],
                      **({"code_train_pool": p["code"]["train_pool_tasks"], "rl_heldout": p["heldout"]["tasks"]}
                         if "heldout" in p else {})}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
