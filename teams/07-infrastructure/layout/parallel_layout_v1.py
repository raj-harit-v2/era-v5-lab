#!/usr/bin/env python3
"""Parallel layout v1: memory and traffic per device for Team 5's model, with config v1's decisions.

In simple words: v0 (parallel_layout.py) counts Team 6's model with AdamW. The model that config v1 trains is
Team 5's week-2 model (teams/05-architecture/harness/week2/model.py) with Muon. v1 counts that model: no
biases, RMSNorm, SwiGLU experts with an explicit expert width, a KE2 projection, an untied head, and Muon's
one momentum buffer on the block matrices. It reads the sizes from a Team 5 test arm (T2 or T3; config v1 has
no sizes yet) and checks them against config v1's decisions. It flags every layout that splits a weight
matrix, because Muon orthogonalizes whole matrices and no distributed Muon exists in the lab.

    python layout/parallel_layout_v1.py --arm ../05-architecture/configs/arms/t2.yaml --world 1 --markdown
    python layout/parallel_layout_v1.py --arm ../05-architecture/configs/arms/t3.yaml \
           --decisions <config_v1.yaml> --layout b=1,m=8 --layout b=8,m=1 --device-gib 80

The numbers are formulas (results/layouts.md, "How v1 counts"), nothing measured. The activation terms
were fitted to the tensors autograd saves for Team 5's model on CPU (test_parallel_layout_v1.py); the CUDA
attention-score term is an assumption that the job requests check.

Needs PyYAML, and Team 5's harness folder (its config resolver is pure Python). Torch only for the tests.
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TEAM5 = HERE.parents[1] / "05-architecture"
sys.path.insert(0, str(TEAM5 / "harness"))
from week2.config import load_runtime  # noqa: E402  Team 5's own arm resolver: explicit expert width, no ratio fallback

GIB = 1024 ** 3
N_BYTES = 256                      # KE2 codec: 256 byte values per byte position
DEFAULT_DECISIONS = TEAM5 / "configs" / "config_v1.yaml"

# Attention-score bytes kept per (query, key, head) for one sequence, by where the model runs.
#   cuda  bf16 autocast: the eager scores are bf16, softmax runs in fp32 under CUDA autocast (4 bytes kept), then
#         .to(bf16) for the product with V (2 bytes kept): 6. Assumed from PyTorch's CUDA autocast op list.
#   cpu   bf16 autocast: softmax stays bf16, one 2-byte tensor kept (measured by the test).
#   fp32  one 4-byte softmax output kept (measured by the test).
SCORE_BYTES = {("cuda", "bf16"): 6, ("cpu", "bf16"): 2, ("cuda", "fp32"): 4, ("cpu", "fp32"): 4}


# ---------------------------------------------------------------- the model shape
@dataclass
class Shape:
    vocab: int
    seq: int
    layers: int
    d: int
    n_head: int
    n_kv: int
    ffn_hidden: int                # width of every expert, routed and shared (Team 5 moe.ffn_hidden)
    n_exp: int
    top_k: int
    n_shared: int
    ke_pos: int                    # KE2 byte positions P
    mtp: bool = False
    optimizer: str = "muon"        # muon | adamw (config v1: muon)
    dtype: str = "bf16"            # bf16 (fp32 weights, bf16 autocast) | fp32
    source: str = ""

    @property
    def hd(self) -> int:
        return self.d // self.n_head

    def problems(self) -> list:
        p = []
        if self.d % self.n_head:
            p.append(f"d {self.d} is not divisible by n_head {self.n_head}")
        if self.n_kv < 1 or self.n_head % self.n_kv:
            p.append(f"n_kv {self.n_kv} must divide n_head {self.n_head}")
        if not 1 <= self.top_k <= self.n_exp:
            p.append(f"top_k {self.top_k} is outside 1..{self.n_exp}")
        if self.optimizer not in ("muon", "adamw"):
            p.append(f"optimizer {self.optimizer!r} is muon or adamw")
        if self.dtype not in ("bf16", "fp32"):
            p.append(f"dtype {self.dtype!r} is bf16 or fp32")
        return p


# config v1 key -> (Shape field, Team 5 runtime value).  PR 447 key names: moe.n_shared, model.d_ff.
DECISION_KEYS = {
    "tokenizer.vocab_size": "vocab", "data.seq_len": "seq", "model.n_layer": "layers", "model.d_model": "d",
    "model.n_head": "n_head", "model.n_kv_head": "n_kv", "model.d_ff": "ffn_hidden", "moe.n_expert": "n_exp",
    "moe.top_k": "top_k", "moe.n_shared": "n_shared", "embedding.pos_dim": "ke_pos", "optim.name": "optimizer",
    "precision": "dtype",
}


def shape_from_arm(arm: str) -> tuple:
    """Team 5's resolver turns the arm into the model the harness builds. Only the v0 attention is counted."""
    cfg = load_runtime(Path(arm))
    m = cfg["model"]
    if m.get("attn_impl") != "eager" or m.get("attn_gate") or m.get("attn_sink") or m.get("attn_window") \
            or any(x != "G" for x in (m.get("attn_pattern") or [])):
        raise SystemExit(f"{arm}: v1 counts the v0 attention only (eager, no gate, sink or window)")
    if m.get("reversible"):
        raise SystemExit(f"{arm}: the reversible stack is not Team 5's harness model")
    moe = m["moe"]
    s = Shape(vocab=m["vocab_size"], seq=m["block_size"], layers=m["n_layer"], d=m["n_embd"], n_head=m["n_head"],
              n_kv=m["n_kv_head"], ffn_hidden=moe["ffn_hidden"], n_exp=moe["num_experts"], top_k=moe["top_k"],
              n_shared=moe["num_shared"], ke_pos=m["ke_max_pos"], mtp=bool(m["mtp"]),
              optimizer=cfg["optim"]["name"], dtype=cfg["run"]["dtype"], source=str(arm))
    return s, cfg["run"]


