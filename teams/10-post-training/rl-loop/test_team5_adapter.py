"""CPU tests for team5_adapter.py and runtime.py.

    G10_BASELINE_TOKENIZER=<BrahmicTokenizer-131K tokenizer.json> \
    G10_OLMOE_SHAPE_CKPT=<dir with config.json + model.safetensors> \
    python -m pytest teams/10-post-training/rl-loop/test_team5_adapter.py -q -p no:cacheprovider

FIXTURE, NOT A G5 ARTIFACT. Team 5's small-model checkpoint does not exist yet. These tests build:
  * tokenizer v0.1 from the baseline with Team 3's own build_v0.py / build_v0_1.py (hash-checked against
    teams/03-tokenizer/v0/SHA256SUMS), and its KE2 raw table with Team 4's build_tables.py;
  * a G5 LanguageModel checkpoint at the geometry of the 25 MB OLMoE shape checkpoint, with the attention, router,
    expert and norm tensors copied from that file. The KE2 projection and the output head have no OLMoE
    counterpart and are seeded. The checkpoint carries the fixture marker, so real mode refuses it.
They prove the adapter's checks and plumbing, not anything about the delivered model.
Tests that need the two inputs skip when the environment variables are not set.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from pytest import fixture  # bare decorator: pr-guard reads '+@a.b' as an email
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import runtime  # noqa: E402
import team5_adapter as ta  # noqa: E402

REPO = HERE.parents[2]
TEAM5 = REPO / "teams" / "05-architecture"
TEAM10 = REPO / "teams" / "10-post-training"
BASELINE_SHA = "01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff"
V0_1_SHA = "a33c9907ec16876bc57b011714e8380879919fba1327d84bfb0d60407fe6e578"
OLMOE_SHAPE_SHA = "0bd7ae8765726b87521ff6be7547f4ad6673eb7c908abfc37068e2063e8ce15c"  # model.safetensors
G5_ROUTER = [r"(^|\.)moe\.router\.weight$"]
SPECIAL = {"pad": {"token": "<|pad|>", "id": 130726}, "end_of_turn": {"token": "<|im_end|>", "id": 130816},
           "end_of_sequence": {"token": "<|endoftext|>", "id": 130822},
           "im_start": {"token": "<|im_start|>", "id": 129994}, "stop": ["end_of_turn", "end_of_sequence"]}

BASELINE = os.environ.get("G10_BASELINE_TOKENIZER")
OLMOE = os.environ.get("G10_OLMOE_SHAPE_CKPT")
needs_inputs = pytest.mark.skipif(not (BASELINE and OLMOE), reason="set G10_BASELINE_TOKENIZER and G10_OLMOE_SHAPE_CKPT")


def _git_head() -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


# --- fixture construction ------------------------------------------------------------------------------

class FX:
    pass


def _olmoe_overrides(cfg: dict) -> dict:
    return {"n_layer": cfg["num_hidden_layers"], "n_head": cfg["num_attention_heads"],
            "n_kv_head": cfg["num_key_value_heads"], "n_embd": cfg["hidden_size"],
            "block_size": cfg["max_position_embeddings"],
            "moe": {"num_experts": cfg["num_experts"], "top_k": cfg["num_experts_per_tok"], "num_shared": 0,
                    "ffn_hidden": cfg["intermediate_size"]}}


def _transplant_map(n_layer: int, n_experts: int) -> dict:
    m = {"norm.weight": "model.norm.weight"}
    for i in range(n_layer):
        g, o = f"blocks.{i}.", f"model.layers.{i}."
        m.update({g + "n1.weight": o + "input_layernorm.weight", g + "n2.weight": o + "post_attention_layernorm.weight",
                  g + "moe.router.weight": o + "mlp.gate.weight"})
        for a in "qkvo":
            m[g + f"attn.{a}.weight"] = o + f"self_attn.{a}_proj.weight"
        for e in range(n_experts):
            for a in ("gate", "up", "down"):
                m[g + f"moe.experts.{e}.{a}.weight"] = o + f"mlp.experts.{e}.{a}_proj.weight"
    return m


def _save_g5_pt(sd: dict, path: Path, fixture: bool = True) -> str:
    """Same top-level layout as harness/train_week2.py's torch.save, plus the fixture marker."""
    obj = {"model": sd, "optimizer": {"state": {}, "param_groups": []},
           "stream": {"order": [0, 1], "offset": 0, "rng": torch.Generator().manual_seed(0).get_state()},
           "torch_rng": torch.get_rng_state(), "cuda_rng": None, "python_rng": random.getstate(),
           "numpy_rng": np.random.get_state(), "step": 0, "identity_sha256": "0" * 64, "trace": [], "ntp_trace": [],
           "rows": [], "wall_seconds": 0.0}
    if fixture:
        obj[ta.FIXTURE_MARKER_KEY] = ta.FIXTURE_MARKER_VALUE
    torch.save(obj, path)
    return ta.sha256_file(path)


@fixture(scope="session")
def fx(tmp_path_factory):
    if not (BASELINE and OLMOE):
        pytest.skip("set G10_BASELINE_TOKENIZER and G10_OLMOE_SHAPE_CKPT")
    if _git_head() is None:
        pytest.skip("G5 source pinning needs a git checkout")
    return build_fixture(tmp_path_factory.mktemp("t0_fixture"))


def build_fixture(d: Path) -> FX:
    """Build the labelled fixture inputs into directory d (also used to write CLI configs by hand)."""
    head = _git_head()
    f = FX()
    f.dir = d
    assert ta.sha256_file(Path(BASELINE)) == BASELINE_SHA
    olmoe = Path(OLMOE)
    f.olmoe_st = olmoe / "model.safetensors"
    assert ta.sha256_file(f.olmoe_st) == OLMOE_SHAPE_SHA, "not the pinned OLMoE shape fixture"
    f.olmoe_cfg = json.loads((olmoe / "config.json").read_text())
    # Team 3 tokenizer v0 -> v0.1, Team 4 KE2 raw table: their own scripts, isolated interpreter.
    v0, f.tok = d / "v0_tokenizer.json", d / "v0_1" / "tokenizer.json"
    f.tok.parent.mkdir()
    tv0 = REPO / "teams" / "03-tokenizer" / "v0"
    subprocess.run([sys.executable, "-I", str(tv0 / "build_v0.py"), BASELINE, str(v0)], check=True, capture_output=True)
    subprocess.run([sys.executable, "-I", str(tv0 / "build_v0_1.py"), str(v0), str(f.tok)], check=True, capture_output=True)
    assert ta.sha256_file(f.tok) == V0_1_SHA
    subprocess.run([sys.executable, "-I", str(REPO / "teams/04-ke2/src/build_tables.py"), "--tokenizer", str(f.tok),
                    "--out", str(d / "ke2"), "--pos-dims", "32"], check=True, capture_output=True)
    f.table = d / "ke2" / "raw_table_P32.npz"
    f.template = TEAM10 / "chat-format" / "chat_template.jinja"
    f.head = head
    f.g5_files = {p: ta.sha256_file(TEAM5 / p) for p in ta.G5_FILES_REQUIRED}
    f.overrides = _olmoe_overrides(f.olmoe_cfg)
    if str(TEAM5 / "harness") not in sys.path:
        sys.path.append(str(TEAM5 / "harness"))  # after rl-loop: G5 harness/train.py must not shadow rl-loop/train.py
    from week2.artifacts import Artifacts  # noqa: PLC0415
    f.art = Artifacts(f.tok, f.table, expected_tokenizer_sha=V0_1_SHA, expected_vocab=131072)
    f.table_content = f.art.table_content_sha
    f.probe_ids = f.art.encode("नमस्ते! 12 + 30 = 42. Hello, world.")
    f.ckpt, f.ckpt_sha, f.transplanted = _make_fixture_ckpt(f, d / "g5_fixture.pt")
    return f


def _spec(f) -> dict:
    g5 = ta._load_g5({"root": str(REPO), "commit": f.head, "files_sha256": f.g5_files}, Path("/"))
    cfg = ta._resolve(g5, {"arm": "configs/arms/t1.yaml", "resolution": "configs/small/smoke_resolution.yaml"},
                      "fixture", f.overrides)
    return g5, cfg["model"]


def _make_fixture_ckpt(f, path: Path):
    from safetensors import safe_open  # noqa: PLC0415
    g5, spec = _spec(f)
    torch.manual_seed(0)
    model = g5["mods"]["week2.model"].LanguageModel(spec, f.art.bytes, f.art.lengths)
    sd = model.state_dict()
    tmap = _transplant_map(spec["n_layer"], spec["moe"]["num_experts"])
    with safe_open(str(f.olmoe_st), "pt") as src:
        for g, o in tmap.items():
            t = src.get_tensor(o)
            assert t.shape == sd[g].shape, (g, o)
            sd[g] = t.clone()
    sha = _save_g5_pt(sd, path)
    return path, sha, sorted(tmap)


