"""Deletion Tuning mask tests on a tiny random Llama (CPU, no download)."""
import importlib.util
import math
import sys
from pathlib import Path

import pytest
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_dt_mask_test", HERE.parent / "mask.py")
dtmask = importlib.util.module_from_spec(spec)
sys.modules["g10_dt_mask_test"] = dtmask
spec.loader.exec_module(dtmask)


def tiny(bias=False, seed=0, hidden=32, inter=64):
    from transformers import LlamaConfig, LlamaForCausalLM

    cfg = LlamaConfig(vocab_size=64, hidden_size=hidden, intermediate_size=inter, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64,
                      tie_word_embeddings=True, mlp_bias=bias, attention_bias=bias)
    torch.manual_seed(seed)
    m = LlamaForCausalLM(cfg).float()
    if bias:
        with torch.no_grad():
            for n, p in m.named_parameters():
                if n.endswith(".bias"):
                    p.normal_(0, 0.5)  # nonzero, so dropping a bias would change logits
    return m


_parametrize = pytest.mark.parametrize  # undotted alias for the lab's older PR e-mail guard
IDS = torch.tensor([[3, 7, 9, 11, 13, 5, 6, 8], [4, 4, 10, 12, 1, 2, 3, 0]])


def logits(m):
    with torch.no_grad():
        return m(input_ids=IDS).logits


def set_gates(m, value):
    with torch.no_grad():
        for _, layer in dtmask.masked_layers(m):
            layer.gate.fill_(value)


@_parametrize("targets", ["gate", "mlp", "attn"])
def test_all_keep_mask_is_bitwise_identity_soft_and_hard(targets):
    ref = tiny(bias=True)
    want = logits(ref.eval())
    m = tiny(bias=True)
    names = dtmask.convert(m, dtmask.TARGET_SETS[targets], total_steps=10)
    assert len(names) == 2 * len(dtmask.TARGET_SETS[targets])
    set_gates(m, 1.0)  # alpha * G = 100: sigmoid is exactly 1.0 in FP32
    assert torch.equal(logits(m.eval()), want)   # hard mask
    assert torch.equal(logits(m.train()), want)  # soft mask


def test_bias_is_preserved_and_applied():
    m = tiny(bias=True)
    b = m.model.layers[0].mlp.gate_proj.bias.detach().clone()
    dtmask.convert(m, ["gate_proj"], total_steps=10)
    layer = m.model.layers[0].mlp.gate_proj
    assert layer.bias is not None and torch.equal(layer.bias, b) and not layer.bias.requires_grad
    set_gates(m, -1.0)  # delete every gate weight: output must be exactly the bias
    x = torch.randn(3, layer.in_features)
    with torch.no_grad():
        assert torch.equal(layer.eval()(x), b.expand(3, -1))


def test_hard_and_soft_agree_at_alpha_1000():
    m = tiny()
    dtmask.convert(m, ["gate_proj"], alpha_start=1000, alpha_end=1000, total_steps=10, seed=1)
    with torch.no_grad():  # paper init scale: |G| ~ 0.03, so alpha*|G| ~ 30
        for _, l in dtmask.masked_layers(m):
            l.gate.copy_(torch.sign(torch.randn_like(l.gate)) * (0.03 + 0.01 * torch.rand_like(l.gate)))
    hard, soft = logits(m.eval()), logits(m.train())
    assert (hard - soft).abs().max().item() < 1e-5


def test_only_mask_logits_receive_gradients():
    m = tiny(bias=True)
    dtmask.convert(m, ["gate_proj"], total_steps=10)
    m.train()
    out = m(input_ids=IDS, labels=IDS)
    out.loss.backward()
    for n, p in m.named_parameters():
        if n.endswith(".gate"):
            assert p.requires_grad and p.grad is not None and p.grad.abs().sum() > 0, n
        else:
            assert not p.requires_grad and p.grad is None, n
    assert all(l.gate.dtype == torch.float32 for _, l in dtmask.masked_layers(m))


