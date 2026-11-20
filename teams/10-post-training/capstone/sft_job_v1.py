"""G10 first real SFT job on a Team 5 run folder: OCR-2 code rows that fit the model's context, full traces vs short answers.

    python capstone/sft_job_v1.py --g5-root <lab checkout> --run-folder <dir with manifest.json/checkpoint.pt/summary.json> \
        --tokenizer tokenizer.json --byte-table raw_table_P32.npz --heldout H.jsonl --heldout-sources S.jsonl \
        --packs <shard-00000>/pack.firewalled.jsonl ... --rl-tasks cc.jsonl --rl-ids capstone/probe_rl_easy_ids.txt \
        --device cuda --out out/

One question: on this checkpoint, which shape of the same code SFT rows gives more RL-usable output within the model's
context, full reasoning traces (A2) or the same rows with the reasoning deleted (A4, the E9 short-answer rule), and at
what forgetting cost?

Steps (each writes out/<step>.json; summary.json last; exit 1 if any step failed):
  pins        tokenizer sha256 and byte-table content hash against the run manifest (day_one_probe.check_pins), then
              every input present (run folder checkpoint and manifest, the four pack shards, the RL pool and ids), the
              run's block size equal to --max-tokens, the RL pool's sha256, and the four Team 5 source files of the
              run folder's manifest (train_week2.py, model.py, config.py, artifacts.py) against --g5-root (the same
              pin the adapter applies later); any failure stops the job before any rows are built, with a message
              naming the missing or mismatched input
  inputs      capstone/sft_slice_v1.py: firewalled pack shards (sha256-checked against the committed firewall record),
              rows <= the model's block size, re-tokenised and checked against the pack ids, dev split by statement,
              A2 and A4 forms of the same rows. Rows live in out/_inputs/ and are deleted at exit
  sft_a2      capstone/sft_g5.py on the A2 rows: base evaluation first (dev NLL, forgetting bpb on the run's held-out,
              greedy format screen on dev prompts, RL screen k samples per easy prompt), then training, then the same
              evaluation; mask, step-1 writeback, frozen-weight and reload checks
  sft_a4      the same on the A4 rows, run for exactly the optimizer steps sft_a2 completed (so a training-time cap
              cannot make the arms unequal) and with --no-before (the base was measured in sft_a2)
  compare     per arm: change in forgetting bpb, format validity, closed turns, code-fence share, programs that run,
              pass rate and mixed groups, with the decision rule of the job request applied. With --rl-seconds and
              --gen-seconds each screen stops starting new prompts at its budget; A2 and A4 are compared on the
              prompts both screens reached (same ids, same order), and the base on the same ids
With --deadline-minutes the job ends by itself at that wall-clock time: an arm still running is killed, its weights
are removed, and summary.json names the step that stopped. Outputs are aggregates only: each arm's weights and generations are deleted after its reload check (day_one_probe
run_sft_arm), the rows at exit. Network: none. Writes only to --out. Resumable state is not saved (see the request).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM10 = HERE.parent
sys.path.insert(0, str(TEAM10 / "rl-loop"))
sys.path.insert(0, str(HERE))

import day_one_probe as probe  # noqa: E402

RL_POOL_SHA256 = "91ee99512f0411aea2de4ca5eaf10b87b2d8f785ca73747bf8deb45dd6ea9be0"  # out/v1/cc.jsonl, RL data v1
FORGET_LIMIT_BPB = 0.05  # the team's forgetting limit (E9 RESULTS, PREREG)
MIXED_MIN = 2            # decision rule: an arm "gives RL signal" with at least this many mixed groups


def common_prefix(screens: list[dict | None], key: str) -> list[str] | None:
    """Ids every given screen reached. Screens walk the same ids in the same order and stop at a time budget, so the
    common set is the shortest screen's prefix; None when a screen has no per-item record (older report)."""
    if not screens or any(not s or key not in s for s in screens):
        return None
    lists = [[x[0] for x in s[key]] for s in screens]
    n = min(len(x) for x in lists)
    if any(x[:n] != lists[0][:n] for x in lists):
        raise RuntimeError(f"screens did not walk the same {key} order")
    return lists[0][:n]


