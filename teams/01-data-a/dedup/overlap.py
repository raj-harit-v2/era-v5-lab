r"""Cross-pack overlap: the all-to-all Jaccard similarity of every pair of documents across several packs.

Reads all cleaned Parquet parts under train/ and heldout/ as one combined set, builds each document's H1 key
(h1_sha256.py: spec v1 normalize.match_key, then NFKC, casefold, whitespace), splits it into word 5-grams
(jaccard_matrix.py) and computes the exact Jaccard similarity of every pair of documents, inside a pack and across packs.
A document is named <pack_id>-<doc_id>, e.g. en-dclm-0086b8a3e2a24597. Pairs scoring 1.0 are kept and listed like every
other pair; "exact" marks the pairs whose H1 keys are identical (same SHA-256), and two empty documents score 1.0.
Documents are never changed, and no text is written out: IDs, scores and counts only.

Pack identity comes exclusively from each row's pack_id column, never from a filename or directory.
All parts with the same pack_id form one logical pack, across both splits. Reports outside the split
folders are ignored. Input checksum verification is deferred; no manifest or SHA256SUMS is required.

HOW TO RUN IT
=============
With the cleaner outputs under out/tokenizer_sample_v0_clean/ in the repository root. Python 3.10 or later with
numpy, scipy, pandas, pyarrow and pygments (see requirements_overlap.txt). It needs no network and no keys, reads only its
inputs and writes only to out/ in the repository root. Paths in the config are relative to the repository root, the
job's working directory, so the script can also be started from any other folder.

    python teams/01-data-a/dedup/overlap.py --config teams/01-data-a/dedup/overlap.json

CONFIG (JSON; keys starting with "_" are comments)
==================================================
  inputs              the cleaned output folder               (default out/tokenizer_sample_v0_clean)
  splits              train and/or heldout                     (default both)
  out                 the output folder, inside out/                             (default out/overlap)
  floor               raw word-score reporting floor, above 0 and at most 0.80   (default 0.5)
  k, block, top       words per shingle, matrix rows per step, pairs printed     (default 5, 256, 20)
  max_output_mb       fail if the outputs are larger                             (default 50)
  expected_packs      optional exact inventory check; [] discovers whatever is present

WHAT IT WRITES (in out)
=======================
  overlap_matrix.csv     source x source shares of documents with at least one qualifying H1/H2 match
  overlap_matrix_counts.csv  numerators and denominators for those shares; diagonal excludes self-matches
  overlap_matches.csv    qualifying H1/H2 pairs; mixed domains must pass both domains' H2 rules
  overlap_pairs.csv       every pair at or above the floor, 1.0 included, highest first: id_a, id_b, jaccard, shared
                          5-grams, exact, and each document's pack, split, part, size and matrix row
  overlap_matrix.npz      the N x N matrix, for scipy.sparse.load_npz: symmetric, 1 on the diagonal, row i is row i of
                          overlap_docs.parquet. Only scores at or above the floor are stored, so an empty cell means
                          "below the floor", not 0.
  overlap_docs.parquet    matrix row -> document: row, id, doc_id, pack, split, part, row_in_part, words, shingles
  overlap_by_pack.csv     pack x pack: pairs at or above each level (the floor, the E1 thresholds, 1.0) and exact pairs
  overlap_histogram.csv   all N(N-1)/2 pairs in bins of 0.01, including the pairs that share nothing (Jaccard 0)
  overlap_summary.json    the counts, the input parts and document counts, wall time, peak RSS, package versions, and
                          each other output's size and sha256
"""
import sys
sys.dont_write_bytecode = True   # write only to ./out/: no __pycache__ beside the scripts

import argparse, csv, hashlib, json, platform, resource, time  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from h1_sha256 import NORMALIZE_ID, h1_key, write_csv  # noqa: E402
from jaccard_matrix import THRESHOLDS, shingles  # noqa: E402
from overlap_report import write_matrix  # noqa: E402
from overlap_rules import domain, qualifying_pairs  # noqa: E402

REPO = Path(__file__).resolve().parents[3]   # teams/01-data-a/dedup/overlap.py -> the repository root
DEFAULTS = {"inputs": "out/tokenizer_sample_v0_clean",
            "splits": ["train", "heldout"], "out": "out/overlap", "floor": 0.5, "k": 5, "block": 256, "top": 20,
            "max_output_mb": 50, "expected_packs": []}
CHUNK = 2000   # documents per block of shingle digests while reading