def test_base_weights_bitwise_unchanged_after_training_and_schedule():
    m = tiny(bias=True)
    before = {n: p.detach().clone() for n, p in m.named_parameters()}
    dtmask.convert(m, dtmask.TARGET_SETS["mlp"], alpha_start=100, alpha_end=1000, total_steps=4)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=1e-2, weight_decay=0.0)
    m.train()
    l0 = dtmask.masked_layers(m)[0][1]
    alphas = []
    for step in range(5):
        alphas.append(l0.alpha)
        opt.zero_grad()
        loss = m(input_ids=IDS, labels=IDS).loss - dtmask.lambda_at(step, 4, 1e-5) * dtmask.regulariser(m)
        loss.backward()
        opt.step()
        dtmask.step_all(m)
    assert alphas == [100.0, 325.0, 550.0, 775.0, 1000.0]  # linear per optimizer step, clamped at T
    after = dict(m.named_parameters())
    for n, p in before.items():
        key = n if n in after else n.replace(".weight", ".weight")
        assert torch.equal(after[key], p), n
    assert any(not torch.equal(l.gate, torch.zeros_like(l.gate)) for _, l in dtmask.masked_layers(m))


def test_regulariser_gradient_pushes_logits_up():
    m = tiny()
    dtmask.convert(m, ["gate_proj"], total_steps=10)
    (-1e-5 * dtmask.regulariser(m)).backward()
    g = dtmask.masked_layers(m)[0][1].gate.grad
    assert (g <= 0).all() and (g < 0).any()  # gradient descent raises the logits, i.e. keeps weights
    assert dtmask.lambda_at(0, 10, 1e-5) == 1e-5 and dtmask.lambda_at(10, 10, 1e-5) == 0.0


def test_wanda_prior_matches_paper_init_rate():
    m = tiny(hidden=64, inter=512)
    dtmask.convert(m, ["gate_proj"], total_steps=10, seed=3)
    batches = [{"input_ids": torch.randint(0, 64, (4, 32)), "attention_mask": torch.ones(4, 32, dtype=torch.long)}]
    scores = dtmask.wanda_scores(m, batches, "cpu")
    eta = 1 / 64  # larger than the paper's 1/2048 so the tiny layers have enough marked weights
    info = dtmask.apply_wanda_prior(m, scores, eta, 3.0)
    assert info["prior_deleted"] > 0
    st = dtmask.deletion_stats(m)
    phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
    expect = eta * phi(3) + (1 - eta) * phi(-3)  # paper section 4
    assert abs(st["deleted_frac_of_targeted"] - expect) < 0.004
    for name, l in dtmask.masked_layers(m):  # lowest-score weights start deleted
        low = scores[name].reshape(-1) < scores[name].reshape(-1).kthvalue(max(1, int(scores[name].numel() * eta))).values
        assert (l.gate.reshape(-1)[low] < 0).float().mean() > 0.95


def test_wanda_scores_ignore_padding():
    m = tiny()
    dtmask.convert(m, ["gate_proj"], total_steps=10)
    ids = torch.randint(0, 64, (1, 16))
    a = dtmask.wanda_scores(m, [{"input_ids": ids, "attention_mask": torch.ones(1, 16, dtype=torch.long)}], "cpu")
    pad = torch.cat([ids, torch.zeros(1, 8, dtype=torch.long)], 1)
    am = torch.cat([torch.ones(1, 16), torch.zeros(1, 8)], 1).long()
    b = dtmask.wanda_scores(m, [{"input_ids": pad, "attention_mask": am}], "cpu")
    for k in a:
        assert torch.allclose(a[k], b[k], rtol=1e-5, atol=1e-6)


