"""Task 5: the KE2 input path folds into a normal embedding table (``src/export/fold_check.py``).

Fast checks on the committed frozen p1536 raw P = 32 table (no tokenizer needed) with a small random projection:
the folded rows equal Team 5's ``KE2(ids)`` bit for bit, match the float64 closed form, and cover all 356 special ids.
The full run on all 131,072 ids at d_model 512 is ``python src/export/fold_check.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "export"))

import fold_check

WIDTH = 64


def _inputs():
    z = np.load(fold_check.TABLE)
    rows, lengths = z["bytes"], z["lengths"]
    g = torch.Generator().manual_seed(1)
    weight = torch.randn(WIDTH, 256 * fold_check.P, generator=g) / np.sqrt(256 * fold_check.P)
    module = fold_check.KE2(rows, lengths, WIDTH)
    module.projection.weight.data.copy_(weight)
    return rows, lengths, weight, module


def test_table_is_the_frozen_p1536_table():
    z = np.load(fold_check.TABLE)
    assert fold_check.table_content_sha256(z["bytes"], z["lengths"]) == fold_check.TABLE_CONTENT_SHA256
    assert str(z["tokenizer_sha256"]) == fold_check.FROZEN_TOKENIZER_SHA256


def test_special_ids_are_the_356_of_the_manifest():
    ids = fold_check.special_ids(131072)
    assert len(ids) == 356
    assert set(fold_check.ROLE_IDS.values()) <= set(ids)


def test_fold_equals_trainer_and_float64():
    rows, lengths, weight, module = _inputs()
    ids = np.unique(np.r_[np.arange(4096), fold_check.special_ids(len(rows)), np.argsort(-lengths, kind="stable")[:64]])
    with torch.no_grad():
        folded = module(torch.from_numpy(ids))
        batch = torch.from_numpy(ids[np.random.default_rng(0).integers(0, len(ids), (4, 128))])
        assert torch.equal(module(batch), folded[torch.searchsorted(torch.from_numpy(ids), batch)])
    w64 = weight.double().t().contiguous()
    ref = fold_check.fold_f64_chunk(rows[ids], lengths[ids], w64, w64.sum(0))
    rel = ((folded.double() - ref).abs().amax(-1) / ref.abs().amax(-1)).max().item()
    assert rel < 1e-5
    assert bool((folded.abs().amax(-1) > 0).all())


def test_committed_result_passes():
    rec = json.loads((fold_check.OUT_DIR / f"fold_check_P{fold_check.P}.json").read_text(encoding="utf-8"))
    assert rec["pass"] is True
    assert rec["inputs"]["table_content_sha256"] == fold_check.TABLE_CONTENT_SHA256
    assert rec["result"]["lookup_vs_trainer"]["rows_differ"] == 0
    assert rec["result"]["special_tokens"]["count"] == 356
