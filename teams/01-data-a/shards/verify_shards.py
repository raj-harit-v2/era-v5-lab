"""Check the shards in a folder against the files on disk, not against shards_summary.json alone.

  python -I teams/01-data-a/shards/verify_shards.py --out <shards dir> --manifest <run>/pipeline_manifest.json \
      --tokenizer <c3>/tokenizer.json [--pack-table pack_table.json]

verify() looks at every shard manifest (<shard_id>.json) in --out and returns the problems it found (an empty list: all
good) and the sha256 of the big files it read, so a caller does not have to hash them again.

For each shard:
  files      payload (.bin), index (.idx.npy), sample metadata (.docs.parquet), quality report, dump and the run's
             cleaning_pipeline.json exist; their sha256 are the manifest's (cleaning_pipeline.json: also the run's own copy)
  format     the manifest has every field of shard_manifest_v1.template.json and the fixed ones are right; the .bin header
             (magic, version, token count) and size agree with the manifest (1,024 + 4 x token_count); the index is int64,
             strictly increasing, from 0 to token_count, doc_count + 1 entries; every id is below the vocabulary; the only
             special ids are the EOS at the end of each document; the metadata has doc_count rows and n_tokens = the index steps
  pack       language, script, domain and capability_lane are the pack's row in pack_table.json
  run        the tokenizer is the one given, the F2 fingerprint set is the pipeline manifest's
  content    (skipped when the folder's cleaning_pipeline.json is not the run's own: other processing, other final data)
             the first and the last document of the shard: its row in the run's final part (found by input_part and
             input_row) has the doc_id the metadata says, its text encodes to the tokens in the .bin, followed by EOS, and
             decodes back to the normalized text. Checking every document is the writer's job; this ties the .bin to the
             final data at two points
With a summary (shards_summary.json in --out): the shards it lists as written are the shards in --out, with its docs and
tokens. Needs numpy, pyarrow and tokenizers (no torch).
"""
import sys
sys.dont_write_bytecode = True

import argparse, hashlib, json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pack_table  # noqa: E402

MAGIC, VERSION, HEADER_BYTES = 20261025, 2, 1024  # G6's .bin header: magic, version, token count (256 little-endian int32)
VOCAB = 131_072
EOS_ID, EOS = 130_822, "<|endoftext|>"
SPECIAL_BLOCK = range(130_725, VOCAB)  # G3: named specials and reserved slots; plus every added token marked special
SUMMARY, RECORD = "shards_summary.json", "cleaning_pipeline.json"
TEMPLATE = HERE / "shard_manifest_v1.template.json"
CHUNK = 1 << 24  # tokens looked at per step: a full shard is 2^26 tokens


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def special_ids(tok):
    """Every id that may not occur inside a document: the added tokens marked special, and G3's block of specials."""
    return {i for i, t in tok.get_added_tokens_decoder().items() if t.special} | set(SPECIAL_BLOCK)


def summary_shards(summary):
    """{shard_id: its entry in its part's "shards" list (docs, tokens, rows)} of the parts the summary calls written; a part
    has one shard or several (rollover). The only place that knows the summary's layout."""
    return {x["shard_id"]: x for e in summary.get("parts", {}).values() if e.get("status") == "written" for x in e.get("shards", [])}


def read_row(path, row):
    """(doc_id, text) of one row of a Parquet file, reading only the row group that holds it; None if the row is not there."""
    pf = pq.ParquetFile(path)
    start = 0
    for g in range(pf.num_row_groups):
        n = pf.metadata.row_group(g).num_rows
        if row < start + n:
            t = pf.read_row_group(g, columns=["doc_id", "text"])
            return t.column("doc_id")[row - start].as_py(), t.column("text")[row - start].as_py()
        start += n
    return None


