"""The fingerprint set on disk, and the lookup that decontam_check.py uses.

    fingerprints/v1/
        MANIFEST.json          version, normalize ID, set_sha256, one entry per benchmark
        SHA256SUMS             sha256 of every file, path relative to the set folder
        <benchmark>/MANIFEST.json, n13-000.tsv, n20-000.tsv ..., canaries.txt

Shard line: <item_ref> TAB <hash> <hash> ...   (hashes sorted and unique for each item)
A shard holds the hashes of one run length (n13 = 13 words, n20 = 20 code tokens).
set_sha256 is the sha256 of SHA256SUMS. Each benchmark folder can be rebuilt alone.
"""

import hashlib
import json
from pathlib import Path

from lab_canary import LAB_CANARY, LAB_CANARY_ID, read_canary_file
from normalize import DESCRIPTION, NORMALIZE_ID, normalize, words_with_offsets

VERSION = "v1"
HASH_BYTES = 8  # blake2b, 64 bits, written as 16 hex characters
MAX_SHARD_BYTES = 4_000_000  # the repo limit is 5 MB for each file

# Build-time filters. A gram that a filter matches carries no benchmark content, so it is not
# written. Measured on the 38 sample packs (19,000 documents):
#   numeric_only  "1 2 3 ... 13" in solutions and patches
#   single_chars  "a b c d ... m" (alphabets in tests)
GRAM_FILTERS = {
    "numeric_only": lambda g: all(w.isdigit() for w in g),
    "single_chars": lambda g: all(len(w) == 1 for w in g),
}
DEFAULT_GRAM_FILTERS = ("numeric_only", "single_chars")

# Boilerplate: text that is in benchmark items but also in millions of other documents
# (licence headers in SWE-bench patches, lorem ipsum). A gram is not written when at least
# half of its words are inside a boilerplate run of BOILERPLATE_N words.
BOILERPLATE_DIR = Path(__file__).resolve().parent / "boilerplate"
BOILERPLATE_N = 8


def gram_hash(gram_words):
    return hashlib.blake2b(" ".join(gram_words).encode("utf-8"), digest_size=HASH_BYTES).hexdigest()


class Boilerplate:
    def __init__(self, folder=BOILERPLATE_DIR):
        self.files = {}
        self.grams = set()
        for f in sorted(Path(folder).glob("*.txt")) if folder else []:
            data = f.read_bytes()
            self.files[f.name] = hashlib.sha256(data).hexdigest()
            ws = normalize(data.decode("utf-8"))
            self.grams.update(tuple(ws[i:i + BOILERPLATE_N]) for i in range(len(ws) - BOILERPLATE_N + 1))

    def covered(self, ws):
        """For each word: is it inside a boilerplate run?"""
        cov = [False] * len(ws)
        if self.grams:
            for i in range(len(ws) - BOILERPLATE_N + 1):
                if tuple(ws[i:i + BOILERPLATE_N]) in self.grams:
                    cov[i:i + BOILERPLATE_N] = [True] * BOILERPLATE_N
        return cov


# Short texts: a prose text of SHORT_MIN to n-1 words has no n-gram. It is stored as one hash of
# the whole text (at its own length), but only when no other item of the benchmark has the same
# text: shared short texts are templates ("which of the following statements is correct").
# Measured on the 38 sample packs: 37,539 short texts, the only matches were such templates.
SHORT_MIN = 8


def item_hashes(texts, n, gram_filters=DEFAULT_GRAM_FILTERS, boilerplate=None, short_min=None):
    """Hashes of the texts of one item (an item can have several text forms): {run length: set}.

    Every n-gram, and with short_min, the whole text when it has short_min to n-1 words.
    """
    drop = [GRAM_FILTERS[f] for f in gram_filters]
    out = {}
    for t in texts:
        ws = normalize(t)
        if short_min and short_min <= len(ws) < n:
            if not any(f(ws) for f in drop):
                out.setdefault(len(ws), set()).add(gram_hash(ws))
            continue
        cov = boilerplate.covered(ws) if boilerplate else None
        for i in range(len(ws) - n + 1):
            g = ws[i:i + n]
            if any(f(g) for f in drop) or (cov and 2 * sum(cov[i:i + n]) >= n):
                continue
            out.setdefault(n, set()).add(gram_hash(g))
    return out


