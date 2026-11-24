"""Router bias (#748) and the KAS V2 head (#717) through G10's own code, on Team 5's real classes (job ADP, 24 Nov 2026).

Team 5's MoE chooses experts with topk(scores + router_bias) when model.moe.bias_gamma != 0 and ignores the buffer when it is 0;
loading fills a MISSING router_bias with zeros (#750). So routing depends on a weight, a buffer and a config value, and the two
wrong readers (buffer lost, gamma 0) load without an error. Each test here was shown once to fail on a deliberately broken
variant (work/adp-2026-11-24/broken_variants/). Tiny CPU models, Team 5's t2 arm shrunk; no lab run folder needed.

    python -m pytest capstone/test_router_bias_kas.py -q
"""
from __future__ import annotations

import copy
import json
import sys
import types
from pathlib import Path

import pytest
from pytest import fixture  # bare decorator: pr-guard reads a dotted decorator as an e-mail address

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
HERE = Path(__file__).resolve().parent
TEAMS = HERE.parents[1]
H5 = TEAMS / "05-architecture" / "harness"
sys.path[:0] = [str(HERE), str(TEAMS / "10-post-training" / "rl-loop"), str(H5)]
import keep_weights as kw  # noqa: E402
import sft_g5  # noqa: E402
from sft_g5 import bench  # noqa: E402
from week2 import config as C  # noqa: E402
from week2.model import MoE, LanguageModel  # noqa: E402

import g5_decode  # noqa: E402
import router as g10_router  # noqa: E402
import team5_adapter as ta  # noqa: E402

parametrize = pytest.mark.parametrize
skipif = pytest.mark.skipif
HAS_BIAS = "router_bias" in dict(MoE({"n_embd": 4, "moe": {"ffn_hidden": 4, "top_k": 1, "num_experts": 2, "num_shared": 0,
                                                             "bias": False}}).named_buffers())
HAS_KAS = (H5 / "week2" / "kas_v2.py").is_file()
needs_bias = skipif(not HAS_BIAS, reason="Team 5's harness here predates #748 (no MoE.router_bias)")
needs_kas = skipif(not HAS_KAS, reason="Team 5's harness here predates #717 (no week2/kas_v2.py)")
IDS = torch.randint(0, 256, (2, 16), generator=torch.Generator().manual_seed(5))
VALID = torch.ones_like(IDS, dtype=torch.bool)


def _spec(gamma: float) -> dict:
    m = copy.deepcopy(C.load_runtime(str(TEAMS / "05-architecture" / "configs" / "arms" / "t2.yaml"))["model"])
    m.update(vocab_size=256, block_size=32, n_layer=2, n_head=2, n_kv_head=1, n_embd=64)
    m["moe"] = dict(m["moe"], num_experts=4, top_k=2, num_shared=1, ffn_hidden=32, bias_gamma=gamma)
    return m


ROWS = torch.randint(0, 255, (256, 32), generator=torch.Generator().manual_seed(1)).to(torch.uint8)
LENGTHS = torch.randint(1, 5, (256,), generator=torch.Generator().manual_seed(2))


def _make(gamma: float = 0.001):
    torch.manual_seed(0)
    return LanguageModel(_spec(gamma), ROWS, LENGTHS)


def _routing_bias(model, value: float = 1.0):
    """A bias that changes the chosen set at most positions: +value on expert 0 of every layer, -value on expert 1."""
    with torch.no_grad():
        for n, b in model.named_buffers():
            if n.endswith("router_bias"):
                b.zero_()
                b[0], b[1] = value, -value
    return model


def _logits(model):
    model.eval()
    with torch.no_grad():
        return model(IDS, VALID)


@fixture
def events(tmp_path, monkeypatch):
    monkeypatch.setenv("V5_EVENTS_DIR", str(tmp_path / "ev"))
    torch.use_deterministic_algorithms(True)


# ---------------------------------------------------------------- (a) + (b): keep_weights round trip, strict reload


