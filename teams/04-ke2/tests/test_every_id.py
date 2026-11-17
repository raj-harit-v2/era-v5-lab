"""Task 3, week 3: correctness on every token ID of the KE2 input path that dry run 1 runs.

The path: Team 5's trainer and its ``week2.model.KE2`` (#475), the dense untied head, bf16 autocast at T2 width 512.
The tokenizer: TSAI's Gate 3 notice (16 Nov) replaced C3 with p1536 (Team 3, #414), ``tokenizer.json`` sha256
``e6b93a93…``, and Team 4 rebuilds its raw P = 32 byte table. This file pins that table's content sha256
(``21072027…``, from ``src/build_tables.py --pos-dims 32``). The table is rebuilt locally and never committed
(lab rule, 15 Nov). TSAI (16 Nov): the output head stays dense and the KE2 cosine decoder is an evaluation-time
tool, so its round trip is checked here and no output-head check is.

Every check runs on each table: the frozen p1536 table (skipped until it is available, see Environment) and the
committed ``results/tables/raw_table_P32.npz`` (week 2's table, always present).

1. Table: the p1536 table has the pinned tokenizer and content hashes (built here from the tokenizer, or loaded and
   checked); the committed table is the one week 2 decoded.
2. Round trip, structural: each code, fp32 and bf16, decodes to its own bytes and so to its own ID (Theorem 2).
3. Round trip, cosine: the evaluation-time decoder (cosine against all V codes, ties to the lowest ID, the
   ``decode_ref`` contract) returns each code's own ID. fp32 scores via ``ke2.scoring.StructuredScorer``; a sample
   also through ``decode_ref.decode`` in float64. A full run on the committed table reproduces week 2's ID hash.
4. Input path: Team 5's ``week2.model.KE2`` and Team 6's ``models/ke2.py`` ``KE2Embedding`` against G4's float64
   codec, ``encode_f64(ids) @ W.T``: outputs and the projection gradient through Team 6's
   ``correctness.framework.check`` with its TOLERANCES (fp32 1e-5 / 5e-5, bf16 autocast 1e-2 / 3e-2), chunk by chunk,
   and the output tolerance again on every ID's own row.
5. bf16 code: Team 5's dense ``codec``, rounded to bf16, equals the upstream fp32 ``kronecker_codec`` rounded to bf16,
   bit for bit, for every ID (the definition the frozen bf16 codes use).

Environment:
  KE2_EVERY_ID_FULL=1          all 131,072 IDs (default: a fixed sample, see ``ids_under_test``)
  KE2_FROZEN_TOKENIZER=PATH    the p1536 tokenizer.json; the test builds the raw table from it
  KE2_FROZEN_TABLE=PATH        or a raw_table_P32.npz built from it (with both, they must agree row for row)
  KE2_EVERY_ID_DEVICE=cpu|cuda default: cuda if available
  KE2_EVERY_ID_REPORT=PATH     append one JSON line per check (table, IDs, worst errors, hashes) for the run log
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import torch
from decode_theorems import decode_structural_batch

from decode_gpu import id_digest
from decode_ref import CodeTable, decode
from ke2.codec import encode_f64
from ke2.config import CHAR_DIM, RESULTS_DIR, TABLES_DIR, TEAM_DIR, TOKENIZER_SHA256
from ke2.scoring import StructuredScorer
from ke2.tables import ByteTable, build_raw_table
from ke2.tokenizer import load_tokenizer

TEAMS_DIR = TEAM_DIR.parent
for _p in (TEAMS_DIR / "05-architecture" / "harness", TEAMS_DIR / "06-performance"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

from correctness.framework import TOLERANCES, Case, Pair, check  # noqa: E402  Team 6
from models.ke2 import KE2Embedding  # noqa: E402  Team 6
from week2.model import KE2, codec  # noqa: E402  Team 5: the class dry run 1 trains

# Aliases: pr-guard's email check misreads dotted pytest decorators as addresses.
fixture = pytest.fixture
parametrize = pytest.mark.parametrize

P = 32
V = 131_072
WIDTH = 512  # T2 n_embd (configs/arms/t2.yaml), the dry run 1 size (#475)
FROZEN_NAME = "p1536"
FROZEN_TOKENIZER_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"  # TSAI notice, 16 Nov
FROZEN_RAW_TABLE_SHA256 = "21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a"  # build_tables.py, P = 32
ROLE_IDS = (36, 130725, 130726, 130727, 130822)  # <|end_of_text|>, bos, pad, unk, eos: same ids in C3 and p1536
FULL = os.environ.get("KE2_EVERY_ID_FULL") == "1"
DEVICE = torch.device(os.environ.get("KE2_EVERY_ID_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu"))
REPORT = os.environ.get("KE2_EVERY_ID_REPORT")
CHUNK = 2048  # IDs per chunk: an fp64 code chunk is CHUNK x 8,192 x 8 bytes = 128 MiB
SCORE_CHUNK = 512  # queries per cosine chunk: V x 512 float32 scores = 256 MiB
COMMITTED_TABLE = TABLES_DIR / f"raw_table_P{P}.npz"
WEEK2_DECODE = RESULTS_DIR / "decode_gpu" / f"raw_P{P}.json"
DTYPES = {"fp32": torch.float32, "bf16": torch.bfloat16}


@dataclass
class Subject:
    """One table under test."""

    name: str
    table: ByteTable
    week2_id_sha256: str | None = None  # the full-vocabulary ID hash week 2 recorded for this table

    @property
    def rows(self) -> torch.Tensor:
        return torch.from_numpy(self.table.bytes)

    @property
    def lengths(self) -> torch.Tensor:
        return torch.from_numpy(self.table.lengths.astype(np.int64))


def committed_subject() -> Subject:
    table = ByteTable.load(COMMITTED_TABLE, tokenizer_sha256=TOKENIZER_SHA256)
    week2 = json.loads(WEEK2_DECODE.read_text(encoding="utf-8"))
    assert week2["inputs"]["table_sha256"] == table.sha256(), "week 2's decode record is for another table"
    return Subject("committed", table, week2["cpu_reference"]["id_sha256"])


def frozen_subject() -> Subject:
    tokenizer_path = os.environ.get("KE2_FROZEN_TOKENIZER")
    table_path = os.environ.get("KE2_FROZEN_TABLE")
    if not tokenizer_path and not table_path:
        pytest.skip(
            f"frozen {FROZEN_NAME} table not available: set KE2_FROZEN_TOKENIZER to its tokenizer.json "
            f"(sha256 {FROZEN_TOKENIZER_SHA256[:8]}…) or KE2_FROZEN_TABLE to a raw_table_P{P}.npz built from it"
        )
    tables = []
    if tokenizer_path:
        tables.append(build_raw_table(load_tokenizer(tokenizer_path, expected_sha256=FROZEN_TOKENIZER_SHA256), P))
    if table_path:
        tables.append(ByteTable.load(Path(table_path), tokenizer_sha256=FROZEN_TOKENIZER_SHA256))
    table = tables[0]
    for other in tables[1:]:
        assert np.array_equal(other.bytes, table.bytes) and np.array_equal(other.lengths, table.lengths), (
            "KE2_FROZEN_TABLE differs from the table built from KE2_FROZEN_TOKENIZER"
        )
    return Subject(FROZEN_NAME, table)


@fixture(scope="module", params=[FROZEN_NAME, "committed"])
def subject(request) -> Subject:
    return frozen_subject() if request.param == FROZEN_NAME else committed_subject()


def ids_under_test(table: ByteTable) -> np.ndarray:
    """Every ID with KE2_EVERY_ID_FULL=1. Otherwise both ends, the special-role IDs, the longest and the shortest
    tokens, and 2,000 random IDs (seed 0): enough to exercise every code path in seconds."""
    if FULL:
        return np.arange(table.vocab_size)
    L = table.lengths
    rng = np.random.default_rng(0)
    picks = [
        np.array([0, 1, V - 2, V - 1]),
        np.array(ROLE_IDS),
        np.flatnonzero(L.max() == L)[:64],
        np.flatnonzero(L == 1)[:64],
        rng.choice(V, 2000, replace=False),
    ]
    return np.unique(np.concatenate(picks))


def chunks(ids: np.ndarray, size: int) -> Iterator[np.ndarray]:
    for s in range(0, len(ids), size):
        yield ids[s : s + size]


def record(**fields) -> None:
    """One JSON line per check for the run log (KE2_EVERY_ID_REPORT)."""
    fields.update(full=FULL, device=str(DEVICE))
    if REPORT:
        with open(REPORT, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(fields, sort_keys=True) + "\n")


# --- 1. table --------------------------------------------------------------------------------------------------


def test_table_is_the_recorded_one(subject):
    t = subject.table
    assert (t.kind, t.pos_dim, t.vocab_size) == ("raw", P, V)
    assert t.n_truncated == 0 and t.n_empty_rows == 0
    assert int(t.lengths.min()) >= 1 and int(t.lengths.max()) <= P
    assert len({t.row(i) for i in range(V)}) == V, "two IDs share a byte row: no round trip can separate them"
    if subject.name == FROZEN_NAME:
        assert t.tokenizer_sha256 == FROZEN_TOKENIZER_SHA256
        assert t.sha256() == FROZEN_RAW_TABLE_SHA256, "not the frozen p1536 raw table"
    record(check="table", table=subject.name, sha256=t.sha256(), tokenizer_sha256=t.tokenizer_sha256, rows=V)


# --- 2. round trip, structural (Theorem 2) ----------------------------------------------------------------------


def fp32_codes(subject: Subject, ids: np.ndarray) -> torch.Tensor:
    """Team 5's dense fp32 code (week2.model.codec), the code the trainer's KE2 projects."""
    idx = torch.from_numpy(ids)
    return codec(subject.rows[idx].to(DEVICE), subject.lengths[idx].to(DEVICE))


def upstream_bf16_bits(subject: Subject, ids: np.ndarray) -> np.ndarray:
    """The upstream fp32 kronecker_codec rounded to bf16, as uint16 bit patterns, shape (n, 8192)."""
    from kronecker_embeddings.codec import kronecker_codec  # made importable by conftest

    t = subject.table
    out = kronecker_codec(
        torch.from_numpy(np.ascontiguousarray(t.bytes[ids])),
        torch.from_numpy(t.lengths[ids].astype(np.int64)),
        char_dim=CHAR_DIM,
        pos_dim=P,
    )
    return out.to(torch.bfloat16).view(torch.int16).numpy().view(np.uint16)


def bf16_codes(subject: Subject, ids: np.ndarray) -> np.ndarray:
    """The reference bf16 code rows, widened exactly to float64."""
    bits = upstream_bf16_bits(subject, ids).astype(np.uint32) << 16
    return bits.view(np.float32).astype(np.float64)


@parametrize("dtype", list(DTYPES))
def test_round_trip_structural(subject, dtype):
    t = subject.table
    id_of = {t.row(i): i for i in range(V)}
    ids = ids_under_test(t)
    wrong = []
    for c in chunks(ids, CHUNK):
        q = fp32_codes(subject, c) if dtype == "fp32" else bf16_codes(subject, c)
        got = decode_structural_batch(q, P)
        wrong += [int(i) for i, b in zip(c, got, strict=True) if id_of.get(b) != i]
    record(check="round_trip_structural", table=subject.name, dtype=dtype, ids=len(ids), wrong=len(wrong))
    assert not wrong, f"{len(wrong)} IDs do not decode to themselves, first {wrong[:10]}"


# --- 3. round trip, cosine (the evaluation-time decoder) ------------------------------------------------------


@fixture(scope="module")
def scorer(subject):
    """(float64 reference code table, fp32 structured scorer on DEVICE) for the subject's table."""
    code_table = CodeTable.from_byte_table(subject.table)
    return code_table, StructuredScorer(code_table, DEVICE, torch.float32)


