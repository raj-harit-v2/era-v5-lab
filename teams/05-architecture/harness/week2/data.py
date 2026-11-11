"""Document-isolated teacher forcing; every text token/byte scored once."""

from pathlib import Path
import json
import hashlib
import inspect
import os
import tempfile
from collections.abc import Sequence
import numpy as np
import torch


CACHE_FORMAT = 1
WINDOW_DTYPE = np.dtype([("start", "<u8"), ("length", "<u4"),
                         ("previous", "<u4"), ("slice", "u1")])


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _cache_identity(path, artifacts, seq_len, require_ids, sources_path):
    if type(seq_len) is not int or not 0 < seq_len < 2**32:
        raise ValueError("Cache sequence length must be a positive uint32")
    identity = {
        "format": CACHE_FORMAT, "input_sha256": _sha256(path),
        "artifacts": artifacts.identity(), "seq_len": seq_len,
        "require_ids": bool(require_ids),
        "sources_sha256": _sha256(sources_path) if sources_path else None,
        "data_implementation_sha256": _sha256(__file__),
        "encoder_implementation_sha256": _sha256(inspect.getfile(type(artifacts))),
    }
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return key, identity


class _MappedWindows(Sequence):
    def __init__(self, tokens, rows, artifacts):
        self.tokens, self.rows, self.artifacts = tokens, rows, artifacts

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        row = self.rows[index]
        start, length = int(row["start"]), int(row["length"])
        target = self.tokens[start:start + length].tolist()
        return ([int(row["previous"])] + target[:-1], target,
                [int(self.artifacts.lengths[i]) for i in target])


class _MappedSlices(Sequence):
    def __init__(self, rows, names):
        self.rows, self.names = rows, names

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        return self.names[int(self.rows[index]["slice"])]


def _load_window_cache(directory, identity, artifacts):
    """Verify once at open; batches only read numeric, read-only memory maps."""
    directory = Path(directory)
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf8"))
    if metadata["identity"] != identity:
        raise ValueError("Window cache identity mismatch")
    expected_names = {"tokens.bin", "windows.bin", "document_hashes.bin"}
    if set(metadata["files"]) != expected_names:
        raise ValueError("Unexpected window cache payloads")
    for name, receipt in metadata["files"].items():
        path = directory / name
        if path.is_symlink() or path.stat().st_size != receipt["bytes"]:
            raise ValueError("Window cache payload size/type mismatch")
        if _sha256(path) != receipt["sha256"]:
            raise ValueError("Window cache checksum mismatch")
    summary = metadata["summary"]
    counts = {"tokens.bin": summary["tokens"] * 4,
              "windows.bin": summary["windows"] * WINDOW_DTYPE.itemsize,
              "document_hashes.bin": summary["document_count"] * 32}
    if any(metadata["files"][k]["bytes"] != size for k, size in counts.items()):
        raise ValueError("Window cache count/size mismatch")
    if min(summary["tokens"], summary["windows"], summary["raw_bytes"],
           summary["document_count"]) <= 0:
        raise ValueError("Empty/zero-byte window cache")
    tokens = np.memmap(directory / "tokens.bin", mode="r", dtype="<u4")
    rows = np.memmap(directory / "windows.bin", mode="r", dtype=WINDOW_DTYPE)
    names = metadata["slice_names"]
    if (not names or names[0] is not None or len(names) > 256
            or np.any(rows["length"] == 0)
            or np.any(rows["length"] > identity["seq_len"])
            or np.any(rows["start"] + rows["length"] > len(tokens))
            or int(rows["slice"].max()) >= len(names)):
        raise ValueError("Invalid window cache index")
    if int(rows["length"].sum()) != len(tokens):
        raise ValueError("Window cache token conservation failed")
    if int(rows[0]["start"]) != 0 or np.any(
        rows["start"][1:] != rows["start"][:-1] + rows["length"][:-1]
    ) or np.any(rows["previous"] >= len(artifacts.lengths)):
        raise ValueError("Window cache coverage/previous-token mismatch")
    # Chunked checks bound temporary arrays for multi-billion-token corpora.
    byte_count = 0
    for start in range(0, len(tokens), 1024 * 1024):
        chunk = tokens[start:start + 1024 * 1024]
        if int(chunk.max()) >= len(artifacts.lengths):
            raise ValueError("Window cache token outside vocabulary")
        byte_count += int(np.asarray(artifacts.lengths)[chunk].sum(dtype=np.int64))
    if byte_count != summary["raw_bytes"]:
        raise ValueError("Window cache byte conservation failed")
    hashes = np.memmap(directory / "document_hashes.bin", mode="r", dtype="u1")
    return {
        "windows": _MappedWindows(tokens, rows, artifacts),
        "window_slices": _MappedSlices(rows, names),
        "raw_bytes": summary["raw_bytes"], "tokens": summary["tokens"],
        "document_count": summary["document_count"],
        "document_hashes": {bytes(row).hex() for row in hashes.reshape(-1, 32)},
        "slice_raw_bytes": summary["slice_raw_bytes"],
        "pad_id": artifacts.pad_id, "seq_len": identity["seq_len"],
    }


