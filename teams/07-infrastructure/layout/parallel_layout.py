#!/usr/bin/env python3
"""Parallel layout v0 (docs/parallel_layout_v0.md): memory and traffic per device for each layout.

In simple words: give it the model shape (a Team 6 / Team 5 config) and a layout (how many devices for data,
tensor, pipeline, expert and context parallel, which ZeRO stage, the micro-batch). It prints, per device, the
bytes of weights, gradients, optimizer state and activations, and the bytes each device sends per optimizer
step. The numbers are the formulas of docs/parallel_layout_v0.md, nothing measured. They are for choosing a
layout before we pay for one; a measured run replaces them.

    python layout/parallel_layout.py --config ../06-performance/configs/tiny_cpu.yaml --world 2
    python layout/parallel_layout.py --config <config_v1.yaml> --layout dp=4,zero=3,b=4,m=2 --device-gib 40
    python layout/parallel_layout.py --config <config_v1.yaml> --world 8 --markdown     # table for the doc

Needs PyYAML. Torch only for the tests that compare the counts with Team 6's model.
"""
from __future__ import annotations

import argparse
import copy
import math
import sys
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

import yaml

GIB = 1024 ** 3
N_BYTES = 256                    # Kronecker embedding codec: 256 byte values per byte position (Team 6 ke1/ke2)

# bytes per parameter: (stored weight, gradient, optimizer state without the moments).  The moments come from
# --opt-bytes (AdamW: 8 = exp_avg + exp_avg_sq in fp32).
#   amp   fp32 weights and grads, bf16 compute under autocast (Team 6 bench today)
#   bf16  bf16 weights and grads + an fp32 master copy in the optimizer (the ZeRO paper's accounting)
#   fp32  everything fp32
PRECISION = {"amp": (4, 4, 0), "bf16": (2, 2, 4), "fp32": (4, 4, 0)}
ACT_SCALE = {"amp": 1.0, "bf16": 1.0, "fp32": 2.0}        # the 34 / 5 constants below assume 16-bit activations


# ---------------------------------------------------------------- the model shape
@dataclass
class Shape:
    vocab: int
    seq: int
    layers: int
    d: int
    n_head: int
    n_kv: int
    mlp_ratio: int
    ffn: str = "mlp"             # mlp | moe
    n_exp: int = 0               # routed experts
    top_k: int = 0
    n_shared: int = 0            # shared experts (always active, replicated like dense weights)
    embedding: str = "table"     # table (tied head) | ke1 | ke2 (Kronecker, untied head)
    ke_max_pos: int = 32
    mtp: bool = False            # second untied head for token t+2
    source: str = ""

    def problems(self) -> list:
        p = []
        if self.d % self.n_head:
            p.append(f"d {self.d} is not divisible by n_head {self.n_head}")
        if self.n_kv < 1 or self.n_head % self.n_kv:
            p.append(f"n_kv {self.n_kv} must divide n_head {self.n_head}")
        if self.ffn not in ("mlp", "moe"):
            p.append(f"ffn {self.ffn!r} is mlp or moe")
        if self.ffn == "moe" and not 1 <= self.top_k <= self.n_exp:
            p.append(f"top_k {self.top_k} is outside 1..{self.n_exp}")
        if self.embedding not in ("table", "ke1", "ke2"):
            p.append(f"embedding {self.embedding!r} is table, ke1 or ke2")
        return p


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _load_inherit(path: Path) -> dict:
    """Team 6 YAML: `inherit: <parent>.yaml` is merged first (models/config.py does the same)."""
    cfg = yaml.safe_load(path.read_text()) or {}
    parent = cfg.pop("inherit", None)
    return _merge(_load_inherit(path.parent / parent), cfg) if parent else cfg


def shape_from_team6(cfg: dict, source: str = "") -> Shape:
    m = cfg["model"]
    moe = m.get("moe") or {}                     # read even when ffn is mlp, so --set ffn=moe works
    return Shape(vocab=m["vocab_size"], seq=m["block_size"], layers=m["n_layer"], d=m["n_embd"],
                 n_head=m["n_head"], n_kv=m.get("n_kv_head") or m["n_head"], mlp_ratio=m["mlp_ratio"],
                 ffn=m.get("ffn", "mlp"), n_exp=moe.get("num_experts", 0), top_k=moe.get("top_k", 0),
                 n_shared=moe.get("num_shared", 0),
                 embedding=m.get("embedding", "table"), ke_max_pos=m.get("ke_max_pos", 32),
                 mtp=bool(m.get("mtp", False)), source=source)


