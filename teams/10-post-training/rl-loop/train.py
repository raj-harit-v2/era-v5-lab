"""RL loop v0: group-relative policy optimisation with a frozen MoE router.

    python teams/10-post-training/rl-loop/train.py --config teams/10-post-training/rl-loop/config/smoke_tiny_olmoe.yaml

One step: take `prompts_per_step` training prompts, sample `k` completions for each, score them, drop groups whose
rewards are all equal, and take `ppo_epochs` optimiser steps on the clipped surrogate of the chosen algorithm (grpo,
dr_grpo, rloo or gspo; see grpo.py). `algo: objective_v1` instead uses the lead's Session 18 objective
(rl/objective_v1.md): centred rewards, dropped tied groups, plain -A*log pi with a closed trust-region mask on the
ratio to the sampling policy, one batch-global token denominator; it has no clipping, IS weight or reference KL.
Every `eval_every` steps the held-out prompts are scored (that is the number Gate 4 should be judged on, not the training reward). The router is frozen before training and its checksum must
be identical at the end; the run fails otherwise.

Writes to `out_dir` (default ./out, the TSAI job rule): metrics.jsonl (one line per step), summary.json.

Model kinds (config `model.kind`):
    tiny_olmoe   a random tiny OLMoE from a config (no download); for smoke tests on a laptop
    hf           AutoModelForCausalLM.from_pretrained(model.path), e.g. a local copy of allenai/OLMoE-1B-7B-0125-Instruct
    team5        Team 5's harness LanguageModel (teams/05-architecture/harness/week2/model.py), built with their own
                 config loader from model.arm + model.resolution, plus model.overrides; the KE2 code table is a
                 seeded stand-in until Team 5 ships the real model on 18 Nov (smoke only)
    team5_adapter  Team 5's real checkpoint through team5_adapter.py (model.adapter_config): pinned G5 code,
                 strict checkpoint/KE2/tokenizer checks, G10 chat codec, router and trainable sets from the adapter.
                 Exits 3 with out_dir/status.json = WAITING_FOR_G5_ARTIFACT until the checkpoint exists. A fixture
                 adapter config needs model.allow_fixture_smoke: true and writes smoke_summary.json, never summary.json.
                 model.kv_cache: true samples through rl-loop/g5_decode.py (KV cache built from G5's own modules).
Task kinds (config `task.kind`): toy (see tasks.py), code_tasks (rl/tasks via rl/reward.py; needs an hf tokenizer).

GPU-run options (config `train.*`, all optional):
    sampler        policy | g5_batch | hf_batch | vllm (rollout.py). Default hf_batch for HF models, policy otherwise.
                   g5_batch (G5 only): every prompt of a step in one KV-cached decode; sampler_max_rows (default 128)
                   caps the rows decoded together.
    vllm           kwargs for the colocated engine, e.g. {gpu_memory_utilization: 0.3, max_model_len: 2048}
    fp32_master    default true: trainable weights in fp32 under bf16 autocast (policy.use_fp32_master)
    autocast       bf16 | unset (default): force bf16 autocast for the policy's forward. Needed for a G5 checkpoint,
                   which is stored in fp32 (fp32_master then converts nothing and the run would be all-fp32)
    tis_clip       truncated importance sampling for the vLLM/trainer gap (grpo.tis_weights), e.g. 2.0
    routing_log    expert load and top-k flip rates (routing.py); routing_probe = held-out prompts in the probe
    kl_to_start    K3 KL(current || step 0) on held-out completions at every eval
    tr_epsilon     objective_v1 only: trust-region half-width, default 0.2 (kl_coef and tis_clip must be unset)
    fail_on_lost_update  objective_v1 only, default true: raise when, of the probed trainable entries that had a
                   nonzero gradient, fewer than min_stored_update_ratio (default 0.5) changed in storage after the
                   optimizer step (a small update rounded away in bf16); false = warn and log only
    update_mode    train (default, unchanged) | eval: old_lp and the update forward run in eval mode, the samplers' mode,
                   so a train-only layer (an output head's vocabulary dropout) cannot put noise into the ratio. Not with dt
    logprob_gate   opt-in (true, or {mean_abs_tol: 0.01, outside_frac_tol: 0.005, eps, prompts: 1, max_new: 256}):
                   before the screen and the first update, sample k completions of the first train prompt(s) with an own
                   generator, score them as the update will and compare with the behaviour log-probs at identical
                   weights; stop with an error above the tolerance; logprob_gate.json and summary["logprob_gate"]. Not with dt
metrics.jsonl adds per-step timings (rollout, reward, old_logprobs, train, sync), sampled tokens and tokens/s,
GPU memory, and the sampler/trainer mismatch. summary.json adds the paired-bootstrap CI of the held-out change,
the trainable-weight change, and the library versions.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import os
import random
import threading
import re
import sys
import time
from pathlib import Path

import torch
import yaml
from torch import no_grad  # decorator without a dot: pr-guard reads '+@a.b' as an email

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grpo  # noqa: E402
import heldout  # noqa: E402
import rollout  # noqa: E402
import router  # noqa: E402
import routing  # noqa: E402
import tasks  # noqa: E402
from policy import HFPolicy, completion_logprobs, hf_policy, module_policy, use_fp32_master  # noqa: E402

TEAM5_HARNESS = HERE.parents[1] / "05-architecture" / "harness"


# --- building the model and the task --------------------------------------------------------------

def build_model(mcfg: dict, device: str):
    kind = mcfg["kind"]
    if kind == "tiny_olmoe":
        from transformers import OlmoeConfig, OlmoeForCausalLM  # noqa: PLC0415
        cfg = OlmoeConfig(eos_token_id=None, bos_token_id=None, pad_token_id=None, **mcfg["config"])
        return hf_policy(OlmoeForCausalLM(cfg), None, device), None
    if kind == "hf":
        from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415
        dtype = getattr(torch, mcfg.get("dtype", "float32"))
        model = AutoModelForCausalLM.from_pretrained(mcfg["path"], dtype=dtype, local_files_only=True)
        try:
            tok = AutoTokenizer.from_pretrained(mcfg["path"], local_files_only=True)
        except (OSError, ValueError):
            tok = None  # the toy task needs no tokenizer
        if mcfg.get("gradient_checkpointing"):
            model.gradient_checkpointing_enable()
        eos = tok.eos_token_id if tok is not None and mcfg.get("stop_at_eos", True) else None
        return hf_policy(model, eos, device), tok
    if kind == "team5":
        import numpy as np  # noqa: PLC0415
        sys.path.insert(0, str(TEAM5_HARNESS))
        from week2.config import load, load_runtime, merge  # noqa: PLC0415
        from week2.model import LanguageModel  # noqa: PLC0415
        team5 = TEAM5_HARNESS.parent
        spec = merge(load_runtime(team5 / mcfg["arm"]), load(team5 / mcfg["resolution"]))["model"]
        moe = mcfg.get("overrides", {}).pop("moe", {}) if mcfg.get("overrides") else {}
        spec.update(mcfg.get("overrides", {}))
        spec["moe"].update(moe)
        rng = np.random.default_rng(mcfg.get("ke2_seed", 7))  # stand-in KE2 code table until Team 5's model lands
        rows = rng.integers(0, 256, (spec["vocab_size"], 4), dtype=np.uint8)
        lengths = rng.integers(1, 5, spec["vocab_size"], dtype=np.int16)
        return module_policy(LanguageModel(spec, rows, lengths), None, device), None
    if kind == "team5_adapter":
        import team5_adapter  # noqa: PLC0415
        return team5_adapter.build_policy_and_codec(mcfg["adapter_config"], device, mcfg.get("effort", "4k"),
                                                    bool(mcfg.get("allow_fixture_smoke", False)),
                                                    bool(mcfg.get("kv_cache", False)))
    raise ValueError(f"unknown model.kind {kind!r}")


def build_task(tcfg: dict, tokenizer, seed: int, pool=None):
    if tcfg["kind"] == "toy":
        # task.seed pins the prompts independently of the run seed (same held-out prompts for every run of a comparison)
        return tasks.ToyTask(**{k: v for k, v in tcfg.items() if k not in ("kind", "seed")}, seed=tcfg.get("seed", seed))
    if tcfg["kind"] == "code_tasks":
        if tokenizer is None:
            raise ValueError("code_tasks needs model.kind hf (a tokenizer)")
        return tasks.RewardEnvTask(tokenizer, tasks.code_task_prompts(tcfg["train"]),
                                   tasks.code_task_prompts(tcfg["heldout"]))
    if tcfg["kind"] == "math":
        return math_task(tcfg, tokenizer)
    if tcfg["kind"] == "stdio":
        return stdio_task(tcfg, tokenizer, pool)
    raise ValueError(f"unknown task.kind {tcfg['kind']!r}")


def math_task(tcfg: dict, tokenizer):
    """MATH-style tasks (rl-data/build_math.py records) scored by rl-data/math_check.py.

    task: {kind: math, tasks: <jsonl>, train_ids: <file>, heldout_ids: <file>, instruction_file: <file or null>}
    The instruction file is written by a team member (TSAI 3 Nov rule) and holds the user message with {problem};
    without it the raw problem text is the prompt.
    """
    import importlib.util  # noqa: PLC0415
    if tokenizer is None:
        raise ValueError("math tasks need model.kind hf (a tokenizer)")
    spec = importlib.util.spec_from_file_location("g10_math_check", HERE.parent / "rl-data" / "math_check.py")
    mc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mc)
    by_id = {}
    for line in Path(tcfg["tasks"]).read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            by_id[t["id"]] = t
    instr = Path(tcfg["instruction_file"]).read_text(encoding="utf-8") if tcfg.get("instruction_file") else None
    if instr is not None and "{problem}" not in instr:
        raise ValueError("instruction_file needs a {problem} placeholder")

    def items(ids_file):
        ids = [x.strip() for x in Path(ids_file).read_text(encoding="utf-8").splitlines() if x.strip()]
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise ValueError(f"{len(missing)} ids not in {tcfg['tasks']}, e.g. {missing[:3]}")
        return [(i, instr.replace("{problem}", by_id[i]["problem"]) if instr else by_id[i]["problem"]) for i in ids]

    def reward_fn(env_id: str, text: str):
        r = mc.score(by_id[env_id], text)
        return float(r["reward"]), r

    return tasks.RewardEnvTask(tokenizer, items(tcfg["train_ids"]), items(tcfg["heldout_ids"]), reward_fn)


def stdio_task(tcfg: dict, tokenizer, pool=None):
    """stdin/stdout program tasks (rl-data/build.py records, e.g. RL data v1 code_contests) scored by
    rl-data/stdio_check.py (Docker, or G10_STDIO_RUNNER=local where Docker is absent, e.g. Modal).

    task: {kind: stdio, tasks: <jsonl>, train_ids: <file>, heldout_ids: <file>}
    require_verifier runs known-answer checks and treats runner failures as errors for the job.
    The prompt is the record's human-written statement as the user message. No instruction text is added: the team
    has not written one, and assistant-written text may not become RL prompts (TSAI 3 Nov rule).
    """
    import importlib.util  # noqa: PLC0415
    if tokenizer is None:
        raise ValueError("stdio tasks need model.kind hf (a tokenizer)")
    spec = importlib.util.spec_from_file_location("g10_stdio_check", HERE.parent / "rl-data" / "stdio_check.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    by_id = {}
    for line in Path(tcfg["tasks"]).read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            by_id[t["id"]] = t

    def items(ids_file):
        ids = [x.strip() for x in Path(ids_file).read_text(encoding="utf-8").splitlines() if x.strip()]
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise ValueError(f"{len(missing)} ids not in {tcfg['tasks']}")
        return [(i, by_id[i]["statement"]) for i in ids]

    reasons, lock = collections.Counter(), threading.Lock()
    require_verifier = bool(tcfg.get("require_verifier", False))

    def score_stdio(samples):
        results = pool.score(samples) if pool is not None else [sc.score(record, text) for record, text in samples]
        buckets = [reason_bucket(result) for result in results]
        if require_verifier:
            for result, bucket in zip(results, buckets):
                # "timeout on a test" is a candidate timeout; "timeout" is the outer runner deadline.
                if bucket == "runner_failure" or result.get("reason") == "timeout":
                    raise RuntimeError(f"stdio verifier runner failed: {result.get('reason', 'unknown reason')}")
        return results, buckets

    if require_verifier:
        probe = {"id": "stdio-preflight", "tests": [{"input": "7\n", "output": "8\n"}]}
        correct = "```python\nprint(int(input()) + 1)\n```"
        wrong = "```python\nprint(int(input()) - 1)\n```"
        _, buckets = score_stdio([(probe, correct), (probe, wrong)])
        if buckets != ["pass", "wrong_answer"]:
            raise RuntimeError(f"stdio verifier preflight expected a pass and a wrong answer, got {buckets}")

    def reward_fn(env_id: str, text: str):
        results, buckets = score_stdio([(by_id[env_id], text)])
        with lock:
            reasons.update(buckets)
        return float(results[0]["reward"]), results[0]

    task = tasks.RewardEnvTask(tokenizer, items(tcfg["train_ids"]), items(tcfg["heldout_ids"]), reward_fn)
    task.reason_counts, task.reason_lock = reasons, lock
    sub_key = tcfg.get("subgroup_key", "judge")  # observer: which slice of the input mixture a prompt belongs to
    task.subgroup_of = lambda prompt: str(by_id[task._items[tuple(prompt)]].get(sub_key, "unknown"))
    if pool is not None:  # score in the small worker processes (score_pool.py), same score() and same order
        def batch_reward(pairs):
            res, buckets = score_stdio([(by_id[task._items[tuple(p)]], task.decode(c)) for p, c in pairs])
            with lock:
                reasons.update(buckets)
            return [float(r["reward"]) for r in res]
        task.batch_reward = batch_reward
    return task


def reason_bucket(r: dict) -> str:
    """Why a completion scored what it did: separates format failures from wrong programs (observer metric)."""
    if r.get("reward") == 1:
        return "pass"
    why = str(r.get("reason", ""))
    if why.startswith("wrong answer"):
        return "wrong_answer"
    if why.startswith("timeout"):
        return "timeout"
    if why.startswith("error on a test"):
        return "runtime_error"
    if "total" not in r and not why.startswith(("runner", "no readable", "output file")):
        return "no_code"  # extract_code found no program in the completion
    return "runner_failure"


def pop_reasons(task) -> dict | None:
    """Counts since the last call (one scoring phase), or None for tasks that do not record reasons."""
    counts = getattr(task, "reason_counts", None)
    if counts is None:
        return None
    with task.reason_lock:
        out = dict(sorted(counts.items()))
        counts.clear()
    return out


def prompt_order_sha256(task, prompts: list[list[int]]) -> str:
    """Identify a score vector's ordered prompt tokens and environment IDs without logging either."""
    env_ids = getattr(task, "_items", {})
    ordered = [(env_ids.get(tuple(tokens)), tokens) for tokens in prompts]
    return hashlib.sha256(json.dumps(ordered, separators=(",", ":")).encode()).hexdigest()


