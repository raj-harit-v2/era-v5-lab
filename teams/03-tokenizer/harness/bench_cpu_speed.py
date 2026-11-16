#!/usr/bin/env python3
"""
bench_cpu_speed.py
==================

CPU encode throughput for two tokenizer.json files on English / Code / Indic text.

Timing boundary: texts are loaded and UTF-8-encoded into memory before the clock starts.
Only Tokenizer.encode(..., add_special_tokens=False) is timed. Warm-up encodes are
outside the measured window. I/O and Parquet decompression are excluded.

One process, TOKENIZERS_PARALLELISM=false. On Linux, pin with os.sched_setaffinity or
`taskset -c N`. macOS has no user-space CPU affinity API comparable to sched_setaffinity;
this script records that limitation instead of claiming a pin.

    python teams/03-tokenizer/harness/bench_cpu_speed.py \\
        --data-root /path/to/week3data \\
        --c3 /path/to/c3/tokenizer.json \\
        --p1536 /path/to/p1536/tokenizer.json \\
        --results-dir teams/03-tokenizer/results \\
        --target-bytes 1000000000 --runs 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

DOMAINS = ("english", "code", "indic")
TEXT_COL_CANDIDATES = ("text", "content", "document", "body")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_text_column(names):
    for c in TEXT_COL_CANDIDATES:
        if c in names:
            return c
    raise SystemExit(f"no text column among {names}; tried {TEXT_COL_CANDIDATES}")


def list_parquet(domain_dir: Path):
    return sorted(domain_dir.rglob("*.parquet"), key=lambda p: str(p).lower())


def load_domain_texts(domain_dir: Path, target_bytes: int):
    """Deterministic: files sorted by path, rows in file order. Stop once target_bytes reached.
    Never duplicates. If total available < target, use all."""
    import pyarrow.parquet as pq

    files = list_parquet(domain_dir)
    if not files:
        raise SystemExit(f"no parquet under {domain_dir}")

    texts: list[str] = []
    selected = []
    input_bytes = 0
    source_files = []
    text_columns = {}

    for f in files:
        table = pq.read_table(f)
        col = detect_text_column(table.column_names)
        text_columns[str(f)] = col
        source_files.append({
            "path": str(f.resolve()),
            "sha256": sha256_file(f),
            "rows": table.num_rows,
            "text_column": col,
            "parquet_bytes": f.stat().st_size,
        })
        col_data = table[col].to_pylist()
        used = 0
        for i, raw in enumerate(col_data):
            if not isinstance(raw, str) or not raw:
                continue
            b = raw.encode("utf-8")
            if target_bytes > 0 and input_bytes >= target_bytes:
                break
            texts.append(raw)
            input_bytes += len(b)
            used += 1
            selected.append({"file": str(f.resolve()), "row": i, "utf8_bytes": len(b)})
        if target_bytes > 0 and input_bytes >= target_bytes:
            break

    # Hash of the exact UTF-8 stream passed to the tokenizer (length-prefixed records).
    h = hashlib.sha256()
    for t in texts:
        b = t.encode("utf-8")
        h.update(len(b).to_bytes(8, "little"))
        h.update(b)
    return {
        "texts": texts,
        "input_bytes": input_bytes,
        "n_records": len(texts),
        "source_files": source_files,
        "selected_records": len(selected),
        "selected": selected,
        "text_columns": text_columns,
        "benchmark_input_sha256": h.hexdigest(),
        "target_bytes": target_bytes,
        "used_all_available": input_bytes < target_bytes if target_bytes > 0 else True,
    }


def affinity_report():
    info = {
        "os": platform.system(),
        "sched_setaffinity_available": hasattr(os, "sched_setaffinity"),
        "requested": "one CPU core",
        "enforced": False,
        "method": None,
        "cpus": None,
        "limitation": None,
    }
    if hasattr(os, "sched_setaffinity"):
        try:
            os.sched_setaffinity(0, {0})
            info["enforced"] = True
            info["method"] = "os.sched_setaffinity(0, {0})"
            info["cpus"] = sorted(os.sched_getaffinity(0))
        except Exception as e:  # noqa: BLE001
            info["limitation"] = f"sched_setaffinity failed: {type(e).__name__}: {e}"
    else:
        info["limitation"] = (
            f"{platform.system()} provides no os.sched_setaffinity; "
            "TOKENIZERS_PARALLELISM=false and OMP/MKL/OPENBLAS/VECLIB/NUMEXPR threads=1 are set, "
            "but a hard one-core CPU affinity pin could not be verified."
        )
    return info


def load_tokenizer(path: Path):
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(path))


def encode_all(tok, texts: list[str]) -> int:
    n = 0
    for t in texts:
        n += len(tok.encode(t, add_special_tokens=False).ids)
    return n


def median(xs):
    return statistics.median(xs)


def run_measured(tok, texts, runs: int, warmup: int):
    for _ in range(warmup):
        encode_all(tok, texts)
    results = []
    for i in range(runs):
        t0 = time.perf_counter()
        tokens = encode_all(tok, texts)
        elapsed = time.perf_counter() - t0
        results.append({"run": i + 1, "elapsed_s": elapsed, "total_tokens": tokens})
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--c3", type=Path, required=True, help="frozen C3 sample-v0 tokenizer.json")
    ap.add_argument("--p1536", type=Path, required=True, help="p1536 tokenizer.json")
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--target-bytes", type=int, default=1_000_000_000)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--domains", default="english,code,indic")
    ap.add_argument("--smoke-bytes", type=int, default=0,
                    help="if >0, override target-bytes for a short smoke")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--manifest-json", type=Path, default=None)
    ap.add_argument("--log", type=Path, default=None)
    args = ap.parse_args()

    results_dir = args.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_json or (results_dir / "speed_v1.json")
    manifest_json = args.manifest_json or (results_dir / "dataset_manifest.json")
    log_path = args.log or (results_dir / "benchmark_execution.log")

    target = args.smoke_bytes if args.smoke_bytes > 0 else args.target_bytes
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]

    aff = affinity_report()
    tok_paths = {
        "c3_sample_v0": args.c3.resolve(),
        "p1536": args.p1536.resolve(),
    }
    tok_meta = {name: {"path": str(p), "sha256": sha256_file(p)} for name, p in tok_paths.items()}

    log_lines = []
    def log(msg):
        print(msg, flush=True)
        log_lines.append(msg)

    log(f"bench_cpu_speed.py start {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    log(f"python {sys.version.replace(chr(10), ' ')}")
    log(f"platform {platform.platform()} machine={platform.machine()} processor={platform.processor()}")
    log(f"affinity {json.dumps(aff)}")
    log(f"tokenizers {tok_meta}")
    log(f"target_bytes {target} runs {args.runs} warmup {args.warmup}")

    # Load datasets once; both tokenizers see identical lists.
    domain_data = {}
    manifest = {"target_bytes": target, "domains": {}, "notes": [
        "Input size is UTF-8 bytes of the strings passed to Tokenizer.encode.",
        "Selection is deterministic: sorted parquet paths, row order within each file.",
        "No record duplication; if available text < target_bytes, all available text is used.",
    ]}
    for dom in domains:
        ddir = args.data_root / dom
        log(f"loading domain {dom} from {ddir}")
        packed = load_domain_texts(ddir, target)
        domain_data[dom] = packed
        manifest["domains"][dom] = {
            "source_files": packed["source_files"],
            "text_columns": packed["text_columns"],
            "record_count_available_scanned": sum(s["rows"] for s in packed["source_files"]),
            "selected_records": packed["selected_records"],
            "input_utf8_bytes": packed["input_bytes"],
            "benchmark_input_sha256": packed["benchmark_input_sha256"],
            "used_all_available": packed["used_all_available"],
            "target_bytes": target,
        }
        log(f"  records={packed['n_records']} utf8_bytes={packed['input_bytes']} "
            f"sha256={packed['benchmark_input_sha256'][:16]}… used_all={packed['used_all_available']}")

    manifest_json.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    log(f"wrote {manifest_json}")

    tokenizers = {name: load_tokenizer(path) for name, path in tok_paths.items()}
    # Smoke: first 2 texts
    for name, tok in tokenizers.items():
        n = encode_all(tok, domain_data[domains[0]]["texts"][:2])
        log(f"smoke {name}: tokens_on_2_docs={n}")

    matrix = {}
    for dom in domains:
        texts = domain_data[dom]["texts"]
        nbytes = domain_data[dom]["input_bytes"]
        matrix[dom] = {}
        for name, tok in tokenizers.items():
            log(f"=== {dom} / {name} ({args.runs} runs, warmup={args.warmup}) ===")
            runs = run_measured(tok, texts, args.runs, args.warmup)
            for r in runs:
                mb_s = (nbytes / 1_000_000) / r["elapsed_s"]
                tok_s = r["total_tokens"] / r["elapsed_s"]
                tpb = r["total_tokens"] / nbytes if nbytes else float("nan")
                r.update({
                    "input_bytes": nbytes,
                    "mb_per_s": mb_s,
                    "tokens_per_s": tok_s,
                    "tokens_per_byte": tpb,
                })
                log(f"  run {r['run']}: {r['elapsed_s']:.3f}s  {mb_s:.2f} MB/s  "
                    f"{tok_s:.0f} tokens/s  tokens={r['total_tokens']}")
            mb_vals = [r["mb_per_s"] for r in runs]
            tok_vals = [r["tokens_per_s"] for r in runs]
            tpb_vals = [r["tokens_per_byte"] for r in runs]
            # token counts must be identical across runs (deterministic encode)
            tok_counts = {r["total_tokens"] for r in runs}
            if len(tok_counts) != 1:
                raise SystemExit(f"non-deterministic token counts for {dom}/{name}: {tok_counts}")
            matrix[dom][name] = {
                "runs": runs,
                "median_mb_per_s": median(mb_vals),
                "median_tokens_per_s": median(tok_vals),
                "tokens_per_byte": tpb_vals[0],
                "total_tokens": runs[0]["total_tokens"],
                "input_bytes": nbytes,
                "benchmark_input_sha256": domain_data[dom]["benchmark_input_sha256"],
            }
            log(f"  median: {matrix[dom][name]['median_mb_per_s']:.2f} MB/s  "
                f"{matrix[dom][name]['median_tokens_per_s']:.0f} tokens/s")

    from importlib import metadata as importlib_metadata
    try:
        tokenizers_ver = importlib_metadata.version("tokenizers")
    except Exception:  # noqa: BLE001
        tokenizers_ver = None
    try:
        pyarrow_ver = importlib_metadata.version("pyarrow")
    except Exception:  # noqa: BLE001
        pyarrow_ver = None

    payload = {
        "schema": "tokenizer_cpu_speed_v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__)),
        "git_commit": os.environ.get("GIT_COMMIT") or None,
        "machine": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version,
            "tokenizers": tokenizers_ver,
            "pyarrow": pyarrow_ver,
            "cpu_brand": None,
        },
        "affinity": aff,
        "config": {
            "runs": args.runs,
            "warmup": args.warmup,
            "target_bytes": target,
            "add_special_tokens": False,
            "timing": "encode loop only; load/decode/warmup excluded",
        },
        "tokenizers": tok_meta,
        "domains": {
            dom: {
                "input_utf8_bytes": domain_data[dom]["input_bytes"],
                "selected_records": domain_data[dom]["n_records"],
                "benchmark_input_sha256": domain_data[dom]["benchmark_input_sha256"],
                "used_all_available": domain_data[dom]["used_all_available"],
            }
            for dom in domains
        },
        "results": matrix,
    }
    # best-effort CPU brand on macOS
    if platform.system() == "Darwin":
        try:
            import subprocess
            brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
            payload["machine"]["cpu_brand"] = brand
            payload["machine"]["logical_cpus"] = int(
                subprocess.check_output(["sysctl", "-n", "hw.logicalcpu"], text=True).strip()
            )
        except Exception:  # noqa: BLE001
            pass

    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    log(f"wrote {out_json}")
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    log(f"wrote {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
