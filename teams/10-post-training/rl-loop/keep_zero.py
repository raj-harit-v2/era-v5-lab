"""Keep Deletion-Tuning-deleted weights at zero while the model trains further (RL after DT-SFT).

After SFT with Deletion Tuning the mask is baked: a deleted weight is exactly 0.0 and the model is a plain
LanguageModel. Any later optimizer step could make such a weight nonzero again (a nonzero gradient reaches it: the
entry is not special to autograd). Two ways to hold the deletion:
  gradient mask (default): a hook multiplies the gradient of every masked parameter by the keep mask, so a deleted
      entry never sees a gradient. With weight decay 0 AdamW then leaves it exactly where it was (zero gradient,
      zero moments, zero step). Only undeleted weights train.
  enforce: additionally set the deleted entries back to 0 after each step (a backstop; off by default so that the
      gradient mask alone is what the integrity check tests).
`deleted_nonzero()` counts the deleted entries that are not exactly 0 right now; `check()` raises when it is not 0.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch


def load_masks(path: str | Path) -> dict[str, torch.Tensor]:
    """{param name: bool keep mask} from `<path>` (packbits+zlib bytes, as dt/mask.py pack_masks) and `<path>.json`."""
    masks, _ = load_masks_with_digests(path)
    return masks


def load_masks_with_digests(path: str | Path) -> tuple[dict[str, torch.Tensor], dict[str, str]]:
    """Decode the mask and hash the exact bytes consumed by the decoder."""
    import importlib.util  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location("g10_dt_mask_kz", Path(__file__).resolve().parent.parent / "dt" / "mask.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    path = Path(path)
    blob = path.read_bytes()
    meta = Path(str(path) + ".json").read_bytes()
    return mod.unpack_masks(blob, json.loads(meta)), {
        "sha256": hashlib.sha256(blob).hexdigest(),
        "metadata_sha256": hashlib.sha256(meta).hexdigest(),
    }


class KeepZero:
    def __init__(self, named_params: list[tuple[str, torch.nn.Parameter]], keep: dict[str, torch.Tensor],
                 enforce: bool = False, weight_decay: float = 0.0):
        if weight_decay != 0.0 and not enforce:
            raise ValueError("a gradient mask only holds a deleted weight at 0 when weight decay is 0 (or enforce: true)")
        by_name = dict(named_params)
        missing = [n for n in keep if n not in by_name]
        if missing:
            raise ValueError(f"{len(missing)} masked parameters are not trainable or not in the model, e.g. {missing[:2]}")
        self.enforce_after_step = enforce
        self.params: dict[str, torch.nn.Parameter] = {}
        self.keep: dict[str, torch.Tensor] = {}
        self.all_params = [p for _, p in named_params]
        for name in sorted(keep):
            p = by_name[name]
            k = keep[name].to(p.device)
            if tuple(k.shape) != tuple(p.shape):
                raise ValueError(f"{name}: mask shape {tuple(k.shape)} != parameter shape {tuple(p.shape)}")
            self.params[name], self.keep[name] = p, k
            p.register_hook(lambda g, kf=k.to(p.dtype): g * kf)
        self.n_masked = sum(k.numel() for k in self.keep.values())
        self.n_deleted0 = sum(int((~k).sum()) for k in self.keep.values())
        self.n_total = sum(p.numel() for p in self.all_params)

    @torch.no_grad()
    def deleted_nonzero(self) -> int:
        """Deleted entries (mask False) that are not exactly 0 now."""
        return int(sum(int(((p != 0) & ~self.keep[n]).sum()) for n, p in self.params.items()))

    @torch.no_grad()
    def deleted_zero(self) -> int:
        return int(sum(int(((p == 0) & ~self.keep[n]).sum()) for n, p in self.params.items()))

    @torch.no_grad()
    def zero_share(self) -> float:
        """Share of all trainable weights that are exactly 0 (deleted weights plus any natural zeros)."""
        return sum(int((p == 0).sum()) for p in self.all_params) / max(self.n_total, 1)

    @torch.no_grad()
    def enforce(self) -> None:
        for n, p in self.params.items():
            p.mul_(self.keep[n].to(p.dtype))

    def check(self, where: str) -> int:
        bad = self.deleted_nonzero()
        if bad:
            raise RuntimeError(f"{where}: {bad} deleted weights are nonzero (the deletion did not survive training)")
        return bad
