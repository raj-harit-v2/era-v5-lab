"""Small-model SFT trainer for the WP3 bench: one loss, pluggable methods (full | lora | dt).

    python train.py --train <slice>/train.tok.jsonl --model HuggingFaceTB/SmolLM2-135M \
        --revision 93efa2f097d58c2a74874c7e644dbc9b0cee75a2 --method full --steps 400 --lr 3e-5 --seed 1 --out <dir>

Loss: exactly the contract of `sft/train_probe.py` (imported, not copied): the logit at t predicts token t+1 and is
supervised only if loss_mask[t+1] == 1; padding comes from row lengths; the update loss is the sum of token NLL
over every valid shifted target in all microbatches divided by their global count; a row without a target is
rejected. Logits are computed only at target positions (same value, less memory) and cross-entropy runs in FP32.

Weights: FP32 master weights in FP32 storage (AdamW), FP32 compute. On Apple MPS and CPU no autocast is used (M1 has no
BF16 units). On CUDA `--autocast bf16` runs forward/backward under BF16 autocast while weights, gradients and AdamW
state stay FP32 (the plan's GPU setting); the report records the compute dtype. Step 1 records a stored-weight writeback check on one trainable tensor:
the change actually stored versus the AdamW step-1 update recomputed in FP32 from the clipped gradient, the
fraction of entries that moved, and the fraction that would have moved had the tensor been stored in BF16.
After the last step the model is saved (FP32 safetensors, Hugging Face layout, so `evaluate.py` and Team 9's
eval-mini can load the folder) and reloaded in a fresh object: every tensor must be bit-identical and the logits
on a fixed batch must match exactly (full) or within the stated tolerance (lora: merged weights).

This file never imports `evaluate.py` and refuses rows whose `split` is not "train" (eval firewall).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import random
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = _load("g10_train_probe_for_bench", HERE.parent / "train_probe.py")
dtmask = _load("g10_dt_mask", HERE.parents[1] / "dt" / "mask.py")
IGNORE = probe.IGNORE
ZeroTargetError = probe.ZeroTargetError
masked_nll_sum = probe.masked_nll_sum
METHODS = ("full", "lora", "dt", "markers")


def retok_markers() -> list[tuple[str, int]]:
    """(surrogate surface, id) of every mapped G10 marker, from retok.MARKER_MAP (the single source of the mapping)."""
    retok = _load("g10_bench_retok", HERE / "retok.py")
    return list(retok.MARKER_MAP.values())


# ---------------------------------------------------------------- rows and batches


def load_train_rows(path: str | Path, max_tokens: int, vocab_size: int | None = None) -> tuple[list[dict], dict]:
    rows, rejected = [], {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw.get("split") != "train":
                raise SystemExit(f"{path}: row {raw.get('id')} has split {raw.get('split')!r}; train.py reads train rows only")
            try:
                row = probe.truncate(probe.validate_example({"input_ids": raw["input_ids"], "loss_mask": raw["loss_mask"]},
                                                            vocab_size), max_tokens)
            except ZeroTargetError:
                rejected["zero_targets"] = rejected.get("zero_targets", 0) + 1
                continue
            row["id"] = raw["id"]
            rows.append(row)
    return rows, rejected


def collate(rows: list[dict], pad_id: int) -> probe.Batch:
    """Vectorised equivalent of train_probe.collate (labels and attention mask; `kinds` left as context/target only)."""
    if not rows:
        raise ValueError("empty batch")
    lens = torch.tensor([len(r["input_ids"]) for r in rows])
    T = int(lens.max())
    ids = torch.full((len(rows), T), pad_id, dtype=torch.long)
    mask = torch.zeros((len(rows), T), dtype=torch.long)
    for b, r in enumerate(rows):
        n = len(r["input_ids"])
        ids[b, :n] = torch.tensor(r["input_ids"], dtype=torch.long)
        mask[b, :n] = torch.tensor(r["loss_mask"], dtype=torch.long)
    attn = (torch.arange(T)[None, :] < lens[:, None]).long()
    tgt_ok = (mask[:, 1:] == 1) & (attn[:, 1:] == 1)
    labels = torch.where(tgt_ok, ids[:, 1:], torch.full_like(ids[:, 1:], IGNORE))
    kinds = torch.where(attn[:, 1:] == 1, torch.where(tgt_ok, probe.KIND_TARGET, probe.KIND_CONTEXT), probe.KIND_PAD)
    return probe.Batch(ids, attn, labels, kinds)


def plan_microbatches(rows: list[dict], micro_tokens: int) -> list[list[dict]]:
    """Sort the update's rows by length and pack them so that rows x longest <= micro_tokens (less padding)."""
    order = sorted(rows, key=lambda r: len(r["input_ids"]))
    groups, cur = [], []
    for r in order:
        cand = cur + [r]
        if cur and len(cand) * len(r["input_ids"]) > micro_tokens:
            groups.append(cur)
            cand = [r]
        cur = cand
    if cur:
        groups.append(cur)
    return groups


