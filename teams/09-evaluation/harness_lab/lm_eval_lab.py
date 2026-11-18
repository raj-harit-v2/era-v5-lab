"""eval-mini on a Team 5 lab model: the lm-eval model class, the task-group runner, and the scorer that
``run_lab_ckpt.py --scorer lm_eval_lab:team5`` loads (``eval_watcher.py`` runs that on every new checkpoint).

LabLM follows lm_eval's HF model (HFLM) for log-likelihood requests, as teams/12-quantization/eval_mini/llamacpp_lm.py
does for GGUF files: trailing spaces of the context move to the continuation, the continuation tokens are the tail of
the jointly tokenized string, the sequence is left-truncated to the model's context, and the score is the summed
log-probability of the continuation tokens. Like Team 5's training windows (week2/data.py), every sequence starts with
the BOS token <|begin_of_text|>.

Speed (course rule of 13 Nov: batched operations, no Python loop over tokens, no avoidable host-device syncs):
- each distinct text is tokenized once, in one batched tokenizer call per request list;
- requests with the same input tokens share one forward row (the answer letters of a multiple-choice item);
- rows are sorted by length and batched under --max-batch-tokens, right-padded with the `valid` mask (attention is
  causal and the MoE skips invalid rows, so padding does not change a real position);
- the output head runs only on the continuation positions, in chunks, so a 131,072-way softmax is never built for the
  whole batch, and each batch makes one device-to-host copy;
- lm-eval indexes only the task folders in eval_lab_v1.yaml, and its per-call environment report (pip list, OS queries,
  git) is skipped.

    # what the watcher runs for each checkpoint (Tier A = the freeze set; Tier B = the labelled diagnostics)
    python teams/09-evaluation/harness_lab/run_lab_ckpt.py --run-dir <remote_root>/<run_id> --step <N> --device cuda \\
        --scorer lm_eval_lab:team5 --out <file> --model-config <arm.yaml | manifest.json> --tokenizer <tokenizer.json> \\
        --tokenizer-sha256 <sha256> --byte-table <raw table .npz> --tier A --hf-home <HF cache> --offline

Firewall (firewall/eval_firewall.md, section 3): with --offline it needs no network, reads only its inputs, never logs
samples or prompts, and writes scores only. Token ids are cached in memory for one process and never written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import platform
import sys
import time
from contextlib import contextmanager, nullcontext
from importlib import metadata
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from lm_eval.api.model import LM  # imports neither datasets nor huggingface_hub, so --hf-home still takes effect

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent                                                # teams/09-evaluation
HARNESS05 = TEAM.parent / "05-architecture" / "harness"           # Team 5's week2 package, used as is
TASKS_DIR = TEAM / "harness_code_indic" / "tasks"                 # MILU task configs
LM_EVAL_TASKS = Path(sys.modules[LM.__module__].__file__).resolve().parents[1] / "tasks"
HEAD_CHUNK_BYTES = 256 << 20         # fp32 logits per output-head chunk (512 positions at a 131,072 vocabulary)
PROBE_SHAPE, PROBE_SEED = (2, 32), 1234
TIER_ROLE = {"A": ("freeze",), "B": ("diagnostic",), "AB": ("freeze", "diagnostic")}


def split_pair(context: str, continuation: str) -> tuple[str, str]:
    """HFLM's rule: trailing whitespace of the context belongs to the continuation."""
    n = len(context) - len(context.rstrip())
    return (context[:-n], context[-n:] + continuation) if n else (context, continuation)


