"""Tests for the WP3 bench (slice, retok, train, evaluate, exec_tasks).

Fixture text below is code-generated test input, never training data. Tests that need the pinned SmolLM2 tokenizer
use G10_BENCH_TOKENIZER (path to tokenizer.json) or the local Hugging Face cache, and skip if neither exists.
Real-data checks run when G10_BENCH_SLICE names a built slice folder (private, outside Git).

    python -m pytest teams/10-post-training/sft/bench/tests -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import pytest

# Avoid dotted-decorator false positives in the lab's older PR email guard.
_skip_if = pytest.mark.skipif
_fixture = pytest.fixture
import torch

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


retok = _load("g10_bench_retok", BENCH / "retok.py")
train = _load("g10_bench_train", BENCH / "train.py")
evaluate = _load("g10_bench_evaluate", BENCH / "evaluate.py")
slicer = _load("g10_bench_slice", BENCH / "slice.py")
exec_tasks = _load("g10_bench_exec_tasks", BENCH / "exec_tasks.py")
convert, render, probe = retok.convert, retok.render, train.probe
T = render.T

_CACHE = Path.home() / ".cache/huggingface/hub/models--HuggingFaceTB--SmolLM2-135M/snapshots" / retok.SURROGATE["revision"] / "tokenizer.json"
TOK_PATH = Path(os.environ.get("G10_BENCH_TOKENIZER", _CACHE))
needs_tok = pytest.mark.skipif(not TOK_PATH.is_file(), reason="SmolLM2 tokenizer not available")
SLICE = os.environ.get("G10_BENCH_SLICE")


def tok():
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(TOK_PATH))


def fixture_row(i: int, effort="1k", think=True) -> dict:
    msgs = [{"role": "user", "content": f"Problem {i}: read n and print n*{i}.\n"},
            {"role": "assistant", "content": f"```python\nn = int(input())\nprint(n * {i})\n```",
             **({"think": f"multiply by {i}"} if think else {})}]
    text = render.render(msgs, effort)
    return {"id": f"fx/{i}", "text": text, "train_spans": [list(s) for s in convert.train_spans(text)]}


# ---------------------------------------------------------------- retok


@needs_tok
def test_marker_ids_match_tokenizer():
    retok.check_tokenizer(tok())
    t = tok()
    for name, (surf, sid) in retok.MARKER_MAP.items():
        assert t.encode(surf, add_special_tokens=False).ids == [sid]
    assert [retok.MARKER_MAP[k][1] for k in ("endoftext", "im_start", "im_end")] == [0, 1, 2]


@needs_tok
def test_retok_mask_matches_convert_and_boundaries():
    t = tok()
    rows = [fixture_row(i, think=i % 2 == 0) for i in range(6)]
    out, rej = retok.retokenize(rows, t)
    assert rej == {} and len(out) == 6
    for src, r in zip(rows, out):
        surr, moves = retok.to_surrogate(src["text"])
        assert surr == r["surrogate_text"]
        spans = convert.train_spans(surr)
        enc = t.encode(surr, add_special_tokens=False)
        assert r["input_ids"] == enc.ids
        assert r["loss_mask"] == convert.token_mask(spans, enc.offsets)  # same function, same spans
        ids, mask = r["input_ids"], r["loss_mask"]
        im_end_targets = [m for i, m in zip(ids, mask) if i == retok.IM_END_ID]
        assert im_end_targets[-1] == 1 and sum(im_end_targets) == len(spans)  # assistant <|im_end|> trained, others not
        assert ids[-1] == retok.EOS_ID and mask[-1] == 0  # final <|endoftext|> never a target
        assert ids[0] == 1 and mask[0] == 0
        assert all(mask[i] == 0 for i in range(r["prompt_len"]))  # nothing in the prompt is trained
        # every trained token lies inside an assistant span
        for (a, b), m in zip(enc.offsets, mask):
            if m:
                assert any(s <= a and b <= e for s, e in spans)
        # target bytes = G10-surface bytes of the assistant spans (no token straddles a span edge in the fixture)
        g10_bytes = sum(len(src["text"][s:e].encode()) for s, e in src["train_spans"])
        assert r["target_bytes"] == g10_bytes
        assert retok.from_surrogate(surr) == src["text"]


@needs_tok
def test_target_bytes_count_each_byte_once_with_byte_fallback():
    """Regression (14 Nov): emoji/CJK fall back to byte tokens that share one character's offsets; bytes count once."""
    t = tok()
    bodies = ["\U0001F600", "x \U0001F600\U0001F680 y", "na\u00efve \u0939\u093f\u0928\u094d\u0926\u0940 \u6f22\u5b57"]
    rows = []
    for i, body in enumerate(bodies):
        text = render.render([{"role": "user", "content": "q"}, {"role": "assistant", "content": body}], "1k")
        rows.append({"id": f"u/{i}", "text": text, "train_spans": [list(s) for s in convert.train_spans(text)]})
    out, rej = retok.retokenize(rows, t)
    assert rej == {} and len(out) == 3
    enc = t.encode(retok.to_surrogate(rows[0]["text"])[0], add_special_tokens=False)
    assert len(enc.offsets) != len(set(enc.offsets))  # the fixture really has overlapping offsets
    for src, r in zip(rows, out):
        true = sum(len(src["text"][a:b].encode("utf-8")) for a, b in src["train_spans"])
        assert r["target_bytes"] == true == retok.target_bytes_of(r["surrogate_text"])
        assert r["loss_mask"] == convert.token_mask(convert.train_spans(r["surrogate_text"]), enc.offsets if src is rows[0] else
                                                    t.encode(r["surrogate_text"], add_special_tokens=False).offsets)