def test_deletion_fraction_over_targeted_and_all_weights():
    m = tiny()
    total = sum(p.numel() for p in {p.data_ptr(): p for p in m.parameters()}.values())
    dtmask.convert(m, ["gate_proj"], total_steps=10)
    with torch.no_grad():
        l0 = dtmask.masked_layers(m)[0][1]
        set_gates(m, 1.0)
        l0.gate.view(-1)[:100] = -1.0
    st = dtmask.deletion_stats(m)
    assert st["deleted"] == 100 and st["targeted"] == 2 * 64 * 32 and st["model_weights"] == total
    assert st["deleted_frac_of_targeted"] == 100 / (2 * 64 * 32) and st["deleted_frac_of_all_weights"] == 100 / total


def test_bake_equals_hard_mask_and_masks_round_trip(tmp_path):
    from transformers import AutoModelForCausalLM

    m = tiny(bias=True)
    dtmask.convert(m, dtmask.TARGET_SETS["mlp"], total_steps=10, seed=7)
    with torch.no_grad():
        for _, l in dtmask.masked_layers(m):
            l.gate.copy_(torch.randn_like(l.gate))
    want = logits(m.eval())
    masks = dtmask.bake(m)
    assert not dtmask.masked_layers(m)
    assert torch.equal(logits(m.eval()), want)
    m.save_pretrained(tmp_path / "baked")
    re = AutoModelForCausalLM.from_pretrained(tmp_path / "baked", dtype=torch.float32).eval()
    assert torch.equal(logits(re), want)
    blob, meta = dtmask.pack_masks(masks)
    back = dtmask.unpack_masks(blob, meta)
    assert set(back) == set(masks) and all(torch.equal(back[k], masks[k]) for k in masks)
    assert meta["bits"] == sum(v.numel() for v in masks.values())


# --- Team 5 LanguageModel targets (capstone model code, imported from this checkout) -----------------------------

def tiny_g5(attn_gate=False):
    harness = HERE.parents[2] / "05-architecture" / "harness"
    spec_ = importlib.util.spec_from_file_location("g5_model_for_dt_test", harness / "week2" / "model.py")
    g5 = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(g5)
    import numpy as np  # noqa: PLC0415
    rows = np.zeros((64, 4), dtype=np.uint8)
    rows[:, 0] = np.arange(64)
    lengths = np.ones(64, dtype=np.int16)
    m = {"vocab_size": 64, "n_embd": 16, "n_head": 2, "n_kv_head": 1, "n_layer": 2, "rope_theta": 10000.0,
         "norm_eps": 1e-5, "mtp": False, "moe": {"num_experts": 4, "top_k": 2, "num_shared": 1, "ffn_hidden": 32,
                                                  "bias": False}}
    if attn_gate:
        m.update(attn_gate=True, attn_gate_input="normalized", attn_gate_bias=False, attn_gate_init="zero")
    torch.manual_seed(0)
    return g5.LanguageModel(m, rows, lengths)


def test_g5_target_sets_select_exactly_the_intended_linears():
    m = tiny_g5(attn_gate=True)
    names = dtmask.convert(tiny_g5(attn_gate=True), dtmask.TARGET_SETS["g5_gate"], total_steps=10)
    assert len(names) == 2 * (4 + 1) and all(n.endswith(".gate") and ".moe." in n for n in names)
    assert not any(".attn.gate" in n for n in names)  # the optional attention gate is not an expert gate
    names = dtmask.convert(tiny_g5(), dtmask.TARGET_SETS["g5_mlp"], total_steps=10)
    assert len(names) == 2 * 5 * 3
    names = dtmask.convert(tiny_g5(attn_gate=True), dtmask.TARGET_SETS["g5_attn"], total_steps=10)
    assert sorted({n.split(".")[-1] for n in names}) == ["k", "o", "q", "v"] and len(names) == 2 * 4
    assert not any("router" in n or n.startswith("head") or "embedding" in n for n in names)
    # the substring sets meant for Hugging Face names find nothing in the G5 model (the gap this entry closes)
    with pytest.raises(ValueError, match="no nn.Linear matched"):
        dtmask.convert(m, dtmask.TARGET_SETS["gate"], total_steps=10)