def _sd(f) -> dict:
    return ta._read_checkpoint(f.ckpt, "g5_train_week2_pt")[0]  # the adapter's weights_only reader


def cfg_for(f, **kw) -> dict:
    c = {"_base": "/", "mode": "fixture",
         "g5": {"root": str(REPO), "commit": f.head, "files_sha256": dict(f.g5_files),
                "arm": "configs/arms/t1.yaml", "resolution": "configs/small/smoke_resolution.yaml"},
         "fixture_overrides": copy.deepcopy(f.overrides),
         "checkpoint": {"path": str(f.ckpt), "sha256": f.ckpt_sha, "format": "g5_train_week2_pt"},
         "ke2": {"table": str(f.table), "table_file_sha256": ta.sha256_file(f.table),
                 "table_content_sha256": f.table_content, "vocab_size": 131072, "pos_dim": 32},
         "tokenizer": {"path": str(f.tok), "sha256": V0_1_SHA, "chat_template": str(f.template),
                       "chat_template_sha256": ta.sha256_file(f.template)},
         "special_tokens": copy.deepcopy(SPECIAL),
         "trainable": {"router_patterns": list(G5_ROUTER), "trainable_patterns": [r"\.attn\."]},
         "probe": {"ids": list(f.probe_ids)}}
    for path, value in kw.items():
        node = c
        keys = path.split("__")
        for k in keys[:-1]:
            node = node[k]
        if value is DELETE:
            node.pop(keys[-1], None)
        else:
            node[keys[-1]] = value
    return c


DELETE = object()


@fixture(scope="session")
def bundle(fx):
    r = ta.build(cfg_for(fx))
    assert r.status == ta.FIXTURE_READY
    return r.bundle


def _rejects(f, match: str, **kw):
    with pytest.raises(ta.ArtifactError, match=match):
        ta.build(cfg_for(f, **kw))


# --- the OLMoE shape checkpoint as a real file ------------------------------------------------------------

@needs_inputs
def test_olmoe_shape_fixture_identity_and_naming(fx):
    from safetensors import safe_open  # noqa: PLC0415
    import router  # noqa: PLC0415
    import re  # noqa: PLC0415
    with safe_open(str(fx.olmoe_st), "pt") as s:
        keys = list(s.keys())
        assert s.get_slice("lm_head.weight").get_shape() == [50304, 64]
    assert len(keys) == 69
    olmoe_routers = [k for k in keys if re.search(router.ROUTER_PATTERNS[0], k)]
    assert olmoe_routers == ["model.layers.0.mlp.gate.weight", "model.layers.1.mlp.gate.weight"]
    assert not any(re.search(G5_ROUTER[0], k) for k in keys)  # OLMoE names are not a G5 contract


@needs_inputs
def test_olmoe_checkpoint_rejected_as_g5(fx):
    sha = ta.sha256_file(fx.olmoe_st)
    _rejects(fx, "keys do not match the G5 model", mode="real", fixture_overrides=None,
             checkpoint={"path": str(fx.olmoe_st), "sha256": sha, "format": "state_dict_safetensors"},
             probe={"ids": [1, 2, 3], "expected_mean_nll": 1.0})
    _rejects(fx, "fixture marker", checkpoint={"path": str(fx.olmoe_st), "sha256": sha,
                                               "format": "state_dict_safetensors"})


# --- bundle contents --------------------------------------------------------------------------------------

@needs_inputs
def test_fixture_bundle_manifest(fx, bundle):
    m = bundle.manifest
    assert m["status"] == ta.FIXTURE_READY and m["learning_report_allowed"] is False
    assert m["g5"]["commit"] == fx.head and set(m["g5"]["files_sha256"]) == set(ta.G5_FILES_REQUIRED)
    assert m["checkpoint"]["sha256"] == fx.ckpt_sha and m["checkpoint"]["fixture_marker"] is True
    assert m["ke2"]["tokenizer_sha256"] == V0_1_SHA and m["ke2"]["vocab_size"] == 131072
    assert m["ke2"]["table_content_sha256"] == fx.table_content
    sel = m["selection"]
    assert sel["router_names"] == ["blocks.0.moe.router.weight", "blocks.1.moe.router.weight"]
    assert sel["router_count"] == 2 * 8 * 64
    assert all(".attn." in n for n in sel["trainable_names"]) and len(sel["trainable_names"]) == 8
    assert set(sel["trainable_dtypes"].values()) == {"torch.float32"}
    assert sel["trainable_count"] == 2 * 4 * 64 * 64
    names = {r["name"]: r for r in m["inventory"]}
    assert names["embedding.rows"]["kind"] == "buffer" and names["embedding.rows"]["shape"] == [131072, 32]
    assert names["head.weight"]["shape"] == [131072, 64]
    sp = m["special_tokens"]
    assert sp["stop_ids"] == [130816, 130822] and sp["pad_id"] == 130726 == sp["pad_id_g5"]
    trainable_now = sorted(n for n, p in bundle.model.named_parameters() if p.requires_grad)
    assert trainable_now == sel["trainable_names"]
    # the transplanted OLMoE tensors are what was loaded
    from safetensors import safe_open  # noqa: PLC0415
    with safe_open(str(fx.olmoe_st), "pt") as s:
        assert torch.equal(bundle.model.blocks[1].moe.router.weight, s.get_tensor("model.layers.1.mlp.gate.weight"))
    with pytest.raises(RuntimeError, match="refusing a learning report"):
        ta.require_learning_ready(ta.Result(ta.FIXTURE_READY, "fixture", [], m, bundle))


@needs_inputs
def test_waiting_when_checkpoint_absent(fx):
    for ck in ({"path": str(fx.dir / "not_there.pt"), "sha256": "0" * 64, "format": "g5_train_week2_pt"},
               {"path": None, "sha256": None, "format": None}):
        r = ta.build(cfg_for(fx, mode="real", fixture_overrides=None, checkpoint=ck, probe=DELETE))
        assert r.status == ta.WAITING == "WAITING_FOR_G5_ARTIFACT" and r.bundle is None
        assert r.manifest["status"] == ta.WAITING
        with pytest.raises(RuntimeError, match="WAITING_FOR_G5_ARTIFACT"):
            r.require_bundle()
        with pytest.raises(RuntimeError, match="refusing a learning report"):
            ta.require_learning_ready(r)


@needs_inputs
def test_real_mode_refuses_fixture_inputs(fx):
    _rejects(fx, "fixture marker", mode="real", fixture_overrides=None,
             probe={"ids": list(fx.probe_ids), "expected_mean_nll": 12.0})
    _rejects(fx, "only allowed in fixture mode", mode="real")
    # a fixture-mode build without the marker is refused too
    sd = _sd(fx)
    p = fx.dir / "unmarked.pt"
    sha = _save_g5_pt(sd, p, fixture=False)
    _rejects(fx, "only loads checkpoints carrying the fixture marker",
             checkpoint={"path": str(p), "sha256": sha, "format": "g5_train_week2_pt"})


# --- rejection cases ----------------------------------------------------------------------------------------

@needs_inputs
def test_missing_artifacts_rejected(fx):
    _rejects(fx, "checkpoint missing", checkpoint__path=str(fx.dir / "nope.pt"))
    _rejects(fx, "KE2 table missing", ke2__table=str(fx.dir / "nope.npz"))
    _rejects(fx, "tokenizer missing", tokenizer__path=str(fx.dir / "nope.json"))
    _rejects(fx, "chat template missing", tokenizer__chat_template=str(fx.dir / "nope.jinja"))
    _rejects(fx, "ke2.table_file_sha256 is required", ke2__table_file_sha256=None)
    _rejects(fx, "checkpoint hash mismatch", checkpoint__sha256="f" * 64)
    _rejects(fx, "tokenizer hash mismatch", tokenizer__sha256="f" * 64)


@needs_inputs
def test_wrong_vocabulary_rejected(fx):
    # the vocabulary the KE2 table/tokenizer must have
    _rejects(fx, "Vocabulary mismatch", ke2__vocab_size=50304)
    # a KE2 table built for a different tokenizer (the baseline table committed by Team 4)
    other = REPO / "teams/04-ke2/results/tables/raw_table_P32.npz"
    _rejects(fx, "different tokenizer", ke2__table=str(other), ke2__table_file_sha256=ta.sha256_file(other))
    # a checkpoint whose output head has the OLMoE vocabulary
    from safetensors import safe_open  # noqa: PLC0415
    sd = _sd(fx)
    with safe_open(str(fx.olmoe_st), "pt") as s:
        sd["head.weight"] = s.get_tensor("lm_head.weight")
    p = fx.dir / "olmoe_vocab_head.pt"
    sha = _save_g5_pt(sd, p)
    _rejects(fx, "vocabulary/KE2 shape mismatch", checkpoint={"path": str(p), "sha256": sha, "format": "g5_train_week2_pt"})
    # special token ids that do not belong to this tokenizer
    _rejects(fx, "special token end_of_sequence", special_tokens__end_of_sequence={"token": "<|endoftext|>", "id": 36})


