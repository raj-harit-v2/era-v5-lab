r"""H3, the same content in another language: candidate document pairs from a multilingual sentence encoder, confirmed
by sentence alignment. A measurement job (E5): it lists and counts pairs and removes nothing.

dedup_design_v1.md, "H3": H1 and H2 find same-language copies within and across packs; translations need another
method, since they share no hash and few word shingles. Two documents in different languages are an H3 pair when most
sentences of the shorter one have a mutual best match in the other:

    coverage = aligned sentence pairs / sentences of the shorter document >= coverage_threshold

as H2's Jaccard counts shared shingles. The thresholds here are provisional; E5's sweep and hand review set them. Rule 0
applies to any later removal: a held-out copy always survives (source_priority_v1.md).

HOW TO RUN IT
=============
Python 3.10+ with numpy, pyarrow, torch and sentence-transformers (requirements_h3.txt), and the encoder in a local
folder (model_path: LaBSE in sentence-transformers format). The model is never downloaded: the script sets the Hugging
Face libraries offline, so it needs no network and no keys. It reads only its inputs and writes only to out/ in the
repository root; paths in the config are relative to the repository root.

    python teams/01-data-a/dedup/h3.py --config teams/01-data-a/dedup/h3_local.json

STAGES (cheapest first, so the encoder sees as little text as possible; each stage is timed)
==========================================================================================
  read      only the parts whose pack_id matches a configured pack (the pack_id column is read first), in record
            batches; sentences are split and short documents skipped without the model; with max_docs_per_pack a part
            is left as soon as its packs have enough documents
  encode    one vector per document from its first head_sentences sentences, in chunks; cached per part under cache,
            so a rerun with other thresholds encodes nothing again
  url       pages whose URLs differ only in a language marker (hi.example.org, /hi/, ?lang=hi): an exact key join
  retrieve  for each configured language pair, each document's top_k nearest documents in the other language by exact
            cosine, in blocks of rows (no index to build, no estimate); with mutual, a pair must be in both lists
  verify    URL pairs first, then the others by cosine, at most max_verify: the length ratio is checked, the texts of
            those documents are read again (only the row groups that hold them), their sentences encoded once, and each
            pair's mutual best sentence matches counted, pair_batch pairs per step

SPEED (TSAI rule, 14 Nov: batched operations, no Python loops over tokens, no avoidable host-device syncs)
==========================================================================================================
Text is processed as whole pyarrow record batches (the batch functions of h3_signals.py) and indices as numpy arrays:
no Python loop runs over rows, documents, sentences, tokens or pairs. Vectors stay on the encoder's device: retrieval
is a blocked matmul with topk and alignment one bmm per batch of pairs (h3_align.py), and each stage's result is copied
to the host once. The encoder runs the model's preprocessing and forward pass itself, on texts sorted by length so
that batches pad little; on CUDA each token batch and index array goes to the device from pinned memory without
blocking. precision "auto" is fp16 on CUDA, with TF32 matmuls, and fp32 elsewhere. With sync_debug on CUDA, torch
warns at every host-device sync after the read stage. Python loops remain over parts, record batches, encoder chunks
and batches, row blocks, pair batches, the configured packs and language pairs, the distinct sizes of URL groups and
the distinct non-ASCII digits in numbers. The cache copies each part's head vectors to the host, once per part.

TIME
====
max_minutes stops the run at the next check (between record batches, encoder chunks, blocks and pair batches). The
summary then has status "stopped_time_limit" and no other output is written: an incomplete run must not be used. Each
stage's seconds and rate are in the summary. A test run limited by max_docs_per_pack also gets an estimate for all
documents of the selected packs, and a suggested Max time for the job request (1.5 x the estimate).

CONFIG (JSON; keys starting with "_" are comments)
==================================================
  inputs              TSAI's cleaned output, train/ and heldout/: only the parts under those two folders are read, as by
                      overlap.py. Or the raw <pack>/Part_N/ and <pack>/Heldout/: every part is read, a folder named
                      heldout, in any case, is held-out and everything else is train
  out, cache          the output folder and the embedding cache, both inside out/; cache "" turns the cache off
  packs               {pack_id pattern: language}, e.g. {"ind-hi-*": "hi", "en-*": "en"}; other packs are not read
  pairs               the language pairs to compare, e.g. [["sa", "en"], ["hi", "en"]]
  model_path, device, precision                      the local encoder folder; auto, cpu, mps or cuda; auto, fp32,
                                                     fp16 or bf16
  batch_size, max_seq_length                         encoder batch and token limit
  min_chars, min_sentences                           shorter documents are skipped (counted, never encoded)
  sentence_min_chars, head_sentences, max_sentences  sentence length; sentences in the document vector; sentences kept
  top_k, doc_floor, mutual                           neighbours per document, lowest cosine kept, both lists required
  max_length_ratio                                   longer/shorter characters allowed (URL pairs are kept regardless)
  sentence_threshold, coverage_threshold, report_floor   aligned sentence cosine, H3 coverage, lowest coverage listed;
                                                     sentence_threshold is one value, or {"sa-en": 0.55} per
                                                     language pair (either order; a pair not named gets 0.7)
  max_verify, url_group_max, block (rows per retrieval step), pair_batch (pairs per alignment step),
  max_docs_per_pack (0: all), max_minutes, max_output_mb, sync_debug (true: torch warns at host-device syncs on CUDA)

WHAT IT WRITES (in out; IDs, scores and counts only, never text)
================================================================
  h3_docs.parquet     row -> document: row, id, doc_id, pack, lang, split, part, row_in_part, chars, sentences
  h3_candidates.csv   every verified pair at or above report_floor, and every URL pair, highest coverage first
  h3_matches.csv      pairs at or above coverage_threshold, keyed by document for dedup.py (h3_join.py): pack_id, split,
                      part, row_in_part and doc_id of each document, then lang_a, lang_b, coverage
  h3_by_pack.csv      pack x pack: retrieved, URL, verified, listed and qualifying pairs
  h3_histogram.csv    bins of 0.01: the cosine of every retrieved pair, the coverage of every verified pair
  h3_summary.json     counts, stage times and rates, the estimate, the model and package versions, each output's sha256

In TSAI's cleaned output, part is the path under the split folder, as in overlap_docs.parquet, and row_in_part counts
every row of the part from 0, as overlap.py does. dedup.py finds each document of h3_matches.csv in overlap_docs.parquet
by (pack_id, split, part, row_in_part) and checks its doc_id, so H3 and overlap must read the same cleaned parts.
"""
import sys
sys.dont_write_bytecode = True   # write only to ./out/: no __pycache__ beside the scripts

