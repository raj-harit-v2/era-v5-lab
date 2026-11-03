"""Run lm-evaluation-harness for one model and record everything needed to reproduce the numbers.

Usage (from this folder):
    python -u run_lm_eval.py --model qwen2.5-1.5b --tasks leaderboard_mmlu_pro --tag gate_leaderboard_mmlu_pro
    python -u run_lm_eval.py --model gemma-2-2b --tasks milu_Hindi --num-fewshot 5 --limit 20 --tag probe
    python -u run_lm_eval.py --model llama-3.2-3b --samples-file eval_mini_v0_spec.json --tag eval_mini_v0

Models and their pinned revisions come from published_scores.json. MILU task configs are loaded from ./tasks.
Results go to ./runs/<model>/<tag>/results.json (gitignored). Per-sample logs, if asked for, go next to them.
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "decontam"))  # append: decontam/registry.py must not shadow other modules
from lab_canary import stamp  # noqa: E402  the lab canary goes on every logged sample (they hold the items)
RUNS = HERE / "runs"  # gitignored (.gitignore in this folder); never commit run outputs, caches or samples


def gpu_state():
    """SM clock, temperature and power state now. This laptop throttles and pages, so every number carries its clock."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,clocks.sm,temperature.gpu,memory.used,memory.total",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.strip()
        name, sm, temp, used, total = [x.strip() for x in out.split(",")]
        state = {"gpu": name, "sm_clock_mhz": int(sm), "temp_c": int(temp), "mem_used_mib": int(used), "mem_total_mib": int(total)}
    except Exception as e:
        state = {"error": repr(e)}
    if platform.system() == "Windows":
        try:
            ps = ("(Get-CimInstance -Namespace root/wmi -ClassName BatteryStatus | Select-Object -First 1).PowerOnline;"
                  "(powercfg /getactivescheme) -replace '.*\\((.*)\\).*', '$1'")
            online, scheme = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                            capture_output=True, text=True, timeout=20).stdout.split()[:2]
            state["on_ac"], state["power_plan"] = online == "True", scheme
        except Exception:
            pass
    return state


def keep_awake():
    """Ask Windows not to sleep while this process runs. No power setting changes; the request ends with the process.
    ES_SYSTEM_REQUIRED alone does not stop Modern Standby on this laptop: on 26 Oct it entered standby at 03:36 when the
    screen timed out and suspended a run until 07:27. ES_DISPLAY_REQUIRED keeps the display awake, which blocks idle
    standby. Closing the lid can still put the machine to sleep."""
    if platform.system() == "Windows":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)  # CONTINUOUS | SYSTEM | DISPLAY


def cap_vram():
    """Turn silent paging into a real OOM: the WDDM driver otherwise spills VRAM to host RAM."""
    import torch
    if torch.cuda.device_count() == 0:
        return None
    free, total = torch.cuda.mem_get_info()
    fraction = free / total
    torch.cuda.set_per_process_memory_fraction(fraction)
    return round(fraction, 3)


def keep_only_scored_logits(keep=512):
    """lm-eval's HF backend computes logits for every position, but only the continuation is scored. On 8 GB that
    OOMs gemma-2-2b (256k vocab: about 3.3 GB per 6.4k-token prompt, twice over with log_softmax) and Llama-3.2-3B
    (6.4 GB of weights). At batch size 1, lm-eval slices the continuation relative to the returned length
    (ctx_len = inplen + logits.shape[0] - padding_len_inp), so returning only the last `keep` positions selects the
    same logits. use_cache=False drops the unused KV cache. A guard stops the run if a continuation ever exceeds `keep`."""
    import torch
    from lm_eval.models.huggingface import HFLM
    original_call, original_select = HFLM._model_call, HFLM._select_cont_toks

    def _model_call(self, inps, attn_mask=None, labels=None):
        if attn_mask is not None or labels is not None or inps.shape[0] != 1:
            return original_call(self, inps, attn_mask, labels)
        with torch.no_grad():
            return self.model(inps, logits_to_keep=min(keep, inps.shape[1]), use_cache=False).logits

    def _select_cont_toks(self, logits, contlen=None, inplen=None):
        if self.backend == "causal" and inplen is not None and contlen is not None and inplen - contlen < 0:
            raise RuntimeError(f"continuation of {contlen} tokens is longer than the {logits.shape[0]} kept logits; raise keep")
        return original_select(self, logits, contlen=contlen, inplen=inplen)

    HFLM._model_call, HFLM._select_cont_toks = _model_call, _select_cont_toks