# ---------------------------------------------------------------- loss (train_probe contract)


def target_nll_sum(model: nn.Module, batch: probe.Batch) -> tuple[torch.Tensor, int]:
    """sum NLL over valid shifted targets, computing the LM head only at those positions.

    Equal to masked_nll_sum(full shifted logits, labels): rows of the logits that carry IGNORE contribute nothing.
    """
    # one unpadded row: no mask tensor, so attention takes the plain causal path (less memory on MPS)
    attn = None if batch.input_ids.size(0) == 1 else batch.attention_mask
    out = model.model(input_ids=batch.input_ids, attention_mask=attn)
    hidden = out.last_hidden_state[:, :-1, :]
    sel = batch.labels != IGNORE
    logits = model.lm_head(hidden[sel])  # (N, V)
    return masked_nll_sum(logits[None], batch.labels[sel][None])


AUTOCAST = {"dtype": None}


def autocast_ctx(device: str):
    import contextlib

    if AUTOCAST["dtype"] is None:
        return contextlib.nullcontext()
    return torch.autocast(device_type="cuda", dtype=AUTOCAST["dtype"])


def accumulate(model: nn.Module, mbs: list[probe.Batch], device) -> tuple[float, int]:
    """Backward over all microbatches; gradient of sum(NLL) / global target count (train_probe contract)."""
    global_count = sum(mb.n_targets for mb in mbs)
    if global_count == 0:
        raise ZeroTargetError("update has no valid targets")
    total = torch.zeros((), device=device)
    for mb in mbs:
        mb = probe.Batch(*(t.to(device) for t in (mb.input_ids, mb.attention_mask, mb.labels, mb.kinds)))
        with autocast_ctx(device):
            nll, _ = target_nll_sum(model, mb)
        part = nll / global_count
        part.backward()
        total += part.detach()
    return float(total), global_count


# ---------------------------------------------------------------- methods


class LoRALinear(nn.Module):
    """y = W x + (alpha / r) * B(A x); W frozen. A ~ Kaiming-uniform, B = 0 (so step 0 equals the base model)."""

    def __init__(self, base: nn.Linear, r: int, alpha: float, seed_gen: torch.Generator):
        super().__init__()
        self.base = base
        self.r, self.scale = r, alpha / r
        a = torch.empty(r, base.in_features, dtype=base.weight.dtype)
        bound = 1 / math.sqrt(base.in_features)
        a.uniform_(-bound, bound, generator=seed_gen)  # CPU generator: same init on every backend
        dev = base.weight.device
        self.lora_A = nn.Parameter(a.to(dev))
        self.lora_B = nn.Parameter(torch.zeros(base.out_features, r, dtype=base.weight.dtype, device=dev))
        base.weight.requires_grad_(False)
        if base.bias is not None:
            base.bias.requires_grad_(False)

    def forward(self, x):
        return self.base(x) + (x @ self.lora_A.t() @ self.lora_B.t()) * self.scale

    def merged_weight(self) -> torch.Tensor:
        return self.base.weight + self.scale * (self.lora_B @ self.lora_A)

    # There is no dropout on the adapter input. The effective weight below cannot express one, so a future change that
    # adds it must not leave the property silently bypassing it (the check in `weight` fails loudly instead).
    dropout = 0.0

    @property
    def weight(self) -> torch.Tensor:
        """The weight this layer applies: W + scale * B A, kept in the autograd graph (lora_A and lora_B get gradient
        through it; W stays frozen). Code that reads a layer's weight instead of calling it (G5's fused MoE path since
        #521 stacks `e.gate.weight` of every routed expert) therefore sees the adapter. `forward` is unchanged, so a
        layer that is called as a module gives the same bits as before; this property is read only by such code and is
        not a registered parameter, so state_dict keys and merge_lora are unchanged. Bias is not part of it (the fused
        path ignores expert bias, as for every layer)."""
        if self.dropout:
            raise ValueError("LoRALinear.weight cannot represent adapter dropout (lora dropout "
                             f"{self.dropout} > 0): call the module instead of reading its weight")
        return self.merged_weight()


