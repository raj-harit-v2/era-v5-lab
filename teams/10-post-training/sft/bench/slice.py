"""Build the WP3 bench slice from admitted OCR-2 pack rows: split by problem cluster, never by row.

    python slice.py --shard-dir <run>/shards/shard-00000 ... --clusters family_clusters.json \
        --heldout-ids heldout_eval_v1_ids.PRIVATE.jsonl --tokenizer <smollm2 tokenizer.json> --out-dir <private dir>

Inputs per shard folder (the `run_ocr2.py --mode admission` layout): `pack/pack.jsonl` (training rows) and
`join/joined.sidecar.jsonl` (one line per rendered row: problem family key, source row key, OCR ids).
`pack/pack.heldout_eval_v1.jsonl` is never opened: the held-out problems are known from the id list
(`--heldout-ids`, ids and keys only).

Grouping key. A pack row's `source_id` is the OCR-2 completion id (`sidecar.ocr_id`), not a problem id: one problem
has many completions. The unit here is the near-duplicate cluster of the row's `problem_family_key` (exact
statement identity across TACO/APPS/code_contests, from the pack build), using the cluster map given in
`--clusters` (10 Nov MinHash, word 5-gram Jaccard >= 0.8). A family missing from the map is its own cluster.

Rules, in order: (1) the row id must map to a sidecar line whose `ocr_id` equals the row's `source_id`; (2) a row
whose cluster contains a WP1 held-out family is dropped (`cluster_touches_heldout`); (3) the row must re-tokenise
under the surrogate (`retok.retokenize`) within `--max-tokens`; (4) split = salted sha256 of the cluster id against
the cumulative `--fractions` (train, dev, test); (5) optional per-split row caps keep the rows with the smallest
salted row hash (deterministic). Writes `<split>.jsonl` (pack text + spans + keys), `<split>.tok.jsonl` and
`manifest.json` (counts, ids, sha256 of every input and output). Keep `--out-dir` out of Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import retok  # noqa: E402

SPLITS = ("train", "dev", "test")
DEFAULT_SALT = "g10-bench-slice-v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def unit_hash(salt: str, key: str) -> float:
    d = hashlib.sha256(f"{salt}\n{key}".encode("utf-8")).digest()
    return int.from_bytes(d[:8], "big") / 2**64


def assign_split(cluster: str, salt: str, fractions: tuple[float, float, float]) -> str:
    u = unit_hash(salt, cluster)
    if u < fractions[0]:
        return "train"
    if u < fractions[0] + fractions[1]:
        return "dev"
    return "test"


def read_shard(shard_dir: Path) -> tuple[list[dict], dict[str, dict]]:
    side = {}
    with open(shard_dir / "join" / "joined.sidecar.jsonl", encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            side[e["rendered_id"]] = e
    rows = []
    with open(shard_dir / "pack" / "pack.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            row = {k: r[k] for k in ("id", "set", "source_id", "effort", "text", "train_spans")}
            row["c3_len"] = len(r["input_ids"])
            rows.append(row)
    return rows, side


def build(shard_dirs: list[Path], clusters_path: Path, heldout_ids: Path, tokenizer: Path, out_dir: Path,
          max_tokens: int, fractions: tuple[float, float, float], salt: str, caps: dict[str, int | None],
          prefilter_factor: float = 2.0) -> dict:
    t0 = time.time()
    cmap = json.loads(clusters_path.read_text(encoding="utf-8"))
    fam_cluster = cmap["family_to_cluster"]
    held_fams = {json.loads(l)["problem_family_key"] for l in heldout_ids.read_text(encoding="utf-8").splitlines() if l.strip()}
    held_clusters = {fam_cluster[f] for f in held_fams if f in fam_cluster}
    tok, tok_sha = retok.load_tokenizer(tokenizer)
    counts: Counter = Counter()
    keep, seen_ids = [], set()
    inputs = {}
    for sd in shard_dirs:
        rows, side = read_shard(sd)
        inputs[sd.name] = {"pack_sha256": sha256_file(sd / "pack" / "pack.jsonl"),
                           "sidecar_sha256": sha256_file(sd / "join" / "joined.sidecar.jsonl"), "pack_rows": len(rows)}
        for r in rows:
            counts["pack_rows"] += 1
            e = side.get(r["id"])
            if e is None or e["ocr_id"] != r["source_id"] or r["id"] in seen_ids:
                raise SystemExit(f"row {r['id']}: sidecar join failed or duplicate id")
            seen_ids.add(r["id"])
            fam = e["problem_family_key"]
            if fam in held_fams:
                raise SystemExit(f"row {r['id']}: family is in the WP1 held-out list (pack and held-out overlap)")
            cl = fam_cluster.get(fam)
            if cl is None:
                counts["family_without_cluster_signature"] += 1
                cl = "f:" + fam
            if cl in held_clusters:
                counts["dropped_cluster_touches_heldout"] += 1
                continue
            if r["c3_len"] > prefilter_factor * max_tokens:
                counts["dropped_c3_prefilter"] += 1
                continue
            r.update(problem_family_key=fam, cluster=cl, ocr_question_id=e["ocr_question_id"],
                     source_row_key=e["source_row_key"], source_file=e["source_file"],
                     source_local_ordinal=e["source_local_ordinal"], question_sha256=e["question_sha256"])
            keep.append(r)
    # C3 prefilter above keeps memory bounded; it is lossless while surrogate/C3 length >= 1/prefilter_factor,
    # and the smallest observed ratio is recorded so that can be checked. Tokenise in chunks.
    tokd = []
    for i in range(0, len(keep), 1000):
        part, rejected = retok.retokenize(keep[i : i + 1000], tok, max_tokens)
        tokd += part
        for k, v in rejected.items():
            counts[f"dropped_{k}"] += v
    min_ratio = min((len(r["input_ids"]) / r["c3_len"] for r in tokd), default=None)
    by_split = {s: [] for s in SPLITS}
    for r in tokd:
        r["split"] = assign_split(r["cluster"], salt, fractions)
        by_split[r["split"]].append(r)
    uncapped = {s: len(v) for s, v in by_split.items()}
    for s in SPLITS:
        cap = caps.get(s)
        if cap is not None and len(by_split[s]) > cap:
            by_split[s] = sorted(by_split[s], key=lambda r: unit_hash(salt + "/row", r["id"]))[:cap]
        by_split[s].sort(key=lambda r: r["id"])
    # zero-overlap proof at every grouping level
    level_sets = {lvl: {s: {r[lvl] for r in by_split[s]} for s in SPLITS}
                  for lvl in ("cluster", "problem_family_key", "question_sha256", "ocr_question_id")}
    overlap = {lvl: {f"{a}&{b}": len(sets[a] & sets[b]) for a, b in (("train", "dev"), ("train", "test"), ("dev", "test"))}
               for lvl, sets in level_sets.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for s in SPLITS:
        text_rows = [{k: r[k] for k in ("id", "set", "source_id", "effort", "text", "train_spans", "problem_family_key",
                                         "cluster", "source_row_key", "source_file", "source_local_ordinal",
                                         "question_sha256", "ocr_question_id", "split")} for r in by_split[s]]
        blob = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in text_rows).encode("utf-8")
        (out_dir / f"{s}.jsonl").write_bytes(blob)
        tblob = "".join(json.dumps({k: r[k] for k in ("id", "split", "cluster", "problem_family_key", "surrogate_text",
                                                        "input_ids", "loss_mask", "prompt_len", "target_tokens",
                                                        "target_bytes", "source_row_key", "source_file",
                                                        "source_local_ordinal", "question_sha256")},
                                   ensure_ascii=False) + "\n" for r in by_split[s]).encode("utf-8")
        (out_dir / f"{s}.tok.jsonl").write_bytes(tblob)
        files[s] = {"rows": len(by_split[s]), "rows_before_cap": uncapped[s], "jsonl_sha256": hashlib.sha256(blob).hexdigest(),
                    "tok_sha256": hashlib.sha256(tblob).hexdigest(), "clusters": len(level_sets["cluster"][s]),
                    "families": len(level_sets["problem_family_key"][s]),
                    "tokens": sum(len(r["input_ids"]) for r in by_split[s]),
                    "target_tokens": sum(r["target_tokens"] for r in by_split[s]),
                    "target_bytes": sum(r["target_bytes"] for r in by_split[s]),
                    "max_len": max((len(r["input_ids"]) for r in by_split[s]), default=0),
                    "by_source": dict(sorted(Counter(r["source_row_key"][2] for r in by_split[s]).items())),
                    "ids_sha256": hashlib.sha256("\n".join(r["id"] for r in by_split[s]).encode()).hexdigest()}
    manifest = {
        "schema": "g10-bench-slice/1",
        "data_provenance": "WP1 C3 OCR-2 pack v1, CONDITIONAL build (draft PR #79; WP11 verdicts and the held-out "
                           "split decision open). Rows are the training pack only; held-out rows never read.",
        "inputs": inputs, "clusters": {"path_sha256": sha256_file(clusters_path), "threshold": cmap.get("threshold"),
                                       "parity_with_combine_dedup": cmap.get("parity_with_combine_dedup")},
        "heldout_ids_sha256": sha256_file(heldout_ids), "heldout_families": len(held_fams),
        "heldout_clusters_in_map": len(held_clusters),
        "surrogate": {**retok.SURROGATE, "tokenizer_sha256_used": tok_sha,
                      "marker_map": {k: list(v) for k, v in retok.MARKER_MAP.items()}},
        "max_tokens": max_tokens, "fractions": fractions, "salt": salt, "caps": caps, "unit": "near-duplicate cluster of problem_family_key",
        "c3_prefilter": {"factor": prefilter_factor, "min_surrogate_over_c3_ratio_kept": min_ratio,
                         "lossless_if_ratio_ge": 1 / prefilter_factor},
        "counts": dict(counts), "rows_after_filters": len(tokd), "splits": files, "overlap": overlap,
        "zero_overlap": all(v == 0 for lv in overlap.values() for v in lv.values()),
        "seconds": round(time.time() - t0, 1),
        "ids": {s: [r["id"] for r in by_split[s]] for s in SPLITS},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    if not manifest["zero_overlap"]:
        raise SystemExit("split overlap found; see manifest.json")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shard-dir", action="append", required=True, type=Path)
    ap.add_argument("--clusters", required=True, type=Path)
    ap.add_argument("--heldout-ids", required=True, type=Path)
    ap.add_argument("--tokenizer", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--fractions", default="0.90,0.05,0.05")
    ap.add_argument("--salt", default=DEFAULT_SALT)
    ap.add_argument("--cap-train", type=int, default=4000)
    ap.add_argument("--cap-dev", type=int, default=300)
    ap.add_argument("--cap-test", type=int, default=300)
    args = ap.parse_args(argv)
    fr = tuple(float(x) for x in args.fractions.split(","))
    if len(fr) != 3 or abs(sum(fr) - 1) > 1e-9:
        raise SystemExit("--fractions needs three values summing to 1")
    m = build(args.shard_dir, args.clusters, args.heldout_ids, args.tokenizer, args.out_dir, args.max_tokens, fr,
              args.salt, {"train": args.cap_train, "dev": args.cap_dev, "test": args.cap_test})
    print(json.dumps({k: m[k] for k in ("counts", "rows_after_filters", "splits", "zero_overlap", "seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
