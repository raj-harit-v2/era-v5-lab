"""Verify and package the OCR-2 pack's held-out split seed and row ids for TSAI (G10, week-3 task 1).

    python ocr2_heldout_handoff.py --ids heldout_eval_v1_ids.PRIVATE.jsonl --bundle-dir <private folder> \
        --summary results/ocr2_heldout_v1_handoff.json

TSAI (G10, 15 Nov): keep the 2% held-out split and record the split seed and the row ids in the pack manifest.
The split has no random seed: `pack_admission.heldout_selector` holds a problem family out when the first 8 bytes of
sha256(salt + "\\n" + family key) fall under fraction * 2**64. The salt and fraction in `ocr2_policy.json` are the seed.

This script checks the private id list against that rule and against the public pack manifest, then writes
- a private bundle (`--bundle-dir`, keep it out of Git): the split rule, the id list, the family list and SHA256SUMS;
- a public summary (`--summary`): rule, counts and hashes only, no id and no family key.

Checks (any failure exits 1 and writes nothing): the manifest's rule equals the policy's; every listed row's family
is held under the rule; ids are unique; rows, families, rows by source and rows by shard equal the manifest; the id
list sha256 equals the manifest's. The train side (no pack row's family is held) was checked at build time by
`pack_admission.py` and the aggregator; this script does not reread the packs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = "g10-ocr2-heldout-handoff/1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def selector(fraction: float, salt: str):
    """Same rule as pack_admission.heldout_selector (kept import-free so the check runs without the pack tooling)."""
    threshold = int(fraction * 2**64)

    def held(family: str) -> bool:
        return int.from_bytes(hashlib.sha256(f"{salt}\n{family}".encode("utf-8")).digest()[:8], "big") < threshold
    return held


def verify(ids_path: Path, policy: dict, manifest: dict) -> tuple[dict, list[dict]]:
    spec = policy["pack"]["heldout_eval_v1"]
    held = selector(spec["fraction"], spec["salt"])
    rows = [json.loads(line) for line in ids_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    fam = Counter(r["problem_family_key"] for r in rows)
    by_source = Counter(f"{r['source_row_key'][2]}/{r['source_row_key'][3]}" for r in rows)
    by_shard = Counter(r["shard_id"] for r in rows)
    m = manifest["heldout_eval_v1"]
    shard_rows = {s["shard_id"]: s["heldout_rows"] for s in manifest["shards"]}
    not_held = sum(1 for f in fam if not held(f))
    checks = {
        "rule_in_manifest_equals_policy": m["rule"]["fraction"] == spec["fraction"] and m["rule"]["salt"] == spec["salt"],
        "every_family_held_under_rule": not_held == 0,
        "ids_unique": len({r["id"] for r in rows}) == len(rows),
        "rows_equal_manifest": len(rows) == m["rows"],
        "families_equal_manifest": len(fam) == m["families"],
        "rows_by_source_equal_manifest": dict(by_source) == m["rows_by_source"],
        "rows_by_shard_equal_manifest": all(by_shard.get(k, 0) == v for k, v in shard_rows.items())
                                         and set(by_shard) <= set(shard_rows),
        "id_list_sha256_equals_manifest": sha256_file(ids_path) == m["id_list_sha256"],
    }
    summary = {
        "schema": SCHEMA,
        "split_rule": {"fraction": spec["fraction"], "salt": spec["salt"], "unit": "problem family key",
                       "function": "held(family) = int.from_bytes(sha256(salt + '\\n' + family)[:8], 'big') < fraction * 2**64",
                       "code": "sft/pack_admission.py heldout_selector", "random_seed": None,
                       "seed_note": "deterministic salted hash: the salt and fraction are the split seed"},
        "rows": len(rows), "families": len(fam), "rows_by_source": dict(sorted(by_source.items())),
        "shards_with_heldout_rows": len(by_shard), "families_not_held_under_rule": not_held,
        "id_list_sha256": sha256_file(ids_path),
        "family_list_sha256": hashlib.sha256("".join(f"{f}\n" for f in sorted(fam)).encode()).hexdigest(),
        "pack_manifest": {"name": "ocr2_pack_v1_manifest.json"},
        "checks": checks, "ok": all(checks.values()),
        "private_bundle_note": "the id list and family list are private (ids and keys only, no text); TSAI receives "
                               "them through a job request, and Git holds only these hashes",
    }
    return summary, rows


def write_bundle(bundle: Path, ids_path: Path, rows: list[dict], summary: dict) -> None:
    bundle.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ids_path, bundle / "heldout_eval_v1_ids.jsonl")
    fams = sorted({r["problem_family_key"] for r in rows})
    (bundle / "heldout_eval_v1_families.txt").write_text("".join(f"{f}\n" for f in fams), encoding="utf-8")
    (bundle / "split_rule.json").write_text(json.dumps(summary["split_rule"], indent=1) + "\n", encoding="utf-8")
    sums = [f"{sha256_file(bundle / n)}  {n}\n" for n in ("heldout_eval_v1_ids.jsonl", "heldout_eval_v1_families.txt",
                                                          "split_rule.json")]
    (bundle / "SHA256SUMS").write_text("".join(sums), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", required=True, type=Path, help="private held-out id list (heldout_eval_v1_ids.PRIVATE.jsonl)")
    ap.add_argument("--policy", type=Path, default=HERE / "ocr2_policy.json")
    ap.add_argument("--manifest", type=Path, default=HERE / "results" / "ocr2_pack_v1_p1536_manifest.json",
                    help="pack manifest (p1536 since 16 Nov 2026; the C3 record is ocr2_pack_v1_c3_manifest.json)")
    ap.add_argument("--bundle-dir", type=Path, help="private output folder (not in Git)")
    ap.add_argument("--summary", type=Path, help="public summary JSON (counts and hashes only)")
    a = ap.parse_args(argv)
    summary, rows = verify(a.ids, json.loads(a.policy.read_text(encoding="utf-8")),
                           json.loads(a.manifest.read_text(encoding="utf-8")))
    summary["pack_manifest"] = {"name": a.manifest.name, "sha256": sha256_file(a.manifest)}
    bad = [k for k, v in summary["checks"].items() if not v]
    print(f"held-out rows {summary['rows']} families {summary['families']} by source {summary['rows_by_source']} "
          f"not held under rule {summary['families_not_held_under_rule']} -> {'OK' if not bad else 'FAILED: ' + ', '.join(bad)}")
    if bad:
        return 1
    if a.bundle_dir:
        write_bundle(a.bundle_dir, a.ids, rows, summary)
    if a.summary:
        a.summary.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