def apply_decisions(s: Shape, path: str) -> tuple:
    """Config v1 decides; the arm gives what config v1 leaves empty. A shape value that disagrees stops the
    calculator. The optimizer is a decision, not a shape: config v1's optimizer replaces the arm's, with a note."""
    settings = {x["key"]: x.get("value") for x in (yaml.safe_load(Path(path).read_text()) or {})["settings"]}
    notes, wrong = [], []
    for key, field in DECISION_KEYS.items():
        want = settings.get(key)
        have = getattr(s, field)
        if want is None:
            notes.append(f"{key}: empty in config v1, arm value {have} (test size)")
            continue
        if field == "optimizer" and want != have:
            notes.append(f"optim.name: config v1 says {want}, the arm trains {have}; counted as {want}")
            s = replace(s, optimizer=want)
        elif field == "dtype" and want != have:
            wrong.append(f"precision {want} vs arm dtype {have}")
        elif want != have:
            wrong.append(f"{key} {want} vs arm {have}")
    if settings.get("attention.impl") not in (None, "eager"):
        wrong.append(f"attention.impl {settings['attention.impl']} vs arm eager")
    if settings.get("embedding.type") not in (None, "kronecker"):
        wrong.append(f"embedding.type {settings['embedding.type']} vs arm Kronecker KE2")
    if wrong:
        raise SystemExit(f"{s.source} disagrees with {path}: " + "; ".join(wrong))
    return s, notes


def load_shape(arm: str, decisions: str = None, sets: dict = None) -> tuple:
    s, run = shape_from_arm(arm)
    notes = []
    if decisions:
        s, notes = apply_decisions(s, decisions)
    return replace(s, **(sets or {})), run, notes


# ---------------------------------------------------------------- parameter counts (exact for Team 5 week2/model.py)
def matrices(s: Shape) -> dict:
    """Every 2D block weight of one layer, (rows, cols), by group. All but the router are the Muon matrices (uses_muon);
    the MoE router is on AdamW (G5, 21 Nov, TSAI's recommendation)."""
    f, kv = s.ffn_hidden, s.n_kv * s.hd
    attn = [(s.d, s.d), (kv, s.d), (kv, s.d), (s.d, s.d)]                         # q, k, v, o
    swiglu = [(f, s.d), (f, s.d), (s.d, f)]                                         # gate, up, down
    return {"attn": attn, "router": [(s.n_exp, s.d)], "shared": swiglu * s.n_shared, "experts": swiglu * s.n_exp}


