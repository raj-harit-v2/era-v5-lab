"""B2: model.vocab_pad_multiple pads the head rows; vocab_pad_mode keeps the padded columns out of the loss
(slice: cut off; mask: -inf bias). The padded model must be the unpadded one: same logits, same loss, zero gradient
on the padding rows, in both modes."""
import pytest
import torch

from models.config import ModelConfig
from models.gpt import GPT

V, D, MULT = 97, 32, 128      # 97 is not a multiple of 128, so the head really grows to 128 rows


def _cfg(**kw):
    base = dict(vocab_size=V, block_size=8, n_layer=1, n_head=2, n_embd=D, reversible=False, ffn="mlp",
                embedding="table", tie_embeddings=False)
    base.update(kw)
    return ModelConfig(**base)


@pytest.fixture(params=["slice", "mask"])
def mode(request):
    return request.param


def _pair(mode="slice", **kw):
    """(unpadded, padded) models with identical weights on the first V rows."""
    torch.manual_seed(0)
    plain = GPT(_cfg(**kw))
    padded = GPT(_cfg(vocab_pad_multiple=MULT, vocab_pad_mode=mode, **kw))
    sd = plain.state_dict()
    for k, v in padded.state_dict().items():
        if v.shape == sd[k].shape:
            v.copy_(sd[k])
        else:                                   # a padded [128, d] table / head: copy the first V rows
            v[:V].copy_(sd[k])
    return plain, padded


def test_padded_vocab_size():
    assert _cfg().padded_vocab_size == V
    assert _cfg(vocab_pad_multiple=MULT).padded_vocab_size == 128
    assert ModelConfig().padded_vocab_size == 131072 == ModelConfig(vocab_pad_multiple=128).padded_vocab_size


@pytest.mark.parametrize("bad", [0, -128, 1.5, None])
def test_bad_multiple_rejected(bad):
    with pytest.raises(AssertionError, match="vocab_pad_multiple"):
        _cfg(vocab_pad_multiple=bad)


MEMORY_BOUNDED = ["chunked", "fused", "fused_cached", "fused_liger", "fused_cce"]
CE_KW = {"chunked": dict(ce_chunks=3), "fused": dict(ce_chunks=3), "fused_cached": dict(ce_token_chunk=5),
         "fused_liger": dict(ce_token_chunk=5), "fused_cce": dict(ce_vocab_chunk=16)}


def _check_equal(kw, mode):
    plain, padded = _pair(mode, **kw)
    assert padded.head.weight.shape[0] == 128 and plain.head.weight.shape[0] == V
    idx = torch.randint(0, V, (2, 8))
    tgt = torch.randint(0, V, (2, 8))
    lp, lossp = plain(idx, tgt)
    ld, lossd = padded(idx, tgt)
    if lp is not None:                                   # memory-bounded CE returns logits=None
        assert ld.shape == lp.shape == (2, 8, V)
        torch.testing.assert_close(ld, lp)
    torch.testing.assert_close(lossd, lossp)
    lossp.backward()
    lossd.backward()
    tied = kw.get("tie_embeddings")
    for name in ("head", "mtp_head"):
        if hasattr(padded, name):
            g, gp = getattr(padded, name).weight.grad, getattr(plain, name).weight.grad
            assert g.shape[0] == 128
            assert g[V:].abs().max() == 0, f"{name}: padding rows must get no gradient"
            torch.testing.assert_close(g[:V], gp)        # tied: this is the table, so it holds the embedding grad too
    if tied:                                             # the tied table and head are one tensor
        assert padded.tok.weight is padded.head.weight
        torch.testing.assert_close(padded.tok.weight.grad[:V], plain.tok.weight.grad)
        assert padded.tok.weight.grad[V:].abs().max() == 0
    for (n, pp), (_, pd) in zip(plain.named_parameters(), padded.named_parameters()):
        if pp.shape == pd.shape:                         # every unpadded parameter gets the same gradient
            torch.testing.assert_close(pd.grad, pp.grad, msg=lambda m, n=n: f"{n}: {m}")


def test_torch_ce(mode):
    _check_equal({}, mode)


@pytest.mark.parametrize("ce", MEMORY_BOUNDED)
def test_memory_bounded_ce(ce, mode):                    # _head_ce dispatches each of these separately
    _check_equal(dict(ce_impl=ce, **CE_KW[ce]), mode)


