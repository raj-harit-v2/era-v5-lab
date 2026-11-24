"""Strict G5 (Team 5) artifact adapter for the RL loop.

Builds a validated bundle around Team 5's own `harness/week2` code: the real `LanguageModel` class, G5's own config
resolution (`load_runtime` + `train_week2.apply_resolution` + `validate`), G5's own tokenizer/KE2 integrity check
(`week2.artifacts.Artifacts`) and G5's own state hash (`train_week2.model_hash`). Nothing from G5 is copied here.

    result = build(config)                    # dict, or path to a YAML file
    result.status                              # READY | FIXTURE_READY | WAITING_FOR_G5_ARTIFACT
    bundle = result.require_bundle()           # raises unless a model was built
    logits = bundle.forward(ids, valid)        # [B, T, V], main head, right padding only

Modes (config `mode`):
    real      the G5 delivery. No overrides, no fixture marker, a G5-supplied probe expectation is required. If the
              checkpoint is not there yet the result is WAITING_FOR_G5_ARTIFACT and no model is built.
    fixture   development only. May shrink the model with `fixture_overrides` and must load a checkpoint that carries
              the fixture marker. A fixture bundle can never back a learning report (`require_learning_ready`).
    run_folder  a folder written by Team 5's `train_week2.py` (manifest.json, checkpoint.pt, summary.json). The model
              spec is the manifest's resolved config (re-validated by G5's `validate`); the manifest's source hashes
              must equal the pinned import; tokenizer and KE2 table must be the manifest's; the checkpoint's
              identity hash must be the manifest's, and G5's `model_hash` of the loaded model must equal
              summary.json's `final_model_sha256`. `run_folder.origin` says who trained it:
                g10_rehearsal  a run G10 trained itself with G5's code (e.g. a small width on a laptop). Status
                               REHEARSAL_READY: mechanics and relative comparisons only, never a learning report.
                g5_delivery    a run folder from Team 5 / TSAI. Needs a non-smoke manifest (AGREED_BASELINE_RUN)
                               and a probe expectation; status READY.

Config keys (paths are relative to the config file):
    g5:            root (repo root holding teams/05-architecture), commit (40-hex), files_sha256 {relpath: sha256},
                   arm, resolution, runtime (optional). Without a git checkout: commit null, pin: file_hashes,
                   source_commit (recorded only) and every harness/week2/*.py + harness/train_week2.py hashed.
    checkpoint:    path, sha256, format (g5_train_week2_pt | state_dict_safetensors)   (real / fixture)
    run_folder:    path, origin (g10_rehearsal | g5_delivery), manifest_sha256, checkpoint_sha256   (run_folder)
    ke2:           table, table_file_sha256, table_content_sha256, vocab_size, pos_dim
    tokenizer:     path, sha256, chat_template, chat_template_sha256
    special_tokens: pad / end_of_turn / end_of_sequence / im_start, each {token, id}; stop: [names]
    trainable:     router_patterns [regex], trainable_patterns [regex]
    probe:         ids [int], expected_mean_nll, atol   (required in real mode; G5 supplies the number)
    fixture_overrides: {model dims}   (fixture mode only)
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))  # rl-loop modules (policy.py) for the existing sampling seam

READY = "READY"
FIXTURE_READY = "FIXTURE_READY"
WAITING = "WAITING_FOR_G5_ARTIFACT"
REHEARSAL_READY = "REHEARSAL_READY"
RUN_FOLDER_ORIGINS = ("g10_rehearsal", "g5_delivery")
# Files Team 5's train_week2.py hashes into manifest["sources"] (by basename) that must equal the pinned import.
RUN_FOLDER_SOURCE_FILES = {"train_week2.py": "harness/train_week2.py", "model.py": "harness/week2/model.py",
                           "config.py": "harness/week2/config.py", "artifacts.py": "harness/week2/artifacts.py"}
# Compared too when the run's manifest recorded them (Team 5 hashes every week2/*.py, train_week2.py:406): the KAS V2 head
# and input (#717). A changed head forward would otherwise load cleanly and pass a probe computed with the same new code.
RUN_FOLDER_SOURCE_FILES_IF_RECORDED = {"kas_v2.py": "harness/week2/kas_v2.py", "kas_terms.py": "harness/week2/kas_terms.py",
                                       "unigram.py": "harness/week2/unigram.py", "raw_vocab.py": "harness/week2/raw_vocab.py"}

FIXTURE_MARKER_KEY = "g10_fixture"  # top-level key in a .pt dict / safetensors metadata key
FIXTURE_MARKER_VALUE = "FIXTURE_NOT_A_G5_ARTIFACT"
CHECKPOINT_FORMATS = ("g5_train_week2_pt", "state_dict_safetensors")
SPECIAL_NAMES = ("pad", "end_of_turn", "end_of_sequence", "im_start")
TOP_KEYS = {"mode", "g5", "checkpoint", "run_folder", "ke2", "tokenizer", "special_tokens", "trainable", "probe",
            "fixture_overrides", "notes"}
G5_FILES_REQUIRED = ("harness/week2/model.py", "harness/week2/config.py", "harness/week2/artifacts.py",
                     "harness/train_week2.py")


class ArtifactError(ValueError):
    """A supplied artifact or config is missing, inconsistent or unsafe. The build is refused."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _sha_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _need(d: dict, key: str, ctx: str):
    if not isinstance(d, dict) or key not in d or d[key] is None:
        raise ArtifactError(f"{ctx}.{key} is required")
    return d[key]


def _hex(v, n: int, ctx: str) -> str:
    if not isinstance(v, str) or not re.fullmatch(f"[0-9a-f]{{{n}}}", v):
        raise ArtifactError(f"{ctx} must be {n} lowercase hex characters")
    return v


# --- G5 source: import the delivered code, pinned by commit and file hashes --------------------------

def _git(root: Path, *args) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise ArtifactError(f"git {' '.join(args)} failed in {root}: {r.stderr.strip()}")
    return r.stdout.strip()


