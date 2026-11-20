"""Check shards (shards/shard_format_v1.md) against their manifests: fields, hashes and token counts, one shard or a
whole shard folder, including the part-to-shards map of a run with rollover.

    python -I teams/01-data-a/audit/check_shard.py <folder> <shard_id> [options]      one shard
    python -I teams/01-data-a/audit/check_shard.py <folder> [options]                 every shard in <folder>, and the map

Options: --expect-tokenizer p1536, --expect-dataset-version corpus-v1, --specials-from <tokenizer.json>,
--summary <shards_summary.json> (default: the one in <folder>), --subset (the folder holds only some of the run's
shards), --json <out.json>, --verbose.

<folder> holds <shard_id>.json and whichever of the shard's files you have. In single-shard mode, an omitted file
(for example a sample bundle without payloads) is reported NOT CHECKED. Folder mode requires all files that each
present manifest names: a missing file is FAIL, including with --subset (which permits missing whole shards).
With the .bin it also checks the header, the size, every id below the vocab, an EOS at the end of every document and no
other special id.

Folder mode also checks the map run_shards.py writes to shards_summary.json (one part gives one shard or several):
every shard the summary lists is in the folder and every shard in the folder is listed; a pack's shards are numbered
000000, 000001, ... across its parts in part order; each part's shards cover its rows without a gap or an overlap
(first_row 0, each next first_row = the previous rows_read, the last rows_read = rows_in_part); the summary's docs,
tokens, rows and left-out counts are the shards' own; each shard's .docs.parquet rows come from its part, inside its
row range; no doc_id is in two shards of a pack. With --subset (an auditor's few shards), the listed shards that are
not in the folder are NOT CHECKED instead of FAIL.

It is an auditor's check, independent of the pipeline: it imports nothing from shards/ or pipeline/ (verify_shards.py
and reconcile_shards.py are the pipeline's own checks). Decoding the text is G9's
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
CLEAN_PYS = (REPO / "teams/01-data-a/spec_v1_1/clean.py", REPO / "teams/01-data-a/spec_v1/clean.py")  # v1.1 (#595), v1
SUMMARY, RECORD = "shards_summary.json", "cleaning_pipeline.json"
DEDUP_FIELDS = ("remove_list_sha256", "remove_list_rows", "overlap", "settings")  # cleaning_pipeline.json "dedup" (#56)
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


def run_checks(folder, shard_id, template=TEMPLATE, clean_pys=CLEAN_PYS, expect_tokenizer=None, special_ids=(),
               expect_dataset_version=None, require_files=False):
    """Return a list of {check, status, expected, observed}.

    expect_tokenizer: a tokenizer sha256 the shard must name (default: either frozen tokenizer).
    special_ids: extra special ids (below 130,725) that must not occur inside a document, from special_ids_from().
    expect_dataset_version: the manifest's dataset_version must be this (e.g. corpus-v1); default: only reported.
    require_files: folder audits require every manifest-listed file; single-shard partial bundles may omit them.
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
        licence = {"license", "license_source"}  # optional, both or neither: a pack table row may give neither (pack_table.py)
        missing = sorted(set(tmpl) - set(m) - (set() if licence & set(m) else licence))
        extra = sorted(set(m) - set(tmpl))
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
    dv = m.get("dataset_version")
    if expect_dataset_version:
        check(f"dataset_version is {expect_dataset_version}", dv == expect_dataset_version, expect_dataset_version, dv)
    else:
        check("dataset_version (reported, no --expect-dataset-version)", None, "", dv)
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
            check(f"{sha_key} ({p.name})", False if require_files else None, short(m[sha_key]), "file not present")
    cp = folder / "cleaning_pipeline.json"
    if cp.exists():
        got = sha(cp)
        check("cleaning_pipeline_sha256", got == m["cleaning_pipeline_sha256"], short(m["cleaning_pipeline_sha256"]), short(got))
        c = json.loads(cp.read_text())
        check("cleaning_pipeline F2 set = manifest decontam set", c.get("f2_set_sha256") == m["decontam_set_sha256"],
              short(m["decontam_set_sha256"]), short(c.get("f2_set_sha256")))
        d = c.get("dedup")
        check("cleaning_pipeline records a dedup run", isinstance(d, dict), "the dedup record (#56)", short(d) if d else d)
        if isinstance(d, dict):
            gaps = [k for k in DEDUP_FIELDS if d.get(k) is None]
            check("dedup record has remove list, overlap and settings", not gaps, "none missing", gaps or "none missing")
            codes = {"dedup": d.get("code_sha256"), "overlap": (d.get("overlap") or {}).get("code_sha256")}
            nulls = [k for k, v in codes.items() if v is None]
            check("dedup and overlap code_sha256 recorded", None if nulls else True, "both",
                  f"null for {nulls}: adopted, not run by the pipeline" if nulls else "both")
        known = {sha(p): p.relative_to(REPO).as_posix() for p in clean_pys if Path(p).exists()}
        if known:
            got = c.get("clean_py_sha256")
            check("cleaning_pipeline clean.py is a clean.py in this checkout", got in known, " or ".join(known.values()),
                  f"{known.get(got, 'none of them')} {short(got)}")
    else:
        check("cleaning_pipeline_sha256", False if require_files else None, short(m["cleaning_pipeline_sha256"]), "file not present")

    # 3. Index and token counts
    idx = None
    ip = folder / Path(m["index_uri"]).name
    if ip.exists():
        try:
            idx = np.load(ip, allow_pickle=False)
        except (ValueError, EOFError, OSError) as exc:
            check("index can be read", False, "readable .npy", f"{type(exc).__name__}: {exc}")
    if idx is not None:
        valid = isinstance(idx, np.ndarray) and idx.ndim == 1 and idx.dtype == np.int64
        check("index is a one-dimensional int64 array", valid, "1D int64", f"shape={getattr(idx, 'shape', None)}, dtype={getattr(idx, 'dtype', None)}")
        if not valid:
            idx = None
    if idx is not None:
        lens = np.diff(idx)
        check("index dtype int64", idx.dtype == np.int64, "int64", idx.dtype)
        check("index length = doc_count + 1", len(idx) == dc + 1, dc + 1, len(idx))
        check("index starts at 0", len(idx) > 0 and int(idx[0]) == 0, 0, int(idx[0]) if len(idx) else "empty")
        check("index ends at token_count", len(idx) > 0 and int(idx[-1]) == tc, tc, int(idx[-1]) if len(idx) else "empty")
        check("every document has >= 2 tokens (text + EOS)", bool(len(lens)) and bool((lens >= 2).all()), ">= 2",
              int(lens.min()) if len(lens) else "no docs")
        check("document lengths sum to token_count", int(lens.sum()) == tc, tc, int(lens.sum()))
        check("shard within 2^26 tokens, or one document", tc <= 2**26 or dc == 1, "<= 67108864", tc)
    elif not ip.exists():
        check("index checks", None, "", "index not present")

    qp = folder / Path(m["quality_report_uri"]).name
    if qp.exists():
        q = json.loads(qp.read_text())
        left = q.get("left_out", {})
        lists = {k: len(v) for k, v in q.get("left_out_docs", {}).items()}
        check("quality report shard_id", q.get("shard_id") == shard_id, shard_id, q.get("shard_id"))
        check("quality report docs_in_shard = doc_count", q.get("docs_in_shard") == dc, dc, q.get("docs_in_shard"))
        first = q.get("first_row", 0)  # a part's later shards (rollover) start past row 0; older reports have no first_row
        check("rows_read - first_row = docs_in_shard + left out",
              q.get("rows_read", 0) - first == q.get("docs_in_shard", 0) + sum(left.values()),
              first + q.get("docs_in_shard", 0) + sum(left.values()), q.get("rows_read"))
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
        if (idx is not None and len(idx) > 1 and len(toks) == tc and int(idx[-1]) == tc
                and bool((idx[1:] > 0).all()) and bool((idx[1:] <= len(toks)).all())):
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
        cols = pq.read_schema(mp).names
        t = pq.read_table(mp, columns=[c for c in ("doc_id", "n_tokens", "input_part", "input_row") if c in cols]).to_pydict()
        n = len(t["doc_id"])
        check("docs.parquet rows = doc_count", n == dc, dc, n)
        check("docs.parquet doc_ids unique", len(set(t["doc_id"])) == n, n, len(set(t["doc_id"])))
        if idx is not None:
            same = [int(x) for x in np.diff(idx)] == [int(x) for x in t["n_tokens"]]
            check("docs.parquet n_tokens = index lengths", same, "equal", "equal" if same else "differ")
        if "input_part" in t and n:
            parts = sorted(set(t["input_part"]))
            want = (q.get("upstream") or {}).get("input_part") if qp.exists() else None
            check("docs.parquet rows come from one input part", len(parts) == 1 and (want is None or parts == [want]),
                  want or "one part", parts if len(parts) > 1 else parts[0])
        if "input_row" in t and n and qp.exists() and "first_row" in q:
            r = np.asarray(t["input_row"], dtype=np.int64)
            ok = bool((np.diff(r) > 0).all()) and int(r[0]) >= q["first_row"] and int(r[-1]) < q["rows_read"]
            check("docs.parquet input_row increasing, inside first_row..rows_read-1", ok,
                  f"{q['first_row']}..{q['rows_read'] - 1}", f"{int(r.min())}..{int(r.max())}")
    else:
        check(".docs.parquet checks", None, "", ".docs.parquet not present")
    return rows