@needs_inputs
def test_checkpoint_ke2_must_equal_table(fx):
    sd = _sd(fx)
    sd["embedding.rows"] = sd["embedding.rows"].clone()
    sd["embedding.rows"][1000, 0] ^= 1
    p = fx.dir / "tampered_rows.pt"
    sha = _save_g5_pt(sd, p)
    _rejects(fx, "KE2 rows differ", checkpoint={"path": str(p), "sha256": sha, "format": "g5_train_week2_pt"})
    sd = _sd(fx)
    del sd["blocks.1.attn.q.weight"]
    sd["extra.weight"] = torch.zeros(1)
    p = fx.dir / "wrong_keys.pt"
    sha = _save_g5_pt(sd, p)
    _rejects(fx, r"missing \['blocks.1.attn.q.weight'\].*unexpected \['extra.weight'\]",
             checkpoint={"path": str(p), "sha256": sha, "format": "g5_train_week2_pt"})


@needs_inputs
def test_router_selection_rejections(fx):
    _rejects(fx, "match no parameter", trainable__router_patterns=[r"(^|\.)mlp\.gate\.weight$"])  # OLMoE regex
    _rejects(fx, "match expert parameters", trainable__router_patterns=[r"gate\.weight$"])
    _rejects(fx, "match expert parameters", trainable__router_patterns=G5_ROUTER + [r"experts\.0\.gate\.weight$"])
    _rejects(fx, "miss routers", trainable__router_patterns=[r"blocks\.0\.moe\.router\.weight$"])
    _rejects(fx, "match non-router parameters", trainable__router_patterns=G5_ROUTER + [r"\.attn\.q\."])
    _rejects(fx, "trainable_patterns .* match no parameter", trainable__trainable_patterns=[r"\.self_attn\."])
    _rejects(fx, "select frozen router weights", trainable__trainable_patterns=[r"\.attn\.", r"router"])


@needs_inputs
def test_g5_source_pinning(fx):
    _rejects(fx, "config pins", g5__commit="0" * 40)
    bad = dict(fx.g5_files)
    bad["harness/week2/model.py"] = "0" * 64
    _rejects(fx, "G5 file hash mismatch for harness/week2/model.py", g5__files_sha256=bad)
    short = {k: v for k, v in fx.g5_files.items() if k != "harness/train_week2.py"}
    _rejects(fx, "must pin", g5__files_sha256=short)
    _rejects(fx, "cannot change", fixture_overrides={**fx.overrides, "vocab_size": 50304})


# --- determinism, no mutation, save/reload ----------------------------------------------------------------

@needs_inputs
def test_no_mutation_and_repeated_builds_agree(fx):
    c = cfg_for(fx)
    before = copy.deepcopy(c)
    r1, r2 = ta.build(c), ta.build(c)
    assert c == before  # the supplied config is untouched (overrides.moe is not popped)
    assert r1.manifest == r2.manifest
    assert r1.manifest["model_hash_g5"] == r2.manifest["model_hash_g5"]
    ids = torch.tensor([fx.probe_ids])
    v = torch.ones_like(ids, dtype=torch.bool)
    with torch.no_grad():
        assert torch.equal(r1.bundle.forward(ids, v), r2.bundle.forward(ids, v))
    s = torch.random.get_rng_state()
    ta.build(c)
    assert torch.equal(s, torch.random.get_rng_state())  # building does not advance the caller's RNG


@needs_inputs
def test_load_save_reload_equality(fx, bundle):
    out = fx.dir / "export.safetensors"
    sha = ta.export_state(bundle, out)
    r2 = ta.build(cfg_for(fx, checkpoint={"path": str(out), "sha256": sha, "format": "state_dict_safetensors"}))
    a, b = bundle.model.state_dict(), r2.bundle.model.state_dict()
    assert a.keys() == b.keys() and all(torch.equal(a[k], b[k]) and a[k].dtype == b[k].dtype for k in a)
    assert r2.manifest["model_hash_g5"] == bundle.manifest["model_hash_g5"]
    assert r2.manifest["probe"]["mean_nll"] == bundle.manifest["probe"]["mean_nll"]
    assert r2.manifest["inventory_sha256"] == bundle.manifest["inventory_sha256"]
    # and the probe value pins it: a wrong expectation is refused
    exp = bundle.manifest["probe"]["mean_nll"]
    r3 = ta.build(cfg_for(fx, probe={"ids": list(fx.probe_ids), "expected_mean_nll": exp, "atol": 1e-6}))
    assert r3.manifest["probe"]["verified_against"] == exp
    _rejects(fx, "probe mean NLL", probe={"ids": list(fx.probe_ids), "expected_mean_nll": exp + 0.01, "atol": 1e-6})


# --- forward, labels, padding ----------------------------------------------------------------------------

@needs_inputs
def test_forward_is_the_delivered_main_head(fx, bundle):
    ids = torch.tensor([fx.probe_ids])
    v = torch.ones_like(ids, dtype=torch.bool)
    with torch.no_grad():
        got = bundle.forward(ids, v)
        m = bundle.model
        ref = m.head(m.hidden(ids, v))
        main, mtp = m(ids, v, return_mtp=True)
    assert got.shape == (1, len(fx.probe_ids), 131072)
    assert torch.equal(got, ref) and torch.equal(got, main) and mtp is None
    assert type(m).__module__ == "week2.model" and Path(sys.modules["week2.model"].__file__).resolve() == (
        TEAM5 / "harness/week2/model.py").resolve()


@needs_inputs
def test_real_causal_labels_and_backward(fx, bundle):
    msgs = [{"role": "user", "content": "2 + 2 कितना है?"}, {"role": "assistant", "content": "उत्तर 4 है।"}]
    text = bundle.render_mod.render(msgs, effort="1k")
    ids = fx.art.encode(text)
    prefix = bundle.encode_generation_prefix(msgs[:1], effort="1k")
    assert ids[:len(prefix)] == prefix  # the generation prefix is exactly the training-time prefix
    im_end = SPECIAL["end_of_turn"]["id"]
    end = len(ids) - 1 - ids[::-1].index(im_end)  # the assistant's <|im_end|>
    loss_mask = torch.zeros(1, len(ids), dtype=torch.bool)
    loss_mask[0, len(prefix):end + 1] = True  # assistant content and its end-of-turn marker are targets
    t = torch.tensor([ids])
    v = torch.ones_like(t, dtype=torch.bool)
    tgt, pair = bundle.causal_targets(t, v)
    assert torch.equal(tgt[0], t[0, 1:]) and bool(pair.all())
    supervised = tgt[0][(pair & loss_mask[:, 1:])[0]].tolist()
    assert supervised[-1] == im_end and supervised == ids[len(prefix):end + 1]
    assert bundle.decode_completion(supervised) == "उत्तर 4 है।<|im_end|>"
    bundle.model.zero_grad(set_to_none=True)
    s, n = bundle.token_nll(t, v, loss_mask)
    logits = bundle.forward(t, v)[0, :-1].float()
    manual = torch.nn.functional.cross_entropy(logits, t[0, 1:], reduction="none")[loss_mask[0, 1:]].sum()
    assert n == len(supervised) and torch.allclose(s, manual)
    (s / n).backward()
    for name, p in bundle.model.named_parameters():
        if name in bundle.selection["trainable_names"]:
            assert p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0, name
        else:
            assert p.grad is None, name  # router and experts receive nothing
    bundle.model.zero_grad(set_to_none=True)


@needs_inputs
def test_padding_invariance_right_padding(fx, bundle):
    a = fx.art.encode("ప్రశ్న: 7 × 6 = ?") + [SPECIAL["end_of_turn"]["id"]]
    b = fx.art.encode("x = 3")
    T = max(len(a), len(b))
    pad = SPECIAL["pad"]["id"]
    ids = torch.tensor([a + [pad] * (T - len(a)), b + [pad] * (T - len(b))])
    valid = torch.tensor([[1] * len(a) + [0] * (T - len(a)), [1] * len(b) + [0] * (T - len(b))], dtype=torch.bool)
    with torch.no_grad():
        batched = bundle.forward(ids, valid)
        for row, seq in enumerate([a, b]):
            alone = bundle.forward(torch.tensor([seq]), torch.ones(1, len(seq), dtype=torch.bool))
            assert torch.allclose(batched[row, :len(seq)], alone[0], atol=1e-5, rtol=1e-5)
        s_b, n_b = bundle.token_nll(ids, valid)
        s_a = sum(bundle.token_nll(torch.tensor([q]), torch.ones(1, len(q), dtype=torch.bool))[0] for q in (a, b))
    assert n_b == len(a) - 1 + len(b) - 1 and torch.allclose(s_b, s_a, atol=1e-4)
    left = torch.tensor([[pad] + b]), torch.tensor([[False] + [True] * len(b)])
    with pytest.raises(ValueError, match="left padding"):
        bundle.forward(*left)
    holes = valid.clone()
    holes[1, 0:2] = torch.tensor([True, False])
    holes[1, 2] = True
    with pytest.raises(ValueError, match="right-padded"):
        bundle.forward(ids, holes)
    with pytest.raises(ValueError, match="outside the vocabulary"):
        bundle.forward(torch.tensor([[131072]]), torch.ones(1, 1, dtype=torch.bool))


