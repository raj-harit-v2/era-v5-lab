"""pytest setup for the correctness tests.

  * Puts teams/06-performance on sys.path, so `pytest teams/06-performance/correctness` works from the
    repo root (the Gate 1 command) as well as from teams/06-performance.
  * `device` fixture: cuda if available, else cpu.
  * A test that hits a stub (NotImplementedError) is reported as SKIPPED with the stub's name, not failed.
    `pytest -rs` lists them. At Gate 1 no stub skip may be left (skips for missing CUDA / bf16 are expected
    on a laptop).
  * Only what configs/base.yaml uses runs by default. A test of a feature base.yaml does not select (MoE when
    model.ffn is mlp, KE1 when model.embedding is ke2, SDPA when model.attn_impl is eager, ...) is DESELECTED:
    it does not run and is not listed, and its 1.01 drill goes with it. `pytest correctness --all-configs` runs every test (Gate 1:
    the KE, attention, MoE and reversible pairs must all pass). The rules are in config_requirements() below.
    Exception: the strict xfail in test_ke.py (a recorded KE1 contract gap) always runs, so every run shows it.
  * At the end of the run: one row per pair, grouped by area: the worst output and gradient error, how much
    of the tolerance it uses, whether two runs were bit-identical, and PASS/FAIL with the first failure line.
"""
from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CONFIG = ROOT / "configs" / "base.yaml"
ATTN_TEST_HEADS = 8                  # N_HEAD in test_attention.py: test_causal's first parameter is n_kv_head


def pytest_addoption(parser):
    parser.addoption("--all-configs", action="store_true",
                     help="run every test, not only those for what configs/base.yaml selects")


@functools.cache
def _config():
    from models.config import load_config, model_config
    cfg = load_config(CONFIG)
    return cfg, model_config(cfg)


def _attn_kind(n_head, n_kv_head):
    return "mha" if n_kv_head == n_head else "mqa" if n_kv_head == 1 else "gqa"


def _pair_needs(name):
    """[(key, value)] a registered pair needs from base.yaml; None = always skipped by default."""
    if name.startswith("attention."):
        impl = "eager" if "eager" in name else "sdpa"
        kind = "mha" if "mha" in name else "mqa" if "mqa" in name else "gqa"
        return [("model.attn_impl", impl), ("attention", kind)]
    if name.startswith("ke1."):
        return [("model.embedding", "ke1"), ("model.ke_mode", name.split(".")[1])]
    if name.startswith("ke2"):
        return [("model.embedding", "ke2")]
    if name.startswith("moe."):
        return [("model.ffn", "moe"), ("model.moe.dispatch", name.split(".")[1])]
    if name.startswith("reversible."):
        return [("model.reversible", True), ("model.ffn", name.split(".")[1])]
    if re.match(r"model\.base\.(embedding|ffn|attn_impl|reversible)_", name):
        return None                  # a choice base.yaml does not make (test_model.CHOICES)
    needs = []
    if name.endswith(".bf16"):
        needs.append(("run.dtype", "bf16"))
    if ".chunked" in name:
        needs.append(("model.ce_impl", "chunked"))
    if ".mtp" in name:
        needs.append(("model.mtp", True))
    return needs


def _test_needs(item):
    """[(key, value)] a test that is not a pair needs from base.yaml (by file and test name)."""
    file, fn = item.path.name, item.originalname
    param = item.callspec.id if hasattr(item, "callspec") else ""
    if file == "test_attention.py":
        if fn == "test_causal":
            kv, impl = param.split("-")
            return [("model.attn_impl", "eager" if impl == "eager" else "sdpa"),
                    ("attention", _attn_kind(ATTN_TEST_HEADS, int(kv)))]
        if fn == "test_gqa_paths_agree":
            return [("model.attn_impl", "sdpa"), ("attention", "gqa" if param != "1" else "mqa")]
        if fn == "test_eager_matches_sdpa":
            return [("model.attn_impl", "sdpa")]
    if fn == "test_a_token_longer_than_P_is_normalised_with_L_truncated_to_P":
        return []                    # a recorded contract gap (strict xfail): shown in every run until it is fixed
    if file in ("test_ke.py", "test_tokenizer_optimizer.py"):
        return [("model.embedding", "ke1")] + ([("model.ke_mode", param)] if param in ("dynamic", "cached") else [])
    if file == "test_ke2.py":
        return [("model.embedding", "ke2")]
    if file == "test_moe.py":
        return [("model.ffn", "moe")] + ([("model.moe.dispatch", param)] if param in ("loop", "sorted") else [])
    if file == "test_reversible.py":
        moe = "moe" in fn or param == "moe" or fn == "test_bf16_grad_agrees_with_plain"
        return [("model.reversible", True)] + ([("model.ffn", "moe")] if moe else
                                                [("model.ffn", "mlp")] if param == "mlp" else [])
    if file == "test_model.py" and fn == "test_mtp_loss_parts":
        return [("model.mtp", True)]
    if file == "test_ce.py":
        return [("model.ce_impl", "chunked")]
    if file == "test_optimizer.py":
        if "polar" in fn:
            return [("optim.name", "polar_muon_adamw")]
        if "pure_adamw" in fn:
            return [("optim.name", "adamw")]
        if "cosine" in fn:
            return [("optim.schedule", "cosine")]
        needs = [("optim.name", "muon")]
        if fn == "test_optimizer_ownership_and_norm_gains":
            impl, emb = param.split("-")
            needs += [("optim.muon_impl", impl), ("model.embedding", emb)]
        if fn == "test_batched_newton_schulz_matches_per_matrix_reference":
            needs.append(("optim.muon_impl", "batched"))
        if "grad_scaler" in fn:
            needs.append(("run.dtype", "fp16"))
        return needs
    return []


