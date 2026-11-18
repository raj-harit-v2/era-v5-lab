r"""H2 all-to-all Jaccard matrix across one pack's folders: word 5-grams of the H1 key, every pair of documents.

Reads the Part_* and Heldout folders of one pack as one combined set, in the same order and with the same H1 key as
h1_sha256.py (normalize.match_key, then NFKC, casefold, whitespace), turns each key into its set of word 5-grams
(dedup_design_v1.md H2) and computes the exact Jaccard similarity |A & B| / |A | B| of every pair of documents. A
document shorter than 5 words is one shingle, its whole key. Documents are never changed, and no text is written out:
IDs, scores and counts only.

How: X is the documents x shingles 0/1 matrix. X times its transpose, one block of rows at a time, gives |A & B| for
every pair that shares a shingle; every other pair has Jaccard 0. Shingles are compared by 64-bit hashes (gram_hashes). A
shingle found in only one document is left out of X (it can never be shared) but still counts in that document's size.

HOW TO RUN IT
=============
Run from teams/01-data-a/ with the packages pinned in dedup/requirements_overlap.txt.

    python3 -I dedup/jaccard_matrix.py --pack <packs folder>/en-dclm --out <output folder, outside the repo>
    python3 -I dedup/jaccard_matrix.py --pack <packs folder>/en-dclm --out <...> --floor 0.3

WHAT IT WRITES (in --out)
=========================
  jaccard_matrix.npz      the N x N matrix, for scipy.sparse.load_npz: symmetric, 1 on the diagonal, row i is row i of
                          jaccard_docs.csv. Only scores at or above --floor are stored, so an empty cell means "below
                          the floor", not 0. (A dense matrix of 61,975 documents would be about 15 GB.)
  jaccard_docs.csv        matrix row -> document: row, folder, file, row_in_file, doc_id, words, shingles
  jaccard_pairs.csv       every pair at or above --floor, highest score first
  jaccard_histogram.csv   all N(N-1)/2 pairs in bins of 0.01, including the pairs that share nothing (Jaccard 0)
  jaccard_summary.json    the counts: pairs at or above each E1 threshold (0.70 ... 0.95), and per folder pair
"""
import argparse, json, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from h1_sha256 import NORMALIZE_ID, h1_key, pack_folders, read_docs, write_csv  # noqa: E402

THRESHOLDS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)   # dedup_design_v1.md E1
MIN_WORDS = 50                                      # dedup_design_v1.md H2 minimum for prose: counted, not dropped


# One fixed odd 64-bit multiplier per position in a k-gram (k <= 8). Changing them changes every gram hash:
# only with a check that the overlap outputs stay byte-identical.
_POSITION = (0x9E3779B97F4A7C15, 0xC2B2AE3D27D4EB4F, 0x165667B19E3779F9, 0xD6E8FEB86659FD93,
             0xFF51AFD7ED558CCD, 0xC4CEB9FE1A85EC53, 0x27D4EB2F165667C5, 0x94D049BB133111EB)


def gram_hashes(units, k):
    """Distinct 64-bit hashes of every run of k consecutive units (words or code tokens), as joined 8-byte values.

    Each unit is hashed once in C (pandas SipHash with its fixed default key, the same on every machine), and the
    k hashes of each window are combined with NumPy arithmetic (a sum with one odd multiplier per position, then the
    splitmix64 finaliser). No Python loop runs over units or k-grams. Fewer than k units give no gram.
    """
    import numpy as np
    from pandas.util import hash_array
    n = len(units) - k + 1
    if n <= 0:
        return b""
    h = hash_array(np.asarray(units, dtype=object), categorize=False)
    with np.errstate(over="ignore"):
        z = np.zeros(n, dtype=np.uint64)
        for j in range(k):                                   # k positions, not units
            z += h[j:j + n] * np.uint64(_POSITION[j])
        z ^= z >> np.uint64(30); z *= np.uint64(0xBF58476D1CE4E5B9)
        z ^= z >> np.uint64(27); z *= np.uint64(0x94D049BB133111EB)
        z ^= z >> np.uint64(31)
    return np.unique(z).tobytes()