# --- durable state ---------------------------------------------------------------------------------
# A run with train.state_dir keeps everything needed to continue after a kill: fp32 trainable weights, optimizer
# moments, every random stream, the screened cohort and the step. Files are written to a temporary name and renamed,
# then LATEST.json is replaced the same way; the previous state file is kept until the next one is complete.
# Evaluations and step metrics are append-only files, so a result exists on disk as soon as it is measured.

STATE_VERSION = 1


def _file_or_value(v):
    if isinstance(v, str) and os.path.isfile(v):
        return "sha256:" + hashlib.sha256(Path(v).read_bytes()).hexdigest()
    return v


def state_identity(cfg: dict, trainable_named, *, init_state_sha256: str | None = None,
                   keep_zero_identity: dict | None = None) -> dict:
    """What must match for a saved state to be continued. `steps`, deadlines and paths may differ between calls."""
    t = cfg["train"]
    keys = ("algo", "k", "max_new", "temperature", "lr", "prompts_per_step", "ppo_epochs", "trainable", "tr_epsilon",
            "micro_rows", "weight_decay", "fp32_master", "sampler", "clip_eps", "kl_coef", "grad_clip", "screen")
    if t.get("autocast") is not None:  # preserve identities of runs saved before this option existed
        keys += ("autocast",)
    if t.get("sampler_max_rows") is not None:  # chunking changes which random draws each row gets
        keys += ("sampler_max_rows",)
    if t.get("dt"):  # only present for Deletion Tuning runs, so states saved before train.dt existed stay valid
        keys += ("dt",)
    if t.get("update_mode", "train") != "train":  # default runs keep the identities they had
        keys += ("update_mode",)
    model = {k_: cfg["model"].get(k_) for k_ in ("kind", "path", "dtype", "config")}
    if init_state_sha256 is not None:
        model["init_state_sha256"] = init_state_sha256
    train = {k_: t.get(k_) for k_ in keys}
    if keep_zero_identity is not None:
        train["keep_zero"] = keep_zero_identity
    names = "\n".join(f"{n}:{tuple(p_.shape)}" for n, p_ in trainable_named)
    return {"version": STATE_VERSION, "seed": int(cfg.get("seed", 1234)), "model": model,
            "task": {k_: _file_or_value(v) for k_, v in sorted(cfg["task"].items())},
            "train": train,
            "trainable_sha256": hashlib.sha256(names.encode()).hexdigest()}


def save_state(state_dir: Path, step: int, payload: dict, keep: int = 2) -> dict:
    state_dir.mkdir(parents=True, exist_ok=True)
    name = f"state.step{step:06d}.pt"
    tmp = state_dir / (name + ".tmp")
    c0 = time.time()
    torch.save(payload, tmp)
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, state_dir / name)
    rec = {"step": step, "file": name, "bytes": (state_dir / name).stat().st_size,
           "identity_sha256": hashlib.sha256(json.dumps(payload["identity"], sort_keys=True).encode()).hexdigest(),
           "saved_unix": time.time(), "write_s": round(time.time() - c0, 2)}
    latest_tmp = state_dir / "LATEST.json.tmp"
    latest_tmp.write_text(json.dumps(rec))
    os.replace(latest_tmp, state_dir / "LATEST.json")
    for old in sorted(state_dir.glob("state.step*.pt"))[:-keep]:
        old.unlink()
    return rec


def load_state(state_dir: Path, identity: dict) -> dict | None:
    """The newest complete state, or None when there is none. A state from a different run is an error, not a
    silent restart: continuing someone else's weights or cohort would be worse than stopping."""
    latest = state_dir / "LATEST.json"
    if not latest.exists():
        return None
    rec = json.loads(latest.read_text())
    files = [state_dir / rec["file"]] + sorted((f for f in state_dir.glob("state.step*.pt")
                                               if f.name != rec["file"]), reverse=True)
    for i, f in enumerate(files):
        if not f.exists() or (i == 0 and f.stat().st_size != rec["bytes"]):
            continue
        try:
            payload = torch.load(f, map_location="cpu", weights_only=False)
        except Exception as e:  # noqa: BLE001  (a torn file: try the previous one)
            print(json.dumps({"state_unreadable": f.name, "error": repr(e)[:200]}), flush=True)
            continue
        if payload["identity"] != identity:
            diff = sorted(k_ for k_ in set(payload["identity"]) | set(identity)
                          if payload["identity"].get(k_) != identity.get(k_))
            raise RuntimeError(f"{f} belongs to a different run (differs in {diff}); refusing to continue it")
        payload["_file"] = f.name
        return payload
    raise RuntimeError(f"{state_dir} has LATEST.json but no readable state file")


def read_jsonl(path: Path, max_step: int | None = None) -> list[dict]:
    """Rows of an append-only file. With max_step, rows from steps after the restored state are dropped and the file
    is rewritten (those steps will be redone, so their old rows must not be counted twice)."""
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if max_step is not None:
        kept = [r for r in rows if r["step"] <= max_step]
        if len(kept) != len(rows):
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text("".join(json.dumps(r) + "\n" for r in kept))
            os.replace(tmp, path)
        rows = kept
    return rows


def append_jsonl(path: Path, rec: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_dt():
    """teams/10-post-training/dt/mask.py (the Deletion Tuning port), loaded by path."""
    import importlib.util  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location("g10_dt_mask", HERE.parent / "dt" / "mask.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dt_hard_weights(dtmask, model) -> list[tuple[str, torch.Tensor]]:
    """What a Deletion Tuning policy samples with: W * 1[G > 0] for every masked layer, under its Hugging Face
    weight name. The sampler must hold these, never the soft-masked training weights."""
    return [(f"{name}.weight", m.base_weight * (m.gate > 0).to(m.base_weight.dtype))
            for name, m in dtmask.masked_layers(model)]


def score_completions(task, pairs: list[tuple[list[int], list[int]]], workers: int = 1) -> list[float]:
    """task.reward over (prompt, completion) pairs, in order. workers > 1 scores in threads (the stdio checker runs
    each program in a subprocess, so threads overlap); workers == 1 is the original sequential loop."""
    if getattr(task, "batch_reward", None) is not None:
        return task.batch_reward(pairs)
    if workers <= 1:
        return [task.reward(p, c) for p, c in pairs]
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda pc: task.reward(*pc), pairs))


def set_trainable(model, patterns: list[str] | None) -> int:
    """If patterns are given, train only matching parameters (e.g. attention); the router stays frozen regardless."""
    if patterns:
        rx = [re.compile(p) for p in patterns]
        for n, p in model.named_parameters():
            p.requires_grad_(any(r.search(n) for r in rx))
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# --- evaluation and training ----------------------------------------------------------------------

def evaluate(sampler, task, prompts, k: int, max_new: int, temperature: float, gen, workers: int = 1):
    """Per-problem pass@1 (mean reward over k samples) and the rollouts (reused as the routing probe)."""
    rolls = sampler.sample(prompts, k, max_new, temperature, gen)
    pairs = [(p, row[m].tolist()) for p, r in zip(prompts, rolls) for row, m in zip(r.seq[:, len(p):], r.cmask)]
    flat = score_completions(task, pairs, workers)
    per_problem, i = [], 0
    for r in rolls:
        n = r.seq.shape[0]
        per_problem.append(sum(flat[i:i + n]) / n)
        i += n
    return per_problem, rolls