def load_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = sorted(k for k in raw if not k.startswith("_") and k not in DEFAULTS)
    if unknown:
        sys.exit(f"ERROR: unknown keys in {path}: {unknown}")
    cfg = {**DEFAULTS, **{k: v for k, v in raw.items() if not k.startswith("_")}}
    if any(cfg[k] and Path(cfg[k]).is_absolute() for k in ("inputs", "out")):
        sys.exit("ERROR: inputs and out must be relative to the repository root")
    if not 0 < cfg["floor"] <= 0.80:
        sys.exit("ERROR: floor must be above 0 and at most 0.80 to retain every H2 prose candidate")
    if not (REPO / cfg["out"]).resolve().is_relative_to((REPO / "out").resolve()):
        sys.exit(f"ERROR: out must be inside out/ in the repository root, not {cfg['out']}")
    if (not isinstance(cfg["splits"], list) or not cfg["splits"]
            or any(s not in ("train", "heldout") for s in cfg["splits"])
            or len(set(cfg["splits"])) != len(cfg["splits"])):
        sys.exit(f"ERROR: splits must be train and/or heldout, not {cfg['splits']}")
    for name in ("k", "block"):
        if type(cfg[name]) is not int or cfg[name] <= 0:
            sys.exit(f"ERROR: {name} must be a positive integer")
    if cfg["k"] != 5:
        sys.exit("ERROR: k must be 5 for the H2 design rules")
    if type(cfg["top"]) is not int or cfg["top"] < 0:
        sys.exit("ERROR: top must be a nonnegative integer")
    if not isinstance(cfg["max_output_mb"], (int, float)) or not 0 < cfg["max_output_mb"] <= 50:
        sys.exit("ERROR: max_output_mb must be above 0 and at most 50 (JOB_REQUEST.md)")
    expected = cfg["expected_packs"]
    if not isinstance(expected, list) or any(not isinstance(p, str) or not p.strip() for p in expected) or len(set(expected)) != len(expected):
        sys.exit("ERROR: expected_packs must be a list of distinct nonempty pack IDs")
    return cfg


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_parts(inputs, splits):
    """All Parquet files under the selected split folders; paths provide provenance only."""
    for split in splits:
        if not (inputs / split).is_dir():
            sys.exit(f"ERROR: missing selected split folder: {inputs / split}")
    parts = [(split, str(path.relative_to(inputs / split)), path)
             for split in splits for path in sorted((inputs / split).rglob("*.parquet")) if path.is_file()]
    if not parts:
        sys.exit(f"ERROR: no Parquet parts under {inputs} in splits {splits}")
    return parts


