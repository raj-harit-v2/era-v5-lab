#!/usr/bin/env python3
"""
fetch_corpus.py
===============

Streams a fixed-size monolingual sample per Brahmic language from FineWeb-2
(HuggingFaceFW/fineweb-2, not gated) into <out>/<lang>.txt for train_bpe.py.

The sample is the first N documents of the first train shard, in file order,
so two runs with the same --mb produce the same bytes. FLORES-200 is the
evaluation set and is never used here.

Usage
-----
    python fetch_corpus.py --out /path/to/corpus --mb 20
    python fetch_corpus.py --out /path/to/corpus --mb 20 --langs Hi,Or

Do not commit the output. pr-guard rejects data files and files over 5 MB.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

# Paper label -> FineWeb-2 config. Same 11 languages as the FLORES benchmark.
LANGS = {
    "Hi": "hin_Deva", "Bn": "ben_Beng", "Ta": "tam_Taml", "Te": "tel_Telu",
    "Kn": "kan_Knda", "Ml": "mal_Mlym", "Mr": "mar_Deva", "Gu": "guj_Gujr",
    "Pa": "pan_Guru", "Or": "ory_Orya", "As": "asm_Beng",
}


def fetch(lang, config, out_dir, budget):
    from datasets import load_dataset

    path = out_dir / f"{lang}.txt"
    ds = load_dataset("HuggingFaceFW/fineweb-2", name=config, split="train", streaming=True)
    h = hashlib.sha256()
    n_docs = n_bytes = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in ds:
            text = row["text"].strip()
            if not text:
                continue
            chunk = text + "\n"
            f.write(chunk)
            b = chunk.encode("utf-8")
            h.update(b)
            n_docs += 1
            n_bytes += len(b)
            if n_bytes >= budget:
                break
    return {"config": config, "file": path.name, "docs": n_docs, "bytes": n_bytes, "sha256": h.hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="output directory (outside the repo)")
    ap.add_argument("--mb", type=float, default=20, help="UTF-8 megabytes per language (default 20)")
    ap.add_argument("--langs", default="all", help='"all" or comma list of labels, e.g. "Hi,Or"')
    args = ap.parse_args()

    langs = list(LANGS) if args.langs == "all" else [s.strip() for s in args.langs.split(",")]
    bad = [lang for lang in langs if lang not in LANGS]
    if bad:
        sys.exit(f"ERROR: unknown languages {bad}. Available: {list(LANGS)}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    budget = int(args.mb * 1_000_000)
    manifest_path = out_dir / "corpus_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for lang in langs:
        t0 = time.time()
        manifest[lang] = fetch(lang, LANGS[lang], out_dir, budget)
        m = manifest[lang]
        print(f"{lang} ({m['config']}): {m['docs']} docs, {m['bytes'] / 1e6:.1f} MB, "
              f"sha256 {m['sha256'][:12]}  ({time.time() - t0:.0f}s)", flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
