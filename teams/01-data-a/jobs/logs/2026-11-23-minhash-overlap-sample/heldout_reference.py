"""Exact reference for every pair with at least one held-out document (independent of MinHash).

Words: index every held-out document's word 5-gram shingles (overlap.py's), stream every document of the run, count
shared shingles with each held-out document, and keep pairs at exact Jaccard >= 0.80 (empty documents left out, as
in LSH). Code: the exact code-token shingle sets that step 1 wrote (work/*.code.npy, overlap_rules.code_shingles), for
code documents with >= 20 nonblank lines; pairs at token Jaccard >= 0.85. Then checks that the MinHash run lists every
reference pair: word pairs in overlap_pairs.csv (verified candidates >= the floor) or as H1, code pairs as H2 matches.
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0, "teams/01-data-a/dedup")
from minhash_overlap import read_file, find_parts
from h1_sha256 import h1_key
from jaccard_matrix import shingles

RUN, WORK, INPUTS = Path("out/mh_ho"), Path("out/mh_full/work"), Path("out/s2")
docs = pq.read_table(RUN / "overlap_docs.parquet").to_pandas()
key = {(r.split, r.part, r.row_in_part): r.row for r in docs.itertuples()}
held = docs[docs.split == "heldout"]
sizes = docs.shingles.to_numpy()

# word reference
parts = find_parts(INPUTS, ["train", "heldout"])
index = defaultdict(list)
held_sets = {}
for split, part, path in parts:
    if split != "heldout":
        continue
    for row, pack, doc_id, text in read_file(path):
        g = key[(split, part, row)]
        s = np.frombuffer(shingles(h1_key(text or ""), 5)[0], dtype=np.uint64)
        held_sets[g] = s
        for h in s.tolist():
            index[h].append(g)
hkeys = np.array(sorted(index), dtype=np.uint64)
def shared_only(s):
    if not len(hkeys) or not len(s):
        return []
    pos = np.minimum(np.searchsorted(hkeys, s), len(hkeys) - 1)
    return s[hkeys[pos] == s].tolist()
ref_word = set()
for split, part, path in parts:
    for row, pack, doc_id, text in read_file(path):
        g = key[(split, part, row)]
        if sizes[g] == 0:
            continue
        s = np.frombuffer(shingles(h1_key(text or ""), 5)[0], dtype=np.uint64)
        cnt = defaultdict(int)
        for h in shared_only(s):
            for o in index[h]:
                if o != g:
                    cnt[o] += 1
        for o, inter in cnt.items():
            if sizes[o] and inter / (sizes[g] + sizes[o] - inter) >= 0.80:
                ref_word.add((min(g, o), max(g, o)))
    print(split, part, len(ref_word), flush=True)

# code reference from step 1's exact code-token sets
summ = json.loads((RUN / "overlap_summary.json").read_text())
code = {}
offset = 0
for p in summ["inputs"]["parts"]:
    sp, pt = p["part"].split("/", 1)
    stem = WORK / sp / pt.replace("/", "__")
    z = np.load(stem.with_suffix(".docs.npz"), allow_pickle=True)
    hashes = np.load(stem.with_suffix(".code.npy"))
    st = np.r_[0, np.cumsum(z["code_size"])]
    for i, (r, lines) in enumerate(zip(z["code_row"].tolist(), z["code_lines"].tolist())):
        if lines >= 20 and z["code_size"][i] > 0:
            code[offset + r] = (sp, hashes[st[i]:st[i + 1]])
    offset += len(z["row"])
cindex = defaultdict(list)
for g, (sp, s) in code.items():
    if sp == "heldout":
        for h in s.tolist():
            cindex[h].append(g)
ref_code = set()
for g, (sp, s) in code.items():
    cnt = defaultdict(int)
    for h in s.tolist():
        for o in cindex.get(h, ()):
            if o != g:
                cnt[o] += 1
    for o, inter in cnt.items():
        if inter / (len(s) + len(code[o][1]) - inter) >= 0.85:
            ref_code.add((min(g, o), max(g, o)))

sha = None
pairs = {(int(r["row_a"]), int(r["row_b"])) for r in csv.DictReader(open(RUN / "overlap_pairs.csv"))}
matches = list(csv.DictReader(open(RUN / "overlap_matches.csv")))
h2_code = {(int(r["row_a"]), int(r["row_b"])) for r in matches if r["rule"] == "H2" and r["code_jaccard"]}
h1_edges = [(int(r["row_a"]), int(r["row_b"])) for r in matches if r["rule"] == "H1"]
comp = {}
for a, b in h1_edges:
    comp[b] = a
same_h1 = lambda a, b: comp.get(a, a) == comp.get(b, b)
miss_word = [p for p in ref_word if p not in pairs and not same_h1(*p)]
miss_code = [p for p in ref_code if p not in h2_code and not same_h1(*p)]
out = {"heldout_documents": int(len(held)), "reference_word_pairs_ge_0.80": len(ref_word),
       "reference_code_pairs_ge_0.85": len(ref_code),
       "word_pairs_not_candidates": len(miss_word), "code_pairs_not_found": len(miss_code),
       "heldout_train_word_pairs": sum(1 for a, b in ref_word if docs.split[a] != docs.split[b]),
       "heldout_heldout_word_pairs": sum(1 for a, b in ref_word if docs.split[a] == docs.split[b] == "heldout"),
       "examples": [[docs.id[a], docs.id[b]] for a, b in (miss_word + miss_code)[:10]]}
Path("out/heldout_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