@needs_bias
def test_a_b_router_bias_survives_keep_weights_and_reload_bit_for_bit_on_a_bias_sensitive_batch(tmp_path, events):
    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file
    model = _routing_bias(_make())
    want = _logits(model).clone()
    zeroed = copy.deepcopy(model)
    for n, b in zeroed.named_buffers():
        if n.endswith("router_bias"):
            b.zero_()
    assert float((_logits(zeroed) - want).abs().max()) > 1e-3  # (b) the batch is one where the bias changes the output
    info = kw.save_run_folder(model, tmp_path / "keep", "g10-bias", step=3, probe_fn=kw.team5_probe)
    out = tmp_path / "m.safetensors"
    export_safetensors(info["run_dir"], _make, kw.team5_probe, str(out), step=3)
    sd = load_file(str(out))
    fresh = _make()
    fresh.load_state_dict(sd, strict=True)
    for n, b in model.named_buffers():
        if n.endswith("router_bias"):
            assert torch.equal(sd[n], b) and torch.equal(dict(fresh.named_buffers())[n], b), n
    assert torch.equal(_logits(fresh), want)
    rec = json.loads((Path(info["run_dir"]) / kw.MODEL_CONFIG_FILE).read_text())
    assert rec["bias_gamma"] == 0.001 and rec["router_bias_absmax"] == 1.0 and info["bias_gamma"] == 0.001
    man = json.loads((tmp_path / "keep" / info["manifest_path"]).read_text())
    assert set(man["frozen"]) == {"embedding.rows", "embedding.lengths"} == set(info["frozen_keys"])


@needs_bias
def test_a_a_checkpoint_without_router_bias_is_refused_by_our_reader_though_team5s_strict_load_takes_it():
    """Team 5's _load_from_state_dict zero-fills a missing router_bias (#750), so load_state_dict(strict=True) passes and the
    model routes differently. team5_adapter._finish compares key sets BEFORE loading; its first check must refuse."""
    model = _routing_bias(_make())
    sd = {k: v for k, v in model.state_dict().items() if not k.endswith("router_bias")}
    lenient = _make()
    lenient.load_state_dict(dict(sd), strict=True)  # the hazard: no error ...
    assert float((_logits(lenient) - _logits(model)).abs().max()) > 1e-3  # ... and different outputs
    with pytest.raises(ta.ArtifactError, match=r"missing \['blocks.0.moe.router_bias', 'blocks.1.moe.router_bias'\]"):
        ta.check_keys(_make(), sd)
    assert ta.check_keys(_make(), model.state_dict()) == set(model.state_dict())
    src = (TEAMS / "10-post-training" / "rl-loop" / "team5_adapter.py").read_text()
    assert src.index("want = check_keys(model, sd)") < src.index("model.load_state_dict(sd, strict=True)")  # before the load


# ---------------------------------------------------------------- (c): DT, LoRA, full FT leave the bias where it was


def _train_steps(model, steps: int = 3):
    gen = torch.Generator().manual_seed(3)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=1e-2, weight_decay=0.0)
    model.train()
    for _ in range(steps):
        ids = torch.randint(0, 256, (2, 16), generator=gen)
        logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
        loss = torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]), ids[:, 1:].reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()


@needs_bias
@parametrize("method", ["full", "lora", "dt"])
def test_c_method_wrappers_and_adamw_leave_router_bias_bit_identical(method, monkeypatch):
    """apply_method's wrappers plus AdamW steps in train mode (this test's own loop). The trainers' report field is
    asserted end to end on a real sft_g5 run in test_c_sft_g5_reports_router_bias_unchanged_per_method."""
    model = _routing_bias(_make(), 0.3)
    args = types.SimpleNamespace(seed=1, lora_r=4, lora_alpha=8.0, dt_targets="g5_mlp", dt_alpha_start=100.0,
                                 dt_alpha_end=1000.0, steps=3, dt_lambda=0.0, dt_eta=0.0)
    sft_g5.apply_method(model, method, args)
    before, frozen = g10_router.router_bias_checksum(model), bench.frozen_sha256(model)
    _train_steps(model)
    assert any(getattr(b.moe, "_balance_load", None) is not None for b in model.blocks)  # train mode counted the load
    g10_router.clear_router_bias_load(model)
    assert all(b.moe._balance_load is None for b in model.blocks)
    assert g10_router.router_bias_checksum(model) == before
    if method != "full":
        assert bench.frozen_sha256(model) == frozen


