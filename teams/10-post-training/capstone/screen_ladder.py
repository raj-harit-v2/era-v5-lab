"""Where does RL data v1 carry gradient? Pass rates and mixed-group shares of saved screens by difficulty field, judge
and statement length, and an estimate of the share of the code pool with at least one success at k samples.

    python capstone/screen_ladder.py --tasks cc.jsonl --pool code_pool_ids.txt --tokenizer tokenizer.json \
        --screen 1.5B=fitA2/screen.json --screen 7B=p7b/screen.json --survey survey_results.json --out ladder.json

Inputs are screens the trainer already wrote (`per_task`: [{id, passes}], k samples each) and the 12 Nov attainability
survey (`rows[model]`: [{id, kind, n, k_passed}]). No sampling, no task text written: the output holds counts only.

A group carries gradient under objective_v1 only if its rewards are not all equal ("mixed"). The pool estimate
re-weights each screen's per-stratum mixed share and pass@k to the pool's own composition (judge x length tercile;
strata absent from a screen fall back to that judge, then to the screen's overall share). Strata come only from
fields in the admitted records (judge, difficulty) and the statement length under the frozen tokenizer.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def load_screen(path: Path) -> tuple[int, dict[str, int]]:
    s = json.loads(path.read_text())
    return int(s["k"]), {t["id"]: int(t["passes"]) for t in s["per_task"]}


def load_survey(path: Path) -> dict[str, tuple[int, dict[str, int]]]:
    s = json.loads(path.read_text())
    out = {}
    for model, rows in s["rows"].items():
        stdio = {r["id"]: int(r["k_passed"]) for r in rows if r.get("kind") == "stdio"}
        ks = {int(r["n"]) for r in rows if r.get("kind") == "stdio"}
        if stdio and len(ks) == 1:
            out[f"survey:{s['models'][model]['repo'].split('/')[-1]}"] = (ks.pop(), stdio)
    return out


def summarise(passes: dict[str, int], k: int, meta: dict[str, dict], key) -> dict:
    groups = collections.defaultdict(list)
    for tid, p in passes.items():
        if tid in meta:
            groups[key(meta[tid])].append(p)
    out = {}
    for g, ps in sorted(groups.items(), key=lambda kv: str(kv[0])):
        n = len(ps)
        out[str(g)] = {"prompts": n, "pass_rate": round(sum(ps) / (n * k), 4),
                       "mixed_share": round(sum(0 < p < k for p in ps) / n, 4),
                       "pass_at_k": round(sum(p > 0 for p in ps) / n, 4), "all_pass_share": round(sum(p == k for p in ps) / n, 4)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--pool", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--screen", action="append", default=[], help="label=path to a trainer screen.json")
    ap.add_argument("--survey", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    from tokenizers import Tokenizer  # noqa: PLC0415
    tok = Tokenizer.from_file(str(a.tokenizer))
    tasks = [json.loads(x) for x in a.tasks.read_text(encoding="utf-8").splitlines() if x.strip()]
    lens = [len(e.ids) for e in tok.encode_batch([t["statement"] for t in tasks], add_special_tokens=False)]
    pool = set(a.pool.read_text().split())
    pool_lens = sorted(n for t, n in zip(tasks, lens) if t["id"] in pool)
    cut = (pool_lens[len(pool_lens) // 3], pool_lens[2 * len(pool_lens) // 3])
    meta = {}
    for t, n in zip(tasks, lens):
        meta[t["id"]] = {"judge": t.get("judge", "unknown"), "difficulty": t.get("difficulty"),
                         "len": "short" if n <= cut[0] else ("mid" if n <= cut[1] else "long"), "tokens": n}
    screens = {}
    for spec in a.screen:
        label, path = spec.split("=", 1)
        screens[label] = load_screen(Path(path))
    if a.survey:
        screens.update(load_survey(a.survey))
    pool_strata = collections.Counter((meta[i]["judge"], meta[i]["len"]) for i in pool if i in meta)
    report = {"statement_tokens_tercile_cuts": cut, "pool_prompts": len(pool),
              "pool_by_judge": dict(collections.Counter(meta[i]["judge"] for i in pool if i in meta)),
              "pool_by_difficulty": dict(sorted(collections.Counter(str(meta[i]["difficulty"]) for i in pool
                                                                    if i in meta).items())),
              "screens": {}}
    for label, (k, passes) in screens.items():
        s = {"k": k, "prompts": len(passes), "in_pool": sum(i in pool for i in passes),
             "overall": summarise(passes, k, meta, lambda m: "all")["all"],
             "by_judge": summarise(passes, k, meta, lambda m: m["judge"]),
             "by_difficulty": summarise(passes, k, meta, lambda m: m["difficulty"]),
             "by_length": summarise(passes, k, meta, lambda m: m["len"])}
        js = summarise(passes, k, meta, lambda m: (m["judge"], m["len"]))
        mixed = passk = 0.0
        for (judge, ln), n in pool_strata.items():
            cell = js.get(str((judge, ln))) or s["by_judge"].get(judge) or s["overall"]
            mixed += n * cell["mixed_share"]
            passk += n * cell["pass_at_k"]
        total = sum(pool_strata.values())
        s["pool_estimate"] = {"mixed_share": round(mixed / total, 4), "pass_at_k_share": round(passk / total, 4),
                              "mixed_prompts": round(mixed), "method": "per (judge, length tercile) re-weighting to "
                              "the pool; fallback judge, then overall"}
        report["screens"][label] = s
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1))
    print(json.dumps({lab: {**v["overall"], **{"pool_mixed": v["pool_estimate"]["mixed_share"]}}
                      for lab, v in report["screens"].items()}, indent=0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