@needs_tok
def test_retok_rejects_ambiguous_rows():
    t = tok()
    bad = fixture_row(1)
    bad["text"] = bad["text"].replace("multiply", "<filename> multiply")
    bad["train_spans"] = [list(s) for s in convert.train_spans(bad["text"])]
    tool = render.render([{"role": "user", "content": "q"},
                          {"role": "assistant", "content": "", "tool_calls": [{"name": "f", "arguments": {}}]},
                          {"role": "tool", "content": "r"}, {"role": "assistant", "content": "done"}], "1k")
    trow = {"id": "fx/tool", "text": tool, "train_spans": [list(s) for s in convert.train_spans(tool)]}
    wrong = fixture_row(2)
    wrong["train_spans"] = [[0, 5]]
    out, rej = retok.retokenize([bad, trow, wrong], t)
    assert out == [] and rej == {"surrogate_special_in_content": 1, "unmapped_marker": 1, "pack_spans_differ_from_convert": 1}


@_skip_if(not SLICE, reason="G10_BENCH_SLICE not set")
@needs_tok
def test_real_rows_mask_parity_50():
    """50 real train rows: re-running retok reproduces the slice's tokens and masks; masks respect the spans."""
    t = tok()
    src = [json.loads(l) for _, l in zip(range(50), open(Path(SLICE) / "train.jsonl", encoding="utf-8"))]
    tokd = {json.loads(l)["id"]: json.loads(l) for l in open(Path(SLICE) / "train.tok.jsonl", encoding="utf-8")}
    out, rej = retok.retokenize(src, t)
    assert rej == {} and len(out) == 50
    for r in out:
        ref = tokd[r["id"]]
        assert r["input_ids"] == ref["input_ids"] and r["loss_mask"] == ref["loss_mask"]
        spans = convert.train_spans(r["surrogate_text"])
        ims = [m for i, m in zip(r["input_ids"], r["loss_mask"]) if i == retok.IM_END_ID]
        assert sum(ims) == len(spans) and r["loss_mask"][-1] == 0


@_skip_if(not SLICE, reason="G10_BENCH_SLICE not set")
def test_real_slice_zero_overlap():
    m = json.loads((Path(SLICE) / "manifest.json").read_text())
    assert m["zero_overlap"] is True
    ids = {s: set(m["ids"][s]) for s in ("train", "dev", "test")}
    assert not (ids["train"] & ids["dev"]) and not (ids["train"] & ids["test"]) and not (ids["dev"] & ids["test"])
    clusters = {}
    for s in ("train", "dev", "test"):
        clusters[s] = {json.loads(l)["cluster"] for l in open(Path(SLICE) / f"{s}.tok.jsonl", encoding="utf-8")}
    assert not (clusters["train"] & clusters["test"]) and not (clusters["train"] & clusters["dev"]) and not (clusters["dev"] & clusters["test"])