# --- generation and stop ids ------------------------------------------------------------------------------

@needs_inputs
def test_fixed_seed_generation(fx, bundle):
    prompt = bundle.encode_generation_prefix([{"role": "user", "content": "नमस्ते"}])
    g = lambda s: torch.Generator(device="cpu").manual_seed(s)  # noqa: E731
    s1 = bundle.sample(prompt, 3, 6, 1.0, g(7))
    s2 = bundle.sample(prompt, 3, 6, 1.0, g(7))
    s3 = bundle.sample(prompt, 3, 6, 1.0, g(8))
    assert torch.equal(s1[0], s2[0]) and torch.equal(s1[1], s2[1]) and s1[2] == s2[2]
    assert not torch.equal(s1[0], s3[0])
    # parity with the unchanged rl-loop seam (policy.module_policy) when the only stop is end_of_turn
    from policy import module_policy  # noqa: PLC0415
    pol = module_policy(bundle.model, SPECIAL["end_of_turn"]["id"], "cpu")
    pseq, pmask = pol.sample(prompt, 3, 6, 1.0, g(7))
    aseq, amask, _ = bundle.sample(prompt, 3, 6, 1.0, g(7), stop_ids=[SPECIAL["end_of_turn"]["id"]])
    P = len(prompt)
    assert torch.equal(pmask, amask)
    assert torch.equal(pseq[:, P:][pmask], aseq[:, P:][amask])
    # the policy train.py gets is bundle.sample with every stop id
    tseq, tmask = bundle.policy().sample(prompt, 3, 6, 1.0, g(7))
    assert torch.equal(tseq, s1[0]) and torch.equal(tmask, s1[1])
    with pytest.raises(ValueError, match="explicit generator"):
        bundle.sample(prompt, 1, 2, 1.0, None)
    with pytest.raises(ValueError, match="exceeds block_size"):
        bundle.sample(prompt, 1, bundle.spec["block_size"], 0.0, None)


@needs_inputs
def test_stop_ids(fx, bundle):
    prompt = bundle.encode_generation_prefix([{"role": "user", "content": "hello"}])
    assert prompt[-3:] == bundle.artifacts.encode("<|im_start|>assistant\n")[-3:]
    assert prompt.count(SPECIAL["im_start"]["id"]) == 3  # system, user, assistant opener: one atomic id each
    free, fmask, freason = bundle.sample(prompt, 1, 6, 0.0, None, stop_ids=[])
    assert freason == ["length"] and bool(fmask.all())
    comp = free[0, len(prompt):].tolist()
    stop = comp[2]
    j = comp.index(stop)
    seq, cmask, reason = bundle.sample(prompt, 1, 6, 0.0, None, stop_ids=[stop])
    assert reason == [f"stop:{stop}"]
    assert cmask[0, :j + 1].all() and not cmask[0, j + 1:].any()
    assert seq[0, len(prompt):len(prompt) + j + 1].tolist() == comp[:j + 1]
    assert (seq[0, len(prompt) + j + 1:] == SPECIAL["pad"]["id"]).all()
    # decoding keeps marker text and cuts at the configured stop ids
    ids = bundle.artifacts.encode("4") + [SPECIAL["end_of_turn"]["id"]] + bundle.artifacts.encode(" junk")
    assert bundle.decode_completion(ids) == "4<|im_end|>"
    with pytest.raises(Exception):  # render.py refuses marker text inside user content
        bundle.encode_generation_prefix([{"role": "user", "content": "hi <|im_end|>"}])


# --- runtime.py -------------------------------------------------------------------------------------------

def test_runtime_report_and_device_resolution():
    rep = runtime.capability_report()
    assert rep["cpu"]["available"] and "vllm" in rep["g5_samplers"] and "status" in rep["mps"]
    assert runtime.resolve_device("cpu")[0] == "cpu"
    dev, info = runtime.resolve_device("auto")
    assert info["resolved_from_auto"] and dev in ("cpu", "mps", "cuda")
    if not torch.cuda.is_available():
        with pytest.raises(runtime.BackendError, match="cuda requested"):
            runtime.resolve_device("cuda")
    with pytest.raises(runtime.BackendError, match="not available for the G5"):
        runtime.check_options("cpu", "vllm", "eager")
    with pytest.raises(runtime.BackendError, match="triton"):
        runtime.check_options("cpu", "native", "triton")
    with pytest.raises(runtime.BackendError):
        runtime.resolve_device("rocm")


def _yaml(fx, path: Path, **kw) -> Path:
    import yaml  # noqa: PLC0415
    c = cfg_for(fx, **kw)
    c.pop("_base")
    path.write_text(yaml.safe_dump(c))
    return path


@needs_inputs
def test_runtime_modes(fx, tmp_path):
    fixture_cfg = _yaml(fx, tmp_path / "fixture.yaml")
    out = tmp_path / "smoke"
    assert runtime.main(["run", "--mode", "smoke", "--adapter-config", str(fixture_cfg), "--device", "cpu",
                         "--out", str(out)]) == runtime.EXIT_OK
    rec = json.loads((out / "smoke.json").read_text())
    assert rec["status"] == "SMOKE_NOT_A_RESULT" and rec["fixture"] is True and rec["gpu_experiment"] is False
    assert rec["checks"]["trainable_grads_finite"] and not rec["checks"]["router_grad_present"]
    m = ["run", "--mode", "measured", "--adapter-config", str(fixture_cfg), "--out", str(tmp_path / "m")]
    assert runtime.main(m + ["--device", "auto"]) == runtime.EXIT_BAD
    assert runtime.main(m + ["--device", "cpu"]) == runtime.EXIT_BAD  # not the GPU experiment
    assert runtime.main(m + ["--device", "cpu", "--accept-non-gpu"]) == runtime.EXIT_REFUSED  # fixture
    assert runtime.main(m + ["--device", "cpu", "--sampler", "vllm", "--accept-non-gpu"]) == runtime.EXIT_BAD
    waiting = _yaml(fx, tmp_path / "real.yaml", mode="real", fixture_overrides=None, probe=DELETE,
                    checkpoint={"path": str(tmp_path / "g5_small_moe_not_delivered.pt"), "sha256": "0" * 64,
                                "format": "g5_train_week2_pt"})
    wm = ["run", "--adapter-config", str(waiting), "--device", "cpu", "--out", str(tmp_path / "w")]
    assert runtime.main(wm + ["--mode", "smoke"]) == runtime.EXIT_WAITING
    assert runtime.main(wm + ["--mode", "measured", "--accept-non-gpu"]) == runtime.EXIT_WAITING
    assert json.loads((tmp_path / "w" / "measured.json").read_text())["status"] == ta.WAITING


# --- wiring: tasks.py and train.py ------------------------------------------------------------------------

@needs_inputs
def test_reward_env_task_with_g10_codec(fx, bundle):
    import tasks  # noqa: PLC0415
    seen = []
    codec = bundle.codec("1k")
    t = tasks.RewardEnvTask(codec, [("m/1", "2 + 2 = ?"), ("m/2", "3 + 3 = ?")], [("m/3", "4 + 4 = ?")],
                            reward_fn=lambda env_id, text: (seen.append((env_id, text)) or (1.0, {})))
    assert t.train[1] == bundle.encode_generation_prefix([{"role": "user", "content": "3 + 3 = ?"}], effort="1k")
    comp = fx.art.encode("उत्तर 6") + [SPECIAL["end_of_turn"]["id"]] + fx.art.encode(" junk")
    assert t.reward(t.train[1], comp) == 1.0
    assert seen == [("m/2", "उत्तर 6")]  # the terminating stop is consumed by the codec; tokens after it cut
    with pytest.raises(ValueError, match="encodes identically"):  # same prompt in train and heldout
        tasks.RewardEnvTask(codec, [("m/1", "2 + 2 = ?")], [("m/9", "2 + 2 = ?")], reward_fn=lambda e, x: (0.0, {}))
    with pytest.raises(ValueError, match="encodes identically"):  # two env ids, one prompt
        tasks.RewardEnvTask(codec, [("m/1", "q"), ("m/2", "q")], [], reward_fn=lambda e, x: (0.0, {}))


def _train_cfg(adapter_yaml: Path, out: Path, **model_kw) -> dict:
    return {"seed": 7, "device": "cpu", "out_dir": str(out), "verbose": False,
            "model": {"kind": "team5_adapter", "adapter_config": str(adapter_yaml), **model_kw},
            "task": {"kind": "toy", "vocab": 131072, "rule": "parity", "prompt_len": 4, "n_train": 4, "n_heldout": 2},
            "train": {"algo": "grpo", "steps": 2, "prompts_per_step": 2, "k": 2, "max_new": 2, "temperature": 1.0,
                      "lr": 1e-3, "clip_eps": 0.2, "ppo_epochs": 1, "kl_coef": 0.0, "eval_every": 1, "eval_k": 2}}


