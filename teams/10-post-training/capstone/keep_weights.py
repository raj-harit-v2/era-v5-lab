"""Save one finished model as a Team 7 checkpoint run folder, so Team 9's run_lab_ckpt.py can read it (--run-dir).

In simple words: the G10 job scripts delete every weight at exit. With `--keep-weights-dir` one arm's plain weights are
written here instead, through Team 7's own Checkpointer (the only way Team 9's reader accepts), and nothing else.

    from keep_weights import save_run_folder, team5_probe
    info = save_run_folder(model, "keep/", "g10-sft-a2", step=243, probe_fn=team5_probe)
    # keep/g10-sft-a2/latest.json, commits.jsonl, main/step_00000243-e1/{MANIFEST.json, shards}

Only Team 7's public API is used: Checkpointer(...).save(...) and .wait(), and (in the test) export_safetensors.
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
        ck = Checkpointer(run_id, local, str(remote_root), seed=seed, code_paths=(str(Path(__file__).resolve()),))
        saved = ck.save(step, model, optim, SyntheticLoader(0, 2, 0, 1), probe_fn, tokens=tokens, reason="keep-weights")
        if not (saved and ck.wait()):
            raise RuntimeError(f"keep-weights: the checkpoint for {run_id} step {step} was not committed")
    finally:
        for p, flag in flags:
            p.requires_grad_(flag)
        shutil.rmtree(local, ignore_errors=True)
    run_dir = remote_root / run_id
    pointer = json.loads((run_dir / "latest.json").read_text(encoding="utf-8"))
    manifest = run_dir / pointer["path"] / "MANIFEST.json"
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    return {"run_dir": str(run_dir), "step": step, "manifest_path": str(manifest.relative_to(remote_root)),
            "manifest_sha256": _sha256(manifest), "state_digest": meta.get("state_digest")}