GENERATION_CAP_LOG = []


def apply_generation_cap():
    """Make lm-eval's own generation cap (max_gen_toks, 256 for GSM8K) apply. Qwen2.5 ships max_new_tokens=2048 in its
    generation_config.json, and transformers lets that win over the max_length lm-eval passes to generate(), so
    generations run far longer than a standard lm-eval run and the answer filter sees different text. Clearing it
    restores lm-eval's documented behaviour. Found by Mahesh Sv (PR #21, apply_generation_cap); same logic here.
    Affects generation tasks only; log-likelihood tasks never call generate()."""
    from lm_eval.models.huggingface import HFLM
    original = HFLM.__init__

    def __init__(self, *args, **kwargs):
        original(self, *args, **kwargs)
        gc = getattr(getattr(self, "model", None), "generation_config", None)
        if gc is None:
            return
        if gc.max_new_tokens is not None:
            GENERATION_CAP_LOG.append(f"cleared generation_config.max_new_tokens={gc.max_new_tokens}")
            gc.max_new_tokens = None
        if gc.max_length not in (None, 20):
            GENERATION_CAP_LOG.append(f"reset generation_config.max_length={gc.max_length} to 20")
            gc.max_length = 20  # transformers' default; lm-eval sets the real limit per call

    HFLM.__init__ = __init__


