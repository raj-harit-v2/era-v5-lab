"""Run Team 5's unmodified `train_week2.py` for a G10 rehearsal run folder.

Team 5's code is imported from a pinned lab checkout and executed as is. This launcher changes exactly two
things, both recorded in `<out>/G10_LAUNCH.json` next to Team 5's own manifest:

1. tokenizer identity: `week2.artifacts.Artifacts` defaults to tokenizer v0 (sha 2de039f2...). The frozen tokenizer
   is p1536 since 15 Nov (TSAI Gate 3 notice). `--tokenizer-sha256` replaces only that default argument.
2. device: `train_week2.py` offers `cpu` and `cuda`. `--allow-mps` adds `mps` to the argparse choices. Team 5's AMP
   context is CUDA-only, so MPS runs compute in fp32; use an arm with `run.dtype: fp32` so the manifest says so.
   MPS has no float64, so with `--allow-mps` a `.double()` on an MPS tensor makes its copy on the CPU (exact; Team 5's
   evaluator calls `.double().cpu()` on per-token losses). The KE2 backward has no deterministic MPS kernel, so on MPS
   Team 5's `use_deterministic_algorithms(True)` runs with `warn_only=True`: MPS run folders are not bit-reproducible.

Everything else (config resolution, validation, data windows, model, optimizer, evaluation, checkpoint, manifest,
summary) is Team 5's code. Usage:

    python capstone/g5_launch.py --g5-root <lab checkout> --tokenizer-sha256 <hex> [--allow-mps] -- <train_week2 args>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import runpy
import sys
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _out_dir(argv: list[str]) -> Path | None:
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            return Path(argv[i + 1])
        if a.startswith("--out="):
            return Path(a.split("=", 1)[1])
    return None


def install_mps_double_patch() -> None:
    """MPS has no float64. Team 5's evaluator does `nll.double().cpu()`; making the float64 copy of an MPS tensor on
    the CPU gives identical values (fp32 -> fp64 is exact) and only moves where the copy lives. Idempotent."""
    import torch

    if getattr(torch.Tensor.double, "_g10_mps_patch", False):
        return
    original_double = torch.Tensor.double

    def double(self, *a, **kw):
        if self.device.type == "mps":
            return original_double(self.cpu(), *a, **kw)
        return original_double(self, *a, **kw)

    double._g10_mps_patch = True
    torch.Tensor.double = double


def _mps(argv: list[str]) -> bool:
    return any(a == "--device" and i + 1 < len(argv) and argv[i + 1] == "mps" for i, a in enumerate(argv))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        raise SystemExit("usage: g5_launch.py [launcher options] -- <train_week2.py arguments>")
    cut = argv.index("--")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--g5-root", type=Path, required=True, help="lab checkout holding teams/05-architecture")
    p.add_argument("--tokenizer-sha256", required=True)
    p.add_argument("--allow-mps", action="store_true")
    opts = p.parse_args(argv[:cut])
    train_args = argv[cut + 1:]
    harness = (opts.g5_root / "teams" / "05-architecture" / "harness").resolve()
    script = harness / "train_week2.py"
    if not script.is_file():
        raise SystemExit(f"train_week2.py not found under {harness}")
    sys.path.insert(0, str(harness))
    import week2.artifacts as artifacts  # Team 5's module, unmodified

    defaults = list(artifacts.Artifacts.__init__.__defaults__)
    original_sha = defaults[0]
    defaults[0] = opts.tokenizer_sha256
    artifacts.Artifacts.__init__.__defaults__ = tuple(defaults)

    if opts.allow_mps:
        original_add = argparse.ArgumentParser.add_argument

        def add_argument(self, *names, **kw):
            if "--device" in names and "choices" in kw:
                kw = dict(kw, choices=[*kw["choices"], "mps"])
            return original_add(self, *names, **kw)

        argparse.ArgumentParser.add_argument = add_argument

        import torch

        install_mps_double_patch()

        # The KE2 projection's backward (index_put with accumulate) has no deterministic MPS kernel. On MPS only,
        # Team 5's `use_deterministic_algorithms(True)` becomes warn_only: MPS runs are NOT bit-reproducible.
        original_det = torch.use_deterministic_algorithms

        def use_deterministic_algorithms(mode, *, warn_only=False):
            return original_det(mode, warn_only=True if "--device=mps" in sys.argv or _mps(sys.argv) else warn_only)

        torch.use_deterministic_algorithms = use_deterministic_algorithms

    record = {
        "launcher": "teams/10-post-training/capstone/g5_launch.py",
        "launcher_sha256": sha256_file(Path(__file__)),
        "g5_root": str(opts.g5_root),
        "train_week2_sha256": sha256_file(script),
        "week2_sources_sha256": {f.name: sha256_file(f) for f in sorted((harness / "week2").glob("*.py"))},
        "patches": {
            "Artifacts.expected_tokenizer_sha": {"team5_default": original_sha, "used": opts.tokenizer_sha256},
            "device_choices_add_mps": bool(opts.allow_mps),
            "mps_tensor_double_on_cpu": bool(opts.allow_mps),
            "deterministic_warn_only_on_mps": bool(opts.allow_mps) and _mps(train_args),
        },
        "train_week2_args": train_args,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "started_unix": time.time(),
    }
    sys.argv = [str(script), *train_args]
    status = 0
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e:  # argparse errors from Team 5's own checks
        status = e.code if isinstance(e.code, int) else 1
    record["finished_unix"] = time.time()
    record["exit_status"] = status
    out = _out_dir(train_args)
    if out is not None and out.is_dir():
        (out / "G10_LAUNCH.json").write_text(json.dumps(record, indent=2), encoding="utf8")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
