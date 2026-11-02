"""Correctness tests for configurable MoE expert width."""

import pytest
import torch

from models.config import ModelConfig
from models.gpt import Block


def make_config(width, ratio=4):
    return ModelConfig(
        vocab_size=32,
        block_size=8,
        n_layer=1,
        n_head=2,
        n_embd=8,
        mlp_ratio=ratio,
        ffn="moe",
        moe={
            "num_experts": 4,
            "top_k": 2,
            "num_shared": 1,
            "bias_gamma": 0.01,
            "dispatch": "loop",
            "ffn_hidden": width,
        },
    )


@pytest.mark.parametrize("width", [None, 12, 768, 896])
def test_expert_shapes(width):
    block = Block(make_config(width), 0)
    expected = 32 if width is None else width
    assert block.ffn.expert_hidden == expected

    for expert in [*block.ffn.experts, *block.ffn.shared]:
        assert expert.c_fc.weight.shape == (expected, 8)
        assert expert.c_proj.weight.shape == (8, expected)


def test_null_mlp_ratio_with_explicit_width():
    block = Block(make_config(768, ratio=None), 0)
    assert block.ffn.expert_hidden == 768


@pytest.mark.parametrize("width", [0, -1, True, 1.5, "768"])
def test_invalid_width(width):
    with pytest.raises(AssertionError, match="ffn_hidden"):
        make_config(width)


def test_forward_backward():
    block = Block(make_config(12), 0)
    x = torch.randn(2, 4, 8, requires_grad=True)
    y = block(x)
    assert y.shape == x.shape
    y.square().mean().backward()
    assert x.grad is not None
    assert block.ffn.experts[0].c_fc.weight.grad is not None
