"""Check a multilingual encoder (LaBSE by default) for H3 on Sanskrit, Hindi and Odia (dedup v2 proposal, H3-i).

  python labse_check.py --pairs out/known_pairs.parquet --out out/labse
         [--model sentence-transformers/LaBSE] [--langs san_Deva hin_Deva ory_Orya] [--flores-dir DIR] [--max-pairs N]

WHAT IT MEASURES
================
H3 (h3_design_v1.md) aligns sentences of two documents: two sentences align when each is the other's best match and
their cosine is at least 0.7; a pair qualifies when aligned sentences / sentences of the shorter document >= 0.6.
Whether those numbers suit Sanskrit and Odia is unknown (H3-h, H3-i). This script measures them on:

A. FLORES-200 devtest (true translations, sentence-aligned): for each language L against English (and Sanskrit
   against Hindi), the cosine of true sentence pairs, retrieval precision at 1 in both directions, and the share of
   true pairs at or above each sentence threshold. FLORES is an evaluation benchmark: it is read here to test the
   encoder and is never training data.
B. FLORES pseudo-documents: blocks of 8 consecutive sentences in L and in English. A true block pair is a translation;
   a block paired with another block is a same-domain non-translation. Coverage (H3's score) for both, at sentence
   thresholds 0.5 to 0.9: where true and false pairs separate.
C. ind-sa-fw2 same-document pairs (build_known_pairs.py): a Sanskrit half and an English or Hindi half of one page.
   On inspection most are NOT translations (a Sanskrit news story with an embedded English tweet on the same event),
   so they are the hard case H3 must keep. Their coverage at each threshold shows how many H3 would wrongly match.
   The 15 highest-scoring pairs are listed by doc_id for a human check (some are real translations).

Document text never leaves --out. summary.json holds numbers and doc_ids only.

NEEDS
=====
  pip install sentence-transformers datasets pyarrow numpy
FLORES-200 comes from the Hugging Face dataset openlanguagedata/flores_plus, which is gated: log in (`hf auth login`)
and accept its terms on the dataset page once. Or pass --flores-dir with one file per language, <lang>.txt (one
sentence per line, devtest order). The model (about 1.9 GB) downloads on first use. CPU is fine: about 20k sentences.
"""
import sys
sys.dont_write_bytecode = True

import argparse, json, random, re, time
from pathlib import Path

import numpy as np

SENT_END = re.compile(r"(?<=[.!?।॥])\s+|\n+")
MIN_SENT_CHARS = 20      # h3_design_v1.md: sentences under 20 characters are dropped
MAX_SENTENCES = 16       # h3_design_v1.md: max_sentences
SENT_THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9]
COVERAGE_RULE = 0.6      # h3_design_v1.md, provisional
BLOCK = 8                # sentences per FLORES pseudo-document


def sentences(text):
    out = [s.strip() for s in SENT_END.split(text or "") if s and len(s.strip()) >= MIN_SENT_CHARS]
    return out[:MAX_SENTENCES]


def coverage(a, b, thr):
    """H3's score: mutual-best sentence pairs at cosine >= thr, over the shorter side. a, b: normalised rows."""
    if len(a) == 0 or len(b) == 0:
        return 0.0
    s = a @ b.T
    best_b, best_a = s.argmax(1), s.argmax(0)
    aligned = sum(1 for i, j in enumerate(best_b) if best_a[j] == i and s[i, j] >= thr)
    return aligned / min(len(a), len(b))


def q(xs):
    if len(xs) == 0:
        return {}
    xs = np.sort(np.asarray(xs, dtype=float))
    return {k: round(float(np.quantile(xs, p)), 4) for k, p in
            (("p05", .05), ("p25", .25), ("median", .5), ("p75", .75), ("p95", .95))} | {"mean": round(float(xs.mean()), 4)}