@needs_inputs
def test_train_waiting_for_g5(fx, tmp_path):
    import train  # noqa: PLC0415
    import yaml  # noqa: PLC0415
    waiting = _yaml(fx, tmp_path / "real.yaml", mode="real", fixture_overrides=None, probe=DELETE,
                    checkpoint={"path": str(tmp_path / "not_delivered.pt"), "sha256": "0" * 64,
                                "format": "g5_train_week2_pt"})
    out = tmp_path / "run"
    cfg_path = tmp_path / "train.yaml"
    cfg_path.write_text(yaml.safe_dump(_train_cfg(waiting, out)))
    assert train.main(["--config", str(cfg_path)]) == 3
    assert json.loads((out / "status.json").read_text())["status"] == ta.WAITING
    assert sorted(p.name for p in out.iterdir()) == ["status.json"]  # no metrics, no summary


@needs_inputs
def test_train_refusals_for_adapter(fx, tmp_path):
    import train  # noqa: PLC0415
    fixture_yaml = _yaml(fx, tmp_path / "fixture.yaml")
    with pytest.raises(ta.ArtifactError, match="FIXTURE"):
        train.train(_train_cfg(fixture_yaml, tmp_path / "a"))
    c = _train_cfg(fixture_yaml, tmp_path / "b", allow_fixture_smoke=True)
    c["train"]["trainable"] = [r"\.moe\."]
    with pytest.raises(ValueError, match="from the adapter config only"):
        train.train(c)
    c = _train_cfg(fixture_yaml, tmp_path / "c", allow_fixture_smoke=True)
    c["train"]["sampler"] = "hf_batch"
    with pytest.raises(ValueError, match="not available for the G5"):
        train.train(c)


@needs_inputs
def test_train_fixture_smoke_is_labelled(fx, tmp_path):
    """Two optimiser steps on the FIXTURE, toy parity task: proves the wiring runs, says nothing about learning."""
    import train  # noqa: PLC0415
    out = tmp_path / "smoke"
    s = train.train(_train_cfg(_yaml(fx, tmp_path / "fixture.yaml"), out, allow_fixture_smoke=True))
    names = sorted(p.name for p in out.iterdir())
    # evals.jsonl is the durable evaluation log added with resumable trainer state (c9f9b39); it carries no result
    # label of its own, so the smoke labels below are what keeps a fixture run from reading as a result.
    assert sorted(set(names) - {"evals.jsonl"}) == ["FIXTURE_SMOKE_NOT_A_RESULT", "smoke_metrics.jsonl",
                                                    "smoke_summary.json"]
    assert "metrics.jsonl" not in names and "summary.json" not in names
    assert s["status"] == "FIXTURE_SMOKE_NOT_A_RESULT" and s["team5_adapter"]["learning_report_allowed"] is False
    assert s["router_unchanged"] and s["router_params_frozen"] == ["blocks.0.moe.router.weight",
                                                                   "blocks.1.moe.router.weight"]
    assert s["team5_adapter"]["router_names"] == s["router_params_frozen"]
    assert all(".attn." in n for n in s["team5_adapter"]["trainable_names"])
    assert s["trainable_params"] == 2 * 4 * 64 * 64 and s["sampler"] == "policy"


# --- reward parsers on marker-bearing text ----------------------------------------------------------------

def _load_by_path(name: str, path: Path):
    import importlib.util  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@needs_inputs
def test_codec_reward_text_through_code_and_patch_parsers(fx, bundle, tmp_path):
    """Real parsers, real token ids. chat_template.jinja writes content + <|im_end|> with no newline."""
    vf = _load_by_path("g10_verifier_t", TEAM10 / "rl" / "verifier.py")
    eot = SPECIAL["end_of_turn"]["id"]
    codec = bundle.codec()
    code_ids = fx.art.encode("Here:\n```python\ndef f(x):\n    return x + 1\n```") + [eot]
    kept = bundle.decode_completion(code_ids, keep_stop=True)
    assert kept.endswith("```<|im_end|>") and vf.extract_code(kept)[1] == "no code block"  # the failure mode
    code, reason = vf.extract_code(codec.decode_completion(code_ids))
    assert reason == "ok" and code == "def f(x):\n    return x + 1\n"
    think = fx.art.encode("<|think|>\n```python\nwrong()\n```\n<|/think|>\n```python\nok()\n```") + [eot]
    assert vf.extract_code(codec.decode_completion(think))[0] == "ok()\n"  # interior markers kept, last block wins
    patch = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2"
    patch_ids = fx.art.encode(patch) + [eot]

    def git_apply(text: str) -> tuple[int, str | None]:
        """(git apply exit, a.py afterwards or None)."""
        d = tmp_path / f"g{len(list(tmp_path.iterdir()))}"
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        (d / "a.py").write_text("x = 1\n")
        (d / "c.patch").write_text(text)
        rc = subprocess.run(["git", "-C", str(d), "apply", "c.patch"], capture_output=True).returncode
        return rc, (d / "a.py").read_text() if rc == 0 else None

    kept = bundle.decode_completion(patch_ids, keep_stop=True)  # "...+x = 2<|im_end|>"
    assert git_apply(kept)[0] != 0  # as decoded: "corrupt patch"
    assert git_apply(kept + "\n") == (0, "x = 2<|im_end|>\n")  # newline added: the marker lands in the source file
    text = codec.decode_completion(patch_ids)
    assert git_apply(text + "\n") == (0, "x = 2\n")


@needs_inputs
def test_codec_reward_text_through_math_check(fx, bundle):
    try:
        import math_verify  # noqa: F401, PLC0415
    except ImportError:
        pytest.skip("math_verify not installed: math_check.score on codec text is UNTESTED in this environment")
    if not (TEAM10 / "rl-data" / "math_check.py").is_file():
        pytest.skip("rl-data/math_check.py not in this checkout: math_check.score on codec text is UNTESTED here")
    mc = _load_by_path("g10_math_check_t", TEAM10 / "rl-data" / "math_check.py")
    eot, eos = SPECIAL["end_of_turn"]["id"], SPECIAL["end_of_sequence"]["id"]
    codec = bundle.codec()

    def score(text: str, ids_tail: list[int], answer: str) -> int:
        return mc.score({"id": "t", "answer": answer}, codec.decode_completion(fx.art.encode(text) + ids_tail))["reward"]

    assert score(r"so \boxed{4}", [eot], "4") == 1
    assert score(r"so \boxed 4", [eos], "4") == 1
    assert score(r"x = \frac{1}{2}", [eot], "0.5") == 1
    assert score(r"so \boxed{4}", [eot] + fx.art.encode(r" \boxed{9}"), "4") == 1  # text after the stop is cut
    t = "<|think|>\nmaybe \\boxed{3}\n<|/think|>\nThe answer is \\boxed{4}"
    assert score(t, [eot], "4") == 1 and score(t, [eot], "3") == 0
    # Known behaviour, not changed here: a length-capped completion that stops inside <|think|> is scored on
    # whatever the thinking contains (the HF path with skip_special_tokens does the same).
    assert score("<|think|>\nI guess \\boxed{3} but", [], "3") == 1


@needs_inputs
def test_train_fixture_reward_reaches_the_trainer(fx, tmp_path, monkeypatch):
    """FIXTURE, 2 optimiser steps. Rewards are computed from codec-decoded text by a test-only reward function
    (1 if the decoded completion's UTF-8 length is even): this proves sampled ids -> codec text -> reward_fn ->
    advantages -> optimiser step on the trainable weights. It says nothing about any real reward or learning."""
    import tasks  # noqa: PLC0415
    import train  # noqa: PLC0415
    calls = []
    train_ids, heldout_ids = ["t/1", "t/2", "t/3"], ["h/1", "h/2"]

    def reward_fn(env_id: str, text: str):
        r = float(len(text.encode("utf-8")) % 2 == 0)
        calls.append((env_id, text, r))
        return r, {}

    def build_task(tcfg, tok, seed):
        assert isinstance(tok, ta.G10Codec)  # train.py hands the adapter's codec to the task
        return tasks.RewardEnvTask(tok, [(i, f"Question {i}: add 2 and 3.") for i in train_ids],
                                   [(i, f"Question {i}: add 4 and 5.") for i in heldout_ids], reward_fn)

    monkeypatch.setattr(train, "build_task", build_task)
    cfg = _train_cfg(_yaml(fx, tmp_path / "fixture.yaml"), tmp_path / "run", allow_fixture_smoke=True)
    cfg["train"].update(k=4, prompts_per_step=2, max_new=3, eval_k=2)
    s = train.train(cfg)
    stop_text = (SPECIAL["end_of_turn"]["token"], SPECIAL["end_of_sequence"]["token"])
    assert calls and all(not text.endswith(stop_text) for _, text, _ in calls)
    tr = [c for c in calls if c[0] in train_ids]
    assert {c[0] for c in calls} <= set(train_ids) | set(heldout_ids) and len(tr) == 2 * 2 * 4
    recs = [json.loads(x) for x in (tmp_path / "run" / "smoke_metrics.jsonl").read_text().splitlines()]
    for step, rec in enumerate(recs):  # the reward the trainer logged is exactly what the reward function returned
        mine = [r for _, _, r in tr[step * 8:(step + 1) * 8]]
        assert rec["train_reward"] == pytest.approx(sum(mine) / len(mine))
    assert max(rec["train_reward"] for rec in recs) > 0
    # GRPO's first-epoch loss is 0 by construction (ratio 1, advantages sum to 0); the gradient is not
    assert s["groups_used_total"] >= 1 and all(rec["grad_norm"] > 0 for rec in recs if rec["groups_used"])
    assert s["trainable_weight_change"]["share_changed"] > 0 and s["router_unchanged"]
    assert s["status"] == "FIXTURE_SMOKE_NOT_A_RESULT"