def use_memory_efficient_sdpa():
    """This PyTorch build (Windows, cu126) has no flash SDPA kernel, and its memory-efficient kernel rejects enable_gqa.
    For grouped-query models (Llama-3.2, Qwen2.5), transformers passes enable_gqa=True when there is no mask, so SDPA
    falls back to the math kernel and builds the full attention matrix: about 1.5 GiB per layer for Llama-3.2-3B at
    4096 tokens, which OOMs. Repeating the KV heads first (transformers' own path when a mask is present) lets the
    memory-efficient kernel run. Same computation, different kernel. gemma-2 uses eager attention and is unaffected."""
    import transformers.integrations.sdpa_attention as sdpa
    sdpa.use_gqa_in_sdpa = lambda attention_mask, key, value: False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="key in published_scores.json 'models'")
    ap.add_argument("--tasks", help="comma-separated lm-eval task names")
    ap.add_argument("--samples-file", help="eval-mini spec: JSON with {'tasks': {task: {'doc_ids': [...], 'num_fewshot': n}}}")
    ap.add_argument("--num-fewshot", type=int)
    ap.add_argument("--limit", type=int, help="first N docs per task (probes only; never for gate runs)")
    ap.add_argument("--batch-size", default="1", help="1 on 8 GB: full-sequence logits (152k-256k vocab) OOM at 4, and 'auto' undersizes")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--log-samples", action="store_true")
    ap.add_argument("--full-logits", action="store_true", help="disable keep_only_scored_logits (equivalence tests only)")
    ap.add_argument("--gqa-math-kernel", action="store_true", help="disable use_memory_efficient_sdpa (equivalence tests only)")
    a = ap.parse_args()
    if a.batch_size != "1" and not a.full_logits:
        ap.error("keep_only_scored_logits is only correct at --batch-size 1")

    spec = json.loads((HERE / "published_scores.json").read_text(encoding="utf-8"))
    m = spec["models"][a.model]
    from fetch_weights import local_dir
    weights = local_dir(m["hf_id"], m["revision"])
    if (weights / "SOURCE.json").exists():  # verified local copy of the pinned revision (see fetch_weights.py)
        model_args = f"pretrained={weights.as_posix()},dtype=bfloat16"
    else:
        model_args = f"pretrained={m['hf_id']},revision={m['revision']},dtype=bfloat16"
    model_args += f",max_length={m['max_length']}"  # same context limit (and so the same truncation) as the anchor runs
    if a.model.startswith("gemma-2"):
        model_args += ",attn_implementation=eager"  # gemma-2 logit soft-capping needs eager attention; the anchor run used it

    samples, fewshot_by_task = None, {}
    if a.samples_file:
        mini = json.loads(Path(a.samples_file).read_text(encoding="utf-8"))
        samples = {t: v["doc_ids"] for t, v in mini["tasks"].items()}
        fewshot_by_task = {t: v.get("num_fewshot") for t, v in mini["tasks"].items()}
        tasks = list(samples)
    else:
        tasks = [t.strip() for t in a.tasks.split(",") if t.strip()]

    out_dir = RUNS / a.model / a.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    keep_awake()
    fraction = cap_vram()

    import lm_eval
    from lm_eval.tasks import TaskManager

    if not a.full_logits:
        keep_only_scored_logits()
    if not a.gqa_math_kernel:
        use_memory_efficient_sdpa()
    apply_generation_cap()

    tm = TaskManager(include_path=str(HERE / "tasks"))
    groups = {}
    for nshot in sorted({fewshot_by_task.get(t, a.num_fewshot) for t in tasks}, key=lambda x: -1 if x is None else x):
        groups[nshot] = [t for t in tasks if fewshot_by_task.get(t, a.num_fewshot) == nshot]

    before, t0, all_results = gpu_state(), time.time(), {}
    for nshot, group in groups.items():
        print(f"[{datetime.now():%H:%M:%S}] {a.model}: {group} num_fewshot={nshot}", flush=True)
        res = lm_eval.simple_evaluate(
            model="hf", model_args=model_args, tasks=group, num_fewshot=nshot, batch_size=a.batch_size,
            use_cache=str(out_dir / "lm_cache"), limit=a.limit,
            samples={t: samples[t] for t in group} if samples else None,
            log_samples=a.log_samples, task_manager=tm, apply_chat_template=False, fewshot_as_multiturn=False,
        )
        for key in ("results", "versions", "n-shot", "n-samples", "higher_is_better"):
            all_results.setdefault(key, {}).update(res.get(key, {}))
        all_results.setdefault("config", res.get("config", {}))
        if a.log_samples:
            with open(out_dir / f"samples_{nshot}.jsonl", "w", encoding="utf-8", newline="\n") as f:
                for task, rows in res.get("samples", {}).items():
                    for row in rows:
                        f.write(json.dumps(stamp({"task": task, **row}), ensure_ascii=False, default=str) + "\n")
    wall = time.time() - t0

    record = {
        "model": a.model, "hf_id": m["hf_id"], "revision": m["revision"], "model_args": model_args, "tag": a.tag,
        "tasks": tasks, "limit": a.limit, "samples_file": a.samples_file, "batch_size": a.batch_size,
        "generation_cap": GENERATION_CAP_LOG or ["no generation_config override present"],
        "scored_logits_only": not a.full_logits, "sdpa_gqa": "math kernel (enable_gqa)" if a.gqa_math_kernel else "repeat_kv + memory-efficient kernel",
        "started_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(timespec="seconds"), "wall_seconds": round(wall, 1),
        "env": {"python": sys.version.split()[0], "platform": platform.platform(), "vram_fraction_cap": fraction,
                **{p: metadata.version(p) for p in ("lm_eval", "torch", "transformers", "accelerate", "datasets")}},
        "gpu_before": before, "gpu_after": gpu_state(),
        **{k: all_results.get(k) for k in ("results", "versions", "n-shot", "n-samples", "higher_is_better")},
    }
    path = out_dir / "results.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"[{datetime.now():%H:%M:%S}] done in {wall / 60:.1f} min -> {path}", flush=True)
    for task, r in record["results"].items():
        print("   ", task, {k: v for k, v in r.items() if isinstance(v, float)})


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
