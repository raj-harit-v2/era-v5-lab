"""RMSNorm in the G5 form (teams/05-architecture/harness/week2/model.py), the torch reference for model.norm=rmsnorm.

    y = (float(s) * rsqrt(mean(float(s)^2) + eps) * weight).to(s.dtype),    s = x (+ residual)

Weight only, no bias, no mean subtraction. forward(x, residual) normalises x + residual: Block.f passes p and a
for LN2 so the Triton module (kernels/rms_norm.py) can do the add in the same kernel; here it is a plain add.
"""
from __future__ import annotations

import torch
from torch import nn


class RMSNorm(nn.Module):
    fuses_add = True     # forward(x, residual) is norm(x + residual)

    def __init__(self, width: int, eps: float = 1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width))
        self.eps = eps

    def forward(self, x: torch.Tensor, residual: torch.Tensor | None = None) -> torch.Tensor:
        if residual is not None:
            x = x + residual
        xf = x.float()
        return (xf * torch.rsqrt(xf.square().mean(-1, keepdim=True) + self.eps) * self.weight).to(x.dtype)

    def extra_repr(self) -> str:
        return f"{self.weight.numel()}, eps={self.eps}"
