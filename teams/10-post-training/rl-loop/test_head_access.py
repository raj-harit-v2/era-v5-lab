"""team5_adapter.head_access / head_logits: the one place that knows what G5's output head may be.

Dense `nn.Linear` (dry run 1) and a KE2/KAS-like untied head with a per-token `tok_u` [V, r] (Team 5 #694/#702/#706;
real code not yet on main) are accepted; any other head raises instead of being guessed. The KAS-like module here is a
tiny interface stand-in, not Team 4's maths.
"""
import sys
from pathlib import Path

import pytest
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "capstone"))
import team5_adapter as ta  # noqa: E402

V, D, R = 50, 12, 4
_parametrize = pytest.mark.parametrize  # undotted decorator: the lab's older PR guard reads "@pytest.x" as an e-mail


class _KASLike(nn.Module):
    """Untied: own projection, per-token log-prior and rank-R correction `tok_u`; inner Linears named like LoRA targets."""

    def __init__(self):
        super().__init__()
        self.up = nn.Linear(D, 8, bias=False)  # named like a LoRA target on purpose
        self.code = nn.Parameter(torch.randn(V, 8) * 0.1)
        self.q = nn.Linear(D, R, bias=False)
        self.tok_u = nn.Parameter(torch.randn(V, R) * 0.1)
        self.log_prior = nn.Parameter(torch.zeros(V))

    def forward(self, h):
        return self.up(h) @ self.code.t() + self.q(h) @ self.tok_u.t() + self.log_prior


class _LM(nn.Module):
    def __init__(self, head):
        super().__init__()
        self.embedding = nn.Module()
        self.embedding.projection = nn.Linear(16, D, bias=False)
        self.emb = nn.Embedding(V, D)
        self.blocks = nn.ModuleList([nn.Module()])
        self.blocks[0].attn = nn.Module()
        self.blocks[0].attn.q = nn.Linear(D, D, bias=False)
        self.head = head

    def hidden(self, ids, valid):
        return self.blocks[0].attn.q(self.emb(ids))

    def forward(self, ids, valid):
        return self.head(self.hidden(ids, valid))


def test_dense_head():
    lm = _LM(nn.Linear(D, V, bias=False))
    info = ta.head_access(lm)
    assert info["kind"] == "dense" and info["vocab_size"] == V and info["per_token"] is lm.head.weight
    assert info["per_token_name"] == "head.weight" and info["tied"] is False
    h = torch.randn(2, 3, D)
    assert torch.equal(ta.head_logits(lm, h), lm.head(h))


def test_kas_like_head():
    lm = _LM(_KASLike())
    info = ta.head_access(lm)
    assert info["kind"] == "kas" and info["vocab_size"] == V and info["per_token"] is lm.head.tok_u
    assert info["per_token_name"] == "head.tok_u" and info["tied"] is False
    assert ta.head_logits(lm, torch.randn(2, 3, D)).shape == (2, 3, V)


def test_tied_heads_are_reported():
    lm = _LM(nn.Linear(D, V, bias=False))
    lm.head.weight = lm.embedding.projection.weight  # shares storage (shape is irrelevant to the check)
    assert ta.head_access(lm)["tied"] is True
    kas = _LM(_KASLike())
    kas.head.up.weight = nn.Parameter(torch.randn(8, D))
    kas.embedding.projection.weight = kas.head.up.weight
    assert ta.head_access(kas)["tied"] is True


@_parametrize("head", [None, nn.Identity(), nn.Sequential(nn.Linear(D, V)), nn.Bilinear(D, D, V)])
def test_unknown_head_raises(head):
    lm = _LM(nn.Linear(D, V))
    lm.head = head
    with pytest.raises(ta.ArtifactError, match="unknown G5 output head"):
        ta.head_access(lm)


def test_kas_head_without_2d_tok_u_raises():
    head = _KASLike()
    head.tok_u = nn.Parameter(torch.zeros(V))  # 1-D: not a per-token matrix
    with pytest.raises(ta.ArtifactError, match="tok_u"):
        ta.head_access(_LM(head))


def test_sft_marker_rows_and_lora_skip_on_both_heads():
    import sft_g5

    for head in (nn.Linear(D, V, bias=False), _KASLike()):
        lm = _LM(head)
        for p in lm.parameters():
            p.requires_grad_(False)
        w = sft_g5.enable_head_rows(lm, [2, 7])
        assert w is ta.head_access(lm)["per_token"]
        x = torch.tensor([[1, 2, 7, 3]])
        lm(x, None).logsumexp(-1).sum().backward()
        rows = (w.grad.abs().sum(1) > 0).nonzero().flatten().tolist()
        assert rows == [2, 7]
        with pytest.raises(ValueError, match="outside"):
            sft_g5.enable_head_rows(lm, [V])

    class A:
        seed, lora_r, lora_alpha = 0, 2, 4.0

    lm = _LM(_KASLike())
    sft_g5.apply_method(lm, "lora", A)
    wrapped = [n for n, m in lm.named_modules() if type(m).__name__ == "LoRALinear"]
    assert wrapped == ["blocks.0.attn.q"]  # head.up / head.q are never wrapped


def test_sft_marker_rows_unknown_head_is_a_clear_error():
    import sft_g5

    lm = _LM(nn.Identity())
    with pytest.raises(ValueError, match="--marker-rows: unknown G5 output head"):
        sft_g5.enable_head_rows(lm, [1])


def test_sft_keep_weights_id_alias():
    import sft_g5

    base = ["--adapter-config", "a.yaml", "--train", "t.jsonl", "--eval", "e.jsonl", "--method", "full", "--out", "o"]
    assert sft_g5.parse_args(base + ["--keep-weights-id", "g10-dr2-dt"]).keep_run_id == "g10-dr2-dt"
    assert sft_g5.parse_args(base + ["--keep-run-id", "x"]).keep_run_id == "x"
    assert sft_g5.parse_args(base).keep_run_id == "g10-sft"


def test_dt_g5_targets_never_select_the_output_head():
    sys.path.insert(0, str(HERE.parent / "dt"))
    import mask as dtmask

    head_names = ["head", "head.proj", "head.tok_a", "head.gate", "head.up", "head.q", "mtp_head"]
    for key in ("g5_gate", "g5_mlp", "g5_attn"):
        assert not any(dtmask.target_match(n, dtmask.TARGET_SETS[key]) for n in head_names)
    assert dtmask.target_match("blocks.0.moe.experts.3.gate", dtmask.TARGET_SETS["g5_gate"])
