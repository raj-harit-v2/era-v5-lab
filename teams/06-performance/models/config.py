"""Model config and YAML loading.  Contract: bench, report and tests read these field names.

    cfg = load_config("configs/base.yaml", ["model.n_layer=4", "run.batch_size=8"])
    mcfg = model_config(cfg)          # ModelConfig

No model number is hard-coded anywhere else. The YAML is the only source of values: a key written twice, an
override of a key the config lacks, or a model field missing from the YAML is an error. New fields get a default,
so old configs still load; the dataclass defaults only serve tests that build one part directly.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml

MOE_KEYS = {"num_experts", "top_k", "num_shared", "bias_gamma", "dispatch", "ffn_hidden"}   # SparseMoE keyword arguments
CE_IMPLS = ("torch", "chunked", "fused", "fused_cached", "fused_liger", "fused_cce")
ATTN_IMPLS = ("sdpa", "eager")
ACTIVATIONS = ("gelu", "swiglu")
REV_IMPLS = ("two_pass", "one_pass")
POSITIONS = ("learned", "rope")


@dataclass
class ModelConfig:
    vocab_size: int = 131072         # exact BrahmicTokenizer-131K vocabulary, no padding
    block_size: int = 512            # sequence length T
    n_layer: int = 9
    n_head: int = 8                  # query heads
    n_kv_head: int | None = None     # GQA: key/value heads, divides n_head; None = n_head (plain multi-head)
    n_embd: int = 256                # d_model
    attn_impl: str = "sdpa"          # sdpa (F.scaled_dot_product_attention) | eager (explicit softmax; G5 config_v0)
    position: str = "learned"        # learned (block_size x d table added to the embedding) | rope (rotary q, k)
    rope_theta: float | None = None  # RoPE base: pair i of a head turns by t * rope_theta^(-2i / head_dim);
                                     # required with position=rope (no silent default), unused by learned
    mlp_ratio: int = 4               # MLP / expert hidden = mlp_ratio * n_embd
    activation: str = "gelu"         # gelu: c_proj(GELU(c_fc x)), with biases | swiglu: c_proj(SiLU(c_gate x) * c_fc x),
                                     # no biases. Dense MLP, routed experts (every dispatch) and shared experts
    embedding: str = "table"         # table (tied head) | ke1 (Kronecker v1, untied head) | ke2 (Kronecker v2, G4 raw table, untied head)
    tie_embeddings: bool | None = None  # None: tie iff embedding==table; True: require table; False: never tie
    ke_max_pos: int = 32             # KE v1 byte positions: codec dim = 256 * ke_max_pos
    ke_mode: str = "dynamic"         # KE v1: dynamic (codec every step) | cached (V x D table)
    ffn: str = "mlp"                 # mlp | moe
    moe: dict = field(default_factory=lambda: dict(num_experts=8, top_k=2, num_shared=0,
                                                   bias_gamma=0.01, dispatch="loop", ffn_hidden=None))
    reversible: bool = False         # True: midpoint reversible stack
    rev_h: float = 1.0               # midpoint step size
    rev_impl: str = "two_pass"       # two_pass (invert + recompute) | one_pass (single f in backward)
    ce_impl: str = "torch"           # torch | chunked | fused | fused_cached | fused_liger | fused_cce
    ce_chunks: int = 8                # number of token chunks for chunked / fused
    ce_vocab_chunk: int = 4096        # vocabulary tile size for fused_cce
    ce_token_chunk: int = 16           # token tile size for fused_cached / fused_liger
    mtp: bool = False                # True: second untied head predicts token t+2 (G5 config_v0); loss = ntp + mtp

    def __post_init__(self):
        assert self.embedding in ("table", "ke1", "ke2"), f"embedding={self.embedding!r}"
        assert self.tie_embeddings in (None, True, False), f"tie_embeddings={self.tie_embeddings!r}"
        if self.tie_embeddings is True:
            assert self.embedding == "table", (
                "tie_embeddings=True requires model.embedding='table' (KE1/KE2 has no [V, d] table)"
            )
        assert self.ffn in ("mlp", "moe"), f"ffn={self.ffn!r}"
        assert self.n_embd % self.n_head == 0, "n_embd must be divisible by n_head"
        assert self.attn_impl in ATTN_IMPLS, f"attn_impl={self.attn_impl!r} not in {ATTN_IMPLS}"
        assert self.activation in ACTIVATIONS, f"activation={self.activation!r} not in {ACTIVATIONS}"
        assert self.rev_impl in REV_IMPLS, f"rev_impl={self.rev_impl!r} not in {REV_IMPLS}"
        assert self.position in POSITIONS, f"position={self.position!r} not in {POSITIONS}"
        if self.position == "rope":
            assert (self.n_embd // self.n_head) % 2 == 0, "position=rope needs an even head dim"
            assert self.rope_theta is not None, (
                "position=rope needs model.rope_theta (e.g. model.rope_theta=10000); null is for learned only")
            assert self.rope_theta > 0, "rope_theta must be > 0"
        assert self.ce_impl in CE_IMPLS, f"ce_impl={self.ce_impl!r} not in {CE_IMPLS}"
        assert self.ce_chunks > 0 and self.ce_vocab_chunk > 0 and self.ce_token_chunk > 0, \
            "cross-entropy chunk sizes must be positive"
        unknown = sorted(set(self.moe) - MOE_KEYS)
        assert not unknown, f"unknown moe keys {unknown}; known: {sorted(MOE_KEYS)}"
        hidden = self.moe.get("ffn_hidden")
        assert hidden is None or (type(hidden) is int and hidden > 0), (
            "model.moe.ffn_hidden must be a positive integer or null"
        )
        if self.ffn == "moe" and hidden is None:
            assert type(self.mlp_ratio) is int and self.mlp_ratio > 0, (
                "MoE requires ffn_hidden or positive mlp_ratio"
            )
        if self.n_kv_head is None:
            self.n_kv_head = self.n_head
        assert self.n_kv_head > 0 and self.n_head % self.n_kv_head == 0, "n_kv_head must be > 0 and divide n_head"

    def to_dict(self):
        return asdict(self)


def _merge(base, over):
    """base with over's values on top; nested dicts merge key by key (inherit: child over parent)."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses a key written twice in one mapping (plain YAML keeps the last one silently)."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ValueError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}: "
                                 f"{key_node.start_mark.name}")
            seen.add(key)
        return super().construct_mapping(node, deep)


