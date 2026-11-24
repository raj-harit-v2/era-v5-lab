"""G10 first RL job on the dry run 1 checkpoint (Team 5 T2 checkpoint): 10 objective_v1 updates on the RL data v1 code pool.

    G10_STDIO_RUNNER=docker G10_STDIO_SECRET_PATHS=<POOL>/out/v1/cc.jsonl python capstone/rl_job_v1.py \
        --g5-root <lab checkout> --run-folder <dir> --tokenizer tokenizer.json --byte-table raw_table_P32.npz \
        --rl-tasks <POOL>/out/v1/cc.jsonl --train-pool rl-code-v1-train.pool.jsonl --heldout-pool rl-code-v1-heldout.pool.jsonl \
        --sft-arm a4 --packs <shard-0000N>/pack.firewalled.jsonl ... --heldout H.jsonl --device cuda --out out/

One question: do a bounded number of objective_v1 RL updates, on the code pool minus the 66 free-reward and 55 effort-suite
ids, raise the pass rate on unfiltered RL held-out problems, and is the gain more than a format gain? (work/rl-real-job-
request PREREG and its amendments; the request is jobs/2026-11-19-g10-rl-dryrun1.md.)

Steps (each writes out/<step>.json; summary.json last; exit 1 if a step failed; NO_GO is a result, not a failure):
  env      the verifier runner and versions, printed first
  guard    BEFORE the model loads: G10_STDIO_SECRET_PATHS must name the task file given (every path must exist);
           runner local also runs stdio_check.preflight_isolation(); a known pass/wrong check, and a secret-read attack
           (a program that opens the task file and prints the expected output of the test it is given) must score 0
  pins     tokenizer, byte table, run folder, G5 sources, RL pool and the three id files against their pins
  pool     ids: trained pool = train pool - free-reward ids - effort-suite ids (ordered: the probe's easy ids first),
           held-out subset (unfiltered, file order); counts, zero overlap with both exclusion lists asserted
  tricks   the no-skill programs of the 18 Nov verifier audit scored on the screen candidates and the held-out subset
  sft      optional (--sft-arm a2|a4): rebuild #587's arm in-job (its weights are deleted at its exit), or --start-weights
  plan     time table; screen size = largest of 64/128/256 that fits 10 minutes at the measured decode rate;
           if the time left cannot hold screen + 3 updates + the last evaluation: screen only, then stop
  rl       rl-loop/train.py (objective_v1, screen, resumable state, deadline) with a literal-sample detector on the
           held-out evaluations; report.json applies the decision rule. Before the first update the log-prob gate checks
           that the update forward reproduces the sampler's log-probs at identical weights (--no-logprob-gate skips it;
           --update-mode eval is the switch it asks for when a train-only layer such as head dropout breaks it)
Weights, built rows and resumable state are deleted at exit (state only when the run is complete or stopped at the screen).
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import hashlib
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM10 = HERE.parent
sys.path.insert(0, str(TEAM10 / "rl-loop"))
sys.path.insert(0, str(TEAM10 / "rl-data"))
sys.path.insert(0, str(HERE))

import day_one_probe as probe  # noqa: E402

TRAIN_POOL_SHA256 = "cd1aa76ef1216f6fc6fdcf63fc0b69c98fa6a5d58a510f28be9050fecbedcce1"  # rl-code-v1-train.pool.jsonl (#564), 3,251 ids
HELDOUT_POOL_SHA256 = "935857bb0246172aa0439445dd54ef9bbbe282ad2b5ea87ddd100429c9e31ae5"  # rl-code-v1-heldout.pool.jsonl (#564), 255 ids
EASY_IDS_SHA256 = "452178c10e7325bc1cea62b0ad567a68dc32f6596f273b97dc8a36728f985c6f"  # capstone/probe_rl_easy_ids.txt (#587's screen ids)
FREE_IDS_SHA256 = "c97568952d2374be473e747184ea2b23098601797c936aad35363d8e0539aa2e"  # capstone/rl_exclusions_v1/free_reward_ids.txt (66)
# 66 = the 23 of the 18 Nov verifier audit (first 23 lines, unchanged) + 43 found from the kept tests alone by
# rl-data/free_reward_ids.py (one fixed output, or one fixed token per case, passes every scored test); was 3709f52b... (23)
EFFORT_MANIFEST = TEAM10 / "eval" / "effort_manifest.json"  # training_exclusion.task_ids (55)
FREE_IDS = HERE / "rl_exclusions_v1" / "free_reward_ids.txt"
EASY_IDS = HERE / "probe_rl_easy_ids.txt"
MAX_UPDATES = 10          # Amendment 1: updates are capped; more steps on the same cohort buy memorisation (15 Nov, E1)
SCREEN_SIZES = (64, 128, 256)
SCREEN_BUDGET_S = 600.0   # Amendment 1: the screen is the largest size that fits ten minutes
MIN_MIXED = 4
MIN_UPDATES_TO_START = 3  # Amendment 1: fewer than screen + 3 updates + last evaluation left -> save the screen, stop
STDIN_MARKERS = ("input(", "sys.stdin", "open(0", "fileinput", "readline", "os.read(0")

# the no-skill programs of the 18 Nov verifier audit (work/verifier-audit-code-2026-11-18/RESULTS.md); sample-hardcode is
# not rebuilt here: its 13 tasks are among the 66 free-reward ids, which are out of training
TRICKS = {"prints_nothing": "pass", "echo_stdin": "import sys\nsys.stdout.write(sys.stdin.read())", "zero": "print(0)",
          "one": "print(1)", "minus_one": "print(-1)", "YES": "print('YES')", "NO": "print('NO')",
          "Yes": "print('Yes')", "No": "print('No')"}


# ---------------------------------------------------------------------------- pure helpers (unit tested)

def read_ids(path: Path) -> list[str]:
    """One id per line; a tab starts a comment column (free_reward_ids.txt is `id<TAB>trick`); blank and # lines skipped."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.split("\t")[0].split()[0])
    return out