def write_benchmark(set_dir, bid, items, n, meta=None, gram_filters=DEFAULT_GRAM_FILTERS, canaries=None,
                    boilerplate=None, short_min=SHORT_MIN):
    """Write one benchmark folder.

    items: iterable of (item_ref, {"prose": [texts], "code": [texts]}).
    n: run length for each kind, for example {"prose": 13, "code": 20}.
    canaries: a set that the items iterator fills while it runs (benchmark canary strings,
    for example the GPQA and HLE GUIDs). They are written to canaries.txt after the items.
    short_min: store whole short prose texts (see SHORT_MIN). None: no short texts.
    """
    out = Path(set_dir) / bid
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.tsv")) + list(out.glob("canaries.txt")):
        old.unlink()

    # Pass 1: hashes of every item. Short-text hashes of more than one item are templates.
    all_items, short_owners = [], {}
    for ref, texts in items:
        by_len = {}
        for kind, ts in texts.items():
            if ts:
                sm = short_min if kind == "prose" else None
                for length, hs in item_hashes(ts, n[kind], gram_filters, boilerplate, sm).items():
                    by_len.setdefault(length, set()).update(hs)
        for length, hs in by_len.items():
            if length < n["prose"]:
                for h in hs:
                    short_owners[h] = short_owners.get(h, 0) + 1
        all_items.append((ref, by_len))
    templates = {h for h, c in short_owners.items() if c > 1}

    # Pass 2: write the shards.
    shards = {}                          # run length -> list of file names
    lines = {}                           # run length -> (lines, size) not yet written
    n_items = n_empty = n_grams = n_short = 0

    def flush(length):
        buf, _ = lines.pop(length, ([], 0))
        if buf:
            names = shards.setdefault(length, [])
            fname = f"n{length}-{len(names):03d}.tsv"
            (out / fname).write_text("".join(buf), encoding="utf-8", newline="\n")
            names.append(fname)

    for ref, by_len in all_items:
        n_items += 1
        for length in [k for k in by_len if k < n["prose"]]:
            by_len[length] -= templates
        if not any(by_len.values()):
            n_empty += 1
            continue
        for length, hs in sorted(by_len.items()):
            if not hs:
                continue
            n_grams += len(hs)
            if length < n["prose"]:
                n_short += len(hs)
            line = ref + "\t" + " ".join(sorted(hs)) + "\n"
            buf, size = lines.get(length, ([], 0))
            if size + len(line) > MAX_SHARD_BYTES:
                flush(length)
                buf, size = [], 0
            buf.append(line)
            lines[length] = (buf, size + len(line))
    for length in list(lines):
        flush(length)
    if canaries:
        (out / "canaries.txt").write_text("".join(c + "\n" for c in sorted(canaries)), encoding="utf-8", newline="\n")
    manifest = {**(meta or {}), "id": bid, "n": n, "gram_filters": list(gram_filters),
                "boilerplate": boilerplate.files if boilerplate else {},
                "short_min": short_min, "short_texts": n_short, "short_templates_dropped": len(templates),
                "items": n_items, "items_without_ngram": n_empty, "item_grams": n_grams,
                "canaries": len(canaries or ()),
                "shards": {str(k): v for k, v in sorted(shards.items())}}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def _files(bm):
    return [f for names in bm["shards"].values() for f in names] + (["canaries.txt"] if bm.get("canaries") else [])


# The top MANIFEST.json is not in SHA256SUMS (it holds set_sha256). Its parts are checked another way:
# the summary of each benchmark against the benchmark's own MANIFEST.json, and not_covered against
# not_covered.json, which is in SHA256SUMS.
SUMMARY_KEYS = ("name", "tags", "n", "items", "items_without_ngram", "item_grams", "short_texts", "canaries")
NOT_COVERED_FILE = "not_covered.json"


def _summary(bm):
    return {k: bm[k] for k in SUMMARY_KEYS if k in bm}


