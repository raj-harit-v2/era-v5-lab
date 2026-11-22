"""RL screen of a (post-SFT) surrogate model: what share of k samples per RL prompt clears each step of
"closed turn -> code block -> program runs -> right answer", and how many prompts give a mixed group.

    python rl_screen.py --model <saved model dir> --tasks cc.jsonl --set rung1=<ids> --set rest=<ids> \
        --k 8 --temperature 1 --max-new 1024 --out <private dir>
    python rl_screen.py --control constant --tasks cc.jsonl --set rung1=<ids> --k 8 --out <dir>   # cheap-trick rows
    python rl_screen.py --rescore --out <dir> --hidden-tests hidden.jsonl                          # strict tests

Prompt: the record's human-written statement as the user turn, under the pack's own system line ("Reasoning effort:
1k"), then `<|im_start|>assistant\\n`, rendered with the G10 markers and mapped to the surrogate's specials by
retok.py. No instruction text is added (the same rule as rl-loop/train.py stdio tasks). Sampling: temperature 1, no
top-k / top-p truncation (the RL sampler's distribution), stop on `<|im_end|>`, `<|endoftext|>` or `<|im_start|>`.

Per completion (private generations.jsonl): the bench format judge (evaluate.judge: closed turn, valid render,
code fence), whether rl/verifier.extract_code finds a program, whether it parses (ast), and the RL reward record
(rl-data/stdio_check.score on the decoded completion, exactly what the RL loop scores; Docker sandbox through
rl-loop/score_pool.py). Identical (task, program) pairs are run once. With --hidden-tests, every completion that
passed the kept tests is also run on the unused source tests ("strict"). Shares and the mixed-group share come with
95% intervals from a bootstrap over problems (the independent unit). No dataset or completion text is printed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ev = _load("g10_bench_evaluate", HERE / "evaluate.py")
retok = ev.retok
T = ev.T
verifier = _load("g10_rl_verifier_for_screen", TEAM / "rl" / "verifier.py")
STOP_IDS = (retok.IM_END_ID, retok.EOS_ID, retok.MARKER_MAP["im_start"][1])
CONSTANT_REPLY = "```python\nprint(0)\n```"  # a control, never training data: closed turn + a program that always runs
LADDER = ("closed", "closed_content", "valid_format", "code_block", "parses", "runs", "pass_kept", "pass_strict")


# ---------------------------------------------------------------- prompts


def render_prompt(statement: str, effort: str = "1k") -> str:
    """G10-surface prompt: system effort line, the statement as the user turn, the assistant header."""
    return (f"{T['im_start']}system\nReasoning effort: {effort}{T['im_end']}\n"
            f"{T['im_start']}user\n{statement}{T['im_end']}\n{T['im_start']}assistant\n")


def encode_prompts(tok, tasks: list[dict], effort: str) -> tuple[list[tuple[dict, list[int]]], dict]:
    out, rejected = [], {}
    texts, keep = [], []
    for t in tasks:
        try:
            surr, _ = retok.to_surrogate(render_prompt(t["statement"], effort))
        except retok.RetokReject as e:
            rejected[str(e)] = rejected.get(str(e), 0) + 1
            continue
        texts.append(surr)
        keep.append(t)
    for t, enc in zip(keep, tok.encode_batch(texts, add_special_tokens=False)):
        out.append((t, enc.ids))
    return out, rejected


# ---------------------------------------------------------------- per-completion record


def code_status(text: str) -> dict:
    code, why = verifier.extract_code(text)
    rec = {"has_fence": "```" in text, "code_extracted": code is not None, "extract_reason": why if code is None else "ok"}
    if code is not None:
        try:
            ast.parse(code)
            rec["parses"] = True
        except (SyntaxError, ValueError):
            rec["parses"] = False
    else:
        rec["parses"] = False
    return rec


def outcome(rec: dict) -> str:
    """One failure reason per completion, ordered along the ladder (the first step it fails)."""
    if not rec["code_extracted"]:
        if rec.get("hit_budget"):
            return "no_code_truncated"
        return "no_code_closed" if rec.get("closed_im_end") else "no_code_other_stop"
    if not rec["parses"]:
        return "syntax_error"
    why = str(rec.get("score_reason", ""))
    if rec.get("reward") == 1:
        return "pass"
    if why.startswith("wrong answer"):
        return "wrong_answer"
    if why.startswith("timeout"):
        return "timeout"
    if why.startswith("error on a test"):
        return "runtime_error"
    return "runner_failure"


def ladder_flags(rec: dict) -> dict:
    out = outcome(rec)
    flags = {"closed": bool(rec.get("closed_im_end")),
             "closed_content": bool(rec.get("closed_im_end")) and bool(str(rec.get("text", "")).strip()),
             "valid_format": bool(rec.get("valid")),
             "code_block": bool(rec["code_extracted"]), "parses": bool(rec["parses"]),
             "runs": out in ("pass", "wrong_answer"), "pass_kept": rec.get("reward") == 1}
    if "strict" in rec:
        flags["pass_strict"] = bool(rec["strict"])
    return flags


# ---------------------------------------------------------------- aggregation


def bootstrap_ci(per_prob: list[tuple[float, float]], n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% percentile interval of sum(num)/sum(den), resampling problems."""
    import numpy as np  # noqa: PLC0415
    a = np.asarray(per_prob, dtype=float)
    if len(a) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n_boot, len(a)))
    num, den = a[idx, 0].sum(1), a[idx, 1].sum(1)
    est = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)
    lo, hi = np.nanpercentile(est, [2.5, 97.5])
    return (round(float(lo), 4), round(float(hi), 4))


