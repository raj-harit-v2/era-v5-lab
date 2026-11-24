r"""Cross-pack overlap at scale: H1 exact hashes, then MinHash + LSH near-duplicate candidates, then v1's exact rules.

A drop-in replacement for overlap.py at corpus scale (TSAI, 23 Nov 2026: exact all-pairs overlap is not acceptable at
corpus-v1 scale). It writes the three files dedup.py and run_pipeline.py read -- overlap_summary.json,
overlap_matches.csv (same columns) and overlap_docs.parquet (same rows, same row order) -- so dedup, apply, F2, the
ledger and the reconciliation do not change. It writes no N x N matrix and no all-pairs histogram.

HOW IT WORKS
============
1. Per part, in parallel (`workers` processes), resumable: read the part, build each document's H1 key (h1_sha256.py),
   its word 5-gram shingles (jaccard_matrix.py, exactly overlap.py's) and a MinHash signature of `hashes` values; for
   code packs also the code-token shingles (overlap_rules.code_shingles) and their signature. Each part's result is
   saved under `work` with the part's input sha256; a rerun reuses every part whose input and settings are unchanged.
2. H1: documents with the same H1 sha256 are exact copies (rule H1). Each group is written as star edges (every member
   with the group's first row); dedup.py joins matches by connected components, so the groups are the same.
3. LSH across all packs and both splits: `bands` bands of `hashes / bands` rows. Two documents whose band values agree
   in any band are a candidate pair. Bands are processed one at a time from memory-mapped signature files. A bucket
   larger than `max_bucket` is written as star edges to its first member instead of all pairs (reported).
4. Every candidate is scored with the EXACT Jaccard of its shingle sets, and overlap.py's H1/H2 rules decide
   (overlap_rules: prose >= 0.80 and both >= 50 words; math >= 0.90 and identical numbers; code >= 0.85 token Jaccard
   and both >= 20 nonblank lines; mixed domains must pass both). MinHash only picks candidates; it never decides.
   Agreement with exact overlap on the sample (dedup v2 item 11): 32 x 4 bands found every qualifying H1/H2 pair.

HOW TO RUN IT
=============
    python teams/01-data-a/dedup/minhash_overlap.py --config teams/01-data-a/dedup/minhash_overlap.json

CONFIG (JSON; keys starting with "_" are comments). overlap.py's keys, plus the MinHash settings:
  inputs, splits, out, floor, k, top, expected_packs    as in overlap.py ("block" is accepted and unused)
  max_output_mb       limit for the files returned to the repository (CSVs and the summary)      (default 50)
  hashes, bands       MinHash values per document and LSH bands; hashes % bands == 0           (default 128, 32)
  seed                fixes the hash functions                                                  (default 20261122)
  workers             processes for step 1; 0 = all cores                                       (default 0)
  max_bucket          LSH bucket size above which a bucket gives star edges only                 (default 2000)
  work                per-part intermediate folder, inside out/                         (default <out>/work)

WHAT IT WRITES (in out)
=======================
  overlap_docs.parquet       row -> document, as overlap.py (job storage; one row per document)
  overlap_matches.csv        qualifying H1/H2 pairs: row_a, row_b, rule, stage, pack_a, pack_b, word_jaccard, code_jaccard
  overlap_matrix.csv, overlap_matrix_counts.csv   source x source shares, as overlap.py
  overlap_by_pack.csv        pack x pack counts of verified pairs at each level
  overlap_pairs.csv          verified candidate pairs at or above the floor (job storage). Below 0.70 this is a
                             sample of the pairs, not all of them: LSH is tuned for >= 0.80.
  overlap_summary.json       counts, inputs and their sha256, stage times, peak RSS, versions, output sizes and sha256
  work/                      per-part signatures (job storage; reused on a rerun)
"""
import sys
sys.dont_write_bytecode = True

import argparse, csv, hashlib, json, os, platform, time  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from h1_sha256 import NORMALIZE_ID, h1_key, write_csv  # noqa: E402
from jaccard_matrix import THRESHOLDS as LEVELS, shingles  # noqa: E402
from overlap_report import write_matrix  # noqa: E402
from overlap_rules import NUMBERS, THRESHOLDS, code_shingles, domain  # noqa: E402

REPO = HERE.parents[2]
DEFAULTS = {"inputs": "out/tokenizer_sample_v0_clean", "splits": ["train", "heldout"], "out": "out/overlap",
            "floor": 0.5, "k": 5, "block": 256, "top": 20, "max_output_mb": 50, "expected_packs": [],
            "hashes": 128, "bands": 32, "seed": 20261122, "workers": 0, "max_bucket": 2000, "work": None}