def read_file(path):
    """Read embedded pack identity without changing the shared H1 reader's interface."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    columns = ["pack_id", "doc_id", "text"]
    missing = set(columns) - set(pf.schema_arrow.names)
    if missing:
        sys.exit(f"ERROR: {path} has no {sorted(missing)} column (it has {pf.schema_arrow.names})")
    row = 0
    for batch in pf.iter_batches(batch_size=1000, columns=columns):
        for pack, doc_id, text in zip(*(batch.column(c).to_pylist() for c in columns)):
            if not isinstance(pack, str) or not pack.strip():
                sys.exit(f"ERROR: {path} row {row} has invalid pack_id {pack!r}")
            if not isinstance(doc_id, str) or not doc_id.strip():
                sys.exit(f"ERROR: {path} row {row} has invalid doc_id {doc_id!r}")
            if not isinstance(text, str):
                sys.exit(f"ERROR: {path} row {row} has invalid text (expected string)")
            yield row, pack, doc_id, text
            row += 1


def peak_rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss   # bytes on macOS, KiB on Linux
    return round(r / (1 << 20) if sys.platform == "darwin" else r / 1024, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="JSON config; see CONFIG above")
    cfg = load_config(ap.parse_args().config)
    try:
        import numpy as np
        import pyarrow as pa
        import pyarrow.parquet as pq
        import scipy
        import pandas
        import pygments
        from scipy import sparse
    except ImportError:
        sys.exit("ERROR: needs numpy, scipy, pandas, pyarrow and pygments: "
                 "python3 -m pip install -r teams/01-data-a/dedup/requirements_overlap.txt")
    t0 = time.time()
    inputs, out, splits = REPO / cfg["inputs"], REPO / cfg["out"], cfg["splits"]
    parts = find_parts(inputs, splits)
    print(f"{len(parts)} cleaned parts found (input checksum verification deferred)", flush=True)

    # 1. Combine every part of every pack: one row per document, with its H1 hash and its set of shingles.
    # docs[i] = (pack, split, part, row_in_part, doc_id, words, shingles, sha256)
    docs, chunks, buf, part_docs = [], [], [], []
    for split, part, path in parts:
        n = 0
        for row, pack, doc_id, text in read_file(path):
            key = h1_key(text or "")
            blob, words = shingles(key, cfg["k"])
            buf.append(blob)
            docs.append((pack, split, part, row, doc_id, words, len(blob) // 8,
                         hashlib.sha256(key.encode("utf-8")).hexdigest()))
            n += 1
            if len(buf) == CHUNK:
                chunks.append(np.frombuffer(b"".join(buf), dtype=np.int64))
                buf = []
        part_docs.append(n)
        print(f"{split}/{part}: {n} documents ({time.time() - t0:.0f}s)", flush=True)
    if buf:
        chunks.append(np.frombuffer(b"".join(buf), dtype=np.int64))
    N = len(docs)
    if N < 2:
        sys.exit(f"ERROR: {N} document(s); nothing to compare")
    sizes = np.array([d[6] for d in docs], dtype=np.int64)
    indptr = np.concatenate(([0], np.cumsum(sizes)))
    packs = sorted({d[0] for d in docs})
    for pack in packs:
        domain(pack)  # Refuse unsupported code-pack IDs before expensive scoring.
    if cfg["expected_packs"] and set(packs) != set(cfg["expected_packs"]):
        sys.exit(f"ERROR: pack inventory mismatch: missing={sorted(set(cfg['expected_packs']) - set(packs))}, "
                 f"unexpected={sorted(set(packs) - set(cfg['expected_packs']))}")
    pack_index = {pack: i for i, pack in enumerate(packs)}
    pack_ix = np.array([pack_index[d[0]] for d in docs], dtype=np.int64)
    ids = [f"{d[0]}-{d[4]}" for d in docs]
    sha = [d[7] for d in docs]

    # 2. X: documents x the shingles found in 2+ documents (a shingle in one document can never be shared).
    s = np.concatenate(chunks)
    s.sort()
    eq = s[1:] == s[:-1]
    shared, distinct = np.unique(s[1:][eq]), len(s) - int(eq.sum())
    del s, eq
    rows, cols, start = [], [], 0
    for c in chunks:
        pos = np.minimum(np.searchsorted(shared, c), max(len(shared) - 1, 0))
        hit = shared[pos] == c if len(shared) else np.zeros(len(c), bool)
        cols.append(pos[hit])
        rows.append(np.searchsorted(indptr, start + np.flatnonzero(hit), side="right") - 1)
        start += len(c)
    del chunks
    rows, cols = np.concatenate(rows), np.concatenate(cols)
    X = sparse.csr_matrix((np.ones(len(rows), np.int32), (rows, cols)), shape=(N, len(shared)))
    XT = X.T.tocsr()
    steps = int((np.bincount(cols).astype(np.int64) ** 2).sum()) if len(cols) else 0
    del rows, cols
    print(f"{N} documents, {distinct} distinct shingles, {len(shared)} of them in 2+ documents; "
          f"about {steps:,} intersection steps", flush=True)

    # 3. All-to-all: |A & B| for every pair that shares a shingle, block by block; every other pair is 0.
    total = N * (N - 1) // 2
    hist, over, sharing = np.zeros(100, np.int64), dict.fromkeys(THRESHOLDS, 0), 0
    kept = ([], [], [], [])   # row a, row b, Jaccard, shared shingles: pairs at or above the floor
    t1 = time.time()
    for step, lo in enumerate(range(0, N, cfg["block"])):
        hi = min(lo + cfg["block"], N)
        P = (X[lo:hi] @ XT).tocoo()
        i, j = P.row.astype(np.int64) + lo, P.col.astype(np.int64)
        m = j > i
        i, j, inter = i[m], j[m], P.data[m].astype(np.int64)
        score = inter / (sizes[i] + sizes[j] - inter)
        sharing += len(score)
        hist += np.bincount(np.minimum((score * 100 + 1e-9).astype(np.int64), 99), minlength=100)
        for t in THRESHOLDS:
            over[t] += int((score >= t).sum())
        k = score >= cfg["floor"]
        for acc, v in zip(kept, (i[k], j[k], score[k], inter[k])):
            acc.append(v)
        if step % 50 == 0 or hi == N:
            el = time.time() - t1
            print(f"  rows {hi}/{N}: {el:.0f}s, about {el * (N - hi) / hi:.0f}s left", flush=True)
    empty = np.flatnonzero(sizes == 0)   # documents with an empty key: identical to each other, so 1.0
    a, b = np.triu_indices(len(empty), 1)
    for acc, v in zip(kept, (empty[a], empty[b], np.ones(len(a)), np.zeros(len(a), np.int64))):
        acc.append(v)
    hist[99] += len(a)
    for t in THRESHOLDS:
        over[t] += len(a)
    hist[0] += total - sharing - len(a)
    del X, XT, P  # Free the word index before the independent code-token pass.

    I, J, S, K = (np.concatenate(v) for v in kept)
    order = np.lexsort((J, I, -S))
    I, J, S, K = I[order], J[order], S[order], K[order]
    exact = np.array([sha[x] == sha[y] for x, y in zip(I.tolist(), J.tolist())], dtype=bool)

    # 4. Outputs, all inside ./out/.
    out.mkdir(parents=True, exist_ok=True)
    diag = np.arange(N)
    M = sparse.coo_matrix((np.concatenate([S, S, np.ones(N)]),
                           (np.concatenate([I, J, diag]), np.concatenate([J, I, diag]))), shape=(N, N)).tocsr()
    sparse.save_npz(out / "overlap_matrix.npz", M)
    pq.write_table(pa.table({"row": np.arange(N), "id": ids, "doc_id": [d[4] for d in docs],
                             "pack": [d[0] for d in docs], "split": [d[1] for d in docs],
                             "part": [d[2] for d in docs], "row_in_part": [d[3] for d in docs],
                             "words": [d[5] for d in docs], "shingles": sizes}),
                   out / "overlap_docs.parquet", compression="zstd")
    side = lambda r: [docs[r][0], docs[r][1], docs[r][2], docs[r][6], r]
    write_csv(out / "overlap_pairs.csv", ["id_a", "id_b", "jaccard", "shared_shingles", "exact",
                                          "pack_a", "split_a", "part_a", "shingles_a", "row_a",
                                          "pack_b", "split_b", "part_b", "shingles_b", "row_b"],
              ([ids[x], ids[y], f"{s:.6f}", n, e, *side(x), *side(y)]
               for x, y, s, n, e in zip(I.tolist(), J.tolist(), S.tolist(), K.tolist(), exact.tolist())))
    write_csv(out / "overlap_histogram.csv", ["jaccard_from", "jaccard_to", "pairs"],
              ([f"{b / 100:.2f}", f"{(b + 1) / 100:.2f}", int(hist[b])] for b in range(100)))

    # File order need not match embedded pack order; count each unordered pack pair once.
    pa_ix, pb_ix = np.minimum(pack_ix[I], pack_ix[J]), np.maximum(pack_ix[I], pack_ix[J])
    levels = [(f"{t:.2f}", S >= t) for t in sorted({cfg["floor"], *(t for t in THRESHOLDS if t >= cfg["floor"]), 1.0})]
    levels.append(("exact", exact))
    by_pack = {}
    for name, m in levels:
        c = Counter(zip(pa_ix[m].tolist(), pb_ix[m].tolist()))
        by_pack[name] = {f"{packs[x]} x {packs[y]}": c[(x, y)] for x in range(len(packs)) for y in range(x, len(packs))}
    write_csv(out / "overlap_by_pack.csv", ["level", "pack_a", "pack_b", "pairs"],
              ([name, *pair.split(" x "), n] for name, grid in by_pack.items() for pair, n in grid.items()))

    print("Applying H1/H2 rules; scoring code token pairs independently of raw word scores", flush=True)
    match_counts = Counter()
    def match_rows():
        for x, y, rule, word_score, code_score in qualifying_pairs(parts, docs, I, J, S, exact, read_file, cfg["block"]):
            stage = "within_pack" if docs[x][0] == docs[y][0] else "cross_pack"
            match_counts[rule] += 1
            yield [x, y, rule, stage, docs[x][0], docs[y][0], word_score, code_score]
    write_csv(out / "overlap_matches.csv", ["row_a", "row_b", "rule", "stage", "pack_a", "pack_b",
                                            "word_jaccard", "code_jaccard"], match_rows())
    with (out / "overlap_matches.csv").open(newline="", encoding="utf-8") as f:
        write_matrix(out, {i: d[0] for i, d in enumerate(docs)},
                     ((int(p["row_a"]), int(p["row_b"])) for p in csv.DictReader(f)))

    written = ("overlap_pairs.csv", "overlap_matrix.npz", "overlap_docs.parquet", "overlap_by_pack.csv",
               "overlap_histogram.csv", "overlap_matches.csv", "overlap_matrix.csv", "overlap_matrix_counts.csv")
    files = {f: {"bytes": (out / f).stat().st_size, "sha256": sha256_file(out / f)} for f in written}
    output_bytes = sum(v["bytes"] for v in files.values())
    output_mb = round(output_bytes / (1 << 20), 1)
    h1 = [n for n in Counter(sha).values() if n > 1]
    per_split = Counter((d[0], d[1]) for d in docs)
    summary = {
        "status": "complete",
        "config": cfg,
        "normalize_id": NORMALIZE_ID,
        "key": "h1_key of h1_sha256.py: normalize.match_key, then NFKC, casefold, whitespace runs to one space",
        "shingles": f"word {cfg['k']}-grams of the key as 64-bit hashes (gram_hashes: pandas SipHash per word, combined per window); a key under {cfg['k']} words is one shingle",
        "inputs": {"root": cfg["inputs"], "checksum_verification": "deferred",
                   "parts": [{"part": f"{sp}/{pt}", "documents": n}
                             for (sp, pt, _), n in zip(parts, part_docs)]},
        "documents": {p: {**{sp: per_split[(p, sp)] for sp in splits}, "all": sum(per_split[(p, sp)] for sp in splits)}
                      for p in packs},
        "documents_all": N,
        "ids_used_by_2_or_more_documents": sum(n > 1 for n in Counter(ids).values()),
        "h1_exact_groups": len(h1),
        "documents_in_h1_exact_groups": sum(h1),
        "empty_documents": len(empty),
        "distinct_shingles": distinct,
        "shingles_in_2_or_more_documents": len(shared),
        "pairs_compared": total,
        "pairs_sharing_a_shingle": sharing,
        "pairs_at_or_above": {f"{t:.2f}": over[t] for t in THRESHOLDS},
        "pairs_stored": len(S),
        "pairs_by_pack": by_pack,
        "qualifying_pairs_by_rule": dict(match_counts),
        "matrix_definition": "distinct documents in row source with another qualifying H1/H2 match in column source / row source documents",
        "duplicate_rules": {"prose": "word Jaccard >= 0.80; both >= 50 words",
                            "math": "word Jaccard >= 0.90; identical signed number multisets",
                            "code": "token Jaccard >= 0.85; both >= 20 nonblank lines after comment removal",
                            "mixed_domains": "both domains' rules must pass on both documents",
                            "h1": "same H1 SHA256; bypasses H2 guards", "translations": "not detected"},
        "pack_domains": {p: domain(p) for p in packs},
        "wall_seconds": round(time.time() - t0, 1),
        "peak_rss_mb": peak_rss_mb(),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                     "pandas": pandas.__version__, "pyarrow": pa.__version__, "pygments": pygments.__version__,
                     "platform": platform.platform()},
        "outputs": files,
        "output_mb": output_mb,
    }
    (out / "overlap_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("config", "inputs", "pairs_by_pack", "outputs")},
                     indent=2))
    for name in ("0.80", "1.00", "exact"):
        print(f"\nPairs at {'Jaccard ' + name + ' and above' if name != 'exact' else 'exact (same H1 key)'}:")
        for pair, n in by_pack.get(name, {}).items():
            if n:
                print(f"  {pair:45} {n}")
    print(f"\nTop {min(cfg['top'], len(S))} pairs:")
    for x, y, s, e in list(zip(I.tolist(), J.tolist(), S.tolist(), exact.tolist()))[:cfg["top"]]:
        print(f"  {s:.4f}  {'exact ' if e else '      '}{ids[x]}  {ids[y]}")
    print(f"\nWrote {', '.join(files)} and overlap_summary.json to {out.relative_to(REPO)} ({output_mb} MB)")
    if output_bytes + (out / "overlap_summary.json").stat().st_size > cfg["max_output_mb"] * (1 << 20):
        summary["status"] = "failed_output_limit"
        (out / "overlap_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        sys.exit(f"ERROR: the outputs are {output_mb} MB, over max_output_mb {cfg['max_output_mb']}; job failed")


if __name__ == "__main__":
    sys.exit(main())