def aggregate(records: list[dict], k: int, n_boot: int = 2000) -> dict:
    by_task: dict[str, list[dict]] = {}
    for r in records:
        by_task.setdefault(r["task_id"], []).append(r)
    probs = sorted(by_task)
    n = sum(len(v) for v in by_task.values())
    rep = {"problems": len(probs), "completions": n, "k": k}
    flags = {tid: [ladder_flags(r) for r in by_task[tid]] for tid in probs}
    keys = [key for key in LADDER if all(key in f for fl in flags.values() for f in fl)]
    shares = {}
    for key in keys:
        pp = [(sum(f[key] for f in flags[tid]), len(flags[tid])) for tid in probs]
        shares[key] = {"share": round(sum(a for a, _ in pp) / max(n, 1), 4), "ci95": bootstrap_ci(pp, n_boot)}
    rep["ladder"] = shares
    reasons: dict[str, int] = {}
    for r in records:
        o = outcome(r)
        reasons[o] = reasons.get(o, 0) + 1
    rep["outcomes"] = dict(sorted(reasons.items(), key=lambda kv: -kv[1]))
    for key in ("pass_kept", "pass_strict"):
        if key not in keys:
            continue
        passes = [sum(f[key] for f in flags[tid]) for tid in probs]
        sizes = [len(flags[tid]) for tid in probs]
        mixed = [(int(0 < p < s), 1) for p, s in zip(passes, sizes)]
        rep[f"groups_{key}"] = {"mixed": sum(m for m, _ in mixed), "all_fail": sum(p == 0 for p in passes),
                                "all_pass": sum(p == s for p, s in zip(passes, sizes)),
                                "mixed_share": round(sum(m for m, _ in mixed) / max(len(probs), 1), 4),
                                "mixed_share_ci95": bootstrap_ci(mixed, n_boot),
                                "pass_at_k_share": round(sum(p > 0 for p in passes) / max(len(probs), 1), 4)}
    toks = [r.get("gen_tokens", 0) for r in records]
    rep["gen_tokens_mean"] = round(sum(toks) / max(n, 1), 1)
    rep["truncated_share"] = round(sum(bool(r.get("hit_budget")) for r in records) / max(n, 1), 4)
    return rep