# ---------------------------------------------------------------- slice


@needs_tok
def test_slice_splits_by_cluster_and_guards_heldout(tmp_path):
    shard = tmp_path / "shard-00000"
    (shard / "pack").mkdir(parents=True)
    (shard / "join").mkdir()
    pack, side, fam_cluster = [], [], {}
    for i in range(60):
        r = fixture_row(i)
        fam = f"sha256:{i // 3:064x}"  # 3 completions per problem
        cl = f"c:{(i // 6):064x}"  # 2 problems per near-duplicate cluster
        fam_cluster[fam] = cl
        rid = f"set/{i}"
        pack.append({"id": rid, "set": "set", "source_id": f"ocr{i}", "effort": "1k", "text": r["text"],
                     "train_spans": r["train_spans"], "input_ids": [1] * 10, "loss_mask": [0] * 10})
        side.append({"rendered_id": rid, "ocr_id": f"ocr{i}", "ocr_question_id": f"q{i // 3}", "problem_family_key": fam,
                     "source_row_key": ["repo", "rev", "taco", "train", str(i)], "source_file": "f", "source_local_ordinal": str(i),
                     "question_sha256": f"{i // 3:064x}"})
    (shard / "pack" / "pack.jsonl").write_text("".join(json.dumps(r) + "\n" for r in pack))
    (shard / "join" / "joined.sidecar.jsonl").write_text("".join(json.dumps(r) + "\n" for r in side))
    held_family = "sha256:" + "f" * 64  # a WP1 held-out family that sits in cluster 0
    fam_cluster[held_family] = f"c:{0:064x}"
    (tmp_path / "cl.json").write_text(json.dumps({"family_to_cluster": fam_cluster, "threshold": 0.8}))
    (tmp_path / "held.jsonl").write_text(json.dumps({"problem_family_key": held_family}) + "\n")
    m = slicer.build([shard], tmp_path / "cl.json", tmp_path / "held.jsonl", TOK_PATH, tmp_path / "out", 2048,
                     (0.6, 0.2, 0.2), "salt", {"train": None, "dev": None, "test": None})
    assert m["zero_overlap"] and m["counts"]["dropped_cluster_touches_heldout"] == 6
    seen = {}
    for s in ("train", "dev", "test"):
        for line in open(tmp_path / "out" / f"{s}.tok.jsonl"):
            r = json.loads(line)
            assert r["split"] == s
            assert seen.setdefault(r["cluster"], s) == s
    # a pack row whose family is itself held out is a hard error
    (tmp_path / "held2.jsonl").write_text(json.dumps({"problem_family_key": side[7]["problem_family_key"]}) + "\n")
    with pytest.raises(SystemExit):
        slicer.build([shard], tmp_path / "cl.json", tmp_path / "held2.jsonl", TOK_PATH, tmp_path / "out2", 2048,
                     (0.6, 0.2, 0.2), "salt", {"train": None, "dev": None, "test": None})


def test_assign_split_is_deterministic_and_cluster_level():
    a = [slicer.assign_split(f"c{i}", "s", (0.7, 0.1, 0.2)) for i in range(2000)]
    assert a == [slicer.assign_split(f"c{i}", "s", (0.7, 0.1, 0.2)) for i in range(2000)]
    frac = {s: a.count(s) / len(a) for s in ("train", "dev", "test")}
    assert abs(frac["train"] - 0.7) < 0.04 and abs(frac["test"] - 0.2) < 0.04


# ---------------------------------------------------------------- firewall


def test_train_never_imports_evaluate_or_reads_heldout():
    src = (BENCH / "train.py").read_text()
    code = re.sub(r'""".*?"""', "", src, flags=re.S)
    assert "import evaluate" not in code and "evaluate.py\"" not in code and "evaluate\"" not in code
    assert "heldout" not in code.lower() and "exec_tasks" not in code


