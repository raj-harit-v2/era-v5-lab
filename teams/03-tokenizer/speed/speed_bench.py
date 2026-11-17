#!/usr/bin/env python3
"""
speed_bench.py
==============

Encode throughput (MB/s and tokens/s) of one or more tokenizer.json files on a
FineWeb-2 corpus from train/fetch_corpus.py. FLORES and benchmark text are
never used.

Modes (--modes, comma list). A mode is a layout, plus "_fast" for encode_batch_fast:
  single     1 process x 1 thread  (one CPU core)
  batch      1 process x all cores (Rayon threads inside tokenizers)
  procs      --procs processes x --proc-threads threads (default: one process per
             core, 1 thread each), each on its own share of the documents, as a
             tokenizing job that gives each process its own shard
  *_fast     the same layout with encode_batch_fast: same ids, no character offsets

Every mode encodes in chunks of --chunk documents per call (default 256, as
teams/01-data-a/shards/shard_writer.py does), with add_special_tokens=False.

How a run is timed:
  - each worker process sets RAYON_NUM_THREADS before it imports tokenizers;
  - every worker reads the corpus into memory and checks it against
    corpus_manifest.json before the clock starts; worker k keeps documents k, k+P, ...
    of each language (P = number of processes);
  - documents are rebuilt by grouping lines up to the language's mean document
    size (fetch_corpus.py writes one document as one or more lines);
  - one warm-up call per worker, then --repeats timed passes; for each language
    all workers start together at a barrier, and the time ends when the last
    worker is done; the median pass is reported.
--check-ids encodes the whole corpus with encode_batch and encode_batch_fast and
fails if any document gets different ids.

Only numbers are written. No corpus text goes into the output.

Usage
-----
    python speed_bench.py --corpus /path/to/corpus \
        --tok p1536=/path/to/p1536/tokenizer.json \
        --tok brahmic=/path/to/BrahmicTokenizer-131K/tokenizer.json \
        --modes single,batch,single_fast,batch_fast,procs_fast --check-ids \
        --out speed_results.json
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import statistics
import sys
import time
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_docs(corpus, manifest, part=0, parts=1):
    """Return {lang: (docs, n_bytes)} for share `part` of `parts`; docs rebuilt to the mean doc size."""
    out = {}
    for lang, m in manifest.items():
        target = max(1, m["bytes"] // max(1, m["docs"]))
        raw = (corpus / m["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != m["sha256"]:
            raise SystemExit(f"ERROR: {m['file']} does not match corpus_manifest.json")
        docs, buf, size = [], [], 0
        for line in raw.decode("utf-8").splitlines(keepends=True):
            buf.append(line)
            size += len(line.encode("utf-8"))
            if size >= target:
                docs.append("".join(buf))
                buf, size = [], 0
        if buf:
            docs.append("".join(buf))
        docs = docs[part::parts]
        out[lang] = (docs, sum(len(d.encode("utf-8")) for d in docs))
    return out


def worker(k, nproc, threads, corpus, tok_path, api, chunk, repeats, barrier, results):
    os.environ["RAYON_NUM_THREADS"] = str(threads)
    os.environ["TOKENIZERS_PARALLELISM"] = "true"
    from tokenizers import Tokenizer

    corpus = Path(corpus)
    manifest = json.loads((corpus / "corpus_manifest.json").read_text())
    data = load_docs(corpus, manifest, k, nproc)
    tok = Tokenizer.from_file(tok_path)
    encode = tok.encode_batch_fast if api == "fast" else tok.encode_batch
    langs = list(data)
    encode(data[langs[0]][0][:chunk], add_special_tokens=False)  # warm-up
    for _ in range(repeats):
        for lang in langs:
            docs, n_bytes = data[lang]
            barrier.wait()
            n_tok = 0
            for i in range(0, len(docs), chunk):
                n_tok += sum(len(e.ids) for e in encode(docs[i:i + chunk], add_special_tokens=False))
            results.put((lang, n_tok, n_bytes, len(docs)))


def run_mode(corpus, manifest, tok_path, api, nproc, threads, chunk, repeats):
    ctx = mp.get_context("spawn")
    barrier, results = ctx.Barrier(nproc + 1), ctx.Queue()
    procs = [ctx.Process(target=worker, args=(k, nproc, threads, str(corpus), tok_path, api, chunk,
                                              repeats, barrier, results)) for k in range(nproc)]
    for p in procs:
        p.start()
    langs = list(manifest)
    passes = []
    for _ in range(repeats):
        res = {}
        for lang in langs:
            barrier.wait()
            t0 = time.perf_counter()
            got = [results.get() for _ in range(nproc)]
            dt = time.perf_counter() - t0
            res[lang] = (dt, sum(g[1] for g in got), sum(g[2] for g in got), sum(g[3] for g in got))
        passes.append(res)
    for p in procs:
        p.join()
        if p.exitcode:
            raise SystemExit(f"worker failed with exit code {p.exitcode}")

    per_lang = {}
    for lang in langs:
        times = [p[lang][0] for p in passes]
        dt = statistics.median(times)
        _, n_tok, n_bytes, n_docs = passes[0][lang]
        per_lang[lang] = {
            "bytes": n_bytes, "docs": n_docs, "tokens": n_tok,
            "seconds_median": round(dt, 4), "seconds_all": [round(t, 4) for t in times],
            "mb_per_s": round(n_bytes / 1e6 / dt, 3), "tokens_per_s": round(n_tok / dt, 1),
        }
    totals = [sum(p[lang][0] for lang in langs) for p in passes]
    dt = statistics.median(totals)
    n_bytes = sum(v["bytes"] for v in per_lang.values())
    n_tok = sum(v["tokens"] for v in per_lang.values())
    return {"processes": nproc, "threads_per_process": threads, "chunk": chunk, "api": api,
            "per_lang": per_lang,
            "total": {"bytes": n_bytes, "tokens": n_tok, "seconds_median": round(dt, 4),
                      "seconds_all": [round(t, 4) for t in totals],
                      "mb_per_s": round(n_bytes / 1e6 / dt, 3), "tokens_per_s": round(n_tok / dt, 1)}}


def check_ids(corpus, manifest, path, chunk):
    """True if encode_batch_fast gives the same ids as encode_batch for every document."""
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(path)
    for docs, _ in load_docs(corpus, manifest).values():
        for i in range(0, len(docs), chunk):
            part = docs[i:i + chunk]
            a = tok.encode_batch(part, add_special_tokens=False)
            b = tok.encode_batch_fast(part, add_special_tokens=False)
            if any(x.ids != y.ids for x, y in zip(a, b)):
                return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", required=True, help="fetch_corpus.py output folder")
    ap.add_argument("--tok", action="append", default=[], help="name=path/to/tokenizer.json (repeat)")
    ap.add_argument("--modes", default="single,batch,single_fast,batch_fast,procs_fast")
    ap.add_argument("--procs", type=int, default=0, help="processes in procs mode (0 = one per core)")
    ap.add_argument("--proc-threads", type=int, default=1, help="threads per process in procs mode")
    ap.add_argument("--chunk", type=int, default=256, help="documents per encode call")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--check-ids", action="store_true", help="check encode_batch_fast ids == encode_batch ids")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import tokenizers
    cores = os.cpu_count()
    corpus = Path(args.corpus)
    manifest = json.loads((corpus / "corpus_manifest.json").read_text())
    layouts = {"single": (1, 1), "batch": (1, cores), "procs": (args.procs or cores, args.proc_threads)}
    result = {
        "corpus": {lang: {k: m[k] for k in ("config", "docs", "bytes", "sha256")} for lang, m in manifest.items()},
        "env": {"python": platform.python_version(), "tokenizers": tokenizers.__version__,
                "machine": platform.machine(), "platform": platform.platform(),
                "cpu_count": cores, "repeats": args.repeats, "chunk": args.chunk},
        "runs": {},
    }
    for spec in args.tok:
        name, path = spec.split("=", 1)
        result["runs"][name] = {"tokenizer_sha256": sha256_file(path)}
        for mode in args.modes.split(","):
            layout, _, fast = mode.partition("_")
            nproc, threads = layouts[layout]
            t0 = time.time()
            run = run_mode(corpus, manifest, path, "fast" if fast else "plain", nproc, threads,
                           args.chunk, args.repeats)
            result["runs"][name][mode] = run
            t = run["total"]
            print(f"{name:10s} {mode:12s} {nproc:2d}p x {threads:2d}t {t['mb_per_s']:9.2f} MB/s "
                  f"{t['tokens_per_s']:14,.0f} tok/s ({time.time() - t0:.0f}s wall)", flush=True)
        if args.check_ids:
            ok = check_ids(corpus, manifest, path, args.chunk)
            result["runs"][name]["fast_ids_equal"] = ok
            print(f"{name:10s} encode_batch_fast ids equal: {ok}", flush=True)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
