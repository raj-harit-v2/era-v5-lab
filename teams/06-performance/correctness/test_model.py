"""The whole model: models.gpt.GPT against an fp64 model written from the definitions, on real Brahmic tokens.

The parts have their own pairs (test_attention.py, test_ke.py, test_ke2.py, test_moe.py, test_reversible.py). This
file checks that they fit together the way bench runs them: configs/base.yaml (the default config of bench and
smoke) at full width and depth, so a change to base.yaml is tested as it is, the real
BrahmicTokenizer-131K vocabulary and KE byte table, real text (English, Hindi, Tamil, Bengali, code), the reversible
custom backward, the tied or untied 131072-row head and the fp32 cross-entropy. T is short (64) so it runs on a CPU.
Weights: the model's own init, except the head x HEAD_SCALE. At init the softmax over 131072 tokens is nearly
uniform, and a loss-side bug (label smoothing 0.01) then moves the loss by only 8e-6; with x10 by 5.8e-5.

Reference (never calls the model's forward; reads only its weights): KE v1 codec built byte by byte; KE2 from
G4's dense fp64 encoder (ke2.codec.encode_f64) on G4's raw table; LayerNorm,
GELU and cross-entropy by formula; naive GQA attention (test_attention.naive_attention); MoE computed densely
(every expert on every token, gate 0 when not chosen); the stack by its recurrence (midpoint p_next = p_prev +
2h f(p_curr), or plain x + f(x)) with ordinary autograd.

Pairs (outputs logits and loss; every parameter gradient). Every pair is configs/base.yaml as it is; the variants
change only the key named, so each other choice of base.yaml is still covered whatever base.yaml selects:
  model.base             base.yaml, fp32. With MoE the reference routes by itself, so the router is checked too.
  model.base.chunked     model.ce_impl=chunked, fp32: loss only (no logits), every gradient.
  model.base.mtp         model.mtp=true (t+2 head, loss = ntp + mtp), fp32. The reference adds the t+2 loss.
  model.base.mtp.chunked the same with model.ce_impl=chunked: both heads in checkpointed pieces.
  model.base.<key>       model.embedding = table / ke1 / ke2, model.ffn = mlp / moe, model.attn_impl = sdpa / eager,
                         model.reversible = true / false, model.activation = gelu / swiglu: the values base.yaml
                         does not select.
  model.base.activation_<a>.bf16 / .moe   the activation base.yaml does not select, under bf16 autocast (routing
                         replayed as in model.base.bf16) and with model.ffn=moe (routed + shared experts), fp32.
  model.base.bf16        base.yaml under bf16 autocast, TOLERANCES[bfloat16]. In bf16 a few tokens go to other
                         experts than in fp64 (4 of 128 here), and a flipped token makes the expert gradients
                         noise (13-26%). So this reference REPLAYS the fast routing (the expert choice only, from
                         models.reversible._forward_recording); gates and experts are still computed in fp64.
The fp32 builder asserts that no routing decision is a near tie (margin > 1e-6): a near tie could flip between
fp32 and fp64 and fail the pair for no bug. If that fires after a model change, change SEED.
"""
from __future__ import annotations

import functools
import math
from pathlib import Path

import pytest
import torch

from correctness.framework import PAIRS, Case, check, pair, pairs_in, to64
from models.config import load_config, model_config
# Bare name, as pytest and test_framework.py import test files: correctness.test_attention would load the file a
# second time and register its pairs twice.
from test_attention import naive_attention
from models.gpt import GPT

cache = functools.cache

ROOT = Path(__file__).resolve().parents[1]
B, T, SEED = 2, 64, 0
HEAD_SCALE = 10       # head weights x10: the softmax is peaked (max p ~0.4) instead of uniform over 131072
MIN_MARGIN = 1e-6
TEXT = (
    "The lab model reads Indian languages and English with one tokenizer of 131072 pieces. "
    "भारत में सैकड़ों भाषाएँ बोली जाती हैं, और हिंदी उनमें सबसे अधिक बोली जाने वाली भाषा है। "
    "தமிழ் உலகின் மிகப் பழமையான மொழிகளில் ஒன்று, இது இந்தியாவிலும் இலங்கையிலும் பேசப்படுகிறது. "
    "বাংলা ভাষা দক্ষিণ এশিয়ার একটি প্রধান ভাষা। "
    "def step(model, x, y):\n    loss = model(x, y)[1]\n    loss.backward()\n    return loss.item()\n"
    "Training runs at 512 tokens per sequence; this test uses 64 so that it runs on a laptop in seconds. "
    "मशीन लर्निंग मॉडल को हर लिपि के लिए सही टोकन चाहिए, नहीं तो एक शब्द कई टुकड़ों में बँट जाता है। "
)