# ---------------------------------------------------------------- scoring


def score_records(records: list[dict], tasks: dict[str, dict], workers: int) -> dict:
    """Fill reward / score_reason. One sandbox run per distinct (task, program)."""
    todo, keymap = {}, []
    for r in records:
        if not r["code_extracted"] or not r["parses"]:
            r["reward"], r["score_reason"] = 0, "not run (no parseable program)"
            keymap.append(None)
            continue
        code, _ = verifier.extract_code(r["text"])
        key = (r["task_id"], hashlib.sha256(code.encode()).hexdigest())
        todo.setdefault(key, r["text"])
        keymap.append(key)
    keys = list(todo)
    t0 = time.time()
    results = {}
    if keys:
        pool = _load("g10_score_pool", TEAM / "rl-loop" / "score_pool.py").ScorePool(workers)
        try:
            res = pool.score([(tasks[tid], todo[(tid, h)]) for tid, h in keys])
        finally:
            pool.close()
        results = dict(zip(keys, res))
    failed = [k for k, v in results.items() if str(v.get("reason", "")).startswith(RUNNER_FAILURES)]
    if failed:  # never a silent zero reward
        raise RuntimeError(f"{len(failed)} of {len(results)} programs hit a sandbox failure, e.g. "
                           f"{results[failed[0]].get('reason')!r}; fix the runner and rescore")
    for r, key in zip(records, keymap):
        if key is not None:
            s = results[key]
            r["reward"], r["score_reason"] = int(s.get("reward", 0)), s.get("reason", "")
            r["tests_passed"] = s.get("passed")
    return {"distinct_programs_run": len(keys), "score_seconds": round(time.time() - t0, 1), "workers": workers}


RUNNER_FAILURES = ("runner exited", "no readable output", "output file has the wrong shape")


def sandbox_preflight(workers: int) -> dict:
    """Positive and negative control through the same scorer pool before anything is generated: a right program must
    score 1 and a wrong one 0. A sandbox that is down (e.g. Docker not running) would otherwise score every program 0."""
    task = {"id": "preflight", "tests": [{"input": "1 2\n", "output": "3\n"}, {"input": "5 7\n", "output": "12\n"}],
            "time_limit_s": 4}
    good = "```python\na, b = map(int, input().split())\nprint(a + b)\n```"
    bad = "```python\nprint(0)\n```"
    pool = _load("g10_score_pool", TEAM / "rl-loop" / "score_pool.py").ScorePool(workers)
    try:
        r_good, r_bad = pool.score([(task, good), (task, bad)])
    finally:
        pool.close()
    if r_good.get("reward") != 1 or r_bad.get("reward") != 0:
        raise SystemExit(f"sandbox preflight failed (is Docker running?): good={r_good} bad={r_bad}")
    return {"good": r_good.get("reason"), "bad": r_bad.get("reason")}


def strict_rescore(records: list[dict], tasks: dict[str, dict], hidden: dict[str, list[dict]], workers: int) -> dict:
    """Completions that passed the kept tests, run on the unused tests in chunks of stdio_check.MAX_TESTS."""
    sc = _load("g10_stdio_check_screen", TEAM / "rl-data" / "stdio_check.py")
    items, idx = [], []
    for i, r in enumerate(records):
        if r.get("reward") != 1:
            r["strict"] = False
            continue
        if r["task_id"] not in hidden:
            r["strict"] = True  # no unused tests exist for this task: strict equals kept
            r["strict_note"] = "no unused tests"
            continue
        tests = hidden[r["task_id"]]
        for c in range(0, len(tests), sc.MAX_TESTS):
            items.append(({**tasks[r["task_id"]], "tests": tests[c:c + sc.MAX_TESTS]}, r["text"]))
            idx.append(i)
    if items:
        pool = _load("g10_score_pool", TEAM / "rl-loop" / "score_pool.py").ScorePool(workers)
        try:
            res = pool.score(items)
        finally:
            pool.close()
        ok: dict[int, bool] = {}
        for i, s in zip(idx, res):
            ok[i] = ok.get(i, True) and s.get("reward") == 1
        for i, v in ok.items():
            records[i]["strict"] = v
    return {"strict_runs": len(items), "tasks_with_unused_tests": sum(1 for r in records if r.get("reward") == 1
                                                                       and r["task_id"] in hidden)}


