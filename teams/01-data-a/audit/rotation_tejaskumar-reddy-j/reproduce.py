"""Reproduce Tejaskumar's two-shard Data A rotation audit; emit IDs, counts and hashes, never text.

Runs check_shard.py (PR #482, on main) on each assigned shard, adds the assigned-pack/sample scope, source-row,
exclusion and writer-history checks of PR #540, and decodes 20 documents per shard with the frozen p1536 tokenizer.
Requires numpy, pyarrow and tokenizers.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import pyarrow
import pyarrow.parquet as pq
import tokenizers
from tokenizers import Tokenizer

TOKENIZER_SHA = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
SHARDS = ("code-go-train-000001", "sci-finepdfs-train-000000")
EOS_ID, HEADER_BYTES, DECODE_N = 130822, 1024, 20


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def decode_sample(tok, folder, sid, idx, docs):
    """Decode 20 documents spread evenly over the shard (first and last included). Records counts and hashes only."""
    payload = np.memmap(folder / (sid + ".bin"), dtype="<u4", mode="r", offset=HEADER_BYTES)
    n = len(idx) - 1
    out = []
    for i in sorted({int(round(x)) for x in np.linspace(0, n - 1, min(DECODE_N, n))}):
        ids = payload[int(idx[i]):int(idx[i + 1])].tolist()
        body = ids[:-1]
        text = tok.decode(body, skip_special_tokens=False)
        out.append({
            "position": i, "doc_id": docs["doc_id"][i], "n_tokens": len(ids), "ends_with_eos": ids[-1] == EOS_ID,
            "replacement_chars": text.count("�"), "decoded_chars": len(text), "n_chars": docs["n_chars"][i],
            "reencode_matches": tok.encode(text, add_special_tokens=False).ids == body,
            "decoded_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--checker", type=Path, default=Path("teams/01-data-a/audit/check_shard.py"))
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if sha(a.tokenizer) != TOKENIZER_SHA:
        raise SystemExit("Refusing a tokenizer other than frozen p1536")
    spec = importlib.util.spec_from_file_location("g1_checker", a.checker)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    specials = checker.special_ids_from(a.tokenizer)
    tok = Tokenizer.from_file(str(a.tokenizer))
    a.out.mkdir(parents=True, exist_ok=True)
    run = {
        "scope": "Data A sample-v0 integrity audit and 20-document decode; not training admission or G9 clearance",
        "repository_commit": subprocess.check_output(
            ["git", "-C", str(a.repo), "rev-parse", "HEAD"], text=True).strip(),
        "checker_sha256": sha(a.checker),
        "tokenizer_sha256": TOKENIZER_SHA,
        "special_token_count": len(specials),
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "pyarrow": pyarrow.__version__, "tokenizers": tokenizers.__version__},
        "shards": [],
    }
    for sid in SHARDS:
        start = time.perf_counter()
        manifest = json.loads((a.input / (sid + ".json")).read_text(encoding="utf-8"))
        quality = json.loads((a.input / (sid + ".quality_report.json")).read_text(encoding="utf-8"))
        rows = checker.run_checks(
            a.input, sid,
            template=a.repo / "teams/01-data-a/shards/shard_manifest_v1.template.json",
            clean_py=a.repo / "teams/01-data-a/spec_v1/clean.py",
            expect_tokenizer=TOKENIZER_SHA, special_ids=specials)

        def check(name, ok, expected, observed):
            rows.append({"check": name, "status": "PASS" if ok else "FAIL",
                         "expected": str(expected), "observed": str(observed)})

        pack = sid.rsplit("-train-", 1)[0]
        check("assigned pack and sample/train scope",
              manifest["pack_id"] == pack and manifest["split"] == "train"
              and manifest["dataset_version"] == "sample", f"{pack}, train, sample",
              f"{manifest['pack_id']}, {manifest['split']}, {manifest['dataset_version']}")
        idx = np.load(a.input / (sid + ".idx.npy"), allow_pickle=False)
        docs = pq.read_table(a.input / (sid + ".docs.parquet")).to_pydict()
        parts = sorted(set(docs["input_part"]))
        input_rows = np.array(docs["input_row"], dtype=np.int64)
        kept_ids = set(docs["doc_id"])
        excluded = [doc_id for ids in quality["left_out_docs"].values() for doc_id in ids]
        excluded = [d["doc_id"] if isinstance(d, dict) else d for d in excluded]
        check("metadata required columns", all(k in docs for k in
              ("doc_id", "input_part", "input_row", "n_tokens", "n_chars", "lang_label")),
              "all six metadata columns", sorted(docs))
        check("metadata source part belongs to assigned pack",
              len(parts) == 1 and parts[0].startswith(pack + "_part-"), pack, parts)
        check("metadata source rows ordered, unique and within rows_read",
              bool(np.all(np.diff(input_rows) > 0)) and int(input_rows[0]) >= 0
              and int(input_rows[-1]) < quality["rows_read"],
              "strictly increasing in [0, rows_read)",
              f"{int(input_rows[0])}..{int(input_rows[-1])}, {len(input_rows)} rows")
        check("metadata source-row gaps equal excluded count",
              quality["rows_read"] - len(input_rows) == len(excluded),
              len(excluded), quality["rows_read"] - len(input_rows))
        check("excluded IDs unique and absent from kept metadata",
              len(set(excluded)) == len(excluded) and not set(excluded).intersection(kept_ids),
              "unique, disjoint", f"{len(excluded)} excluded; intersection {len(set(excluded) & kept_ids)}")
        check("metadata character counts positive", all(n > 0 for n in docs["n_chars"]),
              "all > 0", min(docs["n_chars"]))
        writer = manifest["created_by"]
        on_main = subprocess.run(["git", "-C", str(a.repo), "merge-base", "--is-ancestor",
                                  writer, "HEAD"], capture_output=True).returncode == 0
        check("writer commit in audited main history", on_main, "ancestor of audited main", writer)

        decoded = decode_sample(tok, a.input, sid, idx, docs)
        check(f"decode {DECODE_N} documents: each ends with EOS {EOS_ID}",
              all(d["ends_with_eos"] for d in decoded), len(decoded), sum(d["ends_with_eos"] for d in decoded))
        check("decode: no U+FFFD replacement characters",
              all(d["replacement_chars"] == 0 for d in decoded), 0, sum(d["replacement_chars"] for d in decoded))
        check("decode: re-encoding the decoded text gives the same IDs",
              all(d["reencode_matches"] for d in decoded), len(decoded), sum(d["reencode_matches"] for d in decoded))
        check("decode: decoded length equals metadata n_chars",
              all(d["decoded_chars"] == d["n_chars"] for d in decoded), len(decoded),
              sum(d["decoded_chars"] == d["n_chars"] for d in decoded))

        artifact_hashes = {sid + suffix: sha(a.input / (sid + suffix)) for suffix in
                           (".json", ".bin", ".idx.npy", ".docs.parquet", ".quality_report.json")}
        artifact_hashes["cleaning_pipeline.json"] = sha(a.input / "cleaning_pipeline.json")
        counts = {status: sum(r["status"] == status for r in rows)
                  for status in ("PASS", "FAIL", "NOT CHECKED")}
        result = {"shard_id": sid, "manifest": manifest, "artifact_sha256": artifact_hashes,
                  "checks": rows, "counts": counts,
                  "quality_counts": {"rows_read": quality["rows_read"],
                                     "docs_in_shard": quality["docs_in_shard"],
                                     "left_out": quality["left_out"]},
                  "input_parts": parts, "input_rows": [int(input_rows[0]), int(input_rows[-1])],
                  "min_document_tokens": int(np.diff(idx).min()),
                  "max_document_tokens": int(np.diff(idx).max()),
                  "decoded_documents": decoded,
                  "wall_seconds": round(time.perf_counter() - start, 3)}
        (a.out / (sid + ".checks.json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run["shards"].append({"shard_id": sid, "counts": counts, "wall_seconds": result["wall_seconds"]})
        print(sid, counts, "seconds", result["wall_seconds"])
        for row in rows:
            if row["status"] != "PASS":
                print(row["status"], row["check"], row["observed"])
    (a.out / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return 1 if any(s["counts"]["FAIL"] for s in run["shards"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
