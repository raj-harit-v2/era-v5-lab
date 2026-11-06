"""Reference GQA/RoPE/SwiGLU MoE with G4-compatible projected byte codes.

Dense untied output head per TSAI review; Kronecker projection is input-only.
No fused kernels, reversible layers or expert parallelism are claimed.
"""

import math
import torch
from torch import nn
from torch.nn import functional as F


def codec(rows, lengths):
    """Independent dense FP32 reference; same unbiased-std convention as G4."""
    p = rows.shape[1]
    n = len(rows)
    lengths = lengths.long()
    positions = torch.arange(p, device=rows.device).expand(n, -1)
    indices = rows.long() * p + positions
    source = (positions < lengths[:, None]).float() * lengths.clamp_min(
        1
    ).float().rsqrt()[:, None]
    out = torch.zeros(n, 256 * p, device=rows.device)
    # Each position has a distinct flattened column, including padded positions.
    out.scatter_(1, indices, source)
    centered = out - out.mean(-1, keepdim=True)
    return centered / (centered.std(-1, keepdim=True, correction=1) + 1e-6)


class KE2(nn.Module):
    def __init__(self, rows, lengths, width):
        super().__init__()
        self.register_buffer("rows", torch.as_tensor(rows, dtype=torch.uint8).clone())
        self.register_buffer(
            "lengths", torch.as_tensor(lengths, dtype=torch.long).clone()
        )
        self.p = rows.shape[1]
        self.vocab = len(rows)
        self.width = width
        self.projection = nn.Linear(256 * self.p, width, bias=False)
        nn.init.normal_(self.projection.weight, std=1 / math.sqrt(256 * self.p))

    def projected(self, ids):
        """Sparse closed-form application of the same normalized G4 code.

        Avoid allocating V x (256P) raw codes. Equivalent in real arithmetic;
        FP32 reduction ordering differs and is tested against the dense reference.
        """
        shape = ids.shape
        flat = ids.reshape(-1)
        lengths = self.lengths[flat]
        positions = torch.arange(self.p, device=ids.device)
        indices = self.rows[flat].long() * self.p + positions
        weight = self.projection.weight.float().t()
        selected = weight[indices]  # [tokens, P, d_model]
        valid = positions[None, :] < lengths[:, None]
        selected_sum = (selected * valid[:, :, None]).sum(1)
        dim = 256 * self.p
        l = lengths.float()
        scale = l.clamp_min(1).rsqrt()
        mean = l * scale / dim
        variance = (l * (scale - mean).square() + (dim - l) * mean.square()) / (dim - 1)
        denom = variance.sqrt() + 1e-6
        high = (scale - mean) / denom
        low = -mean / denom
        result = (high - low)[:, None] * selected_sum + low[:, None] * weight.sum(0)
        return result.reshape(*shape, self.width)

    def forward(self, ids):
        return self.projected(ids)


class RMSNorm(nn.Module):
    def __init__(self, width, eps):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width))
        self.eps = eps

    def forward(self, x):
        return (
            x.float()
            * torch.rsqrt(x.float().square().mean(-1, keepdim=True) + self.eps)
            * self.weight
        ).to(x.dtype)


class GQA(nn.Module):
    def __init__(self, m, layer_index=0):
        super().__init__()
        w = m["n_embd"]
        self.nh = m["n_head"]
        self.nkv = m["n_kv_head"]
        self.d = w // self.nh
        # Each query head has its own projection. Groups of queries share K and V.
        self.q = nn.Linear(w, w, bias=False)
        self.k = nn.Linear(w, self.nkv * self.d, bias=False)
        self.v = nn.Linear(w, self.nkv * self.d, bias=False)
        self.o = nn.Linear(w, w, bias=False)
        self.theta = m["rope_theta"]
        self.rotary_dim = 2 * math.floor(m.get("rotary_fraction", 1.0) * self.d / 2)
        pattern = m.get("attn_pattern", ["G"] * m["n_layer"])
        self.local = pattern[layer_index] == "L"
        self.window = m.get("attn_window") if self.local else None
        self.sink = (
            nn.Parameter(torch.zeros(self.nh, dtype=torch.float32))
            if self.local and m.get("attn_sink", False)
            else None
        )
        self.gate = None
        if m.get("attn_gate", False):
            required = ["attn_gate_input", "attn_gate_bias", "attn_gate_init"]
            if any(m.get(k) is None for k in required):
                raise ValueError("Gate choices must be explicit")
            if m["attn_gate_input"] not in ("normalized", "residual"):
                raise ValueError("Invalid gate input")
            self.gate_input = m["attn_gate_input"]
            self.gate = nn.Linear(w, w, bias=m["attn_gate_bias"])
            if m["attn_gate_init"] == "zero":
                nn.init.zeros_(self.gate.weight)
                if self.gate.bias is not None:
                    nn.init.zeros_(self.gate.bias)
            elif m["attn_gate_init"] != "linear_default":
                raise ValueError("Invalid gate initialization")

    def rotary(self, x):
        # One window per document; position offset zero for each independent window.
        inv = self.theta ** (
            -torch.arange(0, self.rotary_dim, 2, device=x.device).float()
            / self.rotary_dim
        )
        angle = (
            torch.arange(x.shape[-2], device=x.device).float()[:, None] * inv[None, :]
        )
        a, b = (
            x.float()[..., : self.rotary_dim : 2],
            x.float()[..., 1 : self.rotary_dim : 2],
        )
        rotated = (
            torch.stack(
                (a * angle.cos() - b * angle.sin(), a * angle.sin() + b * angle.cos()),
                -1,
            )
            .flatten(-2)
            .to(x.dtype)
        )
        return (
            rotated
            if self.rotary_dim == self.d
            else torch.cat((rotated, x[..., self.rotary_dim :]), dim=-1)
        )

    def forward(self, x, residual=None):
        b, t, w = x.shape
        q = self.rotary(self.q(x).view(b, t, self.nh, self.d).transpose(1, 2))
        k = self.rotary(
            self.k(x).view(b, t, self.nkv, self.d).transpose(1, 2)
        ).repeat_interleave(self.nh // self.nkv, dim=1)
        v = (
            self.v(x)
            .view(b, t, self.nkv, self.d)
            .transpose(1, 2)
            .repeat_interleave(self.nh // self.nkv, dim=1)
        )
        logits = q.float() @ k.float().transpose(-2, -1) / math.sqrt(self.d)
        mask = torch.ones(t, t, dtype=torch.bool, device=x.device).tril()
        # Intersect the causal mask with the local window on local layers.
        if self.local:
            positions = torch.arange(t, device=x.device)
            mask = mask & ((positions[:, None] - positions[None, :]) < self.window)
        logits = logits.masked_fill(~mask, float("-inf"))
        # A disabled (-inf) sink takes the exact legacy softmax path. This also
        # avoids changing reduction shape in the equivalence regression test.
        if self.sink is not None and not bool(torch.isneginf(self.sink).all()):
            sink = self.sink.float().view(1, self.nh, 1, 1).expand(b, -1, t, -1)
            a = torch.cat((logits, sink), dim=-1).softmax(-1)[..., :t].to(v.dtype)
        else:
            a = logits.softmax(-1).to(v.dtype)
        out = (a @ v).transpose(1, 2).reshape(b, t, w)
        # Apply the channel gate before mixing heads with the output projection.
        if self.gate is not None:
            gate_input = x if self.gate_input == "normalized" else residual
            if gate_input is None:
                raise ValueError("Residual gate input requires the pre-norm residual")
            out = out * torch.sigmoid(self.gate(gate_input))
        return self.o(out)


class SwiGLU(nn.Module):
    def __init__(self, w, h, bias=False):
        super().__init__()
        self.gate = nn.Linear(w, h, bias=bias)
        self.up = nn.Linear(w, h, bias=bias)
        self.down = nn.Linear(h, w, bias=bias)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))