RETURNED = ("overlap_matches.csv", "overlap_matrix.csv", "overlap_matrix_counts.csv", "overlap_by_pack.csv")
JOB_STORAGE = ("overlap_docs.parquet", "overlap_pairs.csv")
WORK_VERSION = 3   # 2: code-token hashes in their own .code.npy; 3: signatures stored hash-major (hashes x docs)
MAXU = (1 << 64) - 1


# ----------------------------------------------------------------------------------------------------- config, io
def load_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = sorted(k for k in raw if not k.startswith("_") and k not in DEFAULTS)
    if unknown:
        sys.exit(f"ERROR: unknown keys in {path}: {unknown}")
    cfg = {**DEFAULTS, **{k: v for k, v in raw.items() if not k.startswith("_")}}
    if cfg["work"] is None:
        cfg["work"] = str(Path(cfg["out"]) / "work")
    for key in ("inputs", "out", "work"):
        if Path(cfg[key]).is_absolute():
            sys.exit("ERROR: inputs, out and work must be relative to the repository root")
    for key in ("out", "work"):
        if not (REPO / cfg[key]).resolve().is_relative_to((REPO / "out").resolve()):
            sys.exit(f"ERROR: {key} must be inside out/ in the repository root, not {cfg[key]}")
    if not 0 < cfg["floor"] <= 0.80:
        sys.exit("ERROR: floor must be above 0 and at most 0.80")
    if (not isinstance(cfg["splits"], list) or not cfg["splits"]
            or any(s not in ("train", "heldout") for s in cfg["splits"]) or len(set(cfg["splits"])) != len(cfg["splits"])):
        sys.exit(f"ERROR: splits must be train and/or heldout, not {cfg['splits']}")
    if cfg["k"] != 5:
        sys.exit("ERROR: k must be 5 for the H2 design rules")
    for name in ("hashes", "bands", "max_bucket", "block"):
        if type(cfg[name]) is not int or cfg[name] <= 0:
            sys.exit(f"ERROR: {name} must be a positive integer")
    if cfg["hashes"] % cfg["bands"]:
        sys.exit("ERROR: hashes must be a multiple of bands")
    if type(cfg["workers"]) is not int or cfg["workers"] < 0 or type(cfg["seed"]) is not int or type(cfg["top"]) is not int:
        sys.exit("ERROR: workers, seed and top must be integers (workers >= 0)")
    if not isinstance(cfg["max_output_mb"], (int, float)) or not 0 < cfg["max_output_mb"] <= 50:
        sys.exit("ERROR: max_output_mb must be above 0 and at most 50 (JOB_REQUEST.md)")
    exp = cfg["expected_packs"]
    if not isinstance(exp, list) or any(not isinstance(p, str) or not p.strip() for p in exp) or len(set(exp)) != len(exp):
        sys.exit("ERROR: expected_packs must be a list of distinct nonempty pack IDs")
    return cfg


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_parts(inputs, splits):
    for split in splits:
        if not (inputs / split).is_dir():
            sys.exit(f"ERROR: missing selected split folder: {inputs / split}")
    parts = [(split, path.relative_to(inputs / split).as_posix(), path)
             for split in splits for path in sorted((inputs / split).rglob("*.parquet")) if path.is_file()]
    if not parts:
        sys.exit(f"ERROR: no Parquet parts under {inputs} in splits {splits}")
    return parts