@cache
def _tokenizer():
    from dataio.tokenizer import BrahmicTokenizer
    return BrahmicTokenizer()


@cache
def _token_bytes(max_pos):
    return _tokenizer().token_bytes(max_pos)


def _batch(device):
    ids = torch.tensor(_tokenizer().encode(TEXT), dtype=torch.int64)
    assert ids.numel() >= B * (T + 1), f"TEXT gives {ids.numel()} tokens, need {B * (T + 1)}"
    buf = ids[:B * (T + 1)].view(B, T + 1).to(device)
    return buf[:, :-1].contiguous(), buf[:, 1:].contiguous()


CONFIG = ROOT / "configs" / "base.yaml"


@cache
def _base():
    return model_config(load_config(CONFIG))


@cache
def _g4_table(vocab_size, max_pos):
    from models.ke2 import load_g4_table
    return load_g4_table(vocab_size, max_pos)


def _model(device, overrides=()):
    mcfg = model_config(load_config(CONFIG, overrides))
    torch.manual_seed(SEED)
    tb = _token_bytes(mcfg.ke_max_pos) if mcfg.embedding == "ke1" else None
    model = GPT(mcfg, tb).to(device).train()
    with torch.no_grad():
        model.head.weight.mul_(HEAD_SCALE)          # tied in base: the embedding table too
    return model, mcfg


# ------------------------------------------------------------------ fp64 reference
def ref_ke(idx, byte_table, lens, P):
    """kappa(t) = 1/sqrt(L) sum_p onehot256(b_p) (x) onehot_P(p), z-normalised (Bessel std, + 1e-6)."""
    rows = {}
    for t in idx.unique().tolist():
        L = min(int(lens[t]), P)
        v = torch.zeros(256 * P, dtype=torch.float64, device=idx.device)
        for p in range(L):
            v[int(byte_table[t, p]) * P + p] += 1.0 / math.sqrt(L)
        mean = v.sum() / v.numel()
        std = torch.sqrt(((v - mean) ** 2).sum() / (v.numel() - 1))
        rows[t] = (v - mean) / (std + 1e-6)
    return torch.stack([rows[t] for t in idx.reshape(-1).tolist()]).view(*idx.shape, 256 * P)


def ref_ln(x, ln):
    mu = x.mean(-1, keepdim=True)
    var = ((x - mu) ** 2).mean(-1, keepdim=True)
    return (x - mu) / torch.sqrt(var + ln.eps) * ln.weight + ln.bias


def ref_mlp(m, x):
    """Dense MLP or one expert. GELU by its erf formula, with biases; SwiGLU (the module has a c_gate):
    W_down @ (SiLU(W_gate x) * W_up x), SiLU(z) = z / (1 + exp(-z)), no biases."""
    if hasattr(m, "c_gate"):
        g = x @ m.c_gate.weight.T
        return ((g / (1.0 + torch.exp(-g))) * (x @ m.c_fc.weight.T)) @ m.c_proj.weight.T
    h = x @ m.c_fc.weight.T + m.c_fc.bias
    return (0.5 * h * (1.0 + torch.erf(h / math.sqrt(2.0)))) @ m.c_proj.weight.T + m.c_proj.bias


def ref_moe(moe, x, forced=None, margins=None):
    """Dense MoE: softmax router scores; top-k on scores + router_bias (or the forced choice); gates = chosen
    scores renormalised to 1; out = sum gate * expert + shared experts."""
    shp = x.shape
    x = x.reshape(-1, shp[-1])
    scores = torch.softmax(x @ moe.router.weight.T + moe.router.bias, dim=-1)
    biased = (scores + moe.router_bias).detach()
    order = biased.argsort(dim=1, descending=True)
    if margins is not None:
        srt = biased.gather(1, order)
        margins.append(srt[:, moe.top_k - 1] - srt[:, moe.top_k])
    chosen = order[:, :moe.top_k] if forced is None else forced.long()
    gates = scores * torch.zeros_like(scores).scatter(1, chosen, 1.0)
    gates = gates / gates.sum(1, keepdim=True)
    out = sum(gates[:, e:e + 1] * ref_mlp(moe.experts[e], x) for e in range(moe.num_experts))
    for s in moe.shared:
        out = out + ref_mlp(s, x)
    return out.reshape(shp)


