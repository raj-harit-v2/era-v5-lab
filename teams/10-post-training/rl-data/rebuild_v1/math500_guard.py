"""Hard limit 2 guard: no MATH-500 (MATH test subset) item may be in the MATH training records.
Fingerprints v2 has no MATH-500 benchmark, so this is our own direct check (not Team 9's tool):
  - exact match of the normalised problem (lowercase, whitespace collapsed),
  - any shared 13-word run (same window size as Team 9's prose fingerprints, simpler normaliser),
  - every record's provenance says split == "train" and its file is a train-*.parquet.
Only counts and ids are written; no problem text.

    python math500_guard.py <math_tasks.jsonl> <MATH-500 test.jsonl> <out.json>
"""
import json
import re
import sys

tasks_p, m500_p, out_p = sys.argv[1:4]


def norm(s):
    return " ".join(re.sub(r"\s+", " ", s.lower()).split())


def grams(s, n=13):
    w = norm(s).split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


tasks = [json.loads(x) for x in open(tasks_p, encoding="utf-8")]
m500 = [json.loads(x) for x in open(m500_p, encoding="utf-8")]
m_exact = {norm(r["problem"]): r["unique_id"] for r in m500}
m_grams = {}
for r in m500:
    for g in grams(r["problem"]):
        m_grams.setdefault(g, set()).add(r["unique_id"])
exact, gram_hits, bad_split = [], [], []
for t in tasks:
    if norm(t["problem"]) in m_exact:
        exact.append((t["id"], m_exact[norm(t["problem"])]))
    hits = set().union(*(m_grams.get(g, set()) for g in grams(t["problem"]))) if t["problem"] else set()
    if hits:
        gram_hits.append({"task": t["id"], "math500_items": sorted(hits)})
    p = t["provenance"]
    if p["split"] != "train" or not p["file"].rsplit("/", 1)[-1].startswith("train-"):
        bad_split.append(t["id"])
out = {"tasks": len(tasks), "math500_items": len(m500), "exact_matches": exact,
       "tasks_sharing_a_13_word_run": len(gram_hits), "gram_hits": gram_hits, "non_train_provenance": bad_split}
json.dump(out, open(out_p, "w"), indent=1)
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in out.items()}))
sys.exit(0 if not exact and not bad_split else 1)