def _load_g5(g5: dict, base: Path) -> dict:
    root = (base / _need(g5, "root", "g5")).resolve()
    team = root / "teams" / "05-architecture"
    harness = team / "harness"
    if not (harness / "week2" / "model.py").is_file():
        raise ArtifactError(f"G5 harness not found under {root}")
    files = _need(g5, "files_sha256", "g5")
    missing = [f for f in G5_FILES_REQUIRED if f not in files]
    if missing:
        raise ArtifactError(f"g5.files_sha256 must pin {missing}")
    if g5.get("commit") is None and g5.get("pin") == "file_hashes":
        # No git checkout (e.g. a hash-pinned bundle on Kaggle): every Python file of the harness that train_week2
        # imports must be pinned by hash; the commit it came from is recorded as `source_commit`, not verified.
        need = sorted(f"harness/week2/{p.name}" for p in (harness / "week2").glob("*.py")) + ["harness/train_week2.py"]
        unpinned = [f for f in need if f not in files]
        if unpinned:
            raise ArtifactError(f"pin: file_hashes needs every harness file pinned; missing {unpinned}")
        commit = "nogit:" + str(g5.get("source_commit") or "unknown")
    else:
        commit = _hex(_need(g5, "commit", "g5"), 40, "g5.commit")
        head = _git(root, "rev-parse", "HEAD")
        if head != commit:
            raise ArtifactError(f"G5 source is at {head}, config pins {commit}")
        rel = [str(Path("teams/05-architecture") / f) for f in files]
        dirty = _git(root, "status", "--porcelain", "--", *rel)
        if dirty:
            raise ArtifactError(f"G5 files differ from commit {commit}: {dirty}")
    actual = {}
    for f, want in files.items():
        p = team / f
        if not p.is_file():
            raise ArtifactError(f"pinned G5 file missing: {f}")
        actual[f] = sha256_file(p)
        if actual[f] != _hex(want, 64, f"g5.files_sha256[{f}]"):
            raise ArtifactError(f"G5 file hash mismatch for {f}: {actual[f]} != {want}")
    # Import the delivered package. A different `week2` already imported in this process is refused, never reused.
    if str(harness) not in sys.path:
        # Appended, not prepended: G5's harness/train.py must not shadow rl-loop/train.py. The source check below
        # still refuses a week2/train_week2 that resolves anywhere but the pinned root.
        sys.path.append(str(harness))
    mods = {}
    for name in ("week2.model", "week2.config", "week2.artifacts", "train_week2"):
        m = importlib.import_module(name)
        src = Path(inspect.getsourcefile(m)).resolve()
        if not src.is_relative_to(harness):
            raise ArtifactError(f"{name} already imported from {src}, not from the pinned G5 root {harness}")
        mods[name] = m
    model_src = Path(inspect.getsourcefile(mods["week2.model"].LanguageModel)).resolve()
    if sha256_file(model_src) != actual["harness/week2/model.py"]:
        raise ArtifactError("LanguageModel class is not from the pinned model.py")
    return {"root": root, "team": team, "commit": commit, "files_sha256": actual, "mods": mods}


# --- config resolution through G5's own loader -------------------------------------------------------

FIXTURE_OVERRIDE_KEYS = {"n_layer", "n_head", "n_kv_head", "n_embd", "block_size", "moe"}
FIXTURE_MOE_KEYS = {"num_experts", "top_k", "num_shared", "ffn_hidden"}


def _resolve(g5src: dict, g5: dict, mode: str, overrides: dict | None) -> dict:
    team = g5src["team"]
    cfgmod, tw = g5src["mods"]["week2.config"], g5src["mods"]["train_week2"]
    arm = team / _need(g5, "arm", "g5")
    resolution = team / _need(g5, "resolution", "g5")
    runtime = team / g5["runtime"] if g5.get("runtime") else None
    for p in [arm, resolution] + ([runtime] if runtime else []):
        if not p.is_file():
            raise ArtifactError(f"G5 config file missing: {p}")
    cfg = tw.apply_resolution(cfgmod.load_runtime(arm, runtime), cfgmod.load(resolution))
    if overrides:
        if mode != "fixture":
            raise ArtifactError("fixture_overrides are only allowed in fixture mode")
        extra = set(overrides) - FIXTURE_OVERRIDE_KEYS
        extra |= {f"moe.{k}" for k in set(overrides.get("moe", {})) - FIXTURE_MOE_KEYS}
        if extra:
            raise ArtifactError(f"fixture_overrides cannot change {sorted(extra)} (vocab and KE2 P follow the artifacts)")
        ov = copy.deepcopy(overrides)  # never mutate the caller's config
        moe = ov.pop("moe", {})
        cfg["model"].update(ov)
        cfg["model"]["moe"].update(moe)
    errors = cfgmod.validate(cfg)
    if errors:
        raise ArtifactError("G5 validate() rejected the resolved config: " + "; ".join(errors))
    return cfg


# --- tokenizer, special tokens, chat template ---------------------------------------------------------

def _load_tokenizer(tcfg: dict, base: Path) -> dict:
    tok_path = base / _need(tcfg, "path", "tokenizer")
    tmpl_path = base / _need(tcfg, "chat_template", "tokenizer")
    for p, what in [(tok_path, "tokenizer"), (tmpl_path, "chat template")]:
        if not p.is_file():
            raise ArtifactError(f"{what} missing: {p}")
    tok_sha = sha256_file(tok_path)
    if tok_sha != _hex(_need(tcfg, "sha256", "tokenizer"), 64, "tokenizer.sha256"):
        raise ArtifactError(f"tokenizer hash mismatch: {tok_sha}")
    tmpl_sha = sha256_file(tmpl_path)
    if tmpl_sha != _hex(_need(tcfg, "chat_template_sha256", "tokenizer"), 64, "tokenizer.chat_template_sha256"):
        raise ArtifactError(f"chat template hash mismatch: {tmpl_sha}")
    return {"path": tok_path, "sha256": tok_sha, "template_path": tmpl_path, "template_sha256": tmpl_sha}


def _load_ke2(kcfg: dict, base: Path, tok: dict, g5src: dict):
    table = base / _need(kcfg, "table", "ke2")
    if not table.is_file():
        raise ArtifactError(f"KE2 table missing: {table}")
    file_sha = sha256_file(table)
    if file_sha != _hex(_need(kcfg, "table_file_sha256", "ke2"), 64, "ke2.table_file_sha256"):
        raise ArtifactError(f"KE2 table file hash mismatch: {file_sha}")
    vocab = _need(kcfg, "vocab_size", "ke2")
    try:  # G5's own check: tokenizer identity, v2 RAW format, content hash, every row against tokenizer.json
        art = g5src["mods"]["week2.artifacts"].Artifacts(tok["path"], table, expected_tokenizer_sha=tok["sha256"],
                                                         expected_vocab=vocab)
    except ValueError as e:
        raise ArtifactError(f"G5 Artifacts rejected tokenizer/KE2: {e}") from e
    if art.table_content_sha != _hex(_need(kcfg, "table_content_sha256", "ke2"), 64, "ke2.table_content_sha256"):
        raise ArtifactError("KE2 table content hash differs from the config")
    if art.pos_dim != _need(kcfg, "pos_dim", "ke2"):
        raise ArtifactError(f"KE2 pos_dim {art.pos_dim} != config {kcfg['pos_dim']}")
    return art


def _special_map(scfg: dict, art) -> dict:
    out = {}
    for name in SPECIAL_NAMES:
        ent = _need(scfg, name, "special_tokens")
        tok, want = _need(ent, "token", f"special_tokens.{name}"), _need(ent, "id", f"special_tokens.{name}")
        got = art.tokenizer.token_to_id(tok)
        if got is None or got != want:
            raise ArtifactError(f"special token {name} {tok!r}: tokenizer id {got}, config {want}")
        if art.tokenizer.encode(tok, add_special_tokens=False).ids != [want]:
            raise ArtifactError(f"special token {tok!r} is not one atomic token")
        out[name] = {"token": tok, "id": int(want)}
    ids = [v["id"] for v in out.values()]
    if len(set(ids)) != len(ids):
        raise ArtifactError(f"special tokens share an id: {out}")
    stop = scfg.get("stop", ["end_of_turn", "end_of_sequence"])
    bad = [s for s in stop if s not in out or s == "pad"]
    if not stop or bad:
        raise ArtifactError(f"special_tokens.stop must name end_of_turn/end_of_sequence entries, got {stop}")
    return {"tokens": out, "stop_names": list(stop), "stop_ids": [out[s]["id"] for s in stop],
            "pad_id": out["pad"]["id"], "bos_id_g5": int(art.bos_id), "pad_id_g5": int(art.pad_id)}


