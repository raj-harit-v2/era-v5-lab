"""Materialize the first-training pipeline config from a frozen input inventory.

Run after build_inventory.py. All generated files stay under out/; the raw parts,
tokenizer, model and approved pack table are read only.
"""
import argparse
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TOKENIZER_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
DATASET_VERSION = "first-training-v1"
MODEL_REVISION = "836121a0533e5664b21c7aacc5d22951f2b8b25b"
MODEL_FILES = {
    "model.safetensors": (1883734344, "77d8e1f2dbab6eb5d3c261ce9d3dbf1e3c69e02938c95f934f94f42c22dfa31f"),
    "2_Dense/model.safetensors": (2362528, "f866c945fa2147ce4940c8ead0b4b20af4217e0f4664bd35f41c2a0967c4fe77"),
    "config.json": (804, "b6bd83d561db8d2ccb7f44dafcd945e39bea16dc2819072ffb10adb45608b029"),
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def relative_or_absolute(path):
    path = path.resolve()
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def prepare(bundle, raw, tokenizer, pack_table, run_id, model_path=None, f2_workers=1):
    if type(f2_workers) is not int or f2_workers < 1:
        raise ValueError("f2_workers must be a positive integer")
    bundle, raw, tokenizer = (Path(p).resolve() for p in (bundle, raw, tokenizer))
    make_table = pack_table is None
    pack_table = bundle / "pack_metadata.json" if make_table else Path(pack_table).resolve()
    if not bundle.is_relative_to(REPO / "out"):
        raise ValueError("bundle must be inside the repository's out/ folder")
    if not raw.is_dir():
        raise ValueError(f"raw input folder does not exist: {raw}")
    if not run_id or "/" in run_id or "\\" in run_id or run_id in (".", ".."):
        raise ValueError("run_id must be one safe folder name")
    output = bundle / "run.json"
    if output.exists():
        raise ValueError(f"run config already exists: {output}; use a new bundle or run_id")
    manifest_path, inventory_path = bundle / "input_manifest.json", bundle / "expected_inventory.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("input_manifest_sha256") != sha256(manifest_path):
        raise ValueError("input inventory does not pin this manifest")
    scope = json.loads((HERE / "approved_inputs.json").read_text(encoding="utf-8"))
    if manifest.get("approved_inputs_sha256") != sha256(HERE / "approved_inputs.json"):
        raise ValueError("input manifest was built from another approved_inputs.json; rebuild the inventory")
    packs = [p["pack_id"] for p in scope["packs"]]
    if inventory.get("packs") != packs:
        raise ValueError("inventory does not list every approved pack in order")
    parts = manifest.get("shards") or []
    if {p["path"] for p in parts} != {p["part"] for p in inventory["parts"]}:
        raise ValueError("manifest and inventory list different parts")
    counts = {split: sum(p["split"] == split for p in parts) for split in ("train", "heldout")}
    if not all(counts.values()):
        raise ValueError("both train and heldout must have parts")
    if not tokenizer.is_file() or sha256(tokenizer) != TOKENIZER_SHA256:
        raise ValueError("tokenizer is missing or is not frozen p1536")
    fields = ("language", "script", "domain", "lane", "license", "license_source")
    if make_table and pack_table.exists():
        raise ValueError(f"pack table already exists: {pack_table}; use a new bundle")
    table = ({p["pack_id"]: {k: p[k] for k in fields} for p in scope["packs"]} if make_table
             else json.loads(pack_table.read_text(encoding="utf-8"))["packs"])
    if set(table) != set(packs):
        raise ValueError("pack table must list exactly the approved packs")
    for p in scope["packs"]:
        row = table[p["pack_id"]]
        if any(not isinstance(row.get(k), str) or not row[k].strip()
               for k in fields):
            raise ValueError(f"pack table has incomplete metadata for {p['pack_id']}")
        if (row["license"], row["license_source"]) != (p["license"], p["license_source"]):
            raise ValueError(f"pack table licence differs from approved inputs for {p['pack_id']}")
    if model_path is None:
        h3 = json.loads((HERE / "h3.json").read_text(encoding="utf-8"))
        model_path = REPO / h3["model_path"]
    if not Path(model_path).resolve().is_dir():
        raise ValueError(f"offline H3 model folder is missing: {model_path}")
    for name, (size, expected) in MODEL_FILES.items():
        file = Path(model_path) / name
        if not file.is_file() or file.stat().st_size != size or sha256(file) != expected:
            raise ValueError(f"offline H3 model differs from LaBSE revision {MODEL_REVISION}: {name}")
    cfg = {
        "run_id": run_id, "out": "out/pipeline", "inventory": relative_or_absolute(inventory_path),
        "intermediates": "keep",
        "stages": {
            "clean": {"mode": "run", "settings": "teams/01-data-a/pipeline/clean.json",
                      "input": relative_or_absolute(raw), "manifest": relative_or_absolute(manifest_path),
                      "manifest_sha256": inventory["input_manifest_sha256"], "expected_parts": counts},
            "overlap": {"mode": "run", "settings": "teams/01-data-a/dedup/overlap.json"},
            "h3": {"mode": "run", "settings": "teams/01-data-a/jobs/2026-11-19-first-training/h3.json"},
            "dedup": {"mode": "run", "settings": "teams/01-data-a/dedup/dedup.json"},
            "f2": {"pool": True, "workers": f2_workers},
            "ledger": {"raw": relative_or_absolute(raw)},
            "shards": {"tokenizer": relative_or_absolute(tokenizer), "dataset_version": DATASET_VERSION,
                       "pack_table": relative_or_absolute(pack_table)},
            "reconcile": {},
        },
    }
    if make_table:
        pack_table.write_text(json.dumps({"packs": table}, indent=2) + "\n", encoding="utf-8", newline="\n")
    output.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8", newline="\n")
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--pack-table", type=Path,
                    help="Optional explicit table; by default materialize the approved input metadata in the bundle.")
    ap.add_argument("--f2-workers", type=int, default=1,
                    help="F2 processes; default 1. Set explicitly for the host's available CPU and RAM.")
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    try:
        print(prepare(args.bundle, args.input_root, args.tokenizer, args.pack_table, args.run_id,
                      f2_workers=args.f2_workers))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(1, f"prepare_run: {exc}\n")


if __name__ == "__main__":
    main()