def length_stats(rolls, max_new: int, eos_id) -> dict:
    """Share of completions that hit the token cap without ending (a cut answer scores 0), and mean length."""
    n = cut = toks = 0
    for r in rolls:
        lens = r.cmask.sum(1)
        last = r.seq[torch.arange(r.seq.shape[0]), r.seq.shape[1] - r.cmask.shape[1] + lens.clamp_min(1) - 1]
        hit = lens == max_new
        if eos_id is not None:
            hit = hit & (last != eos_id)
        cut += int(hit.sum())
        toks += int(lens.sum())
        n += lens.numel()
    return {"truncated": round(cut / max(n, 1), 4), "mean_tokens": round(toks / max(n, 1), 1)}


def gpu_memory() -> dict:
    if not torch.cuda.is_available():
        return {}
    free, total = torch.cuda.mem_get_info()
    return {"peak_torch_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
            "gpu_used_gb": round((total - free) / 2**30, 2), "gpu_total_gb": round(total / 2**30, 2)}


def versions() -> dict:
    out = {"torch": torch.__version__}
    for mod in ("transformers", "vllm"):
        try:
            out[mod] = __import__(mod).__version__
        except ImportError:
            out[mod] = None
    return out


class StartWeights:
    """The trainable weights at step 0, kept on the CPU, for the KL-to-start metric (cheaper than a second model)."""

    def __init__(self, model):
        self.params = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
        self.saved = [p.detach().to("cpu", copy=True) for _, p in self.params]

    @torch.no_grad()
    def change(self) -> dict:
        """How far the trainable weights moved: share of entries that changed, and ||w - w0|| / ||w0||."""
        changed = total = 0
        diff_sq = base_sq = 0.0
        for (_, p), s in zip(self.params, self.saved):
            w = p.detach().to("cpu", torch.float32)
            s32 = s.to(torch.float32)
            changed += int((w != s32).sum())
            total += w.numel()
            diff_sq += float((w - s32).pow(2).sum())
            base_sq += float(s32.pow(2).sum())
        return {"share_changed": changed / max(total, 1), "relative_l2": (diff_sq ** 0.5) / max(base_sq ** 0.5, 1e-30)}

    @torch.no_grad()
    def swap(self):
        for (_, p), s in zip(self.params, self.saved):
            tmp = p.detach().to("cpu", copy=True)
            p.copy_(s.to(p.device))
            s.copy_(tmp)


@no_grad()
def kl_to_start(policy, start: StartWeights, rolls, prompts) -> float:
    """K3 estimate of KL(current || start) per completion token, on completions sampled from the current policy."""
    cur = [completion_logprobs(policy, r.seq, len(p)) for p, r in zip(prompts, rolls)]
    start.swap()
    try:
        ref = [completion_logprobs(policy, r.seq, len(p)) for p, r in zip(prompts, rolls)]
    finally:
        start.swap()
    num = den = 0.0
    for c, f, r in zip(cur, ref, rolls):
        m = r.cmask.float()
        d = (f - c) * m
        num += float(((torch.exp(d) - d - 1) * m).sum())
        den += float(m.sum())
    return num / max(den, 1.0)


def chunked_logprobs(policy, seq: torch.Tensor, plen: int, micro_rows: int | None) -> torch.Tensor:
    """completion_logprobs over row chunks: the [rows, T, vocab] fp32 logits are the memory peak (C1/C2 ran out of
    memory on an 80 GB H100 at step 84 with 8 rows x ~1,500 tokens x 50,304 vocab)."""
    if not micro_rows or micro_rows >= seq.shape[0]:
        return completion_logprobs(policy, seq, plen)
    return torch.cat([completion_logprobs(policy, seq[i:i + micro_rows], plen)
                      for i in range(0, seq.shape[0], micro_rows)], 0)


UPDATE_MODES = ("train", "eval")
GATE_MEAN_ABS_TOL = 0.01      # nats; work/lpgate-2026-11-23/PREREG.md (fixed before any run)
GATE_OUTSIDE_FRAC_TOL = 0.005  # share of real tokens whose equal-weights ratio leaves [1 - eps, 1 + eps]


def update_forward_mode(model, update_mode: str) -> None:
    """Module mode of the forwards that feed the ratio. "train" (default) is the trainer's historical behaviour: the update
    runs after model.train(), and old_lp in whatever mode the model is in (eval at step 1, train mode after). "eval" runs
    old_lp and the update in eval mode, the mode every sampler here uses, so train-only layers (dropout, e.g. an output
    head's vocabulary dropout) cannot put noise into ratio = exp(new_lp - old_lp). Gradients flow the same in eval mode."""
    model.train(update_mode == "train")


def logprob_gate(policy, model, items, update_mode: str, eps: float, micro_rows: int | None,
                 mean_abs_tol: float = GATE_MEAN_ABS_TOL, outside_frac_tol: float = GATE_OUTSIDE_FRAC_TOL) -> dict:
    """Identical-weights check before the first update: score sampled tokens with the training forward exactly as the
    update will (module mode `update_mode`, same autocast, same row chunks) and compare with the behaviour policy.

    items: (seq [k, P+T], cmask [k, T], plen, behaviour_lp [k, T] or None). The behaviour log-probs are the sampler's
    own (vLLM rollout_lp) when it reports them; otherwise the eval-mode full forward under the same autocast, i.e. the
    sampler's mode and dtype without its KV cache (the cache's own gap is measured offline, work/lpgate-2026-11-23).
    One extra forward when the reference is given; two when it is not. One host sync. Never changes the weights."""
    was = model.training
    gaps, refs = [], []
    with torch.no_grad():
        for seq, cmask, plen, ref in items:
            if ref is None:
                model.eval()
                ref = chunked_logprobs(policy, seq, plen, micro_rows)
                refs.append("eval_forward")
            else:
                refs.append("rollout_lp")
            update_forward_mode(model, update_mode)
            cur = chunked_logprobs(policy, seq, plen, micro_rows)
            gaps.append((cur.double() - ref.double())[cmask])
    model.train(was)
    d = torch.cat(gaps) if gaps else torch.zeros(0, dtype=torch.float64)
    n = int(d.numel())
    if n == 0:
        return {"ok": True, "tokens": 0, "note": "no real tokens"}
    a = d.abs()
    r = torch.exp(d)
    vals = torch.stack([a.max(), a.mean(), ((r < 1 - eps) | (r > 1 + eps)).double().mean(),
                        torch.isfinite(d).all().double()]).tolist()  # one host sync
    rec = {"tokens": n, "max_abs": float(f"{vals[0]:.4g}"), "mean_abs": float(f"{vals[1]:.4g}"),
           "outside_frac": round(vals[2], 6), "finite": bool(vals[3]), "eps": eps, "update_mode": update_mode,
           "reference": sorted(set(refs)), "mean_abs_tol": mean_abs_tol, "outside_frac_tol": outside_frac_tol}
    rec["ok"] = rec["finite"] and vals[1] <= mean_abs_tol and vals[2] <= outside_frac_tol
    return rec


def backward_group(policy, group, algo: str, clip_eps: float, kl_coef: float, n_groups: int,
                   micro_rows: int | None) -> tuple[float, dict]:
    """Loss and backward for one group, optionally in row chunks. Every loss in grpo.py is a mean over the group's
    rows (grpo, gspo) or a sum divided by rows x T (dr_grpo, rloo), so a chunk's loss times rows_in_chunk / k is
    its exact share, and the summed gradients equal the one-shot gradient.

    The reference KL (kl_coef > 0) is the group-global token mean: the k3 term of grpo.policy_loss summed over each
    chunk's valid tokens and divided by the valid-token count of the whole group, so every chunking gives the same
    value as the unchunked group. (Before 11 Nov it was normalised per chunk and weighted by row share, which is
    wrong for uneven completion lengths.) With kl_coef == 0 this function computes exactly what it did before."""
    seq, cmask, adv, old_lp, ref_lp, plen, isw = group
    k = seq.shape[0]
    step = micro_rows if micro_rows and micro_rows < k else k
    use_kl = ref_lp is not None and kl_coef > 0
    n_valid = float(cmask.float().sum().clamp_min(1))  # group-global KL denominator
    total, agg = 0.0, {"clip_frac": 0.0, "ratio_mean": 0.0, "kl": 0.0}
    for i in range(0, k, step):
        sl = slice(i, min(i + step, k))
        rows = sl.stop - sl.start
        new_lp = completion_logprobs(policy, seq[sl], plen)
        loss, st = grpo.policy_loss(new_lp, old_lp[sl], adv[sl], cmask[sl], algo, clip_eps, None, 0.0,
                                    None if isw is None else isw[sl])
        share = rows / k
        obj = loss * share
        if use_kl:
            m = cmask[sl].float()
            d = (ref_lp[sl] - new_lp) * m
            kl_part = ((torch.exp(d) - d - 1) * m).sum() / n_valid  # same k3 as grpo.policy_loss
            obj = obj + kl_coef * kl_part
            agg["kl"] += float(kl_part.detach())
        (obj / n_groups).backward()
        total += float(loss.detach()) * share / n_groups
        if use_kl:
            total += kl_coef * float(kl_part.detach()) / n_groups
        for key in ("clip_frac", "ratio_mean"):
            agg[key] += st[key] * share
    return total, agg


def backward_objective_v1(policy, group, eps: float, n_tokens: int, micro_rows: int | None):
    """Loss and backward for one kept group under objective_v1, optionally in row chunks.

    group = (seq, cmask, adv, sampler_lp, None, plen, None); sampler_lp is the log-probability of each sampled token
    under the policy that sampled it (vLLM's rollout_lp when present, else the trainer's pre-update old_lp).
    n_tokens is the real-token count of ALL kept groups in the step, so each chunk's numerator / n_tokens is its exact
    share of the batch loss and any chunking (or grouping) sums to the same gradient. Returns device tensors only."""
    seq, cmask, adv, sampler_lp, hard_lp, plen, _ = group
    k = seq.shape[0]
    step = micro_rows if micro_rows and micro_rows < k else k
    total, agg = None, {}
    for i in range(0, k, step):
        sl = slice(i, min(i + step, k))
        new_lp = completion_logprobs(policy, seq[sl], plen)
        num, st = grpo.objective_v1_terms(new_lp, sampler_lp[sl], adv[sl], cmask[sl], eps)
        if hard_lp is not None:  # Deletion Tuning: the trainer's soft-mask policy vs the same weights hard-masked
            st = {**st, **soft_hard_terms(new_lp.detach(), hard_lp[sl], cmask[sl], eps)}
        part = num / n_tokens
        part.backward()
        total = part.detach() if total is None else total + part.detach()
        for key, v in st.items():
            agg[key] = v if key not in agg else agg[key] + v
    return total, agg


SOFT_HARD_KEYS = ("sh_k3_sum", "sh_abs_sum", "sh_outside")


