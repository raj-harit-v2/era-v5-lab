"""Check one shard (shards/shard_format_v1.md) against its manifest: fields, hashes and token counts.

    python -I teams/01-data-a/audit/check_shard.py <folder> <shard_id> [--json <out.json>]

<folder> holds <shard_id>.json and whichever of the shard's files you have. A file that is not there (for example the
.bin and .docs.parquet of the sample shard, which pr-guard keeps out of git) is reported NOT CHECKED, never PASS.
With the .bin it also checks the header, the size, every id below the vocab, an EOS at the end of every document and no
other special id. Decoding the text and the decontamination check are G9's
teams/09-evaluation/decontam/decode_shard.py. Prints IDs, counts and hashes only, never document text.
Exit code 1 when a check fails. Needs numpy, and pyarrow for the .docs.parquet.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "teams/01-data-a/shards/shard_manifest_v1.template.json"
CLEAN_PY = REPO / "teams/01-data-a/spec_v1/clean.py"
P1536_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"  # Gate 3 freeze, #504
C3_SHA256 = "15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3"  # earlier freeze, #340 (sample shard)
FROZEN_TOKENIZERS = {P1536_SHA256: "p1536", C3_SHA256: "C3"}
F2_V2_SHA256 = "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"  # G9 fingerprints v2
EOS_ID, VOCAB, SPECIAL_LO = 130_822, 131_072, 130_725  # SPECIAL_LO..VOCAB-1: G3's special and reserved ids
HEADER_BYTES, MAGIC, VERSION = 1024, 20261025, 2
CHUNK = 1 << 22  # tokens read at a time from the .bin (16 MiB)
PASS, FAIL, NOT_CHECKED = "PASS", "FAIL", "NOT CHECKED"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def special_ids_from(tokenizer_json):
    """Ids of the added tokens marked special in a tokenizer.json (p1536 and C3 have the same ones, G3 #504)."""
    data = json.loads(Path(tokenizer_json).read_text(encoding="utf-8"))
    return sorted(t["id"] for t in data.get("added_tokens", []) if t.get("special"))


def run_checks(folder, shard_id, template=TEMPLATE, clean_py=CLEAN_PY, expect_tokenizer=None, special_ids=()):
    """Return a list of {check, status, expected, observed}.

    expect_tokenizer: a tokenizer sha256 the shard must name (default: either frozen tokenizer).
    special_ids: extra special ids (below 130,725) that must not occur inside a document, from special_ids_from().
    """
    folder = Path(folder)
    rows = []

    def check(name, ok, expected="", observed=""):
        status = PASS if ok is True else FAIL if ok is False else NOT_CHECKED
        rows.append({"check": name, "status": status, "expected": str(expected), "observed": str(observed)})

    def short(v):
        return str(v)[:16]

    man_path = folder / f"{shard_id}.json"
    m = json.loads(man_path.read_text())
    check("manifest file sha256 (recorded)", True, "", sha(man_path))
    tc, dc = m.get("token_count"), m.get("doc_count")

    # 1. Manifest fields
    if Path(template).exists():
        tmpl = json.loads(Path(template).read_text())
        missing, extra = sorted(set(tmpl) - set(m)), sorted(set(m) - set(tmpl))
        check("all template fields present", not missing, "none missing", missing or "none missing")
        check("no fields outside the template", not extra, "none extra", extra or "none extra")
    empty = [k for k, v in m.items() if v in ("", None) or (isinstance(v, str) and v.startswith("<"))]
    check("no empty or placeholder values", not empty, "none", empty or "none")
    check("schema_version", m.get("schema_version") == "shard-v1", "shard-v1", m.get("schema_version"))
    check("format", m.get("format") == "brahmic_u32_v2+doc_index", "brahmic_u32_v2+doc_index", m.get("format"))
    check("token_dtype", m.get("token_dtype") == "uint32", "uint32", m.get("token_dtype"))
    check("eos_token_id", m.get("eos_token_id") == EOS_ID, EOS_ID, m.get("eos_token_id"))
    tok = m.get("tokenizer_sha256")
    want = FROZEN_TOKENIZERS.get(expect_tokenizer) if expect_tokenizer else None
    if expect_tokenizer:
        check(f"tokenizer_sha256 is {want or expect_tokenizer[:12]}", tok == expect_tokenizer, short(expect_tokenizer), short(tok))
    else:
        check("tokenizer_sha256 is a frozen tokenizer (p1536 or C3)", tok in FROZEN_TOKENIZERS, "p1536 or C3",
              f"{FROZEN_TOKENIZERS.get(tok, 'unknown')} {short(tok)}")
    check("decontam_set_sha256 is F2 v2", m.get("decontam_set_sha256") == F2_V2_SHA256, short(F2_V2_SHA256), short(m.get("decontam_set_sha256")))
    check("split is train or validation", m.get("split") in ("train", "validation"), "train|validation", m.get("split"))
    id_ok = re.fullmatch(rf"{re.escape(str(m.get('pack_id')))}-{re.escape(str(m.get('split')))}-\d{{6}}", shard_id)
    check("shard_id = <pack_id>-<split>-<6 digits>", bool(id_ok) and m.get("shard_id") == shard_id,
          f"{m.get('pack_id')}-{m.get('split')}-NNNNNN", m.get("shard_id"))
    writer = str(m.get("created_by"))
    check("created_by is a full git commit hash", bool(re.fullmatch(r"[0-9a-f]{40}", writer)), "40 hex characters",
          writer[:12] if re.fullmatch(r"[0-9a-f]{40}", writer) else writer)
    if isinstance(tc, int):
        check("payload_bytes = 1024 + 4 x token_count", m.get("payload_bytes") == HEADER_BYTES + 4 * tc,
              HEADER_BYTES + 4 * tc, m.get("payload_bytes"))

    # 2. Hashes of every file the manifest names
    for uri_key, sha_key in [("payload_uri", "payload_sha256"), ("index_uri", "index_sha256"),
                             ("sample_metadata_uri", "sample_metadata_sha256"),
                             ("quality_report_uri", "quality_report_sha256")]:
        p = folder / Path(m[uri_key]).name
        if p.exists():
            got = sha(p)
            check(f"{sha_key} ({p.name})", got == m[sha_key], short(m[sha_key]), short(got))
        else:
            check(f"{sha_key} ({p.name})", None, short(m[sha_key]), "file not present")
    cp = folder / "cleaning_pipeline.json"
    if cp.exists():
        got = sha(cp)
        check("cleaning_pipeline_sha256", got == m["cleaning_pipeline_sha256"], short(m["cleaning_pipeline_sha256"]), short(got))
        c = json.loads(cp.read_text())
        check("cleaning_pipeline F2 set = manifest decontam set", c.get("f2_set_sha256") == m["decontam_set_sha256"],
              short(m["decontam_set_sha256"]), short(c.get("f2_set_sha256")))
        check("cleaning_pipeline records a dedup version", c.get("dedup") is not None, "a dedup version", c.get("dedup"))
        if Path(clean_py).exists():
            cur = sha(clean_py)
            check("cleaning_pipeline clean.py = clean.py in this checkout", cur == c.get("clean_py_sha256"),
                  short(c.get("clean_py_sha256")), short(cur))
    else:
        check("cleaning_pipeline_sha256", None, short(m["cleaning_pipeline_sha256"]), "file not present")

    # 3. Index and token counts
    idx = None
    ip = folder / Path(m["index_uri"]).name
    if ip.exists():
        idx = np.load(ip, allow_pickle=False)
        lens = np.diff(idx)
        check("index dtype int64", idx.dtype == np.int64, "int64", idx.dtype)
        check("index length = doc_count + 1", len(idx) == dc + 1, dc + 1, len(idx))
        check("index starts at 0", len(idx) > 0 and int(idx[0]) == 0, 0, int(idx[0]) if len(idx) else "empty")
        check("index ends at token_count", len(idx) > 0 and int(idx[-1]) == tc, tc, int(idx[-1]) if len(idx) else "empty")
        check("every document has >= 2 tokens (text + EOS)", bool(len(lens)) and bool((lens >= 2).all()), ">= 2",
              int(lens.min()) if len(lens) else "no docs")
        check("document lengths sum to token_count", int(lens.sum()) == tc, tc, int(lens.sum()))
        check("shard within 2^26 tokens, or one document", tc <= 2**26 or dc == 1, "<= 67108864", tc)
    else:
        check("index checks", None, "", "index not present")

    qp = folder / Path(m["quality_report_uri"]).name
    if qp.exists():
        q = json.loads(qp.read_text())
        left = q.get("left_out", {})
        lists = {k: len(v) for k, v in q.get("left_out_docs", {}).items()}
        check("quality report shard_id", q.get("shard_id") == shard_id, shard_id, q.get("shard_id"))
        check("quality report docs_in_shard = doc_count", q.get("docs_in_shard") == dc, dc, q.get("docs_in_shard"))
        check("rows_read = docs_in_shard + left out", q.get("rows_read") == q.get("docs_in_shard", 0) + sum(left.values()),
              q.get("docs_in_shard", 0) + sum(left.values()), q.get("rows_read"))
        check("left_out counts = left_out_docs lists", lists == left, left, lists)

    # 4. The .bin itself
    bp = folder / Path(m["payload_uri"]).name
    if bp.exists():
        size = bp.stat().st_size
        check(".bin size = payload_bytes", size == m["payload_bytes"], m["payload_bytes"], size)
        head = np.fromfile(bp, dtype="<i4", count=HEADER_BYTES // 4)
        check(".bin header magic", int(head[0]) == MAGIC, MAGIC, int(head[0]))
        check(".bin header version", int(head[1]) == VERSION, VERSION, int(head[1]))
        check(".bin header token count", int(head[2]) == tc, tc, int(head[2]))
        check(".bin header rest is zeros", not head[3:].any(), "zeros", "zeros" if not head[3:].any() else "non-zero")
        toks = np.memmap(bp, dtype="<u4", mode="r", offset=HEADER_BYTES)
        check("tokens after the header = token_count", len(toks) == tc, tc, len(toks))
        # One pass in fixed-size chunks, so memory stays flat whatever the shard size: a lookup table over the
        # vocab marks each id 0 (ordinary), 1 (special below SPECIAL_LO) or 2 (SPECIAL_LO and above, or outside
        # the vocab), and bincount counts the marks. No copy of the tokens and no np.isin.
        low = sorted({int(i) for i in special_ids if i < SPECIAL_LO})
        lut = np.zeros(VOCAB, dtype=np.uint8)
        lut[low] = 1
        lut[SPECIAL_LO:] = 2
        top, marks = 0, np.zeros(3, dtype=np.int64)
        clipped = np.empty(min(CHUNK, len(toks)), dtype="<u4")
        for start in range(0, len(toks), CHUNK):
            chunk = toks[start:start + CHUNK]
            top = max(top, int(chunk.max()))
            np.minimum(chunk, VOCAB - 1, out=clipped[:len(chunk)])  # an id outside the vocab counts as mark 2
            marks += np.bincount(lut[clipped[:len(chunk)]], minlength=3)
        check("every id < vocab 131072", top < VOCAB, f"< {VOCAB}", top)
        if idx is not None and len(toks) == tc and int(idx[-1]) == tc:
            ends = idx[1:] - 1
            last = np.asarray(toks[ends])
            n_eos = int((last == EOS_ID).sum())
            check("every document ends with EOS", n_eos == dc, dc, n_eos)
            # A special id is allowed only at a document's last position, and only EOS there (checked above), so
            # the marks inside documents are all marks minus the marks at the last positions.
            inside = marks - np.bincount(lut[np.minimum(last, VOCAB - 1)], minlength=3)
            n_inside = int(inside[2])
            check(f"no special id >= {SPECIAL_LO} inside a document", n_inside == 0, 0, n_inside)
            if low:
                n_low = int(inside[1])
                check(f"none of the {len(low)} special ids below {SPECIAL_LO} inside a document", n_low == 0, 0, n_low)
            else:
                check(f"special ids below {SPECIAL_LO} inside a document", None, "", "no --specials-from tokenizer given")
    else:
        check(".bin checks (size, header, ids, EOS)", None, "", ".bin not present")

    mp = folder / Path(m["sample_metadata_uri"]).name
    if mp.exists():
        import pyarrow.parquet as pq
        t = pq.read_table(mp, columns=["doc_id", "n_tokens"]).to_pydict()
        n = len(t["doc_id"])
        check("docs.parquet rows = doc_count", n == dc, dc, n)
        check("docs.parquet doc_ids unique", len(set(t["doc_id"])) == n, n, len(set(t["doc_id"])))
        if idx is not None:
            same = [int(x) for x in np.diff(idx)] == [int(x) for x in t["n_tokens"]]
            check("docs.parquet n_tokens = index lengths", same, "equal", "equal" if same else "differ")
    else:
        check(".docs.parquet checks", None, "", ".docs.parquet not present")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("shard_id")
    ap.add_argument("--json", type=Path, help="also write the results here")
    ap.add_argument("--expect-tokenizer", choices=["p1536", "C3"],
                    help="the frozen tokenizer the shard must name (default: either)")
    ap.add_argument("--specials-from", type=Path, metavar="TOKENIZER_JSON",
                    help="a tokenizer.json to read the special ids from (p1536 or C3: the same special ids)")
    a = ap.parse_args(argv)
    expect = {v: k for k, v in FROZEN_TOKENIZERS.items()}.get(a.expect_tokenizer)
    specials = special_ids_from(a.specials_from) if a.specials_from else ()
    rows = run_checks(a.folder, a.shard_id, expect_tokenizer=expect, special_ids=specials)
    w = max(len(r["check"]) for r in rows)
    for r in rows:
        print(f"{r['status']:<12} {r['check']:<{w}}  expected={r['expected']}  observed={r['observed']}")
    counts = {s: sum(r["status"] == s for r in rows) for s in (PASS, FAIL, NOT_CHECKED)}
    print(counts)
    if a.json:
        a.json.write_text(json.dumps({"shard_id": a.shard_id, "checks": rows, "counts": counts}, indent=2) + "\n")
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
