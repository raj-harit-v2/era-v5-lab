"""Original-split source index for the OpenCodeReasoning-2 question join (G10).

OCR-2 stores every question as "-" and names the problem by `(dataset, split, index)`. The publisher's
card ("How to use it") reads `index` as the row ordinal in the ORIGINAL source split, before any filter:
it is not an offset into an OCR-2 shard and not an index into a cleaned pool.

This module builds one small SQLite file from a source manifest that pins, per original split: the
repository, the revision, the ordered files, their row counts and their sha256. A lookup then needs no
network and cannot silently land on another snapshot:

- a file whose sha256 is not the pinned one stops the build (wrong revision or reordered rows);
- the ordinal is parsed canonically (no negative, fractional, boolean, padded or overflowing value);
- bounds come from the declared original row counts, cumulated in file order;
- a protected split (upstream valid/test) is indexed by hash only: its text is never stored, but a train
  row whose statement is the same problem can still be recognised and held out with its family.

    python source_index.py build --manifest source_manifest.json --out source_index.sqlite
    python source_index.py show --index source_index.sqlite

The index holds problem statements. Keep it out of Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Iterator

MANIFEST_SCHEMA = "g10-ocr2-source-manifest/1"
INDEX_SCHEMA = "g10-ocr2-source-index/1"
MAX_ORDINAL = 2**63 - 1
IDENTITY_LEVELS = ("verified", "diagnostic")
KINDS = ("parquet", "jsonl", "arrow", "statement_extraction")
ASSEMBLIES = ("question", "description", "codeforces")
_CANONICAL_INT = re.compile(r"0|[1-9][0-9]*")
_CODEFORCES_COLUMNS = ["description", "input_format", "output_format", "examples", "note"]


class SourceIndexError(Exception):
    """The manifest, a pinned file or the index itself cannot be trusted."""


class BadOrdinal(ValueError):
    """The index value is not a canonical non-negative row ordinal."""


class OutOfBounds(LookupError):
    """The ordinal is past the last row of the original split."""


# --- hashes ------------------------------------------------------------------------------------

def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def family_sha256(text: str) -> str:
    """Exact content identity of a statement: NFC, runs of whitespace collapsed, ends stripped.

    Two rows with the same value are the same problem. A different value proves nothing: near
    duplicates need a review, this key does not find them.
    """
    return text_sha256(" ".join(unicodedata.normalize("NFC", text).split()))


# --- the ordinal -------------------------------------------------------------------------------

def parse_ordinal(value) -> int:
    """`index` as a row ordinal, or BadOrdinal.

    Accepted: a non-negative int, or a string of ASCII digits in canonical form ("0", "17").
    Refused: bool, float, None, "", "-1", "+1", "01", " 1", "1.0", "1e3", other digit scripts,
    and anything over 2**63 - 1. Python's own int("-1") and list[-1] would accept a negative
    value and return the last row of the split.
    """
    if isinstance(value, bool):
        raise BadOrdinal("boolean index")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        if len(value) > 19 or not _CANONICAL_INT.fullmatch(value):
            raise BadOrdinal("index is not a canonical non-negative decimal")
        number = int(value)
    else:
        raise BadOrdinal(f"index of type {type(value).__name__}")
    if number < 0:
        raise BadOrdinal("negative index")
    if number > MAX_ORDINAL:
        raise BadOrdinal("index over 2**63 - 1")
    return number


# --- the publisher's question assembly ---------------------------------------------------------

def assemble_question(assembly: str, row: dict) -> str | None:
    """The question text exactly as the publisher's recipe builds it, or None when it gives none."""
    if assembly == "question":  # TACO, APPS
        text = row.get("question")
    elif assembly == "description":  # deepmind/code_contests
        text = row.get("description")
    elif assembly == "codeforces":  # open-r1/codeforces
        text = row.get("description")
        if not isinstance(text, str) or not text:
            return None
        parts = [text]
        if row.get("input_format"):
            parts += ["\n\nInput\n\n", row["input_format"]]
        if row.get("output_format"):
            parts += ["\n\nOutput\n\n", row["output_format"]]
        if row.get("examples"):
            parts.append("\n\nExamples")
            for example in row["examples"]:
                if "input" in example:
                    parts += ["\n\nInput\n\n", example["input"]]
                if "output" in example:
                    parts += ["\n\nOutput\n\n", example["output"]]
        if row.get("note"):
            parts += ["\n\nNote\n\n", row["note"]]
        if not all(isinstance(part, str) for part in parts):
            return None  # the recipe would fail on a null part; do not guess a repair
        text = "".join(parts)
    else:
        raise SourceIndexError(f"unknown question assembly {assembly!r}")
    return text if isinstance(text, str) and text else None


