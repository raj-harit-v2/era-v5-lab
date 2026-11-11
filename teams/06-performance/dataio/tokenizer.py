"""BrahmicTokenizer artifact from its pinned GitHub source (never the Hub).

The byte alphabet follows the source repo's verify_max_byte_length.py.
Special tokens use their literal UTF-8 spelling; normal pieces retain raw bytes,
including incomplete UTF-8 sequences.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

REVISION = "7dfcf398172c825c6689ad578e8b484ca5f57bc9"
SHA256 = "01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff"
URL = f"https://raw.githubusercontent.com/theschoolofai/BrahmicTokenizer-131K/{REVISION}/tokenizer.json"
VOCAB_SIZE = 131072
DEFAULT_PATH = "~/.cache/era-perf/BrahmicTokenizer-131K/tokenizer.json"


class BrahmicTokenizer:
    """The pinned tokenizer.json: downloaded once into the cache, SHA-256 checked on every load."""

    def __init__(self, path=None):
        artifact = Path(path or DEFAULT_PATH).expanduser()
        if not artifact.exists():
            if path is not None:
                raise FileNotFoundError(artifact)
            raw = urlopen(URL, timeout=120).read()
            self._verify(raw)
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(raw)
        raw = artifact.read_bytes()
        self._verify(raw)
        self.path = artifact
        self.spec = json.loads(raw)
        vocab = self.spec["model"]["vocab"]
        self.vocab_size = len(vocab)
        if self.vocab_size != VOCAB_SIZE or set(vocab.values()) != set(range(VOCAB_SIZE)):
            raise ValueError("Brahmic vocabulary must contain contiguous IDs 0..131071")
        self._encoder = None

    @staticmethod
    def _verify(raw):
        """Raise unless raw is the pinned artifact."""
        if hashlib.sha256(raw).hexdigest() != SHA256:
            raise ValueError("Tokenizer checksum differs from the pinned GitHub source artifact")

    def encode(self, text):
        """Token IDs of text, without special tokens."""
        if self._encoder is None:
            from tokenizers import Tokenizer
            self._encoder = Tokenizer.from_file(str(self.path))
        return self._encoder.encode(text, add_special_tokens=False).ids

    def raw_token_bytes(self):
        """Return exact byte strings in token ID order, without lossy UTF-8 decode."""
        # Inverse ByteLevel alphabet (the GPT-2 byte-to-unicode map), without a GPT-2 tokenizer dependency.
        bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
        cs = bs.copy()
        n = 0
        for b in range(256):
            if b not in bs:
                bs.append(b)
                cs.append(256 + n)
                n += 1
        inverse = {chr(c): b for b, c in zip(bs, cs)}
        special = {a["content"] for a in self.spec["added_tokens"] if a["special"]}
        rows = [None] * self.vocab_size
        for token, idx in self.spec["model"]["vocab"].items():
            rows[idx] = token.encode("utf-8") if token in special else bytes(inverse[c] for c in token)
        return rows

    def token_bytes(self, max_pos=32):
        """(bytes [V, max_pos] uint8, lens [V]) for KE; fails if a token is longer than max_pos."""
        import torch
        if max_pos < 1:
            raise ValueError("max_pos must be positive")
        table = torch.zeros((self.vocab_size, max_pos), dtype=torch.uint8)
        lens = torch.empty(self.vocab_size, dtype=torch.int64)
        for idx, raw in enumerate(self.raw_token_bytes()):
            if not raw or len(raw) > max_pos:
                raise ValueError(f"Token {idx} needs {len(raw)} byte positions; ke_max_pos={max_pos}")
            table[idx, :len(raw)] = torch.tensor(list(raw), dtype=torch.uint8)
            lens[idx] = len(raw)
        return table, lens