import argparse, fnmatch, hashlib, json, math, os, platform, time  # noqa: E402,E401
from collections import Counter, defaultdict  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from pathlib import Path  # noqa: E402

try:
    import resource   # Unix only: without it (Windows), peak_rss_mb is null
except ImportError:
    resource = None

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.csv as pacsv
    import pyarrow.parquet as pq
    import torch
    from h3_align import align_batch, cross_topk, unit
    from h3_signals import (head_texts, latin_token_lists, number_tokens, pair_overlap, rank_in_group,
                            sentences_batch, url_keys)
except ImportError:   # main() says what to install
    np = None

REPO = Path(__file__).resolve().parents[3]   # teams/01-data-a/dedup/h3.py -> the repository root
SENTENCE_THRESHOLD = 0.7   # the default, and a language pair's when a sentence_threshold map does not name it
DEFAULTS = {"inputs": "out/tokenizer_sample_v0_clean", "out": "out/h3", "cache": "out/h3_cache",
            "packs": {}, "pairs": [], "model_path": "", "device": "auto", "precision": "auto", "batch_size": 64,
            "max_seq_length": 128, "min_chars": 200, "min_sentences": 3, "sentence_min_chars": 20, "head_sentences": 4,
            "max_sentences": 16, "top_k": 3, "doc_floor": 0.5, "mutual": True, "max_length_ratio": 4.0,
            "sentence_threshold": SENTENCE_THRESHOLD, "coverage_threshold": 0.6, "report_floor": 0.3,
            "max_verify": 10000, "url_group_max": 20, "block": 512, "pair_batch": 1024, "max_docs_per_pack": 0,
            "max_minutes": 60, "max_output_mb": 50, "sync_debug": False}
POSITIVE = ("batch_size", "max_seq_length", "head_sentences", "max_sentences", "top_k", "max_verify", "url_group_max",
            "block", "pair_batch")
NONNEGATIVE = ("min_chars", "min_sentences", "sentence_min_chars", "max_docs_per_pack")
OUTPUTS = ("h3_docs.parquet", "h3_candidates.csv", "h3_matches.csv", "h3_by_pack.csv", "h3_histogram.csv")
MATCHES_HEADER = ["pack_id_a", "split_a", "part_a", "row_in_part_a", "doc_id_a",      # H3_HEADER of h3_join.py
                  "pack_id_b", "split_b", "part_b", "row_in_part_b", "doc_id_b", "lang_a", "lang_b", "coverage"]
SPLITS = ("train", "heldout")   # the split folders of TSAI's cleaned output, as overlap.py reads them
PRECISIONS = ("auto", "fp32", "fp16", "bf16")
BATCH_ROWS = 16384      # rows per record batch read
CHUNK = 2048            # texts per encoder call; the time limit is checked between calls


class TimeLimit(Exception):
    pass


class Clock:
    """Seconds per stage, and the time limit of the whole run."""

    def __init__(self, max_minutes):
        self.t0 = time.time()
        self.deadline = self.t0 + max_minutes * 60
        self.stages = {}

    @contextmanager
    def stage(self, name):
        start = time.time()
        try:
            yield
        finally:
            self.stages[name] = round(self.stages.get(name, 0.0) + time.time() - start, 3)

    def check(self):
        if time.time() > self.deadline:
            raise TimeLimit

    def elapsed(self):
        return time.time() - self.t0


def load_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = sorted(k for k in raw if not k.startswith("_") and k not in DEFAULTS)
    if unknown:
        sys.exit(f"ERROR: unknown keys in {path}: {unknown}")
    cfg = {**DEFAULTS, **{k: v for k, v in raw.items() if not k.startswith("_")}}
    for name in ("inputs", "out", "cache", "model_path"):
        if not isinstance(cfg[name], str) or Path(cfg[name]).is_absolute():
            sys.exit(f"ERROR: {name} must be a path relative to the repository root")
    for name in ("out", "cache"):
        if (name == "out" or cfg[name]) and not (REPO / cfg[name]).resolve().is_relative_to((REPO / "out").resolve()):
            sys.exit(f"ERROR: {name} must be inside out/ in the repository root, not {cfg[name]!r}")
    packs = cfg["packs"]
    if (not isinstance(packs, dict) or not packs
            or any(not isinstance(v, str) or not k.strip() or not v.strip() for k, v in packs.items())):
        sys.exit("ERROR: packs must be a nonempty {pack_id pattern: language} map")
    langs, pairs = set(packs.values()), cfg["pairs"]
    if (not isinstance(pairs, list) or not pairs
            or any(not isinstance(p, list) or len(p) != 2 or not all(isinstance(x, str) for x in p)
                   or p[0] == p[1] or not set(p) <= langs for p in pairs)
            or len({frozenset(p) for p in pairs}) != len(pairs)):
        sys.exit(f"ERROR: pairs must be distinct [language, language] pairs of two languages in packs {sorted(langs)}")
    for name in POSITIVE:
        if type(cfg[name]) is not int or cfg[name] <= 0:
            sys.exit(f"ERROR: {name} must be a positive integer")
    for name in NONNEGATIVE:
        if type(cfg[name]) is not int or cfg[name] < 0:
            sys.exit(f"ERROR: {name} must be a nonnegative integer")
    if cfg["head_sentences"] > cfg["max_sentences"]:
        sys.exit("ERROR: head_sentences must be at most max_sentences")
    number = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    if not number(cfg["doc_floor"]) or not -1 <= cfg["doc_floor"] <= 1:
        sys.exit("ERROR: doc_floor must be a cosine between -1 and 1")
    for name in ("coverage_threshold", "report_floor"):
        if not number(cfg[name]) or not 0 <= cfg[name] <= 1:
            sys.exit(f"ERROR: {name} must be between 0 and 1")
    st = cfg["sentence_threshold"]
    if isinstance(st, dict):                                     # {"la-lb": value}, either order of a pair's name
        names = {**{f"{b}-{a}": f"{a}-{b}" for a, b in pairs}, **{f"{a}-{b}": f"{a}-{b}" for a, b in pairs}}
        named = [names.get(k) for k in st]
        if None in named or len(set(named)) < len(named):
            sys.exit(f"ERROR: sentence_threshold keys must each name a different language pair of pairs: "
                     f"{sorted(set(names.values()))} (either order)")
    if not all(number(v) and 0 <= v <= 1 for v in (st.values() if isinstance(st, dict) else [st])):
        sys.exit("ERROR: sentence_threshold must be between 0 and 1: one value, or a {language pair: value} map")
    if not number(cfg["max_length_ratio"]) or cfg["max_length_ratio"] < 1:
        sys.exit("ERROR: max_length_ratio must be at least 1")
    if not number(cfg["max_minutes"]) or cfg["max_minutes"] <= 0:
        sys.exit("ERROR: max_minutes must be above 0")
    if not number(cfg["max_output_mb"]) or not 0 < cfg["max_output_mb"] <= 50:
        sys.exit("ERROR: max_output_mb must be above 0 and at most 50 (JOB_REQUEST.md)")
    for name in ("mutual", "sync_debug"):
        if type(cfg[name]) is not bool:
            sys.exit(f"ERROR: {name} must be true or false")
    if cfg["device"] not in ("auto", "cpu", "mps", "cuda"):
        sys.exit("ERROR: device must be auto, cpu, mps or cuda")
    if cfg["precision"] not in PRECISIONS:
        sys.exit(f"ERROR: precision must be one of {', '.join(PRECISIONS)}")
    return cfg