# --- checkpoint ---------------------------------------------------------------------------------------

def _np_safe_globals():
    import numpy as np  # noqa: PLC0415
    g = [np.ndarray, np.dtype]
    for path in ("numpy.core.multiarray._reconstruct", "numpy._core.multiarray._reconstruct"):
        mod, _, attr = path.rpartition(".")
        try:
            g.append(getattr(importlib.import_module(mod), attr))
        except (ImportError, AttributeError):
            pass
    for name in ("UInt32DType", "Int64DType", "Float64DType"):
        t = getattr(getattr(np, "dtypes", None), name, None)
        if t is not None:
            g.append(t)
    return g


def _read_checkpoint(path: Path, fmt: str) -> tuple[dict, bool, dict]:
    """Returns (state_dict, has_fixture_marker, extra identity fields). Never unpickles arbitrary objects."""
    if fmt == "state_dict_safetensors":
        from safetensors import safe_open  # noqa: PLC0415
        with safe_open(str(path), "pt") as f:
            meta = f.metadata() or {}
            sd = {k: f.get_tensor(k) for k in f.keys()}
        return sd, meta.get(FIXTURE_MARKER_KEY) == FIXTURE_MARKER_VALUE, {"metadata": meta}
    if fmt == "g5_train_week2_pt":
        try:
            with torch.serialization.safe_globals(_np_safe_globals()):
                obj = torch.load(path, map_location="cpu", weights_only=True)
        except Exception as e:  # noqa: BLE001  pickle errors come in several types
            raise ArtifactError(f"checkpoint is not loadable with weights_only=True ({type(e).__name__}: {e}); "
                                "ask G5/G7 for a safetensors state-dict export") from e
        if not isinstance(obj, dict) or not isinstance(obj.get("model"), dict):
            raise ArtifactError("G5 trainer checkpoint must be a dict with a 'model' state dict")
        extra = {k: obj[k] for k in ("step", "identity_sha256") if k in obj}
        return obj["model"], obj.get(FIXTURE_MARKER_KEY) == FIXTURE_MARKER_VALUE, extra
    raise ArtifactError(f"checkpoint.format must be one of {CHECKPOINT_FORMATS}")


def _inventory(model) -> list[dict]:
    rows = [{"name": n, "kind": "param", "shape": list(p.shape), "dtype": str(p.dtype)} for n, p in model.named_parameters()]
    rows += [{"name": n, "kind": "buffer", "shape": list(b.shape), "dtype": str(b.dtype)} for n, b in model.named_buffers()]
    return sorted(rows, key=lambda r: r["name"])


# --- router / trainable selection ---------------------------------------------------------------------

def _select(model, moe_cls, tcfg: dict) -> dict:
    router_rx = [re.compile(p) for p in _need(tcfg, "router_patterns", "trainable")]
    train_rx = [re.compile(p) for p in _need(tcfg, "trainable_patterns", "trainable")]
    params = dict(model.named_parameters())
    structural = sorted(f"{n}.router.weight" for n, m in model.named_modules() if isinstance(m, moe_cls))
    if not structural:
        raise ArtifactError("model has no G5 MoE layers")
    matched = sorted(n for n in params if any(r.search(n) for r in router_rx))
    if not matched:
        raise ArtifactError(f"router_patterns {tcfg['router_patterns']} match no parameter")
    wrong = [n for n in matched if n not in structural]
    if wrong:
        kind = "expert" if any(".experts." in n or ".shared." in n for n in wrong) else "non-router"
        raise ArtifactError(f"router_patterns match {kind} parameters, e.g. {wrong[:3]} ({len(wrong)} total)")
    if matched != structural:
        raise ArtifactError(f"router_patterns miss routers: {sorted(set(structural) - set(matched))}")
    trainable = sorted(n for n in params if any(r.search(n) for r in train_rx))
    if not trainable:
        raise ArtifactError(f"trainable_patterns {tcfg['trainable_patterns']} match no parameter")
    overlap = sorted(set(trainable) & set(matched))
    if overlap:
        raise ArtifactError(f"trainable_patterns select frozen router weights: {overlap}")
    dt = lambda names: {n: str(params[n].dtype) for n in names}  # noqa: E731
    return {"router_names": matched, "router_dtypes": dt(matched),
            "router_count": sum(params[n].numel() for n in matched),
            "trainable_names": trainable, "trainable_dtypes": dt(trainable),
            "trainable_count": sum(params[n].numel() for n in trainable),
            "router_patterns": list(tcfg["router_patterns"]), "trainable_patterns": list(tcfg["trainable_patterns"])}


# --- the bundle ---------------------------------------------------------------------------------------

# --- output head access: the one place that knows what LanguageModel.head may be ---------------------------------

def head_access(model) -> dict:
    """What G10 code needs from G5's output head. Two kinds are known; anything else raises ArtifactError.

    dense: dry run 1's untied `nn.Linear(n_embd, V)`; per-token matrix `head.weight` [V, n_embd].
    kas:   Team 5's KAS V2 untied head (#717, kas_v2.KASHead), recognised by a 2-D Parameter `head.tok_u` [V, 64] (the
           rank-64 per-token correction). Per token it owns `tok_u[v]` and `unigram[v]`; `W_out`, `tok_c`, `beta` are
           shared; there is no `head.weight`. `head(h)` maps [..., n_embd] to [..., V].
    Returns {"kind", "vocab_size", "per_token" (Parameter whose row i belongs to token i), "per_token_name", "tied"};
    "tied" is True when any head tensor shares storage with the input embedding.
    """
    head = getattr(model, "head", None)
    if isinstance(head, torch.nn.Linear):
        kind, per_token, name, vocab = "dense", head.weight, "head.weight", int(head.out_features)
    elif (isinstance(head, torch.nn.Module) and isinstance(getattr(head, "tok_u", None), torch.nn.Parameter)
          and head.tok_u.ndim == 2):
        kind, per_token, name, vocab = "kas", head.tok_u, "head.tok_u", int(head.tok_u.shape[0])
    else:
        mats = (sorted(n for n, q in head.named_parameters() if q.ndim == 2) if isinstance(head, torch.nn.Module)
                else [])
        raise ArtifactError(f"unknown G5 output head {type(head).__name__}: G10 handles a dense nn.Linear or a "
                            f"KE2/KAS head with a 2-D `tok_u` [V, r]; its 2-D parameters: {mats}")
    emb = getattr(model, "embedding", None)
    emb_ptrs = {q.data_ptr() for q in emb.parameters()} if isinstance(emb, torch.nn.Module) else set()
    tied = any(q.data_ptr() in emb_ptrs for q in head.parameters())
    return {"kind": kind, "vocab_size": vocab, "per_token": per_token, "per_token_name": name, "tied": tied}