def param_counts(s: Shape) -> dict:
    mats = {k: sum(r * c for r, c in v) for k, v in matrices(s).items()}
    dense_matrix = mats["attn"] + mats["router"] + mats["shared"]
    norms = 2 * s.d                                                                 # n1, n2 (RMSNorm gains)
    dense_layer = dense_matrix + norms
    expert_layer = mats["experts"]
    embed = N_BYTES * s.ke_pos * s.d                                                # KE2 projection, no bias
    head = s.vocab * s.d * (2 if s.mtp else 1) + s.d                                # head (+ mtp head) + final norm
    total = s.layers * (dense_layer + expert_layer) + embed + head
    muon = s.layers * (dense_matrix - mats["router"] + expert_layer) if s.optimizer == "muon" else 0
    swiglu = 3 * s.d * s.ffn_hidden
    active = s.layers * (mats["attn"] + mats["router"] + (s.top_k + s.n_shared) * swiglu) + s.vocab * s.d * (
        2 if s.mtp else 1)
    return {"dense_layer": dense_layer, "dense_matrix": dense_matrix, "expert_layer": expert_layer, "embed": embed,
            "head": head, "total": total, "routed_experts": s.layers * expert_layer, "muon": muon,
            "adamw": total - muon, "active_matmul": active}


# ---------------------------------------------------------------- the layout
@dataclass
class Layout:
    dp: int = 1
    tp: int = 1
    pp: int = 1
    ep: int = 1                  # taken from the dp x cp devices
    cp: int = 1
    zero: int = 0                # 0 DDP | 1 | 2 | 3 (= FSDP full shard)
    shard: int = 0               # ZeRO-3 only: shard group size (HSDP)
    b: int = 1                   # micro-batch: sequences per device per forward (Team 5 run.micro_batch_size)
    m: int = 1                   # micro-batches per optimizer step (Team 5 batch_size / micro_batch_size)
    recompute: str = "none"      # none | selective | full (Team 5's harness has none)

    @property
    def world(self) -> int:
        return self.dp * self.tp * self.pp * self.cp

    def name(self) -> str:
        parts = [f"{k}={v}" for k, v in (("dp", self.dp), ("tp", self.tp), ("pp", self.pp), ("ep", self.ep),
                                          ("cp", self.cp)) if v > 1] or ["single"]
        if self.zero:
            parts.append(f"zero={self.zero}" + (f"/shard={self.shard}" if self.shard else ""))
        if self.recompute != "none":
            parts.append(f"recompute={self.recompute}")
        return ",".join(parts)


def parse_layout(text: str) -> Layout:
    lay = Layout()
    types = {f.name: f.type for f in fields(Layout)}
    for item in filter(None, (t.strip() for t in text.split(","))):
        key, sep, val = item.partition("=")
        if not sep or key not in types:
            raise SystemExit(f"layout item {item!r}: use key=value with key in {', '.join(types)}")
        setattr(lay, key, val if types[key] == "str" else int(val))
    return lay


def layout_problems(s: Shape, lay: Layout, world: int = 0) -> list:
    p = []
    if world and lay.world != world:
        p.append(f"dp x tp x pp x cp = {lay.world}, not the {world} devices")
    if min(lay.dp, lay.tp, lay.pp, lay.ep, lay.cp, lay.b, lay.m) < 1:
        return p + ["every degree, b and m must be at least 1"]
    if s.n_head % lay.tp or s.n_kv % lay.tp:
        p.append(f"tp {lay.tp} must divide n_head {s.n_head} and n_kv {s.n_kv}")
    if s.ffn_hidden % lay.tp:
        p.append(f"tp {lay.tp} must divide the expert width {s.ffn_hidden}")
    if lay.pp > s.layers:
        p.append(f"pp {lay.pp} is more than the {s.layers} layers")
    if s.n_exp % lay.ep:
        p.append(f"ep {lay.ep} must divide the {s.n_exp} routed experts")
    if (lay.dp * lay.cp) % lay.ep:
        p.append(f"ep {lay.ep} must divide dp x cp = {lay.dp * lay.cp}")
    if s.seq % lay.cp:
        p.append(f"cp {lay.cp} must divide the sequence length {s.seq}")
    if lay.zero not in (0, 1, 2, 3):
        p.append("zero is 0, 1, 2 or 3")
    if lay.shard and (lay.zero != 3 or (lay.dp * lay.cp) % lay.shard):
        p.append("shard (HSDP) needs zero=3 and must divide dp x cp")
    if lay.recompute not in ("none", "selective", "full"):
        p.append("recompute is none, selective or full")
    if lay.pp > 1 and lay.m < lay.pp:
        p.append(f"m {lay.m} < pp {lay.pp}: the pipeline never fills (bubble over 50%)")
    return p