def check_shard(out, sid, m, ctx, bad, hashes):
    """The checks of one shard (see the docstring). bad(sid, message) records a problem; hashes gets {file name: sha256}."""
    lacking = sorted(ctx["keys"] - set(m))  # without the licence fields: they are checked against the pack table below
    if lacking:
        return bad(sid, f"the manifest lacks {', '.join(lacking)}")
    for field, want in (("shard_id", sid), ("schema_version", "shard-v1"), ("format", "brahmic_u32_v2+doc_index"),
                        ("token_dtype", "uint32"), ("eos_token_id", EOS_ID)):
        if m[field] != want:
            bad(sid, f"{field} is {m[field]!r}, expected {want!r}")
    if m["split"] not in ("train", "validation") or not sid.startswith(f"{m['pack_id']}-{m['split']}-"):
        bad(sid, f"the shard id does not start with its pack and split ({m['pack_id']}-{m['split']}-)")
    try:
        row = pack_table.row(m["pack_id"], ctx["table"])
    except pack_table.PackTableError as e:
        bad(sid, str(e))
    else:
        for field, key in (("language", "language"), ("script", "script"), ("domain", "domain"), ("capability_lane", "lane")):
            if m[field] != row[key]:
                bad(sid, f"{field} is {m[field]!r}, pack_table.json says {row[key]!r} for {m['pack_id']}")
        for field in pack_table.LICENCE:  # both in the manifest when the table gives them, neither when it does not
            if m.get(field) != row.get(field):
                bad(sid, f"{field} is {m.get(field)!r}, the pack table says {row.get(field)!r} for {m['pack_id']}")
    if m["tokenizer_sha256"] != ctx["tok_sha"]:
        bad(sid, f"tokenizer_sha256 {m['tokenizer_sha256'][:12]}…, the tokenizer given has {ctx['tok_sha'][:12]}…")
    if ctx["f2_set"] and m["decontam_set_sha256"] != ctx["f2_set"]:
        bad(sid, f"decontam_set_sha256 {m['decontam_set_sha256'][:12]}…, the pipeline manifest's F2 set is {ctx['f2_set'][:12]}…")
    if ctx["record_sha"] and m["cleaning_pipeline_sha256"] != ctx["record_sha"]:
        bad(sid, f"cleaning_pipeline_sha256 {m['cleaning_pipeline_sha256'][:12]}…, {RECORD} in the folder has {ctx['record_sha'][:12]}…")

    files = {}
    for uri, sha_field in (("payload_uri", "payload_sha256"), ("index_uri", "index_sha256"),
                           ("sample_metadata_uri", "sample_metadata_sha256"), ("quality_report_uri", "quality_report_sha256")):
        name = m[uri]
        if not isinstance(name, str) or Path(name).name != name:
            bad(sid, f"{uri} {name!r} is not a plain file name in the folder")
            continue
        if not (out / name).is_file():
            bad(sid, f"{name} is missing")
            continue
        got = sha256(out / name)
        if got != m[sha_field]:
            bad(sid, f"{name}: sha256 {got[:12]}…, the manifest says {str(m[sha_field])[:12]}…")
        if uri != "quality_report_uri":
            hashes[name] = got
        files[uri] = out / name
    if not (out / f"{sid}.dump.md").is_file():
        bad(sid, f"{sid}.dump.md is missing")

    n, docs = m["token_count"], m["doc_count"]
    tokens = idx = None
    if "payload_uri" in files:
        path, size = files["payload_uri"], files["payload_uri"].stat().st_size
        header = np.fromfile(path, dtype="<i4", count=256)
        if len(header) != 256 or header[0] != MAGIC or header[1] != VERSION:
            bad(sid, f"{path.name}: not a G6 shard header (magic {MAGIC}, version {VERSION})")
        elif int(header[2]) != n:
            bad(sid, f"{path.name}: the header says {int(header[2]):,} tokens, the manifest {n:,}")
        if size != HEADER_BYTES + 4 * n or m["payload_bytes"] != size:
            bad(sid, f"{path.name}: {size:,} bytes, token_count {n:,} gives {HEADER_BYTES + 4 * n:,}, payload_bytes says {m['payload_bytes']:,}")
        elif n > 0:
            tokens = np.memmap(path, dtype="<u4", mode="r", offset=HEADER_BYTES, shape=(n,))
    if "index_uri" in files:
        try:
            idx = np.load(files["index_uri"])
        except Exception as e:  # not a .npy file
            bad(sid, f"{files['index_uri'].name} cannot be read ({type(e).__name__})")
        else:
            if idx.dtype != np.dtype("<i8") or idx.ndim != 1 or len(idx) != docs + 1 or idx[0] != 0 or idx[-1] != n \
                    or not (np.diff(idx) > 0).all():
                bad(sid, f"{files['index_uri'].name}: not an int64 index of {docs + 1:,} strictly increasing starts from 0 to {n:,}")
                idx = None
    meta = None
    if "sample_metadata_uri" in files:
        try:
            meta = pq.read_table(files["sample_metadata_uri"])
            need = {"doc_id", "input_part", "input_row", "n_tokens", "n_chars", "lang_label"}
            if not need <= set(meta.column_names):
                bad(sid, f"{files['sample_metadata_uri'].name}: no {', '.join(sorted(need - set(meta.column_names)))} column")
                meta = None
            elif meta.num_rows != docs:
                bad(sid, f"{files['sample_metadata_uri'].name}: {meta.num_rows:,} rows, doc_count is {docs:,}")
                meta = None
        except Exception as e:  # not Parquet
            bad(sid, f"{files['sample_metadata_uri'].name} cannot be read ({type(e).__name__})")
    if meta is not None and idx is not None and meta.column("n_tokens").to_pylist() != np.diff(idx).tolist():
        bad(sid, "the metadata's n_tokens are not the steps of the index")
        meta = None

    if tokens is not None and idx is not None:
        special_at = []
        for a in range(0, n, CHUNK):
            chunk = np.asarray(tokens[a:a + CHUNK])
            if int(chunk.max()) >= VOCAB:
                return bad(sid, f"{files['payload_uri'].name}: a token id of {VOCAB} or more")
            special_at.append(np.flatnonzero(ctx["special"][chunk]) + a)
        special_at = np.concatenate(special_at)
        if special_at.shape != (docs,) or not (special_at == idx[1:] - 1).all() or not (tokens[idx[1:] - 1] == EOS_ID).all():
            bad(sid, "a special id other than the EOS at the end of each document, or a document without it")
        elif meta is not None and ctx["content"]:
            for k in sorted({0, docs - 1}):  # the first and the last document, against the final data
                check_document(sid, k, meta, tokens, idx, ctx, bad)