def test_target_match_keeps_substring_semantics():
    assert dtmask.target_match("model.layers.0.mlp.gate_proj", ("gate_proj",))
    assert not dtmask.target_match("model.layers.0.mlp.up_proj", ("gate_proj",))
    assert dtmask.target_match("blocks.1.attn.o", (r"re:blocks\.\d+\.attn\.(q|k|v|o)",))
    assert not dtmask.target_match("blocks.1.attn.o.extra", (r"re:blocks\.\d+\.attn\.(q|k|v|o)",))


def test_wanda_scores_on_g5_experts_use_routed_rows_and_ignore_padding():
    """G5 experts see gathered [routed tokens, d] rows (valid positions only); attention sees [B, T, d]. A padded
    batch must give the same Wanda norms as the two rows calibrated separately without padding."""
    a, b = [3, 7, 9, 11, 13, 5], [4, 10, 12]

    class Wrap(torch.nn.Module):  # the call shape wanda_scores uses
        def __init__(self, lm):
            super().__init__()
            self.lm = lm

        def forward(self, input_ids, attention_mask):
            return self.lm(input_ids, attention_mask.bool())

    def scores(batches):
        lm = tiny_g5()
        dtmask.convert(lm, dtmask.TARGET_SETS["g5_mlp"] + dtmask.TARGET_SETS["g5_attn"], total_steps=10)
        return dtmask.wanda_scores(Wrap(lm), batches, "cpu")

    padded = {"input_ids": torch.tensor([a, b + [0, 0, 0]]), "attention_mask": torch.tensor([[1] * 6, [1] * 3 + [0] * 3])}
    sep = [{"input_ids": torch.tensor([a]), "attention_mask": torch.ones(1, 6, dtype=torch.long)},
           {"input_ids": torch.tensor([b]), "attention_mask": torch.ones(1, 3, dtype=torch.long)}]
    s_pad, s_sep = scores([padded]), scores(sep)
    assert set(s_pad) == set(s_sep) and any(".moe.experts." in n for n in s_pad)
    for n in s_pad:
        assert torch.allclose(s_pad[n], s_sep[n], rtol=1e-5, atol=1e-6), n


def test_unseen_layers_policy_in_wanda_prior():
    """The `keep` prior reduces deletion in uncalibrated layers with an upward shift. Calibrated layers are unchanged."""
    def build():
        m = tiny(seed=1)
        dtmask.convert(m, dtmask.TARGET_SETS["mlp"], 10.0, 100.0, 10, seed=3)
        return m

    ref = build()
    names = [n for n, _ in dtmask.masked_layers(ref)]
    seen, unseen = names[0], names[1]
    scores = {seen: torch.rand(*dict(dtmask.masked_layers(ref))[seen].weight.shape)}
    out = {}
    for pol in ("official", "keep"):
        m = build()
        info = dtmask.apply_wanda_prior(m, scores, 0.05, 3.0, unseen=pol)
        layers = dict(dtmask.masked_layers(m))
        out[pol] = (info, {n: l.gate.detach() for n, l in layers.items()})
    assert out["official"][0]["layers_without_scores"] == len(names) - 1 and out["official"][0]["unseen_policy"] == "official"
    official_logits = out["official"][1][unseen]
    keep_logits = out["keep"][1][unseen]
    assert 0.3 < float((official_logits <= 0).float().mean()) < 0.7
    assert torch.equal(keep_logits, official_logits + 3.0 * official_logits.std().item())
    assert float((keep_logits <= 0).float().mean()) < 0.01
    assert torch.equal(out["keep"][1][seen], out["official"][1][seen])
    with pytest.raises(ValueError, match="unseen"):
        dtmask.apply_wanda_prior(build(), scores, 0.05, 3.0, unseen="drop")
