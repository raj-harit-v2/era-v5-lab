"""jobs/g5_config.py: the one G5 config_v1.yaml -> base.yaml mapping used by the dryrun1 prof and nsys jobs.

  * the signed config_v1.yaml still gives exactly the overrides both jobs used before the move (same model timed)
  * prof and nsys call the same function, so they cannot drift apart again
  * a non-null G5 setting with no mapping, an unknown loss.train_on or a different tokenizer stops the job
  * null values keep base.yaml defaults; a plain perfkit config gives no overrides
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "jobs"
G5_CONFIG_V1 = ROOT.parents[1] / "teams" / "05-architecture" / "configs" / "config_v1.yaml"

sys.path.insert(0, str(JOBS))
import g5_config  # noqa: E402

# What run_dryrun1_prof.py and run_dryrun1_nsys.py each produced from the signed config_v1.yaml before this change.
SIGNED_CONFIG_V1_OVERRIDES = [
    "model.ffn=moe",
    "run.seed=1234",
    "run.grad_clip=1.0",
    "optim.name=muon",
    "optim.lr=0.001",
    "optim.muon_lr=0.006",
    "model.vocab_size=131072",
    "model.embedding=ke2",
    "model.ke_max_pos=32",
    "model.attn_impl=eager",
    "model.moe.num_experts=16",
    "model.moe.num_shared=1",
    "model.moe.top_k=2",
    "model.moe.bias_gamma=0.001",   # G5 #748, loss-free balancing (TSAI, 23 Nov)
    "model.mtp=false",
    "model.moe.dispatch=sorted",
]


def _job(name: str):
    spec = importlib.util.spec_from_file_location(f"g5cfg_{name}", JOBS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _settings(tmp_path, *rows: str) -> Path:
    cfg = tmp_path / "config_v1.yaml"
    cfg.write_text("settings:\n" + "".join(f"  - {r}\n" for r in rows))
    return cfg


@pytest.mark.skipif(not G5_CONFIG_V1.exists(), reason="G5 config_v1.yaml not in this tree")
def test_signed_config_v1_maps_unchanged():
    overrides, applied = g5_config.load_g5_overrides(G5_CONFIG_V1)
    assert overrides == SIGNED_CONFIG_V1_OVERRIDES
    assert applied["tokenizer.name"] == g5_config.TOKENIZER_NAME


def test_prof_and_nsys_share_one_mapping():
    prof, nsys = _job("run_dryrun1_prof"), _job("run_dryrun1_nsys")
    assert prof.load_g5_overrides is g5_config.load_g5_overrides
    assert nsys.load_g5_overrides is g5_config.load_g5_overrides
    assert not hasattr(prof, "G5_TO_BASE_KEY") and not hasattr(nsys, "G5_TO_BASE_KEY")


def test_unmapped_key_stops_the_job(tmp_path):
    cfg = _settings(tmp_path, "{key: moe.top_k, value: 2}", "{key: attention.n_kv_head, value: 2}",
                    "{key: model.activation, value: swiglu}")
    with pytest.raises(ValueError, match=r"attention\.n_kv_head=2.*model\.activation=swiglu"):
        g5_config.load_g5_overrides(cfg)


def test_unknown_train_on_stops_the_job(tmp_path):
    with pytest.raises(ValueError, match=r"loss\.train_on=both"):
        g5_config.load_g5_overrides(_settings(tmp_path, "{key: loss.train_on, value: both}"))


@pytest.mark.parametrize("mode, expected", [("ntp", "model.mtp=false"), ("MTP", "model.mtp=true")])
def test_train_on_maps(tmp_path, mode, expected):
    overrides, _ = g5_config.load_g5_overrides(_settings(tmp_path, f"{{key: loss.train_on, value: {mode}}}"))
    assert overrides == [expected]


def test_router_on_muon_true_needs_no_override(tmp_path):
    """perfkit's Muon already includes the router (G5 #736 default), so true maps to nothing."""
    overrides, applied = g5_config.load_g5_overrides(_settings(tmp_path, "{key: optim.router_on_muon, value: true}"))
    assert overrides == [] and applied == {"optim.router_on_muon": True}


def test_router_on_adamw_stops_the_job(tmp_path):
    with pytest.raises(ValueError, match=r"optim\.router_on_muon=False"):
        g5_config.load_g5_overrides(_settings(tmp_path, "{key: optim.router_on_muon, value: false}"))


def test_bias_gamma_maps(tmp_path):
    """G5 #748's loss-free balancing step size reaches perfkit's SparseMoE (same update rule)."""
    overrides, _ = g5_config.load_g5_overrides(_settings(tmp_path, "{key: moe.bias_gamma, value: 0.001}"))
    assert "model.moe.bias_gamma=0.001" in overrides


def test_other_tokenizer_stops_the_job(tmp_path):
    with pytest.raises(ValueError, match=r"tokenizer\.name=OtherTok"):
        g5_config.load_g5_overrides(_settings(tmp_path, "{key: tokenizer.name, value: OtherTok}"))


def test_pinned_tokenizer_passes_with_no_override(tmp_path):
    overrides, applied = g5_config.load_g5_overrides(
        _settings(tmp_path, f"{{key: tokenizer.name, value: {g5_config.TOKENIZER_NAME}}}"))
    assert overrides == [] and applied == {"tokenizer.name": g5_config.TOKENIZER_NAME}


def test_null_values_keep_base_defaults(tmp_path):
    overrides, applied = g5_config.load_g5_overrides(
        _settings(tmp_path, "{key: model.n_layer, value: null}", "{key: some.future_key, value: null}",
                  "{key: run.seed, value: 7}"))
    assert overrides == ["run.seed=7"] and applied == {"run.seed": 7}


def test_plain_perfkit_config_gives_no_overrides(tmp_path):
    cfg = tmp_path / "arm.yaml"
    cfg.write_text("model:\n  n_layer: 2\nrun:\n  seed: 1\n")
    assert g5_config.load_g5_overrides(cfg) == ([], {})


def test_tokenizer_name_is_the_one_dataio_pins():
    """One source of truth: the check accepts exactly the tokenizer dataio/tokenizer.py loads, and bench.py records it.
    A re-pin (p1536) then changes the loader, this check and the run record together."""
    from dataio import tokenizer
    assert g5_config.TOKENIZER_NAME == tokenizer.NAME
    assert g5_config.TOKENIZER_SHA256 == tokenizer.SHA256
    bench_src = (ROOT / "perfkit" / "bench.py").read_text()
    assert '"name": TOKENIZER_NAME' in bench_src and f'"{tokenizer.NAME}"' not in bench_src