@parametrize("dtype", list(DTYPES))
def test_round_trip_cosine(subject, scorer, dtype):
    code_table, fast = scorer
    ids = ids_under_test(subject.table)
    decoded = np.empty_like(ids)
    min_margin, min_margin_id, ties = np.inf, -1, 0
    for s in range(0, len(ids), SCORE_CHUNK):
        c = ids[s : s + SCORE_CHUNK]
        q = fp32_codes(subject, c) if dtype == "fp32" else torch.from_numpy(bf16_codes(subject, c)).float()
        best_id, best, _, second = fast.top2(q)
        decoded[s : s + len(c)] = best_id.numpy()
        margin = (best - second).double().numpy()
        ties += int((margin == 0).sum())
        k = int(margin.argmin())
        if margin[k] < min_margin:
            min_margin, min_margin_id = float(margin[k]), int(c[k])
    wrong = ids[decoded != ids]
    digest = id_digest(P, subject.table.sha256(), ids, decoded)
    record(
        check="round_trip_cosine",
        table=subject.name,
        dtype=dtype,
        ids=len(ids),
        wrong=len(wrong),
        ties=ties,
        min_margin=min_margin,
        min_margin_id=min_margin_id,
        id_sha256=digest,
    )
    assert len(wrong) == 0, f"{len(wrong)} IDs decode to another ID, first {wrong[:10].tolist()}"
    assert ties == 0
    if FULL and subject.week2_id_sha256 and dtype == "fp32":
        assert digest == subject.week2_id_sha256, "full-vocabulary ID hash differs from week 2's GPU and CPU runs"
    # the fast scorer agrees with the float64 reference decoder on a sample
    sample = np.unique(np.concatenate([ids[:8], ids[-8:], ids[:: max(1, len(ids) // 16)]]))
    q64 = fp32_codes(subject, sample).double().cpu().numpy() if dtype == "fp32" else bf16_codes(subject, sample)
    assert np.array_equal(decode(q64, code_table).token_ids, sample)


# --- 4. input path against the float64 codec, with Team 6's framework -------------------------------------------


def embedding(impl: str, subject: Subject):
    """(module, its projection weight) on DEVICE, seeded: Team 5's KE2 or Team 6's KE2Embedding."""
    torch.manual_seed(0)
    if impl == "team5":
        m = KE2(subject.rows, subject.lengths, WIDTH).to(DEVICE)
        return m, m.projection.weight
    m = KE2Embedding(V, WIDTH, P, token_bytes=(subject.rows, subject.lengths)).to(DEVICE)
    return m, m.proj.weight


@parametrize("dtype", list(DTYPES))
@parametrize("impl", ["team5", "team6"])
def test_input_path_matches_float64_codec(subject, impl, dtype):
    t = subject.table
    tdtype = DTYPES[dtype]
    tol, grad_tol = TOLERANCES[tdtype]
    module, w = embedding(impl, subject)
    w_ref = w.detach().double().clone().requires_grad_(True)

    def ref(i):
        idx = i.cpu().numpy()
        return torch.from_numpy(encode_f64(t.bytes[idx], t.lengths[idx], P)).to(i.device) @ w_ref.T

    def fast(i):
        with torch.autocast(DEVICE.type, dtype=torch.bfloat16, enabled=dtype == "bf16"):
            return module(i)

    ids = ids_under_test(t)
    worst = {"out": 0.0, "grad": 0.0, "row": 0.0}
    worst_row_id = -1
    for c in chunks(ids, CHUNK):
        ids_t = torch.from_numpy(c).to(DEVICE)

        def build(device, ids_t=ids_t):
            return Case(ref=ref, fast=fast, inputs=[ids_t], params_ref=[w_ref], params_fast=[w])

        errors = check(Pair(f"ke2.every_id.{impl}.{dtype}", build, tol, grad_tol, tdtype), DEVICE)
        worst["out"] = max(worst["out"], *(v for k, v in errors.items() if k.startswith("out")))
        worst["grad"] = max(worst["grad"], *(v for k, v in errors.items() if k.startswith("grad")))
        with torch.no_grad():  # Team 6's rel_err is one number per chunk; every ID must also pass on its own row
            r, f = ref(ids_t), fast(ids_t).double()
            row = ((f - r).norm(dim=1) / r.norm(dim=1)).cpu().numpy()
        k = int(row.argmax())
        if row[k] > worst["row"]:
            worst["row"], worst_row_id = float(row[k]), int(c[k])
    record(
        check="input_path",
        table=subject.name,
        impl=impl,
        dtype=dtype,
        ids=len(ids),
        tol=tol,
        grad_tol=grad_tol,
        worst_out=worst["out"],
        worst_grad=worst["grad"],
        worst_row=worst["row"],
        worst_row_id=worst_row_id,
    )
    assert worst["row"] <= tol, f"ID {worst_row_id}: row rel_err {worst['row']:.3e} > {tol}"


# --- 5. the trainer's code rounds to the reference bf16 code --------------------------------------------------


def test_trainer_code_rounds_to_reference_bf16(subject):
    ids = ids_under_test(subject.table)
    bad = []
    for c in chunks(ids, CHUNK):
        got = fp32_codes(subject, c).to(torch.bfloat16).view(torch.int16).cpu().numpy().view(np.uint16)
        bad += c[(got != upstream_bf16_bits(subject, c)).any(axis=1)].tolist()
    record(check="bf16_code_bits", table=subject.name, ids=len(ids), rows_differ=len(bad))
    assert not bad, f"{len(bad)} rows differ from the reference bf16 code, first {bad[:10]}"