def _usable(text) -> str | None:
    """A statement that can be stored and rendered: a non-empty str that is valid UTF-8."""
    if not isinstance(text, str) or not text:
        return None
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return text


# --- manifest ----------------------------------------------------------------------------------

def source_key(dataset: str, split: str) -> str:
    return f"{dataset}/{split}"


def load_manifest(path) -> tuple[dict, str, Path]:
    """Read and validate a source manifest. Returns (manifest, sha256 of the file, its folder)."""
    path = Path(path)
    try:
        raw = path.read_bytes()
        manifest = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise SourceIndexError(f"cannot read source manifest {path}: {exc}") from exc

    def need(cond, message):
        if not cond:
            raise SourceIndexError(f"source manifest {path.name}: {message}")

    need(isinstance(manifest, dict) and manifest.get("schema") == MANIFEST_SCHEMA, f"schema is not {MANIFEST_SCHEMA}")
    ocr = manifest.get("ocr2")
    need(isinstance(ocr, dict), "no ocr2 block")
    for field in ("repo", "revision", "config"):
        need(isinstance(ocr.get(field), str) and ocr[field], f"ocr2.{field} is missing")
    shards = ocr.get("shards")
    need(isinstance(shards, list) and shards, "ocr2.shards is missing")
    need([s.get("shard_id") for s in shards] == list(range(len(shards))), "ocr2.shards must be listed in order, ids 0..n-1")
    for shard in shards:
        need(isinstance(shard.get("path"), str) and shard["path"], f"shard {shard.get('shard_id')} has no path")
        rows = shard.get("rows")
        need(rows is None or (isinstance(rows, int) and not isinstance(rows, bool) and rows >= 0),
             f"shard {shard['shard_id']} rows must be null or a count")
    seen = set()
    for entry in ocr.get("inputs", []):
        sid = entry.get("shard_id")
        need(isinstance(sid, int) and not isinstance(sid, bool) and 0 <= sid < len(shards), "an input names an unknown shard")
        need(sid not in seen, f"shard {sid} has two inputs")
        seen.add(sid)
        need(isinstance(entry.get("path"), str) and isinstance(entry.get("sha256"), str), f"input of shard {sid} needs path and sha256")
        need(isinstance(entry.get("rows"), int) and entry["rows"] >= 0, f"input of shard {sid} needs its row count")
        need(entry.get("coverage") in ("full", "prefix"), f"input of shard {sid}: coverage must be full or prefix")
        declared = shards[sid].get("rows")
        if entry["coverage"] == "full" and declared is not None:
            need(declared == entry["rows"], f"input of shard {sid} is marked full but its rows differ from the shard")
    sources = manifest.get("sources")
    need(isinstance(sources, dict), "no sources block")
    for key, spec in sources.items():
        for field in ("dataset", "split", "repo", "revision"):
            need(isinstance(spec.get(field), str) and spec[field], f"{key}: {field} is missing")
        need(key == source_key(spec["dataset"], spec["split"]), f"{key}: the key must be <dataset>/<split>")
        need(spec.get("kind") in KINDS, f"{key}: kind must be one of {KINDS}")
        need(spec.get("assembly") in ASSEMBLIES, f"{key}: assembly must be one of {ASSEMBLIES}")
        need(isinstance(spec.get("protected"), bool), f"{key}: protected must be true or false")
        need((spec.get("identity") or {}).get("level") in IDENTITY_LEVELS, f"{key}: identity.level must be one of {IDENTITY_LEVELS}")
        files = spec.get("files")
        need(isinstance(files, list) and files, f"{key}: no files")
        for f in files:
            need(isinstance(f.get("name"), str) and f["name"], f"{key}: a file has no name")
            need(isinstance(f.get("rows"), int) and not isinstance(f["rows"], bool) and f["rows"] >= 0, f"{key}: {f.get('name')} has no row count")
        need(len({f["name"] for f in files}) == len(files), f"{key}: a file is listed twice")
        need(spec.get("total_rows") == sum(f["rows"] for f in files), f"{key}: total_rows is not the sum of its files")
        if spec["kind"] == "statement_extraction":
            ext = spec.get("extraction") or {}
            for field in ("path", "sha256", "id_prefix"):
                need(isinstance(ext.get(field), str) and ext[field], f"{key}: extraction.{field} is missing")
        else:
            for f in files:
                need(isinstance(f.get("path"), str) and isinstance(f.get("sha256"), str) and len(f["sha256"]) == 64,
                     f"{key}: {f['name']} needs a path and a sha256")
    return manifest, hashlib.sha256(raw).hexdigest(), path.resolve().parent


