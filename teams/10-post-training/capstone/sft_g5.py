"""SFT on Team 5's LanguageModel through the G10 adapter: full | lora | dt | markers, with the bench's loss contract.

    python capstone/sft_g5.py --adapter-config <run_folder adapter yaml> --train rows.jsonl --eval rows.jsonl \
        --method full --steps 200 --lr 3e-4 --device mps --heldout heldout.jsonl --heldout-sources src.jsonl --out DIR

What is reused unchanged
- loss: `sft/bench/train.py` (`collate`, `plan_microbatches`, `accumulate` -> `sft/train_probe.py` contract: logit t
  predicts token t+1, supervised only where loss_mask[t+1] == 1, sum NLL / global target count, FP32 CE);
- LoRA: the bench's `LoRALinear` / `merge_lora`; DT: `dt/mask.py` (`convert`, Wanda prior, regulariser, schedule, bake);
- the step-1 stored-weight writeback check (`writeback_check`), `lr_at` (warmup + cosine);
- forgetting: Team 5's own `week2.evaluation.evaluate` on Team 5's `DocumentWindows` (same bpb as the pre-training run);
- chat format: `chat-format/render.py` parses every generation (the bench's `judge` taxonomy, on native ids).

What differs from the Hugging Face bench, because the model differs
- The model is G5's `LanguageModel` (KE2 byte-code input projection, dense untied head). `G5ForBench` gives it the two
  calls the bench loss needs (`.model(...).last_hidden_state`, `.lm_head`). G5 attention has no padding mask, so batches
  are right-padded only (causal attention never reads the padding of a real position).
- There are no per-token input embedding rows (KE2 projects each token's byte code through one shared matrix), so the
  marker-row control can only train output-head rows: `--marker-rows` trains `head.weight` rows of the nine G10 markers.
- LoRA targets are G5's child names (q, k, v, o, gate, up, down: attention and every routed and shared expert).
- DT targets are `dt/mask.py` `g5_*` sets (anchored names; the Hugging Face `gate_proj` substring finds nothing here).
- The saved model is a G5 state dict (safetensors), reloaded into a fresh LanguageModel for the parity check.

Every result from a G10 rehearsal checkpoint is mechanics and relative comparison at small width, never a quality claim.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch import no_grad

HERE = Path(__file__).resolve().parent
TEAM10 = HERE.parent
sys.path.insert(0, str(TEAM10 / "rl-loop"))
sys.path.insert(0, str(HERE))


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bench = _load("g10_bench_train_for_g5", TEAM10 / "sft" / "bench" / "train.py")
dtmask = bench.dtmask
probe = bench.probe
render = _load("g10_render_for_g5_sft", TEAM10 / "chat-format" / "render.py")
launch = _load("g10_capstone_launch", HERE / "g5_launch.py")
MARKER_NAMES = ("im_start", "tool_call", "tool_result", "im_end", "endoftext", "think", "think_end",
                "tool_call_end", "tool_result_end")
G5_LORA_TARGETS = ("q", "k", "v", "o", "gate", "up", "down")


class _Hidden:
    def __init__(self, h):
        self.last_hidden_state = h


class _Out:
    def __init__(self, logits):
        self.logits = logits


class _Body(nn.Module):
    """`.model(input_ids, attention_mask)` for the bench loss. Holds no parameters of its own."""

    def __init__(self, owner):
        super().__init__()
        object.__setattr__(self, "_owner", owner)  # not a registered submodule: parameters are counted once

    def forward(self, input_ids, attention_mask=None):
        valid = torch.ones_like(input_ids, dtype=torch.bool) if attention_mask is None else attention_mask.bool()
        return _Hidden(self._owner.lm.hidden(input_ids, valid))


class G5ForBench(nn.Module):
    """G5 LanguageModel with the Hugging Face-like calls the bench loss and DT calibration use. Right padding only."""

    def __init__(self, lm: nn.Module):
        super().__init__()
        self.lm = lm
        object.__setattr__(self, "model", _Body(self))

    @property
    def lm_head(self):
        return self.lm.head

    def forward(self, input_ids, attention_mask=None):
        valid = torch.ones_like(input_ids, dtype=torch.bool) if attention_mask is None else attention_mask.bool()
        if bool((valid[:, 1:] & ~valid[:, :-1]).any()):
            raise ValueError("G5 attention has no padding mask: right padding only")
        return _Out(self.lm(input_ids, valid))


# ---------------------------------------------------------------- methods


def apply_method(lm: nn.Module, method: str, args) -> dict:
    if method == "full":
        for p in lm.parameters():
            p.requires_grad_(True)
        return {"method": "full", "trainable": sum(p.numel() for p in lm.parameters())}
    if method == "markers":
        for p in lm.parameters():
            p.requires_grad_(False)
        return {"method": "markers", "trainable": 0, "note": "CONTROL: only the nine marker rows of the output head train"}
    if method == "lora":
        for p in lm.parameters():
            p.requires_grad_(False)
        gen = torch.Generator().manual_seed(args.seed)
        wrapped = []
        for name, module in list(lm.named_modules()):
            if name.endswith(".router") or name == "head" or name.startswith("head."):
                continue  # the output head (dense or KE2/KAS, with any inner Linears) is never LoRA-wrapped
            for child_name, child in list(module.named_children()):
                if child_name in G5_LORA_TARGETS and isinstance(child, nn.Linear):
                    setattr(module, child_name, bench.LoRALinear(child, args.lora_r, args.lora_alpha, gen))
                    wrapped.append(f"{name}.{child_name}")
        return {"method": "lora", "r": args.lora_r, "alpha": args.lora_alpha, "targets": list(G5_LORA_TARGETS),
                "wrapped_modules": len(wrapped), "trainable": sum(p.numel() for p in lm.parameters() if p.requires_grad)}
    if method == "dt":
        names = dtmask.convert(lm, dtmask.TARGET_SETS[args.dt_targets], args.dt_alpha_start, args.dt_alpha_end,
                               args.steps, seed=args.seed)
        return {"method": "dt", "targets": args.dt_targets, "target_patterns": list(dtmask.TARGET_SETS[args.dt_targets]),
                "masked_layers": len(names), "trainable": sum(p.numel() for p in lm.parameters() if p.requires_grad),
                "alpha": [args.dt_alpha_start, args.dt_alpha_end], "lambda": args.dt_lambda, "eta": args.dt_eta}
    raise ValueError(method)


def enable_head_rows(lm: nn.Module, ids: list[int]) -> nn.Parameter:
    """Train only rows `ids` of the output head's per-token matrix (dense `head.weight` or KE2/KAS `head.tok_u`,
    resolved by team5_adapter.head_access, which raises on a head of unknown kind)."""
    import team5_adapter as ta  # noqa: PLC0415  rl-loop/team5_adapter.py

    try:
        info = ta.head_access(lm)
    except ta.ArtifactError as e:
        raise ValueError(f"--marker-rows: {e}") from None
    w = info["per_token"]
    if max(ids) >= w.shape[0]:
        raise ValueError(f"--marker-rows: marker id {max(ids)} outside {info['per_token_name']} rows {w.shape[0]}")
    rowmask = torch.zeros(w.shape[0], 1, dtype=w.dtype, device=w.device)
    rowmask[ids] = 1
    w.requires_grad_(True)
    w.register_hook(lambda g, m=rowmask: g * m)
    return w


# ---------------------------------------------------------------- evaluation


def judge(bundle, prompt_ids: list[int], gen_ids: list[int]) -> dict:
    """The bench's format judge on native ids: decode through the KE2 raw table, parse with render.py."""
    im_end = bundle.special["tokens"]["end_of_turn"]["id"]
    eos = bundle.special["tokens"]["end_of_sequence"]["id"]
    head = f"{render.T['im_start']}assistant\n"
    prompt_text = bundle.completion_bytes(prompt_ids).decode("utf-8", errors="replace")
    if not prompt_text.endswith(head):
        raise RuntimeError("prompt does not end with the assistant header")
    n_prompt = len(render.parse(prompt_text[: -len(head)] + render.T["endoftext"])["messages"])
    stop = next((i for i, t in enumerate(gen_ids) if t in (im_end, eos)), None)
    closed = stop is not None and gen_ids[stop] == im_end
    body = gen_ids[: stop + 1] if stop is not None else gen_ids
    marker_ids = {bundle.artifacts.tokenizer.token_to_id(render.T[n]): n for n in MARKER_NAMES}
    rec = {"gen_tokens": len(body), "closed_im_end": closed, "stopped_eos_first": stop is not None and gen_ids[stop] == eos,
           "hit_budget": stop is None, "markers_emitted": sorted({marker_ids[t] for t in body if t in marker_ids}),
           "valid": False, "has_think": False, "content": None}
    gen_text = bundle.completion_bytes(body).decode("utf-8", errors="replace")
    if not closed:
        rec["reason"] = "no_im_end" if stop is None else "eos_before_im_end"
    else:
        try:
            msgs = render.parse(prompt_text + gen_text + "\n" + render.T["endoftext"])["messages"]
        except render.RenderError as exc:
            rec["reason"] = "parse_error: " + str(exc).split(" at offset")[0][:60]
        else:
            last = msgs[-1]
            if len(msgs) != n_prompt + 1 or last.get("role") != "assistant":
                rec["reason"] = "wrong_turn_structure"
            elif not last.get("content"):
                rec["reason"] = "empty_visible_reply"
                rec["has_think"] = "think" in last
            else:
                rec.update(valid=True, reason="ok", has_think="think" in last)
            rec["content"] = last.get("content")
    rec["text"] = gen_text
    return rec