def load_config(path, overrides=()):
    """YAML with `inherit: <parent>.yaml`, then `a.b.c=value` overrides (values parsed as YAML).
    An override must name a key the config already has."""
    path = Path(path)
    with open(path) as f:
        cfg = yaml.load(f, Loader=_UniqueKeyLoader) or {}
    parent = cfg.pop("inherit", None)
    if parent:
        cfg = _merge(load_config(path.parent / parent), cfg)
    for o in overrides:
        key, sep, val = o.partition("=")
        if not sep:
            raise ValueError(f"override {o!r} must look like key=value")
        node = cfg
        *head, last = key.split(".")
        for h in head:
            if not isinstance(node.get(h), dict):
                raise KeyError(f"override {o!r}: the config has no section {h!r} (see configs/base.yaml)")
            node = node[h]
        if last not in node:
            raise KeyError(f"override {o!r}: the config has no key {key!r} (see configs/base.yaml)")
        node[last] = yaml.safe_load(val)
    return cfg


def model_config(cfg: dict) -> ModelConfig:
    """ModelConfig from a whole config (its model section) or a model dict; every field must be set."""
    m = dict(cfg.get("model", cfg))
    known = {f.name for f in fields(ModelConfig)}
    unknown = sorted(set(m) - known)
    if unknown:
        raise KeyError(f"unknown model keys {unknown}: add them to ModelConfig (with a default) first")
    missing = sorted(known - set(m))
    if missing:
        raise KeyError(f"model keys {missing} are not in the config: set them in configs/base.yaml")
    return ModelConfig(**m)