def load_flores(lang, flores_dir):
    if flores_dir:
        return [l.rstrip("\n") for l in open(Path(flores_dir) / f"{lang}.txt", encoding="utf-8")]
    from datasets import load_dataset
    ds = load_dataset("openlanguagedata/flores_plus", lang, split="devtest")
    col = "text" if "text" in ds.column_names else "sentence"
    return list(ds[col])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", type=Path, required=True, help="known_pairs.parquet from build_known_pairs.py")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="sentence-transformers/LaBSE")
    ap.add_argument("--langs", nargs="+", default=["san_Deva", "hin_Deva", "ory_Orya"])
    ap.add_argument("--flores-dir", type=Path, help="local FLORES files <lang>.txt instead of the Hugging Face dataset")
    ap.add_argument("--max-pairs", type=int, default=0, help="limit part C to this many pairs (0 = all)")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--progress", action="store_true", help="show encoding progress bars and stage times")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(a.seed)
    t0 = time.time()

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(a.model)
    model.max_seq_length = 128  # h3_design_v1.md: max_seq_length 128
    enc = lambda xs, bar=False: model.encode(xs, batch_size=a.batch, normalize_embeddings=True, convert_to_numpy=True,
                                  show_progress_bar=bar)
    summary = {"model": a.model, "settings": {"min_sent_chars": MIN_SENT_CHARS, "max_sentences": MAX_SENTENCES,
               "max_seq_length": 128, "coverage_rule": COVERAGE_RULE, "block": BLOCK, "seed": a.seed}}

    # ---- A and B: FLORES ------------------------------------------------------------------------------------------
    log = (lambda m: print(f"[{time.time() - t0:7.0f} s] {m}", flush=True)) if a.progress else (lambda m: None)
    log(f"model loaded: {a.model}")
    flores = {l: load_flores(l, a.flores_dir) for l in ["eng_Latn", *a.langs]}
    log("FLORES loaded; encoding")
    n = min(len(v) for v in flores.values())
    emb = {l: enc(v[:n], a.progress) for l, v in flores.items()}
    pairs = [(l, "eng_Latn") for l in a.langs]
    if "san_Deva" in a.langs and "hin_Deva" in a.langs:
        pairs.append(("san_Deva", "hin_Deva"))
    log("FLORES encoded")
    summary["flores"] = {"sentences": n}
    for x, y in pairs:
        s = emb[x] @ emb[y].T
        true = np.diag(s)
        off = s.copy(); np.fill_diagonal(off, -1); best_wrong = off.max(1)
        blocks = n // BLOCK
        cov_true = {t: [] for t in SENT_THRESHOLDS}
        cov_false = {t: [] for t in SENT_THRESHOLDS}
        for b in range(blocks):
            ex, ey = emb[x][b * BLOCK:(b + 1) * BLOCK], emb[y][b * BLOCK:(b + 1) * BLOCK]
            o = rnd.choice([k for k in range(blocks) if k != b])
            eo = emb[y][o * BLOCK:(o + 1) * BLOCK]
            for t in SENT_THRESHOLDS:
                cov_true[t].append(coverage(ex, ey, t))
                cov_false[t].append(coverage(ex, eo, t))
        summary["flores"][f"{x}-{y}"] = {
            "p_at_1": {f"{x}->{y}": round(float((s.argmax(1) == np.arange(n)).mean()), 4),
                       f"{y}->{x}": round(float((s.argmax(0) == np.arange(n)).mean()), 4)},
            "true_pair_cosine": q(true),
            "best_wrong_cosine": q(best_wrong),
            "true_pairs_at_or_above": {str(t): round(float((true >= t).mean()), 4) for t in SENT_THRESHOLDS},
            "pseudo_documents": {"blocks": blocks, "sentences_per_block": BLOCK,
                                 "coverage_true": {str(t): q(v) for t, v in cov_true.items()},
                                 "coverage_other_block": {str(t): q(v) for t, v in cov_false.items()},
                                 "true_qualifying_at_rule": {str(t): round(float(np.mean(np.array(v) >= COVERAGE_RULE)), 4)
                                                             for t, v in cov_true.items()},
                                 "other_qualifying_at_rule": {str(t): round(float(np.mean(np.array(v) >= COVERAGE_RULE)), 4)
                                                              for t, v in cov_false.items()}}}

    # ---- C: ind-sa-fw2 same-document pairs ------------------------------------------------------------------------
    import pyarrow.parquet as pq
    rows = pq.read_table(a.pairs).to_pylist()
    if a.max_pairs:
        rows = rnd.sample(rows, min(a.max_pairs, len(rows)))
    log(f"part C: {len(rows)} same-page pairs")
    per_pair = []
    for i, r in enumerate(rows):
        if i and i % 50 == 0:
            log(f"part C: {i} of {len(rows)} pairs")
        sa, tr = sentences(r["sa_text"]), sentences(r["tr_text"])
        if len(sa) < 3 or len(tr) < 3:
            continue
        es, et = enc(sa), enc(tr)
        head = float(enc([" ".join(sa[:4])])[0] @ enc([" ".join(tr[:4])])[0])
        per_pair.append({"doc_id": r["doc_id"], "kind": r.get("kind", ""), "tr_lang": r["tr_lang"],
                         "head_cosine": round(head, 4), "sa_sentences": len(sa), "tr_sentences": len(tr),
                         **{f"coverage_{t}": round(coverage(es, et, t), 4) for t in SENT_THRESHOLDS}})
    c = {"pairs_scored": len(per_pair)}
    for kind in sorted({p["kind"] for p in per_pair}):
        for lang in ("en", "hi"):
            ps = [p for p in per_pair if p["kind"] == kind and p["tr_lang"] == lang]
            if not ps:
                continue
            c[f"{kind}/{lang}"] = {"pairs": len(ps), "head_cosine": q([p["head_cosine"] for p in ps]),
                                   "qualifying_at_rule": {str(t): round(float(np.mean([p[f"coverage_{t}"] >= COVERAGE_RULE for p in ps])), 4)
                                                          for t in SENT_THRESHOLDS}}
    top = sorted(per_pair, key=lambda p: -p["coverage_0.7"])[:15]
    c["highest_coverage_at_0.7"] = [{k: p[k] for k in ("doc_id", "kind", "tr_lang", "coverage_0.7", "head_cosine")} for p in top]
    summary["ind_sa_fw2_same_document_pairs"] = c
    summary["seconds"] = round(time.time() - t0, 1)

    import csv
    with open(a.out / "pair_scores.csv", "w", newline="", encoding="utf-8") as f:
        if per_pair:
            w = csv.DictWriter(f, fieldnames=list(per_pair[0])); w.writeheader(); w.writerows(per_pair)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary["flores"][k]["p_at_1"] for k in summary["flores"] if k != "sentences"}, indent=1))
    print(f"done in {summary['seconds']} s; see {a.out / 'summary.json'}")


if __name__ == "__main__":
    main()