def read_pool_ids(path: Path) -> list[str]:
    return [json.loads(x)["id"] for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def effort_ids(manifest: Path = EFFORT_MANIFEST) -> list[str]:
    return list(json.loads(Path(manifest).read_text(encoding="utf-8"))["training_exclusion"]["task_ids"])


def build_pools(train_ids: list[str], held_ids: list[str], free: list[str], effort: list[str], easy: list[str],
                heldout_n: int = 0) -> dict:
    """Trained pool = train pool minus both exclusion lists, in file order but with the probe's easy ids that are in it
    first (the screen takes the first n; #587's screen walks the same ids). Held-out subset: the first heldout_n ids of the
    held-out pool in file order, never filtered (the free-reward and effort ids in it are counted and kept).
    Raises if the trained pool and held-out share an id, or the trained pool still holds an excluded id."""
    drop = set(free) | set(effort)
    if len(set(train_ids)) != len(train_ids) or len(set(held_ids)) != len(held_ids):
        raise ValueError("duplicate ids in a pool file")
    train = [i for i in train_ids if i not in drop]
    tset = set(train)
    easy_in = [i for i in easy if i in tset]
    seen = set(easy_in)
    ordered = easy_in + [i for i in train if i not in seen]
    held = held_ids[:heldout_n] if heldout_n else list(held_ids)
    if tset & set(held_ids):
        raise ValueError(f"trained pool and held-out pool share {len(tset & set(held_ids))} ids")
    if set(ordered) & drop:
        raise ValueError("trained pool still holds an excluded id")
    counts = {"train_pool_file": len(train_ids), "removed_free": len(set(train_ids) & set(free)),
              "removed_effort": len(set(train_ids) & set(effort)), "trained_pool": len(ordered),
              "heldout_pool_file": len(held_ids), "heldout_subset": len(held),
              "easy_ids": len(easy), "easy_in_trained_pool": len(easy_in), "easy_not_in_trained_pool": len(easy) - len(easy_in),
              "easy_in_heldout_pool_file": len(set(easy) & set(held_ids)),
              "overlap_trained_free": len(set(ordered) & set(free)), "overlap_trained_effort": len(set(ordered) & set(effort)),
              "overlap_trained_heldout": len(set(ordered) & set(held)),
              "heldout_subset_free": len(set(held) & set(free)), "heldout_subset_effort": len(set(held) & set(effort))}
    return {"train_ids": ordered, "heldout_ids": held, "counts": counts}


def pick_screen_n(seconds_per_prompt: float | None, budget_s: float = SCREEN_BUDGET_S, sizes=SCREEN_SIZES) -> dict:
    """Largest of 64/128/256 whose screen (n prompts x k samples decoded together, seconds_per_prompt each) fits the budget.
    Without a rate, or if even the smallest does not fit, the smallest is used and `fits` says so."""
    if not seconds_per_prompt or seconds_per_prompt <= 0:
        return {"n": sizes[0], "fits": None, "basis": "no decode rate given: smallest size"}
    ok = [n for n in sizes if n * seconds_per_prompt <= budget_s]
    return {"n": max(ok) if ok else sizes[0], "fits": bool(ok), "estimated_s": round((max(ok) if ok else sizes[0]) * seconds_per_prompt, 1),
            "basis": f"{seconds_per_prompt:.2f} s per prompt (k samples decoded together), budget {budget_s:.0f} s"}


def time_table(r: float, *, screen_n: int, pps: int, updates: int, heldout_n: int, eval_k: int, k: int, update_s: float,
               score_s: float, fixed_s: float, sft_s: float) -> dict:
    """Seconds per phase from r = seconds to decode one prompt's k samples. Evaluations: heldout_n prompts x eval_k samples
    (decoded in groups of k, so eval_k/k of r each); two of them (step 0 and the last update)."""
    rows = [("fixed (guard, pins, tricks, model load)", fixed_s), ("SFT rebuild of one arm", sft_s),
            (f"screen {screen_n} prompts", screen_n * r + score_s * screen_n),
            (f"{updates} updates ({pps} prompts x {k} samples each)", updates * (pps * r + score_s * pps + update_s)),
            (f"2 evaluations ({heldout_n} prompts x {eval_k})", 2 * heldout_n * r * eval_k / k + 2 * score_s * heldout_n * eval_k / k)]
    return {"rows": [(n, round(s, 1)) for n, s in rows], "total_s": round(sum(s for _, s in rows), 1)}


def enough_time(remaining_s: float, r: float, *, screen_n: int, pps: int, heldout_n: int, eval_k: int, k: int,
                update_s: float, score_s: float) -> dict:
    """Amendment 1 item 4: the screen, 3 updates and the last evaluation must fit in what is left."""
    need = (screen_n * (r + score_s) + MIN_UPDATES_TO_START * (pps * (r + score_s) + update_s)
            + heldout_n * (r + score_s) * eval_k / k)
    return {"remaining_s": round(remaining_s, 1), "needed_s": round(need, 1), "ok": remaining_s >= need}


def reads_stdin(code: str) -> bool:
    return any(m in code for m in STDIN_MARKERS)


def literal_sample(code: str | None, tests: list[dict]) -> str | None:
    """Literal-sample detector for a PASSING program: 'no_stdin' when it never reads stdin (its output cannot depend on
    the input), 'embeds_input' when its source holds a whole test input (4+ characters, raw or with \\n escapes) and so can
    look the answer up. A conservative heuristic: a legitimate program does not contain a test input as a literal."""
    if not code:
        return None
    if not reads_stdin(code):
        return "no_stdin"
    for t in tests:
        s = str(t.get("input", "")).strip()
        if len(s) >= 4 and (s in code or s.replace("\n", "\\n") in code):
            return "embeds_input"
    return None


def boot_ci(values: list[float], n: int = 2000, seed: int = 0) -> dict:
    """Mean with a 95% bootstrap interval over problems (the independent unit)."""
    if not values:
        return {"n": 0, "mean": None, "ci_low": None, "ci_high": None}
    rng = random.Random(seed)
    m = len(values)
    means = sorted(sum(values[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return {"n": m, "mean": round(sum(values) / m, 4), "ci_low": round(means[int(0.025 * n)], 4),
            "ci_high": round(means[int(0.975 * n) - 1], 4)}


def screen_survey(screen: dict) -> dict:
    """The saved survey of a screen: pass rate with an interval over problems, the histogram, and the failure mix
    (reasons are per sample: pass, wrong_answer, timeout, runtime_error, no_code)."""
    k = screen["k"]
    per_problem = [x["passes"] / k for x in screen["per_task"]]
    reasons = screen.get("reasons") or {}
    total = max(sum(reasons.values()), 1)
    return {"problems": len(per_problem), "k": k, "pass_rate": boot_ci(per_problem), "mixed": screen["mixed"],
            "histogram": screen["histogram"], "mixed_threshold": screen["min_mixed"],
            "failure_mix_share": {r: round(v / total, 4) for r, v in sorted(reasons.items())}, "failure_mix_samples": reasons,
            "cut_off_share": screen.get("truncated"), "mean_tokens": screen.get("mean_tokens"),
            "rollout_s": screen["rollout_s"], "score_s": screen["score_s"]}


def decide_rl(change: dict, wrong0: int | None, wrong1: int | None, lit0: float | None, lit1: float | None) -> dict:
    """The preregistered rule, applied mechanically. The literal-sample clause is measured by this job's detector."""
    parts = {"ci_low_above_zero": change["ci_low"] > 0,
             "wrong_answers_not_up": None if wrong0 is None or wrong1 is None else wrong1 <= wrong0,
             "literal_share_not_up": None if lit0 is None or lit1 is None else lit1 <= lit0}
    helps = all(v is True for v in parts.values())
    return {"rl_helps": helps, **parts,
            "reading": "RL helps on the real checkpoint" if helps else
            "the RL path runs on the real checkpoint; no measurable gain at this budget (or a clause failed: see parts)"}


# ---------------------------------------------------------------------------- guard

def attack_program(task_file: Path) -> str:
    """A program that tries to read the expected outputs: opens the task file and prints the output of the test whose
    input it was given. It can only score if the task file is readable from inside the sandbox."""
    return ("import json, sys\n"
            "given = sys.stdin.read().strip()\n"
            f"for line in open({str(task_file)!r}):\n"
            "    r = json.loads(line)\n"
            "    for t in r['tests']:\n"
            "        if t['input'].strip() == given:\n"
            "            print(t['output']); sys.exit()\n")


def guard(a, out: Path) -> dict:
    t0 = time.perf_counter()
    import stdio_check as sc  # noqa: PLC0415
    paths = [p for p in os.environ.get("G10_STDIO_SECRET_PATHS", "").split(os.pathsep) if p]
    if not paths:
        raise RuntimeError("guard refused: G10_STDIO_SECRET_PATHS is not set; it must name the task file (every file with expected outputs)")
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        raise RuntimeError(f"guard refused: G10_STDIO_SECRET_PATHS names a path that does not exist: {missing[0]}")
    if os.path.realpath(a.rl_tasks) not in {os.path.realpath(p) for p in paths}:
        raise RuntimeError(f"guard refused: G10_STDIO_SECRET_PATHS does not name the task file given as --rl-tasks ({a.rl_tasks})")
    res: dict = {"runner": sc.RUNNER_KIND, "secret_paths": len(paths)}
    if sc.RUNNER_KIND == "local":
        sc.preflight_isolation()
        res["preflight_isolation"] = "passed"
    elif sc.RUNNER_KIND != "docker":
        raise RuntimeError(f"guard refused: runner {sc.RUNNER_KIND!r} is not for rewards (use docker, or local as root on Linux)")
    probe_rec = {"id": "guard-known-answer", "tests": [{"input": "7\n", "output": "8\n"}]}
    good = sc.score(probe_rec, "```python\nprint(int(input()) + 1)\n```")["reward"]
    bad = sc.score(probe_rec, "```python\nprint(int(input()) - 1)\n```")["reward"]
    if (good, bad) != (1, 0):
        raise RuntimeError(f"guard refused: known-answer check gave pass={good}, wrong={bad}")
    first = json.loads(next(x for x in Path(a.rl_tasks).read_text(encoding="utf-8").splitlines() if x.strip()))
    atk = sc.score(first, "```python\n" + attack_program(Path(a.rl_tasks)) + "```")
    res.update(known_answer={"pass": good, "wrong": bad}, secret_read_attack={"reward": atk["reward"], "reason": atk.get("reason")})
    if atk["reward"] != 0:
        raise RuntimeError("guard refused: a program that reads the task file scored full reward on this runner")
    res["model_loaded"] = False
    res["guard_seconds"] = round(time.perf_counter() - t0, 2)
    return res


# ---------------------------------------------------------------------------- inputs

def check_inputs(a) -> dict:
    import sft_job_v1 as sj  # noqa: PLC0415
    need = {"run folder checkpoint.pt": a.run_folder / "checkpoint.pt", "run folder manifest.json": a.run_folder / "manifest.json",
            "RL tasks": a.rl_tasks, "train pool": a.train_pool, "held-out pool": a.heldout_pool, "easy ids": EASY_IDS,
            "free-reward ids": FREE_IDS, "effort manifest": EFFORT_MANIFEST,
            **({"start weights": a.start_weights} if a.start_weights else {}),
            **{f"pack shard {i}": p for i, p in enumerate(a.packs if a.sft_arm != "none" else [])}}
    miss = [f"{k}: {v}" for k, v in need.items() if not Path(v).is_file()]
    if miss:
        raise FileNotFoundError("input missing, nothing was built: " + "; ".join(miss))
    if a.origin != "g5_delivery" and not a.allow_fixture_smoke:  # fail before the rebuild, not after it
        raise ValueError(f"--origin {a.origin} gives a rehearsal adapter that rl-loop/train.py refuses; use --origin g5_delivery for "
                         "Team 5's delivered run folder (dry run only: --allow-fixture-smoke, output is never a result)")
    block = json.loads((a.run_folder / "manifest.json").read_text(encoding="utf-8"))["config"]["model"]["block_size"]
    if block != a.max_tokens:
        raise ValueError(f"run folder block_size {block} != --max-tokens {a.max_tokens}")
    shas = {"rl_tasks": (probe.sha256_file(a.rl_tasks), sj.RL_POOL_SHA256), "train_pool": (probe.sha256_file(a.train_pool), TRAIN_POOL_SHA256),
            "heldout_pool": (probe.sha256_file(a.heldout_pool), HELDOUT_POOL_SHA256), "easy_ids": (probe.sha256_file(EASY_IDS), EASY_IDS_SHA256),
            "free_ids": (probe.sha256_file(FREE_IDS), FREE_IDS_SHA256)}
    bad = {k: v for k, v in shas.items() if v[0] != v[1]}
    if bad and not a.no_pack_check:
        raise ValueError("pinned bytes differ: " + "; ".join(f"{k} {v[0]} != {v[1]}" for k, v in bad.items()))
    n_eff = len(effort_ids())
    if n_eff != 55:
        raise ValueError(f"effort manifest lists {n_eff} training-exclusion ids, expected 55")
    return {"block_size": block, "sha256": {k: v[0] for k, v in shas.items()}, "pinned_match": not bad,
            "start_weights_sha256": probe.sha256_file(a.start_weights) if a.start_weights else None}


def adapter_probe(a) -> dict | None:
    """The probe block of the adapter config. Origin g5_delivery: the adapter refuses a delivered run folder without Team 5's
    probe (ids and expected mean NLL), so the job stops in pins, before the pool and the scorer, when --probe-file is missing."""
    from make_adapter_config import load_probe  # noqa: PLC0415
    if a.probe_file:
        return load_probe(a.probe_file)
    if a.origin == "g5_delivery":
        raise ValueError("--origin g5_delivery needs --probe-file (json {ids, expected_mean_nll[, atol]} supplied with Team 5's checkpoint); "
                         "team5_adapter refuses a delivered run folder without it")
    return None


def pins(a, out: Path) -> dict:
    import sft_job_v1 as sj  # noqa: PLC0415
    adapter_probe(a)  # raises before the pool and the scorer if a delivered run folder comes without its probe
    return {**probe.check_pins(a.run_folder, a.tokenizer, a.byte_table), **check_inputs(a), **sj.check_g5_sources(a)}


def pool_step(a, out: Path) -> dict:
    p = build_pools(read_pool_ids(a.train_pool), read_pool_ids(a.heldout_pool), read_ids(FREE_IDS), effort_ids(),
                    read_ids(EASY_IDS), a.heldout_n)
    (out / "train_ids.txt").write_text("\n".join(p["train_ids"]) + "\n")
    (out / "heldout_ids.txt").write_text("\n".join(p["heldout_ids"]) + "\n")
    print(json.dumps({"pool_counts": p["counts"]}), flush=True)
    return {"counts": p["counts"]}


def tricks_step(a, out: Path) -> dict:
    """The no-skill programs on the first --tricks-limit (128) screen candidates and the held-out subset; CPU, before the model loads."""
    import score_pool  # noqa: PLC0415
    by_id = {}
    for line in a.rl_tasks.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            by_id[r["id"]] = r
    tr = (out / "train_ids.txt").read_text().split()[:a.tricks_limit]
    ho = (out / "heldout_ids.txt").read_text().split()
    pool = score_pool.ScorePool(max(1, a.reward_pool))
    try:
        res = {}
        for label, ids in (("screen_candidates", tr), ("heldout_subset", ho)):
            res[label] = {"problems": len(ids), "by_program": {}}
            for name, code in TRICKS.items():
                text = "```python\n" + code + "\n```"
                rs = pool.score([(by_id[i], text) for i in ids])
                res[label]["by_program"][name] = sum(r["reward"] >= 1 for r in rs)
            res[label]["any_program_full_reward"] = max(res[label]["by_program"].values())
    finally:
        pool.close()
    return res


# ---------------------------------------------------------------------------- SFT rebuild (optional)

def sft_rebuild(a, out: Path) -> dict:
    """#587's arm rebuilt (its weights are deleted at its exit): same rows, method, lr, seed and the steps its arm completed.
    The weights stay in out/_work until the job ends. Not #587's arm bit for bit; its report is printed next to #587's."""
    import subprocess  # noqa: PLC0415
    import sft_job_v1 as sj  # noqa: PLC0415
    import sft_slice_v1  # noqa: PLC0415
    from make_adapter_config import write_config  # noqa: PLC0415
    work = out / "_work"
    cfg = write_config(out / "adapter.yaml", a.g5_root, a.run_folder, a.tokenizer, a.byte_table, TEAM10, a.origin, not a.no_git, probe=adapter_probe(a))
    sl = sft_slice_v1.build(a.packs, a.tokenizer, a.byte_table, a.max_tokens, work / "_inputs", a.dev_rows, check_hashes=not a.no_pack_check)
    rows = work / "_inputs" / f"{a.sft_arm}_train.jsonl"
    ns = argparse.Namespace(method="full", lr=a.sft_lr, marker_lr=1e-3, batch=a.sft_batch, max_train_seconds=a.sft_max_train_seconds,
                            device=a.device, seed=a.seed, gen_limit=1, gen_max_new=16, gen_seconds=0.0, heldout=a.heldout,
                            heldout_sources=a.heldout_sources, rl_tasks=a.rl_tasks, rl_ids=EASY_IDS, rl_max_new=a.max_new,
                            rl_limit=a.rate_probe_prompts, rl_k=a.k, rl_seconds=a.rate_probe_seconds)
    arm_out = work / f"sft_{a.sft_arm}"
    cmd = sj.sft_cmd(ns, cfg, rows, work / "_inputs" / "dev.jsonl", arm_out, a.sft_steps, True)
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("SFT rebuild failed: " + r.stderr[-1500:])
    rep = json.loads((arm_out / "sft_report.json").read_text())
    shutil.rmtree(work / "_inputs", ignore_errors=True)
    (arm_out / "generations.jsonl").unlink(missing_ok=True)
    weights = arm_out / "model.safetensors"
    metrics = sj.arm_metrics(rep, None)
    rs = (rep.get("after") or {}).get("rl_screen") or {}
    rate = (rs["seconds"] / rs["prompts"]) if rs.get("prompts") else None
    ref = None
    if a.sft_reference and Path(a.sft_reference).is_file():  # #587's compare.json: printed next to this rebuild's report
        ref = json.loads(Path(a.sft_reference).read_text()).get("arms", {}).get(a.sft_arm.upper())
    print(json.dumps({"sft_rebuild": metrics, "sft_587_reference": ref}), flush=True)
    return {"arm": a.sft_arm, "weights": str(weights), "weights_sha256": probe.sha256_file(weights), "slice": sl,
            "steps_requested": a.sft_steps, "rebuild_report": metrics, "reference_587_report": ref,
            "decode_seconds_per_prompt": rate, "rate_probe": {"prompts": rs.get("prompts"), "seconds": rs.get("seconds"),
                                                                "k": rs.get("k"), "max_new": rs.get("max_new")},
            "rebuild_seconds": round(time.perf_counter() - t0, 1),
            "note": "rebuilt state: not #587's arm bit for bit; step 0 is measured on these weights"}


# ---------------------------------------------------------------------------- RL

def write_train_config(a, out: Path, init_state: Path | None, init_sha: str | None, deadline_unix: float, screen_n: int) -> Path:
    import yaml  # noqa: PLC0415
    cfg = {"seed": a.seed, "device": a.device, "out_dir": str(out / "rl"),
           "model": {"kind": "team5_adapter", "adapter_config": str(out / "adapter.yaml"), "kv_cache": True,
                     **({"allow_fixture_smoke": True} if a.allow_fixture_smoke else {}),
                     **({"init_state": str(init_state), "init_state_sha256": init_sha} if init_state else {})},
           "task": {"kind": "stdio", "require_verifier": True, "tasks": str(a.rl_tasks),
                    "train_ids": str(out / "train_ids.txt"), "heldout_ids": str(out / "heldout_ids.txt")},
           "train": {"algo": "objective_v1", "sampler": getattr(a, "sampler", "policy"), "steps": a.updates, "prompts_per_step": a.prompts_per_step,
                     "k": a.k, "max_new": a.max_new, "temperature": 1.0, "lr": a.lr, "ppo_epochs": 1, "kl_coef": 0.0,
                     "grad_clip": 1.0, "weight_decay": 0.0, "tr_epsilon": a.tr_epsilon, "fp32_master": True,
                     "autocast": "bf16" if a.device.startswith("cuda") else None, "eval_every": a.updates, "eval_k": a.eval_k,
                     "reward_workers": 4, "reward_pool": a.reward_pool,
                     # rows per forward in old_lp and the update (train.py chunked_logprobs / backward_objective_v1).
                     # Whole groups of 8 x 2,048 do not fit: job RLG measured 10.2 GiB for ONE row on a T4 (KAS V2,
                     # bf16 autocast over fp32 weights, AdamW state held) and an OOM at 2; 8 rows extrapolate to 37-62 GiB
                     **({"micro_rows": getattr(a, "micro_rows", 1)} if getattr(a, "micro_rows", 1) else {}),
                     "screen": {"n": screen_n, "k": a.k, "min_mixed": a.min_mixed},
                     "state_dir": str(out / "rl_state"), "state_every": a.state_every, "deadline_unix": deadline_unix,
                     **({"max_steps_this_call": a.max_steps_this_call} if a.max_steps_this_call else {}),
                     **({"sampler_max_rows": a.sampler_max_rows} if getattr(a, "sampler", "policy") == "g5_batch" else {}),
                     # identical-weights check before the first update (rl-loop/train.py logprob_gate); stops the job
                     # if the update forward does not reproduce the sampler's log-probs (work/lpgate-2026-11-23)
                     **({"logprob_gate": True} if getattr(a, "logprob_gate", True) else {}),
                     # auto: rl-loop/train.py resolve_update_mode picks eval (train_quiet with DT) when the model has
                     # train-mode randomness, e.g. the KAS head's tok_u dropout; train otherwise
                     **({"update_mode": a.update_mode} if getattr(a, "update_mode", "auto") not in ("auto", None) else {}),
                     # per-step seconds in rl/metrics.jsonl times_s; this makes the CUDA split exact (train.py time_sync)
                     **({"time_sync": True} if getattr(a, "time_sync", False) else {})}}
    if cfg["train"]["autocast"] is None:
        del cfg["train"]["autocast"]
    if getattr(a, "keep_weights_dir", None):  # default off: train.py writes its trainable tensors here (bf16), keep_final_weights completes them
        cfg["train"]["save_trainable"] = str(out / "_work" / "rl_trainable.pt")
    p = out / "rl_config.yaml"
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return p


def install_detector(train, tasks_by_id: dict, log: list, stand_in_reward: float | None, seed: int,
                     evals_path: Path | None = None, persist_path: Path | None = None):
    """Patch train.evaluate / train.score_completions in this process (train.py itself is unchanged): count, per held-out
    evaluation, the passing samples and those the literal-sample detector flags. With stand_in_reward p, every reward is
    replaced by a seeded coin (a dry-run stand-in that exercises rollout -> advantage -> step -> save -> resume -> evaluation
    on a model that cannot pass anything; never for a real run)."""
    import stdio_check as sc  # noqa: PLC0415
    orig_eval, orig_score = train.evaluate, train.score_completions
    state = {"on": False}
    rng = random.Random(seed)

    def score(task, pairs, workers=1):
        flat = orig_score(task, pairs, workers) if stand_in_reward is None else [float(rng.random() < stand_in_reward) for _ in pairs]
        if state["on"]:
            rec = log[-1]
            for (p, c), rw in zip(pairs, flat):
                rec["samples"] += 1
                if rw >= 1:
                    rec["pass"] += 1
                    env = task._items[tuple(p)]
                    code, _ = sc.extract_code(task.decode(c, env_id=env))
                    why = literal_sample(code, tasks_by_id[env]["tests"][:sc.MAX_TESTS])
                    if why:
                        rec["literal"] += 1
                        rec["literal_by"][why] = rec["literal_by"].get(why, 0) + 1
        return flat

    def evaluate(sampler, task, prompts, *args, **kw):
        counted = prompts is task.heldout
        if counted:  # eval_index = held-out evaluations already in evals.jsonl: stable across a pause and a resume
            done = 0
            if evals_path is not None and Path(evals_path).is_file():
                done = sum('"name": "heldout"' in x for x in Path(evals_path).read_text().splitlines())
            log.append({"eval_index": done, "samples": 0, "pass": 0, "literal": 0, "literal_by": {}})
            state["on"] = True
        try:
            res = orig_eval(sampler, task, prompts, *args, **kw)
            if counted and persist_path is not None:  # an evaluation killed half way leaves no record
                with open(persist_path, "a") as f:
                    f.write(json.dumps(log[-1]) + "\n")
            return res
        finally:
            state["on"] = False
    train.score_completions, train.evaluate = score, evaluate


def failure_counts(evals: list[dict]) -> list[dict]:
    """Held-out evaluations in order: pass rate and the reason counts of this evaluation's samples."""
    return [{"step": e["step"], "pass": e["pass"], "reasons": e.get("reasons") or {}, "problems": e["problems"], "k": e["k"],
             "cut_off_share": e.get("truncated"), "mean_tokens": e.get("mean_tokens")} for e in evals if e.get("name") == "heldout"]


def keep_final_weights(a, out: Path, init_state, step: int, model=None) -> dict:
    """--keep-weights-dir: the final RL weights as a Team 7 run folder (<dir>/g10-rl-final). rl-loop/train.py (unchanged) saves
    only the trainable tensors, in bf16 (train.save_trainable); they are laid over the start weights (the arm or the raw
    checkpoint) in a fresh model, which is then saved whole. Not bit-identical to the trainer's fp32 master copy: the
    trainable tensors are bf16-rounded, as the policy is when it samples under bf16 autocast."""
    import torch  # noqa: PLC0415
    import keep_weights  # noqa: PLC0415
    trainable = torch.load(out / "_work" / "rl_trainable.pt", map_location="cpu", weights_only=True)
    if model is None:
        import team5_adapter as ta  # noqa: PLC0415
        from safetensors.torch import load_file  # noqa: PLC0415
        model = ta.build(out / "adapter.yaml", device="cpu").require_bundle().model
        if init_state:
            model.load_state_dict(load_file(str(init_state)), strict=True)
    unknown = sorted(set(trainable) - set(model.state_dict()))
    if unknown:
        raise RuntimeError(f"trained tensors without a place in the model: {unknown[:3]}")
    model.load_state_dict(trainable, strict=False)
    info = keep_weights.save_run_folder(model, a.keep_weights_dir, "g10-rl-final", step, keep_weights.team5_probe)
    return {**info, "trainable_tensors": len(trainable), "trainable_dtype": "bfloat16"}


def rl_step(a, out: Path, init_state, init_sha, deadline_unix, screen_n) -> dict:
    cfg_path = write_train_config(a, out, init_state, init_sha, deadline_unix, screen_n)
    import yaml  # noqa: PLC0415
    import train  # noqa: PLC0415  (rl-loop/train.py, unchanged)
    cfg = yaml.safe_load(cfg_path.read_text())
    by_id = {}
    for line in a.rl_tasks.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            by_id[r["id"]] = r
    lit: list = []
    persist = out / "literal_sample.jsonl"
    install_detector(train, by_id, lit, a.stand_in_reward, a.seed, out / "rl" / "evals.jsonl", persist)
    summary = train.train(cfg)
    rl_out = out / "rl"
    res: dict = {"status": summary.get("status"), "train_summary_file": str(rl_out / "summary.json")}
    if getattr(a, "keep_weights_dir", None) and summary.get("status") not in ("NO_GO_MIXED_BAND", "PAUSED_AT_DEADLINE"):
        res["kept_weights"] = keep_final_weights(a, out, init_state, int(summary["steps"]))
    if (rl_out / "screen.json").is_file():
        screen = json.loads((rl_out / "screen.json").read_text())
        res["screen_survey"] = screen_survey(screen)
        (out / "screen_survey.json").write_text(json.dumps(res["screen_survey"], indent=1))
    if summary.get("router_bias_unchanged") is False:  # after the kept weights: the step fails, nothing is lost
        why = (summary.get("router_bias_check") or {}).get("reason") or "router_bias changed during RL"
        res.update(ok=False, error=f"{why} (summary.failures); outputs kept", router_bias_unchanged=False)
    if summary.get("status") in ("NO_GO_MIXED_BAND", "PAUSED_AT_DEADLINE"):
        return res
    evals = [json.loads(x) for x in (rl_out / "evals.jsonl").read_text().splitlines() if x.strip()]
    fc = failure_counts(evals)
    by_index = {}
    for x in persist.read_text().splitlines() if persist.is_file() else []:
        r_ = json.loads(x)
        by_index[r_["eval_index"]] = r_            # the last record of an index wins (a re-measured evaluation)
    lit_rep = [{"step": f["step"], **by_index[i], "literal_share_of_passes": (by_index[i]["literal"] / by_index[i]["pass"]) if by_index[i]["pass"] else 0.0}
               for i, f in enumerate(fc) if i in by_index]
    if len(lit_rep) != len(fc):
        raise RuntimeError(f"literal-sample records for {len(lit_rep)} of {len(fc)} held-out evaluations")
    wrong = [f["reasons"].get("wrong_answer", 0) for f in fc]
    mf = rl_out / "metrics.jsonl"
    if not mf.is_file():
        mf = rl_out / "smoke_metrics.jsonl"  # a rehearsal adapter under --allow-fixture-smoke (dry run)
    metrics = [json.loads(x) for x in mf.read_text().splitlines() if x.strip()]
    res.update(heldout_change=summary["heldout_change"], heldout_curve=summary["heldout_curve"], evaluations=fc,
               literal_sample=lit_rep, groups_used_per_step=[m.get("groups_used") for m in metrics],
               group_kinds_total=(summary.get("objective") or {}).get("group_kinds_total"),
               optimizer_steps=(summary.get("objective") or {}).get("steps_with_optimizer_update"),
               time_split_s_per_step=summary.get("mean_times_s_after_step1"), step1_s=summary.get("step1_s"),
               trainable_weight_change=summary.get("trainable_weight_change"), router_unchanged=summary.get("router_unchanged"),
               router_bias_unchanged=summary.get("router_bias_unchanged"),
               logprob_gate=summary.get("logprob_gate"), update_mode=summary.get("update_mode", "train"),
               update_mode_resolution=summary.get("update_mode_resolution"),
               decision=decide_rl(summary["heldout_change"], wrong[0] if wrong else None, wrong[-1] if wrong else None,
                                  lit_rep[0]["literal_share_of_passes"] if lit_rep else None,
                                  lit_rep[-1]["literal_share_of_passes"] if lit_rep else None),
               seconds=summary.get("seconds"))
    (out / "report.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def rate_probe(a, out: Path, init_state) -> dict:
    """Seconds to decode one prompt's k samples at max_new on these weights, from the first easy prompts of the trained pool
    (a short, time-budgeted screen). Used when no rebuild measured it and none was given."""
    import team5_adapter as ta  # noqa: PLC0415
    from safetensors.torch import load_file  # noqa: PLC0415
    ids = (out / "train_ids.txt").read_text().split()[:a.rate_probe_prompts]
    ids_file = out / "rate_ids.txt"
    ids_file.write_text("\n".join(ids) + "\n")
    bundle = ta.build(out / "adapter.yaml", device=a.device).require_bundle()
    if init_state:
        bundle.model.load_state_dict(load_file(str(init_state)), strict=True)
    if getattr(a, "sampler", "policy") == "g5_batch":
        return batched_rate(a, bundle, ids)
    rep = probe.rl_screen_bundle(bundle, a.rl_tasks, ids_file, a.k, a.max_new, a.device, 0, a.rate_probe_seconds)
    return {"decode_seconds_per_prompt": rep["seconds"] / rep["prompts"] if rep["prompts"] else None, "prompts": rep["prompts"],
            "seconds": rep["seconds"], "stopped_at_budget": rep["stopped_at_budget"]}


def batched_rate(a, bundle, ids: list[str]) -> dict:
    """r for sampler g5_batch: one bundle.sample_many over the rate-probe prompts (real stops, bf16 autocast on cuda as the
    trainer samples), seconds divided by the number of prompts. Fewer rows than a 16-prompt step, so it overstates r."""
    import torch  # noqa: PLC0415
    by_id = {}
    for line in a.rl_tasks.read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            by_id[t["id"]] = t
    codec = bundle.codec()
    block = bundle.spec["block_size"]
    prompts = [p for p in (codec.encode_prompt(by_id[i]["statement"]) for i in ids if i in by_id) if block - len(p) >= 16]
    if not prompts:
        return {"decode_seconds_per_prompt": None, "prompts": 0, "seconds": 0.0, "sampler": "g5_batch"}
    mn = min(a.max_new, block - max(len(p) for p in prompts))
    gen = torch.Generator(device=a.device).manual_seed(0)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if a.device.startswith("cuda") else contextlib.nullcontext()
    t0 = time.perf_counter()
    with amp:
        bundle.sample_many(prompts, a.k, mn, 1.0, gen)
    if a.device.startswith("cuda"):
        torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    return {"decode_seconds_per_prompt": dt / len(prompts), "prompts": len(prompts), "seconds": round(dt, 2),
            "max_new": mn, "sampler": "g5_batch", "stopped_at_budget": False}


def screen_only(a, out: Path, init_state, screen_n: int, seconds: float) -> dict:
    """Not enough time left for screen + 3 updates + the last evaluation: run the screen (time-budgeted), save the survey, stop."""
    import team5_adapter as ta  # noqa: PLC0415
    from safetensors.torch import load_file  # noqa: PLC0415
    ids = [x for x in (out / "train_ids.txt").read_text().split()][:screen_n]
    ids_file = out / "screen_ids.txt"
    ids_file.write_text("\n".join(ids) + "\n")
    bundle = ta.build(out / "adapter.yaml", device=a.device).require_bundle()
    if init_state:
        bundle.model.load_state_dict(load_file(str(init_state)), strict=True)
    rep = probe.rl_screen_bundle(bundle, a.rl_tasks, ids_file, a.k, a.max_new, a.device, 0, seconds)
    k = rep["k"]
    pp = rep["per_prompt"]
    survey = {"problems": len(pp), "k": k, "pass_rate": boot_ci([x[1] / k for x in pp]), "mixed": rep["groups"]["mixed"],
              "failure_mix_samples": rep["reasons"], "stopped_at_budget": rep["stopped_at_budget"], "seconds": rep["seconds"]}
    (out / "screen_survey.json").write_text(json.dumps(survey, indent=1))
    return {"status": "STOPPED_NOT_ENOUGH_TIME", "screen_survey": survey}


# ---------------------------------------------------------------------------- driver

def run(a, out: Path) -> int:
    t0 = time.time()
    deadline_unix = t0 + a.deadline_minutes * 60
    results: dict = {}

    def env():
        import platform  # noqa: PLC0415
        import stdio_check as sc  # noqa: PLC0415
        v = {"python": platform.python_version(), "platform": platform.platform(), "runner": sc.RUNNER_KIND}
        try:
            import torch  # noqa: PLC0415
            v["torch"] = torch.__version__
        except Exception as e:  # noqa: BLE001
            v["torch"] = f"not importable: {e}"
        print(json.dumps({"runner": sc.RUNNER_KIND, "env": v}), flush=True)
        return v

    results["env"] = probe.step(out, "env", env)
    results["guard"] = probe.step(out, "guard", lambda: guard(a, out))
    if not results["guard"]["ok"]:
        print(json.dumps({"guard": "refused", "model_loaded": False, "seconds": results["guard"]["seconds"],
                          "error": results["guard"]["error"]}), flush=True)
        return probe.finish(out, results)
    for name, fn in (("pins", pins), ("pool", pool_step), ("tricks", tricks_step)):
        results[name] = probe.step(out, name, lambda fn=fn: fn(a, out))
        if not results[name]["ok"]:
            return probe.finish(out, results)
    init_state, init_sha, rate = None, None, a.decode_seconds_per_prompt
    sft_s = 0.0
    if a.start_weights:
        init_state, init_sha = a.start_weights, probe.sha256_file(a.start_weights)
        from make_adapter_config import write_config  # noqa: PLC0415
        write_config(out / "adapter.yaml", a.g5_root, a.run_folder, a.tokenizer, a.byte_table, TEAM10, a.origin, not a.no_git, probe=adapter_probe(a))
    elif a.sft_arm != "none":
        results["sft"] = probe.step(out, "sft", lambda: sft_rebuild(a, out))
        if not results["sft"]["ok"]:
            return probe.finish(out, results)
        init_state, init_sha = Path(results["sft"]["weights"]), results["sft"]["weights_sha256"]
        if getattr(a, "sampler", "policy") != "g5_batch":  # the rebuild's rate is per prompt; g5_batch measures its own batched rate below
            rate = rate or results["sft"].get("decode_seconds_per_prompt")
        sft_s = results["sft"]["seconds"]
    else:
        from make_adapter_config import write_config  # noqa: PLC0415
        write_config(out / "adapter.yaml", a.g5_root, a.run_folder, a.tokenizer, a.byte_table, TEAM10, a.origin, not a.no_git, probe=adapter_probe(a))

    if rate is None:  # raw checkpoint or --start-weights without a given rate: measure it before choosing sizes
        results["rate"] = probe.step(out, "rate", lambda: rate_probe(a, out, init_state))
        rate = results["rate"].get("decode_seconds_per_prompt") if results["rate"]["ok"] else None

    def plan():
        r = rate if rate else a.max_new * a.ms_per_decode_step / 1000.0
        basis = "measured" if rate else f"worst case: every sample runs to {a.max_new} tokens at {a.ms_per_decode_step} ms per step"
        sc_pick = pick_screen_n(r) if a.screen_n == "auto" else {"n": int(a.screen_n), "fits": None, "basis": "fixed by --screen-n"}
        kw = dict(screen_n=sc_pick["n"], pps=a.prompts_per_step, heldout_n=a.heldout_n or 255, eval_k=a.eval_k, k=a.k,
                  update_s=a.update_seconds, score_s=a.score_seconds_per_prompt)
        table = time_table(r, updates=a.updates, fixed_s=time.time() - t0 - sft_s, sft_s=sft_s, **kw)
        left = enough_time(deadline_unix - time.time(), r, **kw)
        for name, s in table["rows"]:
            print(f"  time table: {name}: {s} s", flush=True)
        print(json.dumps({"plan": {"decode_seconds_per_prompt": round(r, 2), "rate_basis": basis, "screen": sc_pick,
                                   "time_left": left}}), flush=True)
        return {"decode_seconds_per_prompt": r, "rate_basis": basis, "screen": sc_pick, "table": table, "time_left": left}
    results["plan"] = probe.step(out, "plan", plan)
    if not results["plan"]["ok"]:
        return probe.finish(out, results)
    p = results["plan"]
    if a.force_not_enough_time or not p["time_left"]["ok"]:
        results["rl"] = probe.step(out, "rl", lambda: screen_only(a, out, init_state, p["screen"]["n"], SCREEN_BUDGET_S))
    else:
        results["rl"] = probe.step(out, "rl", lambda: rl_step(a, out, init_state, init_sha, deadline_unix, p["screen"]["n"]))
    return probe.finish(out, results)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--g5-root", type=Path, required=True)
    ap.add_argument("--run-folder", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--rl-tasks", type=Path, required=True, help="RL data v1 cc.jsonl (the pinned file; also the secret path)")
    ap.add_argument("--train-pool", type=Path, required=True, help="rl-code-v1-train.pool.jsonl (#564)")
    ap.add_argument("--heldout-pool", type=Path, required=True, help="rl-code-v1-heldout.pool.jsonl (#564)")
    ap.add_argument("--sft-arm", choices=("none", "a2", "a4"), default="none", help="rebuild #587's arm in-job (none = the raw checkpoint)")
    ap.add_argument("--start-weights", type=Path, help="stored weights of the arm (skips the rebuild)")
    ap.add_argument("--sft-reference", type=Path, help="#587's compare.json: its arm report is printed next to the rebuild's")
    ap.add_argument("--packs", type=Path, nargs="*", default=[], help="firewalled OCR-2 pack shards (for the rebuild)")
    ap.add_argument("--heldout", type=Path, help="held-out file of the run (forgetting bpb in the rebuild)")
    ap.add_argument("--heldout-sources", type=Path)
    ap.add_argument("--sft-steps", type=int, default=243, help="the optimizer steps #587's arm completed")
    ap.add_argument("--sft-lr", type=float, default=1e-4)
    ap.add_argument("--sft-batch", type=int, default=16)
    ap.add_argument("--sft-max-train-seconds", type=float, default=1500.0)
    ap.add_argument("--dev-rows", type=int, default=256)
    ap.add_argument("--rate-probe-prompts", type=int, default=8, help="easy prompts the rebuild screens to measure the decode rate")
    ap.add_argument("--rate-probe-seconds", type=float, default=120.0)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--updates", type=int, default=MAX_UPDATES, help=f"optimizer updates, at most {MAX_UPDATES}")
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--prompts-per-step", type=int, default=16, help="min(16, cohort size): the trainer slices the cohort")
    ap.add_argument("--max-new", type=int, default=1536)
    ap.add_argument("--tr-epsilon", type=float, default=0.2)
    ap.add_argument("--min-mixed", type=int, default=MIN_MIXED)
    ap.add_argument("--screen-n", default="auto", help="auto = largest of 64/128/256 that fits 10 minutes, or a fixed number")
    ap.add_argument("--heldout-n", type=int, default=64, help="first N held-out pool ids in file order, unfiltered (0 = all 255); Amendment 2")
    ap.add_argument("--eval-k", type=int, default=4)
    ap.add_argument("--tricks-limit", type=int, default=128, help="screen candidates the no-skill programs are scored on")
    ap.add_argument("--reward-pool", type=int, default=16, help="scorer worker processes (score_pool); must be > 0")
    ap.add_argument("--no-logprob-gate", dest="logprob_gate", action="store_false",
                    help="skip the identical-weights log-prob check before the first update (on by default)")
    ap.add_argument("--update-mode", choices=("auto", "train", "eval", "train_quiet"), default="auto",
                    help="module mode of old_lp and the update forward (rl-loop/train.py update_mode). auto: eval when the "
                         "model has train-mode randomness (a KAS head's tok_u dropout), train otherwise; recorded in the report")
    ap.add_argument("--state-every", type=int, default=5)
    ap.add_argument("--max-steps-this-call", type=int, default=0, help="dry run: pause after this many updates, rerun to resume")
    ap.add_argument("--deadline-minutes", type=float, default=85.0)
    ap.add_argument("--decode-seconds-per-prompt", type=float, help="measured seconds to decode one prompt's k samples (else from the rebuild's rate probe)")
    ap.add_argument("--ms-per-decode-step", type=float, default=98.0, help="worst-case basis when no rate is known (Mac MPS, T2 shape, q3 STATUS)")
    ap.add_argument("--update-seconds", type=float, default=16.0, help="time-table basis: seconds of the loss and optimizer step (E1: 15.8 s)")
    ap.add_argument("--score-seconds-per-prompt", type=float, default=0.5, help="time-table basis: scoring seconds per prompt's k samples")
    ap.add_argument("--force-not-enough-time", action="store_true", help="dry run: take the screen-only branch")
    ap.add_argument("--stand-in-reward", type=float, help="DRY RUN ONLY: replace every reward by a seeded coin with this probability")
    ap.add_argument("--no-pack-check", action="store_true", help="tests only: accept pool files and packs other than the pins")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--origin", default="g5_delivery", choices=("g10_rehearsal", "g5_delivery"),
                    help="g5_delivery: Team 5's delivered run folder (non-smoke manifest); g10_rehearsal is a stand-in and train.py refuses it without --allow-fixture-smoke")
    ap.add_argument("--probe-file", type=Path, help="json {ids, expected_mean_nll[, atol]} supplied with Team 5's checkpoint; required for --origin g5_delivery")
    ap.add_argument("--allow-fixture-smoke", action="store_true", help="DRY RUN ONLY: let train.py load a rehearsal adapter; its output is never a result")
    ap.add_argument("--sampler", choices=("policy", "g5_batch"), default="policy",
                    help="policy: one decode per prompt; g5_batch: every prompt of a step in one decode (B5, 23 Nov: 12.8x on a T4)")
    ap.add_argument("--sampler-max-rows", type=int, default=128, help="g5_batch: rows decoded together at most")
    ap.add_argument("--micro-rows", type=int, default=1,
                    help="rows per forward in old_lp and the update (0 = the whole group of k). Default 1: a group of 8 at "
                         "2,048 tokens peaked at 10.9 GiB with 1 on a T4 and ran out of memory with 2 and 4 (job RLG)")
    ap.add_argument("--time-sync", action="store_true",
                    help="synchronize CUDA at each phase boundary so rl/metrics.jsonl times_s splits sampling (rollout), "
                         "scoring (reward) and the update (old_logprobs + train) exactly; off by default")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--keep-weights-dir", type=Path,
                    help="default off: also keep the FINAL RL weights as a Team 7 run folder <dir>/g10-rl-final (Team 9's run_lab_ckpt.py "
                         "--run-dir); the trainable tensors are bf16 (see keep_final_weights); everything else is deleted as before")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if not 1 <= a.updates <= MAX_UPDATES:
        ap.error(f"--updates must be 1..{MAX_UPDATES}")
    if a.reward_pool < 1:
        ap.error("--reward-pool must be > 0 (the scorer goes through score_pool)")
    if a.sft_arm != "none" and not (a.packs and a.heldout) and not a.start_weights:
        ap.error("--sft-arm a2|a4 needs --packs and --heldout (or --start-weights)")
    return a


def main(argv=None) -> int:
    a = parse_args(argv)
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rc = 1
    try:
        rc = run(a, out)
        return rc
    finally:
        shutil.rmtree(out / "_work", ignore_errors=True)  # SFT weights and built rows never leave the job
        status = None
        for f in (out / "rl" / "summary.json", out / "rl" / "smoke_summary.json", out / "rl" / "status.json"):  # a finished summary wins over an old pause note
            if f.is_file():
                status = json.loads(f.read_text()).get("status") or "COMPLETE"
                break
        if status in ("COMPLETE", "NO_GO_MIXED_BAND", "FIXTURE_SMOKE_NOT_A_RESULT"):
            shutil.rmtree(out / "rl_state", ignore_errors=True)  # a paused run keeps its state: rerun the same command to resume

if __name__ == "__main__":
    raise SystemExit(main())