def shard_index_base(manifest: dict, shard_id: int) -> int:
    """First rendered id of a shard: the ORIGINAL row counts of every earlier shard, never kept counts."""
    base = 0
    for shard in manifest["ocr2"]["shards"][:shard_id]:
        if shard.get("rows") is None:
            raise SourceIndexError(
                f"cannot reserve the id range of shard {shard_id}: the original row count of shard "
                f"{shard['shard_id']} is not in the source manifest")
        base += shard["rows"]
    return base


# --- build -------------------------------------------------------------------------------------

def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _file_rows(path: Path, columns: list[str]) -> Iterator[dict]:
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        pf = pq.ParquetFile(path)
        have = [c for c in columns if c in pf.schema_arrow.names]
        for batch in pf.iter_batches(batch_size=256, columns=have):
            yield from batch.to_pylist()
    elif path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)
    elif path.suffix == ".arrow":
        # BAAI/TACO: its loader script concatenates `datasets.Dataset.from_file(f)` over the listed files, and
        # from_file reads an Arrow IPC *stream*. Rows are yielded in stream order, which is the split order.
        import pyarrow as pa

        with pa.memory_map(str(path), "r") as source:
            try:
                reader = pa.ipc.open_stream(source)
            except pa.ArrowInvalid as exc:
                raise SourceIndexError(f"{path.name}: not an Arrow IPC stream ({exc})") from exc
            have = [c for c in columns if c in reader.schema.names]
            for batch in reader:
                yield from batch.select(have).to_pylist()
    else:
        raise SourceIndexError(f"{path.name}: only .parquet, .jsonl and .arrow source files are read")


def _columns(spec: dict) -> list[str]:
    columns = {"question": ["question"], "description": ["description"], "codeforces": list(_CODEFORCES_COLUMNS)}[spec["assembly"]]
    if spec.get("problem_id_field"):
        columns.append(spec["problem_id_field"])
    return columns


class _Writer:
    def __init__(self, con: sqlite3.Connection):
        self.con, self.digest = con, hashlib.sha256()

    def row(self, key, protected, ordinal, file_ordinal, local, question, problem_id):
        question = _usable(question)
        qsha = text_sha256(question) if question is not None else None
        family = family_sha256(question) if question is not None else None
        problem_id = None if problem_id is None else str(problem_id)
        self.con.execute(
            "INSERT INTO rows VALUES (?,?,?,?,?,?,?,?)",
            (key, ordinal, file_ordinal, local, problem_id, None if protected else question, qsha, family))
        self.digest.update(f"{key}\t{ordinal}\t{qsha or '-'}\t{problem_id or ''}\n".encode("utf-8"))


def _index_files(writer: _Writer, key: str, spec: dict, base: Path) -> None:
    offset = 0
    for file_ordinal, f in enumerate(spec["files"]):
        path = _resolve(base, f["path"])
        if not path.is_file():
            raise SourceIndexError(f"{key}: {path} is not a file")
        actual = sha256_file(path)
        if actual != f["sha256"]:
            raise SourceIndexError(
                f"{key}: {f['name']} has sha256 {actual}, not the pinned {f['sha256']} "
                "(another revision, or the rows were reordered): the index is not built")
        count = 0
        for local, row in enumerate(_file_rows(path, _columns(spec))):
            pid = row.get(spec["problem_id_field"]) if spec.get("problem_id_field") else None
            writer.row(key, spec["protected"], offset + local, file_ordinal, local, assemble_question(spec["assembly"], row), pid)
            count += 1
        if count != f["rows"]:
            raise SourceIndexError(f"{key}: {f['name']} has {count} rows, the manifest says {f['rows']}")
        writer.con.execute("INSERT INTO files VALUES (?,?,?,?,?,?)", (key, file_ordinal, f["name"], f["sha256"], count, offset))
        offset += count