# Team 5 settings list (configs/config_v0.yaml) -> Shape field. A size that is still null stays an error:
# we never guess a model size.
TEAM5_KEYS = {"tokenizer.vocab_size": "vocab", "data.seq_len": "seq", "model.n_layer": "layers",
              "model.d_model": "d", "model.n_head": "n_head", "model.n_kv_head": "n_kv",
              "model.mlp_ratio": "mlp_ratio", "moe.n_expert": "n_exp", "moe.top_k": "top_k",
              "moe.num_shared": "n_shared", "embedding.type": "embedding", "embedding.pos_dim": "ke_max_pos"}


def shape_from_team5(cfg: dict, sets: dict, source: str = "") -> Shape:
    values = {s["key"]: s.get("value") for s in cfg["settings"]}
    got = {f: values.get(k) for k, f in TEAM5_KEYS.items() if values.get(k) is not None}
    got.update(sets)
    if got.get("embedding") == "kronecker":
        raise SystemExit("embedding.type kronecker: say which one with --set embedding=ke1|ke2")
    if "n_exp" in got:
        got.setdefault("ffn", "moe")
    need = ["vocab", "seq", "layers", "d", "n_head", "n_kv", "mlp_ratio"]
    missing = [f for f in need if f not in got]
    if missing:
        raise SystemExit(f"{source}: no value for {', '.join(missing)}. Fill the config or pass --set name=value.")
    return Shape(**got, source=source)


def load_shape(path: str, sets: dict = None) -> Shape:
    p = Path(path)
    cfg = _load_inherit(p)
    sets = sets or {}
    if "settings" in cfg:
        return shape_from_team5(cfg, sets, str(p))
    if "model" not in cfg:
        raise SystemExit(f"{p}: neither a Team 6 config (model:) nor a Team 5 settings list (settings:)")
    return replace(shape_from_team6(cfg, str(p)), **sets)


# ---------------------------------------------------------------- parameter counts (exact for Team 6 models/gpt.py)
def param_counts(s: Shape) -> dict:
    """Every parameter of Team 6's GPT, by group. Biases and LayerNorms included (nn.Linear has bias there)."""
    d, hd = s.d, s.d // s.n_head
    hidden = s.mlp_ratio * d
    attn = d * (s.n_head + 2 * s.n_kv) * hd + (s.n_head + 2 * s.n_kv) * hd + d * d + d   # c_attn, c_proj
    norms = 2 * 2 * d                                                                      # ln1, ln2
    one_mlp = d * hidden + hidden + hidden * d + d
    if s.ffn == "moe":
        router = d * s.n_exp + s.n_exp
        dense_layer = attn + norms + router + s.n_shared * one_mlp
        expert_layer = s.n_exp * one_mlp
    else:
        dense_layer, expert_layer = attn + norms + one_mlp, 0
    tok = s.vocab * d if s.embedding == "table" else N_BYTES * s.ke_max_pos * d
    embed = tok + s.seq * d                                                                # + learned positions
    head = (0 if s.embedding == "table" else s.vocab * d) + (s.vocab * d if s.mtp else 0) + 2 * d   # ln_f
    total = s.layers * (dense_layer + expert_layer) + embed + head
    per_expert = 2 * d * hidden
    active = (s.vocab * d * (2 if s.mtp else 1) + (0 if s.embedding == "table" else N_BYTES * s.ke_max_pos * d)
              + s.layers * (d * (s.n_head + 2 * s.n_kv) * hd + d * d
                            + (d * s.n_exp + per_expert * (s.top_k + s.n_shared) if s.ffn == "moe"
                               else per_expert)))
    return {"dense_layer": dense_layer, "expert_layer": expert_layer, "embed": embed, "head": head,
            "total": total, "routed_experts": s.layers * expert_layer, "active_matmul": active}