def muon_check(s: Shape, lay: Layout) -> str:
    """Muon orthogonalizes each whole matrix. A layout that splits a matrix across devices needs a distributed
    Muon (gather the matrix, or give whole matrices to ranks), which the lab does not have."""
    if s.optimizer != "muon":
        return "n/a"
    split = [x for x, on in (("ZeRO shards", lay.zero >= 1), ("tp splits", lay.tp > 1)) if on]
    return "needs distributed Muon (" + ", ".join(split) + " matrices)" if split else "ok"


def runs_today(lay: Layout) -> str:
    """Team 5's harness (train_week2.py) trains one device, no recompute: only b and m change."""
    return "yes" if lay.world == 1 and lay.ep == 1 and lay.zero == 0 and lay.recompute == "none" else "no script"


# ---------------------------------------------------------------- memory per device
def activation_terms(s: Shape, lay: Layout, device: str = "cuda") -> dict:
    """Bytes autograd keeps for one micro-batch on one device, by part (fitted to Team 5's model on CPU, see
    the test). Tokens per device T = b * s / cp; sequence parallel divides the token terms by tp.
      per layer, per token   bf16: 34 d + top_k (10 d + 8 f) + shared (4 d + 8 f) + 40 + score_bytes * heads * s
                             fp32: 40 d + top_k (12 d + 16 f) + shared 16 f + 40 + 4 * heads * s
      per layer, fixed       mask s * s_c (bool) + rotary 16 * s_c * hd (fp32 angle products)
      outside the blocks     bf16 10 d, fp32 12 d per token (embedding, final norm); log-softmax 4 V per token
    A routed pass costs more than a shared one: the gathered input rows and the gate-weighted output are kept.
    The 40 is the per-token scalars (norm scales, router choices and gates).
    """
    T = lay.b * s.seq / lay.cp
    sc = s.seq / lay.cp
    d, f = s.d, s.ffn_hidden
    score = SCORE_BYTES[(device, s.dtype)] * s.n_head * s.seq / lay.tp            # keys: the whole sequence
    if s.dtype == "bf16":
        tok = (34 * d + s.top_k * (10 * d + 8 * f) + s.n_shared * (4 * d + 8 * f) + 40) / lay.tp
    else:
        tok = (40 * d + s.top_k * (12 * d + 16 * f) + s.n_shared * 16 * f + 40) / lay.tp
    fixed = s.seq * sc + 16 * sc * s.hd
    if lay.recompute == "full":
        layer = 4 * T * s.d / lay.tp                                                # the fp32 residual input only
    elif lay.recompute == "selective":
        layer = T * tok + 16 * sc * s.hd
    else:
        layer = T * (tok + score) + fixed
    heads = 2 if s.mtp else 1
    return {"per_layer": layer, "outside": T * (10 if s.dtype == "bf16" else 12) * s.d / lay.tp,
            "log_softmax": 4 * T * s.vocab / lay.tp * heads,
            # not saved by autograd but alive at the end of forward: the logits the loop keeps (bf16: 2 bytes,
            # plus the fp32 copy that token_nll's .float() makes for cross_entropy; fp32: the 4-byte logits).
            "logits_held": (6 if s.dtype == "bf16" else 4) * T * s.vocab / lay.tp * heads,
            "full_layer": T * (tok + score) + fixed}


def memory(s: Shape, lay: Layout, device: str = "cuda") -> dict:
    """Bytes per device on the busiest pipeline stage (the larger of the first and the last)."""
    return max(memory_stages(s, lay, device), key=lambda row: row["total"])