def generate_and_judge(bundle, rows: list[dict], max_new: int, limit: int,
                       seconds: float = 0.0) -> tuple[dict, list[dict]]:
    """Greedy, one prompt at a time, through the G10 KV-cached decoder (Team 5's model itself has no cache).
    `seconds` > 0: no new prompt is started after that long; `per_row` keeps flags only (no text), in row-id order."""
    prompts = sorted(rows, key=lambda r: r["id"])[:limit]
    recs, t0, gen_tokens, stopped = [], time.perf_counter(), 0, False
    kv = bundle.kv_cache
    bundle.kv_cache = True  # rl-loop/g5_decode.py: same tokens as the re-forward path (test_team5_adapter parity test)
    for r in prompts:
        if seconds and time.perf_counter() - t0 > seconds:
            stopped = True
            break
        prompt = r["input_ids"][: r["prompt_len"]]
        mn = min(max_new, bundle.spec["block_size"] - len(prompt))
        if mn <= 0:
            continue
        seq, cmask, _ = bundle.sample(prompt, 1, mn, 0.0, None)
        gen = seq[0, len(prompt):][cmask[0]].tolist()
        rec = judge(bundle, prompt, gen)
        rec["row_id"] = r["id"]
        gen_tokens += rec["gen_tokens"]
        recs.append(rec)
    bundle.kv_cache = kv
    secs = time.perf_counter() - t0
    n = max(len(recs), 1)
    reasons: dict[str, int] = {}
    markers: dict[str, int] = {}
    for x in recs:
        reasons[x["reason"]] = reasons.get(x["reason"], 0) + 1
        for m in x["markers_emitted"]:
            markers[m] = markers.get(m, 0) + 1
    return {"prompts": len(recs), "format_validity": sum(x["valid"] for x in recs) / n,
            "closed_im_end": sum(x["closed_im_end"] for x in recs) / n, "hit_budget": sum(x["hit_budget"] for x in recs) / n,
            "rows_emitting_marker": markers, "mean_gen_tokens": gen_tokens / n, "reasons": dict(sorted(reasons.items())),
            "decoding": "greedy, KV cache (g5_decode)", "max_new": max_new, "seconds": round(secs, 1),
            "gen_tokens_per_s": round(gen_tokens / max(secs, 1e-9), 1), "budget_seconds": seconds,
            "stopped_at_budget": stopped, "per_row": [[x["row_id"], int(bool(x["valid"])), int(bool(x["closed_im_end"])),
                                                   int(bool(x["hit_budget"])), int(x["gen_tokens"])] for x in recs]}, recs