class LabLM(LM):
    def __init__(self, model, artifacts, block_size: int, device, bf16: bool, max_batch_tokens: int = 16384,
                 head_rows: int | None = None):
        super().__init__()
        self.model, self.art, self.block = model, artifacts, int(block_size)
        self._device = torch.device(device)    # lm_eval's LM exposes it as the read-only property `device`
        self.autocast = (lambda: torch.autocast(device_type="cuda", dtype=torch.bfloat16)) if bf16 else nullcontext
        self.bos, self.pad = artifacts.bos_id, artifacts.pad_id
        self.max_batch_tokens = int(max_batch_tokens)
        self.head_rows = int(head_rows or max(1, HEAD_CHUNK_BYTES // (4 * model.head.out_features)))
        self.encode_fallbacks = 0      # distinct texts whose ids do not rebuild the exact UTF-8 (Team 5's strict check)
        self.requests_scored = 0
        self.rows_scored = 0
        self._ids: dict[str, np.ndarray] = {"": np.zeros(0, dtype=np.int64)}

    # ------------------------------------------------------------------ tokenization
    def _encode_many(self, texts) -> None:
        """Token ids of every text not seen yet. The ids are the tokenizer's, as with Team 5's Artifacts.encode. A text
        whose ids do not rebuild its exact UTF-8 bytes from the byte table is counted: Artifacts.encode refuses it, and
        #387 then took the same tokenizer ids."""
        new = [t for t in dict.fromkeys(texts) if t not in self._ids]
        if not new:
            return
        table, lengths = self.art.bytes, self.art.lengths
        cols = np.arange(table.shape[1])
        for text, enc in zip(new, self.art.tokenizer.encode_batch(new, add_special_tokens=False)):
            ids = np.asarray(enc.ids, dtype=np.int64)
            if table[ids][cols < lengths[ids][:, None]].tobytes() != text.encode("utf-8"):
                self.encode_fallbacks += 1
            self._ids[text] = ids

    # ------------------------------------------------------------------ scoring
    def loglikelihood(self, requests, disable_tqdm: bool = False):
        pairs = [split_pair(*req.args) for req in requests]
        self._encode_many([c for c, _ in pairs] + [c + x for c, x in pairs])
        rows, row_of, members, targets = [], {}, [], []
        for i, (context, continuation) in enumerate(pairs):
            ctx = self._ids[context]
            cont = self._ids[context + continuation][len(ctx):]
            if not len(cont):
                raise ValueError("a continuation produced no tokens")
            toks = np.concatenate(([self.bos], ctx, cont))[-(self.block + 1):]      # left-truncate, as HFLM does
            n = min(len(cont), len(toks) - 1)
            inputs = toks[:-1]
            j = row_of.setdefault(inputs.tobytes(), len(rows))
            if j == len(rows):
                rows.append(inputs)
                members.append([])
            members[j].append(i)
            targets.append(toks[-n:])                     # position p of the row predicts token p + 1
        lens = np.fromiter(map(len, rows), dtype=np.int64, count=len(rows))
        out = [None] * len(pairs)
        batch: list[int] = []
        for j in np.argsort(-lens, kind="stable").tolist():
            if batch and (len(batch) + 1) * int(lens[batch[0]]) > self.max_batch_tokens:
                self._score_rows(batch, rows, lens, members, targets, out)
                batch = []
            batch.append(j)
        if batch:
            self._score_rows(batch, rows, lens, members, targets, out)
        self.requests_scored += len(pairs)
        self.rows_scored += len(rows)
        return out

    def _score_rows(self, batch, rows, lens, members, targets, out) -> None:
        dev, width = self._device, int(lens[batch[0]])
        blen = lens[batch]
        ids = np.full((len(batch), width), self.pad, dtype=np.int64)
        for k, j in enumerate(batch):
            ids[k, : blen[k]] = rows[j]
        reqs = [i for j in batch for i in members[j]]
        per_row = np.fromiter((len(members[j]) for j in batch), dtype=np.int64, count=len(batch))
        n = np.fromiter((len(targets[i]) for i in reqs), dtype=np.int64, count=len(reqs))
        starts = np.cumsum(n) - n
        end = np.repeat(np.arange(len(batch)) * width + blen, per_row)            # flat index just past each input row
        pos = np.repeat(end - n - starts, n) + np.arange(int(n.sum()))             # every continuation position
        tgt = torch.from_numpy(np.concatenate([targets[i] for i in reqs])).to(dev)
        ids_t = torch.from_numpy(ids).to(dev)
        valid = torch.arange(width, device=dev)[None, :] < torch.from_numpy(blen).to(dev)[:, None]
        with torch.inference_mode(), self.autocast():
            hidden = self.model.hidden(ids_t, valid)
            picked = hidden.reshape(-1, hidden.shape[-1]).index_select(0, torch.from_numpy(pos).to(dev))
            logp_t, hit = [], []
            for a in range(0, len(pos), self.head_rows):
                logp = torch.log_softmax(self.model.head(picked[a: a + self.head_rows]).float(), dim=-1)
                t = tgt[a: a + self.head_rows]
                logp_t.append(logp.gather(1, t[:, None]).squeeze(1))
                hit.append(logp.argmax(-1).eq(t))
            both = torch.stack((torch.cat(logp_t), torch.cat(hit).float())).cpu().numpy()   # the one copy per batch
        sums = np.add.reduceat(both[0].astype(np.float64), starts)
        greedy = np.logical_and.reduceat(both[1] > 0.5, starts)
        for i, s, g in zip(reqs, sums.tolist(), greedy.tolist()):
            out[i] = (s, g)

    def loglikelihood_rolling(self, requests, disable_tqdm: bool = False):
        raise NotImplementedError("eval_lab_v1 has no perplexity tasks")

    def generate_until(self, requests, disable_tqdm: bool = False):
        raise NotImplementedError("eval_lab_v1 scores log-likelihood tasks only (no generation)")


# ---- lm-eval task groups ---------------------------------------------------------------------------------------------

def _n_items(res, task):
    ns = res.get("n-samples", {})
    if task in ns:
        return {"effective": ns[task]["effective"], "original": ns[task]["original"]}
    # A group (mmlu): this call evaluated only that group, so its leaf tasks are all the n-samples entries.
    return {"effective": sum(v["effective"] for v in ns.values()), "original": sum(v["original"] for v in ns.values())}


@contextmanager
def without_env_report():
    """lm-eval's simple_evaluate ends every call with torch's collect_env (pip list and OS queries) and a git lookup,
    for result fields (pretty_env_info, git_hash) this scorer never writes: 16 s on the first call and 5 s on each
    later one on the laptop, 2 calls for Tier A and 4 for Tier B. They are skipped for the calls made here."""
    import lm_eval.evaluator as ev

    saved = ev.add_env_info, ev.get_git_commit_hash
    ev.add_env_info, ev.get_git_commit_hash = (lambda results: None), (lambda: None)
    try:
        yield
    finally:
        ev.add_env_info, ev.get_git_commit_hash = saved


def check_lm_eval_version(cfg: dict) -> None:
    """The task folders, prompts and default seeds of eval_lab_v1.yaml are lm-eval's at one version, the one the
    lm-eval records of results/eval_mini_v1.json used; another version can change the numbers without an error."""
    have, want = metadata.version("lm_eval"), str(cfg["lm_eval_version"])
    if have != want:
        raise SystemExit(f"eval_lab_v1.yaml pins lm-eval {want}; this environment has {have}")


_TASK_MANAGERS = {}


def task_manager(paths, include_defaults: bool = True):
    """One lm-eval TaskManager per process and path set. The default index opens every task YAML (about 14,000 files in
    lm-eval 0.4.13); with include_defaults=False only the listed folders are read."""
    key = (tuple(str(p) for p in paths), include_defaults)
    if key not in _TASK_MANAGERS:
        from lm_eval.tasks import TaskManager

        _TASK_MANAGERS[key] = TaskManager(include_path=[str(p) for p in paths], include_defaults=include_defaults)
    return _TASK_MANAGERS[key]


def evaluate_group(lm, group, spec, tm, limit=None):
    """Yield (task entry, {"results", "n"}) for every task of one config group. Never logs samples or prompts."""
    import lm_eval

    s = group["seed"]
    common = dict(model=lm, task_manager=tm, log_samples=False, write_out=False, apply_chat_template=False,
                  fewshot_as_multiturn=False, random_seed=s["random"], numpy_random_seed=s["numpy"],
                  torch_random_seed=s["torch"], fewshot_random_seed=s["fewshot"])
    if group["items"] == "limit":
        # Same as harness/run_eval_mini.py: one call per task, lm-eval's first-N items, the task's own 0-shot config.
        for e in group["tasks"]:
            n = min(limit, e["limit"]) if limit else e["limit"]
            print(f"  scoring {e['task']} (limit {n})", flush=True)
            with without_env_report():
                res = lm_eval.simple_evaluate(tasks=[e["task"]], num_fewshot=e["num_fewshot"] or None, limit=n,
                                              **common)
            yield e, {"results": res["results"], "n": {e["task"]: _n_items(res, e["task"])}}
    else:
        # Same as harness_code_indic/run_lm_eval.py with the eval-mini spec: the spec's doc ids, grouped by shot count.
        by_shot = {}
        for e in group["tasks"]:
            by_shot.setdefault(e["num_fewshot"], []).append(e)
        for shot, entries in by_shot.items():
            names = [e["task"] for e in entries]
            print(f"  scoring {', '.join(names)} ({shot}-shot, spec items)", flush=True)
            samples = {t: spec["tasks"][t]["doc_ids"][:limit] if limit else spec["tasks"][t]["doc_ids"] for t in names}
            with without_env_report():
                res = lm_eval.simple_evaluate(tasks=names, num_fewshot=shot, samples=samples, **common)
            for e in entries:
                yield e, {"results": res["results"], "n": {e["task"]: _n_items(res, e["task"])}}


def points_or_none(x):
    """lm-eval gives a stderr as a fraction, "N/A", or NaN when it cannot compute one (for example 2 items in a test);
    the v1 schema wants points or null."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(100 * v, 2) if math.isfinite(v) else None


def records_for(entry, res, group, spec_sha, label, limit, test_note, common):
    """The v1 record fields of one task (acc, and acc_norm where lm-eval gives it), as #387's run_team5_runs.py."""
    task, r, n = entry["task"], res["results"][entry["task"]], res["n"][entry["task"]]
    if limit:
        item_set = f"limit:{limit}"
    elif group["items"] == "spec":
        item_set = f"spec:{spec_sha}"
    else:
        item_set = f"limit:{entry['limit']}"
    notes = [label["diagnostic"] if entry["role"] == "diagnostic" else label["freeze"]] + test_note
    return [{**common, "task": task, "metric": m, "filter": "none", "primary": m == entry["primary"],
             "value": round(100 * r[f"{m},none"], 2), "stderr": points_or_none(r.get(f"{m}_stderr,none")),
             "n_items": n["effective"], "n_items_total": n["original"], "item_set": item_set, "profile": group["profile"],
             "num_fewshot": entry["num_fewshot"], "seed": dict(group["seed"]), "notes": notes}
            for m in ("acc", "acc_norm") if f"{m},none" in r]


# ---- the Team 5 model ------------------------------------------------------------------------------------------------

def week2():
    if str(HARNESS05) not in sys.path:
        sys.path.append(str(HARNESS05))
    from week2.artifacts import Artifacts
    from week2.model import LanguageModel

    return Artifacts, LanguageModel


def load_model_config(path: Path, runtime: Path | None = None, resolution: Path | None = None) -> dict:
    """Team 5's model map: from a run's manifest.json (``config.model``), a JSON model map, or an arm YAML resolved with
    week2/config.py ``load_runtime`` (plus ``--resolution``, applied as train_week2.py applies it)."""
    week2()
    if path.suffix == ".json":
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc["config"]["model"] if "config" in doc else doc.get("model", doc)
    from week2.config import load, load_runtime

    cfg = load_runtime(path, runtime)
    if resolution:
        from train_week2 import apply_resolution

        cfg = apply_resolution(cfg, load(resolution))
    return cfg["model"]


def build_model(m: dict, art):
    """A fresh Team 5 LanguageModel on CPU (the checkpoint's weights are loaded into it)."""
    _, LanguageModel = week2()
    torch.manual_seed(0)
    return LanguageModel(m, art.bytes, art.lengths)


def probe_loss(model) -> float:
    """Next-token loss on a fixed seeded batch: the probe a trainer passes to Team 7's Checkpointer.save, which
    export_safetensors compares with the saved bits when they were made on the same device class."""
    vocab = model.head.out_features
    ids = torch.randint(0, vocab, PROBE_SHAPE, generator=torch.Generator().manual_seed(PROBE_SEED))
    ids = ids.to(next(model.parameters()).device)
    model.eval()
    with torch.no_grad():
        logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
    return F.cross_entropy(logits[:, :-1].reshape(-1, vocab).float(), ids[:, 1:].reshape(-1)).item()


def text_bytes(path: Path) -> bytes:
    """A text file's bytes with LF line endings: what git stores, so a Windows checkout with core.autocrlf=true
    gives the same sha256 as Linux."""
    return path.read_bytes().replace(b"\r\n", b"\n")


class Team5Scorer:
    """The scorer contract of run_lab_ckpt.py (see its docstring) for a Team 5 LanguageModel."""

    name = "lm_eval"

    def __init__(self, a: argparse.Namespace):
        # Environment first: datasets and huggingface_hub read these at import time, and nothing above imports them.
        if a.hf_home:
            os.environ["HF_HOME"] = str(a.hf_home.resolve())
        if a.offline:
            os.environ["HF_DATASETS_OFFLINE"] = "1"
            os.environ["HF_HUB_OFFLINE"] = "1"
        # Off, as in #387. On, batched encoding was 4.6x faster at 5-shot sizes (about 8 s a Tier A checkpoint on CPU),
        # but the first CPU log run with it on hung once in hellaswag (stopped by --timeout; 5 reruns did not hang).
        # The cause is not proven, so the setting with no hang in any run stays.
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
        for name in ("lm-eval", "lm_eval", "transformers", "huggingface_hub", "urllib3"):
            logging.getLogger(name).setLevel(logging.WARNING)
        import datasets
        import yaml

        # offline, datasets logs two "using the cached version" lines per dataset config: 244 of 332 lines of a Tier A log
        datasets.utils.logging.set_verbosity_error()

        self.a = a
        t0 = time.perf_counter()
        cfg = yaml.safe_load(a.eval_config.read_text(encoding="utf-8"))
        check_lm_eval_version(cfg)
        self.label = cfg["labels"]
        spec_path = TEAM / cfg["spec"]["path"]
        spec = text_bytes(spec_path)
        self.spec_sha = hashlib.sha256(spec).hexdigest()
        if self.spec_sha != cfg["spec"]["sha256"]:
            raise SystemExit(f"{spec_path}: sha256 {self.spec_sha} differs from the config ({cfg['spec']['sha256']})")
        self.spec = json.loads(spec)
        roles = TIER_ROLE[a.tier]
        groups = [dict(g, tasks=[e for e in g["tasks"] if e["role"] in roles]) for g in cfg["groups"]]
        self.groups = [g for g in groups if g["tasks"]]
        self.guard = cfg["guard"]
        self.task_dirs = [TASKS_DIR] + [LM_EVAL_TASKS / d for d in cfg["lm_eval_task_dirs"]]
        self.m = load_model_config(a.model_config, a.runtime, a.resolution)
        Artifacts, _ = week2()
        self.art = Artifacts(a.tokenizer, a.byte_table, expected_tokenizer_sha=a.tokenizer_sha256,
                             expected_vocab=self.m["vocab_size"])
        if self.art.pos_dim != self.m["ke_max_pos"]:
            raise SystemExit(f"byte table P {self.art.pos_dim} differs from the model's ke_max_pos {self.m['ke_max_pos']}")
        self.script_sha = hashlib.sha256(text_bytes(Path(__file__))).hexdigest()
        self.setup_s = time.perf_counter() - t0

    def check(self, manifest: dict) -> None:
        """The checkpoint must have been trained with the tokenizer given: Team 7's MANIFEST.json keeps it in
        env.tokenizer_sha, a Team 5 run's manifest.json in artifacts.tokenizer_sha256."""
        saved = ((manifest.get("env") or {}).get("tokenizer_sha")
                 or (manifest.get("artifacts") or {}).get("tokenizer_sha256") or "unknown")
        if saved != "unknown" and saved != self.a.tokenizer_sha256:
            raise SystemExit(f"the checkpoint was trained with tokenizer {saved[:12]}, not {self.a.tokenizer_sha256[:12]}")

    def factory(self):
        return build_model(self.m, self.art)

    def probe(self, model) -> float:
        return probe_loss(model)

    def score(self, model, device: str) -> list[dict]:
        a, dev = self.a, torch.device(device)
        # lab runs train in bf16 on GPU (Team 5's quality-run rule); a GPU without native bf16, and the CPU, use fp32
        bf16 = dev.type == "cuda" and torch.cuda.is_bf16_supported(including_emulation=False)
        model.to(dev).eval()
        hardware = torch.cuda.get_device_name(dev) if dev.type == "cuda" else (platform.processor() or platform.machine())
        common = {"format": "bf16" if bf16 else "fp32", "dtype": "bfloat16" if bf16 else "float32",
                  "decoding": "loglikelihood", "derived_from": None, "hardware": hardware,
                  "harness": {"name": "lm_eval", "version": metadata.version("lm_eval"),
                              "script_sha256": self.script_sha}}
        test_note = [f"TEST RUN (--limit {a.limit}): not a result"] if a.limit else []
        lm = LabLM(model, self.art, block_size=self.m["block_size"], device=dev, bf16=bf16,
                   max_batch_tokens=a.max_batch_tokens)
        t0 = time.perf_counter()
        tm = task_manager(self.task_dirs, include_defaults=False)
        index_s = time.perf_counter() - t0
        missing = [e["task"] for g in self.groups for e in g["tasks"] if e["task"] not in tm.all_tasks]
        if missing:
            raise SystemExit(f"lm-eval tasks not found under {[str(p) for p in self.task_dirs]}: {missing}")
        records = []
        for g in self.groups:
            for entry, res in evaluate_group(lm, g, self.spec, tm, a.limit):
                records += records_for(entry, res, g, self.spec_sha, self.label, a.limit, test_note, common)
        score_s = time.perf_counter() - t0 - index_s
        print(f"lm-eval ({hardware}, {common['format']}): {lm.requests_scored} requests in {lm.rows_scored} forward "
              f"rows, encode fallbacks {lm.encode_fallbacks}; setup {self.setup_s:.1f} s, task index {index_s:.1f} s, "
              f"scoring {score_s:.1f} s", flush=True)
        self.print_guard(records)
        return records

    def print_guard(self, records) -> None:
        """Pooled freeze-set accuracy over the items scored (decision 3 of results/config_freeze_proposal.md)."""
        freeze = {r["task"]: r for r in records if r["primary"] and r["task"] in self.guard["expected_items"]}
        if not freeze:
            return
        n = sum(r["n_items"] for r in freeze.values())
        pooled = round(sum(r["value"] * r["n_items"] for r in freeze.values()) / n, 2)
        complete = not self.a.limit and all(t in freeze and freeze[t]["n_items"] == k
                                            for t, k in self.guard["expected_items"].items())
        print(f"GUARD pooled freeze-set accuracy {pooled} on {n} items, complete {complete}, "
              f"below the {self.guard['pooled_floor']} floor {pooled < self.guard['pooled_floor']}", flush=True)


def team5(argv: list[str]) -> Team5Scorer:
    """``run_lab_ckpt.py --scorer lm_eval_lab:team5``: the arguments run_lab_ckpt.py does not know come here."""
    ap = argparse.ArgumentParser(prog="run_lab_ckpt.py --scorer lm_eval_lab:team5", allow_abbrev=False,
                                 description="eval-mini on a Team 5 LanguageModel checkpoint")
    ap.add_argument("--model-config", type=Path, required=True,
                    help="the run's manifest.json, a JSON model map, or the arm YAML it trains (configs/arms/...)")
    ap.add_argument("--runtime", type=Path, help="Team 5 runtime.yaml for an arm YAML (default: Team 5's own)")
    ap.add_argument("--resolution", type=Path, help="Team 5 resolution file the run used, for an arm YAML")
    ap.add_argument("--tokenizer", type=Path, required=True, help="the frozen tokenizer.json the run trains with")
    ap.add_argument("--tokenizer-sha256", required=True,
                    help="its sha256 (frozen p1536, Gate 3 notice of 15 Nov: e6b93a93...25a64b; C3 sample-v0, archived: "
                         "15468e66...02ddc3)")
    ap.add_argument("--byte-table", type=Path, required=True,
                    help="Team 4's raw table for that tokenizer (.npz); p1536: "
                         "teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz")
    ap.add_argument("--tier", choices=sorted(TIER_ROLE), default="A",
                    help="A: the freeze set (970 items); B: the labelled diagnostics (1,500 items); AB: both")
    ap.add_argument("--eval-config", type=Path, default=HERE / "eval_lab_v1.yaml", help="task list, items and seeds")
    ap.add_argument("--hf-home", type=Path, help="Hugging Face cache with the datasets (HF_HOME)")
    ap.add_argument("--offline", action="store_true", help="no network: HF_DATASETS_OFFLINE=1 and HF_HUB_OFFLINE=1")
    ap.add_argument("--max-batch-tokens", type=int, default=16384, help="padded tokens per forward pass")
    ap.add_argument("--limit", type=int, help="TEST ONLY: first N items per task (N per subject for MMLU)")
    return Team5Scorer(ap.parse_args(argv))