def shard_ids_in(folder):
    """The shard_ids of the shard manifests in a folder (a .json with a schema_version; not the summary or record)."""
    ids = []
    for p in sorted(Path(folder).glob("*.json")):
        if p.name in (SUMMARY, RECORD) or p.name.endswith(".quality_report.json"):
            continue
        try:
            if "schema_version" in json.loads(p.read_text(encoding="utf-8")):
                ids.append(p.stem)
        except ValueError:
            continue
    return ids


def run_map_checks(folder, summary, subset=False):
    """Check the part-to-shards map of shards_summary.json (run_shards.py) against the shard files in folder.

    summary: the summary as a dict. subset: the folder holds only some of the run's shards, so a listed shard that is not
    there is NOT CHECKED, not FAIL. Returns a list of {check, status, expected, observed}; check names start with the
    part or pack they are about."""
    folder = Path(folder)
    rows = []

    def check(name, ok, expected="", observed=""):
        status = PASS if ok is True else FAIL if ok is False else NOT_CHECKED
        rows.append({"check": name, "status": status, "expected": str(expected), "observed": str(observed)})

    def load(sid, suffix):
        p = folder / f"{sid}{suffix}"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    parts = summary.get("parts", {})
    present = set(shard_ids_in(folder))
    statuses = {}
    for name, e in parts.items():
        statuses[e.get("status")] = statuses.get(e.get("status"), 0) + 1
    bad = {k: v for k, v in statuses.items() if k in ("failed", "skipped")}
    check("run: no part failed or skipped", not bad, "0", bad or "0")
    counts = summary.get("counts", {})
    listed_counts = {k: statuses.get(k, 0) for k in ("written", "empty", "all_left_out", "failed", "skipped", "not_sharded")}
    check("run: summary counts = its parts", all(counts.get(k) == v for k, v in listed_counts.items()), listed_counts,
          {k: counts.get(k) for k in listed_counts})
    check("run: run_shards verified the folder", summary.get("verified") is True if summary.get("verified") is not None else None,
          True, summary.get("verified"))
    check("run: no run-level problems", not summary.get("problems"), "[]", summary.get("problems") or "[]")
    rec = folder / RECORD
    if rec.exists():
        check("run: cleaning_pipeline.json sha256 = the summary's", sha(rec) == summary.get("cleaning_pipeline_sha256"),
              str(summary.get("cleaning_pipeline_sha256"))[:16], sha(rec)[:16])

    listed = {}  # shard_id -> part name
    by_pack = {}  # (split, pack) -> shard ids in part order
    for name in sorted(parts):
        e = parts[name]
        if e.get("status") != "written":
            continue
        split, pack = name.split("/")[0], e.get("pack_id") or name.split("/")[1]
        shards = e.get("shards", [])
        by_pack.setdefault((split, pack), []).extend(x["shard_id"] for x in shards)
        for x in shards:
            listed[x["shard_id"]] = name
        check(f"{name}: has a shard", bool(shards), ">= 1", len(shards))
        if not shards:
            continue
        chain = [(x["first_row"], x["rows_read"]) for x in shards]
        gaps = [i for i in range(1, len(chain)) if chain[i][0] != chain[i - 1][1]]
        ok = chain[0][0] == 0 and not gaps and all(a < b for a, b in chain)
        check(f"{name}: shards cover its rows with no gap or overlap", ok, "0, then first_row = previous rows_read",
              chain if not ok else f"0..{chain[-1][1] - 1} in {len(chain)} shard(s)")
        check(f"{name}: last rows_read = rows_read = rows_in_part, not truncated",
              chain[-1][1] == e.get("rows_read") == e.get("rows_in_part") and e.get("truncated") is False,
              e.get("rows_in_part"), f"{chain[-1][1]}, {e.get('rows_read')}, truncated={e.get('truncated')}")
        check(f"{name}: docs and tokens = the sum over its shards",
              e.get("docs") == sum(x["docs"] for x in shards) and e.get("tokens") == sum(x["tokens"] for x in shards),
              f"{sum(x['docs'] for x in shards)} docs, {sum(x['tokens'] for x in shards)} tokens",
              f"{e.get('docs')} docs, {e.get('tokens')} tokens")

        mine = [x for x in shards if x["shard_id"] in present]
        if len(mine) < len(shards):
            missing = [x["shard_id"] for x in shards if x["shard_id"] not in present]
            check(f"{name}: every listed shard is in the folder", None if subset else False, "all", f"missing {missing}")
        left = {}
        for x in mine:
            sid, m, q = x["shard_id"], load(x["shard_id"], ".json"), load(x["shard_id"], ".quality_report.json")
            check(f"{name}: {sid} docs/tokens = its manifest", (x["docs"], x["tokens"]) == (m.get("doc_count"), m.get("token_count")),
                  f"{x['docs']}, {x['tokens']}", f"{m.get('doc_count')}, {m.get('token_count')}")
            if q is None:
                check(f"{name}: {sid} rows = its quality report", None, "", "quality report not present")
                continue
            check(f"{name}: {sid} rows = its quality report", (x["first_row"], x["rows_read"]) == (q.get("first_row"), q.get("rows_read")),
                  f"{x['first_row']}..{x['rows_read']}", f"{q.get('first_row')}..{q.get('rows_read')}")
            for k, v in q.get("left_out", {}).items():
                left[k] = left.get(k, 0) + v
        if len(mine) == len(shards):
            want = {k: v for k, v in e.get("left_out", {}).items()}
            check(f"{name}: left-out counts = the sum over its shards' reports", left == want, want, left)
        else:
            check(f"{name}: left-out counts = the sum over its shards' reports", None, "", "not every shard present")

    orphans = sorted(present - set(listed))
    check("folder: every shard is listed in the summary", not orphans, "none unlisted", orphans or "none unlisted")
    for (split, pack), ids in sorted(by_pack.items()):
        want = [f"{pack}-{split}-{k:06d}" for k in range(len(ids))]
        check(f"{split}/{pack}: shards numbered from 000000 across its parts, in part order", ids == want,
              f"{want[0]}..{want[-1]}" if want else "-", ids if ids != want else f"{ids[0]}..{ids[-1]}")
        seen, dup = set(), 0
        import pyarrow.parquet as pq
        for sid in ids:
            p = folder / f"{sid}.docs.parquet"
            if p.exists():
                got = pq.read_table(p, columns=["doc_id"]).column(0).to_pylist()
                dup += len(seen.intersection(got))
                seen.update(got)
        check(f"{split}/{pack}: no doc_id in two of its shards", dup == 0 if seen else None, 0, dup if seen else "no .docs.parquet")
    return rows


