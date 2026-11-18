"""Deterministic staging for the E1 code-RL run from the reproduced RL data v1 code_contests file.

    python stage_e1.py <cc.jsonl> <qwen tokenizer.json> <out dir> [--train 192] [--heldout 96]

Same rule as the 15 Nov pilot (wp5_20261115/stage_pilot.py): statement <= 768 Qwen2.5-Coder tokens; held-out when
sha256("g10-wp5-split:" + id) % 10 == 0, else train; both ordered by that hash. The pilot's 64 train candidates and
48 held-out prompts are therefore the first 64 and first 48 of these lists. Held-out is never pass-rate filtered.
Writes private data files (records with tests: never committed) and a metadata summary with hashes only.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer

SOURCE_SHA256 = "91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("tokenizer", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--train", type=int, default=192)
    ap.add_argument("--heldout", type=int, default=96)
    a = ap.parse_args()
    if hashlib.sha256(a.source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise SystemExit("source file is not RL data v1 code_contests (sha256 mismatch)")
    tok = Tokenizer.from_file(str(a.tokenizer))
    rows = [json.loads(line) for line in open(a.source, encoding="utf-8")]
    h = lambda i: hashlib.sha256(f"g10-wp5-split:{i}".encode()).hexdigest()  # noqa: E731
    lens = [len(e.ids) for e in tok.encode_batch([r["statement"] for r in rows])]
    elig = [r for r, n in zip(rows, lens) if n <= 768]
    train = sorted((r for r in elig if int(h(r["id"]), 16) % 10), key=lambda r: h(r["id"]))
    held = sorted((r for r in elig if int(h(r["id"]), 16) % 10 == 0), key=lambda r: h(r["id"]))
    tr, ho = train[:a.train], held[:a.heldout]
    assert not {r["id"] for r in tr} & {r["id"] for r in ho}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "tasks.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in tr + ho))
    (a.out / "train_ids.txt").write_text("".join(r["id"] + "\n" for r in tr))
    (a.out / "heldout_ids.txt").write_text("".join(r["id"] + "\n" for r in ho))
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    meta = {"source_sha256": SOURCE_SHA256, "v1_rows": len(rows), "eligible_le_768_tokens": len(elig),
            "train_pool": len(train), "heldout_pool": len(held), "train_candidates": len(tr), "heldout": len(ho),
            "train_by_judge": dict(collections.Counter(r["judge"] for r in tr)),
            "heldout_by_judge": dict(collections.Counter(r["judge"] for r in ho)),
            "generators": dict(collections.Counter(str(r.get("generator")) for r in tr + ho)),
            "licences": dict(collections.Counter(str(r.get("licence")) for r in tr + ho)),
            "first64_train_ids_sha256": hashlib.sha256("".join(r["id"] + "\n" for r in tr[:64]).encode()).hexdigest(),
            "first48_heldout_ids_sha256": hashlib.sha256("".join(r["id"] + "\n" for r in ho[:48]).encode()).hexdigest(),
            "files_sha256": {p.name: sha(p) for p in sorted(a.out.iterdir()) if p.suffix in (".jsonl", ".txt")}}
    (a.out / "staging.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
