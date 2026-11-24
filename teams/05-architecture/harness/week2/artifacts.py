"""Strict tokenizer-release and G4 v2 raw-table integrity checks."""

from pathlib import Path
import hashlib
import json
import numpy as np
from tokenizers import Tokenizer
from .raw_vocab import VocabHoleError, raw_token_bytes

import os
V0_SHA256 = os.environ.get("TOKBPB_SHA", "2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


C3_SHA256 = "15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3"
# Gate 3 frozen tokenizer (Team 3 #414, released in teams/03-tokenizer/release/, #504).
P1536_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
# --tokenizer-release name -> pinned tokenizer.json sha256.
TOKENIZER_RELEASES = {"v0": V0_SHA256, "frozen-c3": C3_SHA256, "frozen-p1536": P1536_SHA256}
# C3 and p1536 normalize text inside the tokenizer (NFC plus Indic composition rules), so the
# table bytes reconstruct the normalized text; BPB still divides by the original UTF-8 bytes.
NORMALIZING_TOKENIZER_SHAS = frozenset({C3_SHA256, P1536_SHA256})


class Artifacts:
    def __init__(
        self,
        tokenizer_path,
        table_path,
        expected_tokenizer_sha=V0_SHA256,
        expected_vocab=131072,
    ):
        # Check the tokenizer identity before using its token IDs to index the table.
        self.tokenizer_sha = sha256(tokenizer_path)
        if self.tokenizer_sha != expected_tokenizer_sha:
            raise ValueError(
                "Tokenizer identity mismatch: the file is not the selected tokenizer release"
            )
        self.normalize_input = expected_tokenizer_sha in NORMALIZING_TOKENIZER_SHAS
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.no_padding()
        self.tokenizer.no_truncation()
        with np.load(table_path, allow_pickle=False) as z:
            if int(z["format_version"]) != 2 or str(z["kind"]) != "raw":
                raise ValueError(
                    "Expected Team 4 format-v2 RAW table, not decoded-token bytes"
                )
            if str(z["tokenizer_sha256"]) != self.tokenizer_sha:
                raise ValueError(
                    "G4 table belongs to a different tokenizer: rebuild with G4 tool"
                )
            self.bytes = z["bytes"].copy()
            self.lengths = z["lengths"].copy()
            self.pos_dim = int(z["pos_dim"])
            recorded = str(z["table_sha256"])
            if int(z["n_truncated"]) != 0:
                raise ValueError("Truncated table cannot give exact heldout bytes")
        if self.bytes.dtype != np.uint8 or self.lengths.dtype != np.int16:
            raise ValueError("Invalid table dtype")
        if self.bytes.shape != (expected_vocab, self.pos_dim) or self.lengths.shape != (
            expected_vocab,
        ):
            raise ValueError("Invalid table shape")
        if np.any(self.lengths == 0):
            tid = int(np.flatnonzero(self.lengths == 0)[0])
            raise VocabHoleError(f"token id {tid} yields an empty byte string in the raw table")
        if np.any(self.lengths < 0) or np.any(self.lengths > self.pos_dim):
            raise ValueError("Invalid byte lengths")
        h = hashlib.sha256(f"ke2-table-v2|raw|{self.pos_dim}|".encode())
        h.update(np.ascontiguousarray(self.bytes).tobytes())
        h.update(np.ascontiguousarray(self.lengths).tobytes())
        if h.hexdigest() != recorded:
            raise ValueError("Table content hash mismatch")
        # Independently check all rows against the tokenizer JSON, not just sample text.
        spec = json.loads(Path(tokenizer_path).read_text(encoding="utf8"))
        raw_rows = raw_token_bytes(spec, expected_vocab, max_bytes=self.pos_dim)
        if self.tokenizer.get_vocab_size(with_added_tokens=True) != expected_vocab:
            raise ValueError("Vocabulary mismatch")
        for i, expected in enumerate(raw_rows):
            actual = self.bytes[i, : int(self.lengths[i])].tobytes()
            if expected != actual:
                raise ValueError(f"Raw table/tokenizer row mismatch at ID {i}")
        self.table_content_sha = recorded
        self.table_file_sha = sha256(table_path)
        self.bos_id = self.tokenizer.token_to_id("<|begin_of_text|>")
        self.pad_id = self.tokenizer.token_to_id("<|pad|>")
        if self.bos_id is None or self.pad_id is None:
            raise ValueError("Missing actual BOS/PAD IDs")

    def encode(self, text):
        if not isinstance(text, str):
            raise ValueError("Expected a text string")
        ids = self.tokenizer.encode(text, add_special_tokens=False).ids
        raw = b"".join(self.bytes[i, : int(self.lengths[i])].tobytes() for i in ids)
        expected = self.tokenizer.normalizer.normalize_str(text) if self.normalize_input else text
        if raw != expected.encode("utf8"):
            raise ValueError(
                "Tokenizer/table does not reconstruct the expected UTF-8 input"
            )
        return ids

    def identity(self):
        return dict(
            tokenizer_sha256=self.tokenizer_sha,
            table_file_sha256=self.table_file_sha,
            table_content_sha256=self.table_content_sha,
            vocab_size=len(self.lengths),
            pos_dim=self.pos_dim,
            bos_id=self.bos_id,
            pad_id=self.pad_id,
        )