def eval_loss(wrapper: G5ForBench, rows: list[dict], device: str, micro_tokens: int) -> dict:
    """Teacher-forced masked NLL per supervised token on rows (the training loss, no gradient)."""
    total, count = 0.0, 0
    with torch.no_grad():
        for g in bench.plan_microbatches(rows, micro_tokens):
            b = bench.collate(g, 0)
            b = probe.Batch(*(t.to(device) for t in (b.input_ids, b.attention_mask, b.labels, b.kinds)))
            s, n = bench.target_nll_sum(wrapper, b)
            total += float(s)
            count += n
    return {"nll_per_target": total / max(count, 1), "targets": count, "rows": len(rows)}


def forgetting_bpb(bundle, heldout: Path, sources: Path | None, device: str) -> dict:
    """Team 5's own evaluate() on Team 5's DocumentWindows: the pre-training held-out bpb, same code as train_week2."""
    g5 = sys.modules["week2.evaluation"] if "week2.evaluation" in sys.modules else __import__("week2.evaluation").evaluation
    data = sys.modules["week2.data"] if "week2.data" in sys.modules else __import__("week2.data").data
    if device == "mps":
        launch.install_mps_double_patch()
    val = data.DocumentWindows(heldout, bundle.artifacts, bundle.spec["block_size"], require_ids=False,
                               sources_path=sources)
    t0 = time.perf_counter()
    res = g5.evaluate(bundle.model, val, 1, torch.device(device), contextlib.nullcontext, max_batch_tokens=g5.EVAL_BATCH_TOKENS)
    keep = {k: v for k, v in res.items() if k in ("val/bpb", "val/three_group_bpb") or k.startswith("val/groups/")
            or (k.startswith("val/slices/") and k.endswith("/bpb"))}
    keep["seconds"] = round(time.perf_counter() - t0, 1)
    return keep


def mask_checks(wrapper: G5ForBench, rows: list[dict], device: str, bundle) -> dict:
    """On real rows: (1) every unsupervised shifted position has label IGNORE and every supervised one the next id;
    (2) the training loss equals the sum of per-position NLL over loss_mask==1 targets computed from full logits;
    (3) moving a context token's target into or out of supervision is the only thing that changes the loss: the
    loss is invariant to the logits at masked positions (adding noise there leaves it bit-identical)."""
    out = {"rows": len(rows)}
    b = bench.collate(rows, 0)
    lab, ids, m = b.labels, b.input_ids, b.attention_mask
    want = torch.full_like(lab, probe.IGNORE)
    for i, r in enumerate(rows):
        n = len(r["input_ids"])
        for t in range(n - 1):
            if r["loss_mask"][t + 1] == 1:
                want[i, t] = r["input_ids"][t + 1]
    out["labels_match_mask"] = bool(torch.equal(lab, want))
    db = probe.Batch(*(t.to(device) for t in (b.input_ids, b.attention_mask, b.labels, b.kinds)))
    with torch.no_grad():
        s, n = bench.target_nll_sum(wrapper, db)
        logits = wrapper(db.input_ids, db.attention_mask).logits[:, :-1].float()
        per = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]), db.input_ids[:, 1:].reshape(-1),
                                                reduction="none").reshape(lab.shape)
        sup = (db.labels != probe.IGNORE)
        manual = float(per[sup].sum())
        noisy = logits.clone()
        noisy[~sup] += torch.randn_like(noisy[~sup]) * 10
        s_noisy, _ = probe.masked_nll_sum(noisy, db.labels)
        s_clean, _ = probe.masked_nll_sum(logits, db.labels)
    out["loss_equals_manual_masked_sum"] = abs(float(s) - manual) <= 1e-3 * max(1.0, abs(manual))
    out["loss_invariant_to_masked_logits"] = float(s_noisy) == float(s_clean)
    out["supervised_targets"], out["context_positions"] = int(n), int(((m[:, 1:] == 1) & (lab == probe.IGNORE)).sum())
    im_end = bundle.special["tokens"]["end_of_turn"]["id"]
    out["im_end_targets_supervised"] = int(((lab == im_end)).sum())
    out["assistant_header_supervised"] = any(r["loss_mask"][r["prompt_len"] - 1] == 1 for r in rows)
    return out


