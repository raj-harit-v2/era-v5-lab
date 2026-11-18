"""Length-bucketed SFT slice of the firewalled OCR-2 pack for a 2,048-token Team 5 model, in two forms of the same rows.

    python capstone/sft_slice_v1.py --packs <shard-00000>/pack.firewalled.jsonl ... --tokenizer tokenizer.json \
        --byte-table raw_table_P32.npz --max-tokens 2048 --out DIR

Input: firewalled OCR-2 pack shards (`sft/eval_firewall.py apply` output; the training pack TSAI stores from the pack
job). Each file's sha256 must equal the measured value in `sft/results/ocr2_eval_firewall_v1.json` (`applied_locally`),
so only shards whose firewalled bytes were measured (0-3) are accepted, and any other file is refused before it is read.

For each row (pack fields `id`, `text`, `train_spans`, `input_ids`, `loss_mask`, `effort`):
* length first, from the raw line (count of ids, no JSON parse): rows over --max-tokens are counted and dropped, never
  cut. Only rows that fit are parsed (about one in five), which is what keeps a 600 MB shard to seconds;
* the row is re-tokenised with the run's tokenizer and KE2 table (`sft_rows.Retok`): the ids and the mask must equal
  the pack's, else the row is dropped as `retok_mismatch` (a different tokenizer or table shows up here, not in training);
* A4 form: the assistant's reasoning block (`<|think|>` ... `<|/think|>` and the newline after it) is deleted, the rest of
  the text is unchanged (a deletion of admitted text, the E9 A4 rule), the mask is rebuilt by `convert.train_spans`. A row
  with no reasoning block or no code fence after it is dropped from BOTH forms, so the two arms train on the same rows;
* split: dev if sha256("g10-q3-dev-v1" NUL statement)[0] % 20 == 0, where statement = the user turn's text. The system
  turn is left out because it names the effort tier, which differs between completions of one problem; so every
  completion of a problem lands on the same side. Near-duplicate statements across problems are not clustered here
  (the pack's own held-out split is separate and is not read);
* bucket: (0, 512], (512, 1024], (1024, max] by the A2 row's token count. Nothing is resampled: the slice keeps the
  pack's own length mix inside the limit and reports it per bucket.

Writes `a2_train.jsonl` (full reasoning traces), `a4_train.jsonl` (same rows, reasoning deleted), `dev.jsonl` (A2 form,
split "eval", at most --dev-rows, chosen by digest order) and `slice.json` (counts, tokens, buckets, sha256; no row text).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM10 = HERE.parent
sys.path.insert(0, str(HERE))
FIREWALL_RECORD = TEAM10 / "sft" / "results" / "ocr2_eval_firewall_v1.json"
DEV_SALT = b"g10-q3-dev-v1\0"
BUCKETS = (512, 1024)


def expected_pack_hashes(record: Path = FIREWALL_RECORD) -> dict[str, str]:
    """sha256 -> shard id for every firewalled shard whose bytes were measured."""
    d = json.loads(record.read_text(encoding="utf-8"))
    return {v["firewalled_pack_sha256"]: k for k, v in d["applied_locally"].items()}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def n_ids_raw(line: str) -> int:
    """Number of input ids from the raw JSON line without parsing it (ids are ints: commas + 1)."""
    a = line.index('"input_ids": [') + 14
    b = line.index("]", a)
    return 0 if b == a else line.count(",", a, b) + 1


def bucket_of(n: int) -> str:
    lo = 0
    for hi in BUCKETS:
        if n <= hi:
            return f"{lo + 1}-{hi}"
        lo = hi
    return f"{lo + 1}-max"


def user_turn(text: str, T: dict) -> str:
    head = T["im_start"] + "user\n"
    a = text.index(head) + len(head)
    return text[a: text.index(T["im_end"], a)]


def dev_digest(statement: str) -> bytes:
    return hashlib.sha256(DEV_SALT + statement.encode("utf-8")).digest()


def strip_reasoning(text: str, T: dict) -> str | None:
    """Delete the first <|think|> ... <|/think|> block (and one newline after it); None if absent or no code after."""
    a, b = text.find(T["think"]), text.find(T["think_end"])
    if a < 0 or b < a:
        return None
    end = b + len(T["think_end"])
    if text[end:end + 1] == "\n":
        end += 1
    new = text[:a] + text[end:]
    return new if "```" in new[a:] else None


def build(packs: list[Path], tokenizer: Path, table: Path, max_tokens: int, out: Path, dev_rows: int = 256,
          check_hashes: bool = True, record: Path = FIREWALL_RECORD) -> dict:
    import sft_rows  # noqa: PLC0415
    t0 = time.perf_counter()
    out.mkdir(parents=True, exist_ok=True)
    known = expected_pack_hashes(record) if check_hashes else {}
    inputs = []
    for p in packs:
        h = sha256_file(p)
        if check_hashes and h not in known:
            raise ValueError(f"{p.name}: sha256 {h} is not a measured firewalled shard in {record.name}")
        inputs.append({"file": p.name, "shard": known.get(h), "sha256": h, "bytes": p.stat().st_size})
    t_hash = time.perf_counter() - t0
    rt = sft_rows.Retok(tokenizer, table)
    T = rt.convert.render.T
    stats: dict[str, int] = {}
    train, dev = [], []
    for p in packs:
        with open(p, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                stats["rows_read"] = stats.get("rows_read", 0) + 1
                if n_ids_raw(line) > max_tokens:
                    stats["over_max_tokens"] = stats.get("over_max_tokens", 0) + 1
                    continue
                r = json.loads(line)
                row, why = rt.row(r)
                if row is None or row["input_ids"] != r["input_ids"] or row["loss_mask"] != r["loss_mask"]:
                    stats["retok_mismatch" if row is not None else why] = stats.get(
                        "retok_mismatch" if row is not None else why, 0) + 1
                    continue
                short = strip_reasoning(r["text"], T)
                if short is None:
                    stats["no_reasoning_block_or_code"] = stats.get("no_reasoning_block_or_code", 0) + 1
                    continue
                a4, why4 = rt.row({"id": r["id"], "text": short, "train_spans": rt.convert.train_spans(short)})
                if a4 is None:
                    stats["a4_" + why4] = stats.get("a4_" + why4, 0) + 1
                    continue
                d = dev_digest(user_turn(r["text"], T))
                rec = {"a2": row, "a4": a4, "digest": d.hex(), "effort": r.get("effort"),
                       "bucket": bucket_of(row["n_tokens"])}
                (dev if d[0] % 20 == 0 else train).append(rec)
    t_scan = time.perf_counter() - t0 - t_hash
    train.sort(key=lambda x: x["a2"]["id"])
    dev.sort(key=lambda x: x["digest"])
    dev_dropped = max(0, len(dev) - dev_rows)
    dev = dev[:dev_rows]

    def write(name: str, rows: list[dict], form: str, split: str) -> dict:
        blob = "".join(json.dumps({**x[form], "split": split}) + "\n" for x in rows).encode("utf-8")
        (out / name).write_bytes(blob)
        return {"rows": len(rows), "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
                "tokens": sum(x[form]["n_tokens"] for x in rows), "trained_tokens": sum(x[form]["n_trained"] for x in rows)}

    files = {"a2_train.jsonl": write("a2_train.jsonl", train, "a2", "train"),
             "a4_train.jsonl": write("a4_train.jsonl", train, "a4", "train"),
             "dev.jsonl": write("dev.jsonl", dev, "a2", "eval")}

    def by(rows, key):
        c: dict[str, int] = {}
        for x in rows:
            c[str(x[key])] = c.get(str(x[key]), 0) + 1
        return dict(sorted(c.items()))

    def tok_q(rows, form):
        v = sorted(x[form]["n_tokens"] for x in rows)
        return [v[int(q * (len(v) - 1))] for q in (0.5, 0.9, 0.99)] if v else []

    summary = {"schema": "g10-sft-slice/1", "max_tokens": max_tokens, "inputs": inputs, "stats": stats,
               "train_rows": len(train), "dev_rows": len(dev), "dev_rows_not_used": dev_dropped,
               "train_buckets": by(train, "bucket"), "dev_buckets": by(dev, "bucket"), "train_effort": by(train, "effort"),
               "tokens_p50_p90_p99": {"a2": tok_q(train, "a2"), "a4": tok_q(train, "a4")}, "files": files,
               "tokenizer_sha256": sha256_file(tokenizer),
               "seconds": {"hash_inputs": round(t_hash, 1), "scan": round(t_scan, 1),
                           "total": round(time.perf_counter() - t0, 1)}}
    (out / "slice.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--packs", type=Path, nargs="+", required=True)
    p.add_argument("--tokenizer", type=Path, required=True)
    p.add_argument("--byte-table", type=Path, required=True)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--dev-rows", type=int, default=256)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    s = build(a.packs, a.tokenizer, a.byte_table, a.max_tokens, a.out, a.dev_rows)
    print(json.dumps({k: s[k] for k in ("train_rows", "dev_rows", "stats", "train_buckets", "seconds")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