def lang_of(pack, packs):
    """The language of the first pattern in packs that matches pack_id, or None (the pack is not read)."""
    for pattern, lang in packs.items():
        if fnmatch.fnmatchcase(pack, pattern):
            return lang
    return None


def sentence_thresholds(cfg):
    """The sentence threshold of each configured language pair, by its name "la-lb" as in pairs: sentence_threshold
    when it is one value; from a map, the pair's value under either order of its name, or SENTENCE_THRESHOLD."""
    st = cfg["sentence_threshold"]
    if not isinstance(st, dict):
        return {f"{a}-{b}": float(st) for a, b in cfg["pairs"]}
    return {f"{a}-{b}": float(st.get(f"{a}-{b}", st.get(f"{b}-{a}", SENTENCE_THRESHOLD))) for a, b in cfg["pairs"]}


def find_parts(inputs):
    """The Parquet parts to read, as (split, part, path). With a train/ or heldout/ folder under inputs (TSAI's cleaned
    output), only the parts under those folders, and part is the path under the split folder, as overlap.py names it.
    Otherwise (the raw <pack>/Part_N/ layout) every part, part is the path under inputs, and a folder named heldout, in
    any case, makes a part held-out. Pack identity comes only from each row's pack_id."""
    if not inputs.is_dir():
        sys.exit(f"ERROR: no input folder {inputs}")
    roots = [(s, inputs / s) for s in SPLITS if (inputs / s).is_dir()] or [(None, inputs)]
    parts = []
    for split, root in roots:
        for path in sorted(root.rglob("*.parquet")):
            rel = path.relative_to(root)
            if path.is_file() and not any(c.startswith(".") for c in rel.parts):
                s = split or ("heldout" if any(c.lower() == "heldout" for c in rel.parts[:-1]) else "train")
                parts.append((s, rel.as_posix(), path))
    if not parts:
        sys.exit(f"ERROR: no Parquet parts under {inputs}")
    return parts


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def peak_rss_mb():
    """The peak resident memory of this process in MiB; None without the resource module (Windows)."""
    if resource is None:
        return None
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss   # bytes on macOS, KiB on Linux
    return round(r / (1 << 20) if sys.platform == "darwin" else r / 1024, 1)


def write_csv(path, columns):
    """columns: {name: values}, in order. pyarrow quotes every string field ("needed" covers any string, since it
    could hold a quote or a comma); csv.DictReader, as in h3_join.py, reads it unchanged."""
    pacsv.write_csv(pa.table(columns), path, write_options=pacsv.WriteOptions(quoting_style="needed"))


def floats(x, digits=6):
    """A float column rounded to digits; NaN is written as an empty field."""
    x = np.asarray(x, dtype=np.float64)
    return pa.array(np.round(x, digits), mask=np.isnan(x))


def histogram(values):
    """Counts in 100 bins of 0.01 over [0, 1]; values below 0 go to the first bin."""
    v = np.clip(np.asarray(values, dtype=np.float64), 0.0, 1.0)
    return np.bincount(np.minimum((v * 100 + 1e-9).astype(np.int64), 99), minlength=100)


def bools(x):
    return np.asarray(x.to_numpy(zero_copy_only=False), dtype=bool)


def move(t, device):
    """A tensor on device: on CUDA a CPU tensor is copied from pinned memory without blocking the host, so the copy
    is no host-device sync. Values that are not tensors are returned as they are."""
    if not isinstance(t, torch.Tensor):
        return t
    if torch.device(device).type == "cuda" and t.device.type == "cpu":
        return t.pin_memory().to(device, non_blocking=True)
    return t.to(device)


def to_device(a, device, dtype=None):
    """A numpy array (int64 unless dtype is given) as a torch tensor on device, through move()."""
    return move(torch.from_numpy(np.ascontiguousarray(a, dtype=dtype or np.int64)), device)


def string_column(col, path, name):
    """A column as a string array; large strings, dictionaries of strings and all-null columns are cast."""
    col = col.combine_chunks() if isinstance(col, pa.ChunkedArray) else col
    t = col.type
    if t == pa.string():
        return col
    if (pa.types.is_large_string(t) or pa.types.is_null(t)
            or (pa.types.is_dictionary(t) and (pa.types.is_string(t.value_type)
                                               or pa.types.is_large_string(t.value_type)))):
        return pc.cast(col, pa.string())
    sys.exit(f"ERROR: {path} column {name} is {t}, not text")


def resolve_device(name):
    if name != "auto":
        return name
    return "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"