# ---------------------------------------------------------------- main


@no_grad()  # undotted: pr-guard reads '+@a.b' as an email
def marker_lift_stats(lm: nn.Module, rows: list[dict], marker_id: int, device: str, max_rows: int = 32,
                      mid_per_row: int = 32) -> dict:
    """log p(marker) at its supervised target positions (loss_mask 1; scored from the final hidden state one position
    earlier), eval mode, the first `max_rows` rows that have such a target. Also RMS(h) there and, on a KAS V2 head
    (`head.tok_c`), the marker rows' lift budget: z = h @ tok_c.T is what `head.tok_u[marker]` is multiplied by, so AdamW at
    lr moves that logit by at most lr * sum|z_i| per step (`sum_abs_z`, mean over positions), and by at most
    lr * sum_i |mean_p z_i| when one step must serve every position (`sum_abs_mean_z`). work/adp-2026-11-24/PREREG_marker_lr.md.
    `mid_logprob`: log p(marker) at MID-reply supervised positions of the same rows (loss_mask 1, token not the marker; up
    to `mid_per_row` evenly spaced per row), and `end_minus_mid`: the selectivity reached. The marker rows alone cannot
    tell a turn end from mid-reply (they see only z); the method has to supply that through h."""
    was = lm.training
    lm.eval()
    tok_c = getattr(getattr(lm, "head", None), "tok_c", None)
    lps, hs, mids, used = [], [], [], 0
    for r in rows:
        if used >= max_rows:
            break
        ids, mask = r["input_ids"], r["loss_mask"]
        pos = [t for t in range(1, len(ids)) if ids[t] == marker_id and mask[t]]
        if not pos:
            continue
        x = torch.tensor([ids], device=device)
        h = lm.hidden(x, torch.ones_like(x, dtype=torch.bool))[0]
        hp = h[torch.tensor([t - 1 for t in pos], device=device)]
        lps.append(torch.log_softmax(lm.head(hp).float(), -1)[:, marker_id].double().cpu())
        mid = [t for t in range(1, len(ids)) if mask[t] and ids[t] != marker_id]
        if mid:
            mid = [mid[int(j * len(mid) / min(mid_per_row, len(mid)))] for j in range(min(mid_per_row, len(mid)))]
            hm = h[torch.tensor([t - 1 for t in mid], device=device)]
            mids.append(torch.log_softmax(lm.head(hm).float(), -1)[:, marker_id].double().cpu())
        hs.append(hp.float().cpu())
        used += 1
    lm.train(was)
    if not hs:
        return {"marker_id": marker_id, "rows": 0, "positions": 0}
    lp, h = torch.cat(lps), torch.cat(hs)
    out = {"marker_id": marker_id, "rows": used, "positions": int(lp.numel()), "mean_logprob": float(lp.mean()),
           "rms_h": float(h.pow(2).mean().sqrt())}
    if mids:
        mlp = torch.cat(mids)
        out.update(mid_positions=int(mlp.numel()), mid_logprob=float(mlp.mean()),
                   end_minus_mid=float(lp.mean() - mlp.mean()))
    if isinstance(tok_c, torch.Tensor):
        z = h @ tok_c.detach().float().cpu().t()
        out.update(sum_abs_z=float(z.abs().sum(-1).mean()), sum_abs_mean_z=float(z.mean(0).abs().sum()), rank=int(z.shape[1]))
    return out


# work/adp-2026-11-24/PREREG_marker_lr.md, Amendment A1: the marker rows must cover 1.3 x (prior floor 18.79 + 3.0) nats.
MARKER_DEFICIT_NATS = 18.79 + 3.0
MARKER_MARGIN = 1.3


def marker_budget(marker_lr: float, multipliers: list[float], stats: dict) -> dict | None:
    """The lift the marker rows could reach on the logged run: marker_lr x S x sum|z| x c, with S the sum of the completed
    steps' schedule multipliers and c = sum|mean z| / sum|z| at im_end's targets (before training). `under_margin` says
    the frozen arms' chat column is budget-limited, not method-limited. None without a KAS head (no z)."""
    if not stats or not stats.get("sum_abs_z"):
        return None
    S = float(sum(multipliers))
    c = stats["sum_abs_mean_z"] / stats["sum_abs_z"]
    budget = marker_lr * S * stats["sum_abs_z"] * c
    need = MARKER_MARGIN * MARKER_DEFICIT_NATS
    return {"marker_lr": marker_lr, "steps": len(multipliers), "S": S, "sum_abs_z": stats["sum_abs_z"], "coherence": c,
            "budget_nats": budget, "required_nats": need, "under_margin": budget < need,
            "flag": "marker budget under the preregistered margin" if budget < need else None}