LORA_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


def apply_method(model: nn.Module, method: str, args) -> dict:
    """Make the model trainable for `method`. Returns a description (trainable counts, targets)."""
    if method == "dt":
        names = dtmask.convert(model, dtmask.TARGET_SETS[args.dt_targets], args.dt_alpha_start, args.dt_alpha_end,
                               args.steps, seed=args.seed)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        return {"method": "dt", "targets": args.dt_targets, "target_patterns": list(dtmask.TARGET_SETS[args.dt_targets]),
                "masked_layers": len(names), "trainable": trainable, "alpha": [args.dt_alpha_start, args.dt_alpha_end],
                "eta": args.dt_eta, "lambda": args.dt_lambda, "lambda_schedule": "linear decay to 0 (official train_sft.py)",
                "prior_strength": args.dt_prior_strength, "calib_rows": args.dt_calib_rows, "official": dtmask.OFFICIAL}
    if method == "full":
        for p in model.parameters():
            p.requires_grad_(True)
        return {"method": "full", "trainable": sum(p.numel() for p in model.parameters())}
    if method == "markers":  # control: nothing but the marker rows (enabled by --train-marker-rows) is trained
        for p in model.parameters():
            p.requires_grad_(False)
        return {"method": "markers", "trainable": 0,
                "note": "CONTROL: every weight frozen; only the mapped chat-marker embedding/LM-head rows train"}
    if method == "lora":
        for p in model.parameters():
            p.requires_grad_(False)
        gen = torch.Generator().manual_seed(args.seed)
        wrapped = []
        for name, module in list(model.named_modules()):
            for child_name, child in list(module.named_children()):
                if child_name in LORA_TARGETS and isinstance(child, nn.Linear):
                    setattr(module, child_name, LoRALinear(child, args.lora_r, args.lora_alpha, gen))
                    wrapped.append(f"{name}.{child_name}")
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        return {"method": "lora", "r": args.lora_r, "alpha": args.lora_alpha, "targets": list(LORA_TARGETS),
                "wrapped_modules": len(wrapped), "trainable": trainable}
    raise ValueError(f"unknown method {method!r}")


def merge_lora(model: nn.Module) -> None:
    """Replace every LoRALinear by a plain Linear holding W + scale * B A (in place)."""
    for name, module in list(model.named_modules()):
        for child_name, child in list(module.named_children()):
            if isinstance(child, LoRALinear):
                lin = child.base
                with torch.no_grad():
                    lin.weight.copy_(child.merged_weight())
                setattr(module, child_name, lin)


def untie_head(model: nn.Module, trainable: bool = False) -> None:
    """Give the LM head its own copy of the embedding matrix (the capstone dry-run-1 head is dense and untied). The
    two start equal; from here the input rows and the output rows are separate parameters."""
    if model.lm_head.weight is not model.get_input_embeddings().weight:
        return
    model.lm_head.weight = nn.Parameter(model.lm_head.weight.detach().clone(), requires_grad=trainable)
    model.config.tie_word_embeddings = False


