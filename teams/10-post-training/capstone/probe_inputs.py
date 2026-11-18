"""Build the day-one probe's SFT rows from the public Dolly-15k file with the run's own tokenizer (no private inputs).

    python capstone/probe_inputs.py --dolly databricks-dolly-15k.jsonl --tokenizer tokenizer.json \
        --byte-table raw_table_P32.npz --max-tokens 256 --out-dir <dir>

Same rows as the rehearsal's hand-built files, made in one pass so the probe needs nothing that is not public:

* row i of `databricks-dolly-15k.jsonl` gets id `sft-dolly-15k/i` and is rendered by `sft/convert.py` (`dolly`
  adapter, `convert_row`: G10 chat format v0, assistant body plus `<|im_end|>` trained);
* `sft_rows.py` keeps the SFT half (the pre-training half is refused by id hash), re-tokenises with the given
  tokenizer, checks the byte table reproduces the text, applies the assistant-only mask and drops rows over
  `--max-tokens` (never truncates);
* rows go to `sft_train.jsonl` / `sft_eval.jsonl` by the same id hash, in file order, one `json.dumps` line each.

With the p1536 tokenizer and table this reproduces the rehearsal files byte for byte (sha256 c273a4d7... and
f77fc96c...); with the run's tokenizer it gives that run's ids. The text does not depend on the tokenizer (Dolly has
no reasoning trace, so the effort tier is fixed). Writes only to --out-dir. Network: none.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import sft_rows

DOLLY_SET = "sft-dolly-15k"


def _no_trace_count(segment: str) -> int:
    raise AssertionError("Dolly rows have no reasoning trace; the effort tier needs no token count")


def build_dolly(dolly: Path, tokenizer: Path, table: Path, max_tokens: int, out_dir: Path) -> dict:
    rt = sft_rows.Retok(tokenizer, table)
    convert = rt.convert
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"train": out_dir / "sft_train.jsonl", "eval": out_dir / "sft_eval.jsonl"}
    stats: dict[str, int] = {}
    files = {k: p.open("w", encoding="utf-8") for k, p in paths.items()}
    try:
        with dolly.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                row_id = f"{DOLLY_SET}/{i}"
                split = sft_rows.split_of(row_id)
                if split is None:
                    stats["pretrain_half_refused"] = stats.get("pretrain_half_refused", 0) + 1
                    continue
                try:
                    _, text, spans = convert.convert_row(convert.dolly(json.loads(line)), _no_trace_count)
                except convert.Skip as exc:
                    key = f"convert_skip: {exc}"
                    stats[key] = stats.get(key, 0) + 1
                    continue
                row, why = rt.row({"id": row_id, "text": text, "train_spans": [list(s) for s in spans]})
                if row is not None and row["n_tokens"] > max_tokens:
                    why, row = "over_max_tokens", None
                stats[why] = stats.get(why, 0) + 1
                if row is not None:
                    row["split"] = split
                    stats["kept_" + split] = stats.get("kept_" + split, 0) + 1
                    files[split].write(json.dumps(row) + "\n")
    finally:
        for fh in files.values():
            fh.close()

    def sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    return {"source": {"file": dolly.name, "sha256": sha(dolly)}, "tokenizer_sha256": sha(tokenizer),
            "byte_table_file_sha256": sha(table), "max_tokens": max_tokens, "stats": stats,
            "files": {k: {"name": p.name, "sha256": sha(p), "bytes": p.stat().st_size} for k, p in paths.items()}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dolly", type=Path, required=True, help="databricks-dolly-15k.jsonl (Hub revision pinned by caller)")
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(build_dolly(a.dolly, a.tokenizer, a.byte_table, a.max_tokens, a.out_dir), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