def check_document(sid, k, meta, tokens, idx, ctx, bad):
    """Document k of the shard is the tokens of its text in the run's final part."""
    doc_id, part, row = (meta.column(c)[k].as_py() for c in ("doc_id", "input_part", "input_row"))
    src = (ctx["final"] / part).resolve()
    if ctx["final"].resolve() not in src.parents or not src.is_file():
        return bad(sid, f"document {k} ({doc_id}): its input_part {part} is not a file under {ctx['final']}")
    got = read_row(src, row)
    if got is None or got[0] != doc_id:
        return bad(sid, f"document {k}: row {row} of {part} is {got[0] if got else 'not there'}, the metadata says {doc_id}")
    ids = ctx["tok"].encode_batch([got[1]], add_special_tokens=False)[0].ids
    if tokens[idx[k]:idx[k + 1]].tolist() != ids + [EOS_ID]:
        bad(sid, f"document {k} ({doc_id}) is not the tokens of its text in {part}")
    elif ctx["tok"].decode(ids, skip_special_tokens=False) != ctx["norm"](got[1]):
        bad(sid, f"document {k} ({doc_id}) does not decode to its normalized text")


def verify(out, manifest, tokenizer, table=pack_table.TABLE, summary=None):
    """(problems, hashes). out: the shard folder; manifest: the run's pipeline_manifest.json (its final/ folder and F2 set);
    tokenizer: tokenizer.json; table: pack_table.json; summary: shards_summary.json as a dict, or None.
    hashes: {file name: sha256} of every .bin, .idx.npy and .docs.parquet it read."""
    from tokenizers import Tokenizer
    out, manifest = Path(out), Path(manifest)
    problems, hashes = [], {}

    def bad(sid, message):
        problems.append(f"{sid}: {message}" if sid else message)

    run = manifest.resolve().parent
    pm = json.loads(manifest.read_text(encoding="utf-8"))
    tok = Tokenizer.from_file(str(tokenizer))
    special = np.zeros(VOCAB, dtype=bool)
    special[sorted(i for i in special_ids(tok) if i < VOCAB)] = True
    record = out / RECORD
    ctx = {"keys": set(json.loads(TEMPLATE.read_text(encoding="utf-8"))) - set(pack_table.LICENCE),  # the licence fields are optional
           "table": pack_table.load(table), "tok": tok,
           "tok_sha": sha256(tokenizer), "special": special, "final": run / "final",
           "norm": tok.normalizer.normalize_str if tok.normalizer is not None else (lambda t: t),
           "f2_set": next((s.get("set_sha256") for s in pm.get("stages", []) if s.get("stage") == "f2"), None),
           "record_sha": sha256(record) if record.is_file() else None, "content": True}
    if ctx["record_sha"] is None:
        bad(None, f"{RECORD} is missing in {out}")
    elif (run / RECORD).is_file() and sha256(run / RECORD) != ctx["record_sha"]:
        bad(None, f"{RECORD} in {out} is not the run's own ({run / RECORD}): the shards are from other processing, "
                  "so their documents are not compared with this run's final data")
        ctx["content"] = False

    manifests = {}
    for p in sorted(out.glob("*.json")):
        if p.name in (SUMMARY, RECORD) or p.name.endswith(".quality_report.json"):
            continue
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            bad(None, f"{p.name} is not valid JSON")
            continue
        if isinstance(m, dict) and m.get("schema_version") == "shard-v1":
            manifests[p.stem] = m
        else:
            bad(None, f"{p.name} is not a shard manifest")
    if not manifests:
        bad(None, f"no shard manifest in {out}")
    for sid, m in manifests.items():
        check_shard(out, sid, m, ctx, bad, hashes)

    if summary is not None:
        listed = summary_shards(summary)
        for sid in sorted(set(listed) - set(manifests)):
            bad(sid, "the summary lists it as written, but there is no shard manifest for it")
        for sid in sorted(set(manifests) - set(listed)):
            bad(sid, "there is a shard manifest for it, but the summary does not list it as written")
        for sid in sorted(set(listed) & set(manifests)):
            for key, field in (("docs", "doc_count"), ("tokens", "token_count")):
                if listed[sid].get(key) != manifests[sid].get(field):
                    bad(sid, f"the summary says {key} {listed[sid].get(key)}, the manifest {field} {manifests[sid].get(field)}")
        parts = sum(e.get("status") == "written" for e in summary.get("parts", {}).values())
        if summary.get("counts", {}).get("written") != parts:
            bad(None, f"the summary counts {summary.get('counts', {}).get('written')} written parts, and lists {parts}")
    return problems, hashes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="the shard folder")
    ap.add_argument("--manifest", type=Path, required=True, help="the run's pipeline_manifest.json")
    ap.add_argument("--tokenizer", type=Path, required=True, help="the tokenizer.json the shards were made with")
    ap.add_argument("--pack-table", type=Path, default=pack_table.TABLE)
    a = ap.parse_args()
    summary = a.out / SUMMARY
    problems, _ = verify(a.out, a.manifest, a.tokenizer, a.pack_table,
                         json.loads(summary.read_text(encoding="utf-8")) if summary.is_file() else None)
    for p in problems:
        print(p, file=sys.stderr)
    print(f"verify_shards: {len(problems)} problem(s) in {a.out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