@needs_bias
def test_c_a_trainer_that_calls_update_router_bias_is_caught_by_the_checksum():
    model = _make()
    before = g10_router.router_bias_checksum(model)
    _train_steps(model, 1)
    model.update_router_bias()  # what Team 5's pretraining loop does once per step and G10 must never do
    assert g10_router.router_bias_checksum(model) != before


# ---------------------------------------------------------------- (d): KV-cached decode inherits the bias


@needs_bias
def test_d_g5_decode_parity_with_a_bias_that_changes_expert_choices():
    model = _routing_bias(_make()).eval()
    g5_decode.check_supported(model)
    assert g5_decode.parity(model, IDS[:1], 6) <= 1e-4
    assert g5_decode.parity_many(model, [IDS[0, :10].tolist(), IDS[1, :7].tolist()], 4) <= 1e-4
    # sample_many through the cache (greedy, temperature 0) equals the argmax path of fresh full forwards
    gen = torch.Generator().manual_seed(0)
    (seq_out, _, _), = g5_decode.sample_many(model, [IDS[0, :6].tolist()], 1, 5, 0.0, gen, stop_ids=[], pad_id=0,
                                             device="cpu")
    seq = IDS[0, :6].tolist()
    for _ in range(5):
        with torch.no_grad():
            nxt = int(model(torch.tensor([seq]), torch.ones(1, len(seq), dtype=torch.bool))[0, -1].argmax())
        seq.append(nxt)
    assert seq_out[0].tolist() == seq


# ---------------------------------------------------------------- (e): frozen_sha256 covers buffers


@needs_bias
def test_e_frozen_sha256_changes_when_only_router_bias_moves():
    model = _make()
    model.requires_grad_(False)
    before = bench.frozen_sha256(model)
    with torch.no_grad():
        model.blocks[0].moe.router_bias[2] += 0.001
    assert bench.frozen_sha256(model) != before


# ---------------------------------------------------------------- (f): parity_many on a head without .weight (KAS V2)


def _kas_model():
    import numpy as np  # noqa: PLC0415
    m = _spec(0.001)
    m.update(vocab_size=131072, ke_max_pos=32, n_embd=32, head_mode="kas_v2")
    ids = np.arange(131072, dtype=np.uint32)
    rows = np.zeros((131072, 32), dtype=np.uint8)
    for col in range(3):
        rows[:, col] = (ids >> (8 * col)) & 255
    torch.manual_seed(0)
    return LanguageModel(m, rows, np.full(131072, 3, dtype=np.int16))


@needs_kas
def test_f_parity_many_and_head_access_on_the_real_kas_head():
    model = _routing_bias(_kas_model()).eval()
    assert not hasattr(model.head, "weight")
    info = ta.head_access(model)
    assert info["kind"] == "kas" and info["per_token_name"] == "head.tok_u" and tuple(info["per_token"].shape) == (131072, 64)
    assert ta.input_access(model, 32)["kind"] == "ke2_code_2048"
    rows = [[130725, 5, 70000, 9, 12], [130725, 300, 4, 8]]
    assert g5_decode.parity_many(model, rows, 2) <= 1e-4