def _value(key):
    cfg, mcfg = _config()
    if key == "attention":
        return _attn_kind(mcfg.n_head, mcfg.n_kv_head)
    if key.startswith("model."):
        node = mcfg.to_dict()
        for k in key.split(".")[1:]:
            node = node[k]
        return node
    section, k = key.split(".")
    return cfg[section][k]


def config_requirements(item):
    """Why this test does not apply to configs/base.yaml, or None when it does."""
    params = item.callspec.params if hasattr(item, "callspec") else {}
    name = params.get("name")
    if isinstance(name, str) and item.originalname in ("test_pair", "test_every_registered_pair_scaled_fails"):
        needs = _pair_needs(name)
        if needs is None:
            return f"{name}: a variant configs/base.yaml does not select"
    else:
        needs = _test_needs(item)
    wrong = [f"{k}={v}" for k, v in needs if _value(k) != v]
    if wrong:
        return "not in configs/base.yaml: needs " + ", ".join(wrong)
    return None


def pytest_collection_modifyitems(config, items):
    """Tests for what base.yaml does not select are deselected (not run, not shown as skips; pytest prints only
    'N deselected'). `--all-configs` keeps every test. `-v --collect-only --all-configs` lists them all."""
    if config.getoption("--all-configs"):
        return
    keep, drop = [], []
    for item in items:
        (drop if config_requirements(item) else keep).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


@pytest.fixture
def device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


FAILED_PAIRS: dict = {}              # pair name -> first line of its failure (filled by the hook below)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if call.excinfo is not None and call.excinfo.errisinstance(NotImplementedError):
        rep.outcome = "skipped"
        rep.longrepr = (str(item.path), item.location[1] or 0, f"stub: {call.excinfo.value}")
    elif rep.failed and call.excinfo is not None:
        name = getattr(item, "callspec", None) and item.callspec.params.get("name")
        if isinstance(name, str):
            first = str(call.excinfo.value).strip().splitlines()[0] if str(call.excinfo.value).strip() else ""
            FAILED_PAIRS[name] = first.removeprefix(f"{name}: ")


def _used(err, tol) -> str:
    """How much of the tolerance the error uses: '3%' (fine) ... '100%+' (over)."""
    if err is None:
        return ""
    if tol == 0.0:
        return "exact" if err == 0.0 else "OVER"
    pct = 100 * err / tol
    return "<1%" if pct < 1 else f"{pct:.0f}%"


def pytest_terminal_summary(terminalreporter):
    """Each pair's worst error against its tolerance (the Instructor asked for every test's error)."""
    from correctness.framework import RESULTS, TOLERANCES
    names = sorted(set(RESULTS) | set(FAILED_PAIRS))
    if not names:
        return
    tr = terminalreporter
    tr.section("correctness: every pair, fast vs fp64 reference (worst relative error)")
    tr.write_line("used = error / tolerance. repeat = two runs of the fast code are bit-identical.")
    head = f"{'pair':32s} {'dtype':9s} {'output':>9s} {'used':>5s}   {'gradient':>9s} {'used':>5s}   {'repeat':10s} result"
    tr.write_line(head)
    tr.write_line("-" * len(head))
    area = None
    for name in names:
        if area is not None and name.split(".")[0] != area:
            tr.write_line("")
        area = name.split(".")[0]
        if name in FAILED_PAIRS:
            tr.write_line(f"{name:32s} {'':9s} {'':>9s} {'':>5s}   {'':>9s} {'':>5s}   {'':10s} FAIL  {FAILED_PAIRS[name]}",
                          red=True)
            continue
        r = RESULTS[name]
        grad = "-" if r["grad"] is None else f"{r['grad']:.2e}"
        tr.write_line(f"{name:32s} {r['dtype']:9s} {r['out']:9.2e} {_used(r['out'], r['tol']):>5s}   "
                      f"{grad:>9s} {_used(r['grad'], r['grad_tol']):>5s}   {r.get('repeat', ''):10s} PASS")
    tr.write_line("-" * len(head))
    tol = ", ".join(f"{str(d).replace('torch.', '')} {o:g} / {g:g}" for d, (o, g) in TOLERANCES.items())
    failed = len(FAILED_PAIRS)
    tr.write_line(f"{len(names)} pairs: {len(names) - failed} PASS, {failed} FAIL.   tolerance (output / gradient): {tol}",
                  red=bool(failed), green=not failed)
