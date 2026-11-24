"""Verified count ingestion and explicitly selected additive log-prior policy.

Consumes Team 3's counts format (#719). This does not select a training policy,
reweight sources, mask logits, or initialize a head: callers must choose the
smoothing and EOS treatment and include identity() in their run provenance.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re


def _integer(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _digest(value, label):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a lowercase sha256")
    return value


@dataclass(frozen=True)
class UnigramCounts:
    counts: tuple
    documents: int
    eos_id: int
    special_ids: tuple
    file_sha256: str
    tokenizer_sha256: str
    # Immutable source receipts: name, sha256, bytes, documents, tokens.
    sources: tuple
    verified_sha256: str
    checksum_mode: str

    def identity(self):
        return {
            "counts_file_sha256": self.file_sha256,
            "counts_verified_sha256": self.verified_sha256,
            "checksum_mode": self.checksum_mode,
            "tokenizer_sha256": self.tokenizer_sha256,
            "vocab_size": len(self.counts),
            "tokens": sum(self.counts),
            "documents": self.documents,
            "eos_id": self.eos_id,
            "special_ids": list(self.special_ids),
            "sources": {
                name: dict(sha256=sha, bytes=size, docs=docs, tokens=tokens)
                for name, sha, size, docs, tokens in self.sources
            },
        }


def load_counts(path, *, expected_sha256, expected_tokenizer_sha256, expected_vocab_size, checksum_mode="exact"):
    """Load hash-pinned raw counts and verify their summaries/source receipts.

    Exact bytes are checked by default. Explicit checksum_mode="lf" supports
    Git's CRLF checkout conversion for this text JSON artifact. Both the actual
    file digest and verified digest/mode are retained in provenance.
    """
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if checksum_mode not in ("exact", "lf"):
        raise ValueError("Unknown counts checksum mode")
    checked = raw.replace(b"\r\n", b"\n") if checksum_mode == "lf" else raw
    verified = hashlib.sha256(checked).hexdigest()
    if verified != _digest(expected_sha256, "expected counts hash"):
        raise ValueError("Unigram counts file hash mismatch")
    spec = json.loads(raw)
    if spec["tokenizer_sha256"] != _digest(expected_tokenizer_sha256, "expected tokenizer hash"):
        raise ValueError("Unigram counts tokenizer mismatch")
    if type(expected_vocab_size) is not int or expected_vocab_size <= 0:
        raise ValueError("Expected vocabulary size must be a positive integer")
    if type(spec["vocab_size"]) is not int or spec["vocab_size"] != expected_vocab_size:
        raise ValueError("Unigram counts vocabulary mismatch")
    counts = spec["total"]
    if not isinstance(counts, list) or len(counts) != expected_vocab_size:
        raise ValueError("Unigram counts must have one entry per token ID")
    counts = tuple(_integer(n, "Token count") for n in counts)
    specials = spec["special_ids"]
    if not isinstance(specials, list) or any(type(i) is not int or not 0 <= i < len(counts) for i in specials):
        raise ValueError("Invalid special token IDs")
    if len(set(specials)) != len(specials):
        raise ValueError("Duplicate special token IDs")
    eos = spec["eos_id"]
    if type(eos) is not int or eos not in specials:
        raise ValueError("EOS must name a special token ID")
    summary = spec["summary"]
    calculated = {
        "tokens": sum(counts),
        "ids_seen": sum(n > 0 for n in counts),
        "ids_zero": sum(n == 0 for n in counts),
        "special_ids_seen": sum(counts[i] > 0 for i in specials),
    }
    for key, expected in calculated.items():
        if _integer(summary[key], "Summary " + key) != expected:
            raise ValueError("Unigram summary mismatch: " + key)
    docs = _integer(summary["docs"], "Document count")
    sources = []
    for name, source in sorted(spec["sources"].items()):
        sources.append((name, _digest(source["sha256"], "Source hash"),
                        _integer(source["bytes"], "Source bytes"),
                        _integer(source["docs"], "Source documents"),
                        _integer(source["tokens"], "Source tokens")))
    if sum(s[3] for s in sources) != docs or sum(s[4] for s in sources) != sum(counts):
        raise ValueError("Unigram source totals disagree with summary")
    return UnigramCounts(counts, docs, eos, tuple(specials), digest, spec["tokenizer_sha256"],
                         tuple(sources), verified, checksum_mode)


def additive_log_prior(counts, *, smoothing, add_eos_per_document):
    """Return (normalized log probabilities, provenance) for an explicit policy.

    All IDs, including specials, receive the same additive smoothing. There is
    no source reweighting or target masking. EOS correction is applied to a copy
    and refused if the artifact already has EOS counts, to avoid double counting.
    This utility is not a claim about the private reference's implementation.
    """
    if type(smoothing) not in (int, float) or not math.isfinite(smoothing) or smoothing < 0:
        raise ValueError("Smoothing must be finite and nonnegative")
    if type(add_eos_per_document) is not bool:
        raise ValueError("EOS policy must be explicitly true or false")
    adjusted = list(counts.counts)
    if add_eos_per_document:
        if adjusted[counts.eos_id] != 0:
            raise ValueError("Artifact already contains EOS counts; refusing document correction")
        adjusted[counts.eos_id] += counts.documents
    weights = [n + smoothing for n in adjusted]
    if any(n <= 0 or not math.isfinite(n) for n in weights):
        raise ValueError("Every token needs positive finite mass; choose smoothing for zero counts")
    total = math.fsum(weights)
    if not math.isfinite(total):
        raise ValueError("Unigram normalization is nonfinite")
    values = tuple(math.log(n) - math.log(total) for n in weights)
    identity = {
        **counts.identity(),
        "policy": "additive_all_ids",
        "smoothing": smoothing,
        "add_eos_per_document": add_eos_per_document,
        "source_weighting": "raw_total",
    }
    return values, identity
