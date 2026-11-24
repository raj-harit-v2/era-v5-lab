"""Save one finished model as a Team 7 checkpoint run folder, so Team 9's run_lab_ckpt.py can read it (--run-dir).

In simple words: the G10 job scripts delete every weight at exit. With `--keep-weights-dir` one arm's plain weights are
written here instead, through Team 7's own Checkpointer (the only way Team 9's reader accepts), and nothing else.

    from keep_weights import save_run_folder, team5_probe
    info = save_run_folder(model, "keep/", "g10-sft-a2", step=243, probe_fn=team5_probe)
    # keep/g10-sft-a2/latest.json, commits.jsonl, main/step_00000243-e1/{MANIFEST.json, shards}

Only Team 7's public API is used: Checkpointer(...).save(...) and .wait(), and (in the test) export_safetensors.

Two things a Team 7 folder cannot say on its own, added here (job ADP, 24 Nov):
- frozen_keys: Team 5's own (`embedding.rows`, `embedding.lengths`, and `codec.G`, `codec.Phi` on a KAS V2 model,
  train_week2.py), so the step MANIFEST.json carries their fingerprints and a restore checks them.
- `G10_MODEL_CONFIG.json` beside latest.json: the model config the weights need. Routing depends on `router_bias` AND on
  `model.moe.bias_gamma` (#748: gamma 0 never reads the bias), and Team 9's reader builds the model from its own
  --model-config, not from the folder. A reader built with a different config loads these weights without an error;
  `check_reader_config()` (CLI: `python capstone/keep_weights.py check --run-dir <folder> --model-spec <json>`) refuses it.
The optimizer and loader that save() asks for are throwaways (a fresh AdamW with no state, Team 7's SyntheticLoader), as
in Team 9's own test (teams/09-evaluation/harness_lab/tests/test_run_lab_ckpt_scorer.py). The model's optimizer state is
NOT saved: this folder holds weights to score, not a state to resume training from.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

TEAMS = Path(__file__).resolve().parents[2]
TEAM07 = TEAMS / "07-infrastructure"
for p in (TEAM07, TEAM07 / "support" / "simulation"):
    if str(p) not in sys.path:
        sys.path.append(str(p))

# Same probe as teams/09-evaluation/harness_lab/lm_eval_lab.py probe_loss (PROBE_SHAPE, PROBE_SEED). export_safetensors
# compares the saved probe bits with the reader's on the same device class, so these two must stay equal; the test pins them.
PROBE_SHAPE, PROBE_SEED = (2, 32), 1234


def _model_vocab_size(model) -> int:
    head = getattr(model, "head", None)
    for obj, attr in ((head, "out_features"), (head, "vocab_size"), (head, "n_vocab"),
                      (model, "vocab_size"), (model, "n_vocab")):
        val = getattr(obj, attr, None)
        if isinstance(val, int) and val > 0:
            return val
    if head is not None and hasattr(head, "tok_u") and head.tok_u.ndim == 2:
        return int(head.tok_u.shape[0])
    raise ValueError(f"cannot determine vocab size from {type(model).__name__}.head ({type(head).__name__})")


def team5_probe(model) -> float:
    """Next-token loss of a Team 5 LanguageModel on Team 9's fixed seeded batch (identical to lm_eval_lab.probe_loss)."""
    import torch
    import torch.nn.functional as F

    vocab = _model_vocab_size(model)
    ids = torch.randint(0, vocab, PROBE_SHAPE, generator=torch.Generator().manual_seed(PROBE_SEED))
    ids = ids.to(next(model.parameters()).device)
    model.eval()
    with torch.no_grad():
        logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
    return F.cross_entropy(logits[:, :-1].reshape(-1, vocab).float(), ids[:, 1:].reshape(-1)).item()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


MODEL_CONFIG_FILE = "G10_MODEL_CONFIG.json"
TEAM5_FROZEN_KEYS = ("embedding.rows", "embedding.lengths", "codec.G", "codec.Phi")  # train_week2.py (#717), those present
ROUTING_KEYS = ("head_mode", "vocab_size", "ke_max_pos", "n_layer", "n_embd")  # plus moe.* below