def screen_metrics(g: dict | None, rl: dict | None, gen_ids: list[str] | None, rl_ids: list[str] | None) -> dict:
    """Format and RL-screen numbers, restricted to the given ids when per-item records exist (else the aggregates)."""
    out: dict = {}
    g = g or {}
    if gen_ids is not None and "per_row" in g:
        keep = set(gen_ids)
        rows = [r for r in g["per_row"] if r[0] in keep]
        n = max(len(rows), 1)
        out.update({"format_prompts": len(rows), "format_validity": sum(r[1] for r in rows) / n,
                    "closed_im_end": sum(r[2] for r in rows) / n, "hit_budget": sum(r[3] for r in rows) / n,
                    "mean_gen_tokens": sum(r[4] for r in rows) / n})
    else:
        out.update({k: g.get(k) for k in ("format_validity", "closed_im_end", "hit_budget", "mean_gen_tokens")})
    if rl:
        if rl_ids is not None and "per_prompt" in rl:
            keep = set(rl_ids)
            pp = [x for x in rl["per_prompt"] if x[0] in keep]
            k, n = rl["k"], len(pp)
            ns = max(n * rl["k"], 1)
            out.update({"rl_prompts": n, "rl_pass_rate": sum(x[1] for x in pp) / ns,
                        "rl_mixed_groups": sum(0 < x[1] < k for x in pp), "rl_code_fence_share": sum(x[3] for x in pp) / ns,
                        "rl_runs_share": sum(x[2] for x in pp) / ns, "rl_skipped_too_long": rl["skipped_too_long"],
                        "rl_screened_before_budget": rl["prompts"]})
        else:
            n = max(rl["prompts"] * rl["k"], 1)
            reasons = rl.get("reasons", {})
            runs = reasons.get("pass", 0) + reasons.get("wrong answer on a test", 0)
            out.update({"rl_prompts": rl["prompts"], "rl_pass_rate": rl["pass_rate"], "rl_mixed_groups": rl["groups"]["mixed"],
                        "rl_code_fence_share": rl["samples_with_code_fence"] / n, "rl_runs_share": runs / n,
                        "rl_skipped_too_long": rl["skipped_too_long"]})
    return out


def arm_metrics(rep: dict, before: dict | None, gen_ids: list[str] | None = None, rl_ids: list[str] | None = None) -> dict:
    """Deltas and RL-usable counts from one arm's sft_report-derived result (run_sft_arm output)."""
    after = rep.get("after") or {}
    out: dict = {"steps": len(rep.get("log") or []) or None, "stopped_early": rep.get("stopped_early"),
                 "train_seconds": rep.get("train_seconds")}
    if before and before.get("forgetting") and after.get("forgetting"):
        b, a = before["forgetting"], after["forgetting"]
        out["forgetting_delta_bpb"] = a["val/bpb"] - b["val/bpb"] if "val/bpb" in a and "val/bpb" in b else None
        out["forgetting_delta_by_group"] = {k.split("/")[-1]: a[k] - b[k] for k in a
                                            if k.startswith("val/groups/") and k in b}
    out.update(screen_metrics(after.get("generation"), after.get("rl_screen"), gen_ids, rl_ids))
    return out


def decide(a2: dict, a4: dict) -> dict:
    """The request's decision rule, applied mechanically; the reading stays with the team."""
    def ok(m):
        d = m.get("forgetting_delta_bpb")
        return d is not None and d <= FORGET_LIMIT_BPB
    eligible = {k: m for k, m in (("A2", a2), ("A4", a4)) if ok(m)}
    if not eligible:
        return {"verdict": "neither arm within the forgetting limit", "default_shape": None}
    best = max(eligible, key=lambda k: (eligible[k].get("rl_mixed_groups") or 0, eligible[k].get("rl_runs_share") or 0))
    mixed = eligible[best].get("rl_mixed_groups") or 0
    return {"verdict": ("RL signal" if mixed >= MIXED_MIN else "no RL signal at this size"), "default_shape": best,
            "rule": f"within +{FORGET_LIMIT_BPB} bpb forgetting; more mixed groups, then more running programs; "
                    f"'RL signal' needs >= {MIXED_MIN} mixed groups"}


def sft_cmd(a, cfg: Path, rows: Path, dev: Path, arm_out: Path, steps: int, no_before: bool) -> list[str]:
    method = (["--method", "full", "--lr", str(a.lr)] if a.method == "full" else
              ["--method", "lora", "--lr", str(a.lr), "--marker-rows", "--wd", "0", "--marker-lr", str(a.marker_lr)])
    return [sys.executable, str(HERE / "sft_g5.py"), "--adapter-config", str(cfg), "--train", str(rows),
            "--eval", str(dev), *method, "--steps", str(steps), "--batch", str(a.batch),
            "--max-train-seconds", str(a.max_train_seconds), "--device", a.device, "--seed", str(a.seed),
            "--gen-limit", str(a.gen_limit), "--gen-max-new", str(a.gen_max_new), "--gen-seconds", str(a.gen_seconds),
            "--heldout", str(a.heldout),
            *(["--heldout-sources", str(a.heldout_sources)] if a.heldout_sources else []),
            *(["--rl-tasks", str(a.rl_tasks), "--rl-ids", str(a.rl_ids), "--rl-max-new", str(a.rl_max_new),
               "--rl-limit", str(a.rl_limit), "--rl-k", str(a.rl_k),
               "--rl-seconds", str(a.rl_seconds)] if a.rl_tasks and a.rl_ids else []),
            *(["--no-before"] if no_before else []), "--out", str(arm_out)]