def enable_marker_rows(model: nn.Module, ids: list[int], scope: str = "both") -> list[nn.Parameter]:
    """HYBRID control (label it): make only the embedding rows `ids` trainable. The tied LM head shares the tensor, so
    the same rows move on the output side. A gradient hook zeroes every other row; with weight decay 0, AdamW then
    leaves those rows bit-identical (zero first and second moments give an exact zero update).
    scope (untied head only): "input" = embedding rows, "output" = LM-head rows, "both"."""
    emb, head = model.get_input_embeddings().weight, model.lm_head.weight
    if scope != "both" and emb is head:
        raise SystemExit("--marker-scope input/output needs --untie-head (tied rows cannot be trained separately)")
    chosen = {"both": (emb, head), "input": (emb,), "output": (head,)}[scope]
    out = []
    for w in {id(t): t for t in chosen}.values():
        rowmask = torch.zeros(w.shape[0], 1, dtype=w.dtype, device=w.device)
        rowmask[ids] = 1
        w.requires_grad_(True)
        w.register_hook(lambda g, m=rowmask: g * m)
        out.append(w)
    return out


def frozen_sha256(model: nn.Module, marker_ids: list[int] | None = None) -> str:
    """sha256 over every parameter that must not change: all frozen tensors, plus the non-marker rows of a
    marker-trainable embedding. Mask logits and adapter tensors are excluded (they are the trained state)."""
    h = hashlib.sha256()
    for name, p in sorted(model.named_parameters(remove_duplicate=True), key=lambda kv: kv[0]):
        if name.endswith(".gate") or "lora_" in name:
            continue
        t = p.detach()
        if p.requires_grad:
            if not marker_ids or t.dim() != 2:
                continue  # trained tensor (full FT): nothing frozen to hash
            keep = torch.ones(t.shape[0], dtype=torch.bool, device=t.device)
            keep[marker_ids] = False
            t = t[keep]
        h.update(name.encode())
        h.update(t.to("cpu").contiguous().numpy().tobytes())
    return h.hexdigest()


# ---------------------------------------------------------------- checks


def writeback_check(p0: torch.Tensor, g: torch.Tensor, p1: torch.Tensor, lr: float, wd: float, eps: float) -> dict:
    """AdamW step 1 with bias correction: m_hat = g, v_hat = g^2, so p1 = p0 (1 - lr wd) - lr g / (|g| + eps)."""
    p32 = p1.float()
    p0, g, p1 = p0.double(), g.double(), p1.double()
    expected = p0 * (1 - lr * wd) - lr * g / (g.abs() + eps)  # exact replay in float64
    exp32 = expected.float()
    ulp = (torch.nextafter(exp32, torch.full_like(exp32, math.inf)) - exp32).double()
    err_ulps = (p1 - exp32.double()).abs() / ulp
    # tolerance per entry: 2 ULP of the stored value plus 1e-4 of the update (the FP32 intermediates of AdamW round
    # the update itself; near-zero weights have ULPs far below the update, so ULPs alone are the wrong yardstick)
    tol = 2 * ulp + 1e-4 * (expected - p0).abs()
    within = bool(((p1 - exp32.double()).abs() <= tol).all())
    stored = p1 - p0
    want = expected - p0
    b0 = p0.to(torch.bfloat16)
    b1 = (p0 + want).to(torch.bfloat16)
    moved = float((p32 != p0.float()).double().mean())
    return {
        "numel": p0.numel(),
        "fraction_moved_fp32_storage": moved,
        "fraction_would_move_bf16_storage": float((b1 != b0).double().mean()),
        "max_err_ulps_vs_replay_rounded_to_fp32": float(err_ulps.max()),
        "max_abs_update": float(stored.abs().max()),
        "mean_abs_update": float(stored.abs().mean()),
        "relative_err_of_stored_update": float((stored - want).norm() / max(float(want.norm()), 1e-30)),
        "tolerance": "2 ulp(stored) + 1e-4 |update| per entry",
        "all_entries_within_tolerance": within,
        "pass": bool(within and moved > 0.5),
    }