def _index_extraction(writer: _Writer, key: str, spec: dict, base: Path) -> None:
    """A statement extraction: one JSONL of {id, text} for the whole split, ids `<prefix>/<file>/<local row>`.

    The extraction's sha256 is pinned; the file order and the per-file counts must be exactly the declared
    ones, so an ordinal is the cumulated original position and not a position in a filtered list.
    """
    ext = spec["extraction"]
    path = _resolve(base, ext["path"])
    if not path.is_file():
        raise SourceIndexError(f"{key}: {path} is not a file")
    actual = sha256_file(path)
    if actual != ext["sha256"]:
        raise SourceIndexError(f"{key}: extraction has sha256 {actual}, not the pinned {ext['sha256']}: the index is not built")
    id_field, text_field = ext.get("id_field", "id"), ext.get("text_field", "text")
    rows = _file_rows(path, [])
    offset = 0
    for file_ordinal, f in enumerate(spec["files"]):
        for local in range(f["rows"]):
            row = next(rows, None)
            expected = f"{ext['id_prefix']}/{f['name']}/{local}"
            if row is None or row.get(id_field) != expected:
                got = None if row is None else row.get(id_field)
                raise SourceIndexError(f"{key}: extraction row {offset + local} is {got!r}, expected {expected!r} (order or count differs)")
            writer.row(key, spec["protected"], offset + local, file_ordinal, local, row.get(text_field), None)
        writer.con.execute("INSERT INTO files VALUES (?,?,?,?,?,?)", (key, file_ordinal, f["name"], f.get("sha256"), f["rows"], offset))
        offset += f["rows"]
    if next(rows, None) is not None:
        raise SourceIndexError(f"{key}: the extraction has more rows than the declared files")


def _cross_checks(con: sqlite3.Connection, key: str, spec: dict, base: Path) -> list[dict]:
    """Independent identity probes. A failed probe stops the build: the ordinals cannot be trusted then."""
    done = []
    for check in spec.get("cross_checks", []):
        if check.get("kind") == "question_sha256":
            pairs = [(check["ordinal"], check["sha256"])]
            label = f"ordinal {check['ordinal']}"
        elif check.get("kind") == "parquet_column":
            path = _resolve(base, check["path"])
            actual = sha256_file(path)
            if actual != check["sha256"]:
                raise SourceIndexError(f"{key}: cross-check file {path.name} has sha256 {actual}, not {check['sha256']}")
            texts = [_usable(row.get(check["column"])) for row in _file_rows(path, [check["column"]])]
            pairs = [(check["row_offset"] + n, text_sha256(t) if t is not None else None) for n, t in enumerate(texts)]
            label = f"{path.name} at offset {check['row_offset']}"
        else:
            raise SourceIndexError(f"{key}: unknown cross-check kind {check.get('kind')!r}")
        for ordinal, expected in pairs:
            hit = con.execute("SELECT question_sha256 FROM rows WHERE source_key=? AND ordinal=?", (key, ordinal)).fetchone()
            if hit is None or hit[0] != expected:
                raise SourceIndexError(f"{key}: identity cross-check failed at ordinal {ordinal} ({label}): the index is not built")
        done.append({"kind": check["kind"], "label": label, "rows_matched": len(pairs)})
    return done


