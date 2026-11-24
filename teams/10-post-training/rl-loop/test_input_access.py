"""team5_adapter.input_access: G5's input layer detected by name and shape, on main's 8,192 table and the 2,048 code.

The 2,048-code module is an interface stand-in (fixed per-position code of width 64, as in the TSAI ruling of 23 Nov),
not Team 5's code: #717 at 319f2dd7 still builds Linear(8192, d_model). Set G10_IN2K_G5_ROOTS to lab checkouts
(os.pathsep-separated) to also build `week2.model.KE2` from each of them.
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import team5_adapter as ta  # noqa: E402

V, P, D = 20, 4, 8
parametrize = pytest.mark.parametrize  # undotted decorator: the lab's older PR guard reads a dotted one as an e-mail


class _Emb(nn.Module):
    def __init__(self, per_pos, rows=True, lengths=True, projection=True, extra_code=False):
        super().__init__()
        if rows:
            self.register_buffer("rows", torch.zeros(V, P, dtype=torch.uint8))
        if lengths:
            self.register_buffer("lengths", torch.ones(V, dtype=torch.long))
        if extra_code:
            self.register_buffer("char_code", torch.ones(256, per_pos))
        if projection:
            self.projection = nn.Linear(per_pos * P, D, bias=False)


class _LM(nn.Module):
    def __init__(self, emb):
        super().__init__()
        self.embedding = emb


@parametrize("per_pos,kind,extra", [(256, "ke2_raw_table", False), (64, "ke2_code_2048", True)])
def test_both_inputs_are_recognised_by_name_and_shape(per_pos, kind, extra):
    info = ta.input_access(_LM(_Emb(per_pos, extra_code=extra)), P)
    assert (info["kind"], info["width"], info["per_position"], info["n_embd"]) == (kind, per_pos * P, per_pos, D)
    assert "embedding.rows" in info["tensors"] and ("embedding.char_code" in info["tensors"]) == extra


def test_no_embedding_module_is_refused():
    lm = nn.Module()
    lm.embedding = None
    with pytest.raises(ta.ArtifactError, match="no `embedding` module"):
        ta.input_access(lm, P)


@parametrize("kw", [{"rows": False}, {"lengths": False}])
def test_an_input_without_the_byte_table_buffers_is_refused(kw):
    with pytest.raises(ta.ArtifactError, match="no KE2 byte table buffers"):
        ta.input_access(_LM(_Emb(64, **kw)), P)


def test_byte_rows_of_another_length_are_refused():
    with pytest.raises(ta.ArtifactError, match="no KE2 byte table buffers"):
        ta.input_access(_LM(_Emb(64)), P + 1)


def test_an_input_without_a_2d_projection_is_refused():
    with pytest.raises(ta.ArtifactError, match="no 2-D embedding.projection.weight"):
        ta.input_access(_LM(_Emb(64, projection=False)), P)


@parametrize("per_pos", [128, 63])
def test_a_projection_of_another_width_is_refused(per_pos):
    with pytest.raises(ta.ArtifactError, match="neither 256 x 4"):
        ta.input_access(_LM(_Emb(per_pos)), P)


ROOTS = [Path(r) for r in os.environ.get("G10_IN2K_G5_ROOTS", "").split(os.pathsep) if r]


needs_roots = pytest.mark.skipif(not ROOTS, reason="set G10_IN2K_G5_ROOTS to lab checkouts to build their KE2")


@needs_roots
def test_real_ke2_modules_from_lab_checkouts():
    for root in ROOTS:
        harness = root / "teams" / "05-architecture" / "harness"
        spec = importlib.util.spec_from_file_location(f"g5_model_{abs(hash(root))}", harness / "week2" / "model.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        lm = _LM(mod.KE2(np.zeros((V, 32), dtype=np.uint8), np.ones(V, dtype=np.int64), D))
        info = ta.input_access(lm, 32)
        assert info["kind"] in ("ke2_raw_table", "ke2_code_2048"), (root, info)
        print(root.name, info["kind"], info["width"])
