#!/usr/bin/env python3
"""Load Team 01 (Data A) dataset/shard composition summaries into ClickHouse `shard_composition`.

Supports both JSON (list of rows, or dict with `packs` / `rows` / `shards` list)
and CSV summaries produced by the corpus-v1 clean/shard pipeline.

Usage:
    python load_shard_composition.py --input summary.json --dataset-version corpus-v1 --dry-run
    python load_shard_composition.py --input summary.csv --dataset-version corpus-v1 --url http://127.0.0.1:8123
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
SCHEMA_SQL = HERE / "shard_composition.sql"

# Public-dashboard safety guardrail: never ingest cost or hardware/machine metadata.
FORBIDDEN_KEYS = frozenset({
    "cost",
    "usd",
    "spend",
    "gpu_model",
    "hardware",
    "hostname",
    "machine",
    "node_name",
    "ip_address",
})


def _to_int(val, field: str) -> int:
    if val is None or val == "":
        return 0
    n = int(val)
    if n < 0:
        raise ValueError(f"{field} must be non-negative, got {n}")
    return n


def _to_float(val, field: str) -> float:
    x = float(val)
    if x != x:  # NaN
        raise ValueError(f"{field} must be finite, got NaN")
    return x


def normalize_row(raw: dict, default_version: str = "", default_stage: str = "train") -> dict:
    """Validate and normalize one raw manifest/summary row into `shard_composition` columns."""
    lowered_keys = {k.strip().lower() for k in raw.keys()}
    leaked = sorted(lowered_keys & FORBIDDEN_KEYS)
    if leaked:
        raise ValueError(f"forbidden public-dashboard fields present: {leaked}")

    pack_id = str(raw.get("pack_id") or raw.get("pack") or "").strip()
    if not pack_id:
        raise ValueError("missing required field: pack_id")

    dataset_version = str(raw.get("dataset_version") or default_version).strip()
    if not dataset_version:
        raise ValueError(f"pack {pack_id!r}: missing dataset_version (pass --dataset-version or include column)")

    stage = str(raw.get("stage") or raw.get("split") or default_stage).strip()
    domain = str(raw.get("domain") or raw.get("group") or "unknown").strip()
    language = str(raw.get("language") or raw.get("lang_label") or "unknown").strip()

    docs_in = _to_int(raw.get("docs_in", raw.get("rows_in", raw.get("rows", 0))), "docs_in")
    docs_kept = _to_int(raw.get("docs_kept", raw.get("rows_kept", docs_in)), "docs_kept")
    if docs_in > 0 and docs_kept > docs_in:
        raise ValueError(f"pack {pack_id!r}: docs_kept ({docs_kept}) > docs_in ({docs_in})")

    token_count = _to_int(raw.get("token_count", raw.get("tokens", 0)), "token_count")

    if raw.get("drop_rate_pct") not in (None, ""):
        drop_rate_pct = _to_float(raw["drop_rate_pct"], "drop_rate_pct")
    elif raw.get("drop_rate") not in (None, ""):
        rate = _to_float(raw["drop_rate"], "drop_rate")
        drop_rate_pct = rate * 100.0 if 0.0 <= rate <= 1.0 else rate
    elif docs_in > 0:
        drop_rate_pct = round(((docs_in - docs_kept) / docs_in) * 100.0, 4)
    else:
        drop_rate_pct = 0.0

    if not (0.0 <= drop_rate_pct <= 100.0):
        raise ValueError(f"pack {pack_id!r}: drop_rate_pct out of [0, 100]: {drop_rate_pct}")

    return {
        "dataset_version": dataset_version,
        "stage": stage,
        "pack_id": pack_id,
        "domain": domain,
        "language": language,
        "docs_in": docs_in,
        "docs_kept": docs_kept,
        "token_count": token_count,
        "drop_rate_pct": round(drop_rate_pct, 4),
    }


def parse_file(path: Path, dataset_version: str = "", default_stage: str = "train") -> list[dict]:
    """Read a JSON or CSV shard composition summary into normalized rows."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            raw_rows = list(csv.DictReader(f))
    elif suffix in (".json", ".jsonl"):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        if suffix == ".jsonl":
            raw_rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            payload = json.loads(text)
            if isinstance(payload, list):
                raw_rows = payload
            elif isinstance(payload, dict):
                dataset_version = dataset_version or str(payload.get("dataset_version") or "")
                raw_rows = (
                    payload.get("rows")
                    or payload.get("packs")
                    or payload.get("shards")
                    or []
                )
            else:
                raise ValueError(f"unsupported JSON top-level type: {type(payload).__name__}")
    else:
        raise ValueError(f"unsupported file extension: {suffix!r} (expected .json, .jsonl, or .csv)")

    return [normalize_row(r, default_version=dataset_version, default_stage=default_stage) for r in raw_rows]


def _ch_post(sql: str, data: bytes = b"", url: str = "http://127.0.0.1:8123") -> str:
    endpoint = f"{url.rstrip('/')}/?{urllib.parse.urlencode({'query': sql})}"
    req = urllib.request.Request(endpoint, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def ensure_table(url: str = "http://127.0.0.1:8123") -> None:
    ddl = SCHEMA_SQL.read_text(encoding="utf-8")
    for stmt in ddl.split(";"):
        lines = [ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        cleaned = "\n".join(lines).strip()
        if cleaned:
            _ch_post(cleaned, url=url)


def insert_rows(rows: list[dict], url: str = "http://127.0.0.1:8123") -> int:
    if not rows:
        return 0
    ensure_table(url=url)
    payload = ("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n").encode("utf-8")
    _ch_post("INSERT INTO shard_composition FORMAT JSONEachRow", data=payload, url=url)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load shard composition summary into ClickHouse.")
    ap.add_argument("--input", required=True, type=Path, help="Path to JSON, JSONL, or CSV summary file")
    ap.add_argument("--dataset-version", default="", help="Default dataset_version (e.g. corpus-v1)")
    ap.add_argument("--stage", default="train", help="Default stage/split if omitted in rows")
    ap.add_argument("--url", default="http://127.0.0.1:8123", help="ClickHouse HTTP URL")
    ap.add_argument("--dry-run", action="store_true", help="Validate and print JSONEachRow payload without inserting")
    args = ap.parse_args(argv)

    rows = parse_file(args.input, dataset_version=args.dataset_version, default_stage=args.stage)
    if args.dry_run:
        for r in rows:
            print(json.dumps(r, sort_keys=True))
        return 0

    n = insert_rows(rows, url=args.url)
    print(f"inserted {n} shard_composition rows into {args.url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
