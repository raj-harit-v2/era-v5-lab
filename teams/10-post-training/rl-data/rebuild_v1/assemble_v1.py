"""RL data v1 candidate = built records - v2-flagged/canary (decontam_run records) - MATH train tasks sharing any
13-word run with MATH-500 (math500_guard.json). Records keep all builder fields and provenance; each gets
decontam = {fingerprints, set_sha256, math500_guard}. Writes out/v1/{cc,math}.jsonl and out/v1/summary.json."""
import hashlib, json
from pathlib import Path
O = Path("out"); V = O / "v1"; V.mkdir(exist_ok=True)
def load(p): return [json.loads(x) for x in open(p, encoding="utf-8")]
summary = {}
m500 = {h["task"] for h in json.load(open(O / "math500_guard.json"))["gram_hits"]}
for name, tasks_f, rec_f in (("cc", "cc_tasks.jsonl", "decontam/rl-code-code-contests-noncf.record.json"),
                             ("math", "math_tasks.jsonl", "decontam/rl-math-hendrycks-math-train.record.json")):
    rec = json.load(open(rec_f)); assert rec["ok"] and rec["scope"] == "full set"
    flagged = set(rec["flagged"]) | {h.get("doc_id", h.get("id")) for h in rec["canary"]["hits"]}
    tasks = load(O / tasks_f); out = []
    extra = m500 if name == "math" else set()
    for t in tasks:
        if t["id"] in flagged or t["id"] in extra: continue
        t["decontam"] = {"fingerprints": rec["fingerprints"], "set_sha256": rec["set_sha256"], "decontam_set": rec["set"],
                         **({"math500_13gram_guard": "clear"} if name == "math" else {})}
        out.append(t)
    p = V / f"{name}.jsonl"
    p.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in out), encoding="utf-8")
    summary[name] = {"built": len(tasks), "v2_flagged": len(flagged), "math500_overlap": len(extra),
                     "math500_overlap_also_v2_flagged": len(extra & flagged), "removed": len(tasks) - len(out),
                     "v1": len(out), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    if name == "cc":
        from collections import Counter; summary[name]["v1_by_judge"] = dict(Counter(t["judge"] for t in out))
    else:
        from collections import Counter; summary[name]["v1_by_level"] = dict(sorted(Counter(t["level"] for t in out).items()))
(V / "summary.json").write_text(json.dumps(summary, indent=1)); print(json.dumps(summary, indent=1))