def run_arm(out: Path, arm: str, cmd: list[str], timeout: float | None = None) -> dict:
    """day_one_probe.run_sft_arm (weights and generations removed even on failure) plus the optimizer steps done."""
    if timeout is not None and timeout <= 0:
        raise RuntimeError(f"arm {arm} not started: the job's own deadline has passed")
    res = probe.run_sft_arm(out, arm, cmd, timeout)
    res["steps_completed"] = len(json.loads((out / f"sft_{arm}" / "sft_report.json").read_text()).get("log", []))
    return res


def check_run_and_inputs(a) -> dict:
    """Before any row is built: every input file present, the run folder's block size equal to the slice limit (the
    slice hashes in the request are for 2,048), and the RL pool the pinned file. Raises with the input named."""
    need = {"run folder checkpoint.pt": a.run_folder / "checkpoint.pt", "run folder manifest.json": a.run_folder / "manifest.json",
            **{f"pack shard {i} (OCR-2 pack job #565, out/firewalled)": p for i, p in enumerate(a.packs)}}
    if a.rl_tasks:
        need["RL pool cc.jsonl (RL data v1 pool job #564, out/run/out/v1)"] = a.rl_tasks
    if a.rl_ids:
        need["RL ids"] = a.rl_ids
    missing = [f"{k}: {v}" for k, v in need.items() if not Path(v).is_file()]
    if missing:
        raise FileNotFoundError("input missing, nothing was built; run the job that stores it first: " + "; ".join(missing))
    block = json.loads((a.run_folder / "manifest.json").read_text(encoding="utf-8"))["config"]["model"]["block_size"]
    if block != a.max_tokens:
        raise ValueError(f"run folder block_size {block} != --max-tokens {a.max_tokens}: the slice (and its sha256 in the "
                         "request) is defined for the run's context; check the run folder or rebuild the slice table")
    rl_sha = probe.sha256_file(a.rl_tasks) if a.rl_tasks else None
    if rl_sha is not None and rl_sha != RL_POOL_SHA256 and not a.no_pack_check:
        raise ValueError(f"RL pool sha256 {rl_sha} is not the pinned RL data v1 cc.jsonl {RL_POOL_SHA256}")
    return {"block_size": block, "rl_pool_sha256": rl_sha, "inputs_present": sorted(need)}


def check_g5_sources(a) -> dict:
    """The adapter refuses a run folder whose Team 5 source files differ from --g5-root (team5_adapter, run folder
    source pin). Apply the same comparison before any row is built, so a wrong checkout stops the job at once with
    both hashes and the remedy, not after the slice. Not a relaxation: the adapter's own check still runs."""
    from team5_adapter import RUN_FOLDER_SOURCE_FILES  # noqa: PLC0415
    recorded = json.loads((a.run_folder / "manifest.json").read_text(encoding="utf-8")).get("sources") or {}
    team5 = Path(a.g5_root) / "teams" / "05-architecture"
    rows = {}
    for name, rel in RUN_FOLDER_SOURCE_FILES.items():
        f = team5 / rel
        rows[name] = {"run_manifest": recorded.get(name), "g5_root": probe.sha256_file(f) if f.is_file() else None}
    bad = [n for n, r in rows.items() if r["run_manifest"] != r["g5_root"]]
    if bad:
        raise ValueError(
            "--g5-root is not the checkout this run folder was trained from; the adapter would refuse the pair. "
            + "; ".join(f"{n}: run manifest {rows[n]['run_manifest']}, --g5-root {rows[n]['g5_root']}" for n in bad)
            + ". Point --g5-root at a lab checkout whose teams/05-architecture/harness files have the hashes in the "
              "run folder's manifest.json 'sources'.")
    return {"g5_sources": rows}