def ref_forward(rm, cfg, idx, targets, routes=None, margins=None):
    if cfg.embedding == "ke1":
        x = ref_ke(idx, rm.tok.byte_table, rm.tok.lens, cfg.ke_max_pos) @ rm.tok.proj.weight.T
    elif cfg.embedding == "ke2":
        from ke2.codec import encode_f64                 # models.ke2 put teams/04-ke2/src on sys.path
        tb, lens = _g4_table(cfg.vocab_size, cfg.ke_max_pos)
        flat = idx.reshape(-1).cpu()
        codes = torch.from_numpy(encode_f64(tb[flat].numpy(), lens[flat].numpy(), cfg.ke_max_pos)).to(idx.device)
        x = (codes @ rm.tok.proj.weight.T).view(*idx.shape, -1)
    else:
        x = rm.tok.weight[idx]
    x = x + rm.pos.weight[:idx.shape[1]]

    def f(i, blk, p):
        a = naive_attention(ref_ln(p, blk.ln1), blk.attn.c_attn.weight, blk.attn.c_attn.bias,
                            blk.attn.c_proj.weight, blk.attn.c_proj.bias, cfg.n_head, cfg.n_kv_head)
        h = ref_ln(p + a, blk.ln2)
        if cfg.ffn == "moe":
            return a + ref_moe(blk.ffn, h, None if routes is None else routes[i], margins)
        return a + ref_mlp(blk.ffn, h)

    if cfg.reversible:
        a, b = x, x
        for i, blk in enumerate(rm.blocks):
            a, b = b, a + 2 * cfg.rev_h * f(i, blk, b)
        x = b
    else:
        for i, blk in enumerate(rm.blocks):
            x = x + f(i, blk, x)
    h = ref_ln(x, rm.ln_f)
    logits = h @ rm.head.weight.T

    def ce(lg, y):
        lg = lg.reshape(-1, lg.shape[-1])
        return (torch.logsumexp(lg, -1) - lg.gather(1, y.reshape(-1, 1)).squeeze(1)).mean()

    loss = ce(logits, targets)
    if cfg.mtp:                                       # position t predicts token t+2 = targets[t+1]
        loss = loss + ce(h[:, :-1] @ rm.mtp_head.weight.T, targets[:, 1:])
    return logits, loss


def _params(m):
    return [p for _, p in m.named_parameters()]


# ------------------------------------------------------------------ pairs
PAIR_OVERRIDES = {}                                   # pair name -> the base.yaml overrides it builds with


def _fp32_pair(name, overrides=(), grad_tol=None):
    PAIR_OVERRIDES[name] = list(overrides)

    @pair(name, grad_tol=grad_tol)
    def build(device):
        fast, mcfg = _model(device, overrides)
        ref = to64(fast)
        idx, targets = _batch(device)
        if mcfg.ffn == "moe":
            margins = []
            with torch.no_grad():
                ref_forward(ref, mcfg, idx, targets, margins=margins)
            low = torch.cat(margins).min().item()
            assert low > MIN_MARGIN, f"{name}: routing near tie (margin {low:.1e}); change SEED"
        if mcfg.ce_impl == "chunked":                 # chunked returns no logits with targets: compare the loss
            def fast_fn(i, t):
                logits, loss = fast(i, t)
                assert logits is None, "ce_impl=chunked must not build the logits"
                return loss
            return Case(ref=lambda i, t: ref_forward(ref, mcfg, i, t)[1], fast=fast_fn,
                        inputs=[idx, targets], params_ref=_params(ref), params_fast=_params(fast))
        return Case(ref=lambda i, t: ref_forward(ref, mcfg, i, t), fast=lambda i, t: fast(i, t),
                    inputs=[idx, targets], params_ref=_params(ref), params_fast=_params(fast))
    return build


