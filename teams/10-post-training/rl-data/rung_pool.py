"""Rung 1 of the RL code pool: the prompts a weak model is most likely to solve, chosen from admitted fields only.

    python rung_pool.py --tasks cc.jsonl --pool code_pool_ids.txt --tokenizer p1536/tokenizer.json \
        --out-dir <private dir> --rest-sample 128 --seed 1234

Rule (from the saved screens re-analysed in capstone/screen_ladder.py, 16 Nov): for models of 1 to 1.5B, every
group that carried gradient sat in the shortest third of statements and almost none came from Aizu; the
`difficulty` field does not stratify (87% of the pool is 0). So

    rung 1 = pool  AND  judge in {codechef, hackerearth}  AND  statement tokens <= the pool's lower-tercile cut

Statement length is counted with the frozen capstone tokenizer (p1536 on 16 Nov), no special tokens. Nothing is
written or rewritten: the fields are the record's own `judge` and `statement`. The rest of the pool (pool minus rung
1) is also written, with an unfiltered seeded sample of it for evaluation.

Outputs in --out-dir (ids are private; keep them out of Git): rung1_ids.txt, rest_ids.txt, rest_sample_ids.txt,
and rung_pool_manifest.json (counts, cut, input and output sha256; no ids, no text), which is safe to publish.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

DEFAULT_JUDGES = ("codechef", "hackerearth")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def tercile_cut(lengths: list[int]) -> int:
    """The lower-tercile cut used by screen_ladder.py: sorted(lengths)[n // 3]."""
    s = sorted(lengths)
    return s[len(s) // 3]


def build(tasks: list[dict], pool: list[str], lengths: dict[str, int], judges=DEFAULT_JUDGES,
          cut: int | None = None, rest_sample: int = 0, seed: int = 1234) -> dict:
    """Pure selection. `lengths` maps task id -> statement tokens. Returns ids and counts (no text)."""
    by_id = {t["id"]: t for t in tasks}
    missing = [i for i in pool if i not in by_id]
    if missing:
        raise ValueError(f"{len(missing)} pool ids are not in the task file, e.g. {missing[:3]}")
    if len(set(pool)) != len(pool):
        raise ValueError("pool has duplicate ids")
    if cut is None:
        cut = tercile_cut([lengths[i] for i in pool])
    judges = tuple(judges)
    rung = sorted(i for i in pool if by_id[i].get("judge") in judges and lengths[i] <= cut)
    rung_set = set(rung)
    rest = sorted(i for i in pool if i not in rung_set)
    rng = random.Random(seed)
    sample = sorted(rng.sample(rest, min(rest_sample, len(rest)))) if rest_sample else []
    count = lambda ids: dict(sorted(collections.Counter(by_id[i].get("judge", "unknown") for i in ids).items()))  # noqa: E731
    return {"rung1": rung, "rest": rest, "rest_sample": sample, "cut": cut, "judges": list(judges),
            "counts": {"pool": len(pool), "rung1": len(rung), "rest": len(rest), "rest_sample": len(sample),
                       "rung1_by_judge": count(rung), "rest_by_judge": count(rest),
                       "rest_sample_by_judge": count(sample)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tasks", type=Path, required=True, help="RL data v1 code task records (jsonl)")
    ap.add_argument("--pool", type=Path, required=True, help="code_pool_ids.txt from rl_v1_close.py")
    ap.add_argument("--tokenizer", type=Path, required=True, help="frozen capstone tokenizer.json")
    ap.add_argument("--judges", default=",".join(DEFAULT_JUDGES))
    ap.add_argument("--cut", type=int, help="statement-token cut; default the pool's lower-tercile cut")
    ap.add_argument("--rest-sample", type=int, default=128)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args(argv)
    from tokenizers import Tokenizer  # noqa: PLC0415

    tasks_bytes = a.tasks.read_bytes()
    tasks = [json.loads(x) for x in tasks_bytes.decode("utf-8").splitlines() if x.strip()]
    pool_bytes = a.pool.read_bytes()
    pool = pool_bytes.decode().split()
    tok_bytes = a.tokenizer.read_bytes()
    tok = Tokenizer.from_str(tok_bytes.decode("utf-8"))
    in_pool = set(pool)
    sel = [t for t in tasks if t["id"] in in_pool]
    enc = tok.encode_batch([t["statement"] for t in sel], add_special_tokens=False)
    lengths = {t["id"]: len(e.ids) for t, e in zip(sel, enc)}
    res = build(tasks, pool, lengths, a.judges.split(","), a.cut, a.rest_sample, a.seed)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    out_sha = {}
    for name, key in (("rung1_ids.txt", "rung1"), ("rest_ids.txt", "rest"), ("rest_sample_ids.txt", "rest_sample")):
        blob = "".join(i + "\n" for i in res[key]).encode()
        (a.out_dir / name).write_bytes(blob)
        out_sha[name] = sha256_bytes(blob)
    rung_lens = sorted(lengths[i] for i in res["rung1"])
    manifest = {"schema": "g10-rung-pool/1", "rule": f"pool AND judge in {res['judges']} AND statement tokens <= {res['cut']}",
                "cut": res["cut"], "cut_rule": "given" if a.cut is not None else "pool lower tercile (sorted[n//3])",
                "judges": res["judges"], "counts": res["counts"],
                "rung1_statement_tokens": {"min": rung_lens[0], "median": rung_lens[len(rung_lens) // 2],
                                           "max": rung_lens[-1]} if rung_lens else None,
                "rest_sample_seed": a.seed,
                "inputs_sha256": {"tasks": sha256_bytes(tasks_bytes), "pool": sha256_bytes(pool_bytes),
                                  "tokenizer": sha256_bytes(tok_bytes)},
                "outputs_sha256": out_sha,
                "fields_used": ["id", "judge", "statement (length only)"],
                "note": "ids are private (out-dir); this manifest holds counts and hashes only"}
    (a.out_dir / "rung_pool_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({k: manifest[k] for k in ("rule", "counts", "outputs_sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