# ---------------------------------------------------------------- the layout
@dataclass
class Layout:
    dp: int = 1                  # data parallel
    tp: int = 1                  # tensor parallel (Megatron, with sequence parallel)
    pp: int = 1                  # pipeline parallel (1F1B)
    ep: int = 1                  # expert parallel, taken from the dp x cp devices
    cp: int = 1                  # context parallel (ring attention)
    zero: int = 0                # 0 DDP | 1 | 2 | 3 (= FSDP full shard)
    shard: int = 0               # ZeRO-3 only: shard group size (HSDP); 0 = the whole dp x cp group
    b: int = 1                   # micro-batch, sequences per device
    m: int = 1                   # micro-batches per optimizer step (gradient accumulation / pipeline)
    recompute: str = "none"      # none | selective | full
    precision: str = "amp"       # amp | bf16 | fp32
    opt_bytes: int = 8           # optimizer moments per parameter (AdamW 8; momentum-only optimizers 4)
    ce_chunks: int = 1           # Team 6 ce_impl chunked: logits held in this many pieces

    @property
    def world(self) -> int:
        return self.dp * self.tp * self.pp * self.cp

    def name(self) -> str:
        parts = [f"{k}={v}" for k, v in (("dp", self.dp), ("tp", self.tp), ("pp", self.pp), ("ep", self.ep),
                                          ("cp", self.cp)) if v > 1] or ["single"]
        if self.zero:
            parts.append(f"zero={self.zero}" + (f"/shard={self.shard}" if self.shard else ""))
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
    if min(lay.dp, lay.tp, lay.pp, lay.ep, lay.cp, lay.b, lay.m, lay.ce_chunks) < 1:
        p.append("every degree, b, m and ce_chunks must be at least 1")
        return p
    if s.n_head % lay.tp:
        p.append(f"tp {lay.tp} must divide n_head {s.n_head}")
    if s.n_kv % lay.tp:
        p.append(f"tp {lay.tp} must divide n_kv {s.n_kv} (else the KV heads are copied; not modelled in v0)")
    if (s.mlp_ratio * s.d) % lay.tp:
        p.append(f"tp {lay.tp} must divide the FFN width {s.mlp_ratio * s.d}")
    if lay.pp > s.layers:
        p.append(f"pp {lay.pp} is more than the {s.layers} layers")
    if lay.ep > 1 and s.ffn != "moe":
        p.append("ep > 1 needs an MoE model")
    if s.ffn == "moe" and s.n_exp % lay.ep:
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
    if lay.precision not in PRECISION:
        p.append(f"precision is one of {', '.join(PRECISION)}")
    if lay.pp > 1 and lay.m < lay.pp:
        p.append(f"m {lay.m} < pp {lay.pp}: the pipeline never fills (bubble over 50%)")
    return p


# ---------------------------------------------------------------- memory per device
def _frac(n: int) -> float:
    return (n - 1) / n if n > 1 else 0.0


def activation_bytes_per_layer(s: Shape, lay: Layout) -> float:
    """One layer, one micro-batch, per device. Korthikanti et al. 2022, eq. 2 and 4 (tensor + sequence parallel):
    s*b*h*(34/t + 5*a*s/(h*t)) bytes at 16 bits. Selective recompute drops the 5*a*s/h term (the attention
    scores); full recompute keeps only the layer input, 2*s*b*h/t. Derived for multi-head attention with a 4h
    MLP, so for GQA and MoE it is an estimate (section C of the doc)."""
    seq, h, t = s.seq / lay.cp, s.d, lay.tp
    sbh = seq * lay.b * h
    if lay.recompute == "full":
        per = 2 * sbh / t
    elif lay.recompute == "selective":
        per = 34 * sbh / t
    else:
        per = sbh * (34 / t + 5 * s.n_head * seq / (h * t))
    return per * ACT_SCALE[lay.precision]


def memory(s: Shape, lay: Layout) -> dict:
    """Bytes per device on the busiest pipeline stage (the larger of the first and the last stage)."""
    return max(memory_stages(s, lay), key=lambda row: row["total"])