@needs_kas
def test_f_marker_rows_on_the_kas_head_move_only_the_nine_tok_u_rows():
    """enable_head_rows on the real KASHead: after AdamW steps (wd 0) only tok_u[ids] differ; W_out, beta, unigram, tok_c,
    every other tok_u row, and every other tensor of the model are bit-identical."""
    model = _kas_model()
    model.requires_grad_(False)
    ids = [130725, 130822, 7, 99, 1000, 4242, 65000, 100000, 131071]
    w = sft_g5.enable_head_rows(model, ids)
    before = {k: v.clone() for k, v in model.state_dict().items()}
    frozen = bench.frozen_sha256(model, ids)
    opt = torch.optim.AdamW([w], lr=1e-2, weight_decay=0.0)
    model.train()
    for _ in range(3):
        x = torch.tensor([ids[:5] + ids[:3]])
        logits = model(x, torch.ones_like(x, dtype=torch.bool))
        loss = torch.nn.functional.cross_entropy(logits[0, :-1], x[0, 1:])
        opt.zero_grad()
        loss.backward()
        opt.step()
    after = model.state_dict()
    moved = [k for k in before if not torch.equal(before[k], after[k])]
    assert moved == ["head.tok_u"]
    diff = (before["head.tok_u"] != after["head.tok_u"]).any(1).nonzero().flatten().tolist()
    assert set(diff) <= set(ids) and diff
    assert bench.frozen_sha256(model, ids) == frozen


@needs_kas
def test_f_codec_constants_survive_keep_weights_and_are_frozen_keys(tmp_path, events):
    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file
    model = _kas_model().eval()
    g, phi = model.codec.G.clone(), model.codec.Phi.clone()
    info = kw.save_run_folder(model, tmp_path / "keep", "g10-kas", step=1, probe_fn=kw.team5_probe)
    assert info["frozen_keys"] == ["embedding.rows", "embedding.lengths", "codec.G", "codec.Phi"]
    man = json.loads((tmp_path / "keep" / info["manifest_path"]).read_text())
    assert set(man["frozen"]) == set(info["frozen_keys"])
    out = tmp_path / "m.safetensors"
    export_safetensors(info["run_dir"], _kas_model, kw.team5_probe, str(out), step=1)
    sd = load_file(str(out))
    assert sd["codec.G"].dtype == torch.float64 and torch.equal(sd["codec.G"], g) and torch.equal(sd["codec.Phi"], phi)
    assert json.loads((Path(info["run_dir"]) / kw.MODEL_CONFIG_FILE).read_text())["head_mode"] == "kas_v2"


# ---------------------------------------------------------------- (g): a reader built with bias_gamma 0


@needs_bias
@parametrize("reader_class", ["same", "other"])
def test_g_a_gamma0_reader_of_our_folder_is_refused(reader_class, tmp_path, events, monkeypatch):
    """Team 7's export compares probe bits only on the device class that saved them. Same class: the gamma-0 reader's probe
    differs and export raises. Other class (saved on a T4, read on an H100): the check is skipped and the gamma-0 model
    loads silently with other outputs; our G10_MODEL_CONFIG.json check refuses it."""
    import ckpt.ckpt as ck
    from safetensors.torch import load_file
    model = _routing_bias(_make())
    info = kw.save_run_folder(model, tmp_path / "keep", "g10-g", step=2, probe_fn=kw.team5_probe)
    out = tmp_path / "m.safetensors"
    reader = lambda: _make(0.0)  # noqa: E731  Team 9 built with an arm whose gamma is 0
    if reader_class == "same":
        with pytest.raises(ck.RestoreCheckError, match="probe loss bits differ"):
            ck.export_safetensors(info["run_dir"], reader, kw.team5_probe, str(out), step=2)
    else:
        monkeypatch.setattr(ck, "device_class", lambda model=None: "cuda:Other GPU")
        ck.export_safetensors(info["run_dir"], reader, kw.team5_probe, str(out), step=2)  # no error: the hazard
        fresh = reader()
        fresh.load_state_dict(load_file(str(out)), strict=True)
        assert float((_logits(fresh) - _logits(model)).abs().max()) > 1e-3
    with pytest.raises(ValueError, match="bias_gamma"):
        kw.check_reader_config(info["run_dir"], _spec(0.0))
    assert kw.check_reader_config(info["run_dir"], _spec(0.001))["bias_gamma"] == 0.001
    spec_file = tmp_path / "reader.json"
    spec_file.write_text(json.dumps({"model": _spec(0.0)}))
    assert kw.main(["check", "--run-dir", info["run_dir"], "--model-spec", str(spec_file)]) == 1


