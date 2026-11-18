"""SFT data v1 admission index for one converted C3 set (G10, week-3 task 1).

    python sft_v1_admit.py --record results/sft_v1_records/<set>.full.record.json --parts-dir <private>/full/<set> \
        [--partials <private>/partials/<set>] [--decontam-record R.json ...] [--heldout-ids ids.jsonl ...] \
        [--max-len 32768] --out-dir <private admit dir> --summary <public summary.json>

A `full` record from `sft_v1_records.py` says what was converted. Before a pack can use it, three exclusions apply:

1. decontamination: ids flagged by Team 9's full fingerprint set (the pinned set_sha256) or holding a canary, read
   from `decontam_run.py` records. The records' input sha256 values must cover the set: either one input equals the
   record's `content_sha256` (the parts concatenated) or the inputs cover every part's `plain_sha256`.
2. held-out ids: any id listed in a `--heldout-ids` file (JSONL with an `id` field, or one id per line).
3. length: rows longer than `--max-len` tokens (`max_sequence_tokens`, 32768 provisional for SFT data v1).

Each exclusion is counted on its own as well as once per row (a row can fail several). Row ids and lengths come from
the stored per-part check results of `sft_v1_records.py check-parts` when one exists for the exact gz bytes of a
part, else from reading the part (its decompressed bytes must hash to the record's `plain_sha256`).

Private outputs (keep `--out-dir` out of Git): `<set>.kept_ids.txt` (one id per line) and `<set>.excluded.jsonl`
(id and reasons only). Public output: the summary (counts, tokens, hashes; no ids, no text).

`status` is `admissible` only when the licence decision is `allowed` and decontamination covers every part.
Otherwise it says what is missing (`licence_not_admitted`, `decontam_pending`); the index is then not train-ready.
Nothing here grants a licence or a TSAI admission.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

SCHEMA = "g10-sft-v1-admission/1"
PINNED_SET_SHA256 = "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"  # fingerprints v2, lab PR #280
DEFAULT_MAX_LEN = 32768


class AdmitError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_part(gz: Path, plain_sha256: str) -> tuple[list[str], list[int]]:
    """Ids and token lengths of one part, verifying its decompressed bytes."""
    ids, lengths, h = [], [], hashlib.sha256()
    with gzip.open(gz, "rb") as f:
        for line in f:
            h.update(line)
            row = json.loads(line)
            ids.append(row["id"])
            lengths.append(len(row["input_ids"]))
    if h.hexdigest() != plain_sha256:
        raise AdmitError(f"{gz.name}: decompressed sha256 {h.hexdigest()} is not the record's {plain_sha256}")
    return ids, lengths


def part_rows(part: dict, parts_dir: Path, partials: Path | None, tokenizer_sha256: str,
              verify_disk: bool) -> tuple[list[str], list[int], str]:
    gz = parts_dir / part["name"]
    if verify_disk:
        if not gz.is_file():
            raise AdmitError(f"{gz} is missing")
        if gz.stat().st_size != part["gz_bytes"] or sha256_file(gz) != part["gz_sha256"]:
            raise AdmitError(f"{gz.name}: gz bytes on disk differ from the record")
    if partials is not None:
        stored = partials / f"{part['name']}.check.json"
        if stored.is_file():
            p = json.loads(stored.read_text(encoding="utf-8"))
            if (p["file"]["name"] == part["name"] and p["file"]["sha256"] == part["gz_sha256"]
                    and p.get("plain_sha256") == part["plain_sha256"] and p.get("tokenizer_sha256") == tokenizer_sha256
                    and len(p["ids"]) == len(p["lengths"]) == p["rows"]):
                return p["ids"], p["lengths"], "stored_check"
    if not gz.is_file():
        raise AdmitError(f"{gz} is missing and no stored check matches it")
    ids, lengths = read_part(gz, part["plain_sha256"])
    return ids, lengths, "read"


def load_decontam(paths: list[Path], set_id: str, record: dict) -> tuple[set[str], dict]:
    """Removed ids from decontam_run.py records, and whether their inputs cover the whole set."""
    removed, flagged, canary, benchmarks, input_shas = set(), 0, 0, {}, set()
    for path in paths:
        r = json.loads(Path(path).read_text(encoding="utf-8"))
        if r.get("set") != set_id:
            raise AdmitError(f"{path}: decontam record is for {r.get('set')!r}, not {set_id!r}")
        if r.get("set_sha256") != PINNED_SET_SHA256 or r.get("scope") != "full set":
            raise AdmitError(f"{path}: not the full pinned fingerprint set (set_sha256 {r.get('set_sha256')}, "
                             f"scope {r.get('scope')!r})")
        if not r.get("ok") or (r.get("recheck_on_clean") or {}).get("flagged") != 0:
            raise AdmitError(f"{path}: decontam record is not ok (failed check, canary or no clean recheck)")
        ids = set(r["flagged"]) | {h["doc_id"] for h in r["canary"]["hits"]}
        removed |= ids
        flagged += r["rows_flagged"]
        canary += r["rows_canary"]
        for b, n in r["by_benchmark"].items():
            benchmarks[b] = benchmarks.get(b, 0) + n
        input_shas |= {i["sha256"] for i in r["inputs"]}
    whole = record["content_sha256"] in input_shas
    uncovered = [] if whole else sorted(p["name"] for p in record["parts"] if p["plain_sha256"] not in input_shas)
    info = {"records": len(paths), "rows_flagged": flagged, "rows_canary": canary,
            "by_benchmark": dict(sorted(benchmarks.items())), "covers": "whole set" if whole else
            f"{len(record['parts']) - len(uncovered)} of {len(record['parts'])} parts",
            "parts_uncovered": len(uncovered), "complete": whole or not uncovered,
            "fingerprint_set_sha256": PINNED_SET_SHA256}
    if not paths:
        info["complete"] = False
    return removed, info


def load_ids(paths: list[Path]) -> tuple[set[str], list[dict]]:
    out, info = set(), []
    for path in paths:
        n = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                out.add(json.loads(line)["id"] if line.startswith("{") else line)
                n += 1
        info.append({"name": Path(path).name, "rows": n, "sha256": sha256_file(Path(path))})
    return out, info


def admit(record_path: Path, parts_dir: Path, out_dir: Path, partials: Path | None = None,
          decontam: list[Path] | None = None, heldout: list[Path] | None = None,
          max_len: int = DEFAULT_MAX_LEN, verify_disk: bool = True) -> dict:
    record = json.loads(Path(record_path).read_text(encoding="utf-8"))
    set_id = record["set"]
    if not str(record.get("scope", "")).startswith("full") or not record.get("parts"):
        raise AdmitError(f"{record_path}: not a full record with parts")
    ids_all, lens_all, sources = [], [], {"stored_check": 0, "read": 0}
    for part in record["parts"]:
        ids, lengths, how = part_rows(part, Path(parts_dir), Path(partials) if partials else None,
                                      record["tokenizer_sha256"], verify_disk)
        ids_all += ids
        lens_all += lengths
        sources[how] += 1
    if len(ids_all) != record["rows_out"]:
        raise AdmitError(f"{len(ids_all)} rows read, record says {record['rows_out']}")
    if len(set(ids_all)) != len(ids_all):
        raise AdmitError("duplicate ids across parts")
    lengths = np.asarray(lens_all, dtype=np.int64)
    if int(lengths.sum()) != record["checks"]["tokens"]:
        raise AdmitError(f"token total {int(lengths.sum())} differs from the record's {record['checks']['tokens']}")

    removed, dinfo = load_decontam(list(decontam or []), set_id, record)
    held, hinfo = load_ids(list(heldout or []))
    id_arr = np.asarray(ids_all, dtype=object)
    in_decon = np.fromiter((i in removed for i in ids_all), dtype=bool, count=len(ids_all))
    in_held = np.fromiter((i in held for i in ids_all), dtype=bool, count=len(ids_all))
    over = lengths > max_len
    if removed - set(ids_all):
        raise AdmitError(f"{len(removed - set(ids_all))} decontam ids are not ids of this set")
    keep = ~(in_decon | in_held | over)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    kept_path = out_dir / f"{set_id}.kept_ids.txt"
    excl_path = out_dir / f"{set_id}.excluded.jsonl"
    with open(kept_path, "w", encoding="utf-8") as f:
        f.writelines(f"{i}\n" for i in id_arr[keep])
    with open(excl_path, "w", encoding="utf-8") as f:
        for j in np.flatnonzero(~keep):
            reasons = [r for r, m in (("decontam", in_decon), ("heldout", in_held), ("over_max_len", over)) if m[j]]
            f.write(json.dumps({"id": ids_all[j], "reasons": reasons}) + "\n")

    decision = record.get("decision", "")
    licence_ok = decision.lower().startswith("allowed")
    status = [s for s, bad in (("licence_not_admitted", not licence_ok), ("decontam_pending", not dinfo["complete"]))
              if bad] or ["admissible"]
    k = int(keep.sum())
    return {
        "schema": SCHEMA, "set": set_id, "status": "+".join(status),
        "licence_decision": decision,
        "record": {"name": Path(record_path).name, "sha256": sha256_file(Path(record_path)),
                   "content_sha256": record["content_sha256"], "tokenizer_sha256": record["tokenizer_sha256"]},
        "parts": len(record["parts"]), "parts_from_stored_check": sources["stored_check"], "parts_read": sources["read"],
        "max_len": max_len,
        "rows_in": len(ids_all), "tokens_in": int(lengths.sum()),
        "excluded_each": {"decontam": int(in_decon.sum()), "heldout": int(in_held.sum()), "over_max_len": int(over.sum())},
        "rows_excluded": len(ids_all) - k, "rows_kept": k, "tokens_kept": int(lengths[keep].sum()),
        "kept_max_len": int(lengths[keep].max()) if k else None,
        "decontam": dinfo, "heldout_lists": hinfo,
        "kept_ids_sha256": sha256_file(kept_path), "excluded_sha256": sha256_file(excl_path),
        "private_outputs_note": "kept_ids.txt and excluded.jsonl hold row ids: private, not in Git",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", required=True, type=Path, help="full record (results/sft_v1_records/<set>.full.record.json)")
    ap.add_argument("--parts-dir", required=True, type=Path, help="folder with <set>.partNNNN.jsonl.gz")
    ap.add_argument("--partials", type=Path, help="stored per-part checks (sft_v1_records.py check-parts)")
    ap.add_argument("--decontam-record", nargs="*", default=[], type=Path, help="decontam_run.py records of this set")
    ap.add_argument("--heldout-ids", nargs="*", default=[], type=Path, help="held-out id lists to exclude")
    ap.add_argument("--max-len", type=int, default=DEFAULT_MAX_LEN)
    ap.add_argument("--no-verify-disk", action="store_true", help="do not re-hash the gz parts on disk")
    ap.add_argument("--out-dir", required=True, type=Path, help="private output folder (not in Git)")
    ap.add_argument("--summary", required=True, type=Path, help="public summary JSON (counts and hashes only)")
    a = ap.parse_args(argv)
    try:
        s = admit(a.record, a.parts_dir, a.out_dir, a.partials, a.decontam_record, a.heldout_ids, a.max_len,
                  not a.no_verify_disk)
    except (AdmitError, OSError, KeyError, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(s, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    e = s["excluded_each"]
    print(f"{s['set']}: rows {s['rows_in']} kept {s['rows_kept']} (decontam {e['decontam']}, heldout {e['heldout']}, "
          f"over {s['max_len']} {e['over_max_len']}) tokens kept {s['tokens_kept']} status {s['status']} "
          f"decontam {s['decontam']['covers']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
