#!/usr/bin/env python3
"""Revalidate KE byte tables and collisions for named tokenizer candidates.

The tokenizer files are inputs and are never copied into the repository.  The
committed output is compact: table content hashes and metrics, collision totals,
per-script collision counts, and stable summaries of token IDs whose rows differ
between candidates. Full ``.npz`` tables remain reproducible with ``build_tables.py``.

Usage::

    python revalidate_tokenizer_candidates.py \
      --candidate v0=/path/to/v0/tokenizer.json \
      --candidate v0.1=/path/to/v0.1/tokenizer.json \
      --candidate v1-c1=/path/to/v1-c1/tokenizer.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from collisions import build_collisions as collision_audit

from ke2.config import POS_DIMS, RESULTS_DIR
from ke2.tables import build_decode_table, build_raw_table
from ke2.tokenizer import load_tokenizer, raw_bytes_for_id

EXPECTED_SHA256 = {
    "v0": "2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5",
    "v0.1": "a33c9907ec16876bc57b011714e8380879919fba1327d84bfb0d60407fe6e578",
    "v1-c1": "7d2cff92053170fdb17b301448964f1770d88df247b2e794256254227f86af44",
    "C1": "5d386e2ea359f0137b1a8383d161955894f1e6f634cf3179837b2cb59fe46db9",
    "C2": "84204d7897d6677ac2e8ac7552d7472e5fed2baa3c67d392e40dbbfe63e35ad3",
    "C3": "54f20825f61dd863e9bc15a0ece82fefc2f53b45005e1f71edec2d652a055306",
    "C1-s0": "36acf1264248c0f7ed1e3b18cfef6e4e9f489660d749c1e9c2b79e80901c82a2",
    "C2-s0": "b0d44576012cede10ea197d33251377ee5aac72f246aca954b96a95a20f8488a",
    "C3-s0": "15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3",
}
DEFAULT_OUT = RESULTS_DIR / "tokenizer_candidates"


@dataclass(frozen=True)
class CandidateSpec:
    """A display name, exact tokenizer identity, and local artifact path."""

    name: str
    sha256: str
    path: Path


def dependency_versions() -> dict[str, str | None]:
    """Return runtime provenance without importing the optional upstream codec."""
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for distribution in ("numpy", "tokenizers"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def parse_candidate(value: str) -> CandidateSpec:
    """Parse ``NAME=PATH`` or future-proof ``NAME@SHA256=PATH``."""
    identity, separator, path = value.partition("=")
    if not separator or not identity or not path:
        raise argparse.ArgumentTypeError(
            "candidate must be NAME=/path/to/tokenizer.json or NAME@SHA256=/path/to/tokenizer.json"
        )
    if "@" in identity:
        name, sha256 = identity.rsplit("@", 1)
        if not name or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise argparse.ArgumentTypeError("explicit candidate SHA-256 must be 64 lowercase hex characters")
    else:
        name = identity
        try:
            sha256 = EXPECTED_SHA256[name]
        except KeyError:
            known = ", ".join(EXPECTED_SHA256)
            raise argparse.ArgumentTypeError(
                f"unknown candidate {name!r}; use NAME@SHA256=PATH or one of: {known}"
            ) from None
    return CandidateSpec(name, sha256, Path(path).expanduser())


def table_metrics(table) -> dict[str, object]:
    """Return the public, compact measurements for one in-memory byte table."""
    unique = len({table.row(token_id) for token_id in range(table.vocab_size)})
    return {
        "content_sha256": table.sha256(),
        "shape": list(table.bytes.shape),
        "n_truncated": table.n_truncated,
        "n_empty_rows": table.n_empty_rows,
        "n_rows_containing_U+FFFD": table.n_fffd_rows,
        "n_unique_rows": unique,
        "n_colliding_tokens": table.vocab_size - unique,
    }


def build_candidate(spec: CandidateSpec) -> tuple[object, dict, dict]:
    """Build all tables for one pinned candidate and return its audit payload."""
    tokenizer = load_tokenizer(str(spec.path), expected_sha256=spec.sha256)
    tables = {}
    for pos_dim in POS_DIMS:
        tables["decode", pos_dim] = build_decode_table(tokenizer, pos_dim)
        tables["raw", pos_dim] = build_raw_table(tokenizer, pos_dim)

    audit = collision_audit.audit(tokenizer, tables)
    totals = collision_audit.totals(audit)
    raw_lengths = [len(raw_bytes_for_id(tokenizer, token_id)) for token_id in range(tokenizer.vocab_size)]
    payload = {
        "tokenizer_sha256": tokenizer.sha256,
        "vocab_size": tokenizer.vocab_size,
        "added_tokens": len(tokenizer.added),
        "special_ids": len(tokenizer.special_ids),
        "max_raw_byte_length": max(raw_lengths),
        "mean_raw_byte_length": sum(raw_lengths) / len(raw_lengths),
        "tables": {f"{kind}_P{pos_dim}": table_metrics(tables[kind, pos_dim]) for kind, pos_dim in sorted(tables)},
        "collision_totals": totals,
        "gate_zero_other_collision_groups": all(row["causes"].get("other", 0) == 0 for row in totals.values()),
    }
    return tokenizer, payload, {"audit": audit, "tables": tables}


def changed_token_ids(reference, candidate, kind: str) -> list[int]:
    """Return IDs whose untruncated bytes differ for the requested extraction."""
    if reference.vocab_size != candidate.vocab_size:
        raise ValueError("candidate vocabularies have different sizes")
    extraction = raw_bytes_for_id if kind == "raw" else collision_audit.untruncated_bytes
    if kind == "raw":
        return [
            token_id
            for token_id in range(reference.vocab_size)
            if extraction(reference, token_id) != extraction(candidate, token_id)
        ]
    return [
        token_id
        for token_id in range(reference.vocab_size)
        if extraction(reference, kind, token_id) != extraction(candidate, kind, token_id)
    ]


def id_difference_summary(token_ids: list[int]) -> dict[str, object]:
    """Record a small exact list, or a stable digest and examples for a large list."""
    encoded = ",".join(map(str, token_ids)).encode()
    result: dict[str, object] = {
        "count": len(token_ids),
        "ids_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    if len(token_ids) <= 64:
        result["token_ids"] = token_ids
    else:
        result["first_32_token_ids"] = token_ids[:32]
        result["last_32_token_ids"] = token_ids[-32:]
    return result


def write_outputs(candidates: list[CandidateSpec], out_dir: Path) -> dict:
    """Run all candidates and write deterministic JSON and per-script CSV reports."""
    if not candidates:
        raise ValueError("at least one candidate is required")
    names = [candidate.name for candidate in candidates]
    if len(set(names)) != len(names):
        raise ValueError("candidate names must be unique")

    tokenizers = {}
    report = {
        "format": "ke2-tokenizer-candidate-revalidation-v2",
        "versions": dependency_versions(),
        "pos_dims": list(POS_DIMS),
        "candidate_order": names,
        "candidates": {},
        "differences_from_previous_candidate": {},
    }
    collision_rows = []
    group_rows = []
    for candidate in candidates:
        name = candidate.name
        tokenizer, payload, detail = build_candidate(candidate)
        tokenizers[name] = tokenizer
        report["candidates"][name] = payload
        for row in detail["audit"].summary:
            collision_rows.append({"candidate": name, **row})
        for group in detail["audit"].groups:
            group_rows.append(
                {
                    "candidate": name,
                    "extraction": group.extraction,
                    "P": group.P,
                    "group_id": group.group_id,
                    "cause": group.cause,
                    "script_class": group.script_class,
                    "n_tokens": len(group.ids),
                    "n_pairs": len(group.ids) * (len(group.ids) - 1) // 2,
                    "token_ids": ";".join(map(str, group.ids)),
                }
            )

    for reference_name, name in pairwise(names):
        reference = tokenizers[reference_name]
        candidate = tokenizers[name]
        report["differences_from_previous_candidate"][name] = {
            "reference": reference_name,
            "raw_changed": id_difference_summary(changed_token_ids(reference, candidate, "raw")),
            "decode_changed": id_difference_summary(changed_token_ids(reference, candidate, "decode")),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    columns = ["candidate", *collision_audit.SUMMARY_COLUMNS]
    with (out_dir / "collisions_by_script.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(collision_rows)
    group_columns = [
        "candidate",
        "extraction",
        "P",
        "group_id",
        "cause",
        "script_class",
        "n_tokens",
        "n_pairs",
        "token_ids",
    ]
    with (out_dir / "collision_groups.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=group_columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(group_rows)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", type=parse_candidate, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    report = write_outputs(args.candidate, args.out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