def write_index(set_dir, not_covered=None):
    """Write the top MANIFEST.json, not_covered.json and SHA256SUMS. Returns set_sha256."""
    d = Path(set_dir)
    benches, sums = {}, []
    for m in sorted(d.glob("*/MANIFEST.json")):
        bm = json.loads(m.read_text(encoding="utf-8"))
        benches[bm["id"]] = _summary(bm)
        for fname in [m.name] + _files(bm):
            rel = f"{m.parent.name}/{fname}"
            sums.append(f"{hashlib.sha256((d / rel).read_bytes()).hexdigest()}  {rel}\n")
    nc = d / NOT_COVERED_FILE
    nc.write_text(json.dumps(not_covered or {}, indent=2) + "\n", encoding="utf-8", newline="\n")
    sums.append(f"{hashlib.sha256(nc.read_bytes()).hexdigest()}  {NOT_COVERED_FILE}\n")
    sums_text = "".join(sums)
    (d / "SHA256SUMS").write_text(sums_text, encoding="utf-8", newline="\n")
    set_id = hashlib.sha256(sums_text.encode("utf-8")).hexdigest()
    manifest = {
        "version": VERSION,
        "set_sha256": set_id,
        "normalize_id": NORMALIZE_ID,
        "normalize": DESCRIPTION,
        "hash": f"blake2b, digest_size={HASH_BYTES}, hex, of the n words joined by one space (UTF-8)",
        "line_format": "<item_ref>\\t<hash> <hash> ...",
        "benchmarks": benches,
        "not_covered": not_covered or {},
    }
    (d / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return set_id


class Fingerprints:
    """Load a set (all benchmarks, or only some) and check texts against it.

    benchmarks: list of benchmark IDs. tags: list of tags; a benchmark with any of them is loaded.
    With neither, all benchmarks are loaded. Only the full set counts as the formal check.
    """

    def __init__(self, set_dir, benchmarks=None, verify=True, tags=None):
        d = Path(set_dir)
        self.manifest = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
        if self.manifest["normalize_id"] != NORMALIZE_ID:
            raise ValueError(f"set uses normalize {self.manifest['normalize_id']}, this code uses {NORMALIZE_ID}")
        sums = (d / "SHA256SUMS").read_text(encoding="utf-8")
        if verify:
            if hashlib.sha256(sums.encode("utf-8")).hexdigest() != self.manifest["set_sha256"]:
                raise ValueError("SHA256SUMS does not match set_sha256 in MANIFEST.json")
            for line in sums.splitlines():
                want, rel = line.split("  ", 1)
                if hashlib.sha256((d / rel).read_bytes()).hexdigest() != want:
                    raise ValueError(f"{rel}: sha256 does not match SHA256SUMS")
            rels = [line.split("  ", 1)[1] for line in sums.splitlines()]
            folders = {rel.split("/")[0] for rel in rels if "/" in rel}
            if folders != set(self.manifest["benchmarks"]):
                raise ValueError("the benchmarks in MANIFEST.json do not match SHA256SUMS")
            for bid, summary in self.manifest["benchmarks"].items():
                bm = json.loads((d / bid / "MANIFEST.json").read_text(encoding="utf-8"))
                if summary != _summary(bm):
                    raise ValueError(f"{bid}: MANIFEST.json does not match {bid}/MANIFEST.json")
            if NOT_COVERED_FILE not in rels:
                raise ValueError(f"{NOT_COVERED_FILE} is not in SHA256SUMS")
            nc = json.loads((d / NOT_COVERED_FILE).read_text(encoding="utf-8"))
            if nc != self.manifest.get("not_covered", {}):
                raise ValueError(f"not_covered in MANIFEST.json does not match {NOT_COVERED_FILE}")
        self.set_sha256 = self.manifest["set_sha256"]
        all_b = self.manifest["benchmarks"]
        chosen = list(benchmarks or all_b)
        unknown = set(chosen) - set(all_b)
        if unknown:
            raise ValueError(f"not in this set: {sorted(unknown)}")
        if tags:
            chosen = [b for b in chosen if set(tags) & set(all_b[b].get("tags", []))]
            if not chosen:
                raise ValueError(f"no benchmark has the tags {tags}")
        self.benchmarks = chosen
        self.refs, self.size = [], []   # per item: ref and number of grams (all run lengths)
        index = {}                      # ref -> item index
        self.owner = {}                 # run length -> {hash (int) -> item index, or tuple of indexes}
        self.canaries = {LAB_CANARY: LAB_CANARY_ID}  # canary string -> benchmark ID (or the lab canary)
        for bid in chosen:
            bm = json.loads((d / bid / "MANIFEST.json").read_text(encoding="utf-8"))
            if bm.get("canaries"):
                for c in read_canary_file(d / bid / "canaries.txt"):  # stripped, no blank lines
                    self.canaries.setdefault(c, bid)
            for length, names in bm["shards"].items():
                table = self.owner.setdefault(int(length), {})
                for fname in names:
                    with open(d / bid / fname, encoding="utf-8") as f:
                        for line in f:
                            ref, hs = line.rstrip("\n").split("\t")
                            hs = hs.split(" ")
                            idx = index.get(ref)
                            if idx is None:
                                idx = index[ref] = len(self.refs)
                                self.refs.append(ref)
                                self.size.append(0)
                            self.size[idx] += len(hs)
                            for h in hs:
                                k = int(h, 16)
                                old = table.get(k)
                                if old is None:
                                    table[k] = idx
                                elif isinstance(old, tuple):
                                    table[k] = old + (idx,)
                                else:
                                    table[k] = (old, idx)

    def check(self, text, min_hits=1):
        """Return (flagged, hits). hits: list of dicts, best item first."""
        ws = words_with_offsets(text)
        matched, first = {}, {}   # matched: item -> unique grams found
        for n, table in self.owner.items():
            seen = set()
            for i in range(len(ws) - n + 1):
                k = int(gram_hash([w for w, _ in ws[i:i + n]]), 16)
                o = table.get(k)
                if o is None or k in seen:
                    continue
                seen.add(k)
                for idx in (o if isinstance(o, tuple) else (o,)):
                    matched[idx] = matched.get(idx, 0) + 1
                    first[idx] = min(first.get(idx, ws[i][1]), ws[i][1])
        hits = [{"item": self.refs[idx], "grams": c, "item_grams": self.size[idx],
                 "coverage": round(c / self.size[idx], 3), "offset": first[idx]}
                for idx, c in matched.items()]
        hits.sort(key=lambda h: (-h["coverage"], -h["grams"], h["item"]))
        # A benchmark canary string is an exact marker: one occurrence flags the document.
        canary_hits = [{"item": f"{bid}:canary", "canary": c, "offset": text.find(c)}
                       for c, bid in self.canaries.items() if c in text]
        flagged = bool(canary_hits) or any(h["grams"] >= min_hits for h in hits)
        return flagged, canary_hits + hits