def shingles(key, k):
    """The key's set of word k-grams as joined 8-byte hashes (gram_hashes), and its number of words.
    A key of fewer than k words is one shingle: the whole key."""
    words = key.split(" ") if key else []
    if len(words) >= k:
        return gram_hashes(words, k), len(words)
    return (gram_hashes([key], 1) if key else b""), len(words)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", required=True, help="pack folder holding Part_* and Heldout, e.g. <packs>/en-dclm")
    ap.add_argument("--out", required=True, help="output folder; keep it outside the repo")
    ap.add_argument("--floor", type=float, default=0.5, help="store pairs at or above this Jaccard (default 0.5)")
    ap.add_argument("--k", type=int, default=5, help="words per shingle (default 5)")
    ap.add_argument("--block", type=int, default=256, help="matrix rows per step; lower it if memory runs short")
    args = ap.parse_args()
    if not 0 < args.floor <= 1:
        ap.error("--floor must be above 0 and at most 1; the histogram still counts every pair")
    try:
        import numpy as np
        import pandas
        from scipy import sparse
    except ImportError:
        sys.exit("ERROR: needs numpy, scipy and pandas: "
                 "python3 -m pip install -r teams/01-data-a/dedup/requirements_overlap.txt")
    pack, out = Path(args.pack), Path(args.out)
    dirs = pack_folders(pack)
    if not dirs:
        sys.exit(f"ERROR: no Part_* or Heldout folder in {pack}")
    names = [d.name for d in dirs]

    # 1. Combine all folders: one row per document, with its set of shingles.
    docs, blobs, t0 = [], [], time.time()   # docs[i] = (folder, file, row_in_file, doc_id, words, shingles)
    for d in dirs:
        n = 0
        for file, row, doc_id, text in read_docs(d):
            blob, words = shingles(h1_key(text or ""), args.k)
            blobs.append(blob)
            docs.append((d.name, str(file), row, doc_id, words, len(blob) // 8))
            n += 1
        print(f"{d.name}: {n} documents shingled ({time.time() - t0:.0f}s)", flush=True)
    N = len(docs)
    if N < 2:
        sys.exit(f"ERROR: {N} document(s) in {pack}; nothing to compare")
    out.mkdir(parents=True, exist_ok=True)
    sizes = np.array([d[5] for d in docs], dtype=np.int64)
    folder_ix = np.array([names.index(d[0]) for d in docs], dtype=np.int64)

    # 2. X: documents x the shingles found in 2+ documents.
    _, inv = np.unique(np.frombuffer(b"".join(blobs), dtype=np.int64), return_inverse=True)
    del blobs
    df = np.bincount(inv)
    shared = df >= 2
    keep = shared[inv]
    rows = np.repeat(np.arange(N), sizes)[keep]
    cols = (np.cumsum(shared) - 1)[inv[keep]]
    X = sparse.csr_matrix((np.ones(len(rows), np.int32), (rows, cols)), shape=(N, int(shared.sum())))
    XT = X.T.tocsr()
    del inv, keep, rows, cols
    print(f"{N} documents, {len(df)} distinct shingles, {X.shape[1]} of them in 2+ documents; "
          f"about {int((df[shared] ** 2).sum()):,} intersection steps", flush=True)

    # 3. All-to-all: |A & B| for every pair that shares a shingle, block by block; every other pair is 0.
    total = N * (N - 1) // 2
    hist, over, sharing = np.zeros(100, np.int64), dict.fromkeys(THRESHOLDS, 0), 0
    kept = ([], [], [], [])   # row a, row b, Jaccard, shared shingles: pairs at or above --floor
    t1 = time.time()
    for step, lo in enumerate(range(0, N, args.block)):
        hi = min(lo + args.block, N)
        P = (X[lo:hi] @ XT).tocoo()
        i, j = P.row.astype(np.int64) + lo, P.col.astype(np.int64)
        m = j > i
        i, j, inter = i[m], j[m], P.data[m].astype(np.int64)
        score = inter / (sizes[i] + sizes[j] - inter)
        sharing += len(score)
        hist += np.bincount(np.minimum((score * 100 + 1e-9).astype(np.int64), 99), minlength=100)
        for t in THRESHOLDS:
            over[t] += int((score >= t).sum())
        k = score >= args.floor
        for acc, v in zip(kept, (i[k], j[k], score[k], inter[k])):
            acc.append(v)
        if step % 20 == 0 or hi == N:
            el = time.time() - t1
            print(f"  rows {hi}/{N}: {el:.0f}s, about {el * (N - hi) / hi:.0f}s left", flush=True)
    hist[0] += total - sharing

    I, J, S, K = (np.concatenate(a) for a in kept)
    order = np.lexsort((J, I, -S))
    I, J, S, K = I[order], J[order], S[order], K[order]
    diag = np.arange(N)
    M = sparse.coo_matrix((np.concatenate([S, S, np.ones(N)]),
                           (np.concatenate([I, J, diag]), np.concatenate([J, I, diag]))), shape=(N, N)).tocsr()
    sparse.save_npz(out / "jaccard_matrix.npz", M)

    write_csv(out / "jaccard_docs.csv", ["row", "folder", "file", "row_in_file", "doc_id", "words", "shingles"],
              ([r, *d] for r, d in enumerate(docs)))
    doc = lambda r: [r, docs[r][0], docs[r][3], docs[r][5]]
    write_csv(out / "jaccard_pairs.csv", ["jaccard", "shared_shingles", "row_a", "folder_a", "doc_id_a", "shingles_a",
                                         "row_b", "folder_b", "doc_id_b", "shingles_b"],
              ([f"{s:.6f}", n, *doc(a), *doc(b)] for a, b, s, n in zip(I.tolist(), J.tolist(), S.tolist(), K.tolist())))
    write_csv(out / "jaccard_histogram.csv", ["jaccard_from", "jaccard_to", "pairs"],
              ([f"{b / 100:.2f}", f"{(b + 1) / 100:.2f}", int(hist[b])] for b in range(100)))

    # Rows are in folder order and a < b, so each pair's folders come out in that order too.
    levels = sorted({args.floor, *(t for t in THRESHOLDS if t >= args.floor)})
    fa, fb = folder_ix[I], folder_ix[J]
    by_folder = {f"{t:.2f}": {f"{names[a]} x {names[b]}": n
                              for (a, b), n in sorted(Counter(zip(fa[S >= t].tolist(), fb[S >= t].tolist())).items())}
                 for t in levels}
    per_folder = Counter(d[0] for d in docs)
    summary = {
        "pack": str(pack.resolve()),
        "normalize_id": NORMALIZE_ID,
        "key": "h1_key of h1_sha256.py: normalize.match_key, then NFKC, casefold, whitespace runs to one space",
        "shingles": f"word {args.k}-grams of the key as 64-bit hashes (gram_hashes: pandas SipHash per word, combined per window); a key under {args.k} words is one shingle",
        "documents": {**{a: per_folder[a] for a in names}, "all": N},
        f"documents_under_{MIN_WORDS}_words": sum(d[4] < MIN_WORDS for d in docs),
        "distinct_shingles": len(df),
        "shingles_in_2_or_more_documents": X.shape[1],
        "pairs_compared": total,
        "pairs_sharing_a_shingle": sharing,
        "pairs_at_or_above": {f"{t:.2f}": over[t] for t in THRESHOLDS},
        "floor": args.floor,
        "pairs_stored": len(S),
        "pairs_at_or_above_by_folder": by_folder,
        "seconds": round(time.time() - t0, 1),
    }
    (out / "jaccard_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote jaccard_matrix.npz, jaccard_docs.csv, jaccard_pairs.csv, jaccard_histogram.csv and "
          f"jaccard_summary.json to {out}")


if __name__ == "__main__":
    sys.exit(main())
