"""The KAS V2 fixture (fixtures/kas_v2) is self-consistent: the contract equations reproduce the reference numbers."""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "kas_v2"


@pytest.fixture(scope="module")
def checker():
    spec = importlib.util.spec_from_file_location("check_kas_v2_fixture", FIX / "check_kas_v2_fixture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fixture():
    meta = json.loads((FIX / "kas_v2_fixture.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((FIX / "kas_v2_fixture.npz").read_bytes()).hexdigest() == meta["npz_sha256"]
    return np.load(FIX / "kas_v2_fixture.npz", allow_pickle=False), meta


def test_fixture_shapes(fixture):
    z, meta = fixture
    V = len(meta["ids"])
    assert z["G"].shape == (256, 64) and z["Phi"].shape == (32, 32)
    assert z["K"].shape == (V, 2048) and z["M_pos"].shape == (V, 64, 32)
    assert z["W_proj"].shape == (2048, 32) and z["W_out"].shape == (32, 2048)
    assert z["beta"].shape == (33,) and z["unigram"].shape == (V,)
    assert z["tok_u"].shape == (V, 64) and z["tok_c"].shape == (64, 32)
    assert z["logits"].shape == z["logits_f32"].shape == z["logits_dropped"].shape == (8, V)


def test_fixture_covers_special_and_worst_pair_ids(fixture):
    _, meta = fixture
    for i in (36, 130725, 130726, 130727, 130822, 1214, 2420):
        assert i in meta["ids"]
    assert meta["tokenizer_sha256"].startswith("e6b93a93")


def test_contract_equations_reproduce_reference(checker, fixture):
    z, meta = fixture
    out = checker.run_checks(z, meta)
    assert out["pass"], out
    assert out["K_abs"] == 0.0 and out["M_pos_abs"] == 0.0
    assert out["logits_float64_abs"] < 1e-12
