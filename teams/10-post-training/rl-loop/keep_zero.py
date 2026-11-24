"""Keep Deletion-Tuning-deleted weights at zero while the model trains further (RL after DT-SFT).

After SFT with Deletion Tuning the mask is baked: a deleted weight is exactly 0.0 and the model is a plain
LanguageModel. Any later optimizer step could make such a weight nonzero again (a nonzero gradient reaches it: the
entry is not special to autograd). Two ways to hold the deletion:
  gradient mask (default): a hook multiplies the gradient of every masked parameter by the keep mask, so a deleted
      entry never sees a gradient. Adam/AdamW then leave an exact 0 exactly where it was, with or without weight
      decay (zero gradient, zero moments, zero step; decay of 0 is 0). Only undeleted weights train. An
      orthogonalizing optimizer such as Muon does not: `check_optimizer` refuses it unless enforce.
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


_ELEMENTWISE = (torch.optim.Adam, torch.optim.AdamW)  # bound at import: a later patch of torch.optim cannot widen it


class KeepZero:
    def __init__(self, named_params: list[tuple[str, torch.nn.Parameter]], keep: dict[str, torch.Tensor],
                 enforce: bool = False, weight_decay: float = 0.0):
        # weight_decay is accepted and no longer refused: an exact 0 stays 0 under Adam/AdamW decay (see check_optimizer)
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

    def check_optimizer(self, opt) -> None:
        """Refuse an optimizer the gradient mask cannot protect. Under an elementwise optimizer (Adam/AdamW) an entry
        that is exactly 0 with zero gradient stays 0, with or without weight decay (decoupled: 0 x (1 - lr*wd) = 0;
        L2: wd x 0 adds nothing); checked 23 Nov on baked stand-in weights, AdamW and Adam wd 0.1, 3 steps: 0 of 26.74M
        deleted entries moved. An orthogonalizing update such as Team 5's Muon mixes the whole matrix: in the DR2 probe
        (main f360a794 build_optimizer, CPU fp32) one Muon step made 26.48M of 26.74M elementwise-deleted entries
        nonzero. enforce: true re-zeroes after each step and is allowed with any optimizer."""
        if self.enforce_after_step:
            return
        if not isinstance(opt, _ELEMENTWISE):
            raise ValueError(f"keep_zero gradient mask needs Adam/AdamW, got {type(opt).__name__} "
                             "(an orthogonalizing optimizer such as Muon fills the deleted entries); set enforce: true")

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