def memory_stages(s: Shape, lay: Layout, device: str = "cuda") -> list:
    pc = param_counts(s)
    w = g = 4                                       # Team 5 keeps fp32 weights and grads (bf16 only under autocast)
    muon_b, adam_b = 4, 8                           # Muon: one fp32 momentum buffer; AdamW: two fp32 moments
    exp_b = muon_b if s.optimizer == "muon" else adam_b
    dense_matrix_b = muon_b if s.optimizer == "muon" else adam_b
    L = math.ceil(s.layers / lay.pp)
    act = activation_terms(s, lay, device)
    n_dense = lay.shard or lay.dp * lay.cp
    n_exp = max(1, n_dense // lay.ep)

    def shard(x: float, n: int, stage_min: int) -> float:
        return x / n if lay.zero >= stage_min else x

    out = []
    for stage in ("first", "last") if lay.pp > 1 else ("only",):
        first, last = stage in ("first", "only"), stage in ("last", "only")
        extra = (pc["embed"] if first else 0) + (pc["head"] if last else 0)        # AdamW parameters
        norms = L * 2 * s.d
        dmat = L * pc["dense_matrix"] / lay.tp
        dadam = (norms + extra) / lay.tp
        exps = L * pc["expert_layer"] / lay.ep
        weights = shard(w * (dmat + dadam), n_dense, 3) + shard(w * exps, n_exp, 3)
        grads = shard(g * (dmat + dadam), n_dense, 2) + shard(g * exps, n_exp, 2)
        drouter = L * s.n_exp * s.d / lay.tp                                       # router: AdamW, not Muon
        opt = shard(dense_matrix_b * (dmat - drouter) + adam_b * (dadam + drouter), n_dense, 1) + shard(exp_b * exps, n_exp, 1)
        # bf16 autocast keeps a bf16 copy of every matrix it multiplies with (the whole layer, also under ZeRO-3);
        # the router runs outside autocast and the KE2 projection is read in fp32.
        cast = 0.0
        if s.dtype == "bf16":
            router = L * s.n_exp * s.d / lay.tp
            cast = 2 * (dmat - router + exps + (s.vocab * s.d * (2 if s.mtp else 1) / lay.tp if last else 0))
        gather = 2 * w * (pc["dense_layer"] / lay.tp + pc["expert_layer"] / lay.ep) if lay.zero == 3 else 0.0
        in_flight = min(lay.pp, lay.m) if stage == "first" else 1
        acts = L * in_flight * act["per_layer"] + (act["full_layer"] if lay.recompute == "full" else 0)
        acts += act["outside"] if (first or last) else 0
        logits = act["log_softmax"] + act["logits_held"] if last else 0.0
        row = {"stage": stage, "params": dmat + dadam + exps, "weights": weights, "grads": grads,
               "optimizer": opt, "cast_copies": cast, "zero3_gather": gather, "activations": acts,
               "logits": logits}
        row["total"] = sum(row[x] for x in ("weights", "grads", "optimizer", "cast_copies", "zero3_gather",
                                            "activations", "logits"))
        out.append(row)
    return out


def muon_tflop(s: Shape, lay: Layout) -> float:
    """Newton-Schulz work per device per optimizer step (5 steps of X X^T, A A, B X on the short side m x n:
    4 m^2 n + 2 m^3 each). Every rank that holds a whole matrix repeats it: DDP does not divide this work."""
    if s.optimizer != "muon":
        return 0.0
    mats = matrices(s)
    L = math.ceil(s.layers / lay.pp)
    ns = lambda r, c: 5 * (4 * min(r, c) ** 2 * max(r, c) + 2 * min(r, c) ** 3)
    dense = sum(ns(r, c) for k in ("attn", "shared") for r, c in mats[k])         # the router is on AdamW
    experts = sum(ns(r, c) for r, c in mats["experts"]) / lay.ep
    return L * (dense + experts) / 1e12


# ---------------------------------------------------------------- traffic per device per optimizer step
def traffic(s: Shape, lay: Layout) -> dict:
    """Bytes one device sends per optimizer step, ring algorithms (as v0, with Team 5's counts and fp32 grads)."""
    pc = param_counts(s)
    w = g = 4
    L = math.ceil(s.layers / lay.pp)
    extra = pc["embed"] + pc["head"] if lay.pp == 1 else max(pc["embed"], pc["head"])
    dense = (L * pc["dense_layer"] + extra) / lay.tp
    experts = L * pc["expert_layer"] / lay.ep
    n_dense = lay.shard or lay.dp * lay.cp
    n_exp = max(1, n_dense // lay.ep)
    frac = lambda n: (n - 1) / n if n > 1 else 0.0

    def grad_sync(n_params: float, n: int) -> float:
        if lay.zero == 0:
            return 2 * frac(n) * g * n_params
        if lay.zero in (1, 2):
            return frac(n) * (g + w) * n_params
        return lay.m * frac(n) * (2 * w + g) * n_params

    out = {"dp": grad_sync(dense, n_dense) + grad_sync(experts, n_exp)}
    if lay.shard:
        out["dp"] += 2 * frac(lay.dp * lay.cp // lay.shard) * g * (dense / n_dense + experts / n_exp)
    tokens = lay.b * s.seq / lay.cp
    act = 2                                                       # bf16 activation messages
    out["tp"] = lay.m * L * 4 * 2 * frac(lay.tp) * tokens * s.d * act if lay.tp > 1 else 0.0
    out["pp"] = lay.m * 2 * tokens * s.d * act / lay.tp if lay.pp > 1 else 0.0
    out["ep"] = lay.m * L * 4 * frac(lay.ep) * tokens * s.top_k * s.d * act / lay.tp if lay.ep > 1 else 0.0
    out["cp"] = (lay.m * L * 3 * (lay.cp - 1) * 2 * tokens * s.n_kv * s.hd / lay.tp * act) if lay.cp > 1 else 0.0
    out["total"] = sum(out.values())
    out["bubble"] = (lay.pp - 1) / lay.m if lay.pp > 1 else 0.0
    out["tokens_per_step"] = lay.dp * lay.m * lay.b * s.seq
    return out


# ---------------------------------------------------------------- standard layouts
def standard_layouts(s: Shape, world: int, base: Layout) -> list:
    """One device: the micro-batch splits of the arm's global batch. More devices: v0's one-axis layouts."""
    if world == 1:
        gb = base.b * base.m
        out = [replace(base, b=b, m=gb // b) for b in range(1, gb + 1) if gb % b == 0]
    else:
        out = [replace(base, dp=world, zero=z) for z in (0, 1, 2, 3)]
        out += [replace(base, tp=world), replace(base, pp=world, m=max(base.m, 4 * world)),
                replace(base, cp=world), replace(base, dp=world, ep=world)]
    return [lay for lay in out if not layout_problems(s, lay, world)]


# ---------------------------------------------------------------- output
UNITS = {"GiB": GIB, "MiB": 1024 ** 2}


def rows(s: Shape, layouts: list, device_gib: float = 0.0, unit: str = "GiB", device: str = "cuda") -> list:
    def u(x: float) -> str:
        return f"{x / UNITS[unit]:.2f}"

    out = []
    for lay in layouts:
        mem, tr = memory(s, lay, device), traffic(s, lay)
        out.append({"layout": lay.name(), "b": lay.b, "m": lay.m, "tokens/step": tr["tokens_per_step"],
                    "stage": mem["stage"], "weights": u(mem["weights"]), "grads": u(mem["grads"]),
                    "optimizer": u(mem["optimizer"]),
                    "states_end_of_step": u(mem["weights"] + mem["grads"] + mem["optimizer"]),
                    "activations": u(mem["activations"] + mem["logits"] + mem["cast_copies"] + mem["zero3_gather"]),
                    "total": u(mem["total"]),
                    "fits": ("yes" if mem["total"] <= device_gib * GIB else "NO") if device_gib else "-",
                    "muon": muon_check(s, lay), "muon_tflop": f"{muon_tflop(s, lay):.2f}",
                    "send_total": u(tr["total"]), "bubble": f"{tr['bubble']:.2f}", "runs_today": runs_today(lay)})
    return out


def markdown(table: list) -> str:
    if not table:
        return "(no valid layout)"
    head = list(table[0])
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return "\n".join(lines + ["| " + " | ".join(str(r[h]) for h in head) + " |" for r in table])


# ---------------------------------------------------------------- plain-text display (--markdown keeps the table)
def held_logits(s: Shape, lay: Layout, stage: str) -> float:
    """Logits the harness loop still references after optimizer.step(): the last micro-batch's model output
    (bf16 under autocast, else fp32). The fp32 copy and the saved log-softmax are freed by then."""
    if stage not in ("last", "only"):
        return 0.0
    return (2 if s.dtype == "bf16" else 4) * lay.b * s.seq / lay.cp * s.vocab / lay.tp * (2 if s.mtp else 1)


def header_text(s: Shape, pc: dict, notes: list, device: str) -> str:
    empty = [n.split(":")[0] for n in notes if "empty in config v1" in n]
    other = [n for n in notes if "empty in config v1" not in n]
    lines = [f"Model       {s.source}",
             f"  shape     {s.layers} layers, d {s.d}, {s.n_head} heads / {s.n_kv} KV heads, seq {s.seq:,}, "
             f"vocab {s.vocab:,}, KE2 P={s.ke_pos}",
             f"  experts   {s.n_exp} routed + {s.n_shared} shared, top-{s.top_k}, expert width {s.ffn_hidden}, "
             f"MTP {'yes' if s.mtp else 'no'}",
             f"  training  {s.optimizer}, {s.dtype}, attention-score bytes for {device}",
             "Parameters",
             f"  total     {pc['total']:>13,}   routed experts {pc['routed_experts']:,}",
             f"  Muon      {pc['muon']:>13,}   " + ("block matrices" if s.optimizer == "muon" else "(not used)"),
             f"  AdamW     {pc['adamw']:>13,}   " + ("embedding, head, norms, router" if s.optimizer == "muon" else "all"),
             f"  active    {pc['active_matmul']:>13,}   matmul parameters per token"]
    if empty:
        lines.append("Config v1 leaves empty (arm test values used): " + ", ".join(empty))
    lines += [f"Note: {n}" for n in other]
    return "\n".join(lines)


def detail_text(s: Shape, lay: Layout, device: str, device_gib: float, unit: str) -> str:
    k = UNITS[unit]
    mem, tr = memory(s, lay, device), traffic(s, lay)
    states = mem["weights"] + mem["grads"] + mem["optimizer"]
    opt_what = {"muon": "Muon momentum + AdamW moments", "adamw": "AdamW moments"}[s.optimizer]
    row = lambda name, v, why="": f"    {name:<17}{v / k:>8.2f}   {why}".rstrip()
    lines = [f"Layout {lay.name()}: b={lay.b}, m={lay.m}, {tr['tokens_per_step']:,} tokens per optimizer step",
             f"  Peak memory per device, {unit} (stage: {mem['stage']})",
             row("weights", mem["weights"], "fp32"),
             row("gradients", mem["grads"], "fp32"),
             row("optimizer state", mem["optimizer"], opt_what)]
    lines += [row("cast copies", mem["cast_copies"], "bf16 copies made by autocast")] if mem["cast_copies"] else []
    lines += [row("ZeRO-3 gather", mem["zero3_gather"], "one layer gathered")] if mem["zero3_gather"] else []
    lines += [row("activations", mem["activations"], "saved by autograd (blocks, embedding, final norm)"),
              row("logits and loss", mem["logits"], "logits, fp32 copy, log-softmax")]
    fit = ""
    if device_gib:
        spare = device_gib * GIB - mem["total"]
        fit = (f"fits in {device_gib:g} GiB: yes, {spare / k:.2f} spare" if spare >= 0 else
               f"fits in {device_gib:g} GiB: NO, {-spare / k:.2f} over")
    lines.append(row("= peak", mem["total"], fit))

    lines += [f"  Memory after optimizer.step(), {unit}",
              row("states", states, "weights + gradients + optimizer state, kept between steps")]
    if runs_today(lay) == "yes":
        held = held_logits(s, lay, mem["stage"])
        lines += [row("+ held logits", held, "last micro-batch's logits, still referenced by the loop"),
                  row("= allocated", states + held, "compare with the harness's gpu_alloc_gb")]

    lines.append(f"  Communication per device per optimizer step, {unit}")
    sends = [(x, tr[x]) for x in ("dp", "tp", "pp", "ep", "cp") if tr[x]]
    if sends:
        lines += [f"    {x:<17}{v / k:>8.2f}" for x, v in sends] + [f"    {'= total':<17}{tr['total'] / k:>8.2f}"]
    else:
        lines.append("    none")
    if lay.pp > 1:
        lines.append(f"    pipeline bubble  {tr['bubble']:>7.0%}")
    lines.append(f"  Muon       {muon_check(s, lay)}"
                 + (f"; Newton-Schulz {muon_tflop(s, lay):.2f} TFLOP per step" if s.optimizer == "muon" else ""))
    lines.append(f"  Runs today {runs_today(lay)}" + (" (train_week2.py)" if runs_today(lay) == "yes" else ""))
    return "\n".join(lines)


def summary_text(s: Shape, layouts: list, device: str, device_gib: float, unit: str) -> str:
    k = UNITS[unit]
    head = ["layout", "b", "m", "tokens/step", f"peak {unit}", f"states {unit}"] + \
           (["fits"] if device_gib else []) + ["muon", "NS TFLOP", f"send {unit}", "bubble", "runs today"]
    body = []
    for lay in layouts:
        mem, tr = memory(s, lay, device), traffic(s, lay)
        r = [lay.name(), lay.b, lay.m, f"{tr['tokens_per_step']:,}", f"{mem['total'] / k:.2f}",
             f"{(mem['weights'] + mem['grads'] + mem['optimizer']) / k:.2f}"]
        r += [("yes" if mem["total"] <= device_gib * GIB else "NO")] if device_gib else []
        r += [muon_check(s, lay), f"{muon_tflop(s, lay):.2f}", f"{tr['total'] / k:.2f}",
              f"{tr['bubble']:.0%}" if lay.pp > 1 else "-", runs_today(lay)]
        body.append([str(x) for x in r])
    width = [max(len(r[i]) for r in [head] + body) for i in range(len(head))]
    left = {0, head.index("muon"), len(head) - 1}
    fmt = lambda r: "  ".join(c.ljust(w) if i in left else c.rjust(w)
                              for i, (c, w) in enumerate(zip(r, width))).rstrip()
    return "\n".join([fmt(head), "  ".join("-" * w for w in width)] + [fmt(r) for r in body])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", required=True, help="Team 5 arm (configs/arms/t2.yaml, t3.yaml, exp2_muon.yaml, ...)")
    ap.add_argument("--decisions", default=str(DEFAULT_DECISIONS), help="config v1 settings list; '' to skip")
    ap.add_argument("--set", action="append", default=[], help="override a shape field, e.g. mtp=true")
    ap.add_argument("--layout", action="append", default=[], help="e.g. b=2,m=4 or dp=2,ep=2 (repeatable)")
    ap.add_argument("--world", type=int, default=0, help="devices; without --layout, show the standard layouts")
    ap.add_argument("--base", default="", help="shared by the standard layouts; default b=1,m=<arm batch_size>")
    ap.add_argument("--device", choices=["cuda", "cpu"], default="cuda", help="sets the attention-score bytes")
    ap.add_argument("--device-gib", type=float, default=0.0, help="memory per device, to print fits yes/NO")
    ap.add_argument("--unit", choices=sorted(UNITS), default="GiB")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--detail", action="store_true", help="breakdown for every layout (automatic with one layout)")
    args = ap.parse_args(argv)

    sets = {}
    for item in args.set:
        key, _, val = item.partition("=")
        typ = {f.name: f.type for f in fields(Shape)}.get(key)
        if typ is None:
            raise SystemExit(f"--set {item!r}: no shape field {key!r}")
        sets[key] = val if typ == "str" else (val.lower() in ("1", "true", "yes") if typ == "bool" else int(val))
    s, run, notes = load_shape(args.arm, args.decisions or None, sets)
    if s.problems():
        raise SystemExit("; ".join(s.problems()))
    layouts = [parse_layout(t) for t in args.layout]
    if not layouts:
        if not args.world:
            raise SystemExit("give --layout or --world")
        layouts = standard_layouts(s, args.world, parse_layout(args.base or f"b=1,m={run['batch_size']}"))
    bad = [(lay.name(), layout_problems(s, lay, args.world)) for lay in layouts]
    bad = [(n, p) for n, p in bad if p]
    if bad:
        for n, p in bad:
            print(f"FAIL {n}: {'; '.join(p)}")
        return 1
    pc = param_counts(s)
    if not args.markdown:
        print(header_text(s, pc, notes, args.device))
        print("Estimates from formulas, not measured. Memory is per device on the busiest pipeline stage.\n")
        if len(layouts) > 1:
            print(summary_text(s, layouts, args.device, args.device_gib, args.unit) + "\n")
        if len(layouts) == 1 or args.detail:
            print("\n\n".join(detail_text(s, lay, args.device, args.device_gib, args.unit) for lay in layouts))
        else:
            print("Add --detail for the memory and communication breakdown of each layout.")
        return 0
    print(f"shape: {s.source}  layers={s.layers} d={s.d} heads={s.n_head}/{s.n_kv} seq={s.seq} vocab={s.vocab} "
          f"experts={s.n_exp}+{s.n_shared} top_k={s.top_k} expert_width={s.ffn_hidden} optimizer={s.optimizer} "
          f"dtype={s.dtype} device={args.device}")
    print(f"parameters: total={pc['total']:,} routed_experts={pc['routed_experts']:,} muon={pc['muon']:,} "
          f"adamw={pc['adamw']:,} active_matmul={pc['active_matmul']:,}")
    for n in notes:
        print(f"note: {n}")
    print(f"memory in {args.unit} per device, busiest stage; send in {args.unit} per device per optimizer step; "
          "estimates, not measured")
    print(markdown(rows(s, layouts, args.device_gib, args.unit, args.device)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
