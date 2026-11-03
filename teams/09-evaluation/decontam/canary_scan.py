"""Scan documents for canary strings (G9).

    python canary_scan.py shard.parquet                      # Parquet with doc_id and text columns
    python canary_scan.py docs.jsonl --id-field id            # one JSON object per line
    python canary_scan.py some/folder                         # every .parquet .jsonl .json .txt .md below it
    python canary_scan.py shard.parquet --canary "my string"  # also look for an extra string
    python canary_scan.py shard.parquet --lab-only            # only the lab canary, no fingerprint set needed

It looks for the lab canary (lab_canary.py) and for every benchmark canary in the fingerprint set
(benchmarks with canaries in MANIFEST.json: GPQA, HLE). A match is exact: one occurrence is a leak.
It does not load the fingerprints, so it is fast. The full check is still decontam_check.py.

What is scanned:
  .parquet  the --text-field column (the file must have it, and the --id-field column)
  .jsonl    the --text-field value of each line; a line without it (or not a JSON object) is scanned
            whole, as raw text. So eval files like run_lm_eval.py samples_<n>.jsonl are covered.
  others    the whole file as text. The document ID is the path (relative to a scanned folder).

Output: one JSON line per occurrence, with only the canary, the document ID and the offset
(character offset in the scanned text). It never prints document text. The summary goes to stderr.
Exit code: 1 if a canary was found; else 2 if a file could not be read (the scan is incomplete); else 0.
"""

import argparse
import json
import sys
from pathlib import Path

from decontam_check import DEFAULT_SET
from lab_canary import find, load_canaries

SUFFIXES = {".parquet", ".jsonl", ".json", ".txt", ".md"}


def expand(inputs):
    """(path, display name): files as given; a folder gives its files with a known suffix, sorted,
    named by their path relative to the folder."""
    for p in map(Path, inputs):
        if p.is_dir():
            for f in sorted(f for f in p.rglob("*") if f.is_file() and f.suffix in SUFFIXES):
                yield f, f.relative_to(p).as_posix()
        else:
            yield p, str(p)


def read_file(path, name, id_field, text_field):
    """Yield (doc_id, text) for one file. Raises on a file it cannot read."""
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq
        t = pq.read_table(path, columns=[id_field, text_field])
        for doc_id, text in zip(t.column(id_field).to_pylist(), t.column(text_field).to_pylist()):
            yield str(doc_id), text or ""
    elif path.suffix == ".jsonl":
        with open(path, encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    r = None
                if isinstance(r, dict) and isinstance(r.get(text_field), str):
                    yield str(r.get(id_field, f"{name}:{n}")), r[text_field]
                else:  # no text field: scan the raw line
                    doc_id = r.get(id_field) if isinstance(r, dict) else None
                    yield str(doc_id if doc_id is not None else f"{name}:{n}"), line
    else:
        yield name, path.read_text(encoding="utf-8", errors="replace")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="Parquet, JSONL or text files, or folders")
    ap.add_argument("--id-field", default="doc_id")
    ap.add_argument("--text-field", default="text")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--fingerprints", default=str(DEFAULT_SET),
                     help="fingerprint set folder for the benchmark canaries (default: the shipped set)")
    src.add_argument("--lab-only", action="store_true", help="look only for the lab canary (and --canary strings)")
    ap.add_argument("--canary", action="append", default=[], metavar="STRING", help="an extra string to look for")
    args = ap.parse_args(argv)
    if any(not c.strip() for c in args.canary):
        ap.error("--canary must not be empty")

    try:
        canaries = load_canaries(None if args.lab_only else args.fingerprints)
    except (OSError, ValueError, KeyError) as e:
        ap.error(f"cannot load the benchmark canaries: {e}. Give --fingerprints <set folder>, or --lab-only.")
    for c in args.canary:
        canaries.setdefault(c, "extra")
    print(f"canaries {len(canaries)} from {', '.join(sorted(set(canaries.values())))}", file=sys.stderr)

    n_docs = n_with = n_hits = n_skipped = 0
    for path, name in expand(args.inputs):
        try:
            for doc_id, text in read_file(path, name, args.id_field, args.text_field):
                n_docs += 1
                hits = find(text, canaries)
                if hits:
                    n_with += 1
                    n_hits += len(hits)
                for offset, c in hits:
                    print(json.dumps({"canary": c, "doc_id": doc_id, "offset": offset}, ensure_ascii=False))
        except Exception as e:  # one bad file must not stop the scan; it is reported and makes the exit code 2
            n_skipped += 1
            print(f"skipped {name}: {type(e).__name__}: {e}", file=sys.stderr)
    print(f"docs {n_docs} with_canary {n_with} hits {n_hits}" + (f" files_skipped {n_skipped}" if n_skipped else ""),
          file=sys.stderr)
    return 1 if n_hits else (2 if n_skipped else 0)


if __name__ == "__main__":
    sys.exit(main())