def model_config_record(model) -> dict:
    """What a reader must build to get this model's outputs from these weights (from Team 5's LanguageModel.spec)."""
    spec = getattr(model, "spec", None)
    if not isinstance(spec, dict):
        raise ValueError(f"{type(model).__name__} has no Team 5 `spec`: cannot record the model config with its weights")
    biases = {n: b for n, b in model.named_buffers() if n.endswith(".router_bias")}
    moe = dict(spec.get("moe") or {})
    rec = {"head_mode": spec.get("head_mode", "dense_untied"), "bias_gamma": float(moe.get("bias_gamma") or 0.0),
           "moe": moe, **{k: spec.get(k) for k in ROUTING_KEYS if k != "head_mode"},
           "router_bias_absmax": max((float(b.abs().max()) for b in biases.values()), default=0.0),
           "router_bias_layers": len(biases),
           "model_spec": spec,
           "model_spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()}
    if rec["router_bias_absmax"] != 0.0 and rec["bias_gamma"] == 0.0:  # recorded, not refused: the weights are saved
        rec["warning"] = "router_bias is non-zero but model.moe.bias_gamma is 0: this model ignores its bias"
    return rec


def check_reader_config(run_dir, reader_spec: dict) -> dict:
    """Refuse a reader whose model config would not reproduce the saved model: head_mode, bias_gamma and every moe key
    must be equal. Returns the stored record. A folder without the record (saved before job ADP) is refused too."""
    path = Path(run_dir) / MODEL_CONFIG_FILE
    if not path.is_file():
        raise ValueError(f"{path} missing: this folder does not say which model config its weights need")
    rec = json.loads(path.read_text(encoding="utf-8"))
    got = {"head_mode": reader_spec.get("head_mode", "dense_untied"),
           "bias_gamma": float((reader_spec.get("moe") or {}).get("bias_gamma") or 0.0),
           "moe": dict(reader_spec.get("moe") or {}), **{k: reader_spec.get(k) for k in ROUTING_KEYS if k != "head_mode"}}
    bad = {k: (rec.get(k), got[k]) for k in got if rec.get(k) != got[k]}
    if bad:
        raise ValueError(f"reader model config differs from the one {run_dir} was saved with (saved, reader): {bad}")
    return rec


def save_run_folder(model, remote_root, run_id: str, step: int, probe_fn, tokens: int = 0, seed: int = 0) -> dict:
    """Write `model` (plain weights, state_dict keys as they are) as <remote_root>/<run_id>/ and return where it is.

    Returns {"run_dir", "step", "manifest_path", "manifest_sha256", "state_digest"}; the manifest sha256 is what Team 9's
    reader records as model_revision. Raises if the commit did not happen (Checkpointer.wait() False). The model must be
    the unwrapped model (no adapter wrappers): the keys saved are the keys a fresh model loads strictly.
    """
    import torch
    from ckpt.ckpt import Checkpointer
    from trainer.tiny import SyntheticLoader

    bad = [k for k in model.state_dict() if "lora_" in k or k.endswith(".mask") or "keep_mask" in k]
    bad += [f"<module {n}: {type(m).__name__}>" for n, m in model.named_modules() if type(m).__name__ in ("LoRALinear", "MaskedLinear")]
    if bad:
        raise ValueError(f"not plain weights (adapter or mask keys present, merge or bake first): {bad[:3]}")
    config_rec = model_config_record(model) if isinstance(getattr(model, "spec", None), dict) else None
    os.environ.setdefault("V5_EVENTS_DIR", tempfile.mkdtemp(prefix="kw_events_"))
    remote_root = Path(remote_root).resolve()
    remote_root.mkdir(parents=True, exist_ok=True)
    local = tempfile.mkdtemp(prefix="kw_local_")
    model.eval()
    flags = []
    try:
        # Weights only: Team 7's save asks the optimizer for its state and makes zero moments for every parameter that
        # requires grad (3x the bytes). With the flags off for the duration of the save there are none; they are restored.
        flags = [(p, p.requires_grad) for p in model.parameters()]
        for p, _ in flags:
            p.requires_grad_(False)
        optim = torch.optim.AdamW(list(model.parameters()), lr=0.0)
        frozen = tuple(k for k in TEAM5_FROZEN_KEYS if k in model.state_dict())
        ck = Checkpointer(run_id, local, str(remote_root), seed=seed, code_paths=(str(Path(__file__).resolve()),),
                          frozen_keys=frozen)
        saved = ck.save(step, model, optim, SyntheticLoader(0, 2, 0, 1), probe_fn, tokens=tokens, reason="keep-weights")
        if not (saved and ck.wait()):
            raise RuntimeError(f"keep-weights: the checkpoint for {run_id} step {step} was not committed")
    finally:
        for p, flag in flags:
            p.requires_grad_(flag)
        shutil.rmtree(local, ignore_errors=True)
    run_dir = remote_root / run_id
    if config_rec is not None:
        (run_dir / MODEL_CONFIG_FILE).write_text(json.dumps({**config_rec, "frozen_keys": list(frozen)}, indent=1,
                                                            sort_keys=True, default=str), encoding="utf-8")
    pointer = json.loads((run_dir / "latest.json").read_text(encoding="utf-8"))
    manifest = run_dir / pointer["path"] / "MANIFEST.json"
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    return {"run_dir": str(run_dir), "step": step, "manifest_path": str(manifest.relative_to(remote_root)),
            "manifest_sha256": _sha256(manifest), "state_digest": meta.get("state_digest"),
            "frozen_keys": list(frozen), "model_config_file": MODEL_CONFIG_FILE if config_rec is not None else None,
            "bias_gamma": (config_rec or {}).get("bias_gamma"), "head_mode": (config_rec or {}).get("head_mode")}


def main(argv=None) -> int:
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(description="check a reader's model config against a kept-weights folder")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="exit 1 unless --model-spec (a JSON of the resolved `model` config) matches")
    c.add_argument("--run-dir", required=True)
    c.add_argument("--model-spec", required=True, help="JSON file: the reader's resolved config['model'] (or {'model': ...})")
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.model_spec).read_text(encoding="utf-8"))
    spec = spec.get("model", spec)
    try:
        rec = check_reader_config(a.run_dir, spec)
    except ValueError as e:
        print(f"REFUSED: {e}")
        return 1
    print(json.dumps({"ok": True, "head_mode": rec["head_mode"], "bias_gamma": rec["bias_gamma"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
