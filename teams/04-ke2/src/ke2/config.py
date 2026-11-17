"""Pinned identities and paths. Change a value here, not in the modules that use it."""

from __future__ import annotations

from pathlib import Path

CHAR_DIM = 256
"""Byte alphabet size of the Kronecker codec."""

POS_DIMS: tuple[int, ...] = (32, 64)
"""Byte capacities P the team evaluates."""

HF_ID = "theschoolofai/BrahmicTokenizer-131K"
HF_REVISION = "93df154cbc9dbf038a222c010d9b43906a8a72c3"
TOKENIZER_SHA256 = "01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff"
"""SHA-256 of the reviewed BrahmicTokenizer-131K ``tokenizer.json``."""

FROZEN_TOKENIZER_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
"""Gate 3 p1536-s0 tokenizer for new work; earlier baseline results retain TOKENIZER_SHA256."""

UPSTREAM_CODEC_COMMIT = "d07cb543f03d7a72a7c35bc68cfb795bcb02e1ec"
"""Commit of theschoolofai/kronecker-embeddings the team reviewed."""

TEAM_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = TEAM_DIR / "src"
RESULTS_DIR = TEAM_DIR / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FROZEN_TABLES_DIR = TABLES_DIR / "p1536-s0"
"""Byte tables rebuilt for the Gate 3 p1536-s0 tokenizer."""

TOKENIZER_ENV_VARS = ("KE2_TOKENIZER", "BRAHMIC_TOKENIZER_DIR")
"""Environment variables that may point at a local tokenizer.json (or its folder)."""