class MoE(nn.Module):
    def __init__(self, m):
        super().__init__()
        w = m["n_embd"]
        h = m["moe"]["ffn_hidden"]
        cfg = m["moe"]
        self.topk = cfg["top_k"]
        self.router = nn.Linear(w, cfg["num_experts"], bias=False)
        self.experts = nn.ModuleList(
            SwiGLU(w, h, cfg["bias"]) for _ in range(cfg["num_experts"])
        )
        self.shared = nn.ModuleList(
            SwiGLU(w, h, cfg["bias"]) for _ in range(cfg["num_shared"])
        )

    def forward(self, x, valid):
        shape = x.shape
        flat = x.reshape(-1, shape[-1])
        active = valid.reshape(-1)
        with torch.autocast(device_type=x.device.type, enabled=False):
            scores = F.linear(flat.float(), self.router.weight.float()).softmax(-1)
        gates, choice = scores.topk(self.topk, dim=-1)
        gates = gates / gates.sum(-1, keepdim=True)
        output = torch.zeros_like(flat)
        # Each expert sees only selected non-padding rows. Distinct row indices
        # within an expert -> no many-to-one atomic combine operation.
        for e, expert in enumerate(self.experts):
            selected = (choice == e) & active[:, None]
            rows = selected.any(-1).nonzero().flatten()
            if rows.numel():
                weight = (gates[rows] * selected[rows]).sum(-1, keepdim=True)
                values = expert(flat[rows]) * weight.to(flat.dtype)
                output = output + torch.zeros_like(flat).index_copy(0, rows, values)
        for expert in self.shared:
            output = output + expert(flat) * active[:, None]
        return output.reshape(shape)


class Block(nn.Module):
    def __init__(self, m, layer_index=0):
        super().__init__()
        self.n1 = RMSNorm(m["n_embd"], m["norm_eps"])
        self.n2 = RMSNorm(m["n_embd"], m["norm_eps"])
        self.attn = GQA(m, layer_index)
        self.moe = MoE(m)

    def forward(self, x, valid):
        # Normalize before attention, then add its output to the residual stream.
        x = x + self.attn(self.n1(x), residual=x)
        # Feed the updated residual through the pre-norm MoE sublayer.
        return x + self.moe(self.n2(x), valid)


class LanguageModel(nn.Module):
    def __init__(self, m, rows, lengths):
        super().__init__()
        self.spec = m
        self.embedding = KE2(rows, lengths, m["n_embd"])
        self.blocks = nn.ModuleList(Block(m, i) for i in range(m["n_layer"]))
        self.norm = RMSNorm(m["n_embd"], m["norm_eps"])
        self.mtp_head = (
            nn.Linear(m["n_embd"], m["vocab_size"], bias=False) if m["mtp"] else None
        )
        self.head = nn.Linear(m["n_embd"], m["vocab_size"], bias=False)

    def hidden(self, ids, valid):
        x = self.embedding(ids)
        for block in self.blocks:
            x = block(x, valid)
        return self.norm(x)

    def forward(self, ids, valid, return_mtp=False):
        h = self.hidden(ids, valid)
        logits = self.head(h)
        return (
            (logits, self.mtp_head(h) if self.mtp_head is not None else None)
            if return_mtp
            else logits
        )

    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())
