"""Shared test setup for teams/04-ke2.

* Puts src/, src/proofs and src/determinism on sys.path and makes ``kronecker_embeddings``
  importable (installed, ``$KRONECKER_SRC``, or a sibling checkout; see ``ke2.upstream``).
* Finds the pinned BrahmicTokenizer-131K offline (``$KE2_TOKENIZER``, ``$BRAHMIC_TOKENIZER_DIR``,
  or the Hugging Face cache) and exports ``BRAHMIC_TOKENIZER_DIR`` for the proof tests.
* Provides the session table fixtures. Tests that need the real tokenizer are skipped without it.
"""

import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
for p in (SRC / "determinism", SRC / "proofs", SRC):
    sys.path.insert(0, str(p))

from ke2.config import POS_DIMS, TOKENIZER_SHA256  # noqa: E402
from ke2.tables import BUILDERS, KINDS  # noqa: E402
from ke2.tokenizer import load_tokenizer, resolve_tokenizer_path  # noqa: E402
from ke2.upstream import ensure_kronecker_embeddings  # noqa: E402

ensure_kronecker_embeddings()


def _find_tokenizer_dir():
    try:
        path = resolve_tokenizer_path()
    except FileNotFoundError:
        return None
    return path.parent if (path.parent / "special_tokens_map.json").is_file() else None


TOKENIZER_DIR = _find_tokenizer_dir()
if TOKENIZER_DIR is not None:
    os.environ.setdefault("BRAHMIC_TOKENIZER_DIR", str(TOKENIZER_DIR))


@pytest.fixture(scope="session")
def tb():
    if TOKENIZER_DIR is None:
        pytest.skip("BrahmicTokenizer-131K not found; set KE2_TOKENIZER to its tokenizer.json")
    return load_tokenizer(str(TOKENIZER_DIR / "tokenizer.json"), expected_sha256=TOKENIZER_SHA256)


@pytest.fixture(scope="session")
def tables(tb):
    """Every table, keyed by ``(kind, P)``. Building all four takes about a minute."""
    return {(kind, P): BUILDERS[kind](tb, P) for P in POS_DIMS for kind in KINDS}


@pytest.fixture(scope="session")
def dec32(tables):
    return tables["decode", 32]


@pytest.fixture(scope="session")
def raw32(tables):
    return tables["raw", 32]


@pytest.fixture
def make_byte_table():
    """Build a raw ``ByteTable`` from byte strings: ``make_byte_table(rows, P)``."""
    import numpy as np

    from ke2.tables import ByteTable

    def build(rows, P):
        buf = np.zeros((len(rows), P), np.uint8)
        for i, r in enumerate(rows):
            buf[i, : len(r)] = np.frombuffer(r, np.uint8)
        lengths = np.array([len(r) for r in rows], np.int16)
        return ByteTable("raw", P, buf, lengths, 0, 0, int((lengths == 0).sum()), "0" * 64)

    return build


@pytest.fixture(scope="session")
def synthetic_p8():
    """120 distinct non-empty tokens of 1..8 bytes at P = 8; row 7 is ``b"\\x00\\x01"`` (a real 0x00 byte)."""
    import numpy as np

    from ke2.tables import ByteTable

    rng = np.random.default_rng(0)
    P, rows = 8, []
    while len(rows) < 120:
        r = rng.integers(0, 256, rng.integers(1, P + 1)).astype(np.uint8).tobytes()
        if r not in rows and r != b"\x00\x01":
            rows.append(r)
    rows[7] = b"\x00\x01"
    buf = np.zeros((len(rows), P), np.uint8)
    for i, r in enumerate(rows):
        buf[i, : len(r)] = np.frombuffer(r, np.uint8)
    lengths = np.array([len(r) for r in rows], np.int16)
    return ByteTable("raw", P, buf, lengths, 0, 0, 0, "0" * 64)