_fp32_pair("model.base")
# The out-of-memory fallback (README, bench): head + cross-entropy in ce_chunks checkpointed pieces. Its loss and
# every gradient against the same fp64 reference; the head is recomputed in backward, so the head gradient too.
# grad_tol 1e-4, measured: the ln_f.weight gradient is 6.2e-5 off fp64 (ln_f.bias 3.8e-5), and the SAME 6.2e-5
# without chunking when the head runs as a 2-D matmul. The gradient reaching ln_f is (softmax - onehot) @ W, an
# fp32 sum over 131072 vocabulary rows, and the ln_f.weight gradient then cancels to a third of its terms.
# The plain path passes 5e-5 only because its 3-D head matmul takes a BLAS kernel that rounds differently.
# Still 100x below the 1.01 drill (1e-2).
_fp32_pair("model.base.chunked", ["model.ce_impl=chunked"], grad_tol=1e-4)
_fp32_pair("model.base.mtp", ["model.mtp=true"])
_fp32_pair("model.base.mtp.chunked", ["model.mtp=true", "model.ce_impl=chunked"], grad_tol=1e-4)

# The choices base.yaml does not make, one key at a time (base.yaml is read when this file is collected).
CHOICES = {"embedding": ["table", "ke1", "ke2"], "ffn": ["mlp", "moe"], "attn_impl": ["sdpa", "eager"],
           "reversible": [True, False], "activation": ["gelu", "swiglu"]}
for _key, _values in CHOICES.items():
    for _v in _values:
        if getattr(_base(), _key) != _v:
            _fp32_pair(f"model.base.{_key}_{str(_v).lower()}", [f"model.{_key}={str(_v).lower()}"])


def _bf16_pair(name, overrides=()):
    PAIR_OVERRIDES[name] = list(overrides)

    @pair(name, dtype=torch.bfloat16)
    def build(device):                                # a function of this module, so pairs_in() finds it
        return _bf16_case(device, list(overrides))
    return build


def _bf16_case(device, overrides=()):
    from models.reversible import _forward_recording
    fast, mcfg = _model(device, overrides)
    ref = to64(fast)
    idx, targets = _batch(device)

    def amp():
        return torch.autocast(device.type, dtype=torch.bfloat16)

    routes = None
    if mcfg.ffn == "moe" and mcfg.reversible:         # the bf16 expert choice, layer by layer
        with torch.no_grad(), amp():
            emb = fast.tok(idx) + fast.pos(torch.arange(idx.shape[1], device=device))
            routes = [r[0] for r in _forward_recording(fast.blocks, emb)[2]]

    def fast_fn(i, t):
        with amp():
            return fast(i, t)

    return Case(ref=lambda i, t: ref_forward(ref, mcfg, i, t, routes=routes), fast=fast_fn,
                inputs=[idx, targets], params_ref=_params(ref), params_fast=_params(fast))


_bf16_pair("model.base.bf16")
# The activation base.yaml does not select, in bf16 and with MoE experts (the fp32 dense case is in CHOICES above).
for _a in CHOICES["activation"]:
    if _base().activation != _a:
        _bf16_pair(f"model.base.activation_{_a}.bf16", [f"model.activation={_a}"])
        if _base().ffn != "moe":
            _fp32_pair(f"model.base.activation_{_a}.moe", [f"model.activation={_a}", "model.ffn=moe"])


@pytest.mark.parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    n_params = len(list(_model(torch.device("cpu"), PAIR_OVERRIDES.get(name, ()))[0].parameters()))
    assert len([k for k in errors if k.startswith("grad_param")]) == n_params, f"{name}: every gradient must be compared"


def test_mtp_loss_parts():
    """loss = ntp + mtp, both kept for logging; mtp off leaves the loss and the parameters as they were."""
    device = torch.device("cpu")
    idx, targets = _batch(device)
    plain, _ = _model(device, ["model.mtp=false"])
    g5, _ = _model(device, ["model.mtp=true"])
    assert not hasattr(plain, "mtp_head") and plain.loss_parts is None
    with torch.no_grad():
        _, loss = g5(idx, targets)
        _, ntp_only = plain(idx, targets)
    parts = g5.loss_parts
    assert torch.allclose(loss, parts["ntp"] + parts["mtp"])
    assert torch.allclose(parts["ntp"], ntp_only, rtol=1e-5), "same seed and weights: ntp must match the plain model"
    assert g5.mtp_head.weight.data_ptr() != g5.head.weight.data_ptr(), "MTP head must be untied"