# --- run_folder mode: a folder written by Team 5's own train_week2.py ------------------------------------------

TINY_ARM = """# G10 test arm: Team 5's exp2_muon -> t2 chain, tiny sizes. NOT a Team 5 arm.
inherit: exp2_muon.yaml
intended:
  arm: g10-test-tiny
  instructor_expert_ffn: 32
  max_time_min: 5
model:
  block_size: 32
  n_layer: 2
  n_head: 2
  n_kv_head: 1
  n_embd: 16
  moe: {num_experts: 4, top_k: 2, num_shared: 1, dispatch: loop}
run:
  batch_size: 2
  dtype: fp32
"""


@fixture(scope="session")
def run_folder(fx, tmp_path_factory):
    """Train 3 CPU steps with Team 5's unmodified train_week2.py (through capstone/g5_launch.py, which only swaps the
    tokenizer-identity default to v0.1) on a tiny arm kept outside Team 5's tree. A real run folder, tiny model."""
    d = tmp_path_factory.mktemp("g5_run_folder")
    ov = d / "overlay"
    (ov / "configs" / "arms").mkdir(parents=True)
    (ov / "experiments").mkdir()
    for rel in ("configs/runtime.yaml", "configs/arms/t2.yaml", "configs/arms/exp2_muon.yaml",
                "experiments/plan_v1.md"):
        (ov / rel).write_bytes((TEAM5 / rel).read_bytes())
    (ov / "configs" / "arms" / "tiny.yaml").write_text(TINY_ARM)
    docs = []
    for i, p in enumerate(sorted(HERE.glob("*.py"))):
        text = p.read_text(encoding="utf-8")
        try:
            fx.art.encode(text)
        except ValueError:
            continue
        docs.append({"id": f"doc{i}", "text": text[:4000]})
    (d / "train.jsonl").write_text("".join(json.dumps(r) + "\n" for r in docs[2:]))
    (d / "heldout.jsonl").write_text("".join(json.dumps(r) + "\n" for r in docs[:2]))
    out = d / "run"
    cmd = [sys.executable, str(TEAM10 / "capstone" / "g5_launch.py"), "--g5-root", str(REPO),
           "--tokenizer-sha256", V0_1_SHA, "--",
           "--config", str(ov / "configs/arms/tiny.yaml"), "--runtime", str(ov / "configs/runtime.yaml"),
           "--tokenizer", str(fx.tok), "--byte-table", str(fx.table), "--train-data", str(d / "train.jsonl"),
           "--heldout-data", str(d / "heldout.jsonl"), "--device", "cpu", "--smoke", "--smoke-steps", "3",
           "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


def rf_cfg(fx, folder: Path, **kw) -> dict:
    c = cfg_for(fx)
    for key in ("fixture_overrides", "checkpoint"):
        c.pop(key)
    c["g5"].pop("arm")
    c["g5"].pop("resolution")
    c["mode"] = "run_folder"
    c["probe"] = {"ids": list(fx.probe_ids)}
    c["run_folder"] = {"path": str(folder), "origin": "g10_rehearsal",
                       "manifest_sha256": ta.sha256_file(folder / "manifest.json"),
                       "checkpoint_sha256": ta.sha256_file(folder / "checkpoint.pt")}
    for path, value in kw.items():
        node, keys = c, path.split("__")
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value
    return c


@needs_inputs
def test_run_folder_builds_rehearsal_bundle(fx, run_folder):
    r = ta.build(rf_cfg(fx, run_folder))
    assert r.status == ta.REHEARSAL_READY and r.mode == "run_folder"
    summary = json.loads((run_folder / "summary.json").read_text())
    assert r.manifest["model_hash_g5"] == summary["final_model_sha256"]
    assert r.manifest["run_folder"]["g5_status"] == "SMOKE_NOT_A_QUALITY_RESULT"
    assert r.manifest["run_folder"]["g10_launch_patches"]["Artifacts.expected_tokenizer_sha"]["used"] == V0_1_SHA
    assert r.manifest["learning_report_allowed"] is False
    spec = json.loads((run_folder / "manifest.json").read_text())["config"]["model"]
    assert r.bundle.spec == spec and spec["n_embd"] == 16
    ids = torch.tensor([fx.probe_ids[:8]])
    assert r.bundle.forward(ids, torch.ones_like(ids, dtype=torch.bool)).shape == (1, 8, 131072)
    with pytest.raises(RuntimeError, match="refusing a learning report"):
        ta.require_learning_ready(r)


@needs_inputs
def test_run_folder_refusals(fx, run_folder, tmp_path):
    import shutil  # noqa: PLC0415
    with pytest.raises(ta.ArtifactError, match="manifest hash mismatch"):
        ta.build(rf_cfg(fx, run_folder, run_folder__manifest_sha256="0" * 64))
    with pytest.raises(ta.ArtifactError, match="checkpoint hash mismatch"):
        ta.build(rf_cfg(fx, run_folder, run_folder__checkpoint_sha256="0" * 64))
    with pytest.raises(ta.ArtifactError, match="non-smoke AGREED_BASELINE_RUN"):
        ta.build(rf_cfg(fx, run_folder, run_folder__origin="g5_delivery"))
    with pytest.raises(ta.ArtifactError, match="origin must be one of"):
        ta.build(rf_cfg(fx, run_folder, run_folder__origin="somebody"))
    c = rf_cfg(fx, run_folder)
    c["checkpoint"] = {"path": "x"}
    with pytest.raises(ta.ArtifactError, match="remove 'checkpoint'"):
        ta.build(c)
    # summary.json says a different final model: the loaded weights are not the ones the run finished with.
    bad = tmp_path / "bad_summary"
    shutil.copytree(run_folder, bad)
    s = json.loads((bad / "summary.json").read_text())
    s["final_model_sha256"] = "f" * 64
    (bad / "summary.json").write_text(json.dumps(s))
    with pytest.raises(ta.ArtifactError, match="final_model_sha256"):
        ta.build(rf_cfg(fx, bad))
    # manifest claims different trainer source than the pinned import.
    src = tmp_path / "bad_source"
    shutil.copytree(run_folder, src)
    m = json.loads((src / "manifest.json").read_text())
    m["sources"]["model.py"] = "0" * 64
    (src / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ta.ArtifactError, match="different model.py"):
        ta.build(rf_cfg(fx, src))
    # checkpoint from another run (identity hash) is refused.
    ident = tmp_path / "bad_identity"
    shutil.copytree(run_folder, ident)
    m = json.loads((ident / "manifest.json").read_text())
    m["identity_sha256"] = "1" * 64
    (ident / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ta.ArtifactError, match="identity_sha256"):
        ta.build(rf_cfg(fx, ident))
    # run_folder keys are not read in the other modes.
    with pytest.raises(ta.ArtifactError, match="only read in run_folder mode"):
        ta.build(cfg_for(fx, run_folder={"path": str(run_folder)}))


# --- CLAUDE.md G10 GRPO review, literally, on Team 5's LanguageModel (real run folder, real trainer) -------------
# Same scripted-reward cases as test_objective_v1_trainer.py (tiny OLMoE), with the policy built by the adapter from a
# folder Team 5's own train_week2.py wrote: real advantage function, real objective_v1 backward, real AdamW.

def _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, name, scripts, k=4, steps=1, ppo_epochs=1, lr=0.01,
               bf16=False, fp32_master=False, **extra):
    import yaml  # noqa: PLC0415
    import train  # noqa: PLC0415
    from test_objective_v1_trainer import _PromptSeeded, _RecAdamW, ScriptedTask  # noqa: PLC0415
    rec = {"logprob_calls": 0, "groups": []}
    real_lp, real_make, real_build, real_bg = (train.chunked_logprobs, train.rollout.make_sampler, train.build_model,
                                               train.backward_objective_v1)

    def lp(pol, seq, plen, micro):
        rec["logprob_calls"] += 1
        return real_lp(pol, seq, plen, micro)

    def bg(pol, group, *a, **kw):
        rec["groups"].append(tuple(group[0][0, :group[5]].tolist()))
        return real_bg(pol, group, *a, **kw)

    def build(mcfg, device):
        pol, tok = real_build(mcfg, device)
        if bf16:
            pol.model.to(torch.bfloat16)
        return pol, tok

    monkeypatch.setattr(train, "chunked_logprobs", lp)
    monkeypatch.setattr(train, "backward_objective_v1", bg)
    monkeypatch.setattr(train, "build_model", build)
    monkeypatch.setattr(train.rollout, "make_sampler", lambda *a, **kw: _PromptSeeded(real_make(*a, **kw)))
    monkeypatch.setattr(train, "build_task", lambda tcfg, tok, seed: ScriptedTask(scripts))
    monkeypatch.setattr(torch.optim, "AdamW", _RecAdamW)
    _RecAdamW.made = []
    c = rf_cfg(fx, run_folder)
    c.pop("_base")
    ypath = tmp_path / f"{name}_adapter.yaml"
    ypath.write_text(yaml.safe_dump(c))
    cfg = {"seed": 1234, "device": "cpu", "out_dir": str(tmp_path / name), "verbose": False,
           "model": {"kind": "team5_adapter", "adapter_config": str(ypath), "allow_fixture_smoke": True},
           "task": {"kind": "scripted"},
           "train": {"algo": "objective_v1", "steps": steps, "prompts_per_step": len(scripts), "k": k, "max_new": 3,
                     "temperature": 1.0, "lr": lr, "ppo_epochs": ppo_epochs, "kl_coef": 0.0, "eval_every": 100,
                     "eval_k": 2, "sampler": "policy", "fp32_master": fp32_master, **extra}}
    summary = train.train(cfg)
    recs = [json.loads(x) for x in (tmp_path / name / "smoke_metrics.jsonl").read_text().splitlines()]
    return summary, _RecAdamW.made[0], recs, rec


