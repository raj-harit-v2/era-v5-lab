"""The benchmark registry: benchmarks.toml -> items to fingerprint.

Each benchmark is one table in benchmarks.toml. To add a benchmark, add a table.
Write code only for a new source type, file format or text filter (the dicts below).
"""

import ast
import csv
import hashlib
import json
import os
import re
import sys
import tarfile
import tomllib
import urllib.request
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent / "benchmarks.toml"
STATUSES = ("active", "planned", "skip")

# Text kinds. A code token is shorter than a prose word ("import numpy as np" is 4 tokens),
# so code needs a longer run for the same evidence. Measured on SWE-bench and the 38 sample
# packs: code at 20 removes the false hits of shared imports and tracebacks.
#   texts : prose, n words (default 13)
#   code  : code, n_code tokens (default 20)
#   mixed : prose with pasted code (a GitHub issue); split_prose_code() separates the two
KINDS = ("texts", "code", "mixed")
DEFAULT_N = {"prose": 13, "code": 20}

CODE_LINE = re.compile(r"^(\s{4}|\t|>>> |\.\.\. |\$ |Traceback|  File \"|\w+(Error|Exception)\b|"
                       r"import |from \S+ import |def |class |@)")


def split_prose_code(text):
    """Text -> (prose, code). Fenced blocks and code-looking lines are code."""
    prose, code, fence = [], [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fence = not fence
            continue
        (code if fence or CODE_LINE.match(line) else prose).append(line)
    return "\n".join(prose), "\n".join(code)


def run_lengths(b):
    return {"prose": b.get("n", DEFAULT_N["prose"]), "code": b.get("n_code", DEFAULT_N["code"])}


def load(path=REGISTRY):
    with open(path, "rb") as f:
        reg = tomllib.load(f)
    for bid, b in reg.items():
        problems = validate(bid, b)
        if problems:
            raise ValueError(f"{path}: [{bid}] " + "; ".join(problems))
    return reg


def validate(bid, b):
    p = []
    if not re.fullmatch(r"[a-z0-9_]+", bid):
        p.append("the id must be lower case letters, digits and _")
    for k in ("name", "status", "licence"):
        if k not in b:
            p.append(f"missing '{k}'")
    if b.get("status") not in STATUSES:
        p.append(f"status must be one of {STATUSES}")
    if b.get("status") in ("planned", "skip") and not b.get("reason"):
        p.append("a planned or skipped benchmark needs a 'reason'")
    if b.get("status") == "active":
        if b.get("source") not in SOURCES:
            p.append(f"source must be one of {sorted(SOURCES)}")
        if not b.get("files"):
            p.append("an active benchmark needs 'files'")
        for f in b.get("files", []):
            if not f.get("sha256") and b.get("source") != "local":
                p.append(f"{f.get('path')}: pin the file with 'sha256'")
            if file_format(f) not in READERS:
                p.append(f"{f.get('path')}: format must be one of {sorted(READERS)}")
        if not any(b.get(k) for k in KINDS):
            p.append(f"an active benchmark needs templates in one of {KINDS}")
        if b.get("source") == "hf" and not (b.get("repo") and b.get("revision")):
            p.append("an hf source needs 'repo' and 'revision'")
        if b.get("dedupe") and not b.get("id"):
            p.append("'dedupe' needs an 'id' template")
    for t in templates(b):
        for m in FIELD_RE.finditer(t):
            for name in filter(None, m.group(2).split("|")):
                if name not in FILTERS:
                    p.append(f"unknown filter '{name}'")
    if not isinstance(b.get("tags", []), list):
        p.append("'tags' must be a list")
    return p


# ---- sources: where the files come from ----

HF_TOKEN_FILE = Path.home() / ".cache" / "huggingface" / "token"  # where Hugging Face tools keep it


def hf_token():
    """HF_TOKEN from the environment, else the standard token file. Never write it to the repo."""
    token = os.environ.get("HF_TOKEN")
    if not token and HF_TOKEN_FILE.exists():
        token = HF_TOKEN_FILE.read_text(encoding="utf-8").strip()
    return token or None


def _download(url, dest, gated):
    req = urllib.request.Request(url)
    if gated:
        token = hf_token()
        if not token:
            raise SystemExit(f"{url}: gated. Accept the terms on Hugging Face, then set HF_TOKEN "
                             f"or save the token in {HF_TOKEN_FILE}.")
        req.add_header("Authorization", f"Bearer {token}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"download {url}", file=sys.stderr)
    with urllib.request.urlopen(req) as r, open(dest, "wb") as out:
        out.write(r.read())


def _cache_name(path):
    return path.replace("/", "__")  # many sets reuse one file name in several folders (MILU)


def _fetch_hf(bid, b, f, cache):
    dest = cache / bid / _cache_name(f["path"])
    if not dest.exists():
        url = f"https://huggingface.co/datasets/{b['repo']}/resolve/{b['revision']}/{f['path']}"
        _download(url, dest, b.get("gated", False))
    return dest


def _fetch_url(bid, b, f, cache):
    dest = cache / bid / _cache_name(f["path"])
    if not dest.exists():
        _download(f["url"], dest, b.get("gated", False))
    return dest


def _fetch_local(bid, b, f, cache):
    # For private sets (for example FrontierMath, if TSAI gets it) and for tests.
    return Path(os.path.expanduser(f["path"]))


SOURCES = {"hf": _fetch_hf, "url": _fetch_url, "local": _fetch_local}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(bid, b, cache):
    """Download (or find) each file of a benchmark and check its pinned sha256."""
    paths = []
    for f in b["files"]:
        path = SOURCES[b["source"]](bid, b, f, Path(cache))
        if f.get("sha256"):
            got = sha256_file(path)
            if got != f["sha256"]:
                raise SystemExit(f"[{bid}] {path}: sha256 {got} is not the pinned {f['sha256']}")
        paths.append(path)
    return paths


# ---- file formats ----

# A reader yields rows (dicts). 'columns' is the set of fields the templates use, so that
# large files (for example HLE with images, SWE-bench with full patches) stay small in memory.

def _keep(row, columns):
    return {k: row[k] for k in columns if k in row}


def _read_parquet(path, columns):
    import pyarrow.parquet as pq
    f = pq.ParquetFile(path)
    cols = [c for c in f.schema_arrow.names if c in columns]
    for batch in f.iter_batches(batch_size=256, columns=cols):
        yield from batch.to_pylist()


def _read_jsonl(path, columns):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield _keep(json.loads(line), columns)


def _read_json(path, columns):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for row in (data if isinstance(data, list) else data.values()):
        yield _keep(row, columns)


def _read_csv(path, columns):
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            yield _keep(row, columns)


# "# BENCHMARK DATA SHOULD NEVER ... terminal-bench-canary GUID 26b5c67b-..." -> "terminal-bench-canary GUID 26b5c67b-..."
# The GUID alone is BIG-bench's (HLE's canary has it too), so the prefix is kept: it names the benchmark.
TASK_CANARY = re.compile(r"[\w-]*canary GUID [0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
NOT_TEXT = (".enc", ".gz", ".tar", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".bin", ".pt")


def _read_task_dirs(path, columns):
    """A .tar.gz of task folders (Terminal-Bench): one row for each folder with a task.toml.

    Row fields: id (the folder name), instruction (instruction.md), solution (solution/solve.sh) and
    canary (the first canary string in any text file of the folder). The archive is read in memory
    and never extracted, so its paths cannot write anywhere.
    """
    with tarfile.open(path, "r:gz") as t:
        tasks = {}
        for m in t.getmembers():
            parts = m.name.split("/", 2)  # <archive root>/<task folder>/<file>
            if m.isfile() and len(parts) == 3:
                tasks.setdefault(parts[1], {})[parts[2]] = m

        def text(m):
            return t.extractfile(m).read().decode("utf-8", "replace") if m else None

        for tid in sorted(tasks):
            files = tasks[tid]
            if "task.toml" not in files:
                continue
            row = {"id": tid, "instruction": text(files.get("instruction.md")),
                   "solution": text(files.get("solution/solve.sh"))}
            if "canary" in columns:
                hits = (TASK_CANARY.search(text(files[name])) for name in sorted(files)
                        if not name.lower().endswith(NOT_TEXT))
                row["canary"] = next((h.group() for h in hits if h), None)
            yield _keep(row, columns)


READERS = {"parquet": _read_parquet, "jsonl": _read_jsonl, "json": _read_json, "csv": _read_csv,
           "task_dirs": _read_task_dirs}


def file_format(f):
    """The reader of a file: its 'format' key, else its extension. BFCL's .json files are JSON Lines."""
    return f.get("format") or Path(f.get("path", "")).suffix.lstrip(".")


# ---- text templates: "{field|filter|filter}" ----

def _as_list(v):
    if isinstance(v, str) and v.startswith("["):
        try:
            v = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return [v]
    return list(v) if isinstance(v, (list, tuple)) else [v]


FILTERS = {
    "lines": lambda v: "\n".join(map(str, _as_list(v))),
    "lettered": lambda v: "\n".join(f"{chr(65 + i)}. {c}" for i, c in enumerate(_as_list(v))),
    "no_calc": lambda v: re.sub(r"<<[^>]*>>", "", str(v)),  # GSM8K calculator notes
    "diff_added": lambda v: "\n".join(l[1:] for l in str(v).splitlines()
                                      if l.startswith("+") and not l.startswith("+++")),
    # "BENCHMARK DATA SHOULD NEVER ... canary GUID hle:3r2s:26b5c67b-..." -> "hle:3r2s:26b5c67b-..."
    "guid": lambda v: (re.search(r"\w+:\w+:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", str(v)) or
                       re.search(r".+", str(v))).group(),
    # BFCL "question": a list of turns, each a list of {"role", "content"} messages -> the user text
    "user_turns": lambda v: "\n".join(str(m["content"]) for turn in _as_list(v) for m in _as_list(turn)
                                      if isinstance(m, dict) and m.get("role") == "user"),
}

FIELD_RE = re.compile(r"\{([^{}|]+)((?:\|\w+)*)\}")  # field names can have spaces: {Final answer}


def render(template, row):
    """Fill a template from a row. Returns "" when a field is missing or empty."""
    empty = False

    def sub(m):
        nonlocal empty
        v = row.get(m.group(1))
        if v is None or v == "" or v == []:
            empty = True
            return ""
        for name in filter(None, m.group(2).split("|")):
            v = FILTERS[name](v)
        return FILTERS["lines"](v) if isinstance(v, (list, tuple)) else str(v)

    out = FIELD_RE.sub(sub, template)
    return "" if empty else out


def templates(b):
    return [t for k in KINDS for t in b.get(k, [])] + b.get("canaries", []) + ([b["id"]] if b.get("id") else [])


def fields(b):
    """The row fields that the templates of a benchmark use."""
    return {m.group(1) for t in templates(b) for m in FIELD_RE.finditer(t)}


def item_texts(b, row):
    """Row -> {"prose": [texts], "code": [texts]}."""
    out = {"prose": [], "code": []}
    out["prose"] += [render(t, row) for t in b.get("texts", [])]
    out["code"] += [render(t, row) for t in b.get("code", [])]
    for t in b.get("mixed", []):
        prose, code = split_prose_code(render(t, row))
        out["prose"].append(prose)
        out["code"].append(code)
    return {k: [t for t in v if t.strip()] for k, v in out.items()}


def items(bid, b, cache, canaries=None):
    """Yield (item_ref, {"prose": [texts], "code": [texts]}) for an active benchmark.

    With dedupe = true, an item id that comes again (for example in two splits) is skipped.
    Canary strings found in the rows are added to the 'canaries' set, if one is given.
    """
    split = b.get("split", "test")
    cols = fields(b)
    n, seen = 0, set()
    for f, path in zip(b["files"], fetch(bid, b, cache)):
        for row in READERS[file_format(f)](path, cols):
            item_id = render(b["id"], row) if b.get("id") else str(n)
            n += 1
            if b.get("dedupe"):
                if item_id in seen:
                    continue
                seen.add(item_id)
            if canaries is not None:
                canaries.update(c.strip() for c in (render(t, row) for t in b.get("canaries", [])) if c.strip())
            yield f"{bid}:{split}:{item_id}", item_texts(b, row)