def soft_hard_terms(soft_lp: torch.Tensor, hard_lp: torch.Tensor, cmask: torch.Tensor, eps: float) -> dict:
    """Soft/hard mask gap on the real tokens, same engine (HF), same weights, same tokens: r = log pi_soft - log
    pi_hard. Sums (device tensors, no host sync) of K3 = exp(r) - 1 - r and |r|, and the count of tokens whose
    soft/hard ratio alone falls outside [1 - eps, 1 + eps], i.e. tokens the trust-region mask would drop from the
    mask gap even with a perfect sampler. Callers divide by the real-token count."""
    m = cmask.bool()
    r = torch.where(m, soft_lp - hard_lp, torch.zeros_like(soft_lp))
    ratio = torch.exp(r)
    return {"sh_k3_sum": torch.where(m, ratio - 1 - r, torch.zeros_like(r)).sum(dtype=torch.float64),
            "sh_abs_sum": r.abs().sum(dtype=torch.float64),
            "sh_outside": (m & ((ratio < 1 - eps) | (ratio > 1 + eps))).sum()}


class UpdateProbe:
    """Did the optimizer step change the STORED trainable weights? Samples up to n entries of every trainable tensor
    (strided, fixed positions), snapshots them and their gradients before a step and, after it, compares the share of
    entries whose stored value changed with the share that had a nonzero gradient (AdamW moves every such entry by
    about lr). In bf16 storage a small update rounds back to the old value, so stored/expected falls far below 1.
    One host sync per step."""

    def __init__(self, named, n: int = 512):
        self.views = []
        for _, p in named:
            flat = p.detach().view(-1)
            stride = max(1, flat.numel() // n)
            self.views.append((p, stride, min(n, flat.numel())))
        self.saved = None

    @torch.no_grad()
    def _sample(self):
        return [p.detach().view(-1)[::s][:m].clone() for p, s, m in self.views]

    @torch.no_grad()
    def before(self):
        self.saved = self._sample()
        self.graded = [(p.grad.view(-1)[::s][:m] != 0) if p.grad is not None else torch.zeros(m, dtype=torch.bool,
                       device=p.device) for p, s, m in self.views]

    @torch.no_grad()
    def shares(self) -> tuple[float, float]:
        """(share of probed entries whose stored value changed, share that had a nonzero gradient)."""
        now = self._sample()
        changed = torch.stack([(a != b).sum() for a, b in zip(now, self.saved)]).sum()
        graded = torch.stack([g.sum() for g in self.graded]).sum()
        total = max(sum(int(a.numel()) for a in now), 1)
        both = torch.stack([changed, graded]).tolist()
        return both[0] / total, both[1] / total


@no_grad()
def check_vllm_sync(policy, vllm, prompts, trainable_named, max_new: int = 16) -> dict:
    """Prove that sync() really changes what vLLM samples (lessons file: a silent sync failure looks like
    "RL does not learn"). Zero every q_proj weight in the HF model, and measure the sampler/trainer gap (K3 on
    vLLM's samples) three ways: before the change, after the change without a sync, and after a sync. Then put
    the weights back and sync again. A working sync gives: unsynced gap >> synced gap ~ baseline gap."""
    def gap():
        rolls = vllm.sample(prompts, 2, max_new, 1.0, None)
        ks = [grpo.mismatch(completion_logprobs(policy, r.seq, len(p)), r.rollout_lp, r.cmask)["k3"]
              for p, r in zip(prompts, rolls)]
        return sum(ks) / len(ks)

    targets = [(n, p) for n, p in trainable_named if n.endswith("q_proj.weight")]
    if not targets:
        return {"skipped": "no trainable q_proj weights"}
    base = gap()
    saved = [p.detach().clone() for _, p in targets]
    for _, p in targets:
        p.zero_()
    unsynced = gap()
    vllm.sync(trainable_named)
    synced = gap()
    for (_, p), s_ in zip(targets, saved):
        p.copy_(s_)
    vllm.sync(trainable_named)
    restored = gap()
    ok = unsynced > 10 * max(synced, 1e-4) and synced < 10 * base + 0.05 and restored < 10 * base + 0.05
    return {"baseline_k3": base, "zeroed_unsynced_k3": unsynced, "zeroed_synced_k3": synced,
            "restored_k3": restored, "ok": bool(ok), "sync_path": vllm.sync_path}


@no_grad()
def check_vllm_sync_dt(policy, vllm, prompts, dtmask, model, max_new: int = 16) -> dict:
    """The sync check for Deletion Tuning: delete one whole masked layer (all its logits negative), and measure the
    sampler/trainer gap before the change, after it without a sync, and after syncing the hard-masked weights; then
    restore the logits and sync again. Working sync: unsynced gap >> synced gap ~ baseline gap."""
    def gap():
        rolls = vllm.sample(prompts, 2, max_new, 1.0, None)
        ks = [grpo.mismatch(completion_logprobs(policy, r.seq, len(p)), r.rollout_lp, r.cmask)["k3"]
              for p, r in zip(prompts, rolls)]
        return sum(ks) / len(ks)

    was_training = model.training
    model.eval()  # hard mask: the policy the sampler is supposed to hold
    name, layer = dtmask.masked_layers(model)[0]
    base = gap()
    saved = layer.gate.detach().clone()
    layer.gate.fill_(-1.0)
    unsynced = gap()
    vllm.sync(dt_hard_weights(dtmask, model))
    synced = gap()
    layer.gate.copy_(saved)
    vllm.sync(dt_hard_weights(dtmask, model))
    restored = gap()
    model.train(was_training)
    ok = unsynced > 10 * max(synced, 1e-4) and synced < 10 * base + 0.05 and restored < 10 * base + 0.05
    return {"baseline_k3": base, "deleted_layer": name, "deleted_unsynced_k3": unsynced, "deleted_synced_k3": synced,
            "restored_k3": restored, "ok": bool(ok), "sync_path": vllm.sync_path}


def train(cfg: dict) -> dict:
    seed = int(cfg.get("seed", 1234))
    random.seed(seed)
    torch.manual_seed(seed)
    device = cfg.get("device", "cpu")
    out = Path(cfg.get("out_dir", "out"))
    out.mkdir(parents=True, exist_ok=True)
    t = cfg["train"]
    algo, k, max_new = t["algo"], int(t["k"]), int(t["max_new"])
    temperature = float(t["temperature"])
    if algo not in grpo.ALL_ALGOS:
        raise ValueError(f"unknown algo {algo!r}; choose from {grpo.ALL_ALGOS}")
    v1 = algo == grpo.OBJECTIVE_V1
    if v1:  # refuse silent additions to the lead's contract
        if float(t.get("kl_coef", 0)) > 0:
            raise ValueError("objective_v1 has no reference-KL term (rl/objective_v1.md); set kl_coef: 0")
        if t.get("tis_clip"):
            raise ValueError("objective_v1 uses the sampler ratio only as a mask; tis_clip would add IS weighting")
    tr_eps = float(t.get("tr_epsilon", grpo.TR_EPSILON))
    update_mode = t.get("update_mode", "train")  # default: unchanged behaviour (see update_forward_mode)
    if update_mode not in UPDATE_MODES:
        raise ValueError(f"train.update_mode must be one of {UPDATE_MODES}")
    if update_mode == "eval" and t.get("dt"):
        raise ValueError("train.update_mode eval is not for Deletion Tuning: its mask layers are soft only in train mode")
    gate_cfg = t.get("logprob_gate")  # opt-in identical-weights check before the first update (logprob_gate)
    if gate_cfg is True:
        gate_cfg = {}
    if gate_cfg not in (None, False) and not isinstance(gate_cfg, dict):
        raise ValueError("train.logprob_gate must be true or a mapping {mean_abs_tol, outside_frac_tol, eps, prompts, max_new}")
    if isinstance(gate_cfg, dict) and t.get("dt"):
        raise ValueError("train.logprob_gate is not for Deletion Tuning: its soft (train) and hard (eval) masks differ by design")
    gate_rec = None
    state_dir = Path(t["state_dir"]) if t.get("state_dir") else None
    state_every = int(t.get("state_every", t.get("eval_every", 10)))
    deadline = float(t["deadline_unix"]) if t.get("deadline_unix") is not None else None
    cohort_k = int(t.get("cohort_eval_k", 0))
    call_steps = int(t["max_steps_this_call"]) if t.get("max_steps_this_call") else None
    max_train_s = float(t["max_train_seconds"]) if t.get("max_train_seconds") is not None else None
    sampler_kind = t.get("sampler") or ("hf_batch" if cfg["model"]["kind"] in ("hf", "tiny_olmoe") else "policy")
    if sampler_kind == "vllm" and cfg["model"].get("init_state"):
        raise ValueError("model.init_state is incompatible with the vLLM sampler; use a sampler backed by the trainer")
    if v1 and sampler_kind == "vllm" and temperature != 1.0:
        # vLLM reports log-probabilities of the raw model distribution; they equal the sampling distribution only at
        # temperature 1 without truncation (rollout.py), and objective_v1 uses them as the ratio denominator.
        raise ValueError("objective_v1 with the vllm sampler needs temperature 1.0 (sampler ratio contract)")
    if cfg["model"]["kind"] == "team5_adapter" and sampler_kind not in ("policy", "g5_batch"):
        raise ValueError(f"sampler {sampler_kind} is not available for the G5 LanguageModel; use sampler: policy or g5_batch")
    if sampler_kind == "g5_batch" and cfg["model"]["kind"] != "team5_adapter":
        raise ValueError("sampler g5_batch is for the G5 LanguageModel (model.kind team5_adapter)")
    pool = None
    if int(t.get("reward_pool", 0)) > 0:  # before any model loads: the workers must be forked from a small process
        if cfg["task"]["kind"] != "stdio":
            raise ValueError("train.reward_pool is for task.kind stdio")
        import score_pool  # noqa: PLC0415
        pool = score_pool.ScorePool(int(t["reward_pool"]))
    vllm = None
    if sampler_kind == "vllm":  # vLLM reserves its share of the GPU first, then the training model loads
        vllm = rollout.VLLMSampler(cfg["model"]["path"], seed=seed, **t.get("vllm", {}))
    policy, tok = build_model(cfg["model"], device)
    init_state_info = None
    if cfg["model"].get("init_state"):  # a trained state dict (e.g. SFT output) for the same architecture
        from safetensors.torch import load  # noqa: PLC0415
        ip = Path(cfg["model"]["init_state"])
        raw = ip.read_bytes()
        want = cfg["model"].get("init_state_sha256")
        got = hashlib.sha256(raw).hexdigest()
        if want and want != got:
            raise ValueError(f"model.init_state sha256 {got} != expected {want}")
        policy.model.load_state_dict(load(raw), strict=True)
        del raw
        init_state_info = {"path": str(ip), "sha256": got}
    task = build_task(cfg["task"], tok, seed) if pool is None else build_task(cfg["task"], tok, seed, pool)

    model = policy.model
    adapter = getattr(tok, "adapter_result", None)  # team5_adapter: one router/trainable set for everything below
    if adapter is not None:
        if t.get("trainable") or cfg.get("router_patterns") or t.get("router_trainable"):
            raise ValueError("model.kind team5_adapter takes trainable and router sets from the adapter config only")
        patterns = tuple(adapter.bundle.selection["router_patterns"])
    else:
        set_trainable(model, t.get("trainable"))
        patterns = tuple(cfg.get("router_patterns", router.ROUTER_PATTERNS))
    router_trainable = bool(t.get("router_trainable", False))  # control runs only; Gate 4 keeps the router frozen
    dense = bool(cfg["model"].get("dense", False))  # explicit opt-out for dense models (no router to freeze)
    if dense and (adapter is not None or router_trainable):
        raise ValueError("model.dense is for dense HF models only")
    if dense:
        frozen = []
    elif router_trainable:
        frozen = []
        for _, p_ in router.router_params(model, patterns):
            p_.requires_grad_(True)
    else:
        frozen = router.freeze_router(model, patterns)
        router.assert_router_frozen(model, patterns)
    if adapter is not None and frozen != adapter.bundle.selection["router_names"]:
        raise RuntimeError(f"frozen routers {frozen} differ from the adapter's {adapter.bundle.selection['router_names']}")
    checksum_before = "dense model: no router" if dense else router.router_checksum(model, patterns)
    dt_cfg, dtmask, dt_info = t.get("dt"), None, None
    if dt_cfg:  # Deletion Tuning as the RL method: the only trainable tensors are the mask logits
        if not v1 or adapter is not None or t.get("trainable"):
            raise ValueError("train.dt needs algo objective_v1, an hf model and no train.trainable patterns")
        dtmask = load_dt()
        dt_total = int(dt_cfg.get("alpha_steps", int(t["steps"]) * int(t.get("ppo_epochs", 1))))
        dt_names = dtmask.convert(model, dtmask.TARGET_SETS[dt_cfg.get("targets", "gate")],
                                  float(dt_cfg.get("alpha_start", 100.0)), float(dt_cfg.get("alpha_end", 1000.0)),
                                  dt_total, seed=seed)
        n_cal = int(dt_cfg.get("calib_prompts", 64))
        cal = ({"input_ids": torch.tensor([p_], dtype=torch.long), "attention_mask": torch.ones(1, len(p_), dtype=torch.long)}
               for p_ in task.train[:n_cal])  # prompts only, as in the official GRPO calibration
        with policy.autocast():
            scores = dtmask.wanda_scores(model, cal, device)
        dt_info = {"targets": dt_cfg.get("targets", "gate"), "masked_layers": len(dt_names), "alpha_steps": dt_total,
                   "alpha": [float(dt_cfg.get("alpha_start", 100.0)), float(dt_cfg.get("alpha_end", 1000.0))],
                   "lambda": float(dt_cfg.get("lambda", 1e-5)), "calib_prompts": min(n_cal, len(task.train)),
                   "wanda_prior": dtmask.apply_wanda_prior(model, scores, float(dt_cfg.get("eta", 1 / 2048)),
                                                           float(dt_cfg.get("prior_strength", 3.0))),
                   "deletion_at_init": dtmask.deletion_stats(model), "band_at_init": dtmask.band_stats(model),
                   "official": dtmask.OFFICIAL}
        del scores
        model.eval()
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_fp32 = use_fp32_master(policy) if t.get("fp32_master", True) and not dt_cfg else 0
    if t.get("autocast") is not None:
        # Explicit compute dtype. A G5 checkpoint is stored in fp32 (train_week2 keeps fp32 weights under CUDA bf16
        # autocast), so use_fp32_master converts nothing and, without this, the policy runs entirely in fp32. G5's KE2
        # projection also returns fp32 by design, so bf16-stored G5 weights only run under autocast.
        if t["autocast"] != "bf16":
            raise ValueError("train.autocast must be bf16 or unset")
        policy.amp_dtype = torch.bfloat16
    trainable_named = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    kz_cfg, kz, kz_log = t.get("keep_zero"), None, {"max_deleted_nonzero": 0}
    kz_identity = None
    if kz_cfg is not None or t.get("log_zero_share"):
        import keep_zero as keep_zero_mod  # noqa: PLC0415
        masks, enforce = {}, False
        if kz_cfg is not None:
            if not kz_cfg.get("path"):
                raise ValueError("train.keep_zero.path must name the baked keep mask")
            masks, digests = keep_zero_mod.load_masks_with_digests(kz_cfg["path"])
            for key, digest in digests.items():
                expected = kz_cfg.get(key)
                if expected is not None and expected != digest:
                    raise ValueError(f"train.keep_zero {key} {digest} != expected {expected}")
            enforce = bool(kz_cfg.get("enforce", False))
            kz_identity = {**digests, "enforce": enforce}
            kz_log["mask"] = {"path": str(kz_cfg["path"]), **digests}
        kz = keep_zero_mod.KeepZero(trainable_named, masks, enforce, float(t.get("weight_decay", 0.0)))
        kz_log.update(masked_entries=kz.n_masked, deleted_at_start=kz.n_deleted0,
                      deleted_share_of_masked_at_start=round(kz.n_deleted0 / max(kz.n_masked, 1), 6),
                      deleted_nonzero_at_start=kz.deleted_nonzero(), zero_share_at_start=round(kz.zero_share(), 6),
                      enforce=enforce if kz_cfg is not None else None)
        if kz_log["deleted_nonzero_at_start"]:
            raise ValueError(f"{kz_log['deleted_nonzero_at_start']} deleted weights are nonzero before RL starts")

    def sync_named():  # what the sampler must hold after an update
        return dt_hard_weights(dtmask, model) if dt_cfg else trainable_named
    pad_id = tok.pad_token_id if tok is not None and tok.pad_token_id is not None else None
    sampler = rollout.make_sampler(sampler_kind, policy, vllm, pad_id,
                                   **({"max_rows": int(t.get("sampler_max_rows", 128))} if sampler_kind == "g5_batch" else {}))
    ref = None
    if float(t.get("kl_coef", 0)) > 0:
        ref = copy.deepcopy(policy)
        ref.model.requires_grad_(False)
        ref.model.eval()
    start_w = StartWeights(model)  # CPU copy of the trainable weights: weight-change check, and KL to start
    opt = torch.optim.AdamW([p for _, p in trainable_named], lr=float(t["lr"]),
                            weight_decay=float(t.get("weight_decay", 0.0)))
    if kz is not None:
        kz.check_optimizer(opt)
    tis_clip = float(t["tis_clip"]) if t.get("tis_clip") else None
    micro_rows = int(t["micro_rows"]) if t.get("micro_rows") else None
    probe_w = UpdateProbe(trainable_named) if v1 else None
    dt_layer0 = dtmask.masked_layers(model)[0][1] if dt_cfg else None
    # DT logits far from zero are saturated (gradient far below Adam's eps), so most of them rightly do not move:
    # the lost-update rule, written for ordinary weights, would misfire. The shares are still logged.
    fail_on_lost = bool(t.get("fail_on_lost_update", not dt_cfg))
    min_stored = float(t.get("min_stored_update_ratio", 0.5))
    reward_workers = int(t.get("reward_workers", 1))
    log_routing = bool(t.get("routing_log", False)) and bool(routing.router_modules(model))
    n_experts = getattr(getattr(model, "config", None), "num_experts", None)
    # Native sampling draws on the model's device, so its generator lives there; HF/vLLM keep host-side generators.
    gen_device = device if sampler_kind in ("policy", "g5_batch") and not isinstance(policy, HFPolicy) else "cpu"
    gen = torch.Generator(device=gen_device).manual_seed(seed)
    order = list(range(len(task.train)))
    fixture_smoke = adapter is not None and adapter.status != "READY"
    metrics_path = out / ("smoke_metrics.jsonl" if fixture_smoke else "metrics.jsonl")
    if fixture_smoke:
        (out / "FIXTURE_SMOKE_NOT_A_RESULT").write_text(f"Built from a {adapter.status} adapter config "
                                                        f"(mode {adapter.mode}); not a G5 result.\n")
    gen_cohort = torch.Generator(device=gen_device).manual_seed(seed + 3)  # train-cohort evaluation stream
    gen_extra = torch.Generator(device=gen_device).manual_seed(seed + 1)  # own stream: training stays as without it
    gens = {"gen": gen, "gen_extra": gen_extra, "gen_cohort": gen_cohort}
    evals_path = out / "evals.jsonl"
    resumed, start_step, prior_s, cohort_ids = None, 0, 0.0, None
    if state_dir is not None:
        identity = state_identity(
            cfg, trainable_named, init_state_sha256=init_state_info["sha256"] if init_state_info else None,
            keep_zero_identity=kz_identity,
        )
        resumed = load_state(state_dir, identity)
    if resumed is not None:
        with torch.no_grad():
            for n_, p_ in trainable_named:
                p_.copy_(resumed["trainable"][n_].to(p_.device, p_.dtype))
        if kz is not None:
            kz.check("restored checkpoint")
        opt.load_state_dict(resumed["opt"])
        random.setstate(resumed["py_random"])
        torch.set_rng_state(resumed["torch_rng"])
        for name_, g_ in gens.items():
            g_.set_state(resumed["gens"][name_])
        order, start_step, prior_s = list(resumed["order"]), int(resumed["step"]), float(resumed["elapsed_s"])
        cohort_ids = resumed["cohort_ids"]
        if dt_cfg:
            for _, m_ in dtmask.masked_layers(model):
                m_.current_step = int(resumed["dt_steps"])
        if vllm is not None:  # the sampler must hold the restored weights before anything is sampled
            vllm.sync(sync_named())
        print(json.dumps({"resumed_from": resumed["_file"], "step": start_step, "elapsed_s": round(prior_s, 1)}),
              flush=True)
    elif dt_cfg and vllm is not None:
        vllm.sync(sync_named())  # the Wanda prior already deletes a few weights: the sampler starts from them
    dt_prev = dtmask.keep_masks(model) if dt_cfg else None  # hard mask before the next update (gross flip counts)
    if resumed is not None:
        read_jsonl(metrics_path, start_step)  # drop rows of steps that will be redone
    past_evals = read_jsonl(evals_path, start_step) if resumed is not None else []
    if resumed is None and evals_path.exists():
        evals_path.unlink()
    metrics_f = open(metrics_path, "a" if resumed is not None else "w")
    start = time.time()
    heldout_curve, heldout_scores, routing_curve = [], {}, []
    cohort_scores: dict = {}
    for r_ in past_evals:  # results measured before the restart count as measured
        if r_["name"] == "heldout":
            heldout_curve.append((r_["step"], r_["pass"]))
            heldout_scores[r_["step"]] = r_["scores"]
        elif r_["name"] == "train_cohort":
            cohort_scores[r_["step"]] = r_["scores"]

    def write_state(step):
        payload = {"identity": identity, "step": step, "order": list(order), "cohort_ids": cohort_ids,
                   "elapsed_s": prior_s + time.time() - start,
                   "trainable": {n_: p_.detach().to("cpu", copy=True) for n_, p_ in trainable_named},
                   "dt_steps": dtmask.masked_layers(model)[0][1].current_step if dt_cfg else None,
                   "opt": opt.state_dict(), "py_random": random.getstate(), "torch_rng": torch.get_rng_state(),
                   "gens": {name_: g_.get_state() for name_, g_ in gens.items()}}
        rec_ = save_state(state_dir, step, payload)
        print(json.dumps({"state_saved": rec_}), flush=True)
        return rec_

    def cohort_eval(step):
        c0_ = time.time()
        scores, rolls = evaluate(sampler, task, task.train, cohort_k, max_new, temperature, gen_cohort, reward_workers)
        cohort_scores[step] = scores
        rec_ = {"name": "train_cohort", "step": step, "k": cohort_k, "problems": len(scores),
                "prompt_order_sha256": prompt_order_sha256(task, task.train),
                "pass": sum(scores) / len(scores), "scores": scores, **length_stats(rolls, max_new, policy.eos_id),
                "reasons": pop_reasons(task), "seconds": round(time.time() - c0_, 1)}
        append_jsonl(evals_path, rec_)
        print(json.dumps({k_: v for k_, v in rec_.items() if k_ != "scores"}), flush=True)
    probe: dict = {}
    eval_k = int(t.get("eval_k", 4))
    extra_max_new = int(t["extra_eval_max_new"]) if t.get("extra_eval_max_new") else None
    extra_evals: dict = {}

    def extra_eval(step):
        scores, rolls = evaluate(sampler, task, task.heldout, eval_k, extra_max_new, temperature, gen_extra,
                                 reward_workers)
        extra_evals[step] = {"pass": sum(scores) / len(scores), "scores": scores,
                             **length_stats(rolls, extra_max_new, policy.eos_id)}
        print(json.dumps({"extra_eval_step": step, "max_new": extra_max_new,
                          **{k_: v for k_, v in extra_evals[step].items() if k_ != "scores"}}), flush=True)

    def log_heldout(step):
        c0_ = time.time()
        pop_reasons(task)  # start this evaluation's reason counts from zero
        scores, rolls = evaluate(sampler, task, task.heldout, eval_k, max_new, temperature, gen, reward_workers)
        r = sum(scores) / len(scores)
        heldout_curve.append((step, r))
        heldout_scores[step] = scores
        extra = dict(length_stats(rolls, max_new, policy.eos_id))
        append_jsonl(evals_path, {"name": "heldout", "step": step, "k": eval_k, "problems": len(scores), "pass": r,
                                  "prompt_order_sha256": prompt_order_sha256(task, task.heldout),
                                  "scores": scores, **extra, "reasons": pop_reasons(task),
                                  "seconds": round(time.time() - c0_, 1)})
        if t.get("kl_to_start"):
            extra["kl_to_start"] = float(f"{kl_to_start(policy, start_w, rolls, task.heldout):.4g}")
        if log_routing:
            n = int(t.get("routing_probe", 8))
            if not probe:  # fixed probe batch: the first n held-out prompts with their step-0 completions
                probe["items"] = [(p, r_.seq, routing.completion_positions(len(p), r_.cmask))
                                  for p, r_ in zip(task.heldout[:n], rolls[:n])]
            idx = torch.cat([routing.routing(policy, s_, m_) for _, s_, m_ in probe["items"]], 1)
            if "idx0" not in probe:  # noise floor: two identical forwards (GPU kernels need not be bitwise stable)
                again = torch.cat([routing.routing(policy, s_, m_) for _, s_, m_ in probe["items"]], 1)
                extra["flip_noise_floor"] = round(routing.flip_rate(idx, again)[0], 4)
            probe.setdefault("idx0", idx)
            ratio = routing.load_ratio(routing.expert_load(idx, n_experts))
            flip_any, flip_layers = routing.flip_rate(probe["idx0"], idx)
            extra.update({"load_ratio_max": round(float(ratio.max()), 4),
                          "load_ratio_per_layer": [round(float(x), 4) for x in ratio],
                          "flip_vs_step0": round(flip_any, 4), "flip_vs_step0_per_layer": flip_layers,
                          "top1_flip_vs_step0": round(routing.top1_flip_rate(probe["idx0"], idx), 4),
                          "mass_shift_vs_step0": float(f"{routing.mass_shift(probe['idx0'], idx):.4g}")})
        routing_curve.append({"step": step, **extra})
        return r, extra

    sync_check = None
    if vllm is not None and t.get("verify_sync", True):
        sync_check = (check_vllm_sync_dt(policy, vllm, task.train[:2], dtmask, model) if dt_cfg else
                      check_vllm_sync(policy, vllm, task.train[:2], trainable_named))
        print(json.dumps({"vllm_sync_check": sync_check}), flush=True)
        (out / "vllm_sync_check.json").write_text(json.dumps(sync_check, indent=1))
        if sync_check.get("ok") is False:
            raise RuntimeError(f"vLLM weight sync does not work: {sync_check}")
    if isinstance(gate_cfg, dict):
        # Before the screen, so a failure costs no screen and no evaluation. Its own generator: the run's generators
        # (gen, gen_cohort, gen_extra) are untouched. Runs again on a resume (any weights are identical to themselves).
        c0 = time.time()
        g_prompts = task.train[:int(gate_cfg.get("prompts", 1))]
        g_new = min(max_new, int(gate_cfg.get("max_new", 256)))
        g_rolls = sampler.sample(g_prompts, k, g_new, temperature, torch.Generator(device=gen_device).manual_seed(seed + 4))
        gate_rec = logprob_gate(policy, model, [(r_.seq, r_.cmask, len(p_), r_.rollout_lp) for p_, r_ in zip(g_prompts, g_rolls)],
                                update_mode, float(gate_cfg.get("eps", tr_eps)), micro_rows,
                                float(gate_cfg.get("mean_abs_tol", GATE_MEAN_ABS_TOL)),
                                float(gate_cfg.get("outside_frac_tol", GATE_OUTSIDE_FRAC_TOL)))
        gate_rec.update(prompts=len(g_prompts), k=k, max_new=g_new, seconds=round(time.time() - c0, 3))
        (out / "logprob_gate.json").write_text(json.dumps(gate_rec, indent=1))
        print(json.dumps({"logprob_gate": gate_rec}), flush=True)
        if not gate_rec["ok"]:
            metrics_f.close()
            raise RuntimeError(
                f"logprob gate: at identical weights the update forward (mode {update_mode}) differs from the behaviour "
                f"log-probs by mean {gate_rec['mean_abs']} nats (max {gate_rec['max_abs']}); {gate_rec['outside_frac']:.4g} "
                f"of tokens leave the trust region (tolerances {gate_rec['mean_abs_tol']}, {gate_rec['outside_frac_tol']}). "
                f"A train-only layer such as dropout is the usual cause: set train.update_mode: eval "
                f"(rl_job_v1: --update-mode eval).")
    screen = t.get("screen")  # mixed-band selection on TRAIN prompts only; the held-out set is never filtered
    if resumed is not None and cohort_ids is not None:  # the cohort screened before the restart, in its saved order
        by_env = {env: list(key) for key, env in task._items.items()}
        task.train = [by_env[i] for i in cohort_ids]
    elif screen:
        c0 = time.time()
        n_s, k_s, need = int(screen.get("n", 64)), int(screen.get("k", k)), int(screen.get("min_mixed", 12))
        cand = task.train[:n_s]
        gen_s = torch.Generator(device=gen_device).manual_seed(seed + 2)
        s_rolls = sampler.sample(cand, k_s, max_new, temperature, gen_s)
        s_time = time.time() - c0
        s_pairs = [(p, row[m].tolist()) for p, r in zip(cand, s_rolls) for row, m in zip(r.seq[:, len(p):], r.cmask)]
        pop_reasons(task)
        flat = score_completions(task, s_pairs, reward_workers)
        if screen.get("save_completions"):  # private: the same completions re-scored for the matched timing check
            with open(screen["save_completions"], "w") as f_:
                for (p_, c_), rw_ in zip(s_pairs, flat):
                    f_.write(json.dumps({"id": task._items[tuple(p_)], "text": task.decode(c_), "reward": rw_}) + "\n")
        passes = [int(sum(flat[i * k_s:(i + 1) * k_s])) for i in range(len(cand))]
        ids = [getattr(task, "_items", {}).get(tuple(p)) for p in cand]
        mixed = [p for p, c in zip(cand, passes) if 0 < c < k_s]
        s_tok = int(sum(int(r.cmask.sum()) for r in s_rolls))
        rec_s = {"n": len(cand), "k": k_s, "min_mixed": need, "mixed": len(mixed),
                 "all_pass": sum(c == k_s for c in passes), "all_fail": sum(c == 0 for c in passes),
                 "pass_rate": round(sum(passes) / max(len(cand) * k_s, 1), 4),
                 "histogram": {str(i): passes.count(i) for i in range(k_s + 1)},
                 "per_task": [{"id": i, "passes": c} for i, c in zip(ids, passes)],
                 "mixed_ids": [i for i, c in zip(ids, passes) if 0 < c < k_s],
                 "sampled_tokens": s_tok, "rollout_s": round(s_time, 2), "score_s": round(time.time() - c0 - s_time, 2),
                 "reasons": pop_reasons(task), "reward_workers": reward_workers,
                 **length_stats(s_rolls, max_new, policy.eos_id), **gpu_memory()}
        (out / "screen.json").write_text(json.dumps(rec_s, indent=1))
        print(json.dumps({"screen": {k_: v for k_, v in rec_s.items() if k_ not in ("per_task", "mixed_ids")}}),
              flush=True)
        if len(mixed) < max(need, 1):  # min_mixed 0 with no mixed prompt would train on an empty list
            metrics_f.close()
            summary = {"status": "NO_GO_MIXED_BAND", "algo": algo, "screen": {k_: v for k_, v in rec_s.items()
                                                                              if k_ != "per_task"},
                       "seconds": round(time.time() - start, 1), "versions": versions()}
            (out / "summary.json").write_text(json.dumps(summary, indent=1))
            return summary
        task.train = mixed
        order = list(range(len(task.train)))
        cohort_ids = [i for i, c in zip(ids, passes) if 0 < c < k_s]
    if state_dir is not None and resumed is None:
        write_state(0)  # a kill during the first evaluation must not repeat the screen
    if 0 in heldout_scores:
        h0 = heldout_curve[0][1]
    else:
        h0, extra0 = log_heldout(0)
        if cfg.get("verbose", True):
            print(json.dumps({"step": 0, "heldout_reward": h0, **extra0}), flush=True)
    if cohort_k and 0 not in cohort_scores:
        cohort_eval(0)
    if extra_max_new:
        extra_eval(0)
    if state_dir is not None and start_step > 0 and start_step % int(t.get("eval_every", 10)) == 0:
        if start_step not in heldout_scores:  # killed during this step's evaluation: measure it now
            log_heldout(start_step)
        if cohort_k and start_step not in cohort_scores:
            cohort_eval(start_step)
    steps_done, paused, last_step_s = start_step, False, 0.0
    for step in range(start_step + 1, int(t["steps"]) + 1):
        if max_train_s is not None and step > 1 and time.time() - start > max_train_s:
            print(json.dumps({"stopped_early": f"max_train_seconds {max_train_s} reached before step {step}"}),
                  flush=True)
            break
        if (deadline is not None and time.time() + 1.5 * last_step_s > deadline) or (
                call_steps is not None and step - start_step > call_steps):
            print(json.dumps({"paused": f"deadline or max_steps_this_call reached before step {step}"}), flush=True)
            paused = True
            break
        steps_done = step
        times = {}
        random.shuffle(order)
        batch = [task.train[i] for i in order[: int(t["prompts_per_step"])]]
        c0 = time.time()
        rolls = sampler.sample(batch, k, max_new, temperature, gen)
        times["rollout"] = time.time() - c0
        sampled_tokens = int(sum(int(r.cmask.sum()) for r in rolls))
        c0 = time.time()
        groups, rewards_all, dropped, mism = [], [], 0, []
        scored = []
        sub_fn, subgroups = getattr(task, "subgroup_of", None), {}
        # observer token counts: one host sync per step (cmask lives on the sampler device), not one per group
        group_tokens = torch.stack([r.cmask.sum() for r in rolls]).tolist() if sub_fn is not None else None
        kinds = {"all_one": 0, "all_zero": 0, "tied_other": 0, "singleton": 0, "mixed": 0}
        if reward_workers > 1:
            flat = score_completions(task, [(p, row[m].tolist()) for p, r in zip(batch, rolls)
                                            for row, m in zip(r.seq[:, len(p):], r.cmask)], reward_workers)
        for gi, (p, r) in enumerate(zip(batch, rolls)):
            if reward_workers > 1:
                rewards = torch.tensor(flat[gi * k:(gi + 1) * k])
            else:
                rewards = torch.tensor([task.reward(p, row[m].tolist()) for row, m in zip(r.seq[:, len(p):], r.cmask)])
            rewards_all += rewards.tolist()
            scored.append((p, r, grpo.advantages(rewards, algo)))
            if sub_fn is not None:  # input mixture vs what survives group dropping, per subgroup
                sg = subgroups.setdefault(sub_fn(p), {"groups": 0, "kept": 0, "tokens": 0, "kept_tokens": 0,
                                                      "rollouts": 0, "passes": 0})
                kept_ = scored[-1][2] is not None
                n_tok_ = int(group_tokens[gi])
                sg["groups"] += 1
                sg["kept"] += int(kept_)
                sg["tokens"] += n_tok_
                sg["kept_tokens"] += n_tok_ if kept_ else 0
                sg["rollouts"] += len(rewards)
                sg["passes"] += int((rewards == 1.0).sum())
            if v1:
                if not torch.isfinite(rewards).all():
                    raise ValueError("reward must be finite (objective_v1 contract)")
                rl_ = rewards.tolist()
                kinds["singleton" if len(rl_) < 2 else "mixed" if max(rl_) != min(rl_) else
                      "all_one" if rl_[0] == 1.0 else "all_zero" if rl_[0] == 0.0 else "tied_other"] += 1
        times["reward"] = time.time() - c0
        step_reasons = pop_reasons(task)
        c0 = time.time()
        if dt_cfg:
            model.eval()  # hard mask: the engine-mismatch metric compares the same policy in both engines
        if update_mode == "eval":
            update_forward_mode(model, update_mode)  # old_lp in the same mode as the update and the sampler
        for p, r, adv in scored:
            if adv is None:
                dropped += 1
                continue
            with torch.no_grad():
                old_lp = chunked_logprobs(policy, r.seq, len(p), micro_rows)
                ref_lp = chunked_logprobs(ref, r.seq, len(p), micro_rows) if ref is not None else None
            isw = None
            if r.rollout_lp is not None:
                mism.append(grpo.mismatch(old_lp, r.rollout_lp, r.cmask))
                if tis_clip:
                    isw = grpo.tis_weights(old_lp, r.rollout_lp, r.cmask, algo, tis_clip)
            if v1:  # ratio denominator = the policy that sampled the tokens
                sampler_lp = r.rollout_lp if r.rollout_lp is not None else old_lp
                ratio_src = "rollout_lp" if r.rollout_lp is not None else "old_lp"
                # DT runs also carry the trainer's hard-mask log-probs (old_lp, eval mode) for the soft/hard metric
                groups.append((r.seq, r.cmask, adv.to(device), sampler_lp, old_lp if dt_cfg else None, len(p), None))
                continue
            groups.append((r.seq, r.cmask, adv.to(device), old_lp, ref_lp, len(p), isw))
        times["old_logprobs"] = time.time() - c0
        stats = {"clip_frac": 0.0, "ratio_mean": 1.0, "kl": 0.0}
        loss_val = 0.0
        step_flip = step_top1 = step_mass = None
        grad_norm = None
        v1_rec = {}
        if v1:
            stats = {}
            n_tok = int(sum(g_[1].sum() for g_ in groups)) if groups else 0  # batch-global T (one host sync)
            if groups and not bool(torch.stack([torch.isfinite(torch.where(g_[1], g_[3], 0.0)).all()
                                                for g_ in groups]).all()):  # one host sync for the step
                raise ValueError("non-finite sampler log-probability on a real token (objective_v1 contract)")
            v1_rec = {"tr_epsilon": tr_eps, "group_kinds": dict(kinds), "tokens": n_tok,
                      "passes": int(sum(1 for x in rewards_all if x == 1.0)), "rollouts": len(rewards_all),
                      "ratio_source": ratio_src if groups else None, "optimizer_stepped": False}
        c0 = time.time()
        if v1 and groups and n_tok > 0:
            if vllm is not None:
                vllm.sleep()
            update_forward_mode(model, update_mode)  # default "train": model.train(), as before
            epochs = []
            for _ in range(int(t.get("ppo_epochs", 1))):
                opt.zero_grad()
                ep_loss, ep = None, {}
                for g_ in groups:
                    lv, st = backward_objective_v1(policy, g_, tr_eps, n_tok, micro_rows)
                    ep_loss = lv if ep_loss is None else ep_loss + lv
                    for key, v in st.items():
                        ep[key] = v if key not in ep else ep[key] + v
                if int(ep["nonfinite"]):  # before the optimizer step; one host sync per epoch
                    raise ValueError("non-finite current log-probability or ratio on a real token (objective_v1 contract)")
                if dt_cfg and dt_info["lambda"] > 0:  # official regulariser, once per optimizer step
                    lam_t = dtmask.lambda_at(min(dt_layer0.current_step, dt_info["alpha_steps"]), dt_info["alpha_steps"],
                                             dt_info["lambda"])
                    if lam_t > 0:
                        (-lam_t * dtmask.regulariser(model)).backward()
                grad_norm = float(torch.nn.utils.clip_grad_norm_([p for _, p in trainable_named],
                                                                 float(t.get("grad_clip", 1.0))))
                probe_w.before()
                opt.step()
                if dt_cfg:
                    dtmask.step_all(model)
                share, expected = probe_w.shares()
                sh = {key: float(ep.pop(key)) for key in SOFT_HARD_KEYS if key in ep}
                ep = {key: int(v) for key, v in ep.items()}
                if sh:  # DT: soft-mask policy vs hard-mask policy, same engine, before this epoch's update
                    n_ = max(ep["tokens"], 1)
                    sh = {"sh_k3": float(f"{sh['sh_k3_sum'] / n_:.4g}"), "sh_abs_logratio": float(f"{sh['sh_abs_sum'] / n_:.4g}"),
                          "sh_outside_frac": round(sh["sh_outside"] / n_, 6)}
                epochs.append({"loss": float(ep_loss), "tokens_inside": ep["inside"], **sh,
                               "masked_frac": round(1 - ep["inside"] / max(ep["tokens"], 1), 6),
                               "masked_frac_pos": round(ep["masked_pos"] / max(ep["tokens_pos"], 1), 6),
                               "masked_frac_neg": round(ep["masked_neg"] / max(ep["tokens_neg"], 1), 6),
                               "grad_norm": float(f"{grad_norm:.4g}"), "stored_update_share": round(share, 6),
                               "grad_nonzero_share": round(expected, 6)})
                if expected > 0 and share < min_stored * expected:
                    msg = (f"step {step}: {share:.4g} of probed stored weights changed but {expected:.4g} had a "
                           f"nonzero gradient (lost update; bf16 storage without fp32_master?)")
                    if fail_on_lost:
                        raise RuntimeError(msg)
                    print(json.dumps({"warning": msg}), flush=True)
            loss_val = sum(e["loss"] for e in epochs)
            v1_rec.update(optimizer_stepped=True, **{key: epochs[-1][key] for key in epochs[-1] if key != "loss"})
            if dt_cfg:
                d_ = dtmask.deletion_stats(model)
                flips, dt_prev = dtmask.flip_counts(model, dt_prev)
                band = dtmask.band_stats(model)
                v1_rec.update(dt_alpha=dt_layer0.alpha, dt_deleted=d_["deleted"],
                              dt_deleted_frac_of_targeted=d_["deleted_frac_of_targeted"],
                              dt_newly_deleted=flips["newly_deleted"], dt_restored=flips["restored"],
                              dt_live_share=round(band["live_share"], 6), dt_band_share=round(band["band_share"], 6),
                              dt_soft_hard_gap=float(f"{band['soft_hard_gap']:.4g}"))
            if len(epochs) > 1:
                v1_rec["epochs"] = epochs
        elif v1:
            pass  # every group dropped, or kept groups without a real token: no zero_grad, no step, no state
        elif groups:
            if log_routing:
                g = groups[0]
                fmask = routing.completion_positions(g[5], g[1])
                idx_before = routing.routing(policy, g[0], fmask)
            if vllm is not None:
                vllm.sleep()
            update_forward_mode(model, update_mode)  # default "train": model.train(), as before
            for _ in range(int(t.get("ppo_epochs", 1))):
                opt.zero_grad()
                for g_ in groups:
                    lv, stats = backward_group(policy, g_, algo, float(t.get("clip_eps", 0.2)),
                                               float(t.get("kl_coef", 0)), len(groups), micro_rows)
                    loss_val += lv
                grad_norm = float(torch.nn.utils.clip_grad_norm_([p for _, p in trainable_named],
                                                                 float(t.get("grad_clip", 1.0))))
                opt.step()
            if log_routing:
                idx_after = routing.routing(policy, g[0], fmask)
                step_flip = routing.flip_rate(idx_before, idx_after)[0]
                step_top1 = routing.top1_flip_rate(idx_before, idx_after)
                step_mass = routing.mass_shift(idx_before, idx_after)
        if kz is not None and device.startswith("cuda"):
            # Attribute pending optimizer work to training before timing the mask scans.
            torch.cuda.synchronize(device)
        times["train"] = time.time() - c0
        kz_rec = {}
        if kz is not None:
            c0 = time.perf_counter()
            if kz.n_masked:
                dn = kz.deleted_nonzero()  # before any backstop: what the gradient mask alone achieved
                kz_log["max_deleted_nonzero"] = max(kz_log["max_deleted_nonzero"], dn)
                kz_rec["deleted_nonzero"] = dn
                if kz.enforce_after_step:
                    kz.enforce()
                else:
                    kz.check(f"step {step}")
            kz_rec["zero_share"] = round(kz.zero_share(), 6)
            times["keep_zero_checks"] = time.perf_counter() - c0
        c0 = time.time()
        sync_bytes = 0
        if vllm is not None:
            vllm.wake_up()
            if groups:
                sync_bytes = vllm.sync(sync_named())
        times["sync"] = time.time() - c0
        rec = {"step": step, "train_reward": sum(rewards_all) / len(rewards_all), "groups_used": len(groups),
               "groups_dropped": dropped, "loss": loss_val, **stats, **v1_rec, **kz_rec,
               "sampled_tokens": sampled_tokens,
               "rollout_tokens_per_s": round(sampled_tokens / max(times["rollout"], 1e-9), 1),
               "times_s": {k_: round(v, 3) for k_, v in times.items()}, "step_s": round(sum(times.values()), 3),
               "sync_mb": round(sync_bytes / 2**20, 1), **gpu_memory(),
               "seconds": round(prior_s + time.time() - start, 1)}
        if step_reasons is not None:
            rec["reasons"] = step_reasons
        if subgroups:
            rec["subgroups"] = dict(sorted(subgroups.items()))
        last_step_s = rec["step_s"]
        if mism:
            rec["mismatch_k3"] = round(sum(x["k3"] for x in mism) / len(mism), 6)
            rec["mismatch_abs_logratio"] = round(sum(x["abs_logratio"] for x in mism) / len(mism), 6)
        if step_flip is not None:
            rec["step_flip"] = round(step_flip, 4)
            rec["step_top1_flip"] = round(step_top1, 4)
            rec["step_mass_shift"] = float(f"{step_mass:.4g}")
        if grad_norm is not None and "grad_norm" not in rec:
            rec["grad_norm"] = float(f"{grad_norm:.4g}")
        due = step % int(t.get("eval_every", 10)) == 0 or step == int(t["steps"])
        if state_dir is None:  # original order: the evaluation is part of the step's row
            if due:
                rec["heldout_reward"], extra = log_heldout(step)
                rec.update({k_: v for k_, v in extra.items() if not k_.endswith("per_layer")})
            metrics_f.write(json.dumps(rec) + "\n")
            metrics_f.flush()
        else:  # durable order: the step's row and the state reach disk before any evaluation starts
            metrics_f.write(json.dumps(rec) + "\n")
            metrics_f.flush()
            os.fsync(metrics_f.fileno())
            if due or step % state_every == 0:
                write_state(step)
            if due:
                rec["heldout_reward"], _ = log_heldout(step)
                if cohort_k:
                    cohort_eval(step)
        if cfg.get("verbose", True):
            print(json.dumps(rec), flush=True)
    metrics_f.close()
    planned_steps = int(t["steps"])
    if paused:  # out of time for this invocation: the state is on disk, the next call continues from it
        if steps_done > start_step and steps_done % state_every and steps_done % int(t.get("eval_every", 10)):
            write_state(steps_done)
        status = {"status": "PAUSED_AT_DEADLINE", "steps_done": steps_done, "steps_planned": planned_steps,
                  "seconds": round(prior_s + time.time() - start, 1)}
        (out / "status.json").write_text(json.dumps(status))
        return status
    if steps_done < planned_steps:  # stopped by max_train_seconds: evaluate where training stopped
        if state_dir is not None:
            write_state(steps_done)
        if steps_done not in heldout_scores:
            log_heldout(steps_done)
        t["steps"] = steps_done
    if state_dir is not None:  # finalize-only restart: a kill during the last evaluation loses nothing but it
        if steps_done not in heldout_scores:
            log_heldout(steps_done)
        if cohort_k and steps_done not in cohort_scores:
            cohort_eval(steps_done)
    if extra_max_new:
        extra_eval(int(t["steps"]))
    saved_weights = None
    if t.get("save_trainable"):
        path = Path(t["save_trainable"])
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({n: p_.detach().to(torch.bfloat16).cpu() for n, p_ in trainable_named}, path)
        saved_weights = {"path": str(path), "bytes": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    checksum_after = "dense model: no router" if dense else router.router_checksum(model, patterns)
    recs = [json.loads(line) for line in metrics_path.read_text().splitlines()]
    later = recs[1:] or recs  # step 1 includes warm-up (compilation, caches); report it separately
    last = max(heldout_scores)
    summary = {"algo": algo, "steps": int(t["steps"]), "k": k, "prompts_per_step": int(t["prompts_per_step"]),
               "max_new": max_new, "sampler": sampler_kind, "trainable_params": n_trainable,
               "fp32_master_params": n_fp32, "tis_clip": tis_clip,
               "router_params_frozen": frozen, "router_checksum_before": checksum_before,
               "router_checksum_after": checksum_after, "router_unchanged": checksum_before == checksum_after,
               "heldout_reward_start": h0, "heldout_reward_end": heldout_curve[-1][1], "heldout_curve": heldout_curve,
               "heldout_change": heldout.paired_bootstrap(heldout_scores[0], heldout_scores[last], seed=seed),
               "groups_used_total": sum(r["groups_used"] for r in recs),
               "trainable_weight_change": {k_: float(f"{v:.4g}") for k_, v in start_w.change().items()},
               "step1_s": recs[0]["step_s"] if recs else None,
               "mean_step_s_after_step1": round(sum(r["step_s"] for r in later) / len(later), 3),
               "mean_times_s_after_step1": {k_: round(sum(r["times_s"][k_] for r in later) / len(later), 3)
                                            for k_ in later[0]["times_s"]},
               "mean_rollout_tokens_per_s": round(sum(r["rollout_tokens_per_s"] for r in later) / len(later), 1),
               "routing_curve": routing_curve, "vllm_sync_path": getattr(vllm, "sync_path", None),
               "vllm_sync_check": sync_check,
               "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
               "seconds": round(time.time() - start, 1),
               "seconds_per_step": round((time.time() - start) / max(int(t["steps"]), 1), 2),
               "peak_gpu_memory_gb": (round(torch.cuda.max_memory_allocated() / 2**30, 2)
                                      if device.startswith("cuda") else None),
               **{f"end_{k_}": v for k_, v in gpu_memory().items()}, "versions": versions()}
    if any("mismatch_k3" in r for r in recs):
        ks = [r["mismatch_k3"] for r in recs if "mismatch_k3" in r]
        summary["mean_mismatch_k3"] = round(sum(ks) / len(ks), 6)
    summary["router_trainable"] = router_trainable
    if planned_steps != summary["steps"]:
        summary["steps_planned"] = planned_steps
    if v1:
        summary["objective"] = {"name": "objective_v1", "contract": "rl/objective_v1.md (lead, commit ff19ce2)",
                                "tr_epsilon": tr_eps, "reference_kl": "none (not in the contract)",
                                "steps_with_optimizer_update": sum(1 for r in recs if r.get("optimizer_stepped")),
                                "group_kinds_total": {k_: sum(r["group_kinds"][k_] for r in recs)
                                                      for k_ in recs[0]["group_kinds"]} if recs else {}}
    summary["saved_trainable_weights"] = saved_weights
    if update_mode != "train":
        summary["update_mode"] = update_mode
    if gate_cfg not in (None, False):
        summary["logprob_gate"] = gate_rec
    if init_state_info:
        summary["init_state"] = init_state_info
    if kz is not None:
        kz_log.update(deleted_nonzero_end=kz.deleted_nonzero() if kz.n_masked else None,
                      deleted_zero_end=kz.deleted_zero() if kz.n_masked else None,
                      zero_share_end=round(kz.zero_share(), 6))
        kz_log["persistent_mask_tensor_bytes"] = sum(
            mask.numel() * (mask.element_size() + kz.params[name].element_size())
            for name, mask in kz.keep.items()
        )
        summary["keep_zero"] = kz_log
    if dt_cfg:
        summary["deletion_tuning"] = {**dt_info, "deletion_final": dtmask.deletion_stats(model),
                                      "alpha_final": dt_layer0.alpha, "optimizer_steps": dt_layer0.current_step}
    if state_dir is not None:
        summary["status"] = "COMPLETE"
        summary["state"] = json.loads((state_dir / "LATEST.json").read_text())
        summary["resumed_from_step"] = start_step if resumed is not None else None
        summary["seconds_all_invocations"] = round(prior_s + time.time() - start, 1)
    if any("subgroups" in r for r in recs):  # observer: share of the input vs share of what the loss actually saw
        tot: dict = {}
        for r in recs:
            for name_, v in r.get("subgroups", {}).items():
                acc = tot.setdefault(name_, dict.fromkeys(v, 0))
                for key in v:
                    acc[key] += v[key]
        all_g, all_k = sum(v["groups"] for v in tot.values()), sum(v["kept"] for v in tot.values())
        all_kt = sum(v["kept_tokens"] for v in tot.values())
        summary["subgroups"] = {name_: {**v, "sampled_group_share": round(v["groups"] / max(all_g, 1), 4),
                                        "kept_group_share": round(v["kept"] / max(all_k, 1), 4),
                                        "kept_token_share": round(v["kept_tokens"] / max(all_kt, 1), 4)}
                                for name_, v in sorted(tot.items())}
    if cohort_scores:
        first_c, last_c = min(cohort_scores), max(cohort_scores)
        summary["train_cohort"] = {"problems": len(cohort_scores[first_c]), "k": cohort_k,
                                   "curve": [(s_, sum(v) / len(v)) for s_, v in sorted(cohort_scores.items())],
                                   "change": heldout.paired_bootstrap(cohort_scores[first_c], cohort_scores[last_c],
                                                                      seed=seed)}
    if extra_max_new:
        e0, e1 = extra_evals[0], extra_evals[int(t["steps"])]
        summary["extra_eval"] = {"max_new": extra_max_new,
                                 "start": {k_: v for k_, v in e0.items() if k_ != "scores"},
                                 "end": {k_: v for k_, v in e1.items() if k_ != "scores"},
                                 "change": heldout.paired_bootstrap(e0["scores"], e1["scores"], seed=seed)}
    if adapter is not None:
        m = adapter.manifest
        summary["team5_adapter"] = {k_: m.get(k_) for k_ in ("status", "mode", "model_hash_g5", "model_spec_sha256",
                                                            "learning_report_allowed")}
        summary["team5_adapter"].update(g5_commit=m["g5"]["commit"], checkpoint_sha256=m["checkpoint"]["sha256"],
                                        tokenizer_sha256=m["tokenizer"]["sha256"], ke2=m["ke2"],
                                        router_names=m["selection"]["router_names"],
                                        trainable_names=m["selection"]["trainable_names"])
    if fixture_smoke:  # fixture: a smoke record, never a learning report
        summary["status"] = "FIXTURE_SMOKE_NOT_A_RESULT"
        (out / "smoke_summary.json").write_text(json.dumps(summary, indent=1))
    else:
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
    if not summary["router_unchanged"] and not router_trainable:
        raise RuntimeError("router checksum changed during RL")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--steps", type=int, help="override train.steps")
    ap.add_argument("--model-path", help="override model.path (a local checkpoint folder)")
    ap.add_argument("--device", help="override device (cpu, cuda, mps)")
    args = ap.parse_args(argv)
    cfg = yaml.safe_load(args.config.read_text())
    if args.out_dir:
        cfg["out_dir"] = str(args.out_dir)
    if args.steps:
        cfg["train"]["steps"] = args.steps
    if args.model_path:
        cfg["model"]["path"] = args.model_path
    if args.device:
        cfg["device"] = args.device
    try:
        s = train(cfg)
    except Exception as e:
        if type(e).__name__ != "WaitingForArtifact":
            raise
        out = Path(cfg.get("out_dir", "out"))
        out.mkdir(parents=True, exist_ok=True)
        rec = {"status": e.result.status, "reasons": e.result.reasons, "manifest": e.result.manifest}
        (out / "status.json").write_text(json.dumps(rec, indent=1, default=str))
        print(json.dumps({"status": e.result.status, "reasons": e.result.reasons}))
        return 3
    print(json.dumps({k: v for k, v in s.items() if k != "heldout_curve"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