def print_rows(rows, verbose):
    w = max((len(r["check"]) for r in rows), default=0)
    for r in rows:
        if verbose or r["status"] != PASS:
            print(f"{r['status']:<12} {r['check']:<{w}}  expected={r['expected']}  observed={r['observed']}")


def tally(rows):
    return {s: sum(r["status"] == s for r in rows) for s in (PASS, FAIL, NOT_CHECKED)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("shard_id", nargs="?", help="one shard; leave out to check every shard in the folder and the map")
    ap.add_argument("--json", type=Path, help="also write the results here")
    ap.add_argument("--expect-tokenizer", choices=["p1536", "C3"],
                    help="the frozen tokenizer the shard must name (default: either)")
    ap.add_argument("--expect-dataset-version", help="the dataset_version every manifest must name, e.g. corpus-v1")
    ap.add_argument("--specials-from", type=Path, metavar="TOKENIZER_JSON",
                    help="a tokenizer.json to read the special ids from (p1536 or C3: the same special ids)")
    ap.add_argument("--summary", type=Path, help=f"run_shards.py's summary (default: <folder>/{SUMMARY}, if there)")
    ap.add_argument("--subset", action="store_true", help="the folder holds only some of the run's shards")
    ap.add_argument("--verbose", action="store_true", help="print every check, not only the ones that did not pass")
    a = ap.parse_args(argv)
    expect = {v: k for k, v in FROZEN_TOKENIZERS.items()}.get(a.expect_tokenizer)
    specials = special_ids_from(a.specials_from) if a.specials_from else ()
    kw = dict(expect_tokenizer=expect, special_ids=specials, expect_dataset_version=a.expect_dataset_version)

    if a.shard_id:  # one shard, as before: every check printed
        rows = run_checks(a.folder, a.shard_id, **kw)
        print_rows(rows, True)
        counts = tally(rows)
        print(counts)
        if a.json:
            a.json.write_text(json.dumps({"shard_id": a.shard_id, "checks": rows, "counts": counts}, indent=2) + "\n")
        return 1 if counts[FAIL] else 0

    ids = shard_ids_in(a.folder)
    if not ids:
        print(f"no shard manifest in {a.folder}")
        return 1
    result, total = {"shards": {}, "map": None}, {PASS: 0, FAIL: 0, NOT_CHECKED: 0}
    for sid in ids:
        rows = run_checks(a.folder, sid, require_files=True, **kw)
        counts = tally(rows)
        result["shards"][sid] = {"checks": rows, "counts": counts}
        print(f"{sid}: {counts[PASS]} PASS, {counts[FAIL]} FAIL, {counts[NOT_CHECKED]} NOT CHECKED")
        print_rows(rows, a.verbose)
        for k in total:
            total[k] += counts[k]
    summary_path = a.summary or a.folder / SUMMARY
    if summary_path.exists():
        rows = run_map_checks(a.folder, json.loads(summary_path.read_text(encoding="utf-8")), subset=a.subset)
        counts = tally(rows)
        result["map"] = {"summary": str(summary_path), "checks": rows, "counts": counts}
        print(f"map ({summary_path.name}): {counts[PASS]} PASS, {counts[FAIL]} FAIL, {counts[NOT_CHECKED]} NOT CHECKED")
        print_rows(rows, a.verbose)
        for k in total:
            total[k] += counts[k]
    else:
        print(f"map: NOT CHECKED, no {SUMMARY} (give --summary)")
        total[NOT_CHECKED] += 1
    print(f"{len(ids)} shard(s): {total}")
    if a.json:
        result["counts"] = total
        a.json.write_text(json.dumps(result, indent=2) + "\n")
    return 1 if total[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
