"""Re-tokenise G10 chat-format SFT rows with the frozen tokenizer for a Team 5 model: ids, assistant-only loss mask.

Input rows are G10 converter output (`sft/convert.py` parts or OCR-2 pack files): `id`, `text` (chat-format v0 as
rendered), `train_spans` (character spans that are trained). For each row:

* ids = frozen tokenizer encode(text) (markers are added tokens, so each is one id);
* loss_mask = `convert.token_mask(train_spans, offsets)` (the converter's own rule: a token is trained only if it lies
  wholly inside a span);
* the row is kept only if the KE2 raw table reproduces `text` byte for byte from the ids (Team 5's
  `Artifacts.encode` refuses anything else) and at least one token is trained;
* `prompt_len` = index of the first trained token (the generation prefix ends with `<|im_start|>assistant\\n`);
* `split` comes from the id hash: Dolly rows in the pre-training half (see build_pretrain_text.dolly_half) are
  refused; of the rest, `sha256(id)[1] % 10 == 0` is "eval", otherwise "train".

Length is recorded, never cut: rows longer than `--max-tokens` are counted and dropped, not truncated.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def split_of(row_id: str) -> str | None:
    d = hashlib.sha256(row_id.encode()).digest()
    if row_id.startswith("sft-dolly-15k/") and (d[0] & 1) == 0:
        return None  # pre-training half of Dolly (build_pretrain_text.dolly_half == 0)
    return "eval" if d[1] % 10 == 0 else "train"


def read_rows(paths: list[Path]):
    for p in paths:
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


class Retok:
    def __init__(self, tokenizer: Path, table: Path):
        self.convert = _load("g10_convert_for_capstone", HERE.parent / "sft" / "convert.py")
        self.tok = Tokenizer.from_file(str(tokenizer))
        self.tok.no_padding()
        self.tok.no_truncation()
        with np.load(table, allow_pickle=False) as z:
            self.rows, self.lengths = z["bytes"].copy(), z["lengths"].copy()

    def row(self, r: dict) -> tuple[dict | None, str]:
        enc = self.tok.encode(r["text"], add_special_tokens=False)
        raw = b"".join(self.rows[i, : int(self.lengths[i])].tobytes() for i in enc.ids)
        if raw != r["text"].encode("utf-8"):
            return None, "no_exact_roundtrip"
        mask = self.convert.token_mask([tuple(s) for s in r["train_spans"]], enc.offsets)
        if not any(mask):
            return None, "empty_mask"
        first = mask.index(1)
        return {"id": r["id"], "input_ids": list(enc.ids), "loss_mask": list(mask), "prompt_len": first,
                "n_tokens": len(enc.ids), "n_trained": int(sum(mask))}, "ok"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rows", type=Path, nargs="+", required=True)
    p.add_argument("--tokenizer", type=Path, required=True)
    p.add_argument("--byte-table", type=Path, required=True)
    p.add_argument("--max-tokens", type=int, required=True)
    p.add_argument("--limit", type=int, default=0, help="stop after this many input rows (0 = all)")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    rt = Retok(a.tokenizer, a.byte_table)
    stats: dict[str, int] = {}
    lengths = []
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        for n, r in enumerate(read_rows(a.rows)):
            if a.limit and n >= a.limit:
                break
            split = split_of(r["id"])
            if split is None:
                stats["pretrain_half_refused"] = stats.get("pretrain_half_refused", 0) + 1
                continue
            row, why = rt.row(r)
            if row is not None:
                lengths.append(row["n_tokens"])
                if row["n_tokens"] > a.max_tokens:
                    why, row = "over_max_tokens", None
            stats[why] = stats.get(why, 0) + 1
            if row is not None:
                row["split"] = split
                stats["kept_" + split] = stats.get("kept_" + split, 0) + 1
                f.write(json.dumps(row) + "\n")
    q = np.percentile(lengths, [50, 90, 99]).tolist() if lengths else []
    summary = {"stats": stats, "tokens_p50_p90_p99": q, "max_tokens": a.max_tokens,
               "share_within": {str(c): float(np.mean(np.array(lengths) <= c)) if lengths else None
                                for c in (256, 1024, 2048, 4096, 32768)},
               "tokenizer_sha256": hashlib.sha256(a.tokenizer.read_bytes()).hexdigest(),
               "out_sha256": hashlib.sha256(a.out.read_bytes()).hexdigest()}
    a.out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