def router_state(model, moe_cls) -> dict:
    """Team 5's loss-free balancer (#748): the expert choice is topk(scores + router_bias) only when moe.bias_gamma != 0;
    with gamma 0 the buffer is ignored. A non-zero bias under gamma 0 is never valid: the delivered model routed with the
    bias, this one would not, and nothing else errors (job ADP test h). Our trainers never call update_router_bias(), so the
    bias stays as delivered (the owner's rule, 23 Nov: "The bias stays as delivered. Do not keep updating it in SFT or RL")."""
    layers = [(n, m) for n, m in model.named_modules() if isinstance(m, moe_cls)]
    bad = [n for n, m in layers if getattr(m, "balance_gamma", 0.0) == 0.0 and isinstance(getattr(m, "router_bias", None),
                                                                                         torch.Tensor)
           and bool(m.router_bias.ne(0).any())]
    if bad:
        raise ArtifactError(f"router_bias is non-zero in {bad[:3]} ({len(bad)} layers) but the resolved model.moe.bias_gamma "
                            f"is 0, so this model would ignore the bias the checkpoint routed with: build from the arm the "
                            f"run used (dry run 2: bias_gamma 0.001)")
    absmax = [float(m.router_bias.abs().max()) if isinstance(getattr(m, "router_bias", None), torch.Tensor) else None
              for _, m in layers]
    return {"bias_gamma": sorted({float(getattr(m, "balance_gamma", 0.0)) for _, m in layers}),
            "router_bias_absmax": absmax, "bias_updated_by_g10": False}


INPUT_CODES = {256: "ke2_raw_table", 64: "ke2_code_2048"}  # per-position code width -> input kind


def input_access(model, pos_dim: int) -> dict:
    """What G10 checks of G5's input layer, detected by name and shape (never by assuming 8,192).

    ke2_raw_table: main's dry run 2 KE2, `embedding.projection.weight` [n_embd, 256 * P] (P = 32: 8,192).
    ke2_code_2048: the TSAI ruling of 23 Nov (G4 chat): Linear(2048, d_model) over a fixed code, d_c = 64 per byte
                   position, L_max = P = 32. Team 5's KASInput (#717, merged 24 Nov as 61f0a3ae; head_mode kas_v2).
    Both need the byte table buffers `embedding.rows` uint8 [V, P] and `embedding.lengths` [V], which G10 compares
    with the validated KE2 table. Anything else raises ArtifactError instead of being read as one of these.
    """
    emb = getattr(model, "embedding", None)
    if not isinstance(emb, torch.nn.Module):
        raise ArtifactError(f"G5 model has no `embedding` module (got {type(emb).__name__})")
    found = {f"embedding.{n}": tuple(t.shape) for n, t in [*emb.named_buffers(), *emb.named_parameters()]}
    rows, lengths = getattr(emb, "rows", None), getattr(emb, "lengths", None)
    if not (isinstance(rows, torch.Tensor) and rows.ndim == 2 and rows.shape[1] == pos_dim
            and isinstance(lengths, torch.Tensor) and tuple(lengths.shape) == (rows.shape[0],)):
        raise ArtifactError(f"G5 input layer has no KE2 byte table buffers embedding.rows [V, {pos_dim}] and "
                            f"embedding.lengths [V]: G10 cannot check it against the validated table; found {found}")
    proj = getattr(getattr(emb, "projection", None), "weight", None)
    if not (isinstance(proj, torch.Tensor) and proj.ndim == 2):
        raise ArtifactError(f"G5 input layer has no 2-D embedding.projection.weight; found {found}")
    width = int(proj.shape[1])
    per_pos = width // pos_dim
    if width % pos_dim or per_pos not in INPUT_CODES:
        raise ArtifactError(f"G5 input projection width {width} is neither 256 x {pos_dim} (raw KE2 table) nor "
                            f"64 x {pos_dim} (the 2,048 code); found {found}")
    return {"kind": INPUT_CODES[per_pos], "width": width, "per_position": per_pos, "n_embd": int(proj.shape[0]),
            "tensors": found}


def head_logits(model, h: torch.Tensor) -> torch.Tensor:
    """Logits [..., V] from final hidden states [..., n_embd]: G5's own `head(h)` call, for either known kind."""
    return model.head(h)