def run(a, out: Path) -> int:
    t_end = time.monotonic() + a.deadline_minutes * 60 if a.deadline_minutes else None

    def left() -> float | None:
        return None if t_end is None else t_end - time.monotonic()

    results = {"pins": probe.step(out, "pins", lambda: {**probe.check_pins(a.run_folder, a.tokenizer, a.byte_table),
                                                        **check_run_and_inputs(a), **check_g5_sources(a)})}
    if not results["pins"]["ok"]:
        return probe.finish(out, results)
    from make_adapter_config import write_config  # noqa: PLC0415
    cfg = write_config(out / "adapter.yaml", a.g5_root, a.run_folder, a.tokenizer, a.byte_table, TEAM10, a.origin,
                       not a.no_git)
    inp = out / "_inputs"

    def inputs():
        import sft_slice_v1  # noqa: PLC0415
        return sft_slice_v1.build(a.packs, a.tokenizer, a.byte_table, a.max_tokens, inp, a.dev_rows,
                                  check_hashes=not a.no_pack_check)
    results["inputs"] = probe.step(out, "inputs", inputs)
    if not results["inputs"]["ok"]:
        return probe.finish(out, results)
    dev = inp / "dev.jsonl"
    results["sft_a2"] = probe.step(out, "sft_a2", lambda: run_arm(
        out, "a2", sft_cmd(a, cfg, inp / "a2_train.jsonl", dev, out / "sft_a2", a.steps, False), left()))
    a2 = results["sft_a2"]
    steps_a4 = a2.get("steps_completed") or a.steps
    before = a2.get("before") if a2["ok"] else None
    results["sft_a4"] = probe.step(out, "sft_a4", lambda: run_arm(
        out, "a4", sft_cmd(a, cfg, inp / "a4_train.jsonl", dev, out / "sft_a4", steps_a4, before is not None), left()))

    def compare():
        reps = {arm: json.loads((out / f"sft_{arm}" / "sft_report.json").read_text())
                for arm in ("a2", "a4") if results[f"sft_{arm}"]["ok"]}
        if len(reps) < 2:
            raise RuntimeError(f"only {sorted(reps)} finished: no comparison")
        afters = [reps[x].get("after") or {} for x in ("a2", "a4")]
        # arms are compared on the prompts both screens reached within their time budgets (same ids, same order)
        gen_ids = common_prefix([x.get("generation") for x in afters], "per_row")
        rl_ids = common_prefix([x.get("rl_screen") for x in afters], "per_prompt")
        m = {arm.upper(): arm_metrics(rep, before or rep.get("before"), gen_ids, rl_ids) for arm, rep in reps.items()}
        base = before or reps["a2"].get("before") or {}
        return {"arms": m, "steps_matched": m["A2"]["steps"] == m["A4"]["steps"], "decision": decide(m["A2"], m["A4"]),
                "compared_on": {"format_rows": None if gen_ids is None else len(gen_ids),
                                "rl_prompts": None if rl_ids is None else len(rl_ids)},
                "base": {"forgetting": base.get("forgetting"),
                         **screen_metrics(base.get("generation"), base.get("rl_screen"), gen_ids, rl_ids)}}
    results["compare"] = probe.step(out, "compare", compare)
    return probe.finish(out, results)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--g5-root", type=Path, required=True)
    ap.add_argument("--run-folder", type=Path, required=True)
    ap.add_argument("--tokenizer", type=Path, required=True)
    ap.add_argument("--byte-table", type=Path, required=True)
    ap.add_argument("--heldout", type=Path, required=True)
    ap.add_argument("--heldout-sources", type=Path)
    ap.add_argument("--packs", type=Path, nargs="+", required=True, help="firewalled OCR-2 pack shards (sha256-checked)")
    ap.add_argument("--no-pack-check", action="store_true", help="tests only: accept packs not in the firewall record and an RL pool other than the pin")
    ap.add_argument("--max-tokens", type=int, default=2048, help="row length limit (dropped, never cut); = block size")
    ap.add_argument("--dev-rows", type=int, default=256)
    ap.add_argument("--rl-tasks", type=Path)
    ap.add_argument("--rl-ids", type=Path)
    ap.add_argument("--rl-k", type=int, default=8)
    ap.add_argument("--rl-max-new", type=int, default=1536)
    ap.add_argument("--rl-limit", type=int, default=48)
    ap.add_argument("--rl-seconds", type=float, default=0.0,
                    help="time budget per RL screen (base, A2, A4); arms are compared on the prompts both reached")
    ap.add_argument("--method", choices=("full", "lora_markers"), default="full",
                    help="lora_markers = LoRA plus the nine marker rows of the untied output head")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--marker-lr", type=float, default=1e-3)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--max-train-seconds", type=float, default=1200.0, help="training cap of the A2 arm")
    ap.add_argument("--deadline-minutes", type=float, default=0.0,
                    help="wall-clock cap of the whole job from its start: an arm still running then is killed and "
                         "reported as stopped at the deadline (0 = off)")
    ap.add_argument("--gen-limit", type=int, default=32)
    ap.add_argument("--gen-max-new", type=int, default=1536)
    ap.add_argument("--gen-seconds", type=float, default=0.0, help="time budget per greedy format screen")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--origin", default="g10_rehearsal", choices=("g10_rehearsal", "g5_delivery"))
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", type=Path, required=True)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    try:
        return run(a, out)
    finally:
        shutil.rmtree(out / "_inputs", ignore_errors=True)  # built rows never leave the job


if __name__ == "__main__":
    raise SystemExit(main())