def test_split_guards(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps({"id": "a", "split": "test", "input_ids": [1, 2, 3], "loss_mask": [0, 1, 1]}) + "\n")
    with pytest.raises(SystemExit):
        train.load_train_rows(p, 2048)
    q = tmp_path / "y.jsonl"
    q.write_text(json.dumps({"id": "a", "split": "train", "input_ids": [1, 2, 3], "loss_mask": [0, 1, 1]}) + "\n")
    with pytest.raises(SystemExit):
        evaluate.load_eval_rows(q)
    with pytest.raises(SystemExit):
        exec_tasks.build(q, tmp_path)


# ---------------------------------------------------------------- loss contract


class _Wrap(torch.nn.Module):
    """Expose train_probe.TinyCausalLM through the .model(...).last_hidden_state / .lm_head interface."""

    def __init__(self, tiny):
        super().__init__()
        self.tiny, self.lm_head = tiny, tiny.head

    class _Out:
        def __init__(self, h):
            self.last_hidden_state = h

    def model(self, input_ids, attention_mask=None):
        t = self.tiny
        T_ = input_ids.size(1)
        x = t.tok(input_ids) + t.pos(torch.arange(T_))[None]
        causal = torch.nn.Transformer.generate_square_subsequent_mask(T_)
        return self._Out(t.norm(t.blocks(x, mask=causal, is_causal=True)))


def _probe_cfg():
    return probe.check_config({"seed": 3, "vocab_size": 50, "d_model": 16, "n_heads": 2, "n_layers": 1, "max_len": 64,
                               "pad_id": 0, "eos_id": 1, "lr": 1e-3, "weight_decay": 0.0, "betas": [0.9, 0.95],
                               "warmup_steps": 1, "max_steps": 3, "grad_clip": 1.0, "microbatch_size": 2,
                               "fixture_rows": 7, "overfit_ratio": 0.9})


def test_collate_equals_train_probe():
    cfg = _probe_cfg()
    rows = probe.synthetic_rows(cfg)
    a, b = probe.collate(rows, cfg["pad_id"], cfg["eos_id"]), train.collate(rows, cfg["pad_id"])
    assert torch.equal(a.input_ids, b.input_ids) and torch.equal(a.attention_mask, b.attention_mask)
    assert torch.equal(a.labels, b.labels) and a.n_targets == b.n_targets


def test_loss_and_gradient_equal_train_probe():
    cfg = _probe_cfg()
    rows = probe.synthetic_rows(cfg)
    torch.manual_seed(0)
    tiny = probe.build_model(cfg).eval()
    wrap = _Wrap(tiny)
    mbs_probe = probe.microbatches(rows, 2, cfg["pad_id"], cfg["eos_id"])
    tiny.zero_grad()
    lp, cp = probe.accumulate_gradients(tiny, mbs_probe)
    gp = [p.grad.clone() for p in tiny.parameters()]
    tiny.zero_grad()
    mbs = [train.collate(g, 0) for g in train.plan_microbatches(rows, 40)]  # different grouping, same global mean
    lb, cb = train.accumulate(wrap, mbs, "cpu")
    gb = [p.grad.clone() for p in tiny.parameters()]
    assert cp == cb and abs(lp - lb) < 1e-5
    assert all(torch.allclose(x, y, atol=1e-6, rtol=1e-4) for x, y in zip(gp, gb))