@dataclass
class Bundle:
    mode: str
    model: torch.nn.Module
    spec: dict
    artifacts: Any  # week2.artifacts.Artifacts
    special: dict
    selection: dict
    manifest: dict
    template_path: Path
    render_mod: Any
    device: str = "cpu"
    kv_cache: bool = False  # sample() through g5_decode (KV cache) instead of re-forwarding the whole sequence
    _template: Any = field(default=None, repr=False)

    # forward -------------------------------------------------------------------------------------
    def check_batch(self, ids: torch.Tensor, valid: torch.Tensor):
        if ids.dim() != 2 or ids.dtype != torch.long:
            raise ValueError("ids must be a [B, T] int64 tensor")
        if valid.shape != ids.shape or valid.dtype != torch.bool:
            raise ValueError("valid must be a bool tensor shaped like ids")
        if ids.shape[1] > self.spec["block_size"]:
            raise ValueError(f"sequence length {ids.shape[1]} exceeds block_size {self.spec['block_size']}")
        if ids.numel() and (int(ids.min()) < 0 or int(ids.max()) >= self.spec["vocab_size"]):
            raise ValueError("token id outside the vocabulary")
        if not bool(valid[:, 0].all()):
            raise ValueError("every row needs a valid first token (left padding is not supported)")
        if bool((valid[:, 1:] & ~valid[:, :-1]).any()):
            raise ValueError("valid must be a right-padded prefix mask: G5 attention has no padding mask")

    def forward(self, ids: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        """Main-head logits [B, T, V] from the delivered LanguageModel. Rows past `valid` are undefined."""
        self.check_batch(ids, valid)
        out = self.model(ids.to(self.device), valid.to(self.device))  # return_mtp=False -> main head tensor
        if not isinstance(out, torch.Tensor) or out.shape != (*ids.shape, self.spec["vocab_size"]):
            raise RuntimeError(f"G5 forward returned {type(out)} {getattr(out, 'shape', None)}, expected [B,T,V]")
        return out

    __call__ = forward

    # labels --------------------------------------------------------------------------------------
    @staticmethod
    def causal_targets(ids: torch.Tensor, valid: torch.Tensor):
        """Next-token targets: logits[:, t] predicts ids[:, t+1]; only pairs where both tokens are valid count."""
        return ids[:, 1:], valid[:, 1:] & valid[:, :-1]

    def token_nll(self, ids: torch.Tensor, valid: torch.Tensor, loss_mask: torch.Tensor | None = None):
        """(sum NLL, count) over supervised next-token targets; loss_mask[:, t] gates target ids[:, t]."""
        logits = self.forward(ids, valid)[:, :-1].float()
        tgt, m = self.causal_targets(ids.to(self.device), valid.to(self.device))
        if loss_mask is not None:
            m = m & loss_mask[:, 1:].to(self.device)
        if not bool(m.any()):
            raise ValueError("no supervised targets")
        nll = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]), tgt.reshape(-1), reduction="none")
        return (nll * m.reshape(-1)).sum(), int(m.sum())

    # chat format ---------------------------------------------------------------------------------
    def encode_generation_prefix(self, messages: list[dict], effort: str = "4k") -> list[int]:
        """G10 chat_template.jinja with add_generation_prompt=True, encoded with marker IDs kept."""
        import jinja2  # noqa: PLC0415
        if self._template is None:
            self._template = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(
                self.template_path.read_text(encoding="utf-8"))
        # render.py rejects marker text inside content and must agree with the template on the closed transcript.
        closed = self.render_mod.render(messages, effort=effort)
        if self._template.render(messages=messages, effort=effort, add_generation_prompt=False) != closed:
            raise ValueError("chat_template.jinja and render.py disagree on this transcript")
        text = self._template.render(messages=messages, effort=effort, add_generation_prompt=True)
        ids = self.artifacts.encode(text)  # G5: refuses any encoding that does not reproduce the UTF-8 exactly
        im_start = self.special["tokens"]["im_start"]["id"]
        if ids.count(im_start) != text.count(self.special["tokens"]["im_start"]["token"]):
            raise ValueError("im_start marker did not encode atomically")
        if ids[-len(self._assistant_tail()):] != self._assistant_tail():
            raise ValueError("generation prefix does not end with the assistant turn opener")
        if ids and ids[-1] in self.special["stop_ids"]:
            raise ValueError("generation prefix ends with a stop id")
        return ids

    def _assistant_tail(self) -> list[int]:
        return self.artifacts.encode("<|im_start|>assistant\n")

    def completion_bytes(self, ids: list[int]) -> bytes:
        """Exact bytes from the KE2 raw table; markers are kept (no skip_special_tokens)."""
        a = self.artifacts
        return b"".join(a.bytes[i, :int(a.lengths[i])].tobytes() for i in ids)

    def decode_completion(self, ids: list[int], cut_at_stop: bool = True, keep_stop: bool = True) -> str:
        """Text of a completion. cut_at_stop drops everything after the first stop id; keep_stop=False also drops
        that stop id itself (the reward view, see G10Codec). Interior markers such as <|think|> are always kept."""
        if cut_at_stop:
            for j, t in enumerate(ids):
                if t in self.special["stop_ids"]:
                    ids = ids[:j + 1] if keep_stop else ids[:j]
                    break
        return self.completion_bytes(ids).decode("utf-8", errors="replace")

    # sampling ------------------------------------------------------------------------------------
    @torch.no_grad()
    def sample(self, prompt: list[int], k: int, max_new: int, temperature: float,
               generator: torch.Generator | None, stop_ids: list[int] | None = None):
        """k completions of one prompt. Default: re-forward the growing sequence (G5 has no cache) and project only
        the last position through the head. With `kv_cache` set: rl-loop/g5_decode.py (prefill + cached steps).

        Returns (seq [k, P+max_new], completion_mask [k, max_new], stop_reason per row). The stop token itself is
        kept in the mask; everything after it is masked and filled with pad. The generator must live on the
        sampling device (no CPU generator for CUDA probabilities).
        """
        stop = list(self.special["stop_ids"] if stop_ids is None else stop_ids)
        if not prompt or k <= 0 or max_new <= 0:
            raise ValueError("need a non-empty prompt, k > 0 and max_new > 0")
        if len(prompt) + max_new > self.spec["block_size"]:
            raise ValueError(f"prompt {len(prompt)} + max_new {max_new} exceeds block_size {self.spec['block_size']}")
        if temperature > 0:
            if generator is None:
                raise ValueError("sampling with temperature > 0 needs an explicit generator")
            if torch.device(generator.device).type != torch.device(self.device).type:
                raise ValueError(f"generator on {generator.device}, model on {self.device}")
        if self.kv_cache:
            import g5_decode  # noqa: PLC0415  rl-loop/g5_decode.py
            return g5_decode.sample(self.model, list(prompt), k, max_new, temperature, generator, stop,
                                    self.special["pad_id"], self.device)
        was = self.model.training
        self.model.eval()
        dev = self.device
        seq = torch.tensor([prompt] * k, dtype=torch.long, device=dev)
        alive = torch.ones(k, dtype=torch.bool, device=dev)
        cmask = torch.zeros(k, max_new, dtype=torch.bool, device=dev)
        reason = ["length"] * k
        stop_t = torch.tensor(stop, dtype=torch.long, device=dev)
        pad = self.special["pad_id"]
        for t in range(max_new):
            valid = torch.ones_like(seq, dtype=torch.bool)
            self.check_batch(seq, valid)
            # only the last position is sampled: project it alone through the 131,072-row head (same values as
            # forward()[:, -1]; the full-sequence head was L times the work and memory at every step)
            logits = head_logits(self.model, self.model.hidden(seq, valid)[:, -1]).float()
            if temperature <= 0:
                nxt = logits.argmax(-1)
            else:
                nxt = torch.multinomial(torch.softmax(logits / temperature, -1), 1, generator=generator).squeeze(-1)
            nxt = torch.where(alive, nxt, torch.full_like(nxt, pad))
            cmask[:, t] = alive
            hit = alive & torch.isin(nxt, stop_t)
            for r in hit.nonzero().flatten().tolist():
                reason[r] = f"stop:{int(nxt[r])}"
            alive = alive & ~hit
            seq = torch.cat([seq, nxt[:, None]], 1)
            if not bool(alive.any()):
                seq = torch.cat([seq, torch.full((k, max_new - t - 1), pad, device=dev, dtype=torch.long)], 1)
                break
        self.model.train(was)
        return seq, cmask, reason

    @torch.no_grad()
    def sample_many(self, prompts: list[list[int]], k: int, max_new: int, temperature: float,
                    generator: torch.Generator | None, stop_ids: list[int] | None = None):
        """k completions of every prompt in one KV-cached decode (rl-loop/g5_decode.sample_many); same checks and
        per-prompt return contract as sample()."""
        stop = list(self.special["stop_ids"] if stop_ids is None else stop_ids)
        if not prompts or any(not p for p in prompts) or k <= 0 or max_new <= 0:
            raise ValueError("need non-empty prompts, k > 0 and max_new > 0")
        longest = max(len(p) for p in prompts)
        if longest + max_new > self.spec["block_size"]:
            raise ValueError(f"prompt {longest} + max_new {max_new} exceeds block_size {self.spec['block_size']}")
        if temperature > 0:
            if generator is None:
                raise ValueError("sampling with temperature > 0 needs an explicit generator")
            if torch.device(generator.device).type != torch.device(self.device).type:
                raise ValueError(f"generator on {generator.device}, model on {self.device}")
        import g5_decode  # noqa: PLC0415  rl-loop/g5_decode.py
        return g5_decode.sample_many(self.model, [list(p) for p in prompts], k, max_new, temperature, generator, stop,
                                     self.special["pad_id"], self.device)

    def policy(self):
        """A rl-loop Policy whose forward is the checked bundle.forward and whose sampling stops at every stop id."""
        from policy import Policy  # noqa: PLC0415  rl-loop/policy.py, unchanged

        bundle = self

        class Team5Policy(Policy):
            """eos_id is end_of_turn (used for length stats); sampling also stops at end_of_sequence."""

            @torch.no_grad()
            def sample(self, prompt, k, max_new, temperature=1.0, generator=None):
                # same compute dtype as training: under the trainer's bf16 autocast (train.autocast / fp32_master)
                # the sampler must see the same numerics, or the objective_v1 ratio measures a precision gap
                with self.autocast():
                    seq, cmask, _ = bundle.sample(prompt, k, max_new, temperature, generator)
                return seq, cmask

            @torch.no_grad()
            def sample_many(self, prompts, k, max_new, temperature=1.0, generator=None):
                with self.autocast():  # same compute dtype as sample() and the trainer
                    rolls = bundle.sample_many(prompts, k, max_new, temperature, generator)
                return [(seq, cmask) for seq, cmask, _ in rolls]

        return Team5Policy(self.model, lambda m, ids, mask: bundle.forward(ids, mask),
                           self.special["tokens"]["end_of_turn"]["id"], self.device)

    def codec(self, effort: str = "4k") -> "G10Codec":
        return G10Codec(self, effort)

    def to(self, device: str) -> "Bundle":
        self.model.to(device)
        self.device = device
        return self


