"""Tiny MoE smoke test.

Kronecker embeddings, eager multi-head attention, top-k experts.
A second linear head predicts t+2. Each step takes a new batch from a seeded stream.
Seed 1234, run twice: the loss file must match, the loss must fall, no NaN.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from kronecker_embeddings import KroneckerEmbedding
from torch import nn

from check_config import errors_for, load_settings, merge


def as_map(settings: list[dict]) -> dict:
    return {item["key"]: item["value"] for item in settings}


def byte_buffers(vocab: int, pos_dim: int) -> tuple[torch.Tensor, torch.Tensor]:
    byte_buffer = torch.zeros(vocab, pos_dim, dtype=torch.uint8)
    length_buffer = torch.zeros(vocab, dtype=torch.int16)
    for token_id in range(1, vocab):
        byte_buffer[token_id, 0] = token_id % 256
        length_buffer[token_id] = 1
    return byte_buffer, length_buffer


class CausalAttention(nn.Module):
    def __init__(self, d_model: int, n_head: int):
        super().__init__()
        if n_head < 1 or d_model % n_head:
            raise SystemExit(f"model.d_model {d_model} is not divisible by model.n_head {n_head}")
        self.n_head = n_head
        self.head_dim = d_model // n_head
        self.q = nn.Linear(d_model, d_model, bias=False)
        self.k = nn.Linear(d_model, d_model, bias=False)
        self.v = nn.Linear(d_model, d_model, bias=False)
        self.o = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, width = x.shape
        q = self.q(x).view(batch, length, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k(x).view(batch, length, self.n_head, self.head_dim).transpose(1, 2)
        v = self.v(x).view(batch, length, self.n_head, self.head_dim).transpose(1, 2)
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.head_dim)
        mask = torch.triu(torch.ones(length, length, dtype=torch.bool, device=x.device), 1)
        weights = torch.softmax(scores.masked_fill(mask, -1e9), dim=-1)
        mixed = (weights @ v).transpose(1, 2).contiguous().view(batch, length, width)
        return self.o(mixed)


class TopKMoE(nn.Module):
    def __init__(self, d_model: int, d_ff: int, n_expert: int, top_k: int):
        super().__init__()
        if not (1 <= top_k <= n_expert):
            raise SystemExit(f"moe.top_k {top_k} is outside 1..{n_expert}")
        self.top_k = top_k
        self.router = nn.Linear(d_model, n_expert, bias=False)
        self.up = nn.Parameter(torch.empty(n_expert, d_model, d_ff))
        self.down = nn.Parameter(torch.empty(n_expert, d_ff, d_model))
        nn.init.normal_(self.up, std=0.02)
        nn.init.normal_(self.down, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gates = torch.softmax(self.router(x), dim=-1)
        chosen_gates, choice = torch.topk(gates, self.top_k, dim=-1)
        chosen_gates = chosen_gates / chosen_gates.sum(dim=-1, keepdim=True)
        hidden = torch.einsum("btd,edh->bteh", x, self.up)
        hidden = F.gelu(hidden)
        expert_out = torch.einsum("bteh,ehd->bted", hidden, self.down)
        index = choice.unsqueeze(-1).expand(-1, -1, -1, x.shape[-1])
        picked = expert_out.gather(2, index)
        return (picked * chosen_gates.unsqueeze(-1)).sum(dim=2)


class Block(nn.Module):
    def __init__(self, d_model: int, n_head: int, d_ff: int, n_expert: int, top_k: int):
        super().__init__()
        self.norm_1 = nn.RMSNorm(d_model)
        self.attn = CausalAttention(d_model, n_head)
        self.norm_2 = nn.RMSNorm(d_model)
        self.moe = TopKMoE(d_model, d_ff, n_expert, top_k)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm_1(x))
        x = x + self.moe(self.norm_2(x))
        return x


class TinyMoE(nn.Module):
    def __init__(self, cfg: dict):
        super().__init__()
        vocab = int(cfg["tiny.vocab"])
        d_model = int(cfg["model.d_model"])
        pos_dim = int(cfg["embedding.pos_dim"])
        raw, lengths = byte_buffers(vocab, pos_dim)
        self.embed = KroneckerEmbedding(
            vocab_size=vocab,
            d_model=d_model,
            pos_dim=pos_dim,
            mode="cached",
            byte_buffer=raw,
            length_buffer=lengths,
        )
        n_head = int(cfg["model.n_head"])
        self.blocks = nn.ModuleList(
            Block(
                d_model,
                n_head,
                int(cfg["model.d_ff"]),
                int(cfg["moe.n_expert"]),
                int(cfg["moe.top_k"]),
            )
            for _ in range(int(cfg["model.n_layer"]))
        )
        self.norm = nn.RMSNorm(d_model)
        self.head = nn.Linear(d_model, vocab, bias=False)
        self.mtp_head = nn.Linear(d_model, vocab, bias=False)

    def forward(self, token_ids: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.embed(token_ids)
        for block in self.blocks:
            hidden = block(hidden)
        hidden = self.norm(hidden)
        return self.head(hidden), self.mtp_head(hidden)


def stream_for(cfg: dict, seed: int) -> torch.Tensor:
    """One new batch per step. Token t+1 is token t plus one, so both heads can learn."""
    generator = torch.Generator()
    generator.manual_seed(seed)
    vocab = int(cfg["tiny.vocab"])
    n_seq = int(cfg["tiny.steps"]) * int(cfg["tiny.batch"])
    starts = torch.randint(1, vocab, (n_seq, 1), generator=generator)
    offsets = torch.arange(int(cfg["data.seq_len"])).view(1, -1)
    return (starts - 1 + offsets) % (vocab - 1) + 1


def gpu_alloc_gb(device: torch.device) -> float:
    if device.type != "cuda":
        return 0.0
    return torch.cuda.memory_allocated(device) / (1024 ** 3)


def run(cfg: dict, out_dir: Path, device: torch.device) -> None:
    seed = int(cfg["run.seed"])
    torch.manual_seed(seed)
    model = TinyMoE(cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(cfg["optim.lr"]))
    stream = stream_for(cfg, seed)
    batch = int(cfg["tiny.batch"])
    clip = float(cfg["run.grad_clip"])
    out_dir.mkdir(parents=True, exist_ok=True)
    losses = []
    metrics_path = out_dir / "metrics.jsonl"
    with metrics_path.open("w") as handle:
        for step in range(int(cfg["tiny.steps"])):
            tokens = stream[step * batch:(step + 1) * batch].to(device)
            started = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            logits, mtp_logits = model(tokens)
            ntp = F.cross_entropy(
                logits[:, :-1].reshape(-1, logits.shape[-1]),
                tokens[:, 1:].reshape(-1),
            )
            mtp = F.cross_entropy(
                mtp_logits[:, :-2].reshape(-1, mtp_logits.shape[-1]),
                tokens[:, 2:].reshape(-1),
            )
            (ntp + mtp).backward()
            # The norm before clipping. The G8 alarms watch it for spikes.
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
            optimizer.step()
            value = float(ntp.detach())
            mtp_value = float(mtp.detach())
            if math.isnan(value) or math.isnan(mtp_value):
                raise SystemExit(f"NaN at step {step}")
            losses.append(value)
            elapsed = max(time.perf_counter() - started, 1e-9)
            row = {
                "step": step,
                "tokens_per_second": tokens.numel() / elapsed,
                "loss_ntp": value,
                "loss_mtp": mtp_value,
                "loss": value,
                "lr": float(cfg["optim.lr"]),
                "gpu_alloc_gb": gpu_alloc_gb(device),
                "gradient_norm": float(grad_norm),
            }
            handle.write(json.dumps(row) + "\n")
    (out_dir / "losses.txt").write_text("\n".join(f"{item:.8f}" for item in losses) + "\n")
    if not (losses[-1] < losses[0]):
        raise SystemExit(f"loss did not fall: {losses[0]} -> {losses[-1]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tiny", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    settings = merge(load_settings(args.config), args.tiny)
    found = errors_for(settings)
    if found:
        raise SystemExit("\n".join(found))
    run(as_map(settings), args.out, torch.device(args.device))


if __name__ == "__main__":
    main()