def test_zero_target_rows_rejected(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text(json.dumps({"id": "a", "split": "train", "input_ids": [1, 2, 3], "loss_mask": [1, 0, 0]}) + "\n"
                 + json.dumps({"id": "b", "split": "train", "input_ids": [1, 2, 3], "loss_mask": [0, 1, 1]}) + "\n")
    rows, rej = train.load_train_rows(p, 2048)
    assert [r["id"] for r in rows] == ["b"] and rej == {"zero_targets": 1}


def test_writeback_check_detects_real_and_lost_updates():
    torch.manual_seed(0)
    w = torch.nn.Parameter(torch.cat([torch.randn(500) * 0.05, torch.randn(500) * 1e-6]))
    w.grad = torch.randn(1000)
    p0, g = w.detach().clone(), w.grad.clone()
    opt = torch.optim.AdamW([w], lr=1e-6, betas=(0.9, 0.95), eps=1e-8, weight_decay=0.0)
    opt.step()
    ok = train.writeback_check(p0, g, w.detach().clone(), 1e-6, 0.0, 1e-8)
    assert ok["pass"] and ok["fraction_moved_fp32_storage"] > 0.99
    assert ok["fraction_would_move_bf16_storage"] < 0.6  # BF16 storage would drop most updates of the large weights
    lost = train.writeback_check(p0, g, p0.clone(), 1e-6, 0.0, 1e-8)
    assert not lost["pass"]


# ---------------------------------------------------------------- end to end on a tiny random Llama (CPU)


@_fixture(scope="module")
def tiny_setup(tmp_path_factory):
    from transformers import LlamaConfig, LlamaForCausalLM

    d = tmp_path_factory.mktemp("tiny")
    cfg = LlamaConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                      num_key_value_heads=2, max_position_embeddings=128, tie_word_embeddings=True, bos_token_id=0,
                      eos_token_id=0)
    torch.manual_seed(0)
    LlamaForCausalLM(cfg).save_pretrained(d / "base")
    rows = probe.synthetic_rows({**_probe_cfg(), "vocab_size": 64, "fixture_rows": 24})
    (d / "train.tok.jsonl").write_text("".join(json.dumps({"id": f"r{i}", "split": "train", **r}) + "\n" for i, r in enumerate(rows)))
    (d / "tokdir").mkdir()
    return d


def _run(d, out, method="full", seed=5, steps=6):
    args = train.parse_args(["--train", str(d / "train.tok.jsonl"), "--model", str(d / "base"), "--revision", "main",
                             "--tokenizer-dir", str(d / "tokdir"), "--method", method, "--steps", str(steps),
                             "--warmup", "2", "--lr", "1e-3", "--seed", str(seed), "--device", "cpu", "--micro-tokens",
                             "64", "--out", str(d / out), "--log-every", "100"])
    args.revision = None
    return train.train(args)


def test_full_run_checks_and_determinism(tiny_setup):
    a, b = _run(tiny_setup, "a"), _run(tiny_setup, "b")
    assert [r["loss"] for r in a["log"]] == [r["loss"] for r in b["log"]]  # two seeded CPU runs: identical
    assert a["saved_state_sha256"] == b["saved_state_sha256"]
    assert a["checks"]["writeback_step1"]["pass"] and a["checks"]["reload_parity"]["pass"]
    assert a["checks"]["reload_parity"]["logits_max_abs_diff"] == 0.0
    c = _run(tiny_setup, "c", seed=6)
    assert [r["loss"] for r in c["log"]] != [r["loss"] for r in a["log"]]


def test_lora_run_trains_adapters_only(tiny_setup):
    from safetensors.torch import load_file

    rep = _run(tiny_setup, "lora", method="lora")
    assert rep["method"]["wrapped_modules"] == 14 and rep["checks"]["reload_parity"]["pass"]
    assert rep["checks"]["writeback_step1"]["pass"]
    base = load_file(str(tiny_setup / "base" / "model.safetensors"))
    merged = load_file(str(tiny_setup / "lora" / "model" / "model.safetensors"))
    assert torch.equal(base["model.embed_tokens.weight"], merged["model.embed_tokens.weight"])  # not a LoRA target
    assert not torch.equal(base["model.layers.0.self_attn.q_proj.weight"], merged["model.layers.0.self_attn.q_proj.weight"])


def _run_extra(d, out, extra, method="dt", seed=5, steps=6):
    args = train.parse_args(["--train", str(d / "train.tok.jsonl"), "--model", str(d / "base"), "--revision", "main",
                             "--tokenizer-dir", str(d / "tokdir"), "--method", method, "--steps", str(steps),
                             "--warmup", "2", "--lr", "1e-2", "--seed", str(seed), "--device", "cpu", "--micro-tokens",
                             "64", "--out", str(d / out), "--log-every", "100", *extra])
    args.revision = None
    return train.train(args)