@needs_inputs
def test_g5_grpo_review_constant_singleton_mixed_through_the_real_advantage_function():
    import grpo  # noqa: PLC0415
    assert grpo.advantages(torch.tensor([1.0, 1.0, 1.0, 1.0]), "objective_v1") is None  # constant -> dropped
    assert grpo.advantages(torch.tensor([0.0, 0.0, 0.0, 0.0]), "objective_v1") is None
    assert grpo.advantages(torch.tensor([1.0]), "objective_v1") is None  # singleton -> dropped
    a = grpo.advantages(torch.tensor([0.0, 1.0, 0.0, 1.0]), "objective_v1")
    assert torch.isfinite(a).all() and a.tolist() == [-0.5, 0.5, -0.5, 0.5]


@needs_inputs
def test_g5_grpo_review_trainer_mixed_dropped_invariance_and_all_dropped(monkeypatch, tmp_path, fx, run_folder):
    from test_rl_loop import ALL_FAIL, ALL_PASS, MIXED, MIXED_B  # noqa: PLC0415
    # mixed group updates stored weights; constant groups never reach the backward or the denominator
    s, opt, recs, rec = _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "m",
                                   {ALL_PASS: [1, 1, 1, 1], ALL_FAIL: [0, 0, 0, 0], MIXED: [0, 1, 0, 1]})
    r = recs[0]
    assert r["groups_used"] == 1 and r["groups_dropped"] == 2 and rec["groups"] == [MIXED]
    assert r["optimizer_stepped"] and opt.n_steps == 1 and r["tokens"] == 4 * 3 and r["masked_frac"] == 0.0
    assert math.isfinite(r["loss"]) and r["grad_norm"] > 0 and r["stored_update_share"] > 0
    assert s["router_unchanged"] and s["status"] == "FIXTURE_SMOKE_NOT_A_RESULT"
    # adding a dropped group leaves the mixed groups' loss, update and AdamW moments unchanged
    mixed = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    _, o0, r0, _ = _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "d0", dict(mixed), ppo_epochs=2)
    _, o1, r1, rec1 = _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "d1", {**mixed, ALL_PASS: [1, 1, 1, 1]},
                                 ppo_epochs=2)
    assert r1[0]["groups_dropped"] == 1 and ALL_PASS not in rec1["groups"] and r0[0]["tokens"] == r1[0]["tokens"]
    assert r1[0]["loss"] == pytest.approx(r0[0]["loss"], abs=1e-7)
    for p0, p1 in zip(o0.params(), o1.params()):
        assert torch.allclose(p0, p1, atol=1e-7, rtol=0)
        for key in ("exp_avg", "exp_avg_sq"):
            assert torch.allclose(o0.state[p0][key], o1.state[p1][key], atol=1e-9, rtol=1e-5)
    # an all-dropped batch (constant groups, then singletons) never steps the optimizer and creates no state
    _, opt, recs, rec = _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "z",
                                   {ALL_PASS: [1, 1, 1, 1], ALL_FAIL: [0, 0, 0, 0]}, steps=2)
    assert not any(x["optimizer_stepped"] for x in recs) and opt.n_steps == 0 and len(opt.state) == 0
    assert all(torch.equal(p, p0) for p, p0 in zip(opt.params(), opt.start)) and rec["logprob_calls"] == 0
    _, opt, recs, _ = _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "z1", {MIXED: [0, 1, 0, 1]}, k=1)
    assert recs[0]["group_kinds"]["singleton"] == 1 and opt.n_steps == 0 and len(opt.state) == 0


@needs_inputs
def test_g5_stalled_learning_bf16_storage_loses_the_update_fp32_master_keeps_it(monkeypatch, tmp_path, fx,
                                                                               run_folder):
    from test_rl_loop import MIXED  # noqa: PLC0415
    scripts = {MIXED: [0, 1, 0, 1]}
    # bf16-stored G5 weights only run under autocast (KE2 returns fp32 by design): train.autocast bf16. lr 1e-6 is an
    # RL rate; at 1e-9 even fp32 storage cannot hold the step for G5 head rows of magnitude ~0.25 (ulp ~1.5e-8)
    with pytest.raises(RuntimeError, match="lost update"):
        _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "b0", scripts, lr=1e-6, bf16=True, autocast="bf16")
    _, _, recs, _ = _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "b1", scripts, lr=1e-6, bf16=True,
                               autocast="bf16", fail_on_lost_update=False)
    assert recs[0]["grad_nonzero_share"] > 0.5 and recs[0]["stored_update_share"] < 0.01
    s, _, recs, _ = _run_v1_g5(monkeypatch, tmp_path, fx, run_folder, "b2", scripts, lr=1e-6, bf16=True,
                               fp32_master=True)
    assert recs[0]["stored_update_share"] >= 0.5 * recs[0]["grad_nonzero_share"] > 0 and s["fp32_master_params"] > 0


# --- sampling: last-position head and the KV-cached decoder (rl-loop/g5_decode.py) -----------------------------------

@needs_inputs
def test_g5_kv_decoder_matches_team5_forward_and_sampling_paths_agree(fx, run_folder):
    import g5_decode  # noqa: PLC0415
    r = ta.build(rf_cfg(fx, run_folder))
    b = r.bundle
    lm = b.model
    long = list(fx.probe_ids) * 3
    ids = torch.tensor([long[:20], long[1:21]])
    assert g5_decode.parity(lm, ids, split=7) < 1e-4  # prefill 7, then 13 cached one-token steps
    prompt = fx.probe_ids[:6]
    # greedy: re-forward (last-position head), KV cache and Team 5's full forward pick the same tokens
    s0, m0, _ = b.sample(prompt, 2, 8, 0.0, None)
    b.kv_cache = True
    s1, m1, _ = b.sample(prompt, 2, 8, 0.0, None)
    b.kv_cache = False
    assert torch.equal(s0, s1) and torch.equal(m0, m1)
    seq = torch.tensor([prompt])
    for _ in range(8):
        nxt = lm(seq, torch.ones_like(seq, dtype=torch.bool))[:, -1].argmax(-1)
        seq = torch.cat([seq, nxt[:, None]], 1)
    assert torch.equal(seq[0], s0[0, :seq.shape[1]]) or bool(m0[0].logical_not().any())
    # temperature 1 with the same generator seed draws the same completions on both paths (CPU)
    g = torch.Generator().manual_seed(5)
    t0, _, _ = b.sample(prompt, 3, 8, 1.0, g)
    b.kv_cache = True
    g = torch.Generator().manual_seed(5)
    t1, _, _ = b.sample(prompt, 3, 8, 1.0, g)
    b.kv_cache = False
    assert torch.equal(t0, t1)