def state_sha256(model: nn.Module) -> str:
    h = hashlib.sha256()
    for k, v in sorted(model.state_dict().items()):
        h.update(k.encode())
        h.update(v.detach().to("cpu").contiguous().numpy().tobytes())
    return h.hexdigest()


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024


def hardware_label(device: str) -> str:
    if platform.system() == "Darwin":
        try:
            chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
            mem = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) // 2**30
            return f"{chip}, {mem} GB unified memory, device={device}"
        except (OSError, ValueError):
            pass
    if device.startswith("cuda") and torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return f"{platform.machine()} device={device}"


def sync(device: str) -> None:
    if device == "mps":
        torch.mps.synchronize()
    elif device.startswith("cuda"):
        torch.cuda.synchronize()


# ---------------------------------------------------------------- main loop


def lr_at(step: int, args) -> float:
    """Linear warmup then cosine to min_lr_ratio * lr (step counts from 0)."""
    if step < args.warmup:
        return args.lr * (step + 1) / args.warmup
    t = (step - args.warmup) / max(1, args.steps - args.warmup)
    return args.lr * (args.min_lr_ratio + (1 - args.min_lr_ratio) * 0.5 * (1 + math.cos(math.pi * t)))


def load_model(name: str, revision: str | None, device: str):
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(name, revision=revision, dtype=torch.float32, attn_implementation="sdpa")
    return model.to(device)