def read_rows(path: Path, split: str) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    bad = [r["id"] for r in rows if r.get("split") != split]
    if bad:
        raise SystemExit(f"{path}: {len(bad)} rows are not split={split!r}, e.g. {bad[:2]}")
    return rows


def save_state(lm: nn.Module, path: Path, meta: dict) -> str:
    from safetensors.torch import save_file

    sd = {k: v.detach().cpu().contiguous() for k, v in lm.state_dict().items()}
    save_file(sd, str(path), metadata={k: str(v) for k, v in meta.items()})
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args) -> dict:
    import team5_adapter as ta

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = args.device
    result = ta.build(args.adapter_config, device=device)
    bundle = result.require_bundle()
    lm = bundle.model
    wrapper = G5ForBench(lm)
    train_rows = read_rows(args.train, "train")
    eval_rows = read_rows(args.eval, "eval")
    over = [r["id"] for r in train_rows + eval_rows if len(r["input_ids"]) > bundle.spec["block_size"]]
    if over and not args.drop_over_block:
        raise SystemExit(f"{len(over)} rows exceed block_size {bundle.spec['block_size']}; re-render with --max-tokens")
    if over:  # counted, never truncated
        cap = bundle.spec["block_size"]
        train_rows = [r for r in train_rows if len(r["input_ids"]) <= cap]
        eval_rows = [r for r in eval_rows if len(r["input_ids"]) <= cap]
        if not train_rows or not eval_rows:
            raise SystemExit(f"no rows fit block_size {cap}")
    report = {"schema": "g10-capstone-sft/1", "args": {k: str(v) for k, v in vars(args).items()},
              "adapter_status": result.status, "model_spec": bundle.spec, "train_rows": len(train_rows),
              "rows_dropped_over_block": len(over),
              "eval_rows": len(eval_rows), "hardware": bench.hardware_label(device), "torch": torch.__version__}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lm.eval()
    report["mask_checks"] = mask_checks(wrapper, sorted(train_rows, key=lambda r: r["id"])[:4], device, bundle)
    pre, pre_recs = None, []
    if not args.no_before:  # --no-before: another arm of the same job already measured this base model
        pre = {"eval_loss": eval_loss(wrapper, eval_rows, device, args.micro_tokens)}
        if args.heldout:
            pre["forgetting"] = forgetting_bpb(bundle, args.heldout, args.heldout_sources, device)
        pre["generation"], pre_recs = generate_and_judge(bundle, eval_rows, args.gen_max_new, args.gen_limit,
                                                         args.gen_seconds)
        if args.rl_tasks and args.rl_ids:
            import day_one_probe  # noqa: PLC0415
            pre["rl_screen"] = day_one_probe.rl_screen_bundle(bundle, args.rl_tasks, args.rl_ids, args.rl_k,
                                                              args.rl_max_new, device, args.rl_limit,
                                                              args.rl_seconds)
    report["before"] = pre
    marker_ids = [bundle.artifacts.tokenizer.token_to_id(render.T[n]) for n in MARKER_NAMES]
    method_info = apply_method(lm, args.method, args)
    marker_param = enable_head_rows(lm, marker_ids) if args.marker_rows else None
    if args.method == "markers" and marker_param is None:
        raise SystemExit("--method markers needs --marker-rows")
    if marker_param is not None:
        if args.method == "full":
            raise SystemExit("--marker-rows is a control for frozen methods; full FT already trains the head")
        if args.wd != 0:
            raise SystemExit("--marker-rows needs --wd 0")
        method_info["hybrid"] = {"head_rows": marker_ids, "marker_lr": args.marker_lr}
    if args.method == "dt":
        rng = random.Random(10_000 + args.seed)
        calib = [train_rows[i] for i in rng.sample(range(len(train_rows)), min(args.dt_calib_rows, len(train_rows)))]
        cb = [bench.collate(g, 0) for g in bench.plan_microbatches(calib, args.micro_tokens)]
        scores = dtmask.wanda_scores(wrapper, ({"input_ids": b.input_ids, "attention_mask": b.attention_mask}
                                               for b in cb), device)
        # scores are keyed by the wrapper's module names ("lm.blocks..."), so the prior is applied through it too
        method_info["wanda_prior"] = dtmask.apply_wanda_prior(wrapper, scores, args.dt_eta, args.dt_prior_strength,
                                                              unseen=args.dt_unseen)
        method_info["wanda_layers_without_tokens"] = len(dtmask.masked_layers(wrapper)) - len(scores)
        method_info["deletion_at_init"] = dtmask.deletion_stats(lm)
        method_info["band_at_init"] = dtmask.band_stats(lm)
    report["method"] = method_info
    im_end_id = bundle.special["tokens"]["end_of_turn"]["id"]
    report["im_end_at_targets"] = {"before": marker_lift_stats(lm, eval_rows, im_end_id, device)}
    frozen_before = bench.frozen_sha256(lm, marker_ids if marker_param is not None else None) \
        if args.method != "full" else None
    import router as g10_router  # noqa: PLC0415  rl-loop/router.py
    bias_before = g10_router.router_bias_checksum(lm)  # every method, full FT included: the bias is a buffer
    params = [p for p in lm.parameters() if p.requires_grad]
    groups = [{"params": [p for p in params if p is not marker_param], "base_lr": args.lr}]
    groups = [g for g in groups if g["params"]]
    if marker_param is not None:
        groups.append({"params": [marker_param], "base_lr": args.marker_lr})
    opt = torch.optim.AdamW(groups, lr=args.lr, betas=(0.9, 0.95), eps=1e-8, weight_decay=args.wd)
    if args.method == "dt":
        watch_name, layer0 = dtmask.masked_layers(lm)[0]
        watch_name, watch = watch_name + ".gate", layer0.gate
    elif args.method == "lora":
        watch_name, watch = "blocks.0.attn.q.lora_B", lm.blocks[0].attn.q.lora_B
    elif args.method == "markers":
        watch_name, watch = f"{ta.head_access(lm)['per_token_name']} (marker rows)", marker_param
    else:
        watch_name, watch = "blocks.0.attn.q.weight", lm.blocks[0].attn.q.weight
    lm.train()
    rng = random.Random(args.seed)
    order: list[int] = []
    log = []
    t0 = time.perf_counter()
    for step in range(args.steps):
        if len(order) < args.batch:
            perm = list(range(len(train_rows)))
            rng.shuffle(perm)
            order += perm
        take, order = order[: args.batch], order[args.batch:]
        mbs = [bench.collate(g, 0) for g in bench.plan_microbatches([train_rows[i] for i in take], args.micro_tokens)]
        lr = bench.lr_at(step, args)
        for g in opt.param_groups:
            g["lr"] = g["base_lr"] * lr / args.lr
        opt.zero_grad(set_to_none=True)
        loss, count = bench.accumulate(wrapper, mbs, device)
        reg_val = None
        if args.method == "dt" and args.dt_lambda > 0:
            reg = dtmask.regulariser(lm)
            (-dtmask.lambda_at(step, args.steps, args.dt_lambda) * reg).backward()
            reg_val = float(reg.detach())
        gn = torch.nn.utils.clip_grad_norm_(params, args.clip)
        sel = (lambda t: t[marker_ids]) if args.method == "markers" else (lambda t: t)
        if step == 0:
            p0, g0 = sel(watch.detach()).clone(), sel(watch.grad.detach()).clone()
        opt.step()
        if args.method == "dt":
            dtmask.step_all(lm)
        if step == 0:
            wlr = lr * args.marker_lr / args.lr if args.method == "markers" else lr
            report["writeback_step1"] = {"tensor": watch_name, "storage_dtype": str(watch.dtype), "lr": wlr,
                                         **bench.writeback_check(p0.cpu(), g0.cpu(), sel(watch.detach()).cpu(), wlr,
                                                                 args.wd, 1e-8)}
        rec = {"step": step + 1, "loss": loss, "targets": count, "lr": lr, "grad_norm": float(gn)}
        if reg_val is not None:
            rec["reg"] = reg_val
        if (step + 1) % args.log_every == 0 or step == 0 or step + 1 == args.steps:
            bench.sync(device)
            rec["elapsed_s"] = round(time.perf_counter() - t0, 1)
            print(json.dumps(rec), flush=True)
        log.append(rec)
        if not math.isfinite(loss):
            raise SystemExit(f"non-finite loss at step {step + 1}")
        if args.max_train_seconds and time.perf_counter() - t0 > args.max_train_seconds and step + 1 < args.steps:
            report["stopped_early"] = {"after_step": step + 1, "cap_seconds": args.max_train_seconds}
            print(json.dumps({"stopped_early": report["stopped_early"]}), flush=True)
            break
    bench.sync(device)
    report["train_seconds"] = round(time.perf_counter() - t0, 1)
    lm.eval()
    g10_router.clear_router_bias_load(lm)  # train-mode load counts: only update_router_bias() reads them; G10 never calls it
    bias_after = g10_router.router_bias_checksum(lm)
    # pass False also when the arm's config says a bias exists but no router_bias buffer is found (job BNP)
    report["router_bias_unchanged"] = g10_router.router_bias_record(lm, bias_before, bias_after, bundle.spec)
    if frozen_before is not None:
        after = bench.frozen_sha256(lm, marker_ids if marker_param is not None else None)
        report["frozen_weights_unchanged"] = {"before": frozen_before, "after": after, "pass": after == frozen_before}
    if args.method == "dt":
        method_info["deletion_final"] = dtmask.deletion_stats(lm)
        keep = dtmask.bake(lm)  # {param name: bool keep mask}; RL after this SFT holds these entries at zero
        blob, meta = dtmask.pack_masks(keep)
        (out / "dt_keep_masks.bin").write_bytes(blob)
        (out / "dt_keep_masks.bin.json").write_text(json.dumps(meta))
        method_info["keep_masks"] = {"file": "dt_keep_masks.bin", "layers": meta["layers"], "bits": meta["bits"],
                                     "sha256": hashlib.sha256(blob).hexdigest(),
                                     "deleted_final": sum(int((~m).sum()) for m in keep.values())}
    if args.method == "lora":
        bench.merge_lora(lm)
    report["im_end_at_targets"]["after"] = marker_lift_stats(lm, eval_rows, im_end_id, device)
    if marker_param is not None:
        report["marker_budget"] = marker_budget(args.marker_lr, [r["lr"] / args.lr for r in log],
                                                report["im_end_at_targets"]["before"])
    post = {"eval_loss": eval_loss(wrapper, eval_rows, device, args.micro_tokens)}
    if args.heldout:
        post["forgetting"] = forgetting_bpb(bundle, args.heldout, args.heldout_sources, device)
    post["generation"], post_recs = generate_and_judge(bundle, eval_rows, args.gen_max_new, args.gen_limit,
                                                         args.gen_seconds)
    if args.rl_tasks and args.rl_ids:  # does SFT give the RL prompts any signal? base vs trained, same prompts
        import day_one_probe  # noqa: PLC0415
        post["rl_screen"] = day_one_probe.rl_screen_bundle(bundle, args.rl_tasks, args.rl_ids, args.rl_k,
                                                           args.rl_max_new, device, args.rl_limit,
                                                              args.rl_seconds)
    report["after"] = post
    # save as a plain G5 state dict and reload into a fresh LanguageModel
    sha = save_state(lm, out / "model.safetensors", {"g10": "capstone sft " + args.method,
                                                       "adapter_status": result.status})
    from safetensors.torch import load_file

    fresh = type(lm)(bundle.spec, bundle.artifacts.bytes, bundle.artifacts.lengths)
    fresh.load_state_dict(load_file(str(out / "model.safetensors")), strict=True)
    fresh.to(device).eval()
    probe_ids = torch.tensor([eval_rows[0]["input_ids"][:64]], device=device)
    v = torch.ones_like(probe_ids, dtype=torch.bool)
    with torch.no_grad():
        diff = float((fresh(probe_ids, v) - lm(probe_ids, v)).abs().max())
    report["reload_parity"] = {"state_sha256": sha, "logits_max_abs_diff": diff, "pass": diff == 0.0}
    if args.team7_ckpt_remote:
        def _t7_probe(m):
            with torch.no_grad():
                logits = m(probe_ids, v).float()
                return torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, logits.size(-1)),
                                                         probe_ids[:, 1:].reshape(-1))

        t7_local = args.team7_local_root or (out / "_team7_local")
        t7_export = args.team7_export_path or (out / "team7_exported_model.safetensors")
        t7_run_id = args.team7_run_id or out.name
        report["team7_checkpoint"] = save_and_export_team7(
            lm,
            opt,
            model_factory=lambda: type(lm)(bundle.spec, bundle.artifacts.bytes, bundle.artifacts.lengths).to(device).eval(),
            probe_fn=_t7_probe,
            step=len(log),
            tokens=sum(r["targets"] for r in log),
            run_id=t7_run_id,
            local_root=t7_local,
            remote_root=args.team7_ckpt_remote,
            export_path=t7_export,
            seed=args.seed,
            reason=f"sft_{args.method}",
        )
    if args.keep_weights_dir:  # default off: save this arm's plain weights as a Team 7 run folder for Team 9's reader
        import keep_weights  # noqa: PLC0415
        report["kept_weights"] = keep_weights.save_run_folder(lm, args.keep_weights_dir, args.keep_run_id, step=len(log),
                                                              probe_fn=keep_weights.team5_probe)
    report["log"] = log
    report["first_loss"], report["last_loss"] = log[0]["loss"], log[-1]["loss"]
    (out / "sft_report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    priv = out / "generations.jsonl"
    with priv.open("w", encoding="utf-8") as f:
        for when, recs in (("before", pre_recs), ("after", post_recs)):
            for x in recs:
                f.write(json.dumps({"when": when, **x}) + "\n")
    return report


class _SftLoaderState:
    """Minimal loader state for Team 7 Checkpointer.save on single-process G10 SFT runs."""

    def __init__(self, step: int, rows_seen: int):
        self._step = int(step)
        self._rows_seen = int(rows_seen)

    def state_dict(self) -> dict:
        return {"step": self._step, "rows_seen": self._rows_seen}

    def next_batch_id(self) -> int:
        return self._step


def _load_team7_ckpt():
    """Load teams/07-infrastructure/ckpt/ckpt.py from the repo root without touching Team 7 files."""
    ckpt_file = TEAM10.parent / "07-infrastructure" / "ckpt" / "ckpt.py"
    if not ckpt_file.is_file():
        raise FileNotFoundError(f"Team 7 checkpointer not found at {ckpt_file}")
    return _load("g10_team7_ckpt", ckpt_file)


def _optim_matches_model(lm: nn.Module, optim) -> bool:
    if optim is None:
        return False
    model_ids = {id(p) for p in lm.parameters()}
    opt_ids = {id(p) for g in optim.param_groups for p in g["params"]}
    return bool(opt_ids) and opt_ids.issubset(model_ids)


def save_and_export_team7(
    lm: nn.Module,
    optim,
    *,
    model_factory,
    probe_fn,
    step: int,
    tokens: int,
    run_id: str,
    local_root: Path,
    remote_root: str | Path,
    export_path: Path,
    seed: int = 1,
    reason: str = "sft_final",
    code_paths: tuple[str, ...] = (),
) -> dict:
    """Commit a single-process G10 SFT checkpoint through Team 7 Checkpointer and export verified safetensors."""
    ckpt = _load_team7_ckpt()
    save_opt = optim if _optim_matches_model(lm, optim) else torch.optim.SGD(lm.parameters(), lr=0.0)
    local_root = Path(local_root)
    local_root.mkdir(parents=True, exist_ok=True)
    export_path = Path(export_path)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    ck = ckpt.Checkpointer(
        run_id=run_id,
        local_root=str(local_root),
        remote_root=str(remote_root),
        seed=seed,
        verify_mode="full",
        code_paths=code_paths or (str(Path(__file__).resolve()),),
    )
    loader = _SftLoaderState(step=step, rows_seen=tokens)
    saved = ck.save(step=step, model=lm, optim=save_opt, loader=loader, probe_fn=probe_fn,
                    tokens=tokens, reason=reason)
    if not saved:
        raise RuntimeError("Team 7 Checkpointer.save skipped saving (insufficient disk headroom)")
    if not ck.wait():
        raise RuntimeError(f"Team 7 Checkpointer upload/commit failed for run_id={run_id} step={step}")
    exp = ckpt.export_safetensors(
        remote_run=ck.remote_url,
        model_factory=model_factory,
        probe_fn=probe_fn,
        out_path=str(export_path),
        step=step,
    )
    return {
        "run_id": run_id,
        "step": exp["step"],
        "remote_url": ck.remote_url,
        "export_path": str(export_path),
        "export_sha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
        "probe_bits": exp["probe_bits"],
        "used_live_optim": save_opt is optim,
    }


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--adapter-config", type=Path, required=True)
    p.add_argument("--train", type=Path, required=True)
    p.add_argument("--eval", type=Path, required=True)
    p.add_argument("--method", choices=("full", "lora", "dt", "markers"), required=True)
    p.add_argument("--marker-rows", action="store_true")
    p.add_argument("--drop-over-block", action="store_true", help="drop (count, never cut) rows longer than the model")
    p.add_argument("--marker-lr", type=float, default=1e-3)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--batch", type=int, default=16, help="rows per optimizer step")
    p.add_argument("--micro-tokens", type=int, default=2048)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--warmup", type=int, default=10)
    p.add_argument("--min-lr-ratio", type=float, default=0.1)
    p.add_argument("--wd", type=float, default=0.0)
    p.add_argument("--clip", type=float, default=1.0)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=float, default=32.0)
    p.add_argument("--dt-targets", default="g5_mlp", choices=sorted(k for k in dtmask.TARGET_SETS if k.startswith("g5_")))
    p.add_argument("--dt-alpha-start", type=float, default=100.0)
    p.add_argument("--dt-alpha-end", type=float, default=1000.0)
    p.add_argument("--dt-lambda", type=float, default=1e-5)
    p.add_argument("--dt-eta", type=float, default=0.05)
    p.add_argument("--dt-prior-strength", type=float, default=3.0)
    p.add_argument("--dt-unseen", default="official", choices=("official", "keep"),
                   help="uncalibrated layer logits: official = no prior, keep = shift up to reduce initial deletion")
    p.add_argument("--dt-calib-rows", type=int, default=64)
    p.add_argument("--rl-tasks", type=Path, help="RL data v1 stdio task file: screen before and after SFT")
    p.add_argument("--rl-ids", type=Path)
    p.add_argument("--rl-k", type=int, default=8)
    p.add_argument("--rl-max-new", type=int, default=512)
    p.add_argument("--rl-limit", type=int, default=0, help="screen at most this many RL prompts (0 = all)")
    p.add_argument("--rl-seconds", type=float, default=0.0, help="time budget per RL screen; no new prompt after it (0 = off)")
    p.add_argument("--gen-seconds", type=float, default=0.0, help="time budget per greedy format screen (0 = off)")
    p.add_argument("--no-before", action="store_true",
                   help="skip the base-model evaluation (eval loss, forgetting, generation, RL screen) before training")
    p.add_argument("--max-train-seconds", type=float, default=0.0, help="stop training after this long (0 = off)")
    p.add_argument("--heldout", type=Path)
    p.add_argument("--heldout-sources", type=Path)
    p.add_argument("--gen-limit", type=int, default=32)
    p.add_argument("--gen-max-new", type=int, default=48)
    p.add_argument("--device", default="cpu")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--log-every", type=int, default=20)
    p.add_argument("--team7-ckpt-remote", type=str, default=None,
                   help="optional Team 7 Checkpointer remote root (dir or s3://...); saves DCP checkpoint and exports verified safetensors")
    p.add_argument("--team7-run-id", type=str, default=None, help="run_id for Team 7 Checkpointer (default: --out folder name)")
    p.add_argument("--team7-local-root", type=Path, default=None, help="local staging dir for Team 7 Checkpointer")
    p.add_argument("--team7-export-path", type=Path, default=None, help="output path for Team 7 export_safetensors")
    p.add_argument("--keep-weights-dir", type=Path,
                   help="default off: also save the final plain weights as a Team 7 run folder <dir>/<keep-run-id>")
    p.add_argument("--keep-run-id", "--keep-weights-id", dest="keep_run_id", default="g10-sft",
                   help="run id (folder name) of the kept weights; --keep-weights-id is the spelling dryrun2_dt_compare.py passes")
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args(argv)


def main(argv=None) -> int:
    run(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
