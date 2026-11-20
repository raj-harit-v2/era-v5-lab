"""Write one shard in the v1 format (shard_format_v1.md) from one cleaned pack part, check it, and describe it.

  python teams/01-data-a/shards/shard_writer.py --input <run>/final/train/code-go/part-00000.parquet \
      --manifest <run>/pipeline_manifest.json --tokenizer <p1536>/tokenizer.json \
      --language go --script Latn --lane code --out <dir>

Input: one part of the pipeline's final folder (run_pipeline.py: clean, dedup, then F2), and the run's pipeline_manifest.json.
provenance.py checks the part's chain back to the raw sample part (F2 report, apply, remove list, clean job) and stops
when a link breaks; what it returns checks cleaning_pipeline.json and goes into the quality report. The split comes from the
part's folder: train. A held-out part is refused until G3 and G9 say what happens to it (the format has train and
validation only). --domain defaults to clean.py's family of the pack.

Rollover: docs are taken in order into shard <pack>-<split>-<--index>; when the next doc would pass --tokens, that shard is
written and the doc opens the next one (--index + 1, ...), until every row of the part is read. A doc is never split, so
none is lost, repeated or cut. Shard k holds rows first_row..rows_read-1 of the part (its quality report gives both).
main() returns the manifests in shard order; run_shards.py numbers the shards of a pack across its parts.

Tokenizer (G3): the frozen p1536 tokenizer.json (Gate 3, in place of C3), sha256 TOKENIZER_SHA256 below (G3 train/p1536_s0_manifest.json).
Any other file is refused, except with --any-tokenizer (tests only: the shard is marked dataset_version "test").
--dataset-version (the corpus release in the manifest, e.g. sample or corpus-v1) is required otherwise: it is never guessed.
Docs are encoded with encode_batch(add_special_tokens=False); each doc ends with one EOS, <|endoftext|> id 130822 (G3, G10).
No BOS and no language tag. The normalizer is inside tokenizer.json, so no normalizer is applied here.

A doc is left out, counted, and listed by doc_id in the quality report when:
  - secret:     its text looks like it holds an email address or a secret (pr-guard's patterns);
  - empty:      it encodes to no tokens;
  - special:    a special id appears inside it (tokenizers turns a literal "<|im_start|>" in the text into a special id);
  - roundtrip:  decode(ids) is not the tokenizer-normalized text;
  - oversize:   it alone (with its EOS) is more than --tokens, so it fits in no shard (listed with its n_tokens).
A left-out doc is in the report of the shard whose rows it is in. A part with no doc to write (empty, or every row
left out) gets no shard: main() raises NoShard with its row count and left-out doc_ids.
Checks after writing: G6's open_shard reads the .bin, sizes and index match the manifest, every id < 131,072, and the only
special ids in the shard are the EOS at the end of each doc.
Writes, for each shard, <dir>/<shard_id>.{bin,idx.npy,docs.parquet,json}, cleaning_pipeline.json, <shard_id>.quality_report.json and <shard_id>.dump.md
(IDs and counts only, never text). cleaning_pipeline.json describes the processing (clean.py, F2 set, remove list): run_pipeline.py's shard stage writes it
next to the manifest, and the writer checks it against what provenance.py derives and copies it, so every shard of one
run gets the same file; a --out that already holds one from other processing is refused. The quality report's
"upstream" block lists the doc_ids this part lost to dedup (with group and rule) and to F2 (with benchmark item IDs and
offsets). Needs numpy, pyarrow, tokenizers and torch (G6's dataio imports torch).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from tokenizers import Tokenizer

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "teams" / "06-performance"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import provenance  # noqa: E402
from verify_shards import EOS, EOS_ID, VOCAB, special_ids  # noqa: E402  (the shard constants live there, with the checks of a finished shard)
from dataio.loader import HEADER_BYTES, open_shard  # noqa: E402
from dataio.prepare_fineweb import write_shard  # noqa: E402

TOKENIZER_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"  # G3 Gate 3 freeze, p1536 (was C3 15468e66..., #340)
VOCAB = 131_072
EOS_ID, EOS = 130_822, "<|endoftext|>"
SPECIAL_BLOCK = range(130_725, VOCAB)  # G3: named specials and reserved slots; plus every added token marked special
BATCH = 256
LEFT_OUT = ("secret", "empty", "special", "roundtrip", "oversize")  # the reasons a doc is left out
# pr-guard's secret and email patterns (.github/workflows/pr-guard.yml)
SECRET = re.compile("|".join([
    r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"gh[pousr]_[A-Za-z0-9]{30,}", r"\bsk-[A-Za-z0-9_-]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@(?!users\.noreply\.github\.com\b|example\.(?:com|org)\b)"
    r"(?:[A-Za-z0-9-]+\.)+(?:com|org|net|edu|gov|mil|int|in|io|ai|co|uk|us|me|dev|app|info|biz|ac|ca|au|de|fr|jp|sg|ae)\b"]),
    re.IGNORECASE)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dataset_version_problem(version, any_tokenizer):
    """Why this --dataset-version cannot go into a manifest, or None. --any-tokenizer shards are always "test"; any other
    run must name its corpus release (e.g. sample, corpus-v1), and never "test"."""
    if any_tokenizer:
        return None if version in (None, "test") else '--any-tokenizer shards are dataset_version "test"; leave out --dataset-version'
    if not version or version == "test":
        return '--dataset-version is required (e.g. sample, corpus-v1); "test" is only for --any-tokenizer'
    return None


def load_tokenizer(path, any_tokenizer):
    """(tokenizer, sha256, special ids). Refuses anything but p1536 unless any_tokenizer."""
    got = sha(path)
    tok = Tokenizer.from_file(str(path))
    if not any_tokenizer:
        if got != TOKENIZER_SHA256:
            sys.exit(f"{path}: sha256 {got}, not the frozen p1536 {TOKENIZER_SHA256}. --any-tokenizer is for tests only.")
        if tok.id_to_token(EOS_ID) != EOS:
            sys.exit(f"{path}: id {EOS_ID} is {tok.id_to_token(EOS_ID)!r}, not {EOS}")
    if tok.get_vocab_size(with_added_tokens=True) != VOCAB:
        sys.exit(f"{path}: vocab {tok.get_vocab_size(with_added_tokens=True)}, not {VOCAB}")
    return tok, got, special_ids(tok)


def pack_family(pack_id):
    """clean.py's family of the pack (code, english, math, sci, indic), the shard's domain unless --domain says otherwise."""
    sys.path.insert(0, str(REPO / "teams" / "01-data-a" / "spec_v1"))
    try:
        import clean
    finally:
        sys.path.remove(str(REPO / "teams" / "01-data-a" / "spec_v1"))
    if pack_id not in clean._FAMILY:
        sys.exit(f"shard_writer: clean.py has no family for pack {pack_id!r}; give --domain")
    return clean._FAMILY[pack_id]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True, help="a part of the pipeline's final folder: <run>/final/<split>/<pack>/<part>.parquet")
    ap.add_argument("--manifest", type=Path, required=True, help="the run's pipeline_manifest.json")
    ap.add_argument("--tokenizer", type=Path, required=True, help="G3's frozen p1536 tokenizer.json")
    ap.add_argument("--language", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--lane", required=True, help="capability_lane")
    ap.add_argument("--domain", help="default: the pack's family in clean.py")
    ap.add_argument("--license", help="the pack's licence, written into the manifest (with --license-source)")
    ap.add_argument("--license-source", help="where that licence is recorded (with --license)")
    ap.add_argument("--index", type=int, default=0, help="number of the part's first shard within the pack and split")
    ap.add_argument("--tokens", type=int, default=2 ** 26, help="fill each shard up to this many tokens, then roll over")
    ap.add_argument("--any-tokenizer", action="store_true", help="tests only: accept a tokenizer other than p1536")
    ap.add_argument("--dataset-version", help="the manifest's dataset_version (e.g. sample, corpus-v1); required unless --any-tokenizer")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if bool(a.license) != bool(a.license_source):
        sys.exit("shard_writer: --license and --license-source go together: a manifest names a licence with where it is recorded")
    problem = dataset_version_problem(a.dataset_version, a.any_tokenizer)
    if problem:
        sys.exit(f"shard_writer: {problem}")
    a.dataset_version = a.dataset_version or "test"

    try:
        info = provenance.load(a.input, a.manifest)
    except provenance.Stop as e:
        sys.exit(f"shard_writer: {e}")
    pack_id, part_path = info["part"]["pack_id"], f"{info['part']['split']}/{info['part']['part']}"
    if info["part"]["split"] != "train":
        sys.exit(f"shard_writer: {part_path} is a {info['part']['split']} part. Only train parts are sharded for now: the format "
                 "allows train and validation, and what a held-out part becomes is for G3 and G9 to say")
    split = "train"
    domain = a.domain or pack_family(pack_id)
    tok, tok_sha, specials = load_tokenizer(a.tokenizer, a.any_tokenizer)
    norm = tok.normalizer.normalize_str if tok.normalizer is not None else (lambda t: t)  # a Sequence normalizer has len 0, so it is falsy
    pipeline = a.out / "cleaning_pipeline.json"
    run_file = a.manifest.resolve().parent / "cleaning_pipeline.json"  # written by run_pipeline.py's shard stage
    if not run_file.is_file():
        sys.exit(f"shard_writer: {run_file} not found: run_pipeline.py's shard stage writes it "
                 f"(or: python teams/01-data-a/shards/provenance.py --manifest {a.manifest} --write-record)")
    if json.loads(run_file.read_text(encoding="utf-8")) != info["record"]:
        sys.exit(f"shard_writer: {run_file} is not what {a.manifest} and its stage outputs give now; write it again "
                 "(provenance.py --write-record)")
    if pipeline.is_file() and pipeline.read_bytes() != run_file.read_bytes():
        sys.exit(f"shard_writer: {pipeline} describes other processing than {run_file} (another clean.py, F2 set or remove list); use a new --out")
    a.out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    ctx = {"info": info, "tok_sha": tok_sha, "specials": specials, "run_file": run_file, "pipeline": pipeline,
           "part_path": part_path, "pack_id": pack_id, "split": split, "domain": domain, "commit": commit}

    table = pq.read_table(a.input, columns=["doc_id", "text", "lang_label"])
    ids_col, text_col, lang_col = (table.column(c).to_pylist() for c in ("doc_id", "text", "lang_label"))
    del table
    manifests, index = [], a.index
    cur = new_shard(0)
    for b in range(0, len(text_col), BATCH):
        texts = text_col[b:b + BATCH]
        for k, enc in enumerate(tok.encode_batch_fast(texts, add_special_tokens=False)):
            row, text, ids = b + k, texts[k], enc.ids
            doc_id, left_out = ids_col[row], cur["left_out"]
            if SECRET.search(text):
                left_out["secret"].append(doc_id)
                continue
            if not ids:
                left_out["empty"].append(doc_id)
                continue
            inside = sorted(set(ids) & specials)
            if inside:
                left_out["special"].append({"doc_id": doc_id, "ids": inside})
                continue
            if tok.decode(ids, skip_special_tokens=False) != norm(text):
                left_out["roundtrip"].append(doc_id)
                continue
            n = len(ids) + 1
            if n > a.tokens:  # alone it would pass --tokens, and a doc is never split
                left_out["oversize"].append({"doc_id": doc_id, "n_tokens": n})
                continue
            if cur["total"] + n > a.tokens:  # roll over: this shard is full, the doc opens the next one
                manifests.append(finish(a, ctx, f"{pack_id}-{split}-{index:06d}", cur, rows_end=row))
                index += 1
                cur = new_shard(row)
            cur["docs"].append(ids + [EOS_ID])
            cur["rows"].append({"doc_id": doc_id, "input_part": part_path, "input_row": row, "n_tokens": n,
                                "n_chars": len(text), "lang_label": lang_col[row]})
            cur["total"] += n
    if not cur["docs"]:  # rollover only opens a shard with a doc in it, so this part has no doc to write at all
        raise NoShard(len(text_col), cur["left_out"])
    manifests.append(finish(a, ctx, f"{pack_id}-{split}-{index:06d}", cur, rows_end=len(text_col)))
    return manifests


class NoShard(Exception):
    """A part with no document to write: empty (0 rows, e.g. emptied by dedup or F2) or every row left out. No shard (and no
    zero-token shard) is written; rows and left_out (the doc_ids per reason) say why, for run_shards.py's summary."""

    def __init__(self, rows, left_out):
        super().__init__(f"no document of this part goes into a shard: {rows} row(s), "
                         f"{sum(len(v) for v in left_out.values())} left out")
        self.rows, self.left_out = rows, left_out