class G10Codec:
    """What tasks.RewardEnvTask needs instead of an HF tokenizer: G10 generation prefix in, marker-keeping text out.

    encode_prompt(text) renders one user turn with chat_template.jinja (add_generation_prompt=True).
    decode_completion(ids) returns exact bytes from the KE2 raw table up to (not including) the first stop id.
    The terminating stop marker is consumed here, by the format layer: chat_template.jinja writes content and
    <|im_end|> with no newline between them, and parsers then fail on it ("```<|im_end|>" is not a closing fence in
    rl/verifier.extract_code; a diff line ending in "<|im_end|>" is a corrupt patch for git apply). Interior markers
    (<|think|>, <|tool_call|> ...) are kept for the parser. A completion with no stop id is returned whole.
    """

    def __init__(self, bundle: Bundle, effort: str = "4k"):
        bundle.render_mod.effort_limit(effort)  # render.py's own effort check
        self.bundle, self.effort = bundle, effort
        self.pad_token_id = bundle.special["pad_id"]
        self.eos_token_id = bundle.special["tokens"]["end_of_turn"]["id"]
        self.stop_ids = list(bundle.special["stop_ids"])
        self.adapter_result: Result | None = None  # set by build_policy_and_codec

    def encode_prompt(self, text: str) -> list[int]:
        return self.bundle.encode_generation_prefix([{"role": "user", "content": text}], effort=self.effort)

    def decode_completion(self, ids: list[int]) -> str:
        return self.bundle.decode_completion(list(ids), cut_at_stop=True, keep_stop=False)


class WaitingForArtifact(RuntimeError):
    """Raised by build_policy_and_codec when the G5 checkpoint has not been delivered. Nothing may train."""

    def __init__(self, result: "Result"):
        super().__init__(f"{result.status}: {'; '.join(result.reasons)}")
        self.result = result


def build_policy_and_codec(adapter_config, device: str = "cpu", effort: str = "4k", allow_fixture: bool = False,
                           kv_cache: bool = False):
    """For train.py: (Policy, G10Codec). WAITING raises WaitingForArtifact; a fixture needs allow_fixture=True."""
    result = build(adapter_config, device=device)
    if result.status == WAITING:
        raise WaitingForArtifact(result)
    if result.status in (FIXTURE_READY, REHEARSAL_READY) and not allow_fixture:
        raise ArtifactError(f"adapter status is {result.status} (not a G5 delivery); set model.allow_fixture_smoke: "
                            "true for a smoke or rehearsal run (its output is never a result)")
    bundle = result.require_bundle()
    bundle.kv_cache = bool(kv_cache)
    codec = bundle.codec(effort)
    codec.adapter_result = result
    return bundle.policy(), codec


@dataclass
class Result:
    status: str
    mode: str
    reasons: list[str]
    manifest: dict
    bundle: Bundle | None = None

    def require_bundle(self) -> Bundle:
        if self.bundle is None:
            raise RuntimeError(f"{self.status}: no model was built ({'; '.join(self.reasons)})")
        return self.bundle


def require_learning_ready(result: Result) -> Bundle:
    """Gate for anything that writes a learning/eval report: only a READY real G5 bundle passes."""
    if result.status != READY or result.mode not in ("real", "run_folder") or result.bundle is None or (
            result.mode == "run_folder" and result.manifest.get("origin") != "g5_delivery"):
        raise RuntimeError(f"refusing a learning report from status={result.status} mode={result.mode}; "
                           "fixture and waiting bundles never produce learning results")
    return result.bundle