def read_file(path):
    """(row, pack_id, doc_id, text) for every row, validated as overlap.py does."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    columns = ["pack_id", "doc_id", "text"]
    missing = set(columns) - set(pf.schema_arrow.names)
    if missing:
        raise ValueError(f"{path} has no {sorted(missing)} column")
    row = 0
    for batch in pf.iter_batches(batch_size=1000, columns=columns):
        for pack, doc_id, text in zip(*(batch.column(c).to_pylist() for c in columns)):
            if not isinstance(pack, str) or not pack.strip():
                raise ValueError(f"{path} row {row} has invalid pack_id {pack!r}")
            if not isinstance(doc_id, str) or not doc_id.strip():
                raise ValueError(f"{path} row {row} has invalid doc_id {doc_id!r}")
            if not isinstance(text, str):
                raise ValueError(f"{path} row {row} has invalid text")
            yield row, pack, doc_id, text
            row += 1


def peak_rss_mb():
    try:
        import resource
        div = (1 << 20) if sys.platform == "darwin" else 1024
        own = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / div
        kids = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / div
        return {"main": round(own, 1), "largest_worker": round(kids, 1)}
    except ImportError:   # Windows
        try:
            import psutil
            return {"main": round(psutil.Process().memory_info().peak_wset / (1 << 20), 1), "largest_worker": None}
        except Exception:
            return {"main": None, "largest_worker": None}


# ------------------------------------------------------------------------------------------------------- MinHash
def hash_params(hashes, seed):
    import numpy as np
    rng = np.random.default_rng(seed)
    a = rng.integers(1, 2**63, hashes, dtype=np.uint64) | np.uint64(1)
    b = rng.integers(0, 2**63, hashes, dtype=np.uint64)
    return a, b


def mix(z):
    """splitmix64 finaliser, in place on a uint64 array."""
    import numpy as np
    z ^= z >> np.uint64(30); z *= np.uint64(0xBF58476D1CE4E5B9)
    z ^= z >> np.uint64(27); z *= np.uint64(0x94D049BB133111EB)
    z ^= z >> np.uint64(31)
    return z


def signature(s, a, b):
    """MinHash: for each hash function, the smallest value over the document's shingles (all MAXU when empty).
    One NumPy call per document; batching documents was measured slower (dedup v2 item 11)."""
    import numpy as np
    out = np.full(len(a), MAXU, dtype=np.uint64)
    if len(s) == 0:
        return out
    with np.errstate(over="ignore"):
        for i in range(0, len(s), 20000):
            c = s[i:i + 20000]
            out = np.minimum(out, mix(c[None, :] * a[:, None] + b[:, None]).min(axis=1))
    return out


# ------------------------------------------------------------------------------------------- step 1: one part each
def part_job(job):
    """Read one part; write its documents, signatures and code shingles under work/. Returns the work file stem."""
    import numpy as np
    split, part, path, digest, work, hashes, seed, k = job
    stem = Path(work) / split / part.replace("/", "__")
    meta_file = stem.with_suffix(".json")
    settings = {"version": WORK_VERSION, "input_sha256": digest, "hashes": hashes, "seed": seed, "k": k}
    if meta_file.exists():
        try:
            if json.loads(meta_file.read_text(encoding="utf-8")).get("settings") == settings:
                return str(stem), True
        except ValueError:
            pass
    stem.parent.mkdir(parents=True, exist_ok=True)
    a, b = hash_params(hashes, seed)
    t0 = time.time()
    rows, doc_ids, packs, words, nsh, shas, sigs = [], [], [], [], [], [], []
    code_rows, code_lines, code_sigs, code_blobs = [], [], [], []
    for row, pack, doc_id, text in read_file(path):
        key = h1_key(text or "")
        blob, n_words = shingles(key, k)
        s = np.frombuffer(blob, dtype=np.uint64)
        rows.append(row); doc_ids.append(doc_id); packs.append(pack); words.append(n_words); nsh.append(len(s))
        shas.append(hashlib.sha256(key.encode("utf-8")).digest())
        sigs.append(signature(s, a, b))
        if domain(pack) == "code":
            cblob, lines = code_shingles(text or "", pack)
            code_rows.append(len(rows) - 1); code_lines.append(lines); code_blobs.append(cblob)
            code_sigs.append(signature(np.frombuffer(cblob, dtype=np.uint64), a, b))
    n = len(rows)
    # Hash-major (hashes x documents): one LSH band is then one contiguous block of the memory-mapped file.
    np.save(stem.with_suffix(".sig.npy"), np.ascontiguousarray(np.stack(sigs).T) if n else np.zeros((hashes, 0), np.uint64))
    np.save(stem.with_suffix(".csig.npy"),
            np.ascontiguousarray(np.stack(code_sigs).T) if code_sigs else np.zeros((hashes, 0), np.uint64))
    sizes = np.array([len(x) // 8 for x in code_blobs], dtype=np.int64)
    np.savez(stem.with_suffix(".docs.npz"), row=np.array(rows, np.int64), doc_id=np.array(doc_ids, dtype=object),
             pack=np.array(packs, dtype=object), words=np.array(words, np.int64), shingles=np.array(nsh, np.int64),
             sha=np.array(shas, dtype="S32"), code_row=np.array(code_rows, np.int64),
             code_lines=np.array(code_lines, np.int64), code_size=sizes)
    np.save(stem.with_suffix(".code.npy"), np.frombuffer(b"".join(code_blobs), dtype=np.uint64))
    meta_file.write_text(json.dumps({"settings": settings, "documents": n, "seconds": round(time.time() - t0, 1)}),
                         encoding="utf-8")
    return str(stem), False


def reshingle_job(job):
    """Re-read one part. For the asked rows, write their word-shingle hashes (sorted, unique) to <out>.cand.npy, one
    block per row in row order, with the rows and block offsets in <out>.cand_idx.npy; return the out stem and
    {row: numbers} for numbers_for. The main process memory-maps the file, so no shingle set is copied between
    processes or held in memory for the whole run."""
    import numpy as np
    path, rows, numbers_for, out = job
    rows, numbers_for = set(rows), set(numbers_for)
    found, blobs, nums = [], [], {}
    for row, pack, doc_id, text in read_file(path):
        if row in rows or row in numbers_for:
            key = h1_key(text or "")
            if row in rows:
                found.append(row); blobs.append(shingles(key, 5)[0])
            if row in numbers_for:
                nums[row] = Counter(NUMBERS.findall(key))
    if out:
        sizes = np.array([len(b) // 8 for b in blobs], np.int64)
        np.save(out + ".cand.npy", np.frombuffer(b"".join(blobs), dtype=np.uint64))
        np.save(out + ".cand_idx.npy", np.stack([np.array(found, np.int64), np.r_[0, np.cumsum(sizes)][:-1], sizes]))
    return out, nums


def mixed_code_job(job):
    """Code shingles of text documents with a code pack's lexer, for mixed code/text candidate pairs."""
    path, wanted = job   # {row: [code_pack, ...]}
    out = {}
    for row, pack, doc_id, text in read_file(path):
        for code_pack in wanted.get(row, ()):
            out[row, code_pack] = code_shingles(text or "", code_pack)
    return out


