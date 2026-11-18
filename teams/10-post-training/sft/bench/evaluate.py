"""Bench evaluation, run as its own process (eval firewall: train.py never imports this file or reads its inputs).

Model-side metrics (one process, one model):
    python evaluate.py --model <saved model dir | hub id> [--revision sha] --split-file <slice>/test.tok.jsonl \
        --metrics bpb,format,forget --heldout <heldout_v1.jsonl> --heldout-sources <heldout_v1_sources.jsonl> \
        --generations-out gens.jsonl --out report.json
Execution scoring of saved generations (needs Docker; runs where the sandbox is):
    python evaluate.py --score-exec --generations gens.jsonl --exec-tasks test.exec.jsonl --out exec.json
Team 9 eval-mini as a black box (scores only; its own virtualenv):
    python evaluate.py --eval-mini --model <dir> --eval-mini-python <venv>/bin/python --out evalmini.json

(a) bpb      held-out target bits per byte: sum of NLL (nats) over the masked target tokens of every row, teacher
             forced, / ln 2 / the UTF-8 bytes of the rows' G10-surface assistant spans, recomputed from `surrogate_text`
             (retok.target_bytes_of), never taken from the stored `target_bytes` field.
             Loss computation imported from train.py, so it is the trained objective.
(b) format   greedy free generation from each problem's prompt (system + user + `<|im_start|>assistant\\n`), one prompt
             per cluster, up to --gen-limit, total length <= --max-total-tokens. Valid = the generation stops on
             `<|im_end|>`, contains no foreign special token, and prompt + generation + "\\n<|endoftext|>" (mapped back to
             G10 surfaces) is accepted by chat-format `render.parse()` with exactly one new, non-empty assistant turn.
(c) exec     pass@1 (greedy) through `rl-data/stdio_check.score` (Docker sandbox, expected outputs never enter it).
(d) forget   bits per byte on G5 held-out v1, G5 protocol (`harness/week2/data.py`): each document tokenised alone, BOS
             (id 0) before the first window, non-overlapping windows of --forget-window target tokens with the previous
             token as context, every token scored; per slice sum(nats)/ln2/sum(bytes) bound by G5 `scoring.source_slices`
             and grouped by G5 `scoring.group_metrics`.
(e) eval-mini Team 9 `run_eval_mini.py --profile mini --tasks arc_challenge hellaswag`, primary metrics only.
Evaluation runs in FP32 (TF32 off on CUDA) on every backend. No dataset or benchmark text is printed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]
REPO = TEAM.parents[1]
LN2 = math.log(2)


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


retok = _load("g10_bench_retok", HERE / "retok.py")
render = retok.render
T = render.T
SPECIAL_TO_G10 = {sid: T[name] for name, (_, sid) in retok.MARKER_MAP.items()}
N_SPECIAL = len(retok.SURROGATE_SPECIALS)


# ---------------------------------------------------------------- inputs


def load_eval_rows(path: str | Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r.get("split") not in ("dev", "test"):
                    raise SystemExit(f"{path}: row with split {r.get('split')!r}; evaluate.py scores dev/test rows only")
                rows.append(r)
    return rows


def load_model(name: str, revision: str | None, device: str):
    import torch
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(name, revision=revision, dtype=torch.float32, attn_implementation="sdpa")
    return model.to(device).eval()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def token_batches(lengths: list[int], budget: int) -> list[list[int]]:
    order = sorted(range(len(lengths)), key=lambda i: lengths[i])
    out, cur = [], []
    for i in order:
        if cur and (len(cur) + 1) * lengths[i] > budget:
            out.append(cur)
            cur = []
        cur.append(i)
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- (a) target bpb


def target_bpb(model, rows: list[dict], device: str, budget: int) -> dict:
    import torch

    trainmod = _load("g10_bench_train", HERE / "train.py")  # the loss, not the training loop
    nats, n_tgt = 0.0, 0
    for idx in token_batches([len(r["input_ids"]) for r in rows], budget):
        batch = trainmod.collate([{"input_ids": rows[i]["input_ids"], "loss_mask": rows[i]["loss_mask"]} for i in idx], 0)
        batch = trainmod.probe.Batch(*(t.to(device) for t in (batch.input_ids, batch.attention_mask, batch.labels, batch.kinds)))
        with torch.no_grad():
            s, c = trainmod.target_nll_sum(model, batch)
        nats += float(s)
        n_tgt += c
    tbytes = sum(retok.target_bytes_of(r["surrogate_text"]) for r in rows)  # recomputed, not the stored field
    stored = sum(r["target_bytes"] for r in rows)
    want = sum(sum(r["loss_mask"][1:]) for r in rows)
    if n_tgt != want:
        raise RuntimeError(f"scored {n_tgt} targets, rows hold {want}")
    return {"rows": len(rows), "target_tokens": n_tgt, "target_bytes": tbytes, "stored_target_bytes_field": stored, "nll_nats": nats,
            "nats_per_target_token": nats / n_tgt, "bpb": nats / LN2 / tbytes}


# ---------------------------------------------------------------- (b) format validity


def ids_to_g10(tok, ids: list[int]) -> tuple[str, str | None]:
    """Decode ids to G10-surface text. Returns (text, problem) where problem names a foreign special or marker text."""
    parts, run = [], []

    def flush():
        if run:
            piece = tok.decode(run, skip_special_tokens=False)
            parts.append(piece)
            run.clear()
            return piece
        return ""

    problem = None
    for t in ids:
        if t < N_SPECIAL:
            piece = flush()
            if any(s in piece for s in retok.SURROGATE_SPECIALS) and problem is None:
                problem = "special_surface_as_plain_text"
            if t not in SPECIAL_TO_G10:
                problem = problem or "foreign_special_token"
                continue
            parts.append(SPECIAL_TO_G10[t])
        else:
            run.append(t)
    piece = flush()
    if any(s in piece for s in retok.SURROGATE_SPECIALS) and problem is None:
        problem = "special_surface_as_plain_text"
    return "".join(parts), problem


def judge(tok, prompt_ids: list[int], gen_ids: list[int]) -> dict:
    head = f"{T['im_start']}assistant\n"
    prompt_text, _ = ids_to_g10(tok, prompt_ids)
    if not prompt_text.endswith(head):
        raise RuntimeError("prompt does not end with the assistant header")
    n_prompt = len(render.parse(prompt_text[: -len(head)] + T["endoftext"])["messages"])
    stop = next((i for i, t in enumerate(gen_ids) if t in (retok.IM_END_ID, retok.EOS_ID)), None)
    closed = stop is not None and gen_ids[stop] == retok.IM_END_ID
    body = gen_ids[: stop + 1] if stop is not None else gen_ids
    rec = {"gen_tokens": len(body), "closed_im_end": closed,
           "stopped_eos_first": stop is not None and gen_ids[stop] == retok.EOS_ID, "hit_budget": stop is None}
    gen_text, problem = ids_to_g10(tok, body)
    rec.update(valid=False, has_think=False, has_code_block=False, content=None)
    if problem:
        rec["reason"] = problem
    elif not closed:
        rec["reason"] = "no_im_end" if stop is None else "eos_before_im_end"
    else:
        try:
            msgs = render.parse(prompt_text + gen_text + "\n" + T["endoftext"])["messages"]
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
                rec.update(valid=True, reason="ok", has_think="think" in last, has_code_block="```" in last["content"])
            rec["content"] = last.get("content")
    if rec["content"] is None:  # still give the exec scorer the raw text (minus markers) to look for code
        rec["content"] = retok.from_surrogate(gen_text)
    return rec


def generate_and_judge(model, tok, rows: list[dict], device: str, gen_limit: int, max_total: int, batch_size: int) -> tuple[dict, list[dict]]:
    import torch

    reps: dict[str, dict] = {}
    for r in sorted(rows, key=lambda r: r["id"]):
        reps.setdefault(r["cluster"], r)
    prompts = list(reps.values())[:gen_limit]
    order = sorted(range(len(prompts)), key=lambda i: prompts[i]["prompt_len"])
    records = [None] * len(prompts)
    t0 = time.perf_counter()
    gen_tokens = 0
    for b in range(0, len(order), batch_size):
        idx = order[b : b + batch_size]
        plist = [prompts[i]["input_ids"][: prompts[i]["prompt_len"]] for i in idx]
        L = max(len(p) for p in plist)
        ids = torch.zeros((len(plist), L), dtype=torch.long)
        attn = torch.zeros((len(plist), L), dtype=torch.long)
        for j, p in enumerate(plist):  # left padding
            ids[j, L - len(p):] = torch.tensor(p)
            attn[j, L - len(p):] = 1
        max_new = max_total - L
        with torch.no_grad():
            out = model.generate(input_ids=ids.to(device), attention_mask=attn.to(device), max_new_tokens=max_new,
                                 do_sample=False, eos_token_id=[retok.IM_END_ID, retok.EOS_ID], pad_token_id=retok.EOS_ID)
        new = out[:, L:].cpu().tolist()
        for j, i in enumerate(idx):
            rec = judge(tok, plist[j], new[j])
            gen_tokens += rec["gen_tokens"]
            rec.update(cluster=prompts[i]["cluster"], row_id=prompts[i]["id"], max_new_tokens=max_new)
            records[i] = rec
    secs = time.perf_counter() - t0
    n = len(records)
    reasons: dict[str, int] = {}
    for r in records:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    summary = {"prompts": n, "valid": sum(r["valid"] for r in records), "format_validity": sum(r["valid"] for r in records) / n,
               "closed_im_end": sum(r["closed_im_end"] for r in records) / n,
               "hit_budget": sum(r["hit_budget"] for r in records) / n,
               "has_think": sum(r["has_think"] for r in records) / n,
               "valid_with_code_block": sum(r["valid"] and r["has_code_block"] for r in records) / n,
               "mean_gen_tokens": gen_tokens / n, "reasons": dict(sorted(reasons.items())),
               "decoding": "greedy", "max_total_tokens": max_total, "batch_size": batch_size,
               "seconds": round(secs, 1), "gen_tokens_per_s": round(gen_tokens / secs, 1)}
    return summary, records


# ---------------------------------------------------------------- (c) exec


def score_exec(generations: Path, tasks_path: Path, limit: int, workers: int) -> dict:
    stdio = _load("g10_stdio_check_for_bench", TEAM / "rl-data" / "stdio_check.py")
    tasks = {}
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            if t.get("split") == "train":
                raise SystemExit("exec tasks must be dev/test")
            tasks[t["id"]] = t
    gens = [json.loads(l) for l in generations.read_text(encoding="utf-8").splitlines() if l.strip()]
    pairs = [(tasks[g["cluster"]], g["content"] or "") for g in gens if g["cluster"] in tasks][:limit]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(lambda p: stdio.score(p[0], p[1]), pairs))
    reasons: dict[str, int] = {}
    for r in results:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    n = len(results)
    return {"problems": n, "passed": sum(r["reward"] for r in results), "pass_at_1": (sum(r["reward"] for r in results) / n) if n else None,
            "reasons": dict(sorted(reasons.items())), "runner": stdio.RUNNER_KIND, "image": stdio.IMAGE,
            "generations_without_task": sum(1 for g in gens if g["cluster"] not in tasks),
            "seconds": round(time.perf_counter() - t0, 1)}


# ---------------------------------------------------------------- (d) forgetting


def forgetting_bpb(model, tok, heldout: Path, sources: Path, device: str, window: int, budget: int) -> dict:
    import torch
    import torch.nn.functional as F

    scoring = _load("g5_scoring_for_bench", REPO / "teams" / "05-architecture" / "harness" / "week2" / "scoring.py")
    records = [json.loads(l) for l in heldout.read_text(encoding="utf-8").splitlines() if l.strip()]
    slices = scoring.source_slices(sources, records)
    encs = tok.encode_batch([d["text"] for d in records], add_special_tokens=False)
    windows, wslice = [], []
    slice_bytes: dict[str, int] = {}
    for doc, name, enc in zip(records, slices, encs):
        slice_bytes[name] = slice_bytes.get(name, 0) + len(doc["text"].encode("utf-8"))
        ids = enc.ids
        for start in range(0, len(ids), window):
            target = ids[start : start + window]
            prev = retok.EOS_ID if start == 0 else ids[start - 1]  # SmolLM2 bos = <|endoftext|> = 0
            windows.append(([prev] + target[:-1], target))
            wslice.append(name)
    nats: dict[str, float] = {}
    t0 = time.perf_counter()
    n_tok = 0
    for idx in token_batches([len(w[1]) for w in windows], budget):
        L = max(len(windows[i][1]) for i in idx)
        inp = torch.zeros((len(idx), L), dtype=torch.long)
        tgt = torch.full((len(idx), L), -100, dtype=torch.long)
        attn = torch.zeros((len(idx), L), dtype=torch.long)
        for j, i in enumerate(idx):
            a, b = windows[i]
            inp[j, : len(a)] = torch.tensor(a)
            tgt[j, : len(b)] = torch.tensor(b)
            attn[j, : len(a)] = 1
        inp, tgt, attn = inp.to(device), tgt.to(device), attn.to(device)
        with torch.no_grad():
            h = model.model(input_ids=inp, attention_mask=None if len(idx) == 1 else attn).last_hidden_state
            sel = tgt != -100
            logits = model.lm_head(h[sel]).float()
            per = F.cross_entropy(logits, tgt[sel], reduction="none")
        # per-window sums (rows of `sel` are in row-major order)
        counts = sel.sum(dim=1).tolist()
        sums = torch.split(per, counts)
        for j, i in enumerate(idx):
            nats[wslice[i]] = nats.get(wslice[i], 0.0) + float(sums[j].double().sum())
        n_tok += int(sel.sum())
    per_slice = {k: nats[k] / LN2 / slice_bytes[k] for k in nats}
    groups = scoring.group_metrics(per_slice)
    total_bpb = sum(nats.values()) / LN2 / sum(slice_bytes.values())
    return {"heldout_sha256": sha256_file(heldout), "documents": len(records), "tokens": n_tok, "windows": len(windows),
            "window": window, "bpb_all": total_bpb, "groups": groups, "slices": per_slice,
            "seconds": round(time.perf_counter() - t0, 1)}


# ---------------------------------------------------------------- (e) eval-mini


def eval_mini(model_dir: str, python: str, runs_dir: Path, device: str, tasks: list[str]) -> dict:
    runner = REPO / "teams" / "09-evaluation" / "harness" / "run_eval_mini.py"
    cmd = [python, str(runner), "--model", model_dir, "--profile", "mini", "--tasks", *tasks, "--dtype", "float32",
           "--device", device, "--runs-dir", str(runs_dir)]
    t0 = time.perf_counter()
    env = {**os.environ, "HF_HUB_DISABLE_PROGRESS_BARS": "1"}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = {"command": " ".join(cmd[1:]), "returncode": proc.returncode, "seconds": round(time.perf_counter() - t0, 1)}
    summaries = sorted(runs_dir.rglob("summary.json"))
    if proc.returncode != 0 or not summaries:
        out["error_tail"] = [l for l in proc.stderr.splitlines() if "Error" in l or "error" in l][-3:]
        return out
    data = json.loads(summaries[-1].read_text())
    out["records"] = [{k: r[k] for k in ("task", "metric", "filter", "value", "stderr", "n_items", "num_fewshot")}
                      for r in data["records"] if r.get("primary")]
    out["harness"] = data["run_meta"].get("versions")
    return out


# ---------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model")
    ap.add_argument("--revision")
    ap.add_argument("--tokenizer", help="tokenizer.json (default: the model folder's)")
    ap.add_argument("--split-file")
    ap.add_argument("--metrics", default="bpb,format,forget")
    ap.add_argument("--heldout", default=str(REPO / "teams/05-architecture/heldout_v1/data/heldout_v1.jsonl"))
    ap.add_argument("--heldout-sources", default=str(REPO / "teams/05-architecture/heldout_v1/data/heldout_v1_sources.jsonl"))
    ap.add_argument("--forget-window", type=int, default=2048)
    ap.add_argument("--gen-limit", type=int, default=200)
    ap.add_argument("--gen-batch", type=int, default=16)
    ap.add_argument("--max-total-tokens", type=int, default=2048)
    ap.add_argument("--token-budget", type=int, default=8192, help="tokens per teacher-forced batch")
    ap.add_argument("--generations-out")
    ap.add_argument("--score-exec", action="store_true")
    ap.add_argument("--generations")
    ap.add_argument("--exec-tasks")
    ap.add_argument("--exec-limit", type=int, default=100)
    ap.add_argument("--exec-workers", type=int, default=4)
    ap.add_argument("--eval-mini", action="store_true")
    ap.add_argument("--eval-mini-python")
    ap.add_argument("--eval-mini-tasks", default="arc_challenge,hellaswag")
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    for out_path in (args.out, args.generations_out):
        if out_path:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    import torch

    device = args.device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    if device.startswith("cuda"):
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    report: dict = {"schema": "g10-bench-eval/1", "device": device, "torch": torch.__version__,
                    "compute_dtype": "float32 (TF32 off)"}
    if args.score_exec:
        report["exec"] = score_exec(Path(args.generations), Path(args.exec_tasks), args.exec_limit, args.exec_workers)
        report["generations_sha256"] = sha256_file(args.generations)
        report["exec_tasks_sha256"] = sha256_file(args.exec_tasks)
    elif args.eval_mini:
        report["eval_mini"] = eval_mini(args.model, args.eval_mini_python, Path(args.out).with_suffix(".runs"), device,
                                        args.eval_mini_tasks.split(","))
    else:
        from tokenizers import Tokenizer

        model = load_model(args.model, args.revision, device)
        tok_path = args.tokenizer or str(Path(args.model) / "tokenizer.json")
        tok = Tokenizer.from_file(tok_path)
        retok.check_tokenizer(tok)
        report.update(model=args.model, revision=args.revision, tokenizer_sha256=sha256_file(tok_path))
        mfile = Path(args.model) / "model.safetensors"
        if mfile.is_file():
            report["model_safetensors_sha256"] = sha256_file(mfile)
        metrics = args.metrics.split(",")
        rows = load_eval_rows(args.split_file) if args.split_file else []
        if rows:
            report["split_file_sha256"] = sha256_file(args.split_file)
            report["split"] = rows[0]["split"]
        if "bpb" in metrics:
            t0 = time.perf_counter()
            report["target_bpb"] = target_bpb(model, rows, device, args.token_budget)
            report["target_bpb"]["seconds"] = round(time.perf_counter() - t0, 1)
        if "format" in metrics:
            summary, records = generate_and_judge(model, tok, rows, device, args.gen_limit, args.max_total_tokens, args.gen_batch)
            report["format"] = summary
            if args.generations_out:
                Path(args.generations_out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
                report["generations_sha256"] = sha256_file(args.generations_out)
        if "forget" in metrics:
            report["forgetting"] = forgetting_bpb(model, tok, Path(args.heldout), Path(args.heldout_sources), device,
                                                  args.forget_window, args.token_budget)
        if device.startswith("cuda"):
            report["cuda_peak_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
    Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    brief = {k: v for k, v in report.items() if k in ("target_bpb", "exec", "eval_mini")}
    if "format" in report:
        brief["format"] = {k: report["format"][k] for k in ("prompts", "format_validity", "closed_im_end", "hit_budget", "seconds")}
    if "forgetting" in report:
        brief["forgetting"] = {"bpb_all": report["forgetting"]["bpb_all"], "groups": report["forgetting"]["groups"]}
    print(json.dumps(brief, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