def _load_render(team10: Path):
    import importlib.util  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location("g10_render_adapter", team10 / "chat-format" / "render.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_config(config) -> tuple[dict, Path]:
    if isinstance(config, (str, Path)):
        import yaml  # noqa: PLC0415
        p = Path(config).resolve()
        if not p.is_file():
            raise ArtifactError(f"adapter config missing: {p}")
        return yaml.safe_load(p.read_text(encoding="utf-8")), p.parent
    if isinstance(config, dict):
        return copy.deepcopy(config), Path(config.get("_base", ".")).resolve()
    raise ArtifactError("config must be a dict or a YAML path")


def build(config, device: str = "cpu") -> Result:
    """Validate every artifact and build the bundle. Raises ArtifactError on any inconsistency."""
    cfg, base = load_config(config)  # deep copy: the caller's dict is never touched
    cfg.pop("_base", None)
    extra = set(cfg) - TOP_KEYS
    if extra:
        raise ArtifactError(f"unknown adapter config keys {sorted(extra)}")
    mode = cfg.get("mode")
    if mode not in ("real", "fixture", "run_folder"):
        raise ArtifactError("mode must be 'real', 'fixture' or 'run_folder'")
    if mode == "run_folder":
        return _build_run_folder(cfg, base, device)
    if cfg.get("run_folder"):
        raise ArtifactError("run_folder is only read in run_folder mode")
    if mode == "real" and cfg.get("fixture_overrides"):
        raise ArtifactError("fixture_overrides are only allowed in fixture mode")

    g5src = _load_g5(_need(cfg, "g5", "config"), base)
    rcfg = _resolve(g5src, cfg["g5"], mode, cfg.get("fixture_overrides"))
    spec = rcfg["model"]
    tok = _load_tokenizer(_need(cfg, "tokenizer", "config"), base)
    manifest = {
        "adapter": "team5_adapter v1", "mode": mode,
        "g5": {"commit": g5src["commit"], "files_sha256": g5src["files_sha256"],
               "arm": cfg["g5"]["arm"], "resolution": cfg["g5"]["resolution"],
               "provenance": rcfg["provenance"], "approval": rcfg["approval"]},
        "model_spec": spec, "model_spec_sha256": _sha_json(spec),
        "fixture_overrides": cfg.get("fixture_overrides"),
        "tokenizer": {"sha256": tok["sha256"], "chat_template_sha256": tok["template_sha256"]},
    }

    ck = _need(cfg, "checkpoint", "config")
    ck_path = (base / ck["path"]) if ck.get("path") else None
    kcfg = _need(cfg, "ke2", "config")
    if ck_path is None or not ck_path.is_file():
        if mode == "real":
            reasons = [f"checkpoint not present: {ck_path}"]
            if not kcfg.get("table") or not (base / kcfg["table"]).is_file():
                reasons.append("KE2 table from the checkpoint manifest not present")
            manifest["status"] = WAITING
            return Result(WAITING, mode, reasons, manifest)
        raise ArtifactError(f"checkpoint missing: {ck_path}")
    if ck.get("format") not in CHECKPOINT_FORMATS:
        raise ArtifactError(f"checkpoint.format must be one of {CHECKPOINT_FORMATS}")
    ck_sha = sha256_file(ck_path)
    if ck_sha != _hex(_need(ck, "sha256", "checkpoint"), 64, "checkpoint.sha256"):
        raise ArtifactError(f"checkpoint hash mismatch: {ck_sha}")

    art = _load_ke2(kcfg, base, tok, g5src)
    if spec["vocab_size"] != len(art.lengths) or spec["vocab_size"] != kcfg["vocab_size"]:
        raise ArtifactError(f"vocabulary mismatch: model {spec['vocab_size']}, KE2/tokenizer {len(art.lengths)}, "
                            f"config {kcfg['vocab_size']}")
    if spec["ke_max_pos"] != art.pos_dim:
        raise ArtifactError(f"model ke_max_pos {spec['ke_max_pos']} != KE2 pos_dim {art.pos_dim}")
    special = _special_map(_need(cfg, "special_tokens", "config"), art)

    sd, is_fixture_ckpt, ck_extra = _read_checkpoint(ck_path, ck["format"])
    if mode == "real" and is_fixture_ckpt:
        raise ArtifactError("real mode refuses a checkpoint carrying the G10 fixture marker")
    if mode == "fixture" and not is_fixture_ckpt:
        raise ArtifactError("fixture mode only loads checkpoints carrying the fixture marker")

    return _finish(mode, cfg, g5src, spec, tok, art, special, sd, is_fixture_ckpt, ck_extra,
                   {"path_name": ck_path.name, "sha256": ck_sha, "format": ck["format"]}, manifest, device)


def check_keys(model, sd: dict) -> set:
    """The checkpoint must carry exactly the model's state_dict keys, checked BEFORE load_state_dict: Team 5's MoE fills a
    missing `router_bias` with zeros on load (#750), so a strict load alone accepts a checkpoint that lost the bias and
    routes differently. Returns the key set."""
    want = set(model.state_dict())
    have = set(sd)
    missing, unexpected = sorted(want - have), sorted(have - want)
    if missing or unexpected:
        raise ArtifactError(f"checkpoint keys do not match the G5 model: missing {missing[:5]} ({len(missing)}), "
                            f"unexpected {unexpected[:5]} ({len(unexpected)})")
    return want


def _finish(mode, cfg, g5src, spec, tok, art, special, sd, is_fixture_ckpt, ck_extra, ck_info, manifest, device,
            status=None, require_probe=None):
    """Shared tail of every mode: build G5's LanguageModel, load and check the state dict, select trainables, probe."""
    mods = g5src["mods"]
    torch_state = torch.random.get_rng_state()
    model = mods["week2.model"].LanguageModel(spec, art.bytes, art.lengths)  # init values are overwritten below
    torch.random.set_rng_state(torch_state)  # building must not advance the caller's RNG
    want = check_keys(model, sd)
    ref = model.state_dict()
    bad = [(k, tuple(sd[k].shape), tuple(ref[k].shape)) for k in sorted(want) if tuple(sd[k].shape) != tuple(ref[k].shape)]
    if bad:
        if any(k.startswith(("head.", "embedding.")) for k, _, _ in bad):
            raise ArtifactError(f"vocabulary/KE2 shape mismatch in checkpoint: {bad[:3]}")
        raise ArtifactError(f"checkpoint tensor shapes differ from the G5 model: {bad[:3]}")
    inp = input_access(model, art.pos_dim)  # refuses an input layer G10 cannot check (by name and shape)
    # The KE2 code table is a buffer of the checkpoint; it must be exactly the validated table.
    if not torch.equal(sd["embedding.rows"].to(torch.uint8), torch.as_tensor(art.bytes)):
        raise ArtifactError("checkpoint KE2 rows differ from the validated KE2 table")
    if not torch.equal(sd["embedding.lengths"].long(), torch.as_tensor(art.lengths).long()):
        raise ArtifactError("checkpoint KE2 lengths differ from the validated KE2 table")
    for k in want:
        if sd[k].dtype != ref[k].dtype:
            raise ArtifactError(f"dtype of {k} is {sd[k].dtype}, G5 model stores {ref[k].dtype}")
    model.load_state_dict(sd, strict=True)
    router = router_state(model, mods["week2.model"].MoE)  # refuses a non-zero router_bias the config would ignore
    head = head_access(model)  # raises on a head of unknown kind
    if head["tied"]:
        raise ArtifactError("output head unexpectedly tied to the KE2 projection")
    if head["vocab_size"] != spec["vocab_size"]:
        raise ArtifactError(f"output head vocabulary {head['vocab_size']} != model spec {spec['vocab_size']}")
    if (model.mtp_head is not None) != bool(spec.get("mtp")):
        raise ArtifactError("MTP head presence disagrees with the resolved spec")
    model.requires_grad_(True)
    selection = _select(model, mods["week2.model"].MoE, _need(cfg, "trainable", "config"))
    for n, p in model.named_parameters():
        p.requires_grad_(n in selection["trainable_names"])
    model.eval()

    inv = _inventory(model)
    manifest.update({
        "checkpoint": {**ck_info, "fixture_marker": is_fixture_ckpt,
                       **{k: v for k, v in ck_extra.items() if k != "metadata"}},
        "ke2": art.identity() | {"table_file_sha256_config": cfg["ke2"]["table_file_sha256"]},
        "special_tokens": special,
        "inventory": inv, "inventory_sha256": _sha_json(inv),
        "n_parameters": sum(p.numel() for p in model.parameters()),
        "model_hash_g5": mods["train_week2"].model_hash(model),
        "selection": selection,
        "head": {"kind": head["kind"], "tied": False, "mtp_head": model.mtp_head is not None,
                 "forward_returns": "main head logits"},
        "input": {k: v for k, v in inp.items() if k != "tensors"},
        "router": router,
    })
    template = _load_render(Path(__file__).resolve().parents[1])
    bundle = Bundle(mode, model, spec, art, special, selection, manifest, tok["template_path"], template)
    bundle.to(device)

    probe = cfg.get("probe")
    require_probe = (mode == "real") if require_probe is None else require_probe
    if probe is None and require_probe:
        raise ArtifactError("real mode needs probe.ids and probe.expected_mean_nll supplied with the G5 checkpoint")
    if probe is not None:
        ids = torch.tensor([_need(probe, "ids", "probe")], dtype=torch.long)
        with torch.no_grad():
            s, n = bundle.token_nll(ids, torch.ones_like(ids, dtype=torch.bool))
        got = float(s) / n
        manifest["probe"] = {"ids_sha256": _sha_json(probe["ids"]), "mean_nll": got, "targets": n}
        if probe.get("expected_mean_nll") is not None:
            exp, atol = float(probe["expected_mean_nll"]), float(probe.get("atol", 1e-4))
            if not math.isfinite(got) or abs(got - exp) > atol:
                raise ArtifactError(f"probe mean NLL {got:.6f} != expected {exp:.6f} (atol {atol})")
            manifest["probe"]["verified_against"] = exp
        elif require_probe:
            raise ArtifactError("real mode needs probe.expected_mean_nll")
    if status is None:
        status = READY if mode == "real" else FIXTURE_READY
    manifest["status"] = status
    manifest["learning_report_allowed"] = status == READY
    return Result(status, mode, [], manifest, bundle)


def _build_run_folder(cfg: dict, base: Path, device: str) -> Result:
    """mode run_folder: everything about the model comes from what Team 5's trainer wrote, checked against the
    pinned G5 import, the tokenizer and the KE2 table."""
    for key in ("checkpoint", "fixture_overrides"):
        if cfg.get(key):
            raise ArtifactError(f"run_folder mode takes the model from the run folder; remove '{key}'")
    rf = _need(cfg, "run_folder", "config")
    origin = _need(rf, "origin", "run_folder")
    if origin not in RUN_FOLDER_ORIGINS:
        raise ArtifactError(f"run_folder.origin must be one of {RUN_FOLDER_ORIGINS}")
    folder = (base / _need(rf, "path", "run_folder")).resolve()
    man_path, ck_path, sum_path = folder / "manifest.json", folder / "checkpoint.pt", folder / "summary.json"
    for p_ in (man_path, ck_path, sum_path):
        if not p_.is_file():
            raise ArtifactError(f"run folder is missing {p_.name}: {folder}")
    man_sha = sha256_file(man_path)
    if man_sha != _hex(_need(rf, "manifest_sha256", "run_folder"), 64, "run_folder.manifest_sha256"):
        raise ArtifactError(f"run folder manifest hash mismatch: {man_sha}")
    ck_sha = sha256_file(ck_path)
    if ck_sha != _hex(_need(rf, "checkpoint_sha256", "run_folder"), 64, "run_folder.checkpoint_sha256"):
        raise ArtifactError(f"run folder checkpoint hash mismatch: {ck_sha}")
    g5_manifest = json.loads(man_path.read_text(encoding="utf-8"))
    summary = json.loads(sum_path.read_text(encoding="utf-8"))
    launch_path = folder / "G10_LAUNCH.json"
    launch = json.loads(launch_path.read_text(encoding="utf-8")) if launch_path.is_file() else None

    g5src = _load_g5(_need(cfg, "g5", "config"), base)
    sources = g5_manifest.get("sources") or {}
    for name, rel in RUN_FOLDER_SOURCE_FILES.items():
        want = g5src["files_sha256"].get(rel) or sha256_file(g5src["team"] / rel)
        if sources.get(name) != want:
            raise ArtifactError(f"run folder was trained with a different {name} ({sources.get(name)}) than the "
                                f"pinned G5 import ({want})")
    for name, rel in RUN_FOLDER_SOURCE_FILES_IF_RECORDED.items():
        if name not in sources:
            continue
        here = g5src["team"] / rel
        want = g5src["files_sha256"].get(rel) or (sha256_file(here) if here.is_file() else None)
        if sources[name] != want:
            raise ArtifactError(f"run folder was trained with a different {name} ({sources[name]}) than the pinned G5 "
                                f"import ({want or 'file missing'})")
    rcfg = copy.deepcopy(_need(g5_manifest, "config", "manifest.json"))
    errors = g5src["mods"]["week2.config"].validate(rcfg)
    if errors:
        raise ArtifactError("G5 validate() rejected the run folder's config: " + "; ".join(errors))
    spec = rcfg["model"]
    smoke = bool(g5_manifest.get("smoke")) or g5_manifest.get("status") != "AGREED_BASELINE_RUN"
    if origin == "g5_delivery" and smoke:
        raise ArtifactError(f"g5_delivery needs a non-smoke AGREED_BASELINE_RUN manifest, got "
                            f"status={g5_manifest.get('status')} smoke={g5_manifest.get('smoke')}")
    tok = _load_tokenizer(_need(cfg, "tokenizer", "config"), base)
    want_art = _need(g5_manifest, "artifacts", "manifest.json")
    if want_art.get("tokenizer_sha256") != tok["sha256"]:
        raise ArtifactError(f"run folder used tokenizer {want_art.get('tokenizer_sha256')}, config has {tok['sha256']}")
    kcfg = _need(cfg, "ke2", "config")
    art = _load_ke2(kcfg, base, tok, g5src)
    if want_art.get("table_content_sha256") != art.table_content_sha:
        raise ArtifactError("run folder used a different KE2 table content")
    if spec["vocab_size"] != len(art.lengths) or spec["ke_max_pos"] != art.pos_dim:
        raise ArtifactError("run folder spec disagrees with the tokenizer / KE2 table")
    special = _special_map(_need(cfg, "special_tokens", "config"), art)
    sd, is_fixture_ckpt, ck_extra = _read_checkpoint(ck_path, "g5_train_week2_pt")
    if is_fixture_ckpt:
        raise ArtifactError("run_folder mode refuses a checkpoint carrying the G10 fixture marker")
    if ck_extra.get("identity_sha256") != g5_manifest.get("identity_sha256"):
        raise ArtifactError("checkpoint identity_sha256 differs from the run folder manifest")
    manifest = {
        "adapter": "team5_adapter v1", "mode": "run_folder", "origin": origin,
        "g5": {"commit": g5src["commit"], "files_sha256": g5src["files_sha256"],
               "provenance": rcfg.get("provenance"), "approval": rcfg.get("approval")},
        "run_folder": {"manifest_sha256": man_sha, "identity_sha256": g5_manifest.get("identity_sha256"),
                       "g5_status": g5_manifest.get("status"), "smoke": g5_manifest.get("smoke"),
                       "summary_status": summary.get("status"), "steps": summary.get("steps"),
                       "g10_launch_patches": (launch or {}).get("patches")},
        "model_spec": spec, "model_spec_sha256": _sha_json(spec), "fixture_overrides": None,
        "tokenizer": {"sha256": tok["sha256"], "chat_template_sha256": tok["template_sha256"]},
    }
    status = READY if origin == "g5_delivery" else REHEARSAL_READY
    result = _finish("run_folder", cfg, g5src, spec, tok, art, special, sd, False, ck_extra,
                     {"path_name": ck_path.name, "sha256": ck_sha, "format": "g5_train_week2_pt"}, manifest, device,
                     status=status, require_probe=origin == "g5_delivery")
    if result.manifest["model_hash_g5"] != summary.get("final_model_sha256"):
        raise ArtifactError("G5 model_hash of the loaded model differs from summary.json final_model_sha256")
    result.manifest["learning_report_allowed"] = status == READY
    return result


# --- export / reload ----------------------------------------------------------------------------------

def export_state(bundle: Bundle, out_path: Path) -> str:
    """Write the bundle's full state dict as safetensors. Keeps the fixture marker on fixture bundles."""
    from safetensors.torch import save_file  # noqa: PLC0415
    meta = {"g5_commit": bundle.manifest["g5"]["commit"], "source_checkpoint_sha256": bundle.manifest["checkpoint"]["sha256"]}
    if bundle.mode == "fixture":
        meta[FIXTURE_MARKER_KEY] = FIXTURE_MARKER_VALUE
    sd = {k: v.detach().cpu().contiguous() for k, v in bundle.model.state_dict().items()}
    save_file(sd, str(out_path), metadata=meta)
    return sha256_file(out_path)


def manifest_json(result: Result) -> str:
    return json.dumps(result.manifest, indent=2, sort_keys=True, default=str)