# ---------------------------------------------------------------- (h): our adapter refuses non-zero bias under gamma 0


@needs_bias
def test_h_router_state_refuses_a_nonzero_bias_with_gamma_0_and_records_it_otherwise():
    bad = _make(0.0)
    with torch.no_grad():
        bad.blocks[1].moe.router_bias[0] = 0.02
    with pytest.raises(ta.ArtifactError, match="bias_gamma is 0"):
        ta.router_state(bad, MoE)
    assert ta.router_state(_make(0.0), MoE)["bias_gamma"] == [0.0]  # zero bias with gamma 0: an old checkpoint, fine
    rec = ta.router_state(_routing_bias(_make(0.001), 0.04), MoE)
    assert rec["bias_gamma"] == [0.001] and rec["router_bias_absmax"] == pytest.approx([0.04, 0.04])
    assert rec["bias_updated_by_g10"] is False
    src = (TEAMS / "10-post-training" / "rl-loop" / "team5_adapter.py").read_text()
    assert src.index("router = router_state(model") < src.index("head = head_access(model)")  # every mode, after load


# ---------------------------------------------------------------- (c) end to end: sft_g5's report, every method, KAS stand-in

import os  # noqa: E402

_WORK = Path(__file__).resolve().parents[6] / "work"
STANDIN_RUN = Path(os.environ.get("G10_STANDIN_RUN_FOLDER", _WORK / "adp-2026-11-24" / "rebuilt"))
STANDIN_ART = Path(os.environ.get("G10_STANDIN_ARTIFACTS", _WORK / "capstone-rehearsal-2026-11-16" / "artifacts"))
TABLE = TEAMS / "04-ke2" / "results" / "tables" / "p1536-s0" / "raw_table_P32.npz"


def _standin_has_bias() -> bool:
    if not ((STANDIN_RUN / "checkpoint.pt").is_file() and (STANDIN_ART / "tokenizer_p1536.json").is_file() and TABLE.is_file()):
        return False
    m = json.loads((STANDIN_RUN / "manifest.json").read_text())["config"]["model"]
    return bool((m.get("moe") or {}).get("bias_gamma"))


@skipif(not (HAS_BIAS and _standin_has_bias()),
                    reason="set G10_STANDIN_RUN_FOLDER to a run folder trained with bias_gamma != 0 (ADP KAS stand-in)")