def build_window_cache(path, artifacts, seq_len, cache_dir, require_ids=False,
                       sources_path=None, encode_records=None, progress=None):
    """Stream an exact cache; optional ordered encoder yields (document, ids).

    The production CLI's workers call Artifacts.encode unchanged. The default
    encoder makes the same path testable with small, independent byte fixtures.
    """
    key, identity = _cache_identity(path, artifacts, seq_len, require_ids, sources_path)
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / key
    if destination.exists():
        _load_window_cache(destination, identity, artifacts)
        if progress:
            progress({"stage": "verified existing cache", "cache_key": key})
        return destination
    records = read_texts(path, require_ids=require_ids, records=True)
    slices = None
    if sources_path:
        from .scoring import source_slices
        # Source sidecars are heldout-sized; reuse the original exact validator.
        records = list(records)
        slices = iter(source_slices(sources_path, records))
    encoded = (encode_records(iter(records)) if encode_records else
               ((doc, artifacts.encode(doc["text"])) for doc in records))
    names = [None]
    summary = dict(raw_bytes=0, tokens=0, windows=0, document_count=0,
                   slice_raw_bytes={})
    with tempfile.TemporaryDirectory(prefix=f".{key}-", dir=root) as temporary:
        temporary = Path(temporary)
        with (temporary / "tokens.bin").open("wb") as token_file, \
                (temporary / "windows.bin").open("wb") as window_file, \
                (temporary / "document_hashes.bin").open("wb") as hash_file:
            for doc, ids in encoded:
                raw = doc["text"].encode("utf8")
                size = len(raw)
                ids = np.asarray(ids) if len(ids) else np.empty(0, dtype="<u4")
                if ids.ndim != 1 or ids.dtype.kind not in "iu" or (len(ids) and (
                    int(ids.min()) < 0 or int(ids.max()) >= min(len(artifacts.lengths), 2**32)
                )):
                    raise ValueError("Invalid encoded token ID")
                if int(np.asarray(artifacts.lengths)[ids].sum(dtype=np.int64)) != size:
                    raise ValueError("Byte conservation failed")
                name = next(slices) if slices is not None else None
                if name not in names:
                    names.append(name)
                if name is not None:
                    totals = summary["slice_raw_bytes"]
                    totals[name] = totals.get(name, 0) + size
                token_offset = summary["tokens"]
                np.asarray(ids, dtype="<u4").tofile(token_file)
                rows = [(token_offset + start, min(seq_len, len(ids) - start),
                         artifacts.bos_id if start == 0 else int(ids[start - 1]),
                         names.index(name)) for start in range(0, len(ids), seq_len)]
                np.asarray(rows, dtype=WINDOW_DTYPE).tofile(window_file)
                hash_file.write(hashlib.sha256(raw).digest())
                summary["raw_bytes"] += size
                summary["tokens"] += len(ids)
                summary["windows"] += len(rows)
                summary["document_count"] += 1
                if progress and summary["document_count"] % 4096 == 0:
                    progress({"stage": "encoding", **summary})
            for stream in (token_file, window_file, hash_file):
                stream.flush()
                os.fsync(stream.fileno())
        if not summary["windows"] or not summary["raw_bytes"]:
            raise ValueError("Empty/zero-byte dataset")
        if _cache_identity(path, artifacts, seq_len, require_ids, sources_path)[1] != identity:
            raise ValueError("Input changed while building window cache")
        files = {name: {"bytes": (temporary / name).stat().st_size,
                        "sha256": _sha256(temporary / name)}
                 for name in ("tokens.bin", "windows.bin", "document_hashes.bin")}
        metadata = dict(identity=identity, summary=summary, files=files, slice_names=names)
        (temporary / "metadata.json").write_text(
            json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf8")
        if progress:
            progress({"stage": "verifying numeric payloads", **summary})
        _load_window_cache(temporary, identity, artifacts)
        temporary.rename(destination)
    if progress:
        progress({"stage": "complete", "cache_key": key, **summary})
    return destination


def read_texts(path, require_ids=False, records=False):
    path = Path(path)
    if path.suffix == ".jsonl":
        seen = set()
        with path.open(encoding="utf8", errors="strict") as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict) or not isinstance(obj.get("text"), str):
                    raise ValueError(f"{path}:{n}: expected text string")
                if require_ids and "id" not in obj:
                    raise ValueError(f"{path}:{n}: missing document id")
                if "id" in obj:
                    if type(obj["id"]) not in (str, int):
                        raise ValueError("Document id must be string or integer")
                    identity = (type(obj["id"]).__name__, str(obj["id"]))
                    if identity in seen:
                        raise ValueError("Duplicate document id")
                    seen.add(identity)
                yield obj if records else obj["text"]
    elif path.suffix == ".txt":
        yield (
            {"text": path.read_text(encoding="utf8", errors="strict")}
            if records
            else path.read_text(encoding="utf8", errors="strict")
        )
    else:
        raise ValueError(
            "Week-2 byte-auditable input supports JSONL text documents or UTF-8 TXT"
        )