@needs_inputs
def test_g5_kv_decoder_refuses_layouts_it_does_not_reproduce():
    import g5_decode  # noqa: PLC0415
    import importlib.util as iu  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    spec = iu.spec_from_file_location("g5_model_local_test", TEAM5 / "harness" / "week2" / "model.py")
    g5 = iu.module_from_spec(spec)
    spec.loader.exec_module(g5)
    m = {"vocab_size": 8, "n_embd": 8, "n_head": 2, "n_kv_head": 1, "n_layer": 2, "rope_theta": 1e4, "norm_eps": 1e-5,
         "mtp": False, "attn_pattern": ["G", "L"], "attn_window": 4,
         "moe": {"num_experts": 2, "top_k": 1, "num_shared": 0, "ffn_hidden": 8, "bias": False}}
    rows = np.zeros((8, 2), dtype=np.uint8)
    lm = g5.LanguageModel(m, rows, np.ones(8, dtype=np.int16))
    with pytest.raises(NotImplementedError, match="local window"):
        g5_decode.check_supported(lm)


@needs_inputs
def test_run_folder_without_git_pins_every_harness_file(fx, run_folder, tmp_path):
    """A hash-pinned copy of Team 5's harness outside git (the Kaggle bundle) builds; an unpinned file is refused."""
    import shutil  # noqa: PLC0415
    root = tmp_path / "nogit"
    shutil.copytree(TEAM5 / "harness", root / "teams" / "05-architecture" / "harness",
                    ignore=shutil.ignore_patterns("__pycache__"))
    files = {f"harness/week2/{p.name}": ta.sha256_file(p) for p in (TEAM5 / "harness" / "week2").glob("*.py")}
    files["harness/train_week2.py"] = ta.sha256_file(TEAM5 / "harness" / "train_week2.py")
    c = rf_cfg(fx, run_folder)
    c["g5"] = {"root": str(root), "commit": None, "pin": "file_hashes", "source_commit": fx.head, "files_sha256": files}
    for m in [m for m in list(sys.modules) if m == "train_week2" or m.startswith("week2")]:
        sys.modules.pop(m)  # the pinned-root import check refuses modules imported from the git checkout
    sys.path[:] = [p for p in sys.path if not p.endswith("05-architecture/harness")]
    try:
        r = ta.build(c)
        assert r.status == ta.REHEARSAL_READY and r.manifest["g5"]["commit"] == "nogit:" + fx.head
        bad = dict(files)
        bad.pop("harness/week2/data.py")
        c["g5"]["files_sha256"] = bad
        with pytest.raises(ta.ArtifactError, match="every harness file pinned"):
            ta.build(c)
    finally:
        for m in [m for m in list(sys.modules) if m == "train_week2" or m.startswith("week2")]:
            sys.modules.pop(m)
        sys.path[:] = [p for p in sys.path if "nogit" not in p]


# --- SFT driver (capstone/sft_g5.py) on the real tiny run folder ----------------------------------------------------

@needs_inputs
def test_sft_driver_runs_every_method_with_its_checks(fx, run_folder, tmp_path):
    """Two optimizer steps per method on Team 5's model: masks, writeback, frozen weights and reload must pass."""
    import yaml  # noqa: PLC0415
    capstone = TEAM10 / "capstone"
    sys.path.insert(0, str(capstone))
    import sft_g5  # noqa: PLC0415
    import sft_rows  # noqa: PLC0415
    render = sft_g5.render
    convert = sft_rows._load("g10_convert_for_capstone", TEAM10 / "sft" / "convert.py")
    rt = sft_rows.Retok(fx.tok, fx.table)
    rows = []
    for i in range(12):  # test fixtures only: not training data
        text = render.render([{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": f"a{i} b"}])
        row, why = rt.row({"id": f"t/{i}", "text": text, "train_spans": convert.train_spans(text)})
        assert why == "ok"
        row["split"] = "train" if i < 8 else "eval"
        rows.append(row)
    tr, ev = tmp_path / "train.jsonl", tmp_path / "eval.jsonl"
    tr.write_text("".join(json.dumps(r) + "\n" for r in rows if r["split"] == "train"))
    ev.write_text("".join(json.dumps(r) + "\n" for r in rows if r["split"] == "eval"))
    c = rf_cfg(fx, run_folder)
    c.pop("_base")
    ypath = tmp_path / "adapter.yaml"
    ypath.write_text(yaml.safe_dump(c))
    common = ["--adapter-config", str(ypath), "--train", str(tr), "--eval", str(ev), "--steps", "2", "--batch", "4",
              "--device", "cpu", "--gen-limit", "2", "--gen-max-new", "4", "--drop-over-block", "--dt-calib-rows", "4"]
    for name, extra in {"full": ["--method", "full"], "lora_markers": ["--method", "lora", "--marker-rows"],
                        "dt": ["--method", "dt", "--dt-targets", "g5_mlp"], "markers": ["--method", "markers", "--marker-rows"]}.items():
        rep = sft_g5.run(sft_g5.parse_args(common + extra + ["--out", str(tmp_path / name)]))
        m = rep["mask_checks"]
        assert m["labels_match_mask"] and m["loss_equals_manual_masked_sum"] and m["loss_invariant_to_masked_logits"]
        assert not m["assistant_header_supervised"] and m["im_end_targets_supervised"] > 0
        assert rep["writeback_step1"]["pass"] and rep["reload_parity"]["pass"], name
        if name != "full":
            assert rep["frozen_weights_unchanged"]["pass"], name
        assert rep["after"]["generation"]["prompts"] >= 1 and math.isfinite(rep["last_loss"])
    # DT -> RL hand-over: SFT writes the baked keep masks; the saved state has exact zeros exactly where they say
    import keep_zero  # noqa: PLC0415
    from safetensors.torch import load_file  # noqa: PLC0415
    rep = sft_g5.run(sft_g5.parse_args(common + ["--method", "dt", "--dt-targets", "g5_mlp", "--dt-unseen", "keep",
                                                 "--marker-rows", "--wd", "0", "--out", str(tmp_path / "dt_keep")]))
    assert rep["method"]["wanda_prior"]["unseen_policy"] == "keep"
    masks = keep_zero.load_masks(tmp_path / "dt_keep" / "dt_keep_masks.bin")
    sd = load_file(str(tmp_path / "dt_keep" / "model.safetensors"))
    assert len(masks) == rep["method"]["keep_masks"]["layers"] > 0
    assert sum(int((~m).sum()) for m in masks.values()) == rep["method"]["keep_masks"]["deleted_final"]
    for name, keep in masks.items():
        assert bool(((sd[name] == 0) | keep).all()) and bool((sd[name][~keep] == 0).all())
    kz = keep_zero.KeepZero([(n, torch.nn.Parameter(sd[n].clone())) for n in masks], masks)
    assert kz.deleted_nonzero() == 0


@needs_inputs
def test_mismatch_probe_and_screen_ladder_run(fx, run_folder, tmp_path):
    import yaml  # noqa: PLC0415
    sys.path.insert(0, str(TEAM10 / "capstone"))
    import mismatch_g5  # noqa: PLC0415
    import screen_ladder  # noqa: PLC0415
    c = rf_cfg(fx, run_folder)
    c.pop("_base")
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(c))
    ids = list(fx.probe_ids)[:6]
    (tmp_path / "p.jsonl").write_text(json.dumps({"input_ids": ids + [1], "prompt_len": 6}) + "\n")
    assert mismatch_g5.main(["--adapter-config", str(tmp_path / "a.yaml"), "--prompts", str(tmp_path / "p.jsonl"),
                             "--n", "1", "--k", "2", "--max-new", "3", "--out", str(tmp_path / "m.json")]) == 0
    m = json.loads((tmp_path / "m.json").read_text())
    assert m["pairs"]["fp32_row_repeat_vs_fp32_row"]["outside"] == 0.0  # same forward twice: the determinism floor
    assert m["pairs"]["fp32_batch_vs_fp32_row"]["tokens"] == 2 * 3
    assert len(m["pairs"]["bf16_row_vs_fp32_row"]["expert_set_flips_by_layer"]) == 2
    # screen ladder on synthetic task records and a two-task screen (fixtures, no task text)
    tasks = [{"id": f"t{i}", "statement": "x " * (5 + 40 * i), "judge": "j" + str(i % 2), "difficulty": 0} for i in range(6)]
    (tmp_path / "tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks))
    (tmp_path / "pool.txt").write_text("\n".join(t["id"] for t in tasks))
    (tmp_path / "screen.json").write_text(json.dumps({"k": 4, "per_task": [{"id": "t0", "passes": 2}, {"id": "t5", "passes": 0}]}))
    assert screen_ladder.main(["--tasks", str(tmp_path / "tasks.jsonl"), "--pool", str(tmp_path / "pool.txt"),
                               "--tokenizer", str(fx.tok), "--screen", f"s={tmp_path / 'screen.json'}",
                               "--out", str(tmp_path / "l.json")]) == 0
    s = json.loads((tmp_path / "l.json").read_text())["screens"]["s"]
    assert s["overall"] == {"prompts": 2, "pass_rate": 0.25, "mixed_share": 0.5, "pass_at_k": 0.5, "all_pass_share": 0.0}
    assert s["by_length"]["short"]["mixed_share"] == 1.0 and s["by_length"]["long"]["mixed_share"] == 0.0