def build(manifest_path, out_path) -> dict:
    """Build the index next to a `.tmp` name and publish it by rename. Returns the summary stored in it."""
    manifest, manifest_sha, base = load_manifest(manifest_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        con.executescript(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE sources (source_key TEXT PRIMARY KEY, dataset TEXT, split TEXT, repo TEXT, revision TEXT,"
            " kind TEXT, assembly TEXT, protected INTEGER, identity_level TEXT, total_rows INTEGER);"
            "CREATE TABLE files (source_key TEXT, file_ordinal INTEGER, name TEXT, sha256 TEXT, rows INTEGER,"
            " row_offset INTEGER, PRIMARY KEY (source_key, file_ordinal));"
            "CREATE TABLE rows (source_key TEXT, ordinal INTEGER, file_ordinal INTEGER, local_ordinal INTEGER,"
            " problem_id TEXT, question TEXT, question_sha256 TEXT, family_sha256 TEXT,"
            " PRIMARY KEY (source_key, ordinal)) WITHOUT ROWID;")
        writer = _Writer(con)
        summary = {}
        for key in sorted(manifest["sources"]):
            spec = manifest["sources"][key]
            con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (key, spec["dataset"], spec["split"], spec["repo"], spec["revision"], spec["kind"],
                         spec["assembly"], int(spec["protected"]), spec["identity"]["level"], spec["total_rows"]))
            (_index_extraction if spec["kind"] == "statement_extraction" else _index_files)(writer, key, spec, base)
            checks = _cross_checks(con, key, spec, base)
            summary[key] = {"rows": spec["total_rows"], "files": len(spec["files"]), "protected": spec["protected"],
                            "identity_level": spec["identity"]["level"], "cross_checks": checks}
        con.execute("CREATE INDEX rows_family ON rows (family_sha256)")
        meta = {"schema": INDEX_SCHEMA, "manifest_sha256": manifest_sha, "content_sha256": writer.digest.hexdigest(),
                "sources": summary}
        con.executemany("INSERT INTO meta VALUES (?,?)", [(k, json.dumps(v, sort_keys=True)) for k, v in meta.items()])
        con.commit()
    except BaseException:
        con.close()
        tmp.unlink(missing_ok=True)
        raise
    con.close()
    with open(tmp, "rb") as stream:
        os.fsync(stream.fileno())
    os.replace(tmp, out_path)
    return meta


# --- lookup ------------------------------------------------------------------------------------

class SourceIndex:
    """Read-only view of a built index."""

    def __init__(self, path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise SourceIndexError(f"{self.path} is not a built source index")
        self.con = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        try:
            self.meta = {k: json.loads(v) for k, v in self.con.execute("SELECT key, value FROM meta")}
        except sqlite3.DatabaseError as exc:
            raise SourceIndexError(f"{self.path} is not a readable source index: {exc}") from exc
        if self.meta.get("schema") != INDEX_SCHEMA:
            raise SourceIndexError(f"{self.path} has schema {self.meta.get('schema')!r}, not {INDEX_SCHEMA}")
        self._sources = {
            (row[1], row[2]): {"source_key": row[0], "dataset": row[1], "split": row[2], "repo": row[3], "revision": row[4],
                               "kind": row[5], "assembly": row[6], "protected": bool(row[7]), "identity_level": row[8],
                               "total_rows": row[9]}
            for row in self.con.execute("SELECT * FROM sources")}

    def close(self) -> None:
        self.con.close()

    def source(self, dataset: str, split: str) -> dict | None:
        return self._sources.get((dataset, split))

    def resolve(self, dataset: str, split: str, ordinal: int) -> dict:
        """The original row at `ordinal` of (dataset, split). `ordinal` must come from parse_ordinal."""
        src = self._sources.get((dataset, split))
        if src is None:
            raise LookupError(f"{dataset}/{split} is not in this index")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise BadOrdinal("resolve() takes a parsed non-negative ordinal")
        if ordinal >= src["total_rows"]:
            raise OutOfBounds(f"{dataset}/{split} has {src['total_rows']} rows; ordinal {ordinal} is outside")
        row = self.con.execute(
            "SELECT r.file_ordinal, r.local_ordinal, r.problem_id, r.question, r.question_sha256, r.family_sha256, f.name"
            " FROM rows r JOIN files f ON f.source_key = r.source_key AND f.file_ordinal = r.file_ordinal"
            " WHERE r.source_key = ? AND r.ordinal = ?", (src["source_key"], ordinal)).fetchone()
        if row is None:
            raise SourceIndexError(f"{dataset}/{split} ordinal {ordinal} is inside the declared bounds but not indexed")
        return {**src, "ordinal": ordinal, "file_ordinal": row[0], "local_ordinal": row[1], "problem_id": row[2],
                "question": row[3], "question_sha256": row[4], "family_sha256": row[5], "file": row[6]}

    def family_members(self, family: str) -> list[tuple[str, str, bool]]:
        """Every (dataset, split, protected) that holds a statement with this family key."""
        return [(d, s, bool(p)) for d, s, p in self.con.execute(
            "SELECT DISTINCT s.dataset, s.split, s.protected FROM rows r JOIN sources s ON s.source_key = r.source_key"
            " WHERE r.family_sha256 = ? ORDER BY s.dataset, s.split", (family,))]


def open_or_build(manifest_path, index_path) -> SourceIndex:
    """Open the index for this exact manifest; build it when it does not exist yet."""
    _, manifest_sha, _ = load_manifest(manifest_path)
    index_path = Path(index_path)
    if not index_path.is_file():
        build(manifest_path, index_path)
    index = SourceIndex(index_path)
    if index.meta["manifest_sha256"] != manifest_sha:
        index.close()
        raise SourceIndexError(
            f"{index_path} was built from another source manifest ({index.meta['manifest_sha256'][:12]}..., "
            f"now {manifest_sha[:12]}...): build a new index, do not reuse this one")
    return index


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--manifest", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("show")
    s.add_argument("--index", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        meta = build(args.manifest, args.out) if args.command == "build" else SourceIndex(args.index).meta
    except SourceIndexError as exc:
        print(f"source_index: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(meta, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
