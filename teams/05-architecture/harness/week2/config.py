"""Adapt lead-owned G5 arm files; do not load mutable G6 defaults."""
from pathlib import Path
import copy
import hashlib
import math
import yaml

TEAM = Path(__file__).resolve().parents[2]

class UniqueLoader(yaml.SafeLoader):
    pass

def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("Duplicate YAML key: " + str(key))
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)

def merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result

def read_yaml(path):
    value = yaml.load(Path(path).read_text(encoding="utf8"), Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise ValueError("Config must be a mapping: " + str(path))
    return value

def load(path, seen=None):
    """Load small harness resolution files, not the G6-inheriting arm tree."""
    path = Path(path).resolve()
    seen = set() if seen is None else set(seen)
    if path in seen:
        raise ValueError("Config inheritance cycle")
    seen.add(path)
    obj = read_yaml(path)
    parent = obj.pop("inherit", None)
    return merge(load(path.parent / parent, seen), obj) if parent else obj

def _unknown(obj, allowed, context):
    extra = set(obj) - set(allowed)
    if extra:
        raise ValueError(context + ": unsupported fields " + str(sorted(extra)))

def load_runtime(arm_path, runtime_path=None):
    """Resolve G5 declarations to a native runtime config with recorded provenance.

    Only the lead's G5 chain is merged. Stop at t1/t2/t3 BEFORE its G6 inherit.
    Missing dimensions fail; no copied profile constants or default ratio fallback.
    """
    runtime_path = Path(runtime_path or TEAM / "configs/runtime.yaml").resolve()
    team = runtime_path.parents[1]
    arms_root = (team / "configs/arms").resolve()
    runtime = read_yaml(runtime_path)
    _unknown(runtime, ["contract", "model", "optim", "run", "approval", "evaluation", "budgets"], "runtime")
    _unknown(runtime["model"], ["activation", "position", "rope_theta", "rotary_fraction", "norm_eps", "mtp_weight", "moe"], "runtime.model")
    _unknown(runtime["model"]["moe"], ["bias", "bias_gamma"], "runtime.model.moe")
    _unknown(runtime["optim"], ["betas", "eps", "schedule"], "runtime.optim")
    _unknown(runtime["run"], ["micro_batch_size", "eval_every_steps", "compile", "flush_every_steps"], "runtime.run")
    plan = team / "experiments/plan_v1.md"
    plan_hash = hashlib.sha256(plan.read_text(encoding="utf8").encode("utf8")).hexdigest()
    path = Path(arm_path).resolve()
    seen, nodes, sources = set(), [], []
    while True:
        if not path.is_relative_to(arms_root):
            raise ValueError("Arm inheritance must stay inside the lead G5 configs/arms tree")
        if path in seen:
            raise ValueError("Arm inheritance cycle")
        seen.add(path)
        obj = read_yaml(path)
        _unknown(obj, ["inherit", "intended", "model", "optim", "run"], "lead arm")
        sources.append({"path": path.relative_to(team).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        parent = obj.pop("inherit", None)
        nodes.append(obj)
        if path.parent == arms_root and path.stem in ["t1", "t2", "t3"]:
            profile = path.stem.upper()
            if obj.get("intended", {}).get("arm") != profile:
                raise ValueError("Lead profile identity does not match filename")
            break
        if not parent:
            raise ValueError("Arm does not reach a lead t1/t2/t3 profile")
        path = (path.parent / parent).resolve()
    declared = {}
    for obj in reversed(nodes):
        declared = merge(declared, obj)
    src = declared["model"]
    _unknown(src, ["vocab_size", "block_size", "n_layer", "n_head", "n_kv_head", "n_embd", "mlp_ratio", "embedding", "ke_max_pos", "ke_mode", "ffn", "moe", "activation", "position", "rope_theta", "reversible", "mtp", "mtp_weight", "attn_impl", "ce_impl", "norm_eps", "rotary_fraction", "attn_pattern", "attn_window", "attn_sink", "attn_gate", "attn_gate_input", "attn_gate_bias", "attn_gate_init"], "lead model")
    _unknown(src["moe"], ["num_experts", "num_shared", "top_k", "ffn_hidden", "bias", "dispatch", "bias_gamma"], "lead model.moe")
    _unknown(declared["optim"], ["name", "lr", "weight_decay", "muon_lr", "schedule", "warmup_steps", "betas", "eps"], "lead optim")
    _unknown(declared["run"], ["seed", "batch_size", "grad_clip", "dtype", "compile", "steps", "max_time_min"], "lead run")
    if src.get("embedding") not in ["ke1", "g4_raw_ke"] or src.get("ffn") != "moe":
        raise ValueError("Native harness requires the declared Kronecker/MoE path")
    if src.get("ke_mode") not in [None,"dynamic"]:
        raise ValueError("Only dynamic native KE projection is supported; cached mode cannot be ignored")
    model = copy.deepcopy(runtime["model"])
    for key in ["embedding", "attn_impl", "mtp", "reversible", "ce_impl"]:
        if key not in src:raise ValueError("Missing explicit arm setting: model."+key)
        model[key]=src[key]
    if "dispatch" not in src["moe"]:raise ValueError("Missing explicit arm setting: model.moe.dispatch")

    for key in ["vocab_size", "block_size", "n_layer", "n_head", "n_kv_head", "n_embd", "ke_max_pos"]:
        if key not in src:
            raise ValueError("Missing explicit lead dimension: model." + key)
        model[key] = src[key]
    for key in ["activation", "position", "rope_theta", "reversible", "mtp", "mtp_weight", "attn_impl", "ce_impl", "norm_eps", "rotary_fraction", "attn_pattern", "attn_window", "attn_sink", "attn_gate", "attn_gate_input", "attn_gate_bias", "attn_gate_init"]:
        if key in src:
            model[key] = src[key].lower() if key in ["activation", "position"] and isinstance(src[key], str) else src[key]
    model["moe"] = merge(model["moe"], src["moe"])
    explicit_width = src["moe"].get("ffn_hidden")
    intended_width = declared.get("intended", {}).get("instructor_expert_ffn")
    if explicit_width is not None and intended_width is not None and explicit_width != intended_width:
        raise ValueError("Explicit expert width disagrees with lead intended width")
    width = explicit_width if explicit_width is not None else intended_width
    if type(width) is not int or width <= 0:
        raise ValueError("Missing absolute expert width; refuse mlp_ratio fallback")
    ratio = src.get("mlp_ratio")
    if ratio is not None and (type(ratio) not in [float, int] or ratio * model["n_embd"] != width):
        raise ValueError("Lead ratio and absolute expert width conflict")
    model["moe"]["ffn_hidden"] = width
    optim = merge(runtime["optim"], declared["optim"])
    if optim.get("warmup_steps", 0) != 0:
        raise ValueError("Warmup schedule not implemented; do not ignore it")
    optim.pop("warmup_steps", None)
    run = merge(runtime["run"], runtime["budgets"][profile])
    run = merge(run, declared["run"])
    lead_choices = {}
    for key in ["rope_theta", "norm_eps", "reversible", "mtp", "mtp_weight"]:
        if key in src and src[key] is not None:
            lead_choices["model." + key] = src[key]
    if src["moe"].get("bias") is not None:
        lead_choices["model.moe.bias"] = src["moe"]["bias"]
    if "max_time_min" in declared["intended"]:
        run["max_time_min"] = declared["intended"]["max_time_min"]
    return {"intended": {**declared["intended"], "profile": profile, "lead_intent": declared["intended"]},
            "model": model, "optim": optim, "run": run,
            "approval": copy.deepcopy(runtime["approval"]), "evaluation": copy.deepcopy(runtime["evaluation"]),
            "provenance": {"arm_sources": sources, "runtime_sha256": hashlib.sha256(runtime_path.read_bytes()).hexdigest(),
                           "plan_sha256": plan_hash, "plan_hash_normalization": "UTF-8 with LF newlines", "lead_snapshot": runtime["contract"]["lead_snapshot"],
                           "expert_width_source": "model.moe.ffn_hidden" if explicit_width is not None else "intended.instructor_expert_ffn",
                           "lead_explicit_choices": lead_choices, "g6_inheritance": "not loaded; explicit G5 declarations only"}}

def validate(c):
    errors=[];m=c["model"];r=c["run"];e=m["moe"];o=c["optim"]
    def positive(v):return type(v) is int and v>0
    def number(v):return type(v) in (float,int) and math.isfinite(v)
    for k in ["vocab_size","block_size","n_layer","n_head","n_kv_head","n_embd"]:
        if not positive(m.get(k)):errors.append("model."+k+" must be positive integer")
    for k in ["num_experts","top_k","ffn_hidden"]:
        if not positive(e.get(k)):errors.append("model.moe."+k+" must be positive integer")
    for k in ["batch_size","micro_batch_size","steps","eval_every_steps","flush_every_steps"]:
        if not positive(r.get(k)):errors.append("run."+k+" must be positive integer")
    if errors:return errors
    if m["n_embd"]%m["n_head"] or m["n_head"]%m["n_kv_head"]:errors.append("Invalid GQA geometry")
    if (m["n_embd"]//m["n_head"])%2:errors.append("RoPE needs even head dim")
    if not 1<=e["top_k"]<=e["num_experts"] or type(e["num_shared"]) is not int or e["num_shared"]<0:errors.append("Invalid experts")
    if e.get("bias") is not False:errors.append("Only explicit bias-free expert implementation is supported; pending/bias=true must not be ignored")
    if e.get("dispatch")!="loop" or e.get("bias_gamma")!=0.0:errors.append("Only loop dispatch without dynamic router bias is supported")
    if m.get("activation")!="swiglu" or m.get("position")!="rope":errors.append("Week2 requires SwiGLU/RoPE")
    if not number(m.get("rope_theta")) or m["rope_theta"]<=0:errors.append("Explicit positive RoPE theta required")
    if not number(m.get("norm_eps")) or not 0<m["norm_eps"]<1:errors.append("Explicit norm epsilon required")
    fraction=m.get("rotary_fraction",1.0)
    if not number(fraction) or fraction not in (0.5,1.0):errors.append("rotary_fraction must be 0.5 or 1.0")
    elif 2*math.floor(fraction*(m["n_embd"]//m["n_head"])/2)<2:errors.append("Rotary dimension must be at least 2")
    pattern=m.get("attn_pattern",["G"]*m["n_layer"])
    pattern_ok=isinstance(pattern,list) and len(pattern)==m["n_layer"] and all(x in ("G","L") for x in pattern)
    if not pattern_ok:errors.append("attn_pattern must have one G/L entry per layer")
    local=pattern_ok and "L" in pattern
    window=m.get("attn_window")
    if local and (not positive(window) or window>m["block_size"]):errors.append("Local attention needs attn_window in [1, block_size]")
    if not local and window is not None:errors.append("attn_window set without local layers")
    for key in ["attn_sink","attn_gate"]:
        if type(m.get(key,False)) is not bool:errors.append(key+" must be boolean")
    if m.get("attn_sink",False) and not local:errors.append("attn_sink requires local layers")
    if m.get("attn_gate",False):
        if m.get("attn_gate_input") not in ("normalized","residual"):errors.append("Explicit attn_gate_input required: normalized/residual")
        if type(m.get("attn_gate_bias")) is not bool:errors.append("Explicit boolean attn_gate_bias required")
        if m.get("attn_gate_init") not in ("zero","linear_default"):errors.append("Explicit attn_gate_init required: zero/linear_default")
    elif any(m.get(k) is not None for k in ["attn_gate_input","attn_gate_bias","attn_gate_init"]):errors.append("Gate choices set while attn_gate is disabled")
    if m.get("reversible") is not False:errors.append("Reversibility unresolved or unsupported; must be explicit false")
    if type(m.get("mtp")) is not bool:errors.append("MTP must be explicitly true/false")
    if m.get("mtp") is True and (not number(m.get("mtp_weight")) or m["mtp_weight"]<0):errors.append("Explicit finite nonnegative MTP weight required")
    if m.get("mtp") is False and m.get("mtp_weight") not in (None,0.0):errors.append("MTP off requires weight 0")
    if m.get("ce_impl")!="torch" or m.get("attn_impl")!="eager":errors.append("Only eager attention/torch CE implemented")
    if "head_mode" in m or "tie_embeddings" in m:errors.append("Output head is fixed dense untied; head switches are removed")
    if m.get("embedding")!="ke1":errors.append("Only arm embedding ke1 is implemented with G4 raw-code projection")
    if r["batch_size"]%r["micro_batch_size"]:errors.append("Batch not divisible by microbatch")
    if o.get("name") not in ["adamw","muon"]:errors.append("Only AdamW and Muon are implemented; never replaced silently")
    if o.get("name")=="muon" and (not number(o.get("muon_lr")) or o["muon_lr"]<=0):errors.append("Explicit finite positive Muon LR (muon_lr) required")
    if o.get("name")=="adamw" and o.get("muon_lr") is not None:errors.append("muon_lr set on an AdamW arm would be ignored")
    if o.get("schedule")!="constant":errors.append("Only lead's constant schedule supported")
    if not number(o.get("lr")) or o["lr"]<=0:errors.append("Explicit finite positive arm LR required")
    betas=o.get("betas")
    if not isinstance(betas,list) or len(betas)!=2 or not all(number(b) and 0<=b<1 for b in betas):errors.append("Invalid AdamW betas")
    if not number(o.get("eps")) or o["eps"]<=0:errors.append("Invalid AdamW epsilon")
    if not number(o.get("weight_decay")) or o["weight_decay"]<0:errors.append("Invalid weight decay")
    if type(r.get("seed")) is not int or not 0<=r["seed"]<2**32:errors.append("Seed outside supported RNG range")
    if not positive(m.get("ke_max_pos")):errors.append("Invalid KE/head chunk size")
    if c.get("evaluation",{}).get("boundary_policy")!="bos_then_all_text_tokens_document_isolated":errors.append("Unsupported scoring boundary policy")
    if r.get("dtype") not in ["fp32","bf16"]:errors.append("Unsupported precision")
    if r.get("compile") is not False:errors.append("Compiled backend not verified")
    if not number(r.get("grad_clip")) or r["grad_clip"]<=0:errors.append("Invalid gradient clip")
    if not number(r.get("max_time_min")) or r["max_time_min"]<=0:errors.append("Invalid time cap")
    return errors