def test_c_sft_g5_reports_router_bias_unchanged_per_method(tmp_path, events):
    """Two optimizer steps of the real sft_g5.run per method (full, LoRA + marker rows, DT, rows only) on a checkpoint whose
    router_bias is non-zero: each report says router_bias_unchanged.pass, with a non-empty checksum, and logs im_end at its
    target positions before and after (with RMS(h) and sum|z| on the KAS head)."""
    import make_adapter_config as mac
    import sft_rows
    rt = sft_rows.Retok(STANDIN_ART / "tokenizer_p1536.json", TABLE)
    rows = []
    for i in range(10):  # test fixtures only: not training data
        text = sft_g5.render.render([{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": f"a{i} b"}])
        row, why = rt.row({"id": f"t/{i}", "text": text, "train_spans": rt.convert.train_spans(text)})
        assert why == "ok"
        row["split"] = "train" if i < 6 else "eval"
        rows.append(row)
    tr, ev = tmp_path / "train.jsonl", tmp_path / "eval.jsonl"
    tr.write_text("".join(json.dumps(r) + "\n" for r in rows if r["split"] == "train"))
    ev.write_text("".join(json.dumps(r) + "\n" for r in rows if r["split"] == "eval"))
    cfg = mac.write_config(tmp_path / "adapter.yaml", TEAMS.parent, STANDIN_RUN, STANDIN_ART / "tokenizer_p1536.json", TABLE,
                           TEAMS / "10-post-training", "g10_rehearsal", False)
    common = ["--adapter-config", str(cfg), "--train", str(tr), "--eval", str(ev), "--steps", "2", "--batch", "3",
              "--device", "cpu", "--gen-limit", "1", "--gen-max-new", "2", "--dt-calib-rows", "3", "--no-before"]
    for name, extra in {"full": ["--method", "full"], "lora_markers": ["--method", "lora", "--marker-rows", "--wd", "0"],
                        "dt": ["--method", "dt", "--dt-targets", "g5_gate"],
                        "markers": ["--method", "markers", "--marker-rows", "--wd", "0", "--marker-lr", "1e-2"]}.items():
        rep = sft_g5.run(sft_g5.parse_args(common + extra + ["--out", str(tmp_path / name)]))
        rb = rep["router_bias_unchanged"]
        assert rb["pass"] and rb["before"] and rb["before"] == rb["after"], name
        im = rep["im_end_at_targets"]
        assert im["before"]["positions"] > 0 and im["after"]["positions"] == im["before"]["positions"], name
        assert im["before"]["sum_abs_z"] > 0 and im["before"]["rms_h"] > 0, name  # KAS head: z = h @ tok_c.T
        b = im["before"]
        assert b["mid_positions"] > 0 and abs(b["end_minus_mid"] - (b["mean_logprob"] - b["mid_logprob"])) < 1e-9, name
        mb = rep.get("marker_budget")
        assert (mb is None) == ("--marker-rows" not in extra), name
        if mb:  # 2 steps at warmup 10: S = 0.1 + 0.2; far under the 28.3-nat margin, so the flag must be set
            assert mb["steps"] == 2 and abs(mb["S"] - 0.3) < 1e-9 and mb["under_margin"] and mb["flag"], name
        on_disk = json.loads((tmp_path / name / "sft_report.json").read_text())
        assert on_disk["router_bias_unchanged"]["pass"], name



def _unregister_router_bias(model):
    """Job BNP broken input: every MoE keeps its bias as a plain attribute (forward still reads it) but no buffer is named
    `router_bias`, as after a rename in Team 5's code or a module that forgets register_buffer (nothing saves it either)."""
    n = 0
    for mod in model.modules():
        if "router_bias" in mod._buffers:
            t = mod._buffers.pop("router_bias")
            mod.router_bias = t  # not a buffer any more: Module.__setattr__ stores a plain attribute
            n += 1
    return n


@needs_bias
def test_bnp_a_missing_router_bias_buffer_fails_when_the_arm_says_a_bias_exists():
    """None == None must not pass when the arm has MoE experts and bias_gamma > 0. Dense or gamma 0 stays a pass."""
    m = _make(0.001)
    assert _unregister_router_bias(m) == 2
    m.eval()
    with torch.no_grad():
        m(IDS, VALID)  # the model still runs: nothing else would have noticed
    ck = g10_router.router_bias_checksum(m)
    assert ck is None
    rec = g10_router.router_bias_record(m, ck, ck)
    assert rec["expected"] and rec["buffers"] == 0 and rec["pass"] is False and "router_bias" in rec["reason"]
    g0 = _make(0.0)  # gamma 0: the buffer exists but is never read
    ok = g10_router.router_bias_record(g0, g10_router.router_bias_checksum(g0), g10_router.router_bias_checksum(g0))
    assert ok["pass"] and not ok["expected"] and ok["buffers"] == 2
    assert _unregister_router_bias(g0) == 2
    assert g10_router.router_bias_record(g0, None, None)["pass"]  # gamma 0 expects no bias
    dense = {"n_embd": 4}  # no moe block
    assert not g10_router.router_bias_expected(dense) and not g10_router.router_bias_expected(None)
    assert g10_router.router_bias_record(nn_dense(), None, None, dense)["pass"]
    good = _make(0.001)
    rec = g10_router.router_bias_record(good, g10_router.router_bias_checksum(good), g10_router.router_bias_checksum(good))
    assert rec["pass"] and rec["expected"] and rec["buffers"] == 2


def nn_dense():
    return torch.nn.Linear(2, 2)


@skipif(not (HAS_BIAS and _standin_has_bias()),
                    reason="set G10_STANDIN_RUN_FOLDER to a run folder trained with bias_gamma != 0 (ADP KAS stand-in)")
def test_bnp_b_sft_g5_fails_the_bias_check_when_the_buffer_is_not_registered(tmp_path, events, monkeypatch):
    """End to end on the KAS stand-in (bias_gamma 0.001): the same run with the router_bias buffers unregistered after the
    build reports pass False with the reason, on disk too, so the job chain's arm check fails that arm."""
    import make_adapter_config as mac
    import sft_rows
    rt = sft_rows.Retok(STANDIN_ART / "tokenizer_p1536.json", TABLE)
    rows = []
    for i in range(8):  # test fixtures only: not training data
        text = sft_g5.render.render([{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": f"a{i} b"}])
        row, why = rt.row({"id": f"t/{i}", "text": text, "train_spans": rt.convert.train_spans(text)})
        assert why == "ok"
        row["split"] = "train" if i < 5 else "eval"
        rows.append(row)
    tr, ev = tmp_path / "train.jsonl", tmp_path / "eval.jsonl"
    tr.write_text("".join(json.dumps(r) + "\n" for r in rows[:5]))
    ev.write_text("".join(json.dumps(r) + "\n" for r in rows[5:]))
    cfg = mac.write_config(tmp_path / "adapter.yaml", TEAMS.parent, STANDIN_RUN, STANDIN_ART / "tokenizer_p1536.json", TABLE,
                           TEAMS / "10-post-training", "g10_rehearsal", False)
    real = ta.build

    def build(*a, **k):
        res = real(*a, **k)
        assert _unregister_router_bias(res.require_bundle().model) > 0
        return res

    monkeypatch.setattr(ta, "build", build)
    rep = sft_g5.run(sft_g5.parse_args(["--adapter-config", str(cfg), "--train", str(tr), "--eval", str(ev), "--steps", "1",
                                        "--batch", "2", "--device", "cpu", "--gen-limit", "1", "--gen-max-new", "2",
                                        "--no-before", "--method", "full", "--out", str(tmp_path / "full")]))
    rb = rep["router_bias_unchanged"]
    assert rb["pass"] is False and rb["expected"] and rb["buffers"] == 0 and rb["before"] is None and rb["reason"]
    on_disk = json.loads((tmp_path / "full" / "sft_report.json").read_text())["router_bias_unchanged"]
    assert on_disk["pass"] is False

def test_marker_budget_reproduces_the_preregistered_rule():
    """A1 numbers: 1e-2 x S x 59.0 x 0.682 against 1.3 x 21.79 = 28.33. 243 scheduled steps (S 134.1) pass with margin; the
    compressed 126-step schedule (S 69.8) is under it."""
    import math
    def mult(n):
        return [(s + 1) / 10 if s < 10 else 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * (s - 10) / (n - 10))) for s in range(n)]
    st = {"sum_abs_z": 59.0, "sum_abs_mean_z": 59.0 * 0.682}
    full = sft_g5.marker_budget(1e-2, mult(243), st)
    assert abs(full["S"] - 134.1) < 0.05 and abs(full["budget_nats"] - 53.96) < 0.05 and not full["under_margin"]
    short = sft_g5.marker_budget(1e-2, mult(126), st)
    assert short["under_margin"] and short["flag"] == "marker budget under the preregistered margin"
    assert sft_g5.marker_budget(1e-2, mult(10), {"rms_h": 1.0}) is None  # dense head: no z, no budget
