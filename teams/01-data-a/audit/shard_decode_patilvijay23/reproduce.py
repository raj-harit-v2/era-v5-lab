"""Decode 20 deterministic documents per assigned shard; publish hashes, never text."""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pyarrow
import pyarrow.parquet as pq
import tokenizers

TOKENIZER_SHA = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
SHARDS = ("en-dclm-train-000000", "math-megamath-train-000000")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require(ok, name):
    if not ok:
        raise ValueError(name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    require(sha(a.tokenizer) == TOKENIZER_SHA, "wrong tokenizer bytes")
    tok = tokenizers.Tokenizer.from_file(str(a.tokenizer))
    require(tok.get_vocab_size(with_added_tokens=True) == 131072, "vocabulary size")
    require(tok.token_to_id("<|endoftext|>") == 130822, "EOS ID")
    run = {
        "scope": "Core task 6: decode 20 documents per assigned p1536 sample-v0 shard",
        "tokenizer_sha256": TOKENIZER_SHA,
        "sampling": "document index i * (doc_count - 1) // 19 for i=0..19",
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "pyarrow": pyarrow.__version__, "tokenizers": tokenizers.__version__},
        "repository_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip(),
        "shards": [],
    }
    a.out.mkdir(parents=True, exist_ok=True)
    for sid in SHARDS:
        m = json.loads((a.input / (sid + ".json")).read_text())
        require(m["shard_id"] == sid and m["dataset_version"] == "sample"
                and m["split"] == "train" and m["pack_id"] == sid.rsplit("-train-", 1)[0], "assignment/scope")
        require(m["tokenizer_sha256"] == TOKENIZER_SHA and m["eos_token_id"] == 130822, "manifest tokenizer/EOS")
        hashes = {sid + ".json": sha(a.input / (sid + ".json"))}
        for uri, field in (("payload_uri", "payload_sha256"), ("index_uri", "index_sha256"),
                           ("sample_metadata_uri", "sample_metadata_sha256"),
                           ("quality_report_uri", "quality_report_sha256")):
            name = Path(m[uri]).name
            hashes[name] = sha(a.input / name)
            require(hashes[name] == m[field], field)
        hashes["cleaning_pipeline.json"] = sha(a.input / "cleaning_pipeline.json")
        require(hashes["cleaning_pipeline.json"] == m["cleaning_pipeline_sha256"], "cleaning pipeline hash")
        bp = a.input / (sid + ".bin")
        require(bp.stat().st_size == m["payload_bytes"] == 1024 + 4 * m["token_count"], "payload size")
        header = np.fromfile(bp, dtype="<i4", count=256)
        require(header[:3].tolist() == [20261025, 2, m["token_count"]] and not header[3:].any(), "header")
        idx = np.load(a.input / (sid + ".idx.npy"), allow_pickle=False)
        require(idx.dtype == np.int64 and idx.ndim == 1 and len(idx) == m["doc_count"] + 1
                and int(idx[0]) == 0 and int(idx[-1]) == m["token_count"]
                and bool(np.all(np.diff(idx) > 0)), "index")
        docs = pq.read_table(a.input / (sid + ".docs.parquet")).to_pydict()
        require(len(docs["doc_id"]) == m["doc_count"]
                and np.diff(idx).tolist() == docs["n_tokens"], "metadata counts")
        require(m["doc_count"] >= 20, "fewer than 20 documents")
        toks = np.memmap(bp, dtype="<u4", mode="r", offset=1024)
        selected = [i * (m["doc_count"] - 1) // 19 for i in range(20)]
        sample = []
        for i in selected:
            begin, end = int(idx[i]), int(idx[i + 1])
            ids = toks[begin:end - 1].tolist()
            text = tok.decode(ids, skip_special_tokens=False)
            normalized = tok.normalizer.normalize_str(text) if tok.normalizer else text
            sample.append({
                "shard_document_index": i, "doc_id": docs["doc_id"][i],
                "input_part": docs["input_part"][i], "input_row": docs["input_row"][i],
                "token_start": begin, "token_end_exclusive": end, "n_tokens_with_eos": end - begin,
                "metadata_n_chars": docs["n_chars"][i], "decoded_n_chars": len(text),
                "decoded_utf8_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "nonempty": bool(text), "eos_at_end": int(toks[end - 1]) == 130822,
                "normalized": normalized == text,
                "roundtrip_ids_equal": tok.encode(text, add_special_tokens=False).ids == ids,
            })
        passed = sum(d["nonempty"] and d["eos_at_end"] and d["normalized"]
                     and d["roundtrip_ids_equal"] for d in sample)
        result = {"shard_id": sid, "pack_id": m["pack_id"], "doc_count": m["doc_count"],
                  "token_count": m["token_count"], "tokenizer_sha256": TOKENIZER_SHA,
                  "artifact_sha256": hashes, "sampling": run["sampling"],
                  "decoded": 20, "passed": passed, "documents": sample}
        (a.out / (sid + ".decode.json")).write_text(json.dumps(result, indent=2) + "\n")
        run["shards"].append({"shard_id": sid, "decoded": 20, "passed": passed})
        print(sid, f"{passed}/20 decoded, normalized and exact token round-trip")
    (a.out / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    return 0 if all(s["passed"] == 20 for s in run["shards"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