def test_dt_run_trains_logits_only_and_saves_the_hard_mask(tiny_setup):
    from safetensors.torch import load_file

    rep = _run_extra(tiny_setup, "dt", ["--dt-targets", "mlp", "--dt-eta", "0.01", "--dt-calib-rows", "8"])
    c = rep["checks"]
    assert c["writeback_step1"]["pass"] and c["writeback_step1"]["tensor"].endswith(".gate")
    assert c["frozen_weights_unchanged"]["pass"]
    assert c["bake_parity"]["pass"] and c["reload_parity"]["pass"] and c["reload_parity"]["logits_max_abs_diff"] == 0.0
    m = rep["method"]
    assert m["masked_layers"] == 6 and m["trainable"] == 2 * (3 * 64 * 32)
    assert m["deletion_at_init"]["deleted"] > 0 and 0 < m["deletion_final"]["deleted_frac_of_targeted"] < 1
    assert m["alpha_final"] == 1000.0
    assert all("reg" in r for r in rep["log"])
    base = load_file(str(tiny_setup / "base" / "model.safetensors"))
    saved = load_file(str(tiny_setup / "dt" / "model" / "model.safetensors"))
    for k, v in base.items():  # every saved weight is the base weight or exactly zero where the hard mask deletes
        assert ((saved[k] == v) | (saved[k] == 0)).all(), k
        if "mlp" not in k:
            assert torch.equal(saved[k], v), k
    zeros = sum(int(((saved[k] == 0) & (v != 0)).sum()) for k, v in base.items())
    assert zeros == m["deletion_final"]["deleted"]
    assert (tiny_setup / "dt" / "dt_mask.bin").stat().st_size == m["mask_artifact"]["compressed_bytes"]
    a, b = rep, _run_extra(tiny_setup, "dt2", ["--dt-targets", "mlp", "--dt-eta", "0.01", "--dt-calib-rows", "8"])
    assert a["saved_state_sha256"] == b["saved_state_sha256"]  # deterministic on CPU


def test_marker_hybrid_moves_only_marker_rows(tiny_setup):
    from safetensors.torch import load_file

    for method in ("dt", "lora"):
        rep = _run_extra(tiny_setup, f"{method}-m", ["--train-marker-rows", "--marker-lr", "1e-2"], method=method)
        assert rep["method"]["hybrid"]["label"] == f"{method}+markers"
        assert rep["checks"]["frozen_weights_unchanged"]["pass"]
        ids = rep["method"]["hybrid"]["marker_row_ids"]
        assert ids == [0, 1, 2, 15, 16]
        base = load_file(str(tiny_setup / "base" / "model.safetensors"))["model.embed_tokens.weight"]
        new = load_file(str(tiny_setup / f"{method}-m" / "model" / "model.safetensors"))["model.embed_tokens.weight"]
        moved = [i for i in range(base.shape[0]) if not torch.equal(base[i], new[i])]
        assert moved and set(moved) <= set(ids), (method, moved)
    with pytest.raises(SystemExit):
        _run_extra(tiny_setup, "full-m", ["--train-marker-rows"], method="full")
    with pytest.raises(SystemExit):
        _run_extra(tiny_setup, "dt-m-wd", ["--train-marker-rows", "--wd", "0.01"], method="dt")


def test_markers_only_control_trains_nothing_but_marker_rows(tiny_setup):
    from safetensors.torch import load_file

    rep = _run_extra(tiny_setup, "mk", ["--train-marker-rows", "--marker-lr", "1e-2", "--lr", "1e-2"], method="markers")
    assert rep["method"]["method"] == "markers" and rep["method"]["hybrid"]["label"] == "markers+markers"
    c = rep["checks"]
    assert c["frozen_weights_unchanged"]["pass"] and c["reload_parity"]["pass"]
    assert c["writeback_step1"]["pass"] and c["writeback_step1"]["lr"] > 0
    base = load_file(str(tiny_setup / "base" / "model.safetensors"))
    new = load_file(str(tiny_setup / "mk" / "model" / "model.safetensors"))
    for k, v in base.items():
        if k == "model.embed_tokens.weight":
            moved = [i for i in range(v.shape[0]) if not torch.equal(v[i], new[k][i])]
            assert moved and set(moved) <= {0, 1, 2, 15, 16}, moved
        else:
            assert torch.equal(v, new[k]), k
    with pytest.raises(SystemExit):
        _run_extra(tiny_setup, "mk-none", [], method="markers")