# ------------------------------------------------------------------------------------------------- step 3: LSH
def band_pairs(sig_files, n_rows, bands, rows_per_band, eligible, max_bucket):
    """Candidate pairs (int64 a*N+b, a < b) from LSH over memory-mapped signature files, one band at a time."""
    import numpy as np
    N = n_rows
    idx = np.flatnonzero(eligible)
    keys, stats = [], {"buckets_2_or_more": 0, "largest_bucket": 0, "star_buckets": 0, "pairs_before_dedup": 0}
    with np.errstate(over="ignore"):
        for band in range(bands):
            cols = slice(band * rows_per_band, (band + 1) * rows_per_band)
            # Open the maps per band and close them after: a band reads 1/bands of each file, and pages of a map
            # that stays open would count towards this process's RSS for the rest of the run.
            maps = [np.load(f, mmap_mode="r") for f in sig_files]
            v = (np.concatenate([np.array(m[cols, :]).T for m in maps]) if maps
                 else np.zeros((0, rows_per_band), np.uint64))
            del maps
            h = np.zeros(len(v), np.uint64)
            for j in range(rows_per_band):
                h = mix(h ^ v[:, j].astype(np.uint64) ^ np.uint64(j + 1) * np.uint64(0x9E3779B97F4A7C15))
            h = h[idx]
            order = np.argsort(h, kind="stable")
            hs, members = h[order], idx[order]
            starts = np.flatnonzero(np.r_[True, hs[1:] != hs[:-1]])
            sizes = np.diff(np.r_[starts, len(hs)])
            multi = sizes >= 2
            stats["buckets_2_or_more"] += int(multi.sum())
            stats["largest_bucket"] = max(stats["largest_bucket"], int(sizes.max()) if len(sizes) else 0)
            for size in np.unique(sizes[multi]):
                st = starts[sizes == size]
                grp = members[st[:, None] + np.arange(size)[None, :]]       # (buckets, size), sorted by row below
                grp.sort(axis=1)
                if size > max_bucket:
                    stats["star_buckets"] += len(st)
                    a, b = np.repeat(grp[:, 0], size - 1), grp[:, 1:].ravel()
                else:
                    iu, ju = np.triu_indices(size, 1)
                    a, b = grp[:, iu].ravel(), grp[:, ju].ravel()
                stats["pairs_before_dedup"] += len(a)
                keys.append(np.unique(a.astype(np.int64) * N + b.astype(np.int64)))
            if len(keys) > 64:
                keys = [np.unique(np.concatenate(keys))]
    return (np.unique(np.concatenate(keys)) if keys else np.zeros(0, np.int64)), stats


def exact_jaccard(x, y):
    import numpy as np
    if len(x) == 0 and len(y) == 0:
        return 1.0, 0
    inter = len(np.intersect1d(x, y, assume_unique=True))
    return inter / (len(x) + len(y) - inter), inter


