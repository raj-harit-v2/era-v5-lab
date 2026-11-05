"""Check documents against the benchmark fingerprints (G9).

    python decontam_check.py pack.parquet                 # Parquet with doc_id and text columns
    python decontam_check.py docs.jsonl --id-field id     # one JSON object per line
    python decontam_check.py a.txt b.txt                  # plain text files
    python decontam_check.py pack.parquet --benchmarks mmlu gsm8k
    python decontam_check.py heldout_v1.jsonl --id-field id --exclude heldout_g5_v1   # a protected set itself

A document is flagged when it shares at least --min-hits n-grams with one benchmark item.
The script writes one JSON line per flagged document (use --all for every document)
and a summary on stderr. It gives the benchmark item and the character offset of the
first match, for example "gsm8k:test:120 at offset 64". It never prints document text.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from fpset import VERSION, Fingerprints

DEFAULT_SET = Path(__file__).resolve().parent.parent / "fingerprints" / VERSION


def read_docs(paths, id_field, text_field):
    for p in paths:
        p = Path(p)
        if p.suffix == ".parquet":
            import pyarrow.parquet as pq
            t = pq.read_table(p, columns=[id_field, text_field])
            for doc_id, text in zip(t.column(id_field).to_pylist(), t.column(text_field).to_pylist()):
                yield str(doc_id), text or ""
        elif p.suffix == ".jsonl":
            with open(p, encoding="utf-8") as f:
                for n, line in enumerate(f):
                    if line.strip():
                        r = json.loads(line)
                        yield str(r.get(id_field, f"{p.name}:{n}")), r.get(text_field) or ""
        else:
            yield p.name, p.read_text(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--fingerprints", default=str(DEFAULT_SET), help="fingerprint set folder")
    ap.add_argument("--benchmarks", nargs="+", metavar="ID", help="check only these benchmarks (default: all)")
    ap.add_argument("--tags", nargs="+", metavar="TAG",
                    help="check only benchmarks with one of these tags, for example code or indic. "
                         "Only the full set (no --benchmarks, no --tags) is the formal check.")
    ap.add_argument("--exclude", nargs="+", metavar="ID",
                    help="leave out these benchmarks. Only to check a protected set (for example the G5 held-out "
                         "file, without heldout_g5_v1) against all the others.")
    ap.add_argument("--id-field", default="doc_id")
    ap.add_argument("--text-field", default="text")
    ap.add_argument("--min-hits", type=int, default=1, help="n-grams shared with one item to flag (default 1)")
    ap.add_argument("--max-items", type=int, default=5, help="benchmark items to list per document")
    ap.add_argument("--all", action="store_true", help="write a line for every document, not only flagged ones")
    args = ap.parse_args()

    fp = Fingerprints(args.fingerprints, args.benchmarks, tags=args.tags, exclude=args.exclude)
    if args.benchmarks or args.tags:
        scope = f"PARTIAL: {' '.join(fp.benchmarks)}"
    elif args.exclude:
        scope = f"full set except {' '.join(sorted(args.exclude))}"
    else:
        scope = "full set"
    print(f"fingerprints {fp.manifest['version']} set_sha256 {fp.set_sha256} ({scope})", file=sys.stderr)
    n_docs = n_flagged = 0
    per_bench = Counter()
    for doc_id, text in read_docs(args.inputs, args.id_field, args.text_field):
        flagged, hits = fp.check(text, args.min_hits)
        n_docs += 1
        if flagged:
            n_flagged += 1
            per_bench.update({h["item"].split(":")[0] for h in hits
                              if h.get("canary") or h["grams"] >= args.min_hits})
        if flagged or args.all:
            print(json.dumps({"doc_id": doc_id, "flagged": flagged, "n_items": len(hits),
                              "hits": hits[:args.max_items]}, ensure_ascii=False))
    rate = n_flagged / n_docs if n_docs else 0.0
    print(f"docs {n_docs} flagged {n_flagged} ({rate:.2%}) by benchmark {dict(per_bench)}", file=sys.stderr)


if __name__ == "__main__":
    main()
