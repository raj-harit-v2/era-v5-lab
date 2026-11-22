"""G5 config_v1.yaml -> configs/base.yaml overrides, shared by the dry-run-1 jobs.

run_dryrun1_prof.py (class #486) and run_dryrun1_nsys.py (class #492) must profile the same model, so they use this
one mapping. A non-null G5 setting either reaches the model or stops the job: an unknown key, an unknown
loss.train_on value or a tokenizer other than the pinned one raises ValueError instead of being dropped.

Null values (open full-width dimensions in the Gate-2 config_v1.yaml) keep base.yaml's small-width defaults until
G5/G7 lock them; results stay labelled small-width. "kronecker" maps to ke2 and the stack keeps base.yaml's
reversible default; both stay as they are until G5/CAP confirm the dry-run-1 contract (REVIEW-D9/D10).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # teams/06-performance, for dataio (stdlib only)
from dataio.tokenizer import NAME as TOKENIZER_NAME, SHA256 as TOKENIZER_SHA256  # noqa: E402

# G5 config_v1.yaml `settings:` key -> G6 configs/base.yaml key
G5_TO_BASE_KEY = {
    "run.seed": "run.seed",
    "run.grad_clip": "run.grad_clip",
    "optim.name": "optim.name",
    "optim.lr": "optim.lr",
    "optim.muon_lr": "optim.muon_lr",
    "tokenizer.vocab_size": "model.vocab_size",
    "embedding.pos_dim": "model.ke_max_pos",
    "attention.impl": "model.attn_impl",
    "moe.n_expert": "model.moe.num_experts",
    "moe.n_shared": "model.moe.num_shared",
    "moe.top_k": "model.moe.top_k",
    "model.n_layer": "model.n_layer",
    "model.d_model": "model.n_embd",
    "model.n_head": "model.n_head",
    "model.d_ff": "model.moe.ffn_hidden",
    "data.seq_len": "model.block_size",
    "precision": "run.dtype",
}

# TOKENIZER_NAME is the tokenizer perfkit actually loads, read from dataio/tokenizer.py (which pins its file by
# revision + SHA256 and checks its 131,072-id vocab; perfkit/bench.py records the same name in every run). A different
# name in config_v1 cannot be honoured, so it stops the job. Re-pinning dataio/tokenizer.py moves this check with it.


def load_g5_overrides(cfg_path: Path) -> Tuple[List[str], Dict[str, object]]:
    """Translate G5's `settings: [{key, value, ...}]` into base.yaml CLI overrides.

    Returns (overrides, applied): the overrides for perfkit and the non-null G5 settings read. A plain perfkit
    config (with model:/run:, no settings: list) gives no overrides, so perfkit loads it as it is.
    Raises ValueError, naming every offending setting, if a non-null G5 setting has no mapping.
    """
    raw = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw.get("settings"), list):
        return [], {}

    applied: Dict[str, object] = {}
    overrides: List[str] = []
    unmapped: List[str] = []
    has_moe = False

    for item in raw["settings"]:
        if not isinstance(item, dict):
            continue
        key, val = item.get("key"), item.get("value")
        if not key or val is None:
            continue
        applied[key] = val

        if key == "tokenizer.name":
            if str(val) != TOKENIZER_NAME:
                unmapped.append(f"{key}={val} (perfkit loads only {TOKENIZER_NAME}, sha256 {TOKENIZER_SHA256[:12]}…)")
            continue
        if key == "embedding.type":
            overrides.append(f"model.embedding={'ke2' if str(val).lower() in ('kronecker', 'ke2') else val}")
            continue
        if key == "loss.train_on":
            mode = str(val).lower()
            if mode in ("ntp", "mtp"):
                overrides.append(f"model.mtp={'true' if mode == 'mtp' else 'false'}")
            else:
                unmapped.append(f"{key}={val}")
            continue

        has_moe = has_moe or key.startswith("moe.")
        if key in G5_TO_BASE_KEY:
            overrides.append(f"{G5_TO_BASE_KEY[key]}={val}")
        else:
            unmapped.append(f"{key}={val}")

    if unmapped:
        raise ValueError(f"{cfg_path}: G5 settings with no base.yaml mapping (add them to jobs/g5_config.py): "
                         + ", ".join(unmapped))

    if has_moe:
        overrides.insert(0, "model.ffn=moe")
        overrides.append("model.moe.dispatch=sorted")
    return overrides, applied