def train(args) -> dict:
    if args.revision in ("", "none", "None"):
        args.revision = None  # a local folder
    if args.train_marker_rows and args.method == "full":
        raise SystemExit("--train-marker-rows is a hybrid control for frozen-embedding methods; full FT trains every row")
    if args.method == "markers" and not args.train_marker_rows:
        raise SystemExit("--method markers trains only the marker rows: pass --train-marker-rows")
    if args.train_marker_rows and args.wd != 0:
        raise SystemExit("--train-marker-rows needs --wd 0: decoupled weight decay would move the unselected embedding rows")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = args.device
    if args.autocast == "bf16":
        if not device.startswith("cuda"):
            raise SystemExit("--autocast bf16 is for CUDA only (MPS/CPU train in FP32)")
        AUTOCAST["dtype"] = torch.bfloat16
    if device.startswith("cuda"):
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    model = load_model(args.model, args.revision, device)
    vocab = model.config.vocab_size
    rows, rejected = load_train_rows(args.train, args.max_tokens, vocab)
    method_info = apply_method(model, args.method, args)
    if args.untie_head:
        untie_head(model, trainable=args.method == "full")  # frozen like every other weight unless full FT
        method_info["untied_head"] = True
    marker_ids = sorted(sid for _, sid in retok_markers()) if args.train_marker_rows else None
    marker_params = enable_marker_rows(model, marker_ids, args.marker_scope) if marker_ids else []
    if marker_ids:
        method_info["hybrid"] = {"label": f"{args.method}+markers", "marker_row_ids": marker_ids, "marker_lr": args.marker_lr,
                                 "scope": args.marker_scope,
                                 "note": "HYBRID control: embedding/LM-head rows of the mapped chat markers are trained; "
                                         "not the pure method"}
    if args.method == "dt":
        calib_rng = random.Random(10_000 + args.seed)
        calib = [rows[i] for i in calib_rng.sample(range(len(rows)), min(args.dt_calib_rows, len(rows)))]
        cbatches = [collate(g, 0) for g in plan_microbatches(calib, args.micro_tokens)]
        t_cal = time.perf_counter()
        scores = dtmask.wanda_scores(model, ({"input_ids": b.input_ids, "attention_mask": b.attention_mask} for b in cbatches), device)
        method_info["wanda_prior"] = dtmask.apply_wanda_prior(model, scores, args.dt_eta, args.dt_prior_strength)
        method_info["wanda_prior"]["calibration_seconds"] = round(time.perf_counter() - t_cal, 2)
        method_info["wanda_prior"]["calibration_tokens"] = int(sum(int(b.attention_mask.sum()) for b in cbatches))
        method_info["deletion_at_init"] = dtmask.deletion_stats(model)
        method_info["band_at_init"] = dtmask.band_stats(model)
        del scores
    frozen_before = frozen_sha256(model, marker_ids) if args.method != "full" else None
    if args.grad_checkpointing:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    mids = {id(p) for p in marker_params}
    groups = [{"params": [p for p in params if id(p) not in mids], "base_lr": args.lr}]
    if not groups[0]["params"]:
        groups = []
    if marker_params:
        groups.append({"params": marker_params, "base_lr": args.marker_lr})
    opt = torch.optim.AdamW(groups, lr=args.lr, betas=(0.9, 0.95), eps=1e-8, weight_decay=args.wd)
    # the tensor watched by the step-1 writeback check
    if args.method == "full":
        watch_name, watch = "model.layers.0.self_attn.q_proj.weight", model.model.layers[0].self_attn.q_proj.weight
    elif args.method == "dt":
        watch_name, layer0 = dtmask.masked_layers(model)[0]
        watch_name, watch = watch_name + ".gate", layer0.gate
    elif args.method == "markers":  # watch a tensor that trains: with --marker-scope output only the head rows move
        watch = marker_params[0]
        watch_name = ("input embedding (marker rows)" if watch is model.get_input_embeddings().weight
                      else "lm_head (marker rows)")
    else:
        watch_name, watch = "model.layers.0.self_attn.q_proj.lora_B", model.model.layers[0].self_attn.q_proj.lora_B
    rng = random.Random(args.seed)
    order: list[int] = []
    log, checks = [], {}
    t_start = time.perf_counter()
    t_mark = t_start
    per100 = []
    pad_id = 0
    seen_rows = 0
    for step in range(args.steps):
        if len(order) < args.batch:
            perm = list(range(len(rows)))
            rng.shuffle(perm)
            order += perm
        take, order = order[: args.batch], order[args.batch :]
        groups = plan_microbatches([rows[i] for i in take], args.micro_tokens)
        mbs = [collate(g, pad_id) for g in groups]
        lr = lr_at(step, args)
        for g in opt.param_groups:
            g["lr"] = g["base_lr"] * lr / args.lr
        opt.zero_grad(set_to_none=True)
        loss, count = accumulate(model, mbs, device)
        reg_val = None
        if args.method == "dt" and args.dt_lambda > 0:
            lam = dtmask.lambda_at(step, args.steps, args.dt_lambda)
            reg = dtmask.regulariser(model)
            (-lam * reg).backward()  # once per optimizer step: the official per-microbatch term averaged over accumulation
            reg_val = float(reg.detach())
        gn = torch.nn.utils.clip_grad_norm_(params, args.clip)
        if step == 0:
            sel = (lambda t: t[marker_ids]) if args.method == "markers" else (lambda t: t)  # only these rows train
            p0, g0 = sel(watch.detach()).clone(), sel(watch.grad.detach()).clone()
        opt.step()
        if args.method == "dt":
            dtmask.step_all(model)
        if step == 0:
            wlr = lr * args.marker_lr / args.lr if args.method == "markers" else lr  # the watched tensor's group LR
            checks["writeback_step1"] = {"tensor": watch_name, "lr": wlr, "storage_dtype": str(watch.dtype),
                                         **writeback_check(p0.cpu(), g0.cpu(), sel(watch.detach()).cpu(), wlr, args.wd, 1e-8)}
            del p0, g0
        seen_rows += len(take)
        rec = {"step": step + 1, "loss": loss, "targets": count, "lr": lr, "grad_norm": float(gn), **({"reg": reg_val} if reg_val is not None else {}),
               "tokens": sum(len(rows[i]["input_ids"]) for i in take), "microbatches": len(mbs)}
        if (step + 1) % 100 == 0 or step + 1 == args.steps:
            sync(device)
            now = time.perf_counter()
            per100.append({"steps": f"{step + 1 - ((step) % 100)}-{step + 1}", "seconds": round(now - t_mark, 2)})
            t_mark = now
        if (step + 1) % args.log_every == 0 or step == 0 or step + 1 == args.steps:
            rec["elapsed_s"] = round(time.perf_counter() - t_start, 2)
            if device == "mps":
                rec["mps_driver_mb"] = round(torch.mps.driver_allocated_memory() / 2**20, 1)
            print(json.dumps(rec), flush=True)
        log.append(rec)
        if not math.isfinite(loss):
            raise SystemExit(f"non-finite loss at step {step + 1}")
    sync(device)
    train_seconds = time.perf_counter() - t_start
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model.eval()
    # fixed parity batch: the two shortest training rows
    parity_rows = sorted(rows, key=lambda r: len(r["input_ids"]))[:2]
    pb = collate(parity_rows, pad_id)
    with torch.no_grad():
        ref_logits = model(input_ids=pb.input_ids.to(device), attention_mask=pb.attention_mask.to(device)).logits.float().cpu()
    lora_state = None
    if frozen_before is not None:
        frozen_after = frozen_sha256(model, marker_ids)
        checks["frozen_weights_unchanged"] = {"sha256_before": frozen_before, "sha256_after": frozen_after,
                                              "scope": "every frozen tensor" + (" + non-marker embedding rows" if marker_ids else ""),
                                              "pass": frozen_before == frozen_after}
    if args.method == "dt":
        method_info["deletion_final"] = dtmask.deletion_stats(model)
        method_info["alpha_final"] = dtmask.masked_layers(model)[0][1].alpha
        masks = dtmask.bake(model)  # hard mask written into plain Linear layers: every evaluation sees W * 1[G > 0]
        blob, meta = dtmask.pack_masks(masks)
        (out / "dt_mask.bin").write_bytes(blob)
        (out / "dt_mask.json").write_text(json.dumps(meta), encoding="utf-8")
        method_info["mask_artifact"] = {k: v for k, v in meta.items() if k != "shapes"}
        with torch.no_grad():
            baked_logits = model(input_ids=pb.input_ids.to(device), attention_mask=pb.attention_mask.to(device)).logits.float().cpu()
        checks["bake_parity"] = {"logits_max_abs_diff": float((baked_logits - ref_logits)[pb.attention_mask.bool()].abs().max()),
                                 "compared": "eval-mode MaskedLinear (hard mask) vs baked nn.Linear", "tolerance": 0.0}
        checks["bake_parity"]["pass"] = checks["bake_parity"]["logits_max_abs_diff"] == 0.0
    if args.method == "lora":
        lora_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items() if "lora_" in k}
        torch.save(lora_state, out / "lora_adapter.pt")
        merge_lora(model)
    model.save_pretrained(out / "model", safe_serialization=True)
    tok_src = Path(args.tokenizer_dir) if args.tokenizer_dir else None
    if tok_src is None:
        from huggingface_hub import snapshot_download

        tok_src = Path(snapshot_download(args.model, revision=args.revision, allow_patterns=["tokenizer*", "special_tokens_map.json"]))
    for f in ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"):
        if (tok_src / f).is_file():
            shutil.copy(tok_src / f, out / "model" / f)
    mem_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    del model, opt
    if device == "mps":
        torch.mps.empty_cache()
    reloaded = load_model(str(out / "model"), None, device)
    reloaded.eval()
    re_state = reloaded.state_dict()
    tensors_equal = all(torch.equal(mem_state[k], re_state[k].cpu()) for k in mem_state) and set(mem_state) == set(re_state)
    with torch.no_grad():
        re_logits = reloaded(input_ids=pb.input_ids.to(device), attention_mask=pb.attention_mask.to(device)).logits.float().cpu()
    valid = pb.attention_mask.bool()
    max_diff = float((re_logits - ref_logits)[valid].abs().max())
    tol = 1e-3 if args.method == "lora" else 0.0
    checks["reload_parity"] = {"tensors_bit_identical": bool(tensors_equal), "logits_max_abs_diff": max_diff,
                               "tolerance": tol, "compared": "in-memory model (LoRA unmerged) vs reloaded saved folder",
                               "pass": bool(tensors_equal and max_diff <= tol),
                               "saved_dtype": str(next(reloaded.parameters()).dtype)}
    report = {
        "schema": "g10-bench-train/1", "args": vars(args), "method": method_info, "rows": len(rows),
        "rejected": rejected, "rows_seen": seen_rows, "epochs": round(seen_rows / len(rows), 3),
        "train_sha256": hashlib.sha256(Path(args.train).read_bytes()).hexdigest(),
        "device": device, "hardware": hardware_label(device), "dtype": "float32 weights/grads/AdamW state; compute " + ("bf16 autocast (CUDA)" if AUTOCAST["dtype"] else "float32 (TF32 off)"),
        "torch": torch.__version__, "train_seconds": round(train_seconds, 1), "seconds_per_100_steps": per100,
        "peak_rss_mb": round(peak_rss_mb(), 1), "checks": checks,
        "first_loss": log[0]["loss"], "last_loss": log[-1]["loss"],
        "mean_loss_first_20": sum(r["loss"] for r in log[:20]) / min(20, len(log)),
        "mean_loss_last_20": sum(r["loss"] for r in log[-20:]) / min(20, len(log)),
        "saved_state_sha256": state_sha256(reloaded), "log": log,
    }
    if device.startswith("cuda"):
        report["cuda_peak_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
        report["cuda_peak_reserved_mb"] = round(torch.cuda.max_memory_reserved() / 2**20, 1)
    if device == "mps":
        report["mps_driver_mb_end"] = round(torch.mps.driver_allocated_memory() / 2**20, 1)
    (out / "train_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--train", required=True)
    ap.add_argument("--model", default="HuggingFaceTB/SmolLM2-135M")
    ap.add_argument("--revision", default="93efa2f097d58c2a74874c7e644dbc9b0cee75a2")
    ap.add_argument("--tokenizer-dir", help="folder with tokenizer.json etc. to copy into the saved model")
    ap.add_argument("--method", choices=METHODS, default="full")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--batch", type=int, default=8, help="rows per optimizer update")
    ap.add_argument("--micro-tokens", type=int, default=4096, help="rows x longest row per microbatch")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--grad-checkpointing", action="store_true")
    ap.add_argument("--autocast", choices=("none", "bf16"), default="none")
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--min-lr-ratio", type=float, default=0.1)
    ap.add_argument("--wd", type=float, default=0.0)
    ap.add_argument("--clip", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--lora-r", type=int, default=4)
    ap.add_argument("--lora-alpha", type=float, default=8.0)
    ap.add_argument("--dt-targets", choices=sorted(dtmask.TARGET_SETS), default="gate")
    ap.add_argument("--dt-eta", type=float, default=1 / 2048, help="Wanda prior quantile (the knob; deletion is an outcome)")
    ap.add_argument("--dt-alpha-start", type=float, default=100.0)
    ap.add_argument("--dt-alpha-end", type=float, default=1000.0)
    ap.add_argument("--dt-lambda", type=float, default=1e-5)
    ap.add_argument("--dt-prior-strength", type=float, default=3.0)
    ap.add_argument("--dt-calib-rows", type=int, default=64)
    ap.add_argument("--train-marker-rows", action="store_true",
                    help="HYBRID control for lora/dt: also train the embedding rows of the mapped chat markers")
    ap.add_argument("--marker-lr", type=float, default=1e-4, help="peak LR of the marker rows (same schedule shape)")
    ap.add_argument("--untie-head", action="store_true",
                    help="copy the tied embedding matrix into a separate LM head before training (capstone-like head)")
    ap.add_argument("--marker-scope", choices=("both", "input", "output"), default="both",
                    help="with --untie-head: train the marker rows of the embedding, of the LM head, or of both")
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--log-every", type=int, default=10)
    ap.add_argument("--out", required=True)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    rep = train(args)
    summary = {k: rep[k] for k in ("rows", "epochs", "train_seconds", "seconds_per_100_steps", "peak_rss_mb",
                                    "first_loss", "last_loss", "mean_loss_first_20", "mean_loss_last_20", "checks")}
    print(json.dumps(summary, indent=1))
    ok = all(c.get("pass", True) for c in rep["checks"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