def test_untied_head_marker_scope_moves_only_the_chosen_side(tiny_setup):
    from safetensors.torch import load_file

    base = load_file(str(tiny_setup / "base" / "model.safetensors"))["model.embed_tokens.weight"]
    for scope, moved_emb, moved_head in (("input", True, False), ("output", False, True), ("both", True, True)):
        rep = _run_extra(tiny_setup, f"untied-{scope}", ["--train-marker-rows", "--marker-lr", "1e-2", "--untie-head",
                                                         "--marker-scope", scope])
        assert rep["method"]["untied_head"] and rep["method"]["hybrid"]["scope"] == scope
        assert rep["checks"]["frozen_weights_unchanged"]["pass"] and rep["checks"]["reload_parity"]["pass"]
        saved = load_file(str(tiny_setup / f"untied-{scope}" / "model" / "model.safetensors"))
        assert "lm_head.weight" in saved  # the head is its own tensor on disk
        for name, expect in (("model.embed_tokens.weight", moved_emb), ("lm_head.weight", moved_head)):
            rows = [i for i in range(base.shape[0]) if not torch.equal(base[i], saved[name][i])]
            assert set(rows) <= {0, 1, 2, 15, 16}, (scope, name, rows)
            assert bool(rows) == expect, (scope, name, rows)
    with pytest.raises(SystemExit):
        _run_extra(tiny_setup, "tied-output", ["--train-marker-rows", "--marker-scope", "output"])


def test_markers_only_with_untied_output_scope_watches_the_head(tiny_setup):
    # Regression (port review, 15 Nov): the markers control watched the input embedding, which is frozen under
    # --untie-head --marker-scope output, so step 1 crashed on a missing gradient.
    from safetensors.torch import load_file

    rep = _run_extra(tiny_setup, "mk-untied-out", ["--train-marker-rows", "--marker-lr", "1e-2", "--lr", "1e-2",
                                                   "--untie-head", "--marker-scope", "output"], method="markers")
    wb = rep["checks"]["writeback_step1"]
    assert wb["tensor"] == "lm_head (marker rows)" and wb["pass"] and wb["lr"] > 0
    assert rep["checks"]["frozen_weights_unchanged"]["pass"] and rep["checks"]["reload_parity"]["pass"]
    base = load_file(str(tiny_setup / "base" / "model.safetensors"))["model.embed_tokens.weight"]
    saved = load_file(str(tiny_setup / "mk-untied-out" / "model" / "model.safetensors"))
    assert torch.equal(saved["model.embed_tokens.weight"], base)
    moved = [i for i in range(base.shape[0]) if not torch.equal(base[i], saved["lm_head.weight"][i])]
    assert moved and set(moved) <= {0, 1, 2, 15, 16}, moved


# ---------------------------------------------------------------- format judge


@needs_tok
def test_format_judge():
    t = tok()
    r, = retok.retokenize([fixture_row(3)], t)[0]
    prompt, gen = r["input_ids"][: r["prompt_len"]], r["input_ids"][r["prompt_len"]:]
    ok = evaluate.judge(t, prompt, gen[:-2])  # reference continuation up to and including <|im_end|>
    assert ok["valid"] and ok["has_think"] and ok["has_code_block"] and ok["closed_im_end"]
    assert not evaluate.judge(t, prompt, gen[:-3])["valid"]  # no <|im_end|>
    assert evaluate.judge(t, prompt, [6] + gen[:-2])["reason"] == "foreign_special_token"
    no_reply = t.encode("<jupyter_script>\nx\n<empty_output>\n<|im_end|>", add_special_tokens=False).ids
    assert evaluate.judge(t, prompt, no_reply)["reason"] == "empty_visible_reply"