@pytest.mark.parametrize("ce", ["torch"] + MEMORY_BOUNDED)
def test_tied_table(ce, mode):
    _check_equal(dict(tie_embeddings=True, ce_impl=ce, **CE_KW.get(ce, {})), mode)


@pytest.mark.parametrize("ce", ["torch"] + MEMORY_BOUNDED)
def test_mtp(ce, mode):                                  # the t+2 head goes through the same dispatch
    _check_equal(dict(mtp=True, ce_impl=ce, **CE_KW.get(ce, {})), mode)


def test_fused_slices_a_head_bias():
    """Heads are bias=False today; a biased head must be sliced with its weight (else a [128] bias meets [97] rows)."""
    _, padded = _pair(ce_impl="fused")
    padded.head.bias = torch.nn.Parameter(torch.zeros(128))
    x, y = torch.randn(6, D), torch.randint(0, V, (6,))
    for ce in ("fused", "fused_cached", "fused_liger", "fused_cce"):
        padded.cfg.ce_impl = ce
        padded._head_ce(padded.head, x, y).backward()


def test_accounting_ignores_padding_for_model_work(mode):
    from perfkit.metrics import flops_per_token
    for kw in (dict(), dict(mtp=True), dict(ce_impl="fused"), dict(ce_impl="chunked")):
        plain, padded = _pair(mode, **kw)
        assert padded.param_counts()[1] == plain.param_counts()[1]            # active
        assert padded.param_counts()[0] > plain.param_counts()[0]             # total: padded storage is real
        fp, fd = flops_per_token(plain, 5), flops_per_token(padded, 5)
        assert fd["model_flops_per_token"] == fp["model_flops_per_token"]     # MFU numerator is unchanged
        extra = fd["hw_flops_per_token"] - fp["hw_flops_per_token"]
        heads = 1 + (4 / 5 if kw.get("mtp") else 0)                          # T=5: the MTP head sees T-1 positions
        if kw.get("ce_impl") == "fused":
            assert extra == 0                                                 # fused paths run at vocab_size rows
        else:
            assert extra == pytest.approx(heads * (128 - V) * D * (8 if kw.get("ce_impl") == "chunked" else 6))


def test_no_padded_id_in_logits(mode):
    _, padded = _pair(mode)
    logits, _ = padded(torch.randint(0, V, (2, 8)))
    assert logits.shape[-1] == V


def test_mask_mode_head_output_and_buffer():
    """mask: padded columns of the raw head output are -inf, real ones are untouched; the -inf bias is a buffer."""
    plain, padded = _pair("mask")
    x = torch.randn(2, 8, D)
    out = padded._head_out(padded.head, x)
    assert out.shape[-1] == 128 and torch.isinf(out[..., V:]).all() and (out[..., V:] < 0).all()
    torch.testing.assert_close(out[..., :V], plain.head(x))
    assert "pad_bias" in dict(padded.named_buffers()) and "pad_bias" not in padded.state_dict()
    assert "pad_bias" not in dict(plain.named_buffers())


def test_mask_without_padding_is_the_plain_head():
    m = GPT(_cfg(vocab_size=128, vocab_pad_multiple=128, vocab_pad_mode="mask"))     # 128 is already a multiple
    assert "pad_bias" not in dict(m.named_buffers())
    x = torch.randn(2, 8, D)
    torch.testing.assert_close(m._head_out(m.head, x), m.head(x))


def test_mask_under_autocast_bf16():
    """-inf survives the bf16 cast of autocast: finite loss and gradients, padding rows get zero gradient."""
    plain, padded = _pair("mask")
    idx, tgt = torch.randint(0, V, (2, 8)), torch.randint(0, V, (2, 8))
    with torch.autocast("cpu", dtype=torch.bfloat16):
        _, lp = plain(idx, tgt)
        _, ld = padded(idx, tgt)
    assert torch.isfinite(ld) and abs(float(ld.detach()) - float(lp.detach())) < 1e-2
    ld.backward()
    g = padded.head.weight.grad
    assert torch.isfinite(g).all() and g[V:].abs().max() == 0


def test_bad_mode_rejected():
    with pytest.raises(AssertionError, match="vocab_pad_mode"):
        _cfg(vocab_pad_mode="zeros")