def resolve_dtype(precision, device):
    if precision == "auto":
        precision = "fp16" if device == "cuda" else "fp32"
    return {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[precision], precision


class Encoder:
    """The sentence-transformers model in model_path, loaded offline, on device in dtype. encode() runs the model's own
    preprocessing and forward pass in batches and returns its rows as one tensor on the device."""

    def __init__(self, cfg, device, dtype):
        os.environ["HF_HUB_OFFLINE"] = "1"         # never download: the model must already be in model_path
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        path = REPO / cfg["model_path"]
        if not cfg["model_path"] or not path.is_dir():
            sys.exit(f"ERROR: model_path {cfg['model_path']!r} is not a local folder; the model is never downloaded")
        try:
            import sentence_transformers
            from sentence_transformers import SentenceTransformer
        except ImportError:
            sys.exit("ERROR: needs sentence-transformers: "
                     "python3 -m pip install -r teams/01-data-a/dedup/requirements_h3.txt")
        self.model = SentenceTransformer(str(path), device=device)
        if dtype != torch.float32:
            self.model = self.model.to(dtype)
        self.model.eval()
        self.model.max_seq_length = cfg["max_seq_length"]
        self.batch_size, self.device, self.dtype = cfg["batch_size"], torch.device(device), dtype
        name = self.model.default_prompt_name
        self.prompt = self.model.prompts.get(name) if name else None   # the prompt encode() would add; LaBSE has none
        weights = {p.relative_to(path).as_posix(): {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
                   for p in sorted(path.rglob("*")) if p.is_file() and p.suffix in (".safetensors", ".bin")
                   and ".cache" not in p.relative_to(path).parts}
        config_sha = sha256_file(path / "config.json") if (path / "config.json").is_file() else ""
        dim = getattr(self.model, "get_embedding_dimension", None) or self.model.get_sentence_embedding_dimension
        self.dim = dim()
        self.info = {"path": cfg["model_path"], "name": path.name, "device": device, "dtype": str(dtype),
                     "max_seq_length": cfg["max_seq_length"], "dim": self.dim,
                     "config_sha256": config_sha, "weights": weights,
                     "sentence_transformers": sentence_transformers.__version__}
        self.id = hashlib.sha256(json.dumps([config_sha, weights, cfg["max_seq_length"], str(dtype)],
                                            sort_keys=True).encode()).hexdigest()

    def encode(self, texts):
        """The sentence embedding of each text of a list, in order, as one tensor on the device. batch_size texts per
        forward pass: each batch is tokenized at once and copied to the device with move(), so on CUDA the host
        prepares the next batch while the device runs this one, and the batch's rows are written into the output in
        one step. SentenceTransformer.encode() is not used: it splits every batch into rows in Python, stacks them
        again, and copies each batch to the device with a host-device sync."""
        out = torch.empty((len(texts), self.dim), device=self.device, dtype=self.dtype)
        for lo in range(0, len(texts), self.batch_size):           # batches of texts: one forward pass each
            features = self.model.preprocess(texts[lo:lo + self.batch_size], prompt=self.prompt)
            features = {k: move(v, self.device) for k, v in features.items()}
            out[lo:lo + self.batch_size] = self.model(features)["sentence_embedding"]
        return out


def encode(encoder, texts, clock, stats, counter, device, dtype):
    """Unit vectors of a string array of texts, on device in dtype, in the texts' order. The texts go to the encoder
    longest first, so each batch pads little: one encoder call per CHUNK texts, the time limit checked before each,
    and each call's rows written into their places in one output tensor on the device."""
    order = np.asarray(pc.array_sort_indices(pc.utf8_length(texts), order="descending"), dtype=np.int64)
    out = torch.zeros((len(texts), 0), device=device, dtype=dtype)
    for lo in range(0, len(texts), CHUNK):                       # chunks of texts: one encoder call each
        clock.check()
        ix = order[lo:lo + CHUNK]
        chunk = texts.take(pa.array(ix)).to_pylist()              # the tokenizer takes Python strings
        v = unit(torch.as_tensor(encoder.encode(chunk), device=device)).to(dtype)
        if lo == 0:
            out = torch.empty((len(texts), v.shape[1]), device=device, dtype=dtype)
        out.index_copy_(0, to_device(ix, device), v)
        stats[counter] += len(chunk)
    return out


def encode_heads(encoder, heads, rows, path, cfg, cache, clock, stats, device, dtype):
    """One vector per document of a part; from the cache when the same encoder, part bytes, settings and rows were
    encoded before."""
    file = None
    if cache:
        with clock.stage("cache"):
            settings = {k: cfg[k] for k in ("min_chars", "min_sentences", "sentence_min_chars", "head_sentences",
                                            "max_sentences")}
            h = hashlib.sha256()
            for piece in (encoder.id, sha256_file(path), json.dumps(settings, sort_keys=True)):
                h.update(piece.encode())
            h.update(np.asarray(rows, dtype=np.int64).tobytes())
            file = cache / f"{h.hexdigest()}.npy"
            if file.is_file():
                v = np.load(file)
                if len(v) == len(heads):
                    stats["cached_parts"] += 1
                    return unit(torch.from_numpy(v).to(device)).to(dtype)
    with clock.stage("encode"):
        v = encode(encoder, heads, clock, stats, "encoded_heads", device, dtype)
    if file is not None:
        cache.mkdir(parents=True, exist_ok=True)
        np.save(file, v.to(torch.float16).cpu().numpy())         # the cache's one copy of the part to the host
    return v


def select_documents(batch, row0, pack_set, cfg, counts, path):
    """The documents of one record batch to compare, found with no loop over rows: the rows of a configured pack that
    are long enough (min_chars, min_sentences), at most max_docs_per_pack per pack. Adds to counts (examined, eligible
    and taken documents per pack) and returns their columns and heads, or None."""
    examined, eligible, taken = counts
    pidx = pc.index_in(string_column(batch.column(0), path, "pack_id"), value_set=pack_set)
    sel = bools(pc.is_valid(pidx))
    if not sel.any():
        return None
    mask, rows = pa.array(sel), row0 + np.flatnonzero(sel)
    pack = np.asarray(pidx.filter(mask), dtype=np.int64)
    doc_id = string_column(batch.column(1), path, "doc_id").filter(mask)
    bad = bools(pc.fill_null(pc.equal(pc.utf8_length(pc.utf8_trim_whitespace(doc_id)), 0), True))
    if bad.any():
        k = int(np.flatnonzero(bad)[0])
        sys.exit(f"ERROR: {path} row {rows[k]} has invalid doc_id {doc_id[k].as_py()!r}")
    text = pc.fill_null(string_column(batch.column(2), path, "text").filter(mask), "")
    chars = np.asarray(pc.utf8_length(text), dtype=np.int64)
    sents, parent = sentences_batch(text, cfg["sentence_min_chars"], cfg["max_sentences"])
    nsent = np.bincount(parent, minlength=len(pack))
    ok = (chars >= cfg["min_chars"]) & (nsent >= cfg["min_sentences"])
    examined += np.bincount(pack, minlength=len(examined))
    eligible += np.bincount(pack[ok], minlength=len(eligible))
    take = ok.copy()
    if cfg["max_docs_per_pack"]:
        e = np.flatnonzero(ok)
        e = e[np.argsort(pack[e], kind="stable")]                 # eligible rows by pack, in row order within each
        take[e] = rank_in_group(pack[e]) < cfg["max_docs_per_pack"] - taken[pack[e]]
    taken += np.bincount(pack[take], minlength=len(taken))
    t = np.flatnonzero(take)
    if not len(t):
        return None
    ti = pa.array(t)
    url = (url_keys(string_column(batch.column(3), path, "url").filter(mask).take(ti)) if batch.num_columns > 3
           else pa.nulls(len(t), pa.string()))
    return {"pack": pack[t], "row_in_part": rows[t], "doc_id": doc_id.take(ti), "chars": chars[t],
            "sentences": nsent[t], "url": url,
            "head": head_texts(sents, parent, len(pack), cfg["head_sentences"]).take(ti)}


def url_pairs(keys, max_group):
    """Every pair (a, b), a < b, of documents with the same URL key, in groups of at most max_group documents; and the
    number of groups with 2 or more documents and of those over max_group."""
    g = np.asarray(pc.fill_null(pc.dictionary_encode(keys).indices, -1), dtype=np.int64)
    docs = np.flatnonzero(g >= 0)
    docs = docs[np.argsort(g[docs], kind="stable")]               # by key, then document
    empty = np.zeros(0, np.int64)
    if not len(docs):
        return empty, empty, 0, 0
    gs = g[docs]
    starts = np.flatnonzero(np.concatenate(([True], gs[1:] != gs[:-1])))
    sizes = np.diff(np.concatenate((starts, [len(gs)])))
    a, b = [empty], [empty]
    for size in np.unique(sizes[(sizes >= 2) & (sizes <= max_group)]).tolist():   # distinct group sizes only
        first = starts[sizes == size][:, None]
        i, j = np.triu_indices(size, 1)
        a.append(docs[(first + i).ravel()])
        b.append(docs[(first + j).ravel()])
    return np.concatenate(a), np.concatenate(b), int((sizes >= 2).sum()), int((sizes > max_group).sum())


def row_cosines(V, a, b, device):
    """The cosine of each document pair (a[p], b[p]), in one step."""
    if not len(a):
        return np.zeros(0, np.float32)
    return (V[to_device(a, device)].float() * V[to_device(b, device)].float()).sum(1).cpu().numpy()


def merge_pairs(a, b, cos, how, n):
    """One row per document pair (a < b): the cosine of its first listing and how it was found (1 embedding, 2 URL)."""
    if not len(a):
        return a, b, cos, how
    key = a * n + b
    order = np.argsort(key, kind="stable")
    key, cos, how = key[order], cos[order], how[order]
    u, first = np.unique(key, return_index=True)
    return u // n, u % n, cos[first], np.bitwise_or.reduceat(how, first)


def read_texts(docs, part_ix, row_in_part, paths, clock):
    """The text of each document in docs, in that order, reading only the row groups of each part that hold them."""
    pieces, where = [], []
    pdocs = part_ix[docs]
    for part in np.unique(pdocs).tolist():                        # the parts that hold the documents
        clock.check()
        at = np.flatnonzero(pdocs == part)
        rows = row_in_part[docs[at]]
        pf = pq.ParquetFile(paths[part])
        sizes = np.array([pf.metadata.row_group(g).num_rows for g in range(pf.num_row_groups)], np.int64)  # footer
        starts = np.concatenate(([0], np.cumsum(sizes)))
        rg = np.searchsorted(starts, rows, side="right") - 1
        need = np.unique(rg)
        base = np.concatenate(([0], np.cumsum(sizes[need])[:-1]))
        local = rows - starts[rg] + base[np.searchsorted(need, rg)]
        col = pf.read_row_groups(need.tolist(), columns=["text"]).column(0)
        pieces.append(string_column(col, paths[part], "text").take(pa.array(local)))
        where.append(at)
    if not pieces:
        return pa.array([], pa.string())
    return pc.fill_null(pa.concat_arrays(pieces).take(pa.array(np.argsort(np.concatenate(where)))), "")


def estimate(cfg, clock, stats, langs, pack_lang, rows_total, counts, verified):
    """The time for every document of the selected packs, from this run's rates: read scales with rows, encode with
    documents, retrieve with the product of the two languages' documents, verify with the smaller language's documents
    (at most max_verify pairs)."""
    examined, eligible, taken = counts
    st, L = clock.stages, {lang: i for i, lang in enumerate(langs)}
    now = np.bincount(pack_lang, weights=taken, minlength=len(langs))
    share = np.divide(eligible, examined, out=np.zeros(len(eligible)), where=examined > 0)
    full = np.bincount(pack_lang, weights=rows_total * share, minlength=len(langs))
    product = lambda c: sum(c[L[a]] * c[L[b]] for a, b in cfg["pairs"])
    smaller = lambda c: sum(min(c[L[a]], c[L[b]]) for a, b in cfg["pairs"])
    scanned, total_rows = stats["rows_scanned"], int(rows_total.sum())
    sec = {"load_model": st.get("load_model", 0.0),
           "read": st.get("read", 0.0) * total_rows / scanned if scanned else None,
           "encode": (st["encode"] / stats["encoded_heads"] * float(full.sum())
                      if stats["encoded_heads"] and st.get("encode") else None),
           "retrieve": st.get("retrieve", 0.0) * product(full) / product(now) if product(now) else None}
    pairs_full = min(cfg["max_verify"], verified * smaller(full) / smaller(now)) if smaller(now) else 0
    verify_time = st.get("verify_read", 0.0) + st.get("verify", 0.0)
    sec["verify"] = verify_time / verified * pairs_full if verified else None
    known = [v for v in sec.values() if v is not None]
    total = sum(known)
    return {"documents_encoded": {lang: int(now[i]) for lang, i in L.items()},
            "documents_full": {lang: round(float(full[i])) for lang, i in L.items()},
            "seconds": {k: (round(v, 1) if v is not None else None) for k, v in sec.items()},
            "minutes_total": round(total / 60, 1), "every_stage_measured": len(known) == len(sec),
            "suggested_max_time_minutes": math.ceil(1.5 * total / 60) if known else None,
            "basis": "this run's rates; read scales with rows, encode with documents, retrieve with the product of the "
                     "two languages' documents, verify with the smaller language's documents (at most max_verify)"}


def run(cfg, encoder, device, dtype, clock, stats, summary):
    inputs, out = REPO / cfg["inputs"], REPO / cfg["out"]
    cache = REPO / cfg["cache"] if cfg["cache"] else None
    parts = find_parts(inputs)

    # 1. Select the parts by their pack_id column.
    selected, rows_total = [], Counter()
    with clock.stage("read"):
        for split, name, path in parts:
            pf = pq.ParquetFile(path)
            missing = {"pack_id", "doc_id", "text"} - set(pf.schema_arrow.names)
            if missing:
                sys.exit(f"ERROR: {path} has no {sorted(missing)} column (it has {pf.schema_arrow.names})")
            vc = pc.value_counts(pf.read(columns=["pack_id"]).column(0))
            in_part = dict(zip(vc.field("values").to_pylist(), vc.field("counts").to_pylist()))   # one per pack
            keep = sorted(p for p in in_part if isinstance(p, str) and lang_of(p, cfg["packs"]))
            if keep:
                selected.append((split, name, path, keep, "url" in pf.schema_arrow.names))
                for p in keep:
                    rows_total[p] += in_part[p]
    if not selected:
        sys.exit(f"ERROR: no part under {inputs} holds a pack matching {sorted(cfg['packs'])}")
    print(f"{len(selected)} of {len(parts)} parts hold a configured pack: {', '.join(sorted(rows_total))}", flush=True)

    # 2. Read the selected parts in record batches: sentences, length, URL key and the head of each document; encode
    #    each part's heads.
    packs, langs = sorted(rows_total), sorted(set(cfg["packs"].values()))
    pack_lang = np.array([langs.index(lang_of(p, cfg["packs"])) for p in packs], np.int64)
    counts = tuple(np.zeros(len(packs), np.int64) for _ in range(3))      # examined, eligible, taken per pack
    pack_set, limit, cols, vectors = pa.array(packs, pa.string()), cfg["max_docs_per_pack"], defaultdict(list), []
    for part_no, (split, name, path, keep, has_url) in enumerate(selected):
        keep_ix = np.searchsorted(np.array(packs), keep)
        if limit and (counts[2][keep_ix] >= limit).all():
            print(f"{split}/{name}: not read, its packs have max_docs_per_pack documents", flush=True)
            continue
        got = []
        with clock.stage("read"):
            columns = ["pack_id", "doc_id", "text"] + (["url"] if has_url else [])
            row0 = 0
            for batch in pq.ParquetFile(path).iter_batches(batch_size=BATCH_ROWS, columns=columns):
                clock.check()
                docs = select_documents(batch, row0, pack_set, cfg, counts, path)
                if docs:
                    got.append(docs)
                row0 += batch.num_rows
                stats["rows_scanned"] += batch.num_rows
                if limit and (counts[2][keep_ix] >= limit).all():
                    break
        n_docs = 0
        if got:
            rows = np.concatenate([d["row_in_part"] for d in got])
            heads = pa.concat_arrays([d["head"] for d in got])
            vectors.append(encode_heads(encoder, heads, rows, path, cfg, cache, clock, stats, device, dtype))
            for d in got:
                for k in ("pack", "row_in_part", "doc_id", "chars", "sentences", "url"):
                    cols[k].append(d[k])
            cols["part"].append(np.full(len(rows), part_no))
            cols["split"].append(np.full(len(rows), SPLITS.index(split)))
            n_docs = len(rows)
        print(f"{split}/{name}: {n_docs} documents encoded or cached ({clock.elapsed():.0f}s)", flush=True)
    N = int(sum(len(p) for p in cols["pack"]))
    if N < 2:
        sys.exit(f"ERROR: {N} document(s) long enough to compare")
    cat = lambda k: np.concatenate(cols[k])
    pack_ix, part_ix, split_ix, row_in_part = cat("pack"), cat("part"), cat("split"), cat("row_in_part")
    chars, nsent, lang_ix = cat("chars"), cat("sentences"), pack_lang[cat("pack")]
    doc_id, url = pa.concat_arrays(cols["doc_id"]), pa.concat_arrays(cols["url"])
    V = torch.cat(vectors)
    thresholds = sentence_thresholds(cfg)
    allowed = np.zeros((len(langs), len(langs)), bool)
    threshold = np.zeros((len(langs), len(langs)), np.float32)    # the sentence threshold of each language pair
    for la, lb in cfg["pairs"]:                                   # the configured language pairs
        x, y = langs.index(la), langs.index(lb)
        allowed[x, y] = allowed[y, x] = True
        threshold[x, y] = threshold[y, x] = thresholds[f"{la}-{lb}"]
    if cfg["sync_debug"] and device == "cuda":
        torch.cuda.set_sync_debug_mode("warn")

    # 3. URL: the same page in two languages, by an exact join on the language-neutral URL key.
    with clock.stage("url"):
        ua, ub, groups, over = url_pairs(url, cfg["url_group_max"])
        keep = allowed[lang_ix[ua], lang_ix[ub]]
        ua, ub = ua[keep], ub[keep]
        ucos = row_cosines(V, ua, ub, device)
    url_stats = {"groups_with_2_or_more": groups, "groups_over_url_group_max": over, "pairs": int(len(ua))}

    # 4. Retrieve: each document's top_k nearest documents in the other language.
    hist_cos, retrieved, ea, eb, ec = np.zeros(100, np.int64), {}, [], [], []
    with clock.stage("retrieve"):
        for la, lb in cfg["pairs"]:
            ia, ib = np.flatnonzero(lang_ix == langs.index(la)), np.flatnonzero(lang_ix == langs.index(lb))
            name = f"{la}-{lb}"
            retrieved[name] = {"documents_a": int(len(ia)), "documents_b": int(len(ib)), "pairs_in_top_k": 0, "kept": 0}
            if not len(ia) or not len(ib):
                continue
            i, j, cos, side = cross_topk(V[to_device(ia, device)], V[to_device(ib, device)], cfg["top_k"],
                                         cfg["block"], clock.check)
            hist_cos += histogram(cos)
            keep = cos >= cfg["doc_floor"]
            if cfg["mutual"]:
                keep &= side == 3
            x, y = ia[i[keep]], ib[j[keep]]
            ea.append(np.minimum(x, y))
            eb.append(np.maximum(x, y))
            ec.append(cos[keep])
            retrieved[name].update(pairs_in_top_k=int(len(cos)), kept=int(keep.sum()))
            print(f"retrieve {name}: {len(ia)} x {len(ib)} documents, {int(keep.sum())} candidates "
                  f"({clock.elapsed():.0f}s)", flush=True)
    n_emb = int(sum(len(x) for x in ea))
    ca, cb, ccos, chow = merge_pairs(np.concatenate(ea + [ua]), np.concatenate(eb + [ub]),
                                     np.concatenate(ec + [ucos]).astype(np.float32),
                                     np.concatenate([np.ones(n_emb, np.int8), np.full(len(ua), 2, np.int8)]), N)

    # 5. Verify: URL pairs first, then by cosine; the sentence alignment of every pair, in batches of pairs.
    by_url = (chow & 2) > 0
    lo_c, hi_c = np.minimum(chars[ca], chars[cb]), np.maximum(chars[ca], chars[cb]).astype(np.float64)
    ratio = np.divide(hi_c, lo_c, out=np.full(len(ca), np.inf), where=lo_c > 0)
    too_long = (ratio > cfg["max_length_ratio"]) & ~by_url
    order = np.lexsort((cb, ca, -ccos, ~by_url))
    order = order[~too_long[order]]
    not_verified = max(0, len(order) - cfg["max_verify"])
    order = order[:cfg["max_verify"]]
    va, vb, vcos, vhow, vratio = ca[order], cb[order], ccos[order], chow[order], ratio[order]
    paths = [path for _, _, path, _, _ in selected]
    with clock.stage("verify_read"):
        U = np.unique(np.concatenate([va, vb]))
        texts = read_texts(U, part_ix, row_in_part, paths, clock)
    with clock.stage("verify"):
        sents, parent = sentences_batch(texts, cfg["sentence_min_chars"], cfg["max_sentences"])
        count = np.bincount(parent, minlength=len(U))
        start = np.concatenate(([0], np.cumsum(count)[:-1]))
        E = encode(encoder, sents, clock, stats, "encoded_sentences", device, dtype)
        la, lb = np.searchsorted(U, va), np.searchsorted(U, vb)
        st, ct, ta, tb = (to_device(x, device) for x in (start, count, la, lb))
        tt = to_device(threshold[lang_ix[va], lang_ix[vb]], device, np.float32)   # each pair's sentence threshold
        step, n_al, means = cfg["pair_batch"], [], []
        for lo in range(0, len(va), step):                        # batches of pairs: one bmm each
            clock.check()
            n, m = align_batch(E, st, ct, ta[lo:lo + step], tb[lo:lo + step], tt[lo:lo + step], cfg["max_sentences"])
            n_al.append(n)
            means.append(m)
        aligned = torch.cat(n_al).cpu().numpy() if n_al else np.zeros(0, np.int64)    # the stage's copy to the host
        mean_cos = torch.cat(means).cpu().numpy() if means else np.zeros(0)
        na, nb = count[la], count[lb]
        shorter = np.minimum(na, nb)
        coverage = np.divide(aligned, shorter, out=np.zeros(len(va)), where=shorter > 0)
        qualifies = coverage >= cfg["coverage_threshold"]
        tok, tp = number_tokens(texts)
        sh, sa, sb = pair_overlap(tok, tp, len(U), la, lb, distinct=False)
        numbers_j = np.divide(sh, sa + sb - sh, out=np.full(len(va), np.nan), where=(sa + sb) > 0)
        tok, tp = latin_token_lists(texts)
        sh, sa, sb = pair_overlap(tok, tp, len(U), la, lb, distinct=True)
        latin = np.divide(sh, np.minimum(sa, sb), out=np.full(len(va), np.nan), where=np.minimum(sa, sb) > 0)
        print(f"verify: {len(va)} pairs ({clock.elapsed():.0f}s)", flush=True)
    hist_cov = histogram(coverage)

    # 6. Outputs, all inside ./out/: IDs, scores and counts only.
    out.mkdir(parents=True, exist_ok=True)
    take = lambda arr, ix: arr.take(pa.array(np.asarray(ix, dtype=np.int64)))
    pack_arr, lang_arr = take(pa.array(packs), pack_ix), take(pa.array(langs), lang_ix)
    split_arr, part_arr = take(pa.array(list(SPLITS)), split_ix), take(pa.array([s[1] for s in selected]), part_ix)
    ids = pc.binary_join_element_wise(pack_arr, doc_id, "-")
    pq.write_table(pa.table({"row": np.arange(N), "id": ids, "doc_id": doc_id, "pack": pack_arr, "lang": lang_arr,
                             "split": split_arr, "part": part_arr, "row_in_part": row_in_part, "chars": chars,
                             "sentences": nsent}), out / "h3_docs.parquet", compression="zstd")
    listed = (coverage >= cfg["report_floor"]) | ((vhow & 2) > 0)
    Li = np.flatnonzero(listed)
    Li = Li[np.lexsort((vb[Li], va[Li], -vcos[Li], -coverage[Li]))]   # highest coverage first
    a, b = va[Li], vb[Li]
    found = take(pa.array(["", "embedding", "url", "embedding+url"]), vhow[Li])
    write_csv(out / "h3_candidates.csv", {
        "row_a": a, "row_b": b, "id_a": take(ids, a), "id_b": take(ids, b), "pack_a": take(pack_arr, a),
        "pack_b": take(pack_arr, b), "lang_a": take(lang_arr, a), "lang_b": take(lang_arr, b),
        "split_a": take(split_arr, a), "split_b": take(split_arr, b), "found_by": found,
        "doc_cosine": floats(vcos[Li]), "length_ratio": floats(vratio[Li], 3), "numbers_jaccard": floats(numbers_j[Li]),
        "latin_share": floats(latin[Li]), "sentences_a": na[Li], "sentences_b": nb[Li], "aligned": aligned[Li],
        "coverage": floats(coverage[Li]), "mean_sentence_cosine": floats(mean_cos[Li]), "qualifies": qualifies[Li]})
    M = Li[qualifies[Li]]
    side = lambda ix, s: {f"pack_id_{s}": take(pack_arr, ix), f"split_{s}": take(split_arr, ix),
                          f"part_{s}": take(part_arr, ix), f"row_in_part_{s}": row_in_part[ix],
                          f"doc_id_{s}": take(doc_id, ix)}
    matches = {**side(va[M], "a"), **side(vb[M], "b"), "lang_a": take(lang_arr, va[M]),
               "lang_b": take(lang_arr, vb[M]), "coverage": floats(coverage[M])}
    assert list(matches) == MATCHES_HEADER
    write_csv(out / "h3_matches.csv", matches)
    K = len(packs)
    pack_pair = lambda x, y: np.minimum(pack_ix[x], pack_ix[y]) * K + np.maximum(pack_ix[x], pack_ix[y])
    ck, vk = pack_pair(ca, cb), pack_pair(va, vb)
    keys = np.unique(ck)
    tally = lambda k, w=None: np.bincount(np.searchsorted(keys, k), minlength=len(keys),
                                          weights=None if w is None else w.astype(np.float64)).astype(np.int64)
    write_csv(out / "h3_by_pack.csv", {
        "pack_a": take(pa.array(packs), keys // K), "pack_b": take(pa.array(packs), keys % K),
        "retrieved": tally(ck, (chow & 1) > 0), "url": tally(ck, (chow & 2) > 0), "verified": tally(vk),
        "listed": tally(vk, listed), "qualifying": tally(vk, qualifies)})
    write_csv(out / "h3_histogram.csv", {"from": [f"{x / 100:.2f}" for x in range(100)],   # the 100 bin edges
                                         "to": [f"{(x + 1) / 100:.2f}" for x in range(100)],
                                         "retrieved_pairs_doc_cosine": hist_cos, "verified_pairs_coverage": hist_cov})

    files = {f: {"bytes": (out / f).stat().st_size, "sha256": sha256_file(out / f)} for f in OUTPUTS}
    output_bytes = sum(v["bytes"] for v in files.values())
    nl = len(langs)
    lk, ln = np.unique(lang_ix[va[M]] * nl + lang_ix[vb[M]], return_counts=True)
    examined, eligible, taken = counts
    summary.update({
        "status": "complete",
        "inputs": {"root": cfg["inputs"], "parts_found": len(parts), "parts_selected": len(selected),
                   "parts": [f"{s}/{n}" for s, n, *_ in selected]},
        "documents": {p: {"lang": langs[pack_lang[i]], "rows_in_parts": rows_total[p], "read": int(examined[i]),
                          "too_short": int(examined[i] - eligible[i]), "encoded": int(taken[i])}
                      for i, p in enumerate(packs)},
        "documents_compared": N,
        "url": url_stats,
        "retrieved": retrieved,
        "candidates": int(len(ca)),
        "rejected_length_ratio": int(too_long.sum()),
        "not_verified_over_max_verify": not_verified,
        "verified": int(len(va)),
        "listed": int(len(Li)),
        "qualifying": int(len(M)),
        "qualifying_heldout_train": int((split_ix[va[M]] != split_ix[vb[M]]).sum()),
        "qualifying_by_language_pair": {f"{langs[k // nl]}-{langs[k % nl]}": int(c)
                                        for k, c in zip(lk.tolist(), ln.tolist())},
        "rule": {"h3": f"aligned sentences / sentences of the shorter document >= {cfg['coverage_threshold']}; "
                       "a sentence pair aligns when each is the other's best match with cosine >= the language "
                       "pair's sentence threshold",
                 "sentence_threshold": thresholds,
                 "thresholds": "provisional: set by E5's sweep and hand review"},
        "counts": dict(stats),
        "stages_seconds": dict(clock.stages),
        "rates": {"heads_per_second": (round(stats["encoded_heads"] / clock.stages["encode"], 1)
                                       if clock.stages.get("encode") else None),
                  "sentences_per_second": (round(stats["encoded_sentences"] / clock.stages["verify"], 1)
                                           if clock.stages.get("verify") else None)},
        "estimate_all_documents": estimate(cfg, clock, stats, langs, pack_lang,
                                           np.array([rows_total[p] for p in packs], np.float64), counts, len(va)),
        "wall_seconds": round(clock.elapsed(), 1),
        "peak_rss_mb": peak_rss_mb(),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pyarrow": pa.__version__,
                     "torch": torch.__version__, "platform": platform.platform()},
        "outputs": files,
        "output_mb": round(output_bytes / (1 << 20), 2),
    })
    (out / "h3_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    shown = ("documents_compared", "url", "retrieved", "candidates", "verified", "qualifying",
             "qualifying_heldout_train", "qualifying_by_language_pair", "stages_seconds", "rates",
             "estimate_all_documents", "wall_seconds", "peak_rss_mb")
    print(json.dumps({k: summary[k] for k in shown}, indent=2))
    print(f"\nWrote {', '.join(OUTPUTS)} and h3_summary.json to {out.relative_to(REPO)}")
    if output_bytes + (out / "h3_summary.json").stat().st_size > cfg["max_output_mb"] * (1 << 20):
        summary["status"] = "failed_output_limit"
        (out / "h3_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        sys.exit(f"ERROR: the outputs are over max_output_mb {cfg['max_output_mb']}; job failed")


def main(encoder=None):
    """encoder: for the tests, an object with .id, .info and .encode(texts); by default the model in model_path."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="JSON config; see CONFIG above")
    cfg = load_config(ap.parse_args().config)
    if np is None:
        sys.exit("ERROR: needs numpy, pyarrow and torch: "
                 "python3 -m pip install -r teams/01-data-a/dedup/requirements_h3.txt")
    device = resolve_device(cfg["device"])
    dtype, precision = resolve_dtype(cfg["precision"], device)
    if device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    clock, stats, out = Clock(cfg["max_minutes"]), Counter(), REPO / cfg["out"]
    summary = {"status": "running", "config": cfg, "device": device, "precision": precision}
    try:
        if encoder is None:
            with clock.stage("load_model"):
                encoder = Encoder(cfg, device, dtype)
        summary["model"] = encoder.info
        with torch.inference_mode():
            run(cfg, encoder, device, dtype, clock, stats, summary)
    except TimeLimit:
        out.mkdir(parents=True, exist_ok=True)
        for f in OUTPUTS:                     # no output of an earlier run may sit beside this summary
            (out / f).unlink(missing_ok=True)
        summary.update(status="stopped_time_limit", counts=dict(stats), stages_seconds=dict(clock.stages),
                       wall_seconds=round(clock.elapsed(), 1), peak_rss_mb=peak_rss_mb())
        (out / "h3_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        sys.exit(f"ERROR: stopped at max_minutes {cfg['max_minutes']}; the run is incomplete and must not be used")
    finally:
        if cfg["sync_debug"] and device == "cuda":
            torch.cuda.set_sync_debug_mode(0)


if __name__ == "__main__":
    sys.exit(main())