class DocumentWindows:
    def __init__(self, path, artifacts, seq_len, require_ids=False, sources_path=None):
        cache_dir = os.environ.get("G5_DOCUMENT_CACHE_DIR")
        if cache_dir is not None:
            key, identity = _cache_identity(path, artifacts, seq_len, require_ids, sources_path)
            if not cache_dir:
                raise ValueError("G5_DOCUMENT_CACHE_DIR must name a cache directory")
            self.__dict__.update(_load_window_cache(Path(cache_dir) / key, identity, artifacts))
            return
        self.windows = []
        self.raw_bytes = 0
        self.tokens = 0
        self.document_hashes = set()
        self.document_count = 0
        self.pad_id = artifacts.pad_id
        self.seq_len = seq_len
        records = list(read_texts(path, require_ids=require_ids, records=True))
        from .scoring import source_slices

        slices = (
            source_slices(sources_path, records)
            if sources_path
            else [None] * len(records)
        )
        self.window_slices = []
        self.slice_raw_bytes = {}
        for doc, slice_name in zip(records, slices):
            text = doc['text']
            if slice_name is not None:
                self.slice_raw_bytes[slice_name] = self.slice_raw_bytes.get(
                    slice_name, 0
                ) + len(text.encode('utf8'))
            self.document_count += 1
            self.document_hashes.add(hashlib.sha256(text.encode("utf8")).hexdigest())
            ids = artifacts.encode(text)
            self.raw_bytes += len(text.encode("utf8"))
            self.tokens += len(ids)
            for start in range(0, len(ids), seq_len):
                target = ids[start : start + seq_len]
                previous = artifacts.bos_id if start == 0 else ids[start - 1]
                inputs = [previous] + target[:-1]
                lengths = [int(artifacts.lengths[i]) for i in target]
                self.windows.append((inputs, target, lengths))
                self.window_slices.append(slice_name)
        if not self.windows or not self.raw_bytes:
            raise ValueError("Empty/zero-byte dataset")
        if sum(sum(x[2]) for x in self.windows) != self.raw_bytes:
            raise ValueError("Byte conservation failed")

    def batch(self, indices, device):
        rows = [self.windows[int(i)] for i in indices]
        # No cross-document attention: every row is one window of one document.
        x = torch.full((len(rows), self.seq_len), self.pad_id, dtype=torch.long)
        y = torch.full_like(x, -100)
        lengths = torch.zeros_like(x)
        for i, (a, b, c) in enumerate(rows):
            x[i, : len(a)] = torch.tensor(a)
            y[i, : len(b)] = torch.tensor(b)
            lengths[i, : len(c)] = torch.tensor(c)
        return x.to(device), y.to(device), lengths.to(device)


# The sampler owns its RNG so model initialization cannot change data order.
class BatchStream:
    def __init__(self, dataset, batch_size, seed):
        self.dataset = dataset
        self.batch_size = batch_size
        self.generator = torch.Generator().manual_seed(seed)
        self.order = torch.randperm(
            len(dataset.windows), generator=self.generator
        ).tolist()
        self.offset = 0

    def next(self, device):
        ids = []
        while len(ids) < self.batch_size:
            if self.offset == len(self.order):
                self.order = torch.randperm(
                    len(self.dataset.windows), generator=self.generator
                ).tolist()
                self.offset = 0
            n = min(self.batch_size - len(ids), len(self.order) - self.offset)
            ids += self.order[self.offset : self.offset + n]
            self.offset += n
        return self.dataset.batch(ids, device)

    def state_dict(self):
        return dict(
            order=self.order, offset=self.offset, rng=self.generator.get_state()
        )

    def load_state_dict(self, state):
        self.order = state["order"]
        self.offset = state["offset"]
        # A GPU checkpoint load can move this CPU generator's state to CUDA.
        self.generator.set_state(state["rng"].cpu())