# ------------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    cfg = load_config(ap.parse_args().config)
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pandas, pygments, scipy
    from concurrent.futures import ProcessPoolExecutor

    t0 = time.time()
    times, rss = {}, {}
    def mark(stage):
        rss[stage] = peak_rss_mb()
    inputs, out, work = REPO / cfg["inputs"], REPO / cfg["out"], REPO / cfg["work"]
    parts = find_parts(inputs, cfg["splits"])
    workers = cfg["workers"] or os.cpu_count() or 1
    print(f"{len(parts)} cleaned parts, {workers} workers", flush=True)
    digests = [sha256_file(p) for _, _, p in parts]

    # 1. Per part, in parallel and resumable.
    jobs = [(sp, pt, str(path), dg, str(work), cfg["hashes"], cfg["seed"], cfg["k"])
            for (sp, pt, path), dg in zip(parts, digests)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(part_job, jobs, chunksize=1))
    reused = sum(r for _, r in results)
    stems = [Path(s) for s, _ in results]
    times["signatures"] = round(time.time() - t0, 1)
    mark("signatures")
    print(f"step 1: {len(parts)} parts ({reused} reused from work/), {times['signatures']}s", flush=True)

    # Document table in overlap.py's row order (parts in sorted order, rows in file order).
    cols = defaultdict(list)
    part_docs, code_index, part_offset = [], [], []
    offset = 0
    code_size, code_lines, code_global, code_part, code_start, code_maps = [], [], [], [], [], []
    for (split, part, _), stem in zip(parts, stems):
        z = np.load(stem.with_suffix(".docs.npz"), allow_pickle=True)
        n = len(z["row"])
        part_offset.append(offset)
        for name in ("row", "doc_id", "pack", "words", "shingles", "sha"):
            cols[name].append(z[name])
        cols["split"].append(np.full(n, split, dtype=object)); cols["part"].append(np.full(n, part, dtype=object))
        code_global.append(z["code_row"] + offset); code_lines.append(z["code_lines"]); code_size.append(z["code_size"])
        code_part.append(np.full(len(z["code_row"]), len(code_maps), np.int64))
        code_start.append(np.r_[0, np.cumsum(z["code_size"])][:-1].astype(np.int64))
        code_maps.append(np.load(stem.with_suffix(".code.npy"), mmap_mode="r"))   # read only for code candidates
        part_docs.append(n)
        offset += n
    N = offset
    if N < 2:
        sys.exit(f"ERROR: {N} document(s); nothing to compare")
    D = {k: np.concatenate(v) for k, v in cols.items()}
    packs = sorted(set(D["pack"].tolist()))
    for p in packs:
        domain(p)
    if cfg["expected_packs"] and set(packs) != set(cfg["expected_packs"]):
        sys.exit(f"ERROR: pack inventory mismatch: missing={sorted(set(cfg['expected_packs']) - set(packs))}, "
                 f"unexpected={sorted(set(packs) - set(cfg['expected_packs']))}")
    dom = np.array([domain(p) for p in D["pack"].tolist()], dtype=object)
    ids = [f"{p}-{d}" for p, d in zip(D["pack"].tolist(), D["doc_id"].tolist())]
    sizes, words = D["shingles"], D["words"]
    code_global = np.concatenate(code_global); code_lines = np.concatenate(code_lines)
    code_size = np.concatenate(code_size); code_part = np.concatenate(code_part)
    code_start = np.concatenate(code_start)
    code_pos = {int(r): i for i, r in enumerate(code_global.tolist())}

    def code_tokens(i):
        """Code-token hashes of code document i (index into code_global), from its part's memory-mapped file."""
        lo = int(code_start[i])
        return np.asarray(code_maps[code_part[i]][lo:lo + int(code_size[i])])

    mark("table")
    # 2. H1: same sha256 of the H1 key. Star edges per group.
    t = time.time()
    _, inv, counts = np.unique(D["sha"], return_inverse=True, return_counts=True)
    order = np.argsort(inv, kind="stable")          # rows grouped by key, each group in row order
    first = order[np.r_[0, np.cumsum(counts)[:-1]]]  # smallest row of each group
    h1_a = first[inv]
    h1_mask = (counts[inv] > 1) & (np.arange(N) != h1_a)
    H1 = np.stack([h1_a[h1_mask], np.arange(N)[h1_mask]], axis=1)
    empty = np.flatnonzero(sizes == 0)
    times["h1"] = round(time.time() - t, 1)

    # 3. LSH, words: every non-empty document; code: code documents with >= 20 nonblank lines and code shingles.
    t = time.time()
    r = cfg["hashes"] // cfg["bands"]
    # Word banding on one representative per H1 group. All members of a group have the same H1 key, hence the same
    # word shingles and the same word signature, so they fall in exactly the same buckets: banding one and expanding
    # its candidate pairs to every member (below) gives the same candidate pairs as banding them all, without the
    # copy-to-copy pairs in the buckets. Code banding keeps every code document: code tokens come from the raw text,
    # which can differ inside an H1 group.
    is_rep = h1_a == np.arange(N)
    word_keys, word_stats = band_pairs([s.with_suffix(".sig.npy") for s in stems], N, cfg["bands"], r,
                                       (sizes > 0) & is_rep, cfg["max_bucket"])
    word_stats["representatives_banded"] = int(((sizes > 0) & is_rep).sum())
    code_ok = (code_lines >= 20) & (code_size > 0)
    if len(code_global):
        ck, code_stats = band_pairs([s.with_suffix(".csig.npy") for s in stems], len(code_global), cfg["bands"], r,
                                    code_ok, cfg["max_bucket"])
        ca, cb = code_global[ck // len(code_global)], code_global[ck % len(code_global)]
    else:
        ca = cb = np.zeros(0, np.int64); code_stats = {}
    ra, rb = word_keys // N, word_keys % N               # representative pairs (different H1 groups)
    word_stats["candidate_pairs_representatives"] = int(len(ra))
    csame = D["sha"][ca] == D["sha"][cb] if len(ca) else np.zeros(0, bool)
    ca, cb = ca[~csame], cb[~csame]
    times["lsh"] = round(time.time() - t, 1)
    mark("lsh")
    print(f"step 3: {len(ra)} word (representative) and {len(ca)} code candidate pairs, {times['lsh']}s", flush=True)

    # 4a. Exact word Jaccard of the word candidates (re-read only the documents in candidate pairs).
    t = time.time()
    need = np.unique(np.r_[ra, rb])
    part_of = np.searchsorted(np.r_[part_offset, N], need, side="right") - 1
    cand_dir = work / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    pis = np.unique(part_of)
    jobs = [(str(parts[pi][2]), D["row"][need[part_of == pi]].tolist(), [], str(cand_dir / f"p{int(pi)}")) for pi in pis]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(reshingle_job, jobs))
    loc = {}       # document -> (memory map, start, size)
    maps = []
    for pi in pis:
        blk = np.load(cand_dir / f"p{int(pi)}.cand.npy", mmap_mode="r"); maps.append(blk)
        rows_, starts_, sizes_ = np.load(cand_dir / f"p{int(pi)}.cand_idx.npy")
        row_to_g = {int(D["row"][g]): int(g) for g in range(part_offset[pi], part_offset[pi] + part_docs[pi])}
        for row, st, sz in zip(rows_.tolist(), starts_.tolist(), sizes_.tolist()):
            g = row_to_g[row]
            if sz != sizes[g]:   # the re-read must give step 1's shingle count
                raise ValueError("input text changed between passes")
            loc[g] = (len(maps) - 1, st, sz)
    if len(loc) != len(need):
        raise ValueError("input row count changed between passes")
    def word_set(g):
        m, st, sz = loc[g]
        return np.asarray(maps[m][st:st + sz])
    rs = np.empty(len(ra)); ri = np.empty(len(ra), np.int64)
    for i, (x, y) in enumerate(zip(ra.tolist(), rb.tolist())):
        rs[i], ri[i] = exact_jaccard(word_set(x), word_set(y))
    del loc, maps
    # Expand each representative pair to every member pair of the two H1 groups (same shingles, same score).
    starts_g = np.r_[0, np.cumsum(counts)[:-1]]
    ca_n, cb_n = counts[inv[ra]], counts[inv[rb]]
    single = (ca_n == 1) & (cb_n == 1)
    xa, xb, xs, xi = [ra[single]], [rb[single]], [rs[single]], [ri[single]]
    for x, y, sc, it in zip(ra[~single].tolist(), rb[~single].tolist(), rs[~single].tolist(), ri[~single].tolist()):
        mx = order[starts_g[inv[x]]:starts_g[inv[x]] + counts[inv[x]]]
        my = order[starts_g[inv[y]]:starts_g[inv[y]] + counts[inv[y]]]
        p, q = np.repeat(mx, len(my)), np.tile(my, len(mx))
        xa.append(np.minimum(p, q)); xb.append(np.maximum(p, q))
        xs.append(np.full(len(p), sc)); xi.append(np.full(len(p), it, np.int64))
    wa, wb, scores, inters = (np.concatenate(v) for v in (xa, xb, xs, xi))
    o = np.argsort(wa * N + wb, kind="stable")            # the same order as banding every document
    wa, wb, scores, inters = wa[o], wb[o], scores[o], inters[o]
    word_stats["candidate_pairs"] = int(len(wa))
    mark("verify_words")
    times["verify_words"] = round(time.time() - t, 1)

    # 4b. v1's rules on the verified pairs (overlap_rules.qualifying_pairs, with code/code from the code candidates).
    t = time.time()
    rule_rows = []   # (a, b, rule, word, code)
    for a, b in H1.tolist():
        rule_rows.append((a, b, "H1", 1.0, ""))
    cands, wanted, lexers = [], set(), defaultdict(set)
    for a, b, s in zip(wa.tolist(), wb.tolist(), scores.tolist()):
        types = {dom[a], dom[b]}
        if types == {"code"}:
            continue
        threshold = max(THRESHOLDS[x] for x in types if x != "code")
        if s < threshold or ("prose" in types and min(words[a], words[b]) < 50):
            continue
        cands.append((a, b, s))
        if types & {"math", "code"}:
            wanted.update((a, b))
        if "code" in types:
            cp = D["pack"][a] if dom[a] == "code" else D["pack"][b]
            for x in (a, b):
                if D["pack"][x] != cp:
                    lexers[x].add(cp)
    numbers, mixed = {}, {}
    if wanted:
        wl = np.array(sorted(wanted)); pw = np.searchsorted(np.r_[part_offset, N], wl, side="right") - 1
        with ProcessPoolExecutor(max_workers=workers) as pool:
            jobs = [(str(parts[pi][2]), [], D["row"][wl[pw == pi]].tolist(), "") for pi in np.unique(pw)]
            for pi, (_, nums) in zip(np.unique(pw), pool.map(reshingle_job, jobs)):
                rowmap = {int(D["row"][g]): g for g in range(part_offset[pi], part_offset[pi] + part_docs[pi])}
                for row, c in nums.items():
                    numbers[rowmap[row]] = c
    if lexers:
        lx = np.array(sorted(lexers)); pl = np.searchsorted(np.r_[part_offset, N], lx, side="right") - 1
        with ProcessPoolExecutor(max_workers=workers) as pool:
            jobs = [(str(parts[pi][2]), {int(D["row"][g]): sorted(lexers[int(g)]) for g in lx[pl == pi]}) for pi in np.unique(pl)]
            for pi, res in zip(np.unique(pl), pool.map(mixed_code_job, jobs)):
                rowmap = {int(D["row"][g]): g for g in range(part_offset[pi], part_offset[pi] + part_docs[pi])}
                for (row, cp), v in res.items():
                    mixed[rowmap[row], cp] = v

    def code_set(x, pack):
        if D["pack"][x] == pack and x in code_pos:
            i = code_pos[x]
            return code_tokens(i), int(code_lines[i])
        blob, lines = mixed[x, pack]
        return np.frombuffer(blob, dtype=np.uint64), lines

    for a, b, s in cands:
        types = {dom[a], dom[b]}
        if "math" in types and numbers[a] != numbers[b]:
            continue
        cs = ""
        if "code" in types:
            cp = D["pack"][a] if dom[a] == "code" else D["pack"][b]
            (xa, la), (xb, lb) = code_set(a, cp), code_set(b, cp)
            if min(la, lb) < 20:
                continue
            cs = exact_jaccard(xa, xb)[0] if len(xa) or len(xb) else 0.0
            if cs < THRESHOLDS["code"]:
                continue
        rule_rows.append((a, b, "H2", s, cs))
    code_checked = 0
    for a, b in zip(ca.tolist(), cb.tolist()):
        ia, ib = code_pos[a], code_pos[b]
        code_checked += 1
        cs = exact_jaccard(code_tokens(ia), code_tokens(ib))[0]
        if cs >= THRESHOLDS["code"]:
            rule_rows.append((a, b, "H2", "", cs))
    mark("rules")
    times["rules"] = round(time.time() - t, 1)

    # 5. Outputs.
    t = time.time()
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("overlap_matrix.npz", "overlap_histogram.csv"):
        (out / stale).unlink(missing_ok=True)
    pq.write_table(pa.table({"row": np.arange(N), "id": ids, "doc_id": D["doc_id"].tolist(), "pack": D["pack"].tolist(),
                             "split": D["split"].tolist(), "part": D["part"].tolist(), "row_in_part": D["row"],
                             "words": words, "shingles": sizes}), out / "overlap_docs.parquet", compression="zstd")
    counts_by_rule = Counter()
    def match_rows():
        for a, b, rule, ws, cs in rule_rows:
            counts_by_rule[rule] += 1
            stage = "within_pack" if D["pack"][a] == D["pack"][b] else "cross_pack"
            yield [a, b, rule, stage, D["pack"][a], D["pack"][b], ws, cs]
    write_csv(out / "overlap_matches.csv", ["row_a", "row_b", "rule", "stage", "pack_a", "pack_b",
                                            "word_jaccard", "code_jaccard"], match_rows())
    write_matrix(out, dict(enumerate(D["pack"].tolist())), ((a, b) for a, b, *_ in rule_rows))
    keep = scores >= cfg["floor"]
    PI = np.r_[H1[:, 0], wa[keep]]; PJ = np.r_[H1[:, 1], wb[keep]]
    PS = np.r_[np.ones(len(H1)), scores[keep]]; PK = np.r_[sizes[H1[:, 1]], inters[keep]]
    PE = np.r_[np.ones(len(H1), bool), np.zeros(int(keep.sum()), bool)]
    o = np.lexsort((PJ, PI, -PS))
    side = lambda x: [D["pack"][x], D["split"][x], D["part"][x], int(sizes[x]), x]
    write_csv(out / "overlap_pairs.csv", ["id_a", "id_b", "jaccard", "shared_shingles", "exact", "pack_a", "split_a",
                                          "part_a", "shingles_a", "row_a", "pack_b", "split_b", "part_b", "shingles_b",
                                          "row_b"],
              ([ids[x], ids[y], f"{s:.6f}", int(k), bool(e), *side(x), *side(y)]
               for x, y, s, k, e in zip(PI[o].tolist(), PJ[o].tolist(), PS[o].tolist(), PK[o].tolist(), PE[o].tolist())))
    pidx = {p: i for i, p in enumerate(packs)}
    pa_ix = np.array([pidx[p] for p in D["pack"].tolist()])
    lo, hi = np.minimum(pa_ix[PI], pa_ix[PJ]), np.maximum(pa_ix[PI], pa_ix[PJ])
    levels = [(f"{x:.2f}", PS >= x) for x in sorted({cfg["floor"], *(x for x in LEVELS if x >= cfg["floor"]), 1.0})]
    levels.append(("exact", PE))
    by_pack = {}
    for name, m in levels:
        c = Counter(zip(lo[m].tolist(), hi[m].tolist()))
        by_pack[name] = {f"{packs[x]} x {packs[y]}": c[(x, y)] for x in range(len(packs)) for y in range(x, len(packs))}
    write_csv(out / "overlap_by_pack.csv", ["level", "pack_a", "pack_b", "pairs"],
              ([name, *pair.split(" x "), n] for name, grid in by_pack.items() for pair, n in grid.items()))
    times["outputs"] = round(time.time() - t, 1)

    files = {f: {"bytes": (out / f).stat().st_size, "sha256": sha256_file(out / f)} for f in (*RETURNED, *JOB_STORAGE)}
    per_split = Counter(zip(D["pack"].tolist(), D["split"].tolist()))
    h1_groups = counts[counts > 1]
    summary = {
        "status": "complete",
        "method": "minhash_lsh",
        "config": cfg,
        "normalize_id": NORMALIZE_ID,
        "key": "h1_key of h1_sha256.py: normalize.match_key, then NFKC, casefold, whitespace runs to one space",
        "shingles": "word 5-grams of the key as 64-bit hashes (jaccard_matrix.shingles), exactly as overlap.py",
        "inputs": {"root": cfg["inputs"], "checksum_verification": "sha256",
                   "parts": [{"part": f"{sp}/{pt}", "documents": n, "sha256": dg}
                             for (sp, pt, _), n, dg in zip(parts, part_docs, digests)]},
        "documents": {p: {**{sp: per_split[(p, sp)] for sp in cfg["splits"]},
                          "all": sum(per_split[(p, sp)] for sp in cfg["splits"])} for p in packs},
        "documents_all": N,
        "h1_exact_groups": int(len(h1_groups)),
        "documents_in_h1_exact_groups": int(h1_groups.sum()),
        "empty_documents": int(len(empty)),
        "minhash": {"hashes": cfg["hashes"], "bands": cfg["bands"], "rows_per_band": r, "seed": cfg["seed"],
                    "parts_reused": reused, "word": word_stats,
                    "code": {**code_stats, "candidate_pairs": int(len(ca)), "eligible_documents": int(code_ok.sum())},
                    "p_found_at": {f"{x:.2f}": 1 - (1 - x ** r) ** cfg["bands"] for x in (0.7, 0.8, 0.85, 0.9)}},
        "pairs_verified": int(len(wa)),
        "pairs_at_or_above": {f"{x:.2f}": int((scores >= x).sum()) for x in LEVELS},
        "pairs_at_or_above_note": "among verified LSH candidates only; complete at >= 0.80 within LSH recall",
        "qualifying_pairs_by_rule": dict(counts_by_rule),
        "h1_edges": "star: each member of an H1 group paired with the group's first row",
        "duplicate_rules": {"prose": "word Jaccard >= 0.80; both >= 50 words",
                            "math": "word Jaccard >= 0.90; identical signed number multisets",
                            "code": "token Jaccard >= 0.85; both >= 20 nonblank lines after comment removal",
                            "mixed_domains": "both domains' rules must pass on both documents",
                            "h1": "same H1 SHA256; bypasses H2 guards", "translations": "not detected"},
        "pack_domains": {p: domain(p) for p in packs},
        "stage_seconds": times,
        "peak_rss_mb_after_stage": rss,
        "wall_seconds": round(time.time() - t0, 1),
        "workers": workers,
        "peak_rss_mb": peak_rss_mb(),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                     "pandas": pandas.__version__, "pyarrow": pa.__version__, "pygments": pygments.__version__,
                     "platform": platform.platform()},
        "outputs": files,
        "returned_files": list(RETURNED) + ["overlap_summary.json"],
        "job_storage_files": list(JOB_STORAGE) + [cfg["work"]],
    }
    (out / "overlap_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    returned = sum(files[f]["bytes"] for f in RETURNED) + (out / "overlap_summary.json").stat().st_size
    summary["returned_mb"] = round(returned / (1 << 20), 2)
    (out / "overlap_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("documents_all", "qualifying_pairs_by_rule", "stage_seconds",
                                               "wall_seconds", "peak_rss_mb", "returned_mb")}, indent=1))
    if returned > cfg["max_output_mb"] * (1 << 20):
        summary["status"] = "failed_output_limit"
        (out / "overlap_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        sys.exit(f"ERROR: returned files are {summary['returned_mb']} MB, over max_output_mb {cfg['max_output_mb']}")


if __name__ == "__main__":
    sys.exit(main())