def new_shard(first_row):
    """An empty shard that starts at this row of the part. Left-out docs are reported by the shard whose rows they are in."""
    return {"docs": [], "rows": [], "total": 0, "first_row": first_row, "left_out": {k: [] for k in LEFT_OUT}}


def finish(a, ctx, shard_id, cur, rows_end):
    """Write one shard (rows first_row..rows_end-1 of the part), its report, manifest and dump; check it; return the manifest."""
    info, specials, pipeline, part_path = ctx["info"], ctx["specials"], ctx["pipeline"], ctx["part_path"]
    docs, rows, left_out = cur["docs"], cur["rows"], cur["left_out"]
    starts = np.cumsum([0] + [r["n_tokens"] for r in rows]).astype("<i8")  # doc_count + 1 entries; the last is token_count
    bin_path, idx_path, meta_path = (a.out / f"{shard_id}{x}" for x in (".bin", ".idx.npy", ".docs.parquet"))
    write_shard(bin_path, [t for d in docs for t in d])
    np.save(idx_path, starts)
    pq.write_table(pa.Table.from_pylist(rows), meta_path)
    shutil.copyfile(ctx["run_file"], pipeline)  # the run's file, byte for byte: its sha256 is the manifest's cleaning_pipeline_sha256
    tpc = np.array([r["n_tokens"] / max(r["n_chars"], 1) for r in rows])
    worst = sorted(rows, key=lambda r: -r["n_tokens"] / max(r["n_chars"], 1))[:5]
    lo = {k: len(v) for k, v in left_out.items()}
    report = a.out / f"{shard_id}.quality_report.json"
    report.write_text(json.dumps({
        "shard_id": shard_id, "first_row": cur["first_row"], "rows_read": rows_end, "docs_in_shard": len(docs),
        "left_out": lo, "left_out_docs": left_out,
        "tokens_per_char": {"min": round(float(tpc.min()), 3), "median": round(float(np.median(tpc)), 3),
                            "p99": round(float(np.percentile(tpc, 99)), 3), "max": round(float(tpc.max()), 3)},
        "most_tokens_per_char": [{"doc_id": r["doc_id"], "n_tokens": r["n_tokens"], "n_chars": r["n_chars"]} for r in worst],
        "upstream": {"input_part": part_path, "raw_input_sha256": info["raw_input"]["sha256"], "final_sha256": info["final"]["sha256"],
                     "run_id": info["pipeline"]["run_id"], "counts": info["counts"], "removed_by_dedup": info["dedup"]["removed"],
                     "dropped_by_f2": info["f2"]["dropped"]},  # the whole input part, whichever of its shards this is
    }, indent=2) + "\n", encoding="utf-8", newline="\n")

    token_count = int(starts[-1])
    payload_sha = sha(bin_path)  # once: it goes into the manifest and into the dump below
    manifest = {
        "schema_version": "shard-v1", "dataset_version": a.dataset_version, "shard_id": shard_id,
        "format": "brahmic_u32_v2+doc_index", "token_dtype": "uint32",
        "payload_uri": bin_path.name, "payload_sha256": payload_sha, "payload_bytes": bin_path.stat().st_size,
        "index_uri": idx_path.name, "index_sha256": sha(idx_path),
        "doc_count": len(docs), "token_count": token_count, "eos_token_id": EOS_ID,
        "tokenizer_sha256": ctx["tok_sha"],
        "pack_id": ctx["pack_id"], "language": a.language, "script": a.script, "domain": ctx["domain"], "capability_lane": a.lane,
        **({"license": a.license, "license_source": a.license_source} if a.license else {}),  # from the job's pack table
        "split": ctx["split"],
        "inputs_sha256": hashlib.sha256(f"{info['raw_input']['sha256']} {info['raw_input']['part']}\n".encode("utf-8")).hexdigest(),
        "cleaning_pipeline_sha256": sha(pipeline), "decontam_set_sha256": info["f2"]["set_sha256"],
        "sample_metadata_uri": meta_path.name, "sample_metadata_sha256": sha(meta_path),
        "quality_report_uri": report.name, "quality_report_sha256": sha(report),
        "created_by": ctx["commit"],
    }
    # Check the shard against its manifest, reading the .bin the way G6's loader does, before the manifest is published.
    tokens = open_shard(bin_path)
    idx = np.load(idx_path)
    meta = pq.read_table(meta_path)
    assert manifest["payload_bytes"] == HEADER_BYTES + 4 * token_count and len(tokens) == token_count <= a.tokens
    assert idx[0] == 0 and idx[-1] == token_count and len(idx) == len(docs) + 1 == meta.num_rows + 1
    assert meta.column("n_tokens").to_pylist() == np.diff(idx).tolist()
    assert int(tokens.max()) < VOCAB
    special_at = np.flatnonzero(np.isin(tokens, sorted(specials)))
    assert special_at.tolist() == (idx[1:] - 1).tolist(), "a special id other than the final EOS of a doc"
    assert (tokens[idx[1:] - 1] == EOS_ID).all()
    for k, d in enumerate(docs):
        assert tokens[idx[k]:idx[k + 1]].tolist() == d
    del tokens

    header = np.fromfile(bin_path, dtype="<i4", count=3)
    n, tok_sha = meta.num_rows, ctx["tok_sha"]
    lines = [f"# Shard `{shard_id}`\n\n",
             f"Written by `shard_writer.py` from `{part_path}`, after `clean.py`, dedup ({info['counts']['removed_by_dedup']:,} of this "
             f"part's {info['counts']['cleaned']:,} docs removed) and F2 ({info['counts']['dropped_by_f2']:,} dropped; fingerprints "
             f"`{info['f2']['set_sha256'][:12]}`): {n:,} docs from rows {cur['first_row']:,} to {rows_end - 1:,} of the part, "
             f"up to {a.tokens:,} tokens a shard.\n\n",
             f"Tokenizer `{tok_sha[:12]}`" + (" (**not p1536: test only**)" if tok_sha != TOKENIZER_SHA256 else " (p1536, frozen)") +
             f"; EOS `{EOS}` id {EOS_ID} after each doc; no BOS, no language tag.\n\n",
             f"Left out: {lo['secret']} secret-like, {lo['empty']} empty, {lo['special']} with a special id inside, "
             f"{lo['roundtrip']} not round-tripping, {lo['oversize']} longer than a shard "
             f"(doc_ids in `{shard_id}.quality_report.json`).\n\n",
             "| file | bytes | sha256 |\n|---|---:|---|\n",
             *(f"| `{p.name}` | {p.stat().st_size:,} | `{(payload_sha if p == bin_path else sha(p))[:16]}…` |\n" for p in (bin_path, idx_path, meta_path, pipeline, report)),
             f"\n## `{bin_path.name}`\n\n- header, {HEADER_BYTES:,} bytes = 256 little-endian int32: `{header[0]}` (magic), "
             f"`{header[1]}` (version), `{header[2]:,}` (token count), then zeros\n"
             f"- then {token_count:,} little-endian uint32 token IDs; every doc ends with {EOS_ID}, and no other special id occurs\n"
             f"- tokens per character: median {np.median(tpc):.3f}, max {tpc.max():.3f}\n\n",
             f"## `{idx_path.name}`\n\nint64, {n + 1:,} entries (start of each doc, then token_count): "
             f"`{idx[:5].tolist()} … {idx[-2:].tolist()}`\n\n",
             f"## `{meta_path.name}`\n\nOne row per doc in shard order, IDs and counts only. First rows:\n\n"
             "| doc_id | input_part | input_row | n_tokens | n_chars | lang_label |\n|---|---|---:|---:|---:|---|\n",
             *(f"| `{r['doc_id']}` | `{r['input_part']}` | {r['input_row']:,} | {r['n_tokens']:,} | {r['n_chars']:,} | "
               f"{r['lang_label']} |\n" for r in rows[:5])]
    (a.out / f"{shard_id}.dump.md").write_text("".join(lines), encoding="utf-8", newline="\n")
    # The manifest is the shard's completion mark: written last, to a .tmp and renamed, so a shard without one (a run
    # stopped part-way) is incomplete, and run_shards.py writes it again.
    tmp = a.out / f"{shard_id}.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, a.out / f"{shard_id}.json")
    print(json.dumps({"shard_id": shard_id, "docs": n, "tokens": token_count, "first_row": cur["first_row"], "rows_read": rows_end,
                      "left_out": lo, "tokens_per_char_median": round(float(np.median(tpc)), 3), "tokenizer": tok_sha[:12]}))
    return manifest


if __name__ == "__main__":
    try:
        main()
    except NoShard as e:
        print(json.dumps({"no_shard": str(e), "rows": e.rows, "left_out": {k: len(v) for k, v in e.left_out.items()}}))
