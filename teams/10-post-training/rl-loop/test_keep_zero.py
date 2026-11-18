"""Deletion survives RL: KeepZero holds baked-DT zeros at zero, the check can fail, and the trainer wires it in.

Tiny random OLMoE + toy task, CPU. Fixtures, not training data.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest
import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import keep_zero  # noqa: E402
import tasks  # noqa: E402
import train  # noqa: E402


def _toy_params(seed=0):
    g = torch.Generator().manual_seed(seed)
    w = torch.nn.Parameter(torch.randn(8, 16, generator=g))
    free = torch.nn.Parameter(torch.randn(4, 4, generator=g))
    keep = torch.rand(8, 16, generator=g) > 0.3
    with torch.no_grad():
        w.mul_(keep)
    return w, free, keep


def _loss(w, free):
    return ((w * 3.0 + 1.0).pow(2).sum() + (free * 2.0).pow(2).sum())


def test_gradient_mask_holds_deleted_weights_at_zero_under_adamw():
    w, free, keep = _toy_params()
    kz = keep_zero.KeepZero([("w", w), ("free", free)], {"w": keep})
    assert kz.deleted_nonzero() == 0 and kz.n_deleted0 == int((~keep).sum())
    opt = torch.optim.AdamW([w, free], lr=0.05, weight_decay=0.0)
    kept_before = w.detach()[keep].clone()
    for _ in range(25):
        opt.zero_grad()
        _loss(w, free).backward()
        opt.step()
        assert kz.check("toy") == 0
    assert (w.detach()[~keep] == 0).all() and kz.deleted_zero() == kz.n_deleted0
    assert not torch.equal(w.detach()[keep], kept_before)  # the undeleted weights did train
    assert kz.zero_share() >= kz.n_deleted0 / kz.n_total


def test_the_check_can_fail_without_the_hook():
    w, free, keep = _toy_params()
    kz = keep_zero.KeepZero([("w", w), ("free", free)], {"w": keep})
    w._backward_hooks.clear()  # remove the gradient mask: the same steps now fill the deleted entries
    opt = torch.optim.AdamW([w, free], lr=0.05, weight_decay=0.0)
    opt.zero_grad()
    _loss(w, free).backward()
    opt.step()
    assert kz.deleted_nonzero() > 0
    with pytest.raises(RuntimeError, match="deleted weights are nonzero"):
        kz.check("toy")
    kz.enforce()  # the backstop puts them back
    assert kz.deleted_nonzero() == 0


def test_weight_decay_needs_enforce_and_bad_masks_are_refused():
    w, free, keep = _toy_params()
    with pytest.raises(ValueError, match="weight decay"):
        keep_zero.KeepZero([("w", w)], {"w": keep}, weight_decay=0.1)
    keep_zero.KeepZero([("w", w)], {"w": keep}, enforce=True, weight_decay=0.1)
    with pytest.raises(ValueError, match="not trainable"):
        keep_zero.KeepZero([("w", w)], {"missing": keep})
    with pytest.raises(ValueError, match="shape"):
        keep_zero.KeepZero([("w", w)], {"w": keep[:2]})
    # a deleted entry that is not zero is a nonzero count, whatever the reason
    w2 = torch.nn.Parameter(torch.ones(8, 16))
    assert keep_zero.KeepZero([("w", w2)], {"w": keep}).deleted_nonzero() == int((~keep).sum())


def test_packed_mask_roundtrip(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("dtm", HERE.parent / "dt" / "mask.py")
    dtm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dtm)
    _, _, keep = _toy_params()
    blob, meta = dtm.pack_masks({"a.weight": keep, "b.weight": keep[:3, :5].contiguous()})
    (tmp_path / "m.bin").write_bytes(blob)
    (tmp_path / "m.bin.json").write_text(json.dumps(meta))
    back = keep_zero.load_masks(tmp_path / "m.bin")
    assert torch.equal(back["a.weight"], keep) and torch.equal(back["b.weight"], keep[:3, :5])


def test_toy_even_rule_is_prompt_independent():
    t = tasks.ToyTask(vocab=100, prompt_len=4, rule="even", seed=1)
    assert t.reward([1, 2, 3, 5], [4]) == 1.0 and t.reward([1, 2, 3, 5], [7]) == 0.0
    assert t.reward([9, 9, 9, 8], [4]) == 1.0 and t.reward([1], []) == 0.0


def _cfg(out: Path, steps=4):
    cfg = yaml.safe_load((HERE / "config" / "smoke_objective_v1.yaml").read_text())
    cfg["out_dir"] = str(out)
    cfg["verbose"] = False
    cfg["task"] = {"kind": "toy", "vocab": 16, "prompt_len": 4, "rule": "even", "n_train": 32, "n_heldout": 16, "seed": 77}
    cfg["train"].update(steps=steps, eval_every=2, ppo_epochs=1, prompts_per_step=8, lr=0.01)
    return cfg


def _deleted_start_state(tmp_path: Path, cfg: dict, frac=0.4):
    """A baked-DT-like start: zero a fixed random 40% of every attention q/k/v weight, save as an init state."""
    from safetensors.torch import save_file
    policy, _ = train.build_model(cfg["model"], "cpu")  # same seed state as train() would use
    torch.manual_seed(5)
    keep = {}
    with torch.no_grad():
        for n, p in policy.model.named_parameters():
            if "self_attn" in n and n.endswith(("q_proj.weight", "k_proj.weight", "v_proj.weight")):
                keep[n] = torch.rand(p.shape) > frac
                p.mul_(keep[n])
    assert keep
    sd = {k: v.detach().clone().contiguous() for k, v in policy.model.state_dict().items()}
    save_file(sd, str(tmp_path / "start.safetensors"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("dtm2", HERE.parent / "dt" / "mask.py")
    dtm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dtm)
    blob, meta = dtm.pack_masks(keep)
    (tmp_path / "keep.bin").write_bytes(blob)
    (tmp_path / "keep.bin.json").write_text(json.dumps(meta))
    cfg["model"]["init_state"] = str(tmp_path / "start.safetensors")
    cfg["train"]["keep_zero"] = {"path": str(tmp_path / "keep.bin")}
    return keep


def test_trainer_keeps_deleted_weights_at_zero_while_other_weights_train(tmp_path):
    cfg = _cfg(tmp_path / "run")
    keep = _deleted_start_state(tmp_path, cfg)
    s = train.train(cfg)
    kz = s["keep_zero"]
    assert kz["deleted_at_start"] == sum(int((~k).sum()) for k in keep.values()) > 0
    assert kz["max_deleted_nonzero"] == 0 and kz["deleted_nonzero_end"] == 0
    assert kz["deleted_zero_end"] >= kz["deleted_at_start"]
    assert kz["persistent_mask_tensor_bytes"] == kz["masked_entries"] * 5  # bool mask and FP32 hook mask
    assert s["init_state"]["sha256"] and s["trainable_weight_change"]["share_changed"] > 0
    assert s["objective"]["steps_with_optimizer_update"] > 0
    recs = [json.loads(line) for line in (tmp_path / "run" / "metrics.jsonl").read_text().splitlines()]
    assert all(r["deleted_nonzero"] == 0 and 0 < r["zero_share"] < 1 for r in recs)
    assert all(r["times_s"]["keep_zero_checks"] >= 0 for r in recs)


def test_trainer_fails_loudly_when_the_gradient_mask_is_missing(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path / "run")
    _deleted_start_state(tmp_path, cfg)
    real_init = keep_zero.KeepZero.__init__

    def no_hooks(self, *a, **k):
        real_init(self, *a, **k)
        for p in self.params.values():
            p._backward_hooks.clear()
    monkeypatch.setattr(keep_zero.KeepZero, "__init__", no_hooks)
    with pytest.raises(RuntimeError, match="deleted weights are nonzero"):
        train.train(cfg)


def test_trainer_refuses_a_start_whose_deleted_weights_are_nonzero(tmp_path):
    cfg = _cfg(tmp_path / "run")
    _deleted_start_state(tmp_path, cfg)
    cfg["train"]["keep_zero"] = {"path": str(tmp_path / "keep.bin")}
    del cfg["model"]["init_state"]  # random init: nothing is deleted yet
    with pytest.raises(ValueError, match="nonzero before RL starts"):
        train.train(cfg)


def test_bad_init_state_hash_is_refused(tmp_path):
    cfg = _cfg(tmp_path / "run")
    _deleted_start_state(tmp_path, cfg)
    cfg["model"]["init_state_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="init_state sha256"):
        train.train(cfg)


def test_vllm_refuses_a_separate_sft_init_state_before_loading_any_model(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path / "run")
    cfg["model"]["init_state"] = str(tmp_path / "start.safetensors")
    cfg["train"]["sampler"] = "vllm"

    def unexpected_load(*args, **kwargs):
        pytest.fail("incompatible settings reached model setup")

    monkeypatch.setattr(train.rollout, "VLLMSampler", unexpected_load)
    monkeypatch.setattr(train, "build_model", unexpected_load)
    with pytest.raises(ValueError, match="init_state is incompatible with the vLLM sampler"):
        train.train(cfg)


def test_resume_checks_baked_artifacts_and_restored_deletions(tmp_path):
    from safetensors.torch import load_file, save

    cfg = _cfg(tmp_path / "run", steps=1)
    keep = _deleted_start_state(tmp_path, cfg)
    state_dir = tmp_path / "state"
    cfg["train"].update(state_dir=str(state_dir), state_every=1)
    summary = train.train(cfg)
    mask_path = Path(cfg["train"]["keep_zero"]["path"])
    meta_path = Path(f"{mask_path}.json")
    init_path = Path(cfg["model"]["init_state"])

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    digests = {"sha256": sha(mask_path), "metadata_sha256": sha(meta_path)}
    assert summary["init_state"]["sha256"] == sha(init_path)
    assert summary["keep_zero"]["mask"] == {"path": str(mask_path), **digests}
    init_bytes = init_path.read_bytes()
    mask_bytes = mask_path.read_bytes()
    meta_bytes = meta_path.read_bytes()

    changed_init = save(load_file(str(init_path)), metadata={"fixture": "different checkpoint bytes"})
    for path, old, new in (
        (init_path, init_bytes, changed_init),
        (mask_path, mask_bytes, mask_bytes + b"\0"),  # zlib ignores the trailing byte
        (meta_path, meta_bytes, meta_bytes + b"\n"),
    ):
        path.write_bytes(new)
        with pytest.raises(RuntimeError, match="belongs to a different run"):
            train.train(cfg)
        path.write_bytes(old)

    cfg["train"]["keep_zero"]["enforce"] = True
    with pytest.raises(RuntimeError, match="belongs to a different run"):
        train.train(cfg)
    cfg["train"]["keep_zero"]["enforce"] = False

    for hash_key in digests:
        cfg["train"]["keep_zero"][hash_key] = "0" * 64
        with pytest.raises(ValueError, match=f"train.keep_zero {hash_key}"):
            train.train(cfg)
        del cfg["train"]["keep_zero"][hash_key]

    latest = json.loads((state_dir / "LATEST.json").read_text())
    restored = torch.load(state_dir / latest["file"], map_location="cpu", weights_only=False)
    name, mask = next(iter(keep.items()))
    restored["trainable"][name][~mask] = 1
    train.save_state(state_dir, restored["step"], restored)
    with pytest.raises(RuntimeError, match="restored checkpoint: .* deleted weights are nonzero"):
        train.train(cfg)