def memory_stages(s: Shape, lay: Layout) -> list:
    """Bytes per device for each kind of pipeline stage: [only] without pipeline, else [first, last]."""
    pc = param_counts(s)
    w, g, master = PRECISION[lay.precision]
    k = master + lay.opt_bytes
    layers_stage = math.ceil(s.layers / lay.pp)
    act_layer = activation_bytes_per_layer(s, lay)
    full_layer = activation_bytes_per_layer(s, replace(lay, recompute="none"))
    logits = 4 * lay.b * (s.seq / lay.cp) * s.vocab / lay.tp / lay.ce_chunks * (2 if s.mtp else 1)
    n_dense = lay.shard or lay.dp * lay.cp
    n_exp = max(1, n_dense // lay.ep)

    def states(n_params: float, n: int) -> tuple:
        if lay.zero == 0:
            return w * n_params, g * n_params, k * n_params
        if lay.zero == 1:
            return w * n_params, g * n_params, k * n_params / n
        if lay.zero == 2:
            return w * n_params, g * n_params / n, k * n_params / n
        return w * n_params / n, g * n_params / n, k * n_params / n

    out = []
    for stage in ("first", "last") if lay.pp > 1 else ("only",):
        extra = (pc["embed"] if stage in ("first", "only") else 0) + (pc["head"] if stage in ("last", "only") else 0)
        dense = (layers_stage * pc["dense_layer"] + extra) / lay.tp
        experts = layers_stage * pc["expert_layer"] / lay.ep
        wd, gd, od = states(dense, n_dense)
        we, ge, oe = states(experts, n_exp)
        in_flight = min(lay.pp, lay.m) if stage == "first" else 1
        acts = layers_stage * in_flight * act_layer
        if lay.recompute == "full":
            acts += full_layer                                    # the one layer being recomputed
        gather = 0.0
        if lay.zero == 3:                                         # this unit + the prefetched next one, unsharded
            gather = 2 * w * (pc["dense_layer"] / lay.tp + pc["expert_layer"] / lay.ep)
        row = {"stage": stage, "params": dense + experts, "weights": wd + we, "grads": gd + ge,
               "optimizer": od + oe, "zero3_gather": gather, "activations": acts,
               "logits": logits if stage in ("last", "only") else 0.0}
        row["total"] = sum(row[x] for x in ("weights", "grads", "optimizer", "zero3_gather", "activations",
                                            "logits"))
        out.append(row)
    return out


# ---------------------------------------------------------------- traffic per device per optimizer step
def traffic(s: Shape, lay: Layout) -> dict:
    """Bytes one device sends per optimizer step, ring algorithms: all-reduce 2(n-1)/n * M,
    reduce-scatter and all-gather (n-1)/n * M each."""
    pc = param_counts(s)
    w, g, _ = PRECISION[lay.precision]
    layers_stage = math.ceil(s.layers / lay.pp)
    extra = pc["embed"] + pc["head"] if lay.pp == 1 else max(pc["embed"], pc["head"])
    dense = (layers_stage * pc["dense_layer"] + extra) / lay.tp
    experts = layers_stage * pc["expert_layer"] / lay.ep
    n_dense = lay.shard or lay.dp * lay.cp
    n_exp = max(1, n_dense // lay.ep)

    def grad_sync(n_params: float, n: int) -> float:
        if lay.zero == 0:
            return 2 * _frac(n) * g * n_params                    # all-reduce grads once per step
        if lay.zero in (1, 2):
            return _frac(n) * (g + w) * n_params                  # reduce-scatter grads + all-gather weights
        return lay.m * _frac(n) * (2 * w + g) * n_params          # per micro-batch: 2 all-gathers + 1 reduce-scatter

    out = {"dp": grad_sync(dense, n_dense) + grad_sync(experts, n_exp)}
    if lay.shard:                                                 # HSDP: grads all-reduced across the replicas
        out["dp"] += 2 * _frac(lay.dp * lay.cp // lay.shard) * g * (dense / n_dense + experts / n_exp)
    tokens = lay.b * s.seq / lay.cp                               # tokens per device per micro-batch
    act = 2                                                       # bytes per activation value (16-bit)
    out["tp"] = lay.m * layers_stage * 4 * 2 * _frac(lay.tp) * tokens * s.d * act if lay.tp > 1 else 0.0
    out["pp"] = lay.m * 2 * tokens * s.d * act / lay.tp if lay.pp > 1 else 0.0
    moe_layers = layers_stage if s.ffn == "moe" else 0
    out["ep"] = (lay.m * moe_layers * 4 * _frac(lay.ep) * tokens * s.top_k * s.d * act / lay.tp
                 if lay.ep > 1 else 0.0)
    kv = s.n_kv * (s.d // s.n_head) / lay.tp
    out["cp"] = lay.m * layers_stage * 3 * (lay.cp - 1) * 2 * tokens * kv * act if lay.cp > 1 else 0.0
    out["total"] = sum(out.values())
    out["bubble"] = (lay.pp - 1) / lay.m if lay.pp > 1 else 0.0  # 1F1B idle time / ideal time (Narayanan 2021)
    out["tokens_per_step"] = lay.dp * lay.m * lay.b * s.seq
    return out


# ---------------------------------------------------------------- standard layouts for N devices
def standard_layouts(s: Shape, world: int, base: Layout) -> list:
    """The one-axis layouts of the doc's table: DDP, ZeRO 1/2/3, TP, PP, EP, CP, each on all `world` devices."""
    out = [replace(base, dp=world, zero=z) for z in (0, 1, 2, 3)]
    if world > 1:
        out += [replace(base, tp=world), replace(base, pp=world, m=max(base.m, 4 * world)),
                replace(base, cp=world)]
        if s.ffn == "moe":
            out.append(replace(base, dp=world, ep=world))
    return [lay for lay in out if not layout_problems(s, lay, world)]


# ---------------------------------------------------------------- output
UNITS = {"GiB": GIB, "MiB": 1024 ** 2}


def rows(s: Shape, layouts: list, device_gib: float = 0.0, unit: str = "GiB") -> list:
    def _gib(x: float) -> str:
        return f"{x / UNITS[unit]:.3f}"

    out = []
    for lay in layouts:
        mem, tr = memory(s, lay), traffic(s, lay)
        out.append({"layout": lay.name(), "stage": mem["stage"], "weights": _gib(mem["weights"]),
                    "grads": _gib(mem["grads"]), "optimizer": _gib(mem["optimizer"]),
                    "activations": _gib(mem["activations"] + mem["logits"] + mem["zero3_gather"]),
                    "total": _gib(mem["total"]),
                    "fits": ("yes" if mem["total"] <= device_gib * GIB else "NO") if device_gib else "-",
                    "send_dp": _gib(tr["dp"]), "send_tp": _gib(tr["tp"]), "send_pp": _gib(tr["pp"]),
                    "send_ep": _gib(tr["ep"]), "send_cp": _gib(tr["cp"]), "send_total": _gib(tr["total"]),
                    "bubble": f"{tr['bubble']:.2f}"})
    return out


def markdown(table: list) -> str:
    if not table:
        return "(no valid layout)"
    head = list(table[0])
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(r[h]) for h in head) + " |" for r in table]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", required=True, help="Team 6 config (model:) or Team 5 settings list")
    ap.add_argument("--set", action="append", default=[], help="override a shape field, e.g. n_kv=2")
    ap.add_argument("--layout", action="append", default=[], help="e.g. dp=4,zero=3,b=4,m=2 (repeatable)")
    ap.add_argument("--world", type=int, default=0, help="devices; without --layout, show the standard layouts")
    ap.add_argument("--base", default="", help="settings shared by the standard layouts, e.g. b=4,m=2,recompute=selective")
    ap.add_argument("--device-gib", type=float, default=0.0, help="memory per device, to print fits yes/NO")
    ap.add_argument("--unit", choices=sorted(UNITS), default="GiB")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args(argv)

    sets = {}
    for item in args.set:
        key, _, val = item.partition("=")
        typ = {f.name: f.type for f in fields(Shape)}.get(key)
        if typ is None:
            raise SystemExit(f"--set {item!r}: no shape field {key!r}")
        sets[key] = val if typ == "str" else (val.lower() in ("1", "true", "yes") if typ == "bool" else int(val))
    s = load_shape(args.config, sets)
    if s.problems():
        raise SystemExit("; ".join(s.problems()))
    layouts = [parse_layout(t) for t in args.layout]
    if not layouts:
        if not args.world:
            raise SystemExit("give --layout or --world")
        layouts = standard_layouts(s, args.world, parse_layout(args.base))
    bad = [(lay.name(), layout_problems(s, lay, args.world)) for lay in layouts]
    bad = [(n, p) for n, p in bad if p]
    if bad:
        for n, p in bad:
            print(f"FAIL {n}: {'; '.join(p)}")
        return 1
    pc = param_counts(s)
    print(f"shape: {s.source}  layers={s.layers} d={s.d} heads={s.n_head}/{s.n_kv} seq={s.seq} vocab={s.vocab} "
          f"ffn={s.ffn} experts={s.n_exp} top_k={s.top_k} shared={s.n_shared} embedding={s.embedding}")
    print(f"parameters: total={pc['total']:,} routed_experts={pc['routed_experts']:,} "
          f"active_matmul={pc['active_matmul']:,}")
    print(f"memory in {args.unit} per device, busiest stage; send in {args.unit} per device per optimizer step; "
          "estimates, not measured")
    table = rows(s, layouts, args.device_gib, args.unit)
    if args.markdown:
        print(markdown(table))
    else:
        for r in table:
            print("  ".join(f"{k}={v}" for k, v in r.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