# ---------------------------------------------------------------- generation


def register_gqa_decode_attention(name: str = "gqa_decode") -> str:
    """One-token decode attention for grouped-query models without the stock SDPA path's copies. For q_len == 1 the stock
    path (math kernel with a mask) repeats K and V by the group size, scales a full copy of K and then multiplies, so a
    decode step costs about 7 ms per row at a 1,500-token context on a T4 whatever the dtype (17 Nov profile on a
    Kaggle T4). Here the query heads of one KV head are batched as rows of one matmul
    (B x Hkv batches of [G, D] x [D, C]), so K and V are read once. Prefill (q_len > 1) uses the stock SDPA function.
    Select it with `from_pretrained(..., attn_implementation=name)`; same math, different reduction order."""
    import torch  # noqa: PLC0415
    from transformers import AttentionInterface  # noqa: PLC0415
    from transformers.integrations.sdpa_attention import sdpa_attention_forward  # noqa: PLC0415
    from transformers.masking_utils import AttentionMaskInterface, sdpa_mask  # noqa: PLC0415

    def gqa_decode_attention(module, query, key, value, attention_mask, dropout=0.0, scaling=None, is_causal=None, **kw):
        if query.shape[2] != 1:
            return sdpa_attention_forward(module, query, key, value, attention_mask, dropout=dropout, scaling=scaling,
                                          is_causal=is_causal, **kw)
        b, h, _, d = query.shape
        kv_heads = key.shape[1]
        scale = scaling if scaling is not None else d ** -0.5
        scores = torch.matmul(query.reshape(b, kv_heads, h // kv_heads, d), key.transpose(-1, -2)) * scale  # [B, Hkv, G, C]
        if attention_mask is not None:  # [B, 1, 1, C]: bool (True = attend) or additive float
            m = attention_mask[:, :, -1:, : key.shape[-2]]
            scores = scores.masked_fill(~m, float("-inf")) if m.dtype == torch.bool else scores + m
        probs = torch.softmax(scores, dim=-1, dtype=torch.float32).to(value.dtype)
        return torch.matmul(probs, value).reshape(b, 1, h, d), None  # head h = kv * G + g, as repeat_kv orders them

    AttentionInterface.register(name, gqa_decode_attention)
    AttentionMaskInterface.register(name, sdpa_mask)
    return name


def decode_loop(model, ids, attn, k: int, max_new: int, temperature: float, stop_ids, pad_id: int,
                greedy: bool = False, drop_finished: bool = True, compact_every: int = 16,
                exact_rng: bool = True) -> tuple[list[list[int]], int]:
    """Batched sampling with a DynamicCache that drops rows once they hit a stop token (HF `generate` keeps them decoding
    until the whole batch is done). Same row order as `generate(num_return_sequences=k)`: row j*k+s is sample s of prompt j.
    Returns (generated ids per row, padded after the stop token; decoded row-steps). Compaction runs every `compact_every`
    steps and is also the only host sync besides the final copy (rows that finished in between keep decoding until then,
    their tokens are replaced by pad). greedy=True is argmax (the correctness test); otherwise softmax(logits/T) sampling,
    drawn over all n rows (exact_rng) so that the sampled ids equal HF generate's for the same seed."""
    import torch  # noqa: PLC0415
    from transformers import DynamicCache  # noqa: PLC0415
    dev = ids.device
    ids, attn = ids.repeat_interleave(k, 0), attn.repeat_interleave(k, 0)
    n = ids.shape[0]
    pos = (attn.cumsum(-1) - 1).clamp_min(0)  # the position ids HF derives from a left-padded mask
    stop = torch.tensor(list(stop_ids), device=dev)
    out = model(input_ids=ids, attention_mask=attn, position_ids=pos, past_key_values=DynamicCache(config=model.config),
                use_cache=True, logits_to_keep=1)  # logits of the last prompt position only (HF generate does the same)
    cache, logits = out.past_key_values, out.logits[:, -1, :]
    nxt_pos = pos[:, -1:] + 1
    rows = torch.arange(n, device=dev)
    gen = torch.full((n, max_new), pad_id, dtype=torch.long, device=dev)
    finished = torch.zeros(n, dtype=torch.bool, device=dev)
    pad = torch.full((n,), pad_id, dtype=torch.long, device=dev)
    row_steps = 0
    for t in range(max_new):
        if greedy:
            nxt = logits.argmax(-1)
        else:
            probs = torch.softmax(logits.float() / temperature, dim=-1)
            if exact_rng and probs.shape[0] != n:
                # HF generate draws one multinomial over ALL n rows every step. Draw over n rows here too (dropped rows get a
                # dummy one-hot distribution) so each live row consumes the same random numbers and the sampled ids equal
                # generate()'s for the same seed and batch, instead of a different random stream.
                full = torch.zeros((n, probs.shape[1]), dtype=probs.dtype, device=dev)
                full[:, 0] = 1.0
                full[rows] = probs
                nxt = torch.multinomial(full, 1).squeeze(1)[rows]
            else:
                nxt = torch.multinomial(probs, 1).squeeze(1)
        nxt = torch.where(finished, pad[: nxt.shape[0]], nxt)
        gen[rows, t] = nxt
        finished = finished | torch.isin(nxt, stop)
        row_steps += nxt.shape[0]
        if t == max_new - 1:
            break
        if (t + 1) % compact_every == 0:
            if bool(finished.all()):
                break
            if drop_finished and bool(finished.any()):
                keep = (~finished).nonzero().squeeze(1)
                cache.batch_select_indices(keep)
                attn, rows, nxt_pos, nxt, finished = attn[keep], rows[keep], nxt_pos[keep], nxt[keep], finished[keep]
        attn = torch.cat([attn, torch.ones_like(attn[:, :1])], dim=1)
        out = model(input_ids=nxt[:, None], attention_mask=attn, position_ids=nxt_pos, past_key_values=cache, use_cache=True)
        logits = out.logits[:, -1, :]
        nxt_pos = nxt_pos + 1
    return gen.cpu().tolist(), row_steps


def generate(model, tok, items: list[tuple[str, dict, list[int]]], k: int, max_new: int, temperature: float,
             seed: int, device: str, seqs_per_batch: int, out_path: Path, done: set, static_cache: bool = False,
             max_batch_tokens: int = 0, kv_cache_gb: float = 3.0, loop: str = "hf", drop_finished: bool = True,
             greedy: bool = False) -> dict:
    import torch  # noqa: PLC0415
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    todo = [it for it in items if (it[0], it[1]["id"]) not in done]
    todo.sort(key=lambda it: len(it[2]))
    per = max(1, seqs_per_batch // k)
    # memory cap: sequences x (longest prompt + max_new) per batch must fit a fixed KV-cache budget in BYTES computed
    # from the model's own shape (a token cap that grew with max_new let a 2,048-token run allocate twice the memory
    # that already failed at 1,024); long prompts and long generations get smaller batches
    cfg = model.config
    head_dim = getattr(cfg, "head_dim", None) or cfg.hidden_size // cfg.num_attention_heads
    kv_per_token = 2 * cfg.num_hidden_layers * getattr(cfg, "num_key_value_heads", cfg.num_attention_heads) * head_dim * \
        next(model.parameters()).element_size()
    budget = int(kv_cache_gb * 2**30 // kv_per_token)
    if max_batch_tokens:
        budget = min(budget, max_batch_tokens)
    chunks, b = [], 0
    while b < len(todo):
        n = 1
        while n < per and b + n < len(todo) and (n + 1) * k * (len(todo[b + n][2]) + max_new) <= budget:
            n += 1
        chunks.append(todo[b:b + n])
        b += n
    t0, n_tok, row_steps = time.time(), 0, 0
    with open(out_path, "a", encoding="utf-8") as f:
        for chunk in chunks:
            L = max(len(p) for _, _, p in chunk)
            ids = torch.full((len(chunk), L), retok.EOS_ID, dtype=torch.long)
            attn = torch.zeros((len(chunk), L), dtype=torch.long)
            for j, (_, _, p) in enumerate(chunk):
                ids[j, L - len(p):] = torch.tensor(p)
                attn[j, L - len(p):] = 1
            # seed per prompt set position: a restart regenerates the same batch from the same seed
            torch.manual_seed(seed * 1_000_003 + int(hashlib.sha256(chunk[0][1]["id"].encode()).hexdigest()[:8], 16))
            with torch.no_grad():
                if loop == "custom":
                    new, _ = decode_loop(model, ids.to(device), attn.to(device), k, max_new, temperature, STOP_IDS,
                                         retok.EOS_ID, greedy=greedy, drop_finished=drop_finished)
                else:
                    # HF greedy search does not accept num_return_sequences > 1: repeat the rows ourselves (same row order)
                    out = model.generate(input_ids=ids.to(device).repeat_interleave(k if greedy else 1, 0),
                                         attention_mask=attn.to(device).repeat_interleave(k if greedy else 1, 0),
                                         do_sample=not greedy,
                                         **({} if greedy else {"temperature": temperature, "top_k": 0, "top_p": 1.0}),
                                         max_new_tokens=max_new, num_return_sequences=1 if greedy else k, eos_token_id=list(STOP_IDS),
                                         pad_token_id=retok.EOS_ID, **({"cache_implementation": "static"} if static_cache else {}))
                    new = out[:, L:].cpu().tolist()
            batch_tok = []
            for j, (set_name, task, p) in enumerate(chunk):
                for s in range(k):
                    g = new[j * k + s]
                    stop = next((i for i, t in enumerate(g) if t in STOP_IDS), None)
                    body = g[: stop + 1] if stop is not None else g
                    rec = make_record(tok, set_name, task, p, body, sample=s)
                    n_tok += rec["gen_tokens"]
                    batch_tok.append(rec["gen_tokens"])
                    f.write(json.dumps(rec) + "\n")
            row_steps += len(batch_tok) * max(batch_tok)  # rows x steps HF `generate` runs (the longest row decides)
            f.flush()
    secs = time.time() - t0
    stats = {"generated_prompts": len(todo), "batches": len(chunks), "kv_budget_tokens": budget, "gen_seconds": round(secs, 1),
             "gen_tokens": n_tok, "gen_tokens_per_s": round(n_tok / max(secs, 1e-9), 1), "loop": loop,
             "drop_finished": drop_finished if loop == "custom" else False,
             "rows_per_batch_mean": round(sum(len(c) for c in chunks) * k / max(len(chunks), 1), 1),
             "useful_token_share_if_no_drop": round(n_tok / max(row_steps, 1), 3)}
    if device.startswith("cuda"):
        stats["peak_gpu_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
    return stats


def make_record(tok, set_name: str, task: dict, prompt_ids: list[int], body: list[int], sample: int) -> dict:
    j = ev.judge(tok, prompt_ids, body)
    g10_text, _ = ev.ids_to_g10(tok, body)
    # what the RL loop scores for an HF tokenizer: tasks.RewardEnvTask.decode = decode(skip_special_tokens=True)
    text = tok.decode(body, skip_special_tokens=True)
    stopped_new_turn = bool(body) and body[-1] == retok.MARKER_MAP["im_start"][1]
    rec = {"set": set_name, "task_id": task["id"], "sample": sample, "gen_tokens": len(body),
           "closed_im_end": j["closed_im_end"], "valid": j["valid"], "format_reason": j["reason"],
           "hit_budget": j["hit_budget"] and not stopped_new_turn, "stopped_new_turn": stopped_new_turn,
           "text": text, "g10_text": g10_text}
    rec.update(code_status(text))
    return rec


def control_records(tok, kind: str, items) -> list[dict]:
    out = []
    for set_name, task, p in items:
        reply = CONSTANT_REPLY if kind == "constant" else task["statement"]
        surr, _ = retok.to_surrogate(reply + T["im_end"])
        body = tok.encode(surr, add_special_tokens=False).ids
        out.append(make_record(tok, set_name, task, p, body, sample=0))
    return out


# ---------------------------------------------------------------- main


def read_jsonl(path: Path) -> list[dict]:
    """One JSON object per '\n'-terminated line. Not str.splitlines(): it also splits on U+2028, U+0085 and other
    separators, which model outputs contain inside JSON strings when they are written with ensure_ascii=False."""
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").split("\n") if x.strip()]


def load_tasks(path: Path, wanted: set[str]) -> dict[str, dict]:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                t = json.loads(line)
                if t["id"] in wanted:
                    out[t["id"]] = t
    missing = wanted - set(out)
    if missing:
        raise SystemExit(f"{len(missing)} ids not in {path}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", help="saved model folder (HF layout)")
    ap.add_argument("--control", choices=("constant", "copy"), help="score a fixed reply instead of a model")
    ap.add_argument("--rescore", action="store_true", help="only re-aggregate (and strict-score) saved generations")
    ap.add_argument("--tokenizer", help="tokenizer.json (default: the model folder's)")
    ap.add_argument("--tasks", type=Path)
    ap.add_argument("--set", action="append", default=[], help="name=ids_file")
    ap.add_argument("--limit", type=int, default=0, help="first N ids of each set (pilots)")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--max-new", type=int, default=1024)
    ap.add_argument("--effort", default="1k")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seqs-per-batch", type=int, default=64)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--max-batch-tokens", type=int, default=0, help="optional extra cap of sequences x (prompt + max_new)")
    ap.add_argument("--kv-cache-gb", type=float, default=3.0,
                    help="KV-cache budget per batch (MPS 16 GB Mac: 3; a 16 GB T4: ~6; A100: 30)")
    ap.add_argument("--static-cache", action="store_true", help="fixed-shape KV cache (faster on MPS: fewer kernel shapes)")
    ap.add_argument("--dtype", default="float32", choices=("float32", "bfloat16", "float16"),
                    help="sampling dtype (float32 everywhere here; bfloat16 only on GPUs that have it, and say so)")
    ap.add_argument("--decode-loop", choices=("hf", "custom"), default="hf",
                    help="hf = model.generate (finished rows keep decoding); custom = decode_loop (finished rows dropped)")
    ap.add_argument("--attn", choices=("sdpa", "gqa_decode"), default="sdpa",
                    help="gqa_decode = grouped one-token decode attention (no K/V repeat); sdpa = the stock path")
    ap.add_argument("--keep-finished", action="store_true", help="custom loop only: do not drop finished rows (isolates the loop)")
    ap.add_argument("--greedy", action="store_true", help="argmax decoding (equality tests only, not a screen)")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--hidden-tests", type=Path, help="private jsonl {id, tests} of unused source tests")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    gens = a.out / "generations.jsonl"
    meta_path = a.out / "screen_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if not a.rescore:
        meta["sandbox_preflight"] = sandbox_preflight(a.workers)
        sets = [(s.split("=", 1)[0], Path(s.split("=", 1)[1])) for s in a.set]
        ids = {name: p.read_text().split() for name, p in sets}
        if a.limit:
            ids = {k_: v[: a.limit] for k_, v in ids.items()}
        tasks = load_tasks(a.tasks, {i for v in ids.values() for i in v})
        from tokenizers import Tokenizer  # noqa: PLC0415
        tok_path = Path(a.tokenizer) if a.tokenizer else Path(a.model) / "tokenizer.json"
        tok = Tokenizer.from_file(str(tok_path))
        retok.check_tokenizer(tok)
        items = []
        rej_all = {}
        for name, v in ids.items():
            enc, rej = encode_prompts(tok, [tasks[i] for i in v], a.effort)
            rej_all[name] = rej
            items += [(name, t, p) for t, p in enc]
        meta.update({"sets": {n: {"ids_file": str(p), "ids_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                  "used": len(ids[n]), "rejected_prompts": rej_all[n]} for n, p in sets},
                     "tasks_sha256": hashlib.sha256(a.tasks.read_bytes()).hexdigest(), "k": a.k, "effort": a.effort,
                     "tokenizer_sha256": hashlib.sha256(tok_path.read_bytes()).hexdigest()})
        if a.control:
            recs = control_records(tok, a.control, items)
            gens.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
            meta.update({"control": a.control, "k_note": "a fixed reply: every sample is identical, so k = 1 is scored "
                         "and a mixed group is impossible by construction"})
            meta["k"] = 1
        else:
            import torch  # noqa: PLC0415
            from transformers import AutoModelForCausalLM  # noqa: PLC0415
            done = set()
            if gens.exists():
                for r in read_jsonl(gens):
                    done.add((r["set"], r["task_id"]))
            attn_kw = {"attn_implementation": register_gqa_decode_attention()} if a.attn == "gqa_decode" else {}
            model = AutoModelForCausalLM.from_pretrained(a.model, dtype=getattr(torch, a.dtype), **attn_kw).to(a.device).eval()
            gstats = generate(model, tok, items, a.k, a.max_new, a.temperature, a.seed, a.device, a.seqs_per_batch,
                              gens, done, a.static_cache, a.max_batch_tokens, a.kv_cache_gb,
                              a.decode_loop, not a.keep_finished, a.greedy)
            meta.update({"model": a.model, "max_new": a.max_new, "static_cache": a.static_cache, "attn": a.attn, "temperature": a.temperature, "top_k": 0, "top_p": 1.0,
                         "seed": a.seed, "device": a.device, "dtype": a.dtype,
                         "model_sha256": hashlib.sha256((Path(a.model) / "model.safetensors").read_bytes()).hexdigest()
                         if (Path(a.model) / "model.safetensors").exists() else None})
            meta.setdefault("generation_runs", []).append(gstats)
            del model
        records = read_jsonl(gens)
        meta["scoring"] = score_records(records, tasks, a.workers)
        gens.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    else:
        records = read_jsonl(gens)
        tasks = load_tasks(Path(meta["tasks_path"]) if "tasks_path" in meta else a.tasks, {r["task_id"] for r in records})
    if not a.rescore:
        meta["tasks_path"] = str(a.tasks)
    if a.hidden_tests:
        hidden = {}
        for h in read_jsonl(a.hidden_tests):
            hidden[h["id"]] = h["tests"]
        meta["strict"] = strict_rescore(records, tasks, hidden, a.workers)
        meta["strict"]["hidden_tests_sha256"] = hashlib.sha256(a.hidden_tests.read_bytes()).hexdigest()
        gens.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    report = {"schema": "g10-rl-screen/1", "meta": meta, "sets": {}}
    for name in sorted({r["set"] for r in records}):
        report["sets"][name] = aggregate([r for r in records if r["set"] == name], int(meta.get("k", a.k)), a.n_boot)
    meta_path.write_text(json.dumps(meta, indent=1))
    (a.out / "screen_report.json").write_text(json.dumps(report, indent=1))
    brief = {n: {"ladder": {k_: v["share"] for k_, v in s["ladder"].items()},
                 "mixed_kept": s.get("groups_pass_kept", {}).get("mixed_share"), "outcomes": s["outcomes"],
                 "truncated": s["truncated_share"]} for n, s in report["sets"].items()}
    print(json.dumps(brief, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
